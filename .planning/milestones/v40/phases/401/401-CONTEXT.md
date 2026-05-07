# Phase 401: Artifact Catalog, Naming, Layout, Cross-Refs - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce a complete blueprint for the `.state/build/` filesystem — every artifact type, template, on-disk path, naming convention, projection-vs-authored classification, cross-reference format, and 15 consistency validation codes (W001–W015). Builds on Phase 400 tier definitions and state machines. Output is architecture specification documents, not code.

</domain>

<decisions>
## Implementation Decisions

### Artifact catalog — new files & structure

- **D-401-01:** ARC.md and STAGE.md are agent-authored tier-definition files (created by `state-new arc`/`state-new stage`). Projector updates status field only. NOT projector-rebuilt projections.
- **D-401-02:** DECISIONS.md added at each tier for gray-area decision logging. Agent-authored, append-only.
- **D-401-03:** CRIT.md = numbered falsifiable requirements (CRIT-01, CRIT-02, ...). Must-have truths. Format: each criterion is a testable assertion with acceptance evidence trail.
- **D-401-04:** MAP.md = generated plan + tracker. Created by planner during `state-new` flow. Contains child IDs (stages for arc, slices for stage), what each child must accomplish (derived from CRIT), and tracking checkboxes updated by projector automatically as children advance.
- **D-401-05:** MAP.md is unique per tier and CRIT set. Arc MAP.md lists stages with IDs + goals. Stage MAP.md lists slices with IDs + goals.
- **D-401-06:** Slice workflow docs remain separate files: DESIGN.md, RESEARCH.md, stepNPLAN.md (one per step), VERIFICATION.md, SUMMARY.md. Each is the output of its workflow step and input for the next.

### STATE.md consolidation & file count

- **D-401-07:** STATE.md projections are consolidated JSON under `.state/build/state/` (canonical). CLI `state export-state` generates per-directory STATE.md on demand. Keeps source-controlled markdown clean.
- **D-401-08:** Step files remain separate (7+ files per 3-step Slice acceptable). Each file has a clear purpose and workflow role. No consolidation.

### Projection vs authored boundary

- **D-401-09:** Agent-authored artifacts: ARC.md, STAGE.md, CRIT.md, MAP.md, DESIGN.md, RESEARCH.md, stepNPLAN.md, VERIFICATION.md, SUMMARY.md, DECISIONS.md.
- **D-401-10:** Projector-rebuilt artifacts: index.json, consolidated STATE.md JSON projections under `.state/build/state/`.
- **D-401-11:** MAP.md checkboxes updated by projector automatically as child tiers advance (state.stage.*, state.slice.* events trigger checkbox updates).
- **D-401-12:** Immutability: stepNPLAN.md and CRIT.md lock when Slice enters `in_progress`. DESIGN.md and RESEARCH.md remain mutable.
- **D-401-13:** Immutability enforced by snapshot-before-mutation protocol at daemon level. Attempted mutation of a locked artifact is rejected (not warned — blocked).

### Cross-reference & consistency codes

- **D-401-14:** index.json structure: tier-separated — `{arcs: {}, stages: {}, slices: {}, steps: {}}`. Each entry maps ID to type, path, status, last_updated. O(1) ID→path resolution.
- **D-401-15:** Broken reference handling: surface + block. Referrer flagged with W-code. If referrer is `in_progress`, execution blocks until user resolves (reassign target, defer dependency, or remove reference). No auto-cascade.
- **D-401-16:** W001–W015 consistency codes use tiered severity: ERROR (must fix, blocks ship/verify), WARNING (should fix, advisory at plan time), INFO (informational, no action required).
- **D-401-17:** `validate_consistency()` is a blocking gate on daemon startup. ERROR-severity codes prevent daemon start. Daemon MUST auto-launch a resolution workflow (session or subagent) that receives the error context and fixes consistency. Not a deadlock — auto-resolution path exists.

### Claude's Discretion

- Exact frontmatter field list per artifact (user gave structural decisions; planner fills in specific fields)
- The specific 15 W-codes (W001–W015) and their exact severity assignments
- Template exact markdown format (planner creates from artifact decisions)
- index.json exact JSON schema (planner designs from tier-separated decision)
- validate_consistency() function signature and implementation details

</decisions>

<specifics>
## Specific Ideas

- MAP.md is modeled after our own `.planning/ROADMAP.md` — a plan + tracker with IDs, goals, and checkboxes
- MAP.md at Arc level: lists all stages with what each should accomplish, has tracking checkboxes
- MAP.md at Stage level: lists all slices with what each should accomplish, has tracking checkboxes
- CRIT.md holds must-have truths that MAP.md is generated from — planner reads CRIT, creates MAP children
- "I want to avoid filesystem bloat but each file must have a clear purpose — separate is better than consolidated when the purpose is different"

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 401 scope & requirements
- `.planning/milestones/v40/ROADMAP.md` — Phase 401 goal (line 44), success criteria (SC1–SC5)
- `.planning/milestones/v40/REQUIREMENTS.md` — ART-01..05 (artifact catalog), DSK-01..06 (on-disk layout), REF-01..06 (cross-referencing). 17 requirements total.
- `.planning/milestones/v40/HANDOFF.md` — Key questions (now resolved), artifact table, directory tree proposal, mental model, GSD reference patterns

### Phase 400 deliverables (prerequisite — MUST read before planning)
- `.planning/milestones/v40/phases/400/specs/TIER-ARC.md` — Arc tier definition, state machine, owned artifacts
- `.planning/milestones/v40/phases/400/specs/TIER-STAGE.md` — Stage tier definition, state machine, owned artifacts
- `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — Slice tier definition, state machine, owned artifacts
- `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — Step tier definition, state machine, owned artifacts
- `.planning/milestones/v40/phases/400/specs/FSM-TABLES.md` — All state transitions with guard conditions and event triggers
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — Complete event taxonomy for all four tiers
- `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — Step→Slice→Stage→Arc composite event cascade
- `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — Pydantic frontmatter models for all tier artifacts
- `.planning/milestones/v40/phases/400/specs/DESC-SEMANTICS.md` — Descope, abandon, blocked, and decimal insertion semantics
- `.planning/milestones/v40/phases/400/400-CONTEXT.md` — Phase 400 decisions carried forward (D-01 through D-19)

### Project-level constraints
- `.planning/PROJECT.md` — Key decisions table, four-tier hierarchy commitment, STATE.md is projector output
- `.planning/ROADMAP.md` §v40 — Milestone 400/401 phase definitions

### Architecture & integration
- `.planning/research/ARCHITECTURE.md` — CQRS aggregate design, event taxonomy, directory layout
- `src/state_core/projector.py` — Existing CQRS projection engine (19 handlers, 3 cache tables)
- `src/state_core/schema.py` — 34+ existing event types

### GSD reference patterns
- `state-inputs/get-shit-done/bin/lib/artifacts.cjs` — Canonical artifact registry pattern (10 exact-match + 2 pattern-match)
- `state-inputs/get-shit-done/bin/lib/verify.cjs` — Health check pattern (19 warning codes, schema drift detection)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reference only (design-phase, no code to write)
This phase produces architecture specification documents. Shipped code below is reference for understanding existing integration points:

### Reusable Assets
- `state_core.projector` — CQRS handler registration pattern. New handlers for Arc/Stage/Step STATE.md projections follow same pattern.
- `state_core.scheduler` — DAG model, edge types (blocks/soft/data). Cross-reference edge types must match scheduler's expectations.
- `state_core.mode` — `.state/mode.json` validation. `.state/build/` must respect mode isolation (v11).

### Established Patterns
- `extra="forbid"` on all pydantic models
- Event-sourced: SQLite authoritative, SyncEvent mirror
- Daemon HTTP middleware as canonical gate (v6)
- Projector rebuilds from events, never agent-written

### Integration Points
- index.json projector handler must run on every state change
- MAP.md checkbox updates triggered by state.stage.* / state.slice.* events
- validate_consistency() runs on daemon startup (before HTTP server binds)
- Snapshot-before-mutation protocol integrates with v4 Snapshot service
- Artifact schemas extend `state_core.schema` pydantic models
</code_context>

<deferred>
## Deferred Ideas

- Cross-arc dependency use cases — explicitly rejected in Phase 400 D-10 (same-parent only). Can be revisited if a concrete multi-arc integration use case emerges.
- Optional review/lock-in/ship sub-flows at Slice level — deferred from Phase 400. Workflow design for v41/v43, not artifact catalog scope.
- Templates for optional sub-flow artifacts (review, lock-in, ship) — out of scope for Phase 401 core artifact catalog. Add when sub-flows are designed.

</deferred>

---

*Phase: 401-artifact-catalog-naming-layout-cross-refs*
*Context gathered: 2026-05-07*
