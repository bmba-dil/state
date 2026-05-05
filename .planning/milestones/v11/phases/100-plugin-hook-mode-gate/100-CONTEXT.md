# Phase 100: Plugin hook mode gate - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`command.execute.before` rejects `/state:build:*` when mode=teach; `tool.execute.before` rejects `mcp__state-teach__*` when mode=build.

**Goal:** The @state/opencode-plugin's `command.execute.before` and `tool.execute.before` hooks enforce mode isolation by rejecting cross-mode commands and tool invocations. This is layer 4 of the 6-layer defense-in-depth.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion. Key considerations:
- Refine existing hooks from Phase 069/070/077
- command.execute.before: reject /state:build:* commands when mode is "teach"
- tool.execute.before: reject mcp__state-teach__* tools when mode is "build"
- Both modes allowed when mode is "both" (permissive)
- Read .state/mode.json to determine active mode
</decisions>

<code_context>
## Existing Code Insights
- Plugin hooks exist in packages/opencode-plugin/src/hooks/
- Mode config from Phase 097: .state/mode.json with ModeConfig
- Config hook from Phase 099 already reads mode.json
- Existing hooks: command.execute.before, tool.execute.before (Phase 069/070/077)
</code_context>

<specifics>
## Specific Ideas
No specific requirements. Implement per ROADMAP phase goal and MODE-04 requirement.
</specifics>

<deferred>
None.
</deferred>
