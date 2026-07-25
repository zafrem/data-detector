"""
Transformer-based NER detector for PII detection.

Provides a complementary detection path using pre-trained token classification
models from HuggingFace Transformers. Runs alongside regex pattern matching
to improve recall for PII entities that regex patterns might miss.

Requires optional dependency: pip install data-detector[transformer]
"""

import logging
from typing import Any, Dict, List, Optional, Union

from datadetector.models import Category, Match, Severity, TransformerConfig

logger = logging.getLogger(__name__)

# Graceful degradation -- same pattern as nlp.py
try:
    from transformers import pipeline as hf_pipeline  # type: ignore[import-untyped]

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.debug("transformers not available - NER detection disabled")

# Mapping from common NER entity labels to data-detector Category enum.
# Handles label schemes from popular models:
#   dslim/bert-base-NER, lakshyakh93/deberta_finetuned_pii, etc.
NER_LABEL_TO_CATEGORY: Dict[str, Category] = {
    "PER": Category.NAME,
    "PERSON": Category.NAME,
    "NAME": Category.NAME,
    "LOC": Category.LOCATION,
    "LOCATION": Category.LOCATION,
    "ADDRESS": Category.ADDRESS,
    "STREET_ADDRESS": Category.ADDRESS,
    "EMAIL": Category.EMAIL,
    "PHONE": Category.PHONE,
    "PHONE_NUM": Category.PHONE,
    "SSN": Category.SSN,
    "CREDIT_CARD": Category.CREDIT_CARD,
    "ID_NUM": Category.IDENTIFICATION,
    "DATE_OF_BIRTH": Category.DATE_OF_BIRTH,
    "IP_ADDRESS": Category.IP,
}

# Default severity for NER-detected entities by category
NER_CATEGORY_SEVERITY: Dict[Category, Severity] = {
    Category.NAME: Severity.MEDIUM,
    Category.LOCATION: Severity.LOW,
    Category.ADDRESS: Severity.HIGH,
    Category.EMAIL: Severity.MEDIUM,
    Category.PHONE: Severity.HIGH,
    Category.SSN: Severity.CRITICAL,
    Category.CREDIT_CARD: Severity.CRITICAL,
    Category.IDENTIFICATION: Severity.HIGH,
    Category.DATE_OF_BIRTH: Severity.MEDIUM,
    Category.IP: Severity.LOW,
}


class TransformerNERDetector:
    """
    NER-based PII detector using HuggingFace Transformer models.

    Lazily loads the model on first call to detect(). If the transformers
    package is not installed, all calls gracefully return empty results.
    """

    def __init__(self, config: TransformerConfig) -> None:
        self.config = config
        self._pipeline: Union[Any, bool, None] = None  # None=not loaded, False=failed
        self._label_map: Dict[str, Category] = dict(NER_LABEL_TO_CATEGORY)

    def _ensure_pipeline(self) -> bool:
        """Load the NER pipeline on first use. Returns False if unavailable."""
        if self._pipeline is not None:
            return self._pipeline is not False

        if not TRANSFORMERS_AVAILABLE:
            logger.warning("transformers not installed, NER detection disabled")
            self._pipeline = False
            return False

        try:
            device_arg = -1 if self.config.device == "cpu" else self.config.device
            self._pipeline = hf_pipeline(
                "token-classification",
                model=self.config.ner_model,
                device=device_arg,
                aggregation_strategy="simple",
            )
            logger.info(f"Loaded NER model: {self.config.ner_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to load NER model '{self.config.ner_model}': {e}")
            self._pipeline = False
            return False

    def detect(self, text: str) -> List[Match]:
        """
        Run NER on text and return Match objects for detected entities.

        Args:
            text: Input text to scan

        Returns:
            List of Match objects with detection_method="ner"
        """
        if self._pipeline is False:
            return []
        if not self._ensure_pipeline():
            return []

        try:
            entities = self._pipeline(text)
        except Exception as e:
            logger.error(f"NER inference failed: {e}")
            return []

        matches: List[Match] = []
        for ent in entities:
            # Filter by confidence threshold
            if ent["score"] < self.config.ner_confidence_threshold:
                continue

            # Normalize label: strip B-/I- prefixes, uppercase
            label = ent["entity_group"].upper().replace("B-", "").replace("I-", "")
            category = self._label_map.get(label)
            if category is None:
                continue  # Unknown entity type, skip

            severity = NER_CATEGORY_SEVERITY.get(category, Severity.MEDIUM)

            match = Match(
                ns_id=f"ner/{label.lower()}",
                pattern_id=f"ner_{label.lower()}",
                namespace="ner",
                category=category,
                start=ent["start"],
                end=ent["end"],
                matched_text=ent.get("word"),
                severity=severity,
                score=self.config.ner_score,
                context_evidence=[
                    f"NER:{self.config.ner_model} (conf={ent['score']:.3f})"
                ],
                detection_method="ner",
            )
            matches.append(match)

        return matches
