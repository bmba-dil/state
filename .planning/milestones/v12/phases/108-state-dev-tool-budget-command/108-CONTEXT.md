# Phase 108: state-dev-tool-budget-command — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Infrastructure — auto-generated (CLI tool phase, discuss skipped)

<domain>
## Phase Boundary

`state dev tool-budget` command + CI assertion.

Sum tool-description tokens, refuse > budget. The command loads MCP tools from the state-build server module, counts tokens in their descriptions, and exits non-zero if the total exceeds the 15 × 80 = 1200 token budget. Designed to run in CI as a pre-commit or PR gate.
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion.

Key technical decisions:
- Add `dev` sub-app to `state_cli` with `tool-budget` command
- Load tools by importing `state_build.mcp` and introspecting `_tool_manager._tools`
- Token counting: use simple word-based heuristic (split on whitespace) since tiktoken is rejected
- Budget: 15 tools × 80 tokens = 1200 total tokens
- Exit code 0 if within budget, 1 if exceeded
- Optional `--server` flag to specify state-build or state-teach (default: state-build)
</decisions>

<code_context>
## Existing Code Insights

### CLI pattern (state_cli/main.py)
- Typer-based CLI with sub-apps
- Commands are registered via `app.add_typer(sub_app)`
- Error handling: `typer.echo(err=True)` + `raise typer.Exit(code=1)`

### Tool introspection
- `state_build.mcp` exposes `mcp._tool_manager._tools` dict
- Each tool has `.name` and `.description` attributes
</code_context>

<specifics>
## Specific Ideas

Output format:
```
Tool                 Tokens  Budget  Status
──────────────────────────────────────────
plan_step            12      80      ✓
execute_step         11      80      ✓
...
──────────────────────────────────────────
TOTAL                185     1200    ✓ PASS
```

CI usage: `state dev tool-budget || exit 1`
</specifics>

<deferred>
## Deferred Ideas

- Phase 108 CI integration (hook into pre-commit or GitHub Actions) — out of scope, just the command
- Support for state-teach tools
</deferred>
