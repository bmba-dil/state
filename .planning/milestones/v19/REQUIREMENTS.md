# v19 — Teach Drill Engine Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Teach: Drill Engine (A19)

- [ ] **DRL-01**: `drill_prepare` tool — generates drill question per concept + Kolb stage
- [ ] **DRL-02**: `drill_verify` tool — grades learner response, updates mental-model event
- [ ] **DRL-03**: Drill prompts bind to opencode `question` tool for structured input
- [ ] **DRL-04**: Drill prompt budget ≤3000 tokens
- [ ] **DRL-05**: Bayesian mastery update (prior → posterior from drill outcome); formula verified against AOL source
- [ ] **DRL-06**: `state teach drill` CLI fallback for non-opencode hosts (plain stdin)
