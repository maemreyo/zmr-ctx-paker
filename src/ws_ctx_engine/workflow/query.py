"""
Query phase workflow for ws-ctx-engine.

Provides functions for querying indexes and generating output in XML or ZIP format.
"""

import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..budget import BudgetManager
from ..config import Config
from ..domain_map import DomainMapDB
from ..logger import get_logger
from ..monitoring import PerformanceTracker
from ..output import JSONFormatter, MarkdownFormatter, TOONFormatter, YAMLFormatter
from ..packer import XMLPacker, ZIPPacker
from ..perf import timed
from ..retrieval import RetrievalEngine
from ..secret_scanner import SecretScanner
from .indexer import load_indexes

logger = get_logger()


def _load_graph_store(config: "Config", index_path: "Path") -> "Any":
    """Load GraphStore from config. Returns None if unavailable or unhealthy."""
    try:
        from ..graph.cozo_store import GraphStore

        db_path = Path(config.graph_store_path)
        if not db_path.is_absolute():
            db_path = index_path.parent / db_path
        storage_str = f"{config.graph_store_storage}:{db_path}"
        store = GraphStore(storage_str)
        return store if store.is_healthy else None
    except Exception as exc:
        import logging

        logging.getLogger(__name__).debug("GraphStore unavailable: %s", exc)
        return None


def _apply_graph_augmentation(
    ranked_files: list[tuple[str, float]],
    query: str,
    config: "Config",
    index_path: "Path",
) -> list[tuple[str, float]]:
    """Augment vector-ranked files with graph query results. Returns ranked_files unchanged on any failure."""
    try:
        from ..graph.signal_router import classify_graph_intent
        from ..graph.context_assembler import ContextAssembler

        intent = classify_graph_intent(query)
        if intent.intent_type != "none":
            graph_store = _load_graph_store(config, index_path)
            if graph_store is not None:
                assembler = ContextAssembler(
                    graph_store,
                    graph_query_weight=getattr(config, "graph_query_weight", 0.3),
                )
                result = assembler.assemble(ranked_files, intent)
                if result.graph_augmented:
                    logger.info(
                        "Graph augmentation: %d files added (intent=%s, target=%s)",
                        result.graph_files_added,
                        intent.intent_type,
                        intent.target,
                    )
                    return result.ranked_files
    except Exception as exc:
        logger.warning("Graph augmentation failed (continuing without): %s", exc)
    return ranked_files


def _build_index_health(repo_path: str, metadata: Any) -> dict[str, Any]:
    status = "unknown"
    stale_reason = None
    vcs = "none"

    if (Path(repo_path) / ".git").exists():
        vcs = "git"
        try:
            if metadata.is_stale(repo_path):
                status = "stale"
                stale_reason = "Repository files changed since index build"
            else:
                status = "current"
        except Exception:
            status = "unknown"

    return {
        "status": status,
        "stale_reason": stale_reason,
        "files_indexed": metadata.file_count,
        "index_built_at": metadata.created_at.replace(microsecond=0).isoformat() + "Z",
        "vcs": vcs,
    }


def _infer_domain(file_path: str, domain_map: Any) -> str:
    path_tokens = [token for token in Path(file_path).parts if token]
    for token in path_tokens:
        token_lower = token.lower()
        if token_lower in domain_map.keywords:
            return token_lower
    return "general"


def _build_summary(repo_path: str, file_path: str) -> str:
    full_path = Path(repo_path) / file_path
    if not full_path.exists():
        return ""

    try:
        with open(full_path, encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                return line[:140]
    except Exception:
        return ""

    return ""  # all lines were empty/comments


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_file_content(repo_path: str, file_path: str) -> str:
    full_path = Path(repo_path) / file_path
    try:
        with open(full_path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _graph_neighbors(graph: Any, file_path: str) -> tuple[list[str], list[str]]:
    graph_obj = getattr(graph, "graph", None)
    if graph_obj is None:
        return [], []

    try:
        if hasattr(graph, "_nx"):
            deps = sorted(str(x) for x in graph_obj.successors(file_path))
            dependents = sorted(str(x) for x in graph_obj.predecessors(file_path))
            return deps, dependents

        if hasattr(graph, "file_to_vertex") and hasattr(graph, "vertex_to_file"):
            vertex = graph.file_to_vertex.get(file_path)
            if vertex is None:
                return [], []
            deps = sorted(str(graph.vertex_to_file[v]) for v in graph_obj.successors(vertex))
            dependents = sorted(
                str(graph.vertex_to_file[v]) for v in graph_obj.predecessors(vertex)
            )
            return deps, dependents
    except Exception:
        return [], []

    return [], []


def _build_file_payload(
    repo_path: str,
    file_path: str,
    score: float,
    domain: str,
    summary: str,
    graph: Any,
    secret_scanner: SecretScanner | None,
    secrets_scan: bool,
    preloaded_content: str | None = None,
) -> dict[str, Any]:
    content: str | None = (
        preloaded_content
        if preloaded_content is not None
        else _read_file_content(repo_path, file_path)
    )
    scan_result = None
    if secrets_scan and secret_scanner is not None:
        scan_result = secret_scanner.scan(file_path)

    secrets_detected = scan_result.secrets_detected if scan_result else []
    secret_scan_skipped = False if scan_result else True
    if secrets_detected:
        content = None

    dependencies, dependents = _graph_neighbors(graph, file_path)

    return {
        "path": file_path,
        "score": round(float(score), 4),
        "domain": domain,
        "summary": summary,
        "content": content,
        "dependencies": dependencies,
        "dependents": dependents,
        "secrets_detected": secrets_detected,
        "secret_scan_skipped": secret_scan_skipped,
    }


@timed("search_codebase")
def search_codebase(
    repo_path: str,
    query: str,
    config: Config | None = None,
    limit: int = 10,
    domain_filter: str | None = None,
    index_dir: str = ".ws-ctx-engine",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not os.path.exists(repo_path):
        raise ValueError(f"Repository path does not exist: {repo_path}")

    if not os.path.isdir(repo_path):
        raise ValueError(f"Repository path is not a directory: {repo_path}")

    if config is None:
        config = Config.load()

    if limit < 1 or limit > 50:
        raise ValueError(f"limit must be in [1, 50], got {limit}")

    vector_index, graph, metadata = load_indexes(
        repo_path=repo_path,
        index_dir=index_dir,
        auto_rebuild=True,
        config=config,
    )

    domain_map_db_path = Path(repo_path) / index_dir / "domain_map.db"
    domain_map: Any
    try:
        domain_map = DomainMapDB(str(domain_map_db_path))
    except Exception:
        from ..domain_map import DomainKeywordMap

        domain_map = DomainKeywordMap()

    # Load BM25 index if available (built during `wsctx index`)
    bm25_index = None
    try:
        from ..retrieval.bm25_index import BM25Index

        bm25_path = str(Path(repo_path) / index_dir / "bm25.pkl")
        if Path(bm25_path).exists():
            bm25_index = BM25Index.load(bm25_path)
            logger.info(f"BM25 index loaded: {bm25_index.size} documents")
    except Exception as e:
        logger.warning(f"BM25 index load failed (continuing without): {e}")

    # Opt-in cross-encoder reranker
    reranker = None
    try:
        from ..retrieval.reranker import CrossEncoderReranker

        if CrossEncoderReranker.is_enabled():
            reranker = CrossEncoderReranker()
    except Exception as e:
        logger.warning(f"Reranker init failed (continuing without): {e}")

    retrieval_engine = RetrievalEngine(
        vector_index=vector_index,
        graph=graph,
        semantic_weight=config.semantic_weight,
        pagerank_weight=config.pagerank_weight,
        domain_map=domain_map,
        config=config,
        bm25_index=bm25_index,
        reranker=reranker,
    )

    ranked_files = retrieval_engine.retrieve(query=query, top_k=max(limit * 5, 50))

    # Phase 2.5: Graph augmentation (search_codebase path)
    if query and getattr(config, "context_assembler_enabled", True) and getattr(config, "graph_store_enabled", True):
        ranked_files = _apply_graph_augmentation(
            ranked_files, query, config, Path(repo_path) / index_dir
        )

    normalized_domain_filter = domain_filter.lower() if domain_filter else None
    results: list[dict[str, Any]] = []
    for file_path, score in ranked_files:
        inferred_domain = _infer_domain(file_path, domain_map)
        if normalized_domain_filter and inferred_domain != normalized_domain_filter:
            continue

        results.append(
            {
                "path": file_path,
                "score": round(float(score), 4),
                "domain": inferred_domain,
                "summary": _build_summary(repo_path, file_path),
            }
        )

        if len(results) >= limit:
            break

    if isinstance(domain_map, DomainMapDB):
        domain_map.close()

    return results, _build_index_health(repo_path, metadata)


def query_and_pack(
    repo_path: str,
    query: str | None = None,
    changed_files: list[str] | None = None,
    config: Config | None = None,
    index_dir: str = ".ws-ctx-engine",
    secrets_scan: bool = False,
    compress: bool = False,
    shuffle: bool = True,
    agent_phase: str | None = None,
    session_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Query indexes and generate output in configured format.

    This function implements the query phase workflow:
    1. Load indexes with auto-detection
    2. Retrieve candidates with hybrid ranking
    3. Select files within budget
    4. Pack output in configured format (XML or ZIP)

    Args:
        repo_path: Path to the repository root directory
        query: Optional natural language query for semantic search
        changed_files: Optional list of changed files for PageRank boosting
        config: Configuration instance (uses defaults if None)
        index_dir: Directory containing indexes (default: .ws-ctx-engine)

    Returns:
        Tuple of (output_path, PerformanceTracker with query metrics)

    Raises:
        FileNotFoundError: If indexes don't exist
        ValueError: If repo_path is invalid
        RuntimeError: If query phase fails

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 6.1, 7.1, 13.2, 13.3

    Example:
        >>> output_path, tracker = query_and_pack(
        ...     repo_path="/path/to/repo",
        ...     query="authentication logic",
        ...     changed_files=["src/auth.py"]
        ... )
        >>> print(f"Output generated: {output_path}")
        >>> print(tracker.format_metrics("query"))
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
    tracker.start_query()

    logger.info(f"Starting query phase for repository: {repo_path}")
    start_time = time.time()

    # Phase 1: Load indexes with auto-detection
    logger.info("Phase 1: Loading indexes")
    tracker.start_phase("index_loading")
    load_start = time.time()

    try:
        vector_index, graph, metadata = load_indexes(
            repo_path=repo_path,
            index_dir=index_dir,
            auto_rebuild=True,
            config=config,
        )
        load_duration = time.time() - load_start
        tracker.end_phase("index_loading")
        tracker.track_memory()

        logger.log_phase(
            phase="index_loading",
            duration=load_duration,
            backend=metadata.backend,
            file_count=metadata.file_count,
        )
    except FileNotFoundError as e:
        logger.error(f"Indexes not found: {e}")
        logger.info("Please run 'ws-ctx-engine index' first to build indexes")
        raise
    except Exception as e:
        logger.log_error(e, {"phase": "index_loading", "repo_path": repo_path})
        raise RuntimeError(f"Failed to load indexes: {e}") from e

    # Phase 2: Retrieve candidates with hybrid ranking
    logger.info("Phase 2: Retrieving candidates with hybrid ranking")
    tracker.start_phase("retrieval")
    retrieval_start = time.time()

    try:
        domain_map_db_path = Path(repo_path) / index_dir / "domain_map.db"
        domain_map: Any
        try:
            domain_map = DomainMapDB(str(domain_map_db_path))
            logger.info(f"Domain map DB loaded: {domain_map.stats()['keywords']} keywords")
        except Exception as e:
            logger.warning(f"Could not load domain map DB: {e}. Using empty domain map.")
            from ..domain_map import DomainKeywordMap

            domain_map = DomainKeywordMap()

        # Load BM25 index if available
        _bm25_index = None
        try:
            from ..retrieval.bm25_index import BM25Index

            _bm25_path = str(Path(repo_path) / index_dir / "bm25.pkl")
            if Path(_bm25_path).exists():
                _bm25_index = BM25Index.load(_bm25_path)
                logger.info(f"BM25 index loaded: {_bm25_index.size} documents")
        except Exception as _bm25_err:
            logger.warning(f"BM25 index load failed (continuing without): {_bm25_err}")

        # Opt-in cross-encoder reranker
        _reranker = None
        try:
            from ..retrieval.reranker import CrossEncoderReranker

            if CrossEncoderReranker.is_enabled():
                _reranker = CrossEncoderReranker()
        except Exception as _rnk_err:
            logger.warning(f"Reranker init failed (continuing without): {_rnk_err}")

        retrieval_engine = RetrievalEngine(
            vector_index=vector_index,
            graph=graph,
            semantic_weight=config.semantic_weight,
            pagerank_weight=config.pagerank_weight,
            domain_map=domain_map,
            config=config,
            bm25_index=_bm25_index,
            reranker=_reranker,
        )

        ranked_files = retrieval_engine.retrieve(
            query=query,
            changed_files=changed_files,
            top_k=100,
        )

        # Apply phase-aware re-weighting if --mode is specified
        if agent_phase:
            try:
                from ..ranking.phase_ranker import apply_phase_weights, parse_phase

                phase = parse_phase(agent_phase)
                if phase is not None:
                    ranked_files = apply_phase_weights(ranked_files, phase)
            except Exception as exc:
                logger.warning(f"Phase-aware ranking failed (ignored): {exc}")

        # Phase 2.5: Graph augmentation (query_and_pack path)
        if query and getattr(config, "context_assembler_enabled", True) and getattr(config, "graph_store_enabled", True):
            ranked_files = _apply_graph_augmentation(
                ranked_files, query, config, Path(repo_path) / index_dir
            )

        retrieval_duration = time.time() - retrieval_start
        tracker.end_phase("retrieval")
        tracker.track_memory()

        if not ranked_files:
            raise RuntimeError("No files retrieved from indexes")

        logger.log_phase(
            phase="retrieval", duration=retrieval_duration, files_ranked=len(ranked_files)
        )
    except Exception as e:
        logger.log_error(e, {"phase": "retrieval", "repo_path": repo_path})
        raise RuntimeError(f"Failed to retrieve candidates: {e}") from e

    # Phase 3: Select files within budget
    logger.info("Phase 3: Selecting files within token budget")
    tracker.start_phase("budget_selection")
    budget_start = time.time()

    try:
        budget_manager = BudgetManager(token_budget=config.token_budget)
        selected_files, total_tokens = budget_manager.select_files(
            ranked_files=ranked_files, repo_path=repo_path
        )
        budget_duration = time.time() - budget_start
        tracker.end_phase("budget_selection")
        tracker.track_memory()

        if not selected_files:
            raise RuntimeError("No files selected within budget")

        # Track query metrics
        tracker.set_files_selected(len(selected_files))
        tracker.set_total_tokens(total_tokens)

        logger.log_phase(
            phase="budget_selection",
            duration=budget_duration,
            files_selected=len(selected_files),
            total_tokens=total_tokens,
            budget_used_pct=f"{(total_tokens / budget_manager.content_budget) * 100:.1f}%",
        )
    except Exception as e:
        logger.log_error(e, {"phase": "budget_selection", "repo_path": repo_path})
        raise RuntimeError(f"Failed to select files within budget: {e}") from e

    # Phase 4: Pack output in configured format
    logger.info(f"Phase 4: Packing output in {config.format.upper()} format")
    tracker.start_phase("packing")
    pack_start = time.time()

    try:
        index_health = _build_index_health(repo_path, metadata)

        # Create output directory
        output_dir = Path(config.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        scanner = SecretScanner(repo_path=repo_path, index_dir=index_dir) if secrets_scan else None

        # --- Pre-processing: dedup + compression ---

        # Session deduplication — replace already-seen file content with markers
        dedup_cache = None
        if session_id is not None:
            try:
                from ..session.dedup_cache import SessionDeduplicationCache

                dedup_cache = SessionDeduplicationCache(
                    session_id=session_id,
                    cache_dir=Path(repo_path) / index_dir,
                )
                logger.info(
                    f"Session dedup cache loaded: {dedup_cache.size} entries (session={session_id})"
                )
            except Exception as exc:
                logger.warning(f"Session dedup cache init failed (ignored): {exc}")

        deduplicated_count = 0

        # Apply shuffle before compression so highest-ranked files get full content
        effective_files = list(selected_files)
        if shuffle and config.format == "xml":
            try:
                from ..packer.xml_packer import shuffle_for_model_recall

                effective_files = shuffle_for_model_recall(effective_files)
            except Exception as exc:
                logger.warning(f"Context shuffle failed (ignored): {exc}")

        # Build content map: file_path → (possibly compressed / deduplicated) content
        content_map: dict[str, str] = {}
        ranked_scores = dict(ranked_files)

        if compress or dedup_cache is not None:
            try:
                if compress:
                    from ..output.compressor import apply_compression_to_selected_files

                    compressed_pairs = apply_compression_to_selected_files(
                        selected_files=effective_files,
                        ranked_scores=ranked_scores,
                        repo_path=repo_path,
                    )
                    for fp, content in compressed_pairs:
                        content_map[fp] = content
                else:
                    for fp in effective_files:
                        content_map[fp] = _read_file_content(repo_path, fp)
            except Exception as exc:
                logger.warning(f"Pre-processing (compress/dedup) failed (ignored): {exc}")
                content_map = {}

            # Apply dedup over whatever content we have
            if dedup_cache is not None:
                for fp in list(content_map.keys()):
                    is_dup, result = dedup_cache.check_and_mark(fp, content_map[fp])
                    if is_dup:
                        deduplicated_count += 1
                        content_map[fp] = result

        if deduplicated_count:
            logger.info(f"Session dedup: {deduplicated_count} file(s) replaced with markers")

        # Prepare metadata (after dedup count is finalized for this phase)
        output_metadata = {
            "repo_name": os.path.basename(os.path.abspath(repo_path)),
            "file_count": len(selected_files),
            "total_tokens": total_tokens,
            "query": query,
            "changed_files": changed_files,
            "generated_at": _utc_now(),
            "index_health": index_health,
            "session_id": session_id,
            "deduplicated_files": deduplicated_count,
        }

        # Pack based on format
        if config.format == "xml":
            xml_packer = XMLPacker()
            xml_content: str = xml_packer.pack(
                selected_files=effective_files,
                repo_path=repo_path,
                metadata=output_metadata,
                secret_scanner=scanner,
                content_map=content_map if content_map else None,
            )
            output_content: str | bytes = xml_content

            output_path = output_dir / "repomix-output.xml"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

        elif config.format == "zip":
            zip_packer = ZIPPacker()
            importance_scores = dict(ranked_files)
            zip_content: bytes = zip_packer.pack(
                selected_files=effective_files,
                repo_path=repo_path,
                metadata=output_metadata,
                importance_scores=importance_scores,
                secret_scanner=scanner,
            )
            output_content = zip_content

            output_path = output_dir / "ws-ctx-engine.zip"
            with open(output_path, "wb") as f:
                f.write(zip_content)

        elif config.format in {"json", "md", "yaml", "toon"}:
            ranked_lookup = dict(ranked_files)
            domain_map_db_path = Path(repo_path) / index_dir / "domain_map.db"
            try:
                domain_map = DomainMapDB(str(domain_map_db_path))
            except Exception:
                from ..domain_map import DomainKeywordMap

                domain_map = DomainKeywordMap()

            files_payload = [
                _build_file_payload(
                    repo_path=repo_path,
                    file_path=file_path,
                    score=float(ranked_lookup.get(file_path, 0.0)),
                    domain=_infer_domain(file_path, domain_map),
                    summary=_build_summary(repo_path, file_path),
                    graph=graph,
                    secret_scanner=scanner,
                    secrets_scan=secrets_scan,
                    preloaded_content=content_map.get(file_path) if content_map else None,
                )
                for file_path in effective_files
            ]

            if isinstance(domain_map, DomainMapDB):
                domain_map.close()

            if config.format == "json":
                formatter: JSONFormatter | YAMLFormatter | TOONFormatter | MarkdownFormatter = (
                    JSONFormatter()
                )
                output_content = formatter.render(output_metadata, files_payload)
                output_path = output_dir / "ws-ctx-engine.json"
            elif config.format == "yaml":
                formatter = YAMLFormatter()
                output_content = formatter.render(output_metadata, files_payload)
                output_path = output_dir / "ws-ctx-engine.yaml"
            elif config.format == "toon":
                formatter = TOONFormatter()
                output_content = formatter.render(output_metadata, files_payload)
                output_path = output_dir / "ws-ctx-engine.toon"
            else:
                formatter = MarkdownFormatter()
                output_content = formatter.render(output_metadata, files_payload)
                output_path = output_dir / "ws-ctx-engine.md"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_content)

        else:
            raise ValueError(f"Unsupported format: {config.format}")

        pack_duration = time.time() - pack_start
        tracker.end_phase("packing")

        logger.log_phase(
            phase="packing",
            duration=pack_duration,
            format=config.format,
            output_path=str(output_path),
        )
    except Exception as e:
        logger.log_error(e, {"phase": "packing", "repo_path": repo_path})
        raise RuntimeError(f"Failed to pack output: {e}") from e

    # End query tracking
    tracker.end_query()

    # Log completion with metrics
    total_duration = time.time() - start_time
    logger.info(
        f"Query phase complete | total_duration={total_duration:.2f}s | " f"output={output_path}"
    )
    logger.info(f"\n{tracker.format_metrics('query')}")

    return str(output_path), {
        "total_tokens": total_tokens,
        "file_count": len(selected_files),
        "tracker": tracker,
    }
