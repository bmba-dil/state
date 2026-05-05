---
phase: "069"
phase_name: "chat.message Hook"
goal: "Parse /state:*, reject cross-mode, append active Step/Concept hint"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-01]
---

## Plan 1: Implement `chat.message` Hook

**Goal:** Implement the `chat.message` hook that parses `/state:*` commands, validates mode compatibility, and injects context hints.

### Tasks

#### 1.1 Create Mode Detection and Command Parsing Utilities
**Acceptance:** `packages/opencode-plugin/src/hooks/chat-message.ts` exports a `chatMessage` hook function
**Estimated effort:** Medium
**Dependencies:** 068
**Details:**
```xml
<read_first>
- node_modules/@opencode-ai/plugin/dist/index.d.ts (Hooks['chat.message'] type signature)
- src/state_core/schema.py (Mode type definition)
- packages/opencode-plugin/src/index.ts (plugin entry point)
</read_first>

<acceptance_criteria>
- grep 'export.*chatMessage' packages/opencode-plugin/src/hooks/chat-message.ts
- grep 'chat.message' packages/opencode-plugin/src/hooks/chat-message.ts
- grep '/state:' packages/opencode-plugin/src/hooks/chat-message.ts
- grep 'getMode\|detectMode\|mode' packages/opencode-plugin/src/hooks/chat-message.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/chat-message.ts`:

1. Define `StateMode = "build" | "teach" | "kernel"` type
2. Implement `parseStateCommand(message: string)` — returns `{ mode: StateMode, namespace: string, command: string } | null` for `/state:build:plan-phase`, `/state:teach:teach`, etc.
3. Implement `detectCurrentMode()` — reads from process.env.STATE_MODE or defaults to "kernel"
4. Implement `injectBuildContext(parts: Part[])` — appends active Step/Concept hint as a text Part
5. Implement `recordTeachObservation(message: string)` — basic observation recording (placeholder that logs to console for now)
6. Implement the main `chatMessage` hook function:
   - Parse message text for `/state:*` commands
   - If found, check mode compatibility (reject cross-mode)
   - In build mode: inject Step context hint into output parts
   - In teach mode: record observation
7. Export the hook as `export const chatMessage: Hooks["chat.message"]`
</action>
```

#### 1.2 Register Hook in Plugin Server
**Acceptance:** `packages/opencode-plugin/src/index.ts` exports `chatMessage` in the server hooks
**Estimated effort:** Small
**Dependencies:** 1.1
**Details:**
```xml
<read_first>
- packages/opencode-plugin/src/index.ts
- packages/opencode-plugin/src/hooks/chat-message.ts
</read_first>

<acceptance_criteria>
- grep 'chatMessage' packages/opencode-plugin/src/index.ts
- grep 'chat.message' packages/opencode-plugin/src/index.ts
</acceptance_criteria>

<action>
Update `packages/opencode-plugin/src/index.ts`:
- Import `chatMessage` from `./hooks/chat-message.js`
- Register it in the server return: `{ "chat.message": chatMessage }`
</action>
```

#### 1.3 Build Verification
**Acceptance:** `bun run build` and `bun run typecheck` pass
**Estimated effort:** Small
**Dependencies:** 1.1, 1.2
**Details:**
```xml
<read_first>
- packages/opencode-plugin/src/index.ts
- packages/opencode-plugin/src/hooks/chat-message.ts
- packages/opencode-plugin/tsconfig.json
</read_first>

<acceptance_criteria>
- bun run build exits 0 in packages/opencode-plugin/
- bun run typecheck exits 0 in packages/opencode-plugin/
- dist/ contains updated .js and .d.ts files
</acceptance_criteria>

<action>
Working directory: `packages/opencode-plugin/`
1. Run `bun run build` — verify compilation
2. Run `bun run typecheck` — verify no errors
</action>
```

### Verification Criteria (must_haves)
- [ ] `chat.message` hook parses `/state:build:*` and `/state:teach:*` commands
- [ ] Cross-mode commands are rejected (build commands blocked in teach mode, vice versa)
- [ ] Build mode injects Step context hint into message output
- [ ] Teach mode records observation (basic console logging)
- [ ] Hook registered in plugin server and compiles cleanly
