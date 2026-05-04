"""Tests for state_core.providers.cost_accounting — ProviderCostEmitter and aggregator (PRV-05).

Wave 0 (RED): All tests that import from cost_accounting fail until Wave 1 creates
src/state_core/providers/cost_accounting.py.

Security coverage:
- T-028-1: cost_usd=None (not 0.0) for unmapped models
- T-028-2: mode isolation (cost_accounting.py must not import state_build.* or state_teach.*)
- T-028-3: ProviderCostEmitter must re-raise after emitting error event
"""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from state_core.schema import AggregateType, ProviderRequestData, ProviderResponseData

# The following import causes ImportError until Wave 1 creates cost_accounting.py.
# This is the expected RED state for Wave 0.
from state_core.providers.cost_accounting import (
    compute_cost,
    ProviderCostEmitter,
    aggregate_provider_costs,
)


# ---------------------------------------------------------------------------
# PRV-05: compute_cost() — unified cost helper
# ---------------------------------------------------------------------------


def test_compute_cost_known_model() -> None:
    """compute_cost() returns a positive float for a known model in litellm's cost map."""
    pytest.fail("RED: compute_cost not yet implemented")


def test_compute_cost_unknown_model_returns_none() -> None:
    """compute_cost() returns None (not 0.0) for models not in litellm's cost map."""
    pytest.fail("RED: compute_cost unknown-model path not yet implemented")


# ---------------------------------------------------------------------------
# PRV-05: ProviderCostEmitter — event emission
# ---------------------------------------------------------------------------


async def test_emitter_emits_request_event() -> None:
    """ProviderCostEmitter emits state.provider.request event before the inference call."""
    pytest.fail("RED: ProviderCostEmitter not yet implemented")


async def test_emitter_emits_response_event() -> None:
    """ProviderCostEmitter emits state.provider.response event after the inference call."""
    pytest.fail("RED: ProviderCostEmitter not yet implemented")


async def test_response_event_has_token_and_cost_fields() -> None:
    """state.provider.response event data contains input_tokens, output_tokens, cost_usd."""
    pytest.fail("RED: ProviderCostEmitter not yet implemented")


async def test_response_event_cost_none_for_unmapped_model() -> None:
    """state.provider.response has cost_usd=None (not 0.0) when model is unmapped."""
    pytest.fail("RED: cost_usd=None path not yet implemented")


async def test_emitter_reraises_on_provider_error() -> None:
    """ProviderCostEmitter re-raises after emitting error response event — callers see the original error."""
    pytest.fail("RED: re-raise behavior not yet implemented")


async def test_request_response_share_request_id() -> None:
    """Request and response events share the same request_id ULID (correlation key)."""
    pytest.fail("RED: request_id correlation not yet implemented")


# ---------------------------------------------------------------------------
# PRV-05: aggregate_provider_costs() — SQL GROUP BY aggregator
# ---------------------------------------------------------------------------


async def test_aggregate_single_scope() -> None:
    """aggregate_provider_costs() returns a rollup dict keyed by 'scope_type:scope_id'."""
    pytest.fail("RED: aggregate_provider_costs not yet implemented")


async def test_aggregate_multiple_calls_same_scope() -> None:
    """aggregate_provider_costs() sums tokens and cost across multiple calls for the same scope."""
    pytest.fail("RED: aggregator summing not yet implemented")


async def test_aggregate_multiple_scopes() -> None:
    """aggregate_provider_costs() produces separate rollup entries for step vs arc scopes."""
    pytest.fail("RED: multi-scope aggregation not yet implemented")


async def test_aggregate_scope_type_filter() -> None:
    """aggregate_provider_costs(scope_type='step') excludes non-step scope entries."""
    pytest.fail("RED: scope_type filter not yet implemented")


async def test_aggregate_has_unknown_cost_flag() -> None:
    """Aggregator sets has_unknown_cost=True when any response event has cost_usd=None."""
    pytest.fail("RED: has_unknown_cost flag not yet implemented")


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
