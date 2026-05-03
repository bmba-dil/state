---
phase: 021-first-run-import-opencode-local
verified: 2026-05-01T00:00:00Z
status: passed
score: 16/16 must-haves verified
---

# Phase 021: First-run Import from Opencode — Verification Report

**Phase Goal:** Detect + import opencode's auth.json into `.state/auth.json`, preserving array shape (P1-7 defence). Owns the opencode-source migration path + the daemon-start hook that calls it.
**Verified:** 2026-05-01T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (consolidated across 3 plans)

| #   | Truth                                                                                                                                            | Status     | Evidence                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Schema declares `state.auth.imported` event type, `AuthImportedData`, `AuthImportedEvent`, extends `AuthEvent` union                             | ✓ VERIFIED | schema.py:89-92 (AUTH_EVENT_TYPES), :349 (AuthImportedData), :579 (AuthImportedEvent), :633 (AuthEvent union); discriminated-union check passes |
| 2   | `AuthImportedData` has exactly 3 fields (provider_id, source, cred_kind) — NO secret bytes                                                       | ✓ VERIFIED | `model_fields == {'provider_id','cred_kind','source'}`; `extra='forbid'` + `frozen=True` enforced (live ValidationError on both)                |
| 3   | RED scaffold exists with full coverage; module-level import of `state_core.auth.import_opencode` flipped GREEN in Wave 2                         | ✓ VERIFIED | tests/auth/test_import_opencode.py 631 LOC, 26 test functions; pytest 41 passed (Wave 2 baseline)                                               |
| 4   | Mode-isolation lints in tests/auth/test_import_graph.py assert importer imports only stdlib + pydantic + orjson + structlog + state_core sibling | ✓ VERIFIED | test_import_graph.py:154,184 (both functions present); 6 tests passing                                                                          |
| 5   | `import_from_opencode()` reads opencode auth.json, translates entries, single transactional save_vault                                           | ✓ VERIFIED | import_opencode.py:386-509 — `save_vault(target_path, candidate_vault)` called exactly once after all validation                                |
| 6   | Provenance marker `extras["_source"] = "opencode-import"` present on every imported credential                                                   | ✓ VERIFIED | import_opencode.py:230 (api branch), :245 (oauth branch) — assignment is LAST after metadata copy (clobber-resistant)                           |
| 7   | OAUTH_DUMMY_KEY (`opencode-oauth-dummy-key`) detected and skipped                                                                                | ✓ VERIFIED | import_opencode.py:68 constant; :220-225 skip + DEBUG log                                                                                       |
| 8   | Wellknown entries skipped with INFO log                                                                                                          | ✓ VERIFIED | import_opencode.py:208-216                                                                                                                      |
| 9   | Type discriminator translation: opencode `api` → state `api_key`; `oauth` → `oauth`; `wellknown` → skipped                                       | ✓ VERIFIED | import_opencode.py:218 (api branch returns ApiKeyCredential), :237 (oauth branch returns OAuthCredential)                                       |
| 10  | Field renames: accountId → account_id, enterpriseUrl → extras["enterprise_url"], metadata → extras                                               | ✓ VERIFIED | import_opencode.py:250 `account_id=oauth.accountId`; :244 `extras["enterprise_url"]=oauth.enterpriseUrl`; :229 `dict(api.metadata)`             |
| 11  | Identity by (provider_id, access_or_key[:12]) — append-only, never mutates state-side creds                                                      | ✓ VERIFIED | import_opencode.py:259-262 `_identity()`; :487-495 append-only loop with identity check                                                         |
| 12  | Array-shape preservation (P1-7) — `setdefault(pid, []).append(cand)`                                                                             | ✓ VERIFIED | import_opencode.py:494; hypothesis property test in test_import_opencode.py covers 1/2/5 perms (50/50 GREEN)                                    |
| 13  | All-or-nothing transactional: any ValidationError aborts before save_vault                                                                       | ✓ VERIFIED | import_opencode.py:454-471; ValueError/ValidationError propagate up before line 502 save_vault call                                             |
| 14  | Foreign-data tolerance: corrupt/missing opencode auth.json → WARN/DEBUG + continue                                                               | ✓ VERIFIED | import_opencode.py:425-436 (absent), :437-445 (PermissionError/OSError), :458-462 (JSONDecodeError); all return [] without raising              |
| 15  | Emits one `state.auth.imported` event per cred (dual-write to events.sqlite + SyncEvent)                                                         | ✓ VERIFIED | import_opencode.py:355-383 `_emit_imported_event` builds AuthImportedData and calls `store.append(... mirror=mirror)`                           |
| 16  | Determinism rule honored: zero `time.time()` / `datetime.now()` / `datetime.utcnow()` in importer or orchestrator                                | ✓ VERIFIED | grep over both files returns 0 matches                                                                                                          |
| 17  | Mode isolation honored: zero state_build/state_teach imports                                                                                     | ✓ VERIFIED | grep returns 0 matches; allowlist test in test_import_graph.py also enforces                                                                    |
| 18  | `import_from_opencode` re-exported at `state_core.auth` package level                                                                            | ✓ VERIFIED | __init__.py:31 import + :88 `__all__` entry; runtime check resolves to `state_core.auth.import_opencode`                                        |
| 19  | Daemon orchestrator boot order: install → assert_redactor_attached → import_from_opencode → run_repair_now → migrate → reconciler                | ✓ VERIFIED | orchestrator.py:48-86; runtime index check (docstring-stripped) confirms install < assert < importer < repair                                   |
| 20  | Importer failure non-fatal — wrapped in try/except, logged via WARN, daemon continues                                                            | ✓ VERIFIED | orchestrator.py:58-69 `try/except Exception` with `daemon.startup.importer_failed` WARN; `error_type` only (no repr/args/str)                   |
| 21  | Importer awaited and receives store + mirror kwargs                                                                                              | ✓ VERIFIED | orchestrator.py:59 `await import_from_opencode(store=store, mirror=mirror)`; reconciler reuses the same instances (orchestrator.py:85)          |
| 22  | Three orchestrator integration tests pass (boot ordering, failure handling, store/mirror plumbing)                                               | ✓ VERIFIED | tests/test_orchestrator_import_opencode.py:27,98,142 — all 3 GREEN                                                                              |
| 23  | REQUIREMENTS.md AUTH-11 flipped from [ ] to [x]                                                                                                  | ✓ VERIFIED | REQUIREMENTS.md:19 — `- [x] **AUTH-11**: First-run import from opencode's existing auth store when detected`                                    |

**Score:** 23/23 truths verified (consolidated from 16 plan-level must_have categories)

### Required Artifacts

| Artifact                                                | Expected                                                            | Status     | Details                                                                                                              |
| ------------------------------------------------------- | ------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/schema.py`                              | AuthImportedData + AuthImportedEvent + extended AUTH_EVENT_TYPES + AuthEvent union | ✓ VERIFIED | All 4 anchors present; live discriminated-union resolution check passes                                              |
| `src/state_core/auth/import_opencode.py`                | import_from_opencode + discover_opencode_auth_path + parse_opencode_auth + private models | ✓ VERIFIED | 517 LOC (≥250 plan minimum); all 3 public functions present; private _OpencodeApiEntry/_OpencodeOauthEntry/_OpencodeWellKnownEntry present |
| `src/state_core/auth/__init__.py`                       | Re-exports import_from_opencode for daemon orchestrator             | ✓ VERIFIED | import line + `__all__` entry; runtime resolution confirmed                                                          |
| `src/state_daemon/orchestrator.py`                      | Step 0.5 — await import_from_opencode wrapped in try/except         | ✓ VERIFIED | 88 LOC; import line :7, call site :59, defensive WARN :64-69                                                         |
| `tests/auth/test_import_opencode.py`                    | ≥350 LOC RED→GREEN; ≥22 test functions; canary discipline           | ✓ VERIFIED | 631 LOC; 26 test functions; 41 tests passing in pytest run                                                            |
| `tests/auth/test_import_graph.py`                       | Mode-isolation lints for state_core.auth.import_opencode            | ✓ VERIFIED | 2 new functions added (no_mode_imports + imports_only_allowed_modules); 6 tests passing                              |
| `tests/test_orchestrator_import_opencode.py`            | 3 integration tests (boot ordering, failure, store/mirror plumbing) | ✓ VERIFIED | 178 LOC (≥100); 3 async test functions; all 3 GREEN                                                                  |
| `.planning/milestones/v2/REQUIREMENTS.md`               | AUTH-11 closure marker                                              | ✓ VERIFIED | Line 19 flipped to `[x]`                                                                                              |

### Key Link Verification

| From                                          | To                                              | Via                                                              | Status   | Details                                                                                  |
| --------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------- |
| import_opencode.py                            | state_core.auth.store                           | `from state_core.auth.store import AuthVault, ..., save_vault` | ✓ WIRED  | import_opencode.py:57-62; load_vault@:476, save_vault@:502, get_auth_json_path@:474       |
| import_opencode.py                            | state_core.auth.base                            | `from state_core.auth.base import ApiKeyCredential, ...`         | ✓ WIRED  | import_opencode.py:51-55; constructors used at :231 (ApiKey) and :246 (OAuth)             |
| import_opencode.py                            | state_core.schema                               | `from state_core.schema import AuthImportedData`                 | ✓ WIRED  | import_opencode.py:63; instantiated at :366                                              |
| import_opencode.py                            | EventStore.append (Phase 005)                   | `store.append(... event_type="state.auth.imported", ...)`        | ✓ WIRED  | _emit_imported_event @ :370-376; awaited if coroutine                                    |
| import_opencode.py                            | SyncEventMirror                                 | `mirror=mirror` kwarg threaded through                           | ✓ WIRED  | parameter at :392, passed at :375; orchestrator passes mirror_inst                       |
| orchestrator.py                               | state_core.auth.import_from_opencode            | `await import_from_opencode(store=store, mirror=mirror)`         | ✓ WIRED  | orchestrator.py:7 (import) + :59 (await call); both verified at runtime                  |
| orchestrator.py                               | state_core.observability.assert_redactor_attached | ordering invariant: install + assert before importer call       | ✓ WIRED  | Static index check: install=283 < assert=297 < importer=710 < repair=1306 (docstring-stripped) |
| tests/test_orchestrator_import_opencode.py    | state_daemon.orchestrator.startup               | `from state_daemon.orchestrator import startup` + mock.patch     | ✓ WIRED  | All 3 tests pass; parent.mock_calls captures install < assert < importer < repair         |
| tests/auth/test_import_opencode.py            | state_core.auth.import_opencode                  | `from state_core.auth.import_opencode import ...`               | ✓ WIRED  | Module-level import collects cleanly post-Wave-2; 41 tests passing                       |
| AuthEvent union                               | AuthImportedEvent                                | discriminated-union membership                                   | ✓ WIRED  | get_args(get_args(AuthEvent)[0]) contains AuthImportedEvent (live runtime check)          |

### Requirements Coverage

| Requirement | Source Plan(s)             | Description                                                                | Status      | Evidence                                                                                                       |
| ----------- | -------------------------- | -------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------- |
| AUTH-11     | 021-01, 021-02, 021-03     | First-run import from opencode's existing auth store when detected         | ✓ SATISFIED | All 3 waves complete: schema (Wave 1), importer module (Wave 2), daemon hook (Wave 3); REQUIREMENTS.md flipped to `[x]`; 50/50 targeted tests GREEN |

No orphaned requirement IDs — AUTH-11 is the only ID claimed by ROADMAP for this phase, declared in all three plans, and accounted for end-to-end.

### Anti-Patterns Found

Scan over `src/state_core/auth/import_opencode.py`, `src/state_daemon/orchestrator.py`, `src/state_core/schema.py`, `src/state_core/auth/__init__.py`, `tests/auth/test_import_opencode.py`, `tests/auth/test_import_graph.py`, `tests/test_orchestrator_import_opencode.py`:

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none)| —   | —       | —        | TODO/FIXME/XXX/HACK/PLACEHOLDER grep returns 0 matches across all 7 files                                          |

Code-review report (`021-REVIEW.md`) flagged 0 critical / 3 warning / 5 info findings. Per verifier notes, warnings are non-blocking unless they violate must-haves. Cross-checking:

- **WR-01** (orchestrator passes `list[Credential]` to `count=` log key): does NOT block any must_have truth. The `if imported_count:` truthiness works for both list and int. The Phase 020 redactor is a second defense layer if `Credential.__repr__` ever changed. Logged as future hygiene.
- **WR-02** (`auth.import.unreadable` path field omission on JSONDecodeError branch): does NOT block must_have #14 (foreign-data tolerance) — the WARN is still emitted and the function still returns []. Operator-experience polish.
- **WR-03** (AST determinism scan in test has nested-attribute false-negative): does NOT block must_have #16 — primary determinism enforcement is the static grep at `grep -E "time\.time\(|datetime\.now\(|datetime\.utcnow\("` which the verifier ran live (0 matches). The AST scan is a belt-and-suspenders backup.

Recommendation: address WR-01..WR-03 in a Phase 022 cleanup or as targeted debt; none are blocker-class for AUTH-11 closure.

## Step 7b: Quality Findings

Skipped (quality.level: fast)

### Human Verification Required

None — automated checks fully cover Phase 021's deliverables. Phase 022 (CLI) will surface the `extras["_source"] = "opencode-import"` provenance to end-users; user-facing UX testing happens there.

### Gaps Summary

No gaps. Phase 021 fully achieves its goal:

- Opencode's `auth.json` is detected via the documented resolution chain (STATE_OPENCODE_AUTH_PATH → XDG_DATA_HOME → platform default).
- Each entry is translated into state's `Credential` schema (api → api_key, oauth → oauth, wellknown skipped, OAUTH_DUMMY_KEY skipped, camelCase → snake_case).
- Array shape is preserved (P1-7 defended via append-only diff loop and hypothesis property test).
- The whole import is all-or-nothing transactional (single `save_vault` call after full validation).
- One `state.auth.imported` event is dual-written per imported credential (events.sqlite + SyncEvent mirror).
- The daemon orchestrator awaits the importer between redactor self-check and store-driven steps; failure is non-fatal.
- Determinism, mode isolation, and secret-hygiene cardinal rules are all honored (live grep + tests).
- AUTH-11 marker flipped to `[x]` in REQUIREMENTS.md.

50/50 targeted tests pass (41 in test_import_opencode.py + 6 in test_import_graph.py + 3 in test_orchestrator_import_opencode.py). No regression in the 367-test auth suite or 357-test non-auth suite per executor notes.

---

_Verified: 2026-05-01T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
