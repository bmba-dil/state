# v44 Handoff: Rust DB & RTK Agent Interception System

## Milestone Goal

Design a high-performance Rust-based system that intercepts agent tool calls (Read, Grep, Glob, etc.), routes them through a fast database containing a complete catalog of the project's files, codebase structure, dependencies, and relationships, then returns compressed, relevant results to the agent — bypassing slow filesystem operations and providing instant context. Also design the integration of the Rust Token Killer (RTK) concept for token-level compression.

## Background

You mentioned two related ideas:

1. **Rust Token Killer (RTK)**: An existing tool that intercepts agent tool uses and compresses them with Rust. This proves the interception architecture is viable.

2. **Custom Rust database**: A fast database that can instantaneously find files an agent needs, strip whitespace/indentation, and return compressed answers.

The core insight: **intercept agent commands → run through a fast Rust system → return optimized results**. This turns the agent's tool calls into database queries against a pre-built index of the entire project.

## What This Milestone Must Produce

### 1. Interception Architecture

Design how the system intercepts agent tool calls:

**Where interception happens:**
- Option A: At the opencode plugin hook layer (`tool.execute.before` / `tool.execute.after`)
  - Pro: Already have the hooks wired (v8)
  - Con: JavaScript layer, adds latency
- Option B: At the daemon level (HTTP middleware that wraps MCP tool responses)
  - Pro: Python-daemon controlled, can route through Rust via FFI/subprocess
  - Con: Added network hop (worker→daemon→rust→daemon→worker)
- Option C: At the opencode CLI level (patch or proxy the tool execution)
  - Pro: Transparent to the agent
  - Con: Complex, fragile, host-specific
- Option D: A sidecar process that the MCP server calls into
  - Pro: Clean separation, Rust can be a subprocess or gRPC service
  - Con: Another process to manage

**Recommended architecture to evaluate:** The MCP server (state-build) intercepts Read/Grep/Glob calls, routes to a Rust sidecar over Unix domain socket (fast, no network overhead), gets compressed results, returns to agent. This keeps interception in the Python control plane but delegates heavy lifting to Rust.

```
Agent → opencode → MCP tool call (e.g., read_file)
  → state-build MCP server intercepts
  → Checks: "is this a file-lookup? Can Rust DB handle it?"
  → If yes: forward to Rust sidecar over Unix socket
    → Rust queries its pre-built index
    → Rust strips whitespace, compresses, deduplicates
    → Returns optimized result
  → If no: fall through to normal tool execution
  → Returns result to agent
```

### 2. Database Schema Design

Design what the Rust database indexes:

**Project file index (every file in the project):**
- Path (absolute and relative to project root)
- File type (python, markdown, yaml, json, typescript, etc.)
- Size in bytes / lines
- Content hash (SHA-256)
- Last modified timestamp
- AST fingerprint (for Python: top-level classes, functions, imports)
- Belongs to which package/module

**Codebase structure graph:**
- Module → submodule relationships
- Class → method relationships
- Import graph (who imports whom)
- Call graph (who calls whom)
- Inheritance graph
- File → SLICE/STEP association (which Slice owns which file)

**Artifact index (all .planning/ and .state/ artifacts):**
- Artifact type (ARC.md, PHASE.md, SLICE.md, STEP.md, PLAN.md, etc.)
- Tier (Arc/Phase/Slice/Step)
- Parent references
- YAML frontmatter parsed fields
- Content keywords (extracted for search)
- Cross-references (which other artifacts does it reference)

**Event index (from .state/events.sqlite):**
- Event type
- Aggregate ID
- Timestamp
- Mode
- Related file paths mentioned in event data

**Symbol index (for code search):**
- Function names → file + line
- Class names → file + line
- Variable names → file + line (scope-aware)
- String literals → file + line
- Import statements → file + line

### 3. Query Interface

Design what queries the Rust DB supports:

**File finding (the primary use case):**
```
FIND files containing "OAuthProvider" in function names
  → [src/state_core/auth/providers/anthropic.py:142, ...]
FIND files importing "pydantic.BaseModel"
  → [src/state_core/schema.py:14, ...]
FIND artifacts referencing "BLD-03"
  → [.planning/milestones/v14/REQUIREMENTS.md:8, ...]
FIND files modified in Slice "auth-001-oauth-003"
  → [src/state_core/auth/providers/anthropic.py, ...]
FIND where is "StepMachine" defined
  → [src/state_build/kernel.py:10]
FIND all callers of "append_event"
  → [src/state_core/events.py, src/state_daemon/middleware.py, ...]
```

**Context assembly:**
```
GET full context for Step "step-004"
  → STEP.md + PLAN.md + DISCUSS.md + parent SLICE.md + parent PHASE.md + parent ARC.md
  → + all source files in the Slice's worktree
  → stripped of comments and whitespace
  → compressed to token budget
```

**Dependency resolution:**
```
WHAT depends on file "src/state_core/schema.py"?
  → [src/state_core/events.py (imports schema), src/state_daemon/middleware.py (imports schema), ...]
WHAT would break if I rename "StepState" to "StepLifecycle"?
  → [src/state_build/kernel.py:7, src/state_core/schema.py:89, ...]
```

**Cross-reference validation:**
```
Does PLAN.md "01-01-PLAN.md" reference all must-haves from STEP.md "step-004"?
  → Missing: BLD-03 (goal-backward verifier), BLD-08 (security verifier)
    Referenced: BLD-01, BLD-02, BLD-04
    VERDICT: 2 must-haves not covered
```

### 4. Compression Strategy

Design how results are compressed before returning to the agent:

**Whitespace stripping:**
- Remove leading indentation (preserve relative indentation)
- Collapse multiple blank lines to one
- Strip trailing whitespace

**Comment removal:**
- Remove docstrings from Python (but keep type annotations)
- Remove inline comments (but keep TODO/FIXME — those are signals)
- Remove commented-out code blocks

**Content-aware compression:**
- For Python: strip function bodies, keep signatures (option: `signatures_only`)
- For TypeScript: strip implementations, keep type declarations
- For Markdown: strip example blocks, keep section headers and key sentences
- For JSON/YAML: keep structure, remove comments

**Deduplication:**
- If the same file is returned in multiple results, deduplicate
- If the same import path appears in multiple files, flag but don't duplicate

**Token budget awareness:**
- The query accepts a `max_tokens` parameter
- The compression engine estimates token count (approximate: 1 token ≈ 0.75 words)
- If compressed result > max_tokens, apply increasingly aggressive compression:
  1. Strip comments and docstrings
  2. Strip function bodies (keep signatures)
  3. Strip to section headers only
  4. Strip to file list only (no content)
- The agent never sees an uncontrolled context dump

### 5. Indexing Strategy

Design how the Rust DB stays fresh:

**Incremental indexing:**
- On agent commit: daemon notifies Rust sidecar via event → index updated for changed files
- On worktree create/destroy: Rust sidecar adds/removes worktree from index
- On artifact write: daemon notifies Rust sidecar → artifact index updated

**Full re-index:**
- On daemon startup: Rust sidecar performs full re-index of project
- Re-index time budget: < 5 seconds for a 50K LOC project
- Incremental during operation: < 100ms per file change

**Index storage:**
- SQLite? (simple, portable) 
- Custom binary format? (faster, more complex)
- LMDB? (memory-mapped, very fast)
- The design should evaluate options and recommend

### 6. RTK Integration

Design how the Rust Token Killer concept integrates:

**What RTK does** (based on your description): Intercepts agent commands, compresses tokens, returns optimized results.

**State's RTK integration:**
- RTK becomes the compression engine within the Rust sidecar
- It receives raw file content → applies compression rules → returns token-optimized result
- RTK is pluggable: different compression profiles for different query types (file lookup vs context assembly vs code search)

**RTK compression profiles:**
| Profile | Use Case | Rules |
|---------|----------|-------|
| `signatures` | Agent needs to understand a module's API | Strip function bodies, keep signatures + docstrings |
| `overview` | Agent needs context about a file's purpose | Strip implementations, keep comments and structure |
| `full` | Agent needs to modify the file | No compression (but strip whitespace) |
| `references` | Agent needs to understand cross-references | Return only import/call/reference lines |
| `search` | Agent did a grep/glob search | Return matching lines + N context lines before/after |

### 7. Adoption Strategy

This is a v2.0 feature. The design should address:

- **Feature flag**: The interception system is opt-in. Agents work without it (falling through to normal tool execution). It can be enabled per-project, per-Slice, or per-Step.
- **Performance baseline**: Benchmarks before/after for common queries:
  - Finding a file by name: filesystem vs Rust DB
  - Grep for a symbol: ripgrep vs Rust DB
  - Assembling Step context: manual read vs Rust DB context assembly
- **Graceful degradation**: If the Rust sidecar is down, MCP tools fall through to normal execution transparently.
- **Build complexity**: Adding a Rust component to a Python project adds build complexity. Evaluate `maturin` + `pyo3` for Python-native integration vs standalone sidecar.

## Success Criteria

1. The interception architecture is designed with clear data flow from agent tool call → Rust DB → compressed result → agent.
2. The database schema covers file index, codebase structure graph, artifact index, event index, and symbol index.
3. The query interface supports file finding, context assembly, dependency resolution, and cross-reference validation.
4. The compression strategy has tiered rules (whitespace → comments → bodies → headers) with token budget awareness.
5. The indexing strategy supports incremental updates in < 100ms and full re-index in < 5 seconds for 50K LOC.
6. RTK integration is specified with compression profiles and pluggable architecture.
7. Adoption strategy addresses feature flag, performance baseline, graceful degradation, and build complexity.

## Research Inputs

**RTK reference (if available):**
- Check `~/Projects/` for any `rust-token-killer` or `rtk` projects
- Check `state-inputs/` for any RTK documentation
- If not available: research Rust tokenizer libraries (`tokenizers`, `tiktoken` Rust bindings)

**Rust + Python integration:**
- `maturin` / `pyo3` for Python-native Rust extensions
- Unix domain socket IPC for sidecar architecture
- `serde` for serialization between Python and Rust

**Database options:**
- SQLite via `rusqlite` (mature, well-tested, same format as state's event store)
- LMDB via `heed` (memory-mapped, zero-copy reads, very fast for read-heavy workloads)
- Custom binary format (max performance, max complexity)

**Code analysis:**
- `tree-sitter` with Python/TypeScript/Markdown grammars for AST-level indexing
- `rustpython` or `ruff` for Python-specific analysis
- `regex` crate for pattern matching (equivalent to ripgrep's engine)

**State shipped code:**
- `src/state_core/database.py` — existing SQLite connection factory
- `src/state_core/schema.py` — event types to index
- `src/state_core/events.py` — event store API to monitor for index invalidation
- `packages/opencode-plugin/src/hooks/tool-execute-before.ts` — existing hook for interception

## Key Questions for Discuss-Phase

1. **Architecture choice**: Rust sidecar (separate process, Unix socket) vs Rust Python extension (maturin/pyo3, same process)? Sidecar is cleaner but adds deployment complexity. Extension is simpler but ties Rust to Python process lifecycle.

2. **Scope of interception**: Should the system intercept ALL Read/Grep/Glob calls, or only those within the active Slice's worktree? Intercepting everything maximizes benefit but risks transparency issues.

3. **Database engine**: SQLite (known quantity, same as event store) or LMDB (faster reads) or custom? The database is read-heavy — LMDB's memory-mapped architecture would be significantly faster for reads.

4. **Compression aggressiveness**: How aggressive should the default compression be? Stripping function bodies saves tokens but removes information. Should the agent be able to request "uncompressed" for specific files?

5. **Build complexity tradeoff**: Adding a Rust toolchain requirement for Python developers is significant. Is the performance gain worth the build complexity? Could a pure-Python SQLite-based version work as v1, with Rust as v2?

6. **RTK prior art**: Do you have RTK code or documentation we can study? If so, where? If not, should v44 include a survey of token compression techniques?

## Dependencies

- **v41 (Agent Harness)** — MUST be complete. The interception system is part of the harness.
- **v40 (Hierarchy & Artifact System)** — useful but not blocking. The Rust DB indexes the hierarchy but doesn't depend on its design being final.
- **v12 (state-build MCP Server)** — useful. The MCP server is where interception happens.

## Scope Boundaries

**In scope:**
- Interception architecture design
- Database schema design
- Query interface specification
- Compression strategy
- Indexing strategy
- RTK integration design
- Adoption strategy

**Out of scope:**
- Rust implementation (belongs to a future v44+ milestone)
- Performance benchmarks (must wait for implementation)
- Any Python code changes to use the Rust DB
- Teach mode equivalent (teach mode gets the same Rust DB — no separate design needed)

## Reference Patterns

1. **ripgrep's pre-built index**: ripgrep uses a pre-built `.gitignore` index for fast file filtering. The Rust DB should extend this concept to a full project knowledge graph.

2. **Sourcegraph's code intelligence**: Sourcegraph indexes codebases for fast symbol search, cross-references, and dependency navigation. The Rust DB is doing this but agent-facing rather than human-facing.

3. **LLM context windows**: The Rust DB's token-budget-aware compression is solving a problem unique to LLM agents — traditional code intelligence tools don't care about token counts.

4. **Unix domain sockets for IPC**: Faster than TCP (no network stack), supported by both Python (`asyncio.open_unix_connection`) and Rust (`tokio::net::UnixListener`). Ideal for local sidecar communication.
