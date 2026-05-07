# Requirements Archive: v40 v40

**Archived:** 2026-05-07
**Status:** SHIPPED

For current requirements, see `.planning/REQUIREMENTS.md`.

---
# REQUIREMENTS: v40 Build Hierarchy & Artifact System Architecture

**Milestone:** v40 — Build Hierarchy & Artifact System Architecture  
**Type:** Design-phase (no code — architecture documents only)  
**Created:** 2026-05-06  

---

## v40 Requirements

### Tier Definitions (TIER)

- [x] **TIER-01** (Phase 400): Each of the four tiers (Arc, Stage, Slice, Step) has a complete behavioral definition specifying its role in the hierarchy, its relationship to other tiers, its state machine, its owned artifacts, and its behavioral primitives.
- [x] **TIER-02** (Phase 400): Arc definition includes state machine (planned → in_progress → shipped | abandoned), owned artifacts (ARC.md), required frontmatter fields (id, title, status, goal, success_criteria, depends_on, phases), and cross-Arc dependency rules.
- [x] **TIER-03** (Phase 400): Stage definition includes state machine (planned → in_progress → verified → shipped | abandoned), owned artifacts (STAGE.md), Slices as sub-units, success criteria rollup from child Slices, and cross-Stage dependency rules.
- [x] **TIER-04** (Phase 400): Slice definition includes state machine (planned → worktree_ready → in_progress → shipped | reverted), owned artifacts (SLICE.md), Steps as serial sub-units, worktree association (one per Slice), and dependency DAG edges.
- [x] **TIER-05** (Phase 400): Step definition includes state machine (idle → designing → planning → running → verifying → done | blocked | abandoned), owned artifacts (STEP.md, DESIGN.md, PLAN.md, VERIFY.md), and the full design→plan→run→verify cycle ownership.
- [x] **TIER-06** (Phase 400): Every tier defines its event taxonomy — the complete set of events that advance its state machine, including composite events for cross-tier rollup (Step events aggregate into Slice STATE.md, Slice events into Stage, Stage into Arc).
- [x] **TIER-07** (Phase 400): Frontmatter field ownership is explicitly declared per tier — every field is classified as agent-owned (title, goal, goal_criteria) or projector-owned (status, completed_at, child-ID arrays), never mixed within a field.
- [x] **TIER-08** (Phase 400): Pydantic models with `extra="forbid"` are defined for every tier artifact's frontmatter, serving as both the design contract and the future runtime validator.

### Artifact Catalog (ART)

- [ ] **ART-01**: A complete artifact catalog documents every recognized file type across all four tiers — purpose, owning tier, schema ownership (agent vs projector), creation trigger, update triggers, and file format.
- [ ] **ART-02**: Templates exist for every artifact file type (ARC.md.tmpl, PHASE.md.tmpl, SLICE.md.tmpl, STEP.md.tmpl, DISCUSS.md.tmpl, PLAN.md.tmpl, VERIFY.md.tmpl, STATE.md) with validated frontmatter structure.
- [ ] **ART-03**: Immutability rules are specified per tier — STEP.md verify_contract locks after execute begins, ARC.md phases[] array locks while child Phases are in_progress, snapshot-before-mutation protocol for immutable fields.
- [ ] **ART-04**: The artifact catalog defines which artifacts are projections of the event store (STATE.md at every tier, index.json) and which are agent-authored originals (ARC.md goal/description, STEP.md plan, DISCUSS.md).
- [ ] **ART-05**: Schema validation rules are specified — every artifact read validates against its pydantic model, unknown fields are rejected, cross-reference IDs are verified to exist, and descoped-ID references are flagged.

### State Machine Specs (FSM)

- [x] **FSM-01** (Phase 400): Full state transition tables are specified for all four tiers — every state maps to valid next states with guard conditions derived from event completion, child status rollup, or agent invocation.
- [x] **FSM-02** (Phase 400): The composite event cascade is specified — when the last Step in a Slice reaches DONE, a `state.slice.steps_completed` event fires, propagating upward through Slice→Stage→Arc rollup with explicit trigger conditions at each tier.
- [x] **FSM-03** (Phase 400): Descope and abandon semantics are specified — when a Step or Slice is abandoned, dependents are resolved via cascade-abandon, assume-satisfied with explicit flag, or block-and-surface based on the dependency edge type.
- [x] **FSM-04** (Phase 400): The decimal insertion protocol is specified — how Slice/Step IDs support single-level decimal inserts (003.1, 003.2) without renumbering, with a hard cap at one decimal level (no 003.1.2), and with the structural reorganization threshold for when to create a new Stage/Slice instead.
- [x] **FSM-05** (Phase 400): Blocked state semantics are specified — how a Step enters BLOCKED (depends_on unresolved, external condition), what `blocked_reason` stores, and how the scheduler detects unblocking to transition to RUNNING.
- [x] **FSM-06** (Phase 400): Arcs, Stages, and Slices are limitless. The only count constraint is Steps per Slice, bounded by the context token limit so a Slice can complete end-to-end in one agent session. Stage planning scopes each Slice to fit the context window, naturally producing many Slices for broad CRIT.md scope.

### On-Disk Layout (DSK)

- [ ] **DSK-01**: The `.state/build/` directory tree is fully specified — arcs/{arc-id}/phases/{phase-id}/slices/{slice-id}/steps/{step-id}/ hierarchy with all artifact files nested under their owning tier directory.
- [ ] **DSK-02**: Naming conventions are specified for numeric IDs (sequential per parent, zero-padded), directory paths (ID-based, not slug-based), slugs (display-only, derived from title), and display prefixes (child-prefixed for readability: phase-001-003).
- [ ] **DSK-03**: The STATE.md placement strategy is resolved — consolidated JSON projections under `.state/build/state/` are the canonical STATE artifacts, with an `export-state` CLI for on-demand per-directory STATE.md generation.
- [ ] **DSK-04**: File count optimization is specified — per-Step file consolidation strategy (5 separate files vs 1-2 consolidated ARTIFACTS.md), with file count projections at scale (20 Arcs × ~100 Steps = ~2000 Steps) to avoid filesystem bloat.
- [ ] **DSK-05**: An `index.json` artifact registry is specified at `.state/build/index.json` — machine-readable mapping of every artifact ID to its path, type, tier, status, and last-updated timestamp, rebuilt by the projector on every state change.
- [ ] **DSK-06**: The on-disk layout supports concurrent access — multiple worktrees create artifacts under the same hierarchy without conflicts, with clear rules for which tier creates which directories and a lock-free append-only write model.

### Cross-Referencing System (REF)

- [ ] **REF-01**: The cross-reference format is specified — all references use stable IDs (never paths, never slugs), with an ID→path resolution algorithm backed by the projector's artifact index, and content-hash pinning of cross-references at creation time.
- [ ] **REF-02**: Depends-on edge types (blocks, soft, data) are fully specified with their semantics — blocks (hard prerequisite, scheduler blocks until target DONE), soft (advisory ordering, scheduler may override), data (artifact-producing, hard edge + artifact path copy).
- [ ] **REF-03**: Cross-tier dependency policy is specified — same-tier edges allowed, upward edges allowed (Step→Slice), downward edges forbidden (Slice→Step in same Slice fine, but cross-Slice Step→Step requires Slice-level edge), and cross-mode edges blocked at schema validation.
- [ ] **REF-04**: Broken reference handling is specified — behavior when a reference target is deleted, descoped, or abandoned, including cascade rules per edge type, explicit assume-satisfied flags, and surface-to-agent for human judgment cases.
- [ ] **REF-05**: Consistency validation codes (W001–W015) are specified — 15 health checks covering orphan IDs, stale status fields, missing parent pointers, cross-referenced-to-descoped, mismatched state projections, duplicate IDs, invalid edge types, cycle detection, and cross-mode leakage.
- [ ] **REF-06**: A `validate_consistency()` function specification is provided — runs on daemon startup and after every state change, walks all artifacts, verifies every cross-reference resolves, detects filesystem-vs-event-store divergence, and always reports event store as authoritative on mismatch.

---

## Future Requirements (Deferred)

*None — this is a self-contained design milestone. All requirements are scoped to v40.*

---

## Out of Scope

- **Code implementation** — v40 produces architecture documents only. Implementation is v14–v27 (post design spike).
- **Runtime integration** — Pydantic schemas defined in v40 are used as design contracts; wiring into `state_core/schema.py` is v41+.
- **TUI visualization of hierarchy** — Designing the TUI render patterns for the hierarchy is v17 (Build TUI Extensions), which will consume v40's artifact catalog.
- **Agent harness** — Context management, task injection, and deviation handling are v41.
- **Quality pipeline** — Verifiers, plan checker, stub detection, threat modeling are v42.
- **GSD command ports** — Mapping GSD commands to state-native workflows is v43.
- **Teach-mode equivalents** — Teach-mode hierarchy (Subject→Module→Concept→Drill) is v46–v50.

---

## Traceability

| REQ-ID | Phase | Success Criteria |
|--------|-------|-----------------|
| TIER-01 | 400 | SC1 |
| TIER-02 | 400 | SC1, SC2 |
| TIER-03 | 400 | SC1, SC2 |
| TIER-04 | 400 | SC1, SC2 |
| TIER-05 | 400 | SC1, SC2 |
| TIER-06 | 400 | SC3 |
| TIER-07 | 400 | SC4 |
| TIER-08 | 400 | SC4 |
| FSM-01 | 400 | SC2 |
| FSM-02 | 400 | SC3 |
| FSM-03 | 400 | SC5 |
| FSM-04 | 400 | SC5 |
| FSM-05 | 400 | SC5 |
| FSM-06 | 400 | SC2 |
| ART-01 | 401 | SC1 |
| ART-02 | 401 | SC2 |
| ART-03 | 401 | SC4 |
| ART-04 | 401 | SC4 |
| ART-05 | 401 | SC4 |
| DSK-01 | 401 | SC3 |
| DSK-02 | 401 | SC3 |
| DSK-03 | 401 | SC3 |
| DSK-04 | 401 | SC3 |
| DSK-05 | 401 | SC3 |
| DSK-06 | 401 | SC3 |
| REF-01 | 401 | SC3 |
| REF-02 | 401 | SC3 |
| REF-03 | 401 | SC3 |
| REF-04 | 401 | SC4 |
| REF-05 | 401 | SC5 |
| REF-06 | 401 | SC5 |

**Coverage:** 31/31 requirements mapped (100%).

*Last updated: 2026-05-06*
