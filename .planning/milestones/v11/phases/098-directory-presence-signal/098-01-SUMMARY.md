---
phase: 098-directory-presence-signal
plan: 01
subsystem: state-core
tags: [schema, subtree, mode-enforcement, directory-signal, validate_subtree_path]

# Dependency graph
requires:
  - phase: 097-state-mode-json-schema-validator
    provides: "ModeConfig model, validate_mode_config() — reused by mode_init CLI"
provides:
  - BUILD_SUBTREE/TEACH_SUBTREE canonical path constants in schema.py
  - SUBTREE_DIRS dict mapping persistable modes to subtree paths
  - validate_subtree_path() function for subtree boundary enforcement
  - Extended state mode init CLI creating .state/build/ and .state/teach/ directories
affects:
  - 098-02 (daemon middleware enforcement — imports validate_subtree_path)
  - 099 (MCP registration toggle — reads subtree presence)
  - 103 (state mode set — creates subtrees)

# Tech tracking
tech-stack:
  added: []
  patterns: [subtree-constants-in-schema, directory-presence-signal, tdd-with-regression-gate]

key-files:
  created: []
  modified:
    - src/state_core/schema.py
    - src/state_cli/main.py
    - tests/test_schema.py
    - tests/test_cli.py

key-decisions:
  - "SUBTREE_DIRS uses dict[str, str] type annotation (not bare dict) following existing type-annotation conventions in schema.py"
  - "validate_subtree_path() normalizes OS separators via str(Path(path)).replace(os.sep, '/') for cross-platform correctness"
  - "Shared .state/ root files (.state/mode.json, .state/events.sqlite) are always allowed by validate_subtree_path() regardless of mode — these are kernel-level shared files"
  - "Exact dir names without trailing slash (.state/build, .state/teach) are treated as subtree paths and rejected for wrong mode"
  - "Subtree dirs created with exist_ok=True for idempotency — re-running mode init is safe"

patterns-established:
  - "validate_* functions in schema.py wrap Pydantic/validation in ValueError for clean programmatic API (follows validate_mode_config pattern)"
  - "Subtree path constants use .state/ prefix (relative to project root) matching existing project conventions"
  - "CLI subtree creation uses BUILD_SUBTREE.removeprefix('.state/') to construct path relative to state_dir — avoids hardcoding"

requirements-completed:
  - MODE-02

# Metrics
duration: ~5min
completed: 2026-05-05
---

# Phase 098 Plan 01: Subtree Directory Presence Signal Summary

**One-liner:** Added `BUILD_SUBTREE`/`TEACH_SUBTREE` path constants and `validate_subtree_path()` subtree-boundary validator to `schema.py`, and extended `state mode init` to create `.state/build/` and `.state/teach/` directory subtrees as the 2nd layer of 6-layer defense-in-depth.

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-05T12:00:00Z
- **Completed:** 2026-05-05T12:05:00Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 4
- **Commits:** 4 (2 RED + 2 GREEN)

## Accomplishments

- `BUILD_SUBTREE = ".state/build"` and `TEACH_SUBTREE = ".state/teach"` constants provide single source of truth for subtree paths
- `SUBTREE_DIRS` dict maps persistable modes (`build`, `teach`) to their canonical directory paths
- `validate_subtree_path(path, mode)` enforces subtree boundaries — rejects paths crossing into wrong subtree for the active mode while allowing shared `.state/` root files
- `state mode init build|teach|both` now creates the corresponding `.state/build/` and/or `.state/teach/` directory subtrees
- All existing behavior preserved: mode.json creation, 0600 permissions, project root discovery, kernel rejection

## Task Commits

Each task was committed atomically (TDD: RED → GREEN):

1. **Task 1: Add BUILD_SUBTREE/TEACH_SUBTREE constants and validate_subtree_path()** 
   - `a8bcdef` (test): 10 failing validate_subtree_path tests
   - `36061be` (feat): Constants + validate_subtree_path() implementation

2. **Task 2: Extend state mode init to create subtree directories**
   - `6bcde64` (test): 7 failing CLI subtree creation tests
   - `c7ec599` (feat): Subtree directory creation in mode_init()

## Files Created/Modified

- `src/state_core/schema.py` — Added BUILD_SUBTREE, TEACH_SUBTREE, SUBTREE_DIRS constants; added validate_subtree_path() function with full normalization and boundary-checking logic
- `src/state_cli/main.py` — Extended mode_init() to create .state/build/ and .state/teach/ directories; imported BUILD_SUBTREE/TEACH_SUBTREE from schema
- `tests/test_schema.py` — Added TestValidateSubtreePath class with 10 tests covering all mode/path/edge-case combinations
- `tests/test_cli.py` — Extended TestModeInit class with 7 subtree creation tests (build/teach/both/idempotency/pollution)

## Decisions Made

- SUBTREE_DIRS uses `dict[str, str]` type annotation following existing conventions in schema.py
- validate_subtree_path() normalizes paths via `str(Path(path)).replace(os.sep, '/')` for cross-platform correctness
- Shared `.state/` root files are always allowed by validate_subtree_path() regardless of mode
- Exact dir names without trailing slash are treated as subtree paths and rejected for wrong mode
- Subtree dirs use `exist_ok=True` for idempotency

## Deviations from Plan

None — plan executed exactly as written. Both TDD tasks followed RED → GREEN flow with no issues.

## Issues Encountered

None.

## Gate Tracking

No checkpoint gates in this plan — fully autonomous execution.

## Threat Flags

None. All security surface was documented in the plan's threat model:
- T-098-01 mitigated: validate_mode_config() rejects invalid mode strings before any filesystem write
- T-098-02 mitigated: Constants are module-level immutable strings
- T-098-03 accepted: Empty directories with 0755 default perms — no content to leak
- T-098-04 mitigated: Both-mode is documented dual-mode config allowed by ModeConfig Literal constraint

## Known Stubs

None — all constants, functions, and CLI behavior are fully wired and tested.

## Next Phase Readiness

- `validate_subtree_path()` is ready for Plan 098-02 daemon middleware enforcement
- `BUILD_SUBTREE`/`TEACH_SUBTREE` constants available for Phase 099 MCP registration toggle and Phase 103 state mode set
- `.state/build/` and `.state/teach/` directory presence signal is functional for all downstream consumers

---

---

## Self-Check: PASSED

- SUMMARY.md exists: ✓
- All 4 commits verified: `a8bcdef`, `36061be`, `6bcde64`, `c7ec599` ✓
- All modified files exist: schema.py, main.py, test_schema.py, test_cli.py ✓
- 164 tests pass (124 schema + 40 CLI) with zero regressions ✓

---

*Phase: 098-directory-presence-signal*
*Completed: 2026-05-05*
