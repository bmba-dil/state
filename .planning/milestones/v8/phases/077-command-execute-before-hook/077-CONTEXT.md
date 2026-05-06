# Phase 077: command.execute.before Hook - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Reject `/state:build:*` when mode=teach, and vice versa; inject expanded `.planning/*.md` content. Depends on 068 (package scaffolding).
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.
</decisions>

<code_context>
## Existing Code Insights

- opencode plugin API: `command.execute.before` hook intercepts slash command execution
- Build commands: `/state:build:*` — must be blocked in teach mode
- Teach commands: `/state:teach:*` — must be blocked in build mode
- `.planning/*.md` content can be injected as context for relevant commands
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
