"""Tests for CLI commands."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from yoshibookmark.cli import cli
from yoshibookmark.config import ConfigManager
from yoshibookmark.models.config import AppConfig
from yoshibookmark.models.storage import StorageLocation


def _write_valid_setup(config_dir: Path) -> None:
    """Create a minimal valid setup for doctor checks."""
    cm = ConfigManager(config_dir)
    storage_root = config_dir / "onedrive"
    (storage_root / "bookmarks").mkdir(parents=True, exist_ok=True)
    (storage_root / "favicons").mkdir(parents=True, exist_ok=True)
    (storage_root / "screenshots").mkdir(parents=True, exist_ok=True)

    app_config = AppConfig(
        storage_locations=[
            StorageLocation(
                name="onedrive",
                path=str(storage_root),
                is_current=True,
                is_default=True,
            )
        ],
        storage_mode="onedrive_only",
        primary_storage_provider="onedrive_local",
        primary_storage_path=str(storage_root),
        ingest_require_auth=True,
        extension_allowed_origins=["chrome-extension://akegejjndolaellmldpmchibfhjcldgi"],
    )
    cm.save_app_config(app_config)
    cm.create_env_file(api_key="sk-live-test-key")
    cm.env_file.write_text(
        cm.env_file.read_text(encoding="utf-8")
        + "EXTENSION_API_TOKEN=local-test-token\n",
        encoding="utf-8",
    )


class TestCliDoctor:
    """Test yoshibookmark doctor command."""

    @staticmethod
    def _clear_env(monkeypatch) -> None:
        for key in (
            "OPENAI_API_KEY",
            "EXTENSION_API_TOKEN",
            "OPENAI_API_BASE",
            "OPENAI_API_TYPE",
            "OPENAI_API_VERSION",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "AZURE_OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)

    def test_doctor_passes_with_valid_setup(self, monkeypatch):
        self._clear_env(monkeypatch)
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".yoshibookmark"
            _write_valid_setup(config_dir)
            runner = CliRunner()

            result = runner.invoke(cli, ["doctor", "--config-dir", str(config_dir)])

            assert result.exit_code == 0
            assert "[PASS] config.yaml parsed successfully" in result.output
            assert "[PASS] OPENAI_API_KEY looks configured" in result.output
            assert "[PASS] EXTENSION_API_TOKEN looks configured" in result.output

    def test_doctor_fails_when_extension_token_missing(self, monkeypatch):
        self._clear_env(monkeypatch)
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".yoshibookmark"
            _write_valid_setup(config_dir)
            cm = ConfigManager(config_dir)
            cm.env_file.write_text("OPENAI_API_KEY=sk-live-test-key\n", encoding="utf-8")
            runner = CliRunner()

            result = runner.invoke(cli, ["doctor", "--config-dir", str(config_dir)])

            assert result.exit_code == 1
            assert "EXTENSION_API_TOKEN is missing" in result.output

    def test_doctor_fails_when_openai_key_placeholder(self, monkeypatch):
        self._clear_env(monkeypatch)
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".yoshibookmark"
            _write_valid_setup(config_dir)
            cm = ConfigManager(config_dir)
            cm.env_file.write_text(
                "OPENAI_API_KEY=your-openai-api-key-here\nEXTENSION_API_TOKEN=local-test-token\n",
                encoding="utf-8",
            )
            runner = CliRunner()

            result = runner.invoke(cli, ["doctor", "--config-dir", str(config_dir)])

            assert result.exit_code == 1
            assert "OPENAI_API_KEY appears unset or placeholder" in result.output
