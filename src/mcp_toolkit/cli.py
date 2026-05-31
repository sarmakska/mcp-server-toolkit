"""mcp-toolkit CLI: run, doctor, init, login."""
from __future__ import annotations

import asyncio

import typer

from .config import Settings
from .server import serve

app = typer.Typer(help="mcp-server-toolkit CLI", no_args_is_help=True)


@app.command()
def run(
    transport: str = typer.Option("stdio", help="stdio or http"),
    port: int = typer.Option(8000, help="HTTP port (when transport=http)"),
    host: str = typer.Option("0.0.0.0", help="HTTP host (when transport=http)"),
) -> None:
    """Start the MCP server."""
    settings = Settings(transport=transport, http_port=port, http_host=host)
    asyncio.run(serve(settings))


@app.command()
def doctor() -> None:
    """Check the environment and report configuration."""
    from .registry import registry

    settings = Settings()
    # Trigger plugin registration so the tool count is accurate.
    from .plugins import filesystem, sarmalink  # noqa: F401

    typer.echo(f"Transport:       {settings.transport}")
    typer.echo(f"Auth:            {settings.auth}")
    if settings.auth == "oauth":
        typer.echo(f"OAuth issuer:    {settings.oauth_issuer or '(not set)'}")
        typer.echo(f"OAuth audience:  {settings.oauth_audience or '(not set)'}")
    if settings.rate_limit_rps > 0:
        typer.echo(f"Rate limit:      {settings.rate_limit_rps} rps")
    typer.echo(f"OTel endpoint:   {settings.otel_endpoint or '(not set)'}")
    typer.echo(
        f"SarmaLink:       {'configured' if settings.sarmalink_api_key else 'NOT configured'}"
    )
    typer.echo(f"Tools registered: {len(registry.tools)}")


@app.command()
def init(name: str = typer.Argument(..., help="Plugin name")) -> None:
    """Scaffold a new plugin under src/mcp_toolkit/plugins/."""
    typer.echo(f"Create src/mcp_toolkit/plugins/{name}/handlers.py and register handlers:")
    typer.echo("")
    typer.echo("    from ...registry import registry")
    typer.echo("")
    typer.echo(f'    @registry.tool("{name}_hello", description="Say hello")')
    typer.echo("    async def hello(who: str) -> str:")
    typer.echo('        return f"hello {who}"')
    typer.echo("")
    typer.echo(f"Add src/mcp_toolkit/plugins/{name}/__init__.py with: from . import handlers")
    typer.echo("Then import it in server.py so it auto-registers on start.")


@app.command()
def login(
    issuer: str = typer.Option(..., help="OAuth 2.1 issuer URL"),
    client_id: str = typer.Option(..., help="OAuth client id (public client)"),
) -> None:
    """Run the OAuth 2.1 PKCE flow and print a bearer token for a hosted server."""
    import http.server
    import secrets
    import threading
    import urllib.parse
    import webbrowser

    from .oauth_client import AuthorizationServer, OAuthClient, generate_pkce_pair

    settings = Settings()
    verifier, challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)
    captured: dict[str, str] = {}

    parsed = urllib.parse.urlparse(settings.oauth_redirect_uri)
    host, port = parsed.hostname or "127.0.0.1", parsed.port or 8765

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            captured.update({k: v[0] for k, v in params.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Authorisation complete. You may close this tab.")

        def log_message(self, *args: object) -> None:  # silence the server
            return

    httpd = http.server.HTTPServer((host, port), Handler)

    async def _flow() -> None:
        server = await AuthorizationServer.discover(issuer)
        client = OAuthClient(
            client_id=client_id,
            redirect_uri=settings.oauth_redirect_uri,
            server=server,
            scope=settings.oauth_scope,
        )
        url = client.build_authorization_url(challenge, state)
        typer.echo("Opening browser for authorisation. If it does not open, visit:")
        typer.echo(url)
        webbrowser.open(url)

        thread = threading.Thread(target=httpd.handle_request, daemon=True)
        thread.start()
        thread.join(timeout=300)
        httpd.server_close()

        if captured.get("state") != state:
            raise typer.Exit(code=1)
        code = captured.get("code")
        if not code:
            typer.echo("No authorisation code received.")
            raise typer.Exit(code=1)
        token = await client.exchange_code(code, verifier)
        typer.echo("")
        typer.echo("Access token:")
        typer.echo(token.get("access_token", "(none returned)"))

    asyncio.run(_flow())


if __name__ == "__main__":
    app()
