---
phase: "014"
plan: "01"
subsystem: auth
tags: [tdd, red-stubs, oauth, pkce, stealth-headers, AUTH-01]
dependency_graph:
  requires:
    - "011-02 (OAuthCredential, AuthMethod Protocol)"
    - "013-02 (is_expired_buffered)"
  provides:
    - "Wave 0 RED scaffold — executable threat-model assertions for Plans 02+03"
    - "tests/auth/oauth_common/test_pkce.py (1 test)"
    - "tests/auth/providers/conftest.py (5 fixtures)"
    - "tests/auth/providers/test_anthropic.py (17 tests)"
  affects:
    - "Plans 02 and 03 must satisfy these stubs before merge"
    - "Phases 015/016/017 share oauth_common test infrastructure"
tech_stack:
  added: []
  patterns:
    - "try/except ImportError + pytestmark skipif (canonical Phase 013 pattern)"
    - "module-scoped monkeypatch for print (never builtins.print)"
    - "pinned _FIXTURE_VERIFIER with import-time self-check"
key_files:
  created:
    - tests/auth/oauth_common/__init__.py
    - tests/auth/oauth_common/test_pkce.py
    - tests/auth/providers/__init__.py
    - tests/auth/providers/conftest.py
    - tests/auth/providers/test_anthropic.py
  modified: []
decisions:
  - "Used try/except ImportError + pytestmark.skipif instead of pytest.importorskip so tests are individually collected as SKIPPED items (matching Phase 013 canonical pattern; pytest.importorskip at module level skips the entire file during collection)"
  - "_FIXTURE_VERIFIER pinned as 'fixture-verifier-' + 'a'*26 = exactly 43 chars; import-time assert fires LOUD on drift"
  - "All monkeypatch targets are module-scoped (state_core.auth.providers.anthropic.print, state_core.auth.providers.anthropic.getpass.getpass) — never builtins.print"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-29T03:30:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 0
  tests_scaffolded: 18
---

# Phase 014 Plan 01: RED Test Scaffold Summary

Wave 0 RED stubs for AUTH-01 (Anthropic OAuth stealth flow) — 18 tests collected, all SKIPPED until Plans 02/03 land. Executable threat-model contract frozen before any implementation.

## What Was Built

Five files created under `tests/auth/`:

| File | Purpose | Lines |
|------|---------|-------|
| `tests/auth/oauth_common/__init__.py` | pytest package marker | 1 |
| `tests/auth/oauth_common/test_pkce.py` | PKCE verifier format test (row 014-01-01) | 57 |
| `tests/auth/providers/__init__.py` | pytest package marker | 1 |
| `tests/auth/providers/conftest.py` | 5 local fixtures with import-time self-check | 120 |
| `tests/auth/providers/test_anthropic.py` | 17 test stubs (rows 014-01-02 thru 014-01-17 + wire bonus) | 353 |

**Total tests scaffolded: 18** (1 PKCE + 17 anthropic-stub including the invalid_grant precedence regression)

## Wave 0 RED State Confirmed

```
18 tests collected — 18 skipped (Plan 02 not yet landed: No module named 'state_core.auth.providers.anthropic')
```

Every test SKIPS (not ERRORS) at collection because both test files use the canonical `try/except ImportError` + `pytestmark = pytest.mark.skipif(...)` pattern from Phase 013.

## Fixture Details

`tests/auth/providers/conftest.py` provides:

- `fixture_verifier` — `"fixture-verifier-aaaaaaaaaaaaaaaaaaaaaaaaaa"` (EXACTLY 43 chars, base64url-no-pad)
- `fixture_paste` — `f"fixture-code#{fixture_verifier}"`
- `fixture_token_response` — canonical 200-OK token-endpoint payload
- `mock_getpass` — lazy patcher for `state_core.auth.providers.anthropic.getpass.getpass`
- `mock_generate_verifier` — lazy patcher for `state_core.auth.oauth_common.pkce.generate_verifier`

Import-time self-checks:
```python
assert len(_FIXTURE_VERIFIER) == 43, ...
assert re.fullmatch(r"[A-Za-z0-9_-]+", _FIXTURE_VERIFIER), ...
```

## Test Coverage Map

| Row | Test Name | Threat | Plan to turn GREEN |
|-----|-----------|--------|-------------------|
| 014-01-01 | `test_verifier_format` | PKCE length+alphabet+no-pad | Plan 02 |
| 014-01-02 | `test_state_equals_verifier` | P0-8 PKCE state==verifier | Plan 03 |
| 014-01-03 | `test_client_id_matches_claude_code` | P0-5 client_id UUID | Plan 02 |
| 014-01-04 | `test_http_headers_user_agent_exact` | P0-1 user-agent literal | Plan 02 |
| 014-01-05 | `test_http_headers_anthropic_beta_exact` | P0-2 beta string literal | Plan 02 |
| 014-01-06 | `test_http_headers_x_app` | P0-3 x-app literal | Plan 02 |
| 014-01-07 | `test_http_headers_no_x_api_key` | P0-4 Bearer not x-api-key | Plan 02 |
| 014-01-08 | `test_is_expired_uses_300s_buffer` | P0-7 5-min buffer | Plan 02 |
| 014-01-09 | `test_login_token_post_shape` | authorization_code grant body | Plan 03 |
| 014-01-10 | `test_refresh_post_shape` | refresh_token grant body | Plan 03 |
| 014-01-11 | `test_token_response_ignores_unknown_field` | extra=ignore forward-compat | Plan 02 |
| 014-01-12 | `test_inject_stealth_system_prefix` | body-shape mutation all forms | Plan 02 |
| 014-01-13 | `test_url_has_beta_true` | ?beta=true idempotent | Plan 02 |
| 014-01-14 | `test_satisfies_authmethod_protocol` | isinstance + 5-method Protocol | Plan 02 |
| 014-01-15 | `test_paste_format_required` | P1-2 no-# → AuthLoginError | Plan 03 |
| 014-01-16 | `test_401_raises_stealth_rejected` | StealthRejected on stealth 401 | Plan 03 |
| 014-01-17 | `test_invalid_grant_in_refresh_raises_AuthRefreshError_not_StealthRejected` | invalid_grant precedence regression | Plan 03 |
| bonus | `test_token_post_includes_no_x_api_key` | P0-4 wire-level x-api-key absent | Plan 03 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical pattern] Used try/except + pytestmark instead of pytest.importorskip**

- **Found during:** Task 2 execution
- **Issue:** The plan specified `pytest.importorskip("state_core.auth.providers.anthropic")` at module level, but this causes the ENTIRE test file to be skipped during collection (0 items collected), not individually collected-then-skipped. The acceptance criteria require `--collect-only` to list ≥17 tests by name.
- **Fix:** Used the canonical Phase 013 pattern: `try/except ImportError` at module top + `pytestmark = pytest.mark.skipif(not _AVAILABLE, reason=...)`. This results in 18 tests individually collected and then skipped.
- **Files modified:** `tests/auth/oauth_common/test_pkce.py`, `tests/auth/providers/test_anthropic.py`
- **Commit:** 8d2e5fa

## Issues Encountered

None — plan executed cleanly after the importorskip pattern deviation was corrected.

## Hand-off to Plan 02

Plan 02 (Wave 1 — foundation) must turn GREEN:
- `test_verifier_format`
- `test_client_id_matches_claude_code`
- `test_http_headers_user_agent_exact`
- `test_http_headers_anthropic_beta_exact`
- `test_http_headers_x_app`
- `test_http_headers_no_x_api_key`
- `test_is_expired_uses_300s_buffer`
- `test_token_response_ignores_unknown_field`
- `test_inject_stealth_system_prefix`
- `test_url_has_beta_true`
- `test_satisfies_authmethod_protocol`
- `test_paste_format_required`

## Hand-off to Plan 03

Plan 03 (Wave 2 — login/refresh implementation) must turn GREEN:
- `test_state_equals_verifier`
- `test_login_token_post_shape`
- `test_refresh_post_shape`
- `test_401_raises_stealth_rejected`
- `test_token_post_includes_no_x_api_key`
- `test_invalid_grant_in_refresh_raises_AuthRefreshError_not_StealthRejected`

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `tests/auth/oauth_common/__init__.py` | FOUND |
| `tests/auth/oauth_common/test_pkce.py` | FOUND |
| `tests/auth/providers/__init__.py` | FOUND |
| `tests/auth/providers/conftest.py` | FOUND |
| `tests/auth/providers/test_anthropic.py` | FOUND |
| Commit 2c1a157 (Task 1) | FOUND |
| Commit 8d2e5fa (Task 2) | FOUND |
| 18 tests collected | CONFIRMED |
| 18 tests skipped (all RED) | CONFIRMED |
| Existing auth suite (62 passed) | CONFIRMED |
