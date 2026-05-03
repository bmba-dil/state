---
phase: 013
slug: filelock-guarded-refresh-lock
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
---

# Phase 013 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ + pytest-asyncio (asyncio_mode=auto) + filelock 3.29 |
| Quick run | `.venv/bin/python -m pytest tests/auth/test_refresh.py -x -q -m "not integration"` |
| Full | `.venv/bin/python -m pytest tests/auth/ -v` |
| Integration (multiprocessing) | `.venv/bin/python -m pytest tests/auth/test_refresh.py -m integration` |
| Estimated runtime | ~5s unit, ~10s integration |

## Sampling Rate

- After every task commit: quick command
- After every plan wave: full auth suite
- Before /gsd:verify-work: include integration suite (mp-based concurrent refresh test)
- Max feedback latency: ~5s (unit)

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 013-01-* | 01 | 1 | REFRESH-01..REFRESH-30 | unit + integration | pytest tests/auth/test_refresh.py -v | ❌ W0 | ⬜ pending |
| 013-02-* | 02 | 2 | AUTH-07, AUTH-09, P0-6, P0-7 | unit + integration | pytest tests/auth/test_refresh.py -v | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] `tests/auth/test_refresh.py` — RED stubs for REFRESH-01..REFRESH-30
- [ ] `tests/auth/conftest.py` — extend with `expired_oauth_cred`, `vault_with_expired_oauth`, `mock_auth_method` counting-mock fixtures
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` — register `integration` and `slow` markers

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | All concurrency behaviors covered by mp-based integration test | — |

## Validation Sign-Off

- [ ] Wave 0 covers REFRESH-01..REFRESH-30
- [ ] Markers registered (no PytestUnknownMarkWarning)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s

**Approval:** pending
