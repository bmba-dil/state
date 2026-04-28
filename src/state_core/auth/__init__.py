"""Auth layer: 5-method credential management.

Public surface re-exported from state_core.auth.base (Phase 011) and
state_core.auth.store (Phase 012). Downstream phases can
`from state_core.auth import OAuthCredential, AuthVault` instead of
reaching into the submodules.

Phase 013 (refresh.py) will add its own re-exports here when it lands.
Provider modules under state_core.auth.providers/ are intentionally
NOT re-exported — they are accessed via the dispatcher in Phase 014.
"""

from __future__ import annotations

from state_core.auth.base import (
    ApiKeyCredential,
    AuthMethod,
    Credential,
    CredentialAdapter,
    OAuthCredential,
)
from state_core.auth.store import (
    AuthVault,
    AuthVaultPermissionError,
    ensure_initialized,
    get_auth_json_path,
    load_vault,
    save_vault,
)

__all__ = [
    # Phase 011 — base
    "ApiKeyCredential",
    "AuthMethod",
    "Credential",
    "CredentialAdapter",
    "OAuthCredential",
    # Phase 012 — store
    "AuthVault",
    "AuthVaultPermissionError",
    "ensure_initialized",
    "get_auth_json_path",
    "load_vault",
    "save_vault",
]
