# v14 — Build Kernel: Step FSM + Verifiers

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 124–134 (11 phases)

---

## Phases

#### Phase 124 — STEP.md frontmatter schema + pydantic validator
**Goal:** `goal`, `verify_contract`, `depends_on[]`, `model_profile`, `snapshots[]`, `cost_cap`; `extra = "forbid"`.
**Depends on:** 002
**Requirements:** BLD-02
**Parallelizable:** yes

#### Phase 125 — Step state machine (StepMachine)
**Goal:** Per ARCHITECTURE §8.1 pseudocode; on_event handler; event-driven transitions.
**Depends on:** 124, 047
**Requirements:** BLD-01
**Parallelizable:** yes with P3

#### Phase 126 — Product Slice/Phase/Arc scoping containers (simpler FSMs)
**Goal:** `planned → in_progress → shipped | abandoned`.
**Depends on:** 124
**Requirements:** BLD-01
**Parallelizable:** yes with P2

#### Phase 127 — Goal-backward verifier (reads STEP.md goal → walks diff → asserts)
**Goal:** Verify contract runner: `tests`, `lsp`, `script` types; writes VERIFY.md pass/fail + evidence.
**Depends on:** 124, 125
**Requirements:** BLD-03, BLD-09
**Parallelizable:** yes with P5..P9

#### Phase 128 — Slice rollup verifier
**Goal:** Aggregate Step verify results; fail Slice if any Step failed.
**Depends on:** 127
**Requirements:** BLD-04
**Parallelizable:** yes with P6..P9

#### Phase 129 — Phase rollup verifier + Phase-level integration tests
**Goal:** Aggregate Slice rollups plus Phase-level integration tests.
**Depends on:** 128
**Requirements:** BLD-05
**Parallelizable:** yes with P7..P9

#### Phase 130 — Product-Arc rollup verifier
**Goal:** Aggregate product-Phase rollups plus product-Arc acceptance criteria.
**Depends on:** 129
**Requirements:** BLD-06
**Parallelizable:** yes with P8, P9

#### Phase 131 — Cross-tier integration verifier (runs after Arc boundary)
**Goal:** Checks interactions between completed Arcs; rollback if regression.
**Depends on:** 130
**Requirements:** BLD-07
**Parallelizable:** yes with P9

#### Phase 132 — Security verifier (part 1 — input guards: SQLi, path traversal, secret leak, shell meta)
**Goal:** Per-Step; diff-based; uses regex + libs for known patterns.
**Depends on:** 127
**Requirements:** BLD-08, SEC-01, SEC-02, SEC-03
**Parallelizable:** yes with P5..P8

#### Phase 133 — Gray-area decision plumbing (detection + dialog routing)
**Goal:** Planner detects ambiguity; emits `state.decision.asked`; routes to dialog OR logs to DECISIONS.md per config.
**Depends on:** 125, 072
**Requirements:** CMD-08
**Parallelizable:** yes

#### Phase 134 — Verifier integration + 10-Step golden fixture suite
**Goal:** E2E: plan → execute → verify on 10 fixture Steps; assert expected pass/fail.
**Depends on:** 127..P10
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

