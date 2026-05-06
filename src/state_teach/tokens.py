"""Token counting helper for teach-mode drill prompts — Phase 119.

Uses character-based approximation (1 token ≈ 4 characters), the
OpenAI-standard rule of thumb for English text.  Deterministic with
no external dependencies — no side effects, no randomness.
"""

from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)

# Max tokens for drill prompts — MCP-T-06
TOKEN_CAP: int = 3000


def count_tokens(text: str) -> int:
    """Return the estimated token count for *text*.

    Uses the industry-standard character-based approximation where
    1 token ≈ 4 characters for English text.  The result is always
    a non-negative integer.

    Args:
        text: Prompt text to count tokens for.

    Returns:
        Integer token count (floor of ``len(text) // 4``).

    Edge cases:
        * Empty string → 0
        * Whitespace-only → counted the same as any other characters
        * Very long prompts → straightforward integer division
    """
    return len(text) // 4
