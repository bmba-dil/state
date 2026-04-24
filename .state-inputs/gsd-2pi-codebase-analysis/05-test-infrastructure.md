# Test Infrastructure Analysis

## Overview
- **Total Test Files:** 356+
- **Total Test LOC:** ~98,000+
- **Test Framework:** Node.js built-in test runner (`node:test`)
- **Assertion Library:** `node:assert/strict`
- **TypeScript Support:** `--experimental-strip-types` with `resolve-ts.mjs` hook
- **Coverage Tool:** `c8` (v11.0.0) with lcov reporter
- **Node Version Required:** 22.0.0+

## Test Commands
```bash
npm run test:unit                    # Main unit tests (74 src/tests + 282 extensions)
npm run test:integration            # Integration tests (6 + 51 extension)
npm run test:packages               # Package tests (pi-coding-agent core)
npm run test:marketplace            # Marketplace discovery (requires repos)
npm run test:coverage               # Code coverage with c8
npm run test:smoke                  # CLI smoke tests
npm run test:fixtures               # Fixture replay tests
npm run test:fixtures:record        # Record new fixtures
npm run test:live                   # Live LLM tests (requires API keys)
npm run test:browser-tools          # Browser extension tests
npm run test:native                 # Native package grep tests
npm run test:secret-scan            # Secret detection tests
npm run test:live-regression        # Live regression tests
```

## Test Directory Structure

### /src/tests/ (74 test files, ~16,766 lines)
Unit & integration tests for core CLI/agent:

**CLI & Bootstrap:**
- `app-smoke.test.ts` — CLI loader, env vars, extension paths
- `headless-detection.test.ts` — TTY/headless mode detection
- `headless-events.test.ts` — Headless mode event handling
- `tool-bootstrap.test.ts` — Tool initialization
- `startup-perf.test.ts` — Startup performance

**Web Mode (30+ tests):**
- `web-auth-token.test.ts` — Auth token handling
- `web-boot-node24.test.ts` — Node 24 bootstrap
- `web-bridge-contract.test.ts` — Web bridge API contract
- `web-cli-entry.test.ts` — Web CLI entry point
- `web-command-parity-contract.test.ts` — CLI↔Web command parity
- `web-mode-cli.test.ts` — Web mode CLI
- `web-mode-network-flags.test.ts` — Network flag handling
- `web-multi-project-contract.test.ts` — Multi-project support
- `web-onboarding-contract.test.ts` — Onboarding flow
- `web-responsive.test.ts` — Responsive design
- `web-session-parity-contract.test.ts` — Session API parity
- Plus 20+ more web contract tests

**Search & Data:**
- `search-loop-guard.test.ts` — Search iteration limits
- `search-provider-command.test.ts` — Provider search commands
- `search-tavily.test.ts` — Tavily search integration
- `tavily-helpers.test.ts` — Tavily helpers
- `secret-scan.test.ts` — Secret detection
- `token-counter.test.ts` — Token counting

**Extensions & Resources:**
- `extension-discovery.test.ts` — Extension manifest loading
- `extension-smoke.test.ts` — Basic extension functionality
- `resource-loader.test.ts` — Resource bundling & sync
- `resource-sync-staleness.test.ts` — Staleness detection
- `mcp-client-schema.test.ts` — MCP schema validation
- `mcp-server.test.ts` — MCP server initialization

### /src/tests/integration/ (6 files)
- `e2e-smoke.test.ts` — CLI binary smoke tests (spawned processes)
- `pack-install.test.ts` — npm pack → install → launch flow
- `web-mode-assembled.test.ts` — Web mode full stack
- `web-mode-onboarding.test.ts` — Web onboarding flow
- `web-mode-runtime-fixtures.ts` — Runtime fixture setup
- `web-mode-runtime-harness.ts` — Test harness

### /src/resources/extensions/gsd/tests/ (282 files, ~81,729 lines)
Core GSD extension tests organized by domain:

| Domain | Test Count | Examples |
|--------|-----------|----------|
| Auto-loop/Agent Loop | 20 | auto-loop, auto-recovery, auto-worktree |
| Workflow Planning | 15 | plan-milestone, plan-slice, plan-task |
| State Management | 18 | derive-state, derive-state-db, derive-state-draft |
| Database & Persistence | 20 | gsd-db, journal, json-persistence-atomic |
| Worktree Management | 20 | worktree, worktree-db, worktree-e2e |
| Parallel Execution | 8 | parallel-orchestration, parallel-workers |
| Budget & Cost | 8 | context-budget, budget-prediction, cost-projection |
| Doctor/Diagnostics | 15 | doctor, doctor-git, doctor-environment |
| Forensics & Recovery | 8 | forensics-journal, crash-recovery |
| Tools & Commands | 30+ | gsd-tools, commands-logs, exit-command |
| Git/VCS Integration | 8 | git-service, git-self-heal, git-locale |
| Migration | 10 | migrate-command, migrate-parser, migrate-writer |
| Web/UI | 20+ | web-responsive, web-onboarding, web-auth |
| Token Management | 5 | token-counter, token-cost-display |
| Plugins/Extensions | 8 | plugin-importer, skill-lifecycle |

### /tests/ (Harness & Fixture Tests)

**Fixture Recording System:**
- `tests/fixtures/provider.ts` — Recording/replay interfaces
- `tests/fixtures/record.ts` — Recording entry point
- `tests/fixtures/recordings/` — Recorded LLM conversations:
  - `agent-creates-file.json`
  - `agent-handles-error.json`
  - `agent-multi-turn-tools.json`
  - `agent-reads-and-edits.json`

**Smoke Tests:**
- `tests/smoke/run.ts` — Test runner harness
- `tests/smoke/test-help.ts` — Help command
- `tests/smoke/test-init.ts` — Init command
- `tests/smoke/test-version.ts` — Version display

**Live Tests:**
- `tests/live/run.ts` — Live test harness (requires GSD_LIVE_TESTS=1)
- `tests/live/test-anthropic-roundtrip.ts` — Anthropic API roundtrip
- `tests/live/test-openai-roundtrip.ts` — OpenAI API roundtrip

**Bug Reproduction:**
- `tests/repro-worktree-bug/` — Dockerfile + scripts for containerized repro

### /packages/ Tests (47 files)
- **pi-coding-agent** (20+): auth-storage, bash-background, artifact-manager, blob-store
- **pi-agent-core** (5): agent interface contract
- **pi-ai** (3): models, google-shared
- **native** (15+): HTML, clipboard, TTSR, grep, glob

## Coverage Configuration
```bash
c8 --reporter=text --reporter=lcov \
  --check-coverage \
  --statements=50 --lines=50 --branches=20 --functions=20
```

## Mocking & Fixture Strategies

### 1. Mock Function Builders
```typescript
function makeMockSession(opts?) { ... }
function makeMockCtx() { ... }
function makeMockPi() { ... }
```

### 2. Event Bus Mocking
```typescript
const events = [];
const bus = { emit, on, listeners: [] };
```

### 3. Temporary Filesystem
```typescript
const tmp = mkdtempSync(join(tmpdir(), 'prefix-'))
t.after(() => rmSync(tmp, { recursive: true }))
```

### 4. Fixture Recording/Replay
- `GSD_FIXTURE_MODE=record|replay|off`
- JSON with turn-based conversation structure
- Record live LLM conversations, replay in CI

### 5. Spy/Call Recording
```typescript
const calls = []
const spy = (...args) => calls.push(args)
```

## Test Isolation
- `--experimental-test-isolation=process` — Each test in separate process
- Temporary directories for I/O
- Mock objects for state
- No shared test state

## Test Type Distribution
| Type | Percentage | Count |
|------|-----------|-------|
| Unit | 85% | 300+ |
| Integration | 10% | 57+ |
| Contract | 5% | 15+ |
| E2E/Smoke | — | 8+ |
| Regression | — | 50+ |

## Python Rebuild Implications
- **Test framework**: Use `pytest` (equivalent to node:test)
- **Assertions**: Use `pytest` assertions or `unittest`
- **Coverage**: Use `coverage.py` or `pytest-cov`
- **Fixtures**: Use `pytest` fixtures and `tmp_path`
- **Mocking**: Use `unittest.mock` or `pytest-mock`
- **LLM fixture recording**: Implement custom JSON recording/replay (or use `vcrpy` for HTTP)
- **Test isolation**: pytest supports per-test process isolation via `pytest-xdist`
