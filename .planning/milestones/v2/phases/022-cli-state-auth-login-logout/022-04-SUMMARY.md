---
phase: 022-cli-state-auth-login-logout
plan: "04"
subsystem: auth-p0-regression-goldens
tags: [test, regression, golden-files, AUTH-13, P0]
dependency_graph:
  requires:
    - "022-01: Wave 0 RED stubs + golden infrastructure"
    - "022-02: cli_ops ops layer"
    - "src/state_core/auth/providers/anthropic.py (_CLIENT_ID, _USER_AGENT, _ANTHROPIC_BETA, AnthropicAuth)"
    - "src/state_core/auth/refresh.py (is_expired_buffered, refresh_credential, RefreshLockTimeout)"
    - "src/state_core/auth/store.py (load_vault, AuthVaultPermissionError)"
    - "src/state_core/auth/providers/antigravity.py (_USER_AGENT_LITERAL, _X_GOOG_API_CLIENT, _build_client_metadata)"
    - "src/state_core/auth/providers/github_copilot.py (_USER_AGENT, _EDITOR_VERSION, _EDITOR_PLUGIN_VERSION)"
  provides:
    - "tests/auth/test_p0_regression.py: 9 implemented P0 regression tests (GREEN)"
    - "tests/auth/golden/anthropic/login_token_exchange.json: Anthropic stealth-header golden"
    - "tests/auth/golden/anthropic/refresh.json: Anthropic refresh-endpoint golden"
    - "tests/auth/golden/google.gemini/login_loopback.json: Gemini authorization golden"
    - "tests/auth/golden/google.antigravity/login_loopback.json: Antigravity 4-header golden"
    - "tests/auth/golden/github.copilot/device_code_exchange.json: Copilot 4-header golden"
    - "tests/auth/golden/api_key/authorization_header.json: API-key Bearer shape golden"
  affects:
    - "AUTH-13 requirement: captured-header golden regression suite"
tech_stack:
  added: []
  patterns:
    - "Direct constant assertion: _CLIENT_ID == expected UUID (P0-5)"
    - "Direct http_headers() call: no network mock needed for header shape tests (P0-1..P0-4)"
    - "_build_authorize_url + urlparse: behavioral P0-8 assertion (state==verifier)"
    - "Pre-populate vault with expired cred before monkeypatching lock (P0-6 prerequisite)"
    - "Golden JSON: capture_date + provider + flow + positive/negative allowlist + headers"
key_files:
  created:
    - tests/auth/golden/anthropic/login_token_exchange.json
    - tests/auth/golden/anthropic/refresh.json
    - tests/auth/golden/google.gemini/login_loopback.json
    - tests/auth/golden/google.antigravity/login_loopback.json
    - tests/auth/golden/github.copilot/device_code_exchange.json
    - tests/auth/golden/api_key/authorization_header.json
  modified:
    - tests/auth/test_p0_regression.py
decisions:
  - "P0-6: pre-populate vault with expired credential before monkeypatching filelock — refresh_credential does a quick-check outside the lock, so vault must exist and cred must be expired before the lock acquire path is triggered"
  - "P0-2: removed claude-code-20250219 assertion — that flag was REMOVED in Claude Code 2.1.121 (2026-04-29 capture). Test asserts against actual _ANTHROPIC_BETA constant, not against removed flags"
  - "P0-8: used _build_authorize_url + urlparse instead of inspect.getsource — behavioral assertion is more reliable than structural source inspection"
  - "Google Gemini golden: positive_allowlist is [authorization] only — GoogleGeminiAuth.http_headers() only emits authorization (+ optional x-goog-user-project). CONTEXT.md listed User-Agent/X-Goog-Api-Client but these are not in the actual implementation (Antigravity has them, not Gemini)"
  - "http_headers() returns lowercase 'authorization' key — P0-4 checks case-insensitively"
metrics:
  duration: "~15m"
  completed: "2026-05-01T00:00:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 1
---

# Phase 022 Plan 04: P0 Regression Tests GREEN + Golden JSON Fixtures Summary

**One-liner:** 9 AUTH-13 P0 regression tests turned GREEN (direct constant assertions + behavioral http_headers() calls), with 6 provider golden JSON fixtures committing the exact stealth-header shapes for drift detection.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement 9 P0 tests in test_p0_regression.py | 7b3891c | tests/auth/test_p0_regression.py |
| 2 | Generate and commit golden JSON fixtures | 3389ecd | 6 golden/*.json files |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] P0-6 quick-check fails before lock acquisition**
- **Found during:** Task 1, running test_p0_6
- **Issue:** The plan's stub called `refresh_credential(cred=fake_oauth_cred, auth_method=AnthropicAuth(), vault_path=vault_path)` but the actual signature is `refresh_credential(method, provider_id, idx, *, vault_path, ...)`. More critically, `refresh_credential` does a "quick check" outside the lock (reads vault + checks expiry). With an empty vault, this raised `KeyError: "No credentials for provider_id='anthropic'"` before the lock acquire path was triggered.
- **Fix:** Pre-populate the vault with an expired credential (`expires=0.0`) via `save_vault()`, then set `now=1.0` so quick-check sees the cred as expired and proceeds to lock acquisition. The monkeypatched `__aenter__` then raises `filelock.Timeout` → `RefreshLockTimeout`.
- **Files modified:** tests/auth/test_p0_regression.py
- **Commit:** 7b3891c

**2. [Rule 1 - Bug] P0-2 assertion for claude-code-20250219 would fail**
- **Found during:** Task 1, reading the actual `_ANTHROPIC_BETA` constant
- **Issue:** The plan stub included `assert "claude-code-20250219" in headers["anthropic-beta"]` but `claude-code-20250219` was REMOVED from the beta list in Claude Code 2.1.121 (2026-04-29 live capture per source comment). The constant now has 5 different flags: `oauth-2025-04-20`, `interleaved-thinking-2025-05-14`, `redact-thinking-2026-02-12`, `context-management-2025-06-27`, `prompt-caching-scope-2026-01-05`.
- **Fix:** Assert against `_ANTHROPIC_BETA` constant directly (full exact match) + assert `oauth-2025-04-20` present (always required on auth endpoints). Removed the stale `claude-code-20250219` check.
- **Files modified:** tests/auth/test_p0_regression.py
- **Commit:** 7b3891c

**3. [Rule 1 - Bug] P0-8 structural inspect.getsource approach replaced with behavioral assertion**
- **Found during:** Task 1, reading `_build_authorize_url` in anthropic.py
- **Issue:** The plan provided a fallback `inspect.getsource(AnthropicAuth)` structural check but noted "IMPORTANT NOTE: After reading... replace the structural check with a precise behavioral assertion." The `_build_authorize_url(verifier, challenge)` helper is directly callable and exported.
- **Fix:** Import `_build_authorize_url` directly, generate a real verifier+challenge pair, call the function, parse the resulting URL with `urlparse`/`parse_qs`, and assert `params["state"][0] == verifier`. This is a true behavioral test.
- **Files modified:** tests/auth/test_p0_regression.py
- **Commit:** 7b3891c

**4. [Rule 2 - Spec vs Implementation] Google Gemini golden uses actual http_headers() output**
- **Found during:** Task 2, checking GoogleGeminiAuth.http_headers()
- **Issue:** CONTEXT.md positive_allowlist for Gemini listed `User-Agent`, `X-Goog-Api-Client` but `GoogleGeminiAuth.http_headers()` only returns `{"authorization": "Bearer ..."}` (optionally `x-goog-user-project` if project_id present). The spec listed headers from Antigravity, not Gemini.
- **Fix:** Golden reflects actual implementation (`authorization` only). This is the correct regression anchor — it captures what the code ACTUALLY emits, not what CONTEXT.md speculated.
- **Files modified:** tests/auth/golden/google.gemini/login_loopback.json
- **Commit:** 3389ecd

## Issues Encountered

None beyond the auto-fixed deviations above. The worktree had all Wave 1/Wave 2 files deleted in the working tree (git reset --soft artifact from branch initialization). Restored via `git checkout -- .` before starting task implementation.

## Self-Check: PASSED

Files created:
- tests/auth/golden/anthropic/login_token_exchange.json: FOUND
- tests/auth/golden/anthropic/refresh.json: FOUND
- tests/auth/golden/google.gemini/login_loopback.json: FOUND
- tests/auth/golden/google.antigravity/login_loopback.json: FOUND
- tests/auth/golden/github.copilot/device_code_exchange.json: FOUND
- tests/auth/golden/api_key/authorization_header.json: FOUND
- tests/auth/test_p0_regression.py: FOUND (modified)

Commits verified:
- 7b3891c: FOUND (test_p0_regression.py - 9 P0 tests GREEN)
- 3389ecd: FOUND (6 golden JSON files)

Test results:
- pytest tests/auth/test_p0_regression.py -v: 9 PASSED
- grep -r "Bearer sk-" tests/auth/golden/: no matches (clean)
- All golden files contain "headers" key: VERIFIED
- grep -r "Bearer <REDACTED>" tests/auth/golden/anthropic/: 2 matches (login + refresh)
