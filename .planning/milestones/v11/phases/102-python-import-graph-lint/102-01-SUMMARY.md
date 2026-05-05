---
phase: 102-python-import-graph-lint
plan: 01
subsystem: infra
tags: [python, ast, import-lint, mode-isolation, pre-commit, ruff, pytest, coverage]

# Dependency graph
requires:
  - phase: 101-daemon-http-mode-middleware
    provides: "Daemon HTTP middleware (prior mode-enforcement layer)"
provides:
  - "Python import-graph linter enforcing mode isolation at the AST level"
  - "20-test pytest suite with 92%% coverage"
  - "pre-commit hook guarding every commit against cross-mode imports"
affects: [testing, ci, mode-enforcement, code-quality]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AST-based import analysis using stdlib ast module (no third-party deps)"
    - "TDD workflow: RED (failing test) → GREEN (minimal implementation) → extended coverage"
    - "Pre-commit local hook with venv Python for import-lint gate"

key-files:
  created:
    - "src/state_core/import_lint.py"
    - "tests/test_import_lint.py"
  modified:
    - ".pre-commit-config.yaml"

key-decisions:
  - "Used stdlib ast module instead of regex for robust import parsing (handles all ast.Import / ast.ImportFrom shapes)"
  - "Default root resolution walks up from __file__ to find pyproject.toml or .git"
  - "Allowed-cross-importer set (state_daemon, state_cli) is a frozenset at module level for clarity"
  - "Pre-commit hook uses .venv/bin/python3 for local venv portability"
  - "_is_forbidden() returns single boolean expression for ruff SIM103 compliance"
  - "sys.stderr.write used instead of print() for ruff T201 compliance"

patterns-established:
  - "AST-walk pattern for import analysis: walk tree for ast.Import/ast.ImportFrom, extract first module component, check against violation rules"
  - "tmp_path fixture pattern for filesystem-based lint tests with _setup_dirs() helper"
  - "Mode-isolation defense-in-depth: this is layer 6/6, complementing directory signals, MCP registration toggle, plugin hook gate, HTTP middleware, and JSON schema validation"

requirements-completed:
  - MODE-06
  - TST-07

# Metrics
duration: 18min
completed: 2026-05-05
---

# Phase 102 Plan 01: Python Import-Graph Lint Summary

**AST-based import-graph linter enforcing mode isolation between state_build and state_teach at the Python import level — layer 6/6 of defense-in-depth**

## Performance

- **Duration:** ~18 min
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 1
- **Test coverage:** 92% (20 tests, all passing)

## Accomplishments

- Created `src/state_core/import_lint.py` with `lint()`, `CheckResult`, and `Violation` exports — scans all `.py` files under `src/` using stdlib `ast` for cross-mode import violations
- `python3 -m state_core.import_lint` exits 0 on the clean codebase, exits 1 with clear `file:line: forbidden import of target` messages when violations exist
- 20-test pytest suite covering: cross-mode detection (build↔teach), state_core violation detection, allowed paths (state_core imports, daemon/cli cross-imports), relative imports, edge cases (syntax errors, broken symlinks, empty dirs, pycache skip)
- Pre-commit hook added to `.pre-commit-config.yaml` running import-lint on every commit
- Confirmed detection works: injected `from state_teach.concepts import Concept` into `state_build/__init__.py`, linter correctly reported violation and exited 1

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing test suite** — `e0d19ea` (test)
2. **Task 1 GREEN: Implementation** — `4223510` (feat)
3. **Task 2: Comprehensive test coverage** — `0aa20f6` (test)
4. **Pre-commit hook integration** — `9b67cba` (chore)

## Files Created/Modified

- `src/state_core/import_lint.py` — Core linter with Violation/CheckResult dataclasses, `lint()` function walking AST nodes, CLi entry point, MODE-06/TST-07 docstring
- `tests/test_import_lint.py` — 20 pytest functions covering all violation rules, allowed paths, edge cases, and CLI exit codes
- `.pre-commit-config.yaml` — Added local import-lint hook using venv Python

## Decisions Made

- **Stdlib `ast` over regex**: More robust than regex-based import detection, handles all `import`/`from ... import` shapes correctly including multi-line and dotted imports
- **Root resolution**: Walks up from `__file__` to find `pyproject.toml`/`.git`, falls back to `Path.cwd()` — matches project convention from `database.py`
- **Violation rules as single boolean**: `_is_forbidden()` returns a single expression for ruff SIM103 compliance while maintaining readable comments
- **Pre-commit hook with venv Python**: Uses `.venv/bin/python3` for local development; CI would need to create venv first (standard project setup)

## Deviations from Plan

None — plan executed exactly as written. Minor ruff compliance fixes (import ordering, SIM103 return simplification, T201 print→sys.stderr.write) were part of normal implementation flow, not deviations.

## Issues Encountered

- System Python (3.14) didn't have project dependencies installed for pre-commit hook — resolved by pointing hook at `.venv/bin/python3`
- Initial coverage at 82% below the 90% threshold — added 6 targeted edge-case tests (syntax error handling, pycache skip, `from . import x`, broken symlink, missing directories, Violation.__str__ format) to reach 92%

## Next Phase Readiness

- Import-graph lint is now the final layer (6/6) of mode-enforcement defense-in-depth
- Ready for CI integration: pre-commit hook catches violations at commit time
- Future cross-mode import attempts will be blocked before code review
- No blockers; all verification criteria met

---

*Phase: 102-python-import-graph-lint*
*Plan: 01*
*Completed: 2026-05-05*
