# GSD Codebase Analysis — Master Index

## Project Identity
- **Name:** GSD (Get Shit Done) v2.48.0
- **Original Language:** TypeScript/Node.js + Rust (N-API)
- **Total LOC:** ~230,000 (source) + ~98,000 (tests)
- **Architecture:** Monorepo with 5 workspace packages
- **License:** MIT
- **Purpose:** AI-powered autonomous coding agent orchestrator

---

## Analysis Documents

### Architecture & Source Code
| # | Document | Contents |
|---|----------|----------|
| 01 | [Core Architecture](01-core-architecture.md) | CLI entry, bootstrap, resource management, web mode, headless, worktrees, auth, paths, tools, updates, UI/branding, MCP server |
| 02 | [Native Rust Engine](02-native-rust-engine.md) | 18 Rust N-API modules (grep, git, ast, image, clipboard, highlight, diff, parser, etc.), build process, platform support |
| 03 | [VS Code Extension](03-vscode-extension.md) | 15 commands, RPC client, sidebar webview, @gsd chat participant, NDJSON protocol |
| 04 | [Resources & Docs](04-resources-and-docs.md) | 1,095 bundled resources: 5 agents, 25+ extensions, 20 skills, workflow doc, 156 internal docs, public docs |
| 05 | [Test Infrastructure](05-test-infrastructure.md) | 356+ test files, node:test framework, fixture recording, 14 test commands, coverage config |
| 06 | [Packages/Monorepo](06-packages-monorepo.md) | 5 packages: native, pi-agent-core, pi-ai (29+ providers), pi-coding-agent (182 files), pi-tui |
| 07 | [Web & Studio Frontend](07-web-and-studio-frontend.md) | Next.js 16.1.6, 40 API routes, React 19, Radix UI, xterm.js, state management, 9-step onboarding |
| 08 | [Project Config & CI](08-project-config-and-ci.md) | 133 deps, 50+ scripts, 6 GitHub workflows, Docker, security scanning, release pipeline |
| 09 | [Types & API Contracts](09-types-and-api-contracts.md) | 1,279 TS files, 162+ interfaces, 40+ API routes, GSD state types, 79 doctor codes, hook system |

### Rebuild Strategy
| # | Document | Contents |
|---|----------|----------|
| 10 | [Python Rebuild Mapping](10-python-rebuild-mapping.md) | Component-by-component Python equivalents, recommended architecture, dependencies, build priority, effort estimates |

---

## Quick Reference: System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                         │
├──────────┬──────────┬───────────┬──────────┬──────────────────┤
│ CLI/TUI  │ Web UI   │ Headless  │ VS Code  │ MCP Server      │
│ (textual)│(Next.js) │ (RPC)     │Extension │(stdin/stdout)    │
└────┬─────┴────┬─────┴─────┬────┴────┬─────┴────────┬────────┘
     │          │           │         │              │
     └──────────┴───────────┴────┬────┴──────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────┐
│                    AGENT SESSION (pi-coding-agent)              │
│  Session Management │ Compaction │ Extension System │ Skills   │
├────────────────────────────────────────────────────────────────┤
│                    AGENT LOOP (pi-agent-core)                  │
│  Message Queue │ Tool Execution │ Steering │ Follow-up        │
├────────────────────────────────────────────────────────────────┤
│                    LLM PROVIDERS (pi-ai)                       │
│  Anthropic │ OpenAI │ Google │ Bedrock │ Mistral │ 24+ more   │
├────────────────────────────────────────────────────────────────┤
│                    CORE TOOLS                                  │
│  bash │ read │ write │ edit │ grep │ find │ ls                │
├────────────────────────────────────────────────────────────────┤
│                    GSD WORKFLOW ENGINE (extension)              │
│  State Machine │ Auto-Dispatch │ Doctor │ Worktrees │ Hooks   │
│  Phases: Discuss→Research→Plan→Execute→Verify→Summarize→Advance│
├────────────────────────────────────────────────────────────────┤
│                    NATIVE PERFORMANCE (Rust/N-API)             │
│  ripgrep │ tree-sitter │ libgit2 │ syntect │ image │ etc.    │
└────────────────────────────────────────────────────────────────┘
```

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Source files | 1,279 TypeScript + Rust |
| Test files | 356+ |
| Total LOC (source) | ~230,000 |
| Total LOC (tests) | ~98,000 |
| npm dependencies | 133 production + 6 optional |
| LLM providers supported | 29+ |
| Extensions bundled | 25+ |
| Skills bundled | 20 |
| Agent prompts | 5 |
| API routes (web) | 40 |
| VS Code commands | 15 |
| Doctor issue codes | 79 |
| Workflow phases | 15 |
| Unit types | 11 |
| Preference keys | 40+ |
| Native Rust modules | 18 |
| Platforms supported | 5 (macOS ARM/x64, Linux x64/ARM, Windows) |
| CI workflows | 6 |
| npm scripts | 50+ |
| Workspace packages | 5 |
| Estimated Python LOC | ~23,000 (6:1 ratio) |
