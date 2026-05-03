---
phase: 017-github-copilot-device-code-flow
verified: 2026-04-30T20:44:26Z
status: passed
score: 16/16 must-haves verified
---

# Phase 017: GitHub Copilot Device-Code Flow Verification Report

**Phase Goal:** Device-code endpoint polling with 15-min countdown, grant-revocation detection (200-with-null-body), pydantic validation of refresh responses.
**Phase Requirements:** AUTH-04
**Verified:** 2026-04-30T20:44:26Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                            | Status     | Evidence                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | GitHubCopilotAuth provider with `provider_id = "github.copilot"`                                  | ✓ VERIFIED | `github_copilot.py:546` — `provider_id: str = "github.copilot"` (dotted namespace per Pitfall 9-info)                                    |
| 2   | Device-code state machine with 15-min monotonic deadline                                          | ✓ VERIFIED | `github_copilot.py:371-374` — `_PollingState(deadline=monotonic() + float(expires_in))`; expires_in defaults to 900s from RFC 8628        |
| 3   | Persistent `slow_down` increment (NOT reset; Pitfall 6)                                          | ✓ VERIFIED | `github_copilot.py:434-437` — `state.interval += _SLOW_DOWN_BUMP_S` mutates dataclass field; test_poll_slow_down_persists asserts [8,13,18] sleeps |
| 4   | 3-second safety margin between polls (Pitfall 10)                                                 | ✓ VERIFIED | `github_copilot.py:386` — `await sleep(state.interval + state.safety_margin)`; test_poll_safety_margin_3s asserts first sleep == 8.0      |
| 5   | `asyncio.CancelledError` propagates (NOT swallowed; Pitfall 9)                                    | ✓ VERIFIED | grep `except.*CancelledError` returns 0; test_poll_cancelled_via_signal asserts `pytest.raises(CancelledError)`                            |
| 6   | 200-with-null-body grant-revocation detection (P1-6)                                              | ✓ VERIFIED | `github_copilot.py:511-520` — `CopilotSessionResponse.token: str` required; ValidationError → AuthRefreshError("…likely grant revoked…")  |
| 7   | 401/403 grant-revocation paths                                                                    | ✓ VERIFIED | `github_copilot.py:500-504` — explicit 401/403 check raises AuthRefreshError("Copilot grant rejected"); test_mint_grant_revoked_401 GREEN |
| 8   | Pydantic validation of all GitHub responses (DeviceCodeResponse, PollResponse, CopilotSessionResponse) | ✓ VERIFIED | `github_copilot.py:188-238` — three Pydantic models with ConfigDict(extra='ignore') + Field(repr=False) on secret-bearing fields        |
| 9   | Two-tier token model (gho_* in `refresh`, tid_* in `access`, mirror in `extras["oauth_token"]`)   | ✓ VERIFIED | `github_copilot.py:662-682` — login() builds OAuthCredential with access=session.token (tid_*), refresh=oauth_token (gho_*), extras["oauth_token"] mirror |
| 10  | 5-min expiry buffer on `tid_*` only                                                                | ✓ VERIFIED | `github_copilot.py:580` — `is_expired` delegates to `is_expired_buffered` (Phase 013 / AUTH-09); test_is_expired_5min_buffer_session GREEN |
| 11  | Copilot stealth headers in http_headers (4 keys)                                                   | ✓ VERIFIED | `github_copilot.py:601-606` — exactly 4 keys: authorization, user-agent, editor-version, editor-plugin-version; test_http_headers_copilot_stealth GREEN |
| 12  | `refresh()` re-mints via copilot_internal/v2/token (does NOT call OAuth refresh endpoint)         | ✓ VERIFIED | `github_copilot.py:726` — `await _mint_session_token(cred.refresh, base_api=base_api)`; test_refresh_remints_session_no_oauth_call asserts /login/oauth/access_token NEVER hit |
| 13  | argparse login + refresh subcommands work                                                          | ✓ VERIFIED | `github_copilot.py:787-879` — argparse with login (--enterprise-url) + refresh (provider_id, --idx); test_main_argparse_login + test_main_argparse_refresh GREEN |
| 14  | All 26 validation tests GREEN                                                                      | ✓ VERIFIED | `pytest tests/auth/providers/test_github_copilot.py -v` reports 26 passed in 8.14s                                                       |
| 15  | No litellm, no `from filelock`, no oauth_common imports, no full `Ov23li8tweQw6odWQebz` substring | ✓ VERIFIED | grep gates: `from state_core.auth.oauth_common`=0, `import litellm`/`from litellm`=0, `from filelock`/`AsyncFileLock`=0, full `Ov23li8tweQw6odWQebz`=0 (only `Ov23li...` ellipsis warning markers) |
| 16  | Phase 014/015/016 tests still pass (no regression)                                                 | ✓ VERIFIED | `pytest tests/auth -q` reports 172 passed, 1 skipped (was 146 passed pre-phase, now 146 + 26 new = 172)                                  |

**Score:** 16/16 truths verified

### Required Artifacts

| Artifact                                              | Expected                                                                                                            | Status     | Details                                                                                  |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------- |
| `src/state_core/auth/providers/github_copilot.py`     | Constants + 3 Pydantic models + _PollingState + helpers + GitHubCopilotAuth class + _main argparse                  | ✓ VERIFIED | 884 LOC; all stubs filled; isinstance(GitHubCopilotAuth(), AuthMethod) is True            |
| `tests/auth/providers/test_github_copilot.py`         | 26 test cases mapped 1:1 to VALIDATION rows 017-02-01..017-04-10                                                   | ✓ VERIFIED | 1068 LOC; 26 GREEN, 0 XFAIL, 0 SKIP                                                      |
| `tests/auth/providers/conftest.py` (extension)        | 3 new fixtures (mock_device_code_response, mock_token_poll_responses, captured_session_mint_post)                  | ✓ VERIFIED | Phase 014/015/016 fixtures byte-identical (per 017-01-SUMMARY); 3 new fixtures appended  |

### Key Link Verification

| From                                       | To                                              | Via                                                       | Status   | Details                                                                                  |
| ------------------------------------------ | ----------------------------------------------- | --------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------- |
| github_copilot.py                          | state_core.auth.errors                          | `from state_core.auth.errors import …`                   | ✓ WIRED  | Lines 111-115 import AuthError, AuthLoginError, AuthRefreshError                         |
| github_copilot.py                          | state_core.auth.refresh                         | `from state_core.auth.refresh import is_expired_buffered` | ✓ WIRED  | Line 116; called in is_expired (line 580)                                                |
| github_copilot.py                          | state_core.auth.base                            | `from state_core.auth.base import …`                     | ✓ WIRED  | Lines 106-110 import AuthMethod, Credential, OAuthCredential                              |
| login()                                    | _request_device_code                            | `await _request_device_code(base_domain=base_domain)`     | ✓ WIRED  | Line 630                                                                                 |
| login()                                    | _poll_for_token                                 | `await _poll_for_token(device_code=…, …)`                 | ✓ WIRED  | Lines 650-655                                                                            |
| login()                                    | _mint_session_token                             | `await _mint_session_token(oauth_token, base_api=base_api)` | ✓ WIRED | Line 660                                                                                 |
| refresh()                                  | _mint_session_token                             | `await _mint_session_token(cred.refresh, base_api=base_api)` | ✓ WIRED | Line 726                                                                                 |
| _main()                                    | state_core.auth.refresh.refresh_credential      | `from state_core.auth.refresh import refresh_credential`  | ✓ WIRED  | Line 779; called in refresh subcommand at line 856                                       |
| _main()                                    | state_core.auth.store.{ensure_initialized, load_vault, save_vault, get_auth_json_path} | `from state_core.auth.store import …` | ✓ WIRED  | Lines 780-785; vault persistence at lines 836-840                                        |
| _poll_for_token                            | _PollingState                                   | `_PollingState(interval=float(initial_interval), deadline=monotonic()+float(expires_in))` | ✓ WIRED | Lines 371-374                                                                            |
| _poll_for_token                            | time.monotonic / asyncio.sleep                  | injectable kwargs (default time.monotonic / asyncio.sleep) | ✓ WIRED | Lines 332-333 signature; line 386 sleep call; lines 373, 420, 439 monotonic calls         |

### Requirements Coverage

| Requirement | Source Plan(s)                            | Description                                                                  | Status      | Evidence                                                                                                                              |
| ----------- | ----------------------------------------- | ---------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| AUTH-04     | 017-01, 017-02, 017-03, 017-04            | GitHub Copilot device-code flow (polling, grant-revocation handling)         | ✓ SATISFIED | RFC 8628 §3.5 polling state machine landed in `_poll_for_token` (5 outcomes, persistent slow_down, 3s safety margin, monotonic deadline, CancelledError propagation); grant-revocation via Pydantic-required `CopilotSessionResponse.token: str` (200-with-null-body) + 401/403 explicit check. All 26 validation tests GREEN. |

No orphaned requirements: `grep -E "Phase 017" .planning/milestones/v2/REQUIREMENTS.md` returns nothing beyond AUTH-04 declared in plans.

### Anti-Patterns Found

| File                                          | Line | Pattern                | Severity | Impact                                                                                  |
| --------------------------------------------- | ---- | ---------------------- | -------- | --------------------------------------------------------------------------------------- |
| (none)                                        | —    | TODO/FIXME/XXX/HACK    | —        | grep returns 0 across both source and test files                                         |
| (none)                                        | —    | placeholder/coming soon | —        | grep returns 0                                                                           |
| (none)                                        | —    | empty implementations  | —        | All async helpers + class methods have full bodies; only `_main` has `# pragma: no cover` annotation (covered by tests indirectly) |

### Cardinal-Rule Grep Gates (all pass)

| Gate                                                                 | Required | Actual                                       |
| -------------------------------------------------------------------- | -------- | -------------------------------------------- |
| `Iv1.b507a08c87ecfe98` count                                         | ≥ 1      | 5 (literal + docstring/comment markers)      |
| Full wrong client_id `Ov23li8tweQw6odWQebz`                          | 0        | 0 (only `Ov23li...` ellipsis pedagogical warnings — intentional) |
| `from state_core.auth.oauth_common`                                  | 0        | 0                                            |
| `^import litellm` / `^from litellm`                                  | 0        | 0                                            |
| `^from filelock` / `^import filelock` / `AsyncFileLock`              | 0        | 0                                            |
| `state\.build\.` / `state\.teach\.`                                  | 0        | 0                                            |
| `_CLIENT_SECRET`                                                     | 0        | 0                                            |
| `monotonic()`                                                        | ≥ 2      | 6                                            |
| `time\.time()`                                                       | 0        | 0                                            |
| `+ state.safety_margin` / `+ _POLLING_SAFETY_MARGIN_S`               | ≥ 1      | 3                                            |
| `state.interval += _SLOW_DOWN_BUMP_S` AND `state.interval = float(parsed.interval)` (combined) | ≥ 2 | 2 |
| `except.*CancelledError`                                             | 0        | 0                                            |
| `copilot_internal/v2/token`                                          | ≥ 1      | 12                                           |

### Test Run Output

```
$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/auth/providers/test_github_copilot.py -v
26 passed in 8.14s

$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/auth -q --tb=line
172 passed, 1 skipped in 44.74s
```

- 172 passed = 146 baseline + 26 new (matches expected delta)
- 1 skipped = pre-existing baseline skip (unchanged)
- 0 xfailed (was 26 xfailed at end of Wave 0; all flipped to GREEN by Plans 02/03/04)
- Zero regression on Phase 014 / 015 / 016 surfaces

### Step 7b: Quality Findings

Skipped (quality.level: fast)

### Human Verification Required

None — all goal-backward checks verifiable programmatically. Live device-code login against github.com is documented in 017-04-SUMMARY's "Manual Smoke Surface" section but is OPTIONAL (not a goal-blocking verification — the unit tests exhaustively exercise the state machine and exception precedence).

### Gaps Summary

No gaps. AUTH-04 is fully satisfied. The phase delivers the complete two-tier token architecture (gho_* OAuth token in `refresh`, tid_* session token in `access`, server epoch in `expires`, mirror in `extras["oauth_token"]`), the RFC 8628 §3.5 polling state machine with all 5 outcomes (success / authorization_pending / slow_down with persistent increment / expired_token / access_denied), all four NEW OWNED pitfalls addressed (Pitfall 6 slow_down persistence, Pitfall 7 monotonic deadline, Pitfall 9 CancelledError propagation, Pitfall 10 3-second safety margin), Pitfall 4 / P1-6 grant-revocation detection via Pydantic-required `CopilotSessionResponse.token: str`, and the argparse smoke surface with login + refresh subcommands wired into Phase 012's vault persistence (chmod 0600) and Phase 013's filelock-guarded refresh path.

---

_Verified: 2026-04-30T20:44:26Z_
_Verifier: Claude (gsd-verifier)_
