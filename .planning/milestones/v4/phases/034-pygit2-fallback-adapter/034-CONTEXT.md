# Phase 034: pygit2 Fallback Adapter - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Implement the pygit2 fallback worktree adapter. Uses `pygit2.Repository.add_worktree()`, `list_worktrees()`, `Worktree.prune()` when opencode is unavailable (non-opencode hosts). This is the secondary path per WRK-02.

Out-of-tree `state-snapshots` ref namespace for snapshots — worktrees live in `.git/worktrees/` with branches in `refs/heads/slice/...`.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

### Key Constraints
- Implements `WorktreeService` Protocol structurally
- Uses `pygit2` (already in pyproject.toml dependencies)
- Works with local git repository only (path-based)
- Branch naming: `slice/<arc-id>/<product-phase-id>/<slice-id>` (WRK-05)
- `state-snapshots` ref namespace for snapshot objects
</decisions>

<code_context>
## Existing Code Insights
- `src/state_core/worktree.py` — `WorktreeService` Protocol
- `src/state_core/opencode_worktree.py` — OpencodeHTTP adapter (reference)
- `pyproject.toml` — `pygit2>=1.19.2` available
- `.planning/research/STACK.md` — pygit2 preferred, GitPython rejected, subprocess.run() rejected
</code_context>

<specifics>
## Specific Ideas

`Pygit2WorktreeService` adapter:
- Constructor takes `repo_path: str | Path`
- Opens `pygit2.Repository` internally
- `create(name, branch)` → `repo.add_worktree(name, path)` + checkout branch
- `list()` → iterate `repo.list_worktrees()`, return WorktreeInfo list
- `remove(name)` → `Worktree.prune()` + cleanup
- `reset(name)` → hard reset + clean

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>
