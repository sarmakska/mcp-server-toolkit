# mcp-server-toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-1.4-blueviolet)](https://modelcontextprotocol.io)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-traced-purple)](https://opentelemetry.io)
[![Docker](https://img.shields.io/badge/Docker-distroless-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Open Source](https://img.shields.io/badge/Open_Source-%E2%9D%A4-red)](https://github.com/sarmakska/mcp-server-toolkit)

**Production-ready Model Context Protocol server starter with auth, tracing, and a plugin system.**

Built by [Sarma Linux](https://sarmalinux.com).

---

## What this is

MCP went from niche spec to default integration layer in late 2025. Every serious agent now speaks it. Most reference servers are toys: a single tool, no auth, no observability. This toolkit is the opinionated batteries-included alternative.

Scaffold an MCP server in one command. Drop tool handlers into a plugins directory. Get OAuth 2.1 with PKCE, structured logging, OpenTelemetry traces, rate limiting, and a typed tool registry for free. Runs over stdio for local agents and streamable HTTP for remote ones, same code path.

## Architecture

```mermaid
graph TD
  Client[MCP Client<br/>Desktop / Cursor / IDE]
  Client -->|stdio JSON-RPC| Stdio[stdio transport]
  Client -->|streamable HTTP| HTTP[FastAPI HTTP transport]
  Stdio --> Reg[Tool Registry]
  HTTP --> Auth[OAuth 2.1 / API key]
  Auth --> Reg
  Reg --> P1[plugin: filesystem]
  Reg --> P2[plugin: postgres]
  Reg --> P3[plugin: github]
  Reg --> P4[plugin: sarmalink]
  P4 -->|api.sarmalink.ai| SLAI[SarmaLink-AI]

  classDef ext fill:#a78bfa,stroke:#a78bfa,color:#fff
  class SLAI ext
```

## Quick start

```bash
git clone https://github.com/sarmakska/mcp-server-toolkit.git
cd mcp-server-toolkit
uv sync
cp .env.example .env
uv run mcp-toolkit run --transport stdio
```

## Plugin authoring

```python
from mcp_toolkit.registry import registry

@registry.tool("search_docs", description="Search internal docs")
async def search_docs(query: str) -> dict:
    return {"results": [...]}
```

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` or `http` | `stdio` |
| `MCP_AUTH` | `none`, `api_key`, `oauth` | `none` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel collector URL | unset |
| `SARMALINK_API_KEY` | for the sarmalink plugin | unset |

## Deployment

Distroless Docker image, ~120MB. Runs on Fly.io, Render, Railway, k8s.

```bash
docker build -t mcp-toolkit .
docker run -p 8000:8000 --env-file .env mcp-toolkit
```

## Roadmap

See [docs/OPEN-ISSUES.md](docs/OPEN-ISSUES.md). PRs welcome.

## License

MIT.

Built by [Sarma Linux](https://sarmalinux.com).
