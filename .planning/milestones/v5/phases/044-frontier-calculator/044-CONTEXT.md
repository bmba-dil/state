# Phase 044: Frontier Calculator (unblocked set per tick) — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Implement the frontier calculator: given a DAG and node statuses, compute the set of nodes that are unblocked (all `blocks`/`data` predecessors are `done`). Returns the frontier — nodes ready for concurrent dispatch. `soft` edges are advisory and do not block.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped.

</decisions>

<code_context>
## Existing Code Insights

- `src/state_core/scheduler.py` — has Edge (with `kind` field for blocks/soft/data), Node (with `status` field), NodeRegistry, `topo_sort()`. Add `frontier()` alongside these.
- Pure Python, no networkx.
- Tests in `tests/test_scheduler.py` — append `TestFrontier` class.

</code_context>

<specifics>
## Specific Ideas

No specific requirements. `frontier(nodes, edges) -> list[Node]`: returns all nodes whose `blocks` and `data` predecessors have status `done`. `soft` edges do NOT block. Nodes with status `done`/`failed` are excluded from frontier.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
