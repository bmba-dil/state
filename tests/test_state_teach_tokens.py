"""Tests for state-teach token counting helper — Phase 119.

Covers: edge cases (empty, whitespace, long prompt), cap enforcement,
Hypothesis property tests for correctness across arbitrary inputs.
"""

from __future__ import annotations

from hypothesis import given, strategies as st


# ── Edge-case unit tests ───────────────────────────────────────

def test_empty_string_returns_zero() -> None:
    """Empty string yields 0 tokens."""
    from state_teach.tokens import count_tokens

    assert count_tokens("") == 0


def test_whitespace_only_returns_correct_count() -> None:
    """Whitespace-only strings are counted correctly."""
    from state_teach.tokens import count_tokens

    # 4 spaces = 4 chars → 1 token
    assert count_tokens("    ") == 1
    # 8 spaces = 8 chars → 2 tokens
    assert count_tokens("        ") == 2


def test_exact_boundary() -> None:
    """12_000 chars → exactly 3000 tokens."""
    from state_teach.tokens import TOKEN_CAP, count_tokens

    text = "x" * (TOKEN_CAP * 4)
    assert count_tokens(text) == TOKEN_CAP


def test_below_cap_unchanged() -> None:
    """Short text under cap stays unchanged."""
    from state_teach.tokens import count_tokens

    assert count_tokens("hello") == 1  # 5 chars → 1 token
    assert count_tokens("hello world") == 2  # 11 chars → 2 tokens


def test_very_long_prompt() -> None:
    """A 12k+ char prompt yields the expected token count."""
    from state_teach.tokens import count_tokens

    text = "a" * 15000
    assert count_tokens(text) == 3750  # 15000 // 4


# ── Hypothesis property tests ──────────────────────────────────

@given(st.text())
def test_token_count_non_negative(text: str) -> None:
    """Token count is always >= 0 for any text input."""
    from state_teach.tokens import count_tokens

    assert count_tokens(text) >= 0


@given(st.text(max_size=5000), st.text(max_size=5000))
def test_token_count_monotonic(a: str, b: str) -> None:
    """Concatenating strings never reduces token count below either part."""
    from state_teach.tokens import count_tokens

    count_a = count_tokens(a)
    count_b = count_tokens(b)
    count_ab = count_tokens(a + b)

    assert count_ab >= count_a
    assert count_ab >= count_b


@given(st.text(min_size=12000, max_size=20000))
def test_long_text_upper_bound(text: str) -> None:
    """Even long prompts have bounded token counts (never negative overflow)."""
    from state_teach.tokens import count_tokens

    count = count_tokens(text)
    # For 20000 chars max, token count cannot exceed ceil(20000/4)=5000
    assert 0 <= count <= 5000
