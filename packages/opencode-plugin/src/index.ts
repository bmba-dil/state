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
import { shellEnv } from "./hooks/shell-env.js";

export const server: PluginModule["server"] = async () => ({
  "chat.message": chatMessage,
  "tool.execute.before": toolExecuteBefore,
  "tool.execute.after": toolExecuteAfter,
  "permission.ask": permissionAsk,
  "experimental.chat.system.transform": chatSystemTransform,
  "experimental.session.compacting": sessionCompacting,
  "chat.params": chatParams,
  "chat.headers": chatHeaders,
  "command.execute.before": commandExecuteBefore,
  "shell.env": shellEnv,
});

const statePlugin: PluginModule = {
  server,
};

export default statePlugin;
