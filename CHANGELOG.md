# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0]

### Added

- JSON-RPC 2.0 batch requests on both transports. A top-level JSON array of messages is dispatched concurrently through the shared `dispatch_batch` entry point and returns an array of responses with notification members omitted, matching the JSON-RPC specification. An empty batch is rejected as an invalid request, a batch of only notifications produces no response body, and an invalid (non-object) member yields a per-member error rather than failing the whole batch. MCP revision `2025-06-18` removed batching, so this is offered for clients negotiating `2025-03-26` or `2024-11-05` without rejecting them.

### Fixed

- The HTTP `POST /mcp` endpoint now returns a JSON-RPC parse error (`-32700`) for malformed JSON bodies instead of an unhandled `500`.
- `dispatch` now answers a non-object JSON-RPC message with an invalid-request error (`-32600`) rather than raising, which also makes batch members robust.

## [1.1.0]

### Added

- MCP 1.0 compliant protocol layer (`protocol.py`) shared by both transports: `initialize` with protocol version negotiation, `notifications/initialized`, `ping`, `tools/list`, and `tools/call` returning content blocks and `structuredContent`.
- `POST /mcp` JSON-RPC endpoint on the HTTP transport.
- Tool input schema generation from handler type hints, with per-call argument validation via `jsonschema`. Schemas now reflect real types and set `additionalProperties: false`.
- Optional `output_schema` on `@registry.tool`, validated on return and surfaced as MCP structured content.
- OpenTelemetry span per tool call, recording tool name, argument count, duration, and error type, exported over OTLP when `MCP_OTEL_ENDPOINT` is set.
- Authentication module: constant-time API key comparison (`auth/api_key.py`) and OAuth 2.1 resource server JWT validation against the issuer JWKS with issuer and audience checks (`auth/oauth.py`).
- OAuth 2.1 PKCE client flow (`oauth_client.py`) and a `mcp-toolkit login` command to obtain a bearer token against a hosted server.
- Per-client token-bucket rate limiting (`auth/ratelimit.py`), enabled with `MCP_RATE_LIMIT_RPS`.
- Configurable filesystem sandbox root via `MCP_FS_ROOT`.
- End-to-end test suite covering the protocol, both transports, auth, rate limiting, schema validation, and the bundled plugins.
- `ARCHITECTURE.md`, `ROADMAP.md`, and this `CHANGELOG.md`.

### Changed

- Logs now write to stderr so the stdio transport keeps stdout reserved for JSON-RPC, as the MCP specification requires.
- `/health` now reports `tools_registered` and `uptime_seconds`.
- `mcp-toolkit doctor` reports auth, rate limit, and OAuth configuration alongside the registered tool count.
- HTTP transport validates arguments and returns `422` on validation failure for the REST surface.
- Container image rebuilt as a reproducible uv-based multi-stage build running as a non-root user with a health check.
- CI runs on Python 3.12 and 3.13 with updated `actions/checkout` and `setup-uv`.
- Applied non-breaking dependency floor bumps: `mcp>=1.27.2`, `uvicorn>=0.46.0`, `pydantic>=2.13.4`, `pydantic-settings>=2.14.1`, `structlog>=25.5.0`, `opentelemetry-*>=1.41.1`, `httpx>=0.28.1`, `python-jose>=3.5.0`. Added `jsonschema>=4.23`.

### Fixed

- The stdio transport no longer leaks log output onto stdout, which previously corrupted the JSON-RPC stream.
- The filesystem sandbox path check now uses real path containment rather than a string prefix, closing a sibling-directory escape.

## [1.0.0]

- Initial release: decorator-based tool registry, stdio and HTTP transports, structlog logging, OpenTelemetry setup, CLI, filesystem and SarmaLink-AI plugins, container image.
