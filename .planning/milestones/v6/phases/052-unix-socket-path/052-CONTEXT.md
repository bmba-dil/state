# Phase 052: Unix socket path - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Project-hash-based socket name; fallback when `$XDG_RUNTIME_DIR` missing (macOS). The daemon binds to a unix domain socket — this phase determines the socket path with a deterministic hash-based naming scheme.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Socket name: `state-<sha256-hash-of-project-root>.sock`
- Prefer `$XDG_RUNTIME_DIR` on Linux (typically `/run/user/<uid>/`); fallback to `$TMPDIR` or `/tmp` on macOS.
- Path stored in `.state/daemon.sock` for worker discovery.
- Module location: `src/state_core/state_daemon/socket.py`.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/` — existing core package
- Depends on: Phase 050 (HTTP server)

</code_context>

<specifics>
## Specific Ideas

Requirements: DAE-04
Depends on: 050 (HTTP server + unix socket binding)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
