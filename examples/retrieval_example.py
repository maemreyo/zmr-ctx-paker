"""
Example usage of RetrievalEngine for hybrid ranking.

This example demonstrates how to use the RetrievalEngine to combine
semantic search and PageRank scores for intelligent file selection.

Note: This example uses mock implementations to avoid requiring
embedding dependencies. In production, use real VectorIndex and
RepoMapGraph implementations.
"""

from typing import List, Tuple, Dict, Optional
from context_packer.models import CodeChunk
from context_packer.vector_index import VectorIndex
from context_packer.graph import RepoMapGraph
from context_packer.retrieval import RetrievalEngine


# Mock implementations for demonstration
class MockVectorIndex(VectorIndex):
    """Mock VectorIndex for demonstration."""
    
    def __init__(self):
        self.search_results = {}
    
    def build(self, chunks: List[CodeChunk]) -> None:
        # Simulate building index with mock scores
        self.search_results = {
            "src/auth.py": 0.95,
            "src/session.py": 0.75,
            "src/user.py": 0.60,
        }
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        return list(self.search_results.items())[:top_k]
    
    def save(self, path: str) -> None:
        pass
    
    @classmethod
    def load(cls, path: str) -> 'VectorIndex':
        return cls()


class MockRepoMapGraph(RepoMapGraph):
    """Mock RepoMapGraph for demonstration."""
    
    def __init__(self):
        self.pagerank_scores = {}
    
    def build(self, chunks: List[CodeChunk]) -> None:
        # Simulate PageRank scores
        self.pagerank_scores = {
            "src/auth.py": 0.40,
            "src/session.py": 0.35,
            "src/user.py": 0.25,
        }
    
    def pagerank(self, changed_files: Optional[List[str]] = None) -> Dict[str, float]:
        scores = self.pagerank_scores.copy()
        
        # Boost changed files
        if changed_files:
            for file in changed_files:
                if file in scores:
                    scores[file] *= 1.5
            
            # Renormalize
            total = sum(scores.values())
            scores = {k: v / total for k, v in scores.items()}
        
        return scores
    
    def save(self, path: str) -> None:
        pass
    
    @classmethod
    def load(cls, path: str) -> 'RepoMapGraph':
        return cls()


def main():
    """Demonstrate RetrievalEngine usage."""
    
    # Sample code chunks (in practice, these come from AST parsing)
    chunks = [
        CodeChunk(
            path="src/auth.py",
            start_line=1,
            end_line=50,
            content="def authenticate(user, password):\n    # Authentication logic\n    pass",
            symbols_defined=["authenticate"],
            symbols_referenced=["hash_password", "verify_token"],
            language="python"
        ),
        CodeChunk(
            path="src/user.py",
            start_line=1,
            end_line=30,
            content="class User:\n    def __init__(self, username):\n        self.username = username",
            symbols_defined=["User"],
            symbols_referenced=[],
            language="python"
        ),
        CodeChunk(
            path="src/session.py",
            start_line=1,
            end_line=40,
            content="def create_session(user):\n    # Session creation\n    pass",
            symbols_defined=["create_session"],
            symbols_referenced=["User", "authenticate"],
            language="python"
        ),
    ]
    
    # Build vector index for semantic search
    print("Building vector index...")
    vector_index = MockVectorIndex()
    vector_index.build(chunks)
    
    # Build dependency graph for PageRank
    print("Building dependency graph...")
    graph = MockRepoMapGraph()
    graph.build(chunks)
    
    # Create retrieval engine with custom weights
    print("\nCreating retrieval engine...")
    engine = RetrievalEngine(
        vector_index=vector_index,
        graph=graph,
        semantic_weight=0.6,  # 60% weight on semantic similarity
        pagerank_weight=0.4   # 40% weight on structural importance
    )
    
    # Retrieve files for a query
    print("\nRetrieving files for query: 'authentication logic'")
    results = engine.retrieve(
        query="authentication logic",
        changed_files=["src/auth.py"],  # Boost changed files
        top_k=10
    )
    
    # Display results
    print("\nTop ranked files:")
    for i, (file_path, score) in enumerate(results, 1):
        print(f"{i}. {file_path}: {score:.3f}")
    
    # Example with only PageRank (no query)
    print("\n\nRetrieving files based on structure only (no query):")
    results_no_query = engine.retrieve(
        query=None,
        changed_files=["src/auth.py"],
        top_k=10
    )
    
    print("\nTop ranked files (PageRank only):")
    for i, (file_path, score) in enumerate(results_no_query, 1):
        print(f"{i}. {file_path}: {score:.3f}")


if __name__ == "__main__":
    main()
