---
phase: 406
plan: 03
subsystem: harness-architecture-rollup
tags: [harness, intervention-ladder, harness_intervention-event, hrn-04, hrn-05, hrn-06, design-only]
requires:
  - 406-01 (HRN-01 layered diagram + HRN-02 hook inventory)
  - 406-02 (HRN-03 MCP tool catalog — provides emit_advisory, force_clear_and_reinject, surface_human_gate as §3 entries 8/9/10)
provides:
  - HARNESS-ARCHITECTURE.md §4 — 4-tier intervention ladder + state.harness.intervention umbrella event Pydantic class + HRN-06 human-gate-only-via-question structural invariant
affects:
  - HARNESS-ARCHITECTURE.md (single artifact; grew from 1039 → 1390 lines)
  - v14 Build Kernel: contract for state_build/harness/intervention/ module (dispatcher, projector, types, three MCP-tool handlers)
  - v9 TUI bundle: contract for state.harness.intervention SSE subscription + per-tier visual treatment
tech-stack:
  added: []
  patterns:
    - assert_never compile-time exhaustiveness (carried from 405 SUB-06)
    - Pydantic `extra="forbid"` everywhere
    - server-derived umbrella tier (no LLM-as-judge) — PRF-04 spirit
    - 4-counter independence + sole-rollup-point (carry-forward from 404/405)
    - absence-of-bypass structural enforcement via CI grep (carry-forward from 405 DEV-04)
key-files:
  created: []
  modified:
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (1039 → 1390 lines; §4 appended)
decisions:
  - "HarnessIntervention rendered as a verbatim copy of 406-CONTEXT.md `<decisions>` Area 4 — 18-value trigger_reason Literal, 4-value tier Literal, 7 fields including correlation_event_id for two-events-per-intervention replay determinism."
  - "Tier 2 has NO dedicated MCP tool — enforcement lives reactively inside tool.execute.before middleware; documented explicitly in §4.1 surface map note."
  - "Tier dispatcher uses Python match-case with assert_never(source_type) close — mirrors Phase 405 SUBAGENT_RETURN_REGISTRY exhaustiveness pattern."
  - "Tier-2 fan-out (per-layer trigger_reason values) deferred to v17 — tracked at `# TODO(HRN-04.tier2)` in state_build/harness/intervention/types.py. v1 reuses scope_check_unresolved as the umbrella tier-2 reason."
  - "HRN-06 enforced structurally via CI grep on src/state_build/harness/intervention/ rejecting Inquirer / click.prompt / prompt_toolkit / Textual prompts — mirrors 405 DEV-04 absence-of-bypass discipline."
metrics:
  duration: "~6 minutes"
  completed: "2026-05-12"
  tasks: 2
  files: 1
---

# Phase 406 Plan 03: 4-Tier Intervention Ladder + harness_intervention Event Summary

Appended §4 (HRN-04 + HRN-05 + HRN-06) to the canonical `HARNESS-ARCHITECTURE.md`, completing the umbrella-event design layer for the v41 harness rollup. §4 introduces the `state.harness.intervention` event with an 18-value `trigger_reason` Literal that exhaustively rolls up APG / PRF / DEV / SUB / SCOPE / CTX trigger sources into one 4-tier ladder, and asserts the absence-of-UI-bypass structural invariant that pins all human-gate surfaces to opencode's `question` tool.

## What landed

Task 1 — §4.1 + §4.2 + §4.3 (commit `8d4bb64`):

- §4 heading + 1-paragraph synthesis intro citing 406-CONTEXT.md `<specifics>` 4th bullet as load-bearing claim.
- §4.1 4-tier ladder overview rendered verbatim from REQUIREMENTS.md HRN-04 as an ordered list with per-tier operational MCP tool: tier 1 → `emit_advisory` (§3 entry 8); tier 2 → middleware-only (no MCP tool, enforced inside `tool.execute.before` 7-layer stack); tier 3 → `force_clear_and_reinject` (§3 entry 9); tier 4 → `surface_human_gate` (§3 entry 10).
- §4.1 Per-tier MCP-tool surface map table + explanatory note on why tier 2 has no agent-driven MCP tool.
- §4.2 per-tier trigger-source enumeration: 4-row table rendered verbatim from 406-CONTEXT.md across APG, PRF, DEV, SUB, SCOPE, CTX chains, followed by tier-1 / tier-2 / tier-3 / tier-4 per-bullet detail listing source events and owning specs.
- §4.3 `HarnessIntervention` Pydantic class rendered verbatim with `ConfigDict(extra="forbid")`, the 4-value `tier` Literal, the 18-value `trigger_reason` Literal (paralysis_threshold_crossed, paralysis_chain_3_reinject, paralysis_chain_6_human_gate, gate_strike_advisory, gate_strike_3_reinject, gate_strike_6_human_gate, deviation_logged_pending, deviation_cap_exceeded, deviation_rule_4_architectural, subagent_spot_check_failed, subagent_crash_detected, subagent_restart_exhausted, subagent_orphan_persistent, scope_check_unresolved, scope_deviation_rejected, context_threshold_warning, context_threshold_emergency, context_overflow_reactive), and all 7 fields (tier, trigger_reason, target_step_or_task, correlation_event_id, slice_id, session_id, triggered_at).
- §4.3 Field semantics table + module-ownership subsection naming `state_build/harness/intervention/` as single-source-of-truth + 6 submodules (`emit_advisory.py`, `force_clear_and_reinject.py`, `surface_human_gate.py`, `projector.py`, `dispatcher.py`, `types.py`) + event registration under `BUILD_ONLY_EVENT_PREFIXES`.
- §4.3 HRN-05 cross-reference confirming the class satisfies the 3 required HRN-05 fields plus 4 replay-completeness fields.

Task 2 — §4.4 + §4.5 + §4.6 + closing (commit `4129723`):

- §4.4 emission model rendered verbatim with "Two events per intervention" invariant — originating chain emits its own event AND daemon middleware emits the umbrella `state.harness.intervention` event with `correlation_event_id` pointing at the source row.
- §4.4 four-counter independence cross-reference: APG / PRF / DEV / SUB counters never share state; `state.harness.intervention` is the SOLE rollup point.
- §4.4 worked example: tier-3 paralysis reinject scenario in 7 numbered steps demonstrating the paired emission of `state.step.paralysis_event(tier="reinject")` + `state.harness.intervention(tier="clear_reinject", trigger_reason="paralysis_chain_3_reinject")`, including the `force_clear_and_reinject` follow-through that fires `request_compaction_snapshot` and the `session.compacting` reinject hop.
- §4.4 tier dispatcher: full Python `match` block over a 17-value `SourceEventType` Literal mapping each source-chain event type (+ payload discriminator field where needed — `tier`, `strike_number`, `rule_id`, `resolved`/`has_exception`) to the umbrella `(tier, trigger_reason)` tuple. Includes `assert_never(source_type)` close for compile-time exhaustiveness. Tracking-issue note for v17 tier-2 fan-out via `# TODO(HRN-04.tier2)`.
- §4.4 Pure-machine discipline subsection: dispatcher is deterministic match; no LLM-as-judge — carry-forward of PRF-04 spirit + gsd-2 `server-recomputation-of-llm-emitted-fields.md` pattern.
- §4.5 HRN-06 structural invariant rendered verbatim: harness NEVER invents its own UI for human gates; tier-4 paths exclusively use opencode's `question` tool.
- §4.5 CI grep enforcement: explicit `grep -rnE '(\bprompt\(|\binput\(|\bConfirm\(|Inquirer|click\.prompt|TUI human_gate|Textual.*question|prompt_toolkit)' src/state_build/harness/intervention/` target with zero-match expectation.
- §4.5 acceptable-surface code block: the only function in `state_build/harness/intervention/` allowed to produce a human-facing prompt is `surface_human_gate.py`, and only by delegating to opencode's `question` tool.
- §4.5 carry-forward absence-of-bypass paragraph: extends 405 DEV-04 `full_yolo bypass` discipline to the whole intervention directory.
- §4.6 mode-isolation: `state_build/harness/intervention/` MUST NOT import `state_teach/`; CI import-graph lint; event prefix registration; v47 owns teach-mode equivalent.
- Closing pure-machine discipline carry-forward paragraph + Plan-04 forward-reference paragraph naming the `compaction-snapshot-schema` exemplar Slice + tier-1/2/3/4 emission sites including the `checkpoint:decision` task on orjson flag selection.

## HRN coverage verification

- **HRN-04 (4-tier intervention ladder)** — fully covered. §4.1 + §4.2 enumerate all 4 tiers with verbatim trigger-source table + per-tier detail listings spanning APG / PRF / DEV / SUB / SCOPE / CTX chains. Every escalation site documented in Phases 402–405 maps to exactly one tier; the table is the load-bearing HRN-04 claim per 406-CONTEXT.md `<specifics>` 4th bullet.
- **HRN-05 (harness_intervention umbrella event)** — fully covered. §4.3 renders the `HarnessIntervention` Pydantic class verbatim with 4-value tier Literal, 18-value trigger_reason Literal, and 7 fields. §4.4 emission model establishes the "two events per intervention" replay invariant. §4.4 dispatcher renders the deterministic match-case with `assert_never` closure.
- **HRN-06 (human-gate-only-via-opencode-question)** — fully covered as a STRUCTURAL invariant. §4.5 renders the absence-of-UI assertion verbatim; CI grep enforcement subsection targets Inquirer / click.prompt / prompt_toolkit / Textual prompts in `src/state_build/harness/intervention/` with zero-match expectation. Absence-of-bypass discipline carries forward from 405 DEV-04.

## Naming-discipline verification

```bash
grep '\bGSD-' .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
# Returns 0 matches → STATE-* naming preserved
```

Result: **zero `GSD-` literals** anywhere in the spec. All identifiers use `state.*` event names, `state_build/*` module paths, and `STATE-*` prefixes per CLAUDE.md project convention.

## File-state delta

| Metric | Before Plan 03 | After Plan 03 | Delta |
|---|---|---|---|
| HARNESS-ARCHITECTURE.md line count | 1039 | 1390 | +351 |
| §4 line range | (absent) | 1040 – 1390 | +351 |
| Pydantic classes rendered in §4 | 0 | 1 (`HarnessIntervention`) | +1 |
| Trigger_reason Literal values | 0 | 18 | +18 |
| MCP tools referenced as tier surfaces | 0 | 3 (from §3 entries 8/9/10) | +3 |
| Mermaid/code blocks added | 0 | 5 (worked-example, dispatcher Python, Pydantic class, CI grep, surface_human_gate sketch) | +5 |

## Deviations from Plan

None — plan executed exactly as written. One internal plan-grep mismatch observed but does not affect correctness:

- The Task 2 verify-block contains `grep -q "rule_id\\] == 4"` (which searches for the literal `rule_id] == 4`), but the dispatcher excerpt the plan instructed to render verbatim uses `source_payload["rule_id"] == 4` (with the closing `"]`). The literal content rendered matches the plan's `<interfaces>` Excerpt source exactly; the verify-block regex is cosmetically misaligned but the corresponding `acceptance_criteria` requirement ("renders Python match-case with rule_id==4 branch + assert_never(source_type) close") is satisfied. The phase-end verification block (lines 774–828 of the plan) does not contain this specific grep and passes cleanly.

## Worktree note

Initial Edit tool call inadvertently wrote to the upstream repo path (`/Users/tmac/Projects/state/...`) rather than the worktree path (`/Users/tmac/Projects/state/.claude/worktrees/agent-a85c598196622fecb/...`). The upstream-path edit was reverted with `git checkout HEAD --` before any commit; the worktree was then edited correctly. No upstream state escaped the worktree; both commits land in this worktree's branch.

## Issues Encountered

None.

## Self-Check: PASSED

- File modified: `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` — verified present at 1390 lines.
- Commit `8d4bb64` (Task 1) — verified in `git log`.
- Commit `4129723` (Task 2) — verified in `git log`.
- All 18 `trigger_reason` Literal values present (verified via per-value `grep -q`).
- All 8 §4 headings present (`§4`, `4-Tier Ladder Overview`, `Per-tier Trigger-Source Enumeration`, `HarnessIntervention Pydantic class`, `Emission Model`, `HRN-06 Human-Gate-Only-via-opencode-question`, `Mode-isolation note`, `Forward reference`).
- `HarnessIntervention` class definition present.
- `assert_never(source_type)` present.
- `dispatch_to_umbrella` present.
- `compaction-snapshot-schema` exemplar Slice cited.
- CI grep targets (`Inquirer`, `click\.prompt`, `prompt_toolkit`) present.
- No `GSD-` literal anywhere in spec.
- §0 + §1 + §2 + §3 (Plans 01+02 outputs) untouched.

## Forward references

- Plan 04 (Wave 4) consumes §4 outputs:
  - §5 HRN-07 replay protocol enumeration will list `state.harness.intervention` under Category 5 (umbrella + context) of the 5-table breakdown.
  - §6 HRN-08 full-Slice lifecycle Mermaid sequence diagram will surface specific intervention emission points along the `compaction-snapshot-schema` exemplar Slice — at least one tier-1 site (paralysis-counter cross), one tier-2 site (PAP-05 immutability block), one tier-3 site (force_clear_and_reinject demo), one tier-4 site (`checkpoint:decision` orjson flag selection via `surface_human_gate`).
- v14 Build Kernel inherits the §4.4 dispatcher contract + §4.5 absence-of-bypass + §4.6 mode-isolation rules as authoritative implementation constraints.
- v9 TUI bundle inherits the `state.harness.intervention` SSE event shape from §4.3 for per-tier visual treatment rendering.
