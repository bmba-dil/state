---
phase: 400-tier-definitions-state-machines
plan: 03
subsystem: architecture
tags: [descope, abandon, defer, blocked, decimal-insertion, state-machine, cascade]

# Dependency graph
requires:
  - phase: 400-01
    provides: "Tier definitions (ARC/STAGE/SLICE/STEP specs) and tier FSM diagrams"
  - phase: 400-02
    provides: "State transition tables (FSM-TABLES.md), composite cascade rules (COMPOSITE-CASCADE.md), pydantic frontmatter schemas (FRONTMATTER-SCHEMAS.md)"
provides:
  - "Authoritative descope and block semantics specification (DESC-SEMANTICS.md)"
  - "Abandon cascade rules per tier with edge-type-specific behavior"
  - "Deferment strategy with deferred_reason, deferred_dep, and data-edge integrity guard"
  - "Blocked state mechanics: entry conditions, no-timeout rule, unblock detection, per-tier table"
  - "Decimal insertion protocol: single-level format, 5 insertion rules, structural reorganization threshold, ID regex"
affects:
  - "Phase 401 — ART-03 immutability rules (abandoned artifacts frozen), REF-04 broken reference handling"
  - "v41+ scheduler — dependency resolution consuming abandon/defer/blocked rules"
  - "v41+ projector — cascade logic, composite state computation with blocked/deferred children"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cascade-to-blocked (never auto-abandon): abandon cascade always stops at blocked, requiring manual resolution"
    - "Defer-as-soft-done: deferred source unblocks blocks-edge dependents with informational deferred_deps flag"
    - "Data-edge integrity: data edges remain blocked when source deferred — artifacts are non-negotiable"
    - "No-timeout blocked: blocked state persists indefinitely, no scheduler-driven timeout transitions"
    - "Single-decimal insertion: decimal IDs fill integer gaps without renumbering, applied to Stage/Slice/Step"
    - "Per-tier behavior tables: each semantic concept documents tier applicability in a structured table"

key-files:
  created:
    - ".planning/milestones/v40/phases/400/specs/DESC-SEMANTICS.md"
  modified: []

key-decisions:
  - "D-13 encoded: Abandon cascade stops at blocked — no auto-abandon of dependents. User resolves manually."
  - "D-14 encoded: Deferred Slices treated as soft-done for blocks edges, remain blocked for data edges. Reactivation path via undeferred→planned."
  - "D-15 encoded: Blocked state has no timeout. Slice stays blocked indefinitely until deps resolve, user defers, or re-plans."
  - "D-16 encoded: Single decimal level (slice-12.1), no double decimals (12.1.2 rejected). No renumbering. Structural reorganization threshold is advisory."

patterns-established:
  - "Cascade summary table: structured documentation pattern showing parent→child→dependent effects per action"
  - "Decision table (Defer vs Abandon): side-by-side comparison pattern for mutually exclusive semantics"
  - "Tier-specific behavior table: pattern for documenting which tiers support a given semantic concept"
  - "Structural reorganization threshold table: decision-guidance pattern for when to insert vs. create new"

requirements-completed:
  - FSM-03
  - FSM-04
  - FSM-05

# Metrics
duration: 5min
completed: 2026-05-06
---

# Phase 400 Plan 03: Descope and Block Semantics Summary

**Abandon cascade, deferment strategy, blocked state mechanics, and decimal insertion protocol encoded as formal rules across all four tiers in DESC-SEMANTICS.md**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-06T22:17:00-05:00
- **Completed:** 2026-05-06T22:21:00-05:00
- **Tasks:** 2
- **Files created:** 1

## Accomplishments

- Created DESC-SEMANTICS.md (303 lines) — the authoritative specification for how the hierarchy handles descope, abandon, defer, blocked, and decimal insertion
- Encoded D-13 (abandon cascade): per-tier cascade rules with edge-type-specific behavior, no-auto-cascade-abandon principle, blocked_reason format
- Encoded D-14 (deferment strategy): entry conditions, blocks/soft/data edge behavior, reactivation path, Defer vs Abandon decision table
- Encoded D-15 (blocked state mechanics): 4 entry conditions, blocked_reason storage, no-timeout rule, unblock detection, tier-specific blocked behavior table
- Encoded D-16 (decimal insertion protocol): supported/prohibited formats, 5 insertion rules, applicability table, structural reorganization threshold, ID validation regex, index.json resolution

## Task Commits

Each task was committed atomically:

1. **Task 1: Specify descope, abandon, and deferment semantics** — `77da591` (feat)
2. **Task 2: Specify blocked state mechanics and decimal insertion protocol** — `37cf98f` (feat)

## Files Created/Modified

- `.planning/milestones/v40/phases/400/specs/DESC-SEMANTICS.md` — Authoritative reference for hierarchy descope, abandon, defer, blocked, and decimal insertion rules. Four major sections: Abandon Cascade (D-13), Deferment Strategy (D-14), Blocked State Mechanics (D-15/FSM-05), Decimal Insertion Protocol (D-16/FSM-04). Consumed by Phase 401 and v41+ scheduler/projector.

## Decisions Made

All decisions were pre-locked in CONTEXT.md prior to execution (D-13 through D-16). This plan encoded them as formal specification rules without introducing new decisions.

- **D-13:** Abandon cascade stops at `blocked` — no auto-cascade-abandon. Dependents must be manually resolved by the user (abandon, defer, or re-plan). Per-tier cascade table documents Slice/Stage/Arc behavior.
- **D-14:** Deferred Slices treated as soft-done for `blocks` edges, remain blocked for `data` edges. Dependents unblock with `deferred_deps` flag. Reactivation via `state.slice.undeferred → planned`.
- **D-15:** Blocked state has no timeout. Slice stays blocked indefinitely. Unblock detection is projector-driven on every child state change. Only Slice and Step tiers can be blocked; Arc and Stage are too coarse.
- **D-16:** Single decimal level supported (`slice-12.1`). Double decimals (`12.1.2`) rejected at schema validation. No renumbering — existing IDs are immutable. Structural reorganization threshold is advisory.

## Deviations from Plan

None — plan executed exactly as written. All content followed the plan's `<action>` blocks verbatim.

## Issues Encountered

None. The plan provided complete section content in the `<action>` blocks, requiring only assembly into the output file.

## User Setup Required

None — no external service configuration required. This is a design-phase specification document consumed by downstream plans and v41+ implementation.

## Next Phase Readiness

- DESC-SEMANTICS.md is complete and ready for Phase 401 consumption (ART-03 immutability rules — abandoned artifacts are frozen; REF-04 broken reference handling — references to abandoned items trigger surface-to-agent).
- All four locked decisions (D-13/D-14/D-15/D-16) are encoded as formal rules with per-tier behavior tables.
- Cross-reference links to FSM-TABLES.md, TIER-SLICE.md, and TIER-STEP.md establish traceability across Phase 400 specification documents.

---

*Phase: 400-tier-definitions-state-machines*
*Completed: 2026-05-06*
