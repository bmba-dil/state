---
phase: 405
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
autonomous: false
requirements:
  - SUB-05
  - SUB-06
  - SUB-07
  - SUB-08
  - SUB-09

must_haves:
  truths:
    - "SUBAGENT-MONITORING.md exists at .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md and fully specifies the subagent monitoring protocol covering SUB-05 (SSE events), SUB-06 (structured return registry + 4-layer spot-check), SUB-07 (5-source crash taxonomy + 3-restart counter + <prior_crash> continuation context), SUB-08 (task_id survival across compaction and Slice-boundary respawn), SUB-09 (autonomy inheritance from parent Slice)."
    - "Three SSE event Pydantic payloads are rendered verbatim: `SubagentStarted` (with `parent_task_id`, `invocation_id`, `subagent_type`, `slice_id`, `task`, `started_at`, `session_id`), `SubagentProgress` (with `invocation_id`, `parent_task_id`, `kind` Literal of event subtypes, `payload_excerpt`, `emitted_at`), `SubagentComplete` (with `invocation_id`, `parent_task_id`, `stop_reason` Literal, `declared_artifacts`, `declared_commits`, `completed_at`)."
    - "Event-naming convention is documented: `state.step.subagent_started`, `state.step.subagent_progress`, `state.step.subagent_complete`, `state.step.subagent_spot_check_failed`, `state.step.subagent_crash_detected`, `state.step.subagent_restart`, `state.step.subagent_restart_exhausted`, `state.step.subagent_orphan_detected` (8 new events; registered by Plan 04 in EVENT-TAXONOMY.md)."
    - "Parent-task linkage discipline is documented: every subagent event carries `parent_task_id`; the daemon's SSE filter subscribes by `parent_task_id` to surface child events on the parent's TUI stream. Cross-references gsd-2 `agent-lifecycle.md` §2.2 `agent.sessionId` invariant."
    - "The `SUBAGENT_RETURN_REGISTRY` Pydantic registry is rendered verbatim as `dict[SubagentType, type[SubagentReturnBase]]` with all 14 entries (one per SubagentType from Plan 02). Module path `state_build/subagents/returns.py` named as single-source-of-truth."
    - "`ArtifactDeclaration` and `SubagentReturnBase` Pydantic classes are rendered verbatim with `model_config = ConfigDict(extra='forbid')`. SubagentReturnBase fields: `subagent_type` (Literal discriminator), `parent_task_id`, `invocation_id`, `declared_artifacts: list[ArtifactDeclaration]`, `declared_commits: list[str]`, `stop_reason` Literal, `error_message`. ArtifactDeclaration fields: `path`, `sha256`, `line_count`."
    - "Per-type extension example (`ExecutorReturn`) is rendered verbatim with `subagent_type: Literal['executor']` discriminator + extra fields (`files_modified_actual`, `test_pass_count`, `test_fail_count`). Module organization per stage (`state_build/subagents/returns_*.py`) is documented."
    - "4-layer spot-check protocol is rendered as a 4-row markdown table with columns (Layer, Check, Failure trigger) covering: (1) Process classification (exit_code==0 AND stop_reason∉{error,aborted}); (2) Pydantic validate (model_validate_json with extra='forbid'); (3) Artifact existence (path exists AND sha256 matches AND line_count matches); (4) Commit existence (git rev-parse --verify, reachable from worktree branch)."
    - "Server-side recomputation discipline is documented: harness recomputes `overall_success` from layer verdicts; agent-emitted aggregates are rejected. Mirrors gsd-2 `server-recomputation-of-llm-emitted-fields.md` + Phase 404 PRF overall_passed pattern."
    - "`SubagentSpotCheckFailed` event payload is rendered verbatim with fields (`invocation_id`, `parent_task_id`, `subagent_type`, `layer` Literal['process','pydantic','artifact','commit'], `evidence_excerpt` ≤2KB, `failed_at`, `session_id`)."
    - "5-source crash taxonomy is rendered as a 2-column markdown table with all five crash_source values (`process_exit`, `stop_reason`, `spot_check`, `sse_silence` with default `progress_timeout_s=180`, `parent_task_error`)."
    - "`SubagentCrashDetected` event payload is rendered verbatim with fields (`invocation_id`, `parent_task_id`, `subagent_type`, `crash_source` Literal, `restart_number: int  # 1..3; 4 triggers escalation`, `evidence_excerpt`, `detected_at`, `session_id`)."
    - "Restart counter scope is documented as per-`(parent_task_id, subagent_type)` tuple (diverges from per-invocation_id rationale: prevents agent gaming via slight prompt variations on the same logical work unit). Mirrors 404 per-(task_id, check_id) strike discipline."
    - "After-3-restart escalation is documented: parent agent must call `log_deviation` with `rule_id=3` (blocking) or `rule_id=4` (architectural) via cross-reference to DEVIATION-RULES.md. Escalation event `state.step.subagent_restart_exhausted` rendered with payload (`parent_task_id`, `subagent_type`, terminal `crash_source`)."
    - "<prior_crash> continuation context XML structure is rendered verbatim with `<restart_number>`, `<crash_source>`, `<prior_evidence>` (≤2KB excerpt), `<remediation_hint>` blocks plus an `<original_task>` block holding the verbatim original prompt. Mirrors Phase 402 reinject body XML discipline."
    - "Worktree-rollback over partial-artifact-preservation is documented as the v1 invariant; idempotency principle stated; revisit-post-v17 deferred-list note included."
    - "task_id survival cross-reference to CTX-07 is documented (SUB-08): event-store authoritative + daemon projector rehydration on boot; the `CompactionSnapshot` Pydantic model gains `subagent_restart_counters: dict[str, int]` and `in_flight_subagents: list[InFlightSubagent]` fields (extends Phase 402)."
    - "Daemon-down + orphan reconciliation flow is rendered as a 6-step numbered protocol (replay event-store -> probe opencode session API -> wait for natural completion if running -> reconstruct from session log if done-no-event -> emit subagent_orphan_detected if lost -> escalate to Rule 4 if persistent). `SubagentOrphanDetected` + `InFlightSubagent` Pydantic models rendered verbatim."
    - "Autonomy inheritance from parent Slice (SUB-09) is documented as a 3-step flow: (1) parent's effective autonomy = `Slice.frontmatter.autonomy ?? milestone.autonomy`; (2) per-dispatch override allowed via `DispatchSubagent.{single,parallel,chain}[i].autonomy: Literal | None`; (3) grandchildren inherit from child's effective autonomy, not the original parent."
    - "Mode-isolation note rendered: `state_build/subagents/` MUST NOT import from `state_teach/`; events live in BUILD_ONLY_EVENT_PREFIXES; CI import-graph lint enforces."
    - "SUBAGENT-MONITORING.md does NOT contain the literal string `GSD` anywhere (project naming-discipline rule)."
  artifacts:
    - path: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      provides: "Canonical subagent monitoring spec covering SUB-05..SUB-09: SSE event family, SUBAGENT_RETURN_REGISTRY + 4-layer spot-check, 5-source crash taxonomy + 3-restart counter + <prior_crash> continuation, task_id survival across compaction/Slice-boundary, orphan reconciliation flow, autonomy inheritance from parent Slice."
      min_lines: 650
  key_links:
    - from: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      via: "Sibling Part-1-of-2; SUBAGENT-MONITORING.md consumes SubagentType + STAGE_ROSTER + dispatch_subagent shape from Part 1"
      pattern: "SUBAGENT-MANAGEMENT\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      to: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      via: "Spot-check + restart-exhaustion failures escalate via log_deviation to Rule 3 (blocking issue) or Rule 4 (architectural); autonomy inheritance flow consumes DEV-05/DEV-06 tiered autonomy table"
      pattern: "DEVIATION-RULES\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "task_id survival cross-reference (SUB-08 cross-references CTX-07); CompactionSnapshot extended with subagent_restart_counters + in_flight_subagents fields"
      pattern: "CONTEXT-PROTOCOL\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "Three-counter independence (subagent_restart counter is the fourth chain, distinct from APG/PRF/DEV); spot-check overall_success server-recomputation mirrors PRF overall_passed pattern"
      pattern: "PROOF-GATE\\.md"
---

<objective>
Author the canonical `SUBAGENT-MONITORING.md` spec document — Part 2 of 2 (Plan 02 authored Part 1). This file fully specifies the subagent runtime monitoring protocol: (1) the three-event SSE family `subagent_started` / `subagent_progress` / `subagent_complete` linked by parent `task_id` (SUB-05); (2) the central `SUBAGENT_RETURN_REGISTRY` Pydantic registry + 4-layer pure-machine spot-check stack (SUB-06); (3) the 5-source crash taxonomy + 3-restart counter with augmented `<prior_crash>` continuation context XML, worktree-rollback over partial-artifact-preservation (SUB-07); (4) `task_id` survival across compaction and Slice-boundary respawn — cross-references CTX-07 — plus daemon-down orphan reconciliation flow (SUB-08); (5) autonomy inheritance from parent Slice (consumes DEV-05/DEV-06) with per-dispatch override (SUB-09).

Purpose: SUB-05..SUB-09 fully covered. Downstream consumers — v14 (Build Kernel: SSE subscribers, SUBAGENT_RETURN_REGISTRY + spot-check stack, crash projector, restart-counter projector, in-flight projector, orphan reconciliation handler, autonomy-context-block builder), v15 (Build Core Commands: verify-slice integration), Phase 406 (HRN-04 4-tier intervention ladder cites spot-check + crash escalation; HRN-07 event-replay reconstruction cites daemon projector rehydration) — all read from this file.

Output: One markdown spec doc at `.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md`, ≥650 lines, fully populated with: 3 SSE event Pydantic payloads + 5 monitoring event payloads (SubagentSpotCheckFailed, SubagentCrashDetected, SubagentRestart, SubagentRestartExhausted, SubagentOrphanDetected); the SUBAGENT_RETURN_REGISTRY dict literal; ArtifactDeclaration + SubagentReturnBase + per-type extension example; 4-layer spot-check table; 5-source crash taxonomy table; <prior_crash> XML block; CompactionSnapshot extension fields; 6-step orphan reconciliation; 3-step autonomy inheritance flow.
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
@.planning/milestones/v41/phases/405/405-CONTEXT.md
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — `SubagentType` + `STAGE_ROSTER` from Plan 02 (SUBAGENT-MANAGEMENT.md Section 3). SUBAGENT_RETURN_REGISTRY consumes the SubagentType keys verbatim. Do NOT re-define here.

Excerpt B — Phase 402 `CompactionSnapshot` Pydantic model (extends with two new fields):
```python
# From .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
class CompactionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... existing fields ...
    # Phase 405 additions:
    subagent_restart_counters: dict[str, int]            # key = "{parent_task_id}|{subagent_type}", value = restart count
    in_flight_subagents: list[InFlightSubagent]          # for Slice-boundary spawn
```

Excerpt C — `SliceFrontmatter.subagent` nested config (defined by Plan 02; this spec adds two fields):
```python
class SubagentSliceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parallel_cap: int | None = None                       # SUB-04 (Plan 02 owns)
    progress_timeout_s: int | None = None                 # SUB-07 (THIS SPEC OWNS) — default 180s
    remediation_hints: dict[str, str] | None = None       # SUB-07 (THIS SPEC OWNS) — keyed by crash_source
```

Excerpt D — DEVIATION-RULES.md tiered autonomy table (Plan 01; SUB-09 consumes for autonomy inheritance):
```python
# From .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md Section 6
# Modes: --tiered (default) / --full-yolo / --conservative
# Rule 4 ALWAYS stops (4th column, structural-not-policy)
```

Excerpt E — Phase 404 PRF `overall_passed` server-recomputation pattern (SUB-06 spot-check mirrors):
```python
# From .planning/milestones/v41/phases/404/specs/PROOF-GATE.md Section 7 (StepVerifyResult)
# Server recomputes overall_passed from sub-fields; agent-emitted aggregates rejected
# State's 4-layer spot-check applies the same discipline to subagent return shapes
```

Excerpt F — CTX-07 identifier-survival contract (Phase 402; SUB-08 cross-references):
```python
# From .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md §CTX-07
# task_id, step_id, slice_id survive compaction AND Slice-boundary session spawn
# reinjection events reference prior session_id
# SUB-08 extends: task_id of the parent task carries through; subagent invocation_id is fresh per dispatch
```
</interfaces>

<threat_model>
Phase 405 is design-only. SUBAGENT-MONITORING.md introduces no production attack surface — it is a markdown specification. Threats considered:

- **[high] Spot-check bypass via agent-emitted overall_success**: If the spec leaves `overall_success` as agent-set, an LLM could claim success despite layer-3 (artifact existence) failures. **Mitigation in spec:** server-side recomputation is NON-NEGOTIABLE; the spec stipulates the harness derives `overall_success` from layer verdicts and ignores any agent-emitted aggregate. Mirrors 404 PRF + gsd-2 `server-recomputation-of-llm-emitted-fields.md`.

- **[high] Restart-counter evasion via prompt variation**: If the counter scope were per-`invocation_id`, an agent could re-invoke the same subagent type with a slight prompt variation to reset the 3-restart budget. **Mitigation in spec:** per-`(parent_task_id, subagent_type)` tuple is the canonical scope; the spec stipulates this verbatim. Mirrors 404 per-(task_id, check_id) strike discipline. v14 enforces at the projector.

- **[high] Orphan subagent persistence after Slice close**: If a Slice closes with in-flight subagents and the daemon never reconciles, the worktree merge could happen before subagent commits land. **Mitigation in spec:** the 6-step orphan reconciliation flow runs on daemon resume AND at Slice-close gate; persistent orphans escalate to Rule 4 (human resolution via opencode question). Spec stipulates `subagent_orphan_detected` event + Rule-4 alternatives `[abort_slice, retry_subagent, manual_resolve]`.

- **[med] sha256 collision in ArtifactDeclaration**: Layer 3 spot-check verifies declared sha256 matches the file's actual content hash. SHA-256 collisions are computationally infeasible in adversarial conditions but theoretically possible; intentional collision is rejected by spec contract. **Mitigation in spec:** spec stipulates SHA-256 is the canonical hash (not MD5/SHA-1); collision-induced bypass is out of scope for v1 threat model. v14 unit tests assert hash determinism.

- **[med] SSE silence false-positive crash**: If `sse_silence` is 180s but the subagent is doing legitimate long-running work (large file scan, slow LLM call), the harness could prematurely classify it as crashed. **Mitigation in spec:** `progress_timeout_s` is configurable per-Slice (Slice frontmatter `subagent: {progress_timeout_s: int}`); planner may tune to 240/300 if EXEMPLAR-stepNPLAN.md gates show false-positives. Default 180s is a documented starter value.

- **[high] Autonomy inheritance bypass via per-dispatch override**: If a child subagent's `autonomy` could move looser than the parent (e.g., parent `--conservative`, child `--full-yolo`), the parent's strictness is undermined. **Mitigation in spec:** the per-dispatch override CAN move stricter OR looser — explicitly documented per 405-CONTEXT.md (same as DEV-06 Slice override; autonomy is policy, not capability). Rationale: the planner controls plan-time frontmatter; runtime overrides require explicit per-dispatch declaration. Spec must NOT silently propagate Rule-4-bypass — Rule 4 always-stop is structural per DEVIATION-RULES.md (no autonomy short-circuit).

- **[med] Naming-discipline drift**: `STATE-Subagent-Invocation:` trailer mandatory inside subagent sessions. **Mitigation:** spec names the trailer verbatim and forward-references DEVIATION-RULES.md Section 5 single-source-of-truth module. CI grep `grep -nE '\bGSD-'` MUST return zero.

- **[low] Mode-isolation drift**: Build-only spec. **Mitigation:** `state_build/subagents/` module convention; events in BUILD_ONLY_EVENT_PREFIXES; CI import-graph lint.

No production code lands. No secrets. No network calls.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author SUBAGENT-MONITORING.md sections 1-4 (header, SSE event family SUB-05, SUBAGENT_RETURN_REGISTRY SUB-06, 4-layer spot-check SUB-06)</name>
  <files>
    .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Structured return shape registry (SUB-06 expanded)" subsection (verbatim source for Section 3 SUBAGENT_RETURN_REGISTRY + ArtifactDeclaration + SubagentReturnBase + per-type example)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Spot-check protocol (SUB-06 expanded)" subsection (verbatim source for Section 4 4-layer spot-check + SubagentSpotCheckFailed event)
    - .planning/milestones/v41/REQUIREMENTS.md lines 112-117 (SUB-05, SUB-06 verbatim)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md (the Plan 02 sibling — SubagentType + STAGE_ROSTER + dispatch_subagent shape consumed here)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md Section 7 (StepVerifyResult server-recomputation pattern; SUB-06 mirrors)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — naming convention; this spec adds 8 new state.step.subagent_* events)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic `extra="forbid"` convention)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md`. Sections 1-4 below; Task 2 owns sections 5-8. **Concrete content from 405-CONTEXT.md verbatim.**

    ### Section 1 — File header

    ```
    # Subagent Monitoring (Canonical, v41, Part 2 of 2)

    > **Phase:** 405
    > **Status:** Canonical (v41)
    > **Requirements covered (this file, Part 2):** SUB-05, SUB-06, SUB-07, SUB-08, SUB-09
    > **Sibling spec (Part 1 of 2):** SUBAGENT-MANAGEMENT.md (SUB-01..SUB-04 — dispatch_subagent, whitelist, parallel cap).
    > **Cross-reference spec:** DEVIATION-RULES.md (autonomy inheritance consumes DEV-05/DEV-06; spot-check + crash exhaustion escalate via log_deviation Rule 3 / Rule 4).
    > **Cross-reference spec:** CONTEXT-PROTOCOL.md (Phase 402; CTX-07 task_id survival cross-referenced by SUB-08).
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
    > **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Trailer `STATE-Subagent-Invocation: <invocation_id>` mandatory on every commit inside a subagent session.
    > **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
    ```

    1-paragraph overview: the harness monitors every spawned subagent via three SSE events (`subagent_started` / `subagent_progress` / `subagent_complete`) linked by `parent_task_id`. Returns are structured (typed per `SubagentType`); a 4-layer pure-machine spot-check stack validates each return at completion. Crashes (5 sources) feed a per-`(parent_task_id, subagent_type)` 3-restart counter; the 4th occurrence escalates to Rule 3 / Rule 4. Restart prompts carry a `<prior_crash>` XML block with augmented continuation context. `task_id` survives compaction and Slice-boundary respawn via event-store rehydration. Subagents inherit autonomy from the parent Slice, with optional per-dispatch override.

    ### Section 2 — SSE Event Family (SUB-05)

    Heading: `## SSE Event Family (SUB-05)`.

    Sub-section `### Three core events`:

    Bulleted list with full event-type names:
    - `state.step.subagent_started` — emitted by the daemon dispatch handler immediately after opencode's `task` tool spawn confirms session creation. Carries the `SubagentStarted` payload.
    - `state.step.subagent_progress` — emitted on every TUI-visible event from the child session (`message_end`, `tool_use` start/end, etc. per gsd-2 `processSubagentEventLine` shape). Carries the `SubagentProgress` payload.
    - `state.step.subagent_complete` — emitted when the child session reaches `stop_reason` ∈ {`end_turn`, `tool_use`, `max_tokens`, `error`, `aborted`}. Carries the `SubagentComplete` payload.

    Sub-section `### Pydantic event payloads`:

    Render verbatim:

    ```python
    class SubagentStarted(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str               # ulid; unique per dispatch
        parent_task_id: str              # the parent Slice session's active task_id
        subagent_type: SubagentType
        slice_id: str
        task: str                        # the prompt (bounded ≤8KB; mirrors gsd-2 truncation)
        started_at: datetime             # UTC, ISO-8601
        session_id: str                  # opencode session id for the spawned subagent

    class SubagentProgress(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str
        parent_task_id: str
        kind: Literal["message_end", "tool_use_start", "tool_use_end", "step_event", "other"]
        payload_excerpt: str             # ≤2KB; gsd-2 truncation discipline
        emitted_at: datetime
        session_id: str

    class SubagentComplete(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str
        parent_task_id: str
        subagent_type: SubagentType
        stop_reason: Literal["end_turn", "tool_use", "max_tokens", "error", "aborted"]
        declared_artifacts: list[ArtifactDeclaration]   # see Section 3
        declared_commits: list[str]                     # commit SHAs in worktree branch order
        completed_at: datetime
        session_id: str
        error_message: str | None
    ```

    Cite source: "Field set drawn from 405-CONTEXT.md `<decisions>` 'Subagent typed-spawn surface' + 'Structured return shape registry' subsections."

    Sub-section `### Parent-task linkage`:

    Render verbatim: "Every subagent event carries `parent_task_id`. The daemon's SSE filter subscribes by `parent_task_id` to surface child events on the parent's TUI stream (v9 sidebar + statusline). The daemon projector maintains `in_flight_subagents: dict[parent_task_id, list[InFlightSubagent]]` rebuilt from `subagent_started` / `subagent_complete` / `subagent_crash_detected` events. Cross-references gsd-2 `agent-lifecycle.md` §2.2 `agent.sessionId = sessionManager.getSessionId()` invariant — `parent_task_id` is state's stable cross-process identifier."

    Sub-section `### SSE bus position`:

    "The events live on the daemon's SSE bus (the equivalent of gsd-2's Bus A / tool-call bus, per `cross-layer-communication-map.md`). The plugin's `chat.params` and `tool.execute.after` hooks subscribe and forward to opencode's TUI. v14 implements the daemon SSE bus; v9 (shipped) implements the plugin-side subscriber."

    Sub-section `### Granularity (deferred)`:

    "`SubagentProgress.payload_excerpt` granularity (which child events trigger emission) is recommended at gsd-2's `processSubagentEventLine` shape (every message_end + tool_use start/end). Detailed payload schema deferred to v14."

    ### Section 3 — `SUBAGENT_RETURN_REGISTRY` (SUB-06)

    Heading: `## SUBAGENT_RETURN_REGISTRY (SUB-06)`.

    1-paragraph intro: each `SubagentType` has a registered Pydantic return shape. The central registry `SUBAGENT_RETURN_REGISTRY: dict[SubagentType, type[SubagentReturnBase]]` provides compile-time exhaustiveness (via `assert_never` per Plan 02 Section 4). Mirrors gsd-2's `exhaustive-registry-with-satisfies-constraint.md` pattern with Python typing.

    Sub-section `### Common base class`:

    Render verbatim:

    ```python
    class ArtifactDeclaration(BaseModel):
        model_config = ConfigDict(extra="forbid")
        path: str            # repo-root-relative POSIX
        sha256: str          # full file content hash at write time
        line_count: int

    class SubagentReturnBase(BaseModel):
        model_config = ConfigDict(extra="forbid")
        subagent_type: SubagentType                   # narrowed Literal in per-type subclasses
        parent_task_id: str
        invocation_id: str                            # ulid; the dispatch's unique ID
        declared_artifacts: list[ArtifactDeclaration]
        declared_commits: list[str]                   # commit SHAs in worktree branch order
        stop_reason: Literal["end_turn","tool_use","max_tokens","error","aborted"]
        error_message: str | None
    ```

    Sub-section `### Registry`:

    Render verbatim:

    ```python
    SUBAGENT_RETURN_REGISTRY: dict[SubagentType, type[SubagentReturnBase]] = {
        "researcher": ResearcherReturn,
        "code-mapper": CodeMapperReturn,
        "requirements-analyzer": RequirementsAnalyzerReturn,
        "pattern-mapper": PatternMapperReturn,
        "planner": PlannerReturn,
        "plan-validator": PlanValidatorReturn,
        "plan-checker": PlanCheckerReturn,
        "executor": ExecutorReturn,
        "code-fixer": CodeFixerReturn,
        "test-generator": TestGeneratorReturn,
        "security-auditor": SecurityAuditorReturn,
        "verifier": VerifierReturn,
        "integration-checker": IntegrationCheckerReturn,
        "nyquist-auditor": NyquistAuditorReturn,
    }
    ```

    Sub-section `### Per-type extension example: ExecutorReturn`:

    Render verbatim:

    ```python
    class ExecutorReturn(SubagentReturnBase):
        subagent_type: Literal["executor"]                   # narrowed Literal for type discriminator
        files_modified_actual: list[str]                    # repo-root-relative; spot-check ⊆ frontmatter files_modified
        test_pass_count: int
        test_fail_count: int
    ```

    "The 13 remaining per-type subclasses (ResearcherReturn, CodeMapperReturn, etc.) follow the same shape: `subagent_type` narrowed to a single-element Literal for discriminated-union parsing; extension fields specific to each stage's expected output. v14 authors the remaining models during EXEMPLAR work."

    Sub-section `### Module organization`:

    "Single-source-of-truth: `state_build/subagents/returns.py` exports `SUBAGENT_RETURN_REGISTRY`, `ArtifactDeclaration`, `SubagentReturnBase`. Per-type subclasses live in `state_build/subagents/returns_{stage}.py` (one module per stage roster: `returns_discuss.py`, `returns_plan.py`, `returns_execute.py`, `returns_verify.py`) and re-export to the registry."

    Sub-section `### Compile-time exhaustiveness`:

    "Mirrors Plan 02 Section 4's `assert_never` pattern. CI runs `mypy --strict src/state_build/subagents/` to verify every `SubagentType` Literal value has an entry in `SUBAGENT_RETURN_REGISTRY`. Missing entry → mypy error at type-check time. Diverges from gsd-2's runtime-discovery-with-synthetic-error-fallback pattern (`subagent/index.ts:344-358`)."

    ### Section 4 — 4-Layer Pure-Machine Spot-Check (SUB-06)

    Heading: `## 4-Layer Pure-Machine Spot-Check (SUB-06)`.

    1-paragraph intro: at `subagent_complete` event receipt, the harness runs a deterministic 4-layer stack against the structured return. Each layer pure-machine; any layer fails → distinct `layer` field in the `SubagentSpotCheckFailed` event. Mirrors gsd-2's `process-exit-stop-reason-validation.md` 3-signal pattern extended with state's artifact + commit gates.

    Sub-section `### Layer stack (4-row markdown table)`:

    Render verbatim:

    | Layer | Check | Failure trigger |
    |---|---|---|
    | 1. Process classification | `exit_code == 0 AND stop_reason ∉ {error, aborted}` | gsd-2 `isError` formula (`subagent/index.ts:923`) |
    | 2. Pydantic validate | `SUBAGENT_RETURN_REGISTRY[type].model_validate_json(payload)` (`extra="forbid"`) | unknown fields, type mismatches, missing required fields |
    | 3. Artifact existence | for every `ArtifactDeclaration`: file at `path` exists AND `sha256(file_bytes) == declaration.sha256` AND `count_lines(file) == declaration.line_count` | missing file / hash mismatch / line-count mismatch |
    | 4. Commit existence | for every `commit_sha`: `git rev-parse --verify {sha}^{commit}` exits 0 AND commit is reachable from current worktree branch | missing commit / detached |

    Sub-section `### Failure event payload`:

    Render verbatim:

    ```python
    class SubagentSpotCheckFailed(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str
        parent_task_id: str
        subagent_type: SubagentType
        layer: Literal["process","pydantic","artifact","commit"]
        evidence_excerpt: str            # ≤2KB; gsd-2 truncation discipline
        failed_at: datetime
        session_id: str
    ```

    Event type: `state.step.subagent_spot_check_failed` (registered by Plan 04 in EVENT-TAXONOMY.md).

    Sub-section `### Server-side recomputation discipline`:

    Render verbatim: "**The harness recomputes `overall_success` from layer verdicts; agent-emitted aggregates are rejected.** Mirrors gsd-2's `server-recomputation-of-llm-emitted-fields.md` pattern + Phase 404 PRF `overall_passed` recomputation. The subagent's structured return SHALL NOT include an `overall_success` field; if present, it is ignored (Pydantic `extra='forbid'` rejects at parse time)."

    Sub-section `### Spot-check ↔ crash-recovery counter linkage`:

    Render verbatim: "**Spot-check failure feeds the crash-recovery counter (SUB-07), not the PRF strike chain.** The three independent counters discipline (APG, PRF, DEV per DEVIATION-RULES.md Section 8) is preserved; the subagent restart counter is a fourth, parallel chain owned by this spec. Plan 04's EVENT-TAXONOMY.md amendment registers both `subagent_spot_check_failed` and `subagent_crash_detected` under the BUILD_ONLY_EVENT_PREFIXES — emission-wise distinct, but semantically wired: a layer-N spot-check failure on the same `(parent_task_id, subagent_type)` increments the restart counter via `state.step.subagent_crash_detected` with `crash_source='spot_check'`."

    Sub-section `### Module ownership`:

    "Single-source-of-truth module: `state_build/subagents/spot_check.py`. Exports: `run_spot_check_stack(complete_event: SubagentComplete) -> SpotCheckResult`. v14 implements; daemon middleware invokes on every `subagent_complete` event receipt."

    <quality_scan>
      <code_to_reuse>
        - Known: 405-CONTEXT.md `<decisions>` "Structured return shape registry (SUB-06 expanded)" + "Spot-check protocol (SUB-06 expanded)" — verbatim source for Sections 3-4.
        - Known: Plan 02 SUBAGENT-MANAGEMENT.md Sections 3-4 — SubagentType + STAGE_ROSTER + assert_never pattern consumed here; do NOT re-define.
        - Known: 404 PROOF-GATE.md Section 7 — StepVerifyResult server-recomputation pattern mirrored.
        - Grep pattern: `grep -nE "extra=\"forbid\"" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/405-CONTEXT.md | head -20` — locates verbatim Pydantic ConfigDict pattern.
        - Grep pattern: `grep -nE "ArtifactDeclaration|SubagentReturnBase|SUBAGENT_RETURN_REGISTRY" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/405-CONTEXT.md` — locates source.
      </code_to_reuse>
      <docs_to_consult>
        - 405-CONTEXT.md `<decisions>` Structured return shape registry — Section 3 source.
        - 405-CONTEXT.md `<decisions>` Spot-check protocol — Section 4 source.
        - 405-CONTEXT.md `<specifics>` "Spot-check layered stack mirrors 404's tool.execute.before composition" — rationale prose.
        - gsd-2 `process-exit-stop-reason-validation.md` — 3-signal pattern precedent.
        - gsd-2 `server-recomputation-of-llm-emitted-fields.md` — recomputation discipline.
        - gsd-2 `agent-lifecycle.md` §2.2 — parent_task_id invariant.
        - Phase 404 PROOF-GATE.md Section 7 — overall_passed server-recomputation precedent.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's spot-check unit tests assert against the Pydantic registry rendered here.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 280)}' \
        && grep -qE "^# Subagent Monitoring" "$F" \
        && grep -qE "^## SSE Event Family" "$F" \
        && grep -qE "^## SUBAGENT_RETURN_REGISTRY" "$F" \
        && grep -qE "^## 4-Layer Pure-Machine Spot-Check" "$F" \
        && grep -q "SubagentStarted" "$F" \
        && grep -q "SubagentProgress" "$F" \
        && grep -q "SubagentComplete" "$F" \
        && grep -q "SubagentSpotCheckFailed" "$F" \
        && grep -q "ArtifactDeclaration" "$F" \
        && grep -q "SubagentReturnBase" "$F" \
        && grep -q "SUBAGENT_RETURN_REGISTRY" "$F" \
        && grep -q "ExecutorReturn" "$F" \
        && grep -q "state.step.subagent_started" "$F" \
        && grep -q "state.step.subagent_progress" "$F" \
        && grep -q "state.step.subagent_complete" "$F" \
        && grep -q "state.step.subagent_spot_check_failed" "$F" \
        && grep -q "state_build/subagents/returns.py" "$F" \
        && grep -q "state_build/subagents/spot_check.py" "$F" \
        && grep -q 'model_config = ConfigDict(extra="forbid")' "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[1]] Three SSE Pydantic event payloads (SubagentStarted, SubagentProgress, SubagentComplete) render verbatim with all listed fields.
    - [check: must_haves.truths[2]] Event-type strings `state.step.subagent_started/progress/complete/spot_check_failed` rendered as fully qualified names.
    - [check: must_haves.truths[3]] Parent-task linkage discipline rendered; gsd-2 agent-lifecycle.md §2.2 cited.
    - [check: must_haves.truths[4]] SUBAGENT_RETURN_REGISTRY dict renders verbatim with all 14 entries keyed by SubagentType.
    - [check: must_haves.truths[5]] ArtifactDeclaration + SubagentReturnBase render verbatim with `extra="forbid"`.
    - [check: must_haves.truths[6]] ExecutorReturn per-type extension example renders verbatim; module organization (`returns_*.py` per stage) documented.
    - [check: must_haves.truths[7]] 4-row spot-check markdown table renders with all four layers; failure-triggers column populated.
    - [check: must_haves.truths[8]] Server-side recomputation discipline rendered; gsd-2 + 404 PRF cite included.
    - [check: must_haves.truths[9]] SubagentSpotCheckFailed Pydantic event renders verbatim.
    - [check: must_haves.truths[20]] No `GSD-` literal in the file.
  </acceptance_criteria>

  <done>
    SUBAGENT-MONITORING.md exists with sections 1-4; file ≥280 lines (Task 2 brings to ≥650); verify-block bash passes; no `GSD-` literal.
  </done>
</task>

<task type="auto">
  <name>Task 2: Author SUBAGENT-MONITORING.md sections 5-8 (5-source crash taxonomy SUB-07, <prior_crash> continuation, task_id survival SUB-08, daemon-down orphan reconciliation, autonomy inheritance SUB-09)</name>
  <files>
    .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md (the file Task 1 just authored — append sections 5-8 below)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Crash semantics (SUB-07 expanded)" subsection (verbatim source for Section 5 + 5-source taxonomy + restart counter)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Continuation context on restart" subsection (verbatim source for Section 6 <prior_crash> XML)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Counter survival across compaction + Slice-boundary respawn (SUB-08 expanded)" subsection (verbatim source for Section 7)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Daemon-down + in-flight subagent reconciliation" subsection (verbatim source for Section 7's orphan flow)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Autonomy inheritance (SUB-09 expanded)" subsection (verbatim source for Section 8)
    - .planning/milestones/v41/REQUIREMENTS.md lines 114-117 (SUB-07, SUB-08, SUB-09 verbatim)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (the Plan 01 sibling — autonomy table consumed by SUB-09; Rule 3/4 escalation by SUB-07)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (full file — CompactionSnapshot extended; CTX-07 cross-referenced)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — naming convention for crash/restart/orphan events)
  </read_first>

  <action>
    Append sections 5-8 to `.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md`. **Concrete content from 405-CONTEXT.md verbatim.**

    ### Section 5 — 5-Source Crash Taxonomy + 3-Restart Counter (SUB-07)

    Heading: `## 5-Source Crash Taxonomy + 3-Restart Counter (SUB-07)`.

    1-paragraph intro: a "crash" for SUB-07's 3-restart counter is any of five distinct sources. Each emits the same `SubagentCrashDetected` event payload with a `crash_source` Literal discriminator. The per-`(parent_task_id, subagent_type)` counter is the fourth independent chain (alongside APG / PRF / DEV).

    Sub-section `### Five crash sources (markdown table)`:

    Render verbatim:

    | Source | Trigger |
    |---|---|
    | `process_exit` | child opencode `task` process `exit_code != 0` (gsd-2 isError) |
    | `stop_reason` | last `message_end` event has `stop_reason ∈ {error, aborted}` (gsd-2) |
    | `spot_check` | any spot-check layer (1-4 from Section 4) fails |
    | `sse_silence` | no `subagent_progress` SSE event received for > `progress_timeout_s` (default 180s, configurable via Slice frontmatter `subagent: {progress_timeout_s: int}`) |
    | `parent_task_error` | parent-side `task` MCP tool call returns error (provider HTTP failure, auth-refresh mid-call, mode-gate violation) |

    Sub-section `### Pydantic event payload`:

    Render verbatim:

    ```python
    class SubagentCrashDetected(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str
        parent_task_id: str
        subagent_type: SubagentType
        crash_source: Literal["process_exit","stop_reason","spot_check","sse_silence","parent_task_error"]
        restart_number: int                                  # 1..3; 4 triggers escalation
        evidence_excerpt: str                                # ≤2KB
        detected_at: datetime
        session_id: str
    ```

    Event type: `state.step.subagent_crash_detected`. Registered by Plan 04.

    Sub-section `### Restart counter scope`:

    Render verbatim: "**Per-`(parent_task_id, subagent_type)` tuple.** Diverges from per-`invocation_id` because the agent should not get a fresh 3-restart budget by re-invoking the same subagent type with a slightly different prompt for the same logical work unit. Mirrors Phase 404's per-`(task_id, check_id)` strike discipline."

    Sub-section `### After-3-restart escalation`:

    Render verbatim:

    "After 3 restarts on the same tuple, the parent agent MUST call `log_deviation` with `rule_id=3` (blocking issue) or `rule_id=4` (architectural — if the failure indicates a structural problem). The escalation event is `state.step.subagent_restart_exhausted` with payload:"

    ```python
    class SubagentRestartExhausted(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str                                   # most recent invocation
        parent_task_id: str
        subagent_type: SubagentType
        terminal_crash_source: Literal["process_exit","stop_reason","spot_check","sse_silence","parent_task_error"]
        triggered_at: datetime
        session_id: str
    ```

    "The harness emits this event AND surfaces the escalation prompt to the parent agent through opencode's TUI; the parent agent's next `log_deviation(rule_id=3|4)` call closes the chain. Cross-reference: DEVIATION-RULES.md Section 4 (cross-validation) accepts the elevated rule_id without re-promotion."

    Sub-section `### Successful restart event`:

    Render verbatim:

    ```python
    class SubagentRestart(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str                                   # NEW invocation id for the retry
        previous_invocation_id: str                          # the failed invocation
        parent_task_id: str
        subagent_type: SubagentType
        restart_number: int                                  # 1..3
        crash_source: Literal["process_exit","stop_reason","spot_check","sse_silence","parent_task_error"]
        triggered_at: datetime
        session_id: str                                      # new session for the retry
    ```

    Event type: `state.step.subagent_restart`.

    ### Section 6 — `<prior_crash>` Continuation Context (SUB-07 expanded)

    Heading: `## <prior_crash> Continuation Context`.

    1-paragraph intro: restart prompts use an augmented original prompt with a `<prior_crash>` XML block. Mirrors Phase 402 reinject body XML discipline. **Diverges from gsd-2** — gsd-2's parallel-mode retry uses the original prompt verbatim; state's augmented form prevents looping on the same failure mode.

    Sub-section `### XML structure (verbatim)`:

    Render verbatim:

    ```xml
    <prior_crash>
      <restart_number>2 of 3</restart_number>
      <crash_source>spot_check</crash_source>
      <prior_evidence>
        <!-- ≤2KB excerpt of failed stdout / spot-check failure detail -->
        Layer 3 (artifact_existence) failed: declared path
        `src/state_build/snapshot/compaction.py` does not exist; agent claimed
        to write but file is absent at SHA-256 verification.
      </prior_evidence>
      <remediation_hint>
        Verify file path against the worktree before declaring artifacts; ensure
        git add + commit landed before returning.
      </remediation_hint>
    </prior_crash>

    <original_task>
      <!-- verbatim original prompt -->
    </original_task>
    ```

    Sub-section `### remediation_hint sourcing`:

    Render verbatim: "**`remediation_hint` is harness-default per `crash_source`** (single-source-of-truth lookup table `state_build/subagents/remediation_hints.py`). Planner MAY override per Slice frontmatter `subagent: {remediation_hints: dict[CrashSource, str]}` — narrowing-only NOT applicable here (hints are informational, not security gates). The default hint table covers all five `crash_source` values; v14 finalizes the exact default strings during EXEMPLAR work."

    Sub-section `### Worktree-rollback over partial-artifact-preservation (v1)`:

    Render verbatim: "**Partial-artifact preservation rejected for v1.** Worktree rollback on subagent restart is the simpler invariant: `declared_artifacts` that DID pass spot-check on the previous attempt are NOT preserved separately; the restarted subagent re-evaluates from scratch with the augmented prompt. Mirrors gsd-2's 'fresh prompt on parallel-mode retry' + Phase 403's 'replan recomputes from inputs' idempotency principle. Revisit post-v17 if observed restart cycles show systematic partial-success patterns."

    Sub-section `### Module ownership`:

    "Single-source-of-truth: `state_build/subagents/restart.py` exports `build_restart_prompt(original_task: str, crash: SubagentCrashDetected) -> str`. v14 implements; the daemon-side restart handler invokes when emitting `state.step.subagent_restart` events. The XML block is constructed in-memory and injected into the new opencode session via the `task` tool's prompt argument."

    ### Section 7 — `task_id` Survival + Daemon-Down Orphan Reconciliation (SUB-08)

    Heading: `## task_id Survival + Daemon-Down Orphan Reconciliation (SUB-08)`.

    1-paragraph intro: SUB-08 cross-references CTX-07 (Phase 402 identifier-survival contract). The subagent restart counter + in-flight subagent list survive compaction and Slice-boundary respawn via event-store rehydration. Daemon-down + orphan reconciliation extends the same pattern to daemon restart territory.

    Sub-section `### CompactionSnapshot extension`:

    Render verbatim:

    ```python
    class CompactionSnapshot(BaseModel):
        model_config = ConfigDict(extra="forbid")
        # ... existing fields from Phase 402 ...
        # Phase 405 additions:
        subagent_restart_counters: dict[str, int]            # key = "{parent_task_id}|{subagent_type}", value = restart count
        in_flight_subagents: list[InFlightSubagent]          # for Slice-boundary spawn
    ```

    "These two fields extend the Phase 402 `CompactionSnapshot` Pydantic model. Reinject payload carries them; daemon projector consumes on snapshot load."

    Sub-section `### Slice-boundary spawn`:

    Render verbatim: "The new session's `chat.params` metadata includes the prior counters; plugin's `chat.message` hook (or first `tool.execute.before` fire) writes them to plugin-local hot state via the daemon HTTP middleware. Cross-references CTX-07. The same projector pattern handles intra-Slice compaction reinject AND Slice-boundary respawn — both paths rehydrate from event-store."

    Sub-section `### Subagent continuation on daemon restart`:

    Render verbatim: "**Subagents continue independently** when daemon restarts mid-execution. Mirrors Phase 402's 'in-flight subagents finish independently' decision for parent-compaction inheritance. Subagent processes are managed by opencode's `task` tool, not state-daemon; daemon restart doesn't kill them."

    Sub-section `### Orphan reconciliation flow (numbered)`:

    Render verbatim 6-step protocol:

    1. **Replay event-store** to rebuild `in_flight_subagents: dict[invocation_id, InFlightSubagent]` from any `state.step.subagent_started` event WITHOUT a paired `state.step.subagent_complete` / `state.step.subagent_crash_detected` event.
    2. **Probe opencode** for each orphan: HTTP call to opencode's session API with the orphan's session_id / task_id; ask opencode whether the task is still running.
    3. **If opencode reports still running** → re-subscribe to opencode SSE for that session; wait for natural completion event.
    4. **If opencode reports done but no event was received** → reconstruct from opencode's session log (replay the session's recorded events); emit the missing `subagent_complete` event from the reconstruction.
    5. **If opencode reports the task gone (lost)** → emit `state.step.subagent_orphan_detected` event (payload below) with `last_known_state="gone"`.
    6. **Persistent orphan** (still unresolved after Slice-boundary spawn) → surface as DEV-04 Rule 4 human-gate via opencode `question` tool with the orphan details and a recovery alternatives payload pre-authored as `[abort_slice, retry_subagent, manual_resolve]`.

    Sub-section `### Pydantic event + in-flight payloads`:

    Render verbatim:

    ```python
    class SubagentOrphanDetected(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str
        parent_task_id: str
        subagent_type: SubagentType
        last_known_state: Literal["running","unknown","gone"]
        detected_at: datetime

    class InFlightSubagent(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invocation_id: str
        parent_task_id: str
        subagent_type: SubagentType
        started_at: datetime
        last_progress_at: datetime | None
    ```

    Event type: `state.step.subagent_orphan_detected`.

    Sub-section `### HRN-07 guarantee preservation`:

    "Phase 406's HRN-07 'harness state fully reconstructable from event store' guarantee is preserved: every transition emits an event; replay rebuilds state. Daemon restart-safe via the rebuild path. The orphan reconciliation flow is part of the daemon resume handler; v14 implements at `state_build/subagents/orphan_reconcile.py`."

    ### Section 8 — Autonomy Inheritance from Parent Slice (SUB-09)

    Heading: `## Autonomy Inheritance from Parent Slice (SUB-09)`.

    1-paragraph intro: SUB-09 consumes DEVIATION-RULES.md's DEV-05 (tiered autonomy) + DEV-06 (per-Slice override). The parent Slice's effective autonomy propagates to every spawned subagent via the `dispatch_subagent` payload. The daemon middleware builds the opencode `task` tool invocation with the inherited autonomy injected into the child session's context.

    Sub-section `### 3-step inheritance flow`:

    Render verbatim:

    1. **Parent's effective autonomy** = `Slice.frontmatter.autonomy ?? milestone.autonomy_default` (DEV-06 precedence rule from DEVIATION-RULES.md Section 6).
    2. **Per-dispatch override** allowed: `DispatchSubagent.{single,parallel,chain}[i].autonomy: Literal["tiered","full-yolo","conservative"] | None`. If set, the child uses the override; if `None`, inherits the parent's effective autonomy. The override CAN move stricter (parent `--tiered`, child `--conservative`) OR looser (parent `--tiered`, child `--full-yolo`) — same direction-rule as DEV-06 Slice override (narrowing-only does NOT apply to autonomy; autonomy is policy not capability).
    3. **Grandchild recursion**: a child subagent's `dispatch_subagent` calls (for grandchildren) recompute effective autonomy at their session boundary; grandchildren inherit from the child's effective autonomy, **not from the original parent**. Each session boundary applies the same `frontmatter ?? parent_effective` rule.

    Sub-section `### Rule-4 always-stop preservation`:

    Render verbatim: "**Rule 4 always-stop is preserved across inheritance.** Even if a grandchild's effective autonomy is `--full-yolo`, a `log_deviation(rule_id=4)` from the grandchild still synchronously renders opencode `question` (DEVIATION-RULES.md Section 2 structural-not-policy guarantee). Inheritance affects the autonomy mode's first three columns (human-verify / decision / human-action behaviors); the 4th column (Rule 4) is structural and cannot be inherited away."

    Sub-section `### Implementation surface`:

    Render verbatim: "When the daemon middleware builds the opencode `task` tool invocation, it injects the child's effective autonomy into the child session's environment via the `chat.params` hook (plugin-side context-block builder). The autonomy block is a structured `<autonomy>` XML annotation in the child's chat.params metadata; the plugin reads it on first `chat.message` fire and registers it with the daemon's autonomy projector. Mirrors gsd-2's `before-agent-start-context-assembly.md` block-builder shape — gsd-2 has no equivalent autonomy-inheritance block, so state's discipline is stricter."

    Sub-section `### Module ownership`:

    "Single-source-of-truth: `state_build/subagents/autonomy.py` exports `compute_effective_autonomy(parent_effective, override) -> AutonomyMode`. v14 implements; daemon middleware invokes at `dispatch_subagent` time; plugin-side `chat.params` hook injects the result."

    Sub-section `### Cross-reference to DEVIATION-RULES.md`:

    "Plan 01 of Phase 405 (DEVIATION-RULES.md) is the authoritative source for the tiered autonomy table (Section 6) and the per-Slice override mechanism (Section 6). This spec consumes that table verbatim; do not re-render it here. Forward-pointer to `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md` is the canonical citation."

    <quality_scan>
      <code_to_reuse>
        - Known: 405-CONTEXT.md `<decisions>` Crash semantics, Continuation context, Counter survival, Daemon-down + in-flight subagent reconciliation, Autonomy inheritance — all rendered verbatim across Sections 5-8.
        - Known: Plan 01 DEVIATION-RULES.md Section 6 — tiered autonomy table; SUB-09 forward-references rather than re-renders.
        - Known: Phase 402 CONTEXT-PROTOCOL.md — CompactionSnapshot Pydantic model; Section 7 extends with 2 new fields.
        - Grep pattern: `grep -nE "InFlightSubagent|SubagentOrphan|SubagentRestart" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/405-CONTEXT.md` — locates source.
        - Grep pattern: `grep -nE "compute_effective_autonomy|autonomy_default" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/405-CONTEXT.md` — autonomy module shape.
      </code_to_reuse>
      <docs_to_consult>
        - 405-CONTEXT.md `<decisions>` Crash semantics (SUB-07 expanded) — Section 5 source.
        - 405-CONTEXT.md `<decisions>` Continuation context on restart — Section 6 source.
        - 405-CONTEXT.md `<decisions>` Counter survival across compaction + Slice-boundary respawn — Section 7 source.
        - 405-CONTEXT.md `<decisions>` Daemon-down + in-flight subagent reconciliation — Section 7 orphan flow source.
        - 405-CONTEXT.md `<decisions>` Autonomy inheritance (SUB-09 expanded) — Section 8 source.
        - 405-CONTEXT.md `<specifics>` "Augmented restart prompt (not fresh) diverges from gsd-2" — rationale prose for Section 6.
        - 405-CONTEXT.md `<deferred>` Pre-authored `alternatives` for subagent_orphan_detected — Section 7 step 6 alternatives shape.
        - DEVIATION-RULES.md Section 2 + Section 6 — Rule-4 structural-not-policy + autonomy table; forward-referenced by Section 8.
        - Phase 402 CONTEXT-PROTOCOL.md — CompactionSnapshot precedent; Section 7 extension.
        - gsd-2 `before-agent-start-context-assembly.md` — context-block builder pattern.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec).
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 650)}' \
        && grep -qE "^## 5-Source Crash Taxonomy" "$F" \
        && grep -qE "^## <prior_crash> Continuation Context" "$F" \
        && grep -qE "^## task_id Survival" "$F" \
        && grep -qE "^## Autonomy Inheritance from Parent Slice" "$F" \
        && grep -q "SubagentCrashDetected" "$F" \
        && grep -q "SubagentRestart" "$F" \
        && grep -q "SubagentRestartExhausted" "$F" \
        && grep -q "SubagentOrphanDetected" "$F" \
        && grep -q "InFlightSubagent" "$F" \
        && grep -q "process_exit" "$F" \
        && grep -q "stop_reason" "$F" \
        && grep -q "spot_check" "$F" \
        && grep -q "sse_silence" "$F" \
        && grep -q "parent_task_error" "$F" \
        && grep -q "progress_timeout_s" "$F" \
        && grep -q "subagent_restart_counters" "$F" \
        && grep -q "in_flight_subagents" "$F" \
        && grep -q "<prior_crash>" "$F" \
        && grep -q "<original_task>" "$F" \
        && grep -q "remediation_hint" "$F" \
        && grep -q "state_build/subagents/remediation_hints.py" "$F" \
        && grep -q "state_build/subagents/restart.py" "$F" \
        && grep -q "state_build/subagents/orphan_reconcile.py" "$F" \
        && grep -q "state_build/subagents/autonomy.py" "$F" \
        && grep -q "abort_slice" "$F" \
        && grep -q "retry_subagent" "$F" \
        && grep -q "manual_resolve" "$F" \
        && grep -q "CompactionSnapshot" "$F" \
        && grep -q "DEVIATION-RULES.md" "$F" \
        && grep -q "CTX-07" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[10]] 5-source crash taxonomy markdown table renders with all five sources + triggers verbatim.
    - [check: must_haves.truths[11]] SubagentCrashDetected Pydantic event renders with 8 fields including `restart_number: int  # 1..3; 4 triggers escalation`.
    - [check: must_haves.truths[12]] Restart counter scope per-(parent_task_id, subagent_type) documented with gaming-prevention rationale.
    - [check: must_haves.truths[13]] After-3-restart escalation via log_deviation rule_id=3|4 documented; SubagentRestartExhausted event rendered.
    - [check: must_haves.truths[14]] <prior_crash> XML structure renders verbatim with 4 sub-elements + <original_task> wrapper.
    - [check: must_haves.truths[15]] Worktree-rollback-over-partial-artifact-preservation rendered as v1 invariant.
    - [check: must_haves.truths[16]] CompactionSnapshot extension with subagent_restart_counters + in_flight_subagents fields; CTX-07 cross-reference present.
    - [check: must_haves.truths[17]] 6-step orphan reconciliation flow renders verbatim; SubagentOrphanDetected + InFlightSubagent Pydantic models rendered; pre-authored [abort_slice, retry_subagent, manual_resolve] alternatives.
    - [check: must_haves.truths[18]] 3-step autonomy inheritance flow renders; Rule-4 always-stop preservation note; grandchild recursion rule.
    - [check: must_haves.truths[19]] Mode-isolation note rendered.
    - [check: must_haves.truths[20]] No `GSD-` literal in the file.
    - [check: must_haves.artifacts[0]] File at the spec'd path with min_lines: 650.
  </acceptance_criteria>

  <done>
    SUBAGENT-MONITORING.md complete at ≥650 lines; sections 1-8 render per Tasks 1+2; verify-block bash passes; no `GSD-` literal.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

```bash
F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md

for section in \
  "^# Subagent Monitoring" \
  "^## SSE Event Family" \
  "^## SUBAGENT_RETURN_REGISTRY" \
  "^## 4-Layer Pure-Machine Spot-Check" \
  "^## 5-Source Crash Taxonomy" \
  "^## <prior_crash> Continuation Context" \
  "^## task_id Survival" \
  "^## Autonomy Inheritance from Parent Slice"; do
  grep -qE "$section" "$F" || { echo "MISSING: $section"; exit 1; }
done

wc -l "$F" | awk '{ if ($1 < 650) { print "LINE_COUNT_FAIL: " $1; exit 1 } }'
! grep -qE '\bGSD-' "$F" || { echo "GSD_NAMING_VIOLATION"; exit 1; }

for term in \
  'SubagentStarted' \
  'SubagentProgress' \
  'SubagentComplete' \
  'SubagentSpotCheckFailed' \
  'SubagentCrashDetected' \
  'SubagentRestart' \
  'SubagentRestartExhausted' \
  'SubagentOrphanDetected' \
  'InFlightSubagent' \
  'SUBAGENT_RETURN_REGISTRY' \
  'ArtifactDeclaration' \
  'process_exit' \
  'sse_silence' \
  'parent_task_error' \
  'progress_timeout_s' \
  '<prior_crash>' \
  'subagent_restart_counters' \
  'state_build/subagents/returns.py' \
  'state_build/subagents/spot_check.py' \
  'state_build/subagents/restart.py' \
  'state_build/subagents/orphan_reconcile.py' \
  'state_build/subagents/autonomy.py'; do
  grep -q "$term" "$F" || { echo "MISSING_TERM: $term"; exit 1; }
done

echo "SUBAGENT-MONITORING.md verification OK"
```
</verification>

<success_criteria>
- SUBAGENT-MONITORING.md exists at the spec'd path with ≥ 650 lines.
- All 8 sections render verbatim per 405-CONTEXT.md.
- SUB-05..SUB-09 fully covered.
- All 8 new event types (subagent_started, subagent_progress, subagent_complete, subagent_spot_check_failed, subagent_crash_detected, subagent_restart, subagent_restart_exhausted, subagent_orphan_detected) named (Plan 04 registers in EVENT-TAXONOMY.md).
- No `GSD-` literal in the file.
- All Pydantic class definitions render with `model_config = ConfigDict(extra="forbid")`.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/405/03-subagent-monitoring-spec-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: final line count, sections rendered, requirement coverage (SUB-05..SUB-09 all addressed), naming-discipline verification.
</output>
