"""Tests for RAG policy configuration loader."""

import yaml

from datadetector.models import RedactionStrategy
from datadetector.rag_config import RAGPolicyConfig, load_rag_policy
from datadetector.rag_models import SecurityAction, SecurityLayer, SeverityLevel


class TestRAGPolicyConfig:
    """Test RAG policy configuration."""

    def test_init_with_nonexistent_path_uses_defaults(self):
        """Test that nonexistent config path uses defaults."""
        config = RAGPolicyConfig("/nonexistent/path/config.yml")
        assert config.config is not None
        assert "input_layer" in config.config
        assert "storage_layer" in config.config
        assert "output_layer" in config.config

    def test_init_with_none_path_tries_default(self):
        """Test that None path tries default location."""
        config = RAGPolicyConfig(None)
        # Should either load default or use fallback defaults
        assert config.config is not None

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "input_layer": {
                "enabled": True,
                "action": "block",
                "severity_threshold": "high",
                "redaction_strategy": "hash",
                "log_matches": False,
            },
            "storage_layer": {
                "enabled": False,
                "action": "allow",
            },
            "output_layer": {
                "enabled": True,
                "action": "sanitize",
                "severity_threshold": "low",
                "redaction_strategy": "mask",
                "log_matches": True,
                "allow_detokenization": True,
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        assert config.config == config_data

    def test_load_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML."""
        config_file = tmp_path / "invalid.yml"
        config_file.write_text("invalid: yaml: content: [")

        config = RAGPolicyConfig(str(config_file))
        # Should fall back to defaults
        assert "input_layer" in config.config
        assert config.config["input_layer"]["enabled"] is True

    def test_get_input_policy_enabled(self, tmp_path):
        """Test getting input layer policy when enabled."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "input_layer": {
                "enabled": True,
                "action": "sanitize",
                "severity_threshold": "medium",
                "redaction_strategy": "mask",
                "log_matches": True,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        policy = config.get_input_policy()

        assert policy.layer == SecurityLayer.INPUT
        assert policy.action == SecurityAction.SANITIZE
        assert policy.severity_threshold == SeverityLevel.MEDIUM
        assert policy.redaction_strategy == RedactionStrategy.MASK
        assert policy.log_matches is True

    def test_get_input_policy_disabled(self, tmp_path):
        """Test getting input layer policy when disabled."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "input_layer": {
                "enabled": False,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        policy = config.get_input_policy()

        assert policy.layer == SecurityLayer.INPUT
        assert policy.action == SecurityAction.ALLOW

    def test_get_storage_policy_enabled(self, tmp_path):
        """Test getting storage layer policy when enabled."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "storage_layer": {
                "enabled": True,
                "action": "sanitize",
                "severity_threshold": "low",
                "redaction_strategy": "tokenize",
                "log_matches": True,
                "preserve_format": True,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        policy = config.get_storage_policy()

        assert policy.layer == SecurityLayer.STORAGE
        assert policy.action == SecurityAction.SANITIZE
        assert policy.severity_threshold == SeverityLevel.LOW
        assert policy.redaction_strategy == RedactionStrategy.TOKENIZE
        assert policy.log_matches is True
        assert policy.preserve_format is True

    def test_get_storage_policy_disabled(self, tmp_path):
        """Test getting storage layer policy when disabled."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "storage_layer": {
                "enabled": False,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        policy = config.get_storage_policy()

        assert policy.layer == SecurityLayer.STORAGE
        assert policy.action == SecurityAction.ALLOW

    def test_get_output_policy_enabled(self, tmp_path):
        """Test getting output layer policy when enabled."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "output_layer": {
                "enabled": True,
                "action": "block",
                "severity_threshold": "high",
                "redaction_strategy": "mask",
                "log_matches": True,
                "allow_detokenization": False,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        policy = config.get_output_policy()

        assert policy.layer == SecurityLayer.OUTPUT
        assert policy.action == SecurityAction.BLOCK
        assert policy.severity_threshold == SeverityLevel.HIGH
        assert policy.redaction_strategy == RedactionStrategy.MASK
        assert policy.log_matches is True
        assert policy.allow_detokenization is False

    def test_get_output_policy_disabled(self, tmp_path):
        """Test getting output layer policy when disabled."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "output_layer": {
                "enabled": False,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        policy = config.get_output_policy()

        assert policy.layer == SecurityLayer.OUTPUT
        assert policy.action == SecurityAction.ALLOW

    def test_get_namespaces_configured(self, tmp_path):
        """Test getting configured namespaces for a layer."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "input_layer": {
                "enabled": True,
                "namespaces": ["kr", "us", "comm"],
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        namespaces = config.get_namespaces(SecurityLayer.INPUT)

        assert namespaces == ["kr", "us", "comm"]

    def test_get_namespaces_not_configured(self, tmp_path):
        """Test getting namespaces when not configured."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "input_layer": {
                "enabled": True,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        namespaces = config.get_namespaces(SecurityLayer.INPUT)

        assert namespaces is None

    def test_get_global_setting_exists(self, tmp_path):
        """Test getting a global setting that exists."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "global": {
                "max_tokens": 1000,
                "enable_logging": True,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        max_tokens = config.get_global_setting("max_tokens")
        enable_logging = config.get_global_setting("enable_logging")

        assert max_tokens == 1000
        assert enable_logging is True

    def test_get_global_setting_not_exists(self, tmp_path):
        """Test getting a global setting that doesn't exist."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "global": {
                "max_tokens": 1000,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        result = config.get_global_setting("nonexistent", "default_value")

        assert result == "default_value"

    def test_get_global_setting_no_global_section(self, tmp_path):
        """Test getting global setting when no global section exists."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "input_layer": {
                "enabled": True,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = RAGPolicyConfig(str(config_file))
        result = config.get_global_setting("anything", "default")

        assert result == "default"

    def test_load_rag_policy_function(self, tmp_path):
        """Test the load_rag_policy convenience function."""
        config_file = tmp_path / "policy.yml"
        config_data = {
            "input_layer": {
                "enabled": True,
                "action": "block",
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        policy = load_rag_policy(str(config_file))

        assert isinstance(policy, RAGPolicyConfig)
        assert policy.config["input_layer"]["action"] == "block"

    def test_use_defaults(self):
        """Test that default configuration is properly set."""
        config = RAGPolicyConfig("/nonexistent/path.yml")

        assert config.config["input_layer"]["enabled"] is True
        assert config.config["input_layer"]["action"] == "sanitize"
        assert config.config["storage_layer"]["enabled"] is True
        assert config.config["storage_layer"]["action"] == "sanitize"
        assert config.config["output_layer"]["enabled"] is True
        assert config.config["output_layer"]["action"] == "block"
