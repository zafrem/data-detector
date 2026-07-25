# NLP Features

Data Detector includes advanced Natural Language Processing (NLP) features to improve PII detection accuracy, especially for languages like Korean where grammatical particles are often attached directly to PII without spaces.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Features](#features)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Performance Considerations](#performance-considerations)
- [API Reference](#api-reference)

## Overview

NLP features enhance PII detection by:

1. **Language Detection**: Automatically identifies the language of input text
2. **Korean Particle Processing**: Removes Korean grammatical particles (은/는/이/가/을/를) that are attached to PII
3. **Chinese Word Segmentation**: Segments Chinese text which has no spaces between words
4. **Tokenization**: Breaks text into meaningful units for better pattern matching
5. **Stopword Filtering**: Removes common functional words that don't contain PII
6. **Script Boundary Detection**: Inserts spaces at transitions between Latin and CJK characters

### Why NLP for PII Detection?

**Korean**: Grammatical particles are often attached directly to PII:

```
❌ Without NLP: "010-1234-5678은" → Pattern doesn't match because of "은"
✅ With NLP:    "010-1234-5678은" → Preprocessed to "010-1234-5678 은" → Matches!
```

**Chinese**: No spaces between words, making it hard to detect PII boundaries:

```
❌ Without NLP: "我的电话号码是13812345678请联系我" → Hard to identify where PII starts/ends
✅ With NLP:    "我的电话号码是13812345678请联系我" → Segmented to "我/的/电话号码/是/13812345678/请/联系/我"
```

## Installation

NLP features require additional dependencies. Install them with:

```bash
pip install data-detector[nlp]
```

This installs:
- `konlpy` - Korean word segmentation (requires Java)
- `jieba` - Chinese word segmentation
- `sudachipy` & `sudachidict_core` - Japanese word segmentation
- `langdetect` - Language detection


### Korean Tokenization Setup

`konlpy` requires Java (JDK 1.7+) to be installed:

```bash
# macOS
brew install java

# Ubuntu/Debian
sudo apt-get install openjdk-11-jdk

# Windows
# Download and install from https://www.oracle.com/java/technologies/downloads/
```

## Features

### 1. Language Detection

Automatically detects the language of input text to enable language-specific processing.

```python
from datadetector import NLPConfig, Engine, load_registry

nlp_config = NLPConfig(enable_language_detection=True)
engine = Engine(load_registry(), nlp_config=nlp_config)
```

**Supported Languages**: All languages supported by `langdetect` (50+ languages)

### 2. Korean Particle Processing

Removes Korean grammatical particles (조사) that are attached to PII:

**Common Korean Particles**:
- Subject markers: 은/는, 이/가
- Object markers: 을/를
- Other particles: 의, 에, 에서, 로/으로, 와/과, 도, 만, etc.

```python
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_korean_particles=True
)
```

**Example**:
```
Input:  "010-1234-5678은 제 번호입니다"
Output: Phone number detected at correct position
```

### 3. Chinese Word Segmentation

Segments Chinese text into words using jieba (结巴).

Chinese text has no spaces between words, so segmentation is essential for accurate PII detection.

```python
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_chinese_segmentation=True
)
```

**Features**:
- Automatic word segmentation
- Search mode for finer granularity
- Custom dictionary support for domain-specific terms
- POS tagging support

**Example**:
```python
from datadetector import ChineseTokenizer

tokenizer = ChineseTokenizer()
text = "我的电话号码是13812345678"
tokens = tokenizer.tokenize(text)
# Result: ['我', '的', '电话号码', '是', '13812345678']
```

### 4. Tokenization

Breaks text into tokens for analysis:

- **Korean**: Uses konlpy (morphological analysis)
- **Chinese**: Uses jieba (word segmentation)
- **Japanese**: Uses sudachipy (word segmentation)
- **Other**: Basic whitespace tokenization


```python
nlp_config = NLPConfig(enable_tokenization=True)
```

### 5. Stopword Filtering

Removes common functional words that rarely contain PII:

**Korean Stopwords**: 은, 는, 이, 가, 을, 를, 의, 도, 만, etc.
**Chinese Stopwords**: 的, 了, 在, 是, 我, 有, 和, 就, 不, etc.
**English Stopwords**: a, an, the, is, are, in, on, at, etc.

```python
nlp_config = NLPConfig(
    enable_tokenization=True,
    enable_stopword_filtering=True
)
```

You can also add custom stopwords:

```python
nlp_config = NLPConfig(
    enable_stopword_filtering=True,
    custom_stopwords={"mycompany", "internal"}
)
```

### 6. Script Boundary Detection

Automatically enabled for all engines. Inserts spaces at transitions between:
- Latin/ASCII ↔ CJK (Hangul, Hanzi, Kana)
- Numbers ↔ CJK

This is always active and doesn't require configuration.

## Configuration

### NLPConfig Options

```python
from datadetector import NLPConfig

config = NLPConfig(
    # Enable language detection (requires langdetect)
    enable_language_detection: bool = False,

    # Enable tokenization (requires konlpy for Korean)
    enable_tokenization: bool = False,

    # Enable stopword filtering
    enable_stopword_filtering: bool = False,

    # Enable Korean particle processing (requires konlpy)
    enable_korean_particles: bool = False,

    # Enable Chinese word segmentation (requires jieba)
    enable_chinese_segmentation=False,

    # Enable Japanese word segmentation (requires sudachipy)
    enable_japanese_segmentation=False,

    # Custom stopwords to add
    custom_stopwords: set = set(),

    # Korean tokenizer backend (okt, komoran, mecab, hannanum, kkma)
    korean_tokenizer: str = "okt"
)
```

### Recommended Configurations

#### Minimal (Script Boundary Only)
```python
# No config needed - script boundary detection always enabled
engine = Engine(load_registry())
```

#### Korean-Focused
```python
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_korean_particles=True
)
```

#### Chinese-Focused
```python
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_chinese_segmentation=True,
    enable_stopword_filtering=True
)
```

#### Full NLP Pipeline (All Languages)
```python
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_tokenization=True,
    enable_stopword_filtering=True,
    enable_korean_particles=True,
    enable_chinese_segmentation=True
)
```

## Usage Examples

### Basic Usage

```python
from datadetector import Engine, load_registry, NLPConfig

# Configure NLP
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_korean_particles=True
)

# Create engine with NLP
registry = load_registry()
engine = Engine(registry, nlp_config=nlp_config)

# Detect PII in Korean text
text = "제 전화번호는 010-1234-5678은 입니다"
result = engine.find(text, namespaces=["kr"])

print(f"Found {len(result.matches)} matches")
```

### Mixed Language Text

```python
# Korean + English
text = "Email: user@example.com입니다"
result = engine.find(text, namespaces=["common"])

# Chinese + English
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_chinese_segmentation=True
)
engine = Engine(load_registry(), nlp_config=nlp_config)
text = "我的邮箱是test@example.com请联系我"
result = engine.find(text, namespaces=["common"])
```

### Redaction with NLP

```python
from datadetector.models import RedactionStrategy

text = "전화 010-1234-5678, 이메일 user@example.com"
result = engine.redact(
    text,
    namespaces=["kr", "common"],
    strategy=RedactionStrategy.MASK
)

print(f"Redacted: {result.redacted_text}")
```

### Standalone NLP Components

You can use NLP components independently:

```python
from datadetector.nlp import (
    LanguageDetector,
    KoreanTokenizer,
    StopwordFilter,
    SmartTokenizer
)

# Language detection
detector = LanguageDetector()
lang = detector.detect("안녕하세요")  # Returns 'ko'

# Korean tokenization
tokenizer = KoreanTokenizer()
tokens = tokenizer.tokenize("전화번호는 010-1234-5678입니다")

# Remove particles
clean_text = tokenizer.remove_particles("010-1234-5678은")

# Stopword filtering
stopword_filter = StopwordFilter()
filtered = stopword_filter.filter_tokens(["the", "phone", "number"])

# Script boundary detection
smart_tokenizer = SmartTokenizer()
prepared, mapping = smart_tokenizer.prepare_text_for_search("010-1234-5678은")
```

## Performance Considerations

### Speed Impact

NLP processing adds computational overhead:

| Feature | Relative Speed | Impact |
|---------|---------------|---------|
| Script Boundary Detection | ~1.1x | Minimal |
| Language Detection | ~1.2x | Low |
| Korean Particle Processing | ~2-3x | Moderate |
| Full Tokenization | ~3-5x | Higher |

### Recommendations

1. **High-throughput scenarios**: Use minimal NLP or no NLP
2. **Korean text processing**: Enable language detection + particle processing
3. **General use**: Enable only features you need
4. **Future pipelines**: Consider Go implementation for production

### Optimization Tips

```python
# ✅ Enable only what you need
config = NLPConfig(enable_korean_particles=True)  # Just particles

# ❌ Don't enable everything if not needed
config = NLPConfig(
    enable_language_detection=True,
    enable_tokenization=True,
    enable_stopword_filtering=True,
    enable_korean_particles=True
)
```

## API Reference

### NLPConfig

Configuration class for NLP features.

```python
class NLPConfig:
    enable_language_detection: bool = False
    enable_tokenization: bool = False
    enable_stopword_filtering: bool = False
    enable_korean_particles: bool = False
    custom_stopwords: Set[str] = field(default_factory=set)
    korean_tokenizer: str = "okt"

    def is_enabled(self) -> bool:
        """Check if any NLP feature is enabled."""

    def validate(self) -> None:
        """Validate configuration and check dependencies."""
```

### NLPProcessor

Main NLP processor that combines all features.

```python
class NLPProcessor:
    def __init__(self, config: Optional[NLPConfig] = None):
        """Initialize with configuration."""

    def preprocess(self, text: str) -> PreprocessedText:
        """Preprocess text with enabled NLP features."""
```

### LanguageDetector

Detects the language of text.

```python
class LanguageDetector:
    def detect(self, text: str) -> Optional[str]:
        """
        Detect language of text.

        Returns:
            ISO 639-1 language code (e.g., 'ko', 'en', 'ja') or None
        """
```

### KoreanTokenizer

Korean language tokenization using konlpy.

```python
class KoreanTokenizer:
    def __init__(self, backend: str = "okt"):
        """Initialize with backend (okt, komoran, mecab, etc.)."""

    def tokenize(self, text: str, include_pos: bool = False) -> List[str]:
        """Tokenize Korean text."""

    def extract_nouns(self, text: str) -> List[str]:
        """Extract only nouns from text."""

    def remove_particles(self, text: str) -> str:
        """Remove Korean particles from text."""
```

### ChineseTokenizer

Chinese word segmentation using jieba.

```python
class ChineseTokenizer:
    def __init__(self):
        """Initialize Chinese tokenizer."""

    def tokenize(self, text: str, include_pos: bool = False) -> List[str]:
        """
        Tokenize Chinese text.

        Args:
            text: Input text
            include_pos: Include part-of-speech tags

        Returns:
            List of tokens (or token/pos tuples if include_pos=True)
        """

    def tokenize_search(self, text: str) -> List[str]:
        """
        Tokenize for search mode (finer granularity).
        Splits compound words for better search matching.
        """

    def extract_keywords(self, text: str, topk: int = 10) -> List[str]:
        """Extract keywords from text using TF-IDF."""

    def add_word(self, word: str, freq: Optional[int] = None, tag: Optional[str] = None) -> None:
        """
        Add custom word to dictionary.
        Useful for domain-specific terms or PII patterns.
        """
```

### StopwordFilter

Filters stopwords from text.

```python
class StopwordFilter:
    def __init__(self, custom_stopwords: Optional[Set[str]] = None):
        """Initialize with optional custom stopwords."""

    def filter_tokens(self, tokens: List[str]) -> List[str]:
        """Remove stopwords from token list."""

    def is_stopword(self, word: str) -> bool:
        """Check if a word is a stopword."""
```

### SmartTokenizer

Script boundary detection (always enabled).

```python
class SmartTokenizer:
    def prepare_text_for_search(self, text: str) -> Tuple[str, List[int]]:
        """
        Prepare text by inserting spaces at script boundaries.

        Returns:
            Tuple of (prepared_text, index_mapping)
        """

    def map_match_to_original(
        self,
        match_start: int,
        match_end: int,
        mapping: List[int]
    ) -> Tuple[int, int]:
        """Map positions from prepared text back to original."""
```

## Troubleshooting

### konlpy Installation Issues

If konlpy fails to install:

1. **Ensure Java is installed**:
   ```bash
   java -version  # Should show 1.7+
   ```

2. **Install Java if needed**:
   ```bash
   # macOS
   brew install openjdk@11

   # Ubuntu/Debian
   sudo apt-get install openjdk-11-jdk
   ```

3. **Set JAVA_HOME** (if needed):
   ```bash
   export JAVA_HOME=$(/usr/libexec/java_home)  # macOS
   export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64  # Linux
   ```

### Import Errors

If you get import errors for NLP features:

```python
from datadetector.nlp import LANGDETECT_AVAILABLE, KONLPY_AVAILABLE

if not LANGDETECT_AVAILABLE:
    print("Install: pip install langdetect")

if not KONLPY_AVAILABLE:
    print("Install: pip install konlpy")
```

### Performance Issues

If NLP processing is too slow:

1. Disable features you don't need
2. Use language detection only (fastest NLP feature)
3. Consider batch processing
4. For production, plan to use Go implementation

## Future Enhancements

Planned improvements:

- [ ] Support for more tokenizer backends (Mecab, Komoran)
- [ ] Chinese and Japanese particle processing
- [ ] Custom language models
- [ ] Caching for repeated text
- [ ] Parallel processing for batch operations
- [ ] Go implementation for high-performance pipelines

## See Also

- [Examples](../examples/nlp_example.py) - Comprehensive usage examples
- [Tests](../tests/test_nlp.py) - Test suite with more examples
- [API Reference](api-reference.md) - Full API documentation
- [Architecture](ARCHITECTURE.md) - System architecture
