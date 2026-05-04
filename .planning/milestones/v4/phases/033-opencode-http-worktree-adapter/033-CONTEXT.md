# Phase 033: Opencode-HTTP Worktree Adapter - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Implement the opencode-HTTP worktree adapter: `POST /worktree` via the shared opencode HTTP client, subscribe to `worktree.ready`/`worktree.failed` bus events. This is the preferred worktree path (WRK-02) — the pygit2 fallback (Phase 034) is secondary.

The adapter implements the `WorktreeService` Protocol from Phase 032 using the opencode HTTP API.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

### Key Constraints
- Implements `WorktreeService` Protocol structurally
- Uses shared `httpx.AsyncClient` from `state_core.deps`
- Communicates with opencode's worktree HTTP API
- Follows existing patterns: `state_core.http_client`, `state_core.deps`
- Opencode HTTP client base URL from `state_core.config`
</decisions>

<code_context>
## Existing Code Insights

- `src/state_core/worktree.py` — `WorktreeService` Protocol (just completed Phase 032)
- `src/state_core/http_client.py` — `build_shared_client()` for httpx.AsyncClient
- `src/state_core/config.py` — Opencode config discovery / URL resolution
- `src/state_core/deps.py` — Daemon-level Deps container with shared AsyncClient
- `.planning/research/ARCHITECTURE.md §6.2` — Worktree lifecycle (create → bootstrap → assign Steps → destroy/revert)
</code_context>

<specifics>
## Specific Ideas

OpencodeHTTPWorktreeService adapter:
- Constructor takes `httpx.AsyncClient` and `opencode_url: str`
- `create(name, branch)` → `POST {opencode_url}/api/worktree` with JSON body
- `list()` → `GET {opencode_url}/api/worktree`
- `remove(name)` → `DELETE {opencode_url}/api/worktree/{name}`
- `reset(name)` → `POST {opencode_url}/api/worktree/{name}/reset`
- Parse responses into `WorktreeInfo` pydantic models
- Handle opencode-unreachable with retries (exponential backoff)
- Subscribe to `worktree.ready`/`worktree.failed` SSE events via shared client

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
