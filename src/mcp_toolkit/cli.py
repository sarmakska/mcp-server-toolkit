"""mcp-toolkit CLI: init, run, doctor."""
import typer
import asyncio
from .server import serve
from .config import Settings

app = typer.Typer(help="mcp-server-toolkit CLI")


@app.command()
def run(
    transport: str = typer.Option("stdio", help="stdio or http"),
    port: int = typer.Option(8000, help="HTTP port (when transport=http)"),
):
    """Start the MCP server."""
    settings = Settings(transport=transport, http_port=port)
    asyncio.run(serve(settings))


@app.command()
def doctor():
    """Check environment and report issues."""
    from .registry import registry

    settings = Settings()
    typer.echo(f"Transport: {settings.transport}")
    typer.echo(f"Auth: {settings.auth}")
    typer.echo(f"OTel endpoint: {settings.otel_endpoint or '(not set)'}")
    typer.echo(f"SarmaLink: {'configured' if settings.sarmalink_api_key else 'NOT configured'}")
    typer.echo(f"Tools registered: {len(registry.tools)}")


@app.command()
def init(
    name: str = typer.Argument(..., help="Plugin name"),
):
    """Scaffold a new plugin."""
    typer.echo(f"To create a plugin, drop a file in src/mcp_toolkit/plugins/{name}/handlers.py")
    typer.echo("Use the @registry.tool decorator to register handlers.")


if __name__ == "__main__":
    app()
