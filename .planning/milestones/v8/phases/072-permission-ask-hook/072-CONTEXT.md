# Phase 072: permission.ask Hook - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Auto-approve within scope; route to dialog otherwise; persist `state.permission.decided`. Depends on 068 (package scaffolding).
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.
</decisions>

<code_context>
## Existing Code Insights

- opencode plugin API: `permission.ask` hook signature is `(input: {permission_id, tool_name, args, session_id, message}, output: {decision, reason}) => Promise<void>`
- Gray-area decisions are auto-approved when tool is within current mode scope
- Decisions are persisted for audit trail
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
