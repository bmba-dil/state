"""Auth layer: 5-method credential management.

Public surface re-exported from state_core.auth.base (Phase 011),
state_core.auth.store (Phase 012), state_core.auth.refresh (Phase
013), state_core.auth.errors (Phase 015), state_core.auth.loader
(Phase 018), and state_core.auth.rotation (Phase 019). Downstream
phases can
``from state_core.auth import OAuthCredential, AuthVault, refresh_credential``
instead of reaching into the submodules.

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
from state_core.auth.errors import (
    AuthError,
    AuthLoginError,
    AuthRefreshError,
    NoCredentialsAvailableError,
    UnknownApiKeyProviderError,
)
from state_core.auth.import_opencode import import_from_opencode
from state_core.auth.loader import load_credentials
from state_core.auth.refresh import (
    EXPIRY_BUFFER_SECONDS,
    LOCK_TIMEOUT_SECONDS,
    REFRESH_HTTP_TIMEOUT_SECONDS,
    RefreshLockTimeout,
    is_expired_buffered,
    read_credential,
    refresh_credential,
)
from state_core.auth.rotation import (
    BUCKET_MS,
    clear_rate_limited,
    iter_active_credentials,
    mark_rate_limited,
    select_credential,
)
from state_core.auth.store import (
    AuthVault,
    AuthVaultPermissionError,
    ensure_initialized,
    get_auth_json_path,
    load_vault,
    save_vault,
)

# Phase 022 — cli_ops public surface
from state_core.auth.cli_ops import (  # noqa: F401
    StatusReport,
    StatusRow,
    login as auth_login,
    logout as auth_logout,
    status as auth_status,
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
    # Phase 013 — refresh
    "EXPIRY_BUFFER_SECONDS",
    "LOCK_TIMEOUT_SECONDS",
    "REFRESH_HTTP_TIMEOUT_SECONDS",
    "RefreshLockTimeout",
    "is_expired_buffered",
    "read_credential",
    "refresh_credential",
    # Phase 015 — errors (promoted hierarchy)
    "AuthError",
    "AuthLoginError",
    "AuthRefreshError",
    "UnknownApiKeyProviderError",
    # Phase 018 — loader (orchestration; providers/* deliberately not re-exported)
    "load_credentials",
    # Phase 021 — opencode importer (AUTH-11)
    "import_from_opencode",
    # Phase 019 — rotation
    "BUCKET_MS",
    "NoCredentialsAvailableError",
    "clear_rate_limited",
    "iter_active_credentials",
    "mark_rate_limited",
    "select_credential",
    # Phase 022 — cli_ops public surface (AUTH-12)
    "StatusReport",
    "StatusRow",
    "auth_login",
    "auth_logout",
    "auth_status",
]
