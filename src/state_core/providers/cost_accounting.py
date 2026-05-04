"""Cost accounting for provider inference calls — Phase 028 (PRV-05).

Provides three public symbols:
- compute_cost(model, input_tokens, output_tokens) -> float | None
  Uses litellm.completion_cost() with a mock ModelResponse. Returns None
  (never 0.0) for models not in litellm's cost map.
- ProviderCostEmitter: wraps LitellmClient or AnthropicClient calls,
  emitting state.provider.request / state.provider.response domain events
  via SqliteEventStore.append(). Non-streaming only (streaming is Phase 030+).
- aggregate_provider_costs(store, scope_type=None) -> dict[str, dict]
  Reads state.provider.response events and produces per-scope rollups.

Mode isolation: this module imports only from state_core.*  and stdlib.
No build-mode or teach-mode packages are imported here.

Tech debt: Streaming calls not instrumented — deferred to Phase 030+.
"""
from __future__ import annotations

import time
from typing import Any

import litellm
import structlog
from litellm.types.utils import ModelResponse, Usage
from ulid import ULID

from state_core.events import SqliteEventStore
from state_core.schema import Mode, ProviderRequestData, ProviderResponseData

log = structlog.get_logger(__name__)


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Compute cost in USD using litellm's cost map.

    Works for both litellm and Anthropic SDK paths. Model names
    claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5, gpt-4o
    are confirmed in litellm.model_cost as of litellm 1.83.0.

    Returns:
        Cost in USD as a float, or None when the model is not in
        litellm's cost map. Never returns 0.0 for unknown models —
        0.0 is ambiguous with genuinely free-tier calls.
    """
    try:
        mock = ModelResponse()
        mock.model = model
        mock.usage = Usage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
        return litellm.completion_cost(completion_response=mock)
    except Exception:
        return None


class ProviderCostEmitter:
    """Wraps LitellmClient or AnthropicClient to emit cost-accounting events.

    Emits state.provider.request before the call and state.provider.response
    after the call (or on error). Both events share the same request_id ULID
    for correlation.

    Non-streaming only: streaming response usage is not accumulated in a
    form accessible by completion_cost(). Streaming instrumentation is
    deferred to Phase 030 (tech debt).

    Usage:
        emitter = ProviderCostEmitter(store=store, mode="build")
        response = await emitter.acompletion(
            client=litellm_client,
            model="claude-sonnet-4-6",
            messages=messages,
            scope_type="step",
            scope_id="step-17.3",
        )
    """

    def __init__(self, store: SqliteEventStore, mode: Mode = "kernel") -> None:
        self._store = store
        self._mode = mode

    async def acompletion(
        self,
        client: Any,
        model: str,
        messages: list[dict[str, Any]],
        *,
        scope_type: str,
        scope_id: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an inference call with cost-accounting event emission.

        Emits state.provider.request before the call (awaited).
        Emits state.provider.response after the call (awaited).
        On exception: emits state.provider.response with error field set,
        then re-raises the original exception.

        Args:
            client: LitellmClient or AnthropicClient instance.
            model: litellm model string or Anthropic model ID.
            messages: List of message dicts (OpenAI-format).
            scope_type: Scope level — 'step', 'slice', 'phase', or 'arc'.
            scope_id: Scope instance ID, e.g. 'step-17.3', 'arc-01'.
            **kwargs: Forwarded to client.acompletion().

        Returns:
            The raw response from client.acompletion() (ModelResponse or
            anthropic.types.Message depending on client type).

        Raises:
            Whatever client.acompletion() raises, unchanged.
        """
        request_id = str(ULID())
        aggregate_id = f"provider:{scope_type}:{scope_id}"

        await self._store.append(
            aggregate_type="provider",
            aggregate_id=aggregate_id,
            event_type="state.provider.request",
            data=ProviderRequestData(
                model=model,
                scope_type=scope_type,
                scope_id=scope_id,
                request_id=request_id,
            ).model_dump(),
            mode=self._mode,
        )

        t0 = time.monotonic()
        try:
            response = await client.acompletion(model=model, messages=messages, **kwargs)
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            await self._store.append(
                aggregate_type="provider",
                aggregate_id=aggregate_id,
                event_type="state.provider.response",
                data=ProviderResponseData(
                    model=model,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    request_id=request_id,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_usd=None,
                    latency_ms=latency_ms,
                    error=type(exc).__name__,
                ).model_dump(),
                mode=self._mode,
            )
            raise

        latency_ms = int((time.monotonic() - t0) * 1000)
        usage = response.usage

        # litellm path: prompt_tokens / completion_tokens (public fields)
        # Anthropic SDK path: input_tokens / output_tokens
        # ProviderCostEmitter uses litellm-style field names (LitellmClient normalizes).
        # For AnthropicClient, callers must wrap the response before passing usage.
        # Phase 028 scope: litellm path only; Anthropic SDK path is Phase 030+.
        input_tokens: int = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0)
        output_tokens: int = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", 0)
        total_tokens: int = getattr(usage, "total_tokens", input_tokens + output_tokens)

        # Cache tokens: PrivateAttr on litellm Usage (not in model_dump())
        cache_read_tokens: int = getattr(usage, "_cache_read_input_tokens", 0) or 0
        cache_creation_tokens: int = getattr(usage, "_cache_creation_input_tokens", 0) or 0

        cost = compute_cost(model, input_tokens, output_tokens)

        await self._store.append(
            aggregate_type="provider",
            aggregate_id=aggregate_id,
            event_type="state.provider.response",
            data=ProviderResponseData(
                model=model,
                scope_type=scope_type,
                scope_id=scope_id,
                request_id=request_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
            ).model_dump(),
            mode=self._mode,
        )

        log.debug(
            "provider_cost_emitted",
            model=model,
            scope=f"{scope_type}:{scope_id}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        )

        return response


async def aggregate_provider_costs(
    store: SqliteEventStore,
    scope_type: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Aggregate cost + token stats from state.provider.response events.

    Reads all events from the store (mode=None = all modes), filters to
    state.provider.response events, and groups by scope_type:scope_id.

    total_cost_usd is the sum of non-None cost_usd values. If any call in
    the scope has cost_usd=None, has_unknown_cost=True and total_cost_usd
    is a partial sum (undercounting). Callers must check has_unknown_cost.

    Args:
        store: SqliteEventStore to read events from.
        scope_type: Filter to a specific scope level ('step', 'slice',
            'phase', 'arc'). None = return all scope types.

    Returns:
        Dict keyed by '{scope_type}:{scope_id}', e.g.:
        {
          "step:step-17.3": {
            "scope_type": "step",
            "scope_id": "step-17.3",
            "call_count": 3,
            "total_input_tokens": 4200,
            "total_output_tokens": 1800,
            "total_tokens": 6000,
            "total_cost_usd": 0.0315,
            "has_unknown_cost": False,
          },
          ...
        }
    """
    events = await store.read_events()
    response_events = [
        e for e in events
        if e["type"] == "state.provider.response"
    ]

    rollup: dict[str, dict[str, Any]] = {}
    for ev in response_events:
        data = ev["data"]
        st_val = data["scope_type"]
        sid = data["scope_id"]
        if scope_type is not None and st_val != scope_type:
            continue

        key = f"{st_val}:{sid}"
        if key not in rollup:
            rollup[key] = {
                "scope_type": st_val,
                "scope_id": sid,
                "call_count": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "has_unknown_cost": False,
            }

        entry = rollup[key]
        entry["call_count"] += 1
        entry["total_input_tokens"] += data.get("input_tokens", 0)
        entry["total_output_tokens"] += data.get("output_tokens", 0)
        entry["total_tokens"] += data.get("total_tokens", 0)

        cost = data.get("cost_usd")
        if cost is None:
            entry["has_unknown_cost"] = True
        else:
            entry["total_cost_usd"] += cost

    return rollup
