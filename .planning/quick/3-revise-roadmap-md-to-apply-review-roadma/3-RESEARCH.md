# Quick Task 3 — ROADMAP Revision Edit-Coordinate Map (Research)

**Researched:** 2026-04-22
**Domain:** Pre-execution docs revision — applying REVIEW-ROADMAP findings to `.planning/ROADMAP.md` and `.planning/STATE.md`.
**Confidence:** HIGH (all line numbers verified against actual file contents; divergences from REVIEW flagged inline).

**Primary recommendation:** The REVIEW line numbers are largely accurate with two minor drifts (see §10). The planner can treat every coordinate below as ready-to-edit. ROADMAP is 2720 lines (REVIEW said 2660+ — stale by 60 lines, same content). Phase-count reality: `grep -c '^#### Phase' = 256`; Progress-Table column-sum = 256. STATE.md carries `267` in FOUR places, not two (§1 flags all four).

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fix both sides of cross-file MAJORs (STATE.md included).
- v16 = relabel only (no structural phase moves).
- v27 P0-14 owned line added; enumerate hard/soft depends-on at line 2578 and mirror at 2644/2650.
- Expand v11/14/20 verifiers (prefer explicit naming over P11-reference shortcut).
- Apply seven §2a domain-vocab sites (lines 8, 536, 1422, 1447, 1576, 1678, 1722).
- Split v2 goal+verifier; 132 rename; 187 reword (do NOT collapse).
- Add P0-test-matrix artifact bullet to 254.
- Thread P0-13 regression through 256.
- NIT §5b/§5c late-binding edges: defer with one-line TODO.

### Claude's Discretion
- "Shares" wording standardization — recommendation: add reciprocal shares (but research confirms only 2 sites use "shares" today, so fan-out is minimal).
- Changelog footer placement — recommendation: insert AFTER line 2720 (the existing `*Last updated:*` italic line), BEFORE the file EOF. No existing changelog/revision-history section found.

### Deferred Ideas (OUT OF SCOPE)
- Structural phase moves (v16 → v15).
- Source edits to `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/research/*`.
- Per-phase-level depends-on edge tightening across v11, v9, v17 (deferred as TODO).

---

## 1. Cross-file MAJORs (§5d phase-count; §5a parallel-safe)

### 1a. STATE.md — every "267" and parallel-safe overstatement

| Line | Current text (verbatim) | Target edit intent |
|------|--------------------------|---------------------|
| 26 | `**Phases complete:** 0 / 267` | Change `267` → `256`. |
| 42 | `All five Tier 1 milestones have zero predecessors and can run concurrently.` | Reword per REVIEW §5a option (a): "All five Tier 1 milestones can START concurrently; v3 soft-depends on v2 (auth creds for tests) and v5 hard-depends on v1 (reactive event stream)." Add footnote pointer to ROADMAP.md lines 396 + 579. |
| 58 | `\| Phases defined \| 267 \|` | Change `267` → `256`. |
| 65 | `\| Total v1 phases shipped \| 0 / 267 \|` | Change `267` → `256`. |
| 155 | `- `/Users/tmac/Projects/state/.planning/ROADMAP.md` — 27 milestones, 267 phases, DAG` | Change `267 phases` → `256 phases`. |

**Drift vs REVIEW:** REVIEW §5d cites lines 27 and 65 — actual line 27 is a blank line; the text is on line 26. Also REVIEW missed lines 58 and 155 — four sites total, not two. Planner must fix all four.

### 1b. ROADMAP.md — authoritative phase count

- `grep -c '^#### Phase' .planning/ROADMAP.md` → **256**.
- Progress Table (lines 142–167) column-sum arithmetic: 10+12+9+9+9+10+8+12+9+8+9+9+9+11+10+14+8+11+9+11+8+9+8+8+8+8+10 = **256**. ✅ matches grep.
- REVIEW's "256" claim is confirmed.

### 1c. ROADMAP.md — "267" sites to flip to 256

| Line | Current text (verbatim) | Target edit intent |
|------|--------------------------|---------------------|
| 17 | `\| Phases total \| **267** \|` | Change `**267**` → `**256**`. |
| 169 | `\| **TOTAL** \| **0/267** \| — \| — \| — \|` | Change `0/267` → `0/256`. |
| 2705 | `**Total:** 221 v1 requirements → 267 phases across 27 milestones. **Coverage: 100%.**` | Change `267 phases` → `256 phases`. |

(Scope at a Glance has no other 267; no 267 inside `#### Phase` bodies.)

### 1d. Milestone DAG code-block (REVIEW says ~76–83)

**Actual range: lines 76–104** (code fence opens at 76, closes at 104). The Tier 1 portion is lines 77–82:

```
Tier 1 (all independent; no edges between them):
  v1 ─┐
  v2 ─┤
  v3 ─┤ (soft-after v2 for auth headers)
  v4 ─┤
  v5 ─┘
```

Line 77 text `(all independent; no edges between them)` contradicts line 82 which draws the soft v5 edge. Planner edit intent: either (a) rewrite line 77's parenthetical to `(parallel-safe starts; v3 soft-after v2 for auth; v5 reacts to v1 events)`, OR (b) add an explicit `v1 ──► v5 (reactive)` edge and drop "all independent" language. Review suggests (a)-style.

### 1e. Parallel-Safe wave table (REVIEW says line 116)

Lines 114–127 show the table; line 116 is `W1 | v1, v2, v3, v4, v5`. Per CONTEXT.md decision: **split** into:

| Line to edit | Current | Target |
|--------------|---------|--------|
| 116 | `\| W1 \| v1, v2, v3, v4, v5 \|` | Replace with TWO rows: `\| W1 \| v1, v2, v4 \|` and `\| W2-prep \| v3 (after v2 creds), v5 (after v1 events) \|` — then renumber the existing W2 (line 117 `v6 (after A1+A2)`) up by one to W3, and so on through line 127. Alternatively, leave W2..W11 numbers and insert `W1-prep` / `W1` split — less disruptive; recommended pattern. |

Planner picks numbering scheme; both satisfy the review.

---

## 2. MAJOR #2 — v27 P0-14 ownership

| Line | Current text (verbatim) | Target edit intent |
|------|--------------------------|---------------------|
| 2574 | `## v27 — Release & Packaging` | (header, unchanged) |
| 2578 | `**Depends on:** most of v1..v24 (soft); v26 (cross-host verification)` | Replace with: `**Depends on:** v1, v8, v11, v12, v13, v14, v26 (hard); all other v1..v24 (soft — feature completeness)`. |
| *(insert after 2580)* | `**Complexity:** M` is at 2580; v27 has NO `**P0 pitfalls owned:**` line. | Insert new line after 2580: `**P0 pitfalls owned:** P0-14 (shared with v2 — release-time redactor regression in 255)`. |
| 2644 | `**Depends on:** v1..v26 (soft across all)` (253) | Same enumerate pattern: name the hard docs deps (v1, 247) + soft rest. |
| 2650 | `**Depends on:** all milestones (verifiers threaded in)` (254) | Replace with enumerated predecessors: all 27 milestones by ID + note that each milestone's verifier phase must be shipped before 254 runs. |
| 2654 | `#### Phase 255 — Observability finalization (structlog, redactor, event-log forensics, CLI `state logs tail`)` | Add one-line hand-off clause inside the phase body (e.g., in Goal at 2655): "… redactor regression re-runs here (P0-14 hand-off from 020 — release-time verification)." |
| 376 | `**P0 pitfall:** P0-14` (in 020 body) | Cross-reference only — unchanged, but new v27 ownership line must name 020 as the upstream implementor. |
| 2660 | `#### Phase 256 — Security baseline (path-traversal, prompt-injection, shell-meta, regex-DoS, JSON-bomb, chmod-0600 verifiers)` | Verifier phrasing at 2661 already says "chmod-0600 verifiers"; thread **P0-13** explicitly: change Goal line 2661 to add "…chmod-0600 verifier re-runs the P0-13 regression harness from 012…". |

### P0 regression existing inventory (context for 254 matrix — §8 below)

Milestone-level `**P0 pitfalls owned:**` lines: 9 sites — lines 184 (P0-9), 284 (P0-1..8, 13, 14), 399 (shares), 491 (P0-10), 582 (P0-16), 670 (P0-15), 1114 (P0-11), 1205 (P0-12), 1292 (shares P0-12). v27 currently has none — the new line at ~2581 makes it the 10th.

Phase-level `**P0 pitfall:**` tags: lines 325 (P0-13), 332 (P0-6, P0-7), 339 (P0-1..5, 7, 8), 376 (P0-14), 553 (P0-10), 641 (P0-16), 708 (P0-15), 1170 (P0-11). Eight phase-level tags. P0-9 at 007 (line 251) and P0-12 at 113 (line 1271) are named in the phase title/goal rather than with a `**P0 pitfall:**` frontmatter tag — inventory incomplete if only counting frontmatter lines.

---

## 3. MAJOR verifier expansions (§6)

### 3a. v11 (6 layers → 3 named)

| Line | Current text (verbatim) | Target |
|------|--------------------------|--------|
| 1110 | `**Goal:** Physical + runtime + static enforcement of the "exclusive modes" cardinal rule across disk, MCP registration, plugin hooks, command dispatch, daemon HTTP middleware (canonical), and Python import-graph lint.` | (unchanged — defines 6 layers) |
| 1128 | `**Verifier:** Switch mode from build→teach → build MCP server stopped, teach started within 3s; attempted `state.concept.observed` write while mode=build rejected at daemon; `state.build` importing `state.teach` fails CI.` | Expand to name all 6 layers: disk (098 — `.state/build/` vs `.state/teach/` directory-presence check), MCP registration (MCP start/stop <3s, ref 099), plugin hooks (100 — `command.execute.before` rejects cross-mode `/state:*`; `tool.execute.before` rejects cross-mode MCP invocation), command dispatch (same 100), daemon HTTP middleware (101 — canonical gate rejects `state.concept.*` when mode=build), Python import-graph lint (102 — CI fails on cross-mode imports). Reference 105 as the integrating P0-11 regression suite. Add test-harness reference for the `<3s` mode-switch SLO (success criterion #2 at line 1134). |

- **098** (disk) is at line 1147.
- **100** (plugin hooks) is at line 1159.
- **105** (cross-mode regression) is at line 1190.
- Success criterion #2 (`<3s` SLO) is at line 1134.

### 3b. v14 (6 verifier artifacts → 3 named)

| Line | Current text (verbatim) | Target |
|------|--------------------------|--------|
| 1376 | `**Goal:** The heart of build-mode — Step state machine + STEP.md frontmatter schema + goal-backward verifier + Slice/Phase/Arc rollup verifiers + cross-tier integration verifier + security verifier.` | (unchanged — defines 6 artifacts) |
| 1379 | `**Complexity:** XL` | (unchanged; confirmation that XL needs fuller verifier) |
| 1397 | `**Verifier:** 10 golden-fixture Steps with known goal + committed code → assert verifier pass/fail matches expected; Slice rollup fails if any Step fails; cross-tier verifier catches regression when Arc A interacts with Arc B.` | Expand to name all 6: Step FSM (125), goal-backward verifier (127), Slice rollup (128), product-Phase rollup (129), product-Arc rollup (130), cross-tier integration (131), and security verifier part-1 (132 — renamed in §6). Reference 134 as the integrating 10-Step golden-fixture suite. Per REVIEW note, name the synthetic Arc-A/B setup as a documented fixture requirement on the cross-tier assertion. |

- **129** (Phase rollup) is at line 1440.
- **130** (Arc rollup) is at line 1446.
- **132** (Security) is at line 1458.
- **134** (10-Step golden fixture suite) is at line 1470 (title: `Verifier integration + 10-Step golden fixture suite`).

### 3c. v20 (XL, 11 phases, 4 modes × selector × override × drop)

| Line | Current text (verbatim) | Target |
|------|--------------------------|--------|
| 1973 | `**Goal:** PRIMM, Scaffolded, Socratic, Constructivist modes as first-class state machines + mastery-based selector (PRIMM <30% → Scaffolded 30–50% → Socratic 50–70% → Constructivist 70–80%), manual override, drop-to-simpler.` | (unchanged) |
| 1976 | `**Complexity:** XL` | (unchanged) |
| 1993 | `**Verifier:** Each mode runs a full concept teach via its own state machine; selector picks correct mode at each mastery boundary; manual override sticks; drop-to-simpler triggered by frustration signal (175).` | Expand to 4 sub-clauses (one per mode FSM), selector boundary assertion, manual-override-sticks-until-cleared (193), drop-to-simpler on frustration (194), temperature injection per mode (195), per-mode system-prompt templates (196). Reference 197 (four-mode golden-fixture test) as the integrating test. |

- **193** (override) is at line 2042.
- **195** (temperature) is at line 2054.
- **196** (system-prompt templates) is at line 2060.
- **197** (golden fixture) is at line 2066.

---

## 4. v16 relabel (§3 v16, §2a line 1576)

| Line | Current text (verbatim) | Target |
|------|--------------------------|--------|
| 1573 | `## v16 — Build GSD Command Ports` | Rename to `## v16 — Build GSD Command Ports + Net-New Product-Hierarchy Commands`. |
| 53 (summary checklist) | `- [ ] **v16 — Build GSD Command Ports** — All 30 ported/redesigned GSD commands` | Mirror-rename + update tail phrase to reflect "ports + net-new scaffolding." |
| 1576 | `**Goal:** Port or redesign the 30 GSD commands as state-native Step workflows — code-review, intel, map-codebase, debug, forensics, pause/resume-work, thread, workstreams, stats, audit-uat, audit-milestone, docs-update, backlog/todos/notes, undo, ui-phase/review, autonomous, onboard/help, explore, brainstorm, scan, cleanup, reapply-patches, new-arc/phase/slice, insert-slice, add/remove-phase, multi-arc, review, set-quality/profile/settings, health, manager.` | Split into two sentences per REVIEW §2a: (1) "Ports of existing GSD commands: code-review, intel, map-codebase, debug, forensics, pause/resume-work, thread, workstreams, stats, audit-uat, audit-milestone, docs-update, backlog/todos/notes, undo, ui-phase/review, autonomous, onboard/help, explore, brainstorm, scan, cleanup, reapply-patches, review, set-quality/profile/settings, health, manager." (2) "Net-new product-hierarchy commands (no GSD equivalents): new-arc, new-phase (product-Phase tier), new-slice, insert-slice, add-phase, remove-phase, multi-arc." |
| 1593 | `**Verifier:** Each ported command has a golden-file fixture that exercises its input/output contract; commands that spawn subagents assert task completion; multi-Arc batch-planner produces valid DAG.` | Split into 3 classes per CONTEXT decision: (a) file-emitter commands → golden-file assertion; (b) subagent-spawning commands (code-review, intel, forensics, debug, map-codebase) → task-completion assertion; (c) batch/DAG commands (multi-arc, insert-slice, add-phase, remove-phase) → DAG-validity assertion. |
| 1678 | `#### Phase 157 — Hierarchy bootstrapping (`/state:build:new-arc`/`new-phase`/`new-slice`/`insert-slice`/`add-phase`/`remove-phase`) + `/state:build:multi-arc`` | Keep heading; add/keep v16 milestone-level disambiguator (one paragraph after the renamed header) stating "commands named `new-phase`/`add-phase`/`remove-phase` operate on the product-Phase tier, NOT GSD phases." Covered by the relabel + disambiguator rather than renaming commands. |

---

## 5. Domain-vocab MINOR batch §2a

| Line | Current text (verbatim) | Surrounding context | Edit intent |
|------|--------------------------|----------------------|-------------|
| 8 | `**Structural note:** GSD uses milestones → phases (this document). The **product** (`state`) uses Arc → Phase → Slice → Step, which is Thomas's product vocabulary and is built inside the phases themselves. One GSD milestone == one product Arc. GSD phases under a milestone == implementation slices that together ship that Arc.` | Frontmatter; lines 6–8 are granularity/parallel/structural-note; line 10 is `---`. Single-line paragraph. | Reword final sentence per CONTEXT: "A GSD phase DELIVERS capability into one or more product-runtime Slices — but is not itself a Slice object in `.state/`." |
| 536 | `#### Phase 035 — Deterministic branch + worktree naming (`slice/<arc>/<phase>/<slice-id>`)` | Phase heading (line 536) + Goal line 537 (single sentence); depends_on at 538. | Rename path segment `<phase>` → `<product-phase-id>`. Heading becomes `slice/<arc-id>/<product-phase-id>/<slice-id>` (also rename `<arc>` → `<arc-id>` for symmetry). Fan-out check: only one other site has `<phase>` in branch-naming context: **line 510** (Success criterion #1: `…deterministic branch names `slice/<arc>/<phase>/<slice-id>``). Both must be edited in lockstep. Line 2711 uses `<phase>` but as a CLI argument metavariable (`/gsd:plan-phase <milestone> <phase>`) — DIFFERENT meaning (GSD-phase literal); leave alone. |
| 1422 | `#### Phase 126 — Slice/Phase/Arc scoping containers (simpler FSMs)` | Heading (1422), Goal (1423 `planned → in_progress → shipped \| abandoned`), Depends on (1424), Req (1425), Parallelizable (1426). | Prefix with `Product-`: heading becomes `#### Phase 126 — Product Slice/Phase/Arc scoping containers (simpler FSMs)`. |
| 1447 | `**Goal:** Aggregate Phase rollups plus Arc acceptance criteria.` | Inside 130 body (heading at 1446 `Arc rollup verifier`; Goal 1447; Depends 1448; Req 1449). | Prefix product-tier tokens on first mention: `**Goal:** Aggregate product-Phase rollups plus product-Arc acceptance criteria.` Also prefix the heading at 1446 → `Product-Arc rollup verifier`. |
| 1576 | `**Goal:** Port or redesign the 30 GSD commands … (full list) … health, manager.` | v16 goal — 1-paragraph long sentence. | Already covered by §4 (v16 relabel) — split sentence. |
| 1678 | `#### Phase 157 — Hierarchy bootstrapping (`/state:build:new-arc`/`new-phase`/`new-slice`/`insert-slice`/`add-phase`/`remove-phase`) + `/state:build:multi-arc`` | Heading only; goal at 1679; depends at 1680. | Add one-line disambiguator at v16 header per §4; heading itself stays (renaming commands `new-phase` → `new-product-phase` is scope creep per CONTEXT decision). |
| 1722 | `**Goal:** `route.register`; Arc/Phase/Slice/Step hierarchy; burndown + verify-pass rate.` | 159 goal (heading 1721; goal 1722; depends 1723; req 1724). | Add inline gloss: `**Goal:** `route.register`; product Arc/Phase/Slice/Step hierarchy (product-tier); burndown + verify-pass rate.` |

**Fan-out grep for `<phase>` in branch-naming contexts:** only **lines 510 and 536** match. Line 2711 is a CLI metavariable for `/gsd:plan-phase` — not branch-naming; do NOT rename. REVIEW §2a only named 536 — line 510 fan-out is a research-surfaced add (planner should batch both in one edit).

---

## 6. v2 / v3 / 132 MINOR batch

| Line | Current text (verbatim) | Target |
|------|--------------------------|--------|
| 280 | `**Goal:** All five auth methods ship day one with chmod-0600 vault, filelock-guarded refresh, multi-cred round-robin, captured-header regression tests, and zero token leakage to logs — unblocking the Anthropic Pro/Max primary audience.` | Split into 3 clauses per CONTEXT: (1) "Five auth methods operational day one (Anthropic OAuth stealth, Gemini CLI, Antigravity, Copilot device-code, plain API-key)." (2) "Refresh safety + redaction + 0600 enforced (filelock-guarded concurrent refresh, structlog root-logger token redactor, chmod-0600 vault verified on every read)." (3) "Multi-cred fan-out (round-robin across per-provider credential arrays; rate-limit rotation)." |
| 282 | `**Tier:** 1` — but REVIEW cites 282 as verifier. Actual verifier is **line 301**. | **DRIFT: REVIEW §3 v2 says verifier is at line 282 — incorrect.** Real line 301: `**Verifier:** Captured-header regression test (httpx transport mock) for every stealth request; P0 regression test suite (9 tests: P0-1..P0-8 + P0-13); 0600 verification on every read; refresh-lock double-check with concurrent-process harness.` Split to mirror the 3-clause goal: (1) captured-header regression for all 5 methods; (2) P0 regression suite (9 tests: P0-1..P0-8 + P0-13) + 0600 verifier + redactor golden-file; (3) concurrent-refresh filelock double-check harness. |
| 399 | `**P0 pitfalls owned:** (shares P0-1/2/3 with v2 via stealth bypass guard)` | Claude's Discretion per CONTEXT; recommended: **standardize by adding reciprocals**. Since only TWO sites use "shares" (line 399 and line 1292), fan-out is small. Reciprocal additions needed: (a) v2 owns P0-1/2/3 primarily (already named at 284); v3's "shares" line is consistent. (b) v13 line 1292 `**P0 pitfalls owned:** P0-12 (shared with v12)` is reciprocal to v12's line 1205 `**P0 pitfalls owned:** P0-12` — v12 should add `(shared with v13)`. (c) NEW v27 ownership line (§2) uses `(shared with v2 — release-time redactor regression)` — consistent wording. Net: if standardizing, only the v12 line 1205 needs reciprocal fan-out. Alternative "drop shares" path: edit 399 to `(none — P0-1/2/3 primary-owned by v2; v3 provides stealth bypass guard per PRV-03)` and delete `(shared with v12)` from line 1292. |
| 1292 | `**P0 pitfalls owned:** P0-12 (shared with v12)` | Either: keep + add reciprocal `(shared with v13)` to line 1205; OR drop `(shared with v12)` and rely on v12 owning P0-12 primarily. |
| 1205 | `**P0 pitfalls owned:** P0-12 (MCP tool-name collision)` | (IF standardize path): append ` (shared with v13)`. |
| 1458 | `#### Phase 132 — Security verifier (SQLi, path traversal, secret leak, shell meta)` | Rename to signal 256 hand-off: `#### Phase 132 — Security verifier (part 1 — input guards: SQLi, path traversal, secret leak, shell meta)`. 256 body line 2661 already describes itself as "refinement of 132"; the rename makes the hand-off explicit from the v14 side. |

---

## 7. 187 reframing (line 2006)

| Line | Current text (verbatim) | Target |
|------|--------------------------|--------|
| 2006 | `#### Phase 187 — Mode runtime factoring decision + shared plumbing (v18 refinement)` | Rename heading: `#### Phase 187 — Shared plumbing implementation (SUMMARY Q2 resolution — hosted in v18 kernel)`. |
| 2007 | `**Goal:** Resolve SUMMARY Q2 — shared selector/drop/Kolb/observation emission in v18 kernel; modes consume. (Per roadmapper judgment: shared-in-kernel.)` | Reword to drop "Resolve" / "decision" framing: `**Goal:** Implement shared plumbing (selector + drop-to-simpler + Kolb + observation emission) hosted in v18 kernel; four modes (P2–P5) consume. SUMMARY Q2 decision already resolved — this phase is scaffolding, not discussion.` |
| 2008 | `**Depends on:** 177` | (unchanged) |
| 2009 | `**Requirements:** (infrastructure)` | (unchanged; valid tag) |
| 2010 | `**Parallelizable:** no` | (unchanged) |

**STATE.md line 92 resolution text (read-only confirmation):** `2. **Mode-runtime factoring** — resolved: shared plumbing in v18 kernel (Q2, per 187).` ✓ Matches — decision is closed at roadmap time; the P1 reword aligns with this record.

---

## 8. 254 P0-test matrix

| Line | Current text (verbatim) | Target |
|------|--------------------------|--------|
| 2648 | `#### Phase 254 — Full test infrastructure + P0 regression suite (all 16 pitfalls)` | (heading unchanged) |
| 2649 | `**Goal:** pytest + pytest-asyncio (strict_asyncio), Hypothesis property tests, E2E opencode fixture, provider parity matrix, captured-header regression, mode-isolation import-graph, P0 regression tests.` | Append artifact bullet: "Artifact: `.state/build/p0-test-matrix.md` mapping each P0-ID (P0-1..P0-16) → upstream regression-test path + owning milestone/phase." |
| 2650 | `**Depends on:** all milestones (verifiers threaded in)` | Covered by §2 — enumerate. |
| 2651 | `**Requirements:** TST-01, TST-02, TST-03, TST-04, TST-05, TST-06, TST-07, TST-08` | (unchanged — TST-08 is the P0-matrix tie-in; see REQUIREMENTS.md line 321: `TST-08: P0 regression tests — one test per P0 pitfall in PITFALLS.md`) |
| 2652 | `**Parallelizable:** yes` | (unchanged) |
| 2601 | `4. All 16 P0 pitfalls have regression tests (TST-08) — green` | Add cross-reference: `… — green; see P0-test matrix at `.state/build/p0-test-matrix.md`.` |

**TST-08 context (REQUIREMENTS.md line 321, read-only):**
`- [ ] **TST-08**: P0 regression tests — one test per P0 pitfall in PITFALLS.md`

Traceability row for TST-08 at REQUIREMENTS.md line 612: `TST-08 | v27 | 254 + 105 | Pending` — already shows 105 as an integrating site (the P0-11 regression suite). The new artifact extends that per-ID traceability.

**Full P0 inventory for the new matrix (per ROADMAP grep in §2):**
- P0-1..P0-8: 022 (line 385, aggregated) + phase-level tags at 339 (P0-1..5, 7, 8), 332 (P0-6, P0-7)
- P0-9: 007 (line 251)
- P0-10: 037 (line 553)
- P0-11: 105 (line 1190) + phase tag line 1170
- P0-12: 113 (line 1271) + phase tag absent for v13 (inferred from v13.P? — not tagged in frontmatter; gap noted)
- P0-13: 012 (line 325) + 022 aggregate
- P0-14: 020 (line 376) + new 255 hand-off
- P0-15: 051 (line 708)
- P0-16: 046 (line 641)

Planner note: 16 P0s claimed; grep of owner frontmatter finds 10 explicit phase-level tags + 2 aggregate lines (022 line 385, 105 line 1191). P0-12 on v13 side lacks a frontmatter tag — the matrix should either add it or explicitly note v13 defers P0-12 coverage to 113.

---

## 9. Changelog footer decision

**Grep result:** No existing `Changelog`, `Revision history`, `CHANGELOG`, or revision-table section in ROADMAP.md. Only footer artifacts are:

| Line | Text |
|------|------|
| 2717 | `---` (final section break) |
| 2719 | `*Roadmap created: 2026-04-22*` |
| 2720 | `*Last updated: 2026-04-22 after initial creation*` |

**Recommended placement:** Insert a new `## Revision History` section BETWEEN line 2717 (final `---`) and line 2719, or update line 2720 text and add a new dated bullet below it. Prefer the former — adds a proper section rather than mutating italic credits. Sketch:

```
## Revision History

- **2026-04-22 (quick-task-3):** Applied REVIEW-ROADMAP.md findings — cross-file phase-count 267→256, Tier-1 parallel-safe accuracy, v27 P0-14 ownership, v11/14/20 verifier expansions, v16 relabel, §2a domain-vocab batch, 187 reword, 254 matrix artifact. See `.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/` for the per-finding trace.
```

---

## 10. Risk notes

### 10a. Parsers reading ROADMAP frontmatter

- **GSD `roadmap.cjs:164`** regex: `\*\*Depends on:\*\*\s*([^\n]+)` — extracts the single-line depends_on verbatim. Enumerating the list at line 2578 (from `most of v1..v24 (soft); v26 (cross-host verification)` to `v1, v8, v11, v12, v13, v14, v26 (hard); all other v1..v24 (soft)`) stays within one line — **parser-safe**. Same for 2644 and 2650.
- **GSD phase-heading regex** (same file, line 146): `/#{2,4}\s*Phase\s+(\d+[A-Z]?(?:\.\d+)*)\s*:\s*([^\n]+)/gi` — expects `Phase N:` format. This ROADMAP uses `Phase 001 —` (no colon, `M-A` prefix) so the GSD parser already does **not** match this ROADMAP's phase headings. No regression risk from any heading rename here.
- **GSD `phase.cjs:699`** also looks for `Depends on:** Phase N` — same non-matching format (ROADMAP uses `001`, not bare `N`). Safe.

### 10b. REVIEW line-drift vs reality

| REVIEW claim | Actual | Severity |
|--------------|--------|----------|
| "ROADMAP.md (2660+ lines)" (§ top) | 2720 lines | low — "+" qualifier is inclusive |
| "STATE.md line 27 (`Phases complete: 0 / 267`)" (§5d) | Line **26** (line 27 is blank) | **DRIFT — planner use line 26** |
| "v2 verifier at line 282" (§3 v2) | Line **301** (282 is `**Tier:** 1`) | **DRIFT — planner use line 301** |
| "187 at line 2006" (§3 v20, §4) | Line 2006 ✓ | no drift |
| "134 (10-Step golden fixture) — find the exact line" (focus §3) | Line **1470** | resolved |
| "Milestone DAG code block (~76–83)" (focus §1) | Actual block is 76–104; Tier-1 portion 77–82 | minor |
| "v3 line 396 soft-dep" (§5a) | ✓ confirmed | no drift |
| "v5 line 579 hard-dep" (§5a) | ✓ confirmed | no drift |
| "v27 depends-on line 2578" (§5c) | ✓ confirmed | no drift |
| "253 line 2644, 254 line 2650" (§5c) | ✓ confirmed | no drift |
| "132 line 1458" (§4 coverage) | ✓ confirmed | no drift |
| "255 line 2654, 256 line 2660" (§3 v27) | ✓ confirmed | no drift |
| "P0-14 tag at 020 line 376" (§3 v27) | ✓ confirmed | no drift |

### 10c. Other edit-time risks

- **STATE.md fan-out:** REVIEW mentions two 267 sites (lines 27, 65). Reality is FOUR (lines 26, 58, 65, 155). Planner must grep STATE.md for `267` to catch all.
- **ROADMAP fan-out for `<phase>` in branch-naming:** REVIEW mentions only line 536. Reality: lines 510 AND 536 both carry `slice/<arc>/<phase>/<slice-id>` in branch-naming contexts. Planner must batch both.
- **v16 relabel touches the Summary Checklist at line 53** — REVIEW names only the milestone header at 1573 but the checklist at line 53 carries the old name "Build GSD Command Ports". Both edits required for consistency.
- **§5a wave-table edit is renumber-sensitive** — inserting a new W-row shifts W2..W11 labels OR not, planner's choice (§1e). Renumber-less insertion (W1 split into two sub-rows) is lower-blast-radius.
- **No existing `P0 pitfalls owned:**` line on v27** — the insert point after line 2580 (`**Complexity:** M`) is a new line; confirm no blank-line convention violation.
- **No ROADMAP-aware awk phase-counter in GSD toolchain** — `grep -rn "#### Phase" ~/.claude/get-shit-done/` found only a template file (`templates/roadmap.md:171`), no parser. The GSD phase parser regex doesn't match this format anyway (§10a). No downstream tooling blast-radius from phase-count edits beyond STATE.md's internal tracking.

---

## Sources

- `/Users/tmac/Projects/state/.planning/STATE.md` (full, re-read)
- `/Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md` (full, 227 lines)
- `/Users/tmac/Projects/state/.planning/ROADMAP.md` (2720 lines; read sections 1–200, 275–415, 530–545, 1107–1306, 1373–1571, 1573–1732, 1970–2075, 2574–2721; grep-verified phase headings and P0 tags)
- `/Users/tmac/Projects/state/.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/3-CONTEXT.md` (full, locked decisions)
- `/Users/tmac/Projects/state/.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md` (full, evidence cache)
- `/Users/tmac/Projects/state/.planning/REQUIREMENTS.md` (TST-08 at line 321; TST-08 traceability at line 612 — read-only reference)
- `/Users/tmac/.claude/get-shit-done/bin/lib/roadmap.cjs` (parser regex; line 146 + line 164)
- `/Users/tmac/.claude/get-shit-done/bin/lib/phase.cjs` (phase-level depends-on regex; line 699)
- `/Users/tmac/.claude/get-shit-done/templates/roadmap.md` (only template match for `#### Phase`; no runtime parser)

---

*Research complete: 2026-04-22 (quick-task-3 pre-planning)*
