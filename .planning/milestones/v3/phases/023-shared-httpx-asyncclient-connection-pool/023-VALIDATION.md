---
phase: 023
slug: shared-httpx-asyncclient-connection-pool
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 023 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.0+ with pytest-asyncio 1.3.0+ |
| **Config file** | `pyproject.toml` — `asyncio_mode = "auto"` |
| **Quick run command** | `python3 -m pytest tests/test_http_client.py tests/test_deps.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q -m "not e2e and not integration"` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_http_client.py tests/test_deps.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q -m "not e2e and not integration"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 023-01-01 | 01 | 0 | PRV-06 | unit | `pytest tests/test_http_client.py -x` | ❌ W0 | ⬜ pending |
| 023-01-02 | 01 | 0 | PRV-06 | unit | `pytest tests/test_deps.py -x` | ❌ W0 | ⬜ pending |
| 023-02-01 | 02 | 1 | PRV-06 | unit | `pytest tests/test_http_client.py::test_build_shared_client_defaults -x` | ❌ W0 | ⬜ pending |
| 023-02-02 | 02 | 1 | PRV-06 | unit | `pytest tests/test_http_client.py::test_build_shared_client_proxy -x` | ❌ W0 | ⬜ pending |
| 023-02-03 | 02 | 1 | PRV-06 | unit | `pytest tests/test_http_client.py::test_build_shared_client_tls_skip -x` | ❌ W0 | ⬜ pending |
| 023-02-04 | 02 | 1 | PRV-06 | unit | `pytest tests/test_http_client.py::test_build_shared_client_env_proxy -x` | ❌ W0 | ⬜ pending |
| 023-02-05 | 02 | 1 | PRV-06 | unit | `pytest tests/test_http_client.py::test_build_shared_client_env_ca -x` | ❌ W0 | ⬜ pending |
| 023-03-01 | 03 | 1 | PRV-06 | unit | `pytest tests/test_deps.py::test_deps_holds_client -x` | ❌ W0 | ⬜ pending |
| 023-03-02 | 03 | 1 | PRV-06 | unit | `pytest tests/test_deps.py::test_deps_aclose -x` | ❌ W0 | ⬜ pending |
| 023-03-03 | 03 | 1 | PRV-06 | unit | `pytest tests/test_deps.py::test_startup_creates_deps -x` | ❌ W0 | ⬜ pending |
| 023-03-04 | 03 | 1 | PRV-06 | unit | `pytest tests/test_deps.py::test_anthropic_client_injection -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_http_client.py` — stubs for PRV-06 (build_shared_client tests)
- [ ] `tests/test_deps.py` — stubs for PRV-06 (Deps + startup tests)
- [ ] `tests/conftest.py` — shared fixtures if not already present

*Existing pytest infrastructure is in place (pytest 8.4.0 pinned); Wave 0 creates new test files.*

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
