"""Tests for Bookmark model and YAML handler."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from yoshibookmark.models.bookmark import Bookmark
from yoshibookmark.utils.yaml_handler import (
    YAMLError,
    deserialize_bookmark,
    load_bookmark_from_file,
    save_bookmark_to_file,
    serialize_bookmark,
    validate_yaml_structure,
)


class TestBookmarkModel:
    """Test Bookmark model validation."""

    def test_valid_bookmark_creation(self):
        """Test creating a valid bookmark."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example Site",
            storage_location="default",
        )

        assert str(bookmark.url) == "https://example.com/"  # HttpUrl normalizes
        assert bookmark.title == "Example Site"
        assert bookmark.storage_location == "default"
        assert bookmark.deleted is False
        assert len(bookmark.keywords) == 0

    def test_bookmark_with_keywords(self):
        """Test bookmark with keywords."""
        bookmark = Bookmark(
            url="https://github.com/python/cpython",
            title="CPython",
            keywords=["python", "cpython", "github"],
            storage_location="work",
        )

        assert len(bookmark.keywords) == 3
        assert bookmark.keywords[0] == "python"

    def test_invalid_url_rejected(self):
        """Test invalid URL format is rejected."""
        with pytest.raises(ValueError):
            Bookmark(
                url="not-a-url",
                title="Test",
                storage_location="default",
            )

    def test_malformed_url_rejected(self):
        """Test malformed URL is rejected."""
        with pytest.raises(ValueError):
            Bookmark(
                url="htp://missing-t.com",
                title="Test",
                storage_location="default",
            )

    def test_missing_protocol_rejected(self):
        """Test URL without protocol is rejected."""
        with pytest.raises(ValueError):
            Bookmark(
                url="example.com",
                title="Test",
                storage_location="default",
            )

    def test_too_many_keywords_rejected(self):
        """Test more than 4 keywords are rejected."""
        with pytest.raises(ValidationError):
            Bookmark(
                url="https://example.com",
                title="Test",
                keywords=["one", "two", "three", "four", "five"],
                storage_location="default",
            )

    def test_empty_title_rejected(self):
        """Test empty title is rejected."""
        with pytest.raises(ValidationError):
            Bookmark(
                url="https://example.com",
                title="",
                storage_location="default",
            )

    def test_whitespace_only_title_rejected(self):
        """Test whitespace-only title is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Bookmark(
                url="https://example.com",
                title="   ",
                storage_location="default",
            )

    def test_title_trimmed(self):
        """Test title is trimmed of surrounding whitespace."""
        bookmark = Bookmark(
            url="https://example.com",
            title="  Test Title  ",
            storage_location="default",
        )

        assert bookmark.title == "Test Title"

    def test_empty_keywords_filtered(self):
        """Test empty keywords are filtered out."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Test",
            keywords=["python", "", "  ", "django"],
            storage_location="default",
        )

        assert len(bookmark.keywords) == 2
        assert "python" in bookmark.keywords
        assert "django" in bookmark.keywords

    def test_empty_tags_filtered(self):
        """Test empty tags are filtered out."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Test",
            tags=["tag1", "", "  ", "tag2"],
            storage_location="default",
        )

        assert len(bookmark.tags) == 2
        assert "tag1" in bookmark.tags
        assert "tag2" in bookmark.tags

    def test_directory_traversal_in_folder_rejected(self):
        """Test directory traversal in folder path is rejected."""
        with pytest.raises(ValueError, match="directory traversal"):
            Bookmark(
                url="https://example.com",
                title="Test",
                folder_path="../../../etc/passwd",
                storage_location="default",
            )

    def test_absolute_folder_path_rejected(self):
        """Test absolute folder paths are rejected."""
        with pytest.raises(ValueError, match="directory traversal"):
            Bookmark(
                url="https://example.com",
                title="Test",
                folder_path="/absolute/path",
                storage_location="default",
            )

    def test_valid_folder_path(self):
        """Test valid folder path is accepted."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Test",
            folder_path="development/python/frameworks",
            storage_location="default",
        )

        assert bookmark.folder_path == "development/python/frameworks"

    def test_field_type_mismatch(self):
        """Test field type validation."""
        with pytest.raises(ValueError):
            Bookmark(
                url="https://example.com",
                title="Test",
                keywords="should-be-list",  # Should be list, not string
                storage_location="default",
            )


class TestYAMLHandler:
    """Test YAML serialization and deserialization."""

    def test_serialize_bookmark(self):
        """Test serializing bookmark to YAML."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example",
            keywords=["test", "example"],
            description="A test bookmark",
            storage_location="default",
        )

        yaml_str = serialize_bookmark(bookmark)

        assert "url: https://example.com/" in yaml_str
        assert "title: Example" in yaml_str
        assert "keywords:" in yaml_str
        assert "- test" in yaml_str
        assert "- example" in yaml_str

    def test_deserialize_bookmark(self):
        """Test deserializing bookmark from YAML."""
        yaml_str = """
id: test-id-123
url: https://example.com
title: Example Site
keywords:
  - python
  - testing
description: A test bookmark
storage_location: default
created_at: '2026-02-04T10:00:00Z'
deleted: false
        """

        bookmark = deserialize_bookmark(yaml_str)

        assert bookmark.id == "test-id-123"
        assert str(bookmark.url) == "https://example.com/"
        assert bookmark.title == "Example Site"
        assert len(bookmark.keywords) == 2
        assert bookmark.storage_location == "default"

    def test_yaml_round_trip(self):
        """Test serialize → deserialize → equals original."""
        original = Bookmark(
            url="https://github.com/python/cpython",
            title="CPython Repository",
            keywords=["python", "cpython"],
            description="Official Python implementation",
            tags=["programming", "open-source"],
            folder_path="development/python",
            storage_location="work",
        )

        # Serialize
        yaml_str = serialize_bookmark(original)

        # Deserialize
        restored = deserialize_bookmark(yaml_str)

        # Compare (URLs are normalized by HttpUrl)
        assert original.id == restored.id
        assert str(original.url) == str(restored.url)
        assert original.title == restored.title
        assert original.keywords == restored.keywords
        assert original.description == restored.description
        assert original.tags == restored.tags
        assert original.folder_path == restored.folder_path
        assert original.storage_location == restored.storage_location

    def test_deserialize_empty_yaml(self):
        """Test deserializing empty YAML raises error."""
        with pytest.raises(YAMLError, match="empty"):
            deserialize_bookmark("")

    def test_deserialize_invalid_yaml(self):
        """Test deserializing invalid YAML raises error."""
        with pytest.raises(YAMLError, match="Invalid YAML"):
            deserialize_bookmark("invalid: yaml: content:")

    def test_deserialize_missing_required_fields(self):
        """Test deserializing YAML with missing fields raises error."""
        yaml_str = """
url: https://example.com
# Missing title, id, storage_location
        """

        with pytest.raises(YAMLError):
            deserialize_bookmark(yaml_str)

    def test_save_and_load_bookmark_file(self):
        """Test saving and loading bookmark from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "bookmark.yaml"

            bookmark = Bookmark(
                url="https://example.com",
                title="Test Bookmark",
                keywords=["test"],
                storage_location="default",
            )

            # Save
            save_bookmark_to_file(bookmark, file_path)
            assert file_path.exists()

            # Load
            loaded = load_bookmark_from_file(file_path)
            assert loaded.id == bookmark.id
            assert str(loaded.url) == str(bookmark.url)
            assert loaded.title == bookmark.title

    def test_save_bookmark_creates_parent_directory(self):
        """Test saving bookmark creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "nested" / "bookmark.yaml"

            bookmark = Bookmark(
                url="https://example.com",
                title="Test",
                storage_location="default",
            )

            save_bookmark_to_file(bookmark, file_path)
            assert file_path.exists()
            assert file_path.parent.exists()

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        with pytest.raises(YAMLError, match="not found"):
            load_bookmark_from_file(Path("/nonexistent/file.yaml"))

    def test_validate_yaml_structure(self):
        """Test validating YAML structure."""
        valid_data = {
            'id': 'test-123',
            'url': 'https://example.com',
            'title': 'Test',
            'storage_location': 'default',
        }

        # Should not raise
        validate_yaml_structure(valid_data)

    def test_validate_yaml_structure_missing_fields(self):
        """Test validating YAML with missing fields raises error."""
        invalid_data = {
            'id': 'test-123',
            'url': 'https://example.com',
            # Missing title and storage_location
        }

        with pytest.raises(YAMLError, match="Missing required fields"):
            validate_yaml_structure(invalid_data)
