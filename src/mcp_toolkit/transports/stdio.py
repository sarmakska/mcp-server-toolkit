"""JSON-RPC over stdio for local agents (Claude Desktop, Cursor, etc)."""
import asyncio
import json
import sys

from ..registry import Registry


async def run_stdio(registry: Registry, settings) -> None:
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        try:
            msg = json.loads(line)
            response = await handle_message(msg, registry)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": msg.get("id") if "msg" in dir() else None,
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


async def handle_message(msg: dict, registry: Registry) -> dict:
    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": registry.list_tools()}}

    if method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        result = await registry.call(name, args)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": str(result)}]},
        }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }
