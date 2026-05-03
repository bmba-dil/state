---
phase: 022-cli-state-auth-login-logout
plan: "02"
subsystem: auth-cli-ops-layer
tags: [auth, cli-ops, login, logout, status, event-emission, AUTH-12]
dependency_graph:
  requires:
    - "022-01: Wave 0 RED stubs"
    - "src/state_core/auth/base.py (OAuthCredential, ApiKeyCredential)"
    - "src/state_core/auth/store.py (save_vault, load_vault, get_auth_json_path, AuthVault)"
    - "src/state_core/auth/loader.py (load_credentials)"
    - "src/state_core/auth/refresh.py (is_expired_buffered)"
    - "src/state_core/auth/errors.py (AuthError, UnknownApiKeyProviderError)"
    - "src/state_core/auth/providers/api_key.py (_REGISTRY)"
  provides:
    - "src/state_core/auth/cli_ops.py: login(), logout(), status(), StatusReport, StatusRow"
    - "src/state_core/auth/__init__.py: re-exports auth_login, auth_logout, auth_status, StatusReport, StatusRow"
  affects:
    - "022-03: Typer commands call cli_ops.login/logout/status"
    - "Future opencode-plugin TUI modal: imports cli_ops directly (await)"
tech_stack:
  added: []
  patterns:
    - "Provider dispatch table: OAuth (4) + api_key (12) dispatch in login()"
    - "Dual-write event emission: SQLite FIRST via store.append(), SyncEvent second via mirror"
    - "Account-label fallback chain: extras['email_address'] > account_id > prefix12..."
    - "Status ordering: providers alphabetical, vault > opencode-import > env, expires_at ascending"
    - "Lazy _get_all_provider_ids() to avoid circular imports at module load time"
    - "pytest pythonpath=[src] in worktree pyproject.toml for test isolation"
key_files:
  created:
    - src/state_core/auth/cli_ops.py
  modified:
    - src/state_core/auth/__init__.py
    - tests/auth/test_cli_ops.py
    - pyproject.toml
decisions:
  - "PlainApiKeyAuth.login() has no api_key param — construct ApiKeyCredential directly when api_key is pre-supplied"
  - "load_credentials() is api_key-only (uses _REGISTRY) — OAuth providers load from vault directly in status()"
  - "Added pythonpath=['src'] to worktree pyproject.toml so pytest resolves state_core from worktree not main project editable install"
  - "test_status_returns_status_report monkeypatches all api_key env vars to prevent dev machine GEMINI_API_KEY from leaking into test"
metrics:
  duration: "~8m (466 seconds)"
  completed: "2026-05-02T03:07:11Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 3
---

# Phase 022 Plan 02: cli_ops Ops Layer Summary

**One-liner:** Async-native auth operations layer (login/logout/status) with dual-write SQLite-first event emission, provider dispatch table for all 16 providers, and structured StatusReport dataclass for table rendering.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement src/state_core/auth/cli_ops.py | 00587b3 | src/state_core/auth/cli_ops.py, tests/auth/test_cli_ops.py, pyproject.toml |
| 2 | Re-export cli_ops public surface from auth/__init__.py | a8f53d4 | src/state_core/auth/__init__.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PlainApiKeyAuth.login() has no api_key parameter**
- **Found during:** Task 1, implementing api_key provider dispatch in login()
- **Issue:** The plan's dispatch block called `auth_method.login()` for api_key providers and separately used `ApiKeyCredential(provider_id=canonical, key=api_key)`. The actual `PlainApiKeyAuth.login()` reads via getpass/stdin — it has no `key` parameter. The plan's stub showed both paths but the comment "If login() doesn't accept api_key kwarg, create the ApiKeyCredential directly" confirmed this approach.
- **Fix:** When `api_key` is pre-supplied (non-None), construct `ApiKeyCredential` directly. When `from_stdin=True`, read one line and construct directly. Only fall through to `auth_method.login()` for the fully-interactive case.
- **Files modified:** src/state_core/auth/cli_ops.py
- **Commit:** 00587b3

**2. [Rule 1 - Bug] load_credentials() is api_key-only — OAuth providers need vault direct access**
- **Found during:** Task 1, implementing status()
- **Issue:** `load_credentials(provider_id)` raises `UnknownApiKeyProviderError` for OAuth provider IDs (anthropic, google.gemini, etc.) because they are not in `_REGISTRY`. The plan's status() implementation called `load_credentials(pid)` for all providers unconditionally.
- **Fix:** In status(), check if `pid in _OAUTH_PROVIDER_IDS` and load from vault directly; for api_key providers use `load_credentials()` as designed.
- **Files modified:** src/state_core/auth/cli_ops.py
- **Commit:** 00587b3

**3. [Rule 3 - Blocking] Worktree pytest can't find state_core.auth.cli_ops**
- **Found during:** Task 1, running initial tests
- **Issue:** The venv has an editable install pointing to `/Users/tmac/Projects/state/src`, not the worktree's `src/`. pytest couldn't resolve `state_core.auth.cli_ops` from the worktree.
- **Fix:** Added `pythonpath = ["src"]` to `[tool.pytest.ini_options]` in the worktree's pyproject.toml. This makes pytest prepend the worktree's `src/` to `sys.path` so imports resolve from the worktree first.
- **Files modified:** pyproject.toml
- **Commit:** 00587b3

**4. [Rule 1 - Bug] _make_oauth_cred in tests with duplicate field conflicts**
- **Found during:** Task 1, running tests after initial implementation
- **Issue:** `_make_oauth_cred(extras={...})` raised `TypeError: got multiple values for keyword argument 'extras'` because the helper had both hardcoded `extras=...` and `**kwargs`.
- **Fix:** Rewrote `_make_oauth_cred` to build a `defaults` dict and apply `defaults.update(kwargs)` before construction — callers can override any field without duplication.
- **Files modified:** tests/auth/test_cli_ops.py
- **Commit:** 00587b3

**5. [Rule 1 - Bug] test_status_returns_status_report picks up GEMINI_API_KEY from dev environment**
- **Found during:** Task 1, test_status_returns_status_report asserting "1 provider(s)"
- **Issue:** The dev machine has GEMINI_API_KEY set in the shell. status() synthesizes an ephemeral credential for google.ai_studio, producing "2 provider(s) configured" instead of the expected 1.
- **Fix:** Added monkeypatching of all api_key env vars (`for spec in _REGISTRY.values(): monkeypatch.delenv(spec.env_var, raising=False)`) so status() sees only the vault contents.
- **Files modified:** tests/auth/test_cli_ops.py
- **Commit:** 00587b3

## Issues Encountered

**Pre-existing fixture issue in test_api_key.py:** `test_login_rejects_empty_key` fails with `fixture 'mock_api_key_getpass' not found`. This is NOT caused by our changes — it is a pre-existing gap in the test conftest. It was present before Plan 02 started and is out of scope (not in the cli_ops test surface).

**Pre-existing errors in test_rotation.py:** Several `fixture 'mock_auth_method_factory'` and similar errors in test_rotation.py. Also pre-existing, not caused by our changes.

## Self-Check: PASSED

- src/state_core/auth/cli_ops.py: FOUND
- src/state_core/auth/__init__.py: modified with Phase 022 re-exports
- tests/auth/test_cli_ops.py: 14/14 tests PASSED
- tests/auth/test_import_graph.py::test_cli_ops_no_state_cli_imports: PASSED
- Commit 00587b3: FOUND
- Commit a8f53d4: FOUND
- grep reverse imports: 0 (no state_cli imports in cli_ops.py)
- from state_core.auth import StatusReport, StatusRow, auth_login, auth_logout, auth_status: OK
- from state_core.auth import AuthVault, load_vault, save_vault, Credential: OK (existing exports intact)
