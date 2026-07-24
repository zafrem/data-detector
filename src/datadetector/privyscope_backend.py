"""
privyscope-backed NER detector for PII detection.

Provides a complementary detection path using the privyscope engine, vendored
as the `pii-ml-engine` submodule. privyscope is a two-stage hybrid pipeline:
a regex filter plus an optional ONNX BIOES/Viterbi NER stage, with per-text
multilingual routing.

It plugs into the same Engine slot as the HuggingFace NER backend
(TransformerNERDetector) and exposes the same `detect(text) -> List[Match]`
interface, so regex/NER merging and corroboration scoring are unchanged.

privyscope ships no language data on its own -- install the core plus at least
one language pack:

    pip install -e pii-ml-engine
    pip install privyscope-ko      # and/or privyscope-en
"""

import logging
from typing import Any, Dict, List, Union

from datadetector.models import Category, Match, PrivyscopeConfig, Severity

logger = logging.getLogger(__name__)

# Graceful degradation -- same pattern as nlp.py / transformer_ner.py
try:
    from privyscope import Privyscope  # type: ignore[import-not-found]

    PRIVYSCOPE_AVAILABLE = True
except ImportError:
    PRIVYSCOPE_AVAILABLE = False
    logger.debug("privyscope not available - privyscope detection disabled")


# privyscope's eight canonical entity codes (privyscope/_core/entities.py
# BASE_ENTITIES) mapped onto the data-detector Category enum.
PRIVYSCOPE_LABEL_TO_CATEGORY: Dict[str, Category] = {
    "PER": Category.NAME,  # Person name
    "PHONE": Category.PHONE,  # Phone number
    "ID_NUM": Category.IDENTIFICATION,  # National / govt ID
    "EMAIL": Category.EMAIL,  # Email address
    "LOC": Category.ADDRESS,  # Detailed address (not coarse location)
    "BANK": Category.BANK,  # Financial information
    "DATE": Category.DATE_OF_BIRTH,  # Private date
    "SECRET": Category.TOKEN,  # Credentials / secrets
}

# Default severity for privyscope-detected entities by category.
PRIVYSCOPE_CATEGORY_SEVERITY: Dict[Category, Severity] = {
    Category.NAME: Severity.MEDIUM,
    Category.PHONE: Severity.HIGH,
    Category.IDENTIFICATION: Severity.HIGH,
    Category.EMAIL: Severity.MEDIUM,
    Category.ADDRESS: Severity.HIGH,
    Category.BANK: Severity.HIGH,
    Category.DATE_OF_BIRTH: Severity.MEDIUM,
    Category.TOKEN: Severity.HIGH,
}


class PrivyscopeDetector:
    """
    PII detector backed by the privyscope engine.

    Lazily builds the engine on first call to detect(). If privyscope or a
    language pack is not installed, all calls gracefully return empty results.
    """

    def __init__(self, config: PrivyscopeConfig) -> None:
        self.config = config
        self._engine: Union[Any, bool, None] = None  # None=not loaded, False=failed
        self._label_map: Dict[str, Category] = dict(PRIVYSCOPE_LABEL_TO_CATEGORY)

    def _ensure_engine(self) -> bool:
        """Build the privyscope engine on first use. Returns False if unavailable."""
        if self._engine is not None:
            return self._engine is not False

        if not PRIVYSCOPE_AVAILABLE:
            logger.warning("privyscope not installed, privyscope detection disabled")
            self._engine = False
            return False

        try:
            if self.config.auto_language:
                self._engine = Privyscope.auto(
                    self.config.operating_point,
                    cache_dir=self.config.cache_dir,
                    regex_only=self.config.regex_only,
                )
                logger.info("Loaded privyscope engine (auto language routing)")
            else:
                self._engine = Privyscope.from_pretrained(
                    self.config.operating_point,
                    lang=self.config.lang,
                    cache_dir=self.config.cache_dir,
                    regex_only=self.config.regex_only,
                )
                _lang = self.config.lang or "sole installed"
                logger.info(f"Loaded privyscope engine (lang={_lang})")
            return True
        except Exception as e:
            # Most commonly: no language pack installed, or weights unavailable offline.
            logger.error(f"Failed to load privyscope engine: {e}")
            self._engine = False
            return False

    def detect(self, text: str) -> List[Match]:
        """
        Run privyscope on text and return Match objects for detected spans.

        Args:
            text: Input text to scan

        Returns:
            List of Match objects with detection_method="ner"
        """
        if self._engine is False:
            return []
        if not self._ensure_engine():
            return []

        try:
            result = self._engine.redact(text)
        except Exception as e:
            logger.error(f"privyscope inference failed: {e}")
            return []

        matches: List[Match] = []
        for span in result.detected_spans:
            label = span.label.upper()
            category = self._label_map.get(label)
            if category is None:
                continue  # Unknown entity type, skip

            severity = PRIVYSCOPE_CATEGORY_SEVERITY.get(category, Severity.MEDIUM)

            matches.append(
                Match(
                    ns_id=f"privyscope/{label.lower()}",
                    pattern_id=f"privyscope_{label.lower()}",
                    namespace="privyscope",
                    category=category,
                    start=span.start,
                    end=span.end,
                    matched_text=span.text,
                    severity=severity,
                    # privyscope spans carry no per-span confidence, so every
                    # span gets the configured backend score.
                    score=self.config.score,
                    context_evidence=[f"privyscope:{label}"],
                    detection_method="ner",
                )
            )

        return matches
