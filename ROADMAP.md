# Roadmap

## Shipped (1.1.0)

- [x] MCP 1.0 compliant protocol: `initialize` with version negotiation, `notifications/initialized`, `ping`, `tools/list`, `tools/call`
- [x] stdio and streamable HTTP transports sharing one protocol layer
- [x] Decorator-based tool registry with JSON Schema generated from type hints
- [x] Input argument validation and optional output schema validation
- [x] Structured tool results (`structuredContent`) for dict-returning tools
- [x] API key auth (constant-time) and OAuth 2.1 resource server (JWKS validation)
- [x] OAuth 2.1 PKCE client flow via `mcp-toolkit login`
- [x] Per-client token-bucket rate limiting
- [x] OpenTelemetry span export per tool call, structured logging to stderr
- [x] CLI: `run`, `doctor`, `init`, `login`
- [x] Sandboxed filesystem plugin and SarmaLink-AI plugin
- [x] Reproducible uv-based container image, non-root, with a health check
- [x] End-to-end test suite across protocol, transports, auth, and plugins

## Planned

- [ ] Resource and prompt registries (currently tools only)
- [ ] Server-Sent Events streaming for long-running tool calls over HTTP
- [ ] Dynamic Client Registration (RFC 7591) for the OAuth flow
- [ ] Plugin: Postgres query tool with a read-only DSN
- [ ] Plugin: GitHub (issues, PRs, code search)
- [ ] Distributed rate limiter backed by Redis for multi-replica deployments
- [ ] Per-user audit log

## Not planned

- Visual GUI builder (this is code-first)
- Bundled inference (use a separate model service)
- Plugin marketplace (use git for distribution)
- Framework swaps (FastAPI stays)
- Sync-only handlers (everything is async)

## How to contribute

PRs welcome. Pick something from "Planned", open an issue saying you are taking it, fork, branch, push, and open a PR. Releases are published under [GitHub Releases](https://github.com/sarmakska/mcp-server-toolkit/releases).
