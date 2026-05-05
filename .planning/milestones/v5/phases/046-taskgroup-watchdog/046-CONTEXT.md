# Phase 046: TaskGroup Watchdog (P0-16 defence) — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Detect swallowed `CancelledError` in nested TaskGroups and fail loud. Python's `asyncio.TaskGroup` silently swallows `CancelledError` — a known deadlock vector (P0-16). Build a watchdog that inspects `ExceptionGroup` output from `TaskGroup.__aexit__` and catches any `CancelledError` that should have been raised, preventing silent scheduler deadlocks.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

</decisions>

<code_context>
## Existing Code Insights
- `DAGScheduler.tick()` from Phase 045 uses `asyncio.TaskGroup` for dispatch.
- Watchdog wraps the Tick in monitoring that inspects exception groups.
</code_context>

<specifics>
## Specific Ideas
Nested TaskGroup regression harness; watchdog detects `CancelledError` swallow via exception group inspection; fails loud.

</specifics>

<deferred>
## Deferred Ideas
None.
</deferred>
