"""Registry schema generation, validation and tracing."""
import pytest

from mcp_toolkit.registry import Registry, ToolValidationError, build_input_schema


def test_schema_from_type_hints():
    reg = Registry()

    @reg.tool("typed")
    async def typed(name: str, count: int, ratio: float, flag: bool = False) -> dict:
        return {}

    schema = reg.tools["typed"].input_schema
    assert schema["properties"]["name"] == {"type": "string"}
    assert schema["properties"]["count"] == {"type": "integer"}
    assert schema["properties"]["ratio"] == {"type": "number"}
    assert schema["properties"]["flag"] == {"type": "boolean"}
    # flag has a default, so it is optional.
    assert set(schema["required"]) == {"name", "count", "ratio"}
    assert schema["additionalProperties"] is False


def test_optional_and_list_types():
    def fn(items: list[str], note: str | None = None):
        ...

    schema = build_input_schema(fn)
    assert schema["properties"]["items"] == {"type": "array", "items": {"type": "string"}}
    assert schema["properties"]["note"] == {"type": "string"}


def test_sync_handler_rejected():
    reg = Registry()
    with pytest.raises(TypeError):

        @reg.tool("bad")
        def bad(x: str) -> str:  # not async
            return x


async def test_argument_validation_rejects_wrong_type(registry_with_tools):
    with pytest.raises(ToolValidationError):
        await registry_with_tools.call("add", {"a": "not-an-int", "b": 2})


async def test_argument_validation_rejects_unknown_field(registry_with_tools):
    with pytest.raises(ToolValidationError):
        await registry_with_tools.call("echo", {"message": "hi", "extra": 1})


async def test_missing_required_argument(registry_with_tools):
    with pytest.raises(ToolValidationError):
        await registry_with_tools.call("add", {"a": 1})


async def test_output_schema_validation_passes(registry_with_tools):
    result = await registry_with_tools.call("add", {"a": 2, "b": 3})
    assert result == {"sum": 5}


async def test_output_schema_validation_fails():
    reg = Registry()

    @reg.tool("bad_output", output_schema={"type": "object", "required": ["x"]})
    async def bad_output() -> dict:
        return {"y": 1}

    with pytest.raises(ToolValidationError):
        await reg.call("bad_output", {})


async def test_unknown_tool_raises_keyerror(registry_with_tools):
    with pytest.raises(KeyError):
        await registry_with_tools.call("nope", {})
