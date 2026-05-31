"""mcp-server-toolkit, a production-ready MCP server starter."""
import sys

import structlog

__version__ = "1.1.0"

# Logs always go to stderr so the stdio transport can keep stdout reserved for
# JSON-RPC messages, as the MCP specification requires. setup_telemetry refines
# the processor chain; this baseline keeps logging safe before it runs.
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
