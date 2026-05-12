# Subagent Monitoring (Canonical, v41, Part 2 of 2)

> **Phase:** 405
> **Status:** Canonical (v41)
> **Requirements covered (this file, Part 2):** SUB-05, SUB-06, SUB-07, SUB-08, SUB-09
> **Sibling spec (Part 1 of 2):** SUBAGENT-MANAGEMENT.md (SUB-01..SUB-04 — dispatch_subagent, whitelist, parallel cap).
> **Cross-reference spec:** DEVIATION-RULES.md (autonomy inheritance consumes DEV-05/DEV-06; spot-check + crash exhaustion escalate via log_deviation Rule 3 / Rule 4).
> **Cross-reference spec:** CONTEXT-PROTOCOL.md (Phase 402; CTX-07 task_id survival cross-referenced by SUB-08).
> **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
> **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Trailer `STATE-Subagent-Invocation: <invocation_id>` mandatory on every commit inside a subagent session.
> **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.

## Overview

The harness monitors every spawned subagent via three SSE events (`subagent_started` / `subagent_progress` / `subagent_complete`) linked by `parent_task_id`. Returns are structured (typed per `SubagentType`); a 4-layer pure-machine spot-check stack validates each return at completion. Crashes (5 sources) feed a per-`(parent_task_id, subagent_type)` 3-restart counter; the 4th occurrence escalates to Rule 3 / Rule 4. Restart prompts carry a `<prior_crash>` XML block with augmented continuation context. `task_id` survives compaction and Slice-boundary respawn via event-store rehydration. Subagents inherit autonomy from the parent Slice, with optional per-dispatch override.

This is Part 2 of 2. Part 1 (SUBAGENT-MANAGEMENT.md) defines the dispatch surface (SUB-01..SUB-04): `SubagentType` Literal, `STAGE_ROSTER` constant, `dispatch_subagent` MCP tool shape (single/parallel/chain dispatch modes), the whitelist enforcement, and the per-Slice parallel cap. This file (Part 2) defines the runtime monitoring layer that wraps every dispatched subagent from spawn through completion or escalation.

The eight new SSE event types added by this spec are (registered in EVENT-TAXONOMY.md by Plan 04):

- `state.step.subagent_started`
- `state.step.subagent_progress`
- `state.step.subagent_complete`
- `state.step.subagent_spot_check_failed`
- `state.step.subagent_crash_detected`
- `state.step.subagent_restart`
- `state.step.subagent_restart_exhausted`
- `state.step.subagent_orphan_detected`

All event payloads are Pydantic models with `model_config = ConfigDict(extra="forbid")` (cardinal Pydantic discipline; mirrors FRONTMATTER-SCHEMAS.md convention from Phase 400). All Pydantic class definitions in this file are authoritative — prose is supplementary. v14 (Build Kernel) implements the daemon-side projectors and middleware; v9 (shipped) provides the plugin-side SSE subscribers.

## SSE Event Family (SUB-05)

### Three core events

The daemon emits exactly three core SSE events per subagent lifecycle, plus five derived monitoring events covered in later sections. The core three are:

- `state.step.subagent_started` — emitted by the daemon dispatch handler immediately after opencode's `task` tool spawn confirms session creation. Carries the `SubagentStarted` payload.
- `state.step.subagent_progress` — emitted on every TUI-visible event from the child session (`message_end`, `tool_use` start/end, etc. per gsd-2 `processSubagentEventLine` shape). Carries the `SubagentProgress` payload.
- `state.step.subagent_complete` — emitted when the child session reaches `stop_reason` ∈ {`end_turn`, `tool_use`, `max_tokens`, `error`, `aborted`}. Carries the `SubagentComplete` payload.

The three events form an ordered lifecycle: `subagent_started` (exactly one per dispatch) → `subagent_progress` (zero-or-more) → `subagent_complete` (exactly one per dispatch, unless a crash event short-circuits the chain — see Section 5).

### Pydantic event payloads

```python
class SubagentStarted(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str               # ulid; unique per dispatch
    parent_task_id: str              # the parent Slice session's active task_id
    subagent_type: SubagentType
    slice_id: str
    task: str                        # the prompt (bounded ≤8KB; mirrors gsd-2 truncation)
    started_at: datetime             # UTC, ISO-8601
    session_id: str                  # opencode session id for the spawned subagent

class SubagentProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str
    parent_task_id: str
    kind: Literal["message_end", "tool_use_start", "tool_use_end", "step_event", "other"]
    payload_excerpt: str             # ≤2KB; gsd-2 truncation discipline
    emitted_at: datetime
    session_id: str

class SubagentComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str
    parent_task_id: str
    subagent_type: SubagentType
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "error", "aborted"]
    declared_artifacts: list[ArtifactDeclaration]   # see Section 3
    declared_commits: list[str]                     # commit SHAs in worktree branch order
    completed_at: datetime
    session_id: str
    error_message: str | None
```

Field set drawn from 405-CONTEXT.md `<decisions>` "Subagent typed-spawn surface" + "Structured return shape registry" subsections.

### Parent-task linkage

Every subagent event carries `parent_task_id`. The daemon's SSE filter subscribes by `parent_task_id` to surface child events on the parent's TUI stream (v9 sidebar + statusline). The daemon projector maintains `in_flight_subagents: dict[parent_task_id, list[InFlightSubagent]]` rebuilt from `subagent_started` / `subagent_complete` / `subagent_crash_detected` events. Cross-references gsd-2 `agent-lifecycle.md` §2.2 `agent.sessionId = sessionManager.getSessionId()` invariant — `parent_task_id` is state's stable cross-process identifier.

The discipline is strict: NO subagent event may be emitted without a populated `parent_task_id`. The daemon middleware rejects any subagent event missing this field at the event-store write boundary. This invariant is what enables the orphan reconciliation flow (Section 7) to walk the event log and rebuild `in_flight_subagents` from `subagent_started` events that lack a paired terminal event.

The chain of identifier survival reads (from outermost to innermost): `slice_id` (Slice frontmatter, survives all session boundaries via CTX-07) → `parent_task_id` (the Step-tier task within the parent Slice session, survives compaction per CTX-07) → `invocation_id` (the ulid minted at `dispatch_subagent` time, unique per dispatch, does NOT survive across restarts — each restart mints a fresh `invocation_id` referenced by `previous_invocation_id` on the `SubagentRestart` event). The fresh-per-restart `invocation_id` discipline is what keeps the SSE event stream auditable: every `subagent_started` ulid is unique forever, and the projector can rebuild restart chains by following the `previous_invocation_id` back-link.

### SSE bus position

The events live on the daemon's SSE bus (the equivalent of gsd-2's Bus A / tool-call bus, per `cross-layer-communication-map.md`). The plugin's `chat.params` and `tool.execute.after` hooks subscribe and forward to opencode's TUI. v14 implements the daemon SSE bus; v9 (shipped) implements the plugin-side subscriber.

The bus topology is one-way fan-out: the daemon publishes, every interested subscriber (parent's TUI, the autonomy projector, the orphan-reconciliation projector, the restart-counter projector) consumes independently. There is no back-pressure from the SSE bus to the daemon's event-store write path — event-store write is authoritative and happens FIRST, SSE emission is mirrored after the write commits (cardinal rule per PROJECT.md).

### Granularity (deferred)

`SubagentProgress.payload_excerpt` granularity (which child events trigger emission) is recommended at gsd-2's `processSubagentEventLine` shape (every message_end + tool_use start/end). Detailed payload schema deferred to v14.

The conservative starter set covered by the `kind` Literal — `message_end`, `tool_use_start`, `tool_use_end`, `step_event`, `other` — is sufficient for v1 sidebar + statusline updates. v14 may refine `step_event` into a subset of state-emitted child-session events (e.g., child `state.step.proof_emitted` mirrored into the parent's stream as a `step_event` kind), or split `other` into named child-event subtypes.

### Event ordering invariants

The harness enforces three ordering invariants at the projector boundary, all rebuildable from the event-store on daemon resume:

1. **At-most-one `subagent_started` per `invocation_id`.** A duplicate `subagent_started` with the same ulid is a projector-detected anomaly and surfaces as a Rule 4 escalation; ulid collisions are computationally negligible, so a duplicate signals a buggy emitter.
2. **At-most-one terminal event per `invocation_id`** where terminal = `subagent_complete` OR `subagent_crash_detected` (any of the five `crash_source` values). A second terminal for the same invocation is a projector anomaly.
3. **No `subagent_progress` after a terminal event** for the same `invocation_id`. Late progress events are dropped at the projector with a `late_progress_dropped` counter; v14 surfaces the counter on the orphan-reconciliation projector for observability.

These three invariants are what make the orphan reconciliation flow (Section 7) deterministic from event-store alone: every `subagent_started` either has a paired terminal event (and the lifecycle is closed) or does not (and the invocation is an orphan candidate).

## SUBAGENT_RETURN_REGISTRY (SUB-06)

Each `SubagentType` has a registered Pydantic return shape. The central registry `SUBAGENT_RETURN_REGISTRY: dict[SubagentType, type[SubagentReturnBase]]` provides compile-time exhaustiveness (via `assert_never` per Plan 02 Section 4). Mirrors gsd-2's `exhaustive-registry-with-satisfies-constraint.md` pattern with Python typing.

The registry exists to make the structured-return contract enforceable at parse time. When `subagent_complete` arrives carrying the return payload, the harness looks up the registered model by `subagent_type` and calls `model_validate_json(payload)` — Pydantic's `extra="forbid"` rejects unknown fields, missing required fields, and type mismatches in one step. There is no validation logic elsewhere; the registry IS the contract.

### Common base class

```python
class ArtifactDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str            # repo-root-relative POSIX
    sha256: str          # full file content hash at write time
    line_count: int

class SubagentReturnBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subagent_type: SubagentType                   # narrowed Literal in per-type subclasses
    parent_task_id: str
    invocation_id: str                            # ulid; the dispatch's unique ID
    declared_artifacts: list[ArtifactDeclaration]
    declared_commits: list[str]                   # commit SHAs in worktree branch order
    stop_reason: Literal["end_turn","tool_use","max_tokens","error","aborted"]
    error_message: str | None
```

`ArtifactDeclaration` is the unit of file-produced evidence: every file a subagent claims to have created or modified must be declared with a path, a SHA-256 content hash, and a line count. The hash is computed by the subagent at write time and verified by the harness at layer-3 spot-check (Section 4). Repo-root-relative POSIX paths are mandatory — absolute paths or non-POSIX separators are rejected at Pydantic parse time (string validators in v14).

`SubagentReturnBase` is the union root for the discriminated-union registry. Per-type subclasses (`ExecutorReturn`, `ResearcherReturn`, etc.) narrow `subagent_type` to a single-element Literal — this gives Pydantic the discriminator it needs for `Annotated[Union[...], Discriminator("subagent_type")]` parsing in v14.

### Registry

```python
SUBAGENT_RETURN_REGISTRY: dict[SubagentType, type[SubagentReturnBase]] = {
    "researcher": ResearcherReturn,
    "code-mapper": CodeMapperReturn,
    "requirements-analyzer": RequirementsAnalyzerReturn,
    "pattern-mapper": PatternMapperReturn,
    "planner": PlannerReturn,
    "plan-validator": PlanValidatorReturn,
    "plan-checker": PlanCheckerReturn,
    "executor": ExecutorReturn,
    "code-fixer": CodeFixerReturn,
    "test-generator": TestGeneratorReturn,
    "security-auditor": SecurityAuditorReturn,
    "verifier": VerifierReturn,
    "integration-checker": IntegrationCheckerReturn,
    "nyquist-auditor": NyquistAuditorReturn,
}
```

The registry has exactly 14 entries — one per `SubagentType` Literal value defined in Plan 02 (SUBAGENT-MANAGEMENT.md Section 3 STAGE_ROSTER). Adding a new subagent type is a two-step change: (1) extend the `SubagentType` Literal in Plan 02's roster, (2) register a new `<Type>Return` subclass here. Both edits land in the same commit; CI's mypy strict check (see "Compile-time exhaustiveness" below) blocks merges that change one without the other.

### Per-type extension example: ExecutorReturn

```python
class ExecutorReturn(SubagentReturnBase):
    subagent_type: Literal["executor"]                   # narrowed Literal for type discriminator
    files_modified_actual: list[str]                    # repo-root-relative; spot-check ⊆ frontmatter files_modified
    test_pass_count: int
    test_fail_count: int
```

The 13 remaining per-type subclasses (ResearcherReturn, CodeMapperReturn, etc.) follow the same shape: `subagent_type` narrowed to a single-element Literal for discriminated-union parsing; extension fields specific to each stage's expected output. v14 authors the remaining models during EXEMPLAR work.

The `files_modified_actual` field is illustrative of the discipline: ExecutorReturn declares what the subagent ACTUALLY modified, which the harness cross-checks against the parent Step's frontmatter `files_modified` allow-list (Phase 403 STEP-PLAN-FORMAT.md). A subagent declaring writes outside the allow-list fails layer-3 spot-check by independent rule, distinct from the path-existence check.

### Module organization

Single-source-of-truth: `state_build/subagents/returns.py` exports `SUBAGENT_RETURN_REGISTRY`, `ArtifactDeclaration`, `SubagentReturnBase`. Per-type subclasses live in `state_build/subagents/returns_{stage}.py` (one module per stage roster: `returns_discuss.py`, `returns_plan.py`, `returns_execute.py`, `returns_verify.py`) and re-export to the registry.

The four stage-keyed modules group per-type subclasses by their position in the EXEMPLAR-stepNPLAN.md gate flow:

- `returns_discuss.py` — `ResearcherReturn`, `CodeMapperReturn`, `RequirementsAnalyzerReturn`, `PatternMapperReturn`
- `returns_plan.py` — `PlannerReturn`, `PlanValidatorReturn`, `PlanCheckerReturn`
- `returns_execute.py` — `ExecutorReturn`, `CodeFixerReturn`, `TestGeneratorReturn`, `SecurityAuditorReturn`
- `returns_verify.py` — `VerifierReturn`, `IntegrationCheckerReturn`, `NyquistAuditorReturn`

Each per-stage module imports only `SubagentReturnBase` + `ArtifactDeclaration` from `returns.py` and exports its per-type subclasses; `returns.py` then collects them into the registry. This shape lets v14 introduce per-stage tests and per-stage refinements without touching the central registry module.

### Compile-time exhaustiveness

Mirrors Plan 02 Section 4's `assert_never` pattern. CI runs `mypy --strict src/state_build/subagents/` to verify every `SubagentType` Literal value has an entry in `SUBAGENT_RETURN_REGISTRY`. Missing entry → mypy error at type-check time. Diverges from gsd-2's runtime-discovery-with-synthetic-error-fallback pattern (`subagent/index.ts:344-358`).

The mypy strict check works by typing the registry as `dict[SubagentType, type[SubagentReturnBase]]` — Python's structural-typing-via-Literal makes mypy reject any dict literal that omits a Literal value. There is no runtime fallback; a missing registration is a build-time error, not a runtime synthetic-error scenario.

### Discriminated-union parsing

The registry is paired with a discriminated-union alias for parse-time dispatch in v14:

```python
SubagentReturn = Annotated[
    Union[
        ResearcherReturn, CodeMapperReturn, RequirementsAnalyzerReturn, PatternMapperReturn,
        PlannerReturn, PlanValidatorReturn, PlanCheckerReturn,
        ExecutorReturn, CodeFixerReturn, TestGeneratorReturn, SecurityAuditorReturn,
        VerifierReturn, IntegrationCheckerReturn, NyquistAuditorReturn,
    ],
    Discriminator("subagent_type"),
]
```

The harness uses `TypeAdapter(SubagentReturn).validate_json(payload)` to dispatch to the correct subclass by `subagent_type` Literal — no manual branching, no fallback path. A payload whose `subagent_type` value is not in the union (e.g., a typo or a removed type) raises a Pydantic ValidationError; layer-2 spot-check records `evidence_excerpt = str(validation_error)` and emits `SubagentSpotCheckFailed` with `layer="pydantic"`.

## 4-Layer Pure-Machine Spot-Check (SUB-06)

At `subagent_complete` event receipt, the harness runs a deterministic 4-layer stack against the structured return. Each layer pure-machine; any layer fails → distinct `layer` field in the `SubagentSpotCheckFailed` event. Mirrors gsd-2's `process-exit-stop-reason-validation.md` 3-signal pattern extended with state's artifact + commit gates.

"Pure-machine" here means each layer's verdict is computable from inputs the harness already has (the structured return + the worktree's file system + the worktree's git state) without consulting an LLM or any prompt-sourced signal. The discipline is critical because the spot-check is the boundary between subagent-emitted claims and server-side truth — any layer that requires LLM interpretation re-introduces the very prompt-injection / hallucination surface the structured-return contract is designed to close.

### Layer stack (4-row markdown table)

| Layer | Check | Failure trigger |
|---|---|---|
| 1. Process classification | `exit_code == 0 AND stop_reason ∉ {error, aborted}` | gsd-2 `isError` formula (`subagent/index.ts:923`) |
| 2. Pydantic validate | `SUBAGENT_RETURN_REGISTRY[type].model_validate_json(payload)` (`extra="forbid"`) | unknown fields, type mismatches, missing required fields |
| 3. Artifact existence | for every `ArtifactDeclaration`: file at `path` exists AND `sha256(file_bytes) == declaration.sha256` AND `count_lines(file) == declaration.line_count` | missing file / hash mismatch / line-count mismatch |
| 4. Commit existence | for every `commit_sha`: `git rev-parse --verify {sha}^{commit}` exits 0 AND commit is reachable from current worktree branch | missing commit / detached |

Layers run in order; the first failure short-circuits the stack and emits `SubagentSpotCheckFailed` with the failing `layer` recorded. Layer 1 is cheapest (already in the `SubagentComplete` payload); layers 2-4 progress from in-memory parse to file-system probe to git-state probe. v14 may add a layer-5 hash-of-commit-tree check post-v17 if observed commit-rewrite scenarios warrant it.

### Failure event payload

```python
class SubagentSpotCheckFailed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str
    parent_task_id: str
    subagent_type: SubagentType
    layer: Literal["process","pydantic","artifact","commit"]
    evidence_excerpt: str            # ≤2KB; gsd-2 truncation discipline
    failed_at: datetime
    session_id: str
```

Event type: `state.step.subagent_spot_check_failed` (registered by Plan 04 in EVENT-TAXONOMY.md).

The `evidence_excerpt` field is the only free-form payload; the discipline mirrors gsd-2's 2KB truncation on prompt-injectable fields. For layer-1 failures, the excerpt is the child session's terminal stdout tail; for layer-2, the offending fragment of the JSON payload + the Pydantic ValidationError message; for layer-3, the failing artifact's declared-vs-actual diff; for layer-4, the failing commit SHA and the `git rev-parse` stderr.

### Server-side recomputation discipline

**The harness recomputes `overall_success` from layer verdicts; agent-emitted aggregates are rejected.** Mirrors gsd-2's `server-recomputation-of-llm-emitted-fields.md` pattern + Phase 404 PRF `overall_passed` recomputation. The subagent's structured return SHALL NOT include an `overall_success` field; if present, it is ignored (Pydantic `extra='forbid'` rejects at parse time).

The reason this discipline is non-negotiable: an LLM-emitted `overall_success: true` could trivially bypass layer-3 (artifact existence) — the subagent has every incentive to claim success because failure is costly. State's contract is that aggregate success is a SERVER computation derived from independent layer verdicts, never an agent-emitted claim. This is the exact same architectural discipline applied to the Phase 404 PRF `overall_passed` field, and it mirrors gsd-2's broader server-recomputation pattern.

### Spot-check ↔ crash-recovery counter linkage

**Spot-check failure feeds the crash-recovery counter (SUB-07), not the PRF strike chain.** The three independent counters discipline (APG, PRF, DEV per DEVIATION-RULES.md Section 8) is preserved; the subagent restart counter is a fourth, parallel chain owned by this spec. Plan 04's EVENT-TAXONOMY.md amendment registers both `subagent_spot_check_failed` and `subagent_crash_detected` under the BUILD_ONLY_EVENT_PREFIXES — emission-wise distinct, but semantically wired: a layer-N spot-check failure on the same `(parent_task_id, subagent_type)` increments the restart counter via `state.step.subagent_crash_detected` with `crash_source='spot_check'`.

The four-counter independence rule reads: APG (Plan Guard), PRF (Proof Gate), DEV (Deviation Rules), and SUB (this spec's restart counter) each maintain a separate per-tuple state in the daemon's projectors. None of them increment another. This preserves the "no global escalation cascade" property — a Step that has accumulated 2 APG warnings and 2 PRF strikes and 2 DEV deferrals is not auto-escalated into Rule 4 just because the SUB counter ticks; each chain reaches its own terminal threshold independently.

### Module ownership

Single-source-of-truth module: `state_build/subagents/spot_check.py`. Exports: `run_spot_check_stack(complete_event: SubagentComplete) -> SpotCheckResult`. v14 implements; daemon middleware invokes on every `subagent_complete` event receipt.

`SpotCheckResult` is the Pydantic structure carrying the layer-by-layer verdicts plus the server-recomputed `overall_success`. v14 defines it during EXEMPLAR work; for v41 spec purposes the relevant fact is that the function signature takes a `SubagentComplete` (which is event-store authoritative) and returns a result that drives the next event (`subagent_spot_check_failed` if any layer failed, else the spot-check pass is recorded inline on the complete event projection).

### Spot-check determinism + idempotence

Re-running `run_spot_check_stack` against the same `SubagentComplete` event MUST produce the same result, modulo file-system mutation that happens between calls. The function is therefore deterministic per worktree-state but not pure (it reads the file system and git state). The harness invokes it exactly once per `subagent_complete` event at the daemon's projector tick; replay from the event store re-invokes against the worktree state at replay time, which is acceptable because the spot-check `failed_at` field is recorded on the original `SubagentSpotCheckFailed` event — replay does not regenerate timing claims, only verdict recomputation if v14's projector design allows it (deferred).

### Mode-isolation note

`state_build/subagents/` is a Build-mode package. Imports from `state_teach/` are forbidden by the cardinal mode-isolation rule (PROJECT.md). All eight new event types live under the `state.step.subagent_*` namespace, which Plan 04 will register inside `BUILD_ONLY_EVENT_PREFIXES` per EVENT-TAXONOMY.md. CI's import-graph lint catches any cross-mode import attempt at build time; the lint runs `python -m state.tools.import_lint --mode build` and fails on any `state_teach` reference inside `state_build/subagents/`.

### Layer-3 hash determinism note

Layer 3 (artifact existence) hashes the file at verification time. SHA-256 is the canonical algorithm — not MD5, not SHA-1, not BLAKE2. The reason is twofold: (1) SHA-256 is collision-resistant under adversarial conditions, which matters because a malicious or hallucinating subagent could otherwise emit a hash matching a benign file while the actual artifact differs; (2) SHA-256 is the same algorithm used by git's content-addressable-store (post-SHA-256 transition track), aligning state's hash discipline with git's. Hash computation runs on the file's full byte stream — no normalization, no whitespace trimming, no line-ending conversion. A subagent declaring a hash computed on normalized content while the actual file has different line endings will fail layer-3.



