---
phase: 025
slug: direct-anthropic-sdk-escape-hatch
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 025 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.0+ with pytest-asyncio 1.3.0+ (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| **Quick run command** | `python3 -m pytest tests/test_anthropic_client.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_anthropic_client.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 025-01-01 | 01 | 0 | PRV-02 | unit stub | `pytest tests/test_anthropic_client.py -x -q` | ❌ W0 | ⬜ pending |
| 025-01-02 | 01 | 1 | PRV-02 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_uses_shared_http_client -x` | ❌ W0 | ⬜ pending |
| 025-01-03 | 01 | 1 | PRV-02 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_oauth_stealth_headers -x` | ❌ W0 | ⬜ pending |
| 025-01-04 | 01 | 1 | PRV-02 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_no_x_api_key_with_oauth -x` | ❌ W0 | ⬜ pending |
| 025-01-05 | 01 | 1 | PRV-02 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_api_key_credential_headers -x` | ❌ W0 | ⬜ pending |
| 025-01-06 | 01 | 1 | PRV-02 | unit | `pytest tests/test_anthropic_client.py::test_does_not_close_shared_client -x` | ❌ W0 | ⬜ pending |
| 025-01-07 | 01 | 1 | PRV-02 | unit | `pytest tests/test_anthropic_client.py::test_connection_error_maps_to_transient -x` | ❌ W0 | ⬜ pending |
| 025-01-08 | 01 | 1 | PRV-02 | import | `pytest tests/test_anthropic_client.py::test_errors_importable_from_errors_module -x` | ❌ W0 | ⬜ pending |
| 025-01-09 | 01 | 1 | PRV-08 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_thinking_budget_passed_through -x` | ❌ W0 | ⬜ pending |
| 025-01-10 | 01 | 1 | PRV-08 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_thinking_blocks_preserved -x` | ❌ W0 | ⬜ pending |
| 025-01-11 | 01 | 1 | PRV-09 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_cache_control_passed_through -x` | ❌ W0 | ⬜ pending |
| 025-01-12 | 01 | 1 | PRV-09 | unit (httpx_mock) | `pytest tests/test_anthropic_client.py::test_cache_usage_preserved -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_anthropic_client.py` — all 18 RED stubs for PRV-02, PRV-08, PRV-09
- [ ] `src/state_core/providers/errors.py` — extracted `StateProviderError` hierarchy (created in Wave 1 GREEN alongside `test_anthropic_client.py`)

*Note: No framework gaps — pytest infrastructure and `HTTPXMock` pattern already used in `test_sync_mirror.py` and `test_deps.py`. No new conftest fixtures required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stealth headers match `claude-oauth.md` byte-for-byte | PRV-02 | Header spec is in a gitignored input file; automated test uses string literals derived from it | Compare httpx_mock captured headers against `state-inputs/claude-oauth.md` values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
