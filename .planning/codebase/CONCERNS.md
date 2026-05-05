# Codebase Concerns

**Analysis Date:** 2026-05-05

## Tech Debt

**Build/Teach mode stubs are ~90% skeleton:**
- Issue: Both `state_build` and `state_teach` packages exist primarily as empty stubs. Core FSM implementations (`state_build/kernel.py`, `state_teach/kernel.py`) contain only `...` ellipsis method bodies. MCP servers (`state_build/mcp.py`, `state_teach/mcp.py`) are empty (3-line files). Verifiers directory (`state_build/verifiers/__init__.py`) is a 3-line placeholder. Teach submodules (`concepts.py`, `drill.py`, `mental_model.py`) are all 3-line stubs.
- Files: `src/state_build/kernel.py`, `src/state_build/mcp.py`, `src/state_build/verifiers/__init__.py`, `src/state_teach/kernel.py`, `src/state_teach/mcp.py`, `src/state_teach/concepts.py`, `src/state_teach/drill.py`, `src/state_teach/mental_model.py`
- Impact: Milestones v14 (Build Kernel) and v18 (Teach Kernel) cannot start until these stubs are implemented. Current stubs give false impression of readiness.
- Fix approach: These are expected scaffolding — owned by future milestones v14 (phases 124–134) and v18 (phases 124–134). No action needed now beyond awareness that ~16% of source files are stubs.

**Large provider files approaching complexity threshold:**
- Issue: Several auth provider files exceed 700 LOC with dense implementation. `github_copilot.py` (884 lines), `scheduler.py` (828 lines), `antigravity.py` (827 lines), `schema.py` (797 lines). These combine auth flow, token management, header injection, and CLI entry points in single files.
- Files: `src/state_core/auth/providers/github_copilot.py`, `src/state_core/auth/providers/antigravity.py`, `src/state_core/auth/providers/google_gemini.py` (751 lines), `src/state_core/auth/providers/anthropic.py` (741 lines), `src/state_core/scheduler.py`, `src/state_core/schema.py`
- Impact: Modification risk increases linearly with file size. Testing individual behaviors requires understanding full module context.
- Fix approach: Consider splitting auth providers into separate modules for HTTP flows, token models, and refresh logic. Not urgent — files are well-organized with clear section headers. Defer to post-v1 refactoring.

**TODO in model profile resolver:**
- Issue: `GlobalProfileConfig` lives in `state_core.providers.model_profile` but conceptually belongs in the global config module.
- Files: `src/state_core/providers/model_profile.py` line 15: `TODO: consolidate GlobalProfileConfig into state_core.config in a future phase.`
- Impact: Configuration is split across two modules. `state_core.config` and `state_core.providers.model_profile` both hold config-related types.
- Fix approach: Move `GlobalProfileConfig` to `state_core.config` in a dedicated cleanup phase. Add `from state_core.config import GlobalProfileConfig` re-export in model_profile for backward compatibility.

**Streaming cost accounting not instrumented:**
- Issue: `ProviderCostEmitter.acompletion()` in `cost_accounting.py` only handles non-streaming calls. Streaming inference (Phase 030+) will not emit cost-accounting events, creating incomplete cost reports.
- Files: `src/state_core/providers/cost_accounting.py` (line 16: "Tech debt: Streaming calls not instrumented — deferred to Phase 030+")
- Impact: Cost reports will undercount total spend once streaming is in use. Users relying on `state stats` for billing reconciliation will see discrepancies.
- Fix approach: Phase 030 (cache-control e2e) is the natural owner. `ProviderCostEmitter` needs a `astream()` method that accumulates usage from stream chunks.

**Phase 028 cost accounting Anthropic SDK path deferred:**
- Issue: `ProviderCostEmitter.acompletion()` token extraction code (lines 166-168) uses litellm-style field names (`prompt_tokens`/`completion_tokens`). Anthropic SDK responses use `input_tokens`/`output_tokens`. The comment at line 165 notes: "Phase 028 scope: litellm path only; Anthropic SDK path is Phase 030+."
- Files: `src/state_core/providers/cost_accounting.py`
- Impact: Anthropic SDK inference calls will emit cost events with `total_tokens=0` and no cost, making cost reports incomplete for the primary Anthropic OAuth path.
- Fix approach: Phase 030 or a dedicated cost-accounting follow-up phase should add proper Anthropic response normalization.

**Rule 2 deviation in Phase 058:**
- Issue: v6 milestone audit noted a Rule 2 deviation — `src/state_daemon/__main__.py` was created for subprocess spawn. The audit classified it as "essential and intentional."
- Files: `src/state_daemon/__main__.py`
- Impact: Minor — this is an intentional pattern for CLI subprocess launch. Documented in v6 audit.
- Fix approach: No action required. The deviation is acknowledged and intentional.

**Watchers module is empty stub:**
- Issue: `state_daemon/watchers.py` contains only a 3-line stub with a docstring and `from __future__ import annotations`. No file-watching or SSE-watching logic exists.
- Files: `src/state_daemon/watchers.py`
- Impact: The daemon cannot detect external changes to `.state/` files. File-watching for config hot-reload and auth rotation triggers is non-functional.
- Fix approach: This stub belongs to future daemon observability work. Owned by Phase 057 (crash recovery extensions) or a dedicated watchers phase.

**Retroactive SECURITY.md backfill debt (14 phases):**
- Issue: `security_enforcement=true` was enabled mid-v2. Phases 011–022 + 022.1 + 022.2 (14 phases) shipped before the SECURITY.md gate was active. Only Phase 022.3 has a SECURITY.md.
- Files: `.planning/milestones/v2/phases/011/` through `022.2/`
- Impact: Security verification artifacts are missing for 14 phases of the auth subsystem — the most security-critical component of the project.
- Fix approach: Backfill SECURITY.md for all 14 phases as a dedicated v2 close-out task. Priority: HIGH (auth subsystem). Per-project convention, this backfill is "known debt" and must not recur in v3+.

**Per-plan SUMMARY backfill debt (4 plans):**
- Issue: 4 plans (011-01, 011-02, 013-01, 020-01) shipped without per-plan SUMMARY.md during v2 milestone execution. Required manual backfill at milestone close.
- Files: `.planning/milestones/v2/phases/011-*/`, `013-*/`, `020-*/`
- Impact: Audit trail gap — minor. The backfill was completed at v2 milestone close but consumed ~30 minutes of manual effort.
- Fix approach: `execute-phase` agent must land per-plan SUMMARY before declaring plan done. The `summary_strict: true` config flag enforces this for v3 onwards.

**Live OAuth smoke testing not in CI:**
- Issue: All five auth methods (Anthropic OAuth stealth, Gemini CLI, Antigravity, Copilot device-code, plain API-key) rely on captured-header golden suites for CI fidelity. Live OAuth smoke tests are user-owned manual gates at release time.
- Files: `tests/auth/providers/test_anthropic.py`, `tests/auth/providers/test_google_gemini.py`, `tests/auth/providers/test_antigravity.py`, `tests/auth/providers/test_github_copilot.py`
- Impact: Auth regressions from Anthropic/Google/GitHub upstream changes will not be caught by CI. First detection is at manual release smoke or user report.
- Fix approach: Consider periodic CI cron jobs (weekly) that run a minimal live-OAuth smoke suite with disposable test accounts. Blocked on test-account provisioning. Marked as known debt in v2 audit.

---

## Known Bugs

_No active bugs detected at this state. The v6 milestone audit reported passing status with 0 regressions. Previous milestones (v1, v2, v5) all shipped with zero-regression verification. The `last_updated` field in `.planning/STATE.md` shows 2026-05-04 with v6 as the last shipped milestone._

**Potential edge case — daemon notification errors silently swallowed:**
- Issue: In `src/state_daemon/router.py` lines 92-103, JSON-RPC notifications (requests with no `id`) catch handler exceptions silently and return `b""`. No error logging or event emission.
- Files: `src/state_daemon/router.py` (lines 92-103)
- Symptoms: A notification handler that raises an exception will fail silently. The caller receives HTTP 200 with empty body and no indication of failure.
- Trigger: Any JSON-RPC notification where the handler raises.
- Workaround: None currently. Notifications are fire-and-forget by protocol design, but silent error swallowing may hide bugs.

---

## Security Considerations

**Anthropic OAuth stealth header drift (P2-1):**
- Risk: Claude Code adds new beta flags (e.g., new thinking version); `state` doesn't mirror; subscription access quietly downgrades features.
- Files: `src/state_core/auth/providers/anthropic.py` (headers defined in constants)
- Current mitigation: Headers are pinned byte-for-byte against `state-inputs/claude-oauth.md`. `CLAUDE_CODE_VERSION_LOCK.md` tracks version lock.
- Recommendations: Implement staleness warning if version-lock file is >60 days old. Ship `tools/check-claude-cli-headers.py` to diff against live Claude Code headers.

**Dependency version floor (CVE-2026-22701):**
- Risk: `filelock>=3.20.3` floor is enforced for CVE-2026-22701 protection. Lower versions of filelock are vulnerable to symlink-based privilege escalation.
- Files: `pyproject.toml` line 16
- Current mitigation: Version floor `>=3.20.3` enforced in pyproject.toml. `uv.lock` pins resolved version.
- Recommendations: Maintain floor. Add a CI step that verifies resolved filelock version >= 3.20.3 on every build.

**No upper-bound dependency pins:**
- Risk: `pyproject.toml` uses only `>=` pins with no `>=` upper bounds on critical dependencies (`litellm`, `anthropic`, `pygit2`, `mcp`, `httpx`). A major version upgrade could silently break stealth headers, worktree operations, or provider routing.
- Files: `pyproject.toml`
- Current mitigation: `uv.lock` (504KB) pins exact resolved versions, protecting reproducible builds.
- Recommendations: Add `<major+1` upper bounds for security-critical deps (e.g., `litellm>=1.80.0,<3.0.0`). CI should test against both pinned (lockfile) and latest-compatible (upper-bound) dependency sets.

**Free-threaded CPython (PEP 703) incompatibility (P1-37):**
- Risk: Python 3.13+ free-threaded builds (`python3.13t`) may crash with native deps (`pygit2`, `litellm`, `aiosqlite`) that aren't GIL-free compatible.
- Files: `pyproject.toml` (no free-threaded guard)
- Current mitigation: `requires-python = ">=3.12"` with no upper bound — does NOT exclude free-threaded builds.
- Recommendations: Add `requires-python = ">=3.12,<3.14"` or explicitly document "free-threaded not supported" in INSTALL.md. Skip `3.13t` in CI matrix until native deps catch up.

**Per-plan SUMMARY and SECURITY.md compliance for v3+:**
- Risk: 14 v2 phases lack SECURITY.md. 4 v2 plans lack per-plan SUMMARY. The `security_enforcement=true` and `summary_strict=true` flags are now active in `.planning/config.json` but the backlog persists.
- Files: `.planning/config.json`
- Current mitigation: Config enforces gates for v3+ phases. v2 debt is acknowledged and tracked.
- Recommendations: Prioritize backfill of v2 SECURITY.md files for auth phases. This is the most security-critical subsystem and missing security review artifacts constitute a process-level risk.

---

## Performance Bottlenecks

**Full-table scan in cost aggregation:**
- Problem: `aggregate_provider_costs()` in `src/state_core/providers/cost_accounting.py` (line 243) reads ALL events from the event store into memory with `await store.read_events()`, then filters in Python for `state.provider.response` events. No SQL-level filtering.
- Files: `src/state_core/providers/cost_accounting.py` (lines 243-282)
- Cause: The `read_events()` method returns all events without SQL WHERE clause filtering by type.
- Improvement path: Add a `read_events_by_type(event_type: str)` method to `SqliteEventStore` that pushes the type filter to SQLite (indexed column). Currently the `events` table has no index on `type` for this filter path.

**No SSE backpressure or client disconnect detection:**
- Problem: The SSE broadcast bus in `src/state_daemon/sse.py` (409 lines) fans out events to all connected clients. No mechanism prevents a slow client from blocking the broadcast loop or accumulating unbounded backlog.
- Files: `src/state_daemon/sse.py`
- Cause: SSE uses `asyncio.Queue` per client with configurable max size but no per-client timeout on delivery.
- Improvement path: Add per-client send timeout (e.g., 5 seconds). Drop clients that can't keep up. Emit a metric for dropped-client counts.

**SQLite WAL growing unbounded:**
- Problem: SQLite WAL file (`.state/events.sqlite-wal`) grows continuously with event writes. No automatic WAL checkpoint is configured.
- Files: `src/state_core/database.py` (connection setup), `src/state_core/migrations.py` (migration runner)
- Cause: WAL mode `synchronous=NORMAL` trades durability for performance. WAL checkpoint requires explicit invocation.
- Improvement path: Add periodic WAL checkpoint to the daemon's background loop (e.g., every 1000 events or 60 seconds). The `state_core.database.py` module should expose `checkpoint()` alongside the existing connection management.

---

## Fragile Areas

**Provider routing bypass guard (PRV-03):**
- Files: `src/state_core/providers/router.py` (82 lines)
- Why fragile: The OAuth bypass guard relies entirely on `isinstance(cred, OAuthCredential)` type checking. If a future credential subclass is incorrectly typed, OAuth traffic could route through litellm, breaking stealth headers. The guard is a single `if` branch — no defense-in-depth.
- Safe modification: Never add new `Credential` subclasses without updating `ProviderRouter.select()`. Add a unit test that enumerates all `Credential` subclasses and verifies each routes correctly.
- Test coverage: `tests/test_router.py` exists. Verify it covers all credential types including future ones via `__subclasses__()` enumeration.

**Mode isolation — strong in daemon middleware, weak in source packages:**
- Files: `src/state_build/__init__.py`, `src/state_teach/__init__.py` (docstring-only physical silos), `src/state_daemon/middleware.py` (canonical gate)
- Why fragile: Mode isolation has 6 planned defense-in-depth layers. Currently only layer 6 (daemon HTTP middleware) is fully implemented. Layers 1-5 (physical package separation, import-graph lint, plugin shim gating, MCP server gating, event mode filtering) are partially present or not yet built. The `state_build` / `state_teach` packages are empty stubs — the only enforcement is a docstring comment: "PHYSICAL SILO: this package must NEVER import state_teach."
- Safe modification: The daemon middleware (`src/state_daemon/middleware.py`) is the authoritative runtime gate and is fully tested (41 tests per v6 audit). Do not modify middleware without running the full mode-enforcement test suite.
- Test coverage: `tests/test_daemon_middleware.py`. Mode-specific import isolation is tested via `tests/test_imports.py` grep gates.

**v3 milestone code/plan discrepancy:**
- Files: `src/state_core/providers/` (router.py, anthropic_client.py, litellm_client.py, cost_accounting.py, thinking_budget.py, model_profile.py), `src/state_core/deps.py`, `src/state_core/http_client.py`
- Why fragile: Substantial implementation code exists for v3 phases 023-029 in `src/`, but the milestone state claims "0/9 phases complete" and "Status: Ready to plan." The Phase 028 (`cost-accounting-request`) and Phase 029 (`thinking-budget-tag-propagation`) directories have PLANS, SUMMARIES, and VERIFICATION artifacts, but ROADMAP.md still lists all v3 phases as "Not started." The code may have been authored during a research/scaffolding pass and not yet validated through the phase execution pipeline.
- Safe modification: Treat all v3 source code as "draft — not phase-validated." Run the full v3 test suite (`pytest tests/test_router.py tests/test_anthropic_client.py tests/test_litellm_client.py tests/test_cost_accounting.py tests/test_thinking_budget_propagation.py tests/test_model_profile.py tests/test_http_client.py tests/test_deps.py`) to establish baseline state before modifying.

**DAG scheduler CancelledError watchdog (P0-16):**
- Files: `src/state_core/scheduler.py`
- Why fragile: Python 3.12 `asyncio.TaskGroup` has a known CPython issue (#116720) where `CancelledError` can be silently swallowed in nested TaskGroups. The watchdog in Phase 046 detects this by checking for stalled tasks. The watchdog itself is a complex asyncio pattern and could have false positives/negatives.
- Safe modification: Do not modify the watchdog (`_check_cancelled_errors` heuristic) without running the full `tests/test_scheduler_watchdog.py` suite (Hypothesis property tests included).
- Test coverage: `tests/test_scheduler_watchdog.py` — 130 scheduler tests total per v5 audit. P0-16 regression harness is in place.

---

## Scaling Limits

**SQLite as sole event store:**
- Current capacity: ~10,000 events tested (v1 verifier). SQLite handles millions of rows without issue for single-writer workloads.
- Limit: Single-writer architecture (one daemon process owns the write connection). No horizontal scaling. Multi-process writes would require WAL-mode reader concurrency management or external locking.
- Scaling path: For multi-host deployments, migrate to PostgreSQL with the same schema. The `SqliteEventStore` Protocol/ABC pattern allows drop-in replacement of the backend.

**SSE fan-out:**
- Current capacity: Multi-client fan-out via `asyncio.Queue` in `src/state_daemon/sse.py`. Tested with limited concurrent clients.
- Limit: Python's asyncio event loop handles hundreds of concurrent connections. Beyond that, a dedicated pub/sub layer (Redis, NATS) would be needed. The current `SSEBroadcaster` is per-daemon (not clustered).
- Scaling path: Replace `SSEBroadcaster` with a Redis Stream or NATS JetStream bridge for multi-daemon deployments. The SSE client interface (`/events/subscribe`) is protocol-agnostic.

**Worktree count:**
- Current capacity: Per-Slice worktrees with no explicit limit. `state_core/worktree_gc.py` provides orphan cleanup.
- Limit: Git worktrees have a practical limit (~hundreds) before operations slow down. Each worktree adds a `.git/worktrees/<name>/` directory.
- Scaling path: GC policy should cap active worktrees at a configurable maximum. Oldest completed Slice worktrees get pruned first.

---

## Dependencies at Risk

**litellm version drift:**
- Risk: Known upstream issues with `anthropic-beta` header forwarding (BerriAI/litellm #9016), Bedrock beta header drops (#15622), Vertex cache-enabled header failures (#14293). Any litellm upgrade could break Anthropic OAuth stealth traffic if it accidentally intercepts headers.
- Impact: If the ProviderRouter bypass guard (`isinstance(cred, OAuthCredential)`) is defeated, OAuth traffic routes through litellm and stealth headers break.
- Migration plan: Never route OAuth-stealth Anthropic requests through litellm (PRV-03 enforced). Pin litellm and test with every upgrade via captured-header diff. The `ProviderRouter.select()` type-based routing is the defense.

**pygit2 native dependency:**
- Risk: `pygit2>=1.19.2` requires libgit2 native libraries. Platform-specific wheels may not be available for all environments (e.g., ARM Linux, free-threaded Python builds).
- Impact: Worktree fallback path fails if pygit2 is unavailable AND opencode worktree service is unreachable.
- Migration plan: The dual-provider pattern (opencode-preferred, pygit2-fallback, documented in `src/state_core/worktree.py`) provides resilience. If both fail, surface a clear error to CLI.

**No upper-bound pins (repeated from Security, listed here for completeness):**
- Risk: `pyproject.toml` uses only `>=` version pins. A major version bump in any dependency could silently break behavior.
- Impact: Scope varies by dep — litellm, anthropic SDK, pygit2 are highest risk.
- Migration plan: `uv.lock` provides reproducibility. CI matrix should test against both pinned and latest-compatible to catch drift early.

---

## Missing Critical Features

**Build-mode core commands (v15):**
- Problem: The full Build-mode cycle (plan/execute/verify/ship) has no implementation. Only the Step FSM stub exists with `...` method body.
- Blocks: All Build-mode workflows (v14-v17). The engine cannot orchestrate a single Build Slice.
- Owned by: v14 (Build Kernel Step FSM, phases 124-134) and v15 (Build Core Commands, phases 135-144).

**Teach-mode core cycle (v18-v20):**
- Problem: The Kolb FSM only has a `...` method body. Concept graph, drill engine, and mental model are 3-line empty stubs. No teaching can occur.
- Blocks: All Teach-mode workflows (v18-v24).
- Owned by: v18 (Teach Kernel Kolb+Concepts, phases 124-134), v19 (Drill Engine), v20 (Four Teaching Modes).

**Plugin TypeScript bundle (v8, v9):**
- Problem: The `@state/opencode-plugin` TypeScript package does not exist yet. No opencode hooks are wired. No TUI components (sidebar, statusline, toasts) exist.
- Blocks: The `state` engine cannot integrate with opencode sessions. No hook events, no TUI.
- Owned by: v8 (Plugin Server Hooks, phases 068-079) and v9 (Plugin TUI Bundle, phases 080-088).

**MCP servers (v12, v13):**
- Problem: Both `state-build` MCP server and `state-teach` MCP server are 3-line empty stubs (`src/state_build/mcp.py`, `src/state_teach/mcp.py`).
- Blocks: opencode cannot discover or invoke `state` tools. The engine is invisible to the LLM.
- Owned by: v12 (state-build MCP, phases 106-114) and v13 (state-teach MCP, phases 115-123).

**Per-session worker (v7):**
- Problem: No worker process bridges the plugin shim and the daemon. The daemon runs but cannot attach to opencode sessions.
- Blocks: v8 (Plugin Server Hooks) which depends on v7 for hook forwarding.
- Owned by: v7 (Per-Session Worker, phases 060-067).

**Nyquist validation gaps across v6:**
- Problem: All 10 v6 phases shipped without Nyquist validation artifacts. The v6 audit noted: "Nyquist validation not run on any phase (autonomous mode, skip_discuss)."
- Blocks: Process completeness — no functional impact but validation artifacts are missing.
- Owned by: Retrospective validation via `/gsd-validate-phase` for individual v6 phases.

---

## Test Coverage Gaps

**Stub files untested:**
- What's not tested: All empty-stub modules in `state_build` and `state_teach` — `kernel.py`, `mcp.py`, `verifiers/__init__.py`, `concepts.py`, `drill.py`, `mental_model.py`, `personalities/__init__.py`.
- Files: `src/state_build/kernel.py`, `src/state_build/mcp.py`, `src/state_build/verifiers/__init__.py`, `src/state_teach/kernel.py`, `src/state_teach/mcp.py`, `src/state_teach/concepts.py`, `src/state_teach/drill.py`, `src/state_teach/mental_model.py`, `src/state_teach/personalities/__init__.py`
- Risk: Low — these are intentionally empty stubs (3-line files with only `from __future__ import annotations`). No behavior to test. Risk increases when real implementation begins.
- Priority: Low (pre-implementation). Every stub must gain tests when its corresponding milestone phase executes.

**Watchers module untested:**
- What's not tested: `src/state_daemon/watchers.py` — another 3-line empty stub.
- Files: `src/state_daemon/watchers.py`
- Risk: Low — no behavior exists to test.
- Priority: Low (pre-implementation).

**Live OAuth testing not automated (repeated from Security):**
- What's not tested: Live token refresh, PKCE round-trips, device-code polling against real provider endpoints.
- Files: `tests/auth/providers/test_anthropic.py`, `tests/auth/providers/test_google_gemini.py`, `tests/auth/providers/test_antigravity.py`, `tests/auth/providers/test_github_copilot.py`
- Risk: Provider API changes (new required scopes, changed token shapes, header requirements) will go undetected until manual smoke testing or user reports.
- Priority: Medium. Captured-header golden suites cover the structural contract; live testing is a periodic (weekly) concern rather than per-commit.

**Streaming client paths untested for cost accounting:**
- What's not tested: `ProviderCostEmitter` does not handle streaming responses. Streaming cost accounting is entirely untested.
- Files: `src/state_core/providers/cost_accounting.py` (lines 66-68: "Non-streaming only")
- Risk: When streaming is enabled (Phase 030+), cost events will be missing or incorrect.
- Priority: Medium (owned by Phase 030).

---

*Concerns audit: 2026-05-05*
