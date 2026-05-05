# Phase 104: Mode activation event (state.mode.activated) - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Emit event on mode change; SSE fan-out triggers MCP reload.

**Goal:** When mode changes (via `state mode set`), the daemon emits a `state.mode.activated` event. SSE subscribers (plugin, workers) receive the event and reload their MCP registrations. This completes the hot-reload chain started in Phase 099.
</domain>

<decisions>
All at AI's discretion.
</decisions>

<code_context>
- Phase 099: Config hook reads mode.json, event hook scaffold exists
- Phase 100: Plugin hook mode gate
- Phase 097: ModeConfig in schema.py + state mode init/set CLI
- src/state_core/schema.py — Event type definitions
</code_context>

<specifics>
Implement per ROADMAP phase goal and MODE-03, MODE-05 requirements.
</specifics>

<deferred>
None.
</deferred>
