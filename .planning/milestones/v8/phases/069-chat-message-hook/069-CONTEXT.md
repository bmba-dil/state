# Phase 069: chat.message Hook - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Parse `/state:*` user messages, reject cross-mode commands, append active Step/Concept hint. Depends on 068 (package scaffolding) and 063 (session state tracking).
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.
</decisions>

<code_context>
## Existing Code Insights

- Mode is `Literal["build", "teach", "kernel"]` in `src/state_core/schema.py:17`
- Daemon has ModeMiddleware in `src/state_daemon/middleware.py`
- opencode plugin API: `chat.message` hook signature is `(input: {sessionID, agent?, model?, messageID?, variant?}, output: {message: UserMessage, parts: Part[]}) => Promise<void>`
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
