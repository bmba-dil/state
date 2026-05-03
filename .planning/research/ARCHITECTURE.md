# Architecture: `state` — Polyglot Agentic State-Machine Workflow Engine on opencode

**Domain:** Agentic workflow engine fused with adaptive-learning engine, primary host opencode
**Researched:** 2026-04-22
**Confidence:** HIGH on opencode surface (read directly); MEDIUM on teach-mode internals (AOL structure inferred from workflows + learner JSON); HIGH on auth (direct specs in claude-oauth.md and gsd2-auth-analysis.md)

---

## 0. Executive Summary

`state` is split into **six physically distinct processes/artifacts** that cooperate through opencode's event bus, HTTP API, and SQLite event store:

1. **`state-daemon`** — always-on Python user service (systemd / launchd). Owns `.state/events.sqlite`, runs the DAG scheduler, drives the build and teach kernels, serves the dashboard HTTP API even when opencode is closed.
2. **`state-worker`** — per-opencode-session Python worker, spawned on demand by the plugin shim. Holds hot state for the active session's Arc/Phase; proxies HTTP between the plugin and the daemon.
3. **`state-build`** — stdio MCP server exposing build-mode tools (plan, execute, verify, ship, etc.) to any MCP host. Shares a library with state-teach for auth/provider/event plumbing.
4. **`state-teach`** — stdio MCP server exposing teach-mode tools (concept graph ops, drill prepare/verify, mental-model queries). Never registered alongside state-build in the same session (enforced by mode gate).
5. **`@state/opencode-plugin`** — single TypeScript bundle carrying (a) the 9-hook server shim (~300 LOC) and (b) the SolidJS TUI extensions (sidebar, routes, dialogs, slots). Exports both a `PluginModule` (`server`) and a `TuiPluginModule` (`tui`).
6. **On-disk artifacts** — `.state/` directory with `build/`, `teach/`, `events.sqlite`, `auth.json`, `mode.json`, `snapshots/`. Every state transition writes both an opencode `SyncEvent` and a row in `events.sqlite`.

Everything else — kernels, verifiers, DAG scheduler, auth providers, litellm routing — are Python packages inside the daemon/worker, not separate processes.

---

## 1. Component Topology

### 1.1 Process & module diagram

```
┌─────────────────────────────── user machine ───────────────────────────────┐
│                                                                            │
│  ┌──────────────────────┐     ┌────────────────────────────────────────┐   │
│  │   state-daemon       │     │           opencode process             │   │
│  │  (user service)      │     │                                        │   │
│  │                      │◄────┤  ┌──────────────────────────────────┐  │   │
│  │  • DAG scheduler     │ HTTP│  │ @state/opencode-plugin (server)  │  │   │
│  │  • event store       │ SSE │  │   9 hook callbacks → HTTP /rpc   │  │   │
│  │  • build kernel      │─────┤  └──────────────────────────────────┘  │   │
│  │  • teach kernel      │     │                                        │   │
│  │  • auth manager      │     │  ┌──────────────────────────────────┐  │   │
│  │  • provider router   │     │  │ @state/opencode-plugin (tui)     │  │   │
│  │  • worktree service  │     │  │   sidebar / routes / dialogs     │  │   │
│  │                      │     │  └──────────────────────────────────┘  │   │
│  │  ┌──────────────┐    │     │                                        │   │
│  │  │ state-worker │    │     │  built-in: task, todo, question,       │   │
│  │  │ (per session)│────┼─────┤   permission, skill, snapshot, worktree│   │
│  │  └──────────────┘    │     │                                        │   │
│  │                      │     │  MCP clients ─────┐                    │   │
│  └──────────────────────┘     └───────────────────┼────────────────────┘   │
│           │                                       │                        │
│           ▼                                       ▼                        │
│  ┌────────────────────┐          ┌──────────────────────────┐              │
│  │ .state/            │          │ state-build  (stdio MCP) │              │
│  │  events.sqlite     │◄─────────│ state-teach  (stdio MCP) │              │
│  │  auth.json         │  shared  │  (Python, mode-gated)    │              │
│  │  mode.json         │  library └──────────────────────────┘              │
│  │  build/ARC/...     │                                                    │
│  │  teach/CONCEPT/... │                                                    │
│  │  snapshots/        │                                                    │
│  └────────────────────┘                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Call/data flow between Python pieces

| Caller | Callee | Protocol | Purpose |
|---|---|---|---|
| plugin shim (TS) | state-worker | HTTP (loopback, authenticated) | hook event → kernel action |
| state-worker | state-daemon | HTTP (loopback) | durable reads/writes, scheduler signals |
| state-worker | opencode HTTP API | HTTP + SSE | subscribe to bus, drive sessions, control TUI |
| state-daemon | opencode HTTP API | HTTP + SSE (when running) | reflect kernel state into SyncEvents |
| state-daemon | .state/events.sqlite | aiosqlite + filelock | authoritative event log |
| state-build (MCP) | state-daemon | HTTP loopback | read Arc/Phase/Slice state, emit events |
| state-teach (MCP) | state-daemon | HTTP loopback | read concept graph, emit drill observations |
| state-worker | state-build/teach (spawned) | stdio per MCP spec | dispatch mode-scoped tool calls |

**Key invariant:** `events.sqlite` is the single source of truth for planning state. Everything else is a projection or cache. The daemon is the only writer to planning tables; workers/MCP servers write through it.

### 1.3 Library layout (Python packages)

```
state/
├── state_core/            # shared: event store, auth, provider, config, schema
│   ├── events.py          # SQLite + SyncEvent mirror
│   ├── auth/              # 5-method auth (anthropic_oauth, gemini_cli, antigravity, copilot_device, api_key)
│   ├── providers/         # litellm wrapper + direct anthropic SDK escape
│   ├── scheduler.py       # pure-Python DAG scheduler
│   ├── worktree.py        # opencode-preferred / pygit2-fallback abstraction
│   ├── snapshot.py        # Step + Slice tier snapshot glue
│   └── schema.py          # pydantic models for Arc/Phase/Slice/Step/Concept
├── state_build/           # build-mode kernel (siloed)
│   ├── kernel.py          # Step state machine (discuss/plan/execute/verify)
│   ├── commands/          # ported GSD commands as Step workflows
│   ├── verifiers/         # goal-backward + rollup verifiers
│   └── mcp.py             # state-build MCP server entry
├── state_teach/           # teach-mode kernel (siloed)
│   ├── kernel.py          # Kolb-cycle state machine
│   ├── concepts.py        # concept graph ops
│   ├── drill.py           # drill engine (binds to opencode question tool)
│   ├── mental_model.py    # event-sourced projection
│   ├── personalities/     # AOL personality loaders
│   └── mcp.py             # state-teach MCP server entry
├── state_daemon/          # always-on service
│   ├── server.py          # HTTP API (FastAPI/Starlette + uvicorn)
│   ├── watchers.py        # .state/**, opencode SSE subscribers
│   └── cli.py             # `state daemon start/stop/status`
├── state_worker/          # per-session worker
│   ├── main.py            # spawned by plugin shim
│   └── bridge.py          # opencode HTTP client + state-daemon client
└── state_cli/             # `state` top-level CLI (auth login, mode set, etc.)
```

**Physical mode silo:** `state_build/` and `state_teach/` never import each other. All shared logic lives in `state_core/`. This makes the "exclusive modes" rule a Python import-graph invariant that static analysis can enforce.

---

## 2. Opencode Hook Wiring (all 9 hooks → concrete behaviors)

Every hook is implemented in `@state/opencode-plugin`'s `server` export. Each callback typically does: validate → translate payload → POST to state-worker → worker updates event store → returns mutated `output`.

| Hook | Input | Mode | State behavior |
|---|---|---|---|
| `chat.message` | sessionID, parts[] | both | **Prompt guard + state injection.** Parses message for `/state:*` intent, rejects cross-mode commands (build command in teach session), appends active Step/Concept ID hint as a text part for the LLM. Writes `state.message.received` sync event. |
| `tool.execute.before` | tool, sessionID, callID → args | both | **Read-guard / workflow-guard.** Blocks writes outside the active Slice's worktree; blocks `task` spawn of non-allowed subagents; rewrites `read` args to resolve `.state/` paths. In teach mode, blocks `bash` on learner code except inside scaffold sandbox. Writes `state.tool.intercepted`. |
| `tool.execute.after` | tool, callID, args → output | both | **Observation capture.** Teach mode: classify tool output (correct attempt, error, unclear) and feed to mental_model. Build mode: verify output against Step's `verify_contract`; auto-advance Step state if verify passes. Writes `state.tool.observed` with classified kind. |
| `permission.ask` | Permission → status | both | **Auto-approve within scope.** Build: if edit path is inside current Slice's worktree AND Step is in `execute` state AND ruleset permits → `allow`. Teach: if edit is under `./learner-work/` AND scaffold allows → `allow`; otherwise forward. Writes `state.permission.decided`. |
| `event` | generic bus event | both | **Universal observer.** State machine subscribes to `session.idle`, `worktree.ready`, `worktree.failed`, `question.replied`, `permission.replied`, `todo.updated`, `file.edited`, `mcp.tools.changed`. Each triggers a kernel transition (see §6, §8, §9). |
| `experimental.chat.system.transform` | sessionID, model → system[] | both | **State injection.** Prepends mode banner (`MODE: build / Arc A3 / Phase 7 / Slice 2 / Step 17: execute`) + active artifact content (STEP.md frontmatter, verify contract, dependencies). Teach mode prepends active concept card + Kolb stage + teaching-personality preamble. |
| `experimental.session.compacting` | sessionID → {context, prompt} | both | **Phase-aware compaction.** Injects "preserve these IDs and artifacts verbatim" into compaction prompt: active Step ID, last 3 verify results, open gray-area decisions, drill-question answers pending verification. |
| `chat.params` | sessionID → temperature/topP/etc. | both | **Model profile resolver.** Reads Step's `model_profile` frontmatter (or Concept's teaching-style). Build: low-temp (0.2) for verify, mid (0.5) for execute, higher (0.8) for discuss. Teach: per-personality temperature (socratic-gadfly 0.9, patient-mentor 0.4). Also sets provider-specific options (e.g. Anthropic `thinking: { type: "enabled", budget_tokens: N }` for extended thinking). |
| `command.execute.before` | command, arguments → parts[] | both | **Slash command expansion.** `/state:build:plan-phase 7` resolves to: prepend `.planning/PHASE.md` content + `.planning/STATE.md` + all child SLICE.md frontmatter + verify-contract. Teach equivalent pulls concept card + mastery history. |
| `shell.env` | cwd, sessionID → env | both | **Environment injection.** Sets `STATE_MODE`, `STATE_ARC_ID`, `STATE_PHASE_ID`, `STATE_SLICE_ID`, `STATE_STEP_ID`, `STATE_WORKTREE`, `STATE_DAEMON_URL`, `STATE_AUTH_JSON`. Every bash call the LLM makes can cd/read-file against the active scope without guessing. |

**Mode enforcement:** hooks first consult `.state/mode.json`. If `mode == "teach"` and an incoming `tool.execute.before` is for a build-mode MCP tool (`mcp__state-build__*`), hook throws DeniedError. See §7 for the full enforcement story.

---

## 3. TUI Extension Slots

`@state/opencode-plugin`'s `tui` export registers into opencode's TUI via `TuiPluginApi` (see `packages/plugin/src/tui.ts:449`). All JSX is SolidJS (the `@opentui/solid` binding opencode ships with).

| PROJECT.md feature | Opencode API | Slot / mechanism |
|---|---|---|
| **Sidebar: build progress** | `ui.Slot name="sidebar_content"` | SolidJS component subscribes to `state.session.*` + daemon SSE, renders active Arc/Phase/Slice tree with Step status (idle/discussing/planning/executing/verifying/done/blocked) |
| **Sidebar: teach concept state** | same slot, mode-gated by `.state/mode.json` | Renders current concept card, Kolb stage, confidence bar, next-drill timer |
| **Build dashboard** | `route.register({ name: "state.build.dashboard" })` | Full route at `/state/build/dashboard`. Burndown by Slice, verify-pass rate, active worktrees, DAG viz |
| **Teach dashboard** | `route.register({ name: "state.teach.dashboard" })` | Concepts graph, mastery heatmap, confidence-over-time, mistake cluster |
| **DAG viewer** | `route.register({ name: "state.dag" })` | Renders Arc/Phase/Slice/Step DAG with topological layout; click → focus in sidebar. Both modes use this. |
| **Gray-area decision dialog** | `ui.DialogSelect` via `ui.dialog.replace(...)` | Triggered when a build-mode kernel hits an ambiguous branch. Options = structured decision set, `custom: true` for escape hatch. Persists to `state.decision.made` event. |
| **Drill question dialog** | `ui.DialogSelect` OR direct `question.ask` through HTTP API | Preferred: teach kernel calls `client.question.ask(...)` so the answer flows through opencode's native `question.replied` bus event. Fallback: custom DialogSelect for multi-step drills with inline explanations. |
| **Statusline (both modes)** | `ui.Slot name="sidebar_footer"` or `home_footer` | One-line mode + active scope + unblocked Step count. |
| **Toasts** | `ui.toast(...)` | Phase transitions, verify pass/fail, concept mastery, auth refresh events. |
| **Prompt hint** | `ui.Slot name="session_prompt_right"` | Shows model + token cost live + "Step N.m" indicator. |
| **Custom commands** | `command.register(() => TuiCommand[])` | `/state:*` keybinds and quick-switch commands. |
| **Prompt inject on drill** | `ui.Prompt`-replacement in drill route | During a drill, replace the session prompt input with a typed drill input that shows a timer and disables tool use. |

**Key constraint:** TUI-side code does not import `state_build` or `state_teach` Python packages; it talks exclusively to `state-daemon` over HTTP + opencode's own event bus. This makes the TS bundle small and keeps the mode silo intact.

---

## 4. MCP Tool Surfaces

Two servers, each a Python process spawned from `state_build.mcp` / `state_teach.mcp`. Both depend on `state_core` (auth, events, schema). Candidate tool inventories below — roadmap refines exact names.

### 4.1 `state-build` tools

Mapped to GSD's command catalogue (ported / redesigned / dropped per PROJECT.md):

| Tool | GSD precedent | Behavior |
|---|---|---|
| `state_build__plan_phase` | `/gsd:plan-phase` | Produce PHASE.md + child SLICE.md drafts from Arc context; emits `state.phase.planned` |
| `state_build__execute_phase` | `/gsd:execute-phase` | Start scheduler for all unblocked Slices under a Phase |
| `state_build__discuss_step` | (new) | Enter Step discuss state (sets `chat.params` to high-temp) |
| `state_build__plan_step` | (inlined) | Draft STEP.md: goal, verify_contract, depends_on |
| `state_build__verify_step` | `/gsd:verify` | Run Step's verify contract (tests, LSP diagnostics, custom script) |
| `state_build__advance_step` | (state-machine) | Move Step to next cycle state or mark blocked |
| `state_build__research_phase` | `/gsd:research-phase` | Spawn research subagents via opencode `task` tool with `subagent_type="researcher"` |
| `state_build__roadmap` | `/gsd:roadmapper` | Generate Arc/Phase skeleton from PROJECT.md |
| `state_build__intel` | `/gsd:intel` | Run intel subagent (read-only) and attach findings |
| `state_build__map_codebase` | `/gsd:map-codebase` | Generate CODEMAP.md via subagent |
| `state_build__code_review` | `/gsd:code-review` | Kick off review subagent on Slice diff |
| `state_build__code_review_fix` | `/gsd:code-review-fix` | Consume review, emit fix Steps |
| `state_build__ship_slice` | `/gsd:ship` | Merge Slice worktree → primary; tag release |
| `state_build__progress` | `/gsd:progress` | Snapshot of current Arc tree |
| `state_build__stats` | `/gsd:stats` | Rollup stats (verify pass rate, cycle time per Step, etc.) |
| `state_build__audit_uat` | `/gsd:audit-uat` | Run UAT audit verifier across Phase |
| `state_build__audit_milestone` | `/gsd:audit-milestone` | Arc-level audit |
| `state_build__debug` | `/gsd:debug` | Spawn debug subagent on a failing verify |
| `state_build__forensics` | `/gsd:forensics` | Replay events.sqlite → reconstruct failure path |
| `state_build__pause_resume` | `/gsd:pause-work` + `/gsd:resume-work` | Flip Step state to paused; restore later |
| `state_build__thread` | `/gsd:thread` | Spawn cross-Phase thread (side investigation) |
| `state_build__workstreams` | `/gsd:workstreams` | List unblocked Slices, concurrent-safe ones flagged |
| `state_build__snapshot_step` | (new) | Step-tier snapshot via opencode `Snapshot.track` |
| `state_build__revert_step` | (new) | Revert to Step snapshot via `Snapshot.revert` |
| `state_build__decision_record` | `gray-area decisions` | Persist a typed decision from the gray-area dialog |

### 4.2 `state-teach` tools

Mapped from AOL workflows (`teach.md`, `build-subject.md`, `new.md`, `state.md`):

| Tool | AOL precedent | Behavior |
|---|---|---|
| `state_teach__subject_list` | `aol subject list` | Enumerate installed subjects |
| `state_teach__subject_install` | `aol subject install` | Register subject (local or remote) |
| `state_teach__subject_resolve` | `aol subject resolve` | Slug → canonical id |
| `state_teach__concept_next` | (curriculum engine) | Pick next concept given mastery + prereqs |
| `state_teach__concept_teach` | `aol-concept-teacher` skill | Drive Kolb cycle for a concept |
| `state_teach__drill_prepare` | `aol drill prepare` | Generate drill items from concept |
| `state_teach__drill_verify` | `aol drill verify` | Grade drill submission, record mastery update |
| `state_teach__drill_stats` | `aol drill stats` | Mastery projection for concept |
| `state_teach__observation_record` | (mental-modeler subagent) | Append an observation event |
| `state_teach__mental_model_query` | (new) | Projected current mental model |
| `state_teach__scaffold_set` | (scaffolding-mentor) | Adjust scaffold level for concept |
| `state_teach__personality_set` | (teaching-style) | Swap active personality |
| `state_teach__mode_select` | `active-mode.json` | curriculum / drill / review / resume |
| `state_teach__review_start` | (review branch) | Enter review Kolb cycle for a mastered concept |
| `state_teach__verify_learning` | (learning verifier) | Cross-concept integration verifier (AOL-style) |

### 4.3 Shared library (in `state_core`, not MCP tools)

Not exposed as tools; imported by both servers:
- Auth manager (login, token refresh, round-robin)
- Event log (read/write `events.sqlite`, emit SyncEvent)
- Provider router (litellm + anthropic-SDK escape)
- Schema validators (pydantic models)
- Daemon HTTP client

Any tool that the MCP needs auth/provider/event access to gets it via this shared lib — never by duplicating logic.

---

## 5. Event Flow (Dual-Write)

### 5.1 Canonical trace: `/state:build:verify 17.3` issued by user in opencode

```
1. User types command in opencode TUI
2. opencode dispatches slash command → fires command.execute.before hook
     plugin shim: expands $1, injects PHASE.md + STEP.md content
3. opencode prompts LLM; LLM tool-calls `mcp__state-build__verify_step`
4. tool.execute.before hook fires
     plugin shim → POST state-worker: /hook/tool-before
       state-worker checks mode.json, scope, writes state.tool.intercepted
       to events.sqlite (then mirrors as SyncEvent via state-daemon)
5. MCP tool executes in state-build process
     state-build reads STEP.md verify_contract
     state-build POSTs state-daemon: /events/append state.verify.started
       daemon writes row (seq++) to events.sqlite
       daemon calls opencode HTTP: sync.publish(state.verify.started)
       → SyncEvent fires into opencode bus; TUI sidebar re-renders
6. state-build runs the verifier (tests, LSP query, etc.)
7. state-build POSTs state-daemon: /events/append state.verify.passed
     daemon: dual-write (SQLite + opencode SyncEvent)
     opencode bus fan-out: plugin's `event` hook fires on daemon-mirror event,
       kernel advances Step state machine: verify → done
     kernel writes state.step.advanced → daemon → SyncEvent
     TUI sidebar flips Step to "done"; toast shows
8. MCP tool returns to LLM
9. tool.execute.after hook fires
     plugin shim → POST state-worker: /hook/tool-after
     worker records verify metadata (duration, pass/fail) against the Step
```

### 5.2 Dual-write contract

- **Primary writer:** `state-daemon` (the only process that writes to `events.sqlite`).
- **Secondary writer:** opencode's `SyncEvent.run` path, invoked by the daemon over HTTP. This gives opencode's TUI live updates and inter-client replay for free.
- **Failure mode:** if opencode is down, daemon still writes to SQLite. When opencode returns, daemon replays missed events by reading `events.sqlite` since last known `sync_seq` (opencode's own sync mechanism — `sync.replay` HTTP op — consumes those).
- **Schemas:** defined once in `state_core/schema.py` (pydantic). A small adapter generates the Zod schema for `SyncEvent.define` so Python and TS stay in lockstep.

### 5.3 Event taxonomy (`state.*`)

All 28+ event types grouped by aggregate:

| Aggregate | Events |
|---|---|
| Arc | `state.arc.created`, `state.arc.retired`, `state.arc.updated` |
| Phase | `state.phase.planned`, `state.phase.started`, `state.phase.verified`, `state.phase.completed` |
| Slice | `state.slice.planned`, `state.slice.worktree_ready`, `state.slice.shipped`, `state.slice.reverted` |
| Step | `state.step.discussed`, `state.step.planned`, `state.step.executed`, `state.step.verify_started`, `state.step.verify_passed`, `state.step.verify_failed`, `state.step.advanced`, `state.step.blocked`, `state.step.snapshotted`, `state.step.reverted` |
| Concept | `state.concept.introduced`, `state.concept.observed`, `state.concept.drilled`, `state.concept.mastered`, `state.concept.reviewed` |
| Drill | `state.drill.prepared`, `state.drill.submitted`, `state.drill.graded` |
| Mode | `state.mode.activated` |
| Decision | `state.decision.asked`, `state.decision.made` |
| Auth | `state.auth.refreshed`, `state.auth.rotated` |

Every event has `{id, seq, aggregateID, type, data, ts}`. `aggregateID` is Arc ID / Step ID / Concept ID etc. so SyncEvent's per-aggregate ordering guarantees hold.

---

## 6. Worktree Orchestration

### 6.1 Decision tree

```
Is host opencode?
├── YES: call opencode HTTP worktree.create → ready
└── NO (Claude Code / Gemini CLI / Qwen Code / standalone):
      use pygit2 fallback in state_core.worktree
```

The plugin shim POSTs the daemon; the daemon detects host via `STATE_HOST` env var set by shim (or absence of daemon-discovered opencode server URL).

### 6.2 Per-Slice worktree lifecycle

```
state.slice.planned
  └─▶ scheduler picks Slice → ensure worktree
        ├─ worktree name: slug(slice.title)
        ├─ branch: state/<arc>/<phase>/<slice>
        ├─ opencode path: POST /worktree → worktree.ready bus event
        └─ pygit2 path: repo.create_worktree() + bootstrap

state.slice.worktree_ready
  └─▶ scheduler assigns Steps to Slice's worktree
        each Step's tool.execute.before hook scopes edits to worktree path

state.slice.shipped
  └─▶ merge into primary (ours strategy for state artifacts, normal for code)
        opencode path: POST /worktree/remove
        pygit2 path: remove_worktree() + prune branch

state.slice.reverted
  └─▶ keep worktree, restore Slice snapshot
```

### 6.3 Snapshot composition

- **Step tier:** every Step creates a snapshot at `execute` entry and another at `verify` entry. Uses opencode `Snapshot.track()` (separate git-dir under `~/.local/share/state/snapshot/<project>/<worktree-hash>`). Revert via `Snapshot.revert`.
- **Slice tier:** a Slice snapshot = named reference to the final Step snapshot of that Slice. Stored in events.sqlite as `state.slice.shipped.snapshot_hash`. Revert = `Snapshot.restore` to that hash.
- **Cross-tier rollback:** `state_build__revert_slice` = revert all Step snapshots in chronological order (newest first) until the Slice-tier hash is reached. Events emitted per Step.

### 6.4 Who creates, who destroys

| Action | Trigger | Actor |
|---|---|---|
| Create worktree | Scheduler picks unblocked Slice | state-daemon (opencode HTTP or pygit2) |
| Bootstrap worktree | Created | opencode auto-bootstraps via InstanceBootstrap |
| Destroy worktree | `state.slice.shipped` OR explicit `state_build__abandon_slice` | state-daemon |
| Create step snapshot | Step enters execute/verify | Plugin `event` hook → worker → daemon calls `Snapshot.track` |
| Purge old snapshots | opencode's 7-day GC (unchanged) | opencode (we don't override) |

---

## 7. Mode Enforcement Boundary

**Hard rule (PROJECT.md):** Build and Teach never run in the same invocation.

**Physical enforcement layers (defense in depth):**

1. **Disk layer** — `.state/mode.json` has `{mode: "build"|"teach", set_at: ISO8601, by: "cli"|"plugin"}`. CLI command `state mode set build` writes it. A project may have both `build/` and `teach/` dirs, but only one mode active at a time.

2. **MCP registration layer** — `opencode.json` references both servers but with mutually-exclusive `enabled` flags computed by a small wrapper. In practice: the plugin shim reads `.state/mode.json` at boot; if `mode == "build"` it returns a config patch disabling `state-teach` and vice versa via `config` hook. MCP plumbing is invoked through `Config.Service` so toggling is a hot-reload.

3. **Plugin hook layer** — every hook consults `.state/mode.json` once per call (cheap, cached by mtime). `tool.execute.before` DENIES tool IDs prefixed `mcp__state-teach__*` when mode is build.

4. **Command dispatch layer** — `command.execute.before` inspects the command name. `/state:build:*` in teach mode → inject an error message via `output.parts` instead of expanding. Same in reverse.

5. **Daemon layer** — daemon exposes `/events/append` with a mode validation middleware. Event type `state.concept.*` rejected when mode is build. This is the authoritative gate — both MCP servers write through the daemon, so no client can sneak in cross-mode writes.

6. **Python import-graph layer** — `state_build` never imports `state_teach` and vice versa. A linter rule (import-guard) fails CI on violation. This makes the silo structural, not just runtime.

**Canonical enforcement point:** daemon's HTTP middleware. All other layers are UX affordances; the daemon is the last line.

**Switching modes:** `state mode set teach` → write mode.json → daemon reloads → daemon broadcasts `state.mode.activated` SyncEvent → plugin's `event` hook triggers opencode `config` reload → MCP servers restart via the config reload cycle.

---

## 8. Build Kernel Internals

### 8.1 Step state machine

A Step is the only tier that runs the full discuss/plan/execute/verify cycle. Arc/Phase/Slice are scoping containers with simpler lifecycles (planned / in_progress / shipped).

```
                ┌───── create ──────┐
                ▼                    │
       ┌──────────────┐              │
       │   IDLE       │──skip───────▶│
       └──────┬───────┘              │
              │ start                │
              ▼                      │
       ┌──────────────┐              │
       │  DISCUSSING  │─────────────▶│
       └──────┬───────┘              │
              │ plan_accepted        │
              ▼                      │
       ┌──────────────┐              │
       │   PLANNING   │─────────────▶│
       └──────┬───────┘              │
              │ execute_approved     │
              ▼                      │
       ┌──────────────┐    fail      │
       │  EXECUTING   │───────────┐  │
       └──────┬───────┘           │  │
              │ execute_done      │  │
              ▼                   │  │
       ┌──────────────┐           │  │
       │  VERIFYING   │           │  │
       └──────┬───────┘           │  │
         pass │                   │  │
              ▼                   │  │
       ┌──────────────┐           │  │
       │     DONE     │           │  │
       └──────────────┘           │  │
                                  ▼  ▼
                              ┌──────────────┐
                              │   BLOCKED    │─unblock──▶ (back to EXECUTING)
                              └──────────────┘
                                   │
                                   ▼ abandon
                              ┌──────────────┐
                              │  ABANDONED   │
                              └──────────────┘
```

Pseudo-code:

```python
class StepMachine:
    async def on_event(self, event: StateEvent) -> None:
        match (self.state, event.type):
            case (IDLE, "state.step.discussed"):
                self.enter(DISCUSSING)
            case (DISCUSSING, "state.step.planned"):
                self.enter(PLANNING)
            case (PLANNING, "state.step.executed"):
                await self.snapshot(tier="step", reason="pre_execute")
                self.enter(EXECUTING)
            case (EXECUTING, "state.step.verify_started"):
                await self.snapshot(tier="step", reason="pre_verify")
                self.enter(VERIFYING)
            case (VERIFYING, "state.step.verify_passed"):
                self.enter(DONE)
                await self.publish("state.step.advanced")
                await self.scheduler.notify_completed(self.step_id)
            case (VERIFYING, "state.step.verify_failed"):
                self.enter(EXECUTING)
                await self.log_failure(event.data.reason)
            case (_, "state.step.blocked"):
                self.enter(BLOCKED)
            case (BLOCKED, "state.step.unblocked"):
                self.enter(EXECUTING)
```

### 8.2 Arc / Phase / Slice / Step schema

All persisted as Markdown with YAML frontmatter plus pydantic validation.

**ARC.md frontmatter:**
```yaml
id: arc-01
title: Kernel & Event Store
status: in_progress  # planned | in_progress | shipped | abandoned
goal: ...            # one-line outcome
success_criteria:    # list of measurable outcomes
  - events.sqlite writable from all processes
  - 100% SyncEvent mirror parity
depends_on: []       # other Arc IDs
phases: [phase-01, phase-02, phase-03]
opencode_surface:    # required per PROJECT.md mandate
  - packages/opencode/src/sync/
  - packages/opencode/src/storage/
```

**PHASE.md frontmatter:** same + `arc_id`, `slices: [...]`, `verify_rollup: [...]` (criteria to consider the Phase verified).

**SLICE.md frontmatter:** same + `phase_id`, `worktree: {name, branch, dir}`, `steps: [...]`, `snapshot_ref` (slice-tier hash at ship time).

**STEP.md frontmatter (the busiest):**
```yaml
id: step-17.3
slice_id: slice-17
title: Implement verify runner
state: verifying    # idle|discussing|planning|executing|verifying|done|blocked|abandoned
goal: ...
verify_contract:
  - type: tests
    cmd: pytest tests/verify_runner/
  - type: lsp
    path: src/state_build/verifiers/
    severity: error
    allow: 0
  - type: script
    cmd: python scripts/smoke_verify.py
depends_on:
  - id: step-17.1
    kind: blocks          # blocks | soft | data
  - id: step-16.2
    kind: data
model_profile:
  provider: anthropic
  model: claude-opus-4-7
  temperature: 0.2
  thinking: { enabled: true, budget_tokens: 4000 }
subagent_type: state-executor
snapshots:
  pre_execute: abc123
  pre_verify: def456
```

`depends_on` edge kinds:
- `blocks` — target must be DONE before this can start (hard DAG edge)
- `soft` — target should be DONE but scheduler may override
- `data` — target produces artifacts this step consumes (hard, plus copies artifact path)

### 8.3 DAG scheduler

Pure-Python, ~300 LOC. Runs inside state-daemon.

```python
async def schedule_tick(arc_id: ArcID) -> list[StepID]:
    """Return all unblocked Steps under this Arc, ready for concurrent dispatch."""
    steps = await event_store.load_all_steps(arc_id)
    blocked: set[StepID] = set()
    for s in steps:
        if s.state in {DONE, ABANDONED}:
            continue
        for dep in s.depends_on:
            if dep.kind in {"blocks", "data"}:
                target = steps[dep.id]
                if target.state != DONE:
                    blocked.add(s.id)
                    break
    ready = [s for s in steps if s.state == IDLE and s.id not in blocked]
    ready.sort(key=lambda s: (s.slice_id, s.id))  # stable for reproducibility
    return [s.id for s in ready]

async def dispatch(step_ids: list[StepID]) -> None:
    # Group by Slice → one worktree per Slice is the concurrency unit
    by_slice = defaultdict(list)
    for sid in step_ids:
        step = await load(sid)
        by_slice[step.slice_id].append(step)

    # Concurrent by Slice (different worktrees), serial within a Slice
    await asyncio.gather(*[run_slice(steps) for steps in by_slice.values()])
```

Scheduler is **reactive**: recomputes on every `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned`. No polling loop.

---

## 9. Teach Kernel Internals

### 9.1 Concept graph schema

Event-sourced projection stored as JSON at `.state/teach/concepts/<subject>.json`. Rebuildable from `events.sqlite` `state.concept.*` events (AOL precedent: `knowledge-graph.json`).

```json
{
  "schema_version": 2,
  "subject_id": "python_core",
  "concepts": [
    {
      "id": "variables",
      "name": "Variables",
      "mastery_probability": 0.72,
      "bloom_level": "APPLY",
      "scaffold_level": 2,
      "demonstration_count": 14,
      "prerequisites": [],
      "last_demonstrated_at": "2026-04-20T14:30:00Z",
      "next_review_at": "2026-04-24T00:00:00Z",
      "kolb_history": [
        {"stage": "CE", "ts": "..."},
        {"stage": "RO", "ts": "..."},
        ...
      ]
    },
    ...
  ],
  "edges": [
    {"from": "variables", "to": "control_flow", "kind": "prereq"}
  ]
}
```

### 9.2 Kolb-cycle state machine

Each concept under active teaching has a Kolb machine:

```
┌─ CE (Concrete Experience) ──► LLM narrates scenario, learner observes
│         │
│         ▼
│   RO (Reflective Observation) ──► question.ask via opencode question tool
│         │
│         ▼
│   AC (Abstract Conceptualization) ──► learner articulates rule
│         │
│         ▼
│   AE (Active Experimentation) ──► drill: drill_prepare + drill_verify
│         │
│         ▼ ─ pass criterion (mastery_probability >= threshold) ─► MASTERED
│         │
│         ▼ ─ fail                                                  │
└─────────┘ (re-enter CE with scaffold_level bumped up)             │
                                                                    ▼
                                                        re-enters REVIEW cycle
                                                        per next_review_at
```

```python
class KolbMachine:
    async def on_event(self, event: StateEvent) -> None:
        match (self.stage, event.type):
            case (CE, "state.concept.observed"):
                self.enter(RO)
                await self.teach.ask_reflection()     # opencode question tool
            case (RO, "question.replied"):
                await self.observe(event.answer)
                self.enter(AC)
            case (AC, "state.concept.articulated"):
                self.enter(AE)
                await self.drill.prepare(self.concept_id)
            case (AE, "state.drill.graded"):
                if event.data.score >= THRESHOLD:
                    await self.update_mastery(delta=+0.15)
                    if self.projected_mastery() >= MASTERY_CUTOFF:
                        await self.publish("state.concept.mastered")
                        self.enter(MASTERED)
                    else:
                        self.scaffold_level = max(0, self.scaffold_level - 1)
                        self.enter(CE)
                else:
                    self.scaffold_level += 1
                    self.enter(CE)
```

### 9.3 Drill engine integration with opencode `question` tool

The drill engine generates typed questions and dispatches through opencode's native `question.ask`:

```python
async def run_drill(concept_id: ConceptID, session_id: SessionID):
    items = await generate_drill_items(concept_id)
    # Build opencode Question.Info[] with labels + descriptions
    req = [{
        "question": item.prompt,
        "header": item.header[:30],
        "options": [{"label": o.label, "description": o.desc} for o in item.options],
        "multiple": item.multi_select,
        "custom": True,
    } for item in items]
    # Call opencode HTTP: question.ask → blocks until user replies
    answers = await opencode_client.question.ask(session_id=session_id, questions=req)
    # Grade and write observations
    for item, answer in zip(items, answers):
        await record_observation(concept_id, item, answer)
    score = grade(items, answers)
    await publish("state.drill.graded", {concept_id, score, items})
    return score
```

This gives us typed audit history for free (`question.asked` / `question.replied` SyncEvents), no custom drill UI needed for the common case.

### 9.4 Mental-model projection

`MENTAL-MODEL.json` at `.state/teach/<learner>/mental-model.json` is a pure projection of the event stream. Rebuildable by replaying all `state.concept.observed` + `state.drill.graded` + `state.concept.mastered` events for that learner.

```python
def project_mental_model(events: Iterable[StateEvent]) -> MentalModel:
    mm = MentalModel()
    for e in events:
        match e.type:
            case "state.concept.observed":
                mm.concepts[e.data.concept_id].demos += 1
                mm.concepts[e.data.concept_id].last_seen = e.ts
            case "state.drill.graded":
                c = mm.concepts[e.data.concept_id]
                c.mastery_probability = bayes_update(
                    prior=c.mastery_probability,
                    evidence=e.data.score,
                )
                c.demonstration_count += 1
            case "state.concept.mastered":
                mm.concepts[e.data.concept_id].mastered_at = e.ts
    return mm
```

---

## 10. Auth Layer Architecture

### 10.1 Provider abstraction

```
state_core.auth/
├── base.py              # AuthMethod protocol + credential container
├── store.py             # auth.json I/O + filelock + multi-cred array
├── refresh.py           # refresh-lock + round-robin
└── providers/
    ├── anthropic_oauth.py    # claude-oauth.md stealth flow
    ├── gemini_cli.py         # Google OAuth, free-tier code assist
    ├── antigravity.py        # Google OAuth, Gemini-3/Claude/GPT-OSS via GCloud
    ├── copilot_device.py     # GitHub device-code flow
    └── api_key.py            # plain key (Anthropic direct, OpenAI, etc.)
```

Every provider implements:

```python
class AuthMethod(Protocol):
    async def login(self) -> Credential: ...
    async def refresh(self, cred: Credential) -> Credential: ...
    def is_token(self, val: str) -> bool: ...
    def http_headers(self, cred: Credential) -> dict[str, str]: ...
    def is_expired(self, cred: Credential, now: float) -> bool: ...
```

Anthropic OAuth's `http_headers` returns the stealth set verbatim (`user-agent: claude-cli/...`, `x-app: cli`, `anthropic-beta: claude-code-20250219,oauth-2025-04-20,...`). Non-negotiable per claude-oauth.md.

### 10.2 auth.json layout

```json
{
  "schema_version": 1,
  "providers": {
    "anthropic": [
      {
        "type": "oauth",
        "access": "sk-ant-oat-...",
        "refresh": "...",
        "expires": 1712345678,
        "account_id": "...",
        "enterprise_url": null
      },
      {
        "type": "api",
        "key": "sk-ant-api03-..."
      }
    ],
    "google.gemini_cli": [...],
    "google.antigravity": [...],
    "github.copilot": [...]
  },
  "last_rotation": { "anthropic": 0 }
}
```

Array-per-provider preserves GSD 2's multi-credential round-robin shape. chmod 600. First-run bootstrap tries to import from `~/.local/share/opencode/auth.json` when present (enhancement, not fallback).

### 10.3 Refresh-lock mechanism

```python
async def get_usable_credential(provider: str) -> Credential:
    async with filelock(auth_json_path):
        store = load(auth_json_path)
        creds = store.providers[provider]
        # rotate on expiration + rate-limit-seen flags
        for i, cred in cycle_from(creds, store.last_rotation[provider]):
            if not cred.is_expired(now()):
                store.last_rotation[provider] = i
                save(store)
                return cred
            refreshed = await providers[cred.type].refresh(cred)
            creds[i] = refreshed
            save(store)
            return refreshed
```

Filelock via `filelock` library (committed library lock). One refresh at a time across daemon + MCP servers + CLI.

### 10.4 Provider routing (litellm + Anthropic direct)

`state_core.providers.route(model_spec)` returns either a litellm client or the Anthropic SDK with stealth headers. Build-mode's verify path uses Anthropic direct for extended-thinking. All other paths go through litellm.

---

## 11. Data Contracts

### 11.1 `.state/` on-disk layout

```
.state/
├── auth.json                   # chmod 600, portable
├── mode.json                   # { "mode": "build"|"teach", ... }
├── events.sqlite               # WAL-mode; the source of truth
├── events.sqlite-wal
├── events.sqlite-shm
├── daemon.sock                 # unix socket for loopback HTTP (optional)
├── daemon.pid
├── config.toml                 # static config (schedulers, thresholds)
├── build/
│   ├── arcs/
│   │   └── <arc-slug>/ARC.md
│   ├── phases/
│   │   └── <phase-slug>/PHASE.md
│   ├── slices/
│   │   └── <slice-slug>/SLICE.md
│   └── steps/
│       └── <step-id>/STEP.md
├── teach/
│   ├── subjects/
│   │   └── <subject>/
│   │       ├── SUBJECT.md
│   │       └── concepts/
│   │           └── <concept-id>/CONCEPT.md
│   ├── learners/
│   │   └── <learner>/
│   │       ├── mental-model.json          # projection
│   │       ├── knowledge-graph.json       # projection (AOL-compat)
│   │       ├── confidence.jsonl           # append-only (AOL-compat)
│   │       └── mistakes.jsonl             # append-only (AOL-compat)
│   └── personalities/                     # AOL personality ports
├── snapshots/
│   └── <project-hash>/                    # opencode Snapshot storage
├── skills/                                # opencode-scanned (per PROJECT decision)
└── logs/
    ├── daemon.log
    └── worker-<pid>.log
```

### 11.2 CONCEPT.md frontmatter

```yaml
id: variables
subject_id: python_core
name: Variables
bloom_level: APPLY
prerequisites: []
drill_questions_path: drills.yaml
scaffold_levels:
  0: "Learner writes from scratch"
  1: "Signature + docstring provided"
  2: "Partial implementation, blanks to fill"
  3: "Multiple-choice walkthrough"
teaching_modes: [scaffolded, socratic, primm, constructivist]
observation_rules:
  - trigger: tool_error
    weight: -0.1
  - trigger: verify_pass
    weight: +0.15
```

### 11.3 SQLite schema

```sql
-- Event log (authoritative)
CREATE TABLE events (
  id TEXT PRIMARY KEY,           -- ULID
  seq INTEGER NOT NULL,          -- per-aggregate sequence
  aggregate_type TEXT NOT NULL,  -- 'arc' | 'phase' | 'slice' | 'step' | 'concept' | 'drill' | 'decision' | 'auth' | 'mode'
  aggregate_id TEXT NOT NULL,
  type TEXT NOT NULL,            -- 'state.step.verify_passed' etc.
  data TEXT NOT NULL,            -- JSON
  ts TEXT NOT NULL,              -- ISO8601
  synced_to_opencode INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_events_agg ON events(aggregate_id, seq);
CREATE INDEX idx_events_ts ON events(ts);
CREATE INDEX idx_events_unsynced ON events(synced_to_opencode) WHERE synced_to_opencode = 0;

-- Per-aggregate current sequence (for conflict detection)
CREATE TABLE aggregate_seq (
  aggregate_id TEXT PRIMARY KEY,
  seq INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);

-- Step cache (projection, rebuildable)
CREATE TABLE steps (
  id TEXT PRIMARY KEY,
  slice_id TEXT NOT NULL,
  state TEXT NOT NULL,
  title TEXT NOT NULL,
  frontmatter TEXT NOT NULL,  -- JSON dump of STEP.md frontmatter
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_steps_slice ON steps(slice_id);
CREATE INDEX idx_steps_state ON steps(state);

-- Slice cache
CREATE TABLE slices (
  id TEXT PRIMARY KEY,
  phase_id TEXT NOT NULL,
  state TEXT NOT NULL,
  worktree_dir TEXT,
  worktree_branch TEXT,
  frontmatter TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Concepts cache (teach mode)
CREATE TABLE concepts (
  id TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  learner_id TEXT NOT NULL,
  mastery_probability REAL NOT NULL,
  scaffold_level INTEGER NOT NULL,
  bloom_level TEXT NOT NULL,
  frontmatter TEXT NOT NULL,
  last_drilled_at TEXT,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_concepts_learner ON concepts(learner_id);

-- Decisions (gray area + auditable)
CREATE TABLE decisions (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  question TEXT NOT NULL,
  options TEXT NOT NULL,         -- JSON
  answer TEXT,
  answered_at TEXT,
  reason TEXT
);

-- Tool call metadata (for verifier / forensics)
CREATE TABLE tool_calls (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  call_id TEXT NOT NULL,
  tool TEXT NOT NULL,
  step_id TEXT,
  concept_id TEXT,
  args TEXT,
  output TEXT,
  verdict TEXT,                   -- 'correct'|'error'|'unclear' for teach
  ts TEXT NOT NULL
);

-- Auth rotation log (does NOT store credentials — those stay in auth.json)
CREATE TABLE auth_rotations (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  index_used INTEGER NOT NULL,
  ts TEXT NOT NULL,
  outcome TEXT NOT NULL           -- 'ok'|'refresh_ok'|'rate_limited'|'failed'
);
```

Rebuilding from events: `steps`, `slices`, `concepts`, `tool_calls` are all rebuildable by replaying `events` table. `aggregate_seq` is derivable. `decisions` and `auth_rotations` are append-only with their own data.

---

## 12. Cross-Mode Integration Points

**Shared (build + teach both use):**
- `state_core.events` — same `events.sqlite`, event type prefixes disjoint (`state.step.*` vs `state.concept.*`)
- `state_core.auth` — single `auth.json`, both modes call through it
- `state_core.providers` — same litellm + anthropic escape
- `state_core.scheduler` — teach mode uses it for review-due concepts queue
- `state_core.snapshot` — teach uses for sandbox scaffold reset
- `state_core.worktree` — teach uses for "coding-partner" flows (learner's work branch)
- `@state/opencode-plugin` — one TUI bundle; mode-gated slot rendering
- Daemon HTTP + SQLite
- Opencode hooks (same 9)
- TUI DAG viewer route (both render their own tree)

**Isolated (mode silos — do NOT share):**
- `state_build` package never imports `state_teach` (enforced by import-guard)
- Separate MCP servers; only one registered at a time
- Separate on-disk dirs (`build/` vs `teach/`)
- Separate command namespaces (`/state:build:*` vs `/state:teach:*`)
- Separate event type prefixes
- Separate Python subagent definitions (coder / researcher / reviewer vs concept-teacher / drill-grader / mental-modeler)
- Separate sidebar SolidJS components (mode-gated via `.state/mode.json` read at render)

**Touch points (handled explicitly in `state_core`):**
1. **Event store** — shared table, schema allows both aggregate types
2. **Auth refresh** — both modes may trigger a refresh; filelock coordinates
3. **Provider routing** — both call `providers.route(model_spec)`; no mode awareness in router
4. **Daemon HTTP** — single endpoint set, mode-validation middleware gates event writes
5. **Worktree service** — teach's coding-partner Slice is indistinguishable from a build Slice in the worktree layer

---

## 13. Suggested Build Order (Foundational → Dependent)

**Tier 1 — Foundation (no dependencies on teach or build kernels):**
1. state_core.schema (pydantic models) — everything downstream depends on these types
2. state_core.events + events.sqlite (dual-write skeleton with opencode SyncEvent mirror)
3. state_core.auth (all 5 methods + filelock + round-robin) — RELEASE BLOCKER per PROJECT.md
4. state_core.providers (litellm + Anthropic direct)
5. state_core.worktree (opencode-HTTP + pygit2 fallback, same interface)
6. state_core.snapshot (Step + Slice tier composition over opencode Snapshot)
7. state_core.scheduler (pure-Python DAG resolver, no opencode knowledge)
8. state_daemon (HTTP server, middleware, mode gate, SSE, systemd/launchd unit)
9. state_worker (bridge between plugin and daemon; per-session bootstrap)
10. state_cli (top-level `state` binary: daemon start/stop, auth login, mode set)

**Tier 2 — Plugin plumbing (depends on Tier 1):**
11. @state/opencode-plugin server shim (9 hooks; uses state-worker HTTP)
12. @state/opencode-plugin TUI bundle (routes, slots, dialogs; uses opencode HTTP API)
13. TUI DAG viewer (shared by both modes)

**Tier 3 — MCP plumbing (depends on Tier 1 + 2):**
14. state-build MCP server skeleton (health/echo tools only; mode gate wired)
15. state-teach MCP server skeleton (same)

**Tier 4 — Build kernel (depends on all Tier 1+2+3):**
16. Step state machine + STEP.md schema + verify-contract runner
17. Build-mode commands (plan-phase, execute-phase, verify, ship — happy path)
18. Build-mode dashboards + sidebar
19. Build-mode subagents + permission rulesets
20. Ported GSD commands (audit, research, map-codebase, etc.)
21. Slice-tier snapshot / revert / ship flow

**Tier 5 — Teach kernel (depends on Tier 1+2+3; independent of Tier 4):**
22. Kolb state machine + concept graph projection
23. Drill engine using opencode `question` tool
24. Mental-model projection + rebuilder
25. Teach-mode personalities (AOL port)
26. Four teaching modes (PRIMM, Scaffolded, Socratic, Constructivist)
27. Scaffolding-mentor + coding-partner Slices
28. Teach dashboard + sidebar
29. Learning verifier (AOL-style) + cross-tier integration verifier

**Tier 6 — Portability + polish:**
30. Claude Code / Gemini CLI / Qwen Code shims (MCP-only, deprioritized per PROJECT.md)
31. Event replay CLI (`state forensics replay`)
32. Remote skill registry
33. Installer / packaging (`pyproject`, opencode plugin bundle)
34. Release pipeline + updater

---

## 14. Candidate Arcs (component-boundary justified)

Below are 22 Arcs aligned to component boundaries. Each names the opencode surface it extends. These feed the roadmapper directly; some may merge, some may split based on Phase-planning discovery.

| # | Arc title | Component boundary | Opencode surface extended |
|---|---|---|---|
| A1 | **Event store foundation** | `state_core.events` + SQLite schema | `packages/opencode/src/sync/index.ts`, `sync/event.sql.ts`, `storage/` |
| A2 | **Auth coverage (5 methods)** | `state_core.auth` | `packages/opencode/src/auth/index.ts`, plugin `AuthHook` (`plugin/src/index.ts:89`) |
| A3 | **Provider routing** | `state_core.providers` | plugin `chat.params`, `chat.headers`, `provider: ProviderHook` |
| A4 | **Worktree + snapshot service** | `state_core.worktree`, `.snapshot` | `packages/opencode/src/worktree/index.ts`, `snapshot/index.ts` |
| A5 | **DAG scheduler** | `state_core.scheduler` | (pure Python; interacts with A1 only) |
| A6 | **Daemon + HTTP + SSE** | `state_daemon` | opencode HTTP API (90+ ops), SSE event stream |
| A7 | **Per-session worker** | `state_worker` | opencode HTTP session ops + plugin shim |
| A8 | **Plugin server hooks** | `@state/opencode-plugin` (server) | all 9 hooks in `packages/plugin/src/index.ts:222-333` |
| A9 | **Plugin TUI bundle** | `@state/opencode-plugin` (tui) | `packages/plugin/src/tui.ts` entire surface |
| A10 | **TUI DAG viewer route** | (shared) | `route.register`, `ui.Slot` |
| A11 | **Mode enforcement** | `state_core.mode` + gates | `config` hook, `command.execute.before`, `tool.execute.before` |
| A12 | **state-build MCP server** | `state_build.mcp` + kernel skeleton | `packages/opencode/src/mcp/index.ts` (client side) |
| A13 | **state-teach MCP server** | `state_teach.mcp` + kernel skeleton | `packages/opencode/src/mcp/index.ts` (client side) |
| A14 | **Build kernel: Step state machine + verifiers** | `state_build.kernel`, `.verifiers` | `tool.execute.after`, `experimental.chat.system.transform`, `task` tool |
| A15 | **Build commands: plan/execute/verify/ship** | `state_build.commands` | opencode `command.*`, `task` tool, `Snapshot` service |
| A16 | **Build commands: GSD ports (research, map-codebase, review, audit, debug, forensics)** | `state_build.commands` | `task` tool + built-in tools (skill, plan mode, lsp) |
| A17 | **Build TUI (sidebar + dashboard + dialogs)** | `@state/opencode-plugin` (tui/build) | `sidebar_content`, `route.register`, `ui.DialogSelect` |
| A18 | **Teach kernel: Kolb + concepts + mental-model** | `state_teach.kernel`, `.concepts`, `.mental_model` | `experimental.chat.system.transform`, `tool.execute.after` |
| A19 | **Teach kernel: drill engine** | `state_teach.drill` | `packages/opencode/src/question/index.ts`, built-in `question` tool |
| A20 | **Teach commands + personalities + modes** | `state_teach.kernel`, `.personalities` | `chat.params`, `chat.headers`, `agent.options` read |
| A21 | **Teach TUI (sidebar + dashboard + drill)** | `@state/opencode-plugin` (tui/teach) | `route.register`, `ui.Prompt`, `ui.DialogSelect` |
| A22 | **Portability shims (Claude Code / Gemini CLI / Qwen Code)** | shim packages | MCP-only path; no opencode-specific surface |

**Additional candidate Arcs** (the roadmap may split these out):

- A23: Event replay / forensics CLI (consumes A1, A6)
- A24: Remote skill registry ingestion (opencode `cfg.skills.urls`)
- A25: Release & packaging (installer, plugin bundle, updater)
- A26: Verification infrastructure (goal-backward + rollup + cross-tier verifiers) — could merge into A14
- A27: Documentation (arch, user, author, plugin-dev) — explicit Arc per PROJECT.md requirements

That's 27 candidate Arcs, comfortably in the "15-25+" expected range per PROJECT.md.

**Ordering constraints (DAG edges between Arcs):**
- A1 blocks A6, A12, A13, A14, A18
- A2 blocks A6, A15 (auth needed for model calls)
- A3 blocks A14, A18
- A4 blocks A15 (ship needs worktree + snapshot)
- A5 blocks A14, A18
- A6 blocks A7, A10, A11, A12, A13
- A7 blocks A8, A9
- A8, A9 block A10, A17, A21
- A11 blocks A12, A13 (mode gate before MCP registration)
- A12 blocks A14, A15, A16
- A13 blocks A18, A19, A20
- A14 blocks A15, A16
- A18 blocks A19, A20
- A22 soft-depends on all build + teach Arcs (it's a parity tracker)

This ordering lets Arcs A1-A6 run largely in parallel (different packages), A7-A13 form a second wave, A14-A21 form the third. A22 is the tail. A23-A27 slot in where capacity permits.

---

## 15. Sources & Confidence

| Area | Confidence | Primary sources |
|---|---|---|
| Opencode hooks | HIGH | read `packages/plugin/src/index.ts` directly |
| TUI extension | HIGH | read `packages/plugin/src/tui.ts` directly |
| Task tool, permission, question, snapshot, worktree | HIGH | read source files directly |
| MCP, bus, sync | HIGH | read source files directly |
| SyncEvent semantics | HIGH | `sync/index.ts` + `event.sql.ts` read |
| Auth 5-method coverage | HIGH | `claude-oauth.md` + `gsd2-auth-analysis.md` (direct specs) |
| GSD state-machine precedent | MEDIUM | directory structure inspected; individual `.cjs` files not read (GSD path was `sdk/src/*-runner.ts` not `bin/lib/*.cjs`) — not load-bearing since PROJECT.md mandates redesign, not port |
| AOL architecture | MEDIUM | workflows + learners dir structure; schema inferred from `knowledge-graph.json` on disk (schema_version 1) |
| Kolb / scaffold-level semantics | MEDIUM | inferred from AOL frontmatter conventions + standard Kolb model |
| Mastery probability / Bayesian update | LOW | inferred pattern; exact update rule (if GSD/AOL has one) not surfaced in files read — roadmap should confirm against an AOL code deep-dive in its Phase 1 research |

**Gaps flagged for roadmap research:**
- Exact AOL `aol drill verify` internals (grader signatures, mastery_probability update math)
- GSD's current hook-adapter strategy (we're not porting it, but the interface set should be confirmed)
- opencode plugin install/discovery mechanics (`TuiPluginInstallOptions`) — needed for Arc A25 release/packaging
- Interactions between opencode's own `experimental.primary_tools` whitelist and our `mcp__state-*__` tool names — probably fine but a compatibility test in Arc A12/A13 should confirm

---

*End of ARCHITECTURE.md*
