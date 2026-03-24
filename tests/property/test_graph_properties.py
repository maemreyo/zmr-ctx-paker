"""
Property-based tests for RepoMap Graph.

Tests universal properties that should hold for all graph implementations.
"""

import pytest
from hypothesis import given, strategies as st, settings

from context_packer.graph import create_graph, IGraphRepoMap, NetworkXRepoMap
from context_packer.models import CodeChunk


# Strategy for generating valid CodeChunks
@st.composite
def code_chunk_strategy(draw):
    """Generate a valid CodeChunk for testing."""
    path = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='/_.-'
    )))
    
    # Ensure path looks like a file path
    if not path.endswith('.py'):
        path = path + '.py'
    
    start_line = draw(st.integers(min_value=1, max_value=100))
    end_line = draw(st.integers(min_value=start_line, max_value=start_line + 50))
    
    content = draw(st.text(min_size=0, max_size=200))
    
    # Generate symbols (identifiers)
    symbols_defined = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_'
        )),
        min_size=0,
        max_size=5,
        unique=True
    ))
    
    symbols_referenced = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_'
        )),
        min_size=0,
        max_size=5,
        unique=True
    ))
    
    language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
    
    return CodeChunk(
        path=path,
        start_line=start_line,
        end_line=end_line,
        content=content,
        symbols_defined=symbols_defined,
        symbols_referenced=symbols_referenced,
        language=language
    )


# Property 6: Dependency Graph Construction
# Validates: Requirements 3.1
@pytest.mark.property
@given(chunks=st.lists(code_chunk_strategy(), min_size=1, max_size=20))
@settings(max_examples=50, deadline=None)
def test_property_dependency_graph_construction_networkx(chunks):
    """
    Property 6: Dependency Graph Construction
    
    For any set of Code_Chunks with symbol references, the RepoMap_Graph SHALL
    build a directed dependency graph where edges represent symbol dependencies.
    
    Validates: Requirements 3.1
    """
    # Skip if networkx not available
    pytest.importorskip("networkx")
    
    # Create graph with NetworkX backend
    graph = NetworkXRepoMap()
    
    # Build should not raise an exception
    graph.build(chunks)
    
    # Graph should be created
    assert graph.graph is not None
    
    # All unique file paths should be nodes in the graph
    unique_files = set(chunk.path for chunk in chunks)
    assert len(graph.graph.nodes) == len(unique_files)
    
    for file in unique_files:
        assert file in graph.graph.nodes
    
    # Build symbol definition map
    symbol_to_file = {}
    for chunk in chunks:
        for symbol in chunk.symbols_defined:
            symbol_to_file[symbol] = chunk.path
    
    # Verify edges represent symbol dependencies
    for chunk in chunks:
        source_file = chunk.path
        
        for symbol in chunk.symbols_referenced:
            if symbol in symbol_to_file:
                target_file = symbol_to_file[symbol]
                
                # If source != target, there should be an edge
                if source_file != target_file:
                    # Edge should exist (may have multiple edges, so check if path exists)
                    assert graph.graph.has_edge(source_file, target_file), \
                        f"Expected edge {source_file} -> {target_file} for symbol {symbol}"


@pytest.mark.property
@given(chunks=st.lists(code_chunk_strategy(), min_size=1, max_size=20))
@settings(max_examples=50, deadline=None)
def test_property_dependency_graph_construction_igraph(chunks):
    """
    Property 6: Dependency Graph Construction (igraph backend)
    
    For any set of Code_Chunks with symbol references, the RepoMap_Graph SHALL
    build a directed dependency graph where edges represent symbol dependencies.
    
    Validates: Requirements 3.1
    """
    # Skip if igraph not available
    pytest.importorskip("igraph")
    
    # Create graph with igraph backend
    graph = IGraphRepoMap()
    
    # Build should not raise an exception
    graph.build(chunks)
    
    # Graph should be created
    assert graph.graph is not None
    
    # All unique file paths should be nodes in the graph
    unique_files = set(chunk.path for chunk in chunks)
    assert graph.graph.vcount() == len(unique_files)
    
    # Verify all files are in the mapping
    for file in unique_files:
        assert file in graph.file_to_vertex
    
    # Build symbol definition map
    symbol_to_file = {}
    for chunk in chunks:
        for symbol in chunk.symbols_defined:
            symbol_to_file[symbol] = chunk.path
    
    # Verify edges represent symbol dependencies
    for chunk in chunks:
        source_file = chunk.path
        source_vertex = graph.file_to_vertex[source_file]
        
        for symbol in chunk.symbols_referenced:
            if symbol in symbol_to_file:
                target_file = symbol_to_file[symbol]
                target_vertex = graph.file_to_vertex[target_file]
                
                # If source != target, there should be an edge
                if source_file != target_file:
                    # Check if edge exists
                    edge_ids = graph.graph.get_eid(source_vertex, target_vertex, error=False)
                    assert edge_ids != -1, \
                        f"Expected edge {source_file} -> {target_file} for symbol {symbol}"



# Property 7: PageRank Score Validity
# Validates: Requirements 3.2
@pytest.mark.property
@given(chunks=st.lists(code_chunk_strategy(), min_size=1, max_size=20))
@settings(max_examples=50, deadline=None)
def test_property_pagerank_score_validity_networkx(chunks):
    """
    Property 7: PageRank Score Validity
    
    For any built RepoMap_Graph, the computed PageRank scores SHALL sum to 1.0
    (within floating-point tolerance of ±0.001).
    
    Validates: Requirements 3.2
    """
    # Skip if networkx not available
    pytest.importorskip("networkx")
    
    # Create and build graph
    graph = NetworkXRepoMap()
    graph.build(chunks)
    
    # Compute PageRank scores
    scores = graph.pagerank()
    
    # Scores should not be empty
    assert len(scores) > 0
    
    # All scores should be non-negative
    for file, score in scores.items():
        assert score >= 0, f"Score for {file} is negative: {score}"
    
    # Sum of scores should be 1.0 (±0.001 tolerance)
    total = sum(scores.values())
    assert abs(total - 1.0) < 0.001, f"PageRank scores sum to {total}, expected 1.0"


@pytest.mark.property
@given(chunks=st.lists(code_chunk_strategy(), min_size=1, max_size=20))
@settings(max_examples=50, deadline=None)
def test_property_pagerank_score_validity_igraph(chunks):
    """
    Property 7: PageRank Score Validity (igraph backend)
    
    For any built RepoMap_Graph, the computed PageRank scores SHALL sum to 1.0
    (within floating-point tolerance of ±0.001).
    
    Validates: Requirements 3.2
    """
    # Skip if igraph not available
    pytest.importorskip("igraph")
    
    # Create and build graph
    graph = IGraphRepoMap()
    graph.build(chunks)
    
    # Compute PageRank scores
    scores = graph.pagerank()
    
    # Scores should not be empty
    assert len(scores) > 0
    
    # All scores should be non-negative
    for file, score in scores.items():
        assert score >= 0, f"Score for {file} is negative: {score}"
    
    # Sum of scores should be 1.0 (±0.001 tolerance)
    total = sum(scores.values())
    assert abs(total - 1.0) < 0.001, f"PageRank scores sum to {total}, expected 1.0"



# Property 8: Changed File Score Boosting
# Validates: Requirements 3.3
@pytest.mark.property
@given(
    chunks=st.lists(code_chunk_strategy(), min_size=2, max_size=20),
    changed_file_indices=st.lists(st.integers(min_value=0, max_value=19), min_size=1, max_size=5, unique=True)
)
@settings(max_examples=50, deadline=None)
def test_property_changed_file_score_boosting_networkx(chunks, changed_file_indices):
    """
    Property 8: Changed File Score Boosting
    
    For any RepoMap_Graph and set of changed files, the PageRank scores of changed
    files SHALL be higher after boosting than before boosting.
    
    Validates: Requirements 3.3
    """
    # Skip if networkx not available
    pytest.importorskip("networkx")
    
    # Get unique files
    unique_files = sorted(set(chunk.path for chunk in chunks))
    
    # Skip if not enough files
    if len(unique_files) < 2:
        return
    
    # Select changed files (ensure indices are valid)
    changed_files = [
        unique_files[idx % len(unique_files)]
        for idx in changed_file_indices
    ]
    changed_files = list(set(changed_files))  # Remove duplicates
    
    # Create and build graph
    graph = NetworkXRepoMap(boost_factor=2.0)
    graph.build(chunks)
    
    # Compute scores without boosting
    scores_before = graph.pagerank(changed_files=None)
    
    # Compute scores with boosting
    scores_after = graph.pagerank(changed_files=changed_files)
    
    # Skip if all files are changed (boosting all files and renormalizing results in same scores)
    if len(changed_files) == len(unique_files):
        return
    
    # Changed files should have higher scores after boosting
    for file in changed_files:
        if file in scores_before and file in scores_after:
            assert scores_after[file] > scores_before[file], \
                f"Changed file {file} score did not increase: {scores_before[file]} -> {scores_after[file]}"
    
    # Scores should still sum to 1.0 after boosting
    total = sum(scores_after.values())
    assert abs(total - 1.0) < 0.001, f"Boosted scores sum to {total}, expected 1.0"


@pytest.mark.property
@given(
    chunks=st.lists(code_chunk_strategy(), min_size=2, max_size=20),
    changed_file_indices=st.lists(st.integers(min_value=0, max_value=19), min_size=1, max_size=5, unique=True)
)
@settings(max_examples=50, deadline=None)
def test_property_changed_file_score_boosting_igraph(chunks, changed_file_indices):
    """
    Property 8: Changed File Score Boosting (igraph backend)
    
    For any RepoMap_Graph and set of changed files, the PageRank scores of changed
    files SHALL be higher after boosting than before boosting.
    
    Validates: Requirements 3.3
    """
    # Skip if igraph not available
    pytest.importorskip("igraph")
    
    # Get unique files
    unique_files = sorted(set(chunk.path for chunk in chunks))
    
    # Skip if not enough files
    if len(unique_files) < 2:
        return
    
    # Select changed files (ensure indices are valid)
    changed_files = [
        unique_files[idx % len(unique_files)]
        for idx in changed_file_indices
    ]
    changed_files = list(set(changed_files))  # Remove duplicates
    
    # Create and build graph
    graph = IGraphRepoMap(boost_factor=2.0)
    graph.build(chunks)
    
    # Compute scores without boosting
    scores_before = graph.pagerank(changed_files=None)
    
    # Compute scores with boosting
    scores_after = graph.pagerank(changed_files=changed_files)
    
    # Skip if all files are changed (boosting all files and renormalizing results in same scores)
    if len(changed_files) == len(unique_files):
        return
    
    # Changed files should have higher scores after boosting
    for file in changed_files:
        if file in scores_before and file in scores_after:
            assert scores_after[file] > scores_before[file], \
                f"Changed file {file} score did not increase: {scores_before[file]} -> {scores_after[file]}"
    
    # Scores should still sum to 1.0 after boosting
    total = sum(scores_after.values())
    assert abs(total - 1.0) < 0.001, f"Boosted scores sum to {total}, expected 1.0"
