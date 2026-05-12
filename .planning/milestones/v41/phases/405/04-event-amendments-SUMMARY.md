---
phase: 405
plan: 04
subsystem: v40-master-registry-amendments
tags: [v41, phase-405, event-taxonomy, artifact-catalog, frontmatter-schemas, append-only, registry-index]
dependency_graph:
  requires:
    - 405-01 (DEVIATION-RULES.md — source of 4 deviation events + arch_patterns/trailers module paths)
    - 405-02 (SUBAGENT-MANAGEMENT.md — source of subagent_whitelist_violation + cap_expansion_rejected events + dispatch/types/parallel_cap module paths + allowed_subagents/subagent frontmatter fields)
    - 405-03 (SUBAGENT-MONITORING.md — source of 8 subagent runtime events + returns/spot_check/restart/orphan_reconcile/autonomy module paths + CompactionSnapshot extension)
  provides:
    - v40 EVENT-TAXONOMY.md registry index for Phase 405's 14 new state.{step,slice}.* events
    - v40 ARTIFACT-CATALOG.md registry index for Phase 405's 13 new state_build/* modules + stepNSUMMARY ## Deviations section + CompactionSnapshot extension
    - v40 FRONTMATTER-SCHEMAS.md registry index for Phase 405's 3 new SliceFrontmatter fields (autonomy, allowed_subagents, subagent)
  affects:
    - Phase 406 HARNESS-ARCHITECTURE.md (forward-references state.harness.intervention umbrella aggregating 4 of the 14 new events)
    - v14 Build Kernel implementation (must consume registry rows for module creation)
tech_stack:
  added: []
  patterns: [append-only-master-registry-amendment, forward-pointer-to-owning-spec, registry-index-not-schema-source]
key_files:
  created:
    - .planning/milestones/v41/phases/405/04-event-amendments-SUMMARY.md
  modified:
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (+43 lines; 348 -> 391)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (+44 lines; 849 -> 893)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md (+40 lines; 303 -> 343)
decisions:
  - "All 14 new event types use BUILD_ONLY_EVENT_PREFIXES (state.{step,slice}.*); no state.teach.* analogs (teach-mode harness owned by v47)."
  - "Append-only invariant verified by git diff: 127 insertions, 0 deletions across 3 files. Phase 402/403/404 amendment blocks byte-identical."
  - "Registry-index pattern: amendment rows are forward-pointers; full Pydantic schemas + behaviors live in owning Phase 405 spec docs. When index and owning spec drift, owning spec wins (authoritative-ordering note rendered in each amendment block)."
  - "FRONTMATTER-SCHEMAS.md received its first v41 amendment in this plan (no prior v41 amendments existed); the new block is positioned below the v40 design-contract closing line."
  - "STATE-* trailer naming-discipline cross-reference rendered in EVENT-TAXONOMY.md amendment (STATE-Task, STATE-DeviationRule, STATE-DeviationAttempt, STATE-Subagent-Invocation); no GSD- literal in any of the three new amendment blocks."
metrics:
  duration: ~22 min
  completed: 2026-05-11
  tasks_total: 2
  tasks_completed: 2
  files_modified: 3
  lines_added: 127
  lines_removed: 0
  commits: 2
---

# Phase 405 Plan 04: Event Amendments Summary

**One-liner:** Append three append-only v41 amendment blocks to v40 master registry specs (EVENT-TAXONOMY.md, ARTIFACT-CATALOG.md, FRONTMATTER-SCHEMAS.md), registering Phase 405's 14 new state.{step,slice}.* events, 13 new state_build/* modules + CompactionSnapshot extension + ## Deviations projector section, and 3 new SliceFrontmatter fields, with forward-pointers to owning Phase 405 sibling specs.

## Outcome

All 14 deviation/subagent events from Plans 01-03 are now indexed in EVENT-TAXONOMY.md with forward-pointers to their canonical Pydantic schemas. All 13 new Python modules from Plans 01-03 are indexed in ARTIFACT-CATALOG.md. The three new SliceFrontmatter fields (autonomy from DEV-06, allowed_subagents from SUB-03, subagent from SUB-04+SUB-07) are indexed in FRONTMATTER-SCHEMAS.md. The CompactionSnapshot extension (Phase 402 Pydantic + Phase 405's two new fields subagent_restart_counters + in_flight_subagents) is documented in the catalog with SUBAGENT-MONITORING.md §7 forward-pointer.

Phase 405 design is now complete (4/4 plans). Plans 01-03 authored the canonical sibling specs; Plan 04 amended the v40 master registries so v14 Build Kernel readers can discover the new artifacts from the master catalogs and follow forward-pointers to the owning Phase 405 specs.

## Tasks Completed

| Task | Description | Commit | Files |
|---|---|---|---|
| 1 | Append `## v41 Amendment — Phase 405 Deviation + Subagent Event Family` to EVENT-TAXONOMY.md (14 events) | 74b58d6 | EVENT-TAXONOMY.md |
| 2 | Append `## v41 Amendment — Phase 405 Deviation + Subagent Artifacts` to ARTIFACT-CATALOG.md (13 modules + CompactionSnapshot ext + ## Deviations section) AND `## v41 Amendment — Phase 405 SliceFrontmatter Extensions` to FRONTMATTER-SCHEMAS.md (3 fields + SubagentSliceConfig nested shape) | 00c34a0 | ARTIFACT-CATALOG.md, FRONTMATTER-SCHEMAS.md |

## 14 New Event Types Registered

**Deviation family (4 events, all owned by DEV-07 → DEVIATION-RULES.md):**
1. `state.step.deviation_logged`
2. `state.step.deviation_classification_rejected`
3. `state.step.deviation_resolution_recorded`
4. `state.step.deviation_cap_exceeded`

**Subagent control family (2 events):**
5. `state.step.subagent_whitelist_violation` (SUB-03 → SUBAGENT-MANAGEMENT.md §5)
6. `state.slice.subagent_cap_expansion_rejected` (SUB-04 → SUBAGENT-MANAGEMENT.md §6)

**Subagent runtime family (8 events, all owned by SUB-05..SUB-09 → SUBAGENT-MONITORING.md):**
7. `state.step.subagent_started` (SUB-05 §2)
8. `state.step.subagent_progress` (SUB-05 §2)
9. `state.step.subagent_complete` (SUB-05 §2)
10. `state.step.subagent_spot_check_failed` (SUB-06 §4)
11. `state.step.subagent_crash_detected` (SUB-07 §5)
12. `state.step.subagent_restart` (SUB-07 §5-6)
13. `state.step.subagent_restart_exhausted` (SUB-07 §5)
14. `state.step.subagent_orphan_detected` (SUB-08 §7)

All 14 event types match `^state\.(step|slice)\.[a-z_]+$` regex. All 14 live in `BUILD_ONLY_EVENT_PREFIXES` (no `state.teach.*` analogs — teach-mode harness is v47 scope).

## 13 New Modules Registered

| Module | Schema Owner |
|---|---|
| `state_build/deviation/arch_patterns.py` | DEVIATION-RULES.md §5 |
| `state_build/deviation/log_deviation.py` | DEVIATION-RULES.md §3-§4 |
| `state_build/commit/trailers.py` | DEVIATION-RULES.md §5 |
| `state_build/projectors/deviation_summary.py` | DEVIATION-RULES.md §10 |
| `state_build/subagents/types.py` | SUBAGENT-MANAGEMENT.md §3 |
| `state_build/subagents/dispatch.py` | SUBAGENT-MANAGEMENT.md §2 + §5-§6 |
| `state_build/subagents/parallel_cap.py` | SUBAGENT-MANAGEMENT.md §6 |
| `state_build/subagents/returns.py` | SUBAGENT-MONITORING.md §3 |
| `state_build/subagents/spot_check.py` | SUBAGENT-MONITORING.md §4 |
| `state_build/subagents/restart.py` | SUBAGENT-MONITORING.md §6 |
| `state_build/subagents/remediation_hints.py` | SUBAGENT-MONITORING.md §6 |
| `state_build/subagents/orphan_reconcile.py` | SUBAGENT-MONITORING.md §7 |
| `state_build/subagents/autonomy.py` | SUBAGENT-MONITORING.md §8 |

Plus one projector-generated artifact: `stepNSUMMARY.md` `## Deviations` section (DEVIATION-RULES.md §10) and one Phase-402 Pydantic extension: `CompactionSnapshot` gains `subagent_restart_counters: dict[str, int]` + `in_flight_subagents: list[InFlightSubagent]` (SUBAGENT-MONITORING.md §7).

## 3 New SliceFrontmatter Fields Registered

| Field | Type | Owning REQ |
|---|---|---|
| `autonomy` | `Literal["tiered","full-yolo","conservative"] \| None` | DEV-06 → DEVIATION-RULES.md §6 |
| `allowed_subagents` | `list[SubagentType] \| None` | SUB-03 → SUBAGENT-MANAGEMENT.md §5 |
| `subagent` | `SubagentSliceConfig \| None` (nested: parallel_cap, progress_timeout_s, remediation_hints) | SUB-04 + SUB-07 → SUBAGENT-MANAGEMENT.md §6 + SUBAGENT-MONITORING.md §5 |

## Line-Count Deltas

| File | Before | After | Delta |
|---|---:|---:|---:|
| EVENT-TAXONOMY.md | 348 | 391 | +43 |
| ARTIFACT-CATALOG.md | 849 | 893 | +44 |
| FRONTMATTER-SCHEMAS.md | 303 | 343 | +40 |
| **Total** | **1500** | **1627** | **+127** |

All three files exceed plan-mandated line-count floors (≥360, ≥870, ≥230 respectively).

## Append-Only Invariant Verification

`git diff 2162387..HEAD --stat` against the worktree base produced:

```
.../v40/phases/400/specs/EVENT-TAXONOMY.md       | 43 +++++++++++++++++++++
.../v40/phases/400/specs/FRONTMATTER-SCHEMAS.md  | 40 ++++++++++++++++++++
.../v40/phases/401/specs/ARTIFACT-CATALOG.md     | 44 ++++++++++++++++++++++
3 files changed, 127 insertions(+)
```

**Zero deletions.** Phase 402, Phase 403 (Step-Tier), and Phase 404 amendment blocks in EVENT-TAXONOMY.md are byte-identical to the pre-state. Phase 402 and Phase 404 amendments in ARTIFACT-CATALOG.md are byte-identical. FRONTMATTER-SCHEMAS.md v40 contract closing line is byte-identical (no prior v41 amendments existed in this file).

## Naming-Discipline Verification

`awk '/## v41 Amendment — Phase 405/,0' <each-file> | grep -cE '\bGSD-'` returned **0** for all three amended files. No `GSD-` literal in any Phase 405 amendment block. STATE-* trailer cross-reference rendered in EVENT-TAXONOMY.md amendment block (STATE-Task / STATE-DeviationRule / STATE-DeviationAttempt / STATE-Subagent-Invocation per DEVIATION-RULES.md §5).

Pre-existing `GSD-` literals in v40 files: zero (audited at plan start). The plan's threat-model note about a deferred past-phase GSD-rename pass remains scoped to other files, not these three.

## Deviations from Plan

None — plan executed exactly as written. Both tasks landed as specified.

### Observation (not a deviation): Plan verify-block regex did not match existing Phase 402/403 amendment headers

The plan's Task-1 verify block included `grep -qE "^## v41 Amendment — Phase 402"` and `^## v41 Amendment — Phase 403`. The existing EVENT-TAXONOMY.md headings are literally `## v41 Amendment` (no Phase suffix; line 199 — this is the Phase 402 amendment, identified by its body content) and `## v41 Amendment — Step-Tier Event Family Extension` (line 239 — Phase 403). The Phase 404 amendment header (`## v41 Amendment — Phase 404 Discipline-Guard Event Family` at line 285) does match the planned regex.

This is a **pre-existing inconsistency in the v40 file's amendment-heading convention** — not a deviation introduced by this plan and not in scope to fix (append-only invariant). The actually-load-bearing invariant — "prior amendment blocks unchanged" — was verified rigorously via `git diff --stat` showing 0 deletions. The plan-level overall verification block (line 519+) which uses the same `^## v41 Amendment — Phase 402/403` regex would similarly false-negative on this file, but that does not impact correctness. Recommended follow-up: a low-priority retrofit pass to standardize the Phase 402/403 amendment-header convention in EVENT-TAXONOMY.md to match Phase 404+405's shape (`## v41 Amendment — Phase N <subtitle>`). Logging as advisory only — not blocking.

## Quality Gates

**Quality Level:** standard (config `quality.level=high` → treated as standard for sentinel; tighter than `fast`, lighter than `strict`)

| Task | Gate | Outcome | Detail |
|---|---|---|---|
| 1 | codebase_scan | passed | Phase 404 Plan-04 precedent located; existing amendment headers grepped; tail-20 baseline read |
| 1 | context7_lookup | skipped | N/A — markdown amendment only, no external library dependencies |
| 1 | test_baseline | skipped | N/A — quality.test_exemptions covers `.planning/**` (markdown amendments) |
| 1 | test_gate | skipped | N/A — markdown amendment, no new exported logic (test_exemptions match) |
| 1 | diff_review | passed | Clean diff: pure append; 43 insertions, 0 deletions; no TODO/FIXME; no name conflicts |
| 2 | codebase_scan | passed | Last-line of ARTIFACT-CATALOG and FRONTMATTER-SCHEMAS read; Wave 1 spec module paths cross-validated |
| 2 | context7_lookup | skipped | N/A — markdown amendments only |
| 2 | test_gate | skipped | N/A — `.planning/**` exemption |
| 2 | diff_review | passed | Clean diff: pure append; 84 insertions, 0 deletions; all 13 module paths + 3 SliceFrontmatter fields render; no name conflicts |

**Summary:** 9 gates ran, 4 passed, 0 warned, 5 skipped, 0 blocked.

## Issues Encountered

**Worktree base mismatch at start** — `git merge-base HEAD <expected-base>` returned `1e678d8b6...` (a v13-milestone commit) instead of the expected `876ce920...`. `git reset --soft 876ce920` correctly moved HEAD; `git stash --include-untracked` was used to clean the working tree to match the new HEAD. This was a worktree-state quirk (likely from a stale worktree restoration), not a planning error. After cleanup the working tree was clean and HEAD pointed at the expected base commit `876ce920` (= `2162387` per `git log --oneline`). All subsequent commits chained from this base correctly.

No other issues encountered. No checkpoints triggered. No deviations of any kind.

## Self-Check

**Files created/modified verification:**

- FOUND: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (391 lines, Phase 405 amendment present)
- FOUND: `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` (893 lines, Phase 405 amendment present)
- FOUND: `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` (343 lines, Phase 405 amendment present)
- FOUND: `.planning/milestones/v41/phases/405/04-event-amendments-SUMMARY.md` (this file)

**Commit verification:**

- FOUND: 74b58d6 (Task 1 — EVENT-TAXONOMY.md amendment)
- FOUND: 00c34a0 (Task 2 — ARTIFACT-CATALOG.md + FRONTMATTER-SCHEMAS.md amendments)

## Self-Check: PASSED
