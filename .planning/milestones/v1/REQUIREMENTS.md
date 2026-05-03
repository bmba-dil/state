# v1 — Event Store Foundation Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Kernel: Event Store (A1)

- [x] **EVT-01**: Daemon writes every domain event to `.state/events.sqlite` (WAL, synchronous=NORMAL) before mirroring to opencode `SyncEvent`
- [x] **EVT-02**: SQLite is the authoritative event source; daemon reads history from SQLite only
- [x] **EVT-03**: Event sequence is monotonic per stream (Arc / Phase / Slice / Step / concept / learner); crash-recovery reconciles gaps
- [x] **EVT-04**: Startup reconciliation replays unsent events to opencode's `SyncEvent` when opencode reconnects
- [x] **EVT-05**: Pydantic event schemas with `extra = "forbid"` for every event type
- [x] **EVT-06**: Event payloads are deterministic (no `datetime.now()` / randomness in handlers); replay is bit-identical
- [x] **EVT-07**: CLI: `state events tail`, `state events replay --from <ulid>`, `state events export --format jsonl`
- [x] **EVT-08**: Every event carries `mode: build|teach|kernel` for filtering
