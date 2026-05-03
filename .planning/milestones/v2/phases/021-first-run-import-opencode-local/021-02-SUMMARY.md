---
plan: 021-02
phase: 021-first-run-import-opencode-local
status: complete
wave: 2
depends_on: ["021-01"]
completed: 2026-05-01
gap_closure: false
requirements: [AUTH-11]
---

# 021-02 SUMMARY — Wave 2 GREEN: state_core.auth.import_opencode

## Outcome

Wave 2 GREEN flip for AUTH-11 (first-run import from opencode `auth.json`). The new `state_core.auth.import_opencode` module turns every Wave 1 RED test in `tests/auth/test_import_opencode.py` from `ModuleNotFoundError`/`AssertionError` to PASS, and the two mode-isolation tests in `tests/auth/test_import_graph.py` from `Wave 1 RED` `pytest.fail()` to PASS.

The importer is the contractual P1-7 owner: every imported credential is APPENDED to `vault.providers[pid]` (never replaces, never collapses), and the all-or-nothing transactional shape means a single bad opencode entry rolls back the entire import before any disk hit.

## Commits

- `b35a5c8` `feat(021-02): implement state_core.auth.import_opencode (Wave 2 GREEN)`
  - `src/state_core/auth/import_opencode.py` (created, 517 LOC)
  - `tests/auth/test_import_opencode.py` (modified — 3 Rule-1 deviations, see below)
- `e713f2d` `feat(021-02): re-export import_from_opencode from state_core.auth`
  - `src/state_core/auth/__init__.py` (+3 LOC: import + `__all__` entry)

## Key files (created/modified)

- `src/state_core/auth/import_opencode.py` (created, 517 LOC)
- `src/state_core/auth/__init__.py` (modified, +3 LOC)
- `tests/auth/test_import_opencode.py` (modified, 3 Rule-1 deviations documented below)

## Public API delivered

```python
# All async (the importer awaits the EventStore's async append).

async def import_from_opencode(
    *,
    env_content: str | None = None,        # opencode auth.json (in-memory, highest priority)
    existing_vault: AuthVault | None = None, # pre-loaded state vault (test convenience)
    vault_path: Path | None = None,          # save_vault target (defaults to get_auth_json_path)
    store: Any | None = None,                # EventStore — receives auth.imported events
    mirror: Any | None = None,               # SyncEventMirror passthrough
) -> list[Credential]:
    """Returns the credentials newly written to the vault."""

def parse_opencode_auth(
    *,
    env_content: str | None = None,
    raw: bytes | str | None = None,
    existing_vault: AuthVault | None = None,
) -> list[Credential]:
    """Translate opencode JSON -> list[Credential]; filters by existing_vault if provided."""

def discover_opencode_auth_path() -> Path | None:
    """Resolve the opencode auth.json path (POSIX-only). Returns target path
    regardless of whether the file exists; caller decides absence/presence."""
```

Re-exported at `state_core.auth.import_from_opencode` for Plan 03's daemon orchestrator.

## Cardinal rules enforced

- **Array-shape preservation (P1-7):** every imported cred is APPENDED to `candidate_vault.providers[pid]` via `setdefault(pid, []).append(cand)`. The 1/2/5 round-trip property test (IMPORT-18) covers this with hypothesis.
- **All-or-nothing transactional:** translate every entry first, raise on any pydantic ValidationError or unknown type, ONLY then call `save_vault`. IMPORT-22 confirms `auth_json_path.exists() is False` after a failed import.
- **Determinism:** `grep -E "time\.time\(|datetime\.now\(|datetime\.utcnow\(" src/state_core/auth/import_opencode.py` returns 0. AST scan in IMPORT-25 enforces.
- **Mode isolation:** `grep` for `state_build`/`state_teach`/`state.build`/`state.teach` returns 0. `tests/auth/test_import_graph.py::test_import_opencode_imports_only_allowed_modules` enforces an explicit allowlist (stdlib + pydantic + orjson + structlog + state_core.{auth.base, auth.store, auth.providers.api_key, events, schema, sync_mirror}). SF-04 `from src.*` ban also enforced.
- **Secret hygiene:** `_OpencodeApiEntry.key`, `_OpencodeOauthEntry.access`, `_OpencodeOauthEntry.refresh` use `Field(repr=False)`. `AuthImportedData` payload is contractually 3-fielded (provider_id, source, cred_kind) — IMPORT-24 grep-asserts no canary substring leaks.
- **Foreign-data tolerance:** `OSError`/`PermissionError`/`orjson.JSONDecodeError` on opencode's auth.json -> WARN log + return [] (warn-and-continue). The state vault stays untouched.
- **Provenance marker non-clobberable:** `extras["_source"] = "opencode-import"` is written LAST after any `metadata` copy, so an opencode entry with `metadata: {"_source": "totally-not-opencode"}` cannot defeat the marker. IMPORT-14 enforces.

## Verification

- `tests/auth/test_import_opencode.py` — **41 passed** (was: 0 passed, ModuleNotFoundError at collection in Wave 1)
- `tests/auth/test_import_graph.py` — **6 passed** (the 2 Wave-1-RED `pytest.fail("Wave 1 RED ...")` lints now pass against the live module)
- `tests/auth/` (full auth suite) — **364 passed, 1 skipped, 0 failed**
- `tests/test_schema.py` — **103 passed** (no regression from Wave 1 schema additions)
- `tests/` (project-wide, excluding auth) — **357 passed, 0 failed**
- Total run-time: ~47 s (auth) + ~17 s (other) = ~64 s

## Deviations from Plan

### Rule 1 — Auto-fix bugs in Wave 1 RED test wiring

Three deviations from `tests/auth/test_import_opencode.py` were applied during execution. All three are bug-class fixes (Rule 1) that preserve the spirit of every Wave 1 RED stub: the test's intent (RED-by-design until Wave 2 lands) is unchanged, and every test still asserts the originally-intended invariant once the implementation is in place.

**1. Distinct-prefix canary fixture (IMPORT-19 / IMPORT-20)**

- **Found during:** Task 1, first full pytest run.
- **Issue:** `_CANARY_API_KEY` and `_CANARY_API_KEY_2` both began with the literal `sk-TEST-CANARY-`, so their first 12 characters were identical (`sk-TEST-CANA`). Identity-by-prefix (`(provider_id, key[:12])`) deduped them, and the "different prefix -> new array element" branch in IMPORT-19 / IMPORT-20 became unreachable.
- **Fix:** Changed `_CANARY_API_KEY_2` from `"sk-TEST-CANARY-" + "B"*32` to `"sk-2ND-XXXX-TEST-CANARY-" + "B"*32`. First-12 prefix is now `sk-2ND-XXXX-` vs `sk-TEST-CANA` — distinct. The `TEST-CANARY-` substring is preserved (after position 12), so IMPORT-24's grep-style canary leak detector still has a target string if a future regression ever pushes the key into a rendered payload.
- **Files modified:** `tests/auth/test_import_opencode.py` (lines 76–84).
- **Commit:** `b35a5c8`

**2. Async wrapping for sync test bodies (IMPORT-05 / IMPORT-06 / IMPORT-22 / IMPORT-26)**

- **Found during:** Task 1, after async impl fix for IMPORT-23.
- **Issue:** `import_from_opencode` is genuinely async (it must `await store.append(...)` on the Phase 005 `SqliteEventStore`). IMPORT-23 already wrapped its call in `asyncio.run(_run_import_async(...))` and `_run_import_async` did `await import_from_opencode(...)`. But IMPORT-05 / 06 / 22 / 26 originally called `import_from_opencode(...)` synchronously without `await` — the call returned an un-awaited coroutine and the assertions (`result == [] or result is None`, `pytest.raises(Exception)`) all failed. The `# type: ignore[misc]` next to IMPORT-23's `await` hinted the test author intended an async function but forgot the wrapper in 4 sister tests.
- **Fix:** Wrapped each of the 4 sync calls with `asyncio.run(import_from_opencode(...))`. Imported `asyncio` locally inside each test (mirrors the pattern IMPORT-23 already used). The assertions now operate on the awaited result.
- **Files modified:** `tests/auth/test_import_opencode.py` (4 functions).
- **Commit:** `b35a5c8`

**3. Per-test STATE_AUTH_JSON for IMPORT-23**

- **Found during:** Task 1, after fixing deviation 2 — IMPORT-23 began POLLUTING the project's real `.state/auth.json`.
- **Issue:** IMPORT-23 passes `existing_vault=None`, so the importer falls back to `load_vault(get_auth_json_path())`. Without `STATE_AUTH_JSON` set, `get_auth_json_path()` returns `cwd / .state / auth.json` — i.e. the real project vault (the dev box's actual `auth.json`). Two test runs were enough to add canary-shaped api keys to the real `.state/auth.json`. IMPORT-22 by contrast already pinned `STATE_AUTH_JSON` to a tmp path; IMPORT-23 forgot.
- **Fix:** Added the `auth_json_path` fixture (Phase 012's per-test tmp_path-based vault path) and `monkeypatch.setenv("STATE_AUTH_JSON", str(auth_json_path))` to IMPORT-23's signature. The polluted production vault was wiped before the deviation-2 fix's first clean run.
- **Files modified:** `tests/auth/test_import_opencode.py` (test_emits_auth_imported_event_per_credential signature + body).
- **Commit:** `b35a5c8`

### Plan-vs-implementation API shape

The Plan 02 `<action>` block specified `parse_opencode_auth(raw: bytes | str) -> dict[str, dict]` plus a private `_translate_entry(provider_id, entry) -> Credential | None`. The Wave 1 RED test contract (which is the binding spec per the plan's `<scope_note>`: "every CONTEXT.md decision becomes a RED test stub" and "the executor flips the entire file from RED to GREEN once") instead calls `parse_opencode_auth(env_content="...", existing_vault=...)` and expects a `list[Credential]` return. The implementation matches the test contract: `parse_opencode_auth` returns `list[Credential]` (skipping wellknown / OAUTH_DUMMY_KEY, applying field renames, stamping provenance, optionally filtering against `existing_vault`). The plan's `_translate_entry` helper is preserved internally as a private leaf and powers the same translation logic. No semantic deviation from the plan — just a different surface name for the public list-shaped helper.

## Auth gates

None — the importer is read-only against opencode's foreign auth.json and reads no secrets at runtime. No interactive auth flows triggered.

## Self-Check: PASSED

- `[x]` `src/state_core/auth/import_opencode.py` exists (517 LOC, ≥ 250)
- `[x]` `def import_from_opencode` present (1 match)
- `[x]` `def discover_opencode_auth_path` present (1 match)
- `[x]` `def parse_opencode_auth` present (1 match)
- `[x]` `_OPENCODE_OAUTH_DUMMY_KEY: str = "opencode-oauth-dummy-key"` (1 match)
- `[x]` `_PROVENANCE_VALUE: str = "opencode-import"` (1 match)
- `[x]` Determinism grep returns 0 matches
- `[x]` Mode-isolation grep returns 0 matches
- `[x]` `account_id` present (1 match)
- `[x]` `enterprise_url` present (1 match)
- `[x]` `pytest tests/auth/test_import_opencode.py` exits 0 (41 passed)
- `[x]` `pytest tests/auth/test_import_graph.py` exits 0 (6 passed)
- `[x]` `pytest tests/auth/` exits 0 (364 passed, 1 skipped)
- `[x]` `pytest tests/test_schema.py` exits 0 (103 passed)
- `[x]` `pytest tests/` (project-wide ex-auth) exits 0 (357 passed)
- `[x]` `from state_core.auth import import_from_opencode` resolves at the top-level auth package
- `[x]` Existing `state_core.auth` re-exports preserved (no regression)
- `[x]` Commits `b35a5c8` and `e713f2d` exist on branch `gsd/phase-021-first-run-import-opencode-local`

Plan 03 (daemon orchestrator wiring + first-run boot hook) has a clean entry point: `from state_core.auth import import_from_opencode`.
