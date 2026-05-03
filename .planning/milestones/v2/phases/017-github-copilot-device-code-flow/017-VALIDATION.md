---
phase: 017
slug: github-copilot-device-code-flow
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 017 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + pytest-httpx |
| **Quick run command** | `.venv/bin/python -m pytest tests/auth/providers/test_github_copilot.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/auth -x -q` |
| **Estimated runtime** | ~30 seconds |

## Sampling Rate

- After every task commit: quick command
- After every plan wave: full suite
- Before verify-work: full suite must be green

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 017-01-01 | 01 | 1 | AUTH-04 | RED stubs | `pytest tests/auth/providers/test_github_copilot.py --collect-only` | ⬜ pending |
| 017-02-01 | 02 | 2 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_constants -x` | ⬜ pending |
| 017-02-02 | 02 | 2 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_provider_id_dotted -x` | ⬜ pending |
| 017-02-03 | 02 | 2 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_is_token_oauth_long_lived -x` | ⬜ pending |
| 017-02-04 | 02 | 2 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_is_token_session_token -x` | ⬜ pending |
| 017-02-05 | 02 | 2 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_is_expired_5min_buffer_session -x` | ⬜ pending |
| 017-02-06 | 02 | 2 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_http_headers_copilot_stealth -x` | ⬜ pending |
| 017-02-07 | 02 | 2 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_satisfies_authmethod_protocol -x` | ⬜ pending |
| 017-03-01 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_request_device_code -x` | ⬜ pending |
| 017-03-02 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_authorization_pending -x` | ⬜ pending |
| 017-03-03 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_slow_down_increases_interval -x` | ⬜ pending |
| 017-03-04 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_slow_down_persists -x` | ⬜ pending |
| 017-03-05 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_access_denied -x` | ⬜ pending |
| 017-03-06 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_expired_token -x` | ⬜ pending |
| 017-03-07 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_monotonic_deadline -x` | ⬜ pending |
| 017-03-08 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_safety_margin_3s -x` | ⬜ pending |
| 017-03-09 | 03 | 3 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_poll_cancelled_via_signal -x` | ⬜ pending |
| 017-04-01 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_mint_session_token -x` | ⬜ pending |
| 017-04-02 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_mint_grant_revoked_200_null_body -x` | ⬜ pending |
| 017-04-03 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_mint_grant_revoked_401 -x` | ⬜ pending |
| 017-04-04 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_mint_pydantic_validation -x` | ⬜ pending |
| 017-04-05 | 04 | 4 | AUTH-04 | integration | `pytest tests/auth/providers/test_github_copilot.py::test_login_full_device_flow -x` | ⬜ pending |
| 017-04-06 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_refresh_remints_session_no_oauth_call -x` | ⬜ pending |
| 017-04-07 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_refresh_persists_extras_oauth_token -x` | ⬜ pending |
| 017-04-08 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_main_argparse_login -x` | ⬜ pending |
| 017-04-09 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_main_argparse_refresh -x` | ⬜ pending |
| 017-04-10 | 04 | 4 | AUTH-04 | unit | `pytest tests/auth/providers/test_github_copilot.py::test_no_oauth_common_imports -x` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `tests/auth/providers/test_github_copilot.py` — RED stubs covering all 26 cases above
- [ ] `tests/auth/providers/conftest.py` — extend with copilot fixtures (mock_device_code_response, mock_token_poll_responses, captured_session_mint_post)

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end device-flow against live GitHub | AUTH-04 | Requires real GitHub account + browser | `python -m state_core.auth.providers.github_copilot login` then visit verification_uri, enter user_code |
| Copilot session-token mint against live API | AUTH-04 | Requires Copilot subscription | After login, verify session token cached in vault `extras` |
| SAML SSO failure UX | AUTH-04 | Requires org with SAML enforcement | Attempt login with SAML-required account; verify clear error message |

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] No watch-mode flags

**Approval:** pending
