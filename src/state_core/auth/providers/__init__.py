"""Provider-specific OAuth + API-key implementations for state_core auth.

Each module in this package implements state_core.auth.base.AuthMethod
structurally for one provider:

  * anthropic.py  — Anthropic OAuth stealth (Phase 014 / AUTH-01)
  * (gemini.py    — Phase 015 / AUTH-02)
  * (antigravity.py — Phase 016 / AUTH-03)
  * (copilot.py   — Phase 017 / AUTH-04)
  * (api_keys.py  — Phase 018 / AUTH-05)

This __init__.py is INTENTIONALLY EMPTY. Provider modules are accessed
via direct imports (e.g., `from state_core.auth.providers.anthropic
import AnthropicAuth`), NOT re-exported from state_core.auth/__init__.py.
The dispatcher in Phase 022 (`state auth login <provider>`) reads this
package's contents directly. See state_core.auth.__init__ docstring lines
8–11 for the binding decision.
"""
