"""
Query phase workflow for ws-ctx-engine.

Provides functions for querying indexes and generating output in XML or ZIP format.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..budget import BudgetManager
from ..config import Config
from ..domain_map import DomainMapDB
from .indexer import load_indexes
from ..logger import get_logger
from ..monitoring import PerformanceTracker
from ..output import JSONFormatter, MarkdownFormatter
from ..retrieval import RetrievalEngine
from ..packer import XMLPacker, ZIPPacker
from ..secret_scanner import SecretScanner

logger = get_logger()


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
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                return line[:140]
    except Exception:
        return ""

    return ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_file_content(repo_path: str, file_path: str) -> str:
    full_path = Path(repo_path) / file_path
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
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
            dependents = sorted(str(graph.vertex_to_file[v]) for v in graph_obj.predecessors(vertex))
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
    secret_scanner: Optional[SecretScanner],
    secrets_scan: bool,
) -> dict[str, Any]:
    content = _read_file_content(repo_path, file_path)
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


def search_codebase(
    repo_path: str,
    query: str,
    config: Optional[Config] = None,
    limit: int = 10,
    domain_filter: Optional[str] = None,
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
    )

    domain_map_db_path = Path(repo_path) / index_dir / "domain_map.db"
    domain_map: Any
    try:
        domain_map = DomainMapDB(str(domain_map_db_path))
    except Exception:
        from ..domain_map import DomainKeywordMap
        domain_map = DomainKeywordMap()

    retrieval_engine = RetrievalEngine(
        vector_index=vector_index,
        graph=graph,
        semantic_weight=config.semantic_weight,
        pagerank_weight=config.pagerank_weight,
        domain_map=domain_map,
    )

    ranked_files = retrieval_engine.retrieve(query=query, top_k=max(limit * 5, 50))

    normalized_domain_filter = domain_filter.lower() if domain_filter else None
    results: list[dict[str, Any]] = []
    for file_path, score in ranked_files:
        inferred_domain = _infer_domain(file_path, domain_map)
        if normalized_domain_filter and inferred_domain != normalized_domain_filter:
            continue

        results.append({
            "path": file_path,
            "score": round(float(score), 4),
            "domain": inferred_domain,
            "summary": _build_summary(repo_path, file_path),
        })

        if len(results) >= limit:
            break

    if isinstance(domain_map, DomainMapDB):
        domain_map.close()

    return results, _build_index_health(repo_path, metadata)


def query_and_pack(
    repo_path: str,
    query: Optional[str] = None,
    changed_files: Optional[List[str]] = None,
    config: Optional[Config] = None,
    index_dir: str = ".ws-ctx-engine",
    secrets_scan: bool = False,
) -> tuple[str, PerformanceTracker]:
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
            auto_rebuild=True
        )
        load_duration = time.time() - load_start
        tracker.end_phase("index_loading")
        tracker.track_memory()
        
        logger.log_phase(
            phase="index_loading",
            duration=load_duration,
            backend=metadata.backend,
            file_count=metadata.file_count
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
        try:
            domain_map = DomainMapDB(str(domain_map_db_path))
            logger.info(f"Domain map DB loaded: {domain_map.stats()['keywords']} keywords")
        except Exception as e:
            logger.warning(f"Could not load domain map DB: {e}. Using empty domain map.")
            from ..domain_map import DomainKeywordMap
            domain_map = DomainKeywordMap()

        retrieval_engine = RetrievalEngine(
            vector_index=vector_index,
            graph=graph,
            semantic_weight=config.semantic_weight,
            pagerank_weight=config.pagerank_weight,
            domain_map=domain_map
        )

        ranked_files = retrieval_engine.retrieve(
            query=query,
            changed_files=changed_files,
            top_k=100
        )
        retrieval_duration = time.time() - retrieval_start
        tracker.end_phase("retrieval")
        tracker.track_memory()

        if not ranked_files:
            raise RuntimeError("No files retrieved from indexes")

        logger.log_phase(
            phase="retrieval",
            duration=retrieval_duration,
            files_ranked=len(ranked_files)
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
            ranked_files=ranked_files,
            repo_path=repo_path
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
            budget_used_pct=f"{(total_tokens / budget_manager.content_budget) * 100:.1f}%"
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

        # Prepare metadata
        output_metadata = {
            "repo_name": os.path.basename(os.path.abspath(repo_path)),
            "file_count": len(selected_files),
            "total_tokens": total_tokens,
            "query": query,
            "changed_files": changed_files,
            "generated_at": _utc_now(),
            "index_health": index_health,
        }

        # Create output directory
        output_dir = Path(config.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        scanner = SecretScanner(repo_path=repo_path, index_dir=index_dir) if secrets_scan else None

        # Pack based on format
        if config.format == "xml":
            packer = XMLPacker()
            output_content = packer.pack(
                selected_files=selected_files,
                repo_path=repo_path,
                metadata=output_metadata,
                secret_scanner=scanner,
            )

            output_path = output_dir / "repomix-output.xml"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)

        elif config.format == "zip":
            packer = ZIPPacker()
            importance_scores = dict(ranked_files)
            output_content = packer.pack(
                selected_files=selected_files,
                repo_path=repo_path,
                metadata=output_metadata,
                importance_scores=importance_scores,
                secret_scanner=scanner,
            )

            output_path = output_dir / "ws-ctx-engine.zip"
            with open(output_path, 'wb') as f:
                f.write(output_content)

        elif config.format in {"json", "md"}:
            ranked_lookup = dict(ranked_files)
            domain_map_db_path = Path(repo_path) / index_dir / "domain_map.db"
            domain_map: Any
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
                )
                for file_path in selected_files
            ]

            if isinstance(domain_map, DomainMapDB):
                domain_map.close()

            if config.format == "json":
                formatter = JSONFormatter()
                output_content = formatter.render(output_metadata, files_payload)
                output_path = output_dir / "ws-ctx-engine.json"
            else:
                formatter = MarkdownFormatter()
                output_content = formatter.render(output_metadata, files_payload)
                output_path = output_dir / "ws-ctx-engine.md"

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)

        else:
            raise ValueError(f"Unsupported format: {config.format}")
        
        pack_duration = time.time() - pack_start
        tracker.end_phase("packing")
        
        logger.log_phase(
            phase="packing",
            duration=pack_duration,
            format=config.format,
            output_path=str(output_path)
        )
    except Exception as e:
        logger.log_error(e, {"phase": "packing", "repo_path": repo_path})
        raise RuntimeError(f"Failed to pack output: {e}") from e
    
    # End query tracking
    tracker.end_query()
    
    # Log completion with metrics
    total_duration = time.time() - start_time
    logger.info(
        f"Query phase complete | total_duration={total_duration:.2f}s | "
        f"output={output_path}"
    )
    logger.info(f"\n{tracker.format_metrics('query')}")
    
    return str(output_path), tracker
