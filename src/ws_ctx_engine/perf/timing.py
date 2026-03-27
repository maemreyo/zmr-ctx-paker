"""Lightweight timing instrumentation for hot-path profiling.

Provides a ``@timed`` decorator and a ``TimingContext`` context manager that
emit structured log lines so latency can be captured without a heavy profiler.

Example log output::

    DEBUG ws_ctx_engine.perf.timing - [perf] leann_search elapsed=123.4ms
"""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

# Use a logger name NOT under "ws_ctx_engine" so records propagate to root.
# The custom WsCtxEngineLogger sets propagate=False on "ws_ctx_engine", which
# would block child loggers from reaching pytest's caplog handler.
logger = logging.getLogger("wsctx.perf")

F = TypeVar("F", bound=Callable[..., Any])


def timed(label: str) -> Callable[[F], F]:
    """Decorator that logs wall-clock elapsed time for the wrapped function.

    Args:
        label: Short identifier used in the log line (e.g. ``"leann_search"``).

    Returns:
        Decorator that wraps the function with timing instrumentation.

    Example::

        @timed("embedding_encode")
        def encode(texts: list[str]) -> np.ndarray:
            ...
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                logger.debug(f"[perf] {label} elapsed={elapsed_ms:.1f}ms")

        return wrapper  # type: ignore[return-value]

    return decorator


class TimingContext:
    """Context manager that logs wall-clock elapsed time for a code block.

    Args:
        label: Short identifier used in the log line.

    Example::

        with TimingContext("pagerank_compute"):
            scores = graph.pagerank()
    """

    def __init__(self, label: str) -> None:
        self.label = label
        self._t0: float = 0.0

    def __enter__(self) -> "TimingContext":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        elapsed_ms = (time.perf_counter() - self._t0) * 1000
        logger.debug(f"[perf] {self.label} elapsed={elapsed_ms:.1f}ms")
        # Always return None (falsy) so exceptions propagate
