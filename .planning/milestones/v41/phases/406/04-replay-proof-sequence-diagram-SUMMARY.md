---
phase: 406
plan: 04-replay-proof-sequence-diagram
subsystem: harness-architecture-rollup
tags: [HRN-07, HRN-08, replay-proof, sequence-diagram, design-only]
requirements: [HRN-07, HRN-08]
provides:
  sections:
    - "§5 Event-Replay Reconstruction Proof (HRN-07)"
    - "§5.1 5-category replay event enumeration (38 event types)"
    - "§5.2 5-step reconstruction protocol (deterministic, O(N+K), pure-machine)"
    - "§5.3 daemon-restart worked example (mid-run-slice, 2 in-flight subagents, APG 4 of 6)"
    - "§5.3 restart-flow Mermaid sequenceDiagram"
    - "§6 Full-Slice Lifecycle Sequence Diagram (HRN-08)"
    - "§6.1 single Mermaid sequenceDiagram walking compaction-snapshot-schema Slice across 4 stages"
    - "§6.2 per-stage event tally + 4-tier intervention call-out table + HRN-06 verification"
    - "Rollup Complete — HRN-01..08 mapping table + phase-close discipline + v14 forward-reference"
affects:
  files:
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
key-files:
  modified:
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  created: []
decisions:
  - "Use the 403 EXEMPLAR-stepNPLAN.md compaction-snapshot-schema Slice as the named exemplar for HRN-08 — already canonical, mature must_haves, mature threat model, includes a checkpoint:decision task that provides a real (not contrived) tier-4 trigger."
  - "Embed §5.3 restart-flow as a small Mermaid sequenceDiagram (≈30 lines) AND the full-Slice lifecycle as the larger §6.1 sequenceDiagram (≈100 lines) — two diagrams covering complementary scopes (restart-only vs end-to-end). Avoids stuffing the worked example into the lifecycle diagram while keeping both visualizations operative."
  - "Total event surface lands at 38 types across 5 categories (not the ~30 estimate from CONTEXT.md); the count grew because SUB chain has 8 events not 5, and the Plan-lifecycle chain has 9 not 6. Documented in §5.1 closing paragraph as the operative count."
  - "Tier-2 umbrella trigger_reason mapping: §6.1 surfaces plan_edit_blocked → state.harness.intervention(tier=tool_block, trigger_reason=scope_check_unresolved) per §4.4 v1 closest-umbrella-reason discipline; v17 follow-up tracking issue documented inline."
metrics:
  duration: "single-session execution"
  completed: 2026-05-12
  tasks_executed: 6
  commits: 6
  file_size_before_lines: 1390
  file_size_after_lines: 1991
  lines_added: 601
  events_in_HRN-08_diagram: "36 event lines, 14 distinct types"
  tier_interventions_in_HRN-08_diagram: 4
---

# Phase 406 Plan 04: Event-Replay Reconstruction Proof + Full-Slice Sequence Diagram — Summary

Appends §5 (HRN-07 event-replay reconstruction proof) + §6 (HRN-08 full-Slice lifecycle Mermaid sequence diagram) + closing "Rollup Complete — All 8 HRN Requirements Covered" section to `HARNESS-ARCHITECTURE.md`, completing the Phase 406 harness architecture rollup with HRN-01..08 fully covered across §1–§6.

## What landed

### §5 Event-Replay Reconstruction Proof (HRN-07)

- **§5.1 5-category replay event enumeration.** 38 event types organized into 5 tables: Slice-stage chain (4 events), plan-lifecycle chain (9 events), counter chains (17 events spanning APG/PRF/DEV/SUB), scope chain (4 events), umbrella+context (4 events). Per-event: type string + Pydantic class + owning v41 spec. Total surface 38 events; double-count discipline (Category 5 umbrella rows pair with Category 3-4 source events) carried forward from §4.4.
- **§5.2 5-step reconstruction protocol.** Step 1 facade-open; Step 2 latest CompactionSnapshot rehydration (with SUB-08 extension fields seeding `in_flight_subagents` + `subagent_restart_counters`); Step 3 forward-replay applying 5 per-chain reducers (APG / PRF / DEV / SUB / intervention); Step 4 orphan reconciliation via 405 SUB-08 6-step protocol; Step 5 plugin hook resume (chat.params reinject payload + tool.execute.before 6-layer write-block stack). Protocol invariants: deterministic, O(N+K) in event count + orphan count, snapshot-optional, synthetic-event traceable, pure-machine.
- **§5.3 daemon-restart worked example (hard case).** Mid-`run-slice` restart with 2 in-flight subagents (`inv-A` researcher with restart counter 1, `inv-B` pattern-mapper with restart counter 0), APG paralysis counter at 4 of 6 on `task-3`, last `CompactionSnapshot` taken 30s before restart. Walks all 5 steps showing: snapshot rehydration restores SUB state directly; replay forward catches 6 post-snapshot `subagent_progress` + the APG advisory_4 + paired umbrella intervention; orphan probe finds both alive → silent success; reinject payload includes `<prior_crash>` for `inv-A` but no new `<paralysis_advisory>` (rehydration is silent). Restart Mermaid sequenceDiagram (≈30 lines) summarizes the flow. Closing 5-takeaway list seals the HRN-07 proof.

### §6 Full-Slice Lifecycle Sequence Diagram (HRN-08)

- **§6.1 single Mermaid sequenceDiagram** walking the `compaction-snapshot-schema` exemplar Slice (the canonical 403 EXEMPLAR-stepNPLAN.md exemplar) across all 4 stages: design-slice → research-slice → run-slice (Step 1 containing `task-1` RED test + `task-2` GREEN implement + `task-3` `checkpoint:decision` for orjson flag) → verify-slice → close. **36 event lines surfaced (exceeds ≥25 minimum), 14 distinct event types**.
- **4 tier-intervention sites surfaced** (one per tier, each with a named trigger source):
  - **Tier 1** (advisory): APG `paralysis_event(advisory_number=1)` on `task-3` read-only window crossing threshold.
  - **Tier 2** (tool_block): PAP-05 immutability on PLAN.md `<plan>` block triggering `plan_edit_blocked` → umbrella `tier=tool_block`.
  - **Tier 3** (clear_reinject): APG `paralysis_event(advisory_number=3)` firing `compaction.snapshot_taken(trigger=threshold)` + reinject + umbrella `tier=clear_reinject, trigger_reason=paralysis_chain_3_reinject`.
  - **Tier 4** (human_gate): `task-3` `checkpoint:decision` surfacing via opencode's `question` tool with `[OPT_NAIVE_UTC, OPT_UTC_Z]` labeled list — HRN-06 structural invariant verified (no state-side UI primitive in the diagram).
- **§6.2 diagram annotations.** Per-stage event tally; tier-intervention call-out table mapping each named site to source chain + umbrella `trigger_reason`; HRN-06 structural-invariant verification; cross-references to every 402-405 owning spec for every event class surfaced; diagram-extensibility note listing the paths deferred to v14 EXEMPLAR (PRF strike ladder, DEV cap_exceeded, SUB crash/restart, SUB orphan, SCOPE Layer 1, CTX percent-threshold).

### Rollup Complete — All 8 HRN Requirements Covered

- HRN-01..08 → §1–§6 mapping table with operative-contracts-inlined column + upstream-cross-references column.
- Phase-close discipline restated: no amendments to prior 402-405 specs; drift-as-defect rule; build-mode only; STATE-* naming; pure-machine everywhere; append-only event store.
- Forward-reference into v14 (Build Kernel) and v15 (Build Core Commands) implementation contracts.
- Final invariant: "the harness's state is fully reconstructable from `.state/events.sqlite` alone, given a daemon restart at any moment."

## Commits

| Task | Commit | Lines added | Subject |
| --- | --- | --- | --- |
| 1 | `f29a6f9` | +121 | §5.1 5-category replay event enumeration (HRN-07) |
| 2 | `5898c3a` | +68 | §5.2 5-step reconstruction protocol (HRN-07) |
| 3 | `fed2c5c` | +157 | §5.3 daemon-restart worked example + restart Mermaid (HRN-07 hard case) |
| 4 | `7354504` | +146 | §6.1 full-Slice lifecycle Mermaid sequenceDiagram (HRN-08) |
| 5 | `d8204c9` | +63 | §6.2 diagram annotations (HRN-08) |
| 6 | `54fd057` | +46 | Rollup Complete — HRN-01..08 mapping + phase-close |

**Total: 6 commits, +601 lines.** File size 1390 → 1991 lines.

## Verification (per success criteria)

| Criterion | Target | Actual | Status |
| --- | --- | --- | --- |
| All tasks executed | 6 | 6 | PASS |
| Each task committed individually with `--no-verify` | 6 commits | 6 commits | PASS |
| HARNESS-ARCHITECTURE.md final size | ≥1800 lines | 1991 lines | PASS |
| §5 contains 5-category event table | 5 tables, ~30 events | 5 tables, 38 events | PASS |
| §5 contains 5-step reconstruction protocol | Numbered list | §5.2 5 numbered steps | PASS |
| §5 contains daemon-restart worked example | Hard case | §5.3 mid-run-slice + 2 subagents + APG 4-of-6 + restart Mermaid | PASS |
| §6 single Mermaid sequenceDiagram across 4 stages | ≥25 events | 36 event lines, 14 distinct types | PASS |
| §6 ≥4 tier-interventions | 4 (one per tier) | 4 (Tier 1 advisory / Tier 2 tool_block / Tier 3 clear_reinject / Tier 4 human_gate) | PASS |
| Rollup Complete section maps HRN-01..08 to §1-§6 | Mapping table | 8 rows present | PASS |
| Prior wave sections (§0-§4) intact | All present | §1, §2, §3, §4 all present at original line numbers | PASS |
| No `GSD-` literals in §5+§6 body | 0 | 0 | PASS |
| SUMMARY.md created at canonical path | yes | this file | PASS |

### Self-Check

```
[ -f ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md" ] → FOUND
wc -l ≥ 1800 → 1991 (PASS)
grep -nE "^## §[1-6]\." → §1, §2, §3, §4, §5, §6 all present
grep -n "^## Rollup Complete" → line 1948 (FOUND)
grep "GSD-" in §5+§6+rollup → 0 matches
git log --oneline a6f77f6..HEAD → 6 commits f29a6f9, 5898c3a, fed2c5c, 7354504, d8204c9, 54fd057 (all FOUND)
```

## Self-Check: PASSED

## Deviations from Plan

None — the plan was executed exactly as specified by the orchestrator's `<critical_directives>` and `<success_criteria>`. The original `04-replay-proof-sequence-diagram-PLAN.md` file was not present at base commit `a6f77f6` (only its three predecessor SUMMARYs existed); the executor derived the 6-task breakdown directly from the success criteria and the supporting context files (`406-CONTEXT.md` §"Event-replay reconstruction (HRN-07)" subsection, prior phase event-name registries, the canonical 403 exemplar). No architectural deviations; no auth gates; no Rule-4 escalations.

One minor count adjustment: the 406-CONTEXT.md predicted ~30 event types in §5.1; the operative count landed at 38 (the SUB chain has 8 events not 5 per the 405 SUBAGENT-MONITORING.md final spec, and the plan-lifecycle chain has 9 not 6 per 403 STEP-EVENTS.md). The discrepancy is documented inline in §5.1's closing paragraph; the 38-event count is the operative final value for HRN-07's replay-input enumeration.

## Closing

Phase 406 plan 04 is complete. With this plan closed, all 4 plans of Phase 406 have landed:

- Plan 01 (`01-layered-diagram-hook-inventory`) — §1 + §2 (HRN-01, HRN-02)
- Plan 02 (`02-mcp-tool-catalog`) — §3 (HRN-03)
- Plan 03 (`03-intervention-ladder`) — §4 (HRN-04, HRN-05, HRN-06)
- Plan 04 (`04-replay-proof-sequence-diagram`) — §5 + §6 + Rollup Complete (HRN-07, HRN-08)

Phase 406 is design-only; no source code lands. v14 (Build Kernel) will implement the rollup's contracts. v9 TUI bundle will consume the SSE stream. The next phase boundary is the Phase 406 phase-close commit (separate from this plan-close commit) which requires SECURITY.md per `.planning/config.json` `security_enforcement=true`.
