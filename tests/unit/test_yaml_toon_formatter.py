"""Unit tests for YAML and TOON output formatters."""

import yaml

from ws_ctx_engine.output.toon_formatter import TOONFormatter
from ws_ctx_engine.output.yaml_formatter import YAMLFormatter

SAMPLE_METADATA = {
    "repo_name": "my-repo",
    "file_count": 2,
    "total_tokens": 300,
    "query": "authentication logic",
    "generated_at": "2026-01-01T00:00:00Z",
}

SAMPLE_FILES = [
    {
        "path": "src/auth.py",
        "score": 0.95,
        "domain": "auth",
        "summary": "Authentication module",
        "content": "def authenticate(): pass",
        "dependencies": [],
        "dependents": [],
    },
    {
        "path": "src/utils.py",
        "score": 0.4,
        "domain": "general",
        "summary": "Utility functions",
        "content": "def helper(): pass",
        "dependencies": [],
        "dependents": [],
    },
]


class TestYAMLFormatter:
    def test_output_is_valid_yaml(self):
        formatter = YAMLFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        parsed = yaml.safe_load(output)
        assert isinstance(parsed, dict)

    def test_metadata_present(self):
        formatter = YAMLFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        parsed = yaml.safe_load(output)
        assert (
            parsed.get("repo_name") == "my-repo"
            or "metadata" in parsed
            or "repo_name" in str(output)
        )

    def test_files_present(self):
        formatter = YAMLFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert "src/auth.py" in output
        assert "src/utils.py" in output

    def test_empty_files_list(self):
        formatter = YAMLFormatter()
        output = formatter.render(SAMPLE_METADATA, [])
        parsed = yaml.safe_load(output)
        assert parsed is not None

    def test_output_is_string(self):
        formatter = YAMLFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert isinstance(output, str)
        assert len(output) > 0


class TestTOONFormatter:
    def test_output_contains_context_header(self):
        formatter = TOONFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert "--- context ---" in output

    def test_output_contains_end_marker(self):
        formatter = TOONFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert "--- end ---" in output

    def test_output_contains_file_separators(self):
        formatter = TOONFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert "src/auth.py" in output
        assert "src/utils.py" in output

    def test_output_contains_scores(self):
        formatter = TOONFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert "0.9500" in output
        assert "0.4000" in output

    def test_output_contains_file_content(self):
        formatter = TOONFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert "def authenticate(): pass" in output

    def test_metadata_fields_in_output(self):
        formatter = TOONFormatter()
        output = formatter.render(SAMPLE_METADATA, SAMPLE_FILES)
        assert "my-repo" in output
        assert "300" in output

    def test_empty_files_still_renders(self):
        formatter = TOONFormatter()
        output = formatter.render(SAMPLE_METADATA, [])
        assert "--- context ---" in output
        assert "--- end ---" in output

    def test_none_content_handled(self):
        """Files with None content (secrets redacted) should not raise."""
        formatter = TOONFormatter()
        files = [{"path": "secret.py", "score": 0.5, "content": None}]
        output = formatter.render(SAMPLE_METADATA, files)
        assert "secret.py" in output
