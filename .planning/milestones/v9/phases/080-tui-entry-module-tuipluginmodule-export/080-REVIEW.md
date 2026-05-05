---
phase: 080-tui-entry-module-tuipluginmodule-export
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - packages/opencode-plugin/src/index.ts
  - packages/opencode-plugin/src/theme.json
  - packages/opencode-plugin/src/tui.ts
findings:
  critical: 1
  warning: 3
  info: 4
  total: 8
status: issues_found
---

# Phase 080: Code Review Report

**Reviewed:** 2026-05-05
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the three source files in scope for Phase 080 (TUI entry module + TuiPluginModule export): `index.ts` (plugin entry, hook shim), `theme.json` (dark-mode color tokens), and `tui.ts` (TuiPlugin with theme install, slot registration, SSE subscription). Also cross-checked all 9 hook modules imported by `index.ts` for type consistency and error patterns.

**Key concern:** In `tui.ts`, the theme installation (`api.theme.install`) uses a path constructed from `import.meta.url` to load `theme.json` at runtime. After bundling with `bun build`, this asset is not available at the resolved path — a guaranteed runtime failure. This is a **MUST FIX** blocker.

Additional findings include unsafe type assertions in the SSE event handler, `console.log` usage throughout, and a minor ID inconsistency between the plugin module and theme metadata.

---

## Must Fix

### MF-01: theme.json unavailable after bundling — runtime theme install will fail

**File:** `packages/opencode-plugin/src/tui.ts:20-21`
**Issue:** The theme installation constructs a file path from `import.meta.url`:

```ts
const themeURL = new URL("./theme.json", import.meta.url);
await api.theme.install(themeURL.pathname);
```

After bundling with `bun build src/index.ts --outdir=dist ...`, `theme.json` is **not** included in the `dist/` output — the bundler only processes TypeScript/JavaScript, not standalone `.json` assets. At runtime, `themeURL.pathname` resolves to something like `/app/dist/theme.json`, which does not exist. The `api.theme.install()` call will fail silently or throw an error that propagates through the async plugin loader, potentially breaking the entire TUI plugin load.

**Fix:**
```ts
// Option A: Inline the theme object and register it directly (no file I/O)
import themeData from "./theme.json" with { type: "json" };
// ... inside plugin setup:
await api.theme.register(themeData);

// Option B: Copy theme.json to dist/ in the build script (bundle or dist npm script):
// "dist": "tsc && bun run bundle && cp src/theme.json dist/"
```

If the `@opencode-ai/plugin/tui` API only supports `install(path)` and not `register(object)`, then Option B with the build script is the required path. Otherwise, inlining avoids the file dependency entirely — the preferred approach.

---

## Should Fix

### SF-01: Unsafe type cast in SSE event handler — loss of type safety

**File:** `packages/opencode-plugin/src/tui.ts:70-71`
**Issue:** The `api.event.on("session.status", ...)` callback casts the event to `Record<string, unknown>` and accesses `sessionID` and `status` with bracket notation:

```ts
const unsubStatus = api.event.on("session.status", (event) => {
  console.log(
    JSON.stringify({
      ...
      sessionID: (event as Record<string, unknown>).sessionID,
      status: (event as Record<string, unknown>).status,
    })
  );
});
```

If the actual event type from `@opencode-ai/plugin/tui` provides a typed interface for `session.status` events, this cast defeats TypeScript checking. If the event shape changes or the event type string is wrong, the code will still compile but produce silent data errors at runtime.

**Fix:**
```ts
// Import the typed event interface (if available from @opencode-ai/plugin/tui)
import type { SessionStatusEvent } from "@opencode-ai/plugin/tui";

const unsubStatus = api.event.on("session.status", (event: SessionStatusEvent) => {
  console.log(
    JSON.stringify({
      source: "@state/opencode-plugin/tui",
      type: "event.session.status",
      sessionID: event.sessionID,
      status: event.status,
    })
  );
});
```

If `SessionStatusEvent` is not exported from the plugin package, the type cast should at minimum include a runtime guard (`event && typeof event === "object"`) and use a locally-defined interface with proper typing.

---

### SF-02: console.log used for operational logging — no filtering, no levels

**Files:**
- `packages/opencode-plugin/src/tui.ts:31-33, 35-39, 66-73`
- `packages/opencode-plugin/src/hooks/chat-message.ts:57-67`
- `packages/opencode-plugin/src/hooks/tool-execute-after.ts:17-26, 34-43`
- `packages/opencode-plugin/src/hooks/permission-ask.ts:17-29, 41-53, 57-69`
- `packages/opencode-plugin/src/hooks/command-execute-before.ts:48-57`

**Issue:** Six of the nine hooks plus `tui.ts` use raw `console.log` for operational observability. These logs are emitted unconditionally — no level differentiation (debug/info/warn/error), no production toggle, no structured logger. In a production deployment these log streams will be noisy, unactionable, and may slow down the event loop if the underlying stdout is synchronous.

**Fix:** Replace `console.log` calls with the project-mandated structured logger (`structlog>=25.1` from the tech stack):

```ts
// In a shared logging utility (e.g., src/logger.ts):
import { createLogger } from "structlog";
export const log = createLogger({ source: "@state/opencode-plugin" });

// Usage:
log.info("tui.slot.init", { order: 100 });
log.debug("event.session.status", { sessionID: event.sessionID, status: event.status });
```

Minimally, gate with an environment variable if structlog isn't importable yet in the plugin package:

```ts
const DEBUG = process.env.STATE_DEBUG === "1";
if (DEBUG) console.log(JSON.stringify({ ... }));
```

---

### SF-03: Unnecessary `async` on synchronous `server()` factory

**File:** `packages/opencode-plugin/src/index.ts:14`
**Issue:** The `server` property is defined as `async () => ({...})` but the function body contains zero `await` expressions — it returns a plain object literal synchronously:

```ts
export const server: PluginModule["server"] = async () => ({
  "chat.message": chatMessage,
  ...
});
```

While the `PluginModule["server"]` type from `@opencode-ai/plugin` may require an `async` signature (returning `Promise<Record<...>>`), if the type is `() => Record<...> | Promise<Record<...>>`, the `async` keyword is pure overhead — it wraps the object in `Promise.resolve()` unnecessarily, adding a microtask scheduling delay.

**Fix:** Verify the `PluginModule["server"]` type. If it accepts a synchronous return:

```ts
export const server: PluginModule["server"] = () => ({
  "chat.message": chatMessage,
  ...
});
```

If the type requires `Promise<>`, document the constraint to prevent future reviewers from flagging this again.

---

## Worth Knowing

### WK-01: Theme mode hardcoded to "dark" — no light-mode support

**File:** `packages/opencode-plugin/src/theme.json:3`
**Issue:** The theme is locked to `"mode": "dark"` with no mechanism to switch to light mode. If opencode supports user-level theme switching, this plugin will always force dark mode regardless of preference.

**Suggestion:** Consider exposing a mode toggle via environment variable or plugin config, or registering both dark and light themes and deferring to the opencode theme selection API.

---

### WK-02: 8-digit hex color may lack broad parser support

**File:** `packages/opencode-plugin/src/theme.json:14`
**Issue:** `"backgroundElement": "#33415599"` uses 8-character hex notation (RRGGBBAA format, 99 = 60% alpha). This is valid per CSS Color Level 4, but older color parsers (particularly those in terminal/TUI toolkits predating 2024) may only support 6-char hex. If opencode's TUI rendering engine or `@opentui` has a limited color parser, this alpha channel may be silently dropped or cause a parse error.

**Suggestion:** Verify with the `@opentui/core` 0.1.99 color token parser that 8-character hex is supported. If not, convert to `rgba(51, 65, 85, 0.6)` format.

---

### WK-03: Plugin ID mismatch between theme and TuiPluginModule

**Files:**
- `packages/opencode-plugin/src/theme.json:2` — `"name": "@state/opencode-plugin"`
- `packages/opencode-plugin/src/tui.ts:85` — `id: "@state/opencode-plugin/tui"`

**Issue:** The theme metadata uses the short name `@state/opencode-plugin`, while the `TuiPluginModule` uses the qualified sub-path `@state/opencode-plugin/tui`. If opencode's plugin registry uses these identifiers for matching or deduplication, the mismatch could cause the theme to be associated with the wrong plugin.

**Suggestion:** Align to one convention — either both use `@state/opencode-plugin/tui` (scoped to the TUI module) or both use `@state/opencode-plugin` (scoped to the full plugin). The sub-path `.../tui` is more precise.

---

### WK-04: All TUI slot handlers return empty strings — placeholder phase

**File:** `packages/opencode-plugin/src/tui.ts:41-57`
**Issue:** All four slot renderers (`sidebar_content`, `sidebar_footer`, `home_footer`, `session_prompt_right`) return empty string `""`. This is intentional per the comments (phases 081–088 replace these), but until those phases land, the plugin registers fully-functional slot hooks that render nothing — consuming rendering cycles for zero visual output.

**Suggestion:** Consider gating the `api.slots.register(slotPlugin)` call behind an environment variable or feature flag so the placeholder slots don't activate until the real components are ready. Or stub them out entirely and add registration in the implementing phases.

---

_Reviewed: 2026-05-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
