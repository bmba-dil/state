# Phase 018: Plain API-key vault (12 providers) — Research

**Researched:** 2026-04-30
**Domain:** API-key storage, provider-keyed registry, env-var fallback, login UX
**Confidence:** HIGH for ecosystem patterns + module shape; MEDIUM-to-HIGH for individual provider key prefixes (some vendors do not publish a canonical prefix; treated as `()` in the registry).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Provider class shape (one class, registry-driven):**
- Single `PlainApiKeyAuth` class parameterized by `provider_id` — NOT 12 separate provider files. Plain keys are uniform; OAuth precedent (one file per provider) is duplication waste here.
- `_REGISTRY: dict[str, ApiKeyProviderSpec]` — module-level Python constant in `state_core/auth/providers/api_key.py`. Pure Python (no JSON/YAML/pluggy).
- `ApiKeyProviderSpec` carries: `provider_id`, `auth_header: tuple[str, str]` (header name + `{key}`-template), `key_prefixes: tuple[str, ...]` (longest-first), `env_var: str`, plus `notes`/provenance comment. Frozen Pydantic preferred for symmetry with `_CredentialBase` (Claude's discretion).
- Public construction API: `get_api_key_auth(provider_id: str) -> AuthMethod`. `PlainApiKeyAuth.__init__` is internal. Unknown `provider_id` raises new `UnknownApiKeyProviderError` (added to `state_core.auth.errors`).
- Registry iteration order = longest-prefix first; ONLY mechanism for resolving the `sk-` collision.

**Header & key-prefix table:**
- `anthropic.api_key` → `("x-api-key", "{key}")`
- OpenAI / Groq / Together / Mistral / Cohere / DeepSeek / Anyscale / OpenRouter / Grok / Cerebras → `("Authorization", "Bearer {key}")`
- `google.ai_studio` → `("x-goog-api-key", "{key}")` — header form, NOT `?key=` query param.
- `provider_id="anthropic.api_key"` for direct console keys; `"anthropic"` remains Phase 014 OAuth method (mirrors `google.gemini_cli` / `google.antigravity` precedent).
- Prefix validation: warn-and-store (structlog warning, observed_prefix=key[:8], store anyway). Vendor prefix changes (e.g. `sk-proj-` rollout) must not brick users.

**Env-var fallback:**
- Vault > env. Vault-empty fallback only.
- Synthesis lives in NEW module `state_core.auth.loader`. Public API: `load_credentials(provider_id: str) -> list[Credential]`. Imports stdlib + `state_core.auth.base` + `state_core.auth.store` + `state_core.auth.providers.api_key._REGISTRY` only.
- Env-synthesized credentials are ephemeral — never persisted to `auth.json`.
- Empty-string env vars are treated as unset (12-factor convention).

**Login UX & validation:**
- Input: `getpass` on TTY, single-line `stdin` on non-TTY. NO `--api-key` flag (argv leakage to ps/shell history/Mac unified logs).
- Validation: format only (reject empty/whitespace, warn-and-store on prefix mismatch). NO live API call.
- Repeat login: append by default, `--replace` flag to overwrite. Same key string deduplicated.
- `PlainApiKeyAuth.login()` returns a fresh `ApiKeyCredential` after input + format-check. Does NOT touch `auth.json`. Persistence + append/replace/dedup logic lives in Phase 022 CLI handler (or a `loader.py` helper).

### Claude's Discretion

- `ApiKeyProviderSpec` exact shape: frozen Pydantic vs `@dataclass(frozen=True)`. Default frozen Pydantic.
- File location: `providers/api_key.py` single file (default) vs `providers/api_keys/__init__.py` package (only if registry+class+helpers exceed ~600 LOC).
- Test scaffold: parameterized `test_api_key.py` (default) vs per-provider files.
- `__main__` argparse subcommands: at minimum `login <provider_id>`. Whether to add `list` (dump registry) or `refresh` (no-op for api_key, raises) is Claude's call.
- Empty-vault edge case for `load_credentials`: handle vault-missing-FileNotFoundError and vault-present-but-no-bucket identically (synthesize from env if set).
- Whether `loader.py` exposes a `load_all_providers()` helper — defer until Phase 022 needs it.

### Deferred Ideas (OUT OF SCOPE for Phase 018)

- `state auth status --verify` live API check (Phase 022 if asked).
- `state auth import-env` to materialize env vars into vault (Phase 022 if asked).
- `STATE_*`-prefixed env-var override layer (e.g. `STATE_OPENAI_API_KEY`).
- Pluggy hook for downstream providers to register their own api_key entries.
- JSON/YAML data file for the registry.
- Encryption-at-rest for `auth.json` (chmod 0600 is the v2 layer; OS keychain is future).
- Multi-account-per-key (the `extras` dict already supports it; no Phase 018 work needed).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-05 | API key vault (plain keys for Anthropic/OpenAI/Google/DeepSeek/Groq/Together/Anyscale/Mistral/Cohere/OpenRouter/Grok/Cerebras) | Provider Registry Table provides 12-row spec with verified env-vars + auth-headers + (where published) prefixes. Module Shape Reference derives the file layout from Phase 014–017 OAuth provider precedent. `state_core.auth.loader` placement section pins the env-fallback module's import graph. Validation Architecture lists every failure mode the test scaffold must prove. |
</phase_requirements>

## Summary

Phase 018 is the simplest of the auth-provider phases: 12 providers, one class, one registry table, one new loader module. The OAuth-provider precedent established in Phases 014–017 (constants block → Pydantic models → sync helpers → AuthMethod class → `__main__` argparse) collapses for plain keys because every provider's behaviour is *table-driven* — `(env_var, header_name, header_value_template, prefix_tuple)` is the entire spec. CONTEXT.md correctly identifies that giving each provider its own file (the OAuth approach) would be duplication waste; one `PlainApiKeyAuth` class parameterized by `provider_id` is the right shape.

The non-trivial research deliverables are: (1) the 12-row registry table with verified env-var names and auth headers; (2) a longest-prefix-first ordering that resolves the `sk-` collision (Anthropic `sk-ant-api03-`, OpenRouter `sk-or-v1-`, OpenAI `sk-proj-` / bare `sk-`); (3) the placement of the new `state_core.auth.loader` module in a way that doesn't introduce a circular import with `providers/api_key.py`. All three are pinned below.

**Primary recommendation:** Implement `state_core.auth.providers.api_key` as a single ~400 LOC file containing the 12-row `_REGISTRY`, the `ApiKeyProviderSpec` frozen Pydantic model, the `PlainApiKeyAuth` class, and the `__main__` argparse block (login subcommand only). Implement `state_core.auth.loader` as a separate ~120 LOC module that imports `_REGISTRY` from `api_key.py` (one-way; never the reverse). Test via a single parameterized `test_api_key.py` over the 12-row registry plus a separate `test_loader.py` covering the four vault×env precedence combinations. No `pytest-httpx` is needed — Phase 018 has zero outbound HTTP. No `hypothesis` is needed either — the failure surface is enumerable.

## Provider Registry Table

Longest-prefix-first per provider; `()` marks providers with no published canonical prefix (warn-and-store still works because the prefix-mismatch path is permissive). All entries captured 2026-04-30; each registry row in code MUST carry a `# captured 2026-04-30 from <url>` provenance comment, mirroring the byte-for-byte provenance pattern of `claude-oauth.md` (Phase 014).

| provider_id | env_var | auth_header | key_prefixes (longest-first) | source URL | captured |
|-------------|---------|-------------|------------------------------|------------|----------|
| `anthropic.api_key` | `ANTHROPIC_API_KEY` | `("x-api-key", "{key}")` | `("sk-ant-api03-",)` | https://platform.claude.com/docs/en/api/getting-started | 2026-04-30 |
| `openai` | `OPENAI_API_KEY` | `("Authorization", "Bearer {key}")` | `("sk-proj-", "sk-svcacct-", "sk-None-", "sk-")` | https://platform.openai.com/docs/api-reference/authentication (community-confirmed: sk-proj-/sk-svcacct-/sk-None-/legacy sk-) | 2026-04-30 |
| `google.ai_studio` | `GEMINI_API_KEY` | `("x-goog-api-key", "{key}")` | `()` | https://ai.google.dev/gemini-api/docs/api-key | 2026-04-30 |
| `groq` | `GROQ_API_KEY` | `("Authorization", "Bearer {key}")` | `("gsk_",)` | https://console.groq.com/docs/quickstart + https://console.groq.com/docs/production-readiness/security-onboarding | 2026-04-30 |
| `deepseek` | `DEEPSEEK_API_KEY` | `("Authorization", "Bearer {key}")` | `()` | https://api-docs.deepseek.com/ | 2026-04-30 |
| `together` | `TOGETHER_API_KEY` | `("Authorization", "Bearer {key}")` | `()` | https://docs.together.ai/docs/quickstart | 2026-04-30 |
| `anyscale` | `ANYSCALE_API_KEY` | `("Authorization", "Bearer {key}")` | `("esecret_",)` | https://docs.anyscale.com/endpoints/text-generation/authenticate/ | 2026-04-30 |
| `mistral` | `MISTRAL_API_KEY` | `("Authorization", "Bearer {key}")` | `()` | https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key | 2026-04-30 |
| `cohere` | `COHERE_API_KEY` | `("Authorization", "Bearer {key}")` | `()` | https://docs.cohere.com/reference/about | 2026-04-30 |
| `openrouter` | `OPENROUTER_API_KEY` | `("Authorization", "Bearer {key}")` | `("sk-or-v1-", "sk-or-")` | https://openrouter.ai/docs/api/reference/authentication | 2026-04-30 |
| `xai` | `XAI_API_KEY` | `("Authorization", "Bearer {key}")` | `("xai-",)` | https://docs.x.ai/developers/quickstart | 2026-04-30 |
| `cerebras` | `CEREBRAS_API_KEY` | `("Authorization", "Bearer {key}")` | `()` | https://inference-docs.cerebras.ai/api-reference/authentication | 2026-04-30 |

**Notes on prefix confidence:**
- HIGH confidence (vendor-published or near-universally observed): `sk-ant-api03-` (Anthropic), `sk-proj-`/`sk-svcacct-`/`sk-None-`/`sk-` (OpenAI), `gsk_` (Groq), `esecret_` (Anyscale), `sk-or-v1-` (OpenRouter), `xai-` (xAI Grok).
- LOW / no public spec: DeepSeek, Together, Mistral, Cohere, Cerebras, Google AI Studio. Empty `()` is the right registry value — `is_token` returns False for these (downstream sniffer can't auto-route bare keys), and `login` warn-and-stores any key. This is *intentionally* permissive: vendors rotate prefixes (the OpenAI `sk-proj-` rollout is the canonical example) and a hard-coded mismatch would brick users on rotation.

**Cohere env-var caveat:** Cohere's official Python SDK reads `CO_API_KEY` (not `COHERE_API_KEY`). However, `COHERE_API_KEY` is the universally-recognised spelling across third-party tooling (litellm, AutoGen, AG2, OpenClaw, n8n, langchain). Phase 018 uses `COHERE_API_KEY` (12-factor canonical, ecosystem-aligned) and documents the Cohere-SDK divergence in the registry row's `notes` field. If a real user pain materializes, Phase 022 can add `CO_API_KEY` as an alias.

## Header Table Verification

CONTEXT.md's three-bucket assertion holds for every provider:

| Provider | CONTEXT.md assertion | Verified | Notes |
|----------|---------------------|----------|-------|
| `anthropic.api_key` | `("x-api-key", "{key}")` | ✅ | platform.claude.com/docs/en/api/getting-started — explicit `x-api-key` header. |
| `google.ai_studio` | `("x-goog-api-key", "{key}")` (header form, NOT `?key=`) | ✅ | ai.google.dev shows both `?key=` query param and `x-goog-api-key` header — header is preferred and uniform with the rest. CONTEXT.md's choice is correct. |
| openai | `("Authorization", "Bearer {key}")` | ✅ | OpenAI standard. |
| groq | `Bearer` | ✅ | console.groq.com shows `Authorization: Bearer $GROQ_API_KEY`. |
| deepseek | `Bearer` | ✅ | api-docs.deepseek.com shows curl with `Authorization: Bearer ${DEEPSEEK_API_KEY}`. |
| together | `Bearer` | ✅ | docs.together.ai shows Bearer. |
| anyscale | `Bearer` | ✅ | docs.anyscale.com/endpoints — "attach your API key as the bearer token". |
| mistral | `Bearer` | ✅ | docs.mistral.ai — `Authorization: Bearer $MISTRAL_API_KEY`. |
| cohere | `Bearer` | ✅ | docs.cohere.com/reference/about — "the content of `Authorization` should be in the shape of `BEARER [API_KEY]`". |
| openrouter | `Bearer` | ✅ | openrouter.ai/docs/api/reference/authentication — `Authorization: Bearer $OPENROUTER_API_KEY`. |
| xai | `Bearer` | ✅ | docs.x.ai/developers/quickstart — `Authorization: Bearer $XAI_API_KEY`. |
| cerebras | `Bearer` | ✅ | inference-docs.cerebras.ai/api-reference/authentication — "API keys are passed using HTTP Bearer authentication". |

**No deviations found.** Every provider in the 12-row table conforms to one of the three CONTEXT.md-asserted shapes. No provider requires extra headers (e.g., `anthropic-version` is required by Anthropic's *Messages* API but NOT by the auth header itself — it's a per-request concern that lives in v3 inference routing, not in `http_headers(cred)`).

**Anti-pattern noted (out of scope but worth flagging):** Some providers (notably Cohere's older docs and Mistral's curl examples) write `BEARER` in uppercase. RFC 6750 §2.1 mandates *case-insensitive* scheme matching, but the canonical capitalization across ecosystems is `Bearer ` (mixed case, single space). Phase 018 emits `Bearer ` consistently.

## sk- Collision Resolution

CONTEXT.md says registry iteration order = longest-prefix first, and `is_token` checks the provider's own prefix list. The downstream sniffer (Phase 022 CLI? Phase 020 redactor?) iterates the registry in declared order; whichever provider's `is_token(key)` returns True first wins.

**Recommended `_REGISTRY` insertion order** (Python 3.7+ dict iteration order = insertion order, guaranteed):

```python
_REGISTRY: dict[str, ApiKeyProviderSpec] = {
    # 1. anthropic.api_key — sk-ant-api03- is the longest sk- prefix.
    "anthropic.api_key": ...,                # ("sk-ant-api03-",)
    # 2. openrouter — sk-or-v1- before sk-or- (longest within provider).
    "openrouter":        ...,                # ("sk-or-v1-", "sk-or-")
    # 3. openai — sk-proj-/sk-svcacct-/sk-None- before bare sk-.
    "openai":             ...,               # ("sk-proj-", "sk-svcacct-", "sk-None-", "sk-")
    # 4. anyscale — esecret_ — disjoint from sk-, order doesn't matter.
    "anyscale":           ...,               # ("esecret_",)
    # 5. xai — xai- — disjoint from sk-, order doesn't matter.
    "xai":                ...,               # ("xai-",)
    # 6. groq — gsk_ — disjoint, order doesn't matter.
    "groq":               ...,               # ("gsk_",)
    # 7-12. providers with no published prefix — order irrelevant.
    "google.ai_studio":   ...,               # ()
    "deepseek":           ...,               # ()
    "together":           ...,               # ()
    "mistral":            ...,               # ()
    "cohere":             ...,               # ()
    "cerebras":           ...,               # ()
}
```

**Why this resolves cleanly:**
- `sk-ant-api03-XXX` matches `anthropic.api_key` first (longest). It also starts with `sk-` (OpenAI's bare prefix), so without the longest-first rule OpenAI would steal Anthropic keys.
- `sk-or-v1-XXX` matches `openrouter` second (longest among routers). Without longest-first, OpenAI bare `sk-` would steal it.
- `sk-proj-XXX` matches `openai` third. OpenAI's *internal* prefix tuple is also longest-first within the provider.
- Bare `sk-XXX` falls through to OpenAI as the last `sk-`-using provider — correct, since legacy OpenAI user keys still exist.
- `esecret_`, `xai-`, `gsk_`, `co_` (if added later), `mistral_` (if added later) are *disjoint character sets* relative to `sk-`, so their position is irrelevant to the collision.

**Invariant to encode in `_REGISTRY`'s docstring:**
> Registry iteration order is load-bearing. `sk-`-using providers MUST be ordered longest-prefix-first across providers (anthropic.api_key → openrouter → openai). Within a provider, `key_prefixes` MUST also be ordered longest-first. Adding a new `sk-`-prefixed provider requires reviewing this ordering.

A defensive unit test SHOULD assert this ordering: walk `_REGISTRY` once, collect `(provider_id, prefix)` for every prefix that starts with `sk-`, and assert the resulting list is sorted by descending prefix length.

## anthropic.api_key Namespacing Audit

CONTEXT.md uses `provider_id="anthropic"` for OAuth (Phase 014) and `provider_id="anthropic.api_key"` for the direct-console plain key (Phase 018), mirroring the dotted-namespace pattern already established by `google.gemini_cli` / `google.antigravity` / `github.copilot`. This audit confirms nothing else in the auth subsystem hard-codes `"anthropic"` as the *only* Anthropic provider key.

**grep results** (`grep -rn "anthropic" src/state_core/auth/ --include="*.py"`):

| File | Line | Context | Hard-coded "anthropic"? | Status |
|------|------|---------|-------------------------|--------|
| `base.py` | 78 | docstring example: `'anthropic', 'google.gemini_cli', …` | docstring only | **safe** — comment, not code |
| `base.py` | 101 | docstring example: `'anthropic', 'openai', 'google', …` | docstring only | **safe** — comment, not code (and it lists `'openai'` already, so adding `'anthropic.api_key'` is consistent with this comment's intent) |
| `base.py` | 181 | docstring: `(user-agent, x-app, anthropic-beta) byte-for-byte` | refers to header name | **safe** — header name, unrelated to provider_id |
| `errors.py` | 2, 14, 18, 23 | docstrings about Phase 014 history | docstring only | **safe** |
| `providers/anthropic.py` | 295, 447 | `provider_id="anthropic"` literal in `_to_credential` and `AnthropicAuth.provider_id` class attribute | yes, but **scoped to OAuth flow** | **safe** — Phase 014's OAuth provider claims `"anthropic"`, Phase 018's plain-key provider will claim `"anthropic.api_key"` (distinct bucket in `auth.json` — Phase 019 round-robin can never mix the two) |
| `providers/anthropic.py` | 548, 600, 659, 698, 710 | log event names + argparse prog string | log keys / CLI naming | **safe** — unrelated to vault provider_id |
| `refresh.py` | 132–293 | parametric `provider_id: str` in `_extract_cred`, `refresh_credential`, etc. | NO hard-coding | **safe** — fully parametric |

**Conclusion:** No code path hard-codes `"anthropic"` outside the OAuth provider's own module. The Phase 014 OAuth provider's `provider_id="anthropic"` literal is *correct and intentional* (it's that provider's identity); Phase 018 simply registers a *different* provider_id (`"anthropic.api_key"`) and the two coexist as distinct buckets in `vault.providers` — exactly the same shape as `google.gemini_cli` vs `google.antigravity`. Phase 019 round-robin operates inside one provider_id at a time, so OAuth + plain-key creds for "Anthropic the company" never mingle.

**Recommendation:** No refactor needed in Phases 011–017. Phase 018 just adds the new entry. Phase 022's CLI will need a small UX consideration: `state auth login anthropic` should disambiguate (offer both `anthropic` OAuth and `anthropic.api_key`); that's a Phase 022 concern, not 018.

## Module Shape Reference

Phase 018 follows the Phase 014–017 OAuth provider module-layout precedent, *adapted* for the registry-driven shape (no per-provider OAuth flow):

| Section | OAuth precedent (anthropic.py) | Phase 018 plain-key shape |
|---------|-------------------------------|---------------------------|
| Module docstring | ~50 lines: cardinal rules, references to RESEARCH.md, history | ~40 lines: cardinal rules (mode-isolation, secret hygiene, registry ordering invariant), pointer to 018-RESEARCH.md |
| `print = print` re-bind | yes (testability — monkeypatch in tests) | yes (mirror precedent) |
| Imports | stdlib + httpx + pydantic + structlog + state_core.auth.{base, refresh, errors, oauth_common.*} | stdlib + pydantic + structlog + state_core.auth.{base, errors}. **NO httpx, NO oauth_common, NO refresh** (no I/O in this module). |
| Constants block | URLs, scopes, client_id, headers | NONE — all constants live inside the registry rows |
| Pydantic models | TokenResponse + sub-models | `ApiKeyProviderSpec` (frozen, extra="forbid") |
| Helpers | `_to_credential`, `_build_authorize_url`, `_exchange_code` (sync where pure, async where I/O) | `_validate_format(key: str) -> None` (raises on empty/whitespace), `_warn_prefix_mismatch(provider_id, key, spec)` (logs once) |
| AuthMethod class | `AnthropicAuth`, `GoogleGeminiAuth`, etc. — one per provider, each with `provider_id: str = "..."` class attr | ONE class `PlainApiKeyAuth` with `provider_id: str` instance attr (set in `__init__` from registry lookup) |
| Sync methods | `is_token`, `is_expired`, `http_headers` | `is_token` (delegates to `spec.key_prefixes`), `is_expired` (always False), `http_headers` (renders `spec.auth_header` template) |
| Async methods | `login`, `refresh` — full HTTP flows | `login` (getpass/stdin → `_validate_format` → `ApiKeyCredential`), `refresh` (returns `cred` unchanged) |
| Public factory | none (class is the surface) | `get_api_key_auth(provider_id) -> AuthMethod` — raises `UnknownApiKeyProviderError` on miss |
| `__all__` | provider_id, classes, exceptions, helpers | `_REGISTRY`, `ApiKeyProviderSpec`, `PlainApiKeyAuth`, `get_api_key_auth`, `UnknownApiKeyProviderError`, `iter_known_prefixes` (Phase 020 consumer) |
| `__main__` argparse | login [+refresh in 015–017] | login only (CONTEXT.md: list/refresh are Claude's discretion — see §below) |

**File-size sanity check (LOC budget):**
- Module docstring + imports: ~80 LOC
- `ApiKeyProviderSpec`: ~30 LOC
- `_REGISTRY` (12 rows × ~6 lines incl. provenance comment): ~80 LOC
- Helpers: ~40 LOC
- `PlainApiKeyAuth` class: ~120 LOC
- `get_api_key_auth` + `UnknownApiKeyProviderError` + `iter_known_prefixes`: ~30 LOC
- `__main__` argparse: ~50 LOC
- **Total: ~430 LOC** — well under the 600-LOC threshold for promoting to a package. Single file `providers/api_key.py` is correct.

**Test layout reference:**
- `tests/auth/providers/test_anthropic.py` is 534 LOC for one provider with full HTTP mocking.
- `tests/auth/providers/test_github_copilot.py` is 1068 LOC for one provider with sequenced HTTP mocking.
- Phase 018 has zero outbound HTTP and 12 trivial-shape providers — the parameterized layout will be ~300–400 LOC total for `test_api_key.py` + ~150 LOC for `test_loader.py` + ~100 LOC for `test_main.py`. Under 700 LOC of tests for the whole phase.

**conftest reuse:** The existing `tests/auth/providers/conftest.py` provides `mock_getpass` (Phase 014) — reusable by patching `state_core.auth.providers.api_key.getpass.getpass`. Phase 018 should add a `monkeypatch_env` fixture (param: env-var name → value) and a `provider_id_factory` parameterization helper.

## __main__ Argparse Surface

CONTEXT.md says `login` is required; `list` and `refresh` are Claude's discretion. Recommendation:

```
python -m state_core.auth.providers.api_key login <provider_id> [--replace]
python -m state_core.auth.providers.api_key list
python -m state_core.auth.providers.api_key refresh <provider_id> [--idx N]   # ALIAS — no-op
```

**Subcommand decisions:**

1. **`login <provider_id>` — REQUIRED, ship it.**
   - Positional `provider_id`. Required. argparse choices=`list(_REGISTRY)` so unknown providers fail at parse time with the full list.
   - `--replace` flag (default False) → truncate provider's vault entry to single new credential; default is append.
   - NO `--api-key` flag (P0-12 secret-hygiene cardinal rule — argv leakage).
   - Reads via `getpass.getpass()` on TTY, `sys.stdin.readline().rstrip("\n")` on non-TTY (CI path: `echo $KEY | python -m … login openai`).
   - Persists via `store.ensure_initialized` + `store.load_vault` + append-with-dedup + `store.save_vault` — mirrors Phase 017's pattern exactly (github_copilot.py:836–843).
   - Exit codes: 0=success, 1=AuthLoginError/UnknownApiKeyProviderError, 2=argparse usage, 130=SIGINT.

2. **`list` — OPTIONAL, recommend YES.**
   - Prints each registry row: `provider_id  ENV_VAR  prefixes  header_name`. One line per provider, tab-aligned.
   - Useful for discoverability ("which providers does this support?"), 100% offline, ~10 LOC of code.
   - Phase 022's `state auth status` is a *richer* surface (per-provider cred count, env-var presence, etc.); `list` here is the dev-loop smoke version.

3. **`refresh <provider_id>` — OPTIONAL, recommend YES with no-op semantics.**
   - Mirrors the OAuth providers' `refresh` subcommand surface (Phase 015–017 all have one) for *symmetry*.
   - For api_key creds, `PlainApiKeyAuth.refresh(cred)` returns cred unchanged. The CLI prints `"API key credentials never expire — nothing to refresh."` and returns 0.
   - Alternative (rejected): raise `NotImplementedError`. Risk: shell scripts iterating providers would break. The no-op pass is friendlier and mirrors the `is_expired → False` invariant.

**Module-execution path:** `python -m state_core.auth.providers.api_key` works because the module has an `if __name__ == "__main__": sys.exit(_main())` block. This is THE Phase 018 smoke surface for pre-Phase-022 dogfooding (12 providers × interactive login = a real ergonomic test).

## state_core.auth.loader Placement

CONTEXT.md is explicit: imports = stdlib + `state_core.auth.base` + `state_core.auth.store` + `state_core.auth.providers.api_key._REGISTRY` only. The placement question is *where in the package tree* and *which direction* the import edge goes.

**Recommended placement: `src/state_core/auth/loader.py`** (sibling of `base.py`, `store.py`, `refresh.py`, `errors.py`; *not* under `providers/`).

```
src/state_core/auth/
├── __init__.py
├── base.py          # Phase 011 — Credential + AuthMethod (foundation)
├── errors.py        # Phase 015 — AuthError hierarchy
├── store.py         # Phase 012 — auth.json round-trip
├── refresh.py       # Phase 013 — filelock-guarded refresh
├── loader.py        # Phase 018 — NEW — vault > env synthesis
├── oauth_common/    # Phase 014/015 — PKCE + loopback
└── providers/
    ├── __init__.py
    ├── anthropic.py
    ├── google_gemini.py
    ├── antigravity.py
    ├── github_copilot.py
    └── api_key.py   # Phase 018 — NEW — registry + PlainApiKeyAuth
```

**Why not under `providers/`?**
- `loader.py` is *orchestration* (vault + env-fallback fusion), not a *provider implementation*. Putting it next to `store.py` and `refresh.py` matches the "I/O orchestrators live at the auth-module top level" pattern.
- Phase 022 will import from `state_core.auth.loader`; that import path reads as "load credentials" (correct mental model), not "load credentials from a provider" (misleading).

**Import-graph one-way edge (CRITICAL — circular-import safety):**

```
loader.py  ──imports──▶  providers/api_key.py
providers/api_key.py  ──MUST NOT IMPORT──▶  loader.py
```

The asymmetry is non-negotiable. Reasoning:

1. `providers/api_key.py` is the *data layer* — `_REGISTRY` is the canonical spec for the 12 providers. It has no I/O concern beyond `login()`'s getpass call.
2. `loader.py` is the *fusion layer* — it reads `_REGISTRY` to know which env-var to look up per `provider_id`. It does NOT need to expose anything back to `api_key.py`.
3. Reversing the edge (`api_key.py` → `loader.py`) would mean `PlainApiKeyAuth` knows about vault-vs-env precedence, which violates separation of concerns and creates a circular import the moment `loader.py` imports `providers/api_key._REGISTRY`.

**Concrete imports inside `loader.py`:**

```python
from __future__ import annotations
import os
from state_core.auth.base import ApiKeyCredential, Credential
from state_core.auth.store import AuthVaultPermissionError, get_auth_json_path, load_vault
from state_core.auth.providers.api_key import _REGISTRY, UnknownApiKeyProviderError
```

**Concrete absence inside `providers/api_key.py`:** must NOT contain `from state_core.auth.loader import ...`. A unit test SHOULD enforce this:

```python
def test_api_key_does_not_import_loader() -> None:
    src = (Path(state_core.auth.providers.api_key.__file__)).read_text()
    assert "from state_core.auth.loader" not in src
    assert "import state_core.auth.loader" not in src
```

This kind of import-graph assertion already has precedent in the repo (CI import-graph lint per CLAUDE.md mode-isolation rule).

**Re-exports:** `state_core/auth/__init__.py` already establishes the pattern that providers are NOT re-exported from the auth package root. `loader.py` is *orchestration* and *should* be re-exported: `from state_core.auth import load_credentials` is the public API surface for Phase 022.

## Test Scaffolding Recommendation

**Layout (3 files under `tests/auth/providers/` and `tests/auth/`):**

```
tests/auth/providers/test_api_key.py      # Phase 018 main test surface — parameterized over the 12-row registry
tests/auth/test_loader.py                 # Phase 018 — vault/env precedence
tests/auth/providers/test_api_key_main.py # Phase 018 — argparse __main__ surface
```

**`test_api_key.py` — parameterized over `_REGISTRY`:**

- `pytest.mark.parametrize("provider_id", list(_REGISTRY))` for every test that's table-driven (12 rows, one assertion per row, 1 test definition per behaviour).
- Per-provider tests:
  - `test_get_api_key_auth_returns_auth_method` — `isinstance(auth, AuthMethod)` for all 12.
  - `test_is_expired_always_false` — `auth.is_expired(cred, now)` returns False regardless of `now`.
  - `test_refresh_returns_cred_unchanged` — `await auth.refresh(cred) is cred` (or `==`, since frozen Pydantic).
  - `test_http_headers_renders_template` — every provider's `http_headers(cred)` matches `(name, value.format(key=cred.key))`.
  - `test_is_token_matches_known_prefix_and_rejects_others` — only for providers with non-empty `key_prefixes`.
- Non-parameterized tests:
  - `test_unknown_provider_id_raises_UnknownApiKeyProviderError`.
  - `test_registry_iteration_order_resolves_sk_collision` — iterate `_REGISTRY`, collect `sk-`-prefixed entries, assert descending prefix length.
  - `test_registry_provenance_comments_present` — read `api_key.py` source, assert each registry row has a `# captured ` comment.
  - `test_validate_format_rejects_empty_and_whitespace` — `("", " ", "\n", "\t\t")` all raise `AuthLoginError`.
  - `test_login_warn_and_store_on_prefix_mismatch` — capture structlog, supply a key with wrong prefix, assert warning emitted AND credential returned (not raised).
  - `test_login_dedup_on_repeat_same_key` — Phase 022's territory but smoke here.

**`test_loader.py` — vault/env precedence matrix (4 cells × 12 providers, mostly parameterized):**

| vault state | env var state | expected result |
|-------------|---------------|-----------------|
| has 1+ creds for provider_id | unset | vault creds (env ignored) |
| has 1+ creds for provider_id | set | vault creds (env ignored — vault wins) |
| empty list / missing key | set | `[ApiKeyCredential(env value)]` (synthesized, ephemeral) |
| empty list / missing key | unset | `[]` (no error) |
| auth.json file missing entirely | set | synthesized (FileNotFoundError handled like missing key) |
| auth.json file missing entirely | unset | `[]` |
| env value is empty string `""` | n/a | treated as unset (12-factor) |
| env value is whitespace-only | n/a | (Claude's discretion — recommend strip + treat empty as unset) |

Use `tmp_path` + monkeypatched `STATE_AUTH_JSON` for vault path; `monkeypatch.setenv` for env vars; existing `clean_state_auth_json_env` autouse fixture from `tests/auth/conftest.py` for isolation.

**`test_api_key_main.py` — argparse surface (no HTTP, no asyncio.run side-effects on real auth.json):**

- `test_login_unknown_provider_fails_at_argparse` — argparse `choices=` rejects pre-registry.
- `test_login_via_stdin_pipe` — feed key via `monkeypatch.setattr("sys.stdin", io.StringIO("sk-test\n"))`.
- `test_login_via_getpass` — patch `state_core.auth.providers.api_key.getpass.getpass`.
- `test_login_no_api_key_flag_exists` — argparse `--api-key` MUST raise SystemExit (unrecognized arg).
- `test_login_replace_truncates` and `test_login_default_appends` — round-trip through real `auth.json` in tmp_path.
- `test_login_dedup_on_identical_key` — append same key twice, vault contains 1 entry.
- `test_list_subcommand_prints_all_12_providers` — capsys + assert each provider_id appears.
- `test_refresh_subcommand_is_noop_for_api_key` — exit 0, friendly message.
- `test_keyboard_interrupt_returns_130` — patch getpass to raise KeyboardInterrupt.

**Tooling decisions:**
- **`pytest-httpx`: NO.** Phase 018 has zero outbound HTTP. Inheriting it from `tests/auth/providers/conftest.py` is fine if the autouse `httpx_mock` fixture is `non_mocked_hosts=[]`-tolerant; otherwise scope it to the OAuth-provider test files only.
- **`hypothesis`: NO.** The failure surface is enumerable (12 providers × 4 precedence cells × small set of input shapes). Hypothesis would add complexity without finding additional bugs.
- **`pytest.mark.parametrize`: YES, primary tool.** Parameterize over `_REGISTRY` keys; some tests will additionally parameterize over the `(prefix_match_or_mismatch)` axis.
- **`structlog.testing.capture_logs`: YES.** Required for `test_login_warn_and_store_on_prefix_mismatch`.

## Validation Architecture (Nyquist)

`workflow.nyquist_validation: true` in `.planning/config.json` — this section is REQUIRED.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ + pytest-asyncio 1.3+ + pytest-httpx (provider-test scoped only — Phase 018 doesn't use it) |
| Config file | `pyproject.toml` (existing — Phase 014–017) |
| Quick run command | `pytest tests/auth/providers/test_api_key.py tests/auth/test_loader.py -x -q` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-05 | Vault round-trip preserves api_key creds for all 12 providers | unit (parametrize) | `pytest tests/auth/providers/test_api_key.py::test_vault_roundtrip_preserves_api_key_credential -x` | ❌ Wave 0 |
| AUTH-05 | Empty/whitespace key rejected at login | unit | `pytest tests/auth/providers/test_api_key.py::test_validate_format_rejects_empty_and_whitespace -x` | ❌ Wave 0 |
| AUTH-05 | Prefix mismatch warns-and-stores (no raise) | unit | `pytest tests/auth/providers/test_api_key.py::test_login_warn_and_store_on_prefix_mismatch -x` | ❌ Wave 0 |
| AUTH-05 | Unknown provider_id raises UnknownApiKeyProviderError | unit | `pytest tests/auth/providers/test_api_key.py::test_unknown_provider_id_raises -x` | ❌ Wave 0 |
| AUTH-05 | Vault has cred → vault wins (env ignored) | unit | `pytest tests/auth/test_loader.py::test_vault_wins_when_present -x` | ❌ Wave 0 |
| AUTH-05 | Vault empty + env set → synthesizes ephemeral cred | unit | `pytest tests/auth/test_loader.py::test_env_synthesis_when_vault_empty -x` | ❌ Wave 0 |
| AUTH-05 | Vault file missing + env set → synthesizes ephemeral cred | unit | `pytest tests/auth/test_loader.py::test_env_synthesis_when_vault_file_missing -x` | ❌ Wave 0 |
| AUTH-05 | Vault missing + env unset → returns [] (no error) | unit | `pytest tests/auth/test_loader.py::test_returns_empty_when_neither_present -x` | ❌ Wave 0 |
| AUTH-05 | Env value empty string treated as unset | unit | `pytest tests/auth/test_loader.py::test_empty_env_var_treated_as_unset -x` | ❌ Wave 0 |
| AUTH-05 | Repeat login appends by default | integration (tmp_path vault) | `pytest tests/auth/providers/test_api_key_main.py::test_login_default_appends -x` | ❌ Wave 0 |
| AUTH-05 | --replace flag truncates to single entry | integration (tmp_path vault) | `pytest tests/auth/providers/test_api_key_main.py::test_login_replace_truncates -x` | ❌ Wave 0 |
| AUTH-05 | Identical key dedup'd on repeat login | integration | `pytest tests/auth/providers/test_api_key_main.py::test_login_dedup_on_identical_key -x` | ❌ Wave 0 |
| AUTH-05 | sk- collision: longest-prefix-first ordering | unit | `pytest tests/auth/providers/test_api_key.py::test_registry_sk_collision_ordering -x` | ❌ Wave 0 |
| AUTH-05 | http_headers renders template per provider | unit (parametrize 12) | `pytest tests/auth/providers/test_api_key.py::test_http_headers_renders_template -x` | ❌ Wave 0 |
| AUTH-05 | is_expired always False for ApiKeyCredential | unit (parametrize 12) | `pytest tests/auth/providers/test_api_key.py::test_is_expired_always_false -x` | ❌ Wave 0 |
| AUTH-05 | refresh(cred) returns cred unchanged | unit (parametrize 12) | `pytest tests/auth/providers/test_api_key.py::test_refresh_returns_cred_unchanged -x` | ❌ Wave 0 |
| AUTH-05 | __main__ argparse: no --api-key flag | unit | `pytest tests/auth/providers/test_api_key_main.py::test_login_no_api_key_flag_exists -x` | ❌ Wave 0 |
| AUTH-05 | __main__ argparse: getpass on TTY | unit | `pytest tests/auth/providers/test_api_key_main.py::test_login_via_getpass -x` | ❌ Wave 0 |
| AUTH-05 | __main__ argparse: stdin on non-TTY | unit | `pytest tests/auth/providers/test_api_key_main.py::test_login_via_stdin_pipe -x` | ❌ Wave 0 |
| AUTH-05 | Mode isolation: api_key.py imports nothing from loader | unit (import lint) | `pytest tests/auth/providers/test_api_key.py::test_api_key_does_not_import_loader -x` | ❌ Wave 0 |
| AUTH-05 | Provenance comments present on all 12 registry rows | unit (source-text inspection) | `pytest tests/auth/providers/test_api_key.py::test_registry_provenance_comments -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/auth/providers/test_api_key.py tests/auth/test_loader.py tests/auth/providers/test_api_key_main.py -x -q`
- **Per wave merge:** `pytest tests/auth/ -x`
- **Phase gate:** Full `pytest tests/ -x` green before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `tests/auth/providers/test_api_key.py` — parameterized RED stubs covering AUTH-05 unit rows above (~25 stubs)
- [ ] `tests/auth/test_loader.py` — RED stubs for vault/env precedence matrix (~10 stubs)
- [ ] `tests/auth/providers/test_api_key_main.py` — RED stubs for argparse surface (~10 stubs)
- [ ] Extension to `tests/auth/providers/conftest.py` — `monkeypatch_env` fixture, `provider_id_factory` parameterization helper, `mock_stdin_pipe` fixture for non-TTY login path
- [ ] Framework install: NONE — pytest 8.4+ already in use across Phases 011–017.

### Failure Modes Phase 018 MUST Prove It Survives

(consolidated, per CONTEXT.md and audit) — every item below has a corresponding row above:

1. Empty / whitespace-only key → `AuthLoginError` raised at format validation. **unit**
2. Prefix mismatch → structlog warning emitted, credential returned unchanged (warn-and-store). **unit**
3. Unknown provider_id → `UnknownApiKeyProviderError` from `get_api_key_auth`. **unit**
4. Vault present + non-empty list for provider → vault wins (env ignored). **unit**
5. Vault present + empty list / missing bucket for provider + env set → synthesize ephemeral cred. **unit**
6. Vault file missing entirely + env set → synthesize (treat FileNotFoundError identically to missing bucket). **unit**
7. Vault missing + env unset → return `[]` (no error). **unit**
8. Env value is empty string `""` → treated as unset (12-factor). **unit**
9. Append-default repeat login → vault gains a 2nd entry. **integration (tmp_path vault)**
10. `--replace` repeat login → vault contains exactly the new entry. **integration (tmp_path vault)**
11. Same key string login twice → dedup, vault contains 1 entry. **integration (tmp_path vault)**
12. Longest-prefix-first sniff: `sk-ant-api03-XXX` resolves to `anthropic.api_key`, `sk-or-v1-XXX` to `openrouter`, `sk-proj-XXX` to `openai`, bare `sk-XXX` to `openai`. **unit (parametrize)**
13. `http_headers(cred)` injection per provider matches the registry's `auth_header` template byte-for-byte. **unit (parametrize 12)**
14. `is_expired(cred, now)` always returns False for `ApiKeyCredential`. **unit (parametrize 12)**
15. `refresh(cred)` returns `cred` unchanged. **unit (parametrize 12)**
16. Mode-isolation invariant: `providers/api_key.py` does not import `state_core.auth.loader`. **unit (import-graph lint)**
17. `__main__` accepts no `--api-key` flag. **unit (argparse SystemExit on `--api-key`)**
18. `__main__` reads via getpass on TTY, stdin on non-TTY. **unit**
19. Registry ordering invariant: all `sk-`-prefixed providers appear in descending prefix length. **unit (source inspection)**
20. Registry provenance: every row has a `# captured 2026-04-30 from <url>` comment. **unit (source inspection)**

## Security Threat Inputs (ASVS L1)

Ready to be lifted into PLAN.md's `<threat_model>` block:

- **T-018-1: Secret in argv** — `--api-key <key>` flag would leak the key to `ps`, shell history, `script(1)` recordings, Mac unified logs. **Mitigation:** No `--api-key` flag exists. Login reads via `getpass` on TTY, single-line `stdin` on non-TTY. CONTEXT.md locked. Test: `test_login_no_api_key_flag_exists` asserts argparse rejects it. ASVS V8.3.4.
- **T-018-2: Secret in error messages / repr** — exception strings or `repr(cred)` could include the key bytes. **Mitigation:** `ApiKeyCredential.key: str = Field(repr=False)` (already enforced by Phase 011). Phase 018's exceptions (e.g. `UnknownApiKeyProviderError`) MUST NOT carry the key in their message. Test: `repr(cred)` must not contain the key string. ASVS V8.2.1, V7.4.1.
- **T-018-3: Secret in logs** — structlog records, especially the prefix-mismatch warning, could leak the full key. **Mitigation:** Phase 018 logs only `observed_prefix=key[:8]` (first 8 chars), never the full key. Phase 020's root-logger redactor is the second defense layer; Phase 018 *contributes* the prefix data the redactor consumes. Test: capture structlog output during prefix-mismatch path, assert no full-key substring. ASVS V8.3.5.
- **T-018-4: Prefix-rejection brick on vendor rotation** — hard-rejecting unknown prefixes (e.g., when OpenAI rolled out `sk-proj-` in 2024) would lock users out. **Mitigation:** warn-and-store. The registry's `key_prefixes` is *informational* for routing/redaction, not a gate. Test: `test_login_warn_and_store_on_prefix_mismatch` uses a deliberately-wrong prefix. ASVS V1.5.1.
- **T-018-5: Cross-provider env-var leak** — `OPENAI_API_KEY` accidentally being used as the Anthropic key (e.g., user setting both). **Mitigation:** `loader.load_credentials(provider_id)` only consults `_REGISTRY[provider_id].env_var`. Env never participates in round-robin. Provider-id-keyed lookup is the boundary. Test: `test_loader.py` parameterized over the 12 providers, only the matching env var is consulted. ASVS V1.4.5.
- **T-018-6: chmod-0600 enforcement on auth.json reads** — vault file with wrong mode is a security incident. **Mitigation:** Already enforced by Phase 012's `store._verify_mode` on every read. Phase 018 inherits this; its `loader.py` calls `load_vault(path)` which propagates `AuthVaultPermissionError` up to the caller. Test: provoke a wrong-mode auth.json, assert `loader.load_credentials` re-raises. ASVS V14.1.5.
- **T-018-7: Circular dependency between loader.py and api_key.py** — would cause runtime ImportError under certain import orders. **Mitigation:** One-way edge — `loader.py` imports `_REGISTRY` from `api_key.py`, never the reverse. Architectural constraint. Test: `test_api_key_does_not_import_loader` greps the source. ASVS V14.2.1 (modular architecture).
- **T-018-8: Vault-file race during append** — concurrent `state auth login` + `state auth refresh` could clobber. **Mitigation:** OUT OF SCOPE for Phase 018. Phase 013's `filelock`-guarded refresh covers refresh. Phase 022's CLI handler will need the same lock around login persistence. Phase 018's `__main__` is a *smoke surface* — single-user, single-process; race risk acceptable here. Documented as a known gap.
- **T-018-9: Symlink attack on auth.json** — already documented as out-of-scope in Phase 012's `store.py` docstring (Phase 022 audit owns O_NOFOLLOW + lstat). Phase 018 inherits the gap; documented as a known gap.
- **T-018-10: ephemeral env-cred persistence regression** — a future refactor accidentally writing env-synthesized creds into the vault would create the "env was wrong, now it's stuck" footgun CONTEXT.md flagged. **Mitigation:** `loader.load_credentials` returns the synthesized cred WITHOUT calling `save_vault`. Test: assert vault file unchanged after `load_credentials` synthesizes from env. ASVS V8.3.7.

## Open Questions / Risks

1. **Cohere env-var: `COHERE_API_KEY` vs `CO_API_KEY`.** CONTEXT.md says "researcher confirms exact canonical spelling". The Cohere Python SDK reads `CO_API_KEY`; the broader ecosystem (litellm, AutoGen, AG2, n8n, langchain, OpenClaw) reads `COHERE_API_KEY`. **Recommendation:** ship `COHERE_API_KEY` (12-factor canonical, ecosystem-aligned). Document the SDK-divergence in the registry row's `notes`. If a real user reports pain, Phase 022 can add `CO_API_KEY` as an alias env var. **Confidence: MEDIUM.** Decision lives with the planner / user; flagging here for visibility.

2. **Google AI Studio env-var: `GEMINI_API_KEY` vs `GOOGLE_API_KEY`.** Google's official SDK supports both, with `GOOGLE_API_KEY` taking precedence when both are set. CONTEXT.md says `GEMINI_API_KEY`. **Recommendation:** ship `GEMINI_API_KEY` as the registry's canonical env-var name (it's the Gemini-specific spelling, less collision-prone with general "Google" tooling like Cloud Storage / GCS / etc.). Document in `notes` that Google's SDK also accepts `GOOGLE_API_KEY` — Phase 022 can add it as alias if asked. **Confidence: MEDIUM.**

3. **Google AI Studio key prefix: unknown.** ai.google.dev does not publish a stable key prefix. **Recommendation:** registry value `()` — `is_token` returns False; warn-and-store on any key. Acceptable. **Confidence: HIGH for the placeholder; LOW for any future routing-by-prefix logic.**

4. **DeepSeek/Together/Mistral/Cohere/Cerebras prefixes: unknown.** Vendor docs do not publish stable prefixes. Some third-party detectors claim "co_" + 48 chars for Cohere, but unverified against official docs. **Recommendation:** register `()` for all. Phase 020's redactor will key off these provider-id mappings via the SDK env-var name and/or the vault provider-id; missing prefix means the redactor can't auto-detect bare keys, but explicit `provider_id`-keyed redaction still works. **Confidence: HIGH for the omission; the absence is the right answer.**

5. **Anyscale Endpoints status:** Some 2024 sources note Anyscale wound down its public Endpoints product. Their API may be in long-tail maintenance. **Recommendation:** keep `anyscale` in the registry per CONTEXT.md (12-provider lockdown), but the implementer can flag the row's `notes` field with "Endpoints product status uncertain as of 2026-04-30; verify before relying on this provider in production". **Confidence: LOW about availability; HIGH that the registry shape is correct either way.**

6. **`refresh` __main__ subcommand semantics:** Recommend no-op (returns 0 with friendly message). Risk: tooling that calls `state auth refresh <provider>` for every provider in a loop will not error on api_key providers — that's the *desired* shape. Alternative (raise `NotImplementedError`) would force callers to special-case api_key providers, which is worse UX. **Confidence: MEDIUM.** Final call is Claude's discretion per CONTEXT.md.

7. **structlog redactor coupling (Phase 020):** Phase 020 will consume `_REGISTRY` (or a derived `iter_known_prefixes()` helper) to build its regex set. Phase 018 should export `iter_known_prefixes() -> Iterator[str]` to give Phase 020 a stable surface that doesn't depend on `_REGISTRY`'s internal shape. **Confidence: HIGH.** Recommend implementing.

## Sources

### Primary (HIGH confidence)
- platform.claude.com/docs/en/api/getting-started — Anthropic API key + `x-api-key` header [verified 2026-04-30]
- ai.google.dev/gemini-api/docs/api-key — Gemini env vars + `x-goog-api-key` header [verified 2026-04-30]
- console.groq.com/docs/quickstart + production-readiness/security-onboarding — Groq `gsk_` + `GROQ_API_KEY` + Bearer [verified 2026-04-30]
- api-docs.deepseek.com/ — DeepSeek `DEEPSEEK_API_KEY` + Bearer [verified 2026-04-30]
- docs.together.ai/docs/quickstart — Together `TOGETHER_API_KEY` + Bearer [verified 2026-04-30]
- docs.anyscale.com/endpoints/text-generation/authenticate/ — Anyscale `esecret_` + Bearer [verified 2026-04-30]
- docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key — Mistral `MISTRAL_API_KEY` + Bearer [verified 2026-04-30]
- docs.cohere.com/reference/about — Cohere Bearer (env-var SDK divergence noted) [verified 2026-04-30]
- openrouter.ai/docs/api/reference/authentication — OpenRouter `sk-or-v1-` + `OPENROUTER_API_KEY` + Bearer [verified 2026-04-30]
- docs.x.ai/developers/quickstart — xAI `XAI_API_KEY` + Bearer [verified 2026-04-30]
- inference-docs.cerebras.ai/api-reference/authentication — Cerebras `CEREBRAS_API_KEY` + Bearer [verified 2026-04-30]
- `src/state_core/auth/base.py` — Phase 011 ApiKeyCredential + AuthMethod Protocol
- `src/state_core/auth/store.py` — Phase 012 vault round-trip + chmod-0600
- `src/state_core/auth/errors.py` — Phase 015 AuthError hierarchy
- `src/state_core/auth/providers/{anthropic,google_gemini,antigravity,github_copilot}.py` — module-shape precedent

### Secondary (MEDIUM confidence)
- platform.openai.com/docs/api-reference/authentication — direct fetch returned 403; OpenAI key prefix shape (`sk-proj-`/`sk-svcacct-`/`sk-None-`/`sk-`) verified via OpenAI Developer Community threads + multiple SDK README files. Bearer auth is universally observed.
- Cohere `CO_API_KEY` vs `COHERE_API_KEY` env-var divergence — multiple ecosystem sources

### Tertiary (LOW confidence — flagged for future verification)
- Cohere "co_" + 48-char key format — repeated across third-party detectors (GitGuardian, Nightfall, trevorfox tester); not officially documented by Cohere.
- Anyscale Endpoints product viability — historic docs only; product status uncertain.

## Metadata

**Confidence breakdown:**
- Provider Registry Table: HIGH for env-vars + auth-headers; MEDIUM for prefixes (some vendors don't publish — `()` is the right value)
- Header Table Verification: HIGH — every provider verified against official docs
- sk- Collision Resolution: HIGH — algorithm + ordering is mechanical
- Namespacing Audit: HIGH — grep + read of every auth-subsystem file
- Module Shape Reference: HIGH — direct read of Phase 014–017 source
- __main__ Argparse Surface: HIGH — directly mirrors Phase 015–017 precedent
- loader.py Placement: HIGH — directional import is a hard architectural constraint
- Test Scaffolding: HIGH — pytest 8.4+ + parametrize is the established repo pattern
- Validation Architecture: HIGH — every row maps to a concrete test command
- Threat Inputs: HIGH — every threat has an existing or new mitigation

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days — vendor key prefix changes are the most likely drift; treat the registry's provenance comments as the live audit trail)
