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

## Milestone: v5 — DAG Scheduler

**Shipped:** 2026-05-04
**Phases:** 9 | **Plans:** 9 | **Tests:** 130 | **LOC:** ~3,311 (828 scheduler + 96 reactive + 445 CLI + 1,942 tests) | **Timeline:** 1 day

### What Was Built

- **Pure-Python DAG scheduler** — `Edge`/`Node`/`NodeRegistry` types, Kahn's topological sort with stable `(slice_id, step_id)` ordering, DFS 3-color cycle detection returning cycle paths, frontier calculator distinguishing `blocks`/`data` from `soft` edges
- **`DAGScheduler.tick()`** async dispatcher with `asyncio.TaskGroup`, configurable concurrency cap via `SchedulerConfig` from TOML, `StepExecutor` injection for testability
- **P0-16 closed** — `_inspect_for_cancelled()` recursive watchdog catches swallowed `CancelledError` in `BaseExceptionGroup` trees, re-raises via `SwallowedCancelledError`
- **`ReactiveTrigger`** — zero-polling event-driven subscription to v1 event store via existing `add_post_commit_callback()` mechanism; filters to `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned`; fire-and-forget `asyncio.create_task()` dispatch
- **CPM critical-path + priority inversion + silent deadlock detection** — longest-path forward/backward DP on topological order, `detect_priority_inversion()` (critical-path node blocked on soft edge), `detect_silent_deadlock()` (frontier empty + all in-progress stuck on missing predecessors)
- **`state dag show` CLI** — 445 LOC Typer sub-app with Unicode box-drawing, 6 Rich status colors, `--demo`/`--file`/`--arc`/`--phase`/`--slice` flags, Hypothesis property test (200 examples, any valid DAG renders without crash)

### What Worked

- **Batched autonomous phase execution.** Phases 043+044 planned and executed in parallel (both depend only on 041). Cross-contamination from same-file edits merged cleanly — 53 tests passed with zero conflicts.
- **TDD RED/GREEN/REFACTOR per phase.** Every phase (041-049) followed the 3-commit RED→GREEN→REFACTOR pattern. 130 tests added incrementally without regression.
- **Single-file module growth.** `scheduler.py` grew from 11-line skeleton to 828-line module organically. Each phase appends its new types/functions to the existing file — no premature abstraction or file splitting.
- **Consistent contract patterns.** `topo_sort()`, `detect_cycles()`, `frontier()`, `tick()` all take `(edges, nodes)` or `(nodes, edges)`, follow existing conventions, raise `ValueError` on invalid input. No surprise API shapes.

### What Was Inefficient

- **REQUIREMENTS.md traceability table stale.** All 7 DAG requirements were missing from the traceability table at the start and still missing at close — the CLI flagged them as warnings. Traceability needs initial setup at new-milestone time.
- **048 executor hit step limit.** The final phase executor completed code+integration tests but hit the agent step limit, requiring a follow-up commit for SUMMARY.md. 94/94 tests already passing — just the artifact was missing.
- **No VERIFICATION.md files for phases 042-049.** Only 041 has a verifier's VERIFICATION.md. The remaining phases verified via inline test results and manual spot-checks. Formal verification coverage could be more thorough.

### Key Lessons

1. **Parallel phase execution works for independence.** Phases 043+044 (both depend only on 041) were planned and executed in parallel — net ~2× throughput. Same-file conflicts handled cleanly via git merge.
2. **Skeleton→implementation growth pattern is sound.** Starting with `DAGScheduler.tick(): ...` (Phase 041) and filling it in Phase 045 allowed phases 042-044 to add independent functions without coordination overhead.
3. **Frozen pydantic models with `extra="forbid"` prevent drift.** Every data model (Edge, Node, SchedulerConfig) uses `frozen=True` + `extra="forbid"` — zero post-construction mutation bugs across 9 phases.
4. **CancelledError swallow is a real Python footgun.** P0-16's watchdog required understanding `BaseExceptionGroup` (not `ExceptionGroup`) and `task.cancelled()` filtering in `TaskGroup.__aexit__`. The CPython #116720 issue is subtle — `CancelledError` is a `BaseException`, so it's in `BaseExceptionGroup`, not `ExceptionGroup`.

### Cost Observations

- **Model mix:** Primarily deepseek-v4-pro for orchestrator, sonnet/haiku for planner/executor agents.
- **Sessions:** Single continuous session for all 9 phases + lifecycle.
- **Notable efficiency:** Autonomous `--from 041 --to 049` with `skip_discuss=true` executed all 9 phases in a single session. No context-reset needed between phases.

---

## Milestone: v6 — State Daemon (HTTP + SSE + Mode Middleware)

**Shipped:** 2026-05-04
**Phases:** 10 | **Plans:** 10 | **Tests:** ~250 | **LOC:** ~3,443 daemon + 250 tests | **Timeline:** 1 day

### What Was Built

- Unix socket HTTP server with JSON-RPC 2.0 router and pluggable route handlers
- Platform-aware pid-file with stale process detection (P0-15 closed)
- Mode-enforcement HTTP middleware — canonical gate for build/teach isolation
- SSE event broadcast bus with multi-client fan-out and mode filtering
- launchd plist + systemd user unit generator with `state daemon install|uninstall` CLI
- Crash recovery replaying event log, rebuilding projections, detecting in-flight Steps
- Full daemon lifecycle CLI: `state daemon start|stop|restart|status|logs`
- Auth credential refresh loop + round-robin manager + `GET /auth/status`

### Key Lessons

1. **Tier 2 infrastructure can ship before Tier 1 is complete.** v6 (daemon, Tier 2) shipped before v3/v4 (Tier 1) because it was unblocked — v1 events + v2 auth were sufficient dependencies. The critical path for v7 required v6, so early-ship was strategic.
2. **Pid-file stale detection needs platform-awareness.** macOS `ps -o lstart=` format differs from Linux `/proc/<pid>/stat`. Both handled via platform detection in the pid module.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Commits | Timeline | Key Change |
|-----------|--------|-------|---------|----------|------------|
| v1 | 11 (10 + 010.1) | 17 | 67 | 4 days | Foundation; established per-phase TDD pattern |
| v2 | 15 (12 + 022.1/.2/.3) | 41 | 153 | 5 days | Wave-based TDD; decimal-phase gap-closure; captured-header golden suites |
| v5 | 9 | 9 | 25+ | 1 day | Autonomous batch execution; pure-Python DAG scheduler; P0-16 closed |
| v6 | 10 | 10 | 27 | 1 day | Early Tier 2 shipping; daemon infrastructure unblocked |

### Cumulative Quality

| Milestone | Tests Added | Total Tests Passing | Regressions | Net New LoC (Python) |
|-----------|-------------|---------------------|-------------|----------------------|
| v1 | 321 | 321 | 0 | ~2,779 src |
| v2 | 463 | 784 | 0 | ~7,236 src + ~16,255 tests |
| v5 | 130 | 130 | 0 | ~3,311 (scheduler + reactive + CLI) |
| v6 | ~250 | 1,164 | 0 | ~3,443 daemon |

### Top Lessons (Verified Across Milestones)

1. **Per-plan SUMMARY at execute-time.** v1 had this; v2 dropped it on 4 plans; v5 restored it across all 9 plans.
2. **TDD RED→GREEN→REFACTOR commits per phase.** All 4 shipped milestones use this pattern — zero test flake, zero regressions.
3. **Parallel autonomous execution scales.** v5 demonstrated 9-phase autonomous batch in one session with parallel phase planning/execution where dependencies allowed.
4. **Frozen pydantic models with `extra="forbid"` prevent drift.** Every data model across v1, v2, v5, v6 uses this pattern — zero post-construction mutation bugs.
5. **Tech debt should be itemized, not hidden.** v2 established the pattern; v5 continued it with explicit deferred items at close.
