/** @state/opencode-plugin — hook shim + TUI extensions for opencode */

import type { PluginModule } from "@opencode-ai/plugin";
import { chatMessage } from "./hooks/chat-message.js";
import { toolExecuteBefore } from "./hooks/tool-execute-before.js";
import { toolExecuteAfter } from "./hooks/tool-execute-after.js";
import { permissionAsk } from "./hooks/permission-ask.js";
import { chatSystemTransform } from "./hooks/chat-system-transform.js";
import { sessionCompacting } from "./hooks/session-compacting.js";
import { chatParams, chatHeaders } from "./hooks/chat-params.js";
import { commandExecuteBefore } from "./hooks/command-execute-before.js";
import { config } from "./hooks/config.js";
import { event } from "./hooks/event.js";
import { shellEnv } from "./hooks/shell-env.js";

// PluginModule["server"] type is Plugin = (input, options?) => Promise<Hooks>.
// The Promise<Hooks> return type requires the async keyword even though the
// body has no await expressions — without it, the type assignment fails.
export const server: PluginModule["server"] = async () => ({
  "chat.headers": chatHeaders,
  "chat.message": chatMessage,
  "chat.params": chatParams,
  "command.execute.before": commandExecuteBefore,
  "config": config,
  "event": event,
  "experimental.chat.system.transform": chatSystemTransform,
  "experimental.session.compacting": sessionCompacting,
  "permission.ask": permissionAsk,
  "shell.env": shellEnv,
  "tool.execute.after": toolExecuteAfter,
  "tool.execute.before": toolExecuteBefore,
});

const statePlugin: PluginModule = {
  server,
};

export default statePlugin;

export { TuiPluginModule } from "./tui.js";
