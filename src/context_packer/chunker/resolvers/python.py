import re
from typing import List, Set, Optional

from .base import LanguageResolver


class PythonResolver(LanguageResolver):
    """Resolver for Python language."""

    @property
    def language(self) -> str:
        return 'python'

    @property
    def target_types(self) -> Set[str]:
        return {'function_definition', 'class_definition', 'expression_statement'}

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
        elif node.type == 'expression_statement':
            return self._extract_constant_name(node, node.text.decode('utf8'))
        return None

    def _extract_constant_name(self, node, raw: str) -> Optional[str]:
        if node.parent is None or node.parent.type != 'module':
            return None
        match = re.match(r'^([A-Z][A-Z0-9_]+)\s*=', raw.strip())
        return match.group(1) if match else None

    def extract_references(self, node) -> List[str]:
        references: Set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, node, references: Set[str]) -> None:
        if node.type in ('import_statement', 'import_from_statement', 'call_expression'):
            for child in node.children:
                if child.type == 'identifier':
                    references.add(child.text.decode('utf8'))
        for child in node.children:
            self._collect_references(child, references)
