# Phase 010 Research: Event Store Verifier (10,000-event golden fixture)

## Summary

This phase builds the final v1 milestone verifier — a Hypothesis property-test and golden-fixture suite that proves **idempotence** (appending events twice — or replaying them — yields the same state) and **determinism** (replaying the exact same event sequence produces bit-identical event rows, projections, and CLI output). It addresses EVT-06 (the last outstanding v1 requirement) and sits on top of all preceding phases (005 SyncEvent, 007 crash recovery, 008 projector, 009 CLI queries). The output is a static golden-fixture SQLite DB with 10,000 events committed to `.state/fixtures/`, a Hypothesis property-test file, and integration tests that assert replays produce identical results.

---

## Tech Stack

| Component | Technology | Version | Status |
|-----------|-----------|---------|--------|
| Property testing | Hypothesis | >=6.120 | [VERIFIED: pyproject.toml] |
| Async test runner | pytest-asyncio | >=1.3.0 | [VERIFIED: pyproject.toml] |
| Event store | SqliteEventStore + aiosqlite | >=0.22.1 | [VERIFIED: src/state_core/events.py] |
| Deterministic JSON | stdlib json (sort_keys, compact) | — | [VERIFIED: events.py L122, projector.py L75] |
| Deterministic timestamps | Fixed epoch "2026-01-01T00:00:00Z" default | — | [VERIFIED: events.py L149] |
| Deterministic ULIDs | ULID() auto-generation (time-based) | python-ulid >=3.0 | [ASSUMED: ULID() uses system clock — but tests use explicit `id_` parameter for determinism] |
| Fixture storage | `.state/fixtures/events-10k.sqlite` | — | [ASSUMED: no existing fixture directory — must create] |
| CLI replay command | `state events replay --from <ulid>` | — | [VERIFIED: 009-B CLI commands] |
| Projector rebuild | `Projector.rebuild_all()` | — | [VERIFIED: projector.py L436] |
| Schema validation | Pydantic `extra="forbid"` | >=2.13.2 | [VERIFIED: schema.py] |

---

## 1. Hypothesis Property Testing Patterns for Event Stores

### Existing Hypothesis Tests (must extend, not duplicate)

| File | Test | What it covers |
|------|------|----------------|
| `test_events.py` | `test_property_append_read_roundtrip` | Any valid input round-trips through append → read_stream (100 examples, sampled event types, modes, dicts) |
| `test_seq_crash_recovery.py` | `test_hypothesis_seq_monotonic_after_append` | Seq is strictly increasing per aggregate for any append pattern |
| `test_seq_crash_recovery.py` | `test_hypothesis_repair_random_mismatch` | After random aggregate_seq corruption, repair restores correctness |
| `test_seq_crash_recovery.py` | `test_hypothesis_crash_recovery_monotonic` | Any crash offset + repair → monotonic seq, no duplicates, MAX(seq)==agg_seq |
| `test_projector.py` | `test_property_rebuild_no_side_effects` | rebuild_all never modifies the events table |

### Key Pattern Observed Across All Existing Tests

Every Hypothesis test uses the same boilerplate:
1. Create an isolated temp DB with `tmp_path / uuid.uuid4().hex`
2. Copy migrations from the project `.state/migrations/` 
3. Run `await migrate()` and create a `SqliteEventStore()`
4. Generate events using the store's `append()` method
5. Assert properties

**For this phase, the new pattern must be:**
1. **Strategy generation** → Generate complete event sequences (not just single events) that exercise all projection handlers
2. **Deterministic replay** → Generate a sequence, store it, then replay it and assert bit-identical results
3. **Golden fixture generation** → Generate a curated 10K-event sequence once, commit to `.state/fixtures/`, and assert replay always matches

**Critical Finding re: ULID determinism** [VERIFIED: events.py L146-L149]:
- `append()` auto-generates ULID via `str(ULID())` when `id_` is `None` — this uses the system clock and is NON-deterministic
- `append()` auto-generates ts via `"2026-01-01T00:00:00Z"` when `ts` is `None` — this IS deterministic
- **Takeaway:** For golden fixtures that must be bit-identical across replays, ALL events must be created with explicit `id_` parameters. The fixture generator script will need to generate deterministic ULIDs (either sequential ULID-like strings or precomputed ULIDs).

### Strategies Needed

```python
# Event type strategy — sample from ALL 28 event types (not just step events)
event_type_strategy = st.sampled_from([
    # 3 arc events
    "state.arc.created", "state.arc.retired", "state.arc.updated",
    # 4 phase events
    "state.phase.planned", "state.phase.started", "state.phase.verified", "state.phase.completed",
    # 4 slice events
    "state.slice.planned", "state.slice.worktree_ready", "state.slice.shipped", "state.slice.reverted",
    # 10 step events
    "state.step.discussed", "state.step.planned", "state.step.executed",
    "state.step.verify_started", "state.step.verify_passed", "state.step.verify_failed",
    "state.step.advanced", "state.step.blocked", "state.step.snapshotted", "state.step.reverted",
    # 5 concept events
    "state.concept.introduced", "state.concept.observed", "state.concept.drilled",
    "state.concept.mastered", "state.concept.reviewed",
    # 3 drill events
    "state.drill.prepared", "state.drill.submitted", "state.drill.graded",
    # 1 mode event
    "state.mode.activated",
    # 2 decision events
    "state.decision.asked", "state.decision.made",
    # 2 auth events
    "state.auth.refreshed", "state.auth.rotated",
])

# Aggregate type → event type mapping (for valid pairings)
# arc events → aggregate_type="arc", phase events → "phase", etc.
AGGREGATE_FOR_EVENT = {
    "state.arc.created": "arc", "state.arc.retired": "arc", "state.arc.updated": "arc",
    "state.phase.planned": "phase", ...  # map all 28
}

# Valid data per event type — must match Pydantic schema fields exactly
# e.g. state.step.executed requires {"changes_summary": str}
data_per_event = st.builds(
    lambda event_type: {
        "state.step.executed": {"changes_summary": "work"},
        "state.step.discussed": {"approach_summary": "explore"},
        # ... field defaults for all 28
    }[event_type],
    event_type=event_type_strategy,
)
```

---

## 2. Generating Event Sequences That Exercise ALL Projection Handlers

### Handler Registry [VERIFIED: projector.py L82-L399]

The projector has exactly **19 handlers** registered:

| Category | Count | Event Types |
|----------|-------|-------------|
| Step | 10 | discussed, planned, executed, verify_started, verify_passed, verify_failed, advanced, blocked, snapshotted, reverted |
| Slice | 4 | planned, worktree_ready, shipped, reverted |
| Concept | 5 | introduced, observed, drilled, mastered, reviewed |

**9 additional event types have NO projection handler** (arc, phase, drill, decision, auth, mode events) — these are silently skipped by the projector. The verifier must still include them to prove they don't cause crashes or side effects.

### Strategy for Exercise Coverage

Two-tier approach:

**Tier 1: Directed sequences** (guaranteed handler coverage)
- For each handler, construct the minimal event sequence that exercises it (e.g., for `state.step.verify_passed`: append `discussed → planned → executed → verify_started → verify_passed`)
- These are `pytest.mark.parametrize` tests, not Hypothesis — they prove individual correctness
- Already exists in `test_projector.py` as per-event-type tests — verify they exist and add any missing ones

**Tier 2: Random sequences** (Hypothesis — finds edge cases)
- Generate random lists of (aggregate_type, aggregate_id, event_type, data) tuples
- Append them in order
- Call `projector.rebuild_all()` and verify:
  - No exceptions raised
  - All cache tables have expected schema (no missing columns)
  - Rows are internally consistent (e.g., step states cycle through valid transitions)
- The existing `test_property_rebuild_no_side_effects` only tests step events — **extend it to all 28 event types**

### Projector Handlers Are All Pure Functions [VERIFIED: projector.py SUMMARY]

The phase 008 summary explicitly states: "No non-deterministic imports (datetime.now, random, uuid, time, secrets) — all handlers are pure functions." This is critical — it means deterministic replay is achievable at the projector level.

---

## 3. Golden Fixture Approach (10K Events)

### Design

**Directory:** `.state/fixtures/events-10k.sqlite`

**Generator script:** A standalone Python script (NOT a test) at, e.g., `scripts/generate_golden_fixture.py` or within the test infrastructure.

**What it stores:**
- A fully-populated `events.sqlite` database with 10,000 events across all 9 aggregate types
- All 28 event types represented (at minimum 1 per type)
- Mix of build/teach/kernel modes
- Multiple aggregates per type (at least 3 per aggregate type with cached projections)
- Interleaved event sequences (events for different aggregates interleaved by ULID order)
- `aggregate_seq` table correctly populated
- All 5 migrations applied

**Determinism requirements:**
- ALL ULIDs must be deterministic (pre-computed or sequential)
- ALL timestamps must use the fixed epoch `"2026-01-01T00:00:00Z"` (or a deterministic sequence)
- ALL JSON serialization uses `sort_keys=True, separators=(",", ":")`
- A SHA-256 checksum of the entire DB must be recorded alongside the fixture

**Scheme for deterministic ULIDs:** [ASSUMED]
```python
# Since ULIDs are 26-char Crockford base32, use sequential ULID-like IDs:
# "00000000000000000000000001" through "000000000000000000002710"
# Or use the python-ulid library with a fixed timestamp:
# ULID.from_timestamp(datetime(2026, 1, 1)) with incremented random component
# SIMPLEST: just pass explicit id_ strings that sort lexicographically
```

**Script structure:**
```python
# scripts/fixture_generator.py
import asyncio
import hashlib
from pathlib import Path
from src.state_core.events import SqliteEventStore

# Precomputed deterministic events (this is the fixture definition)
EVENTS: list[dict] = [...]  # 10,000 event dicts with deterministic ULIDs

async def generate(fixture_path: Path) -> str:
    """Generate fixture DB, return SHA-256 checksum."""
    # Set STATE_DB_PATH, run migrate(), append all events
    ...
    db_bytes = fixture_path.read_bytes()
    return hashlib.sha256(db_bytes).hexdigest()
```

**What the golden fixture assertion tests:**
1. Load the fixture DB
2. Run `state events export --format jsonl` → get JSONL output
3. Run `state events replay --from <first_ulid>` → get all events
4. Run `Projector.rebuild_all()` → get projections
5. Compare against the **recorded expected output** (stored alongside the fixture)
6. SHA-256 of the fixture DB must match the recorded checksum (proves DB is unchanged)

### 10,000 Event Distribution

| Aggregate Type | Events | Notes |
|---------------|--------|-------|
| step | ~3,000 | Full lifecycle sequences across 100+ step aggregates |
| slice | ~1,500 | Lifecycle sequences across 50 slice aggregates |
| arc | ~1,000 | Created/updated/retired cycles |
| phase | ~1,000 | Planned/started/verified/completed cycles |
| concept | ~1,000 | Introduced/observed/drilled/mastered/reviewed cycles |
| drill | ~750 | Prepared/submitted/graded cycles |
| decision | ~750 | Asked/made cycles |
| auth | ~500 | Refreshed/rotated cycles |
| mode | ~500 | Activated events |

---

## 4. Idempotency Verification Strategy

### What "Idempotency" Means for This Phase

Three distinct idempotency properties must be verified:

**Property 1 — Append idempotency:**
Appending the exact same event twice (with same ULID, seq, data) produces exactly one row in the DB (not a duplicate). This is enforced by the UNIQUE(aggregate_id, seq) index [VERIFIED: migration 0004].

**Hypothesis property test:**
```python
@given(event=valid_event_strategy())
async def test_append_same_event_twice_is_idempotent(event):
    """Same (aggregate_id, seq) pair cannot be inserted twice."""
    id1 = await store.append(..., id_=fixed_ulid, ...)
    with pytest.raises(aiosqlite.IntegrityError):
        await store.append(..., id_=fixed_ulid, ...)  # same ULID, same seq
    # BUT: same data with different ULID → seq will be different (seq increments)
```

**Property 2 — Rebuild idempotency:**
Running `Projector.rebuild_all()` twice produces identical cache tables. Already tested in `test_projector.py::TestRebuildIdempotency::test_rebuild_idempotent`. Extend to all 28 event types.

**Property 3 — Repair idempotency:**
Running `repair_aggregate_seqs()` twice (when already consistent) is a no-op. Already tested in `test_seq_crash_recovery.py::test_repair_twice_idempotent`.

### New Property Tests Needed

| Property | Test | Approach |
|----------|------|----------|
| P1a | Same-event re-append with explicit same ULID | Assert IntegrityError |
| P1b | Same-event data with different ULID | Assert seq increments, no data corruption |
| P2 | rebuild_all() × 2 produces identical cache tables | Extend existing test to 28 event types |
| P3 | repair_aggregate_seqs() × 2 no-op | Already covered |
| P4 | CLI commands (tail/replay/export) do not modify events table | Already in test_cli.py |
| P5 | replay() through EventStore returns same results as direct query | New: compare CLI output vs direct API |

---

## 5. Determinism Verification Strategy

### What "Determinism" Means for EVT-06

**EVT-06 states:** "Event payloads are deterministic — no datetime.now() / randomness in handlers; replay is bit-identical."

This requires verifying **four layers** of determinism:

### Layer 1: Schema Construction [VERIFIED: test_schema.py::TestDeterminism]
- `test_event_construction_is_deterministic`: Same inputs → identical `.model_dump_json()` output
- `test_no_random_defaults_in_data_models`: Data model defaults have no randomness

### Layer 2: Append Serialization [VERIFIED: test_events.py::TestDeterminismAndMode]
- `test_deterministic_json_serialization`: Events.stored JSON uses `sort_keys=True, separators=(",", ":")`
- `test_append_default_timestamp`: Default ts is fixed epoch `"2026-01-01T00:00:00Z"`
- `test_id_and_ts_injected_values_stored`: Explicit id/ts round-trip correctly

### Layer 3: Projector Handlers [VERIFIED: projector.py SUMMARY]
- All 19 handlers are pure functions (no datetime.now, random, uuid, time, secrets)
- Frontmatter serialization uses `json.dumps(sort_keys=True, separators=(",", ":"))`
- `_merge_frontmatter` is deterministic for same input

### Layer 4: End-to-End Replay Determinism (NEW — this phase)
The most critical new test. The golden fixture proves:

```python
async def test_golden_fixture_replay_determinism():
    """Replaying all events from the golden fixture produces bit-identical output."""
    # 1. Load golden fixture at STATE_DB_PATH
    # 2. Export events to JSONL → checksum_A
    # 3. Run Projector.rebuild_all() → checksum_B (cache table projections)
    # 4. Reset fixture DB to clean state (re-copy from source)
    # 5. Repeat steps 2-3 → checksum_A2, checksum_B2
    # 6. Assert checksum_A == checksum_A2 and checksum_B == checksum_B2
```

### Determinism Source Analysis

| Source of Non-determinism | Where | Mitigation |
|--------------------------|-------|------------|
| `ULID()` auto-generation | `events.py L147` | Always pass explicit `id_` in fixture and tests |
| `datetime.now()` | None found in src/ | [VERIFIED: grep returns 0 matches in src/] |
| `random.*` | None found in src/ | [VERIFIED: grep returns 0 matches in src/] |
| `time.*` | None found in src/ | [VERIFIED: grep returns 0 matches in src/] |
| `uuid.*` | Only in test files | Acceptable — test isolation uses uuid for temp dirs |
| `json.dumps` without sort_keys | `projector.py` | Uses `sort_keys=True, separators=(",", ":")` [VERIFIED] |
| `json.dumps` without sort_keys | `events.py` | Uses `sort_keys=True, separators=(",", ":")` [VERIFIED] |
| `datetime('now')` in migrations | `migrations.py L87` | Only for `applied_at` metadata — does NOT affect event payloads |

---

## 6. Existing Hypothesis Tests — Extension Plan

### Files That Need New or Extended Tests

| File | Existing | Gap | Plan |
|------|----------|-----|------|
| `test_events.py` | 1 Hypothesis test (append roundtrip) | Only step events, limited data strategies | Add property tests for ALL 28 event types, add same-event idempotency test |
| `test_seq_crash_recovery.py` | 3 Hypothesis tests (seq monotonic, repair mismatch, crash recovery) | Crash-recovery combined with projection rebuild not tested | Add Hypothesis test: crash → repair → rebuild_all → projectors match |
| `test_projector.py` | 1 Hypothesis test (rebuild no side effects) | Only step events, small scale (0-10 events) | Extend to all aggregate types, larger sequences |
| NEW file | — | Golden fixture, end-to-end determinism, mixed-mode sequences | `tests/test_fixture_verifier.py` |

### Specific Extension Details

**1. Extend `test_events.py::test_property_append_read_roundtrip`:**
- Current: only `sampled_from(["arc", "phase", "slice", "step", "concept", "drill", "decision", "auth", "mode"])`
- Add: per-event-type data strategies that match Pydantic schema fields exactly
- Add: property that reading back gives bit-identical data (modulo seq/id which are assigned by store)

**2. New Hypothesis tests in `test_projector.py`:**
- `test_property_all_28_event_types_rebuild`: Generate sequences containing ALL 28 event types, verify rebuild_all() produces consistent projections
- `test_property_frontmatter_determinism`: Same event sequence → same frontmatter JSON in cache tables

**3. New Hypothesis tests for CLI determinism:**
- `test_property_cli_output_determinism`: Same events in two independent DBs → identical CLI export output

**Important pattern note:** All existing Hypothesis tests use `suppress_health_check=[HealthCheck.function_scoped_fixture]` because they create their own DB inside the test function. The golden fixture test should use Module-scoped fixtures or store the fixture path in `STATE_DB_PATH` env var.

---

## 7. Dependencies and Integration Points

### Phase Dependencies

| Phase | Integration | What This Phase Consumes |
|-------|-------------|-------------------------|
| 005 — SyncEvent mirror | `SyncEventMirror.emit()` | The verifier must test that mirror emission is deterministic (same event → same HTTP body). Already tested in `test_sync_mirror.py::TestEmissionDeterminism` — verify it exists |
| 007 — Crash recovery | `repair_aggregate_seqs()` | The golden fixture must survive a repair cycle — prove that repair on a consistent DB is a no-op |
| 008 — Projector | `Projector.rebuild_all()`, `Projector.apply_event()` | Golden fixture replay must rebuild projections and get identical results |
| 009 — CLI queries | `read_events()`, `read_events_iter()`, `get_last_events()` | CLI export/replay must produce deterministic output from the golden fixture |

### New Dependencies

| Dependency | Purpose | Notes |
|-----------|---------|-------|
| `freezegun` | Already in dev deps [VERIFIED: pyproject.toml] | For deterministic timestamp injection in Hypothesis strategies |
| No new pip dependencies needed | — | All test infrastructure exists |

### Integration Test Flow

```
Golden fixture DB (.state/fixtures/events-10k.sqlite)
    ↓ LOAD (set STATE_DB_PATH)
    ↓
1. Direct API verifier:
   - count_events() == 10000
   - read_events_iter() yields 10000 rows
   - Projector.rebuild_all() → 10000 events processed
   
2. CLI verifier:
   - `state events export --format jsonl` → 10000 lines, compare checksum
   - `state events replay --from <first_ulid>` → 9999 events
   - `state events tail --no-follow --count 10` → 10 events

3. Determinism verifier:
   - Re-export → same checksum
   - Re-rebuild → same cache tables
   
4. Crash-recovery verifier:
   - Copy fixture to temp
   - Run repair_aggregate_seqs() → no repairs needed
   
5. Mode-filter verifier:
   - Count events per mode: build + teach + kernel == 10000
```

### Files Affected

| File | Action | Notes |
|------|--------|-------|
| `.state/fixtures/events-10k.sqlite` | **CREATE** | Binary SQLite file (git-lfs or committed directly if small enough) |
| `.state/fixtures/events-10k.sha256` | **CREATE** | Checksum for integrity verification |
| `scripts/generate_golden_fixture.py` | **CREATE** | Generator script for the 10K fixture |
| `tests/test_fixture_verifier.py` | **CREATE** | New test file — golden fixture assertions, end-to-end determinism |
| `tests/test_events.py` | **MODIFY** | Add property tests for all 28 event types, deterministic strategies |
| `tests/test_projector.py` | **MODIFY** | Extend Hypothesis tests to cover all aggregate types |

---

## Pitfalls

### 1. ULID auto-generation is NOT deterministic
[VERIFIED: events.py L147] — `str(ULID())` uses system clock. For golden fixtures, every event must have an explicit `id_` parameter. Failure to do this will cause bit-identical replay to fail.

### 2. Hypothesis timeouts with 10K operations
The golden fixture test that loads 10K events will be SLOW if each event goes through the full append path (BEGIN IMMEDIATE, seq SELECT, INSERT, aggregate_seq UPDATE, COMMIT). Mitigation: use `freezegun` for timestamp control AND use batch appends or direct SQL INSERT when building the fixture generator (bypassing the append() method's per-event overhead). The verifier test itself can use the fast path: load the pre-built fixture DB directly.

### 3. Migration state in golden fixture
The golden fixture DB must have ALL migrations applied. The fixture generator must run `migrate()` before inserting any events. The verifier must NOT call `migrate()` on the fixture (it would try to re-apply migrations that are already recorded in `_migrations` table, which is harmless due to idempotency, but could add noise to checksums).

### 4. Mode filter for CLI tests
CLI tests currently suppress structlog via `make_filtering_bound_logger(logging.CRITICAL)` [VERIFIED: test_cli.py L27]. The golden fixture verifier must do the same to avoid structlog output polluting CLI result comparison.

### 5. The projector reads ALL events at once
[VERIFIED: projector.py L462] — `cursor.fetchall()` in `rebuild_all()`. For 10K events at ~2KB each ≈ ~20MB. Acceptable but worth noting — the verifier should confirm this works without memory issues.

### 6. JSON serialization must match exactly
The `_merge_frontmatter` in `projector.py` uses `json.dumps(frontmatter, sort_keys=True, separators=(",", ":"))` — note the separators have NO spaces (unlike the default `(", ", ": ")`). Any test that compares JSON strings must use identical serialization settings, or compare parsed objects instead of raw strings.

---

## Alternatives Considered

| Approach | Tradeoffs | Verdict |
|----------|-----------|---------|
| **Hypothesis-only verification** | Pure property testing without a fixed fixture — catches more edge cases, but can't prove bit-identical behavior across runs since Hypothesis generates different inputs each time | **Rejected** — we need both approaches |
| **Golden fixture + Hypothesis** | Best of both: the fixture proves static replay determinism, Hypothesis proves dynamic correctness under random inputs | **Selected** |
| **Store fixture as JSONL** | Easier to diff in git, but loses SQL schema (indexes, aggregate_seq, sync flags) | **Rejected** — must include full DB state |
| **100K events instead of 10K** | More thorough, but slower to generate and test | **Rejected** — 10K is the v1 target; can increase in later milestones |
| **Committed fixture checksum** | Store SHA-256 alongside fixture, fail CI if checksum changes unexpectedly | **Selected** |

---

## Open Questions

1. **Where should the golden fixture generator live?** `scripts/generate_golden_fixture.py` or a pytest fixture with `scope="session"` that generates on first run? A standalone script is simpler but a session-scoped fixture auto-generates during test runs.

2. **Should the fixture be committed to git?** At ~20MB, a 10K-event SQLite DB is questionable for git. Two options:
   - Commit with git-lfs (preferred if repo already uses git-lfs)
   - Generate on first `pytest` run (auto-detected by fixture, cached in `.state/fixtures/`)

3. **What is the exact set of "expected output" snapshots?** We need to define what we compare against. Options:
   - SHA-256 of entire fixture DB
   - SHA-256 of `state events export` output
   - JSON snapshot of all cache table rows after `rebuild_all()`
   - All three (recommended)

4. **How many event types are actually "28"?** The schema defines exactly 28 typed events [VERIFIED: schema.py]: 3 arc + 4 phase + 4 slice + 10 step + 5 concept + 3 drill + 1 mode + 2 decision + 2 auth = 34 (not 28). Need to clarify the exact count. For the phase 010 scope, we should cover ALL typed events in schema.py, regardless of the count.

5. **What about the `migrations.py::datetime('now')` call?** Line 87 uses `datetime('now')` for the `applied_at` column in the `_migrations` meta-table. This affects the `_migrations` table content but does NOT affect event payloads, seq values, or projections. The golden fixture checksum should either be computed EXCLUDING the `_migrations` table, or the fixture must be generated with a frozen clock.

---

## RESEARCH COMPLETE
