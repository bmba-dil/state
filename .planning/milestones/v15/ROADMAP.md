# v15 — Build Core Commands (plan/execute/verify/ship)

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 135–144 (10 phases)

---

## Phases

#### Phase 135 — `/state:build:discuss <step>` command (multi-turn clarification)
**Goal:** Task-based subagent; writes DISCUSS.md on completion; state → DISCUSSING.
**Depends on:** 125, 109
**Requirements:** CMD-01
**Parallelizable:** yes

#### Phase 136 — `/state:build:plan <step>` command (task decomposition, test plan, risks)
**Goal:** Emits PLAN.md with structured sections.
**Depends on:** 135
**Requirements:** CMD-02
**Parallelizable:** yes with P4

#### Phase 137 — Plan-checker agent (validates PLAN will achieve goal)
**Goal:** Before `execute`, plan-checker reviews PLAN.md against STEP.md goal; blocks on red.
**Depends on:** 136
**Requirements:** CMD-07
**Parallelizable:** no

#### Phase 138 — `/state:build:execute <step>` command (atomic commits)
**Goal:** Dispatches to worker; one commit per sub-task; EXECUTE.log.
**Depends on:** 137, 038
**Requirements:** CMD-03
**Parallelizable:** yes with P5

#### Phase 139 — `/state:build:verify <step>` command (runs verifier chain)
**Goal:** Invokes v14 verifier chain; writes VERIFY.md; advances or reverts Step.
**Depends on:** 127, 138
**Requirements:** CMD-04
**Parallelizable:** no

#### Phase 140 — `/state:build:ship <slice>` command (PR + code review + finalize)
**Goal:** Opens PR via `gh`; triggers code-review; on green, finalizes Slice; Slice snapshot.
**Depends on:** 039, 139
**Requirements:** CMD-05
**Parallelizable:** yes

#### Phase 141 — `/state:build:quick <description>` fast path
**Goal:** Skip Arc/Phase scaffolding; inline Slice+Step; execute end-to-end in one command.
**Depends on:** 138, 139
**Requirements:** CMD-06
**Parallelizable:** yes

#### Phase 142 — Gray-area decision routing (dialog vs DECISIONS.md)
**Goal:** Detect ambiguity in planner; surface via `ui.DialogSelect` (TUI) or append to DECISIONS.md (per config).
**Depends on:** 133
**Requirements:** CMD-08
**Parallelizable:** yes

#### Phase 143 — Revert-on-fail wiring (verify fail → snapshot revert)
**Goal:** On `state.step.verify_failed`, call `Snapshot.revert` to `pre_verify` hash.
**Depends on:** 139, 038
**Requirements:** CMD-04
**Parallelizable:** no

#### Phase 144 — End-to-end integration test (discuss → plan → execute → verify → ship)
**Goal:** 3-Step fixture Slice; exercises full happy path and revert path.
**Depends on:** 135..P9
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

