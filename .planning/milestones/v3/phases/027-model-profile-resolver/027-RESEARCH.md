# Phase 027: Model-Profile Resolver — Research

**Researched:** 2026-05-03
**Domain:** Model profile resolution, inheritance chain, opencode `chat.params` hook integration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRV-04 | Model profiles (`quality` / `balanced` / `budget` / `inherit`) configurable per-Arc, per-Phase, or globally | Architecture defines `model_profile` frontmatter on STEP.md; `chat.params` hook is the delivery surface; pydantic model + resolver function is the correct implementation pattern |
</phase_requirements>

---

## Summary

Phase 027 introduces `state_core.providers.model_profile` — the module that resolves a four-name model-profile enum (`quality`, `balanced`, `budget`, `inherit`) to concrete LLM parameters, and makes those parameters available to the opencode `chat.params` hook.

The phase has three parts:

1. **Pydantic model definitions** — `ModelProfile` enum (`quality | balanced | budget | inherit`), `ResolvedProfile` dataclass holding concrete params (model string, temperature, max_tokens, optional thinking budget), and `GlobalProfileConfig` for daemon-level defaults.

2. **Resolver function** — `resolve_profile(scope_profile, *, arc_profile, phase_profile, global_profile)` that walks the inheritance chain (Step → Slice → Phase → Arc → global) and returns a `ResolvedProfile`. `inherit` propagates upward; the first non-inherit value wins.

3. **`chat.params` hook integration point** — a Python function `build_chat_params(resolved: ResolvedProfile) -> dict` that emits the dict the TS plugin's `chat.params` hook modifies its `output` object with. This Python function is called by the daemon's HTTP handler when the plugin shim posts to `/hook/chat-params`. No TS code is written in Phase 027 — the integration point is the daemon HTTP endpoint, which Phase 027 also scaffolds as a thin stub.

The phase depends on Phase 024 (litellm_client — the LitellmClient interface is stable) but does NOT depend on Phase 026 completion. `ProviderRouter.select()` is the consumer of model profiles (Phase 028 wires them together); Phase 027 only needs to produce the resolved profile dict.

830 tests are passing before this phase begins. The test target after Phase 027 is approximately 855-870 (25-40 net-new tests for the profile model, resolver, and HTTP handler stub).

**Primary recommendation:** Implement `ModelProfile` as a `str` enum with `Literal` aliases, `ResolvedProfile` as a frozen Pydantic model, and `resolve_profile()` as a pure function. Keep the module at `state_core/providers/model_profile.py` — it is shared kernel (used by both build and teach modes). The daemon HTTP stub lives in `state_daemon/hooks.py` (new file).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | >=2.13.2 (project pin) | `ModelProfile` enum, `ResolvedProfile`, `GlobalProfileConfig` data models | Project standard for all data models; `extra="forbid"` + `frozen=True` catches schema drift |
| `enum` (stdlib) | 3.12 built-in | `ModelProfile` enum base | `StrEnum` (3.11+) gives natural string comparisons; `Literal` annotation gives type narrowing |
| `structlog` | >=25.1 (project pin) | Debug logging in resolver | Consistent with all `state_core` modules |
| `pydantic-settings` | >=2.7 (project pin) | `GlobalProfileConfig` loaded from `.state/config.toml` | Already used for daemon config; zero new dep |

### Supporting (test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | >=8.4.0 | Test runner | Already installed |
| `pytest-asyncio` | >=1.3.0, `asyncio_mode="auto"` | Any async test for HTTP handler stub | Already configured |
| `hypothesis` | >=6.120 | Property test: inheritance chain is monotone (any sequence of inherit/non-inherit resolves to exactly one non-inherit value or falls to global) | Critical for resolver correctness |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `StrEnum` + frozen Pydantic `ResolvedProfile` | Plain `TypedDict` | Pydantic gives field validation + `.model_dump()` for JSON serialization; consistent with project pattern |
| Module `model_profile.py` in `state_core/providers/` | Separate `state_core/model_profiles/` package | Single-module is appropriate for the scope; the providers package is the natural home since the output feeds `ProviderRouter` |
| Pure function `resolve_profile()` | Method on a `ProfileResolver` class | Pure function is easier to unit-test; no state is needed; class adds ceremony for no benefit |

**Installation:** No new packages. All libraries already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended File Layout
```
src/state_core/providers/
├── __init__.py
├── errors.py                    # Phase 025 — unchanged
├── litellm_client.py            # Phase 024 — unchanged
├── anthropic_client.py          # Phase 025 — unchanged
├── router.py                    # Phase 026 — unchanged
└── model_profile.py             # NEW — Phase 027 (this phase)

src/state_daemon/
├── server.py                    # unchanged
├── orchestrator.py              # unchanged
├── cli.py                       # unchanged
├── watchers.py                  # unchanged
└── hooks.py                     # NEW — Phase 027 thin HTTP stub for /hook/chat-params

tests/
├── test_model_profile.py        # NEW — Wave 0 RED stubs, Wave 1 GREEN
├── test_hooks.py                # NEW — Wave 0 RED stubs for HTTP handler (Wave 1 GREEN)
```

### Pattern 1: `ModelProfile` as `StrEnum`

**What:** A four-value string enum with exactly the names PRV-04 specifies.
**When to use:** Everywhere a profile name is carried (STEP.md frontmatter, daemon config, resolver args).

```python
# Source: Python 3.11+ StrEnum; project uses Python 3.12+ (PROJECT.md mandate)
import enum

class ModelProfile(str, enum.Enum):
    """Four-name model-profile discriminator (PRV-04).

    quality  — highest-capability model, full extended-thinking budget.
                Use for: discuss, architecture-level planning, verify.
    balanced — mid-capability model, moderate temperature.
                Use for: execute-phase implementation tasks.
    budget   — lowest-cost model, restricted token budget.
                Use for: CI runs, research sub-tasks, structured output.
    inherit  — propagate to the parent scope's profile.
                Use in: STEP.md when Phase-level profile should apply.
    """
    quality  = "quality"
    balanced = "balanced"
    budget   = "budget"
    inherit  = "inherit"
```

Because `ModelProfile` inherits from `str`, `model_profile == "quality"` works in comparisons and Pydantic YAML/JSON parsing handles the string-to-enum coercion automatically.

### Pattern 2: `ResolvedProfile` — Concrete Parameter Container

**What:** A frozen Pydantic model holding the concrete LLM parameters after resolution.
**When to use:** Returned by `resolve_profile()`; passed to `build_chat_params()`.

```python
# Source: ARCHITECTURE.md STEP.md frontmatter model_profile section (section 8.2)
# and chat.params hook output: {temperature, topP, topK, maxOutputTokens, options}

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ResolvedProfile(BaseModel):
    """Concrete LLM parameters after profile resolution.

    All fields map directly to the opencode chat.params hook output fields:
      temperature     -> output.temperature
      top_p           -> output.topP
      max_output_tokens -> output.maxOutputTokens
      thinking_budget -> output.options["thinking_budget_tokens"]
      model           -> NOT sent via chat.params; used by ProviderRouter (Phase 028)
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
    Propagated by Phase 029.
    """
```

### Pattern 3: Default Profile Table

**What:** Module-level constants mapping each non-inherit profile name to a `ResolvedProfile`. This is the "global default" — what `resolve_profile()` falls back to when no scope override is set.
**When to use:** As the final fallback in the inheritance chain.

```python
# Default model strings match the ARCHITECTURE.md STEP.md frontmatter example:
# quality: claude-opus-4-7 (high-capability, extended thinking enabled)
# balanced: claude-sonnet-4-6 (mid-tier, standard completion)
# budget: claude-haiku-4-5 (cheapest Anthropic model; also used in Phase 031 parity tests)

_DEFAULTS: dict[ModelProfile, ResolvedProfile] = {
    ModelProfile.quality: ResolvedProfile(
        profile=ModelProfile.quality,
        model="claude-opus-4-7",       # Highest capability (from ARCHITECTURE.md)
        temperature=0.2,               # Low-temp for verify/planning (ARCHITECTURE.md chat.params row)
        top_p=1.0,
        max_output_tokens=None,        # Let model decide
        thinking_budget_tokens=4000,   # ARCHITECTURE.md STEP.md frontmatter example value
    ),
    ModelProfile.balanced: ResolvedProfile(
        profile=ModelProfile.balanced,
        model="claude-sonnet-4-6",     # Mid-tier (current model-string convention)
        temperature=0.5,               # Execute: mid (ARCHITECTURE.md chat.params row)
        top_p=1.0,
        max_output_tokens=None,
        thinking_budget_tokens=None,   # No extended thinking for balanced
    ),
    ModelProfile.budget: ResolvedProfile(
        profile=ModelProfile.budget,
        model="claude-haiku-4-5",      # Lowest cost; confirmed in ROADMAP.md Phase 031
        temperature=0.2,               # Low-temp for structured/deterministic tasks
        top_p=1.0,
        max_output_tokens=4096,        # Cap to control cost
        thinking_budget_tokens=None,
    ),
}
```

### Pattern 4: `resolve_profile()` — Inheritance Chain Walker

**What:** Pure function that walks the scope chain and returns the first non-inherit profile.
**When to use:** Called by the daemon's `chat.params` HTTP handler with the current scope stack (Step profile, Phase profile, Arc profile, global config profile).

PRV-04 specifies: "configurable per-Arc, per-Phase, or globally". The goal statement adds "per-Slice" and "per-Step" scopes. The inheritance chain from innermost to outermost is:

```
Step profile → Slice profile → Phase profile → Arc profile → global config profile
```

`inherit` at any level means "look at the next outer level". If all levels are `inherit`, fall back to `_DEFAULTS[global_profile]` where `global_profile` defaults to `balanced`.

```python
# Source: Pattern derived from PRV-04 requirement + ARCHITECTURE.md STEP.md frontmatter
# (model_profile is a STEP.md field; Phase/Arc frontmatter also carry it)

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
      step -> slice -> phase -> arc -> global -> _DEFAULTS[global]

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
        ResolvedProfile with concrete LLM parameters.
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

    if overrides:
        return base.model_copy(update=overrides)
    return base
```

**Key invariants (for Hypothesis tests):**
- `resolve_profile()` NEVER returns a `ResolvedProfile` with `profile=inherit`.
- If all inputs are `None` or `inherit`, returns `_DEFAULTS[ModelProfile.balanced]`.
- `resolve_profile(step_profile=X)` where X is non-inherit ALWAYS returns `_DEFAULTS[X]` (when no overrides).
- `overrides` fields must be valid `ResolvedProfile` field names; Pydantic `model_copy(update=...)` validates this.

### Pattern 5: `build_chat_params()` — Hook Output Formatter

**What:** Converts a `ResolvedProfile` to the dict shape the opencode `chat.params` hook's `output` object expects.
**When to use:** Called by the daemon's `/hook/chat-params` handler immediately before returning the hook response.

```python
# Source: opencode packages/plugin/src/index.ts line 248-254
# output: { temperature: number, topP: number, topK: number, maxOutputTokens: number | undefined, options: Record<string, any> }

def build_chat_params(resolved: ResolvedProfile) -> dict[str, object]:
    """Convert a ResolvedProfile to the opencode chat.params hook output dict.

    The TS plugin hook output object has fields:
      temperature: number
      topP: number
      topK: number                   (always 0 = disabled; we don't tune topK)
      maxOutputTokens: number | undefined
      options: Record<string, any>   (free-form; we store thinking_budget here)

    The 'model' field from ResolvedProfile is NOT included here — it is used
    by ProviderRouter (Phase 028) separately, not in the chat.params hook.

    Returns:
        Dict suitable for JSON serialization in the /hook/chat-params response.
    """
    params: dict[str, object] = {
        "temperature": resolved.temperature,
        "topP": resolved.top_p,
        "topK": 0,  # Not used in state's profiles
        "maxOutputTokens": resolved.max_output_tokens,
        "options": {},
    }
    if resolved.thinking_budget_tokens is not None:
        params["options"] = {"thinking_budget_tokens": resolved.thinking_budget_tokens}
    return params
```

### Pattern 6: `GlobalProfileConfig` — Daemon-Level Config

**What:** Pydantic settings model for the daemon's global default profile, loaded from `.state/config.toml` or environment variables.
**When to use:** At daemon startup; stored in `Deps` (Phase 023 provides the Deps container).

```python
# Source: pydantic-settings pattern from STACK.md; Deps pattern from state_core/deps.py
from pydantic_settings import BaseSettings

class GlobalProfileConfig(BaseSettings):
    """Daemon-level model profile defaults.

    Loaded from .state/config.toml [provider] section or environment variables.
    Override with STATE_DEFAULT_PROFILE=quality (env var) or [provider] default_profile = "quality" (config).
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
```

### Pattern 7: `/hook/chat-params` Daemon HTTP Stub

**What:** A thin `asyncio` HTTP handler that receives a `chat.params` hook invocation from the plugin shim and returns the resolved profile dict.
**When to use:** When the TS plugin shim POSTs to the daemon's `/hook/chat-params` endpoint.

This is a stub in Phase 027 (it hard-codes a simple resolution; the full scope-stack lookup from `events.sqlite` is Phase 028 work). The stub validates the pattern and gives the Phase 031 parity tests something to call.

```python
# src/state_daemon/hooks.py — Phase 027 stub
# Full integration with Arc/Phase/Slice/Step scope stack comes in Phase 028.

from __future__ import annotations
import json
from aiohttp import web  # or asyncio stdlib — match server.py pattern

from state_core.providers.model_profile import (
    ModelProfile,
    resolve_profile,
    build_chat_params,
)

async def handle_chat_params(request: web.Request) -> web.Response:
    """Handle POST /hook/chat-params from the plugin shim.

    Phase 027 stub: reads step_profile from the request body;
    resolves against global defaults (no scope-stack lookup yet).
    Full scope-stack lookup (Arc/Phase/Slice/Step) is Phase 028.
    """
    body = await request.json()
    step_profile_raw = body.get("step_profile")
    step_profile = ModelProfile(step_profile_raw) if step_profile_raw else None

    resolved = resolve_profile(step_profile=step_profile)
    params = build_chat_params(resolved)

    return web.Response(
        content_type="application/json",
        body=json.dumps(params).encode(),
    )
```

**Note on server framework:** `state_daemon/server.py` (from prior phases) uses aiohttp or asyncio stdlib. This research does not prescribe which; the planner should check `server.py` to match the existing pattern. The important invariant is that `hooks.py` does NOT import `state_build.*` or `state_teach.*`.

### Anti-Patterns to Avoid

- **`inherit` as a resolved profile:** `resolve_profile()` must never return a `ResolvedProfile` with `profile=inherit`. The type system enforces this: `ResolvedProfile.profile` should have type `Literal[ModelProfile.quality, ModelProfile.balanced, ModelProfile.budget]` — or at minimum, the docstring + tests must assert `profile != ModelProfile.inherit`.
- **Routing by model profile in the router:** `ProviderRouter.select()` (Phase 026) routes by credential type, not profile. Phase 028 wires the profile to the call; Phase 027 only resolves it.
- **Hardcoding model strings without config override:** The `quality_model`, `balanced_model`, `budget_model` fields in `GlobalProfileConfig` allow the user to swap model strings without code changes. Always route through config, not bare string literals in business logic.
- **Putting the inheritance-chain logic in TS (plugin side):** The resolver is Python-only (daemon side). The plugin shim only sends the current scope identifiers; the daemon resolves the profile. This keeps the inheritance logic testable in Python and out of the TS hook.
- **Importing `state_build.*` or `state_teach.*` in `model_profile.py`:** This is shared kernel. Mode isolation enforced.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model string registry | Custom dict of `provider_id -> model_id` | `GlobalProfileConfig.quality_model` etc. (pydantic-settings) | Config-file + env-var override is free with pydantic-settings; custom registry adds a new abstraction layer with no benefit |
| Temperature tuning per Step state | Separate `StepStateTuner` class | `overrides: dict` in `resolve_profile()` call-site | The caller (chat.params handler) computes overrides from the Step's current state machine state; the resolver is pure |
| Thinking budget validation | Custom validator in resolver | Let `AnthropicClient.create()` raise `ProviderBadRequestError` if budget >= max_tokens | Phase 025's `AnthropicClient` already handles this; the resolver does not know `max_tokens` at resolution time |
| Profile persistence in SQLite | New `profiles` table | Read from artifact frontmatter on demand | Profiles live in STEP.md/PHASE.md/ARC.md YAML; they are part of the artifact, not a separate entity. The event store records profile overrides as part of step state events, not as standalone events |
| Custom YAML frontmatter parser | `yaml.safe_load()` custom code | pydantic model validation with `ModelProfile` field | The artifact layer (Phase 014+) already reads YAML frontmatter; `model_profile` is just another pydantic-validated field on the artifact schema |

---

## Common Pitfalls

### Pitfall 1: `inherit` Propagating All the Way to No Default

**What goes wrong:** All scope levels are `None` or `inherit`, and the resolver falls through to a bare `inherit` that has no mapping in `_DEFAULTS`, raising `KeyError`.

**Why it happens:** Forgetting to normalize `inherit` at the last step in the chain.

**How to avoid:** The final fallback must always coerce `inherit` to `balanced` (or whichever the project's "safe" default is). The resolver has an explicit guard:
```python
if resolved_name == ModelProfile.inherit:
    resolved_name = ModelProfile.balanced
```

**Warning signs:** `KeyError: <ModelProfile.inherit: 'inherit'>` in tests.

### Pitfall 2: `model_copy(update=...)` Does Not Validate Override Field Types

**What goes wrong:** `overrides={"temperature": "warm"}` raises a `pydantic_core.ValidationError` at `model_copy(update=...)` time because `temperature` is `float`, not `str`. Callers must pass typed values.

**Why it happens:** Pydantic `model_copy(update=...)` does re-validate with `validate_assignment` only if the model has `model_config = ConfigDict(validate_assignment=True)`. `frozen=True` implies fields cannot be set after construction; `model_copy` creates a new instance, which DOES re-validate.

**How to avoid:** Ensure `ResolvedProfile` has `model_config = ConfigDict(frozen=True)` (which validates on `model_copy`). Test the override path with wrong types to confirm `ValidationError` is raised.

**Warning signs:** Callers pass `overrides={"temperature": some_string}` and don't get an error — indicates `validate_assignment` is not active.

### Pitfall 3: `chat.params` Hook Output Expects camelCase Keys

**What goes wrong:** `build_chat_params()` returns `{"top_p": 0.9, "max_output_tokens": 4096}` (Python snake_case). The TS hook output object uses `topP` and `maxOutputTokens` (camelCase). The TS shim reads `output.topP`, not `output.top_p` — the snake_case keys are silently ignored.

**Why it happens:** Python developers naturally use snake_case; the opencode plugin's TypeScript interface uses camelCase (confirmed from `packages/plugin/src/index.ts` line 250: `topP: number`).

**How to avoid:** `build_chat_params()` MUST return camelCase keys: `"topP"`, `"topK"`, `"maxOutputTokens"`. The internal `ResolvedProfile` can use snake_case (Pydantic convention); only the serialized hook output dict uses camelCase. This is explicit in the function — no alias generator needed.

**Warning signs:** Temperature is applied but `topP` changes have no effect.

### Pitfall 4: Thinking Budget Applied to Non-Anthropic Models

**What goes wrong:** `thinking_budget_tokens` is set in a `ResolvedProfile` for the `quality` profile, but the request routes through `LitellmClient` (non-Anthropic API key). litellm does not know what to do with `thinking_budget_tokens` in `options` and either ignores it or raises `UnsupportedParamsError`.

**Why it happens:** Phase 027 resolves the profile without knowing the routing decision (Phase 028 wires routing + profile together). The `quality` profile defaults to `thinking_budget_tokens=4000`.

**How to avoid:** Phase 027 documents this in `build_chat_params()`: "Phase 028 is responsible for gating `thinking_budget_tokens` to AnthropicClient-only paths. Phase 027 always includes it when non-None." The `chat.params` hook `output.options` is free-form (`Record<string, any>`) — unrecognized keys are ignored by the TS shim. The AnthropicClient path (Phase 029) reads `thinking_budget_tokens` from `options`; the litellm path ignores it.

**Warning signs:** `ProviderBadRequestError: unsupported_params: thinking` in Phase 031 parity matrix tests when a non-Anthropic provider is used with `quality` profile.

### Pitfall 5: Mutating `output` in the TS `chat.params` Hook Instead of Replacing Fields

**What goes wrong:** The TS plugin hook's `output` parameter is passed by reference. Assigning `output = build_result` (replacing the object) does nothing — the caller reads the original. The hook must mutate fields on `output` in place: `output.temperature = ...; output.topP = ...`.

**Why it happens:** JavaScript objects are passed by reference; replacing the reference doesn't propagate to the caller.

**How to avoid:** Phase 027 (Python side) does not write TS code. This pitfall is for Phase 027's planner/executor to note in the TS hook documentation. The Python HTTP handler returns a JSON dict; the TS shim reads it and applies fields to `output` via `Object.assign(output, responseBody)`.

**Warning signs:** Temperature is always the model's default (the hook isn't applying the resolved params).

---

## Code Examples

Verified patterns from project source:

### Full `model_profile.py` Skeleton

```python
# src/state_core/providers/model_profile.py
# Source: patterns from state_core/providers/errors.py (frozen Pydantic),
#         state_core/auth/base.py (StrEnum discriminator), ARCHITECTURE.md §8.2

from __future__ import annotations

import enum
import structlog
from pydantic import BaseModel, ConfigDict, Field

log = structlog.get_logger(__name__)


class ModelProfile(str, enum.Enum):
    """Four-name model-profile discriminator (PRV-04).

    quality  — highest-capability model; extended-thinking budget enabled for Anthropic.
    balanced — mid-capability model; moderate temperature; default for most Steps.
    budget   — lowest-cost model; capped token budget; CI / sub-task use.
    inherit  — propagate to the parent scope (Slice → Phase → Arc → global).
    """
    quality  = "quality"
    balanced = "balanced"
    budget   = "budget"
    inherit  = "inherit"


class ResolvedProfile(BaseModel):
    """Concrete LLM parameters after inherit-chain resolution.

    Returned by resolve_profile(); consumed by build_chat_params() and
    Phase 028's ProviderRouter integration.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: ModelProfile
    model: str
    temperature: float = Field(ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_output_tokens: int | None = None
    thinking_budget_tokens: int | None = None


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

    None and 'inherit' both mean 'look at the next outer scope'.
    Chain: step -> slice -> phase -> arc -> global_profile -> balanced (hardcoded last resort).
    """
    chain = [step_profile, slice_profile, phase_profile, arc_profile]
    resolved_name: ModelProfile = global_profile

    for profile in chain:
        if profile is not None and profile != ModelProfile.inherit:
            resolved_name = profile
            break

    if resolved_name == ModelProfile.inherit:
        resolved_name = ModelProfile.balanced

    base = _DEFAULTS[resolved_name]
    log.debug("model_profile.resolved", profile=resolved_name.value, model=base.model)

    if overrides:
        return base.model_copy(update=overrides)
    return base


def build_chat_params(resolved: ResolvedProfile) -> dict[str, object]:
    """Serialize a ResolvedProfile to the opencode chat.params hook output dict.

    Keys are camelCase to match the TypeScript hook output interface:
      output.temperature, output.topP, output.topK,
      output.maxOutputTokens, output.options

    Source: packages/plugin/src/index.ts lines 248-254 (chat.params output type).
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
```

### Hypothesis Property Test: Resolver Invariants

```python
# tests/test_model_profile.py — property tests for inherit-chain correctness
from hypothesis import given, assume
import hypothesis.strategies as st
from state_core.providers.model_profile import ModelProfile, resolve_profile

_ALL_PROFILES = list(ModelProfile)
_PROFILE_OR_NONE = st.one_of(st.none(), st.sampled_from(_ALL_PROFILES))

@given(
    step=_PROFILE_OR_NONE,
    slice_=_PROFILE_OR_NONE,
    phase=_PROFILE_OR_NONE,
    arc=_PROFILE_OR_NONE,
    global_=st.sampled_from(_ALL_PROFILES),
)
def test_resolve_never_returns_inherit(step, slice_, phase, arc, global_):
    """Resolved profile MUST never be 'inherit' regardless of input combination."""
    resolved = resolve_profile(step, slice_, phase, arc, global_profile=global_)
    assert resolved.profile != ModelProfile.inherit

@given(non_inherit=st.sampled_from([ModelProfile.quality, ModelProfile.balanced, ModelProfile.budget]))
def test_step_non_inherit_wins_over_all(non_inherit):
    """A non-inherit step profile MUST override all outer scopes."""
    resolved = resolve_profile(
        step_profile=non_inherit,
        slice_profile=ModelProfile.quality,
        phase_profile=ModelProfile.balanced,
        arc_profile=ModelProfile.budget,
        global_profile=ModelProfile.quality,
    )
    assert resolved.profile == non_inherit

def test_all_inherit_falls_back_to_balanced():
    """All inherit/None inputs -> balanced (project safe default)."""
    resolved = resolve_profile(
        step_profile=ModelProfile.inherit,
        slice_profile=ModelProfile.inherit,
        phase_profile=None,
        arc_profile=None,
        global_profile=ModelProfile.inherit,
    )
    assert resolved.profile == ModelProfile.balanced
```

### chat.params Output Key Test

```python
def test_build_chat_params_camelcase_keys():
    """build_chat_params MUST use camelCase keys for the TS hook interface."""
    from state_core.providers.model_profile import build_chat_params, _DEFAULTS, ModelProfile
    params = build_chat_params(_DEFAULTS[ModelProfile.balanced])
    assert "topP" in params
    assert "maxOutputTokens" in params
    assert "top_p" not in params
    assert "max_output_tokens" not in params

def test_quality_profile_includes_thinking_budget():
    """Quality profile MUST include thinking_budget_tokens in options."""
    from state_core.providers.model_profile import build_chat_params, _DEFAULTS, ModelProfile
    params = build_chat_params(_DEFAULTS[ModelProfile.quality])
    assert "thinking_budget_tokens" in params["options"]
    assert params["options"]["thinking_budget_tokens"] == 4000
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GSD PLAN.md frontmatter `model_profile` read in JS shim | Python daemon resolves profile; TS shim applies output to hook | Phase 027 (this phase) | Resolution logic is testable in Python; TS shim is thin |
| Hardcoded temperature in GSD hooks | Four-profile system with inheritance chain | Phase 027 | Per-Arc/Phase/Step tuning; consistent with the product hierarchy |
| No thinking-budget propagation | `thinking_budget_tokens` field in `ResolvedProfile` | Phase 027 (foundation); Phase 029 wires it to AnthropicClient | Enables extended-thinking budget per profile |

**Deprecated/outdated in this project:**
- The GSD `.planning/config.json` `model_profile: "budget"` field is the *GSD planning tool's* own config (used to set the research/planning agent's temperature). It is not the same as Phase 027's `ModelProfile` system. These are different layers: GSD config sets *how the AI plans this project*, while Phase 027 sets *how the `state` engine's Steps route inference calls at runtime*.

---

## Open Questions

1. **What server framework does `state_daemon/server.py` use?**
   - What we know: `state_daemon/server.py` exists. The ARCHITECTURE.md mentions "HTTP server" in the daemon; the research reads STACK.md which says "asyncio Unix socket + JSON-RPC" as the primary transport, but also mentions an "HTTP API" for the dashboard.
   - What's unclear: Whether `server.py` uses `aiohttp`, `starlette`, raw `asyncio.start_server`, or something else. The HTTP handler stub in `hooks.py` must match.
   - Recommendation: The planner should add Task 0 to read `state_daemon/server.py` before writing `hooks.py`. This research confirms the hook *interface* (inputs, outputs) but not the HTTP framework binding.

2. **Should `thinking_budget_tokens` in `ResolvedProfile` be `int` or be a full `ThinkingConfigParam`?**
   - What we know: `AnthropicClient.create()` (Phase 025) accepts `thinking: ThinkingConfigParam | None` where `ThinkingConfigParam = {"type": "enabled"|"adaptive", "budget_tokens": int}`. The `build_chat_params()` output stores only the integer in `options["thinking_budget_tokens"]`.
   - What's unclear: Should Phase 027 carry the full `ThinkingConfigParam` dict, or just the integer budget? Phase 029 reads from the resolved profile to build the `ThinkingConfigParam`.
   - Recommendation: Carry just `thinking_budget_tokens: int | None` in `ResolvedProfile`. Phase 029 wraps it into `{"type": "enabled", "budget_tokens": N}`. Keeping it as a bare int avoids importing `anthropic.types` into `state_core/providers/model_profile.py` (which is shared kernel and should not depend on the Anthropic SDK directly).

3. **Should `GlobalProfileConfig` live in `model_profile.py` or in `state_daemon/server.py` / `state_core/config.py`?**
   - What we know: `state_core/config.py` exists (confirmed from source listing) and handles opencode config discovery.
   - What's unclear: Whether daemon-level profile defaults belong in the existing config module or in the new `model_profile.py`.
   - Recommendation: Add `GlobalProfileConfig` to `model_profile.py` for Phase 027 (keeps the module self-contained). A future phase can consolidate all daemon config into one settings class. Document the intent with a `# TODO: consolidate into state_core.config` comment.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ with `asyncio_mode = "auto"` (already configured in `pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run python3 -m pytest tests/test_model_profile.py tests/test_hooks.py -x -q` |
| Full suite command | `uv run python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-04 | `ModelProfile` enum has exactly `quality`, `balanced`, `budget`, `inherit` members | unit | `pytest tests/test_model_profile.py::test_model_profile_members -x` | ❌ Wave 0 |
| PRV-04 | `ResolvedProfile` is a frozen Pydantic model with required fields | unit | `pytest tests/test_model_profile.py::test_resolved_profile_frozen -x` | ❌ Wave 0 |
| PRV-04 | `_DEFAULTS` covers exactly the three non-inherit profiles | unit | `pytest tests/test_model_profile.py::test_defaults_coverage -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` never returns `profile=inherit` | property | `pytest tests/test_model_profile.py::test_resolve_never_returns_inherit -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` step-level non-inherit wins over all outer scopes | property | `pytest tests/test_model_profile.py::test_step_non_inherit_wins_over_all -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` phase-level profile applies when step/slice are inherit | unit | `pytest tests/test_model_profile.py::test_phase_profile_applies_when_step_inherit -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` arc-level profile applies when step/slice/phase are inherit | unit | `pytest tests/test_model_profile.py::test_arc_profile_applies_when_inner_inherit -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` all inherit/None falls back to `balanced` | unit | `pytest tests/test_model_profile.py::test_all_inherit_falls_back_to_balanced -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile()` global_profile override respected when all scopes are inherit | unit | `pytest tests/test_model_profile.py::test_global_profile_override -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile(overrides={"temperature": 0.9})` applies the field override | unit | `pytest tests/test_model_profile.py::test_overrides_applied -x` | ❌ Wave 0 |
| PRV-04 | `resolve_profile(overrides={"temperature": "warm"})` raises Pydantic ValidationError | unit | `pytest tests/test_model_profile.py::test_invalid_override_raises -x` | ❌ Wave 0 |
| PRV-04 | `build_chat_params()` returns camelCase keys (`topP`, `maxOutputTokens`) | unit | `pytest tests/test_model_profile.py::test_build_chat_params_camelcase_keys -x` | ❌ Wave 0 |
| PRV-04 | `build_chat_params()` quality profile includes `options.thinking_budget_tokens` | unit | `pytest tests/test_model_profile.py::test_quality_profile_includes_thinking_budget -x` | ❌ Wave 0 |
| PRV-04 | `build_chat_params()` balanced profile has empty `options` dict | unit | `pytest tests/test_model_profile.py::test_balanced_profile_empty_options -x` | ❌ Wave 0 |
| PRV-04 | `/hook/chat-params` HTTP stub returns JSON with correct shape | unit | `pytest tests/test_hooks.py::test_chat_params_handler_returns_valid_shape -x` | ❌ Wave 0 |
| PRV-04 | `/hook/chat-params` with no step_profile returns balanced defaults | unit | `pytest tests/test_hooks.py::test_chat_params_default_profile -x` | ❌ Wave 0 |
| PRV-04 | `/hook/chat-params` with step_profile=quality returns quality temperature (0.2) | unit | `pytest tests/test_hooks.py::test_chat_params_quality_profile -x` | ❌ Wave 0 |
| PRV-04 | Mode isolation: `state_core.providers.model_profile` does NOT import `state_build.*` or `state_teach.*` | import-graph | `pytest tests/test_model_profile.py::test_no_mode_silo_import -x` | ❌ Wave 0 |

**Total: 19 tests.** All RED in Wave 0; Wave 1 implements `model_profile.py` and `hooks.py` stub to make them GREEN.

### Sampling Rate
- **Per task commit:** `uv run python3 -m pytest tests/test_model_profile.py tests/test_hooks.py -x -q`
- **Per wave merge:** `uv run python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Phase gate:** Full suite green (currently 830; target ~849 after Phase 027) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_model_profile.py` — 17 RED stubs (all PRV-04 behavioral tests except HTTP stubs)
- [ ] `tests/test_hooks.py` — 2 RED stubs for `/hook/chat-params`
- [ ] `src/state_core/providers/model_profile.py` — new file (Wave 1 GREEN)
- [ ] `src/state_daemon/hooks.py` — new file with HTTP stub (Wave 1 GREEN)

*(No framework gaps — pytest, asyncio_mode, hypothesis all already installed and configured.)*

---

## Sources

### Primary (HIGH confidence)
- `src/state_core/providers/router.py` — docstring explicitly names Phase 027 as the consumer: "Phase 027 — model-profile resolver passes (cred, deps, model_profile) to select()"
- `src/state_core/providers/anthropic_client.py` — `ThinkingConfigParam`, `thinking_budget_tokens` interface confirmed; `frozen=True` pattern for Pydantic models confirmed
- `src/state_core/providers/errors.py` — `ConfigDict(extra="forbid", frozen=True)` pattern used throughout providers package
- `.state-inputs/opencode/packages/plugin/src/index.ts` lines 246-255 — `chat.params` hook type: `output: { temperature: number, topP: number, topK: number, maxOutputTokens: number | undefined, options: Record<string, any> }`
- `.state-inputs/opencode-extension-surface.md` line 34 — `chat.params(input, output: {temperature, topP, topK, maxOutputTokens, options})`; line 708 — "Model profile resolver | chat.params hook"
- `.planning/research/ARCHITECTURE.md` section 8.2 — STEP.md frontmatter `model_profile` field confirmed; temperature-by-step-state mapping (0.2 verify, 0.5 execute, 0.8 discuss); `thinking: {enabled: true, budget_tokens: 4000}` example value
- `.planning/milestones/v3/REQUIREMENTS.md` — PRV-04: "Model profiles (quality / balanced / budget / inherit) configurable per-Arc, per-Phase, or globally"
- `.planning/milestones/v3/ROADMAP.md` Phase 027 — "Per-Arc/Phase/Slice/Step override, inheritance chain, resolver used by chat.params hook"
- `uv run python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` — 830 passing, 0 failing (baseline confirmed 2026-05-03)
- `pyproject.toml` — `pydantic>=2.13.2`, `pydantic-settings>=2.7`, `structlog>=25.1`, `hypothesis>=6.120`, `asyncio_mode="auto"` all confirmed present

### Secondary (MEDIUM confidence)
- `.planning/milestones/v3/phases/024-litellm-wrapper/024-RESEARCH.md` — `LitellmClient` interface (no constructor args; `acompletion(model, messages, **kwargs)`) confirmed stable
- `.planning/milestones/v3/phases/026-oauth-stealth-bypass-guard/026-RESEARCH.md` — `ProviderRouter.select(cred, deps)` interface confirmed stable; Phase 027 does not need to change `select()`
- `src/state_core/providers/litellm_client.py` — confirmed `LitellmClient` passes `**kwargs` to `litellm.acompletion()`; Phase 028 will use this to pass `temperature`, `max_tokens` from the resolved profile
- `.planning/research/STACK.md` — `pydantic-settings>=2.7` confirmed as project standard for config loading

### Tertiary (LOW confidence)
- Model string defaults (`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`) — derived from ARCHITECTURE.md STEP.md example and ROADMAP.md Phase 031 reference. Anthropic model strings change with new releases. The `GlobalProfileConfig` fields (`quality_model`, `balanced_model`, `budget_model`) allow override without code changes. **Validate at Phase 031 parity-test time.**

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in `pyproject.toml`; no new packages needed
- Architecture (ModelProfile + resolve_profile): HIGH — PRV-04 requirement text, ARCHITECTURE.md STEP.md frontmatter, and `chat.params` hook type are all definitive sources
- chat.params output keys: HIGH — read directly from `packages/plugin/src/index.ts` line 248-254
- Model string defaults: LOW — ARCHITECTURE.md provides examples but Anthropic model strings evolve; treat as configurable placeholders
- HTTP handler framework: LOW — `state_daemon/server.py` was not read in this research; planner must verify before writing `hooks.py`

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (stable domain; revisit if AnthropicClient interface changes in Phase 029/030 or if opencode's `chat.params` hook type changes)
