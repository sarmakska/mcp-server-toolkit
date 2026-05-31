"""Server entry point. Picks transport, wires registry, starts."""
import asyncio

from .config import Settings
from .registry import registry
from .telemetry import setup_telemetry
from .transports.http import run_http
from .transports.stdio import run_stdio


async def serve(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    setup_telemetry(settings)

    # Auto-import plugins so they register with @registry.tool
    from .plugins import filesystem, sarmalink  # noqa: F401

    if settings.transport == "stdio":
        await run_stdio(registry, settings)
    elif settings.transport == "http":
        await run_http(registry, settings)
    else:
        raise ValueError(f"Unknown transport: {settings.transport}")


def main() -> None:
    asyncio.run(serve())
