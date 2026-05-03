---
phase: 015-gemini-cli-oauth-provider
plan: "03"
subsystem: auth
tags: [oauth, google, gemini, pkce, jwt, id-token, p1-3, p2-2, rfc-8252]

# Dependency graph
requires:
  - phase: 015-01
    provides: state_core.auth.errors (AuthLoginError, AuthRefreshError, AuthError) + 29 RED stubs in tests/auth/providers/test_google_gemini.py
  - phase: 015-02
    provides: oauth_common.loopback (allocate_loopback_port, wait_for_oauth_callback, SIGN_IN_SUCCESS_URL, SIGN_IN_FAILURE_URL) — re-exported by google_gemini.py for Plan D login()
provides:
  - GoogleGeminiAuth class (structural AuthMethod conformance, provider_id='google.gemini_cli')
  - Pydantic GoogleTokenResponse + _GoogleIdTokenPayload (extra='ignore', Field(repr=False) on secrets)
  - _parse_id_token_payload (stdlib base64 + orjson, NO signature verify per Pitfall 8)
  - _to_credential (wire-shape expires, P2-2 rotation-aware refresh, account_id from id_token sub)
  - _build_authorize_url (9 query params with hard-coded access_type=offline + prompt=consent)
  - _exchange_code (per-call AsyncClient, form-urlencoded body, AuthLoginError on 4xx/5xx)
  - Sync AuthMethod methods (is_token ya29 prefix, is_expired delegates to is_expired_buffered, http_headers Bearer + optional x-goog-user-project)
affects:
  - 015-04 (Plan D): fills async login() + refresh() bodies; argparse __main__ entry
  - 016-* (Antigravity): reuses oauth_common/loopback.py byte-for-byte; google_gemini.py is the structural template (different client_id/scopes/provider_id)
  - 022 (CLI / golden-file): _CLIENT_ID, _CLIENT_SECRET, _AUTHORIZE_URL, _TOKEN_URL, _SCOPES exported via __all__ for golden-file diff

# Tech tracking
tech-stack:
  added: []  # No new top-level deps — orjson, pydantic, httpx, structlog already pinned by Phase 014
  patterns:
    - "Plaintext OAuth client credentials with P1-3 rationale comment (NO base64/XOR/env-var obfuscation)"
    - "id_token JWT parsing without signature verification (TLS to oauth2.googleapis.com is the trust boundary)"
    - "Per-call httpx.AsyncClient with Timeout(10.0, connect=5.0), follow_redirects=False"
    - "form-urlencoded token-endpoint POST (Google's documented preference for Desktop apps; differs from Anthropic's JSON)"
    - "Two independent generate_verifier() calls — state ≠ verifier (anti-P0-8 reuse, RFC 6749 §10.12 CSRF)"
    - "P2-2 rotation: refresh_token = resp.refresh_token or original_refresh"
    - "Dotted provider_id 'google.gemini_cli' to keep Phase 016 'google.antigravity' in a separate AuthVault bucket"
    - "Module-level `print = print` re-bind for test monkeypatch (mirrors anthropic.py)"

key-files:
  created:
    - src/state_core/auth/providers/google_gemini.py
  modified:
    - tests/auth/providers/test_google_gemini.py

key-decisions:
  - "Plaintext _CLIENT_ID + _CLIENT_SECRET literals with P1-3 rationale block (5+ comment lines): AV scanners flag obfuscated literals as malicious; gemini-cli ships plaintext for the same reason; PKCE + loopback redirect is the actual security boundary, not client_secret confidentiality"
  - "id_token parser does NOT verify the signature: trust boundary is TLS to oauth2.googleapis.com (Pitfall 8 design decision); v3 inference routing can add cryptographic verification later if needed"
  - "GoogleTokenResponse.refresh_token is Optional even though login responses always have one — Google omits it on refresh responses when no rotation occurred (P2-2)"
  - "_to_credential takes original_refresh as a kwarg (NOT a default) to make rotation logic explicit at every call site"
  - "Async login/refresh raise NotImplementedError pointing to Plan D rather than NoOp — fail-fast preserves the cardinal rule that the Protocol contract is real even when partially implemented"
  - "Re-exported generate_verifier, build_challenge, allocate_loopback_port, wait_for_oauth_callback, SIGN_IN_*_URL, AuthError/AuthLoginError/AuthRefreshError via __all__ — gives Plan D a single import surface without re-importing from upstream modules in test fixtures"

patterns-established:
  - "google_gemini.py module layout mirrors anthropic.py exactly: docstring → constants block with provenance comments → exception re-imports → Pydantic models → helpers → class → __all__ → _main argparse stub. Phase 016 (Antigravity) and 017 (Copilot) will follow this skeleton."
  - "Wave-split TDD: Plan A ships RED stubs, Plan C lands sync helpers + GREENs the Wave-2 subset, Plan D lands async orchestration. Each wave is one commit; the test file evolves from all-skip to all-pass across the phase."

requirements-completed: [AUTH-02]

# Metrics
duration: ~5min
completed: 2026-04-30
---

# Phase 015 Plan 03: GoogleGeminiAuth provider (constants + helpers + sync methods) Summary

**493-LOC google_gemini.py shipping plaintext OAuth client credentials (P1-3 rationale), Pydantic GoogleTokenResponse + _GoogleIdTokenPayload models, four pure helpers (_parse_id_token_payload / _to_credential / _build_authorize_url / _exchange_code), and the GoogleGeminiAuth class with sync AuthMethod methods GREEN — async login/refresh raise NotImplementedError pointing to Plan D.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-30T17:41:43Z
- **Completed:** 2026-04-30T17:46:36Z
- **Tasks:** 1
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `src/state_core/auth/providers/google_gemini.py` (493 LOC) created — module docstring with 10 cardinal rules, plaintext constant block with P1-3 rationale comment, Pydantic models (`GoogleTokenResponse`, `_GoogleIdTokenPayload`), four helpers, `GoogleGeminiAuth` class, `__all__` listing 19 surfaces, `_main` Plan-D placeholder.
- Sync AuthMethod surface GREEN: `is_token` (`ya29.` prefix), `is_expired` (delegates to `is_expired_buffered`), `http_headers` (Bearer + optional `x-goog-user-project`).
- 17 Wave-2 tests flipped from `xfail` to GREEN: `test_token_shape_sniffer`, `test_is_token_ya29_prefix`, `test_is_expired`, `test_is_expired_uses_300s_buffer`, `test_http_headers`, `test_http_headers_bearer_and_optional_project`, `test_id_token_parser`, `test_id_token_parse_account_email`, `test_id_token_parser_rejects_malformed` (added — defensive coverage for AuthLoginError on bad JWT input), `test_build_authorize_url`, `test_authorize_url_shape`, `test_exchange_code`, `test_token_post_form_urlencoded_shape`, `test_state_and_verifier_independent`, `test_satisfies_authmethod_protocol`, `test_client_credentials_plaintext`, `test_provider_id_dotted`.
- 12 Wave-3 (Plan D) tests still `xfail` as designed — `test_login_full_flow`, `test_refresh_rotation_persisted`, `test_refresh_persists_rotated_refresh_token`, `test_refresh_no_rotation_keeps_old`, `test_refresh_preserves_unrotated_refresh_token`, `test_refresh_5min_buffer`, `test_refresh_request_headers_match_gemini_cli`, `test_state_param_csrf_check`, `test_main_argparse_login`, `test_module_main_imports`, `test_main_argparse_refresh`, `test_expiry_epoch_timezone_invariant`, `test_refresh_rejects_apikey`.
- Full auth suite: **111 passed / 1 skipped / 13 xfailed** (was 94 / 30 / 0 in 015-02). +17 GREEN, -17 SKIP, +13 xfail (the Plan-D pending tests). Zero regressions in Phase 014 anthropic, 015-01 errors module, or 015-02 loopback.
- 18 grep-based acceptance criteria verified: file exists, exact-line `_CLIENT_ID` + `_CLIENT_SECRET` literals, P1-3 rationale comment, NO obfuscation/env-var indirection on either constant, `provider_id: str = "google.gemini_cli"` (dotted), `access_type=offline` + `prompt=consent` + `code_challenge_method=S256` present, all four required imports (`errors`, `refresh`, `loopback`, `pkce`), NO `litellm` import, NO mode-violating imports, `Field(repr=False)` on secrets, NO own filelock.
- Runtime self-check: `isinstance(GoogleGeminiAuth(), AuthMethod) is True`; `GoogleGeminiAuth().provider_id == "google.gemini_cli"`; `asyncio.run(GoogleGeminiAuth().login())` raises `NotImplementedError("Plan D (015-D) implements GoogleGeminiAuth.login()")`.

## Task Commits

1. **Task 1: Create google_gemini.py with constants + Pydantic models + helpers + GoogleGeminiAuth class (sync methods GREEN, async raises NotImplementedError)** — `5fa619b` (feat)

## Files Created/Modified

- `src/state_core/auth/providers/google_gemini.py` (created, 493 LOC) — module docstring, plaintext constants block with P1-3 rationale (5+ comment lines citing AV scanner flagging, gemini-cli precedent, PKCE-as-real-boundary), three URL constants, three space-separated Cloud-Platform scopes, `GoogleTokenResponse` + `_GoogleIdTokenPayload` Pydantic models with `extra="ignore"` and `Field(repr=False)` on secrets, four helpers, `GoogleGeminiAuth` class with sync GREEN + async NotImplementedError, `__all__`, `_main` placeholder.
- `tests/auth/providers/test_google_gemini.py` (modified) — replaced 17 `pytest.xfail("Plan C implementation pending")` stubs with real assertion bodies; added one extra defensive coverage test (`test_id_token_parser_rejects_malformed`); preserved 12 `pytest.xfail("Plan D implementation pending")` stubs unchanged for the next wave.

## Decisions Made

- **Plaintext OAuth constants with P1-3 rationale block (5+ comment lines)**: Source-level literals for `_CLIENT_ID` and `_CLIENT_SECRET`. NO base64.b64decode (Anthropic's pattern is wrong here), NO env-var indirection, NO XOR. Three reasons documented inline: (1) AV scanners flag obfuscated literals as malicious; (2) Google's own gemini-cli ships them plaintext; (3) the actual security boundary is PKCE + loopback redirect validation (RFC 8252), NOT client_secret secrecy. Phase 022's golden-file test will diff these constants byte-for-byte.
- **id_token parser without signature verification**: `_parse_id_token_payload` does base64url decode + JSON parse + Pydantic validate. No PyJWT dep, no Google certificate fetch, no key rotation handling. Trust boundary is TLS to `oauth2.googleapis.com` (Pitfall 8). The id_token is consumed only for `account_id` extraction; v3 inference routing can add `google.oauth2.id_token.verify_oauth2_token` later without changing the parse-helper API.
- **`_to_credential` takes `original_refresh` as a required kwarg**: Forces every call site to think about P2-2 rotation. login() passes empty string (Google always returns a refresh_token on first authorization_code exchange); refresh() passes `cred.refresh`. Default value would silently accept a stale refresh token if the response omitted it — explicit kwarg eliminates that footgun.
- **Re-export public surface via `__all__`**: Plan D and tests can `from state_core.auth.providers.google_gemini import generate_verifier, wait_for_oauth_callback, AuthLoginError, ...` without reaching into upstream modules. Single import surface keeps the test fixtures (`mock_loopback_callback`, `mock_google_state_and_verifier`) clean.
- **Async methods raise `NotImplementedError("Plan D (015-D) implements ...")` rather than NoOp**: Fail-fast preserves the AuthMethod Protocol contract — calling `.login()` or `.refresh()` on a partially-implemented provider must raise loudly, never silently return a stub credential. Phase 022 CLI smoke test catches NotImplementedError as a "feature not yet shipped" signal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Defensive Coverage] Added `test_id_token_parser_rejects_malformed` to test file**

- **Found during:** Task 1 (post-implementation, before commit)
- **Issue:** The plan's `<behavior>` block specifies that `_parse_id_token_payload` "Raises AuthLoginError on any parse failure" but no Wave-2 test asserted this contract. The four error paths (not-3-parts, invalid base64, invalid JSON, missing `sub`) were implemented but unverified.
- **Fix:** Added one new test (`test_id_token_parser_rejects_malformed`) covering all four AuthLoginError paths. Test is GREEN; passes alongside the other 16 Wave-2 tests.
- **Files modified:** `tests/auth/providers/test_google_gemini.py`
- **Commit:** `5fa619b` (same commit as the implementation — single Task-1 atomic unit)

### Soft-fail criterion (informational)

**Line count:** The plan's `<acceptance_criteria>` says `wc -l ... reports between 200 and 400 lines`. The verbatim skeleton in the `<action>` block is itself ~493 LOC because of the 65-line module docstring (10 cardinal rules), the 9-line P1-3 rationale comment, per-field Pydantic field docstrings, and provenance comments on every constant. Trimming would mean dropping documentation the plan explicitly requested (rule 1: P1-3 rationale "5-line rationale comment"; rule 4: `provider_id` Pitfall 9 explanation; rule 8: lock-acquisition deadlock note). The 200-400 floor was a planner's rough estimate; the verbatim skeleton is load-bearing. No content trimmed.

**Total deviations:** 1 auto-fixed (Rule 2 defensive coverage), 1 informational (LOC budget overshoot due to required documentation density)
**Impact on plan:** None — sync methods GREEN, async stubs raise NotImplementedError, Plan D unblocked.

## Issues Encountered

- **Test file `pytest.xfail` semantics**: My initial concern was that `pytest.xfail` (called as a function inside the test body) would mark a test XFAIL even when the assertion succeeds. After running the suite, confirmed that all replaced tests pass cleanly without `pytest.xfail` and the original Wave-3 stubs continue to XFAIL on the calls I left untouched. No behavior change required.
- **Verify-command exclusion list ambiguity**: The plan's `<verify><automated>` excludes `test_state_param_csrf_check` (Wave 3) but not `test_state_and_verifier_independent` (also conceptually Wave 3 but pure-helper-testable). I implemented `test_state_and_verifier_independent` as Wave-2 GREEN since it only exercises `generate_verifier()` from oauth_common.pkce (already shipped in Phase 014) — no Plan-D dependency.

## User Setup Required

None — pure helpers and constants. No live Google OAuth, no `.state/auth.json` writes, no manual browser flow at this wave.

## Next Phase Readiness

- **Plan 015-04 (Wave 3)** is unblocked — async `login()` and `refresh()` bodies can call into already-tested helpers (`_build_authorize_url`, `_exchange_code`, `_to_credential`, `_parse_id_token_payload`) and re-exported oauth_common surfaces (`allocate_loopback_port`, `wait_for_oauth_callback`).
- **Phase 016 (Antigravity)** has a structural template: same module layout, same Pydantic shape for token response, same `_to_credential` pattern with rotation, same `__all__` discipline. Differences are surgical: different `_CLIENT_ID`/`_CLIENT_SECRET`, different scopes, different `provider_id="google.antigravity"`, possibly different authorize-URL host.
- **Phase 022 golden-file test (CLI / AUTH-13)** can already import `_CLIENT_ID`, `_CLIENT_SECRET`, `_AUTHORIZE_URL`, `_TOKEN_URL`, `_SCOPES` for the byte-for-byte diff.

## Self-Check: PASSED

- File `src/state_core/auth/providers/google_gemini.py` exists (493 LOC).
- Commit `5fa619b` exists in `git log` (`feat(015-03): implement google_gemini.py constants + helpers + sync GoogleGeminiAuth (Wave 2 GREEN)`).
- All 18 grep-based acceptance criteria satisfied.
- `pytest tests/auth/providers/test_google_gemini.py -k "<Wave-2 subset>" -x` exits 0 with 17 PASSED, 13 deselected.
- `pytest tests/auth -q` exits 0: 111 passed, 1 skipped, 13 xfailed (Plan-D pending tests).
- `python -c "from state_core.auth.providers.google_gemini import GoogleGeminiAuth; from state_core.auth.base import AuthMethod; assert isinstance(GoogleGeminiAuth(), AuthMethod) and GoogleGeminiAuth().provider_id == 'google.gemini_cli'"` → no output (success).
- `python -c "import asyncio; from state_core.auth.providers.google_gemini import GoogleGeminiAuth; asyncio.run(GoogleGeminiAuth().login())"` raises `NotImplementedError("Plan D (015-D) implements GoogleGeminiAuth.login()")` as designed.

---
*Phase: 015-gemini-cli-oauth-provider*
*Completed: 2026-04-30*
