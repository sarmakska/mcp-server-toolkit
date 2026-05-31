"""OAuth 2.1 client flow with PKCE for connecting to a hosted MCP server.

This is the client half of the auth story. Use it to obtain a bearer token
against an authorisation server, then present that token to a remote
mcp-server-toolkit instance running ``MCP_AUTH=oauth``. It implements the
authorisation code flow with PKCE (RFC 7636) and the device-independent pieces
of RFC 8414 metadata discovery.

The ``mcp-toolkit login`` command drives this end to end: it opens the
authorisation URL, runs a one-shot loopback server to capture the redirect, and
exchanges the code for a token.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


def generate_pkce_pair() -> tuple[str, str]:
    """Return a ``(verifier, challenge)`` PKCE pair using the S256 method."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


@dataclass
class AuthorizationServer:
    """Endpoints for an OAuth 2.1 authorisation server."""

    authorization_endpoint: str
    token_endpoint: str

    @classmethod
    async def discover(cls, issuer: str) -> AuthorizationServer:
        """Discover endpoints from RFC 8414 / OpenID Connect metadata."""
        issuer = issuer.rstrip("/")
        async with httpx.AsyncClient(timeout=10) as client:
            for suffix in (
                "/.well-known/oauth-authorization-server",
                "/.well-known/openid-configuration",
            ):
                resp = await client.get(f"{issuer}{suffix}")
                if resp.status_code == 200:
                    data = resp.json()
                    return cls(
                        authorization_endpoint=data["authorization_endpoint"],
                        token_endpoint=data["token_endpoint"],
                    )
        raise RuntimeError(f"Could not discover authorisation server metadata for {issuer}")


@dataclass
class OAuthClient:
    """Drives the PKCE authorisation code flow for a public client."""

    client_id: str
    redirect_uri: str
    server: AuthorizationServer
    scope: str = "openid profile"

    def build_authorization_url(self, challenge: str, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.server.authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str, verifier: str) -> dict:
        """Exchange an authorisation code plus PKCE verifier for tokens."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": verifier,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.server.token_endpoint,
                data=data,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
