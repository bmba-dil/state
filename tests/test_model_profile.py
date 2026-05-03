"""Tests for state_core.providers.model_profile — ModelProfile enum and resolver (PRV-04).

Wave 1 (GREEN): All tests fully implemented and passing.

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
    assert set(ModelProfile) == {
        ModelProfile.quality,
        ModelProfile.balanced,
        ModelProfile.budget,
        ModelProfile.inherit,
    }


def test_resolved_profile_frozen() -> None:
    """PRV-04: ResolvedProfile is a frozen Pydantic model with required fields."""
    import pydantic_core

    rp = ResolvedProfile(
        profile=ModelProfile.balanced,
        model="claude-sonnet-4-6",
        temperature=0.5,
    )
    assert rp.profile == ModelProfile.balanced
    assert rp.model == "claude-sonnet-4-6"
    assert rp.temperature == 0.5

    # Frozen: assignment raises ValidationError
    with pytest.raises(pydantic_core.ValidationError):
        rp.temperature = 0.9  # type: ignore[misc]

    # extra="forbid": unknown fields raise ValidationError
    with pytest.raises(pydantic_core.ValidationError):
        ResolvedProfile(
            profile=ModelProfile.balanced,
            model="claude-sonnet-4-6",
            temperature=0.5,
            unknown_field="bad",  # type: ignore[call-arg]
        )


def test_defaults_coverage() -> None:
    """PRV-04: _DEFAULTS covers exactly the three non-inherit profiles."""
    assert set(_DEFAULTS.keys()) == {
        ModelProfile.quality,
        ModelProfile.balanced,
        ModelProfile.budget,
    }
    assert ModelProfile.inherit not in _DEFAULTS


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
    resolved = resolve_profile(step, slice_, phase, arc, global_profile=global_)
    assert resolved.profile != ModelProfile.inherit


@given(
    non_inherit=st.sampled_from(
        [ModelProfile.quality, ModelProfile.balanced, ModelProfile.budget]
    ),
)
def test_step_non_inherit_wins_over_all(non_inherit) -> None:
    """Hypothesis: step-level non-inherit profile beats all outer scopes."""
    resolved = resolve_profile(
        step_profile=non_inherit,
        slice_profile=ModelProfile.quality,
        phase_profile=ModelProfile.balanced,
        arc_profile=ModelProfile.budget,
        global_profile=ModelProfile.quality,
    )
    assert resolved.profile == non_inherit


# ---------------------------------------------------------------------------
# PRV-04: Inheritance chain — unit tests
# ---------------------------------------------------------------------------


def test_phase_profile_applies_when_step_inherit() -> None:
    """Phase profile wins when step/slice are inherit."""
    resolved = resolve_profile(
        step_profile=ModelProfile.inherit,
        slice_profile=ModelProfile.inherit,
        phase_profile=ModelProfile.quality,
    )
    assert resolved.profile == ModelProfile.quality
    assert resolved.temperature == _DEFAULTS[ModelProfile.quality].temperature


def test_arc_profile_applies_when_inner_inherit() -> None:
    """Arc profile wins when step/slice/phase are inherit."""
    resolved = resolve_profile(
        step_profile=ModelProfile.inherit,
        slice_profile=ModelProfile.inherit,
        phase_profile=ModelProfile.inherit,
        arc_profile=ModelProfile.quality,
    )
    assert resolved.profile == ModelProfile.quality


def test_all_inherit_falls_back_to_balanced() -> None:
    """All None/inherit inputs -> balanced (project safe default)."""
    resolved = resolve_profile(
        step_profile=ModelProfile.inherit,
        slice_profile=ModelProfile.inherit,
        phase_profile=None,
        arc_profile=None,
        global_profile=ModelProfile.inherit,
    )
    assert resolved.profile == ModelProfile.balanced
    assert resolved == _DEFAULTS[ModelProfile.balanced]


def test_global_profile_override() -> None:
    """global_profile override is respected when all scopes inherit."""
    resolved = resolve_profile(
        step_profile=None,
        slice_profile=None,
        phase_profile=None,
        arc_profile=None,
        global_profile=ModelProfile.budget,
    )
    assert resolved.profile == ModelProfile.budget
    assert resolved == _DEFAULTS[ModelProfile.budget]


def test_overrides_applied() -> None:
    """resolve_profile(overrides={'temperature': 0.9}) applies the field override."""
    resolved = resolve_profile(
        step_profile=ModelProfile.balanced,
        overrides={"temperature": 0.9},
    )
    assert resolved.temperature == 0.9
    assert resolved.profile == ModelProfile.balanced


def test_invalid_override_raises() -> None:
    """resolve_profile(overrides={'temperature': 'warm'}) raises Pydantic ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        resolve_profile(overrides={"temperature": "warm"})


# ---------------------------------------------------------------------------
# PRV-04: build_chat_params() — hook output formatter
# ---------------------------------------------------------------------------


def test_build_chat_params_camelcase_keys() -> None:
    """build_chat_params() MUST use camelCase keys (topP, maxOutputTokens) for the TS hook interface."""
    params = build_chat_params(_DEFAULTS[ModelProfile.balanced])
    assert "topP" in params
    assert "maxOutputTokens" in params
    assert "top_p" not in params
    assert "max_output_tokens" not in params


def test_quality_profile_includes_thinking_budget() -> None:
    """Quality profile output.options['thinking_budget_tokens'] == 4000."""
    params = build_chat_params(_DEFAULTS[ModelProfile.quality])
    assert "thinking_budget_tokens" in params["options"]
    assert params["options"]["thinking_budget_tokens"] == 4000  # type: ignore[index]


def test_balanced_profile_empty_options() -> None:
    """Balanced profile output['options'] == {}."""
    params = build_chat_params(_DEFAULTS[ModelProfile.balanced])
    assert params["options"] == {}


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
    cfg = GlobalProfileConfig()
    assert cfg.default_profile == ModelProfile.balanced


def test_global_profile_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """STATE_DEFAULT_PROFILE=quality env var sets default_profile=quality."""
    monkeypatch.setenv("STATE_DEFAULT_PROFILE", "quality")
    cfg = GlobalProfileConfig()
    assert cfg.default_profile == ModelProfile.quality
