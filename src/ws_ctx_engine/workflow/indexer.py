"""
Index phase workflow for ws-ctx-engine.

Provides functions for building and persisting indexes for incremental querying.
"""

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

from ..backend_selector import BackendSelector
from ..chunker import parse_with_fallback
from ..config import Config
from ..domain_map import DomainKeywordMap, DomainMapDB
from ..graph import RepoMapGraph
from ..logger import get_logger
from ..models import CodeChunk, IndexMetadata
from ..monitoring import PerformanceTracker
from ..vector_index import VectorIndex

logger = get_logger()


def _detect_incremental_changes(
    repo_path: str,
    index_path: Path,
) -> tuple[bool, list[str], list[str]]:
    """
    Compare stored file hashes against current disk state.

    Returns:
        (incremental_possible, changed_paths, deleted_paths)

        *incremental_possible* is False when no prior metadata exists, meaning
        the caller should fall back to a full rebuild.
    """
    metadata_file = index_path / "metadata.json"
    if not metadata_file.exists():
        return False, [], []

    try:
        data = json.loads(metadata_file.read_text(encoding="utf-8"))
        stored_hashes: dict[str, str] = data.get("file_hashes", {})
    except Exception:
        return False, [], []

    if not stored_hashes:
        return False, [], []

    changed: list[str] = []
    deleted: list[str] = []

    for rel_path, old_hash in stored_hashes.items():
        full_path = Path(repo_path) / rel_path
        if not full_path.exists():
            deleted.append(rel_path)
            continue
        try:
            new_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        except OSError:
            changed.append(rel_path)
            continue
        if new_hash != old_hash:
            changed.append(rel_path)

    return True, changed, deleted


def index_repository(
    repo_path: str,
    config: Config | None = None,
    index_dir: str = ".ws-ctx-engine",
    domain_only: bool = False,
    incremental: bool = False,
) -> PerformanceTracker:
    """
    Build and persist indexes for later queries.

    This function implements the index phase workflow:
    1. Parse codebase with AST Chunker (with fallback)
    2. Build Vector Index (with fallback)
    3. Build RepoMap Graph (with fallback)
    4. Save indexes to .ws-ctx-engine/
    5. Save metadata for staleness detection

    Args:
        repo_path: Path to the repository root directory
        config: Configuration instance (uses defaults if None)
        index_dir: Directory to save indexes (default: .ws-ctx-engine)
        domain_only: If True, only rebuild domain_map.db (skip vector/graph)

    Returns:
        PerformanceTracker with indexing metrics

    Raises:
        ValueError: If repo_path does not exist or is not a directory
        RuntimeError: If indexing fails

    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 13.1, 13.3
    """
    if not os.path.exists(repo_path):
        raise ValueError(f"Repository path does not exist: {repo_path}")

    if not os.path.isdir(repo_path):
        raise ValueError(f"Repository path is not a directory: {repo_path}")

    # Load configuration
    if config is None:
        config = Config.load()

    # Initialize performance tracker
    tracker = PerformanceTracker()
    tracker.start_indexing()

    logger.info(f"Starting index phase for repository: {repo_path}")
    start_time = time.time()

    # Create index directory
    index_path = Path(repo_path) / index_dir
    index_path.mkdir(parents=True, exist_ok=True)

    # Initialize backend selector
    backend_selector = BackendSelector(config)
    backend_selector.log_current_configuration()

    # Phase 1: Parse codebase with AST Chunker (with fallback)
    logger.info("Phase 1: Parsing codebase with AST Chunker")
    tracker.start_phase("parsing")
    parse_start = time.time()

    # Detect changed/deleted files when incremental=True
    _changed_paths: list[str] = []
    _deleted_paths: list[str] = []
    _incremental_mode_active = False

    # Respect performance.incremental_index config flag — if the user has
    # explicitly disabled it, treat the call as a full rebuild regardless of
    # the function parameter.
    if incremental and not config.performance.get("incremental_index", True):
        logger.info(
            "Incremental indexing disabled via config (performance.incremental_index=false)"
        )
        incremental = False

    if incremental:
        _incremental_mode_active, _changed_paths, _deleted_paths = _detect_incremental_changes(
            repo_path, index_path
        )
        if _incremental_mode_active:
            logger.info(
                f"Incremental mode: {len(_changed_paths)} changed, "
                f"{len(_deleted_paths)} deleted files"
            )

    try:
        chunks = parse_with_fallback(repo_path, config=config)
        parse_duration = time.time() - parse_start
        tracker.end_phase("parsing")
        tracker.track_memory()

        if not chunks:
            raise RuntimeError("No code chunks extracted from repository")

        unique_files = len({chunk.path for chunk in chunks})
        tracker.set_files_processed(unique_files)

        logger.log_phase(
            phase="parsing",
            duration=parse_duration,
            chunks_extracted=len(chunks),
            unique_files=unique_files,
        )
    except Exception as e:
        logger.log_error(e, {"phase": "parsing", "repo_path": repo_path})
        raise RuntimeError(f"Failed to parse repository: {e}") from e

    # Phase 2: Build Vector Index (with fallback)
    if domain_only:
        logger.info("Skipping Phase 2: Vector indexing (domain_only mode)")
        tracker.start_phase("vector_indexing")
        tracker.end_phase("vector_indexing")
        vector_index = None
    else:
        logger.info("Phase 2: Building Vector Index")
        tracker.start_phase("vector_indexing")
        vector_start = time.time()

        try:
            vector_index = backend_selector.select_vector_index(
                model_name=config.embeddings["model"],
                device=config.embeddings["device"],
                batch_size=config.embeddings["batch_size"],
                index_path=str(index_path / "leann_index"),
            )

            # Load embedding cache when enabled in config (performance.cache_embeddings).
            # Skipped when False to conserve disk space or ensure deterministic builds.
            embedding_cache = None
            cache_embeddings_enabled = config.performance.get("cache_embeddings", True)
            if cache_embeddings_enabled:
                try:
                    from ..vector_index.embedding_cache import EmbeddingCache

                    embedding_cache = EmbeddingCache(cache_dir=index_path)
                    embedding_cache.load()
                except Exception:
                    embedding_cache = None

            if _incremental_mode_active and embedding_cache is not None:
                # Only rebuild changed files; use cache for unchanged
                changed_chunks = [c for c in chunks if c.path in set(_changed_paths)]
                try:
                    vector_index_path = str(index_path / "vector.idx")
                    from ..vector_index.vector_index import FAISSIndex

                    if hasattr(FAISSIndex, "load") and Path(vector_index_path).exists():
                        vector_index = FAISSIndex.load(vector_index_path)
                        vector_index.update_incremental(
                            deleted_paths=_deleted_paths + _changed_paths,
                            new_chunks=changed_chunks,
                            embedding_cache=embedding_cache,
                        )
                    else:
                        vector_index.build(chunks)
                except Exception as inc_exc:
                    logger.warning(
                        f"Incremental update failed, falling back to full rebuild: {inc_exc}"
                    )
                    vector_index.build(chunks)
            else:
                # Pass embedding_cache to build() so full rebuilds also skip
                # re-embedding unchanged files (H-3).
                vector_index.build(chunks, embedding_cache=embedding_cache)

            if embedding_cache is not None:
                embedding_cache.save()

            vector_duration = time.time() - vector_start
            tracker.end_phase("vector_indexing")
            tracker.track_memory()

            vector_index_path = str(index_path / "vector.idx")
            vector_index.save(vector_index_path)

            logger.log_phase(
                phase="vector_indexing",
                duration=vector_duration,
                backend=vector_index.__class__.__name__,
            )
        except Exception as e:
            logger.log_error(e, {"phase": "vector_indexing", "repo_path": repo_path})
            raise RuntimeError(f"Failed to build vector index: {e}") from e

    # Phase 3: Build RepoMap Graph (with fallback)
    if domain_only:
        logger.info("Skipping Phase 3: Graph building (domain_only mode)")
        tracker.start_phase("graph_building")
        tracker.end_phase("graph_building")
        graph = None
    else:
        logger.info("Phase 3: Building RepoMap Graph")
        tracker.start_phase("graph_building")
        graph_start = time.time()

        try:
            graph = backend_selector.select_graph()
            graph.build(chunks)
            graph_duration = time.time() - graph_start
            tracker.end_phase("graph_building")
            tracker.track_memory()

            graph_path = str(index_path / "graph.pkl")
            graph.save(graph_path)

            logger.log_phase(
                phase="graph_building", duration=graph_duration, backend=graph.__class__.__name__
            )
        except Exception as e:
            logger.log_error(e, {"phase": "graph_building", "repo_path": repo_path})
            raise RuntimeError(f"Failed to build graph: {e}") from e

    # Phase 3.5: Build BM25 index (optional — gracefully skipped if rank-bm25 absent)
    logger.info("Phase 3.5: Building BM25 keyword index")
    try:
        from ..retrieval.bm25_index import BM25Index

        bm25_index = BM25Index()
        bm25_index.build(chunks)
        bm25_path = str(index_path / "bm25.pkl")
        bm25_index.save(bm25_path)
        logger.info(f"BM25 index saved: {len(bm25_index._paths)} documents → {bm25_path}")
    except Exception as e:
        logger.warning(f"BM25 index build skipped: {e}")

    # Phase 4: Save metadata for staleness detection
    logger.info("Phase 4: Saving metadata for staleness detection")
    tracker.start_phase("metadata_saving")
    metadata_start = time.time()

    try:
        # Compute file hashes
        file_hashes = _compute_file_hashes(chunks, repo_path)

        # Create metadata
        backend_str = "N/A"
        if vector_index is not None and graph is not None:
            backend_str = f"{vector_index.__class__.__name__}+{graph.__class__.__name__}"

        metadata = IndexMetadata(
            created_at=datetime.now(),
            repo_path=os.path.abspath(repo_path),
            file_count=len({chunk.path for chunk in chunks}),
            backend=backend_str,
            file_hashes=file_hashes,
        )

        # Save metadata
        metadata_path = index_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "created_at": metadata.created_at.isoformat(),
                    "repo_path": metadata.repo_path,
                    "file_count": metadata.file_count,
                    "backend": metadata.backend,
                    "file_hashes": metadata.file_hashes,
                },
                f,
                indent=2,
            )

        metadata_duration = time.time() - metadata_start
        tracker.end_phase("metadata_saving")

        logger.log_phase(
            phase="metadata_saving", duration=metadata_duration, files_hashed=len(file_hashes)
        )
    except Exception as e:
        logger.log_error(e, {"phase": "metadata_saving", "repo_path": repo_path})
        raise RuntimeError(f"Failed to save metadata: {e}") from e

    # Phase 5: Build Domain Keyword Map (Phase 1: Parallel Write)
    logger.info("Phase 5: Building Domain Keyword Map")
    tracker.start_phase("domain_map_building")
    domain_map_start = time.time()

    try:
        domain_map = DomainKeywordMap()
        domain_map.build(chunks)

        db_path = str(index_path / "domain_map.db")
        db = DomainMapDB(db_path)
        mapping = {k: list(v) for k, v in domain_map._keyword_to_dirs.items()}
        db.bulk_insert(mapping)
        db.close()

        domain_map_duration = time.time() - domain_map_start
        tracker.end_phase("domain_map_building")

        logger.log_phase(
            phase="domain_map_building",
            duration=domain_map_duration,
            keywords=len(domain_map.keywords),
            db_keywords=len(mapping),
        )
    except Exception as e:
        logger.log_error(e, {"phase": "domain_map_building", "repo_path": repo_path})
        raise RuntimeError(f"Failed to build domain map: {e}") from e

    # Calculate index size
    tracker.set_index_size(str(index_path))

    # End indexing tracking
    tracker.end_indexing()

    # Log completion with metrics
    total_duration = time.time() - start_time
    logger.info(
        f"Index phase complete | total_duration={total_duration:.2f}s | " f"index_dir={index_path}"
    )
    logger.info(f"\n{tracker.format_metrics('indexing')}")

    return tracker


def _compute_file_hashes(chunks: list[CodeChunk], repo_path: str) -> dict:
    """
    Compute SHA256 hashes for all files in chunks.

    Args:
        chunks: List of CodeChunk objects
        repo_path: Path to the repository root

    Returns:
        Dictionary mapping file paths to SHA256 hashes
    """
    file_hashes = {}
    unique_files = {chunk.path for chunk in chunks}

    for file_path in unique_files:
        full_path = os.path.join(repo_path, file_path)

        try:
            with open(full_path, "rb") as f:
                content = f.read()
                file_hash = hashlib.sha256(content).hexdigest()
                file_hashes[file_path] = file_hash
        except OSError as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            # Use empty hash for files we can't read
            file_hashes[file_path] = ""

    return file_hashes


def load_indexes(
    repo_path: str,
    index_dir: str = ".ws-ctx-engine",
    auto_rebuild: bool = True,
    config: Config | None = None,
) -> tuple[VectorIndex, RepoMapGraph, IndexMetadata]:
    """
    Load indexes from disk with automatic staleness detection and rebuild.

    Args:
        repo_path: Path to the repository root directory
        index_dir: Directory containing indexes (default: .ws-ctx-engine)
        auto_rebuild: Automatically rebuild stale indexes (default: True)

    Returns:
        Tuple of (VectorIndex, RepoMapGraph, IndexMetadata)

    Raises:
        FileNotFoundError: If indexes don't exist
        RuntimeError: If loading fails

    Requirements: 9.3, 9.4, 9.5, 9.6
    """
    index_path = Path(repo_path) / index_dir

    # Check if indexes exist
    vector_index_path = index_path / "vector.idx"
    graph_path = index_path / "graph.pkl"
    metadata_path = index_path / "metadata.json"

    if not vector_index_path.exists():
        raise FileNotFoundError(f"Vector index not found: {vector_index_path}")

    if not graph_path.exists():
        raise FileNotFoundError(f"Graph not found: {graph_path}")

    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    # Load metadata
    logger.info("Loading index metadata")
    with open(metadata_path) as f:
        metadata_dict = json.load(f)

    metadata = IndexMetadata(
        created_at=datetime.fromisoformat(metadata_dict["created_at"]),
        repo_path=metadata_dict["repo_path"],
        file_count=metadata_dict["file_count"],
        backend=metadata_dict["backend"],
        file_hashes=metadata_dict["file_hashes"],
    )

    # Check staleness
    if metadata.is_stale(repo_path):
        logger.warning("Indexes are stale (files have been modified)")

        if auto_rebuild:
            logger.info("Automatically rebuilding stale indexes")
            index_repository(repo_path, config=config, index_dir=index_dir)
            # Reload after rebuild
            return load_indexes(repo_path, index_dir, auto_rebuild=False, config=config)
        else:
            logger.warning("Auto-rebuild disabled, using stale indexes")

    try:
        # Load vector index with auto-detection
        logger.info(f"Loading vector index from {vector_index_path}")
        from ..vector_index import load_vector_index

        vector_index = load_vector_index(str(vector_index_path))

        # Load graph with auto-detection
        logger.info(f"Loading graph from {graph_path}")
        from ..graph import load_graph

        graph = load_graph(str(graph_path))
    except Exception as e:
        if auto_rebuild:
            logger.warning(f"Failed to load indexes, rebuilding from scratch: {e}")
            index_repository(repo_path, config=config, index_dir=index_dir)
            return load_indexes(repo_path, index_dir, auto_rebuild=False, config=config)
        raise RuntimeError(f"Failed to load indexes: {e}") from e

    logger.info(
        f"Indexes loaded successfully | backend={metadata.backend} | "
        f"file_count={metadata.file_count}"
    )

    return vector_index, graph, metadata
