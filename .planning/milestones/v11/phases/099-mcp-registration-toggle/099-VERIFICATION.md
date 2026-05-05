---
phase: 099-mcp-registration-toggle
verified: 2026-05-05T22:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
deferred:
  - truth: "Hot-reload on mode change (event hook calls applyMcpRegistration to re-register MCP servers)"
    addressed_in: "Phase 104"
    evidence: "Phase 104 goal: 'Emit event on mode change; SSE fan-out triggers MCP reload.' The event.ts scaffold logs mode changes and re-reads mode.json, but defers daemon client API calls for MCP re-registration until the daemon SSE event bus ships."
human_verification:
  - test: "Hot-reload MCP re-registration on mode change is not yet functional"
    expected: "Event hook logs the mode transition but does not re-register MCP servers. This is an intentional scaffold for Phase 104. No action needed now."
    why_human: "Cannot test hot-reload without daemon SSE event bus (Phase 104). The scaffold pattern is confirmed valid — it listens for state.mode.activated, re-reads mode.json, and logs the transition. Full MCP re-registration deferred."
  - test: "Type cast workaround for state.mode.activated event type"
    expected: "The `as string | undefined` cast in event.ts:19 is a workaround because `state.mode.activated` is not yet in the opencode SDK Event.type union. Phase 104 will add this event type to the daemon SSE event bus."
    why_human: "The type cast is correct for now but should be removed when the SDK adds the event type. This is a known deferral to Phase 104."
---

# Phase 099: MCP Registration Toggle Verification Report

**Phase Goal:** Plugin reads `.state/mode.json` at boot; `config` hook returns enabled/disabled for each server; hot-reload on mode change.
**Verified:** 2026-05-05T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | When mode is 'build', state-build is in config.plugin and state-teach is not | ✓ VERIFIED | `applyMcpRegistration` in `config.ts` lines 51-53: only `mode === "build"` triggers `"state-build"` push; `mode === "teach"` check fails → no `"state-teach"` pushed |
| 2 | When mode is 'teach', state-teach is in config.plugin and state-build is not | ✓ VERIFIED | `applyMcpRegistration` in `config.ts` lines 55-57: only `mode === "teach"` triggers `"state-teach"` push; `mode === "build"` check fails → no `"state-build"` pushed |
| 3 | When mode is 'both', both state-build and state-teach are in config.plugin | ✓ VERIFIED | `applyMcpRegistration` lines 51-57: `mode === "both"` triggers both if-blocks → both `"state-build"` and `"state-teach"` pushed |
| 4 | When .state/mode.json is missing, no state-* MCP servers are registered (graceful degradation) | ✓ VERIFIED | `readModeConfig` line 16: `f.exists()` false → returns `null`, logs warning. `applyMcpRegistration` lines 51-57: `mode === null` → no servers pushed |
| 5 | When .state/mode.json is malformed, no state-* MCP servers are registered with a log warning | ✓ VERIFIED | `readModeConfig` line 21: JSON.parse in try/catch → returns `null`, logs error. Lines 25-28: invalid mode value → returns `null`, logs error. Both result in zero servers |

**Score:** 5/5 truths verified

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Hot-reload MCP re-registration via event hook (`applyMcpRegistration` on mode change) | Phase 104 | Phase 104 goal: "Emit event on mode change; SSE fan-out triggers MCP reload." event.ts scaffold validates listener pattern and mode re-read; full re-registration awaits daemon SSE |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `packages/opencode-plugin/src/hooks/config.ts` | Config hook reading mode.json and setting MCP registration | ✓ VERIFIED | 71 lines, 3 exports (`readModeConfig`, `applyMcpRegistration`, `config`). Full implementation with strict mode validation, graceful degradation, state-* filter. |
| `packages/opencode-plugin/src/hooks/event.ts` | Event hook scaffold for state.mode.activated hot-reload | ✓ VERIFIED | 33 lines (plan specified min_lines: 40 — minor discrepancy from intentional scaffold brevity). Export: `event`. Listens for `state.mode.activated`, re-reads mode.json, logs transition. Full MCP re-registration deferred to Phase 104. |

### Artifact Substantive Check (Level 2)

| Artifact | Lines | Key Patterns Present | Substantive? |
| -------- | ----- | -------------------- | ------------ |
| `config.ts` | 71 | `Bun.file`, `exists()`, `JSON.parse` + try/catch, strict mode validation (`===`), `filter()` for state-* removal, `push()` for registration | ✓ Yes |
| `event.ts` | 33 | `NonNullable<Hooks["event"]>`, event type filter, `readModeConfig` reuse, structured logging | ⚠️ Scaffold — logs only, no `applyMcpRegistration` call (intentional, deferred to P104) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `index.ts` | `hooks/config.ts` | `import { config }` | ✓ WIRED | Line 12: `import { config } from "./hooks/config.js"`; Line 24: `"config": config` in server object |
| `hooks/config.ts` | `.state/mode.json` | `Bun.file` read | ✓ WIRED | Lines 12-13: path constructed with `mode.json`, `Bun.file(path)` reads filesystem |

### Wiring Verification (Level 3)

| Artifact | Imported In | Used In (non-import) | Wired? |
| -------- | ----------- | -------------------- | ------ |
| `config.ts` → `index.ts` | Line 12 | Line 24: `"config": config` | ✓ |
| `event.ts` → `index.ts` | Line 13 | Line 25: `"event": event` | ✓ |
| `config.ts` → `event.ts` | N/A | Line 5: `import { readModeConfig } from "./config.js"` | ✓ |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `config.ts` — `config` hook | `mode` (from `readModeConfig`) | `Bun.file(".state/mode.json")` → JSON.parse → validation | ✓ Yes — reads real filesystem file, validates content | ✓ FLOWING |
| `config.ts` — `applyMcpRegistration` | `input.plugin` | Mutated in-place from validated mode | ✓ Yes — pushes real server names based on mode | ✓ FLOWING |
| `event.ts` — `event` hook | `mode` (from `readModeConfig`) | Same as config.ts → `.state/mode.json` | ✓ Yes — reads file, validates, logs | ⚠️ FLOWING to logs only (no MCP re-registration call) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| TypeScript typecheck (phase files only) | `bun run typecheck` filtered to config/event/index | Zero errors in phase 099 files | ✓ PASS |
| Hook wiring count (imports) | `grep -c "import.*from.*hooks/" index.ts` | 11 imports (9 existing + 2 new) | ✓ PASS |
| Hook wiring count (server keys) | `grep -o '"[a-z.]*":' index.ts \| sort -u \| wc -l` | 12 hook keys (10 existing + 2 new) | ✓ PASS |
| `readModeConfig` exported | `grep "export.*readModeConfig" config.ts` | Found at line 11 | ✓ PASS |
| `applyMcpRegistration` exported | `grep "export.*applyMcpRegistration" config.ts` | Found at line 42 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| MODE-03 | 099-01-PLAN.md | MCP server registration — state-build only started when mode in {build, both}; state-teach only when {teach, both} | ✓ SATISFIED | `applyMcpRegistration` in config.ts implements exact logic. `config` hook wired into index.ts. Event hook scaffold present for hot-reload path (deferred to Phase 104). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| _None in phase 099 files_ | — | — | — | — |

**Pre-existing issues (out of scope):** `bun run typecheck` reports errors in 5 test files (toast.test.ts, build-progress.test.ts, dag-viewer.test.ts, integration.test.ts, plugin-install.test.ts). These predate Phase 099 and are unrelated to this phase's implementation.

### Human Verification Required

#### 1. Hot-reload MCP re-registration is a scaffold

**Test:** Observe the event hook behavior when `state.mode.activated` events fire.
**Expected:** The event hook logs the mode transition and re-reads mode.json, but does NOT call `applyMcpRegistration` to update MCP server registration. This is an intentional scaffold — the event listener pattern and mode re-read are validated, but full re-registration awaits the daemon SSE event bus in Phase 104.
**Why human:** Cannot simulate the opencode event system without a running daemon and SSE connection. The code pattern is verified correct (imports from config.ts, validates mode, logs transition). Deferred to Phase 104.

#### 2. Type cast workaround for event type

**Test:** The `as string | undefined` cast on line 19 of event.ts.
**Expected:** This cast is necessary because `"state.mode.activated"` is not yet in the opencode SDK `Event.type` union. Without it, TypeScript reports TS2367 ("comparison appears to be unintentional"). When Phase 104 adds this event type to the daemon SSE event bus, this cast should be removed.
**Why human:** The workaround is type-safe for now but represents technical debt that Phase 104 should resolve. No action needed in this phase.

### Gaps Summary

No blocking gaps found. All 5 must-have truths verified against the codebase. All key links are wired. The config hook correctly implements mode-based MCP registration for all three valid modes with graceful degradation for missing/invalid mode.json.

The event hook scaffold is a documented, intentional deferral to Phase 104 (mode activation event with daemon SSE). The scaffold establishes the correct event listener pattern, re-uses the `readModeConfig` function from config.ts, and validates the mode re-read path. This is NOT a gap — it is a deferred item that Phase 104 is explicitly designed to complete.

One minor discrepancy: `event.ts` is 33 lines vs. the plan's `min_lines: 40` for this artifact. The file is shorter because the implementation follows the plan's exact scaffold design — brevity is not a defect when the scaffold is intentionally minimal. The plan itself specified the exact code for the scaffold.

**Pre-existing test file errors in `bun run typecheck` are out of scope for this phase and predate Phase 099.**

---

_Verified: 2026-05-05T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
