# Phase 017: GitHub Copilot device-code flow - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Device-code endpoint polling with 15-min countdown, grant-revocation detection (200-with-null-body), pydantic validation of refresh responses.

**Depends on:** 013
**Requirements:** AUTH-04
**Parallelizable:** yes with 014, P5, P6

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions. This is the FIRST device-code flow in the project (014 = Anthropic loopback, 015 = Gemini loopback, 016 = Antigravity loopback). Research must verify the exact GitHub Copilot device-code endpoints and contracts.

</decisions>

<code_context>
## Existing Code Insights

Phase 015 shipped `state_core.auth.errors` (reusable). Phase 015's loopback module is NOT applicable here (device-code, not loopback). New device-code helper module may be warranted for code reuse if a future provider needs it. Phase 014/015/016 provider patterns are precedents for module structure (constants + Pydantic models + AuthMethod class + argparse __main__).

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
