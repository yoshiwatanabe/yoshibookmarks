"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from yoshibookmark.config import ConfigError, ConfigManager
from yoshibookmark.models.config import AppConfig, EnvSettings
from yoshibookmark.models.storage import StorageLocation


class TestStorageLocation:
    """Test StorageLocation model validation."""

    def test_valid_storage_location(self):
        """Test creating a valid storage location."""
        storage = StorageLocation(
            name="test_storage",
            path="/absolute/path/to/storage",
            is_current=True,
        )
        assert storage.name == "test_storage"
        assert storage.is_current is True

    def test_invalid_storage_name(self):
        """Test storage name validation."""
        with pytest.raises(ValueError, match="only letters, numbers"):
            StorageLocation(name="invalid name!", path="/path")

    def test_empty_storage_name(self):
        """Test empty storage name is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            StorageLocation(name="", path="/path")

    def test_storage_name_with_special_chars(self):
        """Test storage name with special characters."""
        # This should now pass since we removed strict path validation
        storage = StorageLocation(name="test", path="relative/path")
        assert storage.name == "test"


class TestAppConfig:
    """Test AppConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AppConfig(storage_locations=[])
        assert config.host == "127.0.0.1"
        assert config.port is None
        assert config.enable_semantic_search is True
        assert config.embedding_model == "text-embedding-3-small"
        assert config.storage_mode == "multi"
        assert config.primary_storage_provider == "filesystem"

    def test_config_with_storage(self):
        """Test config with storage locations."""
        storage = StorageLocation(name="default", path="/tmp/storage")
        config = AppConfig(storage_locations=[storage])
        assert len(config.storage_locations) == 1
        assert config.storage_locations[0].name == "default"
        assert config.primary_storage_path is None


class TestConfigManager:
    """Test ConfigManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".yoshibookmark"
        self.config_manager = ConfigManager(self.config_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_dir_creation(self):
        """Test configuration directory is created."""
        assert self.config_manager.config_dir == self.config_dir

    def test_uses_env_config_dir_when_not_provided(self):
        """Test config manager reads YOSHIBOOKMARK_CONFIG_DIR."""
        env_dir = Path(self.temp_dir) / "from_env"
        os.environ["YOSHIBOOKMARK_CONFIG_DIR"] = str(env_dir)
        try:
            cm = ConfigManager()
            assert cm.config_dir == env_dir
        finally:
            os.environ.pop("YOSHIBOOKMARK_CONFIG_DIR", None)

    def test_load_missing_env_file(self):
        """Test loading missing .env file raises error."""
        with pytest.raises(ConfigError, match=".env file not found"):
            self.config_manager.load_env_settings()

    def test_load_missing_config_file(self):
        """Test loading missing config.yaml raises error."""
        with pytest.raises(ConfigError, match="Config file not found"):
            self.config_manager.load_app_config()

    def test_create_env_file(self):
        """Test creating .env file."""
        self.config_manager.create_env_file(api_key="sk-test123")

        assert self.config_manager.env_file.exists()

        content = self.config_manager.env_file.read_text()
        assert "OPENAI_API_KEY=sk-test123" in content
        assert "EXTENSION_API_TOKEN=replace-with-random-local-token" in content

    def test_create_azure_env_file(self):
        """Test creating Azure .env file."""
        self.config_manager.create_env_file(
            api_key="azure-key",
            api_type="azure",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4",
            azure_version="2024-02-15",
        )

        content = self.config_manager.env_file.read_text()
        assert "OPENAI_API_TYPE=azure" in content
        assert "AZURE_OPENAI_ENDPOINT=" in content

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        storage = StorageLocation(
            name="test",
            path=str(Path(self.temp_dir) / "storage"),
            is_current=True,
        )
        config = AppConfig(
            storage_locations=[storage],
            enable_semantic_search=False,
        )

        self.config_manager.save_app_config(config)
        assert self.config_manager.config_file.exists()

        loaded = self.config_manager.load_app_config()
        assert len(loaded.storage_locations) == 1
        assert loaded.storage_locations[0].name == "test"
        assert loaded.enable_semantic_search is False
        assert loaded.primary_storage_path == str(Path(self.temp_dir) / "storage")

    def test_onedrive_only_normalizes_to_single_storage(self):
        """Test onedrive_only config normalizes storage to primary path."""
        target_path = str(Path(self.temp_dir) / "onedrive")
        config = AppConfig(
            storage_locations=[],
            storage_mode="onedrive_only",
            primary_storage_provider="onedrive_local",
            primary_storage_path=target_path,
        )

        self.config_manager.save_app_config(config)
        loaded = self.config_manager.load_app_config()

        assert loaded.storage_mode == "onedrive_only"
        assert loaded.primary_storage_path == target_path
        assert len(loaded.storage_locations) == 1
        assert loaded.storage_locations[0].path == target_path
        assert loaded.storage_locations[0].is_current is True

    def test_invalid_yaml_raises_error(self):
        """Test invalid YAML raises ConfigError."""
        self.config_manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_manager.config_file.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigError, match="Invalid YAML"):
            self.config_manager.load_app_config()

    def test_get_current_storage(self):
        """Test getting current storage location."""
        storage1 = StorageLocation(name="first", path="/path1", is_current=False)
        storage2 = StorageLocation(name="second", path="/path2", is_current=True)
        config = AppConfig(storage_locations=[storage1, storage2])

        current = self.config_manager.get_current_storage(config)
        assert current is not None
        assert current.name == "second"

    def test_get_current_storage_defaults_to_first(self):
        """Test current storage defaults to first if none marked."""
        storage = StorageLocation(name="only", path="/path", is_current=False)
        config = AppConfig(storage_locations=[storage])

        current = self.config_manager.get_current_storage(config)
        assert current is not None
        assert current.name == "only"

    def test_validate_nonexistent_storage(self):
        """Test validating non-existent storage raises error."""
        storage = StorageLocation(name="test", path="/nonexistent/path")

        with pytest.raises(ConfigError, match="does not exist"):
            self.config_manager.validate_storage_access(storage)

    def test_validate_file_as_storage(self):
        """Test validating file path as storage raises error."""
        # Create a file instead of directory
        file_path = Path(self.temp_dir) / "file.txt"
        file_path.write_text("test")

        storage = StorageLocation(name="test", path=str(file_path))

        with pytest.raises(ConfigError, match="not a directory"):
            self.config_manager.validate_storage_access(storage)

    def test_validate_accessible_storage(self):
        """Test validating accessible storage succeeds."""
        storage_path = Path(self.temp_dir) / "storage"
        storage_path.mkdir(parents=True)

        storage = StorageLocation(name="test", path=str(storage_path))

        # Should not raise
        self.config_manager.validate_storage_access(storage)
