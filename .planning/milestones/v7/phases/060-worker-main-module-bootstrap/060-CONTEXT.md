# Phase 060: Worker Main Module + Bootstrap — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`state_worker.main`; reads session ID, attaches to daemon, registers hot state.

Requirements: WRK-10 (worker attaches to daemon on opencode session start; tears down on session close)
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key references:
- Daemon socket discovery via `.state/daemon.sock` marker file (`state_daemon/socket.py:95-113`)
- Daemon HTTP server on Unix socket (`state_daemon/server.py`)
- Daemon logging config (`state_daemon/logging.py`)
- Observability redactor (`state_core/observability/redactor.py`)
- Phase depends on: 050 (daemon shipped)
</decisions>

<code_context>
## Existing Code Insights

- `state_worker/` package exists with stub `__init__.py`, `main.py`, `bridge.py`
- `state_daemon/socket.py` provides `read_socket_path()` for socket discovery
- `state_daemon/server.py` is an async HTTP/1.1 server on Unix socket
- `state_daemon/logging.py` uses structlog + RotatingFileHandler with redaction
- Project uses `structlog` for structured logging throughout
</code_context>

<specifics>
## Specific Ideas

- Worker reads session ID from environment variable or CLI arg
- Worker discovers daemon socket via `.state/daemon.sock`
- Worker registers session with daemon on attach (POST handshake)
- Worker maintains its own PID file for lifecycle management
- Entry point: `python -m state_worker` or CLI command
</specifics>

<deferred>
## Deferred Ideas

- HTTP+SSE client bridge — Phase 061
- Hot state container — Phase 062
- Hook event forwarding — Phase 063
- Version handshake — Phase 064
- Session tear-down — Phase 065
- Per-worker logging — Phase 066
</deferred>
