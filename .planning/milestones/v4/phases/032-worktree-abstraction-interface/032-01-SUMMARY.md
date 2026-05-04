# Phase 032: Worktree Abstraction Interface — Summary

**Completed:** 2026-05-04
**Plan:** 032-01-PLAN.md

## Outcome

Expanded the `WorktreeService` Protocol stub from 2 methods to 4 (`create`, `list`, `remove`, `reset`) and added the `WorktreeInfo` pydantic return model. Host-agnostic — no imports from pygit2 or opencode.

## Files Changed

| File | Change |
|------|--------|
| `src/state_core/worktree.py` | Rewrote 12-line stub → 85-line module with Protocol + model |
| `tests/test_worktree.py` | Created — 8 tests covering model validation + Protocol subtyping |

## Verification

- 8/8 tests passing
- `WorktreeInfo` rejects unknown fields, is frozen.
- `WorktreeService` Protocol accepts structurally conforming implementations.
- `@runtime_checkable` enables `isinstance` checks.
