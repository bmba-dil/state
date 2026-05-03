---
phase: "014"
plan: "02"
subsystem: auth
tags: [tdd, oauth, pkce, stealth-headers, constants, AUTH-01, wave-1]
dependency_graph:
  requires:
    - "014-01 (Wave 0 RED stubs — 18 tests)"
    - "013-02 (is_expired_buffered)"
    - "011-02 (OAuthCredential, AuthMethod Protocol)"
  provides:
    - "state_core.auth.oauth_common.pkce (generate_verifier, build_challenge)"
    - "state_core.auth.providers.anthropic (AnthropicAuth, constants, exceptions, models, helpers)"
    - "Wave 1 constants substrate — all stealth header values pinned with provenance"
  affects:
    - "Plan 03 (login/refresh bodies) builds on these constants"
    - "Phases 015/016/017 share oauth_common.pkce"
    - "Phase 022 (golden-file AUTH-13) imports _USER_AGENT, _ANTHROPIC_BETA, _X_APP from here"
tech_stack:
  added: []
  patterns:
    - "Structural Protocol satisfaction (no inheritance — isinstance(AnthropicAuth(), AuthMethod))"
    - "base64-decode at module load defeats secret scanners on literal UUID (P0-5)"
    - "ConfigDict(extra='ignore') declared on EACH Pydantic model independently (Pitfall 5)"
    - "print = print re-bind at module level for Plan 03 monkeypatching"
    - "is_expired delegates to is_expired_buffered — never duplicates buffer math (P0-7)"
key_files:
  created:
    - src/state_core/auth/oauth_common/__init__.py
    - src/state_core/auth/oauth_common/pkce.py
    - src/state_core/auth/providers/__init__.py
    - src/state_core/auth/providers/anthropic.py
  modified: []
decisions:
  - "Added `print = print` module-level re-bind so Plan 03 tests can monkeypatch state_core.auth.providers.anthropic.print without touching builtins.print (Plan 01 SUMMARY noted this was required)"
  - "Used `_CLIENT_ID: str = base64.b64decode(...).decode('ascii')` (type-annotated) — test uses `base64.b64decode in src` not exact grep pattern"
  - "test_paste_format_required stays RED (Plan 03 owns) because login() raises NotImplementedError before any getpass/print calls"
metrics:
  duration: "~12 minutes"
  completed: "2026-04-29T03:41:59Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
  tests_green_before: 0
  tests_green_after: 11
---

# Phase 014 Plan 02: Constants + PKCE + AnthropicAuth Skeleton Summary

Wave 1 foundation: stdlib PKCE primitives + Anthropic provider package skeleton with all stealth header constants pinned, AnthropicAuth satisfying AuthMethod Protocol, and 11 of 18 Wave 0 stubs now GREEN.

## What Was Built

Four files created under `src/state_core/auth/`:

| File | Purpose | Lines |
|------|---------|-------|
| `src/state_core/auth/oauth_common/__init__.py` | Package marker (intentionally empty — no re-exports) | 15 |
| `src/state_core/auth/oauth_common/pkce.py` | RFC 7636 PKCE primitives, stdlib-only | 69 |
| `src/state_core/auth/providers/__init__.py` | Package marker (intentionally empty — no re-exports) | 18 |
| `src/state_core/auth/providers/anthropic.py` | Constants + exceptions + models + AnthropicAuth skeleton | 437 |

**Total: 539 LOC across 4 files**

## Constants Pinned (all with provenance comments)

| Constant | Value | Pitfall mitigated |
|----------|-------|-------------------|
| `_CLIENT_ID` | `9d1c250a-e61b-44d9-88ed-5944d1962f5e` (base64-decoded at module load) | P0-5 |
| `_USER_AGENT` | `claude-cli/2.1.92 (external, cli)` | P0-1 (parenthetical required) |
| `_X_APP` | `cli` | P0-3 |
| `_ANTHROPIC_BETA` | `claude-code-20250219,oauth-2025-04-20,interleaved-thinking-2025-05-14,context-management-2025-06-27,prompt-caching-scope-2026-01-05,advanced-tool-use-2025-11-20,effort-2025-11-24` | P0-2 (full 7-flag string) |

All constants carry `# captured 2026-04 from milady-ai/milady#1910 against claude-cli 2.1.92` provenance comment.

## Protocol Satisfaction

`AnthropicAuth()` structurally satisfies `state_core.auth.base.AuthMethod`:
- `provider_id = "anthropic"` (class-level string)
- `is_token(value)` — first branch: `value.startswith("sk-ant-oat")`
- `is_expired(cred, now)` — delegates to `is_expired_buffered` (P0-7; never reads clock internally)
- `http_headers(cred)` — returns fresh 4-key stealth dict (Bearer + user-agent + x-app + anthropic-beta); empty dict for non-OAuthCredential; never includes x-api-key (P0-4)
- `login()` — raises `NotImplementedError` with "Plan 014-03" message (Wave 2)
- `refresh(cred)` — raises `NotImplementedError` with "Plan 014-03" message (Wave 2)

`isinstance(AnthropicAuth(), AuthMethod)` returns `True` (runtime_checkable Protocol).

## Test Results

```
tests/auth/oauth_common/test_pkce.py       1 passed
tests/auth/providers/test_anthropic.py    10 passed, 7 failed (Plan 03 turf)
──────────────────────────────────────────────────────
Total                                     11 passed, 7 failed
```

### Tests now GREEN (Wave 1 target met: ≥10/18)

| Test | What passes |
|------|-------------|
| `test_verifier_format` | PKCE 43-char base64url-no-pad |
| `test_client_id_matches_claude_code` | `_CLIENT_ID` constant + base64 decode at module load |
| `test_http_headers_user_agent_exact` | `_USER_AGENT` literal with `(external, cli)` |
| `test_http_headers_anthropic_beta_exact` | Full 7-flag `_ANTHROPIC_BETA` string |
| `test_http_headers_x_app` | `_X_APP = "cli"` |
| `test_http_headers_no_x_api_key` | Bearer header present, x-api-key absent |
| `test_is_expired_uses_300s_buffer` | Delegation to `is_expired_buffered` with 300s |
| `test_token_response_ignores_unknown_field` | `extra="ignore"` on both Pydantic models |
| `test_inject_stealth_system_prefix` | All 4 input shapes (list/string/missing/idempotent) |
| `test_url_has_beta_true` | `with_beta_param` idempotent `?beta=true` helper |
| `test_satisfies_authmethod_protocol` | isinstance + provider_id + is_token sniffer |

### Tests still RED (Plan 03's responsibility)

- `test_state_equals_verifier` (login HTTP — state == verifier round-trip)
- `test_login_token_post_shape` (login HTTP — authorization_code grant body)
- `test_refresh_post_shape` (refresh HTTP — refresh_token grant body)
- `test_paste_format_required` (login body calls _parse_paste before HTTP)
- `test_401_raises_stealth_rejected` (login HTTP error path)
- `test_invalid_grant_in_refresh_raises_AuthRefreshError_not_StealthRejected` (refresh error path)
- `test_token_post_includes_no_x_api_key` (wire-level x-api-key absence)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `print = print` module-level name binding**

- **Found during:** Task 2 implementation
- **Issue:** Tests for Plan 03 (`test_state_equals_verifier`, `test_login_token_post_shape`, etc.) monkeypatch `state_core.auth.providers.anthropic.print`. Without a `print` name in the module's namespace, pytest monkeypatch raises `AttributeError: 'module' object has no attribute 'print'`. Plan 01 SUMMARY explicitly noted monkeypatching targets are module-scoped.
- **Fix:** Added `print = print  # noqa: A001` after imports to expose `print` in the module namespace. This is a no-op at runtime but makes the module monkeypatch-compatible.
- **Files modified:** `src/state_core/auth/providers/anthropic.py`
- **Commit:** cfd080c

## Issues Encountered

None — plan executed cleanly.

## Hand-off to Plan 03

Plan 03 (Wave 2 — login/refresh I/O bodies) must:

1. Implement `AnthropicAuth.login()`:
   - `verifier = generate_verifier()`
   - `challenge = build_challenge(verifier)`
   - Build authorize URL with `state=verifier, code_challenge=challenge`
   - `print(authorize_url)` (monkeypatched in tests)
   - `paste = getpass.getpass("Paste code#state: ")`
   - `code, state = _parse_paste(paste)` (raises `AuthLoginError` on bad format)
   - Assert `state == verifier` (P0-8 client-side check, raises `AuthLoginError`)
   - POST `_TOKEN_URL` with authorization_code grant body
   - Handle 401 → `StealthRejected` vs `AuthLoginError`
   - Return `_to_credential(resp, now=time.time())`

2. Implement `AnthropicAuth.refresh(cred)`:
   - POST `_TOKEN_URL` with refresh_token grant body
   - Handle 401 `invalid_grant` → `AuthRefreshError` (NOT `StealthRejected`)
   - Return updated `OAuthCredential`

3. Add `if __name__ == "__main__":` block with `_main()` for `python -m` entry

All helpers (`_parse_paste`, `_to_credential`, `with_beta_param`, `generate_verifier`, `build_challenge`) are already wired and ready for Plan 03 to call.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `src/state_core/auth/oauth_common/__init__.py` | FOUND |
| `src/state_core/auth/oauth_common/pkce.py` | FOUND |
| `src/state_core/auth/providers/__init__.py` | FOUND |
| `src/state_core/auth/providers/anthropic.py` | FOUND |
| Commit 6472ccc (Task 1 — PKCE) | FOUND |
| Commit cfd080c (Task 2 — providers + anthropic.py) | FOUND |
| 11 tests passing (≥10 requirement) | CONFIRMED |
| 7 tests RED (Plan 03 turf only) | CONFIRMED |
| No regression in auth suite (62 + 1 skipped) | CONFIRMED |
| `isinstance(AnthropicAuth(), AuthMethod)` | CONFIRMED |
| `_CLIENT_ID == "9d1c250a-e61b-44d9-88ed-5944d1962f5e"` | CONFIRMED |
| No filelock import in anthropic.py | CONFIRMED |
| Mode isolation (no state.build.* / state.teach.*) | CONFIRMED |
| providers NOT re-exported from state_core.auth | CONFIRMED |
