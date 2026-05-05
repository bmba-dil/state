---
phase: 053
plan: 053-01
subsystem: state-daemon
tags: [middleware, mode-enforcement, http, security, defense-in-depth]
requires: [050, 004]
provides: [canonical-mode-gate, X-State-Mode-validation, cross-mode-write-rejection]
affects: [058, 061, 070, 100]
tech-stack:
  added: []
  patterns: [middleware-decorator-pattern, router-wrapping, tuple-status-signaling]
key-files:
  created:
    - src/state_daemon/middleware.py
    - tests/test_daemon_middleware.py
  modified:
    - src/state_daemon/server.py
    - src/state_daemon/orchestrator.py
key-decisions:
  - "Router return type extended to bytes | tuple[int, bytes] for backward-compatible middleware status code signaling"
  - "ModeMiddleware wraps the router callable (decorator pattern) rather than modifying DaemonServer internals"
  - "Kernel mode always bypasses mode enforcement (internal operations)"
  - "Default mode is 'both' when .state/mode.json is missing (permissive by default)"
  - "Mode config cached at module level — loaded once at daemon startup, survives per-request"
patterns-established:
  - "Middleware callables implement the Router signature and return tuple[int, bytes] for non-200 status codes"
  - "Rejection payloads follow {error, request_mode, active_mode} schema"
  - "Read operation heuristic: GET/HEAD always read, POST /health is read, everything else is write"
requirements-completed: [DAE-05, MODE-05]
metrics:
  duration: "12m 14s"
  completed: 2026-05-04
---

# Phase 053 Plan 053-01: Mode-Enforcement HTTP Middleware Summary

**One-liner:** Implemented the 6th layer of defense-in-depth mode isolation — an HTTP middleware that validates `X-State-Mode` header on every request, rejects cross-mode writes with 403, and passes read operations through even on mode mismatch.

## Completed Tasks

| #    | Task                           | Status  | Commit   |
| ---- | ------------------------------ | ------- | -------- |
| 053.1 | Mode Configuration Manager    | ✅ Done | 488994f  |
| 053.2 | Mode-Enforcement Middleware   | ✅ Done | 488994f  |
| 053.3 | Integration with DaemonServer | ✅ Done | c95ae5e  |

## What Was Built

### Task 053.1 — Mode Configuration Manager

- **`ModeConfig`** pydantic model with `mode: Literal["build", "teach", "both"]` field
- **`load_mode_config(root)`** reads `.state/mode.json`, validates with pydantic, caches at module level. Creates default `{"mode": "both"}` if missing.
- **`get_current_mode()`** returns active mode string (defaults to `"both"`)
- **`is_valid_mode(mode)`** validates against `{build, teach, both, kernel}`
- 19 unit tests covering valid/invalid config, missing files, JSON errors, mode validation

### Task 053.2 — Mode-Enforcement Middleware

- **`ModeMiddleware`** class implementing the `Router` callable signature
- Reads `X-State-Mode` header (lowercased by DaemonServer)
- Decision tree:
  1. Missing/invalid header → **400** `{"error": "missing_mode_header"/"invalid_mode_header"}`
  2. Active mode `"both"` → allow all
  3. Request mode `"kernel"` → allow all
  4. Modes match → allow
  5. Mismatch + read operation (GET/HEAD, POST /health) → allow
  6. Mismatch + write operation → **403** `{"error": "cross_mode_rejected", "request_mode": "...", "active_mode": "..."}`
- 17 unit tests covering all mode combinations, read vs write, rejection payloads

### Task 053.3 — Server + Orchestrator Integration

- **`DaemonServer`** Router return type extended: `bytes | tuple[int, bytes]`. Server detects tuple returns and uses provided status code instead of default 200.
- **`orchestrator.startup()`** loads `ModeConfig` from project root, creates `ModeMiddleware`, wraps `JsonRpcRouter` before passing to `DaemonServer`
- Added HTTP 403 to status text dictionary
- 5 integration tests using real DaemonServer + ModeMiddleware + JsonRpcRouter over unix sockets

### Test Coverage

**60 tests** (41 new middleware tests + 19 existing server/router tests — all passing):
- `TestModeConfig` — 4 tests
- `TestLoadModeConfig` — 4 tests
- `TestCurrentMode` — 3 tests
- `TestIsValidMode` — 8 parameterized tests
- `TestModeMiddleware` — 17 tests
- `TestIntegration` — 5 tests
- Existing server/router tests — 19 tests (backward-compatible, all pass)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `_reject()` reading stale global config instead of middleware config**
- **Found during:** Task 053.2 test run
- **Issue:** `_reject()` called `get_current_mode()` which read the module-level `_config` global cached from a previous test, returning wrong active_mode in rejection payloads
- **Fix:** Added `active_mode` parameter to `_reject()`, passed from `ModeMiddleware.__call__()` which holds the actual config. Moved `active_mode = self._config.mode` before early rejection calls.
- **Files modified:** `src/state_daemon/middleware.py`
- **Commit:** 488994f

**2. [Rule 3 - Blocking] Fixed `rtk pytest` using system Python (no litellm) instead of project venv**
- **Found during:** Task 053.1 initial test run
- **Issue:** `rtk pytest` resolved to `/opt/homebrew/bin/python3` which lacked `litellm`, causing all tests to fail on `import litellm` in orchestrator
- **Fix:** Used `.venv/bin/python3 -m pytest` directly (project virtual environment has all dependencies installed)
- **Files modified:** none (workflow adjustment only)

## Known Stubs

None — all mode configurations are fully functional. The default-mode-on-missing behavior (`"both"`) is intentional permissive-by-default design until Phase 058 CLI provides explicit `state mode set`.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-auth-surface | `src/state_daemon/middleware.py` | ModeMiddleware introduces a new authorization gate (X-State-Mode header) that sits before all JSON-RPC handlers. Rejection payloads include `active_mode` metadata — verify this doesn't leak to unauthorized callers if the daemon socket permissions (0600) are ever relaxed. |

## Self-Check: PASSED

- ✅ `src/state_daemon/middleware.py` exists (235 lines)
- ✅ `tests/test_daemon_middleware.py` exists (680 lines)
- ✅ Commit 488994f exists (middleware + tests)
- ✅ Commit c95ae5e exists (server + orchestrator wiring)
- ✅ 60/60 tests pass (41 new + 19 existing)
- ✅ No file deletions in either commit
- ✅ `orchestrator.py` imports cleanly
- ✅ Existing server/router tests fully backward-compatible
