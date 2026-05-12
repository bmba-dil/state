---
phase: 403
plan: "01"
subsystem: design-spec
tags: [v41, step-plan, exemplar, design-only, spec]
requirements_satisfied: [STP-01, STP-02, STP-03, STP-04, STP-05, STP-06, STP-07, STP-08, PAP-01, PAP-03, PAP-06]
provides:
  - exemplar_stepnplan_worked_example
  - canonical_gsd_shape_contract
  - parser_test_fixture_for_v14
key_files_created:
  - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
key_files_modified: []
commits:
  - 06580d1
duration_minutes: ~30
completed: 2026-05-10
---

# Plan 403-01 Summary: EXEMPLAR-stepNPLAN.md

**Status:** Shipped
**Completed:** 2026-05-10
**Wave:** 1
**Depends on:** none
**Blocks:** 403-02 (STEP-PLAN-FORMAT.md), 403-03 (PLAN-AS-PROMPT.md)

Authored the canonical worked example at
`.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` (327 lines),
establishing the GSD-shape contract for v14 Build Kernel Step plans. The file uses a
realistic notional Step — "Implement CompactionSnapshot Pydantic model" — from the
`compaction-snapshot-schema` Slice of v14 Build Kernel Phase 1.

## What Was Built

A single 327-line markdown file at
`.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` serving as the
canonical "GSD-shape demonstration plan" required by STP-03 success criterion 2. The
subject — the `CompactionSnapshot` Pydantic model — is drawn from
CONTEXT-PROTOCOL.md §5 (CTX-05/CTX-06) and is concrete enough to exercise every
section of the stepNPLAN.md format:

- **Full YAML frontmatter** validated against `StepFrontmatter` schema: `phase`,
  `slice`, `step`, `type` (`"auto+tdd"`), `wave`, `depends_on`, `files_modified`,
  `autonomous`, `requirements`, and a fully populated `must_haves` block with all
  three sub-blocks (`truths`, `artifacts`, `key_links`).
- **All 9 XML body sections** in canonical order: `<objective>`, `<execution_context>`,
  `<context>`, `<interfaces>`, `<tasks>`, `<threat_model>`, `<verification>`,
  `<success_criteria>`, `<output>`.
- **Three task types** demonstrated in `<tasks>`:
  - `auto+tdd` (Task 1) — RED-before-GREEN with `STATE-Test-Result: FAIL` commit trailer.
  - `auto` (Task 2) — GREEN implementation with `STATE-Test-Result: PASS` commit trailer.
  - `checkpoint:decision` (Task 3) — `<options>` sub-tag with 2 named options
    (`OPT_NAIVE_UTC`, `OPT_UTC_Z`) each carrying `pros` and `cons` attributes.
- **STP-07 compliant `<interfaces>` block** with two LITERAL upstream excerpts:
  `EventEnvelope` from `src/state_core/schema.py` (lines 239-265) and
  `CompactionSnapshot` from CONTEXT-PROTOCOL.md §5.
- **STP-08 compliant `<read_first>` entries** in every task — each cites an exact file
  path plus line range (e.g., `tests/conftest.py lines 1-40`); no unscoped paths.
- **PAP-05 compliant `<discovered_threats>`** — shipped empty with the
  `<!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->`
  comment, locking the append-only semantic.

## Key Decisions

- **Subject chosen:** CompactionSnapshot Pydantic model — matches 403-CONTEXT.md
  recommendation; concrete, plausibly v14, exercises every required section.
- **`step_id` form:** `compaction-snapshot-schema-step-1` — follows the
  `slugify(slice_id) + "-step-" + ordinal` rule from 403-CONTEXT.md Granularity
  §step_id; stable across replans with identical inputs.
- **Task 3 uses 2 options** (OPT_NAIVE_UTC, OPT_UTC_Z) — meets the 2–4 named-options
  floor specified in 403-CONTEXT.md; `pros`/`cons` attributes used literally per the
  `<decisions>` Task-type behaviors subsection. First option (OPT_NAIVE_UTC) is the
  CONTEXT-PROTOCOL.md canonical pin, so `--full-yolo` deterministic pick is also the
  correct pick.
- **`<discovered_threats>` shipped empty** with the runtime-only-append comment —
  locks the PAP-05 carve-out semantic at authoring time so Plan 03 (PLAN-AS-PROMPT.md)
  can reference it as the canonical demonstration.
- **Frontmatter `requirements` field tags only CTX-05/CTX-06** — the EXEMPLAR's actual
  requirements. STP/PAP traceability for Plan 01 is covered by Plan 01's own PLAN.md
  frontmatter, not re-declared in the EXEMPLAR (which is a notional v14 artifact, not
  a Phase 403 planning artifact).

## Files Touched

| File | Action | Lines |
|------|--------|-------|
| `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` | Created | 327 |

## Open Items / Deferred

- `<options>` attribute set may grow if Plan 02/03 sizing reveals a need for `risk` or
  `effort` attributes (per 403-CONTEXT.md Claude's Discretion). v14 implementations
  should treat the current attribute set (`name`, `pros`, `cons`) as the v1 contract.
- Token cap for `@`-resolved inlines (recommended 30k) is not numerically pinned in
  this EXEMPLAR; Plan 03 (PLAN-AS-PROMPT.md) finalizes the exact value. The EXEMPLAR's
  `<context>` block uses 5 `@`-references as representative size.

## Downstream Hooks

- **STEP-PLAN-FORMAT.md (Plan 02)** will quote literal excerpts from this EXEMPLAR for
  STP-03 success criterion 2 — "every XML body section AND every `<task>` sub-tag is
  documented with at least one literal example excerpt from the GSD-shape demonstration
  plan." Every section in this file is a potential citation source.
- **PLAN-AS-PROMPT.md (Plan 03)** will reference the EXEMPLAR for the content-stripping
  rule demonstration (PAP-06) and the `@`-reference resolution example (PAP-02). The
  EXEMPLAR's `<execution_context>` block and `<context>` block are the canonical
  demonstration targets.
- **STEP-EVENTS.md (Plan 04)** will reference the `<options>` sub-tag shape for the
  `checkpoint_auto_resolved` event payload schema — specifically the `selection` field
  set to one of the `option name` attribute values.
- **v14 Build Kernel** uses this file as a parser test fixture: the StepPlan parser must
  round-trip EXEMPLAR-stepNPLAN.md byte-for-byte (frontmatter parses as valid YAML;
  XML body sections parse with the correct tag/attribute structure).
