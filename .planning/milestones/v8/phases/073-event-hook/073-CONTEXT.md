# Phase 073: event Hook - Context

**Gathered:** 2026-05-05
**Status:** Deferred — `event` key not in opencode Hooks type (v1.14.35)
**Mode:** Identified during implementation

<domain>
## Phase Boundary

Subscribe to `session.idle`, `worktree.ready`, `question.replied`, `permission.replied`, etc.; mirror to daemon. Depends on 068 (package scaffolding).
</domain>

<decisions>
## Implementation Decisions

### Deferred
The `event` hook does not exist in opencode's `Hooks` type as of v1.14.35. Implementation is deferred until the API supports it. The SSE mirror utility can be implemented as a standalone module called from other hooks in the interim.
</decisions>

<code_context>
## Existing Code Insights

- opencode's Hooks type (v1.14.35) does not include an `event` key
- When available, the hook should mirror events to the daemon over HTTP+SSE
- Daemon SSE bus is available at `/events/subscribe`
</code_context>

<specifics>
## Specific Ideas

Deferred — will be implemented when opencode adds the `event` hook to its Hooks type.
</specifics>

<deferred>
## Deferred Ideas

All event hook functionality deferred until upstream API support.
</deferred>
