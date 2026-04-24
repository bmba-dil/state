# Packages / Monorepo Analysis

## Overview
**Type:** TypeScript/Node.js monorepo with npm workspaces
**Packages:** 5 sub-packages under `packages/`
**Total Files:** 341 (including tests, configs)
**Total TypeScript Source Files:** 301

## Dependency Graph
```
┌─────────────────────────────────────────────┐
│      @gsd/pi-coding-agent (APPLICATION)     │
│  Main entry point, CLI, tools, sessions     │
└──┬──────────┬──────────────┬────────────────┘
   │          │              │
   └──────────┼──────────────┴─── depends on
              │
      ┌───────┴───────┬──────────┬──────────────┐
      │               │          │              │
   ┌──▼─────────┐ ┌──▼──┐ ┌─────▼───┐ ┌────────▼──┐
   │ pi-agent   │ │pi-ai│ │ pi-tui  │ │  native   │
   │  -core     │ │     │ │         │ │(Rust/NAPI)│
   └────────────┘ └─────┘ └─────────┘ └───────────┘
```

## Build Order
```bash
npm run build:native-pkg       # @gsd/native (N-API compilation)
npm run build:pi-tui           # @gsd/pi-tui
npm run build:pi-ai            # @gsd/pi-ai
npm run build:pi-agent-core    # @gsd/pi-agent-core
npm run build:pi-coding-agent  # @gsd/pi-coding-agent (all above)
```

---

## Package 1: @gsd/native (v0.1.0)

**Purpose:** High-performance Rust N-API native bindings
**Location:** `/packages/native/`
**Source Files:** 32 TypeScript files + N-API bindings

### 16 Sub-Modules

| Module | Purpose | Key Exports |
|--------|---------|------------|
| **grep** | Ripgrep-backed regex search | `searchContent()`, `grep()` |
| **glob** | Gitignore-respecting file discovery | `glob()`, `invalidateFsScanCache()` |
| **clipboard** | Cross-platform clipboard | `copyToClipboard()`, `readTextFromClipboard()` |
| **ps** | Process tree management | `killTree()`, `listDescendants()` |
| **highlight** | Syntect syntax highlighting | `highlightCode()`, `supportsLanguage()` |
| **html** | HTML to Markdown | `htmlToMarkdown()` |
| **text** | ANSI-aware text measurement | `truncateToWidth()`, `visibleWidth()` |
| **fd** | Fuzzy file path discovery | `fuzzyFind()` |
| **image** | Decode/encode/resize images | `parseImage()` |
| **ast** | AST-based code transformation | `astGrep()`, `astEdit()` |
| **diff** | Text diffing and fuzzy matching | `generateDiff()`, `fuzzyFindText()` |
| **xxhash** | Fast hashing | `xxHash32()` |
| **ttsr** | Text-to-Speech Rules engine | `ttsrCompileRules()`, `ttsrCheckBuffer()` |
| **json-parse** | Streaming JSON parsing | `parseJson()`, `parseStreamingJson()` |
| **stream-process** | Stream chunk processing | `processStreamChunk()`, `stripAnsiNative()` |
| **truncate** | Byte-aware text truncation | `truncateTail()`, `truncateHead()` |
| **gsd-parser** | GSD frontmatter/roadmap parsing | `parseFrontmatter()`, `batchParseGsdFiles()` |

### Loading Strategy
Adaptive with graceful fallback:
1. Platform-specific npm dependency (`@gsd-build/engine-{platform}`)
2. Local release build (`native/addon/gsd_engine.{platform}.node`)
3. Local debug build (`native/addon/gsd_engine.dev.node`)
4. Proxy that throws on unsupported platforms (not at import time)

### Dependencies: None (zero)

---

## Package 2: @gsd/pi-agent-core (v0.57.1)

**Purpose:** General-purpose agent loop abstraction (vendored from pi-mono)
**Location:** `/packages/pi-agent-core/`
**Source Files:** 6 TypeScript files

### Architecture
- **agent.ts** — Agent class wrapping the loop
- **agent-loop.ts** — Core loop: context management, tool execution, steering
- **types.ts** — Core interfaces (AgentMessage, AgentState, AgentTool, AgentLoopConfig)
- **proxy.ts** — Proxy/delegation utilities
- **index.ts** — Re-exports

### Key Types
```typescript
interface AgentMessage {
  role: 'user' | 'assistant' | 'toolResult' | 'custom' | 'notification'
  content: Content[]
}

interface AgentLoopConfig {
  model: Model
  convertToLlm: (messages: AgentMessage[]) => LlmMessage[]
  transformContext?: (messages) => messages
  toolExecutionMode: "sequential" | "parallel"
}

interface AgentTool {
  name: string
  description: string
  inputSchema: JSONSchema
  execute: (input) => Promise<ToolResult>
}
```

### Dependencies
- `@gsd/pi-ai` — LLM streaming layer
- `@sinclair/typebox` — JSON Schema generation

---

## Package 3: @gsd/pi-ai (v0.57.1)

**Purpose:** Unified LLM provider API (vendored from pi-mono)
**Location:** `/packages/pi-ai/`
**Source Files:** 50 TypeScript files

### Provider Support (15+ providers)

| Provider | API Type | SDK |
|----------|----------|-----|
| Anthropic | anthropic-messages | `@anthropic-ai/sdk` |
| Anthropic Vertex | anthropic-vertex | `@anthropic-ai/vertex-sdk` |
| OpenAI | openai-completions, openai-responses | `openai` |
| Google | google-generative-ai, google-vertex, google-gemini-cli | `@google/genai` |
| Amazon Bedrock | bedrock-converse-stream | `@aws-sdk/client-bedrock-runtime` |
| Mistral | mistral-conversations | `@mistralai/mistralai` |
| Azure OpenAI | azure-openai-responses | `openai` |
| GitHub Copilot | openai-codex-responses | `openai` |
| Groq, Cerebras, XAI, Huggingface, Kimi, Alibaba | various | various |

### Key Types
```typescript
interface Model<TApi extends Api> {
  id: string
  provider: KnownProvider
  api: TApi
  contextWindow: number
  maxTokens: number
  cost: { input: number; output: number; cacheRead: number; cacheWrite: number }
}

type ThinkingLevel = "minimal" | "low" | "medium" | "high" | "xhigh"

interface SimpleStreamOptions extends StreamOptions {
  reasoning?: ThinkingLevel
  temperature?: number
  maxTokens?: number
  signal?: AbortSignal
}
```

### Special Features
- Prompt Caching ("none" | "short" | "long")
- Extended Thinking with token budgets
- Built-in OAuth (Anthropic, OpenAI Codex, Google CLI)
- Error recovery with configurable retry
- Session ID passing for provider session caching
- Payload inspection callback

### Dependencies (8 main)
`@anthropic-ai/sdk`, `@anthropic-ai/vertex-sdk`, `@aws-sdk/client-bedrock-runtime`, `@google/genai`, `@mistralai/mistralai`, `openai`, `chalk`, `@sinclair/typebox`, `ajv`, `undici`

---

## Package 4: @gsd/pi-coding-agent (v2.48.0)

**Purpose:** Main coding agent application — the largest package
**Location:** `/packages/pi-coding-agent/`
**Source Files:** 182 TypeScript files

### Directory Structure
```
src/
├── cli/                    # CLI entry & command handling
├── core/
│   ├── agent-session.ts   # Central session abstraction
│   ├── auth-storage.ts    # Auth credential management
│   ├── model-registry.ts  # Model selection & registry
│   ├── session-manager.ts # Session persistence & history
│   ├── settings-manager.ts # Configuration management
│   ├── extensions/        # Extension system (hooks, events)
│   ├── compaction/        # Context compaction & summarization
│   ├── tools/             # Tool implementations
│   │   ├── bash.ts        # Bash execution
│   │   ├── read.ts        # File reading
│   │   ├── write.ts       # File writing
│   │   ├── edit.ts        # File editing (diff-based)
│   │   ├── edit-diff.ts   # Diff engine
│   │   ├── grep.ts        # Regex search (native ripgrep)
│   │   ├── find.ts        # File finding (native fd)
│   │   ├── ls.ts          # Directory listing
│   │   └── hashline*.ts   # Hash-based line tracking
│   ├── lsp/               # Language Server Protocol
│   └── skills.ts          # Skill loading & parsing
├── modes/
│   ├── interactive/       # Interactive TUI mode
│   │   ├── components/    # TUI components
│   │   ├── controllers/   # Input/event handling
│   │   └── theme/         # Theme system
│   ├── rpc/               # JSON-RPC mode
│   └── shared/            # Common mode utilities
├── resources/
│   ├── extensions/        # Built-in extensions
│   └── vendor/            # Vendored dependencies
└── utils/                 # Shell, clipboard, frontmatter, etc.
```

### Core Concepts

**AgentSession** — Central abstraction:
- State access, message management
- Turn execution, bash execution
- Context compaction
- Session forking, switching
- Rich event system (message-start, tool-call, etc.)

**7 Core Tools:**
1. **read** — File reading with truncation, line ranges
2. **write** — File writing with safety checks
3. **edit** — Diff-based file editing
4. **bash** — Shell execution with interceptor rules
5. **grep** — Native ripgrep wrapper
6. **find** — Native fd wrapper
7. **ls** — Directory listing

**Compaction System:**
- Token estimation (Claude-3 compatible)
- Branch summaries for conversation pruning
- Cut-point calculation for optimal context window

**Extension System:**
- Lifecycle hooks (before/after agent, tool calls)
- Slash-command extensions
- UI integration (dialogs, widgets)
- Tool wrapping (intercept/modify results)

### Dependencies (25 production)
`@gsd/pi-agent-core`, `@gsd/pi-ai`, `@gsd/native`, `@gsd/pi-tui`, `chalk`, `diff`, `glob`, `marked`, `sql.js`, `yaml`, `file-type`, `extract-zip`, `proper-lockfile`, etc.

---

## Package 5: @gsd/pi-tui (v0.57.1)

**Purpose:** Terminal User Interface library (vendored from pi-mono)
**Location:** `/packages/pi-tui/`
**Source Files:** 31 TypeScript files

### Components (13)
```
components/
├── box.ts                  # Layout container (flexbox-like)
├── text.ts                 # Static text
├── truncated-text.ts       # ANSI-aware truncation
├── input.ts                # Single-line text input
├── editor.ts               # Multi-line code editor
├── markdown.ts             # Markdown rendering
├── image.ts                # Image rendering (Kitty/iTerm2)
├── loader.ts               # Loading spinner
├── cancellable-loader.ts   # Loader with cancel support
├── select-list.ts          # Item selection list
├── settings-list.ts        # Settings/options list
└── spacer.ts               # Vertical spacing
```

### Input Handling
- `keys.ts` — Low-level keyboard parsing (including Kitty protocol)
- `keybindings.ts` — Editor keybindings (Emacs-style defaults)
- `autocomplete.ts` — Fuzzy filtering
- `stdin-buffer.ts` — Batch input processing
- `kill-ring.ts` — Emacs-style kill ring
- `undo-stack.ts` — Undo/redo management

### Terminal Capabilities
- **Image Protocols:** Kitty Graphics, iTerm2 Inline, fallback
- **Input Protocols:** Standard + Kitty Extended Keyboard
- **Cell Dimension Detection** — Auto-detect for image scaling

### Dependencies (3)
`chalk`, `marked`, `mime-types`, `get-east-asian-width`

---

## Information Flow
```
User Input (TUI)
    ↓
pi-tui Components render to terminal
    ↓
Interactive Mode collects input
    ↓
AgentSession processes turn
    ↓
pi-agent-core loop: tool execution → LLM call
    ↓
Tools use native (grep, glob, etc.) + bash execution
    ↓
pi-ai streams responses from LLM provider
    ↓
Results displayed in pi-tui components
```

## Version Alignment
| Package | Version | Notes |
|---------|---------|-------|
| native | 0.1.0 | Low-level infrastructure |
| pi-agent-core | 0.57.1 | Vendored, stable API |
| pi-ai | 0.57.1 | Vendored, stable API |
| pi-tui | 0.57.1 | Vendored, stable API |
| pi-coding-agent | 2.48.0 | Main app version, tracks monorepo releases |

## Python Rebuild Implications

### Package Equivalents
| TypeScript Package | Python Equivalent |
|-------------------|-------------------|
| @gsd/native | Native Python libs: `ripgrepy`, `pygit2`, `tree-sitter`, `Pillow`, `rich` |
| @gsd/pi-agent-core | Custom agent loop module (or `langchain`/`pydantic-ai` core) |
| @gsd/pi-ai | `litellm` (unified LLM API) or custom provider abstraction |
| @gsd/pi-tui | `rich`, `textual`, or `prompt_toolkit` |
| @gsd/pi-coding-agent | Main Python application package |

### Monorepo Structure
Python options:
- **Single package** with submodules (simpler)
- **Multiple packages** with `poetry` workspaces or `hatch` monorepo
- **Namespace packages** (e.g., `gsd.core`, `gsd.ai`, `gsd.tui`)
