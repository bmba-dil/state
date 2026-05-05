---
gsd_state_version: 1.0
milestone: v8
milestone_name: — Plugin Server Hooks
status: v8 milestone complete
last_updated: "2026-05-05T11:09:32.227Z"
---

# STATE: state

**Last updated:** 2026-05-05 — v8 (Plugin Server Hooks) shipped. 8 / 27 milestones complete. v8 delivered 12 phases (068–079), 10/11 HOOK requirements satisfied (HOOK-05 event hook deferred — `event` not in opencode Hooks type v1.14.35). `@state/opencode-plugin` TS package scaffolded with bun build bundling, 9 server hooks implemented, install.sh auto-registration.

---

## Project Reference

**Core Value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.

**Primary host:** opencode
**Runtime:** Python 3.12+
**Mode model:** Build + Teach (exclusive per invocation; shared kernel; siloed logic)
**Planning hierarchy:** Arc → Phase → Slice → Step (product); Milestone → Phase (GSD)
**Granularity:** fine
**Parallelization:** true (DAG-native, not linear)

---

## Current Position

**Current tier:** Tier 2 active (v1 ✓, v2 ✓, v3 ✓, v4 ✓, v5 ✓, v6 ✓, v7 ✓, v8 ✓)
**Last shipped milestone:** v8 — Plugin Server Hooks — Shipped 2026-05-05
**Active milestone:** v8 — just shipped; v9 next unblocked
**Active phase:** None currently (milestone just completed)
**Previous milestones:** v1 (Event Store), v2 (Auth), v3 (Provider Routing), v4 (Worktree), v5 (DAG Scheduler), v6 (Daemon), v7 (Worker)

**Phases complete:** 80 / 268 (v1: 11, v2: 15, v3: 7, v4: 9, v5: 9, v6: 10, v7: 8, v8: 11 of 12)
**Milestones complete:** 8 / 27
**v1 requirements satisfied:** 8 / 8 (EVT-01..EVT-08) — full coverage
**v2 requirements satisfied:** 13 / 13 (AUTH-01..AUTH-13) — full coverage
**v6 requirements satisfied:** 8 / 8 (DAE-01, DAE-03..DAE-09) — DAE-02 owned by v7

```
[##########...................................................] 30%
```

### Unblocked milestones (ready to start, parallel-safe)

- v9 — Plugin TUI Bundle — depends on v8 (now shipped)
- v10 — Build Kernel — depends on v7+v8 (now shipped)

v3, v4, v5, v6, v7, v8 are shipped. Tier 2 (v6–v13) is the active tier.

### Critical path preview

Build critical path: A1 → A6 → A7 ✓ → A8 → A11 → A12 → A14 → A15 → A16 → A27
Teach critical path: A1 → A6 → A7 ✓ → A8 → A11 → A13 → A18 → A20 → A22 → A27

A1 (= v1) and A2 (= v2) now complete.

---

## Performance Metrics

| Metric | Value |
|---|---|
| Roadmap created | 2026-04-22 |
| v1 shipped | 2026-04-26 (merged to main 2026-04-28) |
| v2 shipped | 2026-05-03 (tagged v2) |
| v3 shipped | 2026-05-04 (squash-commit, 7/9 phases) |
| v4 shipped | 2026-05-04 (squash-commit, 9/9 phases) |
| v5 shipped | 2026-05-04 |
| v6 shipped | 2026-05-04 |
| v7 shipped | 2026-05-05 |
| v8 shipped | 2026-05-05 |
| Phases defined | 268 |
| Milestones defined | 27 |
| v1 requirements captured | 221 |
| Coverage | 100% |
| P0 pitfalls identified | 16 |
| P0 pitfalls closed | 12 / 16 (P0-9 in v1; P0-1..P0-8 + P0-13 + P0-14 in v2; P0-10 in v4; P0-15 in v6; P0-16 in v5) |
| Milestones shipped | 8 / 27 |
| v1-milestone phases shipped | 11 / 11 |
| v2-milestone phases shipped | 15 / 15 (12 + 3 gap-closure) |
| v3-milestone phases shipped | 7 / 9 (030/031 deferred) |
| v4-milestone phases shipped | 9 / 9 |
| v5-milestone phases shipped | 9 / 9 |
| v6-milestone phases shipped | 10 / 10 |
| v7-milestone phases shipped | 8 / 8 |
| v8-milestone phases shipped | 11 / 12 (073 deferred) |
| Total project phases shipped | 80 / 268 |
| v1 commits | 67 |
| v2 commits (since v1 tag) | 153 |
| v6 commits (daemon dir) | 27 |
| v6 daemon LoC (Python) | ~3,443 src |
| v1+v2 LoC (Python) | ~10,015 src + ~16,255 tests |
| Tests passing | ~1,034 (321 v1 + 463 v2 + ~250 v6) |
| v1 timeline | 4 days |
| v2 timeline | 5 days (2026-04-28 → 2026-05-02) |

---

## Accumulated Context

### Decisions committed (architectural)

See PROJECT.md Key Decisions table — now annotated with v1+v2 outcomes (✓ Good for delivered decisions; ⚠️ Revisit notes for the two debt items below).

### Open issues / debt going into v9

- **Deferred Items (v8 close, 2026-05-05):** 3 quick-tasks acknowledged at milestone close — pre-execution audit of ROADMAP.md review, audit ROADMAP.md for domain confusion, revise ROADMAP.md to apply review roadmap findings. HOOK-05 (event hook) deferred — `event` key not in opencode Hooks type v1.14.35.
- **Deferred Items (v5 close, 2026-05-04):** 3 quick-tasks acknowledged at milestone close — pre-execution audit of ROADMAP.md review, audit ROADMAP.md for domain confusion, revise ROADMAP.md to apply review roadmap findings.
- Retroactive SECURITY.md backfill for phases 011–022 + 022.1 + 022.2 (security_enforcement gate added mid-v2; only 022.3 has SECURITY.md).
- Manual release-time smoke gates for live OAuth (Anthropic/Gemini/Antigravity/Copilot) — owned by user; not yet in CI.
- Per-plan SUMMARY.md backfilled for 4 plans at v2 close (011-01, 011-02, 013-01, 020-01) — execute-phase agent should land per-plan SUMMARY at execute-time going forward.

### Blockers

(none — v2 shipped; v3/v4/v5 unblocked)

### Phases Completed

See `.planning/milestones/v1/` and `.planning/milestones/v2/` for full per-milestone phase records. Milestone-close summaries live in `.planning/MILESTONES.md`.

---

## Session Continuity

### Next actions (when resuming or starting)

1. **v9 — Plugin TUI Bundle:** TUI extensions (sidebar, routes, dialogs, statusline) for `@state/opencode-plugin`. v8 server hooks unblock this.
2. **v3 deferred items (030/031):** cache-control marker e2e (030) and provider parity matrix (031) — acknowledged tech debt, deferred to release-time smoke.
3. **Optional cleanup:** v3/v4/v5/v6/v7/v8 shipped; old phase branches safe to clean.

### v8 milestone delivered

- `@state/opencode-plugin` TS package scaffolded in `packages/opencode-plugin/`
- 9 server hooks: chat.message, tool.execute.before, tool.execute.after, permission.ask, experimental.chat.system.transform, experimental.session.compacting, chat.params, chat.headers, command.execute.before, shell.env
- Mode gating across all hooks (build/teach/kernel), cross-mode rejection
- Model profile resolution (quality/balanced/budget) with thinking budget headers
- `bun build` bundling (11.5 KB single-file), `install.sh` auto-registration
- 12 phases, 10/11 HOOK requirements satisfied (HOOK-05 deferred — API gap)

### v6 milestone delivered

- Unix socket HTTP server with JSON-RPC 2.0 router
- Platform-aware pid-file + stale process detection (P0-15 closed)
- Deterministic socket path resolution + worker discovery
- Mode-enforcement HTTP middleware (canonical isolation gate — 6th defense-in-depth layer)
- SSE event broadcast bus with multi-client fan-out
- launchd plist + systemd user unit service installer
- structlog + RotatingFileHandler log rotation with Phase 020 redactor
- Crash recovery: event replay + in-flight Step detection
- CLI: `state daemon start|stop|restart|status|logs`
- Auth credential manager with background refresh loop + GET /auth/status
- 10 phases, 33 tasks, ~250 tests, 0 regressions, 8/8 requirements satisfied

### Project state file set

- `.planning/PROJECT.md` — cardinal rules, constraints, key decisions (post-v2 evolution)
- `.planning/ROADMAP.md` — 27 milestones, 256 phases, DAG (v1 ✓, v2 ✓, v3 active)
- `.planning/STATE.md` — this file (live project memory)
- `.planning/MILESTONES.md` — shipped-milestone log (v1 + v2 entries)
- `.planning/milestones/v1/` — v1 milestone artifacts (Complete)
- `.planning/milestones/v2/` — v2 milestone artifacts (Complete)
- `.planning/milestones/v5/` — v5 milestone artifacts (Shipped)
- `.planning/milestones/v6/` — v6 milestone artifacts (Shipped)
- `.planning/milestones/v7/` — v7 milestone artifacts (Shipped)
- `.planning/milestones/v8/` — v8 milestone artifacts (Shipped)
- `.planning/milestones/v3/` — v3 milestone artifacts (Shipped)
- `.planning/milestones/v4/` — v4 milestone artifacts (Shipped)
- `.planning/milestones/v6-MILESTONE-AUDIT.md` — v6 audit (passed)
- `.planning/milestones/v2-{ROADMAP,REQUIREMENTS,MILESTONE-AUDIT}.md` — flat v2 archives
- `.planning/research/` — SUMMARY, ARCHITECTURE, FEATURES, PITFALLS, STACK
- `.planning/config.json` — mode=yolo, granularity=fine, parallelization=true
- `state-inputs/` — gitignored reference material (opencode source, GSD source, AOL workflows, claude-oauth.md, gsd2-auth-analysis.md)

### Tier boundary gates

- **Tier 1 → Tier 2:** all of v1..v5 ship (foundation complete). **v1 ✓ + v2 ✓ + v3 ✓ + v4 ✓ + v5 ✓ — Tier 1 complete (5/5).** Tier 2 (v6–v13) active with v6 ✓ + v7 ✓ + v8 ✓.
- **Tier 2 → Tier 3:** all of v6..v13 ship. **v6 ✓ + v7 ✓ + v8 ✓ — 5 left (v9–v13).**

---

*State initialized: 2026-04-22 — v1 shipped: 2026-04-26 — v2 shipped: 2026-05-03 — v3/v4/v5/v6 shipped: 2026-05-04 — v7/v8 shipped: 2026-05-05*
