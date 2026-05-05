---
phase: 086-plugin-install-script
plan: 01
subsystem: opencode-plugin-tui
tags: [tui, plugin, auto-install, mcp, first-run]
requires:
  provides:
    - First-run auto-install hook in createTuiPlugin()
    - Self-registration of @state/opencode-plugin via TuiPluginInstallOptions
    - Auto-registration of state-build and state-teach MCP servers
    - Unit tests covering first-run, idempotency, and error isolation
  affects: [plugin-deployment, mcp-server-discovery, onboarding]
tech-stack:
  added: []
  patterns:
    - "Fire-and-forget install pattern: .then()/.catch() for non-blocking plugin registration"
key-files:
  created:
    - packages/opencode-plugin/src/tui/plugin-install.test.ts
  modified:
    - packages/opencode-plugin/src/tui.ts
key-decisions:
  - "Non-blocking MCP registration — uses .then/.catch (not await) so plugin load never stalls"
  - "Errors logged but never thrown — plugin load always succeeds even if MCP registration fails"
  - "api.client.mcp.add() passes config properties directly (no body wrapper per actual SDK signature)"
  - "MCP server commands are [name] arrays matching Python entry points (state-build, state-teach)"
  - "createTuiPlugin exported for testability"
patterns-established:
  - "First-run gate pattern: if (meta.state === 'first') { /* fire-and-forget install */ }"
  - "Mock API pattern: makeApi() factory with _installCalls/_mcpAddCalls trackers for test assertions"
requirements-completed: [TUI-05]
metrics:
  duration: 3m
  completed: 2026-05-05
---

# Phase 086 Plan 01: Plugin Auto-Install Script Summary

**One-liner:** Eliminate the manual `install.sh` step by adding a first-run auto-install hook that self-registers the plugin and both MCP servers via the opencode TUI plugin API.

## Tasks Completed

| # | Task | Type | Commit | Key Files |
|---|------|------|--------|-----------|
| 1 | Add first-run auto-install hook | auto | `165a252` | `packages/opencode-plugin/src/tui.ts` |
| 2 | Write unit tests for auto-install | tdd | `d2692d7` | `packages/opencode-plugin/src/tui/plugin-install.test.ts` |

## What Was Built

### Task 1: First-run auto-install hook

Modified `createTuiPlugin()` in `tui.ts` to accept the full `TuiPlugin` signature with `meta` parameter. Added a first-run gate (`meta.state === "first"`) at the top of the returned async function that:

1. **Self-registers the plugin** via `api.plugins.install("@state/opencode-plugin", { global: false })` — uses `TuiPluginInstallOptions` API for project-level installation.
2. **Registers both MCP servers** (`state-build`, `state-teach`) via `api.client.mcp.add()` with `McpLocalConfig` (`type: "local"`, `command: [name]`, `enabled: true`).

Key design properties:
- **Non-blocking**: Uses `.then()/.catch()` (not `await`) — MCP registration never blocks theme installation or slot registration.
- **Error-resilient**: Errors are logged via `log()` but never thrown — plugin load always succeeds.
- **Idempotent**: Non-first states (`"updated"`, `"same"`) are no-ops.

### Task 2: Unit tests

Created `plugin-install.test.ts` with 8 test cases using `bun:test`:

| # | Test | Covers |
|---|------|--------|
| 1 | Accepts TuiPlugin signature | API contract compliance |
| 2 | Calls `api.plugins.install` with correct args | First-run plugin self-registration |
| 3 | Calls `api.client.mcp.add` for both servers | MCP server registration |
| 4 | Passes correct `McpLocalConfig` | Config shape validation |
| 5 | Idempotency: `"updated"` state | No-ops for non-first states |
| 6 | Idempotency: `"same"` state | No-ops for non-first states |
| 7 | Error isolation on `mcp.add` rejection | Plugin load survives MCP failures |
| 8 | Existing setup preserved after install | Theme/slots/SSE still function |

## Verification

- `bun run typecheck` — passes cleanly (0 errors)
- `bun test src/tui/plugin-install.test.ts` — 8 pass, 0 fail, 19 expects
- No file deletions in commits
- No stubs or placeholders introduced

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `api.client.mcp.add()` parameter shape**
- **Found during:** Task 1 typecheck
- **Issue:** Plan template used `{ body: { name, config } }` wrapper, but the actual SDK signature expects `name` and `config` as direct properties (`{ name, config }`).
- **Fix:** Removed the `body` wrapper — `api.client.mcp.add({ name, config: {...} })` instead of `api.client.mcp.add({ body: { name, config: {...} } })`.
- **Files modified:** `packages/opencode-plugin/src/tui.ts`
- **Commit:** `165a252`

## Threat Flags

None — no new security surface beyond what was documented in the plan's threat model. Plugin runs within daemon's process context; MCP add calls route through daemon's existing auth session.

## Self-Check

- [x] `packages/opencode-plugin/src/tui.ts` exists and contains first-run auto-install logic
- [x] `packages/opencode-plugin/src/tui/plugin-install.test.ts` exists with 8 passing tests
- [x] Commit `165a252` present in git log (feat: first-run auto-install)
- [x] Commit `d2692d7` present in git log (test: unit tests)
- [x] Typecheck passes with 0 errors
- [x] All 8 tests pass with 0 failures

## Self-Check: PASSED
