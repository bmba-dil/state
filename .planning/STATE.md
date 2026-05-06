---
gsd_state_version: 1.0
status: v11 milestone complete
last_updated: 2026-05-06T01:06:18.634Z
---

# STATE: state

**Last updated:** 2026-05-06 — Phase 123 (Integration test) complete. v13 SHIPPED: all 9 phases (115–123). 12 / 27 milestones complete. v12 (state-build MCP) in progress.

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

**Current tier:** Tier 2 active (v1 ✓, v2 ✓, v3 ✓, v4 ✓, v5 ✓, v6 ✓, v7 ✓, v8 ✓, v9 ✓, v10 ✓)
**Last shipped milestone:** v11 — Mode Enforcement — Shipped 2026-05-05
**Active milestone:** v12 (state-build MCP) and v13 (state-teach MCP) — both in progress
**Active phase:** Phase 123 (Integration test) — completed, plan 01/01 done
**Previous milestones:** v1 (Event Store), v2 (Auth), v3 (Provider Routing), v4 (Worktree), v5 (DAG Scheduler), v6 (Daemon), v7 (Worker), v8 (Plugin Hooks), v9 (TUI Bundle), v10 (DAG Viewer), v11 (Mode Enforcement)

**Phases complete:** 115 / 260 (v1: 11, v2: 15, v3: 7, v4: 9, v5: 9, v6: 10, v7: 8, v8: 11, v9: 9, v10: 8, v11: 9, v13: 9)
**Milestones complete:** 12 / 27
**v1 requirements satisfied:** 8 / 8 (EVT-01..EVT-08) — full coverage
**v2 requirements satisfied:** 13 / 13 (AUTH-01..AUTH-13) — full coverage
**v6 requirements satisfied:** 8 / 8 (DAE-01, DAE-03..DAE-09) — DAE-02 owned by v7

```
[##################..........................................] 44%
```

### Unblocked milestones (ready to start, parallel-safe)

- v12 — state-build MCP Server (skeleton) — depends on v11 (now shipped)
- v13 — state-teach MCP Server (skeleton) — depends on v11 (now shipped); parallel with v12

v1–v11 are all shipped. Tier 2 (v6–v13) is the active tier with v12 and v13 remaining.

### Critical path preview

Build critical path: A1 → A6 → A7 ✓ → A8 ✓ → A11 ✓ → A12 → A14 → A15 → A16 → A27
Teach critical path: A1 → A6 → A7 ✓ → A8 ✓ → A11 ✓ → A13 → A18 → A20 → A22 → A27

A1–A11 (= v1–v11) complete. A13 (= v13) complete.

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
| v7 shipped | 2026-05-05 |
| v8 shipped | 2026-05-05 |
| v9 shipped | 2026-05-05 |
| v10 shipped | 2026-05-05 |
| v11 shipped | 2026-05-05 |
| Phases defined | 260 |
| Milestones defined | 38 (27 core + 11 design spike v40-v50) |
| v1 requirements captured | 221 |
| Coverage | 100% |
| P0 pitfalls identified | 16 |
| P0 pitfalls closed | 16 / 16 (all closed) |
| Milestones shipped | 11 / 27 |
| v1-milestone phases shipped | 11 / 11 |
| v2-milestone phases shipped | 15 / 15 (12 + 3 gap-closure) |
| v3-milestone phases shipped | 7 / 9 (030/031 deferred) |
| v4-milestone phases shipped | 9 / 9 |
| v5-milestone phases shipped | 9 / 9 |
| v6-milestone phases shipped | 10 / 10 |
| v7-milestone phases shipped | 8 / 8 |
| v8-milestone phases shipped | 11 / 12 (073 deferred) |
| v9-milestone phases shipped | 9 / 9 |
| v10-milestone phases shipped | 8 / 8 |
| v11-milestone phases shipped | 9 / 9 |
| v13-milestone phases shipped | 9 / 9 |
| Total project phases shipped | 109 / 260 |
| v1 commits | 67 |
| v2 commits (since v1 tag) | 153 |
| v6 commits (daemon dir) | 27 |
| v6 daemon LoC (Python) | ~3,443 src |
| v1+v2 LoC (Python) | ~10,015 src + ~16,255 tests |
| Tests passing | ~1,034 (321 v1 + 463 v2 + ~250 v6) |
| v1 timeline | 4 days |
| v2 timeline | 5 days (2026-04-28 → 2026-05-02) |

---
| Phase 119-drill-prompt-token-cap P01 | 386 | 2 tasks | 2 files |

## Accumulated Context

### Decisions committed (architectural)

See PROJECT.md Key Decisions table — now annotated with v1+v2 outcomes (✓ Good for delivered decisions; ⚠️ Revisit notes for the two debt items below).

### Open issues / debt going into v12

- **Deferred Items (v11 close, 2026-05-05):** 3 quick-tasks acknowledged at milestone close — pre-execution audit of ROADMAP.md review, audit ROADMAP.md for domain confusion, revise ROADMAP.md to apply review roadmap findings.
- **Deferred Items (v8 close, 2026-05-05):** HOOK-05 (event hook) deferred — `event` key not in opencode Hooks type v1.14.35.
- **Deferred Items (v5 close, 2026-05-04):** 3 quick-tasks acknowledged at milestone close.
- Retroactive SECURITY.md backfill for phases 011–022 + 022.1 + 022.2 (security_enforcement gate added mid-v2; only 022.3 has SECURITY.md).
- Manual release-time smoke gates for live OAuth (Anthropic/Gemini/Antigravity/Copilot) — owned by user; not yet in CI.

### Blockers

(none — v11 shipped; v12 unblocked)

### Phases Completed

See `.planning/milestones/v1/` and `.planning/milestones/v2/` for full per-milestone phase records. Milestone-close summaries live in `.planning/MILESTONES.md`.

---

## Session Continuity

### Next actions (when resuming or starting)

1. **v12 — state-build MCP Server (skeleton):** Mode-gated MCP server with 15-tool budget. v11 mode enforcement unblocks this. Only remaining milestone in Tier 2.
2. **v40–v50 Design Spike:** 11 design-phase milestones to fully architect the build and teach kernels before v14–v27 are executed. Handoff documents at `.planning/milestones/v{40..50}/HANDOFF.md`. Feed these into `gsd-new-milestone` in new sessions. User will be present for all discuss-phases (NOT autonomous).
3. **v3 deferred items (030/031):** cache-control marker e2e (030) and provider parity matrix (031) — acknowledged tech debt, deferred to release-time smoke.
4. **Optional cleanup:** v1–v11+v13 shipped; old phase branches safe to clean.

### v11 milestone delivered

- 6-layer mode enforcement defense-in-depth implemented: (1) mode.json schema validator, (2) directory presence signal with subtree validation, (3) MCP registration toggle via config hook, (4) plugin hook mode gates with cached getCurrentMode(), (5) daemon HTTP mode middleware with event-type validation, (6) Python import-graph lint with pre-commit hook
- CLI: `state mode init` and `state mode set` with atomic writes, subtree creation, SIGHUP hot-reload
- 114-test cross-mode leakage regression suite
- 9 phases, all 6 layers verified, MODE-01 through MODE-06 satisfied

### v13 milestone delivered

- `state-teach` MCP server (14 tools, all skeleton) — FastMCP stdio entry point with mode-gate check
- 14 tools registered: concept_next, drill_prepare, drill_verify, concept_teach, observation_record, mental_model_show, subject_pick, subject_author, style_edit, learner_state, review_session, mentor_scaffold, coding_partner, learning_verify
- Tool descriptions all ≤80 tokens (o200k_base encoding) — MCP-T-02 compliant
- Question binding wrapper for opencode's question tool (MCP-T-04) — Pydantic Question/Option/Answer models
- Structured Observation schema with 5 kinds and kind discriminator (MCP-T-05)
- Token counting + cap enforcement with Hypothesis property tests (MCP-T-06)
- Shared library wiring to state_core.auth and state_core.events (Phase 120)
- Mode-gate integration: rejects build mode (exit 78), allows teach/both
- Tool-budget CI assertion: `state dev tool-budget --server state-teach` green
- Integration test suite: 10 tests, 4 classes (Registration, Invocation, ModeGate, Structural), all passing in 0.41s
- 9 phases, MCP-T-01 through MCP-T-06 satisfied

### v10 milestone delivered

- `state.dag` route registered in opencode plugin via `api.route.register()`
- Topological layout algorithm (longest-path layering + barycenter cross-reduction)
- Shared status palette (`status-palette.ts`) with 7 statuses and theme-derived colors
- Split-view detail pane with node metadata and dependency display
- Keyboard navigation (↑↓ to navigate, Enter to select, Esc to deselect)
- Filter bar with presets: all, active, blocked, critical-path (DP longest-path)
- SSE live updates with diff-patching for incremental node status changes
- Layout caching with key-based invalidation + viewport clipping for graphs ≥100 nodes
- Accessibility: screen-reader announcements, focus indicators, keyboard-only navigation
- 8 phases, 344 TUI tests, 0 failures, 4/4 DAG-VIEW requirements satisfied

### v9 milestone delivered

- Mode-aware TUI sidebar with conditional render: build-progress tree (Arc/Phase/Slice) vs teach-concept state
- Build-progress sub-component with Step status colors + Slice DAG mini-view
- Teach-concept sub-component with concept card + Kolb stage + mastery bar
- Statusline showing mode / scope / provider / session cost
- Toast notifications for Slice completion, drill availability, auth refresh
- Prompt hint slot with model + token cost + Step indicator
- Plugin install script auto-registering TUI extensions
- 9 phases, 344 total TUI tests, 5/5 TUI requirements satisfied

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
- `.planning/milestones/v9/` — v9 milestone artifacts (Shipped)
- `.planning/milestones/v10/` — v10 milestone artifacts (Shipped)
- `.planning/milestones/v11/` — v11 milestone artifacts (Shipped)
- `.planning/milestones/v3/` — v3 milestone artifacts (Shipped)
- `.planning/milestones/v4/` — v4 milestone artifacts (Shipped)
- `.planning/milestones/v6-MILESTONE-AUDIT.md` — v6 audit (passed)
- `.planning/milestones/v2-{ROADMAP,REQUIREMENTS,MILESTONE-AUDIT}.md` — flat v2 archives
- `.planning/research/` — SUMMARY, ARCHITECTURE, FEATURES, PITFALLS, STACK
- `.planning/config.json` — mode=yolo, granularity=fine, parallelization=true
- `state-inputs/` — gitignored reference material (opencode source, GSD source, AOL workflows, claude-oauth.md, gsd2-auth-analysis.md)

### Tier boundary gates

- **Tier 1 → Tier 2:** all of v1..v5 ship (foundation complete). **v1 ✓ + v2 ✓ + v3 ✓ + v4 ✓ + v5 ✓ — Tier 1 complete (5/5).** Tier 2 (v6–v13) active with v6 ✓ + v7 ✓ + v8 ✓ + v9 ✓ + v10 ✓ + v11 ✓ + v13 ✓.
- **Tier 2 → Tier 3:** all of v6..v13 ship. **v6 ✓ + v7 ✓ + v8 ✓ + v9 ✓ + v10 ✓ + v11 ✓ + v13 ✓ — 1 left (v12).**

---

*State initialized: 2026-04-22 — v1 shipped: 2026-04-26 — v2 shipped: 2026-05-03 — v3/v4/v5/v6 shipped: 2026-05-04 — v7/v8/v9/v10/v11 shipped: 2026-05-05*
