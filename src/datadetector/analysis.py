"""
Context analysis module for PII detection.

This module implements the third step of the detection pipeline: Contextual Analysis.
It validates and scores matches based on surrounding text, using:
1. Keyword Analysis (Deterministic)
2. ML/LLM Analysis (Future Extension)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from datadetector.heuristic import is_placeholder
from datadetector.models import Match, ScoringConfig, TransformerConfig

logger = logging.getLogger(__name__)


class ContextAnalyzer:
    """
    Analyzer for validating PII matches using context.

    Implements a pipeline of analysis steps:
    1. Keyword Check: Looks for related terms near the match
    2. ML/LLM Check: (Placeholder) Advanced semantic analysis
    """

    def __init__(
        self,
        context_dir: Optional[Path] = None,
        transformer_config: Optional[TransformerConfig] = None,
        scoring_config: Optional[ScoringConfig] = None,
    ):
        """
        Initialize ContextAnalyzer.

        Args:
            context_dir: Directory containing keyword YAML files.
                        If None, attempts to locate pii-pattern-engine/keyword.
            transformer_config: Optional Transformer config for ML context classification.
            scoring_config: Optional configuration for detection weights.
        """
        self.context_map: Dict[str, Set[str]] = {}  # category -> set of context phrases
        self._load_contexts(context_dir)

        self.scoring_config = scoring_config or ScoringConfig()

        # Way 2: ML context classifier (lazy-loaded)
        self._transformer_config = transformer_config
        self._auto_discover_models()
        self._classifier: Any = None  # None=not loaded, False=failed
        self._binary_pipeline: Any = None  # Fine-tuned binary classifier
        self._category_pipeline: Any = None  # Fine-tuned category classifier
        self._use_finetuned: bool = False  # Whether to use fine-tuned models

    def _get_project_root(self) -> Path:
        """Determine project root directory."""
        # src/datadetector/analysis.py -> src/datadetector -> src -> root
        root = Path(__file__).parent.parent.parent
        if (root / "pii-pattern-engine").exists():
            return root

        # Check standard locations
        candidates = [
            Path("/app"),
            Path.cwd(),
        ]
        for candidate in candidates:
            if (candidate / "pii-pattern-engine").exists():
                return candidate

        return root

    def _auto_discover_models(self) -> None:
        """Auto-discover fine-tuned transformer models in pii-engine if paths not set.

        Gracefully skips if pii-engine submodule is missing or not populated.
        """
        if self._transformer_config is None:
            return
        cfg = self._transformer_config
        if cfg.binary_model_path and cfg.category_model_path:
            return  # already explicitly configured

        root = self._get_project_root()
        model_base = root / "pii-engine" / "models" / "transformer"

        if not model_base.exists():
            logger.debug(
                "pii-engine/models/transformer/ not found — "
                "ML context classifiers will not be auto-loaded. "
                "Run 'git submodule update --init' or train models first."
            )
            return

        if not cfg.binary_model_path:
            binary_dir = model_base / "binary_classifier" / "final"
            if (binary_dir / "model.safetensors").exists():
                cfg.binary_model_path = str(binary_dir)
                logger.info(f"Auto-discovered binary model: {binary_dir}")

        if not cfg.category_model_path:
            category_dir = model_base / "category_classifier" / "final"
            if (category_dir / "model.safetensors").exists():
                cfg.category_model_path = str(category_dir)
                logger.info(f"Auto-discovered category model: {category_dir}")

    def _load_contexts(self, context_dir: Optional[Path]) -> None:
        """Load context keywords from YAML files."""
        if context_dir is None:
            root = self._get_project_root()
            context_dir = root / "pii-pattern-engine" / "keyword"

        if not context_dir.exists():
            logger.warning(f"Context directory not found: {context_dir}")
            return

        # Load all YAML files in the directory
        yaml_files = sorted(context_dir.glob("*.yml")) + sorted(context_dir.glob("*.yaml"))

        for file_path in yaml_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not data or "categories" not in data:
                        continue

                    # Parse categories and their contexts
                    for cat_name, cat_data in data["categories"].items():
                        if "contexts" in cat_data:
                            self._add_contexts(cat_name, cat_data["contexts"])

            except Exception as e:
                logger.error(f"Failed to load context file {file_path}: {e}")

        logger.info(f"Loaded contexts for {len(self.context_map)} categories")

    def _add_contexts(self, category: str, contexts: List[str]) -> None:
        """Add context phrases to a category."""
        if category not in self.context_map:
            self.context_map[category] = set()

        # Normalize and add contexts
        # We store them lowercase for case-insensitive matching
        for ctx in contexts:
            # Remove punctuation like ':' from "bank account:" for flexible matching
            clean_ctx = ctx.lower().replace(":", "").strip()
            if clean_ctx:
                self.context_map[category].add(clean_ctx)

    def analyze(self, text: str, matches: List[Match]) -> List[Match]:
        """
        Run the full context analysis pipeline on a list of matches.

        Args:
            text: The original text containing the matches
            matches: List of preliminary matches (from Regex+Verification)

        Returns:
            List of matches with updated scores and evidence
        """
        if not matches:
            return []

        # Step 0: Heuristic Placeholder Check
        # Fast filter for common test data (010-1234-5678, test@example.com, etc.)
        if self.scoring_config.filter_placeholders:
            filtered_matches = []
            for m in matches:
                val = m.matched_text or text[m.start : m.end]
                if is_placeholder(val, str(m.category.value)):
                    logger.debug(f"Filtered out placeholder match: {val} ({m.ns_id})")
                    continue
                filtered_matches.append(m)
            matches = filtered_matches

        if not matches:
            return []

        # Step 1: Keyword-based Context Check
        matches = self._keyword_context_check(text, matches)

        # Step 2: ML-based Context Check (Placeholder)
        matches = self._ml_context_check(text, matches)

        # Step 3: LLM-based Context Check (Placeholder)
        matches = self._llm_context_check(text, matches)

        return matches

    def _keyword_context_check(
        self, text: str, matches: List[Match]
    ) -> List[Match]:
        """
        Check for context keywords surrounding the match with proximity scoring.

        Args:
            text: Original text
            matches: List of matches
        """
        sc = self.scoring_config
        window_size = sc.keyword_window
        text_lower = text.lower()

        for match in matches:
            # Determine relevant categories to check
            # For specific categories like 'address', we also check sub-categories like 'address_us'
            categories_to_check = {str(match.category.value), str(match.category.value).lower()}
            if match.category.value == "address":
                categories_to_check.add("address_us")
                categories_to_check.add("address_kr")
                categories_to_check.add("address_jp")
            elif match.category.value == "zipcode":  # If we add zipcode category
                categories_to_check.add("address_us")
                categories_to_check.add("address_kr")
                categories_to_check.add("address_jp")

            # Collect all valid context phrases
            valid_contexts = set()
            for cat in categories_to_check:
                if cat in self.context_map:
                    valid_contexts.update(self.context_map[cat])

            if not valid_contexts:
                continue

            # Define window
            start_idx = max(0, match.start - window_size)
            end_idx = min(len(text), match.end + window_size)

            # Extract window texts
            pre_window = text_lower[start_idx : match.start]
            post_window = text_lower[match.end : end_idx]

            found_evidence = []
            max_boost = 0.0

            for ctx in valid_contexts:
                # Check pre-window (before match)
                # Find the LAST occurrence to get the one closest to the match
                pre_pos = pre_window.rfind(ctx)
                if pre_pos != -1:
                    distance = len(pre_window) - (pre_pos + len(ctx))
                    found_evidence.append(f"{ctx} (dist: -{distance})")

                    # Proximity scoring logic
                    # < 10 chars: High confidence (e.g., "Zip: 90210")
                    if distance < 10:
                        max_boost = max(max_boost, sc.keyword_pre_close_boost)
                    elif distance < 30:
                        max_boost = max(max_boost, sc.keyword_pre_far_boost)
                    else:
                        max_boost = max(max_boost, sc.keyword_pre_weak_boost)

                # Check post-window (after match)
                # Find the FIRST occurrence
                post_pos = post_window.find(ctx)
                if post_pos != -1:
                    distance = post_pos
                    found_evidence.append(f"{ctx} (dist: +{distance})")

                    if distance < 10:
                        max_boost = max(max_boost, sc.keyword_post_close_boost)
                    elif distance < 30:
                        max_boost = max(max_boost, sc.keyword_post_far_boost)
                    else:
                        max_boost = max(max_boost, sc.keyword_post_weak_boost)

            # Update match if evidence found
            if found_evidence:
                match.context_evidence.extend(found_evidence)
                match.score = min(0.99, match.score + max_boost)

        return matches

    def _ml_context_check(self, text: str, matches: List[Match]) -> List[Match]:
        """
        ML-based context analysis using Transformer classifiers.

        Supports two modes:
        1. Fine-tuned mode: Uses locally trained binary + category classifiers
           (set binary_model_path and/or category_model_path in TransformerConfig)
        2. Zero-shot mode: Uses a generic zero-shot classifier (e.g., BART-MNLI)

        For each match, extracts the matched text (or context window) and classifies
        whether it is truly PII. Boosts or penalizes match.score accordingly.

        Requires: pip install data-detector[transformer]
        """
        if not self._transformer_config or not self._transformer_config.is_context_enabled():
            return matches

        if not self._ensure_classifier():
            return matches

        config = self._transformer_config

        if self._use_finetuned:
            return self._finetuned_context_check(text, matches, config)
        else:
            return self._zeroshot_context_check(text, matches, config)

    def _finetuned_context_check(
        self, text: str, matches: List[Match], config: TransformerConfig
    ) -> List[Match]:
        """Use fine-tuned binary + category classifiers to score matches.

        Verified matches (passed checksum/Luhn/format validation) skip the
        binary classifier since they are already confirmed PII.  The category
        classifier still runs on them for informational cross-validation.
        """
        for match in matches:
            # Extract the matched text for classification
            matched_text = text[match.start:match.end]
            if not matched_text.strip():
                continue

            # Binary classifier: is this PII?
            # Skip for verified matches — verification already confirmed PII.
            if self._binary_pipeline and not match.verified:
                try:
                    result = self._binary_pipeline(matched_text)
                    # result is [{"label": "pii"/"non_pii", "score": 0.95}]
                    top = result[0]
                    is_pii = top["label"] == "pii" or top["label"] == "LABEL_1"
                    conf = top["score"]

                    if is_pii and conf > config.context_confidence_threshold:
                        boost = config.context_max_boost * conf
                        match.score = min(0.99, match.score + boost)
                        match.context_evidence.append(
                            f"ML-binary:pii (conf={conf:.3f}, boost=+{boost:.3f})"
                        )
                    elif not is_pii and conf > config.context_confidence_threshold:
                        match.score = max(0.01, match.score - config.context_penalty)
                        match.context_evidence.append(
                            f"ML-binary:non_pii (conf={conf:.3f}, penalty=-{config.context_penalty:.3f})"
                        )
                except Exception as e:
                    logger.warning(f"Binary classifier failed for match at {match.start}: {e}")
            elif self._binary_pipeline and match.verified:
                match.context_evidence.append("ML-binary:skipped (verified by checksum)")

            # Category classifier: does the predicted category match the regex category?
            # Runs on all matches (including verified) for cross-validation.
            if self._category_pipeline:
                try:
                    result = self._category_pipeline(matched_text)
                    predicted_cat = result[0]["label"]
                    cat_conf = result[0]["score"]

                    regex_cat = match.category.value
                    if predicted_cat == regex_cat and cat_conf > config.context_confidence_threshold:
                        boost = self.scoring_config.ml_category_boost * cat_conf
                        match.score = min(0.99, match.score + boost)
                        match.context_evidence.append(
                            f"ML-category:{predicted_cat} (conf={cat_conf:.3f}, boost=+{boost:.3f})"
                        )
                    elif predicted_cat != regex_cat and cat_conf > 0.7:
                        match.context_evidence.append(
                            f"ML-category-mismatch:regex={regex_cat},ml={predicted_cat} (conf={cat_conf:.3f})"
                        )
                except Exception as e:
                    logger.warning(f"Category classifier failed for match at {match.start}: {e}")

        return matches

    def _zeroshot_context_check(
        self, text: str, matches: List[Match], config: TransformerConfig
    ) -> List[Match]:
        """Use zero-shot classifier on context windows around matches."""
        for match in matches:
            # Extract context window around the match
            window_start = max(0, match.start - config.context_window_chars)
            window_end = min(len(text), match.end + config.context_window_chars)
            context_text = text[window_start:window_end]

            if not context_text.strip():
                continue

            # Build candidate labels based on the match category
            category_label = match.category.value.replace("_", " ")
            candidate_labels = [
                f"This text contains {category_label} information",
                "This is personal identifying information",
                "This is not personal information",
                "This is a random number or code",
            ]

            try:
                result = self._classifier(
                    context_text,
                    candidate_labels=candidate_labels,
                )

                # result["labels"] and result["scores"] are ordered by score desc
                top_label = result["labels"][0]
                top_score = result["scores"][0]

                is_pii_label = (
                    "personal" in top_label.lower() or category_label in top_label.lower()
                )

                if is_pii_label and top_score > config.context_confidence_threshold:
                    boost = config.context_max_boost * top_score
                    match.score = min(0.99, match.score + boost)
                    match.context_evidence.append(
                        f"ML:{top_label} (conf={top_score:.3f}, boost=+{boost:.3f})"
                    )
                elif not is_pii_label and top_score > config.context_confidence_threshold:
                    match.score = max(0.01, match.score - config.context_penalty)
                    match.context_evidence.append(
                        f"ML:{top_label} (conf={top_score:.3f}, penalty=-{config.context_penalty:.3f})"
                    )
            except Exception as e:
                logger.warning(f"ML context check failed for match at {match.start}: {e}")
                continue

        return matches

    def _ensure_classifier(self) -> bool:
        """Lazy-load the classifier pipeline(s). Returns False if unavailable."""
        if self._classifier is not None:
            return self._classifier is not False

        try:
            from transformers import pipeline as hf_pipeline  # type: ignore[import-untyped]
        except ImportError:
            logger.debug("transformers not installed, ML context check disabled")
            self._classifier = False
            return False

        config = self._transformer_config
        assert config is not None
        device_arg = -1 if config.device == "cpu" else config.device

        # Check if fine-tuned models are available
        # Validate paths exist before attempting to load (avoids slow fallback on
        # missing pii-engine submodule or incomplete model files)
        binary_path = config.binary_model_path
        category_path = config.category_model_path
        if binary_path and not Path(binary_path).exists():
            logger.warning(f"Binary model path not found, skipping: {binary_path}")
            binary_path = ""
        if category_path and not Path(category_path).exists():
            logger.warning(f"Category model path not found, skipping: {category_path}")
            category_path = ""

        if binary_path or category_path:
            try:
                if binary_path:
                    self._binary_pipeline = hf_pipeline(
                        "text-classification",
                        model=binary_path,
                        device=device_arg,
                    )
                    logger.info(f"Loaded fine-tuned binary classifier: {binary_path}")

                if category_path:
                    self._category_pipeline = hf_pipeline(
                        "text-classification",
                        model=category_path,
                        device=device_arg,
                    )
                    logger.info(f"Loaded fine-tuned category classifier: {category_path}")

                self._use_finetuned = True
                self._classifier = True  # Mark as loaded
                return True
            except Exception as e:
                logger.error(f"Failed to load fine-tuned models: {e}")
                logger.info("Falling back to zero-shot classifier")

        # Fall back to zero-shot classifier
        try:
            self._classifier = hf_pipeline(
                "zero-shot-classification",
                model=config.context_model,
                device=device_arg,
            )
            logger.info(f"Loaded zero-shot classifier: {config.context_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to load context classifier: {e}")
            self._classifier = False
            return False

    def _llm_context_check(self, text: str, matches: List[Match]) -> List[Match]:
        """
        Placeholder for LLM based context analysis.

        This slot is reserved for calling an LLM (e.g., GPT-4, Gemini) for
        ambiguous cases where high precision is required and latency is acceptable.
        """
        # TODO: Implement LLM API call for complex disambiguation
        return matches
