# Phase 076: chat.params + chat.headers Hook - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Inject model profile resolution (from v3.P5), cache-control markers, and thinking budget. Depends on 068 (package scaffolding) and 027 (model-profile resolver).
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.
</decisions>

<code_context>
## Existing Code Insights

- opencode plugin API: `chat.params` hook modifies model parameters (model, thinking budget)
- opencode plugin API: `chat.headers` hook injects custom HTTP headers
- v3 model profiles: quality (claude-opus-4), balanced (claude-sonnet-4), budget (haiku)
- Environment variables: STATE_MODEL_PROFILE, STATE_THINKING_BUDGET
</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.
</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.
</deferred>
