# Phase 111: shared-library-wiring — Context

**Gathered:** 2026-05-05
**Status:** Complete — infrastructure (discuss skipped)
**Mode:** Infrastructure

<domain>
Tool impls call state_core helpers; no duplicate auth/provider logic.

Wired state_core.auth, state_core.events, and state_core.scheduler imports into state_build.mcp. dag_status instantiates real DAGScheduler.
</domain>
