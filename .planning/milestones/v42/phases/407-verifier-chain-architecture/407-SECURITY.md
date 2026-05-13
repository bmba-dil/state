---
status: secured
phase: 407-verifier-chain-architecture
asvs_level: 1
block_on: high
threats_total: 8
threats_closed: 8
threats_open: 0
created: 2026-05-13
updated: 2026-05-13
---

# Phase 407 — Security Audit (Verifier Chain Architecture)

**Type:** Design-spike — markdown spec deliverables only; no production code lands.
**Attack surface:** Spec ambiguity, event-name collision, append-only-amendment integrity, naming-discipline drift. ASVS L1.

## Threat Register

| ID | Category | Component | Disposition | Status | Evidence |
|---|---|---|---|---|---|
| T-407-01 | Spec ambiguity | VERIFIER-CHAIN.md algorithm sections | Mitigate via concrete language + line-count floors | CLOSED | 7 `## VCH-` headings, 479-line file; algorithm cells name exact tools (ruff --fix, aiosqlite, pygit2) and grep patterns. |
| T-407-02 | Forward-reference rot | Step sub-verifier rows | Mitigate via grep-checked REQ-ID forward refs | CLOSED | 15 forward REQ-ID refs (GBP-01..05, THM-01..05, STB-01..04, APS-01..05) present in VCH-01 section. |
| T-407-03 | Ladder ambiguity (LLM/auto-fix conflation) | VCH-06 auto-fix-attempt subsection | Mitigate via deterministic-only definition; ban LLM mediation | CLOSED | `### Auto-Fix-Attempt — Definition and Scope` lists ruff/black/isort verbatim; 0 LLM mentions in subsection; INV-13 invariant locks definition. |
| T-407-04 | Human-gate bypass via informal prompt | VCH-06 human-gate routing | Mitigate via opencode `question` exclusivity, cite HRN-06 | CLOSED | "opencode `question`" + "HRN-06" cited 8× in VERIFIER-CHAIN.md (incl. INV-15 invariant). |
| T-407-05 | Event-name collision | v40 EVENT-TAXONOMY.md v42 Amendment | Mitigate via pre-amendment collision grep | CLOSED | 0 duplicate `state.` event names registered across whole file; namespace `state.verifier.*` is registered as SOLE owner of verifier events. |
| T-407-06 | Append-only-amendment violation | v40 EVENT-TAXONOMY.md | Mitigate via pre/post wc + v41-amendment-count preservation | CLOSED | Pre: 459 lines, 4 v41 amendment headings. Post: 567 lines (+108), same 4 v41 headings unchanged. v42 amendment appears strictly after v41 blocks (line 461). |
| T-407-07 | Spec-ambiguity-by-omission (Cross-Tier alternatives) | VCH-05 justification | Mitigate via explicit rejected-alternative subsections with named cost | CLOSED | `### Alternative (a) — All Arcs (rejected)` and `### Alternative (c) — File-Overlapping Arcs (rejected)` both present in deepening section. |
| T-407-08 | Edge-type opacity in closure walk | VCH-05 justification | Mitigate via `### Edge-Type Precedence in the Closure Walk` subsection | CLOSED | Subsection at line 444 declares `blocks`/`data` mandatory, `soft` excluded; cites v40 D-12. |

## Accepted Risks

None. All identified threats have technical mitigations encoded in the spec deliverables and are grep-verifiable.

## Naming-Discipline Gate

- `grep -cE '\bGSD-[0-9]' .state/build/quality/VERIFIER-CHAIN.md` = 0 (no state-deliverable identifier uses GSD form).
- Lowercase `gsd-2` appears only in the VCH-05 justification subsection as prior-art system reference, per CONTEXT.md exception.
- Canonical tier names (Arc → Stage → Slice → Step) used throughout; "Stage rollup" not "Phase rollup".
- Verifier event namespace verbatim: `state.verifier.*`.

## Audit Trail

### Security Audit 2026-05-13

| Metric | Count |
|---|---|
| Threats found | 8 |
| Closed | 8 |
| Open | 0 |
| Accepted | 0 |
| ASVS Level | 1 |
| Block-on | high |

**Method:** Inline grep audit of deliverable markdown (`.state/build/quality/VERIFIER-CHAIN.md`, `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`). Each PLAN.md `<threat_model>` block listed a grep-verifiable mitigation; each was checked against the produced artifacts.

**Auditor:** orchestrator (inline; threats all design-doc-content checkable, no code surface to scan).

**Outcome:** SECURED.
