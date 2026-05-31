"""Sandboxed filesystem tools for MCP."""
from pathlib import Path

from ...registry import registry

ALLOWED_ROOT = Path.home() / "mcp-data"


def _resolve(path: str) -> Path:
    p = (ALLOWED_ROOT / path).resolve()
    if not str(p).startswith(str(ALLOWED_ROOT.resolve())):
        raise PermissionError(f"Path escapes sandbox: {path}")
    return p


@registry.tool("read_file", description="Read a file from the sandboxed root")
async def read_file(path: str) -> str:
    p = _resolve(path)
    return p.read_text()


@registry.tool("write_file", description="Write a file in the sandboxed root")
async def write_file(path: str, content: str) -> str:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} bytes to {p}"


@registry.tool("list_files", description="List files in a sandboxed directory")
async def list_files(path: str = ".") -> list[str]:
    p = _resolve(path)
    return [str(f.relative_to(ALLOWED_ROOT)) for f in p.iterdir()]
