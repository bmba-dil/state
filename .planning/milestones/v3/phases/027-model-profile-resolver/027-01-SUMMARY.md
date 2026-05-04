---
phase: 027-model-profile-resolver
plan: "01"
subsystem: providers/model-profile
tags: [tdd, wave-0, red-stubs, prv-04, hypothesis]
dependency_graph:
  requires: []
  provides:
    - tests/test_model_profile.py — 17 RED stubs for ModelProfile, ResolvedProfile, resolve_profile(), build_chat_params(), GlobalProfileConfig
    - tests/test_hooks.py — 3 async RED stubs for /hook/chat-params handler
  affects:
    - Wave 1 (Plan 027-02) has a complete, unambiguous test contract to implement against
tech_stack:
  added: []
  patterns:
    - Wave 0 TDD RED pattern: top-level ImportError is the expected RED state; pytest.fail() used for all stubs except mode-isolation test
    - Hypothesis @given decorators written in RED form (strategy constants at module level for Wave 1 reuse)
    - Mode-isolation test written as real assertion (no pytest.fail) — passes GREEN once module exists without state_build/state_teach imports
key_files:
  created:
    - tests/test_model_profile.py
    - tests/test_hooks.py
  modified: []
decisions:
  - Handle mode-isolation test (test_no_mode_silo_import) as a real assertion rather than pytest.fail — it can turn GREEN independently of the full implementation
  - test_hooks.py: 3 tests created (plan spec listed 2 but VALIDATION.md coverage map requires 3 handler behaviors — all 3 stubs included)
  - Hypothesis strategy constants defined at module level so Wave 1 can flip stubs to real assertions without structural changes
metrics:
  duration: "~8 minutes"
  completed: "2026-05-03T22:09:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 027 Plan 01: Wave 0 RED Stubs — Model Profile Resolver Summary

**One-liner:** 17 RED test stubs for ModelProfile/ResolvedProfile/resolve_profile/build_chat_params + 3 async RED stubs for /hook/chat-params handler, establishing the full PRV-04 test contract before any implementation exists.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write RED stubs for model_profile module (17 tests) | 141e4b1 | tests/test_model_profile.py |
| 2 | Write RED stubs for hooks module (3 tests) | 2008e17 | tests/test_hooks.py |

## Verification Results

**RED state confirmed:**
```
ERROR tests/test_model_profile.py  — ModuleNotFoundError: No module named 'state_core.providers.model_profile'
ERROR tests/test_hooks.py          — ModuleNotFoundError: No module named 'state_daemon.hooks'
2 errors in 0.96s
```

**Baseline unaffected:**
```
830 passed, 2 deselected in 54.41s
```
(Baseline 830 tests pass when ignoring the two new RED files.)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one minor clarification:

**Task 2 test count:** The plan frontmatter said "2 RED test stubs for /hook/chat-params handler" but the VALIDATION.md coverage map lists 3 behavioral requirements for the handler (valid shape, default profile, quality profile). All 3 stubs were created as specified in the Task 2 behavior block. The plan text body was authoritative over the frontmatter count.

**Hypothesis test 5 strategy:** The second @given test (test_step_non_inherit_wins_over_all) uses `st.sampled_from([ModelProfile.quality, ModelProfile.balanced, ModelProfile.budget])` directly — the intermediate placeholder conditional was removed for cleanliness. Since the import fails at module level in Wave 0, the strategy is never evaluated; Wave 1 will use the clean form directly.

## Issues Encountered

None — both files created, RED state confirmed, baseline intact.

## Self-Check: PASSED

- [x] tests/test_model_profile.py exists with exactly 17 test functions
- [x] tests/test_hooks.py exists with exactly 3 async test functions
- [x] Both files show ERROR/ImportError RED state (not syntax error, not "passed")
- [x] Baseline 830 tests unaffected
- [x] test_no_mode_silo_import is a real assertion (no pytest.fail)
- [x] Both Hypothesis @given decorators present on tests 4 and 5
- [x] Commits 141e4b1 and 2008e17 exist
