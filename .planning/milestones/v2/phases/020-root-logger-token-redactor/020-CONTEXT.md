# Phase 020: root-logger-token-redactor - Context

**Gathered:** 2026-05-01
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Compiled regex set, applied at root logger, refuse-daemon-start if not attached.

Implements AUTH-10: a root-logger token redactor that strips secret-shaped substrings (`sk-ant-*`, `sk-*`, `ya29.*`, OAuth device codes, refresh tokens, API keys) from every log record before they reach any sink (stderr, file, structlog event-dict, JSON line). Wired as a structlog processor at process start; if not attached when the daemon boots, the daemon must refuse to start (defense against the P0-14 secret-leak pitfall).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Anchor points (from PROJECT.md cardinal rules and prior phases):
- structlog is the project logging stack — the redactor MUST be a structlog processor (NOT a stdlib logging filter, which would miss structlog event-dict values)
- mode-isolation: `state_core.observability.*` (or wherever this lives) must NOT import `state.build.*` or `state.teach.*`
- determinism: regex compilation at module-import time, no per-call compile
- secret-shape patterns from `.planning/research/PITFALLS.md` P0-14 and `state-inputs/claude-oauth.md` — match byte-for-byte
- daemon-start-refusal: a startup self-check that emits a known secret-shaped string through the root logger and asserts the rendered output does not contain it; if the assertion fails, raise a fatal error before any other initialization

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research. Likely touch points:
- `src/state_core/` (where the redactor module lives — `observability/` or `logging/` subpackage)
- `src/state_core/auth/` (callers that produce sensitive event-dict values via structlog)
- daemon startup path (wherever the structlog processor chain is configured)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.

Token shape patterns to redact (from PROJECT.md / claude-oauth.md):
- `sk-ant-oat-*` (Anthropic OAuth access tokens)
- `sk-ant-rt-*` (Anthropic OAuth refresh tokens)
- `sk-ant-api*` (Anthropic API keys)
- `sk-*` (generic OpenAI-shape API keys)
- `ya29.*` (Google OAuth tokens)
- `gho_*` / `ghu_*` / `ghs_*` / `ghp_*` (GitHub Copilot device-code tokens)
- Bearer header values when prefixed with `Bearer `
- Generic device-code shapes (8-character segments, hex token shapes ≥ 32 chars)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
