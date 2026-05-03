---
wave: 1
depends_on: []
files_modified:
  - src/state_core/database.py
autonomous: true
---

## Plan A: Fsync Default — synchronous=FULL as database default
**Goal:** Make `synchronous=FULL` the connection default to ensure all writers get fsync durability.

### Tasks

#### A.1 Change database.py default synchronous mode
<read_first>src/state_core/database.py</read_first>
<acceptance_criteria>
`grep "PRAGMA synchronous" src/state_core/database.py` shows FULL (not NORMAL)
`python3 -m pytest tests/test_seq_crash_recovery.py tests/test_migrations.py -x` passes
</acceptance_criteria>
<action>
Change `synchronous=NORMAL` to `synchronous=FULL` in `src/state_core/database.py` line ~47.
Keep redundant overrides in `events.py` `append()` and `repair_aggregate_seqs()` as defense-in-depth.
Add docstring note explaining the belt-and-suspenders pattern.
</action>
**Estimated effort:** Small
**Dependencies:** None

<threat_model>
- HIGH: Writer gets NORMAL instead of FULL → data loss on crash. Mitigation: change default AND keep per-method overrides.
</threat_model>

---
