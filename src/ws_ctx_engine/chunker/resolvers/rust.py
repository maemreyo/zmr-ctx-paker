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
        else:
            for child in node.children:
                if child.type == "identifier":
                    return str(child.text.decode("utf8"))
        return None

    def extract_references(self, node: Any) -> list[str]:
        references: set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, node: Any, references: set[str]) -> None:
        if node.type == "identifier":
            references.add(node.text.decode("utf8"))
        for child in node.children:
            self._collect_references(child, references)
