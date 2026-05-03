---
status: clean
phase: 015-gemini-cli-oauth-provider
date: 2026-04-30
findings: 1
critical: 0
major: 0
minor: 0
info: 1
---

# Phase 015 Code Review — Gemini CLI OAuth Provider

**Status:** clean (1 info-level nit)
**Depth:** standard
**Files reviewed:** 8 source/test files

## Summary

All cardinal-rule checks pass:

- **P1-3 plaintext rationale** present (lines 121-129 of `google_gemini.py`); regression-tested via `test_client_credentials_plaintext`.
- **state ≠ verifier** (NOT P0-8 reuse) — two independent `generate_verifier()` calls; `test_state_and_verifier_independent` enforces.
- **P2-2 rotation rule** — `new_refresh = parsed.refresh_token or cred.refresh`; both branches covered by `test_refresh_rotation_persisted` + `test_refresh_no_rotation_keeps_old`.
- **chmod 0600 vault** — `_main` calls `save_vault` → routes through `store._atomic_write` (O_CREAT|0o600 + fchmod + fsync + atomic replace).
- **No `from filelock` import** in `google_gemini.py`. Phase 013's `refresh_credential` owns the lock.
- **No litellm imports** — only docstring rules; httpx is the only HTTP path.
- **AuthMethod conformance** — `test_satisfies_authmethod_protocol` runs `isinstance(GoogleGeminiAuth(), AuthMethod)`.
- **Determinism** — pure helpers take `now`/`state`/`verifier` as parameters; only `login()`/`refresh()` read `time.time()` once at entry.
- **`provider_id = "google.gemini_cli"`** (dotted) on line 393.
- **authorize URL** contains `access_type=offline` + `prompt=consent` (lines 324-325).
- **Loopback error handling** — timeout, malformed request, error= param, state mismatch, missing code all redirect to FAILURE_URL; finally-block cleanup; browser-prefetch defense around future resolution.
- **Pitfall coverage** — P1-3, P2-2, P0-7, Pitfall 4/5/7/8/9 all explicitly tested.
- **errors module promotion** — stdlib-only imports, identity-equivalent re-exports preserved in `anthropic.py`, `StealthRejected` stays Anthropic-specific.

## Critical Issues

None.

## Warnings

None.

## Info

### IN-01: `rotated=` log boolean slightly misleading on empty-string refresh_token

- **File:** `src/state_core/auth/providers/google_gemini.py:617`
- **Issue:** `rotated=parsed.refresh_token is not None` diverges from the persistence rule on line 602 (`new_refresh = parsed.refresh_token or cred.refresh`). Both `None` and `""` are treated as "no rotation" by the `or` fallback, but the log would record `rotated=True` for an empty string. Pure observability nit; no behavior bug.
- **Fix:** `rotated=bool(parsed.refresh_token)` keeps log + persistence in lockstep.

### IN-02 (advisory only): error= branch ordering in loopback

- **File:** `src/state_core/auth/oauth_common/loopback.py:142-160`
- **Issue:** `error=` branch runs before state-check. Per RFC 6749 §4.1.2.1 the auth server SHOULD include `state` in error responses, so defensive ordering would be state-check first, then error-check. As shipped, an attacker can trigger `AuthLoginError` without knowing state — but the listener is one-shot and they can't complete a login either way, so net gain is nil. Worth a hardening note for a future pass; not actionable for this phase.

## Notes / Non-issues

- `print = print` rebinding at `google_gemini.py:80` is intentional (mirrors `anthropic.py`); enables monkey-patching of `module.print` in tests. Already noqa'd.
- Bare `except (asyncio.TimeoutError, Exception):` at `loopback.py:178` is defensive cleanup inside `finally:`, on a one-shot listener that's already returning.
- `except Exception` at `google_gemini.py:233` is immediately re-raised as `AuthLoginError(...) from exc` — chain preserved.
- Hand-rolled httpx refresh (vs RESEARCH.md's google-auth recommendation) is a documented deliberate divergence (pytest-httpx body assertions, symmetry with Phase 014, auditability).

## Recommendation

No fixes required. Phase 015 is ready for verification.
