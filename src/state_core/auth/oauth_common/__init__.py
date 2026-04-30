"""Shared OAuth primitives for state_core auth providers.

This package holds protocol-agnostic OAuth helpers used by phases 014–017:

  * pkce.py — RFC 7636 verifier + S256 challenge (stdlib only)

Provider-specific code (Anthropic stealth, Gemini, Antigravity, Copilot)
lives in state_core.auth.providers/.

This package's __init__.py is INTENTIONALLY EMPTY. Direct module imports
keep the dependency graph explicit and prevent accidental coupling
(e.g., a Gemini-specific helper sneaking into the public oauth_common
surface). See .planning/milestones/v2/phases/014-anthropic-oauth-provider/
014-CONTEXT.md §decisions → Module layout for the binding decision.
"""
