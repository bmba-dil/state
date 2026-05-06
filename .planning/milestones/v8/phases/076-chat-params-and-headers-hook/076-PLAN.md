---
phase: "076"
phase_name: "chat.params + chat.headers Hook"
goal: "Inject model profile resolution, cache-control markers, and thinking budget via chat.params and chat.headers hooks"
wave: 1
depends_on: ["068", "027"]
files_modified: []
autonomous: true
requirements: [HOOK-08]
---

## Plan 1: Implement `chat.params` and `chat.headers` Hooks

**Goal:** Inject model profile resolution (quality/balanced/budget) and cache-control/thinking-budget headers.

### Tasks

#### 1.1 Create Profile Resolution and Header Injection
**Acceptance:** `packages/opencode-plugin/src/hooks/chat-params.ts` exports both hooks
**Estimated effort:** Medium
**Dependencies:** 068

<acceptance_criteria>
- grep 'chat.params\|chat.headers' packages/opencode-plugin/src/hooks/chat-params.ts
- grep 'resolveProfile\|STATE_MODEL_PROFILE' packages/opencode-plugin/src/hooks/chat-params.ts
- grep 'X-State-Profile\|X-State-Thinking-Budget' packages/opencode-plugin/src/hooks/chat-params.ts
- grep 'state_thinking_budget' packages/opencode-plugin/src/hooks/chat-params.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/chat-params.ts`:

1. Define model profiles: quality → claude-opus-4, balanced → claude-sonnet-4, budget → claude-haiku
2. Implement `resolveProfile()` — reads STATE_MODEL_PROFILE env var, maps to model ID + thinking budget
3. Implement `chatParams` hook — injects resolved model and thinking budget into params
4. Implement `chatHeaders` hook — injects `X-State-Profile` and `X-State-Thinking-Budget` headers
5. Export both hooks
</action>

#### 1.2 Register Both Hooks and Verify Build
**Acceptance:** Both hooks registered; build passes
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'chat.params\|chat.headers' packages/opencode-plugin/src/index.ts
- bun run build exits 0; bun run typecheck exits 0
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] Inject model profile resolution
- [ ] Cache-control markers
- [ ] Thinking budget injection
- [ ] chat.params and chat.headers hooks registered
- [ ] TypeScript compiles cleanly
