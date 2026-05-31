"""
Typed tool registry with JSON Schema generation, validation and tracing.

Decorator-driven. Plugins import this and register handlers with
``@registry.tool``. The decorator derives an input JSON Schema from the
handler's type hints, validates arguments against it on every call, optionally
validates the return value against an output schema, and wraps each call in an
OpenTelemetry span.
"""
from __future__ import annotations

import inspect
import time
import typing
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, get_args, get_origin

import jsonschema
import structlog
from opentelemetry import trace

log = structlog.get_logger("mcp-toolkit.registry")

# Mapping from Python primitive types to JSON Schema type names.
_PY_TO_JSON: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


class ToolValidationError(ValueError):
    """Raised when tool arguments or output fail schema validation."""


def _schema_for_annotation(annotation: Any) -> dict[str, Any]:
    """Translate a single type annotation into a JSON Schema fragment.

    Falls back to an empty (any) schema for types we cannot map cleanly, which
    keeps the registry usable for handlers that have not been fully annotated.
    """
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}

    origin = get_origin(annotation)
    if origin is not None:
        # Optional[X] / X | None
        if origin is typing.Union:
            args = [a for a in get_args(annotation) if a is not type(None)]
            if len(args) == 1:
                return _schema_for_annotation(args[0])
            return {"anyOf": [_schema_for_annotation(a) for a in args]}
        if origin in (list, set, tuple):
            args = get_args(annotation)
            item = _schema_for_annotation(args[0]) if args else {}
            return {"type": "array", "items": item}
        if origin is dict:
            return {"type": "object"}

    json_type = _PY_TO_JSON.get(annotation)
    if json_type:
        return {"type": json_type}
    return {}


def build_input_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Build a JSON Schema object describing the handler's parameters."""
    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn)
    except Exception:  # pragma: no cover - defensive against exotic annotations
        hints = {}

    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        annotation = hints.get(name, param.annotation)
        properties[name] = _schema_for_annotation(annotation)
        if param.default is inspect.Parameter.empty:
            required.append(name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


@dataclass
class ToolHandler:
    name: str
    description: str
    handler: Callable[..., Awaitable[Any]]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None


@dataclass
class Registry:
    tools: dict[str, ToolHandler] = field(default_factory=dict)

    def tool(
        self,
        name: str,
        description: str = "",
        output_schema: dict[str, Any] | None = None,
    ) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
        """Register an async handler as an MCP tool.

        The input schema is derived from the handler's type hints. Pass
        ``output_schema`` to have the return value validated as well, which maps
        onto the MCP ``outputSchema`` field for structured tool results.
        """

        def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            if not inspect.iscoroutinefunction(fn):
                raise TypeError(f"Tool handler {name!r} must be an async function")
            self.tools[name] = ToolHandler(
                name=name,
                description=description or (fn.__doc__ or "").strip(),
                handler=fn,
                input_schema=build_input_schema(fn),
                output_schema=output_schema,
            )
            return fn

        return decorator

    def list_tools(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for t in self.tools.values():
            entry: dict[str, Any] = {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            if t.output_schema is not None:
                entry["outputSchema"] = t.output_schema
            out.append(entry)
        return out

    def validate_arguments(self, name: str, arguments: dict[str, Any]) -> None:
        tool = self.tools.get(name)
        if tool is None:
            raise KeyError(f"Tool not registered: {name}")
        try:
            jsonschema.validate(arguments, tool.input_schema)
        except jsonschema.ValidationError as err:
            raise ToolValidationError(
                f"Invalid arguments for tool {name!r}: {err.message}"
            ) from err

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self.tools.get(name)
        if tool is None:
            raise KeyError(f"Tool not registered: {name}")

        self.validate_arguments(name, arguments)

        tracer = trace.get_tracer("mcp-toolkit")
        started = time.perf_counter()
        with tracer.start_as_current_span(f"tool.{name}") as span:
            span.set_attribute("mcp.tool.name", name)
            span.set_attribute("mcp.tool.argument_count", len(arguments))
            try:
                result = await tool.handler(**arguments)
            except Exception as err:
                span.set_attribute("mcp.tool.error", type(err).__name__)
                span.record_exception(err)
                log.error("tool_call_failed", tool=name, error=str(err))
                raise

            duration_ms = (time.perf_counter() - started) * 1000
            span.set_attribute("mcp.tool.duration_ms", round(duration_ms, 3))

            if tool.output_schema is not None:
                try:
                    jsonschema.validate(result, tool.output_schema)
                except jsonschema.ValidationError as err:
                    span.set_attribute("mcp.tool.error", "OutputValidationError")
                    raise ToolValidationError(
                        f"Tool {name!r} returned a value that fails its output schema: "
                        f"{err.message}"
                    ) from err

            log.info("tool_call", tool=name, duration_ms=round(duration_ms, 3))
            return result


registry = Registry()
