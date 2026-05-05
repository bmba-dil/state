---
phase: 089
goal: "route.register({ name: 'state.dag' }); topological layout algorithm"
wave: 1
depends_on: [080]
files_modified: [src/tui/dag-viewer.ts, src/tui.ts, src/tui/dag-viewer.test.ts]
autonomous: true
must_haves:
  - api.route.register() called with name "state.dag"
  - DAG route renders nodes with topological layout
  - layout handles ≥50 nodes without visual overlap
  - component follows existing state/pattern conventions
---

# Plan 089-1: DAG Viewer Route + Topological Layout

**Goal:** Register a `state.dag` route in the opencode TUI that renders a DAG visualization using a topological layout algorithm, consuming live DAG state from the daemon via SSE.

## Tasks

### 089.1 Create DAG viewer component with topological layout

**Acceptance:** `src/tui/dag-viewer.ts` exists with exported types, state constant, topological layout algorithm, and render function

**Estimated effort:** Large

**Dependencies:** None (new file)

**Details:**
- Create `src/tui/dag-viewer.ts`
- Define types: `DagViewerState` (connection, nodes, edges, selectedNode), `LayoutNode` (id, name, status, row, col), reuse existing `DagNode`, `DagEdge` from `build-progress.ts`
- Implement topological layout algorithm:
  1. Layer assignment via longest-path layering: root nodes at row 0, child nodes at max(parent row) + 1
  2. Within layers, order by topological sort to minimize edge crossings (barycenter heuristic)
  3. Collapse single-child chains into vertical chains
  4. Output: `LayoutNode[]` with {row, col} positions
- Export `computeTopologicalLayout(nodes: DagNode[], edges: DagEdge[]): LayoutNode[]`
- Export `renderDagViewer(state: DagViewerState): Box` — renders full-page layout using box-drawing chars
- Export `setupDagViewer(api: TuiPluginApi): void` — wires SSE events, populates state
- Use `const T = { ... }` theme constant matching `theme.json`
- Use `createTextAttributes()` for text styling
- Color-code nodes by status (pending=white, running=blue, done=green, blocked=red, failed=red)
- Selected node shows detail sidebar (name, status, kind, edges)
- Consumers: the route render function in task 089.2 reads `DAG_VIEWER_STATE` synchronously

**Files to create:**
- `packages/opencode-plugin/src/tui/dag-viewer.ts`

**Edge cases:**
- Empty DAG (no nodes) → render empty state message
- Single node → centered rendering
- Disconnected nodes → separate component groups
- Long node names (>20 chars) → truncate with ellipsis
- Very large DAG (>100 nodes) → use virtualized viewport with scroll offset

**Testing approach:**
- Unit tests for `computeTopologicalLayout()` with various graph structures (chain, diamond, fork-join, disconnected)
- Snapshot tests for `renderDagViewer()` output

### 089.2 Register state.dag route in tui.ts

**Acceptance:** `api.route.register([{ name: "state.dag", render: ... }])` is called in `src/tui.ts`, navigating to `/state:dag` renders the DAG viewer

**Estimated effort:** Small

**Dependencies:** 089.1

**Details:**
- In `src/tui.ts`, import `renderDagViewer`, `setupDagViewer`, `DAG_VIEWER_STATE`
- In the `createTuiPlugin()` function, after slot registration, add:
  ```typescript
  const unregisterDag = api.route.register([{
    name: "state.dag",
    render: (_input) => renderDagViewer(DAG_VIEWER_STATE) as unknown as JSX.Element,
  }]);
  ```
- Register cleanup: `api.lifecycle.onDispose(() => unregisterDag())`
- Call `setupDagViewer(api)` to wire SSE events
- Consumers: opencode renders this route when user navigates to "state.dag" (via command palette or keyboard shortcut)

**Files to modify:**
- `packages/opencode-plugin/src/tui.ts`

### 089.3 Wire SSE events for live DAG state

**Acceptance:** DAG viewer updates in real-time when daemon emits step/slice/phase status changes

**Estimated effort:** Medium

**Dependencies:** 089.1

**Details:**
- In `setupDagViewer()`, subscribe to `session.status` SSE events
- Parse `session.slices` and `session.steps` from status event to build node/edge lists
- Convert slice/step data to `DagNode[]` + `DagEdge[]`:
  - Each slice → node (kind: "slice")
  - Each step → node (kind: "step")
  - Slice → step edges (kind: "blocks")
  - Cross-step dependency edges (kind: "blocks" or "data")
- If daemon connection is `unreachable`, fall back to placeholder DAG stored in state
- Also subscribe to `session.next.step.ended` for node status updates
- Consumers: `renderDagViewer()` reads the reactive state synchronously

**Files to modify:**
- `packages/opencode-plugin/src/tui/dag-viewer.ts`

### 089.4 Write tests for DAG viewer

**Acceptance:** `src/tui/dag-viewer.test.ts` exists with tests for layout algorithm, rendering, and SSE wiring

**Estimated effort:** Medium

**Dependencies:** 089.1, 089.3

**Details:**
- Test `computeTopologicalLayout()`:
  - Chain of 5 nodes → correct layer assignment (5 rows)
  - Diamond pattern → correct branching/merging
  - Fork-join → correct parallel paths
  - Disconnected components → separate groups
  - Empty input → empty output
  - Single node → position (0,0)
  - 50-node stress test → no overlapping positions
- Test `renderDagViewer()`:
  - Empty state → displays "No DAG data" message
  - 3-node chain → output contains all 3 node names
  - Selected node → detail pane visible
- Test state updates via SSE mock:
  - Mock `api.event.on()` to capture subscriptions
  - Simulate session.status event → state.nodes updated
  - Simulate disconnection → state.connection "unreachable"

**Files to create:**
- `packages/opencode-plugin/src/tui/dag-viewer.test.ts`

### 089.5 Run build and verify

**Acceptance:** `bun build` succeeds, route is navigable

**Estimated effort:** Small

**Dependencies:** 089.1, 089.2, 089.3, 089.4

**Details:**
- Run `bun build` in `packages/opencode-plugin/`
- Verify no TypeScript errors
- Verify `dist/` contains updated bundle with dag-viewer code
- Consumers: the build output is what opencode loads at startup

### Integration Notes
- This phase is the foundation for phases 090-095 (node rendering, click-to-detail, filter bar, SSE updates, keyboard nav, performance)
- The DAG viewer component serves as the container that later phases will enhance
- Follows existing TUI component pattern (state + render + setup)

### Deviation Notes
- ROADMAP says `route.register({ name: "state.dag" })` but the opencode API is `api.route.register([{ name: "state.dag", render: ... }])` — adapted to actual API
- The "topological layout algorithm" is implemented as longest-path layering with barycenter heuristic, which is the standard approach for DAG visualization
