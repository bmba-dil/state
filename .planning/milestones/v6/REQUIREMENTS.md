# v6 — State Daemon (HTTP + SSE + Mode Middleware) Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Kernel: Daemon (A6)

- [ ] **DAE-01**: Always-on user service (launchd plist on macOS, systemd --user unit on Linux)
- [ ] **DAE-02**: Per-session worker spawned by plugin shim; shares event store with daemon via HTTP+SSE
- [x] **DAE-03**: pid-file includes process `start_time_ns`; stale-pid detection via `/proc` (Linux) or `ps` (macOS) ✓ (Phase 051, 2026-05-05)
- [x] **DAE-04**: Unix socket at `$XDG_RUNTIME_DIR/state-<projecthash>.sock` (fallback `/tmp/state-<user>-<hash>.sock`) ✓ (Phase 052, 2026-05-04)
- [ ] **DAE-05**: HTTP API (Starlette or bare) with mode-enforcement middleware (canonical gate)
- [ ] **DAE-06**: SSE broadcast for live TUI updates (event forwarding, Slice status changes, DAG state)
- [ ] **DAE-07**: Log rotation with structlog + `logging.handlers.RotatingFileHandler`
- [ ] **DAE-08**: Crash recovery: daemon restart replays STATE.md projections from event log, resumes in-flight Steps from their last checkpoint
- [ ] **DAE-09**: `state daemon start|stop|restart|status|logs` CLI
