---
phase: "071"
phase_name: "tool.execute.after Hook"
goal: "Build: match against Step verify_contract; Teach: classify + feed mental_model"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-03]
---

## Plan 1: Implement `tool.execute.after` Hook

**Goal:** Implement the `tool.execute.after` hook that verifies tool outputs against build contracts and records teach observations.

### Tasks

#### 1.1 Create Output Verification and Observation Logic
**Acceptance:** `packages/opencode-plugin/src/hooks/tool-execute-after.ts` exports a `toolExecuteAfter` hook function
**Estimated effort:** Medium
**Dependencies:** 068

<acceptance_criteria>
- grep 'export.*toolExecuteAfter' packages/opencode-plugin/src/hooks/tool-execute-after.ts
- grep 'verifyBuildOutput\|recordTeachObservation' packages/opencode-plugin/src/hooks/tool-execute-after.ts
- grep 'tool.execute.after' packages/opencode-plugin/src/hooks/tool-execute-after.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/tool-execute-after.ts`:

1. Implement `verifyBuildOutput(result, contract)` — validates tool output matches Step verify_contract
2. Implement `recordTeachObservation(toolName, result)` — classifies output and feeds observation
3. Implement the main `toolExecuteAfter` hook function that dispatches based on current mode
4. Export as `export const toolExecuteAfter: Hooks["tool.execute.after"]`
</action>

#### 1.2 Register Hook in Plugin Server
**Acceptance:** Hook registered in `src/index.ts`
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'toolExecuteAfter' packages/opencode-plugin/src/index.ts
- grep 'tool.execute.after' packages/opencode-plugin/src/index.ts
</acceptance_criteria>

#### 1.3 Build Verification
**Acceptance:** `bun run build` and `bun run typecheck` pass
**Estimated effort:** Small
**Dependencies:** 1.1, 1.2

### Verification Criteria (must_haves)
- [ ] Build mode verifies output against Step contract
- [ ] Teach mode classifies + feeds observation
- [ ] Hook registered in server
- [ ] TypeScript compiles cleanly
