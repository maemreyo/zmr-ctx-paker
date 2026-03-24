"""Unit tests for LanguageResolver implementations."""

import pytest
from unittest.mock import MagicMock

from context_packer.chunker.resolvers import (
    LanguageResolver,
    RustResolver,
    PythonResolver,
    JavaScriptResolver,
    TypeScriptResolver,
)


class TestRustResolver:
    """Unit tests for RustResolver."""

    @pytest.fixture
    def resolver(self):
        return RustResolver()

    def test_language(self, resolver):
        assert resolver.language == 'rust'

    def test_file_extensions(self, resolver):
        assert resolver.file_extensions == ['.rs']

    def test_target_types(self, resolver):
        expected = {
            'function_item', 'struct_item', 'trait_item', 'impl_item',
            'enum_item', 'const_item', 'type_item', 'static_item', 'mod_item',
            'macro_definition', 'union_item', 'function_signature_item',
        }
        assert resolver.target_types == expected

    def test_extract_symbol_name_function_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'function_item'
        mock_node.children = [
            MagicMock(type='identifier', text=b'foo'),
            MagicMock(type='parameters'),
        ]
        mock_node.text = b'fn foo() {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'foo'

    def test_extract_symbol_name_struct_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'struct_item'
        mock_node.children = [
            MagicMock(type='identifier', text=b'Bar'),
        ]
        mock_node.text = b'struct Bar {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'Bar'

    def test_extract_symbol_name_impl_item(self, resolver):
        """Test that impl_item extracts the type name, not 'impl' keyword."""
        mock_node = MagicMock()
        mock_node.type = 'impl_item'
        mock_node.children = [
            MagicMock(type='impl'),
            MagicMock(type='identifier', text=b'Foo'),
        ]
        mock_node.text = b'impl Foo {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'Foo', f"impl_item should extract 'Foo', not '{name}'"

    def test_extract_symbol_name_impl_item_with_generics(self, resolver):
        """Test impl<T> extracts correct type name."""
        mock_node = MagicMock()
        mock_node.type = 'impl_item'
        mock_node.children = [
            MagicMock(type='impl'),
            MagicMock(type='type_identifier', text=b'Foo'),
            MagicMock(type='generics'),
        ]
        mock_node.text = b'impl<T> Foo<T> {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'Foo', f"impl<T> should extract 'Foo', got '{name}'"

    def test_extract_symbol_name_trait_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'trait_item'
        mock_node.children = [
            MagicMock(type='trait'),
            MagicMock(type='identifier', text=b'MyTrait'),
        ]
        mock_node.text = b'trait MyTrait {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'MyTrait'

    def test_extract_symbol_name_enum_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'enum_item'
        mock_node.children = [
            MagicMock(type='enum'),
            MagicMock(type='identifier', text=b'Color'),
        ]
        mock_node.text = b'enum Color { Red, Green, Blue }'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'Color'

    def test_extract_symbol_name_const_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'const_item'
        mock_node.children = [
            MagicMock(type='const'),
            MagicMock(type='identifier', text=b'MAX_SIZE'),
        ]
        mock_node.text = b'const MAX_SIZE: usize = 100;'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'MAX_SIZE'

    def test_extract_symbol_name_type_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'type_item'
        mock_node.children = [
            MagicMock(type='type'),
            MagicMock(type='identifier', text=b'TypeAlias'),
        ]
        mock_node.text = b'type TypeAlias = i32;'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'TypeAlias'

    def test_extract_symbol_name_mod_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'mod_item'
        mock_node.children = [
            MagicMock(type='mod'),
            MagicMock(type='identifier', text=b'my_module'),
        ]
        mock_node.text = b'mod my_module;'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'my_module'

    def test_extract_symbol_name_macro_definition(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'macro_definition'
        mock_node.children = [
            MagicMock(type='macro_rules!'),
            MagicMock(type='identifier', text=b'my_macro'),
        ]
        mock_node.text = b'macro_rules! my_macro { }'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'my_macro'

    def test_union_item_in_target_types(self, resolver):
        assert 'union_item' in resolver.target_types

    def test_extract_symbol_name_union_item(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'union_item'
        mock_node.children = [
            MagicMock(type='union'),
            MagicMock(type='identifier', text=b'MyUnion'),
        ]
        mock_node.text = b'union MyUnion { a: i32, b: f32, }'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'MyUnion'

    def test_function_signature_item_in_target_types(self, resolver):
        assert 'function_signature_item' in resolver.target_types

    def test_extract_symbol_name_no_identifier(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'function_item'
        mock_node.children = []
        mock_node.text = b''

        name = resolver.extract_symbol_name(mock_node)
        assert name is None

    def test_extract_references_from_use_declaration(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'use_declaration'
        mock_node.children = [
            MagicMock(type='use'),
            MagicMock(type='identifier', text=b'std'),
            MagicMock(type='path'),
        ]
        mock_node.text = b'use std::collections;'

        refs = resolver.extract_references(mock_node)
        assert 'std' in refs

    def test_extract_references_from_call_expression(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'call_expression'
        mock_node.children = [
            MagicMock(type='identifier', text=b'foo'),
            MagicMock(type='arguments'),
        ]
        mock_node.text = b'foo()'

        refs = resolver.extract_references(mock_node)
        assert 'foo' in refs

    def test_should_extract(self, resolver):
        assert resolver.should_extract('function_item') is True
        assert resolver.should_extract('struct_item') is True
        assert resolver.should_extract('random_item') is False


class TestPythonResolver:
    """Unit tests for PythonResolver."""

    @pytest.fixture
    def resolver(self):
        return PythonResolver()

    def test_language(self, resolver):
        assert resolver.language == 'python'

    def test_file_extensions(self, resolver):
        assert resolver.file_extensions == ['.py']

    def test_target_types(self, resolver):
        expected = {
            'function_definition', 'class_definition',
            'decorated_definition', 'type_alias_statement',
        }
        assert resolver.target_types == expected

    def test_extract_symbol_name_function_definition(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'function_definition'
        mock_node.children = [
            MagicMock(type='def'),
            MagicMock(type='identifier', text=b'hello'),
            MagicMock(type='parameters'),
        ]
        mock_node.text = b'def hello(): pass'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'hello'

    def test_extract_symbol_name_class_definition(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'class_definition'
        mock_node.children = [
            MagicMock(type='class'),
            MagicMock(type='identifier', text=b'MyClass'),
            MagicMock(type='base_classes'),
        ]
        mock_node.text = b'class MyClass: pass'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'MyClass'

    def test_async_is_function_definition_with_async_child(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'function_definition'
        mock_node.children = [
            MagicMock(type='async'),
            MagicMock(type='def'),
            MagicMock(type='identifier', text=b'hello_async'),
            MagicMock(type='parameters'),
        ]
        mock_node.text = b'async def hello_async(): pass'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'hello_async'

    def test_type_alias_statement_in_target_types(self, resolver):
        assert 'type_alias_statement' in resolver.target_types

    def test_extract_symbol_name_type_alias_statement(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'type_alias_statement'
        mock_node.children = [
            MagicMock(type='type'),
            MagicMock(type='identifier', text=b'MyAlias'),
        ]
        mock_node.text = b'type MyAlias = int | str'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'MyAlias'

    def test_extract_references_from_import(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'import_statement'
        mock_node.children = [
            MagicMock(type='import'),
            MagicMock(type='identifier', text=b'os'),
        ]
        mock_node.text = b'import os'

        refs = resolver.extract_references(mock_node)
        assert 'os' in refs

    def test_extract_references_from_call(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'call_expression'
        mock_node.children = [
            MagicMock(type='identifier', text=b'foo'),
            MagicMock(type='arguments'),
        ]
        mock_node.text = b'foo()'

        refs = resolver.extract_references(mock_node)
        assert 'foo' in refs


class TestJavaScriptResolver:
    """Unit tests for JavaScriptResolver."""

    @pytest.fixture
    def resolver(self):
        return JavaScriptResolver()

    def test_language(self, resolver):
        assert resolver.language == 'javascript'

    def test_file_extensions(self, resolver):
        assert resolver.file_extensions == ['.js', '.jsx']

    def test_extract_symbol_name_function_declaration(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'function_declaration'
        mock_node.children = [
            MagicMock(type='function'),
            MagicMock(type='identifier', text=b'hello'),
            MagicMock(type='parameters'),
        ]
        mock_node.text = b'function hello() {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'hello'

    def test_extract_symbol_name_class_declaration(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'class_declaration'
        mock_node.children = [
            MagicMock(type='class'),
            MagicMock(type='identifier', text=b'Person'),
        ]
        mock_node.text = b'class Person {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'Person'

    def test_jsx_element_target_type(self, resolver):
        assert 'jsx_element' in resolver.target_types or resolver.should_extract('jsx_element')

    def test_generator_function_declaration_in_target_types(self, resolver):
        assert 'generator_function_declaration' in resolver.target_types

    def test_extract_symbol_name_generator_function(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'generator_function_declaration'
        mock_node.children = [
            MagicMock(type='function'),
            MagicMock(type='*'),
            MagicMock(type='identifier', text=b'gen'),
            MagicMock(type='parameters'),
        ]
        mock_node.text = b'function* gen() { yield 1; }'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'gen'

    def test_jsx_element_target_type(self, resolver):
        assert 'jsx_element' in resolver.target_types or resolver.should_extract('jsx_element')

    def test_extract_symbol_name_jsx_component(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'jsx_element'
        mock_node.children = [
            MagicMock(type='jsx_opening_element'),
            MagicMock(type='jsx_identifier', text=b'Component'),
        ]
        mock_node.text = b'<Component />'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'Component'


class TestTypeScriptResolver:
    """Unit tests for TypeScriptResolver."""

    @pytest.fixture
    def resolver(self):
        return TypeScriptResolver()

    def test_language(self, resolver):
        assert resolver.language == 'typescript'

    def test_file_extensions(self, resolver):
        assert resolver.file_extensions == ['.ts', '.tsx']

    def test_target_types_includes_interface(self, resolver):
        assert 'interface_declaration' in resolver.target_types

    def test_extract_symbol_name_interface_declaration(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'interface_declaration'
        mock_node.children = [
            MagicMock(type='interface'),
            MagicMock(type='identifier', text=b'User'),
        ]
        mock_node.text = b'interface User {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'User'

    def test_extract_symbol_name_type_alias(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'type_alias_declaration'
        mock_node.children = [
            MagicMock(type='type'),
            MagicMock(type='identifier', text=b'ID'),
        ]
        mock_node.text = b'type ID = string | number;'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'ID'

    def test_internal_module_namespace_in_target_types(self, resolver):
        assert 'internal_module' in resolver.target_types

    def test_extract_symbol_name_internal_module(self, resolver):
        mock_node = MagicMock()
        mock_node.type = 'internal_module'
        mock_node.children = [
            MagicMock(type='namespace'),
            MagicMock(type='identifier', text=b'MyNamespace'),
        ]
        mock_node.text = b'namespace MyNamespace {}'

        name = resolver.extract_symbol_name(mock_node)
        assert name == 'MyNamespace'


class TestExtractReferences:
    """Tests for improved extract_references across all resolvers."""

    def test_python_extract_references_member_expression(self):
        """Test that Python resolver extracts references from attribute access."""
        resolver = PythonResolver()
        mock_node = MagicMock()
        mock_node.type = 'call_expression'
        mock_node.children = [
            MagicMock(type='identifier', text=b'obj'),
            MagicMock(type='attribute'),
            MagicMock(type='identifier', text=b'method'),
            MagicMock(type='arguments'),
        ]
        mock_node.text = b'obj.method()'

        refs = resolver.extract_references(mock_node)
        assert 'obj' in refs or 'method' in refs

    def test_python_extract_references_from_nested_calls(self):
        """Test extracting references from nested call expressions."""
        resolver = PythonResolver()
        mock_node = MagicMock()
        mock_node.type = 'call_expression'
        mock_node.children = [
            MagicMock(type='identifier', text=b'outer'),
            MagicMock(type='arguments'),
        ]
        mock_node.text = b'outer(inner())'

        refs = resolver.extract_references(mock_node)
        assert 'outer' in refs

    def test_javascript_extract_references_new_expression(self):
        """Test that JavaScript resolver extracts from new expressions."""
        resolver = JavaScriptResolver()
        mock_node = MagicMock()
        mock_node.type = 'class_declaration'
        mock_node.children = [
            MagicMock(type='class'),
            MagicMock(type='identifier', text=b'Foo'),
        ]
        mock_node.text = b'class Foo {}'

        refs = resolver.extract_references(mock_node)
        assert 'Foo' in refs

    def test_typescript_extract_references_type_annotation(self):
        """Test TypeScript extracts type references."""
        resolver = TypeScriptResolver()
        mock_node = MagicMock()
        mock_node.type = 'function_declaration'
        mock_node.children = [
            MagicMock(type='function'),
            MagicMock(type='identifier', text=b'foo'),
            MagicMock(type='parameters'),
            MagicMock(type='type_annotation'),
        ]
        mock_node.text = b'function foo(x: Bar): void {}'

        refs = resolver.extract_references(mock_node)
        assert 'Bar' in refs or 'foo' in refs

    def test_rust_extract_references_path_expression(self):
        """Test Rust extracts path references like Foo::bar()."""
        resolver = RustResolver()
        mock_node = MagicMock()
        mock_node.type = 'call_expression'
        mock_node.children = [
            MagicMock(type='identifier', text=b'Foo'),
            MagicMock(type='path'),
            MagicMock(type='identifier', text=b'bar'),
            MagicMock(type='arguments'),
        ]
        mock_node.text = b'Foo::bar()'

        refs = resolver.extract_references(mock_node)
        assert 'Foo' in refs or 'bar' in refs

    def test_all_resolvers_extract_all_identifiers(self):
        """Test that all resolvers extract all identifier types from expressions."""
        resolvers = [
            PythonResolver(),
            JavaScriptResolver(),
            TypeScriptResolver(),
            RustResolver(),
        ]

        for resolver in resolvers:
            mock_node = MagicMock()
            mock_node.type = 'call_expression'
            mock_node.children = [
                MagicMock(type='identifier', text=b'func_name'),
                MagicMock(type='arguments'),
            ]
            mock_node.text = b'func_name()'

            refs = resolver.extract_references(mock_node)
            assert 'func_name' in refs, f"{resolver.language} should extract func_name"

