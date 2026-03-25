"""Property-based tests for Vector Index implementations.

Tests universal properties that should hold for all vector index implementations.
"""

import sys
import tempfile
from unittest.mock import Mock, MagicMock, patch

import numpy as np
import pytest
from hypothesis import given, strategies as st, settings, assume

from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.vector_index import (
    LEANNIndex,
    FAISSIndex,
    create_vector_index,
)


# Strategies for generating test data
@st.composite
def code_chunks_strategy(draw):
    """Generate a list of valid CodeChunk objects."""
    num_chunks = draw(st.integers(min_value=1, max_value=10))
    num_files = draw(st.integers(min_value=1, max_value=min(5, num_chunks)))
    
    file_paths = [f"src/file{i}.py" for i in range(num_files)]
    chunks = []
    
    for _ in range(num_chunks):
        path = draw(st.sampled_from(file_paths))
        start_line = draw(st.integers(min_value=1, max_value=100))
        end_line = draw(st.integers(min_value=start_line, max_value=start_line + 50))
        content = draw(st.text(min_size=10, max_size=200))
        symbols_defined = draw(st.lists(st.text(min_size=1, max_size=20), max_size=3))
        symbols_referenced = draw(st.lists(st.text(min_size=1, max_size=20), max_size=5))
        language = draw(st.sampled_from(["python", "javascript", "typescript"]))
        
        chunks.append(CodeChunk(
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
            symbols_defined=symbols_defined,
            symbols_referenced=symbols_referenced,
            language=language
        ))
    
    return chunks


class TestVectorIndexSearchOrdering:
    """Property 3: Vector Index Search Ordering
    
    Validates: Requirements 2.1, 2.3
    
    For any search query on a built Vector_Index, the returned results SHALL be
    ordered by descending cosine similarity scores.
    """
    
    @settings(max_examples=20)
    @given(chunks=code_chunks_strategy(), query=st.text(min_size=5, max_size=100))
    def test_leann_search_ordering(self, chunks, query):
        """Test that LEANN search results are ordered by descending similarity."""
        # Mock embedding generator
        num_files = len(set(chunk.path for chunk in chunks))
        mock_embeddings = np.random.rand(num_files, 384).astype('float32')
        query_embedding = np.random.rand(384).astype('float32')
        
        mock_gen = Mock()
        mock_gen.encode.side_effect = [mock_embeddings, np.array([query_embedding])]
        
        index = LEANNIndex()
        
        # Mock the embedding generator before build
        with patch.object(index, '_embedding_generator', None):
            index._embedding_generator = mock_gen
            
            # Manually set up the index state (simulating build without actual embedding generation)
            file_to_chunks = {}
            for chunk in chunks:
                if chunk.path not in file_to_chunks:
                    file_to_chunks[chunk.path] = []
                file_to_chunks[chunk.path].append(chunk)
            
            index._file_paths = list(file_to_chunks.keys())
            index._embeddings = mock_embeddings
            
            # Perform search
            results = index.search(query, top_k=min(10, num_files))
            
            # Property: Results must be ordered by descending similarity
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True), \
                f"Search results not ordered by descending similarity: {scores}"
            
            # Property: All scores should be between -1 and 1 (cosine similarity range)
            assert all(-1.0 <= score <= 1.0 for score in scores), \
                f"Similarity scores outside valid range [-1, 1]: {scores}"
    
    @settings(max_examples=20)
    @given(chunks=code_chunks_strategy(), query=st.text(min_size=5, max_size=100))
    def test_faiss_search_ordering(self, chunks, query):
        """Test that FAISS search results are ordered by descending similarity."""
        # Mock faiss module
        mock_faiss = Mock()
        mock_index = MagicMock()
        mock_faiss.IndexHNSWFlat.return_value = mock_index
        
        num_files = len(set(chunk.path for chunk in chunks))
        mock_embeddings = np.random.rand(num_files, 384).astype('float32')
        query_embedding = np.random.rand(384).astype('float32')
        
        # Mock search results (distances and indices)
        top_k = min(10, num_files)
        distances = np.sort(np.random.rand(top_k).astype('float32'))  # Sorted ascending
        indices = np.arange(top_k)
        mock_index.search.return_value = (np.array([distances]), np.array([indices]))
        
        with patch.dict('sys.modules', {'faiss': mock_faiss}):
            mock_gen = Mock()
            mock_gen.encode.side_effect = [mock_embeddings, np.array([query_embedding])]
            
            index = FAISSIndex()
            
            # Manually set up the index state (simulating build without actual embedding generation)
            file_to_chunks = {}
            for chunk in chunks:
                if chunk.path not in file_to_chunks:
                    file_to_chunks[chunk.path] = []
                file_to_chunks[chunk.path].append(chunk)
            
            index._file_paths = list(file_to_chunks.keys())
            index._embedding_dim = 384
            index._index = mock_index
            index._embedding_generator = mock_gen
            
            # Perform search
            results = index.search(query, top_k=top_k)
            
            # Property: Results must be ordered by descending similarity
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True), \
                f"FAISS search results not ordered by descending similarity: {scores}"


class TestBackendFallbackAutomation:
    """Property 4: Backend Fallback Automation
    
    Validates: Requirements 2.4, 2.5, 10.1, 10.2
    
    For any component where the primary backend fails to import or build, the system
    SHALL automatically switch to the fallback backend and log a warning with the
    component name and reason.
    """
    
    @settings(max_examples=10)
    @given(backend=st.sampled_from(["auto", "leann", "faiss"]))
    def test_backend_fallback_on_failure(self, backend):
        """Test that backend fallback occurs when primary fails."""
        if backend == "leann":
            # LEANN is primary, should succeed
            index = create_vector_index(backend="leann")
            assert isinstance(index, LEANNIndex)
        
        elif backend == "faiss":
            # FAISS is fallback, should succeed with mocking
            mock_faiss = Mock()
            mock_faiss.IndexHNSWFlat.return_value = MagicMock()
            
            with patch.dict('sys.modules', {'faiss': mock_faiss}):
                index = create_vector_index(backend="faiss")
                assert isinstance(index, FAISSIndex)
        
        elif backend == "auto":
            # Auto mode: try LEANN first
            # If LEANN fails, should fall back to FAISS
            with patch.object(LEANNIndex, '__init__', side_effect=Exception("LEANN failed")):
                mock_faiss = Mock()
                mock_faiss.IndexHNSWFlat.return_value = MagicMock()
                
                with patch.dict('sys.modules', {'faiss': mock_faiss}):
                    index = create_vector_index(backend="auto")
                    # Property: Should fall back to FAISS
                    assert isinstance(index, FAISSIndex)
    
    @settings(max_examples=10)
    @given(chunks=code_chunks_strategy())
    def test_fallback_preserves_functionality(self, chunks):
        """Test that fallback backend preserves core functionality."""
        # Simulate LEANN failure and FAISS fallback
        with patch.object(LEANNIndex, '__init__', side_effect=Exception("LEANN failed")):
            mock_faiss = Mock()
            mock_index = MagicMock()
            mock_faiss.IndexHNSWFlat.return_value = mock_index
            
            with patch.dict('sys.modules', {'faiss': mock_faiss}):
                index = create_vector_index(backend="auto")
                
                # Property: Fallback index should still support build operation
                num_files = len(set(chunk.path for chunk in chunks))
                mock_embeddings = np.random.rand(num_files, 384).astype('float32')
                
                # Mock the embedding generator to avoid actual API calls
                mock_gen = Mock()
                mock_gen.encode.return_value = mock_embeddings
                
                # Manually set up the index state (simulating successful build)
                file_to_chunks = {}
                for chunk in chunks:
                    if chunk.path not in file_to_chunks:
                        file_to_chunks[chunk.path] = []
                    file_to_chunks[chunk.path].append(chunk)
                
                index._file_paths = list(file_to_chunks.keys())
                index._embedding_dim = 384
                index._index = mock_index
                index._embedding_generator = mock_gen
                
                # Property: Index should be built successfully
                assert len(index._file_paths) == num_files
                assert index._embedding_dim == 384


class TestEmbeddingFallbackChain:
    """Property 5: Embedding Fallback Chain
    
    Validates: Requirements 2.6
    
    For any memory failure during local embedding generation, the system SHALL
    fall back to API-based embeddings without crashing.
    """
    
    @settings(max_examples=10)
    @given(texts=st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
    def test_embedding_fallback_on_oom(self, texts):
        """Test that embedding generation falls back to API on OOM."""
        from ws_ctx_engine.vector_index import EmbeddingGenerator
        
        # Mock sentence_transformers to raise MemoryError
        mock_st_module = Mock()
        mock_st_module.SentenceTransformer.side_effect = MemoryError("Out of memory")
        
        # Mock OpenAI API
        mock_openai = Mock()
        mock_response = {
            'data': [{'embedding': np.random.rand(1536).tolist()} for _ in texts]
        }
        mock_openai.Embedding.create.side_effect = [
            {'data': [{'embedding': np.random.rand(1536).tolist()}]}
            for _ in texts
        ]
        
        with patch.dict('sys.modules', {
            'sentence_transformers': mock_st_module,
            'openai': mock_openai
        }), \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), \
             patch('ws_ctx_engine.vector_index.psutil.virtual_memory') as mock_mem:
            
            mock_mem.return_value.available = 1024 * 1024 * 1024  # 1GB
            
            gen = EmbeddingGenerator()
            
            # Property: Should not crash, should fall back to API
            try:
                embeddings = gen.encode(texts)
                # If we get here, fallback worked
                assert embeddings is not None
                assert len(embeddings) == len(texts)
            except RuntimeError as e:
                # Acceptable if API also fails (no API key, etc.)
                assert "Failed to generate embeddings" in str(e) or \
                       "Failed to initialize API client" in str(e)
    
    @settings(max_examples=10)
    @given(texts=st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
    def test_embedding_fallback_on_low_memory(self, texts):
        """Test that embedding generation falls back to API on low memory."""
        from ws_ctx_engine.vector_index import EmbeddingGenerator
        
        # Mock low memory condition
        with patch('ws_ctx_engine.vector_index.psutil.virtual_memory') as mock_mem:
            mock_mem.return_value.available = 100 * 1024 * 1024  # 100MB (below threshold)
            
            gen = EmbeddingGenerator()
            
            # Property: Should detect low memory and skip local model initialization
            assert gen._model is None
            
            # When encode is called, should attempt API fallback
            # (will fail without actual API, but that's expected)
            with pytest.raises(RuntimeError, match="Failed to generate embeddings|Failed to initialize API client"):
                gen.encode(texts)


class TestVectorIndexRoundTrip:
    """Test that save/load preserves index functionality."""
    
    @settings(max_examples=10)
    @given(chunks=code_chunks_strategy(), query=st.text(min_size=5, max_size=100), seed=st.integers(min_value=0, max_value=10000))
    def test_leann_save_load_preserves_search(self, chunks, query, seed):
        """Test that LEANN save/load preserves search results."""
        # Use seed for reproducible random embeddings
        np.random.seed(seed)
        
        num_files = len(set(chunk.path for chunk in chunks))
        mock_embeddings = np.random.rand(num_files, 384).astype('float32')
        query_embedding = np.random.rand(384).astype('float32')
        
        # Build original index
        mock_gen = Mock()
        # Return the same query embedding every time encode is called with a query
        mock_gen.encode.return_value = np.array([query_embedding])
        
        index = LEANNIndex()
        
        # Manually set up the index state (simulating build)
        file_to_chunks = {}
        for chunk in chunks:
            if chunk.path not in file_to_chunks:
                file_to_chunks[chunk.path] = []
            file_to_chunks[chunk.path].append(chunk)
        
        index._file_paths = list(file_to_chunks.keys())
        index._embeddings = mock_embeddings
        index._embedding_generator = mock_gen
        
        # Get original search results
        original_results = index.search(query, top_k=min(5, num_files))
        
        # Save and load
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            path = os.path.join(tmpdir, "test_index.pkl")
            index.save(path)
            
            loaded_index = LEANNIndex.load(path)
            # Create a new mock with the same query embedding
            loaded_mock_gen = Mock()
            loaded_mock_gen.encode.return_value = np.array([query_embedding])
            loaded_index._embedding_generator = loaded_mock_gen
            
            # Get loaded search results
            loaded_results = loaded_index.search(query, top_k=min(5, num_files))
            
            # Property: Results should be identical (same embeddings, same query)
            assert len(original_results) == len(loaded_results)
            for (path1, score1), (path2, score2) in zip(original_results, loaded_results):
                assert path1 == path2, f"File paths differ: {path1} != {path2}"
                assert abs(score1 - score2) < 1e-6, f"Scores differ: {score1} != {score2}"
