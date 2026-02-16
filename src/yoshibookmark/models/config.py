"""Configuration models."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .storage import StorageLocation


class EnvSettings(BaseSettings):
    """Settings loaded from .env file (secrets and credentials)."""

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_api_base: Optional[str] = Field(
        None, description="Custom API endpoint (e.g., Azure)"
    )
    openai_api_type: str = Field(default="openai", description="API type: openai or azure")
    openai_api_version: Optional[str] = Field(None, description="API version for Azure")

    # Azure OpenAI (if using Azure)
    azure_openai_endpoint: Optional[str] = Field(None, description="Azure OpenAI endpoint")
    azure_openai_deployment_name: Optional[str] = Field(
        None, description="Azure deployment name"
    )
    azure_openai_api_key: Optional[str] = Field(None, description="Azure OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(None, description="Google API key for Gemini")

    # Extension/API auth
    extension_api_token: Optional[str] = Field(
        None, description="Bearer token accepted by ingestion endpoints"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AppConfig(BaseModel):
    """Application configuration from config.yaml."""

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: Optional[int] = Field(None, description="Server port (auto-select if None)")

    # Storage locations
    storage_locations: List[StorageLocation] = Field(
        default_factory=list, description="Configured storage locations"
    )
    storage_mode: Literal["multi", "onedrive_only"] = Field(
        default="multi",
        description="Storage behavior mode. 'onedrive_only' enforces one active OneDrive-backed storage.",
    )
    primary_storage_provider: Literal["filesystem", "onedrive_local"] = Field(
        default="filesystem",
        description="Primary storage provider type.",
    )
    primary_storage_path: Optional[str] = Field(
        None,
        description="Absolute path for primary storage location (required for onedrive_only mode).",
    )
    legacy_storage_readonly: bool = Field(
        default=False,
        description="When true, legacy pre-migration storages are read-only references.",
    )

    # Feature flags
    enable_semantic_search: bool = Field(
        default=True, description="Enable semantic search with embeddings"
    )
    enable_screenshots: bool = Field(default=True, description="Enable screenshot capture")
    screenshot_timeout: int = Field(
        default=10, description="Screenshot capture timeout in seconds", ge=1, le=60
    )

    # OpenAI model selection
    embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )
    content_analysis_model: str = Field(
        default="gpt-4o-mini", description="OpenAI model for content analysis"
    )

    # Cache settings
    cache_embeddings: bool = Field(default=True, description="Cache embeddings in memory")
    max_cache_size_mb: int = Field(
        default=100, description="Maximum cache size in MB", ge=10, le=1000
    )

    # Recall settings
    recall_default_limit: int = Field(default=20, ge=1, le=100)
    recall_max_limit: int = Field(default=50, ge=1, le=200)
    recall_semantic_weight: float = Field(default=0.55, ge=0.0, le=1.0)
    recall_keyword_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    recall_query_timeout_ms: int = Field(default=1200, ge=100, le=10000)

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    extension_allowed_origins: List[str] = Field(
        default_factory=list,
        description="Allowed browser extension origins (e.g., chrome-extension://<id>)",
    )
    ingest_require_auth: bool = Field(
        default=True,
        description="Require auth token for ingestion endpoints",
    )
    ingest_preview_ttl_seconds: int = Field(
        default=900,
        ge=60,
        le=86400,
        description="TTL for preview sessions before commit",
    )

    # Agent provider chain config
    agent_providers: List[str] = Field(
        default_factory=lambda: ["openai", "azureopenai", "anthropic", "gemini"],
        description="Ordered provider IDs for AI inference failover",
    )
    agent_default_model: str = Field(
        default="gpt-5-mini",
        description="Primary/default model label for diagnostics and prompts",
    )
    agent_timeout_seconds: int = Field(default=20, ge=5, le=120)
    agent_confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)

    openai_enabled: bool = Field(default=True)
    openai_endpoint: str = Field(default="https://api.openai.com/v1/chat/completions")
    openai_model: str = Field(default="gpt-5-mini")
    openai_api_keys: List[str] = Field(default_factory=list)

    azure_openai_enabled: bool = Field(default=True)
    azure_openai_endpoint: str = Field(default="")
    azure_openai_model: str = Field(default="model-router")
    azure_openai_api_keys: List[str] = Field(default_factory=list)

    anthropic_enabled: bool = Field(default=True)
    anthropic_endpoint: str = Field(default="https://api.anthropic.com/v1/messages")
    anthropic_model: str = Field(default="claude-3-5-haiku-latest")
    anthropic_api_keys: List[str] = Field(default_factory=list)

    gemini_enabled: bool = Field(default=True)
    gemini_endpoint: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )
    gemini_model: str = Field(default="gemini-2.0-flash")
    gemini_api_keys: List[str] = Field(default_factory=list)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "host": "127.0.0.1",
            "port": 8080,
            "storage_locations": [
                {
                    "name": "default",
                    "path": "/home/user/.yoshibookmark/storage/default",
                    "is_current": True,
                    "is_default": True,
                }
            ],
            "storage_mode": "multi",
            "primary_storage_provider": "filesystem",
            "primary_storage_path": "/home/user/.yoshibookmark/storage/default",
            "legacy_storage_readonly": False,
            "enable_semantic_search": True,
            "enable_screenshots": True,
            "embedding_model": "text-embedding-3-small",
            "content_analysis_model": "gpt-4o-mini",
            "extension_allowed_origins": ["chrome-extension://your-extension-id"],
            "ingest_require_auth": True,
            "agent_providers": ["openai", "azureopenai", "anthropic", "gemini"],
            "agent_default_model": "gpt-5-mini",
        }
    })
