"""
Custom exceptions for ws-ctx-engine with actionable suggestions.

Provides structured error handling with helpful suggestions for users.
"""

from typing import Any


class WsCtxEngineError(Exception):
    """
    Base exception for ws-ctx-engine with actionable suggestions.

    All ws-ctx-engine exceptions should inherit from this class and provide
    both an error message and a suggestion for how to fix the issue.
    """

    def __init__(self, message: str, suggestion: str):
        """
        Initialize error with message and suggestion.

        Args:
            message: Description of what went wrong
            suggestion: Actionable suggestion for fixing the issue
        """
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"{message}\n\nSuggestion: {suggestion}")


class DependencyError(WsCtxEngineError):
    """
    Raised when a required dependency is missing.

    Provides installation instructions for the missing dependency.
    """

    @classmethod
    def missing_backend(cls, backend: str, install_cmd: str) -> "DependencyError":
        """
        Create error for missing backend dependency.

        Args:
            backend: Name of the missing backend
            install_cmd: Command to install the backend

        Returns:
            DependencyError instance with installation instructions

        Example:
            >>> raise DependencyError.missing_backend(
            ...     backend="igraph",
            ...     install_cmd="pip install python-igraph"
            ... )
        """
        return cls(
            message=f"Backend '{backend}' is not available",
            suggestion=f"Install with: {install_cmd}",
        )

    @classmethod
    def missing_optional_dependency(
        cls, package: str, feature: str, install_cmd: str
    ) -> "DependencyError":
        """
        Create error for missing optional dependency.

        Args:
            package: Name of the missing package
            feature: Feature that requires the package
            install_cmd: Command to install the package

        Returns:
            DependencyError instance with installation instructions

        Example:
            >>> raise DependencyError.missing_optional_dependency(
            ...     package="sentence-transformers",
            ...     feature="local embeddings",
            ...     install_cmd="pip install sentence-transformers"
            ... )
        """
        return cls(
            message=f"Package '{package}' is required for {feature}",
            suggestion=f"Install with: {install_cmd}",
        )


class ConfigurationError(WsCtxEngineError):
    """
    Raised when configuration is invalid.

    Provides guidance on how to fix the configuration.
    """

    @classmethod
    def invalid_value(cls, field: str, value: Any, expected: str) -> "ConfigurationError":
        """
        Create error for invalid configuration value.

        Args:
            field: Name of the configuration field
            value: Invalid value that was provided
            expected: Description of expected value

        Returns:
            ConfigurationError instance with fix instructions

        Example:
            >>> raise ConfigurationError.invalid_value(
            ...     field="semantic_weight",
            ...     value=1.5,
            ...     expected="a float between 0.0 and 1.0"
            ... )
        """
        return cls(
            message=f"Invalid {field}: {value} (expected {expected})",
            suggestion=f"Update .ws-ctx-engine.yaml with valid {field} value",
        )

    @classmethod
    def missing_file(cls, path: str) -> "ConfigurationError":
        """
        Create error for missing configuration file.

        Args:
            path: Path to the missing configuration file

        Returns:
            ConfigurationError instance with creation instructions

        Example:
            >>> raise ConfigurationError.missing_file(
            ...     path=".ws-ctx-engine.yaml"
            ... )
        """
        return cls(
            message=f"Configuration file not found: {path}",
            suggestion="Create .ws-ctx-engine.yaml or use default configuration",
        )

    @classmethod
    def invalid_format(cls, format_value: str) -> "ConfigurationError":
        """
        Create error for invalid output format.

        Args:
            format_value: Invalid format value

        Returns:
            ConfigurationError instance with valid options

        Example:
            >>> raise ConfigurationError.invalid_format(format_value="json")
        """
        return cls(
            message=f"Invalid output format: {format_value}",
            suggestion="Use 'xml' or 'zip' in .ws-ctx-engine.yaml",
        )


class ParsingError(WsCtxEngineError):
    """
    Raised when source code parsing fails.

    Provides guidance on how to handle parsing failures.
    """

    @classmethod
    def syntax_error(cls, file_path: str, line: int, error: str) -> "ParsingError":
        """
        Create error for syntax error in source file.

        Args:
            file_path: Path to the file with syntax error
            line: Line number where error occurred
            error: Description of the syntax error

        Returns:
            ParsingError instance with fix instructions

        Example:
            >>> raise ParsingError.syntax_error(
            ...     file_path="src/main.py",
            ...     line=42,
            ...     error="unexpected EOF"
            ... )
        """
        return cls(
            message=f"Syntax error in {file_path} at line {line}: {error}",
            suggestion="Fix the syntax error or exclude the file using exclude_patterns",
        )

    @classmethod
    def unsupported_language(cls, file_path: str, language: str) -> "ParsingError":
        """
        Create error for unsupported programming language.

        Args:
            file_path: Path to the file
            language: Unsupported language

        Returns:
            ParsingError instance with supported languages

        Example:
            >>> raise ParsingError.unsupported_language(
            ...     file_path="src/main.rb",
            ...     language="ruby"
            ... )
        """
        return cls(
            message=f"Unsupported language '{language}' in {file_path}",
            suggestion="Supported languages: Python, JavaScript, TypeScript, Java, Go, Rust, C, C++",
        )


class IndexError(WsCtxEngineError):
    """
    Raised when index operations fail.

    Provides guidance on how to rebuild or fix indexes.
    """

    @classmethod
    def corrupted_index(cls, index_path: str) -> "IndexError":
        """
        Create error for corrupted index file.

        Args:
            index_path: Path to the corrupted index

        Returns:
            IndexError instance with rebuild instructions

        Example:
            >>> raise IndexError.corrupted_index(
            ...     index_path=".ws-ctx-engine/vector.idx"
            ... )
        """
        return cls(
            message=f"Index file is corrupted: {index_path}",
            suggestion="Delete the index and rebuild with 'ws-ctx-engine index <repo_path>'",
        )

    @classmethod
    def stale_index(cls, index_path: str) -> "IndexError":
        """
        Create error for stale index.

        Args:
            index_path: Path to the stale index

        Returns:
            IndexError instance with rebuild instructions

        Example:
            >>> raise IndexError.stale_index(
            ...     index_path=".ws-ctx-engine/vector.idx"
            ... )
        """
        return cls(
            message=f"Index is stale: {index_path}",
            suggestion="Rebuild the index with 'ws-ctx-engine index <repo_path>'",
        )


class BudgetError(WsCtxEngineError):
    """
    Raised when token budget operations fail.

    Provides guidance on how to adjust budget or file selection.
    """

    @classmethod
    def budget_exceeded(cls, required: int, available: int) -> "BudgetError":
        """
        Create error for budget exceeded.

        Args:
            required: Required token count
            available: Available token budget

        Returns:
            BudgetError instance with adjustment instructions

        Example:
            >>> raise BudgetError.budget_exceeded(
            ...     required=150000,
            ...     available=100000
            ... )
        """
        return cls(
            message=f"Token budget exceeded: required {required}, available {available}",
            suggestion="Increase token_budget in .ws-ctx-engine.yaml or reduce file selection",
        )

    @classmethod
    def no_files_fit(cls, budget: int, smallest_file_size: int) -> "BudgetError":
        """
        Create error when no files fit in budget.

        Args:
            budget: Token budget
            smallest_file_size: Size of smallest file in tokens

        Returns:
            BudgetError instance with adjustment instructions

        Example:
            >>> raise BudgetError.no_files_fit(
            ...     budget=1000,
            ...     smallest_file_size=5000
            ... )
        """
        return cls(
            message=f"No files fit in budget: budget={budget}, smallest_file={smallest_file_size}",
            suggestion="Increase token_budget in .ws-ctx-engine.yaml",
        )
