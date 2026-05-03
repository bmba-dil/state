# Phase 012: `auth.json` vault (`store.py`) with chmod-0600 + array-per-provider - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

`os.open(..., 0o600)` + `os.fchmod`; array-shape preserved even for single credentials; refuse to proceed if mode wrong.

Owns: `.state/auth.json` storage layer (`store.py`).
Requirement: AUTH-06.
P0 pitfall owned: P0-13 (mode-permission drift / array-shape collapse).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per workflow.skip_discuss. Use ROADMAP, RESEARCH, AUTH-06 spec, P0-13 pitfall, and Phase 011's `Credential` discriminated union.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research. Key consumers:
- Phase 013 refresh.py — reads/writes auth.json under filelock
- Phase 014–018 providers — store login() output through this layer
- Phase 019 multi-cred — array-shape-preserving rotation index updates
- Phase 021 first-run import — opencode auth.json migration

</code_context>

<specifics>
## Specific Ideas

- chmod 0600 enforced on EVERY read; refuse to proceed if file mode wrong (P0-13).
- Array-per-provider shape preserved even for single credentials: `auth.json["anthropic"]` is always a list, never a bare dict.
- `os.open(path, O_CREAT | O_WRONLY | O_TRUNC, 0o600)` for atomic create-with-mode (race-free against subsequent chmod).

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
