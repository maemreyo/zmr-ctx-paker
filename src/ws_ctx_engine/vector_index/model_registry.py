"""Thread-safe singleton registry for embedding models.

Avoids the 6-8 second cold-start penalty by loading each model exactly once
per (model_name, device, backend) combination and caching the instance for
reuse across all calls within the same process.

Environment variables
---------------------
WSCTX_DISABLE_MODEL_PRELOAD
    Set to ``1`` to bypass caching (useful for testing or memory-constrained
    environments). Each ``get_model()`` call will create a fresh instance.

WSCTX_EMBEDDING_MODEL
    Override the model name regardless of what was requested. E.g.
    ``WSCTX_EMBEDDING_MODEL=nomic-embed-text-v1.5``.

WSCTX_DISABLE_ONNX
    Set to ``1`` to force the default PyTorch backend even when ``onnxruntime``
    is installed.  By default the registry auto-detects ``onnxruntime`` and
    uses it for a ~3x CPU encoding speedup.

WSCTX_ENABLE_ONNX
    Legacy opt-in flag, still honoured.  Prefer ``WSCTX_DISABLE_ONNX=1`` to
    turn ONNX off when auto-detection is undesired.

WSCTX_MEMORY_THRESHOLD_MB
    Minimum available RAM in MB required before loading a model (default 500).
    If available RAM is below this threshold, ``get_model()`` returns ``None``.
"""

import os
import threading
from typing import Any


def _onnx_available() -> bool:
    """Return True if both ``onnxruntime`` and ``optimum`` are importable.

    ``sentence-transformers`` ONNX backend requires both packages:
    ``pip install optimum[onnxruntime]`` installs them together.
    """
    try:
        import onnxruntime  # type: ignore[import-untyped]  # noqa: F401
        import optimum  # type: ignore[import-untyped]  # noqa: F401

        return True
    except ImportError:
        return False


def _reinit_registry_after_fork() -> None:
    """Reset the ModelRegistry lock and cache in forked child processes.

    A threading.Lock forked in an acquired state will never be releasable in
    the child, causing a deadlock.  Registering this handler via
    ``os.register_at_fork`` ensures child processes start with a clean slate.
    """
    ModelRegistry._lock = threading.Lock()
    ModelRegistry._registry.clear()


# Register before any fork can occur (safe to call multiple times — no-op on
# platforms that don't support fork, e.g. Windows).
try:
    os.register_at_fork(after_in_child=_reinit_registry_after_fork)
except AttributeError:
    pass  # Windows / environments without fork support

import psutil  # type: ignore[import-untyped]

from ..logger import get_logger

logger = get_logger()

# Default model — BAAI/bge-small-en-v1.5:
#   - Native SentenceTransformer model (no custom pooling needed)
#   - 384-dim embeddings, same shape as all-MiniLM-L6-v2
#   - Trained explicitly for retrieval (unlike MiniLM's 128-token optimum)
#   - 120 MB on disk, fast CPU inference
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_MEMORY_THRESHOLD_MB = 500


class ModelRegistry:
    """Thread-safe singleton registry for SentenceTransformer models.

    Uses double-checked locking to ensure each (model_name, device, backend)
    tuple is loaded at most once even under concurrent access.
    """

    # Class-level state shared across all callers in the same process.
    _registry: dict[tuple[str, str, str], Any] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_model(
        cls,
        model_name: str,
        device: str = "cpu",
        backend: str = "default",
    ) -> Any | None:
        """Return a cached SentenceTransformer model, loading it if necessary.

        Args:
            model_name: HuggingFace model ID to load.
            device: Target device (``"cpu"`` or ``"cuda"``).
            backend: Backend hint; pass ``"onnx"`` for ONNX runtime or
                ``"default"`` for standard PyTorch.

        Returns:
            Loaded model instance, or ``None`` if insufficient memory or
            sentence-transformers is not installed.
        """
        # Allow env-var override of the model name
        env_model = os.environ.get("WSCTX_EMBEDDING_MODEL")
        if env_model:
            model_name = env_model

        # Resolve backend: ONNX is used automatically when onnxruntime is
        # available unless the caller explicitly requests a different backend
        # or the user has set WSCTX_DISABLE_ONNX=1.
        if backend == "default":
            if os.environ.get("WSCTX_DISABLE_ONNX", "").strip() == "1":
                pass  # keep PyTorch
            elif os.environ.get("WSCTX_ENABLE_ONNX", "").strip() == "1":
                backend = "onnx"  # legacy explicit opt-in
            elif _onnx_available():
                backend = "onnx"  # auto-detect: use ONNX when available

        # Memory guard — checked before touching the registry
        threshold_mb = int(os.environ.get("WSCTX_MEMORY_THRESHOLD_MB", DEFAULT_MEMORY_THRESHOLD_MB))
        try:
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
            if available_mb < threshold_mb:
                logger.warning(
                    f"[ModelRegistry] Insufficient RAM: {available_mb:.0f}MB available, "
                    f"{threshold_mb}MB required. Skipping model load."
                )
                return None
        except Exception:
            pass  # If psutil fails, proceed optimistically

        # When preloading is disabled, skip the registry entirely
        if os.environ.get("WSCTX_DISABLE_MODEL_PRELOAD", "").strip() == "1":
            return cls._load_model(model_name, device, backend)

        cache_key = (model_name, device, backend)

        # Fast path — no lock required when already cached
        cached = cls._registry.get(cache_key)
        if cached is not None:
            return cached

        # Slow path — acquire lock and double-check
        with cls._lock:
            cached = cls._registry.get(cache_key)
            if cached is not None:
                return cached

            model = cls._load_model(model_name, device, backend)
            if model is not None:
                cls._registry[cache_key] = model
            return model

    @classmethod
    def _load_model(cls, model_name: str, device: str, backend: str) -> Any | None:
        """Load a SentenceTransformer model.

        Args:
            model_name: HuggingFace model ID.
            device: Target device.
            backend: ``"onnx"`` for ONNX runtime; anything else uses default.

        Returns:
            Loaded model or ``None`` on failure.
        """
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

            kwargs: dict[str, Any] = {"device": device}
            if backend == "onnx":
                kwargs["backend"] = "onnx"

            logger.info(
                f"[ModelRegistry] Loading model={model_name} device={device} backend={backend}"
            )
            model = SentenceTransformer(model_name, **kwargs)

            # Warm up JIT / ONNX compilation with a single dummy encode
            model.encode(["warm-up"], show_progress_bar=False)

            logger.info(f"[ModelRegistry] Model loaded and warmed up: {model_name}")
            return model

        except ImportError:
            logger.warning("[ModelRegistry] sentence-transformers not installed")
            return None
        except Exception as e:
            logger.warning(f"[ModelRegistry] Failed to load model {model_name!r}: {e}")
            return None

    @classmethod
    def clear(cls) -> None:
        """Remove all cached models. Primarily for testing."""
        with cls._lock:
            cls._registry.clear()
