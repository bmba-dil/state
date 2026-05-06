"""Tests for state_teach.token_utils — token counting and prompt cap enforcement.

Uses Hypothesis property tests for invariant verification (monotonic,
cap enforcement, preservation under cap).
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from state_teach.token_utils import count_tokens, enforce_token_cap

# ── Strategies ──────────────────────────────────────────────────

text_strategy = st.text(max_size=2000)

# ── Basic functionality ─────────────────────────────────────────


def test_empty_string_zero_tokens() -> None:
    assert count_tokens("") == 0


def test_basic_token_count() -> None:
    result = count_tokens("hello world")
    assert isinstance(result, int)
    assert result > 0


def test_enforce_token_cap_preserves_short() -> None:
    prompt = "short prompt"
    assert enforce_token_cap(prompt, max_tokens=3000) == prompt


def test_enforce_token_cap_truncates_long() -> None:
    result = enforce_token_cap("x" * 100000, max_tokens=10)
    assert count_tokens(result) <= 10


def test_repeated_character_scales_linearly() -> None:
    c1 = count_tokens("x" * 10)
    c2 = count_tokens("x" * 20)
    assert c2 >= c1


# ── Hypothesis property tests ───────────────────────────────────


@given(s1=st.text(), s2=st.text(min_size=1))
@settings(max_examples=200)
def test_count_tokens_monotonic(s1: str, s2: str) -> None:
    """Adding text never decreases the token count."""
    assert count_tokens(s1 + s2) >= count_tokens(s1)


@given(text=st.text(max_size=5000), max_tokens=st.integers(min_value=1, max_value=3000))
@settings(max_examples=200)
def test_enforce_token_cap_never_exceeds(text: str, max_tokens: int) -> None:
    """enforce_token_cap output never exceeds max_tokens."""
    result = enforce_token_cap(text, max_tokens=max_tokens)
    assert count_tokens(result) <= max_tokens


@given(text=st.text(max_size=2000), max_tokens=st.integers(min_value=100, max_value=5000))
@settings(max_examples=200)
def test_enforce_token_cap_preserves_when_under(text: str, max_tokens: int) -> None:
    """Text under the cap is returned unchanged."""
    assume(count_tokens(text) <= max_tokens)
    assert enforce_token_cap(text, max_tokens=max_tokens) == text


@given(text=st.text(max_size=2000))
@settings(max_examples=200)
def test_reasonable_prompt_under_3000_tokens(text: str) -> None:
    """A prompt under 2000 chars (typical drill prompt size) fits easily under 3000 tokens."""
    assert count_tokens(text) < 3000
