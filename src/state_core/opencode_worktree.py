"""Opencode-HTTP worktree adapter.

Implements the WorktreeService Protocol (Phase 032) via opencode's
HTTP API. This is the preferred worktree path (WRK-02). The pygit2
fallback (Phase 034) is used when opencode is unreachable.

Lifecycle:
  1. Daemon creates one adapter per Deps container.
  2. Adapter uses the shared httpx.AsyncClient to call opencode endpoints.
  3. On opencode-unreachable, the caller falls back to pygit2.

HTTP endpoints (opencode):
  POST   /worktree              — create a new worktree
  GET    /worktree              — list all worktrees
  DELETE /worktree/{name}       — remove a worktree
  POST   /worktree/{name}/reset — reset worktree to clean state
"""

from __future__ import annotations

import httpx
import structlog

from state_core.worktree import WorktreeInfo

log = structlog.get_logger(__name__)

WORKTREE_PATH = "/worktree"


class OpencodeHTTPWorktreeService:
    """Opencode-HTTP implementation of the WorktreeService Protocol."""

    def __init__(self, client: httpx.AsyncClient, opencode_url: str) -> None:
        self._client = client
        self._base_url = opencode_url.rstrip("/")

    def _url(self, path: str | None = None) -> str:
        base = f"{self._base_url}{WORKTREE_PATH}"
        if path:
            return f"{base}/{path.lstrip('/')}"
        return base

    async def create(self, name: str, branch: str) -> WorktreeInfo:
        url = self._url()
        payload = {"name": name, "branch": branch}
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return WorktreeInfo(**data)

    async def list(self) -> list[WorktreeInfo]:
        url = self._url()
        response = await self._client.get(url)
        response.raise_for_status()
        data = response.json()
        return [WorktreeInfo(**item) for item in data]

    async def remove(self, name: str) -> None:
        url = self._url(name)
        response = await self._client.delete(url)
        if response.status_code == 404:
            log.debug("worktree not found, nothing to remove", name=name)
            return
        response.raise_for_status()

    async def reset(self, name: str) -> None:
        url = f"{self._url(name)}/reset"
        response = await self._client.post(url)
        if response.status_code == 404:
            log.debug("worktree not found, nothing to reset", name=name)
            return
        response.raise_for_status()
