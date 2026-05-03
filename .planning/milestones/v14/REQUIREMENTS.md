# v14 — Build Kernel: Step FSM + Verifiers Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Build Kernel: Step FSM + Verifiers (A14)

- [ ] **BLD-01**: Step state machine: `pending → discussing → planning → executing → verifying → shipped | reverted | blocked`
- [ ] **BLD-02**: STEP.md frontmatter schema: `goal`, `verify_contract`, `depends_on[]`, `model_profile`, `snapshots[]`, `cost_cap`
- [ ] **BLD-03**: Goal-backward verifier — reads STEP.md goal, walks committed code, asserts goal achievement; writes VERIFY.md with pass/fail + evidence
- [ ] **BLD-04**: Slice rollup verifier — aggregates Step verify results; fails Slice if any Step failed
- [ ] **BLD-05**: Phase rollup verifier — aggregates Slice verify results plus Phase-level integration tests
- [ ] **BLD-06**: Arc rollup verifier — aggregates Phase rollups plus Arc-level acceptance criteria
- [ ] **BLD-07**: Cross-tier integration verifier — runs after Arc boundary, checks interactions between completed Arcs
- [ ] **BLD-08**: Security verifier — runs per-Step, checks for common vulnerabilities in diff (SQL injection, path traversal, secret leakage, shell meta)
- [ ] **BLD-09**: Verifier writes structured results to SQLite + markdown VERIFY.md
