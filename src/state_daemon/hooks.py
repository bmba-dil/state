# src/state_daemon/hooks.py
"""Daemon HTTP hook handlers — Phase 027 stub.

Provides framework-agnostic async handler functions for opencode plugin hook endpoints.
Each handler takes a parsed JSON body (dict) and returns a dict for JSON serialization.
The daemon HTTP server (server.py, Phase 027+ stub) wraps these handlers in its framework.

Phase 027: handle_chat_params — /hook/chat-params
  Reads step_profile from the request body; resolves against global defaults.
  Full scope-stack lookup (Arc/Phase/Slice/Step from events.sqlite) is Phase 028 work.

Security: invalid step_profile values are caught and fall back to balanced (no 500 errors).
Mode isolation: this module imports only from state_core.providers.model_profile (shared kernel),
stdlib, and structlog — no build or teach mode modules.
"""
from __future__ import annotations

import structlog
from state_core.providers.model_profile import (
    ModelProfile,
    resolve_profile,
    build_chat_params,
)

log = structlog.get_logger(__name__)


async def handle_chat_params(body: dict[str, object]) -> dict[str, object]:
    """Handle POST /hook/chat-params from the opencode plugin shim.

    Phase 027 stub: reads step_profile from the request body;
    resolves against global defaults (no scope-stack lookup yet).
    Full scope-stack lookup (Arc/Phase/Slice/Step) is Phase 028 work.

    Args:
        body: Parsed JSON request body from the plugin shim.
              Expected keys (all optional):
                step_profile: str — one of "quality", "balanced", "budget", "inherit"

    Returns:
        Dict with camelCase keys matching the opencode chat.params hook output interface:
          temperature: float
          topP: float
          topK: int (always 0)
          maxOutputTokens: int | None
          options: dict (contains thinking_budget_tokens if quality profile)

    Security: invalid step_profile values are caught and treated as None (falls back to balanced).
    Overrides are NOT accepted from the HTTP body (Phase 027 scope).
    """
    step_profile_raw = body.get("step_profile")
    step_profile: ModelProfile | None = None
    if step_profile_raw is not None:
        try:
            step_profile = ModelProfile(step_profile_raw)
        except ValueError:
            log.warning(
                "hooks.chat_params.invalid_profile",
                step_profile_raw=step_profile_raw,
                fallback="balanced",
            )
            step_profile = None

    resolved = resolve_profile(step_profile=step_profile)
    params = build_chat_params(resolved)

    log.debug(
        "hooks.chat_params.resolved",
        profile=resolved.profile.value,
        model=resolved.model,
    )
    return params
