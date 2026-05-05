---
phase: 080
slug: tui-entry-module-tuipluginmodule-export
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-05
---

# Phase 080 — UI Design Contract

> Visual and interaction contract for the **opencode TUI plugin** (terminal UI via SolidJS + @opentui). Phase 080 scaffolds the entry module; phases 081–088 build the component inventory against this contract.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (terminal UI — shadcn not applicable) |
| Preset | not applicable |
| Component library | @opentui/solid 0.1.99 (SolidJS bindings for @opentui/core terminal renderer) |
| Icon library | @opentui built-in (text-based terminal icons — Nerd Font symbols, box-drawing characters) |
| Font | Monospace (user's terminal font — plugin does not control this) |
| Renderer | CliRenderer from @opentui/core (character-cell grid, not pixel-based) |
| Theme source | Custom `theme.json` shipped with the plugin — overrides opencode defaults for plugin slots only |

**Phase 080 scope:** This phase creates `tui.ts` with the `TuiPluginModule` export + `TuiPlugin` entry function. It registers the custom theme and slot plugins that phases 081–088 populate. No visual components are rendered by this phase itself.

---

## Spacing Scale

Terminal UI spacing is measured in **character cells**, not pixels. The @opentui renderer maps logical units to cell dimensions.

| Token | Logical Cells | Usage |
|-------|--------------|-------|
| xs | 1 cell | Inline gaps between icon and label, badge internal padding |
| sm | 2 cells | Compact element spacing, list item gaps |
| md | 3 cells | Default element spacing, card padding |
| lg | 4 cells | Section padding, panel insets |
| xl | 5 cells | Layout gaps between major sections |
| 2xl | 8 cells | Major section breaks in sidebar |
| 3xl | 12 cells | Page-level spacing (dashboard routes) |

**@opentui Box props:** Use `gap`, `padding`, `margin` as integer cell counts. Default component padding: `padding={3}` (md) unless overridden.

Exceptions: none.

**Slot dimensions (constrained by opencode):**
- `sidebar_content`: 30 cells wide max (opencode imposes this)
- `sidebar_footer`: 30 cells wide, 3 cells tall
- `home_footer` / `session_prompt_right`: 1 line tall, variable width
- Toast notifications: fit to content, max 50 cells wide

---

## Typography

Terminal typography is **monospace only**. The user's terminal emulator controls the actual font face and size.

| Role | Cells Tall | Weight | Styling |
|------|-----------|--------|---------|
| Body | 1 cell | normal | Default @opentui Text |
| Label | 1 cell | bold | `bold` attribute on Text |
| Heading | 1 cell | bold | Bold + underline; size distinction via color (heading uses `theme.markdownHeading`) |
| Display | 2 cells | bold | Reserved for dashboard titles and route headers; rendered via @opentui Box with height=2 |

**Text attributes available via @opentui:**
- `bold`: True for emphasis
- `italic`: True for secondary text (if terminal supports it)
- `underline`: True for headings and links
- `dim`: True for muted/secondary information
- `strikethrough`: True for completed/disabled items

**Line height:** Not applicable in terminal rendering (1 cell = 1 line of text). No multi-line line-height control.

**Truncation rule:** Text that overflows its container width is truncated with `…` (single ellipsis character). No wrapping in sidebar slots. Dashboard routes may wrap.

---

## Color

Custom `theme.json` overrides opencode's defaults for the plugin's registered slots. Values use RGBA (`{r, g, b, a}` with 0–255 channels, 0–1 alpha).

### 60/30/10 Split

| Role | RGBA | Hex Equivalent | Usage |
|------|------|---------------|-------|
| Dominant (60%) | `{r:15, g:23, b:42, a:1}` | #0F172A | Sidebar background, dashboard background, dialog backgrounds |
| Secondary (30%) | `{r:30, g:41, b:59, a:1}` | #1E293B | Cards, panel surfaces, section headers, list item hover states |
| Accent (10%) | `{r:99, g:102, b:241, a:1}` | #6366F1 | **Reserved for:** active Step status indicator, DAG active-node border, mastery bar fill, Slice-progress highlight, selected list items |

### Semantic Colors

| Token | RGBA | Hex | Usage |
|-------|------|-----|-------|
| `text` | `{r:226, g:232, b:240, a:1}` | #E2E8F0 | Primary body text — high contrast on dominant background |
| `textMuted` | `{r:100, g:116, b:139, a:1}` | #64748B | Secondary/muted text — descriptions, timestamps, disabled items |
| `error` | `{r:239, g:68, b:68, a:1}` | #EF4444 | Destructive actions only — blocked Step indicator, auth failures, toast error variant |
| `warning` | `{r:245, g:158, b:11, a:1}` | #F59E0B | Gray-area decision toasts, stale status warnings |
| `success` | `{r:16, g:185, b:129, a:1}` | #10B981 | Step completion toast, verify-pass indicator, mastery milestone |
| `info` | `{r:59, g:130, b:246, a:1}` | #3B82F6 | Drill availability toast, auth refresh notification |
| `border` | `{r:51, g:65, b:85, a:1}` | #334155 | Subtle borders between sidebar sections |
| `borderActive` | `{r:99, g:102, b:241, a:1}` | #6366F1 | Active/focused element border — matches accent |
| `background` | `{r:15, g:23, b:42, a:1}` | #0F172A | Matches dominant |
| `backgroundPanel` | `{r:30, g:41, b:59, a:1}` | #1E293B | Matches secondary |
| `backgroundElement` | `{r:51, g:65, b:85, a:0.6}` | #334155 60% | Interactive element backgrounds (buttons, input fields) |

**Accent reserved for:** Active Step status indicator (the dot/block next to current Step), DAG active-node border in mini-view, mastery bar fill percentage, Slice-progress highlight bar, selected list item left-border. **Never** applied to general text, borders, or non-active badges.

**Destructive reserved for:** Blocked Step indicator, auth failure toasts, confirm-destructive dialogs. **Never** applied to informational states.

**Theme mode support:** All tokens work in `dark` mode (open code default). Light mode values are not defined — the plugin declares `dark` only. Theme.json should set `"mode": "dark"`.

---

## Copywriting Contract

Phase 080 is a scaffold with **no user-facing text**. The following copy elements are defined for phases 081–088 to use consistently.

| Element | Copy | Phase Owner |
|---------|------|-------------|
| Primary CTA (sidebar) | View Step → | 081 (sidebar slot) |
| Empty state — sidebar (build mode) | No active build session. Run `/gsd:execute-phase` to begin. | 081 |
| Empty state — sidebar (teach mode) | No active concept. Select a subject to begin learning. | 081 |
| Error state — SSE disconnect | Connection lost. Retrying… | 082/083 |
| Error state — daemon unreachable | state-daemon is not running. Run `state-daemon start` to resume. | 082/083 |
| Destructive confirmation | Not applicable (no destructive actions in TUI) | — |
| Toast — Slice complete | Slice {N} complete ✓ | 085 |
| Toast — drill available | Drill ready: {concept name} | 085 |
| Toast — auth refresh | Auth token refreshed | 085 |
| Statusline format | `{mode} · {scope} · {provider} · {cost}` | 084 |
| Prompt hint format | `{model} · {cost} · Step {N}.{m}` | 087 |

**Copy principles:**
- Use sentence case for statusline and labels (not Title Case)
- Truncate with `…` when width-constrained (single ellipsis character, not three dots)
- No trailing punctuation in statusline tokens separated by `·`
- Toast messages: 40-character max, auto-dismiss after 4 seconds (info/success), 6 seconds (warning), persistent until dismissed (error)

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable |
| third-party | none | not applicable |

No blocks from any registry are used. All UI is built with @opentui/solid primitives (bundled with opencode).

---

## Phase-Specific Constraints

### Scaffold Deliverable (Phase 080)
- `src/tui.ts` exports a `TuiPluginModule` with:
  - `tui`: A `TuiPlugin` function that registers a custom `theme.json` via `api.theme.install()`, registers slot plugins for `sidebar_content`, `sidebar_footer`, `home_footer`, and `session_prompt_right`, and subscribes to daemon SSE for state updates.
  - `id`: `"@state/opencode-plugin/tui"`
- Imports must match catalog versions byte-for-byte:
  - `solid-js@1.9.10`
  - `@opentui/core@0.1.99`
  - `@opentui/solid@0.1.99`
- The `theme.json` file is a sibling asset at `src/theme.json` with the color tokens defined above.

### Slot Registration Map (for phases 081–088)
| Slot | Phase | Component |
|------|-------|-----------|
| `sidebar_content` | 081 | Mode-aware renderer (build-tree vs concept-state) |
| `sidebar_content` → build | 082 | BuildProgress sub-component (Step + DAG mini-view) |
| `sidebar_content` → teach | 083 | TeachConcept sub-component (concept card + mastery bar) |
| `sidebar_footer` / `home_footer` | 084 | Statusline (mode + scope + provider + cost) |
| `ui.toast` | 085 | Toast notification handler (Slice, drill, decision, auth) |
| `session_prompt_right` | 087 | PromptHint (model + cost + Step indicator) |

### Visual Interaction Patterns (phases 081–088)
- **List navigation:** Arrow keys (↑↓) move focus; Enter selects. Focused item uses `borderActive` left-border (2 cells) + `accent` background highlight.
- **DAG mini-view:** Rendered with box-drawing characters (┌─┐│└─┘├┤┬┴┼). Active node uses `accent` color. Completed nodes use `success`. Blocked nodes use `error`.
- **Mastery bar:** Horizontal bar using block characters (████░░░░). Fill percentage drives bar width. Color: `accent` for fill, `backgroundElement` for empty.
- **Toast stack:** Max 3 visible toasts. New toasts push old ones up. De-duplication: same message within 10 seconds is suppressed.
- **Statusline:** Single line, no wrapping. Left-to-right: mode icon (Nerd Font), scope label, provider abbreviation, cost. Each segment separated by `·` (middle dot, U+00B7).

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
