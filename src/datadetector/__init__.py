"""
data-detector: A general-purpose engine for detecting and masking personal information.

This package provides tools for PII detection, validation, and redaction using
pattern-based matching organized by country and information type.
"""

__version__ = "0.0.2"

from datadetector.async_engine import AsyncEngine
from datadetector.bulk_generator import BulkDataGenerator
from datadetector.engine import Engine
from datadetector.fake_file_generators import (
    ImageGenerator,
    OfficeFileGenerator,
    PDFGenerator,
    XMLGenerator,
)
from datadetector.fake_generator import FakeDataGenerator
from datadetector.models import FindResult, RedactionResult, ValidationResult
from datadetector.registry import PatternRegistry, load_registry
from datadetector.yaml_utils import (
    PatternFileHandler,
    YAMLHandler,
    read_yaml,
    update_yaml,
    write_yaml,
)

__all__ = [
    "Engine",
    "AsyncEngine",
    "load_registry",
    "PatternRegistry",
    "FindResult",
    "ValidationResult",
    "RedactionResult",
    "FakeDataGenerator",
    "BulkDataGenerator",
    "OfficeFileGenerator",
    "ImageGenerator",
    "PDFGenerator",
    "XMLGenerator",
    "YAMLHandler",
    "PatternFileHandler",
    "read_yaml",
    "write_yaml",
    "update_yaml",
]
