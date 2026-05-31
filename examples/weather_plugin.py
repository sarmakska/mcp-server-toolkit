"""Example plugin: a typed tool with a declared output schema.

Copy this into src/mcp_toolkit/plugins/weather/handlers.py and import the
package in server.py to register it. The response is fixed so the example runs
with no external dependencies; swap in a real HTTP call when you adapt it.
"""
from mcp_toolkit.registry import registry

WEATHER_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": "string"},
        "temperature_c": {"type": "number"},
        "conditions": {"type": "string"},
    },
    "required": ["city", "temperature_c", "conditions"],
}


@registry.tool(
    "get_weather",
    description="Current weather for a city",
    output_schema=WEATHER_OUTPUT_SCHEMA,
)
async def get_weather(city: str) -> dict:
    # Replace with a real async HTTP call. The output schema is validated on
    # return, so a malformed response is caught before it reaches the client.
    return {"city": city, "temperature_c": 14.0, "conditions": "partly cloudy"}
