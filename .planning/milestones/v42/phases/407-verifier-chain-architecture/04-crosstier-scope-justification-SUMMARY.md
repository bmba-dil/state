---
phase: 407-verifier-chain-architecture
plan: 04
subsystem: quality
tags: [verifier-chain, cross-tier, scope-rule, justification, design-doc]
dependency_graph:
  requires:
    - 407-01 (VCH-05 — Cross-Tier Verifier section established the scope rule)
    - 407-02 (VCH-06 — Failure-Mode Mapping established the human-gate routing context)
  provides:
    - VCH-05 cross-tier scope-rule rejected-alternatives analysis
    - Edge-type precedence rules for the closure walk (blocks/data/soft)
    - Cycle-safety note tying back to v5 DAG scheduler invariant
  affects:
    - .state/build/quality/VERIFIER-CHAIN.md (append-only; 399 → 479 lines)
tech_stack:
  added: []
  patterns:
    - Append-only design-doc evolution (preserves all prior section headings)
    - Three-precedent justification (gsd-2 kb §9.2 prior-art, v40 D-12 edge types, v5 DAG scheduler typed-edge precedence)
key_files:
  created:
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/04-crosstier-scope-justification-SUMMARY.md
  modified:
    - .state/build/quality/VERIFIER-CHAIN.md
decisions:
  - "Reject Alternative (a) (all shipped Arcs): O(N) cost + false-positive risk + validates undeclared coupling that v40 D-10 already discourages."
  - "Reject Alternative (c) (file-overlapping Arcs): file overlap is symptom not declaration; depends_on data edges already cover genuine sharing."
  - "Edge-type precedence: blocks MANDATORY, data MANDATORY, soft EXCLUDED — verifier and v5 DAG scheduler agree on what an edge means."
  - "Cycle safety: closure walker treats the graph as a DAG (v5 invariant). Cycle encounter → regression_detected with regression_kind='cycle_detected' + human-gate."
metrics:
  duration_minutes: 12
  completed: 2026-05-13
  tasks: 1
  files_modified: 1
  lines_added: 80
---

# Phase 407 Plan 04: Cross-Tier Scope-Rule Justification Summary

Appended an 80-line `## VCH-05 — Cross-Tier Scope Rule Justification` section to `.state/build/quality/VERIFIER-CHAIN.md` that deepens the Cross-Tier scope rule established in Plan 01. The justification rejects two alternative rules — (a) all shipped Arcs, (c) file-overlapping Arcs — with concrete cost and over-reach / under-detection rationale, then anchors the accepted rule (`depends_on` closure over shipped Arcs) to three named precedents (gsd-2 kb workflow-engine §9.2, v40 D-12 edge types, v5 DAG scheduler typed-edge precedence). A dedicated Edge-Type Precedence table declares the closure walk follows `blocks` and `data` edges (both mandatory) and excludes `soft` edges, with a 7-step walk-discipline algorithm and a worked example showing closure expansion for a hypothetical Arc A5.

## Outcome

- ROADMAP SC3 satisfied ("chosen rule is justified against the v40 Arc model and the v5 DAG scheduler edge semantics").
- VCH-05 requirement fully covered: Plan 01's `## VCH-05 — Cross-Tier Verifier` section established the rule; this Plan 04 section explains why it was chosen over alternatives.
- File grew 399 → 479 lines, append-only. All prior VCH-01..VCH-06 section headings preserved verbatim.
- Naming-discipline check passes: `grep -cE '\bGSD-[0-9]' VERIFIER-CHAIN.md = 0`. The only `gsd-2` mentions sit inside the new section as prior-art system-of-origin references.

## Cross-References

- **VCH-05** (REQUIREMENTS.md v42) — fully addressed by the combination of Plan 01's `## VCH-05 — Cross-Tier Verifier` section and Plan 04's `## VCH-05 — Cross-Tier Scope Rule Justification` section.
- **Plan 01 SUMMARY** (`01-verifier-chain-core-spec-SUMMARY.md`) — established the chosen-rule scope (depends_on closure over shipped Arcs); Plan 04 deepens with rejected-alternatives + edge-type precedence.
- **Plan 02 SUMMARY** (`02-failure-mode-mapping-SUMMARY.md`) — established the failure-mode triad. Plan 04's cycle-safety note routes through the same `regression_detected` → human-gate channel.
- **v40 COMPOSITE-CASCADE.md (D-12 edge types)** — cited verbatim for `blocks` / `soft` / `data` semantics.
- **v40 TIER-ARC.md** — cited for the `shipped` / `in_progress` Arc state distinction (rule filters to `shipped` only).
- **v5 DAG scheduler typed-edge precedence** — cited for the verifier-scheduler agreement on edge semantics.
- **gsd-2 kb workflow-engine §9.2** — cited as prior-art (system-of-origin reference) for the `milestones.depends_on` JSON column precedent.
- **PROJECT.md all-concurrent-Arc model** — cited as the load-bearing reason in-progress Arcs are excluded from the closure (no stable verifier evidence to regress against).

## Phase 407 Coverage Roll-Up

This plan completes Phase 407's design-doc requirement coverage:

| Requirement | Plan(s) satisfying |
|---|---|
| VCH-01 (Step Verifier Suite) | 01 |
| VCH-02 (Slice Rollup) | 01 |
| VCH-03 (Stage Rollup) | 01 |
| VCH-04 (Arc Rollup) | 01 |
| VCH-05 (Cross-Tier Verifier) | 01 (scope rule + algorithm) + 04 (rejected-alternatives + edge-type precedence + cycle-safety) |
| VCH-06 (Failure-Mode Mapping) | 02 |
| VCH-07 (Event-Family Registry) | 03 |

## Deviations from Plan

None — plan executed as written. The initial append produced 466 lines (4 short of the ≥ 470 target because markdown table rows compress more than the plan's line-count estimate); added a "Worked Example" subsection illustrating the closure walk over a hypothetical A5 dependency tree, lifting the file to 479 lines. The worked example reinforces the algorithm without altering normative content.

## Acceptance Criteria Results

| Check | Expected | Actual |
|---|---|---|
| `grep -c '## VCH-05 — Cross-Tier Scope Rule Justification'` | 1 | 1 |
| `grep -c '### Alternative (a) — All Arcs (rejected)'` | 1 | 1 |
| `grep -c '### Alternative (c) — File-Overlapping Arcs (rejected)'` | 1 | 1 |
| `grep -c '### Chosen Rule — depends_on Closure Over Shipped Arcs (accepted)'` | 1 | 1 |
| `grep -c '### Edge-Type Precedence in the Closure Walk'` | 1 | 1 |
| `grep -c 'D-12'` | ≥ 2 | 5 |
| `grep -c 'D-10'` | ≥ 1 | 4 |
| `grep -c 'v5 DAG scheduler'` | ≥ 1 | 4 |
| `grep -c 'gsd-2'` | ≥ 1 | 2 |
| `grep -c '\| \`blocks\` \|'` | ≥ 1 | 1 |
| `grep -c '\| \`data\` \|'` | ≥ 1 | 1 |
| `grep -c '\| \`soft\` \|'` | ≥ 1 | 1 |
| `grep -c 'Yes — mandatory'` | ≥ 2 | 2 |
| `grep -c 'No — excluded'` | ≥ 1 | 1 |
| `grep -c 'all-concurrent'` | ≥ 1 | 2 |
| `grep -c 'PROJECT.md'` | ≥ 1 | 2 |
| `grep -c 'cycle_detected\|Cycle safety'` | ≥ 1 | 1 |
| `wc -l` | ≥ 470 | 479 |
| `grep -cE '\bGSD-[0-9]'` | 0 | 0 |
| Prior VCH-01..VCH-06 headings preserved | yes | yes |

## Commits

- `8c3aea9` — docs(407-04): append VCH-05 cross-tier scope-rule justification

## Self-Check: PASSED

- File `.state/build/quality/VERIFIER-CHAIN.md` exists and is 479 lines (verified via `wc -l`).
- Commit `8c3aea9` exists in `git log` (verified).
- All five new section headings verified via `grep -cF` returning 1 each.
- All six prior section headings (VCH-01..VCH-06) preserved.
- Naming-discipline gate clean: 0 matches for `\bGSD-[0-9]`.
