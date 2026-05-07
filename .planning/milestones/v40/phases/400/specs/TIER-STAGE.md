# Tier Specification: Stage

> **Migration Note:** This tier was formerly called **Phase** in GSD lineage. The rename to **Stage**
> avoids confusion with workflow phases (design phase, run phase, verify phase). All specification
> documents, command names, event type strings, and artifact files use "Stage" going forward.
> Existing codebase event types (`state.phase.*`) and class names (`PhasePlannedData`, etc.) will
> be migrated to `state.stage.*` and `StagePlannedData` in v41+. See the Event Migration table
> below for the complete old→new mapping.

## Role in Hierarchy

Stage is the **decomposition layer** under Arc. A Stage groups related Slices and tracks
cross-Slice verification. Where an Arc defines a broad feature block (e.g., "Auth System"),
a Stage decomposes it into coherent work groupings (e.g., "OAuth Provider Migration",
"Token Management"). A Stage's primary responsibility is to ensure that its child Slices
integrate correctly — this is enforced by the `verified` state, which requires explicit
cross-Slice verification before the Stage can ship.

Stages depend on other Stages within the SAME Arc only (D-10 — same-parent-only constraint).
A Stage cannot transition to `in_progress` until at least one child Slice is `worktree_ready`.
A Stage cannot transition to `verified` until ALL child Slices are `shipped` AND a manual
verify-stage command passes. The Stage's `shipped` state signals to the parent Arc that
this decomposition unit is complete.

## State Machine

```
                 ┌─────────────┐
    created      │   planned   │
  ─────────────► │             │
                 └──────┬──────┘
                        │ state.stage.started
                        │ guard: ≥1 child Slice is worktree_ready
                        ▼
                 ┌─────────────┐
                 │ in_progress │──────────────────────────────┐
                 │             │                              │
                 └──────┬──────┘                              │
                        │ state.stage.slices_shipped           │
                        │ guard: ALL child Slices are shipped  │
                        ▼                                      │
                 ┌─────────────┐                              │
                 │  verified   │                              │
                 │             │                              │
                 └──────┬──────┘                              │
                        │ state.stage.completed                │ state.stage.abandoned
                        │ guard: manual verify-stage           │ guard: explicit abandon
                        │ command passes                       │
                        ▼                                      ▼
                 ┌─────────────┐                      ┌──────────────┐
                 │   shipped   │                      │  abandoned   │
                 │             │                      │              │
                 └─────────────┘                      └──────────────┘

  Forward states (count toward ≤4 budget): planned, in_progress, verified, shipped = 4
  Exit state (excluded from budget): abandoned = 1

  Cascading abandon (D-13): When a Stage is abandoned, its child Slices are abandoned
  and any Slices that depended on those Slices are auto-marked BLOCKED.
```

## State Transition Table

| From | To | Event Trigger | Guard Condition | Budget Check |
|------|----|---------------|-----------------|-------------|
| `planned` | `in_progress` | `state.stage.started` | ≥1 child Slice is `worktree_ready` | ≤4 ✓ |
| `in_progress` | `verified` | `state.stage.slices_shipped` | ALL child Slices are `shipped` (D-19 composite check by projector) | ≤4 ✓ |
| `verified` | `shipped` | `state.stage.completed` | Manual verify-stage command passes (cross-Slice integration + UAT) | ≤4 ✓ |
| `*` | `abandoned` | `state.stage.abandoned` | Explicit abandon; cascade child Slices → abandoned; dependent Slices → blocked (D-13) | — |
| `planned` | `abandoned` | `state.stage.abandoned` | Explicit abandon command | — |
| `in_progress` | `abandoned` | `state.stage.abandoned` | Cascade: child Slices abandoned; dependents → blocked | — |
| `verified` | `abandoned` | `state.stage.abandoned` | Explicit abandon command | — |

**Composite state note (D-19):** The Stage is `in_progress` when any child Slice is active (projector-computed). The transition to `verified` requires ALL child Slices to be `shipped` — this is checked by the projector as a composite condition. The `verified` state itself is entered only after the manual verify-stage command passes, not automatically.

## Owned Artifacts

| Artifact | Purpose | Schema Owner |
|----------|---------|--------------|
| CRIT.md | Must-have criteria for the Stage (replaces REQUIREMENTS) — defines what "done" means at the Stage level | Agent |
| MAP.md | Stage-level roadmap — maps child Slices, their ordering, and dependency edges | Agent |
| STAGE.md | Stage definition document with frontmatter fields (id, title, goal, success_criteria, arc_id, depends_on) | Agent |
| STATE.md | State projection rebuilt by the projector from event store — current status, Slice counts, timestamps | Projector |

**Artifact creation triggers:**
- CRIT.md, MAP.md, STAGE.md — created by agent during Stage planning (`/state-new stage`)
- STATE.md — created and updated by projector on every state change event

**Migration:** The artifact file formerly named `PHASE.md` is now `STAGE.md`. Existing codebase references to `PHASE.md` in directory layout specs are updated to `STAGE.md`.

## Frontmatter Fields

| Field | Type | Owner | Required | Description |
|-------|------|-------|----------|-------------|
| `id` | `str` | Agent | Yes | Stage identifier: `stage-{n}` — dash-prefix, no leading zeros per D-01. Example: `stage-22` |
| `title` | `str` | Agent | Yes | Human-readable name. Example: "OAuth Provider Migration" |
| `goal` | `str` | Agent | Yes | One-line outcome describing what the Stage delivers |
| `success_criteria` | `list[str]` | Agent | Yes | Measurable outcomes that define Stage completion |
| `arc_id` | `str` | Agent | Yes | Parent Arc identifier. Example: `"arc-45"`. Links Stage to its parent Arc. Every Stage belongs to exactly ONE Arc |
| `depends_on` | `list[dict]` | Agent | No | Dependency edges to sibling Stages within the SAME Arc (D-10 same-parent-only). Format per D-12: `[{id: "stage-02", edge: "blocks"}]`. Edge types: `blocks`, `soft`, `data`. Default: `[]` |
| `status` | `Literal["planned", "in_progress", "verified", "shipped", "abandoned"]` | Projector | Yes | Current state, computed from event stream. Default: `"planned"` |
| `slice_count` | `int` | Projector | No | Number of child Slices. Default: `0` |
| `shipped_slice_count` | `int` | Projector | No | Number of child Slices in `shipped` state. Default: `0` |
| `completed_at` | `str \| None` | Projector | No | ISO 8601 timestamp when Stage reached `shipped`. Default: `null` |

**Field ownership note:** Every field is classified EXACTLY ONCE as Agent or Projector. Agent never writes projector-owned fields (`status`, `slice_count`, `shipped_slice_count`, `completed_at`). Projector never writes agent-owned fields (`id`, `title`, `goal`, `success_criteria`, `arc_id`, `depends_on`). The `depends_on` field uses the key `edge` (not `kind`) per D-12.

**ID format:** `stage-{n}` — dash-prefix, lowercase prefix, no leading zeros (D-01). Slugs for display: `stage-{n}-{slug}` (D-02). ID resolution works with or without the slug. Example: `stage-22-oauth-migration/` directory — `stage-22` is the stable ID.

## Events

| Event Type | Trigger | State Transition | Description |
|-----------|---------|------------------|-------------|
| `state.stage.created` | `/state-new stage` | none → `planned` | Stage aggregate created, enters initial state |
| `state.stage.started` | First child Slice reaches `worktree_ready` | `planned` → `in_progress` | At least one child Slice is `worktree_ready` |
| `state.stage.slices_shipped` | Projector detects all child Slices `shipped` | `in_progress` → `verified` | Composite check (D-19): ALL child Slices are `shipped` AND manual verify-stage passes |
| `state.stage.completed` | Manual verify-stage command passes | `verified` → `shipped` | Cross-Slice integration verification + UAT satisfied |
| `state.stage.abandoned` | Explicit abandon command | `*` → `abandoned` | Cascade: child Slices abandoned; dependent Stages → blocked (D-13) |
| `state.stage.updated` | Agent edits STAGE.md frontmatter | — (no state change) | Frontmatter or scope update, does not change state |

### Event Name Migration

| Pre-Rename (existing code) | Post-Rename (v40 design) | Notes |
|---|---|---|
| `state.phase.planned` | `state.stage.planned` | Renamed aggregate: `phase` → `stage` |
| `state.phase.started` | `state.stage.started` | Renamed aggregate |
| `state.phase.verified` | `state.stage.verified` | Renamed aggregate |
| `state.phase.completed` | `state.stage.completed` | Renamed aggregate |
| `PhasePlannedData` | `StagePlannedData` | Class rename (v41+) |
| `PhaseStartedData` | `StageStartedData` | Class rename (v41+) |
| `PhaseVerifiedData` | `StageVerifiedData` | Class rename (v41+) |
| `PhaseCompletedData` | `StageCompletedData` | Class rename (v41+) |
| `phase_number` (field) | `stage_number` | Field rename |
| `phase_id` (field in Slice) | `stage_id` | Field rename |
| `PHASE.md` (artifact) | `STAGE.md` | Artifact file rename |

Existing `src/state_core/schema.py` code uses `PHASE_EVENT_TYPES` with `state.phase.*` literals. Migration to `state.stage.*` is a design contract documented here but implemented in v41+.

## Cross-Tier Relationships

- **Parent of:** Slices (one Stage contains many Slices). The Stage tracks child Slice states and triggers the `slices_shipped` event when all Slices are `shipped`.
- **Sibling of:** Other Stages within the SAME Arc — dependencies via `depends_on` frontmatter field with edge types per D-12. Same-parent-only constraint (D-10): Stages can only depend on sibling Stages in the same Arc.
- **Child of:** ONE Arc (parent). Every Stage belongs to exactly one Arc, identified by `arc_id` in frontmatter.
- **ID format:** `stage-{n}` (D-01). Example: `stage-22`
- **Slug format:** `stage-{n}-{slug}` (D-02). Example: `stage-22-oauth-migration/`
- **Aggregate ID (internal):** `arc-{n}/stage-{n}` — hierarchical, slash-delimited. Example: `arc-45/stage-22`
- **Directory path:** `.state/build/arcs/arc-{n}/stages/stage-{n}/` containing CRIT.md, MAP.md, STAGE.md, STATE.md, and `slices/` subdirectory
