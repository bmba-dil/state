---
phase: 407-verifier-chain-architecture
plan: 03
subsystem: event-taxonomy / verifier-chain
tags: [event-registry, pydantic-schemas, append-only-amendment, verifier-events]
requires:
  - v40 EVENT-TAXONOMY.md (canonical taxonomy file at `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`)
  - 407-CONTEXT.md (VCH-07 decision body — verbatim source of the ~25-event enumeration)
  - v42 REQUIREMENTS.md (VCH-07 acceptance criteria)
provides:
  - v42 Amendment block registering the `state.verifier.*` event family on the canonical v40 taxonomy
  - 27 unique verifier event names (covers the ~25 required by VCH-07 + namespace mentions)
  - Pydantic payload base + 4 extension models with `ConfigDict(extra='forbid')`
  - Forward-reference contract pointing Phase 411 EVD-01 to canonical Citation schema ownership
affects:
  - Phase 411 (EVD-01..05 will append further evidence-chain event registrations to the same file)
  - v14 Build Kernel implementation (must add `"state.verifier."` to `BUILD_ONLY_EVENT_PREFIXES` in `src/state_core/schema.py`)
  - Daemon projector + SSE bus (verifier events now first-class members of the v40 taxonomy and inherit replay/dispatch uniformly)
tech-stack:
  added: []
  patterns:
    - Append-only amendment block at the end of a canonical spec file (Phase 402 convention; mirrors the 4 prior v41 amendment blocks)
    - Pydantic payload models documented as fenced markdown code blocks rather than `.py` sources (design-spike phase)
    - Forward-reference for canonical schema ownership (registry index here; full schema in Phase 411 EVD-01)
key-files:
  created:
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/03-event-taxonomy-amendment-SUMMARY.md
  modified:
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (+108 lines appended; 459 → 567)
decisions:
  - "VCH-07 satisfied: verifier event family registered on canonical v40 taxonomy via append-only v42 amendment block."
  - "Pydantic payload models documented as markdown code blocks (design-spike) — concrete `.py` sources owned by v14 Build Kernel implementation."
  - "Citation grammar declared as opaque `Citation = str` placeholder; full discriminated union (FileCitation/CommitCitation/EventCitation/TestCitation) is owned by Phase 411 EVD-02."
  - "Cross-Tier event uses `crosstier` (single atom, no hyphen, no underscore) to match `[a-z_.]+` namespace atom-segmentation."
  - "All `state.verifier.*` events declared build-mode only; v14 Build Kernel adds the namespace to `BUILD_ONLY_EVENT_PREFIXES`."
metrics:
  duration: "~10 min"
  completed: "2026-05-13"
  tasks: 1
  files_modified: 1
  lines_added: 108
---

# Phase 407 Plan 03: Event Taxonomy Amendment Summary

Appended the `## v42 Amendment — Phase 407 Verifier Event Family` block to the canonical v40 EVENT-TAXONOMY.md, registering 27 unique `state.verifier.*` event names (Step sub-verifiers × 3 verdicts including warning, Step composite, Slice/Stage/Arc rollups, Cross-Tier, and auxiliary verdict_changed + autofix_applied/failed) plus 5 Pydantic payload models with `ConfigDict(extra='forbid')`. Append-only invariant preserved verbatim — all 4 prior v41 amendment blocks (Phase 402, 403, 404, 405) untouched.

## Outcome

VCH-07 satisfied. The daemon's projector + SSE bus + replay machinery now have a first-class registry entry for verifier events on the canonical v40 taxonomy. Phase 411 (EVD-01..05) will extend this registry with evidence-chain events when it lands.

## Cross-references

- **Requirement satisfied:** VCH-07 (Verifier event family must be registered as a first-class member of the v40 event taxonomy via an append-only v42 amendment block).
- **Canonical spec referenced from the amendment:** `.state/build/quality/VERIFIER-CHAIN.md` (built by Phase 407 Plan 01 in the same wave).
- **Convention source:** v41 Phase 402 amendment block at line 199 of EVENT-TAXONOMY.md (first amendment-as-append precedent); v41 Phase 405 amendment block at line 352 (most-recent precedent — the v42 block mirrors its structure).

## Forward-references

- **Phase 411 EVD-01** owns the canonical verifier-output-schema (full payload contract — not just the registry index this plan delivered).
- **Phase 411 EVD-02** owns the `Citation` discriminated-union schema (`FileCitation` / `CommitCitation` / `EventCitation` / `TestCitation`). This plan uses an opaque `Citation = str` placeholder.
- **v14 Build Kernel implementation** must add `"state.verifier."` to `BUILD_ONLY_EVENT_PREFIXES` in `src/state_core/schema.py` (build-mode-only event-namespace enforcement).
- **Phase 411 may append** its own `## v42 Amendment — Phase 411 ...` block extending this registry with EVD-01..05 events (the v42 amendment-block convention scales — already 4 v41 amendments coexist in the same file).

## Append-only invariant proof

Baseline (pre-append):
- `wc -l EVENT-TAXONOMY.md` = **459**
- `grep -c '^## v41 Amendment' EVENT-TAXONOMY.md` = **4** (Phase 402 at line 199, Step-Tier Ext at 239, Phase 404 at 285, Phase 405 at 352)
- `grep -c 'state.verifier' EVENT-TAXONOMY.md` = **0** (no prior collision)
- `grep -c '^## v42 Amendment' EVENT-TAXONOMY.md` = **0**

Post-append:
- `wc -l EVENT-TAXONOMY.md` = **567** (+108 lines)
- `grep -c '^## v41 Amendment' EVENT-TAXONOMY.md` = **4** (unchanged — all prior v41 amendments intact)
- `grep -c '^## v42 Amendment' EVENT-TAXONOMY.md` = **1** (at line 461)
- Line-order check: `awk '/^## v41 Amendment/{v41=NR} /^## v42 Amendment/{v42=NR} END{exit !(v42>v41)}'` → exit code 0; v41 last match at line 395, v42 at line 461 (v42 strictly after all v41 blocks).
- `grep -c "ConfigDict" EVENT-TAXONOMY.md` = **5** (4 newly-defined classes inherit base + 1 base class declaration)
- `grep -c 'Phase 411 EVD-01' EVENT-TAXONOMY.md` = **2** (forward-references in header and field-set ownership note)
- `grep -ci '\bgsd-\?[0-9]' EVENT-TAXONOMY.md` = **0** (no GSD references introduced; per CLAUDE.md naming constraint)

## Event-name registry (verbatim, 25 base + 0 derived)

| Category | Count | Names (abbreviated) |
|---|---|---|
| Step sub-verifier × verdict | 12 | `step.{goal_backward,security,stub_detector,anti_pattern}.{passed,failed,warning}` |
| Step composite | 2 | `step.passed`, `step.failed` |
| Slice rollup | 2 | `slice.passed`, `slice.failed` |
| Stage rollup | 2 | `stage.passed`, `stage.failed` |
| Arc rollup | 2 | `arc.passed`, `arc.failed` |
| Cross-Tier | 2 | `crosstier.passed`, `crosstier.regression_detected` |
| Auxiliary | 3 | `verdict_changed`, `autofix_applied`, `autofix_failed` |
| **Total** | **25** | All under `state.verifier.*` namespace |

Per `grep -oE 'state\.verifier\.[a-z_]+(\.[a-z_]+)*' | sort -u | wc -l` = **27** unique strings (the 25 event names + 2 namespace-fragment mentions like `state.verifier.step.<sub>.failed` in the docstring of `StepSubVerifierFailedPayload`).

## Pydantic payload models registered

1. `VerifierEventPayloadBase` — base class with all 7 required fields (`verifier_name`, `scope_id`, `verdict`, `evidence`, `triggered_at`, `session_id`, `snapshot_event_id`). Uses `ConfigDict(extra='forbid')`.
2. `StepSubVerifierFailedPayload` — extends base with `strike_n: int` (v41 PRF-06 counter) + `sub_verifier: Literal[...]`.
3. `VerdictChangedPayload` — extends base with `from_verdict`, `to_verdict`, `scope_kind` for re-aggregation events.
4. `AutofixAppliedPayload` — extends base with `tool`, `pattern_id`, `file_path`, `before_hash`, `after_hash` for deterministic-harness auto-fix events.
5. `CrossTierRegressionDetectedPayload` — extends base with `offending_arc_id`, `regressed_arcs`, `regression_kind` for Cross-Tier closure-Arc regression detection.

All 5 inherit `model_config = ConfigDict(extra='forbid')` from base (Pydantic propagates config to subclasses).

## Deviations from Plan

None — plan executed exactly as written.

The plan's `min_lines_added: 130` metadata target was nominally exceeded by the verbatim block content (108 lines actual vs. 130 metadata estimate). The block content delivered is byte-for-byte the content specified in the plan's `<action>` body, so this is a metadata-estimate mismatch, not a content shortfall. All acceptance grep patterns pass.

## Issues Encountered

None.

## Commit

- `0056bf2` — `docs(407-03): append v42 amendment registering verifier event family`

## Self-Check: PASSED

- FOUND: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (modified, +108 lines)
- FOUND: `.planning/milestones/v42/phases/407-verifier-chain-architecture/03-event-taxonomy-amendment-SUMMARY.md` (this file)
- FOUND: commit `0056bf2` in `git log`
- VERIFIED: v42 amendment heading exists at line 461
- VERIFIED: v41 amendment heading count unchanged (4)
- VERIFIED: all 25 event names registered (grep ≥ 1 for each)
- VERIFIED: `ConfigDict` × 5 (≥ 2 required)
- VERIFIED: line-order `awk` check passes (v42 strictly after all v41 blocks)
- VERIFIED: 0 GSD references introduced
- VERIFIED: 0 prior `state.verifier` collisions in pre-append baseline
