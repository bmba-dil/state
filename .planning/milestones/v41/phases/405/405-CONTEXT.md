# Phase 405: Deviation Rules & Subagent Management — Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 405 produces two canonical specification documents:

1. **`DEVIATION-RULES.md`** — the 4-rule deviation framework (DEV-01..04), tiered autonomy (DEV-05) and per-Slice override (DEV-06), the `deviation` event payload (DEV-07), the `log_deviation` MCP tool surface with classification mechanism + Rule-4 cross-validation, the per-`(task_id, rule_id, issue_signature)` attempt counter (third independent counter alongside 404's APG and PRF chains), and the `## Deviations` SUMMARY section projector contract.

2. **`SUBAGENT-MANAGEMENT.md`** — the typed-spawn surface over opencode's `task` tool (SUB-01), the static whitelist per Slice stage with frontmatter narrowing-only override (SUB-02 + SUB-03), the 20-default parallel cap (SUB-04), the central Pydantic `SUBAGENT_RETURN_REGISTRY` and 4-layer spot-check protocol (SUB-06), the 5-source crash taxonomy + 3-restart counter with augmented continuation context (SUB-07), `task_id` survival across compaction and Slice-boundary respawn (SUB-08, cross-references CTX-07), and autonomy inheritance from parent Slice (SUB-09 + DEV-05/DEV-06).

Phase 405 is **design-only — no code lands.** Specs are implemented by v14 (Build Kernel) and v15 (Build Core Commands). Every check specified here is **pure-machine** (PRF-04 spirit carries forward); no LLM-as-judge anywhere in the deviation classifier, spot-check stack, or restart-counter accounting.

</domain>

<decisions>
## Implementation Decisions

### Naming discipline (project-wide)

**All new identifiers MUST be `STATE-*` or `state-*`, never `GSD-*`.** State is its own project; gsd-2 is the design heritage and is cited extensively, but trailer prefixes, event names, module paths, env vars, CLI commands, and file prefixes use state's identity, not gsd-2's. Phase 405 introduces:

- Commit trailers: `STATE-DeviationRule: N`, `STATE-DeviationAttempt: K`, `STATE-Subagent-Invocation: <invocation_id>`
- MCP tools: `log_deviation`, `dispatch_subagent` (under `state-build` MCP server)
- Events: `deviation_logged`, `deviation_classification_rejected`, `deviation_resolved`, `subagent_started`, `subagent_progress`, `subagent_complete`, `subagent_spot_check_failed`, `subagent_crash_detected`, `subagent_restart`, `subagent_orphan_detected`
- Modules: `state_build/deviation/`, `state_build/subagents/`

Phase 403 + 404 specs reference `GSD-Test-Result:`, `GSD-Task:`, `GSD-Gate-Strike:` trailers — these are renamed `STATE-TestResult:`, `STATE-Task:`, `STATE-GateStrike:` as part of the deferred rename pass (see `<deferred>`).

### Deviation classification (DEV-01..04 expanded)

**Routing: agent declares via `log_deviation` MCP tool + harness cross-validates.** Hybrid model mirrors gsd-2's defense-in-depth posture: agent self-structures intent via an explicit MCP tool-call boundary (same pattern as Phase 404's `request_step_split` and gsd-2's `complete_task` / `save-decision` at `db-writer.ts:428-430`); harness runs pure-machine validation against the proposed diff + file-path heuristics and rejects mismatches.

**`log_deviation` MCP tool signature:**

```python
def log_deviation(
    rule_id: Literal[1, 2, 3, 4],
    issue_signature: str,                                # caller computes; harness recomputes for verification
    classification_source: Literal[
        "agent_declared",                                # agent self-classified
        "harness_promoted",                              # auto-promoted by file-path heuristic
        "arch_pattern_match",                            # forced Rule 4 by allowlist match
    ],
    justification: str,                                  # ≤1KB agent rationale
    error_excerpt: str,                                  # ≤2KB; gsd-2 formatFailureContext truncation discipline
    alternatives: list[Rule4Option] | None = None,      # REQUIRED for rule_id=4; otherwise None
) -> DeviationLogResult: ...

class Rule4Option(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str                                            # short identifier shown in opencode question
    pros: str                                            # ≤512 chars
    cons: str                                            # ≤512 chars
    recommended: bool                                    # exactly one option in the list should be True

class DeviationLogResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deviation_event_id: str
    attempt_number: int                                  # 1..3 for rules 1-3; always 1 for rule 4
    cap_exceeded: bool                                   # True when this attempt is the 4th — auto-escalation triggered
    classification_accepted: bool                        # False if harness cross-validation rejected the declared rule_id
    rejection_reason: str | None                         # set when classification_accepted is False
```

**Harness cross-validation flow** (post-call, pre-event-emit):

1. **Re-compute `issue_signature`** from agent inputs and the current `(task_id, rule_id, error_kind, file:line, matched_token)` tuple. Reject if disagreement (`deviation_classification_rejected` event with `reason: "issue_signature_mismatch"`).
2. **Rule-4 alternatives check**: `rule_id == 4` and `alternatives is None or len(alternatives) < 2 or sum(o.recommended for o in alternatives) != 1` → reject.
3. **Rule-4 auto-promotion**: scan the agent's recent Write/Edit targets (from `tool.execute.before` event audit) against the arch-pattern allowlist (below). If `rule_id ∈ {1,2,3}` but a recent write hits the allowlist → reject the declared rule and emit a `deviation_classification_rejected` advisory; agent must re-call with `rule_id=4` and an `alternatives` payload.
4. **`scope_deviation_request` correlation**: if there's an open `scope_deviation_request` (Phase 404 SRP-04) for this `(task_id, requested_path)` AND the path matches arch-pattern allowlist, force `rule_id=4`.
5. **Cap check**: `SELECT count(*) FROM deviation_attempts WHERE (task_id, rule_id, issue_signature) = ?` ≥ 3 → `cap_exceeded=True`; auto-escalate per the rule's escalation path (Rule 3 → `checkpoint:decision`; Rules 1-2 → emit `deviation_cap_exceeded` and force Rule-4 promotion).

**Rule-4 detection (DEV-04, arch-pattern allowlist):**

```python
ARCH_PATTERN_ALLOWLIST: list[re.Pattern] = [
    re.compile(r"^alembic/(?!README)"),                          # any non-README path under alembic/
    re.compile(r"(?:^|/)migrations/[^/]+\.(py|sql)$"),
    re.compile(r"(?:^|/)schema\.(sql|prisma|graphql)$"),
    re.compile(r"^pyproject\.toml$|^uv\.lock$"),                # dep-list mutations (planner validates ADD vs BUMP)
    re.compile(r"^src/state_[a-z_]+/__init__\.py$"),            # new top-level package init creation
    re.compile(r"(?:^|/)mcp/tools/[^/]+\.py$"),                  # new MCP tool registrations
]
```

Path-match list mirrors 404's `READ_ONLY_PATTERNS` + `WRITE_SYSCALL_PATTERNS` single-module shape; lives at `state_build/deviation/arch_patterns.py` (mirrors 404 single-source-of-truth scope module convention and gsd-2's `branch-patterns.ts` shape). Match against the **proposed write target path** intercepted via `tool.execute.before`, not against existing on-disk content.

**ADD vs BUMP discrimination for `pyproject.toml` / `uv.lock`:**

- Pure-machine diff parse: lines beginning `+` matching `^\+\s*"[a-zA-Z0-9_\-]+>=`.match the ADD pattern.
- Lines matching `-\s*"X>=A.B"\s*\n\+\s*"X>=C.D"` (same package name, only version delta) match BUMP.
- ADD → arch-pattern match (force Rule 4). BUMP → no auto-promotion.

**Commit trailer convention (extends gsd-2's `COMMIT_TYPE_RULES`):**

State keeps gsd-2's 7-rule keyword-based type-inference table (`git-service.ts:616`, file-tracking.md:463) unchanged for the conventional-commit prefix selection. State adds two new trailers on top:

```
fix: resolve null-pointer in CompactionSnapshot.serialize

Restore the missing None-guard before orjson.dumps.

STATE-Task: 405-deviation-rules/step-2
STATE-DeviationRule: 1
STATE-DeviationAttempt: 1
```

`STATE-DeviationRule: N` (literal `N ∈ {1,2,3,4}`) and `STATE-DeviationAttempt: K` (literal `K ∈ {1,2,3}`) are mandatory on every commit produced as the resolution of an open deviation. Pure-machine grep target: auditors can `git log --grep="STATE-DeviationRule: 4"` to enumerate every architectural change ever made. Single-source-of-truth module: `state_build/commit/trailers.py` exports the trailer constants + the `infer_commit_type` function (adapted from gsd-2's `git-service.ts`).

### Attempt-counter semantics (DEV-07 expanded)

**Counter scope: per-`(task_id, rule_id, issue_signature)` tuple.** Mirrors 404's per-`(task_id, check_id)` PRF strike-chain discipline. Each unique deviation issue has its own 3-attempt chain. Chains for different `issue_signature` tuples do not poison each other.

**`issue_signature` derivation (pure-machine):**

```python
def compute_issue_signature(
    error_kind: ErrorKind,                               # enumerated Literal (below)
    file_path: str,                                      # repo-root-relative
    line_no: int,                                        # 1-indexed
    matched_token: str,                                  # the failing token / error head / scanner match
) -> str:
    # Canonicalize inputs deterministically
    canonical = f"{error_kind.value}|{file_path}|{line_no}|{matched_token}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

```python
class ErrorKind(str, Enum):
    pytest_failure = "pytest_failure"
    type_error = "type_error"                            # mypy / pyright
    import_error = "import_error"
    null_dereference = "null_dereference"
    schema_validation_failure = "schema_validation_failure"  # Pydantic validation
    scope_violation = "scope_violation"                  # 404 SRP-04 deviation request territory
    paralysis_threshold_cross = "paralysis_threshold_cross"  # 404 APG event-correlation
    proof_gate_failure = "proof_gate_failure"            # 404 PRF gate_strike correlation
    subagent_spot_check_failure = "subagent_spot_check_failure"
    other = "other"                                      # fallback; planner extends as new categories emerge
```

`error_kind` is an open-ended Literal; planner extends in v14 as new failure modes surface. **Whole-stack hashing is rejected** — OS/env differences make stack traces nondeterministic (research confirmed).

**Reset rule: on success of the same `(task_id, rule_id, issue_signature)` tuple.** When the next pure-machine eval of that exact tuple returns success (failing test now passes; type error gone; scanner clean), the counter for that tuple drops to 0. Different tuples never share state. Mirrors gsd-2's `consecutiveAllToolErrorTurns = 0`-on-success pattern (`agent-loop.ts:191`) AND 404's strike-chain-resets-on-success principle.

**Three-counter independence:** State now has three independent chains, each capable of independently reaching force-stop / human-gate:

| Chain | Per-tuple key | Trigger | Owner |
|---|---|---|---|
| APG `paralysis_event` | `(task_id,)` | N consecutive read-only operations | 404 |
| PRF `gate_strike` | `(task_id, check_id)` | Failed `must_haves.*` or `<verify>` at completion-claim | 404 |
| DEV `deviation_logged` | `(task_id, rule_id, issue_signature)` | `log_deviation` MCP call | 405 |

The umbrella `harness_intervention` event (HRN-05, owned by Phase 406) is the rollup; all three chains cite it as `trigger_reason`. Mirrors gsd-2 `loop-control.md` §0 Correction 1 (refusal to conflate four distinct counters at four scopes) — state's discipline matches.

**`deviation` event payload (DEV-07 expanded, Pydantic `extra="forbid"`):**

```python
class Deviation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deviation_event_id: str                              # ulid; primary key
    task_id: str
    step_id: str
    slice_id: str
    session_id: str
    rule_id: Literal[1, 2, 3, 4]
    issue_signature: str                                 # 16-char hex
    attempt_number: int                                  # 1..3 for Rules 1-3; always 1 for Rule 4
    classification_source: Literal[
        "agent_declared",
        "harness_promoted",
        "arch_pattern_match",
    ]
    commit_sha: str | None                               # the fix commit if any (set on resolution)
    resolution: Literal[
        "auto_fix_succeeded",
        "auto_fix_failed",
        "escalated_to_decision",
        "escalated_to_human_gate",
        "aborted_chain",
        "pending",                                       # initial state at log_deviation; resolution mutates later
    ]
    alternatives: list[Rule4Option] | None               # only populated for rule_id=4
    error_excerpt: str                                   # ≤2KB; gsd-2 truncation discipline
    agent_response_summary: str                          # ≤2KB
    triggered_at: datetime                               # UTC, ISO-8601
    intervention_event_id: str | None                    # cross-link to HRN-05 umbrella (Phase 406)
```

**Two-event vs single-event shape:** rejected the 404-style request/resolved pair. Single mutable event row (resolution starts `pending`, mutates on resolution). Diverges from 404's `scope_deviation_request` / `scope_deviation_resolved` two-event split because the deviation lifecycle is short-lived (≤3 attempts) and lives within one task boundary; a single row simplifies the `## Deviations` SUMMARY projector. The mutation is recorded as an append-only `deviation_resolution_recorded` event that updates the row by `deviation_event_id`; replay determinism preserved.

### Rule-4 always-human-gate semantics (DEV-04 + DEV-05 expanded)

**Even under `--full-yolo`, `rule_id=4` stops.** The autonomy table (DEV-05 literal) is:

| Mode | `checkpoint:human-verify` | `checkpoint:decision` | `checkpoint:human-action` | **Rule 4 deviation** |
|---|---|---|---|---|
| `--tiered` (default) | auto-approve | stop | stop | **stop** |
| `--full-yolo` | auto-approve | auto-pick option 1 | stop | **stop** |
| `--conservative` | stop | stop | stop | **stop** |

Implementation: the `log_deviation(rule_id=4, ...)` MCP handler synchronously renders opencode `question` tool with the `alternatives` payload — there is no autonomy short-circuit. The autonomy table's first three columns are inherited verbatim from Phase 403 task-type behaviors; the fourth column is novel to Phase 405.

**Per-Slice autonomy override (DEV-06):** Slice frontmatter `autonomy: Literal["tiered","full-yolo","conservative"]` (mirrors Phase 403 `autonomy is NOT a Step frontmatter field` decision — Slice-only). Precedence: **milestone default → Slice override → done.** No Step-level override (locked by Phase 403). Mirrors gsd-2's permissive-vs-strict trust-model divergence (`precedence-divergence-by-trust-model.md`). Slice override CAN move stricter (`--conservative` over milestone `--tiered`) AND CAN move looser (`--full-yolo` over milestone `--tiered`) — narrowing-only does NOT apply here (autonomy is policy, not capability; the SUB-03 narrowing-only rule is capability-only).

### `## Deviations` SUMMARY section projector (DEV-02 + DEV-07 expanded)

**Projector shape: subscribes to `deviation_logged` + `deviation_resolution_recorded`; writes to `stepNSUMMARY.md` `## Deviations` section.** Mirrors 404's `N-VERIFICATION.md` projector pattern + gsd-2's `db-writer.ts` projection discipline:

1. Subscribe to events filtered by `(step_id, slice_id)`.
2. Aggregate by `(rule_id, issue_signature)` — one row per unique issue.
3. Render markdown table with deterministic column order.
4. Atomic write via temp+rename (acknowledged as not-yet-atomic per Phase 402 §7.3 note for `last-snapshot.md`; same v44 follow-up applies).
5. Invalidate the read cache (mirrors gsd-2 `invalidateStateCache()` + `clearParseCache()` trio in `db-writer.ts`).

**Markdown column shape:**

| Column | Source | Notes |
|---|---|---|
| `#` | row ordinal | Stable across runs (sorted by first `triggered_at`) |
| `Rule` | `Deviation.rule_id` formatted as "Rule 1", "Rule 2", "Rule 3", "Rule 4" | |
| `Issue` | `Deviation.error_excerpt[:120]` | gsd-2 truncation, ≤120 char excerpt |
| `Source` | `Deviation.classification_source` | |
| `Attempts` | `max(attempt_number) / 3` | "2 / 3" form; for Rule 4 always "1 / 1" |
| `Resolution` | terminal `Deviation.resolution` | |
| `Commit` | `Deviation.commit_sha[:7]` | short SHA; "—" if pending |
| `When` | `Deviation.triggered_at` | ISO-8601 UTC |

Generated by deterministic projector at task-end (handler subscribes to `step_completed` events; aggregates all deviations for that step; renders the markdown). Lives at `state_build/projectors/deviation_summary.py`. The `## Deviations` section is appended to `stepNSUMMARY.md` when at least one deviation exists for that Step; omitted entirely when zero deviations.

### Subagent typed-spawn surface (SUB-01 + SUB-02 expanded)

**Single MCP tool `dispatch_subagent` wrapping opencode's `task` tool.** Three mutually-exclusive modes (mirrors gsd-2's `SubagentParams` at `subagent/index.ts:618-626`):

```python
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
    pass

class ChainDispatch(SingleDispatch):
    pass                                                 # chain mode uses `{previous}` text-substitution
                                                         # in the `task` field, populated from prior step output
```

Exactly-one-mode validation: a Pydantic root validator enforces exactly one of `single`/`parallel`/`chain` is set (mirrors gsd-2's mode resolution at `subagent/index.ts:709-720`).

**`SubagentType` Literal whitelist (mirrors SUB-02 verbatim):**

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

Lives at `state_build/subagents/types.py`. Exhaustiveness via `assert_never` in the dispatcher and the return-shape registry. Mirrors gsd-2's frontmatter-defined-agent-role pattern but uses Python typing (Literal) instead of TS `satisfies Record<K,V>` for compile-time exhaustiveness. Per-stage rosters (discuss / plan / execute / verify) materialized as a separate `STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]]` used by the whitelist enforcement layer.

### Static whitelist + narrowing-only override (SUB-03 expanded)

**Enforcement point: `tool.execute.before` on the `dispatch_subagent` MCP tool call.** Mirrors 404's layered tool.execute.before stack. Order:

1. Resolve current Slice stage via active task context (`(slice_id, current_stage)`).
2. Lookup `STAGE_ROSTER[current_stage]` → frozenset of allowed `SubagentType` values for this stage.
3. Read Slice frontmatter `allowed_subagents: list[SubagentType] | None` (per-Slice override).
4. Compute effective whitelist: `frontmatter ?? STAGE_ROSTER[current_stage]`; if frontmatter is supplied, verify `set(frontmatter) ⊆ STAGE_ROSTER[current_stage]` (narrowing-only); if frontmatter expands, reject the plan at plan-validation stage (NOT at runtime — narrowing-only validation happens during plan-slice's validation stage per Phase 403 pattern).
5. At runtime: for each (single/parallel/chain) entry, verify `entry.subagent_type ∈ effective_whitelist`. Mismatch → reject the dispatch call with `subagent_whitelist_violation` event (`expected: list[SubagentType], requested: SubagentType, stage: SliceStage`).

**Plan-time narrowing validation** lives in the planner's research-slice validation stage (Phase 403 `N-VALIDATION.md` machinery). The `allowed_subagents` Slice frontmatter field is validated against `STAGE_ROSTER` at plan-validation stage; expansion attempts fail `N-VALIDATION.md` and force a replan iteration. Mirrors Phase 403's `depends_on` cross-check pattern.

**Defense-in-depth pole:** state diverges from gsd-2's permissive runtime model (gsd-2 has no narrowing-only mechanism at plan time — `precedence-divergence-by-trust-model.md` pattern shows gsd-2 trusts the LLM to pick valid agent names at dispatch, with a synthetic-error fallback at `subagent/index.ts:344-358`). State validates both at plan-validation AND at runtime tool.execute.before — both gates pure-machine.

### Parallel cap accounting (SUB-04 expanded)

**Default cap: 20 concurrent subagent invocations per parent Slice session.** Diverges from gsd-2's `MAX_PARALLEL_TASKS=8` schema cap + `MAX_CONCURRENCY=4` runtime semaphore (`subagent/index.ts:42-43`). State's higher default reflects SUB-04's "subagents are free context" guidance and "aggressive fanout encouraged" framing.

**Enforcement: in-flight counter at daemon-side dispatch handler.** When `dispatch_subagent(mode="parallel", parallel=[...20+ entries])` is received, the handler queues entries beyond 20 (FIFO); slots free as `subagent_complete` or `subagent_crash_detected` events fire. Mirrors gsd-2's `pLimit(MAX_CONCURRENCY)` semaphore shape but at the daemon layer rather than per-tool-call.

**Per-Slice override:** Slice frontmatter `subagent: {parallel_cap: int}` may move the cap **stricter** only (narrow to 8 / 4 / 1); attempts to expand beyond 20 are rejected at plan-validation stage with `subagent_cap_expansion_rejected` event. Mirrors Phase 402's `compaction:` field narrowing-only pattern.

**Child-of-child accounting (grandchild fanout):** **rejected for v1.** Subagents are spawned in fresh opencode sessions; their own `task` tool invocations are managed by opencode, not state-daemon. State accounts only for direct children of the parent Slice session. If a child subagent itself dispatches more subagents (grandchildren), they count against the grandchild's session, not the parent's. Risk: `parallel_cap^2 = 400` worst-case process count if every child fans out 20 grandchildren. Documented as known limitation; revisit if real workloads show concurrency-storm patterns. Mirrors gsd-2's "no explicit guard at the grandchild level" framing.

**`subagent_started` event with `parent_task_id` records the parent linkage** (SUB-08); daemon projector maintains `in_flight_subagents: dict[parent_task_id, int]` rebuilt from event-store on boot.

### Structured return shape registry (SUB-06 expanded)

**Central Pydantic registry: `state_build/subagents/returns.py`.** Module exports:

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

# Exhaustiveness: assert_never(typing_unset_subagent_type) in the dispatcher
# guarantees every SubagentType has a registered return shape at type-check time.
```

Mirrors gsd-2's `exhaustive-registry-with-satisfies-constraint` pattern (TypeScript `satisfies Record<K,V>`) using Python typing's `assert_never` + Literal exhaustiveness. **Pydantic `extra="forbid"`** per model — agent-emitted aggregates are rejected at parse time.

**Common base class:**

```python
class ArtifactDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str                                            # repo-root-relative
    sha256: str                                          # full file content hash at write time
    line_count: int

class SubagentReturnBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subagent_type: SubagentType
    parent_task_id: str
    invocation_id: str                                   # ulid; the dispatch's unique ID
    declared_artifacts: list[ArtifactDeclaration]       # what the subagent claims to have written
    declared_commits: list[str]                          # commit SHAs in worktree branch order
    stop_reason: Literal["end_turn","tool_use","max_tokens","error","aborted"]
    error_message: str | None
```

**Per-type extension example (`ExecutorReturn`):**

```python
class ExecutorReturn(SubagentReturnBase):
    subagent_type: Literal["executor"]                   # narrowed Literal for type-discriminator
    files_modified_actual: list[str]                    # repo-root-relative; spot-check ⊆ frontmatter files_modified
    test_pass_count: int
    test_fail_count: int
```

Per-type models live in `state_build/subagents/returns_*.py` (one module per stage roster) and re-export to the registry. Mirrors gsd-2's per-agent role-definition pattern but with strict typing.

### Spot-check protocol (SUB-06 expanded)

**4-layer pure-machine stack, runs at `subagent_complete` event receipt:**

| Layer | Check | Failure trigger |
|---|---|---|
| 1. Process classification | `exit_code == 0 AND stop_reason ∉ {error, aborted}` | gsd-2 isError formula (`subagent/index.ts:923`) |
| 2. Pydantic validate | `SUBAGENT_RETURN_REGISTRY[type].model_validate_json(payload)` (`extra="forbid"`) | unknown fields, type mismatches, missing required fields |
| 3. Artifact existence | for every `ArtifactDeclaration`: file at `path` exists AND `sha256(file_bytes) == declaration.sha256` AND `count_lines(file) == declaration.line_count` | missing file / hash mismatch / line-count mismatch |
| 4. Commit existence | for every `commit_sha`: `git rev-parse --verify {sha}^{commit}` exits 0 AND commit is reachable from current worktree branch | missing commit / detached |

Any layer fails → `subagent_spot_check_failed` event:

```python
class SubagentSpotCheckFailed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: str
    parent_task_id: str
    subagent_type: SubagentType
    layer: Literal["process","pydantic","artifact","commit"]
    evidence_excerpt: str                                # ≤2KB; gsd-2 truncation
    failed_at: datetime
    session_id: str
```

**Server-side recomputation discipline:** the harness recomputes `overall_success` from layer verdicts; agent-emitted aggregates are rejected. Mirrors gsd-2's `server-recomputation-of-llm-emitted-fields.md` pattern + 404's PRF `overall_passed` recomputation.

**Spot-check failure feeds the crash-recovery counter (SUB-07), not the PRF strike chain.** The three independent counters discipline is preserved.

### Crash semantics (SUB-07 expanded)

**Crash taxonomy: 5-source union.** A "crash" for SUB-07's 3-restart counter is any of:

| Source | Trigger |
|---|---|
| `process_exit` | child opencode `task` process `exit_code != 0` (gsd-2 isError) |
| `stop_reason` | last `message_end` event has `stop_reason ∈ {error, aborted}` (gsd-2) |
| `spot_check` | any spot-check layer (1-4 above) fails |
| `sse_silence` | no `subagent_progress` SSE event received for > `progress_timeout_s` (default 180, configurable via Slice frontmatter `subagent: {progress_timeout_s: int}`) |
| `parent_task_error` | parent-side `task` MCP tool call returns error (provider HTTP failure, auth-refresh mid-call, mode-gate violation) |

Each emits:

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

**Restart counter scope: per-`(parent_task_id, subagent_type)`.** Diverges from per-invocation_id because the agent should not get a fresh 3-restart budget by re-invoking the same subagent type with a slightly different prompt for the same logical work unit. Mirrors 404's per-`(task_id, check_id)` strike discipline.

**After 3 restarts → escalation:** the parent agent must call `log_deviation` with `rule_id=3` (blocking issue) or `rule_id=4` (architectural — if the failure indicates a structural problem). The escalation event is `subagent_restart_exhausted` (`parent_task_id`, `subagent_type`, terminal `crash_source`).

### Continuation context on restart

**Augmented original prompt + `<prior_crash>` XML block.** Mirrors Phase 402's reinject body XML discipline. Restart prompt structure:

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

**`remediation_hint` is harness-default per `crash_source`** (single source-of-truth lookup table `state_build/subagents/remediation_hints.py`). Planner MAY override per Slice frontmatter `subagent: {remediation_hints: dict[CrashSource, str]}` — narrowing-only NOT applicable here (hints are informational, not security gates).

**Partial-artifact preservation rejected for v1.** Worktree rollback on subagent restart is the simpler invariant: declared_artifacts that DID pass spot-check on the previous attempt are NOT preserved separately; the restarted subagent re-evaluates from scratch with the augmented prompt. Mirrors gsd-2's "fresh prompt on parallel-mode retry" + Phase 403's "replan recomputes from inputs" idempotency principle. Revisit post-v17 if observed restart cycles show systematic partial-success patterns.

### Counter survival across compaction + Slice-boundary respawn (SUB-08 expanded)

**Event-store authoritative + daemon projector rehydration.** Cross-references CTX-07 (identifier-survival contract from Phase 402).

**Daemon projector:** maintains `subagent_restart_counters: dict[(parent_task_id, SubagentType), int]` in-memory; rebuilt on boot via event-store replay (mirrors v6 daemon crash-recovery pattern).

**Compaction snapshot extension (extends Phase 402 `CompactionSnapshot`):**

```python
class CompactionSnapshot(BaseModel):
    # ... existing fields from Phase 402 ...
    subagent_restart_counters: dict[str, int]            # key = "{parent_task_id}|{subagent_type}", value = restart count
    in_flight_subagents: list[InFlightSubagent]         # for Slice-boundary spawn — see daemon-down section
```

**Slice-boundary spawn:** the new session's `chat.params` metadata includes the prior counters; plugin's `chat.message` hook (or first `tool.execute.before` fire) writes them to plugin-local hot state via the daemon HTTP middleware. Cross-references CTX-07.

### Daemon-down + in-flight subagent reconciliation

**Subagents continue independently** when daemon restarts mid-execution. Mirrors Phase 402's "in-flight subagents finish independently" decision for parent-compaction inheritance. Subagent processes are managed by opencode's `task` tool, not state-daemon; daemon restart doesn't kill them.

**Orphan reconciliation flow** (on daemon resume):

1. Replay event-store to rebuild `in_flight_subagents: dict[invocation_id, InFlightSubagent]` from any `subagent_started` event WITHOUT a paired `subagent_complete` / `subagent_crash_detected` event.
2. For each orphan: probe opencode's `task` tool status (HTTP call to opencode session API with the orphan's `task_id`).
3. If opencode reports the task still running → wait for natural completion (re-subscribe to SSE).
4. If opencode reports the task done but no event was received → reconstruct from opencode's session log (replay).
5. If opencode reports the task gone (lost) → emit `subagent_orphan_detected` event (`invocation_id`, `parent_task_id`, `subagent_type`, last-known-state).
6. Persistent orphan (still unresolved after Slice-boundary spawn) → surface as DEV-04 Rule 4 human-gate via opencode `question` tool with the orphan details and a recovery alternatives payload.

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

HRN-07's "harness state fully reconstructable from event store" guarantee is preserved: every transition emits an event; replay rebuilds state.

### Autonomy inheritance (SUB-09 expanded)

**Parent Slice's `autonomy` propagates to every spawned subagent via `dispatch_subagent` payload.** When the daemon middleware builds the opencode `task` tool invocation, it injects the parent's effective autonomy into the child session's environment:

1. Parent's effective autonomy = `Slice.frontmatter.autonomy ?? milestone.autonomy`.
2. Per-dispatch override allowed: `DispatchSubagent.{single,parallel,chain}[i].autonomy: Literal | None`. If set, the child uses the override; if None, inherits parent's effective autonomy. The override CAN move stricter (parent `--tiered`, child `--conservative`) OR looser (parent `--tiered`, child `--full-yolo`) — same as DEV-06 Slice override.
3. Child subagent's `dispatch_subagent` calls (for grandchildren) recompute effective autonomy at their session boundary; grandchildren inherit from the child's effective autonomy, not from the original parent.

Mirrors gsd-2's `before-agent-start-context-assembly.md` block-builder shape but with autonomy as an explicit context block (gsd-2 has no equivalent — state's discipline is stricter).

### Claude's Discretion

- `ErrorKind` enum completeness — recommended starter set above; planner extends in v14 as new failure modes surface (e.g., `oauth_refresh_failure`, `worktree_checkout_failure`).
- `file_path` canonicalization edge cases — recommended repo-root-relative POSIX form (forward slashes always); planner pins exact `os.path.relpath` vs `pathlib.PurePosixPath.relative_to` strategy.
- `matched_token` extraction rule when the error has no clear token — recommended fall back to first-line-of-error-message-truncated-to-64-chars; planner finalizes.
- Exact wording of advisory messages for `deviation_classification_rejected`, `subagent_whitelist_violation`, `subagent_spot_check_failed`, `subagent_crash_detected`, `subagent_orphan_detected` (recommended: include the failing layer/source, the parent context, the specific remediation hint).
- `progress_timeout_s` default (recommended 180s; planner may tune to 120/240 after EXEMPLAR-stepNPLAN.md gates).
- `infer_commit_type` keyword extension list — recommended gsd-2 verbatim; planner may extend with state-specific keywords (e.g., `harness` → `feat`, `gate` → `feat`, `event-replay` → `refactor`) based on observed commit corpus.
- Whether to expose `--deviation-rule-ids` CLI override for log_deviation rule_id list — recommended: no, lock to literal {1,2,3,4}; revisit post-v17.
- ADD-vs-BUMP regex completeness — recommended starter set above; planner pins multi-line YAML/TOML edge cases.
- Whether `subagent_orphan_detected` Rule-4 escalation pre-authors the alternatives or asks the agent on resume (recommended: harness pre-authors `[abort_slice, retry_subagent, manual_resolve]`).
- Per-stage roster boundaries when a `subagent_type` could plausibly serve two stages (e.g., `researcher` in both discuss-slice and plan-slice rosters per SUB-02) — recommended: list in both stages; runtime stage gates determine which roster applies.
- The exact opencode `task` tool wrapper structure inside `dispatch_subagent` MCP handler — gsd-2's CLI-arg-marshaling shape (`subagent/index.ts:264-277`) is the substrate; planner pins state's daemon-side equivalent.
- `SubagentReturnBase` per-stage extensions beyond the executor example — recommended: each stage roster's per-type subclasses live in `state_build/subagents/returns_{stage}.py`; planner authors the 13 remaining models during v14.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 405 scope & requirements
- `.planning/milestones/v41/ROADMAP.md` §Phase 405 — goal, dependencies (Phase 404), success criteria 1–5.
- `.planning/milestones/v41/REQUIREMENTS.md` — DEV-01..DEV-07 + SUB-01..SUB-09.
- `.planning/milestones/v41/HANDOFF.md` §6 (deviation rules framework), §7 (subagent management), §3 (plan-as-prompt — Rule 4 question tool context).

### Phase 402 + 403 + 404 prior decisions (carry forward — do NOT revisit)
- `.planning/milestones/v41/phases/402/402-CONTEXT.md` — `tool.execute.before` as canonical block hook, plugin-as-thin-reporter, Pydantic `extra="forbid"` convention, event-sourced + SQLite authoritative, `CompactionSnapshot` Pydantic model extends here, subagent-compaction-inheritance ("in-flight subagents finish independently"), reactive overflow recovery (CTX-09).
- `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — reinject payload XML shape; `<active_plan>`/`<upstream_provides>`/`<current_task_pointer>` slots — Phase 405's `<prior_crash>` block reuses the same XML discipline.
- `.planning/milestones/v41/phases/403/403-CONTEXT.md` — `<options>` sub-tag shape (Rule 4 alternatives reuses this verbatim), `autonomy` Slice frontmatter axis (DEV-06 inherits), `tool.execute.before` diff-the-proposed-write enforcement (Rule-4 arch-pattern allowlist applies here), `must_haves.{truths, artifacts, key_links}` schema (ArtifactDeclaration mirrors `ArtifactCheck` shape), `step_id` stable hash convention, content-stripping at injection time (subagent restart prompt is similarly stripped).
- `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` + `EXEMPLAR-stepNPLAN.md` — frontmatter schema (`allowed_subagents`, `autonomy`, `subagent` field nest are new Phase 405 additions); `auto+tdd` RED-before-GREEN protocol; checkpoint:decision `<options>` shape.
- `.planning/milestones/v41/phases/404/404-CONTEXT.md` — per-`(task_id, check_id)` PRF strike-chain discipline (Phase 405's deviation counter mirrors this tuple shape), APG-vs-PRF counter independence (Phase 405's deviation counter is the third independent chain), 6-strike escalation ladder (Phase 405 extends but does NOT inherit — deviation chain is 3-attempt not 6-strike), `scope_deviation_request` (Phase 404 SRP-04) routing to `checkpoint:decision` — Phase 405's `log_deviation` reuses this checkpoint integration for Rules 3/4, single-source-of-truth module convention (`state_build/harness/scope/` mirrored by `state_build/deviation/` + `state_build/subagents/`), bounded truncation 2KB/10KB discipline, server-side recomputation of `overall_passed` (Phase 405 spot-check applies same).
- `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` (when shipped) — `gate_strike` event payload + `StepVerifyResult` Pydantic shape are precedents for Phase 405's `Deviation` + `SubagentSpotCheckFailed` event payloads.
- `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` (when shipped) — `scope_deviation_request` MCP shape Phase 405 extends with `log_deviation`.

### gsd-2 reference patterns (cited inline above)
- `~/projects/gsd2deconstruction/kb/workflow/loop-control.md` §0 Correction 1 — four distinct counters at four scopes (`MAX_CONSECUTIVE_VALIDATION_FAILURES`, tool-call-loop-guard, error-classifier, doctor-proactive); refuses to conflate. Phase 405's deviation counter is the third state-side independent chain (alongside Phase 404's APG and PRF).
- `~/projects/gsd2deconstruction/kb/workflow/loop-control.md` §6 — sliding-window-with-ledger-suppression 4-rule shape; informs state's discipline of separating detection mechanism from cap enforcement.
- `~/projects/gsd2deconstruction/kb/workflow/quality-enforcement.md` — bucketed gate registries pattern; informs `STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]]` shape.
- `~/projects/gsd2deconstruction/kb/workflow/prompt-templates.md` — `## Deviations` SUMMARY section reference (gsd-2 doesn't have one; state synthesizes from gsd-2's `db-writer.ts` projection pattern).
- `~/projects/gsd2deconstruction/kb/walkthroughs/orchestrator.ts.md` §5.5 + §7.1 — post-dispatch hook shape for deviation projector; `RecoveryAdapter.classifyAndRecover` discriminated action discipline.
- `~/projects/gsd2deconstruction/kb/walkthroughs/db-writer.ts.md` §1, §2, §6, §10, §12 — markdown projection pattern (atomic write-temp-rename, freeform-prose-preservation, cache invalidation trio) state's `## Deviations` projector replicates.
- `~/projects/gsd2deconstruction/kb/walkthroughs/gsd-db.ts.md` — event schema / read side; informs state's `deviation_attempts` SQLite shape (though state's primary store is the event-store row, not a separate table).
- `~/projects/gsd2deconstruction/kb/agents/agent-roles.md` §1.1, §3.2, §4.2, §4.4 — agent frontmatter shape, process isolation properties, `isError` formula, per-mode failure handling (single/parallel/chain).
- `~/projects/gsd2deconstruction/kb/patterns/dispatch-rules-table.md` — first-match-wins ordered array pattern; informs state's `ARCH_PATTERN_ALLOWLIST` and per-stage roster lookup.
- `~/projects/gsd2deconstruction/kb/patterns/precedence-divergence-by-trust-model.md` — narrowing-only override semantics (state diverges: narrowing-only for capability, not for autonomy policy).
- `~/projects/gsd2deconstruction/kb/patterns/llm-mediated-trigger-table.md` — trigger-table shape (state rejects LLM-mediated triggers; agent declaration via MCP tool boundary is pure-machine downstream).
- `~/projects/gsd2deconstruction/kb/patterns/derived-state-from-db-decision-tree.md` — phase-as-function discipline; informs state's "effective autonomy" derivation as `Slice.autonomy ?? milestone.autonomy`.
- `~/projects/gsd2deconstruction/kb/patterns/sliding-window-with-ledger-suppression.md` — Rule 2 suppression via retry budget; informs state's reset-on-success counter discipline.
- `~/projects/gsd2deconstruction/kb/patterns/exhaustive-registry-with-satisfies-constraint.md` — TypeScript `satisfies Record<K,V>` pattern; state's Python analog is `Literal` union + `assert_never` + Pydantic registry.
- `~/projects/gsd2deconstruction/kb/patterns/server-recomputation-of-llm-emitted-fields.md` — defensive recomputation of LLM-emitted aggregates; state's spot-check `overall_success` follows this pattern.
- `~/projects/gsd2deconstruction/kb/patterns/process-exit-stop-reason-validation.md` — 3-signal classification pattern (`exitCode`, `stopReason`, `errorMessage`); state extends to 5-source crash taxonomy.
- `~/projects/gsd2deconstruction/kb/patterns/db-driven-crash-recovery.md` — parent-level crash recovery via DB replay; state extends to per-subagent counter rehydration on daemon resume.
- `~/projects/gsd2deconstruction/kb/patterns/parallel-reviewer-fan-out.md` + `~/projects/gsd2deconstruction/kb/patterns/subprocess-isolated-subagent-dispatch.md` — typed-spawn pattern foundation; state's 20-cap diverges from gsd-2's 8/4.
- `~/projects/gsd2deconstruction/kb/patterns/before-agent-start-context-assembly.md` — context block builders; state's autonomy-inheritance context block extends.
- `~/projects/gsd2deconstruction/kb/patterns/three-layer-llm-orchestration.md` — parent/child/grandchild discipline; informs state's "grandchild counts against grandchild's session, not parent's" decision.
- `~/projects/gsd2deconstruction/kb/patterns/nested-loop-budget-isolation.md` — child budget isolation under parent cap; state's parallel cap is per-Slice-session, not rolled-up.
- `~/projects/gsd2deconstruction/kb/patterns/async-local-storage-turn-epoch.md` — ALS for in-process correlation (does NOT cross process boundaries); informs state's choice to use event-store rows for cross-process `parent_task_id` propagation.
- `~/projects/gsd2deconstruction/kb/core/agent-lifecycle.md` §2.2 — `agent.sessionId = sessionManager.getSessionId()` invariant; state's `parent_task_id` is the equivalent stable identifier.
- `~/projects/gsd2deconstruction/kb/core/tool-system.md` §5 — Task tool / typed-spawn definition; state's `dispatch_subagent` MCP wraps opencode's `task` tool with state-specific validation.
- `~/projects/gsd2deconstruction/kb/core/communication-map.md` §2.5 — Subagent Boundary (the inter-process path); state mirrors the JSON-event protocol (`message_end`, `tool_result_end`).
- `~/projects/gsd2deconstruction/kb/app/session-manager.md` — task_id survival across context resets via JSONL header; state's analog is event-store row + projector replay.
- `~/projects/gsd2deconstruction/kb/extensions/plugin-system.md` — extension surface for spawn; state's `dispatch_subagent` MCP tool registers under state-build MCP server (which is the plugin's MCP surface).
- `~/projects/gsd2deconstruction/kb/cross-layer-communication-map.md` — Bus A + Bus B event topology; state's daemon-mediated dispatch lives on the equivalent of Bus A (tool-call bus).
- `~/projects/gsd2deconstruction/kb/INDEX.md` + `~/projects/gsd2deconstruction/kb/patterns/INDEX.md` — orientation; cited for breadth completeness.

### Phase 400 + 401 prior decisions (v40)
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — existing event taxonomy. Phase 405 adds: `deviation_logged`, `deviation_classification_rejected`, `deviation_resolution_recorded`, `subagent_started`, `subagent_progress`, `subagent_complete`, `subagent_spot_check_failed`, `subagent_crash_detected`, `subagent_restart`, `subagent_restart_exhausted`, `subagent_orphan_detected`, `subagent_whitelist_violation`, `deviation_cap_exceeded`, `subagent_cap_expansion_rejected`.
- `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — Pydantic frontmatter convention; Slice frontmatter gains `autonomy`, `allowed_subagents`, `subagent: {parallel_cap, progress_timeout_s, remediation_hints}` nested fields.
- `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — adds `state_build/subagents/returns.py` + `state_build/deviation/arch_patterns.py` to the canonical lineage layout; `stepNSUMMARY.md` gains a `## Deviations` section (projector-generated).

### Project-level constraints
- `.planning/PROJECT.md` — Build/Teach exclusivity (Phase 405 specs Build-only); Python 3.12+; opencode primary host.
- `CLAUDE.md` (project) — per-plan SUMMARY.md mandatory, security_enforcement=true, mode isolation cardinal rule (Phase 405 spec lives under `state_build/` lineage; must not bleed into `state_teach/`).

### Architecture & integration (shipped, reference only — Phase 405 is design-only)
- `src/state_core/schema.py` — existing event Pydantic models; new event types extend the same `EventEnvelope` convention.
- `src/state_worker/hooks/` — `tool.execute.before` handler. Phase 405's deviation classifier cross-validation, subagent whitelist enforcement, and parallel-cap accounting all stack inside this hook in deterministic order alongside Phase 403/404 enforcement layers.
- `src/state_daemon/middleware.py` — daemon decides; the deviation attempt counter + subagent restart counter + in-flight subagent counter state lives here.
- `state-inputs/opencode/packages/plugin/src/index.ts` — opencode `task` tool wrapper, `question` tool for Rule 4 human-gate (HRN-06), hook signatures.

### Downstream consumers (these will read Phase 405 output)
- **v14 Build Kernel** — implements `log_deviation` MCP tool, `dispatch_subagent` MCP tool, the deviation attempt-counter projector, the arch-pattern allowlist module, the `SUBAGENT_RETURN_REGISTRY` and 4-layer spot-check, the 5-source crash taxonomy + restart-counter projector, the orphan reconciliation flow, the `## Deviations` SUMMARY projector, the `infer_commit_type` + STATE-* trailer module.
- **v15 Build Core Commands** — implements the research-slice validation stage that checks `allowed_subagents` narrowing-only against `STAGE_ROSTER`; the verify-slice stage that includes per-Step `## Deviations` SUMMARY section assembly.
- **Phase 406 (Harness Architecture Rollup)** — `harness_intervention` event umbrella aggregates `deviation_logged` (Rule 4 escalations specifically), `subagent_spot_check_failed`, `subagent_crash_detected`, `subagent_orphan_detected`; 4-tier intervention ladder (HRN-04) cites Phase 405 escalation paths; MCP tool catalog (HRN-03) enumerates `log_deviation` and `dispatch_subagent`; layered diagram shows the `tool.execute.before` write-block stack now extended with Phase 405's deviation classifier and subagent whitelist gates in order.

</canonical_refs>

<specifics>
## Specific Ideas

- **gsd-2's refusal to conflate counters is load-bearing for state.** Phase 404 established APG vs PRF counter independence; Phase 405 adds the third independent chain (deviation_attempt) and the fourth via the subagent restart counter. Each can independently reach force-stop/human-gate; conflating any pair would directly violate gsd-2 `loop-control.md` §0 Correction 1.

- **MCP-tool-call boundary is the canonical agent-intent signal.** gsd-2's pattern across `complete_task` / `complete_slice` / `validate_milestone` / `save-decision` is consistent: agent intent is signaled by tool call, never by NL output scan. Phase 404's `request_step_split` follows. Phase 405's `log_deviation` + `dispatch_subagent` follow. NL keyword detection for rule classification was offered and rejected.

- **Defense-in-depth: agent declares + harness validates.** gsd-2's `db-writer.ts` `save-decision` accepts permissive input; state diverges with strict Pydantic + cross-validation. The cross-validation principle: agent self-classifies (cheap, semantically aware), harness verifies against pure-machine signals (commit-diff inspection, file-path heuristics, scope_deviation_request correlation). Mismatch → reject + re-prompt. Mirrors 404's diff-the-proposed-write pattern.

- **`STATE-DeviationRule:` / `STATE-DeviationAttempt:` trailers, NOT `GSD-*`.** Naming discipline pin: state is its own project. Past phases (403, 404) drifted into `GSD-Test-Result:` / `GSD-Task:` / `GSD-Gate-Strike:` references that need a rename pass (logged in deferred). All Phase 405 specs use `STATE-*`.

- **Rule 4 always-stop is the autonomy table's 4th column.** Diverges from the 3-column REQUIREMENTS literal for DEV-05 (`human-verify`/`decision`/`human-action`); Phase 405 adds the deviation column. Even `--full-yolo` cannot override Rule 4. The implementation is structural (Rule 4 path doesn't consult the autonomy mode), not policy (no "if mode == 'full-yolo' bypass" branch exists).

- **Per-`(task_id, rule_id, issue_signature)` chain is the minimum-spec tuple.** Wider scopes (Step-level, Slice-level) risk cross-task chain poisoning; narrower scopes (per-invocation_id) let the agent game by re-invoking with different prompts. Mirrors 404's per-`(task_id, check_id)` PRF strike discipline exactly.

- **Reset-on-success preserves audit clarity AND chain interpretability.** gsd-2's `consecutiveAllToolErrorTurns = 0`-on-success pattern. The same `(task_id, rule_id, issue_signature)` succeeding signals "this issue is resolved"; the counter dropping to 0 lets a future regression of the SAME issue start fresh chain — distinguishable from "this issue has been retried 3 times and failed."

- **20-parallel cap diverges from gsd-2's 8/4 for principled reasons.** gsd-2's caps are tuned for the SubagentParams tool's specific dispatch shape; state's 20 reflects SUB-04's "subagents are free context, aggressive fanout encouraged" framing and the higher per-Slice subagent diversity (14 named types across 4 rosters). Per-Slice narrowing to lower caps is allowed; expansion above 20 is not.

- **Compile-time exhaustiveness via Python `Literal` + `assert_never`.** Diverges from gsd-2's runtime-discovery-with-synthetic-error-fallback pattern (`subagent/index.ts:344-358`). State's stricter validation pole: missing `SubagentType` entry in the registry fails at type-check time (mypy/pyright caught), not at runtime. Mirrors gsd-2's `exhaustive-registry-with-satisfies-constraint.md` pattern with Python idioms.

- **Spot-check layered stack mirrors 404's tool.execute.before composition.** Deterministic order (process → Pydantic → artifact → commit); each layer pure-machine; any layer fail → distinct `layer` field in the event payload. Mirrors gsd-2's `process-exit-stop-reason-validation.md` 3-signal pattern extended with state-specific artifact + commit gates.

- **Augmented restart prompt (not fresh) diverges from gsd-2.** gsd-2's parallel-mode retry uses the original prompt verbatim. Phase 405 adds `<prior_crash>` XML context (mirrors 402 reinject body discipline) so the restarted subagent doesn't loop on the same failure mode. The decision is partly motivated by SUB-07's literal "continuation context" wording; partly by observed effectiveness in 402's reinject pattern.

- **Worktree-rollback over partial-artifact-preservation for v1.** Idempotency wins. Partial preservation is a future optimization; the v1 invariant is "restarted subagent starts fresh from the parent's worktree commit, augmented prompt notwithstanding."

- **Subagents continue independently on daemon restart.** Phase 402 established this pattern for compaction; Phase 405 extends to daemon-restart territory. Orphan reconciliation via event-store replay + opencode probe is the recovery path; persistent orphans escalate to Rule 4 (human resolution).

- **Per-stage roster materialized as `frozenset[SubagentType]`.** Pure-machine subset check (`set(frontmatter) ⊆ STAGE_ROSTER[stage]`). gsd-2's discipline of computing-derived-state-as-function (`derived-state-from-db-decision-tree.md`) applies: `effective_whitelist = frontmatter ?? STAGE_ROSTER[current_stage]` is a function of current state, not stored state.

</specifics>

<code_context>
## Existing Code Insights

### Reference only (Phase 405 is design-only — no code lands)

Phase 405 produces architecture specification documents. Shipped code below is reference for understanding existing patterns and integration points the spec must respect; v14 implements per these specs.

### Reusable Assets

- `state_core.schema` — `EventEnvelope`, `extra="forbid"` Pydantic convention. New event Pydantic models (`Deviation`, `DeviationClassificationRejected`, `DeviationResolutionRecorded`, `SubagentStarted`, `SubagentProgress`, `SubagentComplete`, `SubagentSpotCheckFailed`, `SubagentCrashDetected`, `SubagentRestart`, `SubagentRestartExhausted`, `SubagentOrphanDetected`, `SubagentWhitelistViolation`, `DeviationCapExceeded`, `SubagentCapExpansionRejected`) extend this.
- `state_core.projector` — CQRS handler registration pattern. The `## Deviations` SUMMARY projector subscribes to `deviation_logged` + `deviation_resolution_recorded`; the daemon's `subagent_restart_counters` projector subscribes to `subagent_crash_detected`; the daemon's `in_flight_subagents` projector subscribes to `subagent_started` + `subagent_complete` + `subagent_crash_detected`.
- `state_worker.hooks` (v7) — `tool.execute.before` is the canonical stack. Phase 405 layers added in deterministic order: (1) Phase 403 immutability check → (2) Phase 404 files_modified allowlist → (3) Phase 404 prohibited-language scan → (4) Phase 405 `log_deviation` MCP routing + deviation-classifier cross-validation → (5) Phase 405 `dispatch_subagent` MCP routing + whitelist enforcement + parallel-cap accounting → (6) Phase 405 arch-pattern allowlist match for Rule 4 auto-promotion → (7) Phase 404 `<discovered_threats>` append-only carve-out → allow. Order is significant: cheap (regex/glob) checks first; expensive (DB query) checks last.
- `state_core.scheduler` (v5) — Step DAG ordering. Subagent dispatch fanout is independent of Step DAG (subagents are intra-Step parallelism, not inter-Step).
- v9 statusline + sidebar plugin TUI extensions — `deviation_logged`/`subagent_spot_check_failed`/`subagent_crash_detected` events surface as one-shot toasts so the executor sees the trigger inline. `subagent_started` / `subagent_complete` populate the sidebar's "active subagents" panel. Rule 4 `log_deviation` calls render via opencode `question` tool (HRN-06).
- Phase 402's `CompactionSnapshot` Pydantic — extended with `subagent_restart_counters: dict[str, int]` and `in_flight_subagents: list[InFlightSubagent]` fields; reinject payload carries them.

### Established Patterns

- `extra="forbid"` on every Pydantic model (v1–v11 convention) — frontmatter, all event payloads, every structured return shape.
- Event-sourced: SQLite authoritative + SyncEvent mirror; projector rebuilds harness state from events.
- Daemon HTTP middleware as canonical decision gate (v6) — `tool.execute.before` reports proposed write/MCP call to daemon; daemon runs layered enforcement; replies allow/reject with structured reason.
- Pure-machine gates (PRF-04 spirit) — deviation classifier cross-validation, arch-pattern allowlist match, subagent whitelist subset check, spot-check 4-layer stack, crash-taxonomy classification. No LLM-as-judge anywhere.
- Mode isolation grep gate: Phase 405 specs live under `state_build/` lineage. The deviation module (`state_build/deviation/`) and subagent module (`state_build/subagents/`) MUST NOT import from `state_teach/`. CI import-graph lint enforces.
- Conventional commit `{type}: {description}` + STATE trailers — state extends gsd-2's `COMMIT_TYPE_RULES` with `STATE-Task:`, `STATE-DeviationRule:`, `STATE-DeviationAttempt:`, `STATE-Subagent-Invocation:` trailers. Single-source-of-truth module `state_build/commit/trailers.py`.

### Integration Points

- Plugin's `tool.execute.before` hook posts every MCP tool call to daemon HTTP endpoint; daemon runs the 7-layer stack; replies allow/reject with structured reason and emits the corresponding event.
- Plugin's `chat.params` hook injects autonomy context block (parent's effective `--tiered`/`--full-yolo`/`--conservative`) into spawned subagent sessions per the autonomy-inheritance flow.
- Daemon's `dispatch_subagent` handler is the wrapper around opencode's `task` tool; injects autonomy, validates whitelist + parallel cap, emits `subagent_started`, subscribes to opencode SSE for `subagent_progress` / `subagent_complete` events.
- Daemon's projector subscribes to deviation + subagent events; writes the `## Deviations` SUMMARY section to `stepNSUMMARY.md` at task end; rebuilds `subagent_restart_counters` / `in_flight_subagents` on boot via replay.
- Rule 4 `log_deviation` MCP handler synchronously renders opencode `question` tool with `alternatives` payload — single round-trip through opencode's question flow; resolution writes `deviation_resolution_recorded` event.
- Subagent orphan reconciliation: daemon-resume handler probes opencode session API via HTTP for each in-flight `invocation_id`; replays opencode session log if needed; emits `subagent_orphan_detected` on terminal unresolvable cases; surfaces Rule 4 human-gate.
- Phase 402 compaction (snapshot + reinject), Phase 403 step events, Phase 404 gate/paralysis/scope events, Phase 405 deviation/subagent events all live in the same event store; replay rebuilds the full harness state.
- v9 statusline + sidebar subscribe to Phase 405 SSE events for live executor feedback.

</code_context>

<deferred>
## Deferred Ideas

- **Past-phase `GSD-*` trailer rename pass.** Phase 403 + 404 CONTEXT.md / spec docs / PLAN docs / SUMMARY docs reference `GSD-Task:`, `GSD-Test-Result:`, `GSD-Gate-Strike:` trailers. Audit grep results (Phase 405 discuss-phase logged 20+ hits across `.planning/milestones/v41/phases/403/**` and `.planning/milestones/v41/phases/404/404-CONTEXT.md`). Rename action: `GSD-Test-Result` → `STATE-TestResult`, `GSD-Task` → `STATE-Task`, `GSD-Gate-Strike` → `STATE-GateStrike`. Recommended owner: a follow-up cleanup phase (e.g., 405.1 or as a Phase 406 sweep) before v14 implementation reads these specs. Phase 405 docs use the new convention; old docs retain the original until the rename.

- **`ErrorKind` enum extension** — recommended starter set above; v14 extends as new failure modes surface. Specifically: `oauth_refresh_failure` (Anthropic stealth + auth refresh midstream), `worktree_checkout_failure`, `pygit2_lock_contention`, `mcp_tool_validation_failure`. Defer to v14 EXEMPLAR-driven extension.

- **Spot-check layer 5 (integration test re-run)** — was offered (maximal option) but deferred. Re-running pytest / mypy / etc. on subagent return is redundant with verify-slice / Step-end gates and adds latency. Revisit post-v17 if observed spot-check-pass-but-Step-fail patterns surface.

- **Per-stage roster expansion via plugin** — gsd-2's `extensions/plugin-system.md` documents extension surface for spawn; state's plugins (v8) could theoretically extend `STAGE_ROSTER` with new `SubagentType` entries. Rejected for v1: rosters are pinned to SUB-02's 14 named types; plugin-driven expansion is post-v17 territory.

- **Grandchild parallel-cap rollup** — was offered but rejected. State accounts for direct children only; grandchild concurrency is unbounded in principle. Risk: `parallel_cap^2 = 400` worst-case process count. Revisit post-v17 if real workloads show concurrency-storm patterns.

- **Partial-artifact preservation on subagent restart** — rejected for v1. Worktree-rollback is the simpler invariant. Revisit post-v17 if observed restart cycles show systematic partial-success patterns.

- **`log_deviation` mid-task vs post-task call** — was discussed implicitly. v1 contract: `log_deviation` can be called any time during task execution; the harness records and counters increment. Mid-task incidental calls (e.g., agent realizes a fix attempt failed before commit) accrue toward the 3-attempt cap. Mirrors 404's "strike accrues at completion-claim boundary" discipline NOT applied here — deviations are agent-declared explicitly, not inferred. Documented as different-from-PRF.

- **Hybrid two-event `deviation_logged` + `deviation_resolved` split** — rejected. Single mutable event row (with append-only `deviation_resolution_recorded` mutation event) wins for projector simplicity. Diverges from 404's `scope_deviation_request` / `_resolved` split (which won there for the request/decision separation; not analogous here because deviations don't have an external decision step until Rule 4 escalation).

- **Pre-authored `alternatives` for `subagent_orphan_detected` Rule-4 escalation** — recommended `[abort_slice, retry_subagent, manual_resolve]`; planner finalizes the exact pros/cons text in v14.

- **Suspended-subagent recovery (pause/resume mid-execution)** — out of v1 scope. Subagents either run to completion or crash; no pause/resume affordance. opencode's `task` tool doesn't expose pause API; revisit if opencode adds one.

- **Tiered autonomy CLI flags vs `state daemon set-autonomy` command** — was discussed implicitly. Autonomy is set at Slice frontmatter and milestone config; CLI flag is the runtime override for a single Slice. The shape of the flag (e.g., `state run-slice --autonomy=conservative`) is implementation territory; deferred to v15.

- **Per-stage roster boundaries when a `subagent_type` could plausibly serve two stages** — recommended: list in both stages (e.g., `researcher` in both discuss-slice and plan-slice rosters per SUB-02). Runtime stage gates determine which roster applies. Planner finalizes the exact dual-listed types.

- **`deviation_attempts` SQLite table separate from event store** — rejected for v1. State's event store is authoritative; the in-memory projector rebuilds the per-tuple counter from `deviation_logged` events. A separate SQLite table would duplicate state; replay-from-event-store is the canonical mechanism. Mirrors v6 daemon crash-recovery pattern.

- **`STATE-Subagent-Invocation:` trailer for subagent-produced commits** — recommended on every commit produced inside a subagent session, carrying the `invocation_id`. v14 wires the subagent session's commit hook to inject the trailer. Planner finalizes the exact propagation mechanism (env var? CLI arg? frontmatter injection?).

- **Multi-attempt resolution mutation chain** — currently spec says the `Deviation` row's `resolution` mutates from `pending` → `auto_fix_succeeded` / etc. via `deviation_resolution_recorded` append-only events. The terminal state is a single row mutation; intermediate state (attempt 1 failed, attempt 2 in progress) is NOT separately tracked beyond `attempt_number` increments. v14 may add intermediate-state tracking if EXEMPLAR-stepNPLAN.md gates show value.

- **Strike-counter durability across daemon restart** — implicit in event-sourced design (events are SQLite-authoritative, daemon rehydrates on boot via replay). Explicit specification of the rehydrate path is v14 territory; mirrors 404's same-rationale deferral.

- **`subagent_progress` event payload granularity** — recommended: emit on every TUI-visible event from the child (message_end, tool_use start/end) per gsd-2's `processSubagentEventLine` shape. Detailed payload schema deferred to v14.

</deferred>

---

*Phase: 405-deviation-rules-subagent-management*
*Context gathered: 2026-05-11*
