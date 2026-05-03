---
phase: "010.1"
plan: "B"
type: "gap_closure"
autonomous: false
wave: 1
depends_on: []
files_modified:
  - "src/state_core/events.py"
requirements:
  - "EVT-05"
---

<objective>
Update the `EventStore` Protocol in `src/state_core/events.py` to declare `read_events()`, `read_events_iter()`, `count_events()`, and `get_last_events()` — all of which `SqliteEventStore` already implements but are missing from the Protocol surface. This closes a maintenance risk where new consumers (or mock implementations) cannot rely on the Protocol to discover the full query API.
</objective>

<tasks>

### Task 1: Add query methods to the EventStore Protocol

<read_first>
- `src/state_core/events.py` (full file — pay close attention to the `EventStore` Protocol class at lines 29–47, and each method's signature in `SqliteEventStore`)
- `src/state_core/schema.py` (line 17: `Mode` type — used in method signatures)
</read_first>

<action>
1. Open `src/state_core/events.py` and locate the `EventStore(Protocol)` class (line 29).

2. Add the following four method declarations inside the Protocol body, preserving the same parameter names, types, and default values that `SqliteEventStore` already uses:

   ```python
   async def read_events(
       self,
       *,
       from_id: str | None = None,
       to_id: str | None = None,
       mode: str | None = None,
       limit: int = 0,
   ) -> list[dict[str, Any]]: ...

   async def read_events_iter(
       self,
       *,
       from_id: str | None = None,
       to_id: str | None = None,
       mode: str | None = None,
   ) -> AsyncIterator[dict[str, Any]]: ...

   async def count_events(self, *, mode: str | None = None) -> int: ...

   async def get_last_events(
       self, count: int = 10, *, mode: str | None = None
   ) -> list[dict[str, Any]]: ...
   ```

3. Verify the `AsyncIterator` import is present at the top of the file (it already is at line 15).

4. Run `mypy src/state_core/events.py` to confirm no type errors. `mypy` will check structural subtyping — `SqliteEventStore` must satisfy the expanded Protocol.

5. Run `pytest tests/test_events.py -x` to confirm no regressions.

6. Run `ruff check src/state_core/events.py --fix` to confirm no lint issues.
</action>

<acceptance_criteria>
- `grep -A 10 "class EventStore(Protocol)" src/state_core/events.py` shows all 6 methods (append, read_stream, read_events, read_events_iter, count_events, get_last_events)
- `mypy src/state_core/events.py` exits 0 (structural subtyping check confirms SqliteEventStore satisfies the Protocol)
- `pytest tests/test_events.py -x` passes
- `ruff check src/state_core/events.py` passes
</acceptance_criteria>

</tasks>

<verification>
1. `mypy src/state_core/events.py --strict` exits 0.
2. Full event store test suite passes: `pytest tests/test_events.py -x -v`.
3. Quick structural check: `python3 -c "from src.state_core.events import EventStore, SqliteEventStore; from typing import Protocol; assert issubclass(SqliteEventStore, EventStore) or True; print('ok')"` — this may not work for runtime structural typing but confirms no import errors.
</verification>

<must_haves>
- The Protocol must declare all four query methods with **exactly** the same signature shapes as `SqliteEventStore` (keyword-only args where applicable, same defaults)
- No implementation code added — the Protocol only adds type declarations
- Existing `SqliteEventStore` implementation must not be modified
- No changes to any file outside `src/state_core/events.py`
</must_haves>

<threat_model>
**ASVS L1 coverage:**
- **V5.1 (Input Validation):** Protocol declarations do not change runtime behavior — `SqliteEventStore` already validates/filters in its implementations. No new attack surface.
- **V5.3 (Output Encoding):** The Protocol declares return types (`list[dict]`, `AsyncIterator[dict]`) which already exist in the implementation. No new encoding concerns.
- This is a type-safety improvement only. No secrets, credentials, or runtime logic are added. No escalation risk.
</threat_model>
