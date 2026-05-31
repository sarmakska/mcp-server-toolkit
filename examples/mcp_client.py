"""Minimal stdio MCP client: launch the server, handshake, list and call tools.

Run from the repository root:

    uv run python examples/mcp_client.py
"""
import json
import subprocess
import sys


def send(proc: subprocess.Popen, message: dict) -> dict | None:
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    if "id" not in message:
        return None
    line = proc.stdout.readline()
    return json.loads(line)


def main() -> None:
    proc = subprocess.Popen(
        ["uv", "run", "mcp-toolkit", "run", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        init = send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
        )
        print("protocol version:", init["result"]["protocolVersion"])

        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        tools = send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [t["name"] for t in tools["result"]["tools"]]
        print("tools:", names)

        call = send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "list_files", "arguments": {"path": "."}},
            },
        )
        print("list_files result:", json.dumps(call["result"], indent=2))
    finally:
        proc.stdin.close()
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
