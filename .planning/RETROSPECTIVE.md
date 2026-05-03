# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v2 — Auth Coverage (5 Methods + Multi-Cred)

**Shipped:** 2026-05-03
**Phases:** 15 (12 + 3 gap-closure) | **Plans:** 41 | **Commits:** 153 (since v1 tag) | **Timeline:** 5 days (2026-04-28 → 2026-05-02)

### What Was Built

- All five auth methods landed simultaneously: **Anthropic OAuth stealth** (PKCE state==verifier, claude-cli + anthropic-beta headers, captured-header golden suite), **Gemini CLI OAuth** (refresh-token rotation persisted), **Antigravity OAuth** (FIXED port 51121, 5 scopes, RFC 8252 loopback), **GitHub Copilot device-code** (RFC 8628 polling + grant-revocation detection), and a **12-provider plain-API-key vault**.
- **`state_core.auth.refresh`** — filelock-guarded refresh layer: 10 s acquire, double-check inside the held lock, 5-min expiry buffer applied at check-time only (wire-shape `expires` round-trips unchanged), 15 s outer cap on `method.refresh()`.
- **`auth.json` vault** — `chmod 0600` + `O_NOFOLLOW` symlink defense (T-018-9) + `with_vault_lock` concurrent-writer protection (T-018-8).
- **`state_core.observability.redactor`** — 12-pattern compile-time regex set, `_walk_value` recursive walker (cycle-safe + NamedTuple-safe after WK-01/03 hardening), `assert_redactor_attached()` canary, refuses daemon start if not attached.
- **First-run import from opencode `auth.json`** + **`state auth login|logout|status` CLI** wired through the daemon orchestrator at Step 0.5.

### What Worked

- **Wave-based TDD execution.** Wave 0 RED test scaffold → Wave 1+ GREEN drilling. 463 net-new tests landed without flaking; per-plan SUMMARY/PLAN/VERIFICATION artifacts kept each wave auditable.
- **Mode-isolation grep gates as per-phase verification.** Cheap, catches drift early. Every v2 phase passes `grep -nE "^from state_build|^import state_build|..."` against the introduced module — zero leakage in 15 phases.
- **Captured-header golden suites.** Per-provider stealth fidelity is pinned by frozen header captures in `state-inputs/*.md` + structural assertions in `tests/auth/test_*.py`. CI pins the contract without requiring live OAuth in the test loop.
- **Decimal phases for milestone gap-closure.** 022.1 (typing/Nyquist hygiene), 022.2 (deferred low-pri threats T-018-8/9), 022.3 (redactor reviewer cleanup WK-01..06) — small, focused, plan-then-execute under the same milestone, no roadmap renumbering.
- **Mid-milestone re-audit.** Running `/gsd:audit-milestone` produced the `tech_debt` classification with explicit "intentionally-deferred release-time gates + retroactive SECURITY.md backfill" rationale — surfaced exactly the right items without blocking close.

### What Was Inefficient

- **Per-plan SUMMARY discipline drift.** 4 plans (011-01, 011-02, 013-01, 020-01) landed without a per-plan SUMMARY because the executor consolidated content into VERIFICATION.md or peer SUMMARY at the time. Required backfill at milestone close. **Fix going forward:** execute-phase agent must land a per-plan SUMMARY before declaring the plan done, even when content overlaps with VERIFICATION.
- **Security enforcement enabled mid-milestone.** Phases 011..022 + 022.1 + 022.2 (14 phases) shipped before the SECURITY.md gate was turned on; only 022.3 has SECURITY.md. Backfilling all 14 retroactively is now tech debt. **Fix going forward:** enable security_enforcement at the start of v3, no backfill cost.
- **STATE.md drift across the milestone.** Top-level STATE.md and milestone-level STATE.md were not refreshed mid-milestone — at close they still claimed "phase 011 next up" while phases 011-022.3 were all complete. Required manual reconciliation at close.
- **Linear branch chain made dependency-ordered squash-merge non-trivial.** Each phase branch (018, 019, ..., 022.3) is a strict superset of the previous, so naive `git merge --squash` produced apply-conflicts on phase 019. Resolved by computing per-phase diffs (`git diff <prev>..<this>`) and applying as patches.
- **`gsd-tools milestone complete v2` returned `accomplishments: []`.** The CLI couldn't auto-extract one-liners from the SUMMARY files (likely structure mismatch). Required manual authoring of MILESTONES.md accomplishments.
- **Stale agent worktrees lingered.** 3 `worktree-agent-*` branches sat in `.claude/worktrees/` from completed parallel executor runs. None had unique work, but they showed up as branches and looked like real workstreams.

### Patterns Established

- **`with_vault_lock` context manager** for any RMW window on `auth.json` (login/logout/refresh). All vault-mutating operations now wrap their critical sections — the regression-test pattern (concurrent-writer harness in `tests/auth/test_store.py`) should be reused for any future shared-file structure.
- **Cycle-safe + NamedTuple-safe `_walk_value` recursion.** Pattern: `id()`-keyed `visited: set[int]` for cycle detection; `cls._make(walked) → cls(*walked) → tuple(walked)` cascade for tuple subclasses. Reusable for any future tree-walking code over arbitrary user payloads.
- **Refuse-to-start daemon if security primitive isn't attached.** `assert_redactor_attached()` runs at orchestrator Step 0; if the canary doesn't redact, the daemon crashes loudly. This pattern (post-init self-check) should be the default for any security-critical primitive in v3+ (provider-routing, mode-enforcement).
- **Decimal-phase gap-closure within a milestone.** Confirmed v1's pattern (010.1) works at scale (3 decimal phases in v2). When a milestone audit surfaces gaps, decimal phases under the same milestone are the right shape — no roadmap renumbering, clear "this came from milestone close" provenance.

### Key Lessons

1. **Per-plan SUMMARY is non-negotiable.** Backfill at milestone close cost ~30 min and lost detail. The 5 minutes saved per plan during execution was net negative.
2. **Update STATE.md at every plan boundary, not just at milestone boundaries.** Drift compounds and makes "what's actually done" un-obvious.
3. **Squash-merge linear branch chains via per-phase diff, not `git merge --squash` per branch.** Each later branch's merge-base with main re-includes earlier phases' code, producing spurious conflicts.
4. **Captured-header golden suites are the right shape for stealth-flow fidelity.** They don't require live providers in CI but pin the contract that matters. Reuse for v3 provider-routing's litellm header forwarding.
5. **Mode-isolation grep gates work and should expand.** v2 added them per-phase against `state_build.*` / `state_teach.*` import leakage. v3 should add a third gate: `state_core.providers.*` should NOT import from any specific provider's auth surface (cross-provider isolation).
6. **`tech_debt` is an honest milestone audit verdict** when the debt is itemized + intentional. Don't shoehorn into `passed` to feel good; record what's deferred and why.

### Cost Observations

- **Model mix this milestone:** primarily Claude Opus 4.6 / 4.7 with occasional Sonnet 4.6 for batch verifier work (per `.planning/config.json` `model_profile: budget` for executor agents).
- **Sessions:** ~10–15 sessions across 5 days (precise count not tracked; `.planning/patterns/sessions.jsonl` has the granular log).
- **Notable efficiency:** parallel executor + worktree concurrency materially shortened phases 019–022 (RED-stub authoring + GREEN drilling could overlap). Single-threaded estimate would have been ~2× the wall-clock time.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Commits | Timeline | Key Change |
|-----------|--------|-------|---------|----------|------------|
| v1 | 11 (10 + 010.1) | 17 | 67 | 4 days | Foundation; established per-phase TDD pattern |
| v2 | 15 (12 + 022.1/.2/.3) | 41 | 153 | 5 days | Wave-based TDD; decimal-phase gap-closure; captured-header golden suites |

### Cumulative Quality

| Milestone | Tests Added | Total Tests Passing | Regressions | Net New LoC (Python) |
|-----------|-------------|---------------------|-------------|----------------------|
| v1 | 321 | 321 | 0 | ~2,779 src |
| v2 | 463 | 784 | 0 | ~7,236 src + ~16,255 tests |

### Top Lessons (Verified Across Milestones)

1. **Per-plan SUMMARY at execute-time, not at milestone close.** v1 had this discipline; v2 dropped it on 4 plans and paid the backfill cost. Re-establish for v3.
2. **Decimal-phase gap-closure under the same milestone is the right shape.** v1 (010.1) and v2 (022.1/.2/.3) both used it successfully — no roadmap renumbering, clear provenance.
3. **Mode-isolation enforcement at phase boundaries.** Both milestones rely on grep gates against `state_build.*` / `state_teach.*` imports; both pass. The pattern works.
4. **Wave-based TDD with RED-then-GREEN landing scales.** v1 piloted it on phase 010 (verifier); v2 used it for all 15 phases without test flake.
5. **Tech debt should be itemized, not hidden.** Both milestones used `/gsd:audit-milestone` to surface deferred items explicitly — keeps debt navigable across milestone boundaries.
