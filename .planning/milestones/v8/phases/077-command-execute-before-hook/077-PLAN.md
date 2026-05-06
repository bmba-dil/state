---
phase: "077"
phase_name: "command.execute.before Hook"
goal: "Reject cross-mode slash commands; inject expanded .planning/*.md content"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-09]
---

## Plan 1: Implement `command.execute.before` Hook

**Goal:** Block cross-mode slash commands and inject expanded planning context.

### Tasks

#### 1.1 Create Command Gate and Context Injection
**Acceptance:** `packages/opencode-plugin/src/hooks/command-execute-before.ts` exports the hook
**Estimated effort:** Medium
**Dependencies:** 068

<acceptance_criteria>
- grep 'command.execute.before' packages/opencode-plugin/src/hooks/command-execute-before.ts
- grep '/state:build:\|/state:teach:' packages/opencode-plugin/src/hooks/command-execute-before.ts
- grep 'state:build\|state:teach' packages/opencode-plugin/src/hooks/command-execute-before.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/command-execute-before.ts`:

1. Implement `detectCurrentMode()` — reads from process.env.STATE_MODE
2. Implement `isCrossModeCommand(command, mode)` — detects cross-mode slash command usage
3. Implement `injectPlanningContext(args)` — appends relevant `.planning/*.md` content
4. Implement the main hook function that rejects cross-mode commands
5. Export as `export const commandExecuteBefore: Hooks["command.execute.before"]`
</action>

#### 1.2 Register Hook and Verify Build
**Acceptance:** Hook registered; build passes
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'command.execute.before' packages/opencode-plugin/src/index.ts
- bun run build exits 0; bun run typecheck exits 0
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] Reject `/state:build:*` in teach mode
- [ ] Reject `/state:teach:*` in build mode
- [ ] Hook registered in server
- [ ] TypeScript compiles cleanly
