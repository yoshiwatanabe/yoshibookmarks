"""Integration tests for recall API endpoint."""

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from yoshibookmark.config import ConfigManager


@pytest.fixture
def recall_client():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".yoshibookmark"
        config_dir.mkdir(parents=True)
        storage_dir = config_dir / "storage" / "test"
        storage_dir.mkdir(parents=True)

        env_file = config_dir / ".env"
        env_file.write_text("OPENAI_API_KEY=test-key-123\nEXTENSION_API_TOKEN=test-token\n")

        import yaml

        config_file = config_dir / "config.yaml"
        config_data = {
            "storage_locations": [
                {
                    "name": "test",
                    "path": str(storage_dir),
                    "is_current": True,
                    "is_default": True,
                }
            ],
            "enable_semantic_search": False,
            "enable_screenshots": False,
        }
        config_file.write_text(yaml.safe_dump(config_data))

        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        from yoshibookmark import api
        from yoshibookmark.api.bookmarks import router as bookmarks_router
        from yoshibookmark.api.recall import router as recall_router
        from yoshibookmark.core.bookmark_manager import BookmarkManager
        from yoshibookmark.core.content_analyzer import ContentAnalyzer
        from yoshibookmark.core.recall_service import RecallService
        from yoshibookmark.core.storage_manager import StorageManager

        real_cm = ConfigManager(config_dir)
        app_config = real_cm.load_app_config()
        env_settings = real_cm.load_env_settings()

        api.config_manager = real_cm
        api.runtime_config = app_config
        api.runtime_env_settings = env_settings
        api.storage_manager = StorageManager()

        async def init_storage():
            await api.storage_manager.initialize(app_config.storage_locations)

        asyncio.run(init_storage())
        api.bookmark_manager = BookmarkManager(api.storage_manager)
        api.content_analyzer = ContentAnalyzer(timeout=app_config.screenshot_timeout)
        api.recall_service = RecallService(
            config=app_config,
            storage_manager=api.storage_manager,
            env_settings=env_settings,
        )

        async def seed():
            await api.bookmark_manager.create_bookmark(
                url="https://github.com/yoshiwatanabe/cmdai",
                title="cmdai repository",
                storage_location="test",
                keywords=["cmdai", "github", "ai"],
                description="source for cmdai project",
                tags=["tool", "ai"],
            )
            await api.bookmark_manager.create_bookmark(
                url="https://example.com/python-style",
                title="Python style guide",
                storage_location="test",
                keywords=["python", "guide"],
                description="best practices and linting",
                tags=["python"],
            )

        asyncio.run(seed())

        test_app = FastAPI(version="0.1.0")
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        test_app.include_router(bookmarks_router, prefix="/api/v1", tags=["bookmarks"])
        test_app.include_router(recall_router, prefix="/api/v1", tags=["recall"])

        with TestClient(test_app) as client:
            yield client


class TestRecallEndpoint:
    def test_recall_query_returns_ranked_results(self, recall_client):
        response = recall_client.post(
            "/api/v1/recall/query",
            json={"query": "cmdai github project", "limit": 20, "scope": "all"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "keyword_only"
        assert data["semantic_available"] is False
        assert data["total_returned"] >= 1
        assert data["results"][0]["bookmark"]["title"] == "cmdai repository"

    def test_recall_scope_current(self, recall_client):
        response = recall_client.post(
            "/api/v1/recall/query",
            json={"query": "python guide", "scope": "current"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["searched_storage_names"] == ["test"]
        assert data["total_returned"] >= 1

    def test_recall_invalid_query(self, recall_client):
        response = recall_client.post("/api/v1/recall/query", json={"query": ""})
        assert response.status_code == 422
