# v18 — Teach Kernel: Kolb + Concepts + Mental-Model Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Teach Kernel: Kolb + Concepts + Mental-Model (A18)

- [ ] **TCH-01**: Concept-graph projection from subject authoring (CONCEPT-GRAPH.json) — nodes (concepts), edges (prerequisites)
- [ ] **TCH-02**: Kolb state machine: `concrete-experience → reflective-observation → abstract-conceptualization → active-experimentation` per concept
- [ ] **TCH-03**: Event-sourced mental-model — OBSERVATIONS.jsonl is authoritative; MENTAL-MODEL.json is a projection rebuildable from event log
- [ ] **TCH-04**: Concept-teacher orchestrates mode selection + personality + Kolb stage for each concept
- [ ] **TCH-05**: Drop-to-simpler-mode on frustration signal (detected from observation patterns)
- [ ] **TCH-06**: `state teach next-concept` surfaces the right next concept given current mastery
- [ ] **TCH-07**: Learner privacy: observations never leak raw user inputs; structured schemas only
- [ ] **TCH-08**: Rebuild MENTAL-MODEL.json from OBSERVATIONS.jsonl on demand (`state teach mental-model rebuild`)
