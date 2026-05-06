---
phase: 119-drill-prompt-token-cap
plan: 01
subsystem: state-teach
tags: [token-counting, drill-prompt, cap, hypothesis, tiktoken, MCP-T-06]
requires:
  - phase: 115
    provides: state-teach MCP server scaffold (package exists)
provides:
  - token counting via tiktoken cl100k_base (count_tokens)
  - token-aware prompt truncation (enforce_token_cap, 3000-token default)
  - Hypothesis property test suite (monotonic, cap enforcement, preservation)
affects:
  - Phase 122 (tool-budget CI — drill prompt cap enforcement)
tech-stack:
  added:
    - tiktoken>=0.8.0 (cl100k_base encoding for accurate token counting)
  patterns:
    - Pure leaf utility — no imports from other state_teach modules
    - Token-aware truncation (cuts at token boundaries via decode(tokens[:max_tokens]))
    - Silent truncation safety net — no logging/warnings in enforce_token_cap
    - Hypothesis property tests with st.text() strategies for invariant verification
key-files:
  created:
    - src/state_teach/token_utils.py (47 lines)
    - tests/test_token_utils.py (77 lines)
  modified:
    - pyproject.toml (added tiktoken dependency)
key-decisions:
  - "tiktoken cl100k_base encoding for accurate token counting rather than character approximation — matches OpenAI's actual tokenizer, ensures CI budget assertions are byte-exact"
  - "enforce_token_cap truncation is silent — drill tools are expected to compose prompts under cap; truncation is a safety net, not a policy enforcer"
  - "DEFAULT_TOKEN_CAP = 3000 as module-level constant — satisfies MCP-T-06 directly"
patterns-established:
  - "from __future__ import annotations on all new .py files"
  - "Module-level _ENCODING cache pattern — tiktoken encoding loaded once at import time"
  - "Hypothesis property tests covering monotonic, cap-enforcement, and preservation invariants"
requirements-completed:
  - MCP-T-06
metrics:
  duration: "4 min"
  completed: 2026-05-06
---

# Phase 119 Plan 01: Drill Prompt Token Cap — Summary

**One-liner:** Token counting and prompt-cap enforcement via tiktoken's cl100k_base encoding with 9 passing tests (5 basic + 4 Hypothesis property tests).

## What Was Built

A pure utility module for teach-mode drill tools to enforce the 3000-token cap (MCP-T-06):

- **`src/state_teach/token_utils.py`** (47 lines):
  - `count_tokens(text: str) -> int` — returns exact token count using `tiktoken.get_encoding("cl100k_base").encode()`
  - `enforce_token_cap(prompt: str, max_tokens: int = 3000) -> str` — returns prompt unchanged if under cap, otherwise truncates at token boundaries via `_ENCODING.decode(tokens[:max_tokens])`
  - `DEFAULT_TOKEN_CAP = 3000` — module-level constant
  - `_ENCODING` cached at module level (loaded once)
  - Zero imports from other state_teach modules — pure leaf utility

- **`tests/test_token_utils.py`** (77 lines):
  - 5 basic tests: empty string (0 tokens), basic count (>0), cap preserves short text, cap truncates long text, repeated character scales linearly
  - 4 Hypothesis property tests: monotonic (concatenation never decreases count), cap never exceeds, preservation when under cap, reasonable prompts (<2000 chars) fit under 3000 tokens
  - All 9 tests pass, ruff clean, mypy clean (project's missing py.typed marker is pre-existing)

- **`pyproject.toml`**: Added `"tiktoken>=0.8.0"` to dependencies

## Verification Results

| Check | Status |
|-------|--------|
| `count_tokens("") == 0` | PASS |
| `count_tokens("hello")` returns 1 | PASS |
| `enforce_token_cap("short prompt", 3000)` preserves text | PASS |
| `enforce_token_cap("x" * 100000, 10)` returns ≤10 tokens | PASS |
| 9/9 tests pass (5 basic + 4 Hypothesis) | PASS |
| Ruff clean (both files) | PASS |
| Mypy clean (no new errors) | PASS |
| Cross-mode imports: 0 violations | PASS |
| `tiktoken` importable in venv | PASS |

## Deviations from Plan

None — plan executed exactly as written. Task 1 and Task 2 were naturally combined into a single RED/GREEN cycle since the test file was written with both basic and Hypothesis tests together.

## Known Stubs

None — the implementation is complete. `count_tokens()` is a pure function with full implementation and no TODO/placeholder placeholders.

## Threat Flags

_None — no new network surface, auth paths, or trust boundaries. The module reads only its input string parameter and returns a string/integer. The existing `tokens.py` is a pre-existing character-based implementation from a prior execution — Chesterton's Fence applies._

## TDD Gate Compliance

Task-level `tdd="true"` gates satisfied:

1. **RED:** `35c8c8c` — `test(119-drill-prompt-token-cap): add failing tests for token utils` (all tests failed on ModuleNotFoundError)
2. **GREEN:** `d021e38` — `feat(119-drill-prompt-token-cap): implement token utils with tiktoken` (9/9 passing)

## Self-Check: PASSED

```
FOUND: src/state_teach/token_utils.py
FOUND: tests/test_token_utils.py
FOUND: 35c8c8c (RED test commit)
FOUND: d021e38 (GREEN impl commit)
```
