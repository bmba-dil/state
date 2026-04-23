"""ProviderRouter: resolves model calls to litellm or direct SDK."""

from __future__ import annotations


class ProviderRouter:
    """Routes provider calls — litellm default, Anthropic SDK for extended thinking."""

    async def route(self, model_spec: dict) -> object: ...
