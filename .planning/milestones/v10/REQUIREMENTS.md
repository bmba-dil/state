# v10 — TUI DAG Viewer Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### TUI: DAG Viewer (A10)

- [ ] **DAG-VIEW-01**: `/state:dag` route shows interactive DAG — nodes colored by status (pending/in-progress/done/failed/blocked)
- [ ] **DAG-VIEW-02**: Clicking a node opens detail pane with STEP.md / SLICE.md / PHASE.md / ARC.md contents
- [ ] **DAG-VIEW-03**: Filter by Arc, Phase, Slice, or show critical path
- [ ] **DAG-VIEW-04**: Live updates as scheduler advances state (via SSE)
