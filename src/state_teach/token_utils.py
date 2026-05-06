"""Token counting and prompt-cap enforcement for teach-mode drill tools.

Provides count_tokens() and enforce_token_cap() using tiktoken's
cl100k_base encoding for accurate token-aware truncation.  Satisfies
MCP-T-06 — every drill prompt must stay at or under 3000 tokens.
"""

from __future__ import annotations

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")

DEFAULT_TOKEN_CAP: int = 3000


def count_tokens(text: str) -> int:
    """Return the token count for *text* using cl100k_base encoding.

    Args:
        text: Prompt text to count tokens for.

    Returns:
        Integer token count.  Returns 0 for empty strings.
    """
    return len(_ENCODING.encode(text))


def enforce_token_cap(prompt: str, max_tokens: int = DEFAULT_TOKEN_CAP) -> str:
    """Truncate *prompt* at token boundaries if it exceeds *max_tokens*.

    Encoding is cl100k_base — truncation is token-aware (cuts at token
    boundaries, not character boundaries).

    Args:
        prompt: Prompt text to check and possibly truncate.
        max_tokens: Maximum allowed tokens.  Defaults to 3000 (MCP-T-06).

    Returns:
        The original prompt if under the cap, otherwise the prompt
        truncated to the first *max_tokens* tokens.  Truncation is
        silent — no logging, no warnings, no exceptions.
    """
    tokens = _ENCODING.encode(prompt)
    if len(tokens) <= max_tokens:
        return prompt
    return _ENCODING.decode(tokens[:max_tokens])
