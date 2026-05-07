---
phase: 400-tier-definitions-state-machines
plan: 01
subsystem: architecture
tags: [tier-specifications, state-machines, frontmatter, event-taxonomy, four-tier-hierarchy]

# Dependency graph
requires:
  - phase: 400-context-gathering
    provides: "Decisions D-01 through D-19, PROJECT.md constraints, REQUIREMENTS.md TIER/FSM definitions"
provides:
  - "Four standalone tier specification documents (Arc, Stage, Slice, Step) — each with role, state machine, transition table, owned artifacts, frontmatter fields, events, and cross-tier relationships"
  - "Consistent cross-tier parent-child chain: Arc→Stage→Slice→Step"
  - "D-01 Phase→Stage rename applied throughout with migration tables"
  - "D-03 discuss→design, execute→run rename applied to Step tier with migration tables"
  - "TIER-07 frontmatter field ownership classification: every field Agent or Projector, exactly once"
affects:
  - "Plan 400-02 (FSM-TABLES.md, EVENT-TAXONOMY.md, FRONTMATTER-SCHEMAS.md, COMPOSITE-CASCADE.md)"
  - "Plan 400-03 (DESC-SEMANTICS.md)"
  - "Phase 401 (artifact catalog, templates, immutability rules)"
  - "v41+ implementation (build kernel, agent harness, scheduler integration)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tier specification document structure: Role, State Machine, Transition Table, Owned Artifacts, Frontmatter Fields, Events, Cross-Tier Relationships"
    - "Dash-prefix IDs with no leading zeros: arc-{n}, stage-{n}, slice-{n}, step-{n}"
    - "Event naming convention: state.{tier}.{action}"
    - "Frontmatter field ownership: Agent vs Projector, never mixed within a field"
    - "Migration tables for renamed concepts (Phase→Stage, discussing→designing, executing→running)"

key-files:
  created:
    - .planning/milestones/v40/phases/400/specs/TIER-ARC.md
    - .planning/milestones/v40/phases/400/specs/TIER-STAGE.md
    - .planning/milestones/v40/phases/400/specs/TIER-SLICE.md
    - .planning/milestones/v40/phases/400/specs/TIER-STEP.md
  modified:
    - .planning/milestones/v40/phases/400/specs/TIER-STAGE.md (Task 3 migration table fix)

key-decisions:
  - "Arc auditing is a discrete machine state with entry guard (D-18), NOT a projector-computed composite state"
  - "Slices depend on Slices within same Stage; Stages depend on Stages within same Arc (D-10 same-parent-only)"
  - "depends_on uses 'edge' key (not 'kind') per D-12 with edge types: blocks, soft, data"
  - "Slice deferred state is soft-done: dependents unblock with deferred_dep flag (D-14)"
  - "Blocked state has NO timeout — persists indefinitely until deps resolve or user defers blocker (D-15)"

patterns-established:
  - "All tier specs follow identical 7-section structure for readability without cross-referencing"
  - "ASCII state machine diagrams for all 4 tiers with explicit transition labels and guard conditions"
  - "State transition tables with 5 columns: From, To, Event Trigger, Guard Condition, Budget Check"
  - "Event name migration tables document old→new mappings for Phase→Stage and D-03 renames"
  - "Projector-owned fields: status, *_count fields, completed_at. Agent-owned: id, title, goal, success_criteria, parent_id, depends_on"

requirements-completed:
  - TIER-01
  - TIER-02
  - TIER-03
  - TIER-04
  - TIER-05

# Metrics
duration: 55min
completed: 2026-05-07
---

# Plan 400-01: Tier Definitions & State Machines Summary

**Four standalone tier specification documents defining the Arc→Stage→Slice→Step hierarchy with complete state machines, transition tables, owned artifacts, frontmatter field classifications, event taxonomies, and cross-tier relationships — all aligned to D-01 through D-19 decisions.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-05-07T02:00:00Z
- **Completed:** 2026-05-07T02:55:43Z
- **Tasks:** 3
- **Files created:** 4 (tier specification documents)
- **Files modified:** 1 (migration table fix)

## Accomplishments

- Four standalone tier specification documents created: TIER-ARC.md (120 lines), TIER-STAGE.md (149 lines), TIER-SLICE.md (165 lines), TIER-STEP.md (201 lines) — total 635 lines
- All four tier state machines specified with ASCII diagrams, transition tables, guard conditions, and budget enforcement per D-17 (Arc≤4, Stage≤4, Slice≤4, Step≤8)
- D-01 Phase→Stage rename applied throughout all documents with migration tables documenting old→new event name mappings
- D-03 discuss→design/execute→run rename applied to Step tier with migration tables
- Cross-tier parent-child chain verified bidirectional: Arc→Stage→Slice→Step
- TIER-07 frontmatter field ownership classification: every field classified exactly once as Agent or Projector across all 4 tiers
- D-12 depends_on edge format verified: uses `edge` key (not `kind`), edge types blocks/soft/data
- D-10 same-parent-only constraint documented for Stage and Slice tiers

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Arc and Stage tier specification documents** - `5dd705a` (feat)
2. **Task 2: Create Slice and Step tier specification documents** - `7052233` (feat)
3. **Task 3: Cross-tier consistency verification** - `30a5c62` (fix)

## Files Created/Modified

- `specs/TIER-ARC.md` - Arc tier specification: role, 5-state FSM (planned→in_progress→auditing→shipped | abandoned), 4 owned artifacts, 9 frontmatter fields, 6 events, cross-tier relationships
- `specs/TIER-STAGE.md` - Stage tier specification: role with migration note, 5-state FSM (planned→in_progress→verified→shipped | abandoned), 4 owned artifacts, 10 frontmatter fields with arc_id parent ref, 6 events, event name migration table
- `specs/TIER-SLICE.md` - Slice tier specification: role as terminal container, 7-state FSM (planned→worktree_ready→in_progress→shipped | reverted | blocked | deferred), 9 owned artifacts including stepNPLAN.md flat files, 12 frontmatter fields with stage_id and deferred_reason, 10 events, decimal insertion support
- `specs/TIER-STEP.md` - Step tier specification: role as smallest unit, 8-state FSM (idle→designing→planning→running→verifying→done | blocked | abandoned), 1 owned artifact (stepNPLAN.md), 8 frontmatter fields, 11 events with D-03 rename migration table, cross-tier with no-siblings constraint

## Decisions Made

- Arc `auditing` is a discrete machine state with entry guard (all child Stages shipped per D-18), not a projector-computed composite state — resolved per RESEARCH.md Open Question Q1
- Slice `deferred` state: dependents treat deferred Slices as soft-done and proceed with `deferred_dep` flag (D-14)
- Slice `blocked` state: entered via abandon-cascade (D-13) or explicit block; no timeout per D-15
- Step `blocked→running` transition: resumes at running (not prior state) because agent must re-establish execution context
- Step `idle→planning` direct transition: agent can skip designing for simple work
- Step `verifying→running` loop: verification failure loops back for fixes, can repeat indefinitely
- D-11: Steps NOT scheduler-dispatched — run SERIALLY within single agent session; scheduler dispatches Slices

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale event names in Stage migration table**
- **Found during:** Task 3 (cross-tier consistency audit)
- **Issue:** The migration table in TIER-STAGE.md mapped `state.phase.planned` → `state.stage.planned` and `state.phase.verified` → `state.stage.verified`, but the v40 design does not have `state.stage.planned` or `state.stage.verified` events. The actual events are `state.stage.created` (creation) and `state.stage.slices_shipped` (verified transition), and `state.stage.completed` (shipped transition). The v40 design split what was a single old event into multiple new events.
- **Fix:** Updated the migration table with corrected mappings and explanatory notes about the event split. Updated class name mappings to reflect the expanded event set.
- **Files modified:** specs/TIER-STAGE.md (8 insertions, 6 deletions)
- **Verification:** grep confirmed no stale `state.stage.planned` or `state.stage.verified` event references remain
- **Committed in:** `30a5c62` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary correctness fix for downstream Plan 400-02 consumption. No scope creep.

## Issues Encountered

None — the only issue was the stale event name migration table entries, fixed as Rule 1 auto-fix.

## User Setup Required

None — no external service configuration required.

## Next Plan Readiness

- **Plan 400-02 (FSM tables, event taxonomy, pydantic schemas):** All four tier specs are ready for consumption. The FSM-TABLES.md document will formalize transition tables into a single reference. The EVENT-TAXONOMY.md will consolidate all 33 events into one catalog. The FRONTMATTER-SCHEMAS.md will derive pydantic models from the frontmatter field tables.
- **Plan 400-03 (descope/blocked/decimal semantics):** All state machines include blocked, abandoned, deferred, and reverted states with documented entry/exit conditions. Ready for formal semantics specification.
- **Phase 401 (artifact catalog):** All owned artifacts are documented per tier with schema ownership classification. Templates can be generated directly from these specs.
- **No blockers** — all three plans in Phase 400 are parallel-safe once 400-01 ships.

## Known Stubs

None — all four tier specification documents are complete. No TODO/FIXME placeholders, no hardcoded empty arrays, and no unwired data sources.

## Threat Flags

None — these are architecture specification documents, not executable code. No new network endpoints, auth paths, file access patterns, or trust boundaries introduced.

## Self-Check: PASSED

- [x] All 4 tier spec files exist and ≥80 lines: ARC (120), STAGE (149), SLICE (165), STEP (201)
- [x] All 4 tier specs contain all 7 required sections (Role, State Machine, Transition Table, Artifacts, Frontmatter, Events, Cross-Tier)
- [x] All 3 commits verified: 5dd705a (Task 1), 7052233 (Task 2), 30a5c62 (Task 3)
- [x] SUMMARY.md exists at correct path

---
*Plan: 400-01*
*Completed: 2026-05-07*
