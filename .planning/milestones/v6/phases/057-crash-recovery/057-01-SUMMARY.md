---
phase: 057-crash-recovery
plan: 01
subsystem: infra
tags: [crash-recovery, event-sourcing, CQRS, projection-rebuild, sqlite, aiosqlite]

# Dependency graph
requires:
  - phase: 007
    provides: monotonic seq crash-recovery (aggregate_seq repair)
  - phase: 008
    provides: Projector class (CQRS projection engine)
  - phase: 038
    provides: worktree snapshots (soft dep — best-effort integration)
  - phase: 054
    provides: SSE broadcast bus (wired before recovery)
provides:
  - CrashRecovery class that replays event log through Projector on daemon start
  - In-flight Step detection (executing/verifying status) after crash
  - Resume logic with state.step.resumed event emission
  - Recovery bookmark (last event ULID) for future incremental recovery
  - Worktree snapshot availability detection (Phase 038 soft dep)
  - Integration into daemon orchestrator startup() sequence
affects: [daemon-startup, worker-resume, step-lifecycle, event-store]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CQRS replay recovery: truncate cache tables → replay ALL events through projector → detect in-flight"
    - "Recovery bookmark pattern: last event ULID stored for incremental recovery optimization"
    - "Soft dependency pattern: snapshot integration is best-effort — recovery works without Phase 038"
    - "Event emission for audit: state.step.resumed events record pre-crash status + snapshot flag"

key-files:
  created:
    - src/state_daemon/recovery.py — CrashRecovery, InFlightStep, RecoveryResult, ResumeAction, _check_snapshot
    - tests/test_daemon_recovery.py — 33 unit + integration tests
  modified:
    - src/state_daemon/orchestrator.py — Step 3.6 crash recovery in startup()

key-decisions:
  - "Projector.rebuild_all() used for full replay instead of per-event apply_event() — truncate+replay is simpler and already battle-tested"
  - "CrashRecovery does NOT own the event store — resume_in_flight accepts store as parameter to avoid coupling"
  - "state.step.resumed event emitted with pre_crash_status and snapshot_available in data — worker agents read this to decide resume strategy"
  - "Recovery failure is fatal (SystemExit) — corrupt event store must not allow daemon to accept connections"
  - "Snapshot detection is directory-based (Path.is_dir()) — lightweight, no dependency on SnapshotManager internals"

patterns-established:
  - "Recovery-first startup: projections rebuilt before server accepts connections"
  - "Event-as-audit: state.step.resumed is recorded even without a projection handler — pure audit trail"
  - "Soft dependency handling: snapshot_available flag in event data lets workers decide restore strategy"

requirements-completed: ["DAE-08"]

# Metrics
duration: 11min
completed: 2026-05-05
---

# Phase 057 Plan 01: Crash Recovery Summary

**CQRS event-log replay on daemon start — rebuilds steps/slices/concepts caches, detects and resumes in-flight Steps via state.step.resumed events, with snapshot-aware best-effort resume**

## Performance

- **Duration:** 11 min
- **Started:** 2026-05-05T01:57:11Z
- **Completed:** 2026-05-05T02:07:57Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **CrashRecovery class** (`src/state_daemon/recovery.py`) replays all events through `Projector.rebuild_all()` to rebuild projections, then queries the `steps` cache table for in-flight Steps (status `executing` or `verifying`)
- **Resume logic** emits `state.step.resumed` events with pre-crash status and snapshot availability flags — worker agents use this data to decide resume strategy
- **Orchestrator integration** adds Step 3.6 to `startup()`: recovery runs after SSE bus wiring but before server socket bind, so no connections are accepted until projections are rebuilt. Fatal `SystemExit(1)` on projection failure
- **Recovery bookmark** tracks the last event ULID for future incremental recovery optimization
- **33 tests** covering clean state, in-flight detection, event persistence, snapshot integration, resume failure, and full orchestration flow

## Task Commits

Each task was committed atomically:

1. **Task 057.1: Recovery Manager** - `53bc408` (feat)
2. **Task 057.2: In-Flight Step Resume Logic** - `7a27ae6` (feat)
3. **Task 057.3: Orchestrator Integration** - `b23bf76` (feat)

## Files Created/Modified

- `src/state_daemon/recovery.py` — CrashRecovery class with `recover()`, `resume_in_flight()`, `_find_in_flight_steps()`, `_get_last_event_id()`; dataclasses: `InFlightStep`, `RecoveryResult`, `ResumeAction`; helper: `_check_snapshot()`
- `src/state_daemon/orchestrator.py` — Added Step 3.6 crash recovery call + `_build_in_flight_steps()` helper; imports for `Projector`, `CrashRecovery`, `InFlightStep`, `get_connection`, `aiosqlite`
- `tests/test_daemon_recovery.py` — 33 tests across 10 test classes

## Decisions Made

- **Full rebuild over incremental:** `Projector.rebuild_all()` (truncate + replay all) chosen over per-event `apply_event()` — simpler, already battle-tested in Phase 008, and startup latency is acceptable
- **Store passed as parameter:** `resume_in_flight(store, ...)` rather than storing `SqliteEventStore` in `CrashRecovery.__init__` — avoids coupling recovery manager to store lifecycle
- **Event emission without projection handler:** `state.step.resumed` recorded as pure audit trail — no projection handler registered because the step's cache state (`executing`/`verifying`) is already correct
- **Fatal on corruption:** Projection rebuild failure → `SystemExit(1)` — must not serve requests with stale projections
- **Snapshot as directory check:** `Path(snapshot_root / step_id).is_dir()` — lightweight, zero coupling to `SnapshotManager`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Crash recovery foundation complete — daemon survives restarts without losing in-flight Step state
- Worker agents (future phase) will read `state.step.resumed` events to decide resume strategy
- Recovery bookmark (`last_event_id`) ready for incremental recovery optimization in a future phase

---
*Phase: 057-crash-recovery*
*Completed: 2026-05-05*
