# CONTEXT: Phase 001 — Project scaffolding + pyproject + state_core package skeleton

**Status:** Locked (decisions captured below are NON-NEGOTIABLE for this phase)

---

## Phase Scope

Create the `state_core` package, `pyproject.toml` (pinning per STACK.md), `uv` workspace, and base directory layout for all 6 Python packages: `state_core`, `state_build`, `state_teach`, `state_daemon`, `state_worker`, `state_cli`.

## Locked Decisions

### Build System
- **Package manager:** `uv` (≥0.5.0), not pip/poetry/pipenv
- **Build backend:** `uv_build` (≥0.5.0), not hatchling/setuptools
- **Project name:** `state`
- **Version:** `0.1.0`
- **Python requirement:** `>=3.12`

### Package Layout
- All Python packages live under `src/` (src-layout, not flat)
- `pyproject.toml` carries ALL config (ruff, mypy, pytest) — no `.ruff.toml`, `setup.cfg`, `tox.ini`
- `[tool.setuptools.packages.find]` with `where = ["src"]` for package discovery

### Mode Silos
- `state_build` and `state_teach` are **physically separate packages** that may never import each other
- Each has an `__init__.py` docstring warning about the silo constraint
- Both must be importable in the same process (for CI import-graph lint)

### Package Structure
- `state_core` — shared kernel: schema, events, scheduler, worktree, snapshot, auth, providers
- `state_build` — build-mode kernel: StepMachine, mcp.py, commands/, verifiers/
- `state_teach` — teach-mode kernel: KolbMachine, mcp.py, concepts, drill, mental-model, personalities/
- `state_daemon` — always-on service: server.py, watchers.py, cli.py
- `state_worker` — per-session worker: main.py, bridge.py
- `state_cli` — top-level CLI: main.py (Typer)

### Code Conventions
- Every `.py` file: `from __future__ import annotations` at top
- Every module: docstring describing purpose (1-3 sentences)
- Type annotations on all function signatures, even stubs
- Class/function stubs where ARCHITECTURE.md describes clear responsibility
- `ruff` lint+format, `mypy --strict` type checking

### Testing
- Test directory: `tests/` at project root
- `pytest` with `asyncio_mode = "auto"`
- Phase 001 tests: import smoke tests and `EventEnvelope` schema validation

### Dependencies
- 19 runtime deps from STACK.md (exact version floors)
- Dev deps: pytest ecosystem, ruff, mypy, pre-commit
- No ORM, no networkx, no Textual, no FastAPI, no Prefect/Dask/Airflow
- No `fastmcp` third-party package (use `FastMCP` from official `mcp` package)

## Research Sources Used
- `.planning/research/STACK.md` — library versions, pyproject layout, tooling
- `.planning/research/ARCHITECTURE.md` — directory layout (§1.3), mode enforcement (§7)
- `.planning/PROJECT.md` — cardinal rules, constraints, key decisions
