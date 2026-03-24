from typing import List, Set, Optional

from .base import LanguageResolver


class TypeScriptResolver(LanguageResolver):
    """Resolver for TypeScript language."""

    @property
    def language(self) -> str:
        return 'typescript'

    @property
    def target_types(self) -> Set[str]:
        return {
            'function_declaration', 'class_declaration', 'method_definition',
            'interface_declaration', 'type_alias_declaration', 'enum_declaration',
            'abstract_class_declaration', 'lexical_declaration',
        }

    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx']

    def extract_symbol_name(self, node) -> Optional[str]:
        if node.type in ('function_declaration', 'class_declaration',
                         'interface_declaration', 'enum_declaration',
                         'type_alias_declaration', 'abstract_class_declaration'):
            for child in node.children:
                if child.type == 'identifier':
                    return child.text.decode('utf8')
        elif node.type == 'method_definition':
            for child in node.children:
                if child.type == 'property_identifier':
                    return child.text.decode('utf8')
        elif node.type == 'lexical_declaration':
            return self._extract_arrow_or_var(node)
        return None

    def _extract_arrow_or_var(self, node) -> Optional[str]:
        for child in node.children:
            if child.type == 'variable_declarator':
                identifier = None
                has_arrow = False
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        identifier = subchild.text.decode('utf8')
                    elif subchild.type == 'arrow_function':
                        has_arrow = True
                if identifier and has_arrow:
                    return identifier
        return None

    def extract_references(self, node) -> List[str]:
        references: Set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, node, references: Set[str]) -> None:
        if node.type in ('import_statement', 'call_expression'):
            for child in node.children:
                if child.type == 'identifier':
                    references.add(child.text.decode('utf8'))
        for child in node.children:
            self._collect_references(child, references)
