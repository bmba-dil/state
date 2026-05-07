# State Transition Tables — All Four Tiers

> **Design contract for v41+ runtime state machine implementation.**
> Consumed by: Plan 400-03 (DESC-SEMANTICS.md references these tables). Phase 401 (REF-02 edge types reference transitions). v41+ scheduler/projector implementation.

## Design Conventions

- All transition tables use the same five-column format: `| From State | To State | Trigger Event | Guard Condition | Budget |`
- `*` in the From column means "any state" — the transition applies regardless of current state.
- Budget column shows the per-tier state count constraint (D-17, FSM-06). Exit/alt states (abandoned, blocked, reverted, deferred) are NOT counted in the budget — only the forward progression chain counts. Step is the exception: ≤8 total states (all states counted).
- Composite states (D-19) are projector-computed at query time, NOT explicit machine states. They do NOT appear in these transition tables. The composite state computation is specified in COMPOSITE-CASCADE.md.
- All event type strings use the D-03 renamed terminology: `designing` (not `discussing`), `running` (not `executing`). All tier-event aggregators use `state.stage.*` (not `state.phase.*`) per D-01 rename.
- Guard conditions reference child tier states — the projector validates these at event processing time.

---

## Arc State Transition Table

Arc is the root tier. It defines a feature block or project branch containing multiple Stages.
Forward states: `planned`, `in_progress`, `auditing`, `shipped` = 4 (budget ≤4 ✓).
Exit state: `abandoned` (not counted in budget).

| From | To | Trigger Event | Guard Condition | Budget |
|------|----|---------------|-----------------|--------|
| `planned` | `in_progress` | `state.arc.started` | ≥1 child Stage is `planned` (D-08: Stages can be added mid-flight) | ≤4 ✓ |
| `in_progress` | `auditing` | `state.arc.stages_shipped` | ALL child Stages are `shipped` (projector composite check per D-19) | ≤4 ✓ |
| `auditing` | `shipped` | `state.arc.shipped` | Manual `/state-ship-arc`; ARC-SUMMARY.md produced; audit passes (D-18) | ≤4 ✓ |
| `auditing` | `in_progress` | `state.arc.unshipped` | Audit failed; return to `in_progress` for remediation | ≤4 ✓ |
| `*` | `abandoned` | `state.arc.abandoned` | Explicit abandon command. Cascade: child Stages→abandoned; their Slices→blocked (D-13). | — |
| `in_progress` | `abandoned` | `state.arc.abandoned` | (same as above; explicit listing for clarity) | — |

**Notes:**
- `auditing` is a discrete machine state (per D-18), NOT a projector-computed composite state. It requires an explicit `state.arc.stages_shipped` trigger and entry guard (all child Stages shipped).
- The Arc can remain in `in_progress` even when all Stages are shipped if the audit has not yet been initiated.
- The `abandoned` cascade is implemented by the projector in v41+: when an Arc is abandoned, all child Stages → `abandoned`, and all Slices that depended on those Stages → `blocked`.

---

## Stage State Transition Table

Stage (formerly Phase, renamed per D-01) groups related Slices and tracks cross-Slice verification.
Forward states: `planned`, `in_progress`, `verified`, `shipped` = 4 (budget ≤4 ✓).
Exit state: `abandoned` (not counted in budget).

| From | To | Trigger Event | Guard Condition | Budget |
|------|----|---------------|-----------------|--------|
| `planned` | `in_progress` | `state.stage.started` | ≥1 child Slice is `worktree_ready` | ≤4 ✓ |
| `in_progress` | `verified` | `state.stage.slices_shipped` | ALL child Slices are `shipped` (projector composite check per D-19) | ≤4 ✓ |
| `verified` | `shipped` | `state.stage.completed` | Manual verify-stage command; cross-Slice UAT passes | ≤4 ✓ |
| `verified` | `in_progress` | `state.stage.verification_failed` | Verification failed; return to `in_progress` for remediation | ≤4 ✓ |
| `*` | `abandoned` | `state.stage.abandoned` | Explicit abandon. Cascade: child Slices→blocked; same-Arc dependent Stages→blocked (D-13). | — |

**Notes:**
- Migration: This tier was formerly called "Phase." Event types `state.phase.*` in existing code (`src/state_core/schema.py`) map to `state.stage.*` in the v40 design. The rename is a design contract for v41+ migration.
- The transition `in_progress → verified` uses `state.stage.slices_shipped` (D-18 guard: all child Slices shipped). This is a separate event from `state.stage.completed` which transitions `verified → shipped`.
- Cascading abandon (D-13): When a Stage is abandoned, all child Slices → `abandoned`, and any Slices that depended on those Slices → `blocked`.

---

## Slice State Transition Table

Slice is the terminal container tier — the finest-grained scheduler-dispatched unit. One Slice maps to one worktree.
Forward states: `planned`, `worktree_ready`, `in_progress`, `shipped` = 4 (budget ≤4 ✓).
Exit/alt states: `reverted`, `blocked`, `deferred` (not counted in budget).

| From | To | Trigger Event | Guard Condition | Budget |
|------|----|---------------|-----------------|--------|
| `planned` | `worktree_ready` | `state.slice.worktree_ready` | Worktree bootstrap completes; directory created under `.state/build/` | ≤4 ✓ |
| `worktree_ready` | `in_progress` | `state.slice.started` | ≥1 child Step is `idle` or `designing` | ≤4 ✓ |
| `in_progress` | `shipped` | `state.slice.shipped` | ALL child Steps are `done` (composite). VERIFICATION.md passes. SUMMARY.md produced. | ≤4 ✓ |
| `*` | `blocked` | `state.slice.blocked` | `blocked_reason` set in frontmatter. Entry via abandon-cascade (D-13) or external condition. NO timeout (D-15). | — |
| `blocked` | `in_progress` | `state.slice.unblocked` | Blocking dependency resolved or deferred (D-14). Scheduler polls dep states on each event. | — |
| `*` | `reverted` | `state.slice.reverted` | Explicit revert command. Worktree destroyed; snapshot restored. | — |
| `reverted` | `planned` | `state.slice.replanned` | Re-plan after revert; new worktree created. | — |
| `planned` | `deferred` | `state.slice.deferred` | `deferred_reason` set (D-14). Dependents treat as soft-done with `deferred_dep` flag. | — |
| `deferred` | `planned` | `state.slice.undeferred` | Manual un-defer; re-enters planning. | — |

**Notes:**
- The Slice is the only tier with `worktree_ready` — it owns the git worktree lifecycle.
- `blocked` state has NO timeout (D-15). A Slice stays blocked indefinitely until dependencies resolve or the user defers the blocker.
- `deferred` is soft-done: dependents unblock with `deferred_dep` flag (D-14). The deferred Slice itself can later be `undeferred`.
- `reverted → planned`: The `state.slice.replanned` event triggers worktree recreation. Not the same as `worktree_ready` which is the bootstrap completion event.
- Decimal insertions allowed at Slice level (D-16): `slice-12.1`, `slice-12.354`. No double decimals.

---

## Step State Transition Table

Step is the leaf tier — the smallest unit of work. Steps are markdown FILES (NOT directories) within the parent Slice folder (D-04). Steps are NOT scheduler-dispatched (D-11); they run serially within one agent session.
Forward states: `idle`, `designing`, `planning`, `running`, `verifying`, `done` = 6.
Exit states: `blocked`, `abandoned` = 2. Total: 8 (budget ≤8 ✓).

| From | To | Trigger Event | Guard Condition | Budget |
|------|----|---------------|-----------------|--------|
| `idle` | `designing` | `state.step.designed` | Step created; agent invokes design phase | ≤8 ✓ |
| `designing` | `planning` | `state.step.planned` | DESIGN.md completed | ≤8 ✓ |
| `idle` | `planning` | `state.step.planned` | Design skipped (simple work, no research needed) | ≤8 ✓ |
| `planning` | `running` | `state.step.ran` | PLAN.md (or stepNPLAN.md) completed | ≤8 ✓ |
| `running` | `verifying` | `state.step.verify_started` | All sub-steps complete; agent initiates verification | ≤8 ✓ |
| `verifying` | `done` | `state.step.verify_passed` | VERIFICATION.md all checks pass | ≤8 ✓ |
| `verifying` | `running` | `state.step.verify_failed` | Verification failed; return to `running` for fixes | ≤8 ✓ |
| `*` | `blocked` | `state.step.blocked` | `blocked_reason` set. NO timeout (D-15). | — |
| `blocked` | `planning` | `state.step.unblocked` | Blocking condition resolved; return to `planning` | — |
| `*` | `abandoned` | `state.step.abandoned` | Explicit abandon. No cascade to sibling Steps. | — |
| `idle` | `blocked` | `state.step.blocked` | Created with unresolved dependency | — |

**Notes:**
- State names use D-03 renamed terminology: `designing` (not `discussing`), `running` (not `executing`).
- Design skip path: Steps for simple work can skip `designing` via `idle → planning` direct transition. This is an agent decision.
- Verify loop: `verifying → running` enables iterative fix-and-verify cycles. The loop can repeat until verification passes.
- `blocked → planning`: When unblocked, the Step returns to `planning` (not `running`) because the agent needs to re-establish execution context.
- Steps are FILES (`step1PLAN.md`), NOT directories (D-04). The Slice folder is the terminal container.
- Steps do NOT have a `depends_on` field — intra-Slice ordering is the agent's responsibility (D-11).
- The `state.step.advanced` event is a composite advancement signal — notifies the scheduler of progress for D-19 composite computation but does not change Step state directly.

---

## Budget Enforcement Summary (FSM-06)

Per-tier state count budgets from D-17, with forward/exit classification.

| Tier | Forward States | Exit / Alt States | Total | Budget | Satisfies |
|------|---------------|-------------------|-------|--------|-----------|
| Arc | 4 (`planned`, `in_progress`, `auditing`, `shipped`) | 1 (`abandoned`) | 5 | ≤4 forward | ✓ |
| Stage | 4 (`planned`, `in_progress`, `verified`, `shipped`) | 1 (`abandoned`) | 5 | ≤4 forward | ✓ |
| Slice | 4 (`planned`, `worktree_ready`, `in_progress`, `shipped`) | 3 (`reverted`, `blocked`, `deferred`) | 7 | ≤4 forward | ✓ |
| Step | 6 (`idle`, `designing`, `planning`, `running`, `verifying`, `done`) | 2 (`blocked`, `abandoned`) | 8 | ≤8 total | ✓ |

**Budget rules:**
- **Arc, Stage, Slice:** Only forward progression states count toward the ≤4 budget. Exit/alt states (abandoned, reverted, blocked, deferred) are excluded.
- **Step:** ALL states count toward the ≤8 budget (forward + exit). Step has the most granular lifecycle and thus the largest budget.
- FSM-06 satisfied: All four tiers meet their state count budgets as verified in the transition tables above.

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

*Design contract for v41+ runtime state machine and scheduler implementation. All state transitions validated against D-17 budgets and D-18/D-19 composite state rules.*
