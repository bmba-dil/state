# Phase 059: Auth-manager wiring into daemon - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Daemon owns the auth refresh loop; multi-cred round-robin surfaced via HTTP `GET /auth/status`. The daemon becomes the single process that manages credential lifecycle — refreshing tokens, rotating credentials, and exposing auth status over its HTTP API.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Auth refresh loop: asyncio background task that periodically checks expiry and refreshes near-expiry tokens via filelock (Phase 013).
- HTTP endpoint: `GET /auth/status` returns JSON with per-provider credential status (provider, mode, expiry_with_buffer, credential_index, never raw tokens).
- Multi-cred round-robin: daemon manages rotation state (Phase 019) and selects next credential per request.
- Daemon owns auth.json reads/writes exclusively — workers query via HTTP.
- Initialization: on daemon start, load `.state/auth.json`, verify chmod 0600 (Phase 012).
- Graceful shutdown: cancel refresh loop on daemon stop.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/auth/` — auth vault (Phase 012), filelock refresh (Phase 013), multi-cred rotation (Phase 019)
- `src/state_core/auth/base.py` — AuthMethod protocol
- Depends on: Phase 013 (filelock refresh), Phase 050 (HTTP server)

</code_context>

<specifics>
## Specific Ideas

Requirements: AUTH-07, AUTH-08 (runtime wiring)
Depends on: 013 (filelock refresh), 050 (HTTP server)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
