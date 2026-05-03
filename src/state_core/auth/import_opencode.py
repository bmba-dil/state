"""First-run import from opencode's auth.json into state's vault.

Phase 021 (M-A2 / AUTH-11 / P1-7 owner): the bridge between opencode's
single-source-of-truth `~/.local/share/opencode/auth.json` and state's
own array-per-provider vault.

Cardinal rules enforced here:

  1. Array-shape preservation (P1-7): every imported credential is
     APPENDED to vault.providers[pid] -- never replaces, never collapses.
     The 1/2/5 round-trip property test in tests/auth/test_import_opencode.py
     enforces this via hypothesis.

  2. All-or-nothing transactional: validate every opencode entry first,
     stage a candidate AuthVault in memory, single save_vault() write.
     Any pydantic ValidationError aborts; state's vault stays untouched.

  3. Determinism: no `time.time` / `datetime.now` / `datetime.utcnow`
     calls anywhere. Identity is by (provider_id, access_or_key[:12]) --
     pure value comparison. CARDINAL rule (PROJECT.md).

  4. Mode isolation: imports limited to stdlib + pydantic + orjson +
     structlog + sibling auth modules + state_core.events + state_core.schema
     + state_core.sync_mirror. NO state_build.* / state_teach.* imports.

  5. Secret hygiene: private _OpencodeApiEntry / _OpencodeOauthEntry use
     Field(repr=False) on key/access/refresh. auth.imported event payload
     carries ZERO secret bytes (Phase 020 redactor is layer 2; payload
     contract is layer 1).

  6. Foreign-data tolerance: opencode is read-only from state's perspective.
     If opencode's auth.json is unreadable (corrupt JSON, wrong mode,
     permission denied), WARN and continue. Daemon boots normally.

See .planning/milestones/v2/phases/021-first-run-import-opencode-local/
021-CONTEXT.md for the full rationale, locked decisions, and pitfall map.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Literal

import orjson
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from state_core.auth.base import (
    ApiKeyCredential,
    Credential,
    OAuthCredential,
)
from state_core.auth.providers.api_key import _REGISTRY as _API_KEY_REGISTRY
from state_core.auth.store import (
    AuthVault,
    get_auth_json_path,
    load_vault,
    save_vault,
)
from state_core.schema import AuthImportedData

log = structlog.get_logger(__name__)

# Mirrors opencode auth/index.ts:7 -- sentinel for "logged in via OAuth, no real api key".
_OPENCODE_OAUTH_DUMMY_KEY: str = "opencode-oauth-dummy-key"

# Identity = (provider_id, access_or_key[:_IDENTITY_PREFIX_LEN]).
# A rotated opencode token has a new prefix => imports as a new array element.
_IDENTITY_PREFIX_LEN: int = 12

# Provenance marker per CONTEXT.md decision -- every imported cred carries
# extras["_source"] = "opencode-import". Loader/runtime ignores underscore-
# prefixed extras keys (Phase 018 contract).
_PROVENANCE_KEY: str = "_source"
_PROVENANCE_VALUE: str = "opencode-import"

# Known provider_id allowlist (Phase 018 _REGISTRY U Phases 014-017 OAuth IDs).
# Unknown provider_ids are still imported but emit an INFO log
# (auth.import.untracked_provider_imported) for visibility.
_KNOWN_OAUTH_PROVIDER_IDS: frozenset[str] = frozenset(
    {
        "anthropic",
        "google.gemini_cli",
        "google.antigravity",
        "github.copilot",
    }
)
_KNOWN_PROVIDER_IDS: frozenset[str] = (
    frozenset(_API_KEY_REGISTRY.keys()) | _KNOWN_OAUTH_PROVIDER_IDS
)


# -- Private opencode-shape pydantic models -------------------------------
# (private to this module, hand-rolled per CONTEXT.md decision)


class _OpencodeApiEntry(BaseModel):
    """Mirrors opencode auth/index.ts:22-26 (Api class).

    `extra="ignore"` (NOT forbid) -- opencode may add fields; we only
    care about the ones we use. `repr=False` on key for secret hygiene.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)
    type: Literal["api"]
    key: str = Field(repr=False)
    metadata: dict[str, str] | None = None


class _OpencodeOauthEntry(BaseModel):
    """Mirrors opencode auth/index.ts:13-20 (Oauth class).

    Camel-case fields preserved here (this is opencode's wire shape).
    Translation to snake_case happens in _translate_entry.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)
    type: Literal["oauth"]
    refresh: str = Field(repr=False)
    access: str = Field(repr=False)
    expires: float
    accountId: str | None = None
    enterpriseUrl: str | None = None


class _OpencodeWellKnownEntry(BaseModel):
    """Mirrors opencode auth/index.ts:28-32 (WellKnown class).

    Body intentionally minimal -- we route on `type` alone and skip;
    we never construct a Credential from this shape.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)
    type: Literal["wellknown"]


# -- Path resolution ------------------------------------------------------


def discover_opencode_auth_path() -> Path | None:
    """Resolve the opencode auth.json path per CONTEXT.md.

    Returns the target Path regardless of whether the file exists, so
    callers can decide between "absent" (no candidate location) and
    "present but unreadable" (path resolved, read fails).

    Resolution order (mirrors opencode auth/index.ts:9 + state-side
    override pattern):

      1. STATE_OPENCODE_AUTH_PATH env var (state-side test/CI override).
      2. $XDG_DATA_HOME/opencode/auth.json (if XDG_DATA_HOME set).
      3. Platform default:
           Linux: ~/.local/share/opencode/auth.json
           macOS: ~/Library/Application Support/opencode/auth.json

    Windows is out-of-scope (mirrors Phase 012's POSIX-only stance):
    returns None.

    Note: OPENCODE_AUTH_CONTENT (opencode's in-memory env override at
    auth/index.ts:59) is handled by the caller via the `env_content`
    kwarg on parse_opencode_auth/import_from_opencode -- it never resolves
    to a path.
    """
    # Windows out-of-scope per CONTEXT.md
    if os.name != "posix":
        return None

    # 1. State-side override (highest priority for tests/CI).
    state_override = os.environ.get("STATE_OPENCODE_AUTH_PATH")
    if state_override:
        return Path(state_override).expanduser().resolve()

    # 2. XDG_DATA_HOME (if set).
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return (Path(xdg).expanduser() / "opencode" / "auth.json").resolve()

    # 3. Platform default.
    if sys.platform == "darwin":
        return (
            Path.home() / "Library" / "Application Support" / "opencode" / "auth.json"
        )
    return Path.home() / ".local" / "share" / "opencode" / "auth.json"


# -- Translation primitives -----------------------------------------------


def _translate_entry(
    provider_id: str, entry: dict[str, Any]
) -> Credential | None:
    """Translate one opencode entry into a state Credential, or None to skip.

    Returns:
      OAuthCredential   for opencode type=="oauth"
      ApiKeyCredential  for opencode type=="api" (and key != OAUTH_DUMMY_KEY)
      None              for type=="wellknown" OR OAUTH_DUMMY_KEY (skip)

    Raises:
      ValidationError / ValueError on malformed entry -- caller catches
      and rolls back the entire import (all-or-nothing).
    """
    entry_type = entry.get("type")

    if entry_type == "wellknown":
        # Validate shape (best-effort -- ignore=extras), then skip.
        _OpencodeWellKnownEntry.model_validate(entry)
        log.info(
            "auth.import.wellknown_skipped",
            provider_id=provider_id,
            reason="wellknown_unsupported",
        )
        return None

    if entry_type == "api":
        api = _OpencodeApiEntry.model_validate(entry)
        if api.key == _OPENCODE_OAUTH_DUMMY_KEY:
            log.debug(
                "auth.import.dummy_skipped",
                provider_id=provider_id,
            )
            return None
        # Provenance marker MUST be the LAST write so opencode metadata
        # CANNOT clobber it. An opencode entry whose `metadata` contains
        # a stray `_source` key would otherwise overwrite the marker.
        extras: dict[str, Any] = dict(api.metadata) if api.metadata else {}
        extras[_PROVENANCE_KEY] = _PROVENANCE_VALUE  # always wins (IMPORT-14)
        return ApiKeyCredential(
            key=api.key,
            provider_id=provider_id,
            extras=extras,
        )

    if entry_type == "oauth":
        oauth = _OpencodeOauthEntry.model_validate(entry)
        # Build extras with renames first, then stamp provenance LAST
        # so nothing can overwrite the marker (mirrors api branch above).
        extras = {}
        if oauth.enterpriseUrl is not None:
            # Field RENAME: opencode camelCase -> state snake_case in extras.
            extras["enterprise_url"] = oauth.enterpriseUrl
        extras[_PROVENANCE_KEY] = _PROVENANCE_VALUE  # always wins (IMPORT-14)
        return OAuthCredential(
            access=oauth.access,
            refresh=oauth.refresh,
            expires=oauth.expires,  # epoch seconds verbatim
            account_id=oauth.accountId,  # field RENAME: accountId -> account_id
            provider_id=provider_id,
            extras=extras,
        )

    # Unknown / missing type -> abort the entire import (all-or-nothing).
    raise ValueError(f"unknown opencode entry type: {entry_type!r}")


def _identity(cred: Credential) -> tuple[str, str]:
    """Compute (provider_id, prefix) identity per CONTEXT.md."""
    secret = cred.access if cred.type == "oauth" else cred.key
    return (cred.provider_id, secret[:_IDENTITY_PREFIX_LEN])


# -- Top-level parsing/translation ----------------------------------------


def parse_opencode_auth(
    *,
    env_content: str | None = None,
    raw: bytes | str | None = None,
    existing_vault: AuthVault | None = None,
) -> list[Credential]:
    """Parse opencode auth.json content into a list of state Credentials.

    Inputs (exactly one of env_content / raw is expected):
      env_content -- the opencode auth.json JSON string (in-memory).
      raw         -- raw bytes/string from disk read.

    If `existing_vault` is provided, returns ONLY credentials NOT already
    present (identity by provider_id + access/key[:12]). Otherwise returns
    every translated credential (post-skip rules).

    Skip rules (no entries returned for these):
      * type == "wellknown"  -> skipped with INFO log
      * type == "api" and key == OAUTH_DUMMY_KEY -> skipped with DEBUG log

    Translation rules:
      * type "api"   -> ApiKeyCredential   (discriminator rename)
      * type "oauth" -> OAuthCredential    (camelCase -> snake_case fields)

    Provider validation:
      * unknown provider_ids emit an INFO log (untracked_provider_imported)
        but ARE imported.

    Raises:
      orjson.JSONDecodeError    on malformed JSON
      ValueError                on non-dict root or unknown entry type
      pydantic.ValidationError  on structurally-invalid entries
    """
    # Resolve the bytes source.
    if env_content is not None:
        payload_bytes: bytes = env_content.encode("utf-8")
    elif raw is not None:
        payload_bytes = raw if isinstance(raw, bytes) else raw.encode("utf-8")
    else:
        raise ValueError("parse_opencode_auth requires env_content or raw")

    # Parse JSON (orjson collapses repeated keys at the JSON-object layer,
    # so duplicate provider_ids are structurally impossible by the time we
    # iterate -- IMPORT-21 enforces no in-loop dedup set exists here).
    data = orjson.loads(payload_bytes)
    if not isinstance(data, dict):
        raise ValueError(
            f"opencode auth.json root must be a dict, got {type(data).__name__}"
        )

    # Translate every entry. Validation errors propagate -- caller
    # (import_from_opencode) catches and aborts before any disk write.
    candidates: list[Credential] = []
    for provider_id, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(
                f"opencode auth.json entry for {provider_id!r} must be a dict, "
                f"got {type(entry).__name__}"
            )
        cred = _translate_entry(provider_id, entry)
        if cred is None:
            continue
        candidates.append(cred)

    # Untracked-provider INFO logs (post-translation, pre-dedup).
    for cred in candidates:
        if cred.provider_id not in _KNOWN_PROVIDER_IDS:
            log.info(
                "auth.import.untracked_provider_imported",
                provider_id=cred.provider_id,
            )

    # If existing_vault provided, filter out duplicates (identity match).
    if existing_vault is not None:
        existing_idents: set[tuple[str, str]] = set()
        for pid, creds in existing_vault.providers.items():
            for c in creds:
                existing_idents.add(_identity(c))
        new_creds = [c for c in candidates if _identity(c) not in existing_idents]
        return new_creds

    return candidates


# -- Orchestration --------------------------------------------------------


async def _emit_imported_event(
    store: Any, mirror: Any, cred: Credential
) -> None:
    """Emit a single state.auth.imported event via the store.

    The store's `append` method is async (Phase 005 SqliteEventStore
    contract). Caller awaits this from inside an event loop (daemon
    boot or test asyncio.run wrapper).
    """
    if store is None:
        return
    data = AuthImportedData(
        provider_id=cred.provider_id,
        cred_kind=cred.type,
    )
    result = store.append(
        aggregate_type="auth",
        aggregate_id=f"opencode-import:{cred.provider_id}",
        event_type="state.auth.imported",
        data=data.model_dump(),
        mirror=mirror,
    )
    if asyncio.iscoroutine(result):
        await result
    log.info(
        "auth.import.credential_imported",
        provider_id=cred.provider_id,
        cred_kind=cred.type,
    )


async def import_from_opencode(
    *,
    env_content: str | None = None,
    existing_vault: AuthVault | None = None,
    vault_path: Path | None = None,
    store: Any | None = None,
    mirror: Any | None = None,
) -> list[Credential]:
    """Run the first-run import. Returns the list of newly-imported creds.

    Inputs:
      env_content     -- opencode auth.json content (in-memory, highest priority)
      existing_vault  -- pre-loaded state vault to diff against (test convenience).
                         If None, the importer loads via get_auth_json_path()
                         when a vault write is needed.
      vault_path      -- override path for save_vault() target. Defaults to
                         get_auth_json_path() when None.
      store           -- EventStore (Phase 005). Receives one
                         state.auth.imported event per imported cred. Optional.
      mirror          -- SyncEventMirror (Phase 005). Optional, passed through
                         to store.append().

    Returns:
      list[Credential]  -- the credentials newly written to the vault. Empty
                           list when there is nothing to import.

    Raises:
      Any pydantic.ValidationError / ValueError from translation. The state
      vault is NOT written when validation fails (all-or-nothing).
    """
    # Resolve the opencode source (env-inline > on-disk). `source` tracks the
    # human-readable origin label used in every subsequent log line so that
    # the on-disk path and the env-inline branch share a uniform contract.
    source: str
    if env_content is None:
        path = discover_opencode_auth_path()
        if path is None:
            log.warning(
                "auth.import.windows_unsupported",
                hint="opencode importer is POSIX-only (mirrors Phase 012)",
            )
            return []
        if not path.is_file():
            log.debug(
                "auth.import.absent",
                path=str(path),
                paths_probed=[
                    "STATE_OPENCODE_AUTH_PATH (env)",
                    "$XDG_DATA_HOME/opencode/auth.json",
                    "~/.local/share/opencode/auth.json (Linux)",
                    "~/Library/Application Support/opencode/auth.json (macOS)",
                ],
            )
            return []
        source = str(path)
        try:
            payload_bytes: bytes = path.read_bytes()
        except (PermissionError, OSError) as e:
            log.warning(
                "auth.import.unreadable",
                source=source,
                reason=type(e).__name__,
            )
            return []
        env_content = payload_bytes.decode("utf-8", errors="replace")
        log.info("auth.import.found", source=source)
    else:
        source = "env_inline"
        log.info("auth.import.found", source=source)

    # Translate. orjson.JSONDecodeError + ValidationError both propagate as
    # auth.import.unreadable WARNs when caused by I/O-shaped malformedness;
    # but a structurally-broken entry (missing field) MUST abort and raise.
    try:
        candidates = parse_opencode_auth(
            env_content=env_content, existing_vault=None
        )
    except orjson.JSONDecodeError as e:
        log.warning(
            "auth.import.unreadable",
            source=source,
            reason=type(e).__name__,
        )
        return []
    # ValidationError + ValueError (from missing 'key' / unknown type) bubble
    # up to the caller per IMPORT-22 (transactional all-or-nothing). This is
    # the intended raise path -- vault is untouched because save_vault() has
    # not been reached yet.

    if not candidates:
        log.info("auth.import.completed", count=0)
        return []

    # Resolve target vault (load existing if not provided).
    target_path = vault_path if vault_path is not None else get_auth_json_path()
    if existing_vault is None:
        existing_vault = load_vault(target_path)

    # Diff: build candidate vault with new creds appended at the END.
    candidate_vault = AuthVault(
        schema_version=existing_vault.schema_version,
        providers={
            pid: list(creds) for pid, creds in existing_vault.providers.items()
        },
        last_rotation=dict(existing_vault.last_rotation),
    )

    new_creds: list[Credential] = []
    for cand in candidates:
        existing = candidate_vault.providers.get(cand.provider_id, [])
        existing_idents = {_identity(c) for c in existing}
        if _identity(cand) in existing_idents:
            # Already present -- skip (state-side cred wins, never mutated).
            continue
        candidate_vault.providers.setdefault(cand.provider_id, []).append(cand)
        new_creds.append(cand)

    if not new_creds:
        log.info("auth.import.completed", count=0)
        return []

    # Single transactional write.
    save_vault(target_path, candidate_vault)

    # Emit one auth.imported event per newly-imported cred (dual-write).
    for cred in new_creds:
        await _emit_imported_event(store, mirror, cred)

    log.info("auth.import.completed", count=len(new_creds))
    return new_creds


__all__ = [
    "discover_opencode_auth_path",
    "import_from_opencode",
    "parse_opencode_auth",
    "_OPENCODE_OAUTH_DUMMY_KEY",
]
