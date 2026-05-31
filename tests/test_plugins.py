"""End-to-end exercise of the bundled plugins through the registry."""
import importlib

import pytest

from mcp_toolkit.registry import ToolValidationError, registry


def test_bundled_plugins_register():
    from mcp_toolkit.plugins import filesystem, sarmalink  # noqa: F401

    names = {t["name"] for t in registry.list_tools()}
    assert {"read_file", "write_file", "list_files"} <= names
    assert {"ai_chat", "summarise", "classify"} <= names


async def test_filesystem_roundtrip(fs_sandbox):
    # Reload so the module picks up the patched MCP_FS_ROOT.
    from mcp_toolkit.plugins.filesystem import handlers

    importlib.reload(handlers)

    await handlers.write_file("notes/todo.txt", "buy milk")
    assert (fs_sandbox / "notes" / "todo.txt").read_text() == "buy milk"

    assert await handlers.read_file("notes/todo.txt") == "buy milk"

    listed = await handlers.list_files("notes")
    assert "notes/todo.txt" in listed


async def test_filesystem_sandbox_escape_blocked(fs_sandbox):
    from mcp_toolkit.plugins.filesystem import handlers

    importlib.reload(handlers)
    with pytest.raises(PermissionError):
        await handlers.read_file("../../etc/passwd")


async def test_list_files_output_schema_enforced(fs_sandbox):
    from mcp_toolkit.plugins.filesystem import handlers

    importlib.reload(handlers)
    await handlers.write_file("a.txt", "x")
    # Calling through the registry validates the declared output schema.
    result = await registry.call("list_files", {"path": "."})
    assert isinstance(result, list)
    assert all(isinstance(x, str) for x in result)


async def test_sarmalink_reports_unconfigured(monkeypatch):
    monkeypatch.delenv("MCP_SARMALINK_API_KEY", raising=False)
    from mcp_toolkit.plugins.sarmalink import handlers

    importlib.reload(handlers)
    out = await handlers.ai_chat("hello")
    assert "not configured" in out.lower()


async def test_registry_rejects_unknown_argument():
    from mcp_toolkit.plugins import filesystem  # noqa: F401

    with pytest.raises(ToolValidationError):
        await registry.call("read_file", {"path": "x", "bogus": 1})
