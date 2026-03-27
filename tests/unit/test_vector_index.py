"""Unit tests for Vector Index implementations."""

import os
import sys
import tempfile
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.vector_index import (
    EmbeddingGenerator,
    FAISSIndex,
    LEANNIndex,
    NativeLEANNIndex,
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
            language="python",
        ),
        CodeChunk(
            path="src/auth.py",
            start_line=11,
            end_line=20,
            content="def check_credentials(user, password):\n    return user in database",
            symbols_defined=["check_credentials"],
            symbols_referenced=["database"],
            language="python",
        ),
        CodeChunk(
            path="src/utils.py",
            start_line=1,
            end_line=5,
            content="def format_output(data):\n    return json.dumps(data)",
            symbols_defined=["format_output"],
            symbols_referenced=["json"],
            language="python",
        ),
    ]


@pytest.fixture
def mock_embeddings():
    """Create mock embeddings for testing."""
    # 3 files, 384-dimensional embeddings (all-MiniLM-L6-v2 dimension)
    return np.random.rand(3, 384).astype("float32")


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    def test_init(self):
        """Test initialization."""
        gen = EmbeddingGenerator(model_name="test-model", device="cpu", batch_size=16)
        assert gen.model_name == "test-model"
        assert gen.device == "cpu"
        assert gen.batch_size == 16
        assert gen._model is None
        assert gen._use_api is False

    @patch("ws_ctx_engine.vector_index.vector_index.psutil.virtual_memory")
    def test_check_memory_sufficient(self, mock_memory):
        """Test memory check when sufficient memory available."""
        mock_memory.return_value.available = 1024 * 1024 * 1024  # 1GB
        gen = EmbeddingGenerator()
        assert gen._check_memory() is True

    @patch("ws_ctx_engine.vector_index.vector_index.psutil.virtual_memory")
    def test_check_memory_insufficient(self, mock_memory):
        """Test memory check when insufficient memory available."""
        mock_memory.return_value.available = 100 * 1024 * 1024  # 100MB
        gen = EmbeddingGenerator()
        assert gen._check_memory() is False

    @patch("ws_ctx_engine.vector_index.vector_index.psutil.virtual_memory")
    def test_encode_local_success(self, mock_memory):
        """Test successful local encoding."""
        mock_memory.return_value.available = 1024 * 1024 * 1024  # 1GB

        # Mock sentence_transformers module
        mock_st_module = Mock()
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_st_module.SentenceTransformer.return_value = mock_model

        with patch.dict("sys.modules", {"sentence_transformers": mock_st_module}):
            gen = EmbeddingGenerator()
            texts = ["hello", "world"]
            embeddings = gen.encode(texts)

            assert embeddings.shape == (2, 2)
            # The model registry may issue a warm-up call; assert the real
            # encode call happened with the expected texts (last call).
            assert mock_model.encode.call_count >= 1
            actual_texts = mock_model.encode.call_args_list[-1][0][0]
            assert actual_texts == texts


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

    @patch.object(EmbeddingGenerator, "encode")
    def test_build_success(self, mock_encode, sample_chunks, mock_embeddings):
        """Test successful index building."""
        mock_encode.return_value = mock_embeddings[:2]  # 2 unique files

        index = LEANNIndex()
        index.build(sample_chunks)

        assert len(index._file_paths) == 2  # src/auth.py and src/utils.py
        assert index._embeddings.shape == (2, 384)
        assert "src/auth.py" in index._file_paths
        assert "src/utils.py" in index._file_paths

    @patch.object(EmbeddingGenerator, "encode")
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
        with patch.object(EmbeddingGenerator, "encode", return_value=mock_embeddings[:2]):
            index = LEANNIndex()
            index.build(sample_chunks)

            with pytest.raises(ValueError, match="Query cannot be empty"):
                index.search("")

    @patch.object(EmbeddingGenerator, "encode")
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
        embeddings = np.array(
            [
                [1.0, 0.0, 0.0],  # Same direction, similarity = 1.0
                [0.0, 1.0, 0.0],  # Orthogonal, similarity = 0.0
                [-1.0, 0.0, 0.0],  # Opposite direction, similarity = -1.0
            ]
        )

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

    @patch.object(EmbeddingGenerator, "encode")
    def test_build_success(self, mock_encode, sample_chunks, mock_embeddings):
        """Test successful FAISS index building creates IndexIDMap2 wrapping IndexFlatL2."""
        mock_encode.return_value = mock_embeddings[:2]

        mock_faiss = Mock()
        mock_flat = MagicMock()
        mock_idmap = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_flat
        mock_faiss.IndexIDMap2.return_value = mock_idmap

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            index = FAISSIndex()
            index.build(sample_chunks)

            # H-2: verify IndexFlatL2 + IndexIDMap2 are used, not IndexHNSWFlat
            mock_faiss.IndexFlatL2.assert_called_once_with(384)
            mock_faiss.IndexIDMap2.assert_called_once_with(mock_flat)
            mock_idmap.add_with_ids.assert_called_once()

            assert len(index._file_paths) == 2
            assert index._embedding_dim == 384
            # _id_to_path and _next_id must be populated
            assert len(index._id_to_path) == 2
            assert index._next_id == 2

    def test_build_faiss_not_available(self, sample_chunks):
        """Test building when FAISS not available."""
        with patch.dict("sys.modules", {"faiss": None}):
            index = FAISSIndex()
            with pytest.raises(RuntimeError, match="faiss-cpu not available"):
                index.build(sample_chunks)

    @patch.object(EmbeddingGenerator, "encode")
    def test_search_success(self, mock_encode, sample_chunks, mock_embeddings):
        """Test successful FAISS search using _id_to_path for result resolution."""
        mock_encode.return_value = mock_embeddings[:2]

        mock_faiss = Mock()
        mock_flat = MagicMock()
        mock_idmap = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_flat
        mock_faiss.IndexIDMap2.return_value = mock_idmap

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            index = FAISSIndex()
            index.build(sample_chunks)

            query_embedding = np.array([0.5] * 384)
            mock_encode.return_value = np.array([query_embedding])
            mock_idmap.search.return_value = (
                np.array([[0.1, 0.2]]),  # distances
                np.array([[0, 1]]),       # IDs
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

    @patch.object(EmbeddingGenerator, "encode")
    def test_save_and_load(self, mock_encode, sample_chunks, mock_embeddings):
        """Test saving and loading FAISS index preserves _id_to_path and _next_id."""
        mock_encode.return_value = mock_embeddings[:2]

        mock_faiss = Mock()
        mock_flat = MagicMock()
        mock_idmap = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_flat
        mock_faiss.IndexIDMap2.return_value = mock_idmap

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            index = FAISSIndex(model_name="test-model")
            index.build(sample_chunks)

            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "test_index.pkl")
                index.save(path)
                mock_faiss.write_index.assert_called_once()

                mock_faiss.read_index.return_value = mock_idmap
                # Make the loaded index look like IndexIDMap2 so _ensure_idmap2 is a no-op
                mock_faiss.IndexIDMap2 = type(mock_idmap)

                loaded_index = FAISSIndex.load(path)

                assert loaded_index.model_name == "test-model"
                assert loaded_index._file_paths == index._file_paths
                assert loaded_index._embedding_dim == index._embedding_dim
                # H-1: id mapping must survive round-trip
                assert loaded_index._id_to_path == index._id_to_path
                assert loaded_index._next_id == index._next_id

    @patch.object(EmbeddingGenerator, "encode")
    def test_incremental_update_uses_monotonic_ids(self, mock_encode, sample_chunks, mock_embeddings):
        """After deletion+addition, new IDs must not collide with deleted IDs (H-1)."""
        mock_encode.return_value = mock_embeddings[:2]

        mock_faiss = Mock()
        mock_flat = MagicMock()
        mock_idmap = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_flat
        mock_faiss.IndexIDMap2.return_value = mock_idmap  # used by build()

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            index = FAISSIndex()
            index.build(sample_chunks)
            original_next_id = index._next_id  # == 2 after building 2 files

            # Switch IndexIDMap2 to a real type *after* build so that the
            # isinstance() checks in _ensure_idmap2() and update_incremental()
            # don't raise TypeError (Mock is not a valid type for isinstance).
            mock_faiss.IndexIDMap2 = type(mock_idmap)

            # Simulate deleting the first file and adding a new one
            deleted_path = index._file_paths[0]
            new_chunk = sample_chunks[0].__class__(
                path="src/new_file.py",
                content="new content",
                language="python",
                symbols_defined=[],
                symbols_referenced=[],
                start_line=1,
                end_line=5,
            )
            mock_encode.return_value = mock_embeddings[:1]

            index.update_incremental(
                deleted_paths=[deleted_path],
                new_chunks=[new_chunk],
            )

            # New ID must be >= original _next_id, never reusing the deleted ID
            added_ids = [k for k, v in index._id_to_path.items() if v == "src/new_file.py"]
            assert len(added_ids) == 1
            assert added_ids[0] >= original_next_id
            assert added_ids[0] not in [0, 1]  # not a recycled ID

    @patch.object(EmbeddingGenerator, "encode")
    def test_load_legacy_index_derives_id_to_path(self, mock_encode, sample_chunks, mock_embeddings):
        """Loading an index saved without id_to_path derives it from _file_paths (H-1 backcompat)."""
        mock_encode.return_value = mock_embeddings[:2]

        mock_faiss = Mock()
        mock_flat = MagicMock()
        mock_idmap = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_flat
        mock_faiss.IndexIDMap2.return_value = mock_idmap

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            index = FAISSIndex(model_name="test-model")
            index.build(sample_chunks)

            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "legacy_index.pkl")
                index.save(path)

                # Simulate a legacy file: strip id_to_path / next_id from the pickle
                import pickle
                with open(path, "rb") as f:
                    meta = pickle.load(f)
                meta.pop("id_to_path", None)
                meta.pop("next_id", None)
                with open(path, "wb") as f:
                    pickle.dump(meta, f)

                mock_faiss.read_index.return_value = mock_idmap
                mock_faiss.IndexIDMap2 = type(mock_idmap)

                loaded = FAISSIndex.load(path)

                # Must reconstruct _id_to_path from _file_paths
                expected = {i: p for i, p in enumerate(loaded._file_paths)}
                assert loaded._id_to_path == expected
                assert loaded._next_id == len(loaded._file_paths)


class TestGetFileSymbols:
    """Tests for get_file_symbols() on both index implementations."""

    @patch.object(EmbeddingGenerator, "encode")
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

    @patch.object(EmbeddingGenerator, "encode")
    def test_leann_symbols_persisted_through_save_load(
        self, mock_encode, sample_chunks, mock_embeddings
    ):
        """Symbols survive a save/load round-trip."""
        mock_encode.return_value = mock_embeddings[:2]

        import os
        import tempfile

        index = LEANNIndex(model_name="test-model")
        index.build(sample_chunks)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "index.pkl")
            index.save(path)
            loaded = LEANNIndex.load(path)

        assert loaded.get_file_symbols() == index.get_file_symbols()

    @patch.object(EmbeddingGenerator, "encode")
    def test_faiss_get_file_symbols_after_build(self, mock_encode, sample_chunks, mock_embeddings):
        """FAISSIndex.get_file_symbols() returns correct symbol mapping after build."""
        mock_encode.return_value = mock_embeddings[:2]

        mock_faiss = __import__("unittest.mock", fromlist=["Mock"]).Mock()
        mock_index = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        mock_faiss.IndexHNSWFlat.return_value = mock_index

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules, {"faiss": mock_faiss}
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
        """Test auto mode successfully creates a LEANN-family index (native or pure-Python)."""
        index = create_vector_index(backend="auto")
        assert isinstance(index, (NativeLEANNIndex, LEANNIndex))

    @patch("ws_ctx_engine.vector_index.vector_index.create_vector_index", wraps=None)
    def test_create_vector_index_auto_fallback_to_faiss(self, _mock: Any) -> None:
        """Test auto mode falls back to FAISS when both LEANN variants fail."""
        mock_faiss = Mock()
        mock_faiss.IndexHNSWFlat.return_value = MagicMock()

        with (
            patch.object(NativeLEANNIndex, "__init__", side_effect=Exception("NativeLEANN failed")),
            patch.object(LEANNIndex, "__init__", side_effect=Exception("LEANN failed")),
            patch.dict("sys.modules", {"faiss": mock_faiss}),
        ):
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

    @patch.object(EmbeddingGenerator, "encode")
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

    @patch.object(EmbeddingGenerator, "encode")
    def test_load_vector_index_faiss(self, mock_encode, sample_chunks, mock_embeddings):
        """Test loading FAISS index."""
        mock_encode.return_value = mock_embeddings[:2]

        # Mock faiss module. IndexIDMap2 stays as Mock during build() so that
        # .return_value works. It is switched to a real type before load() so
        # that isinstance() checks in load()/_ensure_idmap2() don't raise TypeError.
        mock_faiss = Mock()
        mock_idmap = MagicMock()
        mock_faiss.IndexFlatL2.return_value = MagicMock()
        mock_faiss.IndexIDMap2.return_value = mock_idmap  # used by build()

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            index = FAISSIndex()
            index.build(sample_chunks)

            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "test_index.pkl")
                index.save(path)

                mock_faiss.read_index.return_value = mock_idmap
                # Switch to a real type so isinstance(loaded._index, faiss.IndexIDMap2) works
                mock_faiss.IndexIDMap2 = type(mock_idmap)
                loaded_index = load_vector_index(path)
                assert isinstance(loaded_index, FAISSIndex)
