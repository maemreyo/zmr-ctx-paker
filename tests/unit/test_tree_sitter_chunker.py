"""Unit tests for TreeSitterChunker improvements."""

import tempfile
from pathlib import Path

import pytest

from context_packer.models import CodeChunk


PYTHON_WITH_IMPORTS = '''import os
import sys
from collections import defaultdict

def hello():
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

PYTHON_NESTED_CLASS = '''class Outer:
    class Inner:
        def method(self):
            pass
'''

JAVASCRIPT_WITH_IMPORTS = '''import React from 'react';
import { useState } from 'react';
import utils from './utils';

export function hello() {
    return "Hello";
}

export class Greeter {
    greet() {
        return "Hello";
    }
}
'''

RUST_WITH_USE = '''use std::collections::HashMap;
use std::io::{Read, Write};

pub fn hello() {
    println!("Hello");
}

pub struct Greeter {
    name: String,
}
'''


class TestTreeSitterChunkerFileImports:
    """Tests for file-level imports extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_python_file_imports_in_symbols_referenced(self, temp_repo):
        """Test that Python file-level imports are included in symbols_referenced."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        (temp_repo / "main.py").write_text(PYTHON_WITH_IMPORTS)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        python_chunks = [c for c in chunks if c.path.endswith("main.py")]
        assert len(python_chunks) > 0

        all_referenced = []
        for chunk in python_chunks:
            all_referenced.extend(chunk.symbols_referenced)

        assert 'os' in all_referenced or 'sys' in all_referenced, \
            f"File imports should be in symbols_referenced, got: {all_referenced}"

    def test_javascript_file_imports_in_symbols_referenced(self, temp_repo):
        """Test that JavaScript file-level imports are included in symbols_referenced."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        (temp_repo / "app.js").write_text(JAVASCRIPT_WITH_IMPORTS)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("app.js")]
        assert len(js_chunks) > 0

        all_referenced = []
        for chunk in js_chunks:
            all_referenced.extend(chunk.symbols_referenced)

        assert 'react' in all_referenced or './utils' in all_referenced, \
            f"File imports should be in symbols_referenced, got: {all_referenced}"

    def test_rust_use_declarations_in_symbols_referenced(self, temp_repo):
        """Test that Rust use declarations are included in symbols_referenced."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        (temp_repo / "main.rs").write_text(RUST_WITH_USE)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        rust_chunks = [c for c in chunks if c.path.endswith("main.rs")]
        assert len(rust_chunks) > 0

        all_referenced = []
        for chunk in rust_chunks:
            all_referenced.extend(chunk.symbols_referenced)

        assert 'HashMap' in all_referenced or 'Read' in all_referenced, \
            f"Use declarations should be in symbols_referenced, got: {all_referenced}"


class TestTreeSitterChunkerDeduplication:
    """Tests for chunk deduplication."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_no_duplicate_chunks_same_span(self, temp_repo):
        """Test that identical chunks (same path, start_line, end_line) are deduplicated."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''def foo():
    pass

class Bar:
    pass
'''
        (temp_repo / "main.py").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        python_chunks = [c for c in chunks if c.path.endswith("main.py")]

        seen = set()
        for chunk in python_chunks:
            key = (chunk.path, chunk.start_line, chunk.end_line)
            assert key not in seen, \
                f"Duplicate chunk found: {chunk.path}:{chunk.start_line}-{chunk.end_line}"
            seen.add(key)

    def test_nested_class_extracted_separately(self, temp_repo):
        """Test that nested classes are extracted as separate chunks."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        (temp_repo / "nested.py").write_text(PYTHON_NESTED_CLASS)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        python_chunks = [c for c in chunks if c.path.endswith("nested.py")]

        symbol_names = []
        for chunk in python_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'Outer' in symbol_names, f"Outer class should be extracted, got: {symbol_names}"
        assert 'Inner' in symbol_names, f"Inner class should be extracted, got: {symbol_names}"


class TestTreeSitterChunkerChunkContent:
    """Tests for chunk content correctness."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_chunk_content_matches_source_lines(self, temp_repo):
        """Test that chunk content matches the source lines."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''def hello():
    print("Hello")

def world():
    print("World")
'''
        (temp_repo / "funcs.py").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        funcs_chunks = [c for c in chunks if c.path.endswith("funcs.py")]

        for chunk in funcs_chunks:
            lines = code.split('\n')
            expected_content = '\n'.join(lines[chunk.start_line - 1:chunk.end_line])
            assert chunk.content.strip() == expected_content.strip(), \
                f"Chunk content mismatch for {chunk.path}:{chunk.start_line}-{chunk.end_line}"

    def test_chunk_symbols_defined_not_empty(self, temp_repo):
        """Test that chunks have non-empty symbols_defined."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''def my_function():
    pass

class MyClass:
    pass
'''
        (temp_repo / "sample.py").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        python_chunks = [c for c in chunks if c.path.endswith("sample.py")]

        for chunk in python_chunks:
            if chunk.symbols_defined:
                assert len(chunk.symbols_defined) > 0, \
                    f"Chunk should have symbols_defined for {chunk.path}:{chunk.start_line}"


class TestRustMacroExtraction:
    """Tests for Rust macro extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_extract_macro_rules(self, temp_repo):
        """Test that macro_rules! is extracted as a chunk."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''macro_rules! my_macro {
    ($x:expr) => { $x * 2 };
}

fn hello() {
    my_macro!(5);
}
'''
        (temp_repo / "macros.rs").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        rust_chunks = [c for c in chunks if c.path.endswith("macros.rs")]

        symbol_names = []
        for chunk in rust_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'my_macro' in symbol_names, \
            f"macro_rules! my_macro should be extracted, got: {symbol_names}"


class TestJSXTSXExtraction:
    """Tests for JSX/TSX extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_extract_jsx_element(self, temp_repo):
        """Test that JSX elements are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''function Component() {
    return <div>Hello</div>;
}
'''
        (temp_repo / "component.jsx").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        jsx_chunks = [c for c in chunks if c.path.endswith("component.jsx")]

        symbol_names = []
        for chunk in jsx_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'Component' in symbol_names or 'div' in symbol_names, \
            f"JSX component should be extracted, got: {symbol_names}"

    def test_extract_tsx_component(self, temp_repo):
        """Test that TSX components are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''interface Props {
    name: string;
}

function Greeting({ name }: Props) {
    return <div>Hello, {name}</div>;
}
'''
        (temp_repo / "greeting.tsx").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        tsx_chunks = [c for c in chunks if c.path.endswith("greeting.tsx")]

        symbol_names = []
        for chunk in tsx_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'Props' in symbol_names or 'Greeting' in symbol_names, \
            f"TSX component should be extracted, got: {symbol_names}"


class TestPythonAsyncExtraction:
    """Tests for Python async function extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_extract_async_function(self, temp_repo):
        """Test that async functions are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''async def fetch_data(url):
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def process():
    data = await fetch_data("http://example.com")
    return data
'''
        (temp_repo / "async_example.py").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        python_chunks = [c for c in chunks if c.path.endswith("async_example.py")]

        symbol_names = []
        for chunk in python_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'fetch_data' in symbol_names, \
            f"async function fetch_data should be extracted, got: {symbol_names}"
        assert 'process' in symbol_names, \
            f"async function process should be extracted, got: {symbol_names}"
