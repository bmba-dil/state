# Bundled Resources & Documentation Analysis

## src/resources/ — Bundled Resources (1,095 files)

### A. Agent System Prompts (5 files)
Specialized LLM personas:
- **researcher.md** — Web researcher using Brave Search, synthesizes findings
- **scout.md** — Fast codebase reconnaissance with compressed context for handoff
- **worker.md** — General-purpose isolated-context subagent for delegated tasks
- **typescript-pro.md** — Advanced TypeScript specialist (5.0+, type system, full-stack)
- **javascript-pro.md** — Modern JavaScript specialist (ES2023+, Node.js 20+, async patterns)

### B. Core Workflow Document
**GSD-WORKFLOW.md** (24.7 KB) — Manual bootstrap protocol:
- The hierarchy: Milestone → Slice → Task
- File locations and formats: STATE.md, roadmaps, plans, contexts, research, summaries
- Seven phases: Discuss, Research, Plan, Execute, Verify, Summarize, Advance
- Continue-here protocol for context compaction
- State management and reconciliation
- Git strategy (branch-per-slice with squash merge)
- Summary injection for downstream tasks
- Fresh session checklist

### C. Extensions (25+ major extensions)

#### 1. GSD Core Extension (~250 TypeScript files)
The workflow engine with:
- **auto/** — Auto-mode state machine and orchestration
- **commands/** — Command handlers
- **bootstrap/** — Initialization
- **tools/** — Tool implementations (bash, write, read, edit, decision/summary save, requirement update, milestone ID generation)
- **prompts/** — Phase-specific LLM prompts
- **workflow-templates/** — Pre-built workflows:
  - bugfix, spike, feature, hotfix, refactor, security-audit, dep-upgrade, full-project
- **docs/** — Extension documentation

Key modules:
- `auto.ts` — State machine
- `auto-dispatch.ts` — Dispatch table
- `complexity-classifier.ts` — Unit classification
- `model-router.ts` — Cost-aware model selection
- `state.ts` — State derivation
- `preferences.ts` — Preference loading
- `git-service.ts` — Git operations
- `memory-store.ts` — Cross-session knowledge

#### 2. Browser Tools Extension
40+ Playwright-based tools:
- Navigation, forms, screenshots, PDF export
- Device emulation, visual regression
- Accessibility tree, route mocking
- Semantic actions, batch operations

#### 3. Search the Web Extension
- Brave Search integration
- Tavily search
- Jina page extraction

#### 4. Context7 Extension
- Library/framework documentation lookup

#### 5. Background Shell Extension
- Long-running process management with readiness detection

#### 6. Async Jobs Extension
- Background command execution (async_bash, await_job, cancel_job)

#### 7. Google Search Extension
- Gemini-powered web search

#### 8. Subagent Extension
- Delegated tasks with isolated context windows

#### 9. Mac Tools Extension
- macOS native app automation via Accessibility APIs

#### 10. Voice Extension
- Real-time speech-to-text

#### 11. Slash Commands Extension
- Custom command creation

#### 12. Remote Questions Extension
- Discord, Slack, Telegram integration for headless mode

#### 13. TTSR Extension (Tool-Triggered System Rules)
- Conditional context injection based on tool usage

#### 14. Universal Config Extension
- Discovery of existing AI tool configs (Claude Code, Cursor, Windsurf)

#### 15. MCP Client Extension
- Native MCP server integration via @modelcontextprotocol/sdk

#### 16. AWS Auth Extension
- AWS authentication handling

#### 17. Claude Code CLI Extension
- Integration with Claude Code

### D. Skills (20 skill directories)

| Skill | Purpose |
|-------|---------|
| frontend-design | Web UI production quality |
| debug-like-expert | Complex debugging methodology |
| agent-browser | Browser automation patterns |
| github-workflows | GitHub Actions CI/CD |
| review | Code review diff analysis |
| test | Test generation and execution |
| lint | ESLint, Biome, Prettier linting |
| accessibility | WCAG compliance |
| react-best-practices | React patterns |
| code-optimizer | Performance optimization |
| core-web-vitals | Web performance metrics |
| create-gsd-extension | Extension scaffolding |
| create-skill | Skill authoring |
| create-workflow | Workflow templates |
| userinterface-wiki | UI patterns database |
| web-design-guidelines | Design systems |
| web-quality-audit | QA scripts |
| make-interfaces-feel-better | UX improvement |
| best-practices | General coding best practices |

Each skill contains:
- `SKILL.md` — LLM instructions
- `references/` — Optional reference files
- `templates/` — Workflow templates
- `rules/` — Domain-specific rules
- `scripts/` — Helper scripts

---

## docs-internal/ — Internal Documentation (156 files)

### Top-Level Documents (19 markdown files)
- `README.md` — Documentation index
- `architecture.md` — System design, extension model, state-on-disk, dispatch pipeline
- `agent-knowledge-index.md` — Machine-operational routing table
- `getting-started.md` — Installation, first run, basic usage
- `auto-mode.md` — Autonomous execution engine
- `commands.md` — All commands reference with flags
- `configuration.md` — Preferences, models, git, token profiles
- `custom-models.md` — Ollama, vLLM, LM Studio, proxies
- `token-optimization.md` — Token profiles, compression, adaptive learning
- `dynamic-model-routing.md` — Complexity-based model selection
- `captures-triage.md` — Fire-and-forget thought capture with triage
- `cost-management.md` — Budget ceilings and cost tracking
- `git-strategy.md` — Worktree isolation, branching, merge behavior
- `parallel-orchestration.md` — Multi-milestone parallel execution
- `skills.md` — Skill discovery, custom skills, health dashboard
- `migration.md` — v1 to v2 migration
- `troubleshooting.md` — Common issues and recovery
- `visualizer.md` — TUI overlay for progress and metrics
- `web-interface.md` — Browser-based dashboard

### Architecture Decision Records
- `ADR-001-branchless-worktree-architecture.md` (16.4 KB) — v2.14 git architecture
- `ADR-003-pipeline-simplification.md` (51 KB) — v2.30 research merged into planning
- `PRD-branchless-worktree-architecture.md` (18.5 KB)
- `FILE-SYSTEM-MAP.md` (70.8 KB)

### Subdirectory Sections

#### what-is-pi/ (20 documents)
Core Pi SDK concepts:
- What Pi is, design philosophy, four modes of operation
- Architecture, agent loop, tools, sessions, compaction
- Customization stack, providers/models, interactive TUI
- Message queue, context files, SDK/RPC
- Pi packages, building branded apps

#### extending-pi/ (25 documents)
Extension development:
- Extension basics, architecture, getting started
- Discovery, structure, lifecycle, events, context, API
- Custom tools, commands, UI components, state management
- Custom rendering, system prompt modification
- Compaction/session control, model/provider management
- Remote execution, packaging, mode behavior
- Error handling, rules/gotchas, file reference, examples

#### context-and-hooks/ (10 documents)
- Context pipeline, hook reference, injection patterns
- Message types and LLM visibility
- Inter-extension communication
- System prompt anatomy

#### pi-ui-tui/ (26 documents)
- UI architecture, component interface, entry points
- Built-in dialogs, persistent UI elements
- Custom components, building blocks
- Quick reference

#### building-coding-agents/ (28 documents)
Research notes on agent design:
- Work decomposition, state machine context
- Optimal storage, parallelization strategy
- Maximizing agent autonomy
- System prompt: LLM vs deterministic
- Speed optimization, top 10 pitfalls
- God-tier context engineering
- Handling ambiguity and contradiction

---

## mintlify-docs/ — Public Documentation (23 files)

### Configuration
- `docs.json` — Mintlify site config (theme: mint, navigation)

### Main Pages
- `introduction.mdx` — What GSD does
- `getting-started.mdx` — Install, first launch, setup

### Guide Documentation (17 files in `/guides/`)
- auto-mode, commands, git-strategy
- configuration, custom-models, token-optimization
- dynamic-model-routing, cost-management
- skills, captures-triage, parallel-orchestration
- remote-questions, visualizer, web-interface
- working-in-teams, troubleshooting, migration

---

## Key Configuration & State Files (On-Disk)

| File | Purpose |
|------|---------|
| `~/.gsd/agent/auth.json` | LLM provider keys, tool API keys |
| `~/.gsd/preferences.md` | Model selection, budgets, timeouts, skill rules |
| `.gsd/preferences.md` | Project-specific overrides |
| `.mcp.json` / `.gsd/mcp.json` | External MCP server configuration |
| `.gsd/STATE.md` | Dashboard (active milestone/slice/task, next action) |
| `.gsd/DECISIONS.md` | Decision log |
| `.gsd/KNOWLEDGE.md` | Knowledge base |
| `.gsd/RUNTIME.md` | Runtime state |
| `.gsd/REQUIREMENTS.md` | Requirements tracking |

---

## Python Rebuild Implications
- **Workflow document** (GSD-WORKFLOW.md) is pure markdown — directly reusable
- **Agent prompts** are pure markdown — directly reusable
- **Skills** are pure markdown with YAML frontmatter — directly reusable
- **Extension system** needs to be rebuilt as a Python plugin architecture
- **Browser tools** could use `playwright` Python package (same underlying engine)
- **State files** (.gsd/ directory) are markdown/JSON — directly compatible
- **Documentation** is infrastructure-agnostic — reusable as-is
