---
phase: 065
gathered: "2026-05-05"
autonomous: true
---

# Phase 065 — Session Tear-Down on Opencode Close

<domain>
## Phase Boundary

Plugin signals close → worker flushes pending hook events → exits cleanly.

Worker accumulates hook events during session. On shutdown signal (SIGTERM/SIGINT or plugin close), flushes all pending hooks to daemon via forward_hook before disconnecting.
</domain>

<decisions>
## Implementation Decisions

### HookQueue: simple list-based buffer
stores (hook_name, payload) tuples. flush_pending iterates and forwards each with forward_hook.

### Best-effort flush
Flush runs regardless of forward_hook failures. Failed hooks are logged but don't block teardown. Queue is always cleared after flush.

### Flush before bridge disconnect
Ensures all hook events are delivered to daemon before the SSE connection is torn down.
</decisions>

<code_context>
## Existing Code Insights

- `forward_hook` (Phase 063) handles HTTP POST with retry
- Main shutdown sequence already handles bridge disconnect + PID cleanup
- Shutdown triggered by SIGTERM/SIGINT via _shutdown_event
</code_context>

<specifics>

</specifics>

<deferred>
## Deferred Ideas

None
</deferred>
