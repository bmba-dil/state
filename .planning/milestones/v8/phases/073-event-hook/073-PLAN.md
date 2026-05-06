---
phase: "073"
phase_name: "event Hook"
goal: "Subscribe to opencode events and mirror to daemon via SSE"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-05]
status: deferred
deferred_reason: "event key not in opencode Hooks type (v1.14.35)"
---

## Plan 1: Implement `event` Hook

**Status: Deferred.** The `event` hook does not exist in opencode's `Hooks` type as of v1.14.35. This plan is a placeholder. When the API supports it, a follow-up phase will implement:

1. Subscribe to opencode events (`session.idle`, `worktree.ready`, `question.replied`, `permission.replied`)
2. Mirror events to daemon via HTTP POST to `/events/mirror`
3. Utility module for SSE mirroring that other hooks can call in the interim

### Verification Criteria (must_haves)
- [ ] Subscribe to opencode events — DEFERRED (API gap)
- [ ] Mirror to daemon — DEFERRED (API gap)
