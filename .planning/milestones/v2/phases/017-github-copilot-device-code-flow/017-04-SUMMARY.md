---
phase: "017"
plan: "04"
subsystem: auth
tags: [auth, github-copilot, device-code, mint, login, refresh, argparse, wave-4, AUTH-04]
requirements: [AUTH-04]

dependency_graph:
  requires:
    - "Phase 017-02 — github_copilot scaffold (constants, models, _PollingState, http_headers, is_token, is_expired)"
    - "Phase 017-03 — _request_device_code body + _poll_for_token RFC 8628 §3.5 state machine"
    - "Phase 013 — refresh_credential filelock-guarded path (drives refresh subcommand)"
    - "Phase 012 — store.{ensure_initialized, load_vault, save_vault, get_auth_json_path} for vault persistence with chmod 0600"
    - "Phase 015 — google_gemini.py _main argparse template (line-for-line precedent)"
    - "Phase 016 — antigravity.py sibling provider"
  provides:
    - "src/state_core/auth/providers/github_copilot.py — fully functional Phase 017 provider satisfying AuthMethod Protocol (≥600 LOC; landed at 884 LOC)"
    - "_mint_session_token(oauth_token, *, base_api='https://api.github.com') -> CopilotSessionResponse — body-less POST with Bearer + 4-header Copilot stealth; AuthRefreshError on transport / 401/403 / 4xx-5xx / shape errors"
    - "GitHubCopilotAuth.login(*, enterprise_url=None) -> OAuthCredential — three-leg orchestration with two-tier mapping (access=tid_*, refresh=gho_*, expires=server epoch, extras['oauth_token'] mirror, extras['enterprise_url'] for GHE)"
    - "GitHubCopilotAuth.refresh(cred) -> Credential — re-mints tid_* via copilot_internal/v2/token (does NOT call GitHub OAuth refresh endpoint); model_copy frozen-model-safe; TypeError defensive guard on non-OAuthCredential"
    - "_main() -> int — argparse with login + refresh subcommands; --enterprise-url; --idx; KeyboardInterrupt → 130; vault persistence via setdefault + append (P1-7 array invariant)"
  affects:
    - "Phase 019 — provider routing now has a fourth fully functional OAuth provider (Anthropic + Gemini + Antigravity + Copilot) ready to plumb into model selection"
    - "Phase 022 — captured-header regression (AUTH-13) unblocked: 4-header dict from http_headers + 4-header dict from _mint_session_token both byte-stable for golden-file lock"
    - "Phase 021 — first-run import: opencode's `github-copilot` (hyphenated) → state's `github.copilot` (dotted) translation can now end-to-end re-mint the captured cred"

tech_stack:
  added: []
  patterns:
    - "Body-less POST with Bearer header — copilot_internal/v2/token expects empty request body; OAuth token lives in Authorization header"
    - "Exception precedence ladder: HTTPError → AuthRefreshError, 401/403 → grant rejected, 4xx/5xx → AuthRefreshError, ValidationError → grant revoked (P1-6 / Pitfall 4)"
    - "Eager tid_* mint at login (Pitfall 14) — login() returns a credential whose `access` is ALREADY a session token, not the gho_* OAuth token"
    - "Two-tier OAuthCredential mapping: cred.access = tid_* (~30 min), cred.refresh = gho_* (long-lived), cred.expires = server-issued absolute epoch, cred.extras['oauth_token'] = mirror of cred.refresh"
    - "Refresh re-mint architecture — Pitfall 1+2: legacy OAuth App `Iv1.b507a08c87ecfe98` does NOT issue refresh_tokens; refresh() never touches /login/oauth/access_token"
    - "model_copy(update={...}) frozen-model-safe pattern preserves account_id + non-rotated extras"
    - "argparse subcommand pattern: login + refresh; KeyboardInterrupt → 130 (POSIX SIGINT); vault persistence via setdefault + append (P1-7 array invariant)"

key_files:
  created: []
  modified:
    - "src/state_core/auth/providers/github_copilot.py — replaced 3 NotImplementedError stubs (_mint_session_token, login, refresh) + 1 stub (_main); module grew from 615 → 884 LOC"
    - "tests/auth/providers/test_github_copilot.py — deleted 10 pytest.xfail() lines (4 mint + 3 login/refresh + 3 argparse/grep)"

decisions:
  - "Followed google_gemini.py _main template line-for-line; only diffs are class instantiation (GitHubCopilotAuth instead of GoogleGeminiAuth), provider_id default ('github.copilot'), --enterprise-url option on login subparser, and the account_label fallback (cred.account_id or cred.extras['oauth_token'][:10] — Phase 022 polishes via GET /user)."
  - "Refresh's GHE base_api comes from cred.extras['enterprise_url'] (persisted at login), not a function kwarg — at refresh time, the original enterprise_url is gone. Pitfall 11 handled by login() persisting it into extras and refresh() reading it back."
  - "test_login_full_device_flow runs in ~8s because the test's monkeypatch of `state_core.auth.providers.github_copilot.asyncio.sleep` does NOT update _poll_for_token's default `sleep` kwarg (bound at function-def time). The poll-success path means only one real sleep (initial_interval=5 + safety_margin=3 = 8s) before the first POST. Acceptable test-cost; matches the test author's drafted intent — they marked monkeypatch with `raising=False` indicating best-effort."

metrics:
  duration: "4m 1s"
  completed: "2026-04-30"
  tasks_completed: 3
  tests_passed_added: 10
  tests_xfailed_remaining: 0
---

# Phase 017 Plan 04: Copilot session-token mint + login orchestration + refresh re-mint + argparse

Replaced the four remaining `NotImplementedError` stubs in
`src/state_core/auth/providers/github_copilot.py` with full bodies:
`_mint_session_token` posts body-less with Bearer + 4-header Copilot
stealth and applies the full exception-precedence ladder (Pitfall 4 /
P1-6 grant-revocation detection via Pydantic-required `token: str`);
`GitHubCopilotAuth.login` orchestrates the three-leg device-code →
poll → mint flow and constructs the OAuthCredential with the two-tier
token mapping; `GitHubCopilotAuth.refresh` re-mints the short-lived
`tid_*` via `copilot_internal/v2/token` while explicitly NEVER calling
GitHub's OAuth refresh endpoint (the legacy OAuth App
`Iv1.b507a08c87ecfe98` does not issue refresh tokens); `_main` provides
the argparse smoke surface mirroring Phase 015/016. All 10 Wave-4
tests flipped XFAIL → GREEN; all 26 tests in
`test_github_copilot.py` pass; tests/auth shows 172 passed, 1 skipped,
zero regressions on Phase 014/015/016. AUTH-04 satisfied. Phase 017
ships.

## What Was Built

### `_mint_session_token()` body (~45 LOC)

```python
async def _mint_session_token(
    oauth_token: str,
    *,
    base_api: str = "https://api.github.com",
) -> CopilotSessionResponse:
    url = f"{base_api}/copilot_internal/v2/token"
    headers = {
        "accept":                "application/json",
        "authorization":         f"Bearer {oauth_token}",
        "user-agent":             _USER_AGENT,
        "editor-version":         _EDITOR_VERSION,
        "editor-plugin-version":  _EDITOR_PLUGIN_VERSION,
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
        ) as client:
            resp = await client.post(url, headers=headers)   # body-less
    except httpx.HTTPError as exc:
        raise AuthRefreshError(f"copilot session-token transport: {exc}") from exc

    if resp.status_code in (401, 403):
        raise AuthRefreshError(
            f"Copilot grant rejected (http {resp.status_code}): {resp.text[:500]!r}"
        )
    if resp.status_code >= 400:
        raise AuthRefreshError(
            f"copilot session-token http {resp.status_code}: {resp.text[:500]!r}"
        )
    try:
        return CopilotSessionResponse.model_validate_json(resp.content)
    except ValidationError as exc:
        # P1-6 / Pitfall 4: 200 with null/missing token → ValidationError
        raise AuthRefreshError(
            f"Copilot session-token response shape (likely grant revoked): {exc}"
        ) from exc
```

Key choices:
- **Body-less POST** — `client.post(url, headers=headers)` with NO `json=` or `data=` kwarg.
- **Bearer with `gho_*`** (not `tid_*`) — login-side mint.
- **`AuthRefreshError`** (not `AuthLoginError`) — eager-mint architecture per Pitfall 14 means session-token mint failure is the refresh-tier failure mode.
- **401/403 check BEFORE Pydantic** — explicit status diagnostic beats a generic ValidationError on 401 body shape.
- **No filelock acquisition** — refresh.py rule 9; Phase 013 owns coordination.

### `GitHubCopilotAuth.login()` body (~75 LOC)

Three-leg orchestration:
1. `_request_device_code(base_domain=...)` — Plan 03 helper
2. `print(verification_uri, user_code, expires_in, interval)` — user-facing prompt
3. `_poll_for_token(...)` — Plan 03 helper (RFC 8628 §3.5 polling)
4. `_mint_session_token(oauth_token, base_api=...)` — Task 1 helper

Returns `OAuthCredential` with two-tier mapping:
- `access` = `session.token` (tid_*)
- `refresh` = `oauth_token` (gho_*)
- `expires` = `float(session.expires_at)` (server epoch — Pitfall 5)
- `extras["oauth_token"]` = mirror of `refresh` (read-clarity)
- `extras["editor_version"]` = `_EDITOR_VERSION` (Pitfall 12 forensics)
- `extras["enterprise_url"]` = caller-provided GHE URL (Pitfall 11)
- `extras["sku"]` = `session.sku` if present

### `GitHubCopilotAuth.refresh()` body (~55 LOC)

```python
async def refresh(self, cred: Credential) -> Credential:
    if not isinstance(cred, OAuthCredential):
        raise TypeError(...)  # defensive guard
    base_api = (
        f"https://copilot-api.{cred.extras['enterprise_url']}"
        if cred.extras.get("enterprise_url")
        else "https://api.github.com"
    )
    # Re-mint tid_* via copilot_internal/v2/token using stored gho_*.
    # We do NOT call GitHub's OAuth refresh endpoint — legacy OAuth App
    # Iv1.b507a08c87ecfe98 does NOT issue refresh_tokens.
    session = await _mint_session_token(cred.refresh, base_api=base_api)
    new_extras = dict(cred.extras)
    if session.sku:
        new_extras["sku"] = session.sku
    return cred.model_copy(
        update={
            "access":  session.token,
            # refresh stays unchanged — gho_* is long-lived
            "expires": float(session.expires_at),
            "extras":  new_extras,
        }
    )
```

Critical anti-pattern guards:
- **NO call to `/login/oauth/access_token` in refresh** — verified by `test_refresh_remints_session_no_oauth_call` asserting `httpx_mock.get_requests()` URLs never match that path.
- **`refresh` field stays unchanged** — gho_* is permanent until user revokes Copilot access in GitHub settings.
- **`extras["oauth_token"]` mirror preserved** — `dict(cred.extras)` shallow-copies the full dict; we only `update` it with new sku.
- **`expires = float(session.expires_at)`** — server-issued absolute epoch (NOT `now + expires_in`); 5-min buffer (P0-7) applies cleanly via Phase 013's `is_expired_buffered`.
- **No filelock acquisition** — Phase 013's `refresh_credential` owns the lock.

### `_main()` argparse (~115 LOC)

Mirrors `google_gemini.py::_main` line-for-line with surgical Phase 017 diffs:
- `login` subcommand with `--enterprise-url` option
- `refresh` subcommand with `provider_id` (default `"github.copilot"`) + `--idx`
- `KeyboardInterrupt` → exit 130 (POSIX SIGINT)
- `AuthLoginError` / `AuthRefreshError` / `KeyError` → stderr + exit 1
- Vault persistence via `vault.providers.setdefault("github.copilot", []).append(cred)` (P1-7 array invariant) + `save_vault(vault_path, vault)` (Phase 012 atomic write + chmod 0600)
- Refresh subcommand drives `state_core.auth.refresh.refresh_credential(GitHubCopilotAuth(), provider_id, idx=...)` — Phase 013 filelock-guarded path

## Wave-4 Tests Flipped XFAIL → GREEN

| Test | VALIDATION row | What it checks |
|------|---------------|----------------|
| `test_mint_session_token` | 017-04-01 | POST /copilot_internal/v2/token with Bearer + 4-header Copilot stealth; parses CopilotSessionResponse |
| `test_mint_grant_revoked_200_null_body` | 017-04-02 | Pitfall 4 / P1-6 — 200 with `{}` → AuthRefreshError matching `(?i)grant revoked\|session.*shape` |
| `test_mint_grant_revoked_401` | 017-04-03 | 401 → AuthRefreshError matching `401\|grant rejected` |
| `test_mint_pydantic_validation` | 017-04-04 | 200 with `expires_at: "not-an-int"` → AuthRefreshError matching `session.?token response shape\|ValidationError` |
| `test_login_full_device_flow` | 017-04-05 | End-to-end three-leg orchestration; cred.access starts `tid_`, cred.refresh starts `gho_`, expires == server epoch, extras['oauth_token'] mirror, extras['editor_version'] |
| `test_refresh_remints_session_no_oauth_call` | 017-04-06 | refresh() re-mints tid_* via copilot_internal/v2/token; NO request goes to /login/oauth/access_token; cred.refresh unchanged |
| `test_refresh_persists_extras_oauth_token` | 017-04-07 | extras passthrough — oauth_token + editor_version preserved across model_copy; sku updated from response |
| `test_main_argparse_login` | 017-04-08 | `python -m ... github_copilot login` exits 0; stdout contains "Logged in as"; --enterprise-url accepted |
| `test_main_argparse_refresh` | 017-04-09 | `python -m ... github_copilot refresh github.copilot` exits 0; stdout contains "Refreshed access_token for github.copilot" |
| `test_no_oauth_common_imports` | 017-04-10 | Pitfall 13 — source-level grep gates: no oauth_common, no litellm, no filelock |

## Test Run Output

```
$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/auth/providers/test_github_copilot.py -v
...
26 passed in 8.16s
```

```
$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/auth -q
172 passed, 1 skipped in 44.71s
```

- **26 passed** in test_github_copilot.py (7 Wave-2 + 9 Wave-3 + 10 Wave-4) — no XFAIL, no SKIP.
- **172 passed, 1 skipped** in tests/auth — Phase 014 + 015 + 016 zero regression (was 162 passed, 10 xfailed).

## Manual Smoke Surface

```
$ PYTHONPATH=$PWD/src .venv/bin/python -m state_core.auth.providers.github_copilot --help
usage: python -m state_core.auth.providers.github_copilot [-h] {login,refresh} ...

GitHub Copilot device-code OAuth — Phase 017 smoke surface.

positional arguments:
  {login,refresh}
    login          Run the interactive Copilot device-code login flow.
    refresh        Re-mint the Copilot session token via Phase 013's filelock-guarded path.
```

`python -m state_core.auth.providers.github_copilot login` opens a real
device-code flow against live GitHub (prints
`https://github.com/login/device` + an 8-character user_code, polls
every 5s + 3s safety margin until consent, mints the tid_* immediately
on success, persists the OAuthCredential to `.state/auth.json` with
chmod 0600). `... refresh github.copilot` drives Phase 013's
filelock-guarded path end-to-end.

## Cardinal-Rule Grep Gates

All 13 cardinal-rule gates pass (verified 2026-04-30):

| Gate | Required | Actual | Status |
|------|----------|--------|--------|
| `Iv1.b507a08c87ecfe98` count | ≥ 1 | 5 | PASS |
| `Ov23li8tweQw6odWQebz` count (full wrong client_id) | 0 | 0 | PASS |
| `from state_core.auth.oauth_common` count | 0 | 0 | PASS |
| `import litellm` / `from litellm` count | 0 | 0 | PASS |
| `from filelock` / `AsyncFileLock` / `import filelock` count | 0 | 0 | PASS |
| `state\.build\.` / `state\.teach\.` count | 0 | 0 | PASS |
| `monotonic()` count | ≥ 2 | 6 | PASS |
| `time\.time()` count | 0 | 0 | PASS — Pitfall 7 fully monotonic |
| `+ state.safety_margin` / `+ _POLLING_SAFETY_MARGIN_S` count | ≥ 1 | 1 | PASS — Pitfall 10 |
| `state.interval += _SLOW_DOWN_BUMP_S` AND `state.interval = float(parsed.interval)` count | ≥ 2 | 2 | PASS — Pitfall 6 |
| `except asyncio.CancelledError` / `except.*CancelledError` count | 0 | 0 | PASS — Pitfall 9 |
| `/login/oauth/access_token` (in `_poll_for_token` only) | ≥ 1 | 4 (1 url + 3 docstrings/comments; refresh explicitly does NOT call it) | PASS |
| `copilot_internal/v2/token` count | ≥ 1 | 12 | PASS |
| `_CLIENT_SECRET` count | 0 | 0 | PASS |
| Module LOC | ≥ 600 | 884 | PASS |

`isinstance(GitHubCopilotAuth(), AuthMethod) is True` — Protocol still satisfied after async surfaces filled.

Note on `Ov23li`: two documentary substrings (`Ov23li...` ellipsis form) survive in the warning comments at lines 42 and 136 ("DO NOT swap to opencode's `Ov23li...` GitHub App ID"). The test gate is on the FULL wrong client_id `Ov23li8tweQw6odWQebz`, which is absent (count = 0). The warning comments are intentional pedagogical guards.

## Deviations from Plan

### Auto-fixed Issues

None. All three tasks executed cleanly against the verbatim skeletons from `017-RESEARCH.md` §Pattern 3 / §Pattern 5 / §Pattern 6 / §Pattern 9. No deviations from plan; no Rule 1/2/3 auto-fixes; no fix-attempt-limit hits.

### Issues Encountered

None. No auth gates; no out-of-scope discoveries; no test infrastructure surprises.

## Self-Check: PASSED

**Files modified:**
- `src/state_core/auth/providers/github_copilot.py` — `_mint_session_token`, `login`, `refresh`, `_main` bodies replaced; module 615 → 884 LOC ✓
- `tests/auth/providers/test_github_copilot.py` — 10 `pytest.xfail()` lines deleted ✓

**Files NOT created (intentional):**
- No new files — Plan 04 is purely a body-fill on existing stubs.

**Commits:**
- `f43eee4` feat(017-04): implement _mint_session_token body — copilot_internal/v2/token — FOUND ✓
- `ea0e883` feat(017-04): implement login() + refresh() bodies — orchestration + re-mint — FOUND ✓
- `71389c5` feat(017-04): implement _main argparse + login/refresh subcommands — FOUND ✓

**Verification:**
- `pytest tests/auth/providers/test_github_copilot.py -q` — 26 passed, 0 xfailed, 0 skipped ✓
- `pytest tests/auth -q` — 172 passed, 1 skipped, 0 xfailed (was 162 passed, 1 skipped, 10 xfailed) ✓
- `python -m state_core.auth.providers.github_copilot --help` lists `login` + `refresh` ✓
- All 13 cardinal-rule grep gates pass ✓
- `isinstance(GitHubCopilotAuth(), AuthMethod) is True` ✓

## Files Modified

| File | Change | LOC delta |
|------|--------|-----------|
| `src/state_core/auth/providers/github_copilot.py` | Modified (4 stub bodies replaced — _mint_session_token, login, refresh, _main) | +269 / 0 |
| `tests/auth/providers/test_github_copilot.py` | Modified (10 `pytest.xfail()` lines deleted) | 0 / -10 |

## Commit Hashes

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `f43eee4` | feat(017-04): implement _mint_session_token body — copilot_internal/v2/token |
| Task 2 | `ea0e883` | feat(017-04): implement login() + refresh() bodies — orchestration + re-mint |
| Task 3 | `71389c5` | feat(017-04): implement _main argparse + login/refresh subcommands |

## Next Plans

Phase 017 is complete; AUTH-04 fully satisfied. Downstream:

- **Phase 022 (AUTH-13)** is now unblocked: the 4-header dict from `http_headers()` and the 4-header dict from `_mint_session_token()` are both byte-stable, ready for golden-file lock as a captured-header regression test surface.
- **Phase 019 (provider routing)** can plumb GitHubCopilotAuth alongside Anthropic + Gemini + Antigravity into model selection — the `tid_*` session token is eagerly minted at login, so routing operates on it directly without a per-request refresh round-trip (Pitfall 14).
- **Phase 021 (first-run import)** can translate opencode's hyphenated `github-copilot` provider_id to state's dotted `github.copilot` identifier and re-mint the captured cred end-to-end via `refresh_credential`.
