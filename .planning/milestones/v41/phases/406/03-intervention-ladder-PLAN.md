---
phase: 406
plan: 03
type: execute
wave: 3
depends_on:
  - "406-02"
files_modified:
  - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
autonomous: true
requirements:
  - HRN-04
  - HRN-05
  - HRN-06

must_haves:
  truths:
    - "HARNESS-ARCHITECTURE.md exists with §0 + §1 + §2 + §3 (from Plans 01 and 02). THIS plan (Plan 03) appends §4 only — without modifying §0–§3. Plan 04 will then append §5 + §6."
    - "§4 heading is rendered verbatim: `## §4 4-Tier Intervention Ladder + harness_intervention Event + Human-Gate-Only-via-question (HRN-04, HRN-05, HRN-06)`. Sub-sections cover (in order): §4.1 4-tier ladder overview, §4.2 per-tier trigger-source enumeration, §4.3 `HarnessIntervention` Pydantic class verbatim, §4.4 emission model (alongside source events, NOT replacing), §4.5 HRN-06 human-gate-only-via-opencode-question structural invariant, §4.6 mode-isolation note."
    - "§4.1 4-tier ladder overview renders the four-tier ordered list verbatim from REQUIREMENTS.md HRN-04: (1) Advisory inject (system message into context); (2) Tool-block (refuse a tool call via `tool.execute.before`); (3) Force context clear+reinject (trigger `session.compacting` with reduced state); (4) Force-stop + human gate (end session, surface via `question` tool). Each tier names the MCP tool from §3 that operationalizes it: tier 1 → `emit_advisory`; tier 2 → no tool (enforced inside `tool.execute.before` middleware directly); tier 3 → `force_clear_and_reinject`; tier 4 → `surface_human_gate`."
    - "§4.2 per-tier trigger-source enumeration renders a 4-row markdown table verbatim from 406-CONTEXT.md `<decisions>` 'harness_intervention event + 4-tier ladder (Area 4)' subsection. Columns: Tier | Trigger sources. Every trigger named verbatim across APG, PRF, DEV, SUB, SCOPE, CTX (full enumeration of all phase chains)."
    - "§4.2 tier-1 trigger sources cover at minimum: APG advisory 1-2 + 4-5; PRF strike 1-2 + 4-5; DEV `log_deviation` accepted (pending resolution); SCOPE `scope_check` unresolved without exception; SUB `subagent_spot_check_failed` first occurrence on a tuple."
    - "§4.2 tier-2 trigger sources cover at minimum (the 7-layer tool.execute.before stack from §2): SRP-04 `files_modified` allowlist (Layer 1); PAP-05 immutability (Layer 2); SRP-02 prohibited-language (Layer 3); PRF-07 gate-failing next-task block (Layer 4); SUB-03 `subagent_whitelist_violation` (Layer 6 stage 2); SUB-04 `subagent_cap_expansion_rejected` (Layer 6 stage 3); CTX-04 warning threshold (≤35%) next-task block."
    - "§4.2 tier-3 trigger sources cover at minimum: APG advisory 3 (paralysis chain reinject); PRF strike 3 (gate chain reinject); CTX-04 emergency threshold (≤25%); CTX-09 reactive overflow recovery one-shot."
    - "§4.2 tier-4 trigger sources cover at minimum: APG advisory 6; PRF strike 6; DEV Rule 4 architectural (always-stop, even under `--full-yolo`); DEV cap_exceeded → Rule 3 checkpoint:decision OR Rule 4 promotion; SUB `subagent_restart_exhausted`; SUB persistent orphan reconciliation step 6; SCOPE `scope_deviation_rejected`."
    - "§4.3 renders the `HarnessIntervention` Pydantic class verbatim from 406-CONTEXT.md `<decisions>` 'harness_intervention event + 4-tier ladder (Area 4)' subsection. The class includes: `model_config = ConfigDict(extra=\"forbid\")`; `tier: Literal[\"advisory\", \"tool_block\", \"clear_reinject\", \"human_gate\"]`; `trigger_reason: Literal[...]` with ALL 18 named trigger_reason values verbatim (paralysis_threshold_crossed, paralysis_chain_3_reinject, paralysis_chain_6_human_gate, gate_strike_advisory, gate_strike_3_reinject, gate_strike_6_human_gate, deviation_logged_pending, deviation_cap_exceeded, deviation_rule_4_architectural, subagent_spot_check_failed, subagent_crash_detected, subagent_restart_exhausted, subagent_orphan_persistent, scope_check_unresolved, scope_deviation_rejected, context_threshold_warning, context_threshold_emergency, context_overflow_reactive); `target_step_or_task: str`; `correlation_event_id: str`; `slice_id: str`; `session_id: str`; `triggered_at: datetime` (UTC, ISO-8601)."
    - "§4.3 includes a `### Module ownership` subsection naming `state_build/harness/intervention/` as the single-source-of-truth module path. Sub-modules: `emit_advisory.py`, `force_clear_and_reinject.py`, `surface_human_gate.py` (the three MCP-tool emitters from §3); `projector.py` (umbrella event reducer); `dispatcher.py` (tier classification dispatch from source chain → umbrella event). Event name `state.harness.intervention` registered under `BUILD_ONLY_EVENT_PREFIXES`."
    - "§4.4 emission model renders verbatim: 'The originating chain emits its own event (e.g., `state.step.paralysis_event` with `tier=\"reinject\"`); the daemon middleware additionally emits `state.harness.intervention` with `tier=\"clear_reinject\"` and `correlation_event_id` pointing at the paralysis_event row. Two events per intervention; replay can reconstruct the umbrella view from `state.harness.intervention` rows OR from the per-chain rows independently. Mirrors the gsd-2 cross-layer comm-map pattern where one runtime action surfaces in multiple bus views.'"
    - "§4.4 includes a `### Worked example — tier-3 paralysis reinject` showing the exact two-event emission pair: (1) `state.step.paralysis_event(tier=\"reinject\", task_id=X, count=3, threshold=5)` emitted by the paralysis projector; (2) `state.harness.intervention(tier=\"clear_reinject\", trigger_reason=\"paralysis_chain_3_reinject\", target_step_or_task=X, correlation_event_id=<paralysis_event row id>, ...)` emitted by `state_build/harness/intervention/dispatcher.py` immediately after. Demonstrates the 'sole rollup point' property of HRN-05 from the 406-CONTEXT.md `<specifics>` 4th bullet."
    - "§4.4 includes a `### Tier dispatcher` subsection rendering a Python match-case showing how the dispatcher maps source-chain event types to umbrella tier values. Cases cover: paralysis_event with chain count → tier; gate_strike with strike count → tier; deviation_logged → tier (advisory for pending, human_gate for rule_id=4); subagent_spot_check_failed → advisory; subagent_crash_detected → varies; CTX threshold crosses → tool_block / clear_reinject. `case _: assert_never(source_event_type)` closes the match for compile-time exhaustiveness."
    - "§4.5 HRN-06 human-gate-only-via-question structural invariant renders verbatim from 406-CONTEXT.md `<decisions>` 'harness_intervention event + 4-tier ladder (Area 4)' Human-Gate-Only subsection: 'The harness NEVER invents its own UI for human gates. Every tier-4 path renders via opencode's `question` tool with the named alternatives payload. The absence of any other UI surface in `state_build/harness/intervention/` is the structural enforcement; CI grep targets the directory and rejects PRs introducing alternate UI primitives. Mirrors the absence-of-bypass pattern from Phase 405 DEV-04 (no `full_yolo bypass` branch in `state_build/deviation/log_deviation.py`).'"
    - "§4.5 includes a CI-enforcement specification: `grep -rE '(prompt|input|Confirm|Inquirer|click\\.prompt|TUI human_gate)' src/state_build/harness/intervention/ MUST return zero matches`. The only acceptable human-gate surface is a call into `surface_human_gate` MCP tool which calls opencode's `question` tool. Carry-forward absence-of-bypass discipline from Phase 405 DEV-04."
    - "§4.6 mode-isolation note asserts `state_build/harness/intervention/` MUST NOT import `state_teach/`; CI import-graph lint enforces; the `state.harness.intervention` event lives in `BUILD_ONLY_EVENT_PREFIXES`."
    - "§4 includes a closing `### Pure-machine discipline carry-forward` paragraph asserting (verbatim): 'The umbrella `tier` value is server-derived, never agent-emitted. The dispatcher (§4.4) is a deterministic match on source-chain event type → umbrella tier; no LLM-as-judge anywhere. Mirrors PRF-04 spirit and the carry-forward rule from §1.'"
    - "§4 forward-references Plan 04: '§5 (Plan 04) will enumerate the `state.harness.intervention` event among the ~30 event types the replay protocol must consume; §6 (Plan 04) will surface specific intervention emission points in the full-Slice lifecycle sequence diagram.'"
    - "HARNESS-ARCHITECTURE.md does NOT contain the literal string `GSD-` anywhere (project naming-discipline rule — STATE-* / state-* only)."
  artifacts:
    - path: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      provides: "Phase 406 rollup — adds §4 4-tier intervention ladder + state.harness.intervention Pydantic event class + emission model (alongside source events) + HRN-06 human-gate-only-via-question structural invariant + tier dispatcher with assert_never exhaustiveness."
      min_lines: 1050
  key_links:
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md"
      via: "§4.2 tier-1 + tier-3 + tier-4 trigger-source rows cite APG paralysis_event chain at strikes 1-2, 3-reinject, 6-human-gate respectively"
      pattern: "ANALYSIS-PARALYSIS-GUARD\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "§4.2 tier-1 + tier-3 + tier-4 trigger-source rows cite PRF gate_strike chain at strikes 1-2, 3-reinject, 6-human-gate respectively"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      via: "§4.2 tier-4 trigger-source row cites DEV Rule 4 always-stop and DEV cap_exceeded; §4.5 HRN-06 invariant cites DEV-04 absence-of-bypass pattern from DEVIATION-RULES.md log_deviation handler"
      pattern: "DEVIATION-RULES\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      via: "§4.2 tier-1 + tier-4 trigger-source rows cite SUB subagent_spot_check_failed (tier 1), subagent_restart_exhausted + subagent_orphan_persistent (tier 4)"
      pattern: "SUBAGENT-MONITORING\\.md"
---

<objective>
Append §4 to the canonical `HARNESS-ARCHITECTURE.md` spec document — the 4-tier intervention ladder (HRN-04), the `state.harness.intervention` umbrella event Pydantic class (HRN-05), and the human-gate-only-via-opencode-`question` structural invariant (HRN-06).

This is Wave 3: depends on Plan 02 (which appended §3 MCP Tool Catalog). The §4 section consumes three MCP tools from §3 — `emit_advisory` (tier 1), `force_clear_and_reinject` (tier 3), `surface_human_gate` (tier 4) — as the operational surfaces for the intervention tiers. Plan 04 (Wave 4) will then append §5 (event-replay reconstruction proof) and §6 (full-Slice lifecycle sequence diagram), the latter of which will surface specific intervention emission points along the lifecycle.

Purpose: HRN-04 + HRN-05 + HRN-06 fully covered. Downstream consumers — Plan 04 (references the `state.harness.intervention` event from the §5 replay enumeration's Category 5 row; references §4.2 trigger-source enumeration when surfacing intervention emission points in the §6 sequence diagram), v14 Build Kernel (implements `state_build/harness/intervention/dispatcher.py` tier classification + `projector.py` umbrella event reducer + the absence-of-bypass discipline for HRN-06), v9 TUI bundle (subscribes to the `state.harness.intervention` SSE stream and renders per-tier visual treatments) — all read from this section.

Output: §4 appended to HARNESS-ARCHITECTURE.md, bringing total to ≥1050 lines. §4 contains: (4.1) tier overview, (4.2) per-tier trigger-source enumeration with full APG/PRF/DEV/SUB/SCOPE/CTX coverage, (4.3) `HarnessIntervention` Pydantic class with 18-value trigger_reason Literal, (4.4) emission model + worked example + tier dispatcher with assert_never, (4.5) HRN-06 structural invariant + CI grep enforcement, (4.6) mode-isolation note, closing pure-machine discipline + Plan-04 forward-reference. No `GSD-` identifier appears.
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
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
@.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
@.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — `HarnessIntervention` Pydantic class (verbatim from 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" subsection). RENDER VERBATIM IN §4.3:

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

Excerpt B — 4-tier ladder trigger-source enumeration (verbatim from 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" subsection). RENDER VERBATIM IN §4.2 as a markdown table:

```
| Tier | Trigger sources |
|---|---|
| Tier 1: advisory inject | APG advisory 1-2 + 4-5; PRF strike 1-2 + 4-5; DEV `log_deviation` accepted (pending resolution); SCOPE `scope_check` unresolved without exception; SUB `subagent_spot_check_failed` first occurrence on a tuple |
| Tier 2: tool-block (via `tool.execute.before`) | SRP-04 `files_modified` allowlist (Layer 1); PAP-05 immutability (Layer 2); SRP-02 prohibited-language (Layer 3); PRF-07 gate-failing next-task block (Layer 4); SUB-03 `subagent_whitelist_violation` (Layer 6 stage 2); SUB-04 `subagent_cap_expansion_rejected` (Layer 6 stage 3); CTX-04 warning threshold (≤35%) next-task block |
| Tier 3: force clear+reinject | APG advisory 3 (paralysis chain reinject); PRF strike 3 (gate chain reinject); CTX-04 emergency threshold (≤25%); CTX-09 reactive overflow recovery one-shot |
| Tier 4: force-stop + human gate (opencode `question` tool only) | APG advisory 6; PRF strike 6; DEV Rule 4 architectural (always-stop, even under `--full-yolo`); DEV cap_exceeded → Rule 3 `checkpoint:decision` OR Rule 4 promotion; SUB `subagent_restart_exhausted`; SUB persistent orphan reconciliation step 6 |
```

Excerpt C — Tier 1 + 3 + 4 MCP tool surfaces (from §3 entries in Plan 02):

```
| Tier | MCP tool                  | Module path                                              |
|------|---------------------------|-----------------------------------------------------------|
| 1    | emit_advisory             | state_build/harness/intervention/emit_advisory.py        |
| 2    | (none — middleware-only)  | (enforced inside tool.execute.before stack)              |
| 3    | force_clear_and_reinject  | state_build/harness/intervention/force_clear_and_reinject.py |
| 4    | surface_human_gate        | state_build/harness/intervention/surface_human_gate.py   |
```

Excerpt D — Source-chain event types that the umbrella dispatches from (from §3 cross-references + Phase 404/405 specs):

```
| Source chain | Event type                                | Owning spec                              |
|--------------|-------------------------------------------|------------------------------------------|
| APG          | state.step.paralysis_event                | ANALYSIS-PARALYSIS-GUARD.md              |
| PRF          | state.step.gate_strike / gate_resolved    | PROOF-GATE.md                            |
| DEV          | state.step.deviation_logged / cap_exceeded / classification_rejected | DEVIATION-RULES.md       |
| SUB          | state.step.subagent_spot_check_failed / crash_detected / restart_exhausted / orphan_detected | SUBAGENT-MONITORING.md |
| SCOPE        | state.step.scope_check / scope_deviation / scope_deviation_rejected | SCOPE-PROHIBITION.md       |
| CTX          | state.session.context_meter / compaction_snapshot_taken / overflow_recovery_attempted | CONTEXT-PROTOCOL.md |
```

Excerpt E — `HRN-06` human-gate-only-via-question invariant (verbatim from 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" Human-Gate-Only subsection):

```
The harness NEVER invents its own UI for human gates. Every tier-4 path renders via
opencode's `question` tool with the named alternatives payload. The absence of any
other UI surface in `state_build/harness/intervention/` is the structural enforcement;
CI grep targets the directory and rejects PRs introducing alternate UI primitives.
Mirrors the absence-of-bypass pattern from Phase 405 DEV-04 (no `full_yolo bypass`
branch in `state_build/deviation/log_deviation.py`).
```

Excerpt F — 4-counter independence (carry-forward from 404 + 405; rendered as cross-reference in §4.4):

```
APG/PRF/DEV/SUB chains never share state; the harness_intervention event is the SOLE
rollup point. Reference: PROOF-GATE.md §6 + DEVIATION-RULES.md §6 + SUBAGENT-MONITORING.md §4.
```
</interfaces>

<threat_model>
Phase 406 is design-only. §4 of HARNESS-ARCHITECTURE.md introduces no production attack surface — it is a markdown specification describing event payload + dispatcher pattern + structural invariants. Threats considered:

- **[high] HRN-06 human-gate bypass.** If the spec leaves human-gate-only-via-opencode-question as a policy assertion without structural enforcement, v14 could introduce a custom TUI surface for human gates and bypass opencode's question tool. Mitigation: spec asserts the absence-of-UI invariant for `state_build/harness/intervention/` directory with a literal CI grep target. Mirrors 405 DEV-04 absence-of-bypass pattern (no `full_yolo bypass` branch in DEVIATION-RULES.md log_deviation handler).
- **[high] Tier-4 autonomy bypass via mis-classified tier.** If `force_clear_and_reinject` could be invoked when the source event is actually a DEV Rule 4 (which requires human gate), an irreversible action could land without human approval. Mitigation: §4.4 tier dispatcher renders as a deterministic match-case on source-chain event type → tier; `assert_never(source_event_type)` closes the match. DEV Rule 4 events ALWAYS map to tier="human_gate"; no other tier is reachable for them. v14 unit tests assert against this invariant.
- **[med] Umbrella event drift from per-chain events.** If `state.harness.intervention.trigger_reason` doesn't exactly enumerate the values that match per-chain event semantics, reconstruction (HRN-07) could miss tier classifications. Mitigation: §4.3 renders the 18-value `trigger_reason` Literal verbatim from 406-CONTEXT.md; the §4.4 emission model documents the "two events per intervention" invariant so replay can reconstruct from EITHER per-chain rows OR umbrella rows independently — drift between the two views is detectable.
- **[med] Pure-machine discipline drift.** If a future patch added an LLM call inside the tier dispatcher (e.g., "ask LLM which tier this maps to"), the umbrella event would lose its server-derived property. Mitigation: §4 closing paragraph asserts "The umbrella `tier` value is server-derived, never agent-emitted. The dispatcher is a deterministic match; no LLM-as-judge anywhere." Carry-forward from PRF-04 spirit.
- **[med] Naming-discipline drift (STATE-* vs GSD-*).** Mitigation: verify-block bash includes `! grep -qE '\bGSD-' "$F"`.
- **[low] Mode-isolation drift.** Mitigation: §4.6 mode-isolation note asserts `state_build/harness/intervention/` MUST NOT import `state_teach/`.

No production code lands. No secrets, no network calls. The spec describes runtime mechanisms; threats listed above target v14 implementation, which this rollup constrains via authoritative Pydantic + match-case shapes.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Append §4.1 + §4.2 + §4.3 — 4-tier overview, per-tier trigger-source enumeration, HarnessIntervention Pydantic class</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Plans 01+02's output — §0–§3 already in place; APPEND §4.1–§4.3 below)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" subsection — VERBATIM source for HarnessIntervention class, 4-tier ladder table, emission model, HRN-06 invariant
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<specifics>` 4th bullet — "The 4-tier ladder enumeration is HRN-04's load-bearing claim" (rendered in §4.2 intro paragraph)
    - .planning/milestones/v41/REQUIREMENTS.md lines 124-134 (HRN-04, HRN-05, HRN-06 verbatim)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md §6 — gate_strike 6-strike ladder (precedent for tier 1 / 3 / 4 escalation pattern)
    - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md — paralysis_event 6-advisory ladder (precedent for tier 1 / 3 / 4 escalation pattern)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (search "Rule 4|always-stop|always.human-gate" — tier-4 DEV-04 trigger source)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md (search "subagent_restart_exhausted|subagent_orphan_persistent|spot_check_failed" — tier-1 + tier-4 SUB trigger sources)
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (search "scope_deviation_rejected|scope_check" — tier-1 + tier-4 SCOPE trigger sources)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "≤25%|≤35%|context_overflow|reactive overflow" — tier-2 + tier-3 CTX trigger sources)
  </read_first>

  <action>
    Append §4.1 + §4.2 + §4.3 to the existing HARNESS-ARCHITECTURE.md. **DO NOT modify §0, §1, §2, or §3.** **Concrete content from 406-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 4 — 4-Tier Intervention Ladder + harness_intervention Event + Human-Gate-Only-via-question (HRN-04, HRN-05, HRN-06)

    Heading: `## §4 4-Tier Intervention Ladder + harness_intervention Event + Human-Gate-Only-via-question (HRN-04, HRN-05, HRN-06)`.

    1-paragraph intro (synthesizing 406-CONTEXT.md `<specifics>` 4th bullet + HRN-04 + HRN-05 + HRN-06 literals):

    "The harness intervenes in agent execution at four ordered tiers — advisory inject → tool-block → force clear+reinject → force-stop + human gate. Each tier escalates the harness's enforcement strength. HRN-04 specifies the four tier behaviors; HRN-05 specifies the `state.harness.intervention` umbrella event that records every intervention regardless of source chain; HRN-06 asserts that all human gates (tier 4) surface exclusively through opencode's `question` tool — the harness invents no custom UI. The 4-tier ladder enumeration in §4.2 is HRN-04's load-bearing claim: every escalation site across APG, PRF, DEV, SUB, SCOPE, and CTX chains is mapped to exactly one tier, so a reader can ground-truth-check 'what fires when APG advisory 3 lands?' Answer: `state.step.paralysis_event(tier=\"reinject\")` + `state.harness.intervention(tier=\"clear_reinject\", trigger_reason=\"paralysis_chain_3_reinject\")` simultaneously."

    ### Section 4.1 — 4-Tier Ladder Overview (HRN-04)

    Heading: `### 4-Tier Ladder Overview (HRN-04)`.

    Render verbatim from REQUIREMENTS.md HRN-04 as an ordered list:

    1. **Advisory inject** — system message into context. The harness pushes an advisory string into the next agent turn via `chat.params` reinject payload. The agent reads it as a system-style message; turn continues normally. Operational tool: `emit_advisory` (§3 entry 8).
    2. **Tool-block** — refuse a tool call via `tool.execute.before`. The hook returns `{allow: false, blockReason: <reason>}`; opencode reports the rejection to the agent; the agent must produce a different tool call. Operational mechanism: the 7-layer write-block stack documented in §2 `tool.execute.before` and §3 cross-references. No dedicated MCP tool — enforcement lives inside the hook middleware.
    3. **Force context clear+reinject** — trigger `session.compacting` with reduced state. The harness invokes `request_compaction_snapshot` then immediately returns the reinject payload to opencode via `session.compacting`; the same session_id continues but with stripped context. Operational tool: `force_clear_and_reinject` (§3 entry 9).
    4. **Force-stop + human gate** — end session, surface via `question` tool. The harness invokes opencode's `question` tool with the named alternatives payload; the agent session pauses pending human selection. Operational tool: `surface_human_gate` (§3 entry 10). HRN-06 asserts this is the ONLY human-gate UI — no custom harness surface.

    Sub-section `### Per-tier MCP-tool surface map`:

    Render verbatim:

    ```
    | Tier | MCP tool                  | Module path                                              | §3 entry |
    |------|---------------------------|-----------------------------------------------------------|----------|
    | 1    | emit_advisory             | state_build/harness/intervention/emit_advisory.py        | 8        |
    | 2    | (none — middleware-only)  | (enforced inside tool.execute.before 7-layer stack)      | n/a      |
    | 3    | force_clear_and_reinject  | state_build/harness/intervention/force_clear_and_reinject.py | 9    |
    | 4    | surface_human_gate        | state_build/harness/intervention/surface_human_gate.py   | 10       |
    ```

    Note: "Tier 2 has NO dedicated MCP tool because the agent does not signal intent to block its own tool call — the block happens reactively in the middleware. Tier-2 events are recorded as `plan_edit_blocked`, `scope_check`, `prohibited_language_detected`, `gate_failing_next_task_blocked`, `subagent_whitelist_violation`, `subagent_cap_expansion_rejected`, `context_threshold_warning_block` (per the 7-layer stack)."

    ### Section 4.2 — Per-tier Trigger-Source Enumeration (the load-bearing HRN-04 claim)

    Heading: `### Per-tier Trigger-Source Enumeration`.

    1-paragraph intro: "Render the canonical 4-row trigger-source table verbatim. Every escalation site documented in Phases 402–405 maps to exactly one tier. The table is the load-bearing HRN-04 claim per 406-CONTEXT.md `<specifics>` 4th bullet."

    Render the 4-row table verbatim from 406-CONTEXT.md:

    ```
    | Tier | Trigger sources |
    |---|---|
    | Tier 1: advisory inject | APG advisory 1-2 + 4-5; PRF strike 1-2 + 4-5; DEV `log_deviation` accepted (pending resolution); SCOPE `scope_check` unresolved without exception; SUB `subagent_spot_check_failed` first occurrence on a tuple |
    | Tier 2: tool-block (via `tool.execute.before`) | SRP-04 `files_modified` allowlist (Layer 1); PAP-05 immutability (Layer 2); SRP-02 prohibited-language (Layer 3); PRF-07 gate-failing next-task block (Layer 4); SUB-03 `subagent_whitelist_violation` (Layer 6 stage 2); SUB-04 `subagent_cap_expansion_rejected` (Layer 6 stage 3); CTX-04 warning threshold (≤35%) next-task block |
    | Tier 3: force clear+reinject | APG advisory 3 (paralysis chain reinject); PRF strike 3 (gate chain reinject); CTX-04 emergency threshold (≤25%); CTX-09 reactive overflow recovery one-shot |
    | Tier 4: force-stop + human gate (opencode `question` tool only) | APG advisory 6; PRF strike 6; DEV Rule 4 architectural (always-stop, even under `--full-yolo`); DEV cap_exceeded → Rule 3 `checkpoint:decision` OR Rule 4 promotion; SUB `subagent_restart_exhausted`; SUB persistent orphan reconciliation step 6 |
    ```

    Sub-section `### Tier-1 trigger-source detail`:

    Render verbatim 5-bullet list (one per source chain):
    - **APG (Analysis Paralysis Guard, 404)** — advisories 1-2 + 4-5 on the per-task consecutive-read-only chain. Source event: `state.step.paralysis_event` (`tier="advisory"`). Owner spec: ANALYSIS-PARALYSIS-GUARD.md §"Counter mechanism" + §"6-advisory ladder".
    - **PRF (Boolean Proof Gate, 404)** — gate strikes 1-2 + 4-5 on the per-`(task_id, check_id)` chain. Source event: `state.step.gate_strike` (`strike_number ∈ {1,2,4,5}`). Owner spec: PROOF-GATE.md §6.
    - **DEV (Deviation Rules, 405)** — `log_deviation` accepted (resolution pending). Source event: `state.step.deviation_logged` with `resolution="pending"`. Owner spec: DEVIATION-RULES.md §3 + §6.
    - **SCOPE (Scope Reduction Prohibition, 404)** — `scope_check` unresolved without tracking-issue exception (SRP-02 / SRP-03). Source event: `state.step.scope_check` with `resolved=False, has_exception=False`. Owner spec: SCOPE-PROHIBITION.md SRP-02 + SRP-03.
    - **SUB (Subagent Management, 405)** — `subagent_spot_check_failed` first occurrence on a `(parent_task_id, subagent_type, return_field)` tuple. Source event: `state.step.subagent_spot_check_failed`. Owner spec: SUBAGENT-MONITORING.md §4.

    Sub-section `### Tier-2 trigger-source detail`:

    Render verbatim 7-bullet list (one per write-block stack layer):
    - **Layer 1: PAP-05 immutability check** (403). Source event: `state.step.plan_edit_blocked`. Owner: PLAN-AS-PROMPT.md PAP-05.
    - **Layer 2: SRP-04 `files_modified` allowlist** (404). Source event: `state.step.scope_check` with `out_of_scope_write=True`. Owner: SCOPE-PROHIBITION.md SRP-04.
    - **Layer 3: SRP-02 prohibited-language scan** (404). Source event: `state.step.scope_check` with `prohibited_token=<token>`. Owner: SCOPE-PROHIBITION.md SRP-02.
    - **Layer 4: PRF-07 gate-failing next-task block** (404). Source event: `state.step.gate_failing_next_task_blocked`. Owner: PROOF-GATE.md PRF-07.
    - **Layer 6 stage 2: SUB-03 `subagent_whitelist_violation`** (405). Source event: `state.step.subagent_whitelist_violation`. Owner: SUBAGENT-MANAGEMENT.md §5.
    - **Layer 6 stage 3: SUB-04 `subagent_cap_expansion_rejected`** (405). Source event: `state.slice.subagent_cap_expansion_rejected`. Owner: SUBAGENT-MANAGEMENT.md §6.
    - **CTX-04 warning threshold ≤35% next-task block** (402). Source event: `state.session.context_threshold_warning_block`. Owner: CONTEXT-PROTOCOL.md CTX-04.

    Sub-section `### Tier-3 trigger-source detail`:

    Render verbatim 4-bullet list:
    - **APG advisory 3 — paralysis chain reinject.** Source event: `state.step.paralysis_event(tier="reinject")`. Owner: ANALYSIS-PARALYSIS-GUARD.md APG-04.
    - **PRF strike 3 — gate chain reinject.** Source event: `state.step.gate_strike(strike_number=3)`. Owner: PROOF-GATE.md §6 6-strike ladder.
    - **CTX-04 emergency threshold (≤25%).** Source event: `state.session.context_threshold_emergency`. Owner: CONTEXT-PROTOCOL.md CTX-04 emergency row.
    - **CTX-09 reactive overflow recovery one-shot.** Source event: `state.session.overflow_recovery_attempted`. One-shot per user turn — the `_overflow_recovery_attempted` flag short-circuits on a second overflow within the same turn. Owner: CONTEXT-PROTOCOL.md CTX-09.

    Sub-section `### Tier-4 trigger-source detail`:

    Render verbatim 6-bullet list:
    - **APG advisory 6 — paralysis chain human gate.** Source event: `state.step.paralysis_event(tier="human_gate")`. Owner: ANALYSIS-PARALYSIS-GUARD.md APG-05.
    - **PRF strike 6 — gate chain human gate.** Source event: `state.step.gate_strike(strike_number=6)`. Owner: PROOF-GATE.md §6 6-strike ladder.
    - **DEV Rule 4 architectural.** Always human gate, even under `--full-yolo`. Source event: `state.step.deviation_logged(rule_id=4)`. Owner: DEVIATION-RULES.md DEV-04 + §"Rule 4 always-human-gate semantics are STRUCTURAL not policy".
    - **DEV cap_exceeded → Rule 3 `checkpoint:decision` OR Rule 4 promotion.** Source event: `state.step.deviation_cap_exceeded`. Owner: DEVIATION-RULES.md §3 cross-validation step 5.
    - **SUB `subagent_restart_exhausted`.** 3-restart counter exceeded; further restart attempts surface human gate. Source event: `state.step.subagent_restart_exhausted`. Owner: SUBAGENT-MONITORING.md §"5-source crash taxonomy + 3-restart counter".
    - **SUB persistent orphan reconciliation step 6.** When orphan probe persists across 6 reconciliation steps (daemon-down recovery 6-step protocol), surface as DEV Rule 4 human gate. Source event: `state.step.subagent_orphan_persistent`. Owner: SUBAGENT-MONITORING.md §"daemon-down orphan reconciliation 6-step protocol".
    - **SCOPE `scope_deviation_rejected`.** When a `scope_deviation_request` is rejected without matching `ARCH_PATTERN_ALLOWLIST`, the agent must surface to human. Source event: `state.step.scope_deviation_rejected`. Owner: SCOPE-PROHIBITION.md SRP-04 + cross-reference to DEVIATION-RULES.md §"cross-validation step 4 — scope_deviation_request correlation".

    ### Section 4.3 — `HarnessIntervention` Pydantic class (HRN-05)

    Heading: `### HarnessIntervention Pydantic class (HRN-05)`.

    1-paragraph intro: "The `state.harness.intervention` event carries the umbrella view of every harness intervention. Its payload is the `HarnessIntervention` Pydantic class. The class is rendered verbatim from 406-CONTEXT.md `<decisions>` 'harness_intervention event + 4-tier ladder (Area 4)' subsection. Fields: `tier` (4-value Literal), `trigger_reason` (18-value Literal exhaustively enumerated across APG / PRF / DEV / SUB / SCOPE / CTX chains), `target_step_or_task`, `correlation_event_id` (back-pointer to originating per-chain event), `slice_id`, `session_id`, `triggered_at` (UTC ISO-8601)."

    Sub-section `#### Class definition (verbatim)`:

    Render the full `HarnessIntervention` Pydantic class verbatim from 406-CONTEXT.md `<decisions>` subsection (see <interfaces> Excerpt A). Use a `python` code-fence. All 18 trigger_reason Literal values MUST appear in the rendered class.

    Sub-section `#### Field semantics`:

    Render verbatim a markdown table:

    ```
    | Field                  | Type                                | Semantics                                                              |
    |------------------------|-------------------------------------|------------------------------------------------------------------------|
    | tier                   | Literal[4 values]                   | Server-derived from source-chain event type → dispatch (§4.4)         |
    | trigger_reason         | Literal[18 values]                  | Exhaustive across APG/PRF/DEV/SUB/SCOPE/CTX; pure-machine assignment    |
    | target_step_or_task    | str                                 | task_id or step_id depending on which chain triggered                  |
    | correlation_event_id   | str                                 | Back-pointer to originating per-chain event (paralysis_event, gate_strike, deviation_logged, etc.) |
    | slice_id               | str                                 | Slice owning the intervention                                          |
    | session_id             | str                                 | Active session at trigger time                                         |
    | triggered_at           | datetime (UTC, ISO-8601)            | Pure-machine timestamp; replay-deterministic                           |
    ```

    Sub-section `#### Module ownership`:

    Render verbatim:
    - **Single-source-of-truth module:** `state_build/harness/intervention/`
    - **Submodules:**
      - `emit_advisory.py` — tier-1 MCP tool handler (§3 entry 8)
      - `force_clear_and_reinject.py` — tier-3 MCP tool handler (§3 entry 9)
      - `surface_human_gate.py` — tier-4 MCP tool handler (§3 entry 10)
      - `projector.py` — umbrella event reducer (CQRS handler chain entry)
      - `dispatcher.py` — tier classification dispatch from source chain → umbrella event
      - `types.py` — `HarnessIntervention` Pydantic class + tier/trigger_reason Literals
    - **Event name:** `state.harness.intervention` (registered under `BUILD_ONLY_EVENT_PREFIXES`)
    - **Event aggregate_type:** `slice` (umbrella event aggregates at Slice level; replay rehydrates per-Slice intervention chain)

    Sub-section `#### Cross-reference: HRN-05 satisfied`:

    Render verbatim: "HRN-05 requires that 'each intervention emits a `harness_intervention` event with tier, trigger reason, target step/task.' The HarnessIntervention class above satisfies HRN-05 exactly: `tier` field (4-value Literal), `trigger_reason` field (18-value Literal), `target_step_or_task` field. The class also adds `correlation_event_id`, `slice_id`, `session_id`, `triggered_at` for replay completeness (HRN-07)."

    <quality_scan>
      <code_to_reuse>
        - Known: 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" — VERBATIM source for HarnessIntervention class + 4-tier trigger-source table.
        - Known: 406-CONTEXT.md `<specifics>` 4th bullet — load-bearing-claim framing for §4.2 intro.
        - Known: REQUIREMENTS.md HRN-04 — 4-tier numbered list verbatim.
        - Known: §3 entries 8, 9, 10 in HARNESS-ARCHITECTURE.md (Plan 02's output) — MCP tool surface map for tier 1 / 3 / 4.
        - Grep pattern: `grep -nE "tier|trigger_reason|HarnessIntervention" /Users/tmac/Projects/state/.planning/milestones/v41/phases/406/406-CONTEXT.md | head -40` — locates verbatim source.
        - Grep pattern: `grep -nE "advisory 1-2|strike 1-2|spot_check_failed|scope_check" /Users/tmac/Projects/state/.planning/milestones/v41/phases/406/406-CONTEXT.md | head -20` — locates trigger source list.
        - Grep pattern: `grep -nE "6-strike|paralysis_event|gate_strike" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md | head -10` — confirms APG/PRF chain semantics.
      </code_to_reuse>
      <docs_to_consult>
        - 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" — verbatim source for all of §4.1, §4.2, §4.3.
        - 406-CONTEXT.md `<specifics>` 4th bullet — load-bearing-claim framing.
        - REQUIREMENTS.md HRN-04 / HRN-05 / HRN-06 — req-level constraints.
        - Phase 404 PROOF-GATE.md §6 — 6-strike ladder source (precedent for tier 1 / 3 / 4 escalation).
        - Phase 404 ANALYSIS-PARALYSIS-GUARD.md APG-04 / APG-05 — APG advisory 3 → reinject; APG advisory 6 → human gate sources.
        - Phase 405 DEVIATION-RULES.md DEV-04 + "Rule 4 always-human-gate STRUCTURAL not policy" — tier-4 DEV trigger source.
        - Phase 405 SUBAGENT-MONITORING.md §4 — SUB tier-1 + tier-4 trigger sources.
        - Phase 404 SCOPE-PROHIBITION.md SRP-04 — tier-2 + tier-4 SCOPE trigger sources.
        - Phase 402 CONTEXT-PROTOCOL.md CTX-04 + CTX-09 — tier-2 + tier-3 CTX trigger sources.
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
        && wc -l "$F" | awk '{exit ($1 < 950)}' \
        && grep -qE "^## §4 4-Tier Intervention Ladder \+ harness_intervention Event \+ Human-Gate-Only-via-question \(HRN-04, HRN-05, HRN-06\)" "$F" \
        && grep -qE "^### 4-Tier Ladder Overview \(HRN-04\)" "$F" \
        && grep -qE "^### Per-tier Trigger-Source Enumeration" "$F" \
        && grep -qE "^### HarnessIntervention Pydantic class \(HRN-05\)" "$F" \
        && grep -q "class HarnessIntervention(BaseModel)" "$F" \
        && grep -q 'tier: Literal\["advisory", "tool_block", "clear_reinject", "human_gate"\]' "$F" \
        && grep -q "paralysis_threshold_crossed" "$F" \
        && grep -q "paralysis_chain_3_reinject" "$F" \
        && grep -q "paralysis_chain_6_human_gate" "$F" \
        && grep -q "gate_strike_advisory" "$F" \
        && grep -q "gate_strike_3_reinject" "$F" \
        && grep -q "gate_strike_6_human_gate" "$F" \
        && grep -q "deviation_logged_pending" "$F" \
        && grep -q "deviation_cap_exceeded" "$F" \
        && grep -q "deviation_rule_4_architectural" "$F" \
        && grep -q "subagent_spot_check_failed" "$F" \
        && grep -q "subagent_crash_detected" "$F" \
        && grep -q "subagent_restart_exhausted" "$F" \
        && grep -q "subagent_orphan_persistent" "$F" \
        && grep -q "scope_check_unresolved" "$F" \
        && grep -q "scope_deviation_rejected" "$F" \
        && grep -q "context_threshold_warning" "$F" \
        && grep -q "context_threshold_emergency" "$F" \
        && grep -q "context_overflow_reactive" "$F" \
        && grep -q "target_step_or_task: str" "$F" \
        && grep -q "correlation_event_id: str" "$F" \
        && grep -q "triggered_at: datetime" "$F" \
        && grep -q "advisory inject\|Advisory inject" "$F" \
        && grep -q "tool-block" "$F" \
        && grep -q "force clear+reinject\|Force context clear" "$F" \
        && grep -q "force-stop \+ human gate\|Force-stop \+ human gate" "$F" \
        && grep -q "emit_advisory" "$F" \
        && grep -q "force_clear_and_reinject" "$F" \
        && grep -q "surface_human_gate" "$F" \
        && grep -q "state_build/harness/intervention/" "$F" \
        && grep -q "state.harness.intervention" "$F" \
        && grep -q "BUILD_ONLY_EVENT_PREFIXES" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] §4 appended; §0–§3 unchanged.
    - [check: must_haves.truths[1]] §4 heading + §4.1 + §4.2 + §4.3 subheadings present.
    - [check: must_haves.truths[2]] §4.1 renders 4-tier ordered list with operational MCP tool per tier.
    - [check: must_haves.truths[3]] §4.2 trigger-source table rendered verbatim with 4 rows.
    - [check: must_haves.truths[4]] §4.2 tier-1 detail covers APG 1-2+4-5, PRF 1-2+4-5, DEV pending, SCOPE unresolved, SUB spot_check_failed.
    - [check: must_haves.truths[5]] §4.2 tier-2 detail covers all 7 write-block stack layers from §2.
    - [check: must_haves.truths[6]] §4.2 tier-3 detail covers APG advisory 3, PRF strike 3, CTX-04 emergency, CTX-09 reactive overflow.
    - [check: must_haves.truths[7]] §4.2 tier-4 detail covers APG advisory 6, PRF strike 6, DEV Rule 4, DEV cap_exceeded, SUB restart_exhausted, SUB orphan_persistent.
    - [check: must_haves.truths[8]] §4.3 HarnessIntervention class renders verbatim with 18-value trigger_reason Literal and all 7 fields.
    - [check: must_haves.truths[9]] §4.3 module-ownership subsection names state_build/harness/intervention/ + 6 submodules + BUILD_ONLY_EVENT_PREFIXES.
    - [check: must_haves.truths[18]] No `GSD-` literal in the file.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md grows by ~150 lines (§4.1 + §4.2 + §4.3); file ≥950 lines; HarnessIntervention class renders verbatim; all 18 trigger_reason Literal values present; 4-tier table renders; tier-1/2/3/4 detail bullet lists render; verify-block bash passes; no `GSD-` literal; §0–§3 untouched.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append §4.4 + §4.5 + §4.6 — emission model + tier dispatcher + HRN-06 structural invariant + mode-isolation + Plan-04 forward-reference</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Task 1's output — append §4.4 + §4.5 + §4.6 below)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" — VERBATIM source for emission model + HRN-06 structural invariant
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<code_context>` "Established patterns (carry-forward)" — pure-machine + plugin-as-thin-reporter discipline cite
    - .planning/milestones/v41/REQUIREMENTS.md lines 132-134 (HRN-06 verbatim)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (search "no .full_yolo bypass. branch|Rule 4 always-human-gate STRUCTURAL" — absence-of-bypass precedent for §4.5)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md (search "exhaustive|assert_never|state_build/subagents/types.py" — module-isolation precedent for §4.6)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (search "pure-machine|server-derived" — PRF-04 discipline cite for closing paragraph)
  </read_first>

  <action>
    Append §4.4 + §4.5 + §4.6 + closing paragraph to the existing HARNESS-ARCHITECTURE.md. **DO NOT modify any prior section.** **Concrete content from 406-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 4.4 — Emission Model (alongside source events, NOT replacing)

    Heading: `### Emission Model — Alongside Source Events`.

    1-paragraph intro (render verbatim from 406-CONTEXT.md `<decisions>` "harness_intervention event" subsection): "The originating chain emits its own event (e.g., `state.step.paralysis_event` with `tier=\"reinject\"`); the daemon middleware additionally emits `state.harness.intervention` with `tier=\"clear_reinject\"` and `correlation_event_id` pointing at the paralysis_event row. **Two events per intervention**; replay can reconstruct the umbrella view from `state.harness.intervention` rows OR from the per-chain rows independently. Mirrors the gsd-2 cross-layer comm-map pattern where one runtime action surfaces in multiple bus views."

    Sub-section `#### Four-counter independence (cross-reference)`:

    Render verbatim: "The four per-chain counters (APG paralysis, PRF gate strike, DEV deviation attempt, SUB restart) remain independent — they never share state. The `state.harness.intervention` event is the SOLE rollup point that unifies these four chains into one umbrella view. Cross-reference: PROOF-GATE.md §6 + DEVIATION-RULES.md §6 + SUBAGENT-MONITORING.md §4. Carry-forward of the 4-counter independence discipline established in 404/405."

    Sub-section `#### Worked example — tier-3 paralysis reinject`:

    Render verbatim:

    ```
    Scenario: agent has hit APG advisory 3 (third paralysis advisory on the same task).

    1. APG counter projector observes consecutive_read_only_count = 5 for task=task-3
       (3rd consecutive threshold cross on the SAME task without intervening write).

    2. APG projector emits:
         state.step.paralysis_event{
             tier="reinject",
             task_id="task-3",
             count=3,                              # 3rd advisory on this task
             threshold=5,                          # execute-slice default
             agent_response_summary="…last turn…",
             triggered_at=...
         }

    3. The daemon's intervention dispatcher (state_build/harness/intervention/dispatcher.py)
       maps source-event paralysis_event(tier="reinject") → umbrella tier "clear_reinject".

    4. Dispatcher emits:
         state.harness.intervention{
             tier="clear_reinject",
             trigger_reason="paralysis_chain_3_reinject",
             target_step_or_task="task-3",
             correlation_event_id="<paralysis_event row id from step 2>",
             slice_id="slice-N",
             session_id="sess-X",
             triggered_at=...
         }

    5. Replay rebuilds the umbrella view from EITHER source (step 2 row) OR umbrella row
       (step 4) — drift between the two views is detectable by replay comparison and
       indicates a dispatcher bug.

    6. force_clear_and_reinject MCP tool fires:
         - request_compaction_snapshot → CompactionSnapshot row emitted
         - session.compacting hook returns reinject payload to opencode
         - Same session_id continues with stripped context + reinject payload

    7. APG counter for task-3 resets on the next intervening write-mutating tool call.
    ```

    Sub-section `#### Tier dispatcher (assert_never exhaustiveness)`:

    Render verbatim:

    ```python
    # state_build/harness/intervention/dispatcher.py
    from typing import assert_never

    SourceEventType = Literal[
        "state.step.paralysis_event",
        "state.step.gate_strike",
        "state.step.deviation_logged",
        "state.step.deviation_cap_exceeded",
        "state.step.subagent_spot_check_failed",
        "state.step.subagent_crash_detected",
        "state.step.subagent_restart_exhausted",
        "state.step.subagent_orphan_persistent",
        "state.step.scope_check",
        "state.step.scope_deviation_rejected",
        "state.session.context_threshold_warning_block",
        "state.session.context_threshold_emergency",
        "state.session.overflow_recovery_attempted",
        # tool.execute.before tier-2 events
        "state.step.plan_edit_blocked",
        "state.step.gate_failing_next_task_blocked",
        "state.step.subagent_whitelist_violation",
        "state.slice.subagent_cap_expansion_rejected",
    ]

    def dispatch_to_umbrella(
        source_type: SourceEventType,
        source_payload: dict,
    ) -> HarnessIntervention | None:
        match source_type:
            # APG chain
            case "state.step.paralysis_event":
                tier_value = source_payload["tier"]  # "advisory" | "reinject" | "human_gate"
                match tier_value:
                    case "advisory":   return _build(tier="advisory", reason="paralysis_threshold_crossed", source_payload=source_payload)
                    case "reinject":   return _build(tier="clear_reinject", reason="paralysis_chain_3_reinject", source_payload=source_payload)
                    case "human_gate": return _build(tier="human_gate", reason="paralysis_chain_6_human_gate", source_payload=source_payload)
                    case _:            raise ValueError(...)

            # PRF chain
            case "state.step.gate_strike":
                strike = source_payload["strike_number"]
                if strike in (1, 2, 4, 5): return _build(tier="advisory", reason="gate_strike_advisory", source_payload=source_payload)
                elif strike == 3:          return _build(tier="clear_reinject", reason="gate_strike_3_reinject", source_payload=source_payload)
                elif strike == 6:          return _build(tier="human_gate", reason="gate_strike_6_human_gate", source_payload=source_payload)
                else: raise ValueError(...)

            # DEV chain
            case "state.step.deviation_logged":
                if source_payload["rule_id"] == 4:
                    return _build(tier="human_gate", reason="deviation_rule_4_architectural", source_payload=source_payload)
                else:
                    return _build(tier="advisory", reason="deviation_logged_pending", source_payload=source_payload)
            case "state.step.deviation_cap_exceeded":
                return _build(tier="human_gate", reason="deviation_cap_exceeded", source_payload=source_payload)

            # SUB chain
            case "state.step.subagent_spot_check_failed":
                return _build(tier="advisory", reason="subagent_spot_check_failed", source_payload=source_payload)
            case "state.step.subagent_crash_detected":
                return _build(tier="advisory", reason="subagent_crash_detected", source_payload=source_payload)
            case "state.step.subagent_restart_exhausted":
                return _build(tier="human_gate", reason="subagent_restart_exhausted", source_payload=source_payload)
            case "state.step.subagent_orphan_persistent":
                return _build(tier="human_gate", reason="subagent_orphan_persistent", source_payload=source_payload)

            # SCOPE chain
            case "state.step.scope_check":
                if source_payload.get("resolved") is False and not source_payload.get("has_exception"):
                    return _build(tier="advisory", reason="scope_check_unresolved", source_payload=source_payload)
                return None  # resolved or exception present — no umbrella emission
            case "state.step.scope_deviation_rejected":
                return _build(tier="human_gate", reason="scope_deviation_rejected", source_payload=source_payload)

            # CTX chain
            case "state.session.context_threshold_warning_block":
                return _build(tier="tool_block", reason="context_threshold_warning", source_payload=source_payload)
            case "state.session.context_threshold_emergency":
                return _build(tier="clear_reinject", reason="context_threshold_emergency", source_payload=source_payload)
            case "state.session.overflow_recovery_attempted":
                return _build(tier="clear_reinject", reason="context_overflow_reactive", source_payload=source_payload)

            # tool.execute.before tier-2 events
            case "state.step.plan_edit_blocked":
                return _build(tier="tool_block", reason="scope_check_unresolved", source_payload=source_payload)  # closest umbrella; v14 may add tier-2-specific reasons in v17
            case "state.step.gate_failing_next_task_blocked":
                return _build(tier="tool_block", reason="scope_check_unresolved", source_payload=source_payload)
            case "state.step.subagent_whitelist_violation":
                return _build(tier="tool_block", reason="scope_check_unresolved", source_payload=source_payload)
            case "state.slice.subagent_cap_expansion_rejected":
                return _build(tier="tool_block", reason="scope_check_unresolved", source_payload=source_payload)

            case _:
                assert_never(source_type)
    ```

    Note: "Future tier-2 trigger_reason values (e.g., `plan_edit_blocked`, `files_modified_violation`, `subagent_whitelist_violation`) may be added in v17 to disambiguate tier-2 umbrella views; v1 uses `scope_check_unresolved` as the closest umbrella reason for all tier-2 tool-blocks. The 18-value Literal in §4.3 covers the cross-chain spectrum; tier-2 fan-out is the documented v17 follow-up. Tracking-issue logged at `# TODO(HRN-04.tier2)` in `state_build/harness/intervention/types.py`."

    Sub-section `#### Pure-machine discipline`:

    Render verbatim: "The umbrella `tier` value is **server-derived**, never agent-emitted. The dispatcher above is a deterministic match on source-chain event type + payload field → umbrella tier; no LLM-as-judge anywhere. Mirrors PRF-04 spirit (gsd-2 `server-recomputation-of-llm-emitted-fields.md`) and the carry-forward rule from §1."

    ### Section 4.5 — HRN-06 Human-Gate-Only-via-opencode-question (structural invariant)

    Heading: `### HRN-06 Human-Gate-Only-via-opencode-question (structural invariant)`.

    Render verbatim from 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" Human-Gate-Only subsection:

    "**The harness NEVER invents its own UI for human gates.** Every tier-4 path renders via opencode's `question` tool with the named alternatives payload. The absence of any other UI surface in `state_build/harness/intervention/` is the structural enforcement; CI grep targets the directory and rejects PRs introducing alternate UI primitives. Mirrors the absence-of-bypass pattern from Phase 405 DEV-04 (no `full_yolo bypass` branch in `state_build/deviation/log_deviation.py`)."

    Sub-section `#### CI grep enforcement`:

    Render verbatim:

    ```bash
    # CI grep target: state_build/harness/intervention/ MUST NOT contain ANY of these:
    grep -rnE '(\\bprompt\\(|\\binput\\(|\\bConfirm\\(|Inquirer|click\\.prompt|TUI human_gate|Textual.*question|prompt_toolkit)' \\
      src/state_build/harness/intervention/

    # Expected: zero matches.
    # The ONLY acceptable human-gate surface in this directory is a call into surface_human_gate
    # MCP tool, which in turn invokes opencode's `question` tool (a primitive provided by opencode
    # core, not state code).
    ```

    Sub-section `#### Acceptable surface (the only one)`:

    Render verbatim:

    ```python
    # state_build/harness/intervention/surface_human_gate.py
    # The ONLY function in state_build/harness/intervention/ that produces a human-facing prompt.
    # It calls into the opencode plugin's question-tool wrapper.

    def surface_human_gate(payload: SurfaceHumanGateInput) -> SurfaceHumanGateOutput:
        # 1. Validate payload (Pydantic extra="forbid").
        # 2. Emit state.harness.intervention(tier="human_gate", ...).
        # 3. Call opencode plugin to surface its `question` tool.
        # 4. Wait for the question response from opencode (SSE-driven).
        # 5. Emit state.step.deviation_resolution_recorded or analogous resolution event.
        ...
    ```

    Sub-section `#### Carry-forward: absence-of-bypass discipline`:

    Render verbatim: "Phase 405 DEV-04 establishes the absence-of-bypass pattern: `state_build/deviation/log_deviation.py` MUST NOT contain any `if mode == 'full-yolo': bypass()` branch; the absence is the structural enforcement. Phase 406 §4.5 extends this to the whole `state_build/harness/intervention/` directory: no custom UI primitives, no autonomy short-circuit branches, no LLM-as-judge calls. CI greps both directories."

    ### Section 4.6 — Mode-isolation

    Heading: `### Mode-isolation note`.

    Render verbatim: "All modules under `state_build/harness/intervention/` MUST NOT import from `state_teach/`. CI import-graph lint enforces. The `state.harness.intervention` event lives in `BUILD_ONLY_EVENT_PREFIXES = frozenset({'state.slice.', 'state.step.', 'state.harness.'})`. Teach-mode equivalent intervention surface is owned by v47; mode silos remain physical. Carry-forward from 405."

    ### Closing — Plan-04 forward reference

    Heading: `### Forward reference: §5 + §6 (Plan 04)`.

    Render verbatim: "§5 (Plan 04 of this phase) will enumerate the `state.harness.intervention` event among the ~30 event types the HRN-07 replay protocol must consume — Category 5 (umbrella + context) of the 5-table breakdown. §6 (Plan 04) will surface specific intervention emission points in the full-Slice lifecycle Mermaid sequence diagram (HRN-08); the exemplar Slice is the `compaction-snapshot-schema` Slice from 403 EXEMPLAR-stepNPLAN.md, with at least one tier-1 advisory site (paralysis-counter cross), one tier-2 site (PAP-05 immutability block), one tier-3 site (force_clear_and_reinject demo), and one tier-4 site (the `checkpoint:decision` task on orjson flag selection, surfaced via surface_human_gate)."

    <quality_scan>
      <code_to_reuse>
        - Known: 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" Human-Gate-Only subsection — VERBATIM source for §4.5.
        - Known: 406-CONTEXT.md `<decisions>` "Event-replay reconstruction (HRN-07)" Category 5 row — preview source for closing forward reference.
        - Known: 406-CONTEXT.md `<code_context>` "Established patterns" — pure-machine + 4-counter independence carry-forward cite.
        - Known: 405 DEVIATION-RULES.md DEV-04 "Rule 4 always-human-gate STRUCTURAL not policy" — absence-of-bypass precedent.
        - Known: 405 SUBAGENT-MANAGEMENT.md Section 4 — assert_never exhaustiveness Python pattern precedent.
        - Known: 403 EXEMPLAR-stepNPLAN.md — exemplar Slice referenced in closing.
        - Grep pattern: `grep -nE "absence.of.bypass|full_yolo bypass|STRUCTURAL not policy" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md | head -5` — locates absence-of-bypass precedent.
        - Grep pattern: `grep -nE "assert_never|match source_type|case \"state" /Users/tmac/Projects/state/.planning/milestones/v41/phases/406/406-CONTEXT.md | head -10` — locates dispatcher reference shape.
      </code_to_reuse>
      <docs_to_consult>
        - 406-CONTEXT.md `<decisions>` "harness_intervention event + 4-tier ladder (Area 4)" — verbatim source for emission model + HRN-06.
        - 405 DEVIATION-RULES.md DEV-04 + Rule 4 STRUCTURAL section — absence-of-bypass precedent.
        - 405 SUBAGENT-MANAGEMENT.md Section 4 — assert_never pattern.
        - REQUIREMENTS.md HRN-06 — req-level constraint.
        - 403 EXEMPLAR-stepNPLAN.md — exemplar Slice for closing forward-reference.
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
        && wc -l "$F" | awk '{exit ($1 < 1050)}' \
        && grep -qE "^### Emission Model" "$F" \
        && grep -qE "^### HRN-06 Human-Gate-Only-via-opencode-question" "$F" \
        && grep -qE "^### Mode-isolation note" "$F" \
        && grep -qE "^### Forward reference" "$F" \
        && grep -q "Two events per intervention" "$F" \
        && grep -q "sole rollup point\|SOLE rollup point\|sole rollup" "$F" \
        && grep -qE "^#### Worked example" "$F" \
        && grep -qE "^#### Tier dispatcher" "$F" \
        && grep -q "dispatch_to_umbrella" "$F" \
        && grep -q "assert_never(source_type)" "$F" \
        && grep -q "match source_type" "$F" \
        && grep -q "rule_id\\] == 4" "$F" \
        && grep -q "deviation_rule_4_architectural" "$F" \
        && grep -q "Pure-machine discipline\\|pure-machine discipline\\|server-derived" "$F" \
        && grep -q "CI grep enforcement\\|CI grep target" "$F" \
        && grep -q "Inquirer\\|click\\.prompt\\|prompt_toolkit" "$F" \
        && grep -q "absence-of-bypass\\|absence of bypass" "$F" \
        && grep -q "full_yolo bypass\\|full-yolo bypass" "$F" \
        && grep -q "state_build/harness/intervention/" "$F" \
        && grep -q "v47\\|teach-mode" "$F" \
        && grep -q "compaction-snapshot-schema" "$F" \
        && grep -q "EXEMPLAR-stepNPLAN\\|EXEMPLAR.stepNPLAN" "$F" \
        && grep -q "checkpoint:decision" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[10]] §4.4 emission-model intro renders the verbatim "two events per intervention" paragraph.
    - [check: must_haves.truths[11]] §4.4 worked example renders all 7 numbered steps with the paralysis_event + harness_intervention emission pair.
    - [check: must_haves.truths[12]] §4.4 tier dispatcher renders Python match-case with rule_id==4 branch + assert_never(source_type) close.
    - [check: must_haves.truths[13]] §4.5 HRN-06 structural invariant renders verbatim including absence-of-UI assertion.
    - [check: must_haves.truths[14]] §4.5 CI grep enforcement subsection renders with the literal grep command targeting Inquirer / click.prompt / prompt_toolkit.
    - [check: must_haves.truths[15]] §4.6 mode-isolation note renders state_build/harness/intervention MUST NOT import state_teach.
    - [check: must_haves.truths[16]] Closing "Pure-machine discipline carry-forward" paragraph renders.
    - [check: must_haves.truths[17]] Plan-04 forward-reference paragraph renders with §5 + §6 cross-references + exemplar Slice cite.
    - [check: must_haves.truths[18]] No `GSD-` literal in the file.
    - [check: must_haves.artifacts[0]] File ≥1050 lines.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md grows by ~100 lines (§4.4 + §4.5 + §4.6 + closing); file ≥1050 lines; emission model + worked example + tier dispatcher + HRN-06 structural invariant + CI grep enforcement + mode-isolation note all render verbatim; verify-block bash passes; no `GSD-` literal; §0–§4.3 untouched.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

```bash
F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md

# §0–§3 still present (Plans 01+02 untouched)
grep -qE "^# Harness Architecture \(Canonical, v41 Rollup\)" "$F" || { echo "MISSING_§0"; exit 1; }
grep -qE "^## §1 Layered Diagram \(HRN-01\)" "$F" || { echo "MISSING_§1"; exit 1; }
grep -qE "^## §2 Plugin Hook Inventory \(HRN-02\)" "$F" || { echo "MISSING_§2"; exit 1; }
grep -qE "^## §3 state-build MCP Tool Catalog \(HRN-03\)" "$F" || { echo "MISSING_§3"; exit 1; }

# §4 + all subsections
for section in \
  "^## §4 4-Tier Intervention Ladder" \
  "^### 4-Tier Ladder Overview" \
  "^### Per-tier Trigger-Source Enumeration" \
  "^### HarnessIntervention Pydantic class" \
  "^### Emission Model" \
  "^### HRN-06 Human-Gate-Only-via-opencode-question" \
  "^### Mode-isolation note" \
  "^### Forward reference"; do
  grep -qE "$section" "$F" || { echo "MISSING: $section"; exit 1; }
done

# All 18 trigger_reason values
for reason in paralysis_threshold_crossed paralysis_chain_3_reinject paralysis_chain_6_human_gate gate_strike_advisory gate_strike_3_reinject gate_strike_6_human_gate deviation_logged_pending deviation_cap_exceeded deviation_rule_4_architectural subagent_spot_check_failed subagent_crash_detected subagent_restart_exhausted subagent_orphan_persistent scope_check_unresolved scope_deviation_rejected context_threshold_warning context_threshold_emergency context_overflow_reactive; do
  grep -q "$reason" "$F" || { echo "MISSING_REASON: $reason"; exit 1; }
done

# HarnessIntervention class
grep -q "class HarnessIntervention(BaseModel)" "$F" || { echo "MISSING_HARNESS_INTERVENTION_CLASS"; exit 1; }
grep -q "target_step_or_task: str" "$F" || { echo "MISSING_FIELD_target_step_or_task"; exit 1; }
grep -q "correlation_event_id: str" "$F" || { echo "MISSING_FIELD_correlation_event_id"; exit 1; }
grep -q "triggered_at: datetime" "$F" || { echo "MISSING_FIELD_triggered_at"; exit 1; }

# Tier dispatcher
grep -q "dispatch_to_umbrella" "$F" || { echo "MISSING_DISPATCHER_FN"; exit 1; }
grep -q "assert_never(source_type)" "$F" || { echo "MISSING_ASSERT_NEVER_SOURCE_TYPE"; exit 1; }

# HRN-06
grep -q "absence-of-bypass\|absence of bypass" "$F" || { echo "MISSING_ABSENCE_OF_BYPASS"; exit 1; }
grep -qE "Inquirer|click\\.prompt|prompt_toolkit" "$F" || { echo "MISSING_CI_GREP_TARGETS"; exit 1; }

# Plan-04 forward reference
grep -q "compaction-snapshot-schema" "$F" || { echo "MISSING_EXEMPLAR_CITE"; exit 1; }

# Line count
wc -l "$F" | awk '{ if ($1 < 1050) { print "LINE_COUNT_FAIL: " $1; exit 1 } }'

# Naming discipline
! grep -qE '\bGSD-' "$F" || { echo "GSD_NAMING_VIOLATION"; exit 1; }

echo "HARNESS-ARCHITECTURE.md §4 verification OK"
```
</verification>

<success_criteria>
- §4 appended to HARNESS-ARCHITECTURE.md; total file ≥ 1050 lines.
- 4-tier ladder overview + per-tier trigger-source table render verbatim from 406-CONTEXT.md.
- HarnessIntervention Pydantic class renders with all 18 trigger_reason Literal values + 7 fields.
- Tier dispatcher with `assert_never(source_type)` exhaustiveness pattern renders.
- Emission-model "two events per intervention" + worked example + 4-counter independence cross-reference all render.
- HRN-06 structural invariant + CI grep enforcement subsections render verbatim.
- Mode-isolation note + Plan-04 forward-reference (§5 + §6) render.
- Section §0–§3 untouched.
- No `GSD-` literal in the file (project naming discipline).
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/406/03-intervention-ladder-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: spec-doc final line count, sections rendered (§4.1–§4.6 + closing forward-reference), HRN-04 / HRN-05 / HRN-06 coverage verification (all 4 tiers documented with operational MCP tools; HarnessIntervention class verbatim with 18-value trigger_reason Literal; human-gate-only-via-question structural invariant + CI grep enforcement), naming-discipline verification result (`grep '\bGSD-' = 0`).
</output>
