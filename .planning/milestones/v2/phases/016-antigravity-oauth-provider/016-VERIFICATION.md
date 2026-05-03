---
phase: 016-antigravity-oauth-provider
verified: 2026-04-30T20:35:00Z
status: passed
score: 11/11 must-haves verified
re_verification:
  is_re_verification: false
---

# Phase 016: Antigravity OAuth Provider Verification Report

**Phase Goal:** Antigravity endpoints, scope list documented with Google discovery-doc link, refresh handling.
**Verified:** 2026-04-30T20:35:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                  | Status     | Evidence                                                                                                          |
| --- | ---------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | AntigravityAuth provider with `provider_id = "google.antigravity"`     | ✓ VERIFIED | `antigravity.py:460` — `provider_id: str = "google.antigravity"`; class at line 448                               |
| 2   | FIXED port 51121, literal `localhost` in redirect_uri                  | ✓ VERIFIED | `_REDIRECT_PORT: int = 51121` (line 141), `_REDIRECT_HOST_LITERAL: str = "localhost"` (line 140); used line 549   |
| 3   | 5 scopes (cloud-platform, userinfo.email, userinfo.profile, cclog, experimentsandconfigs) | ✓ VERIFIED | `_SCOPES` definition at lines 156-162 — all 5 scope URLs present, comment cites Google discovery doc URL          |
| 4   | Custom http_headers (Bearer + 3 antigravity-specific)                  | ✓ VERIFIED | `http_headers()` lines 488-512 — 4-key dict (`authorization` Bearer + `user-agent` + `x-goog-api-client` + `client-metadata`) |
| 5   | state ≠ verifier (two independent calls)                               | ✓ VERIFIED | `login()` lines 541-542 — two separate `generate_verifier()` calls; test_state_and_verifier_independent GREEN     |
| 6   | Refresh rotation `parsed.refresh_token or cred.refresh`                | ✓ VERIFIED | Line 670 verbatim P2-2: `new_refresh = parsed.refresh_token or cred.refresh` (grep returns 2 — source + docstring)|
| 7   | chmod 0600 vault preserved                                             | ✓ VERIFIED | `_main` uses Phase 012's `save_vault` (line 788); store.py enforces 0o600 via os.open + os.fchmod (refs verified) |
| 8   | No litellm, no `from filelock`, no `127.0.0.1` literal                 | ✓ VERIFIED | All three grep gates return 0; cardinal rules clean                                                               |
| 9   | python -m argparse login + refresh subcommands                         | ✓ VERIFIED | `--help` lists both subcommands; argparse implementation at lines 735-823                                         |
| 10  | All 22 antigravity tests GREEN                                         | ✓ VERIFIED | `pytest tests/auth/providers/test_antigravity.py` → 22 passed in 0.15s (no XFAIL, no SKIP)                        |
| 11  | Phase 014/015 tests still pass (no regression)                         | ✓ VERIFIED | `pytest tests/auth -q` → 146 passed, 1 skipped, 0 xfailed (was 124/1 baseline; +22 from Phase 016 = expected)     |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact                                              | Expected                                                                                          | Status     | Details                                                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------- |
| `src/state_core/auth/providers/antigravity.py`        | Complete AuthMethod implementation: constants, models, helpers, class, _main argparse            | ✓ VERIFIED | 827 LOC, all expected symbols present (constants, AntigravityTokenResponse, 6 helpers, class, __all__, _main) |
| `tests/auth/providers/test_antigravity.py`            | 22 GREEN tests mapped 1:1 to VALIDATION.md rows                                                   | ✓ VERIFIED | 663 LOC; `grep -c "^def test_\|^async def test_"` returns 22; all 22 pass                     |
| `tests/auth/providers/conftest.py` (extended)         | 2 antigravity fixtures (mock_authorize_url_antigravity, captured_token_post_antigravity)          | ✓ VERIFIED | Confirmed via Plan 01 SUMMARY + Phase 015 fixtures untouched (Phase 015 tests still GREEN)    |

### Key Link Verification

| From                                | To                                              | Via                                          | Status   | Details                                                                       |
| ----------------------------------- | ----------------------------------------------- | -------------------------------------------- | -------- | ----------------------------------------------------------------------------- |
| `AntigravityAuth.login`             | `wait_for_oauth_callback` (oauth_common)        | `await wait_for_oauth_callback(port=...)`    | ✓ WIRED  | Line 571-575 with kwarg `port=_REDIRECT_PORT`; OSError catch at 576-581       |
| `AntigravityAuth.login`             | `_exchange_code` (Plan 02 helper)               | `await _exchange_code(code, verifier, ...)`  | ✓ WIRED  | Line 589 — full code/verifier/redirect_uri arg flow                           |
| `AntigravityAuth.refresh`           | `_TOKEN_URL` via httpx.AsyncClient              | `client.post(_TOKEN_URL, data=body, ...)`    | ✓ WIRED  | Lines 631-639 — per-call AsyncClient + form-urlencoded                        |
| `AntigravityAuth.refresh`           | P2-2 rotation rule                              | verbatim source line                         | ✓ WIRED  | Line 670: `new_refresh = parsed.refresh_token or cred.refresh`                |
| `_main` refresh subcommand          | `refresh_credential` (Phase 013)                | `asyncio.run(refresh_credential(...))`       | ✓ WIRED  | Lines 805-807 — drives filelock-guarded path                                  |
| `AntigravityAuth.http_headers`      | `_build_client_metadata` + `_platform_for_*`    | nested function call                         | ✓ WIRED  | Line 511 — composed with platform detection per-call                          |
| `AntigravityAuth.is_expired`        | `is_expired_buffered` (Phase 013)               | delegation                                   | ✓ WIRED  | Line 486 — `return is_expired_buffered(cred, now)` (P0-7 single source)       |
| `_main` login persistence           | vault array invariant (P1-7)                    | `setdefault("google.antigravity", []).append`| ✓ WIRED  | Line 787 — preserves array shape                                              |

### Requirements Coverage

| Requirement | Source Plan        | Description                                              | Status      | Evidence                                                                                                          |
| ----------- | ------------------ | -------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------- |
| AUTH-03     | 016-01..016-04 (all 4 plans declare it) | Antigravity OAuth (custom flow, refresh handling) | ✓ SATISFIED | All 11 truths above PASS; full PKCE+loopback flow + refresh rotation + 5-scope OAuth + Antigravity-specific 4-header outbound dict; 22 tests cover the verification contract end-to-end. NOTE: REQUIREMENTS.md still shows `[ ]` for AUTH-03 — checkbox toggle is a separate housekeeping step (typically performed at milestone-close), not a code-side gap. |

No orphaned requirements: AUTH-03 is the sole requirement mapped to Phase 016 and is claimed by all 4 plans' frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | — | All 10 cardinal-rule grep gates pass | — | — |

Cardinal-rule grep gate results (from Step 7 scan):
- `127.0.0.1` literal: **0** (Pitfall 5 surface clean)
- `litellm` import: **0** (CLAUDE.md cardinal rule)
- `filelock`/`AsyncFileLock`/`from filelock`: **0** (refresh.py rule 9)
- `allocate_loopback_port`: **0** (Pitfall 4 — string absent from source)
- `state.build`/`state.teach`: **0** (mode isolation)
- `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` plaintext: **1** (P1-3 preserved verbatim)
- `1071006060591-tmhssin...` client_id: **1**
- `P1-3` rationale comments: **4**
- `P2-2` rotation rule (verbatim regex): **2** (source body + docstring)
- `generate_verifier()` calls: **5** (>= 2 required — state + verifier)
- `is already in use` (Pitfall 4 remediation copy): **1**

No TODO/FIXME/XXX/HACK/PLACEHOLDER markers in changed files.

### Human Verification Required

None for goal achievement. The following are explicitly out-of-scope for autonomous CI per Plan 04 (owned by Phase 022 CLI integration):

1. **Live OAuth login smoke** — `python -m state_core.auth.providers.antigravity login` against real Google OAuth endpoint (browser flow, FIXED port 51121 bind).
2. **Live refresh smoke** — `python -m state_core.auth.providers.antigravity refresh google.antigravity` exercising Phase 013's filelock-guarded path against real `oauth2.googleapis.com/token`.

These are owned by Phase 022 and do not affect Phase 016's verification status.

## Step 7b: Quality Findings

Skipped (quality.level: fast)

### Gaps Summary

No gaps. All 11 must-haves verified. Phase 016 goal achieved:
- AntigravityAuth provider lands with the correct `google.antigravity` provider_id and FIXED-port + literal-localhost loopback configuration.
- 5 scopes are declared with comments citing Google's discovery doc URL.
- Refresh handling implements verbatim P2-2 rotation rule and routes through Phase 013's filelock-guarded `refresh_credential` for end-to-end coordination.
- All 22 phase tests GREEN; full auth suite still GREEN (146 passed / 0 xfailed); zero regression in Phase 014/015.
- All cardinal-rule grep gates pass (no litellm, no filelock, no `127.0.0.1`, no `allocate_loopback_port`, plaintext _CLIENT_SECRET preserved).
- `python -m state_core.auth.providers.antigravity --help` lists both `login` and `refresh` subcommands; argparse fully wired to vault persistence (P1-7 array invariant via `setdefault(...).append(cred)`) and Phase 013's refresh path.

AUTH-03 functional contract is satisfied. The REQUIREMENTS.md `[ ]` → `[x]` toggle for AUTH-03 is a separate housekeeping action (typically at milestone-close) and does NOT represent a code-side gap.

---

_Verified: 2026-04-30T20:35:00Z_
_Verifier: Claude (gsd-verifier)_
