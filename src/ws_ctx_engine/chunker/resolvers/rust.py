from __future__ import annotations

from typing import Any

from .base import LanguageResolver


class RustResolver(LanguageResolver):
    """Resolver for Rust language."""

    @property
    def language(self) -> str:
        return "rust"

    @property
    def target_types(self) -> set[str]:
        return {
            "function_item",
            "struct_item",
            "trait_item",
            "impl_item",
            "enum_item",
            "const_item",
            "type_item",
            "static_item",
            "mod_item",
            "macro_definition",
            "union_item",
            "function_signature_item",
        }

    @property
    def file_extensions(self) -> list[str]:
        return [".rs"]

    def extract_symbol_name(self, node: Any) -> str | None:
        if node.type == "impl_item":
            for child in node.children:
                if child.type in ("type_identifier", "identifier"):
                    return str(child.text.decode("utf8"))
        elif node.type in (
            "struct_item",
            "trait_item",
            "enum_item",
            "type_item",
            "union_item",
        ):
            for child in node.children:
                if child.type in ("type_identifier", "identifier"):
                    return str(child.text.decode("utf8"))
        else:
            for child in node.children:
                if child.type == "identifier":
                    return str(child.text.decode("utf8"))
        return None

    def extract_all_symbols(self, node: Any) -> list[str]:
        """Return primary symbol plus method/function names from body."""
        primary = self.extract_symbol_name(node)
        symbols: list[str] = [primary] if primary else []
        body_types = {
            "impl_item": "declaration_list",
            "trait_item": "declaration_list",
        }
        body_container = body_types.get(node.type)
        if body_container:
            for child in node.children:
                if child.type == body_container:
                    for item in child.children:
                        if item.type in ("function_item", "function_signature_item"):
                            name = self.extract_symbol_name(item)
                            if name and name not in symbols:
                                symbols.append(name)
        return symbols

    def extract_references(self, node: Any) -> list[str]:
        references: set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, root: Any, references: set[str]) -> None:
        """Collect only cross-file references: call targets, type names, imports."""
        stack = [root]
        while stack:
            node = stack.pop()
            if node.type == "use_declaration":
                for child in node.children:
                    if child.type == "identifier":
                        references.add(child.text.decode("utf8"))
                    elif child.type == "scoped_identifier":
                        parts = child.text.decode("utf8").split("::")
                        if parts[0]:
                            references.add(parts[0])
            elif node.type == "call_expression":
                func = node.children[0] if node.children else None
                if func is not None:
                    if func.type == "identifier":
                        references.add(func.text.decode("utf8"))
                    elif func.type == "scoped_identifier":
                        # e.g. helper::transform → collect "helper"
                        parts = func.text.decode("utf8").split("::")
                        if parts[0]:
                            references.add(parts[0])
                    elif func.type == "field_expression":
                        # e.g. self.method() or obj.method()
                        obj = next(
                            (c for c in func.children if c.type == "identifier"), None
                        )
                        if obj:
                            references.add(obj.text.decode("utf8"))
            elif node.type == "macro_invocation":
                macro_name = next(
                    (c for c in node.children if c.type == "identifier"), None
                )
                if macro_name:
                    references.add(macro_name.text.decode("utf8"))
            elif node.type == "type_identifier":
                references.add(node.text.decode("utf8"))
            stack.extend(reversed(node.children))
