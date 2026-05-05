# Phase 057: Crash recovery - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

On start, read last events, rebuild STATE.md projection, find Steps in `executing`/`verifying` → resume from last checkpoint. The daemon must survive crashes without data loss — this phase implements crash recovery that replays the event log to rebuild in-memory state and resumes in-flight work.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Read last events from `.state/events.sqlite` ordered by `aggregate_seq` per aggregate.
- Feed events through the projector (Phase 008) to rebuild steps/slices/concepts cache.
- Find Steps with status `executing` or `verifying` — these were in-flight at crash time.
- Resume policy: re-execute `executing` Steps from their last snapshot; re-verify `verifying` Steps.
- Checkpoint: last event ULID written to a recovery bookmark after successful crash recovery.
- Integration with worktree snapshots (Phase 038, soft dep) — if snapshot exists, restore worktree state too.
- Module location: `src/state_core/state_daemon/recovery.py`.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/store.py` — event store with `read_events` method
- `src/state_core/projector.py` — Phase 008 projector that rebuilds projections
- Phase 007: monotonic seq crash-recovery (P0-9 — different concern but similar pattern)
- Depends on: Phase 007 (crash recovery for event seq), Phase 038 (worktree snapshots, soft)

</code_context>

<specifics>
## Specific Ideas

Requirements: DAE-08
Depends on: 007 (monotonic seq crash-recovery), 038 (worktree snapshots, soft)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
