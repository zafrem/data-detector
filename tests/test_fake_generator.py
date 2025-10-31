"""Tests for fake data generators."""

import csv
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from datadetector import FakeDataGenerator, load_registry


@pytest.fixture
def generator():
    """Create FakeDataGenerator instance."""
    return FakeDataGenerator(seed=12345)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestPatternGeneration:
    """Tests for generating data from specific patterns."""

    def test_from_pattern_email(self, generator):
        """Test generating email from pattern."""
        email = generator.from_pattern("comm/email_01")
        assert "@" in email
        assert "." in email

    def test_from_pattern_phone_us(self, generator):
        """Test generating US phone number."""
        phone = generator.from_pattern("us/phone_01")
        assert len(phone) <= 14
        assert any(c.isdigit() for c in phone)

    def test_from_pattern_korean_mobile(self, generator):
        """Test generating Korean mobile number."""
        mobile = generator.from_pattern("kr/mobile_01")
        assert mobile.startswith("010-")
        assert len(mobile) == 13  # 010-XXXX-XXXX

    def test_from_pattern_ssn(self, generator):
        """Test generating SSN."""
        ssn = generator.from_pattern("us/ssn_01")
        assert len(ssn) == 11  # XXX-XX-XXXX
        assert ssn[3] == "-" and ssn[6] == "-"

    def test_from_pattern_korean_rrn(self, generator):
        """Test generating Korean RRN."""
        rrn = generator.from_pattern("kr/rrn_01")
        assert len(rrn) == 14  # YYMMDD-GNNNNNN
        assert rrn[6] == "-"

    def test_from_pattern_credit_card(self, generator):
        """Test generating credit card number."""
        visa = generator.from_pattern("comm/credit_card_visa_01")
        assert len(visa) >= 13
        assert visa[0] == "4"  # Visa starts with 4

    def test_from_pattern_aws_key(self, generator):
        """Test generating AWS access key."""
        key = generator.from_pattern("comm/aws_access_key_01")
        assert key.startswith("AKIA")
        assert len(key) == 20

    def test_from_pattern_github_token(self, generator):
        """Test generating GitHub token."""
        token = generator.from_pattern("comm/github_token_01")
        assert token.startswith("ghp_")
        assert len(token) == 40

    def test_from_pattern_google_api_key(self, generator):
        """Test generating Google API key."""
        key = generator.from_pattern("comm/google_api_key_01")
        assert key.startswith("AIza")
        assert len(key) == 39

    def test_from_pattern_ipv4(self, generator):
        """Test generating IPv4 address."""
        ip = generator.from_pattern("comm/ipv4_01")
        parts = ip.split(".")
        assert len(parts) == 4
        assert all(0 <= int(p) <= 255 for p in parts)

    def test_from_pattern_zipcode_us(self, generator):
        """Test generating US zipcode."""
        zipcode = generator.from_pattern("us/zipcode_01")
        assert len(zipcode) in [5, 10]  # XXXXX or XXXXX-XXXX

    def test_from_pattern_zipcode_kr(self, generator):
        """Test generating Korean zipcode."""
        zipcode = generator.from_pattern("kr/zipcode_01")
        assert len(zipcode) == 5
        assert zipcode.isdigit()

    def test_from_pattern_url(self, generator):
        """Test generating URL."""
        url = generator.from_pattern("comm/url_01")
        assert url.startswith(("http://", "https://"))

    def test_from_pattern_coordinates(self, generator):
        """Test generating coordinates."""
        lat = generator.from_pattern("comm/latitude_01")
        lon = generator.from_pattern("comm/longitude_01")
        assert -90 <= float(lat) <= 90
        assert -180 <= float(lon) <= 180

    def test_unsupported_pattern(self, generator):
        """Test error handling for unsupported pattern."""
        with pytest.raises(ValueError, match="not supported"):
            generator.from_pattern("invalid/pattern_99")

    def test_supported_patterns(self, generator):
        """Test getting list of supported patterns."""
        patterns = generator.supported_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert "comm/email_01" in patterns
        assert "us/ssn_01" in patterns


class TestTextGeneration:
    """Tests for generating text with PII."""

    def test_generate_text_with_pii_basic(self, generator):
        """Test generating text with PII."""
        text = generator.generate_text_with_pii(num_records=5)
        assert "Record 1:" in text
        assert "Record 5:" in text
        assert "Name:" in text
        assert "Email:" in text

    def test_generate_text_with_pii_patterns(self, generator):
        """Test generating text with specific patterns."""
        text = generator.generate_text_with_pii(
            num_records=3, include_patterns=["us/ssn_01", "comm/ipv4_01"]
        )
        assert "Record 1:" in text
        assert "Email:" in text  # Always included

    def test_generate_text_with_pii_empty(self, generator):
        """Test generating empty text."""
        text = generator.generate_text_with_pii(num_records=0)
        assert text == ""


class TestCSVGeneration:
    """Tests for generating CSV files."""

    def test_create_csv_file_basic(self, generator, temp_dir):
        """Test creating basic CSV file."""
        csv_path = temp_dir / "test.csv"
        generator.create_csv_file(csv_path, rows=10, include_pii=True)

        assert csv_path.exists()

        # Read and verify
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 10
        assert "name" in rows[0]
        assert "email" in rows[0]
        assert "ssn" in rows[0]

    def test_create_csv_file_no_pii(self, generator, temp_dir):
        """Test creating CSV without PII."""
        csv_path = temp_dir / "test_no_pii.csv"
        generator.create_csv_file(csv_path, rows=5, include_pii=False)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 5
        assert "ssn" not in rows[0]
        assert "credit_card" not in rows[0]

    def test_create_csv_file_large(self, generator, temp_dir):
        """Test creating large CSV file."""
        csv_path = temp_dir / "test_large.csv"
        generator.create_csv_file(csv_path, rows=1000, include_pii=True)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            row_count = sum(1 for _ in reader) - 1  # Exclude header

        assert row_count == 1000


class TestJSONGeneration:
    """Tests for generating JSON files."""

    def test_create_json_file_basic(self, generator, temp_dir):
        """Test creating basic JSON file."""
        json_path = temp_dir / "test.json"
        generator.create_json_file(json_path, records=10, include_pii=True)

        assert json_path.exists()

        # Read and verify
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 10
        assert "name" in data[0]
        assert "email" in data[0]
        assert "ssn" in data[0]
        assert "address" in data[0]
        assert "city" in data[0]["address"]

    def test_create_json_file_no_pii(self, generator, temp_dir):
        """Test creating JSON without PII."""
        json_path = temp_dir / "test_no_pii.json"
        generator.create_json_file(json_path, records=5, include_pii=False)

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 5
        assert "ssn" not in data[0]
        assert "credit_card" not in data[0]

    def test_create_json_file_structure(self, generator, temp_dir):
        """Test JSON structure."""
        json_path = temp_dir / "test_structure.json"
        generator.create_json_file(json_path, records=1, include_pii=True)

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        record = data[0]
        assert isinstance(record["id"], int)
        assert isinstance(record["address"], dict)
        assert "street" in record["address"]
        assert "created_at" in record


class TestSQLiteGeneration:
    """Tests for generating SQLite files."""

    def test_create_sqlite_file_basic(self, generator, temp_dir):
        """Test creating basic SQLite file."""
        db_path = temp_dir / "test.db"
        generator.create_sqlite_file(db_path, records=10, include_pii=True)

        assert db_path.exists()

        # Read and verify
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 10

    def test_create_sqlite_file_schema(self, generator, temp_dir):
        """Test SQLite schema with PII."""
        db_path = temp_dir / "test_schema.db"
        generator.create_sqlite_file(db_path, records=5, include_pii=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "name" in columns
        assert "email" in columns
        assert "ssn" in columns
        assert "credit_card" in columns

    def test_create_sqlite_file_no_pii(self, generator, temp_dir):
        """Test SQLite schema without PII."""
        db_path = temp_dir / "test_no_pii.db"
        generator.create_sqlite_file(db_path, records=5, include_pii=False)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "ssn" not in columns
        assert "credit_card" not in columns

    def test_create_sqlite_file_data(self, generator, temp_dir):
        """Test SQLite data integrity."""
        db_path = temp_dir / "test_data.db"
        generator.create_sqlite_file(db_path, records=3, include_pii=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 1  # ID
        assert row[1]  # Name
        assert "@" in row[2]  # Email


class TestLogGeneration:
    """Tests for generating log files."""

    def test_create_log_file_apache(self, generator, temp_dir):
        """Test creating Apache-style log file."""
        log_path = temp_dir / "test_apache.log"
        generator.create_log_file(log_path, lines=100, include_pii=True, log_format="apache")

        assert log_path.exists()

        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 100
        # Apache format: IP - - [timestamp] "METHOD /path HTTP/1.1" status size
        assert "HTTP/1.1" in lines[0]
        assert "[" in lines[0] and "]" in lines[0]

    def test_create_log_file_json(self, generator, temp_dir):
        """Test creating JSON-formatted log file."""
        log_path = temp_dir / "test_json.log"
        generator.create_log_file(log_path, lines=50, include_pii=True, log_format="json")

        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 50
        # Each line should be valid JSON
        log_entry = json.loads(lines[0])
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "ip" in log_entry

    def test_create_log_file_syslog(self, generator, temp_dir):
        """Test creating syslog-style log file."""
        log_path = temp_dir / "test_syslog.log"
        generator.create_log_file(log_path, lines=50, include_pii=True, log_format="syslog")

        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 50
        # Syslog format: timestamp hostname process[pid]: message
        assert "[" in lines[0] and "]" in lines[0]

    def test_create_log_file_no_pii(self, generator, temp_dir):
        """Test creating log without embedded PII."""
        log_path = temp_dir / "test_no_pii.log"
        generator.create_log_file(log_path, lines=100, include_pii=False, log_format="apache")

        # PII should appear less frequently or not in query strings
        assert log_path.exists()


class TestTextFileGeneration:
    """Tests for generating plain text files."""

    def test_create_text_file_basic(self, generator, temp_dir):
        """Test creating basic text file."""
        text_path = temp_dir / "test.txt"
        generator.create_text_file(text_path, paragraphs=10, include_pii=True)

        assert text_path.exists()

        with open(text_path, encoding="utf-8") as f:
            content = f.read()

        # Should have multiple paragraphs (separated by blank lines)
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        assert len(paragraphs) >= 5

    def test_create_text_file_no_pii(self, generator, temp_dir):
        """Test creating text file without PII."""
        text_path = temp_dir / "test_no_pii.txt"
        generator.create_text_file(text_path, paragraphs=5, include_pii=False)

        assert text_path.exists()

    def test_create_text_file_content(self, generator, temp_dir):
        """Test text file content."""
        text_path = temp_dir / "test_content.txt"
        generator.create_text_file(text_path, paragraphs=20, include_pii=True)

        with open(text_path, encoding="utf-8") as f:
            content = f.read()

        # Some paragraphs should have contact info
        assert len(content) > 100


class TestGeneratorConfiguration:
    """Tests for generator configuration."""

    def test_custom_locale(self):
        """Test creating generator with custom locale."""
        generator = FakeDataGenerator(locale="ko_KR")
        name = generator.from_pattern("kr/korean_name_01")
        # Should generate Korean name
        assert len(name) >= 2

    def test_seed_reproducibility(self):
        """Test that seed produces reproducible results."""
        gen1 = FakeDataGenerator(seed=42)
        gen2 = FakeDataGenerator(seed=42)

        email1 = gen1.from_pattern("comm/email_01")
        email2 = gen2.from_pattern("comm/email_01")

        assert email1 == email2

    def test_different_seeds(self):
        """Test that different seeds produce different results."""
        gen1 = FakeDataGenerator(seed=42)
        gen2 = FakeDataGenerator(seed=99)

        email1 = gen1.from_pattern("comm/email_01")
        email2 = gen2.from_pattern("comm/email_01")

        # Very unlikely to be the same
        assert email1 != email2


class TestIntegrationWithDetector:
    """Tests for integration between generator and detector."""

    def test_generated_data_detectable(self, generator, temp_dir):
        """Test that generated fake data can be detected."""
        from datadetector import Engine

        # Generate CSV with PII
        csv_path = temp_dir / "test_detect.csv"
        generator.create_csv_file(csv_path, rows=10, include_pii=True)

        # Read CSV content
        with open(csv_path, encoding="utf-8") as f:
            content = f.read()

        # Detect PII
        registry = load_registry()
        engine = Engine(registry)
        result = engine.find(content)

        # Should find multiple PII instances
        assert result.has_matches
        assert len(result.matches) > 0

    def test_pattern_generation_validates(self, generator):
        """Test that generated patterns validate correctly."""
        from datadetector import Engine

        registry = load_registry()
        engine = Engine(registry)

        # Test multiple patterns
        test_cases = [
            ("comm/email_01", generator.from_pattern("comm/email_01")),
            ("us/ssn_01", generator.from_pattern("us/ssn_01")),
            ("kr/mobile_01", generator.from_pattern("kr/mobile_01")),
        ]

        for pattern_id, value in test_cases:
            result = engine.validate(value, pattern_id)
            assert result.is_valid, f"Generated {pattern_id} value '{value}' should validate"
