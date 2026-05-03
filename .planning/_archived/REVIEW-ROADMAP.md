# REVIEW: ROADMAP.md — Pre-Execution Audit

**Date:** 2026-04-22
**Reviewer stance:** skeptical senior engineer; independent pass (prior `REVIEW-ROADMAP.md` deliberately NOT read — file was removed before this write to avoid pollution)
**Primary target:** `.planning/ROADMAP.md` (2660+ lines, 27 milestones)
**Secondary targets:** `CLAUDE.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/research/{PITFALLS,SUMMARY}.md`, `.planning/STATE.md`
**Evidence cache:** `.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md`

**Severity legend**
- `[BLOCKER]` — must fix before first phase kicks off; execution will derail without it
- `[MAJOR]` — real correctness or scope risk; fix before closing the milestone owning it
- `[MINOR]` — clarity / consistency nick; fix opportunistically
- `[NIT]` — cosmetic

---

## 1. Executive Summary

- **Health call: concerning but not blocker-present.** No single finding derails day-one execution, but three MAJORs (phase-count mismatch, shared P0-14 co-ownership gap, under-constrained parallel-safe claim) should be resolved before the first milestone kickoff.
- **Domain hygiene: MAJOR.** HERE/THERE boundary is largely clean because the roadmap sticks to `.state/*` artifacts — but the Arc/Phase/Slice/Step (product) vs Milestone/Phase (GSD) conflation leaks into several phase titles, goal lines, and the runtime branch-naming scheme (see §2a). The `**Structural note:**` at ROADMAP.md line 8 holds the line but is not enforced downstream.
- **DAG / parallelization: MAJOR.** STATE.md line 42 asserts "All five Tier 1 milestones have zero predecessors and can run concurrently" — this contradicts ROADMAP.md line 396 (v3 soft-depends on v2) and line 579 (v5 hard-depends on v1). Either STATE.md needs a footnote or the parallel-safe wave table (ROADMAP.md line 116) needs sequencing hints.
- **Coverage / P0 ownership: MAJOR.** P0-14 (plaintext token leak on debug=true) is owned only by v2 (line 284), yet PITFALLS.md maps it to both "Auth Arc and Observability Arc." v27 owns the Observability surface (255 line 2654) but has no `**P0 pitfalls owned:**` line at all — shared ownership is not mirrored where the release-time redactor regression actually lives. Also: REQUIREMENTS.md line 390 claims "221/221 (100%)" but the file contains 229 distinct REQ-IDs (9 v2-deferred → 220 v1, one short of 221).
- **Verifier-vs-goal alignment: MINOR.** v11 (6-layer mode isolation) has a three-layer verifier at line 1128; v20 (XL, 11 phases, 4 modes × selector × override × drop-to-simpler) is covered by a single `**Verifier:**` line at 1993; v14 (XL, 6 verifier artifacts claimed) has a verifier (line 1397) that names only 3 of them. See §6.

**Findings: 0 blocker, 7 major, 13 minor, 6 nit.**

---

## 2. Domain Confusion Findings

Confusion categories audited:
- **(a) Arc/Phase/Slice/Step vs GSD Milestone/Phase** — product runtime vocabulary vs repo planning vocabulary. One GSD milestone == one product Arc; they are NOT synonyms. *(new-in-this-pass dimension)*
- **(b) HERE vs THERE** — HERE is the build env (Claude Code + GSD + `.planning/` + `main` branch). THERE is the product (Python `state` engine, opencode plugin, two MCP servers, `.state/` tree, `events.sqlite`) — none of which exists yet.

Toolchain deps (Python 3.12+, pytest, uv, pygit2, typer, rich, etc.) are deliberately excluded from this scan per CONTEXT.md §specifics — they are HERE-resident tools that build the THERE product and are not confusion.

### 2a. Arc/Phase/Slice/Step vs GSD Milestone/Phase

This is the dimension newly called out for this pass. The ROADMAP uses Arc/Phase/Slice/Step 31/55/74 times respectively (per 2-RESEARCH §4); the structural note at ROADMAP.md line 8 tries to disambiguate, but several downstream sites leak the collision.

| Severity | File | Line(s) | Quoted Text | Why It's Confused | Suggested Rewrite (sketch) |
|---|---|---|---|---|---|
| `[MINOR]` | ROADMAP.md | 8 | `GSD phases under a milestone == implementation slices that together ship that Arc.` | Defines GSD-phase == product-Slice — a mapping, not an equivalence. A GSD phase is a planning container here; a product Slice is a runtime scoping container with its own worktree (v4). Merging them in the structural note makes downstream phase titles like `035 — … naming (slice/<arc>/<phase>/<slice-id>)` (line 536) read as if the planning-"phase" and runtime-"<phase>" are the same thing. | Reword: "A GSD phase DELIVERS capability into one or more product-runtime Slices — but is not itself a Slice object in `.state/`." |
| `[MINOR]` | ROADMAP.md | 536 | `#### Phase 035 — Deterministic branch + worktree naming (`slice/<arc>/<phase>/<slice-id>`)` | The runtime branch path component `<phase>` is a product Phase tier, but the heading containing it is a GSD Phase (`035`). Double-meaning of "phase" in one line. | Rename the runtime path segment to `<product-phase-id>`, e.g. `slice/<arc-id>/<product-phase-id>/<slice-id>`. |
| `[MINOR]` | ROADMAP.md | 1422 | `#### Phase 126 — Slice/Phase/Arc scoping containers (simpler FSMs)` | Good intent (defines three smaller FSMs) but reads ambiguously: is "Phase" here the GSD phase we're executing (126), or the product's Phase tier? Context makes it the latter, but the bare word inside a `#### Phase` heading invites a double-take. | `Product Slice/Phase/Arc scoping containers (simpler FSMs)`. |
| `[MINOR]` | ROADMAP.md | 1678 | `#### Phase 157 — Hierarchy bootstrapping (`/state:build:new-arc`/`new-phase`/`new-slice`/`insert-slice`/`add-phase`/`remove-phase`) + `/state:build:multi-arc`` | Same collision: commands named `new-phase`/`add-phase`/`remove-phase` operate on the PRODUCT Phase tier; the `#### Phase 157` header uses "Phase" in the GSD sense. Fourteen tokens in, the reader has parsed "Phase" in two different meanings. | Either rename the commands to `new-product-phase` etc., or add a one-line disambiguator at the top of v16 saying "commands named `*-phase` operate on the product's Phase tier, not GSD phases." |
| `[MINOR]` | ROADMAP.md | 1576 | `**Goal:** Port or redesign the 30 GSD commands as state-native Step workflows — … new-arc/phase/slice, insert-slice, add/remove-phase, multi-arc …` | Goal claims these are ports of 30 *GSD* commands — but `new-arc`, `new-phase`, `new-slice`, `multi-arc` are product-domain commands that don't exist in GSD (GSD has no Arcs or Slices). Conflates a port with net-new product-hierarchy scaffolding. | Split the sentence: "Ports: code-review, intel, map-codebase, …" + "Net-new product-hierarchy commands: new-arc, new-phase, new-slice, insert-slice, multi-arc." |
| `[MINOR]` | ROADMAP.md | 1447 | `**Goal:** Aggregate Phase rollups plus Arc acceptance criteria.` (130 "Arc rollup verifier") | "Phase rollups" here is the product Phase, not this doc's phase. A first-time reader at line 1447 has to look up-context 20 lines to disambiguate. | Prefix with "product-" on every first mention inside a phase body: "Aggregate product-Phase rollups…". |
| `[MINOR]` | ROADMAP.md | 1722 | `**Goal:** `route.register`; Arc/Phase/Slice/Step hierarchy; burndown + verify-pass rate.` (159) | Short goal with the full 4-tier product vocabulary crammed in; fine for builders but inscrutable to a new reader unless they've internalized the note at line 8. | Add inline gloss on first product-tier mention in each milestone: `Arc/product-Phase/Slice/Step`. |
| `[NIT]` | STATE.md | 14 | `**Planning hierarchy:** Arc → Phase → Slice → Step (product); Milestone → Phase (GSD)` | This line is correct and useful — the cleanest elevator explanation in the entire project. | (no rewrite — positive reference; cross-link from ROADMAP.md line 8.) |
| `[NIT]` | CLAUDE.md | 48–49 | `- Product planning hierarchy: **Arc → Phase → Slice → Step** …` / `- GSD planning hierarchy (this repo's `.planning/`): milestones → phases. One GSD milestone = one product Arc.` | CLAUDE.md holds the line correctly. | (no rewrite — positive reference.) |

**CLAUDE.md scan: clean** — reserves "Arc → Phase → Slice → Step" to the product (line 48) and "milestones → phases" to GSD (line 49) without collision.

### 2b. HERE vs THERE (build env vs product)

| Severity | File | Line(s) | Quoted Text | Why It's Confused | Suggested Rewrite (sketch) |
|---|---|---|---|---|---|
| `[MINOR]` | ROADMAP.md | 103 | `most-of-v1..v24  ──► v27` (in Milestone DAG code block) | "most-of" is colloquial for a DAG edge; in a DAG you either have the edge or you don't. This is HERE-repo casual language leaking into what reads as a machine-readable dependency diagram. | Enumerate the hard edges explicitly; downgrade the rest to a comment. |
| `[MINOR]` | ROADMAP.md | 2578 | `**Depends on:** most of v1..v24 (soft); v26 (cross-host verification)` (v27) | Same issue in the primary `**Depends on:**` slot — a scheduler (v5) cannot compute a deterministic frontier for v27. | Replace with an explicit enumeration of soft-deps plus a hard-deps list. |
| `[MINOR]` | ROADMAP.md | 6 vs 103 | `**Granularity:** fine (research/config.json)` (line 6) vs `most-of-v1..v24` (line 103) | Frontmatter advertises "fine" granularity, but the DAG uses coarse-grained natural-language edges for Tier 4. Fine granularity should imply explicit edges. | Tighten v25..v27 depends-on lines. |
| `[NIT]` | ROADMAP.md | 2644, 2650 | `**Depends on:** v1..v26 (soft across all)` (253) / `**Depends on:** all milestones (verifiers threaded in)` (254) | Same pattern, at phase level. | Same fix. |

No BLOCKER or MAJOR HERE/THERE confusion found — the roadmap consistently scopes `.state/`, `events.sqlite`, `state-build`/`state-teach` MCP to the THERE product; and `.planning/`, `main` branch, GSD commands, Claude Code hooks to the HERE env. PROJECT.md cardinal rules (lines 84–103) hold the line.

---

## 3. Per-Milestone Findings

Only milestones with findings appear. No-findings milestones (v1, v4, v5, v6, v7, v8, v9, v10, v12, v13, v15, v17, v18, v19, v21, v22, v23, v24, v25, v26) are omitted.

### v2 — Auth Coverage (5 Methods + Multi-Cred) `[MINOR]`

- `[MINOR]` Goal at ROADMAP.md line 280 packs ~ten capabilities into one sentence (five auth methods + multi-cred + refresh + redaction + 0600 + chmod verify + filelock). Verifier at line 282 is itself a compound ("captured-header regression + 9 P0 tests + 0600 verify + concurrent-refresh harness"). Split the goal into (1) five auth methods operational, (2) refresh + redaction + 0600 enforced, (3) multi-cred fan-out.
- `[MINOR]` Success criteria at line 309 ("Turning on debug logging does NOT leak any `sk-ant-*` / `sk-*` / `ya29.*` tokens") is testable, but phase 255 (line 2654) re-implements the redactor — ownership of the redactor is split across 020 (P0-14 tag, line 376) and 255 without a clear hand-off.

### v3 — Provider Routing + Model Profiles `[MINOR]`

- `[MINOR]` Line 399: `**P0 pitfalls owned:** (shares P0-1/2/3 with v2 via stealth bypass guard)` — v3 is the only milestone that uses "shares" inline while actually owning nothing directly. Contrast v13 line 1292 (shares P0-12 with v12) — similar wording, actually reciprocates with v12 line 1205. Convention is inconsistent: P0-14 (mapped by PITFALLS to Auth + Observability) has no reciprocal "shares" clause on v27's side. Either enforce "shares" everywhere or drop it from v3/v13.

### v11 — Mode Enforcement (6 Layers) `[MAJOR]`

- `[MAJOR]` Goal line 1110 claims six layers (disk, MCP registration, plugin hooks, command dispatch, daemon HTTP middleware [canonical], Python import-graph lint). Verifier line 1128 covers only three (MCP start/stop, daemon gate, import-graph CI). Layers 1 (disk), 4 (command dispatch), and 5 (daemon HTTP canonical writes) are named by phase but not by the milestone verifier. A failure in layer 1 (e.g., `.state/build/` writable while `mode.json == teach`) would not trip the verifier as written.
- `[MINOR]` Success criteria #2 (line 1134) requires `<3s` switch time — add a test-harness reference (which phase asserts the 3s SLO?).

### v14 — Build Kernel: Step FSM + Verifiers `[MAJOR]`

- `[MAJOR]` Complexity=XL (line 1379), 11 phases, 6 distinct verifier artifacts (Step FSM + goal-backward + Slice rollup + Phase rollup + Arc rollup + cross-tier + security), and a single 25-word `**Verifier:**` line at 1397 that names only three ("10 golden-fixture Steps … Slice rollup … cross-tier"). Phase rollup (P6, line 1440), Arc rollup (P7, line 1446), and security verifier (P9, line 1458) are uncovered at the milestone verifier level — only their own `#### Phase` lines promise them.
- `[MINOR]` Line 1397 verifier says "cross-tier verifier catches regression when Arc A interacts with Arc B" but this assumes two completed Arcs exist; at milestone close there may only be one. The test fixture plan needs to be explicit about synthetic Arc-A/B setup.

### v16 — Build GSD Command Ports `[MAJOR]`

- `[MAJOR]` Complexity=XL (line 1579), 14 phases, ~30 commands; verifier at line 1593 is "golden-file fixture per command" — generic assertion that does not distinguish ports (e.g., `code-review` from GSD's gsd-code-reviewer) from net-new product-hierarchy commands (e.g., `new-arc`, `multi-arc`). See §2a for the vocabulary side of this.
- `[MINOR]` `**Requirements covered:** PORT-01 through PORT-30 (all 30 GSD port requirements)` (line 1595) — but the enumeration in the goal (line 1576) exceeds 30 tokens. Confirm PORT-01..PORT-30 in REQUIREMENTS.md covers the full set or note the overflow as v2 scope.

### v20 — Teach Four Modes + Selector `[MAJOR]`

- `[MAJOR]` Complexity=XL (line 1976), 11 phases, 4 mode FSMs + selector + override + drop-to-simpler + `chat.params` + system-prompt templates, all covered by one verifier line at 1993. The verifier merges four mode walkthroughs into one sentence; in practice this is P11's golden-fixture test — but the milestone verifier does not name P11 explicitly.
- `[MINOR]` 187 at line 2006 is titled "Mode runtime factoring decision + shared plumbing (v18 refinement)." STATE.md line 92 records this decision as already resolved at roadmap time ("resolved: shared plumbing in v18 kernel"). If the decision is closed, P1 is scaffold-only and should be marked as such or collapsed into 177.

### v27 — Release & Packaging `[MAJOR]` × 2

- `[MAJOR]` **P0-14 co-ownership gap.** PITFALLS.md P0-14 ("OAuth refresh writes plaintext tokens to log on debug=true") maps to "A2, observability" per SUMMARY §6 (per 2-RESEARCH §1). v2 owns it at line 284 (phase P0 tag at 020 line 376). v27 owns the Observability finalization surface (line 2654, 255 — structlog + redactor + event-log forensics) — exactly where the release-time P0-14 regression lives — but v27 has **no `**P0 pitfalls owned:**` line at all**. The release-phase regression for P0-14 is orphaned: v2 ships early, the redactor is re-implemented by 255, and no ownership hand-off is declared. Either add `**P0 pitfalls owned:** P0-14 (shared with v2 — release-time redactor regression)` to v27, or explicitly record that 255 is a non-owning consumer and name the 254 P0 regression test.
- `[MAJOR]` `**Depends on:** most of v1..v24 (soft); v26 (cross-host verification)` (line 2578). "Most of" is vacuous; the scheduler cannot compute v27's frontier. Enumerate the actual hard predecessors — at minimum v1 (events), v8 (plugin), v11 (modes), v12, v13 (MCP servers), v14 (verifier), v26 (portability). Everything else is genuinely soft.
- `[MINOR]` Verifier at line 2593 asserts `uvx state install` succeeds on macOS + Linux — good — but no regression for P0-13 (auth.json 0600) is named here even though 256 "Security baseline" at line 2660 includes "chmod-0600 verifiers." Thread the P0-13 test through 256 explicitly.

---

## 4. Coverage Audit (REQ-ID ↔ Phase Content)

Five phases spot-checked (weighted toward XL milestones per CONTEXT.md §specifics).

**Phase 132 — Security verifier** (ROADMAP.md line 1458)
- Claims: `BLD-08, SEC-01, SEC-02, SEC-03` (line 1461)
- Content: "SQLi, path traversal, secret leak, shell meta"
- Verdict: `[MINOR]` — SEC-04 (regex-DoS), SEC-05 (JSON-bomb), SEC-06 (chmod-0600) are in scope per REQUIREMENTS.md but deferred to 256 (line 2660). Reasonable split, but the phase title says "Security verifier" without a "partial" qualifier, which invites re-scoping later. Rename to `Security verifier (part 1 — input guards)`.

**Phase 157 — Hierarchy bootstrapping** (line 1678)
- Goal: `/state:build:new-arc / new-phase / new-slice / insert-slice / add-phase / remove-phase / multi-arc`
- Content: net-new product-hierarchy commands (not GSD ports)
- Verdict: `[MINOR]` — framed inside v16 "Build GSD Command Ports" but are not ports. Either mint a PORT-NEW-ARC class of REQ-IDs or move these phases into v15 scope where product-hierarchy scaffolding lives. See §2a.

**Phase 187 — Mode runtime factoring decision + shared plumbing** (line 2006)
- Claims: `(infrastructure)` (line 2009)
- Content: "Resolve SUMMARY Q2 — shared selector/drop/Kolb/observation emission in v18 kernel; modes consume"
- Verdict: `[MINOR]` — the decision is already recorded as resolved in STATE.md line 92. Either (a) collapse P1 into 177, or (b) reword as "Implement shared plumbing decided in SUMMARY Q2" and drop the `decision` framing. As written, it reads like a pre-execution discussion dressed as an implementation phase.

**Phase 254 — Full test infrastructure + P0 regression suite** (line 2648)
- Claims: `TST-01..TST-08` (line 2651); success-criterion #4 at line 2601 says "All 16 P0 pitfalls have regression tests (TST-08) — green"
- Content: pytest, Hypothesis, E2E opencode fixture, provider parity matrix, captured-header regression, mode-isolation import-graph, P0 regression tests
- Verdict: `[MINOR]` — 16 P0s but the roadmap has P0 tags on only 10 milestone-phase pairs (per 2-RESEARCH §1 table). 254 re-runs all 16, but it cannot guarantee coverage unless each P0 has a named regression test file upstream. Add a `P0-test matrix` artifact (P0 ID → test path) to close this loop.

**Phase 105 — Cross-mode leakage regression suite** (line 1190)
- Claims: `(verifier; TST-08)` (line 1193)
- Content: P0-11 test suite — "every illegal combination, assert rejection at canonical gate"
- Verdict: clean (no finding). Good: names the canonical gate explicitly.

**REQUIREMENTS.md coverage discrepancy** (per 2-RESEARCH §6)
- `[MINOR]` REQUIREMENTS.md line 390: `Every v1 REQ-ID is mapped to exactly one milestone + phase. **Coverage: 221/221 (100%).**` — but the file contains 229 `- [ ] **<ID>**` checkbox entries. Nine of those are v2-deferred (PORT-SHIM-V2-01..03, OBS-V2-01..02, EVAL-V2-01..02, ADV-V2-01..02), leaving 220 v1 IDs — one short of 221. Either the claim is off-by-one or one REQ-ID is missing from the checkbox section but counted in traceability.

---

## 5. DAG Audit (Missing + Excessive Edges)

### 5a. Parallel-safe claim recheck — v1..v5

STATE.md lines 34–42 (verbatim):
> All five Tier 1 milestones have zero predecessors and can run concurrently.

Verbatim `**Depends on:**` lines in ROADMAP.md (per 2-RESEARCH §3):
- v1 line 181: `(none — foundation)` ✅ clean
- v2 line 281: `(none — foundation; no runtime deps on A1 yet, auth.json is standalone)` ✅ clean
- v3 line 396: `v2 (soft — provider tests need auth creds, but scaffolding can start in parallel)` ⚠ **soft dep exists**
- v4 line 488: `(none — foundation; snapshot-composition uses opencode Snapshot but abstraction hides it)` ✅ clean
- v5 line 579: `v1 (reactive to event-store updates)` ⚠ **hard dep exists**

**Finding:**
- `[MAJOR]` STATE.md line 42 is overstated. Two of the five Tier 1 milestones have non-empty dependencies (v3 soft, v5 hard). The ROADMAP.md DAG code block at lines 76–83 is more accurate ("soft-after v2") but still draws no edge for v5 ←── v1. Either (a) STATE.md line 42 should read "All five Tier 1 milestones can START concurrently; v3 and v5 have soft/hard predecessors whose scaffolding can proceed in parallel" — or (b) the parallel-safe wave table (ROADMAP.md line 116 `W1 | v1, v2, v3, v4, v5`) should split into `W1 | v1, v2, v4` + `W2-prep | v3, v5` for consistency with line 579.

### 5b. Missing edges

- `[MINOR]` ROADMAP.md line 1111 (v11 `**Depends on:** v6, v8`) — but 099 (line 1153) depends on `068` and 100 (line 1159) depends on `070, 077`. Milestone-level depends-on of "v8" is coarsely correct but hides that 100 needs a late v8 phase (P10). For wave planning this obscures the fact that v11 cannot start fully until near-end of v8.
- `[MINOR]` v9 depends on v7 (2-RESEARCH §2), but 084 "toast" sub-component (line 1002) consumes SSE events from the daemon (v6), not purely worker plumbing (v7). Verify: does v9's toast feature reach v6's SSE directly, or only via v7?
- `[NIT]` v17 (line 1692+, depends on v9, v14) — the gray-area decision dialog (line 1695) requires 133 (gray-area plumbing at line 1464). Soft dependency is implicit but not enumerated.

### 5c. Excessive / vacuous edges

- `[MAJOR]` v27 `**Depends on:** most of v1..v24 (soft); v26 (cross-host verification)` (line 2578). "most of" scares readers (it reads as a cliff) and under-specifies the scheduler. Split into hard + soft enumerated lists.
- `[MINOR]` 253 `**Depends on:** v1..v26 (soft across all)` (line 2644). Same pattern.
- `[MINOR]` 254 `**Depends on:** all milestones (verifiers threaded in)` (line 2650). Same pattern.

### 5d. Phase-count discrepancy

- `[MAJOR]` **STATE.md claims 267 phases; ROADMAP.md has 256 `#### Phase` headings** (per 2-RESEARCH §2 and §7). Evidence: STATE.md line 27 (`Phases complete: 0 / 267`) and line 65 (`Total v1 phases shipped: 0 / 267`); ROADMAP.md `grep -c '^#### Phase'` = 256. The Progress Table (ROADMAP.md lines 142–167) sums to 256 too by inspection (v1: 10, v2: 12, v3: 9, v4: 9, v5: 9, v6: 10, v7: 8, v8: 12, v9: 9, v10: 8, v11: 9, v12: 9, v13: 9, v14: 11, v15: 10, v16: 14, v17: 8, v18: 11, v19: 9, v20: 11, v21: 8, v22: 9, v23: 8, v24: 8, v25: 8, v26: 8, v27: 10 — sum 256). Either STATE.md's 267 is stale (carry-over from an earlier draft), or ROADMAP.md is missing 11 phase headings that were counted earlier. Reconcile before the first milestone kickoff — downstream dashboards, progress bars, and the `state stats` CLI will be wrong by 11 phases out of the gate.

---

## 6. Verifier Audit

Milestones where the `**Verifier:**` line materially under-covers the `**Goal:**` line:

### v11 — Mode Enforcement `[MAJOR]`
- Goal (line 1110): "Physical + runtime + static enforcement of the \"exclusive modes\" cardinal rule across disk, MCP registration, plugin hooks, command dispatch, daemon HTTP middleware (canonical), and Python import-graph lint." → **6 layers**.
- Verifier (line 1128): "Switch mode from build→teach → build MCP server stopped, teach started within 3s; attempted `state.concept.observed` write while mode=build rejected at daemon; `state.build` importing `state.teach` fails CI." → covers MCP registration, daemon HTTP, import-graph. **Missing: disk layer, plugin hook layer, command dispatch layer.** Phase-level verifiers exist (098 disk, 100 plugin hooks, 105 cross-mode regression) but the milestone verifier does not aggregate them.
- **Fix:** extend milestone verifier to "All 6 layers individually tested; P0-11 regression suite green."

### v14 — Build Kernel Step FSM `[MAJOR]`
- Goal (line 1376): "Step state machine + STEP.md frontmatter schema + goal-backward verifier + Slice/Phase/Arc rollup verifiers + cross-tier integration verifier + security verifier" → **6 verifier artifacts**.
- Verifier (line 1397): "10 golden-fixture Steps … Slice rollup fails if any Step fails; cross-tier verifier catches regression when Arc A interacts with Arc B." → covers Step + Slice + cross-tier. **Missing: Phase rollup (129), Arc rollup (130), security verifier (132).**
- **Fix:** extend milestone verifier to name all 6 rollup/verifier types OR reference 134 (10-Step golden fixture suite) as the integrating test.

### v20 — Teach Four Modes + Selector `[MAJOR]`
- Goal (line 1973): 4 mode FSMs + mastery selector + 4 mastery bands + manual override + drop-to-simpler.
- Verifier (line 1993): single-sentence compound. Does not explicitly exercise the manual-override-sticks-until-cleared semantic (phase P7 lines 2042–2046) nor the temperature injection (P9, P10).
- **Fix:** either split verifier into 4 sub-clauses (one per mode + selector) or reference 197 explicitly.

### v16 — Build GSD Command Ports `[MINOR]`
- Goal (line 1576): 30+ commands, heterogeneous (some are task-spawners, some are file emitters, some are pure SQL queries).
- Verifier (line 1593): "Each ported command has a golden-file fixture that exercises its input/output contract; commands that spawn subagents assert task completion; multi-Arc batch-planner produces valid DAG."
- **Fix:** split verifier into (a) file-emitter commands (golden-file), (b) subagent-spawning commands (task-completion assertion), (c) batch/DAG commands (DAG-validity assertion).

### v18 — Teach Kernel `[MINOR]`
- Goal (line 1773 area): concept graph + Kolb FSM + event-sourced mental model + frustration-drop signal (used by 194).
- Verifier (per 2-RESEARCH §2 abridged): "10 observations project; rebuild byte-identical; Kolb fixture; frustration drop."
- **Fix:** verify "byte-identical rebuild" assertion names the projection artifact file explicitly (`mental-model.json` path), and that the frustration-drop fixture has a documented fail mode — per CLAUDE.md line 45 ("Event payloads must be deterministic — no `datetime.now()` or randomness in handlers; replay must be bit-identical").

---

## 7. Recommendations (Prioritized)

Ordered MAJOR first, then MINOR descending; each item names the originating finding. No rewrites — flags and sketches only.

1. `[MAJOR]` Reconcile the phase-count mismatch: STATE.md says 267, ROADMAP.md has 256 `#### Phase` headings. Pick one and sync the other before the first kickoff. (§5d)
2. `[MAJOR]` Resolve P0-14 co-ownership. Either add `**P0 pitfalls owned:** P0-14 (shared with v2)` to v27, or document 255 as a non-owning consumer and explicitly name the release-time regression in 254. (§3 v27, §4)
3. `[MAJOR]` Soften STATE.md line 42 ("All five Tier 1 milestones have zero predecessors and can run concurrently") — v3 and v5 have dependencies. Add a footnote pointing to ROADMAP.md lines 396 and 579. (§5a)
4. `[MAJOR]` Replace v27 `**Depends on:** most of v1..v24 (soft)` with an enumerated hard + soft split. (§5c, §2b, §3 v27)
5. `[MAJOR]` Expand v11's `**Verifier:**` line at 1128 to cover all 6 layers named in the goal (currently covers 3). (§6, §3 v11)
6. `[MAJOR]` Expand v14's `**Verifier:**` line at 1397 to cover Phase rollup, Arc rollup, and security verifier (currently covers Step + Slice + cross-tier). (§6, §3 v14)
7. `[MAJOR]` Expand v20's `**Verifier:**` line at 1993 or reference 197 as the integrating test — the single-sentence compound is hiding an 11-phase XL. (§6, §3 v20)
8. `[MAJOR]` Decide v16 scope: either (a) move `new-arc/new-phase/new-slice` commands into v15 (product-hierarchy scaffolding), or (b) keep in v16 but relabel from "Build GSD Command Ports" to "GSD Ports + Net-New Hierarchy Commands." (§3 v16, §2a line 1576)
9. `[MINOR]` Reconcile REQUIREMENTS.md "Coverage: 221/221 (100%)" claim (line 390) with the 229 checkbox entries (220 v1 post-v2-strip). Fix off-by-one. (§4)
10. `[MINOR]` Rename the path-segment `<phase>` in branch naming (ROADMAP.md line 536) to `<product-phase-id>` or similar to eliminate the Phase-token collision. (§2a)
11. `[MINOR]` Either collapse 187 (line 2006, "Mode runtime factoring decision") into 177 or reword away from the resolved-decision framing. (§4, §3 v20)
12. `[MINOR]` Split v2's goal line 280 into three clauses; split its verifier line 282 the same way. (§3 v2)
13. `[MINOR]` Clarify 132 as "Security verifier (part 1 — input guards)" to signal the 256 hand-off. (§4)
14. `[MINOR]` Add a P0-test matrix artifact (path → P0 ID) to support 254's "all 16 P0 regression tests green" claim. (§4)
15. `[NIT]` Standardize the "shared" P0 ownership convention: either use "(shares P0-X with M-AY)" everywhere or drop it. Currently only v3 and v13 use this wording. (§3 v3)
