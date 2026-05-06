# v13 — state-teach MCP Server (skeleton) Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### MCP: state-teach server (A13)

- [x] **MCP-T-01**: Server registered as `state-teach` in opencode MCP config
- [x] **MCP-T-02**: ≤15 tools with ≤80-token descriptions each
- [x] **MCP-T-03**: Tools include: `concept_next`, `drill_prepare`, `drill_verify`, `concept_teach`, `observation_record`, `mental_model_show`, `subject_pick`, `subject_author`, `style_edit`, `learner_state`, `review_session`, `mentor_scaffold`, `coding_partner`, `learning_verify`
- [ ] **MCP-T-04**: Drill tools bind to opencode `question` tool for structured user input
- [ ] **MCP-T-05**: Observations are structured (schema-validated) only — no freeform text observations
- [ ] **MCP-T-06**: Drill prompts capped at ≤3000 tokens to prevent bloat
