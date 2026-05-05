---
wave: 1
depends_on: ["050", "004"]
files_modified:
  - src/state_daemon/middleware.py
  - src/state_daemon/server.py
  - tests/test_daemon_middleware.py
autonomous: true
---

# Plan 053-1: Mode-Enforcement HTTP Middleware

**Goal:** Implement HTTP middleware that reads `X-State-Mode` header from every request, validates against `.state/mode.json`, and rejects cross-mode write requests with 403 — the canonical mode-isolation gate.

**Requirements:** DAE-05, MODE-05

### Tasks

#### 053.1 Mode Configuration Manager

**Acceptance:** `load_mode_config()` reads `.state/mode.json` and returns `ModeConfig`; `get_current_mode()` returns the active mode.
**Estimated effort:** Small
**Dependencies:** none

**Details:**
- `ModeConfig` pydantic model with `mode: Literal["build", "teach", "both"]` field.
- `load_mode_config(root: str) -> ModeConfig`: reads `.state/mode.json` from project root, validates with pydantic, caches result.
- `get_current_mode() -> str`: returns the active mode string.
- `is_valid_mode(mode: str) -> bool`: checks if mode is one of build/teach/both/kernel.
- Test: unit tests for valid/invalid mode config files.

**Files:**
- `src/state_daemon/middleware.py` — new file

#### 053.2 Mode-Enforcement Middleware

**Acceptance:** Middleware rejects cross-mode write operations with HTTP 403; read operations pass through.
**Estimated effort:** Medium
**Dependencies:** 053.1

**Details:**
- `ModeMiddleware` class that wraps the router callable.
- Reads `X-State-Mode` header from request. If missing or invalid: reject with 400.
- Compare request mode against `.state/mode.json` configured mode:
  - If modes match: allow.
  - If mode is "both": allow all.
  - If mismatched: check if request is read-only (GET, HEAD) — allow. If write (POST, PUT, PATCH, DELETE) — reject with 403.
- Read vs write heuristic: GET/HEAD methods are reads; POST to `/health` is read; POST to `/events/...` is write.
- Special consideration: `kernel` mode always allowed (internal operations).
- Response format on rejection: `{"error": "cross_mode_rejected", "request_mode": "...", "active_mode": "..."}`.
- Test: parameterized tests for all mode combinations, read vs write, missing header, invalid mode.

**Files:**
- `src/state_daemon/middleware.py` — extend with middleware class

#### 053.3 Integration with DaemonServer + Orchestrator

**Acceptance:** Middleware is wired into the request pipeline; cross-mode writes are blocked before reaching handlers.
**Estimated effort:** Small
**Dependencies:** 053.2, 050.3

**Details:**
- Wire `ModeMiddleware` into `orchestrator.startup()` — create after mode config loaded, wrap the router.
- The middleware sits between the HTTP server and the JSON-RPC router.
- Verify: integration test that starts server with mode=build, sends a write with X-State-Mode=teach, asserts 403.
- Test: integration test that READ with mismatched mode passes through (GET /health).

**Files:**
- `src/state_daemon/orchestrator.py` — wire middleware
- `src/state_daemon/server.py` — accept middleware wrapper

### Integration Notes

- This is the **6th layer** of defense-in-depth for mode isolation (canonical daemon gate).
- Later phases (v11) add additional layers at import-graph and static levels.
- `.state/mode.json` is created by `state mode set build|teach|both` (CLI, Phase 058).
- For now, create a default mode.json if missing (default to "both").

### must_haves

1. Middleware reads `X-State-Mode` header and validates mode.
2. Cross-mode write operations rejected with HTTP 403.
3. Read operations pass through even on mode mismatch.
4. Missing/invalid header returns HTTP 400.
5. Kernel mode always allowed.
