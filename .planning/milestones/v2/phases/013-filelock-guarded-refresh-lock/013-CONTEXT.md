# Phase 013: Filelock-guarded refresh lock (`refresh.py`) - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

10s acquire, re-read auth.json, double-check expiry, refresh only if still stale, write, release; reader-path blocks refresher.

Owns: refresh-coordination layer (`src/state_core/auth/refresh.py`).
Requirements: AUTH-07, AUTH-09.
P0 pitfalls owned: P0-6 (concurrent refresh / token clobber), P0-7 (5-minute expiry buffer).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per workflow.skip_discuss. Use ROADMAP, RESEARCH, AUTH-07/AUTH-09 specs, P0-6/P0-7 pitfalls, Phase 012's `load_vault`/`save_vault` API, and Phase 011's `Credential`/`AuthMethod` Protocol.

</decisions>

<code_context>
## Existing Code Insights

Inputs from prior phases:
- Phase 011: `Credential`, `AuthMethod` Protocol with async `refresh(cred) -> Credential`
- Phase 012: `load_vault(path)`, `save_vault(path, vault)`, `get_auth_json_path()`, `AuthVaultPermissionError`

Downstream consumers:
- Phase 014–018 providers — their `refresh()` runs INSIDE the filelock acquired here
- Phase 019 multi-cred round-robin — calls `refresh.refresh_credential` to rotate stale creds
- Phase 022 CLI — `state auth refresh <provider>` invokes this

</code_context>

<specifics>
## Specific Ideas

- `filelock.FileLock(path / "auth.json.lock", timeout=10.0)` — 10-second acquire
- Double-checked refresh pattern: acquire lock → re-read vault → check expiry AGAIN → refresh only if still stale (defends against thundering herd of waiters)
- 5-minute buffer (AUTH-09) lives HERE in `is_expired_buffered(cred, now, buffer=300.0)`, not in `OAuthCredential.expires` field (kept as wire-shape per Phase 011 Pattern 3)
- Reader-side `read_credential(path, provider_id)` MUST acquire the same lock briefly to block during refresh window (avoid reading half-written vault)
- Async-friendly: filelock is sync; wrap in `asyncio.to_thread` for the lock acquisition; `AuthMethod.refresh()` is awaited normally inside
- `RefreshLockTimeout` exception on 10s timeout (subclass of TimeoutError)

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
