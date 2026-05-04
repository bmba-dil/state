"""Tests for state_core.providers.cost_accounting — ProviderCostEmitter and aggregator (PRV-05).

Wave 1 (GREEN): All 15 tests pass after Wave 1 creates
src/state_core/providers/cost_accounting.py.

Security coverage:
- T-028-1: cost_usd=None (not 0.0) for unmapped models
- T-028-2: mode isolation (cost_accounting.py must not import state_build.* or state_teach.*)
- T-028-3: ProviderCostEmitter must re-raise after emitting error event
"""
from __future__ import annotations

import inspect
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from state_core.schema import AggregateType, ProviderRequestData, ProviderResponseData

# Wave 1: cost_accounting.py now exists — import succeeds.
from state_core.providers.cost_accounting import (
    compute_cost,
    ProviderCostEmitter,
    aggregate_provider_costs,
)
from state_core.events import SqliteEventStore
from src.state_core.migrations import migrate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


@pytest.fixture
async def store() -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(
    model: str = "claude-sonnet-4-6",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    total_tokens: int = 150,
) -> MagicMock:
    """Build a mock ModelResponse-like object with a usage attribute."""
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = total_tokens
    usage.input_tokens = prompt_tokens  # Anthropic SDK alias
    usage.output_tokens = completion_tokens  # Anthropic SDK alias
    # PrivateAttr — simulate litellm default (0, not set)
    usage._cache_read_input_tokens = 0
    usage._cache_creation_input_tokens = 0

    response = MagicMock()
    response.model = model
    response.usage = usage
    return response


# ---------------------------------------------------------------------------
# PRV-05: compute_cost() — unified cost helper
# ---------------------------------------------------------------------------


def test_compute_cost_known_model() -> None:
    """compute_cost() returns a positive float for a known model in litellm's cost map."""
    result = compute_cost("claude-sonnet-4-6", 100, 50)
    assert isinstance(result, float), f"Expected float, got {type(result)}: {result}"
    assert result > 0.0, f"Expected positive float, got {result}"


def test_compute_cost_unknown_model_returns_none() -> None:
    """compute_cost() returns None (not 0.0) for models not in litellm's cost map."""
    result = compute_cost("not/a-real-model", 100, 50)
    assert result is None, f"Expected None for unmapped model, got {result!r}"


# ---------------------------------------------------------------------------
# PRV-05: ProviderCostEmitter — event emission
# ---------------------------------------------------------------------------


async def test_emitter_emits_request_event(store: SqliteEventStore) -> None:
    """ProviderCostEmitter emits state.provider.request event before the inference call."""
    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")
    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    events = await store.read_events()
    request_events = [e for e in events if e["type"] == "state.provider.request"]
    assert len(request_events) == 1, f"Expected 1 request event, got {len(request_events)}"
    assert request_events[0]["data"]["model"] == "claude-sonnet-4-6"


async def test_emitter_emits_response_event(store: SqliteEventStore) -> None:
    """ProviderCostEmitter emits state.provider.response event after the inference call."""
    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")
    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    events = await store.read_events()
    response_events = [e for e in events if e["type"] == "state.provider.response"]
    assert len(response_events) == 1, f"Expected 1 response event, got {len(response_events)}"


async def test_response_event_has_token_and_cost_fields(store: SqliteEventStore) -> None:
    """state.provider.response event data contains input_tokens, output_tokens, cost_usd."""
    mock_response = _make_mock_response(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")
    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    events = await store.read_events()
    response_events = [e for e in events if e["type"] == "state.provider.response"]
    assert len(response_events) == 1
    data = response_events[0]["data"]
    assert "input_tokens" in data, "response event data missing 'input_tokens'"
    assert "output_tokens" in data, "response event data missing 'output_tokens'"
    assert "cost_usd" in data, "response event data missing 'cost_usd'"
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 50


async def test_response_event_cost_none_for_unmapped_model(store: SqliteEventStore) -> None:
    """state.provider.response has cost_usd=None (not 0.0) when model is unmapped."""
    mock_response = _make_mock_response(model="not/a-real-model")
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")
    await emitter.acompletion(
        client=mock_client,
        model="not/a-real-model",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    events = await store.read_events()
    response_events = [e for e in events if e["type"] == "state.provider.response"]
    assert len(response_events) == 1
    cost = response_events[0]["data"]["cost_usd"]
    assert cost is None, f"Expected None for unmapped model cost, got {cost!r}"


async def test_emitter_reraises_on_provider_error(store: SqliteEventStore) -> None:
    """ProviderCostEmitter re-raises after emitting error response event — callers see the original error."""
    class ProviderTransientError(Exception):
        pass

    mock_client = AsyncMock()
    mock_client.acompletion.side_effect = ProviderTransientError("connection timeout")

    emitter = ProviderCostEmitter(store=store, mode="kernel")

    with pytest.raises(ProviderTransientError, match="connection timeout"):
        await emitter.acompletion(
            client=mock_client,
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": "hi"}],
            scope_type="step",
            scope_id="step-1",
        )

    # Confirm error response event was emitted before re-raise
    events = await store.read_events()
    response_events = [e for e in events if e["type"] == "state.provider.response"]
    assert len(response_events) == 1
    assert response_events[0]["data"]["error"] == "ProviderTransientError"


async def test_request_response_share_request_id(store: SqliteEventStore) -> None:
    """Request and response events share the same request_id ULID (correlation key)."""
    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")
    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    events = await store.read_events()
    request_events = [e for e in events if e["type"] == "state.provider.request"]
    response_events = [e for e in events if e["type"] == "state.provider.response"]

    assert len(request_events) == 1
    assert len(response_events) == 1

    req_id_from_request = request_events[0]["data"]["request_id"]
    req_id_from_response = response_events[0]["data"]["request_id"]
    assert req_id_from_request == req_id_from_response, (
        f"request_id mismatch: request={req_id_from_request!r}, response={req_id_from_response!r}"
    )


# ---------------------------------------------------------------------------
# PRV-05: aggregate_provider_costs() — SQL GROUP BY aggregator
# ---------------------------------------------------------------------------


async def test_aggregate_single_scope(store: SqliteEventStore) -> None:
    """aggregate_provider_costs() returns a rollup dict keyed by 'scope_type:scope_id'."""
    mock_response = _make_mock_response(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")
    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    rollup = await aggregate_provider_costs(store)
    assert "step:step-1" in rollup, f"Expected 'step:step-1' key in rollup, got: {list(rollup.keys())}"
    entry = rollup["step:step-1"]
    assert entry["scope_type"] == "step"
    assert entry["scope_id"] == "step-1"
    assert entry["call_count"] == 1


async def test_aggregate_multiple_calls_same_scope(store: SqliteEventStore) -> None:
    """aggregate_provider_costs() sums tokens and cost across multiple calls for the same scope."""
    mock_response = _make_mock_response(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")
    for _ in range(2):
        await emitter.acompletion(
            client=mock_client,
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": "hi"}],
            scope_type="step",
            scope_id="step-1",
        )

    rollup = await aggregate_provider_costs(store)
    entry = rollup["step:step-1"]
    assert entry["call_count"] == 2
    assert entry["total_input_tokens"] == 200, f"Expected 200, got {entry['total_input_tokens']}"
    assert entry["total_output_tokens"] == 100, f"Expected 100, got {entry['total_output_tokens']}"


async def test_aggregate_multiple_scopes(store: SqliteEventStore) -> None:
    """aggregate_provider_costs() produces separate rollup entries for step vs arc scopes."""
    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")

    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="arc",
        scope_id="arc-01",
    )

    rollup = await aggregate_provider_costs(store)
    assert "step:step-1" in rollup, f"Missing 'step:step-1'; keys: {list(rollup.keys())}"
    assert "arc:arc-01" in rollup, f"Missing 'arc:arc-01'; keys: {list(rollup.keys())}"
    assert rollup["step:step-1"]["scope_type"] == "step"
    assert rollup["arc:arc-01"]["scope_type"] == "arc"


async def test_aggregate_scope_type_filter(store: SqliteEventStore) -> None:
    """aggregate_provider_costs(scope_type='step') excludes non-step scope entries."""
    mock_response = _make_mock_response()
    mock_client = AsyncMock()
    mock_client.acompletion.return_value = mock_response

    emitter = ProviderCostEmitter(store=store, mode="kernel")

    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    await emitter.acompletion(
        client=mock_client,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="arc",
        scope_id="arc-01",
    )

    rollup = await aggregate_provider_costs(store, scope_type="step")
    assert "step:step-1" in rollup
    assert "arc:arc-01" not in rollup, (
        f"arc:arc-01 should be excluded by scope_type='step' filter, "
        f"but found in rollup: {list(rollup.keys())}"
    )


async def test_aggregate_has_unknown_cost_flag(store: SqliteEventStore) -> None:
    """Aggregator sets has_unknown_cost=True when any response event has cost_usd=None."""
    # First call: known model (cost will be a float)
    mock_response_known = _make_mock_response(model="claude-sonnet-4-6")
    mock_client_known = AsyncMock()
    mock_client_known.acompletion.return_value = mock_response_known

    # Second call: unmapped model (cost will be None)
    mock_response_unknown = _make_mock_response(model="not/a-real-model")
    mock_client_unknown = AsyncMock()
    mock_client_unknown.acompletion.return_value = mock_response_unknown

    emitter = ProviderCostEmitter(store=store, mode="kernel")

    await emitter.acompletion(
        client=mock_client_known,
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    await emitter.acompletion(
        client=mock_client_unknown,
        model="not/a-real-model",
        messages=[{"role": "user", "content": "hi"}],
        scope_type="step",
        scope_id="step-1",
    )

    rollup = await aggregate_provider_costs(store)
    entry = rollup["step:step-1"]
    assert entry["has_unknown_cost"] is True, (
        f"Expected has_unknown_cost=True when one call has cost_usd=None, got {entry['has_unknown_cost']}"
    )


# ---------------------------------------------------------------------------
# Schema / isolation tests (real assertions — go GREEN immediately or after Wave 1)
# ---------------------------------------------------------------------------


def test_provider_aggregate_type_in_schema() -> None:
    """schema.AggregateType Literal must include 'provider' (added in Plan 01 Task 1)."""
    assert "provider" in AggregateType.__args__, (
        "AggregateType missing 'provider' — add it to the Literal in schema.py"
    )


def test_no_mode_silo_import() -> None:
    """cost_accounting.py MUST NOT import state_build.* or state_teach.* (mode isolation)."""
    import state_core.providers.cost_accounting as ca_mod
    source_lines = inspect.getsource(ca_mod)
    assert "state_build" not in source_lines, "mode silo violation: state_build imported"
    assert "state_teach" not in source_lines, "mode silo violation: state_teach imported"
