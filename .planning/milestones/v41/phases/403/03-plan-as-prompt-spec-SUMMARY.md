---
phase: 403-step-task-decomposition-plan-as-prompt
plan: 03
subsystem: design-spec
tags: [plan-injection, mutability, audit-log, pydantic, diff-the-proposed-write, path-confinement, at-reference, harness]

# Dependency graph
requires:
  - phase: 403-01
    provides: EXEMPLAR-stepNPLAN.md (canonical worked example cited for injection demonstrations + path-confinement example)
  - phase: 402
    provides: "CONTEXT-PROTOCOL.md (reinject payload XML shape: <active_plan>, <upstream_provides>, <current_task_pointer>); tool.execute.before canonical block hook; chat.params injection vector; plugin-as-thin-reporter pattern"
  - phase: 400
    provides: EVENT-TAXONOMY.md (append-only event row convention; state.{tier}.{action} naming); FRONTMATTER-SCHEMAS.md (Pydantic extra=forbid convention)

provides:
  - PLAN-AS-PROMPT.md — canonical plan-as-prompt injection + mutability + audit-log spec covering PAP-01..PAP-06
  - 6-step Injection Flow (PAP-01): read → strip → @-resolve → augment → inject via chat.params
  - Runtime augmentation block XML shape with all 4 slots (worktree_path, prior_task_results, upstream_provides, current_task_pointer)
  - @-reference resolution rule (PAP-02): one-level inline, 30_000 token cap, path confinement (realpath-based, fail-closed), cache by (snapshot_event_id, ref_path)
  - Mutability Matrix (PAP-03): 22-row table locking all frontmatter + most body sections; Mutable: <context>, <read_first>, <action>, <discovered_threats> (append-only)
  - PlanEdit Pydantic class (PAP-04): step_id, slice_id, diff, before_sha256, after_sha256, editor (Literal), edited_at, session_id, immutable_section_touched
  - PlanEditBlocked Pydantic class (PAP-05): step_id, slice_id, proposed_diff, locked_section, blocked_at, session_id, proposed_by (Literal)
  - Diff-the-proposed-write algorithm (PAP-05): 7-step protocol via tool.execute.before
  - discovered_threats append-only diff shape: exact ACCEPTED/REJECTED diff examples
  - StepPlanAuthored Pydantic class (PAP-06): step_id, slice_id, original_content, original_sha256, authored_at, authored_by (Literal), session_id
  - Content stripping rules: plan-slice reasoning meta + already-completed upstream interfaces excerpts (replaced with pointer form)
  - Replay reconstruction algorithm: walk diff chain from plan_authored event with SHA-256 verification at each step
  - Token budget accounting: budget_used = stripped plan + inlined @-refs + runtime_augmentation; cap against CTX-01 200k absolute
  - @-reference pseudocode: resolve_at_ref() + inline_at_refs() with confinement check
  - REQUIREMENTS amendments survey: 5-row table concluding no standalone amendment plan needed

affects:
  - 403-04 (STEP-EVENTS.md — Plan 04 owns the full 9-event state.step.* family; this spec embeds 3 inline)
  - 404 (Boolean Proof Gate — consumes immutability lock for <verify> blocks from Mutability Matrix)
  - 405 (Deviation Rules & Subagent Management — consumes autonomy-tier checkpoint behavior from STEP-PLAN-FORMAT.md cross-reference)
  - 406 (Harness Architecture Rollup — cross-references the injection flow and security threat mitigations)
  - v14 Build Kernel — implements: @-reference resolver, diff-the-proposed-write enforcer, chat.params injection trampoline, runtime-augmentation slot assembly, projector replay-verifier

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic models with extra=\"forbid\" for plan-edit event schemas (PlanEdit, PlanEditBlocked, StepPlanAuthored)"
    - "Diff-the-proposed-write: pure-machine immutability enforcement via tool.execute.before + AST diff of locked sections"
    - "Path-confinement via pathlib.Path.resolve() + ancestor check (fail-closed on traversal)"
    - "Replay reconstruction via diff-chain from plan_authored original (before_sha256/after_sha256 at each step)"
    - "Token budget computed at injection time: stripped plan + @-refs (30k cap) + runtime_augmentation, bounded by CTX-01 200k absolute"

key-files:
  created:
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (524 lines, canonical spec covering PAP-01..PAP-06)
  modified: []

key-decisions:
  - "Path confinement stipulated explicitly with positive/negative example pairs (security mitigation for @-reference path traversal threat)"
  - "Token cap pinned to 30_000 tokens for all @-inlined refs combined; v14 may tune to 20k or 40k after EXEMPLAR sizing measurements"
  - "Mutability matrix STRENGTHENS PAP-03 original wording (only must_haves + <verify> required immutable) by locking ALL frontmatter fields + most body sections; rationale: Step-identity-fields"
  - "PlanEdit replay-time SHA-256 integrity check makes diff-payload tampering pure-machine detectable (before_sha256/after_sha256 required)"
  - "<discovered_threats> append-only carve-out shipped with EXACT diff shape definition + 3 worked diff examples (1 ACCEPTED, 2 REJECTED)"
  - "REQUIREMENTS amendments survey concluded: NO standalone amendment plan needed for Phase 403; all decisions satisfy v1 REQ wording or are absorbed inline"
  - "orjson flag pin: OPT_NAIVE_UTC selected (first option, CONTEXT-PROTOCOL.md canonical pin) — auto-selected at checkpoint:decision Task 3"

metrics:
  completed: "2026-05-11"
  duration: "~1h (design-only, no code)"
  tasks: 3
  files: 1

---

# Plan 403-03 Summary: PLAN-AS-PROMPT.md

**Status:** Shipped
**Wave:** 2
**Depends on:** 01 (EXEMPLAR-stepNPLAN.md)
**Blocks:** 04 (STEP-EVENTS.md)

## What Was Built

`PLAN-AS-PROMPT.md` at `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` (524 lines, ≥500 requirement met). The spec covers PAP-01..PAP-06 in full: a 6-step injection flow (chat.params hook → read → strip → @-resolve → augment → inject), the runtime augmentation block XML shape, the @-reference resolution rule with 30_000-token cap and realpath-based path confinement (fail-closed), the comprehensive Mutability Matrix (22 rows), and three Pydantic event classes (PlanEdit, PlanEditBlocked, StepPlanAuthored) — all with `extra="forbid"` and complete field sets. The spec ships the diff-the-proposed-write algorithm (7-step numbered protocol), the `<discovered_threats>` append-only diff shape with exact ACCEPTED and REJECTED diff examples, the no-direct-write contract, a replay reconstruction algorithm with SHA-256 verification, and a REQUIREMENTS amendments survey concluding no standalone amendment plan is needed for Phase 403.

## Key Decisions

- **Path confinement for @-references stipulated explicitly with positive/negative example pairs.** Mitigation for path traversal threat per the plan's `<security_threat_model_gate>`. `realpath()`-based check with fail-closed semantics: injection aborted on violation, `state.step.plan_edit_blocked` emitted with `locked_section="@-reference-confinement"`.
- **Token cap pinned to 30_000 tokens for all inlined refs combined.** v14 may tune to 20k or 40k after EXEMPLAR-stepNPLAN.md realistic measurements per 403-CONTEXT.md Claude's Discretion.
- **Mutability matrix STRENGTHENS PAP-03's original wording.** PAP-03 required only `must_haves.*` and `<verify>` blocks to be immutable. This spec locks ALL frontmatter fields + most body sections. Rationale documented as Step-identity-fields: changing a locked field means it's a different Step, requiring replan not in-place mutation.
- **PlanEdit replay-time SHA-256 integrity check.** `before_sha256` + `after_sha256` verified at replay against on-disk content. Hash mismatch → projector rejects event, daemon surfaces as startup error. Makes diff-payload tampering pure-machine detectable.
- **`<discovered_threats>` append-only carve-out shipped with EXACT diff shape.** Three worked diff examples included (1 ACCEPTED: new threat appended; 2 REJECTED: existing threat text edited; existing threat removed). No diff-shape ambiguity.
- **REQUIREMENTS amendments survey concluded: no standalone amendment plan needed.** 5-row survey table: discovered_threats carve-out (additive sub-tag, no REQ scope extension), options sub-tag (STP-04 non-exhaustive), mutability strengthening (absorbed inline), path-confinement (security supplement), auto+tdd trailer (STP-05 implementation detail).
- **orjson serialization flag: OPT_NAIVE_UTC selected.** Auto-selected at `checkpoint:decision` Task 3 (YOLO mode, first option = CONTEXT-PROTOCOL.md canonical pin). No source file change required — Task 2 already committed OPT_NAIVE_UTC as the default in the orjson call site.

## Files Touched

- `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` — created (524 lines)

## Open Items / Deferred

- Conditional stripping via per-section `inject:` frontmatter flag deferred to v14 (per 403-CONTEXT.md `<deferred>`). Default stripping rules ship now.
- Recursive @-reference expansion deferred — one-level only enforced now. Planners encouraged to inline-expand at planning time.
- Advisory wording on `plan_edit_blocked` is recommended wording in this spec; v14 may tune.
- Filesystem watcher as defense-in-depth for no-direct-write contract noted as v14 MAY; the contract is the hook routing.

## Downstream Hooks

- **v14 Build Kernel implements:** @-reference resolver (`resolve_at_ref()` + `inline_at_refs()` pseudocode in Section 4), diff-the-proposed-write enforcer (Section 7, 7-step algorithm), chat.params injection trampoline (Section 2), runtime-augmentation slot assembly (Section 3), projector replay-verifier (Section 6, SHA-256 chain).
- **STEP-EVENTS.md (Plan 04 / Phase 403)** defines the full Pydantic schemas for the `state.step.*` event family. This spec embeds 3 inline (PlanEdit, PlanEditBlocked, StepPlanAuthored); Plan 04 ships the remaining checkpoint + replan events.
- **Phase 404 (Boolean Proof Gate)** consumes the immutability lock for `<verify>` blocks (Mutability Matrix row: `<verify>` → Locked).
- **Phase 405 (Deviation Rules & Subagent Management)** consumes the autonomy-tier task-type behavior for `checkpoint:*` tasks, cross-referenced in STEP-PLAN-FORMAT.md Section 5.
- **Phase 406 (Harness Architecture Rollup)** cross-references the 6-step injection flow and the security threat mitigations in the layered harness diagram.
