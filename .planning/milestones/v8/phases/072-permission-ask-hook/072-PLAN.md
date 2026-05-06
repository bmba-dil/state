---
phase: "072"
phase_name: "permission.ask Hook"
goal: "Auto-approve within scope; route to dialog otherwise; persist state.permission.decided"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-04]
---

## Plan 1: Implement `permission.ask` Hook

**Goal:** Implement the `permission.ask` hook that auto-approves state-internal permissions and persists decisions.

### Tasks

#### 1.1 Create Permission Routing Logic
**Acceptance:** `packages/opencode-plugin/src/hooks/permission-ask.ts` exports a `permissionAsk` hook function
**Estimated effort:** Medium
**Dependencies:** 068

<acceptance_criteria>
- grep 'export.*permissionAsk' packages/opencode-plugin/src/hooks/permission-ask.ts
- grep 'isStateInternal\|permission\.decided' packages/opencode-plugin/src/hooks/permission-ask.ts
- grep 'permission.ask' packages/opencode-plugin/src/hooks/permission-ask.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/permission-ask.ts`:

1. Implement `isStateInternal(toolName, args)` — checks if tool belongs to state's scope
2. Implement `persistDecision(permissionId, decision)` — logs decision with `permission.decided` type
3. Implement the main `permissionAsk` hook function that auto-approves internal tools, routes others to dialog
4. Export as `export const permissionAsk: Hooks["permission.ask"]`
</action>

#### 1.2 Register Hook and Verify Build
**Acceptance:** Hook registered in `src/index.ts`; build passes
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'permissionAsk' packages/opencode-plugin/src/index.ts
- bun run build exits 0; bun run typecheck exits 0
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] Auto-approve state-internal permissions
- [ ] Persist permission decisions
- [ ] Hook registered in server
- [ ] TypeScript compiles cleanly
