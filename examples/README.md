# Examples

Runnable examples that exercise the toolkit against real code.

## `weather_plugin.py`

A self-contained plugin showing a typed tool with an output schema. Copy it into
`src/mcp_toolkit/plugins/weather/handlers.py`, add an `__init__.py` that imports
`handlers`, and import the package in `server.py` so it registers on start. The
example uses a fixed response so it runs with no external dependencies.

## `mcp_client.py`

A minimal stdio client that launches the server as a subprocess, performs the
`initialize` handshake, lists tools, and calls one. Run it from the repository
root:

```bash
uv run python examples/mcp_client.py
```

It prints the negotiated protocol version, the advertised tools, and the result
of calling `list_files`. This is the same message sequence a desktop client or
IDE uses.
