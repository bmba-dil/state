"""auth.json I/O with chmod 0600 enforcement and array-per-provider invariant.

Phase 012 (M-A2 / AUTH-06 / P0-13 owner): the on-disk vault that
round-trips Credential objects to/from `.state/auth.json`.

Cardinal rules:

  1. Every WRITE goes through _atomic_write — never Path.write_bytes,
     never open('w'). The kernel applies mode 0o600 at file creation;
     os.fchmod is belt-and-suspenders; os.fsync precedes os.replace.

  2. Every READ calls _verify_mode FIRST. A wrong-mode file is a
     security incident (P0-13) — we refuse to read and DO NOT chmod
     the file. The CLI (Phase 022) renders a remediation hint.

  3. providers is ALWAYS a list, even for n=1. The field_validator
     on AuthVault coerces bare-dict provider values during migration
     (P1-7 defense). Phase 019 round-robin and Phase 021 import both
     depend on this invariant.

  4. Mode isolation — imports limited to stdlib + pydantic + orjson
     + structlog + state_core.auth.base. NO state_build.* or
     state_teach.* imports. STORE-17 enforces.

  5. Symlink attack (Pitfall 6, T-018-9) is CLOSED by Phase 022.2 —
     `_atomic_write` opens with O_NOFOLLOW and re-raises ELOOP as
     AuthVaultSymlinkError; `_verify_mode` and `ensure_initialized`
     use os.lstat and refuse symlinks at the vault path itself or
     its parent directory. `tests/auth/test_store.py` exercises ≥4
     symlink-attack scenarios.

See .planning/milestones/v2/phases/012-auth-json-vault-chmod-0600/
012-RESEARCH.md for the full rationale, 8 pitfalls, and downstream
consumer contracts.
"""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path
from typing import Any

import orjson
import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator

from state_core.auth.base import Credential

log = structlog.get_logger(__name__)

VAULT_MODE: int = 0o600
"""Required POSIX mode for .state/auth.json. Enforced at create AND read."""

TMP_SUFFIX: str = ".tmp"
"""Atomic-write tmp file suffix. MUST live in the same directory as the
final file so os.replace is a same-fs rename (atomic on POSIX)."""

_WINDOWS_WARNING_EMITTED = False


# ── Exceptions ──────────────────────────────────────────────────────────


class AuthVaultPermissionError(PermissionError):
    """Raised when auth.json is not chmod 0o600.

    The vault refuses to load. Caller (Phase 022 CLI / M-A6 daemon
    boot) renders the remediation:
        chmod 600 .state/auth.json

    Carries the offending path and observed mode for the CLI.
    Does NOT include any file contents in the message — credential
    bytes never leak into exception strings.
    """

    def __init__(self, path: Path, observed_mode: int) -> None:
        self.path = path
        self.observed_mode = observed_mode
        super().__init__(
            f"Refusing to read {path}: mode is {observed_mode:#o}, "
            f"expected {VAULT_MODE:#o}. Run: chmod 600 {path}"
        )


class AuthVaultSymlinkError(OSError):
    """Raised when a symlink is detected on the vault path, tmp path, or parent dir.

    T-018-9 mitigation (Phase 022.2). Attacker-planted symlinks could redirect
    writes to attacker-controlled locations or leak reads via os.stat following
    the link. We refuse to read or write through any symlink in the vault path
    chain.

    Carries the offending path. Does NOT include any link target contents in
    the message — credential bytes never leak into exception strings.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            errno.ELOOP,
            f"Refusing to traverse symlink at {path}: vault path must be "
            f"a regular file. Investigate before deleting; this may indicate "
            f"a local-FS attack.",
        )


# ── AuthVault schema ────────────────────────────────────────────────────


class AuthVault(BaseModel):
    """Authoritative on-disk schema for .state/auth.json.

    Shape contract (P0-13 / P1-7):
      - providers: every value is ALWAYS a list, even for n=1
      - last_rotation: per-provider integer index for round-robin (Phase 019)
      - schema_version: hand-rolled migration anchor (no Alembic)
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    providers: dict[str, list[Credential]] = Field(default_factory=dict)
    last_rotation: dict[str, int] = Field(default_factory=dict)

    @field_validator("providers", mode="before")
    @classmethod
    def _coerce_to_list(cls, v: Any) -> Any:
        """Coerce a bare-dict provider value into a 1-element list.

        Phase 011 callers always pass lists. Phase 021 (opencode
        import) wraps explicitly. This validator catches the rare
        third-party migration path where a bare dict slipped through.
        Emits a structlog warning so the migration is observable.
        """
        if not isinstance(v, dict):
            return v
        out: dict[str, Any] = {}
        for provider_id, value in v.items():
            if isinstance(value, dict):
                log.warning(
                    "auth_vault.bare_dict_coerced",
                    provider_id=provider_id,
                    hint="upgrade caller to pass [credential] instead of credential",
                )
                out[provider_id] = [value]
            else:
                out[provider_id] = value
        return out


# ── Path resolution ─────────────────────────────────────────────────────


def get_auth_json_path() -> Path:
    """Resolve the auth.json path.

    Priority:
      1. STATE_AUTH_JSON env var (test override; matches state_core.database).
      2. <cwd>/.state/auth.json (default; project-relative per ARCHITECTURE.md §11.1).
    """
    env_path = os.environ.get("STATE_AUTH_JSON")
    if env_path:
        return Path(env_path).resolve()
    return Path.cwd() / ".state" / "auth.json"


# ── Mode verification (read path) ───────────────────────────────────────


def _verify_mode(path: Path) -> None:
    """Raise AuthVaultPermissionError unless *path* is mode 0o600.

    POSIX-only mode check. On Windows, st_mode is synthesized — we emit a
    one-time structlog warning and skip the mode comparison (per Pitfall 2
    in RESEARCH; Mac/Linux first per PROJECT.md). Daemon boot (M-A6) is
    the right place to hard-block Windows.

    Also raises AuthVaultSymlinkError if *path* itself is a symlink
    (T-018-9). This check applies cross-platform — symlink rejection is
    valid on every OS Python supports, even where mode bits are not.

    Raises FileNotFoundError if path doesn't exist (caller decides
    whether that means "first run" or "I/O error").
    """
    global _WINDOWS_WARNING_EMITTED
    if os.name != "posix":
        if not _WINDOWS_WARNING_EMITTED:
            log.warning(
                "auth_vault.mode_check_skipped_on_windows",
                path=str(path),
                hint=(
                    "POSIX mode bits not enforceable on Windows; "
                    "daemon-boot will hard-block this platform"
                ),
            )
            _WINDOWS_WARNING_EMITTED = True
        # Use lstat so a symlink does not transparently validate target's mode.
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode):
            raise AuthVaultSymlinkError(path)
        return

    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        raise AuthVaultSymlinkError(path)
    actual = st.st_mode & 0o777
    if actual != VAULT_MODE:
        raise AuthVaultPermissionError(path, actual)


# ── Atomic write (write path) ───────────────────────────────────────────


def _atomic_write(path: Path, payload: bytes) -> None:
    """Write *payload* to *path* atomically with mode 0o600.

    Sequence (mirrors GSD-pi auth-storage.ts):
      1. mkdir parents (idempotent)
      2. os.open(tmp, O_WRONLY|O_CREAT|O_TRUNC, 0o600)
            kernel applies 0o600 at creation (race-free vs subsequent chmod)
      3. os.fchmod(fd, 0o600)
            defense-in-depth: masks any quirky umask / NFS ACL surprise
      4. os.write(fd, payload) in EINTR-safe loop
      5. os.fsync(fd)  — durability before rename
      6. os.close(fd)
      7. os.replace(tmp, path)
            atomic same-fs rename. Inherits 0o600 from the tmp inode.

    The tmp file lives in the SAME DIRECTORY as the final file so
    os.replace is a same-filesystem rename (atomic on POSIX). Never
    use tempfile.NamedTemporaryFile — it defaults to system /tmp.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Defense-in-depth: refuse to write into a symlinked parent directory (T-018-9).
    parent_st = os.lstat(path.parent)
    if stat.S_ISLNK(parent_st.st_mode):
        raise AuthVaultSymlinkError(path.parent)
    tmp = path.with_name(path.name + TMP_SUFFIX)

    try:
        fd = os.open(
            tmp,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
            VAULT_MODE,
        )
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise AuthVaultSymlinkError(tmp) from exc
        raise
    try:
        # Defense-in-depth: kernel already applied mode at creation,
        # but umask on some filesystems / NFS mounts can surprise us.
        os.fchmod(fd, VAULT_MODE)
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)

    # Atomic same-fs rename. Inherits source inode metadata (mode 0o600).
    os.replace(tmp, path)


# ── Public API ──────────────────────────────────────────────────────────


def load_vault(path: Path) -> AuthVault:
    """Load and validate the vault at *path*.

    Empty-vault edge cases:
      - Path doesn't exist → return AuthVault() (does NOT create the file).
      - Path exists, mode 0o600, file is 0 bytes → return AuthVault()
        (Pitfall 3: legacy partial-write artifact).

    Raises:
        AuthVaultPermissionError: file exists but mode != 0o600
        pydantic.ValidationError: file exists but JSON shape is invalid
        orjson.JSONDecodeError: file exists, is non-empty, and is not valid JSON
    """
    try:
        _verify_mode(path)
    except FileNotFoundError:
        return AuthVault()

    with path.open("rb") as f:
        raw = f.read()
    if not raw:
        return AuthVault()
    data = orjson.loads(raw)
    return AuthVault.model_validate(data)


def save_vault(path: Path, vault: AuthVault) -> None:
    """Atomically write *vault* to *path* with mode 0o600.

    Caller is responsible for cross-process locking (Phase 013's
    filelock). On Windows, mode bits are advisory.

    Pre-write invariant assertion (Pitfall 5): every providers value
    MUST be a list. The Pydantic validator should already guarantee
    this; we double-check before the syscall as a P1-7 defense.
    """
    # P1-7 defense: belt-and-suspenders shape check before disk hits.
    assert all(
        isinstance(v, list) for v in vault.providers.values()
    ), "AuthVault.providers values must all be lists (P1-7 invariant)"

    payload = orjson.dumps(
        vault.model_dump(mode="json"),
        option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2,
    )
    _atomic_write(path, payload)


def ensure_initialized(path: Path) -> Path:
    """Create an empty vault at *path* if it doesn't exist; return *path*.

    Idempotent. Used by Phase 014–018 providers' login() to guarantee
    the file exists before they call save_vault().

    If the file already exists, verify its mode is 0o600 (P0-13
    defense at init). A wrong-mode file at init is a security
    incident — we refuse loudly, NO chmod side effect.
    """
    if not path.exists():
        save_vault(path, AuthVault())
    else:
        # Explicit lstat ahead of _verify_mode delegation. T-018-9
        # belt-and-suspenders — _verify_mode also checks, but the explicit
        # double-check makes the audit trail unambiguous and cheap.
        if path.is_symlink():
            raise AuthVaultSymlinkError(path)
        # File exists — verify mode is 0o600. AuthVaultPermissionError
        # propagates up; we do NOT chmod the offending file.
        _verify_mode(path)
    return path


__all__ = [
    "AuthVault",
    "AuthVaultPermissionError",
    "AuthVaultSymlinkError",
    "TMP_SUFFIX",
    "VAULT_MODE",
    "ensure_initialized",
    "get_auth_json_path",
    "load_vault",
    "save_vault",
]
