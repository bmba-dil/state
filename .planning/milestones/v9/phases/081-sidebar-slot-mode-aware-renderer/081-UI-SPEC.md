---
phase: 081
slug: sidebar-slot-mode-aware-renderer
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-05
---

# Phase 081 — UI Design Contract

> Visual and interaction contract for the mode-aware sidebar renderer. This phase reads `.state/mode.json` at mount and conditionally renders the build-tree slot or concept-state slot within `sidebar_content`. The design system (colors, spacing, typography) is inherited from Phase 080 — only mode-aware render logic and slot container layout are specified here.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (terminal UI — @opentui/solid, same as Phase 080) |
| Preset | not applicable |
| Component library | @opentui/solid 0.1.99 (SolidJS + @opentui/core character-cell renderer) |
| Icon library | @opentui built-in (Nerd Font symbols, box-drawing characters) |
| Font | Monospace (user's terminal font) |
| Theme source | `src/theme.json` (created by Phase 080 — this phase reads it, does not modify it) |

**Inherited from Phase 080-UI-SPEC.** No changes to the design system. Phase 081 is a consumer of the theme registered by Phase 080.

---

## Spacing Scale

**Inherited from Phase 080-UI-SPEC.** No exceptions for this phase.

| Token | Logical Cells | Usage in Phase 081 |
|-------|--------------|---------------------|
| xs | 1 cell | Gap between mode indicator icon and label |
| sm | 2 cells | Padding between mode indicator and content divider |
| md | 3 cells | Default padding — sidebar content inset (left + right) |
| lg | 4 cells | Vertical gap between mode indicator and child slot |
| xl | 5 cells | Vertical gap between empty state icon and message |
| 2xl | 8 cells | Not used in sidebar_content (slot too narrow) |
| 3xl | 12 cells | Not used in sidebar_content |

**Slot dimensions:**
- `sidebar_content`: **30 cells wide** max (opencode-imposed constraint)
- Content area: **28 cells usable** (30 − 2 cells left padding = 28, right edge is flush; content truncated at 28 cells)
- No height constraint — sidebar grows vertically with content

---

## Typography

**Inherited from Phase 080-UI-SPEC.** Types used in this phase:

| Role | Cells Tall | Weight | Styling | Phase 081 Usage |
|------|-----------|--------|---------|-----------------|
| Body | 1 cell | normal | Default Text | Empty state messages, loading text |
| Label | 1 cell | bold | `bold` attribute | Mode indicator label ("BUILD", "TEACH", "BOTH") |
| Heading | 1 cell | bold | Bold + underline | Not used in sidebar (slot too narrow) |
| Display | 2 cells | bold | height=2 | Not used in sidebar |

**Truncation rule (inherited):** Text overflowing 28-cell content width is truncated with `…` (single ellipsis character, U+2026). No wrapping.

---

## Color

**Inherited from Phase 080-UI-SPEC.** Phase 081 uses the following tokens from `src/theme.json`:

### Mode Indicator Colors

| Mode | Color Token | RGBA | Hex | Rationale |
|------|------------|------|-----|-----------|
| Build | `accent` | `{r:99, g:102, b:241, a:1}` | #6366F1 | Primary accent — Build is the dominant mode |
| Teach | `success` | `{r:16, g:185, b:129, a:1}` | #10B981 | Green conveys growth/learning |
| Both | `info` | `{r:59, g:130, b:246, a:1}` | #3B82F6 | Blue conveys dual-mode neutrality |
| None / unknown | `textMuted` | `{r:100, g:116, b:139, a:1}` | #64748B | Muted — no active mode |

### Loading State Colors

| Element | Color Token | Styling |
|---------|------------|---------|
| Loading text | `textMuted` | `dim: true` |
| Loading spinner (if Nerd Font glyph used) | `textMuted` | Animated via opentui `spinner` or character-cycle |

### Error State Colors

| Element | Color Token | Styling |
|---------|------------|---------|
| Error heading | `error` | `bold: true` |
| Error body | `text` | normal |
| Recovery hint | `textMuted` | `dim: true` |

### Container Colors (inherited)

| Element | Color Token | Styling |
|---------|------------|---------|
| Sidebar background | `dominant` (#0F172A) | Full-height fill |
| Content divider (mode ↔ content) | `border` (#334155) | Single character row (`─` repeated, U+2500, 28 cells wide) |
| Empty state icon area | `textMuted` | `dim: true` |
| Slot content area | `dominant` | Transparent — inherits parent |

---

## Copywriting Contract

**Phase 080 defined the empty state copy for 081.** This phase adds loading and error state copy.

| Element | Copy | Notes |
|---------|------|-------|
| Primary CTA (build mode) | View Step → | Inherited from 080 — rendered by Phase 082, not 081 |
| Empty state — build mode | No active build session. Run `/gsd:execute-phase` to begin. | Inherited from 080 — shown when mode=build but no active Step |
| Empty state — teach mode | No active concept. Select a subject to begin learning. | Inherited from 080 — shown when mode=teach but no active concept |
| **Loading state** | Reading mode… | Shown while `.state/mode.json` is being read (≈200ms or less in practice; visible only on slow I/O) |
| **Error state — heading** | Cannot read mode configuration | Shown when mode.json read fails |
| **Error state — body** | state-daemon may not be running. Run `state-daemon start` to resume. | Recovery instruction |
| Destructive confirmation | Not applicable | No destructive actions in this phase |
| Mode label — build | BUILD | Uppercase label shown at top of sidebar_content |
| Mode label — teach | TEACH | Uppercase label shown at top of sidebar_content |
| Mode label — both | BOTH | Uppercase label shown at top of sidebar_content |
| Mode label — none | IDLE | Shown when mode is unset or unknown |

**Copy principles (inherited from 080):**
- Sentence case for messages (not Title Case)
- Mode labels: UPPERCASE (differentiated from body text for visual hierarchy)
- Truncate with `…` when width-constrained
- No trailing punctuation in single-line status indicators

---

## Visual Layout: Sidebar Container

### Slot Registration

Phase 081 registers the `sidebar_content` slot via the TuiPlugin API (setup by Phase 080 in `tui.ts`). The component renders into this constrained region:

```
┌──────────────────────────────────────────────────────────────┐
│  Sidebar Header (opencode default — not controlled by plugin)│
├──────────────────────────────────────────────────────────────┤
│  30 CELLS WIDE                                               │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ← 2-cell left padding                                    │ │
│ │                                                          │ │
│ │  Mode indicator row (1 cell tall, bold, uppercase)       │ │
│ │  ──────────────────────────────────────────── (divider)  │ │
│ │                                                          │ │
│ │  Slot content area (variable height)                     │ │
│ │  ├─ Build state: Phase 082's BuildProgress component     │ │
│ │  └─ Teach state: Phase 083's TeachConcept component      │ │
│ │                                                          │ │
│ │  Empty / Loading / Error states render here              │ │
│ │                                                          │ │
│ └──────────────────────────────────────────────────────────┘ │
│  Sidebar Footer (Phase 084's Statusline — 3 cells tall)     │
└──────────────────────────────────────────────────────────────┘
```

### Container Structure

| Zone | Position | Height | Content |
|------|----------|--------|---------|
| Mode indicator | Top of slot | 1 cell | `{icon} {MODE LABEL}` formatted as bold Label |
| Divider | Below mode indicator | 1 cell | 28 `─` characters (U+2500), color `border` |
| Content area | Below divider | Remaining space | Conditional render: slot / empty / loading / error |

### Mode Indicator

Format: `{Nerd Font icon} {UPPERCASE MODE}` with 1-cell gap (`xs` spacing).

| Mode | Icon (Nerd Font glyph) | Label |
|------|------------------------|-------|
| Build | `` (nf-dev-codeigniter, U+E615) or `⚒` (U+2692) fallback | BUILD |
| Teach | `` (nf-fa-graduation_cap, U+E28C) or `🎓` (U+1F393) fallback | TEACH |
| Both | `󰘨` (nf-md-sync, U+F0628) or `⇆` (U+21C6) fallback | BOTH |
| None | `○` (U+25CB) | IDLE |

Icons use `bold: false`, label uses `bold: true`. Color follows mode indicator color table above.

### Divider

Single line of 28 `─` characters (U+2500, box-drawing light horizontal). Color: `border` (#334155). This separates the mode indicator from the content area below. No left/right margin (full content width).

### Content Area States

The content area renders exactly one of four states:

#### 1. Loading State
```
  Reading mode…
```
- Typography: Body, `dim: true`, color `textMuted`
- Centered vertically in content area (or top-aligned with lg padding)
- Duration: typically <200ms; no spinner needed (visible only on slow I/O)

#### 2. Empty State (mode resolved, no active session)
```
  No active build session.
  Run /gsd:execute-phase to begin.
```
- Heading line: Body, color `textMuted`
- Instruction line: Body, `dim: true`, color `textMuted`
- 1-cell gap between heading and instruction
- Vertical alignment: top of content area with `lg` top padding

**Teach mode variant:**
```
  No active concept.
  Select a subject to begin learning.
```

#### 3. Active State (mode resolved, session active)

Slot renders the appropriate sub-component:
- **Build mode** → Phase 082's `BuildProgress` component (Step status + Slice DAG mini-view)
- **Teach mode** → Phase 083's `TeachConcept` component (concept card + mastery bar)
- **Both mode** → Both components stacked (BuildProgress above, divider, TeachConcept below)

In Phase 081, these slots are **placeholder stubs** — render a thin placeholder box with the component name in `textMuted` + `dim: true` so Phase 082/083 can swap in real implementations:
```
  ┌─ BuildProgress ──────────────────────────┐
  │ (Phase 082 will render here)              │
  └───────────────────────────────────────────┘
```

#### 4. Error State
```
  Cannot read mode configuration
  state-daemon may not be running.
  Run state-daemon start to resume.
```
- Heading: Body, `bold: true`, color `error`
- Body: Body, `dim: false`, color `text`
- Recovery hint: Body, `dim: true`, color `textMuted`
- 1-cell gap between lines
- Vertical alignment: top of content area with `lg` top padding

---

## Interaction Patterns

### Mode Resolution Flow

```
Component mount
    │
    ▼
Read .state/mode.json ──(async)──▶ Show "Reading mode…" (loading state)
    │                                    │
    ├── Success ─────────────────────────┘
    │       │
    │       ├── mode = "build" ──▶ Show BUILD indicator + BuildProgress slot
    │       ├── mode = "teach" ──▶ Show TEACH indicator + TeachConcept slot
    │       ├── mode = "both" ───▶ Show BOTH indicator + both slots stacked
    │       └── mode unset ──────▶ Show IDLE indicator + empty state
    │
    └── Error ───────────────────▶ Show error state with recovery instructions
```

### Key Behaviors

| Behavior | Specification |
|----------|---------------|
| **Mode read** | Read `.state/mode.json` once at component mount via SolidJS `createResource`. Do not poll — the daemon will push mode changes via SSE in a later phase. |
| **File path** | `.state/mode.json` relative to project root (resolved from process cwd or opencode-provided project path). |
| **mode.json schema** | `{ "mode": "build" \| "teach" \| "both" }` — JSON object with a single `mode` key. |
| **Reactivity** | Phase 081: mount-time read only. Mode changes during session are handled by Phase 082/083 SSE subscriptions (out of scope). |
| **No user interaction** | This phase is a render-only component. No keyboard navigation, no click handlers, no focus management. Phases 082/083 add list navigation. |
| **Slot registration** | The component is registered as a SolidJS component to the `sidebar_content` slot via the TuiPlugin API. Phase 080's `tui.ts` provides the registration hook; Phase 081 is the first consumer. |
| **Theme usage** | Reads tokens from the theme installed by Phase 080 via `api.theme.get()`. Does not install or modify the theme. |

### Placeholder Component Contract (for Phases 082/083)

Phase 081 defines the slot interface that Phase 082 and 083 must implement:

```
slot_component: (props: { mode: string }) => JSX.Element
```

- `mode`: The resolved mode string ("build", "teach", "both")
- The component receives no other props from Phase 081
- The component is responsible for its own SSE subscription (Phase 082/083 scope)
- The component renders within the 28-cell content area (padding already applied by the container)

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable |
| third-party | none | not applicable |

**Inherited from Phase 080.** No blocks from any registry. All UI built with @opentui/solid primitives.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
