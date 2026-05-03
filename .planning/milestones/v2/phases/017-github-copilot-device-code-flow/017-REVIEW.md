---
phase: 017-github-copilot-device-code-flow
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/state_core/auth/providers/github_copilot.py
  - tests/auth/providers/test_github_copilot.py
  - tests/auth/providers/conftest.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: clean
---

# Phase 017 Code Review — GitHub Copilot Device-Code OAuth Provider

**Status:** clean (1 warning is a test-side perf/correctness nit, 4 info-level
nits inherited or low-impact). All cardinal rules pass. All Phase 017-specific
deltas land correctly.
**Depth:** standard
**Files reviewed:** 3 (1 source `github_copilot.py` + 1 new test file +
modified conftest)

## Summary

Phase 017 ships `GitHubCopilotAuth` as the fourth concrete `AuthMethod`
implementation and the FIRST without a loopback HTTP listener. The RFC 8628
device-code state machine, two-tier token mapping
(`gho_*` long-lived OAuth + `tid_*` short-lived session), and Copilot-stealth
header trio all match the verified copilot.vim flow byte-for-byte. Every Phase
017-specific pitfall (P1-3 plaintext, Pitfall 2 client_id, Pitfall 4 grant-
revocation, Pitfall 6 slow_down persistence, Pitfall 7 monotonic deadline,
Pitfall 9 CancelledError propagation, Pitfall 10 safety margin, Pitfall 11
GHE URL, Pitfall 12 stealth headers, Pitfall 13 no oauth_common imports,
Pitfall 14 eager mint) has a regression test that validates it directly.

### Phase 017-specific delta verification

- **Pitfall 2 client_id pinning** — `_CLIENT_ID = "Iv1.b507a08c87ecfe98"` at
  line 143 (legacy OAuth App, plaintext). `Ov23li` substring does not appear
  except in the prohibitive comment at line 136. Test
  `test_constants` (017-02-01) source-greps for both presence of the legacy
  literal and absence of the modern GitHub App family.

- **No client_secret (RFC 8628 public client)** — `_CLIENT_SECRET` does not
  exist as either a module attribute or a string literal. Verified by
  `test_constants` lines 117–119.

- **Two-tier token mapping** — `login()` at lines 675–682 maps:
    - `access  = session.token`     (tid_* short-lived; from
      `CopilotSessionResponse.token`, repr=False).
    - `refresh = oauth_token`       (gho_* long-lived; from poll-endpoint
      success, never rotated).
    - `expires = float(session.expires_at)` — server-issued absolute Unix
      epoch, NOT `now + expires_in` math.
    - `extras["oauth_token"]`  mirrors `cred.refresh` for read-clarity.
    - `extras["editor_version"]` captured for Pitfall 12 forensics.
  Tested in `test_login_full_device_flow` (017-04-05).

- **Refresh re-mints, never calls OAuth refresh endpoint** —
  `GitHubCopilotAuth.refresh()` (lines 692–749) issues a single
  `_mint_session_token` POST to `copilot_internal/v2/token`. The grep gate
  in `test_refresh_remints_session_no_oauth_call` (017-04-06) iterates all
  recorded requests and asserts none target `login/oauth/access_token`. The
  string `login/oauth/access_token` does appear in the source three times,
  but only in the device-code POLL endpoint (line 360) and explanatory
  comments (lines 153, 723–724) — never inside `refresh()`. The phase brief's
  `! grep "login/oauth/access_token"` gate is satisfied for the refresh path
  specifically (refresh has zero references to that path).

- **Monotonic-deadline correctness (Pitfall 7)** — `_PollingState.deadline`
  is computed once at line 373 as `monotonic() + float(expires_in)`.
  All deadline checks (lines 420, 439) call `state.remaining(monotonic())`.
  `time.time` does not appear anywhere in the source (count=0; the
  test-side guard tolerates ≤1).

- **Persistent slow_down increment (Pitfall 6)** — `state.interval` is
  mutated in place at lines 435 and 437, so the +5s bump is cumulative
  across iterations. When the server provides its own interval suggestion,
  it REPLACES `state.interval` (a documented and acceptable interpretation
  of RFC §3.5; the test asserts only the no-server-interval branch).
  `test_poll_slow_down_persists` (017-03-04) covers two consecutive
  slow_downs and verifies third sleep == 5+5+5+3 = 18s.

- **3-second safety margin on every sleep (Pitfall 10)** — line 386:
  `await sleep(state.interval + state.safety_margin)`. `safety_margin`
  defaults to `_POLLING_SAFETY_MARGIN_S = 3.0` and is never decremented.
  `test_poll_safety_margin_3s` (017-03-08) asserts first sleep equals
  `initial_interval + 3.0`.

- **`asyncio.CancelledError` propagation (Pitfall 9)** — there is no
  `try/except` wrapping the `await sleep(...)` or `await client.post(...)`
  awaits. Only `httpx.HTTPError` and `ValidationError` are caught, both of
  which are siblings of `BaseException` rather than `CancelledError`.
  `test_poll_cancelled_via_signal` (017-03-09) injects a
  `CancelledError`-raising sleep and asserts propagation.

- **Pydantic-driven grant-revocation (Pitfall 4 / P1-6)** —
  `CopilotSessionResponse.token: str` is required (no `| None`, no default).
  When GitHub responds 200 with `{}` (the legacy OAuth App's revoked-grant
  signal), `model_validate_json` raises `ValidationError` which
  `_mint_session_token` re-raises as `AuthRefreshError` at line 517.
  Alternate paths (401/403) raise at line 500. Both branches tested
  (`test_mint_grant_revoked_200_null_body` 017-04-02 and
  `test_mint_grant_revoked_401` 017-04-03).

- **GHE enterprise URL handling (Pitfall 11)** — `normalize_domain` strips
  protocol + trailing slash. `login()` derives both `base_domain` and
  `base_api`; `refresh()` rederives `base_api` from
  `cred.extras["enterprise_url"]` (line 710) — the only cross-call
  persistence point. The `extras.get("enterprise_url")` guard at 711 prevents
  KeyError on non-enterprise credentials. (Note: not exercised by any test
  in this phase — `test_login_full_device_flow` and the refresh tests only
  cover the github.com path. Acceptable since the URL-construction logic is
  pure-string and trivially covered by inspection; Phase 022 may add a
  GHE round-trip test.)

- **Copilot-stealth headers** — exactly four keys in `http_headers()`
  (lines 599–606): `authorization`, `user-agent`, `editor-version`,
  `editor-plugin-version`. Values match Phase 017 brief literally.
  `test_http_headers_copilot_stealth` (017-02-06) asserts the set and the
  byte-stable values; `test_mint_session_token` (017-04-01) verifies
  the same triple is sent on the mint POST.

### Cardinal-rule checks (Phase 015/016 baseline)

- **AuthMethod Protocol conformance** — `test_satisfies_authmethod_protocol`
  (017-02-07) runs `isinstance(GitHubCopilotAuth(), AuthMethod)`; passes
  because the class exposes `provider_id` plus the five required methods.
- **`provider_id = "github.copilot"`** — class attribute at line 546,
  used in log facts (lines 686, 717, 745) and in `_main` argparse default
  (line 810). Negative test verifies it is NOT the hyphenated form
  `github-copilot` that opencode uses.
- **chmod 0600 vault writes** — `_main` login path (lines 836–840) routes
  through `state_core.auth.store.save_vault` (Phase 011 atomic-write +
  fchmod 0o600). No bypass.
- **No litellm imports** — verified by `test_no_oauth_common_imports`
  (017-04-10) and source-grep.
- **No `from filelock` / `import filelock` / `AsyncFileLock`** —
  same gate; refresh.py owns the lock.
- **No oauth_common imports** — same gate; explicit comments at lines
  118–119 document the intentional absence.
- **OAuth NEVER through litellm** — only `httpx.AsyncClient` is used for
  all three endpoints (device-code, poll, mint).
- **Determinism** — the only wall-clock dependence in the source is the
  optional `time.monotonic` injection in `_poll_for_token`. `is_expired`
  takes `now: float` from caller (line 569). `time.time()` is never
  called. Logs use server-issued `expires_at` directly, no `time.time() +`
  math.

## Critical Issues

None.

## Warnings

### WR-01: `test_login_full_device_flow` real-sleeps 8 seconds despite intent to fast-sleep

- **File:** `tests/auth/providers/test_github_copilot.py:840-844`
- **Issue:** The test patches
  `state_core.auth.providers.github_copilot.asyncio.sleep` with `_fast_sleep`,
  intending to short-circuit polling. However, `_poll_for_token` captures
  its `sleep` parameter as a default argument:
  `sleep: Callable[[float], Awaitable[None]] = asyncio.sleep`
  (source line 333). Default arguments are evaluated **once at def-time**,
  binding the original `asyncio.sleep`. Subsequent monkeypatching of
  `github_copilot.asyncio.sleep` mutates the module attribute but does NOT
  rebind already-captured default args. `login()` calls
  `await _poll_for_token(...)` without explicitly passing `sleep=`, so the
  captured original `asyncio.sleep` runs, and the test will actually sleep
  ~8 seconds (initial_interval=5 + safety_margin=3) on the first poll
  before returning. Side effects: (a) test is slow; (b) under
  pytest-asyncio strict-mode timeouts the test could flake; (c) the
  intended invariant (test runs without real sleep) is violated.
- **Fix:** Patch the source `asyncio.sleep` *call site*, not the default.
  Either:
  ```python
  monkeypatch.setattr("asyncio.sleep", _fast_sleep)
  ```
  (which patches the module everyone shares — works because `_poll_for_token`
  evaluated `asyncio.sleep` at def-time and the captured callable is the
  *same* function object that `asyncio.sleep` rebinds — actually this also
  fails for the same reason). The robust fix is to refactor the test to
  inject `sleep` explicitly via the `sleep=` kwarg, or to expose a
  `_DEFAULT_SLEEP` module attribute that `_poll_for_token` looks up at
  call-time. A minimum-impact alternative is to convert the default to
  late-binding inside the function:
  ```python
  async def _poll_for_token(..., sleep=None, monotonic=None):
      sleep = sleep or asyncio.sleep
      monotonic = monotonic or time.monotonic
  ```
  Then the test's `monkeypatch.setattr("...github_copilot.asyncio.sleep", ...)`
  works because the lookup happens at call-time.

  Severity is "warning" (not "info") because: (1) determinism is a Phase
  017 cardinal rule — slow tests violate the spirit; (2) CI runtime budget
  matters; (3) this is the *only* full-flow login test, so its silent
  slowness masks real future bugs in the polling sleep path. No
  correctness/security impact, hence not "critical".

## Info

### IN-01: `test_poll_slow_down_increases_interval` docstring math contradicts assertion

- **File:** `tests/auth/providers/test_github_copilot.py:428-431`
- **Issue:** The docstring narrative says
  `"Assert second sleep is (initial + 5) + safety_margin = 8 + 3 = 11 seconds"`
  — but the actual assertion at line 432 is `sleep_calls[1] == 13.0`
  (which is the *correct* value: 5 + 5 + 3 = 13). The docstring's "8 + 3 = 11"
  arithmetic is wrong. The implementation matches the assertion, not the
  docstring. Pure documentation defect; reader confusion only.
- **Fix:** Replace `"= 8 + 3 = 11"` with `"= 5 + 5 + 3 = 13"` in the
  docstring at line 431.

### IN-02: `_main` login leaks first 10 chars of OAuth token to stdout when `account_id` is None

- **File:** `src/state_core/auth/providers/github_copilot.py:845-849`
- **Issue:** The fallback at line 847 is
  `cred.extras.get("oauth_token", "<unknown>")[:10]`. For a real
  Copilot login, `account_id` is `None` (Phase 022 will populate it via
  `GET /user`), so the fallback fires and prints `"Logged in as gho_FIXTUR"`
  — i.e., the prefix-plus-7-chars of the live `gho_*` OAuth token to
  stdout. While the OAuth token is itself stored chmod-0600 in the vault,
  printing 10 chars to stdout (which may be redirected to log files,
  pipes, or terminal scrollback) is a partial-credential leak.
  GitHub's `gho_*` tokens use base62 entropy after the prefix; the first
  4 chars `gho_` are non-secret, but the next 6 narrow the keyspace
  measurably for a network-MITM-attempting-to-replay.
- **Fix:** Replace the slice with `cred.account_id or "<unknown>"`. The
  user gets a less informative success line until Phase 022 polishes
  `account_id`, but no token bytes leak. If a label IS desired before
  Phase 022, slice only the non-secret prefix (`[:4]` to print just
  `gho_`).

### IN-03: `print = print` re-bind sits between stdlib and third-party imports (inherited from Phase 015/016 IN-02)

- **File:** `src/state_core/auth/providers/github_copilot.py:100`
- **Issue:** Same isort-PEP-8 nit flagged in Phase 016 IN-02: the
  `print = print` testability re-bind is sandwiched between stdlib imports
  (lines 92–95) and third-party imports (lines 102–104). Strict isort/ruff
  configs would flag this. Inherited convention; sibling providers carry
  the same layout. No behavior or security impact.
- **Fix:** Move to immediately after the final import (e.g., after line 116).
  Defer to project-wide convention — if Phase 015 / 016 / Phase 014
  (`anthropic.py`) all use the same layout, leave alone for consistency.

### IN-04: `test_main_argparse_login` runs the persistence path twice without isolating the vault

- **File:** `tests/auth/providers/test_github_copilot.py:990-1000`
- **Issue:** The test invokes `_main()` twice (once with `["login"]`, once
  with `["login", "--enterprise-url", "company.ghe.com"]`). Both share the
  same `STATE_AUTH_JSON` env var (line 971). The second invocation appends
  a *second* `cred` to `vault.providers["github.copilot"]`, so after the
  test finishes the temp vault contains TWO identical canned credentials.
  This is semantically permitted (P1-7 array invariant says buckets are
  lists), but the second `_main()` call's success doesn't actually verify
  the `--enterprise-url` argparse path interacted with anything — both
  invocations call the same patched `_fake_login` which ignores the
  `enterprise_url` kwarg. The test only verifies argparse *accepts* the
  flag, not that it *threads through* to the login call.
- **Fix:** Either (a) capture `enterprise_url` in a closure inside
  `_fake_login` and assert it equals `"company.ghe.com"` on the second
  invocation, or (b) split the second invocation into a separate test
  with its own `tmp_path`. Optional polish; the current test does what it
  says on the tin (argparse accepts the flag).

## Notes / Non-issues

- The `git diff --name-only` review-scope already excluded planning
  artifacts — only the three source/test files were considered.
- Pydantic's `extra="ignore"` on all three response models gives forward
  compatibility for fields GitHub may add (e.g., `verification_uri_complete`
  is captured but not yet relied upon — Phase 022 may use it for
  one-click flows).
- The poll endpoint's special-cased status check at lines 395–397
  (`>= 500 or (>= 400 and != 400)`) correctly tolerates GitHub's RFC 8628
  deviation of returning 200 for `slow_down`/`authorization_pending` while
  still raising on truly unexpected 4xx (401, 403, 422). Spec-compliant
  400s carrying error-coded JSON bodies are parsed and matched against
  `parsed.error`.
- `_PollingState.remaining()` clamps to `≥ 0.0` rather than allowing
  negative values, so the deadline check `state.remaining(monotonic()) <= 0.0`
  is the correct comparator (deadline elapsed iff returned 0.0).
- `_request_device_code` uses `httpx.Timeout(10.0, connect=5.0)` —
  consistent with Phase 014/015/016 sibling providers. Per-call
  AsyncClient (no module singleton). `follow_redirects=False` defends
  against DoS-by-redirect.
- The success-branch ordering at line 407 (return immediately, no
  deadline check) is correct: a token that arrives ~1ms after deadline
  expiry should still be honored. UX-positive.
- The `_main` `except Exception` at line 841 (vault persistence) is
  fine — CLI top-level, user gets a clear error message + exit 1.
  Same pattern as Phase 016.
- `is_token` accepts the bare prefixes `tid_` and `ghr_` (e.g.,
  `is_token("tid_")` returns True). This matches the test fixture
  expectation and is harmless because `is_token` is a soft routing hint,
  not a security boundary.
- The `extras["oauth_token"]` mirror invariant (`cred.refresh ==
  cred.extras["oauth_token"]`) is established at login (line 663) and
  preserved through `refresh()` because the latter uses
  `dict(cred.extras)` and never overwrites the `oauth_token` key. If a
  corrupted vault arrives with the two diverging, the provider does not
  defensively re-sync — that's acceptable for v1; Phase 022 captured-
  header regression may add a dump-side invariant check.
- All five constants asserted by `test_constants` match the source
  byte-for-byte. No obfuscation. P1-3 satisfied.
- `_main` exit codes (0 / 1 / 2 / 130) match the Phase 014/015/016 sibling
  contract.
- The `extras["editor_version"]` capture at login (line 664) is the
  Phase 022 forensics seed — when GitHub upgrades the Copilot client
  allowlist and the captured-header regression starts failing, the stored
  `editor_version` lets us identify which credentials predate the drift
  without re-login.

---

_Reviewed: 2026-04-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
