# Opencode Extension Surface: Every Integration Point, Categorized

A block-by-block map of every mechanism in opencode that GSD and AOL can exploit to become fully realized state machines. All paths relative to `opencode/packages/opencode/src/` unless noted.

---

## 0. Executive summary — the big discoveries

1. **`task` tool already exists** with `subagent_type`, `prompt`, `description` — **plus** a `task_id` field for *resuming* a prior subagent session. Claude Code can't do that. (`tool/task.ts:20-31`)
2. **Custom tools auto-load from `{tool,tools}/*.{js,ts}` in any config directory.** You don't even need a full plugin — drop a TS file. (`tool/registry.ts:153-166`)
3. **Full HTTP API with 90+ operations** — every internal service has a REST endpoint. Your GSD state machine can drive the TUI, spawn sessions, answer questions, reply to permissions, and inject prompts — all over HTTP from an external daemon.
4. **34 typed bus events** cover every lifecycle moment: session, message, todo, permission, question, tool, file, LSP, MCP, PTY, worktree, VCS, installation, IDE.
5. **`SyncEvent`** is an event-sourced substrate — GSD's state machine can ride it directly instead of re-implementing state persistence.
6. **TUI plugin API (500+ lines)** lets you register commands, routes, dialogs, keybinds, slots, and read live session state. GSD's statusline + inline permission UI + custom dashboards become trivial.
7. **Session hierarchy is first-class**: `parentID`, `fork`, `children` — GSD's phase/plan/task tree maps 1:1.
8. **Permission system is rule-based with `permission.ask` hook** — GSD's workflow guard becomes a typed rule set, not a shell script parsing JSON on stdin.

---

## 1. Plugin Hooks (14 types, `packages/plugin/src/index.ts`)

Every hook has typed input and mutable output. Registered via `Hooks` returned from plugin `server` function.

### Lifecycle & events
| Hook | Purpose | GSD/AOL use |
|---|---|---|
| `event(input: { event: Event })` | Catch-all for every bus event | GSD phase state machine subscribes here; AOL learner-state tracker |
| `config(input: Config)` | Called when config loaded/updated | GSD hot-reloads model profiles; AOL re-reads subject config |

### Chat lifecycle (= Claude Code's UserPromptSubmit + SystemPrompt)
| Hook | Purpose | GSD/AOL use |
|---|---|---|
| `chat.message(input, output: {message, parts})` | Mutate incoming user message parts before LLM sees them | GSD prompt-guard, correction-capture, snapshot inject |
| `chat.params(input, output: {temperature, topP, topK, maxOutputTokens, options})` | Per-call LLM param override | GSD model-profile resolver, AOL teaching-style temperature tuning |
| `chat.headers(input, output: {headers})` | Add HTTP headers per request | Provider-specific auth, request tagging for analytics |
| `experimental.chat.system.transform(input: {sessionID, model}, output: {system: string[]})` | Mutate system prompt array | GSD state injection (replaces `gsd-inject-snapshot.js` hook) |
| `experimental.chat.messages.transform(input, output: {messages})` | Rewrite entire message history pre-send | Context budget manager, conversation surgery |
| `experimental.text.complete(input: {sessionID, messageID, partID}, output: {text})` | Transform text output parts after generation | Response post-processing, citation injection |

### Session compaction (no Claude Code equivalent)
| Hook | Purpose | GSD/AOL use |
|---|---|---|
| `experimental.session.compacting(input, output: {context, prompt?})` | Customize compaction prompt | GSD injects phase state into compaction summary |
| `experimental.compaction.autocontinue(input, output: {enabled})` | Decide whether to auto-continue after compaction | AOL pauses teaching for reflection checkpoints |

### Tool lifecycle (= Claude Code's Pre/PostToolUse)
| Hook | Purpose | GSD/AOL use |
|---|---|---|
| `tool.execute.before(input: {tool, sessionID, callID}, output: {args})` | Mutate or block tool args | GSD read-guard, workflow-guard |
| `tool.execute.after(input: {tool, sessionID, callID, args}, output: {title, output, metadata})` | Rewrite tool results | Correction-capture, commit validation |
| `tool.definition(input: {toolID}, output: {description, parameters})` | Rewrite tool descriptions sent to LLM | Agent-specific tool descriptions, A/B testing |

### Permissions & shell (new surfaces beyond Claude Code)
| Hook | Purpose | GSD/AOL use |
|---|---|---|
| `permission.ask(input: Permission, output: {status: "ask"|"deny"|"allow"})` | Intercept every permission prompt | GSD auto-approves within active phase context |
| `command.execute.before(input: {command, sessionID, arguments}, output: {parts})` | Fires before slash command expansion | Inject phase context into commands |
| `shell.env(input: {cwd, sessionID?, callID?}, output: {env})` | Inject env vars for every shell call | GSD exposes `.planning/` paths as env |

### Auth, provider, tool registration
| Hook | Purpose | GSD/AOL use |
|---|---|---|
| `auth: AuthHook` | Register custom auth methods (OAuth/API) | GSD registers Z.ai/GLM/Qwen providers with OAuth flows |
| `provider: ProviderHook` | Register custom model providers | Custom local model endpoints |
| `tool: {[id]: ToolDefinition}` | Register custom tools | `gsd.spawn`, `gsd.phase.advance`, `aol.curriculum.next` |

---

## 2. Bus Events (34 typed events, grep `BusEvent.define`)

Every bus event is Zod-schema-typed, published via `Bus.publish(Def, properties)`, subscribed via `Bus.subscribe(Def)` or the catch-all `event` hook.

### Session
- `session.status` — active/idle/completed transitions (`session/status.ts:29`)
- `session.idle` — session went idle (`session/status.ts:37`) → **replaces Claude's `Stop` hook**
- `session.created`, `session.updated`, `session.deleted` — CRUD
- `session.compacted` — compaction happened
- `session.diff` — file diff for a session
- `session.error` — error in session

### Messages
- `message.part.delta` — streaming part delta

### Todos
- `todo.updated` — todo list changed → **GSD task tracker mirror**

### Permissions
- `permission.asked` — a permission prompt opened
- `permission.replied` — user replied (once/always/reject)

### Questions
- `question.asked`, `question.replied`, `question.rejected` — structured question flow

### Tools & commands
- `command.executed` — slash command ran
- `mcp.tools.changed` — MCP server rediscovered tools → **hot reload MCP tool set**
- `mcp.browser.open.failed` — MCP OAuth browser open failed

### Files & LSP
- `file.edited` — file was edited
- `file.watcher.updated` — file watcher fired
- `lsp.updated` — LSP state changed
- `lsp.client.diagnostics` — diagnostics received

### PTY (shell sessions)
- `pty.created`, `pty.updated`, `pty.exited`, `pty.deleted`

### VCS / Worktree
- `vcs.branch.updated`
- `worktree.ready`, `worktree.failed`

### Project / Workspace
- `project.updated`
- `workspace.ready`, `workspace.failed`, `workspace.restore`, `workspace.status`

### Installation / IDE / Server
- `installation.updated`, `installation.update-available`
- `ide.installed`
- `server.instance.disposed`, `server.connected`, `global.disposed`

### TUI
- `tui.prompt.append`, `tui.command.execute`, `tui.toast.show`, `tui.session.select`

**GSD/AOL pattern:** your state machine subscribes via `event` hook and advances on the right event. No more shell scripts parsing JSON stdin.

---

## 3. Built-in Tools (17 tools, `tool/registry.ts:179-219`)

Each has its own file with `.ts` impl and `.txt` prompt description.

| Tool ID | Purpose | GSD/AOL relevance |
|---|---|---|
| `invalid` | Fallback for unknown tool calls | — |
| `question` | Structured multi-choice prompt (AskUserQuestion equivalent) | AOL drill questions, GSD gray-area decisions |
| `bash` | Shell execution | — |
| `read`, `write`, `edit` | File ops | — |
| `glob`, `grep`, `codesearch` | Code search | — |
| `fetch`, `search` (websearch) | Web access | — |
| `task` | Spawn subagent, resume via task_id | **replaces Claude Code Task entirely, plus resume** |
| `todo` | Update session todo list (→ `todo.updated` bus event) | GSD TODO mirror |
| `skill` | Load a skill's full content into context | GSD auto-loads workflow skill |
| `patch` (`apply_patch`) | Apply a patch (GPT-style) | — |
| `lsp` (experimental) | Query LSP diagnostics | GSD verifier |
| `plan` (plan mode) | Enter/exit plan mode | GSD discuss-phase mapping |

### Custom tool loading (huge)
`tool/registry.ts:153-166`:
```ts
const dirs = yield* config.directories()
const matches = dirs.flatMap((dir) =>
  Glob.scanSync("{tool,tools}/*.{js,ts}", { cwd: dir, absolute: true }),
)
```

**Drop a `.ts` file in any config directory's `tools/` folder and it's auto-registered.** Example:
```ts
// ~/.config/opencode/tools/gsd.ts
import { tool } from "@opencode-ai/plugin"

export const advance_phase = tool({
  description: "Advance the current GSD phase to the next status",
  args: { phase: tool.schema.string() },
  async execute(args, ctx) {
    // call GSD state machine
    return { output: "Phase advanced", metadata: { phase: args.phase } }
  }
})
```
Tool ID is derived from filename + export. No plugin wrapper needed for simple tools.

### Tool context (`tool/tool.ts`)
Every tool gets a rich context:
- `sessionID`, `messageID`, `agent`, `directory`, `worktree`, `abort: AbortSignal`
- `metadata({title, metadata})` — update live tool call display
- `ask({permission, patterns, always, metadata})` — runtime permission gate

---

## 4. Task Tool Deep Dive (`tool/task.ts`, 175 lines)

This is the centerpiece for GSD orchestration.

```ts
parameters = z.object({
  description: z.string(),   // 3-5 word label
  prompt: z.string(),        // instructions for subagent
  subagent_type: z.string(), // agent name from opencode.json
  task_id: z.string().optional(), // RESUME a prior subagent session
  command: z.string().optional(),
})
```

**What happens on execute:**
1. Permission check via `ctx.ask({permission: "task", patterns: [subagent_type]})` — allows rule-based gating per-subagent
2. Look up agent by name (`Agent.get`)
3. Resolve/create a child session with `parentID = ctx.sessionID`
4. Denies `todowrite` and nested `task` by default unless the target agent has those permissions — recursive subagent control is explicit
5. Applies `cfg.experimental.primary_tools` whitelist
6. Uses `ctx.extra.promptOps` to actually dispatch the LLM call in the child session
7. Returns `task_id: <sessionID>` in output so the caller can resume

**GSD exploit:** the orchestrator agent calls `task({subagent_type: "gsd-executor", prompt: "run PLAN 72.1", task_id: lastExecutorSessionID})` and the executor picks up exactly where it left off. This is impossible in Claude Code — every `Task` call is a fresh conversation.

---

## 5. Agent System (`agent/agent.ts`, 411 lines)

### Built-in agents
- `build` (primary, default) — full access
- `plan` (primary) — deny all edits; allow writing to `.opencode/plans/*.md` and global plans
- `general` (subagent) — parallel multi-step work
- `explore` (subagent) — read-only codebase research
- `compaction`, `title`, `summary` (hidden primary) — internal

### User-defined agents via `opencode.json`
```json
{
  "agent": {
    "gsd-executor": {
      "mode": "subagent",
      "description": "...",
      "prompt": "...",
      "model": "anthropic/claude-sonnet-4-6",
      "temperature": 0.3,
      "permission": {
        "*": "allow",
        "write": { "*": "ask", ".planning/**": "allow" }
      },
      "options": { /* custom per-agent state */ },
      "steps": 50
    }
  }
}
```

### Fields (`Info` schema)
- `mode: "subagent" | "primary" | "all"`
- `prompt`, `description`, `color`, `topP`, `temperature`, `steps`
- `model: {providerID, modelID}`
- `variant` — variant ID for model variants
- `permission` — ruleset (see below)
- `options: Record<string, any>` — **free-form per-agent config**, read by your plugin
- `hidden` — hide from TUI picker
- `native` — built-in flag

### Runtime generation
`agent.generate({description, model})` — LLM-generates an agent config from a natural-language description. Uses `PROMPT_GENERATE`, returns `{identifier, whenToUse, systemPrompt}`. GSD can dynamically spawn specialized subagents per phase.

---

## 6. Permission System (`permission/`, 4 files)

### Ruleset schema
```ts
Rule = { permission: string, pattern: string, action: "allow"|"deny"|"ask" }
Ruleset = Rule[]
```

### Config shape (`fromConfig` in `permission/index.ts:292`)
```json
{
  "permission": {
    "*": "allow",
    "edit": { "*": "ask", ".planning/**": "allow" },
    "task": { "gsd-*": "allow", "*": "ask" },
    "external_directory": { "~/.gsd/**": "allow", "*": "ask" },
    "read": { "*": "allow", "*.env": "ask" }
  }
}
```

### Evaluation model
- Wildcard matching via `Wildcard.match`
- `findLast` — specific rules override `*` fallback
- Three layers merged: defaults + agent-specific + user config
- `EDIT_TOOLS = ["edit", "write", "apply_patch"]` collapse to `"edit"` permission

### Bus events
- `permission.asked` — opened
- `permission.replied` — `{reply: "once"|"always"|"reject", message?}`

### `permission.ask` plugin hook
Intercept before the prompt hits the user. GSD can auto-respond based on active phase state:
```ts
"permission.ask": async (input, output) => {
  if (input.permission === "edit" && gsdState.currentPhase.allowsEdit(input.patterns[0])) {
    output.status = "allow"
  }
}
```

---

## 7. Question Service (`question/index.ts`, 230 lines)

Structured multi-choice questions, backed by the bus. Used by the `question` built-in tool but callable directly from plugins.

```ts
Question.ask({
  sessionID,
  questions: [{
    question: "Which phase strategy?",
    header: "Strategy",
    options: [
      { label: "Aggressive", description: "Ship fast" },
      { label: "Conservative", description: "Ship safe" }
    ],
    multiple: false,
    custom: true  // allow typed custom answer
  }],
  tool: { messageID, callID }  // optional — ties question to a tool call
})
```

Returns `Answer[][]` (array per question, each answer is a string array of selected labels).

Bus events: `question.asked`, `question.replied`, `question.rejected`.

**GSD exploit:** structured gray-area decisions, phase-start confirmations, AOL drill questions all stop being free-form text parsing and become typed records with audit history.

---

## 8. Todo Service (`session/todo.ts`)

- `Todo.update({sessionID, todos: [{content, status, priority}]})`
- `Todo.get(sessionID)` → persisted to SQLite `TodoTable`
- Publishes `todo.updated` bus event

GSD mirrors its `.planning/todos/pending/` JSON store into opencode's todo system; the TUI renders it natively in the sidebar.

---

## 9. MCP System (`mcp/`, 5 files, 800+ lines)

**Full MCP client**, not a hack:
- `stdio` transport (subprocess)
- `streamableHttp` transport
- `sse` transport (deprecated but supported)
- **OAuth flow for MCP servers** (`mcp/oauth-provider.ts`, `mcp/oauth-callback.ts`, `mcp/auth.ts`)
- `ToolListChangedNotificationSchema` support — bus publishes `mcp.tools.changed`
- Per-server connection status (`MCPStatusConnected` | error states)

### Configure in `opencode.json`
```json
{
  "mcp": {
    "gsd-tools": {
      "type": "local",
      "command": ["node", "/Users/tmac/.claude/get-shit-done/bin/gsd-tools.cjs", "mcp"],
      "enabled": true
    },
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com",
      "enabled": true
    }
  }
}
```

**GSD exploit:** your existing `gsd-tools.cjs` MCP server is copy-pasted into opencode with zero rewrites. Same tool names, same handlers. MCP is the portable layer.

---

## 10. Skill System (`skill/`, 2 files, 404 lines)

### Discovery paths (in order)
1. `~/.claude/skills/**/SKILL.md` + `~/.agents/skills/**/SKILL.md` (global external)
2. Project `.claude/skills/` walking up from `directory` to `worktree` (project external)
3. `{skill,skills}/**/SKILL.md` in every config dir (opencode-native)
4. `cfg.skills.paths` — custom absolute/relative paths
5. `cfg.skills.urls` — **remote skill registry URLs** — fetches `<url>/index.json`, downloads each skill's files to cache (`skill/discovery.ts`)

### Remote skills
```json
{
  "skills": {
    "urls": ["https://gsd.anomalyco.com/skills"],
    "paths": ["~/my-skills"]
  }
}
```
Opencode fetches `index.json`, downloads each listed file, caches to `Global.Path.cache/skills/<name>/`. **You could host a GSD skill registry** that updates your skills across machines.

### Skills become commands automatically
`command/index.ts:148-159` — every skill appears as a slash command whose template is the skill's content.

---

## 11. Command System (`command/index.ts`)

### Sources
1. Built-in: `init`, `review`
2. `cfg.command.*` in opencode.json:
   ```json
   { "command": {
     "gsd:phase": {
       "description": "Start a phase",
       "template": "Start phase $1 using $2",
       "agent": "gsd-orchestrator",
       "model": "anthropic/claude-opus-4-7",
       "subtask": true
     }
   }}
   ```
3. **MCP prompts** — every MCP server's `prompts/list` output becomes a slash command
4. Skills (auto-promoted)

### Hints parsing
`$ARGUMENTS`, `$1..$9` — same as Claude Code. Parser at `command/index.ts:50-58`.

### `command.execute.before` hook
Mutate command arg expansion before the LLM sees it. GSD injects `.planning/PHASE-72.md` content as a file part whenever a `/gsd:*` command fires.

---

## 12. Session Service (`session/session.ts`, 750 lines)

### Interface (30 methods)
- `create({parentID, title, permission, workspaceID})` — parentID makes it a child
- `fork({sessionID, messageID})` — branch at a message
- `children(parentID)` — list subagent sessions
- `get`, `messages`, `updateMessage`, `removeMessage`, `updatePart`, `updatePartDelta`
- `setTitle`, `setArchived`, `setPermission`, `setRevert`, `clearRevert`, `setSummary`
- `diff(sessionID)` — file changes for session
- `findMessage(sessionID, predicate)` — newest-first search

### Sync events (event-sourced, different from bus events)
`SyncEvent.define` — `session.created`, `session.updated`, `session.deleted`, `message.*`. These are durable, replay-able, and power the `/sync` HTTP routes for multi-client state.

### Session lifecycle files
- Plan files: `.opencode/plans/<timestamp>-<slug>.md` (VCS) or `$DATA/plans/` (non-VCS)
- DB-backed: sessions, messages, parts, todos, permissions all in SQLite

### Session revert
`setRevert(info)` — records a revertible state. GSD phase rollback.

---

## 13. HTTP Server + SDK (90+ operations, `server/routes/` + `packages/sdk/js/`)

The entire server is exposed over HTTP. Your plugin receives `createOpencodeClient(...)` which talks to this API. An **external** GSD daemon can talk to it too.

### Operation inventory (non-exhaustive, grouped)

**Session (25 ops):** `session.list`, `session.status`, `session.get`, `session.children`, `session.todo`, `session.create`, `session.delete`, `session.update`, `session.init`, `session.fork`, `session.abort`, `session.share`, `session.diff`, `session.unshare`, `session.summarize`, `session.messages`, `session.message`, `session.deleteMessage`, `part.delete`, `part.update`, `session.prompt`, `session.prompt_async`, `session.command`, `session.shell`, `session.revert`, `session.unrevert`, `permission.respond`

**TUI (13 ops):** `tui.control.next`, `tui.control.response`, `tui.appendPrompt`, `tui.openHelp`, `tui.openSessions`, `tui.openThemes`, `tui.openModels`, `tui.submitPrompt`, `tui.clearPrompt`, `tui.executeCommand`, `tui.showToast`, `tui.publish`, `tui.selectSession`

**Sync (3 ops):** `sync.start`, `sync.replay`, `sync.history.list` — event replay for multi-client consistency

**MCP (9 ops):** `mcp.status`, `mcp.add`, `mcp.auth.start`, `mcp.auth.callback`, `mcp.auth.authenticate`, `mcp.auth.remove`, `mcp.connect`, `mcp.disconnect`

**PTY (6 ops):** `pty.list`, `pty.create`, `pty.get`, `pty.update`, `pty.remove`, `pty.connect` — **opencode runs persistent shell sessions**

**Permission / Question (5 ops):** `permission.reply`, `permission.list`, `question.list`, `question.reply`, `question.reject`

**Config / Project (7 ops):** `config.get`, `config.update`, `config.providers`, `project.list`, `project.current`, `project.initGit`, `project.update`

**Files (6 ops):** `find.text`, `find.files`, `find.symbols`, `file.list`, `file.read`, `file.status`

**Provider / Experimental (15+ ops):** `provider.list`, `provider.auth`, `provider.oauth.authorize`, `provider.oauth.callback`, `experimental.console.*`, `tool.ids`, `tool.list`, `worktree.create/list/remove/reset`, `experimental.session.list`, `experimental.resource.list`

**Events:** `GET /event` — Server-Sent Events stream of every bus event

### Event subscription
`event.subscribe` operation + SSE stream = GSD's state machine can run as a **separate process** that just subscribes to the bus over HTTP. No plugin needed for monitoring.

### GSD exploit pattern
```
┌─────────────┐    HTTP       ┌──────────────┐
│ GSD daemon  │ ◄────────────►│ opencode     │
│ (state      │   SSE events  │ server       │
│  machine)   │               │              │
│  - phases   │               │  - sessions  │
│  - plans    │   spawns via  │  - tools     │
│  - todos    │ ─session.create│ - agents     │
└─────────────┘               └──────────────┘
```
GSD runs headless, subscribes to events, drives the session. TUI is just another client.

---

## 14. TUI Plugin API (`packages/plugin/src/tui.ts`, 501 lines)

A full UI extension surface — **not** just a statusline.

### Registration
```ts
export const GsdPlugin: TuiPluginModule = {
  tui: async (api, options, meta) => { /* ... */ }
}
```

### `TuiPluginApi` capabilities
| Namespace | Operations |
|---|---|
| `command` | `register(() => TuiCommand[])`, `trigger(value)`, `show()` — register slash commands, keybinds, callbacks |
| `route` | `register(TuiRouteDefinition[])`, `navigate(name, params)`, `current` — **register full custom views** (routes!) |
| `ui.Dialog*` | `Alert`, `Confirm`, `Prompt`, `Select` (typed options) |
| `ui.Slot` | Register JSX into host slots: `home_logo`, `home_prompt`, `session_prompt`, `sidebar_title`, `sidebar_content`, `sidebar_footer`, `app`, `home_bottom`, `home_footer` |
| `ui.Prompt` | Replace or augment the prompt input |
| `ui.toast(input)` | Show toast |
| `ui.dialog` | Stack of dialogs (`replace`, `clear`, `setSize`) |
| `keybind` | `match`, `print`, `create` |
| `kv` | Key-value store |
| `state` | Live read-only state: session count, diff, todos, messages, status, permissions, questions; lsp & mcp status lists |
| `client` | Full `OpencodeClient` HTTP client |
| `event` | `on(eventType, handler)` — subscribe to typed events in the TUI |
| `renderer` | Raw `CliRenderer` from `@opentui/core` |
| `slots` | Register SolidJS slot plugins |
| `plugins` | Meta: list, activate, deactivate, install — **plugins can install other plugins** |
| `lifecycle` | `signal: AbortSignal`, `onDispose(fn)` |

### GSD TUI exploits
- **Sidebar panel** showing current phase, active plan, todo count — plug into `sidebar_content` slot
- **Custom route** `/gsd/dashboard` with phase graph, burndown, recent commits
- **Toasts** on phase transitions, verification failures
- **Custom dialog** when a `gsd-orchestrator` routes gray-area decision → uses `DialogSelect`
- **Command registry** for every `/gsd:*` command with keybinds
- **Prompt slot** injects phase-context hint at the bottom of the input

### AOL TUI exploits
- Full teaching UI as custom route
- Confidence/mistake heatmap in sidebar
- Custom prompt mode for drill questions with timer

---

## 15. Config System (`config/`, 23 files)

### Top-level schema (`config/config.ts:798` lines)
Every config is a separate Zod schema file, composed in `config.ts`:
- `ConfigAgent` — agents
- `ConfigCommand` — commands
- `ConfigFormatter` — per-language formatters
- `ConfigLayout` — TUI layout
- `ConfigLSP` — LSP config
- `ConfigManaged` — managed-mode flags
- `ConfigMCP` — MCP servers
- `ConfigModelID` — default model
- `ConfigParse` — config parser (JSONC)
- `ConfigPaths` — additional config dirs
- `ConfigPermission` — default permission ruleset
- `ConfigPlugin` — plugin specs
- `ConfigProvider` — providers
- `ConfigServer` — server settings
- `ConfigSkills` — skill paths + registry URLs
- `ConfigVariable` — variable substitution

### Config dirs (`config.directories()`)
Multiple config dirs are merged. Deep-merge with array concat for `instructions`. Returns a sorted list used for skill/command/tool discovery.

### Dynamic config
`cfg.experimental` — escape hatch. `experimental.primary_tools` is a whitelist of tools that remain available to subagents. GSD sets this to include its custom tools.

### Hot-reload
`config` hook fires on every config change. GSD re-scans `.planning/` and updates its state machine.

---

## 16. Snapshot System (`snapshot/index.ts`)

Stores per-session file snapshots — used for `session.diff` and revert. Your plugin can:
- Capture file state before a phase
- Diff after the phase completes
- Roll back via `session.revert`

GSD phase boundary integration = automatic snapshot at phase start, commit on verify-pass.

---

## 17. LSP Integration (`lsp/`, 7 files)

- Full LSP client pool — per-project per-language
- Bus events on diagnostics
- `lsp` tool (experimental) surfaces diagnostics to the LLM
- Auto-launch servers via `lsp/launch.ts`

GSD verifier exploits live diagnostics instead of running `npm test` from scratch.

---

## 18. File Watcher (`file/watcher.ts`)

`file.watcher.updated` bus event. GSD watches `.planning/**` and invalidates its cache on external edits.

---

## 19. PTY Service (`pty/`, 5 files)

Persistent interactive shell sessions with lifecycle events. Attach/reattach, resize, kill. GSD dev server, AOL's REPL mentor.

---

## 20. Plan Mode (`tool/plan.ts`, `tool/plan-enter.txt`, `tool/plan-exit.txt`)

Built-in mode that blocks edits. GSD's discuss-phase maps onto this naturally. The `plan` agent is already defined; you can customize its permission ruleset.

---

## 21. Worktree / Workspace (`worktree/`, `control-plane/`)

### Worktree
- Git worktree management with bus events (`worktree.ready`, `worktree.failed`)
- HTTP ops: `worktree.create`, `worktree.list`, `worktree.remove`, `worktree.reset`

### Workspace adaptors (experimental, plugin API)
```ts
input.experimental_workspace.register(type: string, adaptor: WorkspaceAdaptor)
```
Custom workspace types — GSD can register `gsd-phase` as a workspace type that materializes a phase directory tree.

---

## 22. Auth System (`auth/index.ts`, `provider/auth.ts`)

Three credential types: `api`, `oauth`, `wellknown`. Stored in `auth.json` (chmod 600).

Plugins register new provider auth via `AuthHook` with full prompt/OAuth/API flows:
```ts
auth: {
  provider: "glm",
  methods: [{
    type: "api",
    label: "API Key",
    prompts: [{ type: "text", key: "apiKey", message: "Enter GLM key" }],
    authorize: async (inputs) => ({ type: "success", key: inputs.apiKey })
  }]
}
```

---

## 23. Sync / Event Sourcing (`sync/`, 3 files)

`SyncEvent.define` creates durably-stored events with schemas. Used for session CRUD, message updates. The `sync.start` + `sync.replay` HTTP endpoints let a second client catch up by replaying events.

**GSD exploit:** define your own sync events for phase transitions. Get event sourcing + replay for free.

```ts
const PhaseAdvanced = SyncEvent.define({
  type: "gsd.phase.advanced",
  version: 1,
  aggregate: "phaseID",
  schema: z.object({ phaseID: z.string(), from: z.string(), to: z.string() })
})
```

---

## 24. ACP Protocol (`acp/`, 4 files)

Agent Communication Protocol — external agents talk to opencode over a typed protocol. GSD can run as an ACP agent addressable from any ACP-compatible host.

---

## 25. IDE Integration (`ide/index.ts`)

Bus event `ide.installed`. Install VSCode/JetBrains extensions from within opencode. Not directly GSD-relevant but shows platform reach.

---

## 26. Installation & Updates (`installation/`)

`installation.updated`, `installation.update-available` events. Plugin can gate GSD on opencode version.

---

## 27. Session Overflow / Retry / Compaction (`session/overflow.ts`, `session/retry.ts`, `session/compaction.ts`)

Retry policy per provider; compaction triggers per context-window threshold. Your plugin overrides via `experimental.session.compacting` hook.

---

## 28. Prompt & Processor Pipeline (`session/prompt.ts`, `session/processor.ts`, `session/llm.ts`)

The internal pipeline that turns a user message into an LLM call. Plugin hooks fire at every stage:
1. `chat.message` — incoming
2. `chat.params` — LLM params set
3. `chat.headers` — HTTP headers set
4. `experimental.chat.system.transform` — system prompt built
5. `experimental.chat.messages.transform` — message list prepared
6. LLM call
7. `experimental.text.complete` — text parts post-processed
8. `tool.execute.before`/`after` — any tool invocations
9. Response stored

---

## How GSD maps, block by block

| GSD component | opencode mechanism | Implementation |
|---|---|---|
| `gsd-orchestrator` agent | Agent in opencode.json with `mode: "primary"` | Use `task` tool to spawn specialists |
| `gsd-executor` agent | Subagent in opencode.json | Receives plan via `task` tool, resumable via `task_id` |
| `/gsd:plan-phase` command | `cfg.command.gsd:plan-phase` | Template + `agent` + `subtask: true` |
| `Task({subagent_type})` | Built-in `task` tool | Zero translation |
| `TodoWrite` | Built-in `todo` tool | Zero translation |
| `AskUserQuestion` | Built-in `question` tool | Zero translation |
| `SessionStart` hook (snapshot inject) | `experimental.chat.system.transform` | Reads `.planning/STATE.md`, adds to system array |
| `UserPromptSubmit` hook (prompt-guard) | `chat.message(input, output)` | Inspect parts, mutate or throw |
| `PreToolUse` (read-guard) | `tool.execute.before` | Gate by path, agent, phase state |
| `PostToolUse` (correction-capture) | `tool.execute.after` | Pipe results to `corrections.jsonl` |
| `Stop` hook (save-work-state) | Subscribe to `session.idle` bus event | Write STATE.md |
| `gsd-tools.cjs` MCP | Register in `opencode.json` under `mcp.*` | Zero rewrite |
| Model profile resolver | `chat.params` hook | Read `.planning/PLAN.md` frontmatter, set temperature/model |
| Skill-load tracker | `tool.execute.after` on `skill` tool | Append to `skill-loads.jsonl` |
| Context budget monitor | Subscribe to `message.part.delta` + `session.status` | Abort via `session.abort` HTTP op when ceiling hit |
| Phase state machine | `SyncEvent.define("gsd.phase.*")` | Event-sourced, replayable |
| Workflow guard | `permission.ask` hook + `tool.execute.before` | Deny edits outside active phase scope |
| Statusline | TUI plugin `sidebar_footer` slot or `home_footer` slot | JSX with live state |
| Dashboard | TUI plugin `route.register("gsd.dashboard")` | Full custom view |
| Correction capture | `chat.message` hook + store to SQLite | Own table via `storage/` service |
| `.planning/` snapshots | Snapshot service at phase start, diff at end | `session.diff` + custom store |
| Gray-area decisions | `question.ask` from within a custom tool | Audit trail in `question.replied` events |

## How AOL maps, block by block

| AOL component | opencode mechanism | Implementation |
|---|---|---|
| `aol:teach` command | `cfg.command.aol:teach` + `agent: "aol-curriculum-orchestrator"` | — |
| Curriculum planner subagent | Agent with `mode: "subagent"`, own prompt | Spawn via `task` tool |
| PRIMM / Scaffolded / Socratic / Constructivist modes | Each is an agent `variant` or a per-session `options` field | `agent.options.mode = "socratic"`, read in system-prompt hook |
| Drill questions | `question` tool with structured options | Answers auto-stored in DB |
| Learner state (`.aol/state/`) | Custom SQLite tables via `storage/` service + sync events | Replayable per-learner |
| Mental model tracking | Subscribe to `question.replied`, `tool.execute.after`, `message.part.delta` | Accumulate in mental-model.json equivalent |
| Teaching-style config | `cfg.agent.*.options.style` | Hot-reload via `config` hook |
| Progress dashboard | TUI route `/aol/progress` | Custom JSX view |
| `aol` binary | External CLI kept as-is; plugin shells out via `ctx.$` (Bun shell) or Node child_process | No rewrite |
| Observation recorder | `tool.execute.after` hook writes to JSONL | — |
| Active-mode state | Custom sync events `aol.mode.changed` | — |
| Subject installation | Plugin's `auth` hook (treating subject as "provider") or custom tool | — |

---

## What's impossible or hard in Claude Code but trivial here

1. **Resumable subagents** — `task_id` parameter
2. **Event-sourced state** — `SyncEvent` with replay, no separate event store needed
3. **Structured questions with audit trail** — `question.asked`/`replied` events
4. **Plugins installing plugins** — `api.plugins.install(spec)` at runtime
5. **Custom TUI routes** — full views, not just statusline
6. **HTTP-driven orchestration** — GSD daemon as separate process
7. **Per-agent deep permission rulesets** — nested patterns, not a flat tool list
8. **Remote skill registries** — fetch from URL, auto-cache
9. **Hot-reload config hook** — no restart
10. **MCP OAuth flow built in** — GSD's auth rotation becomes trivial

## What requires real work

1. **Rewriting `.claude/agents/*.md` frontmatter-markdown** into `opencode.json` entries — mechanical, ~1 day for 36 agents
2. **Hook adapter** for existing `~/.claude/hooks/*.js` — ~150 lines, shells out with translated payload
3. **Building the `opencode-gsd` plugin package** — scaffold, config, hooks wired
4. **Testing against multiple providers** — Qwen, Gemini, Claude parity matrix
5. **Custom TUI views in SolidJS** — new skill if you want the dashboard UX

---

## Recommended architecture for GSD-on-opencode

```
~/.config/opencode/
├── opencode.json                  # agents, commands, mcp, permission
├── AGENTS.md                      # → symlink to ~/.claude/CLAUDE.md
├── tools/
│   ├── gsd.ts                     # custom tools: advance_phase, verify, ship, etc.
│   └── aol.ts                     # custom tools: drill, next_concept, etc.
└── plugins/
    ├── opencode-gsd/
    │   ├── index.ts               # Plugin export with Hooks
    │   ├── hooks/
    │   │   ├── chat-message.ts    # prompt-guard, correction-capture
    │   │   ├── system-transform.ts # state injection
    │   │   ├── tool-before.ts     # read-guard, workflow-guard
    │   │   ├── tool-after.ts      # observation recording
    │   │   ├── permission-ask.ts  # auto-approve in-phase
    │   │   ├── params.ts          # model profile resolver
    │   │   └── compacting.ts      # phase-aware compaction
    │   ├── tools/
    │   │   └── spawn.ts           # programmatic subagent spawn
    │   ├── state/
    │   │   ├── phase-machine.ts   # SyncEvent-based state machine
    │   │   └── store.ts           # custom SQLite tables
    │   ├── tui/
    │   │   ├── dashboard.tsx      # full route
    │   │   ├── sidebar.tsx        # phase status slot
    │   │   └── commands.ts        # custom /gsd commands
    │   └── mcp/
    │       └── register.ts        # auto-register gsd-tools.cjs
    └── opencode-aol/
        └── (same structure)
```

Drop-in path: skills stay in `~/.claude/skills/` (cross-compatible), agents live in `opencode.json`, commands split between `opencode.json` and skill conversions, runtime state machine lives in a proper plugin.

---

## Bottom line

Opencode gives you a **strict superset** of Claude Code's extension surface, plus a client/server architecture, an event-sourced substrate, typed bus events, programmatic UI extension, and an HTTP API that lets GSD run as an independent daemon if you want.

The port isn't a rewrite — it's a mapping. Every Claude Code mechanism has an equivalent, and several opencode mechanisms have no Claude Code counterpart at all. When you finish the port, GSD and AOL don't just work on more providers — they become more capable than they are now.
