"""Smoke tests: prove the server entry point and registry boot cleanly."""

from mcp_toolkit import __version__
from mcp_toolkit.config import Settings
from mcp_toolkit.registry import registry


def test_version_present() -> None:
    assert __version__


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.transport == "stdio"
    assert settings.auth == "none"
    assert settings.http_port == 8000


def test_plugins_register_tools() -> None:
    # Importing the bundled plugins should populate the registry via the
    # @registry.tool decorator. This is the path serve() takes on start.
    from mcp_toolkit.plugins import filesystem, sarmalink  # noqa: F401

    assert registry.tools, "no tools registered after importing plugins"
    listed = registry.list_tools()
    names = {entry["name"] for entry in listed}
    assert "read_file" in names
    for entry in listed:
        assert entry["inputSchema"]["type"] == "object"


def test_http_app_builds_and_health() -> None:
    from mcp_toolkit.transports.http import make_app

    app = make_app(registry)
    routes = {route.path for route in app.routes}
    assert "/health" in routes
    assert "/tools" in routes
