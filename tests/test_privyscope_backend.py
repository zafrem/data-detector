"""Tests for the optional privyscope NER backend.

All tests mock the privyscope engine -- no language pack or ONNX weights required.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from datadetector.models import Category, PrivyscopeConfig, Severity
from datadetector.privyscope_backend import (
    PRIVYSCOPE_LABEL_TO_CATEGORY,
    PrivyscopeDetector,
)


def _span(label, start, end, text):
    """Build a stand-in for privyscope's DetectedSpan."""
    return SimpleNamespace(label=label, start=start, end=end, text=text, placeholder=f"<{label}>")


def _result(spans):
    """Build a stand-in for privyscope's RedactionResult."""
    return SimpleNamespace(detected_spans=spans)


# ---------------------------------------------------------------------------
# TestPrivyscopeConfig
# ---------------------------------------------------------------------------
class TestPrivyscopeConfig:
    def test_disabled_by_default(self):
        cfg = PrivyscopeConfig()
        assert not cfg.is_enabled()
        assert cfg.lang is None
        assert cfg.operating_point == "balanced"
        assert not cfg.regex_only

    def test_enabled(self):
        cfg = PrivyscopeConfig(enabled=True, lang="ko")
        assert cfg.is_enabled()
        assert cfg.lang == "ko"


# ---------------------------------------------------------------------------
# TestPrivyscopeDetector
# ---------------------------------------------------------------------------
class TestPrivyscopeDetector:
    def test_returns_empty_when_privyscope_missing(self):
        """Graceful degradation: no privyscope installed -> no matches, no raise."""
        with patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", False):
            detector = PrivyscopeDetector(PrivyscopeConfig(enabled=True))
            assert detector.detect("홍길동 010-1234-5678") == []

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_detect_maps_spans_to_matches(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result(
            [
                _span("PER", 0, 3, "홍길동"),
                _span("PHONE", 4, 17, "010-1234-5678"),
            ]
        )
        mock_cls.from_pretrained.return_value = engine

        detector = PrivyscopeDetector(PrivyscopeConfig(enabled=True, lang="ko"))
        matches = detector.detect("홍길동 010-1234-5678")

        assert len(matches) == 2

        name, phone = matches
        assert name.category == Category.NAME
        assert name.start == 0 and name.end == 3
        assert name.matched_text == "홍길동"
        assert name.namespace == "privyscope"
        assert name.ns_id == "privyscope/per"
        assert name.detection_method == "ner"
        assert name.severity == Severity.MEDIUM

        assert phone.category == Category.PHONE
        assert phone.severity == Severity.HIGH
        assert phone.score == 0.6

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_unknown_labels_are_skipped(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result(
            [_span("PER", 0, 3, "홍길동"), _span("NOT_A_REAL_LABEL", 4, 8, "xxxx")]
        )
        mock_cls.from_pretrained.return_value = engine

        matches = PrivyscopeDetector(PrivyscopeConfig(enabled=True)).detect("x")
        assert len(matches) == 1
        assert matches[0].category == Category.NAME

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_auto_language_uses_auto_constructor(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result([])
        mock_cls.auto.return_value = engine

        detector = PrivyscopeDetector(PrivyscopeConfig(enabled=True, auto_language=True))
        detector.detect("hello")

        mock_cls.auto.assert_called_once()
        mock_cls.from_pretrained.assert_not_called()

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_engine_build_failure_degrades_quietly(self, mock_cls):
        """No language pack installed -> log and return [], never raise."""
        mock_cls.from_pretrained.side_effect = ValueError("no language plugin installed")

        detector = PrivyscopeDetector(PrivyscopeConfig(enabled=True))
        assert detector.detect("hello") == []
        # Second call must not retry the failed construction.
        assert detector.detect("hello") == []
        assert mock_cls.from_pretrained.call_count == 1

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_inference_failure_returns_empty(self, mock_cls):
        engine = MagicMock()
        engine.redact.side_effect = RuntimeError("onnx blew up")
        mock_cls.from_pretrained.return_value = engine

        assert PrivyscopeDetector(PrivyscopeConfig(enabled=True)).detect("hello") == []

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_engine_built_once_across_calls(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result([])
        mock_cls.from_pretrained.return_value = engine

        detector = PrivyscopeDetector(PrivyscopeConfig(enabled=True))
        detector.detect("a")
        detector.detect("b")

        assert mock_cls.from_pretrained.call_count == 1


# ---------------------------------------------------------------------------
# TestLabelMapping
# ---------------------------------------------------------------------------
class TestLabelMapping:
    def test_covers_all_privyscope_base_entities(self):
        """Every entity in privyscope's BASE_ENTITIES must map to a Category."""
        base_entities = {"PER", "PHONE", "ID_NUM", "EMAIL", "LOC", "BANK", "DATE", "SECRET"}
        assert base_entities == set(PRIVYSCOPE_LABEL_TO_CATEGORY)

    def test_maps_to_valid_categories(self):
        for category in PRIVYSCOPE_LABEL_TO_CATEGORY.values():
            assert isinstance(category, Category)


# ---------------------------------------------------------------------------
# TestEngineWiring
# ---------------------------------------------------------------------------
class TestEngineWiring:
    def test_privyscope_takes_the_ner_slot_when_enabled(self):
        from datadetector import Engine, load_registry
        from datadetector.models import TransformerConfig

        engine = Engine(
            load_registry(),
            transformer_config=TransformerConfig(enable_ner=True),
            privyscope_config=PrivyscopeConfig(enabled=True),
        )
        assert isinstance(engine._get_ner_detector(), PrivyscopeDetector)

    def test_falls_back_to_transformer_ner_when_disabled(self):
        from datadetector import Engine, load_registry
        from datadetector.models import TransformerConfig
        from datadetector.transformer_ner import TransformerNERDetector

        engine = Engine(
            load_registry(),
            transformer_config=TransformerConfig(enable_ner=True),
            privyscope_config=PrivyscopeConfig(enabled=False),
        )
        assert isinstance(engine._get_ner_detector(), TransformerNERDetector)

    def test_no_ner_detector_when_neither_enabled(self):
        from datadetector import Engine, load_registry

        engine = Engine(load_registry())
        assert engine._get_ner_detector() is None
