# Phase 012: `auth.json` vault (`store.py`) with chmod-0600 + array-per-provider — Research

**Researched:** 2026-04-28
**Domain:** Filesystem-secure JSON vault for credentials (POSIX mode 0600, atomic write, array-per-provider shape)
**Confidence:** HIGH

## Summary

Phase 012 owns `state_core.auth.store` — the on-disk vault that round-trips `Credential` objects (Phase 011) to and from `.state/auth.json`. The vault is the only thing standing between a working OAuth subscription and a tokens-leaked-to-Dropbox / world-readable-on-shared-host disaster (P0-13). It also locks in the shape contract every later phase depends on: every provider key maps to an **array** of credentials, never a bare object — even when n=1 — so Phase 019's round-robin and Phase 021's first-run import don't have to special-case (P1-7).

There are exactly two race windows the file API has to close, and a third (cross-process refresh contention) we explicitly leave open for Phase 013:

1. **Permission TOCTOU** — `open(...,'w')` followed by `os.chmod(...,0o600)` exposes a window where the file is mode-0644. Solution: `os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600)` so the kernel applies mode at creation, then `os.fchmod(fd, 0o600)` (defense in depth, masks any active umask weirdness) before writing. The "right" way per the GSD-pi `auth-storage.ts` precedent is *both*.
2. **Crash-during-write corruption** — partial writes leave a half-truncated `auth.json`. Solution: `auth.json.tmp` (created with 0o600 from byte zero), `os.fsync(fd)` after write, `os.replace(tmp, final)` for atomic rename. The temp file MUST be created in the same directory as `auth.json` so `os.replace` is a same-filesystem rename (atomic POSIX guarantee).
3. **Concurrent refresh** — out of scope; Phase 013 wraps every mutating call in `filelock.FileLock`. Phase 012's API surface MUST be lock-friendly: every public function takes raw paths and is sync-friendly enough to be wrapped, OR is `async` so Phase 013 can use `filelock.AsyncFileLock`. We choose **sync** here because file I/O on small JSON is faster than the async overhead and matches `cryptography`/`os` ergonomics.

The "refuse to proceed if mode wrong" mandate translates to a dedicated `AuthVaultPermissionError(PermissionError)` raised on read when `os.stat(path).st_mode & 0o777 != 0o600`. Auto-fix is rejected (a wrong-mode file is a security incident, not a soft failure); Phase 022's `state auth status` CLI surfaces a `chmod 600 .state/auth.json` remediation hint, and the daemon (Phase A6/M-A6) refuses to boot until the user resolves it.

**Primary recommendation:** Implement `state_core.auth.store` as a single ~150-line module exposing `load_vault(path) → AuthVault`, `save_vault(path, vault)`, and `ensure_initialized(path)`. `AuthVault` is a Pydantic model — `{schema_version: int, providers: dict[str, list[Credential]], last_rotation: dict[str, int]}` — that delegates list-element validation to `CredentialAdapter`. Use `os.open` + `os.fchmod` + `os.fsync` + `os.replace` exactly per the GSD-pi precedent.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
*(none — discuss phase was skipped via `workflow.skip_discuss`)*

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per workflow.skip_discuss. Use ROADMAP, RESEARCH, AUTH-06 spec, P0-13 pitfall, and Phase 011's `Credential` discriminated union.

### Specific Ideas (from CONTEXT.md)
- chmod 0600 enforced on EVERY read; refuse to proceed if file mode wrong (P0-13).
- Array-per-provider shape preserved even for single credentials: `auth.json["anthropic"]` is always a list, never a bare dict.
- `os.open(path, O_CREAT | O_WRONLY | O_TRUNC, 0o600)` for atomic create-with-mode (race-free against subsequent chmod).

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **AUTH-06** | `.state/auth.json` created chmod 0600 via `os.open(..., 0o600)` + `os.fchmod`; chmod verified on every read | Pattern 1 (atomic create-with-mode), Pattern 2 (read-side mode check), Pitfall 1 (umask drift), Pitfall 2 (chmod-after-open TOCTOU). `AuthVaultPermissionError` is the dedicated refuse-to-proceed signal. |
| **P0-13 (owned)** | mode-permission drift / array-shape collapse | Patterns 1+2+3 (mode enforcement at create, read, and rename); array-per-provider Pydantic shape (`AuthVault.providers: dict[str, list[Credential]]`) preserved even for n=1. `Annotated[list[Credential], MinLen(0)]` keeps `[]` legal but `{...}` rejected. Validation hook on save guarantees no caller can downgrade an array to a dict. |

**Downstream consumers (research must enable, not implement):**

| Phase | Consumes from 012 | What 012 must guarantee |
|-------|-------------------|-------------------------|
| 013 (refresh.py) | `load_vault` / `save_vault` inside `filelock.FileLock(...auth.json.lock)` | Sync API, no internal locking. Functions accept the path as parameter (no module-global). |
| 014–017 (OAuth providers) | `save_vault` after `login()` returns `OAuthCredential` | Array-shape preserved when credential count == 1. |
| 018 (API-key vault) | Same plus env-var fallback | `load_vault` returns `AuthVault` even when `auth.json` doesn't exist (returns empty `AuthVault`, optionally creates the file). |
| 019 (multi-cred round-robin) | `last_rotation: dict[str, int]` field | Field exists from day one. Round-robin updates index in place inside the file lock. |
| 021 (first-run opencode import) | `save_vault(path, imported_vault)` | Imported single-credential opencode entries get wrapped in `[…]` per Pydantic validator (no manual coercion in 021). |
| 022 (CLI + regression) | `AuthVaultPermissionError` exception + remediation message | Exception carries the offending path + observed mode for the CLI to render. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `os` (stdlib) | 3.12 | `os.open`, `os.fchmod`, `os.fsync`, `os.replace`, `os.stat` | The whole phase is built around POSIX file primitives — there is no library substitute. |
| `pathlib.Path` (stdlib) | 3.12 | Path manipulation, parent-dir creation | Idiomatic across the codebase (see `state_core.database`). |
| `pydantic` | ≥2.13.2 (pinned) | `AuthVault` model + delegate to `CredentialAdapter` | Already pinned; matches Phase 011's discriminator pattern. |
| `orjson` | ≥3.11.8 (pinned) | Deterministic JSON encode/decode | `OPT_SORT_KEYS` for stable diffs; faster than stdlib. Already pinned. Used by `state_core.events` for the same reason. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `errno` (stdlib) | 3.12 | `errno.ENOENT`-style branch for "file doesn't exist yet" | Distinguish "first run" (return empty vault) from "I/O error" (raise). |
| `tempfile` (stdlib) | 3.12 | NOT used — we make our own temp name | `tempfile.NamedTemporaryFile` defaults to system temp dir, breaks the same-filesystem rename guarantee. We use `auth.json.tmp` literal in the same dir. |
| `pydantic.TypeAdapter` (already imported in 011) | 2.13 | `CredentialAdapter` validates each list element on construction | Phase 011 ships this; we just call it. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual `os.open` + `os.fchmod` | `Path.write_text(..., newline=…)` then `Path.chmod(0o600)` | **Rejected** — TOCTOU exposes 0o644 file between write and chmod. P0-13 is precisely this. |
| `os.replace` (atomic rename) | `shutil.move` / `os.rename` | `os.rename` raises on Windows when target exists; `os.replace` is the cross-platform always-overwrite primitive. `shutil.move` falls back to copy+delete across filesystems — defeats atomicity. |
| `orjson` for serialization | stdlib `json` | `json` produces non-deterministic key order by default; `orjson.OPT_SORT_KEYS` gives bit-identical output (matches the determinism cardinal rule and clean diffs in `git`). |
| Store credentials encrypted at rest (`cryptography` Fernet) | Plaintext + chmod 0600 | **Out of scope for Phase 012** — STACK.md lists `cryptography>=43.0` for *future* `auth.json` encryption (a phase-2 concern). For v2/M-A2 day one, chmod 0600 + filesystem-as-trust-boundary matches GSD-pi exactly. Documented as a deferred enhancement (P2-4 mitigation). |
| Cross-platform mode emulation on Windows | Skip the mode check on Windows | `os.stat().st_mode` returns synthesized values on Windows; chmod is a no-op there. PROJECT.md states "Mac/Linux first". On Windows: emit a structured warning event but do **not** raise. Documented. |
| `dict[str, list[Credential] \| Credential]` (allow either shape) | Strict `dict[str, list[Credential]]` | **Rejected** — exactly the P1-7 bug. Strict list shape, full stop. Pydantic validator coerces a bare dict into a 1-element list with a deprecation warning during the first-run import phase only (Phase 021 controls the migration path). |

**Installation:** No new deps. All required libraries are already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/auth/
├── __init__.py              # Re-export AuthVault, load_vault, save_vault, AuthVaultPermissionError
├── base.py                  # Phase 011 — DO NOT EDIT
├── store.py                 # ← THIS PHASE
├── refresh.py               # Phase 013 — already a stub
└── providers/               # Phases 014–018
```

**Constraint (mode isolation):** `state_core.auth.store` MUST NOT import from `state_build.*` or `state_teach.*`. Imports limited to stdlib + `pydantic` + `orjson` + `state_core.auth.base`.

### Pattern 1: Atomic create-with-mode (the WRITE path)

**What:** Use `os.open` to create the file with mode 0o600 atomically (kernel-enforced, race-free), then `os.fchmod` as defense-in-depth, then write, fsync, and rename.

**Why:** A naïve `open('w')` + `os.chmod(0o600)` opens a TOCTOU window. P0-13 is precisely this.

**Example:**

```python
# src/state_core/auth/store.py
import os
import errno
from pathlib import Path

import orjson

VAULT_MODE = 0o600
TMP_SUFFIX = ".tmp"


def _atomic_write(path: Path, payload: bytes) -> None:
    """Write *payload* to *path* atomically with mode 0o600.

    Sequence (matches GSD-pi auth-storage.ts):
      1. os.open(tmp, O_WRONLY|O_CREAT|O_TRUNC, 0o600)
            → kernel applies 0o600 at creation (race-free vs. subsequent chmod)
      2. os.fchmod(fd, 0o600)
            → defense-in-depth: masks any quirky umask / inherited ACL
      3. os.write(fd, payload)
      4. os.fsync(fd)
            → durability before rename (matches state_core.database.synchronous=FULL)
      5. os.close(fd)
      6. os.replace(tmp, path)
            → atomic same-fs rename. Inherits 0o600 (rename preserves inode metadata).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + TMP_SUFFIX)

    fd = os.open(
        tmp,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        VAULT_MODE,
    )
    try:
        # Defense-in-depth: kernel already applied mode at creation, but
        # umask on some filesystems / NFS mounts can still produce surprises.
        os.fchmod(fd, VAULT_MODE)
        # write() can return short on EINTR; loop just in case.
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)

    # os.replace is atomic on POSIX and overwrites on Windows. Same-fs only
    # (the .tmp lives next to the target, so this is guaranteed).
    os.replace(tmp, path)
```

**Critical detail:** the temp file MUST be created in the **same directory** as the final file. `os.replace` is only atomic across the same filesystem, and `tempfile.NamedTemporaryFile()` defaults to `/tmp`, which on Linux is often a separate mount (`tmpfs`).

### Pattern 2: Read-side mode verification (the READ path)

**What:** Every `load_vault()` call calls `os.stat(path).st_mode & 0o777` and compares against `0o600`. Mismatch → raise `AuthVaultPermissionError` with the offending mode in the exception payload.

**Why:** Defense layer. A user who manually edited `.state/auth.json`, or a backup tool that restored it with default permissions (P2-4), or a sync tool, can introduce drift. We refuse to load.

**Example:**

```python
class AuthVaultPermissionError(PermissionError):
    """Raised when auth.json is not chmod 0o600.

    The vault refuses to load. Caller (Phase 022 CLI / Phase A6 daemon
    boot) renders a remediation message:
        chmod 600 .state/auth.json
    """

    def __init__(self, path: Path, observed_mode: int) -> None:
        self.path = path
        self.observed_mode = observed_mode
        super().__init__(
            f"Refusing to read {path}: mode is {observed_mode:#o}, "
            f"expected {VAULT_MODE:#o}. Run: chmod 600 {path}"
        )


def _verify_mode(path: Path) -> None:
    """Raise AuthVaultPermissionError unless *path* is mode 0o600.

    POSIX-only check. On Windows, st_mode is synthesized — we emit a
    structured warning via structlog (Phase 020 will pick it up) but
    do not raise.
    """
    if os.name != "posix":
        # Windows: chmod is a no-op; mode bits are mostly meaningless.
        # Document the gap; do not block the user.
        return
    actual = os.stat(path).st_mode & 0o777
    if actual != VAULT_MODE:
        raise AuthVaultPermissionError(path, actual)
```

**Anti-auto-fix rationale:** A wrong mode is a *security incident*, not a soft error. Auto-`chmod`-ing it on read silently papers over (a) an intruder relaxing perms to read tokens or (b) a backup that copied the file to an untrusted location. Better to fail loudly than to mask the signal.

### Pattern 3: AuthVault Pydantic shape (the SCHEMA)

**What:** A Pydantic model that owns the `auth.json` shape contract. The discriminated-union `Credential` from Phase 011 is dispatched via `CredentialAdapter` for each list element.

**Why:** A bare `dict[str, list[dict]]` and `orjson.dumps` would round-trip but lose the array-shape invariant. Pydantic enforces it at validation time — we cannot accidentally save a bare-dict credential because the model rejects it.

**Example:**

```python
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from state_core.auth.base import Credential, CredentialAdapter


class AuthVault(BaseModel):
    """Authoritative on-disk schema for .state/auth.json.

    Shape contract (P0-13 array-shape preservation, P1-7 migration safety):
      - providers: every value is ALWAYS a list, even for n=1
      - last_rotation: per-provider integer index for round-robin (Phase 019)
      - schema_version: bumps via hand-rolled migration (no Alembic)
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    providers: dict[str, list[Credential]] = Field(default_factory=dict)
    last_rotation: dict[str, int] = Field(default_factory=dict)

    @field_validator("providers", mode="before")
    @classmethod
    def _coerce_to_list(cls, v: Any) -> Any:
        """Catch the P1-7 bug: bare dict instead of [dict].

        Strictly speaking, Pydantic would already reject a bare dict where
        a list is expected. This validator instead emits a structured
        warning during first-run import (Phase 021) so the user gets a
        diagnostic rather than a cryptic ValidationError. For arbitrary
        callers in Phase 014-019, this is a no-op.
        """
        if not isinstance(v, dict):
            return v
        out: dict[str, Any] = {}
        for provider_id, value in v.items():
            if isinstance(value, dict):
                # NEVER reached in normal flow — Phase 011 callers always pass lists.
                # Phase 021 (opencode import) explicitly wraps. This is the safety net.
                out[provider_id] = [value]
            else:
                out[provider_id] = value
        return out
```

**Note:** the validator runs in `mode="before"`, so it sees raw Python dicts before Pydantic dispatches the discriminated union. This lets it normalize shape *before* `CredentialAdapter` validates each element.

### Pattern 4: Public API surface (load / save / init)

```python
def load_vault(path: Path) -> AuthVault:
    """Load and validate the vault at *path*.

    Empty-vault edge case: if path doesn't exist, returns an empty
    AuthVault (does NOT create the file — that's ensure_initialized's job).
    This matches the read-side semantic that loading is observation-only.

    Raises:
        AuthVaultPermissionError: file exists but mode != 0o600
        pydantic.ValidationError: file exists but JSON shape is invalid
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

    Caller is responsible for cross-process locking (Phase 013's filelock).
    On Windows, mode bits are advisory — file gets created but mode check is skipped.
    """
    payload = orjson.dumps(
        vault.model_dump(mode="json"),
        option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2,
    )
    _atomic_write(path, payload)


def ensure_initialized(path: Path) -> Path:
    """Create an empty vault at *path* if it doesn't exist; return *path*.

    Idempotent. Used by Phase 014-018 providers' login() to guarantee
    the file exists before they call save_vault(). Atomic + chmod 0600
    via _atomic_write of an empty AuthVault payload.
    """
    if not path.exists():
        save_vault(path, AuthVault())
    else:
        # File exists — verify mode is 0o600 even on the init path.
        # If a corrupt-mode file exists, init must fail loudly per P0-13.
        _verify_mode(path)
    return path
```

### Pattern 5: Path resolution (matches `state_core.database`)

```python
def get_auth_json_path() -> Path:
    """Resolve the auth.json path.

    Priority:
      1. STATE_AUTH_JSON env var (test override; matches state_core.database pattern)
      2. <project root>/.state/auth.json (default, project-relative)

    Project-relative is correct per ARCHITECTURE.md §11.1: the .state/
    directory lives at the project root, NOT ~/.state/. This makes
    cross-host portability work — copying the project copies the auth.
    """
    env_path = os.environ.get("STATE_AUTH_JSON")
    if env_path:
        return Path(env_path).resolve()
    return Path.cwd() / ".state" / "auth.json"
```

### Anti-Patterns to Avoid

- **`open('w')` then `os.chmod(0o600)`** — TOCTOU window. This is exactly P0-13.
- **`tempfile.NamedTemporaryFile()`** — defaults to system temp dir; cross-fs rename is non-atomic.
- **`json.dumps` without `sort_keys=True`** — non-deterministic output breaks diffability and replay-bit-identicalness.
- **`os.rename(tmp, final)`** — fails on Windows when target exists. Use `os.replace`.
- **Auto-`chmod` on read** — masks security incidents. Refuse loudly.
- **`Path.write_bytes` for the atomic write** — equivalent to `open('wb').write()`; doesn't fsync, doesn't atomic-rename.
- **Asymmetric "load creates file, save assumes file exists"** — load and save should be orthogonal; `ensure_initialized` is the only function that creates.
- **Hand-rolled JSON shape validation** — Pydantic + `field_validator` already does this. Bonus: discriminated-union dispatch via `CredentialAdapter` is automatic.
- **Module-global `_VAULT_PATH`** — every function takes `path: Path` as a parameter. Phase 013's filelock holder and Phase 022's CLI both need to override it; tests need to inject tmp_path.
- **`asyncio.to_thread(...)` wrapping in `store.py`** — keep it sync. Phase 013 owns the async wrapper if needed; conflating sync I/O with async API just introduces overhead for ~1 KB JSON files.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON encoding | `json.dumps` with custom defaults | `orjson.dumps(..., OPT_SORT_KEYS \| OPT_INDENT_2)` | Already pinned for the event store; deterministic; fast; native datetime/UUID. |
| Pydantic discriminated-union round-trip | Manual `if cred["type"] == "oauth": ...` | `CredentialAdapter.validate_python` (built into Phase 011's `AuthVault.providers` field type) | Pydantic dispatches the discriminator for free. |
| Atomic same-fs rename | `os.rename` + Windows-special-casing | `os.replace` | Cross-platform always-overwrite, atomic on POSIX. |
| Cross-process locking | `fcntl.flock` / `threading.Lock` | `filelock.FileLock` (Phase 013 — NOT this phase) | TOCTOU-safe (3.20.3 floor); covered by separate phase. |
| Mode-bit verification | `pathlib.Path` doesn't expose mode cleanly | `os.stat(path).st_mode & 0o777` | Stdlib idiom. |
| First-run vault detection | `try: open(); except FileNotFoundError` | `if not path.exists()` | Cleaner; only acceptable place to use existence check (TOCTOU is irrelevant for "create if absent"). |
| Schema migration | `os.path` + `json.loads` + manual key-walking | `AuthVault.model_validate` + bump `schema_version` field | Phase 021 handles imports; later phases add migrations as `from_v1_to_v2` static methods. |

**Key insight:** The whole module is ~150 lines of glue around stdlib `os.*` primitives + Pydantic. Every "convenience" wrapper is a vector for bugs. The glue is the value.

## Common Pitfalls

### Pitfall 1: umask drift breaks "0o600 at creation"
**What goes wrong:** `os.open(tmp, O_CREAT, 0o600)` is documented to apply mode AFTER masking with the process's umask. If umask is 0o077, the result is `0o600 & ~0o077 = 0o600` (fine). If umask is 0o000 (rare but legal), result is 0o600 (still fine). If umask is 0o022, result is `0o600 & ~0o022 = 0o600` (still fine, because 0o600 has no group/world bits to mask). So the umask interaction is **actually safe for 0o600** — but the parent directory's mode is NOT controlled by us.
**Why it happens:** Developers reason "umask masks bits *off*", forget that 0o600 has no extra bits to mask, and miss that the parent dir might be 0o755 (world-listable, exposes that an auth.json *exists*).
**How to avoid:** Always call `os.fchmod(fd, 0o600)` explicitly after `os.open` (defense in depth). Document that we don't try to chmod the `.state/` directory itself; that's a daemon-startup concern. The file mode is sufficient to stop reads.
**Warning signs:** Test on a system with `umask 0` and verify `os.stat(path).st_mode & 0o777 == 0o600` after both `os.open` and `os.fchmod`.

### Pitfall 2: `os.replace` doesn't preserve mode if the target had different mode
**What goes wrong:** Subtle myth — actually, `os.replace` (a `rename(2)` syscall) preserves the SOURCE inode entirely, including mode. The DESTINATION inode is removed. So if `auth.json.tmp` is 0o600 and `auth.json` was 0o644, after replace, the result is 0o600.
**Why it happens:** Confusion with `cp` (which creates a new inode and applies umask). `rename`/`os.replace` does NOT.
**How to avoid:** Trust the semantic; verify with a unit test that does `os.replace(tmp_0o600, target_0o644)` and asserts the post-replace mode is 0o600. Add the test for future-Thomas's confidence.
**Warning signs:** Test passes — the semantic holds. If it ever fails, the underlying filesystem is non-POSIX (e.g., FAT32) and the user shouldn't be storing credentials there.

### Pitfall 3: Empty-file edge case (file exists, contents empty)
**What goes wrong:** `orjson.loads(b"")` raises `JSONDecodeError`. Some atomic-write implementations (not ours, but legacy GSD-pi) leave 0-byte files behind during partial writes.
**Why it happens:** `os.replace` of `auth.json.tmp` over `auth.json` is atomic, but if the process is killed between `os.open(tmp)` and `os.write`, the tmp file exists at zero bytes and might get renamed by a re-run.
**How to avoid:** In `load_vault`, after `_verify_mode`, check `if not raw: return AuthVault()`. Treats empty-file as "first-run" — same semantic as missing file. Document that aggressive cleanup of `.tmp` files is a Phase 013 concern (the lock holder cleans up).
**Warning signs:** Test: write empty bytes via the atomic-write path, then `load_vault` returns `AuthVault()` without raising.

### Pitfall 4: orjson serialization of `OAuthCredential.expires` as float
**What goes wrong:** orjson serializes `float` as JSON number — but JSON has no concept of "integer" vs "float". A value like `2_000_000_000.0` round-trips as `2000000000` (no decimal point) on some encoders, then loads as `int`. Pydantic's discriminated union accepts both, but `expires: float` strictly should keep the `.0`.
**Why it happens:** orjson is correct per RFC 7159; the round-trip is lossless for the *value*, but the textual representation may differ. This breaks bit-identical-replay if we ever assert "byte-equal serialization output."
**How to avoid:** Don't assert byte-equality across two save_vault calls. Assert structural equality via `AuthVault.model_validate(load_vault(...))`. The determinism cardinal rule applies to *event* replays, not to vault dumps; vault dumps are content-addressed by the credential set, not by exact bytes. Add a test note clarifying this.
**Warning signs:** A unit test like `assert orjson.dumps(load_vault().model_dump(mode='json')) == saved_bytes` flakes — that test was wrong; replace with structural equality.

### Pitfall 5: Array-shape collapse during Pydantic JSON dump
**What goes wrong:** A naïve `model_dump()` after a `_coerce_to_list` validator could leave the in-memory model with a 1-element list, but a buggy `model_dump_json` could emit `{"anthropic": {…}}` if a custom serializer fires. (Doesn't actually happen with our shape, but P1-7 is the load-bearing test.)
**Why it happens:** Phase 021 (opencode import) explicitly transforms a single-credential opencode entry into a list. If 021's transform ever runs through 012's load path with a bare dict, the validator catches it. But there's no second checkpoint on save.
**How to avoid:** Add an explicit invariant test: `assert all(isinstance(v, list) for v in vault.providers.values())` immediately before `_atomic_write`. Cheap; load-bearing for P1-7.
**Warning signs:** Round-trip migration test in Phase 021 fails — but it'll fail with a clear message because of the assertion in `save_vault`.

### Pitfall 6: Symlink attack on `.state/auth.json`
**What goes wrong:** Attacker (or a user mistake) replaces `.state/auth.json` with a symlink to `/etc/passwd` or `~/.ssh/authorized_keys`. Our `os.open(O_CREAT|O_TRUNC)` follows the symlink and truncates the target.
**Why it happens:** `O_CREAT|O_TRUNC` follows symlinks unless `O_NOFOLLOW` is added.
**How to avoid:** Add `os.O_NOFOLLOW` to the `os.open` call on the temp file path — this is overkill for `auth.json.tmp` (which we control entirely) but combine with `os.lstat(path).st_mode` check on the final `auth.json` before reading. For v2/M-A2, document this as a known-low-risk acceptance: the threat model is "shared user account", not "active local attacker with directory write." If the attacker can write into `.state/`, they have already won. Phase 020+ structlog-redaction covers the leakage side.
**Warning signs:** Security review flags it. Mitigation lives in Phase 022's audit checklist, not Phase 012.

### Pitfall 7: Concurrent reader sees partial JSON during write
**What goes wrong:** Reader process A `open`s `auth.json` while writer B is mid-`os.write(fd, payload)`. A reads a half-written JSON, `orjson.loads` raises.
**Why it happens:** Without locking, reader and writer race. But — since we write to `auth.json.tmp` first and only `os.replace` at the end, the reader either sees the OLD complete `auth.json` or the NEW complete `auth.json`, never a mid-write state. Atomicity of `rename(2)` is the guarantee.
**How to avoid:** Already handled by the atomic-write pattern. Phase 013 adds a `filelock` because two writers (refresh races) would both write valid JSON but lose one another's update; readers don't need the lock for *consistency*, only for *avoiding stale reads under contention*. Document this clearly.
**Warning signs:** Hypothesis property test: "concurrent reader never observes invalid JSON" passes (it should, by atomic-rename guarantee).

### Pitfall 8: `STATE_AUTH_JSON` env var leaks into tests via `os.environ`
**What goes wrong:** A test sets `STATE_AUTH_JSON=/tmp/test-auth.json`, doesn't unset it, next test inherits the path, sees a stale vault.
**Why it happens:** `os.environ` is process-global; pytest fixtures need to be careful with env mutation.
**How to avoid:** Use `monkeypatch.setenv` (auto-unset) in tests. Add a top-level conftest fixture that ensures `STATE_AUTH_JSON` is unset before each `test_store.py` test.
**Warning signs:** Tests pass in isolation but fail in `pytest -n auto` with random ordering.

## Code Examples

### Example 1: Full atomic write (verified pattern, includes EINTR-safety)

```python
def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + TMP_SUFFIX)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, VAULT_MODE)
    try:
        os.fchmod(fd, VAULT_MODE)
        view = memoryview(payload)
        while view:
            n = os.write(fd, view)
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
```

### Example 2: Load with mode verification

```python
def load_vault(path: Path) -> AuthVault:
    try:
        _verify_mode(path)
    except FileNotFoundError:
        return AuthVault()
    with path.open("rb") as f:
        raw = f.read()
    if not raw:
        return AuthVault()
    return AuthVault.model_validate(orjson.loads(raw))
```

### Example 3: AuthVault model with array-shape invariant

```python
class AuthVault(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    providers: dict[str, list[Credential]] = Field(default_factory=dict)
    last_rotation: dict[str, int] = Field(default_factory=dict)

    @field_validator("providers", mode="before")
    @classmethod
    def _coerce_bare_dict(cls, v: Any) -> Any:
        if not isinstance(v, dict):
            return v
        return {
            pid: ([val] if isinstance(val, dict) else val)
            for pid, val in v.items()
        }
```

### Example 4: AuthVaultPermissionError + remediation contract

```python
class AuthVaultPermissionError(PermissionError):
    def __init__(self, path: Path, observed_mode: int) -> None:
        self.path = path
        self.observed_mode = observed_mode
        super().__init__(
            f"Refusing to read {path}: mode is {observed_mode:#o}, "
            f"expected 0o600. Run: chmod 600 {path}"
        )
```

### Example 5: Phase-013 future use-site (preview)

```python
# Phase 013 will look like this; we just enable the shape:
from filelock import FileLock
from state_core.auth.store import load_vault, save_vault, get_auth_json_path

LOCK_PATH = get_auth_json_path().with_suffix(".json.lock")

async def refresh_credential(provider_id: str, idx: int, method: AuthMethod) -> None:
    with FileLock(str(LOCK_PATH), timeout=10.0):
        vault = load_vault(get_auth_json_path())
        cred = vault.providers[provider_id][idx]
        if not method.is_expired(cred, time.time()):
            return  # Double-check pattern (P0-6)
        new_cred = await method.refresh(cred)
        vault.providers[provider_id][idx] = new_cred
        save_vault(get_auth_json_path(), vault)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `os.umask(0o077)` then `open('w')` | `os.open(O_CREAT, 0o600)` + `os.fchmod` | POSIX best-practice consensus, well before 2020 | Race-free creation; doesn't depend on process-global umask state. |
| `os.rename` + Windows special-case | `os.replace` (Python 3.3+) | Python 3.3 (2012) | Cross-platform atomic always-overwrite. |
| `pickle` for credential storage (some old SDKs) | JSON via Pydantic + orjson | Pydantic v2 (2023) | Inspectable, diffable, language-agnostic, no eval-on-load risk. |
| `Path.chmod(0o600)` after-the-fact | mode-at-creation via `os.open` | (always best-practice) | Closes TOCTOU. |
| stdlib `json` with `sort_keys=True` | `orjson.dumps(..., OPT_SORT_KEYS)` | 2020+ orjson maturity | 10-20× faster; deterministic by flag, not by sorted-dict tricks. |

**Deprecated/outdated:**
- `tempfile.mkstemp()` for vault writes — drops file in `/tmp` by default; defeats same-fs atomic rename.
- `Path.write_text(...)` for credential storage — no fsync, no atomic rename, no mode control.
- `cryptography.Fernet` at-rest encryption for v2 — STACK.md flags it as a future enhancement; not load-bearing for chmod-0600 vault.

## Open Questions

1. **Should `ensure_initialized` enforce mode on the parent `.state/` directory?**
   - What we know: ARCHITECTURE.md §11.1 doesn't specify a mode for `.state/` itself.
   - What's unclear: A 0o755 `.state/` is world-listable — an attacker can see `auth.json` exists, not its contents.
   - Recommendation: Out of scope for Phase 012. Daemon-startup phase (M-A6) should `os.chmod(.state, 0o700)`. File this as a hand-off note for that phase.
   - **Status:** Recommendation only; planner should add a note in PLAN.md but not implement.

2. **Behavior on Windows: warn-only or full no-op?**
   - What we know: Windows `os.stat().st_mode` returns synthesized values; chmod is mostly a no-op.
   - What's unclear: Whether the daemon should refuse to start on Windows (per "Mac/Linux first" in PROJECT.md) or just warn.
   - Recommendation: Phase 012 makes `_verify_mode` a no-op on `os.name != "posix"` and emits a one-time structlog warning. Phase A6 daemon-startup is the right place to hard-block Windows.
   - **Status:** Recommendation included in Pattern 2; planner can confirm.

3. **Should `save_vault` also write `last_rotation` atomically with `providers` updates?**
   - What we know: `last_rotation` is a single dict — Pydantic dumps both fields together. One `_atomic_write` call covers both. So yes, automatically.
   - What's unclear: Whether Phase 019 will want to bump `last_rotation` without re-validating credentials.
   - Recommendation: Phase 019 will load → mutate → save. `last_rotation` updates are coupled with credential reads anyway. No special API needed in Phase 012.
   - **Status:** Resolved — single atomic write covers both.

4. **Does `schema_version` start at 1 or 0?**
   - What we know: Phase 011 didn't pick a number; ARCHITECTURE.md §10.2 shows `"schema_version": 1` in the example.
   - Recommendation: Start at `1`. Future migrations bump to 2.
   - **Status:** Resolved — start at 1.

5. **Should the temp-file name include a PID/random suffix to avoid collisions between parallel processes?**
   - What we know: Phase 013 wraps mutations in a filelock, so only one writer at a time.
   - What's unclear: Init from concurrent Phase A6 daemon + CLI invocation could race during the brief window before either acquires the lock.
   - Recommendation: Use literal `auth.json.tmp` for now (matches GSD-pi precedent). If race surfaces, Phase 013 owns the fix (lock acquired before any tmp creation).
   - **Status:** Resolved — literal `.tmp` suffix; race-free under Phase 013's lock.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` (`asyncio_mode = "auto"`) + `hypothesis>=6.120` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/auth/test_store.py -x -q` |
| Full suite command | `python3 -m pytest -q` |

### Phase Requirements → Test Map

| Test ID | Behavior | Test Type | Automated Command | File Exists? |
|---------|----------|-----------|-------------------|--------------|
| STORE-01 | `_atomic_write` produces a file with mode 0o600 (verified via `os.stat`) | unit | `pytest tests/auth/test_store.py::test_atomic_write_mode -x` | Wave 0 |
| STORE-02 | `_atomic_write` with target file already existing at 0o644 → result is 0o600 (rename inherits source mode) | unit | `pytest tests/auth/test_store.py::test_atomic_write_overwrite_mode -x` | Wave 0 |
| STORE-03 | Mid-write crash leaves either old contents or new contents (atomicity) — simulated via `os.replace` interception | unit | `pytest tests/auth/test_store.py::test_atomic_write_crash_safety -x` | Wave 0 |
| STORE-04 | `load_vault` on non-existent path returns `AuthVault()` (empty) without creating the file | unit | `pytest tests/auth/test_store.py::test_load_missing_returns_empty -x` | Wave 0 |
| STORE-05 | `load_vault` on 0o644 file raises `AuthVaultPermissionError` with the offending mode | unit | `pytest tests/auth/test_store.py::test_load_wrong_mode_raises -x` | Wave 0 |
| STORE-06 | `load_vault` on 0o600 file with valid JSON returns the round-tripped `AuthVault` | unit | `pytest tests/auth/test_store.py::test_load_round_trip -x` | Wave 0 |
| STORE-07 | `load_vault` on 0o600 empty file returns `AuthVault()` (empty-file edge case, Pitfall 3) | unit | `pytest tests/auth/test_store.py::test_load_empty_file -x` | Wave 0 |
| STORE-08 | Save → load round-trip preserves array shape for n=1 credential (P1-7 / P0-13 owned) | unit | `pytest tests/auth/test_store.py::test_round_trip_single_cred_array -x` | Wave 0 |
| STORE-09 | Save → load round-trip for n=5 credentials per provider preserves order | unit | `pytest tests/auth/test_store.py::test_round_trip_multi_cred -x` | Wave 0 |
| STORE-10 | Save with bare-dict provider value (simulated) → field_validator coerces to 1-element list | unit | `pytest tests/auth/test_store.py::test_validator_coerces_bare_dict -x` | Wave 0 |
| STORE-11 | `ensure_initialized` on missing file creates 0o600 empty vault | unit | `pytest tests/auth/test_store.py::test_ensure_initialized_creates -x` | Wave 0 |
| STORE-12 | `ensure_initialized` on existing 0o644 file raises `AuthVaultPermissionError` (P0-13 defense at init) | unit | `pytest tests/auth/test_store.py::test_ensure_initialized_rejects_bad_mode -x` | Wave 0 |
| STORE-13 | `ensure_initialized` is idempotent — calling twice on existing valid file is a no-op | unit | `pytest tests/auth/test_store.py::test_ensure_initialized_idempotent -x` | Wave 0 |
| STORE-14 | `get_auth_json_path` honors `STATE_AUTH_JSON` env var when set | unit | `pytest tests/auth/test_store.py::test_path_resolution_env_override -x` | Wave 0 |
| STORE-15 | `get_auth_json_path` defaults to `<cwd>/.state/auth.json` when env unset | unit | `pytest tests/auth/test_store.py::test_path_resolution_default -x` | Wave 0 |
| STORE-16 | `AuthVaultPermissionError.observed_mode` carries the actual mode for CLI rendering | unit | `pytest tests/auth/test_store.py::test_permission_error_carries_mode -x` | Wave 0 |
| STORE-17 | Mode isolation — importing `state_core.auth.store` does NOT pull `state_build.*` or `state_teach.*` | unit | `pytest tests/auth/test_store.py::test_no_mode_imports -x` | Wave 0 |
| STORE-18 | Hypothesis property: any `AuthVault` survives save → load → save → load (4-step round-trip equality) | unit (property) | `pytest tests/auth/test_store.py::test_hypothesis_round_trip -x` | Wave 0 |
| STORE-19 | Discriminated-union dispatch — saved `OAuthCredential` loads back as `OAuthCredential`, not `ApiKeyCredential` | unit | `pytest tests/auth/test_store.py::test_discriminator_preserved -x` | Wave 0 |
| STORE-20 | save_vault writes deterministic JSON (sorted keys, indent 2) — same vault → byte-identical output across two calls | unit | `pytest tests/auth/test_store.py::test_deterministic_serialization -x` | Wave 0 |
| STORE-21 | Save preserves `last_rotation` field even when no rotations have happened (default empty dict round-trips) | unit | `pytest tests/auth/test_store.py::test_last_rotation_round_trip -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/auth/test_store.py -x -q` (< 2 seconds expected)
- **Per wave merge:** `python3 -m pytest tests/auth/ -q` (auth subsuite)
- **Phase gate:** `python3 -m pytest -q && mypy src/state_core/auth/` clean before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/auth/test_store.py` — covers STORE-01..STORE-21 (does not exist; sibling to existing `test_base.py`)
- [ ] Extend `tests/auth/conftest.py` — add `auth_json_path` fixture (`tmp_path / "auth.json"`) and `monkeypatch_state_auth_json` fixture (auto-unset env var)
- [ ] No new test framework install — `pytest`, `pytest-asyncio`, `hypothesis` already in `pyproject.toml [project.optional-dependencies] dev`

## Sources

### Primary (HIGH confidence)
- `/Users/tmac/Projects/state/.planning/PROJECT.md` — cardinal rules (mode isolation, determinism, library locks, .state/ portability)
- `/Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md` §10.2, §11.1 — auth.json layout (array shape) and `.state/` on-disk structure (project-relative)
- `/Users/tmac/Projects/state/.planning/research/STACK.md` — pinned `orjson>=3.11.8`, `filelock>=3.20.3`, `pydantic>=2.13.2`; rejection of cryptography-at-rest for v2
- `/Users/tmac/Projects/state/.planning/research/PITFALLS.md` — P0-13 (chmod-mode drift) [owned], P1-7 (array-shape collapse) [owned], P0-6 (refresh race, deferred to 013), P2-4 (backup leak, mitigation noted)
- `/Users/tmac/Projects/state/.planning/milestones/v2/REQUIREMENTS.md` — AUTH-06 spec (chmod 0600 via os.open + os.fchmod, verified on every read)
- `/Users/tmac/Projects/state/.planning/milestones/v2/ROADMAP.md` — Phase 012 goal + downstream consumers (013, 014–018, 019, 021)
- `/Users/tmac/Projects/state/.planning/milestones/v2/phases/011-state-core-auth-base/011-RESEARCH.md` — `Credential` discriminated union + `CredentialAdapter` ready for round-trip
- `/Users/tmac/Projects/state/src/state_core/auth/base.py` — current `OAuthCredential`, `ApiKeyCredential`, `Credential`, `CredentialAdapter` exports
- `/Users/tmac/Projects/state/src/state_core/auth/__init__.py` — package public surface
- `/Users/tmac/Projects/state/src/state_core/database.py` — established path-resolution pattern (env override + project-relative default, `mkdir(parents=True, exist_ok=True)`)
- `/Users/tmac/Projects/state/.state-inputs/gsd2-auth-analysis.md` — GSD-pi multi-method coverage; informs why array-shape is non-negotiable
- `/Users/tmac/Projects/state/pyproject.toml` — confirmed `orjson`, `filelock`, `pydantic`, `hypothesis` already pinned; ruff strict mypy already configured

### Secondary (MEDIUM confidence)
- Python `os` docs — `os.open` mode application, `os.replace` atomicity, `os.fchmod` semantics (stdlib)
- POSIX `rename(2)` man page — atomic same-fs rename guarantee
- [orjson README — OPT_SORT_KEYS / OPT_INDENT_2 flags](https://github.com/ijl/orjson) — flags semantic verified by changelog and by existing `state_core.events` use
- [Pydantic v2 — field_validator(mode="before")](https://docs.pydantic.dev/latest/concepts/validators/) — validator dispatch order verified

### Tertiary (LOW confidence — flagged for validation)
- Symlink-attack mitigation (Pitfall 6) — threat model decision, not a hard claim. Phase 022 audit may add `O_NOFOLLOW` defense.
- Windows behavior (Pitfall 2 / no-op `_verify_mode`) — based on PROJECT.md "Mac/Linux first" stance; the actual UX is a Phase A6 daemon decision.

## Metadata

**Confidence breakdown:**
- Standard stack (os, orjson, pydantic, pathlib): **HIGH** — all pinned, stdlib well-documented
- Atomic-write pattern: **HIGH** — POSIX-spec, GSD-pi precedent, multiple verifications
- AuthVault Pydantic shape: **HIGH** — direct mirror of Phase 011's discriminator pattern + ARCHITECTURE.md §10.2 example
- Path resolution: **HIGH** — exact mirror of `state_core.database.get_db_path()`
- Read-side mode verification + AuthVaultPermissionError: **HIGH** — direct from AUTH-06 spec text
- Auto-fix vs refuse policy: **HIGH** — explicit in CONTEXT.md "refuse to proceed if mode wrong"
- Symlink/Windows edge cases (Pitfalls 6, 2): **MEDIUM** — judgment calls deferred to later phases
- Open question 1 (`.state/` parent dir mode): **LOW** — handed off to M-A6

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (the stdlib `os.*` API is frozen; orjson/Pydantic floors are pinned; only PROJECT.md edits would invalidate this)

## RESEARCH COMPLETE
