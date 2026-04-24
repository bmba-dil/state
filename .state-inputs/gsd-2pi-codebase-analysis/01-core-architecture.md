# GSD Core Architecture Analysis

## Entry Point and Bootstrap Flow

### loader.ts (Primary Bootstrap)
Runs BEFORE cli.ts to perform dependency validation and environment setup:
- Checks Node.js version (requires v22+) and git availability
- Sets critical environment variables:
  - `PI_PACKAGE_DIR`: Points to `pkg/` directory for GSD branding
  - `GSD_CODING_AGENT_DIR`: Override for pi's agent directory path
  - `NODE_PATH`: Prepends gsd's node_modules so extensions can resolve @gsd/* packages
  - `GSD_VERSION`: Package version from package.json
  - `GSD_BIN_PATH`: Absolute path to loader.js (used by headless for subagent spawning)
  - `GSD_WORKFLOW_PATH`: Path to bundled GSD-WORKFLOW.md
  - `GSD_BUNDLED_EXTENSION_PATHS`: Dynamically discovered bundled extensions
- Sets up HTTP proxy support via undici if env vars are set
- Links/copies workspace packages (@gsd/*) into node_modules (handles Windows where symlinks fail)
- Dynamically imports cli.js after all setup complete

### cli.ts (Main Orchestrator, ~662 lines)
Parses minimal CLI arguments to detect mode flags (--print, --continue, --web, etc.)

**Early exits for non-interactive modes:**
- `--version`: Print version and exit
- `--help`: Show help text and exit
- Package commands: `install`, `remove`, `list` handled by pi SDK
- `config`: Re-run onboarding wizard
- `update`: Update GSD via npm
- `gsd web stop`: Stop web server
- `gsd web / --web`: Launch web mode
- `gsd sessions`: List and pick past sessions
- `gsd headless`: Run without TUI
- `gsd worktree`: Manage git worktrees

**Validation checks:**
- TTY check (exit if non-interactive without --print or subcommand)
- Version mismatch check: Ensures managed resources aren't newer than binary
- Terminal width warning (minimum 40 columns recommended)

**Setup phase (interactive mode):**
- Provision managed tools (fd, rg) to ~/.gsd/agent/bin/
- Create AuthStorage from ~/.gsd/agent/auth.json
- Migrate credentials from pi's auth.json if needed
- Create ModelRegistry and SettingsManager
- Run onboarding wizard if no LLM provider configured
- Check for updates (non-blocking background check)
- Validate configured model; fallback to sensible default if missing
- Set quiet startup, thinking level, and changelog collapse flags

**Print/subagent mode:**
- Create session (in-memory or disk-backed)
- Load resources via DefaultResourceLoader
- Create agent session with extensions
- Support --mode (text|json|rpc|mcp)
- MCP server mode connects to Model Context Protocol
- Exit immediately

**Interactive mode:**
- Per-directory session storage via getProjectSessionsDir()
- Migrate legacy flat sessions to per-cwd structure
- Create SessionManager (new, continue recent, or open specific)
- Build and reload resource loader (overlapped with session setup)
- Create agent session with extensions
- Restore scoped models from settings
- Print welcome screen (branded two-panel layout)
- Launch InteractiveMode TUI

---

## Resource Management and Bundling

### resource-loader.ts (~492 lines)
**Purpose:** Sync bundled extensions/agents/skills from src/resources/ to ~/.gsd/agent/ on every launch

**Chooser logic:** Prefers dist/resources/ (stable, set at build time) over src/resources/ (live working tree)

**Resource sync process:**
- Reads managed-resources.json to track installed version/content
- Computes lightweight SHA256 fingerprint of resources to detect same-version changes
- Prunes stale root-level extension files removed from bundle
- Syncs extensions/, agents/, skills/ to agent directory
- Tracks installed extensions/root files for next upgrade cleanup
- Makes all files owner-writable (handles Nix store read-only copies)
- Creates node_modules symlink pointing to gsd's node_modules

**Extension loading:**
- buildResourceLoader() creates DefaultResourceLoader with:
  - GSD's bundled extensions (from ~/.gsd/agent/extensions/)
  - Pi's extensions (from ~/.pi/agent/extensions/) as fallback
  - Filters by extension registry enable/disable state

### extension-discovery.ts (~81 lines)
- Discovers extension entry points under extensions/ directory
- Top-level .ts/.js files are standalone extensions
- Subdirectories resolved via package.json pi.extensions field, with index.ts/index.js fallback
- Returns array of absolute paths to extension entry points

### extension-registry.ts (~220 lines)
- **Manifest structure:** id, name, version, tier (core/bundled/community), provides (tools/commands/hooks), dependencies
- **Registry persistence:** ~/.gsd/extensions/registry.json tracks enable/disable state
- **Logic:** Extensions without manifests always load (backwards compatible); fresh installs have empty registry
- **Disable rules:** Cannot disable core extensions; all others can be disabled with reason/timestamp
- ensureRegistryEntries() auto-populates registry for newly discovered extensions

### bundled-extension-paths.ts
- Serializes/deserializes bundled extension paths (colon-delimited on Unix, semicolon on Windows)
- Used by loader.ts to set GSD_BUNDLED_EXTENSION_PATHS env var

### bundled-resource-path.ts
- Helper to resolve bundled raw resource files from package root
- Used by worktree-cli.ts to load extension modules via jiti
- Converts ESM import.meta.url into absolute path to src/resources/

---

## Web Mode Architecture

### cli-web-branch.ts (~307 lines)
- Dedicated CLI parser for web-specific flags (--host, --port, --allowed-origins)
- Handles three commands: `gsd web stop`, `gsd web start`, `gsd --web`
- Context-aware launch: if cwd is under configured devRoot, resolves to one-level-deep project directory
- Migrates legacy flat sessions to per-project structure
- Returns WebModeLaunchStatus with success/failure details

### web-mode.ts (~731 lines)
**Multi-instance registry:** ~/.gsd/web-instances.json tracks running web servers by project cwd

**Lifecycle:**
1. Resolve web host bootstrap (packaged standalone vs. source-dev)
2. Cleanup stale instances from prior ungraceful shutdowns
3. Reserve available port (os.createServer on port 0)
4. Generate auth token (32 bytes random hex)
5. Initialize resources
6. Spawn detached web host process (Node.js or npm dev for source)
7. Poll /api/boot endpoint with exponential backoff
8. Register instance in multi-instance registry
9. Open browser with authenticated URL

**Stop command:** Kill by PID, cleanup registry entries; supports --all for all instances

**Bootstrap resolution:** Checks dist/web/standalone/server.js (packaged) or web/package.json (source-dev)

**Auth token:** Passed as URL fragment (#token=...) to web frontend

**Spawn spec:** buildSpawnSpec() creates command for standalone (direct node) or source-dev (npm run dev)

---

## Headless Orchestration

### headless.ts (~582 lines)
**Purpose:** Run /gsd commands without TUI, auto-responding to extension UI requests

**CLI parser:** Supports --timeout, --json, --model, --context, --auto, --supervised, --answers, --response-timeout, --events

**Execution loop:**
1. Validate .gsd/ directory exists (unless new-milestone creating it)
2. Load context and bootstrap .gsd/ if new-milestone
3. Spawn child RPC process
4. Monitor events via RpcClient.onEvent()
5. Track state: blocked, completed, milestone-ready
6. Auto-respond to extension_ui_request events
7. Support answer injection from JSON file
8. Support supervised mode: forward interactive requests to orchestrator
9. Detect completion: terminal notifications or idle timeout
10. Chain into auto-mode if new-milestone + --auto + milestone ready
11. Restart on crash up to maxRestarts (default 3)
12. Output summary: status, duration, event count, tool calls

**Event tracking:** Observes tool_execution_start, extension_ui_request, agent_end, extension_ui_response

**Exit codes:** 0=complete, 1=error/timeout, 2=blocked

**Idle timeout:** 10s default, 30s for new-milestone

---

## Worktree Management

### worktree-cli.ts
- CLI interface for: list, merge, clean, remove, status banner
- -w flag: create auto-named or named worktree, start interactive session
- Loads extension modules via jiti from src/resources/extensions/gsd/:
  - worktree-manager.ts: create, list, remove, merge, diff
  - auto-worktree.ts: post-create hooks
  - native-git-bridge.ts: native git calls
  - git-service.ts: infer commit type
  - worktree.ts: auto-commit dirty work on session exit

### worktree-name-gen.ts
- Generates random names: adjective-verbing-noun (e.g., "noble-roaming-karp")
- Seed lists: 45 adjectives, 44 verbs, 53 nouns

---

## Authentication and Setup

### onboarding.ts (~100+ lines)
- First-run wizard using @clack/prompts for branded TUI
- Flow: logo → choose LLM provider → authenticate (OAuth or API key) → optional tool keys → summary
- All steps skippable, never crashes boot
- Tool keys: Context7, Jina, Groq (optional)
- Remote questions: Slack/Discord/Telegram configuration

### pi-migration.ts (~80 lines)
- Migrates provider credentials from ~/.pi/agent/auth.json to GSD's AuthStorage
- Detects if LLM provider exists; only runs once on first launch
- Reads Pi's settings.json to get default model/provider for fallback selection

### models-resolver.ts (~40 lines)
- Resolution with fallback to Pi's models.json
- Priority: ~/.gsd/agent/models.json → ~/.pi/agent/models.json → default GSD path

### wizard.ts (~32 lines)
- loadStoredEnvKeys(): Hydrates process.env from stored auth.json on every launch
- Maps provider IDs to env vars: BRAVE_API_KEY, CONTEXT7_API_KEY, JINA_API_KEY, SLACK_BOT_TOKEN, etc.

---

## Path and Preferences

### app-paths.ts
- appRoot: process.env.GSD_HOME or ~/.gsd
- agentDir: ~/.gsd/agent
- sessionsDir: ~/.gsd/sessions
- authFilePath: ~/.gsd/agent/auth.json
- webPidFilePath: ~/.gsd/web-server.pid
- webPreferencesPath: ~/.gsd/web-preferences.json

### project-sessions.ts
- getProjectSessionsDir(): Encodes cwd into safe subdirectory name
- Pattern: --{cwd-with-slashes-as-dashes}--
- Sessions stored per-directory, not global

### remote-questions-config.ts (~47 lines)
- saveRemoteQuestionsConfig(): Updates ~/.gsd/preferences.md with YAML frontmatter
- Handles channel (slack/discord/telegram), channel_id, timeout, poll_interval

---

## Tool Bootstrap

### tool-bootstrap.ts (~134 lines)
- ensureManagedTools(): Provision local fd and rg binaries to ~/.gsd/agent/bin/
- Resolves from PATH first; symlinks or copies to target
- Handles Windows where symlinks fail (falls back to copyFileSync)
- Detects broken symlinks and removes/recreates
- Handles Nix store read-only copies via chmod

---

## Update Management

### update-check.ts (~221 lines)
- Caches last check time to avoid repeated npm registry queries
- 24-hour cache interval; 5s fetch timeout
- Non-blocking background check; prints banner if newer version available
- checkAndPromptForUpdates(): Interactive prompt with 30s timeout before skipping
- compareSemver(): Simple semantic version comparison

### update-cmd.ts (~46 lines)
- Synchronous update via npm install -g
- Compares current vs. latest version
- Inherits stdio for interactive output

---

## UI and Branding

### logo.ts
- GSD_LOGO: 6-line ASCII art block
- renderLogo(): Applies color function to each line

### welcome-screen.ts (~117 lines)
- Two-panel layout: logo left (fixed 34 cols), info right
- Top/bottom full-width accent bars
- Shows model name, provider, directory
- Lists enabled tools (Brave, Jina, Context7, etc.)
- Fallback to simple text on narrow terminals (<70 cols)

### help-text.ts (~172 lines)
- Comprehensive help for main command and subcommands
- 8 subcommands: config, update, sessions, install, remove, list, worktree, headless
- Per-subcommand detailed help with examples

---

## Diagnostics and Monitoring

### startup-timings.ts
- Optional startup profiling via GSD_STARTUP_TIMING env var
- markStartup(): Records delta from last mark
- printStartupTimings(): Shows table at startup (if enabled)

### mcp-server.ts (~109 lines)
- Starts native MCP server over stdin/stdout
- Registers all session tools with MCP
- tools/list and tools/call request handlers
- Converts GSD tool results to MCP content format
- Enables external clients (Claude Desktop, VS Code Copilot) to use GSD tools

---

## Key Data Structures and Types

### CliFlags (cli.ts)
```
mode, print, continue, noSession, worktree, model, listModels,
extensions, appendSystemPrompt, tools, messages, web, webPath,
_selectedSessionPath
```

### HeadlessOptions (headless.ts)
```
timeout, json, model, command, commandArgs, context, contextText,
auto, verbose, maxRestarts, supervised, responseTimeout, answers, eventFilter
```

### WebModeLaunchStatus
Success: mode, ok, cwd, projectSessionsDir, host, port, url, hostKind, hostPath, hostRoot
Failure: plus failureReason, candidates

### WebInstanceRegistry
```
Record<cwd_resolved, { pid, port, url, cwd, startedAt }>
```

### ManagedResourceManifest
```
gsdVersion, syncedAt, contentHash, installedExtensionRootFiles[], installedExtensionDirs[]
```

### ExtensionManifest
```
id, name, version, description, tier, requires,
provides (tools/commands/hooks/shortcuts), dependencies
```

### ExtensionRegistry
```
version=1, entries: Record<id, { id, enabled, source, disabledAt, disabledReason }>
```

---

## Control Flow Diagram

```
loader.ts
├─ Check Node.js >=22, git available
├─ Set env vars (PI_PACKAGE_DIR, GSD_CODING_AGENT_DIR, NODE_PATH, GSD_VERSION, etc.)
├─ Link/copy workspace packages
└─ import('./cli.js')

cli.ts
├─ parseCliArgs()
├─ Version/help fast-path
├─ Package commands (install/remove/list)
├─ Subcommands:
│  ├─ config → runOnboarding()
│  ├─ update → runUpdate()
│  ├─ web stop → runWebCliBranch(stopWebMode)
│  ├─ web/--web → runWebCliBranch(launchWebMode) → web-mode.ts
│  ├─ sessions → SessionManager.list() interactive picker
│  ├─ headless → runHeadless() → headless.ts
│  └─ worktree → worktree-cli.ts (list/merge/clean/remove)
├─ Worktree flag (-w) → handleWorktreeFlag()
├─ Setup phase:
│  ├─ ensureManagedTools()
│  ├─ AuthStorage.create()
│  ├─ migratePiCredentials()
│  ├─ ModelRegistry, SettingsManager
│  ├─ shouldRunOnboarding() → runOnboarding()
│  └─ checkForUpdates()
├─ Print mode: createAgentSession() → runPrintMode() → exit
└─ Interactive mode:
   ├─ SessionManager.create()/continueRecent()/open()
   ├─ initResources() → resource-loader.ts
   ├─ buildResourceLoader() → discoverExtensionEntryPaths()
   ├─ resourceLoader.reload() (overlapped with session setup)
   ├─ createAgentSession()
   ├─ restoreScopedModels()
   ├─ printWelcomeScreen()
   └─ InteractiveMode.run()
```

---

## Key Integration Points

1. **Extension Loading Pipeline:**
   - loader.ts discovers bundled extensions → GSD_BUNDLED_EXTENSION_PATHS env var
   - resource-loader.ts syncs to ~/.gsd/agent/extensions/
   - extension-discovery.ts crawls for entry points
   - extension-registry.ts filters by enable/disable state
   - DefaultResourceLoader merges bundled + pi extensions
   - Pi SDK loads via jiti

2. **Session Persistence:**
   - Per-directory sessions via getProjectSessionsDir() encoding
   - SessionManager.create/continueRecent/open
   - JSONL files stored in ~/.gsd/sessions/--{encoded-cwd}--/

3. **Authentication Flow:**
   - onboarding.ts guides first-time setup
   - AuthStorage persists to ~/.gsd/agent/auth.json
   - loadStoredEnvKeys() hydrates process.env on every launch
   - migratePiCredentials() one-time migration from Pi

4. **Web Mode Lifecycle:**
   - cli-web-branch.ts parses web flags
   - launchWebMode() handles startup orchestration
   - Multi-instance registry (~/.gsd/web-instances.json) tracks running servers
   - Auth tokens embedded in URL fragment

5. **Headless Orchestration:**
   - Spawns child RPC process
   - Monitors RpcClient events
   - Auto-responds to extension_ui_request
   - Supports supervised mode (forward to orchestrator)
   - Answer injection for automation
