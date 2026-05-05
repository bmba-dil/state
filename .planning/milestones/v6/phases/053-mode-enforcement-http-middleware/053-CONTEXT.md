# Phase 053: Mode-enforcement HTTP middleware - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Every request carries `mode` header; validator against `.state/mode.json` rejects mismatches with 403. This is the **authoritative mode-isolation point** — the canonical gate where cross-mode event writes are blocked at the daemon level before any handler runs.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Middleware runs before request dispatch; reads `X-State-Mode` header from every request.
- `.state/mode.json` contains `{"mode": "build" | "teach" | "both"}` — read on daemon start and cached.
- Reject cross-mode write requests with HTTP 403 + JSON error body `{"error": "cross_mode_rejected", ...}`.
- Read requests may be allowed across modes (query-only) — TBD based on security review.
- Write detection: POST/PUT/PATCH/DELETE to `/events/*`, `/auth/*`, `/snapshot/*`.
- Integration with Phase 004 (event store) and Phase 050 (HTTP server).

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/` — existing core package (event store, auth, mode types)
- `Mode` enum exists in `state_core.schema` from Phase 002
- Depends on: Phase 050 (HTTP server), Phase 004 (event store)
- This is the **canonical gate** for mode enforcement (defense-in-depth layer 6)

</code_context>

<specifics>
## Specific Ideas

Requirements: DAE-05, MODE-05
Depends on: 050 (HTTP server), 004 (event store)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
