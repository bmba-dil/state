# Phase 055: launchd plist + systemd user unit + installer - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`state daemon install` drops plist/unit, enables at login; uninstall removes. The daemon must survive user logout and system reboot — this phase creates the OS-level service definitions for macOS (launchd) and Linux (systemd --user).

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- macOS: Generate `~/Library/LaunchAgents/com.state.daemon.plist` with `KeepAlive=true`, `RunAtLoad=true`.
- Linux: Generate `~/.config/systemd/user/state-daemon.service` with `WantedBy=default.target`.
- Install command discovers the daemon script path via `sys.executable` or entry point.
- Uninstall removes the plist/unit file and unloads the service.
- The service definition passes the project root and socket path as arguments.
- Template-based generation: use `.plist.j2` and `.service.j2` templates.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

Reference:
- `src/state_core/` — existing CLI with Typer commands (Phase 009 pattern)
- Depends on: Phase 051 (pid-file)

</code_context>

<specifics>
## Specific Ideas

Requirements: DAE-01
Depends on: 051 (pid-file + stale detection)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
