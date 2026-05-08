# ROADMAP: v41 Agent Harness & Context Control Design

**Milestone:** v41
**Phase range:** 402–406
**Created:** 2026-05-08
**Type:** Design-phase milestone (zero code — architecture/specification documents only)
**Granularity:** fine (from config.json)

**Core value:** The Build-mode agent harness — the **control plane** that governs agent behavior during a Slice's execute phase — is fully specified across context management, plan format, proof gates, discipline guards, deviation handling, and subagent fanout, producing the design contract that v14 (Build Kernel) and v15 (Build Core Commands) implement.

**Depends on:** v40 (Build Hierarchy & Artifact System) — the harness operates on the artifacts and tier definitions specified in Phases 400 and 401. v8 (Plugin Server Hooks) — shipped; the harness is wired through the 9 hooks already implemented. v7 (Per-Session Worker), v6 (State Daemon) — shipped; the harness control plane runs across worker/daemon. v11 (Mode Enforcement) — the harness is Build-only; mode-isolation must hold.

**Locked design decisions respected (D-1..D-12):**
- D-1 Slice owns the cycle (discuss-slice → plan-slice → execute-slice → verify-slice). Step is a leaf artifact.
- D-2 Context boundary = Slice (fresh session per Slice; intra-Slice compaction).
- D-3 Slice budget = 200k absolute (not ratio-scaled).
- D-4 Snapshot artifacts are structured (Pydantic+orjson, not markdown).
- D-5 Step = `stepNN-PLAN.md` (GSD-shape: YAML frontmatter + XML body).
- D-6 Boolean proof gate = `must_haves.{truths, artifacts, key_links}` + per-task `<verify><automated>`.
- D-7 Plans mutable with audit log; `must_haves` and `<verify>` blocks immutable.
- D-8 Proof-gate fail: 3 strikes → context clear+reinject → 3 more strikes → human gate at 6 total.
- D-9 Subagents whitelist static per Slice stage; parallelism near-uncapped (default 20).
- D-10 Intervention tiers: advisory inject → tool-block → force clear+reinject → force-stop+human gate.
- D-11 Tiered autonomy: `--tiered` (default), `--full-yolo`, `--conservative`; per-Slice override allowed.
- D-12 plan-slice itself is multi-stage (research → pattern-mapping → planning → validation, with replanning).

---

## Phases

- [ ] **Phase 402: Slice-Cycle & Context Window Spec** — Slice-owns-cycle correction + 200k absolute budget, fresh-session-per-Slice, compaction snapshot, threshold actions
- [ ] **Phase 403: Step/Task Decomposition & Plan-as-Prompt** — `stepNN-PLAN.md` GSD-shape format + plan-as-prompt injection, mutability/audit, content stripping
- [ ] **Phase 404: Boolean Proof Gate & Discipline Guards** — `must_haves` proof block + per-task `<verify>`, analysis paralysis guard, scope reduction prohibition
- [ ] **Phase 405: Deviation Rules & Subagent Management** — 4-rule deviation framework + tiered autonomy, static subagent whitelist + parallel fanout
- [ ] **Phase 406: Harness Architecture Rollup** — Layered diagram (hooks + MCP + daemon), 4-tier intervention, MCP tool catalog, full-Slice sequence diagram

---

## Phase Details

### Phase 402: Slice-Cycle & Context Window Spec
**Goal**: The Slice cycle is canonically defined as the cycle owner (correcting Phase 400 in-line), and the 200k absolute Slice budget plus session/compaction protocol is fully specified — implementable without further design.
**Depends on**: Nothing (first v41 phase)
**Requirements**: SLC-01, SLC-02, SLC-03, SLC-04, SLC-05, SLC-06, SLC-07, CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CTX-07, CTX-08
**Success Criteria** (what must be TRUE):
  1. A `SLICE-CYCLE.md` spec document exists at `.planning/milestones/v41/phases/402/` defining all four stages (discuss → plan → execute → verify) with stage owner, inputs, outputs, and stage-boundary events; every artifact in the canonical Slice folder layout (SLC-06) is enumerated with its producer stage.
  2. v41 amendment headers are appended to every Phase 400 spec document affected by the Slice-owns-cycle correction (SLC-07), with each amendment block citing the prior model and the v41 canonical model.
  3. A `CONTEXT-PROTOCOL.md` spec document specifies the 200k absolute budget (CTX-01), the fresh-session-per-Slice rule (CTX-02), the intra-Slice compaction rule (CTX-03), and the threshold action table (≤25% emergency, ≤35% warning, slice-boundary spawn — CTX-04) with exact harness behaviors at each threshold.
  4. The compaction snapshot Pydantic model is defined (CTX-05) with `extra="forbid"` and an orjson serialization round-trip example; the rehydrate flow is specified including the exact reinject payload (active PLAN, current task pointer, last verify result, upstream `provides:` blocks, worktree path — CTX-06) and the event-store row schema for snapshots.
  5. The identifier-survival contract is specified (CTX-07): `task_id`, `step_id`, `slice_id` survive both compaction and Slice-boundary session spawn, and reinjection events reference the prior `session_id`. The context-meter read path (CTX-08) names the plugin hook (chat.params or tool.execute.after) and the daemon SSE event emitted to TUI.

**Plans:** 4 plans
- [ ] 402-01-slice-cycle-spec-PLAN.md — Author canonical SLICE-CYCLE.md spec doc (covers SLC-01..07)
- [ ] 402-02-context-protocol-spec-PLAN.md — Author canonical CONTEXT-PROTOCOL.md spec doc (covers CTX-01..09)
- [ ] 402-03-v40-amendments-PLAN.md — Append v41 amendment blocks to 7 v40 spec docs (closes SLC-07)
- [ ] 402-04-requirements-ctx-09-PLAN.md — Add CTX-09 (Reactive overflow recovery) to REQUIREMENTS.md + update ROADMAP coverage

---

### Phase 403: Step/Task Decomposition & Plan-as-Prompt
**Goal**: The `stepNN-PLAN.md` format is fully specified (frontmatter schema + XML body) and the plan-as-prompt injection / mutability / audit-log architecture is implementable verbatim.
**Depends on**: Phase 402
**Requirements**: STP-01, STP-02, STP-03, STP-04, STP-05, STP-06, STP-07, STP-08, PAP-01, PAP-02, PAP-03, PAP-04, PAP-05, PAP-06
**Success Criteria** (what must be TRUE):
  1. A `STEP-PLAN-FORMAT.md` spec document exists with a complete `stepNN-PLAN.md` template (STP-01) and a Pydantic-validated frontmatter schema (`extra="forbid"`) covering every required field from STP-02 (`phase`, `slice`, `step`, `type`, `wave`, `depends_on`, `files_modified`, `autonomous`, `requirements`, `must_haves`).
  2. Every XML body section from STP-03 (`<objective>`, `<execution_context>`, `<context>`, `<interfaces>`, `<tasks>`, `<threat_model>`, `<verification>`, `<success_criteria>`, `<output>`) and every `<task>` sub-tag from STP-04 (`type`, `tdd`, `<name>`, `<files>`, `<read_first>`, `<action>`, `<verify><automated>`, `<acceptance_criteria>`, `<done>`) is documented with at least one literal example excerpt drawn from the GSD-shape demonstration plan.
  3. The five task types from STP-05 (`auto`, `auto+tdd`, `checkpoint:human-verify`, `checkpoint:decision`, `checkpoint:human-action`) each have a behavior specification covering: harness action on encountering the type, gate/checkpoint mechanism, autonomy interaction. The granularity-selection algorithm (STP-06: coarse 1–2 / standard 2–3 / fine 3–5) is specified as a deterministic function of Slice scope and 200k budget.
  4. The `<interfaces>` literal-excerpt rule (STP-07) and the `<read_first>` exact-files-with-line-ranges rule (STP-08) are specified with an explicit zero-codebase-exploration contract for executors; counterexamples (vague references) are listed as rejection cases.
  5. A `PLAN-AS-PROMPT.md` spec document specifies the injection flow (PAP-01 verbatim PLAN injection + runtime augmentation), the `@`-reference resolution rule (PAP-02), the mutability matrix (PAP-03: `must_haves.*` and every `<verify>` block immutable; `<action>`, `<read_first>`, prose mutable), the `plan_edit` event schema (PAP-04), the immutable-section block mechanism via `tool.execute.before` plus `plan_edit_blocked` event (PAP-05), and the content-stripping rule that preserves the on-disk audit-logged original (PAP-06).

**Plans**: TBD

---

### Phase 404: Boolean Proof Gate & Discipline Guards
**Goal**: The pure-machine boolean proof gate is fully specified at task / Step / Slice levels, and the analysis-paralysis and scope-reduction discipline guards are specified with exact thresholds, escalation paths, and prohibited-language scans — implementable as pure-machine checks (no LLM-as-judge).
**Depends on**: Phase 403
**Requirements**: PRF-01, PRF-02, PRF-03, PRF-04, PRF-05, PRF-06, PRF-07, APG-01, APG-02, APG-03, APG-04, APG-05, APG-06, SRP-01, SRP-02, SRP-03, SRP-04, SRP-05, SRP-06
**Success Criteria** (what must be TRUE):
  1. A `PROOF-GATE.md` spec document defines the `must_haves` frontmatter block (PRF-01) with Pydantic schemas for `truths` (bash/python assertion), `artifacts` (`{path, provides, min_lines}`), and `key_links` (`{from, to, via, pattern}`); per-task `<verify><automated>` + `<acceptance_criteria>` (PRF-02); and the slice-level pre-commit `<verification>` + `N-VERIFICATION.md` truth table (PRF-03). Every check type is annotated with its pure-machine evaluator (bash exit code, file existence, `wc -l ≥ min_lines`, regex grep) — PRF-04.
  2. The gate evaluation order (PRF-05: at task end → task `<verify>` + `<acceptance_criteria>`; at Step end → frontmatter `must_haves.*`; at Slice end → slice `<verification>` + write `N-VERIFICATION.md`) is specified as a sequence diagram or numbered protocol, with the exact harness tool (`tool.execute.before` write-block) that enforces "fail blocks advancement" (PRF-07).
  3. The 6-strike escalation ladder (PRF-06: 3 advisory strikes → context clear+reinject → 3 more strikes → human gate at strike 6) is specified with the `gate_strike` event schema (`check_id`, `strike_number`, `agent_response_summary`) and the exact harness action at each strike count.
  4. An `ANALYSIS-PARALYSIS-GUARD.md` spec document defines the read-only tool set (APG-01: Read, Grep, Glob, Explore, Bash-when-read-only-pattern), the default 5-consecutive threshold (APG-02) with the exact advisory message text, the per-step-type threshold table (APG-03: discuss-slice/plan-slice/research = 15; execute-slice = 5), the 3-advisory→clear-and-reinject escalation (APG-04), the 3-more-advisories→force-stop+human-gate (APG-05), and the `paralysis_event` schema (APG-06: `task_id`, `count`, `threshold`, `agent_response`).
  5. A `SCOPE-PROHIBITION.md` spec document defines the `<done>`-vs-`must_haves.artifacts` cross-check (SRP-01), the prohibited-language scan list (SRP-02: `v1`, `simplified`, `placeholder`, `TODO`, `FIXME`, `future`) with the `scope_check` event schema, the tracking-issue exception pattern (SRP-03: `# TODO(SLC-09)` style), the `files_modified` allowlist enforcement via `tool.execute.before` and the deviation-event unblock path (SRP-04), the split-recommendation routing to plan-slice (SRP-05) with `split_recommendation` event, and the `deferred-items.md` out-of-scope logging path (SRP-06).

**Plans**: TBD

---

### Phase 405: Deviation Rules & Subagent Management
**Goal**: The 4-rule deviation framework with tiered autonomy is fully specified, and the subagent management protocol (whitelist, parallel fanout, structured returns, crash recovery) is specified as a complete control-plane subsystem.
**Depends on**: Phase 404
**Requirements**: DEV-01, DEV-02, DEV-03, DEV-04, DEV-05, DEV-06, DEV-07, SUB-01, SUB-02, SUB-03, SUB-04, SUB-05, SUB-06, SUB-07, SUB-08, SUB-09
**Success Criteria** (what must be TRUE):
  1. A `DEVIATION-RULES.md` spec document defines all four rules with category, max-attempts (3), commit-prefix convention, and escalation path: Rule 1 auto-fix bugs (DEV-01), Rule 2 auto-add critical functionality with `## Deviations` SUMMARY section (DEV-02), Rule 3 auto-fix blocking issues with checkpoint:decision escalation (DEV-03), Rule 4 architectural changes always-human-gate via opencode `question` tool with pros/cons table never auto-approved even under `--full-yolo` (DEV-04).
  2. The tiered autonomy table (DEV-05: `--tiered` default / `--full-yolo` / `--conservative`) is specified with per-checkpoint-type behavior (`human-verify`, `decision`, `human-action`) and the always-stop reservation for Rule 4. The per-Slice autonomy override mechanism (DEV-06: `autonomy` frontmatter field on the Slice) is documented with the precedence rule (Slice override beats milestone default).
  3. The `deviation` event schema (DEV-07: `rule_id`, `fix_attempt_count`, `resolution`) is defined and the SUMMARY.md `## Deviations` section generation algorithm (event-stream → markdown) is specified at Step end.
  4. A `SUBAGENT-MANAGEMENT.md` spec document defines the typed-spawn rule (SUB-01: opencode `task` tool with explicit `subagent_type`, no string-prompt-only), the static whitelist per Slice stage (SUB-02: discuss/plan/execute/verify rosters with named subagent_types), the narrowing-only frontmatter override (SUB-03: `allowed_subagents` may subset but not expand), and the 20-default parallel cap with "subagents are free context" guidance (SUB-04).
  5. The subagent monitoring protocol is specified: SSE events linked by parent `task_id` with `subagent_started`/`subagent_progress`/`subagent_complete` schemas (SUB-05), the structured return shape per subagent_type with artifact/commit spot-checks via git log (SUB-06), the 3-restart crash-recovery with `subagent_restart` event (SUB-07), `task_id` survival across compaction and Slice-boundary spawn (SUB-08, cross-references CTX-07), and autonomy inheritance from parent Slice (SUB-09).

**Plans**: TBD

---

### Phase 406: Harness Architecture Rollup
**Goal**: All prior v41 specs are rolled up into a single layered harness architecture document with full plugin-hook role inventory, MCP tool catalog, 4-tier intervention specification, event-replay reconstruction guarantee, and a worked sequence diagram for one full Slice lifecycle.
**Depends on**: Phase 405
**Requirements**: HRN-01, HRN-02, HRN-03, HRN-04, HRN-05, HRN-06, HRN-07, HRN-08
**Success Criteria** (what must be TRUE):
  1. A `HARNESS-ARCHITECTURE.md` spec document contains a layered diagram (HRN-01) showing the three layers — plugin hooks (chat.params, chat.message, tool.execute.before/after, session.compacting, shell.env), state-build MCP server (plan_step, execute_step, verify_step, check_proof_gate, deviation_log + 10+ more), and state-daemon (event store, projector, scheduler, SSE bus, crash recovery) — with arrows for control flow.
  2. Each plugin hook has a role specification (HRN-02) covering signature (TS type from `@opencode-ai/plugin`), firing trigger, what it injects/blocks/records, and which v41 requirement it implements (back-cross-reference to CTX, PAP, PRF, APG, SRP, DEV, SUB).
  3. The state-build MCP tool catalog (HRN-03) enumerates every tool with input and output Pydantic models (`extra="forbid"`); every harness operation specified in Phases 402–405 is mapped to at least one MCP tool.
  4. The 4-tier intervention ladder (HRN-04: advisory inject → tool-block → force clear+reinject → force-stop+human gate) is documented with the trigger rules from each prior phase that escalate at each tier; the `harness_intervention` event schema (HRN-05: `tier`, `trigger_reason`, `target_step_or_task`) is defined; the human-gate-only-via-opencode-`question`-tool rule is asserted (HRN-06).
  5. The event-replay reconstruction proof (HRN-07: harness state fully reconstructable from event store, daemon restart-safe) is specified with a list of events that must replay to rebuild harness state, and a sequence diagram (HRN-08) walks through one full Slice lifecycle (spawn → discuss → plan → execute with one Step → verify → close) showing every event emitted and every harness intervention point.

**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 402. Slice-Cycle & Context Window Spec | 0/4 | Plans drafted | - |
| 403. Step/Task Decomposition & Plan-as-Prompt | 0/0 | Not started | - |
| 404. Boolean Proof Gate & Discipline Guards | 0/0 | Not started | - |
| 405. Deviation Rules & Subagent Management | 0/0 | Not started | - |
| 406. Harness Architecture Rollup | 0/0 | Not started | - |

---

## Requirement Coverage

| Category | Count | REQ-IDs | Phase |
|----------|-------|---------|-------|
| SLC — Slice-Cycle Specification (v40 Correction) | 7 | SLC-01..SLC-07 | 402 |
| CTX — Context Window Management | 8 | CTX-01..CTX-08 | 402 |
| STP — Step / Task Decomposition | 8 | STP-01..STP-08 | 403 |
| PAP — Plan-as-Prompt | 6 | PAP-01..PAP-06 | 403 |
| PRF — Boolean Proof Gate | 7 | PRF-01..PRF-07 | 404 |
| APG — Analysis Paralysis Guard | 6 | APG-01..APG-06 | 404 |
| SRP — Scope Reduction Prohibition | 6 | SRP-01..SRP-06 | 404 |
| DEV — Deviation Rules | 7 | DEV-01..DEV-07 | 405 |
| SUB — Subagent Management | 9 | SUB-01..SUB-09 | 405 |
| HRN — Harness Architecture | 8 | HRN-01..HRN-08 | 406 |
| **Total** | **72** | — | **100% mapped** |

---

## Out of Scope (v41)

- **Implementation code** — v41 is design-only. Code lands in v14+ (Build Kernel) and v15 (Build Core Commands).
- **Verifier algorithm internals** — Owned by v42 (Build Quality Pipeline). v41 specifies the gate contract (PRF), not how each verifier-type computes its result.
- **GSD command port mapping** — Owned by v43 (GSD-to-state command port plan). v41 designs the harness substrate; v43 maps individual GSD commands onto it.
- **Teach-mode harness** — Owned by v47. v41 is Build-only. Mode silos remain physical.
- **Rust DB / event-store rewrite** — Owned by v44.
- **LLM-as-judge gates** — Explicitly excluded. All proof gates are pure-machine.
- **Custom TUI for human gates** — Excluded. Human gates use opencode's `question` tool exclusively.
- **Multi-Slice concurrency from one session** — Excluded. One session = one Slice. Cross-Slice parallelism is achieved by spawning multiple sessions.
- **Mid-execution Slice scope expansion** — Excluded. Scope is locked at end of plan-slice. Expansion requires re-running plan-slice (a re-plan event).

---

*Roadmap created: 2026-05-08*
