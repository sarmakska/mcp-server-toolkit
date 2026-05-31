# Security Policy

## Reporting a vulnerability

If you have found a security issue in this project, please report it privately to security@sarmalinux.com and do not open a public GitHub issue. Include a clear description, steps to reproduce, the commit SHA you tested against, and any proof-of-concept code or output so I can confirm it quickly.

## Response policy

I respond within 7 days. After triage I will confirm the issue, agree a fix timeline with you, patch it on `main`, and release a tagged version. Reporters are credited in the release notes unless they ask to remain anonymous.

## Supported versions

| Version | Supported |
|---|---|
| 1.1.x | Yes |
| 1.0.x | Security fixes only |
| < 1.0 | No |

Only the latest minor release receives feature and security updates. The previous minor line receives security fixes for a transition period. Pin to a tagged release if you need a stable version surface.

## Hardening notes

- Run the HTTP transport with `MCP_AUTH=api_key` or `MCP_AUTH=oauth`. The `none` mode is for stdio and trusted private networks only.
- API keys are compared in constant time. Generate them with `openssl rand -hex 32` and rotate them through your secret store.
- OAuth bearer tokens are validated as JWTs against the issuer's JWKS with issuer and audience checks, and the accepted signing algorithm set is fixed to asymmetric algorithms.
- The filesystem plugin resolves every path against a single sandbox root and rejects any path that escapes it.
- Enable `MCP_RATE_LIMIT_RPS` on public deployments to cap per-client request rates.

## Scope

This policy covers the code in this repository. Vulnerabilities in upstream dependencies should be reported to those projects directly.

## Out of scope

- Issues in third-party services and identity providers
- Findings that require physical access to a developer machine
- Theoretical risks without a working proof of concept
- Denial of service against demo or hosted instances
