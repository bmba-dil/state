# Phase 099: MCP registration toggle (config hook) - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Plugin reads `.state/mode.json` at boot; `config` hook returns enabled/disabled for each server; hot-reload on mode change.

**Goal:** The `@state/opencode-plugin` TypeScript bundle reads `.state/mode.json` at startup and uses the opencode `config` hook to dynamically enable/disable the `state-build` and `state-teach` MCP servers based on the active mode. When mode changes (via `state.mode.activated` event), the plugin hot-reloads its MCP registration.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key considerations:
- This is layer 3 of 6 for mode enforcement
- Plugin reads `.state/mode.json` at boot time (same file from Phase 097)
- OpenCode `config` hook controls which MCP servers are registered
- Hot-reload: when `state.mode.activated` event fires, re-read mode.json and re-apply config
- Build server enabled when mode in {build, both}; teach server enabled when {teach, both}
</decisions>

<code_context>
## Existing Code Insights

### Plugin package (Phase 068)
- `@state/opencode-plugin` TS package exists
- Implements opencode hooks system
- 9 server hooks already implemented (Phase 079)

### Mode config (Phase 097-098)
- `.state/mode.json` schema validated by `ModeConfig` in `src/state_core/schema.py`
- `state mode init` CLI bootstraps file
- `.state/build/` and `.state/teach/` subtrees created

### MCP servers
- `src/state_build/mcp.py` — Build-mode MCP server
- `src/state_teach/mcp.py` — Teach-mode MCP server
- Both registered when their respective mode is active
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Implement per ROADMAP phase goal and MODE-03 requirement.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
