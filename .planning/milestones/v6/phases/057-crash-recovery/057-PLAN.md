---
wave: 1
depends_on: ["007", "038"]
files_modified:
  - src/state_daemon/recovery.py
  - src/state_daemon/orchestrator.py
  - tests/test_daemon_recovery.py
autonomous: true
---

# Plan 057-1: Crash Recovery

**Goal:** On daemon start, replay the event log to rebuild projections and resume in-flight Steps in `executing`/`verifying` status — crash recovery without data loss.

**Requirements:** DAE-08

### Tasks

#### 057.1 Recovery Manager

**Acceptance:** `CrashRecovery.recover(store, projector)` replays events, rebuilds projections, finds in-flight Steps.
**Estimated effort:** Medium
**Dependencies:** none

**Details:**
- `CrashRecovery` class in `src/state_daemon/recovery.py`.
- `recover()` method:
  1. Read all events from the event store ordered by aggregate_seq.
  2. Feed each event through the projector (Phase 008) to rebuild steps/slices/concepts caches.
  3. After replay, query steps table for status IN (`executing`, `verifying`).
  4. Return `RecoveryResult` with: `events_replayed: int`, `in_flight_steps: list[StepId]`, `projection_valid: bool`.
- Track last replayed event ULID as a recovery bookmark.
- Handle clean state (no events, no steps) — recovery is a no-op.
- Test: unit tests with in-memory event store, verify projection rebuild, in-flight detection.

**Files:**
- `src/state_daemon/recovery.py` — new file

#### 057.2 In-Flight Step Resume Logic

**Acceptance:** In-flight `executing` steps are resumed from last snapshot; `verifying` steps are re-verified.
**Estimated effort:** Medium
**Dependencies:** 057.1

**Details:**
- For `executing` Steps: emit a `state.step.resumed` event, reload step's context from STEP.md.
- For `verifying` Steps: re-run the verify contract against current state.
- If a snapshot exists (Phase 038, soft dep): restore worktree state from snapshot before resuming.
- If no snapshot: resume with current working tree state (best effort).
- Structured logging at each recovery step.
- Test: unit tests for resume decisions, snapshot integration (can mock Phase 038 dependency).

**Files:**
- `src/state_daemon/recovery.py` — extend with resume logic

#### 057.3 Orchestrator Integration

**Acceptance:** `startup()` runs crash recovery after repair/migrate/reconcile and before server start.
**Estimated effort:** Small
**Dependencies:** 057.2

**Details:**
- Add `CrashRecovery.recover()` call to `orchestrator.startup()`.
- Placement: after Step 3 (reconciler), before Step 4 (server start).
- Log recovery summary: events replayed, steps found, actions taken.
- If recovery fails (corrupt event store), log critical error and exit.
- Test: integration test that simulates crash (in-flight steps in DB) and verifies recovery flags them.

**Files:**
- `src/state_daemon/orchestrator.py` — add recovery step

### Integration Notes

- Phase 038 (worktree snapshots) is a soft dependency — recovery works without snapshots (best effort resume).
- Phase 007 (monotonic seq crash-recovery) handles event sequence integrity — this phase handles application state recovery.
- The recovery bookmark enables incremental recovery in future optimizations.

### must_haves

1. Event log replayed to rebuild projections on daemon start.
2. In-flight `executing` and `verifying` Steps detected and flagged.
3. Recovery runs before the server accepts connections.
4. Clean startup (no events) is a no-op.
5. Recovery failure exits with a clear error message.
