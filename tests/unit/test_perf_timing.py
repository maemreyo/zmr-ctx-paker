"""Tests for the perf.timing module (Phase 0 — written BEFORE implementation)."""

import logging
import time
from unittest.mock import patch

import pytest

from ws_ctx_engine.perf.timing import TimingContext, timed


# ---------------------------------------------------------------------------
# @timed decorator tests
# ---------------------------------------------------------------------------


def test_timed_decorator_returns_correct_value() -> None:
    """Decorated function must return its original value unchanged."""

    @timed("test_op")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5


def test_timed_decorator_records_elapsed_ms(caplog: pytest.LogCaptureFixture) -> None:
    """@timed must emit a log line containing the label and elapsed_ms."""
    with caplog.at_level(logging.DEBUG, logger="wsctx.perf"):

        @timed("my_label")
        def slow() -> str:
            time.sleep(0.02)
            return "done"

        slow()

    # At least one log record should mention our label
    messages = " ".join(r.message for r in caplog.records)
    assert "my_label" in messages
    assert "ms" in messages


def test_timed_decorator_elapsed_is_positive(caplog: pytest.LogCaptureFixture) -> None:
    """Elapsed time recorded must be > 0."""

    @timed("pos_check")
    def noop() -> None:
        pass

    with caplog.at_level(logging.DEBUG, logger="wsctx.perf"):
        noop()

    # Find the record for pos_check
    for record in caplog.records:
        if "pos_check" in record.message:
            # Extract ms value – simple check that a positive number appears
            import re

            matches = re.findall(r"[\d.]+\s*ms", record.message)
            assert matches, f"No ms value in log: {record.message}"
            ms_val = float(matches[0].replace("ms", "").strip())
            assert ms_val >= 0


def test_timed_decorator_propagates_exceptions() -> None:
    """@timed must not swallow exceptions raised by the wrapped function."""

    @timed("error_op")
    def boom() -> None:
        raise ValueError("intentional error")

    with pytest.raises(ValueError, match="intentional error"):
        boom()


def test_timed_decorator_propagates_exceptions_and_still_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Timing must still be logged even when the function raises."""

    @timed("err_log")
    def fail() -> None:
        raise RuntimeError("oops")

    with caplog.at_level(logging.DEBUG, logger="wsctx.perf"):
        with pytest.raises(RuntimeError):
            fail()

    messages = " ".join(r.message for r in caplog.records)
    assert "err_log" in messages


def test_timed_decorator_works_with_kwargs() -> None:
    """Decorated function must accept keyword arguments normally."""

    @timed("kw_op")
    def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}"

    assert greet(name="World", greeting="Hi") == "Hi, World"


def test_timed_decorator_preserves_function_name() -> None:
    """functools.wraps must preserve the __name__ of the wrapped function."""

    @timed("preserve")
    def my_func() -> None:
        pass

    assert my_func.__name__ == "my_func"


# ---------------------------------------------------------------------------
# TimingContext tests
# ---------------------------------------------------------------------------


def test_timing_context_manager_records_elapsed(caplog: pytest.LogCaptureFixture) -> None:
    """TimingContext must log elapsed time on exit."""
    with caplog.at_level(logging.DEBUG, logger="wsctx.perf"):
        with TimingContext("ctx_label"):
            time.sleep(0.01)

    messages = " ".join(r.message for r in caplog.records)
    assert "ctx_label" in messages
    assert "ms" in messages


def test_timing_context_manager_propagates_exceptions() -> None:
    """TimingContext must not swallow exceptions raised inside the block."""
    with pytest.raises(ZeroDivisionError):
        with TimingContext("ctx_err"):
            _ = 1 / 0


def test_timing_context_manager_logs_on_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TimingContext must still log even when an exception occurs inside."""
    with caplog.at_level(logging.DEBUG, logger="wsctx.perf"):
        with pytest.raises(ZeroDivisionError):
            with TimingContext("ctx_exc_log"):
                _ = 1 / 0

    messages = " ".join(r.message for r in caplog.records)
    assert "ctx_exc_log" in messages
