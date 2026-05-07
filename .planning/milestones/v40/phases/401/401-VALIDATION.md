---
phase: 401
slug: 401-artifact-catalog-naming-layout-cross-refs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-07
---

# Phase 401 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

This phase produces architecture specification documents only — no code to test. Validation is by manual review and cross-reference audit.

| Property | Value |
|----------|-------|
| **Framework** | N/A — architecture documents phase |
| **Config file** | N/A |
| **Quick run command** | `python3 -c "import json, os; print('Validation by spec audit')"` |
| **Full suite command** | Manual review of all spec docs against requirements |
| **Estimated runtime** | ~N/A seconds |

---

## Sampling Rate

- **After every task commit:** Manual review of produced spec document against its requirement
- **After every plan wave:** Cross-reference audit between wave artifacts and upstream Phase 400 specs
- **Before `/gsd-verify-work`:** All 17 requirements (ART-01..05, DSK-01..06, REF-01..06) matched to spec documents
- **Max feedback latency:** N/A (human review cycle)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 401-01-01 | 01 | 1 | ART-01..05 | N/A | Artifact catalog documents all file types correctly | manual-review | `grep -l "purpose\|tier\|schema_ownership" *.md` | ⬜ W0 | ⬜ pending |
| 401-02-01 | 02 | 2 | DSK-01..06 | N/A | Directory tree matches naming conventions and index.json schema | manual-review | `python3 -c "import json; ..."` | ⬜ W0 | ⬜ pending |
| 401-03-01 | 03 | 3 | REF-01..06 | N/A | W-codes assigned correctly and validate_consistency() blocks daemon start on ERROR | manual-review | `python3 -c "..."` | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] No test infrastructure needed — this is an architecture specification phase
- [ ] Spec documents self-validate through cross-reference consistency checks built into Plan 3 (REF)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Artifact catalog completeness | ART-01..05 | Document design review — no runtime behavior to test | Verify every artifact type in catalog has purpose, tier, schema ownership, creation/update triggers, and file format fields populated |
| Directory tree correctness | DSK-01..06 | Specification audit — no code to execute | Walk `.state/build/` directory tree spec and verify all naming conventions, concurrent access rules, and index.json registry rules are specified |
| Cross-reference integrity | REF-01..06 | Design constraint verification — no runtime behavior | Verify all 15 W-codes are defined, each with severity, trigger condition, and resolution path. Verify validate_consistency() function spec covers ERROR-detect on daemon startup |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < {N}s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
