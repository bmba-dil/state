# Coding Conventions

**Analysis Date:** 2026-05-05

## Naming Patterns

**Files:**
- snake_case: `events.py`, `http_client.py`, `anthropic_client.py`, `model_profile.py`
- Test files: `test_<module>.py` — e.g., `test_events.py`, `test_config.py`

**Directories:**
- snake_case with underscores: `state_core/`, `state_daemon/`, `state_cli/`
- Package subdirectories mirror domain boundaries: `src/state_core/providers/`, `src/state_core/auth/`
- Test directories mirror source: `tests/auth/` mirrors `src/state_core/auth/`

**Functions:**
- snake_case: `build_shared_client()`, `get_db_path()`, `_maybe_repair()`, `find_opencode_config()`
- Private helpers: underscore prefix `_build_sdk()`, `_resolve_db_path()`, `_validate_ulid()`

**Variables:**
- snake_case: `db_path`, `event_row`, `consecutive_failures`
- Module-level constants: UPPER_SNAKE_CASE — `DEFAULT_OPENCODE_PORT`, `BACKOFF_MAX`, `REDACTED`, `CYCLE_SENTINEL`
- Module-level private state: underscore prefix — `_INSTALLED`, `_PATTERNS`, `_DEFAULT_MAX_CONNECTIONS`
- Pydantic model fields: snake_case — `aggregate_type`, `provider_id`, `changes_summary`

**Types/Classes:**
- PascalCase: `SqliteEventStore`, `AnthropicClient`, `DaemonServer`, `ProviderRouter`
- Pydantic data payload models: `{Aggregate}{Action}Data` — e.g., `ArcCreatedData`, `StepVerifyPassedData`, `AuthImportedData`
- Pydantic event models: `{Aggregate}{Action}Event` — e.g., `ArcCreatedEvent`, `SchedulerDeadlockEvent`
- Protocols (interfaces): `EventStore`, `AuthMethod`
- Named with suffix when disambiguating: `ProviderTransientError`, `ProviderAuthError`, `ProviderBadRequestError`

**Exception Classes:**
- PascalCase with `Error` suffix: `StateProviderError`, `AuthLoginError`, `RedactorNotAttached`
- Grouped by hierarchy: base class at top, specific subtypes below

## Code Style

**Formatting:**
- Ruff (v0.9.0+) for both linting and formatting
- Line length: **120** characters (`pyproject.toml` line 50)
- Quote style: **double quotes** (`"string"` not `'string'`)
- Indent: **spaces** (4-space)
- Pre-commit hooks: `ruff --fix`, `ruff-format` (formatting), `mypy`, `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`

**Linting:**
- Ruff rules enabled: `E`, `F`, `I`, `N`, `W`, `UP`, `B`, `SIM`, `ARG`, `C4`, `T20`
- Per-file ignore: `__init__.py` ignores `F401` (unused imports — intentional for re-exports)
- mypy: **strict mode** (`strict = true`), `warn_unused_ignores = true`, `explicit_package_bases = true`, `namespace_packages = true`
- Python target: **3.12** (ruff `target-version = "py312"`, mypy `python_version = "3.12"`)

**Future Imports:**
- **Every** `.py` file starts with `from __future__ import annotations` — no exceptions
- This enables PEP 604 union syntax (`str | None`) and deferred annotation evaluation

## Import Organization

**Order (within each group, alphabetized):**
1. `from __future__ import annotations` (always first)
2. Standard library imports (`import asyncio`, `import json`, `from pathlib import Path`)
3. Third-party imports (`import aiosqlite`, `import structlog`, `from pydantic import BaseModel`)
4. Application imports — mix of two styles depending on package context:
   - `src.state_core.*` pattern used in `state_core/database.py`, `tests/test_events.py`
   - Bare `state_core.*` pattern used in `src/state_core/providers/router.py`, `tests/auth/conftest.py`

**Path Aliases:**
- mypy `explicit_package_bases = true` + `namespace_packages = true` allows both `src.state_core.*` and bare `state_core.*` imports
- In provider/auth modules, prefer bare `state_core.*` to match namespace package semantics
- Source under `src/state_core/providers/` uses `from state_core.auth.base import ...` (bare, no `src.` prefix)

**Import Discipline:**
- Mode isolation is physically enforced: `state.build.*` must never import `state.teach.*` or vice versa
- `state_core` must not import `state_build` or `state_teach` — this is lint-enforced in CI and tested in `test_imports.py`
- CLI layer (`state_cli`) imports from `state_core` only — never the reverse

## Module-Level Structure

**Pattern (from `src/state_core/database.py`, `src/state_core/providers/errors.py`):**

```python
"""Module docstring — comprehensive, references phases and decisions."""

from __future__ import annotations

import os
from pathlib import Path

import aiosqlite

# Module-level constants
_DEFAULT_VALUE: int = 42

# Top-level functions
def get_db_path() -> Path:
    ...

# Classes
class SqliteEventStore:
    ...
```

**Section separators (observed in `src/state_core/schema.py`, `tests/test_events.py`):**
```python
# ── Section Name ── (Unicode box-drawing dash characters)
```
Used to separate logical groups within large files.

## Documentation

**Module Docstrings:**
- Every module has a docstring
- Comprehensive — describes purpose, phase lineage, architecture context, cardinal rules
- Example: `src/state_core/events.py` begins with `"""Event store: SQLite writer + SyncEvent mirror for dual-write architecture."""`
- `src/state_core/observability/__init__.py` includes full public surface listing, cardinal rules, and phase references

**Function/Method Docstrings:**
- Google-style: Args, Returns, Raises sections
- Applied to public API methods and complex private methods
- Private helpers have inline comments rather than full docstrings

```python
async def append(
    self,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    data: dict[str, Any],
    *,
    mode: Mode = "kernel",
    ts: str | None = None,
    id_: str | None = None,
    mirror: SyncEventMirror | None = None,
) -> str:
    """Append an event row with ULID generation and seq enforcement.

    Args:
        aggregate_type: Aggregate discriminator (e.g. 'step', 'arc').
        aggregate_id: ID of the aggregate instance.
        event_type: Event type string (e.g. 'state.step.verify_passed').
        data: Event-specific payload dict.
        mode: Execution mode (build, teach, or kernel).
        ts: ISO 8601 timestamp. If None, uses a fixed epoch string.
        id_: ULID for the event. If None, auto-generated.
        mirror: Optional SyncEventMirror for fire-and-forget emission.

    Returns:
        The ULID string of the newly-inserted event.
    """
```

**Inline Comments:**
- Used for security-critical annotations: `# NEVER log cred.access — T-026-1 secret hygiene`
- Used for non-obvious behavior: `# stealth keys: "authorization" (handled by auth_token=), ...`
- Used for phase/decision tracking: `# Phase 028: cost accounting`

**Comment Coverage — Security:**
- Token-related code ALWAYS has explicit comments about what NOT to log
- Secret-cleaning code has provenance comments tracing regex shapes to source files

## Error Handling

**Pattern from `src/state_core/providers/anthropic_client.py` (lines 151-173):**

```python
try:
    return await self._sdk.messages.create(**create_kwargs)
except anthropic.APIConnectionError as e:
    log.warning("anthropic_client.connection_error", error=str(e))
    raise ProviderTransientError(f"connection: {e}") from e
except anthropic.RateLimitError as e:
    log.warning("anthropic_client.rate_limit", error=str(e))
    raise ProviderTransientError(f"rate_limit: {e}") from e
except anthropic.AuthenticationError as e:
    log.warning("anthropic_client.auth_error", status=e.status_code)
    raise ProviderAuthError(f"auth {e.status_code}: {e}") from e
```

**Key Patterns:**
- Catch specific exception types, not broad `Exception`
- Re-raise as domain-specific error with `from e` for traceback preservation
- Log a warning before re-raising (with structured key-value pairs)
- Never log raw tokens in error messages — only status codes and sanitized strings
- `TypeError` for unsupported type conditions (e.g., bad credential type)
- `RuntimeError` for invalid state (e.g., checksum tamper in `migrations.py`)
- `contextlib.suppress(asyncio.CancelledError)` for cleanup in task cancellation

**Custom Error Hierarchies:**
- Flat hierarchies with a base class: `StateProviderError` → `ProviderTransientError`, `ProviderAuthError`, `ProviderBadRequestError`, `ProviderResponseError`
- Fatal errors are exceptions, not return codes: `RedactorNotAttached(RuntimeError)` — daemon exits non-zero

## Logging

**Framework:** `structlog >= 25.1`

**Logger Instantiation:**
```python
import structlog
log = structlog.get_logger(__name__)
```
Consistently used across all source modules. Module-level, not per-function.

**Logging Patterns:**
```python
# Info with structured key-values
log.info("repair_triggered", source=source)
log.info("repair_completed", count=len(repairs))

# Debug for routing decisions
log.debug("provider_router.select", route="anthropic_sdk", provider_id=cred.provider_id)

# Warning for transient errors (noise-level)
log.warning("anthropic_client.connection_error", error=str(e))

# Exception logging with full traceback
log.exception("events.post_commit_callback_error", event_id=id_)
```

**Event Names:** Short, underscore-delimited, `<module>.<action>` pattern: `"repair_triggered"`, `"anthropic_client.create"`, `"provider_router.select"`

**Security:** Token values are NEVER logged. The `state_core.observability.redactor` is a defense-in-depth layer that redacts token-shaped substrings even if a call site accidentally includes them. Log entries for auth operations carry only `provider_id` and `route` — never `access`, `key`, or other secret fields.

## Function Design

**Signature Style:**
- Positional args for required identifiers: `append(self, aggregate_type, aggregate_id, event_type, data, ...)`
- Keyword-only (`*`) for options: `*, mode=..., ts=None, id_=None, mirror=None`
- Return type always annotated
- `__init__` always annotated with `-> None`

**Async/Sync Boundary:**
- I/O-bound: always `async def`
- Pure computation/routing: `def` (synchronous) — e.g., `ProviderRouter.select()` is sync
- Async resource management uses `@asynccontextmanager` and `async with`

**Parameter Design:**
- Clock/datetime values are **injected as parameters**, never read from `datetime.now()` or `time.time()`
- This ensures determinism for testing and replay

## Pydantic Model Conventions

**From `src/state_core/schema.py` and `src/state_core/auth/base.py`:**

```python
class ArcCreatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    goal: str
```

- `extra="forbid"` on ALL models — rejects unknown fields
- `frozen=True` on data payloads — immutability, `model_copy()` for updates
- Secret fields use `Field(repr=False)` — excluded from `repr()`
- `Literal[...]` for discriminated unions and constrained values
- `@field_validator` (classmethod) for custom validation
- `TypeAdapter` for generic (de)serialization of discriminated unions
- `model_copy(update={...})` for creating modified copies

## Module Design

**`__init__.py` Barrel Files:**
- Explicit imports with `from module import Thing` — never `import *`
- `__all__` list matching imports exactly
- `src/state_core/__init__.py` is the public API surface
- `src/state_core/auth/__init__.py` re-exports from submodules but deliberately excludes provider modules

**Protocol Usage:**
- `@runtime_checkable` for structural subtyping: `AuthMethod(Protocol)`
- Protocols used for interfaces consumed by multiple implementations
- `runtime_checkable` enables `isinstance(obj, Protocol)` — but only validates attribute presence, not signatures

**Config/Constants:**
- Module-level constants for defaults and configuration
- Environment variable overrides read via `os.environ.get()`
- Default values are module-level constants, not inlined magic numbers

## Comments

**When to Comment:**
- Module docstrings: Always (purpose, architecture context, phase lineage)
- Public function docstrings: Always (Args, Returns, Raises)
- Security-critical code: Always (what NOT to do, provenance)
- Non-obvious logic: Always (why a workaround exists, why a pattern is chosen)
- Routine code: Sparingly (let the code speak)

**No JSDoc/TSDoc** — this is a Python-only codebase. Functions use standard Python docstrings.

---

*Convention analysis: 2026-05-05*
