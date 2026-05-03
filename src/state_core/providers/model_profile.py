# src/state_core/providers/model_profile.py
"""Model-profile resolver for the state engine (PRV-04).

Defines the four-name ModelProfile enum (quality/balanced/budget/inherit),
the ResolvedProfile Pydantic model holding concrete LLM parameters,
the _DEFAULTS table (three non-inherit profiles with hardcoded defaults),
and the resolve_profile() pure function that walks the scope inheritance chain.

Also provides GlobalProfileConfig (pydantic-settings) for daemon-level defaults,
and build_chat_params() which serializes a ResolvedProfile to the opencode
chat.params hook output dict (camelCase keys to match TS interface).

Mode isolation: this is state_core (shared kernel) — imports are limited to
stdlib, pydantic, pydantic_settings, and structlog only.
TODO: consolidate GlobalProfileConfig into state_core.config in a future phase.
"""
from __future__ import annotations

import enum
import structlog
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

log = structlog.get_logger(__name__)


class ModelProfile(str, enum.Enum):
    """Four-name model-profile discriminator (PRV-04).

    quality  — highest-capability model; extended-thinking budget enabled for Anthropic.
               Use for: discuss, architecture-level planning, verify.
    balanced — mid-capability model; moderate temperature; default for most Steps.
               Use for: execute-phase implementation tasks.
    budget   — lowest-cost model; capped token budget; CI / sub-task use.
               Use for: CI runs, research sub-tasks, structured output.
    inherit  — propagate to the parent scope (Slice -> Phase -> Arc -> global).
               Use in: STEP.md when Phase-level profile should apply.
    """

    quality = "quality"
    balanced = "balanced"
    budget = "budget"
    inherit = "inherit"


class ResolvedProfile(BaseModel):
    """Concrete LLM parameters after inherit-chain resolution.

    Returned by resolve_profile(); consumed by build_chat_params() and
    Phase 028's ProviderRouter integration.

    Note: profile field is never ModelProfile.inherit — resolver guarantees this.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: ModelProfile
    """The source profile name (quality/balanced/budget) — never 'inherit' here."""

    model: str
    """litellm model string or Anthropic model ID.

    e.g. 'claude-opus-4-7' (quality), 'claude-sonnet-4-6' (balanced),
         'claude-haiku-4-5' (budget).
    Phase 028 passes this to ProviderRouter.select() + LitellmClient.acompletion().
    """

    temperature: float = Field(ge=0.0, le=2.0)
    """LLM temperature. Lower = more deterministic (verify), higher = creative (discuss)."""

    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    """Nucleus sampling. Defaults to 1.0 (disabled) for most profiles."""

    max_output_tokens: int | None = None
    """Hard token cap. None means use the model's default."""

    thinking_budget_tokens: int | None = None
    """Extended thinking budget for AnthropicClient.create(thinking=...).

    None for non-thinking profiles (balanced, budget).
    Quality profile uses thinking for verify/discuss steps.
    Note: negative values are rejected by AnthropicClient (Phase 025/029).
    Propagated by Phase 029.
    """


_DEFAULTS: dict[ModelProfile, ResolvedProfile] = {
    ModelProfile.quality: ResolvedProfile(
        profile=ModelProfile.quality,
        model="claude-opus-4-7",
        temperature=0.2,
        top_p=1.0,
        max_output_tokens=None,
        thinking_budget_tokens=4000,
    ),
    ModelProfile.balanced: ResolvedProfile(
        profile=ModelProfile.balanced,
        model="claude-sonnet-4-6",
        temperature=0.5,
        top_p=1.0,
        max_output_tokens=None,
        thinking_budget_tokens=None,
    ),
    ModelProfile.budget: ResolvedProfile(
        profile=ModelProfile.budget,
        model="claude-haiku-4-5",
        temperature=0.2,
        top_p=1.0,
        max_output_tokens=4096,
        thinking_budget_tokens=None,
    ),
}


def resolve_profile(
    step_profile: ModelProfile | None = None,
    slice_profile: ModelProfile | None = None,
    phase_profile: ModelProfile | None = None,
    arc_profile: ModelProfile | None = None,
    *,
    global_profile: ModelProfile = ModelProfile.balanced,
    overrides: dict[str, object] | None = None,
) -> ResolvedProfile:
    """Resolve a concrete LLM profile by walking the scope inheritance chain.

    Chain (innermost to outermost):
      step -> slice -> phase -> arc -> global_profile -> balanced (hardcoded last resort)

    'inherit' at any level propagates to the next outer level.
    None is treated as 'inherit' (absent frontmatter = no override).

    Args:
        step_profile:   Profile declared in STEP.md frontmatter (or None if absent).
        slice_profile:  Profile declared in SLICE.md frontmatter (or None if absent).
        phase_profile:  Profile declared in PHASE.md frontmatter (or None if absent).
        arc_profile:    Profile declared in ARC.md frontmatter (or None if absent).
        global_profile: Daemon-level default from .state/config.toml. Default: balanced.
        overrides:      Optional field-level overrides (temperature, max_output_tokens, etc.)
                        applied AFTER profile resolution (e.g., for teach-mode temperature tuning).

    Returns:
        ResolvedProfile with concrete LLM parameters. profile field is never ModelProfile.inherit.
    """
    chain = [step_profile, slice_profile, phase_profile, arc_profile]

    resolved_name: ModelProfile = global_profile
    for profile in chain:
        if profile is not None and profile != ModelProfile.inherit:
            resolved_name = profile
            break

    # global_profile itself may be 'inherit' — treat as 'balanced' (last resort)
    if resolved_name == ModelProfile.inherit:
        resolved_name = ModelProfile.balanced

    base = _DEFAULTS[resolved_name]
    log.debug("model_profile.resolved", profile=resolved_name.value, model=base.model)

    if overrides:
        # model_copy(update=...) does not re-validate in Pydantic v2 — use model_validate
        # on a merged dict so that type errors in overrides raise ValidationError.
        return ResolvedProfile.model_validate(base.model_dump() | overrides)
    return base


def build_chat_params(resolved: ResolvedProfile) -> dict[str, object]:
    """Convert a ResolvedProfile to the opencode chat.params hook output dict.

    Keys are camelCase to match the TypeScript hook output interface:
      output.temperature, output.topP, output.topK,
      output.maxOutputTokens, output.options

    Source: packages/plugin/src/index.ts lines 248-254 (chat.params output type).

    Note: The 'model' field from ResolvedProfile is NOT included here — it is used
    by ProviderRouter (Phase 028) separately, not in the chat.params hook.
    Phase 028 is responsible for gating thinking_budget_tokens to AnthropicClient-only
    paths. Phase 027 always includes it when non-None.
    """
    params: dict[str, object] = {
        "temperature": resolved.temperature,
        "topP": resolved.top_p,
        "topK": 0,
        "maxOutputTokens": resolved.max_output_tokens,
        "options": {},
    }
    if resolved.thinking_budget_tokens is not None:
        params["options"] = {"thinking_budget_tokens": resolved.thinking_budget_tokens}
    return params


class GlobalProfileConfig(BaseSettings):
    """Daemon-level model profile defaults.

    Loaded from .state/config.toml [provider] section or environment variables.
    Override with STATE_DEFAULT_PROFILE=quality (env var) or
    [provider] default_profile = "quality" (config).
    """

    model_config = ConfigDict(extra="ignore", env_prefix="STATE_")

    default_profile: ModelProfile = ModelProfile.balanced
    """Global fallback profile. Overridden by per-Arc/Phase/Step frontmatter."""

    quality_model: str = "claude-opus-4-7"
    """Model string for the 'quality' profile. Override if a newer model is preferred."""

    balanced_model: str = "claude-sonnet-4-6"
    """Model string for the 'balanced' profile."""

    budget_model: str = "claude-haiku-4-5"
    """Model string for the 'budget' profile."""
