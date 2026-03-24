"""
Retrieval Engine for Context Packer.

Combines semantic search and structural ranking (PageRank) to produce
hybrid importance scores for file selection.
"""

import logging
from typing import Dict, List, Optional, Tuple

from context_packer.graph import RepoMapGraph
from context_packer.vector_index import VectorIndex

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """
    Hybrid retrieval engine combining semantic and structural ranking.
    
    The RetrievalEngine merges semantic similarity scores from vector search
    with structural importance scores from PageRank to produce final importance
    scores for file selection.
    
    Attributes:
        vector_index: VectorIndex instance for semantic search
        graph: RepoMapGraph instance for structural ranking
        semantic_weight: Weight for semantic scores (default 0.6)
        pagerank_weight: Weight for PageRank scores (default 0.4)
    
    Example:
        >>> from context_packer.vector_index import create_vector_index
        >>> from context_packer.graph import create_graph
        >>> 
        >>> # Build indexes
        >>> vector_index = create_vector_index()
        >>> graph = create_graph()
        >>> vector_index.build(chunks)
        >>> graph.build(chunks)
        >>> 
        >>> # Create retrieval engine
        >>> engine = RetrievalEngine(
        ...     vector_index=vector_index,
        ...     graph=graph,
        ...     semantic_weight=0.6,
        ...     pagerank_weight=0.4
        ... )
        >>> 
        >>> # Retrieve files
        >>> results = engine.retrieve(
        ...     query="authentication logic",
        ...     changed_files=["src/auth.py"],
        ...     top_k=100
        ... )
    """
    
    def __init__(
        self,
        vector_index: VectorIndex,
        graph: RepoMapGraph,
        semantic_weight: float = 0.6,
        pagerank_weight: float = 0.4
    ):
        """
        Initialize RetrievalEngine with indexes and weights.
        
        Args:
            vector_index: VectorIndex instance for semantic search
            graph: RepoMapGraph instance for structural ranking
            semantic_weight: Weight for semantic scores (default 0.6)
            pagerank_weight: Weight for PageRank scores (default 0.4)
        
        Raises:
            ValueError: If weights are not in [0, 1] range or don't sum to 1.0
        """
        if not (0 <= semantic_weight <= 1):
            raise ValueError(f"semantic_weight must be in [0, 1], got {semantic_weight}")
        
        if not (0 <= pagerank_weight <= 1):
            raise ValueError(f"pagerank_weight must be in [0, 1], got {pagerank_weight}")
        
        if abs(semantic_weight + pagerank_weight - 1.0) > 0.001:
            raise ValueError(
                f"Weights must sum to 1.0, got {semantic_weight + pagerank_weight}"
            )
        
        self.vector_index = vector_index
        self.graph = graph
        self.semantic_weight = semantic_weight
        self.pagerank_weight = pagerank_weight
        
        logger.info(
            f"RetrievalEngine initialized with weights: "
            f"semantic={semantic_weight}, pagerank={pagerank_weight}"
        )
    
    def retrieve(
        self,
        query: Optional[str] = None,
        changed_files: Optional[List[str]] = None,
        top_k: int = 100
    ) -> List[Tuple[str, float]]:
        """
        Retrieve files with hybrid importance scores.
        
        Combines semantic search results with PageRank scores using configured
        weights. Both score types are normalized to [0, 1] range before merging.
        
        Args:
            query: Optional natural language query for semantic search
            changed_files: Optional list of changed files for PageRank boosting
            top_k: Maximum number of results to return (default 100)
        
        Returns:
            List of (file_path, importance_score) tuples sorted by score descending
        
        Example:
            >>> results = engine.retrieve(
            ...     query="authentication logic",
            ...     changed_files=["src/auth.py"],
            ...     top_k=50
            ... )
            >>> for file_path, score in results[:5]:
            ...     print(f"{file_path}: {score:.3f}")
            src/auth.py: 0.892
            src/user.py: 0.745
            src/session.py: 0.623
        """
        logger.info(
            f"Starting retrieval: query={'<provided>' if query else '<none>'}, "
            f"changed_files={len(changed_files) if changed_files else 0}, "
            f"top_k={top_k}"
        )
        
        # 1. Get semantic scores
        semantic_scores: Dict[str, float] = {}
        if query:
            try:
                semantic_results = self.vector_index.search(query, top_k)
                semantic_scores = dict(semantic_results)
                logger.info(f"Semantic search returned {len(semantic_scores)} results")
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}, continuing with PageRank only")
        
        # 2. Get PageRank scores
        pagerank_scores: Dict[str, float] = {}
        try:
            pagerank_scores = self.graph.pagerank(changed_files)
            logger.info(f"PageRank computed for {len(pagerank_scores)} files")
        except Exception as e:
            logger.warning(f"PageRank computation failed: {e}, continuing with semantic only")
        
        # 3. Normalize both to [0, 1]
        semantic_normalized = self._normalize(semantic_scores)
        pagerank_normalized = self._normalize(pagerank_scores)
        
        # 4. Merge with weights
        merged = self._merge_scores(
            semantic_normalized,
            pagerank_normalized
        )
        
        # 5. Sort by score descending
        results = sorted(merged.items(), key=lambda x: x[1], reverse=True)
        
        logger.info(f"Retrieval complete: {len(results)} files ranked")
        
        return results[:top_k]
    
    def _normalize(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize scores to [0, 1] range using min-max normalization.
        
        If all scores are equal or there's only one score, returns all 1.0.
        If scores dict is empty, returns empty dict.
        
        Args:
            scores: Dictionary mapping file paths to raw scores
        
        Returns:
            Dictionary mapping file paths to normalized scores in [0, 1]
        
        Example:
            >>> engine._normalize({"a.py": 0.5, "b.py": 1.0, "c.py": 0.0})
            {'a.py': 0.5, 'b.py': 1.0, 'c.py': 0.0}
        """
        if not scores:
            return {}
        
        values = list(scores.values())
        min_score = min(values)
        max_score = max(values)
        
        # If all scores are equal, return all 1.0
        if max_score - min_score < 1e-9:
            return {file: 1.0 for file in scores}
        
        # Min-max normalization
        normalized = {
            file: (score - min_score) / (max_score - min_score)
            for file, score in scores.items()
        }
        
        return normalized
    
    def _merge_scores(
        self,
        semantic_scores: Dict[str, float],
        pagerank_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Merge normalized semantic and PageRank scores using configured weights.
        
        For files present in both score dicts, computes weighted sum.
        For files present in only one dict, uses that score with appropriate weight.
        
        Args:
            semantic_scores: Normalized semantic similarity scores
            pagerank_scores: Normalized PageRank scores
        
        Returns:
            Dictionary mapping file paths to merged importance scores
        
        Example:
            >>> semantic = {"a.py": 0.8, "b.py": 0.6}
            >>> pagerank = {"a.py": 0.5, "c.py": 0.9}
            >>> engine._merge_scores(semantic, pagerank)
            {'a.py': 0.68, 'b.py': 0.36, 'c.py': 0.36}
        """
        # Get all unique files
        all_files = set(semantic_scores.keys()) | set(pagerank_scores.keys())
        
        merged = {}
        for file in all_files:
            semantic_score = semantic_scores.get(file, 0.0)
            pagerank_score = pagerank_scores.get(file, 0.0)
            
            # Weighted sum
            importance_score = (
                self.semantic_weight * semantic_score +
                self.pagerank_weight * pagerank_score
            )
            
            merged[file] = importance_score
        
        return merged
