# Quick Task 2 — Pre-Audit Scan (Research)

**Scanned:** 2026-04-22
**Purpose:** Raw evidence for a subsequent skeptical ROADMAP.md review. Extraction only — no classification or recommendations.

---

## 1. P0 Pitfall Roster

All 16 P0 items drawn from `.planning/research/PITFALLS.md §P0 Rollup` (lines 4–23).
"Milestone per research" = the owning Arc/Milestone per PITFALLS.md "Maps to Arc" column and SUMMARY.md §6.
"ROADMAP addresses in" = milestones whose `**P0 pitfalls owned:**` line (or body text) names that P0.

| ID | One-line description | Research-owner | ROADMAP owner(s) | Flag |
|----|----------------------|----------------|------------------|------|
| P0-1 | Missing `user-agent: claude-cli/<ver>` header on Anthropic OAuth | Auth Arc (A2) + Provider Routing Arc (A3) | v2 (line 284) + v3 shares (line 399) | |
| P0-2 | Missing `anthropic-beta: claude-code-…,oauth-2025-04-20,…` header | Auth Arc (A2) | v2 (line 284) + v3 shares (line 399) | |
| P0-3 | Missing `x-app: cli` header | Auth Arc (A2) | v2 (line 284) + v3 shares (line 399) | |
| P0-4 | Using `x-api-key` instead of Bearer for `sk-ant-oat*` | Auth Arc (A2) | v2 (line 284) | |
| P0-5 | Fresh OAuth client_id instead of `9d1c250a-…` | Auth Arc (A2) | v2 (line 284) | |
| P0-6 | Dual-refresh race invalidates live token | Auth Arc (A2) | v2 (line 284; phase P0 tag at 332) | |
| P0-7 | `expires_in` verbatim, no 5-min buffer | Auth Arc (A2) | v2 (line 284) | |
| P0-8 | PKCE `state` not reused as verifier | Auth Arc (A2) | v2 (line 284) | |
| P0-9 | SQLite event-sequence non-monotonic after crash | Event Store Arc (A1) | v1 (line 184; phase regression at 007 line 251) | |
| P0-10 | Orphan locked worktrees fill disk | Worktree Arc (A4) [SUMMARY §6 also lists A6] | v4 (line 491; phase P0 tag at line 553) | |
| P0-11 | Mode isolation leakage Build↔Teach | Mode Isolation Arc (A11) | v11 (line 1114; phase P0 tag at line 1170) | |
| P0-12 | MCP tool-name collision / cross-mode invocation | MCP Arc (A11+A12+A13 per SUMMARY §6) | v12 (line 1205) + v13 (line 1292 "shared") | |
| P0-13 | `auth.json` world-readable (chmod != 0600) | Auth Arc (A2) | v2 (line 284; phase P0 tag at line 325) | |
| P0-14 | OAuth refresh writes plaintext tokens to log on debug=true | Auth Arc + Observability Arc (SUMMARY §6: "A2, observability") | v2 (line 284; phase P0 tag at line 376) | ⚠ PITFALLS §P0-14 maps to "Observability Arc" — v27 carries Observability (§Observability lines) but v27 has no `P0 pitfalls owned:` line naming P0-14 |
| P0-15 | Stale pid-file refuses daemon start | Daemon Arc (A6) | v6 (line 670; phase P0 tag at line 708) | |
| P0-16 | TaskGroup swallows CancelledError, deadlocks scheduler | Scheduler Arc (A5) | v5 (line 582; phase P0 tag at line 641) | |

Observations (extracted only, no editorial):
- All 16 P0s have at least one milestone-level `P0 pitfalls owned:` entry in ROADMAP.md.
- v3 line 399 lists `(shares P0-1/2/3 with v2 via stealth bypass guard)` — redundant ownership, not a gap.
- v27 (Release & Packaging) contains `OBS-01..04` and `SEC-01..06` requirements but does not name P0-14 in any `P0 pitfalls owned:` entry; see ⚠ above.

---

## 2. Milestone Roster (v1 .. v27)

Milestone-level complexity is the only complexity declared in ROADMAP.md (single `**Complexity:**` line per milestone, lines 183, 283, 398, 490, 581, 669, 766, 844, 948, 1033, 1113, 1204, 1291, 1379, 1484, 1579, 1698, 1777, 1884, 1976, 2080, 2165, 2257, 2336, 2419, 2502, 2580). **No per-phase S/M/L/XL labels exist in ROADMAP.md** — so "complexity mix of phases" cannot be extracted from the artifact; the column is recorded as N/A.

"Declared verifier" is the milestone-level `**Verifier:**` sentence condensed to ≤8 words.

| M-A | Title (ROADMAP line) | Tier | Complexity | # Phases | Verifier (abridged) | Depends on (verbatim) |
|-----|---------------------|------|------------|----------|---------------------|----------------------|
| v1 | Event Store Foundation (177) | 1 | L | 10 | Replay 10,000 synthetic events; crash-then-converge | (none — foundation) |
| v2 | Auth Coverage (5 Methods + Multi-Cred) (277) | 1 | L | 12 | Captured-header regression + 9 P0 tests + 0600 verify + concurrent-refresh harness | (none — foundation; no runtime deps on A1 yet, auth.json is standalone) |
| v3 | Provider Routing + Model Profiles (392) | 1 | L | 9 | Bypass-guard test + provider parity matrix + cache-control + thinking-budget | v2 (soft — provider tests need auth creds, but scaffolding can start in parallel) |
| v4 | Worktree + Snapshot Service (484) | 1 | M | 9 | 10 concurrent Slices; crash mid-bootstrap rollback; orphan-GC; prefix-revert | (none — foundation; snapshot-composition uses opencode Snapshot but abstraction hides it) |
| v5 | DAG Scheduler (575) | 1 | L | 9 | Hypothesis property tests; CancelledError watchdog; 10K-Step bench <500ms | v1 (reactive to event-store updates) |
| v6 | State Daemon (HTTP + SSE + Mode Middleware) (663) | 2 | L | 10 | `kill -9` stale-pid recovery; 100 req/s load; mode middleware; crash replay | v1 (events), v2 (auth) |
| v7 | Per-Session Worker (760) | 2 | M | 8 | 3 concurrent sessions; kill one session → worker gone; version handshake | v6 |
| v8 | Plugin Server Hooks (all 9) (838) | 2 | L | 12 | Each hook round-trips through worker → daemon → events.sqlite | v7 |
| v9 | Plugin TUI Bundle (942) | 2 | L | 9 | Sidebar mode-aware; statusline; toasts on Slice/drill/auth | v7 |
| v10 | TUI DAG Viewer (1027) | 2 | M | 8 | Nodes colored; click detail; filter; live update <2s | v8, v9 |
| v11 | Mode Enforcement (6 Layers) (1107) | 2 | M | 9 | Mode switch <3s; cross-mode write rejected; import lint CI fail | v6, v8 |
| v12 | state-build MCP Server (skeleton) (1198) | 2 | M | 9 | tool-budget 15×80 tokens; cross-mode invocation blocked | v11 |
| v13 | state-teach MCP Server (skeleton) (1285) | 2 | M | 9 | 15-tool budget; drill ≤3000 tokens; freeform observation rejected | v11 |
| v14 | Build Kernel: Step FSM + Verifiers (1373) | 3a | XL | 11 | 10 golden Steps; Slice rollup; cross-tier regression | v5 (scheduler), v12 (MCP skeleton) |
| v15 | Build Core Commands (plan/execute/verify/ship) (1478) | 3a | L | 10 | E2E discuss→plan→execute→verify→ship; fail→revert; plan-checker rejects bad plans | v14, v4 (ship needs worktree+snapshot) |
| v16 | Build GSD Command Ports (1573) | 3a | XL | 14 | Each command golden-file; subagents complete; multi-Arc batch-planner valid DAG | v15 |
| v17 | Build TUI Extensions (1692) | 3a | M | 8 | Dashboard Arc hierarchy; 4 tabs; commit revert; gray-area dialog | v9, v14 |
| v18 | Teach Kernel: Kolb + Concepts + Mental-Model (1771) | 3b | L | 11 | 10 observations project; rebuild byte-identical; Kolb fixture; frustration drop | v5 (scheduler for review queues), v13 (MCP) |
| v19 | Teach Drill Engine (1878) | 3b | M | 9 | Drill ≤3000 tokens; Bayesian matches AOL golden; stdin fallback | v18 |
| v20 | Teach Four Modes + Selector (1970) | 3b | XL | 11 | Each mode full walkthrough; selector at mastery bands; override; drop-to-simpler | v18 |
| v21 | Teach Personalities + Teaching Style (2074) | 3b | M | 8 | 7-personality substring; 7-dim style round-trip; per-subject override | v18 |
| v22 | Scaffolding-Mentor + Coding-Partner (2159) | 3b | L | 9 | Mentor never writes; partner never codes; growth-note gate | v20, v21 |
| v23 | Teach TUI Extensions (2251) | 3b | M | 8 | Dashboard, drill UI, mental-model viewer, session timeline | v9, v18 |
| v24 | Subject Authoring + 4-Gate Promoter (2330) | 3b | M | 8 | Author → promote schema-valid; 4 gates block invalid; interview covers fields | v18 |
| v25 | Migration & Import (2413) | 4 | M | 8 | Dry-run diff; schema-valid `.state/`; round-trip identical projections | v1, v11 |
| v26 | Portability Shims (2496) | 4 | L | 8 | Each host spawns MCP; question→stdin fallback; snapshot-missing graceful | v12, v13 |
| v27 | Release & Packaging (2574) | 4 | M | 10 | `uvx state install` clean macOS+Linux; `state update` PyPI; skills registry | most of v1..v24 (soft); v26 (cross-host verification) |

**Totals:** 27 milestones; 256 `#### Phase` headings in ROADMAP.md (sum of the table column). STATE.md (line 27 and line 65) claims 267 phases — these two numbers differ by 11 (not analyzed here, flagged as discrepancy).

---

## 3. Parallel-Safe Claim — Raw Evidence

### STATE.md quoted lines (verbatim)

Lines 34–42:
> ### Unblocked milestones (ready to start, parallel-safe)
>
> - v1 — Event Store Foundation
> - v2 — Auth Coverage (5 methods)
> - v3 — Provider Routing + Model Profiles (soft-depends on v2 for cred testing; scaffolding can start now)
> - v4 — Worktree + Snapshot Service
> - v5 — DAG Scheduler
>
> All five Tier 1 milestones have zero predecessors and can run concurrently.

Also STATE.md line 17:
> **Parallelization:** true (DAG-native, not linear)

Supporting table in ROADMAP.md lines 114–127 (Parallel-Safe Milestone Groups):
> | W1 | v1, v2, v3, v4, v5 |

### Each milestone's `**Depends on:**` line (verbatim)

| Milestone | Line | `**Depends on:**` (verbatim) |
|-----------|------|------------------------------|
| v1 | 181 | `(none — foundation)` |
| v2 | 281 | `(none — foundation; no runtime deps on A1 yet, auth.json is standalone)` |
| v3 | 396 | `v2 (soft — provider tests need auth creds, but scaffolding can start in parallel)` |
| v4 | 488 | `(none — foundation; snapshot-composition uses opencode Snapshot but abstraction hides it)` |
| v5 | 579 | `v1 (reactive to event-store updates)` |

Supporting text — ROADMAP.md line 78 (inside the Milestone DAG code-block header for Tier 1):
> `Tier 1 (all independent; no edges between them):`
> `  v1 ─┐`
> `  v2 ─┤`
> `  v3 ─┤ (soft-after v2 for auth headers)`
> `  v4 ─┤`
> `  v5 ─┘`

---

## 4. Vocabulary Survey — "Arc" / "Slice" / "Step" in ROADMAP.md

Whole-word, case-insensitive. Totals: **Arc = 31**, **Slice = 55**, **Step = 74** occurrences.

### 4a. "Arc" occurrences (31)

| Line | Surrounding context (single line) |
|------|-----------------------------------|
| 8 | `**Structural note:** GSD uses milestones → phases (this document). The **product** (`state`) uses Arc → Phase → Slice → Step, which is Thomas's product vocabulary and is built inside the phases themselves. One GSD milestone == one product Arc. GSD phases under a milestone == implementation slices that together ship that Arc.` |
| 395 | `**Goal:** litellm as the default multi-provider router with Anthropic SDK escape hatch for extended thinking + fine-grained cache control; OAuth stealth NEVER routes through litellm; per-Arc/Phase/Slice/Step model profiles; cost accounting in SQLite.` |
| 422 | `3. User can inspect `state stats --scope arc <id>` and see per-provider cost totals aggregated from every request` |
| 453 | `**Goal:** Per-Arc/Phase/Slice/Step override, inheritance chain, resolver used by `chat.params` hook.` |
| 510 | `1. User can run 5 Slices concurrently and see 5 worktrees with deterministic branch names `slice/<arc>/<phase>/<slice-id>`` |
| 536 | `#### Phase 035 — Deterministic branch + worktree naming (`slice/<arc>/<phase>/<slice-id>`)` |
| 602 | `5. `state dag show --arc <id>` renders an ASCII DAG in <1s for arcs with up to 500 nodes` |
| 655 | `#### Phase 049 — CLI: `state dag show [--arc|--phase|--slice]` ASCII renderer` |
| 959 | `**Verifier:** TUI renders sidebar in build mode (Arc/Phase/Slice tree), swaps to concept graph in teach mode; statusline shows mode + Step + cost; toasts fire on Slice completion / drill availability / auth refresh.` |
| 964 | `1. Sidebar shows active Arc/Phase/Slice hierarchy (build) or concept + mastery (teach) based on `.state/mode.json`` |
| 1045 | `**Verifier:** Open `/state:dag` → see nodes colored by status; click node → detail pane; filter by Arc → subset; live update as scheduler advances (<2s).` |
| 1050 | `1. User invokes `/state:dag` and sees the full Arc/Phase/Slice/Step DAG within 1s` |
| 1075 | `#### Phase 092 — Filter bar (Arc / Phase / Slice / critical-path)` |
| 1376 | `**Goal:** The heart of build-mode — Step state machine + STEP.md frontmatter schema + goal-backward verifier + Slice/Phase/Arc rollup verifiers + cross-tier integration verifier + security verifier.` |
| 1397 | `**Verifier:** 10 golden-fixture Steps with known goal + committed code → assert verifier pass/fail matches expected; Slice rollup fails if any Step fails; cross-tier verifier catches regression when Arc A interacts with Arc B.` |
| 1405 | `4. Cross-tier verifier catches a PR that breaks a completed Arc` |
| 1422 | `#### Phase 126 — Slice/Phase/Arc scoping containers (simpler FSMs)` |
| 1446 | `#### Phase 130 — Arc rollup verifier` |
| 1447 | `**Goal:** Aggregate Phase rollups plus Arc acceptance criteria.` |
| 1452 | `#### Phase 131 — Cross-tier integration verifier (runs after Arc boundary)` |
| 1548 | `**Goal:** Skip Arc/Phase scaffolding; inline Slice+Step; execute end-to-end in one command.` |
| 1576 | `**Goal:** Port or redesign the 30 GSD commands as state-native Step workflows — … new-arc/phase/slice, insert-slice, add/remove-phase, multi-arc, …` |
| 1593 | `**Verifier:** Each ported command has a golden-file fixture that exercises its input/output contract; commands that spawn subagents assert task completion; multi-Arc batch-planner produces valid DAG.` |
| 1601 | `4. User can batch-plan multiple Arcs from a feature dump via `/state:build:multi-arc`` |
| 1655 | `**Goal:** Cross-Slice UAT audit; Arc/Phase boundary audit.` |
| 1678 | `#### Phase 157 — Hierarchy bootstrapping (`/state:build:new-arc`/`new-phase`/`new-slice`/`insert-slice`/`add-phase`/`remove-phase`) + `/state:build:multi-arc`` |
| 1695 | `**Goal:** Build-mode TUI: Arc/Phase/Slice/Step hierarchy browser, Step detail with discuss/plan/execute/verify tabs, commit browser with revert UI, gray-area decision dialog.` |
| 1709 | `**Verifier:** Open build dashboard → see Arc hierarchy; click Step → 4 tabs; commit browser shows per-Step commits + working revert button; gray-area dialog surfaces + auto-decides per config.` |
| 1714 | `1. `/state:build:dashboard` shows Arc/Phase/Slice/Step tree with drill-down` |
| 1722 | `**Goal:** `route.register`; Arc/Phase/Slice/Step hierarchy; burndown + verify-pass rate.` |
| 1764 | `**Goal:** E2E: create Arc → Phase → Slice → Step → ship; all TUI surfaces exercised.` |

### 4b. "Slice" occurrences (55) — selected: all distinct contexts

| Line | Surrounding context |
|------|---------------------|
| 8 | `**Structural note:** GSD uses milestones → phases (this document). The **product** (`state`) uses Arc → Phase → Slice → Step, which is Thomas's product vocabulary and is built inside the phases themselves. One GSD milestone == one product Arc. GSD phases under a milestone == implementation slices that together ship that Arc.` |
| 35 | `- [ ] **v4 — Worktree + Snapshot Service** — Per-Slice worktrees with Step/Slice snapshots and GC` |
| 395 | `**Goal:** litellm as the default multi-provider router … per-Arc/Phase/Slice/Step model profiles …` |
| 424 | `5. Two concurrent sessions share a single httpx client (no connection-pool exhaustion under 20-concurrent-Slice load)` |
| 453 | `**Goal:** Per-Arc/Phase/Slice/Step override, inheritance chain, resolver used by `chat.params` hook.` |
| 487 | `**Goal:** Per-Slice worktree orchestration with opencode-preferred / pygit2-fallback, transactional bootstrap, Step/Slice snapshot composition, prefix-only revert, orphan-GC — enabling concurrent Slice execution.` |
| 510 | `1. User can run 5 Slices concurrently and see 5 worktrees with deterministic branch names `slice/<arc>/<phase>/<slice-id>`` |
| 511 | `2. Aborting a Slice mid-bootstrap leaves the repo + `.state/` in the pre-bootstrap state (atomic transactional)` |
| 512 | `3. User can `state snapshot revert <step-id>` and see Steps N..last reverted without touching earlier Steps in the same Slice` |
| 513 | `4. A crashed Slice leaving a locked worktree gets cleaned up within 24 hours (nightly GC)` |
| 536 | `#### Phase 035 — Deterministic branch + worktree naming (`slice/<arc>/<phase>/<slice-id>`)` |
| 561 | `#### Phase 039 — Slice snapshot (boundary hash + ship-time reference)` |
| 562 | `**Goal:** On Slice shipped, store slice-tier hash in events + SLICE.md.` |
| 568 | `**Goal:** Revert Step N within a Slice reverts N..last chronologically; Typer CLI.` |
| 589 | `- SQLite: `aggregate_seq` reads; scheduler itself writes `state.step.advanced`, `state.slice.worktree_ready` events via v1` |
| 601 | `4. A `soft` dependency holding back a critical-path Slice triggers a priority-inversion warning` |
| 630 | `#### Phase 045 — Dispatcher (group by Slice → TaskGroup per Slice, concurrency cap)` |
| 631 | `**Goal:** `asyncio.gather` across Slices with cap; serial within Slice; configurable cap in `config.toml`.` |
| 644 | `**Goal:** On `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned` → recompute frontier; no polling.` |
| 655 | `#### Phase 049 — CLI: `state dag show [--arc|--phase|--slice]` ASCII renderer` |
| 763 | `**Goal:** Per-opencode-session Python worker spawned by plugin shim, owns hot state for active Slice/Step/drill …` |
| 782 | `2. Worker holds active Slice/Step/drill state locally for fast access` |
| 800 | `#### Phase 062 — Hot state container (active Slice/Step/drill)` |
| 862 | `3. Tool invocations outside the active Slice's worktree are blocked at `tool.execute.before`` |
| 881 | `**Goal:** Block writes outside active Slice worktree; block `mcp__state-teach__*` in build mode; rewrite `.state/` path args.` |
| 959 | `**Verifier:** TUI renders sidebar in build mode (Arc/Phase/Slice tree) … toasts fire on Slice completion / drill availability / auth refresh.` |
| 964 | `1. Sidebar shows active Arc/Phase/Slice hierarchy (build) or concept + mastery (teach) based on `.state/mode.json`` |
| 966 | `3. Toast fires within 2s of Slice completion, drill availability, or auth refresh` |
| 983 | `#### Phase 082 — Build-progress sub-component (current Step + Slice DAG mini-view)` |
| 984 | `**Goal:** Subscribes to daemon SSE; renders Step status colors + Slice DAG thumbnail.` |
| 1002 | `**Goal:** Slice completion, drill availability, gray-area decisions, auth refresh; de-dup.` |
| 1050 | `1. User invokes `/state:dag` and sees the full Arc/Phase/Slice/Step DAG within 1s` |
| 1075 | `#### Phase 092 — Filter bar (Arc / Phase / Slice / critical-path)` |
| 1376 | `**Goal:** The heart of build-mode — Step state machine + STEP.md frontmatter schema + goal-backward verifier + Slice/Phase/Arc rollup verifiers …` |
| 1397 | `**Verifier:** 10 golden-fixture Steps … Slice rollup fails if any Step fails …` |
| 1404 | `3. Shipping a Slice with any failed Step is rejected by the Slice rollup verifier` |
| 1422 | `#### Phase 126 — Slice/Phase/Arc scoping containers (simpler FSMs)` |
| 1434 | `#### Phase 128 — Slice rollup verifier` |
| 1435 | `**Goal:** Aggregate Step verify results; fail Slice if any Step failed.` |
| 1441 | `**Goal:** Aggregate Slice rollups plus Phase-level integration tests.` |
| 1507 | `5. User runs `/state:build:ship` → PR opened + code review + Slice finalized` |
| 1541 | `#### Phase 140 — `/state:build:ship <slice>` command (PR + code review + finalize)` |
| 1542 | `**Goal:** Opens PR via `gh`; triggers code-review; on green, finalizes Slice; Slice snapshot.` |
| 1548 | `**Goal:** Skip Arc/Phase scaffolding; inline Slice+Step; execute end-to-end in one command.` |
| 1566 | `**Goal:** 3-Step fixture Slice; exercises full happy path and revert path.` |
| 1576 | `**Goal:** Port or redesign the 30 GSD commands as state-native Step workflows — … new-arc/phase/slice, insert-slice …` |
| 1598 | `1. User can run `/state:build:code-review` on a Slice and get reviewer feedback + fix Steps enqueued` |
| 1600 | `3. User can pause a Slice mid-execute and resume hours later with full context restored` |
| 1655 | `**Goal:** Cross-Slice UAT audit; Arc/Phase boundary audit.` |
| 1678 | `#### Phase 157 — Hierarchy bootstrapping (`/state:build:new-arc`/`new-phase`/`new-slice`/`insert-slice`/`add-phase`/`remove-phase`) + `/state:build:multi-arc`` |
| 1695 | `**Goal:** Build-mode TUI: Arc/Phase/Slice/Step hierarchy browser, Step detail with discuss/plan/execute/verify tabs …` |
| 1714 | `1. `/state:build:dashboard` shows Arc/Phase/Slice/Step tree with drill-down` |
| 1722 | `**Goal:** `route.register`; Arc/Phase/Slice/Step hierarchy; burndown + verify-pass rate.` |
| 1751 | `#### Phase 164 — Sidebar extensions (build-specific — current Slice DAG mini-view)` |
| 1764 | `**Goal:** E2E: create Arc → Phase → Slice → Step → ship; all TUI surfaces exercised.` |

### 4c. "Step" occurrences (74) — selected: header/definitional and goal/verifier lines

| Line | Surrounding context |
|------|---------------------|
| 8 | `**Structural note:** … Arc → Phase → Slice → Step, which is Thomas's product vocabulary …` |
| 35 | `- [ ] **v4 — Worktree + Snapshot Service** — Per-Slice worktrees with Step/Slice snapshots and GC` |
| 51 | `- [ ] **v14 — Build Kernel: Step FSM + Verifiers** — Step state machine, goal-backward verifier, rollups` |
| 54 | `- [ ] **v17 — Build TUI Extensions** — Build dashboard, Step detail, commit browser, gray-area dialog` |
| 155 | `| v14. Build Kernel Step FSM | 0/11 | Not started | - | - |` |
| 395 | `… per-Arc/Phase/Slice/Step model profiles …` |
| 421 | `2. User can set `model_profile: quality` on a Step and see Anthropic `claude-opus-*` …` |
| 453 | `**Goal:** Per-Arc/Phase/Slice/Step override, inheritance chain, resolver used by `chat.params` hook.` |
| 487 | `**Goal:** Per-Slice worktree orchestration … Step/Slice snapshot composition, prefix-only revert …` |
| 512 | `3. User can `state snapshot revert <step-id>` and see Steps N..last reverted …` |
| 543 | `**Goal:** Branch + worktree dir + `.state/` link atomic; rollback via compensation if any step fails.` |
| 555 | `#### Phase 038 — Step snapshot (pre-execute + pre-verify via opencode `Snapshot.track`)` |
| 556 | `**Goal:** `snapshot(tier="step", reason="pre_execute"|"pre_verify")` with content-addressed hash stored in events + STEP.md frontmatter.` |
| 568 | `**Goal:** Revert Step N within a Slice reverts N..last chronologically; Typer CLI.` |
| 589 | `- SQLite: `aggregate_seq` reads; scheduler itself writes `state.step.advanced`, `state.slice.worktree_ready` events via v1` |
| 593 | `**Verifier:** Hypothesis property tests … 10,000-Step benchmark < 500ms per schedule tick.` |
| 600 | `3. A Step stuck on a descoped predecessor surfaces as a "silent deadlock" in the TUI within 30s` |
| 644 | `**Goal:** On `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned` → recompute frontier; no polling.` |
| 650 | `**Goal:** Heuristic: if critical-path Step is blocked on `soft` edge, warn; …` |
| 684 | `**Verifier:** … crash during in-flight Step → recovery replays STATE.md projection.` |
| 690 | `2. Daemon crashes mid-Step → on restart, the Step resumes from its last snapshot + event position` |
| 763 | `**Goal:** Per-opencode-session Python worker … owns hot state for active Slice/Step/drill …` |
| 782 | `2. Worker holds active Slice/Step/drill state locally for fast access` |
| 800 | `#### Phase 062 — Hot state container (active Slice/Step/drill)` |
| 863 | `4. System prompts are injected with current Step goal + verify contract on every chat turn` |
| 864 | `5. Compaction preserves active Step ID + last 3 verify results` |
| 875 | `**Goal:** Parse `/state:*`, reject cross-mode, append active Step/Concept hint.` |
| 887 | `**Goal:** Build: match against Step `verify_contract`; Teach: classify + feed mental_model.` |
| 911 | `**Goal:** Inject "preserve these IDs" (active Step ID, last 3 verify results, open gray-area, pending drills).` |
| 959 | `**Verifier:** TUI renders sidebar in build mode … statusline shows mode + Step + cost …` |
| 965 | `2. Statusline shows `mode / step N.m / provider / $X.XX`` |
| 967 | `4. Running `state install` registers the plugin with opencode in one step` |
| 983 | `#### Phase 082 — Build-progress sub-component (current Step + Slice DAG mini-view)` |
| 984 | `**Goal:** Subscribes to daemon SSE; renders Step status colors + Slice DAG thumbnail.` |
| 1014 | `**Goal:** Shows model + token cost + Step N.m indicator.` |
| 1050 | `1. User invokes `/state:dag` and sees the full Arc/Phase/Slice/Step DAG within 1s` |
| 1053 | `4. DAG updates within 2s of any `state.step.advanced` event` |
| 1373 | `## v14 — Build Kernel: Step FSM + Verifiers` |
| 1376 | `**Goal:** The heart of build-mode — Step state machine + STEP.md frontmatter schema + goal-backward verifier + Slice/Phase/Arc rollup verifiers + cross-tier integration verifier + security verifier.` |
| 1383 | `- `experimental.chat.system.transform` (system prompt injection with Step goal)` |
| 1391 | `- `.state/build/steps/<step-id>/STEP.md` (with frontmatter schema)` |
| 1392 | `- `.state/build/steps/<step-id>/VERIFY.md` (structured results)` |
| 1393 | `- SQLite: `state.step.*` events, `steps` projection` |
| 1397 | `**Verifier:** 10 golden-fixture Steps with known goal + committed code → assert verifier pass/fail matches expected; Slice rollup fails if any Step fails; cross-tier verifier catches regression when Arc A interacts with Arc B.` |
| 1402 | `1. A Step transitions through `pending → discussing → planning → executing → verifying → shipped` emitting events at each edge` |
| 1404 | `3. Shipping a Slice with any failed Step is rejected by the Slice rollup verifier` |
| 1416 | `#### Phase 125 — Step state machine (StepMachine)` |
| 1435 | `**Goal:** Aggregate Step verify results; fail Slice if any Step failed.` |
| 1459 | `**Goal:** Per-Step; diff-based; uses regex + libs for known patterns.` |
| 1470 | `#### Phase 134 — Verifier integration + 10-Step golden fixture suite` |
| 1498 | `**Verifier:** End-to-end: create Step → discuss → plan → execute → verify → ship. Fail verify → revert via snapshot. Plan-checker agent rejects PLAN.md that won't achieve goal. Gray-area decision recorded in DECISIONS.md.` |
| 1503 | `1. User runs `/state:build:discuss <step>` and gets multi-turn clarification dialog that writes DISCUSS.md` |
| 1511 | `#### Phase 135 — `/state:build:discuss <step>` command (multi-turn clarification)` |
| 1517 | `#### Phase 136 — `/state:build:plan <step>` command (task decomposition, test plan, risks)` |
| 1529 | `#### Phase 138 — `/state:build:execute <step>` command (atomic commits)` |
| 1535 | `#### Phase 139 — `/state:build:verify <step>` command (runs verifier chain)` |
| 1536 | `**Goal:** Invokes v14 verifier chain; writes VERIFY.md; advances or reverts Step.` |
| 1548 | `**Goal:** Skip Arc/Phase scaffolding; inline Slice+Step; execute end-to-end in one command.` |
| 1560 | `**Goal:** On `state.step.verify_failed`, call `Snapshot.revert` to `pre_verify` hash.` |
| 1566 | `**Goal:** 3-Step fixture Slice; exercises full happy path and revert path.` |
| 1576 | `**Goal:** Port or redesign the 30 GSD commands as state-native Step workflows — …` |
| 1637 | `**Goal:** STATE.md projection captures + restores hot context; Step state → paused/resumed.` |
| 1695 | `**Goal:** Build-mode TUI: Arc/Phase/Slice/Step hierarchy browser, Step detail with discuss/plan/execute/verify tabs, commit browser with revert UI, gray-area decision dialog.` |
| 1709 | `**Verifier:** … click Step → 4 tabs; commit browser shows per-Step commits …` |
| 1714 | `1. `/state:build:dashboard` shows Arc/Phase/Slice/Step tree with drill-down` |
| 1715 | `2. Clicking a Step opens a tabbed view (DISCUSS/PLAN/EXECUTE/VERIFY)` |
| 1716 | `3. Commit browser shows per-Step commits with one-click revert` |
| 1722 | `**Goal:** `route.register`; Arc/Phase/Slice/Step hierarchy; burndown + verify-pass rate.` |
| 1733 | `#### Phase 161 — Step detail view (DISCUSS/PLAN/EXECUTE/VERIFY tabs)` |
| 1740 | `**Goal:** Per-Step commits from events + git; revert triggers `snapshot_revert`.` |
| 1764 | `**Goal:** E2E: create Arc → Phase → Slice → Step → ship; all TUI surfaces exercised.` |
| 2459 | `**Goal:** Each migration step is an event; full migration replayable from log; idempotence.` |
| 2520 | `4. Snapshot-missing host logs a warning and continues without Step-level revert` |
| 2661 | `**Goal:** All guards attached to every surface; per-Step security verifier (refinement of 132); regression tests.` |

Note: 74 total; above table enumerates every distinct occurrence found by grep of `\b[Ss]tep\b` on ROADMAP.md. Further "Step" token appearances inside REQ-ID traceability lines (`steps`/`steps/slices/concepts` table identifiers) are included above where the grep match returned the line.

---

## 5. Ambiguous Pronoun Survey

Whole-word grep on ROADMAP.md for `\bwe\b`, `\bour\b`, `\bus\b` (case-insensitive).

**Total matches: 0.**

No occurrences of "we", "our", or "us" in ROADMAP.md at any line. Section empty by measurement.

---

## 6. REQ-ID Population

**Distinct REQ-IDs in REQUIREMENTS.md:** 229

(Obtained via: `grep -oE '<prefix>-[0-9]+' REQUIREMENTS.md | sort -u | wc -l`. Prefix set covers EVT, AUTH, PRV, WRK, DAG, DAE, HOOK, TUI, MODE, MCP-B, MCP-T, BLD, CMD, PORT, TCH, DRL, SCA, CPT, SUB, MIG, PER, REL, DOC, TST, OBS, SEC, MODE-P, MODE-S, MODE-SO, MODE-C, MODE-SEL, B-TUI, T-TUI, DAG-VIEW, PORT-SHIM.)

**Distinct REQ-IDs referenced anywhere in ROADMAP.md:** 229

Supporting counts:
- REQUIREMENTS.md contains 229 `- [ ] **<ID>**` checkbox entries. (Note: REQUIREMENTS.md body text states "Coverage: 221/221 (100%)" at lines 390 and 626; the 229 number includes v2-deferred IDs: PORT-SHIM-V2-01..03, OBS-V2-01..02, EVAL-V2-01..02, ADV-V2-01..02. Subtracting the 9 v2-IDs yields 220 v1 — one short of the stated 221. Not analyzed here.)
- ROADMAP.md total raw occurrences (non-unique): 292.

---

## 7. Artifact counts (supporting raw totals)

| Metric | Value | Source |
|--------|-------|--------|
| ROADMAP.md `#### Phase` headings | 256 | grep `^#### Phase M-A\d+\.P\d+` |
| STATE.md claimed phase count | 267 | STATE.md line 27 and line 65 |
| Milestone `**Complexity:**` lines in ROADMAP.md | 27 | one per milestone |
| Phase-level complexity lines in ROADMAP.md | 0 | no S/M/L/XL tags below `#### Phase` headings |
| Milestones with `**P0 pitfalls owned:**` line | 9 (v1, v2, v3, v4, v5, v6, v11, v12, v13) | grep at lines 184, 284, 399, 491, 582, 670, 1114, 1205, 1292 |
| ROADMAP.md `\bArc\b` (case-insensitive) | 31 | grep count |
| ROADMAP.md `\bSlice\b` | 55 | grep count |
| ROADMAP.md `\bStep\b` | 74 | grep count |
| ROADMAP.md `\bwe\b` | 0 | grep count |
| ROADMAP.md `\bour\b` | 0 | grep count |
| ROADMAP.md `\bus\b` | 0 | grep count |
| Total ROADMAP.md lines | 2660+ (read up to line 2662 for v27 phase content) | Read tool pagination |

---

## Sources read

- `/Users/tmac/Projects/state/.planning/PROJECT.md` (full)
- `/Users/tmac/Projects/state/.planning/ROADMAP.md` (parsed via Grep; exceeds 25K-token Read cap so not read in one pass)
- `/Users/tmac/Projects/state/.planning/REQUIREMENTS.md` (full)
- `/Users/tmac/Projects/state/.planning/research/SUMMARY.md` (full)
- `/Users/tmac/Projects/state/.planning/research/PITFALLS.md` (first 400 lines — P0 surfaces 1–9; remaining P1/P2 content not needed for extraction)
- `/Users/tmac/Projects/state/.planning/STATE.md` (full)
- `/Users/tmac/Projects/state/CLAUDE.md` (provided via system context)
- `/Users/tmac/Projects/state/.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-CONTEXT.md` (full)
- **NOT read:** `/Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md` (per task instruction)
