"""
RepoMap Graph implementation for ws-ctx-engine.

Builds dependency graphs from symbol references and computes PageRank scores
for structural importance ranking.
"""

import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from ..logger import get_logger
from ..models import CodeChunk

logger = get_logger()


class RepoMapGraph(ABC):
    """
    Abstract base class for dependency graph and PageRank computation.
    
    Implementations must build directed dependency graphs from symbol references
    and compute PageRank scores for structural importance ranking.
    """
    
    @abstractmethod
    def build(self, chunks: List[CodeChunk]) -> None:
        """
        Build dependency graph from code chunks.
        
        Creates a directed graph where:
        - Nodes represent files
        - Edges represent symbol dependencies (file A imports/calls symbols from file B)
        
        Args:
            chunks: List of CodeChunk objects with symbol definitions and references
            
        Raises:
            ValueError: If chunks list is empty
            RuntimeError: If graph construction fails
        """
        pass
    
    @abstractmethod
    def pagerank(self, changed_files: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Compute PageRank scores for all files in the graph.
        
        PageRank scores indicate structural importance based on dependency relationships.
        If changed_files are provided, their scores are boosted by a configurable factor.
        
        Args:
            changed_files: Optional list of file paths that have changed (for score boosting)
            
        Returns:
            Dictionary mapping file paths to PageRank scores (sum to 1.0)
            
        Raises:
            RuntimeError: If PageRank computation fails
            ValueError: If graph has not been built yet
        """
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """
        Persist graph to disk for incremental indexing.
        
        Args:
            path: File path to save the graph
            
        Raises:
            IOError: If save operation fails
        """
        pass
    
    @classmethod
    @abstractmethod
    def load(cls, path: str) -> 'RepoMapGraph':
        """
        Load graph from disk.
        
        Args:
            path: File path to load the graph from
            
        Returns:
            Loaded RepoMapGraph instance
            
        Raises:
            IOError: If load operation fails
            ValueError: If file format is invalid
        """
        pass



class IGraphRepoMap(RepoMapGraph):
    """
    Primary RepoMap Graph implementation using python-igraph (C++ backend).
    
    Provides fast PageRank computation (<1 second for 10k nodes) using igraph's
    C++ backend. Falls back to NetworkX if igraph is unavailable.
    """
    
    def __init__(self, boost_factor: float = 2.0):
        """
        Initialize IGraphRepoMap.
        
        Args:
            boost_factor: Multiplier for changed file scores (default: 2.0)
            
        Raises:
            ImportError: If python-igraph is not installed
        """
        try:
            import igraph as ig
            self._ig = ig
        except ImportError as e:
            raise ImportError(
                "python-igraph is not installed. "
                "Install with: pip install python-igraph"
            ) from e
        
        self.boost_factor = boost_factor
        self.graph: Optional['ig.Graph'] = None
        self.file_to_vertex: Dict[str, int] = {}
        self.vertex_to_file: Dict[int, str] = {}
    
    def build(self, chunks: List[CodeChunk]) -> None:
        """
        Build directed dependency graph from code chunks using igraph.
        
        Creates a directed graph where edges represent symbol dependencies.
        File A -> File B means A imports or calls symbols defined in B.
        
        Args:
            chunks: List of CodeChunk objects with symbol definitions and references
            
        Raises:
            ValueError: If chunks list is empty
            RuntimeError: If graph construction fails
        """
        if not chunks:
            raise ValueError("Cannot build graph from empty chunks list")
        
        try:
            # Build symbol definition map: symbol -> file path
            symbol_to_file: Dict[str, str] = {}
            for chunk in chunks:
                for symbol in chunk.symbols_defined:
                    symbol_to_file[symbol] = chunk.path
            
            # Collect unique file paths
            unique_files = sorted(set(chunk.path for chunk in chunks))
            
            # Create vertex mapping
            self.file_to_vertex = {file: idx for idx, file in enumerate(unique_files)}
            self.vertex_to_file = {idx: file for file, idx in self.file_to_vertex.items()}
            
            # Create graph with vertices
            self.graph = self._ig.Graph(directed=True)
            self.graph.add_vertices(len(unique_files))
            
            # Add edges based on symbol references
            edges = []
            for chunk in chunks:
                source_file = chunk.path
                source_vertex = self.file_to_vertex[source_file]
                
                for symbol in chunk.symbols_referenced:
                    if symbol in symbol_to_file:
                        target_file = symbol_to_file[symbol]
                        target_vertex = self.file_to_vertex[target_file]
                        
                        # Add edge: source -> target (source depends on target)
                        if source_vertex != target_vertex:  # No self-loops
                            edges.append((source_vertex, target_vertex))
            
            # Add edges to graph (igraph handles duplicates)
            if edges:
                self.graph.add_edges(edges)
            
            logger.info(
                f"Built igraph with {len(unique_files)} nodes and {len(edges)} edges"
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to build igraph: {e}") from e
    
    def pagerank(self, changed_files: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Compute PageRank scores using igraph's C++ backend.
        
        Computes PageRank scores for all files. If changed_files are provided,
        their scores are boosted by multiplying by boost_factor and renormalizing.
        
        Args:
            changed_files: Optional list of file paths that have changed
            
        Returns:
            Dictionary mapping file paths to PageRank scores (sum to 1.0)
            
        Raises:
            RuntimeError: If PageRank computation fails
            ValueError: If graph has not been built yet
        """
        if self.graph is None:
            raise ValueError("Graph has not been built yet. Call build() first.")
        
        try:
            # Compute PageRank using igraph
            scores = self.graph.pagerank(directed=True)
            
            # Map vertex indices to file paths
            pagerank_scores = {
                self.vertex_to_file[idx]: score
                for idx, score in enumerate(scores)
            }
            
            # Boost changed files if provided
            if changed_files:
                for file in changed_files:
                    if file in pagerank_scores:
                        pagerank_scores[file] *= self.boost_factor
                
                # Renormalize to sum to 1.0
                total = sum(pagerank_scores.values())
                if total > 0:
                    pagerank_scores = {
                        file: score / total
                        for file, score in pagerank_scores.items()
                    }
            
            return pagerank_scores
            
        except Exception as e:
            raise RuntimeError(f"Failed to compute PageRank: {e}") from e
    
    def save(self, path: str) -> None:
        """
        Persist graph to disk using pickle.
        
        Args:
            path: File path to save the graph
            
        Raises:
            IOError: If save operation fails
        """
        if self.graph is None:
            raise ValueError("Cannot save graph that has not been built")
        
        try:
            save_path = Path(path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save graph data
            data = {
                'backend': 'igraph',
                'boost_factor': self.boost_factor,
                'file_to_vertex': self.file_to_vertex,
                'vertex_to_file': self.vertex_to_file,
                'graph_pickle': self.graph.__getstate__()  # igraph's serialization
            }
            
            with open(save_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug(f"Saved igraph to {path}")
            
        except Exception as e:
            raise IOError(f"Failed to save graph to {path}: {e}") from e
    
    @classmethod
    def load(cls, path: str) -> 'IGraphRepoMap':
        """
        Load graph from disk.
        
        Args:
            path: File path to load the graph from
            
        Returns:
            Loaded IGraphRepoMap instance
            
        Raises:
            IOError: If load operation fails
            ValueError: If file format is invalid
        """
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            if data.get('backend') != 'igraph':
                raise ValueError(f"Invalid backend in saved file: {data.get('backend')}")
            
            # Create instance
            instance = cls(boost_factor=data['boost_factor'])
            instance.file_to_vertex = data['file_to_vertex']
            instance.vertex_to_file = data['vertex_to_file']
            
            # Restore graph
            instance.graph = instance._ig.Graph()
            instance.graph.__setstate__(data['graph_pickle'])
            
            logger.debug(f"Loaded igraph from {path}")
            
            return instance
            
        except Exception as e:
            raise IOError(f"Failed to load graph from {path}: {e}") from e



class NetworkXRepoMap(RepoMapGraph):
    """
    Fallback RepoMap Graph implementation using NetworkX (pure Python).
    
    Provides PageRank computation using pure Python implementation.
    Slower than igraph (<10 seconds for 10k nodes) but more portable.
    """
    
    def __init__(self, boost_factor: float = 2.0):
        """
        Initialize NetworkXRepoMap.
        
        Args:
            boost_factor: Multiplier for changed file scores (default: 2.0)
            
        Raises:
            ImportError: If networkx is not installed
        """
        try:
            import networkx as nx
            self._nx = nx
        except ImportError as e:
            raise ImportError(
                "networkx is not installed. "
                "Install with: pip install networkx"
            ) from e
        
        self.boost_factor = boost_factor
        self.graph: Optional['nx.DiGraph'] = None
    
    def build(self, chunks: List[CodeChunk]) -> None:
        """
        Build directed dependency graph from code chunks using NetworkX.
        
        Creates a directed graph where edges represent symbol dependencies.
        File A -> File B means A imports or calls symbols defined in B.
        
        Args:
            chunks: List of CodeChunk objects with symbol definitions and references
            
        Raises:
            ValueError: If chunks list is empty
            RuntimeError: If graph construction fails
        """
        if not chunks:
            raise ValueError("Cannot build graph from empty chunks list")
        
        try:
            # Build symbol definition map: symbol -> file path
            symbol_to_file: Dict[str, str] = {}
            for chunk in chunks:
                for symbol in chunk.symbols_defined:
                    symbol_to_file[symbol] = chunk.path
            
            # Collect unique file paths
            unique_files = sorted(set(chunk.path for chunk in chunks))
            
            # Create directed graph
            self.graph = self._nx.DiGraph()
            self.graph.add_nodes_from(unique_files)
            
            # Add edges based on symbol references
            edges = []
            for chunk in chunks:
                source_file = chunk.path
                
                for symbol in chunk.symbols_referenced:
                    if symbol in symbol_to_file:
                        target_file = symbol_to_file[symbol]
                        
                        # Add edge: source -> target (source depends on target)
                        if source_file != target_file:  # No self-loops
                            edges.append((source_file, target_file))
            
            # Add edges to graph
            if edges:
                self.graph.add_edges_from(edges)
            
            logger.info(
                f"Built NetworkX graph with {len(unique_files)} nodes and {len(edges)} edges"
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to build NetworkX graph: {e}") from e
    
    def pagerank(self, changed_files: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Compute PageRank scores using NetworkX's pure Python implementation.
        
        Computes PageRank scores for all files. If changed_files are provided,
        their scores are boosted by multiplying by boost_factor and renormalizing.
        
        Args:
            changed_files: Optional list of file paths that have changed
            
        Returns:
            Dictionary mapping file paths to PageRank scores (sum to 1.0)
            
        Raises:
            RuntimeError: If PageRank computation fails
            ValueError: If graph has not been built yet
        """
        if self.graph is None:
            raise ValueError("Graph has not been built yet. Call build() first.")
        
        try:
            # Compute PageRank using NetworkX
            # Try scipy-based implementation first, fall back to pure Python
            try:
                pagerank_scores = self._nx.pagerank(self.graph)
            except (ImportError, ModuleNotFoundError):
                # scipy not available, use pure Python power iteration
                # This is a simple implementation of PageRank using power iteration
                logger.debug("scipy not available, using pure Python PageRank")
                pagerank_scores = self._pagerank_python(self.graph)
            
            # Boost changed files if provided
            if changed_files:
                for file in changed_files:
                    if file in pagerank_scores:
                        pagerank_scores[file] *= self.boost_factor
                
                # Renormalize to sum to 1.0
                total = sum(pagerank_scores.values())
                if total > 0:
                    pagerank_scores = {
                        file: score / total
                        for file, score in pagerank_scores.items()
                    }
            
            return pagerank_scores
            
        except Exception as e:
            raise RuntimeError(f"Failed to compute PageRank: {e}") from e
    
    def _pagerank_python(self, graph: 'nx.DiGraph', alpha: float = 0.85, max_iter: int = 100, tol: float = 1e-6) -> Dict[str, float]:
        """
        Pure Python implementation of PageRank using power iteration.
        
        Args:
            graph: NetworkX directed graph
            alpha: Damping parameter (default: 0.85)
            max_iter: Maximum iterations (default: 100)
            tol: Convergence tolerance (default: 1e-6)
            
        Returns:
            Dictionary mapping nodes to PageRank scores
        """
        nodes = list(graph.nodes())
        n = len(nodes)
        
        if n == 0:
            return {}
        
        # Initialize scores uniformly
        scores = {node: 1.0 / n for node in nodes}
        
        # Get out-degree for each node
        out_degree = {node: graph.out_degree(node) for node in nodes}
        
        # Power iteration
        for _ in range(max_iter):
            new_scores = {}
            
            for node in nodes:
                # Sum contributions from incoming edges
                rank_sum = 0.0
                for predecessor in graph.predecessors(node):
                    if out_degree[predecessor] > 0:
                        rank_sum += scores[predecessor] / out_degree[predecessor]
                
                # Apply damping factor
                new_scores[node] = (1 - alpha) / n + alpha * rank_sum
            
            # Check convergence
            diff = sum(abs(new_scores[node] - scores[node]) for node in nodes)
            scores = new_scores
            
            if diff < tol:
                break
        
        # Normalize to sum to 1.0
        total = sum(scores.values())
        if total > 0:
            scores = {node: score / total for node, score in scores.items()}
        
        return scores
    
    def save(self, path: str) -> None:
        """
        Persist graph to disk using pickle.
        
        Args:
            path: File path to save the graph
            
        Raises:
            IOError: If save operation fails
        """
        if self.graph is None:
            raise ValueError("Cannot save graph that has not been built")
        
        try:
            save_path = Path(path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save graph data
            data = {
                'backend': 'networkx',
                'boost_factor': self.boost_factor,
                'graph': self.graph
            }
            
            with open(save_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug(f"Saved NetworkX graph to {path}")
            
        except Exception as e:
            raise IOError(f"Failed to save graph to {path}: {e}") from e
    
    @classmethod
    def load(cls, path: str) -> 'NetworkXRepoMap':
        """
        Load graph from disk.
        
        Args:
            path: File path to load the graph from
            
        Returns:
            Loaded NetworkXRepoMap instance
            
        Raises:
            IOError: If load operation fails
            ValueError: If file format is invalid
        """
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            if data.get('backend') != 'networkx':
                raise ValueError(f"Invalid backend in saved file: {data.get('backend')}")
            
            # Create instance
            instance = cls(boost_factor=data['boost_factor'])
            instance.graph = data['graph']
            
            logger.debug(f"Loaded NetworkX graph from {path}")
            
            return instance
            
        except Exception as e:
            raise IOError(f"Failed to load graph from {path}: {e}") from e



def create_graph(backend: str = "auto", boost_factor: float = 2.0) -> RepoMapGraph:
    """
    Create a RepoMapGraph instance with automatic backend selection and fallback.
    
    Tries igraph first (C++ backend, fast), falls back to NetworkX (pure Python)
    if igraph is unavailable.
    
    Args:
        backend: Backend selection ("auto", "igraph", "networkx")
        boost_factor: Multiplier for changed file scores
        
    Returns:
        RepoMapGraph instance (IGraphRepoMap or NetworkXRepoMap)
        
    Raises:
        ImportError: If specified backend is unavailable
        ValueError: If backend parameter is invalid
    """
    if backend not in ("auto", "igraph", "networkx"):
        raise ValueError(f"Invalid backend: {backend}. Must be 'auto', 'igraph', or 'networkx'")
    
    # Try igraph first (unless explicitly requesting networkx)
    if backend in ("auto", "igraph"):
        try:
            graph = IGraphRepoMap(boost_factor=boost_factor)
            logger.info("Using igraph backend for RepoMap Graph")
            return graph
        except ImportError as e:
            if backend == "igraph":
                # User explicitly requested igraph, so fail
                raise ImportError(
                    "igraph backend requested but not available. "
                    "Install with: pip install python-igraph"
                ) from e
            else:
                # Auto mode: log fallback and try NetworkX
                logger.log_fallback(
                    component="graph",
                    primary="igraph",
                    fallback="networkx",
                    reason=str(e)
                )
    
    # Try NetworkX (fallback or explicitly requested)
    try:
        graph = NetworkXRepoMap(boost_factor=boost_factor)
        logger.info("Using NetworkX backend for RepoMap Graph")
        return graph
    except ImportError as e:
        raise ImportError(
            "NetworkX backend not available. "
            "Install with: pip install networkx"
        ) from e


def load_graph(path: str) -> RepoMapGraph:
    """
    Load a RepoMapGraph from disk with automatic backend detection.
    
    Detects the backend used when saving and loads with the appropriate implementation.
    
    Args:
        path: File path to load the graph from
        
    Returns:
        Loaded RepoMapGraph instance
        
    Raises:
        IOError: If load operation fails
        ValueError: If file format is invalid or backend is unavailable
    """
    try:
        # Peek at the backend type
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        backend = data.get('backend')
        
        if backend == 'igraph':
            try:
                return IGraphRepoMap.load(path)
            except ImportError:
                logger.warning(
                    f"Graph was saved with igraph but igraph is not available. "
                    f"Cannot load graph from {path}"
                )
                raise ValueError(
                    "Graph requires igraph backend but python-igraph is not installed. "
                    "Install with: pip install python-igraph"
                )
        elif backend == 'networkx':
            return NetworkXRepoMap.load(path)
        else:
            raise ValueError(f"Unknown backend in saved graph: {backend}")
            
    except Exception as e:
        if isinstance(e, (ValueError, ImportError)):
            raise
        raise IOError(f"Failed to load graph from {path}: {e}") from e
