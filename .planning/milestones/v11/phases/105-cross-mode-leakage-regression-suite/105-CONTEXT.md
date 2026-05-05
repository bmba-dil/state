# Phase 105: Cross-mode leakage regression suite - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

P0-11 test suite: attempt every illegal combination, assert rejection at canonical gate.

**Goal:** Comprehensive regression test suite that attempts every illegal cross-mode operation and verifies it is rejected at the canonical gate (daemon middleware). Covers all 6 layers of mode enforcement. This is the final validation phase.
</domain>

<decisions>
All at AI's discretion. Test all illegal combinations: build mode + teach event, teach mode + build command, cross-subtree writes, etc.
</decisions>

<code_context>
All 6 layers from Phases 097-104 are implemented:
1. mode.json schema (097)
2. Directory presence (098)
3. MCP registration (099)
4. Plugin hook gate (100)
5. Daemon HTTP middleware (101)
6. Import-graph lint (102)
</code_context>

<specifics>
Implement per ROADMAP phase goal and TST-08 requirement. Depends on all prior phases (097-104).
</specifics>

<deferred>
None.
</deferred>
