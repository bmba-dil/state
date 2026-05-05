# Phase 048: Priority Inversion + Silent Deadlock Detection — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Detect two scheduler pathology classes: (1) priority inversion — a critical-path Step blocked on a `soft` edge that could be overridden; (2) silent deadlock — all in-flight nodes blocked on descoped/missing predecessors. Emit `state.scheduler.deadlock` events for TUI consumption.

</domain>

<decisions>
## Implementation Decisions
### AI's Discretion
All implementation choices at AI's discretion.

</decisions>

<code_context>
## Existing Code Insights
- DAGScheduler.tick(), frontier(), ReactiveTrigger, Edge (blocks/soft/data), Node (with status) all available.
- Event emission via existing event infrastructure from Phase 004/009.
</code_context>

<specifics>
## Specific Ideas
Priority inversion: if critical-path Step is blocked on `soft` edge → warning. Silent deadlock: if all in-flight are blocked on descoped/missing predecessors → emit deadlock event.

</specifics>

<deferred>
## Deferred Ideas
None.
</deferred>
