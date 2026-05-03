---
phase: quick-3-revise-roadmap-md-to-apply-review-roadma
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/ROADMAP.md
  - .planning/STATE.md
autonomous: true
requirements:
  - REVIEW-MAJOR-1-phase-count
  - REVIEW-MAJOR-2-tier1-parallel-safe
  - REVIEW-MAJOR-3-v27-P0-14-ownership
  - REVIEW-MAJOR-4-v27-depends-on
  - REVIEW-MAJOR-5-v11-verifier
  - REVIEW-MAJOR-6-v14-verifier
  - REVIEW-MAJOR-7-v20-verifier
  - REVIEW-MAJOR-8-v16-scope-relabel
  - REVIEW-MINOR-2a-domain-vocab
  - REVIEW-MINOR-v2-split
  - REVIEW-MINOR-v3-shares
  - REVIEW-MINOR-v14-P9-rename
  - REVIEW-MINOR-v20-P1-reword
  - REVIEW-MINOR-v27-P8-P0-matrix
  - REVIEW-MINOR-v27-P10-P0-13
  - REVIEW-NIT-5b-5c-defer

must_haves:
  truths:
    - "STATE.md phase counts match ROADMAP.md's authoritative count of 256 at every mention (4 sites)."
    - "STATE.md line 42 accurately reflects that v3 (soft) and v5 (hard) have Tier-1 dependencies."
    - "ROADMAP.md Tier-1 parallel-safe wave table distinguishes W1 (v1, v2, v4) from W2-prep (v3 after v2, v5 after v1)."
    - "v27 declares P0-14 co-ownership with v2 in frontmatter-style `**P0 pitfalls owned:**` line."
    - "v27 milestone and P7/P8 phases enumerate hard + soft depends-on rather than 'most of v1..v24'."
    - "v11, v14, and v20 verifier lines explicitly name every goal-declared sub-artifact with phase cross-references."
    - "v16 is relabeled to reflect 'ports + net-new product-hierarchy commands' with a disambiguator at the header and Summary Checklist."
    - "Seven §2a domain-vocab sites are fixed without substituting Arc/Phase/Slice/Step for GSD Milestone/Phase anywhere in the doc's meta-structure."
    - "256 body names P0-13 (chmod-0600) regression hand-off from 012."
    - "254 acceptance criteria references a `.state/build/p0-test-matrix.md` artifact mapping each P0-ID to its upstream regression path."
    - "ROADMAP.md has a dated Revision History footer section referencing this quick task for traceability."
    - "A single one-line TODO defers NIT §5b/§5c phase-level edge tightening near the ROADMAP DAG code block (no per-phase edits)."

  artifacts:
    - path: ".planning/ROADMAP.md"
      provides: "Revised roadmap with all MAJORs addressed, MINOR batches applied, and revision footer."
      contains: "## Revision History"
    - path: ".planning/STATE.md"
      provides: "Phase-count + parallel-safe claims aligned with ROADMAP.md reality."
      contains: "256"

  key_links:
    - from: ".planning/STATE.md (line 42)"
      to: ".planning/ROADMAP.md (lines 396, 579)"
      via: "Footnote/pointer explaining v3 soft-dep on v2 and v5 hard-dep on v1"
      pattern: "v3.*soft.*v2|v5.*hard.*v1"
    - from: ".planning/ROADMAP.md v27 (line ~2581)"
      to: ".planning/ROADMAP.md 020 (line 376)"
      via: "`**P0 pitfalls owned:** P0-14 (shared with v2 ...)` new line"
      pattern: "P0-14.*shared with v2"
    - from: ".planning/ROADMAP.md 254 (line 2649)"
      to: ".state/build/p0-test-matrix.md (future artifact)"
      via: "Acceptance-criteria bullet naming the matrix path + TST-08 cross-reference at line 2601"
      pattern: "p0-test-matrix\\.md"
    - from: ".planning/ROADMAP.md 132 (line 1458)"
      to: ".planning/ROADMAP.md 256 (line 2660)"
      via: "Phase rename to 'Security verifier (part 1 — input guards)' to signal hand-off"
      pattern: "part 1.*input guards"
    - from: ".planning/ROADMAP.md Revision History footer"
      to: ".planning/quick/3-revise-roadmap-md-to-apply-review-roadma/"
      via: "Dated bullet referencing quick-task-3 directory"
      pattern: "quick/3-"
---

<objective>
Apply REVIEW-ROADMAP.md findings to `.planning/ROADMAP.md` (and the scope-expanded `.planning/STATE.md`) so that all MAJORs from §7 items 1–8 are resolved, approved MINOR batches land in one coherent pass, and deferred NITs are marked with an in-file TODO. Edit coordinates come from 3-RESEARCH.md (authoritative over REVIEW on any line-number drift).

Purpose: Unblock Tier 1 milestone kickoff by eliminating phase-count drift (267 vs 256), parallel-safe overstatements, P0-14 co-ownership gap, under-specified verifier lines, vocabulary collisions (Arc/Phase/Slice/Step vs GSD Milestone/Phase), and vacuous "most of v1..v24" dependency edges.

Output: A revised ROADMAP.md + STATE.md pair with a dated Revision History footer on ROADMAP.md referencing `.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/` for per-finding traceability. No source-code changes; planning artifacts stay local per `commit_docs=false`.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/3-CONTEXT.md
@.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/3-RESEARCH.md
@.planning/REVIEW-ROADMAP.md
@.planning/ROADMAP.md
@.planning/STATE.md
@CLAUDE.md

<constraints>
- **Vocabulary cardinal rule (CLAUDE.md lines 48–49):** Arc/Phase/Slice/Step describes the PRODUCT hierarchy only. GSD uses Milestone → Phase. Never swap.
- **Line numbers come from 3-RESEARCH.md**, not REVIEW-ROADMAP.md (REVIEW has two known drifts: STATE.md phase-count is line 26 not 27; v2 verifier is line 301 not 282).
- **Scope surface is exactly two files:** `.planning/ROADMAP.md` + `.planning/STATE.md`. Do not touch PROJECT.md, REQUIREMENTS.md, or `.planning/research/*`.
- **Parser-safe:** All `**Depends on:**` rewrites must stay on a single line (GSD `roadmap.cjs:164` regex consumes one line verbatim).
- **NIT §5b/§5c deferred:** one-line TODO only; no per-phase edits for v11/v9/v17 edge tightening.
- **Structural surgery out of scope:** v16 relabel only — no moving phases to v15.
</constraints>

<interfaces>
<!-- Key line ranges the executor operates on. Extracted from 3-RESEARCH.md. -->
<!-- Executor should use these directly — no ROADMAP exploration needed beyond sanity-checking -->
<!-- a verbatim line match before every edit (line drift can occur mid-session as edits land). -->

STATE.md 267-sites (§1a): lines 26, 58, 65, 155
STATE.md parallel-safe overstatement (§1a): line 42

ROADMAP.md 267-sites (§1c): lines 17, 169, 2705
ROADMAP.md Milestone DAG Tier-1 block (§1d): lines 77–82 (fence 76–104)
ROADMAP.md Parallel-Safe wave table (§1e): lines 114–127, primary edit at 116
ROADMAP.md Summary Checklist v16 (§4): line 53

ROADMAP.md v2 goal (§6): line 280
ROADMAP.md v2 verifier (§6): line 301  [REVIEW drift — not 282]
ROADMAP.md v3 "shares" (§6): line 399
ROADMAP.md v13 "shares" (§6): line 1292
ROADMAP.md v12 P0-12 (§6): line 1205

ROADMAP.md v11 goal (§3a): line 1110
ROADMAP.md v11 verifier (§3a): line 1128
  — sub-refs: disk 098 (1147), plugin hooks 100 (1159),
    regression 105 (1190), <3s SLO success-criterion #2 (1134)

ROADMAP.md v14 goal (§3b): line 1376
ROADMAP.md v14 verifier (§3b): line 1397
  — sub-refs: Phase rollup 129 (1440), Arc rollup 130 (1446),
    Security 132 (1458), golden-fixture 134 (1470)
ROADMAP.md 126 heading (§5 line 1422): line 1422
ROADMAP.md 130 goal + heading (§5 line 1447 + 1446): 1446–1447
ROADMAP.md 132 heading rename (§6): line 1458

ROADMAP.md v16 header (§4): line 1573
ROADMAP.md v16 goal (§4 + §5 line 1576): line 1576
ROADMAP.md v16 verifier (§4): line 1593
ROADMAP.md 157 heading (§4 + §5 line 1678): line 1678
ROADMAP.md 159 goal (§5 line 1722): line 1722

ROADMAP.md v20 goal (§3c): line 1973
ROADMAP.md v20 verifier (§3c): line 1993
  — sub-refs: override 193 (2042), temperature 195 (2054),
    system-prompt 196 (2060), golden fixture 197 (2066)
ROADMAP.md 187 heading (§7): line 2006
ROADMAP.md 187 goal (§7): line 2007

ROADMAP.md v27 header (§2): line 2574
ROADMAP.md v27 depends_on (§2): line 2578
ROADMAP.md v27 complexity (§2 — insert P0-14 line AFTER this): line 2580
ROADMAP.md v27 success-criterion #4 (§8): line 2601
ROADMAP.md 253 depends_on (§2): line 2644
ROADMAP.md 254 heading (§8): line 2648
ROADMAP.md 254 goal (§8): line 2649
ROADMAP.md 254 depends_on (§2): line 2650
ROADMAP.md 255 heading (§2): line 2654
ROADMAP.md 255 goal (§2 — add P0-14 hand-off clause): line 2655
ROADMAP.md 256 heading (§2): line 2660
ROADMAP.md 256 goal (§2 — add P0-13 thread): line 2661

ROADMAP.md 267-site in requirements footer (§1c): line 2705
ROADMAP.md footer section-break (§9): line 2717
ROADMAP.md footer italic credits (§9): lines 2719–2720

ROADMAP.md branch-naming <phase> fan-out (§5 line 536): lines 510, 536
ROADMAP.md structural-note rewrite (§5 line 8): line 8
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix cross-file phase-count drift (STATE.md + ROADMAP.md 267→256)</name>
  <files>.planning/STATE.md, .planning/ROADMAP.md</files>
  <action>
Address REVIEW §5d MAJOR — authoritative phase count is 256 (verified: `grep -c '^#### Phase' .planning/ROADMAP.md = 256`; Progress Table column sum = 256).

**STATE.md edits (4 sites per 3-RESEARCH §1a):**
- Line 26: `**Phases complete:** 0 / 267` → `**Phases complete:** 0 / 256`
- Line 58: `| Phases defined | 267 |` → `| Phases defined | 256 |`
- Line 65: `| Total v1 phases shipped | 0 / 267 |` → `| Total v1 phases shipped | 0 / 256 |`
- Line 155: `ROADMAP.md` — 27 milestones, 267 phases, DAG` → `ROADMAP.md` — 27 milestones, 256 phases, DAG`

**ROADMAP.md edits (3 sites per 3-RESEARCH §1c):**
- Line 17: `| Phases total | **267** |` → `| Phases total | **256** |`
- Line 169: `| **TOTAL** | **0/267** | — | — | — |` → `| **TOTAL** | **0/256** | — | — | — |`
- Line 2705: `221 v1 requirements → 267 phases across 27 milestones` → `221 v1 requirements → 256 phases across 27 milestones`

**Method:** Use Edit tool with verbatim `old_string` pulled from each line. Before each edit, Read the file at that line ±2 to confirm the anchor matches (line drift can occur if earlier edits in this task shift lines — but within a single file the three STATE.md edits are non-overlapping blocks, so all four STATE.md edits can be issued unconditionally; same for ROADMAP's three 267 sites).

**Do NOT** attempt a global sed/grep replace — other `267` substrings (if any exist in code blocks or identifiers) must not be touched.

<quality_scan>
  <code_to_reuse>
    - Grep pattern (verify fan-out before editing): `grep -n "267" .planning/STATE.md .planning/ROADMAP.md`
    - Expected: 4 hits in STATE.md (lines 26, 58, 65, 155); 3 hits in ROADMAP.md (lines 17, 169, 2705). No other `267` should appear; if grep reveals more, STOP and re-read 3-RESEARCH §1a / §1c before proceeding.
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies (markdown edits only).
  </docs_to_consult>
  <tests_to_write>
    - N/A — no new exported logic. Verification is a post-edit grep (see <verify>).
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -cn "267" .planning/STATE.md .planning/ROADMAP.md | grep -v ":0$"</automated>
    Expected exit: no output (zero lines with remaining `267`) OR only unrelated occurrences in unrelated code blocks that 3-RESEARCH confirmed should stay. If any line in STATE.md or ROADMAP.md still contains `267`, re-open and fix. Secondary check: `grep -n "256" .planning/STATE.md .planning/ROADMAP.md | wc -l` should show ≥7 hits.
  </verify>
  <done>All 7 flagged sites flipped from 267 to 256; no stray 267 remains in either file; visual `grep -n "Phases"` confirms counts are internally consistent.</done>
</task>

<task type="auto">
  <name>Task 2: Fix Tier-1 parallel-safe overstatement (STATE.md line 42 + ROADMAP.md DAG + wave table)</name>
  <files>.planning/STATE.md, .planning/ROADMAP.md</files>
  <action>
Address REVIEW §5a MAJOR — v3 soft-depends on v2 (ROADMAP line 396) and v5 hard-depends on v1 (ROADMAP line 579); current STATE.md line 42 + ROADMAP parallel-safe wave table overstate "all five run concurrently."

**STATE.md line 42 edit (3-RESEARCH §1a):**
Replace:
`All five Tier 1 milestones have zero predecessors and can run concurrently.`
With (keeping original prose register):
`All five Tier 1 milestones can START concurrently; v3 soft-depends on v2 (auth creds for provider tests — scaffolding parallel-safe) and v5 hard-depends on v1 (reactive to event-store stream). See ROADMAP.md lines 396 (v3) and 579 (v5).`

**ROADMAP.md Milestone DAG Tier-1 parenthetical (3-RESEARCH §1d — lines 77–82 inside the lines-76–104 code fence):**
Current line 77 reads `Tier 1 (all independent; no edges between them):` which contradicts line 82's soft v5 edge. Rewrite line 77 to:
`Tier 1 (parallel-safe starts; v3 soft-after v2 for auth; v5 reacts to v1 events):`
Leave lines 78–82 unchanged (existing soft-edge comment on v3 already reflects reality; v5 soft-edge comment should be added if not present — verify lines 78–82 verbatim before editing; if v5 line lacks the edge, append ` (reactive to v1 events)` to the `v5 ─┘` line).

**ROADMAP.md Parallel-Safe wave table (3-RESEARCH §1e — line 116, renumber-less lower-blast-radius pattern):**
Current line 116: `| W1 | v1, v2, v3, v4, v5 |`
Replace with TWO consecutive rows:
```
| W1 | v1, v2, v4 |
| W1-prep | v3 (after v2 creds), v5 (after v1 events) |
```
Using `W1-prep` (not `W2-prep`) avoids renumbering the existing W2..W11 rows on lines 117–127. This is the recommended pattern per 3-RESEARCH §1e (both options satisfy REVIEW; renumber-less is safer).

**Also in this task — Deferred NIT marker (per CONTEXT decision §5b/§5c):**
Locate the ROADMAP DAG code block closing fence (around line 104) and add ONE line immediately after the closing fence:
`<!-- TODO: tighten phase-level depends-on edges (099/P4 → v8 phase specificity; 084 → v6/v7 split; v17 → 133 soft-dep) before v5 wave planning. See REVIEW-ROADMAP.md §5b/§5c. -->`

<quality_scan>
  <code_to_reuse>
    - Grep pattern (locate wave-table for sanity check): `grep -n "^| W1 " .planning/ROADMAP.md` — expect line 116.
    - Grep pattern (locate DAG fence): `grep -n "^\`\`\`$" .planning/ROADMAP.md | head -5` — Tier-1 fence closes around 104.
    - Grep pattern (verify line 77 text): `sed -n '76,82p' .planning/ROADMAP.md` — before editing, confirm verbatim.
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies.
  </docs_to_consult>
  <tests_to_write>
    - N/A — markdown edits.
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -c "can START concurrently" .planning/STATE.md && grep -c "W1-prep" .planning/ROADMAP.md && grep -c "TODO: tighten phase-level depends-on" .planning/ROADMAP.md</automated>
    Expected: each grep returns ≥1. Also manually `sed -n '76,82p' .planning/ROADMAP.md` to confirm line 77 parenthetical was updated.
  </verify>
  <done>STATE.md line 42 reflects v3/v5 deps; ROADMAP Tier-1 parenthetical matches reality; wave table splits W1 into two rows without renumbering W2..W11; single TODO marker defers NIT §5b/§5c.</done>
</task>

<task type="auto">
  <name>Task 3: Add v27 P0-14 co-ownership + enumerate hard/soft depends-on (milestone + P7 + P8)</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Address REVIEW §3 v27 MAJOR (P0-14 co-ownership gap) + §5c MAJOR (vacuous "most of" depends-on). Per 3-RESEARCH §2, all three depends-on sites and the P0-14 insertion point are confirmed at the cited line numbers.

**Edit 1 — v27 depends-on enumeration (line 2578):**
Replace:
`**Depends on:** most of v1..v24 (soft); v26 (cross-host verification)`
With:
`**Depends on:** v1, v8, v11, v12, v13, v14, v26 (hard); all other v1..v24 (soft — feature completeness)`

**Edit 2 — Insert P0-14 ownership line AFTER line 2580:**
Line 2580 is `**Complexity:** M`. Insert new line directly after:
`**P0 pitfalls owned:** P0-14 (shared with v2 — release-time redactor regression in 255)`
Preserve existing blank-line convention (no extra blank line).

**Edit 3 — 253 depends-on enumeration (line 2644):**
Replace:
`**Depends on:** v1..v26 (soft across all)`
With:
`**Depends on:** v1, 247 (hard — docs source-of-truth + structure scaffold); all other v1..v26 (soft — feature-complete docs coverage)`

**Edit 4 — 254 depends-on enumeration (line 2650):**
Replace:
`**Depends on:** all milestones (verifiers threaded in)`
With:
`**Depends on:** v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15, v16, v17, v18, v19, v20, v21, v22, v23, v24, v25, v26 (hard — each milestone's verifier phase must ship before P0-regression matrix is green)`

All four edits keep the `**Depends on:**` content on a single line (parser-safe per 3-RESEARCH §10a — GSD `roadmap.cjs:164` regex).

<quality_scan>
  <code_to_reuse>
    - Grep (verify current text before editing): `sed -n '2574,2584p;2644,2652p' .planning/ROADMAP.md`
    - Grep (confirm parser-safety — depends-on must be single-line): after edits, `grep -n "^\*\*Depends on:\*\*" .planning/ROADMAP.md | wc -l` should still match pre-edit count (no accidental line splits).
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies.
  </docs_to_consult>
  <tests_to_write>
    - N/A — markdown edits.
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -c "P0 pitfalls owned:\*\* P0-14" .planning/ROADMAP.md && grep -c "247 (hard" .planning/ROADMAP.md && grep -c "most of v1\.\.v24" .planning/ROADMAP.md</automated>
    Expected: first two return ≥1; third returns 0 (all "most of" phrasing removed). Also confirm via `sed -n '2578,2582p' .planning/ROADMAP.md` that the P0-14 line sits immediately after the Complexity line.
  </verify>
  <done>v27 milestone has explicit P0-14 co-ownership line; all three "most of" / "all milestones" depends-on lines are replaced with enumerated hard+soft lists; parser compatibility preserved (single-line).</done>
</task>

<task type="auto">
  <name>Task 4: Expand v11, v14, v20 verifier lines (REVIEW §6 MAJORs)</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Address REVIEW §6 MAJORs — verifier lines under-cover the goal lines. Per CONTEXT decision and 3-RESEARCH §3a/§3b/§3c, prefer EXPLICIT NAMING over P11-reference shortcuts (existing compound-sentence ROADMAP style).

**Edit 1 — v11 verifier (line 1128, 3-RESEARCH §3a):**
Replace the current 3-layer verifier with a 6-layer compound sentence naming each phase:
`**Verifier:** All 6 layers individually tested — disk (098: `.state/build/` vs `.state/teach/` directory-presence assertion), MCP registration (099: build→teach switch stops build MCP server, starts teach within the <3s SLO at success-criterion #2 line 1134), plugin hooks (100: `command.execute.before` rejects cross-mode `/state:*`; `tool.execute.before` rejects cross-mode `mcp__state-*__` invocation), command dispatch (100: same layer), daemon HTTP middleware canonical gate (101: attempted `state.concept.observed` write while mode=build rejected with 403), Python import-graph lint (102: `state.build` importing `state.teach` fails CI). 105 P0-11 regression suite is the integrating cross-mode-leakage test.`

**Edit 2 — v14 verifier (line 1397, 3-RESEARCH §3b):**
Replace the current 3-artifact verifier with a 6-artifact compound sentence:
`**Verifier:** 10 golden-fixture Steps with known goal + committed code assert verifier pass/fail per Step FSM (125); goal-backward verifier (127) rejects mismatched must-haves; Slice rollup (128) fails if any child Step fails; product-Phase rollup (129) and product-Arc rollup (130) aggregate upward; cross-tier integration verifier (131) catches regression when product-Arc A interacts with product-Arc B (synthetic Arc-A/B fixture required); security verifier part-1 (132 — input guards) rejects SQLi/path-traversal/secret-leak/shell-meta inputs. 134 10-Step golden-fixture suite is the integrating test.`

**Edit 3 — v20 verifier (line 1993, 3-RESEARCH §3c):**
Replace the current 1-sentence compound with explicit sub-clauses:
`**Verifier:** Each mode FSM runs a full concept teach via its own state machine (PRIMM, Scaffolded, Socratic, Constructivist — 188–P5); mastery-based selector picks correct mode at each boundary (<30% → PRIMM, 30–50% → Scaffolded, 50–70% → Socratic, 70–80% → Constructivist); manual override sticks until explicitly cleared (193); drop-to-simpler triggered by frustration signal from 175 (194); per-mode temperature injection into `chat.params` (195); per-mode system-prompt templates applied (196). 197 four-mode golden-fixture test is the integrating assertion.`

**Style note:** All three verifier rewrites keep the compound-sentence form (existing ROADMAP style per Claude's Discretion in CONTEXT) rather than switching to bulleted sub-lists.

<quality_scan>
  <code_to_reuse>
    - Grep (verify current v11 verifier before editing): `sed -n '1125,1135p' .planning/ROADMAP.md`
    - Grep (verify v14): `sed -n '1395,1400p' .planning/ROADMAP.md`
    - Grep (verify v20): `sed -n '1990,1996p' .planning/ROADMAP.md`
    - Cross-check phase line numbers for refs: 098=1147, P4=1159, P9=1190, P5/P6 inferred by heading grep; 129=1440, P7=1446, P9=1458, P11=1470; 193=2042, P9=2054, P10=2060, P11=2066 (from 3-RESEARCH).
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies.
  </docs_to_consult>
  <tests_to_write>
    - N/A — markdown edits.
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -c "All 6 layers individually tested" .planning/ROADMAP.md && grep -c "134 10-Step golden-fixture suite" .planning/ROADMAP.md && grep -c "197 four-mode golden-fixture" .planning/ROADMAP.md</automated>
    Expected: each grep returns ≥1. Manually sanity-check that each new verifier is a single line (no accidental wrapping broke the `**Verifier:**` prefix).
  </verify>
  <done>v11/v14/v20 verifier lines explicitly name every goal-declared artifact with phase cross-references; integrating P9/P11 tests named; existing compound-sentence style preserved.</done>
</task>

<task type="auto">
  <name>Task 5: Relabel v16 + split verifier into 3 classes + Summary Checklist mirror</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Address REVIEW §3 v16 MAJOR + §6 MINOR + §2a line 1576 MINOR. Per CONTEXT, **relabel only — no structural phase moves**. Per 3-RESEARCH §4, the Summary Checklist at line 53 must mirror-rename for consistency.

**Edit 1 — v16 milestone header (line 1573):**
Replace:
`## v16 — Build GSD Command Ports`
With:
`## v16 — Build GSD Command Ports + Net-New Product-Hierarchy Commands`

**Edit 2 — Summary Checklist mirror (line 53):**
Replace:
`- [ ] **v16 — Build GSD Command Ports** — All 30 ported/redesigned GSD commands`
With:
`- [ ] **v16 — Build GSD Command Ports + Net-New Product-Hierarchy Commands** — GSD ports + net-new product-hierarchy scaffolding commands (new-arc/new-phase/new-slice/insert-slice/add-phase/remove-phase/multi-arc)`

**Edit 3 — Insert a one-paragraph disambiguator immediately after the renamed v16 header (line 1573):**
Add a new blank line + paragraph (before whatever currently follows line 1573; typical pattern is the `**Tier:**` frontmatter — insert BEFORE that line):
```

> **Disambiguator (vocabulary):** Commands named `new-phase`, `add-phase`, `remove-phase` in this milestone operate on the **product-Phase tier** (Arc → Phase → Slice → Step per PROJECT.md / CLAUDE.md lines 48–49). They are NET-NEW scaffolding — GSD has no Arcs or Slices. They are not GSD-phase ports. See PROJECT.md cardinal rules for the vocabulary boundary.

```

**Edit 4 — v16 goal split (line 1576):**
Replace the one-paragraph goal with a two-sentence split:
`**Goal:** Port existing GSD commands as state-native Step workflows — code-review, intel, map-codebase, debug, forensics, pause/resume-work, thread, workstreams, stats, audit-uat, audit-milestone, docs-update, backlog/todos/notes, undo, ui-phase/review, autonomous, onboard/help, explore, brainstorm, scan, cleanup, reapply-patches, review, set-quality/profile/settings, health, manager. Plus net-new product-hierarchy commands (no GSD equivalents): new-arc, new-phase (product-Phase tier), new-slice, insert-slice, add-phase, remove-phase, multi-arc.`

**Edit 5 — v16 verifier split (line 1593, also covering §6 MINOR):**
Replace:
`**Verifier:** Each ported command has a golden-file fixture that exercises its input/output contract; commands that spawn subagents assert task completion; multi-Arc batch-planner produces valid DAG.`
With:
`**Verifier:** Three assertion classes — (a) file-emitter commands (new-arc, new-phase, new-slice, insert-slice, add-phase, remove-phase, docs-update, backlog/todos/notes, stats, health, etc.): golden-file fixture per command exercises input/output contract; (b) subagent-spawning commands (code-review, intel, forensics, debug, map-codebase): task-completion assertion against synthetic Step fixture; (c) batch/DAG commands (multi-arc, insert-slice, add-phase, remove-phase): DAG-validity assertion on generated product-Slice/Phase graph.`

**Do NOT** edit the 157 phase heading at line 1678 — the disambiguator at the v16 header (Edit 3) covers it per CONTEXT decision (avoid command-rename scope creep).

<quality_scan>
  <code_to_reuse>
    - Grep: `grep -n "Build GSD Command Ports" .planning/ROADMAP.md` — expect exactly 2 hits (lines 53 + 1573) before edit; both must update.
    - Sanity read: `sed -n '1573,1596p' .planning/ROADMAP.md` and `sed -n '51,55p' .planning/ROADMAP.md` before editing.
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies.
  </docs_to_consult>
  <tests_to_write>
    - N/A — markdown edits.
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -c "Build GSD Command Ports + Net-New Product-Hierarchy Commands" .planning/ROADMAP.md && grep -c "Disambiguator (vocabulary)" .planning/ROADMAP.md && grep -c "Three assertion classes" .planning/ROADMAP.md</automated>
    Expected: first returns ≥2 (checklist + header), second returns ≥1, third returns ≥1. Confirm no orphan `Build GSD Command Ports` without the new suffix: `grep -c "Build GSD Command Ports\"?[^ +]" .planning/ROADMAP.md` should be 0.
  </verify>
  <done>v16 header + Summary Checklist both carry the relabel; disambiguator paragraph clarifies product-Phase vs GSD-Phase vocabulary; goal split into ports + net-new sentences; verifier split into 3 assertion classes; 157 phase heading unchanged (command names preserved per scope decision).</done>
</task>

<task type="auto">
  <name>Task 6: Apply remaining MINOR batches (§2a vocab + v2 split + 132 rename + 187 reword + shares wording)</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Apply the four approved MINOR batches from CONTEXT that haven't been covered in earlier tasks. All line coordinates from 3-RESEARCH §5, §6, §7. Be careful with line drift: earlier tasks (1–5) edit lines 17, 53, 116, 169, 1128, 1397, 1573, 1576, 1593, 1993, 2578, 2580–2581, 2644, 2650, 2705. None of those overlap with this task's targets, BUT line-number drift from inserted lines (Task 2 TODO after ~104; Task 3 P0-14 line after 2580; Task 5 disambiguator after 1573) means later line numbers shift. **Strategy: anchor every edit by verbatim `old_string` match, NOT by line number.**

**Edit 1 — Structural note reword (line 8, 3-RESEARCH §5):**
Replace (verbatim anchor):
`GSD phases under a milestone == implementation slices that together ship that Arc.`
With:
`A GSD phase DELIVERS capability into one or more product-runtime Slices — but is not itself a Slice object in `.state/`.`

**Edit 2 — Branch-naming vocab fan-out (lines 510 + 536, 3-RESEARCH §5):**
Line 510 (v4 Success criterion #1) and line 536 (035 heading) both use `slice/<arc>/<phase>/<slice-id>`. Rename BOTH to `slice/<arc-id>/<product-phase-id>/<slice-id>` in lockstep.
- Line 510 anchor: `deterministic branch names \`slice/<arc>/<phase>/<slice-id>\``
- Line 536 anchor: `#### Phase 035 — Deterministic branch + worktree naming (\`slice/<arc>/<phase>/<slice-id>\`)`
**Do NOT** edit line 2711 — that `<phase>` is a `/gsd:plan-phase` CLI metavariable (GSD-phase literal, different meaning).

**Edit 3 — 126 product-prefix (line 1422, 3-RESEARCH §5):**
Replace:
`#### Phase 126 — Slice/Phase/Arc scoping containers (simpler FSMs)`
With:
`#### Phase 126 — Product Slice/Phase/Arc scoping containers (simpler FSMs)`

**Edit 4 — 130 product-prefix on heading + goal (lines 1446 + 1447, 3-RESEARCH §5):**
Line 1446 heading: replace `Arc rollup verifier` with `Product-Arc rollup verifier`.
Line 1447 goal: replace `Aggregate Phase rollups plus Arc acceptance criteria.` with `Aggregate product-Phase rollups plus product-Arc acceptance criteria.`

**Edit 5 — 159 goal inline gloss (line 1722, 3-RESEARCH §5):**
Replace:
`**Goal:** \`route.register\`; Arc/Phase/Slice/Step hierarchy; burndown + verify-pass rate.`
With:
`**Goal:** \`route.register\`; product Arc/Phase/Slice/Step hierarchy (product-tier vocabulary, not GSD Milestone/Phase); burndown + verify-pass rate.`

**Edit 6 — v2 goal split (line 280, 3-RESEARCH §6):**
Replace the single compound-goal sentence with a 3-clause split:
`**Goal:** (1) All five auth methods operational day one (Anthropic OAuth stealth, Gemini CLI, Antigravity, Copilot device-code, plain API-key). (2) Refresh safety + redaction + 0600 enforced (filelock-guarded concurrent refresh, structlog root-logger token redactor, chmod-0600 vault verified on every read). (3) Multi-cred fan-out (round-robin across per-provider credential arrays; rate-limit rotation). Unblocks the Anthropic Pro/Max primary audience.`

**Edit 7 — v2 verifier split (line 301 — REVIEW said 282 but that's DRIFT per 3-RESEARCH §10b; actual line is 301):**
Verify current text matches `**Verifier:** Captured-header regression test (httpx transport mock) for every stealth request; P0 regression test suite (9 tests: P0-1..P0-8 + P0-13); 0600 verification on every read; refresh-lock double-check with concurrent-process harness.`
Replace with:
`**Verifier:** (1) Captured-header regression (httpx transport mock) for all 5 auth methods' stealth requests. (2) P0 regression suite (9 tests: P0-1..P0-8 + P0-13) + chmod-0600 verification on every auth.json read + structlog redactor golden-file assertion. (3) Concurrent-refresh filelock double-check harness (two-process race).`

**Edit 8 — 132 rename (line 1458, 3-RESEARCH §6):**
Replace:
`#### Phase 132 — Security verifier (SQLi, path traversal, secret leak, shell meta)`
With:
`#### Phase 132 — Security verifier (part 1 — input guards: SQLi, path traversal, secret leak, shell meta)`

**Edit 9 — 187 reframing (lines 2006 + 2007, 3-RESEARCH §7):**
Line 2006 heading: replace `#### Phase 187 — Mode runtime factoring decision + shared plumbing (v18 refinement)` with `#### Phase 187 — Shared plumbing implementation (SUMMARY Q2 resolution — hosted in v18 kernel)`.
Line 2007 goal: replace `**Goal:** Resolve SUMMARY Q2 — shared selector/drop/Kolb/observation emission in v18 kernel; modes consume. (Per roadmapper judgment: shared-in-kernel.)` with `**Goal:** Implement shared plumbing (selector + drop-to-simpler + Kolb + observation emission) hosted in v18 kernel; four modes (P2–P5) consume. SUMMARY Q2 decision already resolved in STATE.md line 92 — this phase is scaffolding, not discussion.`
Lines 2008–2010 unchanged.

**Edit 10 — "Shares" wording standardization (per Claude's Discretion in CONTEXT — recommended: reciprocate):**
3-RESEARCH §6 confirms only TWO sites use "shares" today (lines 399, 1292). Recommended path: add reciprocal on v12 line 1205.
- Line 1205 anchor: `**P0 pitfalls owned:** P0-12 (MCP tool-name collision)` → append ` (shared with v13)` → new text: `**P0 pitfalls owned:** P0-12 (MCP tool-name collision) (shared with v13)`
- Line 399 unchanged (already uses "shares").
- Line 1292 unchanged (already reciprocates).
- Note: the new v27 P0-14 line from Task 3 already uses consistent "(shared with v2 — ...)" wording.

<quality_scan>
  <code_to_reuse>
    - Grep (vocab fan-out check): `grep -n "slice/<arc>/<phase>" .planning/ROADMAP.md` before editing — expect 2 hits (510, 536). Post-edit expect 0.
    - Grep (shares wording audit): `grep -n "P0 pitfalls owned" .planning/ROADMAP.md` — confirm v12 line (was 1205) now includes "(shared with v13)".
    - Grep (avoid line-2711 false positive): `grep -n "<phase>" .planning/ROADMAP.md` — post-edit, only the CLI metavariable site at/near 2711 should remain.
    - Grep (before Edit 1): `grep -n "GSD phases under a milestone" .planning/ROADMAP.md` — confirm unique match.
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies.
  </docs_to_consult>
  <tests_to_write>
    - N/A — markdown edits.
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -c "product-phase-id" .planning/ROADMAP.md && grep -c "Product Slice/Phase/Arc scoping" .planning/ROADMAP.md && grep -c "part 1 — input guards" .planning/ROADMAP.md && grep -c "SUMMARY Q2 resolution" .planning/ROADMAP.md && grep -c "P0-12 (MCP tool-name collision) (shared with v13)" .planning/ROADMAP.md && grep -c "DELIVERS capability into one or more product-runtime Slices" .planning/ROADMAP.md</automated>
    Expected: each grep returns ≥1. Also: `grep -c "slice/<arc>/<phase>" .planning/ROADMAP.md` should return 0 (both fan-out sites renamed); `grep -c "<phase>" .planning/ROADMAP.md` should return ≥1 (CLI metavariable preserved).
  </verify>
  <done>All seven §2a domain-vocab sites fixed (lines 8, 510+536 [fan-out], 1422, 1446–1447, 1576 [in Task 5], 1678 [disambiguator from Task 5], 1722); v2 goal+verifier split into 3 clauses; 132 renamed; 187 reworded away from decision framing; v12 line 1205 reciprocates P0-12 sharing with v13.</done>
</task>

<task type="auto">
  <name>Task 7: Thread P0-13/P0-14 hand-offs + add P0-test matrix artifact to 254</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Finalize v27-side P0 threading per CONTEXT + 3-RESEARCH §2 and §8.

**Edit 1 — 255 P0-14 hand-off clause (line 2655, 3-RESEARCH §2):**
Current goal mentions structlog + redactor + event-log forensics + `state logs tail`. Add a hand-off clause inline (preserve single-line format):
Replace (verbatim anchor — the Goal line at 2655, locate by matching the P9 heading at 2654 first):
Whatever the current `**Goal:**` line contains, APPEND at the end (before the trailing period if any):
` P0-14 release-time redactor regression re-runs here as the hand-off from 020 — asserts no `sk-ant-*` / `sk-*` / `ya29.*` tokens leak to structlog output when `debug=true`.`

**Edit 2 — 256 P0-13 thread (line 2661, 3-RESEARCH §2):**
Current goal mentions path-traversal, prompt-injection, shell-meta, regex-DoS, JSON-bomb, chmod-0600 verifiers. Thread P0-13 explicitly:
Find the substring `chmod-0600 verifiers` on the goal line and replace with:
`chmod-0600 verifier (re-runs the P0-13 regression harness from 012 — asserts auth.json chmod is verified on every read under concurrent access)`

**Edit 3 — 254 P0-test-matrix artifact bullet (line 2649, 3-RESEARCH §8):**
The 254 goal already lists pytest + Hypothesis + E2E + parity + captured-header + import-graph + P0 regression tests. Append an artifact clause:
Locate the goal line (anchor by the P8 heading at 2648 first — content: `**Goal:** pytest + pytest-asyncio (strict_asyncio), Hypothesis property tests, E2E opencode fixture, provider parity matrix, captured-header regression, mode-isolation import-graph, P0 regression tests.`). Replace with:
`**Goal:** pytest + pytest-asyncio (strict_asyncio), Hypothesis property tests, E2E opencode fixture, provider parity matrix, captured-header regression, mode-isolation import-graph, P0 regression tests. Artifact: \`.state/build/p0-test-matrix.md\` mapping each P0-ID (P0-1..P0-16) → upstream regression-test path + owning milestone/phase + release-time re-run site.`

**Edit 4 — v27 success-criterion #4 cross-reference (line 2601, 3-RESEARCH §8):**
Replace:
`4. All 16 P0 pitfalls have regression tests (TST-08) — green`
With:
`4. All 16 P0 pitfalls have regression tests (TST-08) — green; see P0-test matrix at \`.state/build/p0-test-matrix.md\`.`

<quality_scan>
  <code_to_reuse>
    - Grep (confirm 255 goal text before editing): `sed -n '2654,2657p' .planning/ROADMAP.md`
    - Grep (confirm 256 goal text): `sed -n '2660,2663p' .planning/ROADMAP.md`
    - Grep (confirm 254 goal text): `sed -n '2648,2652p' .planning/ROADMAP.md`
    - Grep (confirm success-criterion #4): `sed -n '2598,2603p' .planning/ROADMAP.md`
    - Note: line numbers above are from 3-RESEARCH §2/§8; earlier tasks have shifted them slightly (Task 3 inserted a P0-14 line after 2580, so everything from 2581 downward shifts by +1). Executor MUST re-read and anchor by verbatim content, not by line number.
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies.
  </docs_to_consult>
  <tests_to_write>
    - N/A — markdown edits.
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -c "P0-14 release-time redactor regression re-runs here" .planning/ROADMAP.md && grep -c "re-runs the P0-13 regression harness from 012" .planning/ROADMAP.md && grep -c "p0-test-matrix.md" .planning/ROADMAP.md</automated>
    Expected: first and second return ≥1; third returns ≥2 (once in 254 goal, once in success-criterion #4).
  </verify>
  <done>255 goal carries P0-14 hand-off from 020; 256 goal threads P0-13 regression from 012; 254 declares `.state/build/p0-test-matrix.md` artifact; success-criterion #4 cross-references the matrix path.</done>
</task>

<task type="auto">
  <name>Task 8: Add dated Revision History footer (closure + traceability)</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Per CONTEXT Claude's Discretion recommendation + 3-RESEARCH §9, add a new `## Revision History` section BETWEEN line 2717 (final `---` section break) and line 2719 (`*Roadmap created: 2026-04-22*`). No existing Changelog/Revision-History section exists — adding a proper section rather than mutating italic credit lines.

**Note on line drift:** By the time this task runs, Tasks 1–7 have added roughly 5–10 lines to the file (P0-14 insertion in Task 3, disambiguator paragraph in Task 5, W1-prep row in Task 2, TODO line in Task 2, appended artifact clauses in Task 7). Anchor by verbatim content: locate the LAST `---` followed by `*Roadmap created:` in the file, and insert the new section between them.

**Insertion content (insert as new block, with blank lines as shown for markdown formatting):**

```

## Revision History

- **2026-04-22 (quick-task-3):** Applied REVIEW-ROADMAP.md findings. MAJORs resolved: cross-file phase-count drift (267→256 across STATE.md + ROADMAP.md); Tier-1 parallel-safe accuracy (STATE.md line 42 + ROADMAP W1/W1-prep split); v27 P0-14 co-ownership with v2; v27 / P7 / P8 enumerated hard+soft depends-on replacing vacuous "most of v1..v24"; v11 / v14 / v20 verifier expansions naming all goal-declared artifacts; v16 relabeled to "Build GSD Command Ports + Net-New Product-Hierarchy Commands" with disambiguator + 3-class verifier split. MINORs batched: §2a domain-vocab fixes (structural note line 8, branch-naming fan-out lines 510+536, 126/P7 product-prefixes, 159 inline gloss); v2 goal+verifier 3-clause split; 132 "part 1 — input guards" rename signaling 256 hand-off; 187 reframing as scaffolding (SUMMARY Q2 resolved); "shares" wording standardized via v12 reciprocal. P0 threading: P0-14 hand-off in 255; P0-13 regression threaded through 256; P0-test matrix artifact (`.state/build/p0-test-matrix.md`) declared in 254 + success-criterion #4. Deferred: NIT §5b/§5c phase-level edges (099/P4, 084, v17) — one-line TODO near ROADMAP DAG block; REQUIREMENTS.md 221/229 off-by-one (§4 REVIEW MINOR) — out of scope for this pass. Traceability: `.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/` (CONTEXT + RESEARCH + this PLAN + SUMMARY).

```

Also update line 2720 italic credit line:
Replace:
`*Last updated: 2026-04-22 after initial creation*`
With:
`*Last updated: 2026-04-22 — REVIEW-ROADMAP.md applied (see Revision History above).*`

<quality_scan>
  <code_to_reuse>
    - Grep: `grep -n "^\*Roadmap created" .planning/ROADMAP.md` — confirms unique anchor for insertion.
    - Grep: `grep -c "^## Revision History" .planning/ROADMAP.md` — must return 0 pre-edit (no existing section).
  </code_to_reuse>
  <docs_to_consult>
    - N/A — no external library dependencies.
  </docs_to_consult>
  <tests_to_write>
    - N/A — markdown edits.
  </tests_to_write>
</quality_scan>
  </action>
  <verify>
    <automated>grep -c "^## Revision History" .planning/ROADMAP.md && grep -c "quick-task-3" .planning/ROADMAP.md && grep -c "REVIEW-ROADMAP.md applied" .planning/ROADMAP.md</automated>
    Expected: each grep returns ≥1. Final sanity check: `tail -30 .planning/ROADMAP.md` shows Revision-History section followed by the italic credits.
  </verify>
  <done>ROADMAP.md carries a `## Revision History` section dated 2026-04-22 summarizing the apply-pass and pointing to `.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/` for traceability; the final italic `*Last updated:*` line is refreshed to reference the new section.</done>
</task>

</tasks>

<verification>

**Phase-level checks (run after all 8 tasks land):**

1. **Phase-count consistency:** `grep -cn "256" .planning/STATE.md` ≥ 4; `grep -cn "256" .planning/ROADMAP.md` ≥ 3. `grep -cn "267" .planning/STATE.md .planning/ROADMAP.md` should return 0 lines (or only unrelated integer tokens in unrelated contexts — 3-RESEARCH confirmed there are none).

2. **Parallel-safe coherence:** STATE.md line 42 area mentions "v3 soft-depends" and "v5 hard-depends"; ROADMAP Tier-1 DAG parenthetical no longer says "all independent"; wave table has W1 + W1-prep rows.

3. **v27 P0-14 + enumeration:** `grep -c "P0-14 (shared with v2" .planning/ROADMAP.md` ≥ 1; `grep -c "most of v1\.\.v24" .planning/ROADMAP.md` = 0; `grep -c "247 (hard" .planning/ROADMAP.md` ≥ 1; `grep -c "all other v1..v26 (soft" .planning/ROADMAP.md` ≥ 1.

4. **Verifier expansions:** all three compound-sentence verifiers (v11, v14, v20) name every goal-declared artifact and reference their integrating P9/P11 test.

5. **v16 relabel:** header + Summary Checklist both show new title; disambiguator paragraph present; goal split into "Ports: ..." + "Net-new ..."; verifier split into 3 classes.

6. **Vocabulary fan-out:** `grep -c "slice/<arc>/<phase>" .planning/ROADMAP.md` = 0; `grep -c "product-phase-id" .planning/ROADMAP.md` ≥ 2 (lines 510+536 both renamed).

7. **v27 P0 threading + matrix:** P0-14 hand-off in 255 goal; P0-13 regression in 256 goal; `.state/build/p0-test-matrix.md` referenced in 254 goal + success-criterion #4.

8. **Revision History footer:** `## Revision History` section exists between the final `---` break and the italic credits; dated 2026-04-22; references `.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/`.

9. **Parser-safety:** no `**Depends on:**` line spans multiple lines: `awk '/^\*\*Depends on:\*\*/ && NR==FNR {line=$0; getline; if (line !~ /\.$|\)$/ && $0 !~ /^\*\*/) print "BROKEN: " line; next}' .planning/ROADMAP.md` should return nothing.

10. **Vocabulary cardinal rule not violated:** Arc/Phase/Slice/Step still used ONLY as product-hierarchy vocabulary; no new site uses them as GSD Milestone/Phase substitutes. `grep -nE "GSD (Arc|Slice|Step)" .planning/ROADMAP.md` should return 0 results (anti-pattern check).

</verification>

<success_criteria>

All 8 MAJORs from REVIEW-ROADMAP.md §7 are resolved:
1. Phase-count drift 267→256 synced across STATE.md (4 sites) + ROADMAP.md (3 sites).
2. STATE.md line 42 no longer overstates Tier-1 concurrency; ROADMAP DAG + wave table match reality.
3. v27 declares `**P0 pitfalls owned:** P0-14 (shared with v2 …)`.
4. v27 / P7 / P8 depends-on lines enumerate hard + soft predecessors.
5. v11 verifier names all 6 layers with phase refs.
6. v14 verifier names all 6 artifacts with phase refs.
7. v20 verifier expanded into sub-clauses for 4 modes + selector + override + drop + temperature + prompts + P11 integrating test.
8. v16 relabeled + disambiguator + 3-class verifier split (no structural moves).

All 7 approved MINOR batches applied:
- §2a domain-vocab (7 sites, with 2-site branch-naming fan-out).
- v2 goal + verifier 3-clause splits.
- 132 rename to "part 1 — input guards".
- 187 reframing as scaffolding (Q2 resolved).
- 254 `.state/build/p0-test-matrix.md` artifact + success-criterion cross-reference.
- 256 P0-13 regression thread.
- "Shares" wording standardized via v12 reciprocal.

NIT §5b/§5c deferred with single-line TODO near ROADMAP DAG code block. Dated Revision History footer section points to `.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/` for per-finding traceability. No source code touched. No edits outside `.planning/ROADMAP.md` and `.planning/STATE.md`. Parser compatibility (GSD `roadmap.cjs:164` regex) preserved — every `**Depends on:**` line remains single-line.

</success_criteria>

<output>
After completion, create `.planning/quick/3-revise-roadmap-md-to-apply-review-roadma/3-SUMMARY.md` documenting:
- Which MAJORs / MINORs were applied (1:1 against REVIEW §7 recommendations).
- Line drift observed during execution (anchored by content, not by number — note any drift from 3-RESEARCH coordinates).
- Any findings that could not be applied (expected: none — all in-scope items are actionable; REQUIREMENTS.md 221/229 off-by-one is explicitly out of scope and deferred).
- Final grep-summary confirming the verification checks above.

Then update `.planning/STATE.md` Quick-Tasks-Completed table with the task-3 row (Description: "Revise ROADMAP.md + STATE.md to apply REVIEW-ROADMAP.md findings (8 MAJORs, 7 MINOR batches)"; Status: Verified; Commit: `(uncommitted — commit_docs=false)`; Directory link: `./quick/3-revise-roadmap-md-to-apply-review-roadma/`).
</output>
