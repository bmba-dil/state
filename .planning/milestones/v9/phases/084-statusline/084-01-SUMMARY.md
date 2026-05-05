---
phase: 084-statusline
plan: 01
subsystem: tui
tags: [statusline, footer, sse-events, constructs-api, nerd-font]
requires:
  - "080: TUI entry module (tui.ts plugin skeleton)"
  - "081: Sidebar content renderer (mode reading pattern)"
  - "082: BuildProgress (event wiring pattern)"
provides:
  - "statusline.ts — one-line statusline component for sidebar_footer and home_footer slots"
  - "Cost tracking via session.next.step.ended SSE event"
  - "Provider display via session.next.model.switched SSE event"
affects:
  - "087: PromptHint (session_prompt_right slot, may share cost/provider state)"
  - "Future: TUI dashboard (multi-line footer with richer status data)"
tech-stack:
  added: []
  patterns:
    - "Module-level mutable state + sync render (same pattern as build-progress.ts)"
    - "Constructs API (Box/Text/TextAttributes) for render trees — no JSX"
    - "Nerd Font glyphs for mode icons (matching sidebar-content-renderer.ts)"
    - "Sync mode.json read at render time (matching sidebar-content-renderer.ts)"
    - "Truncate(28) for fixed-width footer rendering"
key-files:
  created:
    - packages/opencode-plugin/src/tui/statusline.ts
    - packages/opencode-plugin/src/tui/statusline.test.ts
  modified:
    - packages/opencode-plugin/src/tui.ts
key-decisions:
  - "Use session.next.step.ended for cost (SDK has no standalone session.cost event)"
  - "Use session.next.model.switched for provider (SDK has no cost.provider field)"
  - "Render Box element (not string) for footer slots — matches constructs API pattern"
  - "28-cell width cap with U+2026 ellipsis truncation — consistent with other TUI components"
  - "Em dash (—) for empty/unknown values — consistent copywriting contract"
patterns-established:
  - "statusline follows build-progress event-handling pattern: module-level state + event subscriptions + lifecycle cleanup + sync render"
  - "Pure functions (formatCost, getModeIcon, getModeColor) exported for testability"
  - "Txt() helper function for concise inline Text element construction"
  - "JSDoc block header documenting all exports, threat mitigations, and SDK deviations"
requirements-completed:
  - TUI-03
metrics:
  duration: 5m
  completed: 2026-05-05
---

# Phase 84 Plan 01: Statusline Component Summary

One-line statusline component rendering mode icon + scope + provider + cost in `sidebar_footer` and `home_footer` TUI slots. Subscribes to daemon SSE cost/status/provider events via `api.event` bus, updates module-level state, and renders synchronously using @opentui/core constructs API.

## What Was Built

### statusline.ts (222 lines)
Component with 9 sections following the established patterns from `build-progress.ts` and `sidebar-content-renderer.ts`:

1. **Types**: `StatuslineState` interface (connection, mode, step, provider, cost)
2. **Theme colors**: `T` constant matching theme.json hex values exactly
3. **Text attributes**: `ATTR_BOLD` / `ATTR_DIM` pre-computed via `createTextAttributes`
4. **Mode icons**: Nerd Font glyphs (nf-dev-codeigniter for build, nf-fa-graduation_cap for teach, nf-md-sync for both, white circle fallback)
5. **Module-level state**: `STATUSLINE_STATE` — exported const for test inspection
6. **Pure functions**: `formatCost()` (T-084-01 validated), `getModeIcon()`, `getModeColor()`
7. **Mode reader**: `readModeSync()` — sync `.state/mode.json` reader (same pattern as sidebar-content-renderer)
8. **Render**: `renderStatusline()` — single-line Box tree with 3 states (connected, disconnected, unreachable)
9. **Event wiring**: `setupStatusline(api)` — subscriptions + lifecycle cleanup

### statusline.test.ts (20 tests)
- `formatCost`: 5 tests (dollar format, undefined/em dash, rounding)
- `getModeIcon`: 3 tests (build/teach/unknown glyphs)
- `getModeColor`: 4 tests (accent/success/info/textMuted)
- `STATUSLINE_STATE defaults`: 5 tests (connection/mode/step/provider/cost)
- `renderStatusline`: 3 tests (non-null for all connection states)

### tui.ts modifications
- Import `setupStatusline` and `renderStatusline` from `./tui/statusline.js`
- Call `setupStatusline(api)` after `setupTeachConcept(api)` in plugin initialization
- Replace `sidebar_footer` placeholder (`""`) with `renderStatusline() as unknown as string`
- Replace `home_footer` placeholder (`""`) with `renderStatusline() as unknown as string`

## Deviations from Plan

### Planned Deviations (documented in plan's interfaces section)

**1. SDK event type mismatch: `session.cost` does not exist**
- **Found during:** Task 1 implementation (SDK type inspection)
- **Issue:** The plan specified `api.event.on("session.cost", handler)` with `event.properties.totalCost` and `event.properties.provider`. The opencode SDK v2 has no standalone `session.cost` event type.
- **Resolution:** Cost data arrives via `session.next.step.ended` (`properties.cost`). Provider data arrives via `session.next.model.switched` (`properties.providerID`). The plan explicitly instructs: "If the exact `session.cost` or `session.status` event type shape differs from what's described, inspect `@opencode-ai/sdk/v2` types at build time to match the actual properties. Adapt field access accordingly."
- **Files modified:** `statusline.ts` (setupStatusline event subscriptions)
- **Commit:** bba405b

## Threat Mitigations

All four threat mitigations from the plan's threat model are implemented:

| Threat ID | Status | Implementation |
|-----------|--------|---------------|
| T-084-01 | ✓ Mitigated | `formatCost()` validates `typeof number && isFinite()`, clamps to 0–100000 |
| T-084-02 | ✓ Accepted | Cost display only — no privacy boundary crossed |
| T-084-03 | ✓ Mitigated | `readModeSync()` wraps `readFileSync` in try/catch, returns `"unknown"` on failure |
| T-084-04 | ✓ Accepted | Provider name is display-only, not used for auth decisions |

## Verification Results

| Check | Result |
|-------|--------|
| `bun test src/tui/statusline.test.ts` | 20 pass, 0 fail |
| `bun test src/tui/` (all TUI tests) | 67 pass, 0 fail |
| `bun run typecheck` | Pass (no errors) |
| `renderStatusline` in tui.ts (slot calls) | 2 matches (sidebar_footer, home_footer) |
| `setupStatusline` in tui.ts (call site) | 1 match (plugin init) |

## Self-Check: PASSED

- [x] `statusline.ts` exists at `packages/opencode-plugin/src/tui/statusline.ts`
- [x] `statusline.test.ts` exists at `packages/opencode-plugin/src/tui/statusline.test.ts`
- [x] `tui.ts` modified with correct imports and wiring
- [x] All 20 statusline tests pass
- [x] All 67 TUI tests pass (no regressions)
- [x] TypeScript typecheck passes
- [x] All exports verified: `setupStatusline`, `renderStatusline`, `STATUSLINE_STATE`, `formatCost`, `getModeIcon`, `getModeColor`
- [x] Requirement TUI-03 satisfied
