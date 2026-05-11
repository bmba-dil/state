---
phase: 404
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md
autonomous: false
requirements:
  - PRF-01
  - PRF-02
  - PRF-03
  - PRF-04
  - PRF-05
  - PRF-06
  - PRF-07

must_haves:
  truths:
    - "PROOF-GATE.md exists at .planning/milestones/v41/phases/404/specs/PROOF-GATE.md and fully specifies the boolean proof gate at task / Step / Slice levels with pure-machine evaluator dispatch (PRF-04)."
    - "All four `must_haves` evaluator types from PRF-01 (truth/bash, truth/python, artifact, key_link) are documented with their pure-machine evaluator (bash exit code, file existence + wc -l >= min_lines, regex grep against file contents)."
    - "Bullet-to-must_haves index-binding grammar is rendered verbatim: ANNOTATION_RE = r'\\[check:\\s*(must_haves\\.(truths|artifacts|key_links)\\[\\d+\\]|verify_automated)\\]' with literal positive and negative examples drawn from 404-CONTEXT.md Gate-shapes subsection."
    - "Gate evaluation order is rendered as a numbered protocol (task-end -> Step-end -> Slice-end) with the exact harness tool that enforces 'fail blocks advancement' (tool.execute.before write-block targeting next-task files, PRF-07)."
    - "Pydantic StepVerifyResult class is rendered verbatim with model_config = ConfigDict(extra='forbid'), schema_version: Literal[1], nested MustHavesResult / CheckResult sub-models, the four-state verdict Literal['pass', 'flag', 'omitted', 'fail'], and the outcome discriminator Literal['continue', 'retry', 'pause']."
    - "Strike-counter semantics are documented per (task_id, check_id) tuple with the 6-strike escalation ladder (advisory x3 -> reinject single shot -> 3 more advisories -> human gate at strike 6 total) and the 'continue counting across reinject tier' rule from 404-CONTEXT.md."
    - "Strike-trigger semantics (completion-claim boundary) are documented: a strike accrues if-and-only-if the agent signals task complete via attempting Write/Edit to a next-task file OR explicitly calling the complete_task MCP tool, AND at least one pure-machine evaluator returns fail; mid-task incidental gate evaluations do NOT strike."
    - "APG-vs-PRF counter independence is documented citing gsd-2 loop-control.md Correction 1; the harness_intervention umbrella forward-pointer to Phase 406 (HRN-05) is stated."
    - "Pydantic GateStrike event payload is rendered verbatim with the exact field set from 404-CONTEXT.md (task_id, step_id, slice_id, check_id, check_type Literal, strike_number 1..6, tier Literal, agent_response_summary, eval_evidence, triggered_at, session_id, snapshot_event_id optional cross-link to compaction.snapshot_taken)."
    - "Pydantic GateResolved event payload is rendered with the exact field set covering the (task_id, check_id) tuple closure when the chain ends in pass/flag/omitted."
    - "Pydantic StepVerifyCompleted and SliceVerifyCompleted event payloads are rendered with the rolled-up result references (per-Step JSON path; per-Slice N-VERIFICATION.md markdown path)."
    - "Bounded-truncation discipline is documented (2KB per check, 10KB total) with the literal marker '[... truncated <N> bytes ...]' verbatim from 404-CONTEXT.md."
    - "Server-side recomputation of overall_passed is documented as defensive-pattern non-negotiable: harness recomputes from sub-fields; LLM-emitted aggregates with internal contradiction are rejected at parse time."
    - "omitted-if-empty four-state vocabulary (pass/flag/omitted/fail) is documented with the gsd-2 lineage citation (tools/complete-slice.ts:65, 387-424)."
    - "N-VERIFICATION.md rolled-up truth-table column schema is rendered as a 10-column markdown table (step_id, task_id, check_id, scope, source_expr, verdict, strike_count_at_close, gate_strike_event_ids, evidence_excerpt, timestamp) with each column's source field cited."
    - "Per-Step `<verification>` bash-block timeout default (120s) and Slice-level slice-verification.sh timeout default (600s) are pinned with the Slice-frontmatter override mechanism documented (verify: {step_timeout_s: int, slice_timeout_s: int})."
    - "tool.execute.before write-block is documented as the canonical PRF-07 enforcer; the deterministic order of stacked enforcement layers (files_modified allowlist -> Phase 403 immutability check -> prohibited-language scan -> write-block-on-next-task-when-gate-failing) is rendered as a numbered list with forward-pointer to SCOPE-PROHIBITION.md for layers 1+3 and Phase 403 PLAN-AS-PROMPT.md for layer 2."
    - "Mermaid sequence diagram of the harness tool.execute.before write-block gating each transition (task-end -> Step-end -> Slice-end) is rendered; alternative ASCII-arrow form acceptable if Mermaid is rejected."
  artifacts:
    - path: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      provides: "Canonical boolean proof gate spec covering PRF-01..PRF-07."
      min_lines: 550
  key_links:
    - from: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      via: "must_haves frontmatter sub-block schema (MustHaves, ArtifactCheck, KeyLink) consumed from Phase 403"
      pattern: "STEP-PLAN-FORMAT\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      to: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      via: "<verify> block immutability lock (PAP-03) is the precondition for PRF-02 gate stability; diff-the-proposed-write enforcer (PAP-05) is layer 2 of the tool.execute.before stack"
      pattern: "PLAN-AS-PROMPT\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "strike-counter reinject tier cites the compaction.snapshot_taken event via snapshot_event_id cross-link"
      pattern: "CONTEXT-PROTOCOL\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      to: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      via: "stepN-VERIFY.json (per-Step machine-readable) and slice-verification.sh (per-Slice executable) added to canonical Slice folder layout"
      pattern: "ARTIFACT-CATALOG\\.md"
---

<objective>
Author the canonical `PROOF-GATE.md` spec document — the design contract that v14 Build Kernel implements for the pure-machine boolean proof gate. This file fully specifies: (1) the `must_haves` frontmatter block evaluator dispatch (PRF-01); (2) per-task `<verify><automated>` + `<acceptance_criteria>` bullet-to-index binding (PRF-02); (3) Slice-level pre-commit `<verification>` bash + `N-VERIFICATION.md` rolled-up truth table column schema (PRF-03); (4) the pure-machine constraint that no LLM-as-judge appears anywhere in the proof gate (PRF-04); (5) the gate evaluation order at task / Step / Slice boundaries (PRF-05); (6) the 6-strike escalation ladder with `GateStrike` / `GateResolved` event payloads (PRF-06); (7) the `tool.execute.before` write-block that implements "fail blocks advancement" (PRF-07).

Purpose: PRF-01..PRF-07 fully covered. Downstream consumers — v14 (Build Kernel: strike counter + projector + bash-block runner), v15 (Build Core Commands: verify-slice stage that runs `slice-verification.sh` and writes `N-VERIFICATION.md`), Phase 405 (deviation framework consumes strike-counter tier=human_gate events), Phase 406 (harness rollup cites this spec for layer 3 of the intervention ladder) — all read from this file.

Output: One markdown spec doc at `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md`, ≥550 lines, fully populated with literal Pydantic class definitions, gate-evaluation-order protocol, 10-column truth-table schema, strike-counter semantics, four event Pydantic payloads (GateStrike, GateResolved, StepVerifyCompleted, SliceVerifyCompleted), and a sequence diagram of the tool.execute.before write-block stack.
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
@.planning/milestones/v41/phases/404/404-CONTEXT.md
@.planning/milestones/v41/phases/403/403-CONTEXT.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
@.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
@.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
@.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — `MustHaves` / `ArtifactCheck` / `KeyLink` from Phase 403 STEP-PLAN-FORMAT.md frontmatter schema (PRF-01 consumes these):
```python
class ArtifactCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    provides: str
    min_lines: int

class KeyLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_: str    # alias "from" — Python keyword collision
    to: str
    via: str
    pattern: str

class MustHaves(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truths: list[str]                            # bash/python assertions (verifiable per PRF-04)
    artifacts: list[ArtifactCheck]
    key_links: list[KeyLink]
```

Excerpt B — `EventEnvelope` from src/state_core/schema.py lines 239-265 (every event in this spec rides this envelope):
```python
from pydantic import BaseModel, ConfigDict
from typing import Any, Literal

class EventEnvelope(BaseModel):
    """Generic event envelope — used for serialization and generic reads."""
    model_config = ConfigDict(extra="forbid")
    id: str = ""                        # ULID
    seq: int = 0                        # per-aggregate monotonic sequence number
    aggregate_type: str = "arc"         # which aggregate this event belongs to
    aggregate_id: str = ""              # ID of the aggregate instance
    type: str = ""                      # event type string, e.g. "state.step.gate_strike"
    data: dict[str, Any] = {}
```

Excerpt C — `<acceptance_criteria>` annotation grammar from 404-CONTEXT.md (Gate-shapes subsection):
```xml
<acceptance_criteria>
  - [check: must_haves.truths[0]] ofxparse2 module is importable
  - [check: must_haves.artifacts[1]] src/state_build/snapshot.py >= 80 lines, provides CompactionSnapshot
  - [check: must_haves.key_links[0]] tests/test_snapshot.py imports from state_build.snapshot
  - [check: verify_automated] pytest tests/test_snapshot.py exits 0
</acceptance_criteria>
```
ANNOTATION_RE = `r"\[check:\s*(must_haves\.(truths|artifacts|key_links)\[\d+\]|verify_automated)\]"`

Excerpt D — compaction.snapshot_taken cross-link from Phase 402 CONTEXT-PROTOCOL.md — GateStrike.snapshot_event_id forward-references this event when tier=='reinject'.
</interfaces>

<threat_model>
Phase 404 is design-only. PROOF-GATE.md introduces no production attack surface — it is a markdown specification. Threats considered (per `<security_constraint>`):

- **[high] Spec-doc misinterpretation by v14 implementers**: If the spec leaves the four-state verdict vocabulary (pass/flag/omitted/fail) or the strike-counter scope (per-(task_id, check_id)) ambiguous, v14 could collapse states or scope counters incorrectly, breaking audit-replay determinism. **Mitigation in spec:** Pydantic class definitions are authoritative; prose is supplementary. Render every Literal[] union exhaustively; render every field with the exact name/type from 404-CONTEXT.md `<decisions>`. v14's StepVerifyResult unit tests will assert against these Pydantic definitions as fixtures.

- **[med] Strike-counter integer overflow**: An unbounded strike counter could overflow `int` at runtime under pathological agent loops. **Mitigation in spec:** spec MUST stipulate `strike_number: int  # 1..6` is bounded by the ladder semantics — strike 6 fires human_gate and the (task_id, check_id) chain closes; no further strikes accrue. v14 enforces via type guard at the increment site.

- **[high] Server-side recomputation bypass**: If the spec leaves `overall_passed` as agent-emitted, an LLM that writes `overall_passed: true` with a `truths[0].verdict: fail` corrupts the audit log. **Mitigation in spec:** explicit "server-side recomputation is NON-NEGOTIABLE" subsection with positive (recomputed: true) and negative (rejected: agent-emitted with internal contradiction) examples. v14 enforces at the StepVerifyResult parser boundary.

- **[med] Mode-isolation drift**: Build-only spec. **Mitigation:** explicit "Build-mode only" header note; no `state.teach.*` references; events go in `BUILD_ONLY_EVENT_PREFIXES`.

- **[low] Truncation marker injection**: The literal marker `[... truncated <N> bytes ...]` could collide with agent-emitted content if N is user-controllable. **Mitigation:** N is harness-controlled (computed from byte length); spec stipulates the marker is added by the truncation utility, not by the agent.

- **[med] Sequence diagram divergence from prose**: If the Mermaid (or ASCII) sequence diagram contradicts the prose protocol, v14 implementers may follow whichever is more convenient. **Mitigation:** spec MUST state "prose protocol is authoritative; diagram is supplementary" up-front; both must be cross-checked by the planner-validation stage.

No production code lands. No secrets. No network calls. No untrusted input.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author PROOF-GATE.md sections 1-5 (overview, must_haves evaluator dispatch, acceptance-criteria binding, gate evaluation order, tool.execute.before write-block stack)</name>
  <files>
    .planning/milestones/v41/phases/404/specs/PROOF-GATE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (full file — every locked decision is load-bearing; <decisions> subsections "Strike-counter semantics", "Gate shapes (PRF-02 / PRF-03 expanded)", "SRP-04 files_modified enforcement" provide verbatim source)
    - .planning/milestones/v41/REQUIREMENTS.md lines 58-69 (PRF-01..PRF-07 verbatim)
    - .planning/milestones/v41/HANDOFF.md lines 130-200 (§4 Boolean Proof Gate Architecture if present; else search "PROOF" / "boolean")
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — Pydantic MustHaves/ArtifactCheck/KeyLink consumed verbatim from Section 2; <verify>/<acceptance_criteria>/<done> sub-tag specs consumed from Section 4)
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (full file — mutability matrix locks every <verify> block; PAP-05 diff-the-proposed-write enforcer is layer 2 of the tool.execute.before stack)
    - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md (full file — must_haves block example + <acceptance_criteria> annotation examples)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "compaction.snapshot_taken" — GateStrike.snapshot_event_id forward-references this event)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — naming convention state.{tier}.{action}; this spec adds state.step.gate_strike / .gate_resolved / .step_verify_completed / .slice_verify_completed)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic extra="forbid" convention extended here)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (search "VERIFICATION" — confirms N-VERIFICATION.md already cataloged; this spec ADDS stepN-VERIFY.json + slice-verification.sh)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-PLAN.md lines 1-90 (Phase 403 spec-doc plan reference for verbose format/density target)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md`. Sections 1–5 below; Task 2 owns sections 6–10. **Concrete content from 404-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 1 — File header

    ```
    # Boolean Proof Gate (Canonical, v41)

    > **Phase:** 404
    > **Status:** Canonical (v41)
    > **Requirements covered:** PRF-01..PRF-07
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
    > **Sibling specs:** ANALYSIS-PARALYSIS-GUARD.md (APG counter — independent from PRF), SCOPE-PROHIBITION.md (files_modified allowlist + prohibited-language scan — layers 1 and 3 of the tool.execute.before stack).
    > **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
    ```

    1-paragraph overview: the harness gates task / Step / Slice advancement on a pure-machine boolean proof gate. PRF-01 defines the `must_haves` frontmatter block (consumed verbatim from Phase 403's STEP-PLAN-FORMAT.md). PRF-02 carries the gate to the per-task level via `<verify><automated>` + `<acceptance_criteria>` bullets index-bound to `must_haves`. PRF-03 rolls up to the Slice level via the pre-commit `<verification>` bash blocks + the deterministic `N-VERIFICATION.md` projector. PRF-04 forbids LLM-as-judge anywhere. PRF-05 fixes the evaluation order. PRF-06 specifies the 6-strike escalation ladder with `GateStrike` / `GateResolved` event audit. PRF-07 enforces "fail blocks advancement" via `tool.execute.before` write-block on next-task files.

    ### Section 2 — must_haves Evaluator Dispatch (PRF-01, PRF-04)

    Heading: `## must_haves Evaluator Dispatch (PRF-01, PRF-04)`.

    Sub-section `### Inherited frontmatter schema`:
    Quote the Phase 403 `MustHaves` / `ArtifactCheck` / `KeyLink` Pydantic class definitions verbatim from STEP-PLAN-FORMAT.md Section 2 (already rendered above in `<interfaces>` Excerpt A). Cite the source: "From `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` §Frontmatter Schema (STP-02). PRF-01 consumes the same schema; this spec specifies the EVALUATORS that compute verdicts against each list entry."

    Sub-section `### Evaluator dispatch table`:
    Render as a markdown table:

    | must_haves field | Entry type | Pure-machine evaluator | Verdict source |
    |------------------|------------|------------------------|----------------|
    | `truths[i]: str` | bash/python assertion string | Run as `bash -c "<string>"` (or `python3 -c "<string>"` if `#!python3` prefix); exit code 0 = pass, non-zero = fail | bash exit code |
    | `artifacts[i]: ArtifactCheck` | `{path, provides, min_lines}` | (1) `test -f "$path"`; (2) `wc -l "$path"` >= `min_lines`; (3) `provides` string is informational only (NOT machine-evaluated — used in N-VERIFICATION.md prose column) | file existence + line count |
    | `key_links[i]: KeyLink` | `{from, to, via, pattern}` | `grep -E -- "$pattern" "$from"` AND the grep MUST return >= 1 line containing a reference to `to` (full-text substring check, OR regex if `pattern` constrains it); exit code 0 = pass | grep exit code |
    | (task-level) `<verify><automated>` | bash one-liner | Run as `bash -c "<command>" timeout=120s`; exit code 0 = pass | bash exit code |
    | (task-level) `<acceptance_criteria>` bullets | bullet text with `[check: ...]` annotation | Dispatch via ANNOTATION_RE; bullet's evaluator = the indexed must_haves entry OR the task's `<verify><automated>` | dispatched evaluator's verdict |

    Add a 1-paragraph note: "**No LLM-as-judge anywhere (PRF-04).** Every evaluator above is bash exit code, file existence, wc -l, or regex grep — pure machine. The `provides` field on `ArtifactCheck` is human-readable annotation; it does NOT participate in verdict computation. A truth string that requires natural-language interpretation (e.g., 'the implementation is correct') MUST be rejected by the planner-validation stage; the spec stipulates the planner emits `state.slice.validation_failed` with `reason='non-machine-evaluable truth'` and the bullet is replaced with one or more machine-evaluable assertions."

    Sub-section `### Inline interpreter prefix convention (truths)`:
    "A `truths[i]` string MAY use the `#!python3 ` (with trailing space) prefix to indicate Python evaluation: e.g., `#!python3 from state_build.snapshot import CompactionSnapshot; assert CompactionSnapshot.model_config['extra'] == 'forbid'`. Without the prefix, the string is bash. The harness strips the prefix before passing to `python3 -c`. This mirrors the EXEMPLAR-stepNPLAN.md truth: `python3 -c 'from state_build.snapshot.compaction import CompactionSnapshot; ...'` — which the EXEMPLAR currently writes as a bash invocation of python3; both forms produce the same machine verdict. v14 picks one canonical form; the spec accepts both."

    ### Section 3 — Acceptance-Criteria Index-Binding (PRF-02)

    Heading: `## Acceptance-Criteria Index-Binding (PRF-02)`.

    Sub-section `### Bullet annotation grammar`:
    Render verbatim from 404-CONTEXT.md Gate-shapes subsection:

    ```python
    # ANNOTATION_RE — Pydantic-validated at plan parse time
    ANNOTATION_RE = r"\[check:\s*(must_haves\.(truths|artifacts|key_links)\[\d+\]|verify_automated)\]"
    ```

    Then quote `<interfaces>` Excerpt C verbatim — the four-bullet `<acceptance_criteria>` example from 404-CONTEXT.md — as a fenced XML block.

    Sub-section `### Binding semantics`:
    Render verbatim:
    - "Each `<acceptance_criteria>` bullet carries an inline annotation pointing to one entry in the frontmatter `must_haves.{truths, artifacts, key_links}` lists OR to the task's `<verify><automated>` block."
    - "The bullet text is **human-readable**; the machine evaluator is the indexed entry. The harness builds an evaluator per bullet at gate time from the index."
    - "Mirrors gsd-2's `complete_task` field-binding shape — `taskParams.completion_criteria` <-> Q5, `behavior_contract` <-> Q6, `test_plan` <-> Q7 (`tools/complete-task.ts:73-77, 339-355`). Each bullet has a deterministic verdict."
    - "**Bullets without a valid annotation fail plan validation at the planner stage (research-slice / validation stage).** No annotation -> no machine evaluator -> PRF-04 violated."

    Sub-section `### Rejection cases (planner-validation enforcement)`:
    List at least 5 counterexamples literally:
    - `- The implementation is correct.` -> REJECT (no `[check:]` annotation)
    - `- [check: looks_good] verify the output` -> REJECT (annotation does not match ANNOTATION_RE — invalid scope name)
    - `- [check: must_haves.truths[]] anything` -> REJECT (missing index integer)
    - `- [check: must_haves.truths[99]] ...` where `truths` has 3 entries -> REJECT at evaluator-construction time (out-of-bounds index)
    - `- [check: must_haves.unknown_field[0]] ...` -> REJECT (scope not in {truths, artifacts, key_links})

    Add a 1-sentence forward-pointer: "The planner-validation stage emits `state.slice.validation_failed` with `reason='acceptance_criteria_annotation_missing'` or `'acceptance_criteria_annotation_out_of_bounds'`; replan-iteration triggered. v15 Build Core Commands implements the parser."

    ### Section 4 — Gate Evaluation Order (PRF-05)

    Heading: `## Gate Evaluation Order (PRF-05)`.

    1-paragraph intro: gates fire at three boundaries — task end, Step end, Slice end — in deterministic order. Each boundary has its own evaluator set and its own event emission. The harness MUST evaluate IN this order; cross-boundary skips are forbidden.

    Sub-section `### Numbered protocol`:

    Render verbatim:

    1. **task-end** (the moment the agent signals task complete — see "Strike trigger" in Section 6 for the exact signals):
       1. Run the task's `<verify><automated>` bash block with timeout 120s. Capture exit code, stdout (≤2KB), stderr (≤2KB).
       2. For each bullet in `<acceptance_criteria>`: parse the `[check: …]` annotation; dispatch to the indexed evaluator; record per-bullet verdict.
       3. Compute `task_overall_verdict` server-side from per-bullet verdicts + `<verify>` exit code: any `fail` -> task fails; else if all `pass` -> task passes; else `flag` or `omitted` per gsd-2 vocabulary.
       4. On `fail`: increment strike counter for the failing `(task_id, check_id)` tuple (see Section 6) and BLOCK advancement to next task (PRF-07 — Section 5).
       5. On `pass | flag | omitted`: emit `state.step.task_verify_completed` with the task verdict; advance to next task in the Step.

    2. **Step-end** (after the Step's final task in DAG order passes):
       1. Evaluate every entry in frontmatter `must_haves.truths` via the bash/python evaluator (Section 2 dispatch table).
       2. Evaluate every entry in frontmatter `must_haves.artifacts` via file existence + `wc -l` >= `min_lines`.
       3. Evaluate every entry in frontmatter `must_haves.key_links` via `grep -E "$pattern" "$from"` confirming a reference to `to`.
       4. Compute `step_overall_verdict` server-side from the three sub-arrays' per-entry verdicts: any `fail` -> Step fails; else server-side compute pass / flag / omitted.
       5. Write `stepN-VERIFY.json` (per-Step machine-readable artifact — Pydantic StepVerifyResult, Section 7) into the slice's worktree at `slices/N-name/stepN-VERIFY.json` (where N is the Step's numeric ordinal from step_id).
       6. On `fail`: increment strike counter for each failing `(task_id, check_id)` (Step-scope check_ids use `task_id=null` for Step-level evaluators); BLOCK advancement to next Step.
       7. On `pass | flag | omitted`: emit `state.step.step_verify_completed` (rides StepVerifyCompleted payload, Section 7); advance to next Step.

    3. **Slice-end** (after the Slice's final Step in DAG order passes):
       1. Execute `slices/N-name/slice-verification.sh` with timeout 600s. Capture exit code, stdout/stderr.
       2. The script aggregates Step-level evidence (reads each `stepN-VERIFY.json`) + runs cross-Step integration checks (free-form bash).
       3. On non-zero exit: Slice fails; BLOCK Slice close.
       4. On exit 0: invoke the deterministic projector to render `N-VERIFICATION.md` (rolled-up 10-column truth table, Section 8) from all `stepN-VERIFY.json` files + `gate_strike` events in the Slice.
       5. Emit `state.slice.slice_verify_completed` (rides SliceVerifyCompleted payload, Section 7); advance to Slice close (commit + worktree merge).

    Add a 1-line note: "Cross-boundary skips are forbidden. The harness MUST NOT evaluate Step-end before all tasks have evaluated; MUST NOT evaluate Slice-end before all Steps. v14 enforces via FSM state transitions in `src/state_daemon/middleware.py`."

    Sub-section `### Timeouts and overrides`:
    Render verbatim:
    - "**Per-Step `<verification>` bash-block timeout default: 120s.** Slice frontmatter MAY override via `verify: {step_timeout_s: int}`."
    - "**Slice-level `slice-verification.sh` timeout default: 600s.** Slice frontmatter MAY override via `verify: {slice_timeout_s: int}`."
    - "Timeout -> `fail` verdict; the timeout event is `state.step.gate_strike` with `eval_evidence: 'timeout after Ns'` and the check_id of the timing-out evaluator."

    ### Section 5 — tool.execute.before Write-Block Stack (PRF-07)

    Heading: `## tool.execute.before Write-Block Stack (PRF-07)`.

    1-paragraph intro: the canonical "fail blocks advancement" enforcer is the `tool.execute.before` plugin hook. Every proposed Write/Edit passes through a deterministic four-layer stack inside the daemon's HTTP middleware. Each layer either rejects (with a structured reason + event emission) or falls through to the next.

    Sub-section `### Layer order (deterministic, top-to-bottom)`:

    Render as a numbered list verbatim:

    1. **Layer 1 — `files_modified` allowlist (SRP-04)**: target path must match an exact-path or glob entry in the Step's frontmatter `files_modified`. Reject -> emit `state.step.scope_deviation` (see SCOPE-PROHIBITION.md). Fall through on match.
    2. **Layer 2 — Phase 403 immutability check (PAP-05)**: if target is `*/stepNPLAN.md`, apply Phase 403's diff-the-proposed-write enforcer (immutable subset = `must_haves`, `<verify>`, `<acceptance_criteria>`, `<done>`, `<options>`, `<files>`, `<objective>`, `<success_criteria>`, `<interfaces>`, frontmatter, parent `<threat_model>` minus `<discovered_threats>` append-only carve-out). Reject -> emit `state.step.plan_edit_blocked` (see PLAN-AS-PROMPT.md §6). Fall through on no immutable diff.
    3. **Layer 3 — prohibited-language scan (SRP-02)**: scan proposed content for `\b(v1|simplified|placeholder|todo|fixme|future)\b` (case-insensitive); tracking-issue exception via EXCEPTION_RE; spec-doc allowlist via `.planning/**/*.md` path glob. Reject -> emit `state.step.scope_check` (see SCOPE-PROHIBITION.md). Fall through on clean.
    4. **Layer 4 — gate-failing next-task block (PRF-07)**: if the current Step's most recent gate verdict was `fail` AND target is in the NEXT task's `<files>` (determined by DAG ordering + `<files>` membership), reject -> emit `state.step.gate_strike` with `check_type='task_advancement_blocked'` and the check_id of the failing evaluator from the prior task-end gate. Fall through on no gate-failure or non-next-task target.

    "**Fall-through to allow:** if all four layers fall through, the Write/Edit is allowed; the daemon's middleware reports `allow` to the plugin's `tool.execute.before` hook; the plugin returns control to opencode and the tool executes."

    Sub-section `### Sequence diagram (Mermaid)`:
    Render a Mermaid sequence diagram:

    ```mermaid
    sequenceDiagram
      participant Agent as Executor (opencode)
      participant Plugin as @state/opencode-plugin
      participant Daemon as state-daemon middleware
      participant Events as Event Store (SQLite)

      Agent->>Plugin: tool.execute.before (Write/Edit)
      Plugin->>Daemon: POST /hook/tool-execute-before {target, content}
      Daemon->>Daemon: Layer 1: files_modified allowlist
      alt Layer 1 reject
        Daemon->>Events: state.step.scope_deviation
        Daemon-->>Plugin: {decision: "reject", reason}
      else fall through
        Daemon->>Daemon: Layer 2: Phase 403 immutability (if stepNPLAN.md)
        alt Layer 2 reject
          Daemon->>Events: state.step.plan_edit_blocked
          Daemon-->>Plugin: {decision: "reject", reason}
        else fall through
          Daemon->>Daemon: Layer 3: prohibited-language scan
          alt Layer 3 reject (no tracking-issue exception)
            Daemon->>Events: state.step.scope_check (tier=advisory)
            Daemon-->>Plugin: {decision: "reject", reason}
          else fall through
            Daemon->>Daemon: Layer 4: gate-failing next-task block
            alt Layer 4 reject (prior gate failed + target is next-task)
              Daemon->>Events: state.step.gate_strike (check_type=task_advancement_blocked)
              Daemon-->>Plugin: {decision: "reject", reason}
            else fall through
              Daemon-->>Plugin: {decision: "allow"}
            end
          end
        end
      end
      Plugin-->>Agent: hook result (allow or reject)
    ```

    "**Authoritative ordering:** prose protocol (Section 5 numbered list) is authoritative; diagram is supplementary. If the diagram contradicts the prose, the prose wins. v14 implementers MUST cross-check both before shipping the middleware stack."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` Section 2 (frontmatter schema) — Pydantic MustHaves/ArtifactCheck/KeyLink classes already rendered; quote VERBATIM here in Section 2, do NOT re-derive.
        - Known: `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` lines 25-46 — must_haves block example + key_links example; use as the illustrative example throughout Section 2.
        - Known: `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` Section 7 (PAP-05 diff-the-proposed-write enforcer) — the immutable subset list is consumed verbatim in Section 5 Layer 2; quote with cite.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md | head -40` — confirms heading hierarchy depth used in v41 spec docs.
        - Grep pattern: `grep -nE "model_config = ConfigDict" /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` — locates the verbatim Pydantic class rendering pattern.
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<decisions>` Gate-shapes subsection — verbatim source for ANNOTATION_RE + the four-bullet `<acceptance_criteria>` example.
        - 404-CONTEXT.md `<decisions>` Strike-counter semantics subsection — verbatim source for Section 6 (Task 2; cited here for cross-reference).
        - 404-CONTEXT.md `<decisions>` SRP-04 files_modified enforcement subsection — verbatim source for Section 5 Layer 1 description.
        - 404-CONTEXT.md `<specifics>` "Bullet-to-must_haves index binding preserves PRF-04 purity" — informs Section 3 rationale prose.
        - Phase 403 PLAN-AS-PROMPT.md §6 Diff-the-proposed-write enforcement — Layer 2 of the stack inherits this exact mechanism; cite the section.
        - workflow-docs-from-gsd-2/quality-enforcement.md §0 Correction 2 Vocabulary 2 — `pass | flag | omitted` 3-state extended to 4-state with `fail` per 404-CONTEXT.md `<specifics>`.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's PRF dispatcher unit tests will assert against the Pydantic class definitions in this spec as fixtures; this spec doc is the contract those tests assert against.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 280)}' \
        && grep -qE "^# Boolean Proof Gate" "$F" \
        && grep -qE "^## must_haves Evaluator Dispatch" "$F" \
        && grep -qE "^## Acceptance-Criteria Index-Binding" "$F" \
        && grep -qE "^## Gate Evaluation Order" "$F" \
        && grep -qE "^## tool.execute.before Write-Block Stack" "$F" \
        && grep -q "ANNOTATION_RE" "$F" \
        && grep -q 'class MustHaves' "$F" \
        && grep -q 'class ArtifactCheck' "$F" \
        && grep -q 'class KeyLink' "$F" \
        && grep -q 'extra="forbid"' "$F" \
        && grep -q "task-end" "$F" \
        && grep -q "Step-end" "$F" \
        && grep -q "Slice-end" "$F" \
        && grep -q "Layer 1" "$F" \
        && grep -q "Layer 2" "$F" \
        && grep -q "Layer 3" "$F" \
        && grep -q "Layer 4" "$F" \
        && grep -q "scope_deviation" "$F" \
        && grep -q "plan_edit_blocked" "$F" \
        && grep -q "scope_check" "$F" \
        && grep -q "gate_strike" "$F" \
        && grep -q "REJECT" "$F" \
        && grep -q "120s" "$F" \
        && grep -q "600s" "$F" \
        && grep -q "step_timeout_s" "$F" \
        && grep -q "slice_timeout_s" "$F" \
        && grep -q "sequenceDiagram" "$F" \
        && ! grep -q "state.teach" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[0]] File exists at `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` with ≥280 lines after Task 1 (Task 2 extends to ≥550).
    - [check: must_haves.truths[0]] H1 `# Boolean Proof Gate` present.
    - [check: must_haves.truths[1]] All four `must_haves` evaluator types documented in Section 2's dispatch table (truths/bash, truths/python, artifacts, key_links) with their pure-machine evaluators.
    - [check: must_haves.truths[2]] ANNOTATION_RE rendered verbatim in Section 3.
    - [check: must_haves.truths[3]] Gate evaluation order numbered protocol covers task-end -> Step-end -> Slice-end (grep-verifiable headers).
    - [check: must_haves.truths[16]] tool.execute.before write-block four-layer stack rendered with Layer 1..Layer 4 headings + scope_deviation / plan_edit_blocked / scope_check / gate_strike events.
    - [check: must_haves.truths[15]] Per-Step timeout 120s and Slice-level timeout 600s pinned with the verify: {step_timeout_s, slice_timeout_s} override mechanism documented.
    - [check: must_haves.truths[17]] Mermaid sequence diagram present (grep `sequenceDiagram`).
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: must_haves.key_links[0]] STEP-PLAN-FORMAT.md cited (key_link from PROOF-GATE.md to Phase 403 format spec).
    - [check: must_haves.key_links[1]] PLAN-AS-PROMPT.md cited for PAP-05 Layer 2 mechanism.
    - [check: verify_automated] File contains no `state.teach.` references (Build-mode isolation).
    - [check: must_haves.truths[2]] At least 5 REJECT counterexamples in Section 3 (grep -c "REJECT" returns ≥5).
  </acceptance_criteria>

  <done>
    Sections 1–5 of PROOF-GATE.md authored: file header + must_haves evaluator dispatch (PRF-01, PRF-04) + acceptance-criteria index-binding (PRF-02) + gate evaluation order (PRF-05) + tool.execute.before write-block stack (PRF-07). Task 2 will add the strike counter (PRF-06), the Pydantic StepVerifyResult + GateStrike + GateResolved + StepVerifyCompleted + SliceVerifyCompleted event payloads, the N-VERIFICATION.md column schema (PRF-03), and the cross-references closing section.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append PROOF-GATE.md sections 6-10 (strike counter, Pydantic event payloads, StepVerifyResult, N-VERIFICATION.md column schema, cross-references)</name>
  <files>
    .planning/milestones/v41/phases/404/specs/PROOF-GATE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file — Task 1 output; this task appends to it)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md lines 22-105 (Strike-counter semantics subsection — verbatim source for Section 6; lines 180-260 Gate shapes subsection — verbatim source for StepVerifyResult + N-VERIFICATION.md column schema)
    - .planning/milestones/v41/REQUIREMENTS.md lines 67-69 (PRF-06, PRF-07 verbatim)
    - .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md (full file — Pydantic event-class rendering pattern; this spec mirrors that pattern)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "compaction.snapshot_taken" — GateStrike.snapshot_event_id cross-link source)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/quality-enforcement.md (search "§7.1" — EvidenceJSON schema v1 inspiration for StepVerifyResult; "§3.2" — formatFailureContext 2KB/check 10KB/total truncation; "§0 Correction 2 Vocabulary 2" — pass|flag|omitted 3-state)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/loop-control.md (search "§0 Correction 1" — four distinct counters at four scopes; informs APG-vs-PRF independence note; "§4" — preparation-vs-execution narrowing informs strike-trigger semantics)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (search "VERIFICATION" — N-VERIFICATION.md already cataloged; stepN-VERIFY.json + slice-verification.sh ADDED by this spec)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-PLAN.md lines 380-460 (Phase 403 spec-doc plan reference for Task 2 append pattern — appends sections 7-10 to a Task 1 file)
  </read_first>

  <action>
    Append sections 6–10 to the existing `PROOF-GATE.md`. Use Edit (insert at end of file). **Concrete content from 404-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 6 — Strike Counter Semantics (PRF-06)

    Heading: `## Strike Counter Semantics (PRF-06)`.

    Sub-section `### Counter scope`:
    Render verbatim:
    - "**Counter scope: per `(task_id, check_id)` tuple.** Finest analog to gsd-2's per-`runAgentLoop`-invocation `consecutiveAllToolErrorTurns` (`gsd-2/packages/pi-agent-core/src/agent-loop.ts:191`)."
    - "Each failing `must_haves` check — one truth assertion, one artifact entry, one key_link entry — has its own 6-strike chain."
    - "Chains for different checks do not poison each other. Max audit clarity; agent sees per-check escalation."
    - "Step-level evaluators (where the failing check is not bound to a specific task) use `task_id=null` in the tuple; the chain key becomes `(null, check_id)`."

    Sub-section `### Reset rule`:
    Render verbatim:
    - "**Continue counting across the clear+reinject tier.** Literal D-8 reading: 'human gate at strike 6 **total**.'"
    - "Strike 3 fires clear+reinject (single shot); strike 4 is the next failed eval after the reinjected agent re-attempts the same `(task_id, check_id)` pair."
    - "Diverges from gsd-2's `consecutiveAllToolErrorTurns = 0`-on-success pattern (`agent-loop.ts:191`), but D-8 already diverges from gsd-2 by introducing the reinject tier at all — the divergence is principled, not accidental."
    - "**On `(task_id, check_id)` close (pass/flag/omitted verdict):** emit `state.step.gate_resolved` and remove the chain from the in-memory counter; subsequent failures on the SAME tuple start fresh from strike 1 in a new chain."

    Sub-section `### Strike trigger (completion-claim boundary)`:
    Render verbatim:
    - "A strike accrues if-and-only-if:"
    - "1. The agent signals 'task complete' via either (a) attempting any Write/Edit targeting a file owned by the **next** task (PRF-07 boundary detection, Section 5 Layer 4), OR (b) explicitly calling the `complete_task` MCP tool (analog of gsd-2's `complete_task` at `gsd-2/src/resources/extensions/gsd/tools/complete-task.ts`); AND"
    - "2. The harness runs the task's `<verify><automated>` + `<acceptance_criteria>` + frontmatter `must_haves.*` pure-machine evaluators; AND"
    - "3. At least one evaluator returns `fail`."
    - "**Mid-task incidental gate evaluations** (e.g., harness running checks against WIP artifacts mid-Write) do **not** strike. Mirrors gsd-2's preparation-vs-execution narrowing (`agent-loop.ts:324-329`, issue #3618): execution failures are not strikes; only declared-completion-then-still-failing pattern strikes."

    Sub-section `### Escalation ladder (the 6-strike chain)`:

    Render as a markdown table:

    | Strike # | Tier | Harness action | Event emitted |
    |---------|------|----------------|---------------|
    | 1 | advisory | Inject system advisory naming the failing check_id + remediation hint | `state.step.gate_strike` (tier=advisory, strike_number=1) |
    | 2 | advisory | Same advisory; updated count in the message | `state.step.gate_strike` (tier=advisory, strike_number=2) |
    | 3 | advisory + reinject trigger | Inject advisory; then on agent retry that still fails the same `(task_id, check_id)`, fire compaction snapshot + clear context + reinject the PLAN with the focused failing-check prompt; record `snapshot_event_id` cross-link to the `compaction.snapshot_taken` event | `state.step.gate_strike` (tier=reinject, strike_number=3, snapshot_event_id=<id>) |
    | 4 | advisory (post-reinject) | Inject advisory; counter is at 4 of 6 | `state.step.gate_strike` (tier=advisory, strike_number=4) |
    | 5 | advisory | Inject advisory; warning that next failure fires human gate | `state.step.gate_strike` (tier=advisory, strike_number=5) |
    | 6 | human_gate (force-stop) | Force-stop the session; surface a human gate via opencode `question` tool with the failing check_id, the agent_response_summary, the eval_evidence excerpts, and the 6-strike chain audit | `state.step.gate_strike` (tier=human_gate, strike_number=6) |

    "**On strike 6 human resolution:** human picks 'override' or 'reject'. Override -> emit `state.step.gate_resolved` with `resolution='human_override'` and force the check to `pass`; reject -> emit `state.step.gate_resolved` with `resolution='human_reject'` and the Slice transitions to `pending_replan` (handled in SCOPE-PROHIBITION.md SRP-05)."

    Sub-section `### APG-vs-PRF counter independence`:
    Render verbatim:
    - "gsd-2's `loop-control.md` §0 Correction 1 explicitly forbids conflating distinct counters — gsd-2 has FOUR separate counters at four scopes."
    - "State follows the same principle:"
    - "  - `paralysis_event` chain (APG): 3 advisory -> clear+reinject -> 3 more -> human gate. Per task."
    - "  - `gate_strike` chain (PRF): 3 advisory -> clear+reinject -> 3 more -> human gate. Per `(task_id, check_id)`."
    - "  - Each can independently reach force-stop."
    - "  - The `harness_intervention` event (HRN-05, owned by Phase 406) is the umbrella; both `paralysis_event` and `gate_strike` cite it as `trigger_reason`."

    ### Section 7 — Pydantic Event Payloads + StepVerifyResult Schema

    Heading: `## Pydantic Event Payloads + StepVerifyResult Schema`.

    1-paragraph intro: this section renders the four new Pydantic event payloads + the `StepVerifyResult` schema that the harness writes to `stepN-VERIFY.json`. All ride the v40 EventEnvelope outer shape (see `<interfaces>` Excerpt B); all use `model_config = ConfigDict(extra="forbid")`.

    Sub-section `### state.step.gate_strike (GateStrike — PRF-06)`:
    Trigger: "Emitted on every strike accrual (per the trigger rules in Section 6)."
    Render Pydantic class verbatim from 404-CONTEXT.md `<decisions>` Strike-counter semantics subsection:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict
    from typing import Literal

    class GateStrike(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str | None                            # null for Step-level evaluators
        step_id: str
        slice_id: str
        check_id: str                                  # truth_idx | artifact_idx | key_link_idx | verify_automated | acceptance_idx
        check_type: Literal["truth", "artifact", "key_link", "verify_automated", "acceptance"]
        strike_number: int                             # 1..6
        tier: Literal["advisory", "reinject", "human_gate"]
        agent_response_summary: str                    # <= 2KB excerpt (gsd-2 truncation convention)
        eval_evidence: str                             # <= 2KB excerpt of the failed pure-machine output
        triggered_at: datetime                         # UTC, ISO-8601
        session_id: str
        snapshot_event_id: str | None                  # set when tier == "reinject" (cross-link to compaction.snapshot_taken)
    ```

    Sub-section `### state.step.gate_resolved (GateResolved)`:
    Trigger: "Emitted on `(task_id, check_id)` chain close — verdict transitions to pass/flag/omitted, OR human resolution at strike 6."
    Render Pydantic class:

    ```python
    class GateResolved(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str | None
        step_id: str
        slice_id: str
        check_id: str
        check_type: Literal["truth", "artifact", "key_link", "verify_automated", "acceptance"]
        final_strike_count: int                        # 0 if passed on first eval; up to 6 if human-resolved
        resolution: Literal["pass", "flag", "omitted", "human_override", "human_reject"]
        eval_evidence_final: str                       # <= 2KB excerpt of the resolving eval output
        resolved_at: datetime
        session_id: str
        gate_strike_event_ids: list[str]               # full audit chain (event ids of every GateStrike in the closed chain)
    ```

    Sub-section `### state.step.step_verify_completed (StepVerifyCompleted)`:
    Trigger: "Emitted at Step-end after the `stepN-VERIFY.json` file is written. Carries the path + the server-side recomputed overall_verdict."
    Render Pydantic class:

    ```python
    class StepVerifyCompleted(BaseModel):
        model_config = ConfigDict(extra="forbid")
        step_id: str
        slice_id: str
        verify_json_path: str                          # absolute path to slices/N-name/stepN-VERIFY.json
        overall_verdict: Literal["pass", "flag", "omitted", "fail"]
        outcome: Literal["continue", "retry", "pause"]
        completed_at: datetime
        session_id: str
    ```

    Sub-section `### state.slice.slice_verify_completed (SliceVerifyCompleted)`:
    Trigger: "Emitted at Slice-end after `slice-verification.sh` exits 0 AND `N-VERIFICATION.md` is written by the projector."
    Render Pydantic class:

    ```python
    class SliceVerifyCompleted(BaseModel):
        model_config = ConfigDict(extra="forbid")
        slice_id: str
        verification_md_path: str                      # absolute path to slices/N-name/N-VERIFICATION.md
        slice_verification_sh_exit_code: int           # always 0 (non-zero blocks emission)
        completed_at: datetime
        session_id: str
    ```

    Sub-section `### StepVerifyResult JSON schema (stepN-VERIFY.json)`:
    Trigger: "The on-disk per-Step machine-readable artifact. Pydantic-validated; schema-versioned for migration."
    Render verbatim from 404-CONTEXT.md Gate shapes subsection:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict
    from typing import Literal

    class StepVerifyResult(BaseModel):
        model_config = ConfigDict(extra="forbid")
        schema_version: Literal[1]                     # bump literal to migrate; old files surface as parse errors
        step_id: str
        slice_id: str
        timestamp: datetime
        must_haves: "MustHavesResult"                  # nested
        acceptance_criteria: list["AcceptanceResult"]  # one entry per bullet, bound by ANNOTATION_RE index
        verify_automated: "VerifyAutomatedResult"      # bash exit code + stdout/stderr <= 2KB
        overall_passed: bool                           # server-side recomputed; NEVER trust an LLM-emitted aggregate
        overall_verdict: Literal["pass", "flag", "omitted", "fail"]   # extends gsd-2's pass|flag|omitted with "fail"
        outcome: Literal["continue", "retry", "pause"] # mirrors gsd-2 EvidenceJSON outcome discriminator

    class MustHavesResult(BaseModel):
        model_config = ConfigDict(extra="forbid")
        truths: list["CheckResult"]
        artifacts: list["CheckResult"]
        key_links: list["CheckResult"]

    class CheckResult(BaseModel):
        model_config = ConfigDict(extra="forbid")
        index: int
        verdict: Literal["pass", "flag", "omitted", "fail"]
        evidence_excerpt: str                          # <= 2KB (gsd-2 truncation convention)
        strike_count_at_close: int                     # final strike count when this check was closed
        gate_strike_event_ids: list[str]               # full audit chain

    class AcceptanceResult(BaseModel):
        model_config = ConfigDict(extra="forbid")
        bullet_index: int                              # 0-indexed position in <acceptance_criteria>
        annotation: str                                # the literal [check: ...] annotation string
        bound_evaluator: str                           # e.g., "must_haves.truths[0]" or "verify_automated"
        verdict: Literal["pass", "flag", "omitted", "fail"]
        evidence_excerpt: str

    class VerifyAutomatedResult(BaseModel):
        model_config = ConfigDict(extra="forbid")
        command: str                                   # the bash one-liner from <verify><automated>
        exit_code: int
        stdout_excerpt: str                            # <= 2KB
        stderr_excerpt: str                            # <= 2KB
        duration_ms: int
        timed_out: bool
    ```

    Sub-section `### Server-side recomputation of overall_passed`:
    Render verbatim:
    - "**Server-side recomputation is NON-NEGOTIABLE.** Mirrors gsd-2's defensive pattern (`verification-evidence.ts` + `eval-review-schema.ts:210-227`): the harness recomputes `overall_passed` from sub-fields after writing the file."
    - "**Negative example (REJECTED at parse time):**"
    - "  An agent-emitted `overall_passed: true` with `must_haves.truths[0].verdict: fail` is rejected by the StepVerifyResult parser. v14 raises `ValidationError`."
    - "**Positive example (ACCEPTED):**"
    - "  All `must_haves.*.verdict in {pass, flag, omitted}` AND all `acceptance_criteria.*.verdict in {pass, flag, omitted}` AND `verify_automated.exit_code == 0` -> recomputed `overall_passed = True`."

    Sub-section `### Bounded truncation`:
    Render verbatim:
    - "**2KB per check, 10KB total** per `stepN-VERIFY.json`. Mirrors gsd-2's `formatFailureContext` (`verification-gate.ts:115-142`)."
    - "Truncation marker: `[... truncated <N> bytes ...]` where N is the byte count omitted."
    - "Same truncation discipline applies to `formatEvidenceTable` markdown rendering in N-VERIFICATION.md."
    - "The truncation utility is harness-owned (not agent-controllable); the marker is added by the utility."

    Sub-section `### omitted-if-empty four-state vocabulary`:
    Render verbatim:
    - "**pass | flag | omitted | fail** — the four-state vocabulary."
    - "Mirrors gsd-2 (`tools/complete-slice.ts:65, 387-424`): a check with no specified evaluator (e.g., a Step whose `must_haves.key_links` is empty) closes with `omitted`, NOT `pass`."
    - "The omitted state preserves audit clarity ('we checked and the criterion doesn't apply') and is distinct from `pass` ('we checked and confirmed')."
    - "**`fail` is added** for the agent-loop's machine verdict; `pass | flag | omitted` are the closure verdicts (gsd-2's three) carried into `N-VERIFICATION.md`."

    ### Section 8 — N-VERIFICATION.md Rolled-Up Truth-Table Column Schema (PRF-03)

    Heading: `## N-VERIFICATION.md Rolled-Up Truth-Table Column Schema (PRF-03)`.

    1-paragraph intro: at Slice-end, after every Step's `stepN-VERIFY.json` is written, the harness invokes a deterministic projector that renders the rolled-up `N-VERIFICATION.md` markdown table. The projector subscribes to `state.step.step_verify_completed` and `state.step.gate_strike` events; aggregates all Step results in the Slice; renders the table. The table is the WIDE audit-traceable view; the per-Step JSON files are the authoritative machine-readable evidence.

    Sub-section `### Column schema (10 columns)`:

    Render verbatim from 404-CONTEXT.md:

    | Column | Source field | Notes |
    |--------|--------------|-------|
    | `step_id` | `StepVerifyResult.step_id` | One row per check, grouped by step |
    | `task_id` | gate_strike chain (or `null` for Step-level) | When the strike chain references a specific task |
    | `check_id` | `CheckResult.index` formatted as `truths[0]` etc. | Stable across runs |
    | `scope` | `truth \| artifact \| key_link \| verify_automated \| acceptance` | The PRF-01 / PRF-02 check type |
    | `source_expr` | Pydantic dump of the must_haves entry | The actual expression being evaluated |
    | `verdict` | `CheckResult.verdict` (`pass \| flag \| omitted \| fail`) | Extends gsd-2's three-state with `fail` |
    | `strike_count_at_close` | `CheckResult.strike_count_at_close` | 0 if the check passed on first eval |
    | `gate_strike_event_ids` | `CheckResult.gate_strike_event_ids` | Full audit chain (newline-joined event ids) |
    | `evidence_excerpt` | `CheckResult.evidence_excerpt` (<= 2KB) | gsd-2-style bounded |
    | `timestamp` | `StepVerifyResult.timestamp` | ISO-8601 UTC |

    Sub-section `### Projector behavior`:
    Render verbatim:
    - "Generated by a deterministic projector at Slice-verify-stage entry."
    - "Handler subscribes to `state.step.step_verify_completed` events; aggregates all step results in the Slice; renders the markdown."
    - "Ordering: rows sorted by Step DAG topology (depends_on traversal), then by check_id index ascending within each Step."
    - "Truncation: per-row `evidence_excerpt` <= 2KB; whole-file size unbounded (the per-Step JSON files cap evidence; the markdown rolls up)."

    Sub-section `### omitted rows`:
    "Checks with `verdict='omitted'` ARE included in the table (audit clarity); they show `strike_count_at_close=0` and `gate_strike_event_ids=[]`. The projector MUST NOT skip them."

    Sub-section `### Slice-level <verification> artifact paths`:
    Render verbatim:
    - "**Per-Step `<verification>` bash block** lives inside `stepNPLAN.md` (Phase 403 STEP-PLAN-FORMAT.md §XML Body Section Catalog -> `<verification>`). Runs at Step end (before commit). Block content is bash only (no Python; if a Python check is needed, the Step author writes a `.py` file in `files_modified` and the bash block invokes `python3 path.py`). Block is **immutable** under PAP-03 / Phase 403's mutability matrix."
    - "**Slice-level `slice-verification.sh`** is co-located with `N-VERIFICATION.md` at `slices/N-name/slice-verification.sh`. Runs at Slice end (the verify-slice stage). Aggregates Step-level evidence + runs cross-Step integration checks. Single bash script; pure-machine."

    ### Section 9 — Artifact Catalog Additions

    Heading: `## Artifact Catalog Additions`.

    1-paragraph intro: this section enumerates the new on-disk artifacts Phase 404 adds to the canonical Slice folder layout (per v40 ARTIFACT-CATALOG.md). Phase 406's harness rollup cross-references this list.

    Render as a markdown list:

    - **`slices/N-name/stepN-VERIFY.json`** (one per Step, machine-readable). Pydantic-validated against StepVerifyResult schema v1. Authoritative per-Step evidence.
    - **`slices/N-name/slice-verification.sh`** (one per Slice, executable bash). Pure-machine cross-Step integration checks. Authored at plan-slice end; immutable post-execute-slice start.
    - **`slices/N-name/N-VERIFICATION.md`** (one per Slice, deterministic projector output). Wide audit-traceable rolled-up truth table. Re-renderable from event store at any time (projector is idempotent).

    "Forward-pointer: v40 ARTIFACT-CATALOG.md will receive a `## v41 Amendment` block in Plan 04 (this phase) registering these three artifact types."

    ### Section 10 — Cross-references

    Heading: `## Cross-references`.

    Bullet list:
    - **Sibling spec — analysis paralysis:** `ANALYSIS-PARALYSIS-GUARD.md` (Plan 02) defines the APG counter — independent from PRF per Section 6 §APG-vs-PRF; both feed `harness_intervention` (Phase 406 HRN-05).
    - **Sibling spec — scope:** `SCOPE-PROHIBITION.md` (Plan 03) defines layers 1 + 3 of the tool.execute.before stack (files_modified allowlist + prohibited-language scan); Layer 4 (gate-failing next-task block) is owned by this spec.
    - **Phase 403 carry-forward — format:** `STEP-PLAN-FORMAT.md` §Frontmatter Schema (STP-02) provides the `MustHaves` / `ArtifactCheck` / `KeyLink` Pydantic classes this spec evaluates against.
    - **Phase 403 carry-forward — mutability:** `PLAN-AS-PROMPT.md` §Mutability Matrix (PAP-03) locks every `<verify>` block; §6 (PAP-05) is Layer 2 of the tool.execute.before stack.
    - **Phase 402 carry-forward — compaction:** `CONTEXT-PROTOCOL.md` §Compaction (CTX-05/06) is the source of the `compaction.snapshot_taken` event that GateStrike.snapshot_event_id cross-links when tier='reinject'.
    - **v40 baseline:** `EVENT-TAXONOMY.md` naming convention `state.{tier}.{action}`; this spec adds `state.step.gate_strike`, `state.step.gate_resolved`, `state.step.step_verify_completed`, `state.slice.slice_verify_completed`. Plan 04 (this phase) appends a `## v41 Amendment` block to v40 EVENT-TAXONOMY.md registering these.
    - **v40 baseline — artifacts:** `ARTIFACT-CATALOG.md` will receive Plan 04 amendment registering `stepN-VERIFY.json`, `slice-verification.sh`, and confirming `N-VERIFICATION.md` column schema is owned by this spec.
    - **Phase 406 forward:** `harness_intervention` (HRN-05) umbrella event aggregates `gate_strike` + `paralysis_event` + `scope_check` + `scope_deviation_request` + `split_recommendation`; the 4-tier intervention ladder (HRN-04) cites this spec for tier-3 (force clear+reinject) and tier-4 (force-stop+human gate).
    - **gsd-2 lineage:** quality-enforcement.md §7.1 (EvidenceJSON schema), §3.2 (truncation), §0 Correction 2 Vocabulary 2 (pass|flag|omitted); loop-control.md §0 Correction 1 (counter independence), §4 (preparation-vs-execution narrowing); complete-task.ts:73-77, 339-355 (field binding); complete-slice.ts:65, 387-424 (omitted-if-empty); verification-evidence.ts (server-side recomputation).

    Add closing 1-paragraph note: "v14 Build Kernel implements the strike counter (per-(task_id, check_id) tuple, in-memory cache backed by event store), the bash classifier dispatcher, the prohibited-language scanner, the files_modified allowlist checker, the deterministic N-VERIFICATION.md projector, the bounded-truncation utility, and the four event handlers. v15 Build Core Commands implements the research-slice planner-validation stage that checks `<acceptance_criteria>` bullet annotations against ANNOTATION_RE; the verify-slice stage that runs `slice-verification.sh` and writes `N-VERIFICATION.md`. Phase 405's deviation framework consumes strike-counter `tier=human_gate` events. Phase 406's harness rollup cites this spec for the layered diagram's tier-3 and tier-4 intervention behaviors."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` Sections 3-5 — Pydantic event-class rendering pattern (per-event H3 subsection, trigger paragraph, fenced Python class); mirror that structure for the four event payloads in Section 7.
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §5 (CompactionSnapshot) — Pydantic class rendering pattern with field comments; mirror for StepVerifyResult.
        - Grep pattern: `grep -nE "^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` — confirms Task 1's Section headings before appending (run first; expected: Sections 1-5 already present).
        - Grep pattern: `grep -nE "compaction.snapshot_taken" /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — locates exact event-type string for the GateStrike.snapshot_event_id cross-reference.
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<decisions>` Strike-counter semantics subsection — verbatim source for Section 6 (every bullet).
        - 404-CONTEXT.md `<decisions>` Gate shapes subsection — verbatim source for StepVerifyResult + N-VERIFICATION.md column schema in Sections 7-8.
        - quality-enforcement.md §7.1 — EvidenceJSON schema v1; informs StepVerifyResult shape.
        - quality-enforcement.md §3.2 — formatFailureContext 2KB/10KB truncation; verbatim in Section 7 §Bounded truncation.
        - quality-enforcement.md §0 Correction 2 Vocabulary 2 — pass|flag|omitted three-state; extended to four-state with `fail`.
        - loop-control.md §0 Correction 1 — four-counter independence; verbatim in Section 6 §APG-vs-PRF.
        - loop-control.md §4 — preparation-vs-execution narrowing; verbatim in Section 6 §Strike trigger.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown spec. v14's StepVerifyResult parser unit tests will use this spec's Pydantic class renderings as fixtures.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 550)}' \
        && grep -qE "^## Strike Counter Semantics" "$F" \
        && grep -qE "^## Pydantic Event Payloads" "$F" \
        && grep -qE "^## N-VERIFICATION.md Rolled-Up" "$F" \
        && grep -qE "^## Artifact Catalog Additions" "$F" \
        && grep -qE "^## Cross-references" "$F" \
        && grep -q "class GateStrike" "$F" \
        && grep -q "class GateResolved" "$F" \
        && grep -q "class StepVerifyCompleted" "$F" \
        && grep -q "class SliceVerifyCompleted" "$F" \
        && grep -q "class StepVerifyResult" "$F" \
        && grep -q "class MustHavesResult" "$F" \
        && grep -q "class CheckResult" "$F" \
        && grep -q "class AcceptanceResult" "$F" \
        && grep -q "class VerifyAutomatedResult" "$F" \
        && grep -q 'schema_version: Literal\[1\]' "$F" \
        && grep -q '"pass", "flag", "omitted", "fail"' "$F" \
        && grep -q '"continue", "retry", "pause"' "$F" \
        && grep -q "snapshot_event_id" "$F" \
        && grep -q "compaction.snapshot_taken" "$F" \
        && grep -q "task_id, check_id" "$F" \
        && grep -q "completion-claim boundary" "$F" \
        && grep -q "preparation-vs-execution" "$F" \
        && grep -q "stepN-VERIFY.json" "$F" \
        && grep -q "slice-verification.sh" "$F" \
        && grep -q "N-VERIFICATION.md" "$F" \
        && grep -q "ANALYSIS-PARALYSIS-GUARD.md" "$F" \
        && grep -q "SCOPE-PROHIBITION.md" "$F" \
        && grep -q "STEP-PLAN-FORMAT.md" "$F" \
        && grep -q "PLAN-AS-PROMPT.md" "$F" \
        && grep -q "harness_intervention" "$F" \
        && grep -q "2KB" "$F" \
        && grep -q "10KB" "$F" \
        && grep -q "truncated <N> bytes" "$F" \
        && ! grep -q "state.teach" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[0]] PROOF-GATE.md >= 550 lines after this task.
    - [check: must_haves.truths[5]] Strike-counter scope per `(task_id, check_id)` tuple documented with the 6-strike escalation ladder table.
    - [check: must_haves.truths[6]] Strike trigger semantics (completion-claim boundary) rendered: signals (a) and (b) + the pure-machine eval requirement + the "mid-task incidental do not strike" rule.
    - [check: must_haves.truths[7]] APG-vs-PRF counter independence note rendered citing gsd-2 loop-control.md Correction 1.
    - [check: must_haves.truths[8]] Pydantic GateStrike class rendered verbatim with all 12 fields (task_id, step_id, slice_id, check_id, check_type Literal, strike_number int 1..6, tier Literal, agent_response_summary, eval_evidence, triggered_at, session_id, snapshot_event_id optional).
    - [check: must_haves.truths[9]] Pydantic GateResolved class rendered with the chain-close field set.
    - [check: must_haves.truths[10]] Pydantic StepVerifyCompleted and SliceVerifyCompleted classes rendered.
    - [check: must_haves.truths[11]] Bounded-truncation 2KB/check + 10KB/total + literal marker `[... truncated <N> bytes ...]` rendered.
    - [check: must_haves.truths[12]] Server-side recomputation of overall_passed rendered with positive (ACCEPTED) and negative (REJECTED) examples.
    - [check: must_haves.truths[13]] omitted-if-empty four-state vocabulary rendered citing complete-slice.ts:65, 387-424.
    - [check: must_haves.truths[14]] N-VERIFICATION.md 10-column truth-table schema rendered with each column's source field cited.
    - [check: must_haves.key_links[2]] CONTEXT-PROTOCOL.md cited for compaction.snapshot_taken cross-link.
    - [check: must_haves.key_links[3]] ARTIFACT-CATALOG.md cited in Section 9 for the new artifacts.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: verify_automated] File contains no `state.teach.` references (Build-mode isolation).
  </acceptance_criteria>

  <done>
    PROOF-GATE.md complete — all 10 sections present. PRF-01..PRF-07 fully covered with literal Pydantic schemas (GateStrike, GateResolved, StepVerifyCompleted, SliceVerifyCompleted, StepVerifyResult + nested), 10-column N-VERIFICATION.md truth-table schema, strike-counter semantics, server-side recomputation discipline, bounded-truncation rule, omitted-if-empty four-state vocabulary, artifact catalog additions, and cross-references to sibling specs and Phase 402/403 carry-forwards.
  </done>
</task>

<task type="auto">
  <name>Task 3: Write 01-proof-gate-spec-SUMMARY.md</name>
  <files>
    .planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file — Tasks 1+2 output)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md (full file — sibling SUMMARY shape reference)
    - .planning/milestones/v41/phases/403/03-plan-as-prompt-spec-SUMMARY.md (full file — sibling SUMMARY shape reference)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory gate
  </read_first>

  <action>
    Author the per-plan SUMMARY.md. Mirror `403-02-SUMMARY.md` structure (frontmatter `phase/plan/subsystem/tags/requires/provides/affects/tech-stack/key-files/key-decisions/requirements-completed/duration/completed` + the body sections).

    1. Frontmatter (mirror 403-02-SUMMARY.md exactly):
       - `phase: 404-boolean-proof-gate-discipline-guards`
       - `plan: 01`
       - `subsystem: design-spec`
       - `tags: [proof-gate, pydantic, must-haves, strike-counter, harness, prf]`
       - `requires`: 403 (provides STEP-PLAN-FORMAT.md MustHaves/ArtifactCheck/KeyLink; PLAN-AS-PROMPT.md PAP-05 immutability), 402 (provides compaction.snapshot_taken cross-link), 400 (provides EVENT-TAXONOMY.md naming convention + FRONTMATTER-SCHEMAS.md Pydantic convention)
       - `provides`: PROOF-GATE.md — canonical boolean proof gate spec covering PRF-01..PRF-07 (>= 550 lines); GateStrike + GateResolved + StepVerifyCompleted + SliceVerifyCompleted Pydantic event payloads; StepVerifyResult schema v1 with nested MustHavesResult / CheckResult / AcceptanceResult / VerifyAutomatedResult; N-VERIFICATION.md 10-column truth-table schema; tool.execute.before write-block 4-layer stack documented (Layer 4 owned here; Layers 1+3 owned by Plan 03; Layer 2 owned by Phase 403 PAP-05); strike-counter per-(task_id, check_id) semantics with 6-strike ladder; omitted-if-empty four-state vocabulary
       - `affects`: 404-04 (event taxonomy amendment registers the four new events), v14 Build Kernel (implements strike counter + projector + bash runner + truncation utility), v15 Build Core Commands (implements verify-slice stage), Phase 405 (consumes strike-counter tier=human_gate events for deviation framework), Phase 406 (cites this spec for layer 3 + 4 of the intervention ladder)
       - `tech-stack.patterns`: ["Pydantic StepVerifyResult with extra='forbid' + schema_version Literal for migration", "Server-side recomputation of overall_passed (defensive pattern from gsd-2 verification-evidence.ts)", "Bounded truncation 2KB/check + 10KB/total with literal `[... truncated <N> bytes ...]` marker", "Four-state verdict vocabulary pass|flag|omitted|fail extending gsd-2's three-state with `fail` for the agent loop", "Per-(task_id, check_id) strike counter independent from APG paralysis counter (cites loop-control.md Correction 1)"]
       - `key-files.created`: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` (>= 550 lines)
       - `key-decisions`: render the 7-8 key locked-in design choices from 404-CONTEXT.md decisions section (strike scope per-tuple, reset-rule continues across reinject, strike-trigger at completion-claim boundary, server-side recomputation non-negotiable, 4-state vocabulary, ANNOTATION_RE bullet-binding, two-tier authoritative pair: Pydantic + prose)
       - `requirements-completed`: PRF-01..PRF-07
       - `duration`: ~25min (estimated)
       - `completed`: {date}

    2. Body sections:
       - `# Plan 404-01 Summary: PROOF-GATE.md`
       - Bold tagline (1-2 sentences summarizing the spec's contribution)
       - `## What Was Built` — 1 paragraph: PROOF-GATE.md at the canonical path; covers PRF-01..PRF-07 in 10 sections; cites Phase 403 format spec + Phase 402 compaction protocol; renders 5 Pydantic event classes + StepVerifyResult schema v1 (5 nested classes); 10-column N-VERIFICATION.md truth-table schema; 4-layer tool.execute.before write-block sequence diagram (Mermaid).
       - `## Key Decisions` — bullets (mirror 404-CONTEXT.md `<decisions>` summary)
       - `## Files Touched` — PROOF-GATE.md only
       - `## Open Items / Deferred` — bullets:
         - "Inline interpreter prefix convention (`#!python3 `) — v14 may pick one canonical form; spec accepts both per 404-CONTEXT.md Claude's Discretion."
         - "gate_strike advisory message wording — deferred to v14 per 404-CONTEXT.md Claude's Discretion."
         - "Truncation byte values (2KB/10KB) — v14 may tune if EXEMPLAR-stepNPLAN.md gates show systematically larger outputs."
         - "Strike-counter durability across daemon restart — implicit in event-sourced design; explicit rehydrate path is v14 territory."
         - "Plan 04 of this phase will append `## v41 Amendment` block to v40 EVENT-TAXONOMY.md registering the four new events: state.step.gate_strike, state.step.gate_resolved, state.step.step_verify_completed, state.slice.slice_verify_completed."
       - `## Downstream Hooks` — bullets:
         - "v14 Build Kernel implements strike counter + projector + bash-block runner + bounded-truncation utility against this spec."
         - "v15 Build Core Commands implements the research-slice planner-validation stage (ANNOTATION_RE) + verify-slice stage (slice-verification.sh + N-VERIFICATION.md projector)."
         - "Phase 405 (Deviation Rules) consumes strike-counter tier=human_gate events as input to the 4-rule deviation framework (DEV-04 human gate)."
         - "Phase 406 (Harness Rollup) cites this spec for layer 3 (force clear+reinject) and layer 4 (force-stop+human gate) of the 4-tier intervention ladder (HRN-04); harness_intervention event (HRN-05) aggregates GateStrike + ParalysisEvent + ScopeCheck."
         - "Sibling spec ANALYSIS-PARALYSIS-GUARD.md (Plan 02 of this phase) cites this spec for the APG-vs-PRF counter independence statement."
       - `## Task Commits` — placeholder for executor to fill in
       - `## Deviations from Plan` — placeholder; executor fills in actual deviations
       - `## Self-Check: PASSED` (or FAILED) — checklist of every must_haves.truth verified

    Length: 100-180 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md` — sibling SUMMARY exemplar; mirror frontmatter shape + body sections + bullet density.
        - Known: `.planning/milestones/v41/phases/403/03-plan-as-prompt-spec-SUMMARY.md` — second sibling SUMMARY exemplar to confirm consistent shape across Phase 403 plans.
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md per-plan-SUMMARY-mandatory subsection (explicit project-specific gate; SUMMARY MUST land before plan is complete).
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 80)}' \
        && grep -q "Plan 404-01" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "PROOF-GATE.md" "$F" \
        && grep -q "PRF-01" "$F" \
        && grep -q "PRF-07" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] SUMMARY exists with >= 80 lines.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: verify_automated] SUMMARY references Plan 01, the PROOF-GATE.md spec, all 7 PRF requirements covered, and forward-points to Plans 02/03/04 (sibling specs + amendment plan).
    - [check: verify_automated] All four core sections present (What Was Built, Key Decisions, Files Touched, Downstream Hooks).
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate closed for Plan 404-01.
  </done>
</task>

</tasks>

<verification>
- File `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` exists with >= 550 lines.
- File `.planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md` exists with >= 80 lines.
- All 10 H2 sections present in PROOF-GATE.md (must_haves Evaluator Dispatch, Acceptance-Criteria Index-Binding, Gate Evaluation Order, tool.execute.before Write-Block Stack, Strike Counter Semantics, Pydantic Event Payloads, N-VERIFICATION.md Rolled-Up Truth-Table Column Schema, Artifact Catalog Additions, Cross-references — plus the H1 file header).
- All 5 new Pydantic event/result classes present (GateStrike, GateResolved, StepVerifyCompleted, SliceVerifyCompleted, StepVerifyResult).
- All 4 nested StepVerifyResult sub-classes present (MustHavesResult, CheckResult, AcceptanceResult, VerifyAutomatedResult).
- All Pydantic classes use `extra="forbid"`.
- ANNOTATION_RE regex string present verbatim.
- Strike-counter scope per `(task_id, check_id)` documented.
- 6-strike escalation ladder table rendered.
- N-VERIFICATION.md 10-column truth-table schema rendered.
- tool.execute.before 4-layer stack rendered with Mermaid sequence diagram.
- Cross-references to ANALYSIS-PARALYSIS-GUARD.md (sibling Plan 02 forward), SCOPE-PROHIBITION.md (sibling Plan 03 forward), STEP-PLAN-FORMAT.md (Phase 403), PLAN-AS-PROMPT.md (Phase 403), CONTEXT-PROTOCOL.md (Phase 402), EVENT-TAXONOMY.md (v40), ARTIFACT-CATALOG.md (v40) all present.
- No `state.teach.` references.
- 2KB/check + 10KB/total truncation discipline documented with literal `[... truncated <N> bytes ...]` marker.
- Four-state verdict vocabulary `pass | flag | omitted | fail` documented.
- Outcome discriminator `continue | retry | pause` documented.
- Server-side recomputation positive + negative examples rendered.
- ANALYSIS-PARALYSIS-GUARD.md and SCOPE-PROHIBITION.md cited as sibling specs in Section 10.
</verification>

<success_criteria>
- PRF-01 (must_haves frontmatter block schema): Pydantic MustHaves/ArtifactCheck/KeyLink consumed verbatim from Phase 403; per-evaluator dispatch table renders the pure-machine evaluator for each entry type.
- PRF-02 (per-task <verify><automated> + <acceptance_criteria>): ANNOTATION_RE bullet binding rendered with at least 5 REJECT counterexamples.
- PRF-03 (Slice-level <verification> + N-VERIFICATION.md): 10-column truth-table schema rendered; per-Step `<verification>` bash + Slice-level `slice-verification.sh` both pinned with timeout defaults.
- PRF-04 (pure-machine constraint): every evaluator in the dispatch table is bash exit code / file existence / wc -l / regex grep; no LLM-as-judge anywhere; the planner-validation rejection rule for non-machine-evaluable truths is documented.
- PRF-05 (gate evaluation order): numbered protocol for task-end -> Step-end -> Slice-end with exact harness actions; cross-boundary skips forbidden.
- PRF-06 (6-strike ladder): strike-counter per-(task_id, check_id) tuple; 6-strike escalation table; reset rule "continue counting across reinject tier"; strike-trigger at completion-claim boundary; APG-vs-PRF counter independence; GateStrike + GateResolved Pydantic event payloads verbatim.
- PRF-07 (fail blocks advancement): tool.execute.before write-block 4-layer stack with Mermaid sequence diagram; Layer 4 (gate-failing next-task block) owned by this spec; Layers 1/2/3 cross-referenced to sibling specs.
- Per-plan SUMMARY.md gate closed.
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` (>= 550 lines)
- `.planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md` (>= 80 lines)

Plan 04 (v40 EVENT-TAXONOMY.md + ARTIFACT-CATALOG.md amendments) in Wave 2 can now reference this spec for the four new `state.step.gate_strike` / `state.step.gate_resolved` / `state.step.step_verify_completed` / `state.slice.slice_verify_completed` event types and the three new artifact types (`stepN-VERIFY.json`, `slice-verification.sh`, `N-VERIFICATION.md` column schema confirmation).
</output>
