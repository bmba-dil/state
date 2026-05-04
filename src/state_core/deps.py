"""Daemon-level dependency container.

Holds shared resources created once at startup and injected into
every subsystem that needs them.  Currently: the shared httpx.AsyncClient
for provider inference traffic.

Usage (daemon startup)::

    from state_core.http_client import build_shared_client
    from state_core.deps import Deps

    deps = Deps(http_client=build_shared_client())
    # inject deps into subsystems...
    # on shutdown:
    await deps.aclose()

Scope: provider inference only.  Auth provider OAuth flows
(state_core.auth.providers.*) use per-call httpx.AsyncClient — do NOT
pass deps.http_client to those paths.
"""

from __future__ import annotations

import httpx
from pydantic import BaseModel, ConfigDict


class Deps(BaseModel):
    """Daemon-level shared resources. Created once at startup; injected everywhere.

    Fields:
        http_client: The daemon-wide shared httpx.AsyncClient.
                     Used by litellm (via litellm.aclient_session) and
                     the direct Anthropic SDK escape hatch (Phase 025, via
                     AsyncAnthropic(http_client=deps.http_client)).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    http_client: httpx.AsyncClient

    async def aclose(self) -> None:
        """Gracefully close all held resources.

        Call this during daemon shutdown to release OS socket descriptors
        and avoid asyncio ResourceWarning about unclosed client sessions.
        """
        await self.http_client.aclose()
