"""Property-based tests for Budget Manager."""

import os
import tempfile

from hypothesis import given
from hypothesis import strategies as st

from ws_ctx_engine.budget import BudgetManager

# Strategy for generating file content
file_content_strategy = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=10, max_size=1000
)

# Strategy for generating importance scores (0.0 to 1.0)
importance_score_strategy = st.floats(min_value=0.0, max_value=1.0)


def create_temp_files(
    file_data: list[tuple[str, str, float]]
) -> tuple[str, list[tuple[str, float]]]:
    """Create temporary files for testing.

    Args:
        file_data: List of (filename, content, importance_score) tuples

    Returns:
        Tuple of (temp_dir, ranked_files) where ranked_files is
        list of (relative_path, importance_score) tuples
    """
    temp_dir = tempfile.mkdtemp()
    ranked_files = []

    for filename, content, score in file_data:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        ranked_files.append((filename, score))

    return temp_dir, ranked_files


# Feature: ws-ctx-engine, Property 13: Greedy Selection Ordering
@given(
    st.lists(
        st.tuples(
            st.text(
                alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=10
            ),
            file_content_strategy,
            importance_score_strategy,
        ),
        min_size=2,
        max_size=10,
        unique_by=lambda x: x[0],  # Unique filenames
    ),
    st.integers(min_value=1000, max_value=100000),
)
def test_greedy_selection_ordering(file_data, token_budget):
    """**Validates: Requirements 5.2**

    Property 13: For any set of files with importance scores, the Budget_Manager
    SHALL process them in descending order of importance_score during selection.

    This test verifies that files are processed in the correct order by checking
    that if a file is selected, all files with higher importance scores that fit
    in the budget are also selected.
    """
    # Sort by importance score descending (as the system should)
    file_data_sorted = sorted(file_data, key=lambda x: x[2], reverse=True)

    # Create temporary files
    temp_dir, ranked_files = create_temp_files(file_data_sorted)

    try:
        # Create budget manager and select files
        manager = BudgetManager(token_budget=token_budget)
        selected, total_tokens = manager.select_files(ranked_files, temp_dir)

        # Verify: If file at index i is selected, all files at indices < i
        # that would fit should also be selected (greedy ordering property)
        selected_set = set(selected)

        for i, (filename, score) in enumerate(ranked_files):
            if filename in selected_set:
                # All files before this one should be selected (they have higher scores)
                for j in range(i):
                    prev_filename = ranked_files[j][0]
                    # The previous file should be selected (it has higher importance)
                    assert (
                        prev_filename in selected_set
                    ), f"File {prev_filename} (score={ranked_files[j][1]}) should be selected before {filename} (score={score})"
    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# Feature: ws-ctx-engine, Property 14: Budget Enforcement
@given(
    st.lists(
        st.tuples(
            st.text(
                alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=10
            ),
            file_content_strategy,
            importance_score_strategy,
        ),
        min_size=1,
        max_size=20,
        unique_by=lambda x: x[0],
    ),
    st.integers(min_value=100, max_value=50000),
)
def test_budget_enforcement(file_data, token_budget):
    """**Validates: Requirements 5.3, 5.4**

    Property 14: For any file selection, the total tokens of selected files
    SHALL not exceed 80% of the configured Token_Budget.

    This test verifies that the budget manager never exceeds the content budget
    (80% of total budget, with 20% reserved for metadata).
    """
    # Sort by importance score descending
    file_data_sorted = sorted(file_data, key=lambda x: x[2], reverse=True)

    # Create temporary files
    temp_dir, ranked_files = create_temp_files(file_data_sorted)

    try:
        # Create budget manager and select files
        manager = BudgetManager(token_budget=token_budget)
        selected, total_tokens = manager.select_files(ranked_files, temp_dir)

        # Verify: Total tokens must not exceed 80% of budget
        content_budget = int(token_budget * 0.8)
        assert (
            total_tokens <= content_budget
        ), f"Total tokens {total_tokens} exceeds content budget {content_budget} (80% of {token_budget})"

        # Also verify the manager's content_budget attribute is correct
        assert (
            manager.content_budget == content_budget
        ), f"Manager content_budget {manager.content_budget} != expected {content_budget}"
    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# Feature: ws-ctx-engine, Property 15: Budget Manager Output Completeness
@given(
    st.lists(
        st.tuples(
            st.text(
                alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=10
            ),
            file_content_strategy,
            importance_score_strategy,
        ),
        min_size=1,
        max_size=10,
        unique_by=lambda x: x[0],
    ),
    st.integers(min_value=1000, max_value=100000),
)
def test_budget_manager_output_completeness(file_data, token_budget):
    """**Validates: Requirements 5.6**

    Property 15: For any file selection, the Budget_Manager SHALL return both
    the list of selected files and the total token count.

    This test verifies that the output format is correct and complete.
    """
    # Sort by importance score descending
    file_data_sorted = sorted(file_data, key=lambda x: x[2], reverse=True)

    # Create temporary files
    temp_dir, ranked_files = create_temp_files(file_data_sorted)

    try:
        # Create budget manager and select files
        manager = BudgetManager(token_budget=token_budget)
        result = manager.select_files(ranked_files, temp_dir)

        # Verify: Result is a tuple with exactly 2 elements
        assert isinstance(result, tuple), f"Result should be tuple, got {type(result)}"
        assert len(result) == 2, f"Result should have 2 elements, got {len(result)}"

        selected, total_tokens = result

        # Verify: First element is a list of strings (file paths)
        assert isinstance(selected, list), f"Selected should be list, got {type(selected)}"
        for file_path in selected:
            assert isinstance(file_path, str), f"File path should be string, got {type(file_path)}"

        # Verify: Second element is an integer (token count)
        assert isinstance(
            total_tokens, int
        ), f"Total tokens should be int, got {type(total_tokens)}"
        assert total_tokens >= 0, f"Total tokens should be non-negative, got {total_tokens}"
    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# Feature: ws-ctx-engine, Property 16: Greedy Knapsack Optimality
@given(
    st.lists(
        st.tuples(
            st.text(
                alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=10
            ),
            file_content_strategy,
            importance_score_strategy,
        ),
        min_size=3,
        max_size=10,
        unique_by=lambda x: x[0],
    ),
    st.integers(min_value=1000, max_value=50000),
)
def test_greedy_knapsack_optimality(file_data, token_budget):
    """**Validates: Requirements 5.7**

    Property 16: For any file selection result, no single file swap (removing
    one selected file and adding one unselected file) SHALL increase the total
    importance score while staying within the token budget.

    This test verifies the greedy knapsack optimality property: that the
    selection maximizes importance score within the budget constraint.
    """
    # Sort by importance score descending
    file_data_sorted = sorted(file_data, key=lambda x: x[2], reverse=True)

    # Create temporary files
    temp_dir, ranked_files = create_temp_files(file_data_sorted)

    try:
        # Create budget manager and select files
        manager = BudgetManager(token_budget=token_budget)
        selected, total_tokens = manager.select_files(ranked_files, temp_dir)

        # Skip if no files were selected or all files were selected
        # (can't test swapping in these cases)
        if len(selected) == 0 or len(selected) == len(ranked_files):
            return

        # Build mapping of filename -> (content, score, tokens)
        file_info = {}
        for filename, content, score in file_data_sorted:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            tokens = len(manager.encoding.encode(content))
            file_info[filename] = (content, score, tokens)

        # Calculate current total importance score
        selected_set = set(selected)
        current_score = sum(file_info[f][1] for f in selected)

        # Try all possible single-file swaps
        unselected = [f for f, _ in ranked_files if f not in selected_set]

        for selected_file in selected:
            for unselected_file in unselected:
                # Calculate new token count after swap
                new_tokens = (
                    total_tokens - file_info[selected_file][2] + file_info[unselected_file][2]
                )

                # If swap stays within budget
                if new_tokens <= manager.content_budget:
                    # Calculate new importance score
                    new_score = (
                        current_score - file_info[selected_file][1] + file_info[unselected_file][1]
                    )

                    # Verify: No swap should improve the score
                    # (greedy algorithm should have already selected the best files)
                    assert new_score <= current_score, (
                        f"Swap {selected_file} (score={file_info[selected_file][1]}) -> "
                        f"{unselected_file} (score={file_info[unselected_file][1]}) "
                        f"improves score from {current_score} to {new_score}"
                    )
    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
