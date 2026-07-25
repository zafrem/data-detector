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

    def test_from_dict_none_or_empty_is_disabled(self):
        assert PrivyscopeConfig.from_dict(None).is_enabled() is False
        assert PrivyscopeConfig.from_dict({}).is_enabled() is False

    def test_from_dict_full_mapping(self):
        cfg = PrivyscopeConfig.from_dict(
            {
                "enabled": True,
                "lang": "en",
                "auto_language": True,
                "operating_point": "high_recall",
                "regex_only": True,
                "cache_dir": "/tmp/weights",
                "score": 0.8,
            }
        )
        assert cfg.enabled and cfg.lang == "en" and cfg.auto_language
        assert cfg.operating_point == "high_recall" and cfg.regex_only
        assert cfg.cache_dir == "/tmp/weights" and cfg.score == 0.8

    def test_from_dict_ignores_unknown_keys(self):
        cfg = PrivyscopeConfig.from_dict({"enabled": True, "not_a_field": 123})
        assert cfg.is_enabled()

    def test_from_dict_coerces_types(self):
        # YAML/JSON may hand us truthy ints and stringy floats.
        cfg = PrivyscopeConfig.from_dict({"enabled": 1, "score": "0.9"})
        assert cfg.enabled is True
        assert isinstance(cfg.score, float) and cfg.score == 0.9


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
    def test_from_pretrained_called_with_config_args(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result([])
        mock_cls.from_pretrained.return_value = engine

        cfg = PrivyscopeConfig(
            enabled=True,
            lang="ko",
            operating_point="high_precision",
            regex_only=True,
            cache_dir="/w",
        )
        PrivyscopeDetector(cfg).detect("x")

        mock_cls.from_pretrained.assert_called_once_with(
            "high_precision", lang="ko", cache_dir="/w", regex_only=True
        )

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_lowercase_span_label_is_normalized(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result([_span("per", 0, 3, "홍길동")])
        mock_cls.from_pretrained.return_value = engine

        match = PrivyscopeDetector(PrivyscopeConfig(enabled=True)).detect("홍길동")[0]
        assert match.category == Category.NAME
        assert match.ns_id == "privyscope/per"

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_empty_result_returns_empty_list(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result([])
        mock_cls.from_pretrained.return_value = engine

        assert PrivyscopeDetector(PrivyscopeConfig(enabled=True)).detect("nothing here") == []

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_match_metadata_is_populated(self, mock_cls):
        engine = MagicMock()
        engine.redact.return_value = _result([_span("EMAIL", 0, 7, "a@b.com")])
        mock_cls.from_pretrained.return_value = engine

        match = PrivyscopeDetector(PrivyscopeConfig(enabled=True, score=0.42)).detect("a@b.com")[0]
        assert match.pattern_id == "privyscope_email"
        assert match.context_evidence == ["privyscope:EMAIL"]
        assert match.score == 0.42
        assert match.detection_method == "ner"

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


# ---------------------------------------------------------------------------
# TestFindPipelineIntegration -- privyscope merged into Engine.find()
# ---------------------------------------------------------------------------
class TestFindPipelineIntegration:
    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_ner_adds_span_regex_misses(self, mock_cls):
        """A span no regex pattern catches gets surfaced by privyscope in find()."""
        from datadetector import Engine, load_registry

        # "Qwxyz" is in no name list and matches no regex, so only privyscope reports it.
        text = "greeting from Qwxyz today"
        start = text.index("Qwxyz")
        mock_engine = MagicMock()
        mock_engine.redact.return_value = _result([_span("PER", start, start + 5, "Qwxyz")])
        mock_cls.from_pretrained.return_value = mock_engine

        engine = Engine(
            load_registry(), privyscope_config=PrivyscopeConfig(enabled=True, lang="ko")
        )
        result = engine.find(text, include_matched_text=True)

        ner = [m for m in result.matches if m.namespace == "privyscope"]
        assert len(ner) == 1
        assert ner[0].category == Category.NAME
        assert ner[0].detection_method == "ner"

    @patch("datadetector.privyscope_backend.PRIVYSCOPE_AVAILABLE", True)
    @patch("datadetector.privyscope_backend.Privyscope")
    def test_ner_corroborates_overlapping_regex_match(self, mock_cls):
        """When privyscope agrees with a regex hit, the regex match is boosted."""
        from datadetector import Engine, load_registry

        # Non-placeholder domain so the score filter keeps the regex email match.
        text = "email me at alice@acmecorp.io"
        start = text.index("alice@acmecorp.io")
        end = start + len("alice@acmecorp.io")
        mock_engine = MagicMock()
        mock_engine.redact.return_value = _result([_span("EMAIL", start, end, "alice@acmecorp.io")])
        mock_cls.from_pretrained.return_value = mock_engine

        engine = Engine(load_registry(), privyscope_config=PrivyscopeConfig(enabled=True))
        result = engine.find(text)

        emails = [m for m in result.matches if m.category == Category.EMAIL]
        assert emails, "regex should have found the email"
        # The overlapping regex match is merged (boosted), not duplicated.
        assert len(emails) == 1
        assert emails[0].detection_method == "regex+ner"
        assert "NER-corroboration:email" in emails[0].context_evidence


# ---------------------------------------------------------------------------
# TestServerConfigWiring -- config.yml `privyscope:` section -> Engine
# ---------------------------------------------------------------------------
class TestServerConfigWiring:
    @staticmethod
    def _server(cfg):
        from datadetector.server import DataDetectorServer

        return DataDetectorServer(cfg)

    def test_no_section_leaves_privyscope_off(self):
        server = self._server({"registry": {"paths": ["config/tokens.yml"]}})
        assert server.engine.privyscope_config is None

    def test_disabled_section_passes_none(self):
        server = self._server(
            {"registry": {"paths": ["config/tokens.yml"]}, "privyscope": {"enabled": False}}
        )
        assert server.engine.privyscope_config is None

    def test_enabled_section_builds_config(self):
        server = self._server(
            {
                "registry": {"paths": ["config/tokens.yml"]},
                "privyscope": {"enabled": True, "lang": "ko", "regex_only": True},
            }
        )
        pc = server.engine.privyscope_config
        assert pc is not None and pc.is_enabled()
        assert pc.lang == "ko" and pc.regex_only is True

    def test_rag_middleware_inherits_engine(self):
        server = self._server(
            {"registry": {"paths": ["config/tokens.yml"]}, "privyscope": {"enabled": True}}
        )
        assert server.rag_middleware.engine is server.engine


# ---------------------------------------------------------------------------
# TestCLIHelper -- shared --ner/--ner-lang flag wiring
# ---------------------------------------------------------------------------
class TestCLIHelper:
    def test_returns_none_when_ner_off(self):
        from datadetector.cli import _privyscope_config

        assert _privyscope_config(False, None) is None
        assert _privyscope_config(False, "ko") is None

    def test_builds_config_when_ner_on(self):
        from datadetector.cli import _privyscope_config

        pc = _privyscope_config(True, "ko")
        assert pc is not None and pc.is_enabled() and pc.lang == "ko"
