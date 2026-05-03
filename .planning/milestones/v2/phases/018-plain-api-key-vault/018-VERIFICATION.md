---
phase: 018-plain-api-key-vault
verified: 2026-04-30T19:40:00Z
status: passed
score: 9/9 must-haves verified
re_verification:
  is_re_verification: false
---

# Phase 018: Plain API-Key Vault Verification Report

**Phase Goal:** Implement a plain-API-key vault provider (`state_core.auth.providers.api_key`) and credential loader (`state_core.auth.loader`) that fuses Phase 012's vault round-trip with a 12-row provider registry to deliver requirement AUTH-05 — vault-vs-env precedence and a single canonical `load_credentials(provider_id)` entry point for downstream milestones.

**Verified:** 2026-04-30T19:40:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                          | Status     | Evidence                                                                                                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 12 provider_ids registered with verified env-vars, headers, and prefixes (Plan 02 truth)        | VERIFIED   | `len(_REGISTRY) == 12`; insertion order matches canonical tuple; 12 provenance comments (`# captured 2026-04-30 from <url>`); 12 `ApiKeyProviderSpec(` row literals at lines 142–251 of `api_key.py`                       |
| 2   | _REGISTRY iteration order resolves the sk- collision (longest-prefix-first across providers)    | VERIFIED   | `iter_known_prefixes()` yields `['sk-ant-api03-', 'sk-or-v1-', 'sk-or-', 'sk-svcacct-', 'sk-proj-', 'sk-None-', 'sk-', ...]` — `test_sniff_resolves_sk_collision` GREEN                                                  |
| 3   | PlainApiKeyAuth structurally satisfies @runtime_checkable AuthMethod (5-method Protocol)        | VERIFIED   | `isinstance(get_api_key_auth(pid), AuthMethod)` is True for every pid; smoke ran live across all 12                                                                                                                       |
| 4   | get_api_key_auth raises UnknownApiKeyProviderError; subclass of AuthError; key never in message | VERIFIED   | Live smoke: `get_api_key_auth('not-real')` raises `UnknownApiKeyProviderError(provider_id='not-real')`; `isinstance(exc, AuthError)`; `"key=" not in str(exc)` — `errors.py:69-93`                                        |
| 5   | load_credentials: vault wins; env synthesizes when vault empty/missing; 12-factor empty=unset    | VERIFIED   | Live smoke roundtrip in tmp_path proved 3-cell precedence matrix; `test_vault_wins_over_env`, `test_env_synthesizes_when_vault_*`, `test_empty_env_treated_as_unset` all GREEN; vault file unchanged after env synthesis  |
| 6   | Synthesized credentials are NEVER persisted (T-018-10)                                          | VERIFIED   | `loader.py` contains 0 references to `save_vault`/`ensure_initialized`; live smoke confirmed `not vault_path.exists()` after env-only synthesis                                                                            |
| 7   | Cross-provider env-var leak prevented — load_credentials consults ONLY _REGISTRY[pid].env_var   | VERIFIED   | `test_loader_consults_only_matching_env_var` parametrized over 12 providers (24 sub-checks); single `os.environ.get(spec.env_var, "")` access in `loader.py:142`                                                          |
| 8   | One-way import edge: api_key.py MUST NOT import loader; loader.py imports only allowed targets  | VERIFIED   | `grep -n "from state_core.auth.loader\|import state_core.auth.loader" src/state_core/auth/providers/api_key.py` returns 0; `loader.py` imports only from base/errors/providers.api_key/store; both directions GREEN      |
| 9   | __main__ argparse exposes login + list + refresh subcommands; exit codes 0/1/2/130; no --api-key | VERIFIED   | `python3 -m state_core.auth.providers.api_key list` emits 12 lines; smoke 2 demonstrates stdin pipe → vault chmod 600 with key absent from repr; `test_login_no_api_key_flag_exists` GREEN                                |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact                                          | Expected                                                                                                                  | Status     | Details                                                                                                                                       |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/auth/providers/api_key.py`        | 12-row _REGISTRY, ApiKeyProviderSpec, PlainApiKeyAuth, get_api_key_auth, iter_known_prefixes, _main; ≥380 LOC              | VERIFIED   | 607 LOC; 12 `ApiKeyProviderSpec(` row literals; 12 provenance comments; class definitions at lines 111 (Spec) and ~252 (PlainApiKeyAuth)       |
| `src/state_core/auth/errors.py`                   | Adds UnknownApiKeyProviderError to AuthError hierarchy                                                                    | VERIFIED   | 101 LOC; new class at lines 69-93; `__all__` updated to include it; `isinstance(UnknownApiKeyProviderError, AuthError)` confirmed live         |
| `src/state_core/auth/loader.py`                   | load_credentials(provider_id) — vault > env precedence with ephemeral env synthesis; ≥100 LOC                              | VERIFIED   | 169 LOC; single public function at line 80; module docstring documents the 6 resolution rules; 0 references to `save_vault`/`ensure_initialized` |
| `src/state_core/auth/__init__.py`                 | Re-export load_credentials at the auth-package public API surface                                                         | VERIFIED   | Line 22 imports `load_credentials`; line 64 includes it in `__all__`; `from state_core.auth import load_credentials` resolves to `loader.py`   |
| `tests/auth/test_api_key.py`                      | Wave 0 RED stubs for VALIDATION rows 01–03, 12–18, 20; ≥250 lines                                                          | VERIFIED   | File present, 305 LOC, 12 named test functions; all GREEN as of Plan 02                                                                       |
| `tests/auth/test_loader.py`                       | Wave 0 RED stubs for VALIDATION rows 04–08 (vault×env precedence); ≥120 lines                                              | VERIFIED   | File present, 218 LOC, 8 named test functions; all GREEN as of Plan 03                                                                        |
| `tests/auth/test_main_api_key.py`                 | Wave 0 RED stubs for VALIDATION rows 09–11, 19; ≥100 lines                                                                | VERIFIED   | File present, 246 LOC, 10 named test functions; all GREEN as of Plan 02                                                                       |
| `tests/auth/test_import_graph.py`                 | VALIDATION row 21 — providers/api_key.py MUST NOT import loader                                                           | VERIFIED   | File present, 81 LOC; both directional tests GREEN as of Plan 03                                                                              |

### Key Link Verification

| From                                       | To                                              | Via                                                       | Status   | Details                                                                                                                                |
| ------------------------------------------ | ----------------------------------------------- | --------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/auth/providers/api_key.py` | `src/state_core/auth/base.py`                   | `from state_core.auth.base import ApiKeyCredential, AuthMethod` | WIRED    | Imports both at module top; PlainApiKeyAuth structurally satisfies AuthMethod                                                            |
| `src/state_core/auth/providers/api_key.py` | `src/state_core/auth/errors.py`                 | `from state_core.auth.errors import AuthLoginError, UnknownApiKeyProviderError` | WIRED    | get_api_key_auth raises UnknownApiKeyProviderError; _validate_format raises AuthLoginError                                              |
| `src/state_core/auth/providers/api_key.py` | `src/state_core/auth/store.py`                  | Local import inside `_main()` only                        | WIRED    | Module-level grep returns 0 hits for `from state_core.auth.store`; the _main argparse block locally imports for vault persistence       |
| `src/state_core/auth/providers/api_key.py` | `src/state_core/auth/loader.py`                 | MUST NOT IMPORT (T-018-7)                                 | WIRED    | `grep -n "from state_core.auth.loader\|import state_core.auth.loader" src/state_core/auth/providers/api_key.py` returns 0 lines        |
| `src/state_core/auth/loader.py`            | `src/state_core/auth/providers/api_key.py`      | `from state_core.auth.providers.api_key import _REGISTRY`  | WIRED    | `loader.py:70`; one-way edge confirmed                                                                                                  |
| `src/state_core/auth/loader.py`            | `src/state_core/auth/store.py`                  | `from state_core.auth.store import AuthVaultPermissionError, get_auth_json_path, load_vault` | WIRED    | `loader.py:71-75`; only the read side imported (no `save_vault`/`ensure_initialized`)                                                  |
| `src/state_core/auth/loader.py`            | `src/state_core/auth/base.py`                   | `from state_core.auth.base import ApiKeyCredential, Credential` | WIRED    | `loader.py:68`; ApiKeyCredential constructed for env synthesis; Credential is the union return type                                     |
| `src/state_core/auth/__init__.py`          | `src/state_core/auth/loader.py`                 | `from state_core.auth.loader import load_credentials`     | WIRED    | `__init__.py:22`; aliased identity verified live (`load_credentials is direct`)                                                         |

### Requirements Coverage

| Requirement | Source Plan(s)             | Description                                                                                                                                                  | Status      | Evidence                                                                                                                                                                                                            |
| ----------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUTH-05     | 018-01, 018-02, 018-03, 018-04 | API key vault (plain keys for Anthropic, OpenAI, Google, DeepSeek, Groq, Together, Anyscale, Mistral, Cohere, OpenRouter, Grok, Cerebras)                    | SATISFIED   | All 12 named providers present in `_REGISTRY` with verified provenance URLs; live smoke confirmed end-to-end vault round-trip and env-fallback synthesis; 291/1-skipped pytest sweep on `tests/auth/`                |

No orphaned requirements. AUTH-05 is the only requirement claimed by every Phase 018 plan and is fully satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

None detected. No TODO/FIXME/PLACEHOLDER markers in the Phase 018 production files (`api_key.py`, `loader.py`, `errors.py`, `__init__.py`); no empty `return null/{}/[]` stubs in business logic; no console-log-only function bodies. The loader's `return []` on the no-creds path is the documented behavior, not a stub.

### Step 7b: Quality Findings

Skipped (quality.level: fast)

### Human Verification Required

None. All goal-achievement assertions are programmatically verifiable and have been demonstrated:
- 12 registry rows: in-source grep + live `_REGISTRY` introspection
- Header/prefix correctness: parametrized `test_http_headers` over 12 providers
- Vault-vs-env precedence: 5-cell matrix proven by `test_vault_wins_over_env` + `test_env_synthesizes_when_vault_*` + `test_empty_env_treated_as_unset` + live smoke roundtrip
- Secret hygiene (T-018-1/2/3/10): grep + live smoke (key absent from `repr(ApiKeyCredential)`, vault chmod 0600, no save_vault in loader)
- Import-graph (T-018-7): both directions verified by `test_import_graph.py`

### Gaps Summary

No gaps. Phase 018 ships a complete, registry-driven plain-API-key provider plus the canonical `load_credentials` orchestrator with the locked vault-wins-over-env precedence semantics. AUTH-05 is fully satisfied and the public API surface is frozen for downstream Phase 019 (multi-cred round-robin), Phase 020 (logger redactor), Phase 022 (CLI), and v3 (provider routing) consumption.

The deferred LOW threats (T-018-8 vault-file race, T-018-9 symlink attack) remain DEFERRED to Phase 022 as documented in the plans — these are not goal-achievement gaps for AUTH-05.

---

_Verified: 2026-04-30T19:40:00Z_
_Verifier: Claude (gsd-verifier)_
