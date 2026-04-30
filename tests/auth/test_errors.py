"""Unit tests for state_core.auth.errors — promoted exception hierarchy.

Asserts:
  - Three classes live in the new module
  - Hierarchy: AuthError <- AuthLoginError, AuthError <- AuthRefreshError
  - providers/anthropic.py re-exports the names (Phase 022 import contract)
  - StealthRejected stays in providers/anthropic.py (Anthropic-specific)
"""

from __future__ import annotations

import pytest


def test_errors_module_exports() -> None:
    from state_core.auth import errors

    assert hasattr(errors, "AuthError")
    assert hasattr(errors, "AuthLoginError")
    assert hasattr(errors, "AuthRefreshError")
    assert errors.__all__ == ["AuthError", "AuthLoginError", "AuthRefreshError"]


def test_errors_hierarchy() -> None:
    from state_core.auth.errors import AuthError, AuthLoginError, AuthRefreshError

    assert issubclass(AuthLoginError, AuthError)
    assert issubclass(AuthRefreshError, AuthError)
    assert issubclass(AuthError, Exception)


def test_anthropic_reexports_match_errors_module() -> None:
    """Phase 022 / 014 tests import these names from providers.anthropic.
    The re-export must be IDENTITY-equivalent — same class objects, not
    copies."""
    from state_core.auth import errors
    from state_core.auth.providers import anthropic

    assert anthropic.AuthError is errors.AuthError
    assert anthropic.AuthLoginError is errors.AuthLoginError
    assert anthropic.AuthRefreshError is errors.AuthRefreshError


def test_stealth_rejected_stays_anthropic_specific() -> None:
    """StealthRejected is Anthropic-only — must NOT live in errors.py."""
    from state_core.auth import errors
    from state_core.auth.providers.anthropic import StealthRejected

    assert not hasattr(errors, "StealthRejected")
    # And it inherits from the shared AuthError base.
    assert issubclass(StealthRejected, errors.AuthError)


def test_messages_do_not_leak_secrets_by_construction() -> None:
    """Defense: AuthError() with no args is the legal idiom; subclasses
    do not auto-attach payload data. Provider impls are responsible for
    redacting before raising."""
    from state_core.auth.errors import AuthError, AuthLoginError, AuthRefreshError

    e = AuthError()
    assert str(e) == ""
    e = AuthLoginError("safe message")
    assert str(e) == "safe message"
    e = AuthRefreshError("safe message")
    assert str(e) == "safe message"
