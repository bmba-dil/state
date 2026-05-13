---
phase: 403
plan: 04
type: execute
wave: 3
depends_on:
  - 02
  - 03
files_modified:
  - .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
  - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
autonomous: false
requirements:
  - PAP-04
  - PAP-05
  - PAP-06

must_haves:
  truths:
    - "STEP-EVENTS.md exists at .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md and renders Pydantic schemas for all nine new step-tier event types."
    - "All nine event types follow the v40 EVENT-TAXONOMY.md naming convention (state.{tier}.{action}): state.step.plan_authored, state.step.plan_edit, state.step.plan_edit_blocked, state.step.checkpoint_auto_resolved, state.step.checkpoint_human_action_pending, state.step.checkpoint_human_action_resolved, state.step.renamed, state.step.added, state.step.removed."
    - "Each event has a Pydantic class with extra='forbid' and a complete field set; common fields (event_id, aggregate_id, emitted_at) inherited from EventEnvelope per v40 convention."
    - "PlanEdit + PlanEditBlocked + StepPlanAuthored schemas in STEP-EVENTS.md MATCH the schemas already rendered in PLAN-AS-PROMPT.md (Plan 03) — re-rendered here as the canonical event-spec home with PLAN-AS-PROMPT.md cross-referencing back."
    - "Six checkpoint and replan event Pydantic schemas (CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved, StepRenamed, StepAdded, StepRemoved) are rendered for the first time in this spec."
    - "v40 EVENT-TAXONOMY.md has a `## v41 Amendment` block appended at the bottom listing the nine new state.step.* events with a forward-pointer to STEP-EVENTS.md."
    - "v40 EVENT-TAXONOMY.md original content is unchanged (append-only amendment, no in-line strikethroughs) — mirrors Phase 402's 03-v40-amendments-PLAN.md precedent."
    - "Replay-time integrity check is documented for diff-bearing events (PlanEdit hash verification) — cross-references PLAN-AS-PROMPT.md Section 6."
  artifacts:
    - path: ".planning/milestones/v41/phases/403/specs/STEP-EVENTS.md"
      provides: "Canonical step-tier event Pydantic schema spec covering 9 new event types."
      min_lines: 350
    - path: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      provides: "v40 EVENT-TAXONOMY.md with v41 amendment block enumerating new state.step.* events"
      min_lines: 270   # corrected 2026-05-10: original 600 was authoring error — file is 281 lines after amendment; 270 is a realistic floor that still guards against accidental truncation of v40 original (~196 lines pre-amendment)
  key_links:
    - from: ".planning/milestones/v41/phases/403/specs/STEP-EVENTS.md"
      to: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      via: "Naming convention and EventEnvelope inheritance reference"
      pattern: "EVENT-TAXONOMY\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-EVENTS.md"
      via: "v41 Amendment forward-pointer + new event listing"
      pattern: "state\\.step\\.(plan_authored|plan_edit|plan_edit_blocked|checkpoint_auto_resolved|checkpoint_human_action_pending|checkpoint_human_action_resolved|renamed|added|removed)"
    - from: ".planning/milestones/v41/phases/403/specs/STEP-EVENTS.md"
      to: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      via: "Cross-reference: PlanEdit/PlanEditBlocked/StepPlanAuthored shapes match"
      pattern: "PLAN-AS-PROMPT\\.md"
---

<objective>
Author the canonical `STEP-EVENTS.md` spec document and append a `## v41 Amendment` block to v40's `EVENT-TAXONOMY.md`. Together these specify the nine new step-tier event types introduced by Phase 403 — three already shipped in PLAN-AS-PROMPT.md (PlanEdit, PlanEditBlocked, StepPlanAuthored, re-rendered here as the canonical home) and six rendered for the first time (CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved, StepRenamed, StepAdded, StepRemoved).

Why standalone STEP-EVENTS.md vs. amending v40 EVENT-TAXONOMY.md only: nine events is enough mass to justify a dedicated v41 spec doc. v40 EVENT-TAXONOMY.md remains the master taxonomy reference and gets a small forward-pointer amendment block (mirrors Phase 402's `03-v40-amendments-PLAN.md` precedent for append-only v40 amendments). This division keeps the v40 taxonomy doc's 600+ lines stable and lets v41 grow its event family without polluting v40.

Purpose: PAP-04 (`plan_edit` event schema), PAP-05 (`plan_edit_blocked` event), PAP-06 (`step_plan_authored` event for audit-log original) all formally homed. STP-06 replan determinism's `state.step.renamed` / `.added` / `.removed` events get their schemas. STP-05's `checkpoint_auto_resolved` + `checkpoint_human_action_*` events get their schemas.
Output: One new spec doc at `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`, ≥350 lines, plus a `## v41 Amendment` block appended to `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/STATE.md
@.planning/milestones/v41/ROADMAP.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/HANDOFF.md
@.planning/milestones/v41/phases/403/403-CONTEXT.md
@.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
@.planning/milestones/v41/phases/402/02-context-protocol-spec-PLAN.md
@.planning/milestones/v41/phases/402/03-v40-amendments-PLAN.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
</context>

<threat_model>
Phase 403 is design-only. STEP-EVENTS.md introduces no production attack surface. Threats considered (per `<security_threat_model_gate>`):

- **`step_plan_authored` original-content snapshot tampering**: The audit-log original is the authoritative copy of every Step plan. If the snapshot row is mutable, replay loses the original. Mitigation in spec: this doc explicitly states "the `state.step.plan_authored` row is append-only per v40 EVENT-TAXONOMY.md" and renders the Pydantic schema with a `original_sha256` field that the projector verifies on replay (cross-reference to PLAN-AS-PROMPT.md replay verification).
- **PlanEdit replay tampering**: A malicious plan_edit event with a forged diff could rewrite history at replay time. Mitigation in spec: same as PLAN-AS-PROMPT.md Section 6 — before_sha256/after_sha256 fields verified at replay; mismatch rejects the event. STEP-EVENTS.md re-states this rule alongside the schema as the canonical home.
- **Amendment overwriting v40 EVENT-TAXONOMY.md content**: If the amendment writer accidentally edits non-amendment regions, v40 history is corrupted. Mitigation: append-only (write to end of file); the executor uses Edit with unique header anchor `## v41 Amendment` (which does not exist in v40 EVENT-TAXONOMY.md); verification grep checks line count is ≥600 (original size) and confirms v40's original H1 is unchanged.
- **Event taxonomy naming convention drift**: If new step.* events use different naming form than v40's `state.{tier}.{action}`, the projector / replay machinery breaks. Mitigation: every new event in this spec follows `state.step.{action}` form; spec lists them up-front; verification grep confirms no event name violates the convention.
- **Mode-isolation drift**: Build-only spec; all events go in `BUILD_ONLY_EVENT_PREFIXES`. Mitigation — explicit "Build-mode only" header note + "Mode prefix: BUILD_ONLY_EVENT_PREFIXES" line on the spec doc.

No production code lands. No secrets. No network calls. No untrusted input.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author STEP-EVENTS.md with all 9 event Pydantic schemas + replay rules + cross-references</name>
  <files>
    .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/403-CONTEXT.md (full file — every locked decision; events are scattered through <decisions>)
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (full file — Plan 03 output; PlanEdit/PlanEditBlocked/StepPlanAuthored shapes already rendered here; this spec re-renders them as the canonical event-spec home)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — Plan 02 output; references state.step.renamed/added/removed in Section 8 + state.step.checkpoint_* in Section 5)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — naming convention + EventEnvelope shape this spec extends)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic frontmatter + event payload convention)
    - .planning/milestones/v41/REQUIREMENTS.md lines 50-56 (PAP-04, PAP-05, PAP-06 verbatim)
    - .planning/milestones/v41/phases/402/02-context-protocol-spec-PLAN.md lines 80-160 (Phase 402 spec-doc plan reference for Pydantic-class-per-section rendering pattern)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`. Structure below; **concrete content from 403-CONTEXT.md + PLAN-AS-PROMPT.md verbatim — do NOT re-derive.**

    ### Section 1 — File header

    ```
    # Step-Tier Event Schemas (Canonical, v41)

    > **Phase:** 403
    > **Status:** Canonical (v41)
    > **Requirements covered:** PAP-04, PAP-05, PAP-06 (and supports STP-05 + STP-06)
    > **Build-mode only.** All events in this spec go in `BUILD_ONLY_EVENT_PREFIXES` per v40 EVENT-TAXONOMY.md mode-isolation convention.
    > **Master taxonomy:** `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (v40 baseline + v41 amendment block forward-pointing here).
    > **Sibling specs:** STEP-PLAN-FORMAT.md (artifact format); PLAN-AS-PROMPT.md (injection + mutability + content-stripping mechanics).
    ```

    1-paragraph overview: Phase 403 introduces 9 new step-tier event types. Three (`plan_authored`, `plan_edit`, `plan_edit_blocked`) underpin the plan-as-prompt audit-log + immutability-block architecture. Three (`checkpoint_auto_resolved`, `checkpoint_human_action_pending`, `checkpoint_human_action_resolved`) underpin the autonomy-tiered checkpoint behavior. Three (`renamed`, `added`, `removed`) underpin replan diff-replay continuity. Each event follows the v40 `state.{tier}.{action}` naming convention and rides the `EventEnvelope` outer shape.

    ### Section 2 — Conventions

    Heading: `## Conventions`.

    Bullets:
    - "All events have type string `state.step.{action}` per v40 EVENT-TAXONOMY.md."
    - "All events ride the `EventEnvelope` outer shape (event_id, event_type, aggregate_id=step_id or slice_id, emitted_at, payload)."
    - "All payload Pydantic models have `model_config = ConfigDict(extra=\"forbid\")`."
    - "All event store rows are **append-only** — no UPDATE/DELETE; corrections are NEW events."
    - "All `datetime` fields are UTC ISO-8601."
    - "All `*_sha256` fields are lowercase hex SHA-256."
    - "Mode prefix: `BUILD_ONLY_EVENT_PREFIXES` includes `state.step.` (Build-only)."

    Sub-section `### EventEnvelope reference (v40 convention)`:
    Render the EventEnvelope shape as a fenced Python block (mirror v40 EVENT-TAXONOMY.md design conventions section):

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

    "Forward-pointer: full envelope contract lives in `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`."

    ### Section 3 — Plan-Lifecycle Events (PAP-04, PAP-05, PAP-06)

    Heading: `## Plan-Lifecycle Events (PAP-04, PAP-05, PAP-06)`.

    1-paragraph intro: these events form the audit-log + immutability-block backbone. Already rendered in PLAN-AS-PROMPT.md sections 6–8; re-rendered here as the canonical event-spec home.

    Sub-section `### state.step.plan_authored (StepPlanAuthored — PAP-06)`:
    - 1-paragraph trigger: "Emitted at research-slice end (when planner-validation stage passes). Payload is the original verbatim content of `stepNPLAN.md` plus its SHA-256 hash. The event store row is the AUTHORITATIVE audit-log original."
    - State transition: "(none — events are append-only; this is an audit record, not an FSM transition)."
    - Render Pydantic class (matches PLAN-AS-PROMPT.md Section 8):

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

    Sub-section `### state.step.plan_edit (PlanEdit — PAP-04)`:
    - 1-paragraph trigger: "Emitted on every successful edit to `stepNPLAN.md` (executor, harness, or human). Carries unified diff + before/after hashes. Replay reconstructs full content by walking the diff chain from the original `state.step.plan_authored` event."
    - State transition: "(none — append-only audit record)."
    - Render Pydantic class (matches PLAN-AS-PROMPT.md Section 6):

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

    Sub-section `### state.step.plan_edit_blocked (PlanEditBlocked — PAP-05)`:
    - 1-paragraph trigger: "Emitted by the diff-the-proposed-write enforcer (`tool.execute.before` hook) when a proposed edit touches a locked section per the Mutability Matrix. Per PLAN-AS-PROMPT.md §7."
    - State transition: "(none — append-only audit record; the proposed edit did NOT land on disk)."
    - Render Pydantic class (matches PLAN-AS-PROMPT.md Section 7):

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

    Sub-section `### Replay-time integrity check`:
    "On replay, the projector verifies for every `state.step.plan_edit` event:"
    1. "`before_sha256` matches the SHA-256 of the on-disk content prior to applying `diff` (or, on cold replay starting from `state.step.plan_authored`, matches the original content hash)."
    2. "`after_sha256` matches the SHA-256 after applying `diff`."
    3. "On hash mismatch, the projector REJECTS the event (logs error, does not advance the projection state). Mismatched-hash events surface as a daemon-startup error gating the harness from spawning new sessions until reconciled."

    "Cross-reference: PLAN-AS-PROMPT.md §6 (Replay verification subsection) is the authoritative source for this rule."

    ### Section 4 — Checkpoint Events (STP-05)

    Heading: `## Checkpoint Events (STP-05)`.

    1-paragraph intro: these events fire when a `<task type="checkpoint:*">` task is gate-resolved (auto-approved or human-resumed). They support the autonomy-tiered behavior specified in STEP-PLAN-FORMAT.md Section 5.

    Sub-section `### state.step.checkpoint_auto_resolved (CheckpointAutoResolved)`:
    - 1-paragraph trigger: "Emitted when a `checkpoint:human-verify` or `checkpoint:decision` task is auto-resolved by the harness under `--tiered` or `--full-yolo` autonomy. For `human-verify` under tiered/yolo: auto-approves. For `decision` under yolo: picks first option deterministically. See STEP-PLAN-FORMAT.md §5."
    - State transition: "task: `pending` → `resolved`."
    - Render:

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

    Sub-section `### state.step.checkpoint_human_action_pending (CheckpointHumanActionPending)`:
    - Trigger: "Emitted when a `checkpoint:human-action` task is entered. ALL autonomy tiers stop here — harness surfaces via opencode `question` tool."
    - State transition: "task: `running` → `pending_human`."

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

    Sub-section `### state.step.checkpoint_human_action_resolved (CheckpointHumanActionResolved)`:
    - Trigger: "Emitted when a `checkpoint:human-action` task is resumed by human confirmation."
    - State transition: "task: `pending_human` → `resolved`."

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

    ### Section 5 — Replan-Continuity Events (STP-06)

    Heading: `## Replan-Continuity Events (STP-06)`.

    1-paragraph intro: when planner-validation re-runs (replan iteration) with changed inputs, the granularity algorithm may produce a different Step set. Diff-replay continuity events let downstream consumers (Phase 404 gates, scheduler, projector) reconcile the change without losing replay determinism.

    Sub-section `### state.step.renamed (StepRenamed)`:
    - Trigger: "Emitted when replan determines the step_id changed for an authored Step (input change forced rename per STEP-PLAN-FORMAT.md §8 stable-hash rule)."
    - State transition: "step: identity-rebound; new step_id inherits authored content but `must_haves` are re-authored fresh (no carry-over of stale gates)."
    - Render:

    ```python
    class StepRenamed(BaseModel):
        model_config = ConfigDict(extra="forbid")
        slice_id: str
        old_step_id: str
        new_step_id: str
        renamed_at: datetime
        replan_event_id: str               # links to the parent state.slice.replanned event
    ```

    Sub-section `### state.step.added (StepAdded)`:
    - Trigger: "Emitted when replan creates a new Step (e.g., granularity bumped from coarse=1 to coarse=2 due to scope_tokens > 15_000)."
    - State transition: "(new aggregate)."
    - Render:

    ```python
    class StepAdded(BaseModel):
        model_config = ConfigDict(extra="forbid")
        slice_id: str
        step_id: str
        added_at: datetime
        replan_event_id: str
    ```

    Sub-section `### state.step.removed (StepRemoved)`:
    - Trigger: "Emitted when replan eliminates an authored Step (e.g., merged into another Step, or scope reduction from fine to standard granularity)."
    - State transition: "step: `*` → `removed_by_replan`."
    - Render:

    ```python
    class StepRemoved(BaseModel):
        model_config = ConfigDict(extra="forbid")
        slice_id: str
        step_id: str
        removed_at: datetime
        replan_event_id: str
        reason: Literal["merged", "scope_reduction", "other"]
    ```

    Sub-section `### Lock survival across replan`:
    "Per STEP-PLAN-FORMAT.md §8 (Replan determinism subsection): when step_id is **unchanged** across replan, locks held by PAP-03 (`must_haves`, `<verify>`) survive. When step_id **changes** (StepRenamed event fires), the new Step inherits authored content but `must_haves` are re-authored fresh (no carry-over of stale gates)."

    ### Section 6 — Cross-references + Closing

    Heading: `## Cross-references + Closing`.

    Bullet list:
    - **Master event taxonomy:** `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — the v40 baseline; receives a `## v41 Amendment` block via Task 2 of this plan listing all 9 events with forward-pointers here.
    - **Sibling spec — format:** `STEP-PLAN-FORMAT.md` references state.step.renamed / added / removed in §8 and state.step.checkpoint_* in §5.
    - **Sibling spec — injection + mutability:** `PLAN-AS-PROMPT.md` already renders PlanEdit / PlanEditBlocked / StepPlanAuthored in §§6–8 of that doc; STEP-EVENTS.md is the canonical event-spec home with the same shapes.
    - **v14 implementation hooks:** v14 Build Kernel implements (a) the projector replay-verifier (hash check), (b) the daemon emitter for each event type (one `state.step.*` row per harness action), (c) the projection-state reducer that consumes these events to update the per-Step in-memory state.
    - **Phase 404 (Boolean Proof Gate)** consumes `state.step.plan_edit_blocked` indirectly — gate fails when an immutable `<verify>` block is touched.
    - **Phase 405 (Subagent Management)** consumes `state.step.checkpoint_*` events for autonomy-inheritance verification.
    - **Phase 406 (Harness Architecture Rollup)** the layered diagram + sequence diagram cite all 9 events; the event-replay reconstruction proof (HRN-07) lists them as "must replay to rebuild harness state."

    Add closing 1-paragraph note: "Build-mode only. All schemas extend `state_core.schema.EventEnvelope` per v40 convention. v14 Build Kernel ships the Pydantic models. v15 Build Core Commands wires emitters into the research-slice pipeline + execute-slice harness."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` Sections 6, 7, 8 — the three Pydantic schemas (PlanEdit, PlanEditBlocked, StepPlanAuthored) MUST match byte-for-byte. Re-render verbatim from there.
        - Known: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` lines 1-30 — design conventions; mirror the section layout (intro + table + per-event blocks).
        - Known: `.planning/milestones/v41/phases/403/403-CONTEXT.md` — every event class shape is sketched here in the <decisions> "Injection-time mechanics" + "Task-type behaviors" + "Granularity → Replan determinism" subsections; copy field sets verbatim.
        - Grep pattern: `grep -nE "^class |^    model_config" /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md | head -30` — locates the three already-rendered schemas to ensure byte-for-byte match.
      </code_to_reuse>
      <docs_to_consult>
        - 403-CONTEXT.md `<decisions>` Injection-time mechanics — verbatim source for PlanEdit and PlanEditBlocked.
        - 403-CONTEXT.md `<decisions>` Task-type behaviors — auto+tdd commit-trailer convention; checkpoint:* event names.
        - 403-CONTEXT.md `<decisions>` Granularity → Replan determinism — state.step.renamed / added / removed event names.
        - v40 EVENT-TAXONOMY.md Design Conventions section — `state.{tier}.{action}` naming + EventEnvelope shape + append-only guarantee.
        - v40 FRONTMATTER-SCHEMAS.md — Pydantic frontmatter convention extends to event payloads.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown spec; v14 implementation will write Pydantic-roundtrip tests against these schemas.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 350)}' \
        && grep -qE "^# Step-Tier Event Schemas" "$F" \
        && grep -qE "^## Conventions" "$F" \
        && grep -qE "^## Plan-Lifecycle Events" "$F" \
        && grep -qE "^## Checkpoint Events" "$F" \
        && grep -qE "^## Replan-Continuity Events" "$F" \
        && grep -qE "^## Cross-references" "$F" \
        && grep -q "class StepPlanAuthored" "$F" \
        && grep -q "class PlanEdit" "$F" \
        && grep -q "class PlanEditBlocked" "$F" \
        && grep -q "class CheckpointAutoResolved" "$F" \
        && grep -q "class CheckpointHumanActionPending" "$F" \
        && grep -q "class CheckpointHumanActionResolved" "$F" \
        && grep -q "class StepRenamed" "$F" \
        && grep -q "class StepAdded" "$F" \
        && grep -q "class StepRemoved" "$F" \
        && grep -q "state.step.plan_authored" "$F" \
        && grep -q "state.step.plan_edit" "$F" \
        && grep -q "state.step.plan_edit_blocked" "$F" \
        && grep -q "state.step.checkpoint_auto_resolved" "$F" \
        && grep -q "state.step.checkpoint_human_action_pending" "$F" \
        && grep -q "state.step.checkpoint_human_action_resolved" "$F" \
        && grep -q "state.step.renamed" "$F" \
        && grep -q "state.step.added" "$F" \
        && grep -q "state.step.removed" "$F" \
        && grep -c 'extra="forbid"' "$F" | awk '{exit ($1 < 9)}' \
        && grep -q "BUILD_ONLY_EVENT_PREFIXES" "$F" \
        && grep -q "PLAN-AS-PROMPT.md" "$F" \
        && grep -q "STEP-PLAN-FORMAT.md" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - File exists at `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` with ≥350 lines.
    - All 6 H2 section headings present (Conventions, Plan-Lifecycle Events, Checkpoint Events, Replan-Continuity Events, Cross-references — plus H1 file header).
    - All 9 Pydantic class definitions present: StepPlanAuthored, PlanEdit, PlanEditBlocked, CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved, StepRenamed, StepAdded, StepRemoved.
    - All 9 event-type strings present in `state.step.{action}` form (line-grep returns ≥9 matches).
    - `extra="forbid"` appears at least 9 times (one per Pydantic class).
    - `BUILD_ONLY_EVENT_PREFIXES` cited in conventions.
    - PlanEdit / PlanEditBlocked / StepPlanAuthored field sets match PLAN-AS-PROMPT.md byte-for-byte (manual diff: `diff <(grep -A 12 "class PlanEdit" PLAN-AS-PROMPT.md) <(grep -A 12 "class PlanEdit" STEP-EVENTS.md)` returns minimal diff).
    - Forward-pointers to PLAN-AS-PROMPT.md and STEP-PLAN-FORMAT.md present.
  </acceptance_criteria>

  <done>
    STEP-EVENTS.md complete — 9 step-tier event Pydantic schemas formally homed; replay-verification rule cross-referenced; v40 EVENT-TAXONOMY.md naming convention respected. Task 2 will append the v40 amendment block.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append `## v41 Amendment` block to v40 EVENT-TAXONOMY.md listing the 9 new state.step.* events</name>
  <files>
    .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
  </files>

  <read_first>
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — original; the amendment is APPENDED at the bottom; do not edit existing content)
    - .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md (full file — Task 1 output; the amendment forward-points here)
    - .planning/milestones/v41/phases/402/03-v40-amendments-PLAN.md (full file — Phase 402 v40-amendment plan; mirror its append-only style, "Prior model (v40)" / "Canonical model (v41)" structure if applicable; THIS task's amendment is purely additive — new events, not a model correction — so the prior/canonical phrasing is adapted to "v40 baseline scope" / "v41 extension scope")
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md last 30 lines (to confirm where to append; ensure no existing `## v41 Amendment` section before writing)
  </read_first>

  <action>
    Append a `## v41 Amendment` block to the END of `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`. **Do NOT edit any existing content.** Use Edit tool with the file's last existing line as the anchor (find the final non-blank line and append a new section after it).

    Render the amendment block exactly:

    ```markdown
    ---

    ## v41 Amendment — Step-Tier Event Family Extension

    > **Source phase:** v41 Phase 403 (Step/Task Decomposition & Plan-as-Prompt)
    > **Amendment date:** {today's date in YYYY-MM-DD form}
    > **Amendment type:** Additive — new event types added to the step tier; v40 baseline events unchanged.
    > **Forward-pointer:** Full Pydantic schemas + replay rules in `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`.

    ### v40 baseline scope

    The original v40 EVENT-TAXONOMY.md covered Arc, Stage, Slice, and Step events at the FSM-transition layer (e.g., `state.step.created`, `state.step.completed`). v41 Phase 403 extends the step tier with NINE new events for plan-authoring, plan-mutation, autonomy-tiered checkpoint resolution, and replan diff-replay continuity. None of these v41 additions change v40 baseline event semantics or names.

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
    - Projector replay-verifier (PlanEdit hash chain integrity check; see STEP-EVENTS.md §3 Replay-time integrity check).
    - Projection-state reducers (per-Step in-memory state updated from event stream).

    See `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` for full schemas and replay rules.
    ```

    **Verification before commit:** verify the file's pre-amendment line count is ≥600 (original size guard) and v40's H1 (line 1: `# Event Taxonomy — All Four Tiers`) is unchanged.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/03-v40-amendments-PLAN.md` — Phase 402's append-only amendment precedent. Mirror the "## v41 Amendment" header style + "v40 baseline scope" / "v41 extension scope" subsection structure.
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` (Task 1 output) — the 9 event types + forward-pointer target.
        - Grep pattern: `grep -n "^# Event Taxonomy" /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — confirms the anchor H1 line is at top.
        - Grep pattern: `grep -n "^## v41 Amendment" /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — must return 0 matches BEFORE the append (no pre-existing amendment); ≥1 after.
      </code_to_reuse>
      <docs_to_consult>
        - Phase 402's 03-v40-amendments-PLAN.md and the actual amended files (e.g., `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` if it exists) for the canonical "Prior model" / "Canonical model" / "v41 extension" phrasing pattern.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendment.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 600)}' \
        && head -1 "$F" | grep -q "^# Event Taxonomy" \
        && grep -qE "^## v41 Amendment" "$F" \
        && grep -q "Step-Tier Event Family Extension" "$F" \
        && grep -q "STEP-EVENTS.md" "$F" \
        && grep -q "state.step.plan_authored" "$F" \
        && grep -q "state.step.plan_edit_blocked" "$F" \
        && grep -q "state.step.checkpoint_auto_resolved" "$F" \
        && grep -q "state.step.renamed" "$F" \
        && grep -q "state.step.added" "$F" \
        && grep -q "state.step.removed" "$F" \
        && grep -q "PAP-04" "$F" \
        && grep -q "PAP-05" "$F" \
        && grep -q "PAP-06" "$F" \
        && grep -q "STP-05" "$F" \
        && grep -q "STP-06" "$F" \
        && grep -q "BUILD_ONLY_EVENT_PREFIXES" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - v40 EVENT-TAXONOMY.md line count is ≥600 (preserves v40 baseline content).
    - v40 H1 line `# Event Taxonomy — All Four Tiers` unchanged (head -1 grep passes).
    - `## v41 Amendment` heading present exactly once.
    - All 9 new event names listed in the amendment table.
    - REQ-ID columns include PAP-04, PAP-05, PAP-06, STP-05, STP-06.
    - Forward-pointer to STEP-EVENTS.md present.
    - "Additive — new event types" classification stated.
    - `BUILD_ONLY_EVENT_PREFIXES` mode-isolation note present.
  </acceptance_criteria>

  <done>
    v40 EVENT-TAXONOMY.md amendment closes SLC-07-style precedent for Phase 403 — additive v41 extension forward-points to STEP-EVENTS.md without disturbing v40 baseline.
  </done>
</task>

<task type="auto">
  <name>Task 3: Write 04-step-events-SUMMARY.md</name>
  <files>
    .planning/milestones/v41/phases/403/04-step-events-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md (full file — Task 1 output)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — confirm v41 Amendment block landed; Task 2 output)
    - .planning/milestones/v41/phases/402/402-03-SUMMARY.md (full file — sibling SUMMARY shape reference for the v40-amendment-style plan; mirror its structure)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory gate
  </read_first>

  <action>
    Author the per-plan SUMMARY.md mirroring `402-03-SUMMARY.md` (which was Phase 402's v40-amendment plan SUMMARY):

    1. `# Plan 403-04 Summary: STEP-EVENTS.md + v40 Amendment`
    2. Status line: `**Status:** Shipped` + `**Wave:** 3` + `**Depends on:** 02 (STEP-PLAN-FORMAT.md), 03 (PLAN-AS-PROMPT.md)` + `**Blocks:** none (Phase 403 final plan)`.
    3. `## What Was Built` — 1 paragraph: STEP-EVENTS.md at the canonical path with 9 step-tier event Pydantic schemas; v40 EVENT-TAXONOMY.md amended with a forward-pointer block.
    4. `## Key Decisions` — bullets:
       - "Standalone STEP-EVENTS.md spec chosen over inlining all 9 events into PLAN-AS-PROMPT.md — 9 events is sufficient mass to justify a dedicated v41 doc; mirrors Phase 402's v40-amendment-with-companion-spec precedent."
       - "v40 EVENT-TAXONOMY.md amendment is purely additive — no v40 baseline events renamed or repurposed; the amendment scope line says so explicitly."
       - "PlanEdit / PlanEditBlocked / StepPlanAuthored re-rendered in STEP-EVENTS.md byte-for-byte from PLAN-AS-PROMPT.md — STEP-EVENTS.md is the canonical event-spec home; PLAN-AS-PROMPT.md cross-references back."
       - "Six new schemas authored: CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved, StepRenamed, StepAdded, StepRemoved."
       - "Naming convention: every new event is `state.step.{action}` per v40 baseline."
       - "Mode prefix: BUILD_ONLY_EVENT_PREFIXES (state.teach.* not affected)."
    5. `## Files Touched` — 2 files:
       - `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` (new)
       - `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (append-only amendment)
    6. `## Open Items / Deferred` — bullets:
       - "v14 Build Kernel implements: projector replay-verifier (hash chain integrity), daemon emitters, projection-state reducers."
       - "v15 Build Core Commands wires emitters into the research-slice pipeline + execute-slice harness."
       - "Pydantic-roundtrip tests of these schemas land with v14 implementation, not Phase 403 (design-only)."
    7. `## Downstream Hooks` — bullets:
       - "Phase 404 (Boolean Proof Gate) consumes state.step.plan_edit_blocked indirectly — gate fails when an immutable <verify> block is touched."
       - "Phase 405 (Subagent Management) consumes state.step.checkpoint_* events for autonomy-inheritance verification."
       - "Phase 406 (Harness Architecture Rollup) layered diagram + sequence diagram cite all 9 events; HRN-07 event-replay reconstruction proof lists them."

    Length: 80-150 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/402-03-SUMMARY.md` — sibling v40-amendment SUMMARY exemplar.
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md per-plan-SUMMARY-mandatory subsection.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/04-step-events-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 60)}' \
        && grep -q "Plan 403-04" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "STEP-EVENTS.md" "$F" \
        && grep -q "EVENT-TAXONOMY.md" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - SUMMARY exists with ≥60 lines.
    - References Plan 04, both files touched (STEP-EVENTS.md + EVENT-TAXONOMY.md amendment).
    - All four core sections present.
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate closed for Plan 04. Phase 403 plan slate complete.
  </done>
</task>

</tasks>

<verification>
- File `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` exists with ≥350 lines.
- File `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` has line count ≥600 with `## v41 Amendment` block at the bottom.
- File `.planning/milestones/v41/phases/403/04-step-events-SUMMARY.md` exists with ≥60 lines.
- All 9 event Pydantic class definitions in STEP-EVENTS.md.
- All 9 event name strings (state.step.{action}) present in BOTH STEP-EVENTS.md AND the v40 amendment block.
- v40 H1 (`# Event Taxonomy — All Four Tiers`) unchanged.
- `BUILD_ONLY_EVENT_PREFIXES` mode-isolation note in both files.
- No `state.teach.` references.
</verification>

<success_criteria>
- PAP-04 (`plan_edit` event schema) formally homed: PlanEdit Pydantic class with all 9 fields including before_sha256/after_sha256.
- PAP-05 (`plan_edit_blocked` event for immutable-section block): PlanEditBlocked Pydantic class with locked_section field.
- PAP-06 (`step_plan_authored` event for audit-log original): StepPlanAuthored Pydantic class with original_content + original_sha256 fields.
- 6 additional schemas (CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved, StepRenamed, StepAdded, StepRemoved) authored to support STP-05 + STP-06.
- v40 EVENT-TAXONOMY.md amendment is append-only and additive (mirrors Phase 402 v40-amendment precedent).
- Per-plan SUMMARY.md gate closed.
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` (≥350 lines, new)
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (≥600 lines, append-only amendment)
- `.planning/milestones/v41/phases/403/04-step-events-SUMMARY.md` (≥60 lines, new)

Phase 403 plan slate complete: 4 plans, 12 tasks, 3 spec docs (EXEMPLAR-stepNPLAN.md, STEP-PLAN-FORMAT.md, PLAN-AS-PROMPT.md, STEP-EVENTS.md) + 1 v40 amendment.
</output>
