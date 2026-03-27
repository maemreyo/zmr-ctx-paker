from __future__ import annotations

from typing import Any

from .base import LanguageResolver


class TypeScriptResolver(LanguageResolver):
    """Resolver for TypeScript language."""

    @property
    def language(self) -> str:
        return "typescript"

    @property
    def target_types(self) -> set[str]:
        return {
            "function_declaration",
            "class_declaration",
            "method_definition",
            "interface_declaration",
            "type_alias_declaration",
            "enum_declaration",
            "abstract_class_declaration",
            "lexical_declaration",
            "jsx_element",
            "jsx_self_closing_element",
            "export_statement",
            "internal_module",
        }

    @property
    def file_extensions(self) -> list[str]:
        return [".ts", ".tsx"]

    def extract_symbol_name(self, node: Any) -> str | None:
        if node.type in (
            "function_declaration",
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "type_alias_declaration",
            "abstract_class_declaration",
        ):
            for child in node.children:
                if child.type in ("identifier", "type_identifier"):
                    return str(child.text.decode("utf8"))
        elif node.type == "method_definition":
            for child in node.children:
                if child.type == "property_identifier":
                    return str(child.text.decode("utf8"))
        elif node.type == "lexical_declaration":
            return self._extract_arrow_or_var(node)
        elif node.type in ("jsx_element", "jsx_self_closing_element"):
            for child in node.children:
                if child.type in ("jsx_identifier", "jsx_closing_element"):
                    for c in child.children:
                        if c.type == "jsx_identifier":
                            return str(c.text.decode("utf8"))
                if child.type == "jsx_identifier":
                    return str(child.text.decode("utf8"))
        elif node.type == "export_statement":
            for child in node.children:
                if child.type in (
                    "function_declaration",
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                    "type_alias_declaration",
                    "abstract_class_declaration",
                ):
                    for grandchild in child.children:
                        if grandchild.type in ("identifier", "type_identifier"):
                            return str(grandchild.text.decode("utf8"))
        elif node.type == "internal_module":
            for child in node.children:
                if child.type == "identifier":
                    return str(child.text.decode("utf8"))
        return None

    def _extract_arrow_or_var(self, node: Any) -> str | None:
        for child in node.children:
            if child.type == "variable_declarator":
                identifier = None
                has_arrow = False
                for subchild in child.children:
                    if subchild.type == "identifier":
                        identifier = str(subchild.text.decode("utf8"))
                    elif subchild.type == "arrow_function":
                        has_arrow = True
                if identifier and has_arrow:
                    return identifier
        return None

    def extract_all_symbols(self, node: Any) -> list[str]:
        """Return primary symbol plus method names from class body."""
        primary = self.extract_symbol_name(node)
        symbols: list[str] = [primary] if primary else []
        if node.type in ("class_declaration", "abstract_class_declaration"):
            for child in node.children:
                if child.type == "class_body":
                    for item in child.children:
                        if item.type == "method_definition":
                            name = self.extract_symbol_name(item)
                            if name and name not in symbols:
                                symbols.append(name)
        return symbols

    def extract_references(self, node: Any) -> list[str]:
        references: set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, root: Any, references: set[str]) -> None:
        """Collect only cross-file references: call targets and type annotations."""
        stack = [root]
        while stack:
            node = stack.pop()
            if node.type == "call_expression":
                func = node.children[0] if node.children else None
                if func is not None:
                    if func.type == "identifier":
                        references.add(func.text.decode("utf8"))
                    elif func.type == "member_expression":
                        obj = next(
                            (c for c in func.children if c.type == "identifier"), None
                        )
                        if obj:
                            references.add(obj.text.decode("utf8"))
            elif node.type == "type_identifier":
                references.add(node.text.decode("utf8"))
            elif node.type == "extends_clause":
                for child in node.children:
                    if child.type in ("identifier", "type_identifier"):
                        references.add(child.text.decode("utf8"))
            stack.extend(reversed(node.children))
