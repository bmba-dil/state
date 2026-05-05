# Phase 101: Daemon HTTP mode middleware (canonical gate) - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Already partially in Phase 053; extend with event-type-level validation (reject state.concept.* when mode=build).

**Goal:** Extend the daemon's ModeMiddleware to inspect the event type in JSON-RPC request bodies and reject teach-mode events (state.concept.*, state.drill.*) when the active mode is "build", and reject build-mode events when the active mode is "teach". This is layer 5 of 6 — the canonical gate.
</domain>

<decisions>
## Implementation Decisions
All implementation choices at AI's discretion.

Key considerations:
- ModeMiddleware already exists with X-State-Mode header validation (Phase 053)
- Teach-only event types: state.concept.*, state.drill.*
- Build-only event types: state.arc.*, state.phase.*, state.slice.*, state.step.*
- Both-mode allows all events; kernel-mode is internal-only
- Event type extracted from JSON-RPC body `{"method": "state.emit", "params": {"type": "state.concept.introduced"}}`
</decisions>

<code_context>
- src/state_daemon/middleware.py — ModeMiddleware class (lines 178-247)
- src/state_core/schema.py — Event type definitions and aggregates
</code_context>

<specifics>
Implement per ROADMAP phase goal and MODE-05 requirement.
</specifics>

<deferred>
None.
</deferred>
