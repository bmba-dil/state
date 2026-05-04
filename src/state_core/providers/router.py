"""ProviderRouter: credential-type-driven routing guard (PRV-03).

OAuthCredential (sk-ant-oat* tokens) -> AnthropicClient (direct SDK, stealth headers).
Any other credential type -> LitellmClient (litellm abstraction).

The routing decision is type-based, not string-based:
  isinstance(cred, OAuthCredential)  <-- primary discriminator
  NOT cred.access.startswith("sk-ant-oat")  <-- string prefix is documentation only

select() is sync and cheap — AnthropicClient construction does no I/O
(it reuses the shared httpx.AsyncClient from deps). Call select() per
inference request; do not cache the returned client across credential refreshes.

Downstream consumers:
  Phase 027 — model-profile resolver passes (cred, deps, model_profile) to select()
  Phase 028 — cost accounting wraps select() to emit request events
  Phase 031 — parity matrix tests call select() per provider in the matrix

Security (T-026-1): logs contain provider_id and route only. Never log
cred.access, cred.key, or any other credential secret.
"""

from __future__ import annotations

import structlog

from state_core.auth.base import Credential, OAuthCredential
from state_core.deps import Deps
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.litellm_client import LitellmClient

log = structlog.get_logger(__name__)


class ProviderRouter:
    """Routes inference calls — litellm default, Anthropic SDK for OAuth stealth.

    PRV-03: OAuthCredential -> AnthropicClient (always; bypass guard).
    ApiKeyCredential (any provider) -> LitellmClient.

    Usage::

        router = ProviderRouter()
        client = router.select(cred, deps)
        # client is AnthropicClient | LitellmClient
        response = await client.create(model=..., messages=..., max_tokens=...)
    """

    def select(self, cred: Credential, deps: Deps) -> AnthropicClient | LitellmClient:
        """Return the inference client for the given credential (PRV-03).

        OAuthCredential -> AnthropicClient (direct SDK, stealth headers applied).
        Any other credential type -> LitellmClient (litellm abstraction).

        This method is sync — no I/O occurs during client construction.
        AnthropicClient reuses deps.http_client (shared pool, no new connections).
        LitellmClient is stateless (no constructor args).

        Args:
            cred: Credential to route. OAuthCredential routes to direct SDK;
                  ApiKeyCredential routes to litellm.
            deps: Daemon-level shared resources (http_client).

        Returns:
            AnthropicClient if cred is OAuthCredential.
            LitellmClient for all other credential types.
        """
        if isinstance(cred, OAuthCredential):
            log.debug(
                "provider_router.select",
                route="anthropic_sdk",
                provider_id=cred.provider_id,
                # NEVER log cred.access — T-026-1 secret hygiene
            )
            return AnthropicClient(cred, deps)
        log.debug(
            "provider_router.select",
            route="litellm",
            provider_id=cred.provider_id,
            # NEVER log cred.key — T-026-1 secret hygiene
        )
        return LitellmClient()
