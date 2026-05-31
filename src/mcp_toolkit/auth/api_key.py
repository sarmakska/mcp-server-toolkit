"""Header-based API key authentication.

Clients present a key in the ``X-API-Key`` header. The comparison is constant
time so the check does not leak the configured key through timing.
"""
from __future__ import annotations

import hmac


def verify_api_key(presented: str | None, expected: str) -> bool:
    """Return True when ``presented`` matches ``expected`` in constant time.

    An empty configured key means the server has not been set up for API key
    auth, so no request can satisfy it.
    """
    if not expected or not presented:
        return False
    return hmac.compare_digest(presented, expected)
