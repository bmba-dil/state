# Technology Stack

**Analysis Date:** 2026-05-05

## Languages

**Primary:**
- Python 3.12+ — Entire project (daemon, worker, CLI, MCP servers, auth, provider routing, event store). All six packages under `src/` are pure Python.
- `requires-python = ">=3.12"` in `pyproject.toml` line 4

**Secondary:**
- Not applicable — No other languages detected. No `package.json`, `Cargo.toml`, `go.mod`, or `Makefile` present.

## Runtime

**Environment:**
- Python 3.12+ (strict floor — uses 3.12 generics syntax, `from __future__ import annotations`)
- Virtual environment managed via uv (`.venv/` gitignored)

**Package Manager:**
- uv >= 0.5.0 (PEP 621-compliant, manages `pyproject.toml` + `uv.lock`)
- Lockfile: `uv.lock` present (504 KB)
- `pip3` fallback available per global instructions

**Build System:**
- Backend: hatchling >= 1.27 (`[build-system]` in `pyproject.toml` line 44-46)
- Builds six wheel packages from `src/`: `state_core`, `state_build`, `state_teach`, `state_daemon`, `state_worker`, `state_cli` (`pyproject.toml` lines 91-98)

## Frameworks

**Core (Data & Validation):**
- pydantic >= 2.13.2 — All data models, event schemas (28+ event types, 9 aggregates), auth models. All schemas use `extra="forbid"`. `pyproject.toml` lines 10-11
- pydantic-settings >= 2.7 — Runtime configuration management

**CLI:**
- typer >= 0.15 — `src/state_cli/main.py` defines the `state` CLI with subcommands: `db init`, `events tail/replay/export`, `auth`, `snapshot`, `dag`, `daemon`. Five sub-typer apps registered
- rich >= 13.9 — Terminal output formatting (used by typer internally)

**Observability:**
- structlog >= 25.1 — Structured logging throughout all packages. Unified chain: structlog-native loggers + stdlib loggers (httpx, litellm, pygit2, aiosqlite) all flow through shared processor chain. JSON renderer via `ProcessorFormatter`

**Plugin System:**
- pluggy >= 1.6.0 — Plugin architecture for extensible auth methods and MCP tool registration

**MCP Protocol:**
- mcp >= 1.27.0 — MCP SDK for tool registration. Two independent MCP servers (`state-build`, `state-teach`) planned; currently stubbed at `src/state_build/mcp.py` and `src/state_teach/mcp.py`

## Key Dependencies

**Critical (Load-Bearing):**

| Package | Version | Purpose |
|---------|---------|---------|
| mcp | >= 1.27.0 | MCP SDK — matches opencode's TS SDK 1.27.1 |
| litellm | >= 1.80.0 | Provider routing abstraction for 12+ AI model providers |
| anthropic | >= 0.80.0 | Direct Anthropic SDK escape hatch for OAuth stealth + extended thinking |
| httpx | >= 0.28.1 | Async HTTP client for all network I/O (provider calls, opencode API, OAuth flows) |
| aiosqlite | >= 0.22.1 | Async SQLite for event store (WAL mode, synchronous=FULL) |
| pygit2 | >= 1.19.2 | libgit2 wheels for worktree operations (fallback when opencode unreachable) |
| filelock | >= 3.20.3 | Process-level file locking for auth refresh (CVE-2026-22701 floor — hard) |
| orjson | >= 3.11.8 | Fast JSON serialization for event store, auth vault, export |
| python-ulid | >= 3.0 | ULID generation for event IDs (time-sortable, 128-bit) |
| cryptography | >= 43.0 | Cryptographic primitives for auth layer |

**Infrastructure:**

| Package | Version | Purpose |
|---------|---------|---------|
| google-auth | >= 2.35 | Google OAuth credentials for Gemini CLI and Antigravity |
| google-auth-oauthlib | >= 1.2 | OAuthlib integration for Google flows |
| google-genai | >= 0.9 | Google GenAI SDK for Gemini inference |
| openai | >= 1.60 | OpenAI SDK for inference |

**Dev Dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >= 8.4.0 | Test framework |
| pytest-asyncio | >= 1.3.0 | Async test support (asyncio_mode="auto") |
| pytest-cov | >= 6.0 | Coverage reporting |
| hypothesis | >= 6.120 | Property-based testing |
| pytest-httpx | >= 0.35 | HTTP client mocking |
| pytest-mock | >= 3.14 | Mock fixtures |
| freezegun | >= 1.5 | Time freezing for deterministic tests |
| pytest-xdist | >= 3.6 | Parallel test execution |
| ruff | >= 0.9.0 | Linting + formatting |
| mypy | >= 1.14 | Static type checking |
| pre-commit | >= 4.0 | Git hook framework |

## Configuration

**Formatting:**
- ruff (formatter): quote-style="double", indent-style="space", line-length=120, target-version=py312 (`pyproject.toml` lines 48-60)
- pre-commit hooks: ruff --fix, ruff-format, mypy, trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, no-large-files (>500KB) (`.pre-commit-config.yaml`)

**Linting:**
- ruff lint: select=["E","F","I","N","W","UP","B","SIM","ARG","C4","T20"] (`pyproject.toml` lines 52-53)
- mypy: strict=true, python_version="3.12", warn_unused_ignores=true (`pyproject.toml` lines 62-68)

**Type Checking:**
- Strict mypy mode enforced project-wide
- `py.typed` marker in `src/state_core/py.typed`
- Pydantic models use `extra="forbid"` and `frozen=True` throughout
- `__future__ import annotations` used in all modules

**Testing:**
- Test directory: `tests/` (co-located at project root, parallel to `src/`)
- pytest config: asyncio_mode="auto", pythonpath=["src"], testpaths=["tests"] (`pyproject.toml` lines 70-79)
- Custom markers: `e2e`, `provider_parity`, `integration`, `slow`
- Coverage: sources=["state_core","state_build","state_teach","state_daemon","state_worker","state_cli"]
- 49 test modules detected in `tests/`, with dedicated `auth/` subdirectory

**Environment Variables:**
- `STATE_DB_PATH` — override event store database path (default: `.state/events.sqlite`)
- `STATE_OPENCODE_URL` — override opencode API base URL (default: resolved from `opencode.json`)
- `STATE_AUTH_JSON` — override auth vault path (default: `.state/auth.json`)
- `STATE_HTTP_PROXY` — proxy URL for provider inference traffic
- `STATE_CA_BUNDLE` — custom CA certificate PEM file path
- `STATE_TLS_VERIFY` — set "false" to disable TLS verification (dev/test only)

**Project Configuration:**
- `.planning/config.json` — GSD workflow toggles (mode=yolo, granularity=fine, parallelization=true, concurrent=true, quality.level=high)

## Platform Requirements

**Development:**
- Python 3.12+
- macOS (primary development platform) or Linux
- git 2.x+ (for pygit2 worktree operations)
- uv for package management

**Production:**
- macOS: launchd user agent (daemon)
- Linux: systemd --user service (daemon)
- No containerization detected (no Dockerfile, no docker-compose.yml)
- Unix domain sockets for daemon communication (macOS: `$TMPDIR/state-<hash16>.sock`; Linux: `$XDG_RUNTIME_DIR/state-<hash16>.sock`)

---

*Stack analysis: 2026-05-05*
