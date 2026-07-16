import pytest

from rag_assistant.common.ratelimit import (
    RateLimitError,
    Throttle,
    is_rate_limit_error,
    with_retry,
)


class _Status429(Exception):
    status_code = 429


def test_detects_rate_limit_variants():
    assert is_rate_limit_error(RateLimitError())
    assert is_rate_limit_error(_Status429())
    assert is_rate_limit_error(Exception("429 Too Many Requests"))
    assert is_rate_limit_error(Exception("RESOURCE_EXHAUSTED: quota"))
    assert not is_rate_limit_error(ValueError("bad input"))


def test_with_retry_recovers_after_transient_429():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("429")
        return "ok"

    wrapped = with_retry(flaky, max_attempts=5, initial_wait=0, max_wait=0)
    assert wrapped() == "ok"
    assert calls["n"] == 3


def test_with_retry_gives_up_and_reraises():
    def always_429():
        raise RateLimitError("429")

    wrapped = with_retry(always_429, max_attempts=3, initial_wait=0, max_wait=0)
    with pytest.raises(RateLimitError):
        wrapped()


def test_with_retry_does_not_retry_other_errors():
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise ValueError("bad input value")

    wrapped = with_retry(boom, max_attempts=5, initial_wait=0, max_wait=0)
    with pytest.raises(ValueError):
        wrapped()
    assert calls["n"] == 1


def test_throttle_sleeps_to_respect_rpm():
    now = {"t": 0.0}
    slept = []

    def clock() -> float:
        return now["t"]

    def sleep(secs: float) -> None:
        slept.append(secs)
        now["t"] += secs  # avança o relógio como um sleep real faria

    th = Throttle(rpm=60, clock=clock, sleep=sleep)  # min_interval = 1.0s
    th.wait()  # primeira chamada: sem espera (last=0, elapsed=0 < 1 -> dorme 1.0)
    now["t"] += 0.25  # passou só 0,25s desde a última
    th.wait()  # deve dormir ~0,75s
    assert slept[0] == pytest.approx(1.0)
    assert slept[1] == pytest.approx(0.75)
