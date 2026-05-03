---
phase: 014
slug: anthropic-oauth-provider
status: clean-with-suggestions
reviewed: 2026-04-28
files_reviewed:
  - src/state_core/auth/oauth_common/pkce.py
  - src/state_core/auth/providers/anthropic.py
total_loc: 805
findings:
  critical: 0
  major: 0
  minor: 5
  style: 4
---

# Phase 014 Code Review

Advisory review of source-only changes (tests excluded — they exist as the contract). Phase 014 ships in 805 LoC across two modules with byte-for-byte stealth header pinning, full PKCE flow, and async login/refresh.

## Verdict

**CLEAN with suggestions.** No CRITICAL or MAJOR findings. The implementation is auditable, the precedence contract for `invalid_grant` vs stealth-rejection is enforced and visible in source order, and all 18 phase tests + 401 full-suite tests pass green. The 9 MINOR/STYLE items are linter-grade, not gating.

## Findings

### MINOR — Import ordering broken by `print = print` rebind
**File:** `src/state_core/auth/providers/anthropic.py:51-78`
**Issue:** Stdlib imports (lines 53-57) → `print = print` rebind (line 61) → more stdlib imports (lines 62-63) → third-party imports (lines 65-67) → first-party imports (lines 69-78). PEP 8 / isort would group imports first, then non-import code.
**Suggestion:** Move all imports to the top in standard groups; place the `print = print` rebind AFTER all imports with the existing comment intact.
```python
# After all imports:
print = print  # noqa: A001 — module-scoped re-bind for test monkeypatching
```

### MINOR — `# noqa: F401` annotations on `getpass` and `pkce` imports are incorrect
**File:** `src/state_core/auth/providers/anthropic.py:54, 75-78`
**Issue:** Both `getpass.getpass(...)` and `generate_verifier()` / `build_challenge()` are used inside `login()`. They are NOT unused — the `# noqa: F401` comments are misleading and will hide a real F401 if a future refactor drops the call.
**Suggestion:** Remove `# noqa: F401` from both. If ruff flags the `pkce` re-export line, change the comment to `# re-exported for downstream tests` (it's not actually re-exported via `__all__` either, so this could just be removed entirely).

### MINOR — Code duplication: `_exchange_code` and `refresh()` repeat ~30 LOC of HTTP-call + error-classification logic
**File:** `src/state_core/auth/providers/anthropic.py:366-424` (login path) and `558-659` (refresh path)
**Issue:** Both functions: build body → `async with httpx.AsyncClient(...)` → POST → status-code branching → invalid_grant precedence → stealth detection → fallthrough error → response-shape validation. The duplication is intentional for auditability of a security-critical surface, but a private `_post_token_endpoint(body, error_class) -> AnthropicTokenResponse` helper would eliminate ~30 LoC and reduce drift risk between the two paths.
**Suggestion:** Defer until Phase 015 (Gemini) or 016 (Antigravity) lands and confirms shared shape, then extract. As-is is acceptable per the YAGNI rationale already in the file.

### MINOR — `body_json: dict` could be `dict[str, Any]`
**File:** `src/state_core/auth/providers/anthropic.py:396, 614`
**Issue:** Bare `dict` type annotation loses key/value typing.
**Suggestion:** `body_json: dict[str, Any] = {}`. Same for `_is_stealth_rejection(body_json: dict)` parameter (line 328).

### MINOR — `resp.text[:500]` in error messages may echo provider-supplied content into logs
**File:** `src/state_core/auth/providers/anthropic.py:395, 613`
**Issue:** On 4xx/5xx, `body_text = resp.text[:500]` is included in error message via `{body_text!r}`. Anthropic's error bodies for these endpoints don't echo back the refresh_token, but a future server-side change could include it. The structlog redactor (Phase 020) is the second-line defense; until then, an exception traceback could land in stderr/logs without redaction.
**Suggestion:** Either truncate further (50 chars) or strip known token-shape patterns (`sk-ant-*`, `ya29.*`) before logging. Tracked as informational — Phase 020 owns the systematic redaction.

### STYLE — `inject_stealth_system_prefix` returns the same dict it mutates (list case) but builds new structure (string/missing case)
**File:** `src/state_core/auth/providers/anthropic.py:249-276`
**Issue:** Behavior is functionally consistent (caller's `body` reference stays valid), but the contract differs across the three input shapes. Caller cannot rely on "the returned dict is fresh" or "the input is unchanged."
**Suggestion:** Add to docstring: "Mutates *body* and returns it. Do NOT pass a body you want to preserve unchanged."

### STYLE — Long multi-line f-strings inside `raise` statements
**File:** Throughout, e.g., `src/state_core/auth/providers/anthropic.py:220-224, 533-539, 580-587`
**Issue:** Implicit concatenation inside f-strings makes diffs noisier and harder to grep.
**Suggestion:** Extract a constant for messages used in tests / Phase 022 CLI rendering — not for the one-shot internal errors.

### STYLE — `__main__` `_main()` returns 130 for KeyboardInterrupt but uses bare `print(..., file=sys.stderr)` instead of structlog
**File:** `src/state_core/auth/providers/anthropic.py:719-723`
**Issue:** Internally `log.info(...)` is used, but the `__main__` smoke surface bypasses structlog for human-readable output. Acceptable for the smoke surface; Phase 022's CLI will use rich/typer.

### STYLE — Module re-binds `print = print` inside the module rather than at the very top
**File:** `src/state_core/auth/providers/anthropic.py:61`
**Issue:** Combined with finding #1; the rebind happens between import groups.

## Strengths

- **Provenance comments on every stealth constant** (`# captured 2026-04 from milady-ai/milady#1910`) — auditable for future re-capture.
- **Precedence is source-readable** — `invalid_grant` lookup precedes `_is_stealth_rejection(` call in both `_exchange_code` and `refresh()` (verified by acceptance gate).
- **Defensive `assert` at module load** for `_CLIENT_ID` decode — fails LOUD if base64 string is corrupted.
- **`is_expired(self, cred, now)` cleanly delegates** to `is_expired_buffered` — no buffer math duplication, parameter-driven clock per Phase 011 Pattern 3.
- **No `filelock` import** — correctly defers concurrency to Phase 013's `refresh_credential` wrapper.
- **No `state.build.*` / `state.teach.*` imports** — mode isolation enforced.
- **`http_headers()` design note** explains why the `headers.pop("x-api-key", None)` is moot at this layer — preserves audit trail for v3 inference routing.
- **`AnthropicTokenResponse` and nested `AnthropicAccount` BOTH have `extra="ignore"`** — Pydantic v2 ConfigDict is per-model, declared correctly.
- **Test contract preserved** — 18/18 unit tests pass; full suite 401/401 (1 unrelated skip).

## Pre-Merge Manual Gate (CONTEXT-locked)

**Mitmproxy capture is still required before merging this branch to `main`.**

Run:
```bash
mitmproxy --mode regular  # or --mode reverse:https://api.anthropic.com
# then in another terminal: launch real Claude Code, complete one chat turn
# then diff captured headers against:
python3 -c "from state_core.auth.providers.anthropic import _USER_AGENT, _ANTHROPIC_BETA, _X_APP, _CLIENT_ID; print(repr(_USER_AGENT)); print(repr(_ANTHROPIC_BETA)); print(repr(_X_APP)); print(repr(_CLIENT_ID))"
```

The `(external, cli)` parenthetical and the full 7-flag `anthropic-beta` string MUST match captured traffic byte-for-byte.

## Recommendation

Optional cleanup PR for the import ordering + `# noqa: F401` corrections is worth ~15 minutes whenever convenient. Everything else is acceptable as-is.
