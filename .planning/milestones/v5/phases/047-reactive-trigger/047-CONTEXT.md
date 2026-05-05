# Phase 047: Reactive Trigger (subscribe to v1 event stream) — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Wire the DAG scheduler to react to v1 event-store updates. On `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned` events → recompute frontier and trigger scheduling. No polling — event-driven reactivity.

</domain>

<decisions>
## Implementation Decisions
### AI's Discretion
All implementation choices at AI's discretion.

</decisions>

<code_context>
## Existing Code Insights
- Phase 009 delivered `state events tail` CLI and event-stream API.
- Phase 041-045 delivered scheduler core, frontier, dispatcher.
- `DAGScheduler` needs a `subscribe` method or event-listener interface.
</code_context>

<specifics>
## Specific Ideas
Subscribe to event stream from v1; on relevant events, recompute frontier via `tick()`. Use existing event infrastructure from Phase 009 (`SqliteEventStore`, SSE or polling-based fallback).

</specifics>

<deferred>
## Deferred Ideas
None.
</deferred>
