"""
NLP Features Example

This example demonstrates how to use NLP features for improved PII detection,
especially for CJK languages (Korean, Chinese) where text processing is complex.

Features demonstrated:
- Language detection
- Korean particle processing
- Chinese word segmentation
- Tokenization
- Stopword filtering
"""

from datadetector import Engine, load_registry, NLPConfig


def basic_example():
    """Basic example without NLP - particles prevent detection."""
    print("=" * 70)
    print("BASIC EXAMPLE (WITHOUT NLP)")
    print("=" * 70)

    registry = load_registry()
    engine = Engine(registry)

    # Korean text with particle attached to phone number
    text = "제 전화번호는 010-1234-5678은 입니다"

    result = engine.find(text, namespaces=["kr"])
    print(f"\nText: {text}")
    print(f"Matches found: {len(result.matches)}")
    for match in result.matches:
        print(f"  - {match.category}: {text[match.start:match.end]} at {match.start}:{match.end}")


def nlp_example():
    """Example with NLP - improved detection of Korean PII."""
    print("\n" + "=" * 70)
    print("NLP EXAMPLE (WITH KOREAN PARTICLE PROCESSING)")
    print("=" * 70)

    # Configure NLP with Korean particle processing
    nlp_config = NLPConfig(
        enable_language_detection=True,
        enable_korean_particles=True,
    )

    registry = load_registry()
    engine = Engine(registry, nlp_config=nlp_config)

    # Same text as before
    text = "제 전화번호는 010-1234-5678은 입니다"

    result = engine.find(text, namespaces=["kr"])
    print(f"\nText: {text}")
    print(f"Matches found: {len(result.matches)}")
    for match in result.matches:
        print(f"  - {match.category}: {text[match.start:match.end]} at {match.start}:{match.end}")


def full_nlp_pipeline():
    """Example with full NLP pipeline."""
    print("\n" + "=" * 70)
    print("FULL NLP PIPELINE")
    print("=" * 70)

    # Configure all NLP features
    nlp_config = NLPConfig(
        enable_language_detection=True,
        enable_tokenization=True,
        enable_stopword_filtering=True,
        enable_korean_particles=True,
        custom_stopwords={"안녕하세요"},  # Add custom stopwords
    )

    registry = load_registry()
    engine = Engine(registry, nlp_config=nlp_config)

    # Test with various Korean texts
    texts = [
        "안녕하세요, 제 이메일은 user@example.com입니다",
        "전화번호는 010-9876-5432이고 주소는 서울시입니다",
        "주민등록번호는 123456-1234567입니다",
    ]

    for text in texts:
        result = engine.find(text, namespaces=["kr", "common"])
        print(f"\nText: {text}")
        print(f"Matches found: {len(result.matches)}")
        for match in result.matches:
            matched_text = text[match.start:match.end]
            print(f"  - {match.category}: {matched_text}")


def mixed_language_example():
    """Example with mixed Korean and English text."""
    print("\n" + "=" * 70)
    print("MIXED LANGUAGE EXAMPLE (Korean)")
    print("=" * 70)

    nlp_config = NLPConfig(
        enable_language_detection=True,
        enable_korean_particles=True,
    )

    registry = load_registry()
    engine = Engine(registry, nlp_config=nlp_config)

    # Mixed Korean and English
    texts = [
        "Email: test@example.com입니다",
        "My phone: 010-1234-5678은 한국 번호입니다",
        "Credit card: 1234-5678-9012-3456을 사용합니다",
    ]

    for text in texts:
        result = engine.find(text, namespaces=["kr", "common"])
        print(f"\nText: {text}")
        print(f"Matches found: {len(result.matches)}")
        for match in result.matches:
            matched_text = text[match.start:match.end]
            print(f"  - {match.category}: {matched_text}")


def chinese_example():
    """Example with Chinese text segmentation."""
    print("\n" + "=" * 70)
    print("CHINESE SEGMENTATION EXAMPLE")
    print("=" * 70)

    # Configure NLP with Chinese segmentation
    nlp_config = NLPConfig(
        enable_language_detection=True,
        enable_chinese_segmentation=True,
        enable_stopword_filtering=True,
    )

    registry = load_registry()
    engine = Engine(registry, nlp_config=nlp_config)

    # Chinese text (no spaces between words)
    texts = [
        "我的电话号码是13812345678请联系我",
        "邮箱地址test@example.com是公司邮箱",
        "身份证号码是123456789012345678",
    ]

    for text in texts:
        result = engine.find(text, namespaces=["common"])
        print(f"\nText: {text}")
        print(f"Matches found: {len(result.matches)}")
        for match in result.matches:
            matched_text = text[match.start:match.end]
            print(f"  - {match.category}: {matched_text}")


def redaction_with_nlp():
    """Example of redaction with NLP preprocessing."""
    print("\n" + "=" * 70)
    print("REDACTION WITH NLP")
    print("=" * 70)

    nlp_config = NLPConfig(
        enable_language_detection=True,
        enable_korean_particles=True,
    )

    registry = load_registry()
    engine = Engine(registry, nlp_config=nlp_config)

    text = "제 정보: 전화 010-1234-5678, 이메일 user@example.com입니다"

    # Redact with different strategies
    from datadetector.models import RedactionStrategy

    for strategy in [RedactionStrategy.MASK, RedactionStrategy.HASH]:
        result = engine.redact(text, namespaces=["kr", "common"], strategy=strategy)
        print(f"\nStrategy: {strategy.value}")
        print(f"Original:  {result.original_text}")
        print(f"Redacted:  {result.redacted_text}")
        print(f"Redactions: {result.redaction_count}")


def standalone_nlp_components():
    """Example using NLP components standalone."""
    print("\n" + "=" * 70)
    print("STANDALONE NLP COMPONENTS")
    print("=" * 70)

    from datadetector.nlp import (
        LanguageDetector,
        KoreanTokenizer,
        ChineseTokenizer,
        StopwordFilter,
        SmartTokenizer,
        LANGDETECT_AVAILABLE,
        KONLPY_AVAILABLE,
        JIEBA_AVAILABLE,
    )

    # 1. Language Detection
    if LANGDETECT_AVAILABLE:
        print("\n--- Language Detection ---")
        detector = LanguageDetector()
        texts = [
            "Hello world",
            "안녕하세요",
            "こんにちは",
        ]
        for text in texts:
            lang = detector.detect(text)
            print(f"{text}: {lang}")

    # 2. Korean Tokenization
    if KONLPY_AVAILABLE:
        print("\n--- Korean Tokenization ---")
        tokenizer = KoreanTokenizer()
        text = "안녕하세요. 전화번호는 010-1234-5678입니다."
        tokens = tokenizer.tokenize(text)
        print(f"Text: {text}")
        print(f"Tokens: {tokens}")

        # Remove particles
        processed = tokenizer.remove_particles(text)
        print(f"Without particles: {processed}")

    # 3. Chinese Tokenization
    if JIEBA_AVAILABLE:
        print("\n--- Chinese Tokenization ---")
        tokenizer = ChineseTokenizer()
        text = "我的电话号码是13812345678请联系我"
        tokens = tokenizer.tokenize(text)
        print(f"Text: {text}")
        print(f"Tokens: {tokens}")

        # Search mode (finer granularity)
        search_tokens = tokenizer.tokenize_search(text)
        print(f"Search tokens: {search_tokens}")

    # 4. Stopword Filtering
    print("\n--- Stopword Filtering ---")
    filter = StopwordFilter()
    tokens = ["the", "phone", "number", "is", "123-456-7890"]
    filtered = filter.filter_tokens(tokens)
    print(f"Original tokens: {tokens}")
    print(f"Filtered tokens: {filtered}")

    # 4. Smart Tokenization (Script Boundary Detection)
    print("\n--- Smart Tokenization ---")
    tokenizer = SmartTokenizer()
    texts = [
        "010-1234-5678은",
        "test@example.com입니다",
    ]
    for text in texts:
        prepared, mapping = tokenizer.prepare_text_for_search(text)
        print(f"Original:  '{text}'")
        print(f"Prepared:  '{prepared}'")


def configuration_examples():
    """Show different NLP configuration options."""
    print("\n" + "=" * 70)
    print("CONFIGURATION OPTIONS")
    print("=" * 70)

    # Minimal config - just script boundary detection (always enabled)
    config1 = NLPConfig()
    print("\n1. Default (No NLP):")
    print(f"   - Language detection: {config1.enable_language_detection}")
    print(f"   - Tokenization: {config1.enable_tokenization}")
    print(f"   - Stopword filtering: {config1.enable_stopword_filtering}")
    print(f"   - Korean particles: {config1.enable_korean_particles}")

    # Language detection only
    config2 = NLPConfig(enable_language_detection=True)
    print("\n2. Language Detection Only:")
    print("   - Detects text language for better processing")

    # Korean-focused config
    config3 = NLPConfig(
        enable_language_detection=True,
        enable_korean_particles=True,
    )
    print("\n3. Korean-Focused:")
    print("   - Language detection enabled")
    print("   - Korean particle removal enabled")

    # Chinese-focused config
    config4 = NLPConfig(
        enable_language_detection=True,
        enable_chinese_segmentation=True,
        enable_stopword_filtering=True,
    )
    print("\n4. Chinese-Focused:")
    print("   - Language detection enabled")
    print("   - Chinese word segmentation enabled")
    print("   - Stopword filtering enabled")

    # Full pipeline
    config5 = NLPConfig(
        enable_language_detection=True,
        enable_tokenization=True,
        enable_stopword_filtering=True,
        enable_korean_particles=True,
        enable_chinese_segmentation=True,
        custom_stopwords={"custom1", "custom2"},
    )
    print("\n5. Full NLP Pipeline (All Languages):")
    print("   - All features enabled")
    print("   - Korean + Chinese + general tokenization")
    print("   - Custom stopwords added")

    # Performance consideration
    print("\n\nPerformance Considerations:")
    print("- NLP processing adds overhead (acceptable for most use cases)")
    print("- Korean tokenization (konlpy) is slower but more accurate")
    print("- Enable only the features you need")
    print("- For high-throughput pipelines, consider Go implementation")


def main():
    """Run all examples."""
    print("Data Detector - NLP Features Examples")
    print("=" * 70)

    # Show configuration options
    configuration_examples()

    # Check dependencies
    from datadetector.nlp import LANGDETECT_AVAILABLE, KONLPY_AVAILABLE, JIEBA_AVAILABLE

    print("\n\nDependency Status:")
    print(f"  langdetect: {'✓ Installed' if LANGDETECT_AVAILABLE else '✗ Not installed'}")
    print(f"  konlpy:     {'✓ Installed' if KONLPY_AVAILABLE else '✗ Not installed'}")
    print(f"  jieba:      {'✓ Installed' if JIEBA_AVAILABLE else '✗ Not installed'}")

    if not LANGDETECT_AVAILABLE or not KONLPY_AVAILABLE or not JIEBA_AVAILABLE:
        print("\nTo install NLP dependencies:")
        print("  pip install data-detector[nlp]")
        print("\nNotes:")
        print("  - konlpy requires Java runtime for Korean tokenization")
        print("  - jieba is pure Python (no additional dependencies)")

    # Run examples
    basic_example()

    if KONLPY_AVAILABLE:
        nlp_example()
        full_nlp_pipeline()
        mixed_language_example()

    if JIEBA_AVAILABLE:
        chinese_example()

    if KONLPY_AVAILABLE or JIEBA_AVAILABLE:
        redaction_with_nlp()

    if LANGDETECT_AVAILABLE or KONLPY_AVAILABLE or JIEBA_AVAILABLE:
        standalone_nlp_components()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
