---
phase: 097
plan: 02
subsystem: cli
tags: [typer, mode, json, chmod]

# Dependency graph
requires:
  - phase: 097-01
    provides: "ModeConfig model + validate_mode_config() in src/state_core/schema.py"
provides:
  - "state mode init <mode> Typer CLI command wired as mode_app sub-app"
  - "7 TestModeInit tests covering build/teach/both happy paths, kernel/invalid rejection, auto-created .state/ directory, overwrite behavior"
affects: ["Phase 098 (directory-presence signal)", "Phase 103 (state mode set)"]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Typer sub-app composition (mode_app = typer.Typer + app.add_typer)", "validate-before-write CLI pattern (Pydantic guard then filesystem)", "os.chmod 0600 applied immediately after json.dump"]

key-files:
  created: []
  modified:
    - "src/state_cli/main.py — mode_app sub-app + mode_init command"
    - "tests/test_cli.py — TestModeInit class with 7 tests"

key-decisions:
  - "validate_mode_config() from schema.py is the single source of mode validation — kernel/invalid modes rejected before any filesystem write"
  - "Project root discovery walks upward from cwd looking for existing .state/ directory; falls back to cwd if none found"
  - "os.chmod 0o600 applied immediately after json.dump — no window where mode.json is world-readable"

patterns-established:
  - "Typer sub-app: mode_app = typer.Typer(name='mode') + app.add_typer(mode_app)"
  - "Validation-before-write: try/except ValueError wrapping validate_mode_config, raising typer.Exit(code=1) on failure"
  - "Test isolation: os.chdir(tmp_path) with try/finally restore; shutil.rmtree for fixture-created .state/ directories"

requirements-completed: [MODE-01]

# Metrics
duration: 10min
completed: 2026-05-05
---

# Phase 097 Plan 02: CLI `state mode init` Command Summary

**Typer `state mode init build|teach|both` CLI command creating `.state/mode.json` with 0600 permissions and Pydantic validation before filesystem writes**

## Performance

- **Duration:** ~10 min
- **Tasks:** 1 (auto)
- **Files modified:** 2

## Accomplishments

- Registered `mode_app` Typer sub-app with `app.add_typer(mode_app)` following the existing sub-app composition pattern (db_app, events_app, auth_app, etc.)
- Implemented `mode_init` command that validates mode via `validate_mode_config()` from `src.state_core.schema` before touching the filesystem
- Kernel mode ("kernel") and arbitrary strings rejected with clear error messages and exit code 1
- `.state/` directory auto-created if missing; existing `mode.json` overwritten on re-init
- `os.chmod(mode_path, 0o600)` applied immediately after `json.dump` — mitigates Information Disclosure (T-097-05)

## Task Commits

1. **Task 1: Wire state mode init CLI command with tests** — `f458ac3` (feat)

## Files Modified

- `src/state_cli/main.py` — +59 lines: mode_app registration, mode_init command with validate-before-write + project-root discovery + chmod 0600
- `tests/test_cli.py` — +97 lines: TestModeInit class, 7 tests, import of `os` module

## Tests

All 7 TestModeInit tests pass:
- `test_init_build_creates_mode_json` — mode.json exists with `{"mode": "build"}` and 0600 permissions
- `test_init_teach` — `{"mode": "teach"}`
- `test_init_both` — `{"mode": "both"}`
- `test_rejects_invalid_mode` — "invalid" exits non-zero, no file created
- `test_rejects_kernel_mode` — "kernel" exits non-zero (not persistable)
- `test_creates_dot_state_dir_if_missing` — `.state/` auto-created
- `test_overwrites_existing_mode_json` — re-init overwrites existing config

Existing 26 CLI tests (TestTail, TestReplay, TestExport, TestEdgeCases) — zero regressions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture conflict: _isolate_db autouse fixture pre-creates .state/ directory**
- **Found during:** Task 1 verification (first test run)
- **Issue:** The `_isolate_db` autouse fixture copies migrations into `tmp_path/.state/migrations/`, which creates `.state/` before the mode init tests check for its absence. Two tests (`test_creates_dot_state_dir_if_missing`, `test_overwrites_existing_mode_json`) failed on first run because `.state/` already existed.
- **Fix:** 
  - `test_creates_dot_state_dir_if_missing`: Added `shutil.rmtree(state_dir)` before the assertion to remove the fixture-created `.state/` directory.
  - `test_overwrites_existing_mode_json`: Changed `state_dir.mkdir(parents=True)` to `state_dir.mkdir(parents=True, exist_ok=True)`.
- **Files modified:** `tests/test_cli.py`
- **Verification:** All 7 tests pass on second run.
- **Committed in:** `f458ac3` (included in task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Minimal — fixture awareness fix only. No functional changes to the CLI command or validation logic.

## Decisions Made

None beyond plan — followed plan as specified.

## Issues Encountered

None.

## Threat Surface Verification

All three plan-specified threats addressed:
- **T-097-04 (Tampering):** `validate_mode_config()` with `Literal["build","teach","both"]` rejects arbitrary strings before filesystem access ✓
- **T-097-05 (Information Disclosure):** `os.chmod(mode_path, 0o600)` applied immediately after `json.dump` ✓
- **T-097-06 (Elevation of Privilege):** Project-root discovery via upward walk (accepted risk per plan) — documented ✓

No new threat surface introduced beyond plan scope.

## Next Plan Readiness

Ready for Phase 098 (`.state/build/` vs `.state/teach/` directory-presence signal) which depends on the `.state/mode.json` file created by this plan's CLI command.

---

*Phase: 097-state-mode-json-schema-validator*
*Completed: 2026-05-05*
