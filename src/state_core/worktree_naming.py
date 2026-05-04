"""Deterministic worktree branch naming per WRK-05.

Branch naming convention: ``slice/<arc-id>/<phase-id>/<slice-id>``.

Functions:
  format_branch(arc, phase, slice)  → deterministic branch name
  format_worktree_name(arc, phase, slice)  → same as branch name
  find_collision(service, arc, phase, slice)  → check if name already in use
"""

from __future__ import annotations

import re

from state_core.worktree import WorktreeService

BRANCH_PREFIX = "slice"

_SANITIZE_RE = re.compile(r"[^a-z0-9-]+")


def _sanitize_id(raw: str) -> str:
    """Sanitize a component ID for use in a branch name.

    Rules: lowercase, replace non-alphanumeric/dash with dash,
    collapse multiple dashes, strip leading/trailing dashes.
    """
    slug = raw.lower()
    slug = _SANITIZE_RE.sub("-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def format_branch(arc_id: str, phase_id: str, slice_id: str) -> str:
    """Produce a deterministic branch name per WRK-05.

    Returns ``slice/<sanitized-arc>/<sanitized-phase>/<sanitized-slice>``.
    """
    arc = _sanitize_id(arc_id)
    phase = _sanitize_id(phase_id)
    slc = _sanitize_id(slice_id)
    return f"{BRANCH_PREFIX}/{arc}/{phase}/{slc}"


def format_worktree_name(arc_id: str, phase_id: str, slice_id: str) -> str:
    """Produce a deterministic worktree name.

    Worktree names are identical to branch names by convention.
    """
    return format_branch(arc_id, phase_id, slice_id)


async def find_collision(
    service: WorktreeService,
    arc_id: str,
    phase_id: str,
    slice_id: str,
) -> bool:
    """Check whether a worktree with the target name already exists."""
    target = format_worktree_name(arc_id, phase_id, slice_id)
    worktrees = await service.list()
    return any(wt.name == target for wt in worktrees)
