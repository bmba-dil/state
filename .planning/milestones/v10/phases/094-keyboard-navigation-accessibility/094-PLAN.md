# 094-PLAN — Keyboard Navigation + Accessibility

## Tasks

### T1 — Add focusFilter() function
```
focusFilter(state): void
```
Toggles `focusFilter` boolean on state. When true, arrow keys navigate filter presets
instead of DAG nodes.

### T2 — Add announcementText and focusFilter to state
```
announcementText: string
focusFilter: boolean
```

### T3 — Create keybind definitions
In setupDagViewer:
```
const keybinds = api.keybind.create({
  navigateUp: "up",
  navigateDown: "down",
  select: "return",
  deselect: "escape",
  focusFilter: "f",
});
```

### T4 — Wire keyboard events
In setupDagViewer, listen for keyboard events and dispatch to navigation functions.
Use api.renderer or api.event for key event source.

### T5 — Add screen-reader announcements
On node focus change: announce focused node name + status
On filter change: announce filter preset + count

### T6 — Add tests
- focusFilter toggles flag
- All navigation paths verified (wrap-around, empty state)
- Announcement text updated on navigation
- Focus initializes on first arrow key when null

## Verification
- `cd packages/opencode-plugin && bun test src/tui/dag-viewer.test.ts`
