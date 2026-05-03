---
phase: 012
slug: auth-json-vault-chmod-0600
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
---

# Phase 012 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ with pytest-asyncio + tmp_path fixtures |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `.venv/bin/python -m pytest tests/auth/test_store.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/auth/ -v` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full auth suite
- **Before /gsd:verify-work:** Full suite + permissions audit (`stat -f "%Lp"` on test fixtures)
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 012-01-* | 01 | 1 | VAULT-01..VAULT-21 | unit | `.venv/bin/python -m pytest tests/auth/test_store.py -v` | ❌ W0 | ⬜ pending |
| 012-02-* | 02 | 2 | AUTH-06, P0-13 | unit | `.venv/bin/python -m pytest tests/auth/test_store.py -v` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/auth/test_store.py` — RED stubs for VAULT-01..VAULT-21 (atomic write, mode verification, array-shape, P0-13 regression)
- [ ] `tests/auth/conftest.py` — extend with `tmp_vault_path` and `frozen_vault` fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | All file-mode + JSON-shape behaviors covered automatically | — |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
