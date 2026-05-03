---
phase: 001
plan: B
type: auto
autonomous: true
wave: 2
depends_on:
  - phase-001-plan-A
files_modified:
  - src/state_core/__init__.py
  - src/state_core/schema.py
  - src/state_core/events.py
  - src/state_core/scheduler.py
  - src/state_core/worktree.py
  - src/state_core/snapshot.py
  - src/state_core/auth/__init__.py
  - src/state_core/providers/__init__.py
  - src/state_build/__init__.py
  - src/state_build/kernel.py
  - src/state_build/mcp.py
  - src/state_teach/__init__.py
  - src/state_teach/kernel.py
  - src/state_teach/mcp.py
  - src/state_daemon/__init__.py
  - src/state_daemon/server.py
  - src/state_worker/__init__.py
  - src/state_worker/main.py
  - src/state_cli/__init__.py
  - src/state_cli/main.py
  - tests/__init__.py
  - pyproject.toml
requirements: []  # foundational phase, no REQ-IDs assigned
---

<objective>
Create the complete Python package skeleton and directory layout per ARCHITECTURE.md §1.3. This includes `state_core` (shared kernel), `state_build`, `state_teach`, `state_daemon`, `state_worker`, and `state_cli` packages with module stubs, plus the `tests/` directory. The layout must implement the physical mode-silo constraint — `state_build` and `state_teach` are separate packages that must never import each other.
</objective>

<read_first>
  - /Users/tmac/Projects/state/pyproject.toml (created by Plan A)
  - /Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md (§1.3 for directory layout, §7 for mode enforcement)
  - /Users/tmac/Projects/state/.planning/research/STACK.md (lines 80–110 for library layout)
  - /Users/tmac/Projects/state/CLAUDE.md (Python conventions: use `python3`, mode isolation is physical)
</read_first>

---

### Task 1: Create `state_core/` package — shared kernel

<action>
Create directory hierarchy and module stubs under `src/state_core/`:

```
src/state_core/
├── __init__.py            # Package marker + version export
├── schema.py              # Pydantic models for Arc/Phase/Slice/Step/Concept
├── events.py              # SQLite + SyncEvent mirror (docstring stub)
├── scheduler.py           # Pure-Python DAG scheduler (docstring stub)
├── worktree.py            # opencode-preferred / pygit2-fallback abstraction
├── snapshot.py            # Step + Slice tier snapshot glue
├── auth/
│   ├── __init__.py        # AuthMethod protocol exports
│   ├── base.py            # AuthMethod Protocol class stub
│   └── store.py           # auth.json I/O + filelock stub
└── providers/
    ├── __init__.py        # Provider router stub
    └── router.py          # litellm wrapper + direct SDK escape hatch stub
```

Each module file must contain:
- A docstring describing the module's purpose (1-3 sentences)
- A class or function stub where the module clearly needs one (based on ARCHITECTURE.md)
- `from __future__ import annotations` at the top of every module
- Type annotations on all function signatures (even stubs)

**`src/state_core/__init__.py`** content:
```python
"""state — agentic state-machine workflow engine for opencode."""
from __future__ import annotations

__version__ = "0.1.0"
```

**`src/state_core/schema.py`** content (pydantic foundations):
```python
"""Pydantic models for Arc/Phase/Slice/Step/Concept event types."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Literal
import ulid  # NOTE: ulid is a Python stdlib module? actually use a string type alias for now

# Placeholder: concrete schemas will be added in Phase 002
class EventEnvelope(BaseModel):
    """Base event envelope with ULID id and ISO8601 timestamp."""
    model_config = ConfigDict(extra="forbid")
    id: str = ""
    type: str = ""
    ts: str = ""
    data: dict = {}
```

**`src/state_core/events.py`** content:
```python
"""Event store: SQLite writer + SyncEvent mirror for dual-write architecture."""
from __future__ import annotations

from typing import Protocol, AsyncIterator

class EventStore(Protocol):
    """Protocol for writing and reading domain events."""
    async def append(self, aggregate_type: str, aggregate_id: str, event_type: str, data: dict) -> str: ...
    async def read_stream(self, aggregate_id: str, after_seq: int = 0) -> AsyncIterator[dict]: ...
```

**`src/state_core/scheduler.py`** content:
```python
"""Pure-Python DAG scheduler. No networkx dependency."""
from __future__ import annotations

from typing import Any

class DAGScheduler:
    """Reactive DAG scheduler that computes unblocked Steps on state change."""
    async def tick(self, arc_id: str) -> list[str]:
        """Return all Step IDs ready for concurrent dispatch."""
        ...
```

**`src/state_core/worktree.py`** content:
```python
"""Worktree abstraction: opencode-preferred, pygit2 fallback."""
from __future__ import annotations

from typing import Protocol

class WorktreeService(Protocol):
    """Create/list/remove worktrees, preferring opencode HTTP API."""
    async def create(self, name: str, branch: str) -> str: ...
    async def remove(self, name: str) -> None: ...
```

**`src/state_core/snapshot.py`** content:
```python
"""Step + Slice tier snapshot glue for fine-grained revert."""
from __future__ import annotations

class SnapshotManager:
    """Manages snapshots at Step and Slice boundaries."""
    async def track(self, tier: str, ref: str) -> str: ...
    async def revert(self, snapshot_id: str) -> None: ...
```

**`src/state_core/auth/__init__.py`**:
```python
"""Auth layer: 5-method credential management."""
from __future__ import annotations
```

**`src/state_core/auth/base.py`**:
```python
"""AuthMethod protocol + Credential container."""
from __future__ import annotations

from typing import Protocol
from pydantic import BaseModel, ConfigDict

class Credential(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = ""
    access: str = ""
    expires: float = 0.0

class AuthMethod(Protocol):
    async def login(self) -> Credential: ...
    async def refresh(self, cred: Credential) -> Credential: ...
    def is_expired(self, cred: Credential, now: float) -> bool: ...
```

**`src/state_core/auth/store.py`**:
```python
"""auth.json I/O with filelock, chmod 0600 enforcement."""
from __future__ import annotations
```

**`src/state_core/providers/__init__.py`**:
```python
"""Provider routing: litellm default, Anthropic SDK escape hatch."""
from __future__ import annotations
```

**`src/state_core/providers/router.py`**:
```python
"""ProviderRouter: resolves model calls to litellm or direct SDK."""
from __future__ import annotations

class ProviderRouter:
    """Routes provider calls — litellm default, Anthropic SDK for extended thinking."""
    async def route(self, model_spec: dict) -> object: ...
```
</action>

<acceptance_criteria>
  - `src/state_core/__init__.py` exists with `__version__ = "0.1.0"`.
  - `src/state_core/schema.py` exists with `EventEnvelope` pydantic model using `extra="forbid"`.
  - `src/state_core/events.py` exists with `EventStore` protocol class.
  - `src/state_core/scheduler.py` exists with `DAGScheduler` class.
  - `src/state_core/auth/__init__.py` and `src/state_core/auth/base.py` exist.
  - `src/state_core/providers/__init__.py` and `src/state_core/providers/router.py` exist.
  - Every `.py` file starts with `from __future__ import annotations`.
  - `python3 -c "from src.state_core import __version__; print(__version__)"` prints `0.1.0`.
  - `python3 -c "from src.state_core.schema import EventEnvelope; e = EventEnvelope(); print(e.model_config.get('extra'))"` prints `forbid`.
</acceptance_criteria>

---

### Task 2: Create build-mode and teach-mode package skeletons (physical silos)

<action>
Create directory hierarchies for the two mode-siloed packages:

**`src/state_build/` — build-mode kernel:**
```
src/state_build/
├── __init__.py        # Build-mode marker — DO NOT import state_teach
├── kernel.py          # Step state machine stub
├── mcp.py             # state-build MCP server entry stub
├── commands/          # GSD command ports (empty, for Phase 015+)
└── verifiers/         # Goal-backward + rollup verifiers (empty, for Phase 014+)
```

**`src/state_teach/` — teach-mode kernel:**
```
src/state_teach/
├── __init__.py        # Teach-mode marker — DO NOT import state_build
├── kernel.py          # Kolb-cycle state machine stub
├── mcp.py             # state-teach MCP server entry stub
├── concepts.py        # Concept graph operations stub
├── drill.py           # Drill engine stub
├── mental_model.py    # Event-sourced projection stub
└── personalities/     # AOL personality loaders (empty, for Phase 021+)
```

**`src/state_build/__init__.py`:**
```python
"""Build-mode kernel — Step state machine, GSD command ports, verifiers.
   PHYSICAL SILO: this package must NEVER import state_teach."""
from __future__ import annotations
```

**`src/state_teach/__init__.py`:**
```python
"""Teach-mode kernel — Kolb-cycle, concept graph, drill engine, mental model.
   PHYSICAL SILO: this package must NEVER import state_build."""
from __future__ import annotations
```

**`src/state_build/kernel.py`:**
```python
"""Step state machine: idle→discussing→planning→executing→verifying→done."""
from __future__ import annotations

from typing import Literal

StepState = Literal["idle", "discussing", "planning", "executing", "verifying", "done", "blocked", "abandoned"]

class StepMachine:
    """Finite state machine for a single Step's lifecycle."""
    state: StepState = "idle"
    async def on_event(self, event_type: str, data: dict) -> None: ...
```

**`src/state_teach/kernel.py`:**
```python
"""Kolb-cycle state machine: CE→RO→AC→AE for concept teaching."""
from __future__ import annotations

from typing import Literal

KolbStage = Literal["CE", "RO", "AC", "AE", "MASTERED", "REVIEW"]

class KolbMachine:
    """Finite state machine for the Kolb experiential learning cycle."""
    stage: KolbStage = "CE"
    async def on_event(self, event_type: str, data: dict) -> None: ...
```

For all other stub files, create minimal `__init__.py` files with docstrings and `from __future__ import annotations`.
</action>

<acceptance_criteria>
  - `src/state_build/__init__.py` exists with docstring mentioning physical silo constraint.
  - `src/state_teach/__init__.py` exists with docstring mentioning physical silo constraint.
  - `src/state_build/kernel.py` exists with `StepMachine` class and `StepState` type alias.
  - `src/state_teach/kernel.py` exists with `KolbMachine` class and `KolbStage` type alias.
  - `src/state_build/commands/` directory exists (empty aside from `__init__.py`).
  - `src/state_teach/personalities/` directory exists (empty aside from `__init__.py`).
  - `python3 -c "from src.state_build.kernel import StepMachine; s = StepMachine(); print(s.state)"` prints `idle`.
  - `python3 -c "from src.state_teach.kernel import KolbMachine; k = KolbMachine(); print(k.stage)"` prints `CE`.
  - Import guard: `python3 -c "import src.state_build; import src.state_teach; print('both importable')"` succeeds.
</acceptance_criteria>

---

### Task 3: Create daemon, worker, CLI packages + tests directory

<action>
Create the remaining package directories with minimal stubs:

**`src/state_daemon/` — always-on user service:**
```
src/state_daemon/
├── __init__.py        # Daemon package marker
├── server.py          # HTTP API server stub
├── watchers.py        # File/SSE watchers stub
└── cli.py             # `state daemon start/stop/status` stub
```

**`src/state_worker/` — per-session worker:**
```
src/state_worker/
├── __init__.py        # Worker package marker
├── main.py            # Spawned by plugin shim stub
└── bridge.py          # opencode HTTP + state-daemon client stub
```

**`src/state_cli/` — top-level CLI:**
```
src/state_cli/
├── __init__.py        # CLI package marker
└── main.py            # Typer app: `state auth login`, `state mode set`, etc.
```

**`tests/` — test suite:**
```
tests/
├── __init__.py
├── test_schema.py     # Placeholder: "import state_core.schema" smoke test
└── test_imports.py    # Verifies all packages import cleanly
```

**`tests/test_imports.py`** content:
```python
"""Verify all packages import without errors."""
from __future__ import annotations

def test_state_core_imports() -> None:
    import src.state_core  # noqa: F811
    import src.state_core.schema  # noqa: F811
    import src.state_core.events  # noqa: F811
    import src.state_core.scheduler  # noqa: F811

def test_state_build_imports() -> None:
    import src.state_build  # noqa: F811
    import src.state_build.kernel  # noqa: F811

def test_state_teach_imports() -> None:
    import src.state_teach  # noqa: F811
    import src.state_teach.kernel  # noqa: F811

def test_mode_silos_independent() -> None:
    """Verify build and teach can both be imported without conflict."""
    import src.state_build  # noqa: F811
    import src.state_teach  # noqa: F811
```

**`tests/test_schema.py`** content:
```python
"""Smoke tests for state_core.schema."""
from __future__ import annotations

from src.state_core.schema import EventEnvelope

def test_event_envelope_extra_forbid() -> None:
    e = EventEnvelope(id="test-id", type="test.event", ts="2026-04-23T00:00:00Z", data={"key": "val"})
    assert e.id == "test-id"
    assert e.type == "test.event"
    # extra fields should be forbidden
    import pytest
    with pytest.raises(ValueError):
        EventEnvelope(id="x", type="y", ts="z", extra_field="should_fail")  # type: ignore[call-arg]
```

Update `pyproject.toml` to add the `[tool.setuptools.packages.find]` directive so packages under `src/` are discoverable. Add to pyproject.toml:

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["state_core*", "state_build*", "state_teach*", "state_daemon*", "state_worker*", "state_cli*"]
```
</action>

<acceptance_criteria>
  - `src/state_daemon/__init__.py` exists.
  - `src/state_worker/__init__.py` and `src/state_worker/main.py` exist.
  - `src/state_cli/__init__.py` and `src/state_cli/main.py` exist.
  - `tests/__init__.py` exists.
  - `tests/test_imports.py` exists with all 4 test functions.
  - `tests/test_schema.py` exists with `test_event_envelope_extra_forbid`.
  - `pyproject.toml` contains `[tool.setuptools.packages.find]` with `where = ["src"]`.
  - `python3 -m pytest tests/test_imports.py -v` passes all 4 tests.
  - `python3 -m pytest tests/test_schema.py -v` passes the event envelope test.
  - Total `.py` file count under `src/` is at least 20.
</acceptance_criteria>

---

<verification>
1. `python3 -m pytest tests/ -v --tb=short` — all tests pass.
2. `uv run python3 -c "import src.state_core; print('state_core OK')"` — package importable.
3. `uv run python3 -c "import src.state_build; import src.state_teach; print('silos OK')"` — both at once importable.
4. `uv run python3 -c "from src.state_core.schema import EventEnvelope; print('schema OK')"` — schema importable.
5. Check directory tree: `find src -name '*.py' | wc -l` ≥ 20.
6. `ruff check src/ tests/ --no-cache` — exits 0 (ruff catches any issues).
</verification>

<must_haves>
- **state_core** package: `schema.py` with `EventEnvelope` (extra="forbid"), `events.py`, `scheduler.py`, `worktree.py`, `snapshot.py`, `auth/`, `providers/`
- **state_build** package: kernel.py with `StepMachine`, mcp.py
- **state_teach** package: kernel.py with `KolbMachine`, mcp.py, concepts.py, drill.py, mental_model.py
- **state_daemon**, **state_worker**, **state_cli** package stubs
- **tests/** directory with `test_imports.py` and `test_schema.py`
- **Physical silo constraint**: both `state_build` and `state_teach` importable simultaneously
- All `.py` files use `from __future__ import annotations` and have appropriate docstrings
</must_haves>
