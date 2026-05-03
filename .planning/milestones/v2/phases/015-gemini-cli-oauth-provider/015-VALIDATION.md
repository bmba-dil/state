---
phase: 015
slug: gemini-cli-oauth-provider
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 015 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + pytest-httpx |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/auth/oauth_common tests/auth/providers/test_google_gemini.py -x -q` |
| **Full suite command** | `pytest tests/auth -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 015-A-01 | A | 0 | AUTH-02 | RED stubs | `pytest tests/auth/oauth_common/test_loopback.py --collect-only` | ❌ W0 | ⬜ pending |
| 015-A-02 | A | 0 | AUTH-02 | RED stubs | `pytest tests/auth/providers/test_google_gemini.py --collect-only` | ❌ W0 | ⬜ pending |
| 015-A-03 | A | 0 | AUTH-02 | unit | `pytest tests/auth/test_errors.py -x` | ❌ W0 | ⬜ pending |
| 015-B-01 | B | 1 | AUTH-02 | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_port_allocator -x` | ❌ W0 | ⬜ pending |
| 015-B-02 | B | 1 | AUTH-02 | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_state_validation -x` | ❌ W0 | ⬜ pending |
| 015-B-03 | B | 1 | AUTH-02 | unit | `pytest tests/auth/oauth_common/test_loopback.py::test_redirect_handler -x` | ❌ W0 | ⬜ pending |
| 015-C-01 | C | 2 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_token_shape_sniffer -x` | ❌ W0 | ⬜ pending |
| 015-C-02 | C | 2 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_is_expired -x` | ❌ W0 | ⬜ pending |
| 015-C-03 | C | 2 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_http_headers -x` | ❌ W0 | ⬜ pending |
| 015-C-04 | C | 2 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_id_token_parser -x` | ❌ W0 | ⬜ pending |
| 015-C-05 | C | 2 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_build_authorize_url -x` | ❌ W0 | ⬜ pending |
| 015-C-06 | C | 2 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_exchange_code -x` | ❌ W0 | ⬜ pending |
| 015-D-01 | D | 3 | AUTH-02 | integration | `pytest tests/auth/providers/test_google_gemini.py::test_login_full_flow -x` | ❌ W0 | ⬜ pending |
| 015-D-02 | D | 3 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_refresh_rotation_persisted -x` | ❌ W0 | ⬜ pending |
| 015-D-03 | D | 3 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_refresh_no_rotation_keeps_old -x` | ❌ W0 | ⬜ pending |
| 015-D-04 | D | 3 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_refresh_5min_buffer -x` | ❌ W0 | ⬜ pending |
| 015-D-05 | D | 3 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_refresh_request_headers_match_gemini_cli -x` | ❌ W0 | ⬜ pending |
| 015-D-06 | D | 3 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_state_param_csrf_check -x` | ❌ W0 | ⬜ pending |
| 015-D-07 | D | 3 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_main_argparse_login -x` | ❌ W0 | ⬜ pending |
| 015-D-08 | D | 3 | AUTH-02 | unit | `pytest tests/auth/providers/test_google_gemini.py::test_main_argparse_refresh -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/auth/oauth_common/test_loopback.py` — stubs covering port allocator, state validation, success/failure redirect handlers
- [ ] `tests/auth/providers/test_google_gemini.py` — stubs for AUTH-02 (20 cases above)
- [ ] `tests/auth/test_errors.py` — stubs for promoted `AuthError`/`AuthLoginError`/`AuthRefreshError`
- [ ] `tests/auth/conftest.py` — shared fixtures (mock_authorize_url, captured_token_post, fake_credential_factory) — extend if exists from 014
- [ ] `tests/auth/oauth_common/__init__.py`, `tests/auth/oauth_common/conftest.py` — new sub-package fixtures (asyncio listener helper, free-port helper)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end browser-driven login against live Google OAuth | AUTH-02 | Requires real Google account + browser; cannot be automated in unit tests | `python -m state_core.auth.providers.google_gemini login` then complete the consent flow in the opened browser; verify `.state/auth.json` contains a `google.gemini_cli` entry with refresh_token and access_token |
| Refresh against live Google token endpoint | AUTH-02 | Real refresh_token rotation behavior depends on Google's policy; mock can't fully assert | After live login, wait until expiry buffer fires OR force `python -m state_core.auth.providers.google_gemini refresh google.gemini_cli`; confirm vault rewrites with rotated refresh_token (or persists original if Google omitted) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
