# Phase 036: Transactional Bootstrap - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Transactional bootstrap: branch + worktree dir + `.state/` inheritance atomic. Rollback via compensation if any step fails. Per WRK-03 and WRK-01. When a Slice is opened, a worktree is bootstrapped atomically — if any step fails (branch creation, worktree creation, `.state/` linking), all partial state is rolled back.
</domain>

<decisions>
### AI's Discretion
All at AI's discretion.

### Key Constraints
- Uses WorktreeService Protocol (any adapter)
- Three-step transaction: create branch → create worktree → link .state
- Compensation: if any step fails, undo previous steps
- `.state/` inheritance: copy/mount `.state/` from parent repo into worktree
</decisions>

<code_context>
- `src/state_core/worktree.py` — WorktreeService Protocol
- `src/state_core/opencode_worktree.py` — opencode adapter
- `src/state_core/pygit2_worktree.py` — pygit2 fallback
- `src/state_core/worktree_naming.py` — naming module (Phase 035)
</code_context>

<specifics>
### Specific Ideas

`WorktreeBootstrapper` class:
- `bootstrap(service, arc_id, phase_id, slice_id, parent_path) -> WorktreeInfo`
- Step 1: Create branch via format_branch
- Step 2: Create worktree via service.create
- Step 3: Copy/link .state/ directory
- On failure: undo steps (remove worktree, remove branch)
- Uses worktree_naming for deterministic names
</specifics>
