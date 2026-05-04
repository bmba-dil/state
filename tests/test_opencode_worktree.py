"""Tests for state_core.opencode_worktree — OpencodeHTTPWorktreeService."""

from __future__ import annotations

import json as _json

import pytest
from pytest_httpx import HTTPXMock

from state_core.opencode_worktree import OpencodeHTTPWorktreeService
from state_core.worktree import WorktreeService

BASE_URL = "http://127.0.0.1:17495"


@pytest.fixture
def service() -> OpencodeHTTPWorktreeService:
    import httpx

    client = httpx.AsyncClient()
    return OpencodeHTTPWorktreeService(client=client, opencode_url=BASE_URL)


@pytest.mark.asyncio
async def test_protocol_conformance(service: OpencodeHTTPWorktreeService) -> None:
    """OpencodeHTTPWorktreeService satisfies WorktreeService Protocol."""
    assert isinstance(service, WorktreeService)


@pytest.mark.asyncio
async def test_create_sends_post_and_parses_response(
    service: OpencodeHTTPWorktreeService, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/worktree",
        json={
            "name": "slice/a-1/p-2/s-3",
            "path": "/tmp/worktrees/slice-3",
            "branch": "feature/x",
            "locked": False,
            "prunable": False,
        },
        status_code=200,
    )

    info = await service.create(name="slice/a-1/p-2/s-3", branch="feature/x")

    assert info.name == "slice/a-1/p-2/s-3"
    assert info.path == "/tmp/worktrees/slice-3"
    assert info.branch == "feature/x"
    assert info.locked is False

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "POST"
    body = _json.loads(requests[0].content)
    assert body == {"name": "slice/a-1/p-2/s-3", "branch": "feature/x"}


@pytest.mark.asyncio
async def test_list_with_results(
    service: OpencodeHTTPWorktreeService, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/worktree",
        json=[
            {"name": "wt-1", "path": "/tmp/wt-1", "branch": "main", "locked": False, "prunable": False},
            {"name": "wt-2", "path": "/tmp/wt-2", "branch": "develop", "locked": True, "prunable": False},
        ],
        status_code=200,
    )

    result = await service.list()

    assert len(result) == 2
    assert result[0].name == "wt-1"
    assert result[0].branch == "main"
    assert result[1].name == "wt-2"
    assert result[1].locked is True


@pytest.mark.asyncio
async def test_list_empty(
    service: OpencodeHTTPWorktreeService, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE_URL}/worktree",
        json=[],
        status_code=200,
    )

    result = await service.list()

    assert result == []


@pytest.mark.asyncio
async def test_remove_sends_delete(
    service: OpencodeHTTPWorktreeService, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{BASE_URL}/worktree/slice/a-1/p-2/s-3",
        status_code=204,
    )

    await service.remove("slice/a-1/p-2/s-3")

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "DELETE"


@pytest.mark.asyncio
async def test_remove_handles_404(
    service: OpencodeHTTPWorktreeService, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{BASE_URL}/worktree/missing-wt",
        status_code=404,
    )

    await service.remove("missing-wt")


@pytest.mark.asyncio
async def test_reset_sends_post(
    service: OpencodeHTTPWorktreeService, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/worktree/slice/a-1/reset",
        status_code=200,
    )

    await service.reset("slice/a-1")

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "POST"


@pytest.mark.asyncio
async def test_reset_handles_404(
    service: OpencodeHTTPWorktreeService, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/worktree/missing-wt/reset",
        status_code=404,
    )

    await service.reset("missing-wt")
