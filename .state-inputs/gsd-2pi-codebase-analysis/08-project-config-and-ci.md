# Project Configuration, CI/CD & Infrastructure Analysis

## Package Identity
- **Name:** gsd-pi (npm published name)
- **Version:** 2.48.0
- **Type:** ES Module
- **Main Entry:** dist/loader.js
- **CLI Binaries:** `gsd` and `gsd-cli` → dist/loader.js
- **License:** MIT (Copyright 2026 Lex Christopherson)
- **Repository:** https://github.com/gsd-build/gsd-2
- **Node.js Requirement:** >=22.0.0
- **Package Manager:** npm@10.9.3
- **piConfig:** `{ name: "gsd", configDir: ".gsd" }`

---

## Dependencies Summary

| Category | Count | Key Examples |
|----------|-------|-------------|
| Production | 133 | @anthropic-ai/sdk, openai, playwright, sql.js, sharp |
| DevDependencies | 4 | typescript, @types/node, c8 |
| OptionalDependencies | 6 | Platform-specific native binaries, fsevents, koffi |

### LLM Provider SDKs
- `@anthropic-ai/sdk` ^0.73.0
- `@anthropic-ai/vertex-sdk` ^0.14.4
- `@aws-sdk/client-bedrock-runtime` ^3.983.0
- `@google/genai` ^1.40.0
- `@mistralai/mistralai` ^1.14.1
- `openai` ^6.26.0

### Agent Infrastructure
- `@modelcontextprotocol/sdk` ^1.27.1
- `@mariozechner/jiti` ^2.6.2 (runtime module loading)
- `sql.js` ^1.14.1 (SQLite in JS)

### CLI & Terminal
- `@clack/prompts` ^1.1.0
- `chalk` ^5.6.2
- `strip-ansi` ^7.1.0

### Browser Automation
- `playwright` ^1.58.2

### File & Data
- `chokidar` ^5.0.0 (file watching)
- `yaml` ^2.8.2
- `marked` ^15.0.12
- `diff` ^8.0.2
- `sharp` ^0.34.5 (image processing)
- `glob` ^13.0.1
- `proper-lockfile` ^4.1.2

### Platform-Specific Optional
- `@gsd-build/engine-darwin-arm64` >=2.10.2
- `@gsd-build/engine-darwin-x64` >=2.10.2
- `@gsd-build/engine-linux-arm64-gnu` >=2.10.2
- `@gsd-build/engine-linux-x64-gnu` >=2.10.2
- `@gsd-build/engine-win32-x64-msvc` >=2.10.2
- `fsevents` ~2.3.3 (macOS)
- `koffi` ^2.9.0 (native FFI)

---

## NPM Scripts (50+)

### Build & Compilation
- `build` — Full: workspace packages → tsc → copy resources/themes → build web if stale
- `build:pi` — Build ALL workspace packages (sequential)
- `build:pi-tui`, `build:pi-ai`, `build:pi-agent-core`, `build:pi-coding-agent` — Individual
- `build:native-pkg` — Rust N-API compilation
- `build:native` — Release Rust build
- `build:native:dev` — Debug Rust build
- `build:web-host` — Build and stage web standalone
- `copy-resources`, `copy-themes`, `copy-export-html` — Asset copying

### Development
- `dev` — tsc --watch + watch-resources in parallel
- `gsd` — CLI entry for dev (node scripts/dev-cli.js)
- `gsd:web` — Build + copy resources + dev server
- `watch-resources` — File watcher for resources/

### Testing (14 scripts)
- `test` — unit + integration
- `test:unit` — Node.js unit tests with TS support
- `test:integration` — Integration tests
- `test:packages` — Package-specific tests
- `test:coverage` — Coverage with c8
- `test:smoke` — Quick smoke tests
- `test:fixtures` — Fixture replay
- `test:fixtures:record` — Record fixtures
- `test:live` — Live LLM tests (GSD_LIVE_TESTS=1)
- `test:browser-tools` — Browser automation tests
- `test:native` — Native module tests
- `test:secret-scan` — Secret scanning
- `test:live-regression` — Live regression
- `test:marketplace` — Marketplace discovery

### Release
- `release:bump` — Bump version (major/minor/patch)
- `release:changelog` — Generate changelog from commits
- `release:update-changelog` — Update CHANGELOG.md
- `pipeline:version-stamp` — Add dev version suffix for CI
- `sync-pkg-version` — Sync version across packages
- `sync-platform-versions` — Sync native platform versions
- `validate-pack` — Verify npm tarball contents
- `prepublishOnly` — Sync versions, build, validate, test

### Docker
- `docker:build-runtime` — Build runtime image
- `docker:build-builder` — Build CI builder image

### Security
- `secret-scan` — Scan for hardcoded secrets
- `secret-scan:install-hook` — Install pre-commit hook
- `typecheck:extensions` — TS check for extensions

---

## TypeScript Configuration

### tsconfig.json (Main)
```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "target": "ES2022",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "declaration": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"],
  "exclude": ["src/resources", "src/tests", "src/web"]
}
```

### tsconfig.extensions.json (Type check only, no emit)
- For `typecheck:extensions` script
- `allowImportingTsExtensions: true`

### tsconfig.resources.json (Resource compilation)
- Compiles src/resources/extensions/**/*.ts to dist/resources/
- No declarations, no source maps

---

## GitHub CI/CD Workflows

### CI Workflow (ci.yml)
**Trigger:** Push/PR to main
**Jobs:**
1. **detect-changes** — Docs-only detection for conditional skipping
2. **docs-check** — Prompt injection scanning in documentation
3. **lint** — Secret scanning, base64 scanning, .gsd/ check, TypeScript compilation, workspace validation
4. **build** — Install deps, build workspaces, build TS, copy resources, build web, typecheck extensions
5. **test** — Unit tests (with coverage), integration, smoke, fixture, browser-tools, native

### Pipeline Workflow (pipeline.yml)
**Trigger:** CI completes on main
**Jobs:**
1. **dev-publish** — Stamp dev version → publish to npm @dev
2. **test-verify** — Install @dev globally → smoke/fixture/live-regression → promote to @next → Docker runtime image
3. **prod-release** — Requires "prod" environment → tag → publish @latest → Docker builder image

### Build Native Workflow (build-native.yml)
**Matrix:** 5 platforms
- macOS ARM64, macOS x64
- Linux x64-gnu, Linux ARM64-gnu (cross-compile)
- Windows x64 MSVC

### AI Triage Workflow (ai-triage.yml)
- Claude AI classifies new issues/PRs against VISION.md and CONTRIBUTING.md

### Cleanup Dev Versions Workflow
- Removes old @dev npm versions

---

## Docker Configuration

### Dockerfile (2-stage)
**Builder:** node:24-bookworm + Rust toolchain + cross-compile tools
**Runtime:** node:24-slim + git + gsd-pi@${GSD_VERSION}

### Docker Sandbox (`docker/`)
- docker-compose.yml for container isolation
- Dockerfile.sandbox for sandbox image
- Network allowlisting for LLM APIs, npm, GitHub
- Persistent state volume

---

## Scripts Directory (36 scripts)

### Build Scripts
- `build-web-if-stale.cjs` — Conditional web rebuild
- `copy-resources.cjs` — Compile TS resources, copy non-TS, rewrite paths
- `copy-themes.cjs`, `copy-export-html.cjs` — Asset copying
- `watch-resources.js` — Dev watcher

### Package Management
- `link-workspace-packages.cjs` — Link @gsd/* packages
- `ensure-workspace-builds.cjs` — Validate dist/ exists
- `postinstall.js` — Orchestrate linking + builds + playwright
- `validate-pack.js` — Pre-publish tarball validation

### Security
- `secret-scan.sh` (242 lines) — Ripgrep-based secret detection
- `base64-scan.sh` (260+ lines) — Base64-encoded secret detection
- `docs-prompt-injection-scan.sh` (250+ lines) — Documentation injection scanning
- `install-hooks.sh` — Git pre-commit hook installation

### Release
- `version-stamp.mjs` — Dev version suffix
- `bump-version.mjs` — Semver bumping
- `sync-pkg-version.cjs` — Cross-package version sync
- `generate-changelog.mjs` — Conventional commit changelog
- `update-changelog.mjs` — CHANGELOG.md updater

### Recovery
- `recover-gsd-1364.sh/ps1` — Issue #1364 recovery (bash + PowerShell)
- `recover-gsd-1668.sh/ps1` — Issue #1668 recovery

### Quality
- `pr-risk-check.mjs` (450+ lines) — PR risk analysis
- `check-skill-references.mjs` — Skill reference validation

---

## GitHub Configuration

### CODEOWNERS
- Default: @gsd-build/maintainers
- Core (RFC required): packages/pi-agent-core/, src/resources/extensions/gsd/
- High blast radius: .github/, scripts/, Dockerfile, .secretscanignore

### Issue Templates
- **bug_report.yml** — Structured with type, steps, expected/actual, version, OS, area
- **feature_request.yml** — Problem, solution, alternatives, use cases, impact

### PR Template
- TL;DR (What/Why/How)
- Change type checklist
- Scope checkboxes (pi-tui, pi-ai, pi-agent-core, pi-coding-agent, gsd extension, native, ci/build)
- Breaking changes, test plan, AI disclosure

### Funding
- GitHub sponsor: glittercowboy

---

## Plan Files (.plans/, 17 documents)
Strategic planning for future development:
- api-key-manager, autocomplete-qol, directory-safeguards
- dynamic-model-discovery, fix-high-cpu-process-lifecycle
- provider-fallback, git2-migration, dynamic-model-routing
- parallel-milestone-orchestration, native-perf-optimizations
- onboarding-detection-wizard, preferences-wizard-completeness
- single-writer-engine-v3-control-plane, startup-performance
- token-optimization-suite, tui-dashboard-cleanup, workflow-templates

---

## VISION.md Core Principles
1. Extension-first — Capabilities in extensions, not core
2. Simplicity over abstraction — No premature abstractions
3. Tests are the contract — Define what's broken
4. Ship fast, fix fast — Iterate quickly
5. Provider-agnostic — No single-provider bias

---

## Key Architectural Decisions
1. **Extension-First** — New capabilities as extensions
2. **Vendored Dependencies** — pi-agent-core, pi-ai, pi-tui from pi-mono
3. **Workspace Monorepo** — npm workspaces with independent builds
4. **N-API Native Bindings** — Rust for performance-critical operations
5. **Provider-Agnostic AI** — Multiple LLM SDKs, no bias
6. **Single-Writer State Engine** — Controlled state transitions
7. **Type Safety** — Strict TypeScript throughout
8. **Git-Native Isolation** — Worktrees for milestone isolation
9. **Docker Sandbox** — Isolated auto-mode execution
10. **Test-First** — Bug fixes require regression tests

---

## Release Channels
- `@latest` — Production stable
- `@next` — Verified dev build
- `@dev` — Unverified CI build

---

## Python Rebuild Implications
- **Package management**: Use `poetry` or `hatch` for monorepo
- **CI/CD**: GitHub Actions works with Python (replace tsc with mypy, pytest)
- **Docker**: Similar 2-stage build (Python base instead of Node)
- **Secret scanning**: Scripts are bash-based, reusable as-is
- **Release**: Use `twine` for PyPI publishing
- **Version management**: Use `bumpversion` or `commitizen`
