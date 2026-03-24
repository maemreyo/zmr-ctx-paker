"""
Query phase workflow for Context Packer.

Provides functions for querying indexes and generating output in XML or ZIP format.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from .budget import BudgetManager
from .config import Config
from .indexer import load_indexes
from .logger import get_logger
from .performance import PerformanceTracker
from .retrieval import RetrievalEngine
from .packer import XMLPacker, ZIPPacker

logger = get_logger()


def query_and_pack(
    repo_path: str,
    query: Optional[str] = None,
    changed_files: Optional[List[str]] = None,
    config: Optional[Config] = None,
    index_dir: str = ".context-pack"
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
        index_dir: Directory containing indexes (default: .context-pack)
    
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
        logger.info("Please run 'context-pack index' first to build indexes")
        raise
    except Exception as e:
        logger.log_error(e, {"phase": "index_loading", "repo_path": repo_path})
        raise RuntimeError(f"Failed to load indexes: {e}") from e
    
    # Phase 2: Retrieve candidates with hybrid ranking
    logger.info("Phase 2: Retrieving candidates with hybrid ranking")
    tracker.start_phase("retrieval")
    retrieval_start = time.time()
    
    try:
        retrieval_engine = RetrievalEngine(
            vector_index=vector_index,
            graph=graph,
            semantic_weight=config.semantic_weight,
            pagerank_weight=config.pagerank_weight
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
        # Prepare metadata
        output_metadata = {
            "repo_name": os.path.basename(os.path.abspath(repo_path)),
            "file_count": len(selected_files),
            "total_tokens": total_tokens,
            "query": query,
            "changed_files": changed_files
        }
        
        # Create output directory
        output_dir = Path(config.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Pack based on format
        if config.format == "xml":
            packer = XMLPacker()
            output_content = packer.pack(
                selected_files=selected_files,
                repo_path=repo_path,
                metadata=output_metadata
            )
            
            # Write XML to file
            output_path = output_dir / "repomix-output.xml"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
        
        else:  # zip
            packer = ZIPPacker()
            importance_scores = dict(ranked_files)
            output_content = packer.pack(
                selected_files=selected_files,
                repo_path=repo_path,
                metadata=output_metadata,
                importance_scores=importance_scores
            )
            
            # Write ZIP to file
            output_path = output_dir / "context-pack.zip"
            with open(output_path, 'wb') as f:
                f.write(output_content)
        
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
