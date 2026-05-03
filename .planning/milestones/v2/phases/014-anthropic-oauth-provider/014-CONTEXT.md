# Phase 014: Anthropic OAuth provider (stealth flow) - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning
**Mode:** Interactive discuss (overrode workflow.skip_discuss for security-critical phase)

<domain>
## Phase Boundary

First concrete `AuthMethod` implementation for `state_core.auth.providers.anthropic` — PKCE + Authorization-Code login (manual `code#state` paste, no callback server), refresh, and the byte-for-byte stealth headers required to unlock Anthropic Pro/Max subscription-priced inference instead of API-key pricing.

Owns:
- `src/state_core/auth/providers/anthropic.py`
- `src/state_core/auth/oauth_common/pkce.py` (extracted SHARED module — phases 015/016/017 import it)
- `.state-inputs/references/milady/{claude-code-stealth.mjs,milady-refresh-oauth.sh,NOTICE.md}` (reference snapshot)

Requirement: AUTH-01.
P0 pitfalls owned: P0-1 (user-agent), P0-2 (anthropic-beta), P0-3 (x-app), P0-4 (Bearer not x-api-key), P0-5 (client_id), P0-7 (5-min buffer applied at AuthMethod.is_expired layer per Phase 011 Pattern 3), P0-8 (PKCE state=verifier).

Out of scope (deferred to other phases):
- Polished `state auth login` Typer CLI — Phase 022
- AUTH-13 captured-header golden-file regression test — Phase 022
- Multi-cred round-robin selection — Phase 019
- Structlog token redactor — Phase 020 (this phase relies on `Field(repr=False)` only)
- First-run import from `~/.claude/.credentials.json` — Phase 021
- Inference-call routing through stealth headers — v3 provider routing
- Daemon-level proactive refresh timer — v4+ scheduler

</domain>

<decisions>
## Implementation Decisions

### Module layout & PKCE sharing
- **Single file:** `src/state_core/auth/providers/anthropic.py` (~250 LOC mirroring milady's `claude-code-stealth.mjs` shape and easy to byte-diff against `.state-inputs/claude-oauth.md`).
- **Shared PKCE extracted NOW:** `src/state_core/auth/oauth_common/pkce.py` — stdlib only (`secrets`, `hashlib.sha256`, `base64.urlsafe_b64encode`), ~30 LOC. Lands in Phase 014 because phases 015/016/017 are parallel-safe and would otherwise either copy PKCE or block on a mid-milestone refactor.
- **Client_id** lives as a module-level constant in `anthropic.py`: `_CLIENT_ID = base64.b64decode("…").decode()` evaluated at module load (matches spec's "base64-decoded at runtime").
- **Token response** is a Pydantic `AnthropicTokenResponse(BaseModel)` with `extra="ignore"` (NOT `forbid`) so Anthropic can add fields without breaking us. Parses `access_token`, `refresh_token`, `expires_in`, optional `account.uuid`, optional `account.email_address`.

### Login UX surface (Phase 014 only — polished CLI is Phase 022)
- **Two entry points:**
  1. `async def login() -> OAuthCredential` — programmatic / test
  2. `python -m state_core.auth.providers.anthropic login` — interactive paste flow for dev-time smoke-testing stealth against real Anthropic before Phases 015–022 land.
- **Paste flow:** print authorize URL → instruct user to open in browser → single-prompt paste of `code#state` using `getpass.getpass("Paste code#state: ")` (hidden input — treats short-lived auth code as a secret in transit).
- **Existing-cred behavior:** `login()` ALWAYS issues a new credential and the store appends it (preserves array-per-provider shape required by AUTH-08 / Phase 019).
- **`account_id` handling:** parsed from token-response `account.uuid`, stored in `OAuthCredential.account_id`, printed to stdout as `Logged in as <email_address or uuid>` for multi-cred disambiguation.

### Stealth headers — source of truth & version drift
- **Storage:** module-level constants in `anthropic.py`. Single source of truth; Phase 022's golden-file test imports them and diff-checks captured outbound traffic.
- **Pinned values** (sourced from milady-ai/milady#1910 + cross-verified against our own mitmproxy capture before merge):
  ```
  _CLAUDE_CLI_VERSION = "2.1.92"
  _USER_AGENT = f"claude-cli/{_CLAUDE_CLI_VERSION} (external, cli)"
  _X_APP = "cli"
  _ANTHROPIC_BETA = (
      "claude-code-20250219,oauth-2025-04-20,"
      "interleaved-thinking-2025-05-14,"
      "context-management-2025-06-27,"
      "prompt-caching-scope-2026-01-05,"
      "advanced-tool-use-2025-11-20,"
      "effort-2025-11-24"
  )
  ```
  Each constant carries a `# captured 2026-04 from milady-ai/milady#1910 against claude-cli 2.1.92` comment.
- **Validation gate:** before merging Phase 014, run a one-shot mitmproxy capture against a real Claude Code session and diff the captured headers against the constants above. Both `(external, cli)` parenthetical and the full beta list MUST match captured traffic.
- **Drift detection:** belongs to Phase 022 (golden-file test) + a deferred future phase that automates traffic capture (see Deferred Ideas).
- **Other headers:** pin only the four stealth headers. Accept / Accept-Encoding / Connection use httpx defaults.
- **Body shape mutation:** Phase 014 SHIPS a stealth body-mutation helper:
  ```python
  def inject_stealth_system_prefix(body: dict) -> dict
  ```
  Prepends `{"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}` to `body["system"]` if not already present (mirrors milady logic: handle list / string / missing forms). Reverses earlier "headers-only" assumption — milady evidence shows body matters.
- **URL hardening:** add `?beta=true` query param to outbound stealth requests when not present.
- **Defensive header cleanup:** explicitly `headers.pop("x-api-key", None)` before setting Bearer, so a stray upstream caller can't downgrade to API-key pricing (P0-4 in disguise).

### HTTP client lifecycle & error semantics
- **Per-call `httpx.AsyncClient`** inside `login()` and `refresh()` (`async with httpx.AsyncClient(...) as c:`). No module-level singleton — auth calls are infrequent, pooling has near-zero benefit, and avoiding a singleton dodges shutdown choreography + test-isolation pain. Inference-call pooling is a v3 (provider routing) concern.
- **Timeout:** `httpx.Timeout(10.0, connect=5.0)` per call. Aligns with Phase 013's 10s filelock acquire so refresh attempts can't outlive their lock budget.
- **Retry policy:** none. Phase 013 already runs refresh inside a 10s-budgeted filelock; retries inside the provider would consume that budget. Failures bubble; the next caller naturally retries. No `tenacity` dependency.
- **Exception hierarchy:**
  ```python
  class AuthError(Exception): ...
  class AuthLoginError(AuthError): ...        # token exchange failed
  class AuthRefreshError(AuthError): ...      # refresh failed (invalid_grant, network)
  class StealthRejected(AuthError): ...       # 401/403 with stealth-shape signal — header drift suspected
  ```
  All live in `state_core.auth.providers.anthropic` (or a thin `state_core.auth.errors` module if 015–017 want to share — Claude's discretion at planning time).

### Test strategy (Phase 014, in-CI)
- **`pytest-httpx` mock + header-shape assertions** — hermetic, fast, no creds. Asserts every outbound request carries:
  - `Authorization: Bearer sk-ant-oat<fixture>`
  - `user-agent: claude-cli/2.1.92 (external, cli)` (exact)
  - `x-app: cli` (exact)
  - `anthropic-beta: <full pinned string>` (exact)
  - `?beta=true` in URL when not pre-set
  - Body has `system` array with the Claude-Code prefix at index 0 when invoking inference-shape requests
  - `x-api-key` is NOT present
- Live-against-real-Anthropic test is OUT of CI; reserved for the Phase 022 captured-header golden test + manual pre-release smoke.

### Claude's Discretion
- Exact ordering of `headers.set()` calls
- Whether `errors.py` is split into its own module or kept inline (planner decides based on 015–017 sharing needs)
- Internal helper naming (e.g., `_build_authorize_url`, `_exchange_code`)
- structlog event naming for login/refresh observability (constrained only by Phase 020's redactor expectations)
- Test fixture values for fake `sk-ant-oat*` tokens

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `state_core.auth.OAuthCredential` (Phase 011) — exact target shape; `expires` stays wire-shape, buffer applied here in `is_expired`.
- `state_core.auth.AuthMethod` Protocol (Phase 011) — provider conforms structurally; `@runtime_checkable` for plugin discovery, but pair with mypy strict.
- `state_core.auth.refresh_credential` (Phase 013) — provider's `refresh()` runs INSIDE this filelock; provider does NOT acquire its own lock.
- `state_core.auth.is_expired_buffered` (Phase 013) — 5-min buffer math lives there; provider's `is_expired` delegates.
- `state_core.auth.AuthVault` / `load_vault` / `save_vault` (Phase 012) — login() return is fed to vault by the caller, NOT by the provider.

### Established Patterns
- **Determinism:** no `time.time()` / `datetime.now()` reads inside provider methods. `is_expired(cred, now: float)` takes `now` as a parameter (Phase 011 cardinal rule).
- **Frozen models:** `cred.model_copy(update={...})` to swap tokens — never mutate.
- **Secret hygiene:** every secret field uses `Field(repr=False)` (Phase 011); structlog redactor (Phase 020) is the second layer.
- **Mode isolation:** `state_core.auth.*` imports stdlib + pydantic + httpx + filelock only. No `state.build.*` / `state.teach.*` imports (BASE-08 enforced).

### Integration Points
- `state_core.auth.providers.anthropic.AnthropicAuth` is the new module (NOT re-exported from `state_core.auth/__init__.py` per existing comment "Provider modules under state_core.auth.providers/ are intentionally NOT re-exported — they are accessed via the dispatcher in Phase 014").
- Phase 014 may also need to introduce the dispatcher hook referenced by that comment (planner decides whether to scope it in 014 or defer to a separate phase).
- `state_core.auth.oauth_common/pkce.py` is NEW — created in 014 for use by 015/016/017.

### Reference snapshots (under `.state-inputs/references/milady/`)
- `claude-code-stealth.mjs` (124 LOC, MIT) — the milady Bun preload module that finalised our beta string, user-agent parenthetical, system-prefix injection, `?beta=true`, and `x-api-key` defensive deletion.
- `milady-refresh-oauth.sh` (48 LOC, MIT) — operational refresh pattern (60-min proactive timer); informs the deferred daemon-level scheduler, NOT this phase.
- `NOTICE.md` — MIT attribution + commit SHA + capture date.

</code_context>

<specifics>
## Specific Ideas

- "We need to use the same 'secure secret input' thing that CLIs have for pasting keys in" — `getpass.getpass()` for the `code#state` paste step.
- "Capture from real Claude Code traffic to settle [the user-agent parenthetical]" — mitmproxy capture is a hard pre-merge gate, not just a recommendation.
- "Pin milady's string + run our own mitmproxy capture as cross-check" — milady is the seed; our own capture is the verification.
- "Add stealth body-mutation helper, ship it" — body-shape mutation (system-prefix injection) is in scope for Phase 014, reversing earlier "headers-only" framing.
- All four `Recommended` choices on HTTP client lifecycle accepted as-is.

</specifics>

<deferred>
## Deferred Ideas

- **Traffic-capture / drift-detection capability** — automated pipeline that observes real Claude Code traffic and extracts updated headers, client_ids, beta flags, system prefixes, etc. Surfaces drift between `state` and live Claude Code. User explicitly noted this could be its own phase (likely v2.5 or a v3 milestone phase). Out of scope for 014.
- **Daemon-level proactive refresh timer** — milady's 60-min proactive refresh on a systemd timer. Different layer from our 5-min in-flight buffer (AUTH-09): keeps refresh-tokens rolling during idle periods. Belongs to v4+ scheduler / always-on daemon work.
- **`expiresAt`-in-milliseconds conversion** — Claude Code's `~/.claude/.credentials.json` stores `expiresAt` in milliseconds; our `OAuthCredential.expires` is epoch seconds. Phase 021 (first-run import) will need to convert. Captured here so 021 doesn't relearn it.
- **Browser auto-open** — `webbrowser.open(authorize_url)` before the paste prompt. Friendlier UX but fails silently in headless/SSH contexts. Defer to Phase 022 with `--no-browser` flag.
- **Token-validation health-check at login** — call a cheap Anthropic endpoint right after token exchange to confirm stealth works before persisting. Defer to Phase 022 (CLI surface owns user-facing UX).
- **Live-against-real-Anthropic CI test** — gated by `STATE_TEST_LIVE_ANTHROPIC=1`. Defer to Phase 022 release-smoke pipeline.
- **`oauth_common/` extras (shared http client factory, shared error base)** — extract iff 015/016/017 actually want them. Don't over-design before 015 lands.
- **Pulling the full milady repo as a submodule** — rejected: 733MB of unrelated bot code, no Gemini/Antigravity/Copilot OAuth implementations to gain. Snapshotted only the two relevant files.

</deferred>

---

*Phase: 014-anthropic-oauth-provider*
*Context gathered: 2026-04-28*
