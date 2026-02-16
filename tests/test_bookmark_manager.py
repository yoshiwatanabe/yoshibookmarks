"""Tests for BookmarkManager CRUD operations."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from yoshibookmark.core.bookmark_manager import (
    BookmarkAlreadyDeletedError,
    BookmarkManager,
    BookmarkNotFoundError,
)
from yoshibookmark.core.storage_manager import StorageManager
from yoshibookmark.models.storage import StorageLocation


@pytest.fixture
async def manager():
    """Create BookmarkManager with test storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageLocation(name="test", path=temp_dir)

        storage_manager = StorageManager()
        await storage_manager.initialize([storage])

        bookmark_manager = BookmarkManager(storage_manager)

        yield bookmark_manager


class TestBookmarkManager:
    """Test BookmarkManager functionality."""

    @pytest.mark.asyncio
    async def test_create_bookmark_with_valid_data(self, manager):
        """Test creating bookmark with valid data."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test Bookmark",
            storage_location="test",
            keywords=["test", "example"],
            description="A test bookmark",
        )

        assert bookmark.id is not None
        assert str(bookmark.url) == "https://example.com/"
        assert bookmark.title == "Test Bookmark"
        assert len(bookmark.keywords) == 2
        assert bookmark.description == "A test bookmark"
        assert bookmark.created_at is not None

    @pytest.mark.asyncio
    async def test_create_bookmark_with_invalid_url(self, manager):
        """Test creating bookmark with invalid URL fails."""
        with pytest.raises(ValidationError):
            await manager.create_bookmark(
                url="not-a-valid-url",
                title="Test",
                storage_location="test",
            )

    @pytest.mark.asyncio
    async def test_get_existing_bookmark(self, manager):
        """Test getting an existing bookmark."""
        created = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        retrieved = await manager.get_bookmark(created.id, "test")

        assert retrieved.id == created.id
        assert retrieved.title == created.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_bookmark(self, manager):
        """Test getting non-existent bookmark raises error."""
        with pytest.raises(BookmarkNotFoundError, match="Bookmark not found"):
            await manager.get_bookmark("nonexistent-id", "test")

    @pytest.mark.asyncio
    async def test_update_bookmark_title(self, manager):
        """Test updating bookmark title."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Original Title",
            storage_location="test",
        )

        updated = await manager.update_bookmark(
            bookmark.id,
            storage_name="test",
            title="Updated Title",
        )

        assert updated.title == "Updated Title"
        assert updated.last_modified is not None

    @pytest.mark.asyncio
    async def test_update_bookmark_keywords(self, manager):
        """Test updating bookmark keywords."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            keywords=["old"],
            storage_location="test",
        )

        updated = await manager.update_bookmark(
            bookmark.id,
            storage_name="test",
            keywords=["new", "updated"],
        )

        assert len(updated.keywords) == 2
        assert "new" in updated.keywords
        assert "old" not in updated.keywords

    @pytest.mark.asyncio
    async def test_update_nonexistent_bookmark(self, manager):
        """Test updating non-existent bookmark fails."""
        with pytest.raises(BookmarkNotFoundError):
            await manager.update_bookmark(
                "nonexistent-id",
                storage_name="test",
                title="New Title",
            )

    @pytest.mark.asyncio
    async def test_soft_delete_bookmark(self, manager):
        """Test soft deleting a bookmark."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        deleted = await manager.delete_bookmark(bookmark.id, "test")

        assert deleted.deleted is True
        assert deleted.deleted_at is not None

        # Bookmark still exists but is marked deleted
        retrieved = await manager.get_bookmark(bookmark.id, "test")
        assert retrieved.deleted is True

    @pytest.mark.asyncio
    async def test_delete_already_deleted_bookmark(self, manager):
        """Test deleting already deleted bookmark raises error."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        await manager.delete_bookmark(bookmark.id, "test")

        # Try to delete again
        with pytest.raises(BookmarkAlreadyDeletedError, match="already deleted"):
            await manager.delete_bookmark(bookmark.id, "test")

    @pytest.mark.asyncio
    async def test_restore_deleted_bookmark(self, manager):
        """Test restoring a soft-deleted bookmark."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        # Delete
        await manager.delete_bookmark(bookmark.id, "test")

        # Restore
        restored = await manager.restore_bookmark(bookmark.id, "test")

        assert restored.deleted is False
        assert restored.deleted_at is None

    @pytest.mark.asyncio
    async def test_restore_non_deleted_bookmark(self, manager):
        """Test restoring non-deleted bookmark raises error."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        with pytest.raises(ValueError, match="is not deleted"):
            await manager.restore_bookmark(bookmark.id, "test")

    @pytest.mark.asyncio
    async def test_hard_delete_soft_deleted_bookmark(self, manager):
        """Test hard deleting a soft-deleted bookmark."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        # Soft delete first
        await manager.delete_bookmark(bookmark.id, "test")

        # Hard delete
        await manager.hard_delete_bookmark(bookmark.id, "test")

        # Bookmark should no longer exist
        with pytest.raises(BookmarkNotFoundError):
            await manager.get_bookmark(bookmark.id, "test")

    @pytest.mark.asyncio
    async def test_hard_delete_active_bookmark_fails(self, manager):
        """Test hard deleting active bookmark fails (safety check)."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        # Try to hard delete without soft delete
        with pytest.raises(ValueError, match="must be soft-deleted"):
            await manager.hard_delete_bookmark(bookmark.id, "test")

    @pytest.mark.asyncio
    async def test_track_access_updates_timestamp(self, manager):
        """Test tracking access updates last_accessed timestamp."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Test",
            storage_location="test",
        )

        assert bookmark.last_accessed is None

        # Track access
        accessed = await manager.track_access(bookmark.id, "test")

        assert accessed.last_accessed is not None

    @pytest.mark.asyncio
    async def test_list_bookmarks_excludes_deleted(self, manager):
        """Test list_bookmarks excludes deleted by default."""
        # Create active bookmark
        active = await manager.create_bookmark(
            url="https://example1.com",
            title="Active",
            storage_location="test",
        )

        # Create and delete bookmark
        deleted = await manager.create_bookmark(
            url="https://example2.com",
            title="Deleted",
            storage_location="test",
        )
        await manager.delete_bookmark(deleted.id, "test")

        # List bookmarks
        bookmarks = manager.list_bookmarks("test", include_deleted=False)

        assert len(bookmarks) == 1
        assert bookmarks[0].id == active.id

    @pytest.mark.asyncio
    async def test_list_bookmarks_includes_deleted(self, manager):
        """Test list_bookmarks can include deleted."""
        # Create active and deleted bookmarks
        await manager.create_bookmark(
            url="https://example1.com",
            title="Active",
            storage_location="test",
        )

        deleted = await manager.create_bookmark(
            url="https://example2.com",
            title="Deleted",
            storage_location="test",
        )
        await manager.delete_bookmark(deleted.id, "test")

        # List all bookmarks
        all_bookmarks = manager.list_bookmarks("test", include_deleted=True)

        assert len(all_bookmarks) == 2

    @pytest.mark.asyncio
    async def test_list_bookmarks_filter_by_folder(self, manager):
        """Test list_bookmarks filters by folder path."""
        # Create bookmarks in different folders
        await manager.create_bookmark(
            url="https://example1.com",
            title="In Folder 1",
            folder_path="folder1",
            storage_location="test",
        )

        await manager.create_bookmark(
            url="https://example2.com",
            title="In Folder 2",
            folder_path="folder2",
            storage_location="test",
        )

        # Filter by folder1
        folder1_bookmarks = manager.list_bookmarks("test", folder_path="folder1")

        assert len(folder1_bookmarks) == 1
        assert folder1_bookmarks[0].folder_path == "folder1"

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, manager):
        """Test updating multiple fields at once."""
        bookmark = await manager.create_bookmark(
            url="https://example.com",
            title="Original",
            keywords=["old"],
            storage_location="test",
        )

        # Update multiple fields
        updated = await manager.update_bookmark(
            bookmark.id,
            storage_name="test",
            title="Updated Title",
            keywords=["new", "keywords"],
            description="Added description",
        )

        assert updated.title == "Updated Title"
        assert len(updated.keywords) == 2
        assert updated.description == "Added description"
        assert updated.last_modified is not None
