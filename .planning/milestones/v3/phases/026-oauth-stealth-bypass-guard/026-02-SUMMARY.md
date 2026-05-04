---
phase: 026-oauth-stealth-bypass-guard
plan: "02"
subsystem: state_core.providers
tags: [tdd, wave-1, green, prv-03, oauth-routing, bypass-guard]
dependency_graph:
  requires: [026-01-SUMMARY.md]
  provides: [src/state_core/providers/router.py (ProviderRouter.select())]
  affects: [Phase 027 model-profile resolver, Phase 028 cost accounting, Phase 031 parity matrix]
tech_stack:
  added: []
  patterns: [isinstance-dispatch, sync-routing, structlog-secret-hygiene]
key_files:
  created: []
  modified:
    - src/state_core/providers/router.py
decisions:
  - "isinstance(cred, OAuthCredential) used as primary discriminator — NOT string prefix check — per T-026-4 pitfall avoidance"
  - "select() is def (sync), not async def — no I/O occurs during routing; AnthropicClient reuses shared httpx.AsyncClient from deps"
  - "Log calls use only provider_id and route fields — cred.access and cred.key never appear in any log statement (T-026-1)"
metrics:
  duration: "~4 minutes"
  completed: "2026-05-03"
  tasks_completed: 1
  files_changed: 1
---

# Phase 026 Plan 02: OAuth Stealth Bypass Guard — Wave 1 GREEN Summary

ProviderRouter.select() implemented — PRV-03 bypass guard active. All 10 tests GREEN. 830 total tests passing.

## What Was Built

**Task 1** — Replaced the placeholder `router.py` stub (`async def route(self, model_spec: dict) -> object: ...`) with the complete `ProviderRouter.select()` implementation:

- `isinstance(cred, OAuthCredential)` dispatch routes OAuth credentials to `AnthropicClient(cred, deps)` (direct SDK, stealth headers applied)
- All other credential types (`ApiKeyCredential`, including `provider_id="anthropic"`) route to `LitellmClient()` (litellm abstraction)
- `select()` is `def` (sync) — no I/O, cheap to call per inference request
- Logs emit only `provider_id` and `route` fields — `cred.access` and `cred.key` never appear in any log call
- No `state_build.*` or `state_teach.*` imports — mode silo enforced

## Wave 1 Result

```
10 passed in 1.21s  (tests/test_router.py)
830 passed, 2 deselected in 54.84s  (full suite)
```

Correct Wave 1 GREEN state. PRV-03 fully satisfied.

## Security Threats Addressed

| ID | Threat | Control | Status |
|----|--------|---------|--------|
| T-026-1 | OAuth token or API key leaked via structlog | `log.debug` uses only `provider_id` and `route`; credential secrets never logged | CLOSED |
| T-026-2 | OAuthCredential bypassing AnthropicClient to reach LitellmClient | `isinstance(cred, OAuthCredential)` primary gate; 10-test regression suite | CLOSED |
| T-026-3 | Mode silo violation (router imports state_build.*) | router.py imports ONLY from `state_core.*`, `structlog`, `__future__` | CLOSED |
| T-026-4 | Provider_id routing pitfall (`cred.provider_id == "anthropic"` instead of isinstance) | Code uses `isinstance(cred, OAuthCredential)` — `test_anthropic_api_key_routes_to_litellm` enforces this | CLOSED |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. The plan provided the complete implementation verbatim and the test suite from Wave 0 drove the implementation to correctness immediately.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | a33ac1f | feat(v3-026-02): implement ProviderRouter.select() — PRV-03 bypass guard GREEN |

## Verification

All 6 phase verification checks pass:

1. `python3 -m pytest tests/test_router.py -v` → 10 passed
2. `python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` → 830 passed, 2 deselected
3. `grep -n "def select\|def route" src/state_core/providers/router.py` → `def select` at line 49 (no `def route`)
4. `grep -n "class OAuthRoutingError" src/state_core/providers/errors.py` → line 51
5. `grep -n "state_build\|state_teach" src/state_core/providers/router.py` → no match
6. AST analysis of log calls → no `cred.access` or `cred.key` in any log statement

## Self-Check: PASSED

- `src/state_core/providers/router.py` exists: FOUND
- `def select` in router.py: FOUND at line 49
- `async def route` removed: CONFIRMED (no match)
- Task 1 commit a33ac1f: FOUND
- 830 tests passing: CONFIRMED
