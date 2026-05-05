---
phase: 097-state-mode-json-schema-validator
fixed_at: 2026-05-05T00:00:00Z
review_path: .planning/milestones/v11/phases/097-state-mode-json-schema-validator/097-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 097: Code Review Fix Report

**Fixed at:** 2026-05-05T00:00:00Z
**Source review:** `.planning/milestones/v11/phases/097-state-mode-json-schema-validator/097-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### WR-01: Incomplete Provider event implementation — typed classes and union missing

**Files modified:** `src/state_core/schema.py`
**Commit:** `6e68542`
**Applied fix:** Added `ProviderRequestEvent` and `ProviderResponseEvent` typed event classes following the existing pattern (e.g., `SchedulerDeadlockEvent`). Added `ProviderEvent` discriminated union and included it in `AnyStateEvent`. Provider events now participate in the typed validation pipeline alongside all other aggregate events.

### WR-02: TOCTOU race in `load_mode_config` default config creation

**Files modified:** `src/state_daemon/middleware.py`
**Commit:** `c8eded8`
**Applied fix:** Replaced the check-then-create pattern (`os.path.isfile` followed by `open("w")`) with an atomic `os.open` using `O_CREAT | O_EXCL | O_WRONLY` with `0o600` mode. The file is created with correct permissions from the start — no `os.chmod` gap. A `FileExistsError` catch handles the race case where another process creates the file between `isfile()` and `open()`, falling through to the normal read path gracefully.

### WR-03: Inconsistent `VALID_MODES` / valid-mode definitions across three modules

**Files modified:** `src/state_core/schema.py`, `src/state_daemon/middleware.py`, `src/state_cli/main.py`
**Commit:** `9ea0cfe`
**Applied fix:** Defined canonical mode sets in `src/state_core/schema.py`:
- `PERSISTABLE_MODES`: `{"build", "teach", "both"}` — for `mode.json`
- `RUNTIME_MODES`: `{"build", "teach", "kernel"}` — for CLI filtering and event modes
- `ALL_RECOGNISED_MODES`: union of both — for header-validation middleware

`middleware.py` now imports `ALL_RECOGNISED_MODES` (replaces local `_VALID_MODES`). `main.py` now imports `RUNTIME_MODES` (replaces local `VALID_MODES`). Backwards-compatible aliases preserve internal variable names.

### WR-04: Locale-dependent encoding in `_do_export` file output

**Files modified:** `src/state_cli/main.py`
**Commit:** `3fde8e2`
**Applied fix:** Added `encoding="utf-8"` parameter to `open(output, "w")` call in `_do_export()`, matching the pattern already used by `mode_init` command. Prevents `UnicodeEncodeError` or silent corruption on platforms where the default encoding is not UTF-8 (e.g., Windows cp1252, CI runner ASCII).

### WR-05: `_do_export` carries unused `_output_format` parameter

**Files modified:** `src/state_cli/main.py`
**Commit:** `9cfd075`
**Applied fix:** Removed the `_output_format` parameter from `_do_export`'s function signature and from its single call site in the `export()` shell command. Format validation is already handled in the `export()` command before calling `_do_export`, making the parameter dead code in the async implementation.

---

_Fixed: 2026-05-05T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
