"""Budget Manager for token-aware file selection."""

import os

import tiktoken


class BudgetManager:
    """Manages token budget and selects files using greedy knapsack algorithm.

    The BudgetManager implements a greedy knapsack algorithm to select files
    that fit within a token budget while maximizing total importance score.
    It reserves 20% of the budget for metadata and manifest.

    Attributes:
        token_budget: Total token budget for the context
        encoding: tiktoken encoding instance for token counting
        content_budget: 80% of token_budget reserved for file content

    Example:
        >>> import tiktoken
        >>> manager = BudgetManager(token_budget=10000)
        >>> ranked_files = [
        ...     ("src/main.py", 0.95),
        ...     ("src/utils.py", 0.80),
        ...     ("tests/test_main.py", 0.60)
        ... ]
        >>> selected, total = manager.select_files(ranked_files, "/path/to/repo")
        >>> print(f"Selected {len(selected)} files using {total} tokens")
    """

    def __init__(self, token_budget: int, encoding: str = "cl100k_base"):
        """Initialize BudgetManager with token budget and encoding.

        Args:
            token_budget: Total token budget for the context
            encoding: tiktoken encoding name (default: cl100k_base for GPT-4)

        Raises:
            ValueError: If token_budget is not positive
        """
        if token_budget <= 0:
            raise ValueError(f"token_budget must be positive, got {token_budget}")

        self.token_budget = token_budget
        self.encoding = tiktoken.get_encoding(encoding)
        # Reserve 20% for metadata, use 80% for content
        self.content_budget = int(token_budget * 0.8)

    def select_files(
        self, ranked_files: list[tuple[str, float]], repo_path: str
    ) -> tuple[list[str], int]:
        """Select files within budget using greedy knapsack algorithm.

        Implements greedy knapsack: processes files in descending order of
        importance score, accumulating files until the content budget (80%
        of total budget) is reached.

        Args:
            ranked_files: List of (file_path, importance_score) tuples,
                         should be sorted by importance_score descending
            repo_path: Path to repository root for reading file contents

        Returns:
            Tuple of (selected_files, total_tokens) where:
                - selected_files: List of file paths that fit within budget
                - total_tokens: Total token count of selected files

        Example:
            >>> manager = BudgetManager(token_budget=10000)
            >>> ranked = [("a.py", 0.9), ("b.py", 0.8), ("c.py", 0.7)]
            >>> selected, tokens = manager.select_files(ranked, "/repo")
            >>> assert tokens <= manager.content_budget
        """
        selected = []
        total_tokens = 0

        # Process files in order (should already be sorted by importance)
        for file_path, _importance_score in ranked_files:
            full_path = os.path.join(repo_path, file_path)

            # Skip if file doesn't exist
            if not os.path.exists(full_path):
                continue

            # Read file content and count tokens
            try:
                with open(full_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                # Skip files we can't read
                continue

            tokens = len(self.encoding.encode(content))

            # Check if adding this file would exceed budget
            if total_tokens + tokens <= self.content_budget:
                selected.append(file_path)
                total_tokens += tokens
            else:
                # Budget exceeded, stop adding files
                break

        return selected, total_tokens
