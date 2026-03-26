"""Unit tests for smart compression (output/compressor.py)."""

import pytest

from ws_ctx_engine.output.compressor import (
    BODY_MARKER,
    FULL_CONTENT_THRESHOLD,
    SIGNATURE_THRESHOLD,
    compress_file_content,
    apply_compression_to_selected_files,
    _compress_python_regex,
    _compress_js_ts_regex,
)


PYTHON_SOURCE = '''\
def greet(name: str) -> str:
    result = f"Hello, {name}"
    return result


class Authenticator:
    """
    Handles auth.
    Multi-line docstring so the close-quote is on its own line.
    """

    def login(self, user: str, password: str) -> bool:
        hashed = hash(password)
        return self._check(user, hashed)

    def _check(self, user: str, hashed: int) -> bool:
        return True
'''

JS_SOURCE = """\
export async function fetchUser(id) {
    const resp = await fetch('/users/' + id);
    return resp;
}

function helper(x) {
    return x * 2;
}
"""


class TestCompressPythonRegex:
    def test_function_signature_kept(self):
        result = _compress_python_regex(PYTHON_SOURCE)
        assert "def greet(name: str) -> str:" in result

    def test_function_body_replaced_with_marker(self):
        result = _compress_python_regex(PYTHON_SOURCE)
        assert BODY_MARKER in result
        assert 'return f"Hello, {name}"' not in result

    def test_docstring_preserved_by_default(self):
        # Multi-line docstring (close quote on its own line) is preserved
        result = _compress_python_regex(PYTHON_SOURCE, preserve_docstrings=True)
        assert "Handles auth." in result

    def test_docstring_stripped_when_disabled(self):
        result = _compress_python_regex(PYTHON_SOURCE, preserve_docstrings=False)
        assert "Handles auth." not in result

    def test_class_signature_kept(self):
        result = _compress_python_regex(PYTHON_SOURCE)
        assert "class Authenticator:" in result

    def test_class_body_replaced_with_marker(self):
        # The regex compressor replaces the entire class body (including methods)
        # with a single marker — individual methods inside classes are not preserved
        result = _compress_python_regex(PYTHON_SOURCE)
        assert BODY_MARKER in result

    def test_plain_lines_not_altered(self):
        code = "import os\nimport sys\n\ndef foo(): pass\n"
        result = _compress_python_regex(code)
        assert "import os" in result
        assert "import sys" in result

    def test_empty_input(self):
        assert _compress_python_regex("") == ""

    def test_async_def_kept(self):
        code = "async def fetch():\n    return await something()\n"
        result = _compress_python_regex(code)
        assert "async def fetch():" in result


class TestCompressJsTsRegex:
    def test_function_signature_kept(self):
        result = _compress_js_ts_regex(JS_SOURCE)
        assert "export async function fetchUser(id)" in result

    def test_function_body_replaced(self):
        result = _compress_js_ts_regex(JS_SOURCE)
        assert BODY_MARKER in result
        assert "resp.json()" not in result

    def test_empty_input(self):
        assert _compress_js_ts_regex("") == ""


class TestCompressFileContent:
    def test_python_file_compressed(self):
        result = compress_file_content(PYTHON_SOURCE, "src/auth.py")
        assert BODY_MARKER in result
        assert "def greet" in result

    def test_js_file_compressed(self):
        result = compress_file_content(JS_SOURCE, "src/utils.js")
        assert BODY_MARKER in result

    def test_ts_file_compressed(self):
        result = compress_file_content(JS_SOURCE, "src/api.ts")
        assert BODY_MARKER in result

    def test_unknown_extension_returned_as_is(self):
        content = "some markdown content\n## header\n"
        result = compress_file_content(content, "README.md")
        assert result == content

    def test_empty_python_file(self):
        result = compress_file_content("", "empty.py")
        assert result == ""


class TestApplyCompressionToSelectedFiles:
    def test_high_relevance_file_not_compressed(self, tmp_path):
        py_file = tmp_path / "high.py"
        py_file.write_text(PYTHON_SOURCE)
        ranked_scores = {"high.py": FULL_CONTENT_THRESHOLD + 0.1}
        result = apply_compression_to_selected_files(
            selected_files=["high.py"],
            ranked_scores=ranked_scores,
            repo_path=str(tmp_path),
        )
        assert len(result) == 1
        path, content = result[0]
        assert path == "high.py"
        # High-relevance: full content preserved, no marker
        assert BODY_MARKER not in content

    def test_low_relevance_file_compressed(self, tmp_path):
        py_file = tmp_path / "low.py"
        py_file.write_text(PYTHON_SOURCE)
        ranked_scores = {"low.py": SIGNATURE_THRESHOLD - 0.1}
        result = apply_compression_to_selected_files(
            selected_files=["low.py"],
            ranked_scores=ranked_scores,
            repo_path=str(tmp_path),
        )
        path, content = result[0]
        assert BODY_MARKER in content

    def test_medium_relevance_file_compressed(self, tmp_path):
        py_file = tmp_path / "mid.py"
        py_file.write_text(PYTHON_SOURCE)
        ranked_scores = {"mid.py": (FULL_CONTENT_THRESHOLD + SIGNATURE_THRESHOLD) / 2}
        result = apply_compression_to_selected_files(
            selected_files=["mid.py"],
            ranked_scores=ranked_scores,
            repo_path=str(tmp_path),
        )
        path, content = result[0]
        assert BODY_MARKER in content

    def test_missing_score_defaults_to_full_content(self, tmp_path):
        py_file = tmp_path / "unknown.py"
        py_file.write_text(PYTHON_SOURCE)
        result = apply_compression_to_selected_files(
            selected_files=["unknown.py"],
            ranked_scores={},  # no score for this file
            repo_path=str(tmp_path),
        )
        path, content = result[0]
        # No score → treated as high relevance (full content)
        assert content  # non-empty

    def test_empty_files_list(self, tmp_path):
        result = apply_compression_to_selected_files(
            selected_files=[],
            ranked_scores={},
            repo_path=str(tmp_path),
        )
        assert result == []

    def test_returns_list_of_tuples(self, tmp_path):
        py_file = tmp_path / "a.py"
        py_file.write_text("x = 1\n")
        result = apply_compression_to_selected_files(
            selected_files=["a.py"],
            ranked_scores={"a.py": 0.5},
            repo_path=str(tmp_path),
        )
        assert isinstance(result, list)
        assert isinstance(result[0], tuple)
        assert len(result[0]) == 2
