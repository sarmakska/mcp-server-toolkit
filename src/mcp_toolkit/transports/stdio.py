"""JSON-RPC 2.0 over stdio for local agents (desktop clients, IDEs).

Each line of stdin is one JSON-RPC message, or a JSON-RPC 2.0 batch (an array of
messages) on a single line. The shared MCP dispatcher in
:mod:`mcp_toolkit.protocol` produces the response; notifications produce no
output, as the JSON-RPC specification requires.
"""
from __future__ import annotations

import asyncio
import json
import sys

import structlog

from ..protocol import PARSE_ERROR, dispatch_batch
from ..registry import Registry

log = structlog.get_logger("mcp-toolkit.stdio")


def _write(response: dict | list) -> None:
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


async def run_stdio(registry: Registry, settings=None) -> None:
    loop = asyncio.get_event_loop()
    log.info("stdio_transport_start")
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as err:
            _write(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": PARSE_ERROR, "message": f"Parse error: {err}"},
                }
            )
            continue

        response = await dispatch_batch(message, registry)
        if response is not None:
            _write(response)
