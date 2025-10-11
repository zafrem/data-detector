"""YAML file read/write utilities for data-detector."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)


class YAMLHandler:
    """Handler for reading and writing YAML files."""

    @staticmethod
    def read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Read YAML file and return contents as dictionary.

        Args:
            file_path: Path to YAML file

        Returns:
            Dictionary containing YAML contents

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid or not a dictionary
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in {path}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML file to contain a dict, got {type(data)}")

        logger.info(f"Successfully read YAML file: {path}")
        return data

    @staticmethod
    def write_yaml(
        file_path: Union[str, Path],
        data: Dict[str, Any],
        overwrite: bool = False,
        sort_keys: bool = False,
    ) -> None:
        """
        Write dictionary to YAML file.

        Args:
            file_path: Path to output YAML file
            data: Dictionary to write
            overwrite: If True, overwrite existing file
            sort_keys: If True, sort dictionary keys alphabetically

        Raises:
            FileExistsError: If file exists and overwrite=False
            ValueError: If data is not a dictionary
        """
        path = Path(file_path)

        if not isinstance(data, dict):
            raise ValueError(f"Data must be a dictionary, got {type(data)}")

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"File already exists: {path}. Use overwrite=True to overwrite."
            )

        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=sort_keys,
                indent=2,
            )

        logger.info(f"Successfully wrote YAML file: {path}")

    @staticmethod
    def update_yaml(
        file_path: Union[str, Path],
        updates: Dict[str, Any],
        merge: bool = True,
    ) -> Dict[str, Any]:
        """
        Update existing YAML file with new data.

        Args:
            file_path: Path to YAML file
            updates: Dictionary with updates to apply
            merge: If True, merge with existing data. If False, replace completely.

        Returns:
            Updated dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if merge:
            existing_data = YAMLHandler.read_yaml(path)
            existing_data.update(updates)
            data = existing_data
        else:
            data = updates

        YAMLHandler.write_yaml(path, data, overwrite=True)
        return data


class PatternFileHandler:
    """Handler for creating and managing pattern YAML files."""

    @staticmethod
    def create_pattern_file(
        file_path: Union[str, Path],
        namespace: str,
        description: str,
        patterns: Optional[List[Dict[str, Any]]] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Create a new pattern YAML file.

        Args:
            file_path: Path to output file
            namespace: Pattern namespace
            description: Description of the pattern file
            patterns: List of pattern definitions
            overwrite: If True, overwrite existing file

        Example:
            >>> PatternFileHandler.create_pattern_file(
            ...     "my_patterns.yml",
            ...     namespace="custom",
            ...     description="My custom patterns",
            ...     patterns=[{
            ...         "id": "email_01",
            ...         "location": "custom",
            ...         "category": "email",
            ...         "description": "Email pattern",
            ...         "pattern": r"[a-z]+@[a-z]+\\.com",
            ...         "mask": "***@***.***",
            ...         "policy": {
            ...             "store_raw": False,
            ...             "action_on_match": "redact",
            ...             "severity": "medium"
            ...         }
            ...     }]
            ... )
        """
        data = {
            "namespace": namespace,
            "description": description,
            "patterns": patterns or [],
        }

        YAMLHandler.write_yaml(file_path, data, overwrite=overwrite)
        logger.info(f"Created pattern file: {file_path}")

    @staticmethod
    def add_pattern_to_file(
        file_path: Union[str, Path],
        pattern: Dict[str, Any],
    ) -> None:
        """
        Add a pattern to an existing pattern file.

        Args:
            file_path: Path to pattern file
            pattern: Pattern definition to add

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If pattern is invalid
        """
        # Validate required fields
        required_fields = ["id", "location", "category", "pattern", "policy"]
        missing = [f for f in required_fields if f not in pattern]
        if missing:
            raise ValueError(f"Pattern missing required fields: {missing}")

        # Read existing file
        data = YAMLHandler.read_yaml(file_path)

        if "patterns" not in data:
            data["patterns"] = []

        # Check for duplicate pattern ID
        pattern_ids = [p.get("id") for p in data["patterns"]]
        if pattern["id"] in pattern_ids:
            logger.warning(
                f"Pattern {pattern['id']} already exists in {file_path}, will be added anyway"
            )

        # Add pattern
        data["patterns"].append(pattern)

        # Write back
        YAMLHandler.write_yaml(file_path, data, overwrite=True)
        logger.info(f"Added pattern {pattern['id']} to {file_path}")

    @staticmethod
    def remove_pattern_from_file(
        file_path: Union[str, Path],
        pattern_id: str,
    ) -> bool:
        """
        Remove a pattern from a pattern file.

        Args:
            file_path: Path to pattern file
            pattern_id: ID of pattern to remove

        Returns:
            True if pattern was removed, False if not found

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        data = YAMLHandler.read_yaml(file_path)

        if "patterns" not in data:
            return False

        # Find and remove pattern
        original_count = len(data["patterns"])
        data["patterns"] = [p for p in data["patterns"] if p.get("id") != pattern_id]

        if len(data["patterns"]) == original_count:
            logger.warning(f"Pattern {pattern_id} not found in {file_path}")
            return False

        # Write back
        YAMLHandler.write_yaml(file_path, data, overwrite=True)
        logger.info(f"Removed pattern {pattern_id} from {file_path}")
        return True

    @staticmethod
    def update_pattern_in_file(
        file_path: Union[str, Path],
        pattern_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update a pattern in a pattern file.

        Args:
            file_path: Path to pattern file
            pattern_id: ID of pattern to update
            updates: Dictionary of fields to update

        Returns:
            True if pattern was updated, False if not found

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        data = YAMLHandler.read_yaml(file_path)

        if "patterns" not in data:
            return False

        # Find and update pattern
        found = False
        for pattern in data["patterns"]:
            if pattern.get("id") == pattern_id:
                pattern.update(updates)
                found = True
                break

        if not found:
            logger.warning(f"Pattern {pattern_id} not found in {file_path}")
            return False

        # Write back
        YAMLHandler.write_yaml(file_path, data, overwrite=True)
        logger.info(f"Updated pattern {pattern_id} in {file_path}")
        return True

    @staticmethod
    def get_pattern_from_file(
        file_path: Union[str, Path],
        pattern_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern from a pattern file.

        Args:
            file_path: Path to pattern file
            pattern_id: ID of pattern to retrieve

        Returns:
            Pattern dictionary if found, None otherwise
        """
        data = YAMLHandler.read_yaml(file_path)

        if "patterns" not in data:
            return None

        for pattern in data["patterns"]:
            if pattern.get("id") == pattern_id:
                return pattern

        return None

    @staticmethod
    def list_patterns_in_file(
        file_path: Union[str, Path],
    ) -> List[str]:
        """
        List all pattern IDs in a pattern file.

        Args:
            file_path: Path to pattern file

        Returns:
            List of pattern IDs
        """
        data = YAMLHandler.read_yaml(file_path)

        if "patterns" not in data:
            return []

        return [p.get("id", "unknown") for p in data["patterns"]]


# Convenience functions
def read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Read YAML file. Convenience wrapper for YAMLHandler.read_yaml()."""
    return YAMLHandler.read_yaml(file_path)


def write_yaml(
    file_path: Union[str, Path],
    data: Dict[str, Any],
    overwrite: bool = False,
    sort_keys: bool = False,
) -> None:
    """Write YAML file. Convenience wrapper for YAMLHandler.write_yaml()."""
    YAMLHandler.write_yaml(file_path, data, overwrite=overwrite, sort_keys=sort_keys)


def update_yaml(
    file_path: Union[str, Path],
    updates: Dict[str, Any],
    merge: bool = True,
) -> Dict[str, Any]:
    """Update YAML file. Convenience wrapper for YAMLHandler.update_yaml()."""
    return YAMLHandler.update_yaml(file_path, updates, merge=merge)
