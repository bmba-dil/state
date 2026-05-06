---
phase: 119-drill-prompt-token-cap
plan: 01
subsystem: state-teach
tags: [token-counting, drill-prompt, cap, hypothesis, MCP-T-06]
requires:
  - phase: 115
    provides: state-teach MCP server scaffold (package exists)
provides:
  - token counting helper (count_tokens, TOKEN_CAP=3000)
  - Hypothesis property test suite (non-negativity, monotonic, boundary)
affects:
  - Phase 122 (tool-budget CI — drill prompt cap enforcement)
tech-stack:
  added: []
  patterns:
    - character-based token approximation (len(text) // 4) since tiktoken is rejected
    - module-level structlog.Logger for consistent observability
    - Hypothesis property tests with st.text() strategies
key-files:
  created:
    - src/state_teach/tokens.py (38 lines)
    - tests/test_state_teach_tokens.py (86 lines)
  modified: []
key-decisions:
  - "Character-based token counting (len(text) // 4) rather than tiktoken — matches OpenAI-standard rule of thumb, deterministic, zero dependencies, no external API calls"
  - "TOKEN_CAP = 3000 at module level as a named constant rather than magic number — enables import-time verification and future CI budget assertions"
  - "Hypothesis min_size=1000..8000 for text strategy (not 12000..20000) — respects Hypothesis's internal buffer limit while still testing long-prompt scaling"
patterns-established:
  - "Module-level TOKEN_CAP pattern for teach-mode token budgets"
  - "Hypothesis text() strategy with max_size=8000 for Python 3.12 compatibility"
  - "from __future__ import annotations on all new .py files (established convention)"
requirements-completed:
  - MCP-T-06
metrics:
  duration: "7 min"
  completed: 2026-05-06
---

# Phase 119 Plan 01: Token-Cap Helper — Summary

**One-liner:** Character-based token counter at `state_teach.tokens` with `TOKEN_CAP=3000` (MCP-T-06) and 8 passing tests including 3 Hypothesis property tests covering non-negativity, monotonic scaling, and boundary behavior.

## What Was Built

A minimal, deterministic token-counting module for teach-mode drill prompts:

- **`src/state_teach/tokens.py`** (38 lines):
  - `TOKEN_CAP = 3000` — module-level constant per MCP-T-06
  - `count_tokens(text: str) -> int` — returns `len(text) // 4` (OpenAI-standard character approximation)
  - Google-style docstrings with Args/Returns/Edge cases sections
  - Module-level structlog logger (established project pattern)
  - Zero imports from `state_build` (physical mode isolation maintained)

- **`tests/test_state_teach_tokens.py`** (86 lines):
  - 5 edge-case unit tests: empty string, whitespace, exact 3000-token boundary, below-cap, 15k-char long prompt
  - 3 Hypothesis property tests: non-negativity (`>=0` for all text), monotonic (concatenation never reduces count), linear scaling (matches `len//4` exactly)
  - All 8 tests pass, ruff clean, import lint clean

## Design Rationale

Since `tiktoken` is rejected in the project stack, the implementation uses the industry-standard approximation of 1 token ≈ 4 characters (the OpenAI rule of thumb for English text). This approach is:
- **Deterministic** — no randomness, always the same output for the same input (matches project requirement for reproducible event payloads)
- **Zero dependencies** — pure Python integer division, no network calls
- **Accurate enough** for a budget cap — the purpose is preventing prompt bloat, not byte-exact token matching

## Verification Results

| Check | Status |
|-------|--------|
| `count_tokens("") == 0` | PASS |
| `count_tokens("x" * 12000) == 3000` | PASS |
| `count_tokens("a" * 15000) == 3750` | PASS |
| 8/8 tests pass (5 unit + 3 Hypothesis) | PASS |
| Ruff clean (both files) | PASS |
| Import lint clean (0 cross-mode violations) | PASS |
| `TOKEN_CAP == 3000` importable | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Hypothesis text() strategy exceeded internal buffer**
- **Found during:** GREEN phase verification
- **Issue:** `st.text(min_size=12000, max_size=20000)` raised `InvalidArgument` — Hypothesis's internal buffer size (~8k) cannot generate strings that large
- **Fix:** Reduced range to `min_size=1000, max_size=8000` and changed assertion to verify `count == len(text) // 4` (exact match rather than broad upper bound). The 12000-char boundary is still covered by the `test_exact_boundary` unit test.
- **Files modified:** `tests/test_state_teach_tokens.py`
- **Commit:** Included in `0402dd3`

## Known Stubs

None — the implementation is complete. `count_tokens()` is a pure function with full implementation and no TODO/placeholder placeholders.

## Threat Flags

_None — no new network surface, auth paths, or trust boundaries. The module reads only its input string parameter and returns an integer._

## TDD Gate Compliance

Plan-level `type: tdd` gate sequence is satisfied:

1. **RED:** `6b2e613` — `test(119-01): add failing tests for token counting helper` (8 tests, all failing on ModuleNotFoundError)
2. **GREEN:** `0402dd3` — `feat(119-01): implement token counting helper for drill prompt cap` (implementation + 8/8 passing)

## Self-Check: PASSED

```
FOUND: src/state_teach/tokens.py
FOUND: tests/test_state_teach_tokens.py
FOUND: 6b2e613 (RED test commit)
FOUND: 0402dd3 (GREEN impl commit)
```
