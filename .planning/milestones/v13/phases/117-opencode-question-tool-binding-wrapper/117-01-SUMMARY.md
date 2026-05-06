---
phase: 117-opencode-question-tool-binding-wrapper
plan: 01
subsystem: state-teach
tags: [mcp, question-binding, pydantic, skeleton, teach-mode]
requires: [115-mcp-server-scaffold]
provides:
  - Pydantic models (Question, Option, Answer) mirroring opencode question tool schema
  - Skeleton ask_structured() function for drill tool consumption
  - Full test suite with model validation and cross-mode import lint
affects: [drill-tools, integration-test, question-wire-up]
tech-stack:
  added: []
  patterns:
    - Pydantic v2 models with extra="forbid" and Field constraints
    - Skeleton-then-wire pattern (placeholder returns until Phase 123)
key-files:
  created:
    - src/state_teach/question_binding.py (88 lines, Question/Option/Answer models + ask_structured)
    - tests/test_state_teach_question_binding.py (110 lines, 9 tests)
  modified: []
key-decisions:
  - Skeleton ask_structured() returns __placeholder_{i}__ labels indexed by question position
patterns-established:
  - Question binding models mirror opencode's QuestionPrompt/QuestionOption schema byte-for-byte
  - All models enforce extra="forbid" for defense-in-depth against injection
  - ask_structured() is sync (not async) — async conversion deferred to Phase 123
requirements-completed:
  - MCP-T-04
metrics:
  duration: 271s
  completed: 2026-05-06
  tasks: 2
  files: 2
  commits: 2
---

# Phase 117 Plan 01: Opencode Question Tool Binding Wrapper Summary

Pydantic-typed question binding contract for opencode's question tool — Question, Option, Answer models plus a skeleton `ask_structured()` matching the signature drill tools will consume before real MCP wire-up in Phase 123.

## Deviations from Plan

None — plan executed exactly as written. Both TDD tasks completed with all verification checks passing.

## Known Stubs

| File | Line | Stub | Reason |
|------|------|------|--------|
| `src/state_teach/question_binding.py` | 67–72 | `ask_structured()` returns placeholder `__placeholder_{i}__` labels instead of real user input | Intentional skeleton — real `client.question.ask()` call wired in Phase 123 integration test |
| `src/state_teach/question_binding.py` | 65–72 | Function is sync-def, not async | Intentional — async conversion deferred to Phase 123 when real MCP call is added |

## Verification

```
IMPORT_OK — all 4 exports (Question, Option, Answer, ask_structured) importable
9 tests passed (0.16s) — model validation, forbidding, defaults, placeholder format, import lint
ruff — All checks passed!
import_lint — exit_code=0 (no cross-mode violations)
```

## Commits

| Hash | Type | Message |
|------|------|---------|
| `1ef9117` | feat(117-01) | Add question binding module with Pydantic models |
| `ca74646` | test(117-01) | Add question binding test suite with 9 tests |

## Self-Check: PASSED

- [x] `src/state_teach/question_binding.py` exists and is importable
- [x] `tests/test_state_teach_question_binding.py` exists with 9 passing tests
- [x] Both commits exist in git log (`1ef9117`, `ca74646`)
- [x] Ruff clean on both files
- [x] Cross-mode import lint clean
- [x] MCP-T-04 satisfied: typed question binding ready for drill tool consumption
