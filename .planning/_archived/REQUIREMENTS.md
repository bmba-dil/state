# Requirements: state

**Defined:** 2026-04-22
**Core Value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.

## Scope Notes

- "v1" == day-one release (opencode-hosted, full feature surface per cardinal rules).
- "v2" == post-release. Portability shims may land here if opencode parity is achieved faster standalone.
- Requirements are grouped by the 27 candidate Arcs in `research/SUMMARY.md §5`. Roadmapper maps REQ-IDs to phases within each Arc.
- Every v1 requirement must have a test in the verifier before a phase closes (per the `verifier: true` config).

---

## v1 Requirements

### Kernel: Event Store (A1)

- [ ] **EVT-01**: Daemon writes every domain event to `.state/events.sqlite` (WAL, synchronous=NORMAL) before mirroring to opencode `SyncEvent`
- [ ] **EVT-02**: SQLite is the authoritative event source; daemon reads history from SQLite only
- [ ] **EVT-03**: Event sequence is monotonic per stream (Arc / Phase / Slice / Step / concept / learner); crash-recovery reconciles gaps
- [ ] **EVT-04**: Startup reconciliation replays unsent events to opencode's `SyncEvent` when opencode reconnects
- [ ] **EVT-05**: Pydantic event schemas with `extra = "forbid"` for every event type
- [ ] **EVT-06**: Event payloads are deterministic (no `datetime.now()` / randomness in handlers); replay is bit-identical
- [ ] **EVT-07**: CLI: `state events tail`, `state events replay --from <ulid>`, `state events export --format jsonl`
- [ ] **EVT-08**: Every event carries `mode: build|teach|kernel` for filtering

### Kernel: Auth (A2)

- [ ] **AUTH-01**: Anthropic OAuth stealth flow implemented byte-for-byte against `state-inputs/claude-oauth.md` — headers (`user-agent: claude-cli/<ver>`, `x-app: cli`, `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…`), PKCE verifier = OAuth `state`, client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e`, Bearer for `sk-ant-oat*`
- [ ] **AUTH-02**: Gemini CLI free-tier OAuth (google-auth-oauthlib, PKCE, refresh rotation)
- [ ] **AUTH-03**: Antigravity OAuth (custom flow, refresh handling)
- [ ] **AUTH-04**: GitHub Copilot device-code flow (polling, grant-revocation handling)
- [ ] **AUTH-05**: API key vault (plain keys for Anthropic, OpenAI, Google, DeepSeek, Groq, Together, Anyscale, Mistral, Cohere, OpenRouter, Grok, Cerebras)
- [ ] **AUTH-06**: `.state/auth.json` created chmod 0600 via `os.open(..., 0o600)` + `os.fchmod`; chmod verified on every read
- [ ] **AUTH-07**: Filelock-guarded refresh: acquire lock (10s timeout), re-read `auth.json`, double-check expiry, refresh only if stale, write, release
- [ ] **AUTH-08**: Multi-cred round-robin across credentials of the same provider
- [ ] **AUTH-09**: Access token renewal 5 minutes before `expires_in` (never verbatim)
- [ ] **AUTH-10**: Root-logger token redactor strips `sk-ant-*`, `sk-*`, `ya29.*`, etc. from every log record
- [ ] **AUTH-11**: First-run import from opencode's existing auth store when detected
- [ ] **AUTH-12**: `state auth login <provider>` / `state auth logout <provider>` / `state auth status` CLI
- [ ] **AUTH-13**: Captured-header regression test: golden-file compare of actual outbound HTTP headers against claude-oauth.md spec for every stealth request

### Kernel: Provider Routing (A3)

- [ ] **PRV-01**: litellm >= 1.80.0 as default provider abstraction for non-stealth traffic
- [ ] **PRV-02**: Direct Anthropic SDK escape hatch for extended thinking and fine-grained cache-control breakpoints
- [ ] **PRV-03**: OAuth stealth flow NEVER routes through litellm (bypass guard in provider selector)
- [ ] **PRV-04**: Model profiles (`quality` / `balanced` / `budget` / `inherit`) configurable per-Arc, per-Phase, or globally
- [ ] **PRV-05**: Cost accounting per request, aggregated per Step / Slice / Phase / Arc in SQLite
- [ ] **PRV-06**: Shared httpx client across daemon with connection pooling
- [ ] **PRV-07**: Streaming tokens flow through `chat.params` / `chat.headers` hook without mutation loss
- [ ] **PRV-08**: Thinking-budget tag propagation (`thinking.budget_tokens`) for Anthropic extended thinking
- [ ] **PRV-09**: Cache-control marker preservation end-to-end (client → provider → response accounting)

### Kernel: Worktree + Snapshot Service (A4)

- [ ] **WRK-01**: Per-Slice worktree — one worktree for all Steps within a Slice, sequential within, concurrent across Slices
- [ ] **WRK-02**: Opencode worktree service preferred when available; pygit2 fallback otherwise
- [ ] **WRK-03**: Transactional bootstrap: branch + worktree dir + `.state/` inheritance atomic; rollback on failure
- [ ] **WRK-04**: Orphan-worktree GC (nightly daemon task) — detects `.git/worktrees/*/locked`, stale branch names, full removal
- [ ] **WRK-05**: Branch naming: `slice/<arc>/<phase>/<slice-id>` deterministic
- [ ] **WRK-06**: Step snapshots via opencode `Snapshot.track` before execute, `Snapshot.revert` on verify failure
- [ ] **WRK-07**: Slice snapshots on boundary (all Steps complete or aborted) for rollup revert
- [ ] **WRK-08**: Prefix-only revert: reverting Step N within a Slice reverts N..last without touching earlier Steps
- [ ] **WRK-09**: `state snapshot list|diff|revert` CLI

### Kernel: DAG Scheduler (A5)

- [ ] **DAG-01**: Pure-Python scheduler (~300 LOC) — topological sort, cycle detection, typed `depends_on` edges (`blocks`, `soft`, `data`)
- [ ] **DAG-02**: Scheduler dispatches unblocked Slices/Steps up to a configurable concurrency cap
- [ ] **DAG-03**: TaskGroup watchdog — detects swallowed `CancelledError`, fails loud, prevents deadlock
- [ ] **DAG-04**: Reactive to event-store updates — new Slice completion immediately unblocks successors
- [ ] **DAG-05**: Priority inversion detection — warns when a soft dependency keeps a critical-path Slice blocked
- [ ] **DAG-06**: Silent-deadlock detection — if all in-flight Slices are blocked on descoped/missing predecessors, surface to TUI
- [ ] **DAG-07**: `state dag show [--arc|--phase|--slice]` CLI renders current DAG state as ASCII

### Kernel: Daemon (A6)

- [ ] **DAE-01**: Always-on user service (launchd plist on macOS, systemd --user unit on Linux)
- [ ] **DAE-02**: Per-session worker spawned by plugin shim; shares event store with daemon via HTTP+SSE
- [ ] **DAE-03**: pid-file includes process `start_time_ns`; stale-pid detection via `/proc` (Linux) or `ps` (macOS)
- [ ] **DAE-04**: Unix socket at `$XDG_RUNTIME_DIR/state-<projecthash>.sock` (fallback `/tmp/state-<user>-<hash>.sock`)
- [ ] **DAE-05**: HTTP API (Starlette or bare) with mode-enforcement middleware (canonical gate)
- [ ] **DAE-06**: SSE broadcast for live TUI updates (event forwarding, Slice status changes, DAG state)
- [ ] **DAE-07**: Log rotation with structlog + `logging.handlers.RotatingFileHandler`
- [ ] **DAE-08**: Crash recovery: daemon restart replays STATE.md projections from event log, resumes in-flight Steps from their last checkpoint
- [ ] **DAE-09**: `state daemon start|stop|restart|status|logs` CLI

### Kernel: Per-Session Worker (A7)

- [ ] **WRK-10**: Worker attaches to daemon on opencode session start; tears down on session close
- [ ] **WRK-11**: Worker owns hot state for the current session (active Slice, current Step FSM position, in-progress drill)
- [ ] **WRK-12**: Worker forwards opencode hook events to daemon over HTTP+SSE
- [ ] **WRK-13**: Mismatched plugin/daemon version negotiation — handshake header on worker attach; refuses on incompatible

### Opencode Plugin: Server Hooks (A8)

- [ ] **HOOK-01**: `chat.message` — observation recording in teach mode, Step context injection in build mode
- [ ] **HOOK-02**: `tool.execute.before` — mode-gate tool invocation, attribute to Step
- [ ] **HOOK-03**: `tool.execute.after` — verify outputs match Step contract; enqueue verifier trigger
- [ ] **HOOK-04**: `permission.ask` — route gray-area decisions to dialog or auto-decide per config
- [ ] **HOOK-05**: `event` — mirror opencode events to daemon event store
- [ ] **HOOK-06**: `experimental.chat.system.transform` — inject mode-specific system prompts (PRIMM/Socratic/etc. in teach mode; DISCUSS/PLAN boilerplate in build mode)
- [ ] **HOOK-07**: `experimental.session.compacting` — checkpoint Step state before compaction
- [ ] **HOOK-08**: `chat.params` / `chat.headers` — inject model-profile resolution and cache-control
- [ ] **HOOK-09**: `command.execute.before` — mode gate for `/state:*` slash commands
- [ ] **HOOK-10**: `shell.env` — export `STATE_ARC`, `STATE_PHASE`, `STATE_SLICE`, `STATE_STEP` to shell tools
- [ ] **HOOK-11**: Bundled as `@state/opencode-plugin` (server + TUI in one TS package)

### Opencode Plugin: TUI Bundle (A9)

- [ ] **TUI-01**: SolidJS-based TUI extension matching opencode's catalog (solid-js 1.9.10, @opentui/{core,solid} 0.1.99)
- [ ] **TUI-02**: Sidebar slot — build progress (current Step + Slice DAG mini-view) or teach concept state (current concept + mastery)
- [ ] **TUI-03**: Statusline — current mode / current Step / provider / cost so far this session
- [ ] **TUI-04**: Toast notifications for Slice completion, drill availability, gray-area decisions
- [ ] **TUI-05**: Plugin install script auto-registers with opencode via `TuiPluginInstallOptions`

### TUI: DAG Viewer (A10)

- [ ] **DAG-VIEW-01**: `/state:dag` route shows interactive DAG — nodes colored by status (pending/in-progress/done/failed/blocked)
- [ ] **DAG-VIEW-02**: Clicking a node opens detail pane with STEP.md / SLICE.md / PHASE.md / ARC.md contents
- [ ] **DAG-VIEW-03**: Filter by Arc, Phase, Slice, or show critical path
- [ ] **DAG-VIEW-04**: Live updates as scheduler advances state (via SSE)

### Mode Enforcement (A11)

- [ ] **MODE-01**: `.state/mode.json` declares `mode: build|teach|both` with schema validation
- [ ] **MODE-02**: Directory presence (`.state/build/` vs `.state/teach/`) is physical signal; writes to the wrong subtree are rejected at the daemon
- [ ] **MODE-03**: MCP server registration — `state-build` only started when mode in `{build, both}`; `state-teach` only when `{teach, both}`
- [ ] **MODE-04**: Plugin hook mode gate — `command.execute.before` rejects `/state:build:*` when mode is teach, etc.
- [ ] **MODE-05**: Daemon HTTP middleware (canonical gate) — every request carries `mode` header, validated against `mode.json`
- [ ] **MODE-06**: Python import-graph lint — CI test fails if `state.build.*` imports `state.teach.*` or vice versa
- [ ] **MODE-07**: `state mode init build|teach|both` CLI bootstraps the correct `.state/` subtree

### MCP: state-build server (A12)

- [ ] **MCP-B-01**: Server registered as `state-build` in opencode MCP config
- [ ] **MCP-B-02**: ≤15 tools with ≤80-token descriptions each
- [ ] **MCP-B-03**: Tools include: `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `research_step`, `snapshot_revert`, `dag_status`, `arc_show`, `slice_ship`, `code_review`, `debug_session`, `forensics`, `intel_refresh`, `pause_work`, `resume_work`
- [ ] **MCP-B-04**: Stateful tools (discuss/plan/execute/verify/review/debug) use opencode `task` tool + `task_id` resume; survive context compaction
- [ ] **MCP-B-05**: Streaming progress via MCP protocol for long-running tools
- [ ] **MCP-B-06**: `state dev tool-budget` command asserts total tool descriptions fit in the ≤15 × 80-token budget

### MCP: state-teach server (A13)

- [ ] **MCP-T-01**: Server registered as `state-teach` in opencode MCP config
- [ ] **MCP-T-02**: ≤15 tools with ≤80-token descriptions each
- [ ] **MCP-T-03**: Tools include: `concept_next`, `drill_prepare`, `drill_verify`, `concept_teach`, `observation_record`, `mental_model_show`, `subject_pick`, `subject_author`, `style_edit`, `learner_state`, `review_session`, `mentor_scaffold`, `coding_partner`, `learning_verify`
- [ ] **MCP-T-04**: Drill tools bind to opencode `question` tool for structured user input
- [ ] **MCP-T-05**: Observations are structured (schema-validated) only — no freeform text observations
- [ ] **MCP-T-06**: Drill prompts capped at ≤3000 tokens to prevent bloat

### Build Kernel: Step FSM + Verifiers (A14)

- [ ] **BLD-01**: Step state machine: `pending → discussing → planning → executing → verifying → shipped | reverted | blocked`
- [ ] **BLD-02**: STEP.md frontmatter schema: `goal`, `verify_contract`, `depends_on[]`, `model_profile`, `snapshots[]`, `cost_cap`
- [ ] **BLD-03**: Goal-backward verifier — reads STEP.md goal, walks committed code, asserts goal achievement; writes VERIFY.md with pass/fail + evidence
- [ ] **BLD-04**: Slice rollup verifier — aggregates Step verify results; fails Slice if any Step failed
- [ ] **BLD-05**: Phase rollup verifier — aggregates Slice verify results plus Phase-level integration tests
- [ ] **BLD-06**: Arc rollup verifier — aggregates Phase rollups plus Arc-level acceptance criteria
- [ ] **BLD-07**: Cross-tier integration verifier — runs after Arc boundary, checks interactions between completed Arcs
- [ ] **BLD-08**: Security verifier — runs per-Step, checks for common vulnerabilities in diff (SQL injection, path traversal, secret leakage, shell meta)
- [ ] **BLD-09**: Verifier writes structured results to SQLite + markdown VERIFY.md

### Build Kernel: Core Commands — plan/execute/verify/ship (A15)

- [ ] **CMD-01**: `/state:build:discuss <step>` — multi-turn clarification dialog, writes DISCUSS.md
- [ ] **CMD-02**: `/state:build:plan <step>` — produces PLAN.md with task decomposition, test plan, risks
- [ ] **CMD-03**: `/state:build:execute <step>` — dispatches to worker, writes EXECUTE.log, atomic commits per sub-task
- [ ] **CMD-04**: `/state:build:verify <step>` — runs the chain of verifiers; produces VERIFY.md
- [ ] **CMD-05**: `/state:build:ship <slice>` — opens PR, runs code review, finalizes Slice
- [ ] **CMD-06**: `/state:build:quick <description>` — fast path: skip Arc/Phase structure, inline Slice+Step
- [ ] **CMD-07**: Plan-checker agent validates PLAN.md will achieve goal before execute proceeds (`plan_check: true` config)
- [ ] **CMD-08**: Gray-area decision routing — planner detects ambiguity, surfaces to dialog or logs to DECISIONS.md per config

### Build Kernel: GSD Command Ports (A16)

- [ ] **PORT-01**: `/state:build:code-review` + `/state:build:code-review-fix` — spawned gsd-code-reviewer + gsd-code-fixer equivalents
- [ ] **PORT-02**: `/state:build:intel` — codebase intelligence refresh, writes `.state/build/intel/`
- [ ] **PORT-03**: `/state:build:map-codebase` — parallel mapper agents, writes `.state/build/codebase/`
- [ ] **PORT-04**: `/state:build:debug` — persistent debug session with scientific-method guardrails
- [ ] **PORT-05**: `/state:build:forensics` — post-mortem against git history + event log + artifacts
- [ ] **PORT-06**: `/state:build:pause-work` / `/state:build:resume-work` — context handoff via STATE.md projection
- [ ] **PORT-07**: `/state:build:thread` — persistent context threads across Steps/Slices
- [ ] **PORT-08**: `/state:build:workstreams` — multiple parallel work contexts in one project
- [ ] **PORT-09**: `/state:build:stats` — project statistics (phases, plans, requirements, git metrics, timeline)
- [ ] **PORT-10**: `/state:build:audit-uat` — cross-Slice UAT audit
- [ ] **PORT-11**: `/state:build:audit-milestone` — Arc/Phase boundary audit
- [ ] **PORT-12**: `/state:build:docs-update` — regenerate project docs verified against code
- [ ] **PORT-13**: `/state:build:backlog` + `/state:build:todos` + `/state:build:notes` — capture surfaces
- [ ] **PORT-14**: `/state:build:undo` — manifest-aware revert
- [ ] **PORT-15**: `/state:build:ui-phase` + `/state:build:ui-review` — UI spec + retroactive UI audit
- [ ] **PORT-16**: `/state:build:autonomous` — run all remaining unblocked work without interactive gates
- [ ] **PORT-17**: `/state:build:onboard` + `/state:build:help` — discoverability
- [ ] **PORT-18**: `/state:build:explore` — Socratic ideation router
- [ ] **PORT-19**: `/state:build:brainstorm` — 3-stage Seed → Expand → Converge
- [ ] **PORT-20**: `/state:build:scan` — lightweight codebase assessment
- [ ] **PORT-21**: `/state:build:cleanup` — archive completed artifacts
- [ ] **PORT-22**: `/state:build:reapply-patches` — reapply local mods after update
- [ ] **PORT-23**: `/state:build:new-arc` / `/state:build:new-phase` / `/state:build:new-slice` — hierarchy bootstrapping
- [ ] **PORT-24**: `/state:build:insert-slice` — urgent work via decimal numbering
- [ ] **PORT-25**: `/state:build:add-phase` / `/state:build:remove-phase`
- [ ] **PORT-26**: `/state:build:multi-arc` — batch-plan multiple Arcs from a feature dump
- [ ] **PORT-27**: `/state:build:review` — cross-AI peer review from external CLIs
- [ ] **PORT-28**: `/state:build:set-quality` / `/state:build:set-profile` / `/state:build:settings` — runtime toggles
- [ ] **PORT-29**: `/state:build:health` — diagnose planning health
- [ ] **PORT-30**: `/state:build:manager` — interactive command center

### Build TUI (A17)

- [ ] **B-TUI-01**: Build dashboard route — Arc/Phase/Slice hierarchy browser with drill-down
- [ ] **B-TUI-02**: Step detail view — DISCUSS / PLAN / EXECUTE / VERIFY tabs
- [ ] **B-TUI-03**: Commit browser — per-Step commits with revert UI
- [ ] **B-TUI-04**: Gray-area decision dialog — shows options, rationale, auto-decides per config with manual override

### Teach Kernel: Kolb + Concepts + Mental-Model (A18)

- [ ] **TCH-01**: Concept-graph projection from subject authoring (CONCEPT-GRAPH.json) — nodes (concepts), edges (prerequisites)
- [ ] **TCH-02**: Kolb state machine: `concrete-experience → reflective-observation → abstract-conceptualization → active-experimentation` per concept
- [ ] **TCH-03**: Event-sourced mental-model — OBSERVATIONS.jsonl is authoritative; MENTAL-MODEL.json is a projection rebuildable from event log
- [ ] **TCH-04**: Concept-teacher orchestrates mode selection + personality + Kolb stage for each concept
- [ ] **TCH-05**: Drop-to-simpler-mode on frustration signal (detected from observation patterns)
- [ ] **TCH-06**: `state teach next-concept` surfaces the right next concept given current mastery
- [ ] **TCH-07**: Learner privacy: observations never leak raw user inputs; structured schemas only
- [ ] **TCH-08**: Rebuild MENTAL-MODEL.json from OBSERVATIONS.jsonl on demand (`state teach mental-model rebuild`)

### Teach: Drill Engine (A19)

- [ ] **DRL-01**: `drill_prepare` tool — generates drill question per concept + Kolb stage
- [ ] **DRL-02**: `drill_verify` tool — grades learner response, updates mental-model event
- [ ] **DRL-03**: Drill prompts bind to opencode `question` tool for structured input
- [ ] **DRL-04**: Drill prompt budget ≤3000 tokens
- [ ] **DRL-05**: Bayesian mastery update (prior → posterior from drill outcome); formula verified against AOL source
- [ ] **DRL-06**: `state teach drill` CLI fallback for non-opencode hosts (plain stdin)

### Teach: Four Modes + Selector (A20)

- [ ] **MODE-P-01**: PRIMM mode — predict/run/investigate/modify/make, full state machine per concept
- [ ] **MODE-S-01**: Scaffolded mode — graduated hints, prerequisites reinforcement, worked examples
- [ ] **MODE-SO-01**: Socratic mode — question-led discovery, no direct answers
- [ ] **MODE-C-01**: Constructivist mode — build-your-own, minimal scaffolding
- [ ] **MODE-SEL-01**: Mode selector — mastery-based routing (PRIMM <30% → Scaffolded 30–50% → Socratic 50–70% → Constructivist 70–80%)
- [ ] **MODE-SEL-02**: Manual override — learner can pick mode
- [ ] **MODE-SEL-03**: Drop-to-simpler on frustration signal

### Teach: Personalities + Teaching Style (A21)

- [ ] **PER-01**: All 7 AOL personalities ported verbatim as text blocks
- [ ] **PER-02**: Personality loader injects into `chat.params` / `chat.headers` system prompt
- [ ] **PER-03**: Teaching-style config (7 dimensions) via `state teach style edit`
- [ ] **PER-04**: Per-subject personality override

### Teach: Scaffolding Mentor + Coding Partner (A22)

- [ ] **SCA-01**: Scaffolding-mentor guides file-by-file project skeleton creation
- [ ] **SCA-02**: Records observations for every file creation + structural decision
- [ ] **SCA-03**: Never takes the keyboard unless invited
- [ ] **CPT-01**: Coding-partner watches learner code, offers graduated hints when stuck
- [ ] **CPT-02**: Teaches prerequisites proactively from PROJECT-PLAN.md
- [ ] **CPT-03**: Logs accomplishments + end-of-session growth note gate
- [ ] **CPT-04**: Never writes code for the learner

### Teach TUI (A23)

- [ ] **T-TUI-01**: Teach dashboard — subject / concept graph / mastery heatmap
- [ ] **T-TUI-02**: Drill UI — question card, answer input, feedback panel
- [ ] **T-TUI-03**: Mental-model viewer — concept tree with mastery badges
- [ ] **T-TUI-04**: Session timeline — observations log, mode transitions, drill history

### Teach: Subject Authoring (A24)

- [ ] **SUB-01**: Conversational subject-authoring workflow — interview, concept-graph approval
- [ ] **SUB-02**: 4-gate staged draft (interview → graph → draft → promote)
- [ ] **SUB-03**: `state teach subject new|edit|promote` CLI
- [ ] **SUB-04**: Subject schema validation

### Migration & Import (A25)

- [ ] **MIG-01**: `state migrate from-gsd` — read `.planning/` → write `.state/build/`
- [ ] **MIG-02**: `state migrate from-aol` — read `.aol/` → write `.state/teach/`
- [ ] **MIG-03**: Preserve history via event-log replay of migration events
- [ ] **MIG-04**: Dry-run mode with diff preview

### Portability Shims (A26) — MCP-only, reduced UX

- [ ] **PORT-SHIM-01**: Claude Code shim — MCP server registration, no TUI, slash commands via CLAUDE.md guidance
- [ ] **PORT-SHIM-02**: Gemini CLI shim — MCP registration, stdio transport
- [ ] **PORT-SHIM-03**: Qwen Code shim — MCP registration, stdio transport
- [ ] **PORT-SHIM-04**: Host capability detection — gracefully degrades when `question` / TUI slots / `Snapshot` missing

### Release & Packaging (A27)

- [ ] **REL-01**: `pyproject.toml` with `uv_build` backend
- [ ] **REL-02**: `uvx state install` auto-registers plugin + MCP servers with opencode
- [ ] **REL-03**: Wheel includes opencode plugin TS source + bun build output
- [ ] **REL-04**: `state update` checks PyPI for newer version, prompts to upgrade
- [ ] **REL-05**: Remote skill registry — `state skills add <url>` fetches community skills
- [ ] **REL-06**: Release notes generated from commit history + phase artifacts

### Documentation (threaded into every Arc; explicit requirements below)

- [ ] **DOC-01**: Architecture guide (component topology, hook wiring, state machines)
- [ ] **DOC-02**: User guide (install, init, first Arc, first Step, shipping)
- [ ] **DOC-03**: Command reference (every `/state:*` command)
- [ ] **DOC-04**: Build-mode author guide (how to plan an Arc, write a STEP.md, verify contracts)
- [ ] **DOC-05**: Teach-mode author guide (subject authoring, concept graphs, mode selection)
- [ ] **DOC-06**: Plugin development guide (how to write a `state` extension / personality)
- [ ] **DOC-07**: Auth setup guides (per-provider, including OAuth stealth rationale)
- [ ] **DOC-08**: Portability guide (Claude Code / Gemini CLI / Qwen Code setup)

### Test Infrastructure (threaded into every Arc; explicit requirements below)

- [ ] **TST-01**: pytest + pytest-asyncio baseline with `strict_asyncio` mode
- [ ] **TST-02**: Hypothesis property tests for DAG scheduler invariants
- [ ] **TST-03**: Hypothesis property tests for event-log replay (idempotence, determinism)
- [ ] **TST-04**: E2E fixture spawns real opencode binary (pinned version in `resources/opencode-version.txt`)
- [ ] **TST-05**: Provider parity matrix — same prompt across Anthropic / Gemini / Copilot / API-key providers, assert compatible behavior
- [ ] **TST-06**: Captured-header regression tests for all 5 auth methods
- [ ] **TST-07**: Mode-isolation import-graph test — fails if `state.build.*` imports `state.teach.*` or vice versa
- [ ] **TST-08**: P0 regression tests — one test per P0 pitfall in PITFALLS.md

### Observability

- [ ] **OBS-01**: structlog-based structured logging with JSON output option
- [ ] **OBS-02**: Root-logger token redactor (auth.json, OAuth bearers, device codes)
- [ ] **OBS-03**: Event log is the forensic ground truth; logs are supplementary
- [ ] **OBS-04**: `state logs tail [--level] [--component]` CLI

### Security

- [ ] **SEC-01**: Path-traversal guard on every filesystem write (project-root-relative, refuse `..`)
- [ ] **SEC-02**: Prompt-injection guard on MCP tool responses (reject control sequences)
- [ ] **SEC-03**: Shell-meta escaping on all subprocess invocations
- [ ] **SEC-04**: Regex-DoS guard — timeout on user-supplied regex patterns
- [ ] **SEC-05**: JSON-bomb guard — reject pathological nested payloads
- [ ] **SEC-06**: `auth.json` chmod 0600 verified on every read; refuse operation if permissions wrong

---

## v2 Requirements (deferred)

### Portability shims full UX

- **PORT-SHIM-V2-01**: Claude Code skill-based TUI emulation
- **PORT-SHIM-V2-02**: Gemini CLI richer `question` emulation
- **PORT-SHIM-V2-03**: Qwen Code parity testing

### Observability upgrade

- **OBS-V2-01**: OpenTelemetry traces with span per Step
- **OBS-V2-02**: Metrics export to Prometheus / Datadog

### Evaluation infrastructure

- **EVAL-V2-01**: Golden-file eval harness for verifiers
- **EVAL-V2-02**: Agent benchmark suite (against SWE-bench, TeachEval)

### Advanced features

- **ADV-V2-01**: Knowledge graph (Kuzu/DuckDB) for codebase queries
- **ADV-V2-02**: Real-time collaboration — multiple devs sharing a `.state/` tree

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Own TUI framework | Extend opencode's TUI; Textual reserved for standalone utilities |
| Simultaneous build + teach in one invocation | Exclusive-modes cardinal rule |
| API-keys-only v1 | All five auth methods are day-one per cardinal rule 6 |
| Shared mode abstraction | Build and teach share only the kernel; mode logic fully siloed |
| GSD's 2-tier milestone→phase hierarchy | Replaced by 4-tier Arc/Phase/Slice/Step |
| Serial phase execution | Replaced by typed `depends_on` DAG + concurrency scheduler |
| Verbatim port of GSD commands | Each command inventoried and redesigned |
| Prefect / Dask / Airflow | Pure-Python scheduler is committed; those are wrong shape |
| SQLAlchemy / Alembic | Hand-rolled numbered SQL migrations (simplicity, single-table event log) |
| GitPython | `pygit2` via libgit2 wheels |
| NetworkX | DAG scheduler is agent-shaped, not graph-algorithm-shaped |
| LangChain / LangGraph | litellm + direct SDK + pluggy is sufficient |
| Real-time multi-user collab | Single-user focus for v1 |
| Web/HTTP UI | opencode TUI is the only UI surface |
| Mobile | N/A |

---

## Traceability

Every v1 REQ-ID is mapped to exactly one milestone + phase. **Coverage: 221/221 (100%).**

| Requirement | Milestone (Arc) | Phase | Status |
|-------------|-----------------|-------|--------|
| EVT-01 | M-A1 | M-A1.P3 + M-A1.P4 + M-A1.P5 | Pending |
| EVT-02 | M-A1 | M-A1.P3 + M-A1.P4 + M-A1.P8 | Pending |
| EVT-03 | M-A1 | M-A1.P4 + M-A1.P7 | Pending |
| EVT-04 | M-A1 | M-A1.P6 | Pending |
| EVT-05 | M-A1 | M-A1.P2 | Pending |
| EVT-06 | M-A1 | M-A1.P4 + M-A1.P10 | Pending |
| EVT-07 | M-A1 | M-A1.P9 | Pending |
| EVT-08 | M-A1 | M-A1.P2 + M-A1.P9 | Pending |
| AUTH-01 | M-A2 | M-A2.P4 | Pending |
| AUTH-02 | M-A2 | M-A2.P5 | Pending |
| AUTH-03 | M-A2 | M-A2.P6 | Pending |
| AUTH-04 | M-A2 | M-A2.P7 | Pending |
| AUTH-05 | M-A2 | M-A2.P8 | Pending |
| AUTH-06 | M-A2 | M-A2.P2 | Pending |
| AUTH-07 | M-A2 | M-A2.P3 + M-A6.P10 | Pending |
| AUTH-08 | M-A2 | M-A2.P9 + M-A6.P10 | Pending |
| AUTH-09 | M-A2 | M-A2.P3 | Pending |
| AUTH-10 | M-A2 | M-A2.P10 | Pending |
| AUTH-11 | M-A2 | M-A2.P11 + M-A25.P6 | Pending |
| AUTH-12 | M-A2 | M-A2.P12 | Pending |
| AUTH-13 | M-A2 | M-A2.P12 | Pending |
| PRV-01 | M-A3 | M-A3.P2 | Pending |
| PRV-02 | M-A3 | M-A3.P3 | Pending |
| PRV-03 | M-A3 | M-A3.P4 | Pending |
| PRV-04 | M-A3 | M-A3.P5 | Pending |
| PRV-05 | M-A3 | M-A3.P6 | Pending |
| PRV-06 | M-A3 | M-A3.P1 | Pending |
| PRV-07 | M-A3 | M-A3.P2 | Pending |
| PRV-08 | M-A3 | M-A3.P3 + M-A3.P7 | Pending |
| PRV-09 | M-A3 | M-A3.P3 + M-A3.P8 | Pending |
| WRK-01 | M-A4 | M-A4.P5 | Pending |
| WRK-02 | M-A4 | M-A4.P2 + M-A4.P3 + M-A26.P6 | Pending |
| WRK-03 | M-A4 | M-A4.P5 | Pending |
| WRK-04 | M-A4 | M-A4.P6 | Pending |
| WRK-05 | M-A4 | M-A4.P4 | Pending |
| WRK-06 | M-A4 | M-A4.P7 | Pending |
| WRK-07 | M-A4 | M-A4.P8 | Pending |
| WRK-08 | M-A4 | M-A4.P9 | Pending |
| WRK-09 | M-A4 | M-A4.P9 | Pending |
| DAG-01 | M-A5 | M-A5.P1 + M-A5.P2 + M-A5.P3 | Pending |
| DAG-02 | M-A5 | M-A5.P4 + M-A5.P5 | Pending |
| DAG-03 | M-A5 | M-A5.P6 | Pending |
| DAG-04 | M-A5 | M-A5.P7 | Pending |
| DAG-05 | M-A5 | M-A5.P8 | Pending |
| DAG-06 | M-A5 | M-A5.P8 | Pending |
| DAG-07 | M-A5 | M-A5.P9 | Pending |
| DAE-01 | M-A6 | M-A6.P6 | Pending |
| DAE-02 | M-A6 | M-A6.P1 + M-A6.P5 | Pending |
| DAE-03 | M-A6 | M-A6.P2 | Pending |
| DAE-04 | M-A6 | M-A6.P3 | Pending |
| DAE-05 | M-A6 | M-A6.P1 + M-A6.P4 | Pending |
| DAE-06 | M-A6 | M-A6.P5 | Pending |
| DAE-07 | M-A6 | M-A6.P7 | Pending |
| DAE-08 | M-A6 | M-A6.P8 | Pending |
| DAE-09 | M-A6 | M-A6.P9 | Pending |
| WRK-10 | M-A7 | M-A7.P1 + M-A7.P6 | Pending |
| WRK-11 | M-A7 | M-A7.P3 | Pending |
| WRK-12 | M-A7 | M-A7.P4 | Pending |
| WRK-13 | M-A7 | M-A7.P5 | Pending |
| HOOK-01 | M-A8 | M-A8.P2 | Pending |
| HOOK-02 | M-A8 | M-A8.P3 | Pending |
| HOOK-03 | M-A8 | M-A8.P4 | Pending |
| HOOK-04 | M-A8 | M-A8.P5 | Pending |
| HOOK-05 | M-A8 | M-A8.P6 | Pending |
| HOOK-06 | M-A8 | M-A8.P7 | Pending |
| HOOK-07 | M-A8 | M-A8.P8 | Pending |
| HOOK-08 | M-A8 | M-A8.P9 | Pending |
| HOOK-09 | M-A8 | M-A8.P10 | Pending |
| HOOK-10 | M-A8 | M-A8.P11 | Pending |
| HOOK-11 | M-A8 | M-A8.P1 + M-A8.P12 | Pending |
| TUI-01 | M-A9 | M-A9.P1 | Pending |
| TUI-02 | M-A9 | M-A9.P2 + M-A9.P3 + M-A9.P4 + M-A23.P7 | Pending |
| TUI-03 | M-A9 | M-A9.P5 + M-A9.P8 | Pending |
| TUI-04 | M-A9 | M-A9.P6 | Pending |
| TUI-05 | M-A9 | M-A9.P7 | Pending |
| DAG-VIEW-01 | M-A10 | M-A10.P1 + M-A10.P2 + M-A10.P6 + M-A10.P7 | Pending |
| DAG-VIEW-02 | M-A10 | M-A10.P3 | Pending |
| DAG-VIEW-03 | M-A10 | M-A10.P4 | Pending |
| DAG-VIEW-04 | M-A10 | M-A10.P5 | Pending |
| MODE-01 | M-A11 | M-A11.P1 | Pending |
| MODE-02 | M-A11 | M-A11.P2 | Pending |
| MODE-03 | M-A11 | M-A11.P3 + M-A11.P8 + M-A12.P7 + M-A13.P7 | Pending |
| MODE-04 | M-A11 | M-A11.P4 | Pending |
| MODE-05 | M-A11 | M-A11.P5 + M-A11.P8 | Pending |
| MODE-06 | M-A11 | M-A11.P6 | Pending |
| MODE-07 | M-A11 | M-A11.P7 | Pending |
| MCP-B-01 | M-A12 | M-A12.P1 + M-A12.P7 | Pending |
| MCP-B-02 | M-A12 | M-A12.P2 | Pending |
| MCP-B-03 | M-A12 | M-A12.P2 | Pending |
| MCP-B-04 | M-A12 | M-A12.P4 | Pending |
| MCP-B-05 | M-A12 | M-A12.P5 | Pending |
| MCP-B-06 | M-A12 | M-A12.P3 + M-A13.P8 | Pending |
| MCP-T-01 | M-A13 | M-A13.P1 + M-A13.P7 | Pending |
| MCP-T-02 | M-A13 | M-A13.P2 | Pending |
| MCP-T-03 | M-A13 | M-A13.P2 | Pending |
| MCP-T-04 | M-A13 | M-A13.P3 | Pending |
| MCP-T-05 | M-A13 | M-A13.P4 + M-A18.P5 | Pending |
| MCP-T-06 | M-A13 | M-A13.P5 | Pending |
| BLD-01 | M-A14 | M-A14.P2 + M-A14.P3 | Pending |
| BLD-02 | M-A14 | M-A14.P1 | Pending |
| BLD-03 | M-A14 | M-A14.P4 | Pending |
| BLD-04 | M-A14 | M-A14.P5 | Pending |
| BLD-05 | M-A14 | M-A14.P6 | Pending |
| BLD-06 | M-A14 | M-A14.P7 | Pending |
| BLD-07 | M-A14 | M-A14.P8 | Pending |
| BLD-08 | M-A14 | M-A14.P9 | Pending |
| BLD-09 | M-A14 | M-A14.P4 | Pending |
| CMD-01 | M-A15 | M-A15.P1 | Pending |
| CMD-02 | M-A15 | M-A15.P2 | Pending |
| CMD-03 | M-A15 | M-A15.P4 | Pending |
| CMD-04 | M-A15 | M-A15.P5 + M-A15.P9 | Pending |
| CMD-05 | M-A15 | M-A15.P6 | Pending |
| CMD-06 | M-A15 | M-A15.P7 | Pending |
| CMD-07 | M-A15 | M-A15.P3 | Pending |
| CMD-08 | M-A15 | M-A14.P10 + M-A15.P8 | Pending |
| PORT-01 | M-A16 | M-A16.P1 | Pending |
| PORT-02 | M-A16 | M-A16.P2 | Pending |
| PORT-03 | M-A16 | M-A16.P3 | Pending |
| PORT-04 | M-A16 | M-A16.P4 | Pending |
| PORT-05 | M-A16 | M-A16.P5 | Pending |
| PORT-06 | M-A16 | M-A16.P6 | Pending |
| PORT-07 | M-A16 | M-A16.P7 | Pending |
| PORT-08 | M-A16 | M-A16.P7 | Pending |
| PORT-09 | M-A16 | M-A16.P8 | Pending |
| PORT-10 | M-A16 | M-A16.P9 | Pending |
| PORT-11 | M-A16 | M-A16.P9 | Pending |
| PORT-12 | M-A16 | M-A16.P10 | Pending |
| PORT-13 | M-A16 | M-A16.P10 | Pending |
| PORT-14 | M-A16 | M-A16.P11 | Pending |
| PORT-15 | M-A16 | M-A16.P11 | Pending |
| PORT-16 | M-A16 | M-A16.P11 | Pending |
| PORT-17 | M-A16 | M-A16.P12 | Pending |
| PORT-18 | M-A16 | M-A16.P12 | Pending |
| PORT-19 | M-A16 | M-A16.P12 | Pending |
| PORT-20 | M-A16 | M-A16.P12 | Pending |
| PORT-21 | M-A16 | M-A16.P12 | Pending |
| PORT-22 | M-A16 | M-A16.P12 | Pending |
| PORT-23 | M-A16 | M-A16.P13 | Pending |
| PORT-24 | M-A16 | M-A16.P13 | Pending |
| PORT-25 | M-A16 | M-A16.P13 | Pending |
| PORT-26 | M-A16 | M-A16.P13 | Pending |
| PORT-27 | M-A16 | M-A16.P14 | Pending |
| PORT-28 | M-A16 | M-A16.P14 | Pending |
| PORT-29 | M-A16 | M-A16.P14 | Pending |
| PORT-30 | M-A16 | M-A16.P14 | Pending |
| B-TUI-01 | M-A17 | M-A17.P1 + M-A17.P2 + M-A17.P6 + M-A17.P7 | Pending |
| B-TUI-02 | M-A17 | M-A17.P3 | Pending |
| B-TUI-03 | M-A17 | M-A17.P4 | Pending |
| B-TUI-04 | M-A17 | M-A17.P5 | Pending |
| TCH-01 | M-A18 | M-A18.P1 + M-A18.P2 | Pending |
| TCH-02 | M-A18 | M-A18.P3 | Pending |
| TCH-03 | M-A18 | M-A18.P4 | Pending |
| TCH-04 | M-A18 | M-A18.P7 | Pending |
| TCH-05 | M-A18 | M-A18.P9 | Pending |
| TCH-06 | M-A18 | M-A18.P8 | Pending |
| TCH-07 | M-A18 | M-A18.P5 + M-A18.P10 | Pending |
| TCH-08 | M-A18 | M-A18.P6 | Pending |
| DRL-01 | M-A19 | M-A19.P2 | Pending |
| DRL-02 | M-A19 | M-A19.P5 + M-A19.P7 | Pending |
| DRL-03 | M-A19 | M-A19.P4 | Pending |
| DRL-04 | M-A19 | M-A19.P2 + M-A19.P3 | Pending |
| DRL-05 | M-A19 | M-A19.P1 + M-A19.P6 | Pending |
| DRL-06 | M-A19 | M-A19.P8 | Pending |
| MODE-P-01 | M-A20 | M-A20.P2 | Pending |
| MODE-S-01 | M-A20 | M-A20.P3 | Pending |
| MODE-SO-01 | M-A20 | M-A20.P4 | Pending |
| MODE-C-01 | M-A20 | M-A20.P5 | Pending |
| MODE-SEL-01 | M-A20 | M-A20.P6 | Pending |
| MODE-SEL-02 | M-A20 | M-A20.P7 | Pending |
| MODE-SEL-03 | M-A20 | M-A20.P8 | Pending |
| PER-01 | M-A21 | M-A21.P1 + M-A21.P2 | Pending |
| PER-02 | M-A21 | M-A21.P3 | Pending |
| PER-03 | M-A21 | M-A21.P4 + M-A21.P5 | Pending |
| PER-04 | M-A21 | M-A21.P6 | Pending |
| SCA-01 | M-A22 | M-A22.P1 | Pending |
| SCA-02 | M-A22 | M-A22.P2 | Pending |
| SCA-03 | M-A22 | M-A22.P3 | Pending |
| CPT-01 | M-A22 | M-A22.P4 | Pending |
| CPT-02 | M-A22 | M-A22.P5 | Pending |
| CPT-03 | M-A22 | M-A22.P6 | Pending |
| CPT-04 | M-A22 | M-A22.P7 | Pending |
| T-TUI-01 | M-A23 | M-A23.P1 + M-A23.P2 + M-A23.P3 | Pending |
| T-TUI-02 | M-A23 | M-A23.P4 | Pending |
| T-TUI-03 | M-A23 | M-A23.P5 | Pending |
| T-TUI-04 | M-A23 | M-A23.P6 | Pending |
| SUB-01 | M-A24 | M-A24.P2 + M-A24.P3 | Pending |
| SUB-02 | M-A24 | M-A24.P2 + M-A24.P3 + M-A24.P4 + M-A24.P5 | Pending |
| SUB-03 | M-A24 | M-A24.P5 + M-A24.P6 | Pending |
| SUB-04 | M-A24 | M-A24.P1 + M-A24.P7 | Pending |
| MIG-01 | M-A25 | M-A25.P1 + M-A25.P7 | Pending |
| MIG-02 | M-A25 | M-A25.P2 + M-A25.P5 | Pending |
| MIG-03 | M-A25 | M-A25.P3 | Pending |
| MIG-04 | M-A25 | M-A25.P4 | Pending |
| PORT-SHIM-01 | M-A26 | M-A26.P3 | Pending |
| PORT-SHIM-02 | M-A26 | M-A26.P4 | Pending |
| PORT-SHIM-03 | M-A26 | M-A26.P5 | Pending |
| PORT-SHIM-04 | M-A26 | M-A26.P1 + M-A26.P2 | Pending |
| REL-01 | M-A27 | M-A27.P1 | Pending |
| REL-02 | M-A27 | M-A27.P2 | Pending |
| REL-03 | M-A27 | M-A27.P3 | Pending |
| REL-04 | M-A27 | M-A27.P4 | Pending |
| REL-05 | M-A27 | M-A27.P5 | Pending |
| REL-06 | M-A27 | M-A27.P6 | Pending |
| DOC-01 | M-A27 | M-A27.P7 | Pending |
| DOC-02 | M-A27 | M-A27.P7 | Pending |
| DOC-03 | M-A27 | M-A27.P7 | Pending |
| DOC-04 | M-A27 | M-A27.P7 | Pending |
| DOC-05 | M-A27 | M-A27.P7 | Pending |
| DOC-06 | M-A27 | M-A27.P7 | Pending |
| DOC-07 | M-A27 | M-A27.P7 | Pending |
| DOC-08 | M-A27 | M-A27.P7 + M-A26.P8 | Pending |
| TST-01 | M-A27 | M-A27.P8 | Pending |
| TST-02 | M-A27 | M-A27.P8 + M-A5.P9 | Pending |
| TST-03 | M-A27 | M-A27.P8 + M-A1.P10 | Pending |
| TST-04 | M-A27 | M-A27.P8 | Pending |
| TST-05 | M-A27 | M-A27.P8 + M-A3.P9 + M-A26.P7 | Pending |
| TST-06 | M-A27 | M-A27.P8 + M-A2.P12 | Pending |
| TST-07 | M-A27 | M-A27.P8 + M-A11.P6 | Pending |
| TST-08 | M-A27 | M-A27.P8 + M-A11.P9 | Pending |
| OBS-01 | M-A27 | M-A27.P9 + M-A6.P7 + M-A7.P7 | Pending |
| OBS-02 | M-A27 | M-A27.P9 + M-A2.P10 | Pending |
| OBS-03 | M-A27 | M-A27.P9 | Pending |
| OBS-04 | M-A27 | M-A27.P9 | Pending |
| SEC-01 | M-A27 | M-A27.P10 + M-A14.P9 | Pending |
| SEC-02 | M-A27 | M-A27.P10 + M-A14.P9 | Pending |
| SEC-03 | M-A27 | M-A27.P10 + M-A14.P9 | Pending |
| SEC-04 | M-A27 | M-A27.P10 | Pending |
| SEC-05 | M-A27 | M-A27.P10 | Pending |
| SEC-06 | M-A27 | M-A27.P10 + M-A2.P2 | Pending |

**Coverage target:** every v1 REQ-ID must map to exactly one Phase within its named Arc. Unmapped REQ-IDs = roadmap gap.

**Coverage status:** 221/221 (100%) — no orphans, no gaps.

*Note on "multiple phase" entries:* Some requirements are intentionally threaded across multiple phases (e.g., AUTH-07 land in M-A2.P3 for lock primitive + M-A6.P10 for runtime wiring). The **primary owning phase** is the first listed; the others are integration/wiring downstream. Each phase's success criteria include a verifier for its portion of the requirement.

---

*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 after roadmap creation (traceability populated)*
