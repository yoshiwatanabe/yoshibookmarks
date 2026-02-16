"""Bookmark manager for CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from ..models.bookmark import Bookmark
from .storage_manager import StorageError, StorageManager

logger = logging.getLogger(__name__)


class BookmarkNotFoundError(Exception):
    """Bookmark not found error."""

    pass


class BookmarkAlreadyDeletedError(Exception):
    """Bookmark already deleted error."""

    pass


class BookmarkManager:
    """Manages bookmark CRUD operations and business logic."""

    def __init__(self, storage_manager: StorageManager):
        """Initialize bookmark manager.

        Args:
            storage_manager: StorageManager instance
        """
        self.storage = storage_manager

    async def create_bookmark(
        self,
        url: str,
        title: str,
        storage_location: str,
        keywords: Optional[List[str]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        folder_path: Optional[str] = None,
    ) -> Bookmark:
        """Create a new bookmark.

        Args:
            url: URL to bookmark
            title: Bookmark title
            storage_location: Storage location name
            keywords: Optional keywords list
            description: Optional description
            tags: Optional tags list
            folder_path: Optional folder path

        Returns:
            Created Bookmark instance

        Raises:
            ValidationError: If bookmark data is invalid
            StorageError: If storage operation fails
        """
        # Create bookmark (Pydantic will validate)
        bookmark = Bookmark(
            id=str(uuid4()),
            url=url,
            title=title,
            keywords=keywords or [],
            description=description,
            tags=tags or [],
            folder_path=folder_path,
            created_at=datetime.now(timezone.utc),
            storage_location=storage_location,
        )

        # Save to storage
        await self.storage.save_bookmark(bookmark, storage_location)

        logger.info(f"Created bookmark {bookmark.id}: {bookmark.title}")

        return bookmark

    async def get_bookmark(self, bookmark_id: str, storage_name: Optional[str] = None) -> Bookmark:
        """Get bookmark by ID.

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Optional storage location name

        Returns:
            Bookmark instance

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
        """
        bookmark = self.storage.get_bookmark_by_id(bookmark_id, storage_name)

        if bookmark is None:
            raise BookmarkNotFoundError(f"Bookmark not found: {bookmark_id}")

        return bookmark

    async def update_bookmark(
        self,
        bookmark_id: str,
        storage_name: Optional[str] = None,
        title: Optional[str] = None,
        url: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        folder_path: Optional[str] = None,
    ) -> Bookmark:
        """Update bookmark fields.

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Optional storage location name
            title: Updated title
            url: Updated URL
            description: Updated description
            keywords: Updated keywords
            tags: Updated tags
            folder_path: Updated folder path

        Returns:
            Updated Bookmark instance

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
            ValidationError: If updated data is invalid
            StorageError: If storage operation fails
        """
        # Get existing bookmark
        bookmark = await self.get_bookmark(bookmark_id, storage_name)

        # Update fields (Pydantic will validate on model_copy)
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if url is not None:
            update_data["url"] = url
        if description is not None:
            update_data["description"] = description
        if keywords is not None:
            update_data["keywords"] = keywords
        if tags is not None:
            update_data["tags"] = tags
        if folder_path is not None:
            update_data["folder_path"] = folder_path

        # Set last modified timestamp
        update_data["last_modified"] = datetime.now(timezone.utc)

        # Create updated bookmark
        updated_bookmark = bookmark.model_copy(update=update_data)

        # Save to storage
        await self.storage.save_bookmark(updated_bookmark, updated_bookmark.storage_location)

        logger.info(f"Updated bookmark {bookmark_id}")

        return updated_bookmark

    async def delete_bookmark(self, bookmark_id: str, storage_name: Optional[str] = None) -> Bookmark:
        """Soft delete a bookmark.

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Optional storage location name

        Returns:
            Soft-deleted Bookmark instance

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
            BookmarkAlreadyDeletedError: If bookmark is already deleted
            StorageError: If storage operation fails
        """
        # Get existing bookmark
        bookmark = await self.get_bookmark(bookmark_id, storage_name)

        if bookmark.deleted:
            raise BookmarkAlreadyDeletedError(f"Bookmark {bookmark_id} is already deleted")

        # Mark as deleted
        deleted_bookmark = bookmark.model_copy(
            update={
                "deleted": True,
                "deleted_at": datetime.now(timezone.utc),
            }
        )

        # Save to storage
        await self.storage.save_bookmark(deleted_bookmark, deleted_bookmark.storage_location)

        logger.info(f"Soft deleted bookmark {bookmark_id}")

        return deleted_bookmark

    async def restore_bookmark(self, bookmark_id: str, storage_name: Optional[str] = None) -> Bookmark:
        """Restore a soft-deleted bookmark.

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Optional storage location name

        Returns:
            Restored Bookmark instance

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
            ValueError: If bookmark is not deleted
            StorageError: If storage operation fails
        """
        # Get existing bookmark
        bookmark = await self.get_bookmark(bookmark_id, storage_name)

        if not bookmark.deleted:
            raise ValueError(f"Bookmark {bookmark_id} is not deleted")

        # Restore bookmark
        restored_bookmark = bookmark.model_copy(
            update={
                "deleted": False,
                "deleted_at": None,
            }
        )

        # Save to storage
        await self.storage.save_bookmark(restored_bookmark, restored_bookmark.storage_location)

        logger.info(f"Restored bookmark {bookmark_id}")

        return restored_bookmark

    async def hard_delete_bookmark(
        self, bookmark_id: str, storage_name: Optional[str] = None
    ) -> None:
        """Permanently delete a bookmark (hard delete).

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Optional storage location name

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
            ValueError: If bookmark is not soft-deleted (safety check)
            StorageError: If storage operation fails
        """
        # Get existing bookmark
        bookmark = await self.get_bookmark(bookmark_id, storage_name)

        # Safety check: must be soft-deleted first
        if not bookmark.deleted:
            raise ValueError(
                f"Bookmark {bookmark_id} must be soft-deleted before hard delete. "
                "This is a safety measure to prevent accidental data loss."
            )

        # Permanently delete file
        await self.storage.delete_bookmark_file(bookmark_id, bookmark.storage_location)

        logger.warning(f"Hard deleted bookmark {bookmark_id} permanently")

    async def track_access(self, bookmark_id: str, storage_name: Optional[str] = None) -> Bookmark:
        """Update last accessed timestamp for a bookmark.

        Args:
            bookmark_id: Bookmark UUID
            storage_name: Optional storage location name

        Returns:
            Updated Bookmark instance

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
            StorageError: If storage operation fails
        """
        # Get existing bookmark
        bookmark = await self.get_bookmark(bookmark_id, storage_name)

        # Update last accessed
        accessed_bookmark = bookmark.model_copy(
            update={
                "last_accessed": datetime.now(timezone.utc),
            }
        )

        # Save to storage
        await self.storage.save_bookmark(accessed_bookmark, accessed_bookmark.storage_location)

        logger.debug(f"Tracked access for bookmark {bookmark_id}")

        return accessed_bookmark

    def list_bookmarks(
        self,
        storage_name: Optional[str] = None,
        include_deleted: bool = False,
        folder_path: Optional[str] = None,
    ) -> List[Bookmark]:
        """List bookmarks with filters.

        Args:
            storage_name: Optional storage location name (None = all)
            include_deleted: Include soft-deleted bookmarks
            folder_path: Filter by folder path

        Returns:
            List of bookmarks matching filters
        """
        return self.storage.get_bookmarks(
            storage_name=storage_name,
            include_deleted=include_deleted,
            folder_path=folder_path,
        )
