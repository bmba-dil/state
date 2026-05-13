---
phase: 403
plan: 03
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
autonomous: false
requirements:
  - PAP-01
  - PAP-02
  - PAP-03
  - PAP-04
  - PAP-05
  - PAP-06

must_haves:
  truths:
    - "PLAN-AS-PROMPT.md exists at .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md and fully specifies the plan-as-prompt injection / mutability / audit-log architecture."
    - "Injection flow (PAP-01) is documented: at execute-slice start the harness reads on-disk stepNPLAN.md, applies content stripping (PAP-06), resolves @-references (PAP-02), and injects the result verbatim plus runtime augmentation (worktree path, prior task results, resolved upstream provides blocks) via the chat.params plugin hook."
    - "@-reference resolution rule (PAP-02) is documented: harness inlines @.planning/X.md and @-refs at injection time, ONE LEVEL only (no recursive expansion), with a per-injection token cap (pinned: 30_000 tokens for all inlined refs combined), excess content replaced with <truncated path=\"X.md\" bytes_omitted=\"N\"/> marker, cache key (snapshot_event_id, ref_path), cache lifetime = current Slice session, token-counter fallback chars/4 per CTX-08."
    - "Path-confinement rule (PAP-02 security): @-references resolve under repo root + `.planning/` subtree; absolute paths outside repo root and parent-dir traversals (`@/` or `@..`) are REJECTED; the spec stipulates realpath-based confinement with fail-closed semantics."
    - "Mutability matrix (PAP-03) lists every locked-and-mutable section explicitly: ALL frontmatter fields locked; <objective>, <success_criteria>, <interfaces>, every <verify> block, <acceptance_criteria>, <done>, <files>, <options> all locked; <action>, <read_first>, prose <context> mutable; <threat_model> hybrid — parent locked + <discovered_threats> append-only carve-out."
    - "Pydantic PlanEdit class (PAP-04) is rendered with extra='forbid' and exact field set: step_id, slice_id, diff (unified diff string), before_sha256, after_sha256, editor (Literal executor|harness|human), edited_at (datetime UTC ISO-8601), session_id, immutable_section_touched (bool)."
    - "Pydantic PlanEditBlocked class (PAP-05) is rendered with extra='forbid' and exact field set: step_id, slice_id, proposed_diff, locked_section, blocked_at, session_id, proposed_by (Literal executor|harness|human)."
    - "Diff-the-proposed-write enforcement mechanism (PAP-05) is documented: tool.execute.before hook intercepts every Write/Edit targeting */stepNPLAN.md, applies the operation in-memory, parses old + new with the StepPlan parser, compares the immutable subset against the mutability matrix, rejects on locked-section diff with PlanEditBlocked event."
    - "<discovered_threats> append-only carve-out is documented with the EXACT diff shape that counts as 'append-only': only NEW <threat>...</threat> sub-elements added at the end of <discovered_threats>; no removal, no edit of existing children. Positive + negative diff examples included."
    - "step_plan_authored event (PAP-06) is documented: full original content + SHA-256 hash committed to event store at research-slice end; replay reconstructs original by walking the diff chain from this event."
    - "Content stripping rule (PAP-06) is documented: harness strips at injection time (on-disk file unchanged); strips plan-slice reasoning meta + <interfaces> excerpts for already-completed upstream Steps (replaced with <interfaces ref=\"upstream_provides[step-N]\"/> pointer); audit-logged original preserved in event store row."
    - "All four authoring/runtime threats from <security_threat_model_gate> are documented as spec-stipulated mitigations: path-confinement, before/after sha256 verification, no-direct-write contract for stepNPLAN.md, append-only enforcement diff shape."
  artifacts:
    - path: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      provides: "Canonical plan-as-prompt injection + mutability + audit-log spec covering PAP-01..PAP-06."
      min_lines: 500
  key_links:
    - from: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      via: "Sibling-spec cross-reference (mutability matrix references format-spec sections)"
      pattern: "STEP-PLAN-FORMAT\\.md"
    - from: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      to: ".planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md"
      via: "Literal-excerpt citations from EXEMPLAR for injection demonstrations"
      pattern: "EXEMPLAR-stepNPLAN\\.md"
    - from: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "Reinject payload XML body shape (CTX-06) is the runtime-augmentation source for injection"
      pattern: "CONTEXT-PROTOCOL\\.md"
---

<objective>
Author the canonical `PLAN-AS-PROMPT.md` spec document. This file specifies the plan-as-prompt injection flow, the runtime augmentation, the @-reference resolution rule with path confinement, the mutability matrix, the diff-the-proposed-write immutability enforcer, the content-stripping rule, and the audit-log original preservation — fully covering PAP-01..PAP-06.

Purpose: PAP-01..PAP-06 fully covered. v14 Build Kernel implements the @-reference resolver, the tool.execute.before diff-the-proposed-write enforcer, and the chat.params injection trampoline from this spec. Phase 404 (Boolean Proof Gate) consumes the immutability lock for `<verify>` blocks. Phase 406 (Harness Architecture Rollup) cross-references the injection flow.
Output: One markdown spec doc at `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md`, ≥500 lines, fully populated with literal Pydantic class definitions, the mutability matrix table, and the diff-the-proposed-write enforcer pseudocode.
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
@.planning/milestones/v41/HANDOFF.md
@.planning/milestones/v41/phases/403/403-CONTEXT.md
@.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
@.planning/milestones/v41/phases/402/402-CONTEXT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
@.planning/milestones/v41/workflow-docs-from-gsd-2/file-tracking.md
@.planning/milestones/v41/workflow-docs-from-gsd-2/quality-enforcement.md
</context>

<threat_model>
Phase 403 is design-only. PLAN-AS-PROMPT.md introduces no production attack surface — but it specifies the runtime threat-mitigation contract that v14 implements. Threats considered (per `<security_threat_model_gate>`):

- **`@`-reference resolver path traversal**: PAP-02 specifies harness inlines `@.planning/X.md` content. Without confinement, an executor-edited `<context>` could insert `@/etc/passwd` or `@../../../home/user/.ssh/id_rsa` and exfiltrate via the next replay/sync. **Mitigation in spec**: this doc MUST stipulate realpath-based path confinement (resolved path stays within repo root + `.planning/` subtree), fail-closed on traversal (resolver raises + emits `state.step.plan_edit_blocked` with `locked_section="@-reference-confinement"`), and a positive + negative example (allowed: `@.planning/PROJECT.md`; rejected: `@/etc/passwd`, `@..`, `@/home/x/.bashrc`). Forward-pointer to v14 implementation.
- **`plan_edit` event injection / replay tampering**: PAP-04 carries diffs into the event store. If the diff payload is unvalidated, replaying a malicious diff could rewrite history. **Mitigation in spec**: before_sha256 + after_sha256 are verified against on-disk content at replay; mismatched hash rejects the event. The spec MUST require this with an explicit "replay verification" subsection.
- **`plan_edit_blocked` enforcement bypass**: PAP-05 relies on `tool.execute.before`. If the hook is racing with direct file writes (e.g., another tool not routed through the harness, or a subprocess shell call), the immutability guarantee leaks. **Mitigation in spec**: this doc MUST stipulate the no-direct-write contract — ALL writes to `*/stepNPLAN.md` MUST go through `tool.execute.before`. v14 enforces by routing all Write/Edit through the daemon's HTTP middleware (Phase 402 carry-forward: tool.execute.before is the canonical block hook). Subprocess shell calls that mutate stepNPLAN.md are out-of-policy and the spec must say so.
- **`step_plan_authored` original-content snapshot tampering**: Audit-log original is the authoritative copy. If the snapshot row is mutable, replay loses the original. **Mitigation in spec**: event store rows are append-only (existing convention from v40 EVENT-TAXONOMY.md); this doc MUST explicitly cite this for the new event types — "the `state.step.plan_authored` row is append-only; replay rebuilds the original from this row alone."
- **`<discovered_threats>` append-only enforcement bypass via diff masquerade**: The carve-out is principled but the spec must specify the EXACT diff shape. Without strict shape rules, a malicious executor could rewrite an existing threat under the guise of "appending" and the diff-the-proposed-write check would pass. **Mitigation in spec**: append-only diff shape — ONLY NEW `<threat>...</threat>` sub-elements added at the end; no removal, no edit of existing children. Spec MUST include a positive diff (new threat appended) and a negative diff (existing threat text changed) and call them out as accept/reject cases.
- **Mode-isolation drift**: Build-only spec. Mitigation — explicit "Build-mode only" header note; no `state.teach.*` references.

No production code lands. No secrets. No network calls. No untrusted input.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author PLAN-AS-PROMPT.md sections 1-5 (overview, injection flow, runtime augmentation, @-reference resolution, mutability matrix)</name>
  <files>
    .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/403-CONTEXT.md (full file — every locked decision, esp. <decisions> Mutability matrix + Injection-time mechanics subsections)
    - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md (full file — Plan 01 output; quoted for injection demonstrations)
    - .planning/milestones/v41/REQUIREMENTS.md lines 50-56 (PAP-01..PAP-06 verbatim)
    - .planning/milestones/v41/HANDOFF.md lines 74-116 (§3 Plan-as-Prompt Architecture)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (full file — reinject payload XML shape provides the runtime-augmentation source slots: <active_plan>, <upstream_provides>, <current_task_pointer>)
    - .planning/milestones/v41/phases/402/402-CONTEXT.md (Phase 402 carry-forward: tool.execute.before is the canonical block hook; chat.params is the injection vector; plugin-as-thin-reporter)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md lines 1-50 (existing event type conventions; new state.step.* events follow the same shape)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/file-tracking.md (search "Correction 1" — best-effort commit; informs plan_edit diff-with-hashes pattern)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md`. Sections 1–5 below; Task 2 owns sections 6–9. **Concrete content from 403-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 1 — File header

    ```
    # Plan-as-Prompt: Injection, Mutability, Audit-Log (Canonical, v41)

    > **Phase:** 403
    > **Status:** Canonical (v41)
    > **Requirements covered:** PAP-01..PAP-06
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
    > **Sibling specs:** STEP-PLAN-FORMAT.md (frontmatter + body sections); EXEMPLAR-stepNPLAN.md (canonical worked example).
    ```

    1-paragraph overview: at execute-slice start, the on-disk `stepNPLAN.md` IS the executor's primary system prompt. The harness reads it, strips upstream-only sections, resolves `@`-references to inlined content, augments with runtime state (worktree path, prior task results, resolved upstream provides blocks), and injects via the `chat.params` plugin hook. Plans are mutable with audit log; immutable sections are enforced via `tool.execute.before` diff-the-proposed-write.

    ### Section 2 — Injection Flow (PAP-01)

    Heading: `## Injection Flow (PAP-01)`.

    Render a numbered protocol (verbatim from PAP-01 + 403-CONTEXT.md `<decisions>` Injection-time mechanics):

    1. **Slice spawn** — daemon initiates fresh opencode session at Slice boundary (CTX-02). The plugin's `chat.params` hook fires.
    2. **Read on-disk plan** — harness reads the current Step's on-disk `stepNPLAN.md` from the slice's worktree.
    3. **Apply content stripping (PAP-06)** — harness strips plan-slice reasoning meta blocks + `<interfaces>` excerpts for already-completed upstream Steps (deduplicated against the reinject payload's `<upstream_provides>` slot from CTX-06). The on-disk file is unchanged. Audit-logged original preserved in the event store via the `state.step.plan_authored` row.
    4. **Resolve `@`-references (PAP-02)** — harness inlines `@.planning/X.md` content one level only, with a per-injection token cap of 30_000 tokens; excess content replaced with `<truncated path="X.md" bytes_omitted="N"/>`. Cache key `(snapshot_event_id, ref_path)`; cache lifetime = current Slice session.
    5. **Augment with runtime state** — harness appends a `<runtime_augmentation>` block carrying:
       - `<worktree_path>` — current worktree absolute path (from Phase 402 worktree service).
       - `<prior_task_results>` — recent `<verify>` results for completed sibling tasks.
       - `<upstream_provides>` — resolved upstream Step `provides:` blocks from CTX-06 reinject payload.
       - `<current_task_pointer>` — task_id of the next task to execute (CTX-06).
    6. **Inject via `chat.params` hook** — the plugin posts the assembled prompt as the system message of the new chat session. The plugin is a thin reporter (Phase 402 carry-forward); the daemon authoritatively assembles the prompt.

    Add a sub-section `### Why on-disk plan is the source of truth`:
    "The on-disk `stepNPLAN.md` is the LIVE version executors edit. The audit-logged original lives in the event store as a `state.step.plan_authored` row (see Section 8). Replay reconstructs the original from event store; live state from file. Git history of the file (commit_docs=true in v41 config) provides a secondary audit trail — useful for human review, NOT load-bearing."

    Add a sub-section `### What the executor sees`:
    "The executor sees the (potentially stripped + @-resolved + augmented) injected version during execution, NOT the on-disk file directly. To re-read the plan, the executor invokes `Read` on the on-disk path; the resulting content has NO @-resolution applied — the executor reads the same on-disk file the harness saw at injection time. (Re-injection on context overflow per CTX-09 re-runs the full injection flow.)"

    ### Section 3 — Runtime Augmentation Block

    Heading: `## Runtime Augmentation Block`.

    1-paragraph intro: the `<runtime_augmentation>` slot appended to the injected plan carries dynamic state the on-disk plan cannot express. The slot's body shape is fixed by Phase 402's CONTEXT-PROTOCOL.md reinject payload spec; this spec adds the per-Step pointers.

    Render the slot shape verbatim:

    ```xml
    <runtime_augmentation>
      <worktree_path>{absolute_path}</worktree_path>
      <prior_task_results>
        <task_result task_id="..." status="pass|fail" automated_output_excerpt="..."/>
        ...
      </prior_task_results>
      <upstream_provides>
        <provides step_id="..."><![CDATA[{markdown content of upstream SUMMARY.md provides: block}]]></provides>
        ...
      </upstream_provides>
      <current_task_pointer>{task_id}</current_task_pointer>
    </runtime_augmentation>
    ```

    Add a sub-section `### Stripping pointer for upstream <interfaces>`:
    "When an `<interfaces>` excerpt is for an upstream Step whose `provides:` block is already present in `<upstream_provides>` above, the harness REPLACES the excerpt with: `<interfaces ref=\"upstream_provides[step-N]\"/>`. The contract is still in-context (executor scans the named upstream-provides slot for the literal); no STP-07 violation. **Silent removal would force executors to discover that upstream excerpts moved** — the pointer form preserves zero-codebase-exploration."

    Forward-pointer: "Reinject payload XML body shape source: see `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §6 (reinject payload, CTX-06)."

    ### Section 4 — `@`-Reference Resolution Rule (PAP-02)

    Heading: `## @-Reference Resolution Rule (PAP-02)`.

    Sub-section `### Resolution semantics`:
    Render verbatim from 403-CONTEXT.md `<decisions>` Injection-time mechanics:
    - "Harness resolves `@.planning/X.md` and `@-` refs at injection time, **inlines verbatim file content**, **stops at one level** (no recursive @-resolution; if a referenced doc itself uses @-refs, the planner is encouraged to inline-expand them at planning time)."
    - "**Per-injection token cap: 30_000 tokens for all inlined refs combined.** Pinned in this spec; v14 may tune to 20k or 40k based on EXEMPLAR-stepNPLAN.md realistic measurements (per 403-CONTEXT.md Claude's Discretion)."
    - "Excess content replaced with `<truncated path=\"X.md\" bytes_omitted=\"N\"/>` marker."
    - "Cache key: `(snapshot_event_id, ref_path)` tuple; cache lifetime = current Slice session."
    - "Token-counter: same fallback as CTX-08 (Anthropic `usage` if present; chars/4 heuristic otherwise)."

    Sub-section `### Path confinement (security)`:
    "All `@`-references MUST resolve to paths under repo root + `.planning/` subtree OR the workspace's source tree (`src/`, `tests/`, `packages/`, root `*.md` like `CLAUDE.md` and `PROJECT.md`). The exact allow-list is computed at planning time from the milestone's repo-root manifest; v14 implements via `pathlib.Path.resolve()` + ancestor check."

    Render a positive/negative example pair as a fenced block:

    ```text
    ALLOWED:
      @.planning/PROJECT.md          → resolves under repo root + .planning/
      @CLAUDE.md                     → resolves at repo root (allow-listed)
      @src/state_core/schema.py      → resolves under src/

    REJECTED (resolver raises + emits state.step.plan_edit_blocked):
      @/etc/passwd                   → absolute path outside repo root
      @../../../home/user/.ssh/id    → parent-dir traversal escapes repo root
      @/tmp/whatever.md              → absolute path outside repo root
      @http://evil.example/x.md      → URL form not supported (only filesystem refs)
    ```

    "**Fail-closed semantics:** on rejection the resolver does NOT silently drop the reference. The whole injection is aborted; daemon emits `state.step.plan_edit_blocked` with `locked_section=\"@-reference-confinement\"` and `proposed_diff` describing the rejected ref. The Slice session is held; human gate via opencode `question` tool surfaces the violation."

    Sub-section `### Caching`:
    1 paragraph: cache scoped to current Slice session by `(snapshot_event_id, ref_path)`. Slice-boundary spawn invalidates cache (fresh session). Compaction within a Slice (CTX-03) preserves cache (same `session_id`).

    ### Section 5 — Mutability Matrix (PAP-03)

    Heading: `## Mutability Matrix (PAP-03)`.

    1-paragraph intro: this section is the authoritative roll-up of which `stepNPLAN.md` sections are mutable vs. immutable at runtime. STEP-PLAN-FORMAT.md sibling spec marks each section's mutability inline; this section is the canonical reference. The diff-the-proposed-write enforcer (Section 7) reads from this matrix.

    Render the matrix as a markdown table:

    | Section / Block | Lock state | Rationale |
    |-----------------|------------|-----------|
    | All frontmatter fields (every key in `StepFrontmatter`) | **Locked** | Step-identity fields. Changing them means it's a different Step. PAP-03 already locks `must_haves`; this matrix locks the rest. |
    | `must_haves.truths` / `.artifacts` / `.key_links` | **Locked** | PAP-03 verbatim — gate definition. |
    | `<objective>` | **Locked** | Step contract. |
    | `<execution_context>` | **Locked** | Bootstrap doc references. |
    | `<context>` (prose @-refs) | **Mutable** | Executor may add/remove @-refs as it learns. |
    | `<interfaces>` | **Locked** | STP-07 literal upstream excerpts; mutating silently desyncs from upstream artifact (re-plan required if upstream genuinely changes). |
    | `<task type="...">` | (per-sub-tag below) | |
    | `<task>` `type` attribute | **Locked** | Changing the type means it's a different task. |
    | `<task>` `tdd` attribute | **Locked** | Same as above. |
    | `<name>` | **Locked** | Used as event key + SUMMARY anchor. |
    | `<files>` | **Locked** | Task contract; allowlist. SRP-04 enforces. |
    | `<read_first>` | **Mutable** | Executor refines as it discovers what to read. |
    | `<action>` | **Mutable** | Executor refines implementation steps as it learns. |
    | `<verify>` (any nested element) | **Locked** | PAP-03 verbatim — gate per task. |
    | `<acceptance_criteria>` | **Locked** | Task contract. |
    | `<done>` | **Locked** | Task contract. |
    | `<options>` (under `<task type="checkpoint:decision">`) | **Locked** | Decision-bounded; no runtime expansion. 403-CONTEXT.md `<decisions>` Task-type behaviors. |
    | `<threat_model>` (parent block + initial `<threat>` children) | **Locked** | Design-time contract. |
    | `<threat_model>/<discovered_threats>` (carve-out) | **Append-only** | Hybrid; new `<threat>` sub-elements may be appended at runtime. See Section 7 for diff shape. |
    | `<verification>` (Slice-level pre-commit bash block) | **Locked** | Slice gate per PAP-03. |
    | `<success_criteria>` | **Locked** | Step contract. |
    | `<output>` | **Locked** | SUMMARY path; not for runtime mutation. |

    Add a sub-section `### Quick reference — what executors can edit`:
    "Mutable sections (executor edits freely): `<context>`, `<read_first>`, `<action>`, `<discovered_threats>` (append-only). Everything else is locked; attempted edits emit `state.step.plan_edit_blocked` (Section 7)."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` — quote literal `<context>` block as the example for Section 4 path-confinement (the EXEMPLAR's @-refs are all confinement-compliant by design — Plan 01 verified).
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §6 — reinject payload XML body shape; mirror its `<active_plan>`, `<upstream_provides>`, `<current_task_pointer>` slot names verbatim.
        - Known: `.planning/milestones/v41/phases/403/403-CONTEXT.md` `<decisions>` Mutability matrix + Injection-time mechanics — verbatim source for Sections 4 and 5.
        - Grep pattern: `grep -nE "^### " /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md | head -20` — confirms Phase 402 spec H3 hierarchy depth.
      </code_to_reuse>
      <docs_to_consult>
        - 403-CONTEXT.md `<decisions>` "Injection-time mechanics" — verbatim source for Sections 2 and 4.
        - 403-CONTEXT.md `<decisions>` "Mutability matrix" — verbatim source for Section 5.
        - 402-CONTEXT.md (Phase 402 carry-forward) — confirms tool.execute.before block hook canonicalization + chat.params injection vector.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown spec.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 250)}' \
        && grep -qE "^# Plan-as-Prompt" "$F" \
        && grep -qE "^## Injection Flow" "$F" \
        && grep -qE "^## Runtime Augmentation Block" "$F" \
        && grep -qE "^## @-Reference Resolution Rule" "$F" \
        && grep -qE "^## Mutability Matrix" "$F" \
        && grep -q "chat.params" "$F" \
        && grep -q "tool.execute.before" "$F" \
        && grep -q "30_000" "$F" \
        && grep -q "<truncated" "$F" \
        && grep -q "snapshot_event_id" "$F" \
        && grep -q "@/etc/passwd" "$F" \
        && grep -q "REJECTED" "$F" \
        && grep -q "ALLOWED" "$F" \
        && grep -q "fail-closed" "$F" \
        && grep -q "Mutable" "$F" \
        && grep -q "Locked" "$F" \
        && grep -q "Append-only" "$F" \
        && grep -q "discovered_threats" "$F" \
        && grep -q "must_haves" "$F" \
        && grep -q "<runtime_augmentation>" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - File exists at `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` with ≥250 lines.
    - All five section H2 headings present (Injection Flow, Runtime Augmentation Block, @-Reference Resolution Rule, Mutability Matrix — plus H1 file header).
    - Numbered protocol (1–6) for the injection flow present.
    - `<runtime_augmentation>` slot shape rendered with all four sub-slots (worktree_path, prior_task_results, upstream_provides, current_task_pointer).
    - Path confinement positive + negative example block present (ALLOWED + REJECTED labels with at least 3 examples each).
    - Token cap pinned to 30_000.
    - Mutability matrix table renders ≥15 rows with Lock state column populated for each.
    - "fail-closed" semantic stated for @-reference rejection.
    - `<discovered_threats>` carve-out cited as Append-only in matrix.
  </acceptance_criteria>

  <done>
    Sections 1–5 of PLAN-AS-PROMPT.md authored. PAP-01 (injection flow), PAP-02 (@-resolution + path confinement), PAP-03 (mutability matrix) all covered. Task 2 will add PAP-04, PAP-05, PAP-06 (event schemas, diff-the-proposed-write enforcer, content stripping + audit log).
  </done>
</task>

<task type="auto">
  <name>Task 2: Append PLAN-AS-PROMPT.md sections 6-9 (plan_edit event schema, diff-the-proposed-write enforcer, content stripping, audit-log original, cross-references)</name>
  <files>
    .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (full file — Task 1 output; this task appends to it)
    - .planning/milestones/v41/phases/403/403-CONTEXT.md lines 80-130 (Injection-time mechanics: plan_edit, plan_edit_blocked, audit-log original — verbatim source)
    - .planning/milestones/v41/REQUIREMENTS.md lines 53-56 (PAP-04, PAP-05, PAP-06 verbatim)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — event naming convention `state.{tier}.{action}` and the append-only-row guarantee)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic frontmatter convention this spec extends to events)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/file-tracking.md (search "Correction 1" — best-effort commit + diff with hashes pattern)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/quality-enforcement.md (search "§0 Correction 2" — gate verdicts pass|flag|omitted; informs <verify> immutability rationale)
  </read_first>

  <action>
    Append sections 6–9 to the existing `PLAN-AS-PROMPT.md`. Use Edit (insert at end of file). **Concrete content from 403-CONTEXT.md verbatim.**

    ### Section 6 — `plan_edit` Event Schema (PAP-04)

    Heading: `## plan_edit Event Schema (PAP-04)`.

    1-paragraph intro: every plan edit emits a `state.step.plan_edit` event carrying a unified diff + before/after content hashes. Replay reconstructs full content by walking the diff chain from the original `state.step.plan_authored` event. Compact, auditable, replay-deterministic. Aligned with `workflow-docs-from-gsd-2/file-tracking.md` Correction 1 (best-effort commit, not transactional).

    Render the Pydantic class verbatim from 403-CONTEXT.md:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict
    from typing import Literal

    class PlanEdit(BaseModel):
        model_config = ConfigDict(extra="forbid")
        step_id: str
        slice_id: str
        diff: str                                    # git-style unified diff
        before_sha256: str                           # full file before edit
        after_sha256: str                            # full file after edit
        editor: Literal["executor", "harness", "human"]
        edited_at: datetime                          # UTC, ISO-8601
        session_id: str                              # editing session
        immutable_section_touched: bool              # set by tool.execute.before; True triggers plan_edit_blocked instead
    ```

    Sub-section `### Replay verification`:
    "**Replay-time integrity check (security mitigation):** when the projector replays a `state.step.plan_edit` event, it MUST verify:"
    1. "`before_sha256` matches the SHA-256 of the on-disk content prior to applying `diff` (or, on cold replay starting from `state.step.plan_authored`, matches the original content hash)."
    2. "`after_sha256` matches the SHA-256 of the on-disk content after applying `diff`."
    3. "On hash mismatch, the projector REJECTS the event (logs error, does not advance the projection state). Mismatched-hash events surface as a daemon-startup error gating the harness from spawning new sessions until reconciled."
    "Forward-pointer: v14 Build Kernel implements the projector + replay verifier. Reference convention: `state_core.projector` (existing CQRS handler registration)."

    Sub-section `### Event store row append-only guarantee`:
    "Per v40 EVENT-TAXONOMY.md, all event rows are append-only (immutable). The `state.step.plan_edit` row inherits this guarantee — no UPDATE/DELETE on the event row; corrections are NEW events with editor-history transparency."

    ### Section 7 — `plan_edit_blocked` + Diff-the-Proposed-Write Enforcer (PAP-05)

    Heading: `## plan_edit_blocked + Diff-the-Proposed-Write Enforcer (PAP-05)`.

    Sub-section `### PlanEditBlocked Pydantic schema`:
    Render verbatim from 403-CONTEXT.md:

    ```python
    class PlanEditBlocked(BaseModel):
        model_config = ConfigDict(extra="forbid")
        step_id: str
        slice_id: str
        proposed_diff: str
        locked_section: str                          # e.g., "frontmatter.must_haves.truths" or "<acceptance_criteria>"
        blocked_at: datetime
        session_id: str
        proposed_by: Literal["executor", "harness", "human"]
    ```

    Sub-section `### Diff-the-proposed-write algorithm`:
    Render verbatim from 403-CONTEXT.md `<decisions>` "Immutable-section block mechanism":

    1. "`tool.execute.before` hook intercepts every Write/Edit targeting `*/stepNPLAN.md` files."
    2. "Computes prospective new content (apply Edit operation in-memory; for Write, the new content is the input)."
    3. "Parses both old and new with the StepPlan parser (Pydantic frontmatter + XML body) — see STEP-PLAN-FORMAT.md."
    4. "Compares the immutable subset (locked frontmatter keys + locked XML tags from the Mutability Matrix in Section 5) using a normalized AST diff."
    5. "Any change to a locked section → reject + emit `state.step.plan_edit_blocked` event."
    6. "Pure-machine check (matches PRF-04 spirit). Works for both partial Edit and full Write."
    7. "The `<discovered_threats>` append-only carve-out is a special case: writes that ONLY add nodes to `<discovered_threats>` (no other diff) pass."

    Sub-section `### <discovered_threats> append-only diff shape`:
    "**The exact diff shape that counts as 'append-only':** ONLY new `<threat>...</threat>` sub-elements added at the end of `<discovered_threats>`; no removal of existing children, no edit of existing children's text."

    Render positive + negative diff examples as fenced blocks:

    ```diff
    ACCEPTED (new threat appended at end of <discovered_threats>):
    --- before
    +++ after
     <discovered_threats>
       <threat id="T-1">existing threat text</threat>
    +  <threat id="T-2">new threat discovered at runtime</threat>
     </discovered_threats>

    REJECTED (existing threat text edited):
    --- before
    +++ after
     <discovered_threats>
    -  <threat id="T-1">existing threat text</threat>
    +  <threat id="T-1">existing threat text MODIFIED</threat>
     </discovered_threats>

    REJECTED (existing threat removed):
    --- before
    +++ after
     <discovered_threats>
    -  <threat id="T-1">existing threat text</threat>
       <threat id="T-2">other threat</threat>
     </discovered_threats>
    ```

    Sub-section `### No-direct-write contract`:
    "**ALL writes to `*/stepNPLAN.md` MUST go through `tool.execute.before`.** Other write paths (e.g., subprocess shell commands, raw filesystem writes from outside the harness-managed tool surface) are out-of-policy. v14 enforces by routing all Write/Edit through the daemon's HTTP middleware (Phase 402 carry-forward: `tool.execute.before` is the canonical block hook). Subprocess shell calls that mutate stepNPLAN.md bypass the enforcer; the spec stipulates they MUST NOT happen — v14 implementation MAY add a filesystem watcher as defense-in-depth, but the contract is the hook routing."

    Sub-section `### Advisory message text`:
    "On block, harness injects an advisory into the executor's context (system message). Recommended wording (Claude's Discretion per 403-CONTEXT.md):"
    > "Cannot edit immutable `<{locked_section}>` — re-run plan-slice if scope changed. The proposed diff was rejected by the diff-the-proposed-write enforcer (PAP-05). Run `/state-replan` to author a new Step plan, or revise your edit to touch only mutable sections."

    ### Section 8 — Content Stripping + Audit-Log Original (PAP-06)

    Heading: `## Content Stripping + Audit-Log Original (PAP-06)`.

    Sub-section `### What gets stripped at injection time`:
    Render verbatim from 403-CONTEXT.md:
    - "**plan-slice reasoning meta blocks** — research notes, pattern-mapping rationale, validation-stage commentary, alternatives-considered. Belongs in DECISIONS.md, not the executor's working prompt."
    - "**`<interfaces>` excerpts for already-completed upstream Steps** — when the upstream Step's `provides:` blocks are already inlined in `<upstream_provides>` (carried via reinject payload per CTX-06), the redundant `<interfaces>` excerpt is replaced with `<interfaces ref=\"upstream_provides[step-N]\"/>` pointer. Preserves STP-07 zero-codebase-exploration: the contract is still in-context, just deduplicated. Executor scans the named upstream-provides slot for the literal."
    - "**Stripping does NOT modify on-disk `stepNPLAN.md`.** The audit-logged original (event store row) carries the full unredacted content."

    Sub-section `### state.step.plan_authored event (audit-log original)`:
    "Render the `StepPlanAuthored` Pydantic schema as a forward-pointer to STEP-EVENTS.md (Plan 04). Brief shape:"

    ```python
    class StepPlanAuthored(BaseModel):
        model_config = ConfigDict(extra="forbid")
        step_id: str
        slice_id: str
        original_content: str                        # full file content, verbatim
        original_sha256: str                         # SHA-256 of original_content
        authored_at: datetime
        authored_by: Literal["plan-slice", "human", "harness"]
        session_id: str
    ```

    "**Authoritative audit log:** the original is committed at research-slice end (when the planner-validation stage passes). The on-disk `stepNPLAN.md` is the LIVE version; replay reconstructs original from the event store row + diff chain."

    Sub-section `### Why a single file (not stepNPLAN.original.md)`:
    "Per 403-CONTEXT.md `<deferred>`: a two-file scheme (`stepNPLAN.original.md` + `stepNPLAN.md`) is REJECTED — divergence risk + double the per-Slice file count. Single file + event-store snapshot wins."

    Sub-section `### Conditional stripping deferred`:
    "Per 403-CONTEXT.md `<deferred>`: per-section conditional stripping via plan-author-driven `inject:` frontmatter flag is DEFERRED to v14 if EXEMPLAR sizing reveals default rules are insufficient."

    ### Section 9 — Cross-references + REQUIREMENTS Survey

    Heading: `## Cross-references + REQUIREMENTS Survey`.

    Sub-section `### Sibling specs`:
    - **STEP-PLAN-FORMAT.md** — defines the format this spec injects, mutates, and audits.
    - **STEP-EVENTS.md (Plan 04)** — defines the Pydantic schemas for `state.step.plan_authored`, `state.step.plan_edit`, `state.step.plan_edit_blocked`, plus the checkpoint and replan event family.
    - **EXEMPLAR-stepNPLAN.md** — canonical worked example; v14 implementations parse this file as a fixture and mutate it through every Mutability Matrix row to test the enforcer.

    Sub-section `### Phase 402 carry-forward consumed`:
    - **`tool.execute.before` as canonical block hook** — Phase 402 confirmed; PAP-05 enforcer attaches here.
    - **`chat.params` as injection vector** — Phase 402 confirmed; PAP-01 injection flow uses it.
    - **Plugin-as-thin-reporter** — Phase 402 carry-forward; the plugin posts proposed writes to the daemon, which authoritatively decides allow/reject.
    - **Reinject payload XML body shape (CTX-06)** — Phase 402 owns the slot names (`<active_plan>`, `<upstream_provides>`, `<current_task_pointer>`); this spec adds runtime per-Step pointers.

    Sub-section `### REQUIREMENTS amendments survey`:
    "**Surveyed:** the locked decisions in 403-CONTEXT.md were checked against v1 STP-* and PAP-* requirements for any extension that would warrant a REQUIREMENTS.md amendment. Findings:"

    | Decision | Extends a v1 REQ? | Amendment needed? |
    |----------|-------------------|-------------------|
    | `<discovered_threats>` append-only carve-out | Adds a sub-tag under `<threat_model>`. STP-03 enumerates body sections (`<threat_model>`, etc.) but does NOT enumerate sub-tags. | **No** — additive; sub-tags are spec-doc-level concerns. |
    | `<options>` sub-tag for `<task type="checkpoint:decision">` | Adds a type-specific sub-tag. STP-04 enumerates COMMON `<task>` sub-tags (`<name>`, `<files>`, etc.); type-specific sub-tags are part of STP-05 task-type behavior. | **No** — STP-04 is non-exhaustive for type-specific sub-tags. |
    | Mutability matrix locks every frontmatter field (PAP-03 originally only locked `must_haves` + `<verify>`) | **Extends PAP-03 wording** — the original requirement said only `must_haves.*` and `<verify>` blocks immutable; this spec locks all frontmatter + most body sections. | **Yes — but absorbed inline.** This spec's Section 5 IS the canonical mutability matrix; PAP-03 is satisfied as long as `must_haves.*` and `<verify>` are immutable (they are). The spec's broader lock list is a STRENGTHENING of PAP-03, not a contradiction; no separate amendment plan needed. **Documented:** the strengthening is justified by the Step-identity-fields rationale (changing them means it's a different Step). |
    | Path confinement for `@`-resolution (security mitigation in PAP-02) | PAP-02 says "harness resolves all `@.planning/...` and `@-` references at injection time so the executor sees inlined content"; security stipulations are NOT in v1 REQ wording. | **No** — security mitigations supplement the requirement; not extension of the requirement's positive scope. |
    | `auto+tdd` GSD-Test-Result trailer convention | STP-05 says "auto+tdd — autonomous with TDD cycle (RED→GREEN→REFACTOR commits required)". Trailer convention is implementation detail. | **No** — the trailer is the v41 mechanism; STP-05 wording covered. |

    "**Conclusion:** No standalone REQUIREMENTS amendment plan is needed for Phase 403. All decisions either satisfy v1 REQ wording or are absorbed inline as additive specifications."

    Sub-section `### Closing`:
    1 paragraph: v14 Build Kernel implements the @-reference resolver, the diff-the-proposed-write enforcer, the chat.params injection trampoline, the runtime-augmentation slot assembly, and the projector replay-verifier. Phase 404 consumes the immutability lock for `<verify>` blocks. Phase 405 consumes the autonomy-tier behavior for `checkpoint:*` task types (cross-referenced in STEP-PLAN-FORMAT.md Section 5). Phase 406 cross-references the injection flow in the layered harness diagram.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` Section 5 (Task 1 output) — the Mutability Matrix is the lookup table referenced by Section 7's enforcer.
        - Known: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — event naming convention `state.{tier}.{action}`; new events follow `state.step.*` form.
        - Known: 403-CONTEXT.md lines 80-130 — verbatim source for Sections 6, 7, 8.
        - Grep pattern: `grep -nE "^(class|model_config)" /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md | head -30` — confirms how Phase 402 specs render Pydantic class definitions.
      </code_to_reuse>
      <docs_to_consult>
        - 403-CONTEXT.md `<decisions>` Injection-time mechanics — verbatim source.
        - file-tracking.md Correction 1 — best-effort commit; informs PlanEdit diff-with-hashes pattern.
        - quality-enforcement.md §0 Correction 2 — gate verdicts; informs <verify> immutability rationale referenced in Section 5 (already in Task 1 output).
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown spec.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 500)}' \
        && grep -qE "^## plan_edit Event Schema" "$F" \
        && grep -qE "^## plan_edit_blocked \+ Diff-the-Proposed-Write Enforcer" "$F" \
        && grep -qE "^## Content Stripping \+ Audit-Log Original" "$F" \
        && grep -qE "^## Cross-references \+ REQUIREMENTS Survey" "$F" \
        && grep -q "class PlanEdit" "$F" \
        && grep -q "class PlanEditBlocked" "$F" \
        && grep -q "class StepPlanAuthored" "$F" \
        && grep -q "before_sha256" "$F" \
        && grep -q "after_sha256" "$F" \
        && grep -q "immutable_section_touched" "$F" \
        && grep -q "locked_section" "$F" \
        && grep -q "ACCEPTED" "$F" \
        && grep -q "REJECTED" "$F" \
        && grep -q "no removal" "$F" \
        && grep -q "no edit of existing" "$F" \
        && grep -q "no-direct-write" "$F" || grep -q "No-direct-write" "$F" \
        && grep -q "REQUIREMENTS amendments survey" "$F" || grep -q "REQUIREMENTS Survey" "$F" \
        && grep -q "STEP-EVENTS.md" "$F" \
        && grep -q "STEP-PLAN-FORMAT.md" "$F" \
        && grep -q "EXEMPLAR-stepNPLAN.md" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - PLAN-AS-PROMPT.md ≥500 lines after this task.
    - All four new section H2 headings present (plan_edit Event Schema, plan_edit_blocked + Diff-the-Proposed-Write Enforcer, Content Stripping + Audit-Log Original, Cross-references + REQUIREMENTS Survey).
    - Pydantic class definitions present and non-trivial: PlanEdit, PlanEditBlocked, StepPlanAuthored — all with `extra="forbid"` and complete field sets.
    - PlanEdit class contains: step_id, slice_id, diff, before_sha256, after_sha256, editor (Literal), edited_at, session_id, immutable_section_touched.
    - PlanEditBlocked class contains: step_id, slice_id, proposed_diff, locked_section, blocked_at, session_id, proposed_by (Literal).
    - Replay verification subsection present with hash-mismatch rejection rule.
    - Diff-the-proposed-write algorithm rendered as numbered protocol (1–7 steps).
    - <discovered_threats> append-only diff examples present (≥1 ACCEPTED + ≥2 REJECTED diff blocks).
    - No-direct-write contract subsection present.
    - REQUIREMENTS amendments survey table present with ≥4 rows.
    - Forward-pointer to STEP-EVENTS.md (Plan 04) for the full event family.
  </acceptance_criteria>

  <done>
    PLAN-AS-PROMPT.md complete — all 9 sections present. PAP-01..PAP-06 fully covered with Pydantic schemas, diff-the-proposed-write enforcer, append-only carve-out diff shape, audit-log original mechanism, and the REQUIREMENTS amendments survey concluding "no standalone amendment plan needed."
  </done>
</task>

<task type="auto">
  <name>Task 3: Write 03-plan-as-prompt-spec-SUMMARY.md</name>
  <files>
    .planning/milestones/v41/phases/403/03-plan-as-prompt-spec-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (full file — Tasks 1+2 output)
    - .planning/milestones/v41/phases/402/402-02-SUMMARY.md (sibling SUMMARY shape reference)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory gate
  </read_first>

  <action>
    Author the per-plan SUMMARY.md mirroring `402-02-SUMMARY.md`:

    1. `# Plan 403-03 Summary: PLAN-AS-PROMPT.md`
    2. Status line: `**Status:** Shipped` + `**Wave:** 2` + `**Depends on:** 01 (EXEMPLAR-stepNPLAN.md)` + `**Blocks:** 04 (STEP-EVENTS.md)`.
    3. `## What Was Built` — 1 paragraph: PLAN-AS-PROMPT.md at the canonical path; covers PAP-01..PAP-06; renders three Pydantic event schemas (PlanEdit, PlanEditBlocked, StepPlanAuthored); ships the Mutability Matrix as the canonical lookup table for the diff-the-proposed-write enforcer.
    4. `## Key Decisions` — bullets:
       - "Path confinement for @-references stipulated explicitly with positive/negative example pairs (security mitigation per <security_threat_model_gate>)."
       - "Token cap pinned to 30_000 tokens for all inlined refs combined; v14 may tune to 20k or 40k after EXEMPLAR sizing measurements."
       - "Mutability matrix STRENGTHENS PAP-03's original wording (only must_haves + <verify> required immutable) by locking ALL frontmatter fields + most body sections; rationale documented as Step-identity-fields."
       - "PlanEdit replay-time integrity check (before_sha256/after_sha256 verification) makes diff-payload tampering pure-machine detectable."
       - "<discovered_threats> append-only carve-out shipped with EXACT diff shape definition + 3 worked diff examples (1 ACCEPTED, 2 REJECTED) — no diff-shape ambiguity."
       - "REQUIREMENTS amendments survey concluded: NO standalone amendment plan needed for Phase 403. All decisions either satisfy v1 REQ wording or are absorbed inline as additive specifications. Documented in Section 9."
    5. `## Files Touched` — PLAN-AS-PROMPT.md only.
    6. `## Open Items / Deferred` — bullets:
       - "Conditional stripping via per-section `inject:` frontmatter flag deferred to v14 (per 403-CONTEXT.md <deferred>)."
       - "Recursive @-reference expansion deferred — one-level only enforced now."
       - "Advisory wording on plan_edit_blocked is recommended in this spec; v14 may tune."
    7. `## Downstream Hooks` — bullets:
       - "v14 Build Kernel implements: @-reference resolver, diff-the-proposed-write enforcer, chat.params injection trampoline, runtime-augmentation slot assembly, projector replay-verifier."
       - "STEP-EVENTS.md (Plan 04 / Phase 403) defines the full Pydantic schemas for state.step.* event family (this spec embeds 3; the rest live in Plan 04)."
       - "Phase 404 (Boolean Proof Gate) consumes the immutability lock for <verify> blocks."
       - "Phase 405 (Deviation Rules & Subagent Management) consumes the autonomy-tier task-type behavior cross-referenced in STEP-PLAN-FORMAT.md."
       - "Phase 406 (Harness Architecture Rollup) cross-references the injection flow."

    Length: 80-150 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/402-02-SUMMARY.md` — sibling SUMMARY exemplar.
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md per-plan-SUMMARY-mandatory subsection.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/03-plan-as-prompt-spec-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 60)}' \
        && grep -q "Plan 403-03" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "PLAN-AS-PROMPT.md" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - SUMMARY exists with ≥60 lines.
    - References Plan 03, the PLAN-AS-PROMPT.md spec, and forward-points to Plan 04 + downstream phases.
    - All four core sections present.
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate closed for Plan 03.
  </done>
</task>

</tasks>

<verification>
- File `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` exists with ≥500 lines.
- File `.planning/milestones/v41/phases/403/03-plan-as-prompt-spec-SUMMARY.md` exists with ≥60 lines.
- All 9 H2 sections present in PLAN-AS-PROMPT.md (Injection Flow, Runtime Augmentation Block, @-Reference Resolution Rule, Mutability Matrix, plan_edit Event Schema, plan_edit_blocked + Diff-the-Proposed-Write Enforcer, Content Stripping + Audit-Log Original, Cross-references + REQUIREMENTS Survey — plus H1 file header).
- All three Pydantic event class definitions present (PlanEdit, PlanEditBlocked, StepPlanAuthored) with `extra="forbid"` and exact field sets.
- Path confinement positive/negative examples present.
- @-reference token cap pinned to 30_000.
- Diff-the-proposed-write algorithm rendered as numbered protocol.
- <discovered_threats> append-only diff shape rendered with ≥1 ACCEPTED and ≥2 REJECTED diff examples.
- No-direct-write contract stated.
- REQUIREMENTS amendments survey concludes "no standalone amendment plan needed."
- No `state.teach.` references.
</verification>

<success_criteria>
- PAP-01 (verbatim PLAN injection + runtime augmentation) covered with numbered protocol + runtime augmentation slot shape.
- PAP-02 (@-reference resolution rule) covered with one-level inline + 30k token cap + path confinement + cache key spec.
- PAP-03 (mutability matrix) covered with comprehensive table (≥15 rows) + quick reference of mutable sections.
- PAP-04 (plan_edit event schema) covered with Pydantic class + replay verification rule + append-only event store guarantee.
- PAP-05 (immutable-section block via tool.execute.before + plan_edit_blocked event) covered with PlanEditBlocked Pydantic + diff-the-proposed-write algorithm + <discovered_threats> diff-shape examples + no-direct-write contract.
- PAP-06 (content stripping + on-disk audit-logged original preserved) covered with stripping rules + StepPlanAuthored event schema + single-file rationale.
- All four security threats from <security_threat_model_gate> have stipulated mitigations in the spec.
- Per-plan SUMMARY.md gate closed.
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` (≥500 lines)
- `.planning/milestones/v41/phases/403/03-plan-as-prompt-spec-SUMMARY.md` (≥60 lines)

Plan 04 (STEP-EVENTS.md) in Wave 3 can now finalize the full event family schemas (this spec ships 3; Plan 04 ships the remaining 6).
</output>
