FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install --system --no-cache-dir -r pyproject.toml || pip install fastapi uvicorn pydantic pydantic-settings typer structlog httpx mcp opentelemetry-api opentelemetry-sdk python-jose

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src ./src
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["python", "-m", "mcp_toolkit.cli", "run", "--transport", "http", "--port", "8000"]
