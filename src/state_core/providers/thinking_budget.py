# src/state_core/providers/thinking_budget.py
"""Bridge: ResolvedProfile.thinking_budget_tokens → ThinkingConfigParam for AnthropicClient.

NOTE: Only pass result to AnthropicClient.create(thinking=...). LitellmClient raises
UnsupportedParamsError for thinking= kwarg — gate at call site.
"""
from __future__ import annotations

import structlog
from anthropic.types.thinking_config_enabled_param import ThinkingConfigEnabledParam
from anthropic.types.thinking_config_param import ThinkingConfigParam

from state_core.providers.errors import ProviderBadRequestError
from state_core.providers.model_profile import ResolvedProfile

log = structlog.get_logger(__name__)


def build_thinking_param(
    resolved: ResolvedProfile,
    max_tokens: int,
) -> ThinkingConfigParam | None:
    """Convert ResolvedProfile.thinking_budget_tokens to ThinkingConfigParam.

    Returns None if thinking_budget_tokens is None (balanced/budget profiles —
    no extended thinking for this call).
    Returns {"type": "enabled", "budget_tokens": N} if budget is set.

    Pre-flight validation prevents a wasted network round-trip to get a 400:
      - budget_tokens must be >= 1024 (Anthropic SDK minimum)
      - budget_tokens must be < max_tokens (Anthropic API constraint)

    Args:
        resolved:   ResolvedProfile from resolve_profile(). If thinking_budget_tokens
                    is None, returns None.
        max_tokens: The max_tokens to be passed to AnthropicClient.create().
                    Used only for constraint validation.

    Returns:
        ThinkingConfigParam dict or None.

    Raises:
        ProviderBadRequestError: if budget < 1024 or budget >= max_tokens.
    """
    budget = resolved.thinking_budget_tokens
    if budget is None:
        return None
    if budget < 1024:
        raise ProviderBadRequestError(
            f"thinking.budget_tokens must be >= 1024, got {budget}"
        )
    if budget >= max_tokens:
        raise ProviderBadRequestError(
            f"thinking.budget_tokens ({budget}) must be < max_tokens ({max_tokens})"
        )
    log.debug(
        "thinking_budget.build_param",
        budget_tokens=budget,
        max_tokens=max_tokens,
    )
    return ThinkingConfigEnabledParam(type="enabled", budget_tokens=budget)
