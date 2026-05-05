# Phase 080 — UI Review

**Audited:** 2026-05-05
**Baseline:** UI-SPEC.md (Phase 080 — scaffold, no visual components)
**Screenshots:** not captured (no dev server; code-only audit — appropriate for scaffold phase with zero visual output)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | No user-facing text exists — compliant with scaffold scope |
| 2. Visuals | 4/4 | Module structure, slot registration, and theme install match spec exactly |
| 3. Color | 4/4 | All 12 semantic tokens present in theme.json; hex values verified byte-for-byte against UI-SPEC |
| 4. Typography | 4/4 | No rendered text — typography contract deferred to phases 081–088 |
| 5. Spacing | 4/4 | No rendered elements — spacing scale deferred to component phases |
| 6. Experience Design | 4/4 | Lifecycle management correct; SSE subscription with cleanup; logging gated; no registries |

**Overall: 24/24**

---

## Top 3 Priority Fixes

No BLOCKER or WARNING findings for this scaffold phase. Two **WORTH KNOWING** items noted:

1. **Theme name vs Module ID inconsistency** — Theme uses `"name": "@state/opencode-plugin"` while `TuiPluginModule.id` is `"@state/opencode-plugin/tui"`. If opencode's plugin registry scopes themes by identifier, this mismatch could cause misattribution. Align to the sub-path convention `.../tui` for both. — *WORTH KNOWING*

2. **`backgroundElement` uses 8-digit hex** — `#33415599` (RRGGBBAA format). Valid per CSS Color Level 4, but verify `@opentui/core` 0.1.99 color parser supports 8-char hex notation. If not, the alpha channel may be silently dropped. — *WORTH KNOWING*

3. *(No third finding — scaffold has zero visual defects)*

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

**Phase 080 scope:** The UI-SPEC Copywriting Contract explicitly states: "Phase 080 is a scaffold with **no user-facing text**." All copy elements in the contract are assigned to phases 081–088.

**Audit results:**
- Zero generic CTA labels (`Submit`, `Click Here`, `OK`, `Cancel`, `Save`) found in `packages/opencode-plugin/src` — `grep` returns no matches across all 13 `.ts` files.
- Zero empty-state anti-patterns (`No data`, `No results`, `Nothing`, `Empty`) — no matches.
- Zero error-state anti-patterns (`went wrong`, `try again`, `error occurred`) — no matches.
- The only string content in scaffold files is internal debug logging (JSON-structured, gated behind `STATE_DEBUG=1`).

**Slot comment strings** (`tui.ts:41-59`) contain developer-facing phase references (e.g., "Phase 081: Mode-aware renderer") — these are code comments, not user-visible copy. Acceptable.

**Verdict:** Exactly compliant with the scaffold contract. No user-facing copy exists to audit. Score: 4/4.

---

### Pillar 2: Visuals (4/4)

**Phase 080 scope:** The UI-SPEC Design System section states: "No visual components are rendered by this phase itself."

**Audit results:**
- All four registered slot renderers (`sidebar_content`, `sidebar_footer`, `home_footer`, `session_prompt_right`) return empty strings (`""`) — valid `JSX.Element` per opentui's type definition (`string | number | boolean | null | undefined | BaseRenderable`). Zero cells rendered. `tui.ts:45,49,53,57`
- The `TuiPluginModule` export structure matches the spec:
  - `tui`: A `TuiPlugin` function ✓ — `tui.ts:18` (returns `async (api) => {...}`)
  - `id`: `"@state/opencode-plugin/tui"` ✓ — `tui.ts:86`
- Theme installation via `api.theme.install()` ✓ — `tui.ts:21`
- Slot plugin registration via `api.slots.register()` ✓ — `tui.ts:64`
- SSE subscription with cleanup ✓ — `tui.ts:69-80`
- Entry point `index.ts` re-exports `TuiPluginModule` ✓ — `index.ts:36`
- `dist` build script includes `cp src/theme.json dist/` (MF-01 fix from REVIEW.md) ✓ — `package.json:10`

**Deviations from PLAN (documented, accepted):**
- `@opentui/solid` import removed: `Text` is not a top-level export from `@opentui/solid` 0.1.99. Empty strings used instead. This is a documented override in VERIFICATION.md. Actual `@opentui/solid` component imports will be added in phases 081–088. No visual impact — zero visual output either way.
- `TuiPluginModule` type import renamed to `TuiPluginModuleType` to avoid TS2395 under `verbatimModuleSyntax: true`. No semantic difference. `tui.ts:4,86`

**Verdict:** The scaffold establishes the correct structural skeleton. All slot registrations, theme installation, SSE subscription, and lifecycle cleanup match the spec. No visual defects possible for a render-zero-output scaffold. Score: 4/4.

---

### Pillar 3: Color (4/4)

**Contract:** UI-SPEC Color section defines 12 semantic tokens using RGBA `{r, g, b, a}` format. The PLAN translates these to hex for `theme.json`. This audit verifies every hex value against the RGBA source.

#### Token Verification

| Token | UI-SPEC RGBA | Expected Hex | theme.json Hex | Match |
|-------|-------------|-------------|----------------|-------|
| `text` | `{r:226, g:232, b:240, a:1}` | `#E2E8F0` | `#E2E8F0` | ✓ |
| `textMuted` | `{r:100, g:116, b:139, a:1}` | `#64748B` | `#64748B` | ✓ |
| `error` | `{r:239, g:68, b:68, a:1}` | `#EF4444` | `#EF4444` | ✓ |
| `warning` | `{r:245, g:158, b:11, a:1}` | `#F59E0B` | `#F59E0B` | ✓ |
| `success` | `{r:16, g:185, b:129, a:1}` | `#10B981` | `#10B981` | ✓ |
| `info` | `{r:59, g:130, b:246, a:1}` | `#3B82F6` | `#3B82F6` | ✓ |
| `border` | `{r:51, g:65, b:85, a:1}` | `#334155` | `#334155` | ✓ |
| `borderActive` | `{r:99, g:102, b:241, a:1}` | `#6366F1` | `#6366F1` | ✓ |
| `background` | `{r:15, g:23, b:42, a:1}` | `#0F172A` | `#0F172A` | ✓ |
| `backgroundPanel` | `{r:30, g:41, b:59, a:1}` | `#1E293B` | `#1E293B` | ✓ |
| `backgroundElement` | `{r:51, g:65, b:85, a:0.6}` | `#33415599` | `#33415599` | ✓ |
| `accent` | `{r:99, g:102, b:241, a:1}` | `#6366F1` | `#6366F1` | ✓ |

- `backgroundElement` alpha: 0.6 × 255 = 153 = `0x99` → `#33415599` correct.
- All full-opacity tokens: 6-char hex, no trailing alpha (`#RRGGBB`). Correct.
- `"mode": "dark"` declared at `theme.json:3` — compliant with spec requirement "Theme.json should set `"mode": "dark"`."

#### 60/30/10 Split Verification

| Role | Token | Hex | Usage Match |
|------|-------|-----|-------------|
| Dominant (60%) | `background` | `#0F172A` | Sidebar/dashboard/dialog backgrounds |
| Secondary (30%) | `backgroundPanel` | `#1E293B` | Cards, panels, section headers |
| Accent (10%) | `accent` | `#6366F1` | Reserved for active indicators, DAG border, mastery bar |

All three mapped correctly. Accent matches `borderActive` (`#6366F1`) as specified.

#### Accent Overuse Check

The spec reserves accent for: active Step indicator, DAG active-node border, mastery bar fill, Slice-progress highlight, selected-list-item left-border. **No components exist yet** — accent usage will be audited in phases 081–088. No violation possible.

#### Hardcoded Color Check

Zero hardcoded colors in TypeScript source files (`grep` for `#[0-9a-fA-F]{3,8}` and `rgb(` returns no matches in `packages/opencode-plugin/src/**/*.{ts,tsx}`). All color definitions are centralized in `theme.json`.

#### Worth Knowing: Theme name vs Module ID

- `theme.json:2`: `"name": "@state/opencode-plugin"`
- `tui.ts:86`: `id: "@state/opencode-plugin/tui"`

The theme uses the short name (`@state/opencode-plugin`) while the TuiPluginModule uses the qualified sub-path (`@state/opencode-plugin/tui`). If opencode's plugin registry scopes themes by identifier, this mismatch could cause misattribution. The PLAN specified `"name": "@state/opencode-plugin"` — this is per-plan, not a deviation from spec. Recommend aligning both to `@state/opencode-plugin/tui` for consistency.

**Verdict:** All 12 tokens present, all hex values correct, 60/30/10 split verified, no hardcoded colors, dark mode declared. Score: 4/4.

---

### Pillar 4: Typography (4/4)

**Contract:** UI-SPEC Typography section defines 4 text roles (Body, Label, Heading, Display) with attributes (`bold`, `italic`, `underline`, `dim`, `strikethrough`) and a truncation rule (single `…`). Typography is monospace only (terminal constraint).

**Phase 080 applicability:** The scaffold renders zero text. No `Text` component or text attributes are used. The Typography contract is established for phases 081–088 to implement.

**Audit results:**
- Zero font-size classes in source (not applicable — terminal TUI, not CSS)
- Zero font-weight variants in source
- No text rendering at all — empty-string slot renderers produce no output
- The `@opentui/solid` import (which would gate typography primitives) is deferred to phases 081–088 per documented override

**Verdict:** Typography contract is defined but not exercised in this scaffold phase. No violations possible. Score: 4/4.

---

### Pillar 5: Spacing (4/4)

**Contract:** UI-SPEC Spacing Scale defines 7 tokens (`xs` through `3xl`) measured in character cells, not pixels. Slot dimensions are constrained: `sidebar_content` ≤ 30 cells wide, `sidebar_footer` 30×3 cells, toast ≤ 50 cells wide.

**Phase 080 applicability:** No visual components rendered. Spacing tokens will be applied via `@opentui Box` props (`gap`, `padding`, `margin`) in phases 081–088.

**Audit results:**
- Zero arbitrary spacing values in code (`grep` for `[.*px]` and `[.*rem]` returns no matches)
- No `@opentui Box` components used (deferred to component phases)
- Slot registration creates placeholder renderers only — no dimensions to audit

**Verdict:** Spacing scale defined but not yet applied. No violations possible. Score: 4/4.

---

### Pillar 6: Experience Design (4/4)

**Phase 080 scope:** The scaffold provides infrastructure only: theme registration, slot pipeline, and SSE subscription. No interactive components exist.

#### Lifecycle Management

| Concern | Implementation | Status |
|---------|---------------|--------|
| Theme install | `api.theme.install()` on plugin load — `tui.ts:21` | ✓ |
| Slot registration | `api.slots.register(slotPlugin)` with `order: 100` — `tui.ts:64` | ✓ |
| SSE subscription | `api.event.on("session.status", handler)` — `tui.ts:69` | ✓ |
| Cleanup | `api.lifecycle.onDispose(() => unsubStatus())` — `tui.ts:79` | ✓ |
| Slot setup logging | `setup()` logs initialization event — `tui.ts:32` | ✓ |
| Slot dispose logging | `dispose()` logs teardown event — `tui.ts:38` | ✓ |

The lifecycle follows the pattern: install theme → register slots → subscribe events → cleanup on dispose. This is correct.

#### State Coverage

| State | Phase 080 | Future Phase |
|-------|-----------|-------------|
| Loading | N/A (scaffold — no visual) | 081–088 |
| Empty | N/A | 081 (sidebar empty states defined in spec) |
| Error | N/A | 082/083 (SSE disconnect, daemon unreachable defined in spec) |
| Disabled | N/A | 082 (blocked steps) |
| Destructive confirmation | N/A | Not applicable (spec says no destructive actions in TUI) |

No state handling is expected in this scaffold. States are defined in the Copywriting Contract for downstream phases.

#### Logging

The `logger.ts` utility (`packages/opencode-plugin/src/logger.ts:1-11`) gates all operational logging behind `process.env.STATE_DEBUG === "1"`. Production runs produce zero console output from the TUI scaffold. This addresses SF-02 from the code review.

#### SSE Event Handler

The `session.status` handler (`tui.ts:69-76`) logs structured data with `sessionID` and `status` properties — uses `event.properties.sessionID` and `event.properties.status` (correctly accessing the nested `properties` shape, fixing SF-01 from the code review). No unsafe type casts.

#### Bundle Safety

The `dist` build script includes `cp src/theme.json dist/` (`package.json:10`), ensuring the theme asset is available at runtime after bundling. This addresses MF-01 from the code review (theme.json unavailable after bundling).

#### Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable |
| third-party | none | not applicable |

No `components.json` exists in the project. No blocks from any registry are used. All UI is built with `@opentui/solid` primitives (bundled with opencode). Clean.

**Verdict:** Lifecycle management is correct and complete (install → register → subscribe → cleanup). Logging is gated. Bundle safety ensured. Zero registry exposure. No interactive state handling expected at this phase. Score: 4/4.

---

## Files Audited

| File | Lines | Role |
|------|-------|------|
| `packages/opencode-plugin/src/tui.ts` | 88 | TuiPluginModule export, theme install, slot registration, SSE subscription |
| `packages/opencode-plugin/src/theme.json` | 16 | Dark-mode theme with 12 semantic color tokens |
| `packages/opencode-plugin/src/index.ts` | 36 | Entry point — re-exports TuiPluginModule alongside server hooks |
| `packages/opencode-plugin/src/logger.ts` | 11 | Shared debug-gated logger (created during REVIEW-FIX) |
| `packages/opencode-plugin/package.json` | 30 | Catalog versions, dist script with theme.json copy |
| `.planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-UI-SPEC.md` | 195 | Design contract — audit baseline |
| `.planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-01-PLAN.md` | 429 | Implementation plan — expected deliverables |
| `.planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-01-SUMMARY.md` | 136 | Execution summary — deviations and decisions |
| `.planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-REVIEW.md` | 208 | Code review — prior findings (all fixed) |
| `.planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-REVIEW-FIX.md` | 60 | Fix report — 4/4 findings resolved |
| `.planning/milestones/v9/phases/080-tui-entry-module-tuipluginmodule-export/080-VERIFICATION.md` | 125 | Verification report — 8/8 truths passed |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS (4/4 — no user-facing text, compliant with scaffold scope)
- [x] Dimension 2 Visuals: PASS (4/4 — correct module structure and slot registration)
- [x] Dimension 3 Color: PASS (4/4 — all 12 tokens verified byte-for-byte, dark mode, 60/30/10 split)
- [x] Dimension 4 Typography: PASS (4/4 — contract established, no violations possible)
- [x] Dimension 5 Spacing: PASS (4/4 — scale defined, no violations possible)
- [x] Dimension 6 Registry Safety: PASS (4/4 — zero registries, zero blocks, clean)
