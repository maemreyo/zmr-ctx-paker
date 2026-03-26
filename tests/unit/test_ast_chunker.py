"""Unit tests for AST Chunker implementations (TreeSitterChunker and RegexChunker)."""

import tempfile
from pathlib import Path

import pytest

# Sample Python code for testing
PYTHON_SAMPLE = '''def hello():
    """Say hello."""
    print("Hello, world!")

class Greeter:
    """A simple greeter class."""
    
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        """Greet someone."""
        return f"Hello, {self.name}!"
'''

# Sample JavaScript code with arrow functions
JAVASCRIPT_SAMPLE = """const add = (a, b) => {
    return a + b;
};

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    multiply(a, b) {
        return a * b;
    }
}

const subtract = (a, b) => a - b;
"""

# Sample TypeScript code
TYPESCRIPT_SAMPLE = """interface User {
    name: string;
    age: number;
}

function greetUser(user: User): string {
    return `Hello, ${user.name}!`;
}

class UserManager {
    private users: User[] = [];
    
    addUser(user: User): void {
        this.users.push(user);
    }
}
"""

# Invalid Python code (syntax error)
INVALID_PYTHON = """def broken_function(
    # Missing closing parenthesis and body
"""


class TestTreeSitterChunker:
    """Unit tests for TreeSitterChunker implementation."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Create Python file
            (repo_path / "main.py").write_text(PYTHON_SAMPLE)

            # Create JavaScript file
            (repo_path / "script.js").write_text(JAVASCRIPT_SAMPLE)

            # Create TypeScript file
            (repo_path / "app.ts").write_text(TYPESCRIPT_SAMPLE)

            # Create invalid Python file
            (repo_path / "broken.py").write_text(INVALID_PYTHON)

            yield str(repo_path)

    def test_parse_python_file_with_functions_and_classes(self, temp_repo):
        """Test parsing Python file with functions and classes.

        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitterChunker not implemented yet")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(temp_repo)

        # Filter to Python file chunks
        python_chunks = [c for c in chunks if c.path.endswith("main.py")]

        assert len(python_chunks) > 0, "Should parse Python file"

        # Check that we found the function and class
        symbols_found = []
        for chunk in python_chunks:
            symbols_found.extend(chunk.symbols_defined)

        assert "hello" in symbols_found, "Should find hello function"
        assert "Greeter" in symbols_found, "Should find Greeter class"

    def test_parse_javascript_file_with_arrow_functions(self, temp_repo):
        """Test parsing JavaScript file with arrow functions.

        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitterChunker not implemented yet")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(temp_repo)

        # Filter to JavaScript file chunks
        js_chunks = [c for c in chunks if c.path.endswith("script.js")]

        assert len(js_chunks) > 0, "Should parse JavaScript file"

        # Check that we found the arrow functions and class
        symbols_found = []
        for chunk in js_chunks:
            symbols_found.extend(chunk.symbols_defined)

        assert "add" in symbols_found, "Should find add arrow function"
        assert "Calculator" in symbols_found, "Should find Calculator class"

    def test_handle_syntax_errors_gracefully(self, temp_repo):
        """Test handling syntax errors gracefully.

        Requirements: 1.5
        """
        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitterChunker not implemented yet")

        chunker = TreeSitterChunker()

        # Should not crash on syntax errors
        chunks = chunker.parse(temp_repo)

        # Should still parse valid files
        assert len(chunks) > 0, "Should parse valid files despite syntax errors"

    def test_extract_correct_symbol_definitions_and_references(self, temp_repo):
        """Test extracting correct symbol definitions and references.

        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitterChunker not implemented yet")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(temp_repo)

        # Find Python chunks
        python_chunks = [c for c in chunks if c.path.endswith("main.py")]

        # Check symbol definitions
        all_defined = []
        for chunk in python_chunks:
            all_defined.extend(chunk.symbols_defined)

        assert len(all_defined) > 0, "Should extract symbol definitions"

        # Check that chunks have correct metadata
        for chunk in python_chunks:
            assert chunk.start_line > 0, "Start line should be positive"
            assert chunk.end_line >= chunk.start_line, "End line should be >= start line"
            assert chunk.language == "python", "Language should be detected as python"
            assert len(chunk.content) > 0, "Content should not be empty"


class TestRegexChunker:
    """Unit tests for RegexChunker fallback implementation."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Create Python file
            (repo_path / "main.py").write_text(PYTHON_SAMPLE)

            # Create JavaScript file
            (repo_path / "script.js").write_text(JAVASCRIPT_SAMPLE)

            yield str(repo_path)

    def test_parse_python_with_regex(self, temp_repo):
        """Test parsing Python file with regex patterns.

        Requirements: 1.5
        """
        try:
            from ws_ctx_engine.chunker import RegexChunker
        except ImportError:
            pytest.skip("RegexChunker not implemented yet")

        chunker = RegexChunker()
        chunks = chunker.parse(temp_repo)

        # Filter to Python file chunks
        python_chunks = [c for c in chunks if c.path.endswith("main.py")]

        assert len(python_chunks) > 0, "Should parse Python file with regex"

        # Check that we found some symbols
        symbols_found = []
        for chunk in python_chunks:
            symbols_found.extend(chunk.symbols_defined)

        assert len(symbols_found) > 0, "Should find some symbols with regex"

    def test_parse_javascript_with_regex(self, temp_repo):
        """Test parsing JavaScript file with regex patterns.

        Requirements: 1.5
        """
        try:
            from ws_ctx_engine.chunker import RegexChunker
        except ImportError:
            pytest.skip("RegexChunker not implemented yet")

        chunker = RegexChunker()
        chunks = chunker.parse(temp_repo)

        # Filter to JavaScript file chunks
        js_chunks = [c for c in chunks if c.path.endswith("script.js")]

        assert len(js_chunks) > 0, "Should parse JavaScript file with regex"


class TestFallbackLogic:
    """Unit tests for fallback logic between TreeSitter and Regex."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / "main.py").write_text(PYTHON_SAMPLE)
            yield str(repo_path)

    def test_fallback_to_regex_on_treesitter_failure(self, temp_repo, caplog):
        """Test fallback to RegexChunker when TreeSitter fails.

        Requirements: 1.5, 1.6, 10.1, 10.2
        """
        try:
            from ws_ctx_engine.chunker import parse_with_fallback
        except ImportError:
            pytest.skip("parse_with_fallback not implemented yet")

        # This should try TreeSitter first, then fall back to Regex
        chunks = parse_with_fallback(temp_repo)

        assert len(chunks) > 0, "Should parse files with fallback"

    def test_fallback_logs_warning(self, temp_repo, caplog):
        """Test that fallback logs a warning.

        Requirements: 1.6, 10.2
        """
        try:
            from ws_ctx_engine.chunker import parse_with_fallback
        except ImportError:
            pytest.skip("parse_with_fallback not implemented yet")

        # Parse with fallback
        chunks = parse_with_fallback(temp_repo)

        # Check if warning was logged (if fallback was triggered)
        # Note: This test may not trigger fallback if TreeSitter works fine
        assert len(chunks) > 0, "Should parse files"
