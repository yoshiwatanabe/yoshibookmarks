"""Command-line interface for YoshiBookmark."""

import sys
import shutil
from pathlib import Path
from typing import Optional

import click
import httpx
import uvicorn


@click.group()
@click.version_option(version="0.1.0", prog_name="yoshibookmark")
def cli():
    """YoshiBookmark - URL and bookmark management system."""
    pass


@cli.command()
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Configuration directory (default: ~/.yoshibookmark)",
)
@click.option(
    "--openai-api-key",
    type=str,
    default=None,
    help="OpenAI API key (will be saved to .env file)",
)
@click.option(
    "--azure",
    is_flag=True,
    default=False,
    help="Use Azure OpenAI instead of OpenAI",
)
@click.option(
    "--storage-mode",
    type=click.Choice(["multi", "onedrive-only"], case_sensitive=False),
    default="onedrive-only",
    show_default=True,
    help="Storage mode. 'onedrive-only' uses a single OneDrive local sync folder.",
)
@click.option(
    "--onedrive-path",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Local OneDrive folder path used as primary storage in onedrive-only mode.",
)
def init(
    config_dir: Optional[Path],
    openai_api_key: Optional[str],
    azure: bool,
    storage_mode: str,
    onedrive_path: Optional[Path],
):
    """Initialize YoshiBookmark configuration.

    Creates configuration directory with default settings and storage location.
    """
    from .config import ConfigManager, ConfigError
    from .models.config import AppConfig
    from .models.storage import StorageLocation

    try:
        # Initialize config manager
        cm = ConfigManager(config_dir)

        click.echo(f"Initializing YoshiBookmark at {cm.config_dir}...")

        # Create config directory if needed
        cm.config_dir.mkdir(parents=True, exist_ok=True)

        # Create .env file
        if azure:
            cm.create_env_file(openai_api_key or "your-azure-api-key-here", api_type="azure")
            click.echo("[OK] Created .env file (Azure OpenAI)")
        else:
            cm.create_env_file(openai_api_key or "your-openai-api-key-here")
            click.echo("[OK] Created .env file (OpenAI)")

        storage_mode_normalized = storage_mode.lower().replace("-", "_")
        if storage_mode_normalized == "onedrive_only":
            if onedrive_path is None:
                entered = click.prompt(
                    "OneDrive local storage path",
                    type=click.Path(path_type=Path, file_okay=False),
                )
                onedrive_path = Path(entered)
            default_storage_dir = onedrive_path
            storage_name = "onedrive"
            provider = "onedrive_local"
        else:
            default_storage_dir = cm.config_dir / "storage" / "default"
            storage_name = "default"
            provider = "filesystem"

        default_storage_dir.mkdir(parents=True, exist_ok=True)
        (default_storage_dir / "bookmarks").mkdir(parents=True, exist_ok=True)
        (default_storage_dir / "favicons").mkdir(parents=True, exist_ok=True)
        (default_storage_dir / "screenshots").mkdir(parents=True, exist_ok=True)

        # Create default config
        default_config = AppConfig(
            storage_locations=[
                StorageLocation(
                    name=storage_name,
                    path=str(default_storage_dir),
                    is_current=True,
                    is_default=True,
                )
            ],
            storage_mode=storage_mode_normalized,
            primary_storage_provider=provider,
            primary_storage_path=str(default_storage_dir),
            legacy_storage_readonly=False,
            enable_semantic_search=False,
            enable_screenshots=False,
        )

        # Save config
        cm.save_app_config(default_config)
        click.echo("[OK] Created config.yaml")
        click.echo(f"[OK] Created storage directory at {default_storage_dir}")

        click.echo("\n" + "=" * 60)
        click.echo("[SUCCESS] YoshiBookmark initialized successfully!")
        click.echo("=" * 60)

        if not openai_api_key:
            click.echo(f"\n[WARNING] Please update your API key in: {cm.env_file}")
            click.echo("          Open the .env file and add your OpenAI API key")

        click.echo(f"\nConfiguration directory: {cm.config_dir}")
        click.echo(f"Storage directory: {default_storage_dir}")
        click.echo(f"Storage mode: {storage_mode_normalized}")
        click.echo("\nStart the server with: yoshibookmark serve")

    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host to bind (default: 127.0.0.1)",
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port to bind (default: 8000)",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload for development",
)
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Configuration directory (default: ~/.yoshibookmark)",
)
def serve(host: str, port: int, reload: bool, config_dir: Optional[Path]):
    """Start the YoshiBookmark API server.

    Starts the FastAPI server with the specified host and port.
    """
    from .config import ConfigManager, ConfigError

    try:
        # Verify configuration exists
        cm = ConfigManager(config_dir)

        if not cm.config_file.exists():
            click.echo("Error: Configuration not found", err=True)
            click.echo(f"Run 'yoshibookmark init' to create configuration at {cm.config_dir}", err=True)
            sys.exit(1)

        if not cm.env_file.exists():
            click.echo("Error: .env file not found", err=True)
            click.echo(f"Run 'yoshibookmark init' to create .env file at {cm.config_dir}", err=True)
            sys.exit(1)

        # Validate configuration
        try:
            cm.load_app_config()
            cm.load_env_settings()
        except ConfigError as e:
            click.echo(f"Configuration error: {e}", err=True)
            sys.exit(1)

        # Set config directory environment variable if custom
        if config_dir:
            import os
            os.environ["YOSHIBOOKMARK_CONFIG_DIR"] = str(config_dir)

        click.echo("=" * 60)
        click.echo("Starting YoshiBookmark API server...")
        click.echo("=" * 60)
        click.echo(f"Config directory: {cm.config_dir}")
        click.echo(f"Server URL: http://{host}:{port}")
        click.echo(f"API docs: http://{host}:{port}/docs")
        click.echo("=" * 60)
        click.echo("\nPress Ctrl+C to stop the server\n")

        # Start server
        uvicorn.run(
            "yoshibookmark.api:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )

    except KeyboardInterrupt:
        click.echo("\n\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


@cli.command(name="migrate-to-onedrive")
@click.option(
    "--source-path",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=True,
    help="Source storage root path to migrate from.",
)
@click.option(
    "--onedrive-path",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Destination local OneDrive storage path.",
)
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Configuration directory (default: ~/.yoshibookmark)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite conflicting destination files.",
)
def migrate_to_onedrive(
    source_path: Path,
    onedrive_path: Optional[Path],
    config_dir: Optional[Path],
    force: bool,
):
    """Migrate existing bookmark storage to OneDrive local sync folder."""
    from .config import ConfigManager, ConfigError
    from .models.storage import StorageLocation

    try:
        cm = ConfigManager(config_dir)
        app_config = cm.load_app_config()

        if onedrive_path is None:
            entered = click.prompt(
                "OneDrive local destination path",
                type=click.Path(path_type=Path, file_okay=False),
            )
            onedrive_path = Path(entered)

        source_root = source_path
        target_root = onedrive_path

        for dirname in ("bookmarks", "favicons", "screenshots"):
            (target_root / dirname).mkdir(parents=True, exist_ok=True)

        copied = 0
        skipped = 0
        conflicts = 0

        def copy_tree(src_dir: Path, dst_dir: Path) -> None:
            nonlocal copied, skipped, conflicts
            if not src_dir.exists():
                return

            for source_file in src_dir.rglob("*"):
                if source_file.is_dir():
                    continue

                relative = source_file.relative_to(src_dir)
                destination = dst_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)

                if destination.exists():
                    if source_file.read_bytes() == destination.read_bytes():
                        skipped += 1
                        continue
                    if not force:
                        conflicts += 1
                        continue

                shutil.copy2(source_file, destination)
                copied += 1

        copy_tree(source_root / "bookmarks", target_root / "bookmarks")
        copy_tree(source_root / "favicons", target_root / "favicons")
        copy_tree(source_root / "screenshots", target_root / "screenshots")

        app_config = app_config.model_copy(
            update={
                "storage_mode": "onedrive_only",
                "primary_storage_provider": "onedrive_local",
                "primary_storage_path": str(target_root),
                "legacy_storage_readonly": True,
                "storage_locations": [
                    StorageLocation(
                        name="onedrive",
                        path=str(target_root),
                        is_current=True,
                        is_default=True,
                    )
                ],
            }
        )
        cm.save_app_config(app_config)

        click.echo("=" * 60)
        click.echo("Migration complete")
        click.echo("=" * 60)
        click.echo(f"Source path: {source_root}")
        click.echo(f"OneDrive path: {target_root}")
        click.echo(f"Files copied: {copied}")
        click.echo(f"Files skipped (identical): {skipped}")
        click.echo(f"Conflicts not copied: {conflicts}")
        if conflicts and not force:
            click.echo("Use --force to overwrite conflicting destination files")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Migration failed: {e}", err=True)
        sys.exit(1)


def _is_placeholder_secret(value: Optional[str]) -> bool:
    """Detect placeholder/empty secret values that should be replaced."""
    if value is None:
        return True

    normalized = value.strip().lower()
    if not normalized:
        return True

    markers = (
        "your-",
        "replace-with",
        "<random",
        "example",
        "changeme",
        "todo",
    )
    return any(marker in normalized for marker in markers)


@cli.command()
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Configuration directory (default: ~/.yoshibookmark)",
)
@click.option(
    "--api-url",
    type=str,
    default=None,
    help="Optional running API URL to verify (example: http://127.0.0.1:8000)",
)
def doctor(config_dir: Optional[Path], api_url: Optional[str]):
    """Validate local setup and report actionable fixes."""
    from .config import ConfigManager, ConfigError

    cm = ConfigManager(config_dir)
    failures = 0
    warnings = 0
    app_config = None
    env_settings = None

    def report(status: str, message: str, fix: Optional[str] = None) -> None:
        click.echo(f"[{status}] {message}")
        if fix:
            click.echo(f"      Fix: {fix}")

    click.echo("=" * 60)
    click.echo("YoshiBookmark doctor")
    click.echo("=" * 60)
    click.echo(f"Config directory: {cm.config_dir}")

    if cm.config_file.exists():
        report("PASS", f"Found config file: {cm.config_file}")
    else:
        failures += 1
        report("FAIL", f"Missing config file: {cm.config_file}", "Run: yoshibookmark init")

    if cm.env_file.exists():
        report("PASS", f"Found env file: {cm.env_file}")
    else:
        failures += 1
        report("FAIL", f"Missing env file: {cm.env_file}", "Run: yoshibookmark init")

    if cm.config_file.exists():
        try:
            app_config = cm.load_app_config()
            report("PASS", "config.yaml parsed successfully")
        except ConfigError as e:
            failures += 1
            report("FAIL", f"config.yaml validation failed: {e}")

    if cm.env_file.exists():
        try:
            env_settings = cm.load_env_settings()
            report("PASS", ".env parsed successfully")
        except ConfigError as e:
            failures += 1
            report("FAIL", f".env validation failed: {e}")

    if env_settings is not None:
        if _is_placeholder_secret(env_settings.openai_api_key):
            failures += 1
            report(
                "FAIL",
                "OPENAI_API_KEY appears unset or placeholder",
                "Set OPENAI_API_KEY in ~/.yoshibookmark/.env",
            )
        else:
            report("PASS", "OPENAI_API_KEY looks configured")

    if app_config is not None:
        primary_storage = cm.get_primary_storage(app_config)
        if primary_storage is None:
            failures += 1
            report("FAIL", "No primary storage configured in config.yaml")
        else:
            try:
                cm.validate_storage_access(primary_storage)
                report("PASS", f"Primary storage is accessible: {primary_storage.path}")
            except ConfigError as e:
                failures += 1
                report("FAIL", f"Primary storage is not accessible: {e}")

        if app_config.ingest_require_auth:
            if env_settings is None or not env_settings.extension_api_token:
                failures += 1
                report(
                    "FAIL",
                    "Ingestion auth is enabled but EXTENSION_API_TOKEN is missing",
                    "Set EXTENSION_API_TOKEN in ~/.yoshibookmark/.env",
                )
            elif _is_placeholder_secret(env_settings.extension_api_token):
                failures += 1
                report(
                    "FAIL",
                    "EXTENSION_API_TOKEN appears to be a placeholder",
                    "Generate token in PowerShell: [guid]::NewGuid().ToString(\"N\")",
                )
            else:
                report("PASS", "EXTENSION_API_TOKEN looks configured")

        allowed_origins = app_config.extension_allowed_origins
        if not allowed_origins:
            warnings += 1
            report(
                "WARN",
                "extension_allowed_origins is empty",
                "Add your chrome-extension://<id> or edge-extension://<id> origin to config.yaml",
            )
        else:
            placeholder_origins = [
                origin for origin in allowed_origins if "<" in origin or ">" in origin
            ]
            malformed_origins = [
                origin
                for origin in allowed_origins
                if not origin.startswith("chrome-extension://")
                and not origin.startswith("edge-extension://")
            ]
            if placeholder_origins:
                failures += 1
                report(
                    "FAIL",
                    f"extension_allowed_origins contains placeholder entries: {placeholder_origins}",
                    "Replace <your-extension-id> with the real extension ID",
                )
            elif malformed_origins:
                warnings += 1
                report(
                    "WARN",
                    f"Some extension origins look unusual: {malformed_origins}",
                    "Use chrome-extension://<id> or edge-extension://<id>",
                )
            else:
                report("PASS", "Extension origins look valid")

    if api_url:
        health_url = f"{api_url.rstrip('/')}/api/v1/health"
        try:
            response = httpx.get(health_url, timeout=3.0)
            if response.status_code == 200:
                report("PASS", f"Server is reachable: {health_url}")
            else:
                failures += 1
                report(
                    "FAIL",
                    f"Server health check returned HTTP {response.status_code}: {health_url}",
                    "Start server: yoshibookmark serve --port 8000",
                )
        except Exception as e:
            failures += 1
            report(
                "FAIL",
                f"Server is not reachable at {health_url} ({e})",
                "Start server and ensure API URL matches --api-url",
            )
    else:
        warnings += 1
        report("WARN", "Skipped server reachability check (no --api-url provided)")

    click.echo("-" * 60)
    click.echo(f"Summary: {failures} fail, {warnings} warn")

    if failures:
        sys.exit(1)
    sys.exit(0)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
