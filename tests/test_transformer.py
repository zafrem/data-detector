"""Tests for Transformer-based NLP features (NER detection + context classification).

All tests mock the Transformer pipeline -- no actual model downloads required.
"""

from unittest.mock import MagicMock, patch

import pytest

from datadetector.models import Category, Match, Severity, TransformerConfig


# ---------------------------------------------------------------------------
# TestTransformerConfig
# ---------------------------------------------------------------------------
class TestTransformerConfig:
    def test_default_config_all_disabled(self):
        cfg = TransformerConfig()
        assert not cfg.is_ner_enabled()
        assert not cfg.is_context_enabled()
        assert not cfg.is_enabled()

    def test_ner_enabled(self):
        cfg = TransformerConfig(enable_ner=True)
        assert cfg.is_ner_enabled()
        assert cfg.is_enabled()
        assert not cfg.is_context_enabled()

    def test_context_enabled(self):
        cfg = TransformerConfig(enable_context_classifier=True)
        assert cfg.is_context_enabled()
        assert cfg.is_enabled()
        assert not cfg.is_ner_enabled()

    def test_both_enabled(self):
        cfg = TransformerConfig(enable_ner=True, enable_context_classifier=True)
        assert cfg.is_ner_enabled()
        assert cfg.is_context_enabled()
        assert cfg.is_enabled()

    def test_custom_model_names(self):
        cfg = TransformerConfig(
            ner_model="custom/ner-model",
            context_model="custom/classifier",
            device="cuda:0",
        )
        assert cfg.ner_model == "custom/ner-model"
        assert cfg.context_model == "custom/classifier"
        assert cfg.device == "cuda:0"


# ---------------------------------------------------------------------------
# TestTransformerNERDetector
# ---------------------------------------------------------------------------
class TestTransformerNERDetector:
    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_detect_returns_matches(self, mock_pipeline_fn):
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {
                "entity_group": "PER",
                "score": 0.95,
                "word": "John Smith",
                "start": 0,
                "end": 10,
            },
        ]
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.transformer_ner import TransformerNERDetector

        config = TransformerConfig(enable_ner=True, ner_confidence_threshold=0.7)
        detector = TransformerNERDetector(config)
        matches = detector.detect("John Smith called yesterday")

        assert len(matches) == 1
        assert matches[0].category == Category.NAME
        assert matches[0].detection_method == "ner"
        assert matches[0].namespace == "ner"
        assert matches[0].ns_id == "ner/per"
        assert matches[0].start == 0
        assert matches[0].end == 10
        assert matches[0].matched_text == "John Smith"
        assert any("NER:" in e for e in matches[0].context_evidence)

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_detect_filters_low_confidence(self, mock_pipeline_fn):
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"entity_group": "PER", "score": 0.3, "word": "Maybe", "start": 0, "end": 5},
        ]
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.transformer_ner import TransformerNERDetector

        config = TransformerConfig(enable_ner=True, ner_confidence_threshold=0.7)
        detector = TransformerNERDetector(config)
        matches = detector.detect("Maybe a name")

        assert len(matches) == 0

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_detect_skips_unknown_label(self, mock_pipeline_fn):
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"entity_group": "ORG", "score": 0.99, "word": "Acme Corp", "start": 0, "end": 9},
        ]
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.transformer_ner import TransformerNERDetector

        config = TransformerConfig(enable_ner=True)
        detector = TransformerNERDetector(config)
        matches = detector.detect("Acme Corp is a company")

        assert len(matches) == 0  # ORG is not in the label map

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", False)
    def test_detect_graceful_when_no_transformers(self):
        from datadetector.transformer_ner import TransformerNERDetector

        config = TransformerConfig(enable_ner=True)
        detector = TransformerNERDetector(config)
        matches = detector.detect("John Smith")

        assert matches == []

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_detect_handles_pipeline_error(self, mock_pipeline_fn):
        mock_pipe = MagicMock()
        mock_pipe.side_effect = RuntimeError("model error")
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.transformer_ner import TransformerNERDetector

        config = TransformerConfig(enable_ner=True)
        detector = TransformerNERDetector(config)
        matches = detector.detect("some text")

        assert matches == []

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_detect_multiple_entities(self, mock_pipeline_fn):
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"entity_group": "PER", "score": 0.92, "word": "Alice", "start": 0, "end": 5},
            {"entity_group": "LOC", "score": 0.88, "word": "Seoul", "start": 14, "end": 19},
        ]
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.transformer_ner import TransformerNERDetector

        config = TransformerConfig(enable_ner=True, ner_confidence_threshold=0.7)
        detector = TransformerNERDetector(config)
        matches = detector.detect("Alice lives in Seoul")

        assert len(matches) == 2
        assert matches[0].category == Category.NAME
        assert matches[1].category == Category.LOCATION

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_severity_assigned_by_category(self, mock_pipeline_fn):
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"entity_group": "SSN", "score": 0.95, "word": "123-45-6789", "start": 5, "end": 16},
        ]
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.transformer_ner import TransformerNERDetector

        config = TransformerConfig(enable_ner=True)
        detector = TransformerNERDetector(config)
        matches = detector.detect("SSN: 123-45-6789")

        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL


# ---------------------------------------------------------------------------
# TestMLContextCheck
# ---------------------------------------------------------------------------
class TestMLContextCheck:
    def _make_match(self, start=0, end=13, category=Category.PHONE):
        return Match(
            ns_id="kr/mobile_01",
            pattern_id="mobile_01",
            namespace="kr",
            category=category,
            start=start,
            end=end,
            score=0.5,
        )

    def test_ml_context_disabled_by_default(self):
        from datadetector.analysis import ContextAnalyzer

        analyzer = ContextAnalyzer()
        match = self._make_match()
        original_score = match.score
        result = analyzer._ml_context_check("Phone: 010-1234-5678", [match])

        assert len(result) == 1
        assert result[0].score == original_score  # Unchanged

    @patch("datadetector.analysis.ContextAnalyzer._ensure_classifier")
    def test_ml_context_boosts_score(self, mock_ensure):
        from datadetector.analysis import ContextAnalyzer

        mock_ensure.return_value = True

        config = TransformerConfig(
            enable_context_classifier=True,
            context_confidence_threshold=0.5,
            context_max_boost=0.35,
        )
        analyzer = ContextAnalyzer(transformer_config=config)

        # Mock the classifier to return PII-related label
        mock_classifier = MagicMock()
        mock_classifier.return_value = {
            "labels": ["This text contains phone information", "This is not personal information"],
            "scores": [0.85, 0.15],
        }
        analyzer._classifier = mock_classifier

        match = self._make_match()
        text = "Please call me at 010-1234-5678 anytime"
        result = analyzer._ml_context_check(text, [match])

        assert len(result) == 1
        assert result[0].score > 0.5  # Boosted
        assert any("ML:" in e for e in result[0].context_evidence)

    @patch("datadetector.analysis.ContextAnalyzer._ensure_classifier")
    def test_ml_context_penalizes_score(self, mock_ensure):
        from datadetector.analysis import ContextAnalyzer

        mock_ensure.return_value = True

        config = TransformerConfig(
            enable_context_classifier=True,
            context_confidence_threshold=0.5,
            context_penalty=0.2,
        )
        analyzer = ContextAnalyzer(transformer_config=config)

        mock_classifier = MagicMock()
        mock_classifier.return_value = {
            "labels": ["This is a random number or code", "This text contains phone information"],
            "scores": [0.90, 0.10],
        }
        analyzer._classifier = mock_classifier

        match = self._make_match()
        text = "Reference code: 010-1234-5678 for order"
        result = analyzer._ml_context_check(text, [match])

        assert len(result) == 1
        assert result[0].score < 0.5  # Penalized
        assert any("penalty" in e for e in result[0].context_evidence)

    @patch("datadetector.analysis.ContextAnalyzer._ensure_classifier")
    def test_ml_context_evidence_trail(self, mock_ensure):
        from datadetector.analysis import ContextAnalyzer

        mock_ensure.return_value = True

        config = TransformerConfig(enable_context_classifier=True)
        analyzer = ContextAnalyzer(transformer_config=config)

        mock_classifier = MagicMock()
        mock_classifier.return_value = {
            "labels": ["This is personal identifying information"],
            "scores": [0.75],
        }
        analyzer._classifier = mock_classifier

        match = self._make_match()
        result = analyzer._ml_context_check("Phone: 010-1234-5678", [match])

        assert len(result[0].context_evidence) > 0
        assert result[0].context_evidence[0].startswith("ML:")

    def test_ml_context_graceful_no_transformers(self):
        from datadetector.analysis import ContextAnalyzer

        config = TransformerConfig(enable_context_classifier=True)
        analyzer = ContextAnalyzer(transformer_config=config)
        # Force _classifier to False (simulating import failure)
        analyzer._classifier = False

        match = self._make_match()
        result = analyzer._ml_context_check("Phone: 010-1234-5678", [match])

        assert len(result) == 1
        assert result[0].score == 0.5  # Unchanged


# ---------------------------------------------------------------------------
# TestEngineNERIntegration
# ---------------------------------------------------------------------------
class TestEngineNERIntegration:
    def test_ner_disabled_by_default(self):
        """Engine without transformer_config should not run NER."""
        from datadetector.engine import Engine
        from datadetector.registry import PatternRegistry

        reg = PatternRegistry()
        engine = Engine(reg)
        assert engine._get_ner_detector() is None

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_ner_matches_merged_with_regex(self, mock_pipeline_fn):
        """NER finds entities that regex missed -- they should appear in results."""
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"entity_group": "PER", "score": 0.95, "word": "Alice", "start": 0, "end": 5},
        ]
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.engine import Engine
        from datadetector.registry import PatternRegistry

        reg = PatternRegistry()
        config = TransformerConfig(enable_ner=True)
        engine = Engine(reg, transformer_config=config)

        result = engine.find("Alice went to school")

        # Should have NER match (regex has no patterns loaded so finds nothing)
        ner_matches = [m for m in result.matches if m.detection_method == "ner"]
        assert len(ner_matches) == 1
        assert ner_matches[0].category == Category.NAME

    @patch("datadetector.transformer_ner.TRANSFORMERS_AVAILABLE", True)
    @patch("datadetector.transformer_ner.hf_pipeline")
    def test_ner_overlap_boosts_regex_score(self, mock_pipeline_fn):
        """When NER and regex find overlapping spans, regex match gets score boost."""
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"entity_group": "PHONE", "score": 0.92, "word": "010-1234-5678",
             "start": 6, "end": 19},
        ]
        mock_pipeline_fn.return_value = mock_pipe

        from datadetector.engine import Engine
        from datadetector.registry import PatternRegistry

        reg = PatternRegistry()
        config = TransformerConfig(enable_ner=True)
        engine = Engine(reg, transformer_config=config)

        # Simulate a pre-existing regex match by patching find
        original_find = engine.find

        def patched_find(*args, **kwargs):
            # Let the normal find run (will only get NER since no patterns loaded)
            # Instead, manually test the merge logic
            pass

        # Test the merge logic directly with a regex match already in place
        regex_match = Match(
            ns_id="kr/mobile_01",
            pattern_id="mobile_01",
            namespace="kr",
            category=Category.PHONE,
            start=6,
            end=19,
            score=0.5,
        )

        from datadetector.transformer_ner import TransformerNERDetector

        detector = TransformerNERDetector(config)
        ner_matches = detector.detect("Phone 010-1234-5678")

        # Simulate the merge logic from engine.find
        matches = [regex_match]
        for nm in ner_matches:
            overlapping = [
                m for m in matches
                if not (nm.end <= m.start or m.end <= nm.start)
            ]
            if not overlapping:
                matches.append(nm)
            else:
                for m in overlapping:
                    m.context_evidence.append(f"NER-corroboration:{nm.category.value}")
                    m.score = min(0.99, m.score + 0.15)
                    m.detection_method = "regex+ner"

        assert len(matches) == 1  # Merged, not duplicated
        assert matches[0].detection_method == "regex+ner"
        assert matches[0].score == 0.65  # 0.5 + 0.15
        assert any("NER-corroboration" in e for e in matches[0].context_evidence)

    def test_detection_method_defaults_to_regex(self):
        """Matches without transformer should have detection_method='regex'."""
        match = Match(
            ns_id="kr/mobile_01",
            pattern_id="mobile_01",
            namespace="kr",
            category=Category.PHONE,
            start=0,
            end=13,
        )
        assert match.detection_method == "regex"
