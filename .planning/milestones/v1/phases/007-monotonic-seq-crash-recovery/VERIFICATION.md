# Phase 007 — Monotonic Seq Crash Recovery: Verification Report

**Phase goal:** Add fsync discipline + recovery routine that detects and repairs gaps/duplicates in aggregate_seq; Hypothesis property-test that ANY crash offset + replay → monotonic sequence.

**Requirement:** EVT-03 — *"Event sequence is monotonic per stream (Arc / Phase / Slice / Step / concept / learner); crash-recovery reconciles gaps"*

**Verification date:** 2026-04-24
**Verifier:** GSD Verification Agent

---

## Classification

| Verdict | Scope |
|---------|-------|
| **⚠️ GAPS FOUND** | Startup wiring (run_repair_now) — uncommitted regression |

---

## Must-Have Verification

### MH1: Fsync discipline (synchronous=FULL)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Connection default is synchronous=FULL | ✅ **VERIFIED** | `src/state_core/database.py` line 54: `await db.execute("PRAGMA synchronous=FULL;")` |
| Belt-and-suspenders per-method overrides | ✅ **VERIFIED** | `src/state_core/events.py` line 115 (append) and line 237 (repair_aggregate_seqs) both set `PRAGMA synchronous=FULL` inline |
| Belt-and-suspenders docstring explains pattern | ✅ **VERIFIED** | `database.py` docstring lines 8-13 |
| Fsync does not break normal writes | ✅ **VERIFIED** | `TestFsyncDiscipline` — 4 tests, 29/29 pass |
| `grep "PRAGMA synchronous" src/state_core/database.py` shows FULL | ✅ **VERIFIED** | Shows `PRAGMA synchronous=FULL` |

**Source claim:** Plan A (007-A-PLAN.md) — "synchronous=FULL as connection default"

---

### MH2: Recovery routine (repair_aggregate_seqs)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Method exists on SqliteEventStore | ✅ **VERIFIED** | `src/state_core/events.py` lines 218-276 `async def repair_aggregate_seqs()` |
| Scans events for max seq per aggregate | ✅ **VERIFIED** | Line 240-243: `SELECT aggregate_id, MAX(seq) AS max_seq FROM events GROUP BY aggregate_id` |
| Updates aggregate_seq when mismatch found | ✅ **VERIFIED** | Lines 258-264: `INSERT OR REPLACE INTO aggregate_seq` with corrected seq |
| Idempotent (no-op when consistent) | ✅ **VERIFIED** | Test `test_repair_twice_idempotent` and `test_repair_already_consistent` both pass |
| Handles stale seq (events ahead of aggregate_seq) | ✅ **VERIFIED** | `test_repair_stale_seq` passes — corrects seq from 1→3 |
| Handles future seq (aggregate_seq ahead of events) | ✅ **VERIFIED** | `test_repair_future_seq` passes — corrects seq from 99→2 |
| Handles deleted aggregate_seq rows | ✅ **VERIFIED** | `test_repair_empty_aggregate_seq` passes — restores seq 0→2 |
| Handles multiple aggregates | ✅ **VERIFIED** | `test_repair_multiple_aggregates`, `test_repair_mixed_mismatches` pass |
| Append after repair gets correct seq | ✅ **VERIFIED** | `test_append_after_repair_gets_correct_seq` passes |

**Source claim:** Plan A (007-A-PLAN.md) — "repair_aggregate_seqs() recovery routine for post-crash seq repair"

---

### MH3: Migration 0004 — UNIQUE(aggregate_id, seq) index

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Migration SQL file exists | ✅ **VERIFIED** | `.state/migrations/0004_add_unique_agg_seq.sql` |
| Git-tracked | ✅ **VERIFIED** | `git ls-files` confirms it's in the repo |
| Correct SQL: `CREATE UNIQUE INDEX IF NOT EXISTS idx_events_agg_seq ON events(aggregate_id, seq)` | ✅ **VERIFIED** | Content matches exactly |
| Expected index in migration test | ✅ **VERIFIED** | `tests/test_migrations.py` line 205: `"idx_events_agg_seq"` in `expected_indexes` |
| Index test passes | ✅ **VERIFIED** | `test_all_indexes_exist` — 1/1 passes |
| UNIQUE constraint prevents duplicate seq | ✅ **VERIFIED** | `test_unique_constraint_prevents_duplicate_seq` passes |
| UNIQUE allows different seq per aggregate | ✅ **VERIFIED** | `test_unique_constraint_allows_different_seq` passes |
| UNIQUE allows same seq across aggregates | ✅ **VERIFIED** | `test_unique_constraint_allows_same_seq_different_aggregate` passes |

**Source claim:** Plan B (007-B-PLAN.md) — "DB-level constraint preventing seq collisions"

---

### MH4: Hypothesis property tests — crash simulation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `test_hypothesis_crash_recovery_monotonic` exists and passes | ✅ **VERIFIED** | Test at line 348, 100 examples, 29/29 pass |
| Crash simulation via monkeypatched commit() | ✅ **VERIFIED** | Lines 389-397 wrap `aiosqlite.Connection.commit` to raise at configurable offset |
| Property: monotonically increasing seq | ✅ **VERIFIED** | Line 420: `assert sorted(seq_list) == seq_list` |
| Property: no duplicate seq per aggregate | ✅ **VERIFIED** | Line 427: `assert len(set(seq_list)) == len(seq_list)` |
| Property: seq starts at 1 | ✅ **VERIFIED** | Line 433: `assert seq_list[0] == 1` |
| Property: events.MAX(seq) == aggregate_seq.seq | ✅ **VERIFIED** | Lines 438-456 — cross-table verification |
| Edge: empty store crash is no-op | ✅ **VERIFIED** | Lines 459-463: crash_at_op=0 with 0 prior events → no repairs |
| Hypothesis strategies: num_aggregates, prior_events, crash_at_op | ✅ **VERIFIED** | Lines 343-347: 3 strategies with integer ranges |
| Additional property test: seq monotonic after append | ✅ **VERIFIED** | `test_hypothesis_seq_monotonic_after_append` (line 215) |
| Additional property test: random mismatch repair | ✅ **VERIFIED** | `test_hypothesis_repair_random_mismatch` (line 263) |

**Source claim:** Plan D (007-D-PLAN.md) — "Crash-Simulation Hypothesis Property Tests"

---

### MH5: Startup repair wiring — ⚠️ FAILED (Regression)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `__init__` with `_repair_done` flag | ✅ **VERIFIED** | `events.py` lines 57-59 |
| `_maybe_repair()` / `_maybe_run_repair()` called from append() | ✅ **VERIFIED** | Line 107 |
| `_maybe_repair()` / `_maybe_run_repair()` called from read_stream() | ✅ **VERIFIED** | Line 171 |
| `run_repair_now()` public method | ❌ **FAILED** | Present in committed code (HEAD), **REMOVED in working tree** |
| Lazy repair called from get_unsynced_events() | ✅ **VERIFIED** | Line 199 (unplanned addition, working tree only) |
| Lazy repair called from count_unsynced_events() | ✅ **VERIFIED** | Line 284 (unplanned addition, working tree only) |
| Startup ordering docstring (repair → migrate → reconciler) | ❌ **FAILED** | Present in committed code, **removed in working tree** |
| Per-correction structlog logging with direction | ❌ **FAILED** | Present in committed code, **replaced with simplified `repair_on_startup` in working tree** |
| `_maybe_repair` source-tagged logging | ❌ **FAILED** | Present in committed code, **removed in working tree** |

**Failure details:**

The committed version (commit `ac172c1`, preserved through `f50437d`) contains:
- `run_repair_now()` — public method returning `list[dict]` that forces repair regardless of state
- `_maybe_repair(source)` — unconditional once-per-session repair with source tagging
- Per-correction structlog logging with direction (stale/future) tracking
- Startup ordering docstring

The working tree **removed** all of the above, replacing with:
- `_maybe_run_repair()` — gated by `self._run_repair` flag (only fires if constructor gets `run_repair=True`)
- No `run_repair_now()` at all
- Simplified logging with aggregate count only
- No source tagging
- No startup ordering docstring

**Impact:** All existing production callers use `SqliteEventStore()` with no args → `_run_repair=False` → `_maybe_run_repair()` is a permanent no-op. No path exists to force repair before `migrate()` applies migration 0004, violating the threat model from Plan B (§threat_model: HIGH — migration 0004 fails on duplicate seqs) and Plan C (§threat_model: HIGH — UNIQUE index creation blocked).

**Source claim:** Plan C (007-C-PLAN.md) — "Startup Repair Wiring"

---

## Requirements Cross-Reference

| Requirement | Status | Evidence |
|-------------|--------|----------|
| EVT-03: Event sequence monotonic per stream | ✅ **COVERED** | 4 property invariants verified in hypothesis tests |
| EVT-03: Crash-recovery reconciles gaps | ✅ **COVERED** | `repair_aggregate_seqs()` handles stale/future/empty/deleted scenarios |
| EVT-03: Full requirement (roadmap) | ⚠️ **PARTIAL** | Core functionality verified; startup ordering integration broken |

---

## Test Suite Results

| Test file | Tests | Status |
|-----------|-------|--------|
| `tests/test_seq_crash_recovery.py` | 29 | ✅ All passed (6.79s) |
| `tests/test_migrations.py` | 13 | ✅ All passed (index test includes idx_events_agg_seq) |
| `tests/test_events.py` | 27 | ✅ All passed |
| `tests/test_reconciler.py` | 28 | ✅ All passed |
| `tests/test_sync_mirror.py` | 11 | ✅ All passed |
| **Total** | **108** | **✅ All passed** |

---

## Uncommitted Changes Analysis

`git status` shows `src/state_core/events.py` has uncommitted modifications. The diff reveals a wholesale replacement of the repair-wiring subsystem:

### Removed (present in HEAD):
- `run_repair_now()` method
- `_maybe_repair(source)` with source-tagged logging
- Per-correction structured logging (`repair_seq_correction` with direction)
- Repair trigger/summary/noop logging
- Startup ordering docstring (repair → migrate → reconciler)

### Added (working tree only):
- `_maybe_run_repair()` gated by `self._run_repair` flag
- `_run_repair` instance variable stored from constructor param
- `_maybe_run_repair()` guards on `get_unsynced_events()` and `count_unsynced_events()`
- Simplified `repair_on_startup` and `repair_aggregate_seqs` logging

### Net effect:
The working tree changes **broaden guard placement** (adds repair to get_unsynced_events and count_unsynced_events) but **remove the mechanism to force repair** (run_repair_now). Since all production callers use `SqliteEventStore()` with no arguments, `_maybe_run_repair()` will never execute in the current working tree.

---

## Gap Summary

| # | Severity | Gap | Required By |
|---|----------|-----|-------------|
| G1 | **HIGH** | `run_repair_now()` removed from working tree — no way for daemon startup to force repair before migration 0004 | Plan C (§threat_model), Plan B (§threat_model: HIGH) |
| G2 | **HIGH** | All production callers use `SqliteEventStore()` with no args → `_run_repair=False` → `_maybe_run_repair()` is a permanent no-op | Plan C (lazy repair intent) |
| G3 | **MEDIUM** | Startup ordering docstring removed — `repair()` before `migrate()` before `reconciler()` ordering is undocumented in current code | Plan C (§C.3) |
| G4 | **LOW** | Per-correction structlog logging with direction tracking replaced with simplified aggregate-only logging | Plan C (§C.2) |

### Recommended remediation:
1. **Restore `run_repair_now()`** to `SqliteEventStore` as a public method — it's the only way to force repair before migration
2. **Fix lazy repair gate** — either make `_maybe_run_repair()` unconditional-once-per-session (as in the committed code: `if not self._repair_done`) or change `__init__` default to `run_repair=True`
3. **Restore startup ordering docstring** so callers know the repair → migrate → reconciler sequence
4. **Restore per-correction logging** with direction tracking for observability
5. **Commit or reset** — the working tree changes are a regression; either revert to committed version or fix the issues and commit

---

## Summary

**Core phase goal ACHIEVED:** Fsync discipline is in place, `repair_aggregate_seqs()` correctly handles stale/future/empty/deleted seq scenarios, migration 0004 provides DB-level UNIQUE constraint, and Hypothesis property tests verify all 4 monotonic seq invariants across 100 random crash simulations.

**BUT:** The startup wiring integration (`run_repair_now()`) was present in committed code but **removed in uncommitted working tree changes**. This breaks the repair-before-migrate ordering required for migration 0004 safety.

**Recommendation:** Fix and commit the startup wiring regression, then mark phase complete.
