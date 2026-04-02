"""Tests for TrainingDataAdapter using JSONL fixtures."""

import json

import pytest

from datadetector.adapters.training_data import TrainingDataAdapter
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerType,
    DataResource,
    ResourceType,
)


@pytest.fixture
def instruction_dir(tmp_path):
    """Create JSONL files in instruction-tuning format."""
    data = [
        {
            "instruction": "Summarize the customer complaint",
            "input": "My name is John Doe, SSN 123-45-6789. I was charged twice.",
            "output": "Customer John Doe reports a double charge on their account.",
        },
        {
            "instruction": "Extract contact info",
            "input": "Call me at 010-1234-5678 or email jane@example.com",
            "output": "Phone: 010-1234-5678, Email: jane@example.com",
        },
        {
            "instruction": "Translate to Korean",
            "input": "Hello, my address is 123 Main Street",
            "output": "안녕하세요, 제 주소는 123 Main Street입니다",
        },
    ]
    f = tmp_path / "finetune.jsonl"
    f.write_text("\n".join(json.dumps(row) for row in data) + "\n")
    return tmp_path


@pytest.fixture
def chat_dir(tmp_path):
    """Create JSONL files in chat/conversation format."""
    data = [
        {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "My credit card 4111-1111-1111-1111 was stolen",
                },
                {
                    "role": "assistant",
                    "content": "I'll help you report the stolen card ending in 1111.",
                },
            ]
        },
        {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "My email is bob@company.org and SSN is 987-65-4321",
                },
                {
                    "role": "assistant",
                    "content": "I see your contact information. How can I help?",
                },
            ]
        },
    ]
    f = tmp_path / "chat_data.jsonl"
    f.write_text("\n".join(json.dumps(row) for row in data) + "\n")
    return tmp_path


@pytest.fixture
def completion_dir(tmp_path):
    """Create JSONL files in prompt/completion format."""
    data = [
        {
            "prompt": "Customer: My passport number is M12345678\nAgent:",
            "completion": "I've noted your passport number. How can I assist you?",
        },
        {
            "prompt": "Customer: Please update my phone to 010-9876-5432\nAgent:",
            "completion": "Your phone number has been updated to the new number.",
        },
    ]
    f = tmp_path / "completions.jsonl"
    f.write_text("\n".join(json.dumps(row) for row in data) + "\n")
    return tmp_path


@pytest.fixture
def mixed_dir(tmp_path):
    """Create directory with multiple JSONL files of different formats."""
    # instruction format
    inst_data = [
        {"instruction": "Mask PII", "input": "Email: test@test.com", "output": "Email: [MASKED]"},
    ]
    (tmp_path / "instruct.jsonl").write_text("\n".join(json.dumps(r) for r in inst_data) + "\n")

    # completion format
    comp_data = [
        {"prompt": "Hello John", "completion": "Hi there!"},
    ]
    (tmp_path / "completions.jsonl").write_text("\n".join(json.dumps(r) for r in comp_data) + "\n")

    return tmp_path


def _make_adapter(path, **params):
    """Create a TrainingDataAdapter for a path."""
    resource = DataResource(
        name="test-training",
        resource_type=ResourceType.TRAINING_DATA,
        connection=ConnectionConfig(uri=str(path), params={"backend": "jsonl", **params}),
    )
    adapter = TrainingDataAdapter(resource)
    adapter.connect()
    return adapter


class TestTrainingDataAdapterConnect:
    """Test connection behavior."""

    def test_connect_jsonl(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        assert adapter._connected is True
        assert len(adapter._files) == 1
        adapter.close()
        assert adapter._connected is False

    def test_connect_idempotent(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        adapter.connect()
        assert adapter._connected is True
        adapter.close()

    def test_connect_nonexistent_path(self, tmp_path):
        resource = DataResource(
            name="bad",
            resource_type=ResourceType.TRAINING_DATA,
            connection=ConnectionConfig(
                uri=str(tmp_path / "nonexistent"),
                params={"backend": "jsonl"},
            ),
        )
        adapter = TrainingDataAdapter(resource)
        with pytest.raises(ConnectionError, match="does not exist"):
            adapter.connect()

    def test_connect_single_file(self, instruction_dir):
        file_path = instruction_dir / "finetune.jsonl"
        adapter = _make_adapter(file_path)
        assert len(adapter._files) == 1
        adapter.close()

    def test_connect_unsupported_backend(self):
        resource = DataResource(
            name="bad",
            resource_type=ResourceType.TRAINING_DATA,
            connection=ConnectionConfig(
                uri="/tmp",
                params={"backend": "parquet_dataset"},
            ),
        )
        adapter = TrainingDataAdapter(resource)
        with pytest.raises(ValueError, match="Unsupported training data backend"):
            adapter.connect()

    def test_context_manager(self, instruction_dir):
        resource = DataResource(
            name="test-ctx",
            resource_type=ResourceType.TRAINING_DATA,
            connection=ConnectionConfig(
                uri=str(instruction_dir),
                params={"backend": "jsonl"},
            ),
        )
        with TrainingDataAdapter(resource) as adapter:
            assert adapter._connected is True
            containers = adapter.list_containers()
            assert len(containers) > 0
        assert adapter._connected is False


class TestTrainingDataAdapterListContainers:
    """Test container listing."""

    def test_list_jsonl_containers(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        containers = adapter.list_containers()
        assert len(containers) == 1
        assert containers[0].name == "finetune.jsonl"
        assert containers[0].container_type == ContainerType.DATASET
        adapter.close()

    def test_container_metadata(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        containers = adapter.list_containers()
        meta = containers[0].metadata
        assert meta["backend"] == "jsonl"
        assert meta["row_count"] == 3
        assert meta["format"] == "instruction"
        assert "file_path" in meta
        adapter.close()

    def test_detect_chat_format(self, chat_dir):
        adapter = _make_adapter(chat_dir)
        containers = adapter.list_containers()
        assert containers[0].metadata["format"] == "chat"
        adapter.close()

    def test_detect_completion_format(self, completion_dir):
        adapter = _make_adapter(completion_dir)
        containers = adapter.list_containers()
        assert containers[0].metadata["format"] == "completion"
        adapter.close()

    def test_multiple_files(self, mixed_dir):
        adapter = _make_adapter(mixed_dir)
        containers = adapter.list_containers()
        assert len(containers) == 2
        names = {c.name for c in containers}
        assert names == {"instruct.jsonl", "completions.jsonl"}
        adapter.close()

    def test_filter_by_pattern(self, mixed_dir):
        adapter = _make_adapter(mixed_dir)
        containers = adapter.list_containers(pattern="instruct*")
        assert len(containers) == 1
        assert containers[0].name == "instruct.jsonl"
        adapter.close()

    def test_not_connected_raises(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.TRAINING_DATA,
            connection=ConnectionConfig(uri="/tmp", params={"backend": "jsonl"}),
        )
        adapter = TrainingDataAdapter(resource)
        with pytest.raises(RuntimeError, match="not connected"):
            adapter.list_containers()


class TestTrainingDataAdapterListFields:
    """Test field listing."""

    def test_instruction_format_fields(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        fields = adapter.list_fields("finetune.jsonl")
        field_names = [f.name for f in fields]
        assert "instruction" in field_names
        assert "input" in field_names
        assert "output" in field_names
        adapter.close()

    def test_chat_format_expands_roles(self, chat_dir):
        adapter = _make_adapter(chat_dir)
        fields = adapter.list_fields("chat_data.jsonl")
        field_names = [f.name for f in fields]
        assert "messages.system.content" in field_names
        assert "messages.user.content" in field_names
        assert "messages.assistant.content" in field_names
        # Raw "messages" should not be listed as a field
        assert "messages" not in field_names
        adapter.close()

    def test_completion_format_fields(self, completion_dir):
        adapter = _make_adapter(completion_dir)
        fields = adapter.list_fields("completions.jsonl")
        field_names = [f.name for f in fields]
        assert "prompt" in field_names
        assert "completion" in field_names
        adapter.close()

    def test_text_fields_have_text_type(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        fields = adapter.list_fields("finetune.jsonl")
        by_name = {f.name: f for f in fields}
        assert by_name["instruction"].data_type == "text"
        assert by_name["input"].data_type == "text"
        assert by_name["output"].data_type == "text"
        adapter.close()


class TestTrainingDataAdapterSampleValues:
    """Test value sampling."""

    def test_sample_instruction_field(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        values = adapter.sample_values("finetune.jsonl", "input")
        assert len(values) == 3
        assert any("John Doe" in v for v in values)
        assert any("010-1234-5678" in v for v in values)
        adapter.close()

    def test_sample_output_field(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        values = adapter.sample_values("finetune.jsonl", "output")
        assert len(values) == 3
        adapter.close()

    def test_sample_chat_user_content(self, chat_dir):
        adapter = _make_adapter(chat_dir)
        values = adapter.sample_values("chat_data.jsonl", "messages.user.content")
        assert len(values) == 2
        assert any("4111-1111-1111-1111" in v for v in values)
        assert any("987-65-4321" in v for v in values)
        adapter.close()

    def test_sample_chat_assistant_content(self, chat_dir):
        adapter = _make_adapter(chat_dir)
        values = adapter.sample_values("chat_data.jsonl", "messages.assistant.content")
        assert len(values) == 2
        adapter.close()

    def test_sample_with_limit(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        values = adapter.sample_values("finetune.jsonl", "input", limit=1)
        assert len(values) == 1
        adapter.close()

    def test_sample_nonexistent_field(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        values = adapter.sample_values("finetune.jsonl", "nonexistent")
        assert values == []
        adapter.close()

    def test_sample_nonexistent_container(self, instruction_dir):
        adapter = _make_adapter(instruction_dir)
        values = adapter.sample_values("missing.jsonl", "input")
        assert values == []
        adapter.close()


class TestTrainingDataAdapterRelationships:
    """Test relationship detection."""

    def test_shared_schema_relationships(self, mixed_dir):
        adapter = _make_adapter(mixed_dir)
        containers = adapter.list_containers()
        for c in containers:
            adapter.list_fields(c.name)

        relationships = adapter.get_relationships()
        # Both files don't share enough fields (instruction vs completion format)
        # instruct has: instruction, input, output
        # completions has: prompt, completion
        # No overlap >= 2, so no relationships
        assert len(relationships) == 0
        adapter.close()

    def test_shared_schema_with_matching_fields(self, tmp_path):
        """Two files with the same schema should produce relationships."""
        for name in ["train.jsonl", "eval.jsonl"]:
            data = [
                {"instruction": "do something", "input": "text", "output": "result"},
            ]
            (tmp_path / name).write_text("\n".join(json.dumps(r) for r in data) + "\n")

        adapter = _make_adapter(tmp_path)
        containers = adapter.list_containers()
        for c in containers:
            adapter.list_fields(c.name)

        relationships = adapter.get_relationships()
        assert len(relationships) > 0
        # Should detect shared instruction/input/output fields
        shared_fields = {r.source_field.split(".")[-1] for r in relationships}
        assert "instruction" in shared_fields
        adapter.close()


class TestTrainingDataAdapterEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_jsonl_file(self, tmp_path):
        (tmp_path / "empty.jsonl").write_text("")
        adapter = _make_adapter(tmp_path)
        containers = adapter.list_containers()
        assert len(containers) == 1
        assert containers[0].metadata["row_count"] == 0
        adapter.close()

    def test_malformed_jsonl_lines(self, tmp_path):
        content = '{"instruction": "valid"}\nnot json\n{"input": "also valid"}\n'
        (tmp_path / "messy.jsonl").write_text(content)
        adapter = _make_adapter(tmp_path)
        fields = adapter.list_fields("messy.jsonl")
        field_names = [f.name for f in fields]
        assert "instruction" in field_names
        assert "input" in field_names
        adapter.close()

    def test_empty_directory(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        containers = adapter.list_containers()
        assert containers == []
        adapter.close()

    def test_glob_filter(self, tmp_path):
        (tmp_path / "train.jsonl").write_text('{"text": "hello"}\n')
        (tmp_path / "readme.txt").write_text("not a jsonl file")
        adapter = _make_adapter(tmp_path)
        containers = adapter.list_containers()
        # Only .jsonl files should be found
        assert len(containers) == 1
        assert containers[0].name == "train.jsonl"
        adapter.close()
