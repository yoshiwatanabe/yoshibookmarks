"""Storage manager for file operations and in-memory indexing."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ..models.bookmark import Bookmark
from ..models.storage import StorageLocation
from ..utils.file_lock import FileLocker, FileLockError
from ..utils.yaml_handler import YAMLError, load_bookmark_from_file, save_bookmark_to_file

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Storage-related error."""

    pass


class StorageManager:
    """Manages file I/O, indexing, and multi-storage for bookmarks."""

    def __init__(self):
        """Initialize storage manager."""
        self.storage_locations: Dict[str, StorageLocation] = {}
        self.in_memory_index: Dict[str, Dict[str, Bookmark]] = {}
        self.load_errors: Dict[str, List[str]] = {}  # {storage_name: [error_messages]}
        self.conflicts: Dict[str, List[str]] = {}  # {storage_name: [conflict_messages]}
        self.current_storage_name: Optional[str] = None

    async def initialize(self, storage_locations: List[StorageLocation]) -> None:
        """Initialize storage manager with storage locations.

        Args:
            storage_locations: List of configured storage locations

        Raises:
            StorageError: If initialization fails
        """
        for storage in storage_locations:
            try:
                self._validate_storage_location(storage)
                self.storage_locations[storage.name] = storage
                await self.load_storage(storage.name)
            except StorageError as e:
                logger.error(f"Failed to initialize storage {storage.name}: {e}")
                raise

        self.current_storage_name = self._select_current_storage_name()

    def _validate_storage_location(self, storage: StorageLocation) -> None:
        """Validate storage location is accessible.

        Args:
            storage: StorageLocation to validate

        Raises:
            StorageError: If storage is not accessible
        """
        path = Path(storage.path)

        if not path.exists():
            raise StorageError(f"Storage path does not exist: {storage.path}")

        if not path.is_dir():
            raise StorageError(f"Storage path is not a directory: {storage.path}")

        # Check permissions
        try:
            test_file = path / ".yoshibookmark_test"
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            raise StorageError(f"Cannot access storage: Permission denied for {storage.path}")
        except Exception as e:
            raise StorageError(f"Cannot access storage {storage.path}: {e}")

    async def load_storage(self, storage_name: str) -> None:
        """Load all bookmarks from a storage location into memory.

        Args:
            storage_name: Name of storage location to load

        Raises:
            StorageError: If storage doesn't exist or loading fails critically
        """
        if storage_name not in self.storage_locations:
            raise StorageError(f"Storage not found: {storage_name}")

        storage = self.storage_locations[storage_name]
        bookmarks_path = Path(storage.path) / "bookmarks"

        # Create directory structure if it doesn't exist
        self._ensure_storage_structure(Path(storage.path))

        # Initialize index for this storage
        self.in_memory_index[storage_name] = {}
        self.load_errors[storage_name] = []
        self.conflicts[storage_name] = []

        if not bookmarks_path.exists():
            logger.info(f"No bookmarks directory in {storage_name}, created empty")
            return

        # Load all YAML files
        yaml_files = list(bookmarks_path.glob("*.yaml"))
        logger.info(f"Loading {len(yaml_files)} bookmarks from {storage_name}")

        bookmark_sources: Dict[str, Path] = {}
        for yaml_file in yaml_files:
            try:
                bookmark = await asyncio.to_thread(load_bookmark_from_file, yaml_file)

                # Check for duplicate ID
                if bookmark.id in self.in_memory_index[storage_name]:
                    existing = self.in_memory_index[storage_name][bookmark.id]
                    existing_path = bookmark_sources.get(bookmark.id, yaml_file)
                    conflict_msg = (
                        f"Conflict for bookmark ID {bookmark.id}: "
                        f"{existing_path.name} vs {yaml_file.name}"
                    )
                    winner = self._choose_winner(existing, existing_path, bookmark, yaml_file)
                    self.in_memory_index[storage_name][bookmark.id] = winner
                    bookmark_sources[bookmark.id] = (
                        yaml_file if winner is bookmark else existing_path
                    )
                    self.conflicts[storage_name].append(conflict_msg)
                    logger.warning(conflict_msg)
                    continue

                self.in_memory_index[storage_name][bookmark.id] = bookmark
                bookmark_sources[bookmark.id] = yaml_file

            except YAMLError as e:
                # Log and skip corrupted files
                error_msg = f"Corrupted YAML in {yaml_file.name}: {e}"
                logger.warning(error_msg)
                self.load_errors[storage_name].append(error_msg)
                continue
            except Exception as e:
                # Log unexpected errors but continue
                error_msg = f"Failed to load {yaml_file.name}: {e}"
                logger.error(error_msg)
                self.load_errors[storage_name].append(error_msg)
                continue

        logger.info(
            f"Loaded {len(self.in_memory_index[storage_name])} bookmarks from {storage_name} "
            f"({len(self.load_errors[storage_name])} errors, "
            f"{len(self.conflicts[storage_name])} conflicts)"
        )

    def _ensure_storage_structure(self, storage_path: Path) -> None:
        """Ensure storage directory structure exists.

        Args:
            storage_path: Path to storage root

        Raises:
            StorageError: If directory creation fails
        """
        try:
            (storage_path / "bookmarks").mkdir(parents=True, exist_ok=True)
            (storage_path / "favicons").mkdir(parents=True, exist_ok=True)
            (storage_path / "screenshots").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageError(f"Failed to create storage structure: {e}") from e

    async def save_bookmark(self, bookmark: Bookmark, storage_name: str) -> None:
        """Save bookmark to YAML file with file locking.

        Args:
            bookmark: Bookmark instance to save
            storage_name: Storage location name

        Raises:
            StorageError: If storage doesn't exist or save fails
            FileLockError: If file lock cannot be acquired
        """
        if storage_name not in self.storage_locations:
            raise StorageError(f"Storage not found: {storage_name}")

        storage = self.storage_locations[storage_name]
        file_path = Path(storage.path) / "bookmarks" / f"{bookmark.id}.yaml"

        try:
            # Acquire file lock
            async with FileLocker(file_path):
                # Save to file
                await asyncio.to_thread(save_bookmark_to_file, bookmark, file_path)

            # Update in-memory index
            if storage_name not in self.in_memory_index:
                self.in_memory_index[storage_name] = {}

            self.in_memory_index[storage_name][bookmark.id] = bookmark

        except FileLockError as e:
            raise StorageError(f"Could not acquire lock for {bookmark.id}: {e}") from e
        except YAMLError as e:
            raise StorageError(f"Failed to save bookmark {bookmark.id}: {e}") from e
        except Exception as e:
            raise StorageError(f"Unexpected error saving {bookmark.id}: {e}") from e

    def get_bookmarks(
        self,
        storage_name: Optional[str] = None,
        include_deleted: bool = False,
        folder_path: Optional[str] = None,
    ) -> List[Bookmark]:
        """Get bookmarks from in-memory index with filters.

        Args:
            storage_name: Storage location name (None = all storages)
            include_deleted: Include soft-deleted bookmarks
            folder_path: Filter by folder path

        Returns:
            List of bookmarks matching filters
        """
        bookmarks = []

        if storage_name:
            # Single storage
            if storage_name in self.in_memory_index:
                bookmarks = list(self.in_memory_index[storage_name].values())
        else:
            # All storages (Global view)
            for storage_bookmarks in self.in_memory_index.values():
                bookmarks.extend(storage_bookmarks.values())

        # Apply filters
        if not include_deleted:
            bookmarks = [b for b in bookmarks if not b.deleted]

        if folder_path is not None:
            bookmarks = [b for b in bookmarks if b.folder_path == folder_path]

        return bookmarks

    def get_bookmark_by_id(
        self, bookmark_id: str, storage_name: Optional[str] = None
    ) -> Optional[Bookmark]:
        """Get bookmark by ID.

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Storage location name (None = search all)

        Returns:
            Bookmark if found, None otherwise
        """
        if storage_name:
            # Search specific storage
            return self.in_memory_index.get(storage_name, {}).get(bookmark_id)
        else:
            # Search all storages
            for storage_bookmarks in self.in_memory_index.values():
                if bookmark_id in storage_bookmarks:
                    return storage_bookmarks[bookmark_id]
            return None

    async def delete_bookmark_file(self, bookmark_id: str, storage_name: str) -> None:
        """Permanently delete bookmark file (hard delete).

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Storage location name

        Raises:
            StorageError: If deletion fails
        """
        if storage_name not in self.storage_locations:
            raise StorageError(f"Storage not found: {storage_name}")

        storage = self.storage_locations[storage_name]
        file_path = Path(storage.path) / "bookmarks" / f"{bookmark_id}.yaml"

        try:
            if file_path.exists():
                await asyncio.to_thread(file_path.unlink)

            # Remove from in-memory index
            if storage_name in self.in_memory_index:
                self.in_memory_index[storage_name].pop(bookmark_id, None)

        except Exception as e:
            raise StorageError(f"Failed to delete bookmark file {bookmark_id}: {e}") from e

    def get_storage_stats(self, storage_name: str) -> Dict[str, int]:
        """Get statistics for a storage location.

        Args:
            storage_name: Storage location name

        Returns:
            Dictionary with stats (total, active, deleted)

        Raises:
            StorageError: If storage doesn't exist
        """
        if storage_name not in self.in_memory_index:
            raise StorageError(f"Storage not found: {storage_name}")

        bookmarks = self.in_memory_index[storage_name].values()

        total = len(bookmarks)
        deleted = sum(1 for b in bookmarks if b.deleted)
        active = total - deleted

        return {
            "total": total,
            "active": active,
            "deleted": deleted,
            "errors": len(self.load_errors.get(storage_name, [])),
            "conflicts": len(self.conflicts.get(storage_name, [])),
        }

    def get_all_storage_names(self) -> List[str]:
        """Get list of all configured storage names.

        Returns:
            List of storage names
        """
        return list(self.storage_locations.keys())

    def get_current_storage_name(self) -> Optional[str]:
        """Get the currently active storage name."""
        if self.current_storage_name and self.current_storage_name in self.storage_locations:
            return self.current_storage_name
        self.current_storage_name = self._select_current_storage_name()
        return self.current_storage_name

    def get_recent_conflicts(self, limit: int = 20) -> List[str]:
        """Return recent conflict warnings across all storages."""
        merged: List[str] = []
        for storage_name, messages in self.conflicts.items():
            for message in messages:
                merged.append(f"[{storage_name}] {message}")
        return merged[-limit:]

    def _select_current_storage_name(self) -> Optional[str]:
        """Resolve current storage from configured storage metadata."""
        for storage in self.storage_locations.values():
            if storage.is_current:
                return storage.name
        if self.storage_locations:
            return next(iter(self.storage_locations.keys()))
        return None

    def _choose_winner(
        self,
        existing: Bookmark,
        existing_path: Path,
        candidate: Bookmark,
        candidate_path: Path,
    ) -> Bookmark:
        """Resolve duplicate bookmark conflicts using last-writer-wins semantics."""
        existing_ts = self._bookmark_timestamp(existing, existing_path)
        candidate_ts = self._bookmark_timestamp(candidate, candidate_path)
        return candidate if candidate_ts >= existing_ts else existing

    def _bookmark_timestamp(self, bookmark: Bookmark, source_path: Path) -> datetime:
        """Pick best available timestamp for conflict resolution."""
        if bookmark.last_modified:
            return bookmark.last_modified.astimezone(timezone.utc)
        if bookmark.created_at:
            return bookmark.created_at.astimezone(timezone.utc)
        try:
            mtime = source_path.stat().st_mtime
            return datetime.fromtimestamp(mtime, tz=timezone.utc)
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
