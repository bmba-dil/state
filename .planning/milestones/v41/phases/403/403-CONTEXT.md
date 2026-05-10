# Phase 403: Step/Task Decomposition & Plan-as-Prompt — Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 403 produces three canonical specification documents (and supporting amendments to REQUIREMENTS.md if any decision below extends a v1 requirement):

1. **`STEP-PLAN-FORMAT.md`** — full `stepNPLAN.md` template with Pydantic-validated frontmatter schema (`extra="forbid"`) covering every STP-02 field; complete XML body section catalog (STP-03) with `<task>` sub-tag spec (STP-04); five-type task taxonomy behavior spec (STP-05); deterministic granularity-selection algorithm (STP-06); literal-excerpt and exact-files-with-line-ranges contracts (STP-07, STP-08).
2. **`PLAN-AS-PROMPT.md`** — injection flow (PAP-01 verbatim PLAN injection + runtime augmentation); `@`-reference resolution rule with one-level inline + token cap (PAP-02); mutability matrix (PAP-03 + the locks decided here); `plan_edit` event schema (PAP-04); immutable-section block mechanism via `tool.execute.before` plus `plan_edit_blocked` event (PAP-05); content-stripping rule with on-disk audit-logged original preserved (PAP-06).
3. **`EXEMPLAR-stepNPLAN.md`** — a fully realized worked-example Step plan using a realistic state-project Slice (e.g., "Implement CompactionSnapshot Pydantic model" or similar plausible v14 Step). Both spec docs above cite literal excerpts from this exemplar. Lives at `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`. This is the canonical "GSD-shape demonstration plan" referenced by STP-03's success criterion 2.

Phase 403 is design-only — no code lands. The harness behaviors specified here are implemented in v14 (Build Kernel) and v15 (Build Core Commands).

</domain>

<decisions>
## Implementation Decisions

### Frontmatter schema completeness (STP-02 expanded)

**`must_haves` location: frontmatter sub-block.** YAML `must_haves: {truths, artifacts, key_links}` validated by Pydantic `StepFrontmatter` model (`extra="forbid"`). Manifest-in-head, action-in-body — same shape as gsd-2 SKILL.md / agent.md frontmatter discovery patterns (`frontmatter-first-skill-discovery.md`, `frontmatter-defined-agent-role.md`), but with project's strict-validation pole (Pydantic forbids extras; gsd-2 agent loader is permissive — state diverges deliberately).

**Field types & constraints (Pydantic-validated):**

```python
class StepFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: str                                   # e.g., "402"
    slice: str                                   # slice_id (slug form)
    step: str                                    # step_id (slug form, stable across replans — see Granularity)
    type: Literal["auto", "auto+tdd",
                  "checkpoint:human-verify",
                  "checkpoint:decision",
                  "checkpoint:human-action"]
    wave: int                                    # non-negative; v5 scheduler input
    depends_on: list[str]                        # same-Slice step_ids ONLY (cross-Slice deps belong to Slice DAG)
    files_modified: list[str]                    # exact paths or globs (planner picks; spec allows both)
    autonomous: bool                             # legacy boolean retained for back-compat with REQUIREMENTS wording
    requirements: list[str]                      # REQ-IDs (e.g., ["STP-01", "PAP-04"])
    must_haves: MustHaves                        # nested model — truths/artifacts/key_links
class MustHaves(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truths: list[str]                            # bash/python assertions (verifiable per PRF-04)
    artifacts: list[ArtifactCheck]               # {path, provides, min_lines}
    key_links: list[KeyLink]                     # {from, to, via, pattern}
```

**autonomy is NOT a Step frontmatter field.** Per DEV-06 + SUB-09, autonomy lives only on the Slice frontmatter; Steps inherit. Single precedence chain: milestone default → Slice override → done. No Step-level autonomy axis.

**`depends_on` cross-check (planner validation):** at the research-slice validation stage, the planner verifies `depends_on` is consistent with `<read_first>` references against upstream Steps' `provides:` blocks. Misalignment fails `N-VALIDATION.md` and forces a replan iteration. This is state's hybrid of gsd-2's slice-scope explicit `depends` JSON (authored intent) + gsd-2's task-scope `reactive-graph.ts` IO derivation (verified consistency). **Reference:** `workflow-engine.md` §6 three-scope dependency model + Correction 2.

### Mutability matrix (PAP-03 expanded)

**Immutable (locked):**
- ALL frontmatter fields. `must_haves.*` was already locked by PAP-03; lock the rest as Step-identity fields (changing them means it's a different Step).
- `<objective>`, `<success_criteria>` — Step contract.
- `<acceptance_criteria>`, `<done>`, `<files>` — task contract (per `<task>`).
- `<interfaces>` — STP-07 literal upstream excerpts; mutating silently desyncs from upstream artifact (re-plan required if upstream genuinely changes).
- Every `<verify>` block at task and Slice level — already PAP-03.

**Mutable (executor may edit):**
- `<action>`, `<read_first>`, prose-style `<context>` sections (executor refines as it learns).

**Hybrid: `<threat_model>`** — design-time block is **locked**, but the executor MAY APPEND newly discovered threats into a dedicated `<discovered_threats>` sub-tag (write-only-append). Keeps the design contract immutable while allowing observed-during-execution security findings to land in the artifact instead of getting lost. The append-only semantic is enforced via `tool.execute.before` (writes into `<discovered_threats>` allowed; writes into the parent `<threat_model>` rejected).

### Injection-time mechanics

**`@`-reference resolution (PAP-02):** one-level inline + per-injection token cap.
- Harness resolves `@.planning/X.md` and `@-` refs at injection time, inlines verbatim file content, stops at one level (no recursive @-resolution).
- Per-injection token cap (initial: 30k tokens for all inlined refs combined; planner pins exact value in `PLAN-AS-PROMPT.md`).
- Excess content replaced with `<truncated path="X.md" bytes_omitted="N"/>` marker.
- Cache key: `(snapshot_event_id, ref_path)` tuple; cache lifetime = current Slice session.
- Token-counter: same fallback as CTX-08 (Anthropic `usage` if present; chars/4 heuristic otherwise).

**Content stripping (PAP-06):** harness strips at injection time, on-disk file unchanged.
- **plan-slice reasoning meta blocks** — research notes, pattern-mapping rationale, validation-stage commentary, alternatives-considered. Belongs in DECISIONS.md, not the executor's working prompt.
- **`<interfaces>` excerpts for already-completed upstream Steps** — when the upstream Step's `provides:` blocks are already inlined in `<upstream_provides>` (carried via reinject payload per CTX-06), the redundant `<interfaces>` excerpt is replaced with `<interfaces ref="upstream_provides[step-N]"/>` pointer. Preserves STP-07 zero-codebase-exploration: the contract is still in-context, just deduplicated. Executor scans the named upstream-provides slot for the literal.
- Stripping does NOT modify on-disk `stepNPLAN.md`. The audit-logged original (event store row) carries the full unredacted content.

**`plan_edit` event payload (PAP-04):** unified diff + before/after content hashes.

```python
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

Replay reconstructs full content by walking the diff chain from the original `step_plan_authored` event. Compact, auditable, replay-deterministic. Aligned with gsd-2's best-effort-diff convention (`file-tracking.md` §0 Correction 1: per-turn git commit is best-effort, not transactional).

**Audit-log original (PAP-06):** event store row + on-disk file is the live (mutable) version.
- Original committed to event store as `step_plan_authored` event at research-slice end (full content + SHA-256 hash). Authoritative.
- On-disk `stepNPLAN.md` is the LIVE version executors edit (subject to PAP-05 immutability blocks).
- Replay reconstructs original from event store; live state from file.
- Git history of the file (commit_docs=true in v41 config) provides a secondary audit trail — useful for human review, NOT load-bearing.
- Executor sees the (potentially stripped) injected version during execution, NOT the on-disk file directly.

**Immutable-section block mechanism (PAP-05):** diff-the-proposed-write approach.
- `tool.execute.before` hook intercepts every Write/Edit targeting `stepNPLAN.md` files.
- Computes prospective new content (apply Edit operation in-memory; for Write, the new content is the input).
- Parses both old and new with the StepPlan parser (Pydantic frontmatter + XML body).
- Compares the immutable subset (locked frontmatter keys + locked XML tags from the Mutability Matrix above).
- Any change to a locked section → reject + emit `plan_edit_blocked` event. Pure-machine check (matches PRF-04 spirit). Works for both partial Edit and full Write. The `<discovered_threats>` append-only carve-out is a special case: writes that ONLY add nodes to `<discovered_threats>` (no other diff) pass.

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

### Granularity selection algorithm (STP-06)

**Inputs (deterministic):**
1. **Slice scope token estimate** — sum of input artifact sizes (`DESIGN.md` + `RESEARCH.md` + `PATTERNS.md`) tokenized with a fixed tokenizer (planner pins `tiktoken cl100k_base` or chars/4 fallback per CTX-08 rule).
2. **`files_modified` union count** — distinct files the Slice will touch, computed from the planner's preliminary file map before Step assignment.
3. **`provides:` blocks count** — distinct upstream→downstream artifact handoffs the Slice will produce; maps to DAG edge count.

LLM-counted task estimates are explicitly REJECTED — they violate STP-06's "deterministic function" wording.

**Algorithm: table-driven with bucketed thresholds.**

```text
granularity(scope_tokens, files, provides) -> "coarse" | "standard" | "fine":
  if scope_tokens ≤ 30_000 AND files ≤ 3 AND provides ≤ 2:
    return "coarse"        # 1–2 Steps
  elif scope_tokens ≤ 80_000 AND files ≤ 6 AND provides ≤ 5:
    return "standard"      # 2–3 Steps
  else:
    return "fine"          # 3–5 Steps
```

**Step count (collapsing the range to a single integer):**
- coarse → 2 if `scope_tokens > 15_000`, else 1.
- standard → 3 if `scope_tokens > 50_000` OR `files > 4`, else 2.
- fine → ceil(`provides` / 2), clamped to [3, 5].

Match REQUIREMENTS literal ranges (1–2 / 2–3 / 3–5). Reproducible, debuggable, easy to tune. Inspired by gsd-2 quality-enforcement bucketed gate registries (`quality-enforcement.md` §1 five-pipeline taxonomy) — fixed lookup tables beat formula tuning for spec docs.

**Replan determinism:** same inputs → same Step count + same step_ids.
- step_ids derived from a stable hash: `step_id = slugify(slice_id) + "-step-" + ordinal`, where `ordinal` is the position after sorting candidate Steps by (min `files_modified` path lexicographically, then provides-count desc).
- Replan with identical inputs reproduces the same plan exactly (idempotent at the file level).
- Replan with changed inputs recomputes granularity and emits `step_renamed` / `step_added` / `step_removed` events for diff-replay continuity.
- Locks held by PAP-03 (`must_haves`, `<verify>`) survive replan when step_id is unchanged; if step_id changes (input change forced rename), the new Step inherits authored content but `must_haves` are re-authored fresh (no carry-over of stale gates).

### Task-type behaviors (STP-05 spec)

**`auto`** — fully autonomous; harness allows all writes within `files_modified` allowlist; on completion, gate runs (PRF-02 task `<verify>` + `<acceptance_criteria>`).

**`auto+tdd`** — RED-before-GREEN enforcement via git-log + `tool.execute.before`:
- Harness consults git log for the current task's commit chain.
- Rejects writes to non-test files until at least one commit exists with a `test:` or `red:` prefix AND a captured failing-test artifact (e.g., pytest exit code != 0 stored in commit trailer `GSD-Test-Result: FAIL`).
- After the first commit with `GSD-Test-Result: PASS` (GREEN), refactor commits unrestricted within `files_modified`.
- Pure-machine, replayable. Aligns with `file-tracking.md` Correction 3: GSD metadata in commit trailers (`GSD-Task: <sliceId>/<taskId>`); state extends with `GSD-Test-Result: FAIL|PASS`.

**`checkpoint:human-verify`** — autonomy-tiered behavior per DEV-05 literal:
- `--tiered` (default): auto-approves (visual sanity check passed).
- `--full-yolo`: auto-approves.
- `--conservative`: stops; opencode `question` tool rendered.
- Auto-approval emits `checkpoint_auto_resolved` event with `tier`, `task_id`, `selection="auto-approved"`.

**`checkpoint:decision`** — autonomy-tiered behavior per DEV-05 literal:
- `--tiered`: stops.
- `--full-yolo`: auto-picks option 1 deterministically.
- `--conservative`: stops.
- The option list is authored by the plan author in an `<options>` sub-tag of the `<task>` block. Required: 2–4 named options each with `pros` and `cons` attributes.
  ```xml
  <task type="checkpoint:decision">
    <name>Pick async runtime</name>
    <options>
      <option name="asyncio.TaskGroup" pros="stdlib, structured" cons="3.11+ only"/>
      <option name="anyio" pros="trio-compat" cons="extra dep"/>
    </options>
  </task>
  ```
- Harness renders via opencode `question` tool with the labeled list. Under `--full-yolo`, picks first option deterministically.
- `<options>` is **immutable** (locked, mutability matrix above). Executor cannot add/remove/edit options at runtime.
- No "Other" free-text affordance under build-mode strictness — diverges from AskUserQuestion's default. Decisions are bounded.

**`checkpoint:human-action`** — autonomy-tiered behavior per DEV-05 literal:
- ALL tiers stop. Harness surfaces via opencode `question` tool with the action prompt; resumes when human confirms completion.
- Emits `checkpoint_human_action_pending` on entry, `checkpoint_human_action_resolved` on resume.

### EXEMPLAR-stepNPLAN.md provenance

**Hand-author one as a Phase 403 deliverable** at `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`. Both spec docs (`STEP-PLAN-FORMAT.md`, `PLAN-AS-PROMPT.md`) cite literal excerpts from it. Source content: a fully realized worked example using a realistic state-project Step from v14 Build Kernel scope (e.g., "Implement CompactionSnapshot Pydantic model" — concrete, plausibly real, exercises every section from `<objective>` through `<task><verify><automated>`).

Rejected alternatives:
- Adapting from `state-inputs/get-shit-done/` PLAN.md examples — those use GSD-2 vocabulary (`task` not `Step`, no `provides:`, no Slice context); adaptation cost ≈ rewriting.
- Citing `~/projects/moon/.../02-01-PLAN.md` byte-for-byte (HANDOFF.md reference) — frozen external artifact; citation fragility; designs v41 to match a moving target outside the repo.

The EXEMPLAR file is owned by Phase 403; v14 implementations may diverge from its specifics, but the SHAPE is the contract.

### Claude's Discretion

- Exact tokenizer pin for granularity inputs (`tiktoken cl100k_base` recommended; planner may pick a Python-native alternative if package availability is a concern).
- Exact per-injection token cap value for `@`-resolved inlines (recommended 30k; planner may tune to 20k or 40k based on EXEMPLAR-stepNPLAN.md realistic measurements).
- Bucketed-threshold values (30k/80k/3/6/2/5 above are recommendations; planner finalizes after EXEMPLAR sizing).
- Step-id collision strategy when inputs produce duplicate slugs across Slices (recommended: prefix with slice_id slug, which already happens — so collision-free by construction).
- Exact wording of advisory messages on `plan_edit_blocked` (e.g., "Cannot edit immutable `<acceptance_criteria>` — re-run plan-slice if scope changed").
- The `<options>` sub-tag's exact attribute set (recommended: `name`, `pros`, `cons`; planner may add `risk` or `effort` if EXEMPLAR shows a need).
- Exact event-store row schemas beyond the Pydantic shapes shown above (column types, indexes); inherits state's existing event-store conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 403 scope & requirements
- `.planning/milestones/v41/ROADMAP.md` §Phase 403 — goal, dependencies (Phase 402), success criteria 1–5.
- `.planning/milestones/v41/REQUIREMENTS.md` — STP-01..STP-08 + PAP-01..PAP-06.
- `.planning/milestones/v41/HANDOFF.md` — D-1..D-12 locked design decisions; §2 Task Decomposition Protocol; §3 Plan-as-Prompt Architecture.

### Phase 402 prior decisions (carry forward)
- `.planning/milestones/v41/phases/402/402-CONTEXT.md` — v40↔v41 vocabulary reconciliation (filename `stepNPLAN.md` no-dash form), reinject body XML shape, `tool.execute.before` as canonical block hook, plugin-as-thin-reporter, `chat.params` injection vector.
- `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` (when shipped) — reinject payload `<active_plan>` slot, `<upstream_provides>` slot, `<current_task_pointer>` slot.
- `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` (when shipped) — research-slice multi-stage pipeline owns stepNPLAN.md production; run-slice consumes.

### gsd-2 reference patterns (cited inline above)
- `.planning/milestones/v41/workflow-docs-from-gsd-2/frontmatter-defined-agent-role.md` — manifest-as-frontmatter pattern, permissive-validation pole (state diverges to strict via Pydantic).
- `.planning/milestones/v41/workflow-docs-from-gsd-2/frontmatter-first-skill-discovery.md` — strict-validation pole (regex + length cap); state aligns with this side, replacing regex/length with Pydantic `extra="forbid"`.
- `.planning/milestones/v41/workflow-docs-from-gsd-2/workflow-engine.md` §6 three-scope dependency model + §0 Correction 2 — informs state's hybrid (authored `depends_on` + IO cross-check at validation stage).
- `.planning/milestones/v41/workflow-docs-from-gsd-2/file-tracking.md` §0 Correction 1 (best-effort commit, not transactional) — informs `plan_edit` event diff payload (best-effort with hashes); §0 Correction 3 (commit format `{type}: {description}` with metadata in trailers) — informs `GSD-Test-Result:` trailer for auto+tdd.
- `.planning/milestones/v41/workflow-docs-from-gsd-2/quality-enforcement.md` §0 Correction 2 (gate verdicts `pass | flag | omitted` 3-state) — referenced for Phase 404 verify-block semantics; relevant here because `<verify>` blocks are immutable and Phase 404 specs the verdict states.
- `.planning/milestones/v41/workflow-docs-from-gsd-2/summary-generation-format.md` — referenced for stepNSUMMARY.md shape (run-slice owned, not 403); cited only for context on the verbatim-format-as-contract pattern.

### Phase 400 + 401 prior decisions (v40)
- `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — Step is a leaf artifact; behavioral definition (target of v41 amendment forward-pointer per Phase 402).
- `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — `stepNPLAN.md` filename form (no dash, no leading zeros) — Phase 402 confirmed.
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — existing event taxonomy (Phase 403 adds: `step_plan_authored`, `plan_edit`, `plan_edit_blocked`, `checkpoint_auto_resolved`, `checkpoint_human_action_pending`, `checkpoint_human_action_resolved`, `step_renamed`, `step_added`, `step_removed`).
- `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — Pydantic frontmatter convention (`StepFrontmatter` extends).

### Project-level constraints
- `.planning/PROJECT.md` — Build/Teach exclusivity, Python 3.12+, opencode primary host, library locks.
- `CLAUDE.md` (project) — per-plan SUMMARY.md mandatory, security_enforcement, mode isolation cardinal rule.

### Architecture & integration (shipped, reference only — Phase 403 is design-only)
- `.planning/research/ARCHITECTURE.md` — daemon/worker/plugin trio, event store, mode middleware.
- `src/state_core/schema.py` — existing event types; new event Pydantic models extend the same convention.
- `src/state_worker/hooks/` — `tool.execute.before` handler is where the diff-the-proposed-write block lands at v14 implementation.
- `state-inputs/opencode/packages/plugin/src/index.ts` — opencode `task` tool, `question` tool, hook signatures.

### Downstream consumers (these will read Phase 403 output)
- v14 Build Kernel — implements the StepPlan parser, the `tool.execute.before` immutability block, the @-reference resolver with token cap, the granularity-selection function, the auto+tdd RED-before-GREEN enforcer.
- v15 Build Core Commands — implements the research-slice multi-stage pipeline that produces stepNPLAN.md files (planning + validation stages).
- Phase 404 (Boolean Proof Gate) — consumes the `must_haves` frontmatter sub-block schema; consumes the `<verify>` immutability lock; the gate-verdict 3-state (`pass | flag | omitted`) lands there.
- Phase 405 (Deviation Rules & Subagent Management) — consumes `<options>` sub-tag for checkpoint:decision; consumes the autonomy-tiered checkpoint behaviors.
- Phase 406 (Harness Architecture Rollup) — consumes all of the above; the layered-diagram + sequence-diagram cite Phase 403 events.

</canonical_refs>

<specifics>
## Specific Ideas

- **Strict frontmatter validation wins.** State's `extra="forbid"` Pydantic convention is the strict pole; gsd-2's permissive `typeof === "string"` agent loader is rejected as too loose for a contract artifact. The `frontmatter-first-skill-discovery.md` strict-validation pattern (regex + length caps) is closer to state's posture, and Pydantic supersedes regex/length with full type-graph validation.

- **Hybrid dependency declaration.** State's `depends_on` is authored explicitly (gsd-2 slice-scope `depends` JSON pattern) AND verified against IO at validation stage (gsd-2 task-scope `reactive-graph` pattern, but offline rather than runtime-reactive). Best of both: planner intent + IO reality cross-check. Misalignment fails N-VALIDATION.md.

- **Diff-the-proposed-write is the canonical immutability enforcer.** Pure-machine (parses both old and new with the same StepPlan parser, compares locked subset). Mirrors PRF-04's pure-machine spirit (no LLM-as-judge anywhere in the gate). Works uniformly for partial Edit and full Write.

- **`<discovered_threats>` append-only carve-out.** Locks the design contract (immutable `<threat_model>`) while allowing observed-during-execution security findings to land in the artifact. Without this, threats found during execution would either get lost or trigger a deviation event (DEV-04 Rule 4) for an essentially additive change. The carve-out is principled: locked-by-default, append-only escape valve, both verifiable by the same diff-the-proposed-write enforcer.

- **`@`-reference one-level-only inline.** Recursive expansion violates token-budget predictability (Phase 402's CTX-01 200k absolute is load-bearing). One-level + token cap + truncation marker keeps the prompt budget computable at planning time.

- **Strip `<interfaces>` on later Steps via pointer, not removal.** Replacing with `<interfaces ref="upstream_provides[step-N]"/>` preserves STP-07's zero-codebase-exploration contract — the contract is still in-context, just deduplicated. Silent removal would force executors to discover that upstream excerpts moved.

- **EXEMPLAR-stepNPLAN.md is a Phase 403 deliverable.** STP-03 success criterion 2 requires "literal example excerpts from the GSD-shape demonstration plan"; that file doesn't exist yet. Hand-authoring it inside Phase 403 means: (a) we control its evolution, (b) it matches v41 vocabulary exactly, (c) downstream specs (PLAN-AS-PROMPT.md) can cite it without external dep.

- **DEV-05 literal mapping wins for checkpoint behaviors.** Diverging from REQUIREMENTS would force a REQUIREMENTS amendment cascade. Tighter (tiered stops at human-verify) and looser (tiered auto-picks decision option 1) both rejected.

- **Same-Slice-only `depends_on` preserves Slice-as-context-boundary.** Cross-Slice deps belong to the Slice DAG (planner-managed at the milestone level, executed via fresh-session-per-Slice spawn per CTX-02). Allowing cross-Slice Step deps would smuggle the Slice DAG into Step plans and break the fresh-session abstraction.

</specifics>

<code_context>
## Existing Code Insights

### Reference only (Phase 403 is design-only — no code lands)

This phase produces architecture specification documents. Shipped code below is reference for understanding existing patterns and integration points the spec must respect; v14 implements per these specs.

### Reusable Assets

- `state_core.schema` — `EventEnvelope`, `extra="forbid"` Pydantic convention. New event Pydantic models (`PlanEdit`, `PlanEditBlocked`, `StepPlanAuthored`, `CheckpointAutoResolved`, `CheckpointHumanActionPending|Resolved`, `StepRenamed|Added|Removed`) extend this.
- `state_core.projector` — CQRS handler registration. New handler for the `step_plan_authored` event writes the original-content snapshot row (immutable audit log).
- `state_worker.hooks` (v7) — `tool.execute.before` is where the diff-the-proposed-write immutability block lands. Reads target path; if matches `*/stepNPLAN.md`, parses old + proposed-new with StepPlan parser; rejects on locked-section diff.
- `state_core.scheduler` (v5) — `wave: int` and `depends_on: list[str]` are this scheduler's input; existing Step DAG semantics carry forward.
- v9 statusline + sidebar plugin TUI extensions — surface `plan_edit_blocked` events as one-shot toasts so the executor sees the rejection reason inline.

### Established Patterns

- `extra="forbid"` on every Pydantic model (v1–v11 convention) — frontmatter, all event payloads.
- Event-sourced: SQLite authoritative + SyncEvent mirror; projector rebuilds from events.
- Daemon HTTP middleware as canonical decision gate (v6) — `tool.execute.before` reports proposed write to daemon; daemon decides; reply blocks or allows.
- Pure-machine gates (PRF-04 spirit) — diff-the-proposed-write, granularity table lookup, RED-before-GREEN git-log check.
- Mode isolation grep gate: harness lives under `state_build/`; must NOT import `state_teach/`.
- Conventional commit `{type}: {description}` + GSD trailers (`file-tracking.md` Correction 3) — state extends with `GSD-Test-Result: FAIL|PASS` trailer for auto+tdd.

### Integration Points

- Plugin's `tool.execute.before` hook posts proposed writes targeting `stepNPLAN.md` to daemon HTTP endpoint; daemon parses + diffs + decides; replies allow/reject.
- Daemon's projector subscribes to `step_plan_authored`; writes the original content + hash to event store row; never touches on-disk file.
- Daemon SSE bus emits `plan_edit_blocked` events; v9 toast surfaces to executor.
- Scheduler reads `wave` + `depends_on` from frontmatter (Pydantic-loaded); cycles fail fast at planner validation, NOT runtime (state's planner+validation-stage intentionally validates DAG before execution; gsd-2's `reactive-graph.ts:detectDeadlock` is a runtime check that state doesn't need because Steps are pre-planned).
- Compaction events (Phase 402) and Step events (Phase 403) live in the same event store; replay rebuilds Step state alongside Slice/compaction state.

</code_context>

<deferred>
## Deferred Ideas

- **Conditional stripping via explicit `inject:` frontmatter flag per section** — was offered but deferred. Plan-author-driven per-section inject policy (e.g., `inject: {threat_model: "never", interfaces: "first-step-only"}`) is more expressive but adds a schema axis. Defer to v14 implementation if EXEMPLAR-stepNPLAN.md sizing shows the default stripping rules are insufficient.

- **Step-level autonomy override (mirroring SUB-03 narrowing-only)** — was offered but rejected for v1. Slice-level autonomy is sufficient. Revisit post-v17 if a real Step-vs-Slice autonomy mismatch surfaces.

- **Recursive `@`-reference expansion (depth > 1)** — rejected for v1. If a referenced doc itself uses `@`-refs that need to be resolved at injection time, the planner is encouraged to inline-expand them at planning time (one-shot work) rather than push the cost to every injection.

- **`<options>` "Other" free-text affordance for checkpoint:decision** — rejected for build-mode strictness. Decisions are bounded by plan author. May be revisited for teach-mode harness (v47) where open-ended decisions might be pedagogically useful.

- **`stepNPLAN.original.md` two-file scheme** — rejected. Single file + event-store snapshot wins. Two files would risk divergence and double the per-Slice file count.

- **LLM-counted task estimate for granularity** — rejected. Violates STP-06 "deterministic function." Determinism is load-bearing for replan idempotency.

- **`step_id` purely sequential ordinals (replan-mints-fresh-IDs)** — rejected. Stable hash-derived IDs are required for PAP-04 audit-log clarity across replans.

- **Cycle detection in the Step DAG** — handled at planner validation stage (research-slice → validation), NOT at runtime. State's Steps are pre-planned, so runtime cycle detection (gsd-2's `reactive-graph.ts:detectDeadlock`) is not needed; cycles fail before execute-slice ever spawns. If runtime cycle detection becomes useful (e.g., for dynamic Step injection in a later milestone), revisit.

- **Per-task token-budget assertion** — was discussed implicitly via granularity but not formalized. v14 may add a per-task token-budget check (e.g., `<task>` injected content ≤ N tokens) if observed task sizes drift; for v1, the granularity algorithm is the budget proxy.

- **Checkpoint:decision option scoring / weighting** — `<options>` carries `pros`/`cons` strings only. Adding numeric scoring (effort, risk, impact) could automate option selection under `--full-yolo` beyond "first option deterministic." Defer until --full-yolo runs reveal first-option-pick is unsatisfactory.

</deferred>

---

*Phase: 403-step-task-decomposition-plan-as-prompt*
*Context gathered: 2026-05-10*
</content>
</invoke>