"""Recall endpoints for natural-language retrieval."""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class RecallQueryRequest(BaseModel):
    """Request payload for recall query."""

    query: str = Field(..., min_length=1, max_length=2000)
    limit: Optional[int] = Field(default=None, ge=1, le=50)
    scope: Literal["all", "current"] = "all"


@router.post("/recall/query", response_model=dict)
async def recall_query(request: RecallQueryRequest):
    """Recall bookmarks from natural-language query."""
    try:
        from . import recall_service, storage_manager

        current_storage = storage_manager.get_current_storage_name()
        return await recall_service.query(
            query_text=request.query,
            limit=request.limit,
            scope=request.scope,
            current_storage=current_storage,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recall failed: {e}")
