---
phase: 016
slug: antigravity-oauth-provider
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 016 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + pytest-httpx |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `.venv/bin/python -m pytest tests/auth/providers/test_antigravity.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/auth -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 016-01-01 | 01 | 1 | AUTH-03 | RED stubs | `pytest tests/auth/providers/test_antigravity.py --collect-only` | ⬜ pending |
| 016-02-01 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_constants_plaintext -x` | ⬜ pending |
| 016-02-02 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_build_authorize_url -x` | ⬜ pending |
| 016-02-03 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_localhost_literal_in_redirect_uri -x` | ⬜ pending |
| 016-02-04 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_fixed_port_51121 -x` | ⬜ pending |
| 016-02-05 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_five_scopes_present -x` | ⬜ pending |
| 016-02-06 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_id_token_parser -x` | ⬜ pending |
| 016-02-07 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_exchange_code -x` | ⬜ pending |
| 016-02-08 | 02 | 2 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_client_metadata_platform_detection -x` | ⬜ pending |
| 016-03-01 | 03 | 3 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_provider_id_dotted -x` | ⬜ pending |
| 016-03-02 | 03 | 3 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_is_token -x` | ⬜ pending |
| 016-03-03 | 03 | 3 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_is_expired_5min_buffer -x` | ⬜ pending |
| 016-03-04 | 03 | 3 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_http_headers_user_agent -x` | ⬜ pending |
| 016-03-05 | 03 | 3 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_http_headers_goog_api_client -x` | ⬜ pending |
| 016-03-06 | 03 | 3 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_http_headers_client_metadata_json -x` | ⬜ pending |
| 016-03-07 | 03 | 3 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_satisfies_authmethod_protocol -x` | ⬜ pending |
| 016-04-01 | 04 | 4 | AUTH-03 | integration | `pytest tests/auth/providers/test_antigravity.py::test_login_full_flow -x` | ⬜ pending |
| 016-04-02 | 04 | 4 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_refresh_rotation_persisted -x` | ⬜ pending |
| 016-04-03 | 04 | 4 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_refresh_no_rotation_keeps_old -x` | ⬜ pending |
| 016-04-04 | 04 | 4 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_state_and_verifier_independent -x` | ⬜ pending |
| 016-04-05 | 04 | 4 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_main_argparse_login -x` | ⬜ pending |
| 016-04-06 | 04 | 4 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_main_argparse_refresh -x` | ⬜ pending |
| 016-04-07 | 04 | 4 | AUTH-03 | unit | `pytest tests/auth/providers/test_antigravity.py::test_port_51121_in_use_error_message -x` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/auth/providers/test_antigravity.py` — RED stubs covering all 23 cases above (xfail/skip until implementation lands)
- [ ] `tests/auth/providers/conftest.py` — extend with antigravity-specific fixtures (mock_authorize_url_antigravity, captured_token_post_antigravity)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end browser-driven login against live Google OAuth (Antigravity client) | AUTH-03 | Requires real Google account + browser; cannot be automated | `python -m state_core.auth.providers.antigravity login` then complete consent in browser; verify `.state/auth.json` contains `google.antigravity` entry |
| Refresh against live Google token endpoint | AUTH-03 | Real refresh-token rotation depends on Google's policy | After live login, force `python -m state_core.auth.providers.antigravity refresh google.antigravity`; confirm rotation behavior |
| FIXED port 51121 collision UX | AUTH-03 | Requires manually occupying port 51121 first | Run any listener on 51121, then `python -m state_core.auth.providers.antigravity login`; verify clear error message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags

**Approval:** pending
