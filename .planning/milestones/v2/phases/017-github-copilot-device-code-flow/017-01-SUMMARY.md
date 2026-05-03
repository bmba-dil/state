---
phase: "017"
plan: "01"
subsystem: auth
tags: [auth, github-copilot, device-code, rfc-8628, red-stubs, wave-0, AUTH-04]
requirements: [AUTH-04]

dependency_graph:
  requires:
    - "Phase 011 — OAuthCredential / AuthMethod Protocol"
    - "Phase 013 — refresh_credential filelock-guarded path"
    - "Phase 015 — state_core.auth.errors (AuthError / AuthLoginError / AuthRefreshError)"
    - "Phase 014/015/016 — provider module structural template (constants → models → AuthMethod class → argparse __main__)"
  provides:
    - "tests/auth/providers/test_github_copilot.py — 26 RED-stub test cases mapped 1:1 to VALIDATION.md rows 017-02-01 through 017-04-10"
    - "tests/auth/providers/conftest.py — three new fixtures (mock_device_code_response / mock_token_poll_responses / captured_session_mint_post)"
    - "Verification contract for AUTH-04 — Plans 017-02/03/04 turn xfail → green by deleting xfail() lines"
  affects:
    - "Plan 017-02 (sync helpers / constants / models — Wave 2 — 7 tests)"
    - "Plan 017-03 (device-code polling state machine — Wave 3 — 9 tests)"
    - "Plan 017-04 (mint / login / refresh / argparse — Wave 4 — 10 tests)"

tech_stack:
  added: []
  patterns:
    - "RED-stubs via try/except ImportError + module-level pytestmark.skipif (matches Phase 015/016 — surfaces test names under --collect-only while runtime skips cleanly)"
    - "pytest.xfail(reason) as FIRST line of each test body, followed by FULL drafted assertion body (Plans 02-04 delete only the xfail line to flip XFAIL → GREEN)"
    - "Polling-state-machine tests inject monotonic + sleep callables EXPLICITLY (no global monkeypatch on time.monotonic / asyncio.sleep — test isolation)"
    - "Pinned constants HARD-CODED in test file (not imported from not-yet-existing source) — test file IS the spec"

key_files:
  created:
    - "tests/auth/providers/test_github_copilot.py — 1089 LOC, 26 tests"
  modified:
    - "tests/auth/providers/conftest.py — appended 96 LOC (3 fixtures); Phase 014/015/016 fixtures untouched"

decisions:
  - "Used try/except ImportError + pytestmark.skipif pattern (mirrors Phase 015 test_google_gemini.py and Phase 016 test_antigravity.py) instead of pytest.importorskip at module level. Reason: importorskip causes pytest --collect-only to emit zero tests, defeating the plan-checker traceability requirement that all 26 cases be listed by name. The try/except pattern lets collection enumerate every test while the skipif marker skips runtime execution until the module exists."
  - "Test names are HARD-CODED as the canonical row IDs in VALIDATION.md (test_constants → 017-02-01, test_provider_id_dotted → 017-02-02, …). Each docstring opens with 'VALIDATION row 017-NN-NN' so plan-checker / verify-work can map test names to rows by string match without needing a separate lookup file."
  - "For test_constants (017-02-01): combined three sub-checks into one test (plaintext literal in source, no obfuscation regex, no _CLIENT_SECRET) to keep the test count at the planned 26 rather than splitting across multiple tests. The single test body asserts all sub-conditions individually so per-row provenance is preserved in failure messages."
  - "For test_poll_slow_down_increases_interval (017-03-03): the second sleep duration was computed as (initial=5 + slow_down_bump=5 + safety=3) = 13s, not the 11s mentioned in the plan's prose. Reason: the plan body's arithmetic 'initial + 5 + safety_margin = 8 + 3 = 11' double-counts the safety margin (it would add safety twice — once into the 8 and once on top). Tests assert the unambiguous 13s = (5 + 5_bump + 3_safety). Plan 03's implementation must satisfy this value or revise the test."
  - "For test_poll_slow_down_persists (017-03-04): analogous correction — third sleep is (5 + 5 + 5 + 3) = 18s, matching the plan's stated end value. The intermediate sleeps are 8s (initial) → 13s (after first slow_down) → 18s (after second slow_down) — interval persists, NOT reset."
  - "test_login_full_device_flow patches state_core.auth.providers.github_copilot.asyncio.sleep with raising=False so the patch lands silently in Wave 0 RED state (module not yet on disk during pytest collection) and on Plan 04 GREEN state (module present)."

metrics:
  duration: "6m 10s"
  completed: "2026-04-30"
  tasks_completed: 2
  tests_added: 26
  fixtures_added: 3
---

# Phase 017 Plan 01: Wave 0 RED stubs for GitHubCopilotAuth — Summary

Created 26 RED-stub test cases (1:1 with VALIDATION.md rows 017-02-01 through 017-04-10) in `tests/auth/providers/test_github_copilot.py` and extended `tests/auth/providers/conftest.py` with three GitHub-Copilot-specific fixtures. All tests collect under pytest --collect-only and skip cleanly at runtime; Plans 02/03/04 will turn fixed subsets from XFAIL → GREEN by deleting `pytest.xfail()` lines.

## What Was Built

### Test file (1089 LOC, 26 tests)

`tests/auth/providers/test_github_copilot.py` — uses the Phase 015/016 try/except + pytestmark.skipif pattern so all 26 test names are surfaced under `--collect-only` while runtime executions skip until `state_core.auth.providers.github_copilot` exists.

**Wave 2 (Plan 02 — 7 tests, sync helpers + constants):**

| Test | VALIDATION row | Pitfall |
|------|---------------|---------|
| `test_constants` | 017-02-01 | P1-3, Pitfall 2 (legacy OAuth App `Iv1.b507a08c87ecfe98`) |
| `test_provider_id_dotted` | 017-02-02 | Pitfall 9-info (dotted vs hyphenated) |
| `test_is_token_oauth_long_lived` | 017-02-03 | — |
| `test_is_token_session_token` | 017-02-04 | — |
| `test_is_expired_5min_buffer_session` | 017-02-05 | Pitfall 5, P0-7 / AUTH-09 |
| `test_http_headers_copilot_stealth` | 017-02-06 | Pitfall 12 (byte-stable stealth headers) |
| `test_satisfies_authmethod_protocol` | 017-02-07 | — |

**Wave 3 (Plan 03 — 9 tests, device-code polling state machine):**

| Test | VALIDATION row | Pitfall |
|------|---------------|---------|
| `test_request_device_code` | 017-03-01 | — |
| `test_poll_authorization_pending` | 017-03-02 | — |
| `test_poll_slow_down_increases_interval` | 017-03-03 | Pitfall 6 |
| `test_poll_slow_down_persists` | 017-03-04 | Pitfall 6 (NEW OWNED) |
| `test_poll_access_denied` | 017-03-05 | — |
| `test_poll_expired_token` | 017-03-06 | Pitfall 3 |
| `test_poll_monotonic_deadline` | 017-03-07 | Pitfall 7 (NEW OWNED) |
| `test_poll_safety_margin_3s` | 017-03-08 | Pitfall 10 (NEW OWNED) |
| `test_poll_cancelled_via_signal` | 017-03-09 | Pitfall 9 (NEW OWNED) |

**Wave 4 (Plan 04 — 10 tests, mint / login / refresh / argparse):**

| Test | VALIDATION row | Pitfall |
|------|---------------|---------|
| `test_mint_session_token` | 017-04-01 | — |
| `test_mint_grant_revoked_200_null_body` | 017-04-02 | Pitfall 4 / P1-6 |
| `test_mint_grant_revoked_401` | 017-04-03 | — |
| `test_mint_pydantic_validation` | 017-04-04 | — |
| `test_login_full_device_flow` | 017-04-05 | — |
| `test_refresh_remints_session_no_oauth_call` | 017-04-06 | — |
| `test_refresh_persists_extras_oauth_token` | 017-04-07 | — |
| `test_main_argparse_login` | 017-04-08 | — |
| `test_main_argparse_refresh` | 017-04-09 | — |
| `test_no_oauth_common_imports` | 017-04-10 | Pitfall 13 |

### Conftest fixtures (3 added, 96 LOC appended)

`tests/auth/providers/conftest.py` was EXTENDED — Phase 014/015/016 fixtures (lines 1-363) untouched. Three new fixtures appended under a marked `# ── GitHub Copilot fixtures (Phase 017) ──` section:

```python
@pytest.fixture
def mock_device_code_response() -> dict[str, Any]:
    """Canonical 200-OK payload from POST https://github.com/login/device/code."""

@pytest.fixture
def mock_token_poll_responses() -> dict[str, dict[str, Any]]:
    """Canonical RFC 8628 §3.5 poll-endpoint response variants
    (success, authorization_pending, slow_down with/without server interval,
    expired_token, access_denied)."""

@pytest.fixture
def captured_session_mint_post() -> dict[str, Any]:
    """Canonical 200-OK payload from POST https://api.github.com/copilot_internal/v2/token.
    expires_at pinned to 2030-01-01 UTC (1893456000) so tests never see naturally-expired tokens."""
```

### Constants embedded in test file

The test file owns these literals directly so Plan 02 can land the source module without re-deriving from RESEARCH.md:

| Constant | Value | Origin |
|---------|-------|--------|
| `_CLIENT_ID` | `"Iv1.b507a08c87ecfe98"` | Legacy OAuth App; verified via copilot.vim, B00TK1D/copilot-api, litellm, hermes-agent #16551 (Pitfall 2 regression — opencode's `Ov23li8tweQw6odWQebz` is the WRONG ID for the two-tier mint) |
| `_SCOPE` | `"read:user"` | RFC 8628 device-code body field |
| `_USER_AGENT` | `"GithubCopilot/1.155.0"` | Copilot-stealth UA — Pattern 7 |
| `_EDITOR_VERSION` | `"Neovim/0.6.1"` | Copilot-stealth Editor-Version |
| `_EDITOR_PLUGIN_VERSION` | `"copilot.vim/1.16.0"` | Copilot-stealth Editor-Plugin-Version |
| `_PROVIDER_ID` | `"github.copilot"` | Dotted-namespace (NOT opencode's hyphenated `github-copilot` — Phase 021 import maps) |
| `_POLLING_SAFETY_MARGIN_S` | `3.0` | OAUTH_POLLING_SAFETY_MARGIN_MS = 3000 — Pitfall 10 |
| `_SLOW_DOWN_BUMP_S` | `5.0` | RFC 8628 §3.5 slow_down increment — Pitfall 6 |

## Wave 0 RED-State Confirmed

```
$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest \
    tests/auth/providers/test_github_copilot.py --collect-only -q
  …
  tests/auth/providers/test_github_copilot.py::test_main_argparse_login
  tests/auth/providers/test_github_copilot.py::test_main_argparse_refresh
  tests/auth/providers/test_github_copilot.py::test_no_oauth_common_imports

  26 tests collected in 0.05s

$ PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/auth -q
  146 passed, 27 skipped in 36.50s
```

- **26 tests collected** — all listed by name under --collect-only ✓
- **146 passed** (baseline 146 — zero regression vs Phase 014/015/016) ✓
- **27 skipped** — 26 new (test_github_copilot.py) + 1 baseline (pre-existing) ✓
- All 26 stubs execute `pytest.skip` via the module-level `pytestmark` (the inner `pytest.xfail()` lines never run because `state_core.auth.providers.github_copilot` does not yet exist) ✓

## Grep Gate Results

```
VALIDATION row 017- count          : 26    (≥26 required)
Iv1.b507a08c87ecfe98 count         : 7     (≥1 required — Pitfall 2 regression)
pytest.xfail|importorskip count    : 28    (≥20 required)
fixtures in conftest.py            : 3     (≥3 required)
```

All required literals appear at least once: `Iv1.b507a08c87ecfe98` (7), `GithubCopilot/1.155.0` (4), `Neovim/0.6.1` (5), `copilot.vim/1.16.0` (4), `read:user` (4), `tid_` (28), `gho_` (41), `ghu_` (5), `ghr_` (4), `github.copilot` (58), `copilot_internal/v2/token` (14), `login/device/code` (4), `login/oauth/access_token` (16).

## Phase 014/015/016 Regression Guard

```
$ git diff HEAD~2 HEAD -- tests/auth/providers/conftest.py | grep '^-' | grep -v '^---'
  (no output — no lines deleted from existing fixtures)
```

The conftest.py edits are pure additions — every Phase 014, 015, and 016 fixture (`fixture_verifier`, `fixture_paste`, `fixture_token_response`, `mock_getpass`, `mock_generate_verifier`, `fixture_gemini_*`, `fixture_google_*`, `mock_google_state_and_verifier`, `mock_loopback_callback`, `mock_authorize_url_antigravity`, `captured_token_post_antigravity`) is byte-identical to the pre-plan state.

`pytest tests/auth/providers/test_google_gemini.py tests/auth/providers/test_antigravity.py --collect-only` still collects 52 tests (unchanged from baseline).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Switched from pytest.importorskip to try/except + pytestmark.skipif**
- **Found during:** Task 2 verification (first `pytest --collect-only` run)
- **Issue:** The plan's `<action>` block specified using `pytest.importorskip("state_core.auth.providers.github_copilot", ...)` at module top. When the module does not exist, importorskip causes the entire module to be SKIPPED at the collection stage, so `--collect-only` reports `0 tests collected` instead of listing the 26 cases by name. This violates the plan's `<done>` criterion that all 26 cases be enumerated.
- **Fix:** Adopted the same try/except ImportError + module-level `pytestmark = pytest.mark.skipif(not _AVAILABLE, reason=...)` pattern used in Phase 015 (`test_google_gemini.py`) and Phase 016 (`test_antigravity.py`). This pattern lets pytest collect every test by name while still skipping execution until the module lands.
- **Files modified:** `tests/auth/providers/test_github_copilot.py` (header block only)
- **Commit:** `972c464`
- **Documented in plan as:** the plan listed this same alternative inside `test_google_gemini.py`'s precedent — the deviation is from the prose suggestion, not from the precedent reference.

### Issues Encountered

None — both tasks executed cleanly; no out-of-scope discoveries; no auth gates.

## Self-Check: PASSED

**Files created:**
- `tests/auth/providers/test_github_copilot.py` — FOUND ✓

**Files modified:**
- `tests/auth/providers/conftest.py` — FOUND (96 LOC appended) ✓

**Commits:**
- `539cd94` test(017-01): extend conftest.py with GitHub Copilot fixtures — FOUND ✓
- `972c464` test(017-01): add 26 RED-stub test cases for GitHubCopilotAuth — FOUND ✓

**Verification:**
- `pytest tests/auth/providers/test_github_copilot.py --collect-only -q` — 26 tests collected ✓
- `pytest tests/auth -q` — 146 passed, 27 skipped (zero regression vs baseline 146 passed, 1 skipped + 26 new skips) ✓
- All grep gates pass ✓

## Files Modified

| File | Change | LOC |
|------|--------|-----|
| `tests/auth/providers/test_github_copilot.py` | Created | +1089 |
| `tests/auth/providers/conftest.py` | Appended (3 fixtures) | +96 |

## Commit Hashes

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `539cd94` | test(017-01): extend conftest.py with GitHub Copilot fixtures |
| Task 2 | `972c464` | test(017-01): add 26 RED-stub test cases for GitHubCopilotAuth |

## Next Plans

- **Plan 017-02** turns the 7 Wave-2 sync-helper tests GREEN by landing `_CLIENT_ID`, `_SCOPE`, `_USER_AGENT`, `_EDITOR_VERSION`, `_EDITOR_PLUGIN_VERSION`, `_POLLING_SAFETY_MARGIN_S`, `_SLOW_DOWN_BUMP_S`, the three Pydantic models (`DeviceCodeResponse`, `DeviceTokenResponse`, `CopilotSessionResponse`), and the `GitHubCopilotAuth` class with `provider_id` / `is_token` / `is_expired` / `http_headers` methods.
- **Plan 017-03** turns the 9 Wave-3 polling tests GREEN by landing `_request_device_code` and `_poll_for_token` with the RFC 8628 §3.5 state machine.
- **Plan 017-04** turns the 10 Wave-4 tests GREEN by landing `_mint_session_token`, `login`, `refresh`, and the `_main` argparse entry point.
