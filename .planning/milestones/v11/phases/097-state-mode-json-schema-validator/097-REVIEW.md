---
phase: 097-state-mode-json-schema-validator
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/state_core/schema.py
  - src/state_daemon/middleware.py
  - src/state_cli/main.py
  - tests/test_schema.py
  - tests/test_daemon_middleware.py
  - tests/test_cli.py
findings:
  critical: 0
  warning: 5
  info: 5
  total: 10
status: issues_found
---

# Phase 097: Code Review Report

**Reviewed:** 2026-05-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed three source modules (`schema.py`, `middleware.py`, `main.py`) and three test modules for Phase 097 (state-mode-json-schema-validator). The core schema definitions are thorough and correctly use Pydantic v2 discriminators, `extra="forbid"`, and frozen data models. The mode-enforcement middleware and CLI mode-init command are functionally sound.

**Key concerns:**

1. **Incomplete Provider event implementation** — data models and event type literals exist but no typed event classes or discriminated union, excluding provider events from `AnyStateEvent` parsing.
2. **TOCTOU race in default config creation** — the `load_mode_config()` function checks for file existence before creating, allowing another process to intervene.
3. **Inconsistent `VALID_MODES` sets** across three modules — each module defines its own slightly different set of valid mode strings, creating a maintenance hazard.
4. **Missing UTF-8 encoding on `open()`** in the export command — locale-dependent default encoding could corrupt event data on some platforms.
5. **Type hint gap in `build_event` factory** — the `data` parameter is typed as `object` rather than the expected typed data model.

No critical/blocking security vulnerabilities or data-loss bugs were found.

---

## Warnings

### WR-01: Incomplete Provider event implementation — typed classes and union missing

**File:** `src/state_core/schema.py:98-101, 423-468, 786-789`
**Issue:** `PROVIDER_EVENT_TYPES` (two literals: `state.provider.request`, `state.provider.response`) and their data models (`ProviderRequestData`, `ProviderResponseData`) are fully defined, but the corresponding typed event classes (`ProviderRequestEvent`, `ProviderResponseEvent`) and the `ProviderEvent` discriminated union are absent. Provider events are also excluded from `AnyStateEvent`. This means provider events can only be represented as generic `EventEnvelope` instances — the typed validation pipeline cannot handle them. While the `# Phase 028: cost accounting` comment on line 30 suggests this is deferred work, leaving data models and event-type literals in the code without the typed classes creates an inconsistent intermediate state that confuses contributors.

**Fix:** Either (a) complete the implementation by adding `ProviderRequestEvent`, `ProviderResponseEvent`, a `ProviderEvent` union, and including it in `AnyStateEvent`, or (b) if Phase 028 will own this, gate the data models and literals behind a feature flag or move them to a separate module to clearly signal they are not yet live.

---

### WR-02: TOCTOU race in `load_mode_config` default config creation

**File:** `src/state_daemon/middleware.py:48-53`
**Issue:** When `mode.json` is missing, the code checks `os.path.isfile(mode_path)` (line 48) and then separately creates the file (line 50-51). If another process creates the file between these calls, the existing config is silently overwritten. Additionally, `os.chmod` (line 52) runs after `open()` — a concurrent reader could access the file with incorrect permissions during the gap.

**Fix:**
```python
import os as _os

if not os.path.isfile(mode_path):
    default = ModeConfig(mode="both")
    # Atomically create with correct permissions
    fd = os.open(mode_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"mode": "both"}, f)
    except:
        os.unlink(mode_path)
        raise
    _config = default
    return default
```

---

### WR-03: Inconsistent `VALID_MODES` / valid-mode definitions across three modules

**File:** `src/state_core/schema.py:17`, `src/state_daemon/middleware.py:91`, `src/state_cli/main.py:73`
**Issue:** Three modules define subtly different mode validation sets:

| Module | Valid modes |
|---|---|
| `schema.py` (`Mode` literal) | `build`, `teach`, `kernel` |
| `schema.py` (`ModeConfig.mode` literal) | `build`, `teach`, `both` |
| `middleware.py` (`_VALID_MODES`) | `build`, `teach`, `both`, `kernel` |
| `main.py` (`VALID_MODES`) | `build`, `teach`, `kernel` |

These serve different purposes (event-filtering vs. config-persistence vs. header-validation vs. CLI-filtering), but the fact that each module independently defines its own set creates a maintenance hazard. If a new mode is added later, all four locations must be updated — and missing one would cause silent bugs.

**Fix:** Define the canonical mode sets in `state_core.schema` and import them everywhere else. For example:
```python
# In schema.py
PERSISTABLE_MODES: frozenset[str] = frozenset({"build", "teach", "both"})
RUNTIME_MODES: frozenset[str] = frozenset({"build", "teach", "kernel"})
ALL_RECOGNISED_MODES: frozenset[str] = PERSISTABLE_MODES | RUNTIME_MODES
```
Then import in `middleware.py` and `main.py` instead of defining local copies.

---

### WR-04: Locale-dependent encoding in `_do_export` file output

**File:** `src/state_cli/main.py:217`
**Issue:** The `open(output, "w")` call on line 217 lacks an explicit `encoding="utf-8"` parameter. Python's default `open()` encoding is `locale.getpreferredencoding()`, which varies by platform (e.g., ASCII on some CI runners, cp1252 on Windows). If event data contains non-ASCII characters (e.g., Unicode in `aggregate_id` or `changes_summary`), the write could raise `UnicodeEncodeError` or silently corrupt the output. By contrast, the `mode_init` command at line 271 correctly uses `encoding="utf-8"`.

**Fix:**
```python
with open(output, "w", encoding="utf-8") as fh:
```

---

### WR-05: `_do_export` carries unused `_output_format` parameter

**File:** `src/state_cli/main.py:206`
**Issue:** The `_output_format` parameter (defaulting to `"jsonl"`) is accepted in the function signature of `_do_export` but is never read or used within the function body. The format validation happens in the `export()` shell command, making this parameter dead code in the async implementation. This is misleading — a caller of `_do_export` might pass a different format expecting it to take effect.

**Fix:** Remove `_output_format` from `_do_export`'s signature, or pass it through and validate it within the async function for defense-in-depth:
```python
async def _do_export(
    from_id: str | None = None,
    to_id: str | None = None,
    mode: str | None = None,
    output: str | None = None,
) -> None:
```

---

## Info

### IN-01: ULID validator accepts non-Crockford base32 characters

**File:** `src/state_core/schema.py:148`
**Issue:** The `_ULID_PATTERN` regex (`^[0-7][0-9A-Za-z]{25}$`) accepts all alphanumeric characters. However, the Crockford base32 encoding used by ULIDs explicitly excludes `I`, `L`, `O`, and `U` (to avoid visual ambiguity). While the `ulid` library generates spec-compliant ULIDs, this validator would accept non-compliant strings like `01ILOU...`, weakening the validation contract.

**Fix:** If strict Crockford compliance is desired:
```python
_ULID_PATTERN = re.compile(r"^[0-7][0-9A-HJKMNP-Za-hjkmnp-z]{25}$")
```
Otherwise, document that the validator is intentionally lenient for forward compatibility.

---

### IN-02: `build_event` `data` parameter typed as `object` loses type safety

**File:** `src/state_core/schema.py:798`
**Issue:** The `data` parameter is annotated as `object`, which means type-checkers cannot verify that the passed data model matches the event class. For example, `build_event(ArcCreatedEvent, "arc-01", PhasePlannedData(...))` would pass type-checking but fail at runtime with a Pydantic `ValidationError`.

**Fix:** Use a `TypeVar` bound or overload to express the relationship:
```python
from typing import TypeVar

_DataT = TypeVar("_DataT", bound=BaseModel)

def build_event[T: EventEnvelope](
    event_cls: type[T],
    aggregate_id: str,
    data: object,  # Pydantic validates at runtime; type-safety deferred
    ...
) -> T:
```
(Python's type system cannot easily express "the `data` parameter's type must match `T.data`'s type" without overloads or protocols, so document this as a known gap or add runtime type-checking.)

---

### IN-03: Type annotations mismatch — `str` with `None` default should be `str | None`

**File:** `src/state_cli/main.py:94`
**Issue:** The `tail` command's `from_id` parameter is typed as `str` but defaults to `None`:
```python
from_id: str = typer.Option(None, "--from", ...)
```
This misleads type-checkers (mypy/pyright flag it). The same pattern appears in several other command parameters (lines 153, 183, 184). Typer correctly handles `None` at runtime, but the annotation is imprecise.

**Fix:**
```python
from_id: str | None = typer.Option(None, "--from", ...)
```

---

### IN-04: `EventEnvelope` allows empty strings for most fields — no validation

**File:** `src/state_core/schema.py:162-194`
**Issue:** `EventEnvelope` defaults `id`, `aggregate_id`, `type`, `ts` to `""` (empty string). While the docstring explains this supports "incremental construction," it means the base class imposes no validation on these fields — empty strings pass through silently. Only `id` has a conditional validator (only checks non-empty). The per-aggregate typed events fix this with `Literal` defaults, but generic `EventEnvelope` usage has no such guard. This is a deliberate design choice but worth documenting explicitly as a risk for generic event handling.

---

### IN-05: Magic number `-13` in `_print_event_line` format truncation

**File:** `src/state_cli/main.py:88`
**Issue:** The format string uses `ev['id'][-13:]` to show the last 13 characters of a 26-char ULID. The magic number `-13` and the hardcoded column widths (`<40s`, `<20s`, `<8s`) are repeated without named constants. If the ULID or column layout changes, these numbers must be updated in multiple places.

**Fix:** Extract format constants:
```python
_ULID_SUFFIX_LEN = 13
_TYPE_COL_WIDTH = 40
_AGG_COL_WIDTH = 20
_MODE_COL_WIDTH = 8

def _print_event_line(ev: dict) -> None:
    typer.echo(
        f"{ev['id'][-_ULID_SUFFIX_LEN:]}  "
        f"{ev['type']:<{_TYPE_COL_WIDTH}s} "
        f"{ev['aggregate_id'][:_AGG_COL_WIDTH]:<{_AGG_COL_WIDTH}s} "
        f"{ev['mode']:<{_MODE_COL_WIDTH}s} {ev['ts']}"
    )
```

---

_Reviewed: 2026-05-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
