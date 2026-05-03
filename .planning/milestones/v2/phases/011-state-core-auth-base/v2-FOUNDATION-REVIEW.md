# v2 Auth Foundation — Cross-Phase Review (011 + 012 + 013)

**VERDICT: SAFE TO MERGE WITH NOTES** — the API surface composes cleanly, the determinism story holds, and the secret-hygiene posture is genuinely good. Two items are worth tightening before phase 014 lands; everything else is FYI.

Reviewer: senior-eng pre-merge pass. Scope: cross-phase composition only — per-phase REVIEWs are CLEAN.

---

## What I'd block on

**None.** Nothing here is bad enough to block the merge. The two items below are noted as "tighten before / during phase 014" rather than pre-merge gates, because they don't break correctness today — they just create predictable tripping hazards for the OAuth provider work.

## What I'd flag but not block on

### 1. `refresh_credential` quietly re-resolves `now` mid-call — fine in practice, but the contract is fuzzy
`src/state_core/auth/refresh.py:227-228` — when callers pass `now=None`, the module reads `time()` once and reuses that value for both the quick-check and the in-lock double-check. Good. But the docstring (lines 213-224) does not state this. Phase 019's round-robin mutation of `last_rotation` will want to inject `now` for replay-determinism, and a future contributor reading just the public docstring won't know that omitting `now` produces a non-deterministic call. **Fix:** one-line docstring addition: "When `now` is None, the wall clock is read once at entry and frozen for the duration of the call."

### 2. `http_headers` Protocol does not pin dict ordering — a real risk for phase 014 stealth
`src/state_core/auth/base.py:176-184`. The Protocol returns `dict[str, str]`. CPython 3.7+ preserves insertion order, so a careful provider implementation will emit `{authorization, user-agent, x-app, anthropic-beta}` byte-for-byte. But:

- there is no test asserting order is preserved across a round-trip
- no test asserting that `**header_dict` into httpx preserves order
- `orjson.OPT_SORT_KEYS` is used for the vault payload (`store.py:269`) — if anyone reflexively reaches for that pattern in phase 014's regression test fixture, the captured-headers golden file will silently reorder

`.state-inputs/claude-oauth.md:45-48` confirms three stealth headers must match byte-for-byte. **Fix:** add a one-line BASE-12 test in tests/auth/test_base.py asserting `list(method.http_headers(cred).keys()) == [...expected order...]` once a real provider exists. Cheap, prevents a debugging nightmare.

### 3. `extras: dict[str, Any]` is a mutability footgun the docstring acknowledges but doesn't enforce
`base.py:80-86, 103-104` — frozen=True freezes the *instance*, not the dict it holds. A provider doing `cred.extras["scope"] = "..."` post-construction silently violates the immutability contract. Docstring says "undefined behavior"; the test suite never exercises it. Phase 019 (round-robin) and Phase 020 (redactor) will both touch this. **Fix:** consider `MappingProxyType` wrapping in a `field_validator(mode="after")`, or at minimum a unit test that `cred.extras["k"] = "v"` either fails or doesn't escape the frozen contract. Not load-bearing, but a 30-line preventive measure.

### 4. `read_credential` and the `lock_path.touch(exist_ok=True)` re-creation
`refresh.py:194-201, 300-307` — filelock 3.29 unlinks on release; the code re-creates the lockfile so REFRESH-22 / observability tools see it. This is fine for the current setup, but: (a) on a read-only filesystem the `OSError` is swallowed (`except OSError: pass`), so a corrupt/RO `.state/` becomes a silent no-op rather than a loud error. (b) Phase 014's OAuth callback server (listening on localhost) will run **outside** any held lock, but if the callback handler then calls `save_vault` directly without going through `refresh_credential`, you bypass the lock entirely. **Fix:** Phase 014 RESEARCH should call out "vault writes from the OAuth callback handler must go through `refresh_credential` (force=True for first login) or acquire `_new_async_lock` explicitly." This is a phase-014 documentation concern, not a phase-013 bug.

### 5. Phase 019 round-robin will mutate `vault.last_rotation` — current API doesn't expose a write helper
`refresh.py:204-307` only writes via `save_vault` after `vault.providers[provider_id][idx] = new_cred`. Phase 019 will need to mutate `vault.last_rotation[provider_id] = next_idx` inside the same lock window. Today there is no `update_last_rotation()` helper, so phase 019 will either (a) inline its own `_new_async_lock` block (duplication), or (b) extend `refresh_credential` with a callback. Not a blocker — just flagging that the API surface is incomplete for the milestone, by design. Per-phase reviews wouldn't catch this because each phase is internally consistent.

### 6. Lockfile cleanup after process kill — covered, but not the `.tmp` file
REFRESH-21 (`tests/auth/test_refresh.py:524-566`) verifies flock(2) auto-release on SIGKILL. Good. But `_atomic_write` (`store.py:200`) creates `auth.json.tmp` with mode 0o600 — if `os.fsync` or `os.write` is the syscall that gets killed, the `.tmp` lingers. No test for that. Future-cred-rotation diagnostics will want this cleaned up; today it's harmless (next save overwrites). **Fix:** consider `try/finally` around the `os.write`/`os.fsync` block to `os.unlink(tmp)` on exception. Or punt to phase 022 audit. Fine either way.

### 7. Symlink attack surface — explicitly deferred, but make sure phase 014 inherits that debt
STORE-22 (`test_store.py:472-480`) is a `@pytest.mark.skip` placeholder pointing at phase 022. Phase 014's `ensure_initialized` call is the first place a real attacker could plant a symlinked `.state/auth.json` → `~/.ssh/authorized_keys`. The 0o600 enforcement protects the *target* mode, but the write goes through. **Fix:** phase 014's plan should explicitly inherit STORE-22 as a known gap, not silently assume "the foundation handles it."

## What's surprisingly well done

1. **The "wire-shape `expires`, buffer at check-time" rule is consistent across all three modules.** `base.py:65-72` documents it; `refresh.py:154-167` enforces it; nothing in `store.py` ever subtracts. The hypothesis property test (REFRESH-26, `test_refresh.py:687-697`) makes the buffer boundary genuinely lockable. No double-application risk. This is the kind of cross-phase invariant that's easy to violate in v3 — the docstrings make the rule difficult to misread.

2. **Re-entry deadlock is documented AND tested, not hand-waved.** `refresh.py:41-46` explicitly calls out Pitfall 6, REFRESH-27 (`test_refresh.py:702-723`) is a `@pytest.mark.slow` test that proves the deadlock by waiting for the 10 s timeout. Most teams skip the "prove the footgun fires" test because it's slow; including it means future refactors that accidentally call `read_credential` from inside a lock will fail loudly instead of hanging in production.

3. **Secret hygiene is layered correctly.** `Field(repr=False)` on `access`/`refresh`/`key` (base.py:59,62,97); `AuthVaultPermissionError.__str__` (store.py:73-79) explicitly excludes file contents; the structlog events in `refresh.py` (lines 247-296) only ever log `provider_id`, `idx`, `lock_path`, and `lock_held_seconds` — never the credential. STORE-16 (`test_store.py:330-349`) actively asserts `sk-ant`-shaped substrings don't leak into the exception message. The Phase 020 redactor will be a net for accidents, not the primary defense — that's the right posture.

---

## Spot checks that came back clean

- **Mode isolation**: BASE-08, STORE-17, REFRESH-23 all verify no `state_build` / `state_teach` leak via `sys.modules` delta after `importlib.reload`. Imports in all three modules are stdlib + pydantic + orjson + structlog + filelock + sibling `state_core.auth.*`. Clean.
- **Re-export naming collisions**: `__init__.py:40-62` exports 17 symbols. None shadow Python builtins. `Credential`, `AuthVault`, `RefreshLockTimeout`, `is_expired_buffered` are all clear, no underscore-prefixed names accidentally exposed.
- **TypeAdapter usage**: `CredentialAdapter` (base.py:120) is module-level, not constructed per-call — the per-call construction antipattern that Pydantic v2 docs warn about. Good.
- **`assert` in `save_vault`** (`store.py:263-265`): runs under `python3 -O`-stripping risk, but the Pydantic validator already guarantees the invariant. Belt-and-suspenders, not load-bearing. Acceptable.
- **`pytest.importorskip` in conftest** (`conftest.py:78,106`): elegant RED-state handling that survived the Plan 01 → Plan 02 lag. No fixtures error at collection.

---

_Reviewed: 2026-04-28_
_Reviewer: senior-eng cross-phase pass_
_Branch: `gsd/phase-011-state-core-auth-base` (12 commits, ~2,495 lines)_
_Scope: 011 + 012 + 013 composition only_
