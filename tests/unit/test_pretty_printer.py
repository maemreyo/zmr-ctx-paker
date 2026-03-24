"""Unit tests for Pretty Printer.

These tests validate specific examples and edge cases for the PrettyPrinter.
"""

import ast
import tempfile
from pathlib import Path

import pytest

from context_packer.chunker import TreeSitterChunker
from context_packer.formatters import PrettyPrinter
from context_packer.models import CodeChunk


class TestPrettyPrinterBasics:
    """Test basic PrettyPrinter functionality."""
    
    def test_format_single_python_function(self):
        """Test formatting a single Python function chunk."""
        chunks = [
            CodeChunk(
                path="test.py",
                start_line=1,
                end_line=3,
                content="def hello():\n    return 'world'",
                symbols_defined=["hello"],
                symbols_referenced=[],
                language="python"
            )
        ]
        
        printer = PrettyPrinter()
        formatted = printer.format(chunks)
        
        # Should be valid Python
        ast.parse(formatted)
        
        # Should contain the function
        assert "def hello():" in formatted
        assert "return 'world'" in formatted
    
    def test_format_multiple_python_chunks(self):
        """Test formatting multiple Python chunks."""
        chunks = [
            CodeChunk(
                path="test.py",
                start_line=1,
                end_line=3,
                content="def func1():\n    pass",
                symbols_defined=["func1"],
                symbols_referenced=[],
                language="python"
            ),
            CodeChunk(
                path="test.py",
                start_line=5,
                end_line=7,
                content="def func2():\n    pass",
                symbols_defined=["func2"],
                symbols_referenced=[],
                language="python"
            )
        ]
        
        printer = PrettyPrinter()
        formatted = printer.format(chunks)
        
        # Should be valid Python
        ast.parse(formatted)
        
        # Should contain both functions
        assert "def func1():" in formatted
        assert "def func2():" in formatted
    
    def test_format_python_class(self):
        """Test formatting a Python class chunk."""
        chunks = [
            CodeChunk(
                path="test.py",
                start_line=1,
                end_line=5,
                content="class MyClass:\n    def method(self):\n        return 42",
                symbols_defined=["MyClass"],
                symbols_referenced=[],
                language="python"
            )
        ]
        
        printer = PrettyPrinter()
        formatted = printer.format(chunks)
        
        # Should be valid Python
        ast.parse(formatted)
        
        # Should contain the class
        assert "class MyClass:" in formatted
        assert "def method(self):" in formatted
    
    def test_format_javascript_function(self):
        """Test formatting a JavaScript function chunk."""
        chunks = [
            CodeChunk(
                path="test.js",
                start_line=1,
                end_line=3,
                content="function hello() {\n    return 42;\n}",
                symbols_defined=["hello"],
                symbols_referenced=[],
                language="javascript"
            )
        ]
        
        printer = PrettyPrinter()
        formatted = printer.format(chunks)
        
        # Should contain the function
        assert "function hello()" in formatted
        assert "return 42;" in formatted
    
    def test_format_javascript_class(self):
        """Test formatting a JavaScript class chunk."""
        chunks = [
            CodeChunk(
                path="test.js",
                start_line=1,
                end_line=7,
                content="class MyClass {\n    constructor() {\n        this.value = 0;\n    }\n}",
                symbols_defined=["MyClass"],
                symbols_referenced=[],
                language="javascript"
            )
        ]
        
        printer = PrettyPrinter()
        formatted = printer.format(chunks)
        
        # Should contain the class
        assert "class MyClass" in formatted
        assert "constructor()" in formatted


class TestPrettyPrinterRoundTrip:
    """Test round-trip equivalence for various source files."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("tree_sitter", reason="tree-sitter not available"),
        reason="Requires tree-sitter"
    )
    def test_python_round_trip_simple_function(self):
        """Test round-trip for simple Python function."""
        original_code = """def greet(name):
    '''Greet someone.'''
    return f'Hello, {name}!'
"""
        
        try:
            chunker = TreeSitterChunker()
        except ImportError:
            pytest.skip("TreeSitterChunker not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            
            # First parse
            file_path.write_text(original_code)
            chunks1 = chunker.parse(tmpdir)
            
            # Format
            printer = PrettyPrinter()
            formatted = printer.format(chunks1)
            
            # Second parse
            file_path.write_text(formatted)
            chunks2 = chunker.parse(tmpdir)
            
            # Should have same number of chunks
            assert len(chunks1) == len(chunks2)
            
            # Should have same symbols
            symbols1 = {s for c in chunks1 for s in c.symbols_defined}
            symbols2 = {s for c in chunks2 for s in c.symbols_defined}
            assert symbols1 == symbols2
    
    @pytest.mark.skipif(
        not pytest.importorskip("tree_sitter", reason="tree-sitter not available"),
        reason="Requires tree-sitter"
    )
    def test_python_round_trip_class_with_methods(self):
        """Test round-trip for Python class with methods."""
        original_code = """class Calculator:
    '''A simple calculator.'''
    
    def add(self, a, b):
        '''Add two numbers.'''
        return a + b
    
    def subtract(self, a, b):
        '''Subtract two numbers.'''
        return a - b
"""
        
        try:
            chunker = TreeSitterChunker()
        except ImportError:
            pytest.skip("TreeSitterChunker not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            
            # First parse
            file_path.write_text(original_code)
            chunks1 = chunker.parse(tmpdir)
            
            # Format
            printer = PrettyPrinter()
            formatted = printer.format(chunks1)
            
            # Second parse
            file_path.write_text(formatted)
            chunks2 = chunker.parse(tmpdir)
            
            # Should have same number of chunks
            assert len(chunks1) == len(chunks2)
            
            # Should have same symbols
            symbols1 = {s for c in chunks1 for s in c.symbols_defined}
            symbols2 = {s for c in chunks2 for s in c.symbols_defined}
            assert symbols1 == symbols2
    
    @pytest.mark.skipif(
        not pytest.importorskip("tree_sitter", reason="tree-sitter not available"),
        reason="Requires tree-sitter"
    )
    def test_javascript_round_trip_function_and_class(self):
        """Test round-trip for JavaScript function and class."""
        original_code = """function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }
    
    sayHello() {
        return greet(this.name);
    }
}
"""
        
        try:
            chunker = TreeSitterChunker()
        except ImportError:
            pytest.skip("TreeSitterChunker not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.js"
            
            # First parse
            file_path.write_text(original_code)
            chunks1 = chunker.parse(tmpdir)
            
            # Format
            printer = PrettyPrinter()
            formatted = printer.format(chunks1)
            
            # Second parse
            file_path.write_text(formatted)
            chunks2 = chunker.parse(tmpdir)
            
            # Should have same number of chunks
            assert len(chunks1) == len(chunks2)
            
            # Should have same symbols
            symbols1 = {s for c in chunks1 for s in c.symbols_defined}
            symbols2 = {s for c in chunks2 for s in c.symbols_defined}
            assert symbols1 == symbols2


class TestPrettyPrinterEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_chunks_list_raises_error(self):
        """Test that empty chunks list raises ValueError."""
        printer = PrettyPrinter()
        
        with pytest.raises(ValueError, match="Cannot format empty chunks list"):
            printer.format([])
    
    def test_mixed_languages_raises_error(self):
        """Test that mixed language chunks raise ValueError."""
        chunks = [
            CodeChunk(
                path="test.py",
                start_line=1,
                end_line=2,
                content="def hello():\n    pass",
                symbols_defined=["hello"],
                symbols_referenced=[],
                language="python"
            ),
            CodeChunk(
                path="test.js",
                start_line=1,
                end_line=2,
                content="function hello() {}",
                symbols_defined=["hello"],
                symbols_referenced=[],
                language="javascript"
            )
        ]
        
        printer = PrettyPrinter()
        
        with pytest.raises(ValueError, match="All chunks must be same language"):
            printer.format(chunks)
    
    def test_unsupported_language_raises_error(self):
        """Test that unsupported language raises ValueError."""
        chunks = [
            CodeChunk(
                path="test.rb",
                start_line=1,
                end_line=2,
                content="def hello\n  puts 'world'\nend",
                symbols_defined=["hello"],
                symbols_referenced=[],
                language="ruby"
            )
        ]
        
        printer = PrettyPrinter()
        
        with pytest.raises(ValueError, match="Unsupported language"):
            printer.format(chunks)
    
    def test_format_file_filters_by_path(self):
        """Test that format_file filters chunks by path."""
        chunks = [
            CodeChunk(
                path="file1.py",
                start_line=1,
                end_line=2,
                content="def func1():\n    pass",
                symbols_defined=["func1"],
                symbols_referenced=[],
                language="python"
            ),
            CodeChunk(
                path="file2.py",
                start_line=1,
                end_line=2,
                content="def func2():\n    pass",
                symbols_defined=["func2"],
                symbols_referenced=[],
                language="python"
            )
        ]
        
        printer = PrettyPrinter()
        formatted = printer.format_file(chunks, "file1.py")
        
        # Should only contain func1
        assert "def func1():" in formatted
        assert "def func2():" not in formatted
    
    def test_format_file_nonexistent_path_raises_error(self):
        """Test that format_file raises error for non-existent path."""
        chunks = [
            CodeChunk(
                path="file1.py",
                start_line=1,
                end_line=2,
                content="def func1():\n    pass",
                symbols_defined=["func1"],
                symbols_referenced=[],
                language="python"
            )
        ]
        
        printer = PrettyPrinter()
        
        with pytest.raises(ValueError, match="No chunks found for file"):
            printer.format_file(chunks, "nonexistent.py")
    
    def test_chunks_sorted_by_line_number(self):
        """Test that chunks are sorted by line number when formatting."""
        chunks = [
            CodeChunk(
                path="test.py",
                start_line=10,
                end_line=12,
                content="def func2():\n    pass",
                symbols_defined=["func2"],
                symbols_referenced=[],
                language="python"
            ),
            CodeChunk(
                path="test.py",
                start_line=1,
                end_line=3,
                content="def func1():\n    pass",
                symbols_defined=["func1"],
                symbols_referenced=[],
                language="python"
            )
        ]
        
        printer = PrettyPrinter()
        formatted = printer.format(chunks)
        
        # func1 should appear before func2
        func1_pos = formatted.find("def func1():")
        func2_pos = formatted.find("def func2():")
        
        assert func1_pos < func2_pos, "Chunks should be sorted by line number"
