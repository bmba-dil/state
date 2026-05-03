# v7 — Per-Session Worker

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 060–067 (8 phases)

---

## Phases

#### Phase 060 — Worker main module + bootstrap (spawned by plugin shim)
**Goal:** `state_worker.main`; reads session ID, attaches to daemon, registers hot state.
**Depends on:** 050
**Requirements:** WRK-10
**Parallelizable:** yes

#### Phase 061 — Daemon ↔ worker bridge (HTTP+SSE client)
**Goal:** Worker connects to daemon unix socket; subscribes to SSE for session-scoped events.
**Depends on:** 060, 054
**Requirements:** WRK-10, WRK-12
**Parallelizable:** no

#### Phase 062 — Hot state container (active Slice/Step/drill)
**Goal:** In-memory pydantic container synced from daemon on attach; updated on events.
**Depends on:** 061
**Requirements:** WRK-11
**Parallelizable:** yes with 063

#### Phase 063 — Hook event forwarding (HTTP POST to daemon)
**Goal:** `POST /hook/<name>` with typed payload; retries on transient failure.
**Depends on:** 061
**Requirements:** WRK-12
**Parallelizable:** yes with 062

#### Phase 064 — Version handshake (plugin/daemon compatibility)
**Goal:** Plugin sends `X-State-Plugin-Version`; worker/daemon validates against compat range; refuse attach with error.
**Depends on:** 060
**Requirements:** WRK-13
**Parallelizable:** yes

#### Phase 065 — Session tear-down on opencode close
**Goal:** Plugin signals close → worker flushes pending hook events → exits cleanly.
**Depends on:** 063
**Requirements:** WRK-10
**Parallelizable:** yes

#### Phase 066 — Worker logs + structured logging
**Goal:** Per-worker-PID log file; rotating; redactor attached.
**Depends on:** 056
**Requirements:** OBS-01 (partial)
**Parallelizable:** yes

#### Phase 067 — Multi-session stress test + teardown verifier
**Goal:** 3-session concurrent harness; kill/restart + verify no leaked workers.
**Depends on:** 060..P7
**Requirements:** (verifier for WRK-10..13)
**Parallelizable:** no (final)

---

