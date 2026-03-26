"""Property-based tests for AST Chunker.

These tests validate universal properties that should hold for all inputs.
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from ws_ctx_engine.chunker import RegexChunker, TreeSitterChunker, parse_with_fallback
from ws_ctx_engine.models import CodeChunk


# Strategy for generating valid Python code
@st.composite
def python_code(draw):
    """Generate valid Python code with functions and classes."""
    func_name = draw(
        st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=1, max_size=10)
    )
    class_name = draw(
        st.text(alphabet=st.characters(whitelist_categories=("Lu",)), min_size=1, max_size=10)
    )

    # Ensure valid identifiers
    assume(func_name.isidentifier())
    assume(class_name.isidentifier())

    code = f'''def {func_name}():
    """A test function."""
    pass

class {class_name}:
    """A test class."""
    
    def method(self):
        """A test method."""
        pass
'''
    return code, func_name, class_name


# Strategy for generating valid JavaScript code
@st.composite
def javascript_code(draw):
    """Generate valid JavaScript code with functions and classes."""
    func_name = draw(
        st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=1, max_size=10)
    )
    class_name = draw(
        st.text(alphabet=st.characters(whitelist_categories=("Lu",)), min_size=1, max_size=10)
    )

    # Ensure valid identifiers
    assume(func_name.isidentifier())
    assume(class_name.isidentifier())

    code = f"""function {func_name}() {{
    return 42;
}}

class {class_name} {{
    constructor() {{
        this.value = 0;
    }}
    
    method() {{
        return this.value;
    }}
}}

const arrow = () => {{
    return 100;
}};
"""
    return code, func_name, class_name


@pytest.mark.property
class TestASTParsingCompleteness:
    """Property 1: AST Parsing Completeness

    For any valid source file in a supported language (Python, JavaScript, TypeScript),
    parsing SHALL produce Code_Chunks with correct function and class boundaries,
    including all symbol definitions and references.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """

    @given(python_code())
    @settings(max_examples=20)  # Reduced for faster testing
    def test_python_parsing_produces_valid_chunks(self, code_data):
        """Test that valid Python code produces correct Code_Chunks."""
        code, func_name, class_name = code_data

        try:
            chunker = TreeSitterChunker()
        except ImportError:
            pytest.skip("TreeSitterChunker not available")

        # Create temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            # Parse
            chunks = chunker.parse(tmpdir)

            # Property: Should produce at least one chunk
            assert len(chunks) > 0, "Should produce at least one chunk"

            # Property: All chunks should have valid line numbers
            for chunk in chunks:
                assert chunk.start_line > 0, "Start line should be positive"
                assert chunk.end_line >= chunk.start_line, "End line should be >= start line"
                assert chunk.language == "python", "Language should be detected as python"
                assert len(chunk.content) > 0, "Content should not be empty"

            # Property: Should find the function and class we defined
            all_symbols = []
            for chunk in chunks:
                all_symbols.extend(chunk.symbols_defined)

            assert func_name in all_symbols, f"Should find function {func_name}"
            assert class_name in all_symbols, f"Should find class {class_name}"

    @given(javascript_code())
    @settings(max_examples=20)
    def test_javascript_parsing_produces_valid_chunks(self, code_data):
        """Test that valid JavaScript code produces correct Code_Chunks."""
        code, func_name, class_name = code_data

        try:
            chunker = TreeSitterChunker()
        except ImportError:
            pytest.skip("TreeSitterChunker not available")

        # Create temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.js"
            file_path.write_text(code)

            # Parse
            chunks = chunker.parse(tmpdir)

            # Property: Should produce at least one chunk
            assert len(chunks) > 0, "Should produce at least one chunk"

            # Property: All chunks should have valid line numbers
            for chunk in chunks:
                assert chunk.start_line > 0, "Start line should be positive"
                assert chunk.end_line >= chunk.start_line, "End line should be >= start line"
                assert chunk.language == "javascript", "Language should be detected as javascript"
                assert len(chunk.content) > 0, "Content should not be empty"

            # Property: Should find the function and class we defined
            all_symbols = []
            for chunk in chunks:
                all_symbols.extend(chunk.symbols_defined)

            assert func_name in all_symbols, f"Should find function {func_name}"
            assert class_name in all_symbols, f"Should find class {class_name}"

    @given(st.text(min_size=10, max_size=100))
    @settings(max_examples=20)
    def test_chunks_have_required_fields(self, content):
        """Test that all chunks have required fields regardless of input."""
        try:
            chunker = TreeSitterChunker()
        except ImportError:
            pytest.skip("TreeSitterChunker not available")

        # Create temporary Python file with arbitrary content
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(content)

            # Parse (may produce empty list for invalid code)
            chunks = chunker.parse(tmpdir)

            # Property: All chunks must have required fields
            for chunk in chunks:
                assert isinstance(chunk, CodeChunk), "Should be CodeChunk instance"
                assert isinstance(chunk.path, str), "path should be string"
                assert isinstance(chunk.start_line, int), "start_line should be int"
                assert isinstance(chunk.end_line, int), "end_line should be int"
                assert isinstance(chunk.content, str), "content should be string"
                assert isinstance(chunk.symbols_defined, list), "symbols_defined should be list"
                assert isinstance(
                    chunk.symbols_referenced, list
                ), "symbols_referenced should be list"
                assert isinstance(chunk.language, str), "language should be string"


@pytest.mark.property
class TestParserFallbackResilience:
    """Property 2: Parser Fallback Resilience

    For any file that causes Tree_Sitter to fail, the system SHALL fall back
    to regex-based parsing and log a warning, rather than crashing.

    **Validates: Requirements 1.5, 1.6**
    """

    @given(st.text(min_size=10, max_size=200))
    @settings(max_examples=20)
    def test_fallback_never_crashes(self, content):
        """Test that parse_with_fallback never crashes regardless of input."""
        # Create temporary file with arbitrary content
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(content)

            # Property: Should never crash, even with invalid code
            try:
                chunks = parse_with_fallback(tmpdir)
                # Should return a list (possibly empty)
                assert isinstance(chunks, list), "Should return a list"
            except Exception as e:
                pytest.fail(f"parse_with_fallback crashed with: {e}")

    @given(python_code())
    @settings(max_examples=20)
    def test_fallback_produces_valid_chunks(self, code_data):
        """Test that fallback produces valid chunks for valid code."""
        code, func_name, class_name = code_data

        # Create temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            # Parse with fallback
            chunks = parse_with_fallback(tmpdir)

            # Property: Should produce at least one chunk
            assert len(chunks) > 0, "Should produce at least one chunk"

            # Property: All chunks should be valid
            for chunk in chunks:
                assert isinstance(chunk, CodeChunk), "Should be CodeChunk instance"
                assert chunk.start_line > 0, "Start line should be positive"
                assert chunk.end_line >= chunk.start_line, "End line should be >= start line"

    def test_regex_chunker_never_crashes_on_invalid_code(self):
        """Test that RegexChunker handles invalid code gracefully."""
        invalid_codes = [
            "def broken(",  # Incomplete function
            "class Broken",  # Incomplete class
            "function broken(",  # Incomplete JS function
            "const x = (",  # Incomplete expression
            "",  # Empty file
            "   ",  # Whitespace only
        ]

        chunker = RegexChunker()

        for invalid_code in invalid_codes:
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = Path(tmpdir) / "test.py"
                file_path.write_text(invalid_code)

                # Property: Should not crash
                try:
                    chunks = chunker.parse(tmpdir)
                    assert isinstance(chunks, list), "Should return a list"
                except Exception as e:
                    pytest.fail(f"RegexChunker crashed on '{invalid_code}': {e}")
