---
phase: 016-antigravity-oauth-provider
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/state_core/auth/providers/antigravity.py
  - tests/auth/providers/test_antigravity.py
  - tests/auth/providers/conftest.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 016 Code Review — Antigravity OAuth Provider

**Status:** clean (2 info-level nits, both inherited from Phase 015 sibling)
**Depth:** standard
**Files reviewed:** 3 (1 source + 2 tests/fixtures)

## Summary

Phase 016 ships `AntigravityAuth` as a clean sibling of `GoogleGeminiAuth`
(Phase 015). All Phase 016-specific deltas land correctly and every cardinal
rule passes. No critical or warning issues.

### Phase 016-specific delta verification

- **Identity constants (P1-3 plaintext)** — `_CLIENT_ID` (`1071006060591-…`) and
  `_CLIENT_SECRET` (`GOCSPX-K58FWR486…`) present plaintext at lines 115–116
  with full P1-3 rationale block (lines 87–113) covering AV-flag, three-source
  cross-verification, and PKCE-as-real-boundary reasoning. Matches the
  hard-coded test assertion at `test_antigravity.py:78-83`.

- **5 scopes (P2-3)** — `_SCOPES` literal at lines 156–162 contains all five:
  `cloud-platform`, `userinfo.email`, `userinfo.profile`, `cclog`,
  `experimentsandconfigs`. Header comment block (lines 144–154) names P2-3 as
  this phase's owned pitfall and explains the 403/IAM_PERMISSION_DENIED
  consequence of drift. Regression-tested in `test_five_scopes_present`.

- **FIXED port 51121 (Pitfall 4)** — `_REDIRECT_PORT: int = 51121` at line 141.
  Source-text grep confirms `allocate_loopback_port` does NOT appear anywhere
  in the file (verified via `test_fixed_port_51121`). The exclusion of the
  helper from `__all__` (lines 705–707 with explicit comment) closes the
  re-export back-door.

- **Literal `localhost` (Pitfall 5)** — `_REDIRECT_HOST_LITERAL: str = "localhost"`
  at line 140. Module-wide grep for `127.0.0.1` returns zero matches. The
  redirect_uri is assembled with f-string interpolation at line 549, preserving
  the exact-string-match required by Google's OAuth pre-registration.

- **`provider_id = "google.antigravity"` (Pitfall 10)** — set as class attribute
  at line 460, threaded into `_to_credential` (line 315), login log facts (594),
  refresh log facts (627, 682). Sibling-bucket separation from
  `google.gemini_cli` is structural.

- **Custom outbound headers** — `http_headers` at lines 488–512 emits the
  4-key dict (`authorization` Bearer + `user-agent` literal `antigravity` +
  `x-goog-api-client` literal + `client-metadata` JSON). The `client-metadata`
  value is built per-call via `_build_client_metadata(_platform_for_client_metadata())`
  so `monkeypatch.setattr("sys.platform", ...)` works in tests. JSON keys are
  inserted in fixed order (`ideType` → `platform` → `pluginType`) to keep the
  AUTH-13 golden-file binding deterministic.

- **`is_token` returns True for `ya29.*` by design (Pitfall 6)** — line 478.
  Docstring explicitly notes the intentional collision with Gemini and that
  disambiguation lives at the routing layer via `provider_id`, never via token
  shape. Three `is_token` call paths are tested: `ya29.foo` → True, bare
  `ya29.` prefix → True, `sk-ant-foo`/`1//bar`/empty → False.

### Cardinal-rule checks

- **state ≠ verifier** — TWO independent `generate_verifier()` calls at lines
  541–542; `test_state_and_verifier_independent` patches the function with a
  counter and asserts `len(calls) == 2` and `calls[0] != calls[1]`.
- **P2-2 rotation rule** — `new_refresh = parsed.refresh_token or cred.refresh`
  at line 670 (verbatim). Both branches covered by `test_refresh_rotation_persisted`
  and `test_refresh_no_rotation_keeps_old`.
- **chmod 0600 vault** — `_main` login path (lines 776–791) routes through
  `state_core.auth.store.save_vault`, which carries the Phase-011 `_atomic_write`
  + `fchmod(0o600)` + `fsync` + atomic replace.
- **No `from filelock` import** — verified via grep; Phase 013's
  `refresh_credential` owns the lock and is invoked by `_main` (line 806).
- **No litellm imports** — verified; only `httpx` for the two `_TOKEN_URL` POSTs.
- **No `127.0.0.1` literal** — verified via grep across the source file.
- **AuthMethod Protocol conformance** — `test_satisfies_authmethod_protocol`
  runs `isinstance(AntigravityAuth(), AuthMethod)`; `runtime_checkable` Protocol
  validates structural presence of all five required attributes.
- **Determinism** — pure helpers (`_build_authorize_url`, `_to_credential`,
  `_exchange_code`, `_build_client_metadata`) take `now` / `state` / `verifier`
  / `platform` as parameters. Only `login()` / `refresh()` read `time.time()`
  once at entry (lines 583, 672).

### UX surfaces specific to FIXED port 51121

- **Port-collision error path (Pitfall 4)** — `OSError EADDRINUSE` from
  `wait_for_oauth_callback` is caught at line 576 and re-raised as
  `AuthLoginError` with explicit remediation copy ("port 51121 is already in
  use… Close any other state-cli antigravity-login process or wait for it to
  finish, then retry."). Regression-tested in
  `test_port_51121_in_use_error_message`.

- **Concurrent-CLI UX caveat (out of scope, advisory only)** — because the port
  is pre-registered with Google and cannot be moved, two simultaneous
  `state auth login google.antigravity` invocations on the same host always
  fail the second one. The remediation message is correct; no code change is
  recommended. Worth noting in the eventual user-facing CLI docs (Phase 022).

### Client-Metadata JSON injection surface (audited — clean)

The `Client-Metadata` header value is constructed by `_build_client_metadata`
(line 380). Inputs come from `_platform_for_client_metadata`, which returns one
of the four hard-coded literals `MACOS` / `LINUX` / `WINDOWS` / `LINUX`
(defensive fallback). No untrusted input flows into the JSON body. `orjson.dumps`
escapes safely, and the platform string is never user-supplied. No JSON-injection
attack surface.

## Critical Issues

None.

## Warnings

None.

## Info

### IN-01: `rotated=` log boolean diverges from persistence rule (inherited from Phase 015 IN-01)

- **File:** `src/state_core/auth/providers/antigravity.py:685`
- **Issue:** `rotated=parsed.refresh_token is not None` is `True` for an empty
  string `""`, but the persistence rule at line 670 (`new_refresh =
  parsed.refresh_token or cred.refresh`) treats `""` as "no rotation" via the
  `or` fallback. The two facts can disagree on the (extremely unlikely) edge
  case where Google returns `refresh_token: ""`. Pure observability nit; no
  behavior bug, no security implication. Carried over verbatim from Phase 015.
- **Fix:** `rotated=bool(parsed.refresh_token)` keeps log and persistence in
  lockstep. If Phase 015 is fixed, mirror here.

### IN-02: `print = print` re-bind appears between stdlib imports and third-party imports

- **File:** `src/state_core/auth/providers/antigravity.py:46`
- **Issue:** The intentional `print = print` re-bind (which enables
  `monkeypatch.setattr(module, "print", …)` in tests) sits at line 46, after
  `import base64 / sys / time` (38–40) and before `from typing import Any`
  (48), `import httpx` (51), etc. PEP 8 prefers all imports grouped before any
  module-level code. This will trip strict isort/ruff configs that don't already
  whitelist the pattern.
- **Fix:** Move the `print = print` line to immediately after the final import
  (e.g., after line 75), matching the layout that ruff/isort produce by default.
  Mirrors the sibling layout in `anthropic.py` and `google_gemini.py` — if
  those have the same quirk this is a project-wide convention and can be left
  alone. Either way, no behavior or security impact.

## Notes / Non-issues

- The XFAIL→GREEN flip discipline (test commits paired with implementation
  commits, never the same commit) is preserved across all four waves; the
  commit log shows `test(016-04): flip … xfails (RED)` immediately preceding
  each `feat(016-04): implement …` commit.
- `_main`'s broad `except Exception` at line 789 (vault persistence) is fine —
  it's CLI top-level and the user gets a clear `"Failed to persist credential
  to vault: …"` message with exit code 1.
- `body_json: dict = {}` then `body_json = resp.json()` inside `try/except
  Exception: pass` (lines 645–649) is intentional defense — Google sometimes
  returns non-JSON 4xx bodies (HTML 502 from edge proxies) and we MUST still
  surface a meaningful `AuthRefreshError`. The fall-through correctly skips
  the `invalid_grant` precedence branch and lands on the generic-status
  message.
- Test `test_state_and_verifier_independent` calls `asyncio.run` from a sync
  test body and wraps the call in `try/except Exception: pass`. This is
  acceptable: the test's sole assertion is on the `calls` counter, which is
  populated BEFORE any awaited I/O. If pytest-asyncio's strict mode is later
  enabled and complains, switch to `@pytest.mark.asyncio` and `await`.
- The `extras={}` initialization in `_to_credential` when `id_token` is absent
  (line 309) preserves the OAuthCredential extras-is-dict invariant. Tests do
  not currently exercise the no-id_token branch, but the path is defensive.

---

_Reviewed: 2026-04-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
