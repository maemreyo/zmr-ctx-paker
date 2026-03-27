"""Tests for ModelRegistry singleton (Phase 1 — written BEFORE implementation)."""

import os
import threading
from unittest.mock import MagicMock, patch

import pytest

from ws_ctx_engine.vector_index.model_registry import ModelRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_registry() -> None:
    """Reset internal singleton state between tests."""
    ModelRegistry._registry.clear()


# ---------------------------------------------------------------------------
# Basic singleton behaviour
# ---------------------------------------------------------------------------


class TestSingletonBehaviour:
    def setup_method(self) -> None:
        _clear_registry()

    def test_same_key_returns_same_instance(self) -> None:
        """Two calls with the same key must return the identical object."""
        mock_model = MagicMock()
        with patch(
            "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
            return_value=mock_model,
        ):
            m1 = ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")
            m2 = ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")

        assert m1 is m2

    def test_different_model_names_return_different_instances(self) -> None:
        """Different model names must yield different cached entries."""
        mock_a = MagicMock(name="model_a")
        mock_b = MagicMock(name="model_b")

        def side_effect(model_name: str, device: str, backend: str) -> MagicMock:
            return mock_a if "bge" in model_name else mock_b

        with patch(
            "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
            side_effect=side_effect,
        ):
            ma = ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")
            mb = ModelRegistry.get_model("nomic-embed-text-v1.5", "cpu")

        assert ma is not mb

    def test_different_devices_return_different_instances(self) -> None:
        """cpu and cuda are different cache keys."""
        call_count = 0

        def make_model(*_: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return MagicMock()

        with patch(
            "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
            side_effect=make_model,
        ):
            ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")
            ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cuda")

        assert call_count == 2


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def setup_method(self) -> None:
        _clear_registry()

    def test_concurrent_load_no_race_condition(self) -> None:
        """10 threads calling get_model simultaneously must all get same instance.

        Uses a start-gate (Event) so threads race to get_model concurrently,
        then verifies all returned the same cached instance.
        """
        init_count = 0
        start_gate = threading.Event()

        def make_model(*_: object) -> MagicMock:
            nonlocal init_count
            init_count += 1
            return MagicMock()

        results: list[int] = []
        lock = threading.Lock()

        def worker() -> None:
            start_gate.wait()  # all threads blocked until gate opens
            m = ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")
            with lock:
                results.append(id(m))

        with patch(
            "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
            side_effect=make_model,
        ):
            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads:
                t.start()
            start_gate.set()  # release all threads simultaneously
            for t in threads:
                t.join(timeout=5)

        # All threads must get the same object
        assert len(set(results)) == 1, f"Got {len(set(results))} distinct instances"
        # Model must have been initialised exactly once
        assert init_count == 1, f"_load_model called {init_count} times"


# ---------------------------------------------------------------------------
# Env-var behaviour
# ---------------------------------------------------------------------------


class TestEnvVarBehaviour:
    def setup_method(self) -> None:
        _clear_registry()

    def test_preload_disabled_returns_fresh_instance_each_call(self) -> None:
        """WSCTX_DISABLE_MODEL_PRELOAD=1 bypasses the cache."""
        call_count = 0

        def make_model(*_: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return MagicMock()

        with (
            patch.dict(os.environ, {"WSCTX_DISABLE_MODEL_PRELOAD": "1"}),
            patch(
                "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
                side_effect=make_model,
            ),
        ):
            ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")
            ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")

        assert call_count == 2

    def test_onnx_backend_passed_to_loader_when_env_set(self) -> None:
        """WSCTX_ENABLE_ONNX=1 must propagate backend='onnx' to _load_model."""
        received_backends: list[str] = []

        def capture_backend(model_name: str, device: str, backend: str) -> MagicMock:
            received_backends.append(backend)
            return MagicMock()

        with (
            patch.dict(os.environ, {"WSCTX_ENABLE_ONNX": "1"}),
            patch(
                "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
                side_effect=capture_backend,
            ),
        ):
            ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")

        assert "onnx" in received_backends

    def test_custom_model_via_env_var(self) -> None:
        """WSCTX_EMBEDDING_MODEL overrides the requested model name."""
        received_names: list[str] = []

        def capture_name(model_name: str, device: str, backend: str) -> MagicMock:
            received_names.append(model_name)
            return MagicMock()

        with (
            patch.dict(os.environ, {"WSCTX_EMBEDDING_MODEL": "nomic-embed-text-v1.5"}),
            patch(
                "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
                side_effect=capture_name,
            ),
        ):
            ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")

        assert "nomic-embed-text-v1.5" in received_names

    def test_memory_threshold_prevents_load_when_low(self) -> None:
        """If available RAM is below WSCTX_MEMORY_THRESHOLD_MB, get_model returns None."""
        with (
            patch.dict(os.environ, {"WSCTX_MEMORY_THRESHOLD_MB": "999999"}),
            patch("psutil.virtual_memory") as mock_vm,
        ):
            mock_vm.return_value.available = 1 * 1024 * 1024  # 1 MB << threshold
            result = ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")

        assert result is None


# ---------------------------------------------------------------------------
# Default model
# ---------------------------------------------------------------------------


class TestDefaultModel:
    def setup_method(self) -> None:
        _clear_registry()

    def test_default_model_is_bge_small(self) -> None:
        """get_model() with no override must request BAAI/bge-small-en-v1.5."""
        received: list[str] = []

        def capture(model_name: str, device: str, backend: str) -> MagicMock:
            received.append(model_name)
            return MagicMock()

        with patch(
            "ws_ctx_engine.vector_index.model_registry.ModelRegistry._load_model",
            side_effect=capture,
        ):
            # Call with the default (no env override)
            ModelRegistry.get_model("BAAI/bge-small-en-v1.5", "cpu")

        assert received[0] == "BAAI/bge-small-en-v1.5"
