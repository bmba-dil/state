# Architecture Discussion: Pros, Cons & Tradeoffs

## 1. The Big Picture: Monolith vs Modular

The original GSD is a **5-package monorepo** (native, pi-agent-core, pi-ai, pi-tui, pi-coding-agent). That's largely because Node.js/TypeScript benefits from package boundaries for build isolation and API contracts.

**Python doesn't need that.** Python's module system gives you clean separation without the overhead of separate packages.

| Approach | Pros | Cons |
|----------|------|------|
| **Single package with submodules** (`gsd.core`, `gsd.ai`, `gsd.tools`) | Simple packaging, one `pyproject.toml`, easy to install, `pip install gsd` just works | Can become a big ball of mud if you're not disciplined with module boundaries |
| **Multiple packages** (poetry workspaces / hatch monorepo) | Enforced API boundaries, independent versioning, can publish `gsd-core` separately | Packaging complexity, dependency resolution headaches, CI overhead |

**Recommendation:** Single package. Python's `__init__.py` exports give you clean APIs without the ceremony. The original only split into packages because of vendoring from pi-mono — that constraint doesn't exist in your rebuild.

---

## 2. Async Model: This Is Actually the First Decision

GSD does a LOT of concurrent work — streaming LLM responses, running background shells, watching files, SSE streams, PTY management. The original uses Node.js's event loop natively.

| Approach | Pros | Cons |
|----------|------|------|
| **Full async (`asyncio`)** | Natural fit for streaming, concurrent tool execution, SSE, WebSockets. FastAPI is async-native. Matches Node.js's concurrency model | Async infects everything (async/await everywhere). Some libraries don't support async. Debugging is harder |
| **Sync with threading** | Simpler code, easier debugging, more library compatibility | Doesn't scale as cleanly for streaming. Thread safety concerns. Harder to do concurrent tool execution |
| **Hybrid** (async web layer, sync core) | Best of both — async where needed, simple where not | Two mental models. Bridging async↔sync requires `asyncio.to_thread()` / `loop.run_until_complete()` |

**Recommendation:** Go async. The streaming LLM responses alone justify it. `litellm`, `anthropic`, `openai`, `fastapi`, `textual` — all your key dependencies support async natively. You'll fight the architecture less.

---

## 3. LLM Provider Layer

This is the heart of the system. The original pi-ai has 50 files supporting 29+ providers with unified streaming, thinking levels, caching, OAuth, and retry logic.

| Approach | Pros | Cons |
|----------|------|------|
| **`litellm`** | 100+ providers out of the box. Streaming, caching, fallbacks, load balancing, cost tracking all built-in. Active community, 15k+ stars | Another dependency to maintain. Sometimes lags behind provider SDK updates. Opinionated about response format. Some edge cases with exotic providers |
| **Custom wrapper over SDKs** | Full control. Can match original pi-ai behavior exactly. No middleman | Massive effort (50+ files in original). Must maintain per-provider code. Every SDK update is your problem |
| **`aisuite`** | Lightweight, simple | Too simple — no streaming, no caching, no fallbacks |
| **`pydantic-ai`** | Clean abstractions, Pydantic-native | Newer, less battle-tested at scale. May not cover all 29 providers |

**Recommendation:** `litellm` for the provider layer, with thin custom wrappers for GSD-specific features (thinking levels, token profiles, dynamic routing). litellm handles the painful parts (SDK differences, streaming normalization, retry logic) while you focus on the GSD-specific intelligence (model routing, budget management, cost tracking).

**Risk with litellm:** If you need very fine-grained control over prompt caching (`CacheRetention: "short" | "long"`) or Anthropic-specific extended thinking, you may need to bypass litellm for those calls and go direct to the `anthropic` SDK. That's fine — use litellm as the default path and direct SDK for special cases.

---

## 4. Agent Loop

The original pi-agent-core is surprisingly small (6 files, ~1,500 lines). It's essentially:
1. Send messages to LLM
2. If LLM wants to use tools, execute them
3. Feed results back
4. Repeat until done or stopped

| Approach | Pros | Cons |
|----------|------|------|
| **Custom (recommended)** | Simple, ~300-500 lines Python. Full control over steering, follow-up messages, tool execution mode. No framework lock-in | You maintain it. But it's small |
| **`pydantic-ai`** | Clean tool definitions via decorators, Pydantic validation of tool inputs. Good DX | Less control over the loop internals. May not support GSD's steering/follow-up message injection cleanly |
| **`langchain`** | Huge ecosystem, lots of pre-built tools | Massively over-engineered for this. Abstraction layers on abstraction layers. Performance overhead. The community is moving away from it |
| **`smolagents`** (HuggingFace) | Lightweight, well-designed | Newer, HF-centric, may not support all your providers |

**Recommendation:** Custom. The agent loop is the core IP of your system — you don't want a framework between you and the LLM. The original is only ~1,500 lines TypeScript which translates to maybe 400 lines Python. The complexity isn't in the loop itself, it's in the GSD workflow engine on top of it.

---

## 5. Terminal UI

This is where it gets interesting. The original pi-tui is a custom TUI framework (31 files) with:
- Component-based rendering
- Kitty/iTerm2 image protocol support
- Emacs keybindings
- Autocomplete, undo/redo
- Overlay system

| Approach | Pros | Cons |
|----------|------|------|
| **`textual`** | Full TUI framework with CSS styling, 50+ built-in widgets, hot-reload, web deployment via `textual-web`. Most active Python TUI project. Rich ecosystem | Learning curve for CSS-based layout. Opinionated about architecture. Image support is limited vs Kitty protocol |
| **`rich` + `prompt_toolkit`** | `rich` for output rendering (markdown, syntax, tables). `prompt_toolkit` for input (completion, history, keybindings). Lighter weight | Two libraries to integrate. No built-in component model. You'd build your own layout system |
| **`urwid`** | Battle-tested, very flexible, low-level | Old API design, steep learning curve, smaller community |
| **`blessed`/`curses`** | Maximum control | Maximum pain. Don't |

**Recommendation:** `textual`. It's the clear winner for Python TUI in 2026. The CSS styling is actually a huge advantage — the original pi-tui essentially reinvents CSS layout primitives manually. Textual gives you that for free. The web deployment option (`textual-web`) is a bonus that could replace the entire Next.js frontend for simpler deployments.

**One concern:** Textual's image rendering is less sophisticated than the original's Kitty Graphics Protocol support. If inline images are critical, you may need to add custom Kitty protocol escape sequences. Not a blocker, but worth noting.

---

## 6. Web Frontend

This is the biggest decision because it has the most options and the most effort variance.

| Approach | Pros | Cons |
|----------|------|------|
| **A: Keep React/Next.js, Python backend** | Minimal frontend work. Existing UI is polished (40 routes, Radix UI, xterm.js). Just swap the `/src/web/*.ts` services for FastAPI | Two languages in one project. Node.js still required for frontend build. Deployment complexity |
| **B: FastAPI + htmx** | Single language. Server-rendered, fast. htmx handles dynamic updates. Very simple architecture | Less interactive than React. No component reuse. Rebuilding 40 routes + complex UI (chat, terminal, file browser) in htmx is painful |
| **C: FastAPI + React SPA (decoupled)** | React frontend is standalone. Python API is clean REST/SSE. Can develop independently | Still two languages. But clearly separated — React app is a static build |
| **D: Textual Web** | One codebase for TUI + web. Pure Python. Simplest architecture | Experimental. Less polished than React. No custom styling (it's your terminal, in a browser). Limited interactive widgets |
| **E: Django + React** | Django admin gives you free data management UI. Batteries included (auth, ORM, sessions) | Django is heavyweight for this. ORM is overkill when state lives on filesystem |

**Analysis by priority:**

- **If you want to ship fast:** Option A (keep React, Python backend). The existing frontend is 20,000 lines of polished React. Rewriting it is months of work for no functional gain.

- **If you want pure Python simplicity:** Option D (Textual Web) for MVP, graduate to Option C later if you need more UI sophistication.

- **If you want the best long-term architecture:** Option C (FastAPI + React SPA). Clean separation, each part can evolve independently, and you can hire frontend and backend specialists separately.

---

## 7. State & Data Persistence

The original uses:
- JSONL files for sessions
- Markdown files for state (STATE.md, DECISIONS.md, etc.)
- SQLite via sql.js for structured data
- JSON files for config/registry

| Approach | Pros | Cons |
|----------|------|------|
| **Keep filesystem-first (markdown + JSONL + SQLite)** | Compatible with original state format. Human-readable. Git-friendly. Simple | File locking complexity. No query language for markdown. Performance at scale |
| **SQLite for everything** | Single file, ACID, fast, queryable. Python's `sqlite3` is stdlib | Loses human-readable state files. Git diffs become meaningless |
| **Hybrid (recommended)** | Markdown for human-facing state (STATE.md, DECISIONS.md). SQLite for structured data (sessions, metrics, events). JSON for config | Two storage layers. But matches the original's design |

**Recommendation:** Hybrid, matching the original. The markdown-on-disk state files are a core part of GSD's design philosophy — they're meant to be human-readable and git-tracked. Don't lose that. Use SQLite for the stuff that benefits from queries (session history, metrics, event logs).

---

## 8. Native Performance

The Rust N-API layer provides 18 high-performance modules. You need a strategy for each.

| Approach | Pros | Cons |
|----------|------|------|
| **Subprocess to CLI tools** (`rg`, `fd`, `git`) | Simplest. These tools are fast. No compilation needed | External dependency on installed tools. Parsing stdout. Process spawn overhead |
| **Python bindings** (`pygit2`, `py-tree-sitter`, `Pillow`) | Native speed without subprocess overhead. Pythonic API | Some bindings are less maintained. `pygit2` can be tricky to install |
| **PyO3/Rust bindings** (keep existing Rust, expose via PyO3) | Maximum performance. Reuse existing Rust code | Build complexity (need Rust toolchain). Packaging for multiple platforms. Significant effort |
| **Pure Python** | Zero native dependencies. Easy install. Works everywhere | Slower for large codebases. `re` module is slower than ripgrep. `difflib` is slower than `similar` |

**Recommendation:** Tiered approach:

1. **Start with subprocess** for `rg` (grep), `fd` (find), and `git` — they're fast enough and universally available
2. **Use Python libraries** for everything else: `Pillow` (image), `pygments` (highlight), `pyperclip` (clipboard), `psutil` (process), `tree-sitter` (AST), `difflib` (diff)
3. **Consider PyO3** later ONLY if profiling shows bottlenecks — premature optimization is the enemy here

The original went Rust because Node.js is fundamentally single-threaded and needed native code for CPU-bound work. Python with `asyncio` + subprocess for CLI tools doesn't have that same bottleneck.

---

## 9. Extension System

The original has a sophisticated extension system with hooks, commands, tools, UI components, and a registry.

| Approach | Pros | Cons |
|----------|------|------|
| **`pluggy`** | Battle-tested (powers pytest). Hook-based, supports hook ordering, early-return. Well-documented | No built-in tool/command/UI registration. You'd build that on top |
| **`importlib.metadata` entry points** | Standard Python mechanism. pip-installable plugins | Requires package installation for each plugin. Less dynamic |
| **Custom (directory-based discovery)** | Matches original's approach. Scan directories, import modules, call register functions | You maintain it. But it's not complex |

**Recommendation:** `pluggy` for the hook system + custom directory scanning for discovery. The original's extension system is really two things: (1) lifecycle hooks (before/after tool calls, session start, etc.) — that's exactly what pluggy does well — and (2) dynamic discovery of extension files — that's simple `importlib.import_module()` over a directory scan.

---

## 10. The Elephant in the Room: What NOT to Rebuild

Some parts of the original are there because of TypeScript/Node.js limitations, not because they're inherently needed:

| Original Component | Why It Exists | Python Equivalent |
|-------------------|---------------|-------------------|
| loader.ts bootstrap | Node.js env setup, symlinks, version checks | Python's `__main__.py` + `setuptools` handles this |
| jiti (runtime TS loading) | TypeScript can't import .ts at runtime | Python imports .py natively — just `import` |
| N-API bindings wrapper | Node.js can't call Rust directly | `subprocess.run("rg ...")` or `ctypes`/PyO3 |
| node_modules symlink dance | npm workspace linking | `pip install -e .` just works |
| pi-migration.ts | Migrate from Pi's auth format | Not needed — fresh start |
| bundled-extension-paths.ts | Serialize extension paths across processes | Python `sys.path` + `PYTHONPATH` |
| worktree-name-gen.ts | Random name generation | `faker` or 3 lines of `random.choice()` |

**Don't rebuild these.** They're Node.js plumbing that Python doesn't need.

---

## Recommended Stack Summary

```
CLI:          typer + rich
Agent Loop:   Custom (~400 lines)
LLM Layer:    litellm + direct anthropic/openai for edge cases
TUI:          textual
Web Backend:  FastAPI + uvicorn
Web Frontend: Keep existing React (Phase 1) or Textual Web (simpler)
State:        Markdown files + SQLite (hybrid)
Git:          subprocess git (start) → pygit2 (later)
Search:       subprocess rg/fd
Extensions:   pluggy + directory scanning
Types:        Pydantic v2 (all data models)
Testing:      pytest + pytest-asyncio
Async:        Full asyncio
Package:      Single package, submodules
```
