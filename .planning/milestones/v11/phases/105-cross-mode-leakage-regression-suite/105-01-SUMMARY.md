---
phase: 105-cross-mode-leakage-regression-suite
plan: 01
subsystem: testing
tags:
  - regression
  - mode-enforcement
  - defense-in-depth
requires:
  prior_phase: "097, 098, 099, 100, 101, 102"
  provides: "Consolidated 6-layer cross-mode leakage regression suite"
provides:
  - "tests/test_mode_leakage_regression.py"
affects:
  - "mode-isolation"
  - "verification"
  - "ci"
tech-stack:
  added: []
  patterns:
    - "Python test helper functions reproducing TypeScript plugin logic for gate testing"
    - "Parametrized pytest matrices for exhaustive mode×method×event-type testing"
    - "Direct ModeMiddleware.__call__() invocation (no socket) for fast isolated tests"
key-files:
  created:
    - "tests/test_mode_leakage_regression.py"
  modified: []
key-decisions:
  - "Use .venv/bin/python3 for test execution because system pydantic namespace is broken"
  - "Layers 3+4 logic reproduced as testable Python helpers matching TypeScript contracts byte-for-byte"
  - "Middleware tests call __call__() directly — no daemon socket needed, sub-ms per test"
  - "test_no_external_conftest_dependency uses line-by-line check to avoid matching its own assertion strings"
patterns-established:
  - "All 6 mode-enforcement layers tested in single file with parametrized matrices"
  - "Regression tests for mode boundaries call production code at arm's length via public API"
  - "Middleware tests assert rejection tuples (status, body) for 400/403; pass-through returns plain bytes"
requirements-completed:
  - TST-08
metrics:
  duration: "8m 37s"
  completed: "2026-05-05"
---

# Phase 105 Plan 01: Cross-Mode Leakage Regression Suite Summary

**One-liner:** Consolidated 114-test regression harness validating all 6 defense-in-depth mode-enforcement layers reject every illegal cross-mode combination at the canonical gate.

## Results

| Metric | Value |
|--------|-------|
| Total tests | 114 (63 unparametrized, 51 parametrized expansions) |
| Pass rate | 114/114 (100%) |
| Runtime | 1.17s |
| File size | 833 lines |
| Commits | 3 |

## Layer Coverage

### Layer 1 — mode.json Schema Validation (11 tests)
- ModeConfig accepts "build", "teach", "both"; rejects "kernel", "invalid", "", None
- Extra fields rejected (extra="forbid")
- validate_mode_config() raises ValueError for missing mode key, empty dict, unknown value

### Layer 2 — Subtree Path Enforcement (17 tests)
- Cross-mode paths: `.state/teach/*` rejected in build, `.state/build/*` rejected in teach
- Exact directory matches (`.state/build`, `.state/teach`) rejected in opposite mode
- Kernel files (mode.json, events.sqlite, auth.json) always allowed
- Path objects and strings behave identically
- "both" mode allows all subtrees

### Layer 3 — MCP Registration Logic (7 tests)
- Build → `["state-build"]`, Teach → `["state-teach"]`, Both → `["state-build", "state-teach"]`
- Null/unknown mode → `[]`
- Cross-mode exclusion: build list excludes `state-teach`, teach list excludes `state-build`

### Layer 4 — Plugin Hook Gate Logic (20 tests)
- Command gate: `/state:teach:*` blocked in build, `/state:build:*` blocked in teach
- Tool gate: `mcp__state-teach__*` blocked in build, `mcp__state-build__*` blocked in teach
- Both mode allows all commands and tools
- Non-state commands/tools never blocked (no false positives)

### Layer 5 — Daemon HTTP Middleware (32 tests)
- Cross-mode writes (POST/PUT/PATCH/DELETE) → 403 "cross_mode_rejected"
- Reads (GET/HEAD) with mismatch → allowed (200)
- Missing/invalid/whitespace header → 400
- Kernel bypass always allowed
- Both active mode allows all headers
- All 8 teach event types rejected in build → 403 "cross_mode_event_rejected"
- All 4 build prefix families rejected in teach → 403 "cross_mode_event_rejected"
- Allowed paths: same-mode events, non-state.emit, malformed JSON, empty body, null type
- Prefix constant counts verified (2 teach, 4 build)

### Layer 6 — Python Import-Graph Lint (9 tests)
- Detects: build→teach, teach→build, core→build, core→teach
- Allows: build→core, teach→core, daemon→build, daemon→teach
- Clean codebase: `lint()` exits 0

### Full-Suite Smoke (6 tests)
- All 7 test classes exist with test methods
- Clean import without errors
- 50+ unparametrized test methods (63 actual)
- No conftest dependency
- MCP server separation guarantee
- No false positives for common commands/tools

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_no_external_conftest_dependency matching its own assertion string**
- **Found during:** Task 3 verification
- **Issue:** The test searched file content for the literal string "import conftest", which appeared in the test's own assertion `assert "import conftest" not in content`. The content read included the test code itself, creating a false positive failure.
- **Fix:** Changed to line-by-line checking of import statements (using `line.strip().startswith()`) to avoid matching assertion strings in the file content.
- **Files modified:** `tests/test_mode_leakage_regression.py`
- **Commit:** `14b99d5`

**2. [Rule 3 - Blocking] System Python has broken pydantic namespace; switched to .venv/bin/python3**
- **Found during:** Task 1 initial test run
- **Issue:** `python3` on the host uses a namespace package at `/opt/homebrew/lib/python3.14/site-packages/pydantic/` with no `__init__.py`, preventing `from pydantic import ValidationError`. The project's `.venv/` has a working pydantic v2.13 installation.
- **Fix:** Use `.venv/bin/python3` for all test runs (not a code change — environment workaround).
- **Note:** This is a pre-existing environment issue affecting all tests in the project, not specific to this plan.

## Verification

```bash
# Run full regression suite
.venv/bin/python3 -m pytest tests/test_mode_leakage_regression.py -x -v

# Spot-check specific assertions
.venv/bin/python3 -m pytest tests/test_mode_leakage_regression.py -x -v -k "test_build_mode_rejects_teach_event"
.venv/bin/python3 -m pytest tests/test_mode_leakage_regression.py -x -v -k "test_cross_mode_write_rejected_403"
.venv/bin/python3 -m pytest tests/test_mode_leakage_regression.py -x -v -k "test_lint_clean_on_codebase"
```

**Result:** 114/114 passed in 1.17s, zero warnings.

## Commits

| Hash | Type | Message |
|------|------|---------|
| `84e308d` | test | add failing regression tests for Layers 1,2,6 (mode schema, subtree, import lint) |
| `080a5a0` | test | add Layer 5 regression tests for daemon middleware canonical gate |
| `14b99d5` | test | add Layers 3+4 (MCP registration, hook gates) and full-suite smoke tests |

## Self-Check: PASSED

- [x] `tests/test_mode_leakage_regression.py` exists (833 lines)
- [x] Commit `84e308d` exists (Task 1)
- [x] Commit `080a5a0` exists (Task 2)
- [x] Commit `14b99d5` exists (Task 3)
- [x] All 114 tests pass
- [x] SUMMARY.md created at correct path
