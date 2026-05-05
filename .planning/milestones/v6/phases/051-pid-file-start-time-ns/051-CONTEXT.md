# Phase 051: pid-file + start_time_ns + stale detection - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`.state/daemon.pid` with `{pid, start_time_ns}`; `/proc/<pid>/stat` on Linux, `ps -o lstart=` on macOS; stale pid → remove and start fresh. Defense against P0-15: stale pid file preventing daemon restart.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Write pid-file atomically (write temp + rename) to prevent partial reads.
- `start_time_ns` = `time.monotonic_ns()` at daemon start — used to detect stale pids (compare process start time vs file start time).
- Platform detection: `sys.platform` for Linux vs Darwin.
- File format: JSON `{"pid": int, "start_time_ns": int}`.
- Module location: `src/state_core/state_daemon/pid.py` or similar.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/` — existing core package
- P0-15 pitfall: stale pid prevents daemon restart
- Depends on: Phase 001 (foundation)

</code_context>

<specifics>
## Specific Ideas

Requirements: DAE-03
Depends on: 001 (foundation)
P0 pitfall: P0-15

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
