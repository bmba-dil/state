# v15 — Build Core Commands (plan/execute/verify/ship) Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Build Kernel: Core Commands — plan/execute/verify/ship (A15)

- [ ] **CMD-01**: `/state:build:discuss <step>` — multi-turn clarification dialog, writes DISCUSS.md
- [ ] **CMD-02**: `/state:build:plan <step>` — produces PLAN.md with task decomposition, test plan, risks
- [ ] **CMD-03**: `/state:build:execute <step>` — dispatches to worker, writes EXECUTE.log, atomic commits per sub-task
- [ ] **CMD-04**: `/state:build:verify <step>` — runs the chain of verifiers; produces VERIFY.md
- [ ] **CMD-05**: `/state:build:ship <slice>` — opens PR, runs code review, finalizes Slice
- [ ] **CMD-06**: `/state:build:quick <description>` — fast path: skip Arc/Phase structure, inline Slice+Step
- [ ] **CMD-07**: Plan-checker agent validates PLAN.md will achieve goal before execute proceeds (`plan_check: true` config)
- [ ] **CMD-08**: Gray-area decision routing — planner detects ambiguity, surfaces to dialog or logs to DECISIONS.md per config
