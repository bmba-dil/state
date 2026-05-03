---
phase: 015-gemini-cli-oauth-provider
plan: "01"
status: complete
date: 2026-04-30
commits:
  - 5e545b7 feat(015-01) promote AuthError hierarchy to state_core.auth.errors
  - be5046d test(015-01) add RED stubs for oauth_common.loopback + Phase 015 fixtures
  - a11fdbd test(015-01) add 29 RED stubs for google_gemini provider (AUTH-02)
requirements:
  - AUTH-02
---

# Plan 015-01 — RED test scaffold + promote `state_core.auth.errors`

## Outcome

Wave 1 complete. AuthError/AuthLoginError/AuthRefreshError now live in `state_core.auth.errors`. `providers/anthropic.py` re-imports them (identity-equivalent). 014 tests still pass. RED stubs landed: 9 loopback stubs + 29 gemini stubs (AUTH-02 validation map). Phase 014 untouched: 80/1 baseline preserved.

## Tasks

1. **errors module** — `src/state_core/auth/errors.py` created; classes moved out of `anthropic.py`; re-exported via identity-equivalent import.
2. **loopback RED stubs** — `tests/auth/oauth_common/test_loopback.py` + `__init__.py`; covers port-allocator, state-CSRF, error-param rejection, success/failure redirect, multi-request behavior. All RED (skipped pending Wave 2 implementation).
3. **gemini RED stubs** — `tests/auth/providers/test_google_gemini.py` (29 stubs ≥ VALIDATION map's 20-row floor); `tests/auth/providers/conftest.py` extended with 10 fixtures.

## Test Suite

- 85 passed, 39 skipped at end of plan (was 80/1; +5 GREEN errors, +9 RED loopback, +29 RED gemini, +1 fixtures init).

## Deviations

- Used `try/except + pytestmark.skipif` RED pattern (mirrors test_anthropic.py / test_pkce.py) instead of `pytest.importorskip` — required to satisfy "stub names must appear in --collect-only" must_have which `importorskip` would have skipped pre-collection.

## Key files

- `src/state_core/auth/errors.py` (new)
- `src/state_core/auth/providers/anthropic.py` (modified — re-imports)
- `tests/auth/test_errors.py` (new)
- `tests/auth/oauth_common/__init__.py`, `tests/auth/oauth_common/test_loopback.py` (new)
- `tests/auth/providers/test_google_gemini.py` (new)
- `tests/auth/providers/conftest.py` (modified)

Wave 2 (`015-02` loopback impl) is unblocked.
