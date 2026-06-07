"""MCP 1.0 JSON-RPC dispatch behaviour, shared by both transports."""
import json

from mcp_toolkit.protocol import (
    INVALID_REQUEST,
    LATEST_PROTOCOL_VERSION,
    dispatch,
    dispatch_batch,
    negotiate_protocol_version,
)


def test_protocol_version_negotiation():
    assert negotiate_protocol_version("2025-06-18") == "2025-06-18"
    assert negotiate_protocol_version("2024-11-05") == "2024-11-05"
    assert negotiate_protocol_version("1999-01-01") == LATEST_PROTOCOL_VERSION
    assert negotiate_protocol_version(None) == LATEST_PROTOCOL_VERSION


async def test_initialize_handshake(registry_with_tools):
    resp = await dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}},
        },
        registry_with_tools,
    )
    assert resp["result"]["protocolVersion"] == "2025-06-18"
    assert resp["result"]["serverInfo"]["name"] == "mcp-server-toolkit"
    assert "tools" in resp["result"]["capabilities"]


async def test_initialized_notification_has_no_response(registry_with_tools):
    resp = await dispatch(
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        registry_with_tools,
    )
    assert resp is None


async def test_ping(registry_with_tools):
    resp = await dispatch({"jsonrpc": "2.0", "id": 7, "method": "ping"}, registry_with_tools)
    assert resp == {"jsonrpc": "2.0", "id": 7, "result": {}}


async def test_tools_list(registry_with_tools):
    resp = await dispatch(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, registry_with_tools
    )
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == {"echo", "add"}


async def test_tools_call_text_result(registry_with_tools):
    resp = await dispatch(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"message": "hello"}},
        },
        registry_with_tools,
    )
    assert resp["result"]["content"][0]["text"] == "hello"
    assert resp["result"]["isError"] is False


async def test_tools_call_structured_result(registry_with_tools):
    resp = await dispatch(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 2, "b": 5}},
        },
        registry_with_tools,
    )
    assert resp["result"]["structuredContent"] == {"sum": 7}
    assert json.loads(resp["result"]["content"][0]["text"]) == {"sum": 7}


async def test_tools_call_validation_error(registry_with_tools):
    resp = await dispatch(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": "x", "b": 1}},
        },
        registry_with_tools,
    )
    assert resp["error"]["code"] == -32602


async def test_unknown_tool_is_method_not_found(registry_with_tools):
    resp = await dispatch(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "ghost", "arguments": {}},
        },
        registry_with_tools,
    )
    assert resp["error"]["code"] == -32601


async def test_unknown_method(registry_with_tools):
    resp = await dispatch(
        {"jsonrpc": "2.0", "id": 8, "method": "does/notexist"}, registry_with_tools
    )
    assert resp["error"]["code"] == -32601


async def test_non_object_message_is_invalid_request(registry_with_tools):
    resp = await dispatch("not-an-object", registry_with_tools)
    assert resp["error"]["code"] == INVALID_REQUEST
    assert resp["id"] is None


async def test_dispatch_batch_single_message(registry_with_tools):
    resp = await dispatch_batch(
        {"jsonrpc": "2.0", "id": 1, "method": "ping"}, registry_with_tools
    )
    assert resp == {"jsonrpc": "2.0", "id": 1, "result": {}}


async def test_dispatch_batch_returns_responses_in_order(registry_with_tools):
    batch = [
        {"jsonrpc": "2.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 2, "b": 3}},
        },
    ]
    resp = await dispatch_batch(batch, registry_with_tools)
    assert isinstance(resp, list)
    assert [r["id"] for r in resp] == [1, 2, 3]
    assert resp[0]["result"] == {}
    assert resp[2]["result"]["structuredContent"] == {"sum": 5}


async def test_dispatch_batch_omits_notification_responses(registry_with_tools):
    batch = [
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 9, "method": "ping"},
    ]
    resp = await dispatch_batch(batch, registry_with_tools)
    assert isinstance(resp, list)
    assert len(resp) == 1
    assert resp[0]["id"] == 9


async def test_dispatch_batch_all_notifications_returns_none(registry_with_tools):
    batch = [
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ]
    resp = await dispatch_batch(batch, registry_with_tools)
    assert resp is None


async def test_dispatch_batch_empty_array_is_invalid_request(registry_with_tools):
    resp = await dispatch_batch([], registry_with_tools)
    assert resp["error"]["code"] == INVALID_REQUEST


async def test_dispatch_batch_invalid_member_yields_error_in_batch(registry_with_tools):
    batch = [
        {"jsonrpc": "2.0", "id": 1, "method": "ping"},
        "not-an-object",
    ]
    resp = await dispatch_batch(batch, registry_with_tools)
    assert isinstance(resp, list)
    assert len(resp) == 2
    assert resp[1]["error"]["code"] == INVALID_REQUEST
