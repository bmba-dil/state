---
phase: 403
status: major_issues
findings_critical: 0
findings_major: 2
findings_minor: 4
created: 2026-05-10
---

# Phase 403 Code Review

**Reviewed:** 2026-05-10
**Depth:** standard (spec-document consistency review)
**Files Reviewed:** 5
**Status:** major_issues

---

## Files Reviewed

- `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`
- `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md`
- `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md`
- `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (amendment block, lines 239–282)

---

## Summary

The four spec documents are internally coherent at the macro-structure level: section ordering, mutability matrix rows, STP/PAP requirement coverage, and replan-continuity event semantics all hang together well. The EVENT-TAXONOMY.md amendment block is correctly additive and follows Phase 402 convention.

Two major issues surface on close reading. First, the `EventEnvelope` schema cited in STEP-EVENTS.md as the "v40 convention" carries different field names than the one pasted verbatim from `src/state_core/schema.py` in the EXEMPLAR's `<interfaces>` block — a v14 implementer faces two conflicting schemas for the same class. Second, the `PlanEdit` Pydantic model retains an `immutable_section_touched: bool` field that PLAN-AS-PROMPT.md explicitly states can never be `True` on an emitted event (blocked writes produce `plan_edit_blocked`, not `plan_edit`), making the field a dead branch that signals a split-design leftover.

Four minor issues follow: an event name discrepancy in the PLAN-AS-PROMPT summary table, a missing Pydantic alias on `KeyLink.from_`, a `must_haves.truths` field name that diverges from the actual model, and a missing `ge=0` constraint on `StepFrontmatter.wave`.

---

## CRITICAL

None.

---

## MAJOR

### [MAJOR] `EventEnvelope` schema in STEP-EVENTS.md diverges from the authoritative `src/state_core/schema.py` excerpt in EXEMPLAR

**File:** `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`:51–58 vs `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:86–95

**Issue:** STEP-EVENTS.md presents the following as the "v40 convention" `EventEnvelope`:

```python
class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    event_type: str
    aggregate_id: str
    emitted_at: str
    payload: dict
```

The EXEMPLAR's `<interfaces>` block pastes the literal content of `src/state_core/schema.py` lines 239–265, showing a materially different shape:

```python
class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = ""
    seq: int = 0
    aggregate_type: str = "arc"
    aggregate_id: str = ""
    type: str = ""
    data: dict[str, Any] = {}
```

The field names differ on every key except `aggregate_id`: `id` vs `event_id`, `type` vs `event_type`, `data` vs `payload`; the schema.py version carries `seq` and `aggregate_type` which the STEP-EVENTS.md version omits entirely; `emitted_at` is present in STEP-EVENTS.md but absent from schema.py. The EXEMPLAR's excerpt is labelled "LITERAL upstream content" per STP-07, meaning it is the authoritative excerpt of existing code. STEP-EVENTS.md cross-references the same v40 EVENT-TAXONOMY.md as the canonical source. A v14 implementer reading both documents faces two incompatible envelope contracts.

**Suggestion:** Determine which shape is canonical for v14. If STEP-EVENTS.md is specifying a NEW envelope shape (v41 redesign), the spec must explicitly call out the migration: add a note to STEP-EVENTS.md's `EventEnvelope reference` section stating "this is a v41 redesign of the envelope; the existing `schema.py` shape is the v40 baseline, to be migrated in v14." Correspondingly, either update the EXEMPLAR's `<interfaces>` excerpt to show the v41 shape (if that is now authoritative) or add a note that the EXEMPLAR reflects the v40 schema.py baseline. Do not leave both shapes in the spec suite with no bridge.

---

### [MAJOR] `PlanEdit.immutable_section_touched` is a dead-branch field contradicted by PLAN-AS-PROMPT.md

**File:** `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`:109 and `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md`:405–406

**Issue:** The `PlanEdit` Pydantic schema includes `immutable_section_touched: bool` with the inline note "True triggers `plan_edit_blocked` instead". However, PLAN-AS-PROMPT.md §7 (plan_edit_blocked + Diff-the-Proposed-Write Enforcer) states unambiguously:

> "When `tool.execute.before` detects a locked-section diff, it emits ONLY `state.step.plan_edit_blocked` — NOT `state.step.plan_edit`."

If `immutable_section_touched=True` causes the enforcer to emit `plan_edit_blocked` instead of `plan_edit`, then a `PlanEdit` event with `immutable_section_touched=True` is never emitted. The field is unreachable in normal operation. A v14 implementer who reads only STEP-EVENTS.md will model the emitter to set `immutable_section_touched=True` before switching events; a v14 implementer who reads only PLAN-AS-PROMPT.md will model two completely separate code paths with no shared field. The projector reducer and the emitter logic will disagree.

The field also appears identically in PLAN-AS-PROMPT.md's inline `PlanEdit` schema (line 301), so the contradiction exists within PLAN-AS-PROMPT.md itself: the field says it triggers an alternative event, while the prose says the alternative event is emitted instead.

**Suggestion:** Remove `immutable_section_touched` from `PlanEdit`. The invariant "a single proposed write produces EITHER `plan_edit` OR `plan_edit_blocked`, never both" (stated in the field-constraints table at STEP-EVENTS.md line 316) is self-documenting and sufficient. If the field is retained for tooling/debugging purposes, add a validation invariant: `immutable_section_touched` MUST always be `False` on any emitted `PlanEdit` event (since `True` means the event would have been `plan_edit_blocked`). Make this explicit in both STEP-EVENTS.md and PLAN-AS-PROMPT.md.

---

## MINOR

### [MINOR] PLAN-AS-PROMPT event summary table uses `checkpoint_resolved` instead of `checkpoint_auto_resolved`

**File:** `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md`:280

**Issue:** The event summary table in §PAP-04 lists `state.step.checkpoint_resolved` as the event name for checkpoint resolution. The canonical event home (STEP-EVENTS.md) defines `state.step.checkpoint_auto_resolved`. The STEP-PLAN-FORMAT.md §5 (checkpoint:human-verify behavior) also uses `state.step.checkpoint_auto_resolved`. The PLAN-AS-PROMPT table is the odd one out.

**Suggestion:** Change line 280 of PLAN-AS-PROMPT.md from `` `state.step.checkpoint_resolved` `` to `` `state.step.checkpoint_auto_resolved` `` to match the canonical name in STEP-EVENTS.md.

---

### [MINOR] `KeyLink.from_` has no Pydantic alias declared; YAML round-trip will fail

**File:** `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md`:41–42

**Issue:** The `KeyLink` Pydantic model declares:

```python
class KeyLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_: str    # alias "from" — Python keyword collision
    to: str
    via: str
    pattern: str
```

The comment says `from_` is an alias for `from`, but no `Field(alias="from")` or `model_config = ConfigDict(extra="forbid", populate_by_name=True)` with alias is specified. The EXEMPLAR YAML uses `from:` (line 38, 42). When `StepFrontmatter.model_validate(yaml.safe_load(frontmatter))` runs against the EXEMPLAR YAML, Pydantic will look for the field name `from_` in the dict, not `from`. Since `from` is a Python reserved word, `yaml.safe_load` will produce `{'from': '...'}` and `model_validate` will raise `ValidationError` (unknown key `from` with `extra="forbid"`, missing required field `from_`).

**Suggestion:** Add a Pydantic field alias to the model definition:

```python
from pydantic import BaseModel, ConfigDict, Field

class KeyLink(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_: str = Field(alias="from")
    to: str
    via: str
    pattern: str
```

`populate_by_name=True` allows both `from_` (Python side) and `from` (YAML/JSON side) to work. This must be added to the spec schema before v14 implements the `StepPlan` validator.

---

### [MINOR] `must_haves.truths` and `success_criteria` name the field `upstream_provides` but the model uses `provides_blocks`

**File:** `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:29 and 317

**Issue:** `must_haves.truths` at line 29 states:

> "All seven snapshot fields from CONTEXT-PROTOCOL.md are present (slice_id, step_id, task_id, session_id, active_plan_path, current_task_pointer, **upstream_provides**)."

The `success_criteria` at line 317 repeats: "All seven required fields from CONTEXT-PROTOCOL.md §5 (CTX-05) are present in the model: `slice_id`, `step_id`, `task_id`, `session_id`, `active_plan_path`, `current_task_pointer` (via `current_task_pointer`), and `upstream_provides` (via `provides_blocks`)."

The `CompactionSnapshot` schema in Excerpt B (lines 118–119) shows the field is `provides_blocks: list`, not `upstream_provides`. The EXEMPLAR's own `<interfaces>` block contradicts its `must_haves.truths`. The `success_criteria` partially recovers by noting "(via `provides_blocks`)" but the parenthetical is inverted — it should say "upstream_provides (not present; represented by `provides_blocks`)".

This creates a false truth assertion: if a validator runs `grep -q "upstream_provides" src/state_build/snapshot/compaction.py`, the file implementing the spec would correctly have `provides_blocks` and the grep would return non-zero (failing a truth that uses `upstream_provides` as the field name).

**Suggestion:** In `must_haves.truths` at line 29, replace `upstream_provides` with `provides_blocks`. In `success_criteria` at line 317, remove the parenthetical `(via `provides_blocks`)` and write `provides_blocks` directly as the seventh field name.

---

### [MINOR] `StepFrontmatter.wave` has no non-negative constraint in the Pydantic schema

**File:** `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md`:63

**Issue:** The `wave` field is documented as "non-negative; v5 scheduler input" in a comment, but the Pydantic declaration is `wave: int` with no constraint. A negative wave value (e.g., `wave: -1`) would pass `model_validate` without error. Planner validation is cited as the enforcement mechanism for field constraints, but this constraint is not present in the schema.

**Suggestion:** Use an annotated type to enforce the non-negative constraint at the Pydantic layer:

```python
from typing import Annotated
from pydantic import Field

class StepFrontmatter(BaseModel):
    ...
    wave: Annotated[int, Field(ge=0)]   # non-negative; v5 scheduler input
```

This makes the constraint machine-checkable at `model_validate` time rather than relying on a prose comment.

---

## STYLE

None.

---

*Reviewed: 2026-05-10*
*Reviewer: Claude (gsd-code-reviewer)*
*Depth: standard (spec-document consistency)*
