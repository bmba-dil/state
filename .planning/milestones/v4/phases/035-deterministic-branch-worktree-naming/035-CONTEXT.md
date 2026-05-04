# Phase 035: Deterministic Branch + Worktree Naming - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Name generator with collision detection for the worktree branch naming convention: `slice/<arc-id>/<product-phase-id>/<slice-id>` per WRK-05. Must be deterministic — same inputs always produce the same name. Handles collision detection when a worktree already exists with the target name.

</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
All implementation choices at AI's discretion.

### Key Constraints
- Deterministic naming: same arc/phase/slice IDs → same branch name
- Naming template: `slice/{arc_id}/{phase_id}/{slice_id}` per WRK-05
- Slashes in name must work with pygit2 (Phase 034 handles this)
- Collision detection via existing WorktreeService.list()
- No external dependencies — pure string manipulation
</decisions>

<code_context>
## Existing Code Insights
- `src/state_core/worktree.py` — WorktreeService Protocol, WorktreeInfo model
- `src/state_core/pygit2_worktree.py` — handles slashes in worktree names
- WRK-05: "Branch naming: `slice/<arc>/<phase>/<slice-id>` deterministic"
</code_context>

<specifics>
## Specific Ideas

`worktree_naming.py` module with:
- `format_branch(arc_id, phase_id, slice_id) -> str` — produces `slice/{arc_id}/{phase_id}/{slice_id}`
- `format_worktree_name(arc_id, phase_id, slice_id) -> str` — same format (names = branch names for worktrees)
- `find_collision(service, arc_id, phase_id, slice_id) -> bool` — checks if name already in use
- Sanitization of IDs (replace spaces, special chars with dashes)
</specifics>

<deferred>
## Deferred Ideas
None
</deferred>
