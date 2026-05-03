---
phase: 010-event-store-verifier-10-000
plan: A
type: auto
autonomous: true
wave: 1
depends_on: []
files_modified:
  - .gitignore
  - .state/fixtures/golden-10k.sqlite
  - .state/fixtures/golden-10k-checksums.json
  - .state/fixtures/regenerate_fixture.py
requirements: [EVT-06]
---

<objective>
Create the golden fixture generation script and produce the 10,000-event fixture database. The fixture is a deterministic SQLite DB with all 34 event types, all 9 aggregate types, and all 3 modes. The regeneration script can be rerun on demand.
</objective>

<threat_model>
ASVS L1 threats for Plan A:
- V12.1 (File Integrity): The golden fixture file could be corrupted or tampered with, causing tests to silently pass on bad data. Mitigation: SHA-256 checksum stored alongside fixture, verified by tests in Plan D.
- V12.3 (Upload Validation): The regeneration script runs locally and reads/writes only to known paths under the project root — no user-controlled input.
- V10 (Malicious Code): The fixture generator script could be modified to produce deterministic-but-wrong data. Mitigation: the cross-checksum triple-assertion in Plan D detects any divergence.
- V7 (Error Handling): Script must fail loudly if any step fails (migrations, append, checksum). No silent corruption.
- V2 (Authentication): N/A — no credentials in fixtures.
</threat_model>

<read_first>
- .planning/milestones/v1/phases/010-event-store-verifier-10-000/010-RESEARCH.md
- src/state_core/events.py (append() API, explicit id_ parameter)
- src/state_core/schema.py (all 34 event types and their data fields)
- .gitignore (line 36 — /.state/ is gitignored; needs exception for fixtures/)
</read_first>

## Tasks

### Task 1: Update .gitignore to allow fixture files in .state/fixtures/

<read_first>.gitignore line 36</read_first>

<action>
Add two lines after `/.state/` to negate the fixtures subdirectory:

```gitignore
# Project
/.state/

# Allow fixtures directory under .state (golden verification DB)
!.state/fixtures/
!.state/fixtures/**
```

This creates the gitignore exception so `.state/fixtures/golden-10k.sqlite` and `.state/fixtures/regenerate_fixture.py` can be tracked by git.
</action>

<acceptance_criteria>
- `git check-ignore .state/fixtures/golden-10k.sqlite` exits with non-zero (not ignored)
- `git check-ignore .state/events.sqlite` exits with zero (still ignored)
</acceptance_criteria>

### Task 2: Create .state/fixtures/ directory and regenerate_fixture.py

<read_first>
- src/state_core/events.py (append method signature, seq enforcement, migration integration)
- src/state_core/schema.py (all 34 event type data models — must match field names exactly)
- src/state_core/migrations.py (migrate function)
- src/state_core/database.py (get_db_path, get_connection)
</read_first>

<action>
Write `.state/fixtures/regenerate_fixture.py` — a standalone Python script with `from freezegun import freeze_time` at the top, wrapping the main execution in `with freeze_time("2026-01-01T00:00:00Z"):`. The script:

1. **Accepts** optional `--output` CLI arg (default: `.state/fixtures/golden-10k.sqlite`).

2. **Creates a temp directory** with `.state/migrations/` copied from the project root.

3. **Sets STATE_DB_PATH** to a temp events.sqlite inside the temp dir.

4. **Calls `migrate()`** to bootstrap all migrations. The entire script MUST be wrapped in `freezegun.freeze_time("2026-01-01T00:00:00Z")` so that `migrations.py`'s `datetime('now')` call for the `_migrations.applied_at` column produces a deterministic value — without this, rerunning the script at a different wall clock produces a non-bit-identical DB file.

5. **Generates 10,000 deterministic events** programmatically, not by hardcoding dicts. Design:
   - Use a deterministic ULID generator: `f"{i:024d}01"` for i=1..10000 (ULID-valid, starts with 0, lexicographic sort order)
   - Use fixed timestamp `"2026-01-01T00:00:00Z"` for all events
   - Distribute events across 9 aggregate types using hardcoded counts:

     | Aggregate | Aggregates | Events/Agg | Total |
     |-----------|-----------|-----------|-------|
     | step      | 100       | 30        | 3000  |
     | slice     | 50        | 30        | 1500  |
     | arc       | 50        | 20        | 1000  |
     | phase     | 50        | 20        | 1000  |
     | concept   | 40        | 25        | 1000  |
     | drill     | 25        | 30        | 750   |
     | decision  | 25        | 30        | 750   |
     | auth      | 20        | 25        | 500   |
     | mode      | 20        | 25        | 500   |

   - For each aggregate, cycle through its valid event types from schema.py
   - Generate data dicts that match the Pydantic schema fields exactly (extra="forbid")
   - Cycle modes through build/teach/kernel
   - Use `store.append()` with explicit `id_` parameter — NEVER use auto-generated ULIDs

6. **Copies the temp DB** to the output path after all appends.

7. **Computes three checksums** and writes `.state/fixtures/golden-10k-checksums.json`:

   a. **db_sha256**: SHA-256 of the entire output SQLite file
   b. **export_jsonl_sha256**: Loads the fixture DB as STATE_DB_PATH, exports all events as JSONL (using same `json.dumps(sort_keys=True, separators=(",", ":"))` as CLI), computes SHA-256 of the full JSONL
   c. **projection_snapshot_sha256**: Loads the fixture DB, runs `Projector.rebuild_all()`, dumps all 3 cache tables (steps, slices, concepts) as sorted JSON, computes SHA-256 of the combined JSON

8. **Prints** "Fixture generated: <path> (10000 events, SHA-256: <hex>)" on success. Exits with code 1 on any error.

The script MUST be idempotent: rerunning it produces the exact same fixture DB (bit-identical).
</action>

<acceptance_criteria>
- `.state/fixtures/regenerate_fixture.py` exists and is executable (`chmod +x`)
- `python3 .state/fixtures/regenerate_fixture.py` exits with code 0
- Output file `.state/fixtures/golden-10k.sqlite` exists and has size > 1MB
- Output file `.state/fixtures/golden-10k-checksums.json` exists and is valid JSON
- Rerunning the script produces bit-identical `golden-10k.sqlite` (deterministic)
</acceptance_criteria>

### Task 3: Generate the golden fixture and checksums

<read_first>.state/fixtures/regenerate_fixture.py</read_first>

<action>
Run `python3 .state/fixtures/regenerate_fixture.py` to produce:
- `.state/fixtures/golden-10k.sqlite`
- `.state/fixtures/golden-10k-checksums.json`

Verify the output:
```bash
python3 -c "
import json
c = json.load(open('.state/fixtures/golden-10k-checksums.json'))
print(f'DB: {c[\"db_sha256\"]}')
print(f'Export JSONL: {c[\"export_jsonl_sha256\"]}')
print(f'Projection: {c[\"projection_snapshot_sha256\"]}')
"
```
</action>

<acceptance_criteria>
- `.state/fixtures/golden-10k.sqlite` file exists (size > 1MB, typically 10-20MB)
- `.state/fixtures/golden-10k-checksums.json` contains exactly 3 keys: `db_sha256`, `export_jsonl_sha256`, `projection_snapshot_sha256`
- All three checksums are 64-char hex strings
- Running `sqlite3 .state/fixtures/golden-10k.sqlite "SELECT COUNT(*) FROM events"` returns 10000
- Running `sqlite3 .state/fixtures/golden-10k.sqlite "SELECT COUNT(DISTINCT mode) FROM events"` returns 3
</acceptance_criteria>

## Verification

1. `git status` shows `.state/fixtures/` files as trackable (not ignored)
2. `python3 .state/fixtures/regenerate_fixture.py` runs cleanly twice with bit-identical output
3. `sqlite3 .state/fixtures/golden-10k.sqlite "SELECT mode, COUNT(*) FROM events GROUP BY mode"` shows all 3 modes present
4. `sqlite3 .state/fixtures/golden-10k.sqlite "SELECT type, COUNT(*) FROM events GROUP BY type"` shows all 34 event types present (check `python3 -c "import re; print(len(set(...))))"` against schema.py)

## Must Haves

- Deterministic ULIDs (no `str(ULID())` calls during fixture generation — all via explicit `id_`)
- Script wrapped in `freezegun.freeze_time("2026-01-01T00:00:00Z")` for deterministic `_migrations.applied_at`
- `.state/fixtures/golden-10k-checksums.json` with exactly 3 checksum entries
- Generator script is idempotent (bit-identical on rerun)
- All 34 event types represented in the fixture
- All 3 modes (build, teach, kernel) represented
- `.state/fixtures/` directory is NOT gitignored after .gitignore update
</must_haves>
