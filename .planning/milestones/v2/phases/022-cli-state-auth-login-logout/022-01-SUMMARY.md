---
phase: 022-cli-state-auth-login-logout
plan: "01"
subsystem: auth-test-scaffold
tags: [test-scaffold, golden-infrastructure, wave-0-red, AUTH-12, AUTH-13]
dependency_graph:
  requires: []
  provides:
    - tests/auth/conftest.py golden infrastructure fixtures
    - tests/auth/golden/ provider subdirectory tree
    - tests/auth/test_p0_regression.py 9 P0 RED stubs
    - tests/auth/test_cli_ops.py 14 ops-layer RED stubs
    - tests/auth/test_cli_typer.py 15 Typer command RED stubs
    - tests/auth/test_import_graph.py Phase 022 CLI mode-isolation rows
  affects:
    - Plans 02, 03, 04 (turn stubs GREEN)
tech_stack:
  added: []
  patterns:
    - pytest_addoption hook for --update-goldens flag
    - golden_load fixture factory (provider_id, flow_name) -> dict
    - json_dump_deterministic with Bearer secret scrubbing
    - pytest.fail (not pytest.skip) for Wave 0 RED stubs
key_files:
  created:
    - tests/auth/test_p0_regression.py
    - tests/auth/test_cli_ops.py
    - tests/auth/test_cli_typer.py
    - tests/auth/test_import_graph.py
    - tests/auth/golden/.gitkeep
    - tests/auth/golden/anthropic/.gitkeep
    - tests/auth/golden/google.gemini/.gitkeep
    - tests/auth/golden/google.antigravity/.gitkeep
    - tests/auth/golden/github.copilot/.gitkeep
    - tests/auth/golden/api_key/.gitkeep
  modified:
    - tests/auth/conftest.py
decisions:
  - "Used pytest.fail() (not pytest.skip) for all Wave 0 RED stubs — ensures visible RED, not silent green"
  - "Golden dirs created at conftest module level (idempotent mkdir) — no fixture scope needed"
  - "test_import_graph.py created from scratch in worktree (absent from this branch); includes full Phase 018/019/021 content plus Phase 022 additions"
metrics:
  duration: "~6m"
  completed: "2026-05-02T02:54:10Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 10
  files_modified: 1
---

# Phase 022 Plan 01: Wave 0 RED Stubs + Golden Infrastructure Summary

**One-liner:** Test scaffold with 38 Wave-0-RED stubs (9 P0 + 14 ops-layer + 15 Typer), pytest_addoption --update-goldens flag, json_dump_deterministic with Bearer secret scrubbing, and golden/ directory tree for 5 providers.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | conftest.py golden infrastructure + shared fixtures | 26c787f | tests/auth/conftest.py, tests/auth/golden/ (6 files) |
| 2 | RED stubs — test_p0_regression.py, test_cli_ops.py, test_cli_typer.py, test_import_graph.py | e945abb | 4 test files created/extended |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**One note on test_import_graph.py:** The plan specified "EXTEND (do NOT replace)" for `test_import_graph.py`. In this worktree (branched before Phase 018/019/021 work was merged), the file did not exist. The file was created from scratch with the full canonical content (Phase 018/019/021 rows copied from the main branch read at execution start) plus the new Phase 022 rows. This is semantically equivalent to an "extend" — the Phase 022 rows are correctly appended at the end.

## Issues Encountered

None — all 38 stubs collect and fail as FAILED (not ERROR). Pre-existing test_base.py (hypothesis dep) and test_anthropic.py (pytest-httpx dep) issues required installing missing deps in the worktree venv; these are pre-existing infrastructure gaps, not regressions from Plan 01 changes.

## Self-Check: PASSED

- tests/auth/conftest.py: FOUND
- tests/auth/test_p0_regression.py: FOUND
- tests/auth/test_cli_ops.py: FOUND
- tests/auth/test_cli_typer.py: FOUND
- tests/auth/test_import_graph.py: FOUND
- tests/auth/golden/{anthropic,google.gemini,google.antigravity,github.copilot,api_key}: FOUND
- Commit 26c787f: FOUND
- Commit e945abb: FOUND
- 38 stubs fail as FAILED (not ERROR): VERIFIED
- All imports OK: VERIFIED
- No secrets in golden tree: VERIFIED
