# src/state_core/providers/thinking_budget.py
"""Thinking-budget tag propagation adapter (PRV-08, Phase 029).

Bridges ResolvedProfile.thinking_budget_tokens to the ThinkingConfigParam
TypedDict required by AnthropicClient.create(thinking=...).

Design rationale:
- model_profile.py has a constrained import policy (no SDK deps).
- anthropic_client.py accepts ThinkingConfigParam directly (no ResolvedProfile dep).
- This module is the bridge between the two, with pre-flight constraint validation.

CALLER RESPONSIBILITY: The result of build_thinking_param() must only be passed
to AnthropicClient.create(thinking=...). Do NOT pass to LitellmClient.acompletion()
— litellm raises UnsupportedParamsError for the thinking= kwarg.
Gate at call site: if isinstance(client, AnthropicClient): thinking=build_thinking_param(...)

Note on model compatibility: this module always returns type="enabled". For
claude-opus-4-6 and claude-mythos-preview, the anthropic SDK warns that
type="adaptive" is preferred. This is intentional for Phase 029 scope —
the quality profile uses claude-opus-4-7 which does not trigger this warning.
If the project adopts a newer quality model, update the return type here.
"""
from __future__ import annotations

import structlog
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
    return {"type": "enabled", "budget_tokens": budget}
