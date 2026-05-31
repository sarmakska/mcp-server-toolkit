"""Sandboxed filesystem tools for MCP.

Every path is resolved relative to a single sandbox root and rejected if it
escapes that root. The root defaults to ``~/mcp-data`` and can be overridden
with ``MCP_FS_ROOT``, which keeps the sandbox testable and lets an operator
mount a dedicated volume.
"""
import os
from pathlib import Path

from ...registry import registry


def _root() -> Path:
    return Path(os.getenv("MCP_FS_ROOT", str(Path.home() / "mcp-data"))).resolve()


def _resolve(path: str) -> Path:
    root = _root()
    p = (root / path).resolve()
    if p != root and root not in p.parents:
        raise PermissionError(f"Path escapes sandbox: {path}")
    return p


@registry.tool("read_file", description="Read a file from the sandboxed root")
async def read_file(path: str) -> str:
    return _resolve(path).read_text()


@registry.tool("write_file", description="Write a file in the sandboxed root")
async def write_file(path: str, content: str) -> str:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} bytes to {p}"


@registry.tool(
    "list_files",
    description="List files in a sandboxed directory",
    output_schema={"type": "array", "items": {"type": "string"}},
)
async def list_files(path: str = ".") -> list[str]:
    root = _root()
    p = _resolve(path)
    return [str(f.relative_to(root)) for f in p.iterdir()]
