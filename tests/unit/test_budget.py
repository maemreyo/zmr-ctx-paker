"""Unit tests for Budget Manager."""

import os
import shutil
import tempfile

import pytest

from ws_ctx_engine.budget import BudgetManager


@pytest.fixture
def temp_repo():
    """Create a temporary repository with test files."""
    temp_dir = tempfile.mkdtemp()

    # Create test files with known content
    files = {
        "small.py": "def hello():\n    print('Hello')\n",  # Small file
        "medium.py": "def process(data):\n    result = []\n    for item in data:\n        result.append(item * 2)\n    return result\n",  # Medium file
        "large.py": "class DataProcessor:\n    def __init__(self):\n        self.data = []\n    \n    def add(self, item):\n        self.data.append(item)\n    \n    def process(self):\n        return [x * 2 for x in self.data]\n    \n    def clear(self):\n        self.data = []\n",  # Large file
    }

    for filename, content in files.items():
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    yield temp_dir, files

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_budget_manager_initialization():
    """Test BudgetManager initialization with valid parameters.

    Requirements: 5.1
    """
    manager = BudgetManager(token_budget=10000)

    assert manager.token_budget == 10000
    assert manager.content_budget == 8000  # 80% of 10000
    assert manager.encoding is not None


def test_budget_manager_invalid_budget():
    """Test BudgetManager raises error for invalid budget.

    Requirements: 5.1
    """
    with pytest.raises(ValueError, match="token_budget must be positive"):
        BudgetManager(token_budget=0)

    with pytest.raises(ValueError, match="token_budget must be positive"):
        BudgetManager(token_budget=-100)


def test_select_files_within_budget(temp_repo):
    """Test selecting files within token budget.

    Requirements: 5.1, 5.2, 5.3, 5.4
    """
    temp_dir, files = temp_repo

    # Create ranked files (sorted by importance descending)
    ranked_files = [
        ("large.py", 0.95),
        ("medium.py", 0.80),
        ("small.py", 0.60),
    ]

    # Set budget that can fit all files
    manager = BudgetManager(token_budget=10000)
    selected, total_tokens = manager.select_files(ranked_files, temp_dir)

    # Verify all files are selected
    assert len(selected) == 3
    assert "large.py" in selected
    assert "medium.py" in selected
    assert "small.py" in selected

    # Verify total tokens is within budget
    assert total_tokens <= manager.content_budget
    assert total_tokens > 0


def test_select_files_exceeds_budget(temp_repo):
    """Test selecting files when budget is exceeded.

    Requirements: 5.2, 5.3, 5.4
    """
    temp_dir, files = temp_repo

    # Create ranked files (sorted by importance descending)
    ranked_files = [
        ("large.py", 0.95),
        ("medium.py", 0.80),
        ("small.py", 0.60),
    ]

    # Set very small budget that can only fit one file
    manager = BudgetManager(token_budget=100)
    selected, total_tokens = manager.select_files(ranked_files, temp_dir)

    # Verify only highest importance file(s) are selected
    assert len(selected) >= 1
    assert "large.py" in selected  # Highest importance should be selected

    # Verify total tokens is within budget
    assert total_tokens <= manager.content_budget


def test_greedy_selection_maximizes_importance(temp_repo):
    """Test greedy selection maximizes importance score.

    Requirements: 5.2, 5.7
    """
    temp_dir, files = temp_repo

    # Create ranked files (sorted by importance descending)
    ranked_files = [
        ("large.py", 0.95),
        ("medium.py", 0.80),
        ("small.py", 0.60),
    ]

    manager = BudgetManager(token_budget=1000)
    selected, total_tokens = manager.select_files(ranked_files, temp_dir)

    # Verify files are selected in order of importance
    # If a file is selected, all higher-importance files should be selected
    selected_indices = [i for i, (f, _) in enumerate(ranked_files) if f in selected]

    if selected_indices:
        # All indices from 0 to max selected index should be selected
        max_index = max(selected_indices)
        for i in range(max_index + 1):
            filename = ranked_files[i][0]
            # Check if this file would fit in budget
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            len(manager.encoding.encode(content))

            # If we're checking a file before the last selected one,
            # it should definitely be selected
            if i < max_index:
                assert (
                    filename in selected
                ), f"File {filename} at index {i} should be selected before index {max_index}"


def test_reserve_20_percent_for_metadata():
    """Test reserving 20% of budget for metadata.

    Requirements: 5.4
    """
    token_budget = 10000
    manager = BudgetManager(token_budget=token_budget)

    # Verify content budget is 80% of total
    expected_content_budget = int(token_budget * 0.8)
    assert manager.content_budget == expected_content_budget

    # Verify 20% is reserved (not used for content)
    reserved = token_budget - manager.content_budget
    assert reserved == int(token_budget * 0.2)


def test_token_counting_accuracy(temp_repo):
    """Test token counting accuracy within ±2%.

    Requirements: 5.1, 5.5
    """
    temp_dir, files = temp_repo

    # Create ranked files
    ranked_files = [
        ("small.py", 0.9),
    ]

    manager = BudgetManager(token_budget=10000)
    selected, total_tokens = manager.select_files(ranked_files, temp_dir)

    # Manually count tokens for verification
    file_path = os.path.join(temp_dir, "small.py")
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    expected_tokens = len(manager.encoding.encode(content))

    # Verify token count matches (should be exact since we're using same encoding)
    assert total_tokens == expected_tokens

    # Verify accuracy is within ±2% (should be exact, but test the requirement)
    tolerance = expected_tokens * 0.02
    assert abs(total_tokens - expected_tokens) <= tolerance


def test_select_files_with_missing_file(temp_repo):
    """Test handling of missing files gracefully.

    Requirements: 5.2
    """
    temp_dir, files = temp_repo

    # Include a non-existent file in ranked list
    ranked_files = [
        ("large.py", 0.95),
        ("nonexistent.py", 0.90),  # This file doesn't exist
        ("medium.py", 0.80),
    ]

    manager = BudgetManager(token_budget=10000)
    selected, total_tokens = manager.select_files(ranked_files, temp_dir)

    # Verify missing file is skipped
    assert "nonexistent.py" not in selected

    # Verify other files are still selected
    assert "large.py" in selected
    assert "medium.py" in selected


def test_select_files_empty_list():
    """Test selecting files from empty list.

    Requirements: 5.6
    """
    manager = BudgetManager(token_budget=10000)
    selected, total_tokens = manager.select_files([], "/tmp")

    # Verify empty result
    assert selected == []
    assert total_tokens == 0


def test_output_format(temp_repo):
    """Test output format includes file list and token count.

    Requirements: 5.6
    """
    temp_dir, files = temp_repo

    ranked_files = [
        ("small.py", 0.9),
    ]

    manager = BudgetManager(token_budget=10000)
    result = manager.select_files(ranked_files, temp_dir)

    # Verify result is a tuple with 2 elements
    assert isinstance(result, tuple)
    assert len(result) == 2

    selected, total_tokens = result

    # Verify types
    assert isinstance(selected, list)
    assert isinstance(total_tokens, int)

    # Verify content
    assert len(selected) > 0
    assert total_tokens > 0


def test_different_encodings():
    """Test BudgetManager with different tiktoken encodings.

    Requirements: 5.1
    """
    # Test with cl100k_base (default, GPT-4)
    manager1 = BudgetManager(token_budget=10000, encoding="cl100k_base")
    assert manager1.encoding is not None

    # Test with p50k_base (GPT-3)
    manager2 = BudgetManager(token_budget=10000, encoding="p50k_base")
    assert manager2.encoding is not None

    # Both should work
    assert manager1.content_budget == manager2.content_budget == 8000
