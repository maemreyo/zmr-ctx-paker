"""Unit tests for Vector Index implementations."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from context_packer.models import CodeChunk
from context_packer.vector_index import (
    EmbeddingGenerator,
    FAISSIndex,
    LEANNIndex,
    VectorIndex,
    create_vector_index,
    load_vector_index,
)


@pytest.fixture
def sample_chunks():
    """Create sample code chunks for testing."""
    return [
        CodeChunk(
            path="src/auth.py",
            start_line=1,
            end_line=10,
            content="def authenticate(user, password):\n    return check_credentials(user, password)",
            symbols_defined=["authenticate"],
            symbols_referenced=["check_credentials"],
            language="python"
        ),
        CodeChunk(
            path="src/auth.py",
            start_line=11,
            end_line=20,
            content="def check_credentials(user, password):\n    return user in database",
            symbols_defined=["check_credentials"],
            symbols_referenced=["database"],
            language="python"
        ),
        CodeChunk(
            path="src/utils.py",
            start_line=1,
            end_line=5,
            content="def format_output(data):\n    return json.dumps(data)",
            symbols_defined=["format_output"],
            symbols_referenced=["json"],
            language="python"
        ),
    ]


@pytest.fixture
def mock_embeddings():
    """Create mock embeddings for testing."""
    # 3 files, 384-dimensional embeddings (all-MiniLM-L6-v2 dimension)
    return np.random.rand(3, 384).astype('float32')


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""
    
    def test_init(self):
        """Test initialization."""
        gen = EmbeddingGenerator(
            model_name="test-model",
            device="cpu",
            batch_size=16
        )
        assert gen.model_name == "test-model"
        assert gen.device == "cpu"
        assert gen.batch_size == 16
        assert gen._model is None
        assert gen._use_api is False
    
    @patch('context_packer.vector_index.vector_index.psutil.virtual_memory')
    def test_check_memory_sufficient(self, mock_memory):
        """Test memory check when sufficient memory available."""
        mock_memory.return_value.available = 1024 * 1024 * 1024  # 1GB
        gen = EmbeddingGenerator()
        assert gen._check_memory() is True
    
    @patch('context_packer.vector_index.vector_index.psutil.virtual_memory')
    def test_check_memory_insufficient(self, mock_memory):
        """Test memory check when insufficient memory available."""
        mock_memory.return_value.available = 100 * 1024 * 1024  # 100MB
        gen = EmbeddingGenerator()
        assert gen._check_memory() is False
    
    @patch('context_packer.vector_index.vector_index.psutil.virtual_memory')
    def test_encode_local_success(self, mock_memory):
        """Test successful local encoding."""
        mock_memory.return_value.available = 1024 * 1024 * 1024  # 1GB
        
        # Mock sentence_transformers module
        mock_st_module = Mock()
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_st_module.SentenceTransformer.return_value = mock_model
        
        with patch.dict('sys.modules', {'sentence_transformers': mock_st_module}):
            gen = EmbeddingGenerator()
            texts = ["hello", "world"]
            embeddings = gen.encode(texts)
            
            assert embeddings.shape == (2, 2)
            mock_model.encode.assert_called_once()


class TestLEANNIndex:
    """Test LEANNIndex class."""
    
    def test_init(self):
        """Test initialization."""
        index = LEANNIndex(model_name="test-model", device="cpu", batch_size=16)
        assert index.model_name == "test-model"
        assert index.device == "cpu"
        assert index.batch_size == 16
        assert index._embeddings is None
        assert index._file_paths == []
    
    def test_build_empty_chunks(self):
        """Test building index with empty chunks raises error."""
        index = LEANNIndex()
        with pytest.raises(ValueError, match="Cannot build index from empty chunks"):
            index.build([])
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_build_success(self, mock_encode, sample_chunks, mock_embeddings):
        """Test successful index building."""
        mock_encode.return_value = mock_embeddings[:2]  # 2 unique files
        
        index = LEANNIndex()
        index.build(sample_chunks)
        
        assert len(index._file_paths) == 2  # src/auth.py and src/utils.py
        assert index._embeddings.shape == (2, 384)
        assert "src/auth.py" in index._file_paths
        assert "src/utils.py" in index._file_paths
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_search_success(self, mock_encode, sample_chunks, mock_embeddings):
        """Test successful search."""
        # Mock build
        mock_encode.return_value = mock_embeddings[:2]
        index = LEANNIndex()
        index.build(sample_chunks)
        
        # Mock search
        query_embedding = np.array([0.5] * 384)
        mock_encode.return_value = np.array([query_embedding])
        
        results = index.search("authentication", top_k=2)
        
        assert len(results) == 2
        assert all(isinstance(path, str) for path, _ in results)
        assert all(isinstance(score, float) for _, score in results)
        # Results should be ordered by descending similarity
        assert results[0][1] >= results[1][1]
    
    def test_search_without_build(self):
        """Test search without building index raises error."""
        index = LEANNIndex()
        with pytest.raises(RuntimeError, match="Index not built"):
            index.search("test")
    
    def test_search_empty_query(self, sample_chunks, mock_embeddings):
        """Test search with empty query raises error."""
        with patch.object(EmbeddingGenerator, 'encode', return_value=mock_embeddings[:2]):
            index = LEANNIndex()
            index.build(sample_chunks)
            
            with pytest.raises(ValueError, match="Query cannot be empty"):
                index.search("")
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_save_and_load(self, mock_encode, sample_chunks, mock_embeddings):
        """Test saving and loading index."""
        mock_encode.return_value = mock_embeddings[:2]
        
        # Build and save
        index = LEANNIndex(model_name="test-model")
        index.build(sample_chunks)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_index.pkl")
            index.save(path)
            
            # Load
            loaded_index = LEANNIndex.load(path)
            
            assert loaded_index.model_name == "test-model"
            assert loaded_index._file_paths == index._file_paths
            assert np.array_equal(loaded_index._embeddings, index._embeddings)
    
    def test_save_without_build(self):
        """Test save without building index raises error."""
        index = LEANNIndex()
        with pytest.raises(RuntimeError, match="Index not built"):
            index.save("/tmp/test.pkl")
    
    def test_cosine_similarity(self):
        """Test cosine similarity computation."""
        query = np.array([1.0, 0.0, 0.0])
        embeddings = np.array([
            [1.0, 0.0, 0.0],  # Same direction, similarity = 1.0
            [0.0, 1.0, 0.0],  # Orthogonal, similarity = 0.0
            [-1.0, 0.0, 0.0], # Opposite direction, similarity = -1.0
        ])
        
        similarities = LEANNIndex._cosine_similarity(query, embeddings)
        
        assert similarities.shape == (3,)
        assert abs(similarities[0] - 1.0) < 1e-6
        assert abs(similarities[1] - 0.0) < 1e-6
        assert abs(similarities[2] - (-1.0)) < 1e-6


class TestFAISSIndex:
    """Test FAISSIndex class."""
    
    def test_init(self):
        """Test initialization."""
        index = FAISSIndex(model_name="test-model", device="cpu", batch_size=16)
        assert index.model_name == "test-model"
        assert index.device == "cpu"
        assert index.batch_size == 16
        assert index._index is None
        assert index._file_paths == []
    
    def test_build_empty_chunks(self):
        """Test building index with empty chunks raises error."""
        index = FAISSIndex()
        with pytest.raises(ValueError, match="Cannot build index from empty chunks"):
            index.build([])
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_build_success(self, mock_encode, sample_chunks, mock_embeddings):
        """Test successful FAISS index building."""
        mock_encode.return_value = mock_embeddings[:2]
        
        # Mock faiss module
        mock_faiss = Mock()
        mock_index = MagicMock()
        mock_faiss.IndexHNSWFlat.return_value = mock_index
        
        with patch.dict('sys.modules', {'faiss': mock_faiss}):
            index = FAISSIndex()
            index.build(sample_chunks)
            
            assert len(index._file_paths) == 2
            assert index._embedding_dim == 384
            mock_index.add.assert_called_once()
    
    def test_build_faiss_not_available(self, sample_chunks):
        """Test building when FAISS not available."""
        with patch.dict('sys.modules', {'faiss': None}):
            index = FAISSIndex()
            with pytest.raises(RuntimeError, match="faiss-cpu not available"):
                index.build(sample_chunks)
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_search_success(self, mock_encode, sample_chunks, mock_embeddings):
        """Test successful FAISS search."""
        # Mock build
        mock_encode.return_value = mock_embeddings[:2]
        
        # Mock faiss module
        mock_faiss = Mock()
        mock_index = MagicMock()
        mock_faiss.IndexHNSWFlat.return_value = mock_index
        
        with patch.dict('sys.modules', {'faiss': mock_faiss}):
            index = FAISSIndex()
            index.build(sample_chunks)
            
            # Mock search
            query_embedding = np.array([0.5] * 384)
            mock_encode.return_value = np.array([query_embedding])
            mock_index.search.return_value = (
                np.array([[0.1, 0.2]]),  # distances
                np.array([[0, 1]])        # indices
            )
            
            results = index.search("authentication", top_k=2)
            
            assert len(results) == 2
            assert all(isinstance(path, str) for path, _ in results)
            assert all(isinstance(score, float) for _, score in results)
    
    def test_search_without_build(self):
        """Test search without building index raises error."""
        index = FAISSIndex()
        with pytest.raises(RuntimeError, match="Index not built"):
            index.search("test")
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_save_and_load(self, mock_encode, sample_chunks, mock_embeddings):
        """Test saving and loading FAISS index."""
        mock_encode.return_value = mock_embeddings[:2]
        
        # Mock faiss module
        mock_faiss = Mock()
        mock_index = MagicMock()
        mock_faiss.IndexHNSWFlat.return_value = mock_index
        
        with patch.dict('sys.modules', {'faiss': mock_faiss}):
            # Build and save
            index = FAISSIndex(model_name="test-model")
            index.build(sample_chunks)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "test_index.pkl")
                index.save(path)
                
                # Verify save was called
                mock_faiss.write_index.assert_called_once()
                
                # Mock load
                mock_faiss.read_index.return_value = mock_index
                
                # Load
                loaded_index = FAISSIndex.load(path)
                
                assert loaded_index.model_name == "test-model"
                assert loaded_index._file_paths == index._file_paths
                assert loaded_index._embedding_dim == index._embedding_dim


class TestGetFileSymbols:
    """Tests for get_file_symbols() on both index implementations."""

    @patch.object(EmbeddingGenerator, 'encode')
    def test_leann_get_file_symbols_after_build(self, mock_encode, sample_chunks, mock_embeddings):
        """LEANNIndex.get_file_symbols() returns correct symbol mapping after build."""
        mock_encode.return_value = mock_embeddings[:2]

        index = LEANNIndex()
        index.build(sample_chunks)

        file_symbols = index.get_file_symbols()

        assert "src/auth.py" in file_symbols
        assert "src/utils.py" in file_symbols
        # auth.py defines authenticate and check_credentials
        assert "authenticate" in file_symbols["src/auth.py"]
        assert "check_credentials" in file_symbols["src/auth.py"]
        # utils.py defines format_output
        assert "format_output" in file_symbols["src/utils.py"]

    def test_leann_get_file_symbols_before_build(self):
        """LEANNIndex.get_file_symbols() returns empty dict before build."""
        index = LEANNIndex()
        assert index.get_file_symbols() == {}

    @patch.object(EmbeddingGenerator, 'encode')
    def test_leann_symbols_persisted_through_save_load(self, mock_encode, sample_chunks, mock_embeddings):
        """Symbols survive a save/load round-trip."""
        mock_encode.return_value = mock_embeddings[:2]

        import tempfile, os
        index = LEANNIndex(model_name="test-model")
        index.build(sample_chunks)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "index.pkl")
            index.save(path)
            loaded = LEANNIndex.load(path)

        assert loaded.get_file_symbols() == index.get_file_symbols()

    @patch.object(EmbeddingGenerator, 'encode')
    def test_faiss_get_file_symbols_after_build(self, mock_encode, sample_chunks, mock_embeddings):
        """FAISSIndex.get_file_symbols() returns correct symbol mapping after build."""
        mock_encode.return_value = mock_embeddings[:2]

        mock_faiss = __import__('unittest.mock', fromlist=['Mock']).Mock()
        mock_index = __import__('unittest.mock', fromlist=['MagicMock']).MagicMock()
        mock_faiss.IndexHNSWFlat.return_value = mock_index

        import sys
        with __import__('unittest.mock', fromlist=['patch']).patch.dict(
            sys.modules, {'faiss': mock_faiss}
        ):
            index = FAISSIndex()
            index.build(sample_chunks)

        file_symbols = index.get_file_symbols()
        assert "src/auth.py" in file_symbols
        assert "authenticate" in file_symbols["src/auth.py"]
        assert "format_output" in file_symbols["src/utils.py"]

    def test_vector_index_base_default_returns_empty(self):
        """VectorIndex base class get_file_symbols() returns empty dict by default."""
        # MockVectorIndex inherits the base implementation
        from tests.unit.test_retrieval import MockVectorIndex
        idx = MockVectorIndex()
        assert idx.get_file_symbols() == {}


class TestBackendSelection:
    """Test backend selection and fallback logic."""
    
    def test_create_vector_index_auto_leann_success(self):
        """Test auto mode successfully creates LEANN index."""
        index = create_vector_index(backend="auto")
        assert isinstance(index, LEANNIndex)
    
    @patch.object(LEANNIndex, '__init__', side_effect=Exception("LEANN failed"))
    def test_create_vector_index_auto_fallback_to_faiss(self, mock_leann_init):
        """Test auto mode falls back to FAISS when LEANN fails."""
        # Mock faiss module
        mock_faiss = Mock()
        mock_faiss.IndexHNSWFlat.return_value = MagicMock()
        
        with patch.dict('sys.modules', {'faiss': mock_faiss}):
            index = create_vector_index(backend="auto")
            assert isinstance(index, FAISSIndex)
    
    def test_create_vector_index_specific_backend(self):
        """Test creating index with specific backend."""
        leann_index = create_vector_index(backend="leann")
        assert isinstance(leann_index, LEANNIndex)
    
    def test_create_vector_index_invalid_backend(self):
        """Test creating index with invalid backend raises error."""
        with pytest.raises(ValueError, match="Invalid backend"):
            create_vector_index(backend="invalid")
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_load_vector_index_leann(self, mock_encode, sample_chunks, mock_embeddings):
        """Test loading LEANN index."""
        mock_encode.return_value = mock_embeddings[:2]
        
        index = LEANNIndex()
        index.build(sample_chunks)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_index.pkl")
            index.save(path)
            
            loaded_index = load_vector_index(path)
            assert isinstance(loaded_index, LEANNIndex)
    
    @patch.object(EmbeddingGenerator, 'encode')
    def test_load_vector_index_faiss(self, mock_encode, sample_chunks, mock_embeddings):
        """Test loading FAISS index."""
        mock_encode.return_value = mock_embeddings[:2]
        
        # Mock faiss module
        mock_faiss = Mock()
        mock_index = MagicMock()
        mock_faiss.IndexHNSWFlat.return_value = mock_index
        
        with patch.dict('sys.modules', {'faiss': mock_faiss}):
            index = FAISSIndex()
            index.build(sample_chunks)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "test_index.pkl")
                index.save(path)
                
                mock_faiss.read_index.return_value = mock_index
                loaded_index = load_vector_index(path)
                assert isinstance(loaded_index, FAISSIndex)
