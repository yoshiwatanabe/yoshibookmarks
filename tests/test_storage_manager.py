"""Tests for StorageManager and file locking."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from yoshibookmark.core.storage_manager import StorageError, StorageManager
from yoshibookmark.models.bookmark import Bookmark
from yoshibookmark.models.storage import StorageLocation
from yoshibookmark.utils.file_lock import FileLocker, FileLockError


class TestFileLocker:
    """Test file locking functionality."""

    def test_file_lock_acquire_release(self):
        """Test basic lock acquisition and release."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            file_path.touch()

            with FileLocker(file_path) as locker:
                assert locker.acquired
                assert locker.lock_path.exists()

            # Lock should be released
            assert not locker.lock_path.exists()

    @pytest.mark.asyncio
    async def test_async_file_lock(self):
        """Test async file locking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            file_path.touch()

            async with FileLocker(file_path) as locker:
                assert locker.acquired
                assert locker.lock_path.exists()

            assert not locker.lock_path.exists()

    def test_concurrent_lock_blocks(self):
        """Test that concurrent lock attempts block correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            file_path.touch()

            with FileLocker(file_path, timeout=1.0):
                # Second lock should timeout
                with pytest.raises(FileLockError, match="Could not acquire lock"):
                    with FileLocker(file_path, timeout=0.5):
                        pass

    def test_stale_lock_removed(self):
        """Test that stale locks are cleaned up."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            lock_path = Path(str(file_path) + ".lock")

            # Create a stale lock file and make it old
            lock_path.touch()
            import time
            import os
            # Set modification time to be old enough to be considered stale
            old_time = time.time() - 20  # 20 seconds ago
            os.utime(lock_path, (old_time, old_time))

            # Should be able to acquire despite stale lock
            with FileLocker(file_path, timeout=2.0):
                pass  # Should not timeout


class TestStorageManager:
    """Test StorageManager functionality."""

    @pytest.mark.asyncio
    async def test_initialize_storage(self):
        """Test initializing storage manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageLocation(
                name="test",
                path=temp_dir,
                is_current=True,
            )

            manager = StorageManager()
            await manager.initialize([storage])

            assert "test" in manager.storage_locations
            assert "test" in manager.in_memory_index
            assert manager.get_current_storage_name() == "test"

    @pytest.mark.asyncio
    async def test_storage_structure_created(self):
        """Test storage directory structure is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            assert (Path(temp_dir) / "bookmarks").exists()
            assert (Path(temp_dir) / "favicons").exists()
            assert (Path(temp_dir) / "screenshots").exists()

    @pytest.mark.asyncio
    async def test_save_and_load_bookmark(self):
        """Test saving and loading a bookmark."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            bookmark = Bookmark(
                url="https://example.com",
                title="Test Bookmark",
                keywords=["test"],
                storage_location="test",
            )

            # Save
            await manager.save_bookmark(bookmark, "test")

            # Verify file exists
            file_path = Path(temp_dir) / "bookmarks" / f"{bookmark.id}.yaml"
            assert file_path.exists()

            # Verify in-memory index
            loaded = manager.get_bookmark_by_id(bookmark.id, "test")
            assert loaded is not None
            assert loaded.title == "Test Bookmark"

    @pytest.mark.asyncio
    async def test_get_bookmarks_with_filters(self):
        """Test getting bookmarks with various filters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            # Create multiple bookmarks
            bookmark1 = Bookmark(
                url="https://example1.com",
                title="Bookmark 1",
                folder_path="folder1",
                storage_location="test",
            )
            bookmark2 = Bookmark(
                url="https://example2.com",
                title="Bookmark 2",
                folder_path="folder2",
                deleted=True,
                storage_location="test",
            )
            bookmark3 = Bookmark(
                url="https://example3.com",
                title="Bookmark 3",
                folder_path="folder1",
                storage_location="test",
            )

            await manager.save_bookmark(bookmark1, "test")
            await manager.save_bookmark(bookmark2, "test")
            await manager.save_bookmark(bookmark3, "test")

            # Test: Get all active bookmarks
            active = manager.get_bookmarks("test", include_deleted=False)
            assert len(active) == 2

            # Test: Get all including deleted
            all_bookmarks = manager.get_bookmarks("test", include_deleted=True)
            assert len(all_bookmarks) == 3

            # Test: Filter by folder
            folder1_bookmarks = manager.get_bookmarks("test", folder_path="folder1")
            assert len(folder1_bookmarks) == 2

    @pytest.mark.asyncio
    async def test_delete_bookmark_file(self):
        """Test hard deleting a bookmark file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            bookmark = Bookmark(
                url="https://example.com",
                title="Test",
                storage_location="test",
            )

            await manager.save_bookmark(bookmark, "test")

            file_path = Path(temp_dir) / "bookmarks" / f"{bookmark.id}.yaml"
            assert file_path.exists()

            # Delete
            await manager.delete_bookmark_file(bookmark.id, "test")

            assert not file_path.exists()
            assert manager.get_bookmark_by_id(bookmark.id, "test") is None

    @pytest.mark.asyncio
    async def test_load_corrupted_yaml_file(self):
        """Test loading storage with corrupted YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bookmarks_dir = Path(temp_dir) / "bookmarks"
            bookmarks_dir.mkdir(parents=True)

            # Create corrupted YAML file
            corrupted_file = bookmarks_dir / "corrupted.yaml"
            corrupted_file.write_text("invalid: yaml: content:")

            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            # Should skip corrupted file and continue
            assert len(manager.in_memory_index["test"]) == 0
            assert len(manager.load_errors["test"]) == 1

    @pytest.mark.asyncio
    async def test_duplicate_bookmark_id_detected(self):
        """Test duplicate bookmark ID conflict resolution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bookmarks_dir = Path(temp_dir) / "bookmarks"
            bookmarks_dir.mkdir(parents=True)

            # Create two files with same bookmark ID
            bookmark_id = "duplicate-id-123"
            yaml_content = f"""
id: {bookmark_id}
url: https://example.com
title: Test
storage_location: test
created_at: '2026-02-04T10:00:00Z'
keywords: []
deleted: false
"""

            (bookmarks_dir / "file1.yaml").write_text(yaml_content)
            (bookmarks_dir / "file2.yaml").write_text(yaml_content)

            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            # Should keep one winner and report a conflict
            assert len(manager.in_memory_index["test"]) == 1
            assert len(manager.conflicts["test"]) == 1
            assert "Conflict for bookmark ID" in manager.conflicts["test"][0]

    @pytest.mark.asyncio
    async def test_nonexistent_storage_error(self):
        """Test error when storage path doesn't exist."""
        storage = StorageLocation(
            name="test",
            path="/nonexistent/path/that/does/not/exist",
        )

        manager = StorageManager()

        with pytest.raises(StorageError, match="does not exist"):
            await manager.initialize([storage])

    @pytest.mark.asyncio
    async def test_file_as_storage_error(self):
        """Test error when storage path is a file, not directory."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file_path = tmp_file.name

        try:
            storage = StorageLocation(name="test", path=file_path)

            manager = StorageManager()

            with pytest.raises(StorageError, match="not a directory"):
                await manager.initialize([storage])
        finally:
            Path(file_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_permission_denied_error(self):
        """Test error when storage path is not writable."""
        # This test is platform-dependent and may need adjustment
        # Skipping on Windows where permission handling is different
        import sys
        if sys.platform == "win32":
            pytest.skip("Permission test not reliable on Windows")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Make directory read-only
            import os
            os.chmod(temp_dir, 0o444)

            try:
                storage = StorageLocation(name="test", path=temp_dir)
                manager = StorageManager()

                with pytest.raises(StorageError, match="Permission denied"):
                    await manager.initialize([storage])
            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)

    @pytest.mark.asyncio
    async def test_get_storage_stats(self):
        """Test getting storage statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            # Add bookmarks
            bookmark1 = Bookmark(
                url="https://example1.com",
                title="Active",
                storage_location="test",
            )
            bookmark2 = Bookmark(
                url="https://example2.com",
                title="Deleted",
                deleted=True,
                storage_location="test",
            )

            await manager.save_bookmark(bookmark1, "test")
            await manager.save_bookmark(bookmark2, "test")

            stats = manager.get_storage_stats("test")

            assert stats["total"] == 2
            assert stats["active"] == 1
            assert stats["deleted"] == 1
            assert stats["errors"] == 0
            assert stats["conflicts"] == 0

    @pytest.mark.asyncio
    async def test_get_bookmark_global_search(self):
        """Test searching for bookmark across all storages."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            with tempfile.TemporaryDirectory() as temp_dir2:
                storage1 = StorageLocation(name="storage1", path=temp_dir1)
                storage2 = StorageLocation(name="storage2", path=temp_dir2)

                manager = StorageManager()
                await manager.initialize([storage1, storage2])

                bookmark1 = Bookmark(
                    url="https://example1.com",
                    title="In Storage 1",
                    storage_location="storage1",
                )
                bookmark2 = Bookmark(
                    url="https://example2.com",
                    title="In Storage 2",
                    storage_location="storage2",
                )

                await manager.save_bookmark(bookmark1, "storage1")
                await manager.save_bookmark(bookmark2, "storage2")

                # Search without specifying storage
                found = manager.get_bookmark_by_id(bookmark1.id)
                assert found is not None
                assert found.title == "In Storage 1"

                found2 = manager.get_bookmark_by_id(bookmark2.id)
                assert found2 is not None
                assert found2.title == "In Storage 2"

    @pytest.mark.asyncio
    async def test_concurrent_saves(self):
        """Test concurrent bookmark saves with file locking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageLocation(name="test", path=temp_dir)

            manager = StorageManager()
            await manager.initialize([storage])

            # Create multiple bookmarks
            bookmarks = [
                Bookmark(
                    url=f"https://example{i}.com",
                    title=f"Bookmark {i}",
                    storage_location="test",
                )
                for i in range(10)
            ]

            # Save concurrently
            tasks = [manager.save_bookmark(b, "test") for b in bookmarks]
            await asyncio.gather(*tasks)

            # All should be saved
            assert len(manager.in_memory_index["test"]) == 10
