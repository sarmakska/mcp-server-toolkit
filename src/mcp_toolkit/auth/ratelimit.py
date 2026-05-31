"""Per-client token bucket rate limiting.

A simple in-process token bucket keyed by client identity (API key, OAuth
subject, or remote address). It needs no external store, which keeps a single
instance dependency-free; put a shared limiter in front when you run several
replicas.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Token bucket allowing ``rate`` requests per second with ``burst`` depth.

    Parameters
    ----------
    rate:
        Sustained requests per second permitted per client.
    burst:
        Maximum number of requests that can be made instantaneously. Defaults to
        ``rate`` so a client may spend a full second of budget at once.
    """

    def __init__(self, rate: float, burst: int | None = None) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.rate = rate
        self.burst = float(burst if burst is not None else rate)
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, client: str, cost: float = 1.0) -> bool:
        """Consume ``cost`` tokens for ``client``; return False if exhausted."""
        now = time.monotonic()
        bucket = self._buckets.get(client)
        if bucket is None:
            bucket = _Bucket(tokens=self.burst, last_refill=now)
            self._buckets[client] = bucket
        else:
            elapsed = now - bucket.last_refill
            bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate)
            bucket.last_refill = now

        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return True
        return False
