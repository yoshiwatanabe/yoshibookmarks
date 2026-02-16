"""Bookmark CRUD endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from ..core.bookmark_manager import BookmarkAlreadyDeletedError, BookmarkNotFoundError
from ..core.storage_manager import StorageError
from ..models.bookmark import Bookmark

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_storage_name(
    requested_storage: Optional[str],
    for_create: bool = False,
) -> Optional[str]:
    """Resolve effective storage based on runtime mode and request."""
    from . import runtime_config, storage_manager

    current_storage = storage_manager.get_current_storage_name()

    if runtime_config and runtime_config.storage_mode == "onedrive_only":
        if current_storage is None:
            raise HTTPException(status_code=500, detail="Primary OneDrive storage is not available")

        if requested_storage and requested_storage != current_storage:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"OneDrive-only mode is active. Use primary storage '{current_storage}' "
                    "or omit storage parameter."
                ),
            )
        return current_storage

    if requested_storage:
        return requested_storage

    if for_create:
        return current_storage

    return None


# Request/Response Models
class CreateBookmarkRequest(BaseModel):
    """Request model for creating a bookmark."""

    url: HttpUrl
    title: Optional[str] = None  # Auto-generated if not provided
    description: Optional[str] = None
    keywords: Optional[List[str]] = Field(None, max_length=4)
    tags: Optional[List[str]] = None
    folder_path: Optional[str] = None
    storage_location: Optional[str] = None  # Uses current if not provided


class UpdateBookmarkRequest(BaseModel):
    """Request model for updating a bookmark."""

    title: Optional[str] = None
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = Field(None, max_length=4)
    tags: Optional[List[str]] = None
    folder_path: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    details: Optional[dict] = None


# Endpoints
@router.post("/bookmarks", response_model=Bookmark, status_code=201)
async def create_bookmark(request: CreateBookmarkRequest):
    """Create a new bookmark.

    Automatically fetches webpage content and suggests title/keywords if not provided.
    """
    try:
        # Import managers dynamically
        from . import bookmark_manager, content_analyzer, storage_manager

        # Determine storage location
        storage_location = _resolve_storage_name(
            request.storage_location,
            for_create=True,
        )
        if not storage_location:
            raise HTTPException(status_code=500, detail="No writable storage configured")

        # Auto-generate title and keywords if not provided
        title = request.title
        keywords = request.keywords or []

        if not title or not keywords:
            # Analyze URL
            analysis = await content_analyzer.analyze_url(str(request.url))

            if not title:
                title = analysis["title"]

            if not keywords:
                keywords = analysis["keywords"]

        # Create bookmark
        bookmark = await bookmark_manager.create_bookmark(
            url=str(request.url),
            title=title,
            storage_location=storage_location,
            keywords=keywords,
            description=request.description,
            tags=request.tags,
            folder_path=request.folder_path,
        )

        return bookmark

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create bookmark: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.get("/bookmarks", response_model=dict)
async def list_bookmarks(
    storage: Optional[str] = Query(None, description="Storage location name"),
    include_deleted: bool = Query(False, description="Include soft-deleted bookmarks"),
    folder: Optional[str] = Query(None, description="Filter by folder path"),
):
    """List bookmarks with optional filters."""
    try:
        from . import bookmark_manager

        resolved_storage = _resolve_storage_name(storage)
        bookmarks = bookmark_manager.list_bookmarks(
            storage_name=resolved_storage,
            include_deleted=include_deleted,
            folder_path=folder,
        )

        return {
            "bookmarks": bookmarks,
            "total": len(bookmarks),
            "storage": resolved_storage or "all",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list bookmarks: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.get("/bookmarks/{bookmark_id}", response_model=Bookmark)
async def get_bookmark(
    bookmark_id: str,
    storage: Optional[str] = Query(None, description="Storage location name"),
):
    """Get a specific bookmark by ID."""
    try:
        from . import bookmark_manager

        resolved_storage = _resolve_storage_name(storage)
        bookmark = await bookmark_manager.get_bookmark(bookmark_id, resolved_storage)
        return bookmark

    except BookmarkNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bookmark {bookmark_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.put("/bookmarks/{bookmark_id}", response_model=Bookmark)
async def update_bookmark(
    bookmark_id: str,
    request: UpdateBookmarkRequest,
    storage: Optional[str] = Query(None, description="Storage location name"),
):
    """Update a bookmark."""
    try:
        from . import bookmark_manager

        resolved_storage = _resolve_storage_name(storage)
        bookmark = await bookmark_manager.update_bookmark(
            bookmark_id=bookmark_id,
            storage_name=resolved_storage,
            title=request.title,
            url=str(request.url) if request.url else None,
            description=request.description,
            keywords=request.keywords,
            tags=request.tags,
            folder_path=request.folder_path,
        )

        return bookmark

    except BookmarkNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update bookmark {bookmark_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.delete("/bookmarks/{bookmark_id}", response_model=Bookmark)
async def delete_bookmark(
    bookmark_id: str,
    hard: bool = Query(False, description="Perform hard delete (permanent)"),
    storage: Optional[str] = Query(None, description="Storage location name"),
):
    """Delete a bookmark (soft delete by default, hard delete if hard=true)."""
    try:
        from . import bookmark_manager

        resolved_storage = _resolve_storage_name(storage)

        if hard:
            # Get bookmark first to return it
            bookmark = await bookmark_manager.get_bookmark(bookmark_id, resolved_storage)

            # Hard delete
            await bookmark_manager.hard_delete_bookmark(bookmark_id, resolved_storage)

            # Return the bookmark that was deleted
            return bookmark
        else:
            # Soft delete
            bookmark = await bookmark_manager.delete_bookmark(bookmark_id, resolved_storage)
            return bookmark

    except BookmarkNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BookmarkAlreadyDeletedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        # Hard delete safety check failure
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete bookmark {bookmark_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/bookmarks/{bookmark_id}/restore", response_model=Bookmark)
async def restore_bookmark(
    bookmark_id: str,
    storage: Optional[str] = Query(None, description="Storage location name"),
):
    """Restore a soft-deleted bookmark."""
    try:
        from . import bookmark_manager

        resolved_storage = _resolve_storage_name(storage)
        bookmark = await bookmark_manager.restore_bookmark(bookmark_id, resolved_storage)
        return bookmark

    except BookmarkNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # Not deleted
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore bookmark {bookmark_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/bookmarks/{bookmark_id}/access", response_model=Bookmark)
async def track_bookmark_access(
    bookmark_id: str,
    storage: Optional[str] = Query(None, description="Storage location name"),
):
    """Track bookmark access (updates last_accessed timestamp)."""
    try:
        from . import bookmark_manager

        resolved_storage = _resolve_storage_name(storage)
        bookmark = await bookmark_manager.track_access(bookmark_id, resolved_storage)
        return bookmark

    except BookmarkNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track access for {bookmark_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
