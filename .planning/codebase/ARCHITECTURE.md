# Architecture

**Analysis Date:** 2026-05-05

## Pattern Overview

**Overall:** Component-based, event-sourced, with physical mode silos

**Key Characteristics:**
- Six physically distinct processes/artifacts cooperating through SQLite event store and HTTP IPC
- Dual-write event sourcing: `events.sqlite` is authoritative, opencode `SyncEvent` mirror is secondary
- Mode isolation enforced at 6 layers (disk, MCP registration, hooks, commands, daemon middleware, import-graph linter)
- Reactively-scheduled DAG concurrency with per-Slice worktree isolation
- Agentic state machines for both build (Step FSM) and teach (Kolb cycle) modes
- Pure-Python DAG scheduler (~800 LOC) — no NetworkX dependency

## Components (Physical Processes)

### 1. `state-daemon` — Always-on User Service
- Location: `src/state_daemon/`
- Purpose: Owns the SQLite event store, runs the DAG scheduler, drives build/teach kernels, serves HTTP API on Unix socket, enforces mode gating
- Runs as: `python -m state_daemon` (launchd/systemd user unit)
- Entry: `src/state_daemon/__main__.py` → `src/state_daemon/orchestrator.py:startup()`
- Startup sequence: redactor install → logging → pid file → auth import → repair → migrate → reconciler → SSE bus → crash recovery → HTTP server → mode middleware → auth manager
- Key files: `server.py`, `middleware.py`, `router.py`, `orchestrator.py`, `sse.py`, `pid.py`, `recovery.py`, `auth_manager.py`, `cli.py`, `logging.py`

### 2. `state-worker` — Per-Session Worker
- Location: `src/state_worker/`
- Purpose: Per-opencode-session Python process spawned by the plugin shim. Holds hot session state for the active Arc/Phase, proxies HTTP between plugin and daemon
- Entry: `src/state_worker/__main__.py` → `src/state_worker/main.py`
- Key files: `main.py`, `session.py`, `bridge.py`

### 3. `state-build` — Build-mode MCP Server
- Location: `src/state_build/`
- Purpose: stdio MCP server exposing build-mode tools (plan, execute, verify, ship)
- PHYSICAL SILO: must NEVER import `state_teach` — enforced by linter rule
- Entry: `src/state_build/mcp.py`
- Key files: `kernel.py`, `commands/`, `verifiers/`

### 4. `state-teach` — Teach-mode MCP Server
- Location: `src/state_teach/`
- Purpose: stdio MCP server exposing teach-mode tools (concept ops, drill prepare/verify, mental-model queries)
- PHYSICAL SILO: must NEVER import `state_build` — enforced by linter rule
- Entry: `src/state_teach/mcp.py`
- Key files: `kernel.py`, `concepts.py`, `drill.py`, `mental_model.py`, `personalities/`

### 5. `@state/opencode-plugin` — TypeScript Plugin Bundle
- Location: Not yet in repo (planned for milestone v8/v9, not yet scaffolded)
- Purpose: Single TS bundle carrying 9-hook shim (~300 LOC) and SolidJS TUI extensions
- Exports: `PluginModule` (server) + `TuiPluginModule` (tui)
- Key constraint: TUI code talks exclusively to state-daemon over HTTP — never imports Python packages directly

### 6. `.state/` — On-Disk Artifact Tree
- Location: `.state/` at project root
- Purpose: All persistent state — SQLite databases, auth vault, mode config, build/teach markdown artifacts, snapshots, logs
- Key files: `events.sqlite`, `auth.json` (chmod 600), `mode.json`, `daemon.pid`, `config.toml`

## Library Layout (Python Packages)

```
src/
├── state_core/      # Shared: event store, auth, providers, config, schema, scheduler
├── state_build/     # Build-mode kernel (siloed from state_teach)
├── state_teach/     # Teach-mode kernel (siloed from state_build)
├── state_daemon/    # Always-on service (depends on state_core)
├── state_worker/    # Per-session worker (depends on state_core + state_daemon)
└── state_cli/       # Top-level CLI (depends on state_core, state_daemon, state_build, state_teach)
```

## Layers

### Core Layer (`state_core/`)
- Purpose: Shared library consumed by all other components — the common substrate
- Location: `src/state_core/`
- Contains: Event store, auth providers, DAG scheduler, pydantic schemas, provider routing, worktree abstraction, database connection factory, config resolution, projector, reconciler, observability (redactor)
- Depends on: Only stdlib + third-party libraries (pydantic, aiosqlite, httpx, pygit2, structlog, etc.)
- Used by: ALL other components
- Import patterns: Components use BOTH `from state_core.X import Y` and `from src.state_core.X import Y` (dual-path — both work because `src/` is in `pythonpath` per pytest config)

### Daemon Layer (`state_daemon/`)
- Purpose: Always-on orchestrator process — owns the event store, enforces mode isolation, serves HTTP API
- Location: `src/state_daemon/`
- Contains: HTTP server (Unix socket), JSON-RPC router, mode enforcement middleware, SSE broadcast bus, PID management, crash recovery, auth refresh loop, structured logging config, CLI sub-app
- Depends on: `state_core/` heavily
- Used by: `state_worker/`, `state_cli/`, `state-build/` MCP, `state-teach/` MCP

### Build Layer (`state_build/`)
- Purpose: Build-mode domain logic — Step state machine, GSD command ports, verifiers
- Location: `src/state_build/`
- Contains: Step FSM kernel, MCP server entry point, command implementations, verifier implementations
- Depends on: `state_core/`, `state_daemon/` (for event writes)
- Used by: MCP host (opencode)
- **Hard constraint:** MUST NOT import `state_teach/` — this is a physical import-graph invariant

### Teach Layer (`state_teach/`)
- Purpose: Teach-mode domain logic — Kolb cycle, concept graph, drill engine, mental model
- Location: `src/state_teach/`
- Contains: Kolb FSM kernel, MCP server entry point, concept graph ops, drill engine, mental-model projection, personality loaders
- Depends on: `state_core/`, `state_daemon/` (for event writes)
- Used by: MCP host (opencode)
- **Hard constraint:** MUST NOT import `state_build/` — this is a physical import-graph invariant

### CLI Layer (`state_cli/`)
- Purpose: Top-level `state` command — Typer app with sub-apps for db, events, auth, snapshot, dag, daemon
- Location: `src/state_cli/`
- Contains: CLI entry point, auth commands, snapshot commands, DAG commands, daemon sub-app delegation
- Depends on: `state_core/`, `state_daemon/`, `state_build/`, `state_teach/`
- Used by: End user directly via `state <subcommand>`

### Worker Layer (`state_worker/`)
- Purpose: Per-opencode-session process — session-scoped proxy between plugin shim and daemon
- Location: `src/state_worker/`
- Contains: Worker entry point, session identity management, daemon bridge, hook event forwarding
- Depends on: `state_core/`, `state_daemon/`
- Used by: `@state/opencode-plugin` shim (spawns worker per opencode session)

## Data Flow

### Dual-Write Event Flow

Every state transition follows this exact pattern:

1. Event is generated (e.g., `state.step.verify_passed`)
2. **Primary write:** `SqliteEventStore.append()` in `src/state_core/events.py` writes to `events.sqlite` with:
   - ULID generation (via `python-ulid`)
   - Per-aggregate monotonic seq enforcement (`aggregate_seq` table)
   - Deterministic JSON serialization (sort_keys, compact separators)
   - Single `BEGIN IMMEDIATE` / `COMMIT` transaction
   - `PRAGMA synchronous=FULL` belt-and-suspenders
   - Post-commit callbacks (SSE broadcast via `SseBus`)
3. **Secondary write:** If a `SyncEventMirror` is provided, a fire-and-forget `asyncio.ensure_future()` schedules an HTTP POST to opencode's SyncEvent endpoint
4. **Unsynced reconciliation:** `StartupReconciler` in `src/state_core/reconciler.py` runs periodic sweeps for events where `synced_to_opencode = 0`, replaying them when opencode comes back online

**Key invariant:** `events.sqlite` is the single source of truth. Everything else (projections, caches, SyncEvents) is a projection or mirror. The daemon is the ONLY writer to planning tables; workers/MCP servers write through it.

### Canonical Trace: `state.step.verify_passed`

```
1. MCP tool `state_build__verify_step` executes in state-build process
2. state-build POSTs state-daemon: /events/append → state.verify.started
3. Daemon: dual-write (SQLite row + opencode SyncEvent)
4. Opencode bus: `event` hook fires on SyncEvent, kernel advances Step FSM
5. Step FSM emits state.step.advanced → daemon → SQLite + SyncEvent
6. Post-commit callback: SSE bus broadcasts to all subscribers
7. TUI sidebar re-renders Step status to "done"; toast notification shows
8. MCP tool returns result to LLM
9. tool.execute.after hook captures verification metadata
```

### State Management

- **Persistence:** `events.sqlite` with WAL mode, per-aggregate sequence numbers, rebuildable projections
- **Hot State:** Held in-memory by daemon (cached config, active connections) and worker (session context)
- **Projections:** Rebuildable from event stream — `steps`, `slices`, `concepts`, `tool_calls` cache tables are all derived
- **Reactive:** DAG scheduler recomputes on every `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned` — no polling loop

## Key Abstractions

### `SqliteEventStore` — Event Persistence
- Location: `src/state_core/events.py`
- Purpose: Append-only event log with ULID generation, per-aggregate sequence enforcement, deterministic JSON serialization, post-commit callbacks
- Implements: `EventStore` Protocol
- Pattern: async context manager per operation (via `get_connection()`), `BEGIN IMMEDIATE` transactions

### `DAGScheduler` — Reactive Work Dispatcher
- Location: `src/state_core/scheduler.py`
- Purpose: Pure-Python reactive DAG scheduler — computes unblocked frontier, groups by Slice, dispatches concurrently
- Key functions: `frontier()`, `topo_sort()`, `detect_cycles()`, `detect_priority_inversion()`, `detect_silent_deadlock()`, `_critical_path_nodes()`
- Pattern: `tick()` method receives all nodes + edges, returns dispatched node IDs; reactive (no polling)

### `StepMachine` — Build State Machine
- Location: `src/state_build/kernel.py`
- Purpose: Finite state machine for a single Step's lifecycle
- States: idle → discussing → planning → executing → verifying → done (with blocked/abandoned fallbacks)
- Pattern: `on_event(event_type, data)` dispatch with snapshot creation at execute/verify boundaries

### `KolbMachine` — Teach State Machine
- Location: `src/state_teach/kernel.py`
- Purpose: Kolb experiential learning cycle state machine
- Stages: CE (Concrete Experience) → RO (Reflective Observation) → AC (Abstract Conceptualization) → AE (Active Experimentation) → MASTERED/REVIEW
- Pattern: `on_event(event_type, data)` dispatch with Bayesian mastery updates

### `ModeMiddleware` — Mode Enforcement Gate
- Location: `src/state_daemon/middleware.py`
- Purpose: HTTP middleware wrapping the JSON-RPC router — enforces `X-State-Mode` header validation
- Rules: Missing/invalid header → 400; mode=both → allow all; mode=kernel → allow all; match → allow; mismatch+read → allow; mismatch+write → 403
- Pattern: Callable (`__call__`) that wraps inner router, returns `bytes | tuple[int, bytes]`

### `AuthMethod` Protocol — Credential Abstraction
- Location: `src/state_core/auth/base.py`
- Purpose: Protocol for auth providers — login, refresh, token validation, HTTP header generation
- Implementations: `src/state_core/auth/providers/` (anthropic, google_gemini, antigravity, github_copilot, api_key)
- Pattern: `@runtime_checkable Protocol` with `async login()`, `async refresh()`, `is_token()`, `http_headers()`, `is_expired()`

### `Projector` — Event Stream Projection
- Location: `src/state_core/projector.py`
- Purpose: Rebuilds cache tables (steps, slices, concepts) from the raw event stream
- Pattern: `rebuild_all()` replays all events → reconstructs derived tables

### `Deps` — Dependency Injection Container
- Location: `src/state_core/deps.py`
- Purpose: Holds daemon-level shared resources (shared `httpx.AsyncClient`) created once at startup
- Pattern: Pydantic BaseModel with `arbitrary_types_allowed`, injected into subsystems

## Entry Points

### Daemon Startup
- Location: `src/state_daemon/__main__.py`
- Triggers: `python -m state_daemon --project-root /path --socket /path/to/sock`
- Responsibilities: Parse CLI args → set env vars → call `startup()` from `orchestrator.py` → run event loop forever

### CLI
- Location: `src/state_cli/main.py`
- Triggers: `state <subcommand>` via Typer
- Responsibilities: Route to sub-apps: `state db init`, `state auth login`, `state events tail|replay|export`, `state snapshot`, `state dag`, `state daemon start|stop|status`

### Daemon HTTP Server
- Location: `src/state_daemon/server.py`
- Triggers: Daemon startup binds to Unix domain socket (`~/.local/state/daemon.sock` or configurable)
- Responsibilities: Accept connections, parse HTTP/1.1, route through `ModeMiddleware` → `JsonRpcRouter`, delegate GET `/events/subscribe` to SSE handler

### Worker
- Location: `src/state_worker/__main__.py`
- Triggers: Spawned by `@state/opencode-plugin` per opencode session
- Responsibilities: Attach to daemon, manage session identity, forward hooks, manage hot session state

### MCP Servers (build + teach)
- Location: `src/state_build/mcp.py` + `src/state_teach/mcp.py`
- Triggers: Registered in opencode MCP config, launched as subprocesses via stdio transport
- Responsibilities: Expose mode-scoped tools to LLM via MCP protocol

## Error Handling

**Strategy:** Fail loud, recover gracefully. Every critical path has a defined failure mode.

**Patterns:**
- **Daemon startup gating:** Each step in `orchestrator.py:startup()` is gated on the previous step. Critical failures (redactor not attached, projection invalid, socket in use) raise `SystemExit(1)`. Non-critical failures (auth import fails) log WARN and continue.
- **Transaction integrity:** `BEGIN IMMEDIATE` + `COMMIT` wrapping every event store append; `PRAGMA synchronous=FULL` on critical writes
- **Crash recovery:** `src/state_daemon/recovery.py` replays event log through projector on startup, resumes in-flight Steps
- **Aggregate seq repair:** `SqliteEventStore.repair_aggregate_seqs()` detects and repairs gaps/duplicates in `aggregate_seq` table
- **Exception group watchdog:** `_inspect_for_cancelled()` in `src/state_core/scheduler.py` prevents swallowed `CancelledError` deadlocks in `asyncio.TaskGroup`
- **structured logging:** All errors logged with `structlog` — error_type, context IDs, but never secret bytes (redactor installed BEFORE any other I/O)

## Cross-Cutting Concerns

**Logging:** `structlog` with rotating file handler (`src/state_daemon/logging.py`), redactor processor on root logger (`src/state_core/observability/redactor.py`), JSON output for production, human-readable for dev

**Validation:** Pydantic v2 with `extra="forbid"` on all models (`src/state_core/schema.py`), ULID format validation, discriminated unions for typed event handling

**Authentication:** 5-method auth (`src/state_core/auth/`), filelock-guarded credential vault (`src/state_core/auth/store.py`), round-robin refresh (`src/state_core/auth/refresh.py`), background refresh loop in daemon (`src/state_daemon/auth_manager.py`), chmod 600 enforcement on `auth.json`

**Mode Enforcement:** 6-layer defense-in-depth — disk (`mode.json`), MCP registration (mutually exclusive `enabled` flags), plugin hooks (per-call mode check), command dispatch (namespace gate), daemon middleware (`ModeMiddleware` — canonical gate), Python import-graph linter (`state_build` ↔ `state_teach` import guard)

**Provider Routing:** `src/state_core/providers/router.py` — litellm default path, Anthropic SDK escape hatch for OAuth stealth and extended thinking, shared `httpx.AsyncClient` via `Deps`

---

*Architecture analysis: 2026-05-05*
