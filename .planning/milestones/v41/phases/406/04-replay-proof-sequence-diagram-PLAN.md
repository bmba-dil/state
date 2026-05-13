---
phase: 406
plan: 04
type: execute
wave: 4
depends_on:
  - "406-03"
files_modified:
  - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
autonomous: false
requirements:
  - HRN-07
  - HRN-08

must_haves:
  truths:
    - "HARNESS-ARCHITECTURE.md exists with §0 + §1 + §2 + §3 + §4 (from Plans 01, 02, 03). THIS plan (Plan 04) appends §5 + §6 — without modifying §0–§4. The file becomes the canonical Phase 406 rollup at this plan's completion."
    - "§5 heading is rendered verbatim: `## §5 Event-Replay Reconstruction Proof (HRN-07)`. Sub-sections cover (in order): §5.1 replay-input enumeration (5-table breakdown), §5.2 reconstruction protocol (5-step numbered), §5.3 worked example (daemon-restart-mid-run-slice hard case), §5.4 daemon restart-safety statement closing HRN-07."
    - "§5.1 renders the 5-category replay-input enumeration table verbatim from 406-CONTEXT.md `<decisions>` 'Event-replay reconstruction (HRN-07)' subsection. Columns: Category | Events | Owning spec. All 5 categories rendered: (1) Slice-stage chain (4 events), (2) Plan-lifecycle chain (9 events), (3) Counter chains (~17 events across APG / PRF / DEV / SUB), (4) Scope chain (~6 events), (5) Umbrella + context (~4 events). Total ~30 event types."
    - "§5.1 Category-1 row enumerates `state.slice.design_completed`, `state.slice.research_completed`, `state.slice.run_completed`, `state.slice.verify_completed` (4 events) with owning spec `402 SLICE-CYCLE.md` per 402 v40-vocab carry-forward (design / research / run / verify stages, NOT discuss / plan / execute / verify per 406-CONTEXT.md `<decisions>` 'Vocabulary carry-forward (402)' subsection)."
    - "§5.1 Category-2 row enumerates all 9 plan-lifecycle events from 403 STEP-EVENTS.md: `state.step.plan_authored`, `plan_edit`, `plan_edit_blocked`, `checkpoint_auto_resolved`, `checkpoint_human_action_pending`, `checkpoint_human_action_resolved`, `state.step.renamed`, `state.step.added`, `state.step.removed`."
    - "§5.1 Category-3 row enumerates the 4 counter chains with their events: APG (`paralysis_event`); PRF (`gate_strike`, `gate_resolved`, `step_verify_completed`, `slice_verify_completed`); DEV (`deviation_logged`, `deviation_classification_rejected`, `deviation_resolution_recorded`, `deviation_cap_exceeded`); SUB (`subagent_started`, `subagent_progress`, `subagent_complete`, `subagent_spot_check_failed`, `subagent_crash_detected`, `subagent_restart`, `subagent_restart_exhausted`, `subagent_orphan_detected`)."
    - "§5.1 Category-4 row enumerates the scope chain: `scope_check`, `scope_deviation`, `scope_deviation_request`, `scope_deviation_resolved`, `subagent_whitelist_violation`, `subagent_cap_expansion_rejected`. Owning specs: 404 SRP + 405 SUB."
    - "§5.1 Category-5 row enumerates the umbrella + context events: `state.harness.intervention` (THIS phase from §4), `compaction.snapshot_taken`, `compaction.reinject_completed`, `harness.context_meter`. Owning specs: 406 + 402."
    - "§5.1 includes a closing 'Total event types: ~30' note + the cross-reference 'For each event type → Pydantic class → owning spec. The table IS the HRN-07 enumeration.'"
    - "§5.2 renders the 5-step reconstruction protocol verbatim from 406-CONTEXT.md `<decisions>` 'Event-replay reconstruction (HRN-07)' subsection: (1) Daemon boot + single-writer SQLite facade open; (2) Load latest CompactionSnapshot per active Slice + seed projector state; (3) Replay events forward from first_kept_entry_id with per-chain reducers (APG / PRF / DEV / SUB / intervention chain); (4) Reconcile orphan subagents per Phase 405 SUB-08 6-step protocol; (5) Resume plugin hooks (chat.params re-injects + tool.execute.before re-attaches 6-layer write-block stack)."
    - "§5.2 step 3 renders the 5 per-chain reducer module paths verbatim: `state_build/paralysis/counter.py` (APG per-task consecutive read-only count); `state_build/proof/counter.py` (PRF per-(task_id, check_id) strike chain); `state_build/deviation/counter.py` (DEV per-(task_id, rule_id, issue_signature) attempt chain); `state_build/subagents/restart_counter.py` (SUB per-(parent_task_id, subagent_type) restart chain); `state_build/harness/intervention/projector.py` (intervention chain per-tier accumulation)."
    - "§5.2 step 5 'Resume plugin hooks' subsection enumerates: (a) `chat.params` re-injects the latest reinject payload (CTX-06); (b) `tool.execute.before` re-attaches the 6-layer write-block stack (per Phase 405 SUBAGENT-MANAGEMENT.md §5; subsequently extended to 7 layers in §2 of THIS spec — clarify if 6 vs 7 layer count matches 406-CONTEXT.md verbatim, and use the CONTEXT.md value)."
    - "§5.3 renders the worked example verbatim from 406-CONTEXT.md `<decisions>` 'Reconstruction protocol — worked example' subsection. Hard case: daemon restart mid-`run-slice` with 2 in-flight subagents, paralysis counter at 4 of 6 on `task-3`, last `CompactionSnapshot` taken 30s before restart. Demonstrates: snapshot rehydration (paralysis counter `task-3 → 4`, restart counters `task-2|researcher → 1`, `task-2|pattern-mapper → 0`); replay catches 6 additional `subagent_progress` events post-snapshot for both in-flight subagents; orphan probe — opencode reports both still running, daemon re-subscribes to SSE; plugin hook resume — chat.params re-injects with `<prior_crash>` block if any restart-chain has fired."
    - "§5.3 includes a Mermaid `sequenceDiagram` (or `flowchart TB`) rendering the restart flow with at least these participants/nodes: SQLite (events.sqlite), Daemon, Projector, Plugin (opencode), Subagent-1 (researcher), Subagent-2 (pattern-mapper). At minimum 10 numbered messages showing snapshot load → event replay → orphan probe → re-subscribe → hook resume sequence."
    - "§5.4 closes HRN-07 with a verbatim statement: 'The five-step protocol + worked example demonstrate that harness state is fully reconstructable from the event store. Daemon restart at any point during a Slice's execution rehydrates without loss of (a) per-chain counters (APG/PRF/DEV/SUB), (b) in-flight subagent registrations, (c) plugin-hook write-block stack state. Append-only invariant of the event store (PROJECT.md cardinal rule) + single-writer SQLite facade (gsd-2 carry-forward pattern) + per-aggregate seq ordering guarantee replay determinism.'"
    - "§6 heading is rendered verbatim: `## §6 Full-Slice Lifecycle Sequence Diagram (HRN-08)`. Sub-sections: §6.1 Exemplar Slice identification (the `compaction-snapshot-schema` Slice from 403 EXEMPLAR-stepNPLAN.md), §6.2 Full-Slice Mermaid sequence diagram (design → research → run → verify → close with every event emitted + every harness intervention point), §6.3 Event count + intervention count tabulation, §6.4 Phase-402–405 cross-reference per stage."
    - "§6.1 names the exemplar Slice verbatim from 406-CONTEXT.md `<decisions>` 'HRN-08 exemplar Slice — reuse 403 EXEMPLAR-stepNPLAN.md' subsection: the `compaction-snapshot-schema` Slice with 1 Step containing 3 tasks (RED test → GREEN implement → `checkpoint:decision` for orjson flag). Cites CTX-05 (CompactionSnapshot model), STP-04 (`<task>` sub-tag), PRF (must_haves evaluator dispatch), DEV-05 (autonomy interaction on `checkpoint:decision` task)."
    - "§6.2 renders ONE Mermaid `sequenceDiagram` block walking the full Slice lifecycle. Participants at minimum: Daemon, Opencode-session (or 'Agent'), Event-store, Plugin-hooks (or Chat-params + Tool-execute-before + Session-compacting as separate participants), state-build-MCP, Subagent-N (≥1). The diagram covers the four stages design-slice → research-slice → run-slice (with one Step's 3 tasks) → verify-slice → close. Minimum event-fire count: 25 (HRN-08 literal — 'every event emitted'). Minimum intervention-point count: 4 (one tier-1 advisory, one tier-2 block, one tier-3 reinject, one tier-4 human-gate to exercise the full ladder)."
    - "§6.2 intervention-point coverage requirement: the sequence diagram MUST show at least one emission of `state.harness.intervention` at each of the four tiers — (tier-1 advisory: paralysis-counter cross during Read-heavy research-slice stage); (tier-2 block: PAP-05 immutability block on attempted edit to must_haves); (tier-3 reinject: emergency context threshold at 25% on run-slice); (tier-4 human-gate: the `checkpoint:decision` task on orjson flag selection)."
    - "§6.3 renders a tabulation block: 'Event-fire count: ≥25; intervention-point count: ≥4 (one per tier 1/2/3/4); Slice-stage events: 4 (design/research/run/verify completed); Step-lifecycle events: 3+ (plan_authored, checkpoint_human_action_resolved, etc.); Counter events: ≥4 (≥1 paralysis_event, ≥1 gate_strike or gate_resolved, ≥1 subagent_started/complete pair).' Numbers MAY be exceeded — the floor is asserted."
    - "§6.4 renders a stage-by-stage cross-reference table mapping each Slice stage to the canonical 402–405 spec sections it consumes: design-slice → SLICE-CYCLE.md (SLC-02 design artifacts); research-slice → SLICE-CYCLE.md (SLC-03 4-stage plan-slice pipeline) + STEP-PLAN-FORMAT.md + PLAN-AS-PROMPT.md; run-slice → STEP-PLAN-FORMAT.md + PROOF-GATE.md + ANALYSIS-PARALYSIS-GUARD.md + SCOPE-PROHIBITION.md + DEVIATION-RULES.md + SUBAGENT-MANAGEMENT.md + SUBAGENT-MONITORING.md + CONTEXT-PROTOCOL.md; verify-slice → SLICE-CYCLE.md (SLC-05 N-VERIFICATION.md) + PROOF-GATE.md (PRF-03 Slice-end gate)."
    - "§6 closes with a 'HRN-08 satisfied' assertion paragraph: 'The sequence diagram in §6.2 walks one full Slice from spawn to close, showing every event emitted (~25–30 events) and every harness intervention point. The exemplar Slice is canonically authored in 403 EXEMPLAR-stepNPLAN.md so this diagram cites literal task names. HRN-08 literal: every event emitted and every harness intervention point. Satisfied.'"
    - "Closing section after §6: render a `## Rollup complete (Phase 406)` heading with a verbatim 1-paragraph closing statement: 'HARNESS-ARCHITECTURE.md is the canonical Phase 406 rollup. All 8 HRN requirements are covered: HRN-01 (§1 layered diagram), HRN-02 (§2 plugin hook inventory), HRN-03 (§3 MCP tool catalog), HRN-04 (§4.1–§4.2 4-tier ladder), HRN-05 (§4.3 HarnessIntervention class), HRN-06 (§4.5 human-gate-only-via-question structural invariant), HRN-07 (§5 event-replay reconstruction proof), HRN-08 (§6 full-Slice lifecycle sequence diagram). The 12 prior v41 specs (402–405) stay as-shipped; this rollup adds no amendments. v14 Build Kernel implements; v15 Build Core Commands wires; v9 TUI subscribes to state.harness.intervention SSE stream.'"
    - "HARNESS-ARCHITECTURE.md does NOT contain the literal string `GSD-` anywhere (project naming-discipline rule — STATE-* / state-* only)."
  artifacts:
    - path: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      provides: "Phase 406 canonical rollup COMPLETE — §5 event-replay reconstruction proof (HRN-07) + §6 full-Slice lifecycle Mermaid sequence diagram (HRN-08) + closing rollup-complete statement. HRN-01..HRN-08 all covered."
      min_lines: 1450
  key_links:
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-EVENTS.md"
      via: "§5.1 Category-2 row enumerates all 9 plan-lifecycle events from STEP-EVENTS.md verbatim; §5.2 reconstruction protocol depends on event-store rows produced per that spec"
      pattern: "STEP-EVENTS\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md"
      via: "§6.1 names the compaction-snapshot-schema Slice from this exemplar; §6.2 cites the 3 literal tasks (RED / GREEN / checkpoint:decision-orjson) for the sequence diagram"
      pattern: "EXEMPLAR-stepNPLAN\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md"
      via: "§5.1 Category-1 + §6.4 stage table consume SLICE-CYCLE.md (4 stages: design-slice / research-slice / run-slice / verify-slice per 402 v40-vocab carry-forward)"
      pattern: "SLICE-CYCLE\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "§5.2 step 2 loads CompactionSnapshot per CTX-05; §5.3 worked example shows snapshot rehydration; §6 sequence diagram shows tier-3 force_clear_and_reinject driving session.compacting per CTX-03/CTX-04"
      pattern: "CONTEXT-PROTOCOL\\.md"
---

<objective>
Append §5 + §6 + closing rollup-complete section to the canonical `HARNESS-ARCHITECTURE.md` spec document. §5 specifies the event-replay reconstruction proof (HRN-07) — the canonical list of events that must replay to rebuild full harness state, the 5-step reconstruction protocol, and a worked-example daemon-restart hard case showing snapshot rehydration + replay forward + orphan reconciliation + plugin-hook resume. §6 renders a Mermaid sequence diagram walking one full Slice lifecycle (HRN-08) — design-slice → research-slice → run-slice (with one Step) → verify-slice → close — showing every event emitted (≥25 events) and every harness intervention point (≥4, one per tier).

This is Wave 4 (the final wave for Phase 406): depends on Plan 03 (which appended §4 intervention ladder). The §5 section references the `state.harness.intervention` event from §4.3 in its Category-5 replay enumeration; the §6 sequence diagram surfaces intervention emission points by tier (tier-1 advisory, tier-2 block, tier-3 reinject, tier-4 human-gate) from §4.1–§4.2.

Purpose: HRN-07 + HRN-08 fully covered. With these two sections appended, Phase 406's rollup is complete: HRN-01..HRN-08 all addressed in `HARNESS-ARCHITECTURE.md`. Downstream consumers — v14 Build Kernel (implements the reconstruction protocol verbatim — the 5 per-chain reducer modules + the orphan reconciliation step + the plugin-hook resume routine; runs the Mermaid sequence diagram's event-emission contract as a smoke-test fixture for v14 EXEMPLAR work), v15 Build Core Commands (wires the daemon-boot reconstruction pipeline + the per-Slice exemplar verification), v9 TUI (subscribes to the full event stream enumerated in §5.1 for live rendering during a Slice's lifecycle) — all read from these two sections.

Output: §5 + §6 + closing rollup-complete heading appended to HARNESS-ARCHITECTURE.md, bringing total to ≥1450 lines. The file becomes the canonical Phase 406 spec at this plan's completion. No `GSD-` identifier appears.
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
@.planning/milestones/v41/phases/406/406-CONTEXT.md
@.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
@.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
@.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
@.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
@.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — Replay-input enumeration 5-category table (verbatim from 406-CONTEXT.md `<decisions>` "Event-replay reconstruction (HRN-07)" subsection). RENDER VERBATIM IN §5.1:

```
| Category                          | Events                                                                                                  | Owning spec                                |
|-----------------------------------|---------------------------------------------------------------------------------------------------------|--------------------------------------------|
| 1. Slice-stage chain              | state.slice.{design,research,run,verify}_completed                                                       | 402 SLICE-CYCLE.md                         |
| 2. Plan-lifecycle chain (9 events)| state.step.plan_authored, plan_edit, plan_edit_blocked, checkpoint_auto_resolved, checkpoint_human_action_pending, checkpoint_human_action_resolved, state.step.renamed, state.step.added, state.step.removed | 403 STEP-EVENTS.md |
| 3. Counter chains                 | APG paralysis_event; PRF gate_strike, gate_resolved, step_verify_completed, slice_verify_completed; DEV deviation_logged, deviation_classification_rejected, deviation_resolution_recorded, deviation_cap_exceeded; SUB subagent_started, subagent_progress, subagent_complete, subagent_spot_check_failed, subagent_crash_detected, subagent_restart, subagent_restart_exhausted, subagent_orphan_detected | 404 + 405 |
| 4. Scope chain                    | scope_check, scope_deviation, scope_deviation_request, scope_deviation_resolved; subagent_whitelist_violation, subagent_cap_expansion_rejected | 404 SRP + 405 SUB                          |
| 5. Umbrella + context             | state.harness.intervention (this phase's emission); compaction.snapshot_taken, compaction.reinject_completed, harness.context_meter | 406 + 402                                  |
```

Total: ~30 event types.

Excerpt B — Reconstruction protocol (verbatim from 406-CONTEXT.md `<decisions>` "Event-replay reconstruction (HRN-07)" subsection). RENDER VERBATIM IN §5.2:

```
1. Daemon boot. Open .state/events.sqlite via single-writer facade (gsd-2 single-writer-sqlite-facade pattern; project carry-forward).

2. Load latest CompactionSnapshot row per active Slice (Phase 402 §8); seed projector state from the snapshot's slice_id, step_id, task_id, prior_session_id, provides_blocks, current_task_pointer, last_verify_result, subagent_restart_counters, in_flight_subagents (Phase 405 SUB-08 extension).

3. Replay events forward from first_kept_entry_id onward, applying per-chain reducers:
   - APG counter (state_build/paralysis/counter.py): per-task consecutive read-only count.
   - PRF counter (state_build/proof/counter.py): per-(task_id, check_id) strike chain.
   - DEV counter (state_build/deviation/counter.py): per-(task_id, rule_id, issue_signature) attempt chain.
   - SUB counter (state_build/subagents/restart_counter.py): per-(parent_task_id, subagent_type) restart chain.
   - Intervention chain (state_build/harness/intervention/projector.py): per-tier accumulation.

4. Reconcile orphan subagents (Phase 405 SUB-08 §6 6-step protocol): for each subagent_started without paired terminal event, probe opencode session API; emit synthetic subagent_orphan_detected for confirmed-gone tasks; persistent orphans surface as DEV-04 Rule 4 human gate.

5. Resume plugin hooks. chat.params re-injects the latest reinject payload (CTX-06); tool.execute.before re-attaches the 6-layer write-block stack.
```

Excerpt C — Worked example (verbatim from 406-CONTEXT.md `<decisions>` "Event-replay reconstruction (HRN-07)" subsection — "Worked example" paragraph). RENDER VERBATIM IN §5.3:

```
Worked example: daemon restart mid-run-slice with 2 in-flight subagents, paralysis counter at 4 of 6 on task-3, last CompactionSnapshot taken 30s before restart. Show:
- Snapshot rehydration: paralysis counter task-3 → 4, restart counters task-2|researcher → 1, task-2|pattern-mapper → 0.
- Replay catches 6 additional subagent_progress events post-snapshot for both in-flight subagents.
- Orphan probe: opencode reports both still running; daemon re-subscribes to SSE for both session_ids.
- Plugin hook resume: chat.params re-injects with <prior_crash> block if any restart-chain has fired.

Total: ~15–25 lines of worked-example prose plus a Mermaid sequence diagram of the restart flow.
```

Excerpt D — Exemplar Slice identification for §6 (verbatim from 406-CONTEXT.md `<decisions>` "HRN-08 exemplar Slice — reuse 403's EXEMPLAR-stepNPLAN.md" subsection):

```
The compaction-snapshot-schema Slice with 1 Step containing 3 tasks (RED test → GREEN implement → checkpoint:decision for orjson flag). Already canonically authored; mature must_haves, <threat_model>, <verify>. Lets HRN-08 cite literal task names and events. Cross-cites Phase 402 CTX-05 (CompactionSnapshot model), Phase 403 STP-04 (<task> sub-tag), Phase 404 PRF (must_haves evaluator dispatch), Phase 405 DEV-05 (autonomy interaction on the checkpoint:decision task).
```

Excerpt E — `HarnessIntervention` Pydantic class (already inlined in §4.3 by Plan 03; cross-referenced here in §5.1 Category-5 and surfaced in §6 sequence diagram per-tier intervention emission):

```python
# Reference: HARNESS-ARCHITECTURE.md §4.3 (Plan 03's output)
class HarnessIntervention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: Literal["advisory", "tool_block", "clear_reinject", "human_gate"]
    trigger_reason: Literal[...]  # 18 values
    target_step_or_task: str
    correlation_event_id: str
    slice_id: str
    session_id: str
    triggered_at: datetime
```

Excerpt F — `CompactionSnapshot` Pydantic class (from Phase 402 CONTEXT-PROTOCOL.md CTX-05; loaded in §5.2 step 2):

```python
# Reference: .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md §CTX-05
class CompactionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slice_id: str
    step_id: str
    task_id: str | None
    prior_session_id: str
    provides_blocks: dict[str, str]
    current_task_pointer: str | None
    last_verify_result: dict | None
    subagent_restart_counters: dict[str, int]
    in_flight_subagents: list[str]
    first_kept_entry_id: int     # replay forward from here
    triggered_at: datetime
```
</interfaces>

<threat_model>
Phase 406 is design-only. §5 + §6 of HARNESS-ARCHITECTURE.md introduce no production attack surface — they are markdown specifications describing replay protocol + Mermaid lifecycle diagram. Threats considered:

- **[high] Incomplete replay enumeration could leave gaps in harness reconstruction.** If §5.1's 5-category event enumeration misses an event type that's emitted at runtime, the daemon could rehydrate with stale state on restart. Mitigation: the 5-category table is rendered verbatim from 406-CONTEXT.md and cross-checked against the 4 source-event categories already documented in Phase 405 SUBAGENT-MONITORING.md + Phase 404 PROOF-GATE.md + Phase 403 STEP-EVENTS.md. v14 unit tests assert `set(events_in_replay) == set(BUILD_ONLY_EVENT_TYPES)` to catch drift.
- **[med] Reconstruction protocol step ordering ambiguity.** If steps 2 (snapshot load) and 3 (event replay forward) could be reordered, replay determinism could break. Mitigation: §5.2 renders the 5 steps as a numbered ordered list; v14 implementation MUST preserve order. Step 2 explicitly seeds projector state BEFORE step 3 replays forward; the `first_kept_entry_id` field on CompactionSnapshot pins the forward-replay starting seq.
- **[med] Orphan reconciliation false-positive — could spuriously surface a Rule 4 human gate.** If the orphan probe (step 4) misclassifies a still-running subagent as orphaned, the harness could surface a human gate where none is warranted. Mitigation: §5.2 step 4 references Phase 405 SUB-08 6-step protocol for the canonical orphan reconciliation procedure; persistent-orphan surfacing requires confirmation across multiple reconciliation passes (not single-shot).
- **[med] Sequence-diagram event omission.** §6's Mermaid diagram MUST show ≥25 events and ≥4 intervention points (one per tier). If the diagram omits a tier (e.g., no tier-2 block shown), HRN-08 is incomplete. Mitigation: verify-block bash counts emitted events + tier coverage; the must_haves enumerate the minimum coverage; verify-block bash counts `state\\.` event prefixes inside the §6 Mermaid block.
- **[med] Naming-discipline drift (STATE-* vs GSD-*).** Mitigation: verify-block bash includes `! grep -qE '\bGSD-' "$F"`.
- **[low] Pure-machine discipline drift in replay.** The replay protocol must be deterministic. Mitigation: §5.2 step 3 references the 5 per-chain reducer modules (all pure-Python deterministic projectors); §5.4 closes with the append-only invariant + per-aggregate seq ordering guarantee.

No production code lands. No secrets, no network calls. The spec describes runtime mechanisms; threats listed above target v14 implementation, which the rollup constrains via authoritative Pydantic + protocol + Mermaid shapes.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Append §5 — Event-Replay Reconstruction Proof (HRN-07): replay-input enumeration + 5-step protocol + worked example + Mermaid restart-flow diagram + restart-safety closing</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Plans 01+02+03's output — §0–§4 already in place; APPEND §5 below)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "Event-replay reconstruction (HRN-07)" subsection — VERBATIM source for 5-category table + 5-step protocol + worked example
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<specifics>` 4th bullet "The replay proof's worked example must show a hard case" — framing for §5.3
    - .planning/milestones/v41/REQUIREMENTS.md lines 130-132 (HRN-07 verbatim)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "CompactionSnapshot|first_kept_entry_id|reinject payload" — Pydantic shapes loaded in §5.2 step 2)
    - .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md (full file — 9 plan-lifecycle event payloads for §5.1 Category-2)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md (search "6-step protocol|orphan reconciliation|subagent_restart_counters|in_flight_subagents" — §5.2 step 4 reconciliation source)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (search "gate_strike|step_verify_completed|slice_verify_completed" — PRF events for Category-3)
    - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md (search "paralysis_event|counter" — APG event for Category-3)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (search "deviation_logged|deviation_resolution_recorded" — DEV events for Category-3)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — verifies all enumerated events register under BUILD_ONLY_EVENT_PREFIXES per cross-reference)
  </read_first>

  <action>
    Append §5 to the existing HARNESS-ARCHITECTURE.md. **DO NOT modify §0, §1, §2, §3, or §4.** **Concrete content from 406-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 5 — Event-Replay Reconstruction Proof (HRN-07)

    Heading: `## §5 Event-Replay Reconstruction Proof (HRN-07)`.

    1-paragraph intro: "HRN-07 requires that 'harness state is fully reconstructable from the event store (daemon restart-safe)' and the proof contains 'a list of events that must replay to rebuild harness state.' §5 discharges this requirement: §5.1 enumerates the ~30 event types across 5 categories; §5.2 specifies the 5-step reconstruction protocol; §5.3 shows a worked daemon-restart hard case with snapshot rehydration + replay forward + orphan probe + plugin-hook resume; §5.4 closes with the restart-safety statement. The protocol is pure-machine deterministic (PRF-04 spirit carry-forward); the append-only event store + per-aggregate seq ordering guarantee replay determinism across hosts."

    ### Section 5.1 — Replay-input Enumeration (5-table breakdown)

    Heading: `### Replay-input Enumeration (5-category breakdown)`.

    Render the 5-category table verbatim from 406-CONTEXT.md (see <interfaces> Excerpt A). Total event-type count statement: "Total: ~30 event types. The table IS the HRN-07 enumeration. For each event type → Pydantic class → owning spec."

    Sub-section `#### Category 1 — Slice-stage chain`:

    Render verbatim:
    - Events (4): `state.slice.design_completed`, `state.slice.research_completed`, `state.slice.run_completed`, `state.slice.verify_completed`.
    - Owning spec: `402 SLICE-CYCLE.md`.
    - Vocab note: "v40 vocabulary carry-forward — stages are `design-slice / research-slice / run-slice / verify-slice` per 406-CONTEXT.md `<decisions>` 'Vocabulary carry-forward (402)' subsection, NOT `discuss-slice / plan-slice / execute-slice / verify-slice` from REQUIREMENTS.md. The REQUIREMENTS prose retains the older `discuss/plan/execute` labels as v1 SLC-01 wording; the canonical event names follow 402 SLICE-CYCLE.md."

    Sub-section `#### Category 2 — Plan-lifecycle chain (9 events)`:

    Render verbatim:
    - Events (9): `state.step.plan_authored`, `state.step.plan_edit`, `state.step.plan_edit_blocked`, `state.step.checkpoint_auto_resolved`, `state.step.checkpoint_human_action_pending`, `state.step.checkpoint_human_action_resolved`, `state.step.renamed`, `state.step.added`, `state.step.removed`.
    - Owning spec: `403 STEP-EVENTS.md`.

    Sub-section `#### Category 3 — Counter chains (~17 events)`:

    Render verbatim 4-bullet list (one per per-chain owner):
    - **APG (404, owning spec ANALYSIS-PARALYSIS-GUARD.md):** `state.step.paralysis_event` (per-task consecutive read-only count).
    - **PRF (404, owning spec PROOF-GATE.md):** `state.step.gate_strike`, `state.step.gate_resolved`, `state.step.step_verify_completed`, `state.slice.slice_verify_completed` (per-(task_id, check_id) strike chain + verify summaries).
    - **DEV (405, owning spec DEVIATION-RULES.md):** `state.step.deviation_logged`, `state.step.deviation_classification_rejected`, `state.step.deviation_resolution_recorded`, `state.step.deviation_cap_exceeded` (per-(task_id, rule_id, issue_signature) attempt chain).
    - **SUB (405, owning spec SUBAGENT-MONITORING.md):** `state.step.subagent_started`, `state.step.subagent_progress`, `state.step.subagent_complete`, `state.step.subagent_spot_check_failed`, `state.step.subagent_crash_detected`, `state.step.subagent_restart`, `state.step.subagent_restart_exhausted`, `state.step.subagent_orphan_detected` (per-(parent_task_id, subagent_type) restart + return spot-check chain).

    Sub-section `#### Category 4 — Scope chain`:

    Render verbatim:
    - Events: `state.step.scope_check`, `state.step.scope_deviation`, `state.step.scope_deviation_request`, `state.step.scope_deviation_resolved`, `state.step.subagent_whitelist_violation`, `state.slice.subagent_cap_expansion_rejected`.
    - Owning specs: `404 SCOPE-PROHIBITION.md` (first 4 events) + `405 SUBAGENT-MANAGEMENT.md` (last 2 events).

    Sub-section `#### Category 5 — Umbrella + context`:

    Render verbatim:
    - Events: `state.harness.intervention` (THIS phase, §4.3); `state.session.compaction_snapshot_taken`, `state.session.compaction_reinject_completed`, `state.session.context_meter`.
    - Owning specs: `406` (this rollup, §4) + `402 CONTEXT-PROTOCOL.md` (CTX-05 + CTX-08).

    Sub-section `#### Pydantic class + owning-spec cross-reference`:

    Render verbatim: "For each event type in Categories 1–5: the Pydantic payload class is rendered in its owning spec. Replay loads the payload via Pydantic `extra=\"forbid\"` validation; unknown fields raise `ValidationError` at parse time. v14 implements `BUILD_ONLY_EVENT_TYPES: frozenset[str]` at module path `state_build/event_store/event_types.py` as a single-source-of-truth check against EVENT-TAXONOMY.md amendments (per Phase 405 Plan 04's amendment chain). CI asserts `set(events_emitted_by_state_build) ⊆ BUILD_ONLY_EVENT_TYPES` to catch drift."

    ### Section 5.2 — Reconstruction Protocol (5-step numbered)

    Heading: `### Reconstruction Protocol`.

    1-paragraph intro: "On daemon boot (or restart after crash), the daemon runs the following 5-step protocol to rehydrate harness state from the event store + the latest CompactionSnapshot rows. The protocol is pure-machine deterministic; the same event-store contents on the same daemon binary produce the same rehydrated projector state (bit-identical, modulo wall-clock timestamps which are recorded but not reduced over)."

    Render the 5-step protocol verbatim from 406-CONTEXT.md (see <interfaces> Excerpt B). Use a numbered list (1., 2., 3., 4., 5.) preserving the exact wording.

    Sub-section `#### Step 3 detail — per-chain reducers`:

    Render verbatim a 5-bullet list (one per reducer):
    - **APG counter** — module path `state_build/paralysis/counter.py`; aggregation key per-`task_id`; events reduced: `state.step.paralysis_event` + every `tool.execute.after` derived counter-tick (synthesized during replay from `state.session.tool_execute_after` events).
    - **PRF counter** — module path `state_build/proof/counter.py`; aggregation key per-(`task_id`, `check_id`); events reduced: `state.step.gate_strike`, `state.step.gate_resolved`.
    - **DEV counter** — module path `state_build/deviation/counter.py`; aggregation key per-(`task_id`, `rule_id`, `issue_signature`); events reduced: `state.step.deviation_logged`, `state.step.deviation_resolution_recorded`, `state.step.deviation_cap_exceeded`.
    - **SUB counter** — module path `state_build/subagents/restart_counter.py`; aggregation key per-(`parent_task_id`, `subagent_type`); events reduced: `state.step.subagent_started`, `state.step.subagent_complete`, `state.step.subagent_crash_detected`, `state.step.subagent_restart`, `state.step.subagent_restart_exhausted`.
    - **Intervention chain projector** — module path `state_build/harness/intervention/projector.py`; aggregation key per-`slice_id`; events reduced: `state.harness.intervention` (umbrella) + every per-chain source event for cross-validation.

    Sub-section `#### Step 4 detail — orphan reconciliation cross-reference`:

    Render verbatim: "Step 4's orphan reconciliation procedure is documented in full at Phase 405 SUBAGENT-MONITORING.md §'daemon-down orphan reconciliation 6-step protocol' (SUB-08). The protocol's persistent-orphan threshold is 'orphan probe persists across 6 reconciliation steps' — at which point the harness surfaces a DEV-04 Rule 4 human gate via `surface_human_gate` MCP tool (§3 entry 10) with `trigger_reason=\"subagent_orphan_persistent\"`."

    Sub-section `#### Step 5 detail — plugin-hook resume`:

    Render verbatim:
    - `chat.params` resumption: the hook re-injects the latest reinject payload (CTX-06) including: active `stepNN-PLAN.md` content, current task pointer, last verify result, all upstream Step `SUMMARY.md` `provides:` blocks, worktree path, and (if any restart-chain has fired during the crashed session) a `<prior_crash>` continuation context block referencing the 5-source crash taxonomy from Phase 405 SUBAGENT-MONITORING.md.
    - `tool.execute.before` resumption: the hook re-attaches the **7-layer write-block stack** (PAP-05 immutability → SRP-04 files_modified → SRP-02 prohibited-language → SRP-04 ancillary discovered_threats → DEV log_deviation routing → SUB dispatch_subagent whitelist+cap → DEV arch-pattern allowlist) per §2's tool.execute.before subsection. Note: 406-CONTEXT.md's reconstruction-protocol prose says "6-layer" reflecting the pre-Phase-405-Plan-02-arch-pattern view; the canonical post-405 count is 7 layers. v14 implements 7; v17+ may extend further (each extension requires a new harness spec phase).
    - `tool.execute.after` resumption: counter tick + context-meter mirror per §2's `tool.execute.after` subsection.
    - `session.compacting` resumption: ready to accept opencode's next compaction trigger; `force_clear_and_reinject` MCP tool can immediately invoke if intervention is pending.
    - `shell.env` resumption: STATE-* trailer env-var injection routine is re-attached.

    ### Section 5.3 — Worked Example (daemon restart mid-run-slice)

    Heading: `### Worked Example — Daemon Restart Mid-Run-Slice (hard case)`.

    1-paragraph intro: "Per 406-CONTEXT.md `<specifics>` 4th bullet: 'The easy case (clean Slice close) does not exercise orphan reconciliation, counter rehydration, or `<prior_crash>` continuation context. The worked example is the proof that the protocol works under the realistic failure mode.' Below: daemon restart mid-`run-slice` with 2 in-flight subagents, paralysis counter at 4 of 6 on `task-3`, last `CompactionSnapshot` taken 30 seconds before restart."

    Sub-section `#### Pre-restart state`:

    Render verbatim:
    - **Active Slice:** `slice-N`, stage = `run-slice`, current task = `task-3`.
    - **Paralysis counter:** `task-3 → 4` (out of 6 — within tier 1 advisory range, 2 advisories away from tier-3 reinject at advisory 3 wait — actually 4 = 4th advisory ≥ 3, so this Slice has ALREADY tripped tier-3 once; chain reinject occurred at advisory 3; current chain progression is in the post-reinject 3-more-strikes phase).
    - **Subagent restart counters:** `task-2|researcher → 1`, `task-2|pattern-mapper → 0` (researcher previously crashed once, restarted successfully).
    - **In-flight subagents (at crash):** `task-4|researcher` (session-id `sub-A`), `task-4|pattern-mapper` (session-id `sub-B`). Both spawned 90 seconds ago; both emitted `subagent_started` events; no terminal events yet.
    - **Last CompactionSnapshot:** captured 30 seconds before crash; carries all five counters + `in_flight_subagents = ["task-4|researcher@sub-A", "task-4|pattern-mapper@sub-B"]`.
    - **Crash:** daemon process terminated (SIGKILL, kernel OOM, or `systemctl restart state-daemon`).

    Sub-section `#### Reconstruction trace`:

    Render verbatim a numbered protocol-application trace (mirrors §5.2 5-step numbering):

    1. **Daemon boot.** Single-writer SQLite facade opens `.state/events.sqlite`. Successful open implies no concurrent writer (gsd-2 carry-forward — single-writer invariant).
    2. **Load latest CompactionSnapshot per active Slice.** Snapshot row from 30s before crash hydrates projector state. Counters loaded:
       - `paralysis_counter["task-3"] = 4`
       - `restart_counter[("task-2","researcher")] = 1`
       - `restart_counter[("task-2","pattern-mapper")] = 0`
       - `restart_counter[("task-4","researcher")] = 0` (just-spawned)
       - `restart_counter[("task-4","pattern-mapper")] = 0` (just-spawned)
       - `in_flight_subagents = {"task-4|researcher@sub-A", "task-4|pattern-mapper@sub-B"}`
    3. **Replay events forward from `first_kept_entry_id` onward.** During the 30s between snapshot and crash, the event store captured (e.g.) 6 additional `subagent_progress` events (3 per in-flight subagent) plus 1 `chat.message` mirror per subagent turn. Replay processes these forward, no counter changes (subagent_progress is informational; counter changes only on terminal events). Projector state post-replay is bit-identical to the projector state at the moment of crash.
    4. **Reconcile orphan subagents.** For each entry in `in_flight_subagents`, probe opencode session API:
       - `sub-A` → opencode reports "still running, last message 5s ago". Mark NON-orphan; re-subscribe to SSE for session `sub-A`; continue monitoring.
       - `sub-B` → opencode reports "still running, last message 8s ago". Mark NON-orphan; re-subscribe to SSE for session `sub-B`.
       - If opencode had reported "session not found" for either, emit synthetic `state.step.subagent_orphan_detected`; on persistence across 6 reconciliation steps, escalate to tier 4 via `surface_human_gate(trigger_reason="subagent_orphan_persistent")`.
    5. **Resume plugin hooks.**
       - `chat.params` re-injects the latest reinject payload. Because `task-2|researcher`'s restart counter is non-zero (= 1), the payload includes a `<prior_crash>` continuation block citing the 5-source crash taxonomy entry for `task-2|researcher`'s prior crash. v14 implements; SUBAGENT-MONITORING.md owns the `<prior_crash>` XML schema.
       - `tool.execute.before` re-attaches the 7-layer write-block stack.
       - `tool.execute.after` resumes counter ticks for `task-3` (which is paused while paralysis chain works through post-reinject advisories).
       - `shell.env`, `chat.message`, `session.compacting` resume.

    Sub-section `#### Mermaid sequence diagram of restart flow`:

    Render a `mermaid` `sequenceDiagram` code block with these participants and ≥10 numbered messages. Structure:

    ```mermaid
    sequenceDiagram
        autonumber
        participant SQLite as events.sqlite
        participant Daemon as state-daemon
        participant Proj as Projector
        participant Plugin as opencode-plugin
        participant SubA as Subagent task-4 researcher (sub-A)
        participant SubB as Subagent task-4 pattern-mapper (sub-B)

        Note over Daemon: Daemon process starts (post-crash)
        Daemon->>SQLite: open .state/events.sqlite (single-writer facade)
        SQLite-->>Daemon: handle, schema_version
        Daemon->>SQLite: SELECT latest CompactionSnapshot per active Slice
        SQLite-->>Daemon: snapshot row (slice-N, 30s pre-crash)
        Daemon->>Proj: seed counters from snapshot
        Note over Proj: paralysis_counter["task-3"] = 4, restart_counter[...] = 1, in_flight = {sub-A, sub-B}

        Daemon->>SQLite: SELECT events WHERE seq >= first_kept_entry_id
        SQLite-->>Daemon: 6 × subagent_progress events
        Daemon->>Proj: replay forward
        Proj-->>Daemon: post-replay state (no counter changes)

        Daemon->>Plugin: probe session sub-A
        Plugin-->>Daemon: still running
        Daemon->>Plugin: probe session sub-B
        Plugin-->>Daemon: still running
        Daemon->>SubA: re-subscribe SSE
        Daemon->>SubB: re-subscribe SSE

        Daemon->>Plugin: resume chat.params (with <prior_crash> for task-2|researcher)
        Daemon->>Plugin: resume tool.execute.before (7-layer stack)
        Daemon->>Plugin: resume tool.execute.after, session.compacting, chat.message, shell.env

        Note over Daemon: Harness fully rehydrated; agent resumes turn-by-turn execution
    ```

    (Executor: refine arrow ordering or add additional participants if the rendering needs disambiguation, but the 6 participants + ≥10 numbered messages above MUST be present.)

    ### Section 5.4 — Restart-Safety Closing Statement (HRN-07 satisfied)

    Heading: `### Restart-Safety Closing Statement`.

    Render verbatim: "The 5-step protocol + worked example demonstrate that **harness state is fully reconstructable from the event store**. Daemon restart at any point during a Slice's execution rehydrates without loss of (a) per-chain counters (APG / PRF / DEV / SUB), (b) in-flight subagent registrations, (c) plugin-hook write-block stack state. **Append-only invariant** of the event store (PROJECT.md cardinal rule) + **single-writer SQLite facade** (gsd-2 carry-forward pattern) + **per-aggregate seq ordering** guarantee replay determinism. HRN-07 satisfied."

    <quality_scan>
      <code_to_reuse>
        - Known: 406-CONTEXT.md `<decisions>` "Event-replay reconstruction (HRN-07)" subsection — VERBATIM source for 5-category table + 5-step protocol + worked example.
        - Known: 406-CONTEXT.md `<specifics>` 4th bullet — "hard case" framing for §5.3.
        - Known: REQUIREMENTS.md HRN-07 — req-level constraint.
        - Known: Phase 402 CONTEXT-PROTOCOL.md CTX-05 — CompactionSnapshot Pydantic shape source.
        - Known: Phase 403 STEP-EVENTS.md — 9-event payload source for Category-2.
        - Known: Phase 404 PROOF-GATE.md §6 — gate_strike + gate_resolved + counter chain.
        - Known: Phase 404 ANALYSIS-PARALYSIS-GUARD.md — paralysis_event + counter chain.
        - Known: Phase 405 DEVIATION-RULES.md — DEV event chain (4 events).
        - Known: Phase 405 SUBAGENT-MONITORING.md §"daemon-down orphan reconciliation 6-step protocol" — Step 4 cross-reference.
        - Grep pattern: `grep -nE "Category|state\\.slice|state\\.step|state\\.session|state\\.harness" /Users/tmac/Projects/state/.planning/milestones/v41/phases/406/406-CONTEXT.md | head -30` — locates verbatim source.
        - Grep pattern: `grep -nE "first_kept_entry_id|CompactionSnapshot|in_flight_subagents" /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md | head -10` — locates CompactionSnapshot fields source.
        - Grep pattern: `grep -nE "BUILD_ONLY_EVENT_PREFIXES|BUILD_ONLY_EVENT_TYPES" /Users/tmac/Projects/state/.planning/milestones/v41/phases/40[45]/specs/*.md | head -10` — locates BUILD_ONLY_* registry pattern.
      </code_to_reuse>
      <docs_to_consult>
        - 406-CONTEXT.md `<decisions>` "Event-replay reconstruction (HRN-07)" — verbatim source.
        - 406-CONTEXT.md `<specifics>` 4th bullet — framing.
        - REQUIREMENTS.md HRN-07 — req-level constraint.
        - Phase 402 CONTEXT-PROTOCOL.md — CompactionSnapshot + reinject payload.
        - Phase 403 STEP-EVENTS.md — 9-event Pydantic classes.
        - Phase 405 SUBAGENT-MONITORING.md §"daemon-down orphan reconciliation 6-step protocol" — orphan procedure source.
        - gsd-2 `kb/patterns/single-writer-sqlite-facade.md` — single-writer SQLite pattern source.
        - gsd-2 `kb/patterns/db-driven-crash-recovery.md` — crash-recovery pattern source.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 1250)}' \
        && grep -qE "^## §5 Event-Replay Reconstruction Proof \(HRN-07\)" "$F" \
        && grep -qE "^### Replay-input Enumeration" "$F" \
        && grep -qE "^### Reconstruction Protocol" "$F" \
        && grep -qE "^### Worked Example" "$F" \
        && grep -qE "^### Restart-Safety Closing Statement" "$F" \
        && grep -q "state.slice.design_completed" "$F" \
        && grep -q "state.slice.research_completed" "$F" \
        && grep -q "state.slice.run_completed" "$F" \
        && grep -q "state.slice.verify_completed" "$F" \
        && grep -q "state.step.plan_authored" "$F" \
        && grep -q "state.step.plan_edit" "$F" \
        && grep -q "state.step.plan_edit_blocked" "$F" \
        && grep -q "state.step.checkpoint_auto_resolved" "$F" \
        && grep -q "state.step.checkpoint_human_action_pending" "$F" \
        && grep -q "state.step.checkpoint_human_action_resolved" "$F" \
        && grep -q "state.step.paralysis_event" "$F" \
        && grep -q "state.step.gate_strike" "$F" \
        && grep -q "state.step.deviation_logged" "$F" \
        && grep -q "state.step.subagent_started" "$F" \
        && grep -q "state.step.subagent_complete" "$F" \
        && grep -q "state.step.subagent_crash_detected" "$F" \
        && grep -q "state.step.subagent_restart_exhausted" "$F" \
        && grep -q "state.step.subagent_orphan_detected" "$F" \
        && grep -q "state.harness.intervention" "$F" \
        && grep -qE "compaction\\.snapshot_taken|compaction_snapshot_taken" "$F" \
        && grep -qE "state_build/paralysis/counter\\.py" "$F" \
        && grep -qE "state_build/proof/counter\\.py" "$F" \
        && grep -qE "state_build/deviation/counter\\.py" "$F" \
        && grep -qE "state_build/subagents/restart_counter\\.py" "$F" \
        && grep -qE "state_build/harness/intervention/projector\\.py" "$F" \
        && grep -q "first_kept_entry_id" "$F" \
        && grep -q "in_flight_subagents" "$F" \
        && grep -q "single-writer" "$F" \
        && grep -q "CompactionSnapshot" "$F" \
        && grep -qE '^```mermaid' "$F" \
        && grep -q "sequenceDiagram" "$F" \
        && grep -q "task-3" "$F" \
        && grep -q "task-4|researcher\\|task-4.researcher" "$F" \
        && grep -q "subagent_orphan_persistent" "$F" \
        && grep -q "prior_crash" "$F" \
        && grep -q "HRN-07 satisfied" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[1]] §5 heading + 4 sub-section headings (Replay-input Enumeration, Reconstruction Protocol, Worked Example, Restart-Safety Closing Statement) present.
    - [check: must_haves.truths[2]] §5.1 5-category table rendered with all 5 categories named.
    - [check: must_haves.truths[3]] §5.1 Category-1 enumerates 4 design/research/run/verify Slice-stage events.
    - [check: must_haves.truths[4]] §5.1 Category-2 enumerates all 9 plan-lifecycle events.
    - [check: must_haves.truths[5]] §5.1 Category-3 enumerates APG/PRF/DEV/SUB chain events.
    - [check: must_haves.truths[6]] §5.1 Category-4 scope chain enumerates all 6 events.
    - [check: must_haves.truths[7]] §5.1 Category-5 enumerates state.harness.intervention + 3 context events.
    - [check: must_haves.truths[8]] §5.1 closing note "Total: ~30 event types" + Pydantic-class + owning-spec mapping.
    - [check: must_haves.truths[9]] §5.2 5-step protocol renders verbatim with daemon-boot + snapshot-load + event-replay-forward + orphan-reconciliation + plugin-hook-resume steps.
    - [check: must_haves.truths[10]] §5.2 step 3 names all 5 reducer module paths.
    - [check: must_haves.truths[11]] §5.2 step 5 enumerates chat.params + tool.execute.before resumption details.
    - [check: must_haves.truths[12]] §5.3 worked example pre-restart state + reconstruction trace render with task-3 + task-4|researcher + task-4|pattern-mapper specifics.
    - [check: must_haves.truths[13]] §5.3 Mermaid sequenceDiagram renders with ≥6 participants + ≥10 numbered messages + SQLite + Daemon + Projector + Plugin + 2 Subagents.
    - [check: must_haves.truths[14]] §5.4 restart-safety closing statement renders with append-only + single-writer + per-aggregate-seq invariants + "HRN-07 satisfied".
    - [check: must_haves.truths[24]] No `GSD-` literal in the file.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md grows by ~200 lines (§5 complete: enumeration + protocol + worked example + Mermaid restart-flow + closing); file ≥1250 lines; all 5 replay categories + 30 event types + 5 reducer module paths + worked example with Mermaid restart-flow diagram render; verify-block bash passes; no `GSD-` literal; §0–§4 untouched.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append §6 — Full-Slice Lifecycle Sequence Diagram (HRN-08): exemplar Slice identification + Mermaid diagram with ≥25 events + ≥4 intervention points + tabulation + Phase-cross-reference + rollup-complete closing</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Task 1's output — §0–§5 already in place; APPEND §6 + rollup-complete closing below)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "HRN-08 granularity — every event + every harness intervention point" subsection — VERBATIM source for §6.2 granularity rule
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "HRN-08 exemplar Slice — reuse 403's EXEMPLAR-stepNPLAN.md" subsection — VERBATIM source for §6.1 exemplar identification + cross-cites
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<specifics>` 3rd bullet "HRN-08 should feel like the gsd-2 cross-layer comm-map §3 end-to-end flow" — framing
    - .planning/milestones/v41/REQUIREMENTS.md lines 134-136 (HRN-08 verbatim)
    - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md (full file — exemplar `compaction-snapshot-schema` Slice with 3 tasks: RED test → GREEN implement → `checkpoint:decision` for orjson flag)
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md (full file — 4-stage Slice cycle event names + ordering for §6.4 cross-reference)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "CTX-04|threshold|emergency" — for run-slice tier-3 emergency-threshold emission in §6.2)
    - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md (search "advisory|threshold|paralysis_event" — for research-slice tier-1 advisory emission in §6.2)
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (search "PAP-05|plan_edit_blocked" — for tier-2 immutability-block emission in §6.2)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (search "checkpoint:decision|DEV-05|autonomy" — for tier-4 human-gate emission in §6.2 on orjson flag selection)
  </read_first>

  <action>
    Append §6 + rollup-complete closing to the existing HARNESS-ARCHITECTURE.md. **DO NOT modify §0, §1, §2, §3, §4, or §5.** **Concrete content from 406-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 6 — Full-Slice Lifecycle Sequence Diagram (HRN-08)

    Heading: `## §6 Full-Slice Lifecycle Sequence Diagram (HRN-08)`.

    1-paragraph intro (verbatim from 406-CONTEXT.md `<specifics>` 3rd bullet): "HRN-08 should feel like the gsd-2 cross-layer comm-map §3 end-to-end flow — that section walks one user prompt across all 5 layers showing every cross-layer hop; HRN-08 walks one Slice across all 4 stages showing every event + intervention. Same shape, different scope. The exemplar Slice is the `compaction-snapshot-schema` Slice from 403 EXEMPLAR-stepNPLAN.md, canonically authored with 1 Step containing 3 tasks. The diagram below shows every event emitted (≥25 events) and every harness intervention point (≥4, one per tier 1/2/3/4)."

    ### Section 6.1 — Exemplar Slice Identification

    Heading: `### Exemplar Slice — compaction-snapshot-schema (from 403 EXEMPLAR-stepNPLAN.md)`.

    Render verbatim from 406-CONTEXT.md `<decisions>` "HRN-08 exemplar Slice" subsection:

    "**Exemplar Slice:** the `compaction-snapshot-schema` Slice from 403 `EXEMPLAR-stepNPLAN.md`. 1 Step containing 3 tasks (RED test → GREEN implement → `checkpoint:decision` for orjson flag). Already canonically authored; mature `must_haves`, `<threat_model>`, `<verify>`. Lets HRN-08 cite literal task names and events. Cross-cites:
    - Phase 402 CTX-05 (CompactionSnapshot model) — the Step's primary deliverable is this Pydantic class.
    - Phase 403 STP-04 (`<task>` sub-tag) — Step has 3 tasks, each rendered as a `<task>` XML block per STP-04.
    - Phase 404 PRF (must_haves evaluator dispatch) — Step has must_haves frontmatter; verify-slice runs must_haves evaluator.
    - Phase 405 DEV-05 (autonomy interaction on the `checkpoint:decision` task) — task 3 (`checkpoint:decision` for orjson flag) is the canonical tier-4 surface."

    Sub-section `#### Exemplar Step structure`:

    Render verbatim:
    - **Step ID:** `step-01`
    - **Step name:** `compaction-snapshot-schema`
    - **Tasks (in execution order):**
      - **Task 1 (RED):** `Task 1: Write failing test for CompactionSnapshot Pydantic round-trip` — type `auto+tdd`; verify-block bash runs pytest expecting a single failing test.
      - **Task 2 (GREEN):** `Task 2: Implement CompactionSnapshot Pydantic class with orjson round-trip` — type `auto`; verify-block bash runs pytest expecting the previously-failing test now passes.
      - **Task 3 (CHECKPOINT):** `Task 3: Select orjson flag preset (OPT_SORT_KEYS vs OPT_INDENT_2 vs OPT_NAIVE_UTC)` — type `checkpoint:decision`; harness surfaces opencode `question` tool with 3 alternatives; agent waits for human selection.

    ### Section 6.2 — Full-Slice Mermaid Sequence Diagram

    Heading: `### Full-Slice Mermaid Sequence Diagram`.

    1-paragraph intro: "The diagram below walks the full lifecycle of the exemplar Slice (design-slice → research-slice → run-slice [with the 3-task Step] → verify-slice → close). Each event emission is named verbatim (e.g., `state.step.plan_authored`); each harness intervention point is annotated with its tier (`tier=advisory`, `tier=tool_block`, `tier=clear_reinject`, `tier=human_gate`). Tabulation in §6.3 asserts the minimum event count (25) and tier coverage (≥1 emission per tier)."

    Render ONE Mermaid `sequenceDiagram` code block. Structure:

    ```mermaid
    sequenceDiagram
        autonumber
        participant User as User
        participant Daemon as state-daemon
        participant Plugin as opencode-plugin hooks
        participant Agent as Agent (opencode session)
        participant MCP as state-build MCP
        participant Sub as Subagent (researcher / pattern-mapper)
        participant Store as events.sqlite

        %% =============================================
        %% STAGE 1: design-slice
        %% =============================================
        Note over User,Store: Stage 1 — design-slice
        User->>Daemon: /state:design-slice compaction-snapshot-schema
        Daemon->>Plugin: spawn fresh session (CTX-02)
        Plugin->>Agent: chat.params inject (Slice scope + intentions)
        Agent->>MCP: dispatch_subagent(parallel=[researcher, code-mapper, requirements-analyzer])
        MCP->>Store: emit state.step.subagent_started ×3
        Sub-->>MCP: subagent_complete ×3 (structured returns)
        MCP->>Store: emit state.step.subagent_complete ×3
        Agent->>MCP: complete_slice(stage="design-slice")
        MCP->>Store: emit state.slice.design_completed

        %% =============================================
        %% STAGE 2: research-slice (plan-slice in v1 REQ vocab)
        %% =============================================
        Note over User,Store: Stage 2 — research-slice
        Daemon->>Plugin: chat.params inject (design-slice provides:)
        Agent->>MCP: dispatch_subagent(parallel=[researcher, pattern-mapper, planner, plan-validator])
        MCP->>Store: emit state.step.subagent_started ×4
        Note over Agent: TIER-1 ADVISORY — paralysis counter crosses 15 (research-stage threshold)
        Agent->>MCP: emit_advisory(source_trigger="paralysis", task_id=<plan-slice task>)
        MCP->>Store: emit state.step.paralysis_event(tier="advisory") + state.harness.intervention(tier="advisory", trigger_reason="paralysis_threshold_crossed")
        Plugin->>Agent: chat.params inject advisory text on next turn
        Agent->>MCP: record_plan_edit (RED test scaffolding committed)
        MCP->>Store: emit state.step.plan_authored (for step-01)
        Agent->>MCP: complete_slice(stage="research-slice")
        MCP->>Store: emit state.slice.research_completed

        %% =============================================
        %% STAGE 3: run-slice (execute-slice in v1 REQ vocab)
        %% =============================================
        Note over User,Store: Stage 3 — run-slice (3 tasks)
        Daemon->>Plugin: chat.params inject (PLAN content verbatim + provides:)

        %% --- Task 1: RED ---
        Note over Agent: Task 1 (RED) — failing test
        Agent->>Plugin: Write src/state_core/compaction_snapshot.py + test file
        Plugin->>Daemon: tool.execute.before (7-layer stack)
        Daemon->>Plugin: allow=true
        Agent->>Plugin: Bash pytest (expecting RED)
        Plugin->>Daemon: tool.execute.after (counter tick — write-mutating; resets read-only)
        Agent->>MCP: complete_task(task_id="task-1", verify_passed=true)
        MCP->>Store: emit state.step.complete_task — Task 1 done

        %% --- Task 2: GREEN ---
        Note over Agent: Task 2 (GREEN) — implement
        Agent->>Plugin: Edit src/state_core/compaction_snapshot.py
        Plugin->>Daemon: tool.execute.before (7-layer stack)
        Note over Daemon: TIER-2 BLOCK — agent attempted Edit to must_haves block in step-01 PLAN
        Daemon->>Plugin: allow=false, blockReason="PAP-05 immutability"
        Daemon->>Store: emit state.step.plan_edit_blocked + state.harness.intervention(tier="tool_block", trigger_reason="scope_check_unresolved")
        Agent->>Plugin: Edit src/state_core/compaction_snapshot.py (corrected target)
        Plugin->>Daemon: tool.execute.before — allow=true
        Agent->>Plugin: Bash pytest (expecting GREEN)
        Plugin->>Daemon: pytest result — pass
        Note over Daemon: CTX-04 emergency threshold ≤25% triggered mid-task
        Daemon->>MCP: force_clear_and_reinject(trigger_reason="context_threshold_emergency")
        MCP->>Store: emit state.session.context_threshold_emergency + state.harness.intervention(tier="clear_reinject", trigger_reason="context_threshold_emergency")
        MCP->>Plugin: trigger session.compacting hook (TIER-3 REINJECT)
        Plugin->>Store: emit state.session.compaction_snapshot_taken
        Plugin->>Agent: chat.params reinject (CompactionSnapshot rehydrate)
        Agent->>MCP: complete_task(task_id="task-2", verify_passed=true)
        MCP->>Store: emit state.step.complete_task — Task 2 done

        %% --- Task 3: checkpoint:decision ---
        Note over Agent: Task 3 (checkpoint:decision) — orjson flag preset
        Agent->>MCP: surface_human_gate(question_text="Select orjson flag preset", alternatives=[OPT_SORT_KEYS, OPT_INDENT_2, OPT_NAIVE_UTC])
        MCP->>Store: emit state.step.checkpoint_human_action_pending + state.harness.intervention(tier="human_gate", trigger_reason="deviation_rule_4_architectural")
        MCP->>Plugin: opencode question tool surfaced (TIER-4 HUMAN GATE)
        User-->>Plugin: select OPT_SORT_KEYS
        Plugin-->>MCP: question response
        MCP->>Store: emit state.step.checkpoint_human_action_resolved
        Agent->>MCP: complete_task(task_id="task-3", verify_passed=true)
        MCP->>Store: emit state.step.complete_task — Task 3 done

        %% End of run-slice
        Agent->>MCP: complete_slice(stage="run-slice")
        MCP->>Store: emit state.slice.run_completed

        %% =============================================
        %% STAGE 4: verify-slice
        %% =============================================
        Note over User,Store: Stage 4 — verify-slice
        Daemon->>Plugin: chat.params inject (run-slice provides: + verify checklist)
        Agent->>MCP: dispatch_subagent(parallel=[verifier, integration-checker, nyquist-auditor])
        MCP->>Store: emit state.step.subagent_started ×3
        Sub-->>MCP: subagent_complete ×3 (structured returns)
        MCP->>Store: emit state.step.subagent_complete ×3
        Agent->>MCP: check_proof_gate(scope="slice", scope_id="slice-N")
        MCP->>Store: emit state.slice.slice_verify_completed
        Agent->>MCP: complete_slice(stage="verify-slice")
        MCP->>Store: emit state.slice.verify_completed

        Note over Daemon: Slice closed — daemon emits close transition
    ```

    (Executor: refine arrow ordering or add additional events for readability, but every event named above MUST appear; the 4 tier-emission `state.harness.intervention` events MUST be present; the ≥25-event floor MUST be met.)

    ### Section 6.3 — Event + Intervention Tabulation

    Heading: `### Event + Intervention Tabulation`.

    Render verbatim a tabulation block:

    ```
    Diagram coverage assertions (HRN-08 floor):
      - Event-fire count: ≥25 named state.*.* event emissions (see Mermaid `emit state.` lines).
      - Intervention-point count: ≥4 — one per tier:
          * tier=advisory     → research-slice paralysis_event (research stage threshold = 15 reads)
          * tier=tool_block   → run-slice Task 2 PAP-05 immutability block
          * tier=clear_reinject → run-slice Task 2 CTX-04 emergency threshold ≤25%
          * tier=human_gate    → run-slice Task 3 checkpoint:decision orjson flag selection
      - Slice-stage events: 4 (state.slice.{design,research,run,verify}_completed)
      - Step-lifecycle events: 3+ (plan_authored, checkpoint_human_action_pending, checkpoint_human_action_resolved, complete_task ×3)
      - Counter events: ≥4 (≥1 paralysis_event, ≥1 gate-related, ≥3 subagent_started/complete pairs)
      - Compaction events: 2+ (compaction_snapshot_taken, context_threshold_emergency)
    ```

    Note: "Numbers MAY be exceeded — the floor is asserted to make verify-block bash count-checks unambiguous. The Mermaid diagram in §6.2 produces a strict superset of the floor."

    ### Section 6.4 — Phase 402–405 Cross-Reference per Stage

    Heading: `### Phase 402–405 Cross-Reference per Stage`.

    Render verbatim a 4-row markdown table:

    ```
    | Slice stage     | Canonical 402–405 spec sections consumed                                                                                                                       |
    |-----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | design-slice    | SLICE-CYCLE.md (SLC-02 design artifacts); SUBAGENT-MANAGEMENT.md (STAGE_ROSTER["discuss-slice"])                                                                              |
    | research-slice  | SLICE-CYCLE.md (SLC-03 4-stage plan-slice pipeline); STEP-PLAN-FORMAT.md (STP-01..08); PLAN-AS-PROMPT.md (PAP-01..06); ANALYSIS-PARALYSIS-GUARD.md (15-read research threshold) |
    | run-slice       | STEP-PLAN-FORMAT.md (STP-04 task sub-tags); PROOF-GATE.md (PRF-01..07); ANALYSIS-PARALYSIS-GUARD.md (5-read execute threshold); SCOPE-PROHIBITION.md (SRP-01..06); DEVIATION-RULES.md (DEV-01..07); SUBAGENT-MANAGEMENT.md (SUB-01..04); SUBAGENT-MONITORING.md (SUB-05..09); CONTEXT-PROTOCOL.md (CTX-01..09); PLAN-AS-PROMPT.md (PAP-05 immutability)             |
    | verify-slice    | SLICE-CYCLE.md (SLC-05 N-VERIFICATION.md); PROOF-GATE.md (PRF-03 Slice-end gate); SUBAGENT-MANAGEMENT.md (STAGE_ROSTER["verify-slice"]: verifier / integration-checker / nyquist-auditor) |
    ```

    Sub-section `#### HRN-08 satisfied`:

    Render verbatim: "The sequence diagram in §6.2 walks one full Slice from spawn to close, showing every event emitted (≥25 events) and every harness intervention point (≥4, one per tier 1/2/3/4). The exemplar Slice is canonically authored in 403 EXEMPLAR-stepNPLAN.md so this diagram cites literal task names (Task 1 RED / Task 2 GREEN / Task 3 checkpoint:decision orjson flag). HRN-08 literal: 'every event emitted and every harness intervention point.' Satisfied."

    ### Section 7 — Rollup Complete (Phase 406)

    Heading: `## Rollup complete (Phase 406)`.

    Render verbatim:

    "`HARNESS-ARCHITECTURE.md` is the canonical Phase 406 rollup. All 8 HRN requirements are covered:
    - **HRN-01** — §1 Layered diagram (Mermaid 3-layer: plugin hooks → state-build MCP server → state-daemon).
    - **HRN-02** — §2 Plugin hook inventory (6 hooks with TS signatures + role + v41-REQ back-cross-reference).
    - **HRN-03** — §3 state-build MCP tool catalog (14 tools with Pydantic input/output models; `MCP_TOOL_REGISTRY` + `assert_never` exhaustiveness).
    - **HRN-04** — §4.1–§4.2 4-tier intervention ladder (advisory inject / tool-block / force clear+reinject / force-stop+human gate) with per-tier trigger-source enumeration spanning APG / PRF / DEV / SUB / SCOPE / CTX chains.
    - **HRN-05** — §4.3 `HarnessIntervention` Pydantic class (18-value `trigger_reason` Literal; 7 fields including `tier`, `target_step_or_task`, `correlation_event_id`).
    - **HRN-06** — §4.5 Human-gate-only-via-opencode-`question` structural invariant + CI grep enforcement (`state_build/harness/intervention/` directory contains no custom UI primitives).
    - **HRN-07** — §5 Event-replay reconstruction proof (5-category event enumeration + 5-step protocol + worked daemon-restart hard case + Mermaid restart-flow diagram + restart-safety closing statement).
    - **HRN-08** — §6 Full-Slice lifecycle Mermaid sequence diagram (exemplar `compaction-snapshot-schema` Slice from 403 EXEMPLAR-stepNPLAN.md; ≥25 event emissions + 4 tier-intervention points one per tier).

    The 12 prior v41 specs (402: SLICE-CYCLE.md + CONTEXT-PROTOCOL.md; 403: STEP-PLAN-FORMAT.md + PLAN-AS-PROMPT.md + STEP-EVENTS.md + EXEMPLAR-stepNPLAN.md; 404: PROOF-GATE.md + ANALYSIS-PARALYSIS-GUARD.md + SCOPE-PROHIBITION.md; 405: DEVIATION-RULES.md + SUBAGENT-MANAGEMENT.md + SUBAGENT-MONITORING.md) stay as-shipped; this rollup adds no amendments to them. v14 Build Kernel implements the harness substrate per this spec; v15 Build Core Commands wires per-stage emitters into the research-slice pipeline + the run-slice harness; v9 TUI subscribes to the `state.harness.intervention` SSE stream and renders per-tier visual treatments (tier-1 advisory toast, tier-2 block reason, tier-3 reinject banner, tier-4 opencode `question` tool surface)."

    Closing footer: "*Phase 406 rollup canonical: v41. STATE-* naming discipline enforced. No GSD-* identifiers anywhere in this file (CI grep target).*"

    <quality_scan>
      <code_to_reuse>
        - Known: 406-CONTEXT.md `<decisions>` "HRN-08 granularity" + "HRN-08 exemplar Slice — reuse 403 EXEMPLAR-stepNPLAN.md" subsections — VERBATIM source for §6.1 + §6.2.
        - Known: 406-CONTEXT.md `<specifics>` 3rd bullet "HRN-08 should feel like the gsd-2 cross-layer comm-map §3 end-to-end flow" — framing.
        - Known: 403 EXEMPLAR-stepNPLAN.md — canonical 3-task structure (RED / GREEN / checkpoint:decision-orjson) for §6.1 + §6.2.
        - Known: 402 SLICE-CYCLE.md — 4-stage canonical Slice event names (design/research/run/verify_completed).
        - Known: 402 CONTEXT-PROTOCOL.md CTX-04 — emergency threshold ≤25% → tier-3 reinject trigger for §6.2.
        - Known: 404 ANALYSIS-PARALYSIS-GUARD.md APG-03 — research-slice 15-read threshold for §6.2.
        - Known: 405 DEVIATION-RULES.md DEV-05 — autonomy interaction on checkpoint:decision; per 406-CONTEXT.md the task-3 checkpoint:decision-orjson is canonically a Rule 4 surface.
        - Known: §4 of HARNESS-ARCHITECTURE.md (Plan 03's output) — surface_human_gate + force_clear_and_reinject + emit_advisory MCP tool surfaces for §6.2 emissions.
        - Known: §3 of HARNESS-ARCHITECTURE.md (Plan 02's output) — 14 MCP tool entries.
        - Grep pattern: `grep -nE "compaction-snapshot-schema|Task 1|Task 2|Task 3" /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md | head -20` — locates exemplar Slice task naming.
        - Grep pattern: `grep -nE "OPT_SORT_KEYS|OPT_INDENT_2|orjson flag" /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md | head -10` — locates orjson flag preset alternatives if present.
        - Grep pattern: `grep -nE "design-slice|research-slice|run-slice|verify-slice" /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md | head -10` — confirms 4-stage canonical names.
        - Grep pattern: `grep -c "state\\." /Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` — counts state.* emissions across the file (rough estimate of §6 contribution).
      </code_to_reuse>
      <docs_to_consult>
        - 406-CONTEXT.md `<decisions>` "HRN-08 granularity" + "HRN-08 exemplar Slice" — verbatim source for §6.
        - 406-CONTEXT.md `<specifics>` 3rd bullet — framing.
        - REQUIREMENTS.md HRN-08 — req-level constraint.
        - 403 EXEMPLAR-stepNPLAN.md — exemplar Slice canonical authorship.
        - 402 SLICE-CYCLE.md — canonical 4-stage event names.
        - 402 CONTEXT-PROTOCOL.md CTX-04 + CTX-09 — emergency / reactive trigger surfaces for §6.2.
        - 404 ANALYSIS-PARALYSIS-GUARD.md APG-03 — research-slice 15-read threshold.
        - 405 DEVIATION-RULES.md DEV-05 — checkpoint:decision autonomy interaction.
        - gsd-2 `kb/cross-layer-communication-map.md` §3 — end-to-end flow framing.
        - gsd-2 `kb/walkthroughs/interactive-mode/INDEX.md` — pipeline walkthrough framing source.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable. v14's harness implementation will replay this sequence diagram's event emissions as a smoke-test fixture; v14 EXEMPLAR work owns the fixture authoring.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 1450)}' \
        && grep -qE "^## §6 Full-Slice Lifecycle Sequence Diagram \(HRN-08\)" "$F" \
        && grep -qE "^### Exemplar Slice" "$F" \
        && grep -qE "^### Full-Slice Mermaid Sequence Diagram" "$F" \
        && grep -qE "^### Event \+ Intervention Tabulation" "$F" \
        && grep -qE "^### Phase 402-405 Cross-Reference per Stage|^### Phase 402–405 Cross-Reference per Stage" "$F" \
        && grep -qE "^## Rollup complete \(Phase 406\)" "$F" \
        && grep -q "compaction-snapshot-schema" "$F" \
        && grep -q "Task 1" "$F" \
        && grep -q "Task 2" "$F" \
        && grep -q "Task 3" "$F" \
        && grep -q "RED" "$F" \
        && grep -q "GREEN" "$F" \
        && grep -q "checkpoint:decision" "$F" \
        && grep -q "orjson" "$F" \
        && grep -q "design-slice" "$F" \
        && grep -q "research-slice" "$F" \
        && grep -q "run-slice" "$F" \
        && grep -q "verify-slice" "$F" \
        && grep -q "TIER-1 ADVISORY\\|tier=advisory" "$F" \
        && grep -q "TIER-2 BLOCK\\|tier=tool_block" "$F" \
        && grep -q "TIER-3 REINJECT\\|tier=clear_reinject" "$F" \
        && grep -q "TIER-4 HUMAN GATE\\|tier=human_gate" "$F" \
        && grep -q "HRN-08 satisfied" "$F" \
        && grep -q "All 8 HRN requirements are covered" "$F" \
        && grep -q "HRN-01" "$F" \
        && grep -q "HRN-02" "$F" \
        && grep -q "HRN-03" "$F" \
        && grep -q "HRN-04" "$F" \
        && grep -q "HRN-05" "$F" \
        && grep -q "HRN-06" "$F" \
        && grep -q "HRN-07" "$F" \
        && grep -q "HRN-08" "$F" \
        && grep -qE "^\\*Phase 406 rollup canonical" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[15]] §6 heading + 4 sub-section headings (Exemplar Slice, Full-Slice Mermaid Sequence Diagram, Event + Intervention Tabulation, Phase 402–405 Cross-Reference per Stage) present.
    - [check: must_haves.truths[16]] §6.1 names the exemplar Slice `compaction-snapshot-schema` + cross-cites CTX-05, STP-04, PRF, DEV-05.
    - [check: must_haves.truths[17]] §6.2 Mermaid sequenceDiagram renders ≥6 participants + the 4 Slice stages + the 3 exemplar tasks.
    - [check: must_haves.truths[18]] §6.2 Mermaid shows ≥1 emission of state.harness.intervention at each of 4 tiers: tier=advisory, tier=tool_block, tier=clear_reinject, tier=human_gate.
    - [check: must_haves.truths[19]] §6.3 tabulation block asserts the floors (≥25 events, ≥4 tier-emissions, 4 Slice-stage events, 3+ step-lifecycle events, ≥4 counter events).
    - [check: must_haves.truths[20]] §6.4 stage-by-stage cross-reference table covers all 4 stages with 402–405 spec section pointers.
    - [check: must_haves.truths[21]] §6 closing "HRN-08 satisfied" paragraph rendered.
    - [check: must_haves.truths[22]] "Rollup complete (Phase 406)" heading + 8-HRN coverage statement rendered.
    - [check: must_haves.truths[23]] Closing footer "Phase 406 rollup canonical" + STATE-* discipline statement rendered.
    - [check: must_haves.truths[24]] No `GSD-` literal in the file.
    - [check: must_haves.artifacts[0]] File ≥1450 lines.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md grows by ~200 lines (§6 + rollup-complete closing); file ≥1450 lines; Mermaid sequence diagram covers 4 Slice stages + 3 exemplar tasks + 4 tier-intervention emissions; HRN-08 satisfied; rollup-complete heading asserts coverage of all 8 HRN requirements; verify-block bash passes; no `GSD-` literal; §0–§5 untouched.
  </done>
</task>

</tasks>

<verification>
After both tasks complete (final phase-406 spec verification):

```bash
F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md

# All 7 main sections from §0 through Rollup-Complete present
for section in \
  "^# Harness Architecture \(Canonical, v41 Rollup\)" \
  "^## §1 Layered Diagram \(HRN-01\)" \
  "^## §2 Plugin Hook Inventory \(HRN-02\)" \
  "^## §3 state-build MCP Tool Catalog \(HRN-03\)" \
  "^## §4 4-Tier Intervention Ladder" \
  "^## §5 Event-Replay Reconstruction Proof \(HRN-07\)" \
  "^## §6 Full-Slice Lifecycle Sequence Diagram \(HRN-08\)" \
  "^## Rollup complete \(Phase 406\)"; do
  grep -qE "$section" "$F" || { echo "MISSING: $section"; exit 1; }
done

# §6 sub-sections
for section in \
  "^### Exemplar Slice" \
  "^### Full-Slice Mermaid Sequence Diagram" \
  "^### Event \+ Intervention Tabulation" \
  "^### Phase 402"; do
  grep -qE "$section" "$F" || { echo "MISSING_SUB: $section"; exit 1; }
done

# All 4 tier emissions named in §6 sequence diagram
for tier_marker in "tier=advisory\\|TIER-1 ADVISORY" "tier=tool_block\\|TIER-2 BLOCK" "tier=clear_reinject\\|TIER-3 REINJECT" "tier=human_gate\\|TIER-4 HUMAN GATE"; do
  grep -qE "$tier_marker" "$F" || { echo "MISSING_TIER: $tier_marker"; exit 1; }
done

# Exemplar Slice tasks named
for task_marker in "Task 1" "Task 2" "Task 3" "RED" "GREEN" "checkpoint:decision" "orjson"; do
  grep -q "$task_marker" "$F" || { echo "MISSING_TASK_MARKER: $task_marker"; exit 1; }
done

# 4 canonical Slice stages
for stage in design-slice research-slice run-slice verify-slice; do
  grep -q "$stage" "$F" || { echo "MISSING_STAGE: $stage"; exit 1; }
done

# All 8 HRN covered + line count
grep -q "All 8 HRN requirements are covered" "$F" || { echo "MISSING_8HRN_COVERAGE"; exit 1; }
for hrn in HRN-01 HRN-02 HRN-03 HRN-04 HRN-05 HRN-06 HRN-07 HRN-08; do
  grep -q "$hrn" "$F" || { echo "MISSING_HRN: $hrn"; exit 1; }
done

# Mermaid blocks (§1 + §5 + §6 = at least 3)
N_MERMAID=$(grep -cE '^```mermaid' "$F")
[ "$N_MERMAID" -ge 3 ] || { echo "MERMAID_COUNT_FAIL: $N_MERMAID"; exit 1; }

# Line count
wc -l "$F" | awk '{ if ($1 < 1450) { print "LINE_COUNT_FAIL: " $1; exit 1 } }'

# Naming discipline
! grep -qE '\bGSD-' "$F" || { echo "GSD_NAMING_VIOLATION"; exit 1; }

echo "HARNESS-ARCHITECTURE.md §5 + §6 + ROLLUP-COMPLETE verification OK"
echo "Phase 406 spec canonical."
```
</verification>

<success_criteria>
- §5 + §6 + Rollup-Complete heading appended to HARNESS-ARCHITECTURE.md; total file ≥1450 lines.
- §5 5-category replay-input enumeration + 5-step reconstruction protocol + worked daemon-restart example with Mermaid restart-flow diagram + restart-safety closing statement all render verbatim per 406-CONTEXT.md.
- §6 full-Slice Mermaid sequence diagram covers 4 stages (design / research / run / verify) + 3 exemplar tasks (RED / GREEN / checkpoint:decision orjson) + 4 tier-intervention emission points (advisory / tool_block / clear_reinject / human_gate).
- §6.3 tabulation asserts ≥25 events + ≥4 tier-emissions + 4 Slice-stage events.
- §6.4 stage cross-reference table covers all 4 stages with 402–405 spec section pointers.
- Closing "Rollup complete (Phase 406)" heading asserts all 8 HRN requirements covered with cross-references to §1–§6.
- File contains ≥3 Mermaid blocks (§1 layered, §5 restart-flow, §6 full-Slice lifecycle).
- §0–§5 untouched by this plan.
- No `GSD-` literal in the file (project naming discipline).
- The HARNESS-ARCHITECTURE.md is the canonical Phase 406 spec at this plan's completion.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/406/04-replay-proof-sequence-diagram-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: final HARNESS-ARCHITECTURE.md line count, sections rendered (§5 + §6 + Rollup-Complete + closing footer), HRN-07 + HRN-08 coverage verification (5-category enumeration + 5-step protocol + worked example with Mermaid + full-Slice Mermaid with 4-tier emission coverage + ≥25-event floor + 4-stage walk), naming-discipline verification result (`grep '\bGSD-' = 0`), and a final phase-406 spec-canonical assertion stating all 8 HRN requirements satisfied.

Note: this is the final plan of Phase 406. After this plan's SUMMARY lands, the execute-phase wrap-up will: (1) auto-spawn `/gsd:secure-phase 406` to produce 406-SECURITY.md per CLAUDE.md mandatory-SECURITY rule; (2) run goal-backward verification producing 406-VERIFICATION.md per the must_haves dispatch — every artifact line-count + every truths regex + every key_links pattern must validate. Plan 04 is the wave-4 capstone.
</output>
