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

*Design contract for v41+ runtime event handling. All events validated against FSM-TABLES.md transition tables. Consumed by COMPOSITE-CASCADE.md for cross-tier rollup logic.*

---

## v41 Amendment

**Amended:** Phase 402 (v41 milestone — Slice-Cycle & Context Window Spec)
**Cause:** SLC-07 — Slice-owns-cycle correction; v40 cycle-ownership ambiguity is resolved canonically in v41.
**Canonical successor:** [`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md)

### Prior model (v40)

EVENT-TAXONOMY.md (v40) catalogued 33 events across Arc/Stage/Slice/Step tiers and 2 composite events. Slice events covered FSM transitions (`created`, `worktree_ready`, `started`, `shipped`, `reverted`, `replanned`, `blocked`, `unblocked`, `deferred`, `undeferred`, `updated`) but NOT stage-boundary events for the four Slice stages because cycle ownership was implicit.

### Canonical model (v41)

Four NEW stage-boundary events are added at the Slice tier — one per stage of the four-stage Slice cycle defined in [`SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md):

| Event Type                          | Trigger                                                | Aggregate | Data Fields                                                                                                          |
|-------------------------------------|--------------------------------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------|
| state.slice.design_completed        | design-slice produces DESIGN.md + DECISIONS.md         | slice     | slice_id: str, stage: Literal["design"], produced_artifacts: list[str], completed_at: datetime                       |
| state.slice.research_completed      | research-slice's four sub-stages all produce artifacts | slice     | slice_id: str, stage: Literal["research"], produced_artifacts: list[str], completed_at: datetime                     |
| state.slice.run_completed           | run-slice writes all stepNSUMMARY.md files             | slice     | slice_id: str, stage: Literal["run"], produced_artifacts: list[str], completed_at: datetime                          |
| state.slice.verify_completed        | verify-slice writes N-VERIFICATION.md                  | slice     | slice_id: str, stage: Literal["verify"], produced_artifacts: list[str], completed_at: datetime                       |

Plus two events added for cross-session compaction lineage:

| Event Type                          | Trigger                                       | Aggregate | Data Fields                                                                                                          |
|-------------------------------------|-----------------------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------|
| compaction.snapshot_taken           | Threshold/overflow/manual compaction fires    | session   | (see CONTEXT-PROTOCOL.md §8 — full CompactionSnapshot Pydantic shape)                                                |
| compaction.reinject_completed       | Daemon's `chat.params` ack on new session     | session   | (see CONTEXT-PROTOCOL.md §10 — full CompactionReinjectCompleted Pydantic shape)                                       |

### Effect on this document

Event count rises from 33 to 39 (+4 stage-boundary, +2 compaction lifecycle). The `BUILD_ONLY_EVENT_PREFIXES` frozenset gains `"compaction."` per the new compaction events. Mode-isolation rules unchanged — all new events are build-mode only. Full schema for the compaction events is owned by [`CONTEXT-PROTOCOL.md`](../../../v41/phases/402/specs/CONTEXT-PROTOCOL.md) §8 + §10.

### Mode isolation

All v41-introduced events remain build-mode only (`state.slice.*`, `compaction.*` prefixes). Teach-mode harness is v47 scope.

*Original v40 spec text above this amendment block is untouched. This amendment is a published correction, appended per Phase 402 convention (no in-line strikethroughs).*

---

## v41 Amendment — Step-Tier Event Family Extension

> **Source phase:** v41 Phase 403 (Step/Task Decomposition & Plan-as-Prompt)
> **Amendment date:** 2026-05-11
> **Amendment type:** Additive — new event types added to the step tier; v40 baseline events unchanged.
> **Forward-pointer:** Full Pydantic schemas + replay rules in `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`.

### v40 baseline scope

The original v40 EVENT-TAXONOMY.md covered Arc, Stage, Slice, and Step events at the FSM-transition layer (e.g., `state.step.created`, `state.step.completed`). The Phase 402 amendment added four Slice stage-boundary events and two compaction-lifecycle events. v41 Phase 403 extends the step tier with NINE new events for plan-authoring, plan-mutation, autonomy-tiered checkpoint resolution, and replan diff-replay continuity. None of these v41 additions change v40 baseline event semantics or names.

### v41 extension scope (9 new state.step.* events)

| Event Type | Trigger | State Transition | Owning REQ |
|-----------|---------|------------------|------------|
| `state.step.plan_authored` | research-slice end (planner-validation passes) | (none — append-only audit record) | PAP-06 |
| `state.step.plan_edit` | every successful edit to `stepNPLAN.md` | (none — append-only audit record) | PAP-04 |
| `state.step.plan_edit_blocked` | `tool.execute.before` rejects an edit to a locked section | (none — append-only audit record; edit did NOT land on disk) | PAP-05 |
| `state.step.checkpoint_auto_resolved` | autonomy-tiered auto-approval of `checkpoint:human-verify` or auto-pick of `checkpoint:decision` first option | task: `pending` → `resolved` | STP-05 |
| `state.step.checkpoint_human_action_pending` | `checkpoint:human-action` task entered (all tiers stop) | task: `running` → `pending_human` | STP-05 |
| `state.step.checkpoint_human_action_resolved` | human confirms completion via opencode `question` tool | task: `pending_human` → `resolved` | STP-05 |
| `state.step.renamed` | replan determines step_id changed (input change forced rename per stable-hash rule) | step: identity-rebound | STP-06 |
| `state.step.added` | replan creates a new Step | (new aggregate) | STP-06 |
| `state.step.removed` | replan eliminates an authored Step (merged or scope-reduction) | step: `*` → `removed_by_replan` | STP-06 |

All v41 additions follow v40 conventions:
- Naming: `state.{tier}.{action}` form preserved.
- Envelope: ride `EventEnvelope` outer shape.
- Validation: `model_config = ConfigDict(extra="forbid")` on every payload.
- Append-only: event store rows never UPDATED/DELETED; corrections are NEW events.
- Mode prefix: `BUILD_ONLY_EVENT_PREFIXES` (Build-only).

### v14 implementation pointer

v14 Build Kernel implements:
- Pydantic payload models (per STEP-EVENTS.md schemas).
- Daemon emitters (one row per harness action).
- Projector replay-verifier (PlanEdit hash chain integrity check; see STEP-EVENTS.md §Field-Level Constraints — Replay-time integrity check).
- Projection-state reducers (per-Step in-memory state updated from event stream).

See `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` for full schemas and replay rules.

*Original v40 spec text and Phase 402 amendment above this block are untouched. This amendment is purely additive, appended per Phase 402 convention (no in-line strikethroughs).*

---

## v41 Amendment — Phase 404 Discipline-Guard Event Family

> **Source phase:** v41 Phase 404 (Boolean Proof Gate & Discipline Guards)
> **Amendment date:** 2026-05-11
> **Amendment type:** Additive — new event types added to the step + slice tiers; v40 baseline events + Phase 402 amendment + Phase 403 amendment unchanged.
> **Forward-pointers:**
>   - Gate events: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md`
>   - Paralysis event: `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md`
>   - Scope + split events: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md`

### v40 + Phase 402 + Phase 403 baseline scope

The original v40 EVENT-TAXONOMY.md catalogued 33 events across Arc / Stage / Slice / Step tiers and 2 composite events. The Phase 402 amendment added four Slice stage-boundary events (`state.slice.{design,research,run,verify}_completed`) and two compaction-lifecycle events (`compaction.snapshot_taken`, `compaction.reinject_completed`). The Phase 403 amendment added nine `state.step.*` events for plan-authoring, plan-mutation, autonomy-tiered checkpoint resolution, and replan diff-replay continuity. Phase 404 extends the taxonomy with TEN new events for the boolean proof gate, the analysis-paralysis guard, and the scope-reduction-prohibition discipline guards. None of these v41 additions change v40 baseline event semantics or names.

### v41 extension scope (10 new state.{step,slice}.* events)

| Event Type | Trigger | State Transition | Owning REQ | Owning Spec |
|-----------|---------|------------------|------------|-------------|
| `state.step.gate_strike` | Pure-machine evaluator returns `fail` at the completion-claim boundary (Write/Edit to next-task file OR `complete_task` MCP call); strike counter increments for the (task_id, check_id) tuple | (none — append-only audit record; the strike-counter in-memory state transitions on emission) | PRF-06 | PROOF-GATE.md §6 |
| `state.step.gate_resolved` | (task_id, check_id) chain closes — verdict transitions to pass/flag/omitted, OR human resolution at strike 6 | (none — append-only audit record; closes the strike-chain in the in-memory counter) | PRF-06 | PROOF-GATE.md §7 |
| `state.step.step_verify_completed` | Step-end after `stepN-VERIFY.json` is written; carries the path + server-side recomputed overall_verdict | step: `verifying` → `verified` (or `verify_failed` on fail verdict) | PRF-05 | PROOF-GATE.md §7 |
| `state.slice.slice_verify_completed` | Slice-end after `slice-verification.sh` exits 0 AND `N-VERIFICATION.md` is written by the deterministic projector | slice: `verifying` → `verified` | PRF-05 | PROOF-GATE.md §7 |
| `state.step.paralysis_event` | Per-task consecutive-read-only counter crosses threshold; emits at advisory 1, 2, 3+reinject, 4, 5, 6+human-gate | (none — append-only audit record; the paralysis-counter in-memory state transitions on emission) | APG-06 | ANALYSIS-PARALYSIS-GUARD.md §8 |
| `state.step.scope_check` | Prohibited-language scan match on a Write/Edit content; emitted whether or not EXCEPTION_RE resolves | (none — write decision flows from exception_matched + exception_resolved tuple) | SRP-02 | SCOPE-PROHIBITION.md §5 |
| `state.step.scope_deviation` | tool.execute.before Layer 1 rejects a Write/Edit whose target path is not in `files_modified` | (none — append-only audit record; the write was rejected) | SRP-04 | SCOPE-PROHIBITION.md §6 |
| `state.step.scope_deviation_request` | Agent calls `scope_deviation_request` MCP tool requesting a one-shot allowlist entry | (none — append-only audit record; surfaces a `checkpoint:decision`) | SRP-04 | SCOPE-PROHIBITION.md §7 |
| `state.step.scope_deviation_resolved` | Human (or harness_auto under `--full-yolo` per Phase 405 DEV-05) resolves the `checkpoint:decision`; carries resolution: approve \| reject | one-shot allowlist entry written on approve; nothing on reject | SRP-04 | SCOPE-PROHIBITION.md §7 |
| `state.slice.split_recommendation` | Agent calls `request_step_split` MCP tool; harness records the recommendation + takes worktree snapshot + transitions Slice to `pending_replan` | slice: `running` → `pending_replan` (run-slice terminal state) | SRP-05 | SCOPE-PROHIBITION.md §8 |

### Conventions inherited

All v41 Phase 404 additions follow v40 conventions:
- **Naming**: `state.{tier}.{action}` form preserved; tier ∈ {step, slice}; action is snake_case.
- **Envelope**: ride `EventEnvelope` outer shape (per v40 baseline + Phase 402 amendment confirmation).
- **Validation**: `model_config = ConfigDict(extra="forbid")` on every payload (full Pydantic schemas in the owning specs).
- **Append-only**: event store rows never UPDATED/DELETED; corrections are NEW events (e.g., `state.step.gate_resolved` to close a strike chain; `state.step.scope_deviation_resolved` to close a deviation request).
- **Mode prefix**: all 10 new events live in `BUILD_ONLY_EVENT_PREFIXES`; teach-mode harness is v47 scope.
- **Bounded truncation**: `agent_response_summary` / `eval_evidence` / similar excerpt fields are <= 2KB each; 10KB total per event (mirrors PROOF-GATE.md Section 7 §Bounded truncation discipline).

### Counter independence (load-bearing)

Phase 404 introduces TWO independent counters (per `loop-control.md §0 Correction 1` — distinct counters at distinct scopes; conflation forbidden):

- **`gate_strike` chain (PRF)**: per `(task_id, check_id)` tuple. 3 advisory → clear+reinject (single shot) → 3 more → human gate at strike 6. Per failing must_haves check.
- **`paralysis_event` chain (APG)**: per task. 3 advisory → clear+reinject (single shot) → 3 more → human gate at advisory 6. Per consecutive-read-only-tool-uses window.

Each can independently reach force-stop. The Phase 406 `harness_intervention` event (HRN-05) is the umbrella that aggregates both; this amendment confirms the umbrella's expected member set.

### Event count summary

Event count rises from 39 (after Phase 403 amendment) to **49** after Phase 404 amendment: +4 gate events (gate_strike, gate_resolved, step_verify_completed, slice_verify_completed) + 1 paralysis event + 5 scope events (scope_check, scope_deviation, scope_deviation_request, scope_deviation_resolved, split_recommendation). Mode-isolation rules unchanged — all new events Build-only.

### v14 implementation pointer

v14 Build Kernel implements:
- Pydantic payload models per the owning Phase 404 specs (PROOF-GATE.md / ANALYSIS-PARALYSIS-GUARD.md / SCOPE-PROHIBITION.md).
- Daemon emitters at the documented trigger sites (one row per harness action).
- Projector reducers for in-memory counter state (PRF strike chain, APG paralysis chain, scope_deviation one-shot allowlist).
- Bounded-truncation utility shared across PROOF-GATE.md / ANALYSIS-PARALYSIS-GUARD.md / SCOPE-PROHIBITION.md events (2KB per excerpt, 10KB total per event, literal marker `[... truncated <N> bytes ...]`).
- Deterministic projectors for `N-VERIFICATION.md` (PROOF-GATE.md) and `deferred-items.md` (SCOPE-PROHIBITION.md) — both replayable from event store at any time.

See `.planning/milestones/v41/phases/404/specs/{PROOF-GATE,ANALYSIS-PARALYSIS-GUARD,SCOPE-PROHIBITION}.md` for full schemas, behaviors, and cross-references.

*Original v40 spec text, Phase 402 amendment, and Phase 403 amendment above this block are untouched. This amendment is purely additive, appended per Phase 402 convention (no in-line strikethroughs).*

---

## v41 Amendment — Phase 405 Deviation + Subagent Event Family

**Phase:** 405 (Deviation Rules & Subagent Management)
**Status:** Canonical (v41)
**Append-only:** All entries below are NEW; nothing above this header has been edited.
**Build-mode only:** All 14 new event types live in `BUILD_ONLY_EVENT_PREFIXES`. No `state.teach.*` analog exists; teach-mode harness owns its own event family (v47 territory).
**Naming discipline:** All identifiers are `STATE-*` / `state-*`. The four commit trailers (`STATE-Task`, `STATE-DeviationRule`, `STATE-DeviationAttempt`, `STATE-Subagent-Invocation`) are documented in DEVIATION-RULES.md §5.

Phase 405 introduces three sibling spec documents (DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md) which together specify the deviation framework + subagent management subsystem. The following 14 new event types are emitted by the deviation classifier, subagent dispatch handler, and subagent monitoring projector. Full Pydantic payload schemas live in the owning specs; this amendment is a registry index.

### 14 New Event Types

| Event Type | Trigger | State Transition | Owning REQ → Spec |
|---|---|---|---|
| `state.step.deviation_logged` | `log_deviation` MCP call after harness cross-validation succeeds (or on cap-exceeded for audit completeness) | task → deviation chain attempt N | DEV-07 → DEVIATION-RULES.md §9 |
| `state.step.deviation_classification_rejected` | Cross-validation step 1-4 rejects the agent's declared `rule_id` | (no state change; advisory event) | DEV-07 → DEVIATION-RULES.md §4 |
| `state.step.deviation_resolution_recorded` | Append-only mutation event; updates `Deviation.resolution` from `pending` → terminal value | deviation row resolution → terminal | DEV-07 → DEVIATION-RULES.md §9 |
| `state.step.deviation_cap_exceeded` | Cross-validation step 5 detects the 4th attempt on the same `(task_id, rule_id, issue_signature)` tuple | deviation chain → escalation (Rule 4 promotion or `checkpoint:decision`) | DEV-07 → DEVIATION-RULES.md §4 |
| `state.step.subagent_started` | Daemon dispatch handler after opencode `task` tool spawn confirms session creation | parent task → subagent in-flight | SUB-05 → SUBAGENT-MONITORING.md §2 |
| `state.step.subagent_progress` | Every TUI-visible event from child session (message_end, tool_use start/end) | (no state change; observability event) | SUB-05 → SUBAGENT-MONITORING.md §2 |
| `state.step.subagent_complete` | Child session reaches `stop_reason ∈ {end_turn, tool_use, max_tokens, error, aborted}` | subagent in-flight → completed (success or crash; spot-check follows) | SUB-05 → SUBAGENT-MONITORING.md §2 |
| `state.step.subagent_spot_check_failed` | Any layer 1-4 of the 4-layer pure-machine spot-check stack fails | feeds into restart counter chain (not PRF strike chain) | SUB-06 → SUBAGENT-MONITORING.md §4 |
| `state.step.subagent_crash_detected` | Any of 5 crash sources (process_exit / stop_reason / spot_check / sse_silence / parent_task_error) fires | restart counter for `(parent_task_id, subagent_type)` increments | SUB-07 → SUBAGENT-MONITORING.md §5 |
| `state.step.subagent_restart` | Daemon spawns retry with augmented `<prior_crash>` continuation context | new invocation_id; restart_number 1..3 | SUB-07 → SUBAGENT-MONITORING.md §5-6 |
| `state.step.subagent_restart_exhausted` | Restart counter hits 4th occurrence on the same tuple | escalation → parent must call `log_deviation(rule_id=3|4)` | SUB-07 → SUBAGENT-MONITORING.md §5 |
| `state.step.subagent_orphan_detected` | Daemon resume reconciliation cannot resolve an in-flight subagent | persistent orphan → Rule 4 human gate | SUB-08 → SUBAGENT-MONITORING.md §7 |
| `state.step.subagent_whitelist_violation` | `dispatch_subagent` payload references a SubagentType not in the effective whitelist | dispatch rejected at runtime `tool.execute.before` | SUB-03 → SUBAGENT-MANAGEMENT.md §5 |
| `state.slice.subagent_cap_expansion_rejected` | Slice frontmatter `subagent.parallel_cap` exceeds 20 at plan-validation stage | replan iteration triggered | SUB-04 → SUBAGENT-MANAGEMENT.md §6 |

### Naming-convention check

Every event type above matches the regex `^state\.(step|slice)\.[a-z_]+$`. No naming-drift entries. Mode-isolation gate: all entries are `state.{step,slice}.*` (Build-only); no `state.teach.*` references in Phase 405.

### Authoritative-ordering note

Pydantic class definitions in the owning Phase 405 spec docs are authoritative; this amendment is a registry index. When event-payload field-set details diverge between this index and the owning spec, the owning spec wins.

### Cross-reference to umbrella event (Phase 406)

Phase 406's `state.harness.intervention` umbrella event (HRN-05) aggregates Rule-4 escalations from `deviation_logged`, `subagent_spot_check_failed`, `subagent_crash_detected`, and `subagent_orphan_detected`. The umbrella event is owned by Phase 406's HARNESS-ARCHITECTURE.md; this amendment forward-references the rollup.
