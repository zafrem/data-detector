#!/usr/bin/env python3
"""
Utility functions for YAML pattern file management examples.

This module provides reusable functions that demonstrate various
YAML utilities for pattern file management without creating files
in the current directory.
"""

import os
import tempfile
from typing import Dict, List, Any, Optional

from datadetector import (
    Engine,
    PatternFileHandler,
    load_registry,
    read_yaml,
    write_yaml,
)


class YAMLPatternManager:
    """A utility class for managing YAML pattern files in examples."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize with optional temporary directory."""
        self.temp_dir = temp_dir or tempfile.mkdtemp()
        self.pattern_file = os.path.join(self.temp_dir, "custom_patterns.yml")
        self.backup_file = os.path.join(self.temp_dir, "custom_patterns.backup.yml")
    
    def get_sample_patterns(self) -> List[Dict[str, Any]]:
        """Get sample patterns for demonstration."""
        return [
            {
                "id": "api_key_01",
                "location": "custom",
                "category": "token",
                "description": "Custom API key format",
                "pattern": r"APIKEY-[A-Z0-9]{32}",
                "mask": "APIKEY-" + "*" * 32,
                "examples": {
                    "match": ["APIKEY-ABC123XYZ789ABC123XYZ789ABC123"],
                    "nomatch": ["APIKEY-SHORT", "API-KEY-ABC123"],
                },
                "policy": {"store_raw": False, "action_on_match": "redact", "severity": "critical"},
            },
            {
                "id": "internal_id_01",
                "location": "custom",
                "category": "other",
                "description": "Internal user ID",
                "pattern": r"USR-\d{8}",
                "mask": "USR-********",
                "policy": {"store_raw": False, "action_on_match": "redact", "severity": "medium"},
            },
        ]
    
    def create_pattern_file(self) -> Dict[str, Any]:
        """Create a new pattern file from scratch."""
        patterns = self.get_sample_patterns()
        
        PatternFileHandler.create_pattern_file(
            file_path=self.pattern_file,
            namespace="custom",
            description="Custom patterns for our application",
            patterns=patterns,
            overwrite=True,
        )
        
        data = read_yaml(self.pattern_file)
        return {
            "file_path": self.pattern_file,
            "namespace": data["namespace"],
            "description": data["description"],
            "pattern_count": len(data["patterns"])
        }
    
    def add_pattern(self) -> Dict[str, Any]:
        """Add a new pattern to existing file."""
        new_pattern = {
            "id": "session_token_01",
            "location": "custom",
            "category": "token",
            "description": "Session token",
            "pattern": r"SESSION_[A-F0-9]{40}",
            "mask": "SESSION_" + "*" * 40,
            "policy": {"store_raw": False, "action_on_match": "redact", "severity": "high"},
        }
        
        PatternFileHandler.add_pattern_to_file(self.pattern_file, new_pattern)
        
        pattern_ids = PatternFileHandler.list_patterns_in_file(self.pattern_file)
        return {
            "added_pattern": "session_token_01",
            "total_patterns": len(pattern_ids),
            "pattern_ids": pattern_ids
        }
    
    def update_pattern(self, pattern_id: str = "api_key_01") -> Dict[str, Any]:
        """Update an existing pattern."""
        # Get current pattern
        current = PatternFileHandler.get_pattern_from_file(self.pattern_file, pattern_id)
        current_severity = current["policy"]["severity"]
        
        # Update severity
        success = PatternFileHandler.update_pattern_in_file(
            file_path=self.pattern_file,
            pattern_id=pattern_id,
            updates={"policy": {"severity": "critical", "action_on_match": "tokenize"}},
        )
        
        if success:
            updated = PatternFileHandler.get_pattern_from_file(self.pattern_file, pattern_id)
            return {
                "success": True,
                "pattern_id": pattern_id,
                "old_severity": current_severity,
                "new_severity": updated["policy"]["severity"],
                "new_action": updated["policy"]["action_on_match"]
            }
        
        return {"success": False, "pattern_id": pattern_id}
    
    def query_patterns(self) -> List[Dict[str, Any]]:
        """Query and inspect patterns."""
        pattern_ids = PatternFileHandler.list_patterns_in_file(self.pattern_file)
        patterns_info = []
        
        for pid in pattern_ids:
            pattern = PatternFileHandler.get_pattern_from_file(self.pattern_file, pid)
            patterns_info.append({
                "id": pid,
                "category": pattern["category"],
                "description": pattern["description"],
                "severity": pattern["policy"]["severity"],
                "pattern": pattern["pattern"]
            })
        
        return patterns_info
    
    def test_with_engine(self) -> Dict[str, Any]:
        """Use custom patterns with detection engine."""
        # Load custom patterns (skip example validation for demo)
        registry = load_registry(
            paths=[self.pattern_file], 
            validate_schema=False, 
            validate_examples=False
        )
        
        # Create engine
        engine = Engine(registry)
        
        # Test detection
        test_text = """
        Here are some sensitive items:
        - API Key: APIKEY-ABC123XYZ789ABC123XYZ789ABC123
        - User ID: USR-12345678
        - Session: SESSION_1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B
        """
        
        # Find PII
        result = engine.find(test_text, namespaces=["custom"])
        
        # Redact PII
        redacted = engine.redact(test_text, namespaces=["custom"])
        
        matches_info = []
        for match in result.matches:
            matches_info.append({
                "pattern_id": match.pattern_id,
                "category": match.category.value,
                "position": f"{match.start}-{match.end}",
                "severity": match.severity.value
            })
        
        return {
            "registry_size": len(registry),
            "text_length": len(test_text),
            "match_count": result.match_count,
            "namespaces_searched": result.namespaces_searched,
            "matches": matches_info,
            "redacted_text": redacted.redacted_text,
            "redaction_count": redacted.redaction_count
        }
    
    def remove_pattern(self, pattern_id: str = "internal_id_01") -> Dict[str, Any]:
        """Remove a pattern."""
        success = PatternFileHandler.remove_pattern_from_file(
            self.pattern_file, pattern_id
        )
        
        if success:
            pattern_ids = PatternFileHandler.list_patterns_in_file(self.pattern_file)
            return {
                "success": True,
                "removed_pattern": pattern_id,
                "remaining_patterns": pattern_ids
            }
        
        return {"success": False, "pattern_id": pattern_id}
    
    def backup_and_restore(self) -> Dict[str, Any]:
        """Backup and restore pattern files."""
        # Read current state
        current = read_yaml(self.pattern_file)
        
        # Create backup
        write_yaml(self.backup_file, current, overwrite=True)
        
        # Simulate modification
        temp_pattern = {
            "id": "temp_pattern_01",
            "location": "custom",
            "category": "other",
            "pattern": "temp",
            "policy": {"store_raw": False, "action_on_match": "redact", "severity": "low"},
        }
        
        PatternFileHandler.add_pattern_to_file(self.pattern_file, temp_pattern)
        patterns_after_add = PatternFileHandler.list_patterns_in_file(self.pattern_file)
        
        # Restore from backup
        backup = read_yaml(self.backup_file)
        write_yaml(self.pattern_file, backup, overwrite=True)
        patterns_after_restore = PatternFileHandler.list_patterns_in_file(self.pattern_file)
        
        return {
            "backup_file": self.backup_file,
            "patterns_after_add": patterns_after_add,
            "patterns_after_restore": patterns_after_restore,
            "temp_pattern_added": "temp_pattern_01" in patterns_after_add,
            "temp_pattern_removed": "temp_pattern_01" not in patterns_after_restore
        }
    
    def cleanup(self) -> List[str]:
        """Clean up temporary files."""
        cleaned_files = []
        
        for file_path in [self.pattern_file, self.backup_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
                cleaned_files.append(file_path)
        
        # Try to remove temp directory if empty
        try:
            os.rmdir(self.temp_dir)
            cleaned_files.append(self.temp_dir)
        except OSError:
            pass  # Directory not empty or doesn't exist
        
        return cleaned_files


def run_all_examples() -> Dict[str, Any]:
    """Run all YAML utility examples and return results."""
    manager = YAMLPatternManager()
    results = {}
    
    try:
        results["create_file"] = manager.create_pattern_file()
        results["add_pattern"] = manager.add_pattern()
        results["update_pattern"] = manager.update_pattern()
        results["query_patterns"] = manager.query_patterns()
        results["engine_test"] = manager.test_with_engine()
        results["remove_pattern"] = manager.remove_pattern()
        results["backup_restore"] = manager.backup_and_restore()
        
        return results
        
    finally:
        results["cleanup"] = manager.cleanup()
        return results
