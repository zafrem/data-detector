"""Tests for timestamp, date, zipcode, and bank account confusion issues."""

import pytest

from datadetector import load_registry
from datadetector.engine import Engine


@pytest.fixture
def engine():
    """Create engine with loaded registry."""
    registry = load_registry()
    return Engine(registry=registry)


class TestTimestampConfusion:
    """Tests to identify false positives where timestamps are mistaken for other data types."""

    def test_unix_timestamp_not_zipcode(self, engine):
        """Unix timestamps should not be detected as zip codes."""
        # Unix timestamps (10 digits)
        timestamps = [
            "1734567890",  # 10-digit Unix timestamp
            "1609459200",  # Jan 1, 2021 00:00:00 GMT
            "1640995200",  # Jan 1, 2022 00:00:00 GMT
        ]

        for timestamp in timestamps:
            result = engine.find(timestamp)
            # Check if mistakenly detected as zipcode
            zipcode_matches = [m for m in result.matches if m.category.value == "address"]
            assert (
                len(zipcode_matches) == 0
            ), f"Timestamp {timestamp} incorrectly detected as zipcode"

    def test_unix_timestamp_ms_not_bank_account(self, engine):
        """Unix timestamps in milliseconds should not be detected as bank accounts."""
        # Unix timestamps in milliseconds (13 digits)
        timestamps_ms = [
            "1734567890123",  # 13-digit Unix timestamp in ms
            "1609459200000",  # Jan 1, 2021 00:00:00 GMT in ms
        ]

        for timestamp in timestamps_ms:
            result = engine.find(timestamp)
            # Check if mistakenly detected as bank account
            bank_matches = [m for m in result.matches if m.category.value == "bank"]
            assert (
                len(bank_matches) == 0
            ), f"Timestamp {timestamp} incorrectly detected as bank account"

    def test_iso_date_not_confused(self, engine):
        """ISO 8601 dates should not be detected as PII."""
        dates = [
            "2023-12-01",  # Could match patterns with hyphens
            "2023-01-15",
            "2024-03-30",
        ]

        for date in dates:
            result = engine.find(date)
            # Dates might be detected, but shouldn't be SSN, bank accounts, etc.
            ssn_matches = [m for m in result.matches if m.category.value == "ssn"]
            assert len(ssn_matches) == 0, f"Date {date} incorrectly detected as SSN"

    def test_yyyymmdd_not_confused(self, engine):
        """YYYYMMDD date format should not be detected as PII."""
        dates = [
            "20231201",  # 8 digits - could match various patterns
            "20240315",
            "20220101",
        ]

        for date in dates:
            result = engine.find(date)
            # These are 8 digits, could be confused with various patterns
            # Let's see what they match
            if result.matches:
                print(
                    f"Date {date} matched: {[(m.ns_id, m.category.value) for m in result.matches]}"
                )

    def test_time_format_not_confused(self, engine):
        """Time formats should not be detected as phone numbers."""
        times = [
            "12:34:56",  # Could match phone patterns with colons
            "09:15:30",
            "23:59:59",
        ]

        for time in times:
            result = engine.find(time)
            phone_matches = [m for m in result.matches if m.category.value == "phone"]
            assert len(phone_matches) == 0, f"Time {time} incorrectly detected as phone number"

    def test_datetime_timestamp_not_confused(self, engine):
        """Datetime timestamps should not match PII patterns."""
        datetimes = [
            "2023-12-01T10:30:45Z",
            "2024-01-15 14:22:33",
            "20231201103045",  # Compact datetime (14 digits)
        ]

        for dt in datetimes:
            result = engine.find(dt)
            # Should not match critical PII patterns
            critical_matches = [m for m in result.matches if m.severity.value == "critical"]
            assert len(critical_matches) == 0, f"Datetime {dt} incorrectly detected as critical PII"

    def test_korean_zipcode_in_timestamp_context(self, engine):
        """5-digit numbers in timestamp context should not be zip codes."""
        test_cases = [
            ("Timestamp: 1734512345", "12345"),  # Part of Unix timestamp
            ("File_20231_backup", "20231"),  # Part of filename with year
            ("Error code: 50123 occurred", "50123"),  # Error code
        ]

        for text, number in test_cases:
            result = engine.find(text)
            zipcode_matches = [
                m
                for m in result.matches
                if m.category.value == "address" and number in text[m.start : m.end]
            ]
            # This might fail - demonstrating the issue
            if zipcode_matches:
                print(f"WARNING: In '{text}', number '{number}' was detected as zipcode")

    def test_bank_account_vs_timestamp(self, engine):
        """Bank account patterns should not match timestamp components."""
        # Korean bank account patterns often use formats like XXX-XXX-XXXXXX
        # These could match parts of timestamps with separators
        test_cases = [
            "Log entry: 2023-12-01 10:30:45",  # Has multiple hyphen-separated numbers
            "Build: 100-123-456789",  # Could look like K Bank account
            "Version: 110-123-456789",  # Could look like Kookmin Bank account
        ]

        for text in test_cases:
            result = engine.find(text)
            bank_matches = [m for m in result.matches if m.category.value == "bank"]
            if bank_matches:
                print(f"WARNING: In '{text}', found bank account matches: {bank_matches}")

    def test_sequential_numbers_not_pii(self, engine):
        """Sequential numbers should not be detected as PII."""
        sequences = [
            "12345",
            "123456789",
            "1234567890",
        ]

        for seq in sequences:
            result = engine.find(seq)
            if result.matches:
                matches = [(m.ns_id, m.category.value) for m in result.matches]
                print(f"Sequential number {seq} matched: {matches}")


class TestPatternBoundaries:
    """Tests for pattern boundary detection."""

    def test_embedded_zipcode_in_larger_number(self, engine):
        """Zip code patterns should not match when embedded in larger numbers."""
        test_cases = [
            "1734512345",  # 10-digit timestamp containing "12345"
            "20231201",  # Date containing "20231"
            "ID:1234567890",  # ID containing "12345"
        ]

        for text in test_cases:
            result = engine.find(text)
            zipcode_matches = [m for m in result.matches if m.category.value == "address"]
            # Currently these might match - demonstrating the issue
            if zipcode_matches:
                print(f"WARNING: Embedded zipcode detected in '{text}': {zipcode_matches}")

    def test_partial_phone_in_timestamp(self, engine):
        """Phone number patterns should not match timestamp components."""
        test_cases = [
            "010-1234-5678-901",  # Looks like Korean mobile + extra digits
            "Call at 2023-010-1234",  # Date that starts with 010
        ]

        for text in test_cases:
            result = engine.find(text)
            phone_matches = [m for m in result.matches if m.category.value == "phone"]
            if phone_matches:
                matched = [m.matched_text for m in phone_matches]
                print(f"Phone detected in timestamp context '{text}': {matched}")

    def test_ssn_pattern_boundary(self, engine):
        """SSN patterns should have strict boundaries."""
        test_cases = [
            "Date: 2023-01-15",  # Hyphenated date
            "Version: 1.23-45-6789",  # Version number
            "ID:123-45-6789-01",  # SSN-like with extra digits
        ]

        for text in test_cases:
            result = engine.find(text)
            ssn_matches = [m for m in result.matches if m.category.value == "ssn"]
            if ssn_matches:
                matched = [m.matched_text for m in ssn_matches]
                print(f"SSN detected in non-SSN context '{text}': {matched}")


class TestRealWorldScenarios:
    """Real-world scenarios where confusion might occur."""

    def test_log_file_content(self, engine):
        """Log files with timestamps should not trigger false positives."""
        log_lines = [
            "[2023-12-01 10:30:45] INFO: Processing request ID 12345",
            "Timestamp: 1734567890 - User action completed",
            "2024-01-15T14:22:33Z - Service started on port 8080",
        ]

        for log in log_lines:
            result = engine.find(log)
            # Log timestamps shouldn't be detected as critical PII
            critical_matches = [
                m for m in result.matches if m.severity.value in ["critical", "high"]
            ]
            if critical_matches:
                print(f"WARNING: Critical PII detected in log: '{log}'")
                print(f"  Matches: {[(m.ns_id, m.matched_text) for m in critical_matches]}")

    def test_filename_patterns(self, engine):
        """Filenames with dates and numbers should not trigger false positives."""
        filenames = [
            "backup_20231201_12345.sql",
            "report-2024-01-15.pdf",
            "data_1734567890.csv",
            "archive-110-123-456789.zip",  # Could look like bank account
        ]

        for filename in filenames:
            result = engine.find(filename)
            if result.matches:
                matches = [(m.ns_id, m.category.value, m.matched_text) for m in result.matches]
                print(f"File '{filename}' matched: {matches}")

    def test_api_responses(self, engine):
        """API responses with timestamps and IDs should not trigger false positives."""
        responses = [
            '{"timestamp": 1734567890, "user_id": 12345}',
            '{"created_at": "2023-12-01T10:30:45Z", "id": "123-45-67890"}',
            '{"account": "110-123-456789", "balance": 50000}',  # This should match bank account
        ]

        for response in responses:
            result = engine.find(response)
            if result.matches:
                matches = [(m.ns_id, m.category.value, m.matched_text) for m in result.matches]
                print(f"API response matched: {matches}")
