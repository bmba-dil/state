---
phase: 027-model-profile-resolver
status: issues
reviewed: 2026-05-03
findings: 4
critical: 0
major: 1
minor: 3
---

# Code Review — Phase 027: model-profile-resolver

Files reviewed:
- `src/state_core/providers/model_profile.py`
- `src/state_daemon/hooks.py`
- `tests/test_model_profile.py`
- `tests/test_hooks.py`

---

### [MAJOR] `resolve_profile(overrides={"profile": "inherit"})` silently breaks core invariant
**File:** `src/state_core/providers/model_profile.py:162`
**Issue:** `overrides` can contain `{"profile": "inherit"}`. The `model_validate(base.model_dump() | overrides)` call merges the dict, and Pydantic accepts `ModelProfile.inherit` as a valid `ModelProfile` value — so the returned `ResolvedProfile.profile` is `inherit`, violating the documented guarantee ("profile field is never ModelProfile.inherit"). `test_resolve_never_returns_inherit` does not exercise overrides, so the invariant is untested for this path.
**Suggestion:** Add a post-validation guard in `resolve_profile`:
```python
if overrides:
    result = ResolvedProfile.model_validate(base.model_dump() | overrides)
    if result.profile == ModelProfile.inherit:
        raise ValueError("overrides must not set profile=inherit")
    return result
```
Or strip `profile` from `overrides` before merging (silent correction). Also add a test:
```python
def test_overrides_cannot_set_inherit() -> None:
    import pytest
    with pytest.raises(ValueError):
        resolve_profile(overrides={"profile": "inherit"})
```

---

### [MINOR] `GlobalProfileConfig` model-string fields are dead config
**File:** `src/state_core/providers/model_profile.py:205-211`
**Issue:** `quality_model`, `balanced_model`, and `budget_model` are env-overridable via `STATE_QUALITY_MODEL` etc., but `_DEFAULTS` uses hardcoded model strings and never reads these fields. The config creates a false impression that setting `STATE_QUALITY_MODEL=claude-opus-4-7` changes the model used, when it doesn't. This will silently surprise operators.
**Suggestion:** Either wire the fields to `_DEFAULTS` at startup (requires a factory function or dynamic construction) or remove the fields and add a TODO comment noting they're planned for Phase 028/029. Misleading config is worse than no config.

---

### [MINOR] Unused imports in `tests/test_model_profile.py`
**File:** `tests/test_model_profile.py:9,11,14`
**Issue:** `importlib` (line 9), `os` (line 11), and `settings` from hypothesis (line 14) are imported but never used. These are leftover scaffolding from the RED stub phase.
**Suggestion:** Remove the three unused imports. `importlib` and `os` were likely carried over from the test_router.py pattern but weren't needed; `settings` was imported speculatively for Hypothesis profile tuning that was never applied.

---

### [MINOR] No test for invalid `step_profile` fallback in `handle_chat_params`
**File:** `src/state_daemon/hooks.py:54-62`, `tests/test_hooks.py`
**Issue:** The security-relevant ValueError catch (invalid `step_profile` string → fallback to balanced) has no test. This is the only non-trivial control flow in hooks.py and it's untested.
**Suggestion:** Add to `tests/test_hooks.py`:
```python
async def test_chat_params_invalid_profile_falls_back_to_balanced() -> None:
    """Invalid step_profile string falls back to balanced (no 500)."""
    result = await handle_chat_params({"step_profile": "turbo"})
    assert result["temperature"] == 0.5  # balanced default
    assert result["options"] == {}
```
