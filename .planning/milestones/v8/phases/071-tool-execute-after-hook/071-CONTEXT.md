# Phase 071: tool.execute.after Hook - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Build: match against Step `verify_contract`; Teach: classify + feed mental_model. Depends on 068 (package scaffolding).
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.
</decisions>

<code_context>
## Existing Code Insights

- opencode plugin API: `tool.execute.after` hook signature is `(input: {tool_call_id, tool_name, args, result, session_id}, output: {result}) => Promise<void>`
- Build verification compares tool output against expected contracts
- Teach observation feeds into the mental-model projection
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
