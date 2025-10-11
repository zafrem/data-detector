"""Tests for YAML utilities."""

import pytest
from pathlib import Path

from datadetector.yaml_utils import (
    YAMLHandler,
    PatternFileHandler,
    read_yaml,
    write_yaml,
    update_yaml,
)


class TestYAMLHandler:
    """Test YAMLHandler class."""

    def test_read_yaml(self, tmp_path):
        """Test reading YAML file."""
        yaml_file = tmp_path / "test.yml"
        yaml_file.write_text(
            """
namespace: test
description: Test patterns
patterns:
  - id: test_01
    category: email
"""
        )

        data = YAMLHandler.read_yaml(yaml_file)
        assert data["namespace"] == "test"
        assert data["description"] == "Test patterns"
        assert len(data["patterns"]) == 1

    def test_read_yaml_file_not_found(self, tmp_path):
        """Test reading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            YAMLHandler.read_yaml(tmp_path / "nonexistent.yml")

    def test_read_yaml_invalid_yaml(self, tmp_path):
        """Test reading invalid YAML raises error."""
        yaml_file = tmp_path / "invalid.yml"
        yaml_file.write_text("{ invalid yaml content")

        with pytest.raises(ValueError, match="Invalid YAML"):
            YAMLHandler.read_yaml(yaml_file)

    def test_read_yaml_not_dict(self, tmp_path):
        """Test reading YAML that's not a dict raises error."""
        yaml_file = tmp_path / "list.yml"
        yaml_file.write_text("- item1\n- item2")

        with pytest.raises(ValueError, match="Expected YAML file to contain a dict"):
            YAMLHandler.read_yaml(yaml_file)

    def test_write_yaml(self, tmp_path):
        """Test writing YAML file."""
        yaml_file = tmp_path / "output.yml"
        data = {
            "namespace": "test",
            "description": "Test",
            "patterns": [{"id": "test_01"}],
        }

        YAMLHandler.write_yaml(yaml_file, data)

        assert yaml_file.exists()
        read_data = YAMLHandler.read_yaml(yaml_file)
        assert read_data == data

    def test_write_yaml_with_sort_keys(self, tmp_path):
        """Test writing YAML with sorted keys."""
        yaml_file = tmp_path / "sorted.yml"
        data = {"z": 1, "a": 2, "m": 3}

        YAMLHandler.write_yaml(yaml_file, data, sort_keys=True)

        content = yaml_file.read_text()
        lines = [line for line in content.split("\n") if line.strip()]
        # Keys should be in alphabetical order
        assert lines[0].startswith("a:")
        assert lines[1].startswith("m:")
        assert lines[2].startswith("z:")

    def test_write_yaml_creates_parent_dirs(self, tmp_path):
        """Test writing YAML creates parent directories."""
        yaml_file = tmp_path / "subdir" / "nested" / "test.yml"
        data = {"test": "value"}

        YAMLHandler.write_yaml(yaml_file, data)

        assert yaml_file.exists()
        assert yaml_file.parent.exists()

    def test_write_yaml_overwrite_false(self, tmp_path):
        """Test writing fails when file exists and overwrite=False."""
        yaml_file = tmp_path / "existing.yml"
        yaml_file.write_text("existing: content")

        with pytest.raises(FileExistsError):
            YAMLHandler.write_yaml(yaml_file, {"new": "data"}, overwrite=False)

    def test_write_yaml_overwrite_true(self, tmp_path):
        """Test writing succeeds when file exists and overwrite=True."""
        yaml_file = tmp_path / "existing.yml"
        yaml_file.write_text("existing: content")

        YAMLHandler.write_yaml(yaml_file, {"new": "data"}, overwrite=True)

        data = YAMLHandler.read_yaml(yaml_file)
        assert data == {"new": "data"}

    def test_write_yaml_not_dict_raises_error(self, tmp_path):
        """Test writing non-dict raises error."""
        yaml_file = tmp_path / "test.yml"

        with pytest.raises(ValueError, match="Data must be a dictionary"):
            YAMLHandler.write_yaml(yaml_file, ["not", "a", "dict"])

    def test_update_yaml_merge(self, tmp_path):
        """Test updating YAML with merge=True."""
        yaml_file = tmp_path / "test.yml"
        original = {"a": 1, "b": 2}
        YAMLHandler.write_yaml(yaml_file, original)

        result = YAMLHandler.update_yaml(yaml_file, {"b": 3, "c": 4}, merge=True)

        assert result == {"a": 1, "b": 3, "c": 4}
        data = YAMLHandler.read_yaml(yaml_file)
        assert data == {"a": 1, "b": 3, "c": 4}

    def test_update_yaml_replace(self, tmp_path):
        """Test updating YAML with merge=False."""
        yaml_file = tmp_path / "test.yml"
        original = {"a": 1, "b": 2}
        YAMLHandler.write_yaml(yaml_file, original)

        result = YAMLHandler.update_yaml(yaml_file, {"c": 3}, merge=False)

        assert result == {"c": 3}
        data = YAMLHandler.read_yaml(yaml_file)
        assert data == {"c": 3}


class TestPatternFileHandler:
    """Test PatternFileHandler class."""

    def test_create_pattern_file(self, tmp_path):
        """Test creating a pattern file."""
        yaml_file = tmp_path / "patterns.yml"

        patterns = [
            {
                "id": "email_01",
                "location": "test",
                "category": "email",
                "description": "Email pattern",
                "pattern": r"[a-z]+@[a-z]+\.com",
                "mask": "***@***.***",
                "policy": {
                    "store_raw": False,
                    "action_on_match": "redact",
                    "severity": "medium",
                },
            }
        ]

        PatternFileHandler.create_pattern_file(
            yaml_file,
            namespace="custom",
            description="Custom patterns",
            patterns=patterns,
        )

        assert yaml_file.exists()
        data = YAMLHandler.read_yaml(yaml_file)
        assert data["namespace"] == "custom"
        assert data["description"] == "Custom patterns"
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["id"] == "email_01"

    def test_create_pattern_file_no_patterns(self, tmp_path):
        """Test creating pattern file without patterns."""
        yaml_file = tmp_path / "empty_patterns.yml"

        PatternFileHandler.create_pattern_file(
            yaml_file,
            namespace="test",
            description="Test",
        )

        data = YAMLHandler.read_yaml(yaml_file)
        assert data["patterns"] == []

    def test_add_pattern_to_file(self, tmp_path):
        """Test adding pattern to file."""
        yaml_file = tmp_path / "patterns.yml"
        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test"
        )

        pattern = {
            "id": "phone_01",
            "location": "test",
            "category": "phone",
            "pattern": r"\d{3}-\d{4}",
            "mask": "***-****",
            "policy": {"store_raw": False, "action_on_match": "redact", "severity": "low"},
        }

        PatternFileHandler.add_pattern_to_file(yaml_file, pattern)

        data = YAMLHandler.read_yaml(yaml_file)
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["id"] == "phone_01"

    def test_add_pattern_missing_fields(self, tmp_path):
        """Test adding pattern with missing required fields."""
        yaml_file = tmp_path / "patterns.yml"
        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test"
        )

        invalid_pattern = {"id": "test_01"}  # Missing required fields

        with pytest.raises(ValueError, match="missing required fields"):
            PatternFileHandler.add_pattern_to_file(yaml_file, invalid_pattern)

    def test_add_duplicate_pattern_warning(self, tmp_path, caplog):
        """Test adding duplicate pattern logs warning."""
        yaml_file = tmp_path / "patterns.yml"
        pattern = {
            "id": "test_01",
            "location": "test",
            "category": "email",
            "pattern": r"test",
            "policy": {"store_raw": False, "action_on_match": "redact", "severity": "low"},
        }

        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test", patterns=[pattern]
        )

        PatternFileHandler.add_pattern_to_file(yaml_file, pattern)

        assert "already exists" in caplog.text

    def test_remove_pattern_from_file(self, tmp_path):
        """Test removing pattern from file."""
        yaml_file = tmp_path / "patterns.yml"
        patterns = [
            {
                "id": "test_01",
                "location": "test",
                "category": "email",
                "pattern": r"test",
                "policy": {
                    "store_raw": False,
                    "action_on_match": "redact",
                    "severity": "low",
                },
            }
        ]

        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test", patterns=patterns
        )

        result = PatternFileHandler.remove_pattern_from_file(yaml_file, "test_01")

        assert result is True
        data = YAMLHandler.read_yaml(yaml_file)
        assert len(data["patterns"]) == 0

    def test_remove_pattern_not_found(self, tmp_path, caplog):
        """Test removing non-existent pattern."""
        yaml_file = tmp_path / "patterns.yml"
        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test"
        )

        result = PatternFileHandler.remove_pattern_from_file(yaml_file, "nonexistent")

        assert result is False
        assert "not found" in caplog.text

    def test_update_pattern_in_file(self, tmp_path):
        """Test updating pattern in file."""
        yaml_file = tmp_path / "patterns.yml"
        patterns = [
            {
                "id": "test_01",
                "location": "test",
                "category": "email",
                "pattern": r"old_pattern",
                "mask": "***",
                "policy": {
                    "store_raw": False,
                    "action_on_match": "redact",
                    "severity": "low",
                },
            }
        ]

        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test", patterns=patterns
        )

        result = PatternFileHandler.update_pattern_in_file(
            yaml_file, "test_01", {"pattern": r"new_pattern", "mask": "###"}
        )

        assert result is True
        data = YAMLHandler.read_yaml(yaml_file)
        assert data["patterns"][0]["pattern"] == "new_pattern"
        assert data["patterns"][0]["mask"] == "###"

    def test_update_pattern_not_found(self, tmp_path, caplog):
        """Test updating non-existent pattern."""
        yaml_file = tmp_path / "patterns.yml"
        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test"
        )

        result = PatternFileHandler.update_pattern_in_file(
            yaml_file, "nonexistent", {"pattern": "test"}
        )

        assert result is False
        assert "not found" in caplog.text

    def test_get_pattern_from_file(self, tmp_path):
        """Test getting pattern from file."""
        yaml_file = tmp_path / "patterns.yml"
        patterns = [
            {
                "id": "test_01",
                "location": "test",
                "category": "email",
                "pattern": r"test",
                "policy": {
                    "store_raw": False,
                    "action_on_match": "redact",
                    "severity": "low",
                },
            }
        ]

        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test", patterns=patterns
        )

        pattern = PatternFileHandler.get_pattern_from_file(yaml_file, "test_01")

        assert pattern is not None
        assert pattern["id"] == "test_01"
        assert pattern["pattern"] == "test"

    def test_get_pattern_not_found(self, tmp_path):
        """Test getting non-existent pattern."""
        yaml_file = tmp_path / "patterns.yml"
        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test"
        )

        pattern = PatternFileHandler.get_pattern_from_file(yaml_file, "nonexistent")

        assert pattern is None

    def test_list_patterns_in_file(self, tmp_path):
        """Test listing patterns in file."""
        yaml_file = tmp_path / "patterns.yml"
        patterns = [
            {
                "id": "test_01",
                "location": "test",
                "category": "email",
                "pattern": r"test1",
                "policy": {
                    "store_raw": False,
                    "action_on_match": "redact",
                    "severity": "low",
                },
            },
            {
                "id": "test_02",
                "location": "test",
                "category": "phone",
                "pattern": r"test2",
                "policy": {
                    "store_raw": False,
                    "action_on_match": "redact",
                    "severity": "low",
                },
            },
        ]

        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test", patterns=patterns
        )

        pattern_ids = PatternFileHandler.list_patterns_in_file(yaml_file)

        assert len(pattern_ids) == 2
        assert "test_01" in pattern_ids
        assert "test_02" in pattern_ids

    def test_list_patterns_empty_file(self, tmp_path):
        """Test listing patterns in file with no patterns."""
        yaml_file = tmp_path / "patterns.yml"
        PatternFileHandler.create_pattern_file(
            yaml_file, namespace="test", description="Test"
        )

        pattern_ids = PatternFileHandler.list_patterns_in_file(yaml_file)

        assert pattern_ids == []


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_read_yaml_convenience(self, tmp_path):
        """Test read_yaml convenience function."""
        yaml_file = tmp_path / "test.yml"
        yaml_file.write_text("test: value")

        data = read_yaml(yaml_file)

        assert data == {"test": "value"}

    def test_write_yaml_convenience(self, tmp_path):
        """Test write_yaml convenience function."""
        yaml_file = tmp_path / "test.yml"

        write_yaml(yaml_file, {"test": "value"})

        assert yaml_file.exists()
        assert read_yaml(yaml_file) == {"test": "value"}

    def test_update_yaml_convenience(self, tmp_path):
        """Test update_yaml convenience function."""
        yaml_file = tmp_path / "test.yml"
        write_yaml(yaml_file, {"a": 1})

        result = update_yaml(yaml_file, {"b": 2})

        assert result == {"a": 1, "b": 2}
