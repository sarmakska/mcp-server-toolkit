"""OpenTelemetry and structlog setup.

When ``MCP_OTEL_ENDPOINT`` is set, a tracer provider with an OTLP exporter is
installed and every tool call is exported as a span (see
``registry.Registry.call``). When it is unset, the server still emits structured
JSON logs through structlog but exports no spans.
"""
import sys

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import Settings

_configured = False


def setup_telemetry(settings: Settings) -> None:
    global _configured
    if _configured:
        return

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )

    if settings.otel_endpoint:
        resource = Resource.create({SERVICE_NAME: settings.service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint))
        )
        trace.set_tracer_provider(provider)

    _configured = True


def get_tracer():
    return trace.get_tracer("mcp-toolkit")
