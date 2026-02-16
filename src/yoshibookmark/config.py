"""Configuration management."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from .models.config import AppConfig, EnvSettings
from .models.storage import StorageLocation


class ConfigError(Exception):
    """Configuration-related error."""

    pass


class ConfigManager:
    """Manages application configuration from .env and config.yaml."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Configuration directory path. Defaults to ~/.yoshibookmark
        """
        if config_dir is None:
            env_config_dir = os.environ.get("YOSHIBOOKMARK_CONFIG_DIR")
            if env_config_dir:
                config_dir = Path(env_config_dir)
            else:
                config_dir = Path.home() / '.yoshibookmark'

        self.config_dir = config_dir
        self.config_file = config_dir / 'config.yaml'
        self.env_file = config_dir / '.env'

    def load_env_settings(self) -> EnvSettings:
        """Load environment settings from .env file.

        Returns:
            EnvSettings instance

        Raises:
            ConfigError: If .env file is missing or invalid
        """
        if not self.env_file.exists():
            raise ConfigError(
                f".env file not found at {self.env_file}. "
                f"Run 'yoshibookmark init' to create configuration."
            )

        # Load .env file
        load_dotenv(self.env_file)

        try:
            return EnvSettings()
        except Exception as e:
            raise ConfigError(f"Invalid .env file: {e}") from e

    def load_app_config(self) -> AppConfig:
        """Load application configuration from config.yaml.

        Returns:
            AppConfig instance

        Raises:
            ConfigError: If config file is missing or invalid
        """
        if not self.config_file.exists():
            raise ConfigError(
                f"Config file not found at {self.config_file}. "
                f"Run 'yoshibookmark init' to create configuration."
            )

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data is None:
                data = {}

            config = AppConfig(**data)
            return self._normalize_storage_config(config)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}") from e
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}") from e

    def save_app_config(self, config: AppConfig) -> None:
        """Save application configuration to config.yaml.

        Args:
            config: AppConfig instance to save

        Raises:
            ConfigError: If save fails
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Normalize before saving so config remains consistent across versions.
            normalized = self._normalize_storage_config(config)

            # Convert to dict, handling Pydantic models
            data = normalized.model_dump(mode='json')

            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            raise ConfigError(f"Failed to save config: {e}") from e

    def create_env_file(
        self,
        api_key: str,
        api_type: str = "openai",
        azure_endpoint: Optional[str] = None,
        azure_deployment: Optional[str] = None,
        azure_version: Optional[str] = None,
        custom_base: Optional[str] = None,
    ) -> None:
        """Create .env file with API credentials.

        Args:
            api_key: OpenAI or Azure API key
            api_type: "openai" or "azure"
            azure_endpoint: Azure OpenAI endpoint (if Azure)
            azure_deployment: Azure deployment name (if Azure)
            azure_version: Azure API version (if Azure)
            custom_base: Custom API base URL

        Raises:
            ConfigError: If file creation fails
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            if api_type == "azure":
                env_content = f"""# Azure OpenAI Configuration
OPENAI_API_KEY={api_key}
OPENAI_API_TYPE=azure
AZURE_OPENAI_ENDPOINT={azure_endpoint}
AZURE_OPENAI_DEPLOYMENT_NAME={azure_deployment}
OPENAI_API_VERSION={azure_version or '2024-02-15-preview'}

# Local extension ingest auth (not OAuth). Replace with a random token.
EXTENSION_API_TOKEN=replace-with-random-local-token
"""
            elif custom_base:
                env_content = f"""# OpenAI Configuration (Custom Endpoint)
OPENAI_API_KEY={api_key}
OPENAI_API_BASE={custom_base}

# Local extension ingest auth (not OAuth). Replace with a random token.
EXTENSION_API_TOKEN=replace-with-random-local-token
"""
            else:
                env_content = f"""# OpenAI Configuration
OPENAI_API_KEY={api_key}

# Local extension ingest auth (not OAuth). Replace with a random token.
EXTENSION_API_TOKEN=replace-with-random-local-token
"""

            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)

            # Set restrictive permissions on Unix-like systems
            if os.name != 'nt':  # Not Windows
                os.chmod(self.env_file, 0o600)

        except Exception as e:
            raise ConfigError(f"Failed to create .env file: {e}") from e

    def get_current_storage(self, config: AppConfig) -> Optional[StorageLocation]:
        """Get the currently active storage location.

        Args:
            config: AppConfig instance

        Returns:
            Current StorageLocation or None if no storage configured
        """
        for storage in config.storage_locations:
            if storage.is_current:
                return storage

        # If none marked as current, return first one
        if config.storage_locations:
            return config.storage_locations[0]

        return None

    def get_primary_storage(self, config: AppConfig) -> Optional[StorageLocation]:
        """Get the storage location used for writes in current mode."""
        normalized = self._normalize_storage_config(config)
        return self.get_current_storage(normalized)

    def validate_storage_access(self, storage: StorageLocation) -> None:
        """Validate storage location is accessible.

        Args:
            storage: StorageLocation to validate

        Raises:
            ConfigError: If storage is not accessible
        """
        path = Path(storage.path)

        if not path.exists():
            raise ConfigError(f"Storage path does not exist: {storage.path}")

        if not path.is_dir():
            raise ConfigError(f"Storage path is not a directory: {storage.path}")

        if not os.access(path, os.R_OK):
            raise ConfigError(f"Storage path is not readable: {storage.path}")

        if not os.access(path, os.W_OK):
            raise ConfigError(f"Storage path is not writable: {storage.path}")

    def _normalize_storage_config(self, config: AppConfig) -> AppConfig:
        """Normalize storage fields for backward compatibility and one-drive modes."""
        current = self.get_current_storage(config)

        primary_path = config.primary_storage_path
        if not primary_path and current is not None:
            primary_path = current.path

        if config.storage_mode == "onedrive_only":
            if config.primary_storage_provider != "onedrive_local":
                raise ConfigError(
                    "storage_mode=onedrive_only requires primary_storage_provider=onedrive_local"
                )

            if not primary_path:
                raise ConfigError(
                    "storage_mode=onedrive_only requires primary_storage_path or a configured storage location"
                )

            primary_name = current.name if current else "onedrive"
            normalized_storage = StorageLocation(
                name=primary_name,
                path=primary_path,
                is_current=True,
                is_default=True,
            )
            return config.model_copy(
                update={
                    "storage_locations": [normalized_storage],
                    "primary_storage_path": primary_path,
                }
            )

        return config.model_copy(update={"primary_storage_path": primary_path})
