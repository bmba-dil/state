# MILESTONES: state

## v11 Mode Enforcement (6 Layers) (Shipped: 2026-05-05)

**Phases completed:** 9 phases, 9 plans
**Tests:** 114 (cross-mode leakage regression suite)

**Key accomplishments:**

- 6-layer mode enforcement defense-in-depth: mode.json schema, directory presence, MCP registration toggle, plugin hook gates, daemon HTTP middleware, import-graph lint
- CLI: `state mode init` and `state mode set` with atomic writes and SIGHUP hot-reload
- MODE-01 through MODE-06 satisfied (all 6 v11 requirements)
- All 16 P0 pitfalls closed (final P0-11/P0-12 mode enforcement holes sealed)

---

## v10 TUI DAG Viewer (Shipped: 2026-05-05)

**Phases completed:** 8 phases, 8 plans
**Tests:** 344 passed (TUI) | **Build:** tui.js 51 KB

**Key accomplishments:**

- Registered `state.dag` route in opencode plugin with topological DAG layout (longest-path layering + barycenter cross-reduction)
- Shared status palette (7 statuses, theme-derived colors) consumed by dag-viewer and build-progress
- Full navigation (arrow keys, Enter, Esc) with focus/selection visual indicators and screen-reader accessibility
- Filter bar with critical-path computation (DP longest-path algorithm from roots to leaves)
- SSE live updates with diff-patching for incremental status changes from daemon
- Layout caching with key-based invalidation + viewport clipping for graphs ≥100 nodes
- DAG-VIEW-01 through DAG-VIEW-04 satisfied (all 4 v10 requirements)

---

## v9 Plugin TUI Bundle (Shipped: 2026-05-05)

**Phases completed:** 9 phases, 9 plans
**Tests:** 344 passed (TUI) | **Bundle:** tui.js 51 KB

**Key accomplishments:**

- Mode-aware sidebar with conditional render (build-progress vs teach-concept)
- Build-progress sub-component with Step status colors + Slice DAG mini-view
- Teach-concept sub-component with concept card + Kolb stage + mastery bar
- Statusline: mode / scope / provider / session cost
- Toast notifications: Slice completion, drill availability, auth refresh
- Plugin install script for TUI + MCP auto-registration
- TUI-01 through TUI-05 satisfied (all 5 v9 requirements)

---

## v8 Plugin Server Hooks (Shipped: 2026-05-05)

**Phases completed:** 11/12 phases (073 event hook deferred)
**Bundle:** dist/index.js 11.53 KB | **Hooks:** 10/11 implemented

**Key accomplishments:**

- `@state/opencode-plugin` TS package scaffolded (bun, typescript 5.8.2, @opencode-ai/plugin)
- 10 server hooks implemented: chat.message, tool.execute.before, tool.execute.after, permission.ask, experimental.chat.system.transform, experimental.session.compacting, chat.params, chat.headers, command.execute.before, shell.env
- Mode gating across all hooks (build/teach/kernel), cross-mode rejection
- Model profile resolution (quality/balanced/budget) with thinking budget headers
- `bun build` single-file bundling (11.53 KB), `install.sh` auto-registration
- HOOK-01 through HOOK-04, HOOK-06 through HOOK-11 satisfied (10/11; HOOK-05 deferred — API gap)

---

## v7 Per-Session Worker (Shipped: 2026-05-05)

**Phases completed:** 8 phases, 8 plans
**Tests:** 52 (42 new + 10 augmented) | **Lines of Python:** ~1,200

**Key accomplishments:**

- Worker main module spawned by plugin shim with session ID registration
- Daemon-worker bridge over HTTP+SSE on unix socket
- Hot-state container (active Slice/Step/drill) synced from daemon
- Hook event forwarding (HTTP POST to daemon) with retry on transient failure
- Version handshake between plugin and daemon with compat range
- Session tear-down on opencode close — flush pending events, clean exit
- Structured per-worker-PID logging with redactor attached
- Multi-session stress test (3 concurrent sessions, zero leaked workers)
- WRK-10 through WRK-13 satisfied (all 4 v7 requirements)

---

## v5 DAG Scheduler (Shipped: 2026-05-04)

**Phases completed:** 9 phases, 9 plans
**Tests:** 130 passed | **Lines of Python:** ~1,500 (scheduler, reactive, CLI)

**Key accomplishments:**

- Pure-Python DAG scheduler — Edge/Node/NodeRegistry types, Kahn's topological sort, DFS cycle detection, frontier calculator, async TaskGroup dispatcher with concurrency cap
- P0-16 closed — CancelledError swallow watchdog preventing silent scheduler deadlock
- Reactive event-driven triggers — zero-polling subscription to v1 event store
- Priority inversion + silent deadlock detection with `on_scheduler_event` callback
- `state dag show` CLI with Unicode box-drawing, 6 status colors, JSON DAG loading, Hypothesis property tests
- DAG-01 through DAG-07 satisfied (all 7 v5 requirements)

---

## v6 State Daemon (Shipped: 2026-05-04)

**Phases completed:** 10 phases, 10 plans
**Commits:** 27 (daemon dir) | **Lines of Python (daemon):** ~3,443 | **Tests:** ~250

**Key accomplishments:**

- Unix socket HTTP server with JSON-RPC 2.0 router and pluggable route handlers
- Platform-aware pid-file with stale process detection (P0-15 closed)
- Mode-enforcement HTTP middleware — canonical gate for build/teach isolation (6th defense-in-depth layer)
- SSE event broadcast bus with multi-client fan-out and mode filtering
- launchd plist + systemd user unit generator with `state daemon install|uninstall` CLI
- Crash recovery replaying event log, rebuilding projections, and detecting in-flight Steps
- Full daemon lifecycle CLI: start/stop/restart/status/logs
- Auth credential refresh loop + round-robin manager + GET /auth/status (token-safe)
- DAE-01, DAE-03..DAE-09 satisfied (DAE-02 deferred to v7)

---

## v2 Auth Coverage (Shipped: 2026-05-03)

**Phases completed:** 15 phases, 46 plans, 4 tasks

**Key accomplishments:**

- (none recorded)

---

## v1 Event Store Foundation (Shipped: 2026-04-26)

**Phases completed:** 11 phases, 17 plans
**Commits:** 67 | **Lines of Python:** 2,779 | **Timeline:** 4 days

**Key accomplishments:**

- CQRS projection engine with 19 handler functions and rebuild_all/apply_event
- CLI commands: `state events tail`, `replay --from <ulid>`, `export --format jsonl`
- Golden 10K-event fixture with triple SHA-256 checksum verification (DB = export JSONL = projection)
- Hypothesis property tests for idempotence + determinism across all 34 event types
- All 321 tests passing with zero regressions

---

**Layout:** milestone-scoped
**Total milestones:** 27
**Total phases:** 260
**Created:** 2026-04-22 (migration from monolithic)

---

## Tier 1 — Foundation (parallel after scaffolding)

| Milestone | Name | Phases | Path |
|---|---|---|---|
| v1 | Event Store Foundation | 001–010 (10) | `milestones/v1/` |
| v2 | Auth Coverage (5 Methods + Multi-Cred) | 011–022 (12) | `milestones/v2/` |
| v3 | Provider Routing + Model Profiles | 023–031 (9) | `milestones/v3/` |
| v4 | Worktree + Snapshot Service | 032–040 (9) | `milestones/v4/` |
| v5 | DAG Scheduler | 041–049 (9) | `milestones/v5/` |

## Tier 2 — Kernel & Plumbing

| Milestone | Name | Phases | Path |
|---|---|---|---|
| v6 | State Daemon (HTTP + SSE + Mode Middleware) | 050–059 (10) | `milestones/v6/` |
| v7 | Per-Session Worker | 060–067 (8) | `milestones/v7/` |
| v8 | Plugin Server Hooks (all 9) | 068–079 (12) | `milestones/v8/` |
| v9 | Plugin TUI Bundle | 080–088 (9) | `milestones/v9/` |
| v10 | TUI DAG Viewer | 089–096 (8) | `milestones/v10/` |
| v11 | Mode Enforcement (6 Layers) | 097–105 (9) | `milestones/v11/` |
| v12 | state-build MCP Server (skeleton) | 106–114 (9) | `milestones/v12/` |
| v13 | state-teach MCP Server (skeleton) | 115–123 (9) | `milestones/v13/` |

## Tier 3a — Build Domain Kernel

| Milestone | Name | Phases | Path |
|---|---|---|---|
| v14 | Build Kernel: Step FSM + Verifiers | 124–134 (11) | `milestones/v14/` |
| v15 | Build Core Commands (plan/execute/verify/ship) | 135–144 (10) | `milestones/v15/` |
| v16 | Build GSD Command Ports + Net-New Product-Hierarchy Commands | 145–158 (14) | `milestones/v16/` |
| v17 | Build TUI Extensions | 159–166 (8) | `milestones/v17/` |

## Tier 3b — Teach Domain Kernel

| Milestone | Name | Phases | Path |
|---|---|---|---|
| v18 | Teach Kernel: Kolb + Concepts + Mental-Model | 167–177 (11) | `milestones/v18/` |
| v19 | Teach Drill Engine | 178–186 (9) | `milestones/v19/` |
| v20 | Teach Four Modes + Selector | 187–197 (11) | `milestones/v20/` |
| v21 | Teach Personalities + Teaching Style | 198–205 (8) | `milestones/v21/` |
| v22 | Scaffolding-Mentor + Coding-Partner | 206–214 (9) | `milestones/v22/` |
| v23 | Teach TUI Extensions | 215–222 (8) | `milestones/v23/` |
| v24 | Subject Authoring + 4-Gate Promoter | 223–230 (8) | `milestones/v24/` |

## Tier 4 — Polish & Portability

| Milestone | Name | Phases | Path |
|---|---|---|---|
| v25 | Migration & Import | 231–238 (8) | `milestones/v25/` |
| v26 | Portability Shims | 239–246 (8) | `milestones/v26/` |
| v27 | Release & Packaging | 247–256 (10) | `milestones/v27/` |

---

## Progress

| Milestone | Phases done | Status |
|---|---|---|
| v1 Event Store Foundation | 11/11 | **Complete** — Shipped 2026-04-26, merged to `main` 2026-04-28 |
| v2 Auth Coverage (5 Methods + Multi-Cred) | 15/15 | **Complete** — Shipped 2026-05-03 |
| v3 Provider Routing + Model Profiles | 7/9 | **Complete** — Shipped 2026-05-04 (030/031 deferred) |
| v4 Worktree + Snapshot Service | 9/9 | **Complete** — Shipped 2026-05-04 |
| v5 DAG Scheduler | 9/9 | **Complete** — Shipped 2026-05-04 |
| v6 State Daemon (HTTP + SSE + Mode Middleware) | 10/10 | **Complete** — Shipped 2026-05-04 |
| v7 Per-Session Worker | 8/8 | **Complete** — Shipped 2026-05-05 |
| v8 Plugin Server Hooks (all 9) | 11/12 | **Complete** — Shipped 2026-05-05 (HOOK-05 deferred) |
| v9 Plugin TUI Bundle | 9/9 | **Complete** — Shipped 2026-05-05 |
| v10 TUI DAG Viewer | 8/8 | **Complete** — Shipped 2026-05-05 |
| v11 Mode Enforcement (6 Layers) | 9/9 | **Complete** — Shipped 2026-05-05 |
| v12 state-build MCP Server (skeleton) | 0/9 | Not started |
| v13 state-teach MCP Server (skeleton) | 0/9 | Not started |
| v14 Build Kernel: Step FSM + Verifiers | 0/11 | Not started |
| v15 Build Core Commands (plan/execute/verify/ship) | 0/10 | Not started |
| v16 Build GSD Command Ports + Net-New Product-Hierarchy Commands | 0/14 | Not started |
| v17 Build TUI Extensions | 0/8 | Not started |
| v18 Teach Kernel: Kolb + Concepts + Mental-Model | 0/11 | Not started |
| v19 Teach Drill Engine | 0/9 | Not started |
| v20 Teach Four Modes + Selector | 0/11 | Not started |
| v21 Teach Personalities + Teaching Style | 0/8 | Not started |
| v22 Scaffolding-Mentor + Coding-Partner | 0/9 | Not started |
| v23 Teach TUI Extensions | 0/8 | Not started |
| v24 Subject Authoring + 4-Gate Promoter | 0/8 | Not started |
| v25 Migration & Import | 0/8 | Not started |
| v26 Portability Shims | 0/8 | Not started |
| v27 Release & Packaging | 0/10 | Not started |
| **TOTAL** | **106/260** | — |

*See `_archived/ROADMAP.md` for the pre-migration monolithic roadmap including DAG, tier boundaries, and revision history.*
