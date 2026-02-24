"""FastAPI application and routes."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..config import ConfigManager
from ..core.ai_inference import MultiProviderInferenceService
from ..core.bookmark_manager import BookmarkManager
from ..core.content_analyzer import ContentAnalyzer
from ..core.ingestion_service import IngestionService
from ..core.recall_service import RecallService
from ..core.storage_manager import StorageManager
from ..models.config import AppConfig, EnvSettings

logger = logging.getLogger(__name__)

# Global state (will be initialized in lifespan)
storage_manager: StorageManager = None
bookmark_manager: BookmarkManager = None
content_analyzer: ContentAnalyzer = None
config_manager: ConfigManager = None
runtime_config: AppConfig = None
runtime_env_settings: EnvSettings = None
ingestion_service: IngestionService = None
recall_service: RecallService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global storage_manager, bookmark_manager, content_analyzer
    global config_manager, runtime_config, runtime_env_settings, ingestion_service, recall_service

    # Startup
    logger.info("Starting YoshiBookmark API...")

    # Load configuration
    config_manager = ConfigManager()
    try:
        app_config = config_manager.load_app_config()
        env_settings = config_manager.load_env_settings()
        runtime_config = app_config
        runtime_env_settings = env_settings
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

    # Seed provider key arrays from env settings for compatibility.
    if env_settings.openai_api_key and not app_config.openai_api_keys:
        app_config.openai_api_keys = [env_settings.openai_api_key]
    if env_settings.azure_openai_api_key and not app_config.azure_openai_api_keys:
        app_config.azure_openai_api_keys = [env_settings.azure_openai_api_key]
    if env_settings.anthropic_api_key and not app_config.anthropic_api_keys:
        app_config.anthropic_api_keys = [env_settings.anthropic_api_key]
    if env_settings.google_api_key and not app_config.gemini_api_keys:
        app_config.gemini_api_keys = [env_settings.google_api_key]

    # Initialize storage manager
    storage_manager = StorageManager()
    await storage_manager.initialize(app_config.storage_locations)

    # Initialize bookmark manager
    bookmark_manager = BookmarkManager(storage_manager)

    # Initialize content analyzer
    content_analyzer = ContentAnalyzer(timeout=app_config.screenshot_timeout)
    inference_service = MultiProviderInferenceService(app_config)
    ingestion_service = IngestionService(
        config=app_config,
        bookmark_manager=bookmark_manager,
        storage_manager=storage_manager,
        content_analyzer=content_analyzer,
        inference_service=inference_service,
    )
    recall_service = RecallService(
        config=app_config,
        storage_manager=storage_manager,
        env_settings=env_settings,
    )

    logger.info(
        f"Initialized with {len(storage_manager.storage_locations)} storage location(s)"
    )

    yield

    # Shutdown
    logger.info("Shutting down YoshiBookmark API...")


# Create FastAPI app
app = FastAPI(
    title="YoshiBookmark API",
    description="URL and bookmark management system with intelligent search",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
cors_origins: list[str] = []
try:
    boot_cfg = ConfigManager().load_app_config()
    cors_origins.extend(boot_cfg.extension_allowed_origins)
except Exception:
    # Keep startup robust when config is not available in test/import contexts.
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent.parent / "web" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Import and include routers
from .bookmarks import router as bookmarks_router
from .health import router as health_router
from .ingest import router as ingest_router
from .recall import router as recall_router

app.include_router(bookmarks_router, prefix="/api/v1", tags=["bookmarks"])
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(ingest_router, prefix="/api/v1", tags=["ingest"])
app.include_router(recall_router, prefix="/api/v1", tags=["recall"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "YoshiBookmark API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "app": "/app",
    }


@app.get("/app")
async def web_app():
    """Serve web application shell."""
    return FileResponse(static_dir / "index.html")
