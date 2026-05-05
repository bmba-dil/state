# Phase 062: Hot State Container — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

In-memory pydantic container synced from daemon on attach; updated on events.

Requirements: WRK-11
Depends on: 061 (SSE bridge for event delivery)
</domain>

<decisions>
## Implementation Decisions

### AI's Discretion
- Container is a pydantic BaseModel holding active Slice, Step, and drill references
- Updated via SSE event callback from bridge
- Thread-safe for asyncio (single-threaded event loop)
- Mirror existing schemas from `state_core/schema.py`
- Use `state_core/schema.py` event types for SSE event parsing
</decisions>

<code_context>
## Existing Code Insights
- `state_core/schema.py` has rich event types (ArcEvent, PhaseEvent, SliceEvent, StepEvent, DrillEvent, etc.)
- `state_worker/bridge.py` SseBridge provides `on_event` callback
- `state_worker/main.py` wires bridge into main startup
</code_context>

<specifics>
## Specific Ideas
- `HotState` model with `active_slice_id`, `active_step_id`, `current_mode`, `in_progress_drill`
- `apply_event()` method converts SSE payload to state mutations
- Wire into worker main to create container after bridge connection
- Future phases (064, 065) will use hot state for handshake/teardown context
</specifics>
