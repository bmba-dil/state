# v41 Handoff: Agent Harness & Context Control Design

## Milestone Goal

Design the agent harness — the system that controls agent context windows, injects tasks, enforces discipline, prevents scope reduction, detects analysis paralysis, manages deviations, and calibrates context budgets. This is the **control plane** of Build mode: how the daemon/MCP/plugin trio governs agent behavior during Step execution.

## What This Milestone Must Produce

### 1. Context Window Management Protocol

Design how the harness manages agent context throughout a Step's lifecycle. The core principle: **the harness, not the agent, controls what's in context.**

**Clear-and-reinject cycle:**
- When does the harness clear context? (Between Steps? On context budget thresholds?)
- How does it clear context? (Via opencode's session compaction hook? Via new session spawn?)
- What does it reinject? (The exact set of artifacts, references, and state needed to resume)
- How does the harness decide what the agent needs? (Dependency graph? Last known state?)
- How does it handle partial context — what if the agent can't fit everything?

**Context budget thresholds (with reasoning calibrated to opencode models):**
| Threshold | Models | Action |
|-----------|--------|--------|
| ≤25% remaining | All | Emergency: record state, prepare handoff |
| ≤35% remaining | All | Warning: wrap current task, do not start new |
| ≤50% remaining | ≤200K context | Warning: prefer compaction over new reads |
| N/A | 1M+ context | Relax thresholds — but still enforce |

Define exactly how these are detected (via opencode's context meter hook) and what actions are taken at each threshold.

**Compaction strategy:**
- What gets compacted vs what gets re-injected fresh?
- How does the `session.compacting` hook get wired?
- What state survives compaction? (task_id? step_id? event log offsets?)
- How does the harness resume a compacted session with full context restoration?

### 2. Task Decomposition Protocol (Opencode-Specific)

GSD's task protocol uses Claude Code's specific XML structure (`<task>`, `<name>`, `<action>`, `<verify>`, `<done>`, `<files>`). State must design its **own** protocol built on opencode's capabilities.

**What opencode gives us that Claude Code doesn't:**
- The `question` tool (interactive prompts during execution)
- The `task` tool with `subagent_type` (typed subagent spawning with specialized agents)
- MCP tools (state-build and state-teach tools available to agents)
- Plugin hooks (10 hooks we've already wired)
- SSE event bus (live state updates)
- TUI slots (sidebar, statusline, prompt-hint)

**Design the task format:**
- What does a Step-level task look like? (Not XML — something opencode-native)
- How are files specified with exact paths?
- How are verification criteria specified?
- How are done conditions specified?
- How are action instructions specified?
- How does the harness validate task completeness before allowing advancement?

**Task sizing calibrated to context:**
| Granularity | Tasks per Step | Context % per task |
|-------------|---------------|-------------------|
| Coarse | 1-2 | 40-50% each |
| Standard | 2-3 | 25-35% each |
| Fine | 3-5 | 15-25% each |

The harness should auto-select granularity based on the Step's scope and the active model's context window size.

**Task types:**
- `auto` — fully autonomous, no human gates
- `auto+tdd` — autonomous with TDD cycle (RED→GREEN→REFACTOR commits required)
- `checkpoint:human-verify` — pause for visual/functional verification
- `checkpoint:decision` — pause for implementation choice
- `checkpoint:human-action` — pause for unavoidable manual step

Define how each type behaves, how checkpoints are surfaced (via opencode's `question` tool and TUI), and how auto-mode handles checkpoints.

### 3. Plan-as-Prompt Architecture

When execution begins, PLAN.md IS the prompt. Design how:

- PLAN.md content is structured for maximum executor effectiveness (implementation specifics, type signatures, import paths, exact file paths — not vague descriptions)
- The harness injects PLAN.md into the agent's context at execution start
- The harness augments PLAN.md with session state (prior Step results, current worktree path, relevant event history)
- The harness strips non-execution-relevant planning context to save tokens
- What happens if the agent needs more context than is in PLAN.md — how does the harness provide it?

**PLAN.md template structure** (design this):
```
## Objective
[One sentence — what must be true when this Step is done]

## Context
- Parent Slice: {slice_id}
- Parent Phase: {phase_id}  
- Parent Arc: {arc_id}
- Worktree: {worktree_path}
- Depends on: [{step_ids}]
- Blocks: [{step_ids}]

## Tasks
### Task 1: {name}
- Files: [{exact_paths}]
- Action: {specific_implementation_instructions}
- Verify: {verification_command_or_criteria}
- Done: {measurable_acceptance_criteria}

### Task 2: {name}
...

## Verification Contract
- type: tests | lsp | script
- ...

## Threat Model
[STRIDE register]

## Risks
[identified risks + mitigations]
```

### 4. Analysis Paralysis Guard

Design the guard that detects when an agent is stuck in read-only loops:

- **Trigger**: N consecutive tool uses that are Read/Grep/Glob/Explore without any Write/Edit/Bash
- **Threshold**: 5 consecutive (tuneable)
- **Action**: Inject advisory message into context: "5+ read-only operations. State your hypothesis and either write code or report what's blocking you."
- **Escalation**: After 3 advisory injections without resolution → harness intervenes (records state, potentially restarts agent with different instructions)
- **False-positive avoidance**: Research-specific Steps (discuss, plan) should have higher thresholds or be exempt

### 5. Scope Reduction Prohibition

Design how the harness prevents agents from silently reducing scope:

- **Detection**: The plan-checker (v42) validates PLAN.md against STEP.md goal. But during execution, the harness must detect when the agent is building less than planned.
- **Mechanism**: After each task completion, the harness spot-checks: did the task produce what its `## Done` criteria said it would?
- **Prohibited language**: The harness must flag when agent output contains "v1", "simplified", "placeholder", "future", "TODO", "FIXME" without explicit justification and an associated tracking issue
- **Scope drift**: If the agent modifies files outside the Step's declared `files_modified` list without logging a deviation, the harness warns
- **Split recommendation**: If the agent reports "this is too much for one Step," the harness should recommend a Slice/Step split rather than allowing scope reduction

### 6. Deviation Rules Framework

Design the tiered deviation handling system:

**Rule 1 — Auto-fix bugs (no human needed):**
- Wrong queries, logic errors, type errors, null pointer issues
- Max 3 auto-fix attempts per issue
- Each fix committed with `fix:` prefix
- After 3 failures → escalate to Rule 4

**Rule 2 — Auto-add missing critical functionality (no human needed):**
- Missing error handling, input validation, null checks
- Missing auth on protected routes
- Missing DB indexes
- Max 3 auto-fix attempts per issue
- Documented in SUMMARY.md `## Deviations` section

**Rule 3 — Auto-fix blocking issues (no human needed):**
- Missing dependency, wrong types, broken imports
- Build config errors
- Max 3 auto-fix attempts
- After 3 failures → checkpoint:human-decision

**Rule 4 — Ask about architectural changes (HUMAN GATE):**
- New DB table, major schema change, switching frameworks, new infrastructure
- Surfaces via opencode `question` tool with pros/cons table
- Never auto-approved even in autonomous mode

**Scope boundary enforcement:**
- Only fix issues DIRECTLY caused by current Step's changes
- Log out-of-scope findings to `deferred-items.md` (not in plan)

### 7. Subagent Management

Design how the harness spawns, monitors, and collects results from subagents:

- **Spawning**: Via opencode's `task` tool with `subagent_type`
- **Allowed subagent types**: Whitelist per Step type (discuss Step gets different subagents than execute Step)
- **Monitoring**: SSE events from subagent sessions (daemon subscribes to child session events)
- **Result collection**: Subagent returns structured completion; harness spot-checks (files exist, commits exist)
- **Crash recovery**: Max N restarts (default 3) with continuation context
- **Parallel spawning**: Same-wave Steps can spawn subagents concurrently (if no file overlap)
- **Session linking**: Child sessions linked to parent via `task_id` stored in events — survives context compaction

### 8. Harness Architecture

Define the physical architecture of the harness:

```
Agent Session (opencode)
    │
    ├── Plugin Hooks (control surface)
    │   ├── chat.params → inject system prompt, model profile
    │   ├── chat.message → route slash commands
    │   ├── tool.execute.before → block disallowed tools
    │   ├── tool.execute.after → log, check for paralysis
    │   ├── session.compacting → record state before compaction
    │   └── shell.env → inject worktree PATH
    │
    ├── MCP Server (state-build)
    │   ├── plan_step → validate + write PLAN.md
    │   ├── execute_step → inject plan context + launch
    │   ├── verify_step → run verifier chain
    │   └── ... 12 more tools
    │
    └── Daemon (background)
        ├── Event store → authoritative state
        ├── Projector → rebuilds STATE.md projections
        ├── Scheduler → computes DAG frontier
        ├── SSE bus → live TUI updates
        └── Crash recovery → resume in-flight Steps
```

## Success Criteria

1. The context window management protocol is specified with exact thresholds, actions, and compaction behavior — implementable without further design.
2. The task decomposition protocol works exclusively with opencode's tool set (task, question, MCP tools, hooks) — no Claude Code assumptions.
3. The plan-as-prompt architecture defines exactly what PLAN.md contains and how the harness injects it.
4. The analysis paralysis guard is specified with trigger thresholds, escalation steps, and false-positive exemptions.
5. The scope reduction prohibition defines detection mechanisms and prohibited language patterns.
6. The deviation rules framework is specified with all four rules, max attempts, and escalation paths.
7. Subagent management is specified from spawn to result collection to crash recovery.

## Research Inputs

**Primary reference — GSD agent harness patterns:**
- `state-inputs/get-shit-done/commands/gsd/gsd-executor.md` — deviation rules, analysis paralysis guard, auto-fix protocols, checkpoint behavior
- `state-inputs/get-shit-done/commands/gsd/gsd-planner.md` — task decomposition protocol, scope reduction prohibition, context-budget-aware sizing
- `state-inputs/get-shit-done/commands/gsd/gsd-execute-phase.md` — wave-based parallel execution, context-budget-aware prompt enrichment
- `state-inputs/get-shit-done/hooks/gsd-context-monitor.js` — context meter with WARNING/CRITICAL thresholds
- `state-inputs/get-shit-done/hooks/gsd-workflow-guard.js` — advisory hook preventing un-gated file edits
- `state-inputs/get-shit-done/hooks/gsd-prompt-guard.js` — injection pattern scanning at write time
- `state-inputs/get-shit-done/hooks/gsd-read-guard.js` — read-before-edit enforcement

**Secondary reference — GSD state management:**
- `state-inputs/get-shit-done/bin/lib/state.cjs` — STATE.md advancement, plan counting, session recording
- `state-inputs/get-shit-done/bin/lib/model-profiles.cjs` — agent-to-model routing across profiles
- `state-inputs/get-shit-done/bin/lib/template.cjs` — template selection heuristics

**Opencode reference:**
- `state-inputs/opencode/packages/opencode/src/tool/task.ts` — how subagents are spawned, session linking, result extraction
- `state-inputs/opencode/packages/opencode/src/session/session.ts` — session lifecycle, compaction
- `state-inputs/opencode/packages/opencode/src/hooks/` — available hook types and their signatures
- `state-inputs/opencode/packages/opencode/src/agent/agent.ts` — agent lifecycle, model resolution

**Shipped state code:**
- `packages/opencode-plugin/src/hooks/` — all 10 hook implementations (understand the control surface we already have)
- `packages/opencode-plugin/src/tui/statusline.ts` — statusline with context meter
- `packages/opencode-plugin/src/tui/prompt-hint.ts` — session prompt hint
- `src/state_worker/` — SSE bridge, hot state, hook forwarding
- `src/state_daemon/middleware.py` — mode enforcement via HTTP headers

## Key Questions for Discuss-Phase

1. **Context clearing mechanism**: Does the harness clear context by spawning a new opencode session? Or by using opencode's compaction hook to strip and reinject? The former is cleaner but loses session continuity. The latter preserves the TUI but risks stale state.

2. **Task format**: GSD uses XML in markdown. OpenCode's `task` tool accepts a prompt string. Should state's task format be: (a) structured YAML frontmatter in PLAN.md, (b) a JSON schema the MCP server validates, or (c) a convention within markdown sections?

3. **Auto-approve checkpoints in autonomous mode**: GSD auto-approves `human-verify` and auto-selects first option for `decision` checkpoints in autonomous mode. Should state do the same, or should autonomous mode refuse to proceed past any checkpoint?

4. **Context budget for 1M+ models**: With models that have 1M+ token context windows, is context management even necessary for most Steps? Should the harness detect available context and disable budget management for large-window models?

5. **Subagent type whitelist**: Should the harness use a static whitelist per Step type, or should PLAN.md declare what subagent types are allowed?

6. **Plan mutability during execution**: Can the agent modify PLAN.md during execution (e.g., if it discovers a task needs splitting)? Or is PLAN.md immutable once execution starts?

7. **Harness intervention authority**: Can the harness force-stop an agent? Restart it? Override its tool calls? What's the escalation path from advisory → warning → intervention → force-stop?

## Dependencies

- **v40 (Hierarchy & Artifact System)** — MUST be complete. The harness needs to know what artifacts to inject, what paths to protect, what STATE.md projections to read.
- **v8 (Plugin Hooks)** — shipped. The harness builds on the 10 hooks we've already wired.
- **v7 (Per-Session Worker)** — shipped. The worker's SSE bridge and hot-state container are the harness's connection to the daemon.
- **v6 (State Daemon)** — shipped. The daemon's SSE bus, crash recovery, and mode middleware are harness infrastructure.

## Scope Boundaries

**In scope:**
- Context window management protocol
- Task decomposition protocol (opencode-specific)
- Plan-as-prompt architecture
- Analysis paralysis guard
- Scope reduction prohibition
- Deviation rules framework
- Subagent management
- Harness architecture diagram showing all components

**Out of scope:**
- Verifier algorithm design (v42)
- GSD command port mapping (v43)
- Any implementation code
- Teach mode harness (v47)
- Rust DB (v44)

## Reference Patterns from GSD

1. **Context monitor hook**: GSD's `gsd-context-monitor.js` reads context metrics from the statusline bridge and injects WARNING/CRITICAL messages. State can do better — the daemon can monitor context via SSE events and inject via the `chat.system.transform` hook.

2. **Deviation rules**: GSD's 3-tier auto-fix system is battle-tested. State should adopt the tiered approach but adapt Rule 4 (architectural changes) to use opencode's `question` tool instead of Claude Code's `AskUserQuestion`.

3. **Analysis paralysis**: GSD's 5-read threshold with explanation requirement is simple and effective. State should adopt it with opencode-aware tool counting (what Tools count as "read-only"? `Task` with a research agent? `Question`?).

4. **Plan-as-prompt**: GSD's PLAN.md IS the executor's prompt, containing exact file paths, type signatures, and import paths. State's PLAN.md should exceed this — with the harness augmenting it with live session state, worktree paths, and dependency status from the DAG.
