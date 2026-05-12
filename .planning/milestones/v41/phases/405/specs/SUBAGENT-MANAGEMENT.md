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
