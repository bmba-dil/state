# State Transition Tables — All Four Tiers

> **Design contract for v41+ runtime state machine implementation.**
> Consumed by: Plan 400-03 (DESC-SEMANTICS.md references these tables). Phase 401 (REF-02 edge types reference transitions). v41+ scheduler/projector implementation.

## Design Conventions

- All transition tables use the same four-column format: `| From State | To State | Trigger Event | Guard Condition |`
- `*` in the From column means "any state" — the transition applies regardless of current state.
- Arcs, Stages, and Slices are limitless — there is no cap on their count. The only tier with a count constraint is Step, where the number of Steps per Slice is bounded by the token context limit of a single agent session.
- Composite states (D-19) are projector-computed at query time, NOT explicit machine states. They do NOT appear in these transition tables. The composite state computation is specified in COMPOSITE-CASCADE.md.
- All event type strings use the D-03 renamed terminology: `designing` (not `discussing`), `running` (not `executing`). All tier-event aggregators use `state.stage.*` (not `state.phase.*`) per D-01 rename.
- Guard conditions reference child tier states — the projector validates these at event processing time.

---

## Arc State Transition Table

Arc is the root tier. It defines a feature block or project branch containing multiple Stages.
Arcs are limitless — no cap on the number of Arcs or Stages per Arc.

| From | To | Trigger Event | Guard Condition |
|------|----|---------------|-----------------|
| `planned` | `in_progress` | `state.arc.started` | ≥1 child Stage is `planned` (D-08: Stages can be added mid-flight) |
| `in_progress` | `auditing` | `state.arc.stages_shipped` | ALL child Stages are `shipped` (projector composite check per D-19) |
| `auditing` | `shipped` | `state.arc.shipped` | Manual `/state-ship-arc`; ARC-SUMMARY.md produced; audit passes (D-18) |
| `auditing` | `in_progress` | `state.arc.unshipped` | Audit failed; return to `in_progress` for remediation |
| `*` | `abandoned` | `state.arc.abandoned` | Explicit abandon command. Cascade: child Stages→abandoned; their Slices→blocked (D-13). |
| `in_progress` | `abandoned` | `state.arc.abandoned` | (same as above; explicit listing for clarity) |

**Notes:**
- `auditing` is a discrete machine state (per D-18), NOT a projector-computed composite state. It requires an explicit `state.arc.stages_shipped` trigger and entry guard (all child Stages shipped).
- The Arc can remain in `in_progress` even when all Stages are shipped if the audit has not yet been initiated.
- The `abandoned` cascade is implemented by the projector in v41+: when an Arc is abandoned, all child Stages → `abandoned`, and all Slices that depended on those Stages → `blocked`.

---

## Stage State Transition Table

Stage (formerly Phase, renamed per D-01) groups related Slices and tracks cross-Slice verification.
Stages, like Arcs, have an explicit `auditing` state before shipping. Stages are limitless — no cap on
the number of Stages per Arc or Slices per Stage.

| From | To | Trigger Event | Guard Condition |
|------|----|---------------|-----------------|
| `planned` | `in_progress` | `state.stage.started` | ≥1 child Slice is `worktree_ready` |
| `in_progress` | `verified` | `state.stage.slices_shipped` | ALL child Slices are `shipped` (projector composite check per D-19) |
| `verified` | `auditing` | `state.stage.audited` | Manual audit initiated; cross-Slice integration + UAT verified |
| `auditing` | `shipped` | `state.stage.completed` | Audit passes; STAGE-SUMMARY.md produced |
| `auditing` | `verified` | `state.stage.verification_failed` | Audit failed; return to `verified` for remediation |
| `*` | `abandoned` | `state.stage.abandoned` | Explicit abandon. Cascade: child Slices→blocked; same-Arc dependent Stages→blocked (D-13). |

**Notes:**
- Migration: This tier was formerly called "Phase." Event types `state.phase.*` in existing code (`src/state_core/schema.py`) map to `state.stage.*` in the v40 design. The rename is a design contract for v41+ migration.
- The transition `in_progress → verified` uses `state.stage.slices_shipped` (D-18 guard: all child Slices shipped). This is separate from `state.stage.audited` which transitions `verified → auditing`.
- Like Arcs, Stages require a formal audit (`auditing` state) before shipping.
- Cascading abandon (D-13): When a Stage is abandoned, all child Slices → `abandoned`, and any Slices that depended on those Slices → `blocked`.

---

## Slice State Transition Table

Slice is the terminal container tier — the finest-grained scheduler-dispatched unit. One Slice maps to one worktree.
Slices are limitless — no cap on the number of Slices per Stage. The only constraint is the number of child Steps,
bounded by the context token limit so a Slice can complete end-to-end in one agent session.

| From | To | Trigger Event | Guard Condition |
|------|----|---------------|-----------------|
| `planned` | `worktree_ready` | `state.slice.worktree_ready` | Worktree bootstrap completes; directory created under `.state/build/` |
| `worktree_ready` | `in_progress` | `state.slice.started` | ≥1 child Step is `idle` or `designing` |
| `in_progress` | `shipped` | `state.slice.shipped` | ALL child Steps are `done` (composite). VERIFICATION.md passes. SUMMARY.md produced. |
| `*` | `blocked` | `state.slice.blocked` | `blocked_reason` set in frontmatter. Entry via abandon-cascade (D-13) or external condition. NO timeout (D-15). |
| `blocked` | `in_progress` | `state.slice.unblocked` | Blocking dependency resolved or deferred (D-14). Scheduler polls dep states on each event. |
| `*` | `reverted` | `state.slice.reverted` | Explicit revert command. Worktree destroyed; snapshot restored. |
| `reverted` | `planned` | `state.slice.replanned` | Re-plan after revert; new worktree created. |
| `planned` | `deferred` | `state.slice.deferred` | `deferred_reason` set (D-14). Dependents treat as soft-done with `deferred_dep` flag. |
| `deferred` | `planned` | `state.slice.undeferred` | Manual un-defer; re-enters planning. |

**Notes:**
- The Slice is the only tier with `worktree_ready` — it owns the git worktree lifecycle.

---

## Step State Transition Table

Step is the leaf tier — the smallest unit of work. Steps are markdown FILES (NOT directories) within the parent Slice folder (D-04). Steps are NOT scheduler-dispatched (D-11); they run serially within one agent session.
The number of Steps per Slice is bounded by the context token limit — a Slice contains only as many Steps
as can fully execute end-to-end within one agent session.

| From | To | Trigger Event | Guard Condition |
|------|----|---------------|-----------------|
| `idle` | `designing` | `state.step.designed` | Step created; agent invokes design phase |
| `designing` | `planning` | `state.step.planned` | DESIGN.md completed |
| `idle` | `planning` | `state.step.planned` | Design skipped (simple work, no research needed) |
| `planning` | `running` | `state.step.ran` | PLAN.md (or stepNPLAN.md) completed |
| `running` | `verifying` | `state.step.verify_started` | All sub-steps complete; agent initiates verification |
| `verifying` | `done` | `state.step.verify_passed` | VERIFICATION.md all checks pass |
| `verifying` | `running` | `state.step.verify_failed` | Verification failed; return to `running` for fixes |
| `*` | `blocked` | `state.step.blocked` | `blocked_reason` set. NO timeout (D-15). |
| `blocked` | `planning` | `state.step.unblocked` | Blocking condition resolved; return to `planning` |
| `*` | `abandoned` | `state.step.abandoned` | Explicit abandon. No cascade to sibling Steps. |
| `idle` | `blocked` | `state.step.blocked` | Created with unresolved dependency |

**Notes:**
- State names use D-03 renamed terminology: `designing` (not `discussing`), `running` (not `executing`).
- Design skip path: Steps for simple work can skip `designing` via `idle → planning` direct transition. This is an agent decision.
- Verify loop: `verifying → running` enables iterative fix-and-verify cycles. The loop can repeat until verification passes.
- `blocked → planning`: When unblocked, the Step returns to `planning` (not `running`) because the agent needs to re-establish execution context.
- Steps are FILES (`step1PLAN.md`), NOT directories (D-04). The Slice folder is the terminal container.
- Steps do NOT have a `depends_on` field — intra-Slice ordering is the agent's responsibility (D-11).
- The `state.step.advanced` event is a composite advancement signal — notifies the scheduler of progress for D-19 composite computation but does not change Step state directly.

---

## Tier Count Rules

Tier counts (number of Arcs, Stages per Arc, Slices per Stage) are **limitless** — there is no cap.
Each tier's scope is defined by its parent's planning artifacts:

| Tier | Count Rule | Governed By |
|------|-----------|-------------|
| Arc | Limitless — defined by project scope | Project-level decisions |
| Stage | Limitless — defined by parent Arc's CRIT.md | Arc planning |
| Slice | Limitless — defined by parent Stage's CRIT.md | Stage planning |
| Step | Bounded — ≤N per Slice, where N fills the context token limit of one agent session | Slice planning (context budget) |

**Step count constraint:** The only numerical constraint in the system is Steps per Slice.
When a Stage plans its Slices, each Slice is scoped to contain only as many Steps as can
complete end-to-end within the available token context of a single agent session. This
means a Stage with broad CRIT.md scope naturally produces many Slices, each scoped to fit
the context window.

The Step internal state machine has 8 states (6 forward + 2 exit) — this is a design
property of the machine itself, not a system-wide budget.

---

## D-19: Composite State Disclaimer

Composite states are projector-computed from child states at query time, NOT explicit machine states.
They do NOT appear in these transition tables. The composite state computation specification lives in COMPOSITE-CASCADE.md.

**Examples of composite states (NOT in these tables):**
- Stage "in_progress" = any child Slice has status ∈ {`worktree_ready`, `in_progress`}
- Stage "verified" = all child Slices are `shipped` AND Stage itself is verified
- Arc "in_progress" = any child Stage has status ∈ {`in_progress`, `verified`}
- Arc "auditing" = all child Stages are `shipped` (triggers transition into explicit `auditing` state)
- Arc "shipped" = all child Stages are `shipped` AND Arc itself is shipped

The projector recomputes these on every event, ensuring they never drift from the authoritative event stream.

---

## Cross-Tier Dependency Summary

| Parent Tier | Child Tier | Composite Event | Check Condition | Cascade Behavior |
|-------------|-----------|-----------------|-----------------|------------------|
| Arc | Stage | `state.arc.stages_shipped` | ALL Stages `shipped` | None upward (root tier) |
| Stage | Slice | `state.stage.slices_shipped` | ALL Slices `shipped` | Abandon cascade: child Slices→abandoned, dependents→blocked (D-13) |
| Slice | Step | `state.slice.steps_completed` | ALL Steps `done` | Abandon cascade: Steps in idle→blocked (D-13) |
| Step | — | (leaf tier, no children) | — | No cascade downward (leaf) |

**D-12 Edge types** used in `depends_on` frontmatter field:
- `blocks` — hard prerequisite; dependent cannot proceed until blocker is `shipped`
- `soft` — advisory ordering; dependent can proceed but scheduler prioritizes ordering
- `data` — artifact-producing; hard prerequisite + artifact copy from blocker to dependent

---

*Design contract for v41+ runtime state machine and scheduler implementation. All state transitions validated against D-18/D-19 composite state rules.*
