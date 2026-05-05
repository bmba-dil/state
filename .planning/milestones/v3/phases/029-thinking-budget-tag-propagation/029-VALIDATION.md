---
phase: 029
slug: thinking-budget-tag-propagation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 029 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.0+ with pytest-asyncio 1.3.0+ (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 029-01-01 | 01 | 0 | PRV-08 | unit (RED stubs) | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py -x -q` | ❌ W0 | ⬜ pending |
| 029-02-01 | 02 | 1 | PRV-08 | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_build_thinking_param_quality_returns_enabled -x` | ❌ W0 | ⬜ pending |
| 029-02-02 | 02 | 1 | PRV-08 | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_build_thinking_param_balanced_returns_none -x` | ❌ W0 | ⬜ pending |
| 029-02-03 | 02 | 1 | PRV-08 | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_budget_below_minimum_raises -x` | ❌ W0 | ⬜ pending |
| 029-02-04 | 02 | 1 | PRV-08 | unit (httpx_mock) | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_quality_profile_propagates_budget_to_wire -x` | ❌ W0 | ⬜ pending |
| 029-02-05 | 02 | 1 | PRV-08 | unit (httpx_mock) | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_balanced_profile_no_thinking_in_wire -x` | ❌ W0 | ⬜ pending |
| 029-02-06 | 02 | 1 | PRV-08 | unit (httpx_mock) | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_custom_budget_propagates_to_wire -x` | ❌ W0 | ⬜ pending |
| 029-02-07 | 02 | 1 | PRV-08 | import | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_no_mode_silo_import -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_thinking_budget_propagation.py` — all 10 RED stubs for PRV-08
- [ ] `src/state_core/providers/thinking_budget.py` — stub module (created GREEN in Wave 1)

*Existing infrastructure covers all other phase requirements (pytest + HTTPXMock pattern operational from Phase 025).*

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
