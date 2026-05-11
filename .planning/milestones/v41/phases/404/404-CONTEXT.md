# Phase 404: Boolean Proof Gate & Discipline Guards — Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 404 produces three canonical specification documents (and supporting amendments to REQUIREMENTS.md if any decision below extends a v1 requirement):

1. **`PROOF-GATE.md`** — `must_haves` proof block evaluation semantics (PRF-01 truth/artifact/key_link evaluator types per PRF-04 pure-machine constraint); gate evaluation order at task / Step / Slice boundaries (PRF-02 / PRF-05); per-task `<verify><automated>` + `<acceptance_criteria>` binding rule; the 6-strike escalation ladder (PRF-06 — D-8 locked) with `gate_strike` event schema; the `tool.execute.before` write-block enforcement that implements PRF-07 "fail blocks advancement"; the `gate_strike` / `gate_resolved` event payloads.

2. **`ANALYSIS-PARALYSIS-GUARD.md`** — read-only tool set classification (APG-01) adapted from gsd-2's `bash-interceptor.ts` regex corpus; per-step-type threshold table (APG-02, APG-03 — default 5 for execute; default 15 for discuss/research/plan); 3-advisory → clear+reinject → 3-more → force-stop+human-gate ladder (APG-04, APG-05); `paralysis_event` payload.

3. **`SCOPE-PROHIBITION.md`** — `<done>` vs `must_haves.artifacts` cross-check at task end (SRP-01); prohibited-language scan with regex + scope + exception + path-allowlist (SRP-02, SRP-03); `files_modified` allowlist enforcement via `tool.execute.before` + deviation-unblock event (SRP-04); `split_recommendation` MCP tool routing to plan-slice (SRP-05); `deferred-items.md` out-of-scope logging (SRP-06).

Phase 404 is **design-only — no code lands.** Spec output is implemented by v14 (Build Kernel) and v15 (Build Core Commands). Every check specified here is **pure-machine** (PRF-04); no LLM-as-judge anywhere in the proof gate or discipline guards.

</domain>

<decisions>
## Implementation Decisions

### Strike-counter semantics (PRF-06 expanded)

**Counter scope: per `(task_id, check_id)` tuple.** Finest analog to gsd-2's per-`runAgentLoop`-invocation `consecutiveAllToolErrorTurns` (`gsd-2/packages/pi-agent-core/src/agent-loop.ts:191`). Each failing `must_haves` check — one truth assertion, one artifact entry, one key_link entry — has its own 6-strike chain. Max audit clarity; agent sees per-check escalation; chains for different checks do not poison each other.

**Reset rule: continue counting across the clear+reinject tier.** Literal D-8 reading: "human gate at strike 6 **total**." Strike 3 fires clear+reinject (single shot); strike 4 is the next failed eval after the reinjected agent re-attempts the same `(task_id, check_id)` pair. Diverges from gsd-2's `consecutiveAllToolErrorTurns = 0`-on-success pattern (`agent-loop.ts:191`), but D-8 already diverges from gsd-2 by introducing the reinject tier at all — the divergence is principled, not accidental.

**Strike trigger: failed pure-machine eval at the completion-claim boundary.** A strike accrues if-and-only-if:
1. The agent signals "task complete" via either (a) attempting any Write/Edit targeting a file owned by the **next** task (PRF-07 boundary detection), OR (b) explicitly calling the `complete_task` MCP tool (analog of gsd-2's `complete_task` at `gsd-2/src/resources/extensions/gsd/tools/complete-task.ts`); AND
2. The harness runs the task's `<verify><automated>` + `<acceptance_criteria>` + frontmatter `must_haves.*` pure-machine evaluators; AND
3. At least one evaluator returns `fail`.

Mid-task incidental gate evaluations (e.g., harness running checks against WIP artifacts mid-Write) do **not** strike. Mirrors gsd-2's preparation-vs-execution narrowing (`agent-loop.ts:324-329`, issue #3618): execution failures are not strikes; only declared-completion-then-still-failing pattern strikes.

**APG vs PRF: independent counters.** gsd-2's `loop-control.md` §0 Correction 1 explicitly forbids conflating distinct counters — gsd-2 has FOUR separate counters at four scopes (`MAX_CONSECUTIVE_VALIDATION_FAILURES`, `consecutiveErrors`, `consecutiveAllToolErrorTurns`, `consecutiveErrorUnits`/`ESCALATION_THRESHOLD=5`). State follows the same principle:

- `paralysis_event` chain (APG): 3 advisory → clear+reinject → 3 more → human gate. Per task.
- `gate_strike` chain (PRF): 3 advisory → clear+reinject → 3 more → human gate. Per `(task_id, check_id)`.
- Each can independently reach force-stop.
- The `harness_intervention` event (HRN-05, owned by Phase 406) is the umbrella; both `paralysis_event` and `gate_strike` cite it as `trigger_reason`.

**`gate_strike` event payload (PRF-06 expanded):**

```python
class GateStrike(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    step_id: str
    slice_id: str
    check_id: str                                  # truth_idx | artifact_idx | key_link_idx | verify_automated | acceptance_idx
    check_type: Literal["truth", "artifact", "key_link", "verify_automated", "acceptance"]
    strike_number: int                              # 1..6
    tier: Literal["advisory", "reinject", "human_gate"]
    agent_response_summary: str                     # ≤ 2KB excerpt (gsd-2 truncation convention)
    eval_evidence: str                              # ≤ 2KB excerpt of the failed pure-machine output
    triggered_at: datetime                          # UTC, ISO-8601
    session_id: str
    snapshot_event_id: str | None                   # set when tier == "reinject" (cross-link to compaction.snapshot_taken)
```

### Prohibited-language scan (SRP-02 / SRP-03 expanded)

**Regex form: case-insensitive word boundary.** Single compiled regex per scanner load: `\b(v1|simplified|placeholder|todo|fixme|future)\b` with `re.IGNORECASE`. Matches `# v1 stub`, `# TODO: future work`. Does **not** match `v1.5.2`, `version 1`, `simplified-config-loader.ts` (file name), `oversimplification` (substring), `futures.py` (substring). Mirrors gsd-2's `inferCommitType` shape (`file-tracking.md:445` — "concatenate, lowercase, then for each rule and each keyword, word-boundary regex matches"; multi-word phrases use substring — state has no multi-word tokens in v1 so word-boundary uniformly).

**Single-source-of-truth module.** Regex constants live in a single Python module under `state_build/harness/scope/`, mirroring gsd-2's `branch-patterns.ts` pattern (single module exporting `SLICE_BRANCH_RE`/`QUICK_BRANCH_RE`/`WORKFLOW_BRANCH_RE`; imported by every consumer; updates flow from one place).

**Scan target: source files inside `files_modified` only.** Scope = the SRP-04 allowlist; if a Write/Edit targets a path not in `files_modified` it is rejected by the allowlist before the language scan ever runs. Files with `.md`, `.json`, `.yml`, `.yaml`, `.toml` extensions inside `files_modified` are **still scanned** (they are scoped sources for this Step). Lightest enforcement consistent with PRF-04.

**Tracking-issue exception (SRP-03): strict regex + cross-check.** A prohibited token passes the scan if-and-only-if its occurrence matches the exception regex AND the captured ID resolves to a real reference:

```python
EXCEPTION_RE = re.compile(r"\b(TODO|FIXME)\(([A-Z]+-\d+)\)")
# Captured ID must satisfy:
#   1. Match an entry in .planning/milestones/<MS>/REQUIREMENTS.md (look for `**ID-NN**` heading), OR
#   2. Match an entry in .planning/milestones/<MS>/slices/<N>/deferred-items.md (look for `- ID-NN:` row)
```

Cross-check is **pure-machine grep**, run at scan time. Match fails → emit `scope_check` event (tier=advisory) with the captured ID, the bullet `Unresolved tracking ID: <id>. Add to deferred-items.md or REQUIREMENTS.md first.` Mirrors gsd-2's content-fingerprint-resync-gate pattern (declarative manifest + cross-check).

**Spec-doc allowlist: `.planning/**/*.md` path glob.** Files matching the glob skip the prohibited-language scan entirely. Phase 404's own CONTEXT.md, ROADMAP.md, REQUIREMENTS.md, every `*-PLAN.md`, every `*-SUMMARY.md`, every `*-VERIFICATION.md`, every `*-RESEARCH.md` etc. exempt. Coarse but predictable; matches the project's structural convention that `.planning/` is the meta-prose layer where forbidden tokens carry their **literal meaning** (the word "v1" in a roadmap describes version 1; it is not a placeholder).

Note: this is **scan exemption only**. The path-allowlist does **not** exempt these files from `files_modified` enforcement (SRP-04) — Steps that write `.planning/` artifacts must still declare them in `files_modified`.

**`scope_check` event payload (SRP-02):**

```python
class ScopeCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    step_id: str
    slice_id: str
    file_path: str                                  # the file being written
    matched_token: str                              # the literal token, e.g., "v1", "TODO"
    matched_offset: int                             # byte offset in the proposed content
    matched_line: int                               # 1-indexed line number
    exception_matched: bool                         # True if EXCEPTION_RE matched the surrounding context
    exception_id: str | None                        # captured ID if exception_matched
    exception_resolved: bool                        # True if cross-check found the ID in REQUIREMENTS or deferred-items
    triggered_at: datetime
    session_id: str
```

### Read-only Bash classification (APG-01 expanded)

**Read-only pattern corpus adapts gsd-2's `bash-interceptor.ts:15-54`.** Single Python module `state_build/harness/paralysis/bash_classifier.py` exports a pre-compiled `READ_ONLY_PATTERNS` list. Initial corpus:

```python
# Adapted from gsd-2/packages/pi-coding-agent/src/core/tools/bash-interceptor.ts:15-54
# (the read-side rules) plus state-specific extensions.
READ_ONLY_PATTERNS: list[re.Pattern] = [
    # gsd-2 heritage (5 read patterns from bash-interceptor)
    re.compile(r"^\s*(cat(?!\s*<<)|head|tail|less|more)\s+"),
    re.compile(r"^\s*(grep|rg|ripgrep|ag|ack|fgrep|egrep)\s+"),
    re.compile(r"^\s*(find|fd|locate)\s+"),
    # state-specific extensions (filesystem inspection, no mutation)
    re.compile(r"^\s*(ls|ll|la|wc|file|stat|du|df|pwd|tree|env|which|type|command)\b"),
    re.compile(r"^\s*(jq|yq)\s+(?!.*-[iI]\b).*"),   # jq/yq, but NOT -i in-place mode
    # git read-only subcommands (explicit allowlist)
    re.compile(r"^\s*git\s+(log|show|diff|status|blame|branch\s+-l|config\s+--get|describe|rev-parse|ls-files)\b"),
    # python3 / node / ruby / perl inline scripts handled by INLINE_SCRIPT_RULE below
]
```

**Compound command handling: split + worst-sub-command wins.** Tokenize the command on shell-boundary tokens (`;`, `&&`, `||`, `|`, `&` at word boundaries; heredoc bodies treated as opaque single tokens). Classify each sub-command independently. If **any** sub-command is non-read-allowlist (or matches a write-pattern below), the whole compound is `write`. Pure-machine; no real shell-AST parser required; conservative.

```python
# Split tokens
COMPOUND_SEP = re.compile(r"(?:;|\&\&|\|\||\||\&)(?![\w])")
```

**Output redirection: any path-target redirect = write.**

- `> path` or `>> path` (any non-`/dev/null` path) → write.
- `> /dev/null` and `>> /dev/null` → read (no real write).
- `2> path` or `2>> path` to a path → write.
- `2>&1` (stream merge, no path) → read.
- `| tee` and `| tee -a` (anywhere except `tee --version`) → write.
- Process substitution `>(...)` or `<(...)` → write (conservative).

Pure-machine token detection at parse time. No path-resolution magic (no symlink chasing, no cwd-relative gymnastics) — a redirect is judged by its right-hand token only.

**Inline interpreter scripts: grep the payload for write-syscall patterns.** For `python3 -c '...'`, `node -e '...'`, `ruby -e '...'`, `perl -e '...'`, `bash -c '...'`, `sh -c '...'`: extract the payload (the quoted/escaped string following `-c` / `-e`) and grep it against `WRITE_SYSCALL_PATTERNS`:

```python
WRITE_SYSCALL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bopen\s*\([^)]*,\s*['\"][wax]"),         # open(..., 'w'|'a'|'x' modes)
    re.compile(r"\bprint\s*\([^)]*file\s*="),              # print(..., file=...)
    re.compile(r"\b(os|shutil|pathlib)\.(remove|rename|unlink|copy|move|copyfile|write_text|write_bytes)"),
    re.compile(r"\bsubprocess\."),                          # any subprocess call (conservative)
    re.compile(r"[^&<>|]>(?![&=])"),                        # bare `>` redirect in the payload
    re.compile(r"\b(fs|node:fs)\.(write|writeFile|appendFile|rename|unlink|mkdir|rmdir)"),  # node
    re.compile(r"\b(File|IO)\.(write|open\s*\([^)]*,\s*['\"]w)"),                           # ruby
]
```

Payload match → classify as `write`. Clean payload → classify as `read`. Pure-machine; deterministic; matches PRF-04 spirit.

**Bash exit code is NOT a strike trigger.** Mirrors gsd-2's preparation-vs-execution narrowing (`agent-loop.ts:324-329`, issue #3618): a `grep` that exits 1 ("no matches") is valid usage, not a paralysis trigger. The paralysis counter cares about **classification of the invocation** (read vs write), not about its exit status. Documented as a non-default in `ANALYSIS-PARALYSIS-GUARD.md`.

**`paralysis_event` payload (APG-06 expanded):**

```python
class ParalysisEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    step_id: str
    slice_id: str
    count: int                                      # current consecutive read-only count
    threshold: int                                  # the per-step-type threshold (default 5 for execute, 15 for discuss/research/plan)
    tier: Literal["advisory", "reinject", "human_gate"]
    advisory_number: int                            # 1..6 (3 + 3 ladder)
    agent_response_summary: str                     # ≤ 2KB excerpt
    triggering_command: str                         # the bash command (or tool name) that incremented the counter past threshold
    triggered_at: datetime
    session_id: str
```

### Gate shapes (PRF-02 / PRF-03 expanded)

**`<acceptance_criteria>` bullets bind to `must_haves` by index.** Each bullet carries an inline annotation pointing to one entry in the frontmatter `must_haves.{truths, artifacts, key_links}` lists (Phase 403 schema):

```xml
<acceptance_criteria>
  - [check: must_haves.truths[0]] ofxparse2 module is importable
  - [check: must_haves.artifacts[1]] src/state_build/snapshot.py ≥ 80 lines, provides CompactionSnapshot
  - [check: must_haves.key_links[0]] tests/test_snapshot.py imports from state_build.snapshot
  - [check: verify_automated] pytest tests/test_snapshot.py exits 0
</acceptance_criteria>
```

Pure-machine: bullet text = human-readable; machine evaluator = the indexed must_haves entry (or the task's `<verify><automated>` block). The harness builds an evaluator per bullet at gate time from the index. Mirrors gsd-2's `complete_task` field-binding shape — `taskParams.completion_criteria` ↔ Q5, `behavior_contract` ↔ Q6, `test_plan` ↔ Q7 (`tools/complete-task.ts:73-77, 339-355`). Each bullet has a deterministic verdict.

Bullet annotation grammar (Pydantic-validated at plan parse time):
```
ANNOTATION_RE = r"\[check:\s*(must_haves\.(truths|artifacts|key_links)\[\d+\]|verify_automated)\]"
```

Bullets without a valid annotation fail plan validation at the planner stage (research-slice / validation stage). No annotation → no machine evaluator → PRF-04 violated.

**Per-Step `stepN-VERIFY.json` is authoritative; `N-VERIFICATION.md` is the rolled-up readable view.** Mirror gsd-2's `<task>-VERIFY.json` (`verification-evidence.ts:81-98`) at Step granularity.

Pydantic schema (`extra="forbid"`):

```python
class StepVerifyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]                      # bump literal to migrate; old files surface as parse errors
    step_id: str
    slice_id: str
    timestamp: datetime
    must_haves: MustHavesResult                     # nested
    acceptance_criteria: list[AcceptanceResult]     # one entry per bullet, bound by ANNOTATION_RE index
    verify_automated: VerifyAutomatedResult         # bash exit code + stdout/stderr ≤ 2KB
    overall_passed: bool                            # server-side recomputed; NEVER trust an LLM-emitted aggregate
    overall_verdict: Literal["pass", "flag", "omitted", "fail"]   # extends gsd-2's pass|flag|omitted with "fail" for the agent loop
    outcome: Literal["continue", "retry", "pause"]  # mirrors gsd-2 EvidenceJSON outcome discriminator

class MustHavesResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truths: list[CheckResult]
    artifacts: list[CheckResult]
    key_links: list[CheckResult]

class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    verdict: Literal["pass", "flag", "omitted", "fail"]
    evidence_excerpt: str                           # ≤ 2KB (gsd-2 truncation convention)
    strike_count_at_close: int                      # final strike count when this check was closed
    gate_strike_event_ids: list[str]                # full audit chain
```

**Bounded truncation: 2KB per check, 10KB total.** Mirrors gsd-2's `formatFailureContext` (`verification-gate.ts:115-142`). Truncation marker: `[... truncated <N> bytes ...]`. Same truncation discipline applies to `formatEvidenceTable` markdown rendering.

**Server-side recomputation of `overall_passed`.** Mirrors gsd-2's defensive pattern (`verification-evidence.ts` + `eval-review-schema.ts:210-227`): the harness recomputes `overall_passed` from sub-fields after writing the file. An agent-emitted `overall_passed: true` with `truths[0].verdict: fail` is rejected at parse time.

**`N-VERIFICATION.md` rolled-up truth-table columns (wide audit-traceable).**

| Column | Source | Notes |
|---|---|---|
| `step_id` | `StepVerifyResult.step_id` | One row per check, grouped by step |
| `task_id` | gate_strike chain | When the strike chain references a specific task |
| `check_id` | `CheckResult.index` formatted as `truths[0]` etc. | Stable across runs |
| `scope` | `truth \| artifact \| key_link \| verify_automated \| acceptance` | The PRF-01 / PRF-02 check type |
| `source_expr` | Pydantic dump of the must_haves entry | The actual expression being evaluated |
| `verdict` | `CheckResult.verdict` (`pass \| flag \| omitted \| fail`) | Extends gsd-2's `pass\|flag\|omitted` |
| `strike_count_at_close` | `CheckResult.strike_count_at_close` | 0 if the check passed on first eval |
| `gate_strike_event_ids` | `CheckResult.gate_strike_event_ids` | Full audit chain (newline-joined event ids) |
| `evidence_excerpt` | `CheckResult.evidence_excerpt` (≤ 2KB) | gsd-2-style bounded |
| `timestamp` | `StepVerifyResult.timestamp` | ISO-8601 UTC |

Generated by a deterministic projector at Slice-verify-stage entry (handler subscribes to `step_verify_completed` events; aggregates all step results in the Slice; renders the markdown).

**`omitted-if-empty` pattern.** Mirrors gsd-2 (`tools/complete-slice.ts:65, 387-424`): a check with no specified evaluator (e.g., a Step whose `must_haves.key_links` is empty) closes with `omitted`, NOT `pass`. The omitted state preserves audit clarity ("we checked and the criterion doesn't apply") and is distinct from `pass` ("we checked and confirmed").

### Slice-level `<verification>` artifact shape (PRF-03)

**Bash blocks live in `stepNPLAN.md` per Step + a separate Slice-level script.** Two surfaces:

1. **Per-Step `<verification>` bash block inside `stepNPLAN.md`** — runs at Step end (before commit). Block content is bash only (no Python; if a Python check is needed, the Step author writes a `.py` file in `files_modified` and the bash block invokes `python3 path.py`). Block is **immutable** under PAP-03 / Phase 403's mutability matrix.

2. **Slice-level `slice-verification.sh` co-located with `N-VERIFICATION.md`** — runs at Slice end (the verify-slice stage). Aggregates Step-level evidence + runs cross-Step integration checks. Single bash script; pure-machine.

Both timeout-bounded (default 120s per Step block; default 600s for slice-verification.sh; tunable via Slice frontmatter `verify: {step_timeout_s: int, slice_timeout_s: int}`). Timeout → `fail` verdict.

### SRP-04 `files_modified` enforcement

**`tool.execute.before` write-block enforces the allowlist.** Inherits the diff-the-proposed-write mechanism from Phase 403 PAP-05; reuses the same hook handler. Behavior:

- Compute the prospective target path (Edit operation in-memory; Write target directly).
- If target NOT in `files_modified` (exact match OR glob match — Phase 403 allowed both) → reject the write with `scope_deviation` event.
- If target IS in `files_modified` → fall through to PAP-05 immutability check, then to the prohibited-language scan, then allow.

**Deviation unblock event flow.** When the agent legitimately needs to edit a file outside `files_modified` (e.g., discovers a missing import in a sibling file during execution), the agent emits a `scope_deviation_request` MCP tool call:

```python
class ScopeDeviationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    step_id: str
    slice_id: str
    requested_path: str
    justification: str                              # agent-supplied rationale ≤ 1KB
    requested_at: datetime
    session_id: str
```

The request surfaces as a `checkpoint:decision` under `--tiered` (per Phase 403 task-type behavior + Phase 405 DEV-03 territory). Resolution emits `scope_deviation_resolved` with `resolution: approve | reject`. Approved deviations write a temporary one-shot allowlist entry; the request and resolution events are part of the audit chain. Files_modified itself is **never mutated** at runtime — the override is event-scoped.

### SRP-05 `split_recommendation` mechanism

**Explicit MCP tool `request_step_split` is the canonical trigger.** No NL keyword detection; no heuristic auto-split. The agent must call:

```python
# MCP tool signature
def request_step_split(
    reason: str,                                    # ≤ 2KB; why the current Step exceeds one Step's scope
    partial_artifacts: list[str],                   # paths in the worktree that should be preserved for the replan
) -> SplitRecommendation: ...

class SplitRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    step_id: str
    slice_id: str
    reason: str
    partial_artifacts: list[str]
    requested_at: datetime
    session_id: str
```

On call, the harness:

1. Emits `split_recommendation` event with the payload above.
2. Takes a worktree snapshot (mirrors Phase 402 `compaction.snapshot_taken` plumbing): records `slice_id`, `step_id`, `task_id`, worktree commit SHA, partial artifact paths.
3. Transitions the Slice state to `pending_replan` (run-slice terminal state).
4. Exits run-slice cleanly. Partial commits stay on the worktree branch; the replan inherits them.

The replan re-enters research-slice / planning stage, which reads the `split_recommendation` event + the worktree snapshot and produces new `stepNPLAN.md` files breaking the over-scoped Step into smaller Steps. PAP-03 locks survive replan when step_id is unchanged (Phase 403); a split necessarily changes step_ids, so `must_haves` for the new Steps are re-authored fresh.

Mirrors gsd-2's explicit `complete_task` / `complete_slice` / `validate_milestone` MCP tool-call boundary pattern (`tools/complete-task.ts`, `tools/complete-slice.ts`, `tools/validate-milestone.ts`) — agent intent is signaled by tool call, not by NL output scan.

### Claude's Discretion

- Exact word lists for `READ_ONLY_PATTERNS` extensions beyond gsd-2's heritage (planner finalizes after surveying actual Step-execution shell usage in EXEMPLAR-stepNPLAN.md).
- Exact `WRITE_SYSCALL_PATTERNS` regex completeness (planner adds variants as needed; the substrate is the substantive list above).
- Bounded-truncation byte values (2KB/check, 10KB/total are gsd-2's pins; planner may tune for state's typical evidence sizes if EXEMPLAR-stepNPLAN.md gates show systematically larger outputs).
- Exact wording of advisory messages on `gate_strike`, `paralysis_event`, `scope_check`, `scope_deviation_request` (recommended: include the failing check_id, the strike count, and the specific remediation hint).
- Per-Step verification bash-block timeout default (recommended 120s; planner may tune).
- Slice-level `slice-verification.sh` timeout default (recommended 600s).
- Whether to expose `--prohibited-tokens` CLI override for the language scan list (recommended: no, lock it to the SRP-02 v1 list; revisit post-v17).
- `files_modified` glob syntax pin (recommended: PEP 668 `fnmatch` for filesystem globs; planner may pick Python `pathlib.PurePath.match` instead).
- The deterministic projector implementation for `N-VERIFICATION.md` truth-table generation (handler shape, error recovery on partial step results, ordering of rows beyond Step DAG topology).
- Whether `request_step_split` returns a structured value to the agent (recommended: return `SplitRecommendation` Pydantic model so the agent's last log statement is auditable) or fire-and-exit.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 404 scope & requirements
- `.planning/milestones/v41/ROADMAP.md` §Phase 404 — goal, dependencies (Phase 403), success criteria 1–5.
- `.planning/milestones/v41/REQUIREMENTS.md` — PRF-01..PRF-07 + APG-01..APG-06 + SRP-01..SRP-06.
- `.planning/milestones/v41/HANDOFF.md` — D-6 (boolean proof gate via must_haves + verify), D-8 (6-strike ladder), D-10 (4-tier intervention).

### Phase 402 + 403 prior decisions (carry forward — do NOT revisit)
- `.planning/milestones/v41/phases/402/402-CONTEXT.md` — `tool.execute.before` as canonical block hook, plugin-as-thin-reporter, Pydantic `extra="forbid"` convention, event-sourced + SQLite authoritative.
- `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — reinject payload XML shape; `<active_plan>`/`<upstream_provides>`/`<current_task_pointer>` slots; `compaction.snapshot_taken` event the strike-counter's `tier=reinject` cites via `snapshot_event_id`.
- `.planning/milestones/v41/phases/403/403-CONTEXT.md` — `must_haves.{truths, artifacts, key_links}` frontmatter schema (`MustHaves`, `ArtifactCheck`, `KeyLink` Pydantic models), `<verify>` blocks locked immutable, `files_modified` allowlist (exact paths or globs), `<options>` sub-tag for `checkpoint:decision`, diff-the-proposed-write enforcement, content-stripping at injection time, `stepNPLAN.md` (no-dash form), `step_id` stable hash convention.
- `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` (when shipped) — frontmatter `must_haves`, `<acceptance_criteria>`, `<verify><automated>`, the five task types Phase 404 enforces gates for.
- `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` (when shipped) — mutability matrix; PAP-05 `plan_edit_blocked` mechanism Phase 404 extends with `scope_deviation_request`.

### gsd-2 reference patterns (cited inline above)
- `~/projects/gsd2deconstruction/kb/workflow/quality-enforcement.md` — `EvidenceJSON` schema v1 (§7.1), `formatFailureContext` 2KB/check 10KB/total truncation (§3.2), `quality_gates` table row schema (§8.7), `pass | flag | omitted` 3-state verdict (§0 Correction 2 Vocabulary 2), `omitted-if-empty` pattern (§9.3), server-side recomputation of aggregate fields (§7.1), three-tier discovery (§3), gate registry exhaustiveness (`satisfies Record<GateId, GateDefinition>` + `assertGateCoverage`), explicit MCP tool-call boundary (`complete_task`/`complete_slice`/`validate_milestone`).
- `~/projects/gsd2deconstruction/kb/workflow/loop-control.md` §0 Correction 1 — four distinct counters at four scopes (`MAX_CONSECUTIVE_VALIDATION_FAILURES=3`, `consecutiveErrors`, `consecutiveAllToolErrorTurns`, `consecutiveErrorUnits`/`ESCALATION_THRESHOLD=5`); refuses to conflate distinct failure modes — informs state's APG-vs-PRF counter independence.
- `~/projects/gsd2deconstruction/kb/workflow/loop-control.md` §4 — `consecutiveAllToolErrorTurns = 0` on success; preparation-vs-execution narrowing (#3618 at `agent-loop.ts:324-329`); execution failures (`grep` exit-1) explicitly NOT counted. Informs state's "strike accrues only at completion-claim boundary" semantics.
- `~/projects/gsd2deconstruction/kb/core/tool-system.md` §5 + `~/projects/gsd2deconstruction/kb/patterns/bash-interceptor-as-ergonomic-redirect.md` — `bash-interceptor.ts:15-54` 7 default rules (5 read-side patterns); pre-compiled regex + availability gate at `bash-interceptor.ts:86`; advisory-not-security framing; no command allowlist/denylist (`tool-system.md:851`); graceful degradation on invalid regex.
- `~/projects/gsd2deconstruction/kb/workflow/file-tracking.md` §inferCommitType (line 445) — word-boundary regex + first-match-wins + multi-word phrases use substring. Informs state's prohibited-language scan regex shape.
- `~/projects/gsd2deconstruction/kb/workflow/file-tracking.md` §branch-patterns — `SLICE_BRANCH_RE`/`QUICK_BRANCH_RE`/`WORKFLOW_BRANCH_RE` single-module pattern. Informs state's `state_build/harness/scope/` regex module shape.
- `~/projects/gsd2deconstruction/kb/patterns/llm-mediated-trigger-table.md` — separate trigger column pattern (curated table + LLM reads). NOT the substrate for the 6-strike ladder despite earlier framing speculation; cited here as reference-only for completeness.
- `~/projects/gsd2deconstruction/kb/patterns/dispatch-rules-table.md` (referenced by analysis) — dispatch shape for tier-escalation events; gives a pattern shape for the `harness_intervention` event (Phase 406 owns; Phase 404 emits `gate_strike` / `paralysis_event` / `scope_check` / `scope_deviation_request` that feed it).

### Phase 400 + 401 prior decisions (v40)
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — existing event taxonomy. Phase 404 adds: `gate_strike`, `gate_resolved`, `paralysis_event`, `scope_check`, `scope_deviation_request`, `scope_deviation_resolved`, `split_recommendation`, `step_verify_completed`, `slice_verify_completed`.
- `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — Pydantic frontmatter convention extending the same shape.
- `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — adds `stepN-VERIFY.json` (per Step, machine-readable) and `slice-verification.sh` (per Slice, executable) to the canonical Slice folder layout. `N-VERIFICATION.md` already cataloged; this phase pins its column schema.

### Project-level constraints
- `.planning/PROJECT.md` — Build/Teach exclusivity (Phase 404 specs Build-only), Python 3.12+, opencode primary host.
- `CLAUDE.md` (project) — per-plan SUMMARY.md mandatory, security_enforcement=true, mode isolation cardinal rule (Phase 404 spec lives under `state_build/harness/` lineage; must not bleed into `state_teach/`).

### Architecture & integration (shipped, reference only — Phase 404 is design-only)
- `src/state_core/schema.py` — existing event Pydantic models; new event types extend the same `EventEnvelope` convention.
- `src/state_worker/hooks/` — `tool.execute.before` handler. Phase 404's write-block (PRF-07), files_modified enforcement (SRP-04), prohibited-language scan (SRP-02), and immutability check (Phase 403 PAP-05) all stack inside this hook in deterministic order.
- `src/state_daemon/middleware.py` — daemon decides; the strike-counter state + threshold tables live here.
- `state-inputs/opencode/packages/plugin/src/index.ts` — `tool.execute.before`/`tool.execute.after`/`chat.params` hook signatures; opencode `task` tool for subagent spawn; opencode `question` tool for human gates (HRN-06).

### Downstream consumers (these will read Phase 404 output)
- **v14 Build Kernel** — implements the strike counter (per-(task_id, check_id) tuple, in-memory cache backed by event store), the bash classifier module, the prohibited-language scanner module, the files_modified allowlist checker, the deterministic projector for `N-VERIFICATION.md`, the `request_step_split` MCP tool handler, the bounded-truncation utility.
- **v15 Build Core Commands** — implements the research-slice validation stage that checks `<acceptance_criteria>` bullet annotations (`ANNOTATION_RE`); the verify-slice stage that runs `slice-verification.sh` and writes `N-VERIFICATION.md`; the replan re-entry path that consumes `split_recommendation` events + worktree snapshots.
- **Phase 405 (Deviation Rules & Subagent Management)** — `checkpoint:decision` autonomy under `--tiered` is the resolution path for `scope_deviation_request`; the 4-rule deviation framework (DEV-01..DEV-04) consumes the strike counter's `tier=human_gate` events; tiered autonomy (DEV-05) interacts with the auto-resolution policy for advisory tiers.
- **Phase 406 (Harness Architecture Rollup)** — `harness_intervention` event umbrella aggregates `gate_strike`/`paralysis_event`/`scope_check`/`scope_deviation_request`/`split_recommendation`; the 4-tier intervention ladder (HRN-04) cites Phase 404's per-tier behaviors; the layered diagram shows `tool.execute.before` write-block stack (allowlist → immutability → prohibited-language → write-block) as the canonical enforcement composition.

</canonical_refs>

<specifics>
## Specific Ideas

- **gsd-2's refusal to conflate counters is load-bearing for state.** loop-control.md §0 Correction 1 explicitly enumerates four distinct counters and forbids treating them as one. State follows the same discipline: APG counter and PRF strike counter are independent, emit distinct events, can each independently reach force-stop. Conflating them would directly violate the gsd-2 framing principle we cite.

- **Preparation-vs-execution narrowing is the canonical strike-trigger principle.** gsd-2's `consecutiveAllToolErrorTurns` increments only on schema/preparation failures, not on `grep` exit-1. State's analog: a strike counts only at the completion-claim boundary (agent says "done" via `complete_task` MCP call OR via Write/Edit targeting next-task files). Mid-task incidental failures during work do NOT strike. Mirrors gsd-2's #3618 narrowing.

- **`pass | flag | omitted` is mandatory three-state vocabulary.** gsd-2's `omitted-if-empty` pattern at `tools/complete-slice.ts:65, 387-424` is the operating evidence that two-state (`pass | fail`) is insufficient. State extends to four states (`pass | flag | omitted | fail`) — `fail` is the agent-loop's machine verdict; `pass | flag | omitted` are the closure verdicts (gsd-2's three) carried into `N-VERIFICATION.md`.

- **Server-side recomputation is non-negotiable for `overall_passed`.** gsd-2's `verification-evidence.ts` + `eval-review-schema.ts:210-227` recompute aggregates from sub-fields and reject LLM-emitted aggregates. State applies the same discipline: the harness recomputes `overall_passed` from `must_haves.*.verdict + acceptance_criteria.*.verdict + verify_automated.verdict`. An LLM that writes `overall_passed: true` while a sub-check is `fail` gets rejected at parse time, not at gate-fire time.

- **Bullet-to-must_haves index binding preserves PRF-04 purity.** Free-form acceptance bullets violate "pure-machine." Bullet-as-regex extraction is fragile. Index binding `[check: must_haves.truths[0]]` is the minimum-spec rule that keeps bullets human-readable AND each bullet machine-evaluable. Mirrors gsd-2's `complete_task` field-binding (taskParams fields ↔ Q5/Q6/Q7 gates).

- **Adapt-don't-clone for the bash classifier.** gsd-2's `bash-interceptor.ts` corpus is the heritage substrate but state's use case differs (paralysis counting, not tool-redirect advisory). The READ_ONLY_PATTERNS in `state_build/harness/paralysis/bash_classifier.py` reuses gsd-2's 3 read patterns verbatim and adds state-specific filesystem-inspection extensions (ls, wc, stat, etc.) and git read-only subcommand enumeration. Single-module pattern (gsd-2's `branch-patterns.ts` shape).

- **Path-allowlist `.planning/**/*.md` is the right granularity for the prohibited-language exemption.** Phase 404's own CONTEXT.md writes "v1" in prose. Frontmatter opt-out per file (option 2 in discussion) is too much ceremony for every spec doc. Extension allowlist `*.md` is too loose (catches user-facing READMEs). Path-allowlist matches the structural convention that `.planning/` IS the meta-prose layer.

- **`request_step_split` is an explicit MCP-tool-call boundary, NOT an NL keyword pipe.** gsd-2's pattern across `complete_task` / `complete_slice` / `validate_milestone` is consistent: agent intent is signaled by tool call, never by output scanning. State follows. NL keyword detection was offered and rejected for the same reason gsd-2 rejects it.

- **`scope_deviation_request` resolves via `checkpoint:decision`, not via direct files_modified mutation.** files_modified itself is locked (Phase 403 frontmatter immutability). The deviation flow uses event-scoped one-shot allowlists — the request, the resolution, and the time-bounded permit are all events. Audit-replayable.

- **The strike counter's `tier=reinject` cites the compaction snapshot.** A strike-3 reinject is mechanically the same as a Phase 402 compaction snapshot+reinject; the `gate_strike` event's optional `snapshot_event_id` field carries the cross-link. Replay can reconstruct the full strike chain alongside the compaction chain.

</specifics>

<code_context>
## Existing Code Insights

### Reference only (Phase 404 is design-only — no code lands)

Phase 404 produces architecture specification documents. Shipped code below is reference for understanding existing patterns and integration points the spec must respect; v14 implements per these specs.

### Reusable Assets

- `state_core.schema` — `EventEnvelope`, `extra="forbid"` Pydantic convention. New event Pydantic models (`GateStrike`, `GateResolved`, `ParalysisEvent`, `ScopeCheck`, `ScopeDeviationRequest`, `ScopeDeviationResolved`, `SplitRecommendation`, `StepVerifyCompleted`, `SliceVerifyCompleted`) extend this.
- `state_core.projector` — CQRS handler registration pattern. The `N-VERIFICATION.md` truth-table projector subscribes to `step_verify_completed`/`slice_verify_completed`/`gate_strike` events; renders the rolled-up markdown table deterministically.
- `state_worker.hooks` (v7) — `tool.execute.before` is the single hook where the stack lives: (1) files_modified allowlist → (2) Phase 403 immutability check → (3) prohibited-language scan → (4) `<discovered_threats>` append-only carve-out → allow. Deterministic order; pure-machine each layer.
- `state_core.scheduler` (v5) — Step DAG ordering. Replan after `split_recommendation` re-enters the scheduler input; the existing wave/depends_on semantics carry forward.
- v9 statusline + sidebar plugin TUI extensions — `gate_strike`/`paralysis_event`/`scope_check` events surface as one-shot toasts so the executor sees the trigger inline. `request_step_split` surfaces as a persistent banner ("Slice transitioning to pending_replan; this session will exit cleanly").

### Established Patterns

- `extra="forbid"` on every Pydantic model (v1–v11 convention) — frontmatter, all event payloads, the new `StepVerifyResult` JSON shape.
- Event-sourced: SQLite authoritative + SyncEvent mirror; projector rebuilds `N-VERIFICATION.md` from events on demand.
- Daemon HTTP middleware as canonical decision gate (v6) — `tool.execute.before` reports proposed write to daemon; daemon runs the layered enforcement stack; replies allow/reject with a structured reason.
- Pure-machine gates (PRF-04 spirit) — bash classifier regex match, prohibited-language regex scan, files_modified glob match, must_haves evaluator dispatch. No LLM-as-judge anywhere.
- Mode isolation grep gate: Phase 404 specs live under `state_build/harness/` lineage. The compiled regex modules (`state_build/harness/scope/`, `state_build/harness/paralysis/`) MUST NOT import from `state_teach/`.
- Conventional commit `{type}: {description}` + GSD trailers (gsd-2 `file-tracking.md` Correction 3) — state extends with `GSD-Gate-Strike: <event_id>` trailer when a commit is the agent's response to a strike chain (audit linkage from git log to event store).

### Integration Points

- Plugin's `tool.execute.before` hook posts every Write/Edit to daemon HTTP endpoint; daemon runs the four-layer stack (allowlist → immutability → prohibited-language → write-block-on-next-task-when-gate-failing); replies allow/reject with a structured reason and emits the corresponding event.
- Plugin's `tool.execute.before` for Bash tool: classifies the command via bash_classifier; daemon increments paralysis counter; emits `paralysis_event` on threshold cross.
- Daemon's projector subscribes to `step_verify_completed`, `slice_verify_completed`, `gate_strike`, `scope_check`, `paralysis_event`; writes `stepN-VERIFY.json` (per Step) and `N-VERIFICATION.md` (per Slice, rolled up).
- `request_step_split` MCP tool handler (v14): emits `split_recommendation`, takes worktree snapshot (reuses Phase 402's `compaction.snapshot_taken` plumbing under a new event type), transitions Slice state, signals run-slice to exit cleanly.
- `scope_deviation_request` MCP tool handler: emits the event; daemon surfaces a `checkpoint:decision` via opencode `question` tool with the proposed path + justification; resolution writes `scope_deviation_resolved` and either allows the write or escalates to DEV-04 Rule 4 (Phase 405 territory).
- Compaction events (Phase 402), Step plan events (Phase 403), and Phase 404 gate/paralysis/scope events live in the same event store; replay rebuilds harness state alongside Slice/Step/compaction state.

</code_context>

<deferred>
## Deferred Ideas

- **SRP-04 `files_modified` test-file inference for `auto+tdd`** — was discussed but deferred to v14. For Steps where a task is `auto+tdd` on `src/foo.py`, the corresponding `tests/test_foo.py` should be implicitly allowed without listing — but the inference rule (mirror-path? convention scan?) is implementation territory. v14 finalizes; Phase 404 specifies that the planner emits both source AND test paths in `files_modified` for `auto+tdd` tasks.

- **Generated-file allowlist (lockfiles, migrations, code-gen output)** — deferred to v14. The planner may add a `files_modified.generated: list[glob]` sub-field if EXEMPLAR-stepNPLAN.md sizing shows real friction with auto-regenerated `uv.lock` / `pnpm-lock.yaml` / migration files.

- **Hybrid per-token regex for prohibited language** — rejected. The v1 token list (`v1, simplified, placeholder, todo, fixme, future`) is short enough that uniform word-boundary suffices. Revisit if v2 expands the list with prose tokens that need substring semantics.

- **`scope_check` tier-2 tool-block on first match (vs advisory-only)** — was offered but rejected. Mirrors SRP-02's "Detection emits `scope_check` event and injects a justification request" — tier=advisory, not block. The agent gets a chance to justify (via tracking-issue reference) before the write is rejected. Hard-block on first match would force ceremony before legitimate spec docs ever pass.

- **NL keyword detection for `split_recommendation`** — rejected. gsd-2's pattern: tool-call boundary, never NL scan. State follows.

- **Implicit `split_recommendation` from N-paralysis+N-strike pattern** — rejected. Removes agent intent; risks false positives on legitimately hard checks. The agent calling `request_step_split` is the canonical signal.

- **Shared APG+PRF counter** — rejected. gsd-2 §0 Correction 1 explicitly forbids conflation; state follows.

- **Bullet-as-regex pattern extraction for `<acceptance_criteria>`** — rejected. Index binding wins on machine-evaluability and human readability. Regex extraction from NL prose is fragile.

- **Markdown-only `N-VERIFICATION.md` without per-Step JSON** — rejected. gsd-2's `<task>-VERIFY.json` is the canonical pattern; JSON authoritative + MD rolled-up view is the right shape. Markdown-only loses the round-trippable schema-versioned contract.

- **`stepN-VERIFICATION.md` (per-Step markdown) instead of `stepN-VERIFY.json`** — rejected. Mirrors gsd-2's `<task>-VERIFY.json` shape; markdown-only loses TypeBox/Pydantic migration discipline.

- **Frontmatter opt-out marker for prohibited-language scan** — rejected. Path-allowlist `.planning/**/*.md` is the right granularity; per-file opt-out is too much ceremony.

- **Extension allowlist `*.md` everywhere** — rejected. Catches user-facing READMEs; lets prohibition leak into the BUILT product's docs. Path-allowlist scoped to `.planning/` is correct.

- **Heuristic split-detection as advisory hint surfacing a checkpoint:decision** — rejected for v1. Adds a runtime checkpoint not in the locked REQUIREMENTS; over-spec. Revisit post-v17 if real Step-execution data shows the agent failing to recognize its own scope creep.

- **`gate_strike` advisory message authoring style** — deferred to Claude's Discretion + EXEMPLAR-stepNPLAN.md gates. The planner finalizes wording after worked-example sizing.

- **Strike-counter durability across daemon restart** — implicit in event-sourced design (events are SQLite-authoritative, daemon rehydrates state from events on boot). Explicit specification of the rehydrate path is v14 territory.

- **Inline `python3 -c` write-syscall pattern completeness** — v1 covers the common cases (open/print/os/shutil/pathlib/subprocess/fs/IO). Planner may extend; further extensions deferred to v14 based on EXEMPLAR-driven observation.

- **Per-step-type APG threshold plumbing (frontmatter axis)** — REQUIREMENTS APG-03 already pins defaults (5 for execute; 15 for discuss/research/plan). The frontmatter field to override per Step was discussed; deferred to Phase 403's STP-02 expansion or v14 — currently the threshold derives from `type` field in Step frontmatter (Phase 403 schema), and Slice-level override goes via Slice frontmatter `paralysis: {execute_threshold: int, research_threshold: int}` (mirrors Phase 402's `compaction:` shape). Planner finalizes the field name.

- **Step-level paralysis override** — rejected for v1 (mirrors Phase 403's rejection of Step-level autonomy). Slice-level override is sufficient.

</deferred>

---

*Phase: 404-boolean-proof-gate-discipline-guards*
*Context gathered: 2026-05-11*
