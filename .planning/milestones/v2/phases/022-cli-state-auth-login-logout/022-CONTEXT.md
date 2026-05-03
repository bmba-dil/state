# Phase 022: `state auth login | logout | status` CLI + AUTH-13 Captured-Header Goldens — Context

**Gathered:** 2026-05-01
**Status:** Ready for planning
**Mode:** Interactive discuss (4 areas, 16 questions)

<domain>
## Phase Boundary

Public-facing **standalone Typer/Rich CLI** surface for credential management — `state auth login <provider>`, `state auth logout <provider>`, `state auth status` — sitting on top of the auth primitives already implemented in Phases 011–021, plus the AUTH-13 captured-header golden-file regression suite covering P0-1..P0-8 + P0-13.

Owns:
- `src/state_cli/auth.py` (or equivalent placement under the existing `state_cli` package — the Typer sub-app `state auth ...` registered into `app` from `src/state_cli/main.py:14`).
- `src/state_core/auth/cli_ops.py` (or equivalent): a thin reusable ops layer that the Typer commands call. Exists so a future opencode-plugin TUI modal can import the same primitives without duplicating logic.
- `tests/auth/golden/<provider>/<flow>.json` golden fixtures.
- `tests/auth/test_p0_regression.py` (one named test per P0 pitfall).

Requirements: AUTH-12 (login/logout/status CLI), AUTH-13 (captured-header golden-file regression).

Does NOT own:
- New auth methods or modifications to existing OAuth/API-key flows (014–018 are locked).
- The opencode-plugin TUI modal surface (provider picker / secure key entry / live model switch) — that lives in `@state/opencode-plugin`, a future phase. Phase 022's reusable ops layer is the seam it will plug into.
- Daemon HTTP/JSONRPC API for auth (does not exist yet; v3+).
- `state auth import-opencode --force`, `state auth prune --expired`, auto-import opt-out flag — explicitly **deferred** (see `<deferred>`); 022 ships the trio only.
- Provider routing through stealth headers at inference call time (v3).
- Daemon-level proactive refresh timer (v4+).
- Windows path / mode handling beyond the Phase 012 warn-and-skip pattern.

P0 pitfalls covered (defense replay, not new defense): P0-1, P0-2, P0-3, P0-4, P0-5, P0-6, P0-7, P0-8, P0-13.

</domain>

<decisions>
## Implementation Decisions

### CLI surface & verbs

- **Trio only.** `state auth login`, `state auth logout`, `state auth status`. No `prune`, no `refresh`, no `list`, no `import-opencode --force` in 022. Phase 021's deferrals stay deferred — they belong in a follow-up phase that can be planned independently once 022 lands.
- **Provider as positional arg, prompts when omitted.** `state auth login anthropic` is the canonical form. `state auth login` (no arg) opens an interactive picker (numbered list of the 16 providers + status). The CLI is treated as the **secondary** surface — the future TUI modal in `@state/opencode-plugin` is where the polished day-to-day UX will live; CLI ergonomics optimize for admin/scripting/first-run/escape-hatch use, not for being "the" UI.
- **Standalone CLI, filelock-coordinated.** Typer commands import `state_core.auth.*` directly and run in-process. No daemon HTTP dependency. Phase 013's filelock already serialises auth.json writers (CLI vs daemon refresh worker). The CLI works whether the daemon is running or not — important for first-run / install-time UX.
- **Provider name normalization via alias table.** A small dict in the CLI module: `{"claude": "anthropic", "gemini": "google.gemini", "antigravity": "google.antigravity", "copilot": "github.copilot", ...}`. Lowercase before lookup. Canonical IDs come from Phase 018's `_REGISTRY` (12 API-key providers) ∪ the 4 OAuth provider IDs from 014–017. Unknown name → exit 64 with a `did-you-mean` suggestion via `difflib.get_close_matches`.
- **Architectural seam: Typer commands are thin shells over `state_core.auth.cli_ops` (placement TBD).** The ops module exposes `login(provider_id, *, account_id=None, api_key=None, code_state=None, from_stdin=False) -> OAuthCredential | ApiKeyCredential`, `logout(provider_id, *, account_id=None, all_=False) -> int`, `status(*, provider_id=None) -> StatusReport`. The future opencode-plugin TUI modal will import the same module — no logic in Typer command bodies beyond argument parsing and rendering.

### Login UX

- **Per-provider flows are inherited as-is from existing implementations.** Phase 022 wraps but does not redesign:
  - **Anthropic** — print authorize URL, `getpass.getpass("Paste code#state: ")`, exchange (mirrors `providers/anthropic.py:705` smoke surface).
  - **Google Gemini** — loopback flow on the shared `oauth_common.loopback` module from Phase 015.
  - **Antigravity** — fixed-port (51121) loopback, same shared module.
  - **GitHub Copilot** — device-code with countdown loop (re-uses `_PollingState` from Phase 017).
  - **API keys (12 providers)** — single `getpass` prompt with prefix validation against `iter_known_prefixes()` from Phase 018.
- **Non-TTY login refuses.** When `not sys.stdin.isatty()` AND no non-interactive flag was supplied, exit 64 with: `error: refusing interactive login on non-TTY. Use --api-key/--code-state/--from-stdin or pipe data into stdin.` Prevents silent CI hangs. Detection happens before any provider code runs.
- **Non-interactive flags:**
  - `--api-key <value>` (api-key providers only). Validates against `iter_known_prefixes()`.
  - `--code-state <code#state>` (Anthropic only — exchanges directly, no browser step).
  - `--from-stdin` (provider-aware: reads api-key, or full `code#state`, or device-code answer from a single stdin line). For piping (`echo $KEY | state auth login anthropic --from-stdin`).
  - Loopback / device-code flows do not have a meaningful non-interactive form in 022 — they always require a browser/auth-server interaction, so non-TTY refusal applies.
- **Existing-cred behavior:** matches Phase 014's contract — `login()` ALWAYS issues a new credential and the store appends it to the array. CLI does not "replace"; rotation is Phase 019's job.
- **Success message:** `Logged in to <provider>: <account_label>` where `account_label = extras["email_address"] or account_id or f"{prefix12}…"`. Phase 020 redactor still applies as defense in depth.

### Logout UX

- **Single-cred case:** if `len(providers[pid]) == 1`, prompt `Remove the only <provider> credential (<account_label>)? [y/N]` and act, or skip the prompt with `--yes`. With `--yes` and no cred present, exit 0 silently (idempotent).
- **Multi-cred case:** if `len(providers[pid]) > 1`, print an indexed list (`[0] account_label1 (source: vault, expires 4h12m)` …) and prompt for which to remove. Non-interactive without `--account` or `--all` is a hard error (exit 64).
- **`--account <id>` flag:** matches against `account_id` first, then `extras["email_address"]`, then the first-12 access-prefix (Phase 021's identity model). Ambiguous matches print candidates and exit 64.
- **`--all` flag:** wipes the entire `providers[pid]` array. Requires `--yes` or interactive confirmation.
- **No soft-delete.** Logout rewrites the array to exclude the removed cred(s); no "disabled" state. Re-add via `login` later if needed.
- **Audit:** emit `auth.logged_out` domain event into `.state/events.sqlite` (dual-write to SyncEvent per the v1 cardinal rule) per credential removed. Payload: `{provider_id, cred_kind, source, account_label}`. NEVER includes any secret bytes.

### `status` output schema

- **Row model: one row per credential.** Phase 019's multi-cred reality stays visible (3 anthropic creds = 3 rows). Aggregated counts appear in a footer line: `16 providers configured · 23 credentials · 2 expired · 1 unknown-provider`.
- **Default columns (5, fits 80-col terminals):** `provider | type | account | expires | source`.
  - `type` ∈ `{oauth, api_key}`.
  - `account` = `email_address` > `account_id` > `prefix12…` fallback.
  - `expires` = `valid 4h12m` / `EXPIRED` / `—` (api_key has no expiry concept).
  - `source` = `vault` / `opencode-import` (from `extras["_source"]`, Phase 021) / `env` (Phase 018 ephemeral synthesis).
- **Masking:** **never show token bytes by default.** No prefix, no count, no truncation — the surface is account-label + expires + source. `--show-prefix` is an opt-in flag that reveals the first-12 chars (matches Phase 021's identity prefix). Phase 020 redactor is the second defense layer; the contract here is to not emit secret material in the first place.
- **`--json` envelope (versioned):**
  ```json
  {
    "schema": "state.auth.status/v1",
    "providers": [
      {
        "id": "anthropic",
        "creds": [
          {
            "type": "oauth",
            "account_id": "…",
            "account_label": "user@example.com",
            "expires_at": 1751234567.0,
            "expires_in_seconds": 14520,
            "source": "opencode-import",
            "prefix12": "sk-ant-oat0"
          }
        ]
      }
    ]
  }
  ```
  Stable contract. Future TUI modal phase consumes this. `prefix12` is included in `--json` (machine-readable) but not in default human output (visual).
- **Filtering & sorting (Claude's discretion in planning):** `--provider <id>`, `--expired`. Sort default: providers alphabetical; within a provider, vault entries first, then opencode-import, then env-synthesized; within source, by `expires_at` ascending (soonest-to-expire first).
- **Renderer:** Rich `Table` for human output, `orjson` for `--json`. `--no-color` respected.

### Exit-code policy (uniform across all three commands)

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Generic `AuthError` (login or refresh failed) |
| `2` | Typer's default "unknown subcommand" / argparse failure |
| `3` | `StealthRejected` (signals header drift to CI — distinct from generic auth failure) |
| `64` | `EX_USAGE`: unknown provider, missing required arg, ambiguous `--account`, non-TTY without flag |
| `77` | `EX_NOPERM`: `AuthVaultPermissionError` (chmod-0600 violation, P0-13) |
| `78` | `EX_CONFIG`: registry / loader configuration mismatch |
| `130` | `KeyboardInterrupt` (POSIX SIGINT) |

`StealthRejected → 3` is the distinct-from-1 signal so CI can light up "header drift suspected" specifically.

### AUTH-13 captured-header goldens

- **Method: pytest-httpx + JSON golden files.** Hermetic, fast, no live creds, deterministic. Path layout: `tests/auth/golden/<provider>/<flow>.json` where `<flow>` is one of `login_authorize`, `login_token_exchange`, `refresh`, `inference_stealth_request` (where applicable). Matches Phase 014's "Test strategy" section verbatim. pytest-httpx is already a dev dep.
- **Diff scope: stealth-relevant header allowlist + body-shape + URL invariants. Plus a NEGATIVE allowlist.**
  - **Positive allowlist** (must be present, exact match):
    - Anthropic: `Authorization`, `user-agent`, `x-app`, `anthropic-beta`.
    - Antigravity: `User-Agent`, `X-Goog-Api-Client`, `Client-Metadata`.
    - Gemini: `User-Agent`, `X-Goog-Api-Client`.
    - Copilot: device-code endpoint + token endpoint specific headers per Phase 017 RESEARCH.
    - API-key providers: `Authorization` shape only.
  - **Negative allowlist** (must NOT be present):
    - `x-api-key` on any stealth Anthropic call (P0-4 in disguise).
    - Bearer token in URL query strings (defensive — leakage to access logs).
  - **Body-shape:** for inference-shape requests, assert `body["system"][0]["text"]` starts with `"You are Claude Code, Anthropic's official CLI for Claude."` (Phase 014's `inject_stealth_system_prefix` invariant).
  - **URL invariants:** assert `?beta=true` present on Anthropic stealth requests. Assert host is the canonical hostname per provider.
  - **What the diff IGNORES:** httpx-default headers (`Accept`, `Accept-Encoding`, `Connection`, `Host`) — they drift across httpx versions and are noise.
- **P0 coverage:** **one named test per pitfall**, all in `tests/auth/test_p0_regression.py`:
  - `test_p0_1_user_agent_stealth` — captures Anthropic outbound user-agent matches `claude-cli/<version> (external, cli)`.
  - `test_p0_2_anthropic_beta_full_string` — captures `anthropic-beta` matches the full pinned string from `providers/anthropic.py`.
  - `test_p0_3_x_app_cli` — captures `x-app: cli`.
  - `test_p0_4_bearer_not_x_api_key` — asserts `Authorization: Bearer` AND `x-api-key` NOT present.
  - `test_p0_5_client_id_base64_decoded` — asserts `_CLIENT_ID == "9d1c250a-e61b-44d9-88ed-5944d1962f5e"` post-decode.
  - `test_p0_6_filelock_acquire_timeout` — asserts refresh fails fast on lock timeout (Phase 013 contract).
  - `test_p0_7_five_minute_expiry_buffer` — asserts `is_expired` returns True at `expires_at - 300s`.
  - `test_p0_8_pkce_state_equals_verifier` — asserts the OAuth `state` parameter byte-equals the PKCE verifier in Anthropic flow (and only in Anthropic — Gemini uses two independent verifiers per Phase 015).
  - `test_p0_13_chmod_0600_verified_on_read` — asserts vault read raises `AuthVaultPermissionError` when mode != 0o600.
  Each test's docstring references the pitfall ID and the file/line in PITFALLS.md. Failure messages point back to PITFALLS.md so future Claudes don't have to dig.
- **Golden update flow:** a `--update-goldens` pytest CLI flag (added via `pytest_addoption`) regenerates the JSON files in place. Default behavior is read-only diff. Reviewer manually inspects the golden diff before merge — that's the gate.

### Provider `_main()` argparse stubs — fate

- **Keep all five stubs** (`anthropic.py:705`, `google_gemini.py:659`, `antigravity.py:735`, `github_copilot.py:755`, `api_key.py:463`). They remain reachable as `python -m state_core.auth.providers.<provider> login`.
- **Typer commands and `_main()` stubs both call into the same provider methods** (`AnthropicAuth().login()`, etc.) — two surfaces, one code-path. No duplication, no shelling out between them.
- **Smoke-surface contract preserved:** Phase 014 wrote the stubs as "deliberately minimal so it can be removed cleanly when 022 ships" — but "cleanly" here means "preserved as the provider-level smoke surface, with Phase 022 layered on top". Keeping them avoids regressing the mitmproxy capture gate Phase 014 designed and gives future per-provider debugging (`python -m state_core.auth.providers.anthropic login` is faster than the full Typer entrypoint when you're debugging just one provider).
- **No deprecation warning.** Both surfaces are first-class. The Typer CLI is the public API; the `_main()` stubs are the dev/debug API. They coexist.

### Daemon integration (or lack thereof)

- **022 does not depend on a running daemon.** All commands run in-process, in the CLI's own Python interpreter. Phase 013's filelock serialises against any concurrent daemon refresh.
- **Concurrency safety contract:** every `login`/`logout`/`refresh` write goes through Phase 012's `save_vault()` (atomic write + 0o600 verify). Filelock from Phase 013 prevents lost updates if daemon and CLI race. CLI takes the same lock the daemon does.
- **`auth.logged_in` / `auth.logged_out` events** are dual-written to `.state/events.sqlite` + SyncEvent regardless of whether the daemon is running, per the v1 cardinal rule. If daemon is running, it sees the events on next read.

### Claude's Discretion

- Exact placement of the Typer sub-app (`src/state_cli/auth.py` vs `src/state_cli/auth/__init__.py` vs splitting into `auth/login.py` / `auth/logout.py` / `auth/status.py` if any single file exceeds the established LOC budget).
- Exact placement of the reusable ops layer (`state_core/auth/cli_ops.py` vs `state_core/auth/_ops.py` vs nesting under `state_core/auth/__init__.py`). The constraint: it imports `state_core.auth.{base, store, refresh, loader, providers.*}` — no deps on `state_cli` (one-way edge enforced by the import-graph test).
- Exact alias table contents (`claude` → anthropic, `gemini` → google.gemini, `antigravity` → google.antigravity, `copilot` → github.copilot are confirmed; minor api-key aliases like `openai-key` are at planner discretion).
- Renderer details (Rich `Table` styling, `--no-color` env var detection, color thresholds for "expires soon" — recommend amber when `< 1h`, red when `< 5min` or expired).
- Test fixture strategy for goldens (one fixture per provider vs one per flow vs hypothesis-strategy generators — recommend hand-rolled per flow because the goldens are about exact-byte invariance, not property-based exploration).
- Whether the `--update-goldens` flag is a custom `pytest_addoption` or piggybacks on `pytest --snapshot-update` from `syrupy` (only adopt syrupy if its scope warrants the dep — recommend custom flag, no new dep).
- Exact event-schema field names for `auth.logged_in` / `auth.logged_out`.
- Whether `state auth status` queries env-var fallbacks (Phase 018) and labels them `source: env` — recommend yes; users want to see "I have OPENAI_API_KEY set in my shell" in the same view.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/state_cli/main.py:14`** — `app = typer.Typer(name="state", help="state: agentic state-machine workflow engine")`. Phase 022 adds `auth_app = typer.Typer(name="auth", help="Manage authentication credentials")` and `app.add_typer(auth_app)`, mirroring the existing `db_app` and `events_app` pattern.
- **`state_core.auth.providers.anthropic.AnthropicAuth.login() / refresh()`** (Phase 014) — fully working interactive paste flow + `httpx.AsyncClient` token exchange. The Typer command calls `asyncio.run(AnthropicAuth().login())` and the existing flow does the work.
- **`state_core.auth.providers.google_gemini.GoogleGeminiAuth`** + **`state_core.auth.oauth_common.loopback`** (Phase 015) — loopback listener for browser-callback OAuth. Reused by Antigravity (Phase 016).
- **`state_core.auth.providers.antigravity.AntigravityAuth`** (Phase 016) — fixed-port 51121 loopback flow.
- **`state_core.auth.providers.github_copilot.GitHubCopilotAuth`** (Phase 017) — device-code polling state machine (`_PollingState` dataclass, RFC 8628 §3.5).
- **`state_core.auth.providers.api_key.PlainApiKeyAuth`** + **`state_core.auth.providers.api_key._REGISTRY`** + **`iter_known_prefixes()`** (Phase 018) — 12-row API-key registry, prefix validation. CLI uses `_REGISTRY` for both alias resolution and prefix-validation messages.
- **`state_core.auth.loader.load_credentials(provider_id) -> list[Credential]`** (Phase 018) — vault > env precedence. Primary read API for `state auth status`. Surfaces env-synthesized creds as `source: env`.
- **`state_core.auth.store.AuthVault`** + **`save_vault(path, vault)`** + **`load_vault(path)`** + **`get_auth_json_path()`** (Phase 012) — atomic 0o600 write, mode-verify-on-read. All Phase 022 writes go through `save_vault`.
- **`state_core.auth.refresh.refresh_credential(...)`** (Phase 013) — filelock-guarded refresh. The CLI may call this from `status` (when an OAuth cred is within the 5-min buffer) — Claude's discretion at planning time whether `status` triggers refreshes or just observes.
- **`state_core.auth.errors`** — `AuthError`, `AuthLoginError`, `AuthRefreshError`, `StealthRejected`, `AuthVaultPermissionError`, `NoCredentialsAvailableError`, `UnknownApiKeyProviderError`. Mapped to exit codes per the table above.
- **`state_core.auth.import_opencode`** (Phase 021) — sets `extras["_source"] = "opencode-import"` on every imported cred. `state auth status` reads this for the source column.
- **`state_core.auth.rotation.select_credential(...)`** (Phase 019) — not directly used by 022, but `status` ordering should not interfere with the rotation index it persists.
- **`structlog` root logger with redactor attached** (Phase 020) — safe to log paths, provider IDs, account labels (never bytes). CLI uses `structlog.get_logger("state_cli.auth")`.
- **Existing event-schema patterns** in `state_core.events` — `auth.logged_in` / `auth.logged_out` follow the same envelope shape as `auth.imported` from Phase 021.

### Established Patterns

- **Typer sub-app pattern** (`src/state_cli/main.py:16-20`): `db_app = typer.Typer(name="db"); app.add_typer(db_app); @db_app.command(name="init")`. Phase 022 mirrors this exactly.
- **Async-via-`asyncio.run()` pattern** (`src/state_cli/main.py:25`): `asyncio.run(_do_thing())`. Login/refresh are async; Typer commands are sync wrappers.
- **`typer.echo` for human output, `typer.echo(..., err=True)` for errors** (`src/state_cli/main.py:35`). Match this. Use Rich for tables specifically.
- **`typer.Exit(code=N)` from caught exceptions** (`src/state_cli/main.py:37`). Propagate to the OS exit code via the table above.
- **Per-provider `_main()` argparse smoke surface** — anthropic.py:705, google_gemini.py:659, antigravity.py:735, github_copilot.py:755, api_key.py:463 all share the same shape: argparse with `login`/`refresh` subcommands, `getpass` for sensitive input, exit codes 0/1/130. Phase 022 preserves them; Typer commands import the same provider classes they call.
- **POSIX exit-code conventions** already in use: 130 (SIGINT) per anthropic.py:725.
- **Mode isolation discipline**: `state_core.auth.*` imports are stdlib + pydantic + orjson + structlog + httpx + filelock + sibling auth modules. NO `state_build.*` / `state_teach.*`. The new `state_core.auth.cli_ops` module joins this discipline. The `state_cli.auth` Typer module imports `state_core.auth.*` but NEVER vice-versa — one-way edge enforced by `tests/auth/test_import_graph.py` (extend with a 022 row).
- **Determinism rule for handlers** (no `time.time()`, `datetime.now()`) — does NOT apply to CLI render code (rendering "expires in 4h12m" is not a domain-event handler). It DOES apply to any handler the CLI invokes; the CLI should not pass a clock into provider methods that don't already accept one.
- **pytest-httpx fixture pattern** already used in Phase 014 tests — Phase 022 extends, doesn't redesign.

### Integration Points

- **`src/state_cli/main.py:14`**: insert `from state_cli.auth import auth_app; app.add_typer(auth_app)` near the existing `db_app` / `events_app` registrations.
- **`pyproject.toml` `[project.scripts]`**: `state = "state_cli.main:app"` is presumably already wired (verify in planning). New auth commands are reachable as `state auth ...` automatically once the sub-app is registered.
- **`state_core.events` schema**: add `auth.logged_in` and `auth.logged_out` event-types. Coordinate with the v1 event-schema versioning pattern. Likely `auth` aggregate, mirroring Phase 021's `auth.imported`.
- **Phase 021's importer at daemon start**: unrelated to 022's CLI-time login/logout — but `state auth status` MUST surface the `_source` marker the importer writes, so 021's contract becomes 022's API.
- **`tests/auth/test_import_graph.py`**: extend with a row asserting `state_cli.auth` may import `state_core.auth.*` but NOT `state_build.*` / `state_teach.*`, AND `state_core.auth.cli_ops` may NOT import `state_cli.*`.
- **Future opencode-plugin TUI modal phase**: imports `state_core.auth.cli_ops` (or its successor) directly. The contract being designed in 022 is what that future phase will consume — so the ops module is the deliverable of strategic value, not the Typer commands.

</code_context>

<specifics>
## Specific Ideas

- **Bigger picture (recorded for planning awareness, not for 022's scope):** the eventual primary auth UX is an opencode-plugin TUI modal — slash command opens a modal, arrow-key (and mouse) provider picker, secure input for API key, saves on the spot, switches active provider/model on the spot, and once a key is loaded the user can switch back to that provider/model without re-entering credentials. **That lives in `@state/opencode-plugin`, a future phase under the plugin work — NOT in 022.** Phase 022's contribution to that future is the reusable `state_core.auth.cli_ops` module (or whatever Claude names it) so the modal can call the same primitives. The Typer CLI is the secondary surface; it's first to ship because it's the lowest-stakes way to (a) prove the auth layer end-to-end, (b) give an escape hatch when the TUI breaks, (c) satisfy AUTH-13 goldens without dragging opencode into CI.
- **`StealthRejected` → exit 3** is a deliberate distinct-from-1 signal. CI should grep for exit code 3 to surface "header drift suspected" specifically rather than mixing it with generic auth failures. Document this in the CLI help text.
- **Account label fallback chain (binding):** `extras["email_address"]` > `account_id` > `f"{prefix12}…"`. Same precedence as Phase 014's success print. Keep consistent.
- **Phase 021 deferrals stay deferred to a follow-up phase, not lost.** `state auth import-opencode --force`, `state auth prune --expired`, and the auto-import opt-out flag are tracked in `<deferred>` below; they belong in their own phase that can be planned after 022 ships, since 022 is already large with the goldens + 9 P0 regression tests + Typer sub-app + ops layer.
- **Real opencode shape on the dev box** (verified `~/.local/share/opencode/auth.json` 2026-05-01 from Phase 021): three plain api keys (`opencode`, `openrouter`, `deepseek`). Once Phase 021's importer runs at daemon start, `state auth status` should show three rows with `source: opencode-import` on this box. Smoke-test target.
- **AUTH-13 mapping to existing PITFALLS.md rows** is one-to-one. Each test docstring includes the pitfall ID (`P0-X`) and the file:line reference inside PITFALLS.md. When PITFALLS.md changes, the docstrings are the trace.
- **Provider list as of 022 planning:** 4 OAuth (`anthropic`, `google.gemini`, `google.antigravity`, `github.copilot`) + 12 API key (from Phase 018 `_REGISTRY`: anthropic, openai, google, deepseek, groq, together, anyscale, mistral, cohere, openrouter, grok, cerebras). The CLI's interactive picker enumerates all 16; some show `(api_key)`, others `(oauth)`, some both — when a provider has both surfaces (e.g. `anthropic`), the picker labels them `anthropic (oauth)` and `anthropic (api_key)`.

</specifics>

<deferred>
## Deferred Ideas

- **`state auth import-opencode [--force]`** — manual re-trigger of Phase 021's importer + auto-import opt-out flag. Phase 021 explicitly marked this as a 022 candidate; we're punting it to a follow-up phase to keep 022's scope tight (Typer + ops layer + AUTH-13 goldens is already large).
- **`state auth prune --expired`** — cleanup of accumulated multi-cred arrays from rotation-driven appends. Same follow-up phase.
- **`state auth refresh <provider> [--account]`** — force a refresh outside the normal load-time path. Useful for debugging stealth-header drift. Same follow-up phase. (Note: `refresh` already happens implicitly inside `login` and the `state_core.auth.refresh` lock; explicit CLI surface is convenience.)
- **`state auth providers list`** — discovery aid showing all 16 supported providers and their login readiness. `status` covers the configured-creds case; this would cover the empty case. Possibly absorbed into an enhanced `status --all` flag in the same follow-up phase.
- **opencode-plugin TUI modal** (slash-command-triggered provider picker, secure key entry, live model switch) — separate phase under `@state/opencode-plugin`. Imports `state_core.auth.cli_ops` from 022. Out of scope here.
- **Daemon HTTP/JSONRPC API for auth** — when v3+ adds the daemon control plane, the Typer commands may become thin clients that POST to the daemon. Phase 022 keeps the in-process model; future phase migrates without breaking the CLI surface.
- **Live mitmproxy capture replay in CI** — higher-fidelity than pytest-httpx mocks (catches things mocks miss), but binary fixtures + real-cred capture step is too much for 022. The mitmproxy gate stays as a manual pre-merge step per Phase 014's RESEARCH.
- **`--update-goldens` automation** — wired into a CI workflow that auto-PRs golden updates when stealth headers change upstream. 022 ships the flag; a separate phase wires the automation if it proves useful.
- **Bidirectional sync to opencode auth.json** — explicit non-goal (Phase 021 stance preserved).
- **Windows path / mode handling** — milestone-level Windows arc; 022 emits the same warning Phase 012 / Phase 021 emit.
- **Color-blind / no-color theming polish** — `--no-color` is honored, but bespoke palettes for amber/red urgency colors are deferred to a UX-polish phase.

</deferred>

---

*Phase: 022-cli-state-auth-login-logout*
*Context gathered: 2026-05-01*
