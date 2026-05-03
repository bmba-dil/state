---
phase: quick-3
plan: revise-roadmap-md-to-apply-review-roadma
subsystem: planning-docs
tags: [roadmap, state, review-apply, vocabulary, P0-threading]
dependency_graph:
  requires: [REVIEW-ROADMAP.md, 3-CONTEXT.md, 3-RESEARCH.md]
  provides: [ROADMAP.md revised, STATE.md reconciled, Revision History section]
  affects: [v27 P0-14 ownership, Tier-1 DAG accuracy, v16 vocabulary disambiguation]
tech_stack:
  added: []
  patterns: [content-anchored edits, single-line parser-safe depends-on, compound-sentence verifiers]
key_files:
  created:
    - .planning/quick/3-revise-roadmap-md-to-apply-review-roadma/3-SUMMARY.md
  modified:
    - .planning/ROADMAP.md
    - .planning/STATE.md
decisions:
  - Use W1 + W1-prep split (renumber-less) rather than shifting W2..W11
  - Preserve compound-sentence verifier style over bulleted sub-lists
  - Relabel v16 only (no structural phase moves to v15)
  - Add reciprocal "(shared with v13)" to v12 P0-12 line (standardize-shares path)
  - Keep the literal string "267→256" in Revision History prose (documents the change)
metrics:
  duration: "~25 minutes"
  completed: "2026-04-22"
  tasks_total: 8
  tasks_completed: 8
  deviations: 0
  auth_gates: 0
---

# Quick Task 3: Revise ROADMAP.md + STATE.md to apply REVIEW-ROADMAP findings — Summary

Applied all 8 REVIEW-ROADMAP.md §7 MAJORs and 7 approved MINOR batches across `.planning/ROADMAP.md` and `.planning/STATE.md`, plus a dated Revision History footer for traceability. No source code touched. All edits stayed within the two planned files per scope decision.

## MAJORs Applied (1:1 against REVIEW §7)

| # | REVIEW finding | Resolution |
|---|----------------|-----------|
| §5d | Phase-count drift 267 vs 256 | Flipped all 7 sites — STATE.md (lines 26, 58, 65, 155) + ROADMAP.md (lines 17, 169, 2705) to **256** |
| §5a | Tier-1 parallel-safe overstatement | STATE.md line 42 reworded to name v3 soft-dep + v5 hard-dep; ROADMAP DAG parenthetical at line 77 rewritten; wave table split into `W1` + `W1-prep` (renumber-less) |
| §3 v27 | P0-14 co-ownership gap | v27 frontmatter gained `**P0 pitfalls owned:** P0-14 (shared with v2 — release-time redactor regression in 255)` |
| §5c | "most of v1..v24" vacuous depends-on | v27 + 253 + 254 all rewritten with enumerated hard + soft lists (parser-safe single-line) |
| §6 v11 | Verifier names only 3 of 6 layers | Rewritten to name all 6 (disk / MCP registration / plugin hooks / command dispatch / daemon HTTP middleware / Python import-graph lint) with phase cross-references + 105 integrating test |
| §6 v14 | Verifier names only 3 of 6 artifacts | Rewritten to name all 6 (Step FSM / goal-backward / Slice rollup / product-Phase rollup / product-Arc rollup / cross-tier / security-part-1) + 134 integrating |
| §6 v20 | Verifier single compound sentence | Rewritten with 4 mode FSMs + selector boundaries + override + drop + temperature + system-prompts + 197 integrating |
| §3 v16 | Scope mismatch vs "GSD command ports" label | Relabeled header + Summary Checklist to "...+ Net-New Product-Hierarchy Commands"; disambiguator paragraph added; goal split into ports + net-new; verifier split into 3 assertion classes (file-emitter / subagent-spawning / batch-DAG) |

## MINOR Batches Applied

- **§2a domain-vocab (7 sites):** structural note line 8; branch-naming fan-out lines 513 + 539 (`slice/<arc-id>/<product-phase-id>/<slice-id>`); 126 heading (Product Slice/Phase/Arc); 130 heading + goal (Product-Arc rollup); v16 goal split (covered by §3 v16 MAJOR); 157 covered by disambiguator; 159 inline gloss.
- **v2 goal + verifier:** 3-clause splits (five-method operational / refresh+redaction+0600 / multi-cred fan-out).
- **132 rename:** "Security verifier (part 1 — input guards: ...)" signals 256 hand-off.
- **187 reframing:** heading + goal rewritten from decision framing to scaffolding-implementation framing (SUMMARY Q2 already resolved per STATE.md line 92).
- **254 P0-test matrix:** `.state/build/p0-test-matrix.md` declared in goal + success-criterion #4 cross-reference.
- **256 P0-13 thread:** chmod-0600 verifier now explicitly re-runs the P0-13 regression harness from 012.
- **Shares wording standardization:** v12 P0-12 line gained `(shared with v13)` reciprocal; v27 P0-14 line uses consistent `(shared with v2 — ...)` wording.

## Deferred (per CONTEXT)

- **NIT §5b/§5c phase-level edge tightening** (099/P4, 084, v17 → 133): single-line HTML-comment TODO inserted after DAG code fence (around line 106).
- **REQUIREMENTS.md 221/229 off-by-one** (REVIEW §4 MINOR): explicitly out of scope per CONTEXT; noted in Revision History.

## Line-Drift Observations

| Planned coordinate (3-RESEARCH) | Actual at edit time | Resolution |
|-------------------------------|--------------------|-----------|
| ROADMAP line 77 (DAG Tier-1 parenthetical) | Still line 77 | No drift |
| ROADMAP line 116 (W1 wave row) | Still line 116 | No drift |
| ROADMAP line 510 (branch-name success-criterion) | Line **513** post-Task-2 | Re-anchored by content |
| ROADMAP line 536 (035 heading) | Line **539** | Re-anchored |
| ROADMAP line 1128 (v11 verifier) | Line **1131** | Re-anchored |
| ROADMAP line 1397 (v14 verifier) | Line **1400** | Re-anchored |
| ROADMAP line 1422 (126 heading) | Line **1425** | Re-anchored |
| ROADMAP line 1446–1447 (130) | Lines **1449–1450** | Re-anchored |
| ROADMAP line 1458 (132 heading) | Line **1461** | Re-anchored |
| ROADMAP line 1573 (v16 header) | Line **1576** | Re-anchored |
| ROADMAP line 1593 (v16 verifier) | Line **1596** (pre-edit) | Re-anchored |
| ROADMAP line 1722 (159 goal) | Line **1727** | Re-anchored |
| ROADMAP line 1993 (v20 verifier) | Line **1996** | Re-anchored |
| ROADMAP line 2006–2007 (187) | Lines **2011–2012** | Re-anchored |
| ROADMAP line 2578 (v27 depends-on) | Line **2581** | Re-anchored |
| ROADMAP line 2580 → insert P0-14 line | Inserted after `**Complexity:** M` line 2583 | Re-anchored |
| ROADMAP line 2601 (success-criterion #4) | Line **2607** | Re-anchored |
| ROADMAP line 2644 / 2649 / 2650 / 2655 / 2661 | All +6 shifts (P0-14 insert + earlier growth) | Re-anchored every time |

All drift absorbed by content-anchored `old_string` matches; no invented text.

## Findings Unable to Apply

None. All in-scope REVIEW findings actionable at the documented coordinates.

## Verification Grep Summary

```
=== 1. Phase-count consistency ===
STATE.md "256" = 4; ROADMAP.md "256" = 4
STATE.md "267" = 0; ROADMAP.md "267" = 1  (only in Revision History prose describing the fix)

=== 2. Parallel-safe coherence ===
STATE.md "v3 soft-depends" = 1
ROADMAP.md "W1-prep" = 2  (table row + Revision History mention)
ROADMAP.md "all independent" = 0

=== 3. v27 P0-14 + enumeration ===
"P0-14 (shared with v2" = 1
"247 (hard" = 1
"all other v1..v26 (soft" = 1
"most of v1..v24" = 1  (only in Revision History prose — documents the deprecated phrasing)

=== 4. Verifier expansions ===
"All 6 layers individually tested" = 1
"134 10-Step golden-fixture suite" = 1
"197 four-mode golden-fixture" = 1

=== 5. v16 relabel ===
"Build GSD Command Ports + Net-New Product-Hierarchy Commands" = 2  (checklist + header)
"Disambiguator (vocabulary)" = 1
"Three assertion classes" = 1

=== 6. Vocabulary fan-out ===
"slice/<arc>/<phase>" = 0  (both fan-out sites renamed)
"product-phase-id" = 2

=== 7. v27 P0 threading + matrix ===
"P0-14 release-time redactor regression re-runs here" = 1
"re-runs the P0-13 regression harness from 012" = 1
"p0-test-matrix.md" = 3  (P8 goal + success-criterion #4 + Revision History)

=== 8. Revision History footer ===
"^## Revision History" = 1
"quick-task-3" = 1
"REVIEW-ROADMAP.md applied" = 1

=== 9. Parser-safety ===
Single-line "**Depends on:**" entries = 283

=== 10. Vocabulary cardinal rule not violated ===
"GSD (Arc|Slice|Step)" = 0
```

## Commit Summary

8 atomic per-task commits, each prefixed `docs(roadmap-3):`:

1. `a6f9b59` sync phase count 267 to 256 across STATE and ROADMAP
2. `972f995` correct Tier-1 parallel-safe claim and split wave table
3. `929dce4` enumerate v27 depends-on and declare P0-14 co-ownership
4. `b47cd9b` expand v11/v14/v20 verifier lines to name all artifacts
5. `9984aef` relabel v16 + add disambiguator + split verifier into 3 classes
6. `4bd96a1` apply MINOR batches — §2a vocab + v2 splits + P9/P1 renames
7. `1c581e0` thread P0-13/P0-14 hand-offs and declare P0-test matrix
8. `6a661d5` add Revision History footer section for traceability

## Self-Check: PASSED

All 8 task commits present on `main`; ROADMAP.md + STATE.md modifications verified via grep; Revision History footer present between final `---` break and italic credits; no in-scope REVIEW findings left open.
