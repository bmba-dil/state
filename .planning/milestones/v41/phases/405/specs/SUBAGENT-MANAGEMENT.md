# Subagent Management (Canonical, v41, Part 1 of 2)

> **Phase:** 405
> **Status:** Canonical (v41)
> **Requirements covered (this file, Part 1):** SUB-01, SUB-02, SUB-03, SUB-04
> **Requirements covered by Part 2 (`SUBAGENT-MONITORING.md`):** SUB-05..SUB-09 (Plan 03)
> **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
> **Sibling specs:** DEVIATION-RULES.md (Plan 01 — autonomy inheritance from DEV-05/DEV-06 + escalation to Rule 3 / Rule 4 from spot-check + crash exhaustion; consumed by Part 2).
> **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Trailer `STATE-Subagent-Invocation:` is mandatory on every commit inside a subagent session (DEVIATION-RULES.md cross-references).
> **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.

## Overview

The harness spawns subagents via opencode's `task` tool wrapped by the `dispatch_subagent` MCP tool — typed-spawn only (no string-prompt-only invocations). Each spawn names a `subagent_type` from a static whitelist organized into 4 rosters (one per Slice stage). Slice frontmatter MAY narrow the whitelist (subset only) but never expand. Parallel fanout is near-uncapped (default 20 concurrent) with daemon-side FIFO queuing. Subagents are "free context" — aggressive fanout encouraged for research, pattern-mapping, validation. Plan 03 (sibling spec `SUBAGENT-MONITORING.md`) covers monitoring (SSE events), structured returns + spot-check, crash recovery, task_id survival, and autonomy inheritance.

This spec, Part 1 of 2, owns the **spawn surface**: the typed MCP tool (SUB-01), the static whitelist + per-stage rosters (SUB-02), the narrowing-only frontmatter override with two-gate enforcement (SUB-03), and the 20-default parallel cap with daemon semaphore (SUB-04). Part 2 owns observability and recovery surfaces.

---

## dispatch_subagent MCP Tool (SUB-01)

### Tool registration

MCP tool name: `dispatch_subagent`. Registered under the `state-build` MCP server. Module path: `state_build/subagents/dispatch.py`. Wraps opencode's `task` tool with state-specific validation (whitelist, parallel cap, autonomy inheritance — Plan 03). The opencode `task` tool is the underlying spawn primitive; state never invokes it directly. The state-daemon receives `dispatch_subagent` calls, applies the layered `tool.execute.before` middleware (Section 5), then delegates to opencode's `task` tool with the validated payload.

### Top-level signature (Pydantic-typed)

The `DispatchSubagent` Pydantic class is the canonical typed-spawn surface. Three sub-payload classes (`SingleDispatch`, `ParallelDispatch`, `ChainDispatch`) encode the three execution modes. All four classes use `model_config = ConfigDict(extra="forbid")` per the state convention (Phase 400 FRONTMATTER-SCHEMAS.md).

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict

class DispatchSubagent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["single", "parallel", "chain"]
    single: SingleDispatch | None = None
    parallel: list[ParallelDispatch] | None = None       # 1..20 entries per SUB-04
    chain: list[ChainDispatch] | None = None             # unlimited length, sequential

class SingleDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subagent_type: SubagentType                          # Literal union from SUB-02 whitelist
    task: str                                            # the prompt
    cwd: str | None = None                               # defaults to parent's worktree
    model: str | None = None                             # provider model override
    autonomy: Literal["tiered","full-yolo","conservative"] | None = None  # SUB-09 inheritance override

class ParallelDispatch(SingleDispatch):
    model_config = ConfigDict(extra="forbid")
    pass

class ChainDispatch(SingleDispatch):
    model_config = ConfigDict(extra="forbid")
    pass                                                 # chain mode uses `{previous}` text-substitution
                                                         # in the `task` field, populated from prior step output
```

Reference: `~/projects/gsd2deconstruction/kb/agents/agent-roles.md` §3.2 + `subagent/index.ts:618-626`. The three modes mirror gsd-2's `SubagentParams` shape; state's Python analog uses Pydantic root validators for the exactly-one-mode enforcement. State diverges: 20-cap default (vs gsd-2 `MAX_PARALLEL_TASKS=8` + `MAX_CONCURRENCY=4`).

### Exactly-one-mode validation

A Pydantic root validator enforces exactly one of `single` / `parallel` / `chain` is set; the other two MUST be `None`. The predicate is:

```python
sum(1 for x in (single, parallel, chain) if x is not None) == 1
```

Violation → Pydantic `ValidationError` at parse time. Mirrors gsd-2's mode resolution at `subagent/index.ts:709-720`. v14 unit tests assert against all 8 = 2^3 combinations (`{single, parallel, chain}` × `{set, unset}`).

### Mode semantics

- **`single`:** one subagent invocation, synchronous-from-the-harness-perspective; daemon awaits opencode's `task` tool resolution. Most common for verification-flavored spawns (e.g., `nyquist-auditor` against a completed Slice).

- **`parallel`:** N concurrent invocations, 1..20 entries (capped by SUB-04 per Section 6). All dispatched simultaneously; daemon waits for all to terminate (success or crash) before returning the aggregated result vector. Mirrors gsd-2's `pLimit(MAX_CONCURRENCY)` shape but at the daemon layer rather than per-tool-call.

- **`chain`:** sequential invocations with text-substitution between steps. The `task` field of step `i+1` may include `{previous}` literal placeholders, populated from step `i`'s structured return shape's textual fields (Plan 03 SUB-06 owns the return-shape registry and substitution mapping). Unlimited chain length. Useful for pipelines like `researcher → pattern-mapper → planner`.

### MCP tool name + state ownership

Single-source-of-truth: the tool name `dispatch_subagent` is owned by this spec. No other spec defines a subagent-dispatch entrypoint. Phase 406's HRN-03 MCP tool catalog forward-references this spec. The module path `state_build/subagents/dispatch.py` is named verbatim; v14 implements.

---

## SubagentType Whitelist (SUB-02)

The 14 named subagent types are organized into 4 stage rosters (`discuss-slice`, `plan-slice`, `execute-slice`, `verify-slice`). Some types are dual-listed across rosters (notably `researcher`, which serves both discuss-slice exploration and plan-slice deep-dive); runtime stage gates determine which roster applies for whitelist enforcement.

### SubagentType Literal

The Literal union below is rendered verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Subagent typed-spawn surface (SUB-01 + SUB-02 expanded)" subsection. Mirrors SUB-02 in REQUIREMENTS.md.

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

Total: 14 named types. Comments indicate the primary stage roster for each type. `researcher` is intentionally dual-listed across both `discuss-slice` and `plan-slice` rosters per SUB-02 verbatim (see STAGE_ROSTER below).

### STAGE_ROSTER materialization

`STAGE_ROSTER` is the canonical whitelist lookup table. Keys are `SliceStage` Literal values (Phase 402 SLICE-CYCLE.md); values are `frozenset[SubagentType]` for O(1) membership tests and structural-sharing safety.

```python
STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]] = {
    "discuss-slice": frozenset({"researcher", "code-mapper", "requirements-analyzer"}),
    "plan-slice":    frozenset({"researcher", "pattern-mapper", "planner", "plan-validator", "plan-checker"}),
    "execute-slice": frozenset({"executor", "code-fixer", "test-generator", "security-auditor"}),
    "verify-slice":  frozenset({"verifier", "integration-checker", "nyquist-auditor"}),
}
```

Note: `researcher` is intentionally dual-listed in both `discuss-slice` and `plan-slice` rosters per the SUB-02 specification verbatim. The runtime stage gate (Section 5) determines which roster applies based on the active Slice's current stage. No other type is dual-listed at the v1 starter; the planner finalizes the exact dual-listed types during v14 EXEMPLAR work.

### Module ownership

Single-source-of-truth module: `state_build/subagents/types.py`. Exports:

- `SubagentType` (Literal union, 14 members)
- `STAGE_ROSTER` (`dict[SliceStage, frozenset[SubagentType]]`, 4 keys)
- `SliceStage` (re-exported from Phase 402 module; convenience)
- `assert_subagent_type_in_stage(t: SubagentType, stage: SliceStage) -> None` — raises `SubagentWhitelistViolation` on mismatch
- `effective_whitelist(stage: SliceStage, frontmatter: list[SubagentType] | None) -> frozenset[SubagentType]` — computes the per-Slice effective whitelist (Section 5)

v14 implements; v15 imports for plan-validation; Phase 406's MCP catalog forward-references the module path.

### Per-stage roster boundaries

When a `subagent_type` plausibly serves two stages (e.g., `researcher` in both discuss-slice and plan-slice), the type appears in BOTH stage frozensets. Runtime stage gates determine which roster applies. The planner finalizes the exact dual-listed types during v14 EXEMPLAR work; SUB-02's verbatim roster is the v1 starter (`researcher` dual-listed as documented above). Future patches that add dual-listed types MUST update both stage frozensets AND the SubagentType Literal in a single atomic change to preserve `assert_never` exhaustiveness (Section 4).

---

## Compile-Time Exhaustiveness via assert_never

State adopts a stricter validation pole than gsd-2 for the subagent registry: a missing `SubagentType` entry in the dispatcher or return-shape registry fails at **type-check time** (mypy / pyright), not at runtime. This diverges from gsd-2's runtime-discovery-with-synthetic-error-fallback pattern (`subagent/index.ts:344-358`). Mirrors gsd-2's `exhaustive-registry-with-satisfies-constraint.md` pattern with Python idioms (Literal union + `assert_never` instead of TypeScript `satisfies Record<K,V>`).

### Pattern

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

A future patch adding a `SubagentType` Literal value but forgetting the dispatcher case raises a mypy / pyright error at type-check time. CI MUST run `mypy --strict src/state_build/subagents/` (and `pyright --warnings`) on every PR. Mirrors gsd-2 `exhaustive-registry-with-satisfies-constraint.md` (TypeScript `satisfies Record<K,V>`); state's Python analog is `Literal` union + `assert_never` + Pydantic registry. The same exhaustiveness pattern guards the `SUBAGENT_RETURN_REGISTRY` (Plan 03 owns).

### gsd-2 contrast

gsd-2's `subagent/index.ts:344-358` falls back to a synthetic-error generation when an unknown agent name appears at runtime — a permissive runtime model that trusts the LLM to pick valid agent names at dispatch. State's stricter pole rejects unknown types at compile time AND at runtime. The defensive-pole choice mirrors Phase 404 PROOF-GATE.md's PRF server-recomputation discipline: state never trusts agent-emitted aggregates without machine recomputation.

### Mode-isolation note

`state_build/subagents/types.py` MUST NOT import from `state_teach/`. CI import-graph lint enforces (cardinal rule, PROJECT.md). The 14 named `SubagentType` values are Build-only; teach-mode harness owns its own roster (v47 territory, separate Literal union). Events emitted by this module live in the `BUILD_ONLY_EVENT_PREFIXES` set (Phase 400 EVENT-TAXONOMY.md amendment in Plan 04).

---

## Static Whitelist Enforcement + Narrowing-Only Override (SUB-03)

SUB-03 specifies that Slice frontmatter `allowed_subagents` MAY narrow the per-stage whitelist (subset only) but cannot expand it. Defense-in-depth: state enforces this at **TWO gates** (plan-validation AND runtime `tool.execute.before`) — both pure-machine, both required to agree before dispatch fires. Diverges from gsd-2's single-gate runtime-only model (`precedence-divergence-by-trust-model.md` defense-in-depth pole).

### Slice frontmatter field

The Slice frontmatter schema (Phase 403 STEP-PLAN-FORMAT.md owns the base; this spec adds one field) gains `allowed_subagents`:

```python
class SliceFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... existing v40+Phase 403 fields ...
    allowed_subagents: list[SubagentType] | None = None  # SUB-03
```

`None` means use the per-stage default (`STAGE_ROSTER[current_stage]` verbatim). When set, the list MUST be a non-empty subset of `STAGE_ROSTER[current_stage]` for the Slice's active stage. The empty list `[]` is rejected at plan-validation stage (interpreted as "the planner forgot to fill in the field, not 'no subagents allowed'"; explicit "no subagents" must use the per-Slice `subagent: {parallel_cap: 0}` override in Section 6).

### Enforcement protocol (5-step numbered)

1. **Resolve current Slice stage** via active task context (`(slice_id, current_stage)`). The stage comes from the Slice's FSM state (Phase 402 SLICE-CYCLE.md `state.slice.stage_entered` event). The daemon's session projector maintains `current_stage: SliceStage` per active Slice; rebuilt from event-store on boot.

2. **Lookup `STAGE_ROSTER[current_stage]`** — a `frozenset[SubagentType]` of allowed types for this stage. The lookup is O(1) dict access; the frozenset enables O(1) membership tests.

3. **Read Slice frontmatter `allowed_subagents: list[SubagentType] | None`** — the per-Slice override. The frontmatter is the parsed YAML header of the Slice's `SLICE.md` artifact (Phase 403 STEP-PLAN-FORMAT.md schema).

4. **Compute effective whitelist:** `effective_whitelist = frontmatter ?? STAGE_ROSTER[current_stage]`. If frontmatter is supplied, verify `set(frontmatter) ⊆ STAGE_ROSTER[current_stage]` (narrowing-only); if frontmatter expands (any value not in `STAGE_ROSTER[current_stage]`), reject the plan at plan-validation stage (NOT at runtime — narrowing-only validation happens during plan-slice's validation stage per Phase 403 pattern). The expansion-rejection event is `state.slice.validation_failed` with `reason="allowed_subagents_expansion"` payload.

5. **At runtime:** for each (single/parallel/chain) entry in the `dispatch_subagent` payload, verify `entry.subagent_type ∈ effective_whitelist`. Mismatch → reject the dispatch call with `state.step.subagent_whitelist_violation` event payload:

   ```python
   class SubagentWhitelistViolation(BaseModel):
       model_config = ConfigDict(extra="forbid")
       expected: list[SubagentType]      # the effective_whitelist sorted
       requested: SubagentType            # the offending entry.subagent_type
       stage: SliceStage                  # active Slice stage
       task_id: str                       # parent task ULID
       slice_id: str                      # parent Slice ULID
       triggered_at: datetime             # ISO-8601 UTC
   ```

### Two-gate validation (plan-time + runtime)

State enforces narrowing-only at **two independent gates**, both pure-machine, both required to agree before dispatch fires:

- **Gate 1 — Plan-validation stage (Phase 403 `N-VALIDATION.md` machinery).** The planner's research-slice validation stage runs `set(frontmatter) ⊆ STAGE_ROSTER[stage]` for each Slice's `allowed_subagents` against the Slice's active stage roster. Expansion attempts fail `N-VALIDATION.md` and force a replan iteration. Mirrors Phase 403's `depends_on` cross-check pattern. The validator module is `state_build/validators/subagent_whitelist.py`; v15 implements.

- **Gate 2 — Runtime `tool.execute.before` hook.** Even after plan-validation passes, the daemon's `tool.execute.before` middleware re-verifies the per-entry whitelist at dispatch time. Defense-in-depth against post-plan edits (e.g., plan-edit events that bypass plan-validation by accident, or hand-edited Slice frontmatter that escaped re-validation). The runtime gate is the last line of defense.

- **Both gates pure-machine.** No LLM-as-judge anywhere; subset checks are deterministic set operations (`set(frontmatter) ⊆ STAGE_ROSTER[stage]` and `entry.subagent_type ∈ effective_whitelist`). Both gates import `STAGE_ROSTER` from the same `state_build/subagents/types.py` module to prevent whitelist drift (single-source-of-truth).

### tool.execute.before stack extension

The `dispatch_subagent` MCP call enters the daemon's middleware via `tool.execute.before`. The full layered stack (after Phase 405) is:

1. Phase 403 immutability check (PAP-05).
2. Phase 404 `files_modified` allowlist (SRP-04).
3. Phase 404 prohibited-language scan (SRP-02).
4. Phase 404 `<discovered_threats>` append-only carve-out (SRP-04 ancillary).
5. **Phase 405 log_deviation routing + cross-validation** (DEVIATION-RULES.md Section 4).
6. **Phase 405 dispatch_subagent routing + whitelist enforcement + parallel-cap accounting** (this spec Sections 5-6).
7. **Phase 405 arch-pattern allowlist match** for Rule-4 auto-promotion (DEVIATION-RULES.md Section 5).

Order is significant. Cheap (regex / glob / set-membership) checks first; expensive (DB query / projector lookup) checks last. Layers 5-7 are Phase 405's additions. The full stack lives in the daemon's HTTP middleware; the plugin's `tool.execute.before` hook is a thin reporter that posts to the daemon and applies the daemon's verdict. Mirrors v6's daemon-as-single-decision-gate architecture.

### Layer-6 routing internals

Layer 6 in the stack above dispatches every `dispatch_subagent` MCP call through a four-stage internal pipeline before opencode's `task` tool is invoked:

1. **Mode-arity check.** Validate `DispatchSubagent.mode` matches the exactly-one-mode root validator (Section 2). Reject `ValidationError`s synchronously; no event emitted (Pydantic-level rejection precedes event accounting).
2. **Per-entry stage-roster membership.** For each `entry` in `single | parallel | chain`, verify `entry.subagent_type ∈ effective_whitelist` (Section 5 step 5). Mismatch emits `state.step.subagent_whitelist_violation` and rejects the entire dispatch — partial dispatches are not permitted (atomicity preserved).
3. **Parallel-cap slot acquisition.** For `mode="parallel"` only: call `acquire_slot(parent_task_id)` for each entry; queue beyond `MAX_PARALLEL_CAP_DEFAULT` (Section 6). For `mode="single"` and `mode="chain"` (sequential), the cap accounting is one slot held for the duration of the call.
4. **Autonomy inheritance resolution.** Resolve per-entry `autonomy` field with parent-Slice inheritance fallback (Plan 03 SUB-09 owns the precedence chain; this spec defines the field shape only).

Each stage emits a `state.subagent.dispatch_stage_passed` debug event (Plan 03 owns the schema) for observability. Stage failures emit the stage-specific rejection event and abort the pipeline. The pipeline is purely synchronous up to stage 3; stage 3 may block on slot acquisition.

### Atomicity guarantee

If any entry in a `parallel` or `chain` payload fails layer-6 stage 2 (whitelist check), the entire dispatch is rejected — no entries dispatch. This is the **all-or-nothing semantics** documented for v1. v14 unit tests assert against this invariant. Partial-dispatch semantics (dispatch the valid entries, reject the invalid ones individually) is deferred to post-v17 if real workloads show that all-or-nothing wastes too much context on retries.

### Failure-event flow

When a layer-6 stage rejects a dispatch, the daemon middleware emits the rejection event (one of `state.step.subagent_whitelist_violation`, `state.slice.subagent_cap_expansion_rejected`, or the Plan 03-owned autonomy events), persists it to the event-store, and returns an MCP error response to the calling agent. The agent's `tool.execute.after` hook receives the error and surfaces it as a structured tool-result; the agent's next turn observes the rejection and adjusts (e.g., re-dispatches with a valid subagent_type, or escalates via `log_deviation`). The rejection-event taxonomy is fully registered in Phase 400 EVENT-TAXONOMY.md's v41 amendment (Plan 04).

### gsd-2 contrast

State diverges from gsd-2's permissive runtime model. gsd-2's `subagent/index.ts:344-358` has no narrowing-only mechanism at plan time — gsd-2 trusts the LLM to pick valid agent names at dispatch, with a synthetic-error fallback when an unknown agent name surfaces. State's stricter pole validates both at plan-validation AND at runtime `tool.execute.before` — both gates pure-machine. Mirrors `precedence-divergence-by-trust-model.md`: state's defense-in-depth pole reflects the same principled trade-off as Phase 404's PRF server-recomputation discipline (machine never trusts LLM-emitted aggregates).

---

## Parallel Cap Accounting (SUB-04)

SUB-04 specifies the default cap of 20 concurrent subagent invocations per parent Slice session, configurable per-Slice with narrowing-only override. Diverges from gsd-2's `MAX_PARALLEL_TASKS=8` + `MAX_CONCURRENCY=4` (`subagent/index.ts:42-43`) reflecting SUB-04's "subagents are free context, aggressive fanout encouraged" framing.

### Default cap

**20 concurrent invocations per parent Slice session.** Higher than gsd-2's 8/4 cap because:

- (a) SUB-04 explicitly encourages aggressive fanout for research, pattern-mapping, and validation;
- (b) state's per-Slice subagent diversity is higher (14 named types across 4 rosters);
- (c) opencode's `task` tool spawns each subagent in a fresh process — system-level concurrency is bounded by OS resources (file handles, memory, CPU), not state's framework.

The 20 number is encoded as `MAX_PARALLEL_CAP_DEFAULT: int = 20` in `state_build/subagents/parallel_cap.py`. v14 implements; the constant is the single-source-of-truth.

### Enforcement mechanism

- **In-flight counter at daemon-side dispatch handler.** When `dispatch_subagent(mode="parallel", parallel=[...20+ entries])` is received, the handler queues entries beyond 20 (FIFO); slots free as `state.step.subagent_complete` or `state.step.subagent_crash_detected` events fire (Plan 03 owns these events). The counter is maintained per `parent_task_id` to scope concurrency to the dispatching Slice session.

- **Mirrors gsd-2's `pLimit(MAX_CONCURRENCY)` semaphore shape but at the daemon layer rather than per-tool-call.** State's choice reflects the daemon-as-single-decision-gate architecture (v6). The semaphore is a daemon-level resource, not a process-local one — surviving worker restarts.

- **`subagent_started` event carries `parent_task_id`** to record the parent linkage (SUB-08; Plan 03 owns). Daemon projector maintains `in_flight_subagents: dict[parent_task_id, int]` rebuilt from event-store on boot (mirrors v6 daemon crash-recovery pattern). The projector is the authoritative count source; the in-process semaphore is a read-through cache.

### Per-Slice override (narrowing-only)

- **Slice frontmatter:** `subagent: {parallel_cap: int | None}` (nested under `SubagentSliceConfig`):

  ```python
  class SubagentSliceConfig(BaseModel):
      model_config = ConfigDict(extra="forbid")
      parallel_cap: int | None = None         # SUB-04 narrowing-only override (≤20)
      progress_timeout_s: int | None = None    # SUB-07 (Plan 03 owns)
      remediation_hints: dict[str, str] | None = None  # SUB-07 (Plan 03 owns)
  ```

- **Direction:** narrowing-only. May move stricter (8 / 4 / 1 OK; even 0 = "no subagents allowed this Slice"); attempts to expand beyond 20 are rejected at plan-validation stage with `state.slice.subagent_cap_expansion_rejected` event payload:

  ```python
  class SubagentCapExpansionRejected(BaseModel):
      model_config = ConfigDict(extra="forbid")
      slice_id: str
      requested_cap: int          # the frontmatter-supplied value
      max_allowed: int            # = MAX_PARALLEL_CAP_DEFAULT = 20
      triggered_at: datetime
  ```

- **Mirrors Phase 402's `compaction:` field narrowing-only pattern** — the precedent for nested-config-with-narrowing-only. The same plan-validation stage that runs the SUB-03 narrowing check (Gate 1) also runs the SUB-04 cap narrowing check.

### Child-of-child (grandchild) accounting

**Rejected for v1.** Subagents are spawned in fresh opencode sessions; their own `task` tool invocations are managed by opencode, not state-daemon. State accounts only for direct children of the parent Slice session. If a child subagent itself dispatches more subagents (grandchildren), they count against the grandchild's session, not the parent's.

**Risk:** `parallel_cap^2 = 400` worst-case process count if every child fans out 20 grandchildren. Documented as known limitation; revisit if real workloads show concurrency-storm patterns. Mirrors gsd-2's "no explicit guard at the grandchild level" framing in `three-layer-llm-orchestration.md`. Deferred to post-v17.

Operational mitigation in v14: monitor `in_flight_subagents` projector for sustained-high values; alert on `≥150` (the empirical "many concurrent processes" threshold). The alert is informational, not blocking.

### FIFO queue semantics

Excess entries queued FIFO. The daemon dispatch handler holds the request open (HTTP long-poll style or SSE-driven release); slots free as completion / crash events fire. Latency-sensitive priority queuing is **deferred to post-v17** — FIFO is the v1 invariant for simplicity and determinism.

Known limitation: 20 slow subagents can starve a queue of 100 fast follow-ups. If observed, the planner adds a priority field to `SingleDispatch` / `ParallelDispatch` / `ChainDispatch` in v14+ and the queue becomes a priority-FIFO. v1 ships FIFO-only.

### Cap-counter persistence and crash recovery

The in-flight counter (`in_flight_subagents: dict[parent_task_id, int]`) is **derived state** rebuilt from the event-store on daemon boot. The rebuild query selects all `state.step.subagent_started` events whose matching `state.step.subagent_complete` or `state.step.subagent_crash_detected` event has not yet been observed, and groups by `parent_task_id`. This mirrors v6's `derived-state-from-db-decision-tree.md` pattern — no separate persistence layer for the counter, no risk of drift between counter and event log.

On daemon restart mid-dispatch, queued (not-yet-acquired-a-slot) entries are **lost** — the dispatch handler's HTTP request is dropped when the daemon stops, and the calling agent's MCP request fails with a connection-reset error. The agent's `tool.execute.after` hook surfaces this as a structured error; the agent re-dispatches if the parent Slice's stage still allows. The lost-on-restart semantic is acceptable for v1 because daemon restarts are user-initiated maintenance events, not steady-state behavior. v14 may add a persistent dispatch journal if production telemetry shows frequent restarts disrupting long-running parallel fanouts.

In-flight (slot-holding) entries are not lost — opencode's `task` tool runs in fresh child processes that survive daemon restarts; their completion events arrive when the daemon comes back up and trigger normal slot-release. The cap counter rebuilds correctly from the event-store, even across daemon restarts.

### Module ownership

Single-source-of-truth module: `state_build/subagents/parallel_cap.py`. Exports:

- `MAX_PARALLEL_CAP_DEFAULT: int = 20` — the cap constant; do not edit without milestone-level review.
- `resolve_effective_cap(slice_frontmatter: SliceFrontmatter) -> int` — returns `min(frontmatter.subagent.parallel_cap or 20, 20)` with narrowing-only enforcement (returns the lower of the two).
- `acquire_slot(parent_task_id: str) -> SlotHandle` — async; blocks until a slot is free; returns a handle for `release_slot`.
- `release_slot(parent_task_id: str, handle: SlotHandle) -> None` — releases the slot; fires the SSE event that wakes the next FIFO waiter.
- `in_flight_count(parent_task_id: str) -> int` — read-only count; used by Plan 03's monitoring spec.

v14 implements; daemon middleware imports.

### Mode-isolation note

`state_build/subagents/parallel_cap.py` is Build-only. Events `state.step.subagent_whitelist_violation` and `state.slice.subagent_cap_expansion_rejected` live in `BUILD_ONLY_EVENT_PREFIXES` (Phase 400 EVENT-TAXONOMY.md amendment in Plan 04). CI import-graph lint enforces; `state_teach/` MUST NOT import this module.

### Worked example: 25-entry parallel dispatch

Suppose a `plan-slice` Slice with `allowed_subagents = None` (use stage default) and `subagent.parallel_cap = None` (use 20 default) dispatches:

```python
DispatchSubagent(
    mode="parallel",
    parallel=[
        ParallelDispatch(subagent_type="researcher", task=f"Investigate facet {i}")
        for i in range(25)
    ],
)
```

Flow:

1. **Layer-6 stage 1 (mode-arity):** passes — `mode="parallel"` matches `parallel != None, single == None, chain == None`.
2. **Layer-6 stage 2 (whitelist):** all 25 entries have `subagent_type="researcher"`; `researcher ∈ STAGE_ROSTER["plan-slice"] = frozenset({"researcher", "pattern-mapper", "planner", "plan-validator", "plan-checker"})`. Passes.
3. **Layer-6 stage 3 (parallel-cap):** `effective_cap = 20`. First 20 entries acquire slots and dispatch immediately to opencode's `task` tool; entries 21..25 enqueue FIFO. Each pending entry emits `state.subagent.queued` (Plan 03 owns schema).
4. **Slot release:** as the first 20 emit `state.step.subagent_complete` events, the daemon releases slots FIFO; entries 21..25 dispatch in arrival order.
5. **Aggregate result:** the dispatch handler awaits all 25 completions; the MCP response is a `list[SubagentResult]` of length 25 in dispatch order (Plan 03 SUB-06 defines `SubagentResult`).

Worst-case time = `max(t_first_20) + sum(t_extra_5)` if the first 20 run fully parallel and the queue drains serially; in practice queue drain interleaves as slots free. v14 unit tests assert against this dispatch-order invariant.

### Worked example: cap-expansion rejection at plan time

Suppose a Slice's frontmatter contains:

```yaml
subagent:
  parallel_cap: 50  # attempts to expand beyond 20
```

Flow:

1. **Plan-validation stage (Gate 1, Phase 403 `N-VALIDATION.md`):** validator runs `frontmatter.subagent.parallel_cap <= MAX_PARALLEL_CAP_DEFAULT` ⇒ `50 <= 20` ⇒ false ⇒ emit `state.slice.subagent_cap_expansion_rejected(slice_id=..., requested_cap=50, max_allowed=20, triggered_at=...)`, fail plan-validation.
2. The planner agent receives the validation-failure signal, must edit the frontmatter to `parallel_cap <= 20` (e.g., `parallel_cap: 8`), and re-submit the plan for validation. The Slice does not enter `execute-slice` stage until validation passes.
3. **Runtime defense-in-depth:** even if the plan-validation gate were somehow bypassed, the runtime `resolve_effective_cap` would return `min(50, 20) = 20`; the daemon would simply enforce 20 at slot acquisition. The plan-validation gate is the **authoritative rejection point**; the runtime cap is a belt-and-suspenders fallback.

---

## Cross-Reference: Monitoring + Spot-Check + Crash Recovery + task_id Survival + Autonomy Inheritance

Plan 03 of Phase 405 ships `SUBAGENT-MONITORING.md` (sibling spec doc) covering:

- **SUB-05** — SSE event family (`state.step.subagent_started` / `subagent_progress` / `subagent_complete`) linked by parent `task_id`.
- **SUB-06** — `SUBAGENT_RETURN_REGISTRY` (central Pydantic registry per `SubagentType`) + 4-layer spot-check protocol (process classification / Pydantic validate / artifact existence / commit existence).
- **SUB-07** — 5-source crash taxonomy + 3-restart counter with augmented `<prior_crash>` continuation context.
- **SUB-08** — `task_id` survival across compaction and Slice-boundary respawn (cross-references CTX-07).
- **SUB-09** — Autonomy inheritance from parent Slice (consumes DEV-05 / DEV-06 from DEVIATION-RULES.md Section 6).

The two specs share a single mode-isolation boundary (`state_build/subagents/`) and a single STATE-* trailer convention (`STATE-Subagent-Invocation: <invocation_id>` on every commit produced inside a subagent session; the trailer constant lives in `state_build/commit/trailers.py` per DEVIATION-RULES.md Section 5).

### Forward event registrations (Plan 04)

Plan 04 of Phase 405 appends a `## v41 Amendment — Phase 405 Deviation + Subagent Event Family` block to `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` registering this spec's two new events (`state.step.subagent_whitelist_violation`, `state.slice.subagent_cap_expansion_rejected`) plus DEVIATION-RULES.md's four new events plus Plan 03's eight new events. Authoritative event-payload Pydantic shapes live in the owning specs (this spec, DEVIATION-RULES.md, SUBAGENT-MONITORING.md); the taxonomy amendment is a registry index, not a content source.

### Authoritative-ordering note

**Pydantic class definitions in this spec are authoritative.** The runtime enforcement protocol (Section 5) and the parallel-cap mechanism (Section 6) are operational shapes for v14 to implement; v14 unit tests assert against the Pydantic definitions in this spec as fixtures. If implementation and spec diverge, the spec wins — patch the implementation, do not retroactively edit the spec without a Phase-level amendment.

### Requirement coverage summary

| Requirement | Section | Status |
|---|---|---|
| SUB-01 (dispatch_subagent typed MCP tool) | §2 | Fully specified |
| SUB-02 (static whitelist per stage, 14 types, 4 rosters) | §3 | Fully specified |
| SUB-03 (narrowing-only frontmatter override, 2-gate enforcement) | §5 | Fully specified |
| SUB-04 (20-default parallel cap, FIFO queuing, narrowing-only per-Slice override) | §6 | Fully specified |
| SUB-05..SUB-09 | — | Forward-pointed to Plan 03 (`SUBAGENT-MONITORING.md`) |

### Module path inventory (single-source-of-truth references)

For v14 EXEMPLAR work and v15 plan-validation wiring, the following module paths are the authoritative single-source-of-truth references owned by this spec. v14 implements; v15 imports; do not re-derive in downstream artifacts.

| Module | Purpose | Owned by |
|---|---|---|
| `state_build/subagents/types.py` | `SubagentType` Literal, `STAGE_ROSTER`, `effective_whitelist` | §3, §5 |
| `state_build/subagents/dispatch.py` | `dispatch_subagent` MCP tool handler + layer-6 pipeline | §2, §5 |
| `state_build/subagents/parallel_cap.py` | `MAX_PARALLEL_CAP_DEFAULT`, slot acquisition, in-flight projector | §6 |
| `state_build/validators/subagent_whitelist.py` | plan-validation Gate 1 narrowing-only check | §5 (Gate 1) |
| `state_build/commit/trailers.py` | `STATE-Subagent-Invocation:` trailer constant | §7 (cross-ref) |

### Open questions deferred to v14

The following operational questions are deliberately left open for v14 EXEMPLAR work, which will pick concrete values informed by real workloads:

- **Slot acquisition timeout:** if `acquire_slot` blocks indefinitely, the dispatching agent may stall. v14 picks a per-Slice timeout (likely `progress_timeout_s` from Plan 03 SUB-07 reused).
- **Queue depth alerting threshold:** the `≥150 in-flight` informational alert (Section 6) is a placeholder; v14 tunes to empirical load.
- **Per-`subagent_type` cap differentiation:** v1 ships uniform 20 across all types; v14+ may differentiate (e.g., `researcher: 30, executor: 4`) if real workloads show distinct fanout patterns.

These are open questions, not gaps — the v1 spec is fully self-contained.

### Closing note

This spec is Part 1 of 2. Part 2 (`SUBAGENT-MONITORING.md`, Plan 03 of Phase 405) covers the observability, return-shape registry, spot-check protocol, crash recovery, task_id survival, and autonomy inheritance surfaces. Together the two specs fully cover SUB-01..SUB-09. Plan 04 of Phase 405 amends Phase 400's EVENT-TAXONOMY.md with the v41 event family registrations for both specs.

End of Part 1.
