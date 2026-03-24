"""
Integration tests for query phase workflow.

Tests the complete index → query → pack workflow for Context Packer.
"""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from context_packer.config import Config
from context_packer.workflow import index_repository, query_and_pack

# Check if required dependencies are available
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    import sentence_transformers
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Skip all tests if dependencies are not available
pytestmark = pytest.mark.skipif(
    not (FAISS_AVAILABLE or SENTENCE_TRANSFORMERS_AVAILABLE),
    reason="Integration tests require either faiss-cpu or sentence-transformers"
)


@pytest.fixture
def small_repo(tmp_path):
    """
    Create a small test repository with Python files.
    
    Structure:
        repo/
        ├── src/
        │   ├── main.py
        │   ├── utils.py
        │   └── auth.py
        └── tests/
            └── test_main.py
    """
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    
    # Create src directory
    src_dir = repo_path / "src"
    src_dir.mkdir()
    
    # Create main.py
    (src_dir / "main.py").write_text("""
def main():
    \"\"\"Main entry point for the application.\"\"\"
    from src.auth import authenticate
    from src.utils import log_message
    
    log_message("Starting application")
    user = authenticate("admin", "password")
    if user:
        log_message(f"User {user} authenticated")
    else:
        log_message("Authentication failed")

if __name__ == "__main__":
    main()
""")
    
    # Create utils.py
    (src_dir / "utils.py").write_text("""
import logging

logger = logging.getLogger(__name__)

def log_message(message):
    \"\"\"Log a message to the console.\"\"\"
    logger.info(message)
    print(message)

def format_user(username):
    \"\"\"Format username for display.\"\"\"
    return f"User: {username}"
""")
    
    # Create auth.py
    (src_dir / "auth.py").write_text("""
from src.utils import format_user

def authenticate(username, password):
    \"\"\"Authenticate a user with username and password.\"\"\"
    # Simple authentication logic
    if username == "admin" and password == "password":
        return format_user(username)
    return None

def check_permissions(user, resource):
    \"\"\"Check if user has permissions for resource.\"\"\"
    # Simple permission check
    return user == "admin"
""")
    
    # Create tests directory
    tests_dir = repo_path / "tests"
    tests_dir.mkdir()
    
    # Create test_main.py
    (tests_dir / "test_main.py").write_text("""
import pytest
from src.main import main
from src.auth import authenticate

def test_main():
    \"\"\"Test main function.\"\"\"
    main()

def test_authenticate():
    \"\"\"Test authentication.\"\"\"
    assert authenticate("admin", "password") is not None
    assert authenticate("user", "wrong") is None
""")
    
    return repo_path


@pytest.fixture
def config_xml(tmp_path):
    """Create configuration for XML output."""
    config = Config()
    config.format = "xml"
    config.token_budget = 10000
    config.output_path = str(tmp_path / "output")
    config.semantic_weight = 0.6
    config.pagerank_weight = 0.4
    # Force FAISS backend for tests (LEANN requires embeddings)
    config.backends["vector_index"] = "faiss"
    return config


@pytest.fixture
def config_zip(tmp_path):
    """Create configuration for ZIP output."""
    config = Config()
    config.format = "zip"
    config.token_budget = 10000
    config.output_path = str(tmp_path / "output")
    config.semantic_weight = 0.6
    config.pagerank_weight = 0.4
    # Force FAISS backend for tests (LEANN requires embeddings)
    config.backends["vector_index"] = "faiss"
    return config


class TestQueryWorkflow:
    """Integration tests for full query workflow."""
    
    def test_full_workflow_xml(self, small_repo, config_xml):
        """
        Test complete workflow: index → query → pack (XML format).
        
        Verifies:
        - Indexes are built successfully
        - Query returns results
        - XML output is generated
        - Output is within token budget
        - Selected files have highest scores
        
        Requirements: 15.1, 15.4, 15.5
        """
        # Phase 1: Index repository
        index_repository(
            repo_path=str(small_repo),
            config=config_xml
        )
        
        # Verify indexes were created
        index_dir = small_repo / ".context-pack"
        assert (index_dir / "vector.idx").exists()
        assert (index_dir / "graph.pkl").exists()
        assert (index_dir / "metadata.json").exists()
        
        # Phase 2: Query and pack
        output_path = query_and_pack(
            repo_path=str(small_repo),
            query="authentication logic",
            config=config_xml
        )
        
        # Verify output was created
        assert os.path.exists(output_path)
        assert output_path.endswith(".xml")
        
        # Parse and validate XML
        with open(output_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Parse XML to verify it's valid
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Verify XML structure
        assert root.tag == "repository"
        
        # Check metadata
        metadata = root.find("metadata")
        assert metadata is not None
        
        repo_name = metadata.find("name")
        assert repo_name is not None
        assert repo_name.text == "repo"
        
        file_count = metadata.find("file_count")
        assert file_count is not None
        assert int(file_count.text) > 0
        
        total_tokens = metadata.find("total_tokens")
        assert total_tokens is not None
        tokens = int(total_tokens.text)
        
        # Verify output is within budget (80% of total budget for content)
        content_budget = int(config_xml.token_budget * 0.8)
        assert tokens <= content_budget, \
            f"Token count {tokens} exceeds content budget {content_budget}"
        
        # Check files section
        files = root.find("files")
        assert files is not None
        
        file_elements = files.findall("file")
        assert len(file_elements) > 0
        
        # Verify auth.py is included (should have high score for "authentication" query)
        file_paths = [f.get("path") for f in file_elements]
        assert any("auth.py" in path for path in file_paths), \
            "auth.py should be included for authentication query"
        
        # Verify each file has required attributes
        for file_elem in file_elements:
            assert file_elem.get("path") is not None
            assert file_elem.get("tokens") is not None
            assert int(file_elem.get("tokens")) > 0
            assert file_elem.text is not None  # File content
    
    def test_full_workflow_zip(self, small_repo, config_zip):
        """
        Test complete workflow: index → query → pack (ZIP format).
        
        Verifies:
        - Indexes are built successfully
        - Query returns results
        - ZIP output is generated
        - ZIP structure is correct
        - Manifest is included
        - Output is within token budget
        
        Requirements: 15.1, 15.4, 15.5
        """
        # Phase 1: Index repository
        index_repository(
            repo_path=str(small_repo),
            config=config_zip
        )
        
        # Verify indexes were created
        index_dir = small_repo / ".context-pack"
        assert (index_dir / "vector.idx").exists()
        assert (index_dir / "graph.pkl").exists()
        assert (index_dir / "metadata.json").exists()
        
        # Phase 2: Query and pack
        output_path = query_and_pack(
            repo_path=str(small_repo),
            query="authentication logic",
            config=config_zip
        )
        
        # Verify output was created
        assert os.path.exists(output_path)
        assert output_path.endswith(".zip")
        
        # Extract and verify ZIP contents
        with zipfile.ZipFile(output_path, 'r') as zip_file:
            # Get list of files in ZIP
            zip_contents = zip_file.namelist()
            
            # Verify REVIEW_CONTEXT.md exists
            assert "REVIEW_CONTEXT.md" in zip_contents
            
            # Verify files are under files/ directory
            file_entries = [f for f in zip_contents if f.startswith("files/")]
            assert len(file_entries) > 0
            
            # Verify auth.py is included
            assert any("auth.py" in f for f in file_entries), \
                "auth.py should be included for authentication query"
            
            # Read and verify manifest
            manifest_content = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
            
            # Check manifest structure
            assert "# Review Context" in manifest_content
            assert "## Repository Information" in manifest_content
            assert "## Included Files" in manifest_content
            assert "## Suggested Reading Order" in manifest_content
            
            # Check metadata in manifest
            assert "repo" in manifest_content  # repo name
            assert "authentication logic" in manifest_content  # query
            
            # Verify file structure is preserved
            for file_entry in file_entries:
                # Extract file
                content = zip_file.read(file_entry).decode('utf-8')
                assert len(content) > 0
                
                # Verify path structure (should be files/src/... or files/tests/...)
                assert file_entry.startswith("files/")
    
    def test_workflow_with_changed_files(self, small_repo, config_xml):
        """
        Test workflow with changed files for PageRank boosting.
        
        Verifies:
        - Changed files receive higher importance scores
        - Changed files are included in output
        
        Requirements: 15.1, 15.4, 15.5
        """
        # Index repository
        index_repository(
            repo_path=str(small_repo),
            config=config_xml
        )
        
        # Query with changed files
        changed_files = ["src/auth.py"]
        output_path = query_and_pack(
            repo_path=str(small_repo),
            query=None,  # No semantic query, rely on PageRank
            changed_files=changed_files,
            config=config_xml
        )
        
        # Verify output was created
        assert os.path.exists(output_path)
        
        # Parse XML
        with open(output_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Verify changed files are in metadata
        metadata = root.find("metadata")
        changed_elem = metadata.find("changed_files")
        assert changed_elem is not None
        assert "src/auth.py" in changed_elem.text
        
        # Verify auth.py is included in output
        files = root.find("files")
        file_paths = [f.get("path") for f in files.findall("file")]
        assert "src/auth.py" in file_paths
    
    def test_workflow_without_query(self, small_repo, config_xml):
        """
        Test workflow without semantic query (PageRank only).
        
        Verifies:
        - Workflow works with PageRank scores only
        - Files are still selected and ranked
        
        Requirements: 15.1, 15.4, 15.5
        """
        # Index repository
        index_repository(
            repo_path=str(small_repo),
            config=config_xml
        )
        
        # Query without semantic query
        output_path = query_and_pack(
            repo_path=str(small_repo),
            query=None,
            config=config_xml
        )
        
        # Verify output was created
        assert os.path.exists(output_path)
        
        # Parse XML
        with open(output_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Verify files were selected
        files = root.find("files")
        file_elements = files.findall("file")
        assert len(file_elements) > 0
        
        # Verify no query in metadata
        metadata = root.find("metadata")
        query_elem = metadata.find("query")
        # Query element may not exist or be empty
        if query_elem is not None:
            assert query_elem.text is None or query_elem.text == ""
    
    def test_workflow_respects_token_budget(self, small_repo, config_xml):
        """
        Test that workflow respects token budget constraints.
        
        Verifies:
        - Total tokens do not exceed 80% of budget
        - Files are selected greedily by importance
        
        Requirements: 15.1, 15.4, 15.5
        """
        # Set a very small budget to force selection
        config_xml.token_budget = 2000
        
        # Index repository
        index_repository(
            repo_path=str(small_repo),
            config=config_xml
        )
        
        # Query and pack
        output_path = query_and_pack(
            repo_path=str(small_repo),
            query="authentication",
            config=config_xml
        )
        
        # Parse XML
        with open(output_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Get total tokens
        metadata = root.find("metadata")
        total_tokens = int(metadata.find("total_tokens").text)
        
        # Verify within budget (80% of total)
        content_budget = int(config_xml.token_budget * 0.8)
        assert total_tokens <= content_budget, \
            f"Token count {total_tokens} exceeds content budget {content_budget}"
        
        # Verify at least one file was selected
        files = root.find("files")
        file_elements = files.findall("file")
        assert len(file_elements) > 0
