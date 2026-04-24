# TypeScript Types, Interfaces & API Contracts

## Overview
- **Total TypeScript Files:** 1,279
- **Exported Interfaces:** 162+ files
- **Exported Types:** 63+ files
- **API Routes:** 40+
- **Native Type Modules:** 13
- **Major Type Categories:** 28

---

## 1. Core GSD State Types (`extensions/gsd/types.ts`)

### Phase Enum
```
"pre-planning" | "needs-discussion" | "discussing" | "researching" |
"planning" | "executing" | "verifying" | "summarizing" | "advancing" |
"validating-milestone" | "completing-milestone" | "replanning-slice" |
"complete" | "paused" | "blocked"
```

### GSDState — Central State Object
- Active milestone/slice/task references (ActiveRef: id + title)
- Current phase
- Recent decisions
- Blockers
- Requirements (RequirementCounts: active, validated, deferred, out-of-scope, blocked)

### Roadmap Types
- `Roadmap` — Title, vision, success criteria, slices, boundary map
- `RoadmapSliceEntry` — Slice with risk ("low"|"medium"|"high"), dependencies, done, demo
- `BoundaryMapEntry` — Inter-slice dependencies (produces/consumes)

### Planning Types
- `SlicePlan` — Goal, demo, must-haves, tasks, files likely touched
- `TaskPlanEntry` — Title, description, estimate, files, verify instructions
- `TaskPlanFrontmatter` — Estimated steps/files, skills used

### Summary Types
- `Summary` — Frontmatter, oneLiner, what happened, deviations, files modified
- `SummaryFrontmatter` — Milestone, provides, requires, affects, key files, decisions, patterns, drill-down paths
- `FileModified` — Path and description

### Continue-Here Types
- `Continue` — Frontmatter, completed/remaining work, decisions, context, next action
- `ContinueFrontmatter` — Milestone, slice, task, step tracking, status ("in_progress"|"interrupted"|"compacted")

### Verification Types
- `VerificationResult` — Passed flag, checks, discovery source, timestamp, runtime errors, audit warnings
- `VerificationCheck` — Command, exit code, stdout, stderr, duration
- `RuntimeError` — Source (bg-shell/browser), severity, message, blocking flag
- `AuditWarning` — Package name, severity, title, URL, fix availability

### Secrets Types
- `SecretsManifest` — Milestone, entries[]
- `SecretsManifestEntry` — Key, service, dashboard URL, guidance, format hint, status

---

## 2. Engine & Execution Types (`extensions/gsd/engine-types.ts`)

- `EngineState` — Phase, milestone/slice/task IDs, isComplete, raw opaque state
- `StepContract` — Unit type, ID, prompt for execution
- `DisplayMetadata` — Engine label, current phase, progress summary, step counts
- `EngineDispatchAction` — Discriminated union: dispatch | stop | skip
- `ReconcileResult` — Outcome: continue | milestone-complete | pause | stop
- `RecoveryAction` — Outcome: retry | skip | stop | pause
- `CloseoutResult` — Committed flag, artifacts[]
- `CompletedStep` — Unit type, ID, start/finish timestamps

---

## 3. Dispatch & Rules System

### Dispatch Types (`auto-dispatch.ts`)
- `DispatchAction` — "dispatch" (unitType, unitId, prompt, pauseAfterDispatch, matchedRule) OR "stop" (reason, level)
- `DispatchContext` — basePath, mid, midTitle, state, prefs, optional session
- `DispatchRule` — Name, async match function → DispatchAction | null

### Rule Types (`rule-types.ts`)
- `RulePhase` — "dispatch" | "post-unit" | "pre-dispatch"
- `RuleEvaluation` — "first-match" | "all-matching"
- `RuleLifecycle` — Artifact, retry_on, max_cycles, idempotency_key
- `UnifiedRule` — Name, when, evaluation, where (predicate), then (action)

---

## 4. Preferences & Configuration (`preferences-types.ts`)

### Workflow Modes
- `WorkflowMode` — "solo" | "team"

### 40+ Known Preference Keys
```
version, mode, always_use_skills, prefer_skills, avoid_skills, skill_rules,
custom_instructions, models, skill_discovery, skill_staleness_days,
auto_supervisor, uat_dispatch, unique_milestone_ids, budget_ceiling,
budget_enforcement, context_pause_threshold, notifications, cmux,
remote_questions, git, post_unit_hooks, pre_dispatch_hooks,
dynamic_routing, token_profile, phases, auto_visualize, auto_report,
parallel, verification_commands, verification_auto_fix,
verification_max_retries, search_provider, context_selection,
widget_mode, reactive_execution, github, service_tier,
forensics_dedup, show_token_cost
```

### Model Configuration
- `GSDPhaseModelConfig` — Model ID, provider, fallbacks per phase
- `UnitType` — 11 types: research-milestone, plan-milestone, research-slice, plan-slice, execute-task, reactive-execute, complete-slice, replan-slice, reassess-roadmap, run-uat, complete-milestone
- `ResolvedModelConfig` — Primary + fallbacks array

### Token & Budget
- `TokenProfile` — "budget" | "balanced" | "quality"
- `BudgetEnforcementMode` — "warn" | "pause" | "halt"

### Dynamic Routing
- `DynamicRoutingConfig` — enabled, tier_models, escalate_on_failure, budget_pressure, cross_provider, hooks

### Parallel Execution
- `ParallelConfig` — enabled, max_workers, budget_ceiling, merge_strategy, auto_merge
- `ReactiveExecutionConfig` — enabled, max_parallel, isolation_mode

### Remote Questions
- `RemoteQuestionsConfig` — Channel (slack/discord/telegram), channel_id, timeout_minutes, poll_interval_seconds

---

## 5. Hook Types

### Post-Unit Hooks
- `PostUnitHookConfig` — name, after (unit types), prompt, max_cycles, model override, artifact, retry_on, agent file, enabled
- `HookExecutionState` — Hook name, trigger unit type/id, cycle count, pending retry
- `HookDispatchResult` — Hook name, prompt, model override, synthetic unit type/id

### Pre-Dispatch Hooks
- `PreDispatchHookConfig` — name, before (unit types), action (modify/skip/replace), prepend/append/prompt, unit_type override, skip_if, model override, enabled
- `PreDispatchResult` — action, modified prompt, override unit type, model, fired hooks

### Persistence
- `PersistedHookState` — Cycle counts keyed by "hookName/unitType/unitId", savedAt
- `HookStatusEntry` — name, type (post/pre), enabled, targets, active cycle counts

---

## 6. Doctor Types (`doctor-types.ts`)

### 79 Issue Codes covering:
- Preferences validation
- Task/slice/milestone validation
- Git/worktree integrity
- Environment (node, deps, env file, ports, disk, docker, package managers, languages, git)
- Provider/auth checks
- Database integrity
- Snapshot ref bloat
- Runtime data integrity

### Structures
- `DoctorSeverity` — "info" | "warning" | "error"
- `DoctorIssue` — severity, code, scope, unitId, message, file, fixable
- `DoctorReport` — ok, basePath, issues, fixes applied, timing
- `DoctorSummary` — total/errors/warnings/infos/fixable, byCode

---

## 7. Auto-Loop Types (`auto/types.ts`)

### Constants
- `MAX_LOOP_ITERATIONS` = 500
- `MAX_RECOVERY_CHARS` = 50,000
- `BUDGET_THRESHOLDS` — Array with percentage, label, notification/cmux level

### Execution Types
- `UnitResult` — status (completed/cancelled/error), optional event
- `PhaseResult<T>` — continue | break (reason) | next (data)
- `IterationContext` — ctx, pi, session, deps, prefs, iteration, flowId, nextSeq
- `LoopState` — recent units, stuck recovery attempts
- `IterationData` — unit type/id, prompt, final prompt, pause, state, milestone, retry info

---

## 8. Remote Questions Types

- `RemoteQuestion` — ID, header, question, options, allowMultiple
- `RemotePrompt` — ID, channel, timestamps, pollInterval, questions, context
- `RemoteAnswer` — Record<questionId, answers[] + user_note>
- `RemotePromptStatus` — "pending" | "answered" | "timed_out" | "failed" | "cancelled"
- `ChannelAdapter` — Interface: name, validate(), sendPrompt(), pollAnswer(), acknowledgeAnswer()

---

## 9. Web API Contract Types

### Workspace Store (`gsd-workspace-store.tsx`)
- `WorkspaceMilestoneTarget` — id, title, roadmapPath, slices[]
- `WorkspaceSliceTarget` — id, title, done, tasks[], branch, risk, depends[]
- `WorkspaceTaskTarget` — id, title, done, planPath, summaryPath
- `WorkspaceIndex` — milestones, active scope, validation issues
- `AutoDashboardData` — active, paused, stepMode, current/completed units, costs

### Command Surface (`command-surface-contract.ts`)
- `CommandSurfaceSection` — 65 different sections
- `CommandSurfacePendingAction` — 28 action types
- `CommandSurfaceModelOption` — provider, modelId, name, reasoning, isCurrent
- `CommandSurfaceSessionStats` — session file, ID, message/token counts, cost

### Session Browser (`session-browser-contract.ts`)
- `SessionBrowserSortMode` — "threaded" | "recent" | "relevance"
- `SessionBrowserSession` — id, path, cwd, name, timestamps, messageCount, depth, threading info
- `SessionBrowserResponse` — project, query, totals, sessions

### Git Summary (`git-summary-contract.ts`)
- `GitSummaryCounts` — changed, staged, dirty, untracked, conflicts
- `GitSummaryFile` — path, repoPath, status flags
- `GitSummaryRepoResponse` — branch, mainBranch, hasChanges, counts, files

### Visualizer (`visualizer-types.ts`)
- `VisualizerMilestone/Slice/Task` — Hierarchical structure
- `CriticalPathInfo` — milestone/slice paths with slack
- `AgentActivityInfo` — currentUnit, elapsed, completedUnits, rate, cost, tokens
- `VisualizerData` — milestones, phase, totals, byPhase/Slice/Model, units, criticalPath, changelog

### Diagnostics (`diagnostics-types.ts`)
- `ForensicAnomaly` — 10 types (stuck-loop, cost-spike, timeout, crash, etc.)
- `ForensicReport` — Version, timestamp, anomalies, recentUnits, crashLock, metrics, journal
- `SkillHealthEntry` — name, uses, successRate, avgTokens, trend, staleness, cost, flagged

### Knowledge & Captures (`knowledge-captures-types.ts`)
- `KnowledgeEntry` — id, title, content, type (rule/pattern/lesson/freeform)
- `CaptureEntry` — id, text, timestamp, status, classification, resolution
- `Classification` — "quick-task" | "inject" | "defer" | "replan" | "note"

### History (`remaining-command-types.ts`)
- `HistoryUnitMetrics` — type, id, model, timestamps, tokens, cost, tool/message counts
- `HistoryProjectTotals` — units, tokens, cost, duration, counts
- `HistoryData` — units, totals, byPhase, bySlice, byModel

### Settings (`settings-types.ts`)
- `SettingsDynamicRoutingConfig` — Full routing configuration
- `SettingsRoutingHistory` — patterns, feedback, updatedAt
- `SettingsData` — preferences, routing, budget, history, totals

---

## 10. Pi SDK Types

### pi-agent-core (`types.ts`)
- `AgentLoopConfig` — model, convertToLlm, transformContext, getApiKey, steeringMessages, followUpMessages, toolExecution, beforeToolCall, afterToolCall
- `ToolExecutionMode` — "sequential" | "parallel"
- `BeforeToolCallContext/Result` — Block flag, reason
- `AfterToolCallContext/Result` — Content override, details, isError

### pi-ai (`types.ts`)
- `KnownApi` — 14 API types
- `KnownProvider` — 29+ providers
- `ThinkingLevel` — "minimal" | "low" | "medium" | "high" | "xhigh"
- `CacheRetention` — "none" | "short" | "long"
- `StreamOptions` — temperature, maxTokens, signal, apiKey, transport, caching, session
- Content types: TextContent, ThinkingContent, ImageContent, ToolCall, ServerToolUseContent, WebSearchResultContent
- `Usage` — input, output, cacheRead, cacheWrite, totalTokens, cost
- `StopReason` — "stop" | "length" | "toolUse" | "error" | "aborted"

---

## 11. Native Parser Types (13 type modules)

Located across `/packages/native/src/*/types.ts`:
- GSD parser types (frontmatter, roadmap parsing)
- AST types (code search/transformation)
- Diff types (fuzzy matching, unified diff)
- Grep types (search options, results)
- Glob types (pattern matching, cache)
- Highlight types (syntax highlighting)
- TTSR types (tool-triggered system rules)
- Clipboard types
- Image types (decode/encode/resize)
- HTML types (conversion)
- PS types (process introspection)
- FD types (file discovery)
- Text types (measurement, truncation)

---

## 12. Workflow Events (`workflow-events.ts`)

- `WorkflowEvent` — cmd, params, ts (ISO), hash (SHA256 first 16), actor (agent/system), actor_name, trigger_reason, session_id
- `appendEvent()` — Append to event-log.jsonl
- `readEvents()` — Read from JSONL
- `findForkPoint()` — Last common event between logs
- `compactMilestoneEvents()` — Archive per-milestone

---

## 13. Migration Types (`migrate/types.ts`)

Legacy .planning format structures:
- `PlanningProject` — path, content, roadmap, requirements, state, config, phases, milestones
- `PlanningRoadmap` — content, milestone sections, flat phases
- `PlanningPhase` — directory, number, slug, plans, summaries, research, verifications
- `PlanningPlan` — frontmatter, objectives, tasks, context, verification, success criteria
- `ValidationResult` — valid, issues[]
- `ValidationIssue` — file, severity, message

---

## 14. Constants

- `DEFAULT_COMMAND_TIMEOUT_MS` = 120,000
- `DEFAULT_BASH_TIMEOUT_SECS` = 120
- `DIR_CACHE_MAX` = 200
- `CACHE_MAX` = 50
- `MAX_LOOP_ITERATIONS` = 500
- `MAX_RECOVERY_CHARS` = 50,000

---

## Key Architectural Patterns

1. **Browser-Safe Type Mirrors** — Web layer has mirrored types from node-heavy server modules
2. **Hierarchical State** — Milestones → Slices → Tasks with registry and requirements
3. **Discriminated Unions** — Heavy use for actions (DispatchAction, RemotePromptRecord, EngineDispatchAction)
4. **Plugin/Hook Architecture** — Pre-dispatch and post-unit hooks with lifecycle metadata
5. **Event Sourcing** — WorkflowEvents appended to JSONL with hash deduplication
6. **Provider Abstraction** — Consistent API across 29+ LLM providers
7. **Configuration Composition** — Single GSDPreferences object combining all settings

---

## Python Rebuild Implications

### Type System Translation
| TypeScript | Python Equivalent |
|-----------|-------------------|
| `interface` | `@dataclass` or `TypedDict` or Pydantic `BaseModel` |
| `type` union | `Union[]` or `Literal[]` |
| `enum` | `enum.Enum` or `StrEnum` |
| Discriminated unions | Pydantic discriminated unions or `match` statements |
| Generic types | `Generic[T]` |
| Optional fields | `Optional[]` with default `None` |

### Recommended: Pydantic v2
- Automatic JSON serialization/deserialization
- Discriminated unions via `Discriminator`
- Runtime validation (TypeScript only validates at compile time)
- OpenAPI schema generation for free
- Used by FastAPI natively
