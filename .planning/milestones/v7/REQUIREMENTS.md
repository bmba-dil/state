# v7 — Per-Session Worker Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Kernel: Per-Session Worker (A7)

- [ ] **WRK-10**: Worker attaches to daemon on opencode session start; tears down on session close
- [ ] **WRK-11**: Worker owns hot state for the current session (active Slice, current Step FSM position, in-progress drill)
- [ ] **WRK-12**: Worker forwards opencode hook events to daemon over HTTP+SSE
- [ ] **WRK-13**: Mismatched plugin/daemon version negotiation — handshake header on worker attach; refuses on incompatible
