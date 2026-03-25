"""
Property-based tests for Retrieval Engine.

Tests universal properties that should hold for all retrieval operations.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from ws_ctx_engine.retrieval import RetrievalEngine
from ws_ctx_engine.vector_index import VectorIndex
from ws_ctx_engine.graph import RepoMapGraph
from ws_ctx_engine.models import CodeChunk


# Mock implementations for testing
class MockVectorIndex(VectorIndex):
    """Mock VectorIndex for testing."""
    
    def __init__(self):
        self.search_results = {}
    
    def build(self, chunks):
        pass
    
    def search(self, query, top_k=10):
        return list(self.search_results.items())[:top_k]
    
    def save(self, path):
        pass
    
    @classmethod
    def load(cls, path):
        return cls()
    
    def set_search_results(self, results):
        """Set mock search results."""
        self.search_results = results


class MockRepoMapGraph(RepoMapGraph):
    """Mock RepoMapGraph for testing."""
    
    def __init__(self):
        self.pagerank_scores = {}
    
    def build(self, chunks):
        pass
    
    def pagerank(self, changed_files=None):
        return self.pagerank_scores.copy()
    
    def save(self, path):
        pass
    
    @classmethod
    def load(cls, path):
        return cls()
    
    def set_pagerank_scores(self, scores):
        """Set mock PageRank scores."""
        self.pagerank_scores = scores


# Strategies for generating test data
@st.composite
def file_scores_strategy(draw):
    """Generate a dictionary of file paths to scores."""
    num_files = draw(st.integers(min_value=1, max_value=20))
    
    files = [
        f"src/file_{i}.py"
        for i in range(num_files)
    ]
    
    scores = {
        file: draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
        for file in files
    }
    
    return scores


@st.composite
def weights_strategy(draw):
    """Generate valid weight pairs that sum to 1.0."""
    semantic_weight = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    pagerank_weight = 1.0 - semantic_weight
    
    return semantic_weight, pagerank_weight


# Property 9: Score Merging Correctness
# Validates: Requirements 4.1, 4.3, 4.4
@pytest.mark.property
@given(
    semantic_scores=file_scores_strategy(),
    pagerank_scores=file_scores_strategy(),
    weights=weights_strategy()
)
@settings(max_examples=100, deadline=None)
def test_property_score_merging_correctness(semantic_scores, pagerank_scores, weights):
    """
    Property 9: Score Merging Correctness
    
    For any semantic scores and PageRank scores with weights (w1, w2), the merged
    importance score SHALL equal w1 * normalized_semantic + w2 * normalized_pagerank
    where both score types are normalized to [0, 1].
    
    Validates: Requirements 4.1, 4.3, 4.4
    """
    semantic_weight, pagerank_weight = weights
    
    # Create mock components
    vector_index = MockVectorIndex()
    graph = MockRepoMapGraph()
    
    # Set mock data
    vector_index.set_search_results(semantic_scores)
    graph.set_pagerank_scores(pagerank_scores)
    
    # Create retrieval engine
    engine = RetrievalEngine(
        vector_index=vector_index,
        graph=graph,
        semantic_weight=semantic_weight,
        pagerank_weight=pagerank_weight
    )
    
    # Normalize scores manually
    semantic_normalized = engine._normalize(semantic_scores)
    pagerank_normalized = engine._normalize(pagerank_scores)
    
    # Merge scores
    merged = engine._merge_scores(semantic_normalized, pagerank_normalized)
    
    # Verify merged scores equal weighted sum
    all_files = set(semantic_scores.keys()) | set(pagerank_scores.keys())
    
    for file in all_files:
        semantic_score = semantic_normalized.get(file, 0.0)
        pagerank_score = pagerank_normalized.get(file, 0.0)
        
        expected_score = (
            semantic_weight * semantic_score +
            pagerank_weight * pagerank_score
        )
        
        actual_score = merged[file]
        
        # Allow small floating-point error
        assert abs(actual_score - expected_score) < 1e-9, \
            f"Score mismatch for {file}: expected {expected_score}, got {actual_score}"


# Property 10: Score Normalization Range
# Validates: Requirements 4.4
@pytest.mark.property
@given(scores=file_scores_strategy())
@settings(max_examples=100, deadline=None)
def test_property_score_normalization_range(scores):
    """
    Property 10: Score Normalization Range
    
    For any set of scores after normalization, all values SHALL be in the range [0, 1].
    
    Validates: Requirements 4.4
    """
    # Create mock components
    vector_index = MockVectorIndex()
    graph = MockRepoMapGraph()
    
    # Create retrieval engine
    engine = RetrievalEngine(
        vector_index=vector_index,
        graph=graph
    )
    
    # Normalize scores
    normalized = engine._normalize(scores)
    
    # Verify all normalized scores are in [0, 1]
    for file, score in normalized.items():
        assert 0.0 <= score <= 1.0, \
            f"Normalized score for {file} is out of range: {score}"
    
    # If there are scores, verify at least one is 0.0 and one is 1.0
    # (unless all scores are equal)
    if len(normalized) > 0:
        values = list(normalized.values())
        min_val = min(values)
        max_val = max(values)
        
        # Check that min is 0.0 and max is 1.0 (unless all equal)
        if len(set(values)) > 1:
            assert abs(min_val - 0.0) < 1e-9, f"Min normalized score should be 0.0, got {min_val}"
            assert abs(max_val - 1.0) < 1e-9, f"Max normalized score should be 1.0, got {max_val}"
        else:
            # All scores equal, should all be 1.0
            assert all(abs(v - 1.0) < 1e-9 for v in values), \
                "All equal scores should normalize to 1.0"


# Property 11: Retrieval Output Format
# Validates: Requirements 4.5
@pytest.mark.property
@given(
    semantic_scores=file_scores_strategy(),
    pagerank_scores=file_scores_strategy(),
    top_k=st.integers(min_value=1, max_value=50)
)
@settings(max_examples=100, deadline=None)
def test_property_retrieval_output_format(semantic_scores, pagerank_scores, top_k):
    """
    Property 11: Retrieval Output Format
    
    For any retrieval operation, the output SHALL be a list of (file_path, importance_score)
    tuples sorted by importance_score in descending order.
    
    Validates: Requirements 4.5
    """
    # Create mock components
    vector_index = MockVectorIndex()
    graph = MockRepoMapGraph()
    
    # Set mock data
    vector_index.set_search_results(semantic_scores)
    graph.set_pagerank_scores(pagerank_scores)
    
    # Create retrieval engine
    engine = RetrievalEngine(
        vector_index=vector_index,
        graph=graph
    )
    
    # Retrieve with query
    results = engine.retrieve(
        query="test query",
        changed_files=None,
        top_k=top_k
    )
    
    # Verify output is a list
    assert isinstance(results, list), "Output should be a list"
    
    # Verify each element is a tuple of (str, float)
    for item in results:
        assert isinstance(item, tuple), f"Each item should be a tuple, got {type(item)}"
        assert len(item) == 2, f"Each tuple should have 2 elements, got {len(item)}"
        
        file_path, score = item
        assert isinstance(file_path, str), f"File path should be str, got {type(file_path)}"
        assert isinstance(score, (int, float)), f"Score should be numeric, got {type(score)}"
    
    # Verify results are sorted by score descending
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True), \
        "Results should be sorted by score in descending order"
    
    # Verify length is at most top_k
    assert len(results) <= top_k, \
        f"Results length {len(results)} exceeds top_k {top_k}"
    
    # Verify all scores are in valid range [0, 1]
    for file_path, score in results:
        assert 0.0 <= score <= 1.0, \
            f"Score for {file_path} is out of range: {score}"


# Additional property: Weights validation
@pytest.mark.property
@given(
    semantic_weight=st.floats(min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    pagerank_weight=st.floats(min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_property_weights_validation(semantic_weight, pagerank_weight):
    """
    Test that invalid weights are rejected.
    
    Weights must be in [0, 1] and sum to 1.0.
    """
    vector_index = MockVectorIndex()
    graph = MockRepoMapGraph()
    
    # Check if weights are valid
    weights_valid = (
        0 <= semantic_weight <= 1 and
        0 <= pagerank_weight <= 1 and
        abs(semantic_weight + pagerank_weight - 1.0) < 0.001
    )
    
    if weights_valid:
        # Should succeed
        engine = RetrievalEngine(
            vector_index=vector_index,
            graph=graph,
            semantic_weight=semantic_weight,
            pagerank_weight=pagerank_weight
        )
        assert engine.semantic_weight == semantic_weight
        assert engine.pagerank_weight == pagerank_weight
    else:
        # Should raise ValueError
        with pytest.raises(ValueError):
            RetrievalEngine(
                vector_index=vector_index,
                graph=graph,
                semantic_weight=semantic_weight,
                pagerank_weight=pagerank_weight
            )
