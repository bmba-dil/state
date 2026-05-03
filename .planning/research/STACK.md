# Stack Research: `state`

**Domain:** Python agentic state-machine workflow engine + opencode plugin + MCP servers
**Researched:** 2026-04-22
**Overall Confidence:** HIGH

This document is prescriptive. Every Arc in the roadmap MUST reference libraries by the exact
name + version floor defined here. Alternatives were considered and rejected; the rejection
reasons are recorded so future contributors don't re-litigate.

---

## Scope split

`state` is two physically separate codebases that ship together:

1. **Python daemon** (`state-daemon`, `state-build`, `state-teach`) — the engine, CLIs,
   and two MCP servers. Python 3.12+.
2. **Opencode plugin** (`@state/opencode-plugin`) — TypeScript/SolidJS, ~300-LOC hook shim
   + TUI extensions. Bun-first, mirrors opencode conventions byte-for-byte.

Both are versioned and released together. The Python side is primary; the plugin is a thin
client.

---

## Core Stack — Python daemon

### Runtime & async

| Technology | Version floor | Purpose | Why | Confidence |
|------------|---------------|---------|-----|------------|
| CPython | **3.12.0** | Runtime | Project mandate (learn-through-build). 3.12's `asyncio.TaskGroup`, `typing` improvements, f-string relaxations, and per-interpreter GIL groundwork all pay off | HIGH |
| `asyncio` (stdlib) | 3.12 built-in | Concurrency | TaskGroup is now mature (3.11+), ExceptionGroup handling is clean, subprocess streaming is first-class. Matches the natural shape of MCP + HTTP + DAG scheduling | HIGH |
| `anyio` | **≥4.8.0** | Structured-concurrency abstraction used by the MCP SDK | We don't adopt anyio as our primary concurrency API, but `mcp` transitively depends on it, so pin it for reproducibility and know the API if we need it | HIGH |

**Decision: asyncio over anyio/trio as the primary API.** The ecosystem (httpx, aiosqlite, mcp,
litellm, anthropic SDK, pytest-asyncio) is all asyncio-native. AnyIO buys abstraction we don't
need — we never plan to run on Trio. Exposing `asyncio.TaskGroup` directly is simpler pedagogy
for a Python learner, too.

### HTTP / networking

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `httpx` | **≥0.28.1** | Async HTTP client for opencode server, provider SDK escape hatches, MCP remote transports, OAuth callback server | Industry default; HTTP/2 support; shared client model reuses connections; both sync + async APIs; matches the Anthropic Python SDK's own transport choice |
| `httpx-ws` | optional, ≥0.7 | WebSocket support over httpx if we need live opencode SSE multiplexing | Only pulled in if/when opencode bus SSE needs sustained duplex |

**Pattern:** single `httpx.AsyncClient` owned by the daemon, injected via a `Deps` container
into every caller. Litellm, the Anthropic SDK, and our opencode HTTP client all accept a
user-provided httpx client — reuse the same one for connection pooling and unified proxy/TLS
config.

### IPC / daemon transport

| Mechanism | Purpose | Why |
|-----------|---------|-----|
| Unix domain socket (macOS/Linux) + TCP loopback (Windows fallback) | Daemon ↔ CLI + daemon ↔ plugin | Low-latency, OS-enforced perms, zero deps. `asyncio.start_unix_server` exists in stdlib |
| JSON-RPC 2.0 framing over the socket | Structured calls | Standard, easy to debug with `nc`, mirrors the MCP wire shape |
| SSE (via httpx) | Plugin subscribing to daemon events | Mirrors how opencode exposes its bus; the plugin already knows the pattern |

No new dependency is introduced here — asyncio + orjson cover it. We DO NOT adopt `grpcio`
(overkill, schema overhead), `zmq` (new mental model), or `dbus` (Linux-only).

### Data / serialization

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `pydantic` | **≥2.13.2** | All data models: events, plans, agent specs, config, CLI args | V2 is production-stable, V1 is EOL-adjacent. Rust core is fast enough that we don't dodge it for hot paths. Matches opencode's Zod ethos on the TS side |
| `pydantic-settings` | ≥2.7 | Config loading with layered sources (env, file, CLI) | Native pydantic integration; replaces dynaconf/omegaconf bloat |
| `orjson` | **≥3.11.8** | JSON for events, HTTP, SQLite columns | Fastest correct JSON; native datetime/UUID/dataclass; 10-20× stdlib json. Critical for event replay throughput |

**NOT using:** `dataclasses-json`, `marshmallow`, `attrs`. Pydantic v2 owns this tier.

### Event store / persistence

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `sqlite3` (stdlib) | 3.12 built-in | Schema + writer path (synchronous) for SQLite at `.state/events.sqlite` | Daemon owns all writes on a dedicated writer task; one WAL connection; simple and correct |
| `aiosqlite` | **≥0.22.1** | Async reader path for dashboards, MCP tools, CLI queries | Shared-thread queue semantics match our "one writer, many readers" model; battle-tested; minimal surface |
| `filelock` | **≥3.20.3** | Cross-process lock on `.state/daemon.lock` and `.state/auth.json` writes | TOCTOU-patched (CVE-2026-22701 fixed in 3.20.3); portable; async variant available; covers the rare case where two `state` CLIs race against the same `.state/` directory |

**Pinning note:** we require filelock ≥3.20.3 specifically because of the SoftFileLock TOCTOU
CVE fixed in that release. Do not float below this.

**Migration strategy:** hand-rolled. A `.state/events.sqlite` `schema_migrations` table, plus a
numbered-file pattern (`migrations/0001_init.sql`, `0002_*.sql`). We do NOT adopt Alembic — we
are not SQLAlchemy users and don't want an ORM. Events are append-only; schema evolution is
rare and small.

**NOT using:** SQLAlchemy (too heavy), Tortoise ORM, SQLModel (drags SQLAlchemy), Alembic,
Peewee. The event log is append-only JSON-blobs with indexed metadata columns; an ORM is a
negative-value abstraction here.

### MCP server (two servers: `state-build`, `state-teach`)

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `mcp` (official SDK) | **≥1.27.0** | MCP server protocol, tool/prompt/resource registration, transports | Official Anthropic SDK. Opencode bundles `@modelcontextprotocol/sdk` **1.27.1** (see `packages/opencode/package.json:111`), so version-floor parity avoids protocol drift |
| `mcp[cli]` extras | same | `mcp dev` inspector + STDIO smoke test | Included in same package; zero extra cost |

**Transports we support:**
- **STDIO** — primary. Matches how opencode launches MCP servers (`type: "local", command: [...]`).
- **Streamable HTTP** — for remote hosts (Claude Code over network, headless CI). Use the MCP
  SDK's `streamable_http` transport, not the deprecated SSE transport.
- **NOT SSE** — explicitly deprecated by MCP spec; only used for legacy-client fallback.

**Compatibility claim:** opencode's MCP client is `@modelcontextprotocol/sdk@1.27.1`. Python
SDK `mcp@1.27.0+` speaks the same protocol version — verified HIGH confidence.

**Framework choice within MCP SDK:** we use the `FastMCP` decorator-based server in the
`mcp` package for the build and teach servers. It is the ergonomic layer bundled with the
official SDK; no extra `fastmcp` third-party package is needed (do NOT install the third-party
`fastmcp` package on PyPI — use the one shipped inside `mcp`).

### Provider routing

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `litellm` | **≥1.80.0** | Unified multi-provider routing, cost tracking, fallbacks, retries, streaming normalization | 100+ providers, supports Anthropic extended thinking via `thinking: {type: "adaptive" | "enabled", budget_tokens: N}`, native `cache_control: ephemeral` forwarding on Anthropic. The 1.80 floor is chosen to capture recent extended-thinking + context-management fixes; check actuals at install time |
| `anthropic` | **≥0.80.0** | Direct SDK escape hatch for fine-grained Anthropic features | Extended thinking blocks arrive verbatim (no litellm normalization loss), OAuth token flow for Anthropic Pro/Max stealth (uses same creds format), fine-grained cache-control placement at arbitrary block positions, batching API, files API |
| `google-genai` | ≥0.9 | Gemini CLI OAuth free-tier handshake | The Gemini CLI free-tier uses Google's OAuth; we need the token flow. Raw provider calls still go through litellm |
| `openai` | ≥1.60 | Copilot device-code flow + OpenAI-compat routing helpers | Required for the GitHub Copilot OAuth path; most Copilot endpoints are OpenAI-compat |

**Pattern:** litellm is the default path for every provider call. Our `ProviderRouter` resolves
a call config `(provider_id, model_id, auth_method, features)` and either:
1. **Default path** — `await litellm.acompletion(model="anthropic/...", ..., client=shared_httpx)`
2. **Escape hatch** — if features include `anthropic_extended_thinking_with_cache_breakpoints`
   at specific block positions, bypass litellm and call `anthropic.AsyncAnthropic(http_client=shared_httpx).messages.create(...)` directly.

All SDKs accept a user-provided `httpx.AsyncClient`, so we share connection pooling across the
whole daemon.

**Auth methods covered (day-one requirement):**

| Method | Library | Storage | Notes |
|--------|---------|---------|-------|
| Anthropic OAuth (Claude Pro/Max stealth) | Custom (follows `state-inputs/claude-oauth.md`) | `.state/auth.json` | Non-trivial — implement per the exact stealth spec; Anthropic SDK accepts the resulting bearer token |
| Gemini CLI free-tier OAuth | `google-auth-oauthlib` + `google-auth` + `google-genai` | `.state/auth.json` | Standard Google OAuth; refresh-token flow |
| Antigravity OAuth | Custom via `httpx` + OAuth2 device-code | `.state/auth.json` | Device-code flow; template from Copilot impl |
| GitHub Copilot device-code | Custom via `httpx` | `.state/auth.json` | Device-code → token exchange; sub to OpenAI-compat endpoint |
| Plain API keys | None | `.state/auth.json` (env var fallback) | For every provider litellm knows |

**Auth libraries:**

| Library | Version floor | Purpose |
|---------|---------------|---------|
| `google-auth` | ≥2.35 | Gemini OAuth token management |
| `google-auth-oauthlib` | ≥1.2 | Gemini OAuth flow helpers |
| `cryptography` | ≥43.0 | Token encryption at rest in `.state/auth.json` (chmod 600 is necessary but not sufficient on shared machines) |
| `keyring` | optional ≥25 | OS keychain integration (opt-in; gated behind config flag) |

### Git / worktree layer

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `pygit2` | **≥1.19.2** | Git operations + worktree lifecycle (add/list/lookup/prune) in the fallback path when opencode's worktree service is unavailable | libgit2 bindings; worktree API is stable (`Repository.add_worktree(name, path)`, `list_worktrees()`, `lookup_worktree(name)`, `Worktree.prune()`); wheels bundle libgit2 so no system install; supports Python 3.11–3.14 |

**Hybrid strategy** (matches PROJECT.md "opencode worktree service preferred, pygit2 fallback"):

- **When the host is opencode**: call `client.worktree.create/list/remove/reset` via the
  opencode HTTP client. Zero filesystem-level Git code in `state` itself; opencode owns the
  lifecycle, emits `worktree.ready`/`worktree.failed` bus events we subscribe to.
- **When the host is Claude Code / Gemini CLI / Qwen Code / standalone**: `pygit2` covers
  add_worktree / list / lookup / prune. Snapshots at step/slice boundaries use
  `repo.create_blob_fromdisk` + a `state-snapshots` ref namespace (out-of-tree refs, no
  pollution of user branches).

**Rejected alternatives:**
- **`GitPython`** — subprocess-based, slow, API quirks (detached object lifetimes). We don't
  need its flexibility; `pygit2` is faster and cleaner.
- **Shelling out to `git` directly** — portable but loses structured error handling; error
  parsing from stderr is brittle; subprocess overhead in a hot worktree-creation path is
  avoidable. We keep `asyncio.create_subprocess_exec("git", ...)` as a last-resort escape hatch
  for exotic commands (e.g., `git sparse-checkout`) we may need later.

### DAG / graph algorithms

**Decision: pure Python, no networkx.**

**Rationale:** our DAG is small (dozens to low hundreds of nodes per Arc), agent-shaped (edges
carry type metadata, nodes are Pydantic models), and we need custom semantics (typed
`depends_on`, concurrency budgets per node, partial-completion propagation). NetworkX's value
is algorithm breadth for generic graphs — we use exactly three operations:

1. Topological sort (Kahn's algorithm, ~30 lines of Python)
2. Cycle detection during roadmap validation (DFS with color marking, ~20 lines)
3. "Frontier" calculation — all nodes whose predecessors are complete (trivial)

Importing networkx to use 1% of it drags in `scipy`-adjacent optional deps and adds a mental
model (`nx.DiGraph`) that clashes with our Pydantic-native node objects. We keep the
scheduler ~200 lines of pure Python in `state/core/scheduler.py` with unit tests.

| Library | Version | Purpose |
|---------|---------|---------|
| (none) | — | DAG lives in hand-rolled `state/core/scheduler.py` |

**If we ever outgrow it:** `networkx>=3.6` is the escape hatch. Not before.

### Plugin architecture (extensibility within the Python daemon)

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `pluggy` | **≥1.6.0** | Hook system for extension points: custom verifiers, custom teach-mode modes, third-party mode kernels | Powers pytest and tox; hook ordering + early-return semantics; 38M weekly downloads; minimal surface |
| `importlib.metadata` (stdlib) | 3.12 built-in | Entry-point discovery for pip-installed extensions | Standard discovery path |

**Pattern:** define hook specs in `state/plugins/specs.py`:

```python
hookspec = pluggy.HookspecMarker("state")
hookimpl = pluggy.HookimplMarker("state")

class StateHookSpec:
    @hookspec
    def verify_slice(self, slice: Slice, context: VerifyContext) -> VerifyResult | None: ...
    @hookspec
    def teach_mode_observe(self, event: Event, state: LearnerState) -> None: ...
    @hookspec(firstresult=True)
    def route_gray_area(self, decision: GrayAreaDecision) -> Decision | None: ...
```

Third parties publish `state-plugin-foo` on PyPI with an entry point
`state.plugins = foo:plugin_module`. The daemon discovers + loads on startup.

**NOT using:** `stevedore` (OpenStack-flavored, heavy), custom scanner (reinventing pluggy).

---

## Core Stack — Opencode plugin (`@state/opencode-plugin`)

**Rule: mirror opencode's conventions exactly.** Read directly from
`state-inputs/opencode/packages/plugin/package.json` and the root `package.json` — those are the
source of truth. We pin the exact same catalog versions opencode itself uses, because the plugin
is loaded into opencode's runtime.

### Runtime & packaging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Bun** | **1.3.13** (exact match) | Primary dev runtime, test runner, package manager | opencode's `packageManager: "bun@1.3.13"` (root `package.json:7`). Plugin dev uses `bun dev` equivalent. Deno/Node work is in-progress for opentui but bun is authoritative today |
| **TypeScript** | **5.8.2** (match catalog) | Language | opencode catalog pins `typescript: "5.8.2"` |
| `@tsconfig/node22` | **22.0.2** | tsconfig base | Plugin package extends this — matches opencode plugin's own `tsconfig` pattern |
| `@types/node` | **22.13.9** | Node type defs | Catalog version |
| `@types/bun` | **1.3.12** | Bun type defs | Catalog version |
| Node target | ESM module, `"module": "preserve"`, `"moduleResolution": "bundler"` | Build config | Matches `@opencode-ai/plugin` tsconfig exactly |

### Plugin runtime deps (mirror `@opencode-ai/plugin` peerDependencies)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `@opencode-ai/plugin` | workspace peer, **≥1.14.20** | Plugin types + Hooks interface | Our plugin exports a `PluginModule` + `TuiPluginModule`; types come from here. Opencode's v1.14.20 is the reference |
| `@opencode-ai/sdk` | peer, **≥1.14.20** | `createOpencodeClient` for driving the server from the plugin | Used for programmatic session/tool/worktree control from hooks |
| `effect` | **4.0.0-beta.48** (catalog match) | Effect system opencode uses pervasively | Our plugin consumes `Event`, `Config` etc. which are Effect-flavored Zod schemas; avoid version mismatch |
| `zod` | **4.1.8** (catalog match) | Schema validation inside hooks | Same reason — shared types |
| `@opentui/core` | **0.1.99** peer | TUI primitives | For any custom TUI slot/route |
| `@opentui/solid` | **0.1.99** peer | SolidJS bindings for TUI | Build/teach dashboards, DAG viewer, drill UI written in SolidJS per opencode convention |
| `solid-js` | **1.9.10** (catalog match) | UI framework | Non-negotiable — opencode TUI is SolidJS |

### Plugin-specific deps

| Library | Version floor | Purpose |
|---------|---------------|---------|
| `@modelcontextprotocol/sdk` (TS) | **≥1.27.1** | Register + manage the two `state-*` MCP servers (plugin auto-adds them to opencode config on first install) |
| `ulid` | 3.0.1 (catalog match) | Event + session IDs; matches opencode's own ID format |
| `remeda` | 2.26.0 (catalog match) | Functional helpers, matches opencode style |

### Plugin dev tooling (mirror opencode)

| Tool | Version | Purpose |
|------|---------|---------|
| `oxlint` | **1.60.0** | Linting — opencode uses oxlint, not ESLint |
| `prettier` | **3.6.2** | Formatting, with `{ semi: false, printWidth: 120 }` to match opencode's config exactly |
| `@typescript/native-preview` | 7.0.0-dev.20251207.1 | Fast typecheck via `tsgo --noEmit` — opencode plugin uses this |
| `turbo` | 2.8.13 | Monorepo builds if we split plugin+sdk+types; optional for now |

**Build command:** `tsc` (build plugin) + `bun build` (if bundling). Match
`@opencode-ai/plugin`'s `"build": "tsc"` minimalism — no esbuild/rollup/vite ceremony.

### Plugin scope — what lives in the TS side

Per PROJECT.md constraints, the plugin is **bundled single package** (~300 LOC hook shim + TUI
extensions). TS code is thin; all real logic lives in the Python daemon and the plugin
round-trips through:

1. The daemon's Unix socket / HTTP IPC (JSON-RPC)
2. opencode's `createOpencodeClient` for reading state
3. Registering the two MCP servers programmatically

TS handles:
- Hook wiring (translate opencode hook events → daemon RPC calls)
- TUI slot/route/dialog registrations (sidebar, routes, drill UI, DAG viewer, statusline)
- Auto-registration of MCP servers in `opencode.json` on first run
- MCP server process supervision (start/stop/restart `state-build` and `state-teach`)

---

## Testing stack (Python)

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `pytest` | **≥8.4.0** | Test runner | Industry default; `pytest-asyncio>=1.3` requires 8.4.0 minimum |
| `pytest-asyncio` | **≥1.3.0** | Async test support | Latest 1.x stable; strict-mode event-loop management; Python 3.12 support |
| `pytest-cov` | ≥6.0 | Coverage | Standard |
| `hypothesis` | ≥6.120 | Property-based testing for event replay, DAG scheduler invariants, auth token parsing | Critical for the event store: "any sequence of events replays to the same projection" is a property, not a fixture |
| `pytest-httpx` | ≥0.35 | Mock httpx in provider-routing tests | Same transport our production code uses; no wiremock ceremony |
| `pytest-mock` | ≥3.14 | Convenience wrapper on `unittest.mock` | Standard |
| `freezegun` | ≥1.5 | Freeze time in event-ordering tests | Event timestamps are load-bearing in replay |
| `pytest-xdist` | ≥3.6 | Parallel test execution | Helps on the full E2E matrix |
| `trio` | — | NOT USED | We're asyncio-only |

### Opencode E2E tests

- Spawn a real `opencode` binary via `bun` in a pytest fixture (the binary is pinned in
  `resources/opencode-version.txt`), register the plugin via a test-scope config directory,
  drive sessions via `OpencodeClient`.
- Tests live in `tests/e2e_opencode/`; marked `@pytest.mark.e2e` and excluded from default run.
- TS side uses `bun test` for the plugin unit tests (hook translation correctness).

### Provider parity matrix

- `tests/provider_parity/` — for each provider, run the same 10 reference prompts through
  `ProviderRouter`, snapshot the normalized output, diff. Hypothesis-generated prompt set
  fuzzes the cache-control and extended-thinking paths.

---

## Packaging

### Build backend — `uv_build`

| Tool | Version floor | Purpose | Why |
|------|---------------|---------|-----|
| `uv` | **≥0.5.0** | Package manager, installer, lockfile (`uv.lock`), virtualenv | Default for new projects in 2026; 10–100× faster than pip+venv; first-class build backend; lockfile is reproducible across Linux/macOS/Windows |
| `uv_build` | bundled with `uv` | `[build-system]` backend | Now the default `uv init` backend (stable July 2025); zero extra install; picks up `pyproject.toml` naturally |
| `hatchling` | ≥1.27 (fallback only) | Alternative build backend if we need build scripts or vendored C deps | If `uv_build` hits a limitation (e.g., custom C extension for the auth crypto layer), drop to hatchling without changing consumers |

**pyproject layout:**

```toml
[project]
name = "state"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.27.0",
    "litellm>=1.80.0",
    "anthropic>=0.80.0",
    "httpx>=0.28.1",
    "pydantic>=2.13.2",
    "pydantic-settings>=2.7",
    "orjson>=3.11.8",
    "aiosqlite>=0.22.1",
    "filelock>=3.20.3",
    "pluggy>=1.6.0",
    "pygit2>=1.19.2",
    "google-auth>=2.35",
    "google-auth-oauthlib>=1.2",
    "google-genai>=0.9",
    "openai>=1.60",
    "cryptography>=43.0",
    "structlog>=25.1",
    "rich>=13.9",
    "typer>=0.15",
]

[build-system]
requires = ["uv_build>=0.5"]
build-backend = "uv_build"
```

**Installer UX:** `uvx state install` (recommended) or `pipx install state`. Both are
single-command. The installer detects opencode, offers to register the plugin + MCP servers
automatically.

### CLI framework

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `typer` | **≥0.15** | CLI (`state`, `state-build`, `state-teach`) | Type-hint-driven, built on click, plays well with pydantic; matches the "learn Python through types" ethos |
| `rich` | **≥13.9** | Terminal output (tables, progress, tracebacks) | Ubiquitous; Typer uses it; zero config |

**NOT using:** `click` directly (Typer is strictly better for typed CLIs), `argparse`
(learner-hostile), `fire` (magic, surprising).

---

## Development tooling

| Tool | Version floor | Purpose | Why |
|------|---------------|---------|-----|
| `ruff` | **≥0.9.0** | Linter + formatter (replaces Black, isort, flake8, pyupgrade) | 10–100× faster than Black+flake8; 900+ rules; Apache Airflow, FastAPI, pandas, pydantic all use it; one config file |
| `mypy` | **≥1.14** | Type checker | Still the standard; ty (Astral's upcoming checker) not stable enough yet |
| `pre-commit` | ≥4.0 | Git hooks (ruff, mypy, prettier for TS) | Standard |
| `basedpyright` | optional ≥1.27 | Alternative type checker with better inference | Reserved for power debugging; not default |

**NOT using:** Black (ruff format replaces it), isort (ruff replaces it), flake8 (ruff
replaces it), pyright (mypy has better ecosystem docs for a learner).

`pyproject.toml` carries all config — no `.ruff.toml`, `setup.cfg`, `tox.ini` scatter.

---

## Observability

Event replay is load-bearing in both modes. We need logs that join up with events.

| Library | Version floor | Purpose | Why |
|---------|---------------|---------|-----|
| `structlog` | **≥25.1** | Structured logging; every log line is a dict, timestamp + event_id + session_id + slice_id | Structured-native; easy to pipe to JSON for collectors; separates dev-friendly renderer (Rich-styled) from production JSON renderer |
| `rich` | ≥13.9 | Dev-mode log rendering | Already a dep; structlog integrates natively |

**OpenTelemetry: opt-in only, v2 phase.** We ship hooks but do not pin a tracer SDK day-one.
Opencode itself uses `@effect/opentelemetry` heavily (see `opencode/package.json`), and the
daemon can export OTLP traces later without a code rewrite. Adding OTLP now is premature
optimization; Arc-level decision.

| Library (deferred) | Version floor | Purpose |
|--------------------|---------------|---------|
| `opentelemetry-sdk` | ≥1.30 | Tracer SDK (v2 phase) |
| `opentelemetry-exporter-otlp` | ≥1.30 | OTLP exporter (v2 phase) |
| `opentelemetry-instrumentation-httpx` | ≥0.55b | httpx auto-instrumentation (v2 phase) |

**Event replay strategy for forensics:** events are the ground truth. Logs are supplementary.
The event store (`events.sqlite`) + the structured log stream (one JSONL file per daemon
session) together replay any execution. No APM dependency required for forensics.

---

## Version compatibility matrix

| Pair | Constraint | Rationale |
|------|------------|-----------|
| `mcp>=1.27.0` ↔ opencode's `@modelcontextprotocol/sdk` `1.27.1` | Same protocol version (2025-06 revision) | HIGH confidence — both speak current MCP spec |
| `litellm>=1.80.0` ↔ `anthropic>=0.80.0` | litellm uses anthropic SDK internally for some paths; keep both current | Avoid the "litellm requires older anthropic" drift |
| `httpx>=0.28.1` ↔ `anthropic`, `openai`, `google-genai` | All three SDKs accept user-provided httpx client; 0.28+ is their minimum | Shared connection pool |
| `pygit2>=1.19.2` ↔ `libgit2` 1.9.x | Binary wheels bundle libgit2; no system install | Works on macOS/Linux/Windows |
| `pydantic>=2.13.2` ↔ `pydantic-settings>=2.7` | Pydantic v2 APIs only | V1 is frozen |
| `pytest>=8.4.0` ↔ `pytest-asyncio>=1.3.0` | pytest-asyncio 1.3 bumped min pytest to 8.4 | Floor is hard |
| Python 3.12+ ↔ all the above | 3.12 is the minimum per project mandate | No 3.11 back-compat |
| opencode plugin catalog versions | Match opencode root `package.json` catalog **exactly** | Plugin runs inside opencode's runtime; drift causes silent mis-imports |

---

## What NOT to use (with reasons)

| Avoid | Why | Use instead |
|-------|-----|-------------|
| **Prefect / Dask / Airflow** | Data-pipeline engines; wrong shape for human/agent work; heavyweight. Project mandate rejects them | Pure-Python DAG scheduler |
| **LangChain / LangGraph** | Over-engineered; abstraction layers over abstraction layers; moving target | Custom agent loop + litellm |
| **pydantic-ai / smolagents** | Agent frameworks that hide the LLM loop; we want control | Custom loop, ~400 lines |
| **SQLAlchemy / SQLModel / Tortoise ORM** | ORM for append-only event log is negative value | stdlib `sqlite3` + `aiosqlite` |
| **Alembic** | Assumes SQLAlchemy; too heavy for our migration shape | Hand-rolled SQL migrations |
| **GitPython** | Subprocess-based, slow, awkward API | `pygit2` with libgit2 wheels |
| **NetworkX** | Importing a library to use 1% of it; doesn't match our Pydantic node shape | 200 LOC of pure Python scheduler |
| **Textual / Rich Live** (for primary TUI) | We extend opencode's TUI; building our own is waste | opencode TUI plugin (SolidJS + OpenTUI). Textual reserved for standalone utilities only (per PROJECT.md) |
| **FastAPI / uvicorn** (for primary daemon) | Overkill; opencode-plugin + MCP cover all external surfaces; adding an HTTP API is a v2 decision | asyncio Unix socket + JSON-RPC |
| **jiti-style TS-at-runtime loading** | Python imports `.py` natively | `importlib.import_module` |
| **Black, isort, flake8, pyupgrade** | Ruff does all of them 10–100× faster | Ruff (format + lint) |
| **Poetry** | Slower than uv; lockfile format now lagging; second-class build-backend integration | `uv` + `uv_build` |
| **setuptools** (for new greenfield) | Unopinionated; `pyproject.toml`-native alternatives are cleaner | `uv_build` (default) or `hatchling` (fallback) |
| **AnyIO / Trio** as the primary API | asyncio is the ecosystem; no cross-backend need | asyncio directly |
| **fastmcp** (third-party package on PyPI) | Different project from the official `FastMCP` inside `mcp` package; confusing naming | Use `mcp` package's bundled `FastMCP` |
| **tiktoken** | OpenAI-specific; Anthropic/Gemini tokens are different; we let providers count | Provider-reported token usage from litellm responses |

---

## Stack patterns by variant

**If the host is opencode (primary):**
- Use opencode worktree service (HTTP client calls, not pygit2)
- Plugin registers MCP servers programmatically, wires hooks, adds TUI routes
- Daemon talks to opencode server over HTTP (SSE bus subscription)
- `chat.params` + `experimental.chat.system.transform` hooks handle all prompt shaping

**If the host is Claude Code / Gemini CLI / Qwen Code (deprioritized):**
- MCP-only surface. No hook shim, no TUI extension, no bus subscription.
- pygit2 handles worktree lifecycle locally.
- The two MCP servers (`state-build`, `state-teach`) expose the full tool surface.
- `.state/auth.json` first-run import from opencode's `auth.json` if present.

**If standalone (no host):**
- `state` CLI (Typer) drives the daemon directly.
- pygit2 for all git ops.
- No TUI — progress rendered via Rich in the terminal.

---

## Installation

```bash
# Primary install path
uvx state install
# Detects opencode, offers plugin + MCP registration

# Alternative
pipx install state

# Plugin (registered automatically by `state install`, or manually):
#   adds to opencode config:
#     mcp.state-build.command = ["state-build", "mcp"]
#     mcp.state-teach.command = ["state-teach", "mcp"]
#     plugin["@state/opencode-plugin"] — loaded from local clone or npm

# Dev setup
git clone https://github.com/thomas/state
cd state
uv sync                       # Python deps + dev tools
bun install --cwd plugin      # Plugin deps (matches opencode bun-first convention)
uv run pytest                 # Python tests
bun test --cwd plugin         # TS tests
```

---

## Confidence assessment per recommendation

| Recommendation | Confidence | Source quality |
|----------------|------------|----------------|
| Python 3.12+ | HIGH | PROJECT.md mandate |
| asyncio over anyio | HIGH | Ecosystem-wide verified |
| `mcp>=1.27.0` | HIGH | PyPI, GitHub releases; opencode uses 1.27.1 on TS side (same spec) |
| `litellm>=1.80` | HIGH (floor may float) | WebSearch + docs; exact floor reviewed at install time |
| `anthropic>=0.80` escape hatch | HIGH | SDK docs + release notes |
| `pygit2>=1.19.2` | HIGH | Official docs |
| `pluggy>=1.6.0` | HIGH | PyPI + pytest-dev |
| `pydantic>=2.13.2` | HIGH | PyPI + pydantic.dev announcements |
| `orjson>=3.11.8` | HIGH | PyPI + changelog |
| `aiosqlite>=0.22.1` | HIGH | PyPI |
| `filelock>=3.20.3` (CVE floor) | HIGH | CVE-2026-22701 advisory |
| `httpx>=0.28.1` | HIGH | encode/httpx |
| Pure-Python DAG (no networkx) | HIGH | Architectural fit, consistent with PROJECT.md |
| Opencode plugin catalog pins | HIGH | Direct read from opencode's `package.json` |
| `uv` + `uv_build` | HIGH | Astral docs, 2026 consensus |
| `ruff` (replacing Black/isort/flake8) | HIGH | Astral docs, industry adoption |
| `structlog` + deferred OTel | MEDIUM | Common pattern; OTel deferral is an opinion |
| Hand-rolled SQL migrations vs Alembic | MEDIUM | Defensible but biased toward simplicity |

---

## Sources

### Python libraries (version floors and capabilities)

- [MCP Python SDK on PyPI](https://pypi.org/project/mcp/) — 1.27.0, April 2026
- [MCP Python SDK GitHub releases](https://github.com/modelcontextprotocol/python-sdk/releases)
- [LiteLLM Anthropic provider docs](https://docs.litellm.ai/docs/providers/anthropic)
- [LiteLLM prompt caching docs](https://docs.litellm.ai/docs/completion/prompt_caching)
- [LiteLLM reasoning_content / extended thinking](https://docs.litellm.ai/docs/reasoning_content)
- [Anthropic Python SDK on PyPI](https://pypi.org/project/anthropic/)
- [Anthropic SDK GitHub releases](https://github.com/anthropics/anthropic-sdk-python/releases)
- [Anthropic prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [pygit2 1.19.2 docs](https://www.pygit2.org/)
- [pygit2 worktree docs](https://www.pygit2.org/worktree.html)
- [pluggy on PyPI](https://pypi.org/project/pluggy/)
- [aiosqlite on PyPI](https://pypi.org/project/aiosqlite/)
- [Pydantic v2.13 release announcement](https://pydantic.dev/articles/pydantic-v2-12-release)
- [Pydantic on PyPI](https://pypi.org/project/pydantic/)
- [orjson 3.11.8 changelog](https://github.com/ijl/orjson/blob/master/CHANGELOG.md)
- [orjson on PyPI](https://pypi.org/project/orjson/)
- [httpx on PyPI](https://pypi.org/project/httpx/)
- [NetworkX 3.6.1 topological_sort docs](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.topological_sort.html)
- [filelock changelog + CVE-2026-22701 advisory](https://py-filelock.readthedocs.io/en/latest/changelog.html)
- [pytest-asyncio on PyPI](https://pypi.org/project/pytest-asyncio/)
- [Ruff docs](https://docs.astral.sh/ruff/)
- [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/)
- [uv project init](https://docs.astral.sh/uv/concepts/projects/init/)
- [AnyIO why](https://anyio.readthedocs.io/en/stable/why.html)
- [Python.org discussion: adopting anyio/trio patterns into asyncio](https://discuss.python.org/t/adopt-proven-anyio-trio-patterns-natively-into-asyncio-multi-release-roadmap/106067)
- [structlog + OpenTelemetry integration guide](https://www.dash0.com/guides/python-logging-with-structlog)

### Opencode source of truth

- `state-inputs/opencode/package.json` (root) — catalog versions (bun 1.3.13, typescript 5.8.2,
  effect 4.0.0-beta.48, zod 4.1.8, solid-js 1.9.10, @opentui/core and solid 0.1.99, oxlint
  1.60.0, prettier 3.6.2, ulid 3.0.1, remeda 2.26.0, turbo 2.8.13, @tsconfig/node22 22.0.2)
- `state-inputs/opencode/packages/opencode/package.json` — `@modelcontextprotocol/sdk@1.27.1`,
  `@ai-sdk/anthropic@3.0.71`, `@ai-sdk/openai@3.0.53`, `@ai-sdk/google@3.0.63`, full provider
  matrix
- `state-inputs/opencode/packages/plugin/package.json` — plugin peer deps, devDeps,
  `"build": "tsc"`, `"typecheck": "tsgo --noEmit"`, ESM module type
- `state-inputs/opencode/packages/plugin/src/index.ts` — `Hooks` interface (the 14 hook types
  we wire)
- `state-inputs/opencode/packages/plugin/src/tui.ts` — `TuiPluginApi` surface (slots, routes,
  dialogs, commands, keybinds)
- `state-inputs/opencode-extension-surface.md` — full extension map
- `state-inputs/opencode-integration-analysis.md` — integration ROI tiers
- [@opencode-ai/plugin gist by rstacruz](https://gist.github.com/rstacruz/946d02757525c9a0f49b25e316fbe715) — plugin dev conventions
- [OpenTUI](https://github.com/anomalyco/opentui) — bun-first terminal UI core

### Project mandate

- `/Users/tmac/Projects/state/.planning/PROJECT.md` — cardinal rules, library locks,
  rejected alternatives
- `/Users/tmac/Projects/state/state-inputs/gsd-2pi-codebase-analysis/10-python-rebuild-mapping.md`
- `/Users/tmac/Projects/state/state-inputs/gsd-2pi-codebase-analysis/11-architecture-discussion.md`

---

*Stack research for: `state` — Python 3.12+ agentic state-machine workflow engine, extending
opencode, portable via MCP to Claude Code / Gemini CLI / Qwen Code.*
*Researched: 2026-04-22*
