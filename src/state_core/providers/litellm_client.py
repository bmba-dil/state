"""litellm async wrapper for non-Anthropic provider traffic (PRV-01, PRV-07).

This module is the default inference path for all non-Anthropic providers.
Anthropic OAuth stealth traffic MUST NOT route through this module — use
the direct Anthropic SDK escape hatch (Phase 025) for all ``sk-ant-oat*``
credentials.  The routing decision is enforced by Phase 026's ProviderRouter.

The shared httpx.AsyncClient is already wired to ``litellm.aclient_session``
by Phase 023's orchestrator.startup().  This module calls litellm.acompletion
without passing http_client explicitly; litellm picks up aclient_session
automatically for OpenAI-compatible provider paths.

NOTE: aclient_session is best-effort — Anthropic-native model strings
(e.g. "anthropic/claude-*", "claude-*") use litellm's dedicated Anthropic
handler which does NOT honour aclient_session.  Phase 025 is the canonical
Anthropic path.

Security: Never call aclose() on the shared client — lifecycle is owned by
Deps/orchestrator (T-024-2).
"""

from __future__ import annotations

import litellm
import litellm.exceptions as lexc
import structlog
from collections.abc import AsyncGenerator
from litellm.types.utils import ModelResponse, ModelResponseStream

from state_core.providers.errors import (
    StateProviderError,
    ProviderTransientError,
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderResponseError,
)

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# LitellmClient
# ---------------------------------------------------------------------------


class LitellmClient:
    """Thin async wrapper around litellm.acompletion for non-Anthropic traffic.

    No constructor args: the shared httpx.AsyncClient is injected into litellm
    globally via litellm.aclient_session in orchestrator.startup().

    Never instantiate with per-call httpx clients — do not pass http_client
    to litellm here.  Never call aclose() on litellm.aclient_session — the
    lifecycle is owned by Deps (see state_daemon/orchestrator.py).
    # Never close: lifecycle owned by Deps (see orchestrator.py)
    """

    async def acompletion(
        self,
        model: str,
        messages: list[dict],
        **kwargs: object,
    ) -> ModelResponse:
        """Non-streaming inference call via litellm.

        Args:
            model:    litellm model string (e.g. "gpt-4o", "gemini/gemini-1.5-pro").
                      Do NOT pass Anthropic model strings here — use Phase 025's
                      direct SDK path for all Anthropic traffic.
            messages: OpenAI-format message list.
            **kwargs: Passed through to litellm.acompletion (e.g. temperature,
                      max_tokens, tools).

        Returns:
            ModelResponse with choices[0].message.content as the text field.

        Raises:
            ProviderTransientError: RateLimitError, APIConnectionError, Timeout,
                InternalServerError, ServiceUnavailableError, BadGatewayError.
            ProviderAuthError: AuthenticationError, PermissionDeniedError.
            ProviderBadRequestError: BadRequestError, ContextWindowExceededError,
                UnsupportedParamsError, InvalidRequestError, LiteLLMUnknownProvider.
            ProviderResponseError: APIResponseValidationError, JSONSchemaValidationError.
            StateProviderError: Any other litellm exception not covered above.
        """
        try:
            result = await litellm.acompletion(
                model=model,
                messages=messages,
                **kwargs,
            )
            return result  # type: ignore[return-value]
        except (
            lexc.RateLimitError,
            lexc.APIConnectionError,
            lexc.Timeout,
            lexc.InternalServerError,
            lexc.ServiceUnavailableError,
            lexc.BadGatewayError,
        ) as e:
            log.warning("provider.transient_error", model=model, error_type=type(e).__name__)
            raise ProviderTransientError(f"transient: {e}") from e
        except (
            lexc.AuthenticationError,
            lexc.PermissionDeniedError,
        ) as e:
            log.warning("provider.auth_error", model=model, error_type=type(e).__name__)
            raise ProviderAuthError(f"auth: {e}") from e
        except (
            lexc.BadRequestError,
            lexc.ContextWindowExceededError,
            lexc.UnsupportedParamsError,
            lexc.InvalidRequestError,
            lexc.LiteLLMUnknownProvider,
        ) as e:
            log.warning("provider.bad_request", model=model, error_type=type(e).__name__)
            raise ProviderBadRequestError(f"bad_request: {e}") from e
        except (
            lexc.APIResponseValidationError,
            lexc.JSONSchemaValidationError,
        ) as e:
            log.warning("provider.response_error", model=model, error_type=type(e).__name__)
            raise ProviderResponseError(f"response_validation: {e}") from e
        except Exception as e:
            # Catch-all: unknown litellm exceptions must not leak raw (T-024-3).
            log.warning("provider.unknown_error", model=model, error_type=type(e).__name__)
            raise StateProviderError(f"provider_error: {e}") from e

    async def astream(
        self,
        model: str,
        messages: list[dict],
        **kwargs: object,
    ) -> AsyncGenerator[ModelResponseStream, None]:
        """Streaming inference call via litellm.

        Yields ModelResponseStream chunks unchanged.  Access token content as:
            chunk.choices[0].delta.content        (text token, may be None)
            chunk.choices[0].delta.tool_calls     (tool call delta, may be None)
            chunk.choices[0].delta.reasoning_content  (thinking tokens, may be None)
            chunk.choices[0].finish_reason        (None until last chunk)

        PRV-07: chunks are yielded without mutation.  No accumulation, no
        filtering — callers receive the raw litellm stream objects.

        Args:
            model:    litellm model string (non-Anthropic; see acompletion docstring).
            messages: OpenAI-format message list.
            **kwargs: Passed through to litellm.acompletion (stream=True is added
                      automatically — do not pass stream= in kwargs).

        Raises:
            ProviderBadRequestError: BadRequestError at stream setup time.
            StateProviderError: Any other exception at setup or during iteration.
        """
        # Setup: exceptions here (before iteration starts) are mapped same as acompletion.
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                stream=True,
                **kwargs,
            )
        except (
            lexc.BadRequestError,
            lexc.ContextWindowExceededError,
            lexc.UnsupportedParamsError,
            lexc.InvalidRequestError,
        ) as e:
            log.warning("provider.stream_bad_request", model=model, error_type=type(e).__name__)
            raise ProviderBadRequestError(f"bad_request: {e}") from e
        except Exception as e:
            log.warning("provider.stream_setup_error", model=model, error_type=type(e).__name__)
            raise StateProviderError(f"provider_error: {e}") from e

        # Iteration: always use async for (never sync for) — Pitfall 2.
        # Never close the response object — litellm manages the stream lifecycle.
        try:
            async for chunk in response:
                yield chunk
        except Exception as e:
            log.warning("provider.stream_iter_error", model=model, error_type=type(e).__name__)
            raise StateProviderError(f"stream_error: {e}") from e
