---
plan: 021-01
phase: 021-first-run-import-opencode-local
status: complete
wave: 1
completed: 2026-05-01
gap_closure: false
---

# 021-01 SUMMARY — Wave 1 RED scaffold + state.auth.imported event type

## Outcome

Wave 1 RED scaffolding for AUTH-11 (first-run import from opencode `auth.json`) plus the `state.auth.imported` event type added to `state_core.schema`. Schema additions are GREEN-on-arrival; test stubs are RED-by-design (import the not-yet-existing `state_core.auth.import_opencode`).

## Commits

- `c3b09a7` feat(021-01): add state.auth.imported event type to state_core.schema (+35 LOC: AuthImportedData with 3-field secret-free contract, AuthImportedEvent envelope, extended AUTH_EVENT_TYPES + AuthEvent union)
- `228f6fc` test(021-01): add Wave 1 RED scaffold for state_core.auth.import_opencode (598 LOC, 27 stubs covering IMPORT-01..IMPORT-26 with TEST-CANARY discipline + hypothesis @given for IMPORT-18 P1-7 + AST scan for IMPORT-25 determinism)
- `1c6fdcd` test(021-01): extend test_import_graph.py with mode-isolation lints (+100 LOC: six-substring guard + AST allowlist with SF-04 src.* ban)

## Key files (created/modified)

- `src/state_core/schema.py` (modified — AuthImportedData/Event added)
- `tests/auth/test_import_opencode.py` (created — 598 LOC RED stubs)
- `tests/auth/test_import_graph.py` (modified — +100 LOC mode-isolation lints)

## Verification

- 103 schema tests pass (no regression)
- `pytest tests/auth/test_import_opencode.py --collect-only` → exit 2 (ModuleNotFoundError, RED ✓)
- 2 new test_import_graph tests fail with "Wave 1 RED" message ✓ (RED-by-design)
- 4 existing test_import_graph tests still pass

## Self-Check: PASSED

Wave 1 contract is established. Wave 2 will provide the GREEN implementation in `src/state_core/auth/import_opencode.py`.
