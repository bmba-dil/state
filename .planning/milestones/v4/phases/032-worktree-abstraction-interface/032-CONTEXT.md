# Phase 032: Worktree Abstraction Interface - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Create `state_core.worktree.WorktreeService` with `create/list/remove/reset` methods and host-agnostic signature. The Protocol defines the contract that both the opencode-HTTP adapter (Phase 033) and pygit2 fallback adapter (Phase 034) implement.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices are at AI's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Key Constraints
- Protocol class (like existing `AuthMethod` Protocol in `auth/base.py` and existing `WorktreeService` Protocol stub in `worktree.py`)
- Host-agnostic: no opencode or pygit2 imports
- Async methods throughout
- Follows existing patterns in `src/state_core/`

</decisions>

<code_context>
## Existing Code Insights

- `src/state_core/worktree.py` — 12-line `WorktreeService` Protocol stub with `create` and `remove` signatures
- `src/state_core/auth/base.py` — `AuthMethod` Protocol reference pattern
- `src/state_core/schema.py` — `SliceWorktreeReady` event schema
- Database: `slices` table has `worktree_dir TEXT` and `worktree_branch TEXT` columns
- Architectural decisions documented in `.planning/research/ARCHITECTURE.md §6.2`

</code_context>

<specifics>
## Specific Ideas

Host-agnostic WorktreeService Protocol must define:
- `create(name, branch) -> worktree_path` — create a worktree
- `list() -> list[WorktreeInfo]` — list all worktrees
- `remove(name) -> None` — remove a worktree (prune)
- `reset(name) -> None` — reset worktree to clean state

Return types should be pydantic models (`WorktreeInfo`) matching project conventions.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
