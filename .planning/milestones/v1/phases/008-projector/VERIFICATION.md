# Phase 008 — Projector: Verification Report

**Phase:** 008-projector
**Goal:** Rebuildable projections written through the single writer; `state events rebuild-projections` CLI
**Requirement IDs:** EVT-02
**Date:** 2026-04-24
**Verifier:** GSD Verifier

---

## Verdict: ✅ VERIFICATION PASSED

All must-haves are verified in the codebase. No blockers. All 38 tests pass, all 19 handlers registered, CLI command functional, no regressions.

---

## Must-Have Verification Table

### Must-Have 1: Projector Core Module (`src/state_core/projector.py`)

| # | Must-Have | Status | Evidence |
|---|-----------|--------|----------|
| 1.1 | File exists with `class Projector` | ✅ VERIFIED | `src/state_core/projector.py` — 663 lines, `class Projector` at line 420 |
| 1.2 | `HANDLERS` dict with exactly 19 handlers | ✅ VERIFIED | `len(HANDLERS) == 19` confirmed: 10 step + 4 slice + 5 concept |
| 1.3 | `_register_handler` decorator pattern | ✅ VERIFIED | Defined at line 38; used 19 times (grep: 19 `@_register_handler` matches) |
| 1.4 | `_validate_table` whitelist guards all SQL table interpolation | ✅ VERIFIED | Grep: 3 calls to `_validate_table` — one per cache table. Whitelist: `frozenset({"steps", "slices", "concepts"})` |
| 1.5 | `rebuild_all()` — single BEGIN IMMEDIATE/COMMIT transaction | ✅ VERIFIED | Lines 447-557: `PRAGMA synchronous=FULL`, `BEGIN IMMEDIATE`, DELETE + replay + INSERT OR REPLACE, `COMMIT` |
| 1.6 | `apply_event()` — live single-event upsert | ✅ VERIFIED | Lines 561-636: routes handler, reads existing row, INSERT OR REPLACE in own transaction |
| 1.7 | Unknown event types silently ignored | ✅ VERIFIED | `HANDLERS.get(event_type)` returns `None` → `log.debug(...)` + `continue` (rebuild_all) or `return` (apply_event) |
| 1.8 | No non-deterministic imports | ✅ VERIFIED | `grep` for `datetime.now`, `random`, `uuid`, `time`, `secrets` — 0 matches |
| 1.9 | All event payload fields map to cache table columns | ✅ VERIFIED | Step handlers return `(id, slice_id, state, title, frontmatter, updated_at)`; Slice: `(id, phase_id, state, worktree_dir, worktree_branch, frontmatter, updated_at)`; Concept: `(id, subject_id, learner_id, mastery_probability, scaffold_level, bloom_level, frontmatter, last_drilled_at, updated_at)` |

### Must-Have 2: CLI Integration (`src/state_cli/main.py`)

| # | Must-Have | Status | Evidence |
|---|-----------|--------|----------|
| 2.1 | `state events rebuild-projections` CLI command exists and is invocable | ✅ VERIFIED | CliRunner: `state events --help` shows `rebuild-projections` command. Command registered at line 28 |
| 2.2 | Follows `db_app` → `db init` sub-app pattern | ✅ VERIFIED | `events_app = typer.Typer(name="events", ...)` + `app.add_typer(events_app)` at lines 17-18, symmetric to `db_app` at lines 14-15 |
| 2.3 | Calls `_migrate()` before rebuild | ✅ VERIFIED | `_do_rebuild_projections()` at line 42: `await _migrate()` |
| 2.4 | Instantiates `SqliteEventStore` + `Projector` and calls `rebuild_all()` | ✅ VERIFIED | Lines 43-45: `store = SqliteEventStore()`, `projector = _Projector(db=store)`, `count = await projector.rebuild_all()` |
| 2.5 | Reports event count on success | ✅ VERIFIED | Line 46: `f"Projections rebuilt: {count} events processed."` |
| 2.6 | Error handling with try/except and exit code 1 | ✅ VERIFIED | Lines 31-35: `try: asyncio.run(...)` / `except Exception as exc: typer.echo(..., err=True)`, `raise typer.Exit(code=1)` |
| 2.7 | Late import of `SqliteEventStore` inside async function | ✅ VERIFIED | Line 40: `from src.state_core.events import SqliteEventStore` inside `_do_rebuild_projections()` |

### Must-Have 3: Test Suite (`tests/test_projector.py`)

| # | Must-Have | Status | Evidence |
|---|-----------|--------|----------|
| 3.1 | DB isolation fixture (`tmp_path` + `monkeypatch`) | ✅ VERIFIED | `_isolate_db` fixture at line 28 |
| 3.2 | `_append_events` helper | ✅ VERIFIED | Defined at line 50 |
| 3.3 | `_read_table` helper | ✅ VERIFIED | Defined at line 67 |
| 3.4 | 19 per-event-type projection tests (10+4+5) | ✅ VERIFIED | TestStepProjection (10), TestSliceProjection (4), TestConceptProjection (5) — all pass |
| 3.5 | Full rebuild integration tests | ✅ VERIFIED | TestFullRebuild (4 tests): empty log, multi-aggregate, event count, multi-event |
| 3.6 | Rebuild idempotency tests | ✅ VERIFIED | TestRebuildIdempotency (2 tests): same-DB, cross-DB determinism |
| 3.7 | Crash atomicity test | ✅ VERIFIED | TestCrashAtomicity (1 test): handler crash mid-rebuild, transaction rollback preserves cache |
| 3.8 | Live update tests | ✅ VERIFIED | TestLiveUpdate (2 tests): single event, multi-event accumulation |
| 3.9 | Edge case tests | ✅ VERIFIED | TestEdgeCases (4 tests): unknown event type, non-cache aggregate, event count integrity, interleaved aggregates |
| 3.10 | Hypothesis property test (50 examples) | ✅ VERIFIED | `test_property_rebuild_no_side_effects` — passed with 50 examples |
| 3.11 | Handler registry completeness test | ✅ VERIFIED | TestHandlerRegistry (5 tests): 19 handlers, step/slice/concept event keys all confirmed |
| 3.12 | All 38 tests pass | ✅ VERIFIED | `python3 -m pytest tests/test_projector.py -x -v` — 38 passed in 0.68s |

### Requirements Traceability

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **EVT-02**: SQLite is authoritative event source | ✅ VERIFIED | `REQUIREMENTS.md` marks EVT-02 as `[x]`. Projector reads all events from `.state/events.sqlite` exclusively — `rebuild_all()` at line 457: `SELECT ... FROM events ORDER BY aggregate_id ASC, seq ASC`. `apply_event()` reads existing cache rows from the same SQLite database. Projections are derived views — the authoritative source is always the `events` table. |
| **EVT-06**: Event payloads are deterministic | ✅ VERIFIED (indirect) | Projector explicitly enforces this: no `datetime.now()`, `random`, `uuid`, `time`, or `secrets` in projector.py. Handlers only receive `(current_state, event_data)` — no access to clocks or RNG. |

### Regression Check

| Check | Result |
|-------|--------|
| `python3 -m pytest tests/ -x --no-header -q` | **279 passed** in 12.63s — no regressions |

### Git Commit Verification

| Plan | Claimed Commits | Actual | Match |
|------|-----------------|--------|-------|
| A-Task1 | `ecaf766` | `ecaf766 feat(008-A): add projector module skeleton with handler registry pattern` | ✅ |
| A-Task2 | `cf54dae` | `cf54dae feat(008-A): add 19 projection handler functions for steps/slices/concepts` | ✅ |
| A-Task3 | `b864047` | `b864047 feat(008-A): add Projector class with rebuild_all and apply_event` | ✅ |
| B-Task1 | `a33bd54` | `a33bd54 feat(008-projector): add events Typer sub-app and Projector import` | ✅ |
| B-Task2 | `cb02d56` | `cb02d56 feat(008-projector): add state events rebuild-projections CLI command` | ✅ |
| C-Task1 | `9409383` | `9409383 feat(008-projector): add test skeleton with fixtures and helpers for projector tests` | ✅ |
| C-Task2 | `aa087fc` | `aa087fc feat(008-projector): add 19 per-event-type projection tests for step, slice, concept handlers` | ✅ |
| C-Task3 | `5e492a1` | `5e492a1 feat(008-projector): add integration tests for rebuild, idempotency, crash, edge cases, hypothesis` | ✅ |

---

## Minor Observations (Not Blockers)

1. **STATE.md out of date:** `.planning/milestones/v1/STATE.md` lists phase 008 as "Not started". Should be updated to "Complete" or the equivalent status.

2. **Plan acceptance criteria minor imprecision:**
   - Plan C's `grep -c "_isolate_db"` expected 1, actual is 2 (fixture definition + explicit `store` fixture dependency) — noted in Summary C's deviations.
   - `TestHypothesisProperty` was written as a standalone function (per Summary C deviation), not a class as the plan described. Functionality identical.
   - Plan B's `grep -c "rebuild-projections"` expected 1, actual is 2 (command decorator + docstring). Functionally correct.

3. **No `__main__` guard:** `src/state_cli/main.py` has no `if __name__ == "__main__": app()` — intentional per Summary B, the CLI is verified via `CliRunner`. Not a bug.

---

## Conclusion

**Phase 008 goal is fully achieved.** All three plans were executed as designed:
- Projector core module with 19 handlers and transactional rebuild/live update
- CLI command `state events rebuild-projections` with error handling
- 38 comprehensive tests covering all handlers, rebuild, idempotency, crash atomicity, live updates, edge cases, and Hypothesis property tests

EVT-02 is supported: projections always derive from the authoritative SQLite event store. No blockers found.
