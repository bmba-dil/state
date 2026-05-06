---
phase: 116-15-skeleton-tools-80-token
plan: 01
subsystem: state-teach-mcp
tags: [mcp, skeleton, tools, teach-mode]
requires:
  provides: [MCP-T-02, MCP-T-03]
  affects: [phase-117, phase-118, phase-119, phase-120, phase-121, phase-122, phase-123]
tech-stack:
  added: [tiktoken]
  patterns: [async-mcp-tools, decorator-descriptions, dict-return-skeletons]
key-files:
  created:
    - tests/test_state_teach_mcp_tools.py
  modified:
    - src/state_teach/mcp.py
    - tests/test_state_teach_mcp.py
key-decisions:
  - "Use @mcp.tool(description=...) decorator for tool descriptions instead of docstrings"
  - "All skeleton tools return {'error': 'not_implemented'} dict instead of SkeletonResponse model"
  - "Tool descriptions kept <=80 tokens measured with tiktoken o200k_base encoding"
  - "Removed overlapping Phase 116 tests from test_state_teach_mcp.py (superseded by test_state_teach_mcp_tools.py)"
patterns-established:
  - "Skeleton MCP tools use async def, return plain dict, no docstrings, no comments"
  - "Tool descriptions go in @mcp.tool(description=...) decorator parameter"
  - "Token budget enforcement via tiktoken o200k_base in test suite"
requirements-completed:
  - MCP-T-02
  - MCP-T-03
metrics:
  duration: 18m
  completed: 2026-05-06
---

# Phase 116 Plan 01: 15 Skeleton MCP Tools Summary

**One-liner:** Replaced 14 Phase 115 sync skeleton tools with 15 async skeleton MCP tools using decorator descriptions and dict-based not-implemented responses, all verified <=80 tokens per description.

## What Was Built

- **15 `@mcp.tool()` async functions** registered on the state-teach FastMCP instance in `src/state_teach/mcp.py`
- **14 required tools** from MCP-T-03 (`concept_next`, `drill_prepare`, `drill_verify`, `concept_teach`, `observation_record`, `mental_model_show`, `subject_pick`, `subject_author`, `style_edit`, `learner_state`, `review_session`, `mentor_scaffold`, `coding_partner`, `learning_verify`)
- **1 discretionary 15th tool** (`knowledge_check`) for pre-teaching knowledge assessment
- **All tools return `{"error": "not_implemented"}`** — no-op skeletons ready for implementation phases 117-123
- **New test suite** in `tests/test_state_teach_mcp_tools.py` covering registration count, required names, token budgets (tiktoken o200k_base), skeleton return values, and import lint

## Key Format Changes from Phase 115

| Aspect | Phase 115 | Phase 116 |
|--------|-----------|-----------|
| Function style | `def concept_next() -> SkeletonResponse` | `async def concept_next() -> dict[str, str]` |
| Description | Docstring | `@mcp.tool(description="...")` decorator |
| Return value | `SkeletonResponse(tool="concept_next")` | `{"error": "not_implemented"}` |
| Response model | `SkeletonResponse(BaseModel)` | Plain dict (model removed) |
| Comments | Section comments (`# ── Concept...`) | No comments |

## Verification Results

```
13/13 tests pass:
  - 8 Phase 115 tests (mode-gate, server identity, import lint)
  - 5 Phase 116 tests (tool count, names, token budget, return values, import lint)

15 tools: ['coding_partner', 'concept_next', 'concept_teach', 'drill_prepare',
           'drill_verify', 'knowledge_check', 'learner_state', 'learning_verify',
           'mental_model_show', 'mentor_scaffold', 'observation_record',
           'review_session', 'style_edit', 'subject_author', 'subject_pick']

ruff check: All checks passed
import lint: clean (zero cross-mode violations)
```

## Deviation from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed overlapping Phase 116 tests from Phase 115 test file**
- **Found during:** Task 2 execution
- **Issue:** `tests/test_state_teach_mcp.py` contained Phase 116 tool registration tests (`test_all_tools_registered`, `test_tool_description_token_budget`, `test_skeleton_tools_return_not_implemented`) that used the old `SkeletonResponse` format and `mcp._tool_manager._tools` API. These tests conflicted with the new Phase 116 implementation.
- **Fix:** Removed the Phase 116 tests from `test_state_teach_mcp.py` — they are superseded by the new `test_state_teach_mcp_tools.py` which uses the correct introspection API (`mcp._tool_manager.list_tools()`) and matches the new return format.
- **Files modified:** `tests/test_state_teach_mcp.py`

**2. [Rule 2 - Missing critical functionality] Ruff E501 fixes for 6 decorator lines**
- **Found during:** Task 1 verification
- **Issue:** Six tool description decorator lines exceeded the 120-character line limit (ruff E501).
- **Fix:** Shortened 6 descriptions slightly while preserving semantics and keeping all token counts <=80:
  - `concept_next`: removed "based on" and "current" (117 chars, 17 tokens)
  - `concept_teach`: simplified mode selection phrasing (115 chars, 23 tokens)
  - `mental_model_show`: removed "current" (118 chars, 15 tokens)
  - `style_edit`: removed "profile" (113 chars, 16 tokens)
  - `mentor_scaffold`: removed "file-by-file" (108 chars, 12 tokens)
  - `coding_partner`: changed "encounters difficulty" to "is stuck" (110 chars, 13 tokens)
- **Files modified:** `src/state_teach/mcp.py`

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | bd4f57d | test(116-01) | Add failing tests for 15 skeleton tool registration (RED) |
| 2 | ad5d371 | feat(116-01) | Add 15 skeleton teach-mode MCP tools with token-limited descriptions |

## Self-Check

- [x] `src/state_teach/mcp.py` — 15 `@mcp.tool()` async functions present
- [x] `tests/test_state_teach_mcp_tools.py` — 5 passing tests
- [x] `tests/test_state_teach_mcp.py` — 8 passing tests, no regression
- [x] `ruff check` — All checks passed
- [x] Import lint — clean
- [x] Commits bd4f57d and ad5d371 present in git log

## Self-Check: PASSED
