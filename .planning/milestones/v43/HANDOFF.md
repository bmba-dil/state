# v43 Handoff: Build Workflow Orchestration & GSD Port Map

## Milestone Goal

Design the complete workflow orchestration layer — how discuss→plan→execute→verify→ship works at every tier, how the DAG scheduler drives execution, how subagents are spawned and managed, how session state survives across compactions and crashes, how error recovery works, and how all 30 GSD commands map to state-native Step workflows. This is the **operational layer** — how the machine actually runs.

## What This Milestone Must Produce

### 1. Full Workflow Cycle Per Tier

Design the complete lifecycle for each tier:

**Step workflow (the richest — runs full discuss→plan→execute→verify cycle):**

```
IDLE
  │
  ├─ /state:build:discuss <step>
  │   ├── Agent analyzes STEP.md goal + Slice/Phase/Arc context
  │   ├── Multi-turn Q&A via opencode question tool
  │   ├── Gray-area decisions surfaced
  │   └── → DISCUSS.md written → Step state: DISCUSSING
  │
  ├─ /state:build:plan <step>
  │   ├── Agent reads DISCUSS.md, STEP.md goal, upstream context
  │   ├── Task decomposition (per v41 protocol)
  │   ├── Threat model populated
  │   ├── Plan-checker agent validates PLAN.md (per v42)
  │   ├── On BLOCKED → back to DISCUSSING
  │   └── → PLAN.md written → Step state: PLANNING
  │
  ├─ /state:build:execute <step>
  │   ├── Pre-execute snapshot taken (per v4)
  │   ├── Harness injects PLAN.md as prompt
  │   ├── Agent executes tasks sequentially within the Slice worktree
  │   ├── Per-task: commit with type enforcement, auto-fix deviations
  │   ├── Paralysis guard active (per v41)
  │   ├── Scope reduction guard active (per v41)
  │   ├── On checkpoint → pause, surface via question tool
  │   ├── On completion → self-check (files exist, commits exist)
  │   └── → EXECUTE.log written → Step state: EXECUTING
  │
  ├─ /state:build:verify <step>
  │   ├── Pre-verify snapshot taken
  │   ├── Goal-backward verifier runs (per v42)
  │   ├── Security verifier runs
  │   ├── Stub detector runs
  │   ├── Anti-pattern scanner runs
  │   ├── On ALL PASS → Step state: DONE
  │   ├── On FAIL → Step state: EXECUTING (retry loop)
  │   │   └── Max retries? Configurable. Default 3.
  │   │   └── On max retries exceeded → BLOCKED (human decision)
  │   └── → VERIFY.md written → Step state: DONE | EXECUTING | BLOCKED
  │
  └─ /state:build:ship <slice>
      ├── All Steps in Slice must be DONE
      ├── Slice rollup verifier runs
      ├── On PASS → PR opened via gh CLI
      │   ├── Code review spawned
      │   ├── On review BLOCKER findings → spawn fix Steps
      │   └── On green → merge PR → Slice state: SHIPPED
      └── Slice snapshot taken → Slice state: SHIPPED
```

**Slice workflow (simpler — scoping container):**
- `planned` → Slice defined but no Steps exist
- `worktree_ready` → Worktree created and bootstrapped
- `in_progress` → At least one Step is active
- `shipped` → All Steps DONE, Slice rollup passed, PR merged
- `reverted` → Slice worktree reverted to pre-ship snapshot

**Phase workflow (simpler still — aggregation container):**
- `planned` → Phase defined with Slice list
- `in_progress` → At least one Slice is active
- `verified` → Phase rollup verifier passed
- `shipped` → All Slices shipped, Phase acceptance criteria met
- `abandoned` → Phase cancelled

**Arc workflow (simplest — portfolio container):**
- `planned` → Arc defined with Phase list
- `in_progress` → At least one Phase is active
- `shipped` → All Phases shipped, Arc acceptance criteria met
- `abandoned` → Arc cancelled

### 2. DAG Scheduler Integration

Design how the DAG scheduler (v5, shipped) drives the workflow:

- **Frontier computation**: Scheduler reads all SLICE.md depends_on edges, computes which Slices are unblocked
- **Concurrency grouping**: Slices grouped by Phase; Phases grouped by Arc
- **Dispatcher**: For each unblocked Slice, dispatcher creates/ensures worktree, then advances the Slice's first pending Step to DISCUSSING
- **Reactive triggers**: On `state.step.advanced`, scheduler recomputes frontier, potentially unblocking dependent Slices
- **Priority inversion**: If a critical-path Slice is blocked on a soft edge, scheduler fires warning
- **Deadlock detection**: If all in-flight Slices are blocked on missing/descoped predecessors, scheduler fires `state.scheduler.deadlock`
- **Concurrency cap**: Configurable. Default: 3 concurrent Slices. Tuned per-model context budget.

Design the interplay between scheduler and workflow:
- The scheduler doesn't execute Steps — it computes what CAN execute and notifies the harness
- The harness (daemon/worker) picks up scheduler output and launches agent sessions
- The harness reports Step results back to the scheduler via events
- The scheduler recomputes on every `state.step.advanced` event

### 3. Session Management

Design how sessions survive context resets, compactions, and crashes:

**Session identity:**
- Every Step execution gets a unique session ID (ULID)
- Session linked to parent Slice/Phase/Arc via event store
- Session ID stored in `task_id` for opencode task resumption

**Context compaction survival:**
- On `session.compacting` hook: harness records current state to event store
  - Current Step ID, current task within PLAN.md, completed task IDs
  - Current worktree path
  - Event log offset (last event processed)
  - Context budget remaining
- On session resume: harness reads recorded state, reinjects minimal context
  - STEP.md, PLAN.md, completed task summaries
  - Current worktree path
  - Relevant event log tail (not the whole log)
  - Prior verifier results (if any)

**Crash recovery:**
- On daemon startup: crash recovery reads event store for in-flight Steps (state == EXECUTING or VERIFYING with no terminal event)
- For each in-flight Step: emit `state.step.resumed`, reinject context, continue
- If a Step has been in-flight for > N hours (configurable), prompt user: continue or abandon?

**Pause/Resume:**
- `/state:build:pause` — records session state, detaches agent gracefully
- `/state:build:resume <step-id>` — reads recorded state, reinjects, continues
- `/state:build:thread <name>` — persistent context thread for cross-Step work
- `/state:build:workstream <name>` — parallel work context (multiple concurrent Slices per user)

### 4. Error Recovery Patterns

Design error recovery at every stage:

**Discuss failures:**
- Agent can't extract decisions → retry with more focused prompt
- User disconnects during Q&A → save DISCUSS.md partial, resume on reconnect

**Plan failures:**
- Plan checker blocks → agent replans with feedback
- Plan checker blocks 3 times → surface to user for decision
- Plan exceeds context budget → recommend Split (break into more Steps)

**Execute failures:**
- Agent crashes → restart with continuation context (max 3)
- Agent hits analysis paralysis → advisory → warning → intervention
- Agent violates scope → warn, log deviation, on repeat → checkpoint
- Agent produces broken code → auto-fix rules apply (v41), then checkpoint
- Git merge conflict in worktree → agent resolves or checkpoints

**Verify failures:**
- Verifier finds gaps → back to EXECUTING for fix
- Max retries exceeded → BLOCKED → human decision
- Security verifier finds OPEN:BLOCKER → cannot ship, must fix

**Ship failures:**
- PR has merge conflicts → agent resolves
- Code review BLOCKER → spawn fix Step
- CI fails → agent fixes, re-pushes
- gh CLI unavailable → log error, prompt user

### 5. GSD Command Port Map

Catalog all 30 GSD commands and design their state-native equivalents. For each command:

**Phase B — Execute commands (core workflow):**
| GSD Command | State Equivalent | Design Decision | Rationale |
|-------------|-----------------|-----------------|-----------|
| `plan-phase` | `plan-step` + `plan-slice` + `plan-phase` | Redesign for 4 tiers | GSD's single-tier planning doesn't map to 4 tiers. Each tier gets its own plan command with appropriate depth. |
| `execute-phase` | `execute-step` driven by DAG scheduler | Redesign | GSD's wave-based execution becomes DAG-driven. No explicit "phase execution" — the scheduler determines what runs. |
| `verify` | `verify-step` + `verify-slice` + `verify-phase` | Redesign for verifier chain | GSD's single verifier becomes the hierarchical verifier chain (v42). |
| `ship` | `ship-slice` | Port (adapt) | GSD's ship creates PR; state adds Slice snapshot + rollup verification. |
| `quick` | `quick` (fast-path Slice+Step) | Port (adapt) | GSD's quick task creates a phase; state creates a Slice+Step inline. |
| `fast` | `fast` (inline, no artifacts) | Port | Trivial one-shot tasks with no DAG integration. |

**Phase C — Quality commands:**
| GSD Command | State Equivalent | Design Decision |
|-------------|-----------------|-----------------|
| `code-review` | `code-review` (spawns review subagent) | Port (adapt) |
| `code-review-fix` | `code-review-fix` (spawns fix subagent per finding) | Port (adapt) |
| `secure-phase` | `secure-step` (per-Step security verifier, integrated into verify chain) | Redesign — integrated into verify, not standalone |
| `validate-phase` | Part of verify chain (Nyquist validation) | Redesign — integrated |
| `audit-uat` | `audit-uat` (cross-Slice UAT aggregation) | Port (adapt) |
| `audit-milestone` | `audit-arc` (Arc boundary audit) | Redesign — maps to Arc, not milestone |

**Phase D — Intelligence commands:**
| GSD Command | State Equivalent | Design Decision |
|-------------|-----------------|-----------------|
| `map-codebase` | `map-codebase` (parallel mapper subagents, writes `.state/build/codebase/`) | Port (adapt) |
| `intel` | `intel` (parallel intel subagents, writes `.state/build/intel/`) | Port (adapt) |
| `graphify` | `graphify` (knowledge graph, writes `.state/build/graph/`) | Port (adapt) |
| `scan` | `scan` (lightweight codebase assessment) | Port |
| `research-phase` | `research-step` (pre-planning research) | Redesign — Step-level, not Phase-level |

**Phase E — Session commands:**
| GSD Command | State Equivalent | Design Decision |
|-------------|-----------------|-----------------|
| `pause-work` | `pause` (records session state to event store) | Redesign — event-sourced, not markdown |
| `resume-work` | `resume <step-id>` (reads event store, reinjects) | Redesign — event-sourced |
| `thread` | `thread` (persistent cross-Step context) | Port (adapt) |
| `workstreams` | `workstreams` (parallel work contexts) | Port (adapt) |

**Phase F — Visibility commands:**
| GSD Command | State Equivalent | Design Decision |
|-------------|-----------------|-----------------|
| `progress` | `progress` (reads projector output) | Redesign — reads from projector, not STATE.md |
| `stats` | `stats` (aggregate stats from event store) | Redesign — event-sourced, not markdown |
| `health` | `health` (validates consistency across tiers) | Redesign — event-store-vs-filesystem checks |
| `milestone-summary` | `arc-summary` (Arc-level progress summary) | Redesign — maps to Arc |

**Phase G — Discovery commands:**
| GSD Command | State Equivalent | Design Decision |
|-------------|-----------------|-----------------|
| `explore` | `explore` (Socratic ideation before planning) | Port |
| `brainstorm` | `brainstorm` (idea capture) | Port |
| `help` | `help` (command reference) | Port |
| `onboard` | `onboard` (tutorial) | Port |

**Phase H — Meta commands:**
| GSD Command | State Equivalent | Design Decision |
|-------------|-----------------|-----------------|
| `debug` | `debug` (scientific-method FSM, persistent session) | Port (adapt) |
| `forensics` | `forensics` (event replay + git log) | Redesign — event-sourced forensics |
| `undo` | `undo` (manifest-aware revert via snapshots) | Redesign — snapshot-based, not commit-based |
| `autonomous` | `autonomous` (DAG-driven, no interactive gates) | Redesign — DAG scheduler drives it |
| `settings` | `settings` (config management) | Port |
| `docs-update` | `docs-update` (regenerate docs from codebase) | Port |
| `cleanup` | `cleanup` (archive shipped Arcs, GC worktrees) | Redesign — Arc-based cleanup |

**Phase I — New commands (no GSD equivalent):**
| Command | Purpose |
|---------|---------|
| `new-arc` | Create an Arc (feature block) |
| `new-phase` | Create a Phase within an Arc |
| `new-slice` | Create a Slice within a Phase |
| `insert-slice` | Insert urgent Slice with decimal numbering |
| `add-phase` | Add Phase to end of Arc |
| `remove-phase` | Remove future Phase, renumber |
| `multi-arc` | Batch-plan from feature dump |
| `set-quality` | Set execution quality profile |
| `set-profile` | Set model profile |
| `manager` | Interactive command center |

For each command, specify in the design:
- Exact slash command syntax: `/state:build:<command> [args]`
- Which MCP tool it maps to in state-build MCP server
- What artifacts it reads/writes
- What events it emits
- What state transitions it triggers
- What subagents it spawns (if any)
- What hooks it triggers

### 6. Subagent Spawning Protocol

Design how subagents are spawned for each workflow:

**Subagent types and their tools:**
| Subagent | Allowed Tools | Used For |
|----------|--------------|----------|
| `gsd-executor` | All Write/Edit/Bash + task spawn | Execute Step tasks |
| `gsd-planner` | Read/Grep/Glob/Write (PLAN.md only) | Plan Step |
| `gsd-verifier` | Read/Grep/Glob/Bash (test/lsp) | Verify Step output |
| `gsd-code-reviewer` | Read/Grep/Glob | Code review |
| `gsd-code-fixer` | Write/Edit/Bash | Fix review findings |
| `gsd-plan-checker` | Read/Grep/Glob/Write (PLAN.md feedback) | Pre-execution plan validation |
| `gsd-phase-researcher` | Read/Grep/Glob/Write (RESEARCH.md) | Pre-planning research |
| `gsd-codebase-mapper` | Read/Grep/Glob/Write (.state/build/codebase/) | Codebase mapping |
| `gsd-debugger` | All + task spawn | Debug sessions |
| `gsd-security-auditor` | Read/Grep/Glob/Write (SECURITY.md) | Security verification |

**Subagent lifecycle (managed by harness, per v41):**
1. Harness spawns via opencode `task` tool with `subagent_type`
2. Harness monitors via SSE events from child session
3. On completion: harness spot-checks (files exist, commits exist, SUMMARY.md written)
4. On failure/crash: harness restarts up to N times with continuation context
5. On success: harness records result in event store, advances parent Step FSM

## Success Criteria

1. The full discuss→plan→execute→verify→ship cycle is specified for each tier with exact state transitions, events, and artifacts.
2. The DAG scheduler integration is specified — how it computes frontiers, dispatches work, and reacts to completion.
3. Session management is specified — how context compaction, crash recovery, pause/resume, threads, and workstreams work.
4. Error recovery is specified for every stage with escalation paths.
5. All 30 GSD commands are mapped to state-native equivalents with design rationale.
6. Subagent spawning protocols are specified per agent type with allowed tools and lifecycle management.

## Research Inputs

**Primary reference — GSD workflow orchestration:**
- `state-inputs/get-shit-done/commands/gsd/gsd-execute-phase.md` — wave-based parallel execution, subagent spawning, spot-checking, crash recovery
- `state-inputs/get-shit-done/commands/gsd/gsd-plan-phase.md` — full plan-phase workflow (research→plan→check→validate→commit)
- `state-inputs/get-shit-done/commands/gsd/gsd-discuss-phase.md` — discuss-phase workflow, gray-area extraction
- `state-inputs/get-shit-done/commands/gsd/gsd-verifier.md` — verification workflow, gap closure
- `state-inputs/get-shit-done/commands/gsd/gsd-executor.md` — executor protocol, deviation handling, checkpoints
- `state-inputs/get-shit-done/commands/gsd/gsd-quick.md` — quick-task inline execution
- `state-inputs/get-shit-done/commands/gsd/gsd-ship.md` — shipping workflow
- `state-inputs/get-shit-done/commands/gsd/gsd-debug.md` — debug session FSM
- `state-inputs/get-shit-done/commands/gsd/gsd-pause-work.md` — context handoff
- `state-inputs/get-shit-done/commands/gsd/gsd-resume-work.md` — context restoration
- `state-inputs/get-shit-done/commands/gsd/gsd-autonomous.md` — full autonomous execution
- `state-inputs/get-shit-done/commands/gsd/gsd-thread.md` — persistent context threads
- `state-inputs/get-shit-done/commands/gsd/gsd-workstreams.md` — parallel work contexts

**GSD state management:**
- `state-inputs/get-shit-done/bin/lib/phase.cjs` — phase lifecycle, decimal insertions, completion
- `state-inputs/get-shit-done/bin/lib/state.cjs` — state advancement, plan counting, session recording
- `state-inputs/get-shit-done/bin/lib/workstream.cjs` — workstream CRUD, migration
- `state-inputs/get-shit-done/hooks/gsd-statusline.js` — context meter display

**Opencode session management:**
- `state-inputs/opencode/packages/opencode/src/session/session.ts` — session lifecycle, compaction
- `state-inputs/opencode/packages/opencode/src/tool/task.ts` — subagent spawning, session linking
- `state-inputs/opencode/packages/opencode/src/sync/` — event synchronization

**State shipped code:**
- `src/state_core/scheduler.py` — existing DAG scheduler (must integrate with)
- `src/state_worker/` — existing worker session management
- `src/state_daemon/orchestrator.py` — existing daemon startup sequence
- `src/state_daemon/recovery.py` — existing crash recovery
- `src/state_build/mcp.py` — existing MCP skeleton tools (what's already registered)

## Key Questions for Discuss-Phase

1. **Step retry limit**: How many times can a Step fail verification and retry before being BLOCKED? Should this be configurable per Step? Per Slice?

2. **Concurrent Slices cap**: With context budgets in play, what's the maximum number of concurrent Slices? Should it vary by model context window size?

3. **DAG-driven vs user-driven execution**: Should the DAG scheduler auto-start unblocked Steps, or should the user always initiate execution? Hybrid: scheduler recommends what to run next, user approves?

4. **Session isolation**: Should each Step execution get a fresh opencode session? Or can multiple Steps share a session? Trade-off: isolation vs context efficiency.

5. **Autonomous mode scope**: In autonomous mode, should the entire Arc run headless? Or just one Phase? What gates remain (if any)?

6. **GSD command dropping**: Are there GSD commands that should NOT be ported? The original project stated "port, redesign, or drop." Which are dropped?

7. **Worktree GC timing**: When should Slice worktrees be garbage collected? On Slice SHIPPED? On Phase SHIPPED? On Arc SHIPPED? Manual?

## Dependencies

- **v40 (Hierarchy & Artifact System)** — MUST be complete. All workflows operate on the hierarchy.
- **v41 (Agent Harness)** — MUST be complete. Workflows use the harness for context control and agent discipline.
- **v42 (Quality Pipeline)** — MUST be complete. Workflows invoke verifiers and plan checkers.
- **v5 (DAG Scheduler)** — shipped. Workflows integrate with the scheduler.
- **v4 (Worktree + Snapshot)** — shipped. Workflows create/manage worktrees.
- **v1 (Event Store)** — shipped. Workflows emit events.

## Scope Boundaries

**In scope:**
- Full workflow definitions for all four tiers
- DAG scheduler integration
- Session management (compaction, crash recovery, pause/resume)
- Error recovery patterns
- Complete GSD command port map (all 30 commands)
- Subagent spawning protocols

**Out of scope:**
- Implementation of any workflow
- Teach mode workflow (v49)
- Rust DB integration (v44)

## Reference Patterns from GSD

1. **Wave-based execution → DAG-driven execution**: GSD's waves are a simplified DAG (sequential waves with no intra-wave edges). State replaces this with the full DAG scheduler — unblocked Slices run concurrently, not in waves.

2. **STATE.md advancement → event-driven projection**: GSD's `cmdStateAdvancePlan` directly mutates STATE.md. State's projector rebuilds STATE.md from event stream — no agent touches STATE.md directly.

3. **Checkpoint mechanism**: GSD's `checkpoint:human-verify`, `checkpoint:decision`, `checkpoint:human-action` types are well-designed. State should adopt them but surface via opencode's `question` tool and TUI rather than Claude Code's `AskUserQuestion`.

4. **Spot-check protocol**: GSD's executor spot-checks after subagent completion (files exist, commits exist). State should extend this with event-store consistency checks (did the subagent emit the expected events?).
