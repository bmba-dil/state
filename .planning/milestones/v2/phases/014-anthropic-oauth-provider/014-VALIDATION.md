---
phase: 014
slug: anthropic-oauth-provider
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
---

# Phase 014 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 014-RESEARCH.md `## Validation Architecture` section.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` + `pytest-httpx>=0.35` + `pytest-mock>=3.14` |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `pytest tests/auth/oauth_common/ tests/auth/providers/test_anthropic.py -x` |
| **Full suite command** | `pytest -x` |
| **Estimated runtime** | ~3 seconds (Phase 014 isolated) / ~15 seconds (full suite after 011/012/013) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/auth/oauth_common/ tests/auth/providers/test_anthropic.py -x`
- **After every plan wave:** Run `pytest tests/auth/ -x`
- **Before `/gsd:verify-work`:** `pytest -x` (full suite green)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 014-01-01 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/oauth_common/test_pkce.py::test_verifier_format -x` | ❌ W0 | ⬜ pending |
| 014-01-02 | 01 | 0 | AUTH-01 / P0-8 | unit | `pytest tests/auth/providers/test_anthropic.py::test_state_equals_verifier -x` | ❌ W0 | ⬜ pending |
| 014-01-03 | 01 | 0 | AUTH-01 / P0-5 | unit | `pytest tests/auth/providers/test_anthropic.py::test_client_id_matches_claude_code -x` | ❌ W0 | ⬜ pending |
| 014-01-04 | 01 | 0 | AUTH-01 / P0-1 | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_user_agent_exact -x` | ❌ W0 | ⬜ pending |
| 014-01-05 | 01 | 0 | AUTH-01 / P0-2 | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_anthropic_beta_exact -x` | ❌ W0 | ⬜ pending |
| 014-01-06 | 01 | 0 | AUTH-01 / P0-3 | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_x_app -x` | ❌ W0 | ⬜ pending |
| 014-01-07 | 01 | 0 | AUTH-01 / P0-4 | unit | `pytest tests/auth/providers/test_anthropic.py::test_http_headers_no_x_api_key -x` | ❌ W0 | ⬜ pending |
| 014-01-08 | 01 | 0 | AUTH-01 / P0-7 | unit | `pytest tests/auth/providers/test_anthropic.py::test_is_expired_uses_300s_buffer -x` | ❌ W0 | ⬜ pending |
| 014-01-09 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_login_token_post_shape -x` | ❌ W0 | ⬜ pending |
| 014-01-10 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_refresh_post_shape -x` | ❌ W0 | ⬜ pending |
| 014-01-11 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_token_response_ignores_unknown_field -x` | ❌ W0 | ⬜ pending |
| 014-01-12 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_inject_stealth_system_prefix -x` | ❌ W0 | ⬜ pending |
| 014-01-13 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_url_has_beta_true -x` | ❌ W0 | ⬜ pending |
| 014-01-14 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_satisfies_authmethod_protocol -x` | ❌ W0 | ⬜ pending |
| 014-01-15 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_paste_format_required -x` | ❌ W0 | ⬜ pending |
| 014-01-16 | 01 | 0 | AUTH-01 | unit | `pytest tests/auth/providers/test_anthropic.py::test_401_raises_stealth_rejected -x` | ❌ W0 | ⬜ pending |
| 014-01-17 | 01 | 0 | AUTH-01 (precedence regression) | unit | `pytest tests/auth/providers/test_anthropic.py::test_invalid_grant_in_refresh_raises_AuthRefreshError_not_StealthRejected -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/auth/oauth_common/__init__.py` — empty marker
- [ ] `tests/auth/oauth_common/test_pkce.py` — RED stubs for verifier/challenge/state-equals-verifier
- [ ] `tests/auth/providers/__init__.py` — empty marker
- [ ] `tests/auth/providers/test_anthropic.py` — RED stubs for all 17 test rows above (one test per row, including row 014-01-17 invalid_grant precedence regression)
- [ ] `tests/auth/providers/conftest.py` (optional) — fixtures: pinned verifier, fake `code#state`, mock `getpass.getpass`, token-endpoint mock-response factory. Fold into `tests/auth/conftest.py` if no naming clashes.
- [ ] No new framework / no dependency installs — `pytest`, `pytest-asyncio`, `pytest-httpx`, `pytest-mock` already in `pyproject.toml`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-Anthropic stealth round-trip works (subscription pricing, not API-key) | AUTH-01 | Requires a real Pro/Max account + live OAuth flow; cannot run in CI without leaking creds | Phase 022 release-smoke pipeline; gated behind `STATE_TEST_LIVE_ANTHROPIC=1` env var |
| mitmproxy capture cross-verifies pinned `_USER_AGENT`, `_ANTHROPIC_BETA`, token endpoint host, Content-Type | AUTH-01 | Requires running real Claude Code through a proxy | **Pre-merge gate (CONTEXT-locked):** run `mitmproxy --mode regular` against a Claude Code chat turn; diff captured headers against constants in `providers/anthropic.py`; both `(external, cli)` parenthetical and the full beta list MUST match |
| Captured-header golden-file regression test (AUTH-13) | AUTH-13 | Belongs to Phase 022 (post-CLI) | Phase 022 ships `tests/auth/golden/anthropic-headers.json` + a diff test |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies — **17/17 mapped**
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify — **OK (every task has a unit test)**
- [ ] Wave 0 covers all MISSING references — **OK (all 17 test rows in Wave 0 stub list)**
- [ ] No watch-mode flags — **OK (`-x` exit-on-first-fail, no `--watch`)**
- [ ] Feedback latency < 15s — **OK (~3s isolated)**
- [ ] `nyquist_compliant: true` set in frontmatter — **set after Wave 0 lands and stubs are red**
- [ ] mitmproxy pre-merge gate logged in PR description — **manual checklist item**

**Approval:** pending
