# Phase 406: Harness Architecture Rollup — Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 406 produces a single canonical specification document:

1. **`HARNESS-ARCHITECTURE.md`** — the v41 harness rollup. Consolidates all 12 prior v41 specs (`SLICE-CYCLE.md`, `CONTEXT-PROTOCOL.md`, `STEP-PLAN-FORMAT.md`, `PLAN-AS-PROMPT.md`, `STEP-EVENTS.md`, `EXEMPLAR-stepNPLAN.md`, `PROOF-GATE.md`, `ANALYSIS-PARALYSIS-GUARD.md`, `SCOPE-PROHIBITION.md`, `DEVIATION-RULES.md`, `SUBAGENT-MANAGEMENT.md`, `SUBAGENT-MONITORING.md`) into one layered architecture document that:

- Renders the **3-layer physical decomposition** (HRN-01): plugin hooks → state-build MCP server → state-daemon, with named per-component arrows showing control flow.
- Inventories every **plugin hook** (HRN-02) with TS signature, firing trigger, role (inject/block/record), and back-cross-reference to the v41 REQ category it implements (CTX/PAP/PRF/APG/SRP/DEV/SUB).
- Enumerates the **state-build MCP tool catalog** (HRN-03) with full inline Pydantic input/output models (`extra="forbid"`) for every tool; every harness operation specified in Phases 402–405 maps to at least one MCP tool.
- Defines the **4-tier intervention ladder** (HRN-04: advisory inject → tool-block → force clear+reinject → force-stop + human gate) with the explicit trigger source from each prior phase that escalates at each tier.
- Defines the **`state.harness.intervention` Pydantic event schema** (HRN-05) as the umbrella over APG `paralysis_event`, PRF `gate_strike`, DEV `deviation_logged`, SUB `subagent_crash_detected` chains; asserts the **human-gate-only-via-opencode-`question`-tool rule** (HRN-06).
- Specifies the **event-replay reconstruction proof** (HRN-07): the canonical list of events that must replay to rebuild full harness state, plus a numbered reconstruction protocol with a daemon-restart worked example demonstrating restart-safety.
- Walks **one full Slice lifecycle as a Mermaid sequence diagram** (HRN-08): design-slice → research-slice → run-slice (with one Step) → verify-slice → close, showing every event emitted (~25–30 events) and every harness intervention point. The exemplar Slice is the `compaction-snapshot-schema` Slice from 403's `EXEMPLAR-stepNPLAN.md`.

Phase 406 is **design-only — no code lands.** Spec output is implemented by v14 (Build Kernel) and v15 (Build Core Commands). Every check specified or cross-referenced here is **pure-machine** (PRF-04 spirit carries forward); no LLM-as-judge anywhere in the umbrella event, the intervention ladder, or the replay proof.

</domain>

<decisions>
## Implementation Decisions

### Naming discipline (project-wide, carried forward from 405)

**All new identifiers MUST be `STATE-*` or `state-*`, never `GSD-*`.** State is its own project; gsd-2 is the design heritage and is cited extensively, but trailer prefixes, event names, module paths, env vars, CLI commands, and file prefixes use state's identity. Phase 406 introduces:

- Event: `state.harness.intervention` (the HRN-05 umbrella; sole rollup point for APG/PRF/DEV/SUB chains)
- Module: `state_build/harness/intervention/` (umbrella event emitter + tier dispatcher)
- Registry: `MCP_TOOL_REGISTRY: dict[ToolName, type[McpToolBase]]` at `state_build/mcp/registry.py` (mirrors Phase 405 `SUBAGENT_RETURN_REGISTRY` exhaustive-via-`assert_never` pattern)

### Vocabulary carry-forward (402)

v40 vocabulary wins: **design-slice / research-slice / run-slice / verify-slice** (NOT v41 REQUIREMENTS' `discuss-slice/plan-slice/execute-slice`). Stage-boundary events are `state.slice.{design,research,run,verify}_completed` per 402 `SLICE-CYCLE.md`.

### Document structure (Area 1 of discussion)

**Single monolithic `HARNESS-ARCHITECTURE.md`.** All seven HRN-01..08 sections live in one file. Matches the success criteria literal wording ("A `HARNESS-ARCHITECTURE.md` spec document contains…"). Expected size ~50–70k LOC; in line with prior v41 specs (22–58k each).

**Hybrid cross-reference depth.** Inline operative contracts (Pydantic schemas + MCP tool signatures + event payloads) verbatim; pointer-only for explanatory prose. Matches Phase 405's pattern where SUBAGENT-MONITORING.md inlines payloads but cross-references DEVIATION-RULES.md for cross-validation prose. Drift between inlined schema and source spec is a documented defect.

**Section ordering — layers → ladder → lifecycle, matching HRN-01..08 literal:**

1. §1 Layered diagram (HRN-01)
2. §2 Plugin hook inventory (HRN-02)
3. §3 state-build MCP tool catalog (HRN-03)
4. §4 4-tier intervention ladder + `harness_intervention` event + human-gate-only-via-`question`-tool (HRN-04, HRN-05, HRN-06)
5. §5 Event-replay reconstruction proof (HRN-07)
6. §6 Full-Slice lifecycle sequence diagram (HRN-08)

**No amendments to prior v41 specs.** The rollup references forward; the 12 prior 402–405 specs stay as-shipped. Phase 405 already amended v40 EVENT-TAXONOMY.md / ARTIFACT-CATALOG.md / FRONTMATTER-SCHEMAS.md; 406 does not extend that amendment chain. Forward-cross-references in 402–405 specs that mention "HRN-04/05 (Phase 406)" are already in place and need no edit.

### Diagram form & fidelity (Area 2 of discussion)

**Mermaid only.** All diagrams (HRN-01 layered, HRN-08 sequence) are rendered as Mermaid code blocks. Matches PROOF-GATE.md §5 (sequenceDiagram for tool.execute.before stack), 402 SLICE-CYCLE.md stage diagrams, and every kb/ comm-map.

**HRN-01 detail level — box-per-component with named-arrow edges:**

- 3 layer subgraphs:
  - **Hooks layer:** 6 named hook boxes (`chat.params`, `chat.message`, `tool.execute.before`, `tool.execute.after`, `session.compacting`, `shell.env`).
  - **state-build MCP server:** ~12–18 named tool boxes (full roster — see §"MCP tool roster" below).
  - **state-daemon:** 5 named service boxes (event store, projector, scheduler, SSE bus, crash recovery / orphan reconciliation).
- Edges labeled with operation (e.g., `tool.execute.before → log_deviation → cross-validation 1-5`, `subagent_complete → spot_check stack → SubagentSpotCheckFailed`).
- Mirrors kb/cross-layer-communication-map.md §1 layered Mermaid topology.

**HRN-08 granularity — every event + every harness intervention point.** Walk the full Slice lifecycle showing every event firing (~25–30 events) and every intervention site (paralysis advisories, gate strikes, deviation logs, subagent crashes, scope checks, context-meter threshold crosses). HRN-08 literal: "every event emitted and every harness intervention point." Expected diagram size: ~80–120 Mermaid lines.

**HRN-08 exemplar Slice — reuse 403's `EXEMPLAR-stepNPLAN.md`.** The `compaction-snapshot-schema` Slice with 1 Step containing 3 tasks (RED test → GREEN implement → `checkpoint:decision` for orjson flag). Already canonically authored; mature `must_haves`, `<threat_model>`, `<verify>`. Lets HRN-08 cite literal task names and events. Cross-cites Phase 402 CTX-05 (CompactionSnapshot model), Phase 403 STP-04 (`<task>` sub-tag), Phase 404 PRF (must_haves evaluator dispatch), Phase 405 DEV-05 (autonomy interaction on the `checkpoint:decision` task).

### MCP tool catalog (Area 3 of discussion)

**Full Pydantic input/output models inline per tool.** HRN-03 literal: "enumerates every tool with input and output Pydantic models." Matches Phase 405 SUBAGENT-MANAGEMENT §2 which inlines DispatchSubagent/SingleDispatch/ParallelDispatch/ChainDispatch verbatim. Every tool entry includes:

- Tool name (literal `state-build` MCP server registration string)
- Module path (`state_build/<subsystem>/<tool>.py`)
- Pydantic input model (`extra="forbid"`)
- Pydantic output model (`extra="forbid"`)
- 1–2 sentence semantics + pointer to canonical spec section in 402–405
- Plugin-hook integration site (which `tool.execute.before` / `after` layer consumes this tool's call, if any)

**Tool roster — exhaustive map of every Phase 402–405 harness operation.** HRN-03 literal: "every harness operation specified in Phases 402–405 is mapped to at least one MCP tool." The roster (12–18 tools; planner finalizes exact count during plan-slice):

| Tool name | Owning phase | Source spec |
|---|---|---|
| `complete_task` | 403/404 | STEP-PLAN-FORMAT.md §5 task-type behaviors; PROOF-GATE.md §6 strike trigger |
| `complete_slice` | 402/404 | SLICE-CYCLE.md run-slice → verify-slice transition; PROOF-GATE.md §4 Slice-end |
| `request_step_split` | 404 | SCOPE-PROHIBITION.md SRP-05 |
| `scope_deviation_request` | 404 | SCOPE-PROHIBITION.md §"scope_deviation_request MCP Tool Flow" |
| `log_deviation` | 405 | DEVIATION-RULES.md §3 |
| `dispatch_subagent` | 405 | SUBAGENT-MANAGEMENT.md §2 |
| `check_proof_gate` (Step-end / Slice-end driver) | 404 | PROOF-GATE.md §4 numbered protocol |
| `emit_advisory` (tier-1 intervention) | 406 (new) | HRN-04 tier 1 |
| `force_clear_and_reinject` (tier-3 intervention) | 406 (new) | HRN-04 tier 3 |
| `surface_human_gate` (tier-4 intervention) | 406 (new) | HRN-04 tier 4 + HRN-06 |
| `query_context_meter` | 402 | CONTEXT-PROTOCOL.md CTX-08 |
| `request_compaction_snapshot` | 402 | CONTEXT-PROTOCOL.md CTX-03 (daemon-initiated path) |
| `query_event_store` (replay-only read API) | 406 (new) | HRN-07 reconstruction protocol |
| `record_plan_edit` (PAP-04 emit-site) | 403 | PLAN-AS-PROMPT.md §6 |

Hooks-vs-MCP-tools partition: **plugin hooks are sensors + enforcers; MCP tools are agent-driven actions.** Hooks (`chat.params`/`message`, `tool.execute.before/after`, `session.compacting`, `shell.env`) READ harness state and BLOCK writes; MCP tools (`log_deviation`, `dispatch_subagent`, etc.) are what the agent calls to signal intent. Preserves 402's "plugin is thin reporter, daemon decides" and 405's "typed-spawn only via MCP tool" disciplines.

**Registration / exhaustiveness pattern.** Specify `MCP_TOOL_REGISTRY: dict[ToolName, type[McpToolBase]]` at `state_build/mcp/registry.py` mirroring Phase 405 SUBAGENT_RETURN_REGISTRY (SUB-06). Each tool registers a Pydantic input + output class; `mypy --strict src/state_build/mcp/` catches missing registrations. v14 inherits the pattern.

### harness_intervention event + 4-tier ladder (Area 4 of discussion)

**`HarnessIntervention` Pydantic class inline in HARNESS-ARCHITECTURE.md.** Umbrella + 4-tier discriminator. Sketch:

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

class HarnessIntervention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: Literal["advisory", "tool_block", "clear_reinject", "human_gate"]
    trigger_reason: Literal[
        # APG (404)
        "paralysis_threshold_crossed",
        "paralysis_chain_3_reinject",
        "paralysis_chain_6_human_gate",
        # PRF (404)
        "gate_strike_advisory",
        "gate_strike_3_reinject",
        "gate_strike_6_human_gate",
        # DEV (405)
        "deviation_logged_pending",
        "deviation_cap_exceeded",
        "deviation_rule_4_architectural",
        # SUB (405)
        "subagent_spot_check_failed",
        "subagent_crash_detected",
        "subagent_restart_exhausted",
        "subagent_orphan_persistent",
        # SCOPE (404 SRP)
        "scope_check_unresolved",
        "scope_deviation_rejected",
        # CTX (402)
        "context_threshold_warning",
        "context_threshold_emergency",
        "context_overflow_reactive",
    ]
    target_step_or_task: str                      # task_id or step_id depending on chain
    correlation_event_id: str                     # the originating gate_strike / paralysis_event / deviation_logged / subagent_crash_detected / scope_check / harness.context_meter event id
    slice_id: str
    session_id: str
    triggered_at: datetime                        # UTC, ISO-8601
```

**Emission model — alongside source events, NOT replacing.** The originating chain emits its own event (e.g., `state.step.paralysis_event` with `tier="reinject"`); the daemon middleware additionally emits `state.harness.intervention` with `tier="clear_reinject"` and `correlation_event_id` pointing at the paralysis_event row. Two events per intervention; replay can reconstruct the umbrella view from `state.harness.intervention` rows OR from the per-chain rows independently. Mirrors the gsd-2 cross-layer comm-map pattern where one runtime action surfaces in multiple bus views.

**4-tier ladder — trigger source enumeration:**

| Tier | Trigger sources |
|---|---|
| Tier 1: advisory inject | APG advisory 1-2 + 4-5; PRF strike 1-2 + 4-5; DEV `log_deviation` accepted (pending resolution); SCOPE `scope_check` unresolved without exception; SUB `subagent_spot_check_failed` first occurrence on a tuple |
| Tier 2: tool-block (via `tool.execute.before`) | SRP-04 `files_modified` allowlist (Layer 1); PAP-05 immutability (Layer 2); SRP-02 prohibited-language (Layer 3); PRF-07 gate-failing next-task block (Layer 4); SUB-03 `subagent_whitelist_violation` (Layer 6 stage 2); SUB-04 `subagent_cap_expansion_rejected` (Layer 6 stage 3); CTX-04 warning threshold (≤35%) next-task block |
| Tier 3: force clear+reinject | APG advisory 3 (paralysis chain reinject); PRF strike 3 (gate chain reinject); CTX-04 emergency threshold (≤25%); CTX-09 reactive overflow recovery one-shot |
| Tier 4: force-stop + human gate (opencode `question` tool only) | APG advisory 6; PRF strike 6; DEV Rule 4 architectural (always-stop, even under `--full-yolo`); DEV cap_exceeded → Rule 3 `checkpoint:decision` OR Rule 4 promotion; SUB `subagent_restart_exhausted`; SUB persistent orphan reconciliation step 6 |

**Human-gate-only-via-opencode-`question`-tool (HRN-06).** Asserted as a structural invariant: the harness NEVER invents its own UI for human gates. Every tier-4 path renders via opencode's `question` tool with the named alternatives payload. The absence of any other UI surface in `state_build/harness/intervention/` is the structural enforcement; CI grep targets the directory and rejects PRs introducing alternate UI primitives. Mirrors the absence-of-bypass pattern from Phase 405 DEV-04 (no `full_yolo bypass` branch in `state_build/deviation/log_deviation.py`).

### Event-replay reconstruction (HRN-07)

**Replay-input enumeration — categorized 5-table breakdown:**

| Category | Events | Owning spec |
|---|---|---|
| 1. Slice-stage chain | `state.slice.{design,research,run,verify}_completed` | 402 SLICE-CYCLE.md |
| 2. Plan-lifecycle chain | `state.step.plan_authored`, `plan_edit`, `plan_edit_blocked`, `checkpoint_auto_resolved`, `checkpoint_human_action_pending`, `checkpoint_human_action_resolved`, `state.step.renamed`, `state.step.added`, `state.step.removed` (9 events) | 403 STEP-EVENTS.md |
| 3. Counter chains | APG `paralysis_event`; PRF `gate_strike`, `gate_resolved`, `step_verify_completed`, `slice_verify_completed`; DEV `deviation_logged`, `deviation_classification_rejected`, `deviation_resolution_recorded`, `deviation_cap_exceeded`; SUB `subagent_started`, `subagent_progress`, `subagent_complete`, `subagent_spot_check_failed`, `subagent_crash_detected`, `subagent_restart`, `subagent_restart_exhausted`, `subagent_orphan_detected` | 404 + 405 |
| 4. Scope chain | `scope_check`, `scope_deviation`, `scope_deviation_request`, `scope_deviation_resolved`; `subagent_whitelist_violation`, `subagent_cap_expansion_rejected` | 404 SRP + 405 SUB |
| 5. Umbrella + context | `state.harness.intervention` (this phase's emission); `compaction.snapshot_taken`, `compaction.reinject_completed`, `harness.context_meter` | 406 + 402 |

Total: ~30 event types. For each: event type → Pydantic class → owning spec. The table IS the HRN-07 enumeration.

**Reconstruction protocol — numbered + worked example:**

1. Daemon boot. Open `.state/events.sqlite` via single-writer facade (gsd-2 single-writer-sqlite-facade pattern; project carry-forward).
2. Load latest `CompactionSnapshot` row per active Slice (Phase 402 §8); seed projector state from the snapshot's `slice_id`, `step_id`, `task_id`, `prior_session_id`, `provides_blocks`, `current_task_pointer`, `last_verify_result`, `subagent_restart_counters`, `in_flight_subagents` (Phase 405 SUB-08 extension).
3. Replay events forward from `first_kept_entry_id` onward, applying per-chain reducers:
   - APG counter (`state_build/paralysis/counter.py`): per-task consecutive read-only count.
   - PRF counter (`state_build/proof/counter.py`): per-`(task_id, check_id)` strike chain.
   - DEV counter (`state_build/deviation/counter.py`): per-`(task_id, rule_id, issue_signature)` attempt chain.
   - SUB counter (`state_build/subagents/restart_counter.py`): per-`(parent_task_id, subagent_type)` restart chain.
   - Intervention chain (`state_build/harness/intervention/projector.py`): per-tier accumulation.
4. Reconcile orphan subagents (Phase 405 SUB-08 §6 6-step protocol): for each `subagent_started` without paired terminal event, probe opencode session API; emit synthetic `subagent_orphan_detected` for confirmed-gone tasks; persistent orphans surface as DEV-04 Rule 4 human gate.
5. Resume plugin hooks. `chat.params` re-injects the latest reinject payload (CTX-06); `tool.execute.before` re-attaches the 6-layer write-block stack.

**Worked example:** daemon restart mid-`run-slice` with 2 in-flight subagents, paralysis counter at 4 of 6 on `task-3`, last `CompactionSnapshot` taken 30s before restart. Show:
- Snapshot rehydration: paralysis counter `task-3 → 4`, restart counters `task-2|researcher → 1`, `task-2|pattern-mapper → 0`.
- Replay catches 6 additional `subagent_progress` events post-snapshot for both in-flight subagents.
- Orphan probe: opencode reports both still running; daemon re-subscribes to SSE for both session_ids.
- Plugin hook resume: `chat.params` re-injects with `<prior_crash>` block if any restart-chain has fired.

Total: ~15–25 lines of worked-example prose plus a Mermaid sequence diagram of the restart flow.

### Plan decomposition

**4 plans — fine granularity per `.planning/config.json` granularity=fine and 200k Slice budget:**

| Plan | Title | HRN coverage | Expected LOC |
|---|---|---|---|
| 01 | Layered diagram + plugin hook inventory | HRN-01, HRN-02 | ~10–15k |
| 02 | state-build MCP tool catalog | HRN-03 | ~15–20k |
| 03 | 4-tier intervention ladder + harness_intervention event | HRN-04, HRN-05, HRN-06 | ~10–15k |
| 04 | Event-replay reconstruction proof + full-Slice sequence diagram | HRN-07, HRN-08 | ~15–20k |

Each plan within fine-granularity 3–5 step budget per CTX-01. Matches 402–405 plan pattern (4 plans per phase).

### Claude's Discretion

The following are deferred to planner / executor discretion within the boundaries above:

- **Mermaid styling** (subgraph colors, edge styles, node shapes) — pick for readability; no aesthetic constraints from this CONTEXT.
- **Tool name finalization** (the 14 names in the roster table above are the canonical starter set; plan-02 may rename `record_plan_edit` if a more idiomatic name emerges, but the operation count is locked).
- **Per-tier event count enumeration accuracy** (the ~30-event count is approximate; HRN-07 §1 may surface that some events double-count as both per-chain and umbrella).
- **Worked-example narrative depth** (HRN-07 worked example: 1 paragraph minimum, 4 paragraphs maximum).
- **Section anchor naming** (use `#hrn-01-layered-diagram` style or any consistent slug pattern).
- **MCP catalog table layout** (table-per-tool vs section-per-tool — pick for readability against the ~14 tool entries).

</decisions>

<code_context>
## Existing Code Insights

### Prior v41 specs (12 docs, ~480k total) — all carried forward

Phase 406 consolidates these into one rollup. Each is cited inline by HARNESS-ARCHITECTURE.md:

- `402/specs/SLICE-CYCLE.md` (22.8k) — 4-stage cycle, 4 stage-boundary events, Slice folder layout, v40 vocabulary reconciliation.
- `402/specs/CONTEXT-PROTOCOL.md` (33.5k) — 200k absolute budget, fresh-session-per-Slice, intra-Slice compaction, 4-row threshold action table, `CompactionSnapshot` Pydantic, reinject payload, identifier survival, context-meter wiring, reactive overflow.
- `403/specs/STEP-PLAN-FORMAT.md` (39.6k) — frontmatter schema, XML body sections, 5 task types, granularity algorithm, planner validation hooks.
- `403/specs/PLAN-AS-PROMPT.md` (37.0k) — injection flow, @-reference resolution, mutability matrix, `plan_edit` event, immutability enforcer, content stripping.
- `403/specs/STEP-EVENTS.md` (28.7k) — 9 step-tier event Pydantic schemas + field constraints + replay verification.
- `403/specs/EXEMPLAR-stepNPLAN.md` (17.4k) — canonical worked example (the `compaction-snapshot-schema` Slice); reused by HRN-08 sequence diagram.
- `404/specs/PROOF-GATE.md` (47.4k) — `must_haves` evaluator dispatch, gate evaluation order, 4-layer `tool.execute.before` write-block stack (layers 1-4), strike counter with 6-strike ladder, `GateStrike`/`GateResolved`/`StepVerifyCompleted`/`SliceVerifyCompleted` event payloads.
- `404/specs/ANALYSIS-PARALYSIS-GUARD.md` (54.5k) — bash classifier (`bash_classifier.py`), `READ_ONLY_PATTERNS`/`WRITE_SYSCALL_PATTERNS`/`COMPOUND_SEP`, per-step-type threshold table, 6-advisory ladder, `ParalysisEvent` payload.
- `404/specs/SCOPE-PROHIBITION.md` (53.2k) — `<done>`-vs-artifacts cross-check (SRP-01), prohibited-language scan (SRP-02), tracking-issue exception (SRP-03), `files_modified` allowlist with `tool.execute.before` Layer 1 (SRP-04), `request_step_split` MCP tool (SRP-05), `deferred-items.md` (SRP-06). Owns 2 of the 4 write-block layers shared with PROOF-GATE.
- `405/specs/DEVIATION-RULES.md` (58.7k) — 4-rule deviation framework (DEV-01..04), tiered autonomy table (DEV-05) + per-Slice override (DEV-06), `Deviation` event payload + ring of 4 deviation events, `log_deviation` MCP tool with 5-step cross-validation, `ARCH_PATTERN_ALLOWLIST` for Rule-4 detection, `STATE-*` commit trailer convention, `## Deviations` SUMMARY projector.
- `405/specs/SUBAGENT-MANAGEMENT.md` (36.1k) — `dispatch_subagent` MCP tool + 3 modes (single/parallel/chain), `SubagentType` 14-element Literal + `STAGE_ROSTER` 4-stage frozenset map, narrowing-only `allowed_subagents` frontmatter with 2-gate enforcement (plan-validation + runtime), 20-default parallel cap with FIFO queuing, `assert_never` compile-time exhaustiveness.
- `405/specs/SUBAGENT-MONITORING.md` (53.1k) — 8 new SSE event types, `SUBAGENT_RETURN_REGISTRY` central Pydantic registry, 4-layer pure-machine spot-check stack (process / Pydantic / artifact / commit), 5-source crash taxonomy + 3-restart counter, `<prior_crash>` continuation XML block, `task_id` survival across compaction + Slice-boundary respawn, daemon-down orphan reconciliation 6-step protocol.

### gsd-2 KB patterns (`~/Projects/gsd2deconstruction/kb/`) — pattern source

Phase 406 inherits these patterns. Cited by HARNESS-ARCHITECTURE.md where each is operative:

- `kb/INDEX.md` + `kb/cross-layer-communication-map.md` — 5-layer architecture spine + topology master map; template for HRN-01 layered Mermaid.
- `kb/core/communication-map.md` (M1 hub-and-spoke around AgentSession with Bus A / Bus B) + `kb/app/communication-map.md` (M4 hub around `sdk.ts:createAgentSession()`) — templates for HRN-01's hub-and-spoke per layer.
- `kb/extensions/plugin-system.md` — plugin hook surface, 25 emit methods + `invokeHandlers` primitive, 6-strategy composition taxonomy. Template for HRN-02 hook inventory.
- `kb/core/tool-system.md` — typed-tool registry, TypeBox schema passthrough, factory-with-pluggable-operations. Template for HRN-03 MCP tool catalog.
- `kb/walkthroughs/interactive-mode/INDEX.md` + slices 4-6 (`04-slice-4-init.md`, `05-slice-5-run.md`, `06-slice-6-event-queue.md`) — 16-step init pipeline, main run loop, promise-queue event serialization. Template for HRN-08 lifecycle sequence diagram.
- Pattern catalog: `three-layer-llm-orchestration.md`, `host-as-extension-self-hosting.md`, `deep-module-with-adapter-seams.md`, `single-writer-sqlite-facade.md`, `extension-hook-dispatch.md`, `gating-event-dispatcher-with-composition.md`, `before-agent-start-context-assembly.md`, `pre-agent-config-pipeline-with-extension-hooks.md`, `extension-runner-ref-object-for-circular-dep.md`, `tool-factory-with-pluggable-operations.md`, `tool-args-validation-via-schema-passthrough.md`, `exhaustive-registry-with-satisfies-constraint.md`, `pure-decision-kernel-with-discriminated-actions.md`, `dispatch-rules-table.md`, `sliding-window-with-ledger-suppression.md`, `llm-mediated-trigger-table.md`, `db-driven-crash-recovery.md`, `snapshot-persistence.md`, `derived-state-from-db-decision-tree.md` — pattern bank for individual section authoring.

### Reusable assets

- **`state_core/schema.py:239-265`** — `EventEnvelope` outer shape; carries every event in this rollup. The `data: dict[str, Any]` field carries the umbrella `HarnessIntervention` payload alongside per-chain payloads.
- **`state_core/projector`** (existing CQRS handler registration) — projector pattern reused by `state_build/harness/intervention/projector.py` for umbrella event reduction.
- **Phase 405 `state_build/commit/trailers.py`** — trailer rendering helper; Phase 406 does NOT introduce new trailers (no commit machinery in this phase).

### Established patterns (carry-forward)

- **Pure-machine everywhere** (PRF-04 spirit). The umbrella event has no LLM-as-judge; tier classification is a deterministic dispatch from the source chain's tier.
- **Plugin-as-thin-reporter, daemon-decides** (402 carry-forward). Hooks emit/block; daemon middleware owns intervention dispatch.
- **`extra="forbid"` on every Pydantic class.** Unknown field at parse time = `ValidationError`; never silently ignored.
- **Single-source-of-truth modules.** Every registry, regex corpus, and pattern table lives in exactly one Python file imported by every consumer.
- **Server-side recomputation of aggregates** (gsd-2 `server-recomputation-of-llm-emitted-fields.md`; carried by Phases 404/405). The umbrella `tier` is server-derived, never agent-emitted.
- **4-counter independence** (404 PROOF-GATE.md §6 + 405 DEVIATION-RULES.md §6 + 405 SUBAGENT-MONITORING.md §4): APG/PRF/DEV/SUB chains never share state; the `harness_intervention` event is the SOLE rollup point.
- **Append-only event store** (PROJECT.md cardinal rule). Every event in the replay list is append-only; corrections are NEW events.

### Integration points

- **v14 Build Kernel** — implements the daemon's HTTP middleware (including the 6-layer write-block stack: Phase 404 layers 1-4 + Phase 405 layers 5-6), the projector replay-verifier, the `MCP_TOOL_REGISTRY` dispatch, and the `state.harness.intervention` emitter.
- **v15 Build Core Commands** — wires per-stage emitters into the research-slice pipeline + the execute-slice harness; consumes the rollup as the implementation contract.
- **v9 TUI bundle** (shipped) — subscribes to `state.harness.intervention` SSE stream; renders tier-1 (advisory toast), tier-2 (block reason), tier-3 (reinject banner), tier-4 (opencode `question` tool surface via daemon-coordinated hand-off).

</code_context>

<specifics>
## Specific Ideas

- **"The rollup is the index, not the source of truth."** Each prior 402–405 spec stays canonical for its own subsystem; HRN-ARCHITECTURE.md is the consolidation lens that lets a reader see the whole harness at once without reading 480k of prior specs first. Per-section content depth follows the hybrid cross-ref rule: inline operative contracts, pointer-only for prose.

- **"Use Phase 405's two-part split as the precedent for what NOT to do here."** Phase 405 split into SUBAGENT-MANAGEMENT (Part 1) + SUBAGENT-MONITORING (Part 2) because the spawn surface and monitoring surface were architecturally distinct. Phase 406's six sections are NOT architecturally distinct — they are six views of the same harness. One file.

- **"HRN-08 should feel like the gsd-2 cross-layer comm-map §3 end-to-end flow."** That section walks one user prompt across all 5 layers showing every cross-layer hop. HRN-08 walks one Slice across all 4 stages showing every event + intervention. Same shape, different scope.

- **"The replay proof's worked example must show a hard case."** Daemon restart with mid-flight subagents is the hard case; the easy case (clean Slice close) does not exercise orphan reconciliation, counter rehydration, or `<prior_crash>` continuation context. The worked example is the proof that the protocol works under the realistic failure mode.

- **"The 4-tier ladder enumeration is HRN-04's load-bearing claim."** Listing the trigger sources for each tier from APG/PRF/DEV/SUB/SCOPE/CTX prevents the umbrella event from being aspirational. The reader can ground-truth-check: "what fires when APG advisory 3 lands?" Answer: `state.step.paralysis_event(tier=reinject)` + `state.harness.intervention(tier=clear_reinject, trigger_reason=paralysis_chain_3_reinject)` simultaneously.

</specifics>

<deferred>
## Deferred Ideas

The following ideas surfaced during discussion or prior-phase reading but belong in other phases. Captured here so they're not lost.

- **`HarnessIntervention.tier_strike_count` projection** — a derived field summing per-tier counts across the umbrella chain. Useful for v9 TUI rendering; defer to v14 EXEMPLAR work, NOT spec'd here.
- **Per-tool latency budget in the MCP catalog** — each tool's allowed wall-clock budget (e.g., `log_deviation` ≤ 200ms; `check_proof_gate` ≤ 120s for Step-end). Useful for v14 performance regression detection; defer to v14 EXEMPLAR.
- **Cross-host event-store replay determinism test fixture** — a frozen event-store dump that any v14 implementation MUST be able to replay to the same projector state. Defer to v14 EXEMPLAR + v17 portability milestone.
- **Subagent grandchild fanout cap** — Phase 405 SUB-04 deferred grandchild concurrency to post-v17. Phase 406 inherits the deferral; the rollup does NOT introduce new cap discipline.
- **Per-`subagent_type` cap differentiation** — Phase 405 SUB-04 deferred. Inherited.
- **Priority-FIFO subagent queue** — Phase 405 SUB-04 deferred. Inherited.
- **Slot acquisition timeout** — Phase 405 SUB-04 deferred. Inherited.
- **`SubagentReturn` discriminated-union dispatch in v14 unit tests** — Phase 405 SUB-06 deferred. Inherited.
- **Atomic-write for `.state/build/last-snapshot.md`** — Phase 402 §8 acknowledged not-yet-atomic; v44 Rust DB rewrite addresses. Inherited.
- **Atomic-write for `stepNSUMMARY.md` `## Deviations` section** — Phase 405 §10 noted; v44 addresses. Inherited.
- **GSD-* → STATE-* legacy trailer rename pass** — Phase 405 `<deferred>` noted past-phase trailer references inherited from gsd-2 design heritage. Defer to a dedicated cleanup phase post-v41.
- **Teach-mode harness equivalent** — explicitly v47 scope. Mode silos remain physical (`state.build.harness.*` MUST NOT import `state.teach.*`). The rollup is Build-only.
- **Long-running harness telemetry** (mean strikes per Step, paralysis frequency by step-type, deviation rule firing rates) — v2 REQUIREMENT `HARNESS-METRICS`; post-v17.
- **Pattern observer for harness threshold tuning** — v2 REQUIREMENT `HARNESS-LEARNING`; post-v17.
- **Portability shims for Claude Code / Gemini CLI / Qwen Code** — v2 REQUIREMENT `PORTABILITY-HARNESS`; v26.
- **Rust DB / event-store rewrite** — v44 milestone; affects how the replay proof's "load latest snapshot" step is implemented but does NOT change the contract.
- **Mid-execution Slice scope expansion** — explicitly out-of-scope v41 (per ROADMAP.md Out of Scope). Scope is locked at end of plan-slice; expansion requires a re-plan event.

</deferred>

---

*Phase: 406-harness-architecture-rollup*
*Context gathered: 2026-05-12*
