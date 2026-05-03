# Phase 019: Multi-cred round-robin across a provider's credential array — Research

**Researched:** 2026-04-30
**Domain:** Concurrency-safe credential selection over `vault.providers[provider_id]: list[Credential]` with persisted rotation index, 429 fallback, and cool-down marking
**Confidence:** HIGH for module shape, public API, and concurrency model (every primitive — `last_rotation`, filelock, atomic save — is already shipped); MEDIUM-to-HIGH for the cool-down/rate-limit-seen design (multiple acceptable shapes, this RESEARCH pins one with justification); HIGH for pitfalls (PITFALLS.md P1-7 + P1-8 own the failure modes).

<user_constraints>
## User Constraints

CONTEXT.md does not exist for Phase 019 (`workflow.skip_discuss: true` in `.planning/config.json`). Constraints derive from ROADMAP, REQUIREMENTS, PITFALLS, and the upstream-shipped vault schema. The planner has full discretion on implementation details below; the items in this section are NOT user-locked decisions but rather *upstream invariants the implementation must honour*:

### Locked invariants (inherited from upstream phases — non-negotiable)

1. **`AuthVault.last_rotation: dict[str, int]` already exists** (Phase 012, `src/state_core/auth/store.py:98`). Phase 019 MUST consume the existing field — no schema bump, no new field name. Pydantic round-trip already covered by `tests/auth/test_store.py::test_last_rotation_round_trip` (STORE-21).
2. **Array-shape invariant (P1-7 / P0-13):** `vault.providers[provider_id]` is *always* a `list[Credential]`, even for n=1. Phase 019 MUST NOT relax or amend this; the `field_validator("providers", mode="before")` coercion is sufficient (`store.py:100-123`). The pre-write assertion in `save_vault` (`store.py:262-265`) is the second defense layer.
3. **Filelock locking ownership lives in `state_core.auth.refresh`** (Phase 013). Phase 019's persistence path MUST reuse `_new_async_lock(vault_path)` (or its public equivalent) when bumping `last_rotation`; do NOT spin a second lockfile or invent a new lock primitive.
4. **Mode isolation:** `state_core.auth.*` imports stdlib + pydantic + structlog + filelock + httpx + state_core's own auth submodules. NO `state.build.*` or `state.teach.*`. CI import-graph lint (`tests/auth/test_import_graph.py`) is already in place.
5. **Determinism:** No `time.time()` / `datetime.now()` / `random.*` reads inside core selection logic. The clock is injected via a `now: float` parameter (Phase 011 cardinal rule 2; mirrored by Phase 013's `is_expired_buffered`, `refresh_credential`).
6. **Vault > env precedence (Phase 018):** env-synthesized credentials are ephemeral and live outside the vault. Round-robin operates on **vault-sourced lists ONLY**. `loader.load_credentials` returns `[ApiKeyCredential(...)]` from env synthesis with no `last_rotation` to track; Phase 019 MUST gracefully degenerate to "return the only cred" when the list size is 1 — including the env-synth case.

### Claude's Discretion

All implementation choices below the upstream invariants are at Claude's discretion (no `/gsd:discuss-phase` was run; `workflow.skip_discuss: true`):

- **Module placement:** new `state_core/auth/rotation.py` sibling of `loader.py`/`refresh.py` (RECOMMENDED), vs. extending `loader.py`, vs. method on `AuthVault`. RESEARCH §Architecture Patterns picks `rotation.py`.
- **Public API shape:** `select_credential(provider_id, *, vault_path=None, now=None) -> tuple[int, Credential]` returning the chosen `(idx, cred)` pair (RECOMMENDED — caller needs the idx for `refresh_credential` + 429-marking re-call). Alternatives below.
- **Rotation-bump persistence semantics:** persist on EVERY selection (high write traffic) vs. persist only on 429-fallback (low traffic, but index drifts in-memory). RESEARCH recommends **persist-on-bump**: in-memory increment + persist-coalesced via the same filelock that the next refresh would acquire. Mid-confidence; see §Architecture Pattern 2.
- **Cool-down representation:** transient in-memory `dict[(provider_id, idx)] -> expires_at_epoch` (RECOMMENDED, RESEARCH §Pattern 3) vs. persisted `Credential.cool_down_until` field (rejected — would force a Credential schema bump and pollute the wire shape).
- **Algorithm choice:** naive `last_rotation[provider_id] = (last_rotation[provider_id] + 1) % len(creds)` (ROADMAP literal reading) vs. PITFALLS.md P1-8's **time-bucketed rotation** `(now_ms // bucket_ms) % len(creds)`. RESEARCH §Pattern 1 PINS the time-bucketed approach with last_rotation as a *seed/floor* — NOT a naive counter. **This is a load-bearing research finding** that the planner must reconcile with the ROADMAP's wording. See §Open Questions Q1.
- **429 fallback ergonomics:** caller-driven (loader returns next-credential on retry) vs. internal retry loop. RESEARCH recommends **caller-driven** (§Pattern 4): a single `select_credential` call returns one cred + its idx; on 429 the caller marks-cooled-down and re-calls. Caller-driven keeps round-robin synchronous, deterministic, and unit-testable; the alternative requires injecting an httpx client into the rotation module which violates separation of concerns.

### Deferred Ideas (OUT OF SCOPE for Phase 019)

- **Rate-limit-seen flag persisted to disk.** Cool-down is in-memory only for v2/M-A2; persistence would force a Credential schema bump and survives across daemon restarts in a way users probably don't want (a paused 5-min cool-down resumes on next boot). Defer to v3 or a later phase if real telemetry shows skew.
- **Quota-aware weighted round-robin.** Some providers (Gemini free tier) have visible per-day quotas. Phase 019 stays at uniform round-robin; quota-aware weighting is provider-specific and lives in v3 Provider Routing.
- **Per-credential health endpoints / liveness checks.** Phase 022 may add `state auth status --verify`; Phase 019 stays format-only.
- **Multi-provider failover (anthropic exhausted → openrouter).** That's v3 Provider Routing's domain.
- **schema_version 2 bump.** Not needed — `last_rotation` already exists at schema_version 1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **AUTH-08** | Multi-cred round-robin across credentials of the same provider | §Standard Stack (pure stdlib + filelock — no new deps). §Architecture Pattern 1 (time-bucketed selection algorithm using `last_rotation` as the persisted index/seed). §Architecture Pattern 2 (in-lock read-modify-write of `last_rotation` reusing Phase 013's filelock). §Architecture Pattern 3 (in-memory cool-down map for 429-marked credentials). §Architecture Pattern 4 (caller-driven 429 fallback API). §Don't Hand-Roll (delegate locking + atomicity to existing primitives). §Common Pitfalls catalogues P0/P1/P2/P3 ratings of every concurrency edge case. §Validation Architecture maps every behaviour to a pytest row. |
| **(owned) P1-7** | Array-shape preservation across migrations | Already enforced upstream (§User Constraints invariant 2). Phase 019 contributes a *negative* test: round-robin selection on n=1 array remains a list (not collapsed) after `last_rotation` bump. §Validation row ROTATE-13. |
| **(owned) P1-8** | Starvation: same credential refreshed forever | §Pattern 1 (time-bucketed rotation prevents idx-0 monopoly). §Pattern 3 + §Pitfall 4 (cool-down on 429 forces skip even within a time bucket). §Validation rows ROTATE-07, ROTATE-08, ROTATE-09. |
| **(consumed, not owned) P1-9** | Refresh lock deadlock with daemon shutdown | Phase 013 owns the 10s/15s timeouts. Phase 019 reuses `refresh.refresh_credential` for the network refresh path; the rotation persistence path uses a brief read-modify-write inside the same `_new_async_lock` window. §Pitfall 2. |
| **(consumed) P1-4** | Free-tier quota exhaustion not surfaced | Round-robin tries the next credential automatically on 429; surface formatting (TUI toast) is v3 Provider Routing's surface. Phase 019 contributes the `mark_rate_limited(provider_id, idx, until=...)` API the surface layer will call. |
</phase_requirements>

## Summary

Phase 019 is the smallest of the v2 phases by raw LOC count (estimated ~150–250 LOC of implementation across one new module + minor `__init__` re-export edits) but carries non-trivial concurrency reasoning. Every primitive is already shipped:

- **`AuthVault.last_rotation: dict[str, int]`** — Phase 012 (`store.py:98`). Round-tripped (STORE-21).
- **Array-shape invariant** — Phase 012's `field_validator` + pre-write assertion (P0-13 / P1-7 owned).
- **Cross-process filelock with 10s acquire timeout** — Phase 013 (`refresh._new_async_lock`).
- **In-lock atomic save** — Phase 013's `refresh_credential` is the canonical pattern (load → mutate → save under the same lock instance).
- **Vault-sourced credential list** — Phase 018's `loader.load_credentials(provider_id) -> list[Credential]` returns the live array.

The non-trivial design work is:

1. **Algorithm choice.** PITFALLS.md P1-8 prescribes `(now_ms // bucket_ms) % len(creds)` (time-bucketed). The ROADMAP wording ("rotation index persisted in `last_rotation`") could be read either as naive `(last_rotation+1) % n` or as "use `last_rotation` to *seed* a deterministic time-bucketed rotation." This RESEARCH pins **time-bucketed with last_rotation as the persisted seed** — it satisfies both wordings and is what P1-8 mitigation actually requires.

2. **Cool-down representation.** A 429 (or "rate-limit-seen") on cred[i] should temporarily skip cred[i] without permanently mutating the array. Persisting this would require a Credential field bump (rejected — wire shape is already pinned for header tests). In-memory `dict[(provider_id, idx)] -> expires_at` keyed on the rotation-module singleton (or daemon-local state) is the right shape for v2.

3. **429 fallback ergonomics.** Two viable shapes: (a) loader internally retries with next cred until success, or (b) loader returns one cred + its idx; caller marks-cooled-down on 429 and re-calls. (b) is the right answer because it keeps the rotation module pure (no httpx dependency), composes cleanly with Phase 013's `refresh_credential`, and aligns with how v3 Provider Routing will inject the litellm/anthropic-direct call site between selection and 429-handling.

4. **Persistence semantics.** Persist `last_rotation` updates on every selection (under the filelock) vs. only on 429-fallback. Recommendation: **persist on selection** but with a coalesced write — see §Pattern 2. Cost is one filelock acquire + one atomic JSON write per cred selection, which is ~1 ms on a local filesystem and dominated by the actual httpx call that follows. Concrete benefit: index doesn't drift across daemon restarts (the user's "fairness across the cred set over the lifetime of the host" intuition holds).

**Primary recommendation:** Implement `state_core.auth.rotation` as a single ~200 LOC module exposing four functions: `select_credential(provider_id, *, vault_path=None, now=None) -> tuple[int, Credential]`, `mark_rate_limited(provider_id, idx, *, until: float) -> None`, `clear_rate_limited(provider_id, idx) -> None` (callable on 200 OK to clear stale cool-downs early), and `iter_active_credentials(provider_id, *, vault_path=None, now=None) -> Iterator[tuple[int, Credential]]` for diagnostic surfaces. Test as 25 RED stubs in `tests/auth/test_rotation.py` covering the algorithm, persistence, cool-down map, edge cases (n=0, n=1, n shrinks), and a hypothesis property test for fairness over N rounds. No new deps. No schema bump.

## Standard Stack

### Core (all already pinned)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `os` (stdlib) | 3.12 | `os.environ.get("STATE_AUTH_JSON")` for path resolution; reuse `get_auth_json_path()` | Stdlib — every auth module already uses it. |
| `time` (stdlib) | 3.12 | `time.time()` as the *single* clock read in the public-default arm of `select_credential` (the `now=None` branch) — exactly mirrors `refresh.refresh_credential` (`refresh.py:227-228`). | One clock read at module boundary; injected `now` everywhere internally (cardinal rule 2). |
| `pathlib.Path` | 3.12 | Path manipulation, mirrors `store.py` / `refresh.py`. | Idiomatic. |
| `typing` (stdlib) | 3.12 | `Iterator` for the generator helper. | Stdlib. |
| `pydantic` | ≥2.13.2 | Already imported transitively via `AuthVault` round-trip; rotation module does NOT define new Pydantic models for v2. | No new dep. |
| `filelock` | ≥3.20.3 | **REUSE Phase 013's `_new_async_lock(vault_path)`** — do NOT construct a new lock primitive. | Cross-process semantics, CVE-2026-22701 floor, async-aware. |
| `structlog` | ≥25.1 | `log = structlog.get_logger(__name__)` mirroring `loader.py:77`. | Project standard for observability. |
| `state_core.auth.{base,store,refresh,loader,errors}` | — | Internal imports — provides `Credential`, `AuthVault`, `_new_async_lock`, `get_auth_json_path`, `load_vault`, `save_vault`, `load_credentials`, `UnknownApiKeyProviderError`. | Phase 019 is pure orchestration over the existing surface. |

### Supporting (already in dev deps)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | ≥8.4.0 | Unit tests + parametrize. | All tests. |
| `pytest-asyncio` | ≥1.3.0 | `asyncio_mode = "auto"` already set. | If `select_credential` ends up async (RECOMMENDED — see §Pattern 4). |
| `hypothesis` | ≥6.120 | Property test: "every credential is selected at least once over N=10·len(creds) rounds with bucket_ms=1." | One single property test in `test_rotation.py`. |
| `freezegun` (optional) | — | Time injection for the `now`-default arm. | NOT strictly needed — `now: float | None = None` parameter pattern (mirrors Phase 013) makes time injection trivial. Skip freezegun unless we need to test the wall-clock-default branch. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fresh `state_core.auth.rotation` module | Extend `state_core.auth.loader.py` with `select_credential` | **Rejected.** `loader.py`'s job is *vault-vs-env precedence*, a one-shot lookup. Round-robin is *stateful* (needs `last_rotation` + cool-down map) and locks the vault on the persistence path. Mixing them makes both modules harder to reason about. Sibling-module placement matches the existing precedent (refresh.py, loader.py, store.py — each owns one orchestration concern). |
| Method on `AuthVault` | `vault.next_credential(provider_id, now)` instance method | **Rejected.** `AuthVault` is a Pydantic data model; adding a method that opens a filelock on disk would couple in-memory data with I/O orchestration. Same anti-pattern as `cred.refresh()` — Phase 011 deliberately put refresh in `state_core.auth.refresh`, not on the Credential. |
| Naive counter `last_rotation = (last_rotation + 1) % n` | Time-bucketed `(now_ms // bucket_ms) % n` with last_rotation as a seed | **Recommended (time-bucketed).** PITFALLS.md P1-8 explicitly mandates time-bucketed to prevent first-cred-monopoly under refresh-lock contention. ROADMAP wording is satisfied by treating `last_rotation` as the persisted bucket-base index that survives daemon restarts. See §Pattern 1 + §Open Questions Q1. |
| Cool-down on Credential schema (`OAuthCredential.cool_down_until: float \| None`) | In-memory dict on the rotation module | **Rejected.** Bumping the Credential wire shape forces re-serializing every existing vault, and Phase 022's captured-header regression tests (AUTH-13) want the Credential model frozen. In-memory is the right shape for v2 — the daemon is the only long-lived process; restarts on cool-down expiry are acceptable (the cool-down was purely a soft-skip, not a hard-disable). |
| Internal retry loop on 429 (`select_credential` retries until success) | Caller-driven (`select_credential` returns one cred; caller calls `mark_rate_limited` then re-calls) | **Recommended (caller-driven).** Avoids dragging httpx into the rotation module; aligns with Phase 013's pure-orchestration shape; makes unit tests trivial (no httpx mock needed for the rotation module itself). v3 Provider Routing will be the natural site for the loop because it owns the call. |
| Persist `last_rotation` only on 429-fallback (write storm avoidance) | Persist on every selection | **Recommended (persist on every).** Cost is dominated by the httpx call that follows. Benefit: round-robin survives restarts without idx-0 monopoly on cold start. See §Pattern 2 cost analysis. |
| Per-provider locks (separate lockfile per provider_id) | Reuse `auth.json.lock` (single per-vault lock from Phase 013) | **Recommended (reuse).** Simpler. Contention is bounded — `last_rotation` write is a 1-ms read-modify-write, much faster than the ~250-ms httpx refresh that the same lock guards. Per-provider locks are a v3+ optimization if telemetry shows real contention. |
| Async `select_credential` | Sync `select_credential` | **Recommended (async).** Mirrors `refresh.refresh_credential` and keeps `_new_async_lock` usage idiomatic. The `await async_lock.__aenter__` pattern is the only filelock entry point for async code paths in the daemon. Sync would force a `asyncio.run` or `to_thread` wrapper at every call site. |

**Installation:** No new deps. Every library is already pinned and imported by sibling modules.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/auth/
├── __init__.py              # ADD: re-export select_credential, mark_rate_limited, clear_rate_limited
├── base.py                  # Phase 011 — DO NOT EDIT
├── errors.py                # Phase 015 — possibly ADD: NoCredentialsAvailableError (see §Pattern 4)
├── store.py                 # Phase 012 — DO NOT EDIT (last_rotation field already present)
├── refresh.py               # Phase 013 — possibly export _new_async_lock as a public helper
├── loader.py                # Phase 018 — DO NOT EDIT
├── rotation.py              # ← THIS PHASE — new module, ~200 LOC
└── providers/
    ├── api_key.py           # Phase 018 — DO NOT EDIT
    └── …                    # Phases 014–017 — DO NOT EDIT
```

**One module-level edit outside `rotation.py`:** `state_core/auth/__init__.py` re-exports the new public API (mirrors how Phase 018 added `load_credentials`).

**Possible second module-level edit:** Phase 013's `refresh.py` defines `_new_async_lock(vault_path)` as a private helper. Phase 019 needs the same lock primitive. Two options:
   1. **Promote to public (`new_async_lock`)** — minimal edit, adds it to `refresh.__all__`. Recommended.
   2. **Inline the construction in `rotation.py`** — duplicates the `thread_local=False, poll_interval=0.05, timeout=10.0` config across modules. Rejected (single source of truth).

### Pattern 1: Time-bucketed selection algorithm (the SELECT path)

**What:** Select cred index using `last_rotation[provider_id]` as the persisted seed and the current time bucket as the rotation engine. Skip cool-down-marked indices.

**Why:** PITFALLS.md P1-8 mandates time-bucketed rotation to prevent the first-cred-monopoly failure mode (idx 0 always picked → refresh lock serializes on it → other creds never exercised). A naive counter `(last_rotation+1) % n` is theoretically uniform but in practice idx 0 still gets picked first on every cold start — and a refresh-lock contention scenario stacks all callers on the first available cred. Time-bucketing decouples "which cred to use" from "how many calls came in," and `last_rotation` persists the *seed* so different daemon instances and restarts don't all start at idx 0 simultaneously.

**Algorithm:**

```python
# state_core/auth/rotation.py
from __future__ import annotations

from typing import Iterator
import structlog
from state_core.auth.base import Credential
from state_core.auth.store import AuthVault, get_auth_json_path, load_vault, save_vault
from state_core.auth.refresh import _new_async_lock  # or new_async_lock if promoted

log = structlog.get_logger(__name__)

# Bucket width chosen to balance "responsive to load" vs "minimize last_rotation
# write churn." 60_000 ms = 1 minute means rotation steps once a minute under
# nominal load — fine-grained enough that quota-skewed providers shed traffic
# fast, coarse enough that filelock contention from `last_rotation` writes is
# negligible. See §Pattern 2 for the persistence cost analysis.
BUCKET_MS: int = 60_000


def _bucket_index(now_seconds: float, n: int, seed: int) -> int:
    """Return the cred-array index for the current time bucket.

    Pure function. `seed` is `vault.last_rotation.get(provider_id, 0)` — it
    rotates the bucket origin so daemons that start at the same wall-clock
    moment don't all pick idx 0 simultaneously (anti-monopoly fairness).

    >>> _bucket_index(1_770_000_060.0, n=3, seed=0)  # bucket 29_500_001
    1
    >>> _bucket_index(1_770_000_060.0, n=3, seed=1)  # seed shifts +1
    2
    """
    if n <= 0:
        raise ValueError("cannot bucket-index an empty credential array")
    bucket = int(now_seconds * 1000) // BUCKET_MS
    return (bucket + seed) % n
```

**Critical detail:** `last_rotation` is consumed as a *seed* (rotation origin), not a *counter*. The bucket-index calculation drives the actual rotation; `last_rotation` is bumped on each selection so:
   1. The next `select_credential` after a cool-down skip starts from a different origin.
   2. Daemon restarts pick up where the previous instance left off (anti-cold-start-monopoly).

**Why not just `(last_rotation + 1) % n`?** Two failure modes:
   - **Refresh-lock convoy.** Five concurrent callers serialize on the lock; first one picks idx 0, increments, second picks idx 1, etc. This is *fair within the convoy* but the next convoy starts at the same idx the previous ended at, and under sustained load the entire array shifts in lockstep. Time-bucketing breaks the lockstep: at minute boundaries every caller jumps to the same new idx, but cool-down skipping fans them out fairly.
   - **Cold-start monopoly.** On daemon restart `last_rotation` is whatever it was; if a previous run ended on cred 4 of 5, the next run starts on cred 0 (because `(4+1) % 5 = 0`). With time-bucketing the cred is determined by the wall clock, so two daemons that happen to start in different time buckets pick different creds.

### Pattern 2: In-lock read-modify-write of `last_rotation` (the PERSIST path)

**What:** Every `select_credential` call acquires the vault filelock briefly, reads the vault, picks the cred, increments `last_rotation[provider_id]`, saves the vault, releases the lock. Same pattern as Phase 013's `refresh_credential` — load → decide → mutate → save under one lock instance.

**Why:** `last_rotation` must survive daemon restarts; cross-process consistency requires the same filelock that `refresh_credential` uses. Concrete cost analysis:

| Operation | Wall-clock cost (local fs, SSD) |
|-----------|---------------------------------|
| `_new_async_lock` construction | ~10 µs |
| `async with lock:` acquire | ~100–500 µs (uncontended); up to 10 s (timeout, contended) |
| `load_vault(path)` (~2 KB JSON) | ~200 µs |
| `_bucket_index` arithmetic | <1 µs |
| `save_vault(path, vault)` (atomic write + fsync) | ~1–3 ms |
| **Total uncontended** | **~1.5–4 ms** |
| Subsequent httpx call (the actual API request) | **~50–300 ms typical** |

So the persistence overhead is roughly 1–10% of the API call it gates. Acceptable. Under 10× concurrency the filelock becomes the bottleneck, but the same filelock already gates `refresh_credential`, so we're not introducing new contention beyond what's already accepted.

**Optimisation candidates for v3 (NOT v2):** memoize `last_rotation[provider_id]` in the daemon process and flush every K calls or every M seconds. Out of scope for Phase 019 — premature optimization.

**Skeleton (async):**

```python
async def select_credential(
    provider_id: str,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
) -> tuple[int, Credential]:
    """Pick the next credential for *provider_id*; persist updated last_rotation.

    Returns (idx, credential). Caller invokes credential, calls
    `mark_rate_limited(provider_id, idx, until=...)` on 429, and re-calls
    `select_credential` to get the next.

    Raises NoCredentialsAvailableError if the provider has zero credentials
    OR if every credential is cool-down-marked (caller should escalate to
    UI / re-login).
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = _now()  # mirror refresh.py:227

    lock = _new_async_lock(vault_path)
    try:
        async with lock:
            vault = load_vault(vault_path)
            creds = list(vault.providers.get(provider_id, []))
            if not creds:
                raise NoCredentialsAvailableError(provider_id, reason="empty")
            seed = vault.last_rotation.get(provider_id, 0)
            idx = _pick_active_index(creds, seed, now, provider_id)
            # Bump seed for the NEXT caller so post-cool-down rounds advance.
            vault.last_rotation[provider_id] = (seed + 1) % len(creds)
            save_vault(vault_path, vault)
            return idx, creds[idx]
    except filelock.Timeout as exc:
        raise RefreshLockTimeout(_lock_path_for(vault_path)) from exc
    finally:
        # Mirror refresh.py:198-201 — recreate lockfile post-release.
        try:
            _lock_path_for(vault_path).touch(exist_ok=True)
        except OSError:
            pass
```

**Note on lock reuse from `refresh_credential`:** if a caller is already inside a held lock (e.g., daemon middleware acquired the lock for some bigger transaction), constructing a *second* `_new_async_lock` instance will deadlock against the 10s timeout (Phase 013 Pitfall 6 — REFRESH-27 verifies). Document this in the rotation.py module docstring.

### Pattern 3: Transient cool-down map (the SKIP path)

**What:** A module-level `dict[(provider_id, idx)] -> until_epoch_seconds` populated by `mark_rate_limited`. `select_credential` skips entries whose `until > now`. Entries auto-expire when their `until` is in the past — no explicit GC needed because the read path checks `now` against `until`.

**Why:** 429 fallback requires the next call to skip the rate-limited cred. Persisting this would force a Credential schema bump (rejected — frozen wire shape). In-memory state lives for the daemon's lifetime; daemon restarts forget cool-downs (acceptable — 429 cool-downs are typically 60s, and an unscheduled daemon restart inside a 60s window is rare and self-correcting).

**Concurrency:** the cool-down map is daemon-local; multiple daemon processes (rare) wouldn't share it. That's *acceptable* because each daemon would independently observe 429s and mark its own cool-down. Cross-daemon coordination via persisted state is over-engineering for v2.

**Skeleton:**

```python
# Module-level singleton — daemon-process-local, NOT cross-process.
_COOL_DOWN: dict[tuple[str, int], float] = {}


def mark_rate_limited(provider_id: str, idx: int, *, until: float) -> None:
    """Mark `vault.providers[provider_id][idx]` as cool-down-active until *until*.

    *until* is epoch seconds. Idempotent — overwriting an existing entry
    extends or shortens the cool-down. Negative or past *until* values
    clear the entry (equivalent to `clear_rate_limited`).
    """
    if until <= 0:
        _COOL_DOWN.pop((provider_id, idx), None)
        return
    _COOL_DOWN[(provider_id, idx)] = until


def clear_rate_limited(provider_id: str, idx: int) -> None:
    """Clear any cool-down entry for `(provider_id, idx)`. Idempotent."""
    _COOL_DOWN.pop((provider_id, idx), None)


def _is_cooled_down(provider_id: str, idx: int, now: float) -> bool:
    until = _COOL_DOWN.get((provider_id, idx))
    if until is None:
        return False
    if until <= now:
        # Auto-expire: remove the stale entry so the dict doesn't grow forever.
        _COOL_DOWN.pop((provider_id, idx), None)
        return False
    return True


def _pick_active_index(
    creds: list[Credential],
    seed: int,
    now: float,
    provider_id: str,
) -> int:
    """Return the index of the next non-cool-down cred starting from
    `_bucket_index(now, len(creds), seed)`. Walks the array up to len(creds)
    times; if every cred is cool-down-marked, raises NoCredentialsAvailableError.
    """
    n = len(creds)
    start = _bucket_index(now, n, seed)
    for offset in range(n):
        idx = (start + offset) % n
        if not _is_cooled_down(provider_id, idx, now):
            return idx
    raise NoCredentialsAvailableError(provider_id, reason="all_cooled_down")
```

**Test surface for in-memory state:** a `pytest` autouse fixture clears `_COOL_DOWN` between tests (mirroring how `tests/auth/conftest.py` already clears `STATE_AUTH_JSON` autouse).

### Pattern 4: Caller-driven 429 fallback (the CONSUMER contract)

**What:** `select_credential` returns ONE `(idx, cred)` pair per call. The caller invokes the API; on 429 the caller calls `mark_rate_limited(provider_id, idx, until=now+60)` and re-calls `select_credential`. The rotation module never owns the httpx client.

**Why:** Keeps the rotation module pure — no httpx dep, no provider-specific 429-body parsing. `select_credential` returns deterministic data given a vault state and `now`; that's unit-testable without HTTP mocks. v3 Provider Routing will own the call site that wraps `select_credential` + `refresh_credential` + the litellm/anthropic-direct call + 429-handling. The boundary is clean.

**Caller pattern (from v3 Provider Routing's eventual perspective — preview, NOT this phase):**

```python
async def call_provider_with_rotation(provider_id: str, request: Request) -> Response:
    while True:
        try:
            idx, cred = await select_credential(provider_id)
        except NoCredentialsAvailableError as exc:
            raise ProviderUnavailable(provider_id, reason=exc.reason)

        # Phase 013 refresh + http_headers injection
        cred = await refresh_credential(method_for(cred), provider_id, idx)
        try:
            return await httpx_call(request, headers=method.http_headers(cred))
        except RateLimit429 as exc:
            until = parse_retry_after(exc) or (time.time() + 60)
            mark_rate_limited(provider_id, idx, until=until)
            continue   # next iteration picks a different cred (or raises NoCredentialsAvailable)
```

**The 429 cool-down duration default (60 s) is v3's policy decision, not Phase 019's.** Phase 019 just exposes the `mark_rate_limited(..., until=...)` shape; the planner can ship `until` as a required keyword (no default) to force callers to think about it.

### Pattern 5: Iterator helper for diagnostics (the OBSERVABILITY surface)

**What:** `iter_active_credentials(provider_id, *, vault_path=None, now=None) -> Iterator[tuple[int, Credential]]` yields every non-cool-down `(idx, cred)` in current bucket order. Used by Phase 022's `state auth status` and v3 Provider Routing's diagnostics.

**Why:** Phase 022 will want to render "5 credentials configured for openai, 3 active, 2 cooled down (until 14:32:01, 14:35:18)." Read-only — no lock acquisition, no `last_rotation` mutation. Acceptable read-skew is the same level Phase 013's `read_credential` accepts (eventually consistent).

**Skeleton:**

```python
def iter_active_credentials(
    provider_id: str,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
) -> Iterator[tuple[int, Credential]]:
    """Yield (idx, cred) pairs for non-cool-down creds in bucket order.

    Read-only — does NOT acquire the lock. Cool-down map is consulted
    against *now*. Vault path defaults via get_auth_json_path().
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = _now()
    vault = load_vault(vault_path)
    creds = list(vault.providers.get(provider_id, []))
    if not creds:
        return
    seed = vault.last_rotation.get(provider_id, 0)
    n = len(creds)
    start = _bucket_index(now, n, seed)
    for offset in range(n):
        idx = (start + offset) % n
        if not _is_cooled_down(provider_id, idx, now):
            yield idx, creds[idx]
```

### Anti-Patterns to Avoid

- **Per-provider lockfiles** (`auth.json.{provider_id}.lock`). Rejected — Phase 013's per-vault lock is sufficient and per-provider locks are a v3+ optimization. Splitting introduces lock-ordering bugs (deadlock if any caller ever holds two).
- **Module-global `last_rotation` cache without filelock writes.** Tempting (no lock acquire on selection), but breaks cross-process consistency — one daemon's selections aren't visible to another's, defeating P1-8's anti-monopoly defense.
- **Persisting cool-down to `auth.json`.** Bumps schema, pollutes wire shape, survives restarts in surprising ways. Cool-down is a transient runtime concept.
- **`time.time()` reads inside `_pick_active_index` / `_bucket_index`.** Cardinal determinism rule. Tests inject `now`; production uses `now=None` → defaults at the public-API boundary.
- **Returning the credential without the idx.** Caller needs `idx` to call `mark_rate_limited`. Don't return just the cred.
- **Internal retry loop with httpx in `rotation.py`.** Pulls httpx into the rotation module; mixes orchestration with transport. v3 Provider Routing owns the loop.
- **Bumping `last_rotation` outside the lock.** Concurrent bumps from two daemon procs collide; one of them is silently overwritten. Always read-modify-write inside the same `_new_async_lock` window.
- **`_COOL_DOWN.clear()` on module import.** Test isolation pattern only; production code never clears the global. Use a pytest autouse fixture.
- **Race-prone iteration over `_COOL_DOWN`** in `_pick_active_index` (mutation while iterating). The implementation above doesn't iterate the dict; it does individual `dict.get(key)` lookups, which are thread-safe at the single-bucket granularity.
- **`Credential.__eq__` for dedup inside rotation.** Out of scope — Phase 018 handles dedup at login time. Rotation operates on whatever is in the vault.
- **Validating `len(creds) == len(_REGISTRY[provider_id])`.** Provider registry is for plain api_key providers (Phase 018); OAuth providers (014–017) aren't in `_REGISTRY` but still appear in `vault.providers`. Don't couple rotation to the api_key registry.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-process lock | `fcntl.flock` / `multiprocessing.Lock` | Phase 013's `_new_async_lock` (`refresh.py:117-129`) | Already configured with `thread_local=False, timeout=10.0, poll_interval=0.05`; CVE floor pinned. |
| Atomic JSON write | `Path.write_bytes` + `Path.chmod` | `save_vault(path, vault)` (`store.py:252-271`) | TOCTOU-safe atomic write + chmod-0600 + fsync. |
| Path resolution | Hard-coded `~/.state/auth.json` | `get_auth_json_path()` (`store.py:129-139`) | Honors `STATE_AUTH_JSON` env override; matches every other auth module. |
| Vault loading | `orjson.loads(open(...).read())` | `load_vault(path)` (`store.py:226-249`) | chmod-0600 verification + empty-file edge case + Pydantic validation. |
| Mode verification | `os.stat(path).st_mode & 0o777` | implicit via `load_vault` | Already enforced at the read boundary. |
| Credential array shape | Manual `if isinstance(v, list) ...` | Pydantic validator on `AuthVault.providers` (`store.py:100-123`) | Already enforced; `assert all(isinstance(v, list) ...)` in `save_vault` is the second layer. |
| Last-rotation int field | Custom file at `.state/last_rotation.json` | `vault.last_rotation: dict[str, int]` (`store.py:98`) | Already round-trips. STORE-21 covers it. |
| 429 retry logic | Custom retry loop in `rotation.py` | Caller responsibility (v3 Provider Routing) | Keeps rotation pure; no httpx dep. |
| Time-injection plumbing | Re-invent `now: float` parameter | Mirror Phase 013's signature (`refresh.refresh_credential`) | Cardinal determinism rule + tests already use this idiom. |

**Key insight:** The whole module is glue around Phase 012's `last_rotation` field, Phase 013's filelock, and Phase 018's `loader.load_credentials`. Every "convenience" the rotation module exposes (cool-down map, bucket math, NoCredentialsAvailableError) is small enough to inline; everything else is a delegation to existing primitives.

## Common Pitfalls

(Each pitfall is rated P0/P1/P2/P3 per the additional-context request — `P0` = phase-blocker if not handled, `P1` = ship-blocker, `P2` = post-ship hot-fix territory, `P3` = nice-to-have / future audit.)

### Pitfall 1 (P0) — Index drift on concurrent bumps without filelock
**What goes wrong:** Two daemon procs call `select_credential` simultaneously. Both load `vault.last_rotation["openai"] == 3`. Both compute `(3 + 1) % 5 = 4`. Both call `save_vault`. After both commit, `last_rotation == 4` even though *two* selections occurred. Counter is off by one; under sustained load, off by N. Idx 0 becomes the under-served cred (the convoy effect P1-8 warns about) — except now the persisted state lies about it.
**Why it happens:** Read-modify-write without a lock. Standard race condition.
**How to avoid:** **Always** read-modify-write `last_rotation` inside `async with _new_async_lock(vault_path):`. The same lock that `refresh_credential` uses serializes the bump. (Pattern 2.)
**Warning signs:** A property test that runs N concurrent `select_credential` invocations and asserts the post-state `last_rotation` value matches N (mod len). Under no-lock implementation, this test flakes immediately.

### Pitfall 2 (P0) — Reentrant deadlock when called from inside refresh_credential
**What goes wrong:** Daemon middleware acquires the lock for a multi-step transaction (e.g., "select cred, refresh if expired, save"). Calls `select_credential` from inside the held lock. `_new_async_lock` constructs a *new* lock instance; instances are not cross-aware (Phase 013 Pitfall 6 / REFRESH-27). Acquire blocks for 10 s, then raises `RefreshLockTimeout`. Real usage hangs.
**Why it happens:** filelock's `AsyncFileLock` is per-instance, not per-thread/per-task. Two instances pointing at the same path serialize via the kernel's POSIX lock — so even within one process, two instances deadlock.
**How to avoid:** **Document loudly in `rotation.py` module docstring:** "Do NOT call `select_credential` from inside an externally-held `_new_async_lock` block." Provide a `_select_credential_locked(vault: AuthVault, ...)` private helper that takes the already-loaded vault — the daemon middleware uses the locked variant if it needs to compose. Test: REFRESH-27-style test that asserts external-lock + select_credential raises RefreshLockTimeout within 10 s.
**Warning signs:** Tests pass in isolation, daemon hangs in integration.

### Pitfall 3 (P0) — Empty array (`len(creds) == 0`) crashes `_bucket_index`
**What goes wrong:** Caller asks for `select_credential("openai")` but vault has no openai creds AND env synthesis returned `[]`. `_bucket_index` divides by zero (or, in our impl, raises `ValueError`); caller gets a confusing trace.
**Why it happens:** Round-robin only meaningful for `n >= 1`. `n == 0` is a "user hasn't logged in" condition, not a rotation concern.
**How to avoid:** Check `if not creds:` BEFORE entering bucket math; raise dedicated `NoCredentialsAvailableError(provider_id, reason="empty")`. Phase 022 CLI surfaces this as a `state auth login <provider>` prompt.
**Warning signs:** Test ROTATE-02 (empty-bucket → NoCredentialsAvailableError, not ValueError, not IndexError, not KeyError).

### Pitfall 4 (P0) — All credentials cool-down-marked simultaneously
**What goes wrong:** Every cred in the array is currently rate-limited. `_pick_active_index` walks the whole array, never finds an active idx, falls off the loop. Without a guard, returns `None` or raises `IndexError`. Caller sees an opaque crash.
**Why it happens:** All creds hitting 429 in the same minute is plausible (e.g., all share a billing account, or a per-IP rate limit fires). Time-bucketing doesn't save you when every bucket position is cool-down-marked.
**How to avoid:** `_pick_active_index` raises `NoCredentialsAvailableError(provider_id, reason="all_cooled_down")` when the for-loop exhausts without a hit. Caller (v3 Provider Routing) decides whether to wait, escalate, or surface to the user. **Cool-down expiry timestamps stored in `_COOL_DOWN` MUST be human-renderable so the error message can include "earliest cred returns at HH:MM:SS"** — Phase 022 surface concern, but Phase 019 includes the timestamp on the error.
**Warning signs:** Test ROTATE-09 (3-cred vault, all marked cool-down, raises with `reason="all_cooled_down"` and includes earliest expiry).

### Pitfall 5 (P1) — Array shrinks (logout removes a cred) → stale `last_rotation` overflows
**What goes wrong:** Vault was n=5, `last_rotation["openai"] = 4`. User runs `state auth logout openai --idx 3` — array shrinks to n=4. Next selection: `(bucket + 4) % 4 = bucket`, but `creds[4]` doesn't exist. `IndexError` or worse.
**Why it happens:** `last_rotation` isn't updated by Phase 022's logout. Naive use of a stale seed against a smaller array gives an out-of-range index.
**How to avoid:** `_bucket_index` uses `% n` already (the math is safe). The risk is the seed value — and the math saves us: `(bucket + seed) % n` is well-defined for any seed >= 0 and any n > 0. Add a defensive **clamp** anyway: `seed = vault.last_rotation.get(provider_id, 0) % len(creds)` — protects if some downstream code stored a too-large seed. Bonus: Phase 022's logout MAY want to call `clamp_last_rotation(provider_id, vault)` after removing a cred; document this in the rotation module's docstring as a recommended logout-time helper.
**Warning signs:** Test ROTATE-11 (logout shrinks array; seed > new len; selection succeeds via modulo clamp).

### Pitfall 6 (P1) — Stale rate-limit-seen flag persists across daemon restart
**What goes wrong:** User reports "round-robin doesn't pick credential 2 anymore" — but in fact a 429 happened, cool-down was set for 60 s, daemon was killed and restarted within those 60 s; the in-memory map is empty, so cred 2 is selected again. Conversely, the user expected "cool-down survives restart" because they read PITFALLS or the docs.
**Why it happens:** In-memory cool-down is a deliberate v2 design decision (§Pattern 3 rejection of persistence) but its lifetime semantics aren't immediately obvious to users.
**How to avoid:** **Document loudly:** `mark_rate_limited`'s docstring states "in-memory only; daemon restart clears all cool-downs." Phase 022 `state auth status` renders cool-down state with a "(in-memory; survives this daemon process only)" footer. v3 may revisit; v2 is documented and tested.
**Warning signs:** Test ROTATE-15 (cool-down marked; module reload simulated; cool-down empty).

### Pitfall 7 (P1) — Write storm from per-selection persistence under high concurrency
**What goes wrong:** Daemon under sustained load calls `select_credential` 1000×/sec. Each call acquires the filelock, writes 2 KB JSON. 1 ms × 1000 = 1 second of pure write overhead per second of work. Filesystem swamped; latencies climb; user complaints.
**Why it happens:** Persist-on-every-selection is the simple shape; under abnormal load it's a bottleneck.
**How to avoid:** **Phase 019 ships persist-on-every-selection** (simple, correct, predictable). Document as a known v2 limitation. v3 telemetry can add: (a) a process-local in-memory `last_rotation` cache that flushes every K seconds, OR (b) demote `last_rotation` to a separate file with a faster write path. Concrete monitoring: log `rotation.persist_overhead` with the lock-held duration; alert if p99 > 50 ms.
**Warning signs:** Hypothesis-driven concurrent-load test with N=100 callers; fails when p99 lock-held duration > 50 ms.

### Pitfall 8 (P2) — Retry loop exhausts every credential then loops forever
**What goes wrong:** Caller's 429-retry loop calls `select_credential`, gets idx 0, hits 429, marks cool-down, calls again, gets idx 1, hits 429, marks, ... eventually `NoCredentialsAvailableError`. Caller catches it, sleeps, retries — but in the meantime cool-downs auto-expired, so it picks idx 0 again, and goes around the loop. Pathological retry forever.
**Why it happens:** The retry loop is the *caller's* responsibility (Pattern 4); a bad caller can ping-pong. Not Phase 019's bug, but Phase 019 enables the pattern.
**How to avoid:** v3 Provider Routing implementation MUST have a max-retry-budget (e.g., `len(creds)` per request, then escalate). Phase 019's `NoCredentialsAvailableError` includes the next-expiry timestamp so the caller knows how long to wait. Document the recommended caller pattern in the rotation module docstring.
**Warning signs:** Integration test (probably in v3) that asserts the retry loop terminates.

### Pitfall 9 (P2) — Ordering bias on n=2 with one unhealthy credential
**What goes wrong:** Two creds, idx 1 is permanently rate-limited (e.g., quota exhausted for the day). Round-robin always falls back to idx 0; user sees 100% idx-0 usage despite "round-robin." Indistinguishable from the P1-8 monopoly bug at first glance.
**Why it happens:** The skip-cool-down logic is *correct* — there's only one healthy cred, so it gets every selection. But the reporting / observability is misleading.
**How to avoid:** Phase 019 itself doesn't fix this; it's a "round-robin can't fairer than the cred set allows" semantic. Phase 022 / v3 telemetry should surface "credential X is cooled down 100% of the time over the last 1h — consider re-login or quota check." Phase 019 contributes the cool-down-seen counter (could be added as a structlog event on `mark_rate_limited`).
**Warning signs:** User-visible — usage reporting reveals it.

### Pitfall 10 (P2) — last_rotation not preserved when array preserved (asymmetric P1-7)
**What goes wrong:** Phase 021's first-run import preserves `vault.providers[id]` array shape but FORGETS to migrate `last_rotation` (defaults to `{}`). Phase 019 starts every cold-import session with idx 0 monopoly until the first selection bumps the seed.
**Why it happens:** Phase 021 is downstream; `last_rotation` is easy to overlook if the importer thinks "tokens are what matters."
**How to avoid:** Phase 019 contributes a regression test: the round-trip after a Phase 021-style import MUST preserve the array shape AND the `last_rotation` dict (which can be `{}` legitimately). Phase 021 plan-phase research must call this out — Phase 019 gives them the test row to add.
**Warning signs:** Test ROTATE-14 (simulated migration with last_rotation populated; round-trip equality).

### Pitfall 11 (P2) — Schema migration breaking array shape
**What goes wrong:** Some future phase bumps `schema_version: 1 → 2` and the migration helper inadvertently re-introduces a bare-dict provider value. Phase 012's validator coerces it back, but the migration path isn't covered by the rotation tests.
**Why it happens:** Schema migrations are notoriously bug-prone; Phase 019 isn't the migration owner but its tests would catch a regression.
**How to avoid:** Phase 019's hypothesis property test "every credential is selected at least once over N rounds" inherently asserts that the array shape was preserved (a coerced bare-dict would still pass because the validator runs at load time). Add explicit test ROTATE-13: load a vault file containing `{"providers": {"openai": {"key": "...", "type": "api_key", "provider_id": "openai"}}}` (bare dict), assert `select_credential("openai")` returns a single cred at idx 0 without crashing — proves the validator path interoperates with rotation.
**Warning signs:** Schema-migration test fails — the assertion on array shape catches the regression.

### Pitfall 12 (P2) — On-disk last_rotation lag vs. in-memory counter
**What goes wrong:** Pattern 2 persists `last_rotation` on every selection. But what if a daemon caches the value in-memory between calls (a v3 optimization)? Three concurrent procs each cache `last_rotation = 3`; each picks idx 4; only one wins the file write. From the disk's perspective, three calls produced one bump.
**Why it happens:** Read-side caching defeats the persistence guarantee.
**How to avoid:** **Phase 019 does NOT cache `last_rotation` in-memory.** Every selection re-reads the vault under the lock. Document in module docstring: "Implementations downstream MUST NOT cache `last_rotation` between `select_credential` calls — re-read inside the lock." v3 optimization that adds a cache MUST simultaneously add a write coalescer and a cache-coherence test.
**Warning signs:** Hypothesis property test "N concurrent selections produce N bumps" — fails the moment caching is introduced.

### Pitfall 13 (P3) — Bucket boundary jitter
**What goes wrong:** At bucket boundary (e.g., 60_000ms tick), every concurrent caller sees the same new bucket and picks the same idx; refresh-lock convoy returns transiently.
**Why it happens:** Time-bucketing is *deterministic* about which idx the bucket maps to. At the boundary, the determinism that prevents drift also synchronizes callers.
**How to avoid:** The convoy lasts for the duration it takes the lock-held callers to drain (~5 ms each); not a sustained issue. The seed bump (per Pattern 2) shifts the bucket origin between calls so successive calls in the same bucket pick *different* indices via the cool-down-skip walk. Acceptable.
**Warning signs:** Hypothesis property test "every cred is selected at least once over N=20·len(creds) concurrent rounds" — passes, demonstrating the seed bump fairs out.

### Pitfall 14 (P3) — Test isolation: `_COOL_DOWN` module global leaks between tests
**What goes wrong:** Test A marks idx 0 as cool-down. Test B starts; `_COOL_DOWN` still has the entry; test B's selection unexpectedly skips idx 0.
**Why it happens:** Module globals persist across tests in pytest unless explicitly cleared.
**How to avoid:** Add a pytest autouse fixture in `tests/auth/conftest.py` (or `tests/auth/test_rotation.py`):
```python
@pytest.fixture(autouse=True)
def _clear_cool_down() -> None:
    from state_core.auth import rotation
    rotation._COOL_DOWN.clear()
    yield
    rotation._COOL_DOWN.clear()
```
**Warning signs:** Tests pass in isolation, fail in random ordering (`pytest -p no:randomly` passes, `pytest -p randomly` fails).

## Code Examples

### Example 1: Full `select_credential` (canonical implementation outline)

```python
# state_core/auth/rotation.py
from __future__ import annotations

from pathlib import Path
from time import time as _now
from typing import Iterator

import filelock
import structlog

from state_core.auth.base import Credential
from state_core.auth.errors import AuthError
from state_core.auth.refresh import RefreshLockTimeout, _lock_path_for, _new_async_lock
from state_core.auth.store import (
    get_auth_json_path,
    load_vault,
    save_vault,
)

log = structlog.get_logger(__name__)

BUCKET_MS: int = 60_000

# Daemon-process-local — see §Pattern 3.
_COOL_DOWN: dict[tuple[str, int], float] = {}


class NoCredentialsAvailableError(AuthError):
    """No credential is available for *provider_id*.

    Carries:
      - provider_id: which provider has no creds
      - reason: "empty" | "all_cooled_down"
      - earliest_available_at: epoch float | None — only set when reason="all_cooled_down"
    """

    def __init__(
        self,
        provider_id: str,
        *,
        reason: str,
        earliest_available_at: float | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.reason = reason
        self.earliest_available_at = earliest_available_at
        msg = f"No credential available for {provider_id!r} (reason={reason})"
        if earliest_available_at is not None:
            msg += f", earliest at epoch={earliest_available_at}"
        super().__init__(msg)


# (… _bucket_index, mark_rate_limited, clear_rate_limited, _is_cooled_down, _pick_active_index from above …)


async def select_credential(
    provider_id: str,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
) -> tuple[int, Credential]:
    """Select the next credential for *provider_id*; persist last_rotation.

    Returns (idx, credential) — caller uses idx for mark_rate_limited.

    Raises:
        NoCredentialsAvailableError: zero creds or all cool-down-marked
        RefreshLockTimeout: filelock unacquireable in 10 s
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = _now()

    lock = _new_async_lock(vault_path)
    try:
        try:
            async with lock:
                vault = load_vault(vault_path)
                creds = list(vault.providers.get(provider_id, []))
                if not creds:
                    raise NoCredentialsAvailableError(provider_id, reason="empty")
                seed = vault.last_rotation.get(provider_id, 0) % len(creds)
                idx = _pick_active_index(creds, seed, now, provider_id)
                vault.last_rotation[provider_id] = (seed + 1) % len(creds)
                save_vault(vault_path, vault)
                log.debug(
                    "rotation.selected",
                    provider_id=provider_id,
                    idx=idx,
                    seed=seed,
                    n=len(creds),
                )
                return idx, creds[idx]
        except filelock.Timeout as exc:
            raise RefreshLockTimeout(_lock_path_for(vault_path)) from exc
    finally:
        try:
            _lock_path_for(vault_path).touch(exist_ok=True)
        except OSError:
            pass
```

### Example 2: Hypothesis property test — fairness over N rounds

```python
# tests/auth/test_rotation.py
from hypothesis import given, settings
from hypothesis import strategies as st


@settings(max_examples=20, deadline=None)
@given(
    n=st.integers(min_value=2, max_value=8),
    rounds_multiplier=st.integers(min_value=10, max_value=30),
)
async def test_every_cred_selected_over_n_rounds(
    n: int,
    rounds_multiplier: int,
    isolated_vault_path: Path,
) -> None:
    """Property: over N=rounds_multiplier·n selections with no cool-downs,
    every cred index appears at least once.

    This is the load-bearing fairness check that justifies the time-bucketed
    algorithm (PITFALLS.md P1-8). A naive `(last_rotation+1) % n` would also
    pass this test under sequential calls — the harder test (concurrency)
    lives in test_rotation_concurrency.py.
    """
    vault = AuthVault(
        providers={
            "openai": [
                ApiKeyCredential(key=f"key-{i}", provider_id="openai")
                for i in range(n)
            ],
        }
    )
    save_vault(isolated_vault_path, vault)

    seen: set[int] = set()
    base_time = 1_770_000_000.0
    for round_i in range(rounds_multiplier * n):
        # Advance time by 1 minute per round → bucket walks predictably.
        idx, _cred = await select_credential(
            "openai",
            vault_path=isolated_vault_path,
            now=base_time + round_i * 60.0,
        )
        seen.add(idx)

    assert seen == set(range(n)), f"Some creds never selected: missing {set(range(n)) - seen}"
```

### Example 3: 429 fallback flow (caller-side, v3 preview)

```python
# Preview only — NOT in this phase. For documentation in module docstring.
async def _v3_call_with_rotation(provider_id: str, request: Request) -> Response:
    for _attempt in range(_MAX_PROVIDER_RETRIES):
        try:
            idx, cred = await select_credential(provider_id)
        except NoCredentialsAvailableError:
            raise

        cred = await refresh_credential(method_for(cred), provider_id, idx)
        try:
            return await httpx_call(request, headers=method_for(cred).http_headers(cred))
        except HTTP429 as exc:
            until = parse_retry_after(exc) or (time.time() + 60.0)
            mark_rate_limited(provider_id, idx, until=until)
            log.info("rotation.429_fallback", provider_id=provider_id, idx=idx, until=until)
            continue
    raise ProviderUnavailable(provider_id, reason="max_retries")
```

### Example 4: __init__.py re-export edit

```python
# state_core/auth/__init__.py — ADD these lines
from state_core.auth.rotation import (
    NoCredentialsAvailableError,
    clear_rate_limited,
    iter_active_credentials,
    mark_rate_limited,
    select_credential,
)

# Add to __all__:
#     "NoCredentialsAvailableError",
#     "clear_rate_limited",
#     "iter_active_credentials",
#     "mark_rate_limited",
#     "select_credential",
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Naive `(last_rotation + 1) % n` round-robin | Time-bucketed `(now_ms / bucket_ms + last_rotation) % n` with cool-down skip | This phase (per PITFALLS.md P1-8) | Anti-monopoly fairness under refresh-lock contention; cred 0 is no longer privileged on cold start. |
| Synchronous filelock + threads | `filelock.AsyncFileLock` with `thread_local=False` | Phase 013 (already shipped) | Daemon's asyncio event loop integrates cleanly; no `asyncio.to_thread` wrapper. |
| Persist cool-down on disk | In-memory `_COOL_DOWN` dict (module-local) | This phase | No Credential schema bump; restarts forget cool-downs (acceptable per §Pattern 3). |
| Internal retry loop on 429 in the rotation module | Caller-driven (rotation returns one cred + idx) | This phase (per Pattern 4) | Decouples rotation from httpx; v3 Provider Routing owns the retry loop. |
| One lockfile per provider | One `auth.json.lock` per vault | Phase 013 (inherited) | Simpler; per-provider locks is a v3+ optimization that telemetry must justify. |
| `Credential.cool_down_until` field | Module-level `_COOL_DOWN` dict | This phase | Avoids wire-shape churn; AUTH-13 captured-header tests stay valid. |

**Deprecated/outdated:**
- Hand-coded `fcntl.flock` patterns (fragile across libc versions, mac/linux divergence).
- "Pick first non-rate-limited" greedy strategy (degenerates to first-cred monopoly under refresh-lock contention — the P1-8 failure mode).
- Threading-based concurrency for the cool-down map (asyncio + module-local dict + autouse pytest fixture is sufficient for v2; threading.Lock unnecessary because daemon's selection path is single-event-loop).

## Open Questions (RESOLVED)

1. **Is `last_rotation` a counter or a seed for time-bucketed rotation?** This is the load-bearing reconciliation between ROADMAP wording ("rotation index persisted in `last_rotation`") and PITFALLS.md P1-8 ("index into credentials array with `(now_ms // bucket_ms) % len(creds)`"). RESEARCH §Pattern 1 picks **seed for time-bucketed** with `last_rotation` bumped on each selection (so seed advances independently of wall-clock buckets, giving anti-monopoly + restart-resilience). The planner should validate this with the user during plan-phase if there's any doubt — but since `workflow.skip_discuss: true`, the recommendation is to ship time-bucketed with last_rotation as the seed and document the rationale prominently in the module docstring + a Decision Record. **Confidence: HIGH — PITFALLS.md is the authoritative source on the failure modes that drove the requirement.**

2. **Should `select_credential` be async or sync?** RESEARCH recommends **async** (mirror Phase 013's `refresh_credential`). Concrete reason: `_new_async_lock` is the only filelock entry point that doesn't require a sync→async wrapper, and `select_credential` will almost always be called from an async path (daemon middleware, MCP handlers, v3 Provider Routing). Sync would force `asyncio.run` or `to_thread` at every call site. **Confidence: HIGH — same reasoning as Phase 013.**

3. **Should the cool-down map be a module global or a class instance?** Module global is simpler; class instance is more testable. Recommendation: **module global with an autouse pytest fixture for clearing** (mirror `tests/auth/conftest.py`'s `clean_state_auth_json_env` autouse). Class-instance would force every caller to thread through a `Rotator` object reference, which violates the "delegating-orchestration" pattern that loader.py / refresh.py / store.py establish. **Confidence: HIGH.**

4. **Does Phase 019 promote `_new_async_lock` to public API?** Phase 013's `refresh.py` defines it as private. Phase 019 has two viable approaches: (a) promote to `new_async_lock` public, (b) inline the construction. Recommendation: **promote to public**, single source of truth for the `(thread_local=False, poll_interval=0.05, timeout=10.0)` config tuple. Adds one line to `refresh.__all__`. Low-risk edit. **Confidence: HIGH; flag for planner to confirm.**

5. **Should `mark_rate_limited` require `until` or accept a default?** Recommendation: **require** (no default). Forces v3 Provider Routing to think about cool-down duration per provider — Gemini's free-tier 429 has a `Retry-After` header, OpenAI's doesn't, Anthropic's varies. Defaulting to e.g. 60 s would mask provider-specific signal. **Confidence: HIGH.**

6. **Should `iter_active_credentials` acquire the filelock?** Recommendation: **NO — read-only diagnostic**, accepts eventual consistency. Same call shape as Phase 013's `read_credential` minus the lock (read_credential briefly locks for stale-read avoidance, but Phase 022's `state auth status` UI is allowed to lag). Cost: trivial. Benefit: status command runs without contending with daemon's selection loop. **Confidence: MEDIUM — planner can flip if telemetry shows status renders are stale enough to confuse users.**

7. **Should the cool-down map clear on daemon restart be automatic or signal-driven?** Module-level dict `_COOL_DOWN: dict[...] = {}` is automatically empty on import (process start), so no action needed. Restart semantics are "fresh cool-down state every boot" — already the right default. **Confidence: HIGH.**

8. **What happens if a provider entry is removed (logout) between `select_credential` returning idx=3 and the caller calling `mark_rate_limited(provider_id, 3, ...)`?** The cool-down entry exists in `_COOL_DOWN` for an idx that no longer exists. No crash — the entry is harmless until cleared by `_is_cooled_down` auto-expiry. Phase 022's logout MAY want to call `clear_rate_limited(provider_id, idx)` for the removed indices to clean up early. Document. **Confidence: MEDIUM — soft cleanup recommended but not enforced by Phase 019.**

## Validation Architecture

`workflow.nyquist_validation: true` in `.planning/config.json` — this section is REQUIRED.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ + pytest-asyncio 1.3+ (`asyncio_mode = "auto"`) + hypothesis 6.120+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `python3 -m pytest tests/auth/test_rotation.py -x -q` |
| Full suite command | `python3 -m pytest -q` |

### Phase Requirements → Test Map

| Test ID | Behavior | Test Type | Automated Command | File Exists? |
|---------|----------|-----------|-------------------|-------------|
| ROTATE-01 | `select_credential` on n=1 vault returns `(0, cred)` and bumps `last_rotation` to 0 | unit (async) | `pytest tests/auth/test_rotation.py::test_select_n1_returns_idx0_and_bumps -x` | ❌ Wave 0 |
| ROTATE-02 | `select_credential` on empty array raises `NoCredentialsAvailableError(reason="empty")` | unit (async) | `pytest tests/auth/test_rotation.py::test_select_empty_raises -x` | ❌ Wave 0 |
| ROTATE-03 | `select_credential` on missing provider_id raises `NoCredentialsAvailableError(reason="empty")` | unit (async) | `pytest tests/auth/test_rotation.py::test_select_missing_provider_raises -x` | ❌ Wave 0 |
| ROTATE-04 | Time-bucketed selection: bucket changes → idx changes deterministically | unit (async, parametrize over now offsets) | `pytest tests/auth/test_rotation.py::test_bucket_advances_with_time -x` | ❌ Wave 0 |
| ROTATE-05 | `last_rotation` persisted to disk inside the lock — survives reload | unit (async) | `pytest tests/auth/test_rotation.py::test_last_rotation_persisted -x` | ❌ Wave 0 |
| ROTATE-06 | `last_rotation` round-trips after `select_credential` (P1-7 array shape preserved) | unit (async) | `pytest tests/auth/test_rotation.py::test_array_shape_preserved_after_selection -x` | ❌ Wave 0 |
| ROTATE-07 | `mark_rate_limited` causes the next `select_credential` to skip the marked idx | unit (async) | `pytest tests/auth/test_rotation.py::test_cool_down_skipped_on_next_selection -x` | ❌ Wave 0 |
| ROTATE-08 | Cool-down auto-expires when `now > until`; idx becomes selectable again | unit (async) | `pytest tests/auth/test_rotation.py::test_cool_down_auto_expires -x` | ❌ Wave 0 |
| ROTATE-09 | All creds cool-down-marked → `NoCredentialsAvailableError(reason="all_cooled_down", earliest_available_at=...)` | unit (async) | `pytest tests/auth/test_rotation.py::test_all_cooled_down_raises_with_earliest -x` | ❌ Wave 0 |
| ROTATE-10 | `clear_rate_limited` removes the entry; idx becomes selectable in the same `now` | unit (async) | `pytest tests/auth/test_rotation.py::test_clear_rate_limited_removes_entry -x` | ❌ Wave 0 |
| ROTATE-11 | Stale `last_rotation` >= len(creds) (array shrunk) clamps via modulo, no IndexError | unit (async) | `pytest tests/auth/test_rotation.py::test_last_rotation_modulo_clamp -x` | ❌ Wave 0 |
| ROTATE-12 | `mark_rate_limited(until=0)` is equivalent to `clear_rate_limited` (idempotent contract) | unit | `pytest tests/auth/test_rotation.py::test_mark_zero_until_clears -x` | ❌ Wave 0 |
| ROTATE-13 | Bare-dict provider value in raw vault file → coerced to list (P1-7 regression) | unit (async; loads raw JSON) | `pytest tests/auth/test_rotation.py::test_bare_dict_coerced_p1_7 -x` | ❌ Wave 0 |
| ROTATE-14 | Migration round-trip preserves both `providers` array shape AND `last_rotation` | unit (async) | `pytest tests/auth/test_rotation.py::test_migration_preserves_last_rotation -x` | ❌ Wave 0 |
| ROTATE-15 | In-memory cool-down map is cleared on module reimport (proves daemon-restart semantics) | unit | `pytest tests/auth/test_rotation.py::test_cool_down_lost_on_module_reimport -x` | ❌ Wave 0 |
| ROTATE-16 | `iter_active_credentials` yields all creds when none cool-down-marked, in bucket order | unit | `pytest tests/auth/test_rotation.py::test_iter_active_yields_bucket_order -x` | ❌ Wave 0 |
| ROTATE-17 | `iter_active_credentials` skips cool-down-marked entries | unit | `pytest tests/auth/test_rotation.py::test_iter_active_skips_cool_down -x` | ❌ Wave 0 |
| ROTATE-18 | `iter_active_credentials` does NOT acquire the lock (read-only proof) | unit (sync; lock-held in another async task) | `pytest tests/auth/test_rotation.py::test_iter_active_does_not_lock -x` | ❌ Wave 0 |
| ROTATE-19 | `select_credential` raises `RefreshLockTimeout` if lock unacquireable within 10 s (mirrors REFRESH-25) | unit (async; busy-locker fixture) | `pytest tests/auth/test_rotation.py::test_select_lock_timeout_raises -x` | ❌ Wave 0 |
| ROTATE-20 | Reentrant call from inside an externally-held `_new_async_lock` → RefreshLockTimeout (Pitfall 2 / REFRESH-27 pattern) | unit (async) | `pytest tests/auth/test_rotation.py::test_select_reentrant_deadlock_raises -x` | ❌ Wave 0 |
| ROTATE-21 | Mode isolation: `state_core.auth.rotation` does NOT import `state.build.*` or `state.teach.*` | unit (import-graph) | `pytest tests/auth/test_import_graph.py::test_rotation_no_mode_imports -x` | ❌ Wave 0 (extend existing test_import_graph.py) |
| ROTATE-22 | `select_credential` invokes `save_vault` exactly ONCE per call (audit via spy) | unit (async) | `pytest tests/auth/test_rotation.py::test_select_calls_save_vault_once -x` | ❌ Wave 0 |
| ROTATE-23 | Hypothesis property: every cred is selected at least once over N=20·len(creds) rounds with bucket-advancing now | property (async) | `pytest tests/auth/test_rotation.py::test_every_cred_selected_over_n_rounds -x` | ❌ Wave 0 |
| ROTATE-24 | Hypothesis property: `select_credential` post-state vault always satisfies `0 <= last_rotation[id] < len(creds)` | property (async) | `pytest tests/auth/test_rotation.py::test_last_rotation_invariant -x` | ❌ Wave 0 |
| ROTATE-25 | Determinism: `select_credential(provider_id, now=X)` is bit-identical across two runs (no `time.time()` reads internally) | unit (async; assert two calls with same now/vault produce same idx) | `pytest tests/auth/test_rotation.py::test_select_deterministic_for_fixed_now -x` | ❌ Wave 0 |
| ROTATE-26 | Re-export: `from state_core.auth import select_credential, mark_rate_limited, clear_rate_limited, iter_active_credentials, NoCredentialsAvailableError` succeeds | unit | `pytest tests/auth/test_rotation.py::test_public_reexports -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/auth/test_rotation.py -x -q` (target < 5 seconds)
- **Per wave merge:** `python3 -m pytest tests/auth/ -x -q` (full auth subsuite)
- **Phase gate:** `python3 -m pytest -q && mypy src/state_core/auth/` clean before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/auth/test_rotation.py` — covers ROTATE-01..ROTATE-26 (26 stubs, RED at Wave 0; turn GREEN as Wave 2 implementation lands)
- [ ] Extend `tests/auth/conftest.py` — add `_clear_cool_down` autouse fixture; add `isolated_vault_path` fixture if not already present (likely already present from Phase 018)
- [ ] Extend `tests/auth/test_import_graph.py` — add `test_rotation_no_mode_imports` row (matches Phase 011/012/013/018 precedent)
- [ ] No new test framework install — pytest, pytest-asyncio, hypothesis already in `pyproject.toml [project.optional-dependencies] dev`

### Failure Modes Phase 019 MUST Prove It Survives

(consolidated from §Common Pitfalls — every item has a corresponding row above)

1. Empty vault array → `NoCredentialsAvailableError(reason="empty")` (ROTATE-02, P0)
2. Missing provider_id → `NoCredentialsAvailableError(reason="empty")` (ROTATE-03, P0)
3. All creds cool-down-marked → `NoCredentialsAvailableError(reason="all_cooled_down")` with earliest expiry (ROTATE-09, P0)
4. Concurrent `select_credential` calls → `last_rotation` bump count == call count (ROTATE-22 + ROTATE-24 hypothesis property, P0)
5. Reentrant call from held lock → `RefreshLockTimeout` (ROTATE-20, P0)
6. Stale `last_rotation` >= len(creds) → modulo clamp, no IndexError (ROTATE-11, P1)
7. Cool-down auto-expires → idx selectable again (ROTATE-08, P1)
8. Cool-down lost on daemon restart (proven via module reimport) (ROTATE-15, P1)
9. Bare-dict in raw JSON → P1-7 validator coerces; rotation works (ROTATE-13, P1)
10. Migration preserves last_rotation alongside providers (ROTATE-14, P2)
11. Lock unacquireable → `RefreshLockTimeout` (ROTATE-19, P1)
12. Determinism for fixed `now` (ROTATE-25, P1)
13. Mode isolation (ROTATE-21, P1)
14. n=1 graceful degeneration (ROTATE-01, P1)
15. Iteration without lock (ROTATE-18, P2)
16. Re-export surface stable (ROTATE-26, P2)

## Security Threat Inputs (ASVS L1 mapping — for plan-phase `<threat_model>` lift)

- **T-019-1: Index-drift via concurrent unlocked bumps.** Two procs read `last_rotation=3`, both write `4` — one bump silently lost. **Mitigation:** All bumps inside `_new_async_lock`. **Test:** ROTATE-22 + ROTATE-24. ASVS V14.2.5.
- **T-019-2: Reentrant deadlock from caller holding the same vault lock.** **Mitigation:** Document loudly; provide a `_select_credential_locked` private helper for already-locked composition. **Test:** ROTATE-20. ASVS V11.1.7.
- **T-019-3: NoCredentialsAvailableError leaks vault contents.** Exception message could include cred shapes. **Mitigation:** Error message contains only `provider_id` + `reason` + `earliest_available_at` (epoch float). NEVER includes `Credential.key`, `OAuthCredential.access`, or `refresh`. **Test:** assert exception message contains no key prefix substrings. ASVS V8.3.1, V7.4.1.
- **T-019-4: Cool-down map collusion across providers.** A bug where `_COOL_DOWN[("anthropic", 0)]` is consulted for `("openai", 0)` would route Anthropic 429s to OpenAI. **Mitigation:** Tuple key `(provider_id, idx)` with strict equality. **Test:** ROTATE-07 + parametrize over multiple provider_ids. ASVS V1.4.5.
- **T-019-5: Lock-held duration extends beyond intent.** Slow `save_vault` (NFS, full disk) keeps the lock held past the 10s acquire timeout for the next caller, causing storms of `RefreshLockTimeout`. **Mitigation:** Inherited from Phase 013's lock contract; structlog `rotation.persist_overhead` log line lets ops detect. **Test:** No new test (Phase 013 covers via REFRESH-22). Document.
- **T-019-6: Symlink attack on `auth.json`** during the in-lock `save_vault` call. **Mitigation:** Inherited from Phase 012 docstring (Phase 022 audit owns O_NOFOLLOW + lstat). Out of scope. Document.
- **T-019-7: Cross-provider env-var leak via cool-down state.** Hypothetical bug: a typo causes `mark_rate_limited("anthropi", 0, ...)` instead of `"anthropic"` — silently creates dangling state. **Mitigation:** Phase 019 does NOT validate provider_id strings on cool-down operations (would force the rotation module to know the registry, violating loose coupling). Trust the caller. Phase 022 status command surfaces the dangling key visibly. ASVS V14.2.1 (loose coupling > strict validation here).

## Sources

### Primary (HIGH confidence)
- `/Users/tmac/Projects/state/.planning/research/PITFALLS.md` §Surface 5 (P1-7, P1-8, P1-9, P2-5) — the load-bearing source for the algorithm choice and starvation defense
- `/Users/tmac/Projects/state/.planning/milestones/v2/REQUIREMENTS.md` line 16 — AUTH-08 unchecked
- `/Users/tmac/Projects/state/.planning/milestones/v2/ROADMAP.md` line 102–105 — Phase 019 goal text
- `/Users/tmac/Projects/state/.planning/_archived/REQUIREMENTS.md` line 409 — historical AUTH-08 plan-phase reference (M-A2.P9)
- `/Users/tmac/Projects/state/src/state_core/auth/store.py` — `AuthVault.last_rotation` field, `field_validator`, `save_vault` invariant assert
- `/Users/tmac/Projects/state/src/state_core/auth/refresh.py` — `_new_async_lock`, `_lock_path_for`, `RefreshLockTimeout`, `_extract_cred`, the canonical "load → mutate → save under lock" pattern
- `/Users/tmac/Projects/state/src/state_core/auth/loader.py` — `load_credentials(provider_id) -> list[Credential]`, vault-vs-env precedence, log idiom
- `/Users/tmac/Projects/state/src/state_core/auth/base.py` — `Credential`, `AuthMethod` Protocol, frozen Pydantic, secret hygiene rules
- `/Users/tmac/Projects/state/src/state_core/auth/errors.py` — `AuthError` hierarchy, `UnknownApiKeyProviderError` precedent for `NoCredentialsAvailableError`
- `/Users/tmac/Projects/state/src/state_core/auth/__init__.py` — re-export pattern for the public surface
- `/Users/tmac/Projects/state/tests/auth/test_store.py` line 452–469 — `test_last_rotation_round_trip` (STORE-21) confirms the field is already round-tripped
- `/Users/tmac/Projects/state/tests/auth/conftest.py` — `clean_state_auth_json_env` autouse fixture (the pattern to mirror for `_clear_cool_down`)
- `/Users/tmac/Projects/state/.planning/milestones/v2/phases/012-auth-json-vault-chmod-0600/012-RESEARCH.md` — `last_rotation` design intent + array-shape rationale
- `/Users/tmac/Projects/state/.planning/milestones/v2/phases/018-plain-api-key-vault/018-RESEARCH.md` — module-shape precedent + Validation Architecture rendering style
- `/Users/tmac/Projects/state/.planning/PROJECT.md` — cardinal rules (mode isolation, determinism, library locks); STACK.md inherited via reference
- `/Users/tmac/Projects/state/.planning/config.json` — `nyquist_validation: true`, `skip_discuss: true` confirmed

### Secondary (MEDIUM confidence)
- Python `time.time()` documentation (stdlib) — wall-clock semantics
- `filelock` README — `AsyncFileLock(thread_local=False)` semantics, `poll_interval` knob (already verified by Phase 013 RESEARCH)
- POSIX rename(2) atomicity (already established by Phase 012 RESEARCH)
- `pytest-asyncio` `asyncio_mode = "auto"` (existing config)

### Tertiary (LOW confidence — flagged for validation)
- `BUCKET_MS = 60_000` choice — chosen to balance write-traffic against rotation responsiveness; no telemetry yet to confirm. Alternative values 30_000 / 120_000 are equally defensible. The planner can flip during plan-phase if a strong preference emerges.
- 60-second default cool-down for 429 (mentioned in §Pattern 4 preview) — purely advisory; v3 owns the policy.
- "Per-process cool-down survives the daemon's lifetime" UX expectation — anecdotal; user feedback (post-ship) may flip this to persisted state.

## Metadata

**Confidence breakdown:**
- Module placement (`rotation.py` sibling of `loader.py`): **HIGH** — direct mirror of established `state_core.auth.*` orchestration-module pattern
- Public API shape (`select_credential` returning `(idx, cred)`): **HIGH** — caller needs idx for `mark_rate_limited`; alternatives rejected with reasons
- Algorithm choice (time-bucketed with `last_rotation` as seed): **HIGH** — PITFALLS.md P1-8 is authoritative; ROADMAP wording satisfied
- Cool-down representation (in-memory `_COOL_DOWN` dict): **MEDIUM-HIGH** — defensible; persisted-cool-down is a v3 candidate but not v2
- 429 fallback (caller-driven): **HIGH** — mirrors how Phase 013 handles refresh; keeps rotation module pure
- Persistence semantics (write on every selection): **MEDIUM-HIGH** — cost analysis is honest; v3 may add coalescing if telemetry shows real overhead
- Pitfalls catalogue + P0/P1/P2/P3 ratings: **HIGH** — every pitfall mapped to a ROTATE-XX test row
- Validation Architecture: **HIGH** — every behavior has a concrete pytest command
- Open Questions: most rated HIGH; Q6 (`iter_active_credentials` lock) and Q8 (cool-down cleanup on logout) rated MEDIUM and flagged for planner attention

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days — the underlying primitives are all stdlib + already-shipped state_core surface; only PROJECT.md or PITFALLS.md edits would invalidate this research)

## RESEARCH COMPLETE
