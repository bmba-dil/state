# Phase 037: Orphan Worktree GC - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Orphan-worktree GC (nightly daemon task). Scans `.git/worktrees/*/locked`, stale branch names, removes orphaned worktrees. Never swallows errors. Per P0-10 defence.
</domain>

<decisions>
### AI's Discretion
All at AI's discretion. Key constraint: P0-10 — never silently swallow errors.
</decisions>

<code_context>
- src/state_core/worktree.py — WorktreeService Protocol
- src/state_core/pygit2_worktree.py — pygit2 layer for direct .git/worktrees access
</code_context>

<specifics>
### Specific Ideas
`WorktreeGC` class:
- `collect(service) -> list[WorktreeInfo]` — identify orphaned worktrees
- `prune(service, dry_run=False) -> list[WorktreeInfo]` — gc orphaned worktrees
- Orphan criteria: locked file present AND branch deleted, or worktree dir missing
- Daemon calls this periodically (nightly task)
</specifics>
