# Research: Phase 009 — CLI: `state events tail | replay | export`

## Summary

This phase adds three interactive CLI commands to the existing `events` Typer sub-app: `tail` (polling-based watch for new events), `replay --from <ulid>` (event history playback from an offset), and `export --format jsonl` (bulk export to JSON Lines). All three commands accept `--mode build|teach|kernel` filtering. The core work breaks into (a) new global-read methods on `SqliteEventStore`, (b) a new migration 0005 adding an index on `events.id`, (c) three CLI command functions following the established `asyncio.run()` wrapper pattern, and (d) a `CliRunner`-based test suite.

---

## Tech Stack

| Layer | Technology | Version | Provenance |
|-------|-----------|---------|------------|
| CLI framework | `typer` | `>=0.15` | [VERIFIED: pyproject.toml] |
| Async runtime | `asyncio` (stdlib) | — | [VERIFIED: src/state_cli/main.py uses asyncio.run()] |
| SQLite driver | `aiosqlite` | `>=0.22.1` | [VERIFIED: pyproject.toml] |
| Output formatting | `rich` | `>=13.9` | [VERIFIED: pyproject.toml] |
| Event ID | `python-ulid` | `>=3.0` | [VERIFIED: pyproject.toml] |
| Serialization | `orjson` | `>=3.11.8` | [VERIFIED: pyproject.toml] — available for fast JSONL encoding; fallback to stdlib `json` |
| Testing | `pytest` + `pytest-asyncio` + `typer.testing.CliRunner` | latest | [VERIFIED: pyproject.toml, test patterns] |
| Protocol | `EventStore` (Protocol class) | — | [VERIFIED: src/state_core/events.py:30-48] |

---

## Patterns

### 1. CLI Command Structure (existing pattern, MUST follow)

```
src/state_cli/main.py
  app = typer.Typer(name="state", ...)
  events_app = typer.Typer(name="events", ...)
  app.add_typer(events_app)

  @events_app.command(name="cmd-name")
  def cmd_name(...) -> None:
      try:
          asyncio.run(_do_cmd_name(...))
      except Exception as exc:
          typer.echo(f"Error: {exc}", err=True)
          raise typer.Exit(code=1) from exc

  async def _do_cmd_name(...) -> None:
      from src.state_core.events import SqliteEventStore  # late import
      store = SqliteEventStore()
      ...
```

Key points [VERIFIED: src/state_cli/main.py]:
- Sync command function → `asyncio.run()` → async runner
- Late imports inside async runner to avoid circular imports
- `typer.echo(...)` for stdout, `err=True` for stderr
- `typer.Exit(code=1)` on failure
- No `__name__ == "__main__"` guard — use `typer.testing.CliRunner`

### 2. Event Store Read Pattern

New global-read methods on `SqliteEventStore` (not just per-aggregate `read_stream`):

```python
async def read_events(
    self,
    *,
    from_id: str | None = None,
    to_id: str | None = None,
    mode: str | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Read events with optional ULID offset, mode filter, and limit.
    Ordered by id ASC (lexicographic = chronological for ULIDs).
    Returns event dicts with 'data' deserialized from JSON string.
    """

async def count_events(self, *, mode: str | None = None) -> int:
    """Count events with optional mode filter."""
```

SQL pattern:
```sql
SELECT id, seq, aggregate_type, aggregate_id, type, data, ts, mode
FROM events
WHERE id > ?             -- optional from_id
  AND id < ?             -- optional to_id
  AND mode IN (?, ?)     -- optional mode filter
ORDER BY id ASC
LIMIT ?;                 -- optional limit (0 = no limit)
```

**ULID ordering guarantee [ASSUMED]:** ULIDs encode a 48-bit millisecond timestamp in the first 10 characters (Crockford base32), making string comparison of 26-char ULIDs equivalent to chronological ordering. The `WHERE id > ?` pattern works correctly. [CITED: https://github.com/ulid/spec — "lexicographically sortable"]

### 3. Polling-Based Tail Pattern

For `state events tail`, since this is a direct-SQLite CLI tool (not an HTTP client to the daemon), implement polling:

```python
async def _do_tail(from_id: str | None = None, mode: str | None = None,
                   format: str = "text", follow: bool = True) -> None:
    from src.state_core.events import SqliteEventStore
    store = SqliteEventStore()

    last_id = from_id
    while True:
        events = await store.read_events(from_id=last_id, mode=mode, ...)
        for ev in events:
            _print_event(ev, format)
            last_id = ev["id"]
        if not follow:
            break
        await asyncio.sleep(1)  # poll interval
```

- Graceful shutdown: Ctrl+C → `asyncio.CancelledError` → clean exit
- Default: `--follow / -f` (like `tail -f`)
- `--count / -n 10` for showing last N events before following
- Migration 0005 index ensures the `WHERE id > ? ORDER BY id ASC` query is fast

### 4. JSONL Export Format

JSONL (JSON Lines) — one compact JSON object per line, no trailing comma, no outer array [CITED: https://jsonlines.org/]:

```jsonl
{"id":"01ARZ3NDEKTSV4RRFFQ69G5FAV","seq":1,"aggregate_type":"step","aggregate_id":"step-01","type":"state.step.executed","data":{"changes_summary":"x"},"ts":"2026-01-01T00:00:00Z","mode":"build"}
{"id":"01ARZ3NDEKTSV4RRFFQ69G5FAW","seq":2,...}
```

- Use `orjson.dumps()` for speed if available, otherwise `json.dumps(separators=(',', ':'), sort_keys=True)` for determinism [ASSUMED]
- `export --format jsonl` is explicit; `--output <file>` to write to file instead of stdout
- Default to stdout when `--output` not given

### 5. Mode Filtering on All Commands

Typer option pattern:
```python
@events_app.command(name="replay")
def replay(
    from_id: str = typer.Option(None, "--from", help="ULID offset to start from"),
    mode: str = typer.Option(None, "--mode", help="Filter by mode (build|teach|kernel)"),
    format: str = typer.Option("text", "--format", help="Output format (text|jsonl)"),
    ...
```

Multiple mode values: Accept `--mode` multiple times via `List[str]` with `typer.Option(...)`:
```python
mode: list[str] = typer.Option(None, "--mode", help="Filter by mode"),
```

### 6. Database Migration 0005 — Index on `events.id`

A migration is needed for the `WHERE id > ? ORDER BY id ASC` queries to avoid full table scans [ASSUMED]:
```sql
-- 0005_add_events_id_index: Support ULID-offset queries for CLI tail/replay/export
CREATE INDEX IF NOT EXISTS idx_events_id ON events(id ASC);
```

Notes:
- The existing `idx_events_ts` index on `(ts)` is NOT useful for ULID-offset queries — ULID ordering is independent of the `ts` column (the `id` ULID embeds its own timestamp).
- Without this index, every `WHERE id > ?` query scans the full events table.

---

## Pitfalls and Mitigations

### P1. Circular imports between events.py and main.py
**Risk:** `events.py` imports from `schema.py`, `database.py`, `sync_mirror.py`. `main.py` imports from `events.py`. No cycle exists currently, but adding new imports could introduce one.
**Mitigation:** Follow existing pattern — import `SqliteEventStore` inside async functions, not at module top level [VERIFIED: src/state_cli/main.py:40].

### P2. ULID comparison correctness with SQLite TEXT
**Risk:** SQLite TEXT comparison uses BINARY collation by default. ULIDs must be exactly 26 characters for lexical ordering to be correct. Shorter or longer values would break ordering.
**Verification:** All ULIDs in the events table are generated by `str(ULID())` which always produces 26-char strings. The PK constraints prevent non-ULID values [VERIFIED: src/state_core/events.py:147-148].
**No action needed** — the invariant is enforced by the application layer.

### P3. Large event volumes in memory
**Risk:** `read_all()` without LIMIT could load thousands of events into memory.
**Mitigation:** `export` and `replay` MUST use streaming/iterators where possible:
```python
async def read_events_iter(self, *, from_id=None, ...) -> AsyncIterator[dict]:
    """Yields events one at a time — memory-safe for large volumes."""
```
For `export`, write each event to stdout (or file) as it's received, not after collecting all. For `tail`, by nature it processes one event at a time. For `replay`, add a `--limit` option.

### P4. `tail -f` blocks the terminal
**Risk:** The polling loop runs forever until Ctrl+C. Rusty CLI users expect `tail` to follow by default.
**Mitigation:** 
- Default `--follow` to True for `tail` (like real `tail`), but support `--no-follow` to print current events and exit
- Clean up with `try/except asyncio.CancelledError` on Ctrl+C
- Print nothing on graceful shutdown (just `\n`)

### P5. Typer `--from` is a Python reserved keyword
**Risk:** `from` is a Python keyword, can't use it as a function parameter.
**Mitigation:** Use `from_id` as the Python parameter name, `--from` as the CLI option name:
```python
def replay(from_id: str = typer.Option(None, "--from", ...)):
```
This is explicitly supported by Typer [ASSUMED].

### P6. Typer version quirk with group names
**Risk:** Phase 008-B discovered that `typer>=0.15` returns `DefaultPlaceholder` for `g.name` on registered groups [VERIFIED: 008-B-SUMMARY.md:66].
**Mitigation:** For CliRunner verification of command listing, access via `g.typer_instance.info.name` instead of `g.name`. Not a concern for command implementation, only for tests that introspect the CLI tree.

---

## Dependencies

### New dependencies (none — all in stack already)

Everything needed is already in `pyproject.toml`:
- `typer>=0.15` — CLI framework
- `asyncio` — async runner (stdlib)
- `aiosqlite>=0.22.1` — async SQLite
- `rich>=13.9` — formatted output / tables (optional, could use plain `typer.echo`)
- `orjson>=3.11.8` — fast JSON serialization for JSONL export (optional; fallback to `json`)
- `python-ulid>=3.0` — ULID generation (used by EventStore, not directly needed by CLI)
- `pytest-asyncio>=1.3.0` — for `CliRunner` tests with async commands (dev)

### New SQLite migration: 0005

File: `.state/migrations/0005_add_events_id_index.sql`
```sql
CREATE INDEX IF NOT EXISTS idx_events_id ON events(id ASC);
```

This is needed for performant `WHERE id > ? ORDER BY id ASC` queries.

### New EventStore methods (in `src/state_core/events.py`)

| Method | Purpose | Used by |
|--------|---------|---------|
| `read_events(from_id, to_id, mode, limit)` → `list[dict]` | Global event query with filters | `replay`, `export`, `tail` (initial batch) |
| `read_events_iter(from_id, to_id, mode)` → `AsyncIterator[dict]` | Streaming variant for memory safety | `export` (large volumes) |
| `count_events(mode)` → `int` | Count filtered events | `tail --count` / progress reporting |
| `get_last_events(count, mode)` → `list[dict]` | Last N events (ordered by id DESC) | `tail -n N` |

### New CLI commands (in `src/state_cli/main.py`)

| Command | Options | Async runner |
|---------|---------|-------------|
| `state events tail` | `--from`, `--mode`, `--format` (text\|jsonl), `--follow / -f`, `--count / -n` | `_do_tail()` |
| `state events replay` | `--from`, `--to`, `--mode`, `--format` (text\|jsonl), `--limit` | `_do_replay()` |
| `state events export` | `--from`, `--to`, `--mode`, `--format` (jsonl\|csv), `--output` | `_do_export()` |

---

## Alternatives Considered

### A1. HTTP SSE via daemon vs. direct SQLite polling for `tail`

| Approach | Pros | Cons |
|----------|------|------|
| **Direct SQLite polling (chosen)** | No daemon dependency; consistent with all existing CLI commands; simple implementation; works offline | Polling latency (1s); no real push |
| HTTP SSE from daemon | True push; lower latency; proper SSE event stream format | Requires running daemon; adds HTTP client dependency to CLI; architectural inconsistency with other commands |

**Decision:** Direct SQLite polling. The daemon-SSE approach can be added later as an alternative backend if low-latency tail is needed. The polling approach uses the same `EventStore.read_events()` that replay and export use, maximizing code reuse.

### A2. Output format for `tail`/`replay`

| Format | Pros | Cons |
|--------|------|------|
| **Compact single-line (chosen)** | Easy to read; grep-able; familiar from `tail -f` | Truncated data payload |
| Rich table | Pretty; scrollable in terminal | Too wide for real-time tailing; lines wrap badly |
| JSON lines | Machine-parseable | Not human-readable for watching |

**Decision:** Default to compact single-line format for `tail`/`replay` showing: `id[12:] type aggregate_id mode ts`. Support `--format jsonl` for machine-readable. Consider `--verbose` for full data dump.

Default format example:
```
...ARZ3NDEKTSV4  state.step.executed    step-01    build  2026-01-01T00:00:00Z
...ARZ3NDEKTSV5  state.step.planned     step-01    build  2026-01-01T00:00:01Z
```

### A3. Single `read_events` return vs. cursor-based pagination

| Approach | Pros | Cons |
|----------|------|------|
| **List return (chosen for simplicity)** | Simple; matches existing `get_unsynced_events()` pattern; adequate for moderate volumes | Memory-heavy for 100k+ events |
| AsyncIterator yield | Memory-safe for any volume | More complex; callers must iterate |
| SQLite LIMIT/OFFSET pagination | Memory-safe; standard pattern | Complex cursor management; OFFSET is slow on large tables |

**Decision:** Provide both — `read_events()` returns a list (for small-to-moderate use, matching existing patterns), and `read_events_iter()` yields an `AsyncIterator` (for `export` where volume is unbounded). The `limit` parameter on `read_events()` prevents accidental full-table-loads.

---

## Open Questions

1. **`--format` for `export`:** The requirement says `--format jsonl`. Should we support additional formats like `csv` or `yaml` from the start, or add `jsonl` only and extend later? (Recommend: start with `jsonl` only — simplest, YAGNI.)

2. **`tail` default behavior:** Should `state events tail` default to `--follow` (like Unix `tail -f`), or default to showing current events and exiting (like `tail` without `-f`)? (Recommend: `--follow` by default since that's the valuable use case — watching events in real time. Support `--no-follow` for one-shot.)

3. **Verbose output:** Should `tail`/`replay` include the full event `data` payload by default, or only in a `--verbose` mode? (Recommend: default to summary line; `--verbose` shows full payload via `orjson.dumps()`.)

4. **Event count in `tail -n`:** The last-N-events feature needs `SELECT ... ORDER BY id DESC LIMIT N` then reverse. Should this be a separate CLI flag `--count / -n` or implicit from `--from` being omitted? (Recommend: explicit `--count / -n N` — clearest UX.)

5. **Export file output:** `state events export --output events.jsonl` writes to a file. Should the path be resolved relative to CWD or require an absolute path? (Recommend: resolved relative to CWD, same as all other CLI path operations.)

6. **Daemon integration for tail:** Currently no daemon dependency. If future phases add daemon HTTP endpoints for SSE, the `tail` command could be upgraded to try the daemon first, then fall back to polling. Is this a design concern now or later? (Recommend: later — phase scope stays tight.)

---

## ULID Ordering Verification Plan

Before implementing queries that rely on `id > ?`, verify with a quick test:
1. Insert events with explicit ULIDs at known timestamps
2. Query with `WHERE id > ? ORDER BY id ASC`
3. Assert results are in chronological order

This should pass by ULID spec design [CITED: https://github.com/ulid/spec] but a concrete test eliminates implementation doubt.

---

## RESEARCH COMPLETE
