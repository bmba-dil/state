---
phase: 121
plan: 01
subsystem: state-teach MCP
tags: [mode-gate, security, refactor]
requires: [Phase 097]
provides:
  - Lightweight mode-gate for state-teach matching Phase 112 pattern
  - MODE-03 compliance (state-teach only starts when mode ∈ {teach, both})
affects: [mode enforcement, MCP server startup]
tech-stack:
  added: []
  patterns:
    - Lightweight pre-flight mode gate using inline JSON parsing (no schema/logging deps)
    - sys.exit(78) sysexits convention for configuration errors
    - sys.stderr.write() instead of structlog for gate messages
key-files:
  created:
    - .planning/milestones/v13/phases/121-mode-gate-integration/121-SUMMARY.md
  modified:
    - src/state_teach/mcp.py
    - tests/test_state_teach_mcp.py
key-decisions:
  - "Refactored check_mode_gate → _check_mode_gate to match Phase 112 naming convention"
  - "Replaced structlog + validate_mode_config with lightweight inline JSON parsing (no dependency on state_core.schema)"
  - "Changed exit code from 1 to 78 (sysexits EX_CONFIG convention matching Phase 112)"
  - "Changed corrupt JSON behavior from sys.exit(1) to silent return (leniency matching Phase 112)"
  - "Kept project_root: Path parameter (better testability than 112's CWD-relative path)"
patterns-established:
  - "Mode gates are lightweight pre-flight checks — no structlog, no schema imports"
  - "sys.exit(78) for configuration errors; sys.stderr.write() for error messages"
  - "Missing/corrupt mode.json always allows startup (development mode leniency)"
  - "Private function naming: _check_mode_gate"
requirements-completed:
  - MCP-T-01
  - MODE-03
metrics:
  duration: 222
  completed: 2026-05-05
---

# Phase 121 Plan 01: Mode-Gate Integration Summary

Refactored the Phase 115 `check_mode_gate()` in `state-teach/mcp.py` to match the Phase 112 `state-build` pattern: lightweight inline JSON parsing, `sys.stderr.write()` for errors, `sys.exit(78)` for mode mismatches, and no structlog or `state_core.schema` dependency.

## What Changed

### `src/state_teach/mcp.py`
- **Renamed** `check_mode_gate` → `_check_mode_gate` (private function convention)
- **Removed** `import structlog`, `from state_core.schema import validate_mode_config`, and `log = structlog.get_logger(__name__)` — gate is now a standalone pre-flight check
- **Rewrote gate body**: uses inline `json.loads()` + `data.get("mode")`, checks against literal allowlist `("teach", "both")`, writes to `sys.stderr.write()` on failure, exits with `sys.exit(78)`
- **Changed behavior**: corrupt/unreadable mode.json now allows startup (was `sys.exit(1)`) — matches Phase 112 leniency
- **Updated** `__main__` block to call `_check_mode_gate(Path.cwd())`

### `tests/test_state_teach_mcp.py`
- **Updated import**: `check_mode_gate` → `_check_mode_gate`
- **Updated exit code assertions**: `1` → `78` for build rejection and invalid mode tests
- **Changed `test_mode_gate_invalid_json`**: now expects normal return (no SystemExit) — corrupt JSON allows startup
- **Updated `test_mode_gate_still_works_after_tool_registration`**: exit code 1 → 78, docstring Phase 115 → Phase 121
- All 12 tests pass

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_state_teach_mcp.py -v` | 12/12 passed |
| `ruff check src/state_teach/mcp.py` | All checks passed |
| `test_import_lint_clean` | PASSED |
| `structlog` in `mcp.py` | 0 |
| `validate_mode_config` in `mcp.py` | 0 |
| `_check_mode_gate` refs in `mcp.py` | 2 (def + call) |

## MODE-03 Compliance

| Condition | Result |
|-----------|--------|
| state-teach exits when mode=build | ✓ exit 78 |
| state-teach starts when mode=teach | ✓ |
| state-teach starts when mode=both | ✓ |
| state-teach starts when mode.json missing | ✓ |
| state-teach starts when mode.json corrupt | ✓ |
| state-build gate (Phase 112) rejects teach | ✓ separate gate |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `src/state_teach/mcp.py` exists and contains `_check_mode_gate` (line 25)
- [x] `tests/test_state_teach_mcp.py` exists and imports `_check_mode_gate`
- [x] Commit `6ac3b8c` exists in git log: `refactor(121-mode-gate): align state-teach gate with Phase 112 pattern`
- [x] All 12 test assertions pass
- [x] Ruff lint passes clean
- [x] No structlog or validate_mode_config in mcp.py
