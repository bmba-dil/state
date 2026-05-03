"""Direct Anthropic SDK escape hatch for OAuth stealth inference (PRV-02).

Use AnthropicClient for all sk-ant-oat* (OAuth) credentials. The litellm
path (Phase 024) does not support Anthropic-native features: extended
thinking (PRV-08) and fine-grained cache-control (PRV-09).

Construction: AnthropicClient(cred, deps)
  - OAuthCredential  -> stealth headers, X-Api-Key suppressed
  - ApiKeyCredential -> standard X-Api-Key header

Lifecycle rules (CRITICAL):
  - NEVER call deps.http_client.aclose() — lifecycle owned by Deps
  - NEVER call self._sdk.close() — shares the same httpx client
  - max_retries=0 on AsyncAnthropic — State owns retry via ProviderTransientError

Phase 026 (ProviderRouter) selects AnthropicClient for OAuth credentials;
Phase 029 (thinking budget propagation) and Phase 030 (cache-control e2e)
consume this client's create() and stream() methods.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator
from typing import Any

import anthropic
from anthropic import omit
from anthropic.types import Message, RawMessageStreamEvent
from anthropic.types.cache_control_ephemeral_param import CacheControlEphemeralParam
from anthropic.types.thinking_config_param import ThinkingConfigParam
import structlog

from state_core.auth.base import ApiKeyCredential, Credential, OAuthCredential
from state_core.auth.providers.anthropic import AnthropicAuth, inject_stealth_system_prefix
from state_core.deps import Deps
from state_core.providers.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderTransientError,
    StateProviderError,
)

log = structlog.get_logger(__name__)


class AnthropicClient:
    """Direct Anthropic SDK escape hatch for OAuth stealth inference (PRV-02).

    One instance per (credential, deps) pair. Cheap to create; the SDK
    client is built once in __init__ and reused across calls.
    """

    def __init__(self, cred: Credential, deps: Deps) -> None:
        self._cred = cred
        self._deps = deps
        self._sdk = self._build_sdk(cred, deps)

    def _build_sdk(self, cred: Credential, deps: Deps) -> anthropic.AsyncAnthropic:
        """Build AsyncAnthropic with correct auth strategy for the credential type."""
        if isinstance(cred, OAuthCredential):
            stealth = AnthropicAuth().http_headers(cred)
            # stealth keys: "authorization" (handled by auth_token=), "user-agent", "x-app", "anthropic-beta"
            return anthropic.AsyncAnthropic(
                auth_token=cred.access,
                api_key=None,
                http_client=deps.http_client,
                default_headers={
                    # Suppress X-Api-Key even if ANTHROPIC_API_KEY env var is set.
                    # SDK env fallback: api_key=None -> os.environ.get("ANTHROPIC_API_KEY").
                    # _merge_mappings removes Omit values after auth_headers built (T-025-2).
                    "X-Api-Key": omit,
                    # Use "User-Agent" (same casing as SDK's default_headers key) so Python
                    # dict merge overwrites the SDK's "AsyncAnthropic/Python x.y.z" value
                    # instead of creating a duplicate key that httpx would concatenate.
                    "User-Agent": stealth["user-agent"],
                    "x-app": stealth["x-app"],
                    "anthropic-beta": stealth["anthropic-beta"],
                },
                default_query={"beta": "true"},
                max_retries=0,
            )
        elif isinstance(cred, ApiKeyCredential):
            return anthropic.AsyncAnthropic(
                api_key=cred.key,
                http_client=deps.http_client,
                default_query={"beta": "true"},
                max_retries=0,
            )
        else:
            raise TypeError(
                f"AnthropicClient: unsupported credential type {type(cred).__name__}. "
                "Expected OAuthCredential or ApiKeyCredential."
            )

    async def create(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        thinking: ThinkingConfigParam | None = None,
        cache_control: CacheControlEphemeralParam | None = None,
        system: str | list[Any] | None = None,
        **kwargs: Any,
    ) -> Message:
        """Non-streaming inference via direct Anthropic SDK (PRV-02).

        Args:
            model:         Anthropic model string (e.g. "claude-opus-4-5-20241022").
            messages:      OpenAI-format message list.
            max_tokens:    Maximum tokens in response.
            thinking:      ThinkingConfigParam for extended thinking (PRV-08).
                           Pass {"type": "enabled", "budget_tokens": N} or {"type": "adaptive"}.
                           If budget_tokens >= max_tokens, raises ProviderBadRequestError.
            cache_control: CacheControlEphemeralParam for fine-grained caching (PRV-09).
                           Pass {"type": "ephemeral", "ttl": "5m"} or {"ttl": "1h"}.
            system:        System prompt. OAuthCredential path prepends Claude-Code prefix.
            **kwargs:      Passed through to messages.create() (e.g. temperature, tools).

        Returns:
            Full anthropic.types.Message. Callers (Phase 028) read
            response.usage.cache_creation_input_tokens and cache_read_input_tokens.

        Raises:
            ProviderTransientError: APIConnectionError, APITimeoutError, RateLimitError, 5xx.
            ProviderAuthError: AuthenticationError (401), PermissionDeniedError (403).
            ProviderBadRequestError: BadRequestError (400), thinking budget constraint violated.
            StateProviderError: other APIStatusError not covered above.
        """
        # Stealth system prefix for OAuth credentials only (T-025-3).
        if isinstance(self._cred, OAuthCredential):
            body: dict[str, Any] = {"system": system}
            inject_stealth_system_prefix(body)
            system = body["system"]

        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if thinking is not None:
            create_kwargs["thinking"] = thinking
        if cache_control is not None:
            create_kwargs["cache_control"] = cache_control
        if system is not None:
            create_kwargs["system"] = system

        log.debug("anthropic_client.create", model=model, max_tokens=max_tokens)
        try:
            return await self._sdk.messages.create(**create_kwargs)
        except anthropic.APIConnectionError as e:
            log.warning("anthropic_client.connection_error", error=str(e))
            raise ProviderTransientError(f"connection: {e}") from e
        except anthropic.RateLimitError as e:
            log.warning("anthropic_client.rate_limit", error=str(e))
            raise ProviderTransientError(f"rate_limit: {e}") from e
        except anthropic.AuthenticationError as e:
            log.warning("anthropic_client.auth_error", status=e.status_code)
            raise ProviderAuthError(f"auth {e.status_code}: {e}") from e
        except anthropic.PermissionDeniedError as e:
            log.warning("anthropic_client.permission_denied", status=e.status_code)
            raise ProviderAuthError(f"permission {e.status_code}: {e}") from e
        except anthropic.BadRequestError as e:
            log.warning("anthropic_client.bad_request", status=e.status_code)
            raise ProviderBadRequestError(f"bad_request: {e}") from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                log.warning("anthropic_client.server_error", status=e.status_code)
                raise ProviderTransientError(f"server_error {e.status_code}: {e}") from e
            log.warning("anthropic_client.api_error", status=e.status_code)
            raise StateProviderError(f"api_error {e.status_code}: {e}") from e

    async def stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        thinking: ThinkingConfigParam | None = None,
        cache_control: CacheControlEphemeralParam | None = None,
        system: str | list[Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[RawMessageStreamEvent, None]:
        """Streaming inference via direct Anthropic SDK (PRV-02).

        Yields RawMessageStreamEvent objects unchanged. For thinking blocks,
        events include RawContentBlockDeltaEvent with delta.type="thinking_delta".
        For cache accounting (PRV-09), the final RawMessageDeltaEvent contains usage.

        Use messages.create(stream=True) NOT messages.stream() — the latter
        accumulates events (loses raw thinking deltas and streaming cache usage).

        Raises:
            ProviderTransientError: APIConnectionError at stream setup.
            ProviderBadRequestError: BadRequestError at stream setup.
            StateProviderError: other errors at setup or during iteration.
        """
        if isinstance(self._cred, OAuthCredential):
            body: dict[str, Any] = {"system": system}
            inject_stealth_system_prefix(body)
            system = body["system"]

        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }
        if thinking is not None:
            create_kwargs["thinking"] = thinking
        if cache_control is not None:
            create_kwargs["cache_control"] = cache_control
        if system is not None:
            create_kwargs["system"] = system

        try:
            # The SDK's @required_args decorator makes messages.create not detected as
            # a coroutine function by inspect. At runtime it IS async; we use
            # inspect.isawaitable to handle both the real SDK (returns coroutine)
            # and test mocks (return AsyncGenerator directly without an await step).
            raw = self._sdk.messages.create(**create_kwargs)
            response = await raw if inspect.isawaitable(raw) else raw
        except anthropic.APIConnectionError as e:
            raise ProviderTransientError(f"connection: {e}") from e
        except anthropic.BadRequestError as e:
            raise ProviderBadRequestError(f"bad_request: {e}") from e
        except Exception as e:
            raise StateProviderError(f"stream_setup: {e}") from e

        try:
            async for event in response:
                yield event
        except Exception as e:
            log.warning("anthropic_client.stream_iter_error", error=str(e))
            raise StateProviderError(f"stream_error: {e}") from e
