/** Cached mode reader — wraps readModeConfig with module-level cache */

import { readModeConfig } from "./hooks/config.js";

export type ResolvedMode = "build" | "teach" | "both" | null;

let cachedMode: ResolvedMode | undefined;

/**
 * Return the active mode from .state/mode.json.
 * Reads the file once and caches the result at module scope.
 * Returns null when mode.json is absent, malformed, or contains an
 * invalid mode — callers treat null as permissive (no blocking).
 */
export async function getCurrentMode(projectDir: string): Promise<ResolvedMode> {
  if (cachedMode !== undefined) return cachedMode;
  const mode = await readModeConfig(projectDir);
  // readModeConfig returns "build" | "teach" | "both" | null
  cachedMode = mode as ResolvedMode;
  return cachedMode;
}

/**
 * Invalidate the cached mode so the next getCurrentMode() call
 * re-reads .state/mode.json. Used for hot-reload on mode change.
 */
export function resetModeCache(): void {
  cachedMode = undefined;
}
