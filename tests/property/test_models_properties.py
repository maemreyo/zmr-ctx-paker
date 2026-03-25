"""Property-based tests for data models.

These tests validate universal properties that should hold for all valid inputs.
"""

import pytest
import tiktoken
from hypothesis import given, strategies as st

from ws_ctx_engine.models import CodeChunk


# Custom strategies for generating test data
@st.composite
def code_chunk_strategy(draw):
    """Generate valid CodeChunk instances."""
    # Generate path
    path_parts = draw(st.lists(
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=10),
        min_size=1,
        max_size=5
    ))
    path = "/".join(path_parts) + draw(st.sampled_from([".py", ".js", ".ts", ".java", ".go"]))
    
    # Generate line numbers (start_line <= end_line)
    start_line = draw(st.integers(min_value=1, max_value=10000))
    end_line = draw(st.integers(min_value=start_line, max_value=start_line + 1000))
    
    # Generate content (printable text)
    content = draw(st.text(min_size=0, max_size=5000))
    
    # Generate symbols
    symbol_name = st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_'),
        min_size=1,
        max_size=50
    )
    symbols_defined = draw(st.lists(symbol_name, max_size=20))
    symbols_referenced = draw(st.lists(symbol_name, max_size=20))
    
    # Generate language
    language = draw(st.sampled_from(["python", "javascript", "typescript", "java", "go", "rust", "c", "cpp"]))
    
    return CodeChunk(
        path=path,
        start_line=start_line,
        end_line=end_line,
        content=content,
        symbols_defined=symbols_defined,
        symbols_referenced=symbols_referenced,
        language=language
    )


class TestCodeChunkProperties:
    """Property-based tests for CodeChunk."""
    
    @given(code_chunk_strategy())
    def test_property_token_count_consistency(self, chunk):
        """Property 12: Token counting SHALL produce the same count when called multiple times.
        
        **Validates: Requirements 5.1**
        
        For any file content, token counting using tiktoken SHALL produce the same count
        when called multiple times on the same content.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # Call token_count multiple times
        count1 = chunk.token_count(encoding)
        count2 = chunk.token_count(encoding)
        count3 = chunk.token_count(encoding)
        
        # All counts should be identical
        assert count1 == count2 == count3, \
            f"Token count inconsistent: {count1}, {count2}, {count3}"
    
    @given(code_chunk_strategy())
    def test_property_token_count_non_negative(self, chunk):
        """Property: Token count SHALL always be non-negative.
        
        **Validates: Requirements 5.1**
        
        For any file content, the token count must be >= 0.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        token_count = chunk.token_count(encoding)
        
        assert token_count >= 0, \
            f"Token count must be non-negative, got {token_count}"
    
    @given(st.text(min_size=0, max_size=1000))
    def test_property_empty_content_zero_tokens(self, content):
        """Property: Empty content SHALL have zero tokens.
        
        **Validates: Requirements 5.1**
        
        When content is empty, token count must be exactly 0.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        chunk = CodeChunk(
            path="test.py",
            start_line=1,
            end_line=1,
            content="" if not content else content,
            symbols_defined=[],
            symbols_referenced=[],
            language="python"
        )
        
        token_count = chunk.token_count(encoding)
        
        if chunk.content == "":
            assert token_count == 0, \
                f"Empty content should have 0 tokens, got {token_count}"
        else:
            # Non-empty content should have positive token count
            assert token_count > 0, \
                f"Non-empty content should have positive tokens, got {token_count}"
    
    @given(code_chunk_strategy())
    def test_property_line_numbers_valid(self, chunk):
        """Property: Line numbers SHALL be valid (start_line <= end_line, both positive).
        
        **Validates: Requirements 1.1, 1.3, 1.4**
        
        For any CodeChunk, start_line must be <= end_line and both must be positive.
        """
        assert chunk.start_line >= 1, \
            f"start_line must be >= 1, got {chunk.start_line}"
        assert chunk.end_line >= 1, \
            f"end_line must be >= 1, got {chunk.end_line}"
        assert chunk.start_line <= chunk.end_line, \
            f"start_line ({chunk.start_line}) must be <= end_line ({chunk.end_line})"
    
    @given(code_chunk_strategy())
    def test_property_symbols_are_lists(self, chunk):
        """Property: Symbol fields SHALL always be lists.
        
        **Validates: Requirements 1.3, 1.4**
        
        For any CodeChunk, symbols_defined and symbols_referenced must be list types.
        """
        assert isinstance(chunk.symbols_defined, list), \
            f"symbols_defined must be a list, got {type(chunk.symbols_defined)}"
        assert isinstance(chunk.symbols_referenced, list), \
            f"symbols_referenced must be a list, got {type(chunk.symbols_referenced)}"
    
    @given(code_chunk_strategy())
    def test_property_path_is_string(self, chunk):
        """Property: Path SHALL always be a string.
        
        **Validates: Requirements 1.1**
        
        For any CodeChunk, path must be a string type.
        """
        assert isinstance(chunk.path, str), \
            f"path must be a string, got {type(chunk.path)}"
        assert len(chunk.path) > 0, \
            "path must not be empty"
    
    @given(code_chunk_strategy())
    def test_property_language_is_string(self, chunk):
        """Property: Language SHALL always be a string.
        
        **Validates: Requirements 1.1**
        
        For any CodeChunk, language must be a string type.
        """
        assert isinstance(chunk.language, str), \
            f"language must be a string, got {type(chunk.language)}"
    
    @given(code_chunk_strategy())
    def test_property_content_is_string(self, chunk):
        """Property: Content SHALL always be a string.
        
        **Validates: Requirements 1.1**
        
        For any CodeChunk, content must be a string type.
        """
        assert isinstance(chunk.content, str), \
            f"content must be a string, got {type(chunk.content)}"
    
    @given(st.text(min_size=1, max_size=1000))
    def test_property_longer_content_more_tokens(self, base_content):
        """Property: Longer content SHALL generally have more or equal tokens.
        
        **Validates: Requirements 5.1**
        
        When content is extended, token count should not decrease.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        
        chunk1 = CodeChunk(
            path="test.py",
            start_line=1,
            end_line=1,
            content=base_content,
            symbols_defined=[],
            symbols_referenced=[],
            language="python"
        )
        
        # Extended content
        chunk2 = CodeChunk(
            path="test.py",
            start_line=1,
            end_line=2,
            content=base_content + "\n" + base_content,
            symbols_defined=[],
            symbols_referenced=[],
            language="python"
        )
        
        count1 = chunk1.token_count(encoding)
        count2 = chunk2.token_count(encoding)
        
        # Extended content should have more or equal tokens
        assert count2 >= count1, \
            f"Extended content should have >= tokens: {count1} vs {count2}"
    
    @given(code_chunk_strategy())
    def test_property_token_count_matches_tiktoken_directly(self, chunk):
        """Property: Token count SHALL match direct tiktoken encoding.
        
        **Validates: Requirements 5.1, 5.5**
        
        The token_count method should produce the same result as directly
        encoding the content with tiktoken.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        
        chunk_count = chunk.token_count(encoding)
        direct_count = len(encoding.encode(chunk.content))
        
        assert chunk_count == direct_count, \
            f"Token count mismatch: chunk.token_count()={chunk_count}, direct encoding={direct_count}"
