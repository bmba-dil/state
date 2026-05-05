# v7-REQUIREMENTS — Per-Session Worker

**Archived:** 2026-05-05
**Status:** Shipped
**Phase range:** 060–067

---

## Kernel: Per-Session Worker (A7)

- [x] **WRK-10**: Worker attaches to daemon on opencode session start; tears down on session close
  - Verified by: Phase 060 (attach/health check), Phase 061 (SSE bridge), Phase 065 (teardown), Phase 067 (stress test)
  - Outcome: Validated — worker discovers daemon, attaches, flushes hooks, disconnects cleanly.

- [x] **WRK-11**: Worker owns hot state for the current session (active Slice, current Step FSM position, in-progress drill)
  - Verified by: Phase 062 (HotState container), Phase 067 (stress test)
  - Outcome: Validated — HotState pydantic model synced from daemon events via bridge callback.

- [x] **WRK-12**: Worker forwards opencode hook events to daemon over HTTP+SSE
  - Verified by: Phase 061 (SSE bridge), Phase 063 (forward_hook), Phase 067 (stress test)
  - Outcome: Validated — forward_hook with retry, version header, SSE event parsing.

- [x] **WRK-13**: Mismatched plugin/daemon version negotiation — handshake header on worker attach; refuses on incompatible
  - Verified by: Phase 064 (version check), Phase 067 (stress test)
  - Outcome: Validated — `x-state-plugin-version` header, compat range check, HTTP 426 rejection.

- [x] **OBS-01** (partial): Structured logging with rotation and redaction for worker
  - Verified by: Phase 066 (worker logging)
  - Outcome: Partial — per-worker-PID rotating log file with redactor. Full observability unification deferred to v8+.

## Traceability

| Requirement | Phase(s) | Test Coverage | Status |
|-------------|----------|---------------|--------|
| WRK-10 | 060, 061, 065, 067 | 16 main + 8 bridge + 8 hooks + 4 stress = 36 | ✅ |
| WRK-11 | 062, 067 | hot_state tests + 4 stress = 4+ | ✅ |
| WRK-12 | 061, 063, 067 | 8 bridge + 5 forward_hook + 4 stress = 17 | ✅ |
| WRK-13 | 064, 067 | 7 version + 4 daemon handshake + 4 stress = 15 | ✅ |
| OBS-01 | 066 | 4 logging | ⚠️ (partial) |
