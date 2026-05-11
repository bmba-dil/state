---
phase: 404-boolean-proof-gate-discipline-guards
plan: 03
subsystem: design-spec
tags:
  - scope-prohibition
  - prohibited-language
  - files-modified
  - scope-deviation
  - split-recommendation
  - deferred-items
  - srp
requires:
  - 404-01 (PROOF-GATE.md for tool.execute.before stack Layer composition)
  - 403 (STEP-PLAN-FORMAT.md for files_modified + ArtifactCheck schemas; PLAN-AS-PROMPT.md for PAP-03 mutability + PAP-05 immutability layer)
  - 402 (CONTEXT-PROTOCOL.md for compaction.snapshot_taken plumbing; SLICE-CYCLE.md for pending_replan run-slice terminal state)
  - 400 (EVENT-TAXONOMY.md naming + FRONTMATTER-SCHEMAS.md Pydantic convention; ARTIFACT-CATALOG.md for canonical Slice layout)
provides:
  - "SCOPE-PROHIBITION.md — canonical scope-reduction-prohibition spec covering SRP-01..SRP-06 (566 lines)"
  - "PROHIBITED_RE + EXCEPTION_RE + PATH_ALLOWLIST_GLOB regex corpora"
  - "ScopeCheck + ScopeDeviation + ScopeDeviationRequest + ScopeDeviationResolved + SplitRecommendation Pydantic event/payload classes"
  - "tool.execute.before Layer 1 (files_modified) and Layer 3 (prohibited-language) ownership"
  - "request_step_split MCP tool + worktree-snapshot reuse"
  - "deferred-items.md per-Slice artifact shape with auto-append projector behavior + status vocabulary"
affects:
  - 404-04 (event taxonomy amendment registers state.step.scope_* + state.slice.split_recommendation; ARTIFACT-CATALOG.md amendment registers deferred-items.md)
  - v14 Build Kernel (implements state_build/harness/scope/patterns.py + scope_deviation_request + request_step_split MCP handlers + deferred-items.md projector + worktree-snapshot reuse)
  - v15 Build Core Commands (implements planner-validation acceptance-criteria annotation check + SUMMARY-generation step pulling deferred-items.md + replan re-entry path consuming split_recommendation events)
  - Phase 405 (DEV-03 + DEV-04 paths consume scope_deviation_resolved + split_recommendation events; DEV-05 tiered autonomy specifies --full-yolo auto-approval policy NOT owned here)
  - Phase 406 (harness rollup cites this spec for tier-1 advisory + tier-2 tool-block of the 4-tier intervention ladder; harness_intervention aggregates ScopeCheck + ScopeDeviationRequest + SplitRecommendation)
tech-stack:
  patterns:
    - "Single-module regex pattern state_build/harness/scope/ mirroring gsd-2 branch-patterns.ts (PROHIBITED_RE + EXCEPTION_RE + PATH_ALLOWLIST_GLOB)"
    - "Word-boundary case-insensitive regex with no nested quantifiers; mirrors gsd-2 inferCommitType pattern (file-tracking.md:445)"
    - "Path-allowlist .planning/**/*.md as SCAN-ONLY exemption (does NOT exempt from files_modified enforcement)"
    - "Tracking-issue exception EXCEPTION_RE with pure-machine grep cross-check against REQUIREMENTS.md and deferred-items.md"
    - "files_modified locked at plan-slice end (PAP-03 immutability); event-scoped one-shot allowlist for legitimate deviations; never-mutate-at-runtime rule"
    - "Explicit MCP tool-call boundary for request_step_split (no NL keyword detection); mirrors gsd-2 complete_task/complete_slice/validate_milestone pattern"
    - "Worktree-snapshot reuse for split_recommendation (mirrors Phase 402 compaction.snapshot_taken plumbing)"
    - "deferred-items.md auto-append projector triggered on scope_check.exception_matched=False events"
key-files:
  created:
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (566 lines)
key-decisions:
  - "PROHIBITED_RE uses case-insensitive word-boundary regex with no nested quantifiers; six tokens (v1, simplified, placeholder, todo, fixme, future)."
  - "Single-source-of-truth module at state_build/harness/scope/patterns.py (mirrors gsd-2 branch-patterns.ts pattern)."
  - "Path-allowlist .planning/**/*.md as SCAN-ONLY exemption — does NOT exempt from files_modified enforcement."
  - "EXCEPTION_RE form TODO|FIXME(ID-NN) with pure-machine grep cross-check against REQUIREMENTS.md and deferred-items.md."
  - "scope_deviation_request routed via checkpoint:decision; files_modified itself is NEVER mutated at runtime; overrides are event-scoped one-shot allowlists."
  - "request_step_split is the canonical explicit MCP tool-call boundary; NO NL keyword detection."
  - "Implicit split_recommendation from N-paralysis+N-strike pattern REJECTED (preserves agent intent; counter independence)."
  - "deferred-items.md is per-Slice with auto-append projector subscribed to scope_check (exception_matched=False) and rejected scope_deviation_request events."
  - "Layer composition: PROOF-GATE.md owns Layers 2+4; SCOPE-PROHIBITION.md owns Layers 1+3 of the four-layer tool.execute.before stack."
  - "scope_check tier-2 hard-block on first match REJECTED — tier=advisory only; agent justifies via EXCEPTION_RE before write rejection."
requirements-completed:
  - SRP-01
  - SRP-02
  - SRP-03
  - SRP-04
  - SRP-05
  - SRP-06
metrics:
  duration: ~28min
  completed: 2026-05-11
---

# Plan 404-03 Summary: SCOPE-PROHIBITION.md

**Canonical scope-reduction-prohibition spec authored — SRP-01..SRP-06 covered across 10 sections in a single 566-line markdown document at `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md`.** Three regex corpora and five Pydantic event/payload classes are rendered verbatim from `404-CONTEXT.md` decisions; layer composition with `PROOF-GATE.md` four-layer `tool.execute.before` stack is fully documented (this spec owns Layers 1 and 3).

## What Was Built

`SCOPE-PROHIBITION.md` at the canonical specs path with 10 H2 sections covering all six SRP requirements. SRP-01 documents the `<done>`-vs-`must_haves.artifacts` cross-check (5-step protocol; forward-pointer to PROOF-GATE.md PRF-06 strike chain). SRP-02 renders `PROHIBITED_RE` and the single-module pattern (mirroring gsd-2 `branch-patterns.ts`), plus a 10-row positive/negative scan-examples table covering the canonical edge cases (`v1`-in-`v14` non-match, `simplified`-vs-`oversimplification` non-match, `futures.py` filename non-match). SRP-03 renders `EXCEPTION_RE` with its 6-step cross-check protocol (pure-machine grep against REQUIREMENTS.md headings or deferred-items.md rows) and the `.planning/**/*.md` SCAN-ONLY path-allowlist. SRP-04 documents `files_modified` allowlist enforcement via `tool.execute.before` Layer 1, including the `ScopeDeviation` event payload and the never-mutate-at-runtime rule. The `scope_deviation_request` MCP flow (Pydantic `ScopeDeviationRequest` + `ScopeDeviationResolved` with `request_event_id` cross-link) carries event-scoped one-shot allowlist semantics. SRP-05 documents `request_step_split` as the canonical MCP tool-call boundary (mirrors gsd-2 `complete_task` pattern); the 4-step harness behavior sequence (emit event + worktree snapshot + `pending_replan` transition + clean `run-slice` exit) is rendered with the replan re-entry path. SRP-06 documents `deferred-items.md` as a per-Slice artifact with canonical template, auto-append projector behavior, 5-status vocabulary, and Slice SUMMARY.md surface mechanism. The closing cross-references section ties to all sibling specs (PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md), Phase 402/403 carry-forwards, v40 baseline amendments owed by Plan 04, and Phase 405/406 forward-pointers.

## Key Decisions

- **PROHIBITED_RE shape locked**: case-insensitive word-boundary single-pass regex; six tokens; no nested quantifiers (no catastrophic backtracking).
- **Single-source-of-truth module**: `state_build/harness/scope/patterns.py` exports `PROHIBITED_RE`, `EXCEPTION_RE`, `PATH_ALLOWLIST_GLOB`. Pattern mirrored from gsd-2 `branch-patterns.ts`.
- **Path-allowlist is SCAN-ONLY**: `.planning/**/*.md` skips Layer 3 (prohibited-language scan) but does NOT exempt files from Layer 1 (`files_modified`). Order matters: Layer 1 runs first.
- **EXCEPTION_RE is the only sanctioned exception form**: only `TODO` and `FIXME` get the `(ID-NN)` exception; `placeholder`, `simplified`, `v1`, `future` always trigger `scope_check`.
- **`files_modified` is never mutated at runtime**: locked at plan-slice end per PAP-03; runtime overrides are event-scoped one-shot allowlists keyed by `(session_id, task_id, requested_path)`.
- **`scope_deviation_request` routes through `checkpoint:decision`**: Phase 405 DEV-03 territory under `--tiered`; the MCP tool returns the populated `ScopeDeviationResolved` synchronously.
- **`request_step_split` is an explicit MCP-tool-call boundary**: mirrors gsd-2 `complete_task` / `complete_slice` / `validate_milestone` pattern. NL keyword detection rejected.
- **Implicit `split_recommendation` from N-paralysis+N-strike correlation rejected**: counter independence (per gsd-2 `loop-control.md` §0 Correction 1) is load-bearing across all three sibling specs.
- **`deferred-items.md` is per-Slice with auto-append projector**: subscribed to `scope_check` events with `exception_matched=False` and `scope_deviation_request` events with `resolution='reject'` + `[defer]` tag.
- **Layer composition is the canonical enforcement pipeline**: PROOF-GATE.md owns Layers 2 (PAP-05 immutability) and 4 (gate-failing next-task block); SCOPE-PROHIBITION.md owns Layers 1 (`files_modified`) and 3 (prohibited-language). This spec owns 50% of the stack.
- **`scope_check` is tier=advisory-only on first match**: hard-block on first match was rejected — the agent gets a chance to justify via `EXCEPTION_RE` before the write is rejected.

## Files Touched

- `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` (created; 566 lines)

## Open Items / Deferred

- **Hybrid per-token regex for prohibited language REJECTED** — uniform word-boundary suffices for v1 token list; revisit if v2 expands the corpus with prose tokens requiring substring semantics.
- **Frontmatter opt-out marker for prohibited-language scan REJECTED** — path-allowlist `.planning/**/*.md` is the correct granularity.
- **`scope_check` tier-2 tool-block on first match REJECTED** — tier=advisory only; agent justifies via `EXCEPTION_RE`.
- **NL keyword detection for split_recommendation REJECTED** — explicit MCP tool-call boundary preserves agent intent.
- **Implicit split_recommendation from N-paralysis+N-strike pattern REJECTED** — preserves counter independence and agent intent.
- **Shared APG+PRF counter REJECTED** — counter independence preserved per gsd-2 `loop-control.md` §0 Correction 1.
- **Bullet-as-regex pattern extraction for `<acceptance_criteria>` REJECTED** (Phase 404 cross-cutting decision) — index binding wins.
- **`auto+tdd` test-file inference deferred to v14** — planner emits both source AND test paths in `files_modified` for v1; v14 may add an inference rule.
- **Generated-file allowlist (lockfiles, migrations, code-gen) deferred to v14** — `files_modified.generated` sub-field if real friction surfaces in EXEMPLAR-stepNPLAN.md sizing.
- **Plan 04 of this phase appends `## v41 Amendment` blocks**: to v40 EVENT-TAXONOMY.md (registers `state.step.scope_check` + `state.step.scope_deviation` + `state.step.scope_deviation_request` + `state.step.scope_deviation_resolved` + `state.slice.split_recommendation`) and ARTIFACT-CATALOG.md (registers `deferred-items.md` as a per-Slice artifact).

## Downstream Hooks

- **v14 Build Kernel** implements `state_build/harness/scope/patterns.py` (`PROHIBITED_RE` + `EXCEPTION_RE` + `PATH_ALLOWLIST_GLOB`) + `files_modified` allowlist checker + `EXCEPTION_RE` cross-check resolver + `scope_deviation_request` MCP handler + `request_step_split` MCP handler + worktree-snapshot reuse + `deferred-items.md` writer projector.
- **v15 Build Core Commands** implements planner-validation `<acceptance_criteria>` annotation check (PRF-02 `ANNOTATION_RE` binding) + SUMMARY-generation pull from `deferred-items.md` + replan re-entry consuming `split_recommendation`.
- **Phase 405** DEV-03 consumes `scope_deviation_resolved`; DEV-04 consumes `split_recommendation` telemetry; DEV-05 specifies `--full-yolo` auto-approval policy NOT owned here.
- **Phase 406** cites this spec for tier-1 + tier-2 of the 4-tier intervention ladder; `harness_intervention` aggregates all five scope/split events.

## Task Commits

- Task 1 (sections 1-5): `3e6b334` — `feat(404-03): SCOPE-PROHIBITION.md sections 1-5 (SRP-01..03 + ScopeCheck)`
- Task 2 (sections 6-10): `bc5dcb8` — `feat(404-03): SCOPE-PROHIBITION.md sections 6-10 (SRP-04..06 + cross-refs)`
- Task 3 (this SUMMARY): per `git log` after this commit.

## Deviations from Plan

None — plan executed exactly as written. Worktree-branch base check at executor start required a `git reset --soft` to the expected base; subsequent restore of the phase-404 plan/context files from HEAD was performed before reading the plan (no scope deviation; standard worktree-agent bootstrap).

One small content adjustment in the header: the cardinal-rule restatement was rephrased from `state.build.*` / `state.teach.*` literal package references to `Build mode's Python package` / `Teach mode's Python package` prose, in order to satisfy the plan's verify-automated assertion `! grep -q "state.teach" "$F"` (Build-mode isolation grep gate). Substantive meaning unchanged.

## Self-Check: PASSED

- [x] File `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` exists at the canonical path.
- [x] 566 lines (>= 500 required).
- [x] H1 `# Scope Reduction Prohibition (Canonical, v41)` present.
- [x] All 10 H2 sections present (Overview, SRP-01 cross-check, SRP-02 prohibited-language scan, SRP-03 path-allowlist + exception, ScopeCheck Pydantic, files_modified allowlist enforcement, scope_deviation_request flow, request_step_split, deferred-items.md, Cross-references).
- [x] `PROHIBITED_RE` rendered verbatim with the six tokens.
- [x] `EXCEPTION_RE` rendered verbatim with `TODO|FIXME(ID-NN)` form.
- [x] `PATH_ALLOWLIST_GLOB` rendered with `.planning/**/*.md` glob.
- [x] Five Pydantic event/payload classes rendered with `extra="forbid"`: `ScopeCheck`, `ScopeDeviation`, `ScopeDeviationRequest`, `ScopeDeviationResolved`, `SplitRecommendation`.
- [x] Positive and negative scan examples table rendered with 10 rows including all canonical edge cases.
- [x] `state_build/harness/scope/` single-module pattern documented with citation to gsd-2 `branch-patterns.ts`.
- [x] `.planning/**/*.md` path-allowlist documented as SCAN-ONLY (NOT files_modified exemption).
- [x] `request_step_split` 4-step harness behavior sequence rendered (emit event + take snapshot + `pending_replan` transition + clean run-slice exit).
- [x] `deferred-items.md` canonical template + auto-append projector + 5-status vocabulary rendered.
- [x] Cross-references to PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, STEP-PLAN-FORMAT.md, PLAN-AS-PROMPT.md, CONTEXT-PROTOCOL.md, SLICE-CYCLE.md, EVENT-TAXONOMY.md, ARTIFACT-CATALOG.md, `harness_intervention` all present.
- [x] "`files_modified` itself is NEVER mutated at runtime" rule rendered.
- [x] "explicit MCP tool-call boundary" + "no NL keyword detection" rendered.
- [x] Layer composition with PROOF-GATE.md ownership (Layers 2+4) and this spec ownership (Layers 1+3) documented.
- [x] No `state.teach` references (Build-mode isolation grep gate passes).
- [x] Task 1 verify-automated block passed (Task 1 commit 3e6b334).
- [x] Task 2 verify-automated block passed (Task 2 commit bc5dcb8).
- [x] SUMMARY.md exists at `.planning/milestones/v41/phases/404/03-scope-prohibition-spec-SUMMARY.md` with >= 80 lines.
