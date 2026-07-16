"""Resiliência de quota do free tier: backoff em 429 + throttle de RPM (RNF-09).

Os providers levantam exceções diferentes para "limite de taxa"; `is_rate_limit_error`
normaliza a detecção. `with_retry` faz backoff exponencial só nesses casos.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

T = TypeVar("T")


class RateLimitError(Exception):
    """Limite de taxa do free tier (equivalente a HTTP 429)."""


def is_rate_limit_error(exc: BaseException) -> bool:
    """Detecta 429/quota entre as várias exceções dos providers."""
    if isinstance(exc, RateLimitError):
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status == 429:
        return True
    text = str(exc).lower()
    needles = ("429", "rate limit", "resource_exhausted", "quota", "too many requests")
    return any(n in text for n in needles)


def with_retry(
    fn: Callable[..., T],
    *,
    max_attempts: int = 5,
    initial_wait: float = 1.0,
    max_wait: float = 30.0,
) -> Callable[..., T]:
    """Envolve uma chamada de provider com backoff exponencial apenas em 429."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=initial_wait, max=max_wait),
        retry=retry_if_exception(is_rate_limit_error),
    )(fn)


class Throttle:
    """Garante um intervalo mínimo entre chamadas (respeita o RPM do free tier)."""

    def __init__(
        self,
        rpm: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rpm <= 0:
            raise ValueError("rpm deve ser > 0")
        self._min_interval = 60.0 / rpm
        self._clock = clock
        self._sleep = sleep
        self._last = 0.0

    def wait(self) -> None:
        elapsed = self._clock() - self._last
        if elapsed < self._min_interval:
            self._sleep(self._min_interval - elapsed)
        self._last = self._clock()
