# Web & Studio Frontend Analysis

## Technology Stack

### Web Application (`/web/`) — Next.js 16.1.6
- **Framework:** React 19.2.4 with Next.js 16.1.6 (App Router)
- **Language:** TypeScript 5.7.3
- **Build:** Webpack (Turbopack disabled due to extensionAlias needs)
- **State Management:** Custom Zustand-like store (GSDWorkspaceStore)
- **Styling:** Tailwind CSS 4.2.0 with postcss
- **Components:** Radix UI v1.x-2.x (40+ components)
- **Icons:** Lucide React 0.564.0
- **Terminal:** xterm.js 6.0.0 with CodeMirror 4.25.8
- **Charts:** Recharts 2.15.0
- **Animation:** Motion 12.36.0 (Framer Motion API)
- **Forms:** React Hook Form 7.54.1 + Zod validation
- **Toasts:** Sonner 1.7.1
- **Markdown:** react-markdown + remark-gfm
- **Theme:** next-themes 0.4.6 (dark mode)
- **PTY:** node-pty 1.1.0 (server-side pseudo-terminal)

### Studio Desktop (`/studio/`) — Electron + Vite + React
- **Framework:** Electron 41.0.3
- **Renderer:** React 19.2.0 + Vite 5.0.0
- **Build:** electron-vite 5.0.0
- **Styling:** Tailwind CSS 4.2.1
- **Icons:** Phosphor Icons 2.1.10
- **State:** Zustand 5.0.8
- **Layout:** react-resizable-panels 4.7.3
- **Fonts:** Inter, JetBrains Mono (custom woff2)

---

## API Routes (40 total in `/web/app/api/`)

### Core Infrastructure
- `GET /api/boot` — Initial project/workspace payload
- `GET /api/live-state` — Selective state updates (auto, workspace, resumable_sessions)

### Terminal/PTY
- `GET /api/terminal/stream` — SSE stream of PTY output
- `POST /api/terminal/input` — Send input to PTY
- `POST /api/terminal/resize` — Resize PTY
- `GET /api/terminal/sessions` — List active sessions
- `POST /api/terminal/upload` — File upload
- `GET /api/bridge-terminal/stream` — Secondary terminal stream
- `POST /api/bridge-terminal/input` — Secondary terminal input
- `POST /api/bridge-terminal/resize` — Secondary terminal resize

### Session Management
- `POST /api/session/command` — Send RPC command to agent bridge
- `GET /api/session/browser` — Browse and manage sessions
- `POST /api/session/manage` — Rename, fork, or delete sessions
- `GET /api/session/events` — Stream session state events

### Diagnostics & Utility
- `GET /api/doctor` — Run diagnostics
- `GET /api/forensics` — Forensic analysis
- `GET /api/skill-health` — Skill status checks
- `GET /api/history` — Execution history
- `GET /api/visualizer` — Visualization data
- `GET /api/knowledge` — Knowledge/captures management
- `GET /api/files` — File browser
- `GET /api/git` — Git summary
- `GET /api/inspect` — Inspection data
- `GET /api/hooks` — Hooks configuration
- `GET /api/steer` — Steering data
- `GET /api/undo` — Undo state
- `GET /api/export-data` — Export results
- `GET /api/cleanup` — Cleanup analysis
- `GET /api/projects` — Project discovery
- `GET /api/preferences` — Preferences
- `GET /api/settings-data` — Settings data
- `GET /api/captures` — Captures data
- `GET /api/onboarding` — Onboarding state
- `GET /api/remote-questions` — Remote questions
- `GET /api/update` — Update availability
- `GET /api/dev-mode` — Dev mode toggles
- `POST /api/switch-root` — Switch project root
- `GET /api/browse-directories` — Directory browser
- `GET /api/recovery` — Recovery options
- `POST /api/shutdown` — Graceful shutdown

---

## State Management Architecture

### Primary Store: GSDWorkspaceStore
- Custom external store with `useSyncExternalStore` hook
- Provider: `GSDWorkspaceProvider` context

**Key State Domains:**
- `boot`: WorkspaceBootPayload (project, workspace index, auto-dashboard, onboarding, bridge runtime)
- `workspace`: Current workspace index (milestones, slices, tasks, active scope, validation issues)
- `auto`: AutoDashboardData (active/paused/stepMode, current/completed units, costs, tokens)
- `bridge`: BridgeRuntimeSnapshot (agent session state, models, thinking level, streaming status)
- `onboarding`: WorkspaceOnboardingState (provider auth flows, OAuth status)
- `commandSurface`: OpenCommandSurfaceState (active dialog/panel, pending actions)
- `sessionBrowser`: Session browsing/filtering state
- `recovery`: Recovery diagnostics when auto-mode fails

### Per-Project Store: ProjectStoreManager
- Map<projectCwd, GSDWorkspaceStore>
- Auto-disconnects SSE on inactive projects, reconnects on reactivation
- Lazy creates stores on first access

### Terminal Chat Parser (`pty-chat-parser.ts`)
- Stateful message accumulator consuming SSE data chunks
- ANSI stripping via regex
- Detects TUI prompts (select lists, text inputs, checkboxes)
- Emits structured ChatMessage[] with completion signals

---

## Component Architecture

### Layout Hierarchy
```
GSDAppShell (main container)
├── DevOverridesProvider
├── ProjectStoreManagerProvider
├── GSDWorkspaceProvider (state context)
├── ProjectSelectionGate (project picker overlay)
├── OnboardingGate (multi-step wizard overlay)
├── WorkspaceChrome (main UI)
│   ├── NavRail (left icon bar: views, theme, logout)
│   ├── Sidebar (milestones, slices, tasks, status icons)
│   │   ├── MilestoneExplorer (hierarchical view)
│   │   └── CollapsedMilestoneSidebar (compact mode)
│   ├── MainContent (center, resizable panels)
│   │   ├── ViewRenderer (dashboard/chat/files/activity/roadmap/visualize)
│   │   └── FocusedPanel (full-screen modal)
│   ├── DualTerminal (bottom: shell + main session terminal)
│   ├── CommandSurface (overlay: settings, diagnostics, recovery)
│   └── UpdateBanner (top: update notification)
```

### Views

| View | File | Lines | Purpose |
|------|------|-------|---------|
| Dashboard | `dashboard.tsx` | 560 | Metrics cards, progress, activity timeline |
| Chat Mode | `chat-mode.tsx` | 2100+ | Message rendering, TUI prompts, action buttons, image support |
| Files | `files-view.tsx` | 1200+ | Tree explorer, dual-root, syntax highlighting via Shiki |
| Activity | `activity-view.tsx` | — | Timeline of completed units |
| Roadmap | `roadmap.tsx` | — | Visual planning board |
| Visualizer | `visualizer-view.tsx` | — | Interactive TUI, progress graphs, metrics |
| Projects | `projects-view.tsx` | 1400+ | Project picker, GSD folder detection, session history |

### Onboarding Wizard (9 steps)
1. **step-welcome.tsx** — Intro with logo
2. **step-mode.tsx** — Solo vs Team selection
3. **step-provider.tsx** — LLM provider selection
4. **step-authenticate.tsx** — API key or OAuth
5. **step-project.tsx** — Select/create GSD project
6. **step-dev-root.tsx** — Development root directory
7. **step-optional.tsx** — Optional integrations (Slack, Discord)
8. **step-remote.tsx** — Remote auto-mode setup
9. **step-ready.tsx** — Final confirmation

### Command Surface (`command-surface.tsx`, 2500+ lines)
Sheet-based overlay with panels:
- QuickPanel — Common shortcuts
- SettingsPanels — Prefs, Model Routing, Budget, Remote Questions, General
- DiagnosticsPanels — Doctor, Forensics, Skill Health
- KnowledgeCapturesPanel — Knowledge base management
- SessionManagement — Switch, rename, fork
- GitIntegration — Branch operations
- RecoveryOptions — Auto-mode failure recovery
- AdminPanel — Dev overrides

### UI Component Library (59 base components in `/components/ui/`)
All built on Radix UI primitives with Tailwind CSS styling:
- **Interaction:** button, checkbox, input, select, slider, switch, textarea, toggle
- **Feedback:** alert, dialog, drawer, popover, tooltip, progress, sheet, toast
- **Navigation:** breadcrumb, dropdown-menu, menubar, sidebar, tabs, accordion
- **Layout:** card, resizable panels, scroll-area, separator
- **Display:** avatar, badge, table, chart

---

## Styling & Theming
- oklch color space for accessible color math
- CSS custom properties for light/dark themes
- Default: always dark
- Theme toggle via next-themes (class-based)
- Tailwind CSS with class-variance-authority for component variants

---

## Backend Bridge Architecture

### Bridge Service (`/src/web/bridge-service.ts`, 2000+ lines)
1. Spawns `node src/loader.ts --mode rpc` as child process
2. Bidirectional event stream via stdin/stdout/stderr
3. Forwards HTTP requests to stdin as JSON RPC commands
4. Parses stdout for RPC responses and AgentSessionEvents

### Service Modules (`/src/web/*.ts`, 23 services)
Each wraps a GSD subcommand or feature:
- bridge-service.ts — RPC bridge lifecycle
- auto-dashboard-service.ts — Real-time execution metrics
- onboarding-service.ts — Provider auth, OAuth flows
- history-service.ts — Metrics ledger parsing
- forensics-service.ts — Failure analysis
- doctor-service.ts — Diagnostics
- git-summary-service.ts — Branch/commit info
- project-discovery-service.ts — Find GSD projects
- skill-health-service.ts — Skill availability
- captures-service.ts — Knowledge captures CRUD
- settings-service.ts — Preferences persistence
- export-service.ts — Milestone/slice export
- cleanup-service.ts — Merged branches, stale snapshots
- update-service.ts — Version checks
- undo-service.ts — Revert last completed unit
- steer-service.ts — Course corrections
- inspect-service.ts — Workspace inspection
- recovery-diagnostics-service.ts — Auto-mode failure analysis
- hooks-service.ts — Lifecycle hooks
- visualizer-service.ts — TUI visualization data

---

## Frontend-Backend Communication

### Authentication
- Bearer token generated at server startup (random hex)
- Passed to browser via URL fragment: `#token=<hex>`
- Extracted to sessionStorage (survives refresh)
- All requests: `Authorization: Bearer <token>`
- SSE: `?_token=<hex>` query param

### SSE Streams
- Terminal: `GET /api/terminal/stream?id=<sessionId>`
- Session events: `GET /api/session/events`
- Live state: Polling endpoint for selective refresh

### Request-Response
- `POST /api/session/command` — RPC commands
- GET endpoints — Diagnostics, history, settings
- All responses: `Cache-Control: no-store`

---

## Studio Desktop App (Early Stage)
- Window: 1400x900, min 1100x720, dark background #0a0a0a
- Currently: Status dashboard showing theme/font/tech info
- Architecture ready for IPC bridge (comments indicate future work)
- Separate from web — could share components but doesn't yet

---

## Deployment
### Web Application
- Build: `next build --webpack` → standalone bundle
- Runtime: `node .next/standalone/web/server.js`
- Port: Default 3000

### Studio Desktop
- Build: `electron-vite build`
- Runtime: Electron from dist/

---

## Python Rebuild Implications

### Frontend Options
The web frontend is **framework-agnostic** in terms of backend — it communicates via HTTP/SSE/JSON-RPC. For a Python rebuild:

1. **Keep Next.js frontend, Python backend** — Replace `/src/web/*.ts` services with Python FastAPI/Flask endpoints. The React frontend doesn't care what language the backend is.

2. **Replace with Python-native web framework:**
   - **FastAPI + htmx/React** — Python backend serving React SPA
   - **Django + React** — Full-featured Python backend
   - **Textual Web** — Python TUI-to-web (for terminal-native approach)

3. **Terminal UI replacement:**
   - `textual` (Python) — Rich TUI framework, closest to pi-tui
   - `rich` — Terminal rendering library
   - `prompt_toolkit` — Interactive prompts

### Key APIs to reimplement in Python:
- PTY management (use `ptyprocess` or `pexpect`)
- SSE streaming (use `sse-starlette` with FastAPI)
- Session/state management (use SQLite via `sqlite3` or `sqlalchemy`)
- File browser (use `pathlib` + `watchdog`)
- Git operations (use `pygit2` or `gitpython`)
