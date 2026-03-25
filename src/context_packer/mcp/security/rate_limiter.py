from __future__ import annotations

import math
import time
from dataclasses import dataclass


@dataclass
class _BucketState:
    tokens: float
    last_refill_monotonic: float


class RateLimiter:
    def __init__(self, limits_per_minute: dict[str, int]) -> None:
        self._limits = limits_per_minute
        self._states: dict[str, _BucketState] = {}

    def allow(self, key: str) -> tuple[bool, int]:
        limit = self._limits.get(key)
        if limit is None or limit <= 0:
            return True, 0

        now = time.monotonic()
        capacity = float(limit)
        refill_rate_per_second = capacity / 60.0

        state = self._states.get(key)
        if state is None:
            state = _BucketState(tokens=capacity, last_refill_monotonic=now)

        elapsed = max(0.0, now - state.last_refill_monotonic)
        state.tokens = min(capacity, state.tokens + (elapsed * refill_rate_per_second))
        state.last_refill_monotonic = now

        if state.tokens >= 1.0:
            state.tokens -= 1.0
            self._states[key] = state
            return True, 0

        seconds_until_next_token = (1.0 - state.tokens) / refill_rate_per_second
        retry_after = max(1, int(math.ceil(seconds_until_next_token)))
        self._states[key] = state
        return False, retry_after
