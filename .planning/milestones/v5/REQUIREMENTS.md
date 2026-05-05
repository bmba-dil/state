# v5 — DAG Scheduler Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Kernel: DAG Scheduler (A5)

- [x] **DAG-01**: Pure-Python scheduler (~300 LOC) — topological sort, cycle detection, typed `depends_on` edges (`blocks`, `soft`, `data`)
- [x] **DAG-02**: Scheduler dispatches unblocked Slices/Steps up to a configurable concurrency cap
- [x] **DAG-03**: TaskGroup watchdog — detects swallowed `CancelledError`, fails loud, prevents deadlock
- [x] **DAG-04**: Reactive to event-store updates — new Slice completion immediately unblocks successors
- [ ] **DAG-05**: Priority inversion detection — warns when a soft dependency keeps a critical-path Slice blocked
- [ ] **DAG-06**: Silent-deadlock detection — if all in-flight Slices are blocked on descoped/missing predecessors, surface to TUI
- [x] **DAG-07**: `state dag show [--arc|--phase|--slice]` CLI renders current DAG state as ASCII
