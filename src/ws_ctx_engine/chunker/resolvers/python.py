from __future__ import annotations

from typing import Any

from .base import LanguageResolver


class PythonResolver(LanguageResolver):
    """Resolver for Python language."""

    @property
    def language(self) -> str:
        return "python"

    @property
    def target_types(self) -> set[str]:
        return {
            "function_definition",
            "class_definition",
            "decorated_definition",
            "type_alias_statement",
        }

    @property
    def file_extensions(self) -> list[str]:
        return [".py"]

    def extract_symbol_name(self, node: Any) -> str | None:
        if node.type == "function_definition":
            for child in node.children:
                if child.type == "identifier":
                    return str(child.text.decode("utf8"))
        elif node.type == "class_definition":
            for child in node.children:
                if child.type == "identifier":
                    return str(child.text.decode("utf8"))
        elif node.type == "decorated_definition":
            for child in node.children:
                if child.type == "function_definition":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return str(grandchild.text.decode("utf8"))
                elif child.type == "class_definition":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return str(grandchild.text.decode("utf8"))
        elif node.type == "type_alias_statement":
            for child in node.children:
                if child.type == "identifier":
                    return str(child.text.decode("utf8"))
        return None

    def extract_all_symbols(self, node: Any) -> list[str]:
        """Return primary symbol plus method names from class body."""
        primary = self.extract_symbol_name(node)
        symbols: list[str] = [primary] if primary else []
        if node.type == "class_definition":
            for child in node.children:
                if child.type == "block":
                    for item in child.children:
                        item_node = item
                        # Unwrap decorated definitions
                        if item_node.type == "decorated_definition":
                            for sub in item_node.children:
                                if sub.type == "function_definition":
                                    item_node = sub
                                    break
                        if item_node.type == "function_definition":
                            name = self.extract_symbol_name(item_node)
                            if name and name not in symbols:
                                symbols.append(name)
        return symbols

    def extract_references(self, node: Any) -> list[str]:
        references: set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, root: Any, references: set[str]) -> None:
        """Collect only cross-file references: function calls and imports."""
        stack = [root]
        while stack:
            node = stack.pop()
            if node.type in ("import_statement", "import_from_statement"):
                for child in node.children:
                    if child.type == "dotted_name":
                        # import os.path → add "os" (root module)
                        first_id = next(
                            (c for c in child.children if c.type == "identifier"), None
                        )
                        if first_id:
                            references.add(first_id.text.decode("utf8"))
                    elif child.type == "identifier":
                        references.add(child.text.decode("utf8"))
            elif node.type in ("call", "call_expression"):
                # Only inspect the first child (function part, not arguments).
                first = node.children[0] if node.children else None
                if first is not None:
                    if first.type == "identifier":
                        references.add(first.text.decode("utf8"))
                    elif first.type == "attribute":
                        # obj.method() → collect all identifiers in the attribute
                        # chain (e.g. self._query → "self", "_query"; also captures
                        # module.func for cross-file CALLS edges).
                        for child in first.children:
                            if child.type == "identifier":
                                references.add(child.text.decode("utf8"))
            stack.extend(reversed(node.children))
