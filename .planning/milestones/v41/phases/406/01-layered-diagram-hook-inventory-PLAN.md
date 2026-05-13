---
phase: 406
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
autonomous: false
requirements:
  - HRN-01
  - HRN-02

must_haves:
  truths:
    - "HARNESS-ARCHITECTURE.md exists at .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md and is created by THIS plan (Plan 01); the file did not exist before. Plans 02, 03, 04 append §3, §4, §5–6 respectively."
    - "File preamble (§0) is rendered verbatim including: title heading `# Harness Architecture (Canonical, v41 Rollup)`; Phase: 406; Status: Canonical (v41); Requirements covered: HRN-01..HRN-08; Build-mode only header note (`state.build.*` MUST NOT import `state.teach.*`); section ordering preview (§1 Layered diagram, §2 Plugin hook inventory, §3 state-build MCP tool catalog, §4 4-tier intervention ladder + harness_intervention event + human-gate-only-via-question, §5 Event-replay reconstruction proof, §6 Full-Slice lifecycle sequence diagram); rollup vs source-of-truth note ('The rollup is the index, not the source of truth' — each prior 402–405 spec stays canonical for its own subsystem)."
    - "§1 Layered diagram (HRN-01) renders ONE Mermaid `flowchart` (or `graph TB`) code block with THREE labelled subgraphs: `Hooks layer` (6 hook boxes: chat.params, chat.message, tool.execute.before, tool.execute.after, session.compacting, shell.env), `state-build MCP server` (≥12 tool boxes from the 14-tool roster — minimum: complete_task, complete_slice, request_step_split, scope_deviation_request, log_deviation, dispatch_subagent, check_proof_gate, emit_advisory, force_clear_and_reinject, surface_human_gate, query_context_meter, request_compaction_snapshot, query_event_store, record_plan_edit), `state-daemon` (5 service boxes: event store, projector, scheduler, SSE bus, crash recovery / orphan reconciliation)."
    - "§1 Mermaid block contains named-arrow edges with operation labels (NOT bare arrows). Minimum labelled edges: `tool.execute.before --> log_deviation`, `tool.execute.before --> dispatch_subagent`, `subagent_complete --> spot_check_stack`, `session.compacting --> request_compaction_snapshot`, `chat.params --> query_context_meter`, projector --> SSE bus, scheduler --> dispatch handler, crash recovery --> orphan reconciliation. Mirrors gsd-2 `kb/cross-layer-communication-map.md` §1 layered Mermaid topology."
    - "§1 includes a 'Layered decomposition (HRN-01)' prose paragraph documenting the partition: plugin hooks are sensors + enforcers (READ harness state, BLOCK writes); state-build MCP tools are agent-driven actions (the agent CALLS them to signal intent); state-daemon owns the decision logic, event store, projector, scheduler, SSE bus, and crash recovery. Cites carry-forward discipline 'plugin-as-thin-reporter, daemon-decides' from Phase 402."
    - "§1 includes a 'Mode-isolation note' subsection asserting that `state_build/*` modules MUST NOT import `state_teach/*`; CI import-graph lint enforces; events live in `BUILD_ONLY_EVENT_PREFIXES`. Cross-references PROJECT.md cardinal rule and 405 carry-forward."
    - "§2 Plugin Hook Inventory (HRN-02) renders SIX hook subsections, one per hook, in the literal order: chat.params, chat.message, tool.execute.before, tool.execute.after, session.compacting, shell.env. Each subsection has a literal heading `### {hook_name}`."
    - "Each of the 6 hook subsections covers four fields verbatim: (1) **Signature** — TypeScript type signature from `@opencode-ai/plugin` rendered in a `typescript` code-fence; (2) **Firing trigger** — when opencode invokes the hook (1-2 sentences); (3) **Role: inject / block / record** — what the harness does in this hook (1-3 bullets); (4) **v41 REQ cross-reference** — which v41 requirement(s) this hook implements (CTX-02/CTX-03/CTX-08, PAP-01/PAP-02/PAP-05, PRF-07, APG-01/APG-04, SRP-02/SRP-04, DEV-04 question-tool surface, SUB-03/SUB-04 dispatch routing — distributed across the 6 hooks per the hooks-vs-MCP partition)."
    - "chat.params subsection cross-references at minimum: CTX-02 (Slice-boundary session spawn injects new Slice context), PAP-01 (verbatim PLAN injection), PAP-02 (@-reference resolution at injection time), CTX-06 (reinject payload after compaction)."
    - "tool.execute.before subsection cross-references at minimum: PAP-05 (immutable-section block on plan_edit attempts), PRF-07 (gate-failing next-task write block), SRP-02 (prohibited-language scan), SRP-04 (files_modified allowlist), DEV-04 (architectural change classification step — log_deviation routing), SUB-03 (subagent whitelist enforcement), SUB-04 (parallel-cap accounting). Lists the 7-layer write-block stack order verbatim from 405 PROOF-GATE.md + this rollup's layer 5-7 additions."
    - "session.compacting subsection cross-references at minimum: CTX-03 (intra-Slice compaction trigger), CTX-05 (structured snapshot via Pydantic+orjson), CTX-06 (reinject payload). Notes that compaction never spawns a new session_id (CTX-03 vs CTX-02 distinction)."
    - "tool.execute.after subsection cross-references at minimum: APG-01 (consecutive read-only counter increment), SUB-05 (subagent SSE event correlation), CTX-08 (context-meter mirror to SSE)."
    - "shell.env subsection cross-references at minimum: STATE-Task / STATE-DeviationRule / STATE-Subagent-Invocation trailer env-var injection for git commits inside subagent sessions (DEVIATION-RULES.md commit-trailer convention)."
    - "chat.message subsection documents harness use for SSE-mirroring agent turns to the daemon event store (no harness blocking; thin-reporter discipline)."
    - "§2 includes a closing 'Hook surface = sensors + enforcers' summary paragraph contrasting with §3 (MCP tools = agent-driven actions); cites the hooks-vs-MCP partition from 406-CONTEXT.md `<decisions>` 'MCP tool catalog (Area 3 of discussion)' subsection verbatim."
    - "HARNESS-ARCHITECTURE.md does NOT contain the literal string `GSD-` anywhere (project naming-discipline rule — all identifiers are STATE-* / state-*). gsd-2 may appear ONLY as a directory-name reference (e.g., `gsd-2`, `gsd2deconstruction/kb/`) — never as an identifier prefix."
  artifacts:
    - path: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      provides: "Phase 406 canonical rollup spec doc — §0 preamble + §1 Layered diagram (HRN-01) + §2 Plugin hook inventory (HRN-02). Plans 02/03/04 append §3/§4/§5–6 respectively."
      min_lines: 350
  key_links:
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "§2 chat.params and session.compacting hooks cite CTX-02 / CTX-03 / CTX-05 / CTX-06 / CTX-08 verbatim for hook role specification"
      pattern: "CONTEXT-PROTOCOL\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      via: "§2 chat.params and tool.execute.before hooks cite PAP-01 / PAP-02 / PAP-05 verbatim for inject + block behaviors"
      pattern: "PLAN-AS-PROMPT\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "§2 tool.execute.before hook cites PRF-07 + the 4-layer write-block stack precedent extended by Phase 405 to 7 layers"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      via: "§2 tool.execute.before hook cites SUB-03 + SUB-04 + the 7-layer extended write-block stack; the dispatch_subagent box in §1 references this spec"
      pattern: "SUBAGENT-MANAGEMENT\\.md"
---

<objective>
Create the canonical `HARNESS-ARCHITECTURE.md` spec document — the Phase 406 rollup — and author its first two sections: §1 the three-layer Mermaid diagram (HRN-01) showing plugin hooks → state-build MCP server → state-daemon with named-arrow edges, and §2 the plugin hook inventory (HRN-02) enumerating all six hooks (chat.params, chat.message, tool.execute.before, tool.execute.after, session.compacting, shell.env) with signature + firing trigger + role + v41-REQ back-cross-reference.

This plan ALSO authors §0 — the file preamble — because it creates the file. Plans 02, 03, 04 append §3, §4, §5–6 respectively. The four plans share a single file (`HARNESS-ARCHITECTURE.md`); the wave ordering 1→2→3→4 enforces sequential append.

Purpose: HRN-01 + HRN-02 fully covered. Downstream consumers — Plan 02 (appends §3 MCP tool catalog and references the §1 layered diagram's MCP server subgraph for box-name consistency), Plan 03 (appends §4 intervention ladder and references the §2 hook inventory for tier-1 advisory inject site and tier-2 tool-block site), Plan 04 (appends §5 replay proof and §6 sequence diagram, references §2 chat.params + session.compacting for restart hook resume sequence) — all read from this file.

Output: One markdown spec doc at `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md`, ≥350 lines, fully populated with §0 preamble + §1 Mermaid 3-layer diagram with named-arrow edges + §2 six-hook inventory with TS signatures + role bullets + v41-REQ cross-references + Mode-isolation note + the hooks-vs-MCP partition summary. No `GSD-` identifier appears.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/STATE.md
@.planning/milestones/v41/ROADMAP.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/phases/406/406-CONTEXT.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
@.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
@.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
@.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — The 14-tool MCP roster (verbatim from 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3 of discussion)" subsection; Plan 02 fully details these; Plan 01 only needs the names for §1 diagram boxes):

```
| Tool name                                     | Owning phase | Source spec |
|---|---|---|
| complete_task                                 | 403/404      | STEP-PLAN-FORMAT.md §5 task-type behaviors; PROOF-GATE.md §6 strike trigger |
| complete_slice                                | 402/404      | SLICE-CYCLE.md run-slice → verify-slice transition; PROOF-GATE.md §4 Slice-end |
| request_step_split                            | 404          | SCOPE-PROHIBITION.md SRP-05 |
| scope_deviation_request                       | 404          | SCOPE-PROHIBITION.md "scope_deviation_request MCP Tool Flow" |
| log_deviation                                 | 405          | DEVIATION-RULES.md §3 |
| dispatch_subagent                             | 405          | SUBAGENT-MANAGEMENT.md §2 |
| check_proof_gate                              | 404          | PROOF-GATE.md §4 |
| emit_advisory                                 | 406 (new)    | HRN-04 tier 1 |
| force_clear_and_reinject                      | 406 (new)    | HRN-04 tier 3 |
| surface_human_gate                            | 406 (new)    | HRN-04 tier 4 + HRN-06 |
| query_context_meter                           | 402          | CONTEXT-PROTOCOL.md CTX-08 |
| request_compaction_snapshot                   | 402          | CONTEXT-PROTOCOL.md CTX-03 |
| query_event_store                             | 406 (new)    | HRN-07 reconstruction protocol |
| record_plan_edit                              | 403          | PLAN-AS-PROMPT.md §6 |
```

Excerpt B — TypeScript hook signatures from `@opencode-ai/plugin` (cite source path; render verbatim from gsd-2 kb where available):

```typescript
// Reference: ~/projects/gsd2deconstruction/kb/extensions/plugin-system.md §"Plugin hook surface"
// 6 hooks consumed by state's harness:

// chat.params: invoked before each agent turn; harness injects PLAN content + reinject payload
type ChatParamsHook = (ctx: ChatParamsContext) => ChatParams | Promise<ChatParams>;

// chat.message: invoked on each user/assistant message; harness mirrors to SSE event store
type ChatMessageHook = (ctx: ChatMessageContext) => void | Promise<void>;

// tool.execute.before: invoked before any tool call; harness applies 7-layer write-block stack
type ToolExecuteBeforeHook = (ctx: ToolExecuteBeforeContext) => ToolBlockResult | Promise<ToolBlockResult>;

// tool.execute.after: invoked after a tool call resolves; harness updates counters + context-meter mirror
type ToolExecuteAfterHook = (ctx: ToolExecuteAfterContext) => void | Promise<void>;

// session.compacting: invoked when opencode initiates intra-session compaction; harness writes structured snapshot + reinject payload
type SessionCompactingHook = (ctx: SessionCompactingContext) => CompactionResult | Promise<CompactionResult>;

// shell.env: invoked before shell commands; harness injects STATE-* trailer env vars for git commits
type ShellEnvHook = (ctx: ShellEnvContext) => Env | Promise<Env>;
```

Excerpt C — Hooks-vs-MCP-tools partition (verbatim from 406-CONTEXT.md `<decisions>` "MCP tool catalog" subsection):

```
plugin hooks are sensors + enforcers; MCP tools are agent-driven actions.
Hooks (chat.params/message, tool.execute.before/after, session.compacting, shell.env) READ harness state and BLOCK writes;
MCP tools (log_deviation, dispatch_subagent, etc.) are what the agent calls to signal intent.
Preserves 402's "plugin is thin reporter, daemon decides" and 405's "typed-spawn only via MCP tool" disciplines.
```

Excerpt D — 7-layer tool.execute.before write-block stack (from Phase 405 SUBAGENT-MANAGEMENT.md §5; rendered here for §2 tool.execute.before subsection):

```
1. Phase 403 immutability check (PAP-05).
2. Phase 404 `files_modified` allowlist (SRP-04).
3. Phase 404 prohibited-language scan (SRP-02).
4. Phase 404 `<discovered_threats>` append-only carve-out (SRP-04 ancillary).
5. Phase 405 `log_deviation` routing + cross-validation (DEVIATION-RULES.md §4).
6. Phase 405 `dispatch_subagent` routing + whitelist enforcement + parallel-cap accounting (SUBAGENT-MANAGEMENT.md §5–6).
7. Phase 405 arch-pattern allowlist match for Rule-4 auto-promotion (DEVIATION-RULES.md §5).
```
</interfaces>

<threat_model>
Phase 406 is design-only. HARNESS-ARCHITECTURE.md introduces no production attack surface — it is a markdown specification rolled up from 402–405. Threats considered (per `<security_constraint>` baseline applicable to a markdown spec doc):

- **[med] Spec inaccuracy could mislead v14 implementation.** Mitigation: every operative contract (TS hook signatures, MCP tool names, write-block stack ordering, v41 REQ cross-references) is rendered verbatim from upstream specs (Phase 402–405) or from 406-CONTEXT.md's `<decisions>` block which is itself derived from those upstream specs. Drift between this rollup and a source spec is detectable by grep (e.g., `grep "ChainDispatch" HARNESS-ARCHITECTURE.md` must match the literal in 405 SUBAGENT-MANAGEMENT.md). The 406-CONTEXT.md `<specifics>` note 'The rollup is the index, not the source of truth' is rendered verbatim in §0.
- **[med] Naming-discipline drift (STATE-* vs GSD-*).** Mitigation: §0 header asserts STATE-* discipline; verify-block bash includes `! grep -qE '\bGSD-' "$F"` which fails the plan if a `GSD-` identifier appears. gsd-2 may appear as a directory reference (e.g., `~/projects/gsd2deconstruction/kb/`) but never as an identifier prefix.
- **[low] Mode-isolation drift.** Mitigation: §1 includes an explicit Mode-isolation subsection asserting `state_build/*` MUST NOT import `state_teach/*`; CI import-graph lint enforces. Carry-forward from 405.

No production code lands. No secrets, no network calls, no untrusted input parsed by this spec doc. The spec describes runtime mechanisms; threats listed above target v14 implementation, which this Phase 406 rollup constrains via authoritative cross-references to 402–405 source specs.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Create HARNESS-ARCHITECTURE.md with §0 preamble + §1 layered Mermaid diagram (HRN-01)</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<domain>` Phase Boundary (verbatim source for §0 preamble and HRN-01..HRN-08 section preview)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "Document structure (Area 1)" (verbatim source for section ordering)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "Diagram form & fidelity (Area 2)" (verbatim source for §1 Mermaid box-per-component + named-arrow rules)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" — tool roster (14 names) for §1 MCP server subgraph boxes
    - .planning/milestones/v41/REQUIREMENTS.md lines 118-126 (HRN-01, HRN-02 verbatim)
    - .planning/milestones/v41/phases/405/01-deviation-rules-spec-PLAN.md lines 190-260 (Section 1 preamble convention reference)
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md (search "Mermaid|graph TB" — Mermaid styling precedent)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (search "sequenceDiagram|flowchart" — Mermaid styling precedent)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md lines 1-50 (file-header convention)
  </read_first>

  <action>
    Create the file `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` from scratch. Author §0 (preamble) and §1 (layered Mermaid diagram + prose).

    **Concrete content from 406-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 0 — File preamble

    Render the header block verbatim (using literal markdown):

    ```
    # Harness Architecture (Canonical, v41 Rollup)

    > **Phase:** 406
    > **Status:** Canonical (v41)
    > **Requirements covered:** HRN-01, HRN-02, HRN-03, HRN-04, HRN-05, HRN-06, HRN-07, HRN-08
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
    > **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Never `GSD-*`.
    > **Authoritative ordering:** Upstream specs (402–405) are the source of truth for their own subsystems; this rollup is the consolidation lens. Drift between this file and an upstream source spec is a documented defect.
    ```

    1-paragraph overview (verbatim from 406-CONTEXT.md `<specifics>` first bullet): "The rollup is the index, not the source of truth." Each prior 402–405 spec stays canonical for its own subsystem; HARNESS-ARCHITECTURE.md is the consolidation lens that lets a reader see the whole harness at once without reading 480k of prior specs first. Per-section content depth follows the hybrid cross-ref rule: inline operative contracts (Pydantic schemas + MCP tool signatures + event payloads); pointer-only for explanatory prose.

    Sub-section `## Section ordering`:

    Render verbatim:
    1. §1 Layered diagram (HRN-01) — this plan (Plan 01).
    2. §2 Plugin hook inventory (HRN-02) — this plan (Plan 01).
    3. §3 state-build MCP tool catalog (HRN-03) — Plan 02 of this phase.
    4. §4 4-tier intervention ladder + `harness_intervention` event + human-gate-only-via-`question` (HRN-04, HRN-05, HRN-06) — Plan 03 of this phase.
    5. §5 Event-replay reconstruction proof (HRN-07) — Plan 04 of this phase.
    6. §6 Full-Slice lifecycle sequence diagram (HRN-08) — Plan 04 of this phase.

    Sub-section `## Cross-references`:
    "Every section back-cross-references the canonical 402–405 spec that owns the underlying mechanism. The 12 canonical prior specs (SLICE-CYCLE.md, CONTEXT-PROTOCOL.md, STEP-PLAN-FORMAT.md, PLAN-AS-PROMPT.md, STEP-EVENTS.md, EXEMPLAR-stepNPLAN.md, PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, SCOPE-PROHIBITION.md, DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md) stay as-shipped; this rollup adds no amendments to them."

    ### Section 1 — Layered Diagram (HRN-01)

    Heading: `## §1 Layered Diagram (HRN-01)`.

    1-paragraph intro: the harness is decomposed into three physical layers — plugin hooks (control surface inside opencode), state-build MCP server (agent-callable tool surface), state-daemon (background decision logic). The three layers communicate via three primary channels: plugin → daemon HTTP+SSE for hook events, agent → MCP server stdio for tool calls, daemon → SSE bus for cross-component event distribution. Mirrors gsd-2 `kb/cross-layer-communication-map.md` §1 layered Mermaid topology adapted to state's 3-layer (vs gsd-2's 5-layer) decomposition.

    Sub-section `### Layered topology`:

    Render one Mermaid `flowchart TB` (or `graph TB`) code block. Structure:

    ```mermaid
    flowchart TB
      subgraph Hooks ["Plugin hooks (control surface)"]
        H_CP[chat.params]
        H_CM[chat.message]
        H_TEB[tool.execute.before]
        H_TEA[tool.execute.after]
        H_SC[session.compacting]
        H_SE[shell.env]
      end

      subgraph MCP ["state-build MCP server"]
        T_CT[complete_task]
        T_CS[complete_slice]
        T_RSS[request_step_split]
        T_SDR[scope_deviation_request]
        T_LD[log_deviation]
        T_DS[dispatch_subagent]
        T_CPG[check_proof_gate]
        T_EA[emit_advisory]
        T_FCR[force_clear_and_reinject]
        T_SHG[surface_human_gate]
        T_QCM[query_context_meter]
        T_RCS[request_compaction_snapshot]
        T_QES[query_event_store]
        T_RPE[record_plan_edit]
      end

      subgraph Daemon ["state-daemon (background)"]
        D_ES[(event store sqlite)]
        D_PR[projector]
        D_SC[scheduler]
        D_SSE[SSE bus]
        D_CR[crash recovery / orphan reconciliation]
      end

      H_TEB -- "log_deviation routing" --> T_LD
      H_TEB -- "dispatch_subagent routing" --> T_DS
      H_TEB -- "files_modified + immutability + prohibited-language stack" --> D_PR
      H_CP -- "PLAN injection + reinject payload" --> D_PR
      H_CP -- "context-meter read" --> T_QCM
      H_SC -- "snapshot + reinject" --> T_RCS
      H_TEA -- "counter tick + context-meter mirror" --> D_PR
      H_CM -- "turn mirror" --> D_ES
      H_SE -- "STATE-* trailer env vars" --> D_ES

      T_LD -- "Deviation event" --> D_ES
      T_DS -- "subagent_started event" --> D_ES
      T_CT -- "task_complete event" --> D_PR
      T_CS -- "slice_complete event" --> D_PR
      T_CPG -- "must_haves evaluator dispatch" --> D_PR
      T_EA -- "advisory injection" --> D_PR
      T_FCR -- "force compaction + reinject" --> H_SC
      T_SHG -- "opencode question tool surface" --> D_PR
      T_RCS -- "CompactionSnapshot row" --> D_ES
      T_QES -- "event-store read" --> D_ES
      T_RPE -- "plan_edit event" --> D_ES

      D_ES --> D_PR
      D_PR --> D_SSE
      D_SC -- "dispatch queue + parallel cap" --> T_DS
      D_CR -- "orphan probe + rehydrate" --> D_ES
      D_SSE -- "TUI + projection consumers" --> Daemon
    ```

    (Executor: the diagram body above is a starting structure; you MAY refine arrow ordering and add additional labelled edges for readability, but every node listed above MUST appear, and at minimum the 8 labelled edges listed in the must_haves truths block must be present.)

    Sub-section `### Layered decomposition (HRN-01)`:

    Render verbatim:
    - **Plugin hooks (control surface).** Six TypeScript hooks fired by opencode inside the agent session. State's `@state/opencode-plugin` bundle subscribes to all six. Hooks are sensors + enforcers — they READ harness state from the daemon and BLOCK writes via the `tool.execute.before` return value. Hooks themselves contain NO decision logic; they are thin reporters posting hook events to the daemon over HTTP+SSE. The `state.build.harness` package owns the daemon-side decision logic.
    - **state-build MCP server.** A separate process (registered with opencode as an MCP server) exposing 14 agent-callable tools. MCP tools are agent-driven actions — the agent CALLS them to signal intent (`log_deviation`, `dispatch_subagent`, `check_proof_gate`, etc.). The MCP server's tool handlers communicate with the daemon to record events and consult policy state. Mirrors 405's "typed-spawn only via MCP tool" discipline extended to the full harness surface.
    - **state-daemon.** A long-lived user-service process owning the canonical state. Five subsystems: (1) **event store** — append-only SQLite `events.sqlite` with single-writer facade (gsd-2 `single-writer-sqlite-facade.md` pattern); (2) **projector** — CQRS handler chain that builds derived state (paralysis counter, gate strike counter, deviation counter, restart counter, intervention chain) from the event stream; (3) **scheduler** — dispatch queue with parallel-cap accounting (SUB-04); (4) **SSE bus** — distributes events to plugin hooks, MCP tool handlers, TUI subscribers; (5) **crash recovery / orphan reconciliation** — daemon-restart-safe state rehydration from the latest CompactionSnapshot row + event replay forward.

    Sub-section `### Cross-layer communication channels`:

    Render verbatim a 3-row table:

    ```
    | Direction              | Channel               | Payload                                              |
    |---|---|---|
    | plugin hook → daemon   | HTTP POST + SSE       | hook events (tool.execute.before context, chat.params runtime augmentation request, etc.) |
    | agent → MCP server     | MCP stdio (per opencode plugin protocol) | typed tool calls (log_deviation, dispatch_subagent, check_proof_gate, ...) |
    | daemon → all consumers | SSE bus               | event-store rows (state.*.* events) for TUI + plugin re-injection + MCP handler advisories |
    ```

    Sub-section `### Mode-isolation note`:

    Render verbatim: "All harness modules live under `src/state_build/harness/` and MUST NOT import from `src/state_teach/`. Build-mode discipline is physical, not policy — CI import-graph lint (PROJECT.md cardinal rule) enforces. Events live in `BUILD_ONLY_EVENT_PREFIXES = frozenset({'state.slice.', 'state.step.', 'state.harness.'})`. Carry-forward from Phase 405."

    Sub-section `### Carry-forward disciplines`:

    Render verbatim a 6-bullet list (from 406-CONTEXT.md `<code_context>` "Established patterns"):
    - **Pure-machine everywhere** (PRF-04 spirit). No LLM-as-judge in the umbrella event, the intervention ladder, or the replay proof.
    - **Plugin-as-thin-reporter, daemon-decides** (402 carry-forward). Hooks emit/block; daemon middleware owns decision dispatch.
    - **`extra="forbid"` on every Pydantic class.** Unknown field at parse time = `ValidationError`.
    - **Single-source-of-truth modules.** Every registry, regex corpus, and pattern table lives in exactly one Python file imported by every consumer.
    - **Server-side recomputation of aggregates** (gsd-2 `server-recomputation-of-llm-emitted-fields.md`; carried by 404/405). The umbrella `tier` is server-derived, never agent-emitted.
    - **4-counter independence** (PROOF-GATE.md §6 + DEVIATION-RULES.md §6 + SUBAGENT-MONITORING.md §4). APG/PRF/DEV/SUB chains never share state; `state.harness.intervention` (Plan 03 owns) is the SOLE rollup point.
    - **Append-only event store** (PROJECT.md cardinal rule). Every event is append-only; corrections are NEW events.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/406/406-CONTEXT.md` `<decisions>` "Document structure" + "Diagram form & fidelity" + "MCP tool catalog" subsections — verbatim source for §0 preamble + §1 Mermaid + 14-tool roster names. Do NOT re-derive.
        - Known: `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md` lines 1-50 — file-header markdown convention (used as Section 1 of Phase 405 plan-02).
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` — Mermaid sequenceDiagram precedent for tool.execute.before stack rendering.
        - Known: `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` — Mermaid stage diagram precedent.
        - Grep pattern: `grep -nE "^# |^## |^### " /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md | head -30` — heading hierarchy convention from sibling spec.
        - Grep pattern: `grep -nE "mermaid|flowchart|graph TB|sequenceDiagram" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md | head -10` — Mermaid block syntax precedent.
        - Grep pattern: `grep -n "BUILD_ONLY_EVENT_PREFIXES" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/*.md | head -5` — mode-isolation note precedent.
      </code_to_reuse>
      <docs_to_consult>
        - 406-CONTEXT.md `<decisions>` "Document structure (Area 1)" — verbatim source for section ordering preview.
        - 406-CONTEXT.md `<decisions>` "Diagram form & fidelity (Area 2)" — HRN-01 box-per-component + named-arrow rules verbatim.
        - 406-CONTEXT.md `<code_context>` "Established patterns (carry-forward)" — 6-bullet pattern carry-forward block verbatim.
        - 406-CONTEXT.md `<specifics>` first bullet ("The rollup is the index") — §0 overview paragraph verbatim.
        - gsd-2 `kb/cross-layer-communication-map.md` §1 — layered Mermaid topology pattern source.
        - gsd-2 `kb/core/communication-map.md` (M1 hub-and-spoke around AgentSession) — per-layer hub template.
        - gsd-2 `kb/extensions/plugin-system.md` — hook surface signature source.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's harness implementation unit tests will assert against the Pydantic class definitions in 402–405 specs (this rollup does not duplicate them); v14 also runs a Mermaid lint to confirm §1 + §6 diagrams parse.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 130)}' \
        && grep -qE "^# Harness Architecture \(Canonical, v41 Rollup\)" "$F" \
        && grep -qE "Requirements covered:.*HRN-01.*HRN-02.*HRN-03.*HRN-04.*HRN-05.*HRN-06.*HRN-07.*HRN-08" "$F" \
        && grep -qE "^## §1 Layered Diagram \(HRN-01\)" "$F" \
        && grep -qE '^```mermaid' "$F" \
        && grep -q "flowchart TB\|graph TB" "$F" \
        && grep -q "Plugin hooks (control surface)" "$F" \
        && grep -q "state-build MCP server" "$F" \
        && grep -q "state-daemon" "$F" \
        && grep -q "chat.params" "$F" \
        && grep -q "tool.execute.before" "$F" \
        && grep -q "session.compacting" "$F" \
        && grep -q "log_deviation" "$F" \
        && grep -q "dispatch_subagent" "$F" \
        && grep -q "check_proof_gate" "$F" \
        && grep -q "emit_advisory" "$F" \
        && grep -q "force_clear_and_reinject" "$F" \
        && grep -q "surface_human_gate" "$F" \
        && grep -q "query_event_store" "$F" \
        && grep -q "event store" "$F" \
        && grep -q "projector" "$F" \
        && grep -q "scheduler" "$F" \
        && grep -q "SSE bus" "$F" \
        && grep -q "crash recovery" "$F" \
        && grep -q "Mode-isolation" "$F" \
        && grep -q "BUILD_ONLY_EVENT_PREFIXES" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] File created at the spec'd path; this plan is the file's first author.
    - [check: must_haves.truths[1]] §0 preamble rendered with title heading, Phase: 406, Status: Canonical (v41), Requirements covered: HRN-01..HRN-08, Build-mode only header, section ordering preview, rollup-is-the-index note.
    - [check: must_haves.truths[2]] §1 Mermaid block contains 3 labelled subgraphs with all required node boxes (6 hooks, ≥12 MCP tools, 5 daemon services).
    - [check: must_haves.truths[3]] §1 Mermaid has ≥8 labelled edges (operation labels, not bare arrows).
    - [check: must_haves.truths[4]] §1 prose paragraph documents plugin-hooks-as-sensors-and-enforcers + MCP-tools-as-agent-driven-actions + daemon-owns-decision-logic.
    - [check: must_haves.truths[5]] §1 Mode-isolation subsection asserts state_build MUST NOT import state_teach + BUILD_ONLY_EVENT_PREFIXES.
    - [check: must_haves.truths[13]] No `GSD-` literal in the file.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md exists at the spec'd path; §0 preamble + §1 layered Mermaid diagram + prose subsections complete; file ≥130 lines (Task 2 brings to ≥350); verify-block bash passes; no `GSD-` literal.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append §2 Plugin Hook Inventory (HRN-02) — six hook subsections + hooks-vs-MCP partition summary</name>
  <files>
    .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md (Task 1's output — append §2 below)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" — verbatim hooks-vs-MCP partition note
    - .planning/milestones/v41/REQUIREMENTS.md lines 124-126 (HRN-02 verbatim)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "chat.params|session.compacting|tool.execute.after" — CTX hook usage)
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (search "chat.params|tool.execute.before" — PAP-01/02/05 hook usage)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md Section 5 (search "tool.execute.before" — 4-layer write-block stack precedent; this spec extends to 7 layers)
    - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md (search "tool.execute.after|chat.message" — APG counter wiring)
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (search "tool.execute.before" — SRP-02 + SRP-04 layer hooks)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (search "tool.execute.before|opencode question" — DEV-04 question-tool surface)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md Section 5 — full 7-layer write-block stack rendering
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md (search "tool.execute.after|chat.message" — SUB-05 SSE event correlation)
  </read_first>

  <action>
    Append §2 to `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md`. **Concrete content from upstream specs verbatim — do NOT re-derive.**

    ### Section 2 — Plugin Hook Inventory (HRN-02)

    Heading: `## §2 Plugin Hook Inventory (HRN-02)`.

    1-paragraph intro: HRN-02 specifies each plugin hook's role: signature, when it fires, what it injects/blocks/records, and which v41 requirement it implements. State's `@state/opencode-plugin` bundle subscribes to all six hooks. The hooks live inside opencode's plugin runtime; they communicate with the daemon over HTTP+SSE; they own NO decision logic (plugin-as-thin-reporter discipline, 402 carry-forward).

    Sub-section `### Hooks-vs-MCP-tools partition`:

    Render verbatim from 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" subsection:

    "**Plugin hooks are sensors + enforcers; MCP tools are agent-driven actions.** Hooks (`chat.params`/`message`, `tool.execute.before`/`after`, `session.compacting`, `shell.env`) READ harness state and BLOCK writes; MCP tools (`log_deviation`, `dispatch_subagent`, etc.) are what the agent CALLS to signal intent. Preserves 402's 'plugin is thin reporter, daemon decides' and 405's 'typed-spawn only via MCP tool' disciplines."

    For each of the six hooks, render a subsection following this template (each subsection ~30-50 lines):

    ---

    ### `chat.params`

    **Signature** (from `@opencode-ai/plugin`):
    ```typescript
    type ChatParamsHook = (ctx: ChatParamsContext) => ChatParams | Promise<ChatParams>;
    // ctx provides: sessionId, sliceId, stepId, taskId, lastVerifyResult, providesBlocks, worktreePath
    ```

    **Firing trigger:** Invoked by opencode immediately before each agent turn (LLM call). Fires at session bootstrap (the first turn after `chat.message` from user) AND on every subsequent turn.

    **Role (inject + record):**
    - **Inject (CTX-06 reinject payload):** PLAN content (active `stepNN-PLAN.md`), current task pointer, last verify result, all upstream Step `SUMMARY.md` `provides:` blocks for resolved deps, current worktree path. Performed via the daemon-driven `record_plan_edit` audit-logged source-of-truth load.
    - **Inject (PAP-01 + PAP-02):** verbatim `stepNN-PLAN.md` injection at execute-slice start; resolves all `@.planning/...` and `@-` references at injection time so the executor sees inlined content, not literal `@` syntax.
    - **Inject (PAP-06 content stripping):** harness removes upstream-only sections (e.g., plan-slice reasoning meta) at injection time to save tokens, preserving the audit-logged original on disk.
    - **Record (CTX-08 context-meter read):** harness reads opencode's context meter via this hook on each tool-execute event (mirror to SSE for TUI).
    - **Record:** emit `state.session.chat_params_invoked` event to event store.

    **Records / does NOT block.** chat.params injects; it cannot abort the turn. Blocking writes happen in `tool.execute.before`.

    **v41 REQ cross-reference:** CTX-02 (Slice-boundary spawn), CTX-06 (reinject payload), CTX-08 (context-meter read), PAP-01 (verbatim PLAN injection), PAP-02 (@-reference resolution), PAP-06 (content stripping).

    **Source spec:** CONTEXT-PROTOCOL.md §"Reinject payload" + PLAN-AS-PROMPT.md §"Injection flow".

    ---

    ### `chat.message`

    **Signature:**
    ```typescript
    type ChatMessageHook = (ctx: ChatMessageContext) => void | Promise<void>;
    // ctx provides: sessionId, role ("user" | "assistant"), content, turnIndex
    ```

    **Firing trigger:** Invoked by opencode on each user/assistant message added to the session conversation.

    **Role (record only):**
    - **Record:** mirror the message turn to the daemon event store as `state.session.message_turn` for replay, TUI rendering, and SSE distribution.
    - **Record (SUB-05 monitoring):** harness uses chat.message to mirror subagent assistant turns up to the parent task via parent_task_id correlation. The harness does NOT inspect message content for decision making — thin-reporter discipline.

    **v41 REQ cross-reference:** SUB-05 (subagent session SSE mirror by parent task_id).

    **Source spec:** SUBAGENT-MONITORING.md §"SSE event family".

    ---

    ### `tool.execute.before`

    **Signature:**
    ```typescript
    type ToolExecuteBeforeHook = (ctx: ToolExecuteBeforeContext) => ToolBlockResult | Promise<ToolBlockResult>;
    // ctx provides: sessionId, sliceId, stepId, taskId, toolName, toolArgs
    // ToolBlockResult: { allow: boolean, blockReason?: string, blockEventType?: string }
    ```

    **Firing trigger:** Invoked by opencode before any tool call. Harness applies a 7-layer pure-machine write-block stack and returns the verdict.

    **Role (block):** the 7-layer write-block stack (rendered verbatim from Phase 405 SUBAGENT-MANAGEMENT.md §5):

    1. **PAP-05 immutability check.** Reject edits targeting `must_haves.*` or any `<verify>` block. Emit `state.step.plan_edit_blocked`.
    2. **SRP-04 `files_modified` allowlist.** Reject Write/Edit to files outside the active Step's allowlist unless a `scope_deviation_request` is open. Emit `state.step.scope_check`.
    3. **SRP-02 prohibited-language scan.** Reject content containing `v1`, `simplified`, `placeholder`, `TODO`, `FIXME`, `future` unless paired with a tracking-issue reference (SRP-03). Emit `state.step.scope_check`.
    4. **SRP-04 ancillary — `<discovered_threats>` append-only carve-out.** Allow append-only edits to `<discovered_threats>` blocks inside `<threat_model>`; block all other in-place edits to the same XML scope.
    5. **DEV `log_deviation` routing + 5-step cross-validation.** When the agent invokes `log_deviation`, the daemon middleware runs issue_signature recomputation, Rule-4 alternatives check, Rule-4 auto-promotion against `ARCH_PATTERN_ALLOWLIST`, scope_deviation_request correlation, cap check. Mismatches emit `state.step.deviation_classification_rejected` or `state.step.deviation_cap_exceeded`.
    6. **SUB `dispatch_subagent` routing + whitelist enforcement + parallel-cap accounting.** Verify subagent_type ∈ `STAGE_ROSTER[current_stage]` ∩ `effective_whitelist`; verify in-flight count < `MAX_PARALLEL_CAP_DEFAULT` (20); reject + emit `state.step.subagent_whitelist_violation` or queue FIFO.
    7. **DEV arch-pattern allowlist match.** Pre-check Write targets against `ARCH_PATTERN_ALLOWLIST`; force `rule_id=4` auto-promotion on match.

    **Plus PRF-07 next-task block:** when the active Step's `must_haves.*` evaluator returns failure, this hook ALSO rejects writes to files belonging to the next Step (gate-failing advancement block).

    **Record:** every block emits a typed event (`plan_edit_blocked`, `scope_check`, `deviation_classification_rejected`, `subagent_whitelist_violation`, etc.) to the event store.

    **v41 REQ cross-reference:** PAP-05, PRF-07, SRP-02, SRP-04, DEV-04 (architectural classification), SUB-03 (whitelist), SUB-04 (parallel cap).

    **Source spec:** PROOF-GATE.md §5 (layers 1-4 baseline) + DEVIATION-RULES.md §4–5 (layer 5 + 7) + SUBAGENT-MANAGEMENT.md §5 (layer 6).

    ---

    ### `tool.execute.after`

    **Signature:**
    ```typescript
    type ToolExecuteAfterHook = (ctx: ToolExecuteAfterContext) => void | Promise<void>;
    // ctx provides: sessionId, taskId, toolName, toolResult, durationMs
    ```

    **Firing trigger:** Invoked by opencode after a tool call resolves (success or error).

    **Role (record + counter tick):**
    - **APG-01 counter tick.** Classify the tool call as read-only or write/mutating using `bash_classifier.py` (READ_ONLY_PATTERNS / WRITE_SYSCALL_PATTERNS / COMPOUND_SEP). Increment per-task consecutive read-only count; reset on write/mutating call.
    - **APG-02 threshold check.** If consecutive read-only count crosses 5 (execute-slice) or 15 (research-heavy stages), invoke `emit_advisory` MCP tool with the canonical advisory message. Emit `state.step.paralysis_event`.
    - **CTX-08 context-meter mirror.** Read opencode's context meter from the tool result; emit `state.session.context_meter` to SSE bus.
    - **SUB-05 subagent SSE correlation.** When the tool call is `task` (opencode subagent spawn), correlate the child session_id to parent task_id and emit `state.step.subagent_started`.

    **Records / does NOT block.** All blocking happens in `tool.execute.before`.

    **v41 REQ cross-reference:** APG-01 (read-only counter), APG-02 (threshold), CTX-08 (context-meter mirror), SUB-05 (subagent SSE).

    **Source spec:** ANALYSIS-PARALYSIS-GUARD.md §"Counter mechanism" + CONTEXT-PROTOCOL.md §CTX-08 + SUBAGENT-MONITORING.md §"SSE event family".

    ---

    ### `session.compacting`

    **Signature:**
    ```typescript
    type SessionCompactingHook = (ctx: SessionCompactingContext) => CompactionResult | Promise<CompactionResult>;
    // ctx provides: sessionId, sliceId, currentTaskPointer, lastVerifyResult, providesBlocks, worktreePath
    // CompactionResult: { reinjectPayload: bytes /* orjson-serialized CompactionSnapshot */ }
    ```

    **Firing trigger:** Invoked by opencode when intra-session compaction is triggered (either opencode-initiated on context-window pressure OR daemon-initiated via `request_compaction_snapshot` MCP tool for force clear+reinject — HRN-04 tier 3).

    **Role (record + inject):**
    - **CTX-03 intra-Slice compaction.** Same session_id continues. Distinguishes from CTX-02 (Slice-boundary fresh-session spawn).
    - **CTX-05 structured snapshot.** Harness builds the `CompactionSnapshot` Pydantic model from current task state and serializes via orjson. Stored as an event-store row (NOT a markdown file).
    - **CTX-06 reinject payload.** Returns the rehydrate payload to opencode: active PLAN, current task pointer, last verify result, upstream provides blocks, worktree path, subagent_restart_counters, in_flight_subagents.
    - **CTX-09 reactive overflow recovery (one-shot).** When invoked via `force_clear_and_reinject` MCP tool with overflow_recovery=True flag, sets `_overflow_recovery_attempted` session flag; flag resets on next user/agent message OR successful turn.
    - **Record:** emit `state.session.compaction_snapshot_taken` + `state.session.compaction_reinject_completed`.

    **v41 REQ cross-reference:** CTX-03 (intra-Slice compaction), CTX-05 (structured snapshot), CTX-06 (reinject payload), CTX-09 (reactive overflow recovery).

    **Source spec:** CONTEXT-PROTOCOL.md §"Compaction snapshot" + §"Reinject payload" + §"Reactive overflow recovery".

    ---

    ### `shell.env`

    **Signature:**
    ```typescript
    type ShellEnvHook = (ctx: ShellEnvContext) => Env | Promise<Env>;
    // ctx provides: sessionId, taskId, command, baseEnv
    ```

    **Firing trigger:** Invoked by opencode before shell commands (Bash tool calls).

    **Role (inject):**
    - **STATE-* trailer env injection.** Inject the four trailers as environment variables so `git commit` invocations inside subagent sessions carry the canonical trailers automatically:
      - `STATE_TASK={task_id}`
      - `STATE_DEVIATION_RULE={rule_id_if_active}` (omitted when no active deviation chain)
      - `STATE_DEVIATION_ATTEMPT={attempt_number_if_active}` (omitted when no active deviation chain)
      - `STATE_SUBAGENT_INVOCATION={invocation_id_if_subagent_session}` (set only inside subagent sessions)
    - The trailer constants come from `state_build/commit/trailers.py` (single-source-of-truth module per DEVIATION-RULES.md Section 5).

    **v41 REQ cross-reference:** DEVIATION-RULES.md commit-trailer convention (cross-references DEV-07).

    **Source spec:** DEVIATION-RULES.md §"Naming Discipline" + §"Commit Trailer Convention".

    ---

    Sub-section `### Hook surface summary`:

    Render verbatim: "The six hooks collectively form the harness's **control surface** inside opencode. They are pure sensors + enforcers: chat.params injects context, tool.execute.before applies the 7-layer write-block stack, tool.execute.after ticks counters + mirrors context-meter, session.compacting performs structured snapshot + reinject, shell.env injects STATE-* trailer env vars, chat.message mirrors message turns. None of them contain decision logic — every decision (Rule 4 always-stop, advisory escalation, gate strike chain, intervention tier dispatch) lives in the daemon. The agent-callable decision surface lives in §3 (MCP tool catalog, Plan 02). The 4-tier intervention ladder that consumes these hooks (advisory inject ↔ chat.params; tool-block ↔ tool.execute.before; force clear+reinject ↔ session.compacting; force-stop + human gate ↔ opencode `question` tool surfaced via daemon-coordinated hand-off) is documented in §4 (Plan 03)."

    <quality_scan>
      <code_to_reuse>
        - Known: 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" — hooks-vs-MCP partition note rendered verbatim.
        - Known: Phase 405 SUBAGENT-MANAGEMENT.md §5 — 7-layer tool.execute.before write-block stack rendered verbatim.
        - Known: Phase 402 CONTEXT-PROTOCOL.md — chat.params + session.compacting hook usage verbatim.
        - Known: Phase 404 ANALYSIS-PARALYSIS-GUARD.md — tool.execute.after counter classification logic.
        - Known: Phase 405 DEVIATION-RULES.md — shell.env trailer env injection convention.
        - Grep pattern: `grep -nE "tool\\.execute\\.(before|after)|chat\\.(params|message)|session\\.compacting|shell\\.env" /Users/tmac/Projects/state/.planning/milestones/v41/phases/40[2-5]/specs/*.md | head -30` — surveys every hook usage cite in upstream specs.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` — confirms §1 ↔ §2 heading hierarchy consistency.
      </code_to_reuse>
      <docs_to_consult>
        - 406-CONTEXT.md `<decisions>` "MCP tool catalog (Area 3)" — hooks-vs-MCP partition source.
        - Phase 405 SUBAGENT-MANAGEMENT.md §5 — verbatim source for tool.execute.before 7-layer stack.
        - Phase 404 PROOF-GATE.md §5 — baseline 4-layer stack precedent (layers 1-4).
        - Phase 403 PLAN-AS-PROMPT.md — PAP-01 / PAP-02 / PAP-05 hook usage source.
        - Phase 402 CONTEXT-PROTOCOL.md — CTX-02 / CTX-03 / CTX-05 / CTX-06 / CTX-08 / CTX-09 hook usage source.
        - Phase 405 SUBAGENT-MONITORING.md — SUB-05 SSE event family.
        - gsd-2 `kb/extensions/plugin-system.md` — TS hook signature shapes.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 350)}' \
        && grep -qE "^## §2 Plugin Hook Inventory \(HRN-02\)" "$F" \
        && grep -qE "^### \`chat\\.params\`" "$F" \
        && grep -qE "^### \`chat\\.message\`" "$F" \
        && grep -qE "^### \`tool\\.execute\\.before\`" "$F" \
        && grep -qE "^### \`tool\\.execute\\.after\`" "$F" \
        && grep -qE "^### \`session\\.compacting\`" "$F" \
        && grep -qE "^### \`shell\\.env\`" "$F" \
        && grep -q "ChatParamsHook" "$F" \
        && grep -q "ToolExecuteBeforeHook" "$F" \
        && grep -q "SessionCompactingHook" "$F" \
        && grep -q "Hooks-vs-MCP-tools partition" "$F" \
        && grep -q "plugin-as-thin-reporter\|thin reporter\|thin-reporter" "$F" \
        && grep -q "CTX-02" "$F" \
        && grep -q "CTX-06" "$F" \
        && grep -q "CTX-08" "$F" \
        && grep -q "PAP-01" "$F" \
        && grep -q "PAP-05" "$F" \
        && grep -q "PRF-07" "$F" \
        && grep -q "APG-01" "$F" \
        && grep -q "APG-02" "$F" \
        && grep -q "SRP-02" "$F" \
        && grep -q "SRP-04" "$F" \
        && grep -q "SUB-03" "$F" \
        && grep -q "SUB-04" "$F" \
        && grep -q "SUB-05" "$F" \
        && grep -q "STATE_TASK" "$F" \
        && grep -q "STATE_DEVIATION_RULE" "$F" \
        && grep -q "STATE_SUBAGENT_INVOCATION" "$F" \
        && grep -qE "1\\. .*PAP-05" "$F" \
        && grep -qE "7\\. .*arch-pattern allowlist" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[6]] §2 renders six hook subsections in order: chat.params, chat.message, tool.execute.before, tool.execute.after, session.compacting, shell.env.
    - [check: must_haves.truths[7]] Each hook subsection covers Signature (TS code-fence), Firing trigger, Role (inject/block/record), v41 REQ cross-reference.
    - [check: must_haves.truths[8]] chat.params cross-references CTX-02, PAP-01, PAP-02, CTX-06 at minimum.
    - [check: must_haves.truths[9]] tool.execute.before renders the 7-layer write-block stack with all layers numbered 1-7 verbatim from Phase 405 SUBAGENT-MANAGEMENT.md §5.
    - [check: must_haves.truths[10]] session.compacting cross-references CTX-03, CTX-05, CTX-06 + distinguishes from CTX-02 fresh-session spawn.
    - [check: must_haves.truths[11]] tool.execute.after cross-references APG-01, SUB-05, CTX-08.
    - [check: must_haves.truths[12]] shell.env cross-references STATE-Task/STATE-DeviationRule/STATE-Subagent-Invocation trailer env injection.
    - [check: must_haves.truths[14]] Closing "Hook surface = sensors + enforcers" summary paragraph rendered.
    - [check: must_haves.truths[13]] No `GSD-` literal in the file.
    - [check: must_haves.artifacts[0]] File at the spec'd path with min_lines: 350.
  </acceptance_criteria>

  <done>
    HARNESS-ARCHITECTURE.md complete with §0 + §1 + §2 at ≥350 lines; all 6 hook subsections render with TS signatures + role bullets + v41 REQ cross-references; tool.execute.before 7-layer stack rendered verbatim; verify-block bash passes; no `GSD-` literal.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

```bash
F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md

# Sections present
for section in \
  "^# Harness Architecture \(Canonical, v41 Rollup\)" \
  "^## §1 Layered Diagram \(HRN-01\)" \
  "^## §2 Plugin Hook Inventory \(HRN-02\)" \
  "^### \`chat\\.params\`" \
  "^### \`chat\\.message\`" \
  "^### \`tool\\.execute\\.before\`" \
  "^### \`tool\\.execute\\.after\`" \
  "^### \`session\\.compacting\`" \
  "^### \`shell\\.env\`"; do
  grep -qE "$section" "$F" || { echo "MISSING: $section"; exit 1; }
done

# Line count
wc -l "$F" | awk '{ if ($1 < 350) { print "LINE_COUNT_FAIL: " $1; exit 1 } }'

# Mermaid block + 3 subgraphs
grep -qE '^```mermaid' "$F" || { echo "MISSING_MERMAID_BLOCK"; exit 1; }
grep -q "Plugin hooks (control surface)" "$F" || { echo "MISSING_HOOKS_SUBGRAPH"; exit 1; }
grep -q "state-build MCP server" "$F" || { echo "MISSING_MCP_SUBGRAPH"; exit 1; }
grep -q "state-daemon" "$F" || { echo "MISSING_DAEMON_SUBGRAPH"; exit 1; }

# All 6 hooks named
for hook in 'chat\.params' 'chat\.message' 'tool\.execute\.before' 'tool\.execute\.after' 'session\.compacting' 'shell\.env'; do
  grep -qE "$hook" "$F" || { echo "MISSING_HOOK: $hook"; exit 1; }
done

# All 14 MCP tools named in §1 diagram
for tool in complete_task complete_slice request_step_split scope_deviation_request log_deviation dispatch_subagent check_proof_gate emit_advisory force_clear_and_reinject surface_human_gate query_context_meter request_compaction_snapshot query_event_store record_plan_edit; do
  grep -q "$tool" "$F" || { echo "MISSING_TOOL: $tool"; exit 1; }
done

# v41 REQ cross-references
for req in CTX-02 CTX-06 CTX-08 PAP-01 PAP-05 PRF-07 APG-01 APG-02 SRP-02 SRP-04 SUB-03 SUB-04 SUB-05; do
  grep -q "$req" "$F" || { echo "MISSING_REQ_REF: $req"; exit 1; }
done

# Naming discipline
! grep -qE '\bGSD-' "$F" || { echo "GSD_NAMING_VIOLATION"; exit 1; }

# Mode-isolation note
grep -q "BUILD_ONLY_EVENT_PREFIXES" "$F" || { echo "MISSING_MODE_ISOLATION"; exit 1; }

echo "HARNESS-ARCHITECTURE.md §0+§1+§2 verification OK"
```
</verification>

<success_criteria>
- HARNESS-ARCHITECTURE.md exists at `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` with ≥350 lines.
- §0 preamble + §1 layered Mermaid diagram + §2 six-hook inventory render verbatim per 406-CONTEXT.md and per upstream 402–405 specs.
- HRN-01 + HRN-02 fully covered (HRN-03..HRN-08 deferred to Plans 02, 03, 04).
- No `GSD-` literal in the file (project naming discipline).
- §1 Mermaid contains 3 subgraphs (hooks, MCP server, daemon), ≥12 MCP tool boxes, ≥8 labelled-arrow edges.
- §2 covers all 6 hooks with TS signature + firing trigger + role + v41-REQ back-cross-reference.
- tool.execute.before subsection renders 7-layer write-block stack verbatim.
- Mode-isolation note rendered (BUILD_ONLY_EVENT_PREFIXES + state_build vs state_teach assertion).
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/406/01-layered-diagram-hook-inventory-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: spec-doc final line count, sections rendered (§0 + §1 + §2), HRN coverage (HRN-01 + HRN-02 addressed; HRN-03..HRN-08 forward-pointed to Plans 02–04), naming-discipline verification result (`grep '\bGSD-' = 0`), and the Mermaid block name and approximate node/edge count.
</output>
