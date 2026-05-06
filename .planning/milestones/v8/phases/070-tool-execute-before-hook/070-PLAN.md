---
phase: "070"
phase_name: "tool.execute.before Hook"
goal: "Block writes outside active Slice worktree; block mcp__state-teach__* in build mode; rewrite .state/ path args"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-02]
---

## Plan 1: Implement `tool.execute.before` Hook

**Goal:** Implement the `tool.execute.before` hook that blocks cross-mode tool invocations, enforces worktree scope, and rewrites `.state/` paths.

### Tasks

#### 1.1 Create Mode Gate and Scope Gate Logic
**Acceptance:** `packages/opencode-plugin/src/hooks/tool-execute-before.ts` exports a `toolExecuteBefore` hook function
**Estimated effort:** Medium
**Dependencies:** 068

<acceptance_criteria>
- grep 'export.*toolExecuteBefore' packages/opencode-plugin/src/hooks/tool-execute-before.ts
- grep 'tool.execute.before' packages/opencode-plugin/src/hooks/tool-execute-before.ts
- grep 'mcp__state-teach__\|mcp__state-build__' packages/opencode-plugin/src/hooks/tool-execute-before.ts
- grep 'rewriteStatePaths\|.state/' packages/opencode-plugin/src/hooks/tool-execute-before.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/tool-execute-before.ts`:

1. Implement `detectCurrentMode()` — reads from process.env.STATE_MODE
2. Implement `isCrossModeTool(toolName, mode)` — blocks `mcp__state-teach__*` in build mode, `mcp__state-build__*` in teach mode
3. Implement `rewriteStatePaths(args)` — transforms `.state/` prefix to `$STATE_HOME/`
4. Implement the main `toolExecuteBefore` hook function that rejects cross-mode tools and rewrites paths
5. Export as `export const toolExecuteBefore: Hooks["tool.execute.before"]`
</action>

#### 1.2 Register Hook in Plugin Server
**Acceptance:** `packages/opencode-plugin/src/index.ts` exports `toolExecuteBefore` in server hooks
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'toolExecuteBefore' packages/opencode-plugin/src/index.ts
- grep 'tool.execute.before' packages/opencode-plugin/src/index.ts
</acceptance_criteria>

<action>
Update `packages/opencode-plugin/src/index.ts`: import and register `toolExecuteBefore` as `"tool.execute.before"`.
</action>

#### 1.3 Build Verification
**Acceptance:** `bun run build` and `bun run typecheck` pass
**Estimated effort:** Small
**Dependencies:** 1.1, 1.2

<acceptance_criteria>
- bun run build exits 0 in packages/opencode-plugin/
- bun run typecheck exits 0 in packages/opencode-plugin/
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] Block `mcp__state-teach__*` in build mode
- [ ] Block `mcp__state-build__*` in teach mode
- [ ] Rewrite `.state/` path args for state tools
- [ ] Hook registered in server
- [ ] TypeScript compiles cleanly
