"""Models for RAG security integration."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from datadetector.models import Match, RedactionStrategy


class SecurityLayer(str, Enum):
    """RAG security layers."""

    INPUT = "input"  # User query scanning
    STORAGE = "storage"  # Document indexing scanning
    OUTPUT = "output"  # LLM response scanning


class SecurityAction(str, Enum):
    """Actions to take when PII is detected."""

    BLOCK = "block"  # Block the operation entirely
    WARN = "warn"  # Log warning but allow
    SANITIZE = "sanitize"  # Remove/mask PII and continue
    ALLOW = "allow"  # Allow without modification


class SeverityLevel(str, Enum):
    """PII severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityPolicy:
    """Policy for PII handling in RAG systems."""

    layer: SecurityLayer
    action: SecurityAction
    severity_threshold: SeverityLevel = SeverityLevel.MEDIUM
    redaction_strategy: RedactionStrategy = RedactionStrategy.MASK
    log_matches: bool = True
    preserve_format: bool = True  # For tokenization
    allow_detokenization: bool = False  # For output layer

    def should_block(self, severity: str) -> bool:
        """
        Check if severity level should trigger blocking.

        Args:
            severity: Severity level from pattern match

        Returns:
            True if should block based on policy
        """
        severity_order = {
            "low": 0,
            "medium": 1,
            "high": 2,
            "critical": 3,
        }

        match_level = severity_order.get(severity.lower(), 0)
        threshold_level = severity_order.get(self.severity_threshold.value, 1)

        return match_level >= threshold_level


@dataclass
class TokenMap:
    """Secure token mapping for reversible PII masking."""

    tokens: Dict[str, str] = field(default_factory=dict)  # token -> original
    hash: Optional[str] = None  # Hash for secure storage
    encrypted: Optional[bytes] = None  # Encrypted mapping

    def add(self, token: str, original: str) -> None:
        """Add token mapping."""
        self.tokens[token] = original

    def reverse(self, token: str) -> Optional[str]:
        """Get original value for token."""
        return self.tokens.get(token)


@dataclass
class SecurityScanResult:
    """Result of security scan with policy applied."""

    original_text: str
    sanitized_text: str
    matches: List[Match]
    action_taken: SecurityAction
    blocked: bool
    layer: SecurityLayer
    reason: Optional[str] = None
    token_map: Optional[TokenMap] = None

    @property
    def has_pii(self) -> bool:
        """Check if PII was detected."""
        return len(self.matches) > 0

    @property
    def match_count(self) -> int:
        """Number of PII matches found."""
        return len(self.matches)


@dataclass
class QueryScanResult(SecurityScanResult):
    """Result for input layer query scanning."""

    pass


@dataclass
class DocumentScanResult(SecurityScanResult):
    """Result for storage layer document scanning."""

    chunk_id: Optional[int] = None
    total_chunks: Optional[int] = None


@dataclass
class ResponseScanResult(SecurityScanResult):
    """Result for output layer response scanning."""

    pass
