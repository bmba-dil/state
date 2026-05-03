---
phase: 018-plain-api-key-vault
plan: 01
subsystem: auth
tags: [auth, api-key, wave-0, red-scaffolding, tdd]
dependency_graph:
  requires:
    - state_core.auth.base (ApiKeyCredential, AuthMethod, OAuthCredential)
    - state_core.auth.errors (AuthError, AuthLoginError)
    - state_core.auth.store (AuthVault, AuthVaultPermissionError, save_vault, load_vault)
  provides:
    - tests/auth/test_api_key.py (12 RED tests — VALIDATION rows 01–03, 12–18, 20)
    - tests/auth/test_loader.py (8 RED tests — VALIDATION rows 04–08 + 3 mitigations)
    - tests/auth/test_main_api_key.py (10 RED tests — VALIDATION rows 09–11, 19 + 4 supporting)
    - tests/auth/test_import_graph.py (2 RED tests — VALIDATION row 21 + companion)
    - tests/auth/conftest.py extension (5 fixtures + 1 module-level constant)
  affects:
    - none (test-only; no production code touched)
tech_stack:
  added:
    - none (pytest 8.4 + pytest-asyncio 1.3 already in dev deps)
  patterns:
    - structlog.testing.capture_logs for log-leak assertions
    - parametrize-over-12-providers for header/expiry/refresh symmetry
    - late-bind monkeypatch for modules that don't yet exist (Wave 0 RED-safe)
    - isolated_vault_path tmp_path + STATE_AUTH_JSON for __main__ vault tests
key_files:
  created:
    - tests/auth/test_api_key.py
    - tests/auth/test_loader.py
    - tests/auth/test_main_api_key.py
    - tests/auth/test_import_graph.py
    - .planning/milestones/v2/phases/018-plain-api-key-vault/018-01-SUMMARY.md
  modified:
    - tests/auth/conftest.py (append-only — 5 fixtures + 1 constant)
decisions:
  - Wave 0 tests fail at import-time (ModuleNotFoundError) by design — no
    pytest.importorskip; the loud collection failure IS the RED signal.
  - mock_api_key_getpass + mock_stdin_pipe use late-bind monkeypatch
    (try/except ModuleNotFoundError → silent no-op) so collection survives
    when the api_key module is absent. The test functions themselves still
    fail at the top-level import — failure mode is consistent.
  - test_import_graph.py uses pytest.fail (not import) so it remains
    collectable in Wave 0; tests RED with explicit "Wave 0 RED" messages.
  - File path tests/auth/test_api_key.py (NOT under providers/) tracks
    VALIDATION.md row paths exactly.
metrics:
  duration_minutes: ~10
  completed_date: 2026-04-30
  task_count: 3
  file_count: 4 created + 1 modified + 1 SUMMARY
  test_function_count: 32 (12 + 8 + 10 + 2)
  fixture_count_added: 5
---

# Phase 018 Plan 01: Wave 0 RED Test Scaffolding Summary

Wave 0 RED scaffolding for `state_core.auth.providers.api_key` (12 plain-API-key
providers) and `state_core.auth.loader` (vault×env precedence layer). All 21
VALIDATION.md sampling rows now map 1:1 to a named test function. Every test
fails by design — Wave 1 (Plan 02) and Wave 2 (Plan 03) flip them GREEN.

## Tasks Executed

| Task | Name                                                            | Commit  |
| ---- | --------------------------------------------------------------- | ------- |
| 1    | Extend tests/auth/conftest.py with Phase 018 fixtures           | 4d28b5f |
| 2    | Write tests/auth/test_api_key.py (rows 01–03, 12–18, 20)        | 5057a19 |
| 3    | Write test_loader.py + test_main_api_key.py + test_import_graph.py | a18ce39 |

## VALIDATION.md → Test Function Mapping (21 rows + companions)

| Row | Behavior under test                                       | Target file              | Test function                                        |
| --- | --------------------------------------------------------- | ------------------------ | ---------------------------------------------------- |
| 01  | empty / whitespace key rejected                           | test_api_key.py          | `test_login_rejects_empty_key`                       |
| 02  | prefix mismatch warns and stores (no key in logs)         | test_api_key.py          | `test_login_warns_on_prefix_mismatch`                |
| 03  | unknown provider_id raises UnknownApiKeyProviderError     | test_api_key.py          | `test_get_api_key_auth_unknown_provider`             |
| 04  | vault non-empty wins over env                             | test_loader.py           | `test_vault_wins_over_env`                           |
| 05  | vault empty + env set → env synthesizes                   | test_loader.py           | `test_env_synthesizes_when_vault_empty`              |
| 06  | vault file missing + env set → env synthesizes            | test_loader.py           | `test_env_synthesizes_when_vault_missing`            |
| 07  | vault missing + env unset → empty list                    | test_loader.py           | `test_returns_empty_when_no_creds_anywhere`          |
| 08  | empty / whitespace env var treated as unset               | test_loader.py           | `test_empty_env_treated_as_unset`                    |
| 09  | append-default repeat login                               | test_main_api_key.py     | `test_login_appends_by_default`                      |
| 10  | --replace truncates to single entry                       | test_main_api_key.py     | `test_login_replace_truncates`                       |
| 11  | dedup on identical key string                             | test_main_api_key.py     | `test_login_dedups_identical_key`                    |
| 12  | longest-prefix-first sniff resolves sk- collisions        | test_api_key.py          | `test_sniff_resolves_sk_collision`                   |
| 13  | http_headers Anthropic uses x-api-key                     | test_api_key.py          | `test_http_headers[anthropic.api_key]`               |
| 14  | http_headers Google AI Studio uses x-goog-api-key         | test_api_key.py          | `test_http_headers[google.ai_studio]`                |
| 15  | http_headers all-others use Authorization Bearer (10 IDs) | test_api_key.py          | `test_http_headers[<10 others>]`                     |
| 16  | is_expired always False (∀ provider, ∀ now)               | test_api_key.py          | `test_is_expired_always_false`                       |
| 17  | refresh(cred) returns cred unchanged                      | test_api_key.py          | `test_refresh_returns_unchanged`                     |
| 18  | _REGISTRY has 12 providers in load-bearing order          | test_api_key.py          | `test_registry_has_12_providers`                     |
| 19  | argv never contains the key (getpass / stdin only)        | test_main_api_key.py     | `test_login_uses_getpass_or_stdin` + 2 companion tests |
| 20  | ApiKeyCredential repr does not leak key                   | test_api_key.py          | `test_credential_repr_does_not_leak`                 |
| 21  | api_key.py does NOT import loader.py                      | test_import_graph.py     | `test_api_key_does_not_import_loader`                |

### Companion / mitigation tests beyond the 21 rows

| Concern                                              | Target file              | Test function                                          |
| ---------------------------------------------------- | ------------------------ | ------------------------------------------------------ |
| RESEARCH provenance comments per spec                | test_api_key.py          | `test_registry_provenance_comments`                    |
| AuthMethod Protocol satisfaction (12 providers)      | test_api_key.py          | `test_get_api_key_auth_returns_auth_method`            |
| iter_known_prefixes is callable                      | test_api_key.py          | `test_iter_known_prefixes_is_callable`                 |
| Loader proxies registry lookup for unknown provider  | test_loader.py           | `test_loader_unknown_provider_id_raises`               |
| T-018-6 wrong-mode vault propagates, no fallback     | test_loader.py           | `test_loader_propagates_vault_permission_error`        |
| T-018-5 cross-provider env-var leak (12 providers)   | test_loader.py           | `test_loader_consults_only_matching_env_var`           |
| T-018-1 --api-key flag does not exist                | test_main_api_key.py     | `test_login_no_api_key_flag_exists`                    |
| Non-TTY stdin pipe path                              | test_main_api_key.py     | `test_login_via_stdin_pipe`                            |
| Argparse choices= rejection                          | test_main_api_key.py     | `test_login_unknown_provider_fails_at_argparse`        |
| KeyboardInterrupt → exit 130                         | test_main_api_key.py     | `test_keyboard_interrupt_returns_130`                  |
| `list` subcommand enumerates 12 providers            | test_main_api_key.py     | `test_list_subcommand_prints_all_12_providers`         |
| `refresh` is no-op-with-explanation for API keys     | test_main_api_key.py     | `test_refresh_subcommand_is_noop_for_api_key`          |
| Companion: loader imports bounded                    | test_import_graph.py     | `test_loader_imports_only_allowed_targets`             |

## New Fixtures (tests/auth/conftest.py)

| Fixture                | Scope    | Purpose                                                                |
| ---------------------- | -------- | ---------------------------------------------------------------------- |
| `_PHASE_018_PROVIDER_IDS` | module | Tuple of 12 canonical provider_ids in longest-prefix-first order        |
| `all_provider_ids`     | function | Exposes the tuple to tests                                             |
| `provider_id_factory`  | function | Returns callable that yields a fresh iterator on each call              |
| `isolated_vault_path`  | function | tmp_path .state/auth.json + STATE_AUTH_JSON env override                |
| `mock_stdin_pipe`      | function | Returns callable that patches sys.stdin with non-TTY StringIO          |
| `mock_api_key_getpass` | function | Returns callable that patches getpass.getpass (late-bind, Wave 0 safe) |

## Wave 0 RED State (proof of failure-by-design)

Full pytest run on the 4 test files:

```
=========================== short test summary info ============================
ERROR tests/auth/test_api_key.py
ERROR tests/auth/test_loader.py
ERROR tests/auth/test_main_api_key.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
============================== 3 errors in 0.09s ===============================
```

Three files fail at collection-time with `ModuleNotFoundError: No module named
'state_core.auth.providers.api_key'` (and similarly for `state_core.auth.loader`).
The fourth file (`test_import_graph.py`) collects successfully but every test
fails with `pytest.fail("Wave 0 RED: ...")`. **Zero tests pass — exactly the
intended Wave 0 state.**

Per-file function counts:
- `test_api_key.py` — 12 named test functions (305 LOC)
- `test_loader.py` — 8 named test functions (218 LOC)
- `test_main_api_key.py` — 10 named test functions (246 LOC)
- `test_import_graph.py` — 2 named test functions (81 LOC)
- **Total: 32 named test functions** (and many more parametrize expansions)

## No-Regression Verification

Pre-existing auth test files still pass:

```
$ pytest tests/auth/test_base.py tests/auth/test_store.py tests/auth/test_errors.py
======================== 37 passed, 1 skipped in 0.15s =========================
```

The new fixtures are visible to existing tests; conftest collection succeeds:

```
$ pytest tests/auth/ --collect-only -q
173 tests collected in 0.11s
```

## Deviations from Plan

None — plan executed exactly as written. Three nits worth noting:

1. The plan's example imports listed `import structlog` in `test_api_key.py` even
   though only `from structlog.testing import capture_logs` is consumed. The
   structlog top-level import is preserved verbatim for fixture-precedent style
   (parent conftest also imports structlog top-level).
2. Provenance-comment guard (`test_registry_provenance_comments`) reads the
   source file from disk via a repository-relative `Path(__file__).parent.parent`.
   Plan said `parent.parent.parent / "src"` — corrected to `parent.parent / "src"`
   because tests live at `tests/auth/test_api_key.py` (depth 2 to repo root) and
   the source lives at `src/state_core/auth/providers/api_key.py`.
3. The plan's verification block said "Expect: >= 25 test items" from
   `--collect-only`. With Wave 0 RED-by-design, three of four files fail at
   collection-time so individual tests inside them are not enumerated; only the
   2 import_graph tests are collectable. This is the **intended** Wave 0 outcome
   per the plan's own `must_haves.truths`. Test functions exist in the source
   (32 total per `grep`) and will be enumerated as soon as Wave 1's
   `state_core.auth.providers.api_key` lands.

## Quality Gates

`quality.level = "fast"` — sentinel skipped per protocol; no Quality Gates
section emitted.

## Issues Encountered

- **Worktree base mismatch**: The worktree branch was initially based on
  `5acaf88` (v1 milestone tip) instead of the expected `62b3c76` (post-phase-017
  v2 tip). Per protocol, did `git reset --hard 62b3c76` (working tree was clean
  before reset — no work lost). All commits since are based on the correct base.
- **Phase directory absent on disk**: `.planning/milestones/v2/phases/018-plain-api-key-vault/`
  did not exist in the working tree (only 016 had a SUMMARY in v2 phases).
  Created the directory and wrote SUMMARY.md into it.

## Hand-off to Wave 1 (Plan 02)

Wave 1 must create `src/state_core/auth/providers/api_key.py` exporting:

```python
_REGISTRY: dict[str, ApiKeyProviderSpec]   # 12 entries in longest-prefix-first order
class ApiKeyProviderSpec(BaseModel):       # frozen, extra="forbid"
    provider_id: str
    auth_header: tuple[str, str]            # (header_name, value_template_or_value)
    key_prefixes: tuple[str, ...]
    env_var: str
    notes: str = ""
class PlainApiKeyAuth: ...                 # AuthMethod-conforming
def get_api_key_auth(provider_id: str) -> AuthMethod: ...
def iter_known_prefixes() -> Iterator[str]: ...
def _main() -> int: ...                    # argparse __main__: login / list / refresh
```

Wave 1 must add to `src/state_core/auth/errors.py`:

```python
class UnknownApiKeyProviderError(AuthError): ...
```

Wave 2 (Plan 03) must create `src/state_core/auth/loader.py` exporting:

```python
def load_credentials(provider_id: str) -> list[Credential]: ...
```

The loader's allowed import set (per the import-graph companion test) is:
`state_core.auth.base`, `state_core.auth.store`, `state_core.auth.providers.api_key`,
`state_core.auth.errors`. Anything else is a test failure.

## Self-Check: PASSED

Files created and verified on disk:
- `tests/auth/test_api_key.py` — FOUND
- `tests/auth/test_loader.py` — FOUND
- `tests/auth/test_main_api_key.py` — FOUND
- `tests/auth/test_import_graph.py` — FOUND
- `tests/auth/conftest.py` — FOUND (extended)

Commits exist in branch history:
- `4d28b5f` — FOUND
- `5057a19` — FOUND
- `a18ce39` — FOUND
