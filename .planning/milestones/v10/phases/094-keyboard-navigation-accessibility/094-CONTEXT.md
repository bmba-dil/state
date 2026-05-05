# 094-CONTEXT — Keyboard Navigation + Accessibility

**Phase:** 094 — Arrow keys, Enter, Escape, F for filter; screen-reader support
**Depends on:** 091, 092
**Target file:** `packages/opencode-plugin/src/tui/dag-viewer.ts`

## Current State

`navigateUp`, `navigateDown`, `selectFocused`, `deselectNode` already implemented.
They use topological order for traversal with wrap-around. No keyboard wiring in
setupDagViewer. No accessibility announcements.

## What This Phase Adds

1. `focusFilter()` — sets filter bar as focused target (toggles focusFilter flag)
2. Keybind definitions via `api.keybind.create()` in setupDagViewer
3. Key event wiring to dispatch arrow keys → navigate, enter → select, esc → deselect, F → focusFilter
4. `announcementText` in DagViewerState for screen-reader accessible status
5. Refine existing navigation: ensure focus is set on first node if null

## Key Decisions

- Keyboard is wired in setupDagViewer via api.renderer or api.keybind
- announceStatus(text) helper updates announcementText in state
- Wrap-around already works (implemented in navigateUp/navigateDown)
- Focus filter toggles `focusFilter` boolean in state

## Edge Cases

- No nodes: all navigation is no-op
- focusedNode is null on initial load: first arrow key sets focus to first node
- Exit filter mode: second F press or Escape returns to node navigation
