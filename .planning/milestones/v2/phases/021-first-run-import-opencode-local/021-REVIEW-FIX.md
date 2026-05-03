---
phase: 021-first-run-import-opencode-local
fixed_at: 2026-05-01T00:00:00Z
review_path: .planning/milestones/v2/phases/021-first-run-import-opencode-local/021-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 021: Code Review Fix Report

**Fixed at:** 2026-05-01T00:00:00Z
**Source review:** .planning/milestones/v2/phases/021-first-run-import-opencode-local/021-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (Critical: 0, Warning: 3)
- Fixed: 3
- Skipped: 0

Info findings (IN-01 .. IN-05) were out of scope for this fix iteration
(`fix_scope: critical_warning`).

## Fixed Issues

### WR-01: Orchestrator passes coroutine return value to a `count` log key but the importer returns `list[Credential]`

**Files modified:** `src/state_daemon/orchestrator.py`, `tests/test_orchestrator_import_opencode.py`
**Commit:** bdbc271
**Applied fix:** Renamed local from `imported_count` to `imported`, changed log to `count=len(imported)` so structlog never serializes a `Credential` repr into log output. Updated both orchestrator integration tests (`test_orchestrator_runs_importer_after_redactor_selfcheck`, `test_orchestrator_passes_store_and_mirror_to_importer`) to set `mock_importer.return_value = []` instead of `0`, enforcing the real `list[Credential]` contract at the test boundary.

Verification: `uv run pytest tests/test_orchestrator_import_opencode.py -q` — 3 passed.

### WR-02: `auth.import.unreadable` log path on JSONDecodeError omits the `path` field that the disk-read variant supplies

**Files modified:** `src/state_core/auth/import_opencode.py`, `tests/auth/test_import_opencode.py`
**Commit:** 3f86a9d
**Applied fix:** Threaded a single `source: str` local through `import_from_opencode` (set to `str(path)` on the disk-read branch and `"env_inline"` on the env-content branch). Both `auth.import.unreadable` log call sites now emit a uniform `source=...` field (renamed from `path=...` on the disk-read branch). Tightened the IMPORT-06 test (`test_unreadable_file_warn_and_continue`): replaced the OR-clause that masked missing fields with an assertion that every `auth.import.unreadable` WARN has `log_level == "warning"` AND a non-empty `source` field.

Verification: `uv run pytest tests/auth/test_import_opencode.py -q` — 41 passed.

### WR-03: The AST-based determinism scan in `test_importer_does_not_call_time_or_datetime_now` does not actually detect `time.time()` / `datetime.now()` calls

**Files modified:** `tests/auth/test_import_opencode.py`
**Commit:** 0cdb200
**Applied fix:** Replaced the brittle 2-segment Attribute walker with a three-layer guard: (1) substring scan for dotted call sites — catches `time.time(`, `datetime.now(`, `datetime.utcnow(`, `.utcnow(`; (2) `ast.ImportFrom` walker — catches `from time import time; time()` and `from datetime import datetime; datetime.now()`; (3) `ast.Import` walker — catches `import time as t; t.time()` aliased forms. The IMPORT-25 false-negative gap is now closed.

Verification: `uv run pytest tests/auth/test_import_opencode.py::test_importer_does_not_call_time_or_datetime_now -v` — passed; full file still 41 passed.

## Final Verification

`uv run pytest tests/auth/ tests/test_orchestrator_import_opencode.py -q` — **367 passed, 1 skipped** in 47.10s.

No regressions introduced.

---

_Fixed: 2026-05-01T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
