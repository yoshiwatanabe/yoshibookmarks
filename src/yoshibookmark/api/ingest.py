"""Ingestion endpoints for browser-extension capture workflows."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestPreviewRequest(BaseModel):
    """Request payload for ingestion preview."""

    url: HttpUrl
    page_title: Optional[str] = None
    page_excerpt: Optional[str] = None
    selected_text: Optional[str] = None
    user_note: Optional[str] = None
    storage_location: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_path: Optional[str] = None
    source_app: Optional[str] = None
    source_project: Optional[str] = None


class IngestCommitRequest(BaseModel):
    """Commit payload from a previously generated preview."""

    preview_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = Field(None, max_length=4)
    tags: Optional[List[str]] = None
    folder_path: Optional[str] = None


class IngestQuickSaveRequest(BaseModel):
    """Quick-save request payload."""

    url: HttpUrl
    page_title: Optional[str] = None
    page_excerpt: Optional[str] = None
    selected_text: Optional[str] = None
    user_note: Optional[str] = None
    storage_location: Optional[str] = None
    source_app: Optional[str] = None
    source_project: Optional[str] = None


def _resolve_storage_name(requested_storage: Optional[str]) -> str:
    from . import runtime_config, storage_manager

    current_storage = storage_manager.get_current_storage_name()
    if current_storage is None:
        raise HTTPException(status_code=500, detail="No writable storage configured")

    if runtime_config and runtime_config.storage_mode == "onedrive_only":
        if requested_storage and requested_storage != current_storage:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"OneDrive-only mode is active. Use primary storage '{current_storage}' "
                    "or omit storage parameter."
                ),
            )
        return current_storage

    return requested_storage or current_storage


def _require_extension_auth(
    authorization: Optional[str],
    x_extension_token: Optional[str],
) -> None:
    from . import runtime_config, runtime_env_settings

    if runtime_config and not runtime_config.ingest_require_auth:
        return

    expected = runtime_env_settings.extension_api_token if runtime_env_settings else None
    if not expected:
        raise HTTPException(status_code=503, detail="Ingestion auth token is not configured")

    presented = x_extension_token
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:]

    if not presented or presented != expected:
        raise HTTPException(status_code=401, detail="Invalid ingestion token")


@router.post("/ingest/preview", response_model=dict)
async def ingest_preview(
    request: IngestPreviewRequest,
    authorization: Optional[str] = Header(default=None),
    x_extension_token: Optional[str] = Header(default=None),
):
    """Create metadata suggestions from capture context without persisting bookmark."""
    try:
        from . import ingestion_service

        _require_extension_auth(authorization, x_extension_token)
        storage = _resolve_storage_name(request.storage_location)
        preview = await ingestion_service.create_preview(
            payload=request.model_dump(mode="json"),
            storage_location=storage,
        )
        return preview
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create ingest preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create preview: {e}")


@router.post("/ingest/commit", response_model=dict)
async def ingest_commit(
    request: IngestCommitRequest,
    authorization: Optional[str] = Header(default=None),
    x_extension_token: Optional[str] = Header(default=None),
):
    """Commit a previously generated preview into bookmark storage."""
    try:
        from . import ingestion_service

        _require_extension_auth(authorization, x_extension_token)
        bookmark = await ingestion_service.commit_preview(
            preview_id=request.preview_id,
            final_data=request.model_dump(mode="json"),
        )
        return {"bookmark": bookmark, "status": "committed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to commit ingest preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to commit preview: {e}")


@router.post("/ingest/quick-save", response_model=dict)
async def ingest_quick_save(
    request: IngestQuickSaveRequest,
    authorization: Optional[str] = Header(default=None),
    x_extension_token: Optional[str] = Header(default=None),
):
    """Save a bookmark immediately from capture context."""
    try:
        from . import ingestion_service

        _require_extension_auth(authorization, x_extension_token)
        storage = _resolve_storage_name(request.storage_location)
        bookmark = await ingestion_service.quick_save(
            payload=request.model_dump(mode="json"),
            storage_location=storage,
        )
        return {"bookmark": bookmark, "status": "saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to quick-save ingest capture: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to quick-save: {e}")


@router.get("/ingest/providers/status", response_model=dict)
async def ingest_provider_status():
    """Get ingestion provider chain status."""
    try:
        from . import ingestion_service

        return {"providers": ingestion_service.get_provider_status()}
    except Exception as e:
        logger.error(f"Failed to fetch ingest provider status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch provider status: {e}")


@router.get("/ingest/preview/{preview_id}/diagnostics", response_model=dict)
async def ingest_preview_diagnostics(preview_id: str):
    """Get provider trace for a preview id."""
    try:
        from . import ingestion_service

        return {"preview_id": preview_id, "provider_trace": ingestion_service.get_preview_trace(preview_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch preview diagnostics: {e}")
        raise HTTPException(status_code=404, detail=f"Diagnostics unavailable: {e}")
