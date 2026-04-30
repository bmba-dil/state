---
phase: "016-antigravity-oauth-provider"
plan: "01"
subsystem: auth
tags: [oauth, antigravity, pkce, loopback, red-stubs, tdd]

# Dependency graph
requires:
  - phase: 015-gemini-cli-oauth-provider
    provides: "PKCE-with-loopback skeleton, oauth_common/loopback, oauth_common/pkce, errors.AuthLoginError/AuthRefreshError, conftest fixture patterns"
provides:
  - "22 RED test stubs in tests/auth/providers/test_antigravity.py mapped 1:1 to VALIDATION.md rows 016-02-01..016-04-07"
  - "2 antigravity-specific pytest fixtures in tests/auth/providers/conftest.py (mock_authorize_url_antigravity, captured_token_post_antigravity)"
  - "Hard-coded Antigravity constants embedded in test asserts (CLIENT_ID 1071006060591-..., CLIENT_SECRET GOCSPX-K58FWR486..., FIXED port 51121, localhost literal, 5-scope string, MACOS/LINUX/WINDOWS branches, google.antigravity provider_id) — the test file IS the spec"
  - "RED-state strategy: module-level try/except + pytestmark.skipif so collection succeeds before src/state_core/auth/providers/antigravity.py exists; per-test pytest.xfail(...) so each later plan only deletes one line to flip XFAIL -> GREEN"
affects: [016-02 helpers, 016-03 sync class, 016-04 async login/refresh, 022 cli golden-file regression, 019 round-robin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 RED-stub pattern: module-level skipif via try/except ImportError, body-drafted xfail per test — single-line GREEN-flip per stub"
    - "Constants-in-test-file pattern: verification contract decoupled from source-module existence; tests are runnable spec, not import-bound"
    - "Late-bind fixture pattern: monkeypatch on a late-imported module (mock_authorize_url_antigravity) is inert during Wave 0 collection but live once the module ships"

key-files:
  created:
    - tests/auth/providers/test_antigravity.py
  modified:
    - tests/auth/providers/conftest.py

key-decisions:
  - "Plan structures the RED stubs with try/except + pytestmark.skipif (test_google_gemini.py pattern) rather than module-level pytest.importorskip — the latter caused 0 tests to be collected at the file level."
  - "Each test body is drafted in full (not stubbed `pass`) and gated by a runtime `pytest.xfail(...)` call at function entry. Plans 02/03/04 only need to delete the single xfail line per test to turn XFAIL -> GREEN — preserves traceability and reduces churn."
  - "Antigravity constants are hard-coded in test asserts, not imported from the source module. The test file is the source of truth for AUTH-03's verification contract."
  - "23rd VALIDATION row (016-01-01) is the collection-only gate — satisfied by `pytest --collect-only tests/auth/providers/test_antigravity.py` succeeding. Not represented as a function in the test file."

patterns-established:
  - "RED-stub collection-safe header: try/except ImportError for the not-yet-existing module + pytestmark.skipif gates the whole file"
  - "VALIDATION row ID in every test docstring: `VALIDATION row 016-NN-NN` for plan-checker / verify-work mapping"
  - "Pitfall ID citation in stub docstrings (P1-3, P2-2, P2-3, Pitfall 4, Pitfall 5, Pitfall 6, Pitfall 10) — RED stubs encode threat-model surface"

requirements-completed: [AUTH-03]

# Metrics
duration: 22min
completed: 2026-04-30
---

# Phase 016 Plan 01: Antigravity Wave 0 RED Stubs Summary

**22 RED test stubs + 2 conftest fixtures encode the AUTH-03 verification contract for Antigravity OAuth — every Plan 02/03/04 turns its share of XFAILs to GREEN with single-line deletes.**

## Performance

- **Duration:** ~22 min
- **Tasks:** 2 (both `type="auto" tdd="true"`)
- **Files modified:** 2 (1 created, 1 extended)

## Accomplishments

- 22 test functions in `tests/auth/providers/test_antigravity.py` mapped 1:1 to VALIDATION.md rows 016-02-01 through 016-04-07
- 2 antigravity-specific pytest fixtures (`mock_authorize_url_antigravity`, `captured_token_post_antigravity`) appended to conftest.py — Phase 015 fixtures untouched (regression guard satisfied)
- All 22 stubs collect-but-skip cleanly in Wave 0 (module-level skipif gate); fully drafted bodies with per-test `pytest.xfail(...)` to flip XFAIL → GREEN one line at a time
- Phase 014 + Phase 015 tests still pass with zero regression: `124 passed, 23 skipped (1 prior + 22 new antigravity stubs)`
- Antigravity constants embedded as test-file literals (`1071006060591-…`, `GOCSPX-K58FWR486…`, `51121`, `localhost`, `cclog`, `experimentsandconfigs`, `MACOS/LINUX/WINDOWS`, `google.antigravity`) — test file is the spec; Plan 02 lands the constants in source and tests turn GREEN with no test-file edits

## Task Commits

1. **Task 1: Extend conftest.py with antigravity-specific fixtures** — `43e1845` (test)
2. **Task 2: Create test_antigravity.py with 22 RED-stub test cases** — `a62be8f` (test)

**Plan metadata:** _to be appended after this SUMMARY commits_

## Files Created/Modified

- `tests/auth/providers/test_antigravity.py` (created, 685 LOC) — 22 RED-stub test functions covering constants, helpers, sync class methods, async login/refresh, and `__main__` argparse paths. Each test body is fully drafted and gated by a single `pytest.xfail(...)` line at function entry.
- `tests/auth/providers/conftest.py` (extended, +77 LOC) — added two pytest fixtures at the bottom of the file:
  - `mock_authorize_url_antigravity`: late-binds monkeypatch on `state_core.auth.providers.antigravity.print` to capture authorize URLs (no-op in Wave 0 since the module does not yet exist)
  - `captured_token_post_antigravity`: 200-OK token-response dict with the 5-scope string and a 3-part JWT id_token decoding to `{sub: test_sub_antigravity, email: test@example.com, email_verified: true}`
  - Phase 015 fixtures (`mock_authorize_url`, `captured_token_post`, `fixture_gemini_*`, `mock_loopback_callback`, etc.) untouched.

## VALIDATION Row → Test Function Map

| VALIDATION Row | Test Function | Wave |
|---|---|---|
| 016-01-01 | _(file-level `pytest --collect-only` gate — Task 1)_ | 1 |
| 016-02-01 | `test_constants_plaintext` | 2 |
| 016-02-02 | `test_build_authorize_url` | 2 |
| 016-02-03 | `test_localhost_literal_in_redirect_uri` | 2 |
| 016-02-04 | `test_fixed_port_51121` | 2 |
| 016-02-05 | `test_five_scopes_present` | 2 |
| 016-02-06 | `test_id_token_parser` | 2 |
| 016-02-07 | `test_exchange_code` | 2 |
| 016-02-08 | `test_client_metadata_platform_detection` | 2 |
| 016-03-01 | `test_provider_id_dotted` | 3 |
| 016-03-02 | `test_is_token` | 3 |
| 016-03-03 | `test_is_expired_5min_buffer` | 3 |
| 016-03-04 | `test_http_headers_user_agent` | 3 |
| 016-03-05 | `test_http_headers_goog_api_client` | 3 |
| 016-03-06 | `test_http_headers_client_metadata_json` | 3 |
| 016-03-07 | `test_satisfies_authmethod_protocol` | 3 |
| 016-04-01 | `test_login_full_flow` | 4 |
| 016-04-02 | `test_refresh_rotation_persisted` | 4 |
| 016-04-03 | `test_refresh_no_rotation_keeps_old` | 4 |
| 016-04-04 | `test_state_and_verifier_independent` | 4 |
| 016-04-05 | `test_main_argparse_login` | 4 |
| 016-04-06 | `test_main_argparse_refresh` | 4 |
| 016-04-07 | `test_port_51121_in_use_error_message` | 4 |

## Decisions Made

- **RED-state strategy via skipif (not importorskip):** initial attempt used `pytest.importorskip("state_core.auth.providers.antigravity")` at module level, which caused `pytest --collect-only` to report "no tests collected" because the importorskip raised the skip *during collection* before pytest enumerated functions. Switched to the `try/except ImportError` + `pytestmark = pytest.mark.skipif(...)` pattern from `test_google_gemini.py` — collection now reports all 22 tests by name, and they all skip cleanly at run time. This is the established Phase 015 pattern; Phase 016 mirrors it byte-for-byte.
- **Body-drafted xfail per test:** each test contains a fully drafted assertion body preceded by a runtime `pytest.xfail("Plan NN ...")` call. Later plans flip XFAIL → GREEN by deleting the xfail line; the assertion logic was authored once at Wave 0 to keep the verification contract stable across waves.
- **Constants hard-coded in test asserts:** the test file embeds `1071006060591-tmhssin2h21lcre235vtolojh4g403ep`, `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`, `51121`, `localhost`, the 5-scope list, and `google.antigravity` directly. Plan 02 will land these as module constants in `src/state_core/auth/providers/antigravity.py`; the tests then validate the source matches the spec without test-file edits.
- **23rd VALIDATION row is the collection gate:** row 016-01-01 from VALIDATION.md is `pytest --collect-only tests/auth/providers/test_antigravity.py` succeeding at all — it's not a function in the test file. The plan's `<done>` block in Task 2 explicitly notes 22 functions collected (not 23).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Module-level `pytest.importorskip` collected 0 tests; switched to skipif gate**
- **Found during:** Task 2 (after first write of test_antigravity.py)
- **Issue:** The plan's `<action>` block suggested `antigravity = pytest.importorskip("state_core.auth.providers.antigravity", reason=...)` at module top. When the module doesn't exist on disk (Wave 0), `importorskip` raises Skipped *during collection*, so `pytest --collect-only` reported "no tests collected in 0.06s" — failing the success criterion of `≥22 tests`.
- **Fix:** Replaced with the `try/except ImportError` + `pytestmark = pytest.mark.skipif(not _ANTIGRAVITY_AVAILABLE, ...)` pattern that `tests/auth/providers/test_google_gemini.py` already uses successfully. Collection now reports all 22 tests by name; run-time skips are clean.
- **Files modified:** `tests/auth/providers/test_antigravity.py`
- **Verification:** `pytest --collect-only` now lists 22 tests; `pytest -q` shows `22 skipped`; full `tests/auth` suite shows `124 passed, 23 skipped` (1 prior + 22 new).
- **Committed in:** `a62be8f` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — collection-strategy correction)
**Impact on plan:** No scope creep; pattern aligned with Phase 015's working precedent; success criteria still met.

## Issues Encountered

None — both tasks completed cleanly. Test baseline (Phase 014 + Phase 015) was green at start (`124 passed, 1 skipped`) and remains green after Plan 01 (`124 passed, 23 skipped` — the 22 new skipped are intentional Wave 0 RED stubs).

## Self-Check: PASSED

- `tests/auth/providers/test_antigravity.py` exists ✓
- `tests/auth/providers/conftest.py` extended ✓
- `pytest --collect-only tests/auth/providers/test_antigravity.py` → 22 tests collected ✓
- `pytest tests/auth -q` → 124 passed, 23 skipped (no regression vs 124 passed baseline) ✓
- All 22 test names match VALIDATION.md row IDs ✓
- All test bodies drafted (not stubbed `pass`); each gated by `pytest.xfail(...)` ✓
- Antigravity literals present in test file: `1071006060591-…` (4×), `GOCSPX-K58FWR486…` (4×), `localhost` (12×), `51121` (19×), `cclog` (4×), `experimentsandconfigs` (4×), `MACOS/LINUX/WINDOWS` (16×), `google.antigravity` (17×), `antigravity` (89×) ✓
- Phase 015 conftest fixtures untouched (verified by Phase 015 tests still passing) ✓
- Commits: Task 1 `43e1845`, Task 2 `a62be8f` ✓

## Next Phase Readiness

- **Plan 02 (constants + helpers):** Ready. Plan 02 will create `src/state_core/auth/providers/antigravity.py` with `_CLIENT_ID`, `_CLIENT_SECRET`, `_REDIRECT_PORT`, `_REDIRECT_HOST_LITERAL`, `_REDIRECT_PATH`, `_SCOPES`, `_AUTHORIZE_URL`, `_TOKEN_URL`, `AntigravityTokenResponse`, `_GoogleIdTokenPayload` (or shared), `_parse_id_token_payload`, `_to_credential`, `_build_authorize_url`, `_exchange_code`, `_platform_for_client_metadata`, `_build_client_metadata`. Eight tests (016-02-01..016-02-08) flip XFAIL → GREEN.
- **Plan 03 (sync class):** Ready. `AntigravityAuth` class with `provider_id`, `is_token`, `is_expired`, `http_headers`. Seven tests (016-03-01..016-03-07) flip GREEN.
- **Plan 04 (async + __main__):** Ready. `login()`, `refresh()`, `_main()` argparse. Seven tests (016-04-01..016-04-07) flip GREEN.

No blockers. The verification contract is locked; Plans 02/03/04 implement against it.

---
*Phase: 016-antigravity-oauth-provider*
*Completed: 2026-04-30*
