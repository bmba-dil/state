---
phase: 405
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
autonomous: false
requirements:
  - SUB-01
  - SUB-02
  - SUB-03
  - SUB-04

must_haves:
  truths:
    - "SUBAGENT-MANAGEMENT.md exists at .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md and fully specifies the subagent typed-spawn surface (SUB-01), static whitelist per Slice stage (SUB-02), narrowing-only frontmatter override (SUB-03), and 20-default parallel cap (SUB-04). Plan 03 covers SUB-05..SUB-09 in a sibling file or by extending this one — this plan stops at the spawn surface."
    - "The `dispatch_subagent` MCP tool is rendered as a Pydantic-typed top-level class `DispatchSubagent(BaseModel)` with mode discriminator `Literal['single','parallel','chain']` and three sub-payload classes (SingleDispatch, ParallelDispatch, ChainDispatch) with `model_config = ConfigDict(extra='forbid')`."
    - "The exactly-one-mode Pydantic root validator is documented: exactly one of `single` / `parallel` / `chain` is set; the other two are `None`. Cites gsd-2's mode resolution at `subagent/index.ts:709-720`."
    - "The `SubagentType` Literal whitelist is rendered verbatim with all 14 named types organized by stage roster (discuss-slice: researcher, code-mapper, requirements-analyzer; plan-slice: pattern-mapper, planner, plan-validator, plan-checker; execute-slice: executor, code-fixer, test-generator, security-auditor; verify-slice: verifier, integration-checker, nyquist-auditor). Plus `researcher` dual-listed in both discuss-slice and plan-slice per SUB-02 verbatim."
    - "The `STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]]` materialization is documented as the canonical whitelist lookup. Module path `state_build/subagents/types.py` is named as single-source-of-truth."
    - "Compile-time exhaustiveness via `assert_never` is documented: missing SubagentType entry in the registry fails at type-check time (mypy/pyright caught), not at runtime. Diverges from gsd-2's runtime-discovery-with-synthetic-error-fallback (`subagent/index.ts:344-358`)."
    - "Static whitelist enforcement protocol is rendered as a numbered 5-step list (resolve current Slice stage -> lookup STAGE_ROSTER -> read Slice frontmatter `allowed_subagents` -> compute effective whitelist with `frontmatter ?? STAGE_ROSTER[current_stage]` -> runtime per-entry verification against effective_whitelist) with rejection event `subagent_whitelist_violation` and event payload (expected, requested, stage)."
    - "Narrowing-only validation (SUB-03) is documented as a TWO-GATE enforcement: (1) plan-validation stage emits `state.slice.validation_failed` if `set(frontmatter) ⊄ STAGE_ROSTER[current_stage]` (expansion attempt at plan time); (2) runtime tool.execute.before re-verifies per-entry membership at dispatch time. Both gates pure-machine."
    - "Defense-in-depth contrast with gsd-2 is rendered: state validates BOTH at plan-validation AND at runtime tool.execute.before; gsd-2 validates only at runtime (`subagent/index.ts:344-358`). Cites `precedence-divergence-by-trust-model.md`."
    - "The 20-default parallel cap (SUB-04) is documented with rationale: diverges from gsd-2's MAX_PARALLEL_TASKS=8 + MAX_CONCURRENCY=4 (`subagent/index.ts:42-43`) reflecting SUB-04's 'subagents are free context, aggressive fanout encouraged' framing."
    - "In-flight counter enforcement at daemon-side dispatch handler is documented: when `dispatch_subagent(mode='parallel', parallel=[...20+ entries])` is received, the handler queues entries beyond 20 FIFO; slots free as `subagent_complete` or `subagent_crash_detected` fires. Mirrors gsd-2's `pLimit(MAX_CONCURRENCY)` semaphore shape at the daemon layer."
    - "Per-Slice parallel-cap narrowing (`subagent: {parallel_cap: int}` frontmatter field) is rendered: narrowing-only (8/4/1 OK; >20 rejected). Rejection event `subagent_cap_expansion_rejected` emitted at plan-validation stage."
    - "Child-of-child (grandchild) accounting is documented as REJECTED for v1: state accounts only for direct children of the parent Slice session. Documented risk: parallel_cap^2 = 400 worst-case process count. Deferred to post-v17."
    - "MCP tool name `dispatch_subagent` and module path `state_build/subagents/dispatch.py` are named as single-source-of-truth. The tool is registered under the `state-build` MCP server."
    - "Mode-isolation note: `state_build/subagents/` MUST NOT import from `state_teach/`; CI import-graph lint enforces. Events live in `BUILD_ONLY_EVENT_PREFIXES`."
    - "SUBAGENT-MANAGEMENT.md does NOT contain the literal string `GSD` anywhere (project naming-discipline rule — STATE-* / state-* only)."
  artifacts:
    - path: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      provides: "Canonical subagent typed-spawn + whitelist + parallel-cap spec covering SUB-01..SUB-04: dispatch_subagent MCP tool, STAGE_ROSTER, narrowing-only enforcement at plan+runtime, 20-cap with daemon semaphore. Plan 03 extends with SUB-05..SUB-09 (monitoring, spot-check, crash recovery, task_id survival, autonomy inheritance)."
      min_lines: 450
  key_links:
    - from: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      via: "Slice frontmatter gains `allowed_subagents: list[SubagentType] | None` (SUB-03) and `subagent: {parallel_cap, progress_timeout_s, remediation_hints} | None` (SUB-04 + Plan 03's SUB-07) — both extensions to Phase 403's frontmatter schema"
      pattern: "STEP-PLAN-FORMAT\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      to: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      via: "tool.execute.before layered enforcement stack — Phase 405 adds dispatch_subagent whitelist + parallel-cap layers in deterministic order alongside Phase 404's files_modified + prohibited-language scan"
      pattern: "SCOPE-PROHIBITION\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      to: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      via: "Subagent spot-check failures (Plan 03, SUB-06) and crash exhaustion (Plan 03, SUB-07) escalate to Rule 3 or Rule 4 via log_deviation; the autonomy inheritance flow (Plan 03, SUB-09) consumes DEV-05/DEV-06 mode resolution"
      pattern: "DEVIATION-RULES\\.md"
---

<objective>
Author the canonical `SUBAGENT-MANAGEMENT.md` spec document — Part 1 of 2 (Plan 03 authors Part 2). This file fully specifies: (1) the `dispatch_subagent` MCP tool wrapping opencode's `task` tool with explicit `subagent_type` (SUB-01); (2) the static whitelist per Slice stage with the 14 named subagent types organized into 4 rosters (SUB-02); (3) the narrowing-only frontmatter override `allowed_subagents` enforced at BOTH plan-validation and runtime tool.execute.before (SUB-03); (4) the 20-default parallel cap with daemon-side FIFO queuing semaphore plus per-Slice narrowing-only override (SUB-04).

Purpose: SUB-01..SUB-04 fully covered. Downstream consumers — Plan 03 (extends with SUB-05..SUB-09: SSE monitoring, structured returns, crash recovery, task_id survival, autonomy inheritance), v14 (Build Kernel: dispatch_subagent MCP handler, STAGE_ROSTER module, per-stage roster lookup, daemon semaphore), v15 (Build Core Commands: plan-validation stage narrowing-only check), Phase 406 (HRN-03 MCP tool catalog enumerates dispatch_subagent) — all read from this file.

Output: One markdown spec doc at `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md`, ≥450 lines, fully populated with: literal Pydantic class definitions for `DispatchSubagent` + `SingleDispatch`/`ParallelDispatch`/`ChainDispatch` + the `SubagentType` Literal union (14 named types) + `STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]]`; the 5-step whitelist enforcement protocol; the two-gate narrowing-only validation; the 20-cap rationale + daemon semaphore mechanism; the per-Slice narrowing override mechanism; the grandchild accounting deferral; mode-isolation note; STATE-* naming discipline.
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
@.planning/milestones/v41/phases/405/405-CONTEXT.md
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — `SliceFrontmatter` extension (this spec adds two fields; renders verbatim from 405-CONTEXT.md):
```python
class SliceFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... existing v40+Phase 403 fields ...
    autonomy: Literal["tiered","full-yolo","conservative"] | None = None  # DEV-06 (DEVIATION-RULES.md owns)
    allowed_subagents: list[SubagentType] | None = None                   # SUB-03 (THIS SPEC OWNS)
    subagent: SubagentSliceConfig | None = None                           # SUB-04 (THIS SPEC OWNS)

class SubagentSliceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parallel_cap: int | None = None                                       # SUB-04 narrowing-only override (≤20)
    progress_timeout_s: int | None = None                                 # SUB-07 (Plan 03 owns)
    remediation_hints: dict[str, str] | None = None                       # SUB-07 (Plan 03 owns)
```

Excerpt B — `SliceStage` Literal (from Phase 402 SLICE-CYCLE.md; STAGE_ROSTER keys):
```python
SliceStage = Literal["discuss-slice", "plan-slice", "execute-slice", "verify-slice"]
```

Excerpt C — gsd-2 SubagentParams reference (state's DispatchSubagent mirrors this shape; render as commented annotation):
```typescript
// Reference: ~/projects/gsd2deconstruction/kb/agents/agent-roles.md §3.2 + subagent/index.ts:618-626
// Three modes: single | parallel | chain
// state's Python analog uses Pydantic root validator for exactly-one-mode enforcement
// State diverges: 20-cap default (vs gsd-2 MAX_PARALLEL_TASKS=8 + MAX_CONCURRENCY=4)
```

Excerpt D — Phase 404 tool.execute.before layer stack (this spec extends with 2 new layers — dispatch_subagent routing + parallel-cap accounting):
```python
# Reference: .planning/milestones/v41/phases/404/specs/PROOF-GATE.md Section 5 (PRF-07)
# Current stack: (1) files_modified allowlist (2) Phase 403 immutability (3) prohibited-language (4) gate-failing next-task block
# Phase 405 adds: (5) log_deviation routing + cross-validation [DEVIATION-RULES.md] (6) dispatch_subagent routing + whitelist + cap [THIS SPEC] (7) arch-pattern allowlist match [DEVIATION-RULES.md]
# Order is significant per 405-CONTEXT.md <code_context> Reusable Assets
```
</interfaces>

<threat_model>
Phase 405 is design-only. SUBAGENT-MANAGEMENT.md introduces no production attack surface — it is a markdown specification. Threats considered (per `<security_constraint>` and ASVS L1):

- **[high] Whitelist bypass via expansion**: If the spec allowed Slice frontmatter `allowed_subagents` to expand beyond `STAGE_ROSTER[current_stage]`, a malicious or mistaken plan could spawn an unauthorized subagent type. **Mitigation in spec:** narrowing-only is documented as a TWO-GATE enforcement (plan-validation stage AND runtime tool.execute.before) — both pure-machine; both must agree before dispatch fires. The spec stipulates `set(frontmatter) ⊆ STAGE_ROSTER[current_stage]` MUST hold or plan-validation fails. Spec MUST contrast with gsd-2's single-gate runtime-only model (defense-in-depth pole).

- **[high] Parallel-cap evasion via grandchild fanout**: If a child subagent could itself dispatch 20 grandchildren, the worst-case process count is `parallel_cap^2 = 400`. **Mitigation in spec:** explicit "grandchild accounting REJECTED for v1" subsection with documented risk and post-v17 revisit. State accounts only for direct children of the parent Slice session. v14 implements the per-Slice-session counter; grandchildren are managed by opencode at their own session.

- **[med] Whitelist drift between plan-validation and runtime**: If plan-validation uses an outdated STAGE_ROSTER snapshot, runtime may reject what plan-validation approved. **Mitigation in spec:** single-source-of-truth module `state_build/subagents/types.py` exports STAGE_ROSTER as a module-level constant; both gates import the same constant. The constant is computed-derived-state (`frozenset[SubagentType]` per stage), not stored. Mirrors gsd-2 `derived-state-from-db-decision-tree.md`.

- **[med] Compile-time exhaustiveness gap**: If a future patch adds a SubagentType Literal value but forgets the STAGE_ROSTER entry, runtime will fail-open or fail-loud unpredictably. **Mitigation in spec:** `assert_never(typing_unset_subagent_type)` in both the dispatcher and the (Plan 03) SUBAGENT_RETURN_REGISTRY. mypy/pyright catch missing entries at type-check time. The spec stipulates CI runs `mypy --strict` against `state_build/subagents/types.py`.

- **[med] Exactly-one-mode validation bypass**: If the Pydantic root validator missed an edge case (e.g., `single` and `parallel` both set), the dispatcher could nondeterministically choose. **Mitigation in spec:** the validator is documented with the exact `sum(x is not None for x in [single, parallel, chain]) == 1` predicate. Cites gsd-2's mode-resolution shape at `subagent/index.ts:709-720`. v14 unit tests assert against all 8 = 2^3 combinations.

- **[high] Naming-discipline drift (STATE-* vs GSD-*)**: Subagent invocation trailer is `STATE-Subagent-Invocation:` (not `GSD-*`). **Mitigation in spec:** the trailer is named verbatim in the cross-reference to DEVIATION-RULES.md commit-trailer convention; CI grep `grep -nE '\bGSD-' .planning/milestones/v41/phases/405/` MUST return zero. Spec author verifies before commit.

- **[low] FIFO queue starvation**: If 20 slow subagents block a queue of 100 fast ones, latency-sensitive work starves. **Mitigation in spec:** FIFO is the v1 invariant (simplest, deterministic). Priority queuing deferred to post-v17. Spec acknowledges the known limitation.

- **[low] Mode-isolation drift**: Build-only spec. **Mitigation:** explicit "Build-mode only" header note; module paths under `state_build/subagents/`; events go in `BUILD_ONLY_EVENT_PREFIXES`; CI import-graph lint.

No production code lands. No secrets. No network calls. No untrusted input parsed by the spec doc itself.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author SUBAGENT-MANAGEMENT.md sections 1-4 (header, dispatch_subagent MCP tool, SubagentType whitelist + STAGE_ROSTER, compile-time exhaustiveness)</name>
  <files>
    .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Subagent typed-spawn surface (SUB-01 + SUB-02 expanded)" subsection (verbatim source for DispatchSubagent + SubagentType + STAGE_ROSTER)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Static whitelist + narrowing-only override (SUB-03 expanded)" subsection (verbatim source for Section 5 enforcement protocol — Task 2)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Parallel cap accounting (SUB-04 expanded)" subsection (verbatim source for Section 6 — Task 2)
    - .planning/milestones/v41/REQUIREMENTS.md lines 102-114 (SUB-01..SUB-04 verbatim)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — frontmatter schema; SliceFrontmatter gets two new fields)
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md (search "discuss-slice|plan-slice|execute-slice|verify-slice" — SliceStage Literal source)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md Section 5 (tool.execute.before stack; this spec extends with 2 new layers)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md lines 1-100 (naming convention; this spec adds state.step.subagent_whitelist_violation + state.slice.subagent_cap_expansion_rejected events — Plan 04 registers)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic `extra="forbid"` convention)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md`. Sections 1-4 below; Task 2 owns Sections 5-7. **Concrete content from 405-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 1 — File header

    ```
    # Subagent Management (Canonical, v41, Part 1 of 2)

    > **Phase:** 405
    > **Status:** Canonical (v41)
    > **Requirements covered (this file, Part 1):** SUB-01, SUB-02, SUB-03, SUB-04
    > **Requirements covered by Part 2 (`SUBAGENT-MONITORING.md`):** SUB-05..SUB-09 (Plan 03)
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
    > **Sibling specs:** DEVIATION-RULES.md (Plan 01 — autonomy inheritance from DEV-05/DEV-06 + escalation to Rule 3 / Rule 4 from spot-check + crash exhaustion; consumed by Part 2).
    > **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Trailer `STATE-Subagent-Invocation:` is mandatory on every commit inside a subagent session (DEVIATION-RULES.md cross-references).
    > **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
    ```

    1-paragraph overview: the harness spawns subagents via opencode's `task` tool wrapped by the `dispatch_subagent` MCP tool — typed-spawn only (no string-prompt-only invocations). Each spawn names a `subagent_type` from a static whitelist organized into 4 rosters (one per Slice stage). Slice frontmatter MAY narrow the whitelist (subset only) but never expand. Parallel fanout is near-uncapped (default 20 concurrent) with daemon-side FIFO queuing. Subagents are "free context" — aggressive fanout encouraged for research, pattern-mapping, validation. Plan 03 covers monitoring (SSE events), structured returns + spot-check, crash recovery, task_id survival, and autonomy inheritance.

    ### Section 2 — `dispatch_subagent` MCP Tool

    Heading: `## dispatch_subagent MCP Tool (SUB-01)`.

    Sub-section `### Tool registration`:
    "MCP tool name: `dispatch_subagent`. Registered under the `state-build` MCP server. Module path: `state_build/subagents/dispatch.py`. Wraps opencode's `task` tool with state-specific validation (whitelist, parallel cap, autonomy inheritance — Plan 03). The opencode `task` tool is the underlying spawn primitive; state never invokes it directly."

    Sub-section `### Top-level signature (Pydantic-typed)`:

    Render the `DispatchSubagent` + `SingleDispatch` + `ParallelDispatch` + `ChainDispatch` Pydantic classes verbatim from 405-CONTEXT.md `<decisions>` "Subagent typed-spawn surface" subsection. Use `python` code-fence. Include `model_config = ConfigDict(extra="forbid")` on every class.

    Sub-section `### Exactly-one-mode validation`:
    Render verbatim: "A Pydantic root validator enforces exactly one of `single` / `parallel` / `chain` is set; the other two MUST be `None`. The predicate is `sum(1 for x in (single, parallel, chain) if x is not None) == 1`. Violation -> Pydantic `ValidationError` at parse time. Mirrors gsd-2's mode resolution at `subagent/index.ts:709-720`."

    Sub-section `### Mode semantics`:
    - **`single`:** one subagent invocation, synchronous-from-the-harness-perspective; daemon awaits opencode's `task` tool resolution. Most common for verification-flavored spawns (e.g., `nyquist-auditor`).
    - **`parallel`:** N concurrent invocations, 1..20 entries (capped by SUB-04). All dispatched simultaneously; daemon waits for all to terminate (success or crash) before returning. Mirrors gsd-2's `pLimit(MAX_CONCURRENCY)` shape but at the daemon layer.
    - **`chain`:** sequential invocations with text-substitution between steps. The `task` field of step `i+1` may include `{previous}` literal placeholders, populated from step `i`'s structured return shape's textual fields (Plan 03 SUB-06 owns the return-shape registry). Unlimited chain length.

    Sub-section `### MCP tool name + state ownership`:
    "Single-source-of-truth: the tool name `dispatch_subagent` is owned by this spec. No other spec defines a subagent-dispatch entrypoint. Phase 406's HRN-03 MCP tool catalog forward-references this spec."

    ### Section 3 — `SubagentType` Whitelist (SUB-02)

    Heading: `## SubagentType Whitelist (SUB-02)`.

    1-paragraph intro: the 14 named subagent types are organized into 4 stage rosters (discuss-slice, plan-slice, execute-slice, verify-slice). Some types are dual-listed across rosters (e.g., `researcher`); runtime stage gates determine which roster applies for whitelist enforcement.

    Sub-section `### SubagentType Literal`:

    Render verbatim from 405-CONTEXT.md `<decisions>` "Subagent typed-spawn surface (SUB-01 + SUB-02 expanded)" subsection:

    ```python
    SubagentType = Literal[
        # discuss-slice roster
        "researcher", "code-mapper", "requirements-analyzer",
        # plan-slice roster (research-slice in v40 vocab)
        "pattern-mapper", "planner", "plan-validator", "plan-checker",
        # execute-slice roster (run-slice in v40 vocab)
        "executor", "code-fixer", "test-generator", "security-auditor",
        # verify-slice roster
        "verifier", "integration-checker", "nyquist-auditor",
    ]
    ```

    Cite source: "Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` 'Subagent typed-spawn surface (SUB-01 + SUB-02 expanded)' subsection. Mirrors SUB-02 in REQUIREMENTS.md."

    Sub-section `### STAGE_ROSTER materialization`:

    Render verbatim:

    ```python
    STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]] = {
        "discuss-slice": frozenset({"researcher", "code-mapper", "requirements-analyzer"}),
        "plan-slice":    frozenset({"researcher", "pattern-mapper", "planner", "plan-validator", "plan-checker"}),
        "execute-slice": frozenset({"executor", "code-fixer", "test-generator", "security-auditor"}),
        "verify-slice":  frozenset({"verifier", "integration-checker", "nyquist-auditor"}),
    }
    ```

    Note: `researcher` is intentionally dual-listed in both `discuss-slice` and `plan-slice` rosters per the SUB-02 specification verbatim. The runtime stage gate (Section 5) determines which roster applies based on the active Slice's current stage.

    Sub-section `### Module ownership`:
    "Single-source-of-truth module: `state_build/subagents/types.py`. Exports: `SubagentType` (Literal union), `STAGE_ROSTER` (dict[SliceStage, frozenset[SubagentType]]), `assert_subagent_type_in_stage(t: SubagentType, stage: SliceStage) -> None`. v14 implements; v15 imports for plan-validation."

    Sub-section `### Per-stage roster boundaries`:
    "When a `subagent_type` plausibly serves two stages (e.g., `researcher` in both discuss-slice and plan-slice), the type appears in BOTH stage frozensets. Runtime stage gates determine which roster applies. The planner finalizes the exact dual-listed types during v14 EXEMPLAR work; SUB-02's verbatim roster is the v1 starter (`researcher` dual-listed as documented above)."

    ### Section 4 — Compile-Time Exhaustiveness via `assert_never`

    Heading: `## Compile-Time Exhaustiveness via assert_never`.

    1-paragraph intro: state's stricter validation pole — missing `SubagentType` entry in the registry fails at type-check time (mypy/pyright caught), not at runtime. Diverges from gsd-2's runtime-discovery-with-synthetic-error-fallback pattern (`subagent/index.ts:344-358`). Mirrors gsd-2's `exhaustive-registry-with-satisfies-constraint.md` pattern with Python idioms.

    Sub-section `### Pattern`:

    Render verbatim:

    ```python
    from typing import assert_never

    def dispatch_one(entry: SingleDispatch, stage: SliceStage) -> None:
        match entry.subagent_type:
            case "researcher": ...
            case "code-mapper": ...
            case "requirements-analyzer": ...
            case "pattern-mapper": ...
            case "planner": ...
            case "plan-validator": ...
            case "plan-checker": ...
            case "executor": ...
            case "code-fixer": ...
            case "test-generator": ...
            case "security-auditor": ...
            case "verifier": ...
            case "integration-checker": ...
            case "nyquist-auditor": ...
            case _:
                assert_never(entry.subagent_type)
    ```

    Note: "A future patch adding a SubagentType Literal value but forgetting the dispatcher case raises a mypy/pyright error at type-check time. CI MUST run `mypy --strict src/state_build/subagents/` (and `pyright --warnings`). Mirrors gsd-2 `exhaustive-registry-with-satisfies-constraint.md` (TypeScript `satisfies Record<K,V>`); state's Python analog is `Literal` union + `assert_never` + Pydantic registry. The same exhaustiveness pattern guards the `SUBAGENT_RETURN_REGISTRY` (Plan 03 owns)."

    Sub-section `### gsd-2 contrast`:

    "gsd-2's `subagent/index.ts:344-358` falls back to a synthetic-error generation when an unknown agent name appears at runtime — a permissive runtime model. State's stricter pole rejects unknown types at compile time AND at runtime. The defensive-pole choice mirrors 404's PRF server-recomputation discipline."

    Sub-section `### Mode-isolation note`:
    "`state_build/subagents/types.py` MUST NOT import from `state_teach/`. CI import-graph lint enforces. The 14 named SubagentType values are Build-only; teach-mode harness owns its own roster (v47 territory)."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Subagent typed-spawn surface (SUB-01 + SUB-02 expanded)" subsection — DispatchSubagent + SingleDispatch + ParallelDispatch + ChainDispatch + SubagentType Literal + STAGE_ROSTER rendered verbatim; do NOT re-derive.
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` Section 5 — tool.execute.before stack precedent; Section 5 of THIS spec (Task 2) extends with 2 new layers.
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` — SliceFrontmatter schema; gains `allowed_subagents`, `subagent` nested fields here.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md | head -40` — heading hierarchy convention.
        - Grep pattern: `grep -nE "model_config = ConfigDict" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md | head -20` — Pydantic class rendering convention.
        - Grep pattern: `grep -n "SubagentType" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/405-CONTEXT.md` — locates verbatim source.
      </code_to_reuse>
      <docs_to_consult>
        - 405-CONTEXT.md `<decisions>` Subagent typed-spawn surface — verbatim source for Sections 2-3.
        - 405-CONTEXT.md `<specifics>` "Compile-time exhaustiveness via Python Literal + assert_never" — verbatim source for Section 4.
        - gsd-2 `subagent/index.ts.md:618-626` — SubagentParams shape; state's DispatchSubagent mirrors.
        - gsd-2 `exhaustive-registry-with-satisfies-constraint.md` — TypeScript pattern; state's Python analog.
        - gsd-2 `agent-roles.md` §3.2 — typed-spawn semantics; cite for SUB-01 framing.
        - Phase 402 SLICE-CYCLE.md — SliceStage Literal source.
        - Phase 404 PROOF-GATE.md Section 5 — tool.execute.before stack; new layers documented in Section 5 of THIS spec.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's dispatch_subagent handler unit tests will assert against the Pydantic class definitions in this spec as fixtures; this spec doc is the contract.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 180)}' \
        && grep -qE "^# Subagent Management" "$F" \
        && grep -qE "^## dispatch_subagent MCP Tool" "$F" \
        && grep -qE "^## SubagentType Whitelist" "$F" \
        && grep -qE "^## Compile-Time Exhaustiveness" "$F" \
        && grep -q "DispatchSubagent" "$F" \
        && grep -q "SingleDispatch" "$F" \
        && grep -q "ParallelDispatch" "$F" \
        && grep -q "ChainDispatch" "$F" \
        && grep -q "STAGE_ROSTER" "$F" \
        && grep -q '"researcher"' "$F" \
        && grep -q '"executor"' "$F" \
        && grep -q '"nyquist-auditor"' "$F" \
        && grep -q "assert_never" "$F" \
        && grep -q "state_build/subagents/types.py" "$F" \
        && grep -q "state_build/subagents/dispatch.py" "$F" \
        && grep -q 'model_config = ConfigDict(extra="forbid")' "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[1]] DispatchSubagent + SingleDispatch + ParallelDispatch + ChainDispatch Pydantic classes render verbatim.
    - [check: must_haves.truths[2]] Pydantic exactly-one-mode root validator is documented with the `sum(...) == 1` predicate; gsd-2 cite included.
    - [check: must_haves.truths[3]] SubagentType Literal renders verbatim with all 14 named types organized by stage roster comments; `researcher` dual-listed in discuss-slice AND plan-slice frozensets.
    - [check: must_haves.truths[4]] STAGE_ROSTER dict renders verbatim with 4 keys (discuss-slice/plan-slice/execute-slice/verify-slice) mapping to frozenset[SubagentType] values; `state_build/subagents/types.py` module path named.
    - [check: must_haves.truths[5]] `assert_never` exhaustiveness pattern renders; gsd-2 runtime-fallback contrast rendered.
    - [check: must_haves.truths[15]] No `GSD-` literal in the file.
  </acceptance_criteria>

  <done>
    SUBAGENT-MANAGEMENT.md exists with sections 1-4; file ≥180 lines (Task 2 brings to ≥450); verify-block bash passes; no `GSD-` literal.
  </done>
</task>

<task type="auto">
  <name>Task 2: Author SUBAGENT-MANAGEMENT.md sections 5-7 (static whitelist enforcement 2-gate, 20-default parallel cap + daemon semaphore, grandchild deferral)</name>
  <files>
    .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md (the file Task 1 just authored — append sections 5-7 below)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Static whitelist + narrowing-only override (SUB-03 expanded)" subsection (verbatim source for Section 5)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md `<decisions>` "Parallel cap accounting (SUB-04 expanded)" subsection (verbatim source for Section 6)
    - .planning/milestones/v41/REQUIREMENTS.md lines 108-114 (SUB-03 + SUB-04 verbatim)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md Section 5 (tool.execute.before stack precedent)
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (full file — Phase 404 enforcement layers; this spec adds 2 more)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (search "frontmatter" — narrowing-only validation lands at plan-validation stage)
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md (search "validation" — plan-validation stage precedent)
  </read_first>

  <action>
    Append sections 5-7 to `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md`. **Concrete content from 405-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 5 — Static Whitelist Enforcement + Narrowing-Only Override (SUB-03)

    Heading: `## Static Whitelist Enforcement + Narrowing-Only Override (SUB-03)`.

    1-paragraph intro: SUB-03 specifies that Slice frontmatter `allowed_subagents` MAY narrow the per-stage whitelist (subset only) but cannot expand it. Defense-in-depth: state enforces this at TWO gates (plan-validation AND runtime tool.execute.before) — both pure-machine, both required to agree before dispatch fires. Diverges from gsd-2's single-gate runtime-only model.

    Sub-section `### Slice frontmatter field`:

    Render verbatim:

    ```python
    class SliceFrontmatter(BaseModel):
        model_config = ConfigDict(extra="forbid")
        # ... existing v40+Phase 403 fields ...
        allowed_subagents: list[SubagentType] | None = None  # SUB-03
    ```

    Note: "`None` means use the per-stage default (`STAGE_ROSTER[current_stage]` verbatim). When set, the list MUST be a non-empty subset of `STAGE_ROSTER[current_stage]` for the Slice's active stage."

    Sub-section `### Enforcement protocol (5-step numbered)`:

    Render verbatim:

    1. **Resolve current Slice stage** via active task context (`(slice_id, current_stage)`). The stage comes from the Slice's FSM state (Phase 402 SLICE-CYCLE.md `state.slice.stage_entered` event).
    2. **Lookup `STAGE_ROSTER[current_stage]`** — a `frozenset[SubagentType]` of allowed types for this stage.
    3. **Read Slice frontmatter `allowed_subagents: list[SubagentType] | None`** — the per-Slice override.
    4. **Compute effective whitelist:** `effective_whitelist = frontmatter ?? STAGE_ROSTER[current_stage]`. If frontmatter is supplied, verify `set(frontmatter) ⊆ STAGE_ROSTER[current_stage]` (narrowing-only); if frontmatter expands (any value not in `STAGE_ROSTER[current_stage]`), reject the plan at plan-validation stage (NOT at runtime — narrowing-only validation happens during plan-slice's validation stage per Phase 403 pattern).
    5. **At runtime:** for each (single/parallel/chain) entry in the `dispatch_subagent` payload, verify `entry.subagent_type ∈ effective_whitelist`. Mismatch -> reject the dispatch call with `state.step.subagent_whitelist_violation` event payload `{expected: list[SubagentType], requested: SubagentType, stage: SliceStage, task_id, slice_id, triggered_at}`.

    Sub-section `### Two-gate validation (plan-time + runtime)`:

    Render verbatim:
    - **Gate 1 — Plan-validation stage (Phase 403 `N-VALIDATION.md` machinery).** The planner's research-slice validation stage runs `set(frontmatter) ⊆ STAGE_ROSTER[stage]` for each Slice's `allowed_subagents` against the Slice's active stage roster. Expansion attempts fail `N-VALIDATION.md` and force a replan iteration. Mirrors Phase 403's `depends_on` cross-check pattern.
    - **Gate 2 — Runtime `tool.execute.before` hook.** Even after plan-validation passes, the daemon's `tool.execute.before` middleware re-verifies the per-entry whitelist at dispatch time. Defense-in-depth against post-plan edits (e.g., plan-edit events that bypass plan-validation by accident).
    - **Both gates pure-machine.** No LLM-as-judge anywhere; subset checks are deterministic set operations.

    Sub-section `### tool.execute.before stack extension`:

    "The `dispatch_subagent` MCP call enters the daemon's middleware via `tool.execute.before`. The full layered stack (after Phase 405) is:"

    Render verbatim:
    1. Phase 403 immutability check (PAP-05).
    2. Phase 404 `files_modified` allowlist (SRP-04).
    3. Phase 404 prohibited-language scan (SRP-02).
    4. Phase 404 `<discovered_threats>` append-only carve-out (SRP-04 ancillary).
    5. **Phase 405 `log_deviation` routing + cross-validation** (DEVIATION-RULES.md Section 4).
    6. **Phase 405 `dispatch_subagent` routing + whitelist enforcement + parallel-cap accounting** (this spec Sections 5-6).
    7. **Phase 405 arch-pattern allowlist match** for Rule-4 auto-promotion (DEVIATION-RULES.md Section 5).

    Note: "Order is significant. Cheap (regex/glob) checks first; expensive (DB query) checks last. Layers 5-7 are Phase 405's additions. The full stack lives in the daemon's HTTP middleware; the plugin's `tool.execute.before` hook is a thin reporter that posts to the daemon and applies the daemon's verdict."

    Sub-section `### gsd-2 contrast`:

    "State diverges from gsd-2's permissive runtime model. gsd-2's `subagent/index.ts:344-358` has no narrowing-only mechanism at plan time — gsd-2 trusts the LLM to pick valid agent names at dispatch, with a synthetic-error fallback. State's stricter pole validates both at plan-validation AND at runtime tool.execute.before — both gates pure-machine. Mirrors `precedence-divergence-by-trust-model.md`: state's defense-in-depth pole."

    ### Section 6 — Parallel Cap Accounting (SUB-04)

    Heading: `## Parallel Cap Accounting (SUB-04)`.

    1-paragraph intro: SUB-04 specifies the default cap of 20 concurrent subagent invocations per parent Slice session, configurable per-Slice with narrowing-only override. Diverges from gsd-2's MAX_PARALLEL_TASKS=8 + MAX_CONCURRENCY=4 (`subagent/index.ts:42-43`) reflecting SUB-04's "subagents are free context, aggressive fanout encouraged" framing.

    Sub-section `### Default cap`:

    Render verbatim: "**20 concurrent invocations per parent Slice session.** Higher than gsd-2's 8/4 cap because (a) SUB-04 explicitly encourages aggressive fanout for research, pattern-mapping, and validation; (b) state's per-Slice subagent diversity is higher (14 named types across 4 rosters); (c) opencode's `task` tool spawns each subagent in a fresh process — system-level concurrency is bounded by OS resources, not state's framework."

    Sub-section `### Enforcement mechanism`:

    Render verbatim:
    - **In-flight counter at daemon-side dispatch handler.** When `dispatch_subagent(mode="parallel", parallel=[...20+ entries])` is received, the handler queues entries beyond 20 (FIFO); slots free as `state.step.subagent_complete` or `state.step.subagent_crash_detected` events fire (Plan 03 owns these events).
    - **Mirrors gsd-2's `pLimit(MAX_CONCURRENCY)` semaphore shape but at the daemon layer rather than per-tool-call.** State's choice reflects the daemon-as-single-decision-gate architecture (v6).
    - **`subagent_started` event carries `parent_task_id`** to record the parent linkage (SUB-08; Plan 03 owns). Daemon projector maintains `in_flight_subagents: dict[parent_task_id, int]` rebuilt from event-store on boot (mirrors v6 daemon crash-recovery pattern).

    Sub-section `### Per-Slice override (narrowing-only)`:

    Render verbatim:
    - **Slice frontmatter:** `subagent: {parallel_cap: int | None}` (nested under `SubagentSliceConfig`).
    - **Direction:** narrowing-only. May move stricter (8 / 4 / 1 OK); attempts to expand beyond 20 are rejected at plan-validation stage with `state.slice.subagent_cap_expansion_rejected` event payload `{slice_id, requested_cap: int, max_allowed: 20, triggered_at}`.
    - **Mirrors Phase 402's `compaction:` field narrowing-only pattern** — the precedent for nested-config-with-narrowing-only.

    Sub-section `### Child-of-child (grandchild) accounting`:

    Render verbatim: "**Rejected for v1.** Subagents are spawned in fresh opencode sessions; their own `task` tool invocations are managed by opencode, not state-daemon. State accounts only for direct children of the parent Slice session. If a child subagent itself dispatches more subagents (grandchildren), they count against the grandchild's session, not the parent's. **Risk:** `parallel_cap^2 = 400` worst-case process count if every child fans out 20 grandchildren. Documented as known limitation; revisit if real workloads show concurrency-storm patterns. Mirrors gsd-2's 'no explicit guard at the grandchild level' framing in `three-layer-llm-orchestration.md`."

    Sub-section `### FIFO queue semantics`:

    Render verbatim: "Excess entries queued FIFO. The daemon dispatch handler holds the request open (HTTP long-poll style or SSE-driven release); slots free as completion/crash events fire. Latency-sensitive priority queuing is **deferred to post-v17** — FIFO is the v1 invariant for simplicity and determinism. Known limitation: 20 slow subagents can starve a queue of 100 fast follow-ups; if observed, planner adds a priority field to `SingleDispatch`/`ParallelDispatch`/`ChainDispatch` in v14+."

    Sub-section `### Module ownership`:
    "Single-source-of-truth module: `state_build/subagents/parallel_cap.py`. Exports: `MAX_PARALLEL_CAP_DEFAULT: int = 20`, `resolve_effective_cap(slice_frontmatter: SliceFrontmatter) -> int`, `acquire_slot(parent_task_id: str) -> SlotHandle`, `release_slot(parent_task_id: str, handle: SlotHandle) -> None`. v14 implements; daemon middleware imports."

    ### Section 7 — Cross-Reference to Plan 03 (SUB-05..SUB-09)

    Heading: `## Cross-Reference: Monitoring + Spot-Check + Crash Recovery + task_id Survival + Autonomy Inheritance`.

    Render verbatim:

    Plan 03 of Phase 405 ships `SUBAGENT-MONITORING.md` (sibling spec doc) covering:
    - **SUB-05** — SSE event family (`state.step.subagent_started` / `subagent_progress` / `subagent_complete`) linked by parent `task_id`.
    - **SUB-06** — `SUBAGENT_RETURN_REGISTRY` (central Pydantic registry per `SubagentType`) + 4-layer spot-check protocol (process classification / Pydantic validate / artifact existence / commit existence).
    - **SUB-07** — 5-source crash taxonomy + 3-restart counter with augmented `<prior_crash>` continuation context.
    - **SUB-08** — `task_id` survival across compaction and Slice-boundary respawn (cross-references CTX-07).
    - **SUB-09** — Autonomy inheritance from parent Slice (consumes DEV-05/DEV-06 from DEVIATION-RULES.md Section 6).

    The two specs share a single mode-isolation boundary (`state_build/subagents/`) and a single STATE-* trailer convention (`STATE-Subagent-Invocation: <invocation_id>` on every commit produced inside a subagent session; the trailer constant lives in `state_build/commit/trailers.py` per DEVIATION-RULES.md Section 5).

    Sub-section `### Forward event registrations (Plan 04)`:

    "Plan 04 of Phase 405 appends a `## v41 Amendment — Phase 405 Deviation + Subagent Event Family` block to `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` registering this spec's two new events (`state.step.subagent_whitelist_violation`, `state.slice.subagent_cap_expansion_rejected`) plus DEVIATION-RULES.md's four new events plus Plan 03's eight new events. Authoritative event-payload Pydantic shapes live in the owning specs (this spec, DEVIATION-RULES.md, SUBAGENT-MONITORING.md); the taxonomy amendment is a registry index."

    Sub-section `### Authoritative-ordering note`:

    "**Pydantic class definitions in this spec are authoritative.** The runtime enforcement protocol (Section 5) and the parallel-cap mechanism (Section 6) are operational shapes for v14 to implement; v14 unit tests assert against the Pydantic definitions in this spec as fixtures."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Static whitelist + narrowing-only override (SUB-03 expanded)" subsection — 5-step protocol + two-gate validation rendered verbatim.
        - Known: `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Parallel cap accounting (SUB-04 expanded)" subsection — 20-cap default + daemon semaphore + grandchild deferral rendered verbatim.
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` Section 5 — tool.execute.before stack precedent; THIS spec Section 5 extends with 2 new layers (Phase 405 layers 5-7).
        - Known: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` §SRP-04 — files_modified allowlist as layer 2 of the tool.execute.before stack; cited in Section 5's stack listing.
        - Grep pattern: `grep -nE "tool.execute.before" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md | head -10` — locates stack ordering precedent.
        - Grep pattern: `grep -nE "MAX_PARALLEL_TASKS|MAX_CONCURRENCY" /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/405-CONTEXT.md` — confirms gsd-2 cap divergence numbers.
      </code_to_reuse>
      <docs_to_consult>
        - 405-CONTEXT.md `<decisions>` Static whitelist + narrowing-only — verbatim source for Section 5.
        - 405-CONTEXT.md `<decisions>` Parallel cap accounting — verbatim source for Section 6.
        - 405-CONTEXT.md `<specifics>` "20-parallel cap diverges from gsd-2's 8/4 for principled reasons" — rationale prose.
        - gsd-2 `precedence-divergence-by-trust-model.md` — defense-in-depth pole framing.
        - gsd-2 `three-layer-llm-orchestration.md` — grandchild accounting precedent.
        - gsd-2 `subagent/index.ts.md:42-43` — gsd-2 cap numbers.
        - Phase 402 SLICE-CYCLE.md — plan-validation stage (Gate 1) machinery.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec).
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 450)}' \
        && grep -qE "^## Static Whitelist Enforcement" "$F" \
        && grep -qE "^## Parallel Cap Accounting" "$F" \
        && grep -qE "^## Cross-Reference" "$F" \
        && grep -q "allowed_subagents" "$F" \
        && grep -q "subagent_whitelist_violation" "$F" \
        && grep -q "subagent_cap_expansion_rejected" "$F" \
        && grep -q "MAX_PARALLEL_CAP_DEFAULT" "$F" \
        && grep -q "state_build/subagents/parallel_cap.py" "$F" \
        && grep -q "Two-gate validation\|two-gate\|TWO-GATE" "$F" \
        && grep -q "plan-validation" "$F" \
        && grep -q "tool.execute.before" "$F" \
        && grep -q "FIFO" "$F" \
        && grep -q "20" "$F" \
        && grep -q "grandchild" "$F" \
        && grep -qE "log_deviation routing|log_deviation \(DEVIATION-RULES" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[6]] Section 5 renders the 5-step enforcement protocol with all five literal steps verbatim and the `subagent_whitelist_violation` event payload.
    - [check: must_haves.truths[7]] Two-gate validation (plan-validation Gate 1 + runtime Gate 2) is documented; defense-in-depth contrast with gsd-2 rendered.
    - [check: must_haves.truths[8]] tool.execute.before 7-layer extended stack rendered with Phase 405's layers 5-7 named.
    - [check: must_haves.truths[9]] 20-default cap + rationale rendered; gsd-2 8/4 contrast cited.
    - [check: must_haves.truths[10]] Daemon-side FIFO queue mechanism documented; pLimit(MAX_CONCURRENCY) gsd-2 parallel cited.
    - [check: must_haves.truths[11]] Per-Slice `subagent: {parallel_cap}` narrowing-only override rendered; `subagent_cap_expansion_rejected` event named.
    - [check: must_haves.truths[12]] Grandchild accounting deferral renders with parallel_cap^2 = 400 risk acknowledged.
    - [check: must_haves.truths[13]] dispatch_subagent + state_build/subagents/dispatch.py module path named.
    - [check: must_haves.truths[14]] Mode-isolation note rendered (BUILD_ONLY_EVENT_PREFIXES, CI import-graph lint).
    - [check: must_haves.truths[15]] No `GSD-` literal in the file.
    - [check: must_haves.artifacts[0]] File at the spec'd path with min_lines: 450.
  </acceptance_criteria>

  <done>
    SUBAGENT-MANAGEMENT.md complete at ≥450 lines; sections 1-7 render per Tasks 1+2; verify-block bash passes; no `GSD-` literal.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

```bash
F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md

for section in \
  "^# Subagent Management" \
  "^## dispatch_subagent MCP Tool" \
  "^## SubagentType Whitelist" \
  "^## Compile-Time Exhaustiveness" \
  "^## Static Whitelist Enforcement" \
  "^## Parallel Cap Accounting" \
  "^## Cross-Reference"; do
  grep -qE "$section" "$F" || { echo "MISSING: $section"; exit 1; }
done

wc -l "$F" | awk '{ if ($1 < 450) { print "LINE_COUNT_FAIL: " $1; exit 1 } }'
! grep -qE '\bGSD-' "$F" || { echo "GSD_NAMING_VIOLATION"; exit 1; }

for term in \
  'DispatchSubagent' \
  'SingleDispatch' \
  'ParallelDispatch' \
  'ChainDispatch' \
  'SubagentType' \
  'STAGE_ROSTER' \
  'assert_never' \
  'allowed_subagents' \
  'subagent_whitelist_violation' \
  'subagent_cap_expansion_rejected' \
  'MAX_PARALLEL_CAP_DEFAULT' \
  'state_build/subagents/types.py' \
  'state_build/subagents/dispatch.py' \
  'state_build/subagents/parallel_cap.py'; do
  grep -q "$term" "$F" || { echo "MISSING_TERM: $term"; exit 1; }
done

echo "SUBAGENT-MANAGEMENT.md verification OK"
```
</verification>

<success_criteria>
- SUBAGENT-MANAGEMENT.md exists at `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md` with ≥ 450 lines.
- All 7 sections render verbatim per 405-CONTEXT.md.
- SUB-01..SUB-04 fully covered (SUB-05..SUB-09 deferred to Plan 03).
- No `GSD-` literal in the file (project naming discipline).
- All Pydantic class definitions render with `model_config = ConfigDict(extra="forbid")`.
- Forward-pointers to Plan 03 (SUBAGENT-MONITORING.md) and Plan 04 (EVENT-TAXONOMY.md amendment) rendered.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/405/02-subagent-management-spec-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: spec-doc final line count, sections rendered, requirement coverage (SUB-01..SUB-04 all addressed; SUB-05..SUB-09 forward-pointed to Plan 03), naming-discipline verification result (`grep '\bGSD-' = 0`).
</output>
