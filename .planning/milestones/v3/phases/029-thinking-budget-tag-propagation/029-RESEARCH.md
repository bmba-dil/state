# Phase 029: Thinking-budget tag propagation — Research

**Researched:** 2026-05-04
**Domain:** Anthropic extended thinking propagation — ResolvedProfile.thinking_budget_tokens -> AnthropicClient.create(thinking=...)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — discuss phase was skipped per `workflow.skip_discuss`. All implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices — propagation adapter design, test coverage scope, file placement, constraint validation logic.

### Deferred Ideas (OUT OF SCOPE)
None declared.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRV-08 | Thinking-budget tag propagation (`thinking.budget_tokens`) for Anthropic extended thinking | Phase 025 built `AnthropicClient.create(thinking=ThinkingConfigParam)` with full passthrough. Phase 027 built `ResolvedProfile.thinking_budget_tokens` (quality=4000, others=None) + `build_chat_params()` which puts it in `options["thinking_budget_tokens"]`. Phase 029's job is the bridge: a `build_thinking_param()` function that converts `ResolvedProfile.thinking_budget_tokens → ThinkingConfigParam`, plus the validated call path `AnthropicClient.create(..., thinking=build_thinking_param(resolved))`. Regression test with capture validates the full path end-to-end. |
</phase_requirements>

---

## Summary

Phase 025 (direct Anthropic SDK escape hatch) already implements `AnthropicClient.create(thinking=ThinkingConfigParam)` and the 18 tests confirming it passes `thinking=` correctly to the wire. Phase 027 (model-profile resolver) already sets `ResolvedProfile.thinking_budget_tokens = 4000` for the quality profile and `None` for balanced/budget.

The gap Phase 029 closes is the **bridge layer**: a utility function that converts `ResolvedProfile.thinking_budget_tokens` to the `ThinkingConfigParam` TypedDict that `AnthropicClient.create(thinking=)` expects, plus the **call-site adapter** that reads this conversion in the path where ProviderRouter selects AnthropicClient. Additionally, the phase mandates a **regression test with capture** — a test that verifies the full flow from profile resolution through to the wire body, asserting that `thinking.budget_tokens` in the HTTP request body matches the profile value.

There is also a constraint-validation gap: `model_profile.py` documents "negative values are rejected by AnthropicClient (Phase 025/029)" but the budget constraint check (budget_tokens >= 1024, < max_tokens) is currently deferred to the Anthropic API (a 400 server error). Phase 029 should add a pre-flight guard in the propagation adapter so constraint violations surface as `ProviderBadRequestError` before any network call.

**Primary recommendation:** Add `build_thinking_param(resolved: ResolvedProfile, max_tokens: int) -> ThinkingConfigParam | None` to `model_profile.py`, add its call in a new `propagate_thinking_budget(resolved, anthropic_client, model, messages, max_tokens, **kwargs)` helper in `state_core/providers/`, and add a regression test file `tests/test_thinking_budget_propagation.py` with capture tests verifying the wire body.

---

## What Phase 025 Already Provides (Do Not Rebuild)

Phase 025 is VERIFIED (score 9/9, 820 tests green as of 2026-05-03). It provides:

- `AnthropicClient.create(thinking=ThinkingConfigParam | None)` — passthrough to `messages.create()`; tested by `test_thinking_budget_passed_through`, `test_thinking_blocks_preserved`, `test_adaptive_thinking_accepted`
- `AnthropicClient.stream(thinking=ThinkingConfigParam | None)` — streaming passthrough; tested by `test_stream_thinking_delta_yielded`
- `ThinkingBlock` and `RedactedThinkingBlock` preserved in returned `Message` — tested
- SDK type imports: `from anthropic.types.thinking_config_param import ThinkingConfigParam`

Phase 029 must NOT rebuild any of this. The unit tests from Phase 025 are the regression suite for `AnthropicClient` itself.

## What Phase 027 Already Provides (Do Not Rebuild)

Phase 027 is VERIFIED (27 tests green). It provides:

- `ResolvedProfile.thinking_budget_tokens: int | None` — `4000` for quality, `None` for balanced/budget
- `build_chat_params(resolved)` — serializes to `options: {"thinking_budget_tokens": 4000}` for the TS hook output
- `resolve_profile(...)` — inheritance chain resolver

Phase 029 must NOT rebuild any of this. The existing `test_quality_profile_includes_thinking_budget` test covers the profile side.

## The Actual Gap (What Phase 029 Must Build)

The gap is in `state_core/providers/` — there is no function that converts `ResolvedProfile.thinking_budget_tokens` to a `ThinkingConfigParam` for use with `AnthropicClient.create()`. Currently:

- `hooks.py:handle_chat_params()` calls `build_chat_params(resolved)` → returns `options: {"thinking_budget_tokens": 4000}` to the TS shim
- The TS shim passes this to the model call via opencode
- But `AnthropicClient.create(thinking=...)` is called from Python code, not the TS shim

The Python-side inference path needs: `resolved.thinking_budget_tokens` → `ThinkingConfigParam({"type": "enabled", "budget_tokens": N})` → passed as `thinking=` to `AnthropicClient.create()`.

The Phase 027 RESEARCH.md explicitly documents this as Phase 029's responsibility:
> "The AnthropicClient path (Phase 029) reads `thinking_budget_tokens` from `options`; the litellm path ignores it."

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | 0.96.0 (pinned >=0.80.0) | `ThinkingConfigParam`, `ThinkingConfigEnabledParam`, `ThinkingBlock`, `ThinkingDelta` | Project pin; already installed and tested |
| `pytest-httpx` | 0.36.2 | `HTTPXMock` — wire-level body capture for regression tests | Already used in Phase 025 tests; same pattern applies |
| `pytest-asyncio` | 1.3.0+ | `asyncio_mode = "auto"` for async tests | Already configured |

### No New Dependencies
All libraries needed are already installed. No `pyproject.toml` changes required.

---

## Architecture Patterns

### Recommended File Layout

```
src/state_core/providers/
├── model_profile.py       # Phase 027 — add build_thinking_param() here
├── anthropic_client.py    # Phase 025 — UNTOUCHED (no changes needed)
├── router.py              # Phase 026 — UNTOUCHED
└── ...

tests/
└── test_thinking_budget_propagation.py   # NEW — Phase 029 regression tests
```

No changes to `anthropic_client.py` are expected. The bridge belongs in `model_profile.py` (where `ResolvedProfile` is defined) or as a standalone module. Keeping it in `model_profile.py` avoids a circular import (model_profile.py already does not import from anthropic_client.py; the conversion function just returns a TypedDict).

**IMPORTANT:** `build_thinking_param()` in `model_profile.py` must import `ThinkingConfigParam` from `anthropic.types` — confirm this does not break mode isolation (it doesn't: `anthropic` is in the shared kernel `state_core.providers`, not in `state_build` or `state_teach`).

### Pattern 1: `build_thinking_param()` — Profile to ThinkingConfigParam Conversion

**What:** Convert `ResolvedProfile.thinking_budget_tokens` to a `ThinkingConfigParam` dict.
**When to use:** At the call site where `AnthropicClient.create()` is invoked with a `ResolvedProfile`.

```python
# Source: anthropic 0.96.0 types/thinking_config_enabled_param.py + types/thinking_config_param.py
from anthropic.types.thinking_config_param import ThinkingConfigParam

def build_thinking_param(
    resolved: ResolvedProfile,
    max_tokens: int,
) -> ThinkingConfigParam | None:
    """Convert ResolvedProfile.thinking_budget_tokens to ThinkingConfigParam.

    Returns None if thinking_budget_tokens is None (balanced/budget profiles).
    Returns ThinkingConfigEnabledParam if budget_tokens is set.

    Pre-flight validation:
      - budget_tokens must be >= 1024 (Anthropic API minimum)
      - budget_tokens must be < max_tokens (Anthropic API constraint)

    Raises ProviderBadRequestError (not ValueError) so callers see a consistent
    error hierarchy — the same error they'd get from the Anthropic API itself.

    Args:
        resolved:   ResolvedProfile from resolve_profile(). If thinking_budget_tokens
                    is None, returns None (no thinking for this call).
        max_tokens: The max_tokens to be passed to AnthropicClient.create().
                    Used for pre-flight constraint validation only.
    """
    budget = resolved.thinking_budget_tokens
    if budget is None:
        return None

    # Pre-flight validation — avoid a round-trip 400 from Anthropic API
    if budget < 1024:
        from state_core.providers.errors import ProviderBadRequestError
        raise ProviderBadRequestError(
            f"thinking.budget_tokens must be >= 1024, got {budget}"
        )
    if budget >= max_tokens:
        from state_core.providers.errors import ProviderBadRequestError
        raise ProviderBadRequestError(
            f"thinking.budget_tokens ({budget}) must be < max_tokens ({max_tokens})"
        )

    return {"type": "enabled", "budget_tokens": budget}
```

**Why lazy import for `ProviderBadRequestError`:** `model_profile.py` currently imports nothing from `state_core.providers.errors`. Adding a lazy import only in the error branch avoids adding a module-level dependency from `model_profile` onto `errors` (cleaner for `model_profile` which is intentionally limited in its deps per the module docstring: "imports are limited to stdlib, pydantic, pydantic_settings, and structlog only"). An alternative is to raise `ValueError` and let the caller re-wrap, but that breaks the error hierarchy contract. The cleanest approach is to move `build_thinking_param` out of `model_profile.py` and into a thin `thinking_budget.py` module in `state_core/providers/` that can freely import from `errors.py`.

### Pattern 2: `thinking_budget.py` — Preferred File Placement

To avoid adding an `anthropic` SDK import to `model_profile.py` (which the module docstring says is stdlib/pydantic/pydantic_settings/structlog only), put `build_thinking_param()` in a dedicated thin module:

```
src/state_core/providers/
├── thinking_budget.py    # NEW — Phase 029 bridge utility
```

```python
# src/state_core/providers/thinking_budget.py
"""Thinking-budget tag propagation adapter (PRV-08, Phase 029).

Bridges ResolvedProfile.thinking_budget_tokens to the ThinkingConfigParam
TypedDict required by AnthropicClient.create(thinking=...).

Design rationale:
- model_profile.py has a constrained import policy (no SDK deps).
- anthropic_client.py accepts ThinkingConfigParam directly (no ResolvedProfile dep).
- This module is the bridge between the two, with pre-flight constraint validation.
"""
from __future__ import annotations

from anthropic.types.thinking_config_param import ThinkingConfigParam
from state_core.providers.errors import ProviderBadRequestError
from state_core.providers.model_profile import ResolvedProfile


def build_thinking_param(
    resolved: ResolvedProfile,
    max_tokens: int,
) -> ThinkingConfigParam | None:
    """Convert ResolvedProfile.thinking_budget_tokens to ThinkingConfigParam.

    Returns None if thinking_budget_tokens is None (no extended thinking).
    Returns {"type": "enabled", "budget_tokens": N} if set.

    Raises ProviderBadRequestError if the budget violates Anthropic's constraints:
      - budget_tokens < 1024
      - budget_tokens >= max_tokens
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
    return {"type": "enabled", "budget_tokens": budget}
```

### Pattern 3: Regression Test — Wire Capture (The Core of Phase 029)

The goal is "regression test with capture" — meaning the test inspects the actual HTTP request body sent to the Anthropic API and asserts `body["thinking"]["budget_tokens"]` matches the profile's value. This is the same `HTTPXMock` pattern already established in Phase 025.

```python
# tests/test_thinking_budget_propagation.py
# Source: same HTTPXMock pattern from tests/test_anthropic_client.py (Phase 025)
import json
import httpx
import pytest
from pytest_httpx import HTTPXMock
from state_core.auth.base import OAuthCredential
from state_core.deps import Deps
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.model_profile import ModelProfile, resolve_profile
from state_core.providers.thinking_budget import build_thinking_param
from state_core.providers.errors import ProviderBadRequestError

FAKE_OAUTH_CRED = OAuthCredential(
    access="sk-ant-oat-fake",
    refresh="sk-ant-oat-fake-refresh",
    expires=9_999_999_999.0,
    provider_id="anthropic",
)

_MSG_RESPONSE = {
    "id": "msg_01test",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello!"}],
    "model": "claude-opus-4-7",
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 5,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    },
}


async def test_quality_profile_propagates_budget_to_wire(
    httpx_mock: HTTPXMock,
) -> None:
    """quality profile -> thinking.budget_tokens=4000 appears in request body (PRV-08)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    resolved = resolve_profile(step_profile=ModelProfile.quality)
    max_tokens = 16000
    thinking_param = build_thinking_param(resolved, max_tokens=max_tokens)

    deps = Deps(http_client=httpx.AsyncClient())
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model=resolved.model,
        messages=[{"role": "user", "content": "Plan this arc."}],
        max_tokens=max_tokens,
        thinking=thinking_param,
    )
    req = httpx_mock.get_requests()[0]
    body = json.loads(req.content)
    assert body["thinking"]["type"] == "enabled"
    assert body["thinking"]["budget_tokens"] == 4000


async def test_balanced_profile_no_thinking_param(
    httpx_mock: HTTPXMock,
) -> None:
    """balanced profile -> build_thinking_param returns None -> thinking key absent from body (PRV-08)."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,
    )
    resolved = resolve_profile(step_profile=ModelProfile.balanced)
    thinking_param = build_thinking_param(resolved, max_tokens=4096)
    assert thinking_param is None

    deps = Deps(http_client=httpx.AsyncClient())
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model=resolved.model,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=4096,
        thinking=thinking_param,
    )
    req = httpx_mock.get_requests()[0]
    body = json.loads(req.content)
    assert "thinking" not in body
```

### Pattern 4: Constraint Validation Tests

```python
def test_budget_tokens_below_minimum_raises() -> None:
    """budget_tokens < 1024 -> ProviderBadRequestError (pre-flight, no network call)."""
    from state_core.providers.model_profile import ResolvedProfile, ModelProfile
    resolved = ResolvedProfile(
        profile=ModelProfile.quality,
        model="claude-opus-4-7",
        temperature=0.2,
        thinking_budget_tokens=500,  # below 1024 minimum
    )
    with pytest.raises(ProviderBadRequestError, match="must be >= 1024"):
        build_thinking_param(resolved, max_tokens=16000)


def test_budget_tokens_ge_max_tokens_raises() -> None:
    """budget_tokens >= max_tokens -> ProviderBadRequestError (pre-flight, no network call)."""
    from state_core.providers.model_profile import ResolvedProfile, ModelProfile
    resolved = ResolvedProfile(
        profile=ModelProfile.quality,
        model="claude-opus-4-7",
        temperature=0.2,
        thinking_budget_tokens=8000,
    )
    with pytest.raises(ProviderBadRequestError, match="must be < max_tokens"):
        build_thinking_param(resolved, max_tokens=8000)  # equal: budget >= max_tokens
```

### Anti-Patterns to Avoid

- **Modifying `anthropic_client.py`:** `AnthropicClient.create(thinking=...)` already accepts and passes `ThinkingConfigParam`. No changes needed there.
- **Adding `anthropic` SDK imports to `model_profile.py`:** The module docstring explicitly constrains to "stdlib, pydantic, pydantic_settings, and structlog only". Put the bridge logic in `thinking_budget.py`.
- **Checking `isinstance(client, AnthropicClient)` to gate thinking:** The gate is `resolved.thinking_budget_tokens is not None`. If the profile has a budget, pass it; if not, pass `None`. `AnthropicClient` already handles `thinking=None` by omitting the param.
- **Using `thinking.type="adaptive"` in the propagation adapter:** `ResolvedProfile.thinking_budget_tokens` is a concrete integer — it maps to `{"type": "enabled", "budget_tokens": N}`. Adaptive thinking (`{"type": "adaptive"}`) is a separate opt-in, not driven by the profile budget field. Do not conflate the two.
- **Calling litellm with `thinking=` param:** litellm does not support `thinking=`. The `build_thinking_param()` result should only ever be passed to `AnthropicClient.create()`, not to `LitellmClient.acompletion()`. The gate belongs in the call site.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `thinking=` serialization | Custom JSON dict construction | `ThinkingConfigParam` TypedDict = `{"type": "enabled", "budget_tokens": N}` — already a plain dict | SDK accepts dict directly; no class instantiation needed |
| Budget constraint validation | Server-round-trip to get 400 | Pre-flight check in `build_thinking_param()` | Avoids wasted network call; same error class as the SDK error |
| Wire-level capture in tests | `unittest.mock.patch` on create() | `HTTPXMock` + `json.loads(req.content)` | Already established pattern in Phase 025; validates actual HTTP body, not just that a method was called |

---

## Common Pitfalls

### Pitfall 1: budget_tokens >= max_tokens Causes Anthropic 400

**What goes wrong:** If `thinking.budget_tokens` equals or exceeds `max_tokens`, the Anthropic API returns `{"error": {"type": "invalid_request_error", "message": "budget_tokens must be less than max_tokens"}}` as a 400. Phase 025's `AnthropicClient.create()` maps this to `ProviderBadRequestError`, but it still causes a network round-trip.

**Why it happens:** SDK does not validate this client-side. The quality profile's default `thinking_budget_tokens=4000` will trigger this if a caller passes `max_tokens <= 4000`.

**How to avoid:** `build_thinking_param()` validates `budget < max_tokens` before returning. Callers using the quality profile with extended thinking should set `max_tokens > 4000` (e.g., 8192 or 16000).

**Warning signs:** Tests with quality profile + small max_tokens produce `ProviderBadRequestError`.

### Pitfall 2: thinking_budget_tokens Must Not Flow to LitellmClient

**What goes wrong:** If `build_thinking_param(resolved)` result is passed as a kwarg to `LitellmClient.acompletion(..., thinking=...)`, litellm will raise `UnsupportedParamsError` (for Anthropic) or silently ignore it (for other providers).

**Why it happens:** Phase 027 RESEARCH documents this explicitly: "Phase 028 is responsible for gating thinking_budget_tokens to AnthropicClient-only paths." The model_profile layer does not know the routing decision.

**How to avoid:** The call site that calls `build_thinking_param()` must only pass the result to `AnthropicClient.create()`. The `ProviderRouter.select()` return type (`AnthropicClient | LitellmClient`) is the gating point. Pattern: `if isinstance(client, AnthropicClient): thinking=build_thinking_param(resolved, max_tokens) else: thinking=None`.

**Warning signs:** `UnsupportedParamsError` in parity matrix tests (Phase 031) when a non-OAuth credential routes through litellm with quality profile.

### Pitfall 3: budget_tokens < 1024 on the Quality Profile Default

**What goes wrong:** The quality profile defaults to `thinking_budget_tokens=4000`. But a caller could pass an override like `resolve_profile(overrides={"thinking_budget_tokens": 512})`. The SDK minimum is 1024.

**Why it happens:** `ResolvedProfile` has no `ge=1024` constraint on `thinking_budget_tokens` (it would reject None). The model_profile layer doesn't validate against SDK constraints.

**How to avoid:** `build_thinking_param()` validates `budget >= 1024` before returning. This catches any invalid override before the network call.

**Warning signs:** `ProviderBadRequestError: must be >= 1024` in tests that use small budgets.

### Pitfall 4: MODELS_TO_WARN_WITH_THINKING_ENABLED Applies to Newer Models

**What goes wrong:** For `claude-opus-4-6` and `claude-mythos-preview`, the SDK warns that `type="enabled"` should use `type="adaptive"` instead. `build_thinking_param()` currently always returns `type="enabled"`.

**Why it happens:** Newer models prefer adaptive thinking (the model decides when to think). The `type="enabled"` form is still accepted but generates an SDK warning.

**How to avoid:** For Phase 029 scope: keep `type="enabled"` — it is still supported and matches the `budget_tokens` integer field in `ResolvedProfile`. Document that if the project adopts `claude-opus-4-6` or later as the quality model, the caller can switch to `{"type": "adaptive"}` (which ignores `budget_tokens`). Phase 029 should not auto-detect the model and switch to adaptive — that would be a separate enhancement.

**Warning signs:** SDK warning logs about `type="enabled"` when using claude-opus-4-6 model strings.

---

## Code Examples

Verified patterns from installed sources:

### Full `thinking_budget.py` Module

```python
# src/state_core/providers/thinking_budget.py
# Source: anthropic 0.96.0 types/thinking_config_enabled_param.py; project patterns from errors.py
"""Thinking-budget tag propagation adapter (PRV-08, Phase 029).

Bridges ResolvedProfile.thinking_budget_tokens to the ThinkingConfigParam
TypedDict required by AnthropicClient.create(thinking=...).
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

    Returns None if thinking_budget_tokens is None.
    Returns {"type": "enabled", "budget_tokens": N} if set.

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
```

### Wire Capture in Tests

```python
# Source: same HTTPXMock pattern as tests/test_anthropic_client.py (Phase 025)
import json
import httpx
from pytest_httpx import HTTPXMock
from state_core.providers.anthropic_client import AnthropicClient
from state_core.providers.model_profile import ModelProfile, resolve_profile
from state_core.providers.thinking_budget import build_thinking_param
from state_core.deps import Deps
from state_core.auth.base import OAuthCredential

async def test_quality_profile_propagates_budget_to_wire(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.anthropic.com/v1/messages?beta=true",
        json=_MSG_RESPONSE,   # minimal valid Message JSON
    )
    resolved = resolve_profile(step_profile=ModelProfile.quality)
    thinking_param = build_thinking_param(resolved, max_tokens=16000)

    deps = Deps(http_client=httpx.AsyncClient())
    client = AnthropicClient(FAKE_OAUTH_CRED, deps)
    await client.create(
        model=resolved.model,
        messages=[{"role": "user", "content": "Plan this."}],
        max_tokens=16000,
        thinking=thinking_param,
    )
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["thinking"]["type"] == "enabled"
    assert body["thinking"]["budget_tokens"] == 4000  # quality profile default
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `thinking.type="enabled"` always | `thinking.type="adaptive"` for claude-opus-4-6+ | anthropic 0.96.0 | SDK warns for newer models; `type="enabled"` still works but "adaptive" recommended |
| No bridge between profile and SDK param | `build_thinking_param(resolved, max_tokens)` in Phase 029 | Phase 029 (now) | Profile-driven thinking budget flows correctly to Anthropic API |
| Constraint violation caught at API level (400) | Pre-flight `ProviderBadRequestError` in `build_thinking_param` | Phase 029 (now) | Faster failure, no wasted network call |

**Deprecated/outdated:**
- `thinking.type="enabled"` for `claude-opus-4-6` and `claude-mythos-preview` — still works but SDK warns; project currently uses `claude-opus-4-7` for quality profile, so no immediate issue.

---

## Open Questions

1. **Should `build_thinking_param()` live in `model_profile.py` or a new `thinking_budget.py`?**
   - What we know: `model_profile.py` docstring says "imports are limited to stdlib, pydantic, pydantic_settings, and structlog only". Adding `from anthropic.types...` violates this constraint.
   - Recommendation: Use `thinking_budget.py`. Clean separation, no circular imports, respects the existing import policy.

2. **Should there be a call-site adapter that takes `ResolvedProfile + AnthropicClient` and calls `build_thinking_param` + `create()`?**
   - What we know: Phase 029's goal is propagation + regression test. The regression test itself calls `build_thinking_param()` + `AnthropicClient.create()` directly. A higher-level adapter is useful but may be Phase 030/031 scope.
   - What's unclear: Whether Phase 029 should wire the full `resolved_profile -> thinking_param -> create()` path in a single function, or just provide the conversion primitive.
   - Recommendation: For Phase 029, provide `build_thinking_param()` as the bridge primitive. The call site in actual daemon code (Phase 030+) will assemble the pieces. The regression test validates end-to-end correctness without requiring the full daemon stack.

3. **Does `ApiKeyCredential` path also need thinking budget propagation?**
   - What we know: `AnthropicClient` accepts both `OAuthCredential` and `ApiKeyCredential`. The thinking parameter works the same way for both. Phase 026 routes `ApiKeyCredential` through `LitellmClient`, not `AnthropicClient`.
   - What's unclear: Can a user configure a direct Anthropic API key and still get extended thinking via the AnthropicClient path?
   - Recommendation: Phase 029 tests should cover `OAuthCredential` (the primary path). `ApiKeyCredential` + `AnthropicClient` + thinking is theoretically possible but Phase 026 routes API keys through litellm. Document as future consideration, not Phase 029 scope.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0+ with pytest-asyncio 1.3.0+ (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| Quick run command | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-08 | `build_thinking_param(quality_resolved, max_tokens=16000)` returns `{"type": "enabled", "budget_tokens": 4000}` | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_build_thinking_param_quality_returns_enabled -x` | ❌ Wave 0 |
| PRV-08 | `build_thinking_param(balanced_resolved, max_tokens=4096)` returns `None` | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_build_thinking_param_balanced_returns_none -x` | ❌ Wave 0 |
| PRV-08 | `build_thinking_param(budget_resolved, max_tokens=4096)` returns `None` | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_build_thinking_param_budget_returns_none -x` | ❌ Wave 0 |
| PRV-08 | `budget_tokens < 1024` raises `ProviderBadRequestError` before any network call | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_budget_below_minimum_raises -x` | ❌ Wave 0 |
| PRV-08 | `budget_tokens >= max_tokens` raises `ProviderBadRequestError` before any network call | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_budget_ge_max_tokens_raises -x` | ❌ Wave 0 |
| PRV-08 | `budget_tokens == max_tokens - 1` is accepted (boundary: just below max_tokens) | unit | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_budget_exactly_below_max_tokens_accepted -x` | ❌ Wave 0 |
| PRV-08 | REGRESSION CAPTURE: quality profile -> `thinking.budget_tokens=4000` in HTTP request body wire | unit (httpx_mock capture) | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_quality_profile_propagates_budget_to_wire -x` | ❌ Wave 0 |
| PRV-08 | REGRESSION CAPTURE: balanced profile -> `thinking` key absent from HTTP request body | unit (httpx_mock capture) | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_balanced_profile_no_thinking_in_wire -x` | ❌ Wave 0 |
| PRV-08 | REGRESSION CAPTURE: custom budget (resolve_profile with override) -> correct budget_tokens in body | unit (httpx_mock capture) | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_custom_budget_propagates_to_wire -x` | ❌ Wave 0 |
| PRV-08 | `thinking_budget.py` mode isolation: no `state_build.*` or `state_teach.*` imports | import | `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py::test_no_mode_silo_import -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/test_thinking_budget_propagation.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Phase gate:** Full suite green (currently 865 collected) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_thinking_budget_propagation.py` — all 10 RED stubs listed above
- [ ] `src/state_core/providers/thinking_budget.py` — module (created in Wave 1 GREEN)

*(No framework gaps — pytest infrastructure and HTTPXMock pattern fully operational from Phase 025.)*

---

## Sources

### Primary (HIGH confidence)
- `anthropic 0.96.0` installed at `.venv/lib/python3.12/site-packages/anthropic/`:
  - `types/thinking_config_enabled_param.py` — `ThinkingConfigEnabledParam` with `budget_tokens: Required[int]`, `type: Required[Literal["enabled"]]`; constraint `>= 1024 and < max_tokens` in docstring
  - `types/thinking_config_adaptive_param.py` — `ThinkingConfigAdaptiveParam` with `type: "adaptive"` + `display`
  - `types/thinking_config_param.py` — `ThinkingConfigParam = Union[Enabled, Disabled, Adaptive]`
  - `types/thinking_block.py` — `ThinkingBlock(signature, thinking, type)`
  - `types/thinking_delta.py` — `ThinkingDelta(thinking, type="thinking_delta")`
  - `resources/messages/messages.py` — `MODELS_TO_WARN_WITH_THINKING_ENABLED = ["claude-opus-4-6", "claude-mythos-preview"]`
- `src/state_core/providers/anthropic_client.py` (Phase 025) — `create(thinking=ThinkingConfigParam | None)` — VERIFIED passing 18 tests including 3 PRV-08 tests
- `src/state_core/providers/model_profile.py` (Phase 027) — `ResolvedProfile.thinking_budget_tokens: int | None`; quality default `4000`; docstring "Propagated by Phase 029"; `build_chat_params()` includes thinking_budget_tokens in `options`
- `src/state_core/providers/errors.py` (Phase 025) — `ProviderBadRequestError` available for pre-flight validation
- `tests/test_anthropic_client.py` (Phase 025) — confirmed `test_thinking_budget_passed_through` captures `body["thinking"] == {"type": "enabled", "budget_tokens": 8192}` at wire level; same pattern applies for Phase 029 regression tests
- `.planning/milestones/v3/phases/027-model-profile-resolver/027-RESEARCH.md` — Pitfall 4 explicitly states "The AnthropicClient path (Phase 029) reads `thinking_budget_tokens` from `options`; the litellm path ignores it"
- `.venv/bin/python -m pytest tests/test_anthropic_client.py -x -q` — 18 passed in 0.34s (confirmed clean baseline)

### Secondary (MEDIUM confidence)
- `.planning/milestones/v3/phases/025-direct-anthropic-sdk-escape-hatch/025-VERIFICATION.md` — PRV-08 marked SATISFIED at Phase 025 scope (transport layer); Phase 029 extends to profile-driven propagation
- `.planning/milestones/v3/phases/027-model-profile-resolver/027-VERIFICATION.md` — confirmed `thinking_budget_tokens=4000` for quality profile is live in source

### Tertiary (LOW confidence)
- None — all critical claims verified from installed package source or project files.

---

## Metadata

**Confidence breakdown:**
- What Phase 025 provides: HIGH — verified from source + 18 passing tests
- What Phase 027 provides: HIGH — verified from source + passing tests
- Gap identification (build_thinking_param bridge): HIGH — model_profile.py docstring "Propagated by Phase 029" + 027-RESEARCH Pitfall 4 are explicit
- ThinkingConfigEnabledParam shape: HIGH — verified from installed anthropic 0.96.0 TypedDict source
- Constraint values (>=1024, <max_tokens): HIGH — from SDK docstring in thinking_config_enabled_param.py
- Placement decision (thinking_budget.py vs model_profile.py): HIGH — model_profile module docstring explicitly restricts imports

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (anthropic SDK thinking API is stable at 0.96.0; re-verify if bumped past 0.100.0 or if project adopts claude-opus-4-6+ as quality model, which changes the recommended thinking type)
