---
wave: 2
depends_on:
  - 007-A-PLAN.md
  - 007-B-PLAN.md
  - 007-C-PLAN.md
files_modified:
  - tests/test_seq_crash_recovery.py
autonomous: false
---

## Plan D: Crash-Simulation Hypothesis Property Tests
**Goal:** Property-test that ANY crash offset + replay produces monotonic sequence.

### Tasks

#### D.1 Add crash-simulation Hypothesis test
<read_first>tests/test_seq_crash_recovery.py (existing tests: test_repair_empty, test_repair_stale_seq, test_repair_future_seq, test_repair_deleted_rows, test_repair_multiple_aggregates)</read_first>
<acceptance_criteria>
`python3 -m pytest tests/test_seq_crash_recovery.py -v -k test_hypothesis_crash_recovery_monotonic` passes
</acceptance_criteria>
<action>
Add Hypothesis property test `test_hypothesis_crash_recovery_monotonic` to `tests/test_seq_crash_recovery.py`:

1. **Monkeypatch crash simulation:**
   - Wrap `aiosqlite.Connection.commit()` to raise exception at a configurable `crash_at_op` offset (e.g., after events INSERT but before aggregate_seq UPSERT)

2. **Hypothesis strategy:**
   - `crash_at_op`: integer between 0 and N (N = number of ops in append flow)
   - Event payloads: text(), binary(), minimal dict
   - Number of prior events per aggregate: integers 0-5
   - Number of aggregates: integers 1-3

3. **Property assertions (post-crash + repair):**
   - `sorted(seq_list) == seq_list` — monotonically increasing per aggregate
   - `events.MAX(seq)` equals `aggregate_seq.seq` per aggregate
   - No duplicate seq values per aggregate: `len(set(seq_list)) == len(seq_list)`

4. **Edge case strategies:**
   - Empty store (no prior events): crash_at_op should be a no-op
   - Single event: crash_at_op=0 prevents any write
   - Single event: crash_at_op past commit succeeds
   - Multiple aggregates: one crashes, others unaffected

5. **Test isolation:**
   - Use `_isolate_db` fixture (tmp_path + STATE_DB_PATH override + copy migrations)
   - Call `await migrate()` to apply all migrations including 0004 before running tests (matches existing test pattern)
</action>
**Estimated effort:** Large
**Dependencies:** Plan B (migration 0004 applied), Plan C (startup repair wiring in place)

<threat_model>
- HIGH: Hypothesis test is trivially passing (no-op). Mitigation: acceptance criteria requires specific test name and property assertions described in action.
- MEDIUM: Test flakiness from Hypothesis strategy. Mitigation: set `max_examples=100` with explicit deadline=None.
</threat_model>

---
