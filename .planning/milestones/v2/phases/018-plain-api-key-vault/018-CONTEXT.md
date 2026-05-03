# Phase 018: Plain API-key vault (12 providers) - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

API-key storage layer + AuthMethod implementations for 12 plain-key providers (Anthropic-direct, OpenAI, Google AI Studio, DeepSeek, Groq, Together, Anyscale, Mistral, Cohere, OpenRouter, Grok / xAI, Cerebras), plus env-var fallback synthesis.

**Owns:**
- `state_core.auth.providers.api_key` — PlainApiKeyAuth class + 12-row registry
- `state_core.auth.loader` (NEW) — `load_credentials(provider_id)` orchestrator that fuses vault + env-var fallback
- `__main__` argparse entry-point for `python -m state_core.auth.providers.api_key login <provider_id>`

**Depends on:** 011 (`ApiKeyCredential` model + `AuthMethod` Protocol), 012 (`store.py` round-trip + array-per-provider invariant)

**Requirement:** AUTH-05.

**Does NOT own:**
- Round-robin rotation across multi-cred lists — Phase 019.
- Token redaction patterns for these key shapes — Phase 020 (this phase contributes prefix data via the registry; redactor consumes it).
- `state auth login|logout|status` CLI surface — Phase 022 (this phase exposes a `__main__` plumbed AuthMethod; CLI wraps it).
- Provider routing / base URLs / model dispatch — Tier-1 v3 (Provider Routing milestone).

</domain>

<decisions>
## Implementation Decisions

### Provider class shape (one class, registry-driven)
- **Single `PlainApiKeyAuth` class** parameterized by `provider_id`. NOT 12 separate provider files. Plain keys are uniform enough that the OAuth-precedent (one file per provider) is duplication waste here; OAuth providers earn their own files because each has unique flows, plain keys do not.
- **`_REGISTRY: dict[str, ApiKeyProviderSpec]`** as a module-level Python constant in `state_core/auth/providers/api_key.py`. Pure Python (no JSON / YAML / pluggy) — typecheckable, IDE-completable, no import-time I/O, mode-isolation clean.
- **`ApiKeyProviderSpec`** carries: `provider_id: str`, `auth_header: tuple[str, str]` (header name + `{key}`-templated value), `key_prefixes: tuple[str, ...]` (longest-first), `env_var: str`, plus a free-form `notes` / provenance comment. Shape: frozen Pydantic model OR `@dataclass(frozen=True)` (Claude's discretion — frozen Pydantic preferred for symmetry with `_CredentialBase`).
- **Factory function `get_api_key_auth(provider_id: str) -> AuthMethod`** is the public construction API. `PlainApiKeyAuth.__init__` is internal. Unknown `provider_id` raises `UnknownApiKeyProviderError` (new, in `state_core.auth.errors`).
- **Registry iteration order = longest-prefix first.** This is the ONLY mechanism for resolving the `sk-` collision (Anthropic `sk-ant-api03-`, OpenRouter `sk-or-`, OpenAI `sk-proj-` / bare `sk-`). Each `PlainApiKeyAuth.is_token()` checks ITS OWN prefix list; the downstream sniffer iterates registry entries in declared order. Documented invariant in `_REGISTRY`.

### Header & key-prefix table
- **Auth header encoding: single `(name, value_template)` tuple per row.** Examples:
  - `anthropic.api_key` → `("x-api-key", "{key}")`
  - OpenAI / Groq / Together / Mistral / Cohere / DeepSeek / Anyscale / OpenRouter / Grok / Cerebras → `("Authorization", "Bearer {key}")`
  - `google.ai_studio` (Gemini API key) → `("x-goog-api-key", "{key}")` — header form, NOT `?key=` query param (uniform across all 12).
- **Provider-id namespacing for Anthropic disambiguation:** `provider_id="anthropic.api_key"` for direct console keys; `"anthropic"` remains the Phase 014 OAuth method. Mirrors existing `"google.gemini_cli"` / `"google.antigravity"` precedent. Distinct provider-buckets in `auth.json` so Phase 019 round-robin never mixes OAuth + api_key creds.
- **Prefix validation: warn-and-store, never refuse.** If the entered key doesn't match any of the registry's known `key_prefixes` for that provider, emit `structlog.warning("api_key.prefix_mismatch", provider_id=..., observed_prefix=key[:8])` and store anyway. Reason: vendor-side prefix introductions (`sk-proj-` rolling out for OpenAI in 2024, `sk-ant-api03-` superseding `sk-ant-api02-`) would brick users on rotation if we hard-rejected. The `is_token` sniffer still works for known shapes; unknown prefixes mean the user must explicitly pass `provider_id`.
- **Canonical prefix lists & env-var names: researcher fills in at plan-phase.** `018-RESEARCH.md` MUST confirm each provider's current public-key prefix(es) and standard env-var name from official docs at the time research runs (Anthropic console, OpenAI platform docs, Google AI Studio, Groq console, Cohere dashboard, Mistral console, DeepSeek platform, Together AI, Anyscale Endpoints, OpenRouter dashboard, xAI console, Cerebras Inference). Each registry row gets a `# captured 2026-04-30 from <url>` provenance comment, mirroring the byte-for-byte provenance pattern that `claude-oauth.md` established for Phase 014.

### Env-var fallback
- **Vault > env. Vault-empty fallback only.** If `auth.json` has at least one credential for `provider_id`, vault wins. Only when vault has no entry (or auth.json is missing) do we synthesize from env. Matches user mental model "I logged in, so use that key"; env covers first-run / CI without a login step. Phase 019 multi-cred operates on vault entries ONLY — env never participates in round-robin.
- **Synthesis lives in a new module: `state_core.auth.loader`.** Public API: `load_credentials(provider_id: str) -> list[Credential]`. Internally: `load_vault(get_auth_json_path()).providers.get(provider_id, [])` → if non-empty, return it; else if `os.environ.get(spec.env_var)` is set + non-empty, return `[ApiKeyCredential(key=..., provider_id=...)]`; else `[]`. Keeps `store.py` pure (no env knowledge), keeps `PlainApiKeyAuth` pure (no I/O for header injection), gives Phase 019/022 a single canonical entry point. Mode-isolation: imports stdlib + `state_core.auth.base` + `state_core.auth.store` + `state_core.auth.providers.api_key._REGISTRY` only.
- **Env-synthesized credentials are ephemeral.** Never persisted to `auth.json`. Avoids the "env was wrong, now it's stuck in the vault" footgun and keeps `auth.json` authoritative-when-present. Phase 019 round-robin sees an empty list when only env is set; that's intentional.
- **Env-var names: standard vendor names.** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY` (Google AI Studio), `COHERE_API_KEY`, `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `TOGETHER_API_KEY`, `ANYSCALE_API_KEY`, `OPENROUTER_API_KEY`, `XAI_API_KEY` (Grok), `CEREBRAS_API_KEY`. Researcher confirms exact canonical spelling per official docs at plan-phase. Empty-string env vars are treated as unset (12-factor convention).

### Login UX & validation
- **Input: getpass on TTY, single-line stdin on non-TTY.** No `--api-key` flag — argv leaks to `ps` / shell history / Mac unified logs. CI uses `echo $KEY | python -m state_core.auth.providers.api_key login openai` or env-var fallback (which is the preferred CI path).
- **Validation: format only, no live API call.** Reject empty / whitespace-only keys; warn-and-store on prefix mismatch (above). Reasons: Phase 018 must be offline-testable; live-call paths multiply per-provider verify endpoints (DeepSeek / Cohere / Mistral all differ); a wrong key fails fast on first real request anyway. A future opt-in `state auth status --verify` (Phase 022) can add live checks if a real need surfaces.
- **Repeat login: append by default, `--replace` flag to overwrite.** Default appends to `vault.providers[provider_id]` list (preserves array-per-provider P0-13 invariant; sets up Phase 019 round-robin naturally). `--replace` truncates to a single new entry. Same key string is deduplicated (no dupe inserts).
- **Owner of the login body: `PlainApiKeyAuth.login()` returns a fresh `ApiKeyCredential` after input + format-check.** Does NOT touch `auth.json` directly. Persistence + append/replace/dedup logic lives in the Phase 022 CLI handler (or `loader.py` helper if the Phase 022 plan factors it that way). Mirrors Phase 014–017 OAuth providers, which all return `Credential` without writing to disk. Keeps `PlainApiKeyAuth` pure and testable; preserves `AuthMethod` Protocol symmetry for downstream `runtime_checkable` plugin discovery.

### Claude's Discretion
- `ApiKeyProviderSpec` exact shape: frozen Pydantic vs `@dataclass(frozen=True)`. Default to frozen Pydantic for symmetry with `_CredentialBase` unless plan-phase research surfaces a reason.
- File location: `providers/api_key.py` (single file) vs `providers/api_keys/__init__.py` package. Default to single file; promote to package only if the registry + class + helpers exceed ~600 LOC.
- Test scaffold layout: one parameterized `test_api_key.py` with `pytest.mark.parametrize` over the 12 providers vs per-provider test files. Default to parameterized (the class is shared; the data is what varies).
- `__main__` argparse subcommand surface: at minimum `login <provider_id>`. Whether to also expose `list` (dump registry) or `refresh` (no-op for api_key, raises) is Claude's discretion — match the OAuth providers' `__main__` surface where it adds value, skip where it doesn't.
- Empty-vault edge case for `load_credentials`: when vault exists but `provider_id` key is missing AND env var is set, synthesize. When vault is missing (`FileNotFoundError`) AND env var is set, synthesize. Both should be handled identically.
- Whether `loader.py` exposes a `load_all_providers() -> dict[str, list[Credential]]` helper for Phase 022's `state auth status` enumeration. Defer until Phase 022 needs it.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ApiKeyCredential`** (`src/state_core/auth/base.py`) — already defined: `type="api_key"`, `key: str` (Field repr=False), `provider_id: str`, `extras: dict`. No expiry, no refresh. Phase 018 instantiates this directly.
- **`AuthMethod` Protocol** (`src/state_core/auth/base.py`) — `is_token` / `is_expired` / `http_headers` / `login` / `refresh`. PlainApiKeyAuth satisfies structurally: `is_expired → False`, `refresh(cred) → cred` unchanged.
- **`store.py`** (`src/state_core/auth/store.py`) — `load_vault` / `save_vault` / `ensure_initialized` already round-trip the `Credential` discriminated union. Plain api_key credentials Just Work via `CredentialAdapter`. No store changes required for Phase 018.
- **`state_core.auth.errors`** (`src/state_core/auth/errors.py`) — `AuthError` / `AuthLoginError` / `AuthRefreshError` already promoted (Phase 015). Phase 018 ADDS `UnknownApiKeyProviderError` (raised by `get_api_key_auth`).

### Established Patterns
- **Module structure (Phase 014–017 precedent):** Constants block at top → Pydantic models → sync helpers → AuthMethod class → `if __name__ == "__main__"` argparse block. Phase 018 follows the same shape but the "AuthMethod class" section is just `PlainApiKeyAuth` (one class), and the constants block is the `_REGISTRY` dict.
- **Determinism rule (Phase 011 / `base.py` cardinal rule 2):** `is_expired(cred, now)` takes `now` as a parameter — never `time.time()` internally. Phase 018 trivially complies (always returns False).
- **Mode isolation (`CLAUDE.md`):** `state_core.*` may NOT import `state.build.*` / `state.teach.*`. Phase 018 imports stdlib + `pydantic` + `structlog` + `state_core.auth.base` + (loader.py only) `state_core.auth.store`. CI import-graph lint enforces.
- **Secret hygiene (Phase 011 cardinal rule 3):** `key: str = Field(repr=False)` already excludes the secret from repr. Phase 020 (root-logger redactor) is the second defense layer; Phase 018 contributes the prefix data the redactor will consume.
- **Per-call construction (no module-level singletons)** — Phase 014 RESEARCH §Pattern 2, P1-9 defense. `get_api_key_auth()` returns a fresh instance per call.

### Integration Points
- **Phase 019 (multi-cred round-robin)** — operates on `vault.providers[provider_id]` lists ONLY. Phase 018 ensures the array shape is preserved on every login (append-default + dedup). Env-synthesized creds are ephemeral and never participate.
- **Phase 020 (root-logger token redactor)** — consumes the registry's `key_prefixes` to build the regex set. Phase 018 exports `_REGISTRY` (or a derived `iter_known_prefixes()` helper) for this.
- **Phase 021 (first-run import from opencode `auth.json`)** — opencode stores plain api_keys under similar provider names; Phase 021 maps opencode IDs → state's registry IDs (where they differ, e.g. `anthropic` OAuth vs `anthropic.api_key`). Phase 018's stable provider_ids are the import target.
- **Phase 022 (CLI: `state auth login|logout|status`)** — wraps `PlainApiKeyAuth.login()` for the interactive flow, calls `load_credentials()` for `status` enumeration, owns the `--replace` flag and the on-disk persistence around the AuthMethod call. Phase 018 gives Phase 022 a clean `__main__` to delegate to (or to import directly).
- **v3 milestone (Provider Routing)** — consumes `http_headers(cred)` output to inject auth into outbound litellm calls (or the Anthropic OAuth stealth escape hatch). Header table living in Phase 018's registry is the single source of truth for the auth-header dimension.

</code_context>

<specifics>
## Specific Ideas

- **DRY beats precedent here.** OAuth providers each got their own file because they each had unique flows (PKCE+stealth vs PKCE+loopback vs device-code). Plain keys are genuinely uniform — header + prefix + env var per provider, nothing else. One class + registry table is the right shape.
- **Provenance comments matter.** Every registry row gets a `# captured 2026-04-30 from <url>` comment mirroring `claude-oauth.md`. Vendors change prefixes (`sk-proj-` is the canonical recent example); the provenance is what makes drift detectable.
- **No live API call during login.** Offline-testable phase, no per-provider verify-URL table, fail-fast happens on first real request anyway.
- **Append-default repeat login** preserves the array-per-provider P0-13 invariant Phase 012 enforced — Phase 019 round-robin gets a populated list naturally, no special-case bootstrapping.
- **Env-fallback synthesis is ephemeral.** Vault stays authoritative-when-present; env covers zero-config / CI flows without contaminating the vault.

</specifics>

<deferred>
## Deferred Ideas

- **`state auth status --verify` live API check** — adds per-provider verify-URL table; defer to Phase 022 if a real ask surfaces.
- **`state auth import-env` command** to materialize env vars into the vault — defer to Phase 022 unless onboarding pain materializes.
- **`STATE_*`-prefixed env-var override layer** (e.g., `STATE_OPENAI_API_KEY` taking precedence over `OPENAI_API_KEY`) — speculative; defer until a multi-tool collision actually bites.
- **Pluggy hook for downstream providers to register their own api_key entries** — aligns with v1's plugin direction but YAGNI for a 12-row built-in table; revisit when an external plugin actually needs to add a 13th provider.
- **JSON / YAML data file for the registry** — rejected for Phase 018 (no benefit over a Python constant); revisit only if non-developers need to edit the table without a code review.
- **Encryption-at-rest for `auth.json`** — chmod 0600 is the layer for v2; OS keychain integration is a future milestone, not Phase 018.
- **Multi-account-per-key (e.g., one OpenAI key with multiple project IDs)** — `extras` dict already supports this if needed; no Phase 018 work required.

</deferred>

---

*Phase: 018-plain-api-key-vault*
*Context gathered: 2026-04-30*
