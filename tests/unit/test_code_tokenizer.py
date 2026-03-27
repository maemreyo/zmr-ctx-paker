"""Tests for ws_ctx_engine.retrieval.code_tokenizer (Phase 3 — TDD-first)."""

import pytest

from ws_ctx_engine.retrieval.code_tokenizer import tokenize_code, tokenize_query


# ---------------------------------------------------------------------------
# tokenize_code — chunk content tokenisation
# ---------------------------------------------------------------------------


class TestTokenizeCode:
    def test_splits_snake_case(self) -> None:
        assert "authenticate" in tokenize_code("def authenticate_user(): pass")
        assert "user" in tokenize_code("def authenticate_user(): pass")

    def test_splits_camel_case(self) -> None:
        tokens = tokenize_code("getUserById")
        assert "get" in tokens
        assert "user" in tokens
        assert "by" in tokens or "id" in tokens  # at least one

    def test_lowercases_tokens(self) -> None:
        tokens = tokenize_code("MyClass")
        assert "my" in tokens
        assert "class" in tokens
        assert "MyClass" not in tokens

    def test_strips_punctuation(self) -> None:
        tokens = tokenize_code("foo(bar, baz);")
        assert "foo" in tokens
        assert "bar" in tokens
        assert "baz" in tokens

    def test_removes_very_short_tokens(self) -> None:
        """Tokens of length < 2 should be filtered out."""
        tokens = tokenize_code("a = b + c")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "c" not in tokens

    def test_returns_list(self) -> None:
        result = tokenize_code("hello world")
        assert isinstance(result, list)

    def test_empty_string_returns_empty(self) -> None:
        assert tokenize_code("") == []

    def test_numeric_tokens_excluded(self) -> None:
        """Pure numeric tokens carry no semantic signal."""
        tokens = tokenize_code("x = 42")
        assert "42" not in tokens

    def test_preserves_acronyms_split(self) -> None:
        """HTTPSClient → ['https', 'client'] or ['http', 's', 'client']."""
        tokens = tokenize_code("HTTPSClient")
        # At minimum 'client' must be present
        assert "client" in tokens

    def test_handles_multiline_code(self) -> None:
        code = "def hash_password(pw: str) -> str:\n    return sha256(pw)"
        tokens = tokenize_code(code)
        assert "hash" in tokens
        assert "password" in tokens
        assert "sha256" in tokens or "sha" in tokens

    def test_deduplicates_tokens(self) -> None:
        """Same token appearing multiple times should appear once."""
        tokens = tokenize_code("foo foo foo")
        assert tokens.count("foo") == 1

    def test_private_prefix_stripped(self) -> None:
        """Leading underscores in _private_func should not produce empty tokens."""
        tokens = tokenize_code("_private_func")
        assert "private" in tokens
        assert "func" in tokens
        assert "" not in tokens


# ---------------------------------------------------------------------------
# tokenize_query — natural language query tokenisation
# ---------------------------------------------------------------------------


class TestTokenizeQuery:
    def test_basic_split(self) -> None:
        tokens = tokenize_query("authenticate user")
        assert "authenticate" in tokens
        assert "user" in tokens

    def test_removes_stop_words(self) -> None:
        tokens = tokenize_query("how does authentication work")
        assert "how" not in tokens
        assert "does" not in tokens
        assert "authentication" in tokens

    def test_lowercases(self) -> None:
        tokens = tokenize_query("Find The AuthService")
        assert "authservice" in tokens or "auth" in tokens or "service" in tokens

    def test_returns_list(self) -> None:
        assert isinstance(tokenize_query("foo bar"), list)

    def test_empty_returns_empty(self) -> None:
        assert tokenize_query("") == []

    def test_camel_case_query(self) -> None:
        """Query may contain identifiers like getUserById.

        'get' is a stop word so it may be filtered; 'user' and 'id' should
        survive the split and stop-word removal.
        """
        tokens = tokenize_query("getUserById implementation")
        assert "user" in tokens or "id" in tokens
        assert "implementation" in tokens

    def test_deduplicates(self) -> None:
        tokens = tokenize_query("auth auth auth")
        assert tokens.count("auth") == 1
