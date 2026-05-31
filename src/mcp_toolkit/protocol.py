"""
MCP 1.0 JSON-RPC dispatch shared by the stdio and HTTP transports.

This module implements the Model Context Protocol message handling once so both
transports behave identically. It covers the ``initialize`` handshake with
protocol version negotiation, the ``notifications/initialized`` acknowledgement,
``ping``, ``tools/list`` and ``tools/call``. Tool results are returned in the
MCP content-block shape, with structured results surfaced through
``structuredContent`` when a tool declares an output schema.
"""
from __future__ import annotations

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
