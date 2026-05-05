# Phase 042: Topological Sort (Kahn's algorithm) — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Implement Kahn's algorithm for topological sort with stable ordering, keyed by `(slice_id, step_id)`. Consumes the Edge/Node/NodeRegistry data model from Phase 041. Produces a deterministic, stable topological ordering of the DAG that downstream phases (frontier calculator, dispatcher, CLI renderer) consume.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

- `src/state_core/scheduler.py` — Phase 041 delivered `Edge`, `Node`, `NodeRegistry`, `EdgeKind` types. The `DAGScheduler` skeleton with `tick()` is preserved.
- Follows pydantic conventions: `extra="forbid"`, `frozen=True` on data models.
- Tests use class-based organization with pytest.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Use pure Python (no networkx), stable ordering by `(slice_id, step_id)` sort key, Kahn's algorithm with in-degree tracking.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
