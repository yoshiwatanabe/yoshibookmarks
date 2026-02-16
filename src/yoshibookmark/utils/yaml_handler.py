"""YAML serialization and deserialization utilities for bookmarks."""

from pathlib import Path
from typing import Any, Dict

import yaml

from ..models.bookmark import Bookmark


class YAMLError(Exception):
    """YAML processing error."""

    pass


def serialize_bookmark(bookmark: Bookmark) -> str:
    """Serialize a Bookmark to YAML string.

    Args:
        bookmark: Bookmark instance to serialize

    Returns:
        YAML string representation

    Raises:
        YAMLError: If serialization fails
    """
    try:
        # Convert Pydantic model to dict
        data = bookmark.model_dump(mode='json')

        # Convert HttpUrl to string for YAML
        if 'url' in data and hasattr(data['url'], '__str__'):
            data['url'] = str(data['url'])

        # Serialize to YAML
        yaml_str = yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        return yaml_str

    except Exception as e:
        raise YAMLError(f"Failed to serialize bookmark: {e}") from e


def deserialize_bookmark(yaml_str: str) -> Bookmark:
    """Deserialize a Bookmark from YAML string.

    Args:
        yaml_str: YAML string to deserialize

    Returns:
        Bookmark instance

    Raises:
        YAMLError: If deserialization fails
    """
    try:
        # Parse YAML
        data = yaml.safe_load(yaml_str)

        if data is None:
            raise YAMLError("YAML content is empty")

        # Create Bookmark from dict
        bookmark = Bookmark(**data)

        return bookmark

    except yaml.YAMLError as e:
        raise YAMLError(f"Invalid YAML format: {e}") from e
    except Exception as e:
        raise YAMLError(f"Failed to deserialize bookmark: {e}") from e


def load_bookmark_from_file(file_path: Path) -> Bookmark:
    """Load a Bookmark from YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Bookmark instance

    Raises:
        YAMLError: If file reading or parsing fails
    """
    try:
        if not file_path.exists():
            raise YAMLError(f"File not found: {file_path}")

        yaml_str = file_path.read_text(encoding='utf-8')
        return deserialize_bookmark(yaml_str)

    except YAMLError:
        raise
    except Exception as e:
        raise YAMLError(f"Failed to load bookmark from {file_path}: {e}") from e


def save_bookmark_to_file(bookmark: Bookmark, file_path: Path) -> None:
    """Save a Bookmark to YAML file.

    Args:
        bookmark: Bookmark instance to save
        file_path: Path where to save the YAML file

    Raises:
        YAMLError: If file writing fails
    """
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        yaml_str = serialize_bookmark(bookmark)
        file_path.write_text(yaml_str, encoding='utf-8')

    except YAMLError:
        raise
    except Exception as e:
        raise YAMLError(f"Failed to save bookmark to {file_path}: {e}") from e


def validate_yaml_structure(data: Dict[str, Any]) -> None:
    """Validate YAML data structure has required bookmark fields.

    Args:
        data: Parsed YAML data dictionary

    Raises:
        YAMLError: If required fields are missing
    """
    required_fields = ['id', 'url', 'title', 'storage_location']

    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise YAMLError(
            f"Missing required fields in YAML: {', '.join(missing_fields)}"
        )
