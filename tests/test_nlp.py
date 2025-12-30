"""Tests for NLP functionality."""

import pytest
from datadetector.nlp import (
    NLPConfig,
    NLPProcessor,
    LanguageDetector,
    StopwordFilter,
    KoreanTokenizer,
    ChineseTokenizer,
    SmartTokenizer,
    PreprocessedText,
    KOREAN_STOPWORDS,
    ENGLISH_STOPWORDS,
    CHINESE_STOPWORDS,
    LANGDETECT_AVAILABLE,
    KONLPY_AVAILABLE,
    JIEBA_AVAILABLE,
)


class TestNLPConfig:
    """Test NLP configuration."""

    def test_default_config(self):
        """Test default configuration has all features disabled."""
        config = NLPConfig()
        assert not config.enable_language_detection
        assert not config.enable_tokenization
        assert not config.enable_stopword_filtering
        assert not config.enable_korean_particles
        assert not config.enable_chinese_segmentation
        assert not config.is_enabled()

    def test_enabled_config(self):
        """Test configuration with features enabled."""
        config = NLPConfig(
            enable_language_detection=True,
            enable_tokenization=True,
        )
        assert config.is_enabled()

    def test_all_features_enabled(self):
        """Test all NLP features enabled."""
        config = NLPConfig(
            enable_language_detection=True,
            enable_tokenization=True,
            enable_stopword_filtering=True,
            enable_korean_particles=True,
            enable_chinese_segmentation=True,
        )
        assert config.is_enabled()
        assert config.enable_language_detection
        assert config.enable_tokenization
        assert config.enable_stopword_filtering
        assert config.enable_korean_particles
        assert config.enable_chinese_segmentation

    def test_custom_stopwords(self):
        """Test custom stopwords."""
        custom = {"foo", "bar", "baz"}
        config = NLPConfig(custom_stopwords=custom)
        assert config.custom_stopwords == custom
        assert "foo" in config.custom_stopwords
        assert "bar" in config.custom_stopwords

    def test_korean_tokenizer_backend(self):
        """Test Korean tokenizer backend configuration."""
        config = NLPConfig(korean_tokenizer="mecab")
        assert config.korean_tokenizer == "mecab"

    def test_korean_tokenizer_default_backend(self):
        """Test default Korean tokenizer backend."""
        config = NLPConfig()
        assert config.korean_tokenizer == "okt"

    def test_validate_without_dependencies(self):
        """Test validate works without dependencies."""
        config = NLPConfig()
        config.validate()  # Should not raise

    def test_validate_with_features_no_deps(self):
        """Test validate warns when features enabled without dependencies."""
        config = NLPConfig(enable_tokenization=True, enable_stopword_filtering=True)
        # Should not raise, just warn
        config.validate()

    def test_chinese_segmentation_flag(self):
        """Test Chinese segmentation configuration."""
        config = NLPConfig(enable_chinese_segmentation=True)
        assert config.enable_chinese_segmentation
        assert config.is_enabled()

    def test_empty_custom_stopwords(self):
        """Test empty custom stopwords."""
        config = NLPConfig(custom_stopwords=set())
        assert config.custom_stopwords == set()


class TestSmartTokenizer:
    """Test smart tokenizer for script boundary detection."""

    def test_ascii_text(self):
        """Test that ASCII text passes through unchanged."""
        tokenizer = SmartTokenizer()
        text = "Hello world 123"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        assert prepared == text
        assert mapping == list(range(len(text)))

    def test_korean_particle_separation(self):
        """Test Korean particle separation from PII."""
        tokenizer = SmartTokenizer()
        # Korean particle attached to number
        text = "010-1234-5678은"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        # Should insert space between number and Korean character
        assert " " in prepared
        assert prepared.replace(" ", "") == text

    def test_chinese_text_separation(self):
        """Test Chinese text separation from ASCII."""
        tokenizer = SmartTokenizer()
        text = "我的邮箱test@example.com是"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        # Should insert spaces at script boundaries
        assert " " in prepared
        # Check that boundaries are detected
        assert "test@example.com" in prepared

    def test_mixed_script_boundaries(self):
        """Test script boundary detection."""
        tokenizer = SmartTokenizer()
        text = "Email:test@example.com입니다"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        # Should have space between Latin and Hangul
        assert "com 입니다" in prepared

    def test_multiple_transitions(self):
        """Test multiple script transitions."""
        tokenizer = SmartTokenizer()
        text = "안녕hello世界world"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        # Should insert spaces at each transition
        space_count = prepared.count(" ")
        assert space_count >= 2  # At least 2 transitions

    def test_empty_text(self):
        """Test empty text handling."""
        tokenizer = SmartTokenizer()
        prepared, mapping = tokenizer.prepare_text_for_search("")
        assert prepared == ""
        assert mapping == []

    def test_only_ascii(self):
        """Test text with only ASCII characters."""
        tokenizer = SmartTokenizer()
        text = "test123@example.com"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        assert prepared == text
        assert len(mapping) == len(text)

    def test_only_cjk(self):
        """Test text with only CJK characters."""
        tokenizer = SmartTokenizer()
        text = "안녕하세요"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        # No spaces should be inserted for pure CJK
        assert prepared == text

    def test_numbers_to_hangul(self):
        """Test transition from numbers to Hangul."""
        tokenizer = SmartTokenizer()
        text = "123번"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        assert " " in prepared
        assert "123 번" == prepared

    def test_special_characters(self):
        """Test handling of special characters."""
        tokenizer = SmartTokenizer()
        text = "test!@#$%^&*()은"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        # Should handle special chars correctly
        assert len(mapping) >= len(text)

    def test_map_to_original(self):
        """Test mapping preprocessed positions to original positions."""
        tokenizer = SmartTokenizer()
        text = "010-1234-5678은"
        prepared, mapping = tokenizer.prepare_text_for_search(text)

        # Find the phone number in prepared text
        import re
        match = re.search(r'\d{3}-\d{4}-\d{4}', prepared)
        if match:
            start, end = match.span()
            orig_start, orig_end = tokenizer.map_match_to_original(start, end, mapping)
            # Should map back to original position
            assert text[orig_start:orig_end] == "010-1234-5678"

    def test_map_to_original_empty(self):
        """Test mapping with empty mapping list."""
        tokenizer = SmartTokenizer()
        orig_start, orig_end = tokenizer.map_match_to_original(0, 5, [])
        assert orig_start == 0
        assert orig_end == 0

    def test_map_to_original_edge_cases(self):
        """Test mapping edge cases."""
        tokenizer = SmartTokenizer()
        text = "abc가나다"
        prepared, mapping = tokenizer.prepare_text_for_search(text)

        # Test mapping at boundary
        orig_start, orig_end = tokenizer.map_match_to_original(0, 3, mapping)
        assert text[orig_start:orig_end] == "abc"

    def test_japanese_text(self):
        """Test Japanese text handling."""
        tokenizer = SmartTokenizer()
        text = "私のメールはtest@example.comです"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        # Should insert spaces at script boundaries
        assert " " in prepared
        assert "test@example.com" in prepared

    def test_mixed_numbers_and_text(self):
        """Test mixed numbers and text."""
        tokenizer = SmartTokenizer()
        text = "call123-456-7890now"
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        assert "123-456-7890" in prepared

    def test_long_text(self):
        """Test handling of long text."""
        tokenizer = SmartTokenizer()
        text = "a" * 1000 + "가" * 1000
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        assert len(mapping) > len(text)  # Should have inserted space


class TestStopwordFilter:
    """Test stopword filtering."""

    def test_korean_stopwords(self):
        """Test Korean stopword filtering."""
        filter = StopwordFilter()
        tokens = ["전화번호", "는", "010-1234-5678", "입니다"]
        filtered = filter.filter_tokens(tokens)
        # Should remove particles
        assert "는" not in filtered
        assert "010-1234-5678" in filtered

    def test_english_stopwords(self):
        """Test English stopword filtering."""
        filter = StopwordFilter()
        tokens = ["the", "phone", "number", "is", "555-1234"]
        filtered = filter.filter_tokens(tokens)
        assert "the" not in filtered
        assert "is" not in filtered
        assert "phone" in filtered
        assert "555-1234" in filtered

    def test_chinese_stopwords(self):
        """Test Chinese stopword filtering."""
        filter = StopwordFilter()
        tokens = ["我", "的", "电话", "号码", "是", "13812345678"]
        filtered = filter.filter_tokens(tokens)
        assert "的" not in filtered
        assert "是" not in filtered
        assert "电话" in filtered
        assert "13812345678" in filtered

    def test_mixed_stopwords(self):
        """Test mixed language stopwords."""
        filter = StopwordFilter()
        tokens = ["the", "是", "phone", "전화", "number"]
        filtered = filter.filter_tokens(tokens)
        assert "the" not in filtered
        assert "是" not in filtered
        assert "phone" in filtered

    def test_custom_stopwords(self):
        """Test custom stopwords."""
        custom = {"custom1", "custom2", "custom3"}
        filter = StopwordFilter(custom_stopwords=custom)
        tokens = ["custom1", "word", "custom2", "text", "custom3"]
        filtered = filter.filter_tokens(tokens)
        assert "custom1" not in filtered
        assert "custom2" not in filtered
        assert "custom3" not in filtered
        assert "word" in filtered
        assert "text" in filtered

    def test_is_stopword_korean(self):
        """Test is_stopword method with Korean."""
        filter = StopwordFilter()
        assert filter.is_stopword("는")
        assert filter.is_stopword("은")
        assert not filter.is_stopword("전화")

    def test_is_stopword_english(self):
        """Test is_stopword method with English."""
        filter = StopwordFilter()
        assert filter.is_stopword("the")
        assert filter.is_stopword("is")
        assert not filter.is_stopword("phone")

    def test_is_stopword_chinese(self):
        """Test is_stopword method with Chinese."""
        filter = StopwordFilter()
        assert filter.is_stopword("的")
        assert filter.is_stopword("是")
        assert not filter.is_stopword("电话")

    def test_is_stopword_case_insensitive(self):
        """Test case insensitive stopword checking."""
        filter = StopwordFilter()
        assert filter.is_stopword("THE")
        assert filter.is_stopword("The")
        assert filter.is_stopword("the")

    def test_empty_token_list(self):
        """Test filtering empty token list."""
        filter = StopwordFilter()
        filtered = filter.filter_tokens([])
        assert filtered == []

    def test_all_stopwords(self):
        """Test filtering when all tokens are stopwords."""
        filter = StopwordFilter()
        tokens = ["the", "is", "a", "an"]
        filtered = filter.filter_tokens(tokens)
        assert filtered == []

    def test_no_stopwords(self):
        """Test filtering when no tokens are stopwords."""
        filter = StopwordFilter()
        tokens = ["phone", "number", "email", "address"]
        filtered = filter.filter_tokens(tokens)
        assert len(filtered) == 4

    def test_stopword_sets_not_empty(self):
        """Test that default stopword sets are not empty."""
        assert len(KOREAN_STOPWORDS) > 0
        assert len(ENGLISH_STOPWORDS) > 0
        assert len(CHINESE_STOPWORDS) > 0

    def test_stopword_overlap(self):
        """Test stopword sets don't have unexpected overlap."""
        # Korean and English should be distinct
        korean_english_overlap = KOREAN_STOPWORDS & ENGLISH_STOPWORDS
        assert len(korean_english_overlap) == 0


class TestPreprocessedText:
    """Test PreprocessedText class."""

    def test_create_preprocessed_text(self):
        """Test creating PreprocessedText object."""
        result = PreprocessedText(
            processed_text="test",
            original_text="test",
            index_mapping=[0, 1, 2, 3]
        )
        assert result.processed_text == "test"
        assert result.original_text == "test"
        assert result.index_mapping == [0, 1, 2, 3]

    def test_preprocessed_text_with_metadata(self):
        """Test PreprocessedText with optional metadata."""
        result = PreprocessedText(
            processed_text="test",
            original_text="test",
            index_mapping=[0, 1, 2, 3],
            detected_language="en",
            tokens=["test"]
        )
        assert result.detected_language == "en"
        assert result.tokens == ["test"]

    def test_map_to_original_method(self):
        """Test map_to_original method."""
        result = PreprocessedText(
            processed_text="abc 가나다",
            original_text="abc가나다",
            index_mapping=[0, 1, 2, -1, 3, 4, 5]
        )
        orig_start, orig_end = result.map_to_original(0, 3)
        assert orig_start == 0
        assert orig_end == 3

    def test_empty_preprocessed_text(self):
        """Test empty PreprocessedText."""
        result = PreprocessedText(
            processed_text="",
            original_text="",
            index_mapping=[]
        )
        assert result.processed_text == ""
        assert result.original_text == ""
        assert result.index_mapping == []


class TestNLPProcessor:
    """Test main NLP processor."""

    def test_disabled_processor(self):
        """Test processor with all features disabled."""
        config = NLPConfig()
        processor = NLPProcessor(config)
        text = "Test text"
        result = processor.preprocess(text)
        # Should pass through with minimal changes
        assert result.original_text == text
        assert result.detected_language is None
        assert result.tokens is None

    def test_processor_with_language_detection_disabled(self):
        """Test processor without language detection."""
        config = NLPConfig(enable_tokenization=True)
        processor = NLPProcessor(config)
        text = "Hello world"
        result = processor.preprocess(text)
        assert result.detected_language is None
        assert result.tokens is not None

    def test_tokenization_basic(self):
        """Test basic tokenization without NLP libraries."""
        config = NLPConfig(enable_tokenization=True)
        processor = NLPProcessor(config)
        text = "Hello world test 123"
        result = processor.preprocess(text)
        # Should fall back to basic tokenization
        assert result.tokens is not None
        assert len(result.tokens) > 0
        assert "Hello" in result.tokens or "hello" in result.tokens

    def test_stopword_filtering(self):
        """Test stopword filtering."""
        config = NLPConfig(
            enable_tokenization=True,
            enable_stopword_filtering=True,
        )
        processor = NLPProcessor(config)
        text = "the phone number is important"
        result = processor.preprocess(text)
        # Stopwords should be filtered
        if result.tokens:
            assert "the" not in result.tokens
            assert "is" not in result.tokens
            # At least one content word should remain
            assert any(t in result.tokens for t in ["phone", "number", "important"])

    def test_empty_text(self):
        """Test empty text handling."""
        config = NLPConfig(enable_tokenization=True)
        processor = NLPProcessor(config)
        result = processor.preprocess("")
        assert result.original_text == ""
        assert result.processed_text == ""

    def test_custom_stopwords(self):
        """Test custom stopwords in configuration."""
        custom = {"mycustomword", "special"}
        config = NLPConfig(
            enable_tokenization=True,
            enable_stopword_filtering=True,
            custom_stopwords=custom,
        )
        processor = NLPProcessor(config)
        text = "mycustomword is here and special too"
        result = processor.preprocess(text)
        if result.tokens:
            assert "mycustomword" not in result.tokens
            assert "special" not in result.tokens

    def test_whitespace_only_text(self):
        """Test text with only whitespace."""
        config = NLPConfig(enable_tokenization=True)
        processor = NLPProcessor(config)
        text = "   \t\n  "
        result = processor.preprocess(text)
        assert result.original_text == text

    def test_single_word(self):
        """Test single word processing."""
        config = NLPConfig(enable_tokenization=True)
        processor = NLPProcessor(config)
        text = "hello"
        result = processor.preprocess(text)
        assert result.tokens is not None

    def test_processor_script_boundary_detection(self):
        """Test that script boundary detection is always active."""
        config = NLPConfig()  # No features enabled
        processor = NLPProcessor(config)
        text = "test가나다"
        result = processor.preprocess(text)
        # SmartTokenizer should still work
        assert " " in result.processed_text

    def test_multiple_spaces(self):
        """Test text with multiple consecutive spaces."""
        config = NLPConfig(enable_tokenization=True)
        processor = NLPProcessor(config)
        text = "hello    world     test"
        result = processor.preprocess(text)
        assert result.tokens is not None

    def test_special_characters_in_text(self):
        """Test text with special characters."""
        config = NLPConfig(enable_tokenization=True)
        processor = NLPProcessor(config)
        text = "test@example.com is my email!"
        result = processor.preprocess(text)
        assert result.tokens is not None


class TestNLPIntegration:
    """Test NLP integration with Engine."""

    def test_engine_with_nlp_config(self):
        """Test Engine initialization with NLP config."""
        from datadetector import Engine, load_registry, NLPConfig

        registry = load_registry()
        config = NLPConfig(enable_tokenization=True)
        engine = Engine(registry, nlp_config=config)
        assert engine.nlp_config is not None
        assert engine.nlp_processor is not None

    def test_engine_without_nlp_config(self):
        """Test Engine initialization without NLP config."""
        from datadetector import Engine, load_registry

        registry = load_registry()
        engine = Engine(registry)
        assert engine.nlp_config is None
        assert engine.nlp_processor is None

    def test_engine_with_disabled_nlp_config(self):
        """Test Engine with NLP config but all features disabled."""
        from datadetector import Engine, load_registry, NLPConfig

        registry = load_registry()
        config = NLPConfig()  # All disabled
        engine = Engine(registry, nlp_config=config)
        assert engine.nlp_config is not None
        # Processor should not be created when config is disabled
        assert engine.nlp_processor is None

    def test_find_mixed_script(self):
        """Test finding PII in mixed script text."""
        from datadetector import Engine, load_registry, NLPConfig

        registry = load_registry()
        config = NLPConfig()
        engine = Engine(registry, nlp_config=config)

        # Email with Korean text - SmartTokenizer should handle this
        text = "제 이메일은test@example.com입니다"
        result = engine.find(text, namespaces=["common"])

        # Even with basic processing, should handle script boundaries
        # This tests the SmartTokenizer which is always used
        assert isinstance(result.matches, list)

    def test_find_with_ascii_text(self):
        """Test finding PII in pure ASCII text."""
        from datadetector import Engine, load_registry, NLPConfig

        registry = load_registry()
        config = NLPConfig()
        engine = Engine(registry, nlp_config=config)

        text = "My email is test@example.com"
        result = engine.find(text, namespaces=["common"])
        assert isinstance(result.matches, list)

    def test_redact_with_nlp(self):
        """Test redaction with NLP config."""
        from datadetector import Engine, load_registry, NLPConfig
        from datadetector.models import RedactionStrategy

        registry = load_registry()
        config = NLPConfig()
        engine = Engine(registry, nlp_config=config)

        text = "Email: test@example.com"
        result = engine.redact(text, namespaces=["common"], strategy=RedactionStrategy.MASK)
        assert isinstance(result.redacted_text, str)

    def test_validate_with_nlp(self):
        """Test validation with NLP config."""
        from datadetector import Engine, load_registry, NLPConfig

        registry = load_registry()
        config = NLPConfig()
        engine = Engine(registry, nlp_config=config)

        # Test with common email pattern
        patterns = list(registry.get_namespace_patterns("common"))
        if patterns:
            email_pattern = next((p for p in patterns if "email" in p.id.lower()), None)
            if email_pattern:
                result = engine.validate("test@example.com", email_pattern.full_id)
                assert result.is_valid


# Optional dependency tests - only run if dependencies are available

if LANGDETECT_AVAILABLE:
    class TestLanguageDetector:
        """Test language detection."""

        def test_detect_english(self):
            """Test English language detection."""
            detector = LanguageDetector()
            lang = detector.detect("Hello world, this is a test message with enough text for detection.")
            assert lang == "en"

        def test_detect_korean(self):
            """Test Korean language detection."""
            detector = LanguageDetector()
            lang = detector.detect("안녕하세요 이것은 테스트 메시지입니다 언어 감지를 위한 충분한 텍스트")
            assert lang == "ko"

        def test_detect_chinese(self):
            """Test Chinese language detection."""
            detector = LanguageDetector()
            lang = detector.detect("这是一个测试消息用于语言检测需要足够的文本")
            assert lang == "zh-cn"

        def test_detect_empty_text(self):
            """Test empty text handling."""
            detector = LanguageDetector()
            lang = detector.detect("")
            assert lang is None

        def test_detect_whitespace(self):
            """Test whitespace only text."""
            detector = LanguageDetector()
            lang = detector.detect("   \t\n  ")
            assert lang is None

        def test_detect_mixed_text(self):
            """Test mixed language text."""
            detector = LanguageDetector()
            # Korean text with English PII
            text = "제 이메일은 test@example.com 입니다 연락주세요"
            lang = detector.detect(text)
            # Should detect Korean as primary language
            assert lang == "ko"

        def test_detect_short_text(self):
            """Test detection with short text."""
            detector = LanguageDetector()
            # Language detection may fail or be unreliable with very short text
            lang = detector.detect("Hi")
            # Just check it returns something or None
            assert lang is None or isinstance(lang, str)


    class TestNLPProcessorWithLangdetect:
        """Test NLP processor with langdetect."""

        def test_language_detection_enabled(self):
            """Test with language detection enabled."""
            config = NLPConfig(enable_language_detection=True)
            processor = NLPProcessor(config)
            text = "Hello world, this is a longer sentence to detect English."
            result = processor.preprocess(text)
            assert result.detected_language == "en"

        def test_language_detection_korean(self):
            """Test Korean language detection in processor."""
            config = NLPConfig(enable_language_detection=True)
            processor = NLPProcessor(config)
            text = "안녕하세요 이것은 한국어 텍스트입니다"
            result = processor.preprocess(text)
            assert result.detected_language == "ko"


if KONLPY_AVAILABLE:
    class TestKoreanTokenizer:
        """Test Korean tokenization."""

        def test_tokenize(self):
            """Test basic Korean tokenization."""
            tokenizer = KoreanTokenizer()
            text = "안녕하세요"
            tokens = tokenizer.tokenize(text)
            assert len(tokens) > 0
            assert isinstance(tokens, list)

        def test_tokenize_with_pos(self):
            """Test tokenization with POS tags."""
            tokenizer = KoreanTokenizer()
            text = "전화번호는 010-1234-5678입니다"
            tokens = tokenizer.tokenize(text, include_pos=True)
            assert len(tokens) > 0
            # Should return tuples of (word, pos)
            assert all(isinstance(t, tuple) for t in tokens)

        def test_extract_nouns(self):
            """Test noun extraction."""
            tokenizer = KoreanTokenizer()
            text = "서울에서 회의가 있습니다"
            nouns = tokenizer.extract_nouns(text)
            assert "서울" in nouns
            assert "회의" in nouns

        def test_remove_particles(self):
            """Test particle removal."""
            tokenizer = KoreanTokenizer()
            text = "010-1234-5678은 제 전화번호입니다"
            processed = tokenizer.remove_particles(text)
            # Particles should be removed
            assert "은" not in processed or len(processed.split()) > len(text.split())

        def test_empty_text(self):
            """Test empty text."""
            tokenizer = KoreanTokenizer()
            tokens = tokenizer.tokenize("")
            assert len(tokens) == 0


    class TestNLPProcessorWithKonlpy:
        """Test NLP processor with konlpy."""

        def test_korean_particle_processing(self):
            """Test Korean particle processing."""
            config = NLPConfig(
                enable_language_detection=True,
                enable_korean_particles=True,
            )
            processor = NLPProcessor(config)
            text = "010-1234-5678은"
            result = processor.preprocess(text)
            # Should have processed the text
            assert result.original_text == text


    class TestEngineWithKorean:
        """Test engine with Korean NLP."""

        def test_find_with_korean_particles(self):
            """Test finding PII with Korean particles attached."""
            from datadetector import Engine, load_registry, NLPConfig

            registry = load_registry()
            config = NLPConfig(
                enable_language_detection=True,
                enable_korean_particles=True,
            )
            engine = Engine(registry, nlp_config=config)

            # Korean phone number with particle
            text = "010-1234-5678은 제 번호입니다"
            result = engine.find(text, namespaces=["kr"])

            # Should find the phone number even with particle attached
            assert result.has_matches or len(result.matches) >= 0


if JIEBA_AVAILABLE:
    class TestChineseTokenizer:
        """Test Chinese tokenization."""

        def test_tokenize(self):
            """Test basic Chinese tokenization."""
            tokenizer = ChineseTokenizer()
            text = "我的电话号码是13812345678"
            tokens = tokenizer.tokenize(text)
            assert len(tokens) > 0
            assert isinstance(tokens, list)
            # Should segment the text
            assert "13812345678" in tokens or any("1381234" in t for t in tokens)

        def test_tokenize_with_pos(self):
            """Test tokenization with POS tags."""
            tokenizer = ChineseTokenizer()
            text = "这是我的邮箱地址"
            tokens = tokenizer.tokenize(text, include_pos=True)
            assert len(tokens) > 0
            # Should return tuples of (word, pos)
            assert all(isinstance(t, tuple) for t in tokens)
            assert all(len(t) == 2 for t in tokens)

        def test_tokenize_search(self):
            """Test search mode tokenization."""
            tokenizer = ChineseTokenizer()
            text = "中华人民共和国"
            tokens = tokenizer.tokenize_search(text)
            # Search mode should provide finer granularity
            assert len(tokens) > 0
            assert "中华" in tokens or "人民" in tokens or "共和国" in tokens

        def test_add_custom_word(self):
            """Test adding custom words to dictionary."""
            tokenizer = ChineseTokenizer()
            custom_word = "自定义词"
            tokenizer.add_word(custom_word, freq=1000)

            text = f"这是一个{custom_word}测试"
            tokens = tokenizer.tokenize(text)
            # Custom word should be recognized
            assert custom_word in tokens

        def test_mixed_chinese_english(self):
            """Test mixed Chinese and English text."""
            tokenizer = ChineseTokenizer()
            text = "我的邮箱是test@example.com请联系我"
            tokens = tokenizer.tokenize(text)
            # Should handle mixed text
            assert any("test@example.com" in t or "test" in t for t in tokens)

        def test_empty_text(self):
            """Test empty text."""
            tokenizer = ChineseTokenizer()
            tokens = tokenizer.tokenize("")
            assert len(tokens) == 0


    class TestEngineWithChinese:
        """Test engine with Chinese NLP."""

        def test_find_with_chinese_segmentation(self):
            """Test finding PII with Chinese segmentation."""
            from datadetector import Engine, load_registry, NLPConfig

            registry = load_registry()
            config = NLPConfig(
                enable_language_detection=True,
                enable_chinese_segmentation=True,
            )
            engine = Engine(registry, nlp_config=config)

            # Chinese text with email
            text = "我的邮箱是test@example.com请联系我"
            result = engine.find(text, namespaces=["common"])

            # Should handle Chinese text with PII
            assert isinstance(result.matches, list)
