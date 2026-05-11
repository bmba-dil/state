---
phase: 403
status: all_fixed
findings_in_scope: 2
fixed: 2
skipped: 0
iteration: 1
created: 2026-05-10
---

# Phase 403: Code Review Fix Report

**Fixed at:** 2026-05-10
**Source review:** `.planning/milestones/v41/phases/403/403-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (MAJOR): 2
- Fixed: 2
- Skipped: 0
- Optional MINOR also fixed: 2 of 4 (M1 and M3; M2 and M4 out of default scope)

---

## Fixed Issues

### MAJOR-1: EventEnvelope schema fork

**Files modified:** `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`
**Commit:** `12f4ca9`
**Applied fix:** Added a blockquote "Schema authority note" immediately before the logical EventEnvelope code block in the `§Conventions/EventEnvelope reference` section. The note explicitly states:
1. The **runtime shape** (authoritative for v14 implementation) is in `src/state_core/schema.py` lines 239-265, pasted verbatim in EXEMPLAR-stepNPLAN.md `<interfaces>` Excerpt A — fields: `id`, `seq`, `aggregate_type`, `aggregate_id`, `type`, `data`.
2. The **logical/conceptual shape** shown in this section uses descriptive field names for spec-doc readability only, with a per-field mapping comment (`id` → `event_id`, `type` → `event_type`, `data` → `payload`).
3. v14 implementers MUST use the runtime shape; `src/state_core/schema.py` wins on any divergence.

Also updated the conventions bullet that referenced the old conceptual field names to point to the §EventEnvelope reference section for the logical↔runtime mapping.

The EXEMPLAR's `<interfaces>` Excerpt A is deliberately left unchanged — it IS the authoritative literal excerpt of `schema.py` and must not be modified.

---

### MAJOR-2: PlanEdit.immutable_section_touched dead-branch field

**Files modified:** `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`, `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md`
**Commit:** `801c46c`
**Applied fix:**

In **STEP-EVENTS.md:**
- Removed `immutable_section_touched: bool` from the `PlanEdit` Pydantic class definition.
- Removed the `immutable_section_touched` row from the PlanEdit field constraints table.
- Replaced the removed field constraint with an explicit **Mutual-exclusion invariant** prose note: "A single proposed write produces EITHER a `plan_edit` event OR a `plan_edit_blocked` event, never both. The `tool.execute.before` enforcer determines which path is taken before any event is emitted; `plan_edit` is only emitted for writes that pass the mutability check."

In **PLAN-AS-PROMPT.md:**
- Removed `immutable_section_touched: bool` from the inline `PlanEdit` Pydantic class definition.
- Replaced with a comment block explaining the invariant: "immutable_section_touched is NOT a field on PlanEdit. A write that touches a locked section emits plan_edit_blocked INSTEAD of plan_edit. A single proposed write produces EITHER plan_edit OR plan_edit_blocked, never both."

---

## Optional MINOR Issues Fixed (out of default scope, applied as cheap fixes)

### MINOR-1: checkpoint_resolved → checkpoint_auto_resolved typo in PLAN-AS-PROMPT.md

**Files modified:** `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md`
**Commit:** `bd15082`
**Applied fix:** Changed the event summary table in §PAP-04 from `state.step.checkpoint_resolved` to `state.step.checkpoint_auto_resolved`, matching the canonical name defined in STEP-EVENTS.md and STEP-PLAN-FORMAT.md §5. Also updated the description text from "When a checkpoint task is resolved (auto or human)" to "When a checkpoint task is auto-resolved by the harness (tiered or full-yolo)" for precision — the human-action path is a separate pair of events.

### MINOR-3: upstream_provides → provides_blocks field name inconsistency

**Files modified:** `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`, `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md`
**Commit:** `cb53a85`
**Applied fix:**
- In EXEMPLAR `must_haves.truths` (line 29): replaced `upstream_provides` with `provides_blocks` to match the actual `CompactionSnapshot` field name from CONTEXT-PROTOCOL.md §5.
- In EXEMPLAR `<success_criteria>` (line 317): replaced the convoluted `upstream_provides (via provides_blocks)` phrasing with a clean `provides_blocks` direct reference and removed the inverted parenthetical.
- In EXEMPLAR `<threat_model>` DoS threat label (line 282): replaced `oversized upstream_provides dict` with `oversized provides_blocks list` for consistency.
- In STEP-PLAN-FORMAT.md literal EXEMPLAR excerpt (line 118): updated the copied `must_haves.truths` truth to match the now-corrected EXEMPLAR source.

---

## Skipped Issues

None — all in-scope findings were fixed. MINOR-2 (KeyLink.from_ alias) and MINOR-4 (StepFrontmatter.wave ge=0) were not in scope and were not applied.

---

_Fixed: 2026-05-10_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
