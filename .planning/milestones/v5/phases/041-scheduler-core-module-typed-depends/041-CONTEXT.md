# Phase 041: Scheduler Core Module — typed `depends_on` edges - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Define the foundational scheduler types: edge kinds `blocks`/`soft`/`data`, a pydantic `Edge` model, and a node registry. This phase delivers the core data model that phases 042-049 build on — no scheduling logic yet, just the typed graph representation.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

### Key integration points
- `src/state_core/` — existing package where `scheduler` module will live
- `src/state_core/schema/` — pydantic event schemas (v1), conventions for typed models with `extra = "forbid"`
- Phase 001 scaffolded the `state_core` package — use existing `pyproject.toml` and module structure

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
