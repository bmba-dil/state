---
phase: 015-gemini-cli-oauth-provider
plan: "04"
subsystem: auth
tags: [oauth, google, gemini, loopback, pkce, csrf, p2-2, rfc-8252, refresh-rotation, argparse]

# Dependency graph
requires:
  - phase: 015-01
    provides: state_core.auth.errors (AuthLoginError, AuthRefreshError) + RED stubs in tests/auth/providers/test_google_gemini.py
  - phase: 015-02
    provides: oauth_common.loopback (allocate_loopback_port, wait_for_oauth_callback, SIGN_IN_*_URL)
  - phase: 015-03
    provides: GoogleGeminiAuth class (sync methods GREEN; async raises NotImplementedError) + Pydantic models + helpers (_build_authorize_url, _exchange_code, _to_credential, _parse_id_token_payload)
provides:
  - Full GoogleGeminiAuth.login() body — loopback flow + CSRF gate + token exchange + credential construction
  - Full GoogleGeminiAuth.refresh() body — hand-rolled httpx + P2-2 rotation rule
  - `python -m state_core.auth.providers.google_gemini login|refresh [provider_id]` argparse entry-point
  - Phase 013 integration proven end-to-end via the `refresh` subcommand calling `refresh_credential`
affects:
  - Phase 016 (Antigravity) — structural template ready: same loopback flow, same refresh rotation pattern, swap _CLIENT_ID/_CLIENT_SECRET/_SCOPES + provider_id
  - Phase 022 (CLI) — `state auth login google.gemini_cli` Typer command will wrap the same login() coroutine
  - v3 inference routing — http_headers + cred.extras["project_id"] + cred.access ready for cloudcode-pa.googleapis.com calls

# Tech tracking
tech-stack:
  added: []  # All deps already pinned
  patterns:
    - "Loopback OAuth login: TWO independent generate_verifier() calls (state ≠ verifier) — RFC 6749 §10.12 CSRF + RFC 7636 PKCE are orthogonal"
    - "Hand-rolled refresh-token POST (NOT google-auth Credentials.refresh) for testability via pytest-httpx + symmetry with 014"
    - "P2-2 rotation rule verbatim: `new_refresh = parsed.refresh_token or cred.refresh` — opaque, no compare-and-skip"
    - "argparse subcommands: login (no args) + refresh [provider_id] [--idx N], default provider_id=google.gemini_cli"
    - "CLI persistence: ensure_initialized → load_vault → setdefault(provider_id, []).append(cred) → save_vault (chmod 0600 atomic)"
    - "Phase 013 integration via _main refresh subcommand: drives refresh_credential end-to-end (filelock + double-check + 15s wait_for cap)"
    - "POSIX SIGINT exit 130 on KeyboardInterrupt during interactive flow"

key-files:
  created: []
  modified:
    - src/state_core/auth/providers/google_gemini.py
    - tests/auth/providers/test_google_gemini.py

key-decisions:
  - "TWO independent `secrets.token_urlsafe(32)` calls for state and verifier — NOT P0-8's state==verifier reuse (Anthropic-only). Code comment cites RFC 6749 §10.12 + RFC 7636 + 2^-256 collision probability."
  - "Refresh hand-rolled (httpx form-urlencoded) instead of google-auth's Credentials.refresh() — enables pytest-httpx assertions on body shape + matches Phase 014's symmetry. Rotation logic auditable inline at the call site."
  - "invalid_grant precedence FIRST in refresh-error branching — refresh-token expiry is unambiguous; surfaces re-login remediation cleanly. Mirrors anthropic.py refresh()'s pattern (minus stealth-rejection branch which is Anthropic-specific)."
  - "_main argparse uses subparsers (login + refresh) rather than positional cmd — extends 014's single-command argparse cleanly. refresh subcommand drives Phase 013's refresh_credential, NOT the provider's refresh() directly — proves the filelock-guarded path."
  - "CLI persistence uses setdefault(provider_id, []).append — preserves array invariant (P1-7) and supports future multi-cred (Phase 019). NOT model_copy / direct assignment."
  - "Print 'Logged in as <email>' fallback chain: extras['email'] → account_id → '<unknown>'. Never echoes access/refresh tokens. KeyboardInterrupt exits 130 (POSIX SIGINT)."

patterns-established:
  - "google_gemini.py: loopback login() body is the structural template for Phase 016 (Antigravity). Difference vs. anthropic.py is the loopback wait_for_oauth_callback substitution for getpass-paste; everything else (verifier/challenge gen, authorize URL, _exchange_code, _to_credential, model_copy refresh) is shared shape."
  - "_main argparse pattern: subparsers + login/refresh + KeyboardInterrupt 130 + provider_id default + Phase 013 integration. Phase 016/017 will copy this verbatim with provider_id swap."

requirements-completed: [AUTH-02]

# Metrics
duration: ~10min
completed: 2026-04-30
---

# Phase 015 Plan 04: GoogleGeminiAuth login() + refresh() bodies + _main argparse Summary

**Filled the three async surfaces (login, refresh, _main argparse with login + refresh subcommands) on top of Plan C's frozen substrate — turning all 13 remaining Wave-3 tests GREEN, satisfying AUTH-02, and shipping a runnable smoke surface (`python -m state_core.auth.providers.google_gemini login|refresh`) that proves Phase 013's filelock-guarded refresh path end-to-end.**

## Performance

- **Duration:** ~10 min (start 2026-04-30T17:51:02Z, end 2026-04-30T18:00:34Z)
- **Tasks:** 3 (all type="auto", all tdd="true")
- **Files modified:** 2 (1 source, 1 test — no new files)
- **LOC added:** +258 net (src/google_gemini.py +138, tests/test_google_gemini.py +120)

## Accomplishments

- **`GoogleGeminiAuth.login()` body (Task 1)** — full loopback flow:
  1. TWO independent `generate_verifier()` calls — state (CSRF) and verifier (PKCE) are 43-char base64url-no-pad strings from independent `os.urandom(32)` draws. Comment cites RFC 6749 §10.12 + RFC 7636 + 2^-256 collision rate.
  2. `allocate_loopback_port()` → kernel-ephemeral port; `redirect_uri = f"http://127.0.0.1:{port}/oauth2callback"`.
  3. `_build_authorize_url(redirect_uri, state, challenge)` — already-tested helper from Plan C.
  4. `print(authorize_url)` to stdout — supports headless SSH copy-paste fallback (Phase 022 will add `webbrowser.open` + `--no-browser`).
  5. `await wait_for_oauth_callback(port, expected_state=state, timeout=300.0)` — CSRF gate.
  6. ONE `time.time()` read (determinism); `_exchange_code` → `_to_credential(resp, original_refresh="", now=now)`.
  7. structlog logs port + account_id + expires_in_seconds — never tokens.

- **`GoogleGeminiAuth.refresh()` body (Task 2)** — hand-rolled httpx with rotation:
  1. `isinstance(cred, OAuthCredential)` defensive guard → TypeError on ApiKeyCredential.
  2. Form-urlencoded body with 4 fields (grant_type, refresh_token, client_id, client_secret).
  3. Per-call `httpx.AsyncClient(Timeout(10.0, connect=5.0), follow_redirects=False)` — NO own filelock (Phase 013 owns it; rule 9).
  4. POST with `data=body` + `headers={"accept":"application/json"}` — NO Authorization header (refresh uses body credentials).
  5. Status >= 400: parse JSON safely, `invalid_grant` precedence FIRST → `AuthRefreshError(f"Refresh token rejected: {desc}")`, else generic `AuthRefreshError(f"refresh http {status}: {body[:500]!r}")`.
  6. ValidationError → `AuthRefreshError(f"refresh response shape: {exc}")`.
  7. **P2-2 ROTATION RULE VERBATIM:** `new_refresh = parsed.refresh_token or cred.refresh`.
  8. ONE `time.time()` read; `cred.model_copy(update={access, refresh, expires})` — preserves account_id + extras (project_id, email).
  9. structlog logs `rotated=parsed.refresh_token is not None` — fact of rotation, NEVER the token value.

- **`_main` argparse entry-point (Task 3)** — login + refresh subcommands:
  1. `argparse.ArgumentParser` with `add_subparsers(dest="cmd", required=True)`.
  2. `login` subcommand: `asyncio.run(GoogleGeminiAuth().login())` → KeyboardInterrupt → exit 130; AuthLoginError → stderr + exit 1; on success: `ensure_initialized` + `load_vault` + `setdefault.append` + `save_vault` (P1-7 array invariant; chmod 0600 atomic via Phase 012's `_atomic_write`); print `Logged in as <email or sub>`.
  3. `refresh [provider_id] [--idx N]` subcommand: `asyncio.run(refresh_credential(GoogleGeminiAuth(), args.provider_id, idx=args.idx))` — drives Phase 013's filelock-guarded path → KeyError → stderr + exit 1; AuthRefreshError → stderr + exit 1; print `Refreshed access_token for <provider_id>`.
  4. `python -m state_core.auth.providers.google_gemini --help` lists both subcommands.

- **Test results:** 13 previously-XFAIL tests flipped to GREEN. Full `tests/auth -q`: **124 passed / 1 skipped / 0 xfailed** (was 111/1/13 at end of 015-03; +13 GREEN, -13 XFAIL).
- **Cardinal-rule grep gates all PASS:** 5+ `generate_verifier()` calls, P2-2 rotation rule verbatim in source, NO `from filelock` / `AsyncFileLock`, NO `import litellm`, NO `state.build` / `state.teach` imports, plaintext `_CLIENT_SECRET` literal preserved, P1-3 rationale present.

## Task Commits

1. **Task 1: Implement GoogleGeminiAuth.login() body — loopback flow + CSRF gate** — `0c60dac` (feat)
2. **Task 2: Implement GoogleGeminiAuth.refresh() body — hand-rolled httpx + P2-2 rotation** — `4e21751` (feat)
3. **Task 3: _main argparse with login + refresh subcommands; integrate Phase 013** — `7a3a3f4` (feat)

## Files Created/Modified

- `src/state_core/auth/providers/google_gemini.py` (modified, 493 → 751 LOC; +258) — three async surfaces filled: login() body (~75 LOC), refresh() body (~110 LOC), _main argparse (~90 LOC). NotImplementedError stubs from Plan C all replaced.
- `tests/auth/providers/test_google_gemini.py` (modified, +120 LOC net) — 13 `pytest.xfail("Plan D implementation pending")` stubs replaced with full assertion bodies. Test count unchanged; XFAIL → PASS for 13 tests.

## Decisions Made

- **TWO independent `generate_verifier()` calls** for state and verifier — NOT P0-8's reuse pattern (Anthropic-specific). Inline comment cites RFC 6749 §10.12 (CSRF orthogonal to PKCE) + 2^-256 collision rate from independent `os.urandom(32)` draws. Test `test_state_and_verifier_independent` proves the assertion at runtime.
- **Hand-rolled refresh httpx POST** rather than `google.oauth2.credentials.Credentials.refresh()` — three reasons: (a) pytest-httpx body assertions require the wire-level call to be visible, (b) symmetry with Phase 014's anthropic.py refresh body keeps the pattern recognizable across providers, (c) inline rotation logic is auditable at the call site rather than buried inside google-auth's transport layer.
- **`invalid_grant` precedence FIRST** in refresh-error branching — `parsed.error == "invalid_grant"` is unambiguous (refresh-token expiry); surfacing it cleanly via `AuthRefreshError(f"Refresh token rejected: {desc}")` lets Phase 022 CLI render the "run state auth login google.gemini_cli" remediation. Mirrors 014 anthropic.py's pattern minus the stealth-rejection branch (Google does not have a stealth signal).
- **CLI vault persistence via `setdefault(provider_id, []).append(cred)`** — preserves the P1-7 array invariant (every provider value is a list, even for n=1). Future Phase 019 round-robin operates on the list directly.
- **`_main` refresh subcommand drives `refresh_credential`** (Phase 013), not the provider's `refresh()` directly — proves the filelock-guarded path end-to-end (lock acquire + double-check + 15s wait_for cap) at the integration boundary the user actually invokes.
- **KeyboardInterrupt during login → exit 130** (POSIX SIGINT) — matches Phase 014 pattern; lets shell scripts distinguish user-cancel from genuine login failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Environment] Pre-existing worktree+venv mismatch — added PYTHONPATH override**

- **Found during:** Task 2 verification (first pytest run after refresh body landed)
- **Issue:** The shared `.venv` at `/Users/tmac/projects/state/.venv` resolves the installed `state` package to `/Users/tmac/Projects/state/src/...` (the main checkout), not the worktree at `/Users/tmac/Projects/state/.claude/worktrees/agent-a1d263bc3ff1d7119/src/...`. As a result, the first invocation of `pytest tests/auth/providers/test_google_gemini.py -k refresh` loaded the OLD module body and the test failed with `NotImplementedError: Plan D implements GoogleGeminiAuth.refresh()` — even though my edit was already on disk in the worktree.
- **Fix:** Prefixed every test invocation with `PYTHONPATH=$PWD/src` to force the worktree's source to take precedence on `sys.path`. Verified via `python -c "import state_core.auth.providers.google_gemini as g; print(g.__file__)"` that the resolved path matches the worktree.
- **Files modified:** None — environment-level fix, not a source change.
- **Commit:** Folded into `4e21751` (Task 2) since it surfaced during Task 2 verification.

**2. [Rule 3 - Tooling state] Initial commit accidentally included `.planning/STATE.md` + `pyproject.toml` from soft-reset index**

- **Found during:** Task 1 commit
- **Issue:** The `git reset --soft 5fa619b` left the index populated with the previous HEAD's (5acaf88) older copies of these two files; `git add` of the auth files brought them along.
- **Fix:** `git reset --soft HEAD~1` + `git restore --staged` + `git checkout HEAD --` to restore the v2-state versions in the working tree, then re-staged ONLY the auth files and re-committed.
- **Files modified:** None (cleanup only).
- **Commit:** `0c60dac` is the corrected Task 1 commit; the original aborted commit `f82fd99` was discarded via reset.

### Soft-Fail Observation (informational)

**Test count vs. plan acceptance criteria** — the plan's `<verification>` section says "20+ tests PASSED". After Plan C, the file had 30 tests (all collected; 17 GREEN, 13 XFAIL). After Plan D, all 30 are GREEN (no SKIP, no XFAIL). The "20+" floor in the plan was a planner's rough estimate; actual count is 30. No content trimmed.

**Total deviations:** 2 auto-fixed (both Rule 3 environment / tooling), 1 informational (test count delta).
**Impact on plan:** None — all acceptance criteria met, all 13 Wave-3 tests GREEN, AUTH-02 requirement satisfied.

## Issues Encountered

- **Editor cache lag during early Task 1 edits:** The first round of `Edit` calls reported "updated successfully" but `grep` against the on-disk file showed unchanged content. After several diagnostic reads, the discrepancy resolved itself on subsequent Edit calls (likely an internal cache invalidation). Final verification via `grep` against the on-disk file confirmed every edit landed correctly. No source content lost.
- **Worktree Python venv pointer:** Documented above as Rule-3 deviation #1. Will recur on future plans against this worktree until the venv is rebound; mitigation is the `PYTHONPATH=$PWD/src` prefix on every pytest invocation.

## User Setup Required

None for this plan. Manual smoke (out of scope for autonomous verification — owned by Phase 022's CLI):

- `python -m state_core.auth.providers.google_gemini login` — opens browser flow against live Google OAuth, expects `.state/auth.json` to receive a `google.gemini_cli` entry with `ya29.*` access + `1//*` refresh + `account_id` from id_token sub claim.
- `python -m state_core.auth.providers.google_gemini refresh google.gemini_cli` — after the 5-min expiry buffer fires, expects vault to rewrite with rotated refresh_token (or preserve original if Google omitted).

## Next Phase Readiness

- **Phase 015 complete; AUTH-02 satisfied.** All 30 `tests/auth/providers/test_google_gemini.py` tests GREEN. Full auth suite: 124 passed / 1 skipped / 0 xfailed.
- **Phase 016 (Antigravity)** is unblocked — the structural template is now `google_gemini.py`. Differences will be surgical: `_CLIENT_ID`/`_CLIENT_SECRET` swap, possibly different scopes (Antigravity adds extras), `provider_id="google.antigravity"`, possibly different `_AUTHORIZE_URL` host. The loopback flow, refresh rotation, _main argparse pattern are all reusable verbatim shape.
- **Phase 022 (CLI)** can wrap `GoogleGeminiAuth().login()` and `refresh_credential(GoogleGeminiAuth(), ...)` into a Typer command; the smoke surface in `_main` is the integration baseline.
- **v3 inference routing** has the headers it needs: `auth.http_headers(cred)` returns `Authorization: Bearer ya29...` plus optional `x-goog-user-project` from `cred.extras["project_id"]`.

## Self-Check: PASSED

- File `src/state_core/auth/providers/google_gemini.py` exists (751 LOC).
- File `tests/auth/providers/test_google_gemini.py` exists (698 LOC).
- Commits exist in `git log`:
  - `0c60dac` (Task 1: login body)
  - `4e21751` (Task 2: refresh body)
  - `7a3a3f4` (Task 3: _main argparse)
- All cardinal-rule grep gates PASS:
  - 5+ `generate_verifier()` calls (≥ 2 required)
  - `new_refresh = parsed.refresh_token or cred.refresh` verbatim present
  - NO `from filelock` / `AsyncFileLock` / `import filelock`
  - NO `import litellm` / `from litellm`
  - NO `state.build.` / `state.teach.` imports
  - Plaintext `_CLIENT_SECRET: str = "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"` preserved
  - `P1-3` rationale comment block intact
- `python -m state_core.auth.providers.google_gemini --help` lists `login` and `refresh` subcommands.
- `pytest tests/auth -q` exits 0 with **124 passed, 1 skipped, 0 xfailed** (was 111/1/13 at end of 015-03; net +13 GREEN, -13 XFAIL).
- `pytest tests/auth/providers/test_google_gemini.py -q` exits 0 with **30 tests passing**, no SKIP, no XFAIL — Phase 015 complete.

---
*Phase: 015-gemini-cli-oauth-provider*
*Completed: 2026-04-30*
