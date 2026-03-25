from context_packer.mcp.security.rate_limiter import RateLimiter


def test_rate_limiter_allows_unconfigured_tool() -> None:
    limiter = RateLimiter({"search_codebase": 1})
    allowed, retry_after = limiter.allow("unknown_tool")
    assert allowed is True
    assert retry_after == 0


def test_rate_limiter_refills_token_bucket_and_allows_again(monkeypatch) -> None:
    limiter = RateLimiter({"search_codebase": 1})

    ticks = iter([100.0, 100.5, 161.0])
    monkeypatch.setattr("context_packer.mcp.security.rate_limiter.time.monotonic", lambda: next(ticks))

    first_allowed, _ = limiter.allow("search_codebase")
    assert first_allowed is True

    second_allowed, retry = limiter.allow("search_codebase")
    assert second_allowed is False
    assert retry > 0

    third_allowed, third_retry = limiter.allow("search_codebase")
    assert third_allowed is True
    assert third_retry == 0


def test_rate_limiter_allows_non_positive_configured_limit() -> None:
    limiter = RateLimiter({"search_codebase": 0})
    allowed, retry_after = limiter.allow("search_codebase")
    assert allowed is True
    assert retry_after == 0


def test_rate_limiter_retry_after_has_minimum_of_one(monkeypatch) -> None:
    limiter = RateLimiter({"search_codebase": 1})

    ticks = iter([100.0, 159.9])
    monkeypatch.setattr("context_packer.mcp.security.rate_limiter.time.monotonic", lambda: next(ticks))

    first_allowed, _ = limiter.allow("search_codebase")
    assert first_allowed is True

    second_allowed, retry_after = limiter.allow("search_codebase")
    assert second_allowed is False
    assert retry_after == 1


def test_rate_limiter_honors_bucket_capacity_burst(monkeypatch) -> None:
    limiter = RateLimiter({"search_codebase": 2})

    ticks = iter([100.0, 100.1, 100.2])
    monkeypatch.setattr("context_packer.mcp.security.rate_limiter.time.monotonic", lambda: next(ticks))

    first_allowed, _ = limiter.allow("search_codebase")
    second_allowed, _ = limiter.allow("search_codebase")
    third_allowed, retry_after = limiter.allow("search_codebase")

    assert first_allowed is True
    assert second_allowed is True
    assert third_allowed is False
    assert retry_after >= 1
