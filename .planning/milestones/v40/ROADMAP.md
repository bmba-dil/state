# ROADMAP: v40 Build Hierarchy & Artifact System Architecture

**Milestone:** v40
**Phase range:** 400–401
**Created:** 2026-05-06
**Type:** Design-phase milestone (zero code — architecture documents only)
**Granularity:** fine (from config.json)

**Core value:** The four-tier product hierarchy (Arc → Phase → Slice → Step) and its complete artifact system are fully architected as pydantic schemas, state machine diagrams, on-disk layout specifications, and cross-referencing rules — providing the design contract for all downstream build-mode implementation (v41–v43, v14–v17).

**Depends on:** v11 (Mode Enforcement) — the hierarchy lives under `.state/build/` and must respect mode isolation. v5 (DAG Scheduler) — the design must integrate with the existing scheduler. v4 (Worktree + Snapshot) — worktrees attach to Slices; snapshots attach to Steps. v1 (Event Store) — all state changes are events.

---

## Phases

- [x] **Phase 400: Tier Definitions & State Machines** (Completed 2026-05-06) — Complete behavioral definitions, state machines, event taxonomies, and pydantic frontmatter models for all four tiers
- [ ] **Phase 401: Artifact Catalog, Naming, Layout, Cross-Refs** — Every artifact, naming convention, on-disk path, and cross-reference rule fully specified

---

## Phase Details

### Phase 400: Tier Definitions & State Machines
**Goal**: All four tiers have complete behavioral definitions, state machines, and event taxonomies that are internally consistent and ready for artifact catalog design.
**Depends on**: Nothing (first v40 phase)
**Requirements**: TIER-01, TIER-02, TIER-03, TIER-04, TIER-05, TIER-06, TIER-07, TIER-08, FSM-01, FSM-02, FSM-03, FSM-04, FSM-05, FSM-06
**Success Criteria** (what must be TRUE):
  1. Every tier (Arc, Stage, Slice, Step) has a standalone specification document that can be read and understood without referencing other documents — defining role, owned artifacts, behavioral primitives, and cross-tier relationships.
2. State transition tables exist for all four tiers specifying every valid state transition with guard conditions and event triggers. Arcs, Stages, and Slices are limitless. Only Steps per Slice are bounded by the token context limit.
3. The composite event cascade from Step→Slice→Stage→Arc is fully specified with explicit trigger conditions at each tier.
4. Pydantic models with `extra="forbid"` are defined for all tier artifact frontmatter, with explicit agent-owned vs projector-owned field classification (TIER-07 boundaries respected per field).
5. Both Arcs and Stages require a formal auditing state before shipping. Slices self-verify inline, recording verification in their directory's tracking files. Descope, abandon, blocked, and decimal-insertion semantics are specified consistently across all four tiers with cascade rules per edge type.

**Plans**: 3 plans in 2 waves (01 autonomous, 02+03 autonomous)

Plans:
- [x] 400-01-PLAN.md — Four tier specification documents (Arc, Stage, Slice, Step)
- [x] 400-02-PLAN.md — State transition tables, event taxonomy, composite cascade, frontmatter schemas
- [x] 400-03-PLAN.md — Descope, abandon, blocked, and decimal insertion semantics

---

### Phase 401: Artifact Catalog, Naming, Layout, Cross-Refs
**Goal**: Every artifact, naming convention, on-disk path, and cross-reference rule is fully specified, producing a complete blueprint for the `.state/build/` filesystem.
**Depends on**: Phase 400
**Requirements**: ART-01, ART-02, ART-03, ART-04, ART-05, DSK-01, DSK-02, DSK-03, DSK-04, DSK-05, DSK-06, REF-01, REF-02, REF-03, REF-04, REF-05, REF-06
**Success Criteria** (what must be TRUE):
  1. The artifact catalog documents every file type across all four tiers with purpose, owning tier, schema ownership (agent vs projector), creation/update triggers, and file format.
  2. Templates exist for every artifact file type (ARC.md.tmpl, PHASE.md.tmpl, SLICE.md.tmpl, STEP.md.tmpl, DISCUSS.md.tmpl, PLAN.md.tmpl, VERIFY.md.tmpl, STATE.md) with validated frontmatter structure.
  3. The complete `.state/build/` directory tree is specified with all naming conventions (IDs, directories, slugs, display prefixes), concurrent access rules, and the `index.json` artifact registry.
  4. Immutability rules, projection-vs-authored distinction, schema validation rules, and broken-reference handling are specified per tier with edge-type cascade rules.
  5. The 15 consistency validation codes (W001–W015) and the `validate_consistency()` function specification are defined.
**Plans**: 3 plans in 3 waves

Plans:
- [ ] 401-01-PLAN.md — Artifact catalog + templates + immutability + schema ownership (ART-01..05)
- [ ] 401-02-PLAN.md — Directory tree + naming + STATE placement + index.json schema (DSK-01..06)
- [ ] 401-03-PLAN.md — Cross-reference format + W-codes + validate_consistency() (REF-01..06)

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 400. Tier Definitions & State Machines | 3/3 | Complete | 2026-05-06 |
| 401. Artifact Catalog, Naming, Layout, Cross-Refs | 3/3 | Planned | 2026-05-07 |

---

## Requirement Coverage

| Category | Count | REQ-IDs | Phase |
|----------|-------|---------|-------|
| TIER — Tier Definitions | 8 | TIER-01..TIER-08 | 400 |
| FSM — State Machine Specs | 6 | FSM-01..FSM-06 | 400 |
| ART — Artifact Catalog | 5 | ART-01..ART-05 | 401 |
| DSK — On-Disk Layout | 6 | DSK-01..DSK-06 | 401 |
| REF — Cross-Referencing System | 6 | REF-01..REF-06 | 401 |
| **Total** | **31** | — | **100% mapped** |

---

## Out of Scope (v40)

- **Code implementation** — v40 produces architecture documents only. Implementation is v14–v27 (post design spike).
- **Runtime integration** — Pydantic schemas defined in v40 are used as design contracts; wiring into `state_core/schema.py` is v41+.
- **TUI visualization of hierarchy** — Designing the TUI render patterns for the hierarchy is v17.
- **Agent harness** — Context management, task injection, and deviation handling are v41.
- **Quality pipeline** — Verifiers, plan checker, stub detection, threat modeling are v42.
- **GSD command ports** — Mapping GSD commands to state-native workflows is v43.
- **Teach-mode equivalents** — Teach-mode hierarchy (Subject→Module→Concept→Drill) is v46–v50.

---

*Roadmap created: 2026-05-06*
