"""RAG security policy configuration loader."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from datadetector.models import RedactionStrategy
from datadetector.rag_models import SecurityAction, SecurityLayer, SecurityPolicy, SeverityLevel

logger = logging.getLogger(__name__)


class RAGPolicyConfig:
    """
    RAG security policy configuration.

    Loads and manages security policies from YAML configuration.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize policy configuration.

        Args:
            config_path: Path to YAML config file. If None, uses default.
        """
        if config_path is None:
            # Use default config
            config_path = Path(__file__).parent.parent.parent / "config" / "rag_security_policy.yml"

        self.config_path = Path(config_path)
        self.config: Dict = {}
        self.load()

    def load(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self._use_defaults()
            return

        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded RAG security policy from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            self._use_defaults()

    def _use_defaults(self) -> None:
        """Use default configuration."""
        self.config = {
            "input_layer": {
                "enabled": True,
                "action": "sanitize",
                "severity_threshold": "medium",
                "redaction_strategy": "mask",
                "log_matches": True,
            },
            "storage_layer": {
                "enabled": True,
                "action": "sanitize",
                "severity_threshold": "low",
                "redaction_strategy": "tokenize",
                "preserve_format": True,
                "log_matches": True,
            },
            "output_layer": {
                "enabled": True,
                "action": "block",
                "severity_threshold": "high",
                "redaction_strategy": "mask",
                "log_matches": True,
            },
        }

    def get_input_policy(self) -> SecurityPolicy:
        """Get input layer security policy."""
        layer_config = self.config.get("input_layer", {})

        if not layer_config.get("enabled", True):
            # Disabled layer - allow everything
            return SecurityPolicy(
                layer=SecurityLayer.INPUT,
                action=SecurityAction.ALLOW,
            )

        return SecurityPolicy(
            layer=SecurityLayer.INPUT,
            action=SecurityAction(layer_config.get("action", "sanitize")),
            severity_threshold=SeverityLevel(layer_config.get("severity_threshold", "medium")),
            redaction_strategy=RedactionStrategy(layer_config.get("redaction_strategy", "mask")),
            log_matches=layer_config.get("log_matches", True),
        )

    def get_storage_policy(self) -> SecurityPolicy:
        """Get storage layer security policy."""
        layer_config = self.config.get("storage_layer", {})

        if not layer_config.get("enabled", True):
            return SecurityPolicy(
                layer=SecurityLayer.STORAGE,
                action=SecurityAction.ALLOW,
            )

        return SecurityPolicy(
            layer=SecurityLayer.STORAGE,
            action=SecurityAction(layer_config.get("action", "sanitize")),
            severity_threshold=SeverityLevel(layer_config.get("severity_threshold", "low")),
            redaction_strategy=RedactionStrategy(
                layer_config.get("redaction_strategy", "tokenize")
            ),
            log_matches=layer_config.get("log_matches", True),
            preserve_format=layer_config.get("preserve_format", True),
        )

    def get_output_policy(self) -> SecurityPolicy:
        """Get output layer security policy."""
        layer_config = self.config.get("output_layer", {})

        if not layer_config.get("enabled", True):
            return SecurityPolicy(
                layer=SecurityLayer.OUTPUT,
                action=SecurityAction.ALLOW,
            )

        return SecurityPolicy(
            layer=SecurityLayer.OUTPUT,
            action=SecurityAction(layer_config.get("action", "block")),
            severity_threshold=SeverityLevel(layer_config.get("severity_threshold", "high")),
            redaction_strategy=RedactionStrategy(layer_config.get("redaction_strategy", "mask")),
            log_matches=layer_config.get("log_matches", True),
            allow_detokenization=layer_config.get("allow_detokenization", False),
        )

    def get_namespaces(self, layer: SecurityLayer) -> Optional[List[str]]:
        """
        Get configured namespaces for a layer.

        Args:
            layer: Security layer

        Returns:
            List of namespace IDs or None for all
        """
        layer_key = f"{layer.value}_layer"
        layer_config = self.config.get(layer_key, {})
        return layer_config.get("namespaces")

    def get_global_setting(self, key: str, default=None):
        """
        Get global configuration setting.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value
        """
        global_config = self.config.get("global", {})
        return global_config.get(key, default)


def load_rag_policy(config_path: Optional[str] = None) -> RAGPolicyConfig:
    """
    Load RAG security policy from YAML configuration.

    Args:
        config_path: Path to config file (optional)

    Returns:
        RAGPolicyConfig instance

    Example:
        >>> policy = load_rag_policy("custom_policy.yml")
        >>> input_policy = policy.get_input_policy()
        >>> print(input_policy.action)
        sanitize
    """
    return RAGPolicyConfig(config_path)
