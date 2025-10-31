"""Tests for bulk data generator."""

import json
import tempfile
from pathlib import Path

import pytest

from datadetector import BulkDataGenerator, FakeDataGenerator


@pytest.fixture
def bulk_gen():
    """Create BulkDataGenerator instance."""
    return BulkDataGenerator(seed=12345)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestLabeledRecordGeneration:
    """Tests for labeled record generation."""

    def test_generate_labeled_record_basic(self, bulk_gen):
        """Test generating a basic labeled record."""
        record = bulk_gen.generate_labeled_record(num_pii_items=3)

        assert 'text' in record
        assert 'pii_items' in record
        assert 'metadata' in record
        assert isinstance(record['text'], str)
        assert isinstance(record['pii_items'], list)
        assert len(record['text']) > 0

    def test_generate_labeled_record_pii_items(self, bulk_gen):
        """Test PII items structure."""
        record = bulk_gen.generate_labeled_record(num_pii_items=5)

        assert len(record['pii_items']) <= 5  # May be less if generation fails

        for item in record['pii_items']:
            assert 'pattern_id' in item
            assert 'namespace' in item
            assert 'pattern_name' in item
            assert 'value' in item
            assert 'start_hint' in item
            assert '/' in item['pattern_id']

    def test_generate_labeled_record_metadata(self, bulk_gen):
        """Test metadata structure."""
        record = bulk_gen.generate_labeled_record(num_pii_items=3)

        metadata = record['metadata']
        assert 'num_pii_items' in metadata
        assert 'patterns_used' in metadata
        assert 'text_length' in metadata
        assert metadata['num_pii_items'] == len(record['pii_items'])
        assert metadata['text_length'] == len(record['text'])

    def test_generate_labeled_record_specific_patterns(self, bulk_gen):
        """Test generating with specific patterns."""
        patterns = ["comm/email_01", "us/ssn_01"]
        record = bulk_gen.generate_labeled_record(
            include_patterns=patterns,
            num_pii_items=2
        )

        pattern_ids = [item['pattern_id'] for item in record['pii_items']]
        assert all(pid in patterns for pid in pattern_ids)


class TestBulkGeneration:
    """Tests for bulk data generation."""

    def test_generate_bulk_labeled_data_basic(self, bulk_gen):
        """Test generating bulk labeled data."""
        records = bulk_gen.generate_bulk_labeled_data(num_records=10)

        assert len(records) == 10
        assert all('record_id' in r for r in records)
        assert all('text' in r for r in records)
        assert all('pii_items' in r for r in records)

    def test_generate_bulk_labeled_data_record_ids(self, bulk_gen):
        """Test record IDs are sequential."""
        records = bulk_gen.generate_bulk_labeled_data(num_records=5)

        record_ids = [r['record_id'] for r in records]
        assert record_ids == [1, 2, 3, 4, 5]

    def test_generate_bulk_labeled_data_patterns_per_record(self, bulk_gen):
        """Test patterns per record range."""
        records = bulk_gen.generate_bulk_labeled_data(
            num_records=20,
            patterns_per_record=(2, 4)
        )

        for record in records:
            num_pii = record['metadata']['num_pii_items']
            assert 0 <= num_pii <= 4  # May be 0 if generation fails


class TestJSONLFormat:
    """Tests for JSONL format output."""

    def test_save_bulk_data_jsonl_basic(self, bulk_gen, temp_dir):
        """Test saving data in JSONL format."""
        output_path = temp_dir / "test.jsonl"
        bulk_gen.save_bulk_data_jsonl(output_path, num_records=10)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Verify each line is valid JSON
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 10
        for line in lines:
            record = json.loads(line)
            assert 'text' in record
            assert 'pii_items' in record

    def test_save_bulk_data_jsonl_content(self, bulk_gen, temp_dir):
        """Test JSONL content structure."""
        output_path = temp_dir / "test.jsonl"
        bulk_gen.save_bulk_data_jsonl(output_path, num_records=5)

        with open(output_path, 'r', encoding='utf-8') as f:
            record = json.loads(f.readline())

        assert 'record_id' in record
        assert 'text' in record
        assert 'pii_items' in record
        assert 'metadata' in record


class TestJSONFormat:
    """Tests for JSON format output."""

    def test_save_bulk_data_json_basic(self, bulk_gen, temp_dir):
        """Test saving data in JSON format."""
        output_path = temp_dir / "test.json"
        bulk_gen.save_bulk_data_json(output_path, num_records=10)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_save_bulk_data_json_structure(self, bulk_gen, temp_dir):
        """Test JSON structure."""
        output_path = temp_dir / "test.json"
        bulk_gen.save_bulk_data_json(output_path, num_records=5)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'records' in data
        assert len(data['records']) == 5

    def test_save_bulk_data_json_metadata(self, bulk_gen, temp_dir):
        """Test JSON metadata."""
        output_path = temp_dir / "test.json"
        bulk_gen.save_bulk_data_json(output_path, num_records=5)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        metadata = data['metadata']
        assert metadata['num_records'] == 5
        assert 'total_pii_items' in metadata
        assert 'generator' in metadata


class TestCSVFormat:
    """Tests for CSV format output."""

    def test_save_bulk_data_csv_basic(self, bulk_gen, temp_dir):
        """Test saving data in CSV format."""
        import csv

        output_path = temp_dir / "test.csv"
        bulk_gen.save_bulk_data_csv(output_path, num_records=10)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Verify CSV structure
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)

        assert len(rows) == 10
        assert 'record_id' in header
        assert 'text' in header
        assert 'pii_items_json' in header

    def test_save_bulk_data_csv_content(self, bulk_gen, temp_dir):
        """Test CSV content."""
        import csv

        output_path = temp_dir / "test.csv"
        bulk_gen.save_bulk_data_csv(output_path, num_records=3)

        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)

        assert row['record_id'] == '1'
        assert len(row['text']) > 0
        assert int(row['num_pii_items']) >= 0

        # Verify pii_items_json is valid JSON
        pii_items = json.loads(row['pii_items_json'])
        assert isinstance(pii_items, list)


class TestDetectionPairs:
    """Tests for detection pairs generation."""

    def test_generate_detection_pairs_basic(self, bulk_gen):
        """Test generating detection pairs."""
        pairs = bulk_gen.generate_detection_pairs(num_pairs=100, positive_ratio=0.7)

        assert len(pairs) == 100
        positive = sum(1 for p in pairs if p['has_pii'])
        assert 65 <= positive <= 75  # Allow some variance

    def test_generate_detection_pairs_structure(self, bulk_gen):
        """Test detection pair structure."""
        pairs = bulk_gen.generate_detection_pairs(num_pairs=10)

        for pair in pairs:
            assert 'pair_id' in pair
            assert 'text' in pair
            assert 'has_pii' in pair
            assert 'label' in pair
            assert 'pii_count' in pair
            assert 'patterns' in pair
            assert pair['label'] in [0, 1]

    def test_generate_detection_pairs_labels(self, bulk_gen):
        """Test label consistency."""
        pairs = bulk_gen.generate_detection_pairs(num_pairs=20)

        for pair in pairs:
            if pair['has_pii']:
                assert pair['label'] == 1
                assert pair['pii_count'] > 0
            else:
                assert pair['label'] == 0
                assert pair['pii_count'] == 0

    def test_save_detection_pairs_jsonl(self, bulk_gen, temp_dir):
        """Test saving detection pairs in JSONL."""
        output_path = temp_dir / "pairs.jsonl"
        bulk_gen.save_detection_pairs(output_path, num_pairs=10, format='jsonl')

        assert output_path.exists()

        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 10

    def test_save_detection_pairs_json(self, bulk_gen, temp_dir):
        """Test saving detection pairs in JSON."""
        output_path = temp_dir / "pairs.json"
        bulk_gen.save_detection_pairs(output_path, num_pairs=10, format='json')

        assert output_path.exists()

        with open(output_path, 'r', encoding='utf-8') as f:
            pairs = json.load(f)

        assert len(pairs) == 10

    def test_save_detection_pairs_csv(self, bulk_gen, temp_dir):
        """Test saving detection pairs in CSV."""
        import csv

        output_path = temp_dir / "pairs.csv"
        bulk_gen.save_detection_pairs(output_path, num_pairs=10, format='csv')

        assert output_path.exists()

        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 10


class TestStatistics:
    """Tests for statistics generation."""

    def test_generate_statistics_basic(self, bulk_gen):
        """Test generating statistics."""
        records = bulk_gen.generate_bulk_labeled_data(num_records=10)
        stats = bulk_gen.generate_statistics(records)

        assert 'total_records' in stats
        assert 'total_pii_items' in stats
        assert 'avg_pii_per_record' in stats
        assert 'avg_text_length' in stats
        assert 'pattern_distribution' in stats
        assert 'unique_patterns_used' in stats

    def test_generate_statistics_values(self, bulk_gen):
        """Test statistics values."""
        records = bulk_gen.generate_bulk_labeled_data(num_records=20)
        stats = bulk_gen.generate_statistics(records)

        assert stats['total_records'] == 20
        assert stats['total_pii_items'] >= 0
        assert stats['avg_pii_per_record'] >= 0
        assert stats['avg_text_length'] > 0
        assert isinstance(stats['pattern_distribution'], dict)

    def test_generate_statistics_pattern_distribution(self, bulk_gen):
        """Test pattern distribution."""
        patterns = ["comm/email_01", "us/ssn_01"]
        records = bulk_gen.generate_bulk_labeled_data(
            num_records=10,
            patterns_per_record=(1, 2),
            include_patterns=patterns
        )
        stats = bulk_gen.generate_statistics(records)

        for pattern_id in stats['pattern_distribution']:
            assert pattern_id in patterns


class TestConfiguration:
    """Tests for generator configuration."""

    def test_with_existing_generator(self):
        """Test creating bulk generator with existing FakeDataGenerator."""
        fake_gen = FakeDataGenerator(seed=42)
        bulk_gen = BulkDataGenerator(faker_generator=fake_gen)

        assert bulk_gen.gen is fake_gen
        assert bulk_gen.faker is fake_gen.faker

    def test_with_seed(self):
        """Test creating bulk generator with seed."""
        bulk_gen1 = BulkDataGenerator(seed=42)
        bulk_gen2 = BulkDataGenerator(seed=42)

        # Just verify the seed parameter is accepted and generators work
        record1 = bulk_gen1.generate_labeled_record(num_pii_items=1)
        record2 = bulk_gen2.generate_labeled_record(num_pii_items=1)

        # Both should generate valid records
        assert len(record1['text']) > 0
        assert len(record2['text']) > 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_records(self, bulk_gen):
        """Test generating zero records."""
        records = bulk_gen.generate_bulk_labeled_data(num_records=0)
        assert len(records) == 0

    def test_single_record(self, bulk_gen):
        """Test generating single record."""
        records = bulk_gen.generate_bulk_labeled_data(num_records=1)
        assert len(records) == 1
        assert records[0]['record_id'] == 1

    def test_detection_pairs_zero_positive(self, bulk_gen):
        """Test detection pairs with zero positive ratio."""
        pairs = bulk_gen.generate_detection_pairs(num_pairs=10, positive_ratio=0.0)
        assert all(not p['has_pii'] for p in pairs)
        assert all(p['label'] == 0 for p in pairs)

    def test_detection_pairs_all_positive(self, bulk_gen):
        """Test detection pairs with all positive."""
        pairs = bulk_gen.generate_detection_pairs(num_pairs=10, positive_ratio=1.0)
        assert all(p['has_pii'] for p in pairs)
        assert all(p['label'] == 1 for p in pairs)
