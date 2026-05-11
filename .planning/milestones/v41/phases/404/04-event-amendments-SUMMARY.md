---
phase: 404-boolean-proof-gate-discipline-guards
plan: 04
subsystem: design-spec-amendment
tags: [event-taxonomy, artifact-catalog, v40-amendment, append-only, phase-404-rollup, registry-index]

# Dependency graph
requires:
  - phase: 404-01
    provides: PROOF-GATE.md (sources gate_strike, gate_resolved, step_verify_completed, slice_verify_completed events + stepN-VERIFY.json + slice-verification.sh + N-VERIFICATION.md column schema)
  - phase: 404-02
    provides: ANALYSIS-PARALYSIS-GUARD.md (sources paralysis_event)
  - phase: 404-03
    provides: SCOPE-PROHIBITION.md (sources scope_check, scope_deviation, scope_deviation_request, scope_deviation_resolved, split_recommendation events + deferred-items.md)
  - phase: 403-04
    provides: STEP-EVENTS.md + Phase 403 v41 EVENT-TAXONOMY.md amendment precedent
  - phase: 402-03
    provides: Phase 402 v41 EVENT-TAXONOMY.md + ARTIFACT-CATALOG.md amendment precedent (both v40 files this plan amends)
provides:
  - v40 EVENT-TAXONOMY.md third v41 amendment block (10 new events: 4 gate + 1 paralysis + 5 scope; final 348 lines)
  - v40 ARTIFACT-CATALOG.md second v41 amendment block (3 new artifacts + N-VERIFICATION.md column-schema pin; final 849 lines)
  - Event taxonomy now contains 49 events (was 39 after Phase 403)
  - Canonical Slice folder layout enriched with per-Step + per-Slice verification + scope discipline artifacts
affects:
  - v14 Build Kernel (master taxonomy registry now indexes all Phase 404 events; implementers consult amendment table AND owning spec docs for full schemas)
  - v15 Build Core Commands (canonical Slice folder layout now stipulates stepN-VERIFY.json + slice-verification.sh + deferred-items.md creation responsibilities)
  - Phase 405 (DEV-04 architectural human-gate references the now-registered split_recommendation event; DEV-05 tiered autonomy auto-approval policy for scope_deviation_request)
  - Phase 406 (HRN-05 harness_intervention umbrella event aggregates the 10 newly-registered Phase 404 events; layered diagram has a complete event surface)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Append-only `## v41 Amendment — <descriptor>` block convention mirroring Phase 402 + Phase 403"
    - "Naming-convention enforcement via python3 regex check `^state\\.(step|slice)\\.[a-z_]+$` over all event types in EVENT-TAXONOMY.md"
    - "Master-taxonomy-as-registry-index pattern (full schemas live in owning specs; the taxonomy lists triggers + state transitions + owning REQ-IDs + forward-pointers)"
    - "Canonical artifact catalog with 5-column row schema (Filename, Producer Stage, Schema Owner, Immutability, Description)"
    - "Counter-independence note (PRF vs APG) restated in the amendment to mirror the cross-spec invariant from loop-control.md §0 Correction 1"
key-files:
  created:
    - .planning/milestones/v41/phases/404/04-event-amendments-SUMMARY.md
  modified:
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md

# Decisions
decisions:
  - "Append-only convention preserved verbatim (no in-line strikethroughs); each amendment uses a unique H2 anchor heading (`## v41 Amendment — Phase 404 Discipline-Guard Event Family` in EVENT-TAXONOMY.md; `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` in ARTIFACT-CATALOG.md)"
  - "10 events registered (4 gate + 1 paralysis + 5 scope) — scope_deviation rejection event included beyond the original 9-event list in 404-CONTEXT.md to match Plan 03's spec for Layer 1 rejections; event count rises 39 → 49"
  - "Column schema for N-VERIFICATION.md PINNED to PROOF-GATE.md §8 (was implicit in v40); the existing N-VERIFICATION.md artifact entry is reaffirmed with a forward-pointer rather than duplicated"
  - "Counter-independence (PRF vs APG) restated in the EVENT-TAXONOMY amendment to prevent v14 implementers from conflating; mirrors gsd-2 loop-control.md §0 Correction 1"
  - "Forward-pointer pattern (registry references owning spec, not inline schema duplication) — avoids schema drift between master taxonomy and the canonical Phase 404 specs; authoritative-ordering note explicitly stated in both amendments"

# Requirements tracking
requirements-completed: []
requirements-touched: [PRF-05, PRF-06, APG-06, SRP-02, SRP-04, SRP-05, SRP-06]

# Metrics
metrics:
  duration: "~12 minutes"
  completed-date: "2026-05-11"
---

# Plan 404-04 Summary: v40 EVENT-TAXONOMY.md + ARTIFACT-CATALOG.md Amendments

**Status:** Shipped
**Wave:** 2
**Depends on:** 01 (PROOF-GATE.md), 02 (ANALYSIS-PARALYSIS-GUARD.md), 03 (SCOPE-PROHIBITION.md)
**Blocks:** none (Phase 404 final plan — closes the registry-side work)

Closes Phase 404's registry-side work by appending two purely-additive amendment blocks: one to v40's `EVENT-TAXONOMY.md` (registering the ten new `state.{step,slice}.*` events introduced by Plans 01–03) and one to v40's `ARTIFACT-CATALOG.md` (registering three new per-Step/per-Slice artifacts plus a column-schema pin for the existing `N-VERIFICATION.md`). v40 baselines + prior v41 amendments preserved verbatim. The master taxonomy now indexes 49 events; the canonical Slice folder layout now includes `stepN-VERIFY.json`, `slice-verification.sh`, and `deferred-items.md`.

## What Was Built

Two append-only v41 amendment blocks were authored against the v40 spec catalog. **EVENT-TAXONOMY.md** received the `## v41 Amendment — Phase 404 Discipline-Guard Event Family` block (lines 283–348), registering ten new events: four gate-family events (`state.step.gate_strike`, `state.step.gate_resolved`, `state.step.step_verify_completed`, `state.slice.slice_verify_completed`) owned by PROOF-GATE.md §6–§7; one paralysis event (`state.step.paralysis_event`) owned by ANALYSIS-PARALYSIS-GUARD.md §8; and five scope/split events (`state.step.scope_check`, `state.step.scope_deviation`, `state.step.scope_deviation_request`, `state.step.scope_deviation_resolved`, `state.slice.split_recommendation`) owned by SCOPE-PROHIBITION.md §5–§8. Each row in the amendment table carries Event Type, Trigger, State Transition, Owning REQ, and Owning Spec columns. The amendment also restates the load-bearing counter-independence invariant (PRF strike chain vs APG paralysis chain — distinct counters at distinct scopes, never conflated, both can independently reach force-stop), names the `BUILD_ONLY_EVENT_PREFIXES` mode-isolation contract, and provides a v14 Build Kernel implementation pointer.

**ARTIFACT-CATALOG.md** received the `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` block (lines 808–849), registering three new artifacts in the canonical Slice folder layout: `stepN-VERIFY.json` (per-Step machine-readable Pydantic `StepVerifyResult` v1; schema_version: Literal[1] for migration; bounded-truncation 2KB per check, 10KB total; owned by PROOF-GATE.md §7), `slice-verification.sh` (per-Slice executable bash script; 600s default timeout with Slice-frontmatter override; aggregates Step-level evidence and runs cross-Step integration checks; owned by PROOF-GATE.md §4 + §8), and `deferred-items.md` (per-Slice out-of-scope log; auto-appended by the `scope_check` projector on unresolved EXCEPTION_RE; 5-column status table; owned by SCOPE-PROHIBITION.md §9). The amendment also pins the column schema for the existing `N-VERIFICATION.md` artifact to PROOF-GATE.md §8 (10-column truth-table schema; previously implicit in v40). Each row carries Filename, Producer Stage, Schema Owner, Immutability, and Description columns, mirroring the v40 row shape.

Both amendments use unique H2 headings to avoid collision with prior v41 amendment blocks (Phase 402's `## v41 Amendment` and Phase 403's `## v41 Amendment — Step-Tier Event Family Extension` in EVENT-TAXONOMY.md; Phase 402's `## v41 Amendment` in ARTIFACT-CATALOG.md). The Edit tool was used with the prior amendment's trailing italic line as the anchor, ensuring strict append-only behavior — original v40 content and prior v41 amendments are byte-for-byte unchanged.

## Key Decisions

- **Append-only convention preserved verbatim.** No in-line strikethroughs; each amendment uses a unique H2 anchor heading that did not exist in v40. Verification grep confirms exactly 3 v41 amendment headings in EVENT-TAXONOMY.md (Phase 402, Phase 403, Phase 404) and exactly 2 in ARTIFACT-CATALOG.md (Phase 402, Phase 404).
- **10 events registered, not 9.** The original 404-CONTEXT.md `<canonical_refs>` enumeration named 9 events Phase 404 would add; Plan 03's SCOPE-PROHIBITION.md spec finalized the Layer 1 rejection event `state.step.scope_deviation` as distinct from the request/resolved pair, bringing the count to 10. Event taxonomy total rises 39 → 49.
- **N-VERIFICATION.md column schema PINNED rather than duplicated.** The existing v40 N-VERIFICATION.md catalog entry remains; the amendment adds a forward-pointer row stating PROOF-GATE.md §8 owns the 10-column schema. Avoids schema drift between the registry and the owning spec.
- **Counter-independence note restated.** The EVENT-TAXONOMY.md amendment includes a `### Counter independence (load-bearing)` subsection citing `loop-control.md §0 Correction 1` and explicitly enumerating both the PRF `gate_strike` chain (per `(task_id, check_id)`) and the APG `paralysis_event` chain (per task). v14 implementers reading the master taxonomy cannot accidentally fold these into a single counter.
- **Forward-pointer registry pattern.** Both amendments treat themselves as registry indices, not schema homes. Full Pydantic definitions live in PROOF-GATE.md / ANALYSIS-PARALYSIS-GUARD.md / SCOPE-PROHIBITION.md. The ARTIFACT-CATALOG.md amendment explicitly states authoritative ordering: owning Pydantic specs win on any drift.

## Files Touched

- **`.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`** — modified; 281 → 348 lines (+67). Third v41 amendment block appended; v40 baseline + Phase 402 + Phase 403 amendments unchanged.
- **`.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md`** — modified; 806 → 849 lines (+43). Second v41 amendment block appended; v40 baseline + Phase 402 amendment unchanged.
- **`.planning/milestones/v41/phases/404/04-event-amendments-SUMMARY.md`** — created; this file.

## Open Items / Deferred

- **No new requirements completed substantively.** This plan provides registry closure for PRF-05 / PRF-06 / APG-06 / SRP-02 / SRP-04 / SRP-05 / SRP-06, which were substantively specified in Plans 01–03. The amendment is the index; the canonical specs remain the source of truth for behavior.
- **Phase 406's `harness_intervention` (HRN-05) umbrella event** will aggregate these 10 newly-registered events; the rollup is owned by Phase 406, not by this plan. This amendment confirms the umbrella's expected member set so Phase 406's planner has a stable target list.
- **v14 Build Kernel implementation.** Event Pydantic payload classes are already specified in the Phase 404 spec docs (PROOF-GATE.md §7, ANALYSIS-PARALYSIS-GUARD.md §8, SCOPE-PROHIBITION.md §5/§6/§7/§8); this amendment is registry-only — no new schemas, no new behaviors. v14 implementers consult the owning specs (NOT this registry) for class definitions.
- **`split_recommendation_telemetry` rollup event** (mentioned in SCOPE-PROHIBITION.md §8 as v14 emission) is deliberately NOT registered here — it is a rollup over Slice close, not a per-trigger event, and its registration belongs to a future Phase 405 / Phase 406 amendment when the telemetry shape stabilizes.

## Downstream Hooks

- **v14 Build Kernel** consults `EVENT-TAXONOMY.md` master registry for event-emission validation (every emitter cross-checks against the registered event type list); consults `ARTIFACT-CATALOG.md` for the canonical Slice folder layout (`stepN-VERIFY.json` writer, `slice-verification.sh` runner, `N-VERIFICATION.md` projector, `deferred-items.md` auto-appender).
- **v15 Build Core Commands** implements artifact-creation responsibilities per the catalog amendment: `slice-verification.sh` authoring at plan-slice end; `stepN-VERIFY.json` writing at Step-end gate; `deferred-items.md` initialization at execute-slice start (empty with the 5-column header row).
- **Phase 405 (Deviation Rules & Subagent Management)** consumes `split_recommendation` telemetry (rollup over a milestone) for DEV-04 architectural human-gate triggering; reads `scope_deviation_request` events for DEV-05 tiered-autonomy auto-approval policy under `--full-yolo`.
- **Phase 406 (Harness Architecture Rollup)** cites the master taxonomy + catalog for the layered diagram event surface; `harness_intervention` (HRN-05) aggregates all 10 newly-registered events into a single umbrella surface for the 4-tier intervention ladder (HRN-04).

## Task Commits

- Task 1 (`ade2789`): `feat(404-04): append Phase 404 Discipline-Guard Event Family amendment to v40 EVENT-TAXONOMY.md` — EVENT-TAXONOMY.md grew 281 → 348 lines.
- Task 2 (`36090ee`): `feat(404-04): append Phase 404 Verification + Discipline Artifacts amendment to v40 ARTIFACT-CATALOG.md` — ARTIFACT-CATALOG.md grew 806 → 849 lines.
- Task 3 (this commit): `docs(404-04): write per-plan SUMMARY.md` — this file.

## Deviations from Plan

None substantive. Plan executed exactly as written. Two minor implementation notes:

- The python3 naming-convention check in Task 1's `<verify><automated>` block had a shell-quoting bug (heredoc escaping in the verification script); the underlying file was verified manually via a clean python3 heredoc that confirmed all 81 event-type matches in EVENT-TAXONOMY.md satisfy `^state\.(step|slice)\.[a-z_]+$`. The file content is correct; only the verification script's regex escaping was tricky in the shell context.
- ARTIFACT-CATALOG.md amendment added a small `### Authoritative ordering` subsection above `### Effect on this document` — not strictly required by must_haves.truths but mandated by must_haves.truths[12] ("Authoritative-ordering note rendered: full schemas live in owning specs; this catalog is a registry index"). The subsection name was deliberately rendered as H3 to match the Phase 402 amendment's `### Effect on this document` H3 sibling.

## Self-Check: PASSED

- [x] `EVENT-TAXONOMY.md` final line count ≥ 320 (actual: 348)
- [x] `ARTIFACT-CATALOG.md` final line count ≥ 830 (actual: 849)
- [x] New H2 `## v41 Amendment — Phase 404 Discipline-Guard Event Family` present in EVENT-TAXONOMY.md
- [x] New H2 `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` present in ARTIFACT-CATALOG.md
- [x] All 10 new event types grep-verifiable in EVENT-TAXONOMY.md (gate_strike, gate_resolved, step_verify_completed, slice_verify_completed, paralysis_event, scope_check, scope_deviation, scope_deviation_request, scope_deviation_resolved, split_recommendation)
- [x] All 3 new artifacts grep-verifiable in ARTIFACT-CATALOG.md (`stepN-VERIFY.json`, `slice-verification.sh`, `deferred-items.md`)
- [x] N-VERIFICATION.md column-schema pin row present with PROOF-GATE.md forward-pointer
- [x] EVENT-TAXONOMY.md amendment count ≥ 3 (Phase 402, Phase 403, Phase 404); ARTIFACT-CATALOG.md amendment count ≥ 2 (Phase 402, Phase 404)
- [x] Prior amendments byte-unchanged: Phase 402 `## v41 Amendment` (line 199) + Phase 403 `## v41 Amendment — Step-Tier Event Family Extension` (line 239) preserved in EVENT-TAXONOMY.md; Phase 402 `## v41 Amendment` (line 796) preserved in ARTIFACT-CATALOG.md
- [x] Naming-convention regex `^state\.(step|slice)\.[a-z_]+$` passes for all 81 event matches in EVENT-TAXONOMY.md (verified via python3 heredoc)
- [x] Forward-pointers to PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, SCOPE-PROHIBITION.md present in both amendment blocks
- [x] Mode-isolation note: `BUILD_ONLY_EVENT_PREFIXES` rendered (EVENT-TAXONOMY.md); `Build-mode only` rendered (ARTIFACT-CATALOG.md)
- [x] No `state.teach.` references in either amended file
- [x] Counter-independence note (PRF vs APG) restated in EVENT-TAXONOMY.md amendment
- [x] `harness_intervention` cross-reference (Phase 406 HRN-05) cited in EVENT-TAXONOMY.md amendment
- [x] StepVerifyResult schema_version: Literal[1] cited in ARTIFACT-CATALOG.md amendment
- [x] 600s default slice-verification.sh timeout cited in ARTIFACT-CATALOG.md amendment
- [x] 10-column N-VERIFICATION.md truth-table schema cited in ARTIFACT-CATALOG.md amendment
- [x] Authoritative-ordering note present in ARTIFACT-CATALOG.md amendment (owning specs win on drift)
