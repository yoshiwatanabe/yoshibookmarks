"""Integration tests for bookmark API endpoints."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from yoshibookmark.config import ConfigManager
from yoshibookmark.models.storage import StorageLocation


@pytest.fixture
def test_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".yoshibookmark"
        config_dir.mkdir(parents=True)

        # Create storage directory
        storage_dir = config_dir / "storage" / "test"
        storage_dir.mkdir(parents=True)

        # Create .env file
        env_file = config_dir / ".env"
        env_file.write_text("OPENAI_API_KEY=test-key-123")

        # Create config.yaml
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

        yield config_dir


@pytest.fixture
def client(test_config_dir):
    """Create test client with initialized managers."""
    # Import required modules
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from yoshibookmark import api
    from yoshibookmark.api.bookmarks import router as bookmarks_router
    from yoshibookmark.api.health import router as health_router
    from yoshibookmark.core.bookmark_manager import BookmarkManager
    from yoshibookmark.core.content_analyzer import ContentAnalyzer
    from yoshibookmark.core.storage_manager import StorageManager

    # Load actual config
    real_cm = ConfigManager(test_config_dir)
    app_config = real_cm.load_app_config()
    env_settings = real_cm.load_env_settings()

    # Initialize managers directly
    api.config_manager = real_cm
    api.runtime_config = app_config
    api.storage_manager = StorageManager()

    # Run async initialization
    async def init_storage():
        await api.storage_manager.initialize(app_config.storage_locations)

    asyncio.run(init_storage())

    api.bookmark_manager = BookmarkManager(api.storage_manager)
    api.content_analyzer = ContentAnalyzer(timeout=app_config.screenshot_timeout)

    # Create test app without lifespan handler
    test_app = FastAPI(
        title="YoshiBookmark API",
        description="URL and bookmark management system with intelligent search",
        version="0.1.0",
    )

    # Add CORS middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    test_app.include_router(bookmarks_router, prefix="/api/v1", tags=["bookmarks"])
    test_app.include_router(health_router, prefix="/api/v1", tags=["health"])

    # Add root endpoint
    @test_app.get("/")
    async def root():
        return {
            "name": "YoshiBookmark API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    with TestClient(test_app) as test_client:
        yield test_client


class TestBookmarkEndpoints:
    """Test bookmark CRUD endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "YoshiBookmark API"
        assert "docs" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["storage_mode"] != "unknown"
        assert data["primary_storage_provider"] != "unknown"
        assert data["storage_count"] >= 1
        assert data["current_storage"] is not None
        assert "conflict_count" in data

    def test_create_bookmark_with_auto_analysis(self, client):
        """Test creating bookmark with automatic title/keyword analysis."""
        # Mock content analyzer
        from yoshibookmark import api

        mock_analysis = {
            "title": "Example Domain",
            "keywords": ["example", "test"],
            "error": None,
        }

        with patch.object(api.content_analyzer, 'analyze_url', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis

            response = client.post(
                "/api/v1/bookmarks",
                json={
                    "url": "https://example.com",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["url"] == "https://example.com/"
            assert data["title"] == "Example Domain"
            assert "example" in data["keywords"]

    def test_create_bookmark_with_manual_title(self, client):
        """Test creating bookmark with manual title."""
        response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "My Custom Title",
                "keywords": ["custom", "test"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Custom Title"
        assert "custom" in data["keywords"]

    def test_create_bookmark_with_invalid_url(self, client):
        """Test creating bookmark with invalid URL fails."""
        response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "not-a-valid-url",
                "title": "Test",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_list_bookmarks_empty(self, client):
        """Test listing bookmarks when none exist."""
        response = client.get("/api/v1/bookmarks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["bookmarks"] == []

    def test_list_bookmarks_with_data(self, client):
        """Test listing bookmarks."""
        # Create a bookmark first
        client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test Bookmark",
                "keywords": ["test"],
            },
        )

        # List bookmarks
        response = client.get("/api/v1/bookmarks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["bookmarks"]) == 1
        assert data["bookmarks"][0]["title"] == "Test Bookmark"

    def test_get_bookmark_by_id(self, client):
        """Test getting a specific bookmark."""
        # Create bookmark
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test",
                "keywords": ["test"],
            },
        )
        bookmark_id = create_response.json()["id"]

        # Get bookmark
        response = client.get(f"/api/v1/bookmarks/{bookmark_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bookmark_id
        assert data["title"] == "Test"

    def test_get_nonexistent_bookmark(self, client):
        """Test getting non-existent bookmark returns 404."""
        response = client.get("/api/v1/bookmarks/nonexistent-id")

        assert response.status_code == 404

    def test_update_bookmark(self, client):
        """Test updating a bookmark."""
        # Create bookmark
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Original Title",
                "keywords": ["original"],
            },
        )
        bookmark_id = create_response.json()["id"]

        # Update bookmark
        response = client.put(
            f"/api/v1/bookmarks/{bookmark_id}",
            json={
                "title": "Updated Title",
                "keywords": ["updated"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert "updated" in data["keywords"]
        assert data["last_modified"] is not None

    def test_update_nonexistent_bookmark(self, client):
        """Test updating non-existent bookmark returns 404."""
        response = client.put(
            "/api/v1/bookmarks/nonexistent-id",
            json={"title": "New Title"},
        )

        assert response.status_code == 404

    def test_soft_delete_bookmark(self, client):
        """Test soft deleting a bookmark."""
        # Create bookmark
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test",
                "keywords": ["test"],
            },
        )
        bookmark_id = create_response.json()["id"]

        # Soft delete
        response = client.delete(f"/api/v1/bookmarks/{bookmark_id}?hard=false")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert data["deleted_at"] is not None

    def test_hard_delete_requires_soft_delete_first(self, client):
        """Test hard delete requires soft delete first."""
        # Create bookmark
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test",
                "keywords": ["test"],
            },
        )
        bookmark_id = create_response.json()["id"]

        # Try to hard delete without soft delete
        response = client.delete(f"/api/v1/bookmarks/{bookmark_id}?hard=true")

        assert response.status_code == 400  # Bad request

    def test_delete_already_deleted_bookmark(self, client):
        """Test deleting already deleted bookmark returns 409."""
        # Create and soft delete bookmark
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test",
                "keywords": ["test"],
            },
        )
        bookmark_id = create_response.json()["id"]

        client.delete(f"/api/v1/bookmarks/{bookmark_id}")

        # Try to delete again
        response = client.delete(f"/api/v1/bookmarks/{bookmark_id}")

        assert response.status_code == 409  # Conflict

    def test_restore_deleted_bookmark(self, client):
        """Test restoring a soft-deleted bookmark."""
        # Create and delete bookmark
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test",
                "keywords": ["test"],
            },
        )
        bookmark_id = create_response.json()["id"]

        client.delete(f"/api/v1/bookmarks/{bookmark_id}")

        # Restore
        response = client.post(f"/api/v1/bookmarks/{bookmark_id}/restore")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is False
        assert data["deleted_at"] is None

    def test_restore_non_deleted_bookmark(self, client):
        """Test restoring non-deleted bookmark returns 409."""
        # Create bookmark (not deleted)
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test",
                "keywords": ["test"],
            },
        )
        bookmark_id = create_response.json()["id"]

        # Try to restore
        response = client.post(f"/api/v1/bookmarks/{bookmark_id}/restore")

        assert response.status_code == 409  # Conflict

    def test_track_bookmark_access(self, client):
        """Test tracking bookmark access."""
        # Create bookmark
        create_response = client.post(
            "/api/v1/bookmarks",
            json={
                "url": "https://example.com",
                "title": "Test",
                "keywords": ["test"],
            },
        )
        bookmark_id = create_response.json()["id"]

        # Track access
        response = client.post(f"/api/v1/bookmarks/{bookmark_id}/access")

        assert response.status_code == 200
        data = response.json()
        assert data["last_accessed"] is not None

    def test_list_bookmarks_exclude_deleted(self, client):
        """Test list excludes deleted bookmarks by default."""
        # Create two bookmarks
        resp1 = client.post(
            "/api/v1/bookmarks",
            json={"url": "https://example1.com", "title": "Active", "keywords": ["test"]},
        )

        resp2 = client.post(
            "/api/v1/bookmarks",
            json={"url": "https://example2.com", "title": "Deleted", "keywords": ["test"]},
        )

        # Delete second bookmark
        bookmark_id = resp2.json()["id"]
        client.delete(f"/api/v1/bookmarks/{bookmark_id}")

        # List bookmarks (should exclude deleted)
        response = client.get("/api/v1/bookmarks?include_deleted=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["bookmarks"][0]["title"] == "Active"

    def test_list_bookmarks_include_deleted(self, client):
        """Test list can include deleted bookmarks."""
        # Create and delete bookmark
        resp = client.post(
            "/api/v1/bookmarks",
            json={"url": "https://example.com", "title": "Deleted", "keywords": ["test"]},
        )
        bookmark_id = resp.json()["id"]
        client.delete(f"/api/v1/bookmarks/{bookmark_id}")

        # List with deleted
        response = client.get("/api/v1/bookmarks?include_deleted=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["bookmarks"][0]["deleted"] is True

    def test_onedrive_only_rejects_mismatched_storage(self, test_config_dir):
        """Test OneDrive-only mode rejects non-primary storage in requests."""
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.testclient import TestClient

        from yoshibookmark import api
        from yoshibookmark.api.bookmarks import router as bookmarks_router
        from yoshibookmark.api.health import router as health_router
        from yoshibookmark.core.bookmark_manager import BookmarkManager
        from yoshibookmark.core.content_analyzer import ContentAnalyzer
        from yoshibookmark.core.storage_manager import StorageManager

        cm = ConfigManager(test_config_dir)
        app_config = cm.load_app_config().model_copy(
            update={
                "storage_mode": "onedrive_only",
                "primary_storage_provider": "onedrive_local",
                "primary_storage_path": cm.load_app_config().storage_locations[0].path,
            }
        )

        api.config_manager = cm
        api.runtime_config = app_config
        api.storage_manager = StorageManager()

        async def init_storage():
            await api.storage_manager.initialize(app_config.storage_locations)

        asyncio.run(init_storage())
        api.bookmark_manager = BookmarkManager(api.storage_manager)
        api.content_analyzer = ContentAnalyzer(timeout=app_config.screenshot_timeout)

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

        with TestClient(test_app) as local_client:
            response = local_client.post(
                "/api/v1/bookmarks",
                json={
                    "url": "https://example.com",
                    "title": "Test",
                    "keywords": ["test"],
                    "storage_location": "wrong-storage",
                },
            )
            assert response.status_code == 400
