---
phase: 403-step-task-decomposition-plan-as-prompt
plan: 04
subsystem: design-spec
tags: [step-events, event-taxonomy, pydantic-schemas, plan-lifecycle, checkpoint-events, replan-continuity, v40-amendment]

# Dependency graph
requires:
  - phase: 403-02
    provides: STEP-PLAN-FORMAT.md (canonical format spec; defines step_id, slice_id contract; §5 checkpoint behaviors; §8 replan determinism)
  - phase: 403-03
    provides: PLAN-AS-PROMPT.md (injection + mutability spec; PlanEdit/PlanEditBlocked/StepPlanAuthored schemas already rendered in §§6-8)
provides:
  - STEP-EVENTS.md (canonical Pydantic schema spec for 9 new state.step.* event types)
  - v40 EVENT-TAXONOMY.md amended with Step-Tier Event Family Extension block (9-event forward-pointer table)
  - PAP-04 (plan_edit event schema) formally homed in STEP-EVENTS.md
  - PAP-05 (plan_edit_blocked event) formally homed in STEP-EVENTS.md
  - PAP-06 (step_plan_authored event) formally homed in STEP-EVENTS.md
  - STP-05 checkpoint event schemas (auto-resolved, human-action-pending, human-action-resolved)
  - STP-06 replan-continuity event schemas (renamed, added, removed)
affects:
  - v14 Build Kernel implementer reading STEP-EVENTS.md gets all 9 Pydantic schemas without hunting
  - v40 EVENT-TAXONOMY.md readers see the 9 new step-tier events directly via the amendment forward-pointer
  - Phase 404 (Boolean Proof Gate) gate logic references PlanEditBlocked.locked_section
  - Phase 405 (Subagent Management) checkpoint behavior references CheckpointAutoResolved.tier
  - Phase 406 (Harness Architecture Rollup) HRN-07 event-replay proof cites all 9 events

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic extra='forbid' on every event payload — schema contract enforced at parse time"
    - "Append-only event store rows — corrections are NEW events, no UPDATE/DELETE"
    - "SHA-256 hash chain for plan_edit replay — before_sha256/after_sha256 verified by projector"
    - "Append-only v40 amendment convention — distinct heading (v41 Amendment — Step-Tier Event Family Extension) avoids heading collision with Phase 402 amendment"
key-files:
  created:
    - .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
    - .planning/milestones/v41/phases/403/04-step-events-SUMMARY.md
  modified:
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md

# Decisions
decisions:
  - "Standalone STEP-EVENTS.md spec chosen over inlining all 9 events into PLAN-AS-PROMPT.md — 9 events is sufficient mass to justify a dedicated v41 doc; mirrors Phase 402 v40-amendment-with-companion-spec precedent"
  - "v40 EVENT-TAXONOMY.md amendment is purely additive — no v40 baseline events renamed or repurposed; amendment scope line states this explicitly"
  - "PlanEdit / PlanEditBlocked / StepPlanAuthored re-rendered in STEP-EVENTS.md byte-for-byte from PLAN-AS-PROMPT.md — STEP-EVENTS.md is the canonical event-spec home; PLAN-AS-PROMPT.md cross-references back"
  - "Six new schemas authored: CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved, StepRenamed, StepAdded, StepRemoved"
  - "Naming convention: every new event is state.step.{action} per v40 baseline"
  - "Mode prefix: BUILD_ONLY_EVENT_PREFIXES (state.teach.* not affected)"
  - "Deviation: plan spec min_lines: 600 for EVENT-TAXONOMY.md; actual pre-amendment file was 235 lines (Phase 402 amendment had already been committed); the append-only intent IS satisfied (all content preserved, new block at end); file grew from 235 to 281 lines"

# Metrics
metrics:
  duration: "~25 minutes"
  completed-date: "2026-05-11"
---

# Plan 403-04 Summary: STEP-EVENTS.md + v40 Amendment

**Status:** Shipped
**Wave:** 3
**Depends on:** 02 (STEP-PLAN-FORMAT.md), 03 (PLAN-AS-PROMPT.md)
**Blocks:** none (Phase 403 final plan)

Authored the canonical `STEP-EVENTS.md` specification at `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` (429 lines) with nine step-tier event Pydantic schemas covering plan-lifecycle, checkpoint, and replan-continuity events. Appended a `## v41 Amendment — Step-Tier Event Family Extension` block to v40's `EVENT-TAXONOMY.md` listing all 9 new `state.step.*` events with triggers, state transitions, owning requirement IDs, and a forward-pointer to `STEP-EVENTS.md`. Phase 403's four-plan slate is now complete: EXEMPLAR-stepNPLAN.md, STEP-PLAN-FORMAT.md, PLAN-AS-PROMPT.md, and STEP-EVENTS.md.

## What Was Built

STEP-EVENTS.md is the canonical event-spec home for all nine step-tier events introduced by Phase 403. The spec is organized into six sections: Event Family Overview (summary table of all 9 events), Conventions (EventEnvelope reference, naming rules, append-only guarantee), Plan-Lifecycle Events (PAP-04/PAP-05/PAP-06 — StepPlanAuthored, PlanEdit, PlanEditBlocked with replay-time integrity check pseudocode), Checkpoint Events (STP-05 — CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved), Replan-Continuity Events (STP-06 — StepRenamed, StepAdded, StepRemoved with lock-survival rule), and Cross-references + Closing (downstream consumer summary). A Field-Level Constraints section provides per-field validation rules for all nine schemas, and a v14 Implementation Notes section maps each event to its daemon emitter and projector reducer. The three plan-lifecycle schemas (PlanEdit, PlanEditBlocked, StepPlanAuthored) are rendered byte-for-byte from PLAN-AS-PROMPT.md — STEP-EVENTS.md wins as canonical home if there is ever a discrepancy.

The v40 EVENT-TAXONOMY.md amendment uses the heading `## v41 Amendment — Step-Tier Event Family Extension` (distinct from Phase 402's `## v41 Amendment` heading at line 199) to avoid heading collision. The amendment is strictly additive — a 9-row table plus v40-conventions compliance list and v14 implementation pointer.

## Key Decisions

- **Standalone STEP-EVENTS.md spec** chosen over inlining all 9 events into PLAN-AS-PROMPT.md — 9 events is sufficient mass to justify a dedicated v41 doc; mirrors Phase 402's v40-amendment-with-companion-spec precedent (SLICE-CYCLE.md + 7 v40 amendment blocks).
- **v40 EVENT-TAXONOMY.md amendment is purely additive** — no v40 baseline events renamed or repurposed; the amendment scope line says so explicitly ("new event types added to the step tier; v40 baseline events unchanged").
- **PlanEdit / PlanEditBlocked / StepPlanAuthored re-rendered** in STEP-EVENTS.md byte-for-byte from PLAN-AS-PROMPT.md — STEP-EVENTS.md is the canonical event-spec home; PLAN-AS-PROMPT.md cross-references back with a forward-pointer.
- **Six new schemas authored for the first time:** CheckpointAutoResolved, CheckpointHumanActionPending, CheckpointHumanActionResolved, StepRenamed, StepAdded, StepRemoved (not present in PLAN-AS-PROMPT.md or STEP-PLAN-FORMAT.md beyond narrative references).
- **Naming convention:** every new event is `state.step.{action}` per v40 EVENT-TAXONOMY.md baseline. Replan-continuity events use `slice_id` as `aggregate_id` (the Slice is the unit of replanning).
- **Mode prefix:** `BUILD_ONLY_EVENT_PREFIXES` includes `state.step.` — all 9 events are Build-only; no `state.teach.*` events introduced.
- **Field-level constraints table added** (not in plan spec) — documents per-field validation rules, ordering invariants, and pairing invariants (e.g., every `CheckpointHumanActionPending` paired with exactly one `CheckpointHumanActionResolved`). This strengthens the spec for v14 implementers.

## Files Touched

| File | Action | Lines (pre → post) |
|------|--------|---------------------|
| `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` | Created (new) | 0 → 429 |
| `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` | Append-only amendment | 235 → 281 |

## Deviations from Plan

**1. Plan spec min_lines: 600 for EVENT-TAXONOMY.md vs actual 235 lines pre-amendment**

The plan's `must_haves.artifacts` specified `min_lines: 600` for `EVENT-TAXONOMY.md`. The actual file at execution time was 235 lines (Phase 402's 40-line amendment had already been committed). The verify bash script's `wc -l "$F" | awk '{exit ($1 < 600)}'` check therefore fails on the actual file size. The underlying **intent** of the check — "verify original v40 content is preserved (append-only)" — IS satisfied: all 235 pre-amendment lines are present verbatim; the Phase 403 amendment added 46 lines at the end. This appears to be a planning error where the 600-line threshold was estimated against a hypothetical larger v40 taxonomy that may have existed before Phase 402's archival/consolidation. No in-line fix was possible (the file is correctly 281 lines; inflating it to hit 600 would add spurious content). Documented here per the plan's append-only intent.

## Open Items / Deferred

- **v14 Build Kernel** implements: projector replay-verifier (SHA-256 hash chain integrity check for `plan_edit` events), daemon emitters for all 9 event types, projection-state reducers in `state_core.projectors.step`.
- **v15 Build Core Commands** wires emitters into the research-slice pipeline (for `state.step.plan_authored`) and the execute-slice harness (for the remaining 8 event types).
- **Pydantic-roundtrip tests** of all nine schemas land with v14 implementation (design-only phase — no production code in Phase 403).
- **EXEMPLAR-stepNPLAN.md as fixture** — v14 implementation MUST use it as the canonical fixture for plan-lifecycle event tests (mutate through every Mutability Matrix row to test the enforcer).

## Downstream Hooks

- **Phase 404 (Boolean Proof Gate)** consumes `state.step.plan_edit_blocked` indirectly — the gate fails when an immutable `<verify>` block is touched (locked_section = `"<verify>"` triggers the Boolean Proof Gate error mode).
- **Phase 405 (Subagent Management)** consumes `state.step.checkpoint_*` events for autonomy-inheritance verification — the `CheckpointAutoResolved.tier` field confirms which autonomy tier resolved the checkpoint.
- **Phase 406 (Harness Architecture Rollup)** layered diagram + sequence diagram cite all 9 events; the HRN-07 event-replay reconstruction proof lists them as "must replay to rebuild harness state."
- **v14 Build Kernel** is the primary implementation consumer of all Pydantic schemas in STEP-EVENTS.md.

## Self-Check

- [x] STEP-EVENTS.md exists at `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` (429 lines, ≥350 requirement met)
- [x] All 9 Pydantic class definitions present (verified by grep)
- [x] All 9 event-type strings present in `state.step.{action}` form
- [x] `extra="forbid"` appears 12 times (≥9 requirement met)
- [x] `BUILD_ONLY_EVENT_PREFIXES` cited in Conventions and Cross-references sections
- [x] Forward-pointers to PLAN-AS-PROMPT.md (5 occurrences) and STEP-PLAN-FORMAT.md (6 occurrences) present
- [x] v40 EVENT-TAXONOMY.md H1 `# Event Taxonomy — All Four Tiers` unchanged (verified head -1)
- [x] `## v41 Amendment — Step-Tier Event Family Extension` block appended at end of EVENT-TAXONOMY.md
- [x] All 9 event names in amendment table with PAP-04/PAP-05/PAP-06/STP-05/STP-06 REQ-IDs
- [x] SUMMARY.md present and covers all required sections
- [x] Deviation documented: EVENT-TAXONOMY.md min_lines 600 vs actual 281
