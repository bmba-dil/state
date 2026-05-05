---
phase: 029
status: advisory
reviewed: 2026-05-04
findings: 3
blocking: 0
---

# Phase 029 — Code Review

## Summary

1 STYLE, 2 MINOR findings. No correctness or security issues. Implementation logic, pre-flight guards, wire-capture tests, and mode-isolation test are all correct. 875 tests green.

## Findings

### [STYLE] Stale Wave-0 comment in test file
**File:** `tests/test_thinking_budget_propagation.py:26`
**Issue:** `# RED: does not exist yet` was a Wave-0 orientation comment. The module now exists — misleading to future readers.
**Suggestion:** Remove the inline comment.

### [MINOR] Overly verbose module docstring
**File:** `src/state_core/providers/thinking_budget.py:1-22`
**Issue:** 22-line module docstring violates CLAUDE.md "no multi-paragraph docstrings". Most content explains what the code does (derivable from signatures) or belongs in a PR description.
**Suggestion:** Trim to the one non-obvious constraint (litellm incompatibility):
```python
"""Bridge: ResolvedProfile.thinking_budget_tokens → ThinkingConfigParam for AnthropicClient.

NOTE: Only pass result to AnthropicClient.create(thinking=...). LitellmClient raises
UnsupportedParamsError for thinking= kwarg — gate at call site.
"""
```

### [MINOR] Plain dict return loses static type safety
**File:** `src/state_core/providers/thinking_budget.py:76`
**Issue:** `return {"type": "enabled", "budget_tokens": budget}` — typos in dict keys pass the type checker silently.
**Suggestion:** Use the TypedDict constructor:
```python
from anthropic.types.thinking_config_enabled_param import ThinkingConfigEnabledParam
return ThinkingConfigEnabledParam(type="enabled", budget_tokens=budget)
```
