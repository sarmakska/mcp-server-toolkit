"""
MCP 1.0 JSON-RPC dispatch shared by the stdio and HTTP transports.

This module implements the Model Context Protocol message handling once so both
transports behave identically. It covers the ``initialize`` handshake with
protocol version negotiation, the ``notifications/initialized`` acknowledgement,
``ping``, ``tools/list`` and ``tools/call``. Tool results are returned in the
MCP content-block shape, with structured results surfaced through
``structuredContent`` when a tool declares an output schema.

JSON-RPC 2.0 batch requests (a top-level array of messages) are handled by
:func:`dispatch_batch`, which both transports call. A batch yields an array of
responses with notifications omitted, an empty array is an invalid request, and
a batch made entirely of notifications produces no response at all, matching the
JSON-RPC specification. MCP revision ``2025-06-18`` removed batching, so a batch
is only a transport-level concern for clients negotiating an earlier revision;
the dispatcher accepts it regardless rather than rejecting older clients.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

from . import __version__
from .registry import Registry, ToolValidationError

log = structlog.get_logger("mcp-toolkit.protocol")

# Protocol revisions this server speaks, newest first. The client proposes one
# in ``initialize``; we echo it back if we support it, otherwise we answer with
# our most recent supported revision.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

SERVER_INFO = {"name": "mcp-server-toolkit", "version": __version__}

# JSON-RPC error codes used by MCP.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _result(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def negotiate_protocol_version(requested: str | None) -> str:
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return LATEST_PROTOCOL_VERSION


def _content_blocks(result: Any) -> dict[str, Any]:
    """Render a handler return value as an MCP ``tools/call`` result.

    Strings become a single text block. Anything else is JSON-encoded into a
    text block and also attached as ``structuredContent`` so clients that
    understand structured output can consume it directly.
    """
    if isinstance(result, str):
        return {"content": [{"type": "text", "text": result}], "isError": False}

    text = json.dumps(result, ensure_ascii=False, default=str)
    block: dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "isError": False,
    }
    if isinstance(result, dict):
        block["structuredContent"] = result
    return block


async def dispatch(message: dict[str, Any], registry: Registry) -> dict[str, Any] | None:
    """Handle a single JSON-RPC message and return the response.

    Returns ``None`` for notifications (messages without an ``id``), which must
    not produce a response per the JSON-RPC specification.
    """
    if not isinstance(message, dict):
        return _error(None, INVALID_REQUEST, "Request must be a JSON object")

    if message.get("jsonrpc") != "2.0":
        return _error(message.get("id"), INVALID_REQUEST, "jsonrpc must be '2.0'")

    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}
    is_notification = "id" not in message

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = negotiate_protocol_version(requested)
        log.info("initialize", requested_version=requested, agreed_version=version)
        return _result(
            msg_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method in ("notifications/initialized", "initialized"):
        # Acknowledgement notification. No response.
        return None

    if method == "ping":
        return _result(msg_id, {})

    if method == "tools/list":
        return _result(msg_id, {"tools": registry.list_tools()})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not name:
            return _error(msg_id, INVALID_PARAMS, "tools/call requires a 'name'")
        try:
            result = await registry.call(name, arguments)
        except KeyError:
            return _error(msg_id, METHOD_NOT_FOUND, f"Unknown tool: {name}")
        except ToolValidationError as err:
            return _error(msg_id, INVALID_PARAMS, str(err))
        except Exception as err:  # surfaced to the client as a tool error
            log.error("tool_call_exception", tool=name, error=str(err))
            return _result(
                msg_id,
                {
                    "content": [{"type": "text", "text": str(err)}],
                    "isError": True,
                },
            )
        return _result(msg_id, _content_blocks(result))

    if is_notification:
        # Unknown notification: ignore silently per spec.
        return None

    return _error(msg_id, METHOD_NOT_FOUND, f"Unknown method: {method}")


async def dispatch_batch(
    payload: Any, registry: Registry
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Dispatch a single JSON-RPC message or a JSON-RPC 2.0 batch.

    A batch is a top-level JSON array of request and notification objects. The
    members are dispatched concurrently and the responses returned in a list,
    with notification members (which have no ``id``) omitted. Per the JSON-RPC
    specification an empty batch array is itself an invalid request, and a batch
    that contains only notifications yields no response at all (``None``), which
    a transport renders as an empty body.

    A non-array payload is dispatched as a single message, so callers can route
    both shapes through this one entry point.
    """
    if not isinstance(payload, list):
        return await dispatch(payload, registry)

    if not payload:
        return _error(None, INVALID_REQUEST, "Batch must not be empty")

    responses = await asyncio.gather(
        *(dispatch(message, registry) for message in payload)
    )
    return [r for r in responses if r is not None] or None
