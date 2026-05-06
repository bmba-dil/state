---
phase: "078"
phase_name: "shell.env Hook"
goal: "Export STATE_ARC, STATE_PHASE, STATE_SLICE, STATE_STEP, STATE_WORKTREE, STATE_DAEMON_URL, STATE_AUTH_JSON"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-10]
---

## Plan 1: Implement `shell.env` Hook

**Goal:** Export all 7 STATE_* environment variables to shell sessions.

### Tasks

#### 1.1 Create Environment Variable Injection
**Acceptance:** `packages/opencode-plugin/src/hooks/shell-env.ts` exports the hook
**Estimated effort:** Small
**Dependencies:** 068

<acceptance_criteria>
- grep 'shell.env' packages/opencode-plugin/src/hooks/shell-env.ts
- grep 'STATE_ARC\|STATE_PHASE\|STATE_SLICE\|STATE_STEP' packages/opencode-plugin/src/hooks/shell-env.ts
- grep 'STATE_WORKTREE\|STATE_DAEMON_URL\|STATE_AUTH_JSON' packages/opencode-plugin/src/hooks/shell-env.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/shell-env.ts`:

1. Read STATE_ARC, STATE_PHASE, STATE_SLICE, STATE_STEP from process.env
2. Read STATE_WORKTREE from process.env.STATE_WORKTREE
3. Set STATE_DAEMON_URL default: `http://localhost:9337`
4. Set STATE_AUTH_JSON default: `.state/auth.json`
5. Return env map with all 7 variables
6. Export as `export const shellEnv: Hooks["shell.env"]`
</action>

#### 1.2 Register Hook and Verify Build
**Acceptance:** Hook registered; build passes
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'shell.env' packages/opencode-plugin/src/index.ts
- bun run build exits 0; bun run typecheck exits 0
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] Export STATE_ARC, STATE_PHASE, STATE_SLICE, STATE_STEP
- [ ] Export STATE_WORKTREE
- [ ] Export STATE_DAEMON_URL
- [ ] Export STATE_AUTH_JSON
- [ ] Hook registered in server
- [ ] TypeScript compiles cleanly
