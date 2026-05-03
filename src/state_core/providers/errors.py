"""Shared provider error hierarchy for state_core.providers.

Both litellm_client (PRV-01) and anthropic_client (PRV-02) raise these.
Callers catch StateProviderError for generic handling, or specific
subclasses for retry/auth/bad-request differentiation.

Extracted from state_core.providers.litellm_client in Phase 025.
"""

from __future__ import annotations


class StateProviderError(Exception):
    """Base for all state provider errors.

    Callers should catch this base class for generic provider-failure
    handling, or catch the specific subclasses for retry/auth logic.
    """


class ProviderTransientError(StateProviderError):
    """Retry-able error; caller should back off and retry.

    Raised for: RateLimitError, APIConnectionError, Timeout,
    InternalServerError, ServiceUnavailableError, BadGatewayError.
    """


class ProviderAuthError(StateProviderError):
    """Authentication failure; caller should refresh credentials.

    Raised for: AuthenticationError (401), PermissionDeniedError (403).
    """


class ProviderBadRequestError(StateProviderError):
    """Non-retryable request error; caller must fix the request.

    Raised for: BadRequestError, ContextWindowExceededError,
    UnsupportedParamsError, InvalidRequestError, LiteLLMUnknownProvider.
    """


class ProviderResponseError(StateProviderError):
    """Unexpected or invalid provider response; caller must fix response handling.

    Raised for: APIResponseValidationError, JSONSchemaValidationError.
    """
