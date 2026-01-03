"""
Context analysis module for PII detection.

This module implements the third step of the detection pipeline: Contextual Analysis.
It validates and scores matches based on surrounding text, using:
1. Keyword Analysis (Deterministic)
2. ML/LLM Analysis (Future Extension)
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

from datadetector.models import Match

logger = logging.getLogger(__name__)


class ContextAnalyzer:
    """
    Analyzer for validating PII matches using context.

    Implements a pipeline of analysis steps:
    1. Keyword Check: Looks for related terms near the match
    2. ML/LLM Check: (Placeholder) Advanced semantic analysis
    """

    def __init__(self, context_dir: Optional[Path] = None):
        """
        Initialize ContextAnalyzer.

        Args:
            context_dir: Directory containing keyword YAML files.
                        If None, attempts to locate pattern-engine/keyword.
        """
        self.context_map: Dict[str, Set[str]] = {}  # category -> set of context phrases
        self._load_contexts(context_dir)

    def _get_project_root(self) -> Path:
        """Determine project root directory."""
        # src/datadetector/analysis.py -> src/datadetector -> src -> root
        root = Path(__file__).parent.parent.parent
        if (root / "pattern-engine").exists():
            return root

        # Check standard locations
        candidates = [
            Path("/app"),
            Path.cwd(),
        ]
        for candidate in candidates:
            if (candidate / "pattern-engine").exists():
                return candidate

        return root

    def _load_contexts(self, context_dir: Optional[Path]) -> None:
        """Load context keywords from YAML files."""
        if context_dir is None:
            root = self._get_project_root()
            context_dir = root / "pattern-engine" / "keyword"

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

        # Step 1: Keyword-based Context Check
        matches = self._keyword_context_check(text, matches)

        # Step 2: ML-based Context Check (Placeholder)
        matches = self._ml_context_check(text, matches)

        # Step 3: LLM-based Context Check (Placeholder)
        matches = self._llm_context_check(text, matches)

        return matches

    def _keyword_context_check(
        self, text: str, matches: List[Match], window_size: int = 60
    ) -> List[Match]:
        """
        Check for context keywords surrounding the match with proximity scoring.

        Args:
            text: Original text
            matches: List of matches
            window_size: Number of characters to check before and after the match
        """
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
                        max_boost = max(max_boost, 0.45)  # Boost to ~0.95
                    elif distance < 30:
                        max_boost = max(max_boost, 0.3)  # Boost to ~0.8
                    else:
                        max_boost = max(max_boost, 0.1)  # Weak boost

                # Check post-window (after match)
                # Find the FIRST occurrence
                post_pos = post_window.find(ctx)
                if post_pos != -1:
                    distance = post_pos
                    found_evidence.append(f"{ctx} (dist: +{distance})")

                    if distance < 10:
                        max_boost = max(max_boost, 0.4)
                    elif distance < 30:
                        max_boost = max(max_boost, 0.25)
                    else:
                        max_boost = max(max_boost, 0.1)

            # Update match if evidence found
            if found_evidence:
                match.context_evidence.extend(found_evidence)
                match.score = min(0.99, match.score + max_boost)

        return matches

    def _ml_context_check(self, text: str, matches: List[Match]) -> List[Match]:
        """
        Placeholder for Machine Learning based context analysis.

        This slot is reserved for a lightweight ML model (e.g., BERT-tiny, Random Forest)
        that can classify the context window as "related to category X" or "random noise".
        """
        # TODO: Implement ML model inference
        return matches

    def _llm_context_check(self, text: str, matches: List[Match]) -> List[Match]:
        """
        Placeholder for LLM based context analysis.

        This slot is reserved for calling an LLM (e.g., GPT-4, Gemini) for
        ambiguous cases where high precision is required and latency is acceptable.
        """
        # TODO: Implement LLM API call for complex disambiguation
        return matches
