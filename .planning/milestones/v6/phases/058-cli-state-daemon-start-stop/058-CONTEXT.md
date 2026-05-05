# Phase 058: CLI: state daemon start|stop|restart|status|logs - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Typer commands; `status` shows pid + start_time + events-count + mode; `logs` tails daemon.log. The user-facing CLI for managing the state daemon lifecycle — start/stop/restart/status/logs commands.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- Commands: `state daemon start`, `state daemon stop`, `state daemon restart`, `state daemon status`, `state daemon logs`.
- `start`: Launches daemon as background process (or via launchd/systemd if installed); writes pid-file.
- `stop`: Sends SIGTERM to daemon pid; waits for graceful shutdown; SIGKILL after timeout.
- `restart`: stop + start with short delay.
- `status`: Reads pid-file, checks if process alive, shows pid/start_time/events-count/mode/socket-path.
- `logs`: `tail -f` equivalent on `.state/logs/daemon.log` with optional `--follow` and `--lines N`.
- Typer app: integrate with existing `state` CLI from Phase 009 (add `daemon` subcommand group).
- Integration with Phase 051 (pid-file), Phase 055 (launchd/systemd), Phase 056 (logging).

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/cli/` — existing Typer CLI with `events` subcommand (Phase 009)
- Phase 051: pid-file management
- Phase 055: launchd/systemd service definitions

</code_context>

<specifics>
## Specific Ideas

Requirements: DAE-09
Depends on: 051 (pid-file), 055 (service installer)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
