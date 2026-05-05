---
phase: 064
gathered: "2026-05-05"
autonomous: true
---

# Phase 064 — Version Handshake (Plugin/Daemon Compatibility)

<domain>
## Phase Boundary

Plugin sends `X-State-Plugin-Version` header on worker attach/requests; daemon validates against compat range and refuses on incompatible versions.

Worker-specific endpoints (POST /hook/*, GET /events/subscribe) are gated by the version check. Internal daemon API (POST /) and GET /health are exempt.
</domain>

<decisions>
## Implementation Decisions

### Version format: major.minor prefix match
Worker and daemon share COMPAT_MAJOR_MINOR = "0.1". Any version starting with that prefix (e.g. 0.1.0, 0.1.99) is compatible. A change to "0.2" would break compat.

### Version check scope: worker-specific endpoints only
Only POST /hook/* and GET /events/subscribe are gated. Internal JSON-RPC API (POST /) and GET /health are exempt to avoid breaking existing daemon API consumers (CLI, admin tools).

### Header name: x-state-plugin-version
Consistent with existing header naming convention (x-state-session-id, x-state-mode).

### Rejection: HTTP 426 Upgrade Required
Standard HTTP status for protocol version mismatch. Worker treats 426 as attach failure with clear log message.
</decisions>

<code_context>
## Existing Code Insights

- `state_core.__version__ = "0.1.0"` already exists
- Daemon server already parses HTTP headers and routes by method/path
- Worker already sends `X-State-Session-Id` header pattern
- Mode middleware already validates `X-State-Mode` header
- `_http_response()` helper exists for building responses
</code_context>

<specifics>
## Specific Ideas

- `state_core/version.py` shared module for version constants and compat check
- Daemon server checks version after reading headers, before routing
- Worker sends version on all HTTP requests to daemon (GET /health, SSE connect, POST /hook)
- Future: version negotiation for graceful upgrades
</specifics>

<deferred>
## Deferred Ideas

- Graceful upgrade negotiation (client says "I support 0.1 and 0.2", daemon picks best)
- Version negotiation as a separate startup handshake before SSE
</deferred>
