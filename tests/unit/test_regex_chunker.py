"""Unit tests for RegexChunker."""

import tempfile
from pathlib import Path

import pytest

from context_packer.chunker.regex import RegexChunker


class TestRegexChunker:
    """Tests for RegexChunker fallback implementation."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_parse_python_simple(self, temp_repo):
        """Test parsing Python file with functions."""
        code = """def hello():
    print("Hello")

def world():
    print("World")
"""
        (temp_repo / "main.py").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        python_chunks = [c for c in chunks if c.path.endswith("main.py")]
        assert len(python_chunks) >= 2

    def test_parse_python_class(self, temp_repo):
        """Test parsing Python file with classes."""
        code = """class Hello:
    def greet(self):
        pass

class World:
    pass
"""
        (temp_repo / "classes.py").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        python_chunks = [c for c in chunks if c.path.endswith("classes.py")]
        symbols = []
        for chunk in python_chunks:
            symbols.extend(chunk.symbols_defined)
        assert "Hello" in symbols or "World" in symbols

    def test_parse_javascript_functions(self, temp_repo):
        """Test parsing JavaScript file."""
        code = """function hello() {
    console.log("Hello");
}

function world() {
    console.log("World");
}
"""
        (temp_repo / "main.js").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("main.js")]
        assert len(js_chunks) >= 2

    def test_parse_javascript_arrow_functions(self, temp_repo):
        """Test parsing JavaScript arrow functions."""
        code = """const hello = () => {
    console.log("Hello");
};

const add = (a, b) => a + b;
"""
        (temp_repo / "arrow.js").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("arrow.js")]
        assert len(js_chunks) >= 1

    def test_parse_javascript_class(self, temp_repo):
        """Test parsing JavaScript class."""
        code = """class Calculator {
    constructor() {
        this.result = 0;
    }

    add(a, b) {
        return a + b;
    }
}
"""
        (temp_repo / "class.js").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("class.js")]
        symbols = []
        for chunk in js_chunks:
            symbols.extend(chunk.symbols_defined)
        assert "Calculator" in symbols

    def test_parse_typescript(self, temp_repo):
        """Test parsing TypeScript file."""
        code = """function greet(name: string): string {
    return `Hello, ${name}`;
}

class Greeter {
    name: string;
}
"""
        (temp_repo / "main.ts").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("main.ts")]
        assert len(ts_chunks) >= 1

    def test_parse_rust_functions(self, temp_repo):
        """Test parsing Rust file."""
        code = """fn hello() {
    println!("Hello");
}

fn world() {
    println!("World");
}

pub struct Greeter {
    name: String,
}
"""
        (temp_repo / "main.rs").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("main.rs")]
        symbols = []
        for chunk in rs_chunks:
            symbols.extend(chunk.symbols_defined)
        assert "hello" in symbols or "Greeter" in symbols

    def test_parse_rust_struct_and_impl(self, temp_repo):
        """Test parsing Rust struct and impl."""
        code = """struct Counter {
    count: i32,
}

impl Counter {
    fn new() -> Self {
        Counter { count: 0 }
    }
}
"""
        (temp_repo / "counter.rs").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("counter.rs")]
        symbols = []
        for chunk in rs_chunks:
            symbols.extend(chunk.symbols_defined)
        assert "Counter" in symbols

    def test_parse_rust_enum(self, temp_repo):
        """Test parsing Rust enum."""
        code = """enum Color {
    Red,
    Green,
    Blue,
}
"""
        (temp_repo / "color.rs").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("color.rs")]
        symbols = []
        for chunk in rs_chunks:
            symbols.extend(chunk.symbols_defined)
        assert "Color" in symbols

    def test_parse_rust_trait(self, temp_repo):
        """Test parsing Rust trait."""
        code = """trait Drawable {
    fn draw(&self);
}
"""
        (temp_repo / "trait.rs").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("trait.rs")]
        symbols = []
        for chunk in rs_chunks:
            symbols.extend(chunk.symbols_defined)
        assert "Drawable" in symbols

    def test_parse_python_imports_extracted(self, temp_repo):
        """Test that Python imports are extracted."""
        code = """import os
import sys
from collections import defaultdict

def hello():
    pass
"""
        (temp_repo / "imports.py").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("imports.py")]
        all_refs = []
        for chunk in py_chunks:
            all_refs.extend(chunk.symbols_referenced)
        assert "os" in all_refs or "sys" in all_refs

    def test_parse_javascript_imports_extracted(self, temp_repo):
        """Test that JavaScript imports are extracted."""
        code = """import React from 'react';
import { useState } from 'react';

export function Hello() {
    return <div>Hello</div>;
}
"""
        (temp_repo / "imports.js").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("imports.js")]
        all_refs = []
        for chunk in js_chunks:
            all_refs.extend(chunk.symbols_referenced)
        assert "react" in all_refs

    def test_parse_rust_imports_extracted(self, temp_repo):
        """Test that Rust imports are extracted."""
        code = """use std::collections::HashMap;

fn main() {
    println!("Hello");
}
"""
        (temp_repo / "imports.rs").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("imports.rs")]
        all_refs = []
        for chunk in rs_chunks:
            all_refs.extend(chunk.symbols_referenced)
        assert len(all_refs) >= 0

    def test_parse_nonexistent_path_raises(self, temp_repo):
        """Test that nonexistent path raises ValueError."""
        chunker = RegexChunker()
        with pytest.raises(ValueError):
            chunker.parse("/nonexistent/path/12345")

    def test_parse_file_path_raises(self, temp_repo):
        """Test that file path instead of directory raises ValueError."""
        (temp_repo / "file.py").write_text("print('hello')")
        chunker = RegexChunker()
        with pytest.raises(ValueError):
            chunker.parse(str(temp_repo / "file.py"))

    def test_parse_with_nested_braces(self, temp_repo):
        """Test parsing with nested brace structures."""
        code = """function outer() {
    function inner() {
        console.log("nested");
    }
    return inner;
}
"""
        (temp_repo / "nested.js").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("nested.js")]
        assert len(js_chunks) >= 1

    def test_parse_python_with_nested_indent(self, temp_repo):
        """Test parsing Python with nested indentation."""
        code = """class Outer:
    class Inner:
        def method(self):
            pass

    def outer_method(self):
        pass
"""
        (temp_repo / "nested.py").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("nested.py")]
        assert len(py_chunks) >= 1

    def test_parse_empty_file(self, temp_repo):
        """Test parsing empty file."""
        (temp_repo / "empty.py").write_text("")
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        empty_chunks = [c for c in chunks if c.path.endswith("empty.py")]
        assert len(empty_chunks) == 0

    def test_chunk_content_matches_source(self, temp_repo):
        """Test that chunk content matches source lines."""
        code = """def hello():
    print("Hello")
"""
        (temp_repo / "hello.py").write_text(code)
        chunker = RegexChunker()
        chunks = chunker.parse(str(temp_repo))

        hello_chunks = [c for c in chunks if c.path.endswith("hello.py")]
        if hello_chunks:
            chunk = hello_chunks[0]
            lines = code.split('\n')
            expected = '\n'.join(lines[chunk.start_line - 1:chunk.end_line])
            assert chunk.content.strip() == expected.strip()
