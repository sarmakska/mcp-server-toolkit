"""Streamable HTTP transport via FastAPI.

Exposes the MCP JSON-RPC endpoint at ``POST /mcp`` plus a small REST surface
(``/health``, ``/tools``, ``POST /tools/{name}``) for quick inspection and
health probing. Authentication and per-client rate limiting are enforced on the
protected routes; ``/health`` is always open so it works as a readiness probe.
"""
from __future__ import annotations

import time

import structlog
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request

from ..auth import OAuthError, OAuthVerifier, RateLimiter, verify_api_key
from ..config import Settings
from ..protocol import dispatch
from ..registry import Registry, ToolValidationError

log = structlog.get_logger("mcp-toolkit.http")


def _client_id(request: Request) -> str:
    return (
        request.headers.get("x-api-key")
        or request.headers.get("authorization", "")
        or (request.client.host if request.client else "anonymous")
    )


def make_app(registry: Registry, settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="mcp-server-toolkit")
    started_at = time.monotonic()

    verifier: OAuthVerifier | None = None
    if settings.auth == "oauth":
        verifier = OAuthVerifier(
            issuer=settings.oauth_issuer,
            audience=settings.oauth_audience,
            jwks_uri=settings.oauth_jwks_uri,
        )

    limiter: RateLimiter | None = None
    if settings.rate_limit_rps > 0:
        limiter = RateLimiter(
            rate=settings.rate_limit_rps,
            burst=settings.rate_limit_burst or None,
        )

    async def authenticate(request: Request) -> None:
        if settings.auth == "none":
            pass
        elif settings.auth == "api_key":
            if not verify_api_key(request.headers.get("x-api-key"), settings.api_key):
                raise HTTPException(401, "Invalid or missing API key")
        elif settings.auth == "oauth":
            header = request.headers.get("authorization", "")
            if not header.lower().startswith("bearer "):
                raise HTTPException(401, "Missing bearer token")
            token = header.split(" ", 1)[1]
            assert verifier is not None
            try:
                await verifier.verify(token)
            except OAuthError as err:
                raise HTTPException(401, str(err)) from err
        else:
            raise HTTPException(500, f"Unknown auth mode: {settings.auth}")

        if limiter is not None and not limiter.allow(_client_id(request)):
            raise HTTPException(429, "Rate limit exceeded")

    @app.get("/health")
    async def health() -> dict:
        return {
            "ok": True,
            "tools_registered": len(registry.tools),
            "uptime_seconds": round(time.monotonic() - started_at, 1),
        }

    @app.post("/mcp")
    async def mcp_endpoint(request: Request, _: None = Depends(authenticate)) -> dict | None:
        message = await request.json()
        return await dispatch(message, registry)

    @app.get("/tools")
    async def list_tools(_: None = Depends(authenticate)) -> dict:
        return {"tools": registry.list_tools()}

    @app.post("/tools/{name}")
    async def call_tool(
        name: str, request: Request, _: None = Depends(authenticate)
    ) -> dict:
        body = await request.json()
        try:
            result = await registry.call(name, body or {})
            return {"result": result}
        except KeyError as err:
            raise HTTPException(404, f"Tool {name} not found") from err
        except ToolValidationError as err:
            raise HTTPException(422, str(err)) from err

    return app


async def run_http(registry: Registry, settings: Settings) -> None:
    app = make_app(registry, settings)
    log.info(
        "http_transport_start",
        host=settings.http_host,
        port=settings.http_port,
        auth=settings.auth,
    )
    config = uvicorn.Config(
        app, host=settings.http_host, port=settings.http_port, log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()
