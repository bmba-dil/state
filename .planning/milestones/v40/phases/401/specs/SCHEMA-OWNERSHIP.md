# Schema Ownership: Projection Classification & Validation Rules

> **Design contract for v41+ runtime schema validation and projection pipeline.**
> Consumed by: v41+ (daemon projector rebuild logic, artifact schema validator, `/state-new` frontmatter validator), v42 (quality pipeline verifier), Phase 401 Plan 02 (INDEX-SCHEMA.md projector handler), Phase 401 Plan 03 (CONSISTENCY-CODES.md validation codes).

## Design Conventions

This document classifies every artifact by who owns its schema and specifies the validation rules that enforce ownership boundaries. It builds on Phase 400 FRONTMATTER-SCHEMAS.md §Field Ownership Rules (TIER-07), which classifies individual frontmatter fields as Agent or Projector — this document extends that classification to the artifact level, determining whether the entire artifact is agent-authored, projector-rebuilt, or hybrid.

The classification drives two runtime behaviors: (1) whether the projector rebuilds the artifact from events (and if so, on what triggers), and (2) what validation checks fire when the artifact is created, read, or verified. Locked decisions referenced by ID: D-401-09 through D-401-17 (from 401-CONTEXT.md). Phase 400 specs are referenced by document+section — never reproduced (per PATTERNS.md anti-pattern convention).

Implementing ART-04 (Projection vs Authored classification) and ART-05 (Schema Validation Rules) from Phase 401 requirement set.

---

## Section 1: Projection vs Authored Classification (ART-04)

Every artifact is classified exactly once. The classification determines whether the daemon projector rebuilds it from the event stream, whether the agent writes it directly, or whether it has hybrid ownership.

### Classification Table

| Artifact | Owner | Classification | Rebuild Trigger | Fields Surviving Rebuild |
|----------|-------|----------------|-----------------|--------------------------|
| ARC.md | Agent | Agent-authored | Never rebuilt — agent writes directly; projector only updates `status`, `stage_count`, `shipped_stage_count`, `completed_at` fields | All agent-owned fields (id, title, goal, success_criteria, depends_on) survive. Projector overwrites only its owned fields on state change events |
| STAGE.md | Agent | Agent-authored | Never rebuilt — agent writes directly; projector only updates `status`, `slice_count`, `shipped_slice_count`, `completed_at` fields | All agent-owned fields (id, title, goal, success_criteria, arc_id, depends_on) survive. Projector overwrites only its owned fields |
| SLICE.md | Agent | Agent-authored | Never rebuilt — agent writes directly; projector only updates `status`, `step_count`, `completed_step_count`, `worktree_dir`, `worktree_branch`, `completed_at` fields. Agent reason fields (`deferred_reason`, `blocked_reason`) preserved by projector per TIER-07 | All agent-owned fields (id, title, goal, success_criteria, stage_id, depends_on, deferred_reason, blocked_reason) survive. Projector overwrites only its owned fields |
| CRIT.md | Agent | Agent-authored | Never rebuilt — CRIT.md has NO projector-owned fields. Agent is sole author | All fields survive (no projector writes to CRIT.md). After lock (parent tier in_progress), all mutations rejected per D-401-13 |
| MAP.md | Hybrid | Hybrid (per D-401-11) | Projector updates only `status_checkbox` values in `children` array on `state.stage.shipped` and `state.slice.shipped` events. Agent-written structure (child entries, goals) is never rebuilt | Agent-written child goals survive permanently. Projector updates only checkbox status (`[ ]` → `[x]` / `[!]`). Projector never adds, removes, or reorders child entries |
| DECISIONS.md | Agent | Agent-authored | Never rebuilt — append-only agent log per D-401-02. No projector-owned fields | All fields survive. Decisions once written are never modified |
| DESIGN.md | Agent | Agent-authored | Never rebuilt — living design document. No projector-owned fields. Always mutable per D-401-12 | All fields survive. DESIGN.md is always mutable — agent refines throughout Slice lifecycle |
| RESEARCH.md | Agent | Agent-authored | Never rebuilt — living research document. No projector-owned fields. Always mutable per D-401-12 | All fields survive. RESEARCH.md is always mutable |
| stepNPLAN.md | Agent | Agent-authored | Never rebuilt — agent writes directly; projector only updates `status` and `completed_at` fields. After parent Slice enters `in_progress`, ALL fields lock per D-401-12 | All agent-owned fields (step_number, title, goal, slice_id, plan_summary, verification_criteria, blocked_reason) survive. Projector overwrites only status and completed_at until lock |
| VERIFICATION.md | Agent | Agent-authored | Never rebuilt — agent writes directly. No projector-owned fields. Locked when Slice ships | All fields survive. After Slice shipped, snapshot-before-mutation enforced |
| SUMMARY.md | Agent | Agent-authored | Never rebuilt — agent writes directly. No projector-owned fields. Locked when Slice ships | All fields survive. After Slice shipped, snapshot-before-mutation enforced |
| index.json | Projector | Projector-rebuilt (per D-401-10) | Rebuilt on every `state.*` event (incremental — affected entries only). Full rebuild on daemon startup from event store | All fields are projector-computed — no agent fields survive. Full rebuild overwrites entire file |
| STATE.md projections | Projector | Projector-rebuilt (per D-401-10) | Rebuilt on every `state.*` event (incremental — affected tier's JSON file). Full rebuild on daemon startup | All fields are projector-computed from event stream. No agent fields survive. Full rebuild overwrites entire projection files |

### Classification Summary

| Classification | Count | Artifacts |
|----------------|-------|-----------|
| Agent-authored | 10 | ARC.md, STAGE.md, SLICE.md, CRIT.md, DECISIONS.md, DESIGN.md, RESEARCH.md, stepNPLAN.md, VERIFICATION.md, SUMMARY.md |
| Hybrid | 1 | MAP.md — agent writes child entries and goals; projector updates checkboxes (D-401-11) |
| Projector-rebuilt | 2 | index.json (D-401-14), STATE.md projections (D-401-07) |
| **Total** | **13** | |

**Agent-authored (10 types) per D-401-09:** These are written by the agent during planning and workflow phases. The projector NEVER rebuilds them from events — it only updates its owned frontmatter fields (`status`, counts, timestamps) on state change events. All agent-written fields (titles, goals, descriptions, criteria, decisions) persist permanently and are never overwritten by the projector.

**Projector-rebuilt (2 types) per D-401-10:** These are computed entirely from the event stream. The projector rebuilds them on daemon startup (full rebuild from event store) and incrementally on every state change. Agent NEVER writes to these files — they are "read-only" from the agent's perspective. Any agent modifications would be overwritten on the next projector rebuild.

**Hybrid (1 type) per D-401-11:** MAP.md has split ownership. The planner (agent) creates the file structure, child entries, and goals during `/state-new arc` or `/state-new stage`. The projector exclusively owns checkbox status and updates it reactively as children advance. The projector never adds, removes, or reorders child entries — it only flips checkbox values.

---

## Section 2: MAP.md Hybrid Ownership Detail (D-401-11)

MAP.md is the only hybrid artifact. Its ownership model requires precise specification because both agent and projector write to the same file, but to different fields with different lifecycle triggers.

### Creation and Structure

MAP.md is created by the planner during the `/state-new arc` or `/state-new stage` flow (D-401-04). The planner:
1. Reads the parent tier's CRIT.md to understand what must be accomplished
2. Generates child entries — one per child tier unit — with an ID and a goal derived from CRIT.md
3. Sets all `status_checkbox` values to `"[ ]"` (planned)

Example Arc MAP.md `children` array:
```yaml
children:
  - id: "stage-01"
    goal: "Implement OAuth handlers with byte-for-byte stealth header parity"
    status_checkbox: "[ ]"
  - id: "stage-02"
    goal: "Implement token management with refresh rotation and 10s double-check"
    status_checkbox: "[ ]"
```

Example Stage MAP.md `children` array:
```yaml
children:
  - id: "slice-01"
    goal: "Baseline auth server with dual-write event store"
    status_checkbox: "[ ]"
  - id: "slice-02"
    goal: "Wire Anthropic OAuth stealth with PKCE and beta header"
    status_checkbox: "[ ]"
```

### Projector Checkbox Updates

The projector updates only the `status_checkbox` field within each child entry. It does NOT add, remove, or reorder children. The specific triggers are:

| MAP.md Level | Trigger Event | Checkbox Transition |
|-------------|---------------|---------------------|
| Arc MAP.md | `state.stage.shipped` | Child Stage entry: `[ ]` → `[x]` |
| Arc MAP.md | `state.stage.abandoned` | Child Stage entry: `[ ]` → `[!]` |
| Stage MAP.md | `state.slice.shipped` | Child Slice entry: `[ ]` → `[x]` |
| Stage MAP.md | `state.slice.abandoned` | Child Slice entry: `[ ]` → `[!]` |

The abandoned marker (`[!]`) is the only variance from the standard checkbox. It signals that the child reached a terminal exit state rather than completing successfully — the agent can see at a glance which children were abandoned vs. shipped.

### Checkbox Legend

| Checkbox | Meaning | Set By | Trigger |
|----------|---------|--------|---------|
| `[ ]` | Planned — not yet started | Planner (agent) | MAP.md creation |
| `[x]` | Shipped — completed successfully | Projector | `state.{child-tier}.shipped` |
| `[!]` | Abandoned — terminal exit | Projector | `state.{child-tier}.abandoned` |

### Guarantees

The projector guarantees:
1. **No child insertion or removal:** The `children` array's length and order are immutable once MAP.md is created. The projector never modifies the array structure.
2. **No goal modification:** Child goal strings are agent-written and never touched by the projector.
3. **Idempotent updates:** If a checkbox is already `[x]`, a duplicate `state.*.shipped` event is a no-op (projector is idempotent).
4. **Atomic writes:** Checkbox updates are atomic file writes — no partial state visible to readers.
5. **Bypass immutability:** Projector checkbox updates bypass the immutability lock that applies to agent-initiated edits (per RESEARCH.md open question #5). The agent cannot edit checkboxes — only the projector can.

---

## Section 3: Schema Validation Rules (ART-05)

Validation rules specify WHEN validation fires and WHAT it checks. These are design contracts — implementation details (Python decorator code, SQL queries, pydantic validator methods) are out of scope for v40.

### Validation Timing

| Trigger Point | What Validates | Scope | Consumer |
|---------------|----------------|-------|----------|
| Artifact creation (CLI command) | Frontmatter schema against pydantic model | Single artifact | v41+ `/state-new arc|stage|slice` command + pydantic frontmatter validator |
| Artifact read (daemon loads artifact) | Frontmatter schema + cross-reference ID resolution | Single artifact + referenced IDs | v41+ daemon artifact loader |
| Slice verify phase (`/state-verify slice`) | Full artifact consistency check | All Slice artifacts (SLICE.md through SUMMARY.md) | v41+ verification harness |
| Daemon startup (D-401-17) | Full consistency check via `validate_consistency()` | All artifacts in `.state/build/` | v41+ daemon startup gate |

### Pydantic-Level Validation (Rules 1–5)

These checks are enforced by pydantic `extra="forbid"` on all frontmatter models. They fire at artifact creation and on every artifact read. Consumed by v41+ pydantic frontmatter validator (reads Phase 400 models from `state_core/schemas/frontmatter.py`).

| Rule | Check | Description | Error Behavior |
|------|-------|-------------|----------------|
| V-01 | Unknown field rejection | Every frontmatter field must exist in the corresponding pydantic model. Unknown fields are rejected at parse time by `extra="forbid"` | Artifact creation blocked — invalid frontmatter prevents file write |
| V-02 | Required field presence | All required fields must be present: `id`, `title`, `goal` (all tiers), plus tier-specific required fields (`arc_id` for Stage, `stage_id` for Slice, `step_number`/`slice_id` for Step) | Artifact creation blocked — missing required field prevents file write |
| V-03 | Field type matching | Field types must match the pydantic model: `str` for text fields, `list[str]` for criteria arrays, `list[dict[str, str]]` for `depends_on`, `int` for counts/step_number, `str \| None` for optional fields | Artifact creation blocked — type mismatch prevents file write |
| V-04 | Status literal validation | Status values must be valid `Literal` members for that tier's state machine. See Phase 400 FSM-TABLES.md for valid status values per tier | Artifact read fails — invalid status indicates corrupted or tampered frontmatter |
| V-05 | ID format validation | ID fields must match D-01 regex: `^arc-\d+$`, `^stage-\d+(\.\d+)?$`, `^slice-\d+(\.\d+)?$`, `step_number` is integer (no regex for step_number — it's typed as `int`). Decimal IDs valid for Stage/Slice/Step per D-16 | Artifact creation blocked — invalid ID format prevents file write |

### Cross-Reference Validation (Rules 6–12)

These checks go beyond pydantic — they validate that cross-references between artifacts are consistent, resolvable, and respect hierarchy rules. Consumed by v41+ daemon artifact loader, scheduler dependency resolver, and consistency validator.

| Rule | Check | Description | Severity | Consumer |
|------|-------|-------------|----------|----------|
| V-06 | Dependency ID resolution | Every `depends_on[{id}]` reference must resolve to an existing ID in index.json. O(1) lookup per D-401-14. Unresolved ID → artifact is blocked from entering `in_progress` until resolved (D-401-15) | ERROR (blocks `in_progress` transition) | v41+ daemon artifact loader (reads index.json per D-401-14) |
| V-07 | Edge type validity | Edge types in `depends_on[{edge}]` must be one of: `blocks`, `soft`, `data`. These match scheduler `EdgeKind = Literal["blocks", "soft", "data"]` per Phase 400 D-12. Invalid edge type → artifact creation blocked | ERROR (blocks artifact creation) | v41+ daemon artifact loader (validates against scheduler EdgeKind) |
| V-08 | Same-parent constraint (D-10) | `depends_on` target must be a sibling within the same parent container. Stage deps: sibling Stages within same Arc. Slice deps: sibling Slices within same Stage. Cross-parent deps rejected | ERROR (blocks artifact creation) | v41+ scheduler dependency resolver (reads Phase 400 D-10) |
| V-09 | No downward references | Parent→child references are forbidden. An Arc must not `depends_on` a Stage; a Stage must not `depends_on` a Slice. This violates the scoping hierarchy — parents scope children, not depend on them | ERROR (blocks artifact creation) | v41+ scheduler dependency resolver |
| V-10 | No cross-mode references | Build artifacts (`.state/build/`) must only reference targets in `.state/build/`. Teach artifacts (`.state/teach/`) must only reference targets in `.state/teach/`. Mode isolation per v11. Validated via `BUILD_ONLY_EVENT_PREFIXES` / `TEACH_ONLY_EVENT_PREFIXES` | ERROR (blocks artifact creation) | v41+ daemon mode middleware |
| V-11 | Descoped-ID detection | When a referenced ID is found in index.json but its tier has been abandoned (D-13), the reference is flagged. The referrer is surfaced with a W-code (W005). If referrer is `in_progress`, execution blocks until user resolves (reassign target, defer dependency, or remove reference). Per D-401-15 | WARNING (advisory at plan time); ERROR if referrer `in_progress` | v41+ consistency validator (`validate_consistency()`) |
| V-12 | Content-hash pinning | When artifact A creates a cross-reference to artifact B, A records B's content hash. On subsequent reads, hash mismatch → WARNING if target is mutable (DESIGN.md, RESEARCH.md — expected to change), INFO if immutable (CRIT.md after lock, stepNPLAN.md after lock — unexpected change). Enables drift detection without blocking | WARNING (mutable target) / INFO (immutable target) | v41+ consistency validator (hash comparison in `validate_consistency()`) |

### Validation Rule Summary

| Category | Count | Rules |
|----------|-------|-------|
| Pydantic-level (frontmatter schema) | 5 | V-01 through V-05 |
| Cross-reference (ID resolution + policy) | 7 | V-06 through V-12 |
| **Total** | **12** | |

**Consumer attribution:**
- Rules V-01 through V-05: consumed by v41+ pydantic frontmatter validator (reads Phase 400 models from FRONTMATTER-SCHEMAS.md)
- Rules V-06 through V-07: consumed by v41+ daemon artifact loader (reads index.json per D-401-14)
- Rules V-08 through V-09: consumed by v41+ scheduler dependency resolver (reads Phase 400 D-10)
- Rule V-10: consumed by v41+ daemon mode middleware (reads v11 mode isolation prefixes)
- Rules V-11 through V-12: consumed by v41+ consistency validator (`validate_consistency()` per Plan 401-03)

---

## Section 4: Cross-References to Phase 400

This document depends on the following Phase 400 specifications. Each is referenced by document+section — Phase 400 content is never reproduced.

| Phase 400 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| FRONTMATTER-SCHEMAS.md §Field Ownership Rules (lines 198–235) | Source of truth for which individual frontmatter fields are Agent vs Projector. This document extends that classification to the artifact level (which entire artifacts are agent-authored vs projector-rebuilt). Field ownership table (TIER-07) is the canonical reference — NOT reproduced here |
| FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding (lines 239–269) | Aggregate ID format rules. Regex patterns for ID validation (V-05). Hierarchical slash-delimited encoding for parent extraction. Short form (`arc-{n}`) vs hierarchical form (`arc-{n}/stage-{n}/slice-{n}`) conventions |
| FRONTMATTER-SCHEMAS.md §ArcFrontmatter (lines 18–53) | Arc pydantic model — field list, types, defaults. Referenced by V-01 through V-04 (pydantic-level validation) |
| FRONTMATTER-SCHEMAS.md §StageFrontmatter (lines 55–96) | Stage pydantic model — field list, types, defaults |
| FRONTMATTER-SCHEMAS.md §SliceFrontmatter (lines 99–143) | Slice pydantic model — field list, types, defaults, agent reason fields |
| FRONTMATTER-SCHEMAS.md §StepFrontmatter (lines 146–195) | Step pydantic model — field list, types, defaults, D-03 renamed status values |
| DESC-SEMANTICS.md §Abandon Cascade (D-13) | Descoped-ID detection triggers for V-11. Abandonment cascades create the conditions V-11 detects |
| FSM-TABLES.md | Status `Literal` valid values per tier — used by V-04 (status literal validation). Each tier's state machine defines the set of valid status values |

---

## Section 5: Threat Model Alignment

Mapping specification-level threats to mitigations in this document:

| Threat ID | Category | Mitigation |
|-----------|----------|------------|
| T-401-03 | Elevation of Privilege — Agent writing projector-owned fields | Section 1 classification table explicitly identifies which artifacts are projector-rebuilt (index.json, STATE.md) and which are agent-authored. For agent-authored artifacts, field ownership is per-field (Agent vs Projector) as defined in Phase 400 TIER-07. For projector-rebuilt artifacts, the agent has NO write access — full rebuild overwrites any agent modifications. V-01 (`extra="forbid"`) rejects unknown fields at artifact creation, preventing the agent from adding projector-owned fields to agent-authored artifacts. |
| T-401-04 | Tampering — Immutability bypass | Section 2 MAP.md hybrid ownership detail specifies exact projector trigger events and guarantees the projector never adds/removes/reorders children. D-401-13 snapshot-before-mutation protocol at daemon level enforces artifact-level immutability rules (defined in ARTIFACT-CATALOG.md Section 3). V-12 content-hash pinning detects tampering with supposedly immutable artifacts. |
| T-401-05 | Information Disclosure — Specification quality degradation | Cross-reference consistency checks between Plan 01 (ARTIFACT-CATALOG.md) and Plan 02 (DIRECTORY-TREE.md) verify that every artifact classified here has a corresponding catalog entry and directory placement. No sensitive data in design specs. |

---

*Design contract for v41+ runtime schema validation and projection pipeline. All 13 artifact types classified as Agent (10), Hybrid (1), or Projector (2). MAP.md hybrid ownership specified with exact checkbox trigger event mapping (state.stage.shipped, state.slice.shipped, state.*.abandoned). 12 schema validation rules covering creation, read, verify, and daemon startup timing — 5 pydantic-level, 7 cross-reference/additional. All Phase 400 references by document+section — no reproduction.*
