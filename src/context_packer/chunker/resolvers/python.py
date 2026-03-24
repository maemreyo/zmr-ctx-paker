from typing import List, Set, Optional

from .base import LanguageResolver


class PythonResolver(LanguageResolver):
    """Resolver for Python language."""

    @property
    def language(self) -> str:
        return 'python'

    @property
    def target_types(self) -> Set[str]:
        return {
            'function_definition', 'class_definition',
            'decorated_definition',
            'type_alias_statement',
        }

    @property
    def file_extensions(self) -> List[str]:
        return ['.py']

    def extract_symbol_name(self, node) -> Optional[str]:
        if node.type == 'function_definition':
            for child in node.children:
                if child.type == 'identifier':
                    return child.text.decode('utf8')
        elif node.type == 'class_definition':
            for child in node.children:
                if child.type == 'identifier':
                    return child.text.decode('utf8')
        elif node.type == 'decorated_definition':
            for child in node.children:
                if child.type == 'function_definition':
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            return grandchild.text.decode('utf8')
                elif child.type == 'class_definition':
                    for grandchild in child.children:
                        if grandchild.type == 'identifier':
                            return grandchild.text.decode('utf8')
        elif node.type == 'type_alias_statement':
            for child in node.children:
                if child.type == 'identifier':
                    return child.text.decode('utf8')
        return None

    def extract_references(self, node) -> List[str]:
        references: Set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, node, references: Set[str]) -> None:
        if node.type == 'identifier':
            references.add(node.text.decode('utf8'))
        for child in node.children:
            self._collect_references(child, references)
