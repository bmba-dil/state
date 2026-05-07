---
phase: 400-tier-definitions-state-machines
plan: 02
subsystem: architecture
tags: [state-machines, event-taxonomy, pydantic, frontmatter, composite-cascade, tier-definitions]

# Dependency graph
requires:
  - phase: 400-01
    provides: "Per-tier specification documents (TIER-ARC.md, TIER-STAGE.md, TIER-SLICE.md, TIER-STEP.md) defining tier roles, states, artifacts, and frontmatter fields"
provides:
  - "State transition tables for all four tiers (FSM-TABLES.md) with guard conditions and budget enforcement"
  - "Complete event taxonomy per tier (EVENT-TAXONOMY.md) with 36 events including migration notes"
  - "Composite event cascade specification (COMPOSITE-CASCADE.md) with Step→Slice→Stage→Arc rollup logic"
  - "Pydantic frontmatter schema designs (FRONTMATTER-SCHEMAS.md) with field ownership classification"
affects: [400-03, 401, artifact-catalog, descope-semantics, frontmatter-validation, scheduler, projector]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Five-column transition table format: From | To | Trigger Event | Guard Condition | Budget"
    - "Pydantic v2 ConfigDict(extra=\"forbid\") non-frozen frontmatter schema pattern with agent/projector field ownership"
    - "CQRS composite event cascade: separate append() per composite event, projector-computed states at query time"
    - "Hierarchical slash-delimited aggregate ID encoding: arc-{n}/stage-{n}/slice-{n}/step-{n}"

key-files:
  created:
    - ".planning/milestones/v40/phases/400/specs/FSM-TABLES.md"
    - ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
    - ".planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md"
    - ".planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md"
  modified: []

key-decisions:
  - "Arc has 5 discrete states (4 forward + 1 exit), auditing is a discrete machine state per D-18 not a composite state"
  - "Stage state machine split verification from completion: slices_shipped enters verified, completed enters shipped"
  - "Step budget is ≤8 total (all states counted), other tiers ≤4 forward (exit states excluded)"
  - "blocked_reason and deferred_reason are agent-owned fields — agent writes them, projector preserves but never modifies"
  - "Step frontmatter deliberately omits depends_on, worktree_dir, and slugs — Steps are leaf tier per D-04/D-11"

patterns-established:
  - "Transition table format: five columns with explicit guard conditions and budget checks"
  - "Event taxonomy per-tier tables: Event Type | Trigger | State Transition | Data Fields"
  - "Composite cascade pseudocode: on_*_done(event) → check all children → separate append()"
  - "Field ownership table: every field classified exactly once as Agent or Projector"

requirements-completed:
  - FSM-01
  - FSM-02
  - FSM-06
  - TIER-06
  - TIER-07
  - TIER-08

# Metrics
duration: 11min
completed: 2026-05-07
---

# Phase 400 Plan 02: State machine tables, event taxonomy, composite cascade, and pydantic frontmatter schemas for all four tiers

**Four specification documents encoding D-12/D-13/D-17/D-18/D-19 as formal design contracts — state transition tables with budget enforcement, 36-event taxonomy with migration maps, Step→Slice→Stage→Arc composite cascade with projector pseudocode, and pydantic v2 frontmatter schemas with agent/projector field ownership classification.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-05-07T02:59:52Z
- **Completed:** 2026-05-07T03:11:15Z
- **Tasks:** 3
- **Files created:** 4
- **Total lines:** 961 (168 + 195 + 296 + 302)

## Accomplishments

- Four transition tables (Arc 6 rows, Stage 5 rows, Slice 9 rows, Step 11 rows) with guard conditions, event triggers, and per-tier budget enforcement (FSM-01, FSM-06)
- Complete 36-event taxonomy across all four tiers — Arc (7), Stage (7), Slice (11), Step (11) — with trigger conditions, state transitions, data fields, and migration notes for Phase→Stage (D-01) and Step D-03 renames (TIER-06)
- Step→Slice→Stage→Arc composite event cascade specification with projector pseudocode, D-19 "any" vs "all" threshold tables, edge case handling (0 children), and deterministic startup rebuild logic (FSM-02)
- Four pydantic v2 frontmatter schema designs (ArcFrontmatter, StageFrontmatter, SliceFrontmatter, StepFrontmatter) with `extra="forbid"`, `Literal` status fields, and explicit agent/projector field ownership classification (TIER-07, TIER-08)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create state transition tables for all four tiers** — `d8a900b` (feat)
2. **Task 2: Create event taxonomy and composite cascade documents** — `fbf8579` (feat)
3. **Task 3: Create pydantic frontmatter schema designs** — `4abdddc` (feat)

## Files Created

- `.planning/milestones/v40/phases/400/specs/FSM-TABLES.md` — State transition tables for Arc, Stage, Slice, Step with guard conditions, event triggers, budget columns, and budget enforcement summary (168 lines)
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — Complete event taxonomy with per-tier event tables, migration summaries (Phase→Stage, Step D-03 renames), mode isolation, and event count summary (195 lines)
- `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — Cross-tier cascade specification with projector pseudocode for Step→Slice, Slice→Stage, Stage→Arc; composite state computation rules; edge case handling; startup rebuild logic (296 lines)
- `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — Pydantic v2 model designs for ArcFrontmatter, StageFrontmatter, SliceFrontmatter, StepFrontmatter with field ownership tables, cross-tier ID encoding, and threat model alignment (302 lines)

## Decisions Made

All decisions followed the plan as specified with locked decisions D-12/D-13/D-17/D-18/D-19 from CONTEXT.md. Key implementations:

- **Budget enforcement**: Exit states (abandoned, blocked, reverted, deferred) excluded from forward-state budget for Arc/Stage/Slice; Step counts all states toward ≤8 total
- **Stage event split**: verification split into `slices_shipped` (enters verified) and `completed` (enters shipped) — not a 1:1 mapping from old `state.phase.verified`
- **Reason fields**: `blocked_reason` (Slice, Step) and `deferred_reason` (Slice) classified as agent-owned — projector preserves but never modifies these fields
- **Composite events**: documented as separate `append()` operations per D-19, with deterministic projector rebuild on startup

## Deviations from Plan

None — plan executed exactly as written. All content follows the detailed specifications in the plan's action sections, patterns from 400-PATTERNS.md, and locked decisions from 400-CONTEXT.md.

## Issues Encountered

None.

## User Setup Required

None — these are design-phase specification documents only. No external services, environment variables, or runtime configuration required.

## Next Phase Readiness

All six requirements (FSM-01, FSM-02, FSM-06, TIER-06, TIER-07, TIER-08) are satisfied. The four specification documents form a complete design contract for:

- **Plan 400-03**: DESC-SEMANTICS.md references these transition tables and events for descope semantics
- **Phase 401**: ART-02 template frontmatter validation and ART-05 schema validation rules consume these pydantic models
- **v41+ runtime**: Scheduler and projector implementation consume FSM-TABLES.md, EVENT-TAXONOMY.md, COMPOSITE-CASCADE.md, and FRONTMATTER-SCHEMAS.md

No blockers. Ready for Plan 400-03 execution.

---

*Phase: 400-tier-definitions-state-machines*
*Plan: 02*
*Completed: 2026-05-07*
