# Step-Tier Event Schemas (Canonical, v41)

> **Phase:** 403
> **Status:** Canonical (v41)
> **Requirements covered:** PAP-04, PAP-05, PAP-06 (and supports STP-05 + STP-06)
> **Build-mode only.** All events in this spec go in `BUILD_ONLY_EVENT_PREFIXES` per v40 EVENT-TAXONOMY.md mode-isolation convention.
> **Master taxonomy:** `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (v40 baseline + v41 amendment block forward-pointing here).
> **Sibling specs:** STEP-PLAN-FORMAT.md (artifact format); PLAN-AS-PROMPT.md (injection + mutability + content-stripping mechanics).

Phase 403 introduces 9 new step-tier event types that underpin the Build-mode harness's plan-as-prompt architecture. Three (`plan_authored`, `plan_edit`, `plan_edit_blocked`) form the audit-log and immutability-block backbone for plan-lifecycle tracking. Three (`checkpoint_auto_resolved`, `checkpoint_human_action_pending`, `checkpoint_human_action_resolved`) underpin the autonomy-tiered checkpoint behavior that governs how executor agents interact with human-gated decision points. Three (`renamed`, `added`, `removed`) underpin replan diff-replay continuity — ensuring that when planner-validation re-runs with changed inputs, downstream consumers can reconcile the Step set change without losing replay determinism. Each event follows the v40 `state.{tier}.{action}` naming convention and rides the `EventEnvelope` outer shape defined in the master taxonomy.

---

## Event Family Overview

All nine events introduced in this spec extend the existing `state.step.*` namespace from v40 EVENT-TAXONOMY.md. The v40 taxonomy defined 11 baseline Step events (FSM transitions: `created`, `designed`, `planned`, `ran`, `verify_started`, `verify_passed`, `verify_failed`, `advanced`, `blocked`, `unblocked`, `abandoned`). The nine events below are additive — they do not replace any v40 baseline event and do not alter any v40 FSM state transition.

| Event Type | Pydantic Class | REQ | Aggregate | Section |
|-----------|----------------|-----|-----------|---------|
| `state.step.plan_authored` | `StepPlanAuthored` | PAP-06 | `step_id` | §Plan-Lifecycle |
| `state.step.plan_edit` | `PlanEdit` | PAP-04 | `step_id` | §Plan-Lifecycle |
| `state.step.plan_edit_blocked` | `PlanEditBlocked` | PAP-05 | `step_id` | §Plan-Lifecycle |
| `state.step.checkpoint_auto_resolved` | `CheckpointAutoResolved` | STP-05 | `step_id` | §Checkpoint |
| `state.step.checkpoint_human_action_pending` | `CheckpointHumanActionPending` | STP-05 | `step_id` | §Checkpoint |
| `state.step.checkpoint_human_action_resolved` | `CheckpointHumanActionResolved` | STP-05 | `step_id` | §Checkpoint |
| `state.step.renamed` | `StepRenamed` | STP-06 | `slice_id` | §Replan-Continuity |
| `state.step.added` | `StepAdded` | STP-06 | `slice_id` | §Replan-Continuity |
| `state.step.removed` | `StepRemoved` | STP-06 | `slice_id` | §Replan-Continuity |

Note: Replan-continuity events use `slice_id` as `aggregate_id` because the Slice is the unit of replanning — the replan operation operates on a Slice's full Step set, not individual Steps.

---

## Conventions

- All events have type string `state.step.{action}` per v40 EVENT-TAXONOMY.md.
- All events ride the `EventEnvelope` outer shape (event_id, event_type, aggregate_id=step_id or slice_id, emitted_at, payload).
- All payload Pydantic models have `model_config = ConfigDict(extra="forbid")`.
- All event store rows are **append-only** — no UPDATE/DELETE; corrections are NEW events.
- All `datetime` fields are UTC ISO-8601.
- All `*_sha256` fields are lowercase hex SHA-256.
- Mode prefix: `BUILD_ONLY_EVENT_PREFIXES` includes `state.step.` (Build-only).

### EventEnvelope reference (v40 convention)

The EventEnvelope is the outer shape that wraps every domain event. All nine events defined in this spec ride this envelope.

```python
from pydantic import BaseModel, ConfigDict

class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    event_type: str            # "state.step.{action}"
    aggregate_id: str          # step_id (per-step events) or slice_id (replan events)
    emitted_at: str            # ISO-8601 UTC
    payload: dict              # validated per event_type using one of the schemas below
```

Forward-pointer: full envelope contract lives in `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`.

---

## Plan-Lifecycle Events (PAP-04, PAP-05, PAP-06)

These events form the audit-log and immutability-block backbone of the plan-as-prompt architecture. They were already rendered in PLAN-AS-PROMPT.md sections 6–8 as part of specifying the injection, mutability, and content-stripping mechanics. This section re-renders them here as the canonical event-spec home. PLAN-AS-PROMPT.md cross-references back to this document for the full Pydantic schema definitions. The event type strings and field sets are identical in both documents; if a discrepancy ever appears, STEP-EVENTS.md wins as the canonical home.

### state.step.plan_authored (StepPlanAuthored — PAP-06)

**Trigger:** Emitted at research-slice end (when planner-validation stage passes). Payload is the original verbatim content of `stepNPLAN.md` plus its SHA-256 hash. The event store row is the AUTHORITATIVE audit-log original — the source of truth for replay reconstruction of any edit chain beginning with this Step's plan.

**State transition:** (none — events are append-only; this is an audit record, not an FSM transition).

**Security note:** The `state.step.plan_authored` row is append-only per v40 EVENT-TAXONOMY.md (SQLite rows are never updated or deleted). The `original_sha256` field provides a content integrity check verified by the projector on replay.

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal

class StepPlanAuthored(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    original_content: str              # full file content, verbatim
    original_sha256: str               # SHA-256 of original_content (lowercase hex)
    authored_at: datetime
    authored_by: Literal["plan-slice", "human", "harness"]
    session_id: str
```

### state.step.plan_edit (PlanEdit — PAP-04)

**Trigger:** Emitted on every successful edit to `stepNPLAN.md` (executor, harness, or human). Carries unified diff plus before/after hashes. Replay reconstructs full content by walking the diff chain from the original `state.step.plan_authored` event. The approach is compact, auditable, and replay-deterministic — aligned with the best-effort-diff convention from `workflow-docs-from-gsd-2/file-tracking.md` (Correction 1: per-turn git commit is best-effort, not transactional).

**State transition:** (none — append-only audit record).

```python
class PlanEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    diff: str                          # git-style unified diff
    before_sha256: str                 # full file before edit
    after_sha256: str                  # full file after edit
    editor: Literal["executor", "harness", "human"]
    edited_at: datetime                # UTC, ISO-8601
    session_id: str
    immutable_section_touched: bool    # set by tool.execute.before; True triggers plan_edit_blocked instead
```

### state.step.plan_edit_blocked (PlanEditBlocked — PAP-05)

**Trigger:** Emitted by the diff-the-proposed-write enforcer (`tool.execute.before` hook) when a proposed edit touches a locked section per the Mutability Matrix. Per PLAN-AS-PROMPT.md §7 (Diff-the-Proposed-Write Enforcer): the enforcer intercepts every Write/Edit targeting `*/stepNPLAN.md`, computes the prospective new content, parses both old and new with the StepPlan parser, and compares the immutable subset. Any change to a locked section is rejected with this event.

**State transition:** (none — append-only audit record; the proposed edit did NOT land on disk).

```python
class PlanEditBlocked(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    proposed_diff: str
    locked_section: str                # e.g., "frontmatter.must_haves.truths" or "<acceptance_criteria>"
    blocked_at: datetime
    session_id: str
    proposed_by: Literal["executor", "harness", "human"]
```

### Replay-time integrity check

On replay, the projector verifies for every `state.step.plan_edit` event:

1. `before_sha256` matches the SHA-256 of the on-disk content prior to applying `diff` (or, on cold replay starting from `state.step.plan_authored`, matches the original content hash).
2. `after_sha256` matches the SHA-256 after applying `diff`.
3. On hash mismatch, the projector REJECTS the event (logs error, does not advance the projection state). Mismatched-hash events surface as a daemon-startup error gating the harness from spawning new sessions until reconciled.

Cross-reference: PLAN-AS-PROMPT.md §6 (Replay verification subsection) is the authoritative source for this rule. The pseudocode for the full replay reconstruction algorithm is:

```
content_at_N = plan_authored.original_content
for event in plan_edit_events[0..N]:
    assert sha256(content_at_N) == event.before_sha256      # integrity check
    content_at_N = apply_unified_diff(content_at_N, event.diff)
    assert sha256(content_at_N) == event.after_sha256        # post-apply check
```

Failure at any assertion: the projector raises `PlanEditReplayError` with the event id and hash mismatch detail. The daemon surfaces this via the `GET /health` endpoint as `plan_edit_replay: degraded`.

---

## Checkpoint Events (STP-05)

These events fire when a `<task type="checkpoint:*">` task is gate-resolved — either auto-approved by the harness under a permissive autonomy tier, or confirmed by human action. They support the autonomy-tiered behavior specified in STEP-PLAN-FORMAT.md Section 5, which defines the five task types and their checkpoint semantics. All three checkpoint event types are Build-mode only and ride the `EventEnvelope` outer shape.

### state.step.checkpoint_auto_resolved (CheckpointAutoResolved)

**Trigger:** Emitted when a `checkpoint:human-verify` or `checkpoint:decision` task is auto-resolved by the harness under `--tiered` or `--full-yolo` autonomy. For `human-verify` under tiered/yolo: auto-approves (the harness does not surface a question tool call). For `decision` under yolo: picks first option deterministically from the `<options>` block. See STEP-PLAN-FORMAT.md §5 for the full autonomy tier × task type matrix.

**State transition:** task: `pending` → `resolved`.

```python
class CheckpointAutoResolved(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    task_id: str
    checkpoint_type: Literal["human-verify", "decision"]
    tier: Literal["tiered", "full-yolo"]
    selection: str                     # "auto-approved" | option name from <options>
    resolved_at: datetime
    session_id: str
```

### state.step.checkpoint_human_action_pending (CheckpointHumanActionPending)

**Trigger:** Emitted when a `checkpoint:human-action` task is entered. ALL autonomy tiers stop here — this is the one checkpoint type where the harness cannot auto-resolve regardless of the autonomy setting. The harness surfaces the question via the opencode `question` tool. This event records the entry into the pending-human state so the daemon knows a session is blocked awaiting human input.

**State transition:** task: `running` → `pending_human`.

```python
class CheckpointHumanActionPending(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    task_id: str
    action_prompt: str                 # rendered question text
    pending_at: datetime
    session_id: str
```

### state.step.checkpoint_human_action_resolved (CheckpointHumanActionResolved)

**Trigger:** Emitted when a `checkpoint:human-action` task is resumed by human confirmation — i.e., the human provides their response via the opencode `question` tool reply. The harness emits this event before resuming task execution so the event log captures both the entry (`pending`) and the exit (`resolved`) of the human-gate.

**State transition:** task: `pending_human` → `resolved`.

```python
class CheckpointHumanActionResolved(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    task_id: str
    confirmation: str                  # human's response text from question tool
    resolved_at: datetime
    session_id: str
```

---

## Replan-Continuity Events (STP-06)

When planner-validation re-runs (a replan iteration) with changed inputs, the granularity algorithm may produce a different Step set than the prior run. This happens when scope expands (more Steps needed), scope shrinks (fewer Steps needed), or renamed inputs produce different step_id hashes under the stable-hash rule. Diff-replay continuity events let downstream consumers — Phase 404 Boolean Proof Gates, the v5 DAG scheduler, and the projector — reconcile the change without losing replay determinism. All three replan-continuity events use `slice_id` as their `aggregate_id` (the Slice is the unit of replanning).

### state.step.renamed (StepRenamed)

**Trigger:** Emitted when replan determines the step_id changed for an authored Step. The input change forced a rename per STEP-PLAN-FORMAT.md §8 stable-hash rule: when planner inputs change, the hash-derived step_id for a logically-equivalent Step may differ. The StepRenamed event binds the old and new step_ids so the projector can update its index without losing the event history for the logical Step.

**State transition:** step: identity-rebound; new step_id inherits authored content but `must_haves` are re-authored fresh (no carry-over of stale gates).

```python
class StepRenamed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slice_id: str
    old_step_id: str
    new_step_id: str
    renamed_at: datetime
    replan_event_id: str               # links to the parent state.slice.replanned event
```

### state.step.added (StepAdded)

**Trigger:** Emitted when replan creates a new Step that did not exist in the prior plan. This happens when the granularity algorithm upgrades the bucket — for example, if scope_tokens grows above the `coarse → standard` threshold (scope_tokens > 30_000 or files > 3), the planner may decompose a coarse=1 Step into two standard-granularity Steps, emitting StepAdded for the second one.

**State transition:** (new aggregate — the Step did not exist before this replan iteration).

```python
class StepAdded(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slice_id: str
    step_id: str
    added_at: datetime
    replan_event_id: str
```

### state.step.removed (StepRemoved)

**Trigger:** Emitted when replan eliminates an authored Step that existed in the prior plan. This happens when scope shrinks — for example, when the granularity algorithm downgrades the bucket (e.g., scope_tokens drops below threshold allowing merger into one Step from two), or when a Step's content is absorbed into a sibling Step during replan.

**State transition:** step: `*` → `removed_by_replan`.

```python
class StepRemoved(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slice_id: str
    step_id: str
    removed_at: datetime
    replan_event_id: str
    reason: Literal["merged", "scope_reduction", "other"]
```

### Lock survival across replan

Per STEP-PLAN-FORMAT.md §8 (Replan determinism subsection): when step_id is **unchanged** across replan, locks held by PAP-03 (`must_haves`, `<verify>`) survive. When step_id **changes** (StepRenamed event fires), the new Step inherits authored content but `must_haves` are re-authored fresh (no carry-over of stale gates). Steps that disappear entirely (StepRemoved) lose all locks; Steps that appear fresh (StepAdded) start with no locks — `must_haves` must be authored in the new plan.

The `replan_event_id` field on all three continuity events links back to the parent `state.slice.replanned` event (see EVENT-TAXONOMY.md Slice Events table), giving the projector a complete replan lineage: Slice replanned → set of Step{Renamed,Added,Removed} events → new Step plan_authored events (for new/renamed Steps).

---

## Cross-references + Closing

The nine step-tier events defined in this spec connect to the following sibling specs and downstream consumers:

- **Master event taxonomy:** `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — the v40 baseline; receives a `## v41 Amendment — Step-Tier Event Family Extension` block via Plan 04 Task 2 listing all 9 events with forward-pointers here. v40's naming convention (`state.{tier}.{action}`) and the `EventEnvelope` outer shape are inherited by all 9 events in this spec.
- **Sibling spec — format:** `STEP-PLAN-FORMAT.md` references `state.step.renamed` / `state.step.added` / `state.step.removed` in §8 (Replan Determinism) and `state.step.checkpoint_*` events in §5 (Task Type Behaviors). The format spec defines WHEN events fire in the context of the Step lifecycle; this spec defines the event payloads.
- **Sibling spec — injection + mutability:** `PLAN-AS-PROMPT.md` already renders PlanEdit / PlanEditBlocked / StepPlanAuthored in §§6–8 of that doc (PAP-04, PAP-05, PAP-06 respectively); STEP-EVENTS.md is the canonical event-spec home with the same shapes. PLAN-AS-PROMPT.md cross-references back to this document for the authoritative field definitions.
- **v14 implementation hooks:** v14 Build Kernel implements (a) the projector replay-verifier (hash check on every PlanEdit event — see §3 Replay-time integrity check), (b) the daemon emitter for each event type (one `state.step.*` row per harness action), (c) the projection-state reducer that consumes these events to update the per-Step in-memory state.
- **Phase 404 (Boolean Proof Gate)** consumes `state.step.plan_edit_blocked` indirectly — the gate fails when an immutable `<verify>` block is touched (locked_section = `<verify>` triggers the Boolean Proof Gate error mode).
- **Phase 405 (Subagent Management)** consumes `state.step.checkpoint_*` events for autonomy-inheritance verification — the CheckpointAutoResolved event carries the `tier` field that Phase 405 uses to verify the correct autonomy tier was applied for the given checkpoint type.
- **Phase 406 (Harness Architecture Rollup)** the layered diagram + sequence diagram cite all 9 events; the event-replay reconstruction proof (HRN-07) lists them as "must replay to rebuild harness state."

Build-mode only. All schemas extend `state_core.schema.EventEnvelope` per v40 convention. v14 Build Kernel ships the Pydantic models as part of the `state_core.events.step` module. v15 Build Core Commands wires emitters into the research-slice pipeline (for `state.step.plan_authored`) and the execute-slice harness (for all eight remaining event types).

---

## Field-Level Constraints and Validation Rules

This section specifies field-level constraints for every Pydantic model in this spec. These are normative requirements for v14 implementation. The constraints supplement the Pydantic `extra="forbid"` enforcement.

### StepPlanAuthored field constraints

| Field | Type | Constraint |
|-------|------|-----------|
| `step_id` | `str` | Non-empty; slug form matching the Step's `step` frontmatter field |
| `slice_id` | `str` | Non-empty; slug form matching the parent Slice's `slice` frontmatter field |
| `original_content` | `str` | Non-empty; verbatim bytes of `stepNPLAN.md` at planner-validation-pass time |
| `original_sha256` | `str` | Exactly 64 lowercase hex chars; MUST equal `sha256(original_content.encode("utf-8")).hexdigest()` |
| `authored_at` | `datetime` | UTC; MUST be timezone-aware; no future timestamps |
| `authored_by` | `Literal[...]` | One of: `"plan-slice"` (automated), `"human"` (manual plan authoring), `"harness"` (programmatic) |
| `session_id` | `str` | Non-empty; the active session id at time of authoring |

**Integrity invariant:** the projector verifies `sha256(original_content.encode("utf-8")).hexdigest() == original_sha256` on every `state.step.plan_authored` row load. Hash mismatch raises `PlanAuthoredIntegrityError` and blocks the Slice from advancing.

### PlanEdit field constraints

| Field | Type | Constraint |
|-------|------|-----------|
| `step_id` | `str` | Non-empty; must match an extant `plan_authored` event's `step_id` |
| `slice_id` | `str` | Non-empty; must match the `plan_authored` event's `slice_id` for this Step |
| `diff` | `str` | Non-empty; valid git-style unified diff format |
| `before_sha256` | `str` | Exactly 64 lowercase hex chars |
| `after_sha256` | `str` | Exactly 64 lowercase hex chars; MUST differ from `before_sha256` |
| `editor` | `Literal[...]` | One of: `"executor"`, `"harness"`, `"human"` |
| `edited_at` | `datetime` | UTC; timezone-aware; no future timestamps |
| `session_id` | `str` | Non-empty |
| `immutable_section_touched` | `bool` | Set by `tool.execute.before`; `True` triggers `plan_edit_blocked` instead of `plan_edit` (mutually exclusive — a single proposed write produces EITHER `plan_edit` OR `plan_edit_blocked`, never both) |

**Ordering invariant:** for a given `step_id`, `plan_edit` events are ordered by `edited_at`. The projector replays them in strictly ascending order. A `plan_edit` with `edited_at` earlier than a prior event's `edited_at` raises `PlanEditOrderingError`.

### PlanEditBlocked field constraints

| Field | Type | Constraint |
|-------|------|-----------|
| `step_id` | `str` | Non-empty |
| `slice_id` | `str` | Non-empty |
| `proposed_diff` | `str` | Non-empty; the diff that was REJECTED (the write did NOT land on disk) |
| `locked_section` | `str` | Non-empty; identifies which locked section was touched (e.g., `"frontmatter.step_id"`, `"<verify>"`, `"must_haves.truths"`) |
| `blocked_at` | `datetime` | UTC; timezone-aware |
| `session_id` | `str` | Non-empty |
| `proposed_by` | `Literal[...]` | One of: `"executor"`, `"harness"`, `"human"` |

### CheckpointAutoResolved field constraints

| Field | Type | Constraint |
|-------|------|-----------|
| `step_id` | `str` | Non-empty |
| `slice_id` | `str` | Non-empty |
| `task_id` | `str` | Non-empty; identifies the `<task type="checkpoint:*">` task within the Step plan |
| `checkpoint_type` | `Literal[...]` | `"human-verify"` or `"decision"` ONLY — `"human-action"` checkpoints NEVER auto-resolve |
| `tier` | `Literal[...]` | `"tiered"` or `"full-yolo"` — identifies the autonomy tier that triggered auto-resolution |
| `selection` | `str` | `"auto-approved"` (for `human-verify`) or option name from `<options>` block (for `decision`) |
| `resolved_at` | `datetime` | UTC; timezone-aware |
| `session_id` | `str` | Non-empty |

### CheckpointHumanActionPending and CheckpointHumanActionResolved field constraints

Both human-action checkpoint events share the same `step_id`, `slice_id`, `task_id`, `session_id` constraints as CheckpointAutoResolved. Additional:

| Field | Event | Type | Constraint |
|-------|-------|------|-----------|
| `action_prompt` | `HumanActionPending` | `str` | Non-empty; the rendered question text surfaced to the human via opencode `question` tool |
| `pending_at` | `HumanActionPending` | `datetime` | UTC; timezone-aware |
| `confirmation` | `HumanActionResolved` | `str` | Non-empty; the human's literal response text from the `question` tool reply |
| `resolved_at` | `HumanActionResolved` | `datetime` | UTC; timezone-aware; MUST be after `pending_at` for the corresponding task |

**Pairing invariant:** every `CheckpointHumanActionPending` event MUST be followed by exactly one `CheckpointHumanActionResolved` event for the same `task_id`. A second `Pending` without an intervening `Resolved` is a projector error.

### Replan-continuity event field constraints

All three continuity events (`StepRenamed`, `StepAdded`, `StepRemoved`) share:

| Field | Type | Constraint |
|-------|------|-----------|
| `slice_id` | `str` | Non-empty; the Slice being replanned |
| `replan_event_id` | `str` | Non-empty; the `event_id` of the parent `state.slice.replanned` event |

Additional per-event:

| Field | Event | Constraint |
|-------|-------|-----------|
| `old_step_id` | `StepRenamed` | Non-empty; must match an extant `plan_authored` event's `step_id` |
| `new_step_id` | `StepRenamed` | Non-empty; MUST differ from `old_step_id` |
| `renamed_at` | `StepRenamed` | UTC datetime |
| `step_id` | `StepAdded` | Non-empty; MUST NOT match any extant `plan_authored` event's `step_id` for this Slice |
| `added_at` | `StepAdded` | UTC datetime |
| `step_id` | `StepRemoved` | Non-empty; must match an extant `plan_authored` event's `step_id` for this Slice |
| `removed_at` | `StepRemoved` | UTC datetime |
| `reason` | `StepRemoved` | One of `"merged"`, `"scope_reduction"`, `"other"` |

---

## v14 Implementation Notes

These notes are non-normative. They summarize the v14 Build Kernel implementation tasks that consume this spec. The normative requirements are the Pydantic schemas and field constraints above.

### Module location

All nine Pydantic payload classes live in `src/state_core/events/step.py`. The `EventEnvelope` class lives in `src/state_core/schema.py` (existing file, v40 baseline).

### Daemon emitter registration

The daemon emitter for each event type is registered in `src/state_core/emitters/step.py`. Emitters are called by:

1. The research-slice pipeline at planner-validation-pass → `emit_step_plan_authored(step_id, slice_id, content, session_id)`
2. The `tool.execute.before` hook on every `Write`/`Edit` to `*/stepNPLAN.md`:
   - Allowed edit → `emit_plan_edit(step_id, slice_id, diff, before_sha256, after_sha256, editor, session_id)`
   - Blocked edit → `emit_plan_edit_blocked(step_id, slice_id, proposed_diff, locked_section, proposed_by, session_id)`
3. The execute-slice harness at each checkpoint:
   - Auto-resolved → `emit_checkpoint_auto_resolved(...)`
   - Human-action entered → `emit_checkpoint_human_action_pending(...)`
   - Human-action confirmed → `emit_checkpoint_human_action_resolved(...)`
4. The replan pipeline after `state.slice.replanned` is emitted, one event per Step change:
   - Renamed → `emit_step_renamed(slice_id, old_step_id, new_step_id, replan_event_id)`
   - Added → `emit_step_added(slice_id, step_id, replan_event_id)`
   - Removed → `emit_step_removed(slice_id, step_id, reason, replan_event_id)`

### Projector reducer registration

Each event type has a corresponding reducer in `src/state_core/projectors/step.py`:

- `handle_step_plan_authored` — stores original content + SHA-256 in the `step_plans` projection table.
- `handle_plan_edit` — verifies hash chain (before → apply diff → after), advances `step_plan_current_sha256` projection column.
- `handle_plan_edit_blocked` — logs the blocked attempt; no projection state change (the edit did NOT land).
- `handle_checkpoint_auto_resolved` — advances task status from `pending` → `resolved` in the `step_tasks` projection table.
- `handle_checkpoint_human_action_pending` — advances task status from `running` → `pending_human`.
- `handle_checkpoint_human_action_resolved` — advances task status from `pending_human` → `resolved`.
- `handle_step_renamed` — updates the `step_id` index in the `slice_steps` projection table; no content change.
- `handle_step_added` — inserts a new row into `slice_steps`; status `planned`.
- `handle_step_removed` — marks the row in `slice_steps` as `removed_by_replan`.

### Testing (v14 scope)

Pydantic-roundtrip tests of all nine schemas land with the v14 implementation, NOT in Phase 403 (design-only). EXEMPLAR-stepNPLAN.md is the canonical fixture for the plan-lifecycle events. The projector replay integrity test must simulate a sequence of `plan_authored` + N `plan_edit` events and verify the projector reconstructs the correct content at each step.

---

*Spec: STEP-EVENTS.md — Phase 403 (Step/Task Decomposition & Plan-as-Prompt)*
*Authored: 2026-05-11*
*Requirements: PAP-04, PAP-05, PAP-06 (supports STP-05, STP-06)*
