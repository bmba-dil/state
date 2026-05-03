---
phase: 018-plain-api-key-vault
plan: 04
subsystem: auth
tags: [auth, api-key, wave-3, verification, phase-gate, smoke-test, validation-flip]
dependency_graph:
  requires:
    - 018-01 (Wave 0 RED scaffolding — 32 named test functions across 4 files)
    - 018-02 (Wave 1 GREEN — _REGISTRY + PlainApiKeyAuth + _main argparse surface)
    - 018-03 (Wave 2 GREEN — load_credentials orchestrator with vault > env precedence)
  provides:
    - VALIDATION.md with status=complete, nyquist_compliant=true, wave_0_complete=true
    - 21/21 GREEN row matrix with plan/task IDs filled in
    - Smoke-test evidence that __main__ login persists ApiKeyCredential to chmod-0600 vault
    - AUTH-05 closure ready for /gsd:verify-work and milestone-state.md "Phases complete: 6 / 12" bump
  affects:
    - .planning/milestones/v2/STATE.md (orchestrator will bump completed_phases 5 -> 6)
    - .planning/milestones/v2/ROADMAP.md (orchestrator will flip Phase 018 plans block to [x])
    - Phase 019 (multi-cred round-robin) — next phase per the phase-018 hand-off
tech_stack:
  added:
    - none (verification-only — pytest 8.4 + stdlib only)
  patterns:
    - Phase-gate plan with no production-code changes — exclusively a verification + frontmatter-flip wave
    - Smoke test of __main__ entry point against tmp_path STATE_AUTH_JSON (real argv, real stdin pipe, real os.chmod)
    - Plan/Task ID column in VALIDATION.md per-task verification map (provenance for which plan landed which row)
key_files:
  created:
    - .planning/milestones/v2/phases/018-plain-api-key-vault/018-04-SUMMARY.md (this file)
  modified:
    - .planning/milestones/v2/phases/018-plain-api-key-vault/018-VALIDATION.md (frontmatter flip + plan/task ID column + 11 checkboxes)
key_decisions:
  - Spot-check #5 (`iter_known_prefixes returns sk- prefixes in descending length order globally`) was discovered to be mathematically infeasible given the planner-locked dict order (anthropic.api_key -> openrouter -> openai). This was already documented and accepted in 018-02-SUMMARY decisions §2 — the canonical contract is within-provider longest-first PLUS cross-provider sk-collision resolution via dict ordering, both of which pass. Documenting here as a Rule-1 deviation in the Plan 04 spot-check itself (the check inherited Wave-0-era expectations that were superseded).
  - VALIDATION.md was force-added (`git add -f`) because `.planning/` is repo-gitignored. This matches the established pattern from 010.1-A (commit b549379) and 016-01 (commit 083f2dc).
patterns_established:
  - "Phase-gate plan: verification-only wave that runs the test sweep, smokes the binary, flips the validation contract"
  - "21/21 row matrix with explicit plan/task ID provenance for every assertion"
requirements_completed: [AUTH-05]
metrics:
  duration_minutes: 6
  completed_date: 2026-04-30
  task_count: 1
  file_count: 1 created (this SUMMARY) + 1 modified (VALIDATION.md)
  test_pass_count_quick: 118
  test_pass_count_full_auth: 291
  test_pass_count_repo_minus_auth: 321
  smoke_subcommands_passed: 3
---

# Phase 018 Plan 04: Wave 3 Verification — Phase-Gate Closure for AUTH-05

Wave 3 verifies the cumulative output of Waves 0-2: 21/21 VALIDATION rows
GREEN, no regression anywhere in the repo, the `python -m
state_core.auth.providers.api_key` binary roundtrips through a tmp_path
vault with chmod 0600, and the import-graph one-way edge holds in both
directions. With this gate, `state_core.auth` now offers
`load_credentials(provider_id) -> list[Credential]` for any of the 12
plain-API-key providers — the canonical entry point that v3 Provider
Routing will read.

## Performance

- **Duration:** ~6 min (verification + frontmatter flip + SUMMARY)
- **Started:** 2026-05-01T00:24:00Z
- **Completed:** 2026-05-01T00:29:27Z (approximate; computed from epoch deltas)
- **Tasks:** 1
- **Files modified:** 1 (VALIDATION.md) + 1 created (this SUMMARY)

## Accomplishments

- **291 / 1 skipped** on full `tests/auth/` suite (one Phase 014 skip, pre-existing)
- **321 passed** on `pytest tests/ --ignore=tests/auth` — repo-wide regression sweep clean
- **118 passed** on the targeted Phase-018 quad (`test_api_key.py`,
  `test_loader.py`, `test_main_api_key.py`, `test_import_graph.py`)
- **3 smoke subcommands** (`list`, `login` via stdin pipe, `refresh`)
  pass against a tmp_path-isolated `STATE_AUTH_JSON`; vault chmod 0600
  verified; key absent from `repr(ApiKeyCredential)`
- **Import-graph one-way edge** verified manually: api_key.py has 0
  lines importing from loader; loader.py imports only the 4 allowed
  state_core.* targets (base, errors, providers.api_key, store)

## Task Commits

Each task was committed atomically with `--no-verify` (parallel-executor protocol):

1. **Task 1: Run full Phase 018 verification + dogfooding smoke test** — `7c59cde` (docs)

_Note: This is a verification-only wave. No production code modified;
the only artifact is `018-VALIDATION.md` (frontmatter flip + plan/task
ID column + 11 checkboxes flipped) and this SUMMARY._

## VALIDATION Row Matrix — 21 / 21 GREEN

| # | Behavior under test                                          | Plan/Task            | Status |
|---|--------------------------------------------------------------|----------------------|--------|
| 01 | empty / whitespace key rejected                             | 01-T2 + 02-T2        | PASS   |
| 02 | prefix mismatch warns and stores                            | 01-T2 + 02-T2        | PASS   |
| 03 | unknown provider_id raises UnknownApiKeyProviderError       | 01-T2 + 02-T2        | PASS   |
| 04 | vault non-empty wins over env                               | 01-T3 + 03-T1        | PASS   |
| 05 | vault empty list + env set -> env synthesizes               | 01-T3 + 03-T1        | PASS   |
| 06 | vault file missing + env set -> env synthesizes             | 01-T3 + 03-T1        | PASS   |
| 07 | vault missing + env unset -> empty list                     | 01-T3 + 03-T1        | PASS   |
| 08 | empty-string env var treated as unset (12-factor)           | 01-T3 + 03-T1        | PASS   |
| 09 | append-default repeat login                                 | 01-T3 + 02-T2        | PASS   |
| 10 | --replace truncates to single entry                         | 01-T3 + 02-T2        | PASS   |
| 11 | dedup on identical key string                               | 01-T3 + 02-T2        | PASS   |
| 12 | longest-prefix-first sniff resolves sk- collision           | 01-T2 + 02-T2        | PASS   |
| 13 | http_headers Anthropic uses x-api-key                       | 01-T2 + 02-T2        | PASS   |
| 14 | http_headers Google AI Studio uses x-goog-api-key           | 01-T2 + 02-T2        | PASS   |
| 15 | http_headers all-others use Authorization Bearer (10 IDs)   | 01-T2 + 02-T2        | PASS   |
| 16 | is_expired always False (∀ provider, ∀ now)                 | 01-T2 + 02-T2        | PASS   |
| 17 | refresh(cred) returns cred unchanged                        | 01-T2 + 02-T2        | PASS   |
| 18 | _REGISTRY has all 12 expected provider_ids                  | 01-T2 + 02-T2        | PASS   |
| 19 | argv never contains the key (getpass / stdin only)          | 01-T3 + 02-T2        | PASS   |
| 20 | ApiKeyCredential repr does not leak key (Field repr=False)  | 01-T2 + 02-T2        | PASS   |
| 21 | import-graph: api_key.py does NOT import loader.py          | 01-T3 + 02-T2 + 03-T1 | PASS   |

## Pytest Output (verbatim, tail)

### Step 1 — Quick quad (-x -v):

```
tests/auth/test_import_graph.py::test_api_key_does_not_import_loader PASSED [ 99%]
tests/auth/test_import_graph.py::test_loader_imports_only_allowed_targets PASSED [100%]

============================= 118 passed in 0.12s ==============================
```

### Step 2 — Full auth suite (-q):

```
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 73%]
........................................................................ [ 98%]
...s                                                                     [100%]
291 passed, 1 skipped in 45.16s
```

### Step 3 — Repo-wide minus auth (-q --ignore=tests/auth):

```
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 67%]
........................................................................ [ 89%]
.................................                                        [100%]
321 passed in 15.42s
```

## Smoke-Test Output (verbatim)

### Smoke 1 — `list` subcommand (no I/O, prints all 12 providers):

```
anthropic.api_key       ANTHROPIC_API_KEY       sk-ant-api03-   x-api-key
openrouter              OPENROUTER_API_KEY      sk-or-v1-,sk-or- Authorization
openai                  OPENAI_API_KEY          sk-svcacct-,sk-proj-,sk-None-,sk- Authorization
anyscale                ANYSCALE_API_KEY        esecret_         Authorization
xai                     XAI_API_KEY             xai-             Authorization
groq                    GROQ_API_KEY            gsk_             Authorization
google.ai_studio        GEMINI_API_KEY          (none)           x-goog-api-key
deepseek                DEEPSEEK_API_KEY        (none)           Authorization
together                TOGETHER_API_KEY        (none)           Authorization
mistral                 MISTRAL_API_KEY         (none)           Authorization
cohere                  COHERE_API_KEY          (none)           Authorization
cerebras                CEREBRAS_API_KEY        (none)           Authorization
```

Assertions: 13 lines >= 12, anthropic.api_key + google.ai_studio + x-api-key + x-goog-api-key all present. PASS.

### Smoke 2 — `login openai` via stdin pipe (CI path, tmp_path vault, chmod 0600):

Setup:
```
SMOKE_VAULT=/var/folders/.../tmp.ba97ZFQDin/.state/auth.json
echo "sk-smoke-test-key-not-real-XXXXX" | env STATE_AUTH_JSON="$SMOKE_VAULT" \
    python3 -m state_core.auth.providers.api_key login openai
```

Output:
```
Logged in to openai (1 credential(s) on file).
```

Vault round-trip verification:
```
Mode: 600
OK: smoke login persisted ApiKeyCredential to vault with key not in repr:
ApiKeyCredential(type='api_key', provider_id='openai', extras={})
```

PASS — key not in repr (Phase 011 Field repr=False); chmod 0600 (Phase 012 ASVS V8.3.7); cred.key roundtrips correctly through load_vault.

### Smoke 3 — `refresh openai` is no-op-with-explanation:

```
API key credentials never expire — nothing to refresh for openai.
```

PASS — friendly message printed; matches the regex `never expire|nothing to refresh|no-op|API key`.

## Final 10-Threat Mitigation Status

| ID       | Threat                                       | Layer                            | Status   |
|----------|----------------------------------------------|----------------------------------|----------|
| T-018-1  | --api-key flag leaks key into argv           | argparse: no --api-key flag exists; getpass on TTY / stdin on non-TTY | CLOSED   |
| T-018-2  | UnknownApiKeyProviderError leaks api key     | Error message carries provider_id only; key never passed to ctor      | CLOSED   |
| T-018-3  | Prefix-mismatch log leaks full key           | structlog only logs `observed_prefix=key[:8]`; warn-and-store         | CLOSED   |
| T-018-4  | _REGISTRY drift across vendor prefix changes | Provenance comments above every spec literal (`# captured 2026-04-30 from <url>`) | MITIGATED |
| T-018-5  | Cross-provider env-var leak                  | Loader consults ONLY `_REGISTRY[pid].env_var`; 12 parametrized tests | CLOSED   |
| T-018-6  | Wrong-mode auth.json silent fallback         | AuthVaultPermissionError propagates from store._verify_mode (Phase 012) — loader is pass-through | CLOSED   |
| T-018-7  | Import cycle api_key <-> loader              | One-way edge enforced: api_key.py has 0 loader imports; test_import_graph.py asserts both directions | CLOSED   |
| T-018-8  | Empty-string env treated as set (12-factor)  | `not env_value or not env_value.strip()` -> [] return                | CLOSED   |
| T-018-9  | --replace silently destructive               | --replace is opt-in; default behavior is append + dedup              | CLOSED   |
| T-018-10 | env synthesis silently persists to vault     | Loader does not import any vault-mutation surface; synthesized credential exists only in returned list (ASVS V8.3.7) | CLOSED   |

All HIGH closed; MEDIUM (T-018-4) mitigated via provenance comments + Phase 022 manual revalidation hook; no LOW gaps.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan-level spot-check] Spot-check #5 expected globally-descending sk- prefixes**

- **Found during:** Task 1 Step 7 (CONTEXT.md compliance spot-check)
- **Issue:** Plan 04 Step 7 final spot-check was:
  ```python
  sk_prefixes = [p for p in iter_known_prefixes() if p.startswith('sk-')]
  assert sk_prefixes == sorted(sk_prefixes, key=len, reverse=True)
  ```
  Actual output: `['sk-ant-api03-', 'sk-or-v1-', 'sk-or-', 'sk-svcacct-', 'sk-proj-', 'sk-None-', 'sk-']`. Lengths are 13, 9, 6, 11, 8, 8, 3 — not strictly descending across the whole list (the openrouter group's `sk-or-` is shorter than openai's `sk-svcacct-` which appears later).
- **Root cause:** The plan-level spot-check was inherited from Wave-0-era expectations that were already explicitly superseded by 018-02-SUMMARY Decision §2: "Wave 0 test_sniff_resolves_sk_collision second assertion was relaxed from 'global descending across the registry' to 'within-provider longest-first' — the global form is mathematically infeasible given the planner-locked dict order (anthropic.api_key → openrouter → openai)."
- **Fix:** Documented the deviation here. The canonical sk-collision contract is verified by `test_sniff_resolves_sk_collision` (Step 1 PASS) and the within-provider longest-first invariant holds for all 12 providers (verified by ad-hoc Python assertion run during execution). The 4 other spot-checks all PASS.
- **Files modified:** none (no fix needed; the underlying contract is correct, only the plan-level secondary assertion was outdated).

### Other Deviations

None — Steps 1, 2, 3, 4, 5, 6 executed exactly as the plan specified.

## Quality Gates

`quality.level = "fast"` — sentinel skipped per protocol; no Quality Gates section emitted.

## Issues Encountered

- **Worktree base mismatch:** The branch `worktree-agent-a78fe2d6c3a1b666c`
  was based on `5acaf88` (v1 milestone tip) instead of the expected
  `c06981e` (Phase 018 Plan 03 tip). Per protocol, ran `git reset --hard
  c06981e`. Working tree was clean before reset; no work lost.
- **`.planning/` is repo-gitignored:** VALIDATION.md and SUMMARY.md
  required `git add -f` to stage. This matches the established pattern
  from v1 phases (e.g., `b549379 docs(010.1-gap-closure-A)`) and v2
  Phase 016 (`083f2dc docs(016-01)`). The project's `commit_docs=false`
  config notes planning docs are local-only by default — Phase 018
  follows the same explicit-force-add pattern as the 016/017 phases.

## Hand-off

**AUTH-05 fully satisfied.** Phase 018 ready for `/gsd:verify-work`. The
orchestrator will:

1. Bump `.planning/milestones/v2/STATE.md` `progress.completed_phases`
   from 5 -> 6 and update `last_activity`.
2. Flip `.planning/milestones/v2/ROADMAP.md` Phase 018 plans block to
   `[x]`.
3. Mark requirement `AUTH-05` complete in REQUIREMENTS.md (if present).

**Next phase per STATE.md:** Phase 019 (multi-cred round-robin) — invoke
`/gsd:plan-phase v2.019`.

## Self-Check: PASSED

Files created and verified on disk:
- `.planning/milestones/v2/phases/018-plain-api-key-vault/018-04-SUMMARY.md` — FOUND (this file)
- `.planning/milestones/v2/phases/018-plain-api-key-vault/018-VALIDATION.md` — FOUND (modified, frontmatter flipped)

Commits exist in branch history:
- `7c59cde` (docs(018-04): flip VALIDATION.md to compliant) — FOUND

Test sweep clean:
- `pytest tests/auth/ -q` -> 291 passed, 1 skipped, 0 failed
- `pytest tests/ -q --ignore=tests/auth` -> 321 passed, 0 failed
- Smoke roundtrip: `python -m state_core.auth.providers.api_key {list,login,refresh}` PASS
