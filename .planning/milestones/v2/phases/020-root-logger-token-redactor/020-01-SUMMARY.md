---
phase: 020-root-logger-token-redactor
plan: 01
subsystem: state_core.observability
tags: [observability, redactor, m-a2, auth-10, redact-01..redact-26, red-tests, scaffold]
backfilled: 2026-05-02
backfill_reason: "Executor explicitly consolidated 020-01 SUMMARY into 020-02-SUMMARY per executor protocol (see 020-VERIFICATION.md Truth #4). Backfilled at v2 milestone close for archive traceability."
canonical_record: 020-02-SUMMARY.md
dependency-graph:
  requires:
    - 011 (state_core scaffold)
  provides:
    - tests/test_redactor.py (Wave 1 RED stubs for REDACT-01..REDACT-24, REDACT-26; ≥500 lines)
    - tests/test_observability_import_graph.py (REDACT-25 mode-isolation lint stub; ≥50 lines)
  affects:
    - 020-02..04 (GREEN — drives 26 REDACT-NN truths + Hypothesis property test to pass)
metrics:
  tasks_completed: 1
  red_stubs_authored: 26
  files_created: 2
---

# Phase 020 Plan 01: REDACT-NN Test Scaffold (RED) Summary

**Scope.** Author Wave 1 RED test stubs for the root-logger token redactor (AUTH-10): 25 REDACT-NN rows in `tests/test_redactor.py` (covering 12 token-shape regex families + 12 secret-key context-aware redactions + Hypothesis property test) plus the REDACT-25 mode-isolation lint in `tests/test_observability_import_graph.py`. Tests follow the `structlog.testing.capture_logs` pattern from `tests/auth/test_api_key.py:191`.

**Outcome.** All 26 RED stubs landed; Wave 1 fails by design (collection-time `ImportError` on `state_core.observability.redactor`). Plans 02..04 drove 26/26 GREEN.

## Backfill Note

`020-VERIFICATION.md` (Truth #4) explicitly states: *"020-01 SUMMARY consolidated into 020-02-SUMMARY per executor protocol."* This thin backfill exists at v2 milestone close to maintain a complete plan-summary chain. **For full execution detail and verification evidence, read `020-02-SUMMARY.md` and `020-VERIFICATION.md`.**
