---
phase: "016-antigravity-oauth-provider"
plan: "03"
subsystem: auth
tags: [oauth, antigravity, authmethod-protocol, sync-class, http-headers]

# Dependency graph
requires:
  - phase: 016-02
    provides: "Constants, Pydantic models, 6 sync helpers (_parse_id_token_payload, _to_credential, _build_authorize_url, _platform_for_client_metadata, _build_client_metadata, _exchange_code), __all__ export list, 8 Wave-2 tests GREEN"
  - phase: 015-gemini-cli-oauth-provider
    provides: "GoogleGeminiAuth class shape (line-for-line precedent for sync methods, lines 378-512)"
  - phase: 013-filelock-guarded-refresh-lock
    provides: "is_expired_buffered (5-min buffer at AuthMethod layer per P0-7/AUTH-09)"
  - phase: 011-auth-foundations-credential-union-and-authmethod-protocol
    provides: "AuthMethod runtime_checkable Protocol + OAuthCredential frozen wire-shape"
provides:
  - "AntigravityAuth class implementing AuthMethod Protocol structurally — provider_id='google.antigravity', sync methods (is_token, is_expired, http_headers), async stubs (login, refresh) raising NotImplementedError citing Plan 04"
  - "_main() stub at module bottom + `if __name__ == '__main__'` guard — Plan 04 fills argparse"
  - "AntigravityAuth added to __all__ between helpers and entry-point block"
  - "7/7 Wave-3 tests GREEN (016-03-01..016-03-07): test_provider_id_dotted, test_is_token, test_is_expired_5min_buffer, test_http_headers_user_agent, test_http_headers_goog_api_client, test_http_headers_client_metadata_json, test_satisfies_authmethod_protocol"
affects: [016-04 async login/refresh body + __main__ argparse — fully unblocked]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AuthMethod-Protocol-by-structural-conformance: AntigravityAuth does NOT inherit from AuthMethod — runtime_checkable Protocol + isinstance() are sufficient. Same pattern as GoogleGeminiAuth (Phase 015) and AnthropicAuth (Phase 014)."
    - "is_token-affirmative-by-design: both google.gemini_cli and google.antigravity return True for `ya29.*` prefix (Pitfall 6). Provider disambiguation lives at the cred.provider_id layer, NEVER at token-shape sniffing."
    - "is_expired-as-pure-delegation: AntigravityAuth.is_expired(cred, now) is `return is_expired_buffered(cred, now)` — single line, never duplicates buffer math (P0-7/AUTH-09 single source of truth in refresh.py)."
    - "http_headers-4-header-trio: Bearer + (User-Agent literal 'antigravity') + (X-Goog-Api-Client 'google-cloud-sdk vscode_cloudshelleditor/0.1') + (Client-Metadata JSON computed per-call so sys.platform monkeypatch works in tests). No `x-goog-user-project` (different from Phase 015 — Antigravity attributes the project via Client-Metadata, set by loadCodeAssist boot)."
    - "Async-stubs-with-full-docstrings: login() and refresh() raise NotImplementedError citing Plan 04 BUT carry the full draft docstrings (steps 1-7 for login; rotation rule + AsyncClient lifecycle for refresh). Plan 04 swaps the body, keeps the docstring."

key-files:
  created: []
  modified:
    - src/state_core/auth/providers/antigravity.py
    - tests/auth/providers/test_antigravity.py

key-decisions:
  - "Reused google_gemini.py:378-512 as line-for-line template, with surgical swaps: provider_id literal, is_token unchanged (same prefix), is_expired unchanged (same delegation), http_headers REWRITTEN (4 headers vs 1-2), async stubs raise NotImplementedError instead of executing the body. The 80-LOC class lands in ~80 LOC — close to the plan's target."
  - "_main() also raises NotImplementedError instead of containing argparse-but-with-stub-subcommands. Reason: keeping `_main` body minimal makes Plan 04's diff small (single-function swap) and avoids carrying half-implemented argparse logic that could mask Plan 04 bugs."
  - "Class placed BETWEEN the helpers section and the __all__ list (order: imports → constants → models → helpers → AntigravityAuth class → __all__ → _main + entry guard). Mirrors google_gemini.py's structural ordering byte-for-byte."

patterns-established:
  - "Phase-016 is the SECOND example (after Phase 015) of the AuthMethod-Protocol-by-conformance pattern. Phase 017 (Copilot device-code) and Phase 018 (plain API key) will follow the same shape."

requirements-completed: []
requirements-progress:
  - "AUTH-03 (Antigravity OAuth): Wave 3 sync class complete; only Wave 4 async login/refresh + __main__ remain. Cumulative: 15/22 RED stubs flipped GREEN (8 from Plan 02 + 7 from Plan 03; Plan 04 will flip the remaining 7)."

# Metrics
duration: ~3min
completed: 2026-04-30
---

# Phase 016 Plan 03: AntigravityAuth Sync Class — Wave 3 GREEN

**AntigravityAuth class lands on top of Plan 02's substrate; all 7 Wave-3 verification tests flip XFAIL → GREEN; Phase 014/015 tests untouched; Plan 04 (async login/refresh + __main__) fully unblocked.**

## Performance

- **Duration:** ~3 min
- **Tasks:** 1 (`type="auto" tdd="true"` per plan)
- **Files modified:** 2 (1 source class added, 7 xfail lines removed in test file)

## Accomplishments

- `AntigravityAuth` class added to `src/state_core/auth/providers/antigravity.py` — file grew from 482 → 611 LOC (+129).
- **3 sync methods landed and GREEN:**
  - `is_token(value)` — provider-affirmative `ya29.*` sniffer (Pitfall 6 docstring inline). Returns True for ya29.foo, False for sk-ant-foo, False for 1//bar, False for "".
  - `is_expired(cred, now)` — delegates to `is_expired_buffered(cred, now)` (P0-7/AUTH-09 single source of truth). 4-min cred → True; 6-min cred → False.
  - `http_headers(cred)` — for OAuthCredential, returns 4-header dict (`authorization` Bearer, `user-agent: antigravity`, `x-goog-api-client: google-cloud-sdk vscode_cloudshelleditor/0.1`, `client-metadata` valid JSON with 3 keys). For non-OAuth, returns `{}`.
- **2 async stubs** (login, refresh) raise NotImplementedError citing Plan 04. Both carry full draft docstrings so Plan 04 only swaps the `raise` for the body.
- **`_main()` stub + `if __name__ == "__main__"` guard** also raise NotImplementedError citing Plan 04.
- **`AntigravityAuth` added to `__all__`** in the canonical position (after the helpers, before _main).
- **AuthMethod Protocol conformance verified:** `isinstance(AntigravityAuth(), AuthMethod)` returns True (runtime_checkable structural check; all 6 attributes present — `provider_id`, `is_token`, `is_expired`, `http_headers`, `login`, `refresh`).
- **All 7 Wave-3 tests GREEN** (was XFAIL):
  - `test_provider_id_dotted` (016-03-01)
  - `test_is_token` (016-03-02)
  - `test_is_expired_5min_buffer` (016-03-03)
  - `test_http_headers_user_agent` (016-03-04)
  - `test_http_headers_goog_api_client` (016-03-05)
  - `test_http_headers_client_metadata_json` (016-03-06)
  - `test_satisfies_authmethod_protocol` (016-03-07)
- **Wave-4 tests still XFAIL** (Plan 04 unblocked): `test_login_full_flow`, `test_refresh_rotation_persisted`, `test_refresh_no_rotation_keeps_old`, `test_state_and_verifier_independent`, `test_main_argparse_login`, `test_main_argparse_refresh`, `test_port_51121_in_use_error_message`.
- **Phase 014/015/oauth_common/Plan 02 — zero regressions.** Full `tests/auth` suite: `139 passed, 1 skipped, 7 xfailed` (was `132 passed, 1 skipped, 14 xfailed` before Plan 03; +7 passes from Wave-3 flips, -7 xfailed accordingly, the 7 remaining xfailed are intentional Plan-04 stubs).
- **All grep gates from `<verification>` pass:**
  - `grep -c 'class AntigravityAuth'` returns 1 ✓
  - `grep -c 'provider_id: str = "google.antigravity"'` returns 1 ✓
  - `grep -c 'is_expired_buffered'` returns 3 (≥1 required) — import line + module-doc reference + delegation site ✓
  - `grep -c 'Plan 04 implements'` returns 6 (≥2 required — login docstring, login raise, refresh docstring, refresh raise, _main raise, plus the 016-04-PLAN.md reference path appears twice) ✓
  - `grep -c '__all__'` returns 1 ✓
  - `grep -c 'isinstance(cred, OAuthCredential)'` returns 2 (http_headers guard + reference in `_to_credential` from Plan 02) ✓
  - `grep -c '127.0.0.1'` returns 0 (Pitfall 5 surface-cleanliness preserved) ✓
  - `grep -c 'allocate_loopback_port'` returns 0 (Pitfall 4 surface-cleanliness preserved) ✓

## Task Commits

1. **TDD RED — flip 7 Wave-3 xfails:** `40cb2ae` (test) — removes `pytest.xfail("Plan 03 …")` from 7 Wave-3 tests; all 7 fail with `AttributeError: module 'state_core.auth.providers.antigravity' has no attribute 'AntigravityAuth'`.
2. **TDD GREEN — implement AntigravityAuth class:** `ee4b332` (feat) — appends class + _main stub + entry guard, adds `AntigravityAuth` to `__all__`. All 7 Wave-3 tests pass; 0 regressions in tests/auth.

REFACTOR step intentionally skipped — implementation closely mirrors `GoogleGeminiAuth` per design (same shape, surgical header swap), no cleanup required.

## Files Created/Modified

- `src/state_core/auth/providers/antigravity.py` (modified, +129 LOC; 482 → 611):
  * `AntigravityAuth` class (~110 LOC including docstrings)
  * `_main()` stub + `if __name__ == "__main__"` guard (8 LOC)
  * `"AntigravityAuth"` added to `__all__` between helpers section and entry-point block
- `tests/auth/providers/test_antigravity.py` (modified, -7 LOC; 7 `pytest.xfail("Plan 03 …")` lines deleted to flip Wave-3 stubs from XFAIL to GREEN)

## VALIDATION Row → Test Function → State Map (Plan 03 scope)

| VALIDATION Row | Test Function | Wave | Before Plan 03 | After Plan 03 |
|---|---|---|---|---|
| 016-03-01 | `test_provider_id_dotted` | 3 | XFAIL | GREEN |
| 016-03-02 | `test_is_token` | 3 | XFAIL | GREEN |
| 016-03-03 | `test_is_expired_5min_buffer` | 3 | XFAIL | GREEN |
| 016-03-04 | `test_http_headers_user_agent` | 3 | XFAIL | GREEN |
| 016-03-05 | `test_http_headers_goog_api_client` | 3 | XFAIL | GREEN |
| 016-03-06 | `test_http_headers_client_metadata_json` | 3 | XFAIL | GREEN |
| 016-03-07 | `test_satisfies_authmethod_protocol` | 3 | XFAIL | GREEN |

Cumulative AUTH-03 progress: **15/22 RED stubs → GREEN** (8 from Plan 02 + 7 from Plan 03). Plan 04 owns the remaining 7 (Wave 4: login/refresh/_main).

## Decisions Made

- **Mirrored `GoogleGeminiAuth` (google_gemini.py:378-512) line-for-line as the class shape.** Only diffs from precedent: provider_id literal swap (`google.gemini_cli` → `google.antigravity`); http_headers body — 4-header dict instead of 1-2-header (no `x-goog-user-project` because Antigravity attributes project via Client-Metadata, not header); async login/refresh raise NotImplementedError instead of executing the body.
- **`_main()` raises NotImplementedError instead of carrying half-implemented argparse.** Plan 04 will swap a single-function body. Rationale: keeps Plan 04's diff minimal and avoids stub-argparse paths that could mask Plan 04 bugs in CI.
- **REFACTOR step skipped.** The implementation mirrors GoogleGeminiAuth precedent so closely that no cleanup pass is justified — adding refactor commits would be churn for churn's sake. Documented in the SUMMARY as a deliberate skip.
- **Class placed BETWEEN helpers section and __all__ list** (Plan 02 left the file ending with __all__; the canonical layout has class → __all__ → _main, matching google_gemini.py byte-for-byte).

## Deviations from Plan

None — the plan's `<action>` block was executed verbatim. Class structure, docstrings, method bodies, async stubs, _main stub, and __all__ entry all match the plan exactly.

**Total deviations:** 0
**Impact on plan:** Zero scope drift; Plan 04 fully unblocked.

## Authentication Gates

None — this plan is pure code/test landing; no live OAuth flows exercised.

## Issues Encountered

None — baseline (Phase 014 + 015 + oauth_common + Plan 01 RED + Plan 02 GREEN) was green at start (`132 passed, 1 skipped, 14 xfailed`); after Plan 03 it remains green (`139 passed, 1 skipped, 7 xfailed`) with the expected +7-pass / -7-xfail delta from Wave-3 flips.

## Self-Check: PASSED

- `src/state_core/auth/providers/antigravity.py` exists at 611 LOC ✓
- `class AntigravityAuth` present (grep -c returns 1) ✓
- All 7 Wave-3 tests GREEN: `pytest tests/auth/providers/test_antigravity.py::test_provider_id_dotted ... -v` reports `7 passed` ✓
- Phase 014/015/oauth_common/Plan 02 no regression: `pytest tests/auth -q` returns `139 passed, 1 skipped, 7 xfailed` ✓
- AuthMethod Protocol conformance: `isinstance(AntigravityAuth(), AuthMethod) is True` (verified via inline smoke-test) ✓
- All 8 grep gates pass (provider_id literal, is_expired_buffered ≥ 1, "Plan 04 implements" ≥ 2, __all__ present, isinstance OAuthCredential guard, no 127.0.0.1, no allocate_loopback_port symbol, class present) ✓
- Commits: TDD RED `40cb2ae`, TDD GREEN `ee4b332` ✓

## Next Phase Readiness

- **Plan 04 (async login/refresh + __main__):** Fully ready. Three swap points are in place:
  1. `AntigravityAuth.login()` body — generate two independent state/verifier strings (NOT P0-8 reuse), build redirect_uri with FIXED port 51121 + literal localhost (Pitfalls 4+5), build authorize URL via `_build_authorize_url`, print URL, await `wait_for_oauth_callback(port=51121, ...)` with OSError-EADDRINUSE → AuthLoginError translation, await `_exchange_code`, convert via `_to_credential`. The full draft docstring is already in place.
  2. `AntigravityAuth.refresh()` body — isinstance OAuthCredential guard, form-urlencoded 4-field POST to `_TOKEN_URL`, per-call `httpx.AsyncClient(Timeout(10.0, connect=5.0))`, invalid_grant precedence FIRST, P2-2 rotation `parsed.refresh_token or cred.refresh`, `cred.model_copy(update={...})`. Docstring already in place.
  3. `_main()` body — argparse with `login` and `refresh` subcommands, mirroring google_gemini.py:659-747 line-for-line with the constant swap. Sub-parsers, ensure_initialized, load/save_vault, exit codes 0/1/130 all reusable.

No blockers. AuthMethod-Protocol conformance is verified. Plan 04 is the last leaf of Phase 016.

---
*Phase: 016-antigravity-oauth-provider*
*Completed: 2026-04-30*
