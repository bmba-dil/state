# Phase 070: tool.execute.before Hook - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Block writes outside active Slice worktree; block `mcp__state-teach__*` in build mode; rewrite `.state/` path args. Depends on 068 (package scaffolding).
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.
</decisions>

<code_context>
## Existing Code Insights

- Mode is `Literal["build", "teach", "kernel"]` in `src/state_core/schema.py`
- opencode plugin API: `tool.execute.before` hook signature is `(input: {tool_call_id, tool_name, args, session_id}, output: {args}) => Promise<void>`
- MCP tools are named `mcp__state-build__*` and `mcp__state-teach__*`
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
