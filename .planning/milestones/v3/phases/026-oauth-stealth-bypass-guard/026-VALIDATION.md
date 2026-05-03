---
phase: 026
slug: oauth-stealth-bypass-guard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 026 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.0+ with pytest-asyncio 1.3.0+ (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| **Quick run command** | `python3 -m pytest tests/test_router.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_router.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 026-01-01 | 01 | 0 | PRV-03 | unit | `pytest tests/test_router.py -x -q` | ❌ W0 | ⬜ pending |
| 026-01-02 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_oauth_cred_routes_to_anthropic_client -x` | ❌ W0 | ⬜ pending |
| 026-01-03 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_anthropic_api_key_routes_to_litellm -x` | ❌ W0 | ⬜ pending |
| 026-01-04 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_non_anthropic_api_key_routes_to_litellm -x` | ❌ W0 | ⬜ pending |
| 026-01-05 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_oauth_client_has_correct_cred_bound -x` | ❌ W0 | ⬜ pending |
| 026-01-06 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_oauth_client_has_correct_deps_bound -x` | ❌ W0 | ⬜ pending |
| 026-01-07 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_select_is_sync -x` | ❌ W0 | ⬜ pending |
| 026-01-08 | 01 | 1 | PRV-03 | import | `pytest tests/test_router.py::test_oauth_routing_error_importable -x` | ❌ W0 | ⬜ pending |
| 026-01-09 | 01 | 1 | PRV-03 | import-graph | `pytest tests/test_router.py::test_no_mode_silo_import -x` | ❌ W0 | ⬜ pending |
| 026-01-10 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_oauth_route_log_no_token -x` | ❌ W0 | ⬜ pending |
| 026-01-11 | 01 | 1 | PRV-03 | unit | `pytest tests/test_router.py::test_litellm_route_log_no_token -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_router.py` — all 10 RED stubs (PRV-03 routing + secret hygiene tests)
- [ ] `src/state_core/providers/errors.py` — add `OAuthRoutingError` subclass of `StateProviderError`

*No framework gaps — pytest, `asyncio_mode = "auto"`, and structlog capture patterns are already established.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
