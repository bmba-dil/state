---
phase: "017"
plan: "02"
subsystem: auth
tags: [auth, github-copilot, device-code, rfc-8628, scaffold, wave-2, AUTH-04]
requirements: [AUTH-04]

dependency_graph:
  requires:
    - "Phase 011 — OAuthCredential / AuthMethod Protocol / Credential discriminated union"
    - "Phase 013 — is_expired_buffered (5-min buffer per AUTH-09)"
    - "Phase 015 — state_core.auth.errors (AuthError / AuthLoginError / AuthRefreshError)"
    - "Phase 017-01 — RED-stub test file (26 cases) + 3 conftest fixtures"
  provides:
    - "src/state_core/auth/providers/github_copilot.py — module-level constants, 3 Pydantic models, _PollingState dataclass, normalize_domain helper, GitHubCopilotAuth class with sync methods FULL + async stubs"
    - "Verified Wave-2 GREEN surface for Plan 03 (poll loop) and Plan 04 (mint/login/refresh/argparse) to extend"
  affects:
    - "Plan 017-03 — implements _request_device_code + _poll_for_token bodies (Wave 3 — 9 tests)"
    - "Plan 017-04 — implements _mint_session_token + login + refresh + _main bodies (Wave 4 — 10 tests)"

tech_stack:
  added: []
  patterns:
    - "Mirrored Phase 015/016 module structure section-for-section: module docstring → imports → identity constants → URL/header constants → polling tuning constants → Pydantic models → dataclass → helpers → AuthMethod class → __main__ block"
    - "Async-stub pattern: signatures complete with Awaitable/Callable injection points, body raises NotImplementedError citing future plan number"
    - "Two-tier token mapping documented in module docstring + class docstring: cred.refresh=gho_*, cred.access=tid_*, cred.expires=server epoch, cred.extras['oauth_token']=mirror"

key_files:
  created:
    - "src/state_core/auth/providers/github_copilot.py — 477 LOC"
  modified:
    - "tests/auth/providers/test_github_copilot.py — removed 7 pytest.xfail() lines (Wave 2 only)"

decisions:
  - "Inlined RFC 8628 endpoints as helper-function defaults rather than module-level constants. Reason: base_domain / base_api vary by enterprise URL (Pitfall 11); a module-level _DEVICE_CODE_URL would force every call site to format-string-substitute the domain anyway. Helpers receive base_domain / base_api kwargs and inline-format the URL — matches opencode's TS pattern exactly. Documented as a comment block in the URL endpoints section."
  - "Rephrased multiple cardinal-rule comments to avoid the literal substrings 'Ov23li8tweQw6odWQebz', '_CLIENT_SECRET', and 'from filelock' that test_constants and test_no_oauth_common_imports assert as forbidden. Used 'Ov23li... family', 'client-secret constant', and 'filelock import' (with hyphenation/space) instead. The semantic intent is preserved; the substring scan succeeds."

metrics:
  duration: "5m 21s"
  completed: "2026-04-30"
  tasks_completed: 2
  tests_passed_added: 7
  tests_xfailed_remaining: 19
---

# Phase 017 Plan 02: GitHubCopilotAuth scaffold — Wave-2 sync surface GREEN

Created `src/state_core/auth/providers/github_copilot.py` (477 LOC) with the constants block, three Pydantic response models, `_PollingState` dataclass, `normalize_domain` helper, async-helper stubs (Plans 03/04), and the `GitHubCopilotAuth` class with FULL sync method implementations and async-method NotImplementedError stubs. Flipped 7 Wave-2 tests in `tests/auth/providers/test_github_copilot.py` from XFAIL → GREEN by deleting their `pytest.xfail()` lines. Phase 014/015/016 tests show no regression.

## What Was Built

### `src/state_core/auth/providers/github_copilot.py` (NEW, 477 LOC)

**Module docstring** — ~80 lines covering:
- Phase identification (M-A2 / AUTH-04 / P1-5 + P1-6 owner)
- Two-tier token architecture (cred.refresh = gho_*, cred.access = tid_*, cred.expires = server epoch, cred.extras["oauth_token"] = mirror)
- Module layout listing
- 10 cardinal rules (Pitfall 2 client_id, no client-secret constant, monotonic deadline, slow_down persistence, 3s safety margin, eager tid_* mint, 5-min buffer, no oauth_common, no litellm, no own filelock)

**Imports** — stdlib (`asyncio`, `time`, `dataclasses.dataclass`, `typing`), httpx, structlog, pydantic, and a tightly-scoped re-export from `state_core.auth.{base, errors, refresh}`. Module-level `print = print` re-bind for test monkeypatching (mirrors anthropic.py / google_gemini.py / antigravity.py).

**Identity constants** — pinned from RESEARCH §Code Examples §1:

| Constant | Value | Source |
|---------|-------|--------|
| `_CLIENT_ID` | `"Iv1.b507a08c87ecfe98"` | Legacy OAuth App; copilot.vim, B00TK1D/copilot-api, litellm, hermes-agent #16551, cherry-studio #11905, opencode #20759 cross-verified |
| `_SCOPE` | `"read:user"` | RFC 8628 device-code scope |
| `_USER_AGENT` | `"GithubCopilot/1.155.0"` | Copilot-stealth UA (copilot.vim 1.16.0 capture) |
| `_EDITOR_VERSION` | `"Neovim/0.6.1"` | Copilot-stealth Editor-Version |
| `_EDITOR_PLUGIN_VERSION` | `"copilot.vim/1.16.0"` | Copilot-stealth Editor-Plugin-Version |
| `_POLLING_SAFETY_MARGIN_S` | `3.0` | Pitfall 10 — opencode OAUTH_POLLING_SAFETY_MARGIN_MS=3000 mirror |
| `_SLOW_DOWN_BUMP_S` | `5.0` | RFC 8628 §3.5 minimum slow_down increment (Pitfall 6) |

**No `_CLIENT_SECRET`** — device-code (RFC 8628) is a public OAuth client. The user-consent step at `verification_uri` IS the security boundary; client-secret confidentiality is not part of the threat model. Comment block above the `_CLIENT_ID` line cites P1-3 (no obfuscation) + Pitfall 2 (Iv1 vs Ov23li GitHub App distinction).

**URL endpoints** — inlined into helper-function defaults rather than module-level constants. RFC 8628 endpoints documented in a comment block:
- Device-code request: `POST {base_domain}/login/device/code`
- Token polling: `POST {base_domain}/login/oauth/access_token`
- Session-token mint: `POST {base_api}/copilot_internal/v2/token`

**Pydantic response models** — all use `ConfigDict(extra="ignore")` for forward-compat:

| Model | Required fields | Optional fields | Secret-bearing (repr=False) |
|-------|----------------|----------------|-----------------------------|
| `DeviceCodeResponse` | device_code, user_code, verification_uri, expires_in, interval | verification_uri_complete | device_code |
| `DeviceTokenResponse` | (none — discriminated by access_token vs error) | access_token, token_type, scope, error, error_description, interval | access_token |
| `CopilotSessionResponse` | token, expires_at | refresh_in, sku, chat_enabled | token |

**`CopilotSessionResponse.token` is REQUIRED** — Pydantic ValidationError fires on missing/null. This IS the grant-revocation detector (Pitfall 4 / P1-6): the legacy OAuth App keeps issuing 200s with empty bodies for revoked grants rather than 401s, so Pydantic's required-field check is the tripwire.

**`_PollingState` dataclass:**
```python
@dataclass
class _PollingState:
    interval: float                # mutated on slow_down (Pitfall 6 persistence)
    deadline: float                # time.monotonic() + expires_in (Pitfall 7)
    safety_margin: float = _POLLING_SAFETY_MARGIN_S
    def remaining(self, now_mono: float) -> float:
        return max(0.0, self.deadline - now_mono)
```

**`normalize_domain` helper** — strips protocol + trailing slash for GHE URL handling (Pitfall 11). Mirrors opencode's `copilot.ts:16` pattern.

**Async helper stubs (Plan 03/04):**
- `_request_device_code(*, base_domain="github.com")` — Plan 03 implements
- `_poll_for_token(device_code, initial_interval, expires_in, *, base_domain="github.com", monotonic=time.monotonic, sleep=asyncio.sleep)` — Plan 03 implements; injectable `monotonic` and `sleep` are explicit signatures so Plan 03 unit tests can drive deterministic timing without monkeypatching.
- `_mint_session_token(oauth_token, *, base_api="https://api.github.com")` — Plan 04 implements

**`GitHubCopilotAuth` class — sync methods FULL:**

```python
class GitHubCopilotAuth:
    provider_id: str = "github.copilot"

    def is_token(self, value: str) -> bool:
        return any(value.startswith(p) for p in ("gho_", "ghu_", "tid_", "ghr_"))

    def is_expired(self, cred: Credential, now: float) -> bool:
        return is_expired_buffered(cred, now)   # delegates to Phase 013 / AUTH-09

    def http_headers(self, cred: Credential) -> dict[str, str]:
        if not isinstance(cred, OAuthCredential):
            return {}
        return {
            "authorization":         f"Bearer {cred.access}",
            "user-agent":             _USER_AGENT,
            "editor-version":         _EDITOR_VERSION,
            "editor-plugin-version":  _EDITOR_PLUGIN_VERSION,
        }

    async def login(self, *, enterprise_url: str | None = None) -> OAuthCredential:
        raise NotImplementedError("Plan 04 implements ...")

    async def refresh(self, cred: Credential) -> Credential:
        raise NotImplementedError("Plan 04 implements ...")
```

**`_main()` argparse stub** — raises NotImplementedError citing Plan 04. The `if __name__ == "__main__": sys.exit(_main())` block is in place so Plan 04 only fills in the body.

## Wave-2 Tests Flipped XFAIL → GREEN

7 tests in `tests/auth/providers/test_github_copilot.py` had their `pytest.xfail("Plan 02 ...")` first-lines deleted; they now execute their drafted assertion bodies and pass:

| Test | VALIDATION row | What it checks |
|------|---------------|----------------|
| `test_constants` | 017-02-01 | Plaintext `_CLIENT_ID = "Iv1.b507a08c87ecfe98"`; no obfuscation regex; no `_CLIENT_SECRET`; no `Ov23li8tweQw6odWQebz`; all 7 constants match expected values |
| `test_provider_id_dotted` | 017-02-02 | `GitHubCopilotAuth.provider_id == "github.copilot"` (dotted, NOT hyphenated `github-copilot`) |
| `test_is_token_oauth_long_lived` | 017-02-03 | `is_token` returns True for `gho_*` / `ghu_*` / `ghr_*`; rejects `sk-ant-*` / `ya29.*` / empty / case-mismatched / leading-whitespace |
| `test_is_token_session_token` | 017-02-04 | `is_token` returns True for all four prefixes (gho_/ghu_/tid_/ghr_); rejects upper-case TID_ and `xtid_` |
| `test_is_expired_5min_buffer_session` | 017-02-05 | 5-min-buffer boundaries: 200s before expiry → expired; 400s before → not expired; exactly 300s (boundary) → expired |
| `test_http_headers_copilot_stealth` | 017-02-06 | OAuthCredential → exactly 4 keys (authorization=Bearer tid_*, user-agent, editor-version, editor-plugin-version); ApiKeyCredential → {} |
| `test_satisfies_authmethod_protocol` | 017-02-07 | `isinstance(GitHubCopilotAuth(), AuthMethod) is True` — runtime_checkable Protocol conformance |

## Test Run Output

```
$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/auth/providers/test_github_copilot.py -q
.......xxxxxxxxxxxxxxxxxxx                                               [100%]
7 passed, 19 xfailed in 0.13s

$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/auth -q
153 passed, 1 skipped, 19 xfailed in 36.63s
```

- **7 passed** in test_github_copilot.py (Wave-2 GREEN as required)
- **19 xfailed** in test_github_copilot.py (Wave-3 + Wave-4 still pending Plans 03/04)
- **153 passed** in tests/auth (146 baseline + 7 new) — zero regression on Phase 014/015/016
- **1 skipped** in tests/auth (pre-existing baseline skip, unchanged)

## Cardinal-Rule Grep Gates

All required gates pass (verified 2026-04-30):

| Gate | Required | Actual | Status |
|------|----------|--------|--------|
| `Iv1.b507a08c87ecfe98` count | ≥ 1 | 4 | PASS |
| `Ov23li8tweQw6odWQebz` count | 0 | 0 | PASS |
| `from state_core.auth.oauth_common` count | 0 | 0 | PASS (Pitfall 13) |
| `^import litellm` / `^from litellm` count | 0 | 0 | PASS (CLAUDE.md) |
| `^from filelock` / `^import filelock` count | 0 | 0 | PASS (refresh.py rule 9) |
| `AsyncFileLock` count | 0 | 0 | PASS |
| `_CLIENT_SECRET` substring count | 0 | 0 | PASS (device-code = public client) |
| `_CLIENT_ID: str = "Iv1.b507a08c87ecfe98"` literal | ≥ 1 | 1 | PASS |
| `provider_id: str = "github.copilot"` literal | ≥ 1 | 1 | PASS |
| `NotImplementedError` count | ≥ 6 | 6 | PASS (`_request_device_code`, `_poll_for_token`, `_mint_session_token`, `login`, `refresh`, `_main`) |
| `P1-3` / `Pitfall 2` markers | ≥ 2 | 5 | PASS |
| Module LOC | ≥ 280 | 477 | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Forbidden substrings in cardinal-rule comments tripped test assertions**
- **Found during:** Task 2 verification (first pytest run of `test_constants`)
- **Issue:** The plan's prose suggested writing rationale comments such as "DO NOT swap to opencode's Ov23li8tweQw6odWQebz" and "NO _CLIENT_SECRET — device-code flow ...". The test bodies (which are part of the spec, drafted in Plan 01) assert the exact substrings `"Ov23li8tweQw6odWQebz" not in src`, `"_CLIENT_SECRET" not in src`, and (via the test_no_oauth_common_imports gate that Plan 04 will run) `"from filelock" not in src`. Writing the literal substring even inside a comment fails those gates.
- **Fix:** Rephrased the three comment fragments to avoid the literal substrings while preserving semantic intent:
  - `Ov23li8tweQw6odWQebz` → `Ov23li... family` / `Ov23li... GitHub App ID`
  - `_CLIENT_SECRET` → `client-secret constant` / `client-secret confidentiality`
  - `from filelock` → `filelock import` (no whitespace match)
- **Files modified:** `src/state_core/auth/providers/github_copilot.py` (5 comment-block lines edited)
- **Commits:** Folded into `b39497f` (Task 1) and `5aa37f1` (Task 2) before any push or merge

**2. [Rule 1 — Bug] Initial grep gate hit `# NO from filelock import` comment substring**
- **Found during:** Task 1 grep-gate verification
- **Issue:** Wrote a literal `# NO from filelock import` comment which contains the forbidden substring `from filelock`.
- **Fix:** Rephrased to `Intentionally absent: filelock import (...)` which has the same meaning but no `from filelock` substring.
- **Files modified:** `src/state_core/auth/providers/github_copilot.py` (one comment block, 4 lines)
- **Commits:** Folded into `b39497f` (Task 1)

### Issues Encountered

None. Both tasks executed cleanly; no auth gates; no out-of-scope discoveries. The two issues above are deviations from the plan's prose-suggested comment text, not deviations from the plan's contract — the contract is "constants + models + sync methods full + async stubs" and that contract was met.

## Self-Check: PASSED

**Files created:**
- `src/state_core/auth/providers/github_copilot.py` — FOUND (477 LOC) ✓
- `.planning/milestones/v2/phases/017-github-copilot-device-code-flow/017-02-SUMMARY.md` — FOUND (this file) ✓

**Files modified:**
- `tests/auth/providers/test_github_copilot.py` — 7 `pytest.xfail()` lines deleted ✓

**Commits:**
- `b39497f` feat(017-02): scaffold github_copilot module — constants, models, _PollingState, normalize_domain — FOUND ✓
- `5aa37f1` feat(017-02): GitHubCopilotAuth class — sync methods FULL, async stubbed — FOUND ✓

**Verification:**
- `pytest tests/auth/providers/test_github_copilot.py -q` — 7 passed, 19 xfailed ✓
- `pytest tests/auth -q` — 153 passed, 1 skipped, 19 xfailed (zero regression vs 146-passed baseline) ✓
- All 12 cardinal-rule grep gates pass ✓

## Files Modified

| File | Change | LOC |
|------|--------|-----|
| `src/state_core/auth/providers/github_copilot.py` | Created | +477 |
| `tests/auth/providers/test_github_copilot.py` | Modified (7 xfail lines deleted) | -7 |

## Commit Hashes

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `b39497f` | feat(017-02): scaffold github_copilot module — constants, models, _PollingState, normalize_domain |
| Task 2 | `5aa37f1` | feat(017-02): GitHubCopilotAuth class — sync methods FULL, async stubbed |

## Next Plans

- **Plan 017-03** turns the 9 Wave-3 polling tests GREEN by implementing `_request_device_code` (POST `/login/device/code` with JSON body) and `_poll_for_token` (RFC 8628 §3.5 state machine — slow_down persistence, monotonic deadline, 3s safety margin, asyncio.CancelledError passthrough, terminal access_denied / expired_token branches).
- **Plan 017-04** turns the 10 Wave-4 tests GREEN by implementing `_mint_session_token` (POST `/copilot_internal/v2/token` with Bearer + Copilot-stealth headers, including the 200-with-empty-body grant-revocation branch), `GitHubCopilotAuth.login` (orchestration: device-code → poll → mint → OAuthCredential with `extras["oauth_token"]` mirror), `GitHubCopilotAuth.refresh` (re-mint tid_* without ever calling GitHub's OAuth refresh endpoint), and `_main` (argparse with login + refresh subcommands, supports `--enterprise-url`).
