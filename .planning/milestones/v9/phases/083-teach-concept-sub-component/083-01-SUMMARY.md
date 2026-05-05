---
phase: 083-teach-concept-sub-component
plan: 01
subsystem: teach-concept
tags: [TUI, teach-mode, sidebar, concept-card, Kolb, mastery-bar]
requires: [081-01-sidebar-content-renderer]
provides:
  - TeachConcept sub-component (teach-concept.ts) with event-driven state, Kolb stage display, block-character mastery bar
  - Pure rendering functions kolbStageLabel and masteryBar
  - Wiring into tui.ts event bus and sidebar-content-renderer.ts renderActiveState
affects: [v9-TUI-bundle, teach-dashboard]
tech-stack:
  added: []
  patterns:
    - Module-level mutable state (same pattern as build-progress.ts)
    - @opentui/core constructs API (Box, Text, createTextAttributes)
    - Event-driven sidebar sub-components via api.event subscriptions
    - Pure rendering functions exported for testability
    - TDD RED/GREEN cycle per task
key-files:
  created:
    - packages/opencode-plugin/src/tui/teach-concept.ts (342 lines)
    - packages/opencode-plugin/src/tui/teach-concept.test.ts (126 lines)
  modified:
    - packages/opencode-plugin/src/tui.ts (import + setupTeachConcept call)
    - packages/opencode-plugin/src/tui/sidebar-content-renderer.ts (import + renderTeachConcept calls)
key-decisions:
  - "Mastery bar uses fixed-width 4-char right-aligned label (e.g., '  0%', ' 42%', '100%') with 4 padding spaces between 20-cell bar and label — total 28 chars to match sidebar slot width"
  - "All 4 Kolb stages use info color (#3B82F6) for stage indicator — simple, readable, semantically maps to informational/learning content"
  - "Description split uses word-boundary-aware line breaking with max 3 lines and U+2026 truncation"
  - "renderTeachPlaceholder kept exported from sidebar-content-renderer.ts for existing test compatibility"
patterns-established:
  - "TeachConcept follows the same module-level mutable state + event wiring + pure render function architecture as BuildProgress (Phase 082)"
  - "Setup functions (setupBuildProgress, setupTeachConcept) are called sequentially in createTuiPlugin() — both subscribe to session.status independently"
  - "Render functions are called from renderActiveState in sidebar-content-renderer.ts based on mode resolution"
requirements-completed: [TUI-02]
metrics:
  duration: 4m
  completed: 2026-05-05
---

# Phase 083 Plan 01: TeachConcept Sub-Component Summary

**One-liner:** Live teach-mode sidebar sub-component showing active concept with Kolb learning stage, truncated description, and block-character mastery bar — wired into the opencode TUI plugin event bus alongside BuildProgress.

## Tasks Executed

| Task | Name | Type | Commit |
|------|------|------|--------|
| 1 | Create TeachConcept component with pure rendering functions | auto (tdd) | `7aca167` (RED), `ff0937f` (GREEN) |
| 2 | Wire TeachConcept into tui.ts event bus and sidebar-content-renderer.ts | auto | `92c17ac` |

## What Was Built

### Task 1: TeachConcept Component

**File:** `packages/opencode-plugin/src/tui/teach-concept.ts` (342 lines)

**Exports:**
- `kolbStageLabel(stage)` — maps KolbStage enum to display label (Concrete Experience, Reflective Observation, Abstract Conceptualization, Active Experimentation)
- `masteryBar(score)` — returns 28-char block-character bar: 20 cells (▓ fill, ░ empty) + 4 spacer + right-aligned percentage label
- `renderTeachConcept()` — returns Box tree with 4 mutually exclusive states
- `setupTeachConcept(api)` — subscribes to `session.status` for daemon connectivity heartbeat
- `TEACH_CONCEPT_STATE` — module-level state object

**State rendering matrix:**

| Connection | Concept | What Renders |
|------------|---------|-------------|
| connected | non-null | ● Concept name (accent) + ◈ Stage label (info) + description + mastery bar |
| connected | null | ● No active concept (textMuted) + empty state copywriting |
| disconnected | — | ● No active concept + "Connection lost. Retrying…" (warning) |
| unreachable | — | ● No active concept + "state-daemon not running" (error) + recovery instructions |

**Placeholder concept data:** Python Type Hints (reflective_observation, 42% mastery) — demonstrates all rendering sections with project-relevant data.

### Task 2: Event Bus and Sidebar Wiring

**`tui.ts` changes:**
- Import `setupTeachConcept` from `./tui/teach-concept.js`
- Call `setupTeachConcept(api)` after `setupBuildProgress(api)` — both subscribe independently to `session.status`
- Updated comment block documenting Phase 083 wiring

**`sidebar-content-renderer.ts` changes:**
- Import `renderTeachConcept` from `./teach-concept.js`
- Teach mode: `renderTeachConcept()` replaces `placeholderBox(renderTeachPlaceholder())`
- Both mode: `renderTeachConcept()` stacked directly with `renderBuildProgress()` (no placeholder wrapper)
- `renderTeachPlaceholder` still exported for existing test compatibility

## Verification Results

| Check | Result |
|-------|--------|
| `tsc --noEmit` | ✓ No errors |
| `bun test` (all 3 suites) | ✓ 47 pass, 0 fail |
| teach-concept.ts lines | ✓ 342 (≥150) |
| teach-concept.test.ts lines | ✓ 126 (≥60) |
| Export count | ✓ 5 exports (setupTeachConcept, renderTeachConcept, kolbStageLabel, masteryBar, TEACH_CONCEPT_STATE) |
| PLACEHOLDER_CONCEPT | ✓ Referenced in both comment documentation and event handler |
| Import in tui.ts | ✓ `import { setupTeachConcept }` + call |
| Import in sidebar-content-renderer.ts | ✓ `import { renderTeachConcept }` + usage in teach/both modes |
| `placeholderBox(renderTeachPlaceholder())` count | ✓ 0 (fully replaced) |
| `renderTeachPlaceholder` count | ✓ 2 (export + function — kept for tests) |
| Color tokens match theme.json | ✓ All 8 tokens: accent, success, info, textMuted, error, warning, text, border |
| Copywriting matches UI-SPEC | ✓ Verbatim for all error/disconnected/empty states |
| Mastery bar character set | ✓ U+2593 (▓) fill, U+2591 (░) empty |
| No import cycles | ✓ tui.ts → teach-concept.ts only; sidebar-content-renderer.ts → teach-concept.ts only |
| Both event handlers coexist | ✓ setupBuildProgress + setupTeachConcept both subscribe to session.status |

## Deviations from Plan

None — plan executed exactly as written, with one implementation clarification:

**masteryBar label format:** The plan's test behavior specified exact ending patterns (`/  0%$/`, `/ 42%$/`, `/100%$/`). To satisfy both the 28-char width constraint and these regex expectations, the implementation uses a fixed-width 4-char right-aligned label format: `String(score).padStart(3, " ") + "%"` producing `"  0%"`, `" 42%"`, `"100%"`. This differs slightly from the plan's narrative description of variable-width labels but matches the test behavior specifications exactly.

## Known Stubs

**PLACEHOLDER_CONCEPT** — The component uses static placeholder concept data ("Python Type Hints", reflective_observation, 42%) when the daemon is connected but no teach daemon events are available. The real concept data path is structured and ready: the `TEACH_CONCEPT_STATE.concept` field accepts `ConceptData | null`, and the event handler in `setupTeachConcept` sets this field. A future teach daemon event type will replace the placeholder assignment. This is the same architectural pattern as BuildProgress's placeholder DAG nodes from Phase 082.

## Gates Encountered

No checkpoint gates — plan type is `auto`, fully autonomous execution.

## Self-Check: PASSED

- [✓] `packages/opencode-plugin/src/tui/teach-concept.ts` exists (342 lines)
- [✓] `packages/opencode-plugin/src/tui/teach-concept.test.ts` exists (126 lines)
- [✓] Commit `7aca167`: RED phase (failing test + stub)
- [✓] Commit `ff0937f`: GREEN phase (full implementation)
- [✓] Commit `92c17ac`: Task 2 wiring (tui.ts + sidebar-content-renderer.ts)
