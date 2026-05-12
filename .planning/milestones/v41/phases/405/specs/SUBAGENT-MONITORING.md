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




## 5-Source Crash Taxonomy + 3-Restart Counter (SUB-07)

A "crash" for SUB-07's 3-restart counter is any of five distinct sources. Each emits the same `SubagentCrashDetected` event payload with a `crash_source` Literal discriminator. The per-`(parent_task_id, subagent_type)` counter is the fourth independent chain (alongside APG / PRF / DEV).

The "five-source" framing is deliberate: state's monitoring surface unifies what gsd-2 split across three separate handlers (process-exit, stop-reason, and spot-check-style validation) into one event family with a discriminator, then adds two state-specific sources (`sse_silence` for liveness, `parent_task_error` for parent-side dispatch failures). One Pydantic payload + one event-type + one projector covers all five sources; the discriminator drives per-source remediation and per-source counter behavior.

### Five crash sources (markdown table)

| Source | Trigger |
|---|---|
| `process_exit` | child opencode `task` process `exit_code != 0` (gsd-2 isError) |
| `stop_reason` | last `message_end` event has `stop_reason ∈ {error, aborted}` (gsd-2) |
| `spot_check` | any spot-check layer (1-4 from Section 4) fails |
| `sse_silence` | no `subagent_progress` SSE event received for > `progress_timeout_s` (default 180s, configurable via Slice frontmatter `subagent: {progress_timeout_s: int}`) |
| `parent_task_error` | parent-side `task` MCP tool call returns error (provider HTTP failure, auth-refresh mid-call, mode-gate violation) |

The five sources are exhaustive for v1 — any subagent failure mode the harness can detect maps to one of them. v14 may add a `manual_abort` source post-v17 if user-initiated abort surfaces as a distinct concern, but the v1 contract assumes manual aborts route through DEV-04 Rule 4 (which terminates the Slice rather than incrementing the SUB counter).

### Pydantic event payload

```python
class SubagentCrashDetected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str
    parent_task_id: str
    subagent_type: SubagentType
    crash_source: Literal["process_exit","stop_reason","spot_check","sse_silence","parent_task_error"]
    restart_number: int                                  # 1..3; 4 triggers escalation
    evidence_excerpt: str                                # ≤2KB
    detected_at: datetime
    session_id: str
```

Event type: `state.step.subagent_crash_detected`. Registered by Plan 04.

The `restart_number` field's invariant is: `1..3` on `subagent_crash_detected` events; a value of `4` is impossible because the 4th detected crash event SHALL trigger emission of `subagent_restart_exhausted` instead. v14's projector enforces this at event-store write time — any attempt to emit a `subagent_crash_detected` with `restart_number=4` is rejected and surfaces as a Rule 4 escalation. The discipline keeps the counter chain auditable: a closed chain has exactly 3 `subagent_crash_detected` events (one per restart) followed by one `subagent_restart_exhausted` event, or fewer crash events followed by a `subagent_complete` event.

### Restart counter scope

**Per-`(parent_task_id, subagent_type)` tuple.** Diverges from per-`invocation_id` because the agent should not get a fresh 3-restart budget by re-invoking the same subagent type with a slightly different prompt for the same logical work unit. Mirrors Phase 404's per-`(task_id, check_id)` strike discipline.

The gaming surface this closes: without the per-tuple scope, an agent that observes the harness counting restarts by `invocation_id` could simply dispatch a new subagent of the same type with a slightly rephrased prompt after a crash, getting a fresh 3-strike budget for the same logical work. With the tuple scope, the counter accumulates regardless of prompt variations — the agent must succeed within 3 attempts at the work unit, not 3 attempts per prompt variant. The projector keys its counter dict on `f"{parent_task_id}|{subagent_type}"` (the pipe is a separator unambiguous against valid ulid characters).

### After-3-restart escalation

After 3 restarts on the same tuple, the parent agent MUST call `log_deviation` with `rule_id=3` (blocking issue) or `rule_id=4` (architectural — if the failure indicates a structural problem). The escalation event is `state.step.subagent_restart_exhausted` with payload:

```python
class SubagentRestartExhausted(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str                                   # most recent invocation
    parent_task_id: str
    subagent_type: SubagentType
    terminal_crash_source: Literal["process_exit","stop_reason","spot_check","sse_silence","parent_task_error"]
    triggered_at: datetime
    session_id: str
```

The harness emits this event AND surfaces the escalation prompt to the parent agent through opencode's TUI; the parent agent's next `log_deviation(rule_id=3|4)` call closes the chain. Cross-reference: DEVIATION-RULES.md Section 4 (cross-validation) accepts the elevated rule_id without re-promotion.

### Successful restart event

```python
class SubagentRestart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str                                   # NEW invocation id for the retry
    previous_invocation_id: str                          # the failed invocation
    parent_task_id: str
    subagent_type: SubagentType
    restart_number: int                                  # 1..3
    crash_source: Literal["process_exit","stop_reason","spot_check","sse_silence","parent_task_error"]
    triggered_at: datetime
    session_id: str                                      # new session for the retry
```

Event type: `state.step.subagent_restart`.

The two-ulid linkage (`invocation_id` for the retry + `previous_invocation_id` for the failed attempt) is what lets the projector reconstruct restart chains from event-store replay. A restart chain is a maximal sequence of invocations linked by `previous_invocation_id`; the chain head is the original `subagent_started` (no predecessor), the chain tail is either a `subagent_complete` (success) or a `subagent_restart_exhausted` (terminal failure).

## <prior_crash> Continuation Context

Restart prompts use an augmented original prompt with a `<prior_crash>` XML block. Mirrors Phase 402 reinject body XML discipline. **Diverges from gsd-2** — gsd-2's parallel-mode retry uses the original prompt verbatim; state's augmented form prevents looping on the same failure mode.

The decision rationale: gsd-2's verbatim-retry approach assumes the failure mode is transient (network blip, provider rate-limit, mid-call auth refresh). State's augmented-retry approach handles those transient failures equally well AND prevents systematic loops on persistent failure modes (e.g., a subagent that consistently writes to the wrong file path because it misread the prompt). The cost is a slightly larger restart prompt; the benefit is the agent has explicit evidence of the prior failure to course-correct from.

### XML structure (verbatim)

```xml
<prior_crash>
  <restart_number>2 of 3</restart_number>
  <crash_source>spot_check</crash_source>
  <prior_evidence>
    <!-- ≤2KB excerpt of failed stdout / spot-check failure detail -->
    Layer 3 (artifact_existence) failed: declared path
    `src/state_build/snapshot/compaction.py` does not exist; agent claimed
    to write but file is absent at SHA-256 verification.
  </prior_evidence>
  <remediation_hint>
    Verify file path against the worktree before declaring artifacts; ensure
    git add + commit landed before returning.
  </remediation_hint>
</prior_crash>

<original_task>
  <!-- verbatim original prompt -->
</original_task>
```

### remediation_hint sourcing

**`remediation_hint` is harness-default per `crash_source`** (single-source-of-truth lookup table `state_build/subagents/remediation_hints.py`). Planner MAY override per Slice frontmatter `subagent: {remediation_hints: dict[CrashSource, str]}` — narrowing-only NOT applicable here (hints are informational, not security gates). The default hint table covers all five `crash_source` values; v14 finalizes the exact default strings during EXEMPLAR work.

The hints are informational because the harness has no way to verify whether a subagent followed the hint; they shape the LLM's next-attempt behavior but are not gated. This is why narrowing-only doesn't apply: narrowing-only is the discipline for security-relevant Slice frontmatter overrides (e.g., a Slice cannot expand the parallel cap above the milestone default), but remediation hints can be tuned freely per Slice without exposing a bypass surface.

### Worktree-rollback over partial-artifact-preservation (v1)

**Partial-artifact preservation rejected for v1.** Worktree rollback on subagent restart is the simpler invariant: `declared_artifacts` that DID pass spot-check on the previous attempt are NOT preserved separately; the restarted subagent re-evaluates from scratch with the augmented prompt. Mirrors gsd-2's "fresh prompt on parallel-mode retry" + Phase 403's "replan recomputes from inputs" idempotency principle. Revisit post-v17 if observed restart cycles show systematic partial-success patterns.

The simpler invariant matters because v1's worktree discipline is per-Slice — every subagent in a Slice writes into the same worktree branch. A partial-artifact preservation scheme would require either (a) a per-invocation sub-worktree (defeats the per-Slice grouping), (b) selective git revert (introduces a class of edge cases where partial commits leave the branch in a non-replayable state), or (c) cherry-pick from the failed invocation's commits (re-introduces the prompt-emitted-claim surface that the spot-check is designed to close). Worktree rollback to the pre-invocation HEAD avoids all three traps.

### Module ownership

Single-source-of-truth: `state_build/subagents/restart.py` exports `build_restart_prompt(original_task: str, crash: SubagentCrashDetected) -> str`. v14 implements; the daemon-side restart handler invokes when emitting `state.step.subagent_restart` events. The XML block is constructed in-memory and injected into the new opencode session via the `task` tool's prompt argument.

## task_id Survival + Daemon-Down Orphan Reconciliation (SUB-08)

SUB-08 cross-references CTX-07 (Phase 402 identifier-survival contract). The subagent restart counter + in-flight subagent list survive compaction and Slice-boundary respawn via event-store rehydration. Daemon-down + orphan reconciliation extends the same pattern to daemon restart territory.

The combined identifier-survival + orphan-reconciliation discipline is what makes the subagent lifecycle robust across the three failure modes that matter most: (1) parent-session compaction (which truncates the parent's prompt window), (2) Slice-boundary respawn (which starts a fresh parent session for the next Slice), (3) daemon restart (which clears in-memory projector state). For each mode, the recovery path is "replay event-store"; the in-memory projectors are caches, never authoritative.

### CompactionSnapshot extension

```python
class CompactionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... existing fields from Phase 402 ...
    # Phase 405 additions:
    subagent_restart_counters: dict[str, int]            # key = "{parent_task_id}|{subagent_type}", value = restart count
    in_flight_subagents: list[InFlightSubagent]          # for Slice-boundary spawn
```

These two fields extend the Phase 402 `CompactionSnapshot` Pydantic model. Reinject payload carries them; daemon projector consumes on snapshot load.

### Slice-boundary spawn

The new session's `chat.params` metadata includes the prior counters; plugin's `chat.message` hook (or first `tool.execute.before` fire) writes them to plugin-local hot state via the daemon HTTP middleware. Cross-references CTX-07. The same projector pattern handles intra-Slice compaction reinject AND Slice-boundary respawn — both paths rehydrate from event-store.

### Subagent continuation on daemon restart

**Subagents continue independently** when daemon restarts mid-execution. Mirrors Phase 402's "in-flight subagents finish independently" decision for parent-compaction inheritance. Subagent processes are managed by opencode's `task` tool, not state-daemon; daemon restart doesn't kill them.

The architectural separation matters: opencode owns the subagent processes' lifecycles via its `task` tool; state-daemon is a sibling user-service that observes via SSE and records events. A daemon restart loses the daemon's in-memory projector state but does NOT terminate any running subagent. On daemon resume, the orphan reconciliation flow walks the event-store and reaches out to opencode's session API to reconcile what's still running with what the event log shows.

### Orphan reconciliation flow (numbered)

1. **Replay event-store** to rebuild `in_flight_subagents: dict[invocation_id, InFlightSubagent]` from any `state.step.subagent_started` event WITHOUT a paired `state.step.subagent_complete` / `state.step.subagent_crash_detected` event.
2. **Probe opencode** for each orphan: HTTP call to opencode's session API with the orphan's session_id / task_id; ask opencode whether the task is still running.
3. **If opencode reports still running** → re-subscribe to opencode SSE for that session; wait for natural completion event.
4. **If opencode reports done but no event was received** → reconstruct from opencode's session log (replay the session's recorded events); emit the missing `subagent_complete` event from the reconstruction.
5. **If opencode reports the task gone (lost)** → emit `state.step.subagent_orphan_detected` event (payload below) with `last_known_state="gone"`.
6. **Persistent orphan** (still unresolved after Slice-boundary spawn) → surface as DEV-04 Rule 4 human-gate via opencode `question` tool with the orphan details and a recovery alternatives payload pre-authored as `[abort_slice, retry_subagent, manual_resolve]`.

The six-step protocol is deterministic given the event-store + opencode's session API. Each step has a single, named outcome; there are no time-based escalations within the flow other than the SSE wait in step 3 (which is bounded by `progress_timeout_s`). The pre-authored alternatives in step 6 — `abort_slice`, `retry_subagent`, `manual_resolve` — exist so that the Rule 4 question surface in opencode's TUI presents a concrete decision rather than an open-ended prompt; this matches DEVIATION-RULES.md's Rule 4 always-stop contract.

### Pydantic event + in-flight payloads

```python
class SubagentOrphanDetected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str
    parent_task_id: str
    subagent_type: SubagentType
    last_known_state: Literal["running","unknown","gone"]
    detected_at: datetime

class InFlightSubagent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str
    parent_task_id: str
    subagent_type: SubagentType
    started_at: datetime
    last_progress_at: datetime | None
```

Event type: `state.step.subagent_orphan_detected`.

### HRN-07 guarantee preservation

Phase 406's HRN-07 "harness state fully reconstructable from event store" guarantee is preserved: every transition emits an event; replay rebuilds state. Daemon restart-safe via the rebuild path. The orphan reconciliation flow is part of the daemon resume handler; v14 implements at `state_build/subagents/orphan_reconcile.py`.

The HRN-07 invariant has a strict version in this spec's context: the projector state for `(in_flight_subagents, subagent_restart_counters, restart_chain_links)` is computable from the event-store alone, with `O(N)` time complexity where N is the number of `state.step.subagent_*` events in the relevant Slice window. v14's projector implementation MUST achieve this complexity; a quadratic implementation is rejected at code-review.

## Autonomy Inheritance from Parent Slice (SUB-09)

SUB-09 consumes DEVIATION-RULES.md's DEV-05 (tiered autonomy) + DEV-06 (per-Slice override). The parent Slice's effective autonomy propagates to every spawned subagent via the `dispatch_subagent` payload. The daemon middleware builds the opencode `task` tool invocation with the inherited autonomy injected into the child session's context.

The reason this matters: without inheritance, every subagent would default to the milestone-level autonomy regardless of Slice-level tuning. A Slice marked `--conservative` because it touches security-sensitive code would still spawn `--tiered` subagents that auto-approve human-verify checkpoints inside that Slice. With inheritance, the Slice's effective autonomy is the floor for every subagent it dispatches — and the per-dispatch override can move stricter OR looser per the explicit decision below.

### 3-step inheritance flow

1. **Parent's effective autonomy** = `Slice.frontmatter.autonomy ?? milestone.autonomy_default` (DEV-06 precedence rule from DEVIATION-RULES.md Section 6).
2. **Per-dispatch override** allowed: `DispatchSubagent.{single,parallel,chain}[i].autonomy: Literal["tiered","full-yolo","conservative"] | None`. If set, the child uses the override; if `None`, inherits the parent's effective autonomy. The override CAN move stricter (parent `--tiered`, child `--conservative`) OR looser (parent `--tiered`, child `--full-yolo`) — same direction-rule as DEV-06 Slice override (narrowing-only does NOT apply to autonomy; autonomy is policy not capability).
3. **Grandchild recursion**: a child subagent's `dispatch_subagent` calls (for grandchildren) recompute effective autonomy at their session boundary; grandchildren inherit from the child's effective autonomy, **not from the original parent**. Each session boundary applies the same `frontmatter ?? parent_effective` rule.

The grandchild rule means autonomy is a per-session computed property, not a transitive inherited one. A grandchild whose parent (the child) is `--conservative` and grandparent is `--full-yolo` runs as `--conservative` regardless of the grandparent's setting. This is necessary for predictable behavior: if a Slice's planner sets a child to `--conservative` to gate a sensitive sub-task, the planner's intent must not be defeated by a grandchild silently re-inheriting from the looser grandparent.

### Rule-4 always-stop preservation

**Rule 4 always-stop is preserved across inheritance.** Even if a grandchild's effective autonomy is `--full-yolo`, a `log_deviation(rule_id=4)` from the grandchild still synchronously renders opencode `question` (DEVIATION-RULES.md Section 2 structural-not-policy guarantee). Inheritance affects the autonomy mode's first three columns (human-verify / decision / human-action behaviors); the 4th column (Rule 4) is structural and cannot be inherited away.

### Implementation surface

When the daemon middleware builds the opencode `task` tool invocation, it injects the child's effective autonomy into the child session's environment via the `chat.params` hook (plugin-side context-block builder). The autonomy block is a structured `<autonomy>` XML annotation in the child's chat.params metadata; the plugin reads it on first `chat.message` fire and registers it with the daemon's autonomy projector. Mirrors gsd-2's `before-agent-start-context-assembly.md` block-builder shape — gsd-2 has no equivalent autonomy-inheritance block, so state's discipline is stricter.

### Module ownership

Single-source-of-truth: `state_build/subagents/autonomy.py` exports `compute_effective_autonomy(parent_effective, override) -> AutonomyMode`. v14 implements; daemon middleware invokes at `dispatch_subagent` time; plugin-side `chat.params` hook injects the result.

### Cross-reference to DEVIATION-RULES.md

Plan 01 of Phase 405 (DEVIATION-RULES.md) is the authoritative source for the tiered autonomy table (Section 6) and the per-Slice override mechanism (Section 6). This spec consumes that table verbatim; do not re-render it here. Forward-pointer to `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md` is the canonical citation.

### Mode-isolation note (re-affirmed)

`state_build/subagents/` MUST NOT import from `state_teach/`; the autonomy module, like all other modules in this spec, lives strictly in the Build subtree. Events emitted by this spec all live in BUILD_ONLY_EVENT_PREFIXES per EVENT-TAXONOMY.md. CI import-graph lint enforces.

## Appendix A — Event Stream Worked Example (illustrative)

A concrete worked example of an executor subagent dispatched, crashing once on `spot_check`, and succeeding on the first restart. All event payloads abbreviated for readability; the actual events carry the full Pydantic field sets defined above.

**Step 1: Dispatch**
```
state.step.subagent_started {
  invocation_id: "01HXXX...A",
  parent_task_id: "task-step-7",
  subagent_type: "executor",
  slice_id: "slice-42",
  ...
}
```

**Step 2: Progress (multiple events)**
```
state.step.subagent_progress { invocation_id: "01HXXX...A", kind: "tool_use_start", ... }
state.step.subagent_progress { invocation_id: "01HXXX...A", kind: "tool_use_end", ... }
state.step.subagent_progress { invocation_id: "01HXXX...A", kind: "message_end", ... }
```

**Step 3: Complete (with structured return)**
```
state.step.subagent_complete {
  invocation_id: "01HXXX...A",
  stop_reason: "end_turn",
  declared_artifacts: [{path: "src/x.py", sha256: "abc...", line_count: 42}],
  declared_commits: ["c0ffee1"],
  ...
}
```

**Step 4: Spot-check fails (artifact missing)**
```
state.step.subagent_spot_check_failed {
  invocation_id: "01HXXX...A",
  layer: "artifact",
  evidence_excerpt: "declared path src/x.py does not exist",
  ...
}
```

**Step 5: Crash detected (spot-check feeds crash counter)**
```
state.step.subagent_crash_detected {
  invocation_id: "01HXXX...A",
  crash_source: "spot_check",
  restart_number: 1,
  ...
}
```

**Step 6: Restart triggered**
```
state.step.subagent_restart {
  invocation_id: "01HXXX...B",          # new ulid
  previous_invocation_id: "01HXXX...A",
  restart_number: 1,
  crash_source: "spot_check",
  ...
}
```

**Step 7: Restarted subagent starts (with `<prior_crash>` block in prompt)**
```
state.step.subagent_started {
  invocation_id: "01HXXX...B",
  parent_task_id: "task-step-7",      # same parent
  subagent_type: "executor",
  ...
}
```

**Step 8: Restarted subagent completes successfully**
```
state.step.subagent_complete {
  invocation_id: "01HXXX...B",
  stop_reason: "end_turn",
  declared_artifacts: [{path: "src/x.py", sha256: "def...", line_count: 50}],
  declared_commits: ["c0ffee2"],
  ...
}
```

**Step 9: Spot-check passes** (no `subagent_spot_check_failed` event); the projector records the successful spot-check inline on the complete event's projection. The restart counter for `("task-step-7", "executor")` remains at 1 (not reset; success terminates the chain without resetting). A future `executor` dispatch for the same parent task that fails would start at `restart_number=2`.

## Appendix B — Cross-Reference Index

| Spec | Section | Cross-reference from this file |
|---|---|---|
| SUBAGENT-MANAGEMENT.md | §3 STAGE_ROSTER | Consumed by SUBAGENT_RETURN_REGISTRY (this file §3) |
| SUBAGENT-MANAGEMENT.md | §4 assert_never | Mirrored by compile-time exhaustiveness (this file §3) |
| DEVIATION-RULES.md | §2 Rule 4 structural | Preserved across autonomy inheritance (this file §8) |
| DEVIATION-RULES.md | §4 cross-validation | Accepts subagent_restart_exhausted rule_id (this file §5) |
| DEVIATION-RULES.md | §6 tiered autonomy | Consumed by SUB-09 inheritance flow (this file §8) |
| DEVIATION-RULES.md | §8 three-counter independence | Extended to four-counter (this file §4) |
| CONTEXT-PROTOCOL.md | §CTX-07 task_id survival | Cross-referenced by SUB-08 (this file §7) |
| CONTEXT-PROTOCOL.md | CompactionSnapshot | Extended with 2 new fields (this file §7) |
| PROOF-GATE.md | §7 StepVerifyResult overall_passed | Server-recomputation mirrored (this file §4) |
| STEP-PLAN-FORMAT.md | files_modified frontmatter | Cross-checked by ExecutorReturn (this file §3) |
| EVENT-TAXONOMY.md | BUILD_ONLY_EVENT_PREFIXES | Registers 8 new state.step.subagent_* events (Plan 04) |
| FRONTMATTER-SCHEMAS.md | extra="forbid" convention | Applied to all Pydantic models (this file, all sections) |

## Appendix C — Open Questions Deferred to v14 / v17

The following items are explicitly out of scope for v41 (this spec) and will be resolved during v14 (Build Kernel implementation) or post-v17 (production observation):

1. **Exact default `progress_timeout_s` value.** Spec stipulates 180s as a starter; v14 EXEMPLAR work may tune to 240s / 300s if false-positive `sse_silence` crashes emerge during exemplar Step execution. Tuning is per-Slice via frontmatter override, so the default can be revised without spec amendment.
2. **The 13 remaining per-type return subclasses.** This spec renders `ExecutorReturn` verbatim as an example; v14 authors the other 13 (`ResearcherReturn`, etc.) during EXEMPLAR work, one per stage roster entry. The shape is fixed by the inheritance pattern; the field set per subclass is the v14 design surface.
3. **Default `remediation_hint` strings per `crash_source`.** Spec stipulates `state_build/subagents/remediation_hints.py` as the lookup module; v14 authors the five default strings. Format is plain English, ≤200 chars per hint, addressed to the subagent's LLM.
4. **Layer-5 commit-tree hash spot-check.** Post-v17 consideration if observed commit-rewrite scenarios warrant adding a fifth layer that hashes the commit tree (not just verifies reachability). Out of scope for v1.
5. **Per-stage refinement of `SubagentProgress.kind`.** v14 may split `other` into named sub-kinds; v1 ships with the 5-value Literal as a conservative starter.
6. **Pre-authored alternatives for non-orphan Rule 4 escalations.** This spec pre-authors `[abort_slice, retry_subagent, manual_resolve]` for orphan reconciliation only; other Rule 4 escalations from SUB-* events (e.g., `subagent_restart_exhausted`) use the generic Rule-4 alternative set defined in DEVIATION-RULES.md.

## Appendix D — Versioning & Forward-Compatibility

The Pydantic models defined in this spec ship as v1 of the subagent-monitoring contract. Forward-compatibility rules:

- **Adding a new field** to any payload requires either (a) a default value (existing emitters remain valid) OR (b) bumping the contract version (v2) with a parallel registry. The `extra="forbid"` discipline means consumers reject unknown fields, so adding fields without defaults is a breaking change for legacy emitters.
- **Adding a new `SubagentType` Literal value** requires registering a corresponding `<Type>Return` subclass in the same commit (mypy strict check enforces).
- **Adding a new `crash_source` Literal value** requires updating the `SubagentCrashDetected` / `SubagentRestart` / `SubagentRestartExhausted` payloads AND the remediation_hints lookup table in the same commit.
- **Renaming a Literal value** is always a breaking change; bump contract version.
- **Removing a Literal value** is a breaking change; bump contract version.

The contract version is implicit in v1 (the spec's milestone tag is `v41`); v14 may introduce an explicit `contract_version: int` field on each payload if observed evolution warrants explicit versioning at the event level.

### Event-store migration discipline

Event-store rows are immutable; any contract change must support reading legacy rows during replay. The event-store schema carries an `event_version: str` column adjacent to the `event_type` column (per Phase 400 EVENT-TAXONOMY.md). Future contract bumps insert a new event-version-row pairing while leaving legacy rows readable via a per-version parser registered in `state_build/subagents/parsers.py` (v14 introduces this module if/when a v2 contract ships). The discipline ensures HRN-07 reconstructability holds across contract evolution — legacy events remain replayable into the current projector state shape.

### Subagent type addition checklist

When a new `SubagentType` Literal value is added (i.e., a new subagent class joins the roster), the contributor MUST land all five of the following in a single commit: (1) extend `SubagentType` Literal in SUBAGENT-MANAGEMENT.md `STAGE_ROSTER`; (2) author the `<Type>Return` Pydantic subclass in the appropriate `returns_{stage}.py` module; (3) register the subclass in `SUBAGENT_RETURN_REGISTRY`; (4) extend the discriminated-union `SubagentReturn` alias; (5) update the EXEMPLAR-stepNPLAN.md gate roster if the new type changes any stage's dispatch surface. CI's mypy strict check + the registry exhaustiveness assertion catch incomplete additions.

## Appendix E — Discovered Threats (executor append-only)

<!--
The runtime executor MAY append discovered threats here per PAP-05 carve-out.
This appendix is empty at authoring time.
Future entries follow the format:
- [severity] Threat description — Mitigation
-->

(empty at authoring time)
