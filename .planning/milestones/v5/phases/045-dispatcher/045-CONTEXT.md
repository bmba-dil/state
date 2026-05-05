# Phase 045: Dispatcher — TaskGroup per Slice, Concurrency Cap — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Implement the async dispatcher that groups frontier nodes by Slice, wraps each Slice group in an `asyncio.TaskGroup`, and dispatches concurrent Slice execution up to a configurable concurrency cap. Steps within a Slice execute sequentially. This is the runtime heart of the DAG scheduler.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped.

</decisions>

<code_context>
## Existing Code Insights

- `src/state_core/scheduler.py` — has Edge, Node, NodeRegistry, topo_sort, detect_cycles, frontier, DAGScheduler skeleton.
- `DAGScheduler.tick()` is the method to implement — currently a skeleton with `...` and `-> list[str]`.
- Configuration cap read from `config.toml` via existing config infrastructure.
- Async patterns used: `asyncio.gather`, `asyncio.TaskGroup`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements. `DAGScheduler.tick(arc_id)` should: compute frontier, group by Slice, dispatch up to cap concurrent slices. Within a Slice, steps run sequentially. Configurable concurrency cap.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
