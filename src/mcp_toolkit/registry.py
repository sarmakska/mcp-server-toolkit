"""
Typed tool / resource / prompt registry.

Decorator-driven. Plugins import this and register handlers with @registry.tool.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field


@dataclass
class ToolHandler:
    name: str
    description: str
    handler: Callable[..., Awaitable[Any]]
    schema: dict[str, Any]


@dataclass
class Registry:
    tools: dict[str, ToolHandler] = field(default_factory=dict)

    def tool(self, name: str, description: str = ""):
        def decorator(fn: Callable[..., Awaitable[Any]]):
            sig = inspect.signature(fn)
            schema = {
                "type": "object",
                "properties": {
                    p.name: {"type": "string"}
                    for p in sig.parameters.values()
                    if p.name != "self"
                },
                "required": [
                    p.name
                    for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty and p.name != "self"
                ],
            }
            self.tools[name] = ToolHandler(
                name=name, description=description, handler=fn, schema=schema
            )
            return fn

        return decorator

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.schema}
            for t in self.tools.values()
        ]

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self.tools:
            raise KeyError(f"Tool not registered: {name}")
        return await self.tools[name].handler(**arguments)


registry = Registry()
