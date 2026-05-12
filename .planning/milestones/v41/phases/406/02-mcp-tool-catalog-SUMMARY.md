---
phase: 406
plan: 02
title: "state-build MCP Tool Catalog (HRN-03)"
status: complete
wave: 2
requirements_completed:
  - HRN-03
files_modified:
  - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
commits:
  - b4dd102: "feat(406-02): append §3 intro + roster + MCP_TOOL_REGISTRY + assert_never (HRN-03 part 1)"
  - 937c05c: "feat(406-02): append §3.4 + §3.5 + §3.6 — 14 per-tool entries + hook matrix + coverage (HRN-03 part 2)"
final_line_count: 1039
delta_lines: +674
completed: 2026-05-12
---

# Phase 406 Plan 02: state-build MCP Tool Catalog Summary

**One-liner:** Appended §3 (HRN-03) to HARNESS-ARCHITECTURE.md — full state-build MCP tool catalog with all 14 tools rendered as Pydantic input/output models (`extra="forbid"`), `MCP_TOOL_REGISTRY` + `assert_never` exhaustiveness pattern, hook-integration matrix, and Phase-402–405 coverage cross-reference.

## What was built

`§3 state-build MCP Tool Catalog (HRN-03)` was appended to the canonical rollup at `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md`. The section now sits between Plan 01's §2 (Plugin Hook Inventory) and the future §4 (intervention ladder, Plan 03). File grew from 365 lines (post-Plan-01) to 1039 lines (+674 lines). §0, §1, §2 from Plan 01 remain byte-for-byte untouched.

### Sections rendered

| Subsection | Heading | Purpose |
|---|---|---|
| §3 intro | `## §3 state-build MCP Tool Catalog (HRN-03)` | HRN-03 invariant statement; 14-tool count; hooks-vs-MCP partition cross-reference |
| §3.1 | `### Tool roster` | Locked 14-tool table (name, owning phase, source spec) |
| §3.2 | `### MCP_TOOL_REGISTRY` | `ToolName` Literal union + `McpToolBase` + `McpToolSpec` + registry dict at `state_build/mcp/registry.py` |
| §3.3 | `### Exhaustiveness via assert_never` | 14-case dispatcher with `assert_never(tool_name)` final case; CI `mypy --strict` discipline |
| §3.3a | `#### Mode-isolation note` | `state_build/mcp/` MUST NOT import `state_teach/` |
| §3.4 | `### Per-tool catalog entries` | 14 sub-subsections (`#### N. {tool_name}`) with full Pydantic models |
| §3.5 | `### Hook integration matrix` | Maps each of 14 tools to its `tool.execute.before/after` layer (or "agent-only") |
| §3.6 | `### Coverage cross-reference (HRN-03 closure)` | REQ-category → tools matrix for CTX/STP/PAP/PRF/APG/SRP/DEV/SUB/HRN |

### HRN-03 closure verification

HRN-03 requires that **every harness operation specified in Phases 402–405 is mapped to at least one MCP tool**. The §3.6 coverage matrix discharges this:

| REQ category | Coverage |
|---|---|
| CTX (402) | `query_context_meter`, `request_compaction_snapshot`, `force_clear_and_reinject` (CTX-09) |
| STP (403) | `complete_task`, `record_plan_edit` |
| PAP (403) | `record_plan_edit` (PAP-04 emit-site) |
| PRF (404) | `check_proof_gate`, `complete_task` (strike trigger) |
| APG (404) | `emit_advisory`, `force_clear_and_reinject`, `surface_human_gate` |
| SRP (404) | `request_step_split`, `scope_deviation_request` |
| DEV (405) | `log_deviation`, `surface_human_gate` (Rule 4) |
| SUB (405) | `dispatch_subagent`, `complete_task`, `surface_human_gate` |
| HRN (406 new) | `emit_advisory`, `force_clear_and_reinject`, `surface_human_gate`, `query_event_store` |

100% Phase-402–405 operation coverage confirmed.

### 4 NEW tools (first specification — Phase 406 owns)

| Tool | Tier / role | Source spec pointer |
|---|---|---|
| `emit_advisory` | HRN-04 tier 1 (advisory inject) | THIS spec §4 (Plan 03) |
| `force_clear_and_reinject` | HRN-04 tier 3 (clear + reinject) | THIS spec §4 (Plan 03) + CTX-09 |
| `surface_human_gate` | HRN-04 tier 4 (human gate via opencode `question`) | THIS spec §4 (Plan 03) + HRN-06 |
| `query_event_store` | HRN-07 reconstruction protocol read API | THIS spec §5 (Plan 04) |

All four have full Pydantic input + output models; their `trigger_reason` / `source_trigger` Literal value sets are aligned with the umbrella `HarnessIntervention.trigger_reason` Literal that Plan 03 will document in §4.

### Cross-spec Pydantic re-inlining

Per the hybrid cross-reference rule (operative contracts inlined; explanatory prose by pointer), the following authoritative shapes were re-inlined into §3 verbatim from their owning specs so that v14 implementers can use HARNESS-ARCHITECTURE.md as the implementation contract without round-tripping through 4 prior specs:

- `Rule4Option` ← DEVIATION-RULES.md §3 (used in `log_deviation` input)
- `DispatchSubagent` + `SingleDispatch` + `ParallelDispatch` + `ChainDispatch` ← SUBAGENT-MANAGEMENT.md §2 (used in `dispatch_subagent` input)
- `SubagentRejection` ← SUBAGENT-MANAGEMENT.md §5 (used in `dispatch_subagent` output)
- `MustHavesBlock` + `ArtifactCheck` + `KeyLinkCheck` + `FailedCheck` ← PROOF-GATE.md §4 (used in `check_proof_gate`)
- `EventEnvelope` ← `state_core/schema.py:239-265` (used in `query_event_store` output)
- `QuestionAlternative` ← opencode question-tool spec (used in `surface_human_gate` input)

Drift between any re-inlined class and its source spec is a documented defect detectable by grep.

## Verification result

Plan-level `<verification>` block (from PLAN.md):

```
HARNESS-ARCHITECTURE.md §3 verification OK (1039 lines)
```

All checks passed:

- §0 + §1 + §2 still present (Plan 01 sections untouched)
- §3 + all 6 subsection headings present
- 14 per-tool sub-subsections (`#### 1. complete_task` … `#### 14. record_plan_edit`) present in locked order
- All 14 tool names appear
- `model_config = ConfigDict(extra="forbid")` discipline present (43 occurrences)
- `assert_never(tool_name)` exhaustiveness dispatcher present
- "100% Phase-402–405 operation coverage" statement present
- File ≥ 800 lines (1039 actual)
- **Naming-discipline result: `grep '\bGSD-' = 0`** — zero `GSD-` literals in the file. STATE-* / state-* exclusively.

## Acceptance criteria from PLAN.md

All 25 `must_haves.truths[0..24]` from the plan were satisfied. The single artifact requirement (`min_lines: 800` on HARNESS-ARCHITECTURE.md) was satisfied at 1039 lines. All 4 `key_links` (back-cross-references to DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, PROOF-GATE.md, CONTEXT-PROTOCOL.md) are present in §3.

## Deviations from Plan

**None — plan executed exactly as written**, with one micro-rewording for self-contained verify pass:

**1. [Rule 3 - blocking issue] §3 intro paragraph re-worded to satisfy Task 1 standalone verify-block**

- **Found during:** Task 1 verify
- **Issue:** The plan's verbatim intro literal opened with capital-E "Every harness operation specified in Phases 402–405..." but the verify-block uses a case-sensitive grep for lowercase `every harness operation`. Section 3.6 (Task 2) provides the lowercase phrasing, but Task 1's verify-block failed standalone.
- **Fix:** Prepended "HRN-03 invariant: " so the operative phrase reads "**HRN-03 invariant: every harness operation specified in Phases 402–405 maps to at least one MCP tool**" — preserves the plan's full literal text, satisfies the case-sensitive grep, and reinforces the HRN-03 contract phrasing.
- **Files modified:** `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` (§3 intro)
- **Commit:** `b4dd102`

## Worktree base-mismatch note (orchestrator infra)

The orchestrator spawned this executor in a worktree whose branch tip (`worktree-agent-a0868cd0931cbd0e0`) was at commit `1e678d8` (v13 milestone work on the `state` build-out branch) instead of the EXPECTED_BASE `d1ceb5e` (Plan 01's Wave-1 completion commit on the v41 design lineage). The two lineages are not ancestrally related — a rebase produced merge conflicts. Per `<worktree_branch_check>` fallback protocol, executed `git reset --hard d1ceb5e` to align with the expected base; then re-attached the worktree branch ref to the new HEAD before continuing. The v13 commits that were on this worktree branch tip remain reachable in the main checkout's `main` lineage and are not lost.

This is an orchestrator infra observation worth logging but did NOT affect the plan's correctness — Wave 1's HARNESS-ARCHITECTURE.md was present and intact at d1ceb5e, and both Task 1 + Task 2 commits land cleanly on top.

## Issues Encountered

None beyond the documented deviation above.

## Forward-pointers wired

- **§4 (Plan 03):** consumes `emit_advisory` (tier 1), `force_clear_and_reinject` (tier 3), `surface_human_gate` (tier 4) for the HRN-04 4-tier ladder. Also consumes `log_deviation`, `dispatch_subagent`, `check_proof_gate` for the per-tier trigger-source enumeration.
- **§5 (Plan 04):** consumes `query_event_store` for the HRN-07 reconstruction protocol.
- **§6 (Plan 04):** walks `complete_task` and `complete_slice` through the full-Slice lifecycle sequence diagram (HRN-08).

All four NEW tool Literal value sets (`source_trigger`, `trigger_reason` x3) are pre-aligned with the umbrella `HarnessIntervention.trigger_reason` Literal that Plan 03 will inline — no cross-plan drift expected.

## Self-Check: PASSED

- `[ -f .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md ]` → FOUND (1039 lines)
- `git log --oneline | grep -q b4dd102` → FOUND (Task 1 commit)
- `git log --oneline | grep -q 937c05c` → FOUND (Task 2 commit)
- `! grep -qE '\bGSD-' HARNESS-ARCHITECTURE.md` → FOUND zero GSD- literals
- `grep -c 'model_config = ConfigDict(extra="forbid")' HARNESS-ARCHITECTURE.md` → 43 (well above the 14-tools-×-2-models = 28 minimum)
