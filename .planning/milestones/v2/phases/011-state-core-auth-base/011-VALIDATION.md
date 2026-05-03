---
phase: 011
slug: state-core-auth-base
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
---

# Phase 011 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ with pytest-asyncio 1.3+, hypothesis 6.120+ |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `python3 -m pytest tests/auth/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/auth/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/auth/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/auth/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green + import-graph lint passes
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 011-01-01 | 01 | 1 | BASE-01 | unit | `python3 -m pytest tests/auth/test_base.py -v` | ❌ W0 | ⬜ pending |
| 011-01-02 | 01 | 1 | BASE-02..BASE-11 | unit | `python3 -m pytest tests/auth/test_base.py -v` | ❌ W0 | ⬜ pending |
| 011-01-03 | 01 | 1 | mode-isolation | lint | `python3 -m pytest tests/auth/test_base.py::test_no_mode_imports` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/auth/__init__.py` — package marker
- [ ] `tests/auth/conftest.py` — shared fixtures (frozen now, sample credentials)
- [ ] `tests/auth/test_base.py` — stubs for BASE-01..BASE-11

*pytest infrastructure already installed from v1 work — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | All foundational types have full automated coverage | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
