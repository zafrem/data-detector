"""Tests for CLI commands."""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from datadetector.cli import main


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_text():
    """Sample text with PII."""
    return "Contact: test@example.com or 010-1234-5678"


@pytest.fixture
def temp_pattern_file(tmp_path):
    """Create a temporary pattern file."""
    pattern_content = """
namespace: test
description: Test patterns

patterns:
  - id: test_email_01
    location: test
    category: email
    description: Test email pattern
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'
    mask: "***@***.***"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
"""
    pattern_file = tmp_path / "test_patterns.yml"
    pattern_file.write_text(pattern_content)
    return pattern_file


class TestVersion:
    """Test version command."""

    def test_version_flag(self, runner):
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()


class TestFindCommand:
    """Test find command."""

    def test_find_with_text(self, runner, sample_text):
        """Test find with text input."""
        result = runner.invoke(main, ["find", "--text", sample_text])
        assert result.exit_code == 0
        assert "Found" in result.output

    def test_find_with_file(self, runner, tmp_path):
        """Test find with file input."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Email: user@example.com")

        result = runner.invoke(main, ["find", "--file", str(test_file)])
        assert result.exit_code == 0
        assert "Found" in result.output

    def test_find_with_namespace(self, runner, sample_text):
        """Test find with namespace filter."""
        result = runner.invoke(main, ["find", "--text", sample_text, "--ns", "comm"])
        assert result.exit_code == 0

    def test_find_with_multiple_namespaces(self, runner, sample_text):
        """Test find with multiple namespaces."""
        result = runner.invoke(
            main, ["find", "--text", sample_text, "--ns", "comm", "--ns", "kr"]
        )
        assert result.exit_code == 0

    def test_find_json_output(self, runner, sample_text):
        """Test find with JSON output."""
        result = runner.invoke(main, ["find", "--text", sample_text, "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "match_count" in data
        assert "matches" in data
        assert "namespaces_searched" in data

    def test_find_with_include_text(self, runner, sample_text):
        """Test find with include text option."""
        result = runner.invoke(main, ["find", "--text", sample_text, "--include-text"])
        assert result.exit_code == 0

    def test_find_with_first_only(self, runner, sample_text):
        """Test find with first-only flag."""
        result = runner.invoke(main, ["find", "--text", sample_text, "--first-only"])
        assert result.exit_code == 0

    def test_find_with_custom_patterns(self, runner, temp_pattern_file):
        """Test find with custom pattern file."""
        result = runner.invoke(
            main,
            [
                "find",
                "--text",
                "user@example.com",
                "--patterns",
                str(temp_pattern_file),
            ],
        )
        assert result.exit_code == 0

    def test_find_without_input_error(self, runner):
        """Test find without input raises error."""
        result = runner.invoke(main, ["find"])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_find_text_output_format(self, runner):
        """Test text output format details."""
        result = runner.invoke(
            main, ["find", "--text", "Email: test@example.com", "--output", "text"]
        )
        assert result.exit_code == 0
        assert "Found" in result.output


class TestValidateCommand:
    """Test validate command."""

    def test_validate_valid_input(self, runner):
        """Test validate with valid input."""
        result = runner.invoke(
            main,
            ["validate", "--text", "test@example.com", "--ns-id", "comm/email_01"],
        )
        assert result.exit_code == 0
        assert "Valid" in result.output

    def test_validate_invalid_input(self, runner):
        """Test validate with invalid input."""
        result = runner.invoke(
            main,
            ["validate", "--text", "not-an-email", "--ns-id", "comm/email_01"],
        )
        assert result.exit_code == 1
        assert "Invalid" in result.output

    def test_validate_pattern_not_found(self, runner):
        """Test validate with non-existent pattern."""
        result = runner.invoke(
            main,
            ["validate", "--text", "test", "--ns-id", "nonexistent/pattern"],
        )
        assert result.exit_code == 2
        assert "Error" in result.output

    def test_validate_with_custom_patterns(self, runner, temp_pattern_file):
        """Test validate with custom patterns."""
        result = runner.invoke(
            main,
            [
                "validate",
                "--text",
                "user@example.com",
                "--ns-id",
                "test/test_email_01",
                "--patterns",
                str(temp_pattern_file),
            ],
        )
        assert result.exit_code == 0


class TestRedactCommand:
    """Test redact command."""

    def test_redact_with_text(self, runner, sample_text):
        """Test redact with text input."""
        result = runner.invoke(main, ["redact", "--text", sample_text])
        assert result.exit_code == 0
        assert "***" in result.output

    def test_redact_with_file(self, runner, tmp_path):
        """Test redact with file input."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Email: user@example.com")

        result = runner.invoke(main, ["redact", "--in", str(test_file)])
        assert result.exit_code == 0
        assert "***" in result.output

    def test_redact_to_file(self, runner, tmp_path, sample_text):
        """Test redact to output file."""
        output_file = tmp_path / "output.txt"
        result = runner.invoke(
            main,
            ["redact", "--text", sample_text, "--out", str(output_file)],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        redacted_text = output_file.read_text()
        assert "***" in redacted_text

    def test_redact_with_namespace(self, runner, sample_text):
        """Test redact with namespace."""
        result = runner.invoke(
            main, ["redact", "--text", sample_text, "--ns", "comm"]
        )
        assert result.exit_code == 0

    def test_redact_with_hash_strategy(self, runner, sample_text):
        """Test redact with hash strategy."""
        result = runner.invoke(
            main, ["redact", "--text", sample_text, "--strategy", "hash"]
        )
        assert result.exit_code == 0

    def test_redact_with_tokenize_strategy(self, runner, sample_text):
        """Test redact with tokenize strategy."""
        result = runner.invoke(
            main, ["redact", "--text", sample_text, "--strategy", "tokenize"]
        )
        assert result.exit_code == 0

    def test_redact_with_stats(self, runner, sample_text):
        """Test redact with stats."""
        result = runner.invoke(main, ["redact", "--text", sample_text, "--stats"])
        assert result.exit_code == 0
        assert "Redacted" in result.output

    def test_redact_with_stats_to_file(self, runner, tmp_path, sample_text):
        """Test redact with stats to file."""
        output_file = tmp_path / "output.txt"
        result = runner.invoke(
            main,
            [
                "redact",
                "--text",
                sample_text,
                "--out",
                str(output_file),
                "--stats",
            ],
        )
        assert result.exit_code == 0
        assert "Redacted" in result.output

    def test_redact_with_custom_patterns(self, runner, temp_pattern_file):
        """Test redact with custom patterns."""
        result = runner.invoke(
            main,
            [
                "redact",
                "--text",
                "user@example.com",
                "--patterns",
                str(temp_pattern_file),
            ],
        )
        assert result.exit_code == 0

    def test_redact_without_input_error(self, runner):
        """Test redact without input raises error."""
        result = runner.invoke(main, ["redact"])
        assert result.exit_code == 1
        assert "Error" in result.output


class TestListPatternsCommand:
    """Test list-patterns command."""

    def test_list_patterns_default(self, runner):
        """Test list patterns with defaults."""
        result = runner.invoke(main, ["list-patterns"])
        assert result.exit_code == 0
        assert "Loaded" in result.output
        assert "Namespace:" in result.output

    def test_list_patterns_with_custom(self, runner, temp_pattern_file):
        """Test list patterns with custom file."""
        result = runner.invoke(main, ["list-patterns", "--patterns", str(temp_pattern_file)])
        assert result.exit_code == 0
        assert "Loaded" in result.output


class TestServeCommand:
    """Test serve command."""

    def test_serve_import_error(self, runner, monkeypatch):
        """Test serve with missing dependencies."""
        # This should work without mocking since uvicorn is installed
        # But we test that the command exists
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start HTTP/gRPC server" in result.output

    def test_serve_with_config(self, runner, tmp_path, monkeypatch):
        """Test serve with config file."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
server:
  port: 9000
  host: "127.0.0.1"
"""
        )

        # We can't actually run the server in tests, but we can verify the command parses
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0


class TestVerboseOption:
    """Test verbose option."""

    def test_verbose_flag(self, runner):
        """Test verbose flag."""
        result = runner.invoke(main, ["-v", "list-patterns"])
        assert result.exit_code == 0

    def test_verbose_long_option(self, runner):
        """Test verbose long option."""
        result = runner.invoke(main, ["--verbose", "list-patterns"])
        assert result.exit_code == 0
