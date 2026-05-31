"""Shared fixtures for the test suite."""
import os

import pytest

from mcp_toolkit.registry import Registry


@pytest.fixture
def fs_sandbox(tmp_path, monkeypatch):
    """Point the filesystem plugin sandbox at a throwaway directory."""
    monkeypatch.setenv("MCP_FS_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def registry_with_tools():
    """A fresh registry with a couple of well-typed tools for protocol tests."""
    reg = Registry()

    @reg.tool("echo", description="Echo back the message")
    async def echo(message: str) -> str:
        return message

    @reg.tool(
        "add",
        description="Add two integers",
        output_schema={"type": "object", "properties": {"sum": {"type": "integer"}}},
    )
    async def add(a: int, b: int) -> dict:
        return {"sum": a + b}

    return reg


@pytest.fixture(autouse=True)
def _clean_otel_env(monkeypatch):
    monkeypatch.delenv("MCP_OTEL_ENDPOINT", raising=False)
    yield
    os.environ.pop("MCP_FS_ROOT", None)
