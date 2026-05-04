---
phase: 024
slug: litellm-wrapper
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 024 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.0+ with pytest-asyncio 1.3.0+ |
| **Config file** | `pyproject.toml` — `asyncio_mode = "auto"` |
| **Quick run command** | `uv run python3 -m pytest tests/test_litellm_client.py -x -q` |
| **Full suite command** | `uv run python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python3 -m pytest tests/test_litellm_client.py -x -q`
- **After every plan wave:** Run `uv run python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 024-01-01 | 01 | 0 | PRV-01 | unit | `pytest tests/test_litellm_client.py -x` | ❌ W0 | ⬜ pending |
| 024-02-01 | 02 | 1 | PRV-01 | unit | `pytest tests/test_litellm_client.py::test_acompletion_returns_model_response -x` | ❌ W0 | ⬜ pending |
| 024-02-02 | 02 | 1 | PRV-01 | unit | `pytest tests/test_litellm_client.py::test_client_does_not_close_shared_httpx -x` | ❌ W0 | ⬜ pending |
| 024-02-03 | 02 | 1 | PRV-01 | unit | `pytest tests/test_litellm_client.py::test_rate_limit_maps_to_transient -x` | ❌ W0 | ⬜ pending |
| 024-02-04 | 02 | 1 | PRV-01 | unit | `pytest tests/test_litellm_client.py::test_auth_error_maps_to_auth_error -x` | ❌ W0 | ⬜ pending |
| 024-02-05 | 02 | 1 | PRV-01 | unit | `pytest tests/test_litellm_client.py::test_bad_request_maps_to_bad_request -x` | ❌ W0 | ⬜ pending |
| 024-02-06 | 02 | 1 | PRV-01 | property | `pytest tests/test_litellm_client.py::test_all_litellm_exceptions_map_to_state_errors -x` | ❌ W0 | ⬜ pending |
| 024-02-07 | 02 | 1 | PRV-07 | unit | `pytest tests/test_litellm_client.py::test_astream_yields_chunks_unchanged -x` | ❌ W0 | ⬜ pending |
| 024-02-08 | 02 | 1 | PRV-07 | unit | `pytest tests/test_litellm_client.py::test_astream_chunk_delta_content -x` | ❌ W0 | ⬜ pending |
| 024-02-09 | 02 | 1 | PRV-07 | unit | `pytest tests/test_litellm_client.py::test_astream_chunk_delta_tool_calls -x` | ❌ W0 | ⬜ pending |
| 024-02-10 | 02 | 1 | PRV-07 | unit | `pytest tests/test_litellm_client.py::test_astream_exception_maps_correctly -x` | ❌ W0 | ⬜ pending |
| 024-02-11 | 02 | 1 | both | import-graph | `pytest tests/test_litellm_client.py::test_no_mode_silo_import -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_litellm_client.py` — 11 RED stubs (all tests listed above)

*Existing pytest infrastructure carries over from Phase 023; no new framework gaps.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | All phase behaviors have automated verification. |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
