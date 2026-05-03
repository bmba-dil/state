# v22 — Scaffolding-Mentor + Coding-Partner

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 206–214 (9 phases)

---

## Phases

#### Phase 206 — Scaffolding-mentor state machine + system-prompt template
**Goal:** FSM: introduce → plan → create-file-N → reflect → next; system prompt emphasizes "never take keyboard".
**Depends on:** 187, 200
**Requirements:** SCA-01
**Parallelizable:** yes with P2

#### Phase 207 — Scaffolding-mentor observation hooks (file creation, structural decision)
**Goal:** Tap `tool.execute.after` for file-creation events; record observations.
**Depends on:** 071, 206
**Requirements:** SCA-02
**Parallelizable:** yes

#### Phase 208 — Keyboard-handoff guard (permission.ask blocks mentor-initiated writes)
**Goal:** `permission.ask` hook in scaffolding-mentor mode refuses edit/write by the agent.
**Depends on:** 072, 206
**Requirements:** SCA-03
**Parallelizable:** yes

#### Phase 209 — Coding-partner state machine + system-prompt template
**Goal:** FSM: observe → detect-stuck → hint-level-1 → hint-level-2 → hint-level-3 → back to observe.
**Depends on:** 187, 200
**Requirements:** CPT-01
**Parallelizable:** yes with P5

#### Phase 210 — Prereq teacher (from PROJECT-PLAN.md)
**Goal:** Detect missing prereqs in learner's code; proactively teach before continuing.
**Depends on:** 209
**Requirements:** CPT-02
**Parallelizable:** yes

#### Phase 211 — Accomplishments logger + end-of-session growth-note gate
**Goal:** Append to PARTNER-LOG.md; session-end event triggers growth-note write.
**Depends on:** 209
**Requirements:** CPT-03
**Parallelizable:** yes

#### Phase 212 — Coding-partner keyboard guard (never writes code for learner)
**Goal:** `permission.ask` hook in coding-partner mode refuses edit/write.
**Depends on:** 072, 209
**Requirements:** CPT-04
**Parallelizable:** yes

#### Phase 213 — Scaffolding-mentor + coding-partner handoff (common session)
**Goal:** Mentor finishes scaffold → coding-partner takes over; shared session state.
**Depends on:** 208, 212
**Requirements:** (integration)
**Parallelizable:** yes

#### Phase 214 — Golden-session regression test
**Goal:** Simulated learner session; assert no agent writes; growth note generated; observations recorded.
**Depends on:** 206..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

