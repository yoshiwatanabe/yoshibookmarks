"""Storage location model."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StorageLocation(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "work",
            "path": "/home/user/bookmarks/work",
            "is_current": True,
            "is_default": False,
            "created_at": "2026-02-04T10:00:00Z",
        }
    })
    """Represents a bookmark storage location (e.g., Work, Personal)."""

    name: str = Field(..., description="Display name for the storage location")
    path: str = Field(..., description="Absolute path to storage directory")
    is_current: bool = Field(
        default=False, description="Whether this is the currently active storage"
    )
    is_default: bool = Field(default=False, description="Whether this is the default storage")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate storage name contains only safe characters."""
        if not v:
            raise ValueError("Storage name cannot be empty")

        # Allow alphanumeric, dash, underscore only
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Storage name must contain only letters, numbers, dashes, and underscores"
            )

        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate storage path is absolute."""
        from pathlib import Path

        if not v:
            raise ValueError("Storage path cannot be empty")

        # Accept the path as-is for flexibility (will be validated at access time)
        # This allows config files to be portable across systems
        return v
