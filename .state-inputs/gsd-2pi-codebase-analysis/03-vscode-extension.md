# VS Code Extension Analysis

## Overview
**Location:** `/vscode-extension/`
**Name:** `gsd-2`
**Publisher:** FluxLabs
**Version:** 0.1.0
**Engine:** VS Code ^1.95.0
**Categories:** AI, Chat
**Source Files:** 4 TypeScript files (1,611 LOC)

## File Structure
```
vscode-extension/
├── package.json (manifest + config)
├── package-lock.json
├── tsconfig.json
├── README.md, LICENSE, CHANGELOG.md
├── logo.jpg
├── .gitignore, .vscodeignore
└── src/
    ├── extension.ts (360 lines — activation, command registry)
    ├── gsd-client.ts (521 lines — RPC client via stdin/stdout)
    ├── sidebar.ts (446 lines — webview sidebar provider)
    └── chat-participant.ts (284 lines — @gsd chat participant)
```

## Activation & Lifecycle
- **Activation Event:** `onStartupFinished` (after VS Code startup)
- No per-folder activation — starts immediately for any workspace

## Commands (15 total)

| Command | Title | Handler |
|---------|-------|---------|
| `gsd.start` | Start Agent | Spawns `gsd --mode rpc` |
| `gsd.stop` | Stop Agent | Kills process |
| `gsd.newSession` | New Session | RPC `new_session` |
| `gsd.sendMessage` | Send Message | RPC `prompt` with user input |
| `gsd.cycleModel` | Cycle Model | RPC `cycle_model` |
| `gsd.cycleThinking` | Cycle Thinking Level | RPC `cycle_thinking_level` |
| `gsd.setThinking` | Set Thinking Level | QuickPick + RPC `set_thinking_level` |
| `gsd.switchModel` | Switch Model | QuickPick + RPC `set_model` |
| `gsd.compact` | Compact Context | RPC `compact` |
| `gsd.abort` | Abort Current Operation | RPC `abort` |
| `gsd.exportHtml` | Export Conversation as HTML | RPC `export_html` + file picker |
| `gsd.sessionStats` | Show Session Stats | RPC `get_session_stats` |
| `gsd.runBash` | Run Bash Command | RPC `bash` |
| `gsd.steer` | Steer Agent | RPC `steer` (interrupt mid-stream) |
| `gsd.listCommands` | List Available Commands | RPC `get_commands` |

## Keyboard Shortcuts
- `Cmd+Shift+G Cmd+Shift+N` (macOS) / `Ctrl+Shift+G Ctrl+Shift+N` — New Session
- `Cmd+Shift+G Cmd+Shift+M` — Cycle Model
- `Cmd+Shift+G Cmd+Shift+T` — Cycle Thinking Level

## Configuration Settings

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `gsd.binaryPath` | string | `"gsd"` | Path to GSD binary |
| `gsd.autoStart` | boolean | `false` | Auto-start agent on activation |
| `gsd.autoCompaction` | boolean | `true` | Enable automatic context compaction |

## Source File Details

### extension.ts (360 lines)
- Activates on startup
- Creates `GsdClient` and `GsdSidebarProvider`
- Registers 15 commands with error handling
- Listens to connection changes, logs stderr
- Applies auto-compaction setting on startup
- Implements auto-start if configured
- Cleanup on deactivation

### gsd-client.ts (521 lines)
- Spawns `gsd --mode rpc --no-session` subprocess
- JSON-RPC communication over stdin/stdout
- Auto-restart logic (max 3 restarts in 60s)
- EventEmitter for connection/error/event streaming
- 40+ RPC methods:
  - **Prompting**: `sendPrompt()`, `steer()`, `followUp()`, `abort()`
  - **State**: `getState()`, `getSessionStats()`, `getMessages()`
  - **Model**: `setModel()`, `getAvailableModels()`, `cycleModel()`
  - **Thinking**: `setThinkingLevel()`, `cycleThinkingLevel()`
  - **Compaction**: `compact()`, `setAutoCompaction()`
  - **Session**: `newSession()`, `switchSession()`, `exportHtml()`
  - **Commands**: `getCommands()`
- 30-second timeout per RPC call
- Graceful cleanup with SIGTERM/SIGKILL

### sidebar.ts (446 lines)
- `WebviewViewProvider` for the sidebar panel
- Dynamic HTML with inline CSS + nonce-based CSP
- Displays: status dot, session info, model, thinking level, message count, token stats, cost
- Real-time updates from connection/streaming events
- Periodic refresh every 10 seconds
- Auto-compaction toggle

### chat-participant.ts (284 lines)
- Registers `@gsd` chat participant
- Auto-starts agent if disconnected
- Injects `#file` references as markdown code blocks
- Streams tool execution events as progress messages
- Shows file anchors for modified files
- Token usage summary
- Followup suggestions: `/gsd status`, `/gsd auto`, `/gsd capture`

## RPC Protocol
- **Request format**: `{ id: "req_N", type: "prompt", message: "..." }`
- **Response format**: `{ id: "req_N", type: "response", command: "prompt", success: true, data?: unknown }`
- **Event format**: `{ type: "agent_start" | "message_update" | ... }`
- Newline-delimited JSON (NDJSON)

## Build & Packaging
```bash
npm run build    # tsc → dist/extension.js
npm run package  # vsce package → .vsix
npm run publish  # vsce publish to marketplace
```
- Target: ES2022, Module: Node16
- Strict mode, source maps

## Python Rebuild Implications
For a Python rebuild, the VS Code extension would need to be rewritten to communicate with a Python backend:
- Replace `gsd --mode rpc` spawn with Python process spawn
- Keep the same NDJSON RPC protocol (language-agnostic)
- The extension itself stays as TypeScript (VS Code extensions must be JS/TS)
- Consider also building a JetBrains plugin (Python), Neovim plugin (Lua), etc.
