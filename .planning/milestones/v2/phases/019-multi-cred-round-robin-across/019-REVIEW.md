---
phase: 019-multi-cred-round-robin-across
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/state_core/auth/rotation.py
  - src/state_core/auth/errors.py
  - src/state_core/auth/refresh.py
  - src/state_core/auth/__init__.py
  - tests/auth/test_rotation.py
  - tests/auth/conftest.py
  - tests/auth/test_import_graph.py
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 019 — Code Review Report

**Reviewed:** 2026-04-30
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found (no MUST-FIX; 2 SHOULD-FIX + 5 WORTH-KNOWING)

## Summary

Phase 019 ships round-robin credential selection across the per-provider
credential array: `state_core.auth.rotation` (398 LOC), the
`NoCredentialsAvailableError` addition to `auth/errors.py`, the public
`new_async_lock` alias in `auth/refresh.py`, and 5 new public re-exports
in `auth/__init__.py`. Coverage is 25 ROTATE rows (ROTATE-01..26 with no
ROTATE-21 in the rotation file — that one lives in `test_import_graph.py`)
plus 2 import-graph guards.

Code quality is high. The 5 RESEARCH design patterns map cleanly onto the
implementation: time-bucketed selection (`_bucket_index`), in-lock
read-modify-write (`_select_credential_locked` + the `async with lock`
wrapper in `select_credential`), transient cool-down map (`_COOL_DOWN`
module global with auto-GC), caller-driven 429 fallback
(`mark_rate_limited` + idempotent `clear_rate_limited`), and the
read-only diagnostic iterator (`iter_active_credentials`). The 14
RESEARCH pitfalls are addressed in code with provenance comments
naming each.

Cardinal-rule compliance is clean:

- **Mode isolation:** rotation.py imports only `state_core.auth.{base,
  store, refresh, errors}` — verified by `test_rotation_imports_only_
  allowed_targets` (allowed set includes a sixth entry `loader` that is
  not actually imported, which is fine — extra slack in the allow-list).
- **Determinism:** every internal helper takes `now: float` as a
  parameter; the only `_now()` reads are at the public-API boundary
  (`select_credential` line 313, `iter_active_credentials` line 378).
  `perf_counter()` is used for log telemetry only (lines 320, 336) and
  does not flow into selection logic.
- **Secret hygiene (T-019-3):** `NoCredentialsAvailableError.__init__`
  composes a message from `provider_id`, `reason`, and the float
  `earliest_available_at` — never references `Credential.key`,
  `OAuthCredential.access`, or `refresh`. ROTATE-09 explicitly asserts
  the rendered string contains no `sk-ant-oat-TEST-` substring.
- **Lock + 0o600 round-trip:** `select_credential` delegates persistence
  to Phase 012's `save_vault`, which preserves chmod 0o600 atomically
  via O_CREAT|O_TRUNC|0o600 + os.fchmod + os.replace. No bypass.
- **Reentrancy contract:** Pitfall 2 / ROTATE-20 documented loudly in
  the module docstring, the `select_credential` docstring, and the
  `_select_credential_locked` seam exists exactly so already-locked
  callers can compose without RefreshLockTimeout.

Two SHOULD-FIX items concern composability hazards already documented but
worth tightening (the `iter_active_credentials` "read-only" claim is not
strictly true; the `_select_credential_locked` private helper is
unreachable through the public surface but its docstring promises future
callers will use it). Five WORTH-KNOWING notes record minor smells. None
block landing; verification is GREEN per 019-04-SUMMARY.md.

## SHOULD-FIX

### SF-01: `iter_active_credentials` documented as "read-only" but mutates `_COOL_DOWN` via `_is_cooled_down`

**File:** `src/state_core/auth/rotation.py:354-389` (function), with the
write-side mutation at line 388 → line 128 (`_is_cooled_down` pops
expired entries).

**Issue:** The docstring on line 362 says `Read-only — does NOT acquire
the lock`. That is true with respect to the *vault file* and the
*filelock*, but the function does mutate the module-global `_COOL_DOWN`
dict every time it is called: `_is_cooled_down` pops any
`(provider_id, idx)` whose `until` has passed. Two consequences:

1. A caller relying on the "read-only" guarantee for iteration safety
   under concurrent access could be surprised — the dict is being
   mutated under them. Python's GIL makes individual `dict.pop` calls
   atomic, so this isn't a data-race CVE, but it does violate the
   documented contract. The Phase 022 `state auth status` command
   (named consumer) calls `iter_active_credentials` from a sync code
   path and may interleave with daemon-side `mark_rate_limited` /
   `select_credential` calls; the GC pop is observable.

2. ROTATE-18 asserts the lock is not acquired (`filelock.FileLock(...)
   .acquire()` in another holder, `iter_active_credentials` proceeds).
   It does NOT assert `_COOL_DOWN` is unmodified — and indeed
   `iter_active_credentials` followed by `_COOL_DOWN.get(...)` could
   return None for a key the caller saw "marked" milliseconds prior.

**Fix:** Two equally valid options:

(a) **Tighten the docstring** to match reality — e.g., "Read-only with
respect to the vault file and the filelock; opportunistically GCs
expired cool-down entries as a side-effect." This is a one-line doc
change, no behavior change.

(b) **Use a non-mutating predicate** (`_is_cooled_down_pure`) for the
iterator's filter, leaving GC exclusively to the `select_credential`
write path:

```python
def _is_cooled_down_pure(provider_id: str, idx: int, now: float) -> bool:
    until = _COOL_DOWN.get((provider_id, idx))
    return until is not None and until > now

# In iter_active_credentials:
if not _is_cooled_down_pure(provider_id, idx, now):
    yield idx, creds[idx]
```

Option (a) is the minimal change. Option (b) is cleaner but adds a
helper. Given this is a single-call-site smell and Phase 022 will
exercise the iterator, option (a) is the recommended fix.

### SF-02: `_select_credential_locked` is unreachable through any public symbol; T-019-2 contract is documentation-only

**File:** `src/state_core/auth/rotation.py:236-270`

**Issue:** The module docstring (rule 5) and `select_credential`'s
docstring (lines 304-308) both direct already-locked callers to invoke
`_select_credential_locked(vault, provider_id, now=now)` directly. But:

1. `_select_credential_locked` has a leading underscore — by Python
   convention it is private. Linters / type-checkers that enforce
   `__all__` (like `ruff`'s `PLE0604` or import-time `__all__` checks)
   would flag external usage.

2. It is NOT in `__all__` (line 392-398) and NOT re-exported at
   `state_core.auth.__init__.py` (line 41-47). The only path to it
   from a v3 caller is `from state_core.auth.rotation import
   _select_credential_locked`, which is precisely the import shape
   that mode-isolation linters flag in other parts of this codebase
   (e.g., REFRESH-23 reload tests).

3. T-019-2 (RESEARCH §Threat Model) names this seam as the structural
   mitigation for reentrant deadlock. If v3 Provider Routing is the
   intended consumer (per RESEARCH §Downstream Consumers), then the
   contract is currently doc-only — there is no test ensuring it is
   importable and callable from a held-lock context.

**Fix:** Either (a) promote to public via a non-underscore name and add
to `__all__`, OR (b) add an explicit comment + a unit test that
exercises the underscored seam from a held-lock context to lock the
contract in place:

```python
# Option (a) — promote to public surface
def select_credential_locked(...) -> tuple[int, Credential]:
    """Public seam for already-locked composition (T-019-2)."""
    ...

__all__ = [
    "BUCKET_MS",
    "clear_rate_limited",
    "iter_active_credentials",
    "mark_rate_limited",
    "select_credential",
    "select_credential_locked",  # NEW
]
```

Option (a) signals to v3 that the contract is honored and gives
import-graph linters a public symbol to whitelist. Option (b) is a
lower-cost variant that documents the underscored seam as
"intentionally private but stable for composition" with a regression
test. Either works; do not leave the contract pure-doc.

## WORTH-KNOWING

### WK-01: `_select_credential_locked` bumps `last_rotation` from the seed, ignoring the actually-picked idx after cool-down skip

**File:** `src/state_core/auth/rotation.py:266-270`

**Issue:** When `_pick_active_index` walks the array to skip cool-down
entries, the returned `idx` may differ from `start = _bucket_index(...)`.
The bump on line 269 is `(seed + 1) % n` — i.e., based on the
*pre-walk seed*, not the post-walk picked idx. Concretely: if seed=0,
n=3, idx 0 is cool-down-marked, the walk returns idx 1. We bump to
seed=1. Next call: seed=1, bucket=B → start=(B+1)%3. If idx 1 is
*still* cool-down-marked, we walk again to idx 2. We bump to seed=2.
Etc.

This is **correct for fairness in steady state** (the seed
monotonically advances mod n regardless of cool-down), but it does
**not record which idx was actually used**. A subtle consequence: under
a single-credential-cooled-down condition, the seed can lap idx 0
multiple times in the wall-clock bucket while idx 1 and 2 split the
load — but those splits are bucket-driven, not seed-driven, so the
fairness property still holds (and ROTATE-23 hypothesis verifies via
"every cred selected over n*k rounds").

**Fix:** No change required. Document the choice with an inline
comment for future maintainers:

```python
# Bump from seed (not idx) so the next caller's bucket origin advances
# regardless of cool-down skip. Cool-down skip is a transient effect;
# fairness comes from seed + bucket monotonicity, not from recording
# the actually-picked idx. ROTATE-23 hypothesis verifies coverage.
vault.last_rotation[provider_id] = (seed + 1) % n
```

The current comment ("Bumped on every selection so successive calls in
the same time bucket fan out via cool-down skip" in module docstring
line 21) gestures at this but is several hundred lines from the
implementation.

### WK-02: `_purge_expired_cool_downs` is O(n) per `_pick_active_index` call; module docstring claims O(1) cool-down lookup

**File:** `src/state_core/auth/rotation.py:133-144` (helper),
`src/state_core/auth/rotation.py:165-167` (call site)

**Issue:** The module docstring (and RESEARCH §Performance) claim O(1)
cool-down lookup. That holds for `_is_cooled_down` (single dict get).
But `_pick_active_index` calls `_purge_expired_cool_downs` first,
which iterates `range(n)` and probes the dict n times — O(n) per
selection. For typical n<10 this is negligible (sub-microsecond), but
it's not the O(1) the docstring suggests.

The GC sweep is necessary for ROTATE-08 ("past cool-down: map is GC'd
even when bucket-aligned start short-circuits the walk on offset 0"),
so removing it would regress test coverage.

**Fix:** No change to behavior. Tighten the perf claim in the module
docstring or in `_pick_active_index`'s docstring to say "O(n) GC
sweep + O(1) lookup per offset; n is typically <10 (number of vendor
credentials)." Optional: a single global LRU / time-ordered structure
would be O(log n) GC but adds complexity for a non-bottleneck.

### WK-03: `_COOL_DOWN` has no global GC ceiling; stale per-provider entries accrete across daemon lifetime

**File:** `src/state_core/auth/rotation.py:89, 133-144`

**Issue:** `_purge_expired_cool_downs` sweeps only the *requested*
provider's range `[0, n)`. If a provider was marked once, its idx
expired, and the daemon never selects from that provider again
(perhaps because the cred was logged-out via Phase 022), the dangling
`(provider_id, idx)` keys are never GC'd until the daemon restarts
(Pitfall 6). RESEARCH §Threat Model T-019-7 acknowledges this
("Phase 022 status command surfaces the dangling key visibly") and
explicitly chose loose coupling over strict provider_id validation.

In practice, with ~12 vendors and a small idx ceiling per vendor, the
upper bound on `_COOL_DOWN` size is ~12 × 5 = 60 entries — not a
memory concern. But under a typo'd `mark_rate_limited("anthropi", ...)`
(T-019-7 example), the dangling entry never expires.

**Fix:** No change required for Phase 019. Phase 022's `state auth
status` command is the documented surface for visibility. If desired,
add a ceiling-driven sweep: when `len(_COOL_DOWN) > 256`, sweep all
expired entries globally. Defer until pathology is observed.

### WK-04: `BUCKET_MS` import in `test_rotation.py` is asserted via `_ = BUCKET_MS` at module scope (line 732)

**File:** `tests/auth/test_rotation.py:732`

**Issue:** The trailing line `_ = BUCKET_MS` is a clever-but-unusual
pattern to force the symbol to be load-bearing during Wave 0 RED. Now
that the rotation module exists and is imported successfully, this
becomes dead code — but removing it would silently regress the import
guarantee. The comment on line 730-731 explains the intent.

**Fix:** No change required. If a future test cleanup pass touches
this file, the line can be replaced with an explicit assertion:

```python
def test_bucket_ms_is_60s() -> None:
    """ROTATE-* — BUCKET_MS is 60_000ms (1 minute)."""
    assert BUCKET_MS == 60_000
```

This makes the load-bearing import a real test rather than a
top-level side-effect.

### WK-05: `mark_rate_limited(until=<negative-or-past-but-non-zero>)` clears via the `until <= 0` branch — surprising for callers passing `now - 60`

**File:** `src/state_core/auth/rotation.py:204-212`

**Issue:** The docstring (line 198-199) says: `until <= 0 clears the
entry`. The implementation matches. But a caller writing
`mark_rate_limited("openai", 0, until=now - 60)` (i.e., a marker that
expired 60s ago) likely INTENDS to register an immediately-expired
marker, not clear an existing one. With the current code, this clears
any existing entry instead.

In practice, RESEARCH §Pattern 4 says callers pass `until = now +
retry_after_seconds`, so the negative case shouldn't arise. But the
contract is asymmetric: `until = 0` (sentinel) and `until = -1`
(presumably also sentinel) and `until = now - 60` (logically "already
expired") all collapse to the same code path.

**Fix:** No change required for correctness. If desired, narrow the
sentinel: `if until == 0:` instead of `if until <= 0:`. Then a
past-`now` `until` would register and immediately auto-expire on the
next `_is_cooled_down` check (which is the natural behavior). This
is a contract clarification, not a bug fix.

```python
# Sentinel-only: until=0 clears; negative or past-now registers and
# auto-expires on the next _is_cooled_down probe.
if until == 0:
    _COOL_DOWN.pop((provider_id, idx), None)
    log.debug(...)
    return
_COOL_DOWN[(provider_id, idx)] = until
log.info(...)
```

ROTATE-12 only tests `until=0` exactly, so this narrowing would not
regress coverage.

---

## Cardinal-Rule Spot Check (all PASS)

| Rule | File | Status |
|---|---|---|
| Mode isolation: no `state.build.*` / `state.teach.*` imports | rotation.py | PASS (line 56-78 + ROTATE-21 import-graph test) |
| Mode isolation: rotation.py imports only allowed targets | rotation.py | PASS (`base, store, refresh, errors`; allow-list also includes `loader` unused — extra slack) |
| Determinism: no `time.time()` reads inside selection logic | rotation.py | PASS (`_now()` only at lines 313, 378 — public-API boundary; `perf_counter` is monotonic for telemetry only) |
| Determinism: `_bucket_index` / `_pick_active_index` / `_select_credential_locked` take `now` as parameter | rotation.py:103, 147, 240 | PASS |
| Secret hygiene: `NoCredentialsAvailableError` carries provider_id + reason + earliest only | errors.py:96-145 | PASS (no `Credential.key` / `OAuthCredential.access` / `refresh` references) |
| Secret hygiene: no log line includes credential bytes | rotation.py:206, 214, 225, 326, 332 | PASS (only `provider_id`, `idx`, `until`, `n`, timing) |
| Lock contract: Pitfall 2 / reentrant deadlock documented | rotation.py:34-38 module docstring + 304-308 select_credential | PASS |
| Lock contract: filelock.Timeout → RefreshLockTimeout translation | rotation.py:339-340 | PASS (matches refresh.py:311-312 pattern) |
| Lockfile re-touch in finally: tolerates OSError | rotation.py:345-348 | PASS (matches refresh.py:317-320) |
| Modulo-clamp on stale `last_rotation` (Pitfall 5) | rotation.py:265 | PASS (`% n` before use) |
| Cool-down auto-GC | rotation.py:118-130 + 133-144 | PASS (in `_is_cooled_down` + `_purge_expired_cool_downs`) |
| Public API in `__all__` | rotation.py:392-398 | PASS (5 symbols) |
| Re-export at `state_core.auth.__init__` | __init__.py:41-47, 86-92 | PASS (`BUCKET_MS, clear_rate_limited, iter_active_credentials, mark_rate_limited, select_credential` + `NoCredentialsAvailableError` from errors) |
| `new_async_lock` public alias | refresh.py:142, refresh.py __all__ | PASS (alias of `_new_async_lock`; documented WARNING about reentry) |
| chmod 0o600 round-trip preserved | (delegated to Phase 012 save_vault) | PASS (inherited; rotation never opens auth.json directly) |

## Security Spot Check (all PASS)

- No hardcoded secrets — module contains no API keys, tokens, refresh
  tokens. Test fixtures use `sk-ant-oat-TEST-N` / `TEST-key-N`
  prefixes (clear test sentinels).
- No `eval()` / `exec()` / `os.system()` / `subprocess` use.
- No SQL / shell injection surfaces (no DB / shell calls).
- No path traversal — vault path is resolved via `get_auth_json_path()`
  (Phase 012 owned, validates via STATE_AUTH_JSON env var).
- No insecure crypto (no crypto in this phase).
- No `dangerouslySetInnerHTML` / XSS surfaces (Python backend module).
- T-019-3 verified: `NoCredentialsAvailableError`'s `__str__` contains
  only `provider_id`, `reason`, optional epoch float — never credential
  bytes. ROTATE-09 asserts this explicitly via `assert "sk-ant-oat-TEST-"
  not in rendered`.
- T-019-4 verified: cool-down map keys are `(provider_id, idx)` tuples
  with strict equality — no cross-provider collusion possible.
- T-019-5 (lock-held duration extends): mitigated via Phase 013's 10s
  acquire timeout (inherited); `rotation.persist_overhead` log line
  (line 332) gives ops visibility.
- T-019-6 (symlink attack on auth.json): inherited from Phase 012;
  Phase 022 audit owns O_NOFOLLOW (out of scope here).
- T-019-7 (cross-provider env-var leak via cool-down typo): documented
  acceptance per RESEARCH; Phase 022 status surfaces the dangling key.

## Concurrency Spot Check (all PASS)

- **Read-modify-write atomicity:** the `load_vault → _select_credential_
  locked → save_vault` sequence (lines 321-325) is wrapped in a single
  `async with lock:` block. T-019-1 (index drift) cannot occur.
- **Busy-wait avoidance:** AsyncFileLock with `poll_interval=0.05`
  inherited from `_new_async_lock` (refresh.py:128) — no spinning.
- **Deadlock avoidance:** Pitfall 2 / ROTATE-20 documented and tested;
  `_select_credential_locked` private seam exists for already-locked
  composition (SHOULD-FIX SF-02 above).
- **Cancellation safety:** `try/finally` on lines 317-348 ensures
  lockfile re-touch runs even on `CancelledError` propagation.
- **Hypothesis property ROTATE-24:** invariant `0 <= last_rotation[id]
  < n` after every select holds across 20 randomized n+seed examples.
- **Hypothesis property ROTATE-23:** every cred selected over `n *
  rounds_multiplier` calls with seed-driven coverage (constant `now`
  to isolate seed advancement from bucket advancement). Documented
  rationale for fixed-`now` choice (Phase 019-03-SUMMARY.md
  Deviations) is sound: at bucket-aligned advances, `idx_k = (B + 2k)
  % n` would fail coverage for even n via gcd(2, n) > 1.

## Performance Spot Check (out-of-scope-for-v1, all observations only)

- Bucket index: `_bucket_index` is pure arithmetic, O(1).
- Cool-down lookup: `_is_cooled_down` is O(1) dict probe.
- Cool-down GC: `_purge_expired_cool_downs` is O(n) per
  `_pick_active_index` call (n = creds-per-provider, typically <10).
  Module docstring O(1) claim is accurate per-lookup but not per-walk.
  WK-02 above.
- No N² over credential list — array is iterated at most once
  per selection (the cool-down skip walk).
- Lock-held duration: typically <1ms (load_vault + dict ops + save_vault
  + fsync). `rotation.persist_overhead` log line gives ops visibility.

## Maintainability Spot Check

- **Public API surface:** 5 symbols in `__all__` — `BUCKET_MS`,
  `clear_rate_limited`, `iter_active_credentials`, `mark_rate_limited`,
  `select_credential`. Plus `NoCredentialsAvailableError` from
  `auth/errors.py`. Re-exported at `state_core.auth` root. Clean.
- **Docstring completeness:** every public function has Args / Raises /
  Returns blocks. The module docstring enumerates the 5 RESEARCH design
  patterns with section refs. Excellent provenance.
- **Test coverage:** 25 tests in test_rotation.py (ROTATE-01..26 less
  ROTATE-21 which lives in test_import_graph.py). VALIDATION matrix
  GREEN per 019-04-SUMMARY. Hypothesis properties cover invariants
  beyond the unit cases.
- **Cross-references:** every cardinal rule, every pitfall, every
  threat-model row is named in code via comments. RESEARCH.md is the
  authoritative source — no doc drift.

## No-Regression Confirmation

Per 019-04-SUMMARY.md verification output:
- `pytest tests/auth/ -q` → all 25 ROTATE rows GREEN (full Phase 019
  matrix), Phase 011-018 baseline preserved.
- VALIDATION.md flipped to compliant; AUTH-08 closure recorded.
- Mode-isolation guards (ROTATE-21, test_rotation_imports_only_
  allowed_targets) GREEN.

---

_Reviewed: 2026-04-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
