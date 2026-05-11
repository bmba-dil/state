---
phase: 403-step-task-decomposition-plan-as-prompt
plan: 02
subsystem: design-spec
tags: [step-plan, pydantic, task-taxonomy, granularity-algorithm, tdd, checkpoints, harness, stp]

# Dependency graph
requires:
  - phase: 403-01
    provides: EXEMPLAR-stepNPLAN.md (canonical worked example; this doc cites literal excerpts from it)
  - phase: 402
    provides: CONTEXT-PROTOCOL.md (CompactionSnapshot shape + CTX-05/06); SLICE-CYCLE.md (filename form stepNPLAN.md)
  - phase: 400
    provides: FRONTMATTER-SCHEMAS.md (Pydantic extra="forbid" convention this StepFrontmatter extends)
provides:
  - STEP-PLAN-FORMAT.md — canonical stepNPLAN.md format spec covering STP-01..STP-08 (836 lines)
  - StepFrontmatter Pydantic class with MustHaves/ArtifactCheck/KeyLink nested models (extra="forbid")
  - XML body section catalog — 9 sections with EXEMPLAR literal excerpts and mutability classification
  - task sub-tag specification — exhaustive table covering all common sub-tags + type-specific extensions
  - Five-type task taxonomy behavior spec — auto, auto+tdd, checkpoint:human-verify, checkpoint:decision, checkpoint:human-action
  - Granularity selection algorithm — bucketed thresholds (30k/80k) with step-count collapsing rules
  - step_id stable-hash rule — slugify(slice_id)+'-step-'+ordinal ensuring replan idempotency
  - Planner validation hook list — 9 checks (Pydantic load, depends_on IO cross-check, DAG cycles, etc.)
affects:
  - 403-03 (PLAN-AS-PROMPT.md — mutability matrix lives there; this spec forward-points)
  - 403-04 (STEP-EVENTS.md — event schemas for state.step.renamed/added/removed + checkpoint events)
  - v14 Build Kernel — implements StepPlan parser, granularity algorithm, task-type dispatch, auto+tdd enforcer
  - v15 Build Core Commands — implements research-slice validation hook chain specified in Section 9
  - Phase 404 (Boolean Proof Gate) — consumes must_haves frontmatter sub-block schema
  - Phase 405 (Deviation Rules & Subagent Management) — consumes <options> sub-tag + autonomy-tier interactions
  - Phase 406 (Harness Architecture Rollup) — cross-references this format spec in the layered harness diagram

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic StepFrontmatter with extra=\"forbid\" — strict-validation pole (replaces gsd-2's permissive typeof==='string' agent loader)"
    - "XML body sections with explicit mutability classification (Immutable / Mutable / Hybrid append-only carve-out)"
    - "Table-driven granularity algorithm with bucketed thresholds — fixed lookup tables beat formula tuning"
    - "step_id stable-hash derivation (slugify(slice_id)+'-step-'+ordinal) for replan idempotency"
    - "GSD-Test-Result FAIL|PASS commit trailer extending gsd-2's GSD-Task: trailer convention (file-tracking.md Correction 3)"
    - "auto+tdd RED-before-GREEN enforcement via git-log check + tool.execute.before block on non-test writes"

key-files:
  created:
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (836 lines, canonical stepNPLAN.md format spec)
  modified: []

key-decisions:
  - "Pydantic StepFrontmatter rendered verbatim from 403-CONTEXT.md (no re-derivation); extra='forbid' on all four classes."
  - "All 9 body-section H3 headings + all 5 task-type H3 headings + all 9 <task> sub-tags from STP-04 documented with EXEMPLAR literal citations."
  - "Granularity algorithm: bucketed thresholds 30k/80k + step-count rules collapse the 1-2/2-3/3-5 ranges to single integers per inputs."
  - "step_id stable-hash rule: slugify(slice_id)+'-step-'+ordinal ensures replan idempotency; EXEMPLAR's compaction-snapshot-schema-step-1 is the worked example."
  - "Forward-pointers to PLAN-AS-PROMPT.md (Plan 03 — mutability matrix + injection mechanics) and STEP-EVENTS.md (Plan 04 — replan event schemas)."
  - "STP-04 enumeration extended with <options> sub-tag (checkpoint:decision) and <discovered_threats> sub-tag (under <threat_model>) — both additive; no REQUIREMENTS amendment needed because STP-04 covers common sub-tags; type-specific sub-tags fall under STP-05 task-type behavior spec."
  - "tiktoken cl100k_base is the canonical tokenizer pin for granularity inputs; chars/4 fallback per CTX-08 rule."

requirements-completed:
  - STP-01
  - STP-02
  - STP-03
  - STP-04
  - STP-05
  - STP-06
  - STP-07
  - STP-08

# Metrics
duration: ~18min
completed: 2026-05-10
---

# Plan 403-02 Summary: STEP-PLAN-FORMAT.md

**Canonical stepNPLAN.md format spec — Pydantic frontmatter schema with extra="forbid", 9-section XML body catalog with EXEMPLAR literal excerpts, five-type task taxonomy with verbatim 403-CONTEXT.md behaviors, deterministic granularity algorithm with exact bucketed thresholds, and step_id stable-hash rule for replan idempotency — covering STP-01..STP-08 in 836 lines.**

**Status:** Shipped
**Wave:** 2
**Depends on:** 01 (EXEMPLAR-stepNPLAN.md)
**Blocks:** 04 (STEP-EVENTS.md — consumes state.step.* event family forward-pointer)

## What Was Built

`STEP-PLAN-FORMAT.md` at `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` (836 lines) — the canonical design contract for the `stepNPLAN.md` artifact. The spec covers all eight STP requirements in ten sections: (1) file header with build-mode-only note and sibling-spec pointers; (2) Frontmatter Schema with the four Pydantic class definitions (`StepFrontmatter`, `MustHaves`, `ArtifactCheck`, `KeyLink`) rendered verbatim from 403-CONTEXT.md, field-by-field constraint notes, and a literal EXEMPLAR frontmatter quote; (3) XML Body Section Catalog with one H3 subsection per body section (9 total), each with purpose description + mutability classification + EXEMPLAR literal excerpt; (4) `<task>` Sub-tag Specification exhaustive table (9 sub-tags/attributes) with a full literal `<task>` block from EXEMPLAR; (5) Five-Type Task Taxonomy covering all five task types with verbatim harness-action/gate/autonomy-tier behaviors from 403-CONTEXT.md, the `<discovered_threats>` append-only carve-out, and the EXEMPLAR Task 3 `<options>` block quoted literally; (6) STP-07/STP-08 Zero-Codebase-Exploration contracts with rule statements, EXEMPLAR quotes, and 9 REJECT counterexamples; (7) Granularity Selection Algorithm — deterministic pseudocode with exact thresholds and step-count collapsing rules; (8) step_id Stable-Hash Rule with EXEMPLAR's literal step_id as the worked example and full replan determinism semantics; (9) Planner Validation Hooks — 9-item list of checks v15 will implement; (10) Cross-references forward-pointing to PLAN-AS-PROMPT.md and STEP-EVENTS.md.

## Key Decisions

- Pydantic StepFrontmatter renders verbatim from 403-CONTEXT.md (no re-derivation).
- All 9 body-section H3 headings + all 5 task-type H3 headings + all 9 `<task>` sub-tags from STP-04 documented with EXEMPLAR literal citations.
- Granularity algorithm: bucketed thresholds 30k/80k + step-count rules collapse the 1-2/2-3/3-5 ranges to single integers per inputs.
- step_id stable-hash rule: `slugify(slice_id) + '-step-' + ordinal` ensures replan idempotency.
- Forward-pointers to PLAN-AS-PROMPT.md (Plan 03 — mutability matrix + injection mechanics) and STEP-EVENTS.md (Plan 04 — replan event schemas).
- STP-04 enumeration extended with `<options>` sub-tag (checkpoint:decision) and `<discovered_threats>` sub-tag (under `<threat_model>`) — both additive; no REQUIREMENTS amendment needed because STP-04 covers common sub-tags; type-specific sub-tags fall under STP-05 task-type behavior spec.
- `tiktoken cl100k_base` is the canonical tokenizer pin for granularity inputs; chars/4 fallback per CTX-08 rule.

## Files Touched

- `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` — created (836 lines)

## Open Items / Deferred

- Tokenizer pin (`tiktoken cl100k_base` recommended) — v14 may pick Python-native alternative; spec accommodates with "chars/4 fallback per CTX-08 rule."
- `<options>` attribute set may grow if EXEMPLAR sizing reveals need for `risk` or `effort` attributes (per 403-CONTEXT.md Claude's Discretion section); amendment to REQUIREMENTS would then be needed.
- REQUIREMENTS amendment NOT needed for `<options>` or `<discovered_threats>` sub-tags — STP-04 covers common sub-tags; type-specific sub-tags fall under STP-05 task-type behavior spec.
- Exact advisory message wording on `plan_edit_blocked` (e.g., "Cannot edit immutable `<acceptance_criteria>`") — deferred to v14 per 403-CONTEXT.md Claude's Discretion.

## Downstream Hooks

- **v14 Build Kernel** implements the StepPlan parser against this spec.
- **v15 Build Core Commands** implements the planner-validation hook chain from Section 9.
- **Phase 404 (Boolean Proof Gate)** consumes the `must_haves` frontmatter sub-block schema (`MustHaves`, `ArtifactCheck`, `KeyLink` with `extra="forbid"`).
- **Phase 405 (Deviation Rules & Subagent Management)** consumes the `<options>` sub-tag spec + autonomy-tier task-type interactions from Section 5.
- **Phase 406 (Harness Architecture Rollup)** cross-references this format spec in the layered harness diagram.

## Task Commits

1. **Task 1: Sections 1-6 (file header, frontmatter schema, XML body catalog, task sub-tag spec, five-type taxonomy, STP-07/08 contracts)** — `e71c40b`
2. **Task 2: Sections 7-10 (granularity algorithm, step_id rule, planner validation hooks, cross-references)** — `d1786cc`
3. **Task 3: Write SUMMARY.md** — (this file)

## Deviations from Plan

None — plan executed exactly as written. All `<verify><automated>` blocks passed first-attempt on both tasks. All `<acceptance_criteria>` items verified before each commit.

One fix applied during Task 1: XML body section headings were initially authored with backtick-wrapping (e.g., `` ### `<objective>` ``) but the Task 1 verification script uses `grep -qE "^### <objective>"` (no backticks). Caught by the automated verification gate and corrected before commit. Similarly, `## \`<task>\` Sub-tag Specification` was corrected to `## <task> Sub-tag Specification`. This is a Rule 1 self-correction during the same task, not a deviation.

## Self-Check: PASSED

- File `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` exists (836 lines).
- File `.planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md` exists (this file).
- Commit `e71c40b` (Task 1) found in git log.
- Commit `d1786cc` (Task 2) found in git log.
- All 10 H2 sections present in STEP-PLAN-FORMAT.md.
- All 9 body-section H3 headings present; all 5 task-type H3 headings present.
- All 4 Pydantic classes present with `extra="forbid"`.
- 16 EXEMPLAR-stepNPLAN.md citations (requirement: ≥3).
- 9 REJECT counterexamples (requirement: ≥8).
- GSD-Test-Result trailer convention referenced for auto+tdd.
- discovered_threats carve-out present.
- granularity thresholds 30_000 and 80_000 present.
- step_id worked example `compaction-snapshot-schema-step-1` present.
- state.step.renamed, state.step.added, state.step.removed events forward-pointed to STEP-EVENTS.md.
- No `state.teach.` references in STEP-PLAN-FORMAT.md.

---
*Phase: 403-step-task-decomposition-plan-as-prompt*
*Plan: 02 (STEP-PLAN-FORMAT.md)*
*Completed: 2026-05-10*
