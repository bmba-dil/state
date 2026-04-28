"""Auth layer: 5-method credential management.

Public surface re-exported from state_core.auth.base. Downstream phases
can `from state_core.auth import OAuthCredential` instead of reaching
into the submodule.

Phase 012 (store.py) and Phase 013 (refresh.py) will add their own
re-exports here as they land. Provider modules under
state_core.auth.providers/ are intentionally NOT re-exported — they
are accessed via the dispatcher in Phase 014.
"""

from __future__ import annotations

from state_core.auth.base import (
    ApiKeyCredential,
    AuthMethod,
    Credential,
    CredentialAdapter,
    OAuthCredential,
)

__all__ = [
    "ApiKeyCredential",
    "AuthMethod",
    "Credential",
    "CredentialAdapter",
    "OAuthCredential",
]
