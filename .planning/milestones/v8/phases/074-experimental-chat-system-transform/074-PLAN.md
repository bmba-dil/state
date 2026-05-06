---
phase: "074"
phase_name: "experimental.chat.system.transform Hook"
goal: "Prepend mode banner + active artifact content per mode"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-06]
---

## Plan 1: Implement `experimental.chat.system.transform` Hook

**Goal:** Inject mode-specific system prompts via the `experimental.chat.system.transform` hook.

### Tasks

#### 1.1 Create System Prompt Injection Logic
**Acceptance:** `packages/opencode-plugin/src/hooks/chat-system-transform.ts` exports the hook
**Estimated effort:** Medium
**Dependencies:** 068

<acceptance_criteria>
- grep 'experimental.chat.system.transform' packages/opencode-plugin/src/hooks/chat-system-transform.ts
- grep 'BUILD_BANNER\|TEACH_BANNER' packages/opencode-plugin/src/hooks/chat-system-transform.ts
- grep 'output.system.unshift' packages/opencode-plugin/src/hooks/chat-system-transform.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/chat-system-transform.ts`:

1. Define `BUILD_BANNER` and `TEACH_BANNER` constants with mode-specific context
2. Implement `buildActiveArtifactInfo()` — reads Step goal, verify contract from state env
3. Implement `teachActiveConceptInfo()` — reads concept name, Kolb stage, mastery
4. Implement the main hook function that prepends banner to `output.system` array
5. Export as `export const chatSystemTransform: Hooks["experimental.chat.system.transform"]`
</action>

#### 1.2 Register Hook and Verify Build
**Acceptance:** Hook registered; build passes
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'experimental.chat.system.transform' packages/opencode-plugin/src/index.ts
- bun run build exits 0; bun run typecheck exits 0
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] Prepend mode banner in build mode
- [ ] Prepend mode banner in teach mode
- [ ] Hook registered in server
- [ ] TypeScript compiles cleanly
