# RESEARCH: Phase 007 — Monotonic Seq Crash-Recovery (P0-9 Regression)

<summary>
Phase 007 hardens the existing write-fsync discipline and formalizes the crash-recovery
routine that detects and repairs gaps/duplicates in `aggregate_seq`. The append()
method already uses `BEGIN IMMEDIATE` + `PRAGMA synchronous=FULL` for write durability,
and `repair_aggregate_seqs()` exists as a recovery routine. What's missing: a UNIQUE
constraint on `(aggregate_id, seq)` in the events table, automatic invocation of the
repair routine on daemon startup, a new migration (0004), and Hypothesis property tests
that simulate crashes at various points in the append flow. The key insight is that the
current single-transaction pattern means crash-recovery is *already correct* for the
common case — the safety net routine needs to be wired in and formally verified.
</summary>

<tech_stack>
- **Python 3.12+** — project target, async/await throughout
- **aiosqlite** — single-thread connection factory, WAL mode, synchronous=NORMAL default
- **Hypothesis >=6.120** — property-based testing for crash-scenario invariants
- **ULID** — `python-ulid` for event IDs (26-char Crockford base32, no auto-increment)
- **structlog** — logging for recovery events and warnings

No new dependencies required. Existing pins suffice.
</tech_stack>

<patterns>
(1) **Single-transaction write discipline** — `BEGIN IMMEDIATE` + `PRAGMA synchronous=FULL`
is already used in both `append()` and `repair_aggregate_seqs()`. This is the correct
pattern: within a single transaction, read seq → insert event → upsert aggregate_seq →
commit. If the commit succeeds, both tables are consistent. If it fails, both roll back.

(2) **Repair-on-startup** — After any crash, run `repair_aggregate_seqs()` before any
consumer reads seq values. Already implemented as a discrete method; needs to be wired
into the daemon startup sequence (or `SqliteEventStore.__init__` with a `run_repair` flag).

(3) **Belt-and-suspenders constraint** — Add `UNIQUE(aggregate_id, seq)` on the events
table via migration 0004. This catches any bug where seq values could duplicate, and
provides a clear `IntegrityError` instead of silent data corruption. Even though the
application-layer append() already prevents this, the DB constraint is cheap insurance.

(4) **Hypothesis property-test for crash resilience** — Not just testing `repair_aggregate_seqs()`
in isolation, but simulating a crash mid-append (by killing the connection or rolling back
mid-transaction) and verifying that after recovery the sequence remains monotonic. This
requires a test helper that can intercept the append flow.
</patterns>

<pitfalls>
- **P0-9 (active):** SQLite event-sequence non-monotonic under crash. The existing
  `repair_aggregate_seqs()` handles the post-crash inconsistency where `aggregate_seq`
  has drifted from `events.MAX(seq)`. But if this method is NOT called on startup,
  the next `append()` will produce a wrong seq, breaking the monotonic guarantee.
  *Mitigation:* Wire `repair_aggregate_seqs()` into daemon startup.

- **P0-9 edge case — WAL checkpoint race:** Between the SQLite commit (WAL flush) and
  the WAL checkpoint writing to the main database, a power loss could create a partially-
  checkpointed state. SQLite WAL recovery handles this correctly at the storage layer,
  but the `repair_aggregate_seqs()` safety net is the application-layer backup.
  *Mitigation:* Keep `synchronous=FULL` during writes (fsync on every commit).

- **synchronous=NORMAL vs. FULL tension:** `database.py` sets `synchronous=NORMAL` on
  every connection. `events.py` overrides to `FULL` inside `append()` and
  `repair_aggregate_seqs()`. This means the `get_connection()` context manager returns
  connections in NORMAL mode — any caller that writes WITHOUT first setting FULL is
  at risk. *Mitigation:* Consider changing the default to `synchronous=FULL` for all
  connections, or document that writers must always set FULL. Phase 007 should make
  this explicit.

- **Missing UNIQUE constraint on (aggregate_id, seq):** The events table PRIMARY KEY
  is `id` (ULID). There is no constraint preventing two events with the same
  `aggregate_id` and `seq`. After a crash+repair+replay, a seq collision is theoretically
  possible. *Mitigation:* Add migration 0004 with a UNIQUE index.

- **Phase 006 overlap:** Phase 006 (startup reconciliation) replays unsent SyncEvents.
  If Phase 007 runs repair AFTER Phase 006 emits events, the seq values could change
  mid-emission. *Mitigation:* Define ordering: Phase 007 repair runs FIRST (before any
  consumer reads seq), then Phase 006 replay. Document the startup sequence.
</pitfalls>

<dependencies>
| Dependency | Version | Why |
|---|---|---|
| aiosqlite | (stdlib bundled) | Database access — no change |
| hypothesis | >=6.120 | Property-test crash scenarios |
| structlog | >=25.1 | Logging repair events |
| python-ulid | (already pinned) | Event ID generation |
</dependencies>

<alternatives>
| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| **Keep synchronous=NORMAL default + override to FULL per write** | Minimal change; existing pattern works | Subtle contract; easy for new writers to forget the override | **Adopt — but document** and consider making FULL the default |
| **Change database.py default to synchronous=FULL** | One-line change; all writers get durability | ~5% throughput hit on reads (synchronous affects only writes in WAL mode) | **Consider** — the throughput impact in WAL mode is negligible for this use case |
| **Use SQLite AUTOINCREMENT** | Built-in gap-free seq | Doesn't match our per-aggregate scheme; ULID+per-aggregate seq is the design | Rejected |
| **Store aggregate_seq as a DB trigger** | Automatic, no application logic | Can't control timing; hard to debug | Rejected — application-level is the pattern |
| **Hypothesis crash simulation via fsynccontrol or signal** | Tests actual crash behavior | Platform-specific; fragile; hard to make deterministic | **MEDIUM confidence** — worth exploring kill-based or PRAGMA corruption simulation |
</alternatives>

<open_questions>
1. **Startup sequence ordering:** Should `repair_aggregate_seqs()` be called inside
   `SqliteEventStore.__init__()`, or should it be a separate daemon-startup step?
   (The former is simpler; the latter allows the daemon to log the repair before any
   event reads.)

2. **Crash simulation approach:** How should Hypothesis simulate a crash mid-append?
   Options: (a) monkeypatch `db.commit()` to raise mid-way, (b) use a write-ahead-log
   corruption helper, (c) inject a sleep + kill scenario via subprocess. The cleanest
   for property-testing is (a) — inject a controlled failure inside the transaction.

3. **Migration 0004 format:** Should the UNIQUE constraint be a standalone index
   (`CREATE UNIQUE INDEX IF NOT EXISTS idx_events_agg_seq ON events(aggregate_id, seq)`)
   or an ALTER TABLE to add a table constraint? SQLite doesn't support adding table
   constraints via ALTER TABLE, so a CREATE UNIQUE INDEX is the only option.

4. **gap vs. gap-free semantics:** EVT-03 says "monotonic" (strictly increasing) not
   "gapless". After a crash+rollback, seq values could have gaps (1, 2, 4). Is this
   acceptable? The opencode SyncEvent contract checks `event.seq !== expected+1` —
   does it tolerate gaps? This needs verification against the opencode SyncEvent
   implementation.

5. **Integration test with Phase 006:** Should there be a combined test that runs
   Phase 007 repair + Phase 006 replay to ensure no interaction bugs?

6. **Existing test file status:** `tests/test_seq_crash_recovery.py` already has
   comprehensive tests for `repair_aggregate_seqs()` and fsync discipline. Are these
   tests passing? They reference `store.append()` which exists, and `store.repair_aggregate_seqs()`
   which also exists. Verify current test status.
</open_questions>
