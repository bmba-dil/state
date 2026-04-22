# state

## What This Is

`state` is a Python 3.12+ agentic state-machine workflow engine that fuses software
delivery (GSD-lineage) and adaptive learning (AOL-lineage) into one engine with
**two exclusive execution modes**: Build mode for shipping code, Teach mode for
teaching a learner. Its primary host is [opencode](https://opencode.ai) — `state`
extends opencode's TUI via plugin slots and is invoked through opencode slash
commands (`/state:build:*`, `/state:teach:*`). It is portable to other
provider-based CLIs (Claude Code, Gemini CLI, Qwen Code) via MCP.

This is a deliberate from-scratch rebuild, **not** a port. It extracts the best
intent of `get-shit-done`, `gsd-2pi`, and `agent-of-learning`, redesigns against
opencode's extension surface, and reimagines the planning hierarchy and
concurrency model.

## Core Value

> A single polyglot engine lets me ship software (build mode) and learn new
> skills (teach mode) with the same deep tooling — event-sourced history,
> dependency-DAG concurrency, cross-host portability — so I never have to
> choose between "make progress on my project" and "grow as an engineer."

## Requirements

### Validated

(None yet — ship to validate)

### Active

<!-- High-level capability hypotheses. Refined into REQ-IDs in REQUIREMENTS.md. -->

- [ ] Python daemon with always-on user service + per-opencode-session workers
- [ ] Dual-write event store (opencode SyncEvent + `.state/events.sqlite`)
- [ ] Auth layer covering Anthropic OAuth (Claude Code stealth), Gemini CLI
      free-tier OAuth, Antigravity OAuth, Copilot device-code, and plain API
      keys — all five methods on day one
- [ ] Provider routing via litellm with direct-SDK escape hatches for Anthropic
      extended thinking and fine-grained cache control
- [ ] Two independent MCP servers: `state-build` and `state-teach`, registered
      independently in opencode
- [ ] Single bundled opencode plugin (`@state/opencode-plugin`) carrying the
      hook shim and TUI extensions (sidebar, routes, dialogs)
- [ ] Four-tier planning hierarchy: **Arc → Phase → Slice → Step**, with the
      full discuss/plan/execute/verify cycle at Step level
- [ ] DAG scheduler (pure Python) that identifies all unblocked Slices/Steps
      and runs them concurrently per the `depends_on` graph
- [ ] Per-Slice worktree isolation for concurrent work (opencode worktree
      service preferred, pygit2 fallback for other hosts)
- [ ] Snapshot/diff/revert at Step and Slice boundaries
- [ ] Build-mode kernel reimagining every GSD command (plan-phase,
      execute-phase, verify, ship, code-review, code-review-fix,
      discuss-phase, research-phase, roadmapper, intel, map-codebase,
      progress, stats, audit-uat, audit-milestone, debug, forensics,
      pause-work, resume-work, thread, workstreams, etc.) as state-native
      Step workflows
- [ ] Teach-mode kernel: concept-graph builder, Kolb-cycle runner, drill
      engine (backed by opencode `question` tool), event-sourced mental-model
      tracker, learning verifier
- [ ] All four teaching modes (PRIMM, Scaffolded, Socratic, Constructivist)
      as first-class engine behaviors
- [ ] AOL teaching-personality port and teaching-style config
- [ ] Scaffolding-mentor and coding-partner flows as teach-mode Slices
- [ ] Shared TUI extensions: build dashboard, teach dashboard, DAG viewer,
      drill UI, statusline, toasts, gray-area decision dialog
- [ ] Verification infrastructure: goal-backward Step verifier,
      Slice/Phase/Arc rollup verifiers, AOL-style learning verifier,
      cross-tier integration verifier
- [ ] Event replay for forensics and cross-session state restoration
- [ ] Portability shims for Claude Code, Gemini CLI, and Qwen Code
      (explicitly deprioritized after opencode parity)
- [ ] Documentation: architecture, user guide, command reference, teach-mode
      author guide, build-mode author guide, plugin development guide
- [ ] Test infrastructure: unit, integration, opencode E2E, provider parity
      matrix
- [ ] Release & packaging: `pyproject`, installer, opencode plugin bundle,
      remote skill registry, updater

### Out of Scope

- **Shipping our own TUI framework** — we extend opencode's TUI. Textual (or
  similar) is reserved for standalone utilities only.
- **Running build and teach modes simultaneously in one invocation** — modes
  are exclusive per command; a project may host both mode directories side by
  side but switches between them between invocations.
- **v1-ships-with-API-keys-only** — all five auth methods must land on day
  one. Users on Anthropic Pro/Max are a primary audience; breaking the OAuth
  stealth flow is a release blocker.
- **A shared "mode" abstraction** — build and teach share only the kernel
  (event store, SQLite, MCP plumbing, auth, provider routing, plugin shim).
  Mode logic is fully siloed under separate Python packages and separate
  MCP servers.
- **GSD's two-stage milestone→phase hierarchy** — intentionally replaced by
  the four-tier Arc→Phase→Slice→Step model.
- **Serial phase execution** — GSD's linear a→b→c ordering is replaced by an
  explicit `depends_on` DAG with a concurrency scheduler. Roadmaps are DAGs,
  not lists.
- **Porting GSD commands verbatim** — each GSD command is inventoried and
  decided: port, redesign, or drop. Many will be redesigned.
- **Orchestration via Prefect/Dask/Airflow** — pure-Python scheduler is the
  committed choice. Those engines are the wrong shape for human/agent work.

## Context

**Inputs** — all reference material lives in `state-inputs/` (gitignored) in
the project root. Researchers and the roadmapper read these directly:

- `state-inputs/opencode-extension-surface.md` — the design bible. Every Arc
  must map onto it by file path.
- `state-inputs/opencode-integration-analysis.md` — GSD/AOL-to-opencode
  mapping tables.
- `state-inputs/claude-oauth.md` — Claude Code OAuth stealth flow (must be
  implemented exactly).
- `state-inputs/gsd2-auth-analysis.md` — four-method auth coverage strategy.
- `state-inputs/opencode/` — full opencode source. Must-read paths:
  `packages/plugin/src/index.ts`, `packages/plugin/src/tui.ts`,
  `packages/opencode/src/tool/task.ts`, `tool/registry.ts`, `agent/agent.ts`,
  `permission/index.ts`, `session/session.ts`, `sync/`, `bus/`, `mcp/`,
  `skill/index.ts`, `command/index.ts`, `question/index.ts`, `snapshot/`,
  `worktree/`.
- `state-inputs/get-shit-done/` — current GSD. Must inventory `bin/lib/*.cjs`
  (each `.cjs` is a state machine), `agents/*.md`, `commands/gsd/*.md`,
  `hooks/*.js`.
- `state-inputs/gsd-2pi-codebase-analysis/` — prior Python-rebuild
  analysis. Especially `10-python-rebuild-mapping.md` and
  `11-architecture-discussion.md`.
- `~/.claude/agent-of-learning/` — AOL workflows, personalities, learners
  schema (read in place; not copied).
- `~/.claude/skills/` — every user skill; decide per-skill whether to keep
  cross-compatible, reimplement as mode-specific logic, or drop.

**User background:** Thomas is learning Python. Picking Python 3.12+ is a
deliberate learning-through-building choice, not a performance decision.
Build-mode tooling should not hide Python from the user.

**Philosophical stance:** extreme thoroughness over shipping speed. The
roadmap is expected to produce 15–25+ Arcs, 60–100+ Phases, and hundreds of
Slices. Under-planning is the explicit failure mode. A short happy-path
milestone list is wrong on purpose.

## Constraints

- **Runtime**: Python 3.12+ only. No Python 2 / 3.x<3.12 compatibility.
- **Primary host**: opencode. All first-class UX is delivered through
  opencode's TUI via the plugin shim. Other hosts (Claude Code, Gemini CLI,
  Qwen Code) are MCP-only and explicitly deprioritized.
- **Exclusive modes**: Build and Teach never run in the same invocation.
  Directory layout, command namespaces, and Python packages are siloed.
- **Planning hierarchy**: Arc → Phase → Slice → Step. The Step tier owns
  the full discuss/plan/execute/verify cycle. Arcs/Phases/Slices are scoping
  containers.
- **Concurrency**: `depends_on` DAG, typed edges in artifacts. Scheduler
  resolves unblocked work and dispatches to worktrees.
- **Event store**: dual-write — opencode SyncEvent + `.state/events.sqlite`.
  Daemon reads from SQLite for all queries.
- **Auth**: `.state/auth.json` (portable). First-run import from opencode's
  auth when present. All five auth methods supported day one.
- **Provider routing**: litellm default, direct Anthropic SDK escape hatch
  for extended thinking + fine-grained cache control.
- **Library locks** (from `gsd-2pi-codebase-analysis/10-python-rebuild-mapping.md`):
  `litellm`, `pluggy`, `pygit2`, `mcp` (official SDK), `pydantic`, `orjson`,
  `aiosqlite`, `filelock`, `httpx`. Textual reserved for standalone CLIs only.
- **Opencode hooks extended**: `chat.message`, `tool.execute.before/after`,
  `permission.ask`, `event`, `experimental.chat.system.transform`,
  `experimental.session.compacting`, `chat.params`, `command.execute.before`,
  `shell.env`. Each hook wiring is a first-class Slice.
- **Plugin packaging**: single `@state/opencode-plugin` bundle; hook shim ~300
  LOC, TUI extensions in the same package.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python 3.12+ implementation language | User is learning Python; learn-through-build | — Pending |
| Opencode is the primary host; own no TUI framework | Opencode has a mature plugin + TUI extension surface; duplicating is waste | — Pending |
| Build and Teach modes are exclusive | Different domains, different users, different artifacts; forcing a shared abstraction dilutes both | — Pending |
| Four-tier planning hierarchy (Arc → Phase → Slice → Step) | GSD's two-tier is too coarse and implicitly serial; four tiers separate scope from concurrency from discuss/plan cycle | — Pending |
| Dependency DAG over linear ordering | Mirrors how a real dev team parallelizes work once foundations are in | — Pending |
| Hybrid daemon (always-on + per-session worker) | Always-on serves dashboards/watchers when opencode is closed; per-session workers keep hot state cheap | — Pending |
| Dual-write events (SyncEvent + SQLite) | Opencode drives live UI; SQLite gives the daemon authoritative history when opencode is down | — Pending |
| `.state/auth.json` (portable) | Cross-host reusability is a core goal; coupling to opencode's auth store blocks Claude Code / Gemini shims | — Pending |
| Two MCP servers: `state-build` + `state-teach` | Physically enforces the exclusive-modes cardinal rule; reduces blast radius of mode-specific changes | — Pending |
| Pure-Python DAG scheduler | Zero new deps; our DAG is small and agent-shaped, not data-pipeline-shaped | — Pending |
| Per-Slice worktree, Step+Slice snapshots | Worktree-per-Slice matches a human dev's branch-per-feature; Step snapshots give fine-grained revert, Slice snapshots give rollup checkpoints | — Pending |
| Event-sourced teach-mode mental model | Observations are events; `MENTAL-MODEL.json` is a rebuildable projection; matches dual-write design and supports replay-based forensics | — Pending |
| Worktree lifecycle: opencode service preferred, pygit2 fallback | Best UX on opencode without sacrificing portability | — Pending |
| `.state/mode.json` + directory presence for mode detection | Declarative gate + physical signal; composable with both-mode projects | — Pending |
| Extend opencode's skill scanner to read `.state/skills/` | No duplication; opencode already has the right abstraction | — Pending |
| Single bundled plugin package | One registration, one version; simplest install path for the primary host | — Pending |
| All five auth methods ship day one | Anthropic OAuth stealth is the subscription unlock; shipping API-keys-only blocks the primary audience | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-22 after initialization*
