# v8 — Plugin Server Hooks (all 9) Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Opencode Plugin: Server Hooks (A8)

- [ ] **HOOK-01**: `chat.message` — observation recording in teach mode, Step context injection in build mode
- [ ] **HOOK-02**: `tool.execute.before` — mode-gate tool invocation, attribute to Step
- [ ] **HOOK-03**: `tool.execute.after` — verify outputs match Step contract; enqueue verifier trigger
- [ ] **HOOK-04**: `permission.ask` — route gray-area decisions to dialog or auto-decide per config
- [ ] **HOOK-05**: `event` — mirror opencode events to daemon event store
- [ ] **HOOK-06**: `experimental.chat.system.transform` — inject mode-specific system prompts (PRIMM/Socratic/etc. in teach mode; DISCUSS/PLAN boilerplate in build mode)
- [ ] **HOOK-07**: `experimental.session.compacting` — checkpoint Step state before compaction
- [ ] **HOOK-08**: `chat.params` / `chat.headers` — inject model-profile resolution and cache-control
- [ ] **HOOK-09**: `command.execute.before` — mode gate for `/state:*` slash commands
- [ ] **HOOK-10**: `shell.env` — export `STATE_ARC`, `STATE_PHASE`, `STATE_SLICE`, `STATE_STEP` to shell tools
- [ ] **HOOK-11**: Bundled as `@state/opencode-plugin` (server + TUI in one TS package)
