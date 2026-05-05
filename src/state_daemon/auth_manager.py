"""Daemon auth lifecycle manager — refresh loop, round-robin, and status endpoint.

Phase 059 (v6) — the daemon owns credential lifecycle:
  - AuthRefreshLoop: periodic background refresh of near-expiry credentials
  - AuthRoundRobin: per-provider round-robin credential selection
  - AuthStatusHandler: GET /auth/status HTTP handler

Workers query auth status over HTTP — they never read auth.json directly.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from time import time as _now

import orjson
import structlog

from state_core.auth import (
    EXPIRY_BUFFER_SECONDS,
    ApiKeyCredential,
    AuthRefreshError,
    AuthVaultPermissionError,
    Credential,
    ensure_initialized,
    get_auth_json_path,
    is_expired_buffered,
    load_vault,
    refresh_credential,
    select_credential,
)
from state_core.auth.base import AuthMethod

log = structlog.get_logger(__name__)

# Default interval between refresh scans (seconds).
DEFAULT_REFRESH_INTERVAL: float = 60.0

# Auth status cache TTL (seconds).
AUTH_STATUS_CACHE_TTL: float = 5.0


# ── Provider dispatch helper ───────────────────────────────────────────────


# Known OAuth provider IDs — mirrors cli_ops._OAUTH_PROVIDER_IDS.
_OAUTH_PROVIDER_IDS: frozenset[str] = frozenset({
    "anthropic",
    "google.gemini",
    "google.antigravity",
    "github.copilot",
})


def _get_auth_method(provider_id: str) -> AuthMethod | None:
    """Resolve an AuthMethod instance for *provider_id*.

    OAuth providers are stateless (no-arg constructors). API-key providers
    are resolved via ``get_api_key_auth``. Returns None for unknown providers.

    Per-call construction (not cached) mirrors cli_ops.py Pattern 2 / P1-9 —
    daemon is single-process, single-loop; caching would be premature.
    """
    if provider_id == "anthropic":
        from state_core.auth.providers.anthropic import AnthropicAuth
        return AnthropicAuth()

    if provider_id == "google.gemini":
        from state_core.auth.providers.google_gemini import GoogleGeminiAuth
        return GoogleGeminiAuth()

    if provider_id == "google.antigravity":
        from state_core.auth.providers.antigravity import AntigravityAuth
        return AntigravityAuth()

    if provider_id == "github.copilot":
        from state_core.auth.providers.github_copilot import GitHubCopilotAuth
        return GitHubCopilotAuth()

    # API-key providers — delegate to the registry-based factory.
    try:
        from state_core.auth.providers.api_key import get_api_key_auth
        return get_api_key_auth(provider_id)
    except Exception:
        return None


# ── AuthRefreshLoop ───────────────────────────────────────────────────────


class AuthRefreshLoop:
    """Background asyncio task that periodically refreshes near-expiry credentials.

    On start:
      1. Loads ``.state/auth.json`` via the vault, verifying chmod 0600.
      2. Spawns a background asyncio task that checks all credentials every
         ``interval`` seconds.
      3. For each near-expiry OAuth credential (within ``EXPIRY_BUFFER_SECONDS``
         of ``expires``), calls ``refresh_credential()`` with filelock (Phase 013).
      4. Logs successful refreshes and failures; retains old credentials on failure.

    Graceful stop: cancels the background task on ``stop()``.
    """

    def __init__(
        self,
        *,
        vault_path: Path | None = None,
        interval: float = DEFAULT_REFRESH_INTERVAL,
    ) -> None:
        self._vault_path: Path = vault_path or get_auth_json_path()
        self._interval = interval
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Load the vault, verify permissions, and begin the refresh loop."""
        # Ensure the vault file exists and mode is 0o600 (Phases 012 / 059).
        ensure_initialized(self._vault_path)
        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        log.info(
            "auth_refresh_loop.started",
            vault_path=str(self._vault_path),
            interval=self._interval,
        )

    async def stop(self) -> None:
        """Cancel the background refresh task and await completion."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("auth_refresh_loop.stopped")

    async def _refresh_loop(self) -> None:
        """Main loop: periodically scan + refresh near-expiry credentials."""
        while self._running:
            try:
                await self._scan_and_refresh()
            except asyncio.CancelledError:
                break
            except Exception:
                # Never let an unhandled exception kill the loop — log and
                # continue on the next tick.
                log.exception("auth_refresh_loop.scan_error")
            await asyncio.sleep(self._interval)

    async def _scan_and_refresh(self) -> None:
        """One pass: load the vault, find near-expiry OAuth creds, refresh each."""
        vault = load_vault(self._vault_path)
        now = _now()

        for provider_id, bucket in vault.providers.items():
            if not isinstance(bucket, list):
                continue
            for idx, cred in enumerate(bucket):
                # API-key credentials never expire — skip them.
                if isinstance(cred, ApiKeyCredential):
                    continue
                if not is_expired_buffered(cred, now, buffer=EXPIRY_BUFFER_SECONDS):
                    continue

                # Resolve the AuthMethod for this provider.  If the provider
                # is not recognized (e.g. a vault migration artifact), log
                # and skip — the credential will be re-evaluated next tick.
                method = _get_auth_method(provider_id)
                if method is None:
                    log.debug(
                        "auth_refresh_loop.unknown_provider_skipped",
                        provider_id=provider_id,
                    )
                    continue

                # Credential is within the 5-minute buffer window — refresh it.
                try:
                    new_cred = await refresh_credential(
                        method,
                        provider_id,
                        idx=idx,
                        vault_path=self._vault_path,
                        now=now,
                        force=False,
                    )
                    new_expiry: float | None = None
                    if hasattr(new_cred, "expires"):
                        new_expiry = new_cred.expires  # type: ignore[attr-defined]
                    log.info(
                        "auth_refresh_loop.refreshed",
                        provider_id=provider_id,
                        idx=idx,
                        new_expiry=new_expiry,
                    )
                except AuthRefreshError as e:
                    log.warning(
                        "auth_refresh_loop.refresh_failed_terminal",
                        provider_id=provider_id,
                        idx=idx,
                        error_type=type(e).__name__,
                    )
                except Exception as e:
                    log.warning(
                        "auth_refresh_loop.refresh_failed",
                        provider_id=provider_id,
                        idx=idx,
                        error_type=type(e).__name__,
                    )
                    # Non-terminal failures (network blip, lock contention) —
                    # keep the old credential and retry on the next tick.


# ── AuthRoundRobin ────────────────────────────────────────────────────────


class AuthRoundRobin:
    """Per-provider round-robin credential selector wrapping Phase 019 logic.

    ``next_credential(provider_id)`` returns the next credential in
    round-robin order, with cool-down skip for rate-limited credentials.

    ``last_used_index`` is persisted in ``vault.last_rotation`` via
    ``select_credential()`` — daemon restart reloads state from auth.json.
    """

    def __init__(self, *, vault_path: Path | None = None) -> None:
        self._vault_path: Path = vault_path or get_auth_json_path()

    async def next_credential(self, provider_id: str) -> Credential:
        """Return the next credential for *provider_id* in round-robin order.

        Raises ``NoCredentialsAvailableError`` if the provider has no
        credentials or all are currently rate-limited (cool-down).
        """
        _idx, cred = await select_credential(
            provider_id,
            vault_path=self._vault_path,
        )
        return cred


# ── Auth Status Handler ───────────────────────────────────────────────────


class AuthStatusHandler:
    """GET /auth/status — exposes per-provider credential health over HTTP.

    Deliberately excludes raw tokens (``access_token``, ``refresh_token``,
    ``api_key``, ``client_secret``) — only metadata is exposed.

    Caches the response for ``AUTH_STATUS_CACHE_TTL`` seconds to avoid
    I/O on every request.
    """

    def __init__(self, *, vault_path: Path | None = None) -> None:
        self._vault_path: Path = vault_path or get_auth_json_path()
        self._cached_at: float = 0.0
        self._cached_body: bytes = b""

    async def handle(self) -> bytes:
        """Return the auth status JSON as HTTP response body bytes.

        Rebuilds the cache if it has expired.
        """
        now = _now()
        if now - self._cached_at < AUTH_STATUS_CACHE_TTL:
            return self._cached_body

        return await self._rebuild_cache(now)

    async def _rebuild_cache(self, now: float) -> bytes:
        """Load the vault and build a fresh status report."""
        vault = load_vault(self._vault_path)
        providers_list: list[dict[str, object]] = []

        for provider_id, bucket in vault.providers.items():
            if not isinstance(bucket, list):
                continue
            provider_entry: dict[str, object] = {
                "provider": provider_id,
                "count": len(bucket),
                "credentials": [],
            }
            creds_info: list[dict[str, object]] = []
            for idx, cred in enumerate(bucket):
                cred_info: dict[str, object] = {
                    "credential_index": idx,
                }
                if isinstance(cred, ApiKeyCredential):
                    cred_info["mode"] = "api_key"
                    cred_info["expires_at"] = None
                else:
                    # OAuth cred — expose expiry metadata, never raw tokens.
                    cred_info["mode"] = "bearer"
                    cred_info["expires_at"] = cred.expires
                    cred_info["expires_with_buffer"] = cred.expires - EXPIRY_BUFFER_SECONDS
                    cred_info["expired_buffered"] = is_expired_buffered(cred, now)
                creds_info.append(cred_info)
            provider_entry["credentials"] = creds_info  # type: ignore[index]
            providers_list.append(provider_entry)

        body = orjson.dumps({"providers": providers_list}, option=orjson.OPT_SORT_KEYS)
        self._cached_at = now
        self._cached_body = body
        return body
