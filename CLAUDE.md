<!-- GSD:project-start source:PROJECT.md -->
## Project

**state** — a Python 3.12+ agentic state-machine workflow engine fusing software delivery (GSD-lineage) and adaptive learning (AOL-lineage) into one engine with two exclusive execution modes (Build / Teach), built first-class against opencode's extension surface and portable to other provider-based CLIs via MCP.

See `.planning/PROJECT.md` for full context, cardinal rules, and architectural decisions.

**Core value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.

**Current focus:** Tier 1 foundation milestones (M-A1 Event Store, M-A2 Auth, M-A3 Provider Routing, M-A4 Worktree+Snapshot, M-A5 DAG Scheduler). All five are parallel-safe.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Primary implementation language: **Python 3.12+** (deliberate learning-through-build choice).

Load-bearing pins (from `.planning/research/STACK.md`):

- MCP SDK: `mcp>=1.27.0` (matches opencode's TS SDK 1.27.1)
- Provider routing: `litellm>=1.80.0` + `anthropic>=0.80.0` escape hatch (OAuth stealth never routes through litellm)
- Git/worktree: `pygit2>=1.19.2` (libgit2 wheels)
- Data/async: `pydantic>=2.13.2`, `orjson>=3.11.8`, `aiosqlite>=0.22.1`, `httpx>=0.28.1`
- Locking: `filelock>=3.20.3` (CVE-2026-22701 floor — hard)
- Plugins: `pluggy>=1.6.0`
- Auth: `google-auth>=2.35`, `google-auth-oauthlib>=1.2`, `cryptography>=43.0`
- Packaging: `uv>=0.5.0` + `uv_build`
- CLI: `typer>=0.15`, `rich>=13.9`
- Observability: `structlog>=25.1`
- Testing: `pytest>=8.4.0`, `pytest-asyncio>=1.3.0`, `hypothesis>=6.120`, `pytest-httpx>=0.35`
- Opencode plugin catalog (match byte-for-byte): bun 1.3.13, typescript 5.8.2, effect 4.0.0-beta.48, zod 4.1.8, solid-js 1.9.10, @opentui/{core,solid} 0.1.99

Rejected: Prefect/Dask/Airflow, LangChain/LangGraph, SQLAlchemy/Alembic, GitPython, NetworkX, Textual (primary TUI), FastAPI, Poetry, AnyIO/Trio, fastmcp, tiktoken.

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- Use `python3` / `pip3` (not `python` / `pip`).
- Mode isolation is physical: `state.build.*` must not import `state.teach.*` or vice versa. A CI import-graph lint enforces this.
- Build and Teach modes have separate MCP servers (`state-build`, `state-teach`), separate on-disk subtrees (`.state/build/` vs `.state/teach/`), and separate command namespaces.
- Every domain event is written to `.state/events.sqlite` FIRST, then mirrored to opencode's SyncEvent. SQLite is authoritative.
- Event payloads must be deterministic — no `datetime.now()` or randomness in handlers; replay must be bit-identical.
- Auth credentials live in `.state/auth.json` with chmod 0600 verified on every read.
- Anthropic OAuth stealth headers must match `state-inputs/claude-oauth.md` byte-for-byte. OAuth traffic NEVER routes through litellm.
- Product planning hierarchy: **Arc → Phase → Slice → Step** (the Step tier owns the full discuss/plan/execute/verify cycle).
- GSD planning hierarchy (this repo's `.planning/`): milestones → phases. One GSD milestone = one product Arc.

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Six physical components (see `.planning/research/ARCHITECTURE.md` for full detail):

1. **state-daemon** — always-on user service (launchd / systemd --user). Owns event store, scheduler, auth, provider routing, mode middleware.
2. **state-worker** — per-opencode-session Python process. Owns hot session state, forwards opencode hooks to daemon over HTTP+SSE.
3. **state-build MCP server** — exposes build-mode tools to opencode; registered only when mode in `{build, both}`.
4. **state-teach MCP server** — exposes teach-mode tools; registered only when mode in `{teach, both}`.
5. **@state/opencode-plugin** — single TS bundle carrying the 9-hook shim (~300 LOC) and SolidJS TUI extensions (sidebar, routes, dialogs, statusline).
6. **`.state/` on-disk tree** — markdown artifacts (ARC/PHASE/SLICE/STEP.md, STATE.md, DECISIONS.md) + SQLite (`events.sqlite`, `mental-model` projection) + auth vault.

Mode enforcement is defense-in-depth (6 layers); the canonical gate is the daemon's HTTP middleware.

Worktree: per-Slice. Opencode worktree service preferred when available; pygit2 fallback otherwise.

Snapshots: Step + Slice boundaries.

<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Entry points:
- `/gsd:progress` — check project status and next action
- `/gsd:plan-phase <milestone.phase>` — plan a specific phase before execution (e.g., `/gsd:plan-phase M-A1.P1`)
- `/gsd:execute-phase <milestone.phase>` — execute a planned phase
- `/gsd:quick` — small ad-hoc tasks outside the roadmap
- `/gsd:debug` — investigation and bug fixing

Config: `.planning/config.json` — mode=yolo, granularity=fine, parallelization=true, commit_docs=false (planning docs local-only).

Reference material (gitignored): `state-inputs/opencode/`, `state-inputs/get-shit-done/`, `state-inputs/gsd-2pi-codebase-analysis/`, auth specs (`state-inputs/claude-oauth.md`, `state-inputs/gsd2-auth-analysis.md`).

<!-- GSD:workflow-end -->
