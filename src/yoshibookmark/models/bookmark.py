"""Bookmark data model."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Bookmark(BaseModel):
    """Core bookmark data structure matching DESIGN.md specification."""

    # Required fields
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier (UUID)",
    )
    url: HttpUrl = Field(..., description="The bookmarked URL")
    title: str = Field(..., min_length=1, max_length=500, description="Bookmark title")
    keywords: List[str] = Field(
        default_factory=list,
        max_length=4,
        description="Ordered list of keywords (priority order, max 4)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When bookmark was created",
    )

    # Optional fields
    description: Optional[str] = Field(
        None, max_length=5000, description="User notes and description"
    )
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    folder_path: Optional[str] = Field(
        None, description="Folder hierarchy path (e.g., development/python)"
    )
    last_modified: Optional[datetime] = Field(None, description="Last edit timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last accessed timestamp")

    # Soft delete fields
    deleted: bool = Field(default=False, description="Soft delete flag")
    deleted_at: Optional[datetime] = Field(None, description="When bookmark was deleted")

    # Asset references
    favicon_path: Optional[str] = Field(
        None, description="Relative path to favicon (e.g., favicons/example.com.ico)"
    )
    screenshot_path: Optional[str] = Field(
        None, description="Relative path to screenshot (e.g., screenshots/{id}.png)"
    )

    # Metadata
    storage_location: str = Field(..., description="Which storage this belongs to")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "url": "https://github.com/python/cpython",
                "title": "CPython Official Repository",
                "keywords": ["python", "cpython", "github"],
                "description": "Official Python implementation source code",
                "tags": ["programming", "open-source"],
                "folder_path": "development/python",
                "created_at": "2026-02-03T10:30:00Z",
                "storage_location": "work",
            }
        }
    )

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        """Validate keywords list."""
        if len(v) > 4:
            raise ValueError("Maximum 4 keywords allowed")

        # Filter empty keywords
        keywords = [k.strip() for k in v if k.strip()]

        return keywords

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty or whitespace."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")

        return v.strip()

    @field_validator("folder_path")
    @classmethod
    def validate_folder_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate folder path doesn't contain dangerous characters."""
        if v is None:
            return None

        # Prevent directory traversal
        if ".." in v or v.startswith("/") or v.startswith("\\"):
            raise ValueError(
                "Folder path cannot contain '..' or start with / or \\ (directory traversal)"
            )

        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and clean tags."""
        # Filter empty tags
        tags = [t.strip() for t in v if t.strip()]

        return tags
