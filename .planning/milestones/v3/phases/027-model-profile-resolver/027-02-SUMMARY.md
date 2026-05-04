---
phase: 027-model-profile-resolver
plan: "02"
subsystem: providers/model-profile
tags: [tdd, wave-1, green, prv-04, hypothesis, hooks]
dependency_graph:
  requires:
    - 027-01 (Wave 0 RED stubs for test contract)
  provides:
    - src/state_core/providers/model_profile.py — ModelProfile, ResolvedProfile, _DEFAULTS, resolve_profile(), build_chat_params(), GlobalProfileConfig
    - src/state_daemon/hooks.py — handle_chat_params(body: dict) -> dict framework-agnostic async handler
  affects:
    - Phase 028 (ProviderRouter scope-stack integration consumes resolve_profile() and handle_chat_params())
    - Phase 029 (AnthropicClient thinking_budget_tokens propagation)
    - Phase 031 (provider parity tests call handle_chat_params via quality/balanced/budget profiles)
tech_stack:
  added: []
  patterns:
    - Wave 1 TDD GREEN: full implementation turns 17+3 RED stubs to GREEN
    - Pydantic v2 model_validate(dump | overrides) pattern — model_copy(update=...) does not re-validate in Pydantic v2; model_validate on merged dict does
    - GlobalProfileConfig pydantic-settings with STATE_ env_prefix for daemon-level defaults
    - build_chat_params() returns camelCase keys (topP, maxOutputTokens) matching TS hook output interface
    - Mode isolation enforced by test_no_mode_silo_import (inspect.getsource pattern)
key_files:
  created:
    - src/state_core/providers/model_profile.py
    - src/state_daemon/hooks.py
  modified:
    - tests/test_model_profile.py (stubs replaced with real assertions)
    - tests/test_hooks.py (stubs replaced with real assertions)
decisions:
  - Use ResolvedProfile.model_validate(base.model_dump() | overrides) instead of model_copy(update=overrides) — Pydantic v2 model_copy does not re-validate field types; model_validate creates a new validated instance from the merged dict, which correctly raises ValidationError for type mismatches
  - Remove "state_build" and "state_teach" strings from module docstring — inspect.getsource() returns the literal source including docstrings, so mode-isolation assertions fail if those strings appear anywhere in the file, even in comments
metrics:
  duration: "~4 minutes"
  completed: "2026-05-03T22:18:25Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 2
---

# Phase 027 Plan 02: Wave 1 GREEN — Model Profile Resolver Implementation Summary

**One-liner:** ModelProfile StrEnum + ResolvedProfile frozen Pydantic model + resolve_profile() inheritance-chain walker + build_chat_params() camelCase serializer + handle_chat_params() framework-agnostic daemon hook handler — all 20 tests GREEN, full suite 850 passing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement model_profile.py | 5777d1a | src/state_core/providers/model_profile.py, tests/test_model_profile.py |
| 2 | Implement hooks.py | 9e0b94c | src/state_daemon/hooks.py, tests/test_hooks.py |

## Verification Results

**Step 1 — 20 new tests GREEN:**
```
20 passed in 1.09s
```

**Step 2 — Full suite no regressions:**
```
850 passed, 2 deselected in 54.56s
```
(Baseline was 830; 20 net-new tests added.)

**Step 3 — Mode isolation:**
```
CLEAN (no state_build or state_teach in either implementation file)
```

**Step 4 — Import sanity:**
```
All imports OK
ModelProfile members: [quality, balanced, budget, inherit]
```

**Step 5 — Hypothesis invariants (embedded in Step 1):**
```
test_resolve_never_returns_inherit PASSED
test_step_non_inherit_wins_over_all PASSED
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pydantic v2 model_copy does not re-validate field types**

- **Found during:** Task 1 (test_invalid_override_raises failing: "DID NOT RAISE ValidationError")
- **Issue:** The plan and research (Pitfall 2) stated that `frozen=True` + `model_copy(update=overrides)` would re-validate field types. In Pydantic v2, `model_copy(update=...)` does NOT re-validate — it creates a shallow copy with raw field assignment, bypassing validators. `validate_assignment=True` on the ConfigDict also does not affect `model_copy`.
- **Fix:** Changed `resolve_profile()` to use `ResolvedProfile.model_validate(base.model_dump() | overrides)` instead of `base.model_copy(update=overrides)`. This creates a new validated instance from a merged dict, which correctly raises `pydantic.ValidationError` for type mismatches (e.g., `temperature="warm"`).
- **Files modified:** src/state_core/providers/model_profile.py
- **Commit:** 5777d1a

**2. [Rule 1 - Bug] Module docstring contained mode-isolation trigger strings**

- **Found during:** Task 1 (test_no_mode_silo_import failing after 14/17 tests passed)
- **Issue:** The module docstring in model_profile.py contained the literal text "no state_build or state_teach imports" (copied from the plan's action block). `inspect.getsource()` returns the full source including docstrings, so the mode-isolation assertion `"state_build" not in source_lines` matched the docstring text.
- **Fix:** Rewrote the docstring to say "imports are limited to stdlib, pydantic, pydantic_settings, and structlog only" — preserving the intent without using the trigger strings.
- **Files modified:** src/state_core/providers/model_profile.py
- **Commit:** 5777d1a (same commit, fix applied before commit)

## Issues Encountered

None beyond the two auto-fixed bugs above. Both were caught by the test suite immediately during development.

## Self-Check: PASSED

- [x] src/state_core/providers/model_profile.py exists with 6 exported names (ModelProfile, ResolvedProfile, GlobalProfileConfig, _DEFAULTS, resolve_profile, build_chat_params)
- [x] src/state_daemon/hooks.py exists with handle_chat_params(body: dict) -> dict
- [x] 17/17 test_model_profile.py tests GREEN
- [x] 3/3 test_hooks.py tests GREEN
- [x] Full suite: 850 passed (was 830; +20 net-new)
- [x] Mode isolation: both files CLEAN
- [x] Commits 5777d1a and 9e0b94c exist
- [x] PRV-04 satisfied
