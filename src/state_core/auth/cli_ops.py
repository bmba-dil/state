"""Reusable auth operations layer for CLI commands and future TUI surfaces.

No Typer/Click/state_cli imports. Async-native. The Typer sub-app in
state_cli.auth calls these functions via asyncio.run(); the future
opencode-plugin TUI modal will call them with direct await.

Import chain (one-way only):
    state_cli.auth  ->  state_core.auth.cli_ops  ->  state_core.auth.*
                                                  ->  state_core.events
"""
from __future__ import annotations

import asyncio
import difflib
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from state_core.auth.base import ApiKeyCredential, Credential, OAuthCredential
from state_core.auth.errors import (
    AuthError,
    NoCredentialsAvailableError,
    UnknownApiKeyProviderError,
)
from state_core.auth.loader import load_credentials
from state_core.auth.refresh import is_expired_buffered, with_vault_lock
from state_core.auth.store import (
    AuthVault,
    get_auth_json_path,
    load_vault,
    save_vault,
)

log = structlog.get_logger("state_cli.auth")

# ── Provider alias table (LOCKED) ────────────────────────────────────────────

_PROVIDER_ALIASES: dict[str, str] = {
    # OAuth aliases
    "claude": "anthropic",
    "gemini": "google.gemini",
    "antigravity": "google.antigravity",
    "copilot": "github.copilot",
    # Minor api-key aliases (planner discretion)
    "gpt": "openai",
    "gpt-4": "openai",
    "openai-key": "openai",
    "google-key": "google.ai_studio",
    "gemini-key": "google.ai_studio",
    "deepseek-key": "deepseek",
    "groq-key": "groq",
    "together-key": "together",
    "mistral-key": "mistral",
    "cohere-key": "cohere",
    "openrouter-key": "openrouter",
    "grok-key": "xai",
    "xai-key": "xai",
    "cerebras-key": "cerebras",
    "anyscale-key": "anyscale",
}

# All known canonical OAuth provider IDs
_OAUTH_PROVIDER_IDS: frozenset[str] = frozenset({
    "anthropic",
    "google.gemini",
    "google.antigravity",
    "github.copilot",
})

# _ALL_PROVIDER_IDS is initialized lazily to avoid circular imports at load time
_ALL_PROVIDER_IDS: frozenset[str] | None = None


def _get_all_provider_ids() -> frozenset[str]:
    global _ALL_PROVIDER_IDS
    if _ALL_PROVIDER_IDS is None:
        from state_core.auth.providers.api_key import _REGISTRY
        _ALL_PROVIDER_IDS = _OAUTH_PROVIDER_IDS | frozenset(_REGISTRY.keys())
    return _ALL_PROVIDER_IDS


def _resolve_provider_id(name: str) -> str:
    """Normalize provider name via alias table; raise if unknown.

    Steps:
    1. Lowercase the input.
    2. Look up in _PROVIDER_ALIASES (returns canonical id or original lowercased).
    3. Check against _get_all_provider_ids().
    4. On miss: compute difflib.get_close_matches; include in error message.

    Raises:
        UnknownApiKeyProviderError: if canonical_id not in known set.
    """
    lowered = name.lower()
    canonical = _PROVIDER_ALIASES.get(lowered, lowered)
    if canonical not in _get_all_provider_ids():
        suggestions = difflib.get_close_matches(
            canonical, list(_get_all_provider_ids()), n=3, cutoff=0.6
        )
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        raise UnknownApiKeyProviderError(f"{name!r} (resolved to {canonical!r}){hint}")
    return canonical


# ── StatusRow and StatusReport dataclasses ───────────────────────────────────


@dataclass
class StatusRow:
    """One row in the status table (one credential)."""
    provider_id: str
    type: str            # 'oauth' | 'api_key'
    account_label: str   # extras['email_address'] > account_id > prefix12...
    expires_at: float | None    # None for api_key
    expires_in_seconds: float | None  # None for api_key or expired
    source: str          # 'vault' | 'opencode-import' | 'env'
    prefix12: str | None  # first-12 chars of token (opt-in via --show-prefix)
    is_expired: bool


@dataclass
class StatusReport:
    """Structured response from status(). Renderer decides human vs JSON format."""
    providers: list[dict[str, Any]]   # [{"id": "anthropic", "creds": [...]}, ...]
    rows: list[StatusRow]             # flat sorted list for table rendering
    summary: str                      # '16 providers configured · 23 credentials · 2 expired'
    total_providers: int
    total_credentials: int
    total_expired: int
    total_unknown: int


# ── Account-label and helper functions ───────────────────────────────────────


def _account_label(cred: OAuthCredential | ApiKeyCredential) -> str:
    """Return human-friendly account label using the binding fallback chain:
    extras['email_address'] > account_id > f'{prefix12}...'
    (CONTEXT.md: 'Account label fallback chain (binding)')
    """
    if isinstance(cred, OAuthCredential):
        email = cred.extras.get("email_address")
        if email:
            return str(email)
        if cred.account_id:
            return cred.account_id
        return f"{cred.access[:12]}..."
    # ApiKeyCredential
    if cred.extras.get("email_address"):
        return str(cred.extras["email_address"])
    return f"{cred.key[:12]}..."


def _prefix12(cred: OAuthCredential | ApiKeyCredential) -> str:
    if isinstance(cred, OAuthCredential):
        return cred.access[:12]
    return cred.key[:12]


def _source_label(cred: OAuthCredential | ApiKeyCredential) -> str:
    """Read extras['_source']; default to 'vault'."""
    return str(cred.extras.get("_source", "vault"))


# ── Event emission helpers ────────────────────────────────────────────────────


async def _emit_auth_event(
    event_type: str,
    cred: OAuthCredential | ApiKeyCredential,
    store: Any | None,
    mirror: Any | None,
) -> None:
    """Emit a single auth domain event. SQLite FIRST, SyncEvent second.

    Payload never contains secret bytes — only provider_id, cred_kind,
    source, account_label (CONTEXT.md § Logout UX — Audit).
    """
    if store is None:
        return
    payload = {
        "provider_id": cred.provider_id,
        "cred_kind": cred.type,
        "source": _source_label(cred),
        "account_label": _account_label(cred),
    }
    result = store.append(
        aggregate_type="auth",
        aggregate_id=f"cli:{cred.provider_id}",
        event_type=f"state.{event_type}",
        data=payload,
        mirror=mirror,
    )
    if asyncio.iscoroutine(result):
        await result
    log.info(event_type, provider_id=cred.provider_id, cred_kind=cred.type)


# ── login() ──────────────────────────────────────────────────────────────────


async def login(
    provider_id: str,
    *,
    account_id: str | None = None,
    api_key: str | None = None,
    code_state: str | None = None,
    from_stdin: bool = False,
    store: Any | None = None,
    mirror: Any | None = None,
) -> OAuthCredential | ApiKeyCredential:
    """Log in to provider; save to vault; emit auth.logged_in event.

    Dispatch table:
        canonical_id == 'anthropic'          -> AnthropicAuth().login()
        canonical_id == 'google.gemini'      -> GoogleGeminiAuth().login()
        canonical_id == 'google.antigravity' -> AntigravityAuth().login()
        canonical_id == 'github.copilot'     -> GitHubCopilotAuth().login()
        all api_key providers                -> direct ApiKeyCredential construction
                                                (when api_key is pre-supplied)
                                                or PlainApiKeyAuth().login() for interactive

    Raises:
        UnknownApiKeyProviderError: provider not in known set.
        AuthError / AuthLoginError: any login failure.
    """
    canonical = _resolve_provider_id(provider_id)

    cred: OAuthCredential | ApiKeyCredential

    if canonical == "anthropic":
        from state_core.auth.providers.anthropic import AnthropicAuth
        result = await AnthropicAuth().login()
        cred = result if isinstance(result, (OAuthCredential, ApiKeyCredential)) else result[0]

    elif canonical == "google.gemini":
        from state_core.auth.providers.google_gemini import GoogleGeminiAuth
        result = await GoogleGeminiAuth().login()
        cred = result if isinstance(result, (OAuthCredential, ApiKeyCredential)) else result[0]

    elif canonical == "google.antigravity":
        from state_core.auth.providers.antigravity import AntigravityAuth
        result = await AntigravityAuth().login()
        cred = result if isinstance(result, (OAuthCredential, ApiKeyCredential)) else result[0]

    elif canonical == "github.copilot":
        from state_core.auth.providers.github_copilot import GitHubCopilotAuth
        result = await GitHubCopilotAuth().login()
        cred = result if isinstance(result, (OAuthCredential, ApiKeyCredential)) else result[0]

    else:
        # api_key provider
        if api_key is not None:
            # Pre-supplied key: construct directly (no interactive prompt).
            # PlainApiKeyAuth.login() has no `key` parameter (reads from stdin/getpass).
            cred = ApiKeyCredential(provider_id=canonical, key=api_key)
        else:
            # Interactive or --from-stdin
            from state_core.auth.providers.api_key import get_api_key_auth
            if from_stdin:
                import sys
                # Inject into stdin by calling login which reads sys.stdin
                api_key_val = sys.stdin.readline().rstrip("\n").rstrip("\r")
                cred = ApiKeyCredential(provider_id=canonical, key=api_key_val)
            else:
                auth_method = get_api_key_auth(canonical)
                result = await auth_method.login()
                cred = result if isinstance(result, (OAuthCredential, ApiKeyCredential)) else result

    # Persist: append to vault array (never replaces — Phase 019 round-robin).
    # T-018-8 mitigation (Phase 022.2): hold the vault filelock across the
    # read-modify-write window so concurrent CLI invocations do not clobber.
    vault_path = get_auth_json_path()
    with with_vault_lock(vault_path):
        vault = load_vault(vault_path) if vault_path.exists() else AuthVault()
        existing = list(vault.providers.get(canonical, []))
        existing.append(cred)
        vault = vault.model_copy(update={"providers": {**vault.providers, canonical: existing}})
        save_vault(vault_path, vault)

    # Dual-write event (SQLite first, SyncEvent second — v1 cardinal rule).
    # OUTSIDE the lock: event mirroring can be slow; vault mutation is atomic
    # within the with-block above.
    await _emit_auth_event("auth.logged_in", cred, store, mirror)

    log.info("auth.login.success", provider_id=canonical, account_label=_account_label(cred))
    return cred


# ── logout() ─────────────────────────────────────────────────────────────────


async def logout(
    provider_id: str,
    *,
    account_id: str | None = None,
    all_: bool = False,
    yes: bool = False,
    store: Any | None = None,
    mirror: Any | None = None,
) -> int:
    """Remove credential(s) for provider; return count of removed creds.

    Match priority for --account:
        1. cred.account_id exact match
        2. extras['email_address'] exact match
        3. first-12-chars prefix match

    Raises:
        ValueError: ambiguous --account match (multiple cands); caller renders candidates.
    Returns:
        int: count of credentials removed (0 = idempotent success when nothing to remove)
    """
    canonical = _resolve_provider_id(provider_id)
    vault_path = get_auth_json_path()

    if not vault_path.exists():
        return 0

    # T-018-8 mitigation (Phase 022.2): hold the vault filelock across the
    # read-modify-write window so concurrent CLI invocations do not clobber.
    to_remove: list[OAuthCredential | ApiKeyCredential] = []
    with with_vault_lock(vault_path):
        vault = load_vault(vault_path)
        creds = list(vault.providers.get(canonical, []))

        if not creds:
            return 0

        if all_:
            to_remove = list(creds)
        elif account_id is not None:
            # Match against account_id, then email, then prefix12
            matches = [
                c for c in creds
                if (
                    (isinstance(c, OAuthCredential) and c.account_id == account_id)
                    or c.extras.get("email_address") == account_id
                    or _prefix12(c).startswith(account_id[:12])
                )
            ]
            if len(matches) == 0:
                return 0
            if len(matches) > 1:
                raise ValueError(
                    f"Ambiguous --account {account_id!r}; "
                    f"matched {len(matches)} credentials: "
                    + ", ".join(_account_label(c) for c in matches)
                )
            to_remove = matches
        else:
            # No --account: remove all (single-cred case) OR the entire array
            # Caller (Typer command) should have prompted for confirmation before reaching here
            to_remove = list(creds)

        # Rewrite vault minus to_remove
        to_remove_set = set(id(c) for c in to_remove)
        remaining = [c for c in creds if id(c) not in to_remove_set]

        updated_providers = dict(vault.providers)
        if remaining:
            updated_providers[canonical] = remaining
        else:
            updated_providers.pop(canonical, None)

        vault = vault.model_copy(update={"providers": updated_providers})
        save_vault(vault_path, vault)

    # Emit auth.logged_out per removed cred (OUTSIDE the lock; same rationale as login).
    for c in to_remove:
        await _emit_auth_event("auth.logged_out", c, store, mirror)

    log.info("auth.logout.success", provider_id=canonical, removed=len(to_remove))
    return len(to_remove)


# ── status() ─────────────────────────────────────────────────────────────────

_SOURCE_ORDER = {"vault": 0, "opencode-import": 1, "env": 2}


async def status(
    *,
    provider_id: str | None = None,
    show_expired: bool = False,
    show_prefix: bool = False,
    env_synthesis: bool = True,
) -> StatusReport:
    """Gather all credentials; return structured report.

    Ordering (CONTEXT.md § status output schema — filtering & sorting):
        providers alphabetical; within provider: vault first, opencode-import second, env third;
        within source: expires_at ascending (soonest-to-expire first).

    NOTE: status() is read-only (does NOT trigger refreshes — CONTEXT.md
    §'Claude's Discretion': 'Status() does NOT trigger refreshes').
    """
    all_providers = _get_all_provider_ids()
    target_providers = sorted(
        [provider_id] if provider_id else list(all_providers)
    )

    rows: list[StatusRow] = []
    providers_json: list[dict[str, Any]] = []
    now = time.time()

    # Load vault once for OAuth providers (not in _REGISTRY)
    vault_path = get_auth_json_path()
    vault = load_vault(vault_path) if vault_path.exists() else AuthVault()

    for pid in target_providers:
        creds: list[OAuthCredential | ApiKeyCredential] = []

        if pid in _OAUTH_PROVIDER_IDS:
            # OAuth providers: load directly from vault
            creds = list(vault.providers.get(pid, []))
        else:
            # API-key providers: use load_credentials (vault + env fallback)
            try:
                creds = load_credentials(pid)  # type: ignore[assignment]
            except UnknownApiKeyProviderError:
                continue
            except Exception:
                creds = []

        if not creds:
            continue

        cred_rows: list[StatusRow] = []
        for c in creds:
            src = _source_label(c)
            expires_at: float | None = None
            expires_in: float | None = None
            expired = False

            if isinstance(c, OAuthCredential):
                expires_at = c.expires
                delta = c.expires - now
                expires_in = delta if delta > 0 else None
                # is_expired uses 5-min buffer (is_expired_buffered from Phase 013)
                expired = is_expired_buffered(c, now=now)

            row = StatusRow(
                provider_id=pid,
                type=c.type,
                account_label=_account_label(c),
                expires_at=expires_at,
                expires_in_seconds=expires_in,
                source=src,
                prefix12=_prefix12(c) if show_prefix else None,
                is_expired=expired,
            )
            cred_rows.append(row)

        # Filter: expired only
        if show_expired:
            cred_rows = [r for r in cred_rows if r.is_expired]

        # Sort: vault first, then opencode-import, then env; by expires_at ascending
        cred_rows.sort(
            key=lambda r: (_SOURCE_ORDER.get(r.source, 99), r.expires_at or float("inf"))
        )

        rows.extend(cred_rows)

        # Build --json provider entry
        creds_json = []
        for r in cred_rows:
            entry: dict[str, Any] = {
                "type": r.type,
                "account_id": None,
                "account_label": r.account_label,
                "expires_at": r.expires_at,
                "expires_in_seconds": r.expires_in_seconds,
                "source": r.source,
            }
            if show_prefix and r.prefix12:
                entry["prefix12"] = r.prefix12
            creds_json.append(entry)

        if cred_rows:
            providers_json.append({"id": pid, "creds": creds_json})

    total_creds = len(rows)
    total_expired = sum(1 for r in rows if r.is_expired)
    total_unknown = sum(1 for r in rows if r.source not in ("vault", "opencode-import", "env"))

    summary = (
        f"{len(providers_json)} provider(s) configured "
        f"· {total_creds} credential(s)"
        + (f" · {total_expired} expired" if total_expired else "")
        + (f" · {total_unknown} unknown-source" if total_unknown else "")
    )

    return StatusReport(
        providers=providers_json,
        rows=rows,
        summary=summary,
        total_providers=len(providers_json),
        total_credentials=total_creds,
        total_expired=total_expired,
        total_unknown=total_unknown,
    )


__all__ = [
    "StatusRow",
    "StatusReport",
    "login",
    "logout",
    "status",
    "_resolve_provider_id",
    "_account_label",
]
