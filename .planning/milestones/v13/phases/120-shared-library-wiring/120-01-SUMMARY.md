---
phase: 120
plan: "01"
subsystem: "state_teach"
tags: ["wiring", "shared-library", "state_core", "auth", "events"]
dependency_graph:
  requires: ["115"]  # MCP server scaffold
  provides: ["state_teach wired to state_core.auth and state_core.events"]
  affects: ["121", "122", "123"]
tech_stack:
  added: []
  patterns: ["aliased noqa:F401 shared-library imports (mirrors state_build Phase 111)"]
key_files:
  created:
    - "tests/test_state_teach_wiring.py"
  modified:
    - "src/state_teach/mcp.py"
key_decisions:
  - "Mirrored state_build/mcp.py Phase 111 import pattern: from state_core.auth import load_credentials as _load_credentials, from state_core.events import SqliteEventStore as _SqliteEventStore, both with noqa:F401"
  - "Did NOT import state_core.scheduler.DAGScheduler -- that is build-mode only, not needed by state_teach"
  - "Used private-as aliases (_load_credentials, _SqliteEventStore) to signal 'wired but not yet consumed by tool implementations'"
patterns_established:
  - "Mode-specific shared-library wiring: only import what the mode needs (teach doesn't need DAGScheduler)"
  - "Aliased imports with noqa:F401 until tool implementations consume them"
requirements_completed: []
metrics:
  duration: "2m"
  completed: "2026-05-06"
---

# Phase 120 Plan 01: state_teach → state_core Wiring Summary

Wired state_teach MCP server to the shared state_core library for auth (provider credentials via `load_credentials`) and events (event store via `SqliteEventStore`), following the identical pattern established by state_build in Phase 111.

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Wire state_teach/mcp.py to state_core.auth and state_core.events | ✓ | `f5fc8ad` |
| 2 | Add wiring test | ✓ | `6ed3e44` |

## What Was Built

Two import lines added to `src/state_teach/mcp.py`:

```python
from state_core.auth import load_credentials as _load_credentials  # noqa: F401
from state_core.events import SqliteEventStore as _SqliteEventStore  # noqa: F401
```

Tests in `tests/test_state_teach_wiring.py` verify:
- `load_credentials` is importable and callable
- `SqliteEventStore` is instantiable
- No regression on existing MCP server functionality (tools, mode gate, SkeletonResponse)

## Verification Results

```
=== import lint ===
python3 -m state_core.import_lint → exit 0 (clean, no cross-mode violations)

=== wiring tests (5/5 pass) ===
tests/test_state_teach_wiring.py::test_wiring_load_credentials_importable PASSED
tests/test_state_teach_wiring.py::test_wiring_sqlite_event_store_instantiable PASSED
tests/test_state_teach_wiring.py::test_wiring_mcp_server_still_functional PASSED
tests/test_state_teach_wiring.py::test_wiring_mode_gate_still_works PASSED
tests/test_state_teach_wiring.py::test_wiring_skeleton_response_still_works PASSED

=== regression: existing teach tests ===
tests/test_state_teach_mcp.py — 11/11 pass
tests/test_state_teach_mcp_tools.py — 3/5 pass (2 pre-existing failures unrelated to wiring)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The two imported symbols (`_load_credentials`, `_SqliteEventStore`) use private-as aliases and `noqa:F401` because no tool implementations consume them yet. They are wired for future phases (121 mode-gate integration, 122 tool-budget CI, 123 integration test). This is intentional — the imports establish the shared-library surface that downstream tool implementations will use.

## Self-Check: PASSED

- `src/state_teach/mcp.py` — modified, exists ✓
- `tests/test_state_teach_wiring.py` — created, exists ✓
- `f5fc8ad` (feat commit) — exists ✓
- `6ed3e44` (test commit) — exists ✓
- import lint passes ✓
- all wiring tests pass ✓
