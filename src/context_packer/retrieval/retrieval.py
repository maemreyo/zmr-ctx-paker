"""
Retrieval Engine for Context Packer.

Combines semantic search and structural ranking (PageRank) to produce
hybrid importance scores for file selection.

Additional signals applied on top of the base hybrid score:
  - Symbol-based exact matching: boosts files whose defined symbols match
    identifier tokens extracted from the query.
  - File path scoring: boosts files whose path contains query keywords.
  - Domain scoring: boosts files in directories matching discovered domain keywords.
  - Test file penalty: reduces scores for files that look like test files.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from context_packer.graph import RepoMapGraph
from context_packer.vector_index import VectorIndex

logger = logging.getLogger(__name__)


class DomainKeywordMap:
    """Lightweight domain keyword to directory mapping for query classification."""
    def __init__(self):
        self._keyword_to_dirs: Dict[str, Set[str]] = {}

    def load(self, path: str) -> None:
        import pickle
        from pathlib import Path
        if Path(path).exists():
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self._keyword_to_dirs = {k: set(v) for k, v in data.items()}

    @property
    def keywords(self) -> Set[str]:
        return set(self._keyword_to_dirs.keys())

    def directories_for(self, keyword: str) -> List[str]:
        return list(self._keyword_to_dirs.get(keyword.lower(), set()))

    def keyword_matches(self, token: str) -> bool:
        token_lower = token.lower()
        if token_lower in self._keyword_to_dirs:
            return True
        for kw in self._keyword_to_dirs:
            prefix_len = min(5, len(token_lower), len(kw))
            if prefix_len >= 4 and token_lower[:prefix_len] == kw[:prefix_len]:
                return True
        return False

# Words that carry no semantic signal when matching against file paths or symbols.
_STOP_WORDS: frozenset = frozenset({
    'the', 'a', 'an', 'in', 'for', 'of', 'and', 'or', 'is', 'are', 'how',
    'does', 'what', 'where', 'show', 'me', 'find', 'get', 'use', 'uses',
    'used', 'to', 'from', 'with', 'this', 'that', 'it', 'its', 'by', 'be',
    'do', 'did', 'has', 'have', 'not', 'can', 'all', 'any', 'my', 'our',
    'which', 'when', 'then', 'there', 'their', 'about', 'into', 'should',
    'would', 'could', 'will', 'may', 'might', 'was', 'were', 'been', 'being',
    'just', 'also', 'more', 'like', 'than', 'but', 'so', 'if', 'at', 'on',
})

# Regex patterns that identify test files (matched against the full file path).
_TEST_FILE_PATTERNS: List[re.Pattern] = [
    re.compile(r'(^|/)tests?/', re.IGNORECASE),
    re.compile(r'(^|/)test_', re.IGNORECASE),
    re.compile(r'_test\.(py|js|ts|rs)$', re.IGNORECASE),
    re.compile(r'\.spec\.(js|ts)$', re.IGNORECASE),
]


class RetrievalEngine:
    """
    Hybrid retrieval engine combining semantic and structural ranking.

    The RetrievalEngine merges semantic similarity scores from vector search
    with structural importance scores from PageRank to produce base importance
    scores, then applies three additional signals:

    1. **Symbol boost**: files that *define* identifiers mentioned in the query
       receive a bonus (``symbol_boost`` weight).
    2. **Path boost**: files whose path contains query keywords receive a bonus
       (``path_boost`` weight).
    3. **Test penalty**: files that look like test files have their scores
       scaled down by ``(1 - test_penalty)``.

    All final scores are min-max normalised to [0, 1] before being returned.

    Attributes:
        vector_index: VectorIndex instance for semantic search
        graph: RepoMapGraph instance for structural ranking
        semantic_weight: Weight for semantic scores (default 0.6)
        pagerank_weight: Weight for PageRank scores (default 0.4)
        symbol_boost: Additive weight applied to exact symbol matches (default 0.3)
        path_boost: Additive weight applied to path keyword matches (default 0.2)
        test_penalty: Multiplicative penalty for test files, in [0, 1] (default 0.5)

    Example:
        >>> from context_packer.vector_index import create_vector_index
        >>> from context_packer.graph import create_graph
        >>>
        >>> vector_index = create_vector_index()
        >>> graph = create_graph()
        >>> vector_index.build(chunks)
        >>> graph.build(chunks)
        >>>
        >>> engine = RetrievalEngine(
        ...     vector_index=vector_index,
        ...     graph=graph,
        ...     semantic_weight=0.6,
        ...     pagerank_weight=0.4,
        ...     symbol_boost=0.3,
        ...     path_boost=0.2,
        ...     test_penalty=0.5,
        ... )
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
        pagerank_weight: float = 0.4,
        symbol_boost: float = 0.3,
        path_boost: float = 0.2,
        domain_boost: float = 0.4,
        test_penalty: float = 0.5,
        domain_map: Optional["DomainKeywordMap"] = None,
    ):
        """
        Initialize RetrievalEngine with indexes and weights.

        Args:
            vector_index: VectorIndex instance for semantic search
            graph: RepoMapGraph instance for structural ranking
            semantic_weight: Weight for semantic scores (default 0.6)
            pagerank_weight: Weight for PageRank scores (default 0.4)
            symbol_boost: Additive weight for exact symbol matches (default 0.3)
            path_boost: Additive weight for path keyword matches (default 0.2)
            test_penalty: Score scale-down for test files, in [0, 1] (default 0.5)

        Raises:
            ValueError: If semantic/pagerank weights are not in [0, 1] or don't sum to 1.0
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
        self.symbol_boost = symbol_boost
        self.path_boost = path_boost
        self.domain_boost = domain_boost
        self.domain_map = domain_map if domain_map is not None else DomainKeywordMap()
        self.test_penalty = test_penalty

        logger.info(
            f"RetrievalEngine initialized with weights: "
            f"semantic={semantic_weight}, pagerank={pagerank_weight}, "
            f"symbol_boost={symbol_boost}, path_boost={path_boost}, "
            f"domain_boost={domain_boost}, test_penalty={test_penalty}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: Optional[str] = None,
        changed_files: Optional[List[str]] = None,
        top_k: int = 100,
    ) -> List[Tuple[str, float]]:
        """
        Retrieve files with hybrid importance scores.

        Combines semantic search results with PageRank scores, then applies
        symbol-match boosting, path-keyword boosting, and test-file penalty.
        Final scores are min-max normalised to [0, 1].

        Args:
            query: Optional natural language query for semantic search
            changed_files: Optional list of changed files for PageRank boosting
            top_k: Maximum number of results to return (default 100)

        Returns:
            List of (file_path, importance_score) tuples sorted by score descending,
            with scores in [0, 1].

        Example:
            >>> results = engine.retrieve(
            ...     query="authentication logic",
            ...     changed_files=["src/auth.py"],
            ...     top_k=50
            ... )
            >>> for file_path, score in results[:5]:
            ...     print(f"{file_path}: {score:.3f}")
            src/auth.py: 1.000
            src/user.py: 0.812
            src/session.py: 0.654
        """
        logger.info(
            f"Starting retrieval: query={'<provided>' if query else '<none>'}, "
            f"changed_files={len(changed_files) if changed_files else 0}, "
            f"top_k={top_k}"
        )

        # 1. Semantic scores
        semantic_scores: Dict[str, float] = {}
        if query:
            try:
                semantic_results = self.vector_index.search(query, top_k)
                semantic_scores = dict(semantic_results)
                logger.info(f"Semantic search returned {len(semantic_scores)} results")
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}, continuing with PageRank only")

        # 2. PageRank scores
        pagerank_scores: Dict[str, float] = {}
        try:
            pagerank_scores = self.graph.pagerank(changed_files)
            logger.info(f"PageRank computed for {len(pagerank_scores)} files")
        except Exception as e:
            logger.warning(f"PageRank computation failed: {e}, continuing with semantic only")

        # 3. Normalise and merge base scores
        semantic_normalized = self._normalize(semantic_scores)
        pagerank_normalized = self._normalize(pagerank_scores)
        merged = self._merge_scores(semantic_normalized, pagerank_normalized)

        # 4. Apply additional signals when a query is available
        if query:
            tokens = self._extract_query_tokens(query)

            # Classify query type for adaptive boosting
            query_type = self._classify_query(query, tokens)

            # Effective boost weights per query type
            eff_symbol, eff_path, eff_domain = self._effective_weights(query_type)

            # Symbol boost
            if tokens and eff_symbol > 0:
                file_symbols = self.vector_index.get_file_symbols()
                symbol_scores = self._compute_symbol_scores(tokens, file_symbols)
                for file_path, score in symbol_scores.items():
                    merged[file_path] = merged.get(file_path, 0.0) + eff_symbol * score

            # Path boost
            if tokens and eff_path > 0:
                all_files: Set[str] = set(merged.keys())
                path_scores = self._compute_path_scores(tokens, all_files)
                for file_path, score in path_scores.items():
                    merged[file_path] = merged.get(file_path, 0.0) + eff_path * score

            # Domain boost
            if tokens and eff_domain > 0:
                all_files: Set[str] = set(merged.keys())
                domain_scores = self._compute_domain_scores(tokens, all_files)
                for file_path, score in domain_scores.items():
                    merged[file_path] = merged.get(file_path, 0.0) + eff_domain * score

            logger.info(f"Query type: {query_type}, effective weights: symbol={eff_symbol:.2f}, path={eff_path:.2f}, domain={eff_domain:.2f}")

        # 5. Test file penalty
        if self.test_penalty > 0:
            for file_path in list(merged.keys()):
                if self._is_test_file(file_path):
                    merged[file_path] *= (1.0 - self.test_penalty)

        # 6. Final normalisation → guarantees scores ∈ [0, 1]
        final_scores = self._normalize(merged)

        results = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        logger.info(f"Retrieval complete: {len(results)} files ranked")
        return results[:top_k]

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _extract_query_tokens(self, query: str) -> Set[str]:
        """Extract meaningful identifier-like tokens from a query string.

        Splits on non-alphanumeric characters, lower-cases, and removes
        stop words and tokens shorter than 3 characters.

        Args:
            query: Natural language or code query string

        Returns:
            Set of lowercase token strings
        """
        raw = set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', query))
        return {t.lower() for t in raw if len(t) >= 3 and t.lower() not in _STOP_WORDS}

    def _compute_symbol_scores(
        self,
        tokens: Set[str],
        file_symbols: Dict[str, List[str]],
    ) -> Dict[str, float]:
        """Score files by exact overlap between query tokens and defined symbols.

        Args:
            tokens: Lowercase token set extracted from the query
            file_symbols: Mapping of file_path -> list of symbol names defined there

        Returns:
            Dict of file_path -> score in [0, 1]; only files with ≥1 match included.
        """
        if not tokens or not file_symbols:
            return {}

        scores: Dict[str, float] = {}
        for file_path, symbols in file_symbols.items():
            symbol_set = {s.lower() for s in symbols}
            matches = sum(1 for t in tokens if t in symbol_set)
            if matches:
                scores[file_path] = matches / len(tokens)

        return scores

    def _compute_path_scores(
        self,
        tokens: Set[str],
        all_files: Set[str],
    ) -> Dict[str, float]:
        """Score files by how many query tokens appear in their file path.

        Splits each path on common separators (``/``, ``_``, ``-``, ``.``)
        and checks for matches using three strategies (in order):

        1. **Exact match**: token equals a path part (e.g. ``"python"`` → ``python.py``).
        2. **Substring**: token is contained within a longer path part
           (e.g. ``"auth"`` matches path part ``"authenticate"``).
        3. **Shared prefix ≥ 5 chars**: both token and path part share the same
           first 5 characters (e.g. ``"chunking"`` matches ``"chunker"`` via
           the shared stem ``"chunk"``).

        Args:
            tokens: Lowercase token set extracted from the query
            all_files: All file paths to score

        Returns:
            Dict of file_path -> score in [0, 1]; only files with ≥1 match included.
        """
        if not tokens or not all_files:
            return {}

        def _token_matches(token: str, path_parts: Set[str]) -> bool:
            for part in path_parts:
                if not part:
                    continue
                # 1. Exact match
                if token == part:
                    return True
                # 2. Token is a substring of path part (e.g. "auth" in "authenticate")
                if len(part) >= 4 and token in part:
                    return True
                # 3. Shared 5-char prefix stem (e.g. "chunking"/"chunker" → "chunk")
                prefix_len = min(5, len(token), len(part))
                if prefix_len >= 5 and token[:prefix_len] == part[:prefix_len]:
                    return True
            return False

        scores: Dict[str, float] = {}
        for file_path in all_files:
            path_parts = set(re.split(r'[/_\-.]', file_path.lower()))
            matches = sum(1 for t in tokens if _token_matches(t, path_parts))
            if matches:
                scores[file_path] = min(1.0, matches / len(tokens))

        return scores

    def _classify_query(self, query: str, tokens: Set[str]) -> str:
        """
        Classify query into one of three types for adaptive boosting.

        Args:
            query: Original query string
            tokens: Extracted lowercase tokens

        Returns:
            "symbol" | "path-dominant" | "semantic-dominant"
        """
        import re

        # 1. Path-dominant FIRST: check if any token matches domain keywords
        # This takes priority over symbol detection to avoid "Show" or "Chunking"
        # from being classified as symbol when domain terms are present
        for token in tokens:
            if self.domain_map.keyword_matches(token):
                return "path-dominant"

        # 2. Symbol: PascalCase or snake_case identifier
        # Only check if no domain keywords matched
        if re.search(r'\b[A-Z][a-z]+[A-Z]', query):
            return "symbol"
        if any('_' in t and len(t) > 4 for t in tokens):
            return "symbol"

        # 3. Default
        return "semantic-dominant"

    def _effective_weights(self, query_type: str) -> Tuple[float, float, float]:
        """
        Return effective (symbol, path, domain) boost weights for query type.

        Per the design spec:
        | Query type       | symbol | path | domain |
        |------------------|--------|------|--------|
        | symbol           | 1.5    | 0.5  | 0.3    |
        | path-dominant    | 0.5    | 1.5  | 1.0    |
        | semantic-dominant| 0.2    | 0.2  | 0.2    |
        """
        multipliers = {
            "symbol": (1.5, 0.5, 0.3),
            "path-dominant": (0.5, 1.5, 1.0),
            "semantic-dominant": (0.2, 0.2, 0.2),
        }
        sym_mul, path_mul, dom_mul = multipliers.get(query_type, (0.2, 0.2, 0.2))
        return (
            self.symbol_boost * sym_mul,
            self.path_boost * path_mul,
            self.domain_boost * dom_mul,
        )

    def _compute_domain_scores(
        self,
        tokens: Set[str],
        all_files: Set[str],
    ) -> Dict[str, float]:
        """
        Score files by whether they are in directories matching domain keywords.

        Files under a matched directory get score 1.0, others get 0.0.

        Args:
            tokens: Lowercase token set extracted from the query
            all_files: All file paths to score

        Returns:
            Dict of file_path -> score in {0.0, 1.0}
        """
        if not tokens or not self.domain_map.keywords:
            return {}

        matched_dirs = set()
        for token in tokens:
            for kw in self.domain_map.keywords:
                prefix_len = min(5, len(token), len(kw))
                if token == kw or (prefix_len >= 4 and token[:prefix_len] == kw[:prefix_len]):
                    matched_dirs.update(self.domain_map.directories_for(kw))

        if not matched_dirs:
            return {}

        return {
            fp: 1.0
            for fp in all_files
            if any(fp.startswith(d) for d in matched_dirs)
        }

    def _is_test_file(self, file_path: str) -> bool:
        """Return True if *file_path* looks like a test/spec file."""
        return any(p.search(file_path) for p in _TEST_FILE_PATTERNS)

    # ------------------------------------------------------------------
    # Normalisation and merging (unchanged from original implementation)
    # ------------------------------------------------------------------

    def _normalize(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Normalise scores to [0, 1] using min-max normalisation.

        If all scores are equal or there is only one score, returns all 1.0.
        If *scores* is empty, returns an empty dict.

        Args:
            scores: Dictionary mapping file paths to raw scores

        Returns:
            Dictionary mapping file paths to normalised scores in [0, 1]

        Example:
            >>> engine._normalize({"a.py": 0.5, "b.py": 1.0, "c.py": 0.0})
            {'a.py': 0.5, 'b.py': 1.0, 'c.py': 0.0}
        """
        if not scores:
            return {}

        values = list(scores.values())
        min_score = min(values)
        max_score = max(values)

        if max_score - min_score < 1e-9:
            return {file: 1.0 for file in scores}

        return {
            file: (score - min_score) / (max_score - min_score)
            for file, score in scores.items()
        }

    def _merge_scores(
        self,
        semantic_scores: Dict[str, float],
        pagerank_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Merge normalised semantic and PageRank scores using configured weights.

        For files present in both dicts: weighted sum.
        For files present in only one dict: that score × its weight.

        Args:
            semantic_scores: Normalised semantic similarity scores
            pagerank_scores: Normalised PageRank scores

        Returns:
            Dictionary mapping file paths to merged importance scores

        Example:
            >>> semantic = {"a.py": 0.8, "b.py": 0.6}
            >>> pagerank = {"a.py": 0.5, "c.py": 0.9}
            >>> engine._merge_scores(semantic, pagerank)
            {'a.py': 0.68, 'b.py': 0.36, 'c.py': 0.36}
        """
        all_files = set(semantic_scores.keys()) | set(pagerank_scores.keys())

        return {
            file: (
                self.semantic_weight * semantic_scores.get(file, 0.0)
                + self.pagerank_weight * pagerank_scores.get(file, 0.0)
            )
            for file in all_files
        }
