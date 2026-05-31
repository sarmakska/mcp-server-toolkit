"""End-to-end stdio transport driven through real stdin/stdout."""
import io
import json

import pytest

from mcp_toolkit.transports import stdio


async def _drive(monkeypatch, registry, messages):
    """Feed JSON-RPC lines through run_stdio and capture the output lines."""
    stdin = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
    stdout = io.StringIO()
    monkeypatch.setattr(stdio.sys, "stdin", stdin)
    monkeypatch.setattr(stdio.sys, "stdout", stdout)
    await stdio.run_stdio(registry, None)
    return [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]


async def test_stdio_initialize_then_call(monkeypatch, registry_with_tools):
    out = await _drive(
        monkeypatch,
        registry_with_tools,
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {"message": "ping"}},
            },
        ],
    )
    # initialize, tools/list, tools/call all answer; the notification does not.
    assert len(out) == 3
    assert out[0]["result"]["serverInfo"]["name"] == "mcp-server-toolkit"
    assert {t["name"] for t in out[1]["result"]["tools"]} == {"echo", "add"}
    assert out[2]["result"]["content"][0]["text"] == "ping"


async def test_stdio_parse_error(monkeypatch, registry_with_tools):
    stdin = io.StringIO("this is not json\n")
    stdout = io.StringIO()
    monkeypatch.setattr(stdio.sys, "stdin", stdin)
    monkeypatch.setattr(stdio.sys, "stdout", stdout)
    await stdio.run_stdio(registry_with_tools, None)
    resp = json.loads(stdout.getvalue().strip())
    assert resp["error"]["code"] == -32700


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
async def test_stdio_skips_blank_lines(monkeypatch, registry_with_tools, blank):
    out = await _drive(
        monkeypatch,
        registry_with_tools,
        [{"jsonrpc": "2.0", "id": 1, "method": "ping"}],
    )
    assert out[0]["result"] == {}
