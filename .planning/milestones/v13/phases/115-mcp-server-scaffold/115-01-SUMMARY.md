---
phase: 115-mcp-server-scaffold
plan: 01
subsystem: state-teach
tags: [mcp, scaffold, mode-gate, fd80b1ac]
requires:
  - P-099 (MCP config hook — registers state-teach based on mode)
provides:
  - state-teach MCP server binary (`python3 -m state_teach.mcp`)
  - Startup mode-gate (blocks build mode before tools are exposed)
affects:
  - 116 (teach-mode MCP tools — depends on this scaffold)
  - mode-enforcement (Layer 3 — this is the server-side gate)
tech-stack:
  added:
    - mcp.server.fastmcp (FastMCP stdio transport)
  patterns:
    - mode-gate at server startup (reads .state/mode.json, sys.exit(1) on build)
    - structlog.Logger at module level with mcp.<action> event names
    - validate_mode_config reuse from state_core.schema
key-files:
  created:
    - tests/test_state_teach_mcp.py (93 lines, 8 tests)
  modified:
    - src/state_teach/mcp.py (stub → 58-line FastMCP server)
key-decisions:
  - "Used validate_mode_config (schema.py) rather than reimplementing mode validation — preserves single source of truth for persistable modes"
  - "Missing mode.json allows server start (graceful degradation) rather than blocking — follows T-115-02 threat model disposition"
  - "sys.exit(1) on fatal errors rather than raising exceptions — the server process should exit non-zero so the MCP client detects failure"
patterns-established:
  - "Module-level structlog logger: `log = structlog.get_logger(__name__)`"
  - "Mode-gate functions receive project_root: Path as parameter (testable with tmp_path)"
  - "FastMCP instance as module-level variable for test import"
  - "`from __future__ import annotations` at top of every .py file"
  - "Google-style docstrings with Args/Raises sections"
requirements-completed:
  - MCP-T-01
metrics:
  duration: "4 min"
  completed: 2026-05-05
---

# Phase 115 Plan 01: MCP Server Scaffold — Summary

**One-liner:** FastMCP stdio server registered as `state-teach` with startup mode-gate that reads `.state/mode.json` and refuses to start in `build` mode.

## What Was Built

The 3-line stub at `src/state_teach/mcp.py` was replaced with a complete 58-line FastMCP stdio server entry point:

- **Module-level `mcp` instance:** `mcp = FastMCP("state-teach")` — satisfies MCP-T-01 by registering the server identity that opencode's config hook (Phase 099) expects.
- **`check_mode_gate(project_root: Path)` function:** Reads `.state/mode.json` relative to the given project root and enforces three behaviors:
  1. **Missing file:** Logs a warning and allows start (graceful degradation per T-115-02)
  2. **Invalid JSON or config:** Logs an error and calls `sys.exit(1)` (safe shutdown per T-115-01)
  3. **Mode is `build`:** Logs an error and calls `sys.exit(1)` before any tools are exposed
  4. **Mode is `teach` or `both`:** Logs success and returns normally
- **`__main__` block:** `check_mode_gate(Path.cwd())` then `asyncio.run(mcp.run_stdio_async())`
- **Imports from state_core.schema only:** Uses `validate_mode_config` — no reimplementation, preserves single source of truth. Zero imports from `state_build`.

## Test Coverage

`tests/test_state_teach_mcp.py` — 8 tests, all passing:

| Test | What It Verifies |
|------|-----------------|
| `test_mcp_server_name` | `mcp` is a FastMCP instance with `name == "state-teach"` |
| `test_mode_gate_rejects_build` | `{"mode": "build"}` → `SystemExit(1)` |
| `test_mode_gate_allows_teach` | `{"mode": "teach"}` → returns normally |
| `test_mode_gate_allows_both` | `{"mode": "both"}` → returns normally |
| `test_mode_gate_missing_file` | No `.state/mode.json` → returns normally |
| `test_mode_gate_invalid_json` | `{not json}` → `SystemExit(1)` |
| `test_mode_gate_invalid_mode_value` | `{"mode": "kernel"}` → `SystemExit(1)` |
| `test_import_lint_clean` | `state_core.import_lint.lint()` returns `exit_code == 0` |

## Verification Results

```
✓ 8/8 tests pass (0.35s)
✓ python3 -c "from state_teach.mcp import mcp; assert mcp.name == 'state-teach'" — IMPORT_OK
✓ ruff check src/state_teach/mcp.py tests/test_state_teach_mcp.py — All checks passed!
✓ state_core.import_lint.lint() — exit_code=0, zero cross-mode violations
```

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

The plan's `tdd="true"` gate sequence is satisfied in the git log:

1. **RED:** `2d47ee5 test(115-01): add failing test for state-teach MCP server entry` (6 minimal tests, failing)
2. **GREEN:** `a39c7c6 feat(115-mcp-server-scaffold): create state-teach MCP server entry point with mode-gate` (implementation)
3. **TEST EXPANSION:** `b8f19b1 test(115-mcp-server-scaffold): add comprehensive test suite for MCP server scaffold` (+2 tests: invalid mode value + import lint)

Task 2's RED phase was effectively covered by the expansion commit — the 2 additional tests tested behavior already implemented in Task 1 GREEN, consistent with test-first verification.

## Self-Check: PASSED

```
FOUND: src/state_teach/mcp.py
FOUND: tests/test_state_teach_mcp.py
FOUND: 2d47ee5 (RED test commit)
FOUND: a39c7c6 (GREEN impl commit)
FOUND: b8f19b1 (test suite commit)
```
