---
phase: 021
slug: first-run-import-opencode-local
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-02
---

# Phase 021 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> Authored retroactively as part of phase 022.1 gap-closure (`/gsd:validate-phase 021`
> skill was unavailable from a parallel-executor subagent context, so this document
> was hand-authored from `021-VERIFICATION.md` using `011-VALIDATION.md` as the
> structural template). Phase 021 shipped 23/23 must-haves GREEN per the verification
> report; this file simply makes the audit row machine-checkable.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ with pytest-asyncio 1.3+, hypothesis 6.120+ |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `python3 -m pytest tests/auth/test_import_opencode.py tests/auth/test_import_graph.py tests/test_orchestrator_import_opencode.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/auth/ tests/test_orchestrator_import_opencode.py -v` |
| **Estimated runtime** | ~50 seconds (50 targeted tests) |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/auth/test_import_opencode.py tests/auth/test_import_graph.py tests/test_orchestrator_import_opencode.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/auth/ tests/test_orchestrator_import_opencode.py -v`
- **Before `/gsd:verify-work`:** Full auth suite green + import-graph mode-isolation lint passes + determinism grep returns 0 matches + AUTH-11 flipped to `[x]` in REQUIREMENTS.md
- **Max feedback latency:** ~10 seconds for the targeted 50-test slice

---

## Per-Task Verification Map

| Task ID    | Plan   | Wave | Requirement | Test Type      | Automated Command                                                                                              | File Exists | Status   |
|------------|--------|------|-------------|----------------|----------------------------------------------------------------------------------------------------------------|-------------|----------|
| 021-01-01  | 021-01 | 1    | AUTH-11     | unit (schema)  | `python3 -m pytest tests/test_schema.py -v -k auth_imported`                                                   | ✅          | ✅ green |
| 021-01-02  | 021-01 | 1    | AUTH-11     | unit (RED)     | `python3 -m pytest tests/auth/test_import_opencode.py --collect-only`                                          | ✅          | ✅ green |
| 021-01-03  | 021-01 | 1    | mode-iso    | lint           | `python3 -m pytest tests/auth/test_import_graph.py -v`                                                         | ✅          | ✅ green |
| 021-02-01  | 021-02 | 2    | AUTH-11     | unit (GREEN)   | `python3 -m pytest tests/auth/test_import_opencode.py -v`                                                      | ✅          | ✅ green |
| 021-02-02  | 021-02 | 2    | AUTH-11     | property       | `python3 -m pytest tests/auth/test_import_opencode.py -v -k IMPORT_18`                                         | ✅          | ✅ green |
| 021-02-03  | 021-02 | 2    | mode-iso    | lint (re-run)  | `python3 -m pytest tests/auth/test_import_graph.py -v`                                                         | ✅          | ✅ green |
| 021-03-01  | 021-03 | 3    | AUTH-11     | integration    | `python3 -m pytest tests/test_orchestrator_import_opencode.py -v`                                              | ✅          | ✅ green |
| 021-03-02  | 021-03 | 3    | AUTH-11     | grep contract  | `grep -c "from state_core.auth import import_from_opencode" src/state_daemon/orchestrator.py` (expect 1)       | ✅          | ✅ green |
| 021-03-03  | 021-03 | 3    | AUTH-11     | doc closure    | `grep -c '^\- \[x\] \*\*AUTH-11\*\*' .planning/milestones/v2/REQUIREMENTS.md` (expect 1)                       | ✅          | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/auth/__init__.py` — package marker (exists from Phase 011)
- [x] `tests/auth/conftest.py` — shared fixtures incl. `auth_json_path` for per-test `STATE_AUTH_JSON` isolation (exists from Phase 012)
- [x] `tests/auth/test_import_opencode.py` — 631 LOC, 26 test functions covering IMPORT-01..IMPORT-26 (RED in 021-01, GREEN in 021-02)
- [x] `tests/auth/test_import_graph.py` — 2 new mode-isolation lint functions added in 021-01 (`test_import_opencode_no_mode_imports`, `test_import_opencode_imports_only_allowed_modules`)
- [x] `tests/test_orchestrator_import_opencode.py` — 178 LOC, 3 integration tests for boot ordering / failure handling / store+mirror plumbing (created in 021-03)

*pytest infrastructure already installed from v1 work — no framework install needed.*

---

## Manual-Only Verifications

| Behavior                                         | Requirement | Why Manual                                                       | Test Instructions                                              |
|--------------------------------------------------|-------------|------------------------------------------------------------------|----------------------------------------------------------------|
| (none)                                           | —           | All 23 must-haves have automated verification per 021-VERIFICATION.md | —                                                              |

*Phase 021 is daemon-internal only; user-facing UX surfacing of `extras["_source"] = "opencode-import"` is a Phase 022 deliverable and is validated there.*

---

## Must-Haves Rollup (from 021-VERIFICATION.md)

| Category                         | Count | Source Plan(s)                  | Status     |
|----------------------------------|-------|---------------------------------|------------|
| Schema additions                 | 2     | 021-01                          | ✓ VERIFIED |
| RED scaffold + canary discipline | 1     | 021-01                          | ✓ VERIFIED |
| Mode-isolation lints             | 1     | 021-01, 021-02                  | ✓ VERIFIED |
| Importer module surface          | 5     | 021-02                          | ✓ VERIFIED |
| Provenance + skip rules          | 4     | 021-02                          | ✓ VERIFIED |
| Translation rules                | 2     | 021-02                          | ✓ VERIFIED |
| P1-7 array-shape preservation    | 1     | 021-02                          | ✓ VERIFIED |
| Transactional all-or-nothing     | 1     | 021-02                          | ✓ VERIFIED |
| Foreign-data tolerance           | 1     | 021-02                          | ✓ VERIFIED |
| Audit event dual-write           | 1     | 021-02                          | ✓ VERIFIED |
| Determinism rule                 | 1     | 021-02, 021-03                  | ✓ VERIFIED |
| Mode isolation grep              | 1     | 021-02, 021-03                  | ✓ VERIFIED |
| Re-export at package level       | 1     | 021-02                          | ✓ VERIFIED |
| Daemon boot ordering             | 1     | 021-03                          | ✓ VERIFIED |
| Importer-failure non-fatal       | 1     | 021-03                          | ✓ VERIFIED |
| Store+mirror plumbing            | 1     | 021-03                          | ✓ VERIFIED |
| Integration tests                | 1     | 021-03                          | ✓ VERIFIED |
| AUTH-11 closure marker           | 1     | 021-03                          | ✓ VERIFIED |
| **Total**                        | **23**| **021-01 + 021-02 + 021-03**    | **23/23**  |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — all test files exist)
- [x] No watch-mode flags
- [x] Feedback latency < 10s for the targeted 50-test slice
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete (post-hoc; 50/50 targeted tests GREEN per 021-03-SUMMARY.md verification table; AUTH-11 flipped to `[x]` in `.planning/milestones/v2/REQUIREMENTS.md`).
