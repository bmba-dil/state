---
name: Quick Task 3 Context
description: Revise ROADMAP.md to apply REVIEW-ROADMAP.md findings — locked decisions
type: context
---

# Quick Task 3: Revise ROADMAP.md to apply REVIEW-ROADMAP.md findings — Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Task Boundary

Revise `.planning/ROADMAP.md` to apply findings from `.planning/REVIEW-ROADMAP.md`.

**In scope:**
- `.planning/ROADMAP.md` (primary edit target)
- `.planning/STATE.md` (scope-expanded per user decision — see decisions below)

**Out of scope:**
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/research/*.md` (including `PITFALLS.md`, `SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md`)

**Vocabulary constraint (non-negotiable):**
Preserve Arc/Phase/Slice/Step as **product-hierarchy descriptions only**. Never substitute them for GSD Milestone/Phase. When clarifying, use "product-Phase", "product-Slice", etc. for disambiguation.

**Coverage commitment:**
- Address all MAJORs from REVIEW-ROADMAP.md §7 (items 1–8)
- Batch approved MINOR/NIT groups (see decisions below)
- Defer anything contentious with explicit rationale captured in ROADMAP or SUMMARY.md

</domain>

<decisions>
## Implementation Decisions

### Cross-file MAJORs (REVIEW §5d, §5a)
- **Fully fix both sides.** STATE.md is included in the edit surface despite the original "ROADMAP-only" framing.
- Concretely:
  - **MAJOR §5d — Phase-count mismatch.** Update STATE.md `Phases complete: 0 / 267` and `Total v1 phases shipped: 0 / 267` to match ROADMAP.md's actual 256-phase count (re-count authoritatively during execution; do not trust a single `grep`). Also reconcile the ROADMAP progress table (lines 142–167) sum vs the header `N / 267` claims in STATE.md.
  - **MAJOR §5a — Tier 1 parallel-safe overstatement.** Update STATE.md line 42 to reflect the actual dependency graph (v3 soft-dep on v2, v5 hard-dep on v1). Split the ROADMAP.md parallel-safe wave table (line 116 area) into `W1 | v1, v2, v4` and `W2-prep | v3, v5` per the review's suggested rewrite.

### v16 scope MAJOR (REVIEW §3 v16, §2a line 1576)
- **Relabel only — keep structure.** Rename v16 from "Build GSD Command Ports" to "Build GSD Command Ports + Net-New Product-Hierarchy Commands" (or equivalent). Add a one-paragraph disambiguator at the v16 header: commands named `new-arc`/`new-phase`/`new-slice`/`insert-slice`/`multi-arc` operate on the product Phase tier, not GSD phases; they are net-new scaffolding, not GSD ports.
- **Do NOT move phases to v15.** Structural surgery is out of scope; preserves all existing phase numbering and depends-on edges.
- Also split the verifier line at 1593 into the three classes the review names: (a) file-emitter commands (golden-file), (b) subagent-spawning commands (task-completion assertion), (c) batch/DAG commands (DAG-validity assertion). [Covers MINOR §6 v16 in the same edit.]

### v27 MAJORs (REVIEW §3 v27, §5c)
- **Add `**P0 pitfalls owned:** P0-14 (shared with v2 — release-time redactor regression)` to v27 milestone frontmatter.** Pair with an explicit note in 255 clarifying hand-off from 020.
- **Enumerate the "most of v1..v24 (soft)" depends-on at line 2578.** Hard predecessors: v1, v8, v11, v12, v13, v14, v26. Soft: everything else in v1..v24.
- **Apply the same enumeration pattern to 253 (line 2644) and 254 (line 2650).** [Covers MINOR §5c batch.]
- **Thread P0-13 (auth.json 0600) regression through 256 verifier.** [MINOR companion to the MAJOR.]

### Verifier-coverage MAJORs (REVIEW §6)
- **v11 (line 1128).** Expand verifier to name all 6 layers (disk, MCP registration, plugin hooks, command dispatch, daemon HTTP middleware [canonical], Python import-graph lint). Reference P0-11 regression suite (105) as the integrating test. Add test-harness reference for the `<3s` mode-switch SLO (MINOR companion).
- **v14 (line 1397).** Expand verifier to name Phase rollup (129), Arc rollup (130), and security verifier (132) alongside Step + Slice + cross-tier. Alternatively, reference 134 as the integrating golden-fixture test — prefer explicit naming per review recommendation.
- **v20 (line 1993).** Split the single compound sentence into 4 sub-clauses (one per mode FSM + selector) OR reference 197 explicitly as the integrating test. Prefer explicit reference. Also exercise the manual-override-sticks-until-cleared semantic (193) and temperature injection (195, P10) in the verifier language.

### Domain-vocab MINOR batch §2a
- **Apply to all seven sites:** lines 8, 536, 1422, 1447, 1576, 1678, 1722.
- **Structural note (line 8):** reword to "A GSD phase DELIVERS capability into one or more product-runtime Slices — but is not itself a Slice object in `.state/`."
- **Branch path segment (line 536):** rename `<phase>` to `<product-phase-id>` in the deterministic branch naming scheme `slice/<arc>/<product-phase-id>/<slice-id>`. Update any downstream references (grep for `<phase>` inside branch naming contexts).
- **Phase headings at 1422, 1447, 1722:** prefix first product-tier mentions with "product-" on each first mention inside a phase body.
- **v16 goal line 1576:** split the "ports of 30 GSD commands" sentence into "Ports: …" + "Net-new product-hierarchy commands: …" (also covered by v16 relabel above).
- **157 heading (line 1678):** either rename command names or add a one-line disambiguator at the v16 header (prefer disambiguator; covered by v16 relabel).

### v2 / v3 / 132 MINOR batch
- **v2 goal split (line 280) and verifier split (line 282):** decompose into three clauses — (1) five auth methods operational, (2) refresh + redaction + 0600 enforced, (3) multi-cred fan-out.
- **v3 "shares" wording (line 399):** standardize. Choice: either add explicit reciprocal "shares" clauses wherever PITFALLS.md maps a P0 to two milestones, or drop the "shares" wording from v3 and v13. Claude's Discretion — recommended: **standardize by adding reciprocal shares** (clearer traceability), but if that expands scope too much, drop from v3/v13 and rely on the new v27 P0-14 ownership line.
- **132 rename (line 1458):** "Security verifier" → "Security verifier (part 1 — input guards)" to signal the 256 hand-off.

### 187 reframing MINOR (line 2006)
- **Reword "Mode runtime factoring decision + shared plumbing" → "Implement shared plumbing (resolved in SUMMARY Q2 — hosted in v18 kernel)".** Drop the `decision` framing since STATE.md line 92 records it as resolved.
- Do NOT collapse 187 into 177 — preserves phase numbering and existing depends-on edges.

### 254 P0-test-matrix MINOR
- **Add a bullet to 254 acceptance criteria:** "Artifact: `.state/build/p0-test-matrix.md` mapping each P0-ID to its upstream regression test path."
- **Success criterion reinforcement:** success-criterion #4 (line 2601) stays, but add "see P0-test matrix artifact" reference.

### NIT §5b / §5c: ROADMAP.md v11, v9, v17 edges (deferred)
- **Defer with rationale.** These are late-binding phase-level edges whose impact surfaces only during wave scheduling. Add a one-line "TODO: tighten phase-level depends-on edges before v5 wave planning" note near the ROADMAP DAG code block rather than editing individual phases now.

### Claude's Discretion
- Exact wording choices inside ROADMAP for verifier expansions (e.g., whether v11 verifier enumerates layers as a bulleted sub-list or a compound sentence) — follow the existing ROADMAP style (compound sentence with explicit layer names, since the current verifier line is a sentence, not a list).
- Whether to add a single consolidated "CHANGELOG" or "REVIEW-ROADMAP applied" footnote at the top of ROADMAP — **recommended: yes**, a single dated footer noting the review-apply pass, referencing `quick/3-*/` artifacts for traceability.

</decisions>

<specifics>
## Specific Ideas

- Evidence cache for line numbers and exact quoted text lives in `.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md`.
- REVIEW-ROADMAP.md §7 is the authoritative priority list — MAJORs 1–8, then MINORs.
- Per `CLAUDE.md` GSD Workflow Enforcement, this task runs under `/gsd:quick --full`.
- Per `.planning/config.json`, `commit_docs=false` — `.planning/` files stay local. The final commit is docs-only and goes through `gsd-tools commit`.
- No source code changes — this is a docs-only edit.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/REVIEW-ROADMAP.md` (source of findings)
- `.planning/ROADMAP.md` (primary edit target)
- `.planning/STATE.md` (scope-expanded edit target for cross-file MAJORs)
- `.planning/research/PITFALLS.md` (read-only — P0-14 ownership truth)
- `.planning/research/SUMMARY.md` (read-only — SUMMARY Q2 reference for 187)
- `CLAUDE.md` lines 48–49 (vocabulary cardinal rules — positive reference, do not edit)

</canonical_refs>
