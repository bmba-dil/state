---
phase: 041-scheduler-core-module-typed-depends
reviewed: 2026-05-04T23:55:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/state_core/scheduler.py
  - tests/test_scheduler.py
  - src/state_core/__init__.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 041: Code Review Report

**Reviewed:** 2026-05-04T23:55:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the typed DAG scheduler core module (EdgeKind literal, frozen pydantic Edge/Node models, NodeRegistry, DAGScheduler skeleton) and its test suite. The implementation is solid — 17/17 tests pass, models correctly enforce `extra="forbid"` and `frozen=True`, and the registry provides full dict-backed CRUD operations. All plan must-have truths (8/8) are satisfied.

Two warnings found: a type annotation mismatch in the `DAGScheduler.tick()` skeleton (annotated `-> list[str]` but returns `None` at runtime), and a missing `frozen=True` verification test for the `Node` model (Edge has one, Node does not). Three informational items: empty string node IDs are accepted, self-loop edges are not rejected, and `DAGScheduler` is not exported from the package root.

No security vulnerabilities, correctness bugs, or data loss risks.

---

## Warnings

### WR-01: `DAGScheduler.tick()` has misleading return type annotation

**File:** `src/state_core/scheduler.py:97-99`
**Issue:** The `tick()` method skeleton is annotated as `-> list[str]` but the body is only `...` (Ellipsis). Since `...` is a statement, not a `return`, the coroutine resolves to `None` at runtime when awaited. This creates a type-safety gap — a caller that type-checks against the annotation will expect `list[str]` but receives `None`.

```python
async def tick(self, arc_id: str) -> list[str]:
    """Return all Step IDs ready for concurrent dispatch."""
    ...
```

**Impact:** `await DAGScheduler().tick("arc-01")` returns `None`, not `list[str]`. Any code that iterates or indexes the result will raise `TypeError: 'NoneType' object is not iterable`.

**Fix:** Until the tick implementation lands (phases 042–049), either:
- (A) Remove the return type annotation and use `# type: ignore[return]` to communicate that this is an incomplete skeleton:
  ```python
  async def tick(self, arc_id: str):  # noqa: return type TBD by phase 044
      """Return all Step IDs ready for concurrent dispatch."""
      raise NotImplementedError("Scheduling logic not yet implemented (phases 042-049)")
  ```
- (B) Return an empty list matching the annotation:
  ```python
  async def tick(self, arc_id: str) -> list[str]:
      """Return all Step IDs ready for concurrent dispatch."""
      return []  # skeleton — real logic in phases 042-049
  ```

Option A is preferred — it fails loudly if someone accidentally calls `tick()` before the implementation is ready, rather than silently returning an empty list. Option B is acceptable if this module must not raise exceptions at import/call time.

---

### WR-02: Missing `frozen=True` verification test for `Node` model

**File:** `tests/test_scheduler.py` (test omission)
**Issue:** The test suite includes `test_edge_is_frozen` (line 47) that verifies `Edge` is immutable — but there is no equivalent test for `Node`, despite both models using `ConfigDict(frozen=True)`. The plan requires both models to enforce immutability (threat T-041-01), and the acceptance criteria check for `frozen=True` twice across the module.

If a future refactor accidentally removes `frozen=True` from `Node` (e.g., to add mutable status transitions), this regression would not be caught by the test suite.

**Fix:** Add a `test_node_is_frozen` test to `TestNodeModel`:
```python
def test_node_is_frozen(self) -> None:
    """Node model is frozen — setting .status after construction raises error."""
    n = Node(id="step-1", kind="step")
    with pytest.raises(ValidationError):
        n.status = "done"  # type: ignore[misc]
```

---

## Info

### IN-01: Empty string node IDs accepted with no minimum length validation

**File:** `src/state_core/scheduler.py:39`
**Issue:** `Node(id='', kind='step')` is accepted. The `id` field is typed as `str` with no `min_length` constraint. Empty string IDs can cause confusing behavior in registry lookups and DAG operations — `registry.get("")` would retrieve the empty-ID node, and edges referencing `source_node=""` would match it.

This is not a bug — the DAG validator (phase 043) and edge builder (phase 042) may add node ID validation at a higher level. However, adding a cheap `min_length=1` constraint to the pydantic model would provide defense-in-depth.

**Fix (optional):**
```python
from pydantic import Field

class Node(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(..., min_length=1)
```

---

### IN-02: Self-loop edges are not rejected

**File:** `src/state_core/scheduler.py:21-28` (Edge model)
**Issue:** `Edge(source_node='a', target_node='a', kind='blocks')` is a valid edge. Self-loops (`source_node == target_node`) are not valid in a DAG and can cause infinite scheduling loops if not caught before graph evaluation. No validation prevents this at the model level.

This is a deferred concern — the DAG validator (phase 043) will detect cycles including self-loops. Adding model-level validation now would be premature optimization. Documented here for awareness.

---

### IN-03: `DAGScheduler` class not exported from package `__init__.py`

**File:** `src/state_core/__init__.py:7-13`
**Issue:** The `DAGScheduler` class exists in `scheduler.py` but is not included in `__all__` or the `from src.state_core.scheduler import ...` statement. This creates an asymmetry:
- `from src.state_core.scheduler import DAGScheduler` ✅ works
- `from src.state_core import DAGScheduler` ❌ raises `ImportError`

While the plan only requires Edge/EdgeKind/Node/NodeRegistry exports (DAGScheduler is a skeleton for later phases), this inconsistency could surprise developers who discover the class via IDE autocompletion but cannot import it from the package root.

**Fix (optional):** Add `DAGScheduler` to the exports:
```python
from src.state_core.scheduler import DAGScheduler, Edge, EdgeKind, Node, NodeRegistry

__all__ = [
    "DAGScheduler",
    "Edge",
    "EdgeKind",
    "Node",
    "NodeRegistry",
]
```
Or defer until phase 044 when the scheduler is functional.

---

## Security Review

No security issues found. The threat model (T-041-01 through T-041-04) is correctly addressed:

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-041-01: Field injection / post-construction tampering | `extra="forbid"` + `frozen=True` on both Edge and Node | ✅ Effective — verified by tests 4-5 (Edge) and test 10 (Node) |
| T-041-02: Silent overwrite in NodeRegistry | `ValueError` on duplicate `register()` | ✅ Effective — verified by test 13 |
| T-041-03: DoS via unbounded registry growth | Bounded DAG size (arcs/phases/steps) | ✅ Accepted risk as documented |
| T-041-04: Information disclosure | No secrets in data models | ✅ Confirmed — only string IDs and status enums |

**Additional checks performed:**
- No hardcoded credentials, tokens, or secrets ✅
- No `eval()`, `exec()`, `dangerouslySetInnerHTML`, or `shell_exec` ✅
- No command injection, SQL injection, or path traversal vectors ✅
- No empty catch blocks ✅
- No debug artifacts (console.log, debugger, TODO/FIXME) ✅

---

## Test Quality Assessment

The test suite (17 tests) is comprehensive for the phase scope:

- **Edge model (5 tests):** Valid creation (blocks/soft/data), invalid kind rejection, extra field rejection, frozen immutability
- **Node model (5 tests):** Default status, explicit status, invalid kind/status rejection, extra field rejection
- **NodeRegistry (7 tests):** Register/get round-trip, contains, duplicate rejection, remove-then-get error, all_nodes, len, `in` operator

**Strengths:**
- Tests are isolated and focused on single behaviors
- Proper use of `pytest.raises` for error assertions
- Tests verify identity (`assert registry.get("step-1") is node`) not just equality
- All 17 pass cleanly in 0.11s

**Gap:** `Node` frozen immutability is not tested (see WR-02). One additional test would close this gap.

---

_Reviewed: 2026-05-04T23:55:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
