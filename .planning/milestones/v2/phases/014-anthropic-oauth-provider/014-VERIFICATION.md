---
phase: 014
slug: anthropic-oauth-provider
status: passed
goal_achieved: true
verified: 2026-04-28T23:59:59Z
score: 14/14 must-haves verified
---

# Phase 014 — Verification Report

**Phase Goal:** PKCE verifier reused as `state`, client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e` (base64-decoded at runtime), Bearer for `sk-ant-oat*`, headers `user-agent: claude-cli/<ver>` + `x-app: cli` + `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…`, 5-min expiry buffer, token-shape sniffer first branch.

**Verified:** 2026-04-28 23:59:59 UTC
**Status:** PASSED — Phase delivers goal. AUTH-01 satisfied.

---

## Must-Haves Cross-Check

| # | Must-have | Source-of-truth check | Status |
|---|-----------|----------------------|--------|
| 1 | `_CLIENT_ID == "9d1c250a-e61b-44d9-88ed-5944d1962f5e"` after base64-decode | `python3 -c "from state_core.auth.providers.anthropic import _CLIENT_ID; assert _CLIENT_ID == '9d1c250a-e61b-44d9-88ed-5944d1962f5e'"` | ✓ VERIFIED |
| 2 | `_USER_AGENT == "claude-cli/2.1.92 (external, cli)"` (P0-1) | Literal equality assertion in test + module constant | ✓ VERIFIED |
| 3 | `_X_APP == "cli"` (P0-3) | Module constant, tested exact match | ✓ VERIFIED |
| 4 | `_ANTHROPIC_BETA` == full 7-flag string starting `claude-code-20250219,oauth-2025-04-20,…` (P0-2) | Module constant, tested exact match | ✓ VERIFIED |
| 5 | `AnthropicAuth().is_token("sk-ant-oat01-xxx")` is True; `sk-ant-api03-xxx` is False | Token-shape sniffer first branch via `startswith("sk-ant-oat")` | ✓ VERIFIED |
| 6 | `http_headers(oauth_cred)` returns dict with keys exactly `{authorization, user-agent, x-app, anthropic-beta}` | Test asserts 4 keys, no x-api-key; grep confirms helper doesn't include it | ✓ VERIFIED |
| 7 | `is_expired(cred, now)` delegates to `is_expired_buffered` — 5-min buffer applied at AuthMethod layer | Test: 299s before expiry is True, 301s before is False | ✓ VERIFIED |
| 8 | PKCE state == verifier reuse: same string in authorize URL `state=` AND token POST `code_verifier=` (P0-8) | Test `test_state_equals_verifier` captures authorize URL, verifies POST body contains same verifier | ✓ VERIFIED |
| 9 | Token-endpoint POST carries exact authorization_code grant fields; no x-api-key header (P0-4 wire-level) | Test `test_login_token_post_shape` asserts body shape; test `test_token_post_includes_no_x_api_key` asserts header absent | ✓ VERIFIED |
| 10 | `AnthropicTokenResponse` parses payloads with unknown fields (`extra="ignore"` on both outer and nested models) | Test passes model with unknown field, verifies field is not present on parsed object | ✓ VERIFIED |
| 11 | On 401 invalid_grant → AuthRefreshError (NOT StealthRejected), even when description contains "Claude Code" (P0-7 regression) | Test `test_invalid_grant_in_refresh_raises_AuthRefreshError_not_StealthRejected`; code path pre-checks `body.get("error") == "invalid_grant"` BEFORE `_is_stealth_rejection()` | ✓ VERIFIED |
| 12 | `isinstance(AnthropicAuth(), AuthMethod)` is True (Protocol satisfaction) | Runtime check + 5 method signatures match Protocol contract | ✓ VERIFIED |
| 13 | Provider's `refresh()` does NOT acquire its own filelock (Phase 013 owns lock) | Grep: `! grep -q 'filelock\|AsyncFileLock' src/state_core/auth/providers/anthropic.py` | ✓ VERIFIED |
| 14 | `from state_core.auth.oauth_common.pkce import generate_verifier, build_challenge` works; returns base64url-no-pad strings | Test `test_verifier_format` asserts length ∈ [43, 128], no padding, high entropy | ✓ VERIFIED |

---

## Requirement Traceability

| REQ ID | Required by | Implemented in | Test | Status |
|--------|------------|-----------------|------|--------|
| AUTH-01 | Phase 014 | `src/state_core/auth/providers/anthropic.py` + `src/state_core/auth/oauth_common/pkce.py` | 18 unit tests (1 PKCE + 17 anthropic), all GREEN | ✓ SATISFIED |

---

## Pitfall Traceability (P0-1..P0-5, P0-7, P0-8)

| Pitfall | Mitigation in code | Test | Status |
|---------|-------------------|------|--------|
| P0-1 (user-agent parenthetical) | `_USER_AGENT = f"claude-cli/{_CLAUDE_CLI_VERSION} (external, cli)"` — constant with literal `(external, cli)` | `test_http_headers_user_agent_exact` asserts byte-for-byte equality | ✓ MITIGATED |
| P0-2 (anthropic-beta full 7-flag) | `_ANTHROPIC_BETA` module constant pinned with provenance comment `# captured 2026-04 from milady-ai/milady#1910` | `test_http_headers_anthropic_beta_exact` asserts full string, no substring shortcuts | ✓ MITIGATED |
| P0-3 (x-app) | `_X_APP = "cli"` constant | `test_http_headers_x_app` asserts literal equality | ✓ MITIGATED |
| P0-4 (Bearer not x-api-key) | `http_headers()` returns fresh 4-key dict with Authorization Bearer, explicitly no x-api-key. Per-call AsyncClient in login/refresh never sets x-api-key header. | `test_http_headers_no_x_api_key` asserts absence from dict + `test_token_post_includes_no_x_api_key` asserts absence from wire-level POST headers | ✓ MITIGATED |
| P0-5 (client_id discovery) | `_CLIENT_ID = base64.b64decode("OWQxYzI1MGEtZTYxYi00NGQ5LTg4ZWQtNTk0NGQxOTYyZjVl").decode("ascii")` evaluated at module load with import-time assert | `test_client_id_matches_claude_code` verifies constant + presence of base64 decode in source | ✓ MITIGATED |
| P0-7 (5-min buffer) | `is_expired()` delegates to `is_expired_buffered(cred, now)` from Phase 013, never duplicates buffer math | `test_is_expired_uses_300s_buffer` asserts boundary conditions (299s in, 301s out) | ✓ MITIGATED |
| P0-8 (PKCE state==verifier) | Single `generate_verifier()` call in `login()`, reused as both authorize URL `state=` param AND token POST `code_verifier=` field | `test_state_equals_verifier` monkeypatches `generate_verifier()` to fixture, captures authorize URL, confirms state==verifier in URL and POST body | ✓ MITIGATED |

---

## Test Suite

```
tests/auth/oauth_common/test_pkce.py                    1 passed
tests/auth/providers/test_anthropic.py                  17 passed
─────────────────────────────────────────────────────────────────
Total Phase 014 suite                                   18 passed ✓

Full auth suite (phases 011/012/013/014)               80 passed, 1 skipped
```

All 18 Wave 0 tests are GREEN:
- Row 014-01-01: `test_verifier_format` ✓
- Row 014-01-02: `test_state_equals_verifier` ✓
- Row 014-01-03: `test_client_id_matches_claude_code` ✓
- Row 014-01-04: `test_http_headers_user_agent_exact` ✓
- Row 014-01-05: `test_http_headers_anthropic_beta_exact` ✓
- Row 014-01-06: `test_http_headers_x_app` ✓
- Row 014-01-07: `test_http_headers_no_x_api_key` ✓
- Row 014-01-08: `test_is_expired_uses_300s_buffer` ✓
- Row 014-01-09: `test_login_token_post_shape` ✓
- Row 014-01-10: `test_refresh_post_shape` ✓
- Row 014-01-11: `test_token_response_ignores_unknown_field` ✓
- Row 014-01-12: `test_inject_stealth_system_prefix` ✓
- Row 014-01-13: `test_url_has_beta_true` ✓
- Row 014-01-14: `test_satisfies_authmethod_protocol` ✓
- Row 014-01-15: `test_paste_format_required` ✓
- Row 014-01-16: `test_401_raises_stealth_rejected` ✓
- Row 014-01-17: `test_invalid_grant_in_refresh_raises_AuthRefreshError_not_StealthRejected` ✓
- Bonus: `test_token_post_includes_no_x_api_key` ✓

---

## Manual Gates (Deferred)

### mitmproxy pre-merge capture
**Status:** CONTEXT-locked, manual responsibility of user before merge.

**Requirement:** Before merging Phase 014 to main, run real Claude Code through mitmproxy in regular mode, capture one chat turn, diff captured headers against the constants in `src/state_core/auth/providers/anthropic.py`. Both the `(external, cli)` parenthetical and the full `anthropic-beta` 7-flag string MUST match captured traffic.

**Why deferred:** Requires real Claude Code session + real Anthropic account. Cannot be automated in CI without leaking credentials. The constants are pinned to a known-good baseline (milady-ai/milady#1910, 2026-04); any drift discovered in the mitmproxy capture gates the merge.

**Evidence trail:** Documented in PR description before merge.

### Live Anthropic test
**Status:** Phase 022 release-smoke pipeline.

**Requirement:** Real OAuth flow against live Anthropic (gated behind `STATE_TEST_LIVE_ANTHROPIC=1` env var). Phase 014 ships only the hermetic unit tests.

---

## Anti-Patterns Found

None. Phase 014 is complete and clean:
- No TODO/FIXME comments in source code.
- No stub implementations (both `login()` and `refresh()` are fully implemented).
- No console.log-only methods.
- No bare `print()` debugging left in codebase.
- No lingering `NotImplementedError` (both async methods have bodies).
- No filelock import in provider (Phase 013 owns the lock).
- No `builtins.print` patches in tests (only module-scoped `state_core.auth.providers.anthropic.print`).
- No string-only `state` values (always reused verifier per P0-8).

---

## Verdict

**Status: PASSED**

Phase 014 goal achieved. AUTH-01 satisfied. All 18 Wave 0 tests GREEN. Phase 011/012/013 regression suite still 100%. All 14 must-haves verified in code.

**What works:**
- Anthropic OAuth stealth provider implemented byte-for-byte per spec.
- PKCE verifier/challenge primitives (stdlib-only, shared with phases 015/016/017).
- Token-shape sniffer first branch (`sk-ant-oat*`).
- 5-min buffer applied at AuthMethod layer via delegation to Phase 013 helper.
- Bearer auth (never x-api-key) for OAuth paths.
- `python -m state_core.auth.providers.anthropic login` entry-point for smoke-testing.
- invalid_grant precedence correctly enforced (checked BEFORE stealth heuristic in both login and refresh paths).
- All stealth headers pinned with provenance comments.

**Outstanding:** Pre-merge mitmproxy capture gate (user responsibility per CONTEXT.md).

---

_Verified: 2026-04-28 23:59:59 UTC_  
_Verifier: Claude (gsd-verifier)_  
_All must-haves passed. All tests green. Phase complete._
