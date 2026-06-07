"""End-to-end HTTP transport: MCP endpoint, REST surface, auth, rate limiting."""
import pytest
from fastapi.testclient import TestClient

from mcp_toolkit.config import Settings
from mcp_toolkit.transports.http import make_app


@pytest.fixture
def client(registry_with_tools):
    app = make_app(registry_with_tools, Settings(auth="none"))
    return TestClient(app)


def test_health_reports_tools_and_uptime(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["tools_registered"] == 2
    assert "uptime_seconds" in body


def test_mcp_full_handshake_and_call(client):
    init = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        },
    )
    assert init.json()["result"]["serverInfo"]["name"] == "mcp-server-toolkit"

    call = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 4, "b": 6}},
        },
    )
    assert call.json()["result"]["structuredContent"] == {"sum": 10}


def test_mcp_batch_request_returns_array(client):
    resp = client.post(
        "/mcp",
        json=[
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "add", "arguments": {"a": 1, "b": 1}},
            },
        ],
    )
    body = resp.json()
    assert isinstance(body, list)
    assert [r["id"] for r in body] == [1, 2]
    assert body[1]["result"]["structuredContent"] == {"sum": 2}


def test_mcp_malformed_json_returns_parse_error(client):
    resp = client.post(
        "/mcp", content="{not json", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 200
    assert resp.json()["error"]["code"] == -32700


def test_rest_tools_listing(client):
    resp = client.get("/tools")
    names = {t["name"] for t in resp.json()["tools"]}
    assert names == {"echo", "add"}


def test_rest_call_validation_error_returns_422(client):
    resp = client.post("/tools/add", json={"a": "x", "b": 1})
    assert resp.status_code == 422


def test_api_key_auth_rejects_missing_key(registry_with_tools):
    app = make_app(registry_with_tools, Settings(auth="api_key", api_key="s3cret"))
    client = TestClient(app)
    assert client.get("/tools").status_code == 401
    assert client.get("/health").status_code == 200  # health is always open


def test_api_key_auth_accepts_valid_key(registry_with_tools):
    app = make_app(registry_with_tools, Settings(auth="api_key", api_key="s3cret"))
    client = TestClient(app)
    resp = client.get("/tools", headers={"X-API-Key": "s3cret"})
    assert resp.status_code == 200


def test_rate_limit_returns_429(registry_with_tools):
    settings = Settings(auth="none", rate_limit_rps=1, rate_limit_burst=2)
    client = TestClient(make_app(registry_with_tools, settings))
    codes = [client.get("/tools").status_code for _ in range(5)]
    assert 429 in codes
    assert codes[:2] == [200, 200]
