---
phase: 028-cost-accounting-request
security_auditor: gsd-security-auditor
asvs_level: 1
block_on: high
threats_total: 12
threats_closed: 12
threats_open: 0
result: SECURED
completed: 2026-05-03
---

# Security Audit — Phase 028: Cost Accounting Request

**Result: SECURED**
**Threats Closed:** 12/12
**ASVS Level:** 1
**Block On:** high severity open threats

---

## Threat Verification

### Plan 01 Threats (schema extension + RED stubs)

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-028-P1-1 | Test integrity | mitigate | `tests/test_cost_accounting.py` lines 265, 272, 278, etc. — all stubs used `pytest.fail("RED: ...")`. CLOSED. |
| T-028-P1-2 | Schema integrity | mitigate | `src/state_core/schema.py` line 30 — `"provider"` added as 10th member with no removals. All 9 prior members preserved at lines 21–29. CLOSED. |
| T-028-P1-3 | Data integrity | mitigate | `tests/test_cost_accounting.py` line 98 — `test_compute_cost_unknown_model_returns_none` asserts `result is None`. CLOSED. |
| T-028-P1-4 | Mode isolation | mitigate | `tests/test_cost_accounting.py` lines 414–419 — `test_no_mode_silo_import` uses `inspect.getsource()` to assert absence of `state_build` and `state_teach`. CLOSED. |
| T-028-P1-5 | Error propagation | mitigate | `tests/test_cost_accounting.py` lines 196–219 — `test_emitter_reraises_on_provider_error` asserts `ProviderTransientError` propagates and error event is emitted. CLOSED. |

### Plan 02 Threats (implementation)

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-028-P2-1 | Data integrity | mitigate | `src/state_core/providers/cost_accounting.py` line 55 — `except Exception: return None`. Never returns 0.0 for unmapped models. CLOSED. |
| T-028-P2-2 | Error propagation | mitigate | `src/state_core/providers/cost_accounting.py` line 156 — bare `raise` (not `raise exc`) preserves traceback. CLOSED. |
| T-028-P2-3 | Mode isolation | mitigate | `src/state_core/providers/cost_accounting.py` — grep for `state_build\|state_teach` returns no matches. Imports are strictly `litellm`, `structlog`, `ulid`, `state_core.events`, `state_core.schema`, `time`. CLOSED. |
| T-028-P2-4 | Event durability | mitigate | `src/state_core/providers/cost_accounting.py` lines 120, 138, 176 — all three `self._store.append()` calls are `await`ed. No `asyncio.ensure_future` or `create_task` present. CLOSED. |
| T-028-P2-5 | Data correctness | mitigate | `src/state_core/providers/cost_accounting.py` lines 171–172 — cache tokens accessed as `getattr(usage, "_cache_read_input_tokens", 0)` and `getattr(usage, "_cache_creation_input_tokens", 0)` (direct attribute access, not `model_dump()`). CLOSED. |
| T-028-P2-6 | Measurement accuracy | mitigate | `src/state_core/providers/cost_accounting.py` lines 133, 137, 158 — `time.monotonic()` used exclusively for latency measurement. No `time.time()` calls. CLOSED. |
| T-028-P2-7 | Scope documentation | mitigate | `src/state_core/providers/cost_accounting.py` lines 9, 16 — module docstring states "Non-streaming only (streaming is Phase 030+)" and "Tech debt: Streaming calls not instrumented — deferred to Phase 030+". CLOSED. |

---

## Unregistered Threat Flags

No `## Threat Flags` sections were present in `028-01-SUMMARY.md` or `028-02-SUMMARY.md`. No unregistered flags to report.

---

## Accepted Risks Log

None. All threats are mitigated.

---

## Notes

- T-028-P2-3 (mode isolation): The module docstring originally contained the literal strings "state_build" and "state_teach" in a prohibition comment, which would have caused `test_no_mode_silo_import` to fail (since `inspect.getsource()` includes docstrings). This was caught and fixed during Plan 02 execution — the docstring now uses neutral phrasing "No build-mode or teach-mode packages are imported here." The test correctly enforces source-level isolation including docstrings.

- T-028-P1-1 and T-028-P1-2 are Wave 0 plan threats. By Wave 1, the stubs were replaced with real assertions; the threat controls are now the Wave 1 test assertions themselves.
