---
phase: 028
slug: cost-accounting-request
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 028 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ with `asyncio_mode = "auto"` |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py -x -q` |
| **Full suite command** | `.venv/bin/python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3 -m pytest tests/test_cost_accounting.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 028-01-01 | 01 | 0 | PRV-05 | unit (RED stub) | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py -x -q` | ❌ W0 | ⬜ pending |
| 028-02-01 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_compute_cost_known_model -x` | ❌ W0 | ⬜ pending |
| 028-02-02 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_compute_cost_unknown_model_returns_none -x` | ❌ W0 | ⬜ pending |
| 028-02-03 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_emitter_emits_request_event -x` | ❌ W0 | ⬜ pending |
| 028-02-04 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_emitter_emits_response_event -x` | ❌ W0 | ⬜ pending |
| 028-02-05 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_response_event_has_token_and_cost_fields -x` | ❌ W0 | ⬜ pending |
| 028-02-06 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_response_event_cost_none_for_unmapped_model -x` | ❌ W0 | ⬜ pending |
| 028-02-07 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_emitter_reraises_on_provider_error -x` | ❌ W0 | ⬜ pending |
| 028-02-08 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_request_response_share_request_id -x` | ❌ W0 | ⬜ pending |
| 028-02-09 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_single_scope -x` | ❌ W0 | ⬜ pending |
| 028-02-10 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_multiple_calls_same_scope -x` | ❌ W0 | ⬜ pending |
| 028-02-11 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_multiple_scopes -x` | ❌ W0 | ⬜ pending |
| 028-02-12 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_scope_type_filter -x` | ❌ W0 | ⬜ pending |
| 028-02-13 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_has_unknown_cost_flag -x` | ❌ W0 | ⬜ pending |
| 028-02-14 | 02 | 1 | PRV-05 | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_provider_aggregate_type_in_schema -x` | ❌ W0 | ⬜ pending |
| 028-02-15 | 02 | 1 | PRV-05 | import-graph | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_no_mode_silo_import -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cost_accounting.py` — 15 RED stubs covering all PRV-05 behaviors
- [ ] `src/state_core/schema.py` — add `"provider"` to `AggregateType` Literal + `ProviderRequestData`, `ProviderResponseData`, `PROVIDER_EVENT_TYPES`

*Existing infrastructure covers pytest setup — no new framework needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
