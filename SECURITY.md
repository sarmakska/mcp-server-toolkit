# Security Policy

## Reporting a vulnerability

If you have found a security issue in this project, please report it privately to sarma@sarmalinux.com and do not open a public GitHub issue. Include a clear description, steps to reproduce, the commit SHA you tested against, and any proof-of-concept code or output so I can confirm it quickly.

## Response policy

I respond within 7 days. After triage I will confirm the issue, agree a fix timeline with you, patch it on `main`, and release a tagged version. Reporters are credited in the release notes unless they ask to remain anonymous.

## Supported versions

Only the latest commit on `main` receives security fixes. Pin to a tagged release if you need a stable version surface.

## Scope

This policy covers the code in this repository. Bugs in upstream dependencies should be reported to those projects directly.

## Out of scope

- Issues in third-party services (Vercel, Supabase, GitHub, Cloudflare, etc.)
- Findings that require physical access to a developer machine
- Theoretical risks without a working proof of concept
- Denial of service against demo / hosted instances
