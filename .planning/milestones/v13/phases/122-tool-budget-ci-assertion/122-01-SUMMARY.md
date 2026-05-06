---
phase: 122-tool-budget-ci-assertion
plan: 01
subsystem: state-cli
tags: [ci, tool-budget, teach-mode, assertion]
requires:
  provides: [MCP-B-06]
  affects: [phase-123]
tech-stack:
  added: []
  patterns: [cli-entry-point, ci-assertion-script]
key-files:
  created:
    - src/state_cli/__main__.py
    - scripts/ci/check-teach-tool-budget.sh
  modified:
    - tests/test_cli_tool_budget_teach.py
key-decisions:
  - "Created src/state_cli/__main__.py entry point so python -m state_cli works from CLI"
  - "Reused Phase 108 shared _SERVER_MODULES and _count_tokens infrastructure"
  - "CI script checks all 14 state-teach tool descriptions against 1200-token budget"
requirements-completed:
  - MCP-B-06
metrics:
  duration: 10m
  completed: 2026-05-05
---

# Phase 122 Plan 01: Tool-Budget CI Assertion Summary

**One-liner:** Wired `state dev tool-budget --server state-teach` CLI command with `__main__.py` entry point and CI assertion script, verifying all 14 tool descriptions within budget (114/1200 tokens).

## What Was Built

- `src/state_cli/__main__.py` — CLI entry point for `python -m state_cli`
- `scripts/ci/check-teach-tool-budget.sh` — Shell script CI assertion
- `tests/test_cli_tool_budget_teach.py` — 14 tests verifying tool budget compliance

## Self-Check: PASSED

All 14 tests pass. Tool budget totals 114 tokens (well under 1200 limit). CI script exits 0.
