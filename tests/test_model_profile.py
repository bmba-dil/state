"""Tests for state_core.providers.model_profile — ModelProfile enum and resolver (PRV-04).

Wave 0 (RED): All tests fail with pytest.fail() until Wave 1 creates
src/state_core/providers/model_profile.py.

Security coverage: T-027-1 (mode isolation), T-027-2 (inherit never returned).
"""
from __future__ import annotations

import importlib
import inspect
import os

import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from state_core.providers.model_profile import (
    ModelProfile,
    ResolvedProfile,
    GlobalProfileConfig,
    resolve_profile,
    build_chat_params,
    _DEFAULTS,
)

# ---------------------------------------------------------------------------
# Hypothesis strategy constants
# (written at module level so Wave 1 can reuse them without structural changes)
# ---------------------------------------------------------------------------

_ALL_PROFILES = list(ModelProfile)
_PROFILE_OR_NONE = st.one_of(st.none(), st.sampled_from(_ALL_PROFILES))


# ---------------------------------------------------------------------------
# PRV-04: ModelProfile enum
# ---------------------------------------------------------------------------


def test_model_profile_members() -> None:
    """PRV-04: ModelProfile enum has exactly quality, balanced, budget, inherit."""
    pytest.fail("RED: ModelProfile enum not yet implemented")


def test_resolved_profile_frozen() -> None:
    """PRV-04: ResolvedProfile is a frozen Pydantic model with required fields."""
    pytest.fail("RED: ResolvedProfile not yet implemented")


def test_defaults_coverage() -> None:
    """PRV-04: _DEFAULTS covers exactly the three non-inherit profiles."""
    pytest.fail("RED: _DEFAULTS not yet implemented")


# ---------------------------------------------------------------------------
# PRV-04: Hypothesis property tests — resolver invariants
# ---------------------------------------------------------------------------


@given(
    step=_PROFILE_OR_NONE,
    slice_=_PROFILE_OR_NONE,
    phase=_PROFILE_OR_NONE,
    arc=_PROFILE_OR_NONE,
    global_=st.sampled_from(_ALL_PROFILES),
)
def test_resolve_never_returns_inherit(step, slice_, phase, arc, global_) -> None:
    """Hypothesis: resolve_profile() should never return profile=inherit."""
    pytest.fail("RED: resolve_profile() not yet implemented")


@given(
    non_inherit=st.sampled_from(
        [ModelProfile.quality, ModelProfile.balanced, ModelProfile.budget]
    ),
)
def test_step_non_inherit_wins_over_all(non_inherit) -> None:
    """Hypothesis: step-level non-inherit profile beats all outer scopes."""
    pytest.fail("RED: resolve_profile() not yet implemented")


# ---------------------------------------------------------------------------
# PRV-04: Inheritance chain — unit tests
# ---------------------------------------------------------------------------


def test_phase_profile_applies_when_step_inherit() -> None:
    """Phase profile wins when step/slice are inherit."""
    pytest.fail("RED: resolve_profile() phase-level precedence not yet implemented")


def test_arc_profile_applies_when_inner_inherit() -> None:
    """Arc profile wins when step/slice/phase are inherit."""
    pytest.fail("RED: resolve_profile() arc-level precedence not yet implemented")


def test_all_inherit_falls_back_to_balanced() -> None:
    """All None/inherit inputs -> balanced (project safe default)."""
    pytest.fail("RED: resolve_profile() fallback-to-balanced not yet implemented")


def test_global_profile_override() -> None:
    """global_profile override is respected when all scopes inherit."""
    pytest.fail("RED: resolve_profile() global_profile not yet implemented")


def test_overrides_applied() -> None:
    """resolve_profile(overrides={'temperature': 0.9}) applies the field override."""
    pytest.fail("RED: resolve_profile() overrides not yet implemented")


def test_invalid_override_raises() -> None:
    """resolve_profile(overrides={'temperature': 'warm'}) raises Pydantic ValidationError."""
    pytest.fail("RED: resolve_profile() override validation not yet implemented")


# ---------------------------------------------------------------------------
# PRV-04: build_chat_params() — hook output formatter
# ---------------------------------------------------------------------------


def test_build_chat_params_camelcase_keys() -> None:
    """build_chat_params() MUST use camelCase keys (topP, maxOutputTokens) for the TS hook interface."""
    pytest.fail("RED: build_chat_params() not yet implemented")


def test_quality_profile_includes_thinking_budget() -> None:
    """Quality profile output.options['thinking_budget_tokens'] == 4000."""
    pytest.fail("RED: build_chat_params() thinking_budget not yet implemented")


def test_balanced_profile_empty_options() -> None:
    """Balanced profile output['options'] == {}."""
    pytest.fail("RED: build_chat_params() balanced profile not yet implemented")


# ---------------------------------------------------------------------------
# T-027-1: Mode isolation — import-graph test
# ---------------------------------------------------------------------------


def test_no_mode_silo_import() -> None:
    """model_profile.py MUST NOT import state_build.* or state_teach.*."""
    import state_core.providers.model_profile as mp_mod

    source_lines = inspect.getsource(mp_mod)
    assert "state_build" not in source_lines, "mode silo violation: state_build imported"
    assert "state_teach" not in source_lines, "mode silo violation: state_teach imported"


# ---------------------------------------------------------------------------
# PRV-04: GlobalProfileConfig — daemon-level config
# ---------------------------------------------------------------------------


def test_global_profile_config_defaults() -> None:
    """GlobalProfileConfig() default_profile == balanced."""
    pytest.fail("RED: GlobalProfileConfig not yet implemented")


def test_global_profile_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """STATE_DEFAULT_PROFILE=quality env var sets default_profile=quality."""
    monkeypatch.setenv("STATE_DEFAULT_PROFILE", "quality")
    pytest.fail("RED: GlobalProfileConfig env override not yet implemented")
