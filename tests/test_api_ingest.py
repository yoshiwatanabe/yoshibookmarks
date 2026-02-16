"""Integration tests for ingestion endpoints."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from yoshibookmark.config import ConfigManager


@pytest.fixture
def ingest_client():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".yoshibookmark"
        config_dir.mkdir(parents=True)

        storage_dir = config_dir / "storage" / "test"
        storage_dir.mkdir(parents=True)

        env_file = config_dir / ".env"
        env_file.write_text(
            "\n".join(
                [
                    "OPENAI_API_KEY=test-key-123",
                    "EXTENSION_API_TOKEN=test-token",
                ]
            )
        )

        import yaml

        config_file = config_dir / "config.yaml"
        config_file.write_text(
            yaml.safe_dump(
                {
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
                    "ingest_require_auth": True,
                    "openai_enabled": False,
                    "azure_openai_enabled": False,
                    "anthropic_enabled": False,
                    "gemini_enabled": False,
                }
            )
        )

        from yoshibookmark import api
        from yoshibookmark.api.bookmarks import router as bookmarks_router
        from yoshibookmark.api.health import router as health_router
        from yoshibookmark.api.ingest import router as ingest_router
        from yoshibookmark.core.ai_inference import MultiProviderInferenceService
        from yoshibookmark.core.bookmark_manager import BookmarkManager
        from yoshibookmark.core.content_analyzer import ContentAnalyzer
        from yoshibookmark.core.ingestion_service import IngestionService
        from yoshibookmark.core.storage_manager import StorageManager

        cm = ConfigManager(config_dir)
        app_config = cm.load_app_config()
        env_settings = cm.load_env_settings()

        api.config_manager = cm
        api.runtime_config = app_config
        api.runtime_env_settings = env_settings
        api.storage_manager = StorageManager()

        async def init_storage():
            await api.storage_manager.initialize(app_config.storage_locations)

        asyncio.run(init_storage())

        api.bookmark_manager = BookmarkManager(api.storage_manager)
        api.content_analyzer = ContentAnalyzer(timeout=app_config.screenshot_timeout)
        inference = MultiProviderInferenceService(app_config)
        api.ingestion_service = IngestionService(
            config=app_config,
            bookmark_manager=api.bookmark_manager,
            storage_manager=api.storage_manager,
            content_analyzer=api.content_analyzer,
            inference_service=inference,
        )

        # Avoid external calls in tests.
        api.ingestion_service.inference_service.generate_structured_metadata = AsyncMock(
            return_value=(
                {
                    "title": "Suggested Title",
                    "keywords": ["alpha", "beta"],
                    "tags": ["project-x"],
                    "summary": "Suggested summary",
                    "confidence": 0.92,
                },
                [],
            )
        )

        test_app = FastAPI(version="0.1.0")
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        test_app.include_router(bookmarks_router, prefix="/api/v1", tags=["bookmarks"])
        test_app.include_router(health_router, prefix="/api/v1", tags=["health"])
        test_app.include_router(ingest_router, prefix="/api/v1", tags=["ingest"])

        with TestClient(test_app) as client:
            yield client


class TestIngestEndpoints:
    def test_preview_requires_auth(self, ingest_client):
        response = ingest_client.post(
            "/api/v1/ingest/preview",
            json={"url": "https://example.com", "page_title": "Example"},
        )
        assert response.status_code == 401

    def test_preview_and_commit_flow(self, ingest_client):
        preview_response = ingest_client.post(
            "/api/v1/ingest/preview",
            headers={"Authorization": "Bearer test-token"},
            json={
                "url": "https://example.com",
                "page_title": "Example",
                "selected_text": "important reference",
                "user_note": "for annual report",
            },
        )
        assert preview_response.status_code == 200
        preview = preview_response.json()
        assert "preview_id" in preview
        assert preview["suggested_title"] == "Suggested Title"
        assert "alpha" in preview["suggested_keywords"]

        commit_response = ingest_client.post(
            "/api/v1/ingest/commit",
            headers={"Authorization": "Bearer test-token"},
            json={
                "preview_id": preview["preview_id"],
                "title": "Final Title",
                "keywords": ["final"],
            },
        )
        assert commit_response.status_code == 200
        payload = commit_response.json()
        assert payload["status"] == "committed"
        assert payload["bookmark"]["title"] == "Final Title"
        assert payload["bookmark"]["keywords"][0] == "final"

    def test_quick_save(self, ingest_client):
        response = ingest_client.post(
            "/api/v1/ingest/quick-save",
            headers={"Authorization": "Bearer test-token"},
            json={
                "url": "https://example.org",
                "page_title": "Example Org",
                "selected_text": "some context",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "saved"
        assert body["bookmark"]["url"] == "https://example.org/"

    def test_provider_status(self, ingest_client):
        response = ingest_client.get("/api/v1/ingest/providers/status")
        assert response.status_code == 200
        body = response.json()
        assert "providers" in body
