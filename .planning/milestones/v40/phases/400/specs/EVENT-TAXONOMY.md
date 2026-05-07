# Event Taxonomy — All Four Tiers

> **Design contract for v41+ runtime event handling.**
> Consumed by: Plan 400-03 (DESC-SEMANTICS.md references these events). Phase 401 (REF-02 edge type handlers). v41+ scheduler and projector event handler implementation.

## Design Conventions

- Every event has the format `state.{tier}.{action}` — tier prefix identifies the aggregate, action describes what happened.
- Events are **immutable** — they are appended to the event store and never modified (event-sourced architecture).
- Events carry **deterministic data fields** — no `datetime.now()`, no randomness, no mutable external state (replay must be bit-identical).
- The event type string is the canonical identifier. Event data payloads are validated by pydantic models with `extra="forbid"` (schema contract in FRONTMATTER-SCHEMAS.md).
- Per D-19, composite events are separate `append()` operations — no nested transactions.
- Mode isolation: All events in this taxonomy are **build-mode only** (`BUILD_ONLY_EVENT_PREFIXES`).
- Migration: Event types marked with **RENAMED** or **NEW** reference the v41+ migration path from existing `src/state_core/schema.py` code.

---

## Arc Events

Arc is the root tier — a feature block or project branch containing multiple Stages.
6 events (3 existing in schema.py, 3 new in v40 design).

| Event Type | Trigger | State Transition | Data Fields |
|-----------|---------|------------------|-------------|
| `state.arc.created` | `/state-new arc` | none → `planned` | `title: str`, `goal: str` |
| `state.arc.started` | First child Stage reaches `planned` | `planned` → `in_progress` | (identity only — `aggregate_id: str`) |
| `state.arc.stages_shipped` | Projector detects ALL child Stages are `shipped` | `in_progress` → `auditing` | `shipped_stage_ids: list[str]` |
| `state.arc.shipped` | Manual `/state-ship-arc` command | `auditing` → `shipped` | `reason: str` |
| `state.arc.unshipped` | Audit failure detected | `auditing` → `in_progress` | `failure_reasons: list[str]` |
| `state.arc.abandoned` | Explicit abandon command | `*` → `abandoned` | `reason: str` |
| `state.arc.updated` | Agent edits ARC.md frontmatter | — (no state change) | `updated_fields: list[str]` |

**Migration notes from existing code (`src/state_core/schema.py`):**
- `state.arc.retired` (existing) → replaced by `state.arc.shipped` (terminal success) and `state.arc.abandoned` (terminal failure). More specific terminal events.
- `state.arc.started` (NEW) — no equivalent in existing code; Arc currently has no `in_progress` state.
- `state.arc.stages_shipped` (NEW) — composite event for D-18 auditing entry guard.
- `state.arc.unshipped` (NEW) — explicit audit-failure return path to `in_progress`.

---

## Stage Events

Stage (formerly Phase, renamed per D-01) groups related Slices and tracks cross-Slice verification.
7 events (4 existing as `state.phase.*` in schema.py, migrated and extended in v40 design).

| Event Type | Trigger | State Transition | Data Fields |
|-----------|---------|------------------|-------------|
| `state.stage.created` | `/state-new stage` | none → `planned` | `title: str`, `goal: str`, `arc_id: str` |
| `state.stage.started` | First child Slice reaches `worktree_ready` | `planned` → `in_progress` | (identity only — `aggregate_id: str`) |
| `state.stage.slices_shipped` | Projector detects ALL child Slices are `shipped` | `in_progress` → `verified` | `shipped_slice_ids: list[str]` |
| `state.stage.completed` | Manual verify-stage command passes | `verified` → `shipped` | `verification_summary: str` |
| `state.stage.verification_failed` | Verification failure detected | `verified` → `in_progress` | `failure_reasons: list[str]` |
| `state.stage.abandoned` | Explicit abandon command | `*` → `abandoned` | `reason: str` |
| `state.stage.updated` | Agent edits STAGE.md frontmatter | — (no state change) | `updated_fields: list[str]` |

**Migration notes from existing code (`src/state_core/schema.py`):**
- `state.phase.planned` → `state.stage.created` (Stage enters `planned` state on creation; "planned" is initial state, not trigger event)
- `state.phase.started` → `state.stage.started` (rename aggregate: `phase` → `stage`)
- `state.phase.verified` → split into `state.stage.slices_shipped` (enters `verified` state) + `state.stage.completed` (transitions to `shipped`)
- `state.phase.completed` → `state.stage.completed` (rename aggregate; triggers `verified` → `shipped` transition)
- `state.stage.verification_failed` (NEW) — explicit return path from `verified` to `in_progress`

---

## Slice Events

Slice is the terminal container tier — the finest-grained scheduler-dispatched unit.
11 events (4 existing in schema.py, extended in v40 design).

| Event Type | Trigger | State Transition | Data Fields |
|-----------|---------|------------------|-------------|
| `state.slice.created` | `/state-new slice` | none → `planned` | `title: str`, `goal: str`, `stage_id: str` |
| `state.slice.worktree_ready` | Worktree bootstrap completes | `planned` → `worktree_ready` | `worktree_dir: str`, `worktree_branch: str` |
| `state.slice.started` | Agent begins work on first Step | `worktree_ready` → `in_progress` | (identity only — `aggregate_id: str`) |
| `state.slice.shipped` | ALL Steps are `done` + VERIFICATION.md passes | `in_progress` → `shipped` | `step_ids: list[str]`, `verification_result: str` |
| `state.slice.reverted` | Explicit revert command | `*` → `reverted` | `reason: str`, `snapshot_id: str` |
| `state.slice.replanned` | Re-plan after revert completes | `reverted` → `planned` | (identity only — `aggregate_id: str`) |
| `state.slice.blocked` | Abandon-cascade (D-13) or explicit block | `*` → `blocked` | `blocked_reason: str`, `blocked_by_slice_id: str \| None` |
| `state.slice.unblocked` | Blocking dependency resolved (D-15) | `blocked` → `in_progress` | `resolution: str` |
| `state.slice.deferred` | Manual defer command | `planned` → `deferred` | `deferred_reason: str` |
| `state.slice.undeferred` | Manual un-defer command | `deferred` → `planned` | (identity only — `aggregate_id: str`) |
| `state.slice.updated` | Agent edits SLICE.md frontmatter | — (no state change) | `updated_fields: list[str]` |

**Migration notes from existing code (`src/state_core/schema.py`):**
- `state.slice.planned` → `state.slice.created` (Slice enters `planned` on creation; "planned" is initial state)
- `state.slice.worktree_ready` — unchanged from existing
- `state.slice.shipped` — unchanged from existing (extended data fields)
- `state.slice.reverted` — unchanged from existing
- `state.slice.started` (NEW) — explicit agent-begins-work signal
- `state.slice.replanned` (NEW) — explicit re-plan transition from `reverted`
- `state.slice.blocked`, `state.slice.unblocked` (NEW) — D-13/D-15 block/unblock semantics
- `state.slice.deferred`, `state.slice.undeferred` (NEW) — D-14 deferment semantics

---

## Step Events

Step is the leaf tier — the smallest unit of work, running serially within an agent session.
11 events (10 existing in schema.py, renamed/migrated per D-03).

| Event Type | Trigger | State Transition | Data Fields |
|-----------|---------|------------------|-------------|
| `state.step.created` | Run phase generates Step tracking file | none → `idle` | `step_number: int`, `title: str`, `slice_id: str` |
| `state.step.designed` | Agent completes design for the Step | `idle` → `designing` | `design_approach: str` |
| `state.step.planned` | DESIGN.md completed (or design skipped) | `designing` → `planning` or `idle` → `planning` | `plan_summary: str` |
| `state.step.ran` | PLAN.md completed, agent begins running | `planning` → `running` | `run_output: str` |
| `state.step.verify_started` | All sub-steps complete | `running` → `verifying` | `verification_criteria: list[str]` |
| `state.step.verify_passed` | VERIFICATION.md passes | `verifying` → `done` | `verification_result: str` |
| `state.step.verify_failed` | Verification fails | `verifying` → `running` | `failure_reasons: list[str]` |
| `state.step.advanced` | Composite advancement signal | — (no direct state change) | `new_state: str` |
| `state.step.blocked` | External condition blocks Step | `*` → `blocked` | `blocked_reason: str` |
| `state.step.unblocked` | Blocking condition resolved | `blocked` → `planning` | `resolution: str` |
| `state.step.abandoned` | Explicit abandon command | `*` → `abandoned` | `reason: str` |

**Migration notes from existing code (`src/state_core/schema.py`) — D-03 renames:**
- `state.step.discussed` → `state.step.designed` ("discuss" → "design" per D-03)
- `state.step.planned` — unchanged
- `state.step.executed` → `state.step.ran` ("execute" → "run" per D-03)
- `state.step.verify_started` — unchanged
- `state.step.verify_passed` — unchanged
- `state.step.verify_failed` — unchanged
- `state.step.advanced` — unchanged
- `state.step.blocked` — unchanged
- `state.step.snapshotted` — unchanged (snapshot events not affected by D-03 rename)
- `state.step.reverted` — unchanged (revert events not affected by D-03 rename)
- `state.step.abandoned` (NEW) — explicit terminal exit (replaces gap where Step had no abandon)

---

## Composite Events (Cross-Tier)

Composite events propagate upward through the hierarchy when all children of a parent reach a terminal state. Per D-19, these are separate `append()` operations emitted by the projector, NOT nested transactions.

| Event Type | Trigger Condition | Emitted On | Data Fields |
|-----------|-------------------|------------|-------------|
| `state.slice.steps_completed` | ALL child Steps of parent Slice are `done` | `state.step.verify_passed` (last Step) | `last_step_id: str`, `step_count: int` |
| `state.stage.slices_shipped` | ALL child Slices of parent Stage are `shipped` | `state.slice.shipped` (last Slice) | `shipped_slice_ids: list[str]` |
| `state.arc.stages_shipped` | ALL child Stages of parent Arc are `shipped` | `state.stage.completed` (last Stage) | `shipped_stage_ids: list[str]` |

**Note:** These composite events are ALSO listed in their parent tier's event table above (e.g., `state.stage.slices_shipped` appears in both Stage Events and Composite Events). They serve as both the triggering event for parent state transitions AND the cross-tier cascade signal. The full cascade logic with projector pseudocode is specified in COMPOSITE-CASCADE.md.

---

## Migration Summary

### Phase→Stage Event Migration (4 events, D-01 rename)

| Existing Event (`state.phase.*`) | v40 Design Event (`state.stage.*`) | Notes |
|---|---|---|
| `state.phase.planned` | `state.stage.created` | Aggregate creation (enters `planned` state) |
| `state.phase.started` | `state.stage.started` | Rename aggregate only |
| `state.phase.verified` | `state.stage.slices_shipped` | Split: enters `verified` state |
| `state.phase.completed` | `state.stage.completed` | Split: transitions `verified` → `shipped` |

### Step Event Renames (2 events, D-03)

| Existing Event | v40 Design Event | Notes |
|---|---|---|
| `state.step.discussed` | `state.step.designed` | "discuss" → "design" |
| `state.step.executed` | `state.step.ran` | "execute" → "run" |

**Important:** The existing codebase uses `state.phase.*` and `state.step.discussed/executed`. These are design contracts for v41+ migration. The actual code migration is out of scope for v40. The v40 design documents the target state; v41+ implements the migration with backward-compatible event type aliases during a transition window.

---

## Mode Isolation

All events in this taxonomy are **build-mode only**. Mode isolation is enforced via event prefix filtering:

```python
BUILD_ONLY_EVENT_PREFIXES: frozenset[str] = frozenset({
    "state.arc.",
    "state.stage.",   # post-rename from "state.phase."
    "state.slice.",
    "state.step.",
})
```

The daemon's mode-enforcement middleware validates that an event's type string starts with one of these prefixes before accepting it into a build-mode session. Teach-mode sessions use a separate event taxonomy (not defined in this document). The mode prefix gate is the first line of defense in the 6-layer mode-enforcement stack.

---

## Event Count Summary

| Tier | Events | Composite Events | Total |
|------|--------|-----------------|-------|
| Arc | 6 (+ `updated`) | 0 (root tier) | 7 |
| Stage | 6 (+ `updated`) | 1 (`slices_shipped`) | 7 |
| Slice | 10 (+ `updated`) | 1 (`steps_completed`) | 11 |
| Step | 11 | 0 (leaf tier) | 11 |
| **Total** | **33** (+3 `updated` events) | **2** | **36** |

---

*Design contract for v41+ runtime event handling. All events validated against FSM-TABLES.md transition tables and D-17 state budgets. Consumed by COMPOSITE-CASCADE.md for cross-tier rollup logic.*
