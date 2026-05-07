# Composite Event Cascade — Step→Slice→Stage→Arc

> **Design contract for v41+ projector composite event emission and cross-tier rollup.**
> Consumed by: Plan 400-03 (DESC-SEMANTICS.md). Phase 401 (REF-02 cross-tier references). v41+ projector/scheduler implementation.

## Overview

Composite events propagate upward through the four-tier hierarchy. When all children of a parent reach a terminal state, the projector emits a composite event on the parent aggregate. This cascading upward flow enables the scheduler to detect when higher-tier units are ready for advancement without polling.

**Per D-19:** Composite states are computed at query time from child states, NOT explicit machine states. The composite events documented here are **separate `append()` operations** to the event store — they are NOT nested transactions. Each composite event is its own immutable record, fully replayable, and the projector recomputes all STATE.md projections from the event stream on daemon startup.

---

## Step → Slice Cascade

**Trigger:** `state.step.verify_passed` — a Step reaches `done`.

**Check:** ALL child Steps of the parent Slice have status `done`.

**Action:** Emit `state.slice.steps_completed`.

**Composite transition:** Slice `in_progress` → `shipped` (if VERIFICATION.md also passes).

```
Step-1: verifying → done  ──┐
Step-2: verifying → done  ──┤  state.slice.steps_completed emitted
Step-3: verifying → done  ──┘  (all 3 Steps are done)
                                ↓
                        Slice: in_progress → shipped
                        (if VERIFICATION.md passes)
```

### Projector Pseudocode

```python
async def on_step_done(event: StepEvent):
    """Check if all Steps in the parent Slice are done."""
    slice_id = extract_slice_id(event.aggregate_id)
    steps = await store.read_stream(f"{slice_id}/step-")
    
    all_done = all(
        projector.compute_step_state(step) == "done"
        for step in steps
    )
    
    if all_done:
        # Composite event — separate append, no nested transaction
        await store.append(
            aggregate_type="slice",
            aggregate_id=slice_id,
            event_type="state.slice.steps_completed",
            data={
                "last_step_id": event.aggregate_id,
                "step_count": len(steps),
            },
            mode="build",
        )
```

### Edge Case: Slice with 0 Steps

A Slice with zero Steps is treated as **soft-done** for cascade purposes. The Slice can transition directly to `shipped` without emitting `state.slice.steps_completed`. This handles empty container Slices (e.g., a Slice created as a placeholder that is later descoped entirely).

---

## Slice → Stage Cascade

**Trigger:** `state.slice.shipped` — a Slice reaches `shipped`.

**Check:** ALL child Slices of the parent Stage have status `shipped`.

**Action:** Emit `state.stage.slices_shipped`.

**Composite transition:** Stage `in_progress` → `verified`.

```
Slice-10: shipped  ──┐
Slice-11: shipped  ──┤  state.stage.slices_shipped emitted
Slice-12: shipped  ──┘  (all 3 Slices are shipped)
                        ↓
                Stage: in_progress → verified
                (manual verify-stage required for → shipped)
```

### Projector Pseudocode

```python
async def on_slice_shipped(event: SliceEvent):
    """Check if all Slices in the parent Stage are shipped."""
    stage_id = extract_stage_id(event.aggregate_id)
    slices = await store.read_stream(f"{stage_id}/slice-")
    
    all_shipped = all(
        projector.compute_slice_state(slice) == "shipped"
        for slice in slices
    )
    
    if all_shipped:
        # Composite event — separate append, no nested transaction
        await store.append(
            aggregate_type="stage",
            aggregate_id=stage_id,
            event_type="state.stage.slices_shipped",
            data={
                "shipped_slice_ids": [s.aggregate_id for s in slices],
            },
            mode="build",
        )
```

### Edge Case: Stage with 0 Slices

A Stage with zero Slices is treated as **soft-done** for cascade purposes. The Stage can transition directly to `verified` without the composite event. This handles Stages created as scoping placeholders that are later absorbed into sibling Stages.

---

## Stage → Arc Cascade

**Trigger:** `state.stage.completed` — a Stage reaches `shipped`.

**Check:** ALL child Stages of the parent Arc have status `shipped`.

**Action:** Emit `state.arc.stages_shipped`.

**Composite transition:** Arc `in_progress` → `auditing` (D-18 entry guard).

```
Stage-20: shipped  ──┐
Stage-21: shipped  ──┤  state.arc.stages_shipped emitted
Stage-22: shipped  ──┘  (all 3 Stages are shipped)
                        ↓
                Arc: in_progress → auditing
                (manual /state-ship-arc required for → shipped)
```

### Projector Pseudocode

```python
async def on_stage_completed(event: StageEvent):
    """Check if all Stages in the parent Arc are shipped."""
    arc_id = extract_arc_id(event.aggregate_id)
    stages = await store.read_stream(f"{arc_id}/stage-")
    
    all_shipped = all(
        projector.compute_stage_state(stage) == "shipped"
        for stage in stages
    )
    
    if all_shipped:
        # Composite event — separate append, no nested transaction
        await store.append(
            aggregate_type="arc",
            aggregate_id=arc_id,
            event_type="state.arc.stages_shipped",
            data={
                "shipped_stage_ids": [s.aggregate_id for s in stages],
            },
            mode="build",
        )
```

### Edge Case: Arc with 0 Stages

An Arc with zero Stages is treated as **soft-done** for cascade purposes. The Arc can go directly to `auditing` (D-18 guard: audit triggers on "all Stages shipped" — vacuously true with 0 Stages). This enables Arcs that define only the feature scope without immediate implementation.

---

## Cascade Chain Summary

```
Step: verify_passed (done)
  → check: all Steps in Slice are done
  → emit: state.slice.steps_completed
  → Slice: in_progress → shipped (if VERIFICATION.md passes)

Slice: shipped
  → check: all Slices in Stage are shipped
  → emit: state.stage.slices_shipped
  → Stage: in_progress → verified

Stage: completed (shipped)
  → check: all Stages in Arc are shipped
  → emit: state.arc.stages_shipped
  → Arc: in_progress → auditing

Arc: shipped (manual /state-ship-arc)
  → terminal state — no further cascade (root tier)
```

### Key Properties

1. **Separate append() per composite event** — no nested transactions. Each composite event is an independent, replayable record in the event stream.
2. **Projector-driven** — composite checks run in the projector, not in the scheduler. The projector is the single source of truth for all state computations.
3. **Deterministic** — composite state is computed from the immutable event stream. Replay on daemon startup produces identical STATE.md projections.
4. **"Last child" optimization** — the composite check only fires when the last child transitions to the terminal state. Intermediate child transitions do not trigger the check.
5. **Edge cases handled** — Empty child sets (0 children) are treated as soft-done for cascade purposes, allowing parent tiers to advance.

---

## Composite State Computation (D-19)

Composite states are projector-computed at query time from child states. They are NOT explicit machine states — they do not appear in the FSM transition tables. The following rules define how the projector computes composite states for each tier.

### Stage Composite States

| Composite State | Computation Rule | Threshold |
|----------------|------------------|-----------|
| "in_progress" | Any child Slice has status ∈ {`worktree_ready`, `in_progress`} | ANY active |
| "verified" | ALL child Slices are `shipped` AND Stage passed verification | ALL shipped |

**Rule:** `in_progress` uses ANY active child (a single active Slice keeps the Stage "in progress"). Terminal states (`verified`, `shipped`) use ALL children.

### Arc Composite States

| Composite State | Computation Rule | Threshold |
|----------------|------------------|-----------|
| "in_progress" | Any child Stage has status ∈ {`in_progress`, `verified`} | ANY active |
| "auditing" | ALL child Stages are `shipped` (D-18 guard) | ALL shipped |
| "shipped" | ALL child Stages are `shipped` AND Arc itself is `shipped` | ALL shipped |

**Rule:** Same as Stage — "in progress" uses ANY active child, terminal states use ALL children.

### Slice Composite States

| Composite State | Computation Rule | Threshold |
|----------------|------------------|-----------|
| "in_progress" | Any child Step has status ∈ {`designing`, `planning`, `running`, `verifying`} | ANY active |
| "shipped" | ALL child Steps are `done` AND VERIFICATION.md passes | ALL done + verified |

**Rule:** Same pattern — ANY active keeps the Slice "in progress"; ALL done + verified transitions to "shipped".

### "Any" vs "All" Thresholds

| Tier | "In Progress" Threshold | Terminal Threshold |
|------|------------------------|-------------------|
| Arc | ANY Stage active | ALL Stages `shipped` + Arc shipped |
| Stage | ANY Slice active | ALL Slices `shipped` + Stage verified |
| Slice | ANY Step active | ALL Steps `done` + VERIFICATION passes |

**Rationale:** The "any" threshold for `in_progress` prevents premature advancement — a parent should not be considered "done" while any child is still active. The "all" threshold for terminal states ensures completeness — every child must finish before the parent can advance.

---

## Projector Startup Rebuild

On daemon startup, the projector replays the full event stream and rebuilds all STATE.md projections. Composite events are re-emitted during replay to maintain the cascade chain. The rebuild process:

```python
async def rebuild_all_projections():
    """Rebuild all STATE.md projections from event stream on startup."""
    events = await store.read_all_events(mode="build")
    
    for event in events:
        # Route to per-aggregate handler
        if event.aggregate_type == "step":
            await handle_step_event(event)
            # Composite check: all Steps done in parent Slice?
            await check_step_composite(event)
        elif event.aggregate_type == "slice":
            await handle_slice_event(event)
            # Composite check: all Slices shipped in parent Stage?
            await check_slice_composite(event)
        elif event.aggregate_type == "stage":
            await handle_stage_event(event)
            # Composite check: all Stages shipped in parent Arc?
            await check_stage_composite(event)
        elif event.aggregate_type == "arc":
            await handle_arc_event(event)
    
    # Write final STATE.md files for all aggregates
    await write_all_state_projections()
```

The rebuild is deterministic because:
- All events are immutable and ordered by `sequence_number`
- Composite events are re-emitted in the same order
- No external state influences the computation

---

## Edge Cases Reference

| Edge Case | Behavior | Rationale |
|-----------|----------|-----------|
| Slice has 0 Steps | Treated as soft-done; Slice can ship without `steps_completed` | Empty container Slices (descoped/placeholder) should not block parent advancement |
| Stage has 0 Slices | Treated as soft-done; Stage can verify without `slices_shipped` | Empty scoping Stages should not block Arc advancement |
| Arc has 0 Stages | Treated as soft-done; Arc can audit directly | Empty scoping Arcs should not block pipeline |
| Step `abandoned` (not `done`) | NOT counted as "done" for composite check | Abandoned Steps are terminal exits, not completions — parent Slice cannot ship while any Step is abandoned |
| Slice `blocked` (not `shipped`) | NOT counted as "shipped" for composite check | Blocked Slices are not complete — parent Stage cannot verify while any Slice is blocked |
| Slice `reverted` → `planned` | Reverted Slices re-enter the pipeline; composite check restarts | Revert resets progress — parent Stage returns to "in_progress" state |
| Slice `deferred` | Dependents treat as soft-done with `deferred_dep` flag (D-14) | Deferred Slices unblock dependents but are not "shipped" for parent Stage advancement |
| Concurrent last-child events | Store `append()` is serialized by aggregate ID lock | Event store guarantees at-most-once per aggregate — no double-emit of composite events |

---

*Design contract for v41+ projector composite event emission. All cascade logic validated against FSM-TABLES.md transition tables and EVENT-TAXONOMY.md event definitions. D-19 composite state computation rules are projector-enforced, not FSM-enforced.*
