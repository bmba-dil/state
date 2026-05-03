---
phase: 018-plain-api-key-vault
plan: 03
subsystem: auth
tags: [auth, api-key, wave-2, green, loader, env-fallback, vault-precedence]
dependency_graph:
  requires:
    - state_core.auth.base (ApiKeyCredential, Credential)
    - state_core.auth.errors (UnknownApiKeyProviderError)
    - state_core.auth.providers.api_key (_REGISTRY — Plan 02 deliverable)
    - state_core.auth.store (load_vault, get_auth_json_path, AuthVaultPermissionError)
  provides:
    - state_core.auth.loader.load_credentials (single-function public API)
    - state_core.auth.load_credentials (re-export at package root)
  affects:
    - tests/auth/test_loader.py (Wave 0 RED → GREEN, 24 tests pass)
    - tests/auth/test_import_graph.py::test_loader_imports_only_allowed_targets (Wave 0 RED → GREEN)
tech_stack:
  added:
    - none (stdlib os.environ + structlog already in stack; composes existing Phase 011/012/018-02 contracts)
  patterns:
    - Vault-wins-over-env precedence (5-cell matrix)
    - Ephemeral env synthesis with hard "never persist" guarantee (T-018-10)
    - One-way import edge: loader → providers/api_key (T-018-7)
    - Per-provider env-var isolation via _REGISTRY[pid].env_var lookup (T-018-5)
    - 12-factor empty-string-as-unset semantics (T-018-8)
key_files:
  created:
    - src/state_core/auth/loader.py (169 LOC)
    - .planning/milestones/v2/phases/018-plain-api-key-vault/018-03-SUMMARY.md
  modified:
    - src/state_core/auth/__init__.py (+3 LOC — re-export + __all__ entry)
    - tests/auth/test_loader.py (1 fixture fix — see Deviations)
decisions:
  - load_credentials placed at auth top level (not under providers/) — module is orchestration (vault + env fusion), not a provider implementation. Putting it under providers/ would mislead callers ("load credentials FROM a provider" vs "load credentials").
  - Stripped env value used for synthesized ApiKeyCredential.key — leading/trailing whitespace in an env var is overwhelmingly a typo; matches user intent. Phase 022 may revisit if a real-world complaint surfaces.
  - load_credentials returns a list[Credential] from the vault (not list[ApiKeyCredential]) — preserves Phase 011 union type so future OAuth-in-vault scenarios (Phase 014–017 providers) can also flow through this entry point. Env synthesis is api-key-only (only ApiKeyCredential constructible from a bare string).
  - Re-exported at the auth package root (`from state_core.auth import load_credentials`) — orchestration is a public-API surface; providers/* deliberately remain un-re-exported per RESEARCH §loader Placement.
  - Comments in loader.py rewritten to AVOID the literal substrings "save_vault" / "ensure_initialized" so the acceptance-criterion grep returns 0 hits. Mirrors Plan 02 Deviation 4 (naive substring matching tripped on negative-form documentation).
metrics:
  duration_minutes: 4
  completed_date: 2026-04-30
  task_count: 2
  file_count: 1 created (loader.py) + 1 created (this SUMMARY) + 2 modified (__init__.py + test_loader.py)
  loc_added: ~169 production + ~7 package + ~5 test patch
---

# Phase 018 Plan 03: Wave 2 GREEN — Credential Loader (vault > env precedence)

Wave 2 closes the last AUTH-05 behavior gap. One new module
(`state_core.auth.loader`, 169 LOC) and one re-export at the auth
package root turn VALIDATION rows 04–08 GREEN, complete row 21 (both
directions of the import-graph constraint), and give Phase 022 / v3
Provider Routing a single canonical entry point:
`load_credentials(provider_id) -> list[Credential]`.

The loader fuses Phase 012's vault round-trip with Plan 02's
`_REGISTRY[pid].env_var` to implement the locked precedence: vault
wins; env synthesizes (ephemerally, never persisted) when the vault
has no entry for the provider. Empty / whitespace env values are
treated as unset (12-factor).

## Tasks Executed

| Task | Name                                                                  | Commit  |
| ---- | --------------------------------------------------------------------- | ------- |
| 1    | Implement src/state_core/auth/loader.py with load_credentials         | c2bc7aa |
| 2    | Re-export load_credentials from state_core.auth package root          | c06981e |

## Final LOC + Public-API Verification

| File                                  | LOC | Note                                    |
| ------------------------------------- | --: | --------------------------------------- |
| `src/state_core/auth/loader.py`       | 169 | 1 public function (load_credentials)    |
| `src/state_core/auth/__init__.py`     | +3  | 1 import line + 1 __all__ entry + comment |

```
$ python3 -c "from state_core.auth import load_credentials; print(load_credentials.__module__)"
state_core.auth.loader

$ python3 -c "from state_core.auth import load_credentials; from state_core.auth.loader import load_credentials as direct; assert load_credentials is direct; print('alias=true')"
alias=true
```

## VALIDATION → GREEN Status

| Row | Behavior under test                                  | Test function                                   | Status        |
| --- | ---------------------------------------------------- | ----------------------------------------------- | ------------- |
| 01  | empty / whitespace key rejected                      | `test_login_rejects_empty_key` (5 params)        | GREEN (Plan 02) |
| 02  | prefix mismatch warns and stores                     | `test_login_warns_on_prefix_mismatch`            | GREEN (Plan 02) |
| 03  | unknown provider_id raises UnknownApiKeyProviderError | `test_get_api_key_auth_unknown_provider`        | GREEN (Plan 02) |
| 04  | vault non-empty wins over env                        | `test_vault_wins_over_env`                       | **GREEN (Plan 03)** |
| 05  | vault empty + env set → env synthesizes              | `test_env_synthesizes_when_vault_empty`          | **GREEN (Plan 03)** |
| 06  | vault file missing + env set → env synthesizes       | `test_env_synthesizes_when_vault_missing`        | **GREEN (Plan 03)** |
| 07  | vault missing + env unset → empty list               | `test_returns_empty_when_no_creds_anywhere`      | **GREEN (Plan 03)** |
| 08  | empty / whitespace env var treated as unset          | `test_empty_env_treated_as_unset` (4 params)     | **GREEN (Plan 03)** |
| 09  | append-default repeat login                          | `test_login_appends_by_default`                  | GREEN (Plan 02) |
| 10  | --replace truncates to single entry                  | `test_login_replace_truncates`                   | GREEN (Plan 02) |
| 11  | dedup on identical key string                        | `test_login_dedups_identical_key`                | GREEN (Plan 02) |
| 12  | longest-prefix-first sniff resolves sk- collisions   | `test_sniff_resolves_sk_collision`               | GREEN (Plan 02) |
| 13  | http_headers Anthropic uses x-api-key                | `test_http_headers[anthropic.api_key]`           | GREEN (Plan 02) |
| 14  | http_headers Google AI Studio uses x-goog-api-key    | `test_http_headers[google.ai_studio]`            | GREEN (Plan 02) |
| 15  | http_headers all-others use Authorization Bearer     | `test_http_headers[*]` (10 params)               | GREEN (Plan 02) |
| 16  | is_expired always False                              | `test_is_expired_always_false`                   | GREEN (Plan 02) |
| 17  | refresh(cred) returns cred unchanged                 | `test_refresh_returns_unchanged`                 | GREEN (Plan 02) |
| 18  | _REGISTRY has 12 providers in order                  | `test_registry_has_12_providers`                 | GREEN (Plan 02) |
| 19  | argv never contains the key                          | `test_login_uses_getpass_or_stdin` + companions  | GREEN (Plan 02) |
| 20  | ApiKeyCredential repr does not leak key              | `test_credential_repr_does_not_leak`             | GREEN (Plan 02) |
| 21  | api_key.py does NOT import loader.py                 | `test_api_key_does_not_import_loader`            | GREEN (Plan 02) |
| 21  | loader.py imports only allowed targets               | `test_loader_imports_only_allowed_targets`       | **GREEN (Plan 03)** |

**Plan 03 GREEN tally: rows 04–08 + the loader-side direction of row 21.**
**All 21 VALIDATION rows are GREEN as of Plan 03.**

## Vault × Env Precedence Matrix (5 cells, all verified)

| vault state         | env state    | result                                  | Test                                        |
| ------------------- | ------------ | --------------------------------------- | ------------------------------------------- |
| non-empty (1+ cred) | any          | vault list (env ignored)                | `test_vault_wins_over_env` (row 04)         |
| empty bucket        | set          | 1 ephemeral cred; vault unchanged       | `test_env_synthesizes_when_vault_empty` (05) |
| file missing        | set          | 1 ephemeral cred; vault NOT created     | `test_env_synthesizes_when_vault_missing` (06) |
| file missing        | unset        | `[]` — no error                         | `test_returns_empty_when_no_creds_anywhere` (07) |
| any                 | empty / WS   | `[]` — env treated as unset (12-factor) | `test_empty_env_treated_as_unset` (08, 4 params) |

The "vault file unchanged after env synthesis" assertion (T-018-10) is
explicitly checked by `test_env_synthesizes_when_vault_empty` (re-loads
vault after the call and asserts `providers == {}`) and
`test_env_synthesizes_when_vault_missing` (asserts `not vault_path.exists()`).

## Threat Mitigation Status — Plan 03 Delta

The 6 HIGH threats inherited from Plan 02 carry forward unchanged. Plan
03 closes the remaining loader-side mitigations:

| Threat   | Severity | Status After Plan 03                                                                                  |
| -------- | -------- | ----------------------------------------------------------------------------------------------------- |
| T-018-5  | MED      | **CLOSED** — `load_credentials` consults ONLY `_REGISTRY[provider_id].env_var`; verified by `test_loader_consults_only_matching_env_var` (12 parametrized cases × 2 sub-assertions = 24 sub-checks). |
| T-018-6  | HIGH     | CLOSED (inherited) — `load_vault` raises `AuthVaultPermissionError` on wrong-mode; loader propagates unchanged. Verified by `test_loader_propagates_vault_permission_error`. |
| T-018-7  | HIGH     | CLOSED — both directions verified: api_key.py does NOT import loader (`test_api_key_does_not_import_loader` from Plan 02); loader.py imports ONLY {base, store, providers.api_key, errors} (`test_loader_imports_only_allowed_targets` GREEN as of Plan 03). |
| T-018-8  | LOW      | **CLOSED for the env-input path** — empty / whitespace env values are stripped and treated as unset (`test_empty_env_treated_as_unset`, 4 params). Vault-file race deferred to Phase 022 filelock work. |
| T-018-10 | HIGH     | **CLOSED** — loader.py contains 0 hits for `save_vault` / `ensure_initialized` (verified by acceptance-criteria grep); the env-synthesis path returns the credential without writing. Plan 02 already closed the login-side; Plan 03 closes the loader-side. |

T-018-9 (symlink attack) remains DEFERRED to Phase 022 audit per CONTEXT.md.

## Verification Output

```
$ pytest tests/auth/test_api_key.py tests/auth/test_loader.py tests/auth/test_main_api_key.py tests/auth/test_import_graph.py -q
118 passed in 0.11s
```

```
$ pytest tests/auth/ -q
291 passed, 1 skipped in 44.88s
```

The single skip is the symlink-attack placeholder in `tests/auth/test_store.py`
(Phase 012's tracked deferral; Phase 022 owns).

```
$ python3 -c "
import os, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'auth.json'
    os.environ['STATE_AUTH_JSON'] = str(p)
    os.environ.pop('OPENAI_API_KEY', None)
    from state_core.auth.loader import load_credentials
    assert load_credentials('openai') == []
    os.environ['OPENAI_API_KEY'] = 'sk-test-1'
    creds = load_credentials('openai')
    assert len(creds) == 1 and creds[0].key == 'sk-test-1'
    os.environ['OPENAI_API_KEY'] = '   '
    assert load_credentials('openai') == []
print('precedence matrix: 3/3 cells pass')
"
precedence matrix: 3/3 cells pass
```

```
$ python3 -c "
from state_core.auth.loader import load_credentials
from state_core.auth.errors import UnknownApiKeyProviderError
try:
    load_credentials('not-a-provider')
    assert False
except UnknownApiKeyProviderError as e:
    assert e.provider_id == 'not-a-provider'
print('OK')
"
OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Wave 0 test scaffolding bug] `_PROVIDER_ENV_VARS` mapped `google.ai_studio` → `GOOGLE_API_KEY` but the canonical registry uses `GEMINI_API_KEY`**

- **Found during:** Task 1, first run of `tests/auth/test_loader.py`.
- **Issue:** Wave 0's `test_loader_consults_only_matching_env_var`
  carried a test-local `_PROVIDER_ENV_VARS` dict whose
  `google.ai_studio` value was `GOOGLE_API_KEY`. Plan 02's registry
  canonicalized on `GEMINI_API_KEY` (per the captured 2026-04-30 spec
  from `https://ai.google.dev/gemini-api/docs/api-key`). The test
  set `GOOGLE_API_KEY` to "OWN-KEY" and expected the loader to
  synthesize from it; the loader (correctly) read `GEMINI_API_KEY`
  instead — and the assertion failed because there was a real
  `GEMINI_API_KEY` set in the local environment, surfacing the
  cross-provider env-var leak that the test was supposed to detect.
- **Fix:** Updated the test's `_PROVIDER_ENV_VARS["google.ai_studio"]`
  to `GEMINI_API_KEY` so the test matches the registry byte-for-byte.
  Added a comment explaining the rationale and pointing to Plan 02's
  decision. This is the same fix-pattern Plan 02 applied to Wave 0
  inconsistencies (their Deviations 1, 2, 3, 6).
- **Files modified:** `tests/auth/test_loader.py`
- **Commit:** c2bc7aa

**2. [Rule 1 — Acceptance-criterion grep tripped on negative-form documentation] loader.py comments mentioned `save_vault` literally**

- **Found during:** Task 1 acceptance-criteria verification.
- **Issue:** The plan's acceptance criterion `grep -n "save_vault\|ensure_initialized" src/state_core/auth/loader.py` returns 0 hits is meant to verify the loader never invokes those mutation surfaces. My initial draft had two comment lines saying "MUST NEVER call save_vault" — same-style negative-form documentation Plan 02 had to rework (their Deviation 4 — comment substrings tripped naive import-graph regex).
- **Fix:** Rewrote both comments to describe the constraint without
  using the literal symbol names: e.g., "this code path MUST NOT
  invoke any vault-mutation surface" instead of "MUST NEVER call
  save_vault". Behavior unchanged; only the comment text differs.
- **Files modified:** `src/state_core/auth/loader.py`
- **Commit:** c2bc7aa (folded into the same commit before pushing)

## Authentication Gates

None. All work was implementation-side; no live OAuth or API endpoints
exercised. Phase 022 will own the live-vendor verification.

## Quality Gates

`quality.level = "fast"` — sentinel skipped per protocol; no Quality
Gates section emitted (matching Plan 02's convention).

## Issues Encountered

- **Worktree base mismatch** — initial worktree branch was on
  `5acaf88` (post-merge main tip). Per the worktree_branch_check
  protocol, `git reset --hard 00d3b9b` brought it onto Plan 02's tip
  (working tree was clean — no work lost).
- **One Wave 0 scaffolding bug** (Deviation 1 above), fixed inline
  with Task 1 per Rule 1.

## Hand-off to Plan 04 (verification-only)

AUTH-05 closure check:

- All 12 plain-api-key providers reachable through both pathways:
  - `from state_core.auth.providers.api_key import get_api_key_auth`
    (`AuthMethod` dispatcher path; Plan 02 deliverable)
  - `from state_core.auth import load_credentials`
    (orchestration path with vault > env precedence; Plan 03 deliverable)
- 21 of 21 VALIDATION rows GREEN.
- 6 HIGH threats CLOSED in-code; 2 LOW threats deferred to Phase 022 with explicit tracking.
- Public API surface frozen for Phase 022 / v3 consumption:
  - `state_core.auth.load_credentials(provider_id) -> list[Credential]`
  - `state_core.auth.providers.api_key.get_api_key_auth(provider_id) -> AuthMethod`
  - `state_core.auth.providers.api_key._REGISTRY` (12 frozen rows)
  - `state_core.auth.providers.api_key.iter_known_prefixes()` (Phase 020 redactor consumer)

Smoke commands Plan 04 should run:

```bash
# Full auth suite
pytest tests/auth/ -q
# Expected: 291 passed, 1 skipped (Phase 012 symlink-attack placeholder)

# Phase 018-only suite
pytest tests/auth/test_api_key.py tests/auth/test_loader.py tests/auth/test_main_api_key.py tests/auth/test_import_graph.py -q
# Expected: 118 passed in ~0.1s

# Public-API smoke
python3 -c "from state_core.auth import load_credentials; print(load_credentials.__module__)"
# Expected: state_core.auth.loader

# CLI smoke (per plan §verification)
echo "sk-test-XXXX" | python3 -m state_core.auth.providers.api_key login openai --replace
# Expected exit 0; "Logged in to openai (1 credential(s) on file)."
```

## Self-Check: PASSED

Files created and verified on disk:
- `src/state_core/auth/loader.py` — FOUND (169 LOC)
- `.planning/milestones/v2/phases/018-plain-api-key-vault/018-03-SUMMARY.md` — FOUND (this file)

Files modified and verified:
- `src/state_core/auth/__init__.py` — FOUND (re-export + __all__ entry)
- `tests/auth/test_loader.py` — FOUND (Wave 0 fixture fix per Deviation 1)

Commits exist in branch history:
- `c2bc7aa` — FOUND (Task 1: loader implementation + Wave 0 test fix)
- `c06981e` — FOUND (Task 2: package-root re-export)

Pytest verification:
- `pytest tests/auth/test_loader.py tests/auth/test_import_graph.py -q` → 24 passed
- `pytest tests/auth/test_api_key.py tests/auth/test_loader.py tests/auth/test_main_api_key.py tests/auth/test_import_graph.py -q` → 118 passed
- `pytest tests/auth/ -q` → 291 passed, 1 skipped (no regression)
