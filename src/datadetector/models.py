"""Data models for data-detector."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class Category(str, Enum):
    """PII category types."""

    PHONE = "phone"
    SSN = "ssn"
    RRN = "rrn"
    EMAIL = "email"
    BANK = "bank"
    PASSPORT = "passport"
    ADDRESS = "address"
    CREDIT_CARD = "credit_card"
    IP = "ip"
    NAME = "name"
    IBAN = "iban"
    LOCATION = "location"
    TOKEN = "token"
    OTHER = "other"


class ActionOnMatch(str, Enum):
    """Action to take when pattern matches."""

    REDACT = "redact"
    REPORT = "report"
    TOKENIZE = "tokenize"
    IGNORE = "ignore"


class Severity(str, Enum):
    """Severity level of PII type."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RedactionStrategy(str, Enum):
    """Strategy for redacting matched text."""

    MASK = "mask"
    HASH = "hash"
    TOKENIZE = "tokenize"


@dataclass
class Policy:
    """Pattern policy configuration."""

    store_raw: bool = False
    action_on_match: ActionOnMatch = ActionOnMatch.REDACT
    severity: Severity = Severity.MEDIUM


@dataclass
class Examples:
    """Pattern validation examples."""

    match: List[str] = field(default_factory=list)
    nomatch: List[str] = field(default_factory=list)


@dataclass
class Pattern:
    """Compiled pattern definition."""

    id: str
    namespace: str
    location: str
    category: Category
    pattern: str
    compiled: Any  # re.Pattern
    description: str = ""
    flags: List[str] = field(default_factory=list)
    mask: Optional[str] = None
    examples: Optional[Examples] = None
    policy: Policy = field(default_factory=Policy)
    metadata: Dict[str, Any] = field(default_factory=dict)
    verification: Optional[str] = None  # Name of verification function
    verification_func: Optional[Callable[[str], bool]] = None  # Compiled verification function
    priority: int = 100  # Search priority (lower = higher priority, default = 100)

    @property
    def full_id(self) -> str:
        """Return full namespace/id identifier."""
        return f"{self.namespace}/{self.id}"


@dataclass
class Match:
    """Single pattern match result."""

    ns_id: str  # Full namespace/id (e.g., "kr/mobile")
    pattern_id: str
    namespace: str
    category: Category
    start: int
    end: int
    matched_text: Optional[str] = None  # Only populated if policy allows
    mask: Optional[str] = None
    severity: Severity = Severity.MEDIUM

    @property
    def span(self) -> Tuple[int, int]:
        """Return (start, end) tuple."""
        return (self.start, self.end)


@dataclass
class FindResult:
    """Result from find operation."""

    text: str
    matches: List[Match] = field(default_factory=list)
    namespaces_searched: List[str] = field(default_factory=list)

    @property
    def has_matches(self) -> bool:
        """Return True if any matches found."""
        return len(self.matches) > 0

    @property
    def match_count(self) -> int:
        """Return number of matches."""
        return len(self.matches)


@dataclass
class ValidationResult:
    """Result from validate operation."""

    text: str
    ns_id: str
    is_valid: bool
    match: Optional[Match] = None


@dataclass
class RedactionResult:
    """Result from redact operation."""

    original_text: str
    redacted_text: str
    strategy: RedactionStrategy
    matches: List[Match] = field(default_factory=list)
    redaction_count: int = 0
