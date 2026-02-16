"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    # Read live globals from api module at request time.
    from yoshibookmark import api

    try:
        storage_accessible = len(api.storage_manager.storage_locations) > 0
        conflict_count = sum(len(v) for v in api.storage_manager.conflicts.values())
        current_storage = api.storage_manager.get_current_storage_name()
    except Exception:
        storage_accessible = False
        conflict_count = 0
        current_storage = None

    storage_mode = api.runtime_config.storage_mode if api.runtime_config else "unknown"
    primary_provider = (
        api.runtime_config.primary_storage_provider if api.runtime_config else "unknown"
    )
    primary_path = api.runtime_config.primary_storage_path if api.runtime_config else None

    return {
        "status": "healthy" if storage_accessible else "degraded",
        "version": "0.1.0",
        "storage_accessible": storage_accessible,
        "storage_count": len(api.storage_manager.storage_locations) if storage_accessible else 0,
        "current_storage": current_storage,
        "storage_mode": storage_mode,
        "primary_storage_provider": primary_provider,
        "primary_storage_path": primary_path,
        "conflict_count": conflict_count,
        "recent_conflicts": api.storage_manager.get_recent_conflicts(limit=10)
        if storage_accessible
        else [],
    }
