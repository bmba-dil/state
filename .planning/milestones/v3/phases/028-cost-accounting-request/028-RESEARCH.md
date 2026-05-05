# Phase 028: Cost Accounting Per Request (Event Emission + Aggregation) - Research

**Researched:** 2026-05-03
**Domain:** litellm cost API, event store integration, per-scope SQLite aggregation, state.provider.* event taxonomy
**Confidence:** HIGH

## Summary

Phase 028 adds cost-accounting instrumentation to both inference paths (LitellmClient and AnthropicClient). Every completed inference call emits two domain events: `state.provider.request` (pre-call) and `state.provider.response` (post-call, with usage + cost_usd). A separate aggregator function reads these events from SQLite and produces per-scope rollups (Step / Slice / Phase / Arc).

The cost calculation relies on `litellm.completion_cost(completion_response)` for the litellm path, and a direct lookup in `litellm.model_cost` for the Anthropic SDK path. Both calculation routes use the same model name strings already in the project (`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`), which are confirmed to be in litellm's cost map. When `completion_cost` raises (unmapped model, unknown provider), cost_usd is stored as `null` — never 0.0. This distinction matters for the aggregator.

The phase integrates with the existing `SqliteEventStore.append()` from Phase 004 (aggregate_type="provider", aggregate_id derived from request scope) and with `LitellmClient`/`AnthropicClient` from Phases 024/025. No new infrastructure is needed. The work splits cleanly into two waves: Wave 1 adds the new event schema models + `compute_cost()` helper (no new files), Wave 2 implements the two emitter wrappers and the aggregator query function.

**Primary recommendation:** Add a `ProviderCostEmitter` class to `state_core/providers/cost_accounting.py` that wraps `LitellmClient.acompletion()` and `AnthropicClient.create()` calls, emitting request/response events via `SqliteEventStore.append()`. The aggregator is a standalone `aggregate_provider_costs()` coroutine that runs `GROUP BY scope` SQL on the events table — no in-memory accumulation.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRV-05 | Cost accounting per request, aggregated per Step / Slice / Phase / Arc in SQLite | Emit `state.provider.request`/`state.provider.response` events via Phase 004's `SqliteEventStore.append()`; aggregate with SQL `GROUP BY` on the events table; cost_usd from `litellm.completion_cost()` or direct `litellm.model_cost` lookup |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.83.0 (pinned >=1.80.0) | `litellm.completion_cost(response)` returns cost_usd as float | Already in project; confirmed to map claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5, gpt-4o |
| aiosqlite | 0.22.1 | `SqliteEventStore.append()` writes provider events; aggregator reads via `read_events()` | Phase 004 provides; no new work |
| pydantic | 2.13.2+ | Pydantic models for request/response event data payloads (`ProviderRequestData`, `ProviderResponseData`) | Project standard for all event data models |
| structlog | 25.1+ | Logging in cost_accounting.py | Project standard |

### Supporting (test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | 1.3.0 | `asyncio_mode = "auto"` already set in pyproject.toml | All async test functions |
| freezegun | 1.5 | Freeze time for deterministic ts fields in emitted events | Tests that assert event timestamps |
| hypothesis | 6.152.1 | Property tests on aggregator (various token counts, multiple scopes) | Coverage without enumerating all integer combinations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `litellm.completion_cost(response)` | `litellm.model_cost[model]` dict lookup | `completion_cost` handles provider prefix stripping and edge cases; direct lookup requires manual arithmetic but works for AnthropicClient path where response is not a `ModelResponse` |
| SQL `GROUP BY scope` in `aggregate_provider_costs()` | In-memory accumulation via `read_events()` | SQL aggregation is simpler, memory-safe, requires no intermediate data structure; in-memory works but is O(n) memory |
| New `ProviderCostEmitter` wrapper class | Modify `LitellmClient` and `AnthropicClient` directly | Wrapper keeps cost logic separate from inference logic; easier to test in isolation; avoids touching Phase 024/025 files |

**Installation:** No new packages required. All libraries already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended File Layout
```
src/state_core/providers/
├── __init__.py
├── anthropic_client.py      # Phase 025: AnthropicClient.create() — UNTOUCHED by 028
├── cost_accounting.py       # NEW — Phase 028 (this phase)
├── errors.py                # Phase 025 extract — UNTOUCHED
├── litellm_client.py        # Phase 024: LitellmClient — UNTOUCHED
├── model_profile.py         # Phase 027: ModelProfile resolver — UNTOUCHED
└── router.py                # Phase 026: ProviderRouter — UNTOUCHED

src/state_core/
└── schema.py                # Add ProviderRequestData, ProviderResponseData models + PROVIDER_EVENT_TYPES
```

```
tests/
└── test_cost_accounting.py  # NEW — Wave 0 RED stubs, Wave 1 GREEN
```

**Key constraint:** `state_core.providers.cost_accounting` must not import `state_build.*` or `state_teach.*` (mode isolation rule). It imports only from `state_core.providers.{litellm_client, anthropic_client}`, `state_core.events`, and `state_core.schema`.

### Pattern 1: Event taxonomy for provider aggregate

The events table uses `aggregate_type` and `aggregate_id`. For provider events, use:

```python
# aggregate_type = "provider"
# aggregate_id = f"provider:{scope_type}:{scope_id}"
# where scope_type in ("step", "slice", "phase", "arc")
# e.g. "provider:step:step-17.3" or "provider:arc:arc-01"

# event types:
# "state.provider.request"    — emitted before the call
# "state.provider.response"   — emitted after the call (with usage + cost)
```

This gives a natural `read_stream(aggregate_id="provider:step:step-17.3")` query path
for per-scope cost retrieval.

The `AggregateType` literal in `schema.py` must be extended with `"provider"`.

### Pattern 2: ProviderRequestData and ProviderResponseData Pydantic models

```python
# Source: consistent with existing data model pattern in schema.py
# All event data models use extra="forbid", frozen=True

class ProviderRequestData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model: str                    # litellm model string or Anthropic model ID
    scope_type: str               # "step" | "slice" | "phase" | "arc"
    scope_id: str                 # e.g. "step-17.3", "arc-01"
    request_id: str               # ULID — correlates request event to response event
    prompt_tokens_estimate: int | None = None   # optional pre-call estimate

class ProviderResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model: str
    scope_type: str
    scope_id: str
    request_id: str               # same ULID as ProviderRequestData — correlation key
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None        # None when model is not in litellm cost map
    latency_ms: int               # wall-clock duration of the inference call
    cache_read_tokens: int = 0    # from Usage._cache_read_input_tokens (Anthropic) or 0
    cache_creation_tokens: int = 0  # from Usage._cache_creation_input_tokens (Anthropic)
    error: str | None = None      # set only on failed calls (exception type)
```

### Pattern 3: compute_cost() — unified cost calculation for both paths

`litellm.completion_cost(completion_response)` accepts a `ModelResponse` (litellm path).
For the Anthropic SDK path, the response is `anthropic.types.Message`, not `ModelResponse`.
The canonical solution is a unified helper that uses a fake `ModelResponse`:

```python
# Source: verified from litellm 1.83.0 completion_cost() signature
import litellm
from litellm.types.utils import ModelResponse, Usage

def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Compute cost in USD using litellm's cost map.

    Works for both litellm and Anthropic SDK paths — model names
    (claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5, gpt-4o)
    are in litellm.model_cost.

    Returns None when the model is not in litellm's cost map.
    Never returns 0.0 for unknown models — 0.0 is ambiguous with free-tier.
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
```

Verified: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`, `gpt-4o` are all
in `litellm.model_cost`. `gemini/gemini-1.5-pro` raises `Exception` (not in map) — this
is the correct "returns None" path. The exception is a bare `Exception` (not a litellm
subclass) for "not mapped" models; `litellm.BadRequestError` is raised for models with
no provider prefix at all.

### Pattern 4: ProviderCostEmitter — wrapper for cost-instrumented inference

```python
import time
from state_core.events import SqliteEventStore
from state_core.schema import Mode
from ulid import ULID

class ProviderCostEmitter:
    """Wraps LitellmClient and AnthropicClient to emit cost-accounting events.

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
        client,           # LitellmClient | AnthropicClient
        model: str,
        messages: list[dict],
        *,
        scope_type: str,
        scope_id: str,
        **kwargs,
    ):
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
        except Exception:
            # emit error response event, then re-raise
            ...
            raise

        latency_ms = int((time.monotonic() - t0) * 1000)
        usage = response.usage
        cost = compute_cost(model, usage.prompt_tokens, usage.completion_tokens)

        await self._store.append(
            aggregate_type="provider",
            aggregate_id=aggregate_id,
            event_type="state.provider.response",
            data=ProviderResponseData(
                model=model,
                scope_type=scope_type,
                scope_id=scope_id,
                request_id=request_id,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            ).model_dump(),
            mode=self._mode,
        )
        return response
```

### Pattern 5: aggregate_provider_costs() — SQL GROUP BY aggregator

The aggregator uses `read_events()` with `mode=None` (all modes) and filters by event type
in Python. Do NOT do a second SQL query per scope — load response events once and group:

```python
async def aggregate_provider_costs(
    store: SqliteEventStore,
    scope_type: str | None = None,   # None = all scope types
) -> dict[str, dict]:
    """Aggregate cost + token stats from state.provider.response events.

    Returns:
        {
          "step:step-17.3": {
            "scope_type": "step",
            "scope_id": "step-17.3",
            "call_count": 3,
            "total_input_tokens": 4200,
            "total_output_tokens": 1800,
            "total_tokens": 6000,
            "total_cost_usd": 0.0315,   # None if ANY response has cost_usd=None
            "has_unknown_cost": False,   # True if any call has cost_usd=None
          },
          ...
        }
    """
    events = await store.read_events()  # all events
    response_events = [
        e for e in events
        if e["type"] == "state.provider.response"
    ]

    rollup: dict[str, dict] = {}
    for ev in response_events:
        data = ev["data"]
        st = data["scope_type"]
        sid = data["scope_id"]
        if scope_type is not None and st != scope_type:
            continue

        key = f"{st}:{sid}"
        if key not in rollup:
            rollup[key] = {
                "scope_type": st,
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
```

**Note:** `total_cost_usd` is the sum of non-None costs. If `has_unknown_cost` is True,
`total_cost_usd` is a partial sum (undercounting). Callers should check `has_unknown_cost`.

### Anti-Patterns to Avoid

- **Storing cost_usd as 0.0 when model is not mapped:** 0.0 is ambiguous with genuinely free calls. Store `None` (JSON null) and set `has_unknown_cost=True` in aggregator.
- **Modifying LitellmClient or AnthropicClient directly:** These are Phase 024/025 files with stable test surfaces. Wrap them via `ProviderCostEmitter` instead.
- **Calling `await store.append()` inside the inference try-block before the response is received:** The request event must be emitted before the call; the response event after. Any exception between the two means the response event is not emitted — this is intentional (partial accounting is better than wrong accounting).
- **Using `mode="kernel"` for all provider events:** The mode should reflect the calling context. Pass mode through from the caller; default to "kernel" only when context is unknown.
- **In-memory cost accumulation over the full event history:** Use the SQL `read_events()` approach; full history can be thousands of events across many phases.
- **Importing `state_build.*` or `state_teach.*` in cost_accounting.py:** Mode isolation is enforced by CI; `state_core.providers.*` is shared kernel.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token-to-cost conversion | Custom price table | `litellm.completion_cost(mock_response)` | litellm maintains current pricing for 100+ models; project model names are confirmed in map |
| ULID correlation ID | Random uuid | `str(ULID())` (already imported in events.py) | Time-ordered, project-standard correlation key |
| Event persistence | Custom DB writes | `SqliteEventStore.append()` with aggregate_type="provider" | Phase 004 handles seq enforcement, WAL, deterministic serialization |
| JSON cost aggregation | Custom sum loop | Python dict accumulation from `read_events()` response events | Simple and correct; SQL GROUP BY not needed since data field is JSON (can't be indexed) |

**Key insight:** litellm's cost map is the only up-to-date price source for 100+ models. Custom price tables go stale immediately when providers change pricing.

---

## Common Pitfalls

### Pitfall 1: `litellm.completion_cost` raises bare `Exception` for unmapped models

**What goes wrong:** Models with a known provider prefix but unknown model name (e.g., `gemini/gemini-1.5-pro` which is deprecated) raise `Exception: This model isn't mapped yet` — not a litellm subclass. Models with no provider prefix at all raise `litellm.BadRequestError`.

**Why it happens:** litellm's cost function has two separate failure paths: no-provider and not-mapped. The "not mapped" case is not in the litellm exception hierarchy.

**How to avoid:** Wrap `compute_cost()` with a bare `except Exception: return None`. Never let cost calculation errors propagate as inference errors.

**Warning signs:** If `compute_cost()` raises in tests, the `except` clause is missing.

### Pitfall 2: `usage._cache_creation_input_tokens` is a PrivateAttr, not a model field

**What goes wrong:** `ModelResponse.usage._cache_creation_input_tokens` is a Pydantic `PrivateAttr(0)` — accessing `usage.model_dump()` will NOT include it. It is only accessible as an instance attribute: `usage._cache_creation_input_tokens`.

**Why it happens:** litellm uses a private attribute to hide this from Pydantic serialization (it's a litellm-internal implementation detail for prompt caching).

**How to avoid:** Access cache token counts as `usage._cache_creation_input_tokens` and `usage._cache_read_input_tokens` directly. For the Anthropic SDK path, use `anthropic.types.Usage.cache_creation_input_tokens` and `cache_read_input_tokens` (public fields on that model).

**Warning signs:** `ProviderResponseData.cache_creation_tokens` is always 0 even on Anthropic cache-hit responses.

### Pitfall 3: Aggregate type "provider" is not in the AggregateType Literal

**What goes wrong:** `SqliteEventStore.append(aggregate_type="provider", ...)` succeeds at the DB level (TEXT column accepts any string), but `schema.AggregateType` Literal validation will fail if any code validates the aggregate_type field.

**Why it happens:** The AggregateType Literal in `schema.py` only has the original 9 values. Phase 028 must extend it.

**How to avoid:** Add `"provider"` to the `AggregateType = Literal[...]` in `schema.py`. Update any exhaustiveness checks or match statements that enumerate aggregate types.

**Warning signs:** Any test that constructs an `EventEnvelope(aggregate_type="provider", ...)` raises `ValidationError`.

### Pitfall 4: `time.monotonic()` should be used for latency, not `time.time()`

**What goes wrong:** `time.time()` is subject to clock adjustments (NTP, DST, system time changes) and can produce negative durations or large jumps.

**Why it happens:** Common mistake when measuring wall-clock duration.

**How to avoid:** Always use `t0 = time.monotonic()` before the call and `latency_ms = int((time.monotonic() - t0) * 1000)` after.

### Pitfall 5: `ProviderCostEmitter` must re-raise after emitting error response event

**What goes wrong:** If the emitter catches the exception to emit an error event but does not re-raise, callers lose the original error. ProviderTransientError / ProviderAuthError / etc. must propagate to the caller.

**How to avoid:** Always `raise` after emitting the error response event inside the `except Exception:` block.

### Pitfall 6: Using `asyncio.ensure_future` for append() instead of `await`

**What goes wrong:** If cost event appends are fire-and-forget, a process crash between the response and the append loses the cost data. The Anthropic mirror (Phase 004) uses `ensure_future` for SyncEvent mirroring specifically because the mirror endpoint may fail — cost data has higher fidelity requirements.

**How to avoid:** `await store.append()` for cost events. The additional latency is single-digit milliseconds (SQLite single-row insert in WAL mode).

---

## Code Examples

Verified patterns from official sources:

### compute_cost() — unified cost helper

```python
# Source: verified litellm 1.83.0 venv, completion_cost returns float
# Confirmed: claude-opus-4-7=0.00175, claude-sonnet-4-6=0.00105, claude-haiku-4-5=0.00035
#            per 1000+500 tokens
import litellm
from litellm.types.utils import ModelResponse, Usage

def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
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
```

### Emitting state.provider.request before the call

```python
# Source: consistent with Phase 004 SqliteEventStore.append() usage pattern
request_id = str(ULID())
await store.append(
    aggregate_type="provider",
    aggregate_id=f"provider:{scope_type}:{scope_id}",
    event_type="state.provider.request",
    data={
        "model": model,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "request_id": request_id,
    },
    mode=mode,
)
```

### Emitting state.provider.response after the call

```python
# Source: verified Usage fields from litellm 1.83.0 types/utils.py
usage = response.usage
cost = compute_cost(model, usage.prompt_tokens, usage.completion_tokens)
await store.append(
    aggregate_type="provider",
    aggregate_id=f"provider:{scope_type}:{scope_id}",
    event_type="state.provider.response",
    data={
        "model": model,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "request_id": request_id,
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": cost,       # float | None
        "latency_ms": latency_ms,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
    },
    mode=mode,
)
```

### Accessing Anthropic SDK usage for cache tokens

```python
# Source: verified anthropic.types.Usage model fields (installed package)
# Anthropic SDK returns anthropic.types.Message with .usage: anthropic.types.Usage
#   .input_tokens          = prompt_tokens
#   .output_tokens         = completion_tokens
#   .cache_read_input_tokens   = cache read hits (int | None)
#   .cache_creation_input_tokens = cache writes (int | None)
from anthropic.types import Message as AnthropicMessage

def extract_anthropic_usage(response: AnthropicMessage) -> dict:
    u = response.usage
    return {
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "total_tokens": u.input_tokens + u.output_tokens,
        "cache_read_tokens": u.cache_read_input_tokens or 0,
        "cache_creation_tokens": u.cache_creation_input_tokens or 0,
    }
```

### schema.py extension

```python
# Add "provider" to AggregateType in src/state_core/schema.py
AggregateType = Literal[
    "arc",
    "phase",
    "slice",
    "step",
    "concept",
    "drill",
    "decision",
    "auth",
    "mode",
    "provider",    # Phase 028: cost accounting
]

PROVIDER_EVENT_TYPES = Literal[
    "state.provider.request",
    "state.provider.response",
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `litellm.model_cost[model]` dict lookup | `litellm.completion_cost(response)` | litellm 1.x | `completion_cost` handles provider prefixes, region variants, and context-window pricing |
| `response.usage.cost` (populated by litellm callbacks) | `litellm.completion_cost(response)` explicit call | litellm 1.x | `usage.cost` is only populated when litellm callback hooks run — not available in our wrapper pattern |

**Note:** `litellm.Usage.cost` field is Optional[float] defined in litellm's type stubs but it is NOT populated by `litellm.acompletion()` in the wrapper path (only by internal litellm callbacks). Confirmed: `usage.model_dump()` does not include the `cost` key when not explicitly passed.

**Deprecated/outdated:**
- `litellm.Usage.cost` (via model_dump): Not reliable — only set by litellm internal callbacks, not by our wrapper. Use `litellm.completion_cost(response)` explicitly.

---

## Open Questions

1. **Should `ProviderCostEmitter` also wrap `astream()` (streaming calls)?**
   - What we know: Streaming responses in litellm use `CustomStreamWrapper`; token counts are only available after the stream is exhausted (litellm accumulates them internally). The final chunk has `finish_reason != None` but usage is on a synthetic final object.
   - What's unclear: litellm's streaming usage is accumulated in `_hidden_params` — calling `completion_cost()` on a streaming response is not documented as supported.
   - Recommendation: For Phase 028 (PRV-05), instrument non-streaming calls only. Document the streaming gap as a tech debt item in SUMMARY.md.

2. **Phase 028 scope: emitter or full ProviderRouter integration?**
   - What we know: The router's `select()` returns a bare client. Cost instrumentation requires wrapping the client call. Phase 028 adds `ProviderCostEmitter` as a standalone wrapper; Phase 031's parity tests will call `ProviderCostEmitter` per-matrix-cell.
   - What's unclear: Should `ProviderRouter.select()` be updated to return a cost-instrumented client, or should callers explicitly use `ProviderCostEmitter`?
   - Recommendation: Keep `ProviderCostEmitter` explicit (callers wrap the client). Updating `ProviderRouter` is Phase 031 or later work (PRV-05 only requires the cost accounting infrastructure, not automatic routing integration).

3. **`scope_id` source: how does the emitter know the current step/slice/phase/arc ID?**
   - What we know: The daemon tracks the current context (step, slice, etc.) in its session state. Phase 027's `handle_chat_params` hook receives a body from the opencode plugin.
   - What's unclear: For Phase 028, is the scope_id extracted from the hook body, or does `ProviderCostEmitter` require explicit scope injection from the caller?
   - Recommendation: Require explicit `scope_type` and `scope_id` arguments to `acompletion()`. This is testable without any daemon context. Integration with the full context stack is Phase 030+ work.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ with `asyncio_mode = "auto"` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py -x -q` |
| Full suite command | `.venv/bin/python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-05 | `compute_cost()` returns float for known model (claude-sonnet-4-6, 100+50 tokens) | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_compute_cost_known_model -x` | ❌ Wave 0 |
| PRV-05 | `compute_cost()` returns None for unknown/unmapped model | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_compute_cost_unknown_model_returns_none -x` | ❌ Wave 0 |
| PRV-05 | `ProviderCostEmitter.acompletion()` emits `state.provider.request` event before call | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_emitter_emits_request_event -x` | ❌ Wave 0 |
| PRV-05 | `ProviderCostEmitter.acompletion()` emits `state.provider.response` event after call | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_emitter_emits_response_event -x` | ❌ Wave 0 |
| PRV-05 | `state.provider.response` event data contains input_tokens, output_tokens, cost_usd | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_response_event_has_token_and_cost_fields -x` | ❌ Wave 0 |
| PRV-05 | `state.provider.response` event has cost_usd=None when model is not in cost map | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_response_event_cost_none_for_unmapped_model -x` | ❌ Wave 0 |
| PRV-05 | `ProviderCostEmitter.acompletion()` re-raises ProviderTransientError after emitting error event | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_emitter_reraises_on_provider_error -x` | ❌ Wave 0 |
| PRV-05 | Request and response events share the same `request_id` (correlation key) | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_request_response_share_request_id -x` | ❌ Wave 0 |
| PRV-05 | `aggregate_provider_costs()` returns rollup grouped by scope | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_single_scope -x` | ❌ Wave 0 |
| PRV-05 | `aggregate_provider_costs()` sums tokens + cost across multiple calls for same scope | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_multiple_calls_same_scope -x` | ❌ Wave 0 |
| PRV-05 | `aggregate_provider_costs()` separates rollup by scope (step vs arc) | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_multiple_scopes -x` | ❌ Wave 0 |
| PRV-05 | `aggregate_provider_costs(scope_type="step")` returns only step-scope entries | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_scope_type_filter -x` | ❌ Wave 0 |
| PRV-05 | `has_unknown_cost=True` when any call has cost_usd=None | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_aggregate_has_unknown_cost_flag -x` | ❌ Wave 0 |
| PRV-05 | `schema.AggregateType` includes "provider" | unit | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_provider_aggregate_type_in_schema -x` | ❌ Wave 0 |
| PRV-05 | Import graph: cost_accounting.py does NOT import state_build.* or state_teach.* | import-graph | `.venv/bin/python3 -m pytest tests/test_cost_accounting.py::test_no_mode_silo_import -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3 -m pytest tests/test_cost_accounting.py -x -q`
- **Per wave merge:** `.venv/bin/python3 -m pytest tests/ -x -q -m "not e2e and not integration and not provider_parity"`
- **Phase gate:** Full suite green (currently 852 collected) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cost_accounting.py` — all 15 RED stubs listed above
- [ ] `src/state_core/providers/cost_accounting.py` — module (created in Wave 1 GREEN)
- [ ] `src/state_core/schema.py` — add `"provider"` to `AggregateType` Literal + `ProviderRequestData`, `ProviderResponseData`, `PROVIDER_EVENT_TYPES`

*(No framework gaps — pytest infrastructure carries over from Phase 027.)*

---

## Sources

### Primary (HIGH confidence)
- litellm 1.83.0 installed at `.venv/lib/python3.12/site-packages/litellm/` — `completion_cost()` signature and behavior, `model_cost` dict contents, `Usage` PrivateAttr fields (`_cache_creation_input_tokens`, `_cache_read_input_tokens`), exception types for unmapped models
- Direct venv testing: `compute_cost("claude-opus-4-7", 1000, 500)=0.00175`, `compute_cost("claude-sonnet-4-6", 1000, 500)=0.0105`, `compute_cost("claude-haiku-4-5", 1000, 500)=0.0035`, `compute_cost("gemini/gemini-1.5-pro", ...)=None`
- `src/state_core/events.py` — `SqliteEventStore.append()` signature and mode/aggregate_type/aggregate_id conventions (Phase 004)
- `src/state_core/schema.py` — `AggregateType` Literal (currently missing "provider"), event data model pattern with `extra="forbid", frozen=True`
- `src/state_core/providers/litellm_client.py` — `LitellmClient.acompletion()` return type `ModelResponse` with `.usage` field
- `src/state_core/providers/anthropic_client.py` — `AnthropicClient.create()` return type pattern
- `anthropic.types.Usage` — `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` fields (verified from installed anthropic package)
- `pyproject.toml` — confirmed no new dependencies needed

### Secondary (MEDIUM confidence)
- Phase 024 RESEARCH.md — confirms litellm `Usage` field access pattern, `ModelResponse.choices[0].message.content` structure, streaming chunk structure
- Phase 027 RESEARCH.md / 027-02-PLAN.md — confirms `handle_chat_params` scope and what Phase 028 inherits

### Tertiary (LOW confidence)
- Streaming usage accounting (skipped for Phase 028 scope) — not verified; documented as open question

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from installed litellm 1.83.0 venv execution
- Architecture: HIGH — event store patterns from Phase 004 source; cost calculation verified empirically
- Pitfalls: HIGH — discovered from direct venv testing (bare Exception for unmapped, PrivateAttr for cache tokens, usage.cost not auto-populated)
- Aggregator design: HIGH — follows existing `read_events()` API from Phase 004

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (litellm cost map changes on provider pricing updates; re-verify if litellm is bumped past 1.85.0)
