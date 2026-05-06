---
phase: "079"
phase_name: "Plugin Bundle + bun build Packaging + Install Script"
goal: "Bun build single-file bundle; install.sh auto-registers plugin in opencode config"
wave: 1
depends_on: ["069"]
files_modified: []
autonomous: true
requirements: [HOOK-11]
---

## Plan 1: Bundle Plugin and Create Install Script

**Goal:** Bundle all 10 hook modules via `bun build` and create `install.sh` for auto-registration.

### Tasks

#### 1.1 Configure bun build for Single-File Output
**Acceptance:** `bun build` produces `dist/index.js` bundling all hooks
**Estimated effort:** Small
**Dependencies:** 068-078

<acceptance_criteria>
- grep '"bundle"' packages/opencode-plugin/package.json
- dist/index.js exists and includes all hook module content
- dist/index.js is < 20 KB (target: small, efficient bundle)
</acceptance_criteria>

<action>
1. Add `"bundle": "bun build src/index.ts --outdir dist --target node"` to package.json scripts
2. Run `bun run bundle` — verify single-file output
3. Verify all 10 hooks are bundled into dist/index.js
</action>

#### 1.2 Create install.sh Auto-Registration Script
**Acceptance:** `packages/opencode-plugin/install.sh` registers plugin in opencode config
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- install.sh exists and is executable
- install.sh updates opencode config with plugin path
- install.sh creates backup before modifying config
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/install.sh`:
1. Detect opencode config path (`~/.config/opencode/opencode.json`)
2. Create backup of existing config
3. Add `@state/opencode-plugin` plugin entry with correct path
4. Print success message with next steps
</action>

#### 1.3 Final Build Verification
**Acceptance:** Full build pipeline passes; all hooks export correctly
**Estimated effort:** Small
**Dependencies:** 1.1, 1.2

<acceptance_criteria>
- bun run build exits 0; bun run typecheck exits 0
- dist/ contains index.js, index.d.ts, index.js.map
- ls packages/opencode-plugin/dist/index.js confirms existence
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] `bun build` bundles plugin
- [ ] TypeScript declarations emitted
- [ ] `install.sh` script for auto-registration
- [ ] All hooks registered in server export
- [ ] Package.json has correct build+bundle scripts
- [ ] TypeScript compiles cleanly

### Hooks Delivered

| Hook | Phase | File |
|------|-------|------|
| `chat.message` | 069 | src/hooks/chat-message.ts |
| `tool.execute.before` | 070 | src/hooks/tool-execute-before.ts |
| `tool.execute.after` | 071 | src/hooks/tool-execute-after.ts |
| `permission.ask` | 072 | src/hooks/permission-ask.ts |
| `event` | 073 | Deferred |
| `experimental.chat.system.transform` | 074 | src/hooks/chat-system-transform.ts |
| `experimental.session.compacting` | 075 | src/hooks/session-compacting.ts |
| `chat.params` | 076 | src/hooks/chat-params.ts |
| `chat.headers` | 076 | src/hooks/chat-params.ts |
| `command.execute.before` | 077 | src/hooks/command-execute-before.ts |
| `shell.env` | 078 | src/hooks/shell-env.ts |
