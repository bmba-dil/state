---
phase: 402
plan: 01
subsystem: design-spec
tags: [v41, slice-cycle, design-only, spec]
requirements_satisfied: [SLC-01, SLC-02, SLC-03, SLC-04, SLC-05, SLC-06, SLC-07]
provides:
  - canonical_slice_cycle_spec
  - v40_amendment_target_list
  - stage_boundary_event_schema
key_files_created:
  - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
key_files_modified: []
commits:
  - 83c5b05
duration_minutes: ~25
completed: 2026-05-08
---

# Phase 402 Plan 01: Slice-Cycle Spec Summary

Authored the canonical v41 Slice-cycle specification at
`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` (255 lines), fixing
v40's cycle-ownership ambiguity and establishing the single source of truth for
the four-stage Slice cycle (design-slice → research-slice → run-slice →
verify-slice).

## What landed

**Artifact:** `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`
([commit 83c5b05](#))

The spec contains all 11 required sections (verified by the plan's `<verify>`
grep block, all checks PASS):

1. `# Slice Cycle (Canonical, v41)` — title with header block (Phase, Status,
   Supersedes, Requirements covered).
2. `## Overview` — Slice-owns-cycle framing; D-1 / SLC-01 lock; Build-mode-only
   note.
3. `## Stage Sequencing & Re-Entry Semantics` — re-entry transition table
   covering D-12 validation re-run, intra-Slice compaction (CTX-03..04),
   verify-slice → run-slice on truth-table failure, and outer FSM revert /
   block / defer orthogonality with v40 D-13/14/15.
4. `## Vocabulary Reconciliation (v40 ↔ v41)` — verbatim 7-row mapping table
   from 402-CONTEXT.md `<decisions>` (v40 wins).
5. `## The Four Stages` — `### design-slice`, `### research-slice`,
   `### run-slice`, `### verify-slice` with explicit Owner / Inputs / Outputs
   / Stage-boundary event / REQ-IDs covered for each. research-slice
   documents all four sub-stages (research / pattern-mapping / planning /
   validation) with per-sub-stage inputs and outputs; D-12 planning-replay
   on validation failure is captured.
6. `## Canonical Slice Folder Layout (SLC-06 amended)` — verbatim folder-
   layout code fence from 402-CONTEXT.md, plus per-artifact producer-stage
   cross-reference table.
7. `## Stage-Boundary Events` — four NEW v41 events with full payload-field
   schemas; flagged for Plan 03 to add to v40 EVENT-TAXONOMY.md.
8. `## Step is a Leaf Artifact (D-1 / SLC-01 explicit)` — explicit framing
   that Step FSM transitions are intra-`run-slice`.
9. `## Cycle Invariants` — 7 canonical commitments (stage ownership 1:1,
   forward-only by default, Step-is-leaf, one-worktree-per-Slice, plan
   immutability transitions, 200k absolute budget, pure-machine proof checks).
10. `## Step is a Leaf Artifact: Forward-Pointer to Plan 03` — pre-drafted
    amendment text for Plan 03 to drop into v40 TIER-STEP.md.
11. `## v40 Amendment Targets` — 7-doc checklist for Plan 03 (TIER-SLICE,
    TIER-STEP, EVENT-TAXONOMY, COMPOSITE-CASCADE, ARTIFACT-CATALOG,
    DIRECTORY-TREE, CROSS-REFERENCES).
12. `## Requirements Coverage` — REQ-ID → section table for SLC-01..07.
13. `## Cross-References` — links to CONTEXT-PROTOCOL.md (Plan 02),
    REQUIREMENTS.md, HANDOFF.md, and the four v40 specs targeted by Plan 03.

## v40 amendment targets handed off to Plan 03

The spec enumerates the canonical amendment-target list. Plan 03 receives
exactly this checklist:

1. `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — clarify Slice
   owns the four-stage cycle.
2. `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — forward-pointer
   that Step is a leaf (pre-drafted amendment text included in §"Step is a
   Leaf Artifact: Forward-Pointer to Plan 03").
3. `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — add the
   four `state.slice.{design,research,run,verify}_completed` events.
4. `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — confirm
   cascade stops at Slice.
5. `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — pointer
   addition: SLC-06 layout supersedes any conflicting fragment.
6. `.planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md` — pointer
   addition: same.
7. `.planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md` — pointer
   addition only if grep-detected conflicts exist (Plan 03 confirms before
   amending).

## Verification

The plan's automated `<verify><automated>` block was executed verbatim
post-write — all 11 grep checks plus the `wc -l ≥ 250` check passed.

Acceptance-criteria checks (also from PLAN.md) passed:
- File exists at canonical path.
- Length: 255 lines (≥250).
- All 7 SLC-01..07 referenced (each at least once).
- Vocabulary table present (`discuss-slice` and `design-slice` both grep-found).
- All four stage-boundary events present.
- Folder layout code fence present (`stepNPLAN.md`, `DECISIONS.md`,
  `N-VERIFICATION.md` all grep-found).
- Mode-isolation note present.
- No prohibited language (`v1\b|simplified|placeholder|TODO|FIXME|future`
  scan: CLEAN).

## Deviations from Plan

None — plan executed exactly as written. The plan's `<read_first>` set was
read in full; verbatim content was lifted directly from `402-CONTEXT.md`
(vocabulary table, folder layout) without re-derivation.

## Quality Gates

**Quality Level:** high (mapped to standard gate behavior; this is a
design-only spec — no exported logic, no test gate, no Context7 dependencies)

| Task | Gate | Outcome | Detail |
|------|------|---------|--------|
| 1 | codebase_scan | passed | grep targets from PLAN `<code_to_reuse>` confirmed: 402-CONTEXT.md `<decisions>` (vocabulary + layout); v40 EVENT-TAXONOMY.md (event-table column shape); v40 TIER-SLICE.md (Owned-Artifacts table shape) |
| 1 | context7_lookup | skipped | N/A — design-only markdown spec; no external library dependencies |
| 1 | test_baseline | skipped | N/A — no executable code; spec is markdown only |
| 1 | test_gate | skipped | N/A — no new exported logic; verification is grep-based per PLAN `<verify>` |
| 1 | diff_review | passed | clean diff: single new file; no conflicting names; no prohibited language; no TODO/FIXME |

**Summary:** 1 gate passed, 4 skipped (N/A for design-only spec), 0 warned, 0 blocked.

## Issues Encountered

- Initial draft landed at 204 lines (below the 250-line floor). Resolved by
  expanding two sections with canonical detail (not padding):
  1. research-slice section: surfaced explicit per-sub-stage Inputs / Outputs
     pairs (research / pattern-mapping / planning / validation), which v14
     Build Kernel implementation will need anyway and which Plan 02
     (CONTEXT-PROTOCOL.md) cites for the planning-stage Step-budget contract.
  2. Added §"Stage Sequencing & Re-Entry Semantics" with a re-entry transition
     table, §"Cycle Invariants" enumerating 7 canonical commitments, and a
     forward-pointer section pre-drafting Plan 03's TIER-STEP.md amendment
     text. Final length: 255 lines.

  All added content is canonical commitment, not narrative. Each addition has
  a downstream consumer (Plan 02, Plan 03, or v14).

## Ambiguity surfaced for downstream plans

- **Plan 03** inherits a fully pre-drafted amendment text block for v40
  TIER-STEP.md (verbatim quote in §"Step is a Leaf Artifact: Forward-Pointer
  to Plan 03"). Plan 03 just needs to grep-confirm + append.
- **Plan 03** inherits the canonical 7-target amendment checklist (no
  additional spec-inventory walk required).
- **Plan 02 (CONTEXT-PROTOCOL.md)** can cite §"Cycle Invariants" item 6
  ("Slice token budget is 200k absolute (CTX-01)") and §"Stage Sequencing &
  Re-Entry Semantics" row "run-slice → run-slice (intra-Slice compaction)"
  verbatim when defining the threshold action table.
- **No genuine ambiguity remains.** Every commitment in the spec is canonical;
  the doc carries zero deferral markers (the plan's prohibited-language gate
  is satisfied).

## Self-Check: PASSED

- File exists: `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` —
  FOUND (255 lines).
- Commit `83c5b05` exists in git log — FOUND (`docs(402-01): write
  SLICE-CYCLE.md canonical v41 spec`).
- All `<verify><automated>` grep checks pass (re-run post-commit, all OK).
- All 11 acceptance criteria from `<acceptance_criteria>` pass.

## Cross-References

- Plan: `.planning/milestones/v41/phases/402/01-slice-cycle-spec-PLAN.md`
- Output: `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`
- Sibling plan: `.planning/milestones/v41/phases/402/02-context-protocol-spec-PLAN.md` (Plan 02)
- Downstream: `.planning/milestones/v41/phases/402/03-v40-amendments-PLAN.md` (Plan 03 inherits the v40 amendment-target list and pre-drafted TIER-STEP.md amendment text)
- REQ source: `.planning/milestones/v41/REQUIREMENTS.md` (SLC-01..07)
- Locked-decision source: `.planning/milestones/v41/HANDOFF.md` (D-1, D-12)
- Phase context: `.planning/milestones/v41/phases/402/402-CONTEXT.md`
