---
phase: 406
plan: 02
type: execute
wave: 2
depends_on:
  - "406-01"
files_modified:
  - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
autonomous: true
requirements:
  - HRN-03

must_haves:
  truths:
    - "HARNESS-ARCHITECTURE.md exists at .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Plan 01 created it) and §3 is appended by THIS plan (Plan 02). The file already contains §0 + §1 + §2 from Plan 01; this plan appends §3 without modifying §0–§2."
    - "§3 heading is rendered verbatim: `## §3 state-build MCP Tool Catalog (HRN-03)`. The section opens with a 1-paragraph intro stating: every harness operation specified in Phases 402–405 maps to at least one MCP tool (HRN-03 literal requirement); the catalog enumerates 14 tools; each tool entry includes the literal MCP registration string, module path `state_build/<subsystem>/<tool>.py`, Pydantic input model (`extra=\"forbid\"`), Pydantic output model (`extra=\"forbid\"`), 1–2 sentence semantics + pointer to canonical spec section in 402–405, and plugin-hook integration site."
    - "§3 includes the canonical 14-tool roster table rendered verbatim from 406-CONTEXT.md `<decisions>` 'MCP tool catalog (Area 3)' subsection. Table columns: Tool name | Owning phase | Source spec. All 14 tool names appear in this exact order: complete_task, complete_slice, request_step_split, scope_deviation_request, log_deviation, dispatch_subagent, check_proof_gate, emit_advisory, force_clear_and_reinject, surface_human_gate, query_context_meter, request_compaction_snapshot, query_event_store, record_plan_edit."
    - "§3 includes a `### MCP_TOOL_REGISTRY` subsection documenting `MCP_TOOL_REGISTRY: dict[ToolName, type[McpToolBase]]` at module path `state_build/mcp/registry.py`. The pattern mirrors Phase 405 `SUBAGENT_RETURN_REGISTRY` (SUB-06): each tool registers a Pydantic input + output class; `mypy --strict src/state_build/mcp/` catches missing registrations. The `ToolName` Literal union is rendered with all 14 names verbatim."
    - "§3 includes a `### Exhaustiveness via assert_never` subsection rendering the dispatcher match-case pattern with all 14 tool names as cases and `case _: assert_never(tool_name)` final case. Mirrors Phase 405 SUBAGENT-MANAGEMENT.md Section 4 `assert_never` pattern. CI runs `mypy --strict src/state_build/mcp/` to catch missing dispatcher cases at type-check time."
    - "§3 renders 14 per-tool sub-subsections (one per tool) in the same order as the roster table. Each per-tool entry has a literal heading `### {tool_name}` and contains: (1) MCP registration string verbatim (the literal name registered with `state-build` MCP server); (2) Module path `state_build/<subsystem>/<tool_filename>.py`; (3) Semantics — 1-2 sentence purpose; (4) Source spec pointer — canonical 402–405 (or 406-self) location; (5) Pydantic input model class definition; (6) Pydantic output model class definition; (7) Plugin-hook integration site (which tool.execute.before/after layer consumes this tool, if any)."
    - "Each of the 14 per-tool Pydantic input + output classes is rendered as a `python` code-fence with `model_config = ConfigDict(extra=\"forbid\")` on EVERY class. Required input/output fields are typed (no `Any` field types; every field has a concrete Pydantic-compatible type, with `Literal` discriminators where applicable)."
    - "Tool `complete_task` is documented with input `{task_id: str, step_id: str, slice_id: str, verify_passed: bool, evidence: dict[str, Any]}` and output `{accepted: bool, gate_strike_id: str | None, next_task_id: str | None}`. Cites STEP-PLAN-FORMAT.md §5 (task-type behaviors) + PROOF-GATE.md §6 (strike trigger on verify_passed=False). Integration site: tool.execute.before layer 4 — gate-failing next-task block."
    - "Tool `complete_slice` is documented with input `{slice_id: str, verification_passed: bool, n_verification_md_path: str}` and output `{accepted: bool, slice_event_id: str}`. Cites SLICE-CYCLE.md run-slice → verify-slice transition + PROOF-GATE.md §4 Slice-end."
    - "Tool `request_step_split` is documented per SCOPE-PROHIBITION.md SRP-05 with input `{step_id: str, reason: str, proposed_split: list[str]}` and output `{split_recommendation_event_id: str, replan_required: bool}`."
    - "Tool `scope_deviation_request` is documented per SCOPE-PROHIBITION.md SRP-04 with input `{task_id: str, requested_path: str, justification: str}` and output `{request_event_id: str, granted: bool, granted_paths: list[str] | None}`. Integration site: tool.execute.before layer 2 — files_modified allowlist consults open requests."
    - "Tool `log_deviation` is documented per DEVIATION-RULES.md §3 with input `{task_id: str, rule_id: Literal[1,2,3,4], issue_signature: str, classification_source: Literal['agent_declared','harness_promoted','arch_pattern_match'], alternatives: list[Rule4Option] | None, error_excerpt: str, agent_response_summary: str}` and output `{deviation_event_id: str, attempt_number: int, cap_exceeded: bool, classification_accepted: bool, rejection_reason: str | None}`. Integration site: tool.execute.before layer 5."
    - "Tool `dispatch_subagent` is documented per SUBAGENT-MANAGEMENT.md §2 with input `{single: SingleDispatch | None, parallel: ParallelDispatch | None, chain: ChainDispatch | None}` (exactly-one-mode root validator from 405) and output `{dispatched_task_ids: list[str], queued_count: int, rejected: list[SubagentRejection]}`. Integration site: tool.execute.before layer 6 — whitelist + parallel-cap."
    - "Tool `check_proof_gate` is documented per PROOF-GATE.md §4 with input `{scope: Literal['task','step','slice'], scope_id: str, must_haves: MustHavesBlock | None, automated_command: str | None}` and output `{gate_passed: bool, failed_checks: list[FailedCheck], strike_count: int, escalation_action: Literal['none','advisory','reinject','human_gate']}`."
    - "Tool `emit_advisory` is documented (NEW in Phase 406) with input `{task_id: str, advisory_text: str, source_trigger: Literal['paralysis','gate_strike','deviation_pending','scope_unresolved','subagent_spot_check']}` and output `{advisory_event_id: str, intervention_event_id: str}`. Section §4 (Plan 03) documents the HRN-04 tier-1 advisory inject site that calls this tool."
    - "Tool `force_clear_and_reinject` is documented (NEW in Phase 406) with input `{session_id: str, slice_id: str, trigger_reason: Literal['paralysis_chain_3_reinject','gate_strike_3_reinject','context_threshold_emergency','context_overflow_reactive']}` and output `{compaction_event_id: str, reinject_event_id: str, intervention_event_id: str}`. Cross-references HRN-04 tier 3 (Plan 03) and CTX-09 reactive overflow (CONTEXT-PROTOCOL.md)."
    - "Tool `surface_human_gate` is documented (NEW in Phase 406) with input `{task_id: str | None, slice_id: str, question_text: str, alternatives: list[QuestionAlternative], trigger_reason: Literal['paralysis_chain_6_human_gate','gate_strike_6_human_gate','deviation_rule_4_architectural','deviation_cap_exceeded','subagent_restart_exhausted','subagent_orphan_persistent','scope_deviation_rejected']}` and output `{question_event_id: str, intervention_event_id: str, awaiting_human: bool}`. Asserts the human-gate-only-via-opencode-`question`-tool invariant (HRN-06)."
    - "Tool `query_context_meter` is documented per CONTEXT-PROTOCOL.md CTX-08 with input `{session_id: str}` and output `{tokens_used: int, tokens_remaining: int, percent_remaining: float, model_window: int}`. Plugin-hook integration site: invoked from tool.execute.after to mirror meter state to SSE."
    - "Tool `request_compaction_snapshot` is documented per CONTEXT-PROTOCOL.md CTX-03 with input `{session_id: str, slice_id: str, current_task_id: str, daemon_initiated: bool}` and output `{snapshot_event_id: str, reinject_payload_bytes: bytes}`. Plugin-hook integration site: returns payload consumed by session.compacting hook."
    - "Tool `query_event_store` is documented (NEW in Phase 406) per HRN-07 reconstruction protocol with input `{event_types: list[str], aggregate_id: str | None, from_seq: int | None, to_seq: int | None, limit: int}` and output `{events: list[EventEnvelope], total_matched: int}`. Read-only API consumed by replay protocol (Plan 04 §5) and TUI projection."
    - "Tool `record_plan_edit` is documented per PLAN-AS-PROMPT.md PAP-04 with input `{step_id: str, diff: str, editor: Literal['executor','harness','human']}` and output `{plan_edit_event_id: str, accepted: bool, immutability_violation: str | None}`. Integration site: tool.execute.before layer 1 — PAP-05 immutability check rejects edits to must_haves.* / <verify> blocks."
    - "§3 includes a `### Hook integration matrix` subsection rendering a markdown table mapping each of the 14 tools to its tool.execute.before/after layer (or 'no hook' for purely agent-driven tools like `complete_task`/`complete_slice`). The matrix covers all 14 tools."
    - "§3 includes a `### Mode-isolation note` subsection asserting `state_build/mcp/` MUST NOT import from `state_teach/`; CI import-graph lint enforces; all 14 tools register under the `state-build` MCP server (not `state-teach`)."
    - "§3 includes a `### Cross-reference to operations in Phases 402–405` paragraph asserting (verbatim from HRN-03): 'every harness operation specified in Phases 402–405 is mapped to at least one MCP tool.' Followed by a coverage matrix mapping each REQ category (CTX, STP, PAP, PRF, APG, SRP, DEV, SUB) to the MCP tools that implement its operations."
    - "HARNESS-ARCHITECTURE.md does NOT contain the literal string `GSD-` anywhere (project naming-discipline rule — STATE-* / state-* only)."
  artifacts:
    - path: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      provides: "Phase 406 rollup — adds §3 state-build MCP Tool Catalog (HRN-03). All 14 tools enumerated with Pydantic input/output models, module paths, source-spec pointers, plugin-hook integration sites. MCP_TOOL_REGISTRY + assert_never exhaustiveness pattern documented."
      min_lines: 800
  key_links:
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      via: "§3 log_deviation tool entry inlines the Rule4Option + DeviationLogResult Pydantic shapes from DEVIATION-RULES.md §3 verbatim; pointer-back for cross-validation prose"
      pattern: "DEVIATION-RULES\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      via: "§3 dispatch_subagent tool entry inlines DispatchSubagent/SingleDispatch/ParallelDispatch/ChainDispatch + the exactly-one-mode root validator note from SUBAGENT-MANAGEMENT.md §2 verbatim"
      pattern: "SUBAGENT-MANAGEMENT\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "§3 check_proof_gate tool entry inlines MustHavesBlock + FailedCheck + GateScope shapes from PROOF-GATE.md §4 verbatim; pointer-back for evaluator-dispatch prose"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "§3 query_context_meter + request_compaction_snapshot tool entries cite CTX-03/CTX-05/CTX-08 verbatim; pointer-back for CompactionSnapshot Pydantic shape"
      pattern: "CONTEXT-PROTOCOL\\.md"
---

<objective>
Append §3 to the canonical `HARNESS-ARCHITECTURE.md` spec document — the state-build MCP Tool Catalog (HRN-03). This section enumerates all 14 MCP tools with full Pydantic input/output models (`extra="forbid"`), module paths, source-spec pointers, plugin-hook integration sites, the `MCP_TOOL_REGISTRY` exhaustive-via-`assert_never` pattern, and a hook integration matrix.

This is Wave 2: depends on Plan 01 (which created the file with §0 + §1 + §2). Plan 03 will append §4 (intervention ladder), Plan 04 will append §5 + §6 (replay proof + sequence diagram). All 4 plans modify the SAME file, hence the strict 1→2→3→4 wave sequencing.

Purpose: HRN-03 fully covered. Downstream consumers — Plan 03 (references `emit_advisory`, `force_clear_and_reinject`, `surface_human_gate` for §4 tier-1/3/4 intervention sites; references `log_deviation`, `dispatch_subagent`, `check_proof_gate` for tier-source enumeration), Plan 04 (references `query_event_store` for §5 reconstruction protocol; references `complete_task`/`complete_slice` for §6 lifecycle sequence), v14 Build Kernel (implements `MCP_TOOL_REGISTRY` dispatch + every per-tool handler from this catalog), v15 Build Core Commands (wires MCP server registration to opencode plugin) — all read from this section.

Output: §3 appended to `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md`, bringing file total to ≥800 lines. §3 contains: 1-paragraph intro, 14-tool roster table, MCP_TOOL_REGISTRY subsection with `ToolName` Literal union, `assert_never` exhaustiveness pattern, 14 per-tool sub-subsections (each ≥25 lines with full Pydantic input + output classes), hook-integration-matrix table, mode-isolation note, cross-reference paragraph asserting 100% Phase-402–405 operation coverage. No `GSD-` identifier appears.
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
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
@.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
@.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — 14-tool roster (verbatim from 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" subsection). USE THIS LIST VERBATIM — the planner has locked the exact 14 names:

```
| Tool name                                | Owning phase | Source spec |
|---|---|---|
| complete_task                            | 403/404      | STEP-PLAN-FORMAT.md §5 + PROOF-GATE.md §6 |
| complete_slice                           | 402/404      | SLICE-CYCLE.md run→verify + PROOF-GATE.md §4 |
| request_step_split                       | 404          | SCOPE-PROHIBITION.md SRP-05 |
| scope_deviation_request                  | 404          | SCOPE-PROHIBITION.md "scope_deviation_request MCP Tool Flow" |
| log_deviation                            | 405          | DEVIATION-RULES.md §3 |
| dispatch_subagent                        | 405          | SUBAGENT-MANAGEMENT.md §2 |
| check_proof_gate                         | 404          | PROOF-GATE.md §4 |
| emit_advisory                            | 406 (new)    | HRN-04 tier 1 |
| force_clear_and_reinject                 | 406 (new)    | HRN-04 tier 3 |
| surface_human_gate                       | 406 (new)    | HRN-04 tier 4 + HRN-06 |
| query_context_meter                      | 402          | CONTEXT-PROTOCOL.md CTX-08 |
| request_compaction_snapshot              | 402          | CONTEXT-PROTOCOL.md CTX-03 |
| query_event_store                        | 406 (new)    | HRN-07 reconstruction protocol |
| record_plan_edit                         | 403          | PLAN-AS-PROMPT.md §6 |
```

Excerpt B — Pydantic class rendering convention (from Phase 405 SUBAGENT-MANAGEMENT.md §2):

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class DispatchSubagent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    single: SingleDispatch | None = None
    parallel: ParallelDispatch | None = None
    chain: ChainDispatch | None = None
    # Root validator: sum(1 for x in (single, parallel, chain) if x is not None) == 1
```

Excerpt C — `MCP_TOOL_REGISTRY` pattern (from 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" subsection, mirroring Phase 405 `SUBAGENT_RETURN_REGISTRY` from SUB-06):

```python
# state_build/mcp/registry.py
from typing import assert_never

ToolName = Literal[
    "complete_task", "complete_slice", "request_step_split", "scope_deviation_request",
    "log_deviation", "dispatch_subagent", "check_proof_gate",
    "emit_advisory", "force_clear_and_reinject", "surface_human_gate",
    "query_context_meter", "request_compaction_snapshot", "query_event_store",
    "record_plan_edit",
]

class McpToolBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Per-tool input/output models are subclasses

MCP_TOOL_REGISTRY: dict[ToolName, type[McpToolBase]] = {
    # Each value is the per-tool Pydantic class registering input + output schemas
    ...
}
```

Excerpt D — Phase 405 SubagentRejection shape (used in dispatch_subagent output):

```python
# Reference: SUBAGENT-MANAGEMENT.md §5 — subagent_whitelist_violation event payload shape
class SubagentRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requested: str
    reason: Literal["whitelist_violation", "cap_exceeded", "stage_mismatch"]
    expected: list[str] | None = None
```

Excerpt E — Phase 404 PROOF-GATE.md `MustHavesBlock` shape (used in check_proof_gate input):

```python
# Reference: PROOF-GATE.md §"must_haves frontmatter block"
class MustHavesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truths: list[str]
    artifacts: list[ArtifactCheck]
    key_links: list[KeyLinkCheck]
```

Excerpt F — `EventEnvelope` (used in query_event_store output):

```python
# Reference: state_core/schema.py:239-265
class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    seq: int
    aggregate_type: str
    aggregate_id: str
    type: str
    data: dict[str, Any]
```

Excerpt G — `Rule4Option` (used in log_deviation input):

```python
# Reference: DEVIATION-RULES.md §"log_deviation MCP tool signature"
class Rule4Option(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    pros: list[str]
    cons: list[str]
    recommended: bool  # Exactly one option must have recommended=True
```

Excerpt H — `QuestionAlternative` (used in surface_human_gate input; matches opencode `question` tool's alternatives payload):

```python
# Reference: opencode question tool spec; mirrors Rule4Option for cross-tool consistency
class QuestionAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    detail: str | None = None
```
</interfaces>

<threat_model>
Phase 406 is design-only. §3 of HARNESS-ARCHITECTURE.md introduces no production attack surface — it is a markdown specification rolled up from 402–405 (plus 4 new tools defined in this phase: `emit_advisory`, `force_clear_and_reinject`, `surface_human_gate`, `query_event_store`). Threats considered:

- **[med] Spec inaccuracy in inlined Pydantic shapes could mislead v14 implementation.** Mitigation: every per-tool input/output Pydantic class is rendered with `model_config = ConfigDict(extra="forbid")` and matches the source spec's authoritative shape verbatim (e.g., `dispatch_subagent` input = `DispatchSubagent` from 405 SUBAGENT-MANAGEMENT.md §2; `log_deviation` input matches DEVIATION-RULES.md §3). Drift is detectable by grep against the source spec.
- **[med] Naming-discipline drift (STATE-* vs GSD-*).** Mitigation: verify-block bash includes `! grep -qE '\bGSD-' "$F"` — fails the plan if a `GSD-` identifier appears. Tool names are state-* exclusively.
- **[med] `MCP_TOOL_REGISTRY` exhaustiveness gap.** If a future patch adds a `ToolName` Literal value without registering in `MCP_TOOL_REGISTRY` or without adding the dispatcher case, runtime could fail-open. Mitigation in spec: `assert_never` exhaustiveness pattern documented; CI runs `mypy --strict src/state_build/mcp/` to catch at type-check time. Mirrors 405 SUBAGENT-MANAGEMENT.md Section 4 pattern.
- **[med] 4 NEW Phase-406 tools (`emit_advisory`, `force_clear_and_reinject`, `surface_human_gate`, `query_event_store`) — first specification.** No upstream spec covers these. Mitigation: each NEW tool's Pydantic input/output is documented in this section AND cross-referenced to its operational owner: `emit_advisory` ↔ HRN-04 tier 1 (Plan 03 §4); `force_clear_and_reinject` ↔ HRN-04 tier 3 (Plan 03 §4); `surface_human_gate` ↔ HRN-04 tier 4 + HRN-06 (Plan 03 §4); `query_event_store` ↔ HRN-07 reconstruction protocol (Plan 04 §5). Plans 03 and 04 reference these tools by name; consistency is grep-detectable across §3 ↔ §4 ↔ §5.
- **[low] Mode-isolation drift.** Mitigation: explicit `### Mode-isolation note` subsection asserting `state_build/mcp/` MUST NOT import `state_teach/`.

No production code lands. No secrets, no network calls. The spec describes MCP-tool contracts; v14 implements.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Append §3 intro + 14-tool roster table + MCP_TOOL_REGISTRY + assert_never exhaustiveness subsection</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Plan 01's output — §0 + §1 + §2; APPEND §3 below, do NOT modify existing sections)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3 of discussion)" — verbatim source for 14-tool roster + MCP_TOOL_REGISTRY pattern + hooks-vs-MCP partition + 14-tool registration pattern (`state_build/mcp/registry.py`)
    - .planning/milestones/v41/REQUIREMENTS.md lines 124-128 (HRN-03 verbatim)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md Sections 2 + 4 — DispatchSubagent + SingleDispatch + ParallelDispatch + ChainDispatch Pydantic classes + assert_never pattern (verbatim source for dispatch_subagent entry in Task 2 AND for MCP_TOOL_REGISTRY exhaustiveness pattern in this task)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md (search "SUBAGENT_RETURN_REGISTRY" — registry pattern precedent)
    - .planning/milestones/v41/phases/405/01-deviation-rules-spec-PLAN.md lines 100-180 (rendering-convention reference for log_deviation entry in Task 2)
  </read_first>

  <action>
    Append §3 intro + roster + registry subsections to the existing HARNESS-ARCHITECTURE.md. **DO NOT modify §0, §1, or §2.** **Concrete content from 406-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 3 — state-build MCP Tool Catalog (HRN-03) — intro

    Heading: `## §3 state-build MCP Tool Catalog (HRN-03)`.

    1-paragraph intro (render verbatim with adaptations as noted):

    "HRN-03 specifies the state-build MCP server tool catalog. **Every harness operation specified in Phases 402–405 maps to at least one MCP tool** (HRN-03 literal). This section enumerates 14 tools. Each tool entry includes the literal MCP registration string (the name the agent invokes), the module path `state_build/<subsystem>/<tool_filename>.py` (single-source-of-truth), the Pydantic input model and output model (both with `model_config = ConfigDict(extra=\"forbid\")`), 1–2 sentences of semantics plus a pointer to the canonical 402–405 spec section, and the plugin-hook integration site (which `tool.execute.before` / `after` layer consumes this tool's invocation, when applicable). Of the 14 tools, 10 are owned by Phases 402–405 source specs and 4 are NEW in this phase: `emit_advisory` (HRN-04 tier 1), `force_clear_and_reinject` (HRN-04 tier 3), `surface_human_gate` (HRN-04 tier 4 + HRN-06), `query_event_store` (HRN-07 replay-only read API)."

    Sub-section `### Hooks-vs-MCP partition (cross-reference)`:

    "Plugin hooks (§2) are sensors + enforcers (READ state, BLOCK writes). MCP tools (this section) are agent-driven actions (the agent CALLS them to signal intent). The two surfaces communicate through the daemon middleware — the daemon decides; hooks and MCP tools execute. Cross-reference from 406-CONTEXT.md `<decisions>` 'MCP tool catalog' subsection."

    ### Section 3.1 — Tool roster

    Heading: `### Tool roster`.

    Render verbatim the 14-tool table from 406-CONTEXT.md:

    ```
    | # | Tool name                       | Owning phase | Source spec section                                  |
    |---|---------------------------------|--------------|-------------------------------------------------------|
    | 1 | complete_task                   | 403 + 404    | STEP-PLAN-FORMAT.md §5; PROOF-GATE.md §6              |
    | 2 | complete_slice                  | 402 + 404    | SLICE-CYCLE.md run-slice→verify-slice; PROOF-GATE.md §4 |
    | 3 | request_step_split              | 404          | SCOPE-PROHIBITION.md SRP-05                            |
    | 4 | scope_deviation_request         | 404          | SCOPE-PROHIBITION.md "scope_deviation_request MCP Tool Flow" |
    | 5 | log_deviation                   | 405          | DEVIATION-RULES.md §3                                  |
    | 6 | dispatch_subagent               | 405          | SUBAGENT-MANAGEMENT.md §2                              |
    | 7 | check_proof_gate                | 404          | PROOF-GATE.md §4                                       |
    | 8 | emit_advisory                   | 406 (new)    | THIS spec §4 (Plan 03) — HRN-04 tier 1                 |
    | 9 | force_clear_and_reinject        | 406 (new)    | THIS spec §4 (Plan 03) — HRN-04 tier 3 + CTX-09        |
    |10 | surface_human_gate              | 406 (new)    | THIS spec §4 (Plan 03) — HRN-04 tier 4 + HRN-06        |
    |11 | query_context_meter             | 402          | CONTEXT-PROTOCOL.md CTX-08                             |
    |12 | request_compaction_snapshot     | 402          | CONTEXT-PROTOCOL.md CTX-03                             |
    |13 | query_event_store               | 406 (new)    | THIS spec §5 (Plan 04) — HRN-07 reconstruction         |
    |14 | record_plan_edit                | 403          | PLAN-AS-PROMPT.md PAP-04 / §6                          |
    ```

    Note (verbatim): "The 14-tool roster is the v1 canonical surface. v14 implements; v15 wires; v17+ may extend (extension requires a new harness spec phase, not a v1 amendment to this rollup)."

    ### Section 3.2 — MCP_TOOL_REGISTRY

    Heading: `### MCP_TOOL_REGISTRY`.

    1-paragraph intro: "The 14 tools are registered in a single-source-of-truth dictionary `MCP_TOOL_REGISTRY: dict[ToolName, type[McpToolBase]]` at module path `state_build/mcp/registry.py`. Mirrors Phase 405 `SUBAGENT_RETURN_REGISTRY` from SUB-06. Every tool registers a Pydantic input + output class; `mypy --strict src/state_build/mcp/` catches missing registrations at type-check time."

    Sub-section `#### ToolName Literal`:

    Render verbatim:

    ```python
    # state_build/mcp/registry.py
    from typing import Literal

    ToolName = Literal[
        # Phase 402–405 owned tools
        "complete_task",
        "complete_slice",
        "request_step_split",
        "scope_deviation_request",
        "log_deviation",
        "dispatch_subagent",
        "check_proof_gate",
        "query_context_meter",
        "request_compaction_snapshot",
        "record_plan_edit",
        # Phase 406 NEW tools
        "emit_advisory",
        "force_clear_and_reinject",
        "surface_human_gate",
        "query_event_store",
    ]
    ```

    Sub-section `#### McpToolBase + registry`:

    Render verbatim:

    ```python
    from pydantic import BaseModel, ConfigDict

    class McpToolBase(BaseModel):
        model_config = ConfigDict(extra="forbid")

    class McpToolSpec(BaseModel):
        model_config = ConfigDict(extra="forbid")
        name: ToolName
        module_path: str          # e.g., "state_build/deviation/log_deviation.py"
        input_model: type[McpToolBase]
        output_model: type[McpToolBase]

    MCP_TOOL_REGISTRY: dict[ToolName, McpToolSpec] = {
        # Populated by per-tool module __init__ side effect or explicit register() call.
        # v14 implements; CI verifies len(MCP_TOOL_REGISTRY) == len(typing.get_args(ToolName)).
        ...
    }
    ```

    Note: "v14 unit test asserts `set(MCP_TOOL_REGISTRY.keys()) == set(typing.get_args(ToolName))` — registry exhaustiveness check that fails CI when a new ToolName is added without registry entry. Mirrors gsd-2 `exhaustive-registry-with-satisfies-constraint.md`; state's Python analog uses `set(...) == set(get_args(...))` + `assert_never` together."

    ### Section 3.3 — Exhaustiveness via assert_never

    Heading: `### Exhaustiveness via assert_never`.

    Render verbatim:

    ```python
    from typing import assert_never

    def dispatch_mcp_tool(tool_name: ToolName, payload: dict) -> McpToolBase:
        match tool_name:
            case "complete_task":              return handle_complete_task(payload)
            case "complete_slice":             return handle_complete_slice(payload)
            case "request_step_split":         return handle_request_step_split(payload)
            case "scope_deviation_request":    return handle_scope_deviation_request(payload)
            case "log_deviation":              return handle_log_deviation(payload)
            case "dispatch_subagent":          return handle_dispatch_subagent(payload)
            case "check_proof_gate":           return handle_check_proof_gate(payload)
            case "emit_advisory":              return handle_emit_advisory(payload)
            case "force_clear_and_reinject":   return handle_force_clear_and_reinject(payload)
            case "surface_human_gate":         return handle_surface_human_gate(payload)
            case "query_context_meter":        return handle_query_context_meter(payload)
            case "request_compaction_snapshot": return handle_request_compaction_snapshot(payload)
            case "query_event_store":          return handle_query_event_store(payload)
            case "record_plan_edit":           return handle_record_plan_edit(payload)
            case _:
                assert_never(tool_name)
    ```

    Note: "A future patch adding a `ToolName` Literal value without adding the dispatcher case raises a mypy/pyright error at type-check time. CI MUST run `mypy --strict src/state_build/mcp/`. Mirrors Phase 405 SUBAGENT-MANAGEMENT.md Section 4 `assert_never` pattern with identical 14-case shape."

    Sub-section `#### Mode-isolation note`:

    Render verbatim: "`state_build/mcp/` and every per-tool module under `state_build/<subsystem>/` MUST NOT import from `state_teach/`. CI import-graph lint enforces. All 14 tools register under the `state-build` MCP server (not `state-teach`). Build-mode-only discipline (PROJECT.md cardinal rule, 405 carry-forward)."

    <quality_scan>
      <code_to_reuse>
        - Known: 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" — 14-tool roster + `MCP_TOOL_REGISTRY` pattern (`state_build/mcp/registry.py` module path) verbatim source.
        - Known: 405 SUBAGENT-MANAGEMENT.md Section 4 — `assert_never` exhaustiveness pattern; THIS task mirrors with 14 tool cases instead of 14 subagent_type cases.
        - Known: 405 SUBAGENT-MONITORING.md — `SUBAGENT_RETURN_REGISTRY` pattern precedent.
        - Grep pattern: `grep -nE "assert_never|MCP_TOOL_REGISTRY|SUBAGENT_RETURN_REGISTRY" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/*.md | head -20` — locates registry exhaustiveness precedent.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` — confirms current §0–§2 heading hierarchy before appending §3.
      </code_to_reuse>
      <docs_to_consult>
        - 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3 of discussion)" — verbatim source for roster table + registration pattern.
        - 406-CONTEXT.md `<decisions>` "Document structure (Area 1)" — section ordering confirms §3 lives between §2 and §4.
        - 405 SUBAGENT-MANAGEMENT.md Section 4 — `assert_never` Python pattern reference.
        - 405 SUBAGENT-MONITORING.md — `SUBAGENT_RETURN_REGISTRY` central-registry pattern.
        - gsd-2 `exhaustive-registry-with-satisfies-constraint.md` — TS `satisfies` pattern; state's Python analog.
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
        && wc -l "$F" | awk '{exit ($1 < 470)}' \
        && grep -qE "^## §3 state-build MCP Tool Catalog \(HRN-03\)" "$F" \
        && grep -qE "^### Tool roster" "$F" \
        && grep -qE "^### MCP_TOOL_REGISTRY" "$F" \
        && grep -qE "^### Exhaustiveness via assert_never" "$F" \
        && grep -q "every harness operation specified in Phases 402–405\|every harness operation specified in Phases 402-405\|every harness operation" "$F" \
        && grep -q "ToolName = Literal" "$F" \
        && grep -q "complete_task" "$F" \
        && grep -q "complete_slice" "$F" \
        && grep -q "log_deviation" "$F" \
        && grep -q "dispatch_subagent" "$F" \
        && grep -q "emit_advisory" "$F" \
        && grep -q "force_clear_and_reinject" "$F" \
        && grep -q "surface_human_gate" "$F" \
        && grep -q "query_event_store" "$F" \
        && grep -q "record_plan_edit" "$F" \
        && grep -q "MCP_TOOL_REGISTRY" "$F" \
        && grep -q "state_build/mcp/registry.py" "$F" \
        && grep -q "assert_never(tool_name)" "$F" \
        && grep -q "McpToolBase" "$F" \
        && grep -qE 'model_config = ConfigDict\(extra="forbid"\)' "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] §3 appended; §0–§2 unchanged (verify by ensuring §1 + §2 content still present).
    - [check: must_haves.truths[1]] §3 heading + intro paragraph match the literal text including "every harness operation specified in Phases 402–405" phrasing.
    - [check: must_haves.truths[2]] 14-tool roster table renders verbatim with the locked names in the locked order.
    - [check: must_haves.truths[3]] `MCP_TOOL_REGISTRY` subsection documents the dict + module path + 14-element ToolName Literal.
    - [check: must_haves.truths[4]] `assert_never` dispatcher subsection renders all 14 tool cases.
    - [check: must_haves.truths[23]] Mode-isolation note rendered.
    - [check: must_haves.truths[24]] No `GSD-` literal in the file.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md grows by ~120 lines (§3 intro + roster + registry + exhaustiveness subsections); file ≥470 lines; verify-block bash passes; no `GSD-` literal; §0–§2 untouched.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append §3.4 — 14 per-tool sub-subsections with Pydantic input/output models + hook integration matrix + coverage paragraph</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Task 1's output — append the 14 per-tool sub-subsections + hook matrix + coverage paragraph)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (search "log_deviation|Rule4Option|DeviationLogResult|ARCH_PATTERN_ALLOWLIST" — Pydantic shapes for log_deviation entry)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md Section 2 — DispatchSubagent + SingleDispatch + ParallelDispatch + ChainDispatch + SubagentType verbatim for dispatch_subagent entry
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (search "must_haves|MustHavesBlock|FailedCheck|GateScope|check_proof_gate" — Pydantic shapes for check_proof_gate entry)
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (search "scope_deviation_request|request_step_split" — input/output shapes for SRP-04 + SRP-05 entries)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "CompactionSnapshot|context_meter|query_context_meter|request_compaction_snapshot" — Pydantic shapes for query_context_meter + request_compaction_snapshot entries; also CTX-09 trigger_reason for force_clear_and_reinject NEW tool)
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (search "plan_edit|record_plan_edit" — PAP-04 shape for record_plan_edit entry)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (search "complete_task" — STP-04 task-completion semantics)
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md (search "complete_slice|verify-slice|run-slice" — slice-completion semantics)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md (search "SubagentRejection|subagent_whitelist_violation" — rejection shape for dispatch_subagent output)
  </read_first>

  <action>
    Append §3.4 (14 per-tool sub-subsections), §3.5 (hook integration matrix), and §3.6 (coverage paragraph) to the existing HARNESS-ARCHITECTURE.md. **DO NOT modify any prior section.** **Concrete content from upstream specs verbatim where available — do NOT re-derive published shapes.**

    ### Section 3.4 — Per-tool catalog entries

    Heading: `### Per-tool catalog entries`.

    For each of the 14 tools, render a sub-subsection in the locked order. Each entry follows this template (with the per-tool details below):

    ```
    #### {N}. {tool_name}

    **MCP registration:** `state-build:{tool_name}`
    **Module path:** `state_build/<subsystem>/<filename>.py`
    **Owning phase:** {phase}
    **Source spec:** {pointer}
    **Semantics:** {1-2 sentences}
    **Plugin-hook integration site:** {hook + layer, or "no hook — agent-only" }

    **Input model:**
    ```python
    class {ToolName}Input(McpToolBase):
        model_config = ConfigDict(extra="forbid")
        ...
    ```

    **Output model:**
    ```python
    class {ToolName}Output(McpToolBase):
        model_config = ConfigDict(extra="forbid")
        ...
    ```
    ```

    Use the following per-tool details (literal field names + types — do NOT re-derive; values below are the authoritative shapes for this rollup):

    **#### 1. complete_task**
    - Module path: `state_build/tasks/complete_task.py`
    - Owning phase: 403 + 404
    - Source spec: STEP-PLAN-FORMAT.md §5 (task-type behaviors), PROOF-GATE.md §6 (strike trigger on verify_passed=False)
    - Semantics: Agent signals task completion. Daemon runs task `<verify><automated>` + `<acceptance_criteria>` per PRF-05; on failure, increments `gate_strike` counter per PRF-06.
    - Plugin-hook integration site: tool.execute.before layer 4 (gate-failing next-task block)
    - Input fields: `task_id: str`, `step_id: str`, `slice_id: str`, `verify_passed: bool`, `evidence: dict[str, Any]`
    - Output fields: `accepted: bool`, `gate_strike_id: str | None`, `next_task_id: str | None`

    **#### 2. complete_slice**
    - Module path: `state_build/slices/complete_slice.py`
    - Owning phase: 402 + 404
    - Source spec: SLICE-CYCLE.md run-slice → verify-slice transition, PROOF-GATE.md §4 Slice-end gate
    - Semantics: Agent signals run-slice or verify-slice completion. Daemon runs slice-level `<verification>` block + writes `N-VERIFICATION.md` per PRF-03.
    - Plugin-hook integration site: no hook — agent-only
    - Input fields: `slice_id: str`, `stage: Literal["run-slice","verify-slice"]`, `verification_passed: bool`, `n_verification_md_path: str`
    - Output fields: `accepted: bool`, `slice_event_id: str`, `next_stage: Literal["verify-slice","close"] | None`

    **#### 3. request_step_split**
    - Module path: `state_build/scope/request_step_split.py`
    - Owning phase: 404
    - Source spec: SCOPE-PROHIBITION.md SRP-05
    - Semantics: Agent reports "this Step is too large." Daemon emits `state.step.split_recommendation` and routes to plan-slice for re-planning rather than allowing in-place scope reduction.
    - Plugin-hook integration site: no hook — agent-only
    - Input fields: `step_id: str`, `reason: str`, `proposed_split: list[str]`
    - Output fields: `split_recommendation_event_id: str`, `replan_required: bool`

    **#### 4. scope_deviation_request**
    - Module path: `state_build/scope/scope_deviation_request.py`
    - Owning phase: 404
    - Source spec: SCOPE-PROHIBITION.md "scope_deviation_request MCP Tool Flow" (SRP-04)
    - Semantics: Agent requests permission to Write/Edit outside the active Step's `files_modified` allowlist. Daemon evaluates (often pairing with `log_deviation`); granted requests update the active allowlist set for the open task.
    - Plugin-hook integration site: tool.execute.before layer 2 — files_modified allowlist consults open requests; layer 7 cross-validates against ARCH_PATTERN_ALLOWLIST for Rule-4 auto-promotion.
    - Input fields: `task_id: str`, `requested_path: str`, `justification: str`
    - Output fields: `request_event_id: str`, `granted: bool`, `granted_paths: list[str] | None`, `rejection_reason: str | None`

    **#### 5. log_deviation**
    - Module path: `state_build/deviation/log_deviation.py`
    - Owning phase: 405
    - Source spec: DEVIATION-RULES.md §3
    - Semantics: Agent logs a deviation under one of 4 rules. Daemon runs 5-step cross-validation (issue_signature recomputation → Rule-4 alternatives check → Rule-4 auto-promotion → scope_deviation_request correlation → cap check). Rule 4 always surfaces opencode `question` tool — no autonomy bypass.
    - Plugin-hook integration site: tool.execute.before layer 5
    - Input fields: `task_id: str`, `rule_id: Literal[1,2,3,4]`, `issue_signature: str`, `classification_source: Literal["agent_declared","harness_promoted","arch_pattern_match"]`, `alternatives: list[Rule4Option] | None` (required when `rule_id=4`), `error_excerpt: str`, `agent_response_summary: str`
    - Output fields: `deviation_event_id: str`, `attempt_number: int`, `cap_exceeded: bool`, `classification_accepted: bool`, `rejection_reason: str | None`

    **#### 6. dispatch_subagent**
    - Module path: `state_build/subagents/dispatch.py`
    - Owning phase: 405
    - Source spec: SUBAGENT-MANAGEMENT.md §2 (SUB-01..SUB-04)
    - Semantics: Agent dispatches one or more subagents under typed-spawn discipline (no string-prompt-only). Three modes: single / parallel / chain (exactly-one-mode root validator). Daemon enforces whitelist (`STAGE_ROSTER[current_stage]` ∩ `effective_whitelist`) and 20-default parallel cap with FIFO queuing.
    - Plugin-hook integration site: tool.execute.before layer 6
    - Input: `DispatchSubagent` from SUBAGENT-MANAGEMENT.md §2 (re-inline the class):
      ```python
      class DispatchSubagent(McpToolBase):
          model_config = ConfigDict(extra="forbid")
          single: SingleDispatch | None = None
          parallel: ParallelDispatch | None = None
          chain: ChainDispatch | None = None
          # Root validator: sum(1 for x in (single, parallel, chain) if x is not None) == 1
      ```
    - Output fields: `dispatched_task_ids: list[str]`, `queued_count: int`, `rejected: list[SubagentRejection]`

    **#### 7. check_proof_gate**
    - Module path: `state_build/proof/check_proof_gate.py`
    - Owning phase: 404
    - Source spec: PROOF-GATE.md §4 (gate evaluation order PRF-05)
    - Semantics: Driver tool that runs the proof gate at task-end / Step-end / Slice-end scopes. Pure-machine evaluation (no LLM-as-judge); checks bash exit codes, file existence, line counts, regex matches per PRF-04.
    - Plugin-hook integration site: no hook — invoked by `complete_task` and `complete_slice` handlers internally; agent MAY also call directly for pre-check
    - Input fields: `scope: Literal["task","step","slice"]`, `scope_id: str`, `must_haves: MustHavesBlock | None`, `automated_command: str | None`, `acceptance_criteria: list[str] | None`
    - Output fields: `gate_passed: bool`, `failed_checks: list[FailedCheck]`, `strike_count: int`, `escalation_action: Literal["none","advisory","reinject","human_gate"]`

    **#### 8. emit_advisory** *(NEW in Phase 406 — HRN-04 tier 1)*
    - Module path: `state_build/harness/intervention/emit_advisory.py`
    - Owning phase: 406 (new)
    - Source spec: THIS spec §4 (Plan 03) — HRN-04 tier 1
    - Semantics: Inject an advisory message into the agent's context. Tier-1 intervention. Source triggers: APG advisory 1-2 + 4-5; PRF strike 1-2 + 4-5; DEV log_deviation accepted (pending resolution); SCOPE scope_check unresolved; SUB subagent_spot_check_failed first occurrence. Emits paired `state.harness.intervention` event (tier="advisory") alongside the per-chain source event.
    - Plugin-hook integration site: pushes advisory string into next chat.params reinject payload
    - Input fields: `task_id: str`, `advisory_text: str`, `source_trigger: Literal["paralysis","gate_strike","deviation_pending","scope_unresolved","subagent_spot_check"]`, `correlation_event_id: str`
    - Output fields: `advisory_event_id: str`, `intervention_event_id: str`

    **#### 9. force_clear_and_reinject** *(NEW in Phase 406 — HRN-04 tier 3)*
    - Module path: `state_build/harness/intervention/force_clear_and_reinject.py`
    - Owning phase: 406 (new)
    - Source spec: THIS spec §4 (Plan 03) — HRN-04 tier 3 + CTX-09 reactive overflow
    - Semantics: Force context clear+reinject. Tier-3 intervention. Source triggers: APG advisory 3 (paralysis chain reinject); PRF strike 3 (gate chain reinject); CTX-04 emergency threshold (≤25%); CTX-09 reactive overflow recovery one-shot. Invokes `request_compaction_snapshot` internally then re-injects via session.compacting hook; emits paired `state.harness.intervention` event (tier="clear_reinject").
    - Plugin-hook integration site: drives session.compacting hook
    - Input fields: `session_id: str`, `slice_id: str`, `trigger_reason: Literal["paralysis_chain_3_reinject","gate_strike_3_reinject","context_threshold_emergency","context_overflow_reactive"]`, `correlation_event_id: str`
    - Output fields: `compaction_event_id: str`, `reinject_event_id: str`, `intervention_event_id: str`

    **#### 10. surface_human_gate** *(NEW in Phase 406 — HRN-04 tier 4 + HRN-06)*
    - Module path: `state_build/harness/intervention/surface_human_gate.py`
    - Owning phase: 406 (new)
    - Source spec: THIS spec §4 (Plan 03) — HRN-04 tier 4 + HRN-06
    - Semantics: Surface a human gate via opencode's `question` tool. Tier-4 intervention. Source triggers: APG advisory 6; PRF strike 6; DEV Rule 4 architectural (always-stop, even under `--full-yolo`); DEV cap_exceeded → Rule 3 checkpoint:decision OR Rule 4 promotion; SUB subagent_restart_exhausted; SUB persistent orphan reconciliation step 6; SCOPE scope_deviation_rejected. **HRN-06 invariant: human gates use opencode's `question` tool exclusively — no custom harness UI.** Emits paired `state.harness.intervention` event (tier="human_gate").
    - Plugin-hook integration site: no hook — synchronous call to opencode question tool
    - Input fields: `task_id: str | None`, `slice_id: str`, `question_text: str`, `alternatives: list[QuestionAlternative]`, `trigger_reason: Literal["paralysis_chain_6_human_gate","gate_strike_6_human_gate","deviation_rule_4_architectural","deviation_cap_exceeded","subagent_restart_exhausted","subagent_orphan_persistent","scope_deviation_rejected"]`, `correlation_event_id: str`
    - Output fields: `question_event_id: str`, `intervention_event_id: str`, `awaiting_human: bool`

    **#### 11. query_context_meter**
    - Module path: `state_build/context/query_context_meter.py`
    - Owning phase: 402
    - Source spec: CONTEXT-PROTOCOL.md CTX-08
    - Semantics: Read opencode's current session context meter. Used by tool.execute.after hook to mirror meter state to SSE bus for TUI consumption.
    - Plugin-hook integration site: invoked from tool.execute.after
    - Input fields: `session_id: str`
    - Output fields: `tokens_used: int`, `tokens_remaining: int`, `percent_remaining: float`, `model_window: int`

    **#### 12. request_compaction_snapshot**
    - Module path: `state_build/context/request_compaction_snapshot.py`
    - Owning phase: 402
    - Source spec: CONTEXT-PROTOCOL.md CTX-03 (daemon-initiated compaction path)
    - Semantics: Daemon-initiated compaction. Builds `CompactionSnapshot` Pydantic model from current task state, serializes via orjson, writes event-store row, returns rehydrate payload consumed by session.compacting hook.
    - Plugin-hook integration site: triggers session.compacting hook on opencode side
    - Input fields: `session_id: str`, `slice_id: str`, `current_task_id: str`, `daemon_initiated: bool`
    - Output fields: `snapshot_event_id: str`, `reinject_payload_bytes: bytes`

    **#### 13. query_event_store** *(NEW in Phase 406 — HRN-07 reconstruction)*
    - Module path: `state_build/event_store/query.py`
    - Owning phase: 406 (new)
    - Source spec: THIS spec §5 (Plan 04) — HRN-07 reconstruction protocol
    - Semantics: Read-only API to the `.state/events.sqlite` event store. Used by the reconstruction protocol (Plan 04 §5) and by TUI projection. Append-only invariant preserved — this tool MUST NOT mutate.
    - Plugin-hook integration site: no hook — internal daemon API + replay tooling
    - Input fields: `event_types: list[str]` (e.g., `["state.harness.intervention","state.session.compaction_snapshot_taken"]`), `aggregate_id: str | None`, `from_seq: int | None`, `to_seq: int | None`, `limit: int`
    - Output fields: `events: list[EventEnvelope]`, `total_matched: int`, `next_cursor: int | None`

    **#### 14. record_plan_edit**
    - Module path: `state_build/plan/record_plan_edit.py`
    - Owning phase: 403
    - Source spec: PLAN-AS-PROMPT.md PAP-04 / §6
    - Semantics: Records every plan edit (mutable sections only; immutable sections blocked by tool.execute.before layer 1 / PAP-05). Emits `state.step.plan_edit` event with diff + editor (executor / harness / human).
    - Plugin-hook integration site: tool.execute.before layer 1 — PAP-05 immutability check rejects edits to must_haves.* / `<verify>` blocks
    - Input fields: `step_id: str`, `diff: str`, `editor: Literal["executor","harness","human"]`
    - Output fields: `plan_edit_event_id: str`, `accepted: bool`, `immutability_violation: str | None`

    ### Section 3.5 — Hook integration matrix

    Heading: `### Hook integration matrix`.

    1-paragraph intro: "Cross-reference between §2 plugin hooks and §3 MCP tools. The matrix shows which MCP tools are invoked from which plugin hook layer. Tools without a plugin-hook integration site are agent-only (driven entirely by the agent's tool call, with daemon-side decision logic but no hook-mediated enforcement)."

    Render markdown table:

    ```
    | Tool                          | Plugin-hook integration site                        |
    |-------------------------------|------------------------------------------------------|
    | complete_task                 | tool.execute.before layer 4 (gate-failing next-task) |
    | complete_slice                | (agent-only)                                         |
    | request_step_split            | (agent-only)                                         |
    | scope_deviation_request       | tool.execute.before layer 2 (files_modified consults) + layer 7 (arch-pattern correlation) |
    | log_deviation                 | tool.execute.before layer 5                          |
    | dispatch_subagent             | tool.execute.before layer 6                          |
    | check_proof_gate              | invoked by complete_task / complete_slice handlers   |
    | emit_advisory                 | pushes into chat.params next-turn reinject           |
    | force_clear_and_reinject      | drives session.compacting                            |
    | surface_human_gate            | (agent-only; calls opencode question tool synchronously) |
    | query_context_meter           | invoked from tool.execute.after                      |
    | request_compaction_snapshot   | triggers session.compacting on opencode side         |
    | query_event_store             | (agent-only; read-only daemon API)                   |
    | record_plan_edit              | tool.execute.before layer 1 (PAP-05 immutability)    |
    ```

    ### Section 3.6 — Coverage cross-reference

    Heading: `### Coverage cross-reference (HRN-03 closure)`.

    Render verbatim: "HRN-03 requires that **every harness operation specified in Phases 402–405 is mapped to at least one MCP tool**. The following matrix discharges that obligation."

    Render markdown table:

    ```
    | REQ category | Tools covering category                                           |
    |--------------|-------------------------------------------------------------------|
    | CTX (402)    | query_context_meter, request_compaction_snapshot, force_clear_and_reinject (CTX-09) |
    | STP (403)    | complete_task, record_plan_edit                                   |
    | PAP (403)    | record_plan_edit (PAP-04 emit-site; PAP-01/02/05 enforced via tool.execute.before) |
    | PRF (404)    | check_proof_gate, complete_task (drives strike counter on verify_passed=False) |
    | APG (404)    | emit_advisory (advisory injection), force_clear_and_reinject (chain-3 reinject), surface_human_gate (chain-6 human gate) |
    | SRP (404)    | request_step_split, scope_deviation_request                       |
    | DEV (405)    | log_deviation, surface_human_gate (Rule 4 always-stop)            |
    | SUB (405)    | dispatch_subagent, complete_task (subagent return spot-check consumes), surface_human_gate (restart exhausted) |
    | HRN (406)    | emit_advisory, force_clear_and_reinject, surface_human_gate, query_event_store (new in this phase) |
    ```

    Note: "100% Phase-402–405 operation coverage. Every REQ category (CTX, STP, PAP, PRF, APG, SRP, DEV, SUB, HRN) has at least one mapped tool. Where a tool covers multiple categories, the matrix lists each. Cross-reference: 406-CONTEXT.md `<decisions>` 'Tool roster — exhaustive map of every Phase 402–405 harness operation.'"

    Closing paragraph: "§3 closes. §4 (Plan 03 of this phase) consumes `emit_advisory`, `force_clear_and_reinject`, and `surface_human_gate` to populate the HRN-04 4-tier intervention ladder + the `state.harness.intervention` umbrella event. §5 (Plan 04 of this phase) consumes `query_event_store` for the HRN-07 reconstruction protocol."

    <quality_scan>
      <code_to_reuse>
        - Known: 405 DEVIATION-RULES.md §3 — log_deviation input fields + Rule4Option shape (re-inline verbatim).
        - Known: 405 SUBAGENT-MANAGEMENT.md §2 — DispatchSubagent + SingleDispatch + ParallelDispatch + ChainDispatch verbatim for dispatch_subagent entry.
        - Known: 405 SUBAGENT-MANAGEMENT.md §5 — SubagentRejection shape for dispatch_subagent output.
        - Known: 404 PROOF-GATE.md §4 — MustHavesBlock + FailedCheck + GateScope shapes for check_proof_gate entry.
        - Known: 404 SCOPE-PROHIBITION.md SRP-04 + SRP-05 — scope_deviation_request + request_step_split shapes.
        - Known: 402 CONTEXT-PROTOCOL.md CTX-03 + CTX-08 + CTX-09 — query_context_meter, request_compaction_snapshot, force_clear_and_reinject reactive-overflow trigger.
        - Known: 403 PLAN-AS-PROMPT.md PAP-04 — record_plan_edit input/output shapes.
        - Known: 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" — `surface_human_gate` trigger_reason Literal values verbatim from the umbrella HarnessIntervention.trigger_reason sketch (subset that surfaces tier-4).
        - Grep pattern: `grep -nE "Rule4Option|DeviationLogResult|ARCH_PATTERN_ALLOWLIST" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md | head -20` — locates log_deviation Pydantic shapes.
        - Grep pattern: `grep -nE "SingleDispatch|ParallelDispatch|ChainDispatch|SubagentRejection" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md | head -20` — locates dispatch_subagent Pydantic shapes.
        - Grep pattern: `grep -nE "MustHavesBlock|FailedCheck|GateScope" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md | head -20` — locates check_proof_gate Pydantic shapes.
      </code_to_reuse>
      <docs_to_consult>
        - DEVIATION-RULES.md §3 — verbatim log_deviation Pydantic input/output source.
        - SUBAGENT-MANAGEMENT.md §2 + §5 — verbatim dispatch_subagent + SubagentRejection source.
        - PROOF-GATE.md §4 — verbatim check_proof_gate Pydantic source.
        - SCOPE-PROHIBITION.md SRP-04 + SRP-05 — verbatim scope_deviation_request + request_step_split source.
        - CONTEXT-PROTOCOL.md CTX-03 + CTX-08 + CTX-09 — verbatim context tool sources.
        - PLAN-AS-PROMPT.md PAP-04 — verbatim record_plan_edit source.
        - 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" — Literal trigger_reason values for emit_advisory + force_clear_and_reinject + surface_human_gate.
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
        && wc -l "$F" | awk '{exit ($1 < 800)}' \
        && grep -qE "^### Per-tool catalog entries" "$F" \
        && grep -qE "^### Hook integration matrix" "$F" \
        && grep -qE "^### Coverage cross-reference \(HRN-03 closure\)" "$F" \
        && grep -qE "^#### 1\\. complete_task" "$F" \
        && grep -qE "^#### 2\\. complete_slice" "$F" \
        && grep -qE "^#### 3\\. request_step_split" "$F" \
        && grep -qE "^#### 4\\. scope_deviation_request" "$F" \
        && grep -qE "^#### 5\\. log_deviation" "$F" \
        && grep -qE "^#### 6\\. dispatch_subagent" "$F" \
        && grep -qE "^#### 7\\. check_proof_gate" "$F" \
        && grep -qE "^#### 8\\. emit_advisory" "$F" \
        && grep -qE "^#### 9\\. force_clear_and_reinject" "$F" \
        && grep -qE "^#### 10\\. surface_human_gate" "$F" \
        && grep -qE "^#### 11\\. query_context_meter" "$F" \
        && grep -qE "^#### 12\\. request_compaction_snapshot" "$F" \
        && grep -qE "^#### 13\\. query_event_store" "$F" \
        && grep -qE "^#### 14\\. record_plan_edit" "$F" \
        && grep -q "rule_id: Literal\\[1,2,3,4\\]" "$F" \
        && grep -q "Rule4Option" "$F" \
        && grep -q "DispatchSubagent" "$F" \
        && grep -q "SingleDispatch" "$F" \
        && grep -q "ParallelDispatch" "$F" \
        && grep -q "ChainDispatch" "$F" \
        && grep -q "MustHavesBlock" "$F" \
        && grep -q "FailedCheck" "$F" \
        && grep -q "EventEnvelope" "$F" \
        && grep -q "QuestionAlternative" "$F" \
        && grep -q "SubagentRejection" "$F" \
        && grep -q "paralysis_chain_3_reinject\\|gate_strike_3_reinject\\|context_threshold_emergency\\|context_overflow_reactive" "$F" \
        && grep -q "paralysis_chain_6_human_gate\\|gate_strike_6_human_gate\\|deviation_rule_4_architectural" "$F" \
        && grep -q "100% Phase-402–405 operation coverage\\|100% Phase 402–405 operation coverage\\|100% Phase-402-405\\|every REQ category" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[5]] All 14 per-tool sub-subsections present in locked order with literal headings `#### N. {tool_name}`.
    - [check: must_haves.truths[6]] Each per-tool entry renders Pydantic input + output models with `model_config = ConfigDict(extra="forbid")`.
    - [check: must_haves.truths[7]] complete_task entry renders with all 5 input + 3 output fields verbatim.
    - [check: must_haves.truths[8]] complete_slice entry renders.
    - [check: must_haves.truths[9]] request_step_split entry renders per SRP-05.
    - [check: must_haves.truths[10]] scope_deviation_request entry renders per SRP-04 with tool.execute.before layer 2 cite.
    - [check: must_haves.truths[11]] log_deviation entry renders with Rule4Option + classification_source Literal verbatim.
    - [check: must_haves.truths[12]] dispatch_subagent entry renders DispatchSubagent + 3 mode classes + SubagentRejection.
    - [check: must_haves.truths[13]] check_proof_gate entry renders MustHavesBlock + FailedCheck + escalation_action Literal.
    - [check: must_haves.truths[14]] emit_advisory NEW tool documented with 5-value source_trigger Literal.
    - [check: must_haves.truths[15]] force_clear_and_reinject NEW tool documented with 4-value trigger_reason Literal including CTX-09 context_overflow_reactive.
    - [check: must_haves.truths[16]] surface_human_gate NEW tool documented with 7-value trigger_reason Literal + HRN-06 question-tool invariant assertion.
    - [check: must_haves.truths[17]] query_context_meter entry renders per CTX-08.
    - [check: must_haves.truths[18]] request_compaction_snapshot entry renders per CTX-03.
    - [check: must_haves.truths[19]] query_event_store NEW tool documented as read-only API for HRN-07.
    - [check: must_haves.truths[20]] record_plan_edit entry renders per PAP-04 with tool.execute.before layer 1 (PAP-05) cite.
    - [check: must_haves.truths[21]] Hook-integration matrix rendered with all 14 tools.
    - [check: must_haves.truths[22]] Coverage cross-reference table covers CTX/STP/PAP/PRF/APG/SRP/DEV/SUB/HRN with at least one tool each; closing 100% statement rendered.
    - [check: must_haves.truths[24]] No `GSD-` literal in the file.
    - [check: must_haves.artifacts[0]] File ≥800 lines.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md grows by ~330 lines (§3.4 14 per-tool entries + §3.5 hook matrix + §3.6 coverage); file ≥800 lines; all 14 tools render with Pydantic input + output classes; verify-block bash passes; no `GSD-` literal.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

```bash
F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md

# §0 + §1 + §2 still present (Plan 01 untouched)
grep -qE "^# Harness Architecture \(Canonical, v41 Rollup\)" "$F" || { echo "MISSING_§0"; exit 1; }
grep -qE "^## §1 Layered Diagram \(HRN-01\)" "$F" || { echo "MISSING_§1"; exit 1; }
grep -qE "^## §2 Plugin Hook Inventory \(HRN-02\)" "$F" || { echo "MISSING_§2"; exit 1; }

# §3 + subsections present
for section in \
  "^## §3 state-build MCP Tool Catalog \(HRN-03\)" \
  "^### Tool roster" \
  "^### MCP_TOOL_REGISTRY" \
  "^### Exhaustiveness via assert_never" \
  "^### Per-tool catalog entries" \
  "^### Hook integration matrix" \
  "^### Coverage cross-reference \(HRN-03 closure\)"; do
  grep -qE "$section" "$F" || { echo "MISSING: $section"; exit 1; }
done

# All 14 per-tool sub-subsections
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14; do
  grep -qE "^#### ${i}\\. " "$F" || { echo "MISSING_TOOL_ENTRY: $i"; exit 1; }
done

# All 14 tool names present
for tool in complete_task complete_slice request_step_split scope_deviation_request log_deviation dispatch_subagent check_proof_gate emit_advisory force_clear_and_reinject surface_human_gate query_context_meter request_compaction_snapshot query_event_store record_plan_edit; do
  grep -q "$tool" "$F" || { echo "MISSING_TOOL: $tool"; exit 1; }
done

# Pydantic discipline
grep -qE 'model_config = ConfigDict\(extra="forbid"\)' "$F" || { echo "MISSING_PYDANTIC_FORBID"; exit 1; }
grep -q "assert_never(tool_name)" "$F" || { echo "MISSING_ASSERT_NEVER"; exit 1; }

# Coverage statement
grep -q "100% Phase" "$F" || grep -q "every REQ category" "$F" || { echo "MISSING_COVERAGE_STATEMENT"; exit 1; }

# Line count
wc -l "$F" | awk '{ if ($1 < 800) { print "LINE_COUNT_FAIL: " $1; exit 1 } }'

# Naming discipline
! grep -qE '\bGSD-' "$F" || { echo "GSD_NAMING_VIOLATION"; exit 1; }

echo "HARNESS-ARCHITECTURE.md §3 verification OK"
```
</verification>

<success_criteria>
- §3 appended to HARNESS-ARCHITECTURE.md; total file ≥ 800 lines.
- All 14 per-tool entries render with Pydantic input + output classes + `extra="forbid"`.
- `MCP_TOOL_REGISTRY` + `assert_never` exhaustiveness pattern rendered.
- Hook integration matrix covers all 14 tools.
- Coverage cross-reference table maps every REQ category (CTX, STP, PAP, PRF, APG, SRP, DEV, SUB, HRN) to ≥1 tool.
- Section §0–§2 untouched.
- No `GSD-` literal in the file (project naming discipline).
- Forward-pointers to §4 (Plan 03, intervention ladder) and §5 (Plan 04, replay proof) rendered.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/406/02-mcp-tool-catalog-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: spec-doc final line count, sections rendered (§3 + 14 per-tool entries + hook matrix + coverage table), HRN-03 closure verification (every Phase-402–405 REQ category mapped to ≥1 tool), 4-new-tool roster (`emit_advisory`, `force_clear_and_reinject`, `surface_human_gate`, `query_event_store`), naming-discipline verification result (`grep '\bGSD-' = 0`).
</output>
