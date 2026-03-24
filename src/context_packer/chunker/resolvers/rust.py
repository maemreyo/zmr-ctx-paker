from typing import List, Set, Optional

from .base import LanguageResolver


class RustResolver(LanguageResolver):
    """Resolver for Rust language."""

    @property
    def language(self) -> str:
        return 'rust'

    @property
    def target_types(self) -> Set[str]:
        return {
            'function_item', 'struct_item', 'trait_item', 'impl_item',
            'enum_item', 'const_item', 'type_item', 'static_item', 'mod_item',
        }

    @property
    def file_extensions(self) -> List[str]:
        return ['.rs']

    def extract_symbol_name(self, node) -> Optional[str]:
        for child in node.children:
            if child.type == 'identifier':
                return child.text.decode('utf8')
        return None

    def extract_references(self, node) -> List[str]:
        references: Set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, node, references: Set[str]) -> None:
        if node.type in ('use_declaration', 'call_expression'):
            for child in node.children:
                if child.type == 'identifier':
                    references.add(child.text.decode('utf8'))
        for child in node.children:
            self._collect_references(child, references)
