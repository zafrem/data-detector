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
    DATE_OF_BIRTH = "date_of_birth"
    IDENTIFICATION = "identification"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    DEVICE = "device"
    VEHICLE = "vehicle"
    TOKENS = "tokens"
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
    FAKE = "fake"  # Replace with realistic fake data


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
    match_type: str = "contains"  # "contains" (default) or "exactly_matches"

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
    score: float = 0.5  # Confidence score (0.0-1.0)
    verified: bool = False  # True if passed a verification function (Luhn, checksum, etc.)
    context_evidence: List[str] = field(default_factory=list)  # Found context keywords
    detection_method: str = "regex"  # "regex", "ner", or "regex+ner" for merged

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


@dataclass
class ScoringConfig:
    """Configuration for PII detection weights and scoring."""

    # Initial scores
    initial_verified: float = 0.95
    initial_unverified: float = 0.50

    # Keyword proximity boosts
    keyword_window: int = 60
    # Before match
    keyword_pre_close_boost: float = 0.45  # < 10 chars
    keyword_pre_far_boost: float = 0.30    # < 30 chars
    keyword_pre_weak_boost: float = 0.10   # > 30 chars
    # After match
    keyword_post_close_boost: float = 0.40  # < 10 chars
    keyword_post_far_boost: float = 0.25    # < 30 chars
    keyword_post_weak_boost: float = 0.10   # > 30 chars

    # ML weights (TransformerConfig also has some, but we consolidate logic here)
    ml_category_boost: float = 0.15
    ner_corroboration_boost: float = 0.15

    # Filtering
    min_score: float = 0.0  # Filter results below this score
    filter_placeholders: bool = True  # Filter out test/placeholder data (010-1234-5678, test@example.com)


@dataclass
class TransformerConfig:
    """Configuration for Transformer-based detection features."""

    # Way 1: NER-based detection
    enable_ner: bool = False
    ner_model: str = "dslim/bert-base-NER"
    ner_confidence_threshold: float = 0.7
    ner_score: float = 0.6

    # Way 2: Context classification
    enable_context_classifier: bool = False
    context_model: str = "facebook/bart-large-mnli"
    context_window_chars: int = 100
    context_confidence_threshold: float = 0.5
    context_max_boost: float = 0.35
    context_penalty: float = 0.2

    # Fine-tuned model paths (use local models instead of generic zero-shot)
    # Set these after running: python -m datadetector.training.train_pii_classifier
    binary_model_path: str = ""    # Path to fine-tuned binary PII classifier
    category_model_path: str = ""  # Path to fine-tuned category classifier

    # Shared settings
    device: str = "cpu"
    batch_size: int = 8

    def is_ner_enabled(self) -> bool:
        """Check if NER detection is enabled."""
        return self.enable_ner

    def is_context_enabled(self) -> bool:
        """Check if context classification is enabled."""
        return self.enable_context_classifier

    def is_enabled(self) -> bool:
        """Check if any transformer feature is enabled."""
        return self.enable_ner or self.enable_context_classifier
