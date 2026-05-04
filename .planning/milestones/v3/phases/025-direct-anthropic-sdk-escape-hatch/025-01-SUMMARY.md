---
phase: 025-direct-anthropic-sdk-escape-hatch
plan: 01
subsystem: providers
tags: [anthropic, httpx, oauth, stealth-headers, extended-thinking, cache-control, tdd, pytest-httpx]

requires:
  - phase: 023-shared-httpx-asyncclient-connection-pool
    provides: "Deps container with shared httpx.AsyncClient"
  - phase: 014-anthropic-oauth-stealth
    provides: "AnthropicAuth.http_headers() stealth header builder"
provides:
  - "18 RED test stubs defining AnthropicClient and errors.py API contracts (Wave 0)"
  - "tests/test_anthropic_client.py — failing with ImportError until Wave 1 creates implementations"
affects:
  - 025-02 (Wave 1 GREEN implementation must satisfy all 18 contracts)

tech-stack:
  added: []
  patterns:
    - "Wave 0 RED stubs: top-level imports fail unconditionally, no try/except, no importorskip"
    - "pytest-httpx HTTPXMock at transport layer: intercepts AsyncAnthropic requests because shared httpx.AsyncClient is injected"
    - "FAKE_OAUTH_CRED / FAKE_API_KEY_CRED as module-level constants using actual credential classes"

key-files:
  created:
    - tests/test_anthropic_client.py
  modified: []

key-decisions:
  - "Used unittest.mock.patch on client._sdk.messages.create for test_stream_thinking_delta_yielded to avoid SSE byte-encoding complexity in RED stubs"
  - "test_does_not_close_shared_client constructs a real httpx.AsyncClient (not mocked) so is_closed is a real property"
  - "All 4 security threats (T-025-1..T-025-4) have dedicated test functions verifying mitigation contracts"

patterns-established:
  - "Wave 0 structure: module docstring → module-level imports (no try/except) → FAKE_* constants → fixtures → test sections by requirement group"

requirements-completed:
  - PRV-02
  - PRV-08
  - PRV-09
---

# Phase 025 Plan 01: AnthropicClient RED Stubs Summary

**18 RED test stubs defining the AnthropicClient escape hatch contract — OAuth stealth headers, extended thinking, cache-control, and error mapping — all failing with ImportError until Wave 1 creates the implementations.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-03T16:35:00Z
- **Completed:** 2026-05-03T16:55:04Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- 18 RED test stubs written in `tests/test_anthropic_client.py` organized by requirement group (PRV-02, PRV-08, PRV-09)
- All 4 security threats (T-025-1 through T-025-4) have dedicated test coverage contracts defined
- Collection fails with `ModuleNotFoundError: No module named 'state_core.providers.errors'` — correct RED state confirmed
- Fixed worktree branch rebase issue: restored Phase 023/024 files (deps.py, http_client.py, litellm_client.py) that were staged as deleted after `git reset --soft`

## Task Commits

1. **Task 1: Write 18 RED test stubs for AnthropicClient** - `5e26bc1` (test)

## Files Created/Modified

- `tests/test_anthropic_client.py` — 511 lines, 18 async/sync test stubs for PRV-02 (transport, stealth headers, lifecycle, error mapping, import graph), PRV-08 (thinking), PRV-09 (cache-control) and streaming thinking delta

## Decisions Made

- Used `unittest.mock.patch` on `client._sdk.messages.create` for `test_stream_thinking_delta_yielded` rather than SSE byte-encoding, as recommended by the plan's action section — simpler and avoids transport-layer SSE complexity
- Constructed a real `httpx.AsyncClient()` (not a mock) for `test_does_not_close_shared_client` so `is_closed` is the real property, not a mock attribute
- Module-level `FAKE_OAUTH_CRED` and `FAKE_API_KEY_CRED` use the actual `OAuthCredential` and `ApiKeyCredential` classes (not dicts), so construction errors are caught at import time

## Deviations from Plan

None — plan executed exactly as written. The worktree rebase/reset issue was a pre-execution setup concern, not a task deviation.

## Issues Encountered

**Worktree branch rebase issue:** The worktree was based on an older commit than the required `7667497`. After `git reset --soft` to set HEAD correctly, the working tree had Phase 023/024 source files staged as deleted (`deps.py`, `http_client.py`, `litellm_client.py`, `test_litellm_client.py`, etc.) because the original worktree HEAD predated those commits. Resolved with `git checkout HEAD -- <files>` to restore the working tree to match the new HEAD. This was required for the pytest collection to fail on the correct module (`state_core.providers.errors`) rather than `state_core.deps`.

## Next Phase Readiness

- Wave 1 (025-02-PLAN.md) can now proceed: create `src/state_core/providers/errors.py` and `src/state_core/providers/anthropic_client.py` to turn all 18 RED stubs GREEN
- Test function names in this file exactly match the identifiers in `025-VALIDATION.md`'s per-task verification map

---
*Phase: 025-direct-anthropic-sdk-escape-hatch*
*Completed: 2026-05-03*
