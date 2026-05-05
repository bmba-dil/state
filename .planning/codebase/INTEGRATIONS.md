# External Integrations

**Analysis Date:** 2026-05-05

## APIs & External Services

### AI Provider Inference

**Anthropic (Claude):**
- OAuth stealth flow — Claude Code identity mimicking for Pro/Max subscription-priced inference
  - SDK/Client: `anthropic>=0.80.0` (direct SDK, `src/state_core/providers/anthropic_client.py`)
  - Auth: POST to `https://platform.claude.com/v1/oauth/token`; refresh via same endpoint
  - Stealth headers: byte-for-byte match against `state-inputs/claude-oauth.md` (`src/state_core/auth/providers/anthropic.py` lines 95-136)
  - OAuth NEVER routes through litellm (direct SDK escape hatch only)
  - Support for extended thinking (PRV-08) and fine-grained cache-control (PRV-09) — features litellm does not support
- API Key — Direct console keys via `x-api-key` header
  - SDK/Client: `anthropic>=0.80.0` (same SDK)
  - Auth header: `x-api-key: <key>`, prefix: `sk-ant-api03-`
  - Env var: `ANTHROPIC_API_KEY`

**Google Gemini (Gemini CLI OAuth):**
- Desktop-App OAuth pattern (RFC 8252) for free-tier Gemini inference
  - SDK/Client: Custom httpx calls to `cloudcode-pa.googleapis.com` (no SDK client for auth)
  - Auth: POST to `https://oauth2.googleapis.com/token`; refresh via same endpoint
  - Loopback callback on dynamic port (PKCE + state validation)
  - Env var: Not applicable (OAuth, not api key)
  - Client ID: `681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com` (public distributed-app credential)
  - `src/state_core/auth/providers/google_gemini.py`

**Google Antigravity (Cloud Code Assist Companion):**
- Third-party OAuth for Cloud Code Assist API (unified gateway for Gemini 3 + Claude Opus + GPT-OSS)
  - SDK/Client: Custom httpx calls to `cloudcode-pa.googleapis.com/v1internal`
  - Auth: POST to `https://oauth2.googleapis.com/token`
  - FIXED port 51121, literal `localhost` redirect_uri
  - 4 outbound headers: Bearer, User-Agent, X-Goog-Api-Client, Client-Metadata
  - ⚠️ Terms-of-Service risk noted in `src/state_core/auth/providers/antigravity.py` line 10-14
  - `src/state_core/auth/providers/antigravity.py`

**GitHub Copilot:**
- Device-code OAuth flow (RFC 8628) — two-tier token architecture
  - SDK/Client: Custom httpx calls to `api.githubcopilot.com`
  - Auth: Device code from `https://github.com/login/device`; tokens from `https://github.com/login/oauth/access_token`
  - Session token mint: `copilot_internal/v2/token` (tid_* short-lived ~30 min)
  - OAuth token (gho_*): long-lived, no expiry
  - Client ID: `Iv1.b507a08c87ecfe98` (legacy OAuth App — plaintext per P1-3)
  - No client secret (device-code flow is for public clients)
  - Polling with time.monotonic() deadline math
  - `src/state_core/auth/providers/github_copilot.py`

**12 Plain API Key Providers:**
- All managed via `src/state_core/auth/providers/api_key.py` with a single `PlainApiKeyAuth` class parameterized by `ApiKeyProviderSpec`
- Registry (12 rows, captured 2026-04-30) at `api_key.py` lines 140-258:

| Provider ID | Auth Header | Prefix | Env Var |
|---|---|---|---|
| `anthropic.api_key` | `x-api-key: {key}` | `sk-ant-api03-` | `ANTHROPIC_API_KEY` |
| `openrouter` | `Authorization: Bearer {key}` | `sk-or-v1-`, `sk-or-` | `OPENROUTER_API_KEY` |
| `openai` | `Authorization: Bearer {key}` | `sk-svcacct-`, `sk-proj-`, `sk-None-`, `sk-` | `OPENAI_API_KEY` |
| `anyscale` | `Authorization: Bearer {key}` | `esecret_` | `ANYSCALE_API_KEY` |
| `xai` | `Authorization: Bearer {key}` | `xai-` | `XAI_API_KEY` |
| `groq` | `Authorization: Bearer {key}` | `gsk_` | `GROQ_API_KEY` |
| `google.ai_studio` | `x-goog-api-key: {key}` | (none) | `GEMINI_API_KEY` |
| `deepseek` | `Authorization: Bearer {key}` | (none) | `DEEPSEEK_API_KEY` |
| `together` | `Authorization: Bearer {key}` | (none) | `TOGETHER_API_KEY` |
| `mistral` | `Authorization: Bearer {key}` | (none) | `MISTRAL_API_KEY` |
| `cohere` | `Authorization: Bearer {key}` | (none) | `COHERE_API_KEY` |
| `cerebras` | `Authorization: Bearer {key}` | (none) | `CEREBRAS_API_KEY` |

**Provider Routing:**
- `litellm>=1.80.0` — Abstracts 12+ providers through unified interface (`src/state_core/providers/litellm_client.py`)
- `ProviderRouter` (`src/state_core/providers/router.py`) — type-based routing guard:
  - `OAuthCredential` (sk-ant-oat* tokens) → `AnthropicClient` (direct SDK, stealth headers)
  - All other credential types → `LitellmClient` (litellm abstraction)
- Shared `httpx.AsyncClient` from `src/state_core/http_client.py` for daemon-level connection pooling (100 max connections, 20 keepalive, 30s expiry)

### Opencode Integration

**SyncEvent Mirror (`src/state_core/sync_mirror.py`):**
- POSTs committed events to `{opencode_url}/sync/replay` as fire-and-forget
- 2-attempt retry with 10s timeout; failed events remain `synced_to_opencode = 0` for Phase 006 reconciliation
- Uses own `httpx.AsyncClient` instance (not the shared daemon client)

**Worktree API (`src/state_core/opencode_worktree.py`):**
- Preferred worktree path (WRK-02). Falls back to pygit2 when opencode unreachable
- Endpoints: `POST /worktree` (create), `GET /worktree` (list), `DELETE /worktree/{name}` (remove), `POST /worktree/{name}/reset` (reset)

**Hook Endpoints (`src/state_daemon/hooks.py`):**
- POST `/hook/chat-params` — model profile resolution from opencode plugin shim
- Registered via `DaemonServer.add_get_handler()` extensible GET route system

**Config Resolution (`src/state_core/config.py`):**
- Discovers opencode from `opencode.json` or `.opencode/opencode.json` walking up from CWD
- Default: `http://127.0.0.1:17495` (opencode default)
- Override: `STATE_OPENCODE_URL` env var

## Data Storage

**Databases:**
- SQLite via `aiosqlite>=0.22.1` — `src/state_core/database.py`
  - Connection: `STATE_DB_PATH` env var or `.state/events.sqlite` (default)
  - Client: `aiosqlite` with row_factory + async context manager
  - Config: WAL journal mode + `synchronous=FULL` (fsync on every commit — crash-safe)
  - File: `.state/events.sqlite` (committed, project-relative)
- No ORM — raw SQL with `aiosqlite.execute()`. Schema managed by hand-rolled migration system (`src/state_core/migrations.py`)

**File Storage:**
- Local filesystem only — `.state/` on-disk tree:
  - `.state/auth.json` — Auth vault (chmod 0600 enforced, `src/state_core/auth/store.py`)
  - `.state/events.sqlite` — Event store database
  - `.state/daemon.sock` — Daemon socket path marker (for worker/CLI discovery)
  - `.state/fixtures/` — Golden verification DBs (allowlisted in `.gitignore`)

**Caching:**
- None — No Redis, Memcached, or in-memory cache layer detected

## Authentication & Identity

**Auth Methods (5 total):**

| Method | Provider ID | Flow | Implementation |
|---|---|---|---|
| Anthropic OAuth (stealth) | `anthropic` | PKCE + manual paste | `src/state_core/auth/providers/anthropic.py` |
| Google Gemini OAuth | `google.gemini_cli` | PKCE + loopback redirect | `src/state_core/auth/providers/google_gemini.py` |
| Google Antigravity OAuth | `google.antigravity` | PKCE + loopback (fixed port 51121) | `src/state_core/auth/providers/antigravity.py` |
| GitHub Copilot | `github.copilot` | Device-code (RFC 8628) + two-tier token | `src/state_core/auth/providers/github_copilot.py` |
| Plain API Key (12 providers) | `{provider_id}.api_key` | Interactive getpass/stdin | `src/state_core/auth/providers/api_key.py` |

**Auth Vault (`src/state_core/auth/store.py`):**
- Location: `.state/auth.json` (override via `STATE_AUTH_JSON`)
- Mode: chmod 0600 enforced on every read AND write
- Atomic writes: tmp file + `os.replace` (same-fs, POSIX atomic), `os.fsync` before rename
- Symlink attacks: closed (T-018-9) — `O_NOFOLLOW` on open, `os.lstat` checks on vault path and parent dir
- Schema: `AuthVault` Pydantic model with `providers: dict[str, list[Credential]]` (always list, even n=1)
- Round-robin rotation index: `last_rotation: dict[str, int]`
- Serialization: `orjson` with `OPT_SORT_KEYS | OPT_INDENT_2`

**Secret Hygiene:**
- Layer 1: `Field(repr=False)` on all secret-bearing Pydantic fields (`src/state_core/auth/base.py`)
- Layer 2: `redact_processor` — structlog processor at position 0, redacting 12 token prefixes + secret-key-name values (`src/state_core/observability/redactor.py`)
- Layer 2 also covers stdlib loggers (httpx, litellm, pygit2, aiosqlite) via `ProcessorFormatter.foreign_pre_chain`

## Monitoring & Observability

**Error Tracking:**
- None — No Sentry, Datadog, or third-party error tracking detected
- Errors surfaced through structlog JSON logging with stack traces

**Logs:**
- structlog >= 25.1 with unified processor chain:
  - Position 0: `redact_processor` (token redaction)
  - Subsequent: `merge_contextvars`, `add_log_level`, `TimeStamper(iso, utc)`, `StackInfoRenderer`, `format_exc_info`
  - Rendered as JSON via `structlog.processors.JSONRenderer()`
- Stdlib loggers routed through same chain (`ProcessorFormatter`)
- Redactor attachment verified at daemon startup via canary self-check (`assert_redactor_attached()`)

**Event Broadcasting:**
- SSE (Server-Sent Events) bus for real-time event streaming:
  - `GET /events/subscribe?mode=build&from=01XYZ` endpoint (`src/state_daemon/sse.py`)
  - Multi-client fan-out with mode filtering and ULID offset
  - 30s heartbeat to prevent proxy/load-balancer timeouts
  - Connected workers consume events via SSE for hot-session state

## CI/CD & Deployment

**Hosting:**
- Local-first — daemon runs as user service (launchd on macOS, systemd --user on Linux)
- No container orchestration detected (no Dockerfile, no docker-compose, no Kubernetes manifests)

**CI Pipeline:**
- Not detected — No `.github/workflows/`, `.gitlab-ci.yml`, or CI config files found

**Version Control:**
- git repository with `.gitignore` covering Python artifacts, IDE files, OS files, testing artifacts

## Environment Configuration

**Required env vars (runtime):**
- None strictly required — all have sensible defaults:
  - `STATE_OPENCODE_URL` — defaults to `http://127.0.0.1:17495`
  - `STATE_DB_PATH` — defaults to `.state/events.sqlite`
  - `STATE_AUTH_JSON` — defaults to `.state/auth.json`

**Optional env vars:**
- `STATE_HTTP_PROXY` — proxy for provider inference traffic
- `STATE_CA_BUNDLE` — custom CA certificate path
- `STATE_TLS_VERIFY` — set "false" to disable TLS verification (dev/test only)

**Secrets location:**
- API keys and OAuth tokens stored in `.state/auth.json` (chmod 0600, committed — but project `.gitignore` only excludes `.state/*`, allowing `.state/fixtures/`)
- No `.env` files detected
- Provider env vars (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) read by auth providers but NOT by the vault itself

**Config files:**
- `pyproject.toml` — Build, linting, testing, mypy configuration
- `.pre-commit-config.yaml` — Pre-commit hooks (ruff, mypy, whitespace checks)
- `.planning/config.json` — GSD workflow configuration

## Webhooks & Callbacks

**Incoming:**
- Loopback OAuth callback: `http://127.0.0.1:{port}/oauth2callback` — Used by Gemini CLI (dynamic port) and Antigravity (fixed port 51121) for OAuth redirect capture. Handled by `src/state_core/auth/oauth_common/loopback.py`

**Outgoing:**
- Opencode SyncEvent: `POST {opencode_url}/sync/replay` — Fire-and-forget event mirror
- Opencode Worktree API: `POST/GET/DELETE {opencode_url}/worktree/...` — Worktree lifecycle
- Opencode Hook Endpoints: `POST {opencode_url}/hook/chat-params` — Model profile resolution

## Daemon Communication Protocol

**Internal:**
- Unix domain socket — HTTP/1.1 with JSON-RPC 2.0 (`src/state_daemon/router.py`)
- SSE event streaming over HTTP (`/events/subscribe`)
- Socket path: `{runtime_dir}/state-{sha256(project_root)[:16]}.sock` (platform-aware)
- Socket marker: `.state/daemon.sock` (atomically written, for worker/CLI discovery)
- Socket mode: chmod 0600

---

*Integration audit: 2026-05-05*
