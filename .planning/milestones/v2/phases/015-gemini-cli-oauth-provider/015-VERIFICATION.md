---
phase: 015-gemini-cli-oauth-provider
verified: 2026-04-30T18:15:00Z
status: passed
score: 12/12 must-haves verified
re_verification: null
---

# Phase 015: Gemini CLI OAuth Provider — Verification Report

**Phase Goal:** Desktop OAuth pattern, plaintext client_secret with rationale comment (NOT base64/XOR — P1-3), refresh-token rotation persisted on every refresh.
**Phase Requirement:** AUTH-02
**Verified:** 2026-04-30T18:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                       | Status     | Evidence                                                                                                                                                                                                                                       |
| -- | --------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | AuthMethod-conforming `GoogleGeminiAuth` exists with `provider_id = "google.gemini_cli"`                                    | ✓ VERIFIED | `src/state_core/auth/providers/google_gemini.py:381` declares `class GoogleGeminiAuth`, line 393 sets `provider_id: str = "google.gemini_cli"`. Runtime check `isinstance(GoogleGeminiAuth(), AuthMethod)` returns True (verified via venv).   |
| 2  | All 20+ validation-table tests pass under pytest                                                                            | ✓ VERIFIED | `pytest tests/auth/providers/test_google_gemini.py -q` → **30 passed in 0.09s**, 0 skipped, 0 xfailed. Exceeds 20-test floor; mirrors VALIDATION.md row IDs.                                                                                    |
| 3  | Refresh-token rotation persisted on every refresh (`response.refresh_token or current`)                                     | ✓ VERIFIED | `google_gemini.py:602`: `new_refresh = parsed.refresh_token or cred.refresh` — verbatim P2-2 rotation rule. Tests `test_refresh_rotation_persisted` and `test_refresh_no_rotation_keeps_old` both PASS.                                         |
| 4  | client_secret stored plaintext with P1-3 rationale comment                                                                  | ✓ VERIFIED | `google_gemini.py:132`: `_CLIENT_SECRET: str = "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"` (exact-line match). 9-line P1-3 rationale block at lines 121-129. NO `b64decode`, NO `os.environ`, NO XOR transform anywhere on `_CLIENT_*`.               |
| 5  | state ≠ verifier (two independent `generate_verifier()` calls)                                                              | ✓ VERIFIED | `google_gemini.py:471-472`: `state = generate_verifier()` then `verifier = generate_verifier()`. `grep -c "generate_verifier()" returns 5` (≥ 2 required). `test_state_and_verifier_independent` PASSES.                                        |
| 6  | Shared loopback module at `src/state_core/auth/oauth_common/loopback.py` (reusable for Phase 016)                           | ✓ VERIFIED | File exists, 199 LOC. Imports limited to `asyncio`, `socket`, `urllib.parse`, `state_core.auth.errors.AuthLoginError`. NO Gemini-specific URLs/scopes/client_id in module — provider-agnostic by design.                                        |
| 7  | `python -m state_core.auth.providers.google_gemini` supports `login` + `refresh` argparse subcommands                       | ✓ VERIFIED | `python -m state_core.auth.providers.google_gemini --help` prints both subcommands (verified at runtime). `_main()` uses `add_subparsers(dest="cmd", required=True)` with `login` and `refresh [provider_id] [--idx]`.                          |
| 8  | Errors module promoted; `anthropic.py` imports updated; identity-equivalent                                                 | ✓ VERIFIED | `src/state_core/auth/errors.py` defines `AuthError`, `AuthLoginError`, `AuthRefreshError`. `anthropic.py` re-imports via `from state_core.auth.errors import ...`. `test_anthropic_reexports_match_errors_module` asserts identity equivalence. |
| 9  | chmod 0600 preserved on vault writes                                                                                        | ✓ VERIFIED | `_main` login subcommand persists via Phase 012's `save_vault()` → `_atomic_write()` chain (chmod 0600). No direct `open(..., 'w')` writes in `google_gemini.py`. AUTH-06 contract preserved.                                                   |
| 10 | No `from filelock` import in google_gemini.py                                                                               | ✓ VERIFIED | `grep -E "AsyncFileLock\|^from filelock\|^import filelock" src/state_core/auth/providers/google_gemini.py` → empty. Refresh.py rule 9 satisfied (Phase 013's `refresh_credential` owns the lock).                                               |
| 11 | No litellm imports in OAuth code                                                                                            | ✓ VERIFIED | `grep -E "^import litellm\|^from litellm" src/state_core/auth/providers/google_gemini.py` → empty. Same check in `loopback.py` and `errors.py` → empty. CLAUDE.md cardinal rule preserved.                                                     |
| 12 | Phase 014 tests still pass (no regression)                                                                                  | ✓ VERIFIED | `pytest tests/auth -q` → **124 passed, 1 skipped** (matches latest baseline; was 80/1 pre-phase, now +44 GREEN with 0 regressions). Phase 014 anthropic suite (~17 tests) all GREEN.                                                            |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact                                              | Expected                                                                              | Status     | Details                                                                                                                                                                                              |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/auth/errors.py`                       | Three exception classes: AuthError, AuthLoginError, AuthRefreshError                  | ✓ VERIFIED | 72 LOC. All three classes defined with hierarchy. `__all__ = ["AuthError", "AuthLoginError", "AuthRefreshError"]`. Stdlib-only imports.                                                              |
| `src/state_core/auth/oauth_common/loopback.py`        | asyncio listener with `wait_for_oauth_callback`, `allocate_loopback_port`, URL consts | ✓ VERIFIED | 199 LOC. `asyncio.start_server` at line 186, browser-prefetch defense `if not code_future.done()` at lines 144/156/164/171, CSRF gate `state != expected_state` at line 150. Module docstring rule 1 enforces stdlib-only. |
| `src/state_core/auth/providers/google_gemini.py`      | Constants, Pydantic models, helpers, GoogleGeminiAuth class, _main argparse           | ✓ VERIFIED | 751 LOC. All sections present: docstring (rules 1-10), constants (lines 131-149), models (155-200), helpers (206-375), class (381-619), _main (659-747).                                            |
| `tests/auth/providers/test_google_gemini.py`          | 20+ assertion bodies covering VALIDATION.md rows                                      | ✓ VERIFIED | 698 LOC, 30 test functions (10 above floor). All PASS. Test names mirror 015-VALIDATION.md row IDs.                                                                                                  |
| `tests/auth/oauth_common/test_loopback.py`            | RED stubs flipped GREEN by Plan B                                                     | ✓ VERIFIED | 9 tests PASS (test_port_allocator, test_state_validation, test_redirect_handler, test_loopback_accepts_valid_callback, test_loopback_rejects_state_mismatch, test_loopback_rejects_error_param, test_loopback_redirects_to_google_pages, test_port_allocation_ephemeral, test_loopback_only_first_callback_wins). |
| `tests/auth/test_errors.py`                           | Hierarchy + identity-equivalent re-export tests                                       | ✓ VERIFIED | All tests PASS. Asserts `anthropic.AuthError is errors.AuthError` (identity, not equality).                                                                                                          |
| `tests/auth/providers/conftest.py`                    | Phase 015 fixtures (google_*, gemini_*, mock_loopback_callback)                       | ✓ VERIFIED | All fixtures defined and consumed by Wave-3 tests; no Phase 014 fixture name collisions.                                                                                                             |

### Key Link Verification

| From                                                                       | To                                            | Via                                                              | Status   | Details                                                                                                                                          |
| -------------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `providers/anthropic.py`                                                   | `state_core.auth.errors`                      | `from state_core.auth.errors import AuthError, ...`              | ✓ WIRED  | Verified via Phase 014 test `test_anthropic_reexports_match_errors_module` PASSING; identity equivalence holds.                                  |
| `providers/google_gemini.py`                                               | `state_core.auth.errors`                      | `from state_core.auth.errors import AuthError, AuthLoginError, AuthRefreshError` | ✓ WIRED  | Lines 95-99 of google_gemini.py.                                                                                                                 |
| `providers/google_gemini.py`                                               | `state_core.auth.refresh`                     | `from state_core.auth.refresh import is_expired_buffered`        | ✓ WIRED  | Line 100 of google_gemini.py. Used in `is_expired()` method.                                                                                     |
| `providers/google_gemini.py`                                               | `state_core.auth.oauth_common.pkce`           | `from ... import generate_verifier, build_challenge`             | ✓ WIRED  | Lines 101-104. Both used in `login()` body.                                                                                                      |
| `providers/google_gemini.py`                                               | `state_core.auth.oauth_common.loopback`       | `from ... import allocate_loopback_port, wait_for_oauth_callback, SIGN_IN_*_URL` | ✓ WIRED  | Lines 105-110. `wait_for_oauth_callback(port, expected_state=state, timeout=300.0)` invoked at line 494.                                          |
| `oauth_common/loopback.py`                                                 | `asyncio.start_server`                        | 127.0.0.1 listener with `handle(reader, writer)` coroutine       | ✓ WIRED  | Line 186 of loopback.py.                                                                                                                         |
| `oauth_common/loopback.py`                                                 | `state_core.auth.errors`                      | `from state_core.auth.errors import AuthLoginError`              | ✓ WIRED  | Line 49 of loopback.py.                                                                                                                          |
| `GoogleGeminiAuth.login`                                                   | `_exchange_code` (POST oauth2.googleapis.com) | helper from same module                                          | ✓ WIRED  | Line 502 of google_gemini.py: `resp = await _exchange_code(code, verifier, redirect_uri)`.                                                        |
| `GoogleGeminiAuth.refresh`                                                 | `https://oauth2.googleapis.com/token` (POST refresh_token) | hand-rolled httpx with `grant_type=refresh_token`        | ✓ WIRED  | Lines 552-572 of google_gemini.py. Form-urlencoded body, no Authorization header. `test_refresh_request_headers_match_gemini_cli` PASSES.         |
| `GoogleGeminiAuth.login`                                                   | `wait_for_oauth_callback`                     | `await wait_for_oauth_callback(port, expected_state=state)`      | ✓ WIRED  | Line 494 of google_gemini.py. CSRF gate (`expected_state=state`) wired.                                                                          |
| `GoogleGeminiAuth.login`                                                   | `generate_verifier` (TWO independent calls)   | first for state (CSRF), second for verifier (PKCE)               | ✓ WIRED  | Lines 471-472. Comment cites RFC 6749 §10.12 + 2^-256 collision rate.                                                                           |
| `_main`                                                                    | `state_core.auth.refresh.refresh_credential`  | `refresh` subcommand drives Phase 013                            | ✓ WIRED  | Line 726-731 of google_gemini.py: `from state_core.auth.refresh import refresh_credential` + `asyncio.run(refresh_credential(GoogleGeminiAuth(), args.provider_id, idx=args.idx))`. |

### Requirements Coverage

| Requirement | Source Plan(s)                                              | Description                                                                | Status      | Evidence                                                                                                                                                                                       |
| ----------- | ----------------------------------------------------------- | -------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUTH-02     | 015-01-PLAN, 015-02-PLAN, 015-03-PLAN, 015-04-PLAN          | Gemini CLI free-tier OAuth (google-auth-oauthlib, PKCE, refresh rotation)  | ✓ SATISFIED | All 12 truths verified. PKCE via `oauth_common.pkce.build_challenge` + `code_challenge_method=S256`. Rotation via `parsed.refresh_token or cred.refresh`. Hand-rolled httpx (NOT google-auth) — design deviation documented in 015-RESEARCH §Q1 with rationale (testability). All 30 provider tests + 9 loopback tests PASS. REQUIREMENTS.md still shows `[ ] AUTH-02` checkbox unchecked, but the implementation contract is fully satisfied; the checkbox flip is a separate roadmap-update concern. |

No orphaned requirements detected — REQUIREMENTS.md only maps AUTH-02 to Phase 015, and all four plans claim it.

### Anti-Patterns Found

| File                                              | Line  | Pattern                            | Severity | Impact                                                                                                                  |
| ------------------------------------------------- | ----- | ---------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/auth/oauth_common/loopback.py`    | 178   | `except (TimeoutError, Exception)` | ℹ️ Info  | Bare-Exception-with-tuple is documented as a hardening tweak in 015-02-SUMMARY (catches ConnectionResetError on browser keep-alive). Accepted deviation; no impact on goal. |
| `src/state_core/auth/providers/google_gemini.py`  | 80    | `print = print` rebind             | ℹ️ Info  | Intentional re-bind for testability (mirrors anthropic.py pattern). `# noqa: A001` suppresses lint. Documented; not a stub. |

No 🛑 Blocker or ⚠️ Warning findings. No `TODO`/`FIXME`/`PLACEHOLDER` strings in source. No `return null` / empty-implementation patterns.

## Step 7b: Quality Findings

Skipped (quality.level: fast)

### Human Verification Required

The following items require human/manual verification because they exercise live Google OAuth servers (out of scope for autonomous CI):

1. **End-to-end live login**
   - **Test:** `.venv/bin/python -m state_core.auth.providers.google_gemini login`
   - **Expected:** Browser opens (or URL is printed), user grants consent, `.state/auth.json` receives a `google.gemini_cli` entry with `ya29.*` access token, `1//*` refresh token, `account_id` from id_token sub claim, `extras["email"]` from id_token email. CLI prints `Logged in as <email>`.
   - **Why human:** Requires real Google OAuth consent flow + browser interaction.

2. **End-to-end live refresh after expiry buffer fires**
   - **Test:** Wait > (expires_in − 300s), then run `.venv/bin/python -m state_core.auth.providers.google_gemini refresh google.gemini_cli`
   - **Expected:** Vault is rewritten with new access token. If Google rotated, `refresh_token` is replaced; if not, original is preserved. CLI prints `Refreshed access_token for google.gemini_cli`. Phase 013's filelock-guarded path is exercised.
   - **Why human:** Requires real wall-clock elapsed time + live Google token endpoint.

3. **REQUIREMENTS.md checkbox flip**
   - **Test:** Verify whether AUTH-02 should now be marked `[x]` in `.planning/milestones/v2/REQUIREMENTS.md`.
   - **Expected:** Operator decision — implementation is complete; checkbox is currently `[ ]`. This is a roadmap-state concern, not a code concern.
   - **Why human:** Doc-state policy decision (per `commit_docs=false` in `.planning/config.json`).

### Gaps Summary

None — phase 015 achieves its goal. All 12 must-haves verified; AUTH-02 implementation contract satisfied; 124/1 test baseline matches expected; no regressions in Phase 014; cardinal rules (P1-3 plaintext, P2-2 rotation, no litellm, no own filelock, mode isolation) all grep-verified; key links wired end-to-end.

The two remaining concerns are external to the phase:
- AUTH-02 checkbox in `REQUIREMENTS.md` is informational (operator-controlled).
- Live Google OAuth smoke is owned by Phase 022 (CLI surface).

---

_Verified: 2026-04-30T18:15:00Z_
_Verifier: Claude (gsd-verifier)_
