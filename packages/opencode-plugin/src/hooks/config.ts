/** Config hook — reads .state/mode.json and registers build/teach MCP servers at boot */

import type { Config, Hooks } from "@opencode-ai/plugin";
import { log } from "../logger.js";

/**
 * Read and parse .state/mode.json from the project root.
 * Returns the validated mode string, or null if the file is
 * missing, malformed, or contains an invalid mode value.
 */
export async function readModeConfig(projectDir: string): Promise<string | null> {
  const path = `${projectDir}/.state/mode.json`;
  const f = Bun.file(path);

  if (!(await f.exists())) {
    log({ msg: "mode.json not found — MCP servers will not be registered", path });
    return null;
  }

  try {
    const text = await f.text();
    const data = JSON.parse(text);
    const mode = data.mode;

    if (mode !== "build" && mode !== "teach" && mode !== "both") {
      log({ msg: "Invalid mode in mode.json — expected build/teach/both", path, mode });
      return null;
    }

    return mode;
  } catch (err) {
    log({ msg: "Failed to parse mode.json", path, error: String(err) });
    return null;
  }
}

/**
 * Apply MCP server registration based on the active mode.
 * Mutates input.plugin in-place: removes any existing state-*
 * entries, then pushes the correct servers for the given mode.
 */
export function applyMcpRegistration(mode: string | null, input: Config): void {
  input.plugin = input.plugin || [];

  // Remove any existing state-* entries from prior plugin loads
  input.plugin = input.plugin.filter((p) => {
    const name = Array.isArray(p) ? p[0] : p;
    return name !== "state-build" && name !== "state-teach";
  });

  if (mode === "build" || mode === "both") {
    input.plugin.push("state-build");
  }

  if (mode === "teach" || mode === "both") {
    input.plugin.push("state-teach");
  }

  log({
    msg: "config hook: MCP registration applied",
    mode,
    build_active: mode === "build" || mode === "both",
    teach_active: mode === "teach" || mode === "both",
  });
}

export const config: NonNullable<Hooks["config"]> = async (input) => {
  const cwd = process.cwd();
  const mode = await readModeConfig(cwd);
  applyMcpRegistration(mode, input);
};
