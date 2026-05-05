# Codebase Structure

**Analysis Date:** 2026-05-05

## Directory Layout

```
state/                              # Project root (git repo)
├── .planning/                      # GSD planning artifacts (not product code)
│   ├── PROJECT.md                  # Project charter + cardinal rules
│   ├── ROADMAP.md                  # Full milestone/phase roadmap (27 milestones)
│   ├── STATE.md                    # Current project state
│   ├── config.json                 # GSD workflow configuration
│   ├── research/                   # Architecture + stack research docs
│   │   ├── ARCHITECTURE.md         # Full architecture spec (reference)
│   │   └── STACK.md                # Full technology stack spec (reference)
│   ├── codebase/                   # Generated codebase maps (this dir)
│   ├── milestones/                 # Per-milestone phase directories
│   │   └── v{N}/phases/            # Each phase has discuss/plan/execute artifacts
│   ├── graphs/                     # Knowledge graph outputs
│   ├── patterns/                   # Observed patterns (adaptive learning)
│   ├── quick/                      # Quick ad-hoc task records
│   └── _archived/                  # Archived milestone artifacts
├── src/                            # ALL Python source code
│   ├── state_core/                 # Shared library (event store, auth, scheduler, schema)
│   ├── state_build/                # Build-mode kernel (MUST NOT import state_teach)
│   ├── state_teach/                # Teach-mode kernel (MUST NOT import state_build)
│   ├── state_daemon/               # Always-on daemon service
│   ├── state_worker/               # Per-session worker process
│   └── state_cli/                  # Top-level CLI (`state` command)
├── tests/                          # All Python tests (co-located by domain)
│   ├── conftest.py                 # Root conftest (currently empty)
│   ├── test_events.py              # Event store tests
│   ├── test_schema.py              # Schema/model tests (749 lines)
│   ├── test_scheduler.py           # DAG scheduler tests
│   ├── test_daemon_*.py            # Daemon component tests
│   ├── test_worktree*.py           # Worktree tests
│   ├── test_anthropic_client.py    # Provider client tests
│   ├── test_litellm_client.py      # Provider client tests
│   ├── auth/                       # Auth-specific tests
│   │   ├── conftest.py             # Auth test fixtures
│   │   ├── test_store.py           # Vault tests
│   │   ├── test_refresh.py         # Refresh lock tests
│   │   ├── test_loader.py          # Credential loader tests
│   │   ├── test_rotation.py        # Round-robin tests
│   │   ├── providers/              # Per-provider tests
│   │   ├── oauth_common/           # OAuth helper tests
│   │   └── golden/                 # Golden file tests per provider
│   └── ...
├── .state/                         # Runtime state directory (gitignored)
│   ├── events.sqlite               # Authoritative event store (WAL mode)
│   ├── auth.json                   # Credential vault (chmod 600)
│   ├── mode.json                   # Active mode config
│   ├── config.toml                 # Static daemon config
│   ├── daemon.pid                  # PID file for singleton enforcement
│   ├── daemon.sock                 # Unix domain socket
│   ├── migrations/                 # SQL migration files (numbered)
│   ├── fixtures/                   # Test fixtures
│   ├── build/                      # Build-mode artifact tree
│   ├── teach/                      # Teach-mode artifact tree
│   ├── snapshots/                  # Step/Slice snapshot storage
│   └── logs/                       # Daemon + worker log files
├── .state-inputs/                  # Reference inputs (gitignored)
│   ├── opencode/                   # Opencode source snapshot
│   ├── get-shit-done/              # GSD reference
│   ├── gsd-2pi-codebase-analysis/  # GSD-2pi analysis
│   ├── claude-oauth.md             # Anthropic OAuth stealth spec
│   └── ...
├── .venv/                          # Python virtualenv (gitignored)
├── dist/                           # Build artifacts (gitignored)
├── pyproject.toml                  # Package metadata, deps, tool config
├── uv.lock                         # Lockfile (uv package manager)
├── CLAUDE.md                       # Project instructions for Claude
├── .gitignore                      # Git ignore rules
├── .pre-commit-config.yaml         # Pre-commit hooks (ruff, mypy)
├── .graphifyignore                 # Graphify exclusion list
└── .bg-shell/                      # Background shell artifacts
```

## Package Purposes

### `src/state_core/` — Shared Library
- Purpose: Common substrate consumed by ALL other components — the integration point between build and teach modes
- Contains: Event store (`events.py`), pydantic schemas for all 28+ event types (`schema.py`), DAG scheduler (`scheduler.py`), auth layer (`auth/` with 5 provider implementations), provider routing (`providers/`), worktree abstraction (`worktree.py`), snapshots (`snapshot.py`), database connection factory (`database.py`), migrations runner (`migrations.py`), config resolution (`config.py`), projector (`projector.py`), reconciler (`reconciler.py`), sync mirror (`sync_mirror.py`), dependency container (`deps.py`), HTTP client factory (`http_client.py`), observability (`observability/` with redactor), reactive trigger (`reactive.py`), CLI ops helpers
- Key files: `events.py` (578 lines), `schema.py` (797 lines), `scheduler.py` (828 lines), `auth/base.py` (221 lines), `auth/store.py`

### `src/state_daemon/` — Always-On Service
- Purpose: The engine runtime — owns the event store, serves HTTP API on Unix socket, enforces mode isolation, runs scheduler, manages auth refresh
- Contains: HTTP server (`server.py`), JSON-RPC router (`router.py`), mode middleware (`middleware.py`), SSE bus (`sse.py`), startup orchestrator (`orchestrator.py`), PID management (`pid.py`), crash recovery (`recovery.py`), auth manager (`auth_manager.py`), hook handlers (`hooks.py`), CLI sub-app (`cli.py`), logging config (`logging.py`), Unix socket helpers (`socket.py`), watchers (`watchers.py`), entry point (`__main__.py`)
- Key files: `orchestrator.py` (338 lines — startup sequence), `server.py` (282 lines — custom HTTP/1.1), `middleware.py` (235 lines — mode gate)

### `src/state_build/` — Build-Mode Kernel
- Purpose: GSD-derived build domain — Step state machine, command ports, verifiers, MCP server
- Contains: Step FSM kernel (`kernel.py`), MCP server entry (`mcp.py`), commands (`commands/`), verifiers (`verifiers/`)
- Mode silo: MUST NOT import `state_teach/` (enforced by import-graph linter)
- Key files: `kernel.py` (15 lines — skeleton), `mcp.py` (skeleton)

### `src/state_teach/` — Teach-Mode Kernel
- Purpose: AOL-derived adaptive learning domain — Kolb cycle, concept graph, drill engine, mental model, MCP server
- Contains: Kolb FSM kernel (`kernel.py`), MCP server entry (`mcp.py`), concept graph ops (`concepts.py`), drill engine (`drill.py`), mental model projection (`mental_model.py`), personality loaders (`personalities/`)
- Mode silo: MUST NOT import `state_build/` (enforced by import-graph linter)
- Key files: `kernel.py` (15 lines — skeleton), `mcp.py` (skeleton)

### `src/state_worker/` — Per-Session Worker
- Purpose: Session-scoped worker bridging the opencode plugin shim and the daemon
- Contains: Worker entry (`main.py`, `__main__.py`), session identity (`session.py`), daemon bridge (`bridge.py`)
- Key files: `main.py`, `session.py`

### `src/state_cli/` — Top-Level CLI
- Purpose: The `state` command entry point — Typer app with sub-apps for all operations
- Contains: Main CLI (`main.py`), auth CLI (`auth.py`), snapshot CLI (`snapshot.py`), DAG CLI (`dag.py`)
- Key files: `main.py` (221 lines — Typer app with db, events, auth, snapshot, dag, daemon sub-apps)

## Key File Locations

**Entry Points:**
- `src/state_daemon/__main__.py`: Daemon process entry (`python -m state_daemon`)
- `src/state_cli/main.py`: CLI entry (`state` Typer app)
- `src/state_worker/__main__.py`: Worker process entry (spawned by plugin)
- `src/state_build/mcp.py`: Build MCP server entry
- `src/state_teach/mcp.py`: Teach MCP server entry

**Configuration:**
- `pyproject.toml`: Package metadata, dependencies, ruff config, mypy config, pytest config, coverage config, build config
- `.state/config.toml`: Runtime daemon config (scheduler concurrency cap, etc.)
- `.state/mode.json`: Active execution mode (`build`, `teach`, `both`)
- `.state/auth.json`: Credential vault (chmod 600, gitignored)
- `.planning/config.json`: GSD workflow settings
- `.pre-commit-config.yaml`: Pre-commit hooks (ruff, mypy)

**Core Logic:**
- `src/state_core/events.py`: Event store — append, read, repair, reconcile (578 lines)
- `src/state_core/schema.py`: All 28+ pydantic event models (797 lines)
- `src/state_core/scheduler.py`: Pure-Python DAG scheduler (828 lines)
- `src/state_core/database.py`: SQLite connection factory (60 lines)
- `src/state_core/auth/base.py`: Credential model + AuthMethod protocol (221 lines)
- `src/state_daemon/orchestrator.py`: Daemon startup sequence (338 lines)
- `src/state_daemon/server.py`: Custom async HTTP/1.1 server (282 lines)
- `src/state_daemon/middleware.py`: Mode enforcement middleware (235 lines)

**Testing:**
- `tests/conftest.py`: Root test fixtures (currently empty)
- `tests/test_events.py`: Event store tests — round-trip, seq enforcement, determinism, Hypothesis property tests (697 lines)
- `tests/test_schema.py`: Schema tests — all 29 data models + typed events + discriminated unions (749 lines)
- `tests/test_scheduler.py`: DAG scheduler tests
- `tests/test_daemon_*.py`: Daemon component tests (server, middleware, socket, sse, pid, recovery, logging, cli, auth_manager, service)
- `tests/auth/`: Auth-specific tests with per-provider golden file tests

## Naming Conventions

**Files:**
- Snake_case: `events.py`, `sync_mirror.py`, `auth_manager.py`, `model_profile.py` — all Python files use `snake_case`
- Test files: `test_<module>.py` — mirror source module names
- Migration files: `NNNN_description.sql` — numbered sequentially

**Directories:**
- Package names use `snake_case` with `state_` prefix: `state_core/`, `state_build/`, `state_teach/`, `state_daemon/`, `state_worker/`, `state_cli/`
- Test directories mirror source structure: `tests/auth/` mirrors `src/state_core/auth/`
- Planning directories: `v{N}/phases/{NNN-description}/` — milestone version + sequential phase number + slug

**Classes:**
- PascalCase: `SqliteEventStore`, `DAGScheduler`, `StepMachine`, `KolbMachine`, `ModeMiddleware`, `DaemonServer`, `JsonRpcRouter`, `EventEnvelope`, `CrashRecovery`, `AuthRefreshLoop`, `SseBus`
- Pydantic models use `ConfigDict(extra="forbid", frozen=True)` consistently

**Functions/Methods:**
- snake_case: `append()`, `read_stream()`, `topo_sort()`, `detect_cycles()`, `resolve_opencode_url()`, `build_event()`
- Async functions are idiomatic: `async def append(...)`

**Constants:**
- UPPER_CASE for module-level constants: `DEFAULT_OPENCODE_PORT = 17495`, `PARSE_ERROR = -32700`

**Type Aliases:**
- PascalCase: `Mode = Literal["build", "teach", "kernel"]`, `EdgeKind = Literal["blocks", "soft", "data"]`, `StepState = Literal[...]`, `KolbStage = Literal[...]`

**Protocols:**
- PascalCase: `EventStore`, `Router`, `SseHandler`, `GetHandler`, `StepExecutor`, `AuthMethod`

## Import Patterns

**Two import path styles coexist (both valid due to `src/` in `pythonpath`):**
- Relative-to-package: `from state_core.events import SqliteEventStore` (used in `src/state_daemon/orchestrator.py` for `state_core` imports, and in `src/state_cli/` for `state_core` imports)
- Absolute: `from src.state_core.events import SqliteEventStore` (used in `src/state_core/` internal imports, `src/state_cli/main.py`, `tests/`)
- The `pyproject.toml` sets `pythonpath = ["src"]` for pytest; production entry points handle path resolution via `-m` or installed package

**Import groups (observed convention):**
1. `from __future__ import annotations` — ALWAYS first
2. stdlib imports (asyncio, json, os, pathlib)
3. Third-party imports (aiosqlite, pydantic, structlog, httpx, ulid)
4. `state_core` / `src.state_core` internal imports
5. Same-package imports (`from src.state_daemon.X import Y`)

## Where to Add New Code

**New Event Type:**
- Define data payload model in `src/state_core/schema.py` (add to the file, following the `_Data` naming convention)
- Define typed event class in `src/state_core/schema.py`
- Add to discriminated union (`ArcEvent`, `StepEvent`, etc.)
- Add to `AnyStateEvent` union
- Add to `AggregateType` literal if new aggregate

**New Auth Provider:**
- Create `src/state_core/auth/providers/<provider_name>.py`
- Implement `AuthMethod` Protocol from `src/state_core/auth/base.py`
- Add to credential `Credential` union in `src/state_core/auth/base.py`
- Add tests in `tests/auth/providers/test_<provider_name>.py`
- Add golden file tests in `tests/auth/golden/<provider_name>/`

**New Daemon HTTP Endpoint:**
- Register handler via `JsonRpcRouter.add_method()` or `DaemonServer.add_get_handler()` in `src/state_daemon/orchestrator.py:startup()`
- Mode enforcement is automatically applied by the `ModeMiddleware` wrapper

**New Build-Mode Feature:**
- Add to `src/state_build/` (kernel logic, commands, verifiers, or MCP tools)
- Add tests in `tests/` (not under `tests/auth/`)
- Ensure NO imports from `state_teach` (linted by import guard)

**New Teach-Mode Feature:**
- Add to `src/state_teach/` (kernel logic, concepts, drill, mental model, or MCP tools)
- Add tests in `tests/` (not under `tests/auth/`)
- Ensure NO imports from `state_build` (linted by import guard)

**New CLI Command:**
- Add command function to existing sub-app in `src/state_cli/` or create new sub-app
- Register in `src/state_cli/main.py` via `app.add_typer(sub_app)`
- Use `asyncio.run()` wrapper for async commands

**Tests:**
- Mirror source structure: `tests/test_<module>.py` for `src/state_core/<module>.py`
- Sub-packages get test directories: `tests/auth/` mirrors `src/state_core/auth/`
- Fixtures in `conftest.py` at the appropriate level (root, auth/, providers/)
- Use `pytest.fixture(autouse=True)` for DB isolation (`tmp_path` + `monkeypatch`)
- Use Hypothesis `@given` for property-based tests on event store and scheduler

## Special Directories

**`.planning/`:**
- Purpose: GSD planning artifacts — roadmap, research, phase plans, state tracking
- Generated: Yes (by GSD workflow commands)
- Committed: Yes (planning docs are local-only per `config.json: commit_docs=false`)

**`.state/`:**
- Purpose: Runtime state — databases, auth vault, mode config, build/teach artifacts, logs
- Generated: Yes (by daemon and CLI at runtime)
- Committed: No (gitignored — contains credentials and runtime state)

**`.state-inputs/`:**
- Purpose: Reference materials — opencode source snapshots, auth specs, GSD references
- Generated: Partially (manual snapshots + copied references)
- Committed: No (gitignored — large reference files, some contain sensitive analysis)

**`dist/`:**
- Purpose: Build output artifacts
- Generated: Yes (by `uv build` or `hatchling`)
- Committed: No

**`graphify-out/`:**
- Purpose: Knowledge graph outputs from graphify tool
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-05-05*
