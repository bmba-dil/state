# Tier Specification: Arc

## Role in Hierarchy

Arc is the **coarsest scoping container** in the four-tier product hierarchy. It defines a feature
block or project branch containing multiple Stages. An Arc represents a complete deliverable
(e.g., "Auth System", "Plugin Framework", "Teach-Mode Kernel") and is the only tier that maps
to a GSD milestone. Arcs are flexible — Stages can be added mid-flight while other Stages are
already in progress (D-08). The Arc is the root tier; it has no parent.

Arc is the **only tier with an explicit auditing state** (D-18). Before an Arc can ship, all
child Stages must be shipped, the Arc must pass a cross-Stage audit, and an ARC-SUMMARY.md
must be produced. The ship action is a manual command (`/state-ship-arc`), not automatic.

## State Machine

```
                 ┌─────────────┐
    created      │   planned   │
  ─────────────► │             │
                 └──────┬──────┘
                        │ state.arc.started
                        │ guard: ≥1 child Stage is planned
                        ▼
                 ┌─────────────┐
                 │ in_progress │──────────────────────────────┐
                 │             │                              │
                 └──────┬──────┘                              │
                        │ state.arc.stages_shipped             │
                        │ guard: ALL child Stages are shipped  │
                        ▼                                      │
                 ┌─────────────┐                              │
                 │  auditing   │                              │
                 │             │                              │
                 └──────┬──────┘                              │
                        │ state.arc.shipped                    │ state.arc.abandoned
                        │ guard: audit passes +                │ guard: explicit abandon
                        │ ARC-SUMMARY.md produced              │
                        ▼                                      ▼
                 ┌─────────────┐                      ┌──────────────┐
                 │   shipped   │                      │  abandoned   │
                 │             │                      │              │
                 └─────────────┘                      └──────────────┘

  Forward states (count toward ≤4 budget): planned, in_progress, auditing, shipped = 4
  Exit state (excluded from budget): abandoned = 1

  NOTE: Auditing is a discrete machine state with an entry guard (all child Stages shipped),
  NOT a projector-computed composite state. Composite states (D-19) are computed separately.
```

## State Transition Table

| From | To | Event Trigger | Guard Condition | Budget Check |
|------|----|---------------|-----------------|-------------|
| `planned` | `in_progress` | `state.arc.started` | ≥1 child Stage is `planned` (D-08) | ≤4 ✓ |
| `in_progress` | `auditing` | `state.arc.stages_shipped` | ALL child Stages are `shipped` (D-18, D-19 composite check) | ≤4 ✓ |
| `auditing` | `shipped` | `state.arc.shipped` | Audit passes + ARC-SUMMARY.md produced (manual `/state-ship-arc` command) | ≤4 ✓ |
| `*` | `abandoned` | `state.arc.abandoned` | Explicit abandon command | — |
| `planned` | `abandoned` | `state.arc.abandoned` | Explicit abandon command | — |
| `in_progress` | `abandoned` | `state.arc.abandoned` | Cascade: child Stages → abandoned; dependents → blocked (D-13) | — |
| `auditing` | `abandoned` | `state.arc.abandoned` | Explicit abandon command | — |

**Composite state note (D-19):** The projector computes whether an Arc is "shipped" (all Stages shipped) at query time. The `auditing` state is entered only when that composite condition is true AND an explicit audit is triggered. This means the Arc can remain in `in_progress` even when all Stages are shipped if the audit has not yet been initiated — `auditing` requires an explicit transition trigger.

## Owned Artifacts

| Artifact | Purpose | Schema Owner |
|----------|---------|--------------|
| CRIT.md | Must-have criteria for the Arc (replaces REQUIREMENTS) — defines what "done" means at the Arc level | Agent |
| MAP.md | Arc-level roadmap — maps child Stages, their ordering, and dependency edges | Agent |
| ARC.md | Arc definition document with frontmatter fields (id, title, goal, success_criteria, depends_on) | Agent |
| STATE.md | State projection rebuilt by the projector from event store — current status, Stage counts, timestamps | Projector |

**Artifact creation triggers:**
- CRIT.md, MAP.md, ARC.md — created by agent during Arc planning (`/state-new arc`)
- STATE.md — created and updated by projector on every state change event

## Frontmatter Fields

| Field | Type | Owner | Required | Description |
|-------|------|-------|----------|-------------|
| `id` | `str` | Agent | Yes | Arc identifier: `arc-{n}` — dash-prefix, no leading zeros per D-01. Example: `arc-45` |
| `title` | `str` | Agent | Yes | Human-readable name. Example: "Auth System" |
| `goal` | `str` | Agent | Yes | One-line outcome describing what the Arc delivers |
| `success_criteria` | `list[str]` | Agent | Yes | Measurable outcomes that define Arc completion |
| `depends_on` | `list[dict]` | Agent | No | Dependency edges to sibling Arcs. Format per D-12: `[{id: "arc-02", edge: "blocks"}]`. Edge types: `blocks`, `soft`, `data`. Same-parent-only constraint does not apply to Arc (root tier) — Arcs can depend on any other Arc. Default: `[]` |
| `status` | `Literal["planned", "in_progress", "auditing", "shipped", "abandoned"]` | Projector | Yes | Current state, computed from event stream. Default: `"planned"` |
| `stage_count` | `int` | Projector | No | Number of child Stages. Default: `0` |
| `shipped_stage_count` | `int` | Projector | No | Number of child Stages in `shipped` state. Default: `0` |
| `completed_at` | `str \| None` | Projector | No | ISO 8601 timestamp when Arc reached `shipped`. Default: `null` |

**Field ownership note:** Every field is classified EXACTLY ONCE as Agent or Projector. Agent never writes projector-owned fields (`status`, `stage_count`, `shipped_stage_count`, `completed_at`). Projector never writes agent-owned fields (`id`, `title`, `goal`, `success_criteria`, `depends_on`).

**ID format:** `arc-{n}` — dash-prefix, lowercase prefix, no leading zeros (D-01). Slugs for display: `arc-{n}-{slug}` (D-02). ID resolution works with or without the slug. Example: `arc-45-auth-system/` directory — `arc-45` is the stable ID.

## Events

| Event Type | Trigger | State Transition | Description |
|-----------|---------|------------------|-------------|
| `state.arc.created` | `/state-new arc` | none → `planned` | Arc aggregate created, enters initial state |
| `state.arc.started` | Agent initiates first Stage | `planned` → `in_progress` | At least one child Stage is `planned` |
| `state.arc.stages_shipped` | Projector detects all child Stages `shipped` | `in_progress` → `auditing` | Composite check (D-19): ALL child Stages are `shipped` |
| `state.arc.shipped` | `/state-ship-arc` manual command | `auditing` → `shipped` | Audit passes + ARC-SUMMARY.md produced |
| `state.arc.abandoned` | Explicit abandon command | `*` → `abandoned` | Cascade: child Stages abandoned; dependent Arcs → blocked (D-13) |
| `state.arc.updated` | Agent edits ARC.md frontmatter | — (no state change) | Frontmatter or scope update, does not change state |

**Migration note:** The existing codebase (`src/state_core/schema.py`) defines `state.arc.created`, `state.arc.retired`, and `state.arc.updated`. In the v40 design:
- `state.arc.retired` is replaced by `state.arc.shipped` and `state.arc.abandoned` (more specific terminal transitions)
- `state.arc.started` and `state.arc.stages_shipped` are new events for the expanded state machine

## Cross-Tier Relationships

- **Parent of:** Stages (one Arc contains many Stages)
- **Sibling of:** Other Arcs — dependencies via `depends_on` frontmatter field with edge types per D-12. Arcs are the root tier; cross-Arc dependency rules are less constrained than same-parent-only (D-10) which applies to child tiers.
- **Child of:** None — Arc is the root tier. No parent container.
- **ID format:** `arc-{n}` (D-01). Example: `arc-45`
- **Slug format:** `arc-{n}-{slug}` (D-02). Example: `arc-45-auth-system/`
- **Aggregate ID (internal):** `arc-{n}` — flat, no hierarchical prefix (root tier)
- **Directory path:** `.state/build/arcs/arc-{n}/` containing CRIT.md, MAP.md, ARC.md, STATE.md, and `stages/` subdirectory
