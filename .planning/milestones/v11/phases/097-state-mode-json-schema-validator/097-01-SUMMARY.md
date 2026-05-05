---
phase: 097
plan: 01
type: execute
wave: 1
subsystem: state-core
tags: [schema, mode-config, pydantic, validation]
provides:
  - Canonical ModeConfig model in src/state_core/schema.py
  - Standalone validate_mode_config() function
  - Cleaned middleware imports (zero code duplication)
tech-stack:
  added: []
  modified:
    - pydantic (added ValidationError to schema.py imports)
  patterns: [config-model-not-frozen, canonical-schema-extraction]
key-files:
  created: []
  modified:
    - src/state_core/schema.py
    - src/state_daemon/middleware.py
    - tests/test_schema.py
    - tests/test_daemon_middleware.py
key-decisions:
  - "ModeConfig is NOT frozen (unlike event data models) because it represents a read-write configuration file"
  - "validate_mode_config() wraps Pydantic ValidationError in ValueError for cleaner programmatic API"
  - "ModeConfig's Literal['build','teach','both'] is intentionally narrower than Mode literal (which includes 'kernel') — kernel is internal-only, not persistable"
  - "Removed BaseModel from middleware.py pydantic import since no other class extends it after ModeConfig extraction"
patterns-established:
  - "Config models (non-event) live in schema.py with a separator comment block before the ULID validation section"
  - "Config models use ConfigDict(extra='forbid') but NOT frozen=True"
requirements-completed:
  - MODE-01
metrics:
  duration: "~2 min"
  completed: 2026-05-05
---

# Phase 097 Plan 01: Canonical ModeConfig + Validator in schema.py Summary

**One-liner:** Extracted `ModeConfig` pydantic model from middleware to its canonical home in `src/state_core/schema.py` with a standalone `validate_mode_config()` function, eliminating code duplication.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add ModeConfig and validate_mode_config() to schema.py with tests | `4c2e647` | `src/state_core/schema.py`, `tests/test_schema.py` |
| 2 | Update middleware.py to import ModeConfig from schema.py | `ae71ce0` | `src/state_daemon/middleware.py`, `tests/test_daemon_middleware.py` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing ValidationError import in schema.py**
- **Found during:** Task 1
- **Issue:** `validate_mode_config()` caught `ValidationError` but it wasn't imported. Resulted in `NameError` at runtime when validation failed.
- **Fix:** Added `ValidationError` to the pydantic import line in `schema.py`.
- **Files modified:** `src/state_core/schema.py`
- **Commit:** `4c2e647`

### Cleanups Beyond Plan

1. **Removed unused `Literal` import from middleware.py** — After removing the local `ModeConfig` class, the `from typing import Literal` import was no longer needed. Removed it.

2. **Import ordering fix** — The `from src.state_core.schema import ModeConfig` import was initially placed after `log = structlog.get_logger(__name__)`, which is non-standard. Moved it to the import block at the top of the file.

## Verification Results

### Plan Verification Commands — All Passing

```bash
# Schema + validator tests (11 new tests)
pytest tests/test_schema.py::TestModeConfig tests/test_schema.py::TestValidateModeConfig -v
# Result: 11 passed

# Full schema suite (no regressions)
pytest tests/test_schema.py -v
# Result: 114 passed

# Middleware regression tests (all existing pass with updated imports)
pytest tests/test_daemon_middleware.py -v
# Result: 41 passed

# Verify no local ModeConfig class in middleware
grep -c "class ModeConfig" src/state_daemon/middleware.py
# Result: 0

# Verify canonical import in middleware
grep -c "from src.state_core.schema import ModeConfig" src/state_daemon/middleware.py
# Result: 1

# Verify zero stale imports in test file
grep -c "from src.state_daemon.middleware import.*ModeConfig" tests/test_daemon_middleware.py
# Result: 0
```

### Success Criteria — All Met

1. ✅ ModeConfig is the single canonical definition in `src/state_core/schema.py`
2. ✅ `validate_mode_config()` provides clean programmatic validation without catching ValidationError externally
3. ✅ `src/state_daemon/middleware.py` delegates to canonical ModeConfig — zero code duplication
4. ✅ All existing tests pass with updated imports (no regressions)
5. ✅ New schema tests prove validation correctness for all edge cases:
   - Valid modes (build, teach, both): accepted
   - Invalid mode: rejected with ValidationError
   - Kernel mode: rejected with ValidationError (not persistable)
   - Missing mode: rejected with ValidationError
   - Extra fields: rejected (extra="forbid")
   - validator wrapper: raises ValueError (not ValidationError) on all failure modes

## Threat Flags

None — all threat model mitigations (`ConfigDict(extra="forbid")`, `Literal` type constraints, `ValueError` wrapping) are implemented as planned.

## Self-Check

Self-check verified: all modified files exist and commits are in git history.

```bash
[ -f "src/state_core/schema.py" ]    # FOUND
[ -f "src/state_daemon/middleware.py" ] # FOUND
[ -f "tests/test_schema.py" ]        # FOUND
[ -f "tests/test_daemon_middleware.py" ] # FOUND
```
- `4c2e647` exists: ✓ (Task 1)
- `ae71ce0` exists: ✓ (Task 2)

## Self-Check: PASSED
