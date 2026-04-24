# Python Rebuild Mapping & Strategy Guide

## System Overview for Rebuild

GSD is a **multi-modal AI coding agent orchestrator** with these major subsystems:

| Subsystem | Current Tech | LOC (approx) | Complexity |
|-----------|-------------|--------------|------------|
| CLI Entry & Bootstrap | TypeScript/Node.js | ~3,000 | Medium |
| Agent Loop (pi-agent-core) | TypeScript | ~1,500 | High |
| LLM Provider Layer (pi-ai) | TypeScript, 6 SDKs | ~8,000 | High |
| Terminal UI (pi-tui) | TypeScript | ~5,000 | Medium |
| Coding Agent (pi-coding-agent) | TypeScript | ~30,000 | Very High |
| Native Performance (Rust/N-API) | Rust | ~10,000 | High |
| GSD Workflow Extension | TypeScript | ~50,000+ | Very High |
| Web Frontend (Next.js) | React/TypeScript | ~20,000 | High |
| Studio Desktop (Electron) | React/TypeScript | ~500 | Low |
| VS Code Extension | TypeScript | ~1,600 | Medium |
| Test Suite | TypeScript | ~98,000 | — |
| Scripts & CI | Bash/JS | ~5,000 | Medium |
| **TOTAL** | | **~230,000** | |

---

## Component-by-Component Python Mapping

### 1. CLI Entry & Bootstrap → `click` or `typer`

**Current:** Custom arg parsing in cli.ts + loader.ts bootstrap
**Python:**
- `typer` (built on click) — Modern CLI framework with type hints
- `click` — More established, more control
- Environment setup → Python `os.environ` + `pathlib`
- Module loading → Python `importlib`

### 2. Agent Loop → Custom or `pydantic-ai`

**Current:** pi-agent-core — 6 files, agent loop with tool execution
**Python Options:**
- **Custom implementation** (recommended) — Direct port, ~500 lines Python
- `pydantic-ai` — Agent framework with tool execution
- `langchain` — Over-engineered for this use case
- `magentic` — Lightweight LLM function calling

### 3. LLM Provider Layer → `litellm` or custom

**Current:** pi-ai — 50 files, 29+ providers, unified streaming
**Python Options:**
- **`litellm`** (recommended) — Unified API for 100+ providers, streaming, caching, fallbacks
- **Custom** — Direct SDK usage (anthropic, openai, google-genai, boto3, mistralai)
- `aisuite` — Lightweight multi-provider abstraction

### 4. Terminal UI → `textual` or `rich`

**Current:** pi-tui — 31 files, component-based TUI with image support
**Python Options:**
- **`textual`** (recommended) — Full TUI framework, CSS styling, component-based, web deployment
- `rich` — Terminal rendering (no interactivity, use for output only)
- `prompt_toolkit` — Interactive prompts, completion, history

### 5. Core Tools → Python stdlib + libraries

**Current:** 7 tools in pi-coding-agent

| Tool | Python Implementation |
|------|----------------------|
| **read** | `pathlib.Path.read_text()` + line slicing |
| **write** | `pathlib.Path.write_text()` + safety checks |
| **edit** | `difflib` + custom diff application |
| **bash** | `subprocess.run()` or `asyncio.create_subprocess_exec()` |
| **grep** | `ripgrepy` or subprocess `rg` or `re` module |
| **find** | `pathlib.glob()` or subprocess `fd` or `os.walk()` |
| **ls** | `os.listdir()` + `os.stat()` |

### 6. Native Performance Layer → Python libraries

| Rust Module | Python Equivalent | Notes |
|-------------|------------------|-------|
| grep (ripgrep) | `ripgrepy` or subprocess `rg` | Or pure Python `re` |
| glob | `pathlib.glob()` + `gitignore_parser` | |
| git | `pygit2` (libgit2 bindings) | Or `gitpython` |
| ast | `py-tree-sitter` | Same tree-sitter engine |
| highlight | `pygments` or `rich.syntax` | |
| image | `Pillow` (PIL) | |
| clipboard | `pyperclip` | |
| diff | `difflib` | stdlib |
| text | `rich` + `wcwidth` | ANSI-aware |
| json_parse | `ijson` (streaming) or `orjson` (fast) | |
| xxhash | `xxhash` | |
| html | `markdownify` or `html2text` | |
| process | `psutil` | |
| fd | `pathlib` or subprocess `fd` | |

### 7. Session Management → SQLite + JSON

**Current:** JSONL files in ~/.gsd/sessions/, SQLite via sql.js
**Python:**
- `sqlite3` (stdlib) for structured data
- `json` + `pathlib` for JSONL session files
- `aiosqlite` for async SQLite

### 8. Extension System → Python plugin architecture

**Current:** jiti-based runtime loading, hooks, commands, tools
**Python Options:**
- `pluggy` (used by pytest) — Hook-based plugin system
- `importlib.metadata` entry points — Standard Python plugin discovery
- `stevedore` — Plugin management library
- Custom with `importlib.import_module()` + directory scanning

### 9. Compaction System → Custom

**Current:** Token estimation, branch summaries, context pruning
**Python:**
- `tiktoken` — OpenAI token counting (works for most models)
- `anthropic` SDK has built-in token counting
- Custom summarization logic

### 10. Web Frontend → Keep React or replace

**Option A: Keep Next.js frontend, Python backend (recommended for MVP)**
- Replace `/src/web/*.ts` services with FastAPI endpoints
- Same React UI, same API contracts, different backend language
- Minimal frontend changes

**Option B: Full Python web stack**
- `FastAPI` + `Jinja2` templates + `htmx` — Server-rendered
- `FastAPI` + React SPA — Decoupled frontend
- `Textual Web` — Python TUI served as web app (experimental)
- `Django` + React — Full-featured

**Option C: Textual-first (terminal native)**
- `textual` for TUI
- `textual-web` for browser access
- Simplest architecture, lowest maintenance

### 11. MCP Server → `mcp` Python package

**Current:** @modelcontextprotocol/sdk
**Python:** Official `mcp` package (maintained by Anthropic)

### 12. VS Code Extension → Keep TypeScript

VS Code extensions must be JavaScript/TypeScript. For Python rebuild:
- Keep the extension as-is
- Change the spawn command from `gsd --mode rpc` to `python -m gsd --mode rpc`
- Same NDJSON RPC protocol (language-agnostic)

---

## Recommended Python Architecture

```
gsd/
├── pyproject.toml           # Project config (poetry/hatch)
├── src/
│   └── gsd/
│       ├── __main__.py      # CLI entry point
│       ├── cli.py           # typer CLI definition
│       ├── core/
│       │   ├── agent.py         # Agent loop
│       │   ├── session.py       # Session management
│       │   ├── compaction.py    # Context compaction
│       │   └── settings.py      # Configuration
│       ├── ai/
│       │   ├── providers.py     # litellm wrapper
│       │   ├── models.py        # Model registry
│       │   └── streaming.py     # Stream handling
│       ├── tools/
│       │   ├── bash.py          # Shell execution
│       │   ├── read.py          # File reading
│       │   ├── write.py         # File writing
│       │   ├── edit.py          # File editing
│       │   ├── grep.py          # Search
│       │   ├── find.py          # File finding
│       │   └── ls.py            # Directory listing
│       ├── extensions/
│       │   ├── loader.py        # Extension discovery
│       │   ├── registry.py      # Enable/disable
│       │   └── hooks.py         # Hook system (pluggy)
│       ├── workflow/
│       │   ├── state.py         # GSD state machine
│       │   ├── dispatch.py      # Auto-dispatch
│       │   ├── phases.py        # Phase management
│       │   ├── doctor.py        # Diagnostics
│       │   └── events.py        # Workflow events
│       ├── tui/
│       │   ├── app.py           # Textual app
│       │   ├── components/      # UI components
│       │   └── themes/          # Theme definitions
│       ├── web/
│       │   ├── server.py        # FastAPI app
│       │   ├── routes/          # API endpoints
│       │   ├── services/        # Backend services
│       │   └── bridge.py        # Agent bridge
│       ├── git/
│       │   ├── worktree.py      # Worktree management
│       │   └── operations.py    # Git operations (pygit2)
│       ├── headless/
│       │   ├── runner.py        # Headless mode
│       │   └── rpc.py           # RPC server
│       ├── mcp/
│       │   └── server.py        # MCP server
│       └── utils/
│           ├── paths.py         # App paths
│           ├── tokens.py        # Token counting
│           └── config.py        # Config loading
├── resources/
│   ├── agents/              # Agent prompts (markdown, reuse as-is)
│   ├── extensions/          # Extension configs
│   ├── skills/              # Skill definitions (markdown, reuse as-is)
│   └── GSD-WORKFLOW.md      # Workflow doc (reuse as-is)
├── tests/
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_tools/
│   └── test_workflow/
└── vscode-extension/        # Keep as TypeScript
```

---

## Key Python Dependencies

```toml
[project]
dependencies = [
    # CLI
    "typer>=0.12",
    "rich>=13.0",

    # LLM
    "litellm>=1.40",
    "anthropic>=0.30",
    "openai>=1.30",

    # TUI
    "textual>=0.60",

    # Web
    "fastapi>=0.110",
    "uvicorn>=0.29",
    "sse-starlette>=2.0",

    # Git
    "pygit2>=1.14",

    # Data
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "orjson>=3.10",

    # Tools
    "psutil>=5.9",
    "watchdog>=4.0",
    "tiktoken>=0.7",

    # MCP
    "mcp>=1.0",

    # Browser
    "playwright>=1.44",

    # Extensions
    "pluggy>=1.5",
]
```

---

## Reusable Assets (No Rewrite Needed)

These are language-agnostic and can be copied directly:

1. **Agent system prompts** — All markdown files in resources/agents/
2. **GSD-WORKFLOW.md** — Core workflow document
3. **Skill definitions** — All SKILL.md files and references
4. **Workflow templates** — bugfix, feature, refactor, etc.
5. **State file formats** — STATE.md, DECISIONS.md, KNOWLEDGE.md (all markdown)
6. **Documentation** — docs-internal/, mintlify-docs/
7. **VS Code extension** — Stays TypeScript, just change spawn command
8. **CI scripts** — Bash scripts (secret-scan, base64-scan, etc.)
9. **Docker config** — Adapt Dockerfile for Python base image
10. **GitHub workflows** — Adapt for Python build/test

---

## Build Priority Order

### Phase 1: Core (MVP)
1. CLI entry point (typer)
2. Agent loop (custom)
3. LLM provider integration (litellm)
4. Core tools (bash, read, write, edit)
5. Session management (JSONL + sqlite3)
6. Basic TUI (textual)

### Phase 2: Workflow
7. GSD state machine
8. Auto-dispatch system
9. Preferences and configuration
10. Doctor diagnostics
11. Git worktree management

### Phase 3: Extensions
12. Extension loader (pluggy)
13. Browser tools (playwright)
14. Web search integration
15. MCP server
16. Headless/RPC mode

### Phase 4: Web & Polish
17. Web backend (FastAPI)
18. Web frontend (keep React or rebuild)
19. VS Code extension adaptation
20. Skill system
21. Remote questions (Slack/Discord/Telegram)

---

## Estimated Effort

| Phase | Python LOC (est) | Original TS LOC | Ratio |
|-------|-----------------|-----------------|-------|
| Phase 1: Core | ~5,000 | ~40,000 | 1:8 (Python is more concise) |
| Phase 2: Workflow | ~8,000 | ~50,000 | 1:6 |
| Phase 3: Extensions | ~4,000 | ~30,000 | 1:7 |
| Phase 4: Web | ~6,000 | ~25,000 | 1:4 |
| **Total** | **~23,000** | **~145,000** | **1:6** |

Python's conciseness, stdlib richness, and library ecosystem (litellm, textual, fastapi, pydantic) mean significantly less code to write.
