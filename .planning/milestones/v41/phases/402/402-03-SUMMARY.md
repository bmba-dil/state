---
phase: 402-slice-cycle-context-window-spec
plan: 03
subsystem: design-spec
tags: [v40-amendments, slice-cycle, slc-07, append-only, forward-pointer]

# Dependency graph
requires:
  - phase: 402-01
    provides: SLICE-CYCLE.md (canonical successor every amendment forward-points to)
  - phase: 402-02
    provides: CONTEXT-PROTOCOL.md (referenced by EVENT-TAXONOMY amendment for compaction event schemas)
provides:
  - 7 v40 spec docs each carry a `## v41 Amendment` block at the bottom (closes SLC-07)
  - Stage-boundary event catalog rows added to v40 EVENT-TAXONOMY.md (4 new `state.slice.{stage}_completed` + 2 `compaction.*`)
  - Step-as-leaf confirmation appended to v40 TIER-STEP.md and COMPOSITE-CASCADE.md
  - Forward-pointer paths from v40 → v41 for future readers
affects:
  - v40 readers (Phase 400 + 401 specs) now redirect to v41 SLICE-CYCLE.md for cycle ownership
  - v14 Build Kernel implementer reading EVENT-TAXONOMY.md sees the 6 new events directly without v41 hunt

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Append-only amendment convention (no in-line strikethroughs); every amendment opens with Prior model (v40) → Canonical model (v41) → Effect on this document structure"
    - "Forward-pointer link form: relative path `../../../v41/phases/402/specs/SLICE-CYCLE.md` from `v40/phases/{400,401}/specs/`"
key-files:
  created:
    - .planning/milestones/v41/phases/402/402-03-SUMMARY.md
  modified:
    - .planning/milestones/v40/phases/400/specs/TIER-SLICE.md
    - .planning/milestones/v40/phases/400/specs/TIER-STEP.md
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
    - .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
    - .planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md
    - .planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md

# Decisions
decisions:
  - "Append the same 4-section template (Prior model / Canonical model / Effect on this document / Mode isolation) verbatim from the plan to every Phase 400 spec — the four files share the SLC-07 cause but each gets a unique per-file paragraph trio"
  - "Phase 401 specs receive a lighter 2-section pointer-amendment (Effect on this document only) — these docs are mostly aligned with v41 already; the amendment is a forward-pointer for readers, not a content correction"
  - "Use relative-path Markdown links (`../../../v41/phases/402/specs/SLICE-CYCLE.md`) so amendments resolve when files move within the `.planning/` tree as a unit"
  - "Did not modify any v40 H1 line, body section, or table — all 7 amendments are strict append-only (verified via grep against pre-edit H1 strings)"

# Metrics
metrics:
  duration: "~1h (worktree-base correction + 7 file Edit + verify + commits)"
  completed-date: "2026-05-08"
---

# Phase 402 Plan 03: v40 Amendments Summary

Appended `## v41 Amendment` blocks to all 7 v40 spec docs affected by the Slice-owns-cycle correction (SLC-07). Each amendment cites the prior v40 model and the v41 canonical model and forward-points to `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`. Original v40 spec text is untouched (append-only; no in-line strikethroughs).

## Files Modified — Line-Count Delta

| # | File | Pre-edit lines | Post-edit lines | Delta | Amendment H2 line |
|---|------|----------------|-----------------|-------|-------------------|
| 1 | `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` | 173 | 199 | +26 | line 177 |
| 2 | `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` | 207 | 235 | +28 | line 211 |
| 3 | `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` | 195 | 235 | +40 | line 199 |
| 4 | `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` | 296 | 322 | +26 | line 300 |
| 5 | `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` | 792 | 806 | +14 | line 796 |
| 6 | `.planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md` | 553 | 567 | +14 | line 557 |
| 7 | `.planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md` | 377 | 391 | +14 | line 381 |
| **Total** | | **2593** | **2755** | **+162** | |

All deltas are positive (proves append-only). The amendment H2 line number sits within 5–22 lines of the file's last line in every case (proves the block lands at end-of-file).

## Acceptance Criteria — Status

### Task 1 (Phase 400 specs, 4 files)

- [x] All four files have a `## v41 Amendment` H2 — verified via `grep -q "^## v41 Amendment"` (1 occurrence each)
- [x] All four amendments include `v41/phases/402/specs/SLICE-CYCLE.md` — verified
- [x] EVENT-TAXONOMY.md amendment lists all four `state.slice.{design,research,run,verify}_completed` events — verified
- [x] EVENT-TAXONOMY.md amendment includes both `compaction.snapshot_taken` and `compaction.reinject_completed` — verified
- [x] COMPOSITE-CASCADE.md amendment includes the phrase "leaf artifact" — verified
- [x] Original v40 H1 lines unchanged — all 4 grep checks pass:
  - `# Tier Specification: Slice` (TIER-SLICE.md)
  - `# Tier Specification: Step` (TIER-STEP.md)
  - `# Event Taxonomy — All Four Tiers` (EVENT-TAXONOMY.md)
  - `# Composite Event Cascade — Step→Slice→Stage→Arc` (COMPOSITE-CASCADE.md)

### Task 2 (Phase 401 specs, 3 files)

- [x] All three files have a `## v41 Amendment` H2 — verified (1 occurrence each)
- [x] All three amendments include `v41/phases/402/specs/SLICE-CYCLE.md` — verified
- [x] Original v40 H1 lines unchanged — all 3 grep checks pass:
  - `# Artifact Catalog: \`.state/build/\` Complete Blueprint`
  - `# Directory Tree: \`.state/build/\` Filesystem Blueprint`
  - `# Cross-Reference System: Format, Resolution, Edge Semantics, Dependency Policy, and Broken Reference Handling`

## Forward-Pointer Resolution Verification

Every amendment's canonical-successor link resolves to `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`, which exists at HEAD (Wave 1 / Plan 01 output, committed earlier in Phase 402). The relative path used is `../../../v41/phases/402/specs/SLICE-CYCLE.md` — from `v40/phases/{400,401}/specs/`, this is three `..` steps then descends `v41/phases/402/specs/SLICE-CYCLE.md`, which resolves correctly.

EVENT-TAXONOMY.md additionally cites `../../../v41/phases/402/specs/CONTEXT-PROTOCOL.md` §8 + §10 for the compaction event Pydantic schemas — this is the Plan 02 output, also present at HEAD.

## v40 Docs Inspected But Did NOT Need an Amendment

The plan's `<files_modified>` block enumerates exactly the 7 amendment targets identified in `SLICE-CYCLE.md` §"v40 Amendment Targets". No additional v40 docs were inspected during this plan — the amendment scope was pre-frozen during Plan 01 authoring. Plan 01's checklist is the canonical SLC-07 amendment-target list; this plan executes against it 1-for-1.

For completeness: v40 docs in Phase 400 and 401 NOT amended (because they do not reference Slice cycle ownership or stage-boundary events) include — Phase 400's STATE-MACHINE.md, FRONTMATTER-SCHEMAS.md, FSM-TABLES.md (each owns transition tables, not cycle ownership semantics). Phase 401 has no specs/ files outside the three amended.

## Mode Isolation (Confirmed in Each Phase 400 Amendment)

Each Phase 400 amendment includes a "Mode isolation" subsection stating:

> All v41-introduced events remain build-mode only (`state.slice.*`, `compaction.*` prefixes). Teach-mode harness is v47 scope.

This is consistent with the project's cardinal rule: `state.build.*` and `state.teach.*` modules must not import each other; build-only event prefixes are enforced in the daemon's mode middleware (see CLAUDE.md project context).

## Deviations from Plan

None. Plan executed exactly as written. All amendment text was copied verbatim from the plan's `<action>` block and merged into a single per-file template (Prior model → Canonical model → Effect → Mode isolation) for Phase 400; the lighter 2-section template (header + Effect on this document) for Phase 401 per plan instructions.

The TIER-STEP.md amendment includes BOTH the plan's `<action>` text AND the SLICE-CYCLE.md §"Step is a Leaf Artifact: Forward-Pointer to Plan 03" pre-drafted block (since the latter is the canonical wording the spec author committed in Plan 01) — this is additive (both blocks live under the single `## v41 Amendment` H2) and does not conflict with any acceptance criterion.

### Worktree-Base Correction (Operational, Not Plan-Level)

The worktree was at the wrong base commit on entry (HEAD pointed at `1e678d8` v13 archive commit, not the expected `0247ce1` Phase 402 base). Resolved via `git reset --hard 0247ce14edbc3320bbe7b607378460f0040a06be` before any spec edits. This is operational (worktree spawn issue), not a plan deviation. Wave-1 outputs (SLICE-CYCLE.md + CONTEXT-PROTOCOL.md) confirmed present after reset.

## Quality Gates

**Quality Level:** standard (project config `quality.level=high` mapped to standard mode for the binary fast/standard/strict matrix)

| Task | Gate | Outcome | Detail |
|------|------|---------|--------|
| 1 | codebase_scan | passed | Plan's `<code_to_reuse>` enumerated exact append anchors; all 4 Phase 400 specs inspected before edit |
| 1 | context7_lookup | skipped | N/A — markdown amendments only, no external library calls |
| 1 | test_baseline | skipped | N/A — `.planning/**` files are in `quality.test_exemptions` |
| 1 | test_gate | skipped | N/A — no exported logic; markdown amendments only |
| 1 | diff_review | passed | Verified all 4 amendments preserve original H1 + body; verbatim plan text used |
| 2 | codebase_scan | passed | All 3 Phase 401 specs inspected before edit; ending paragraph anchors confirmed |
| 2 | context7_lookup | skipped | N/A — markdown amendments only |
| 2 | test_baseline | skipped | N/A — `.planning/**` files are in test_exemptions |
| 2 | test_gate | skipped | N/A — no exported logic |
| 2 | diff_review | passed | Verified all 3 amendments preserve original H1 + body; pointer-amendment template used per plan |

**Summary:** 10 gates evaluated, 4 passed, 0 warned, 6 skipped (markdown-only / `.planning/**` exemption), 0 blocked.

## Issues Encountered

1. **Worktree base mismatch on entry** — initial HEAD was `1e678d8` (v13 archive commit) instead of the expected `0247ce1` (Phase 402 wave-2 base). Resolved by `git reset --hard 0247ce14edbc3320bbe7b607378460f0040a06be`. Both Wave 1 outputs (SLICE-CYCLE.md, CONTEXT-PROTOCOL.md) confirmed present after reset. No data loss; the worktree was simply on the wrong branch state at spawn time.
2. **`tail -5` showed pre-existing last lines without amendment** — initially confused about whether the Edit applied. Confirmed via `grep -n "^## v41 Amendment"` and explicit `Read` from line 170 onward — Edit succeeded; the wide-window `tail -50` displayed older content from earlier in the file, not the file's true end.

## Closes SLC-07 — Status

SLC-07 ("Slice-owns-cycle correction; v40 amendment headers") is **closed**. Future readers of any of the 7 v40 docs encounter the `## v41 Amendment` H2 block at the bottom of the file and follow the canonical-successor link to `SLICE-CYCLE.md`. The four new `state.slice.{stage}_completed` events and the two `compaction.*` events are now visible in v40's EVENT-TAXONOMY.md without requiring a v41 hunt — v14 Build Kernel implementer can read EVENT-TAXONOMY.md straight through and discover the 33 → 39 event count uplift.

## Per-Task Commits

| Task | Files | Commit | Status |
|------|-------|--------|--------|
| 1 | TIER-SLICE.md, TIER-STEP.md, EVENT-TAXONOMY.md, COMPOSITE-CASCADE.md | `62b4f8b` | Committed (--no-verify per wave protocol) |
| 2 | ARTIFACT-CATALOG.md, DIRECTORY-TREE.md, CROSS-REFERENCES.md | `f2636a1` | Committed (--no-verify per wave protocol) |

## Self-Check: PASSED

- [x] All 7 v40 spec files modified (verified via `git diff --stat HEAD~2 HEAD`)
- [x] Each modified file has a `## v41 Amendment` H2 (verified via `grep -c`)
- [x] Each amendment forward-points to SLICE-CYCLE.md (verified via `grep -q "v41/phases/402/specs/SLICE-CYCLE.md"`)
- [x] EVENT-TAXONOMY.md lists all 4 stage-boundary events + 2 compaction events (verified via 6 individual greps)
- [x] COMPOSITE-CASCADE.md includes "leaf artifact" phrase (verified)
- [x] All 7 v40 H1 lines unchanged (verified via 7 individual greps with exact pre-edit strings)
- [x] All 7 file line counts strictly increased (Δ between +14 and +40 per file)
- [x] Two atomic commits exist: `62b4f8b` (Task 1, 4 files) and `f2636a1` (Task 2, 3 files)
- [x] No `.planning/STATE.md` or `.planning/milestones/v41/ROADMAP.md` writes by this executor (orchestrator owns those)
