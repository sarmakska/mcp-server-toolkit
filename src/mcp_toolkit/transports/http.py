"""Streamable HTTP transport via FastAPI."""
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from ..registry import Registry


def make_app(registry: Registry) -> FastAPI:
    app = FastAPI(title="MCP Server")

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/tools")
    async def list_tools():
        return {"tools": registry.list_tools()}

    @app.post("/tools/{name}")
    async def call_tool(name: str, request: Request):
        body = await request.json()
        try:
            result = await registry.call(name, body or {})
            return {"result": result}
        except KeyError:
            raise HTTPException(404, f"Tool {name} not found")

    return app


async def run_http(registry: Registry, settings) -> None:
    app = make_app(registry)
    config = uvicorn.Config(app, host=settings.http_host, port=settings.http_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
