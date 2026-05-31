"""OAuth 2.1 resource server verification.

The HTTP transport acts as an OAuth 2.1 protected resource. Bearer tokens are
validated as JWTs against the issuer's published JWKS, with issuer and audience
checks. Keys are cached and refreshed lazily so a key rotation upstream does not
require a restart.

The matching client side of the flow, used to obtain a token against a hosted
server, lives in :mod:`mcp_toolkit.oauth_client`.
"""
from __future__ import annotations

import time
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import JWTError


class OAuthError(Exception):
    """Raised when a bearer token cannot be validated."""


class OAuthVerifier:
    """Validate bearer tokens against an OpenID Connect issuer.

    Parameters
    ----------
    issuer:
        The token issuer. Used to discover the JWKS URI when one is not given
        and checked against the ``iss`` claim.
    audience:
        Expected ``aud`` claim. The token is rejected if it does not match.
    jwks_uri:
        Optional explicit JWKS endpoint. When omitted it is derived from the
        issuer's ``/.well-known/openid-configuration`` document.
    cache_ttl:
        Seconds to cache fetched JWKS before refetching.
    """

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_uri: str = "",
        cache_ttl: int = 3600,
        algorithms: tuple[str, ...] = ("RS256", "ES256", "RS384", "RS512"),
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self._jwks_uri = jwks_uri
        self.cache_ttl = cache_ttl
        self.algorithms = list(algorithms)
        self._jwks: dict[str, Any] | None = None
        self._fetched_at = 0.0

    async def _discover_jwks_uri(self, client: httpx.AsyncClient) -> str:
        if self._jwks_uri:
            return self._jwks_uri
        url = f"{self.issuer}/.well-known/openid-configuration"
        resp = await client.get(url)
        resp.raise_for_status()
        jwks_uri = resp.json().get("jwks_uri")
        if not jwks_uri:
            raise OAuthError("Issuer discovery document has no jwks_uri")
        self._jwks_uri = jwks_uri
        return jwks_uri

    async def _get_jwks(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._jwks is not None and (now - self._fetched_at) < self.cache_ttl:
            return self._jwks
        async with httpx.AsyncClient(timeout=10) as client:
            jwks_uri = await self._discover_jwks_uri(client)
            resp = await client.get(jwks_uri)
            resp.raise_for_status()
            self._jwks = resp.json()
            self._fetched_at = now
        return self._jwks

    async def verify(self, token: str) -> dict[str, Any]:
        """Validate a bearer token and return its claims, or raise OAuthError."""
        if not token:
            raise OAuthError("Missing bearer token")
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as err:
            raise OAuthError(f"Malformed token: {err}") from err

        jwks = await self._get_jwks()
        kid = header.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key is None:
            # Possible rotation: drop the cache and try once more.
            self._jwks = None
            jwks = await self._get_jwks()
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key is None:
            raise OAuthError("No matching signing key for token")

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                options={"require_exp": True},
            )
        except JWTError as err:
            raise OAuthError(f"Token rejected: {err}") from err
        return claims
