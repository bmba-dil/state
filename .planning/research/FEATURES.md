# Feature Landscape — Exhaustive Inventory

**Domain:** Fusion agentic state-machine (build + teach) on opencode host
**Researched:** 2026-04-22
**Scope:** Every feature from GSD, AOL, GSD-2pi, and cross-compatible skills, with port/redesign/drop disposition

This is an **inventory document**, not a summary. Every row is a candidate Arc/Phase/Slice input for the roadmapper. Under-inventorying is the failure mode; duplication across sections is expected when the same capability touches multiple axes.

Disposition legend:

- **port** — carry over the capability essentially as-is (semantics, not files)
- **redesign** — keep the intent, rebuild against state's architecture (Python, DAG, opencode hooks, Arc→Phase→Slice→Step)
- **drop** — do not build; rationale captured inline
- **new** — not present in source, introduced by state

Complexity legend: **S** (≤1 Slice), **M** (1 Phase), **L** (1 Arc), **XL** (cross-Arc initiative).

---

## 1. GSD Commands (slash-command inventory)

Source: `state-inputs/get-shit-done/commands/gsd/*.md` (85 files enumerated).

In state these are not "slash commands" — most become **Step workflows** inside the build-mode kernel, exposed to the user via opencode slash commands (`/state:build:*`) that the plugin-shim installs. The command filename is retained below only as a stable identifier.

### 1.1 Project / Milestone lifecycle

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| new-project | commands/gsd/new-project.md | redesign | L | Arc: Build-Mode Project Bootstrap | Rebuilds against four-tier hierarchy (Arc→Phase→Slice→Step) and DAG roadmap. Discussion → research → requirements → roadmap flow preserved; PROJECT.md shape kept but adds Arc-level sections. |
| new-milestone | commands/gsd/new-milestone.md | redesign | M | Arc: Build-Mode Project Bootstrap | Brownfield entry. In state "milestone" = "Arc". Invokes same research/requirements/roadmap subflow but appends a new Arc to an existing roadmap DAG. |
| complete-milestone | commands/gsd/complete-milestone.md | redesign | M | Arc: Build-Mode Lifecycle & Ship | Audit → archive → CHANGELOG → PROJECT.md evolution. In state, operates on Arcs, triggers a cross-tier verifier rollup. |
| plan-milestone-gaps | commands/gsd/plan-milestone-gaps.md | redesign | S | Arc: Build-Mode Verification | Derives a gap-closure Arc from verifier failures. Fits naturally into the gap-closure Slice pattern. |
| milestone-summary | commands/gsd/milestone-summary.md | port | S | Arc: Build-Mode Reporting | Read-only summary over completed Arc. |
| audit-milestone | commands/gsd/audit-milestone.md | redesign | M | Arc: Build-Mode Verification | Cross-Arc audit. Becomes a Phase-level verifier that rolls up Slice verifiers. |
| audit-uat | commands/gsd/audit-uat.md | redesign | M | Arc: Build-Mode Verification | Scans `*-UAT.md` / `*-VERIFICATION.md` across phases. Reimplement against state's new artifact paths. |
| audit-fix | commands/gsd/audit-fix.md | redesign | S | Arc: Build-Mode Verification | Auto-queue gap-closure Steps when audit finds issues. |

### 1.2 Phase workflow (core discuss/plan/execute/verify cycle)

In state, the full cycle lives at the **Step** tier (not the Phase tier). Each of these commands becomes a Step workflow in build-mode.

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| discuss-phase | commands/gsd/discuss-phase.md | redesign | L | Arc: Build-Mode Discuss Step | Adaptive questioning to surface gray areas; writes CONTEXT.md. In state: the "discuss" sub-step of a Step. Must integrate opencode `question` tool. Has four sub-modes (`--all`, `--auto`, `--chain`, `--power`) — keep all four. |
| list-phase-assumptions | commands/gsd/list-phase-assumptions.md | redesign | S | Arc: Build-Mode Discuss Step | Extracts assumptions from CONTEXT.md. Becomes a helper inside discuss step. |
| plan-phase | commands/gsd/plan-phase.md | redesign | L | Arc: Build-Mode Plan Step | Researcher → planner → plan-checker iterative loop. In state: the "plan" sub-step. Must support `--gaps`, `--prd`, `--reviews`, `--text`, `--tdd`, `--research`, `--skip-research`, `--skip-verify` flags. |
| ultraplan-phase | commands/gsd/ultraplan-phase.md | redesign | M | Arc: Build-Mode Plan Step | Deep-planning variant (higher-tier model, more iterations). Becomes a plan-depth config toggle. |
| insert-phase | commands/gsd/insert-phase.md | redesign | S | Arc: Build-Mode Roadmap CRUD | Roadmap DAG edit — insert Phase (or Slice) at a specific position with dependency rewiring. |
| add-phase | commands/gsd/add-phase.md | redesign | S | Arc: Build-Mode Roadmap CRUD | Append Phase/Slice. In a DAG world this is just "add node + edge(s)". |
| remove-phase | commands/gsd/remove-phase.md | redesign | S | Arc: Build-Mode Roadmap CRUD | Delete node + rewire deps; block if downstream work exists. |
| research-phase | commands/gsd/research-phase.md | redesign | M | Arc: Build-Mode Research Infrastructure | Standalone researcher. Becomes a reusable sub-step callable from plan-step or directly. |
| spec-phase | commands/gsd/spec-phase.md | redesign | M | Arc: Build-Mode Plan Step | Produces a tight spec artifact before planning. Keep as an alt-entry for plan-step. |
| secure-phase | commands/gsd/secure-phase.md | redesign | M | Arc: Build-Mode Security Verification | Security audit gate. In state: optional Slice-level verifier. |
| validate-phase | commands/gsd/validate-phase.md | redesign | S | Arc: Build-Mode Verification | Quick validation before execution. |
| execute-phase | commands/gsd/execute-phase.md | redesign | XL | Arc: Build-Mode Execute Step + DAG Scheduler | Wave-based parallelization maps directly to the state DAG scheduler. `--wave N`, `--gaps-only`, `--interactive`, `--tdd` flags all survive. This is the single biggest redesign — from "waves within a phase" to "unblocked Slices/Steps across the DAG." |
| verify-work | commands/gsd/verify-work.md | redesign | L | Arc: Build-Mode Verify Step | Conversational UAT. In state: Step verifier + Slice rollup. Produces `*-VERIFICATION.md`. |
| add-tests | commands/gsd/add-tests.md | redesign | S | Arc: Build-Mode Verification | Back-fill tests for an already-shipped Slice. |
| ai-integration-phase | commands/gsd/ai-integration-phase.md | redesign | M | Arc: Build-Mode AI Integration | Specialized phase template for AI-feature work. Keep as a Phase template. |
| ui-phase | commands/gsd/ui-phase.md | redesign | M | Arc: Build-Mode UI Phase | UI-specialized phase template (ties into ui-researcher, ui-checker, ui-auditor). |
| ui-review | commands/gsd/ui-review.md | redesign | S | Arc: Build-Mode UI Phase | UI-focused review step. |
| code-review | commands/gsd/code-review.md | redesign | M | Arc: Build-Mode Review & Ship | Cross-AI code review. Becomes a Slice-level verifier callable from ship Step. |
| code-review-fix | commands/gsd/code-review-fix.md | redesign | S | Arc: Build-Mode Review & Ship | Applies review feedback. Generates fix Steps. |
| eval-review | commands/gsd/eval-review.md | redesign | S | Arc: Build-Mode Eval Infrastructure | Post-hoc eval of a completed task. Requires the eval-planner/eval-auditor subagents (see §3). |
| ship | commands/gsd/ship.md | redesign | M | Arc: Build-Mode Review & Ship | PR creation + review + merge tracking. Becomes a terminal Step; integrates opencode `vcs` events. |
| pr-branch | commands/gsd/pr-branch.md | redesign | S | Arc: Build-Mode Review & Ship | Branch management helper. Integrates with opencode worktree service. |

### 1.3 Quick / ad-hoc / autonomy

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| quick | commands/gsd/quick.md | redesign | M | Arc: Build-Mode Quick Tasks | Short-path Step execution with composable `--discuss`/`--research`/`--validate`/`--full` flags. `.planning/quick/` becomes `.state/quick/`. List/status/resume subcommands keep their semantics. |
| fast | commands/gsd/fast.md | redesign | S | Arc: Build-Mode Quick Tasks | Even shorter path than quick. Merge with quick as a `--fast` preset. |
| do | commands/gsd/do.md | redesign | S | Arc: Build-Mode Quick Tasks | Alias/convenience; fold into quick. |
| autonomous | commands/gsd/autonomous.md | redesign | L | Arc: Build-Mode Autonomous Runner | Runs all remaining Phases discuss→plan→execute with minimal interaction. In state: honors DAG concurrency; pauses for gray areas, blockers, validations. `--from N`, `--to N`, `--only N`, `--interactive` preserved. |
| manager | commands/gsd/manager.md | redesign | M | Arc: Build-Mode Autonomous Runner | Higher-level orchestrator across Arcs. In DAG mode, this is the default top-level runner. |
| next | commands/gsd/next.md | redesign | S | Arc: Build-Mode Navigation | "What should I do next?" — DAG-aware next-unblocked-Step picker. |
| explore | commands/gsd/explore.md | redesign | S | Arc: Build-Mode Discovery | Free-form exploration mode (no Step). Keep for ad-hoc codebase Q&A. |
| sketch | commands/gsd/sketch.md | redesign | M | Arc: Build-Mode Sketches & Spikes | Rapid prototyping mode. Produces disposable artifacts outside the DAG. |
| sketch-wrap-up | commands/gsd/sketch-wrap-up.md | redesign | S | Arc: Build-Mode Sketches & Spikes | Terminates a sketch, promotes learnings. |
| spike | commands/gsd/spike.md | redesign | M | Arc: Build-Mode Sketches & Spikes | Time-boxed research with code. Produces learnings, not shipped features. |
| spike-wrap-up | commands/gsd/spike-wrap-up.md | redesign | S | Arc: Build-Mode Sketches & Spikes | Finalize a spike. |
| plant-seed | commands/gsd/plant-seed.md | redesign | S | Arc: Build-Mode Inbox / Seeds | Capture half-formed idea for later. |

### 1.4 State / navigation / visibility

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| progress | commands/gsd/progress.md | redesign | S | Arc: Build-Mode Dashboards | "Where am I?" rollup. In state: reads from SQLite event store. |
| stats | commands/gsd/stats.md | redesign | S | Arc: Build-Mode Dashboards | Session/project stats. |
| health | commands/gsd/health.md | redesign | S | Arc: Build-Mode Health & Self-Check | Config + artifact sanity check. Integrates with audit-open + canonical artifact registry. |
| session-report | commands/gsd/session-report.md | redesign | S | Arc: Build-Mode Reporting | Per-session report. Uses event store. |
| review | commands/gsd/review.md | redesign | S | Arc: Build-Mode Review & Ship | General review entry. |
| review-backlog | commands/gsd/review-backlog.md | redesign | S | Arc: Build-Mode Backlog & TODOs | Backlog triage. |
| check-todos | commands/gsd/check-todos.md | redesign | S | Arc: Build-Mode Backlog & TODOs | `.planning/todos/` walker. Merges with opencode todo tool. |
| list-workspaces | commands/gsd/list-workspaces.md | redesign | S | Arc: Build-Mode Workstreams / Worktrees | In state, "workspace" = "workstream" + worktree. List workstreams across the project. |
| new-workspace | commands/gsd/new-workspace.md | redesign | S | Arc: Build-Mode Workstreams / Worktrees | Parallel milestones (= Arcs) under workstream namespacing. |
| remove-workspace | commands/gsd/remove-workspace.md | redesign | S | Arc: Build-Mode Workstreams / Worktrees | Complete/archive a workstream. |
| workstreams | commands/gsd/workstreams.md | redesign | M | Arc: Build-Mode Workstreams / Worktrees | list/create/status/switch/progress/complete/resume subcommands — all preserved. Physical layout shifts from `.planning/workstreams/{name}/` to `.state/workstreams/{name}/`. |
| pause-work | commands/gsd/pause-work.md | redesign | S | Arc: Build-Mode Session Continuity | Persist session state explicitly. In state: event-log checkpoint. |
| resume-work | commands/gsd/resume-work.md | redesign | S | Arc: Build-Mode Session Continuity | Restore a paused session. Uses event replay. |

### 1.5 Context / intel / knowledge

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| intel | commands/gsd/intel.md | redesign | M | Arc: Build-Mode Codebase Intelligence | query/status/diff/refresh subcommands over file-roles/api-map/dependency-graph/arch-decisions/stack JSONs. Port semantics, rebuild storage against `.state/intel/`. |
| map-codebase | commands/gsd/map-codebase.md | redesign | M | Arc: Build-Mode Codebase Intelligence | Seeds intel. Integrates with opencode's LSP events. |
| graphify | commands/gsd/graphify.md | redesign | L | Arc: Build-Mode Knowledge Graph | Project knowledge graph with build/query/status/diff. Config-gated. Becomes a standalone Arc because of scope (Kuzu/DuckDB-style embedded graph DB). |
| ingest-docs | commands/gsd/ingest-docs.md | redesign | M | Arc: Build-Mode Knowledge Graph | Bring external docs into intel/graph. |
| docs-update | commands/gsd/docs-update.md | redesign | M | Arc: Build-Mode Docs Generation | Auto-generate/refresh project docs. Uses `gsd-doc-*` subagent lineage. |
| update | commands/gsd/update.md | redesign | S | Arc: Build-Mode Self-Update | Self-update of the state toolchain. Delegates to OS package manager + `state-daemon` reload. |
| inbox | commands/gsd/inbox.md | redesign | S | Arc: Build-Mode Inbox / Seeds | Triage captured ideas. |
| import | commands/gsd/import.md | redesign | S | Arc: Build-Mode Migration & Import | Generic import of external plans. |
| from-gsd2 | commands/gsd/from-gsd2.md | drop | S | — | Explicit backport path for GSD-2 `.gsd/` → GSD-1 `.planning/`. State is a greenfield rebuild; back-migration to legacy GSD is out of scope. A forward importer from GSD `.planning/` → state `.state/` is table stakes (see §11 Table Stakes) but is a NEW feature, not a port of this one. |

### 1.6 Roadmap / backlog / todos

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| add-backlog | commands/gsd/add-backlog.md | redesign | S | Arc: Build-Mode Backlog & TODOs | Add to BACKLOG.md. |
| add-todo | commands/gsd/add-todo.md | redesign | S | Arc: Build-Mode Backlog & TODOs | Add to `.state/todos/pending/`. |
| note | commands/gsd/note.md | redesign | S | Arc: Build-Mode Backlog & TODOs | Lightweight note capture. |
| thread | commands/gsd/thread.md | redesign | M | Arc: Build-Mode Threads & Context | Cross-session knowledge threads: list/close/status/resume/create. Port directly — fits naturally in the event store. |
| analyze-dependencies | commands/gsd/analyze-dependencies.md | redesign | M | Arc: Build-Mode DAG Tooling | Dependency analysis over plan artifacts. In DAG world, this becomes a first-class scheduler pre-flight. |

### 1.7 Debug / forensics

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| debug | commands/gsd/debug.md | redesign | L | Arc: Build-Mode Debugger | Scientific-method debugger with persistent session state, hypothesis testing, checkpoints. Fits event-sourcing natively. |
| forensics | commands/gsd/forensics.md | redesign | M | Arc: Build-Mode Forensics | Post-mortem over git + `.state/` + event log. Central driver for event replay. |

### 1.8 Profiling / personalization

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| profile-user | commands/gsd/profile-user.md | redesign | M | Arc: Build-Mode User Profile | Scans prior sessions (opencode SyncEvent store) to infer user preferences. Replaces `.claude/projects/` scan with opencode equivalent. |
| set-profile | commands/gsd/set-profile.md | redesign | S | Arc: Build-Mode User Profile | Select active model profile (quality/balanced/budget/adaptive). |
| extract_learnings | commands/gsd/extract_learnings.md | redesign | S | Arc: Build-Mode Learnings Store | Extract learnings from a session into `~/.state/knowledge/` (mirrors `~/.gsd/knowledge/`). |
| settings | commands/gsd/settings.md | redesign | S | Arc: Build-Mode Config | Interactive config editor. Backed by state's pydantic config schema. |

### 1.9 Help / onboarding / misc

| Name | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| help | commands/gsd/help.md | redesign | S | Arc: Build-Mode Onboarding | Surface state's command map. |
| scan | commands/gsd/scan.md | redesign | S | Arc: Build-Mode Codebase Intelligence | One-shot codebase scan (lighter than map-codebase). |
| cleanup | commands/gsd/cleanup.md | redesign | S | Arc: Build-Mode Health & Self-Check | Clean stale temp/lock files. |
| undo | commands/gsd/undo.md | redesign | M | Arc: Build-Mode Snapshots & Revert | Revert the last Step/Slice. Implemented via snapshots (opencode `snapshot` service). |
| reapply-patches | commands/gsd/reapply-patches.md | redesign | M | Arc: Build-Mode Snapshots & Revert | Re-apply saved patch set; used after forced rebases. |
| plan-review-convergence | commands/gsd/plan-review-convergence.md | redesign | S | Arc: Build-Mode Plan Step | Converge plan-check feedback. |
| sync-skills | commands/gsd/sync-skills.md | redesign | S | Arc: Opencode Integration — Skills | Sync `.state/skills/` with opencode's skill scanner. |
| join-discord | commands/gsd/join-discord.md | drop | — | — | Community vanity link. Out of scope. |

**Command summary:** 85 GSD commands inventoried — 82 redesign, 2 drop, 0 port-as-is (intent is preserved everywhere; surface changes). Every redesign row is a candidate Slice or Step workflow.

---

## 2. GSD State-Machine Modules (bin/lib/*.cjs)

Source: `state-inputs/get-shit-done/get-shit-done/bin/lib/` (26 `.cjs` files). Each module is a logical responsibility that needs a Python home in state.

| Module | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| core.cjs | bin/lib/core.cjs | redesign | L | Arc: State Kernel — Core Utilities | Path helpers, project-root detection, lock file management, config loader, shared constants. Target: `state/core/paths.py`, `state/core/locks.py`, `state/core/config.py`. Multi-repo / sub-repo detection is a first-class concern from day one. |
| state.cjs | bin/lib/state.cjs | redesign | L | Arc: State Kernel — STATE Projection | STATE.md operations — read/write/get/set field. In state, STATE.md is a *projection* of the SQLite event log; most direct writes become event emissions. Target: `state/events/projection/state_md.py`. |
| commands.cjs | bin/lib/commands.cjs | redesign | M | Arc: State Kernel — Standalone Utilities | Slug generation, timestamps, todo listing, phase-status derivation. Target: `state/core/commands.py`. Phase-status determination (Complete/Needs Review/Executed/In Progress/Planned) is the semantic unit — port faithfully. |
| phase.cjs | bin/lib/phase.cjs | redesign | L | Arc: Build-Mode Planning Hierarchy | Phase CRUD. In state, this splits four ways: Arc-CRUD, Phase-CRUD, Slice-CRUD, Step-CRUD. Biggest semantic change in the whole port. |
| milestone.cjs | bin/lib/milestone.cjs | redesign | M | Arc: Build-Mode Planning Hierarchy | Milestone/requirements lifecycle. Milestone=Arc. Requirement mark-complete logic (REQ-ID regex ops) ports directly. |
| roadmap.cjs | bin/lib/roadmap.cjs | redesign | L | Arc: Build-Mode Planning Hierarchy | Roadmap parsing and update. In state, ROADMAP.md is a DAG projection; editors must preserve dep edges. |
| workstream.cjs | bin/lib/workstream.cjs | redesign | M | Arc: Build-Mode Workstreams / Worktrees | Flat → namespaced layout migration. Rebuild against `.state/workstreams/`. Per-workstream ROADMAP/STATE/REQUIREMENTS/phases preserved. |
| artifacts.cjs | bin/lib/artifacts.cjs | redesign | S | Arc: Build-Mode Health & Self-Check | Canonical artifact registry. Port as-is — just extend exact-match set to state's artifacts (add Arc/Phase/Slice/Step files). |
| audit.cjs | bin/lib/audit.cjs | redesign | M | Arc: Build-Mode Verification | Cross-type open-item scanner (debug sessions, UAT, threads). Port against new paths. |
| config.cjs | bin/lib/config.cjs | redesign | M | Arc: State Kernel — Config | Planning config CRUD with key validation + suggestions. Target: pydantic config model. |
| config-schema.cjs | bin/lib/config-schema.cjs | redesign | S | Arc: State Kernel — Config | VALID_CONFIG_KEYS source of truth. In state: pydantic schema fields ARE the keys. |
| docs.cjs | bin/lib/docs.cjs | redesign | M | Arc: Build-Mode Docs Generation | Docs-init signal collector + GSD marker detection. Ports into docs-update workflow. |
| frontmatter.cjs | bin/lib/frontmatter.cjs | redesign | M | Arc: State Kernel — Markdown I/O | YAML frontmatter parser/serializer with inline-array handling. Replace with `python-frontmatter` + custom inline-array helpers. |
| graphify.cjs | bin/lib/graphify.cjs | redesign | M | Arc: Build-Mode Knowledge Graph | Graph build/query subprocess wrapper; config-gated. Rebuild against Python graph library. |
| gsd2-import.cjs | bin/lib/gsd2-import.cjs | drop | — | — | Reverse migration GSD-2 → GSD-1. Not relevant to state. Forward importer GSD-1 → state is a new feature. |
| init.cjs | bin/lib/init.cjs | redesign | M | Arc: State Kernel — Workflow Bootstrap | Compound init commands that feed workflow orchestrators. Port as `state/init/*.py`. Inject project_root + agents-installed + response_language into init outputs. |
| intel.cjs | bin/lib/intel.cjs | redesign | M | Arc: Build-Mode Codebase Intelligence | JSON intel store (file-roles/api-map/dep-graph/arch-decisions/stack). Port against `.state/intel/`. |
| learnings.cjs | bin/lib/learnings.cjs | redesign | M | Arc: Build-Mode Learnings Store | Global `~/.gsd/knowledge/` store → `~/.state/knowledge/`. Content-hash dedup, per-project provenance. Port as-is. |
| model-profiles.cjs | bin/lib/model-profiles.cjs | redesign | M | Arc: Provider Routing & Model Profiles | Agent→model mapping per profile (quality/balanced/budget/adaptive). In state: profiles live in config, resolution runs through litellm + opencode `chat.params`. |
| profile-output.cjs | bin/lib/profile-output.cjs | redesign | M | Arc: Build-Mode User Profile | Render analysis → USER-PROFILE.md, AGENTS.md managed sections, dev-preferences.md. Ports against AGENTS.md (opencode's equivalent of CLAUDE.md). |
| profile-pipeline.cjs | bin/lib/profile-pipeline.cjs | redesign | M | Arc: Build-Mode User Profile | Session scanning + message extraction + recency-weighted sampling. Replace `~/.claude/projects/` scan with opencode SyncEvent store reads. |
| schema-detect.cjs | bin/lib/schema-detect.cjs | redesign | S | Arc: Build-Mode Verification | ORM schema drift detection (Prisma/Drizzle/Payload etc.). Port patterns as-is. |
| security.cjs | bin/lib/security.cjs | redesign | M | Arc: State Kernel — Security | Path traversal + prompt-injection + shell-metachar + JSON + regex-DoS guards. Port all defenses; they're a safety floor, not an option. |
| template.cjs | bin/lib/template.cjs | redesign | M | Arc: Build-Mode Templates | Template selection heuristics + fill. Port; templates themselves get rewritten for the four-tier hierarchy. |
| uat.cjs | bin/lib/uat.cjs | redesign | S | Arc: Build-Mode Verification | Cross-phase UAT scanner. Port. |
| verify.cjs | bin/lib/verify.cjs | redesign | L | Arc: Build-Mode Verification | Verification suite — summary verify, consistency, file-existence spot-check, commit-log check, mandatory-must-have parsing. Biggest logical target for the Step/Slice verifier tier. |

**Module summary:** 26 modules inventoried. 25 redesign (Python-native), 1 drop (gsd2-import). Top-3 weight: verify.cjs, state.cjs, phase.cjs — each easily a full Arc of work.

### Behavioral-intent clusters (for roadmap consumption)

When the roadmapper shapes Arcs, these logical clusters matter more than the per-file list:

1. **Event-sourced state projection** — state.cjs + event emitter + SQLite store + opencode SyncEvent dual-write. (→ Arc: State Kernel — Event Store)
2. **Planning-hierarchy CRUD** — phase.cjs + milestone.cjs + roadmap.cjs + workstream.cjs redesigned for Arc→Phase→Slice→Step with DAG edges. (→ Arc: Build-Mode Planning Hierarchy)
3. **Verification suite** — verify.cjs + uat.cjs + audit.cjs + schema-detect.cjs — the goal-backward verifier tier that state needs at Step, Slice, Phase, Arc, and cross-tier levels. (→ Arc: Build-Mode Verification)
4. **Security baseline** — security.cjs — a cross-cutting concern; its own Slice early in the kernel Arc.
5. **User profiling** — profile-pipeline.cjs + profile-output.cjs + related agents (→ Arc: Build-Mode User Profile)
6. **Knowledge & intel** — intel.cjs + graphify.cjs + learnings.cjs (→ Arc: Build-Mode Codebase Intelligence + Arc: Build-Mode Knowledge Graph)
7. **Config + markdown I/O** — config.cjs + config-schema.cjs + frontmatter.cjs (→ Arc: State Kernel — Config + Arc: State Kernel — Markdown I/O)

---

## 3. GSD Subagents (agents/*.md)

Source: `state-inputs/get-shit-done/agents/` (32 files).

**Translation rule (from opencode-integration-analysis.md):** In opencode, "subagents" are in-process agents defined in `opencode.json` under `agent.<name>` with `mode: "subagent"`, each with their own `prompt`, `model`, `permission` rules. Some GSD subagents become opencode subagents. Others that do batch work the LLM shouldn't see can become **MCP tools** on `state-build` / `state-teach`. A few collapse into Python code (no LLM required).

| Subagent | Source path | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| gsd-planner | agents/gsd-planner.md | redesign → opencode subagent (state-build) | L | Arc: Build-Mode Plan Step | Largest prompt (46KB). Produces PLAN.md. Retain as opencode subagent; rewrite to emit Step-artifacts against new hierarchy. |
| gsd-plan-checker | agents/gsd-plan-checker.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Plan Step | Iterates with planner until plan passes. Keep. |
| gsd-roadmapper | agents/gsd-roadmapper.md | redesign → opencode subagent (state-build) | L | Arc: Build-Mode Project Bootstrap | Derives Phases from requirements; in state, also derives Arcs and Slices and DAG edges. Must output `depends_on` graph. |
| gsd-executor | agents/gsd-executor.md | redesign → opencode subagent (state-build) | L | Arc: Build-Mode Execute Step | Runs a plan atomically (per-task commits). In state: runs a single Step. Multiple executor invocations run concurrently when DAG allows. |
| gsd-verifier | agents/gsd-verifier.md | redesign → opencode subagent (state-build) | L | Arc: Build-Mode Verification | Goal-backward verifier. Keep the adversarial stance verbatim; rebind artifacts to state's tier. |
| gsd-debugger | agents/gsd-debugger.md | redesign → opencode subagent (state-build) | L | Arc: Build-Mode Debugger | 46KB prompt. Scientific-method debugger. Keep. |
| gsd-debug-session-manager | agents/gsd-debug-session-manager.md | redesign → MCP tool (state-build) | M | Arc: Build-Mode Debugger | Debug-state CRUD. No LLM needed — pure bookkeeping over `.state/debug/`. |
| gsd-code-reviewer | agents/gsd-code-reviewer.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Review & Ship | Code review. Keep. |
| gsd-code-fixer | agents/gsd-code-fixer.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Review & Ship | Applies reviewer feedback. Keep. |
| gsd-project-researcher | agents/gsd-project-researcher.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Research Infrastructure | Domain research for new project/milestone (Arc-level). Keep. |
| gsd-phase-researcher | agents/gsd-phase-researcher.md | redesign → opencode subagent (state-build) | L | Arc: Build-Mode Research Infrastructure | Phase/Slice/Step-level research. Keep. |
| gsd-research-synthesizer | agents/gsd-research-synthesizer.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Research Infrastructure | Merges parallel research outputs. Keep. |
| gsd-domain-researcher | agents/gsd-domain-researcher.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Research Infrastructure | Overlaps with project-researcher at finer grain. Consider merging. |
| gsd-ai-researcher | agents/gsd-ai-researcher.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode AI Integration | Specialized for AI-feature work (model selection, prompt strategy). Keep. |
| gsd-framework-selector | agents/gsd-framework-selector.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Research Infrastructure | Picks frameworks during research. Keep. |
| gsd-advisor-researcher | agents/gsd-advisor-researcher.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Research Infrastructure | Advisory research for architectural decisions. Keep. |
| gsd-assumptions-analyzer | agents/gsd-assumptions-analyzer.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Discuss Step | Assumption extraction. Keep. |
| gsd-codebase-mapper | agents/gsd-codebase-mapper.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Codebase Intelligence | Maps codebase to intel JSONs. Heavy grep/glob — candidate for Python-only Prelude step before subagent takes over. |
| gsd-pattern-mapper | agents/gsd-pattern-mapper.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Codebase Intelligence | Finds reusable patterns. Keep. |
| gsd-intel-updater | agents/gsd-intel-updater.md | redesign → MCP tool (state-build) | S | Arc: Build-Mode Codebase Intelligence | Intel JSON mutations. No LLM needed; pure bookkeeping. |
| gsd-integration-checker | agents/gsd-integration-checker.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Verification | Cross-Slice integration verifier. Keep. |
| gsd-nyquist-auditor | agents/gsd-nyquist-auditor.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Verification | Nyquist-style sampling audit of plan artifacts. Keep. |
| gsd-security-auditor | agents/gsd-security-auditor.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Security Verification | Security gate. Keep; pair with security.cjs baseline. |
| gsd-ui-researcher | agents/gsd-ui-researcher.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode UI Phase | UI research agent. Keep. |
| gsd-ui-checker | agents/gsd-ui-checker.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode UI Phase | UI lint/check. Keep. |
| gsd-ui-auditor | agents/gsd-ui-auditor.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode UI Phase | Goal-backward UI verifier. Keep. |
| gsd-doc-writer | agents/gsd-doc-writer.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Docs Generation | 38KB prompt. Writes markdown docs with GSD marker. Keep marker concept. |
| gsd-doc-verifier | agents/gsd-doc-verifier.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Docs Generation | Verifies generated docs. Keep. |
| gsd-doc-classifier | agents/gsd-doc-classifier.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Docs Generation | Classifies existing docs for update routing. Keep. |
| gsd-doc-synthesizer | agents/gsd-doc-synthesizer.md | redesign → opencode subagent (state-build) | S | Arc: Build-Mode Docs Generation | Synthesizes multi-source docs. Keep. |
| gsd-user-profiler | agents/gsd-user-profiler.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode User Profile | Profiles user preferences from session history. Keep. |
| gsd-eval-planner | agents/gsd-eval-planner.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Eval Infrastructure | Plans evals for a task. Keep. |
| gsd-eval-auditor | agents/gsd-eval-auditor.md | redesign → opencode subagent (state-build) | M | Arc: Build-Mode Eval Infrastructure | Audits eval results. Keep. |

**Subagent summary:** 33 subagents inventoried — 31 become opencode subagents (state-build), 2 collapse to MCP tools (debug-session-manager, intel-updater) because they do no LLM work, 0 dropped.

**Cross-cutting decision:** All 31 kept subagents need their `tools:` frontmatter translated into opencode per-agent `permission` rulesets (allow/ask/deny per tool, glob patterns) and `mcp__context7__*` mappings registered in `opencode.json` MCP config.

---

## 4. GSD Hooks (hooks/*.js / *.sh)

Source: `state-inputs/get-shit-done/hooks/` (11 files). Reimplemented as the opencode plugin-shim handlers (`@state/opencode-plugin`).

| Hook | Source path | Disposition | Complexity | Opencode hook binding | Notes |
|---|---|---|---|---|---|
| gsd-prompt-guard | hooks/gsd-prompt-guard.js | redesign | S | `tool.execute.before` (Write/Edit scoped to `.state/`) + `chat.message` | Prompt-injection pattern scanner. Keep INJECTION_PATTERNS + invisible-Unicode detection. Advisory, never block. |
| gsd-read-guard | hooks/gsd-read-guard.js | redesign | S | `tool.execute.before` (Write/Edit when target exists) | Read-before-edit nudge. Advisory. |
| gsd-read-injection-scanner | hooks/gsd-read-injection-scanner.js | redesign | S | `tool.execute.after` (Read) | Scans returned content for SUMMARISATION_PATTERNS + INJECTION_PATTERNS. Advisory. |
| gsd-workflow-guard | hooks/gsd-workflow-guard.js | redesign | S | `tool.execute.before` (Write/Edit outside `.state/`) | Nudge to use state workflows instead of raw edits. Config-gated. |
| gsd-context-monitor | hooks/gsd-context-monitor.js | redesign | S | `tool.execute.after` + TUI plugin statusline bridge | Injects context-budget warnings into the agent's own conversation (not just the user-facing statusline). Thresholds (35% WARNING / 25% CRITICAL). |
| gsd-check-update | hooks/gsd-check-update.js | redesign | S | `session.created` (via `event` hook) | Spawns background update-check worker once per session. |
| gsd-check-update-worker | hooks/gsd-check-update-worker.js | redesign | S | (background, not a hook) | Out-of-process update checker. In state: becomes a state-daemon job. |
| gsd-statusline | hooks/gsd-statusline.js | redesign | M | TUI plugin (`packages/plugin/src/tui.ts`) statusline slot | Primary statusline: model \| current task/state \| directory \| context usage. In state: renders Arc/Phase/Slice/Step tier + DAG position + context %. |
| gsd-session-state.sh | hooks/gsd-session-state.sh | redesign | S | `experimental.chat.system.transform` (session start) | Inject STATE.md head on session start. In state: drops the shell script; read SQLite projection instead. |
| gsd-validate-commit.sh | hooks/gsd-validate-commit.sh | redesign | S | `tool.execute.before` (Bash when command is `git commit`) | Conventional Commits enforcement. Config-gated. Port as pure Python. |
| gsd-phase-boundary.sh | hooks/gsd-phase-boundary.sh | redesign | S | `tool.execute.after` (Write/Edit targeting `.state/`) | Suggest STATE update when planning files change. In state: auto-emits a `state.projection.dirty` event instead of printing advisory. |

**Hook summary:** 11 hooks inventoried — all 11 redesign as opencode plugin-shim handlers. Zero drops. Expanded hook surface in state (per constraints): add bindings on `permission.ask`, `experimental.chat.messages.transform`, `experimental.session.compacting`, `chat.params`, `command.execute.before`, `shell.env`. Each expansion is a first-class Slice.

---

## 5. AOL Workflows (~/.claude/agent-of-learning/workflows/*.md)

Source: `~/.claude/agent-of-learning/workflows/` (10 files, including `_routing.md`, `_TEMPLATE.md`).

| Workflow | Source | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| _routing.md | workflows/_routing.md | redesign | M | Arc: Teach-Mode State Routing | Non-mutating `.aol/` state-detection prelude shared by teach + build + state + style. In state: replaced by a pure-Python `probe_state()` function that returns a typed dataclass; no markdown @-references. |
| _TEMPLATE.md | workflows/_TEMPLATE.md | drop | — | — | Source-format template. State uses its own template shape. |
| new.md | workflows/new.md | redesign | L | Arc: Teach-Mode Onboarding | Conversational onboarding — primary-subject pick, companion-subjects, `aol init`, dep-install per subject, env sanity, teaching-style capture, handoff to `/state:teach`. Checkpoint every step to `onboarding-progress.json`. In state: becomes `/state:teach:new`. |
| teach.md | workflows/teach.md | redesign | L | Arc: Teach-Mode Session Router | State-routed returning-teaching entry. Four branches: curriculum, resume, drill, review. In state: replaces markdown dispatch with a typed routing function; the branches become separate Step workflows. |
| build.md | workflows/build.md | redesign | M | Arc: Teach-Mode Project Build | Dispatches into scaffolding-mentor / coding-partner / code-review skill. In state: becomes `/state:teach:build`. Scaffold/coding-partner logic already lives in skills — state inherits those via cross-compat. |
| build-subject.md | workflows/build-subject.md | redesign | L | Arc: Teach-Mode Subject Authoring | Conversational subject authoring with concept-graph approval + 4-gate promotion (schema → DAG cycle → namespace → drill sandbox). In state: port the 4-gate promoter verbatim in Python. |
| config.md | workflows/config.md | redesign | M | Arc: Teach-Mode Config | Whitelisted learner.* config editor with drift reconciliation + `backup_then_write`. Port the `.bak.<ts>` atomic-write primitive as a cross-cutting helper. |
| dep-install.md | workflows/dep-install.md | redesign | M | Arc: Teach-Mode Onboarding | Per-subject dep installer with teaching moments and user-confirmed shell execution. Subject-aware. Port. |
| state.md | workflows/state.md | redesign | M | Arc: Teach-Mode Dashboards | Read-only "where am I?" orientation — learner, subject, milestone, mastered/weakest concepts, session status. Port against event store + pydantic models. |
| style.md | workflows/style.md | redesign | M | Arc: Teach-Mode Teaching Style | 7-dimension teaching-style editor with lossless round-trip + backup+atomic write. Port — teaching-style dimensions are a core concept. |

**Workflow summary:** 10 files — 8 redesign, 1 drop (template), 1 becomes a helper library. Note that the build workflow already delegates to skills (§8), so porting the skills is the heavy work; porting the workflow is a thin dispatcher.

---

## 6. AOL Teaching Modes

Source: `~/.claude/skills/{primm,scaffolded,socratic,constructivist}.md` + embedded references across AOL.

Per the milestone brief: **each teaching mode is its own Phase with multiple Slices.** These are the heart of teach-mode.

| Mode | Source | Disposition | Complexity | Maps to Phase | Slice candidates |
|---|---|---|---|---|---|
| PRIMM | skills/primm.md | redesign | L | Phase: Teach-Mode PRIMM | Slice 1 — mode-selector rules (engine routes mastery<30% here); Slice 2 — 5-step state machine (Predict→Run→Investigate→Modify→Make); Slice 3 — per-step `question`-tool waits (no proceeding without learner response); Slice 4 — subject-agnostic example binding (python/terminal/typescript); Slice 5 — verifier (PRIMM-specific completion shape); Slice 6 — anti-pattern enforcement (no-reveal-before-predict, never-paste-into-file); Slice 7 — observation emission (prediction+actual for mental-modeler). |
| Scaffolded | skills/scaffolded.md | redesign | L | Phase: Teach-Mode Scaffolded | Slice 1 — mode-selector rules (30–50% mastery); Slice 2 — FULL/PARTIAL/MINIMAL/NONE fade-level resolver driven by curriculum mastery ticker; Slice 3 — per-level code-delivery templates; Slice 4 — one-step-drop logic when learner is stuck; Slice 5 — verifier (Read learner's file, check expected output); Slice 6 — subject-variant examples; Slice 7 — observation emission (scaffold-level drift events). |
| Socratic | skills/socratic.md | redesign | L | Phase: Teach-Mode Socratic | Slice 1 — mode-selector rules (50–70% mastery); Slice 2 — question-type taxonomy (clarifying/probing/hypothetical/evidence); Slice 3 — never-answer enforcement (hard rule, with explicit frustration-override drop-to-Scaffolded); Slice 4 — question-chain construction; Slice 5 — silence tolerance (`question` tool wait semantics); Slice 6 — verifier (learner articulates mental model back); Slice 7 — observation emission. |
| Constructivist | skills/constructivist.md | redesign | L | Phase: Teach-Mode Constructivist | Slice 1 — mode-selector rules (70–80% mastery); Slice 2 — experiment designer (Stage→Play→Reflect); Slice 3 — one-variable scenario generator; Slice 4 — no-warn-about-edge-cases rule (they discover); Slice 5 — reflection question battery; Slice 6 — verifier (learner articulates emergent behavior); Slice 7 — drop-to-Socratic on frustration; Slice 8 — observation emission (discovery quality, hypothesis accuracy). |

**Mode selection layer** (cross-cutting Slice, lives between the four mode Phases):

- Read `CURRICULUM.md` + current concept mastery from event store → pick mode automatically
- Honor curriculum-authored overrides
- Support explicit mode pinning (rare — e.g., review mode)
- Emit `teach.mode.selected` event with reason

**Mode summary:** 4 modes × 7–8 Slices each = ~30 Slices, plus 1 mode-selector Slice. This alone is a significant Arc.

---

## 7. AOL Teaching Personalities

Source: `~/.claude/agent-of-learning/personalities/*.md` (7 files). Orthogonal to modes — a personality modulates Kolb-cycle presentation regardless of which mode is active.

| Personality | Source | Disposition | Complexity | Maps to Phase | Notes |
|---|---|---|---|---|---|
| coach | personalities/coach.md | port | S | Phase: Teach-Mode Personalities | Direct, growth-focused, challenge-driven. Kolb modifiers + do/dont rules + subject-adaptable dialogue. Port content verbatim; wire as config option. |
| enthusiastic-nerd | personalities/enthusiastic-nerd.md | port | S | Phase: Teach-Mode Personalities | Energy + trivia-driven. Same port shape. |
| pair-programming-buddy | personalities/pair-programming-buddy.md | port | S | Phase: Teach-Mode Personalities | "We" language. Same port shape. |
| patient-mentor | personalities/patient-mentor.md | port | S | Phase: Teach-Mode Personalities | Warm, unhurried. Same port shape. |
| schmidt | personalities/schmidt.md | port | S | Phase: Teach-Mode Personalities | Dramatically perfectionist pop-culture voice. Port — flavor personality. |
| socratic-gadfly | personalities/socratic-gadfly.md | port | S | Phase: Teach-Mode Personalities | Questions-only voice. Overlaps conceptually with Socratic mode but operates on a different axis (presentation, not pedagogical method). Port; document the distinction. |
| storyteller | personalities/storyteller.md | port | S | Phase: Teach-Mode Personalities | Narrative-framed explanations. Port. |

Plus: a **personality-loader Slice** that selects the active personality from `teaching-style.json` and injects its voice/Kolb-modifiers/do-dont rules into every teach-mode agent prompt. Subject-adaptation fallback (Python examples when no subject-specific dialogue exists) is a first-class concern.

**Personality summary:** 7 personalities + 1 loader = 8 Slices, fits in one Phase.

---

## 8. AOL Scaffolding-Mentor + Coding-Partner (teach-mode Slices)

Source: `~/.claude/skills/aol-scaffolding-mentor/SKILL.md`, `~/.claude/skills/coding-partner/SKILL.md`, `~/.claude/skills/aol-concept-teacher/SKILL.md` (with per-subject SKILL-*.md variants).

### aol-concept-teacher (the interactive teacher for a single concept)

| Behavior | Source | Disposition | Complexity | Maps to Slice | Notes |
|---|---|---|---|---|---|
| Single-concept invocation | aol-concept-teacher/SKILL.md | redesign | M | Slice: Teach-Mode Concept-Teacher Entry | Per-invocation arg signature (concept_id, mode, scaffold_level, session_id). In state: a Step in teach-mode. |
| Mandatory initial read | aol-concept-teacher/SKILL.md | redesign | S | Slice: Teach-Mode Concept-Teacher Entry | Read learner-config, CURRICULUM.md, mode skill file, next-steps.json, mental-model.json, observations.jsonl. In state: injected context via the same mandatory-initial-read pattern state uses everywhere. |
| Subject-variant example selection | aol-concept-teacher/SKILL.md + SKILL-neovim/shell/terminal/typescript.md | redesign | M | Slice: Teach-Mode Concept-Teacher Subject Adapter | Per-subject SKILL-*.md overrides (neovim, shell, terminal, typescript). In state: multi-subject registry with override files lives under `.state/teach/subjects/<id>/examples/<mode>.md`. |
| Kolb-cycle enforcement | aol-concept-teacher/SKILL.md | redesign | M | Slice: Teach-Mode Kolb Cycle | Experience → Reflect → Conceptualize → Experiment. All four stages mandatory. Dedicated verifier that rejects skipped stages. |
| State-writer delegation | aol-concept-teacher/SKILL.md | redesign | M | Slice: Teach-Mode State-Writer | One observation-writing subagent per concept dispatched after the third pedagogical step. In state: event emissions go straight to SQLite, no subagent hop needed — reduces latency. |
| Verification of learner code | aol-concept-teacher/SKILL.md | redesign | M | Slice: Teach-Mode Learner-Code Verifier | Reads the learner's file, checks it runs, confirms output. Per-subject verifiers (Python runs `python3 file.py`, TS runs `tsc --noEmit` + `tsx`, shell runs bash). |
| CONCEPT TAUGHT structured return | aol-concept-teacher/SKILL.md | redesign | S | Slice: Teach-Mode Concept-Teacher Return | Standard block shape that teach-phase orchestrator consumes. Keep shape, move to a pydantic return model. |

### aol-scaffolding-mentor (project-skeleton guidance)

| Behavior | Source | Disposition | Complexity | Maps to Slice | Notes |
|---|---|---|---|---|---|
| Blueprint generation from PROJECT-PLAN.md | aol-scaffolding-mentor/SKILL.md | redesign | M | Slice: Teach-Mode Scaffold Blueprint | Generate `scaffold-blueprint.json` from plan sections (`## Project:`, `## Milestones`, `## Concepts` / `## Tech Stack`). Pre-computed "answer key." |
| File-by-file guided creation | aol-scaffolding-mentor/SKILL.md | redesign | M | Slice: Teach-Mode Scaffold File Loop | Walks the learner through each file in the blueprint; learner types every line; mentor never creates files. |
| Progress persistence | aol-scaffolding-mentor/SKILL.md | redesign | S | Slice: Teach-Mode Scaffold Progress | `scaffold-progress.json` cursor across context resets. Ports naturally to event store. |
| Per-file verification | aol-scaffolding-mentor/SKILL.md | redesign | S | Slice: Teach-Mode Scaffold File Verifier | Reads each created file, gives specific feedback. |
| Mentoring-style calibration | aol-scaffolding-mentor/SKILL.md | redesign | S | Slice: Teach-Mode Scaffold Style Adapter | Reads `mentoring-style.json`; adapts guidance depth on 5 dimensions. |
| Structural-decision observation recording | aol-scaffolding-mentor/SKILL.md | redesign | S | Slice: Teach-Mode Scaffold Observations | Records observation per file creation + per decision. |
| SCAFFOLD BLOCKED structured return | aol-scaffolding-mentor/SKILL.md | redesign | S | Slice: Teach-Mode Scaffold Return | Structured failure modes (missing_session_id, missing_project_plan, plan_missing_required_sections). Port shape. |
| Per-subject override (typescript) | aol-scaffolding-mentor/SKILL-typescript.md | redesign | S | Slice: Teach-Mode Scaffold Subject Adapter | Typescript-specific scaffold overrides. Subject-registry-driven. |

### coding-partner (active-development mentoring)

| Behavior | Source | Disposition | Complexity | Maps to Slice | Notes |
|---|---|---|---|---|---|
| Graduated hints | coding-partner/SKILL.md | redesign | M | Slice: Teach-Mode Coding-Partner Hints | Hint-depth ladder driven by intervention_threshold dimension. |
| Proactive prerequisite teaching | coding-partner/SKILL.md | redesign | M | Slice: Teach-Mode Coding-Partner Prerequisites | Teaches upcoming concepts from PROJECT-PLAN.md at natural transitions (never mid-task). |
| Accomplishment logging | coding-partner/SKILL.md | redesign | S | Slice: Teach-Mode Coding-Partner Accomplishments | Logs tangible wins. Event-store entries. |
| Growth-note gate | coding-partner/SKILL.md | redesign | M | Slice: Teach-Mode Growth-Note Gate | Session cannot end without a growth note. Hard gate on `/state:teach:build` session-end. |
| Mode-context observations | coding-partner/SKILL.md | redesign | S | Slice: Teach-Mode Coding-Partner Observations | `mode_context=project` vs `curriculum` on every observation. |
| Style calibration (5-dim) | coding-partner/SKILL.md | redesign | S | Slice: Teach-Mode Coding-Partner Style Adapter | intervention_threshold / chattiness / challenge_level / autonomy_preference / code_review_depth. |
| CODING SESSION BLOCKED structured return | coding-partner/SKILL.md | redesign | S | Slice: Teach-Mode Coding-Partner Return | Structured failure modes. Port shape. |
| Per-subject override (typescript) | coding-partner/SKILL-typescript.md | redesign | S | Slice: Teach-Mode Coding-Partner Subject Adapter | Typescript-specific variants. |

**Scaffold/Coding/Concept summary:** 21 behavior Slices across three flows. These three flows own the *behavior* of teach-mode; modes (§6) own the *pedagogical method*; personalities (§7) own the *voice*. All three axes compose.

---

## 9. Cross-Compatible Skills (~/.claude/skills/)

Source: `~/.claude/skills/` (60+ top-level entries). Per opencode-integration-analysis.md, opencode natively reads `~/.claude/skills/**/SKILL.md` and auto-exposes as slash commands — so many of these are **zero-cost carry-overs**.

### 9.1 Pure generic skills — keep as cross-compatible skills (zero port cost)

| Skill | Source | Disposition | Notes |
|---|---|---|---|
| accessibility | skills/accessibility/ | keep | Accessibility checker. Cross-compatible. |
| api-design | skills/api-design/ | keep | REST/GraphQL/etc. patterns. |
| beautiful-commits | skills/beautiful-commits/ | keep | Commit-message generator. |
| best-practices | skills/best-practices/ | keep | General best-practices. |
| code-optimizer | skills/code-optimizer/ | keep | Performance refactors. |
| code-review | skills/code-review/ | keep | Generic code-review. Overlaps with gsd-code-reviewer — keep both (skill for ad-hoc, subagent for workflow). |
| context-handoff | skills/context-handoff/ | keep | Session handoff. |
| core-web-vitals | skills/core-web-vitals/ | keep | Web perf. |
| debug-like-expert | skills/debug-like-expert/ | keep | General debugging. |
| decision-framework | skills/decision-framework/ | keep | Decision helpers. |
| env-setup | skills/env-setup/ | keep | Env bootstrapping. |
| expertise | skills/expertise/ | keep | Domain expertise selector. |
| file-operation-patterns | skills/file-operation-patterns/ | keep | File-op patterns. |
| frontend-design | skills/frontend-design/ | keep | Frontend design. |
| github-workflows | skills/github-workflows/ | keep | GH Actions. |
| lint | skills/lint/ | keep | Linter setup. |
| make-interfaces-feel-better | skills/make-interfaces-feel-better/ | keep | UI polish. |
| python-performance | skills/python-performance/ | keep | Python perf. Relevant to state itself. |
| python-project | skills/python-project/ | keep | Python project setup. Relevant to state. |
| python-quality | skills/python-quality/ | keep | Python quality. Relevant to state. |
| python-testing | skills/python-testing/ | keep | Python testing. Relevant to state. |
| react-best-practices | skills/react-best-practices/ | keep | React patterns. |
| security-hygiene | skills/security-hygiene/ | keep | Security patterns. |
| session-awareness | skills/session-awareness/ | keep | Session-state awareness. |
| test-generator | skills/test-generator/ | keep | Test generation. |
| typescript-patterns | skills/typescript-patterns/ | keep | TS patterns. |
| userinterface-wiki | skills/userinterface-wiki/ | keep | UI component catalog. |
| web-quality-audit | skills/web-quality-audit/ | keep | Web audit. |
| tutor | skills/tutor/ | keep | Generic tutor skill. Distinct from teach-mode — cross-compat. |

### 9.2 Skill-creation / meta-skills — keep cross-compatible

| Skill | Source | Disposition | Notes |
|---|---|---|---|
| create-agent-skills | skills/create-agent-skills/ | keep | Authoring helper for skills. |
| create-hooks | skills/create-hooks/ | keep | Hook authoring. |
| create-mcp-servers | skills/create-mcp-servers/ | keep | MCP authoring. Directly relevant to state's own dev loop. |
| create-meta-prompts | skills/create-meta-prompts/ | keep | Prompt authoring. |
| create-plans | skills/create-plans/ | keep | Plan authoring. Cross-cuts with state's planners. |
| create-slash-commands | skills/create-slash-commands/ | keep | Command authoring. |
| create-subagents | skills/create-subagents/ | keep | Subagent authoring. |
| skill-integration | skills/skill-integration/ | keep | Cross-skill composition. |

### 9.3 AOL-specific skills — reimplement as teach-mode logic

| Skill | Source | Disposition | Notes |
|---|---|---|---|
| aol-concept-teacher | skills/aol-concept-teacher/ | reimplement | See §8. Becomes teach-mode core logic, not a skill. |
| aol-scaffolding-mentor | skills/aol-scaffolding-mentor/ | reimplement | See §8. |
| coding-partner | skills/coding-partner/ | reimplement | See §8. |
| primm, scaffolded, socratic, constructivist | skills/*.md | reimplement | See §6. |
| correction-capture | skills/correction-capture/ | keep + redesign | Cross-compat in build mode; in teach mode becomes a first-class observation emitter. |

### 9.4 GSD-specific skills — reimplement as build-mode logic

| Skill | Source | Disposition | Notes |
|---|---|---|---|
| gsd-onboard | skills/gsd-onboard/ | drop | Old GSD onboarding. Replaced by `/state:build:new` + state's own onboarding. |
| gsd-preflight | skills/gsd-preflight/ | drop | Old GSD preflight. Replaced by state kernel health-check. |
| gsd-trace | skills/gsd-trace/ | drop | Old GSD trace. Replaced by state forensics Arc. |
| gsd-workflow | skills/gsd-workflow/ | drop | Old GSD workflow meta-doc. State has its own authoring guide. |

### 9.5 Specialized / exotic — decide per-skill

| Skill | Source | Disposition | Notes |
|---|---|---|---|
| agent-browser | skills/agent-browser/ | keep | Browsing agent. Cross-compat. |
| beads-state | skills/beads-state/ | keep | State-bead tracking — semantic overlap with state itself; keep for now, re-evaluate after kernel lands. |
| done-retirement | skills/done-retirement/ | keep | "Done" retirement policy. |
| gupp-propulsion | skills/gupp-propulsion/ | keep | User-specific tool. |
| hook-persistence | skills/hook-persistence/ | keep | Hook-persistence patterns. Relevant to state's plugin shim. |
| mail-async | skills/mail-async/ | keep | Async mail. |
| mayor-coordinator | skills/mayor-coordinator/ | keep | Multi-agent coordination. |
| nudge-sync | skills/nudge-sync/ | keep | Nudge pattern. |
| polecat-worker | skills/polecat-worker/ | keep | Worker pattern. |
| refinery-merge | skills/refinery-merge/ | keep | Merge strategy. |
| runtime-hal | skills/runtime-hal/ | keep | Runtime HAL. |
| setup-ralph | skills/setup-ralph/ | keep | Setup helper. |
| sling-dispatch | skills/sling-dispatch/ | keep | Dispatch pattern. |
| witness-observer | skills/witness-observer/ | keep | Observer pattern. |

**Skill summary:** ~60 skills — ~48 keep cross-compat (free), ~8 reimplement as mode-specific logic (§6, §8), 4 drop (obsolete GSD glue). Cross-compat directory wiring is a single Arc Slice: state must discover `.state/skills/` AND respect opencode's native `~/.claude/skills/` scanner AND surface a `/state:sync-skills` command.

---

## 10. GSD-2pi Ideas — new ideas to incorporate

Source: `state-inputs/gsd-2pi-codebase-analysis/*.md`. These are features from the gsd-pi analysis that weren't in original GSD, framed as *additions* to state's design.

| Idea | Source | Disposition | Complexity | Maps to Arc candidate | Notes |
|---|---|---|---|---|---|
| Native Rust performance layer (ripgrep, tree-sitter, libgit2, syntect) | 02-native-rust-engine.md | drop | — | — | State uses opencode's tools; no reason to duplicate native perf. Explicit drop per Python-only runtime constraint. |
| litellm as unified provider layer | 10-python-rebuild-mapping.md | new | L | Arc: Provider Routing & Model Profiles | State commits to litellm default + direct Anthropic SDK escape hatch. GSD had no such abstraction. |
| pluggy-based extension system | 10-python-rebuild-mapping.md | new | M | Arc: State Kernel — Extension Points | Plugin loader for state's own hooks/tools, separate from opencode plugin. |
| Textual TUI framework | 10-python-rebuild-mapping.md | drop | — | — | Explicitly reserved for standalone utilities only. Primary TUI is opencode's. |
| FastAPI web frontend | 10-python-rebuild-mapping.md | drop | — | — | Out of scope — opencode's web surface suffices. |
| pygit2 worktree management | 10-python-rebuild-mapping.md | new | M | Arc: Concurrency — Worktrees | Per-Slice worktree isolation; opencode worktree service preferred, pygit2 is the portability fallback for other hosts. |
| aiosqlite async event store | 10-python-rebuild-mapping.md | new | M | Arc: State Kernel — Event Store | `.state/events.sqlite` async reads, filelock-guarded writes. |
| Four-method OAuth coverage (OpenAI Codex + GitHub Copilot + Gemini CLI + Antigravity) | gsd2-auth-analysis.md | new | L | Arc: Auth — Multi-Provider | Direct port of `packages/pi-ai/src/utils/oauth/` flows. Plus Claude Code OAuth stealth (state-inputs/claude-oauth.md) = **five auth methods day-one** per constraint. |
| Bearer-token Anthropic variant auto-detect | gsd2-auth-analysis.md | new | S | Arc: Auth — Multi-Provider | `usesAnthropicBearerAuth()` — detects Copilot/OpenRouter Claude-via-Bearer. Port as Python detection. |
| API-key fallback path (plain Anthropic/OpenAI/Azure/Bedrock/Vertex/Mistral) | gsd2-auth-analysis.md | new | M | Arc: Auth — Multi-Provider | Covers users without OAuth-eligible subscriptions. |
| Session hierarchy with parentID/fork/children | 11-architecture-discussion.md (reflecting opencode) | new | L | Arc: Concurrency — Session Tree | Maps Arc→Phase→Slice→Step tree 1:1 onto opencode session hierarchy. Use opencode's primitives directly. |
| `task` tool with `task_id` resumption | opencode-extension-surface.md | new | M | Arc: Concurrency — Subagent Dispatch | Resume a prior subagent session. Claude Code can't do this; state gains it for free by being on opencode. |
| 34 typed bus events as state-machine substrate | opencode-extension-surface.md | new | L | Arc: State Kernel — Event Store | State's state machine rides opencode's SyncEvent substrate; own state live in SQLite. |
| Custom auth providers via plugin `auth` hook | opencode-extension-surface.md | new | S | Arc: Auth — Multi-Provider | Each new auth method registers as a plugin auth hook. |
| Custom provider via plugin `provider` hook | opencode-extension-surface.md | new | S | Arc: Provider Routing & Model Profiles | Custom model endpoints registerable via plugin. |
| Permission rule-set per agent | opencode-extension-surface.md | new | M | Arc: Build-Mode Execute Step | Per-subagent allow/ask/deny per tool, glob patterns. Cleaner than GSD's agent frontmatter `tools:` list. |
| Forensics from event log (not just git) | 01-core-architecture.md + event-store | new | M | Arc: Build-Mode Forensics | Superset of GSD forensics — event replay gives higher-fidelity postmortems than git alone. |
| Doctor/health codes (79-code system) | 01-core-architecture.md | new | M | Arc: Build-Mode Health & Self-Check | Numbered diagnostic codes for each kind of misconfiguration/stale-state. Port the pattern. |
| Workflow phases as typed state graph (15 phases in gsd-pi) | 09-types-and-api-contracts.md | drop | — | — | State redefines the graph (Arc→Phase→Slice→Step). Don't inherit the 15-phase gsd-pi list verbatim. |
| Compaction system (tiktoken token counting) | 09-types-and-api-contracts.md | new | M | Arc: Context Budget & Compaction | Context budget manager + `experimental.session.compacting` hook. |
| Headless/RPC mode | 01-core-architecture.md | new | M | Arc: Daemon & RPC | state-daemon is always-on; RPC surface for external drivers. Natural extension of opencode's client/server split. |

**GSD-2pi idea summary:** 20 novel ideas — 15 new (adopt), 5 drop (scope / redundancy). Auth, event store, worktrees, and litellm are the cornerstone adoptions.

---

## 11. Table Stakes (cross-system must-haves)

Features derivable across all three source systems as minimum-viable for state v1.

| Feature | Rationale | Complexity | Maps to Arc candidate |
|---|---|---|---|
| Python 3.12+ daemon (always-on) + per-opencode-session worker | Hybrid daemon pattern; always-on for dashboards, per-session for hot state. | L | Arc: State Daemon |
| Dual-write event store (opencode SyncEvent + `.state/events.sqlite`) | Single source of truth with replay + cross-session restore. | XL | Arc: State Kernel — Event Store |
| Auth layer covering all five methods day-one | Anthropic OAuth stealth + Gemini CLI OAuth + Antigravity + Copilot device-code + API keys. Shipping any subset blocks primary audience. | L | Arc: Auth — Multi-Provider |
| `.state/auth.json` portable store | Import from opencode on first run; portable to Claude Code / Gemini CLI / Qwen Code. | M | Arc: Auth — Multi-Provider |
| Provider routing (litellm + Anthropic direct) | litellm default, Anthropic direct SDK for extended thinking + fine-grained cache control. | L | Arc: Provider Routing & Model Profiles |
| Two independent MCP servers: `state-build` + `state-teach` | Physical enforcement of exclusive-modes cardinal rule. Independently registerable in opencode. | L | Arc: MCP Servers |
| Single bundled opencode plugin (`@state/opencode-plugin`) | Hook shim + TUI extensions in one package. Simplest install. | M | Arc: Opencode Plugin |
| Four-tier planning hierarchy Arc→Phase→Slice→Step | Step owns the discuss/plan/execute/verify cycle; upper tiers are scoping containers. | XL | Arc: Build-Mode Planning Hierarchy |
| Pure-Python DAG scheduler | Identifies all unblocked Slices/Steps; dispatches concurrently. No Prefect/Dask/Airflow. | L | Arc: Concurrency — DAG Scheduler |
| Typed `depends_on` edges in artifacts | Slices/Steps declare dependencies in frontmatter; scheduler resolves. | M | Arc: Build-Mode Planning Hierarchy |
| Per-Slice worktree isolation | opencode worktree service preferred, pygit2 fallback. | L | Arc: Concurrency — Worktrees |
| Snapshot/diff/revert at Step and Slice boundaries | Uses opencode `snapshot` service. Fine-grained undo. | M | Arc: Build-Mode Snapshots & Revert |
| Goal-backward verifier at Step / Slice / Phase / Arc | Multi-tier verification rollup. | XL | Arc: Build-Mode Verification |
| AOL-style learning verifier | Verifies learner actually understood (not just completed). | L | Arc: Teach-Mode Verification |
| Cross-tier integration verifier | Flags contradictions between Step/Slice/Phase artifacts. | M | Arc: Build-Mode Verification |
| Event replay for forensics and cross-session restoration | Replay the event log to reconstruct state at any point. | M | Arc: State Kernel — Event Store |
| Build-mode kernel reimagining every GSD command | See §1. | XL | many Arcs (see §1) |
| Teach-mode kernel (concept-graph, Kolb runner, drill engine, mental model, verifier) | See §6, §8. | XL | many Arcs (see §6, §8) |
| All four teaching modes (PRIMM / Scaffolded / Socratic / Constructivist) as first-class engine behaviors | See §6. | XL | Phase per mode |
| AOL teaching-personality port + teaching-style config | See §7. | M | Arc: Teach-Mode Personalities |
| Scaffolding-mentor + coding-partner as teach-mode Slices | See §8. | L | Arc: Teach-Mode Build-Mentoring |
| Shared TUI extensions (build dashboard, teach dashboard, DAG viewer, drill UI, statusline, toasts, gray-area decision dialog) | Every dashboard is a TUI route in the plugin. | L | Arc: TUI Extensions |
| Opencode hook wiring (full expanded surface: chat.message, tool.execute.*, permission.ask, event, experimental.chat.system.transform, experimental.session.compacting, chat.params, command.execute.before, shell.env) | Each hook wiring is a Slice per constraint. | L | Arc: Opencode Plugin — Hook Shim |
| Portability shims (Claude Code / Gemini CLI / Qwen Code via MCP) | Deprioritized after opencode parity but still in scope. | L | Arc: Host Portability |
| Documentation (architecture, user guide, command reference, teach-mode author guide, build-mode author guide, plugin development guide) | Per constraint. | L | Arc: Documentation |
| Test infrastructure (unit, integration, opencode E2E, provider parity matrix) | Per constraint. | L | Arc: Test Infrastructure |
| Release & packaging (`pyproject`, installer, plugin bundle, remote skill registry, updater) | Per constraint. | M | Arc: Release & Packaging |
| Importer: GSD `.planning/` → state `.state/` | Users coming from GSD must be able to bring their project state over. Forward-only; no back-migration. | M | Arc: Migration & Import |
| Importer: AOL `.aol/` → state `.state/` | Learners coming from AOL keep their mastery/observations/teaching-style. | M | Arc: Migration & Import |
| Mode detection (`.state/mode.json` + directory presence) | Declarative gate + physical signal. Composable with both-mode projects. | S | Arc: State Kernel — Mode Detection |
| Opencode skill-scanner extension (reads `.state/skills/`) | No duplication; extend the existing abstraction. | S | Arc: Opencode Integration — Skills |
| Security baseline (path-traversal + prompt-injection + shell-meta + JSON + regex-DoS guards) | Port from security.cjs on day one. | M | Arc: State Kernel — Security |
| Canonical artifact registry | Port from artifacts.cjs; extended with Arc/Phase/Slice/Step artifacts. | S | Arc: Build-Mode Health & Self-Check |
| Cross-project learnings store (`~/.state/knowledge/`) | Port from learnings.cjs; content-hash dedup. | M | Arc: Build-Mode Learnings Store |
| Lock-file / atomic-write primitives | Filelock + `backup_then_write` + atomicWriteFileSync. Cross-cutting. | S | Arc: State Kernel — I/O Primitives |

---

## 12. Differentiators (what makes `state` different from GSD / AOL / GSD-pi)

| Differentiator | Why it matters | Complexity | Maps to Arc candidate |
|---|---|---|---|
| **Fusion of build + teach in one engine** | No other tool ships both; kernel-shared plumbing (event store, SQLite, MCP, auth, provider routing, plugin shim) with siloed mode logic. | XL | cross-Arc |
| **DAG concurrency over linear phase ordering** | Human dev teams parallelize once foundations land; state models that natively. GSD-1 is strictly serial; gsd-pi's graph is implicit. | L | Arc: Concurrency — DAG Scheduler |
| **Opencode as primary host, not Claude Code** | Multi-provider by design, mid-session model switching, client/server split, typed bus events. State rides this instead of fighting Claude Code's Anthropic-only protocol. | L | Arc: Opencode Plugin |
| **Cross-host portability via MCP** | state-build and state-teach as independent MCP servers means Claude Code / Gemini CLI / Qwen Code users get state too (with reduced UX). | L | Arc: Host Portability |
| **Event-sourced everything** | Both build and teach modes emit events. `STATE.md` / `MENTAL-MODEL.json` are projections. Enables replay, forensics, and cross-session restoration uniformly. | L | Arc: State Kernel — Event Store |
| **Four-tier planning hierarchy with Step owning the discuss/plan/execute/verify cycle** | GSD's two-tier is too coarse; Arc→Phase→Slice→Step separates scope (Arc/Phase) from concurrency-unit (Slice) from atomic work (Step). | L | Arc: Build-Mode Planning Hierarchy |
| **All five auth methods day-one (incl. Anthropic OAuth stealth)** | Direct response to gsd-pi's coverage strategy + Anthropic Pro/Max users being primary audience. API-keys-only would block them. | L | Arc: Auth — Multi-Provider |
| **Teaching modes as first-class engine behaviors** | AOL has modes as markdown skill files. State promotes them to Phase-level state machines with mode-selector + mode-drop rules + per-mode verifiers. | L | Arc per mode + selector |
| **Teaching personalities orthogonal to modes** | Personality (voice) × Mode (pedagogy) × Subject (domain) compose cleanly. Not previously factored this cleanly. | M | Arc: Teach-Mode Personalities |
| **Python as user-facing learning surface** | Build-mode tooling does not hide Python; user is learning Python through building state. A cardinal philosophical stance. | — | cross-cutting |
| **Extreme-thoroughness roadmap (15–25+ Arcs)** | Under-planning is the failure mode. State's own bootstrap produces a vastly richer plan than a typical project. | — | philosophical |
| **Shared TUI extensions in one plugin** | One install, one version, one registration. Simpler than multiple Claude-Code `.claude/` trees. | M | Arc: Opencode Plugin |
| **Dual-write event store (opencode SyncEvent + SQLite)** | Opencode drives live UI; SQLite is authoritative when opencode is closed. Neither source is a single point of failure. | L | Arc: State Kernel — Event Store |
| **Goal-backward verifiers at every tier** | Step, Slice, Phase, Arc, cross-tier. Richer than GSD's per-phase verifier-only model. | L | Arc: Build-Mode Verification |
| **Remote skill registry + updater** | Skills fetched from a registry, not pinned to `.claude/skills/` forever. | M | Arc: Release & Packaging |

---

## 13. Anti-features (do NOT build)

Things to deliberately avoid, drawn from PROJECT.md Out of Scope + cardinal constraints + research signal.

| Anti-feature | Why avoid | What to do instead |
|---|---|---|
| Shipping our own TUI framework | Opencode has a mature plugin+TUI surface; duplicating is waste. | Extend opencode via plugin slots. Textual reserved for standalone utilities only. |
| Running build and teach modes simultaneously in one invocation | Different users, different artifacts, different cognitive shape. Forcing a shared abstraction dilutes both. | Exclusive modes; projects may host both dirs side by side but switch between invocations. Enforced physically by two MCP servers. |
| v1 shipping with API keys only | Anthropic Pro/Max users are primary audience; breaking OAuth stealth is a release blocker. | All five auth methods day one. |
| A shared "mode" abstraction across build and teach | Tempting but dilutes both modes; the fusion point is the *kernel*, not a mode superclass. | Kernel-shared (event store, SQLite, MCP, auth, provider routing, plugin shim). Mode logic fully siloed under separate packages. |
| GSD's two-stage milestone→phase hierarchy | Too coarse; implicitly serial; mixes scope with work-unit. | Four-tier Arc→Phase→Slice→Step. |
| Serial phase execution | Real teams parallelize once foundations are in place. | Explicit `depends_on` DAG + pure-Python scheduler. |
| Porting GSD commands verbatim | Semantics change under the new hierarchy; blind porting leaks GSD's serialism. | Inventory (this file), decide port/redesign/drop per-command. Most redesign. |
| Orchestration via Prefect / Dask / Airflow | Those engines are data-pipeline-shaped, not agent/human-work-shaped. Too heavy. | Pure-Python scheduler over the DAG. |
| Reverse migration state → GSD / GSD-2pi | State is forward-only; looking backward diverts energy. | Only forward migration (GSD/AOL → state). |
| Shipping our own slash-command lexer | Opencode already lexes `$ARGUMENTS`, `$1..$N`. | Use opencode's command surface directly. |
| Shipping our own MCP client | Opencode already runs a full MCP client. | Register `state-build` + `state-teach` as MCP servers. |
| Shipping our own skill scanner | Opencode already scans `~/.claude/skills/`, `.claude/skills/`, `.agents/skills/`. | Extend it to also scan `.state/skills/`. |
| Next.js web frontend | Out of scope; opencode has its own web surface. | None. |
| FastAPI web backend as a core surface | Out of scope for v1. | Only if/when a remote-control surface is needed beyond state-daemon's RPC. |
| Ignoring Anthropic extended thinking / fine-grained cache control | Those features are subscription-value differentiators. | Direct Anthropic SDK escape hatch; litellm for everything else. |
| Coupling auth to opencode's auth store | Blocks Claude Code / Gemini CLI portability. | `.state/auth.json` portable, first-run import from opencode. |
| Coupling event store to opencode only | When opencode is closed, state dashboards still need to work. | Dual-write; SQLite is authoritative. |
| One-big-Python-package monolith | Tempting with Python's module system, but kernel + build + teach need hard boundaries. | Siloed packages: `state`, `state_kernel`, `state_build`, `state_teach`. |
| Textual-web / Textual as primary UI | Opencode TUI is primary; duplicating is waste. | Textual only for standalone CLIs. |
| Shipping a custom agent-loop framework | The loop is small; a framework becomes liability. | Custom ~400 LOC Python loop, or use opencode's agent primitives when staying in-process. |
| Auto-merging gray-area decisions | Teach-mode AskUserQuestion discipline + build-mode discuss-step both demand human decisions. | Gray-area decision dialog (TUI route); captured decisions flow into CONTEXT.md. |

---

## 14. Feature Dependencies (sequencing hints for roadmapper)

The roadmapper owns final ordering, but these dependencies are structural:

```
Auth — Multi-Provider ───────────────┐
Provider Routing & Model Profiles ───┤
                                     ▼
State Kernel — Event Store ──► State Daemon ──► Opencode Plugin ──► MCP Servers
                                     │                 │                │
                                     │                 ▼                │
                                     │          TUI Extensions          │
                                     │                                  │
                                     ▼                                  ▼
                      Build-Mode Planning Hierarchy        Teach-Mode State Routing
                                     │                                  │
                                     ▼                                  ▼
                      Build-Mode Discuss / Plan / Execute /   Teach-Mode Onboarding /
                      Verify Steps (+ DAG Scheduler, Worktrees)  Concept-Teacher / Modes
                                     │                                  │
                                     ▼                                  ▼
                      Review & Ship / Debugger / Forensics      Subject Authoring /
                                                                Personalities / Style
```

Key hard dependencies:

- **Auth lands before Provider Routing** (auth resolves credentials that routing consumes).
- **Event Store lands before Daemon** (daemon reads from it).
- **Daemon lands before Plugin** (plugin RPCs into daemon).
- **Plugin lands before MCP Servers** (MCP uses plugin RPC surface).
- **Planning Hierarchy lands before Discuss/Plan/Execute/Verify Steps** (those operate on the hierarchy).
- **DAG Scheduler lands before Execute Step** (execute runs via scheduler).
- **Worktrees land alongside DAG Scheduler** (scheduler dispatches to worktrees).
- **State Routing + Concept-Teacher land before Modes** (modes are invoked by concept-teacher via router).
- **Modes land before Scaffolding-Mentor + Coding-Partner** (those flows use modes for in-situ concept teaching).
- **Personalities + Teaching-Style config land alongside Mode Phases** (all three axes compose).
- **Security baseline lands in the earliest kernel Arc** (cross-cutting floor).
- **Migration & Import Arcs can land late** — not blocking for fresh-install users, but must exist before general release.

---

## 15. MVP vs Post-MVP Routing (for roadmapper)

Hard MVP (must ship v1.0 day one, per constraints):

1. State Kernel — Event Store + Daemon + Config + Security + I/O Primitives
2. Auth — Multi-Provider (all five methods)
3. Provider Routing & Model Profiles
4. Opencode Plugin (hook shim + TUI extensions bundle)
5. MCP Servers (state-build + state-teach)
6. Build-Mode Planning Hierarchy (Arc/Phase/Slice/Step CRUD)
7. Build-Mode Discuss + Plan + Execute + Verify Step workflows (minimal complete cycle)
8. DAG Scheduler + Worktrees + Snapshots
9. Teach-Mode State Routing + Onboarding + Concept-Teacher
10. All four Teaching Modes (PRIMM, Scaffolded, Socratic, Constructivist)
11. Teaching Personalities (at least 3 of 7; remaining post-MVP)
12. Scaffolding-Mentor + Coding-Partner
13. TUI Extensions (build + teach dashboards, DAG viewer, statusline, gray-area dialog)
14. Docs + Test infra + Release & Packaging

Post-MVP but required before v1.0 general availability:

- Migration & Import (GSD→state, AOL→state)
- Subject Authoring (teach-mode)
- Knowledge Graph (graphify)
- User Profile
- Forensics
- Host Portability shims (explicitly deprioritized after opencode parity)
- Full 7-personality set

Deferred (v1.1+):

- Remote skill registry
- Eval infrastructure (eval-planner + eval-auditor)
- Cross-project learnings store federation

---

## 16. Confidence Assessment

| Area | Confidence | Notes |
|---|---|---|
| GSD command inventory | HIGH | Every file in `commands/gsd/` enumerated and read; cross-checked against PROJECT.md Active requirements. |
| GSD bin/lib modules | HIGH | Every `.cjs` enumerated and its top-level role read. Function-level details flagged only where behavior is non-obvious. |
| GSD agents | HIGH | All 33 enumerated; dispositions driven by opencode-integration-analysis.md's translation rules. |
| GSD hooks | HIGH | All 11 enumerated; opencode-hook bindings named by consulting opencode-extension-surface.md. |
| AOL workflows | HIGH | All 10 enumerated; routing semantics read directly. |
| Teaching modes | HIGH | All four mode skill files read; Slice breakdown grounded in the step-by-step process each file defines. |
| Teaching personalities | HIGH | All 7 read; port disposition is straightforward (content carries over, wiring is new). |
| Scaffolding-mentor / Coding-partner / Concept-teacher | HIGH | All three SKILL.md files read (top half); per-subject overrides noted. Behavior Slices derived from explicit rule numbering in each file. |
| Cross-compatible skills | MEDIUM | ~65 skills listed; a handful of exotic/specialized skills (gupp-propulsion, polecat-worker, etc.) marked keep by default without deep inspection. Low-stakes — they stay free cross-compat either way. |
| GSD-2pi ideas | HIGH | 10-python-rebuild-mapping.md + 11-architecture-discussion.md + gsd2-auth-analysis.md + opencode-extension-surface.md consulted directly. |
| Anti-features | HIGH | Grounded in PROJECT.md Out of Scope + cardinal-rule constraints. |
| Sequencing | MEDIUM | Dependencies are correct but finer ordering is the roadmapper's call. |

---

## 17. Open Questions for the Roadmapper

These are choices the researcher deliberately did NOT make — they belong to the roadmapper:

1. **Arc granularity:** Should "Arc: Build-Mode Verification" be one Arc or split (e.g., Step Verifier Arc + Slice/Phase/Arc Rollup Verifier Arc + Cross-Tier Verifier Arc)? Mapping table hints "one" but the XL complexity suggests splitting.
2. **Mode Phases sharing a cross-cutting "mode runtime" Phase:** There's a small amount of shared plumbing (mode-selector, mode-drop, kolb-cycle runner) that could be its own Phase preceding the four mode Phases, or could be split inside each mode Phase. Roadmapper chooses.
3. **Concept-teacher vs. modes dependency direction:** Does concept-teacher invoke modes (current AOL shape) or do modes invoke concept-teacher (cleaner state shape)? Current inventory assumes the former.
4. **Docs Arc timing:** Docs Arc can be threaded throughout (living docs) or a single late Arc. Preference unset.
5. **Test infrastructure Arc timing:** Same question. State's philosophical-thoroughness stance probably wants threaded test infra.
6. **Workstreams vs. Arcs overlap:** Workstreams (from GSD) and Arcs serve overlapping purposes. Should state collapse them or keep both?
7. **Knowledge-graph Arc fit:** "Arc: Build-Mode Knowledge Graph" vs. folding graphify into "Arc: Build-Mode Codebase Intelligence." Depends on whether state bundles a graph DB.
8. **How many MVP personalities:** 3 chosen above arbitrarily. Could be 7 (full port) or fewer.
9. **Build-mode quick tasks vs. Sketches/Spikes:** Three overlapping entry modes in GSD (quick / sketch / spike). Likely candidates for collapse.
10. **Eval infrastructure Arc:** MVP or post-MVP? Listed post-MVP but gsd-eval-planner/auditor exist as first-class subagents today.

---

## 18. Sources

- `state-inputs/get-shit-done/commands/gsd/` — all 85 files enumerated.
- `state-inputs/get-shit-done/get-shit-done/bin/lib/` — all 26 `.cjs` files read for intent.
- `state-inputs/get-shit-done/agents/` — all 33 files enumerated and sampled.
- `state-inputs/get-shit-done/hooks/` — all 11 files read.
- `state-inputs/opencode-integration-analysis.md` — translation rules for Claude Code → opencode.
- `state-inputs/gsd2-auth-analysis.md` — five-auth-method coverage strategy.
- `state-inputs/opencode-extension-surface.md` — opencode hook/bus/tool surface.
- `state-inputs/gsd-2pi-codebase-analysis/00-INDEX.md`, `10-python-rebuild-mapping.md`, `11-architecture-discussion.md` — Python-rebuild architecture.
- `.planning/PROJECT.md` — cardinal rules, constraints, Active requirements, Out of Scope list.
- `~/.claude/agent-of-learning/workflows/` — all 10 files enumerated and sampled.
- `~/.claude/agent-of-learning/personalities/` — all 7 files read.
- `~/.claude/skills/` — 60+ skills enumerated; AOL-related skills read fully; teaching-mode skills (primm/scaffolded/socratic/constructivist) read fully.
