---
phase: 026-oauth-stealth-bypass-guard
plan: "01"
subsystem: state_core.providers
tags: [tdd, wave-0, red, prv-03, oauth-routing, error-hierarchy]
dependency_graph:
  requires: [025-02-SUMMARY.md]
  provides: [tests/test_router.py, OAuthRoutingError in errors.py]
  affects: [026-02-PLAN.md (Wave 1 GREEN)]
tech_stack:
  added: []
  patterns: [wave-based-tdd, red-stubs-before-implementation, structlog-capture-pattern]
key_files:
  created:
    - tests/test_router.py
  modified:
    - src/state_core/providers/errors.py
decisions:
  - "OAuthRoutingError placed after ProviderResponseError in errors.py — matches docstring format of existing subclasses"
  - "Wave 0 test stubs use AttributeError (not pytest.raises) to confirm RED state naturally"
  - "test_oauth_routing_error_importable and test_no_mode_silo_import are GREEN immediately — they test error hierarchy and import isolation, not select()"
metrics:
  duration: "~2 minutes"
  completed: "2026-05-03"
  tasks_completed: 2
  files_changed: 2
---

# Phase 026 Plan 01: OAuth Stealth Bypass Guard — Wave 0 RED Stubs Summary

Wave 0 (RED) for PRV-03 bypass guard: 10 test stubs + OAuthRoutingError error class.

## What Was Built

**Task 1** — Added `OAuthRoutingError(StateProviderError)` to `src/state_core/providers/errors.py`. The class signals a programmer error when OAuth stealth traffic bypasses `ProviderRouter` to reach `LitellmClient`. Docstring follows the one-line-summary + blank-line + detail format of existing subclasses.

**Task 2** — Created `tests/test_router.py` with 10 PRV-03 regression tests covering:
- Routing correctness (OAuth → AnthropicClient, ApiKey → LitellmClient)
- Client binding verification (_cred and _deps bindings)
- select() is sync (no awaitable return)
- OAuthRoutingError importability and subclass check
- Mode silo isolation (no state_build.* / state_teach.* imports)
- Secret hygiene in logs (T-026-1: no access token or API key in structlog events)

## Wave 0 Result

```
8 failed (AttributeError: 'ProviderRouter' has no attribute 'select')
2 passed (test_oauth_routing_error_importable, test_no_mode_silo_import)
```

Correct Wave 0 RED state. Wave 1 (Plan 026-02) will implement `ProviderRouter.select()` to turn all 8 RED tests GREEN.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. All imports resolved at collection time. The 8 AttributeError failures are the expected RED state, not bugs.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 325e479 | feat(v3-026-01): add OAuthRoutingError to errors.py (PRV-03 Wave 0) |
| 2 | a806d49 | test(v3-026-01): RED stubs for ProviderRouter PRV-03 bypass guard (Wave 0) |

## Verification

- `grep -n "class OAuthRoutingError" src/state_core/providers/errors.py` → line 51
- `python3 -m pytest tests/test_router.py -q` → 8 failed, 2 passed
- `issubclass(OAuthRoutingError, StateProviderError)` → True
- Pre-existing test baseline: 663 passing (unchanged)

## Self-Check: PASSED

- `tests/test_router.py` exists: FOUND
- `class OAuthRoutingError` in `errors.py`: FOUND at line 51
- Task 1 commit 325e479: FOUND
- Task 2 commit a806d49: FOUND
