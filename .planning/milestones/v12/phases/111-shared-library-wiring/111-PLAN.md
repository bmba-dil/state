---
phase: 111
phase_name: shared-library-wiring
wave: 1
depends_on: ["106"]
files_modified:
  - src/state_build/mcp.py
requirements_addressed: ["infrastructure"]
autonomous: true
---

## Plan 01: Wire state_core Imports into MCP Server

**Goal:** Tool impls import and call `state_core` helpers; no duplicate auth/provider logic anywhere in state_build.

### Tasks

#### 01.1 Add state_core import block to mcp.py
**Acceptance:** `grep "from state_core" src/state_build/mcp.py` returns 3 matches for auth, events, scheduler
**Estimated effort:** Small
**Dependencies:** Phase 106 (server scaffold exists)

<action>
Add a shared-library import block at the top of `src/state_build/mcp.py`, after the `mcp`/`pydantic` imports:

```python
# Shared library wiring (Phase 111) — single import surface for all tools
from state_core.auth import load_credentials as _load_credentials  # noqa: F401
from state_core.events import SqliteEventStore as _SqliteEventStore  # noqa: F401
from state_core.scheduler import DAGScheduler as _DAGScheduler  # noqa: F401
```

Each import is underscore-prefixed to signal "wired at the skeleton level, fully utilized in Tier 3a". The `# noqa: F401` suppresses the unused-import lint until real calls land.

Consumed by: every tool in `state_build.mcp` (single import surface), Phase v14 (real StepMachine calls), Phase v15 (real event store calls).
</action>

<read_first>
- src/state_build/mcp.py
- src/state_core/__init__.py (verify public exports exist)
</read_first>

<acceptance_criteria>
- `grep "from state_core.auth import" src/state_build/mcp.py` returns 1 match
- `grep "from state_core.events import" src/state_build/mcp.py` returns 1 match
- `grep "from state_core.scheduler import" src/state_build/mcp.py` returns 1 match
- `ruff check src/state_build/mcp.py` passes (F401 suppressed via noqa)
- `python3 -c "from state_build.mcp import mcp; print('imports OK')"` exits 0
</acceptance_criteria>

#### 01.2 Wire dag_status to use real DAGScheduler
**Acceptance:** `dag_status()` response includes "scheduler_ready" and concurrency cap
**Estimated effort:** Small
**Dependencies:** 01.1

<action>
Update `dag_status()` in `src/state_build/mcp.py` to instantiate a `_DAGScheduler` and report its state:

```python
@mcp.tool()
def dag_status() -> SkeletonResponse:
    """Query build-mode DAG scheduler state. Returns node and edge counts."""
    scheduler = _DAGScheduler()
    return SkeletonResponse(
        tool="dag_status",
        status=f"scheduler_ready (cap={scheduler.concurrency_cap})",
    )
```

This proves the import chain works end-to-end: mcp.py → state_core.scheduler → DAGScheduler. The `concurrency_cap` property (default: 4) is the simplest non-trivial attribute to query.

Consumed by: Phase v14 (populates DAG with real arc/phase/slice/step nodes), opencode TUI (DAG viewer in v10).
</action>

<read_first>
- src/state_build/mcp.py
- src/state_core/scheduler.py (DAGScheduler.__init__ signature)
</read_first>

<acceptance_criteria>
- `grep "_DAGScheduler()" src/state_build/mcp.py` returns 1 match
- `grep "scheduler_ready" src/state_build/mcp.py` returns 1 match
- `python3 -c "from state_build.mcp import dag_status; r = dag_status(); assert 'scheduler_ready' in r.status; assert 'cap=4' in r.status"` exits 0
- `ruff check` clean
</acceptance_criteria>

#### 01.3 Verify no duplicate auth/provider logic
**Acceptance:** No direct `google-auth`, `litellm`, or `anthropic` imports in `state_build/`
**Estimated effort:** Small
**Dependencies:** 01.1
**Details:**
- Audit `state_build/` for any direct auth/provider imports
- All auth/provider access must flow through `state_core` imports
- This is already true since `mcp.py` was the only file with new imports and it uses `state_core`

<action>
Verify with grep that `state_build/` directory contains no direct auth/provider library imports:

```bash
grep -r "google.auth\|litellm\|anthropic" src/state_build/ && echo "LEAK" || echo "CLEAN"
```

Consumed by: import-graph lint (Phase 102), SECURITY.md audit.
</action>

<read_first>
- src/state_build/mcp.py
</read_first>

<acceptance_criteria>
- `grep -r "google.auth\|litellm\|anthropic" src/state_build/` returns 0 matches
- All auth/provider access routed through `state_core.*` imports
</acceptance_criteria>

### Integration Notes
- The underscore-prefixed import pattern (`_DAGScheduler`, `_SqliteEventStore`) is deliberate: signals "skeleton-level wiring, real usage in Tier 3a"
- Phase v14 (Build Kernel) will replace `_ = ctx` stubs with real `ctx.report_progress()` calls that report actual step progress
- Phase v15 (Build Core Commands) will replace `SkeletonResponse` returns with real data from the event store
