# Requirements: state — v41 Agent Harness & Context Control Design

**Defined:** 2026-05-07
**Milestone:** v41 (design spike — no code, only architecture documents)
**Core Value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.

**Milestone framing:** This milestone produces the **design specifications** of the Build-mode agent harness — the control plane that governs agent behavior during a Slice's execute phase. Each REQ below is a behavior the harness **shall** exhibit; v41 lands the design documents that fully specify it (formats, thresholds, mechanisms, escalation paths). Implementation of these specs ships in later milestones (v14 Build Kernel: Step FSM + Verifiers; v15 Build Core Commands).

---

## v1 Requirements

### Slice-Cycle Specification (v40 Correction)

- [ ] **SLC-01**: The Slice tier owns the four-stage cycle: discuss-slice → plan-slice → execute-slice → verify-slice. Step is a leaf artifact, **not** its own cycle. (Corrects Phase 400 spec.)
- [ ] **SLC-02**: discuss-slice produces `N-CONTEXT.md` (XML-tagged: `<domain>`, `<decisions>`, `<canonical_refs>`, `<code_context>`, `<deferred>`) and `N-DISCUSSION-LOG.md` (tabular Q/decision/options).
- [ ] **SLC-03**: plan-slice is a multi-stage internal pipeline (research → pattern-mapping → planning → validation), each stage producing one artifact: `N-RESEARCH.md`, `N-PATTERNS.md`, `stepNN-PLAN.md` (one per Step), `N-VALIDATION.md`. Validation re-runs planning on failure.
- [ ] **SLC-04**: execute-slice runs each Step's PLAN per DAG ordering and writes `stepNN-SUMMARY.md` for each Step.
- [ ] **SLC-05**: verify-slice writes `N-VERIFICATION.md` (truth table) and emits the slice-complete event.
- [ ] **SLC-06**: Slice folder canonical layout: `slices/N-name/{N-CONTEXT.md, N-DISCUSSION-LOG.md, N-RESEARCH.md, N-PATTERNS.md, N-VALIDATION.md, N-UI-SPEC.md (optional), stepNN-PLAN.md (1..M), stepNN-SUMMARY.md (1..M), N-VERIFICATION.md, RESUME.txt}`.
- [ ] **SLC-07**: v41 amends Phase 400 spec documents in-line so Slice-owns-cycle is the canonical model going forward; affected docs receive a `## v41 Amendment` header noting the change.

### Context Window Management (CTX)

- [ ] **CTX-01**: Slice token budget is **200k absolute**, regardless of model context-window size (200k or 1M+). Plan-slice sizes the Step set to ≤80% of budget (~160k of executor work).
- [ ] **CTX-02**: A fresh opencode session is spawned at every Slice boundary. Daemon initiates spawn, plugin's `chat.params` hook injects the new Slice context (parent Phase intentions, non-negotiables/crits, current Slice scope).
- [ ] **CTX-03**: Intra-Slice context pressure is handled via opencode's `session.compacting` hook (no session spawn); harness snapshots state, strips stale content, reinjects compact form. Same session_id continues.
- [ ] **CTX-04**: Threshold actions (relative to active session's context window):
  - **≤25% remaining (Emergency):** record state via compaction, prepare handoff if Step is mid-flight.
  - **≤35% remaining (Warning):** allow current task to wrap, block start of new task in same session.
  - **Slice boundary:** end session, spawn fresh.
- [ ] **CTX-05**: The compaction snapshot is a **structured artifact** (Pydantic model serialized via orjson, stored in event store), not markdown. Reinjection rehydrates from the event-store row, not a filesystem `.md` file.
- [ ] **CTX-06**: On compaction reinject, harness includes: active `stepNN-PLAN.md`, current task pointer, last task's verify result, all upstream Step `SUMMARY.md` `provides:` blocks for resolved deps, current worktree path.
- [ ] **CTX-07**: `task_id`, `step_id`, and `slice_id` survive compaction and Slice-boundary session spawn (linked via event store; reinjection events reference prior session_id).
- [ ] **CTX-08**: Harness reads opencode's context meter via plugin hook on each tool-execute event; daemon mirrors meter state to SSE for TUI consumption.

### Step / Task Decomposition (STP)

- [ ] **STP-01**: Each Step is a single `stepNN-PLAN.md` file: YAML frontmatter + XML-tagged body, matching the GSD-shape demonstrated by `~/projects/moon/.../02-01-PLAN.md`.
- [ ] **STP-02**: Step frontmatter (Pydantic-validated, `extra="forbid"`) declares: `phase`, `slice`, `step`, `type`, `wave`, `depends_on`, `files_modified`, `autonomous`, `requirements`, and the `must_haves` proof block (see PRF-01).
- [ ] **STP-03**: Step body sections (XML-tagged): `<objective>`, `<execution_context>`, `<context>` (`@`-references), `<interfaces>` (literal code excerpts from upstream artifacts), `<tasks>` (one or more `<task>` blocks), `<threat_model>`, `<verification>`, `<success_criteria>`, `<output>`.
- [ ] **STP-04**: Each `<task>` declares: `type`, `tdd` flag, `<name>`, `<files>`, `<read_first>` (exact files + line ranges), `<action>` (step-by-step prose with code blocks), `<verify><automated>` bash, `<acceptance_criteria>`, `<done>`.
- [ ] **STP-05**: Task type taxonomy: `auto`, `auto+tdd`, `checkpoint:human-verify`, `checkpoint:decision`, `checkpoint:human-action`. Behavior of each is fully specified.
- [ ] **STP-06**: plan-slice auto-selects Step granularity (coarse: 1–2 Steps; standard: 2–3; fine: 3–5) based on Slice scope and the 200k budget.
- [ ] **STP-07**: `<interfaces>` block contains literal code excerpts from upstream artifacts so the executor needs **zero codebase exploration** for upstream context.
- [ ] **STP-08**: `<read_first>` specifies exact files and line ranges per task — never "explore the codebase."

### Plan-as-Prompt (PAP)

- [ ] **PAP-01**: `stepNN-PLAN.md` IS the executor's primary system prompt at execute-slice start. The harness injects it verbatim plus runtime augmentation (worktree path, prior task results, resolved dep `provides:` blocks).
- [ ] **PAP-02**: Harness resolves all `@.planning/...` and `@-` references at injection time so the executor sees inlined content, not the literal `@` syntax.
- [ ] **PAP-03**: Plans are **mutable with audit log**: `must_haves.*` and every `<verify>` block (task-level and slice-level) are immutable; `<action>`, `<read_first>`, prose-style sections are mutable by the executor.
- [ ] **PAP-04**: Every plan edit emits a `plan_edit` event with `step_id`, diff, editor (executor/harness/human), and timestamp.
- [ ] **PAP-05**: Harness blocks attempts to edit immutable sections via the `tool.execute.before` hook; rejected edits emit `plan_edit_blocked` events.
- [ ] **PAP-06**: PLAN content stripping: harness removes upstream-only sections (e.g., plan-slice reasoning meta) at injection time to save tokens, but preserves the audit-logged original on disk.

### Boolean Proof Gate (PRF)

- [ ] **PRF-01**: Step proof gate is the `must_haves` frontmatter block:
  - `truths`: list of assertions verifiable by bash/python (e.g., "ofxparse2 is importable").
  - `artifacts`: list of `{path, provides, min_lines}` — files that must exist with content size ≥ `min_lines`.
  - `key_links`: list of `{from, to, via, pattern}` — cross-file references the harness greps for via regex.
- [ ] **PRF-02**: Each `<task>` carries its own gate: `<verify><automated>` bash (must exit 0) and `<acceptance_criteria>` bullets (each verifiable).
- [ ] **PRF-03**: Slice carries a slice-level gate: pre-commit `<verification>` bash blocks at end of each Step + `N-VERIFICATION.md` truth table at Slice wrap.
- [ ] **PRF-04**: All proof checks are **pure-machine**: bash exit codes, file existence, line counts, regex matches. No LLM-as-judge anywhere in the gate.
- [ ] **PRF-05**: Gate evaluation order: at task end → run task `<verify>` + `<acceptance_criteria>`; at Step end → run frontmatter `must_haves.*` checks; at Slice end → run slice `<verification>` + write `N-VERIFICATION.md`.
- [ ] **PRF-06**: Failure escalation: 3 strikes (advisory inject) → context clear+reinject (single shot) → 3 more strikes → human gate at 6 total. Each strike = `gate_strike` event with `check_id`, `strike_number`, `agent_response_summary`.
- [ ] **PRF-07**: A failed gate **blocks advancement**. The agent cannot start the next task/Step until every check passes. The harness enforces this via `tool.execute.before` blocking writes-to-next-step-files.

### Analysis Paralysis Guard (APG)

- [ ] **APG-01**: Harness counts consecutive read-only tool uses per active task. Read-only set: `Read`, `Grep`, `Glob`, `Explore`, `Bash` (when matching read-only command patterns).
- [ ] **APG-02**: Default threshold: **5 consecutive read-only tools** without an intervening Write/Edit/Bash-mutating call. On hit, harness injects advisory: *"5+ read-only operations. State your hypothesis and either write code or report what's blocking you."*
- [ ] **APG-03**: Threshold is configurable per step-type via plan frontmatter: research-heavy stages (discuss-slice, plan-slice/research) default to 15; execute-slice tasks default to 5.
- [ ] **APG-04**: After 3 advisory injections in the same task without resolution, harness escalates: clears context and reinjects PLAN with a focused prompt naming the specific blocker.
- [ ] **APG-05**: After escalation + 3 more advisories without resolution, harness force-stops the session and surfaces a human gate via opencode `question` tool.
- [ ] **APG-06**: Each advisory and escalation emits a `paralysis_event` with task_id, count, threshold, agent_response.

### Scope Reduction Prohibition (SRP)

- [ ] **SRP-01**: Harness validates each task's `<done>` against the Step's `must_haves.artifacts` after task completion; missing artifacts trigger gate failure (PRF-06).
- [ ] **SRP-02**: Prohibited language scan on every Write/Edit content: `v1`, `simplified`, `placeholder`, `TODO`, `FIXME`, `future`. Detection emits `scope_check` event and injects a justification request.
- [ ] **SRP-03**: Prohibited language is allowed only when paired with an explicit tracking-issue reference (e.g., `# TODO(SLC-09)` referencing a deferred-items entry).
- [ ] **SRP-04**: Harness blocks Write/Edit to files outside the Step's `files_modified` allowlist (`tool.execute.before` hook). Out-of-scope edits require a deviation event with justification before being unblocked.
- [ ] **SRP-05**: When the agent reports "this is too much for one Step," harness records a `split_recommendation` event and routes to plan-slice for re-planning rather than allowing scope reduction.
- [ ] **SRP-06**: Out-of-scope findings (issues outside the current Step's blast radius) are logged to `slices/N-name/deferred-items.md` and surface in the Slice SUMMARY.

### Deviation Rules (DEV)

- [ ] **DEV-01**: **Rule 1** — Auto-fix bugs (wrong queries, logic errors, type errors, null pointer). Max 3 attempts per issue. Each fix commits with `fix:` prefix. After 3 failures → escalate to Rule 4.
- [ ] **DEV-02**: **Rule 2** — Auto-add missing critical functionality (error handling, input validation, null checks, missing auth on protected routes, missing DB indexes). Max 3 attempts. Documented in `stepNN-SUMMARY.md` `## Deviations` section.
- [ ] **DEV-03**: **Rule 3** — Auto-fix blocking issues (missing dependency, wrong types, broken imports, build config errors). Max 3 attempts. After 3 failures → `checkpoint:decision`.
- [ ] **DEV-04**: **Rule 4** — Architectural changes (new DB table, major schema change, switching frameworks, new infrastructure). **Always** human gate via opencode `question` tool with pros/cons table. Never auto-approved, even under `--full-yolo`.
- [ ] **DEV-05**: Tiered autonomy levels:
  - **default (`--tiered`)**: `checkpoint:human-verify` auto-approves (visual sanity); `checkpoint:decision` and `checkpoint:human-action` stop.
  - **`--full-yolo`**: `human-verify` and `decision` auto-pick option 1; `human-action` and Rule 4 still stop.
  - **`--conservative`**: stop at every checkpoint.
- [ ] **DEV-06**: Per-Slice autonomy override allowed (sensitive Slices may pin `--conservative` while milestone defaults to `--tiered`). Frontmatter field `autonomy` on the Slice.
- [ ] **DEV-07**: Each deviation emits a `deviation` event with rule_id, fix_attempt_count, resolution path. SUMMARY.md `## Deviations` section is generated from these events at Step end.

### Subagent Management (SUB)

- [ ] **SUB-01**: Harness spawns subagents via opencode's `task` tool with explicit `subagent_type`. No string-prompt-only spawns.
- [ ] **SUB-02**: Static subagent whitelist per Slice stage:
  - **discuss-slice**: `researcher`, `code-mapper`, `requirements-analyzer`
  - **plan-slice**: `researcher`, `pattern-mapper`, `planner`, `plan-validator`, `plan-checker`
  - **execute-slice**: `executor`, `code-fixer`, `test-generator`, `security-auditor`
  - **verify-slice**: `verifier`, `integration-checker`, `nyquist-auditor`
- [ ] **SUB-03**: Plan frontmatter MAY narrow the whitelist (`allowed_subagents:` subset) but cannot expand it. Defense-in-depth.
- [ ] **SUB-04**: Parallel subagent count is near-uncapped (default cap **20 concurrent**, configurable). Subagents are treated as **free context** — aggressive fanout for research, pattern-mapping, validation is encouraged.
- [ ] **SUB-05**: Harness monitors subagent sessions via SSE events linked by parent `task_id`; child sessions emit `subagent_started`, `subagent_progress`, `subagent_complete` events.
- [ ] **SUB-06**: Subagent results are **structured** (typed return shape per subagent_type). Harness spot-checks: declared artifacts exist, declared commits exist (git log).
- [ ] **SUB-07**: Subagent crash recovery: max 3 restarts with continuation context. Each restart emits `subagent_restart` event.
- [ ] **SUB-08**: `task_id` storage in event store survives both compaction and Slice-boundary session spawn.
- [ ] **SUB-09**: Subagents inherit the parent Slice's autonomy level.

### Harness Architecture (HRN)

- [ ] **HRN-01**: Harness physical decomposition is documented as a layered diagram:
  - **Plugin hooks (control surface)** — chat.params, chat.message, tool.execute.before/after, session.compacting, shell.env.
  - **state-build MCP server** — plan_step, execute_step, verify_step, check_proof_gate, deviation_log, and 10+ more tools.
  - **state-daemon (background)** — event store, projector, scheduler, SSE bus, crash recovery.
- [ ] **HRN-02**: Each plugin hook's role is fully specified: signature, when it fires, what it injects/blocks/records.
- [ ] **HRN-03**: state-build MCP tool catalog is enumerated with input/output Pydantic models per tool.
- [ ] **HRN-04**: Intervention tier order (all four levels are designed):
  1. **Advisory inject** (system message into context)
  2. **Tool-block** (refuse a tool call via `tool.execute.before`)
  3. **Force context clear+reinject** (trigger `session.compacting` with reduced state)
  4. **Force-stop + human gate** (end session, surface via `question`)
- [ ] **HRN-05**: Each intervention emits a `harness_intervention` event with tier, trigger reason, target step/task.
- [ ] **HRN-06**: All human gates use opencode's `question` tool; harness never invents its own UI.
- [ ] **HRN-07**: Harness state is fully reconstructable from event store (daemon restart-safe).
- [ ] **HRN-08**: Architecture document includes a sequence diagram for one full Slice lifecycle (spawn → discuss → plan → execute with one Step → verify → close).

---

## v2 Requirements (deferred)

- **TEACH-HARNESS**: Teach-mode harness equivalent (different cycle: concept-graph → drill engine → Kolb stages, not discuss/plan/execute) — v47.
- **HARNESS-METRICS**: Long-running harness telemetry (mean strikes per Step, paralysis frequency by step-type, deviation rule firing rates) — post-v17.
- **HARNESS-LEARNING**: Pattern observer that proposes harness threshold tuning from accumulated event data — post-v17.
- **PORTABILITY-HARNESS**: Harness shims for Claude Code / Gemini CLI / Qwen Code (different hook surfaces, MCP-only control plane) — v26.

---

## Out of Scope

| Item | Reason |
|---|---|
| Implementation code | v41 is design-only. Code lands in v14+ (Build Kernel). |
| Verifier algorithm internals | Owned by v42 (Verification Algorithm Design). v41 specifies the **gate contract**, not how each verifier-type computes its result. |
| GSD command port mapping | Owned by v43 (GSD-to-state command port plan). v41 designs the harness substrate; v43 maps individual GSD commands onto it. |
| Teach-mode harness | Owned by v47. v41 is Build-only. Mode silos remain physical. |
| Rust DB / event-store rewrite | Owned by v44. Out of harness scope. |
| LLM-as-judge gates | Explicitly excluded. All proof gates are pure-machine. |
| Custom TUI for human gates | Excluded. Human gates use opencode's `question` tool exclusively. |
| Multi-Slice concurrency from one session | Excluded. One session = one Slice. Cross-Slice parallelism is achieved by spawning multiple sessions (per-Slice worktrees, scheduler-driven). |
| Mid-execution Slice scope expansion | Excluded. Scope is locked at end of plan-slice. Expansion requires re-running plan-slice (a re-plan event). |

---

## Traceability

Empty. Populated by gsd-roadmapper during ROADMAP creation.

| Requirement | Phase | Status |
|---|---|---|

**Coverage:**
- v1 requirements: TBD (filled by roadmapper)
- Mapped to phases: TBD
- Unmapped: TBD

---

*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 — initial v41 draft from HANDOFF.md + 12 locked design decisions (D-1..D-12)*
