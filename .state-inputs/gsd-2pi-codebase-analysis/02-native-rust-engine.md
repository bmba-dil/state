# Native Rust Engine Analysis

## Overview
**Location:** `/native/`
**Language:** Rust (edition 2021, MSRV 1.70+)
**Binding Layer:** N-API (Node.js native addon interface via `napi-rs`)
**Crate Type:** `cdylib` (compiled to `.node` shared library)

## Platform Support
- macOS (darwin-arm64, darwin-x64)
- Linux (linux-x64-gnu, linux-arm64-gnu)
- Windows (win32-x64-msvc)
- No platform-specific code in Rust — all platform handling via Cargo/Rust stdlib and vendored libgit2

## File Structure
```
native/
├── Cargo.toml (workspace config)
├── Cargo.lock
├── README.md
├── .cargo/config.toml
├── scripts/
│   ├── build.js (build script)
│   └── sync-platform-versions.cjs
├── crates/
│   ├── engine/          # Main crate with N-API exports
│   ├── ast/             # AST-aware search via tree-sitter
│   └── grep/            # Ripgrep core library
└── npm/                 # Platform-specific npm packages
    ├── darwin-arm64/
    ├── darwin-x64/
    ├── linux-arm64-gnu/
    ├── linux-x64-gnu/
    └── win32-x64-msvc/
```

## Native Modules (30+ N-API exports, 9,637 LOC Rust)

| Module | Lines | Purpose | Key Dependencies |
|--------|-------|---------|------------------|
| **grep** | 216 | Ripgrep-backed regex search on files + in-memory content | `grep-regex`, `grep-searcher`, `grep-matcher`, `rayon` |
| **ast** | 2 (wrapper) | AST-aware structural search & rewrite via tree-sitter | `ast-grep-core`, `tree-sitter`, 25+ language parsers |
| **git** | 1676 | Native git operations (read/write) via libgit2 | `git2` with vendored libgit2, path validation |
| **image** | 148 | Image decode/encode/resize | `image` crate (PNG, JPEG, WebP, GIF) |
| **clipboard** | 110 | System clipboard text/image I/O | `arboard` (cross-platform) |
| **text** | 1666 | ANSI-aware text measurement, grapheme handling, UTF-16 interop | `unicode-segmentation`, `unicode-width` |
| **highlight** | 472 | Syntax highlighting with ANSI colors | `syntect` with default themes/syntaxes |
| **diff** | 421 | Fuzzy text matching & unified diff generation | `similar` crate, Unicode normalization |
| **gsd_parser** | 1597 | Custom GSD command/directive parsing & state machine | Pure Rust parser |
| **fs_cache** | 444 | Shared filesystem scan cache with mtime tracking | `ignore` crate for .gitignore support |
| **glob** | 279 | Glob pattern matching with fs_cache integration | `globset`, `ignore` |
| **json_parse** | 410 | Streaming JSON parser with path tracking | Pure Rust streaming logic |
| **stream_process** | 682 | Output stream processing (colorization, pagination) | ANSI handling, custom logic |
| **fd** | 385 | Fast directory traversal | `ignore` crate walker |
| **ps** | 288 | Process introspection (list, kill, signal) | Platform-specific via `libc` |
| **task** | 107 | Libuv thread pool integration for blocking work | `napi` Task trait |
| **xxhash** | 43 | xxhash32 hashing | `xxhash-rust` |
| **html** | 44 | HTML to Markdown conversion | `html-to-markdown-rs` |
| **truncate** | 364 | Line/text truncation | Custom logic |
| **ttsr** | 143 | Tool-triggered system rules | Custom logic |

## Key Rust Dependencies
- **git2** (0.20) — Vendored libgit2 (not spawning `git` CLI)
- **grep-regex**, **grep-searcher**, **grep-matcher** — Ripgrep internals
- **syntect** (5.x) — Syntax highlighting
- **ast-grep-core** (0.39) — AST-aware search engine
- **tree-sitter** (0.25) + 25 language parsers — Language support
- **arboard** (3.x) — Clipboard access
- **image** (0.25) — Image codec support
- **ignore** (0.4) — .gitignore handling
- **dashmap** (6.x) — Concurrent HashMap
- **similar** (2.x) — Diff algorithm
- **globset** (0.4) — Glob matching
- **serde_json**, **napi**, **napi-derive** — JSON & N-API bindings

## N-API Surface (Exported to JavaScript)
- `searchContent(content, options)` — Grep in-memory
- `grep(options)` — Grep on disk
- `astFind(options)`, `astReplace(options)` — AST operations
- `copyToClipboard(text)`, `readTextFromClipboard()`, `readImageFromClipboard()` — Clipboard
- `NativeImage.parse()`, `resize()`, `encode()` — Image ops
- `normalizeForFuzzyMatch()`, `fuzzyFindText()`, `generateDiff()` — Diff/fuzzy
- `gitInit()`, `gitStatus()`, `gitDiff()`, `gitCheckout()`, `gitMerge()` — Git ops
- Plus 20+ more utilities for hashing, highlighting, text measurement, etc.

## Build Process

### Build Script: `/native/scripts/build.js`
1. Invokes `cargo build [--release]` on `native/crates/engine`
2. Locates compiled library:
   - macOS: `libgsd_engine.dylib`
   - Linux: `libgsd_engine.so`
   - Windows: `gsd_engine.dll`
3. Copies to `native/addon/` as:
   - Release: `gsd_engine.{platform}-{arch}.node`
   - Dev: `gsd_engine.dev.node`
4. Node.js loads via `require()` in TypeScript wrapper

### Release Build Optimizations (Cargo.toml)
- `opt-level = 3` (maximum optimization)
- `lto = "fat"` (cross-module LTO)
- `codegen-units = 1` (single codegen unit)
- `strip = true` (strip symbols)
- `panic = "abort"` (no unwinding overhead)

### Dev Build
- `codegen-units = 256` (fast incremental builds)
- `incremental = true`

## Python Rebuild Implications
These native modules are the **performance-critical path**. For a Python rebuild:
- **grep/glob/fd**: Could use `ripgrepy` or subprocess calls to `rg`/`fd`, or pure Python with `pathlib`/`re`
- **git**: Use `pygit2` (libgit2 bindings) or `gitpython`
- **ast**: Use `tree-sitter` Python bindings (available via `py-tree-sitter`)
- **image**: Use `Pillow`
- **clipboard**: Use `pyperclip` or `pyclip`
- **text/highlight**: Use `rich` library for terminal rendering and syntax highlighting
- **diff**: Use `difflib` from stdlib
- **json_parse**: Use `ijson` for streaming JSON
- **xxhash**: Use `xxhash` Python package
- **html**: Use `markdownify` or `html2text`
- **process**: Use `psutil`
