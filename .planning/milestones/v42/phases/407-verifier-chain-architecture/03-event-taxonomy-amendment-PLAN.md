---
phase: 407-verifier-chain-architecture
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
autonomous: true
requirements:
  - VCH-07
must_haves:
  truths:
    - "EVENT-TAXONOMY.md (canonical v40 file at `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`) is amended APPEND-ONLY with a `## v42 Amendment — Phase 407 Verifier Event Family` block."
    - "The amendment registers ~25 new verifier event names following the namespace pattern `state.verifier.<scope>[.<sub_verifier>].<verdict>` — covering Step (4 sub-verifiers × 2 verdicts = 8) + Step composite (2) + Slice/Stage/Arc rollups (3 × 2 = 6) + Cross-Tier (2) + auxiliary events (warning per sub, verdict_changed, autofix_applied, autofix_failed)."
    - "Every registered event has a Pydantic payload model (documented as a markdown code block, NOT a .py source file) with `model_config = ConfigDict(extra='forbid')` and required fields: `verifier_name`, `scope_id`, `verdict: Literal[\"passed\", \"failed\", \"warning\"]`, `evidence: list[Citation]`, `triggered_at: datetime`, `session_id`, `snapshot_event_id: str | None`."
    - "The amendment is APPEND-ONLY — no original v40 entries are modified; no prior v41 amendment blocks are modified. The amendment block sits at the END of the file."
    - "The amendment forward-references Phase 411 EVD-01 for the canonical verifier-output-schema (this Plan 03 enumerates event-name registry + required-field shape only)."
  artifacts:
    - path: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      provides: "v42 Amendment block registering the verifier event family"
      min_lines_added: 130
      contains_sections:
        - "## v42 Amendment — Phase 407 Verifier Event Family"
        - "### Event-Name Registry"
        - "### Pydantic Payload Models"
        - "### Append-Only Note"
  key_links:
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (v42 Amendment block)"
      to: ".state/build/quality/VERIFIER-CHAIN.md"
      via: "header reference to the canonical verifier-chain spec"
    - from: "v42 Amendment block"
      to: "Phase 411 EVD-01 (full verifier-output-schema)"
      via: "forward-reference for canonical schema (Plan 03 scope = name registry + required-field shape only)"
---

<threat_model>
ASVS L1. Event-registry amendment. Two relevant risks:

- **Event-name collision (T-407-05)**: A registered event name that overlaps with an existing v40 or v41 event would cause ambiguous downstream dispatch — a verifier failure could be silently routed to an unrelated handler. **Mitigation**: acceptance criteria require explicit absence of any pre-existing event prefix collision; the action body requires a grep-check inside the executor's workflow against the v40 + v41 amendment blocks for each of the ~25 new event names. Additionally, the registered prefix `state.verifier.*` is documented as the SOLE owner of verifier events (no other namespace may register here).
- **Append-only violation (T-407-06)**: A non-append-only edit to a prior v40 or v41 block would silently corrupt historical specs and break the audit chain. **Mitigation**: acceptance criteria use a byte-checksum-equivalent strategy — `wc -l` baseline taken BEFORE the amendment + a `grep -c '## v41 Amendment'` check that returns the SAME count after the amendment (no v41 amendment was added or removed). Additionally, the action body explicitly tells the executor to append at the end-of-file, never edit existing content.
</threat_model>

<objective>
Append a `## v42 Amendment — Phase 407 Verifier Event Family` block to the canonical v40 EVENT-TAXONOMY.md (at `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`). The amendment registers ~25 new verifier event names, declares the Pydantic payload model shape required of each, and forward-references Phase 411 EVD-01 for the canonical verifier-output-schema. APPEND-ONLY — no prior content is modified.

Purpose: Make verifier events first-class members of the v40 event taxonomy so the daemon's projector + SSE bus + replay machinery treats them uniformly with existing events.

Output: ~130 lines appended to the EVENT-TAXONOMY.md file.

This plan runs in **Wave 1** in parallel with Plan 01 (different file — no conflict).
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md
@.planning/milestones/v42/REQUIREMENTS.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v41/phases/402/402-CONTEXT.md
@.planning/milestones/v41/phases/406/406-CONTEXT.md
</context>

<interfaces>
<!-- Canonical event taxonomy conventions (verbatim from v40 EVENT-TAXONOMY.md head). -->

Event-name format (v40 Design Convention): `state.{tier}.{action}` — tier prefix identifies the aggregate, action describes what happened.

Verifier event namespace shape (Phase 407 extension): `state.verifier.<scope>[.<sub_verifier>].<verdict>` — extends the {tier} slot with a new `verifier` prefix, sub-namespaces by scope (step/slice/stage/arc/crosstier), optionally further by sub-verifier (goal_backward/security/stub_detector/anti_pattern), and terminates with verdict.

Naming convention check (v41 amendment pattern): every event matches regex `^state\.[a-z_]+\.[a-z_.]+$` — only `[a-z_]+` segments allowed.

Pydantic payload requirement: every event has a payload model with `model_config = ConfigDict(extra='forbid')`.

Required payload fields for every verifier event (Phase 407 floor; Phase 411 EVD-01 may extend):
- `verifier_name: str` — fully-qualified event name (e.g., `"state.verifier.step.goal_backward.passed"`)
- `scope_id: str` — Step / Slice / Stage / Arc ID, depending on scope
- `verdict: Literal["passed", "failed", "warning"]`
- `evidence: list[Citation]` — Phase 409 ADV-03 grammar (`file_path:line_number`, `commit:<hash>`, `event:<id>`, `test:<runner-output-id>`)
- `triggered_at: datetime` — UTC, deterministic (replay-stable)
- `session_id: str` — opencode session correlation
- `snapshot_event_id: str | None` — pointer to the Step/Slice/Stage/Arc snapshot event the verifier evaluated (None for Cross-Tier which evaluates against current HEAD)
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Append v42 Amendment block to EVENT-TAXONOMY.md with event-name registry and Pydantic payload models</name>
  <files>.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md</files>
  <read_first>
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (verify v41 amendment blocks already exist at lines ~199, ~239, ~285, ~352; capture current line count via `wc -l` before editing)
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md (`<decisions>` block — VCH-07 subsection verbatim, including the full ~25 event-name enumeration)
    - .planning/milestones/v42/REQUIREMENTS.md (VCH-07 verbatim)
    - .planning/milestones/v41/phases/402/402-CONTEXT.md (amendment-as-append pattern; Phase 402 was the first amendment)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md (Phase 405 amendment-as-append pattern; latest example in EVENT-TAXONOMY.md)
  </read_first>
  <behavior>
    - Appends ONLY to the end of `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — no prior content (original v40 spec + v41 amendments) is modified.
    - Adds a `## v42 Amendment — Phase 407 Verifier Event Family` block.
    - The block contains: header context paragraph + event-name registry table (~25 events) + a section of Pydantic payload models (markdown code blocks) + an append-only note + forward-reference to Phase 411 EVD-01.
    - Every event name follows the regex `^state\.verifier\.[a-z_.]+$`.
    - Every payload model uses `model_config = ConfigDict(extra='forbid')`.
  </behavior>
  <action>
    Append the following content to `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`. Use the Edit/Write tool. DO NOT modify any existing content.

    **Block start:**

    ```markdown
    ## v42 Amendment — Phase 407 Verifier Event Family

    *Owned by:* Phase 407 (Verifier Chain Architecture).
    *Canonical spec:* `.state/build/quality/VERIFIER-CHAIN.md`.
    *Forward-reference:* Phase 411 EVD-01 owns the full `Citation` Pydantic schema + extended verifier-output-schema; this amendment registers event names + required-field shape only.

    Registers the verifier event family — every event a verifier emits when it runs (passed/failed/warning) or when the daemon's projector re-aggregates a parent rollup. Namespace shape: `state.verifier.<scope>[.<sub_verifier>].<verdict>`. All events are deterministic, replay-stable, and validated by Pydantic with `extra="forbid"`.

    ### Event-Name Registry

    | Event name | Category | Scope ID type | Notes |
    |---|---|---|---|
    | `state.verifier.step.goal_backward.passed` | Step sub-verifier | `step_id` | Goal-backward sub-verifier success. Forward-refs Phase 409. |
    | `state.verifier.step.goal_backward.failed` | Step sub-verifier | `step_id` | Goal-backward sub-verifier BLOCKER finding. |
    | `state.verifier.step.goal_backward.warning` | Step sub-verifier | `step_id` | Goal-backward WARNING-only finding (no BLOCKER). |
    | `state.verifier.step.security.passed` | Step sub-verifier | `step_id` | Security sub-verifier success. Forward-refs Phase 410 THM. |
    | `state.verifier.step.security.failed` | Step sub-verifier | `step_id` | Security sub-verifier BLOCKER (open mitigation, missing registry entry, etc.). |
    | `state.verifier.step.security.warning` | Step sub-verifier | `step_id` | Security WARNING (e.g., `transfer` disposition with thin verification). |
    | `state.verifier.step.stub_detector.passed` | Step sub-verifier | `step_id` | Stub-detector success (no unregistered stubs reaching user surface). Forward-refs Phase 408 STB. |
    | `state.verifier.step.stub_detector.failed` | Step sub-verifier | `step_id` | Stub-detector BLOCKER (stub reaches rendering/API surface). |
    | `state.verifier.step.stub_detector.warning` | Step sub-verifier | `step_id` | Stub-detector WARNING (stub present but consumer handles gracefully). |
    | `state.verifier.step.anti_pattern.passed` | Step sub-verifier | `step_id` | Anti-pattern scanner success. Forward-refs Phase 410 APS. |
    | `state.verifier.step.anti_pattern.failed` | Step sub-verifier | `step_id` | Anti-pattern BLOCKER (after auto-fix-attempt exhausted). |
    | `state.verifier.step.anti_pattern.warning` | Step sub-verifier | `step_id` | Anti-pattern WARNING-severity finding. |
    | `state.verifier.step.passed` | Step composite | `step_id` | All 4 sub-verifiers `passed` or `warning`. Server-recomputed. |
    | `state.verifier.step.failed` | Step composite | `step_id` | Any sub-verifier `failed`. |
    | `state.verifier.slice.passed` | Slice rollup | `slice_id` | All child Steps `passed`/`warning` AND Slice integration check passed. |
    | `state.verifier.slice.failed` | Slice rollup | `slice_id` | Any child Step `failed` OR Slice integration check failed. |
    | `state.verifier.stage.passed` | Stage rollup | `stage_id` | All child Slices `passed`/`warning` AND Stage acceptance check passed. |
    | `state.verifier.stage.failed` | Stage rollup | `stage_id` | Any child Slice `failed` OR Stage acceptance check failed. |
    | `state.verifier.arc.passed` | Arc rollup | `arc_id` | All child Stages `passed`/`warning` AND Arc acceptance check passed. |
    | `state.verifier.arc.failed` | Arc rollup | `arc_id` | Any child Stage `failed` OR Arc acceptance check failed. |
    | `state.verifier.crosstier.passed` | Cross-Tier | `arc_id` | No regression detected across `depends_on` closure of shipped Arcs. |
    | `state.verifier.crosstier.regression_detected` | Cross-Tier | `arc_id` | At least one closure-Arc shows verdict-flip OR must-have unsatisfaction; fires `human-gate`. |
    | `state.verifier.verdict_changed` | Re-aggregation | varies (composite key: `scope_id + scope_kind`) | Fires when daemon's projector re-aggregates a parent rollup after a child verdict-flip; payload includes `from_verdict` + `to_verdict`. |
    | `state.verifier.autofix_applied` | Anti-pattern auto-fix | `step_id` | Deterministic harness pass succeeded (pattern resolved by ruff/black/isort); payload includes `tool` + `pattern_id` + `before_hash` / `after_hash`. |
    | `state.verifier.autofix_failed` | Anti-pattern auto-fix | `step_id` | Deterministic harness pass ran but pattern remains; harness escalates to `retry-loop`. |

    ### Pydantic Payload Models

    Every verifier event has a Pydantic payload model with `model_config = ConfigDict(extra='forbid')`. The base shape (inherited by all verifier events):

    ```python
    from datetime import datetime
    from typing import Literal
    from pydantic import BaseModel, ConfigDict

    # Citation grammar is owned by Phase 409 ADV-03 / Phase 411 EVD-02.
    # Plan 03 references the type but does not define it here.
    Citation = str  # opaque placeholder — full union owned by EVD-02

    class VerifierEventPayloadBase(BaseModel):
        model_config = ConfigDict(extra='forbid')
        verifier_name: str                       # fully-qualified event name
        scope_id: str                            # step_id / slice_id / stage_id / arc_id
        verdict: Literal['passed', 'failed', 'warning']
        evidence: list[Citation]                 # ADV-03 / EVD-02 grammar
        triggered_at: datetime                   # UTC, replay-stable
        session_id: str                          # opencode session correlation
        snapshot_event_id: str | None            # snapshot the verifier evaluated; None for Cross-Tier
    ```

    Per-event extensions (auxiliary fields beyond the base):

    ```python
    class StepSubVerifierFailedPayload(VerifierEventPayloadBase):
        """Used by every `state.verifier.step.<sub>.failed` event."""
        strike_n: int                            # 1..3 per v41 PRF-06 per-(task_id, check_id) counter
        sub_verifier: Literal['goal_backward', 'security', 'stub_detector', 'anti_pattern']

    class VerdictChangedPayload(VerifierEventPayloadBase):
        """Used by `state.verifier.verdict_changed`. Server-emitted by projector during re-aggregation."""
        from_verdict: Literal['passed', 'failed', 'warning']
        to_verdict: Literal['passed', 'failed', 'warning']
        scope_kind: Literal['step', 'slice', 'stage', 'arc']

    class AutofixAppliedPayload(VerifierEventPayloadBase):
        """Used by `state.verifier.autofix_applied` and `state.verifier.autofix_failed`."""
        tool: Literal['ruff', 'black', 'isort']
        pattern_id: str                          # ruff rule ID or AST match name
        file_path: str                           # relative to Slice worktree root
        before_hash: str                         # SHA-256 of file pre-fix
        after_hash: str                          # SHA-256 of file post-fix (== before_hash if autofix_failed)

    class CrossTierRegressionDetectedPayload(VerifierEventPayloadBase):
        """Used by `state.verifier.crosstier.regression_detected`."""
        offending_arc_id: str                    # the just-shipped Arc that triggered regression
        regressed_arcs: list[str]                # closure-Arcs whose verdict flipped OR must_haves unsatisfied
        regression_kind: Literal['verdict_flip', 'must_have_unsatisfied', 'both']
    ```

    **Field-set ownership note**: Phase 411 EVD-01 owns the canonical verifier-output-schema, including the full `Citation` discriminated union (`FileCitation`, `CommitCitation`, `EventCitation`, `TestCitation`). When the field-set details diverge between this amendment (registry index) and Phase 411 EVD-01 (canonical schema), Phase 411 EVD-01 wins.

    ### Naming-Convention Check

    - All event names match regex `^state\.verifier\.[a-z_.]+$`.
    - Sub-verifier names use snake_case verbatim (`goal_backward`, `stub_detector`, `anti_pattern`) — never CamelCase, never hyphens.
    - Cross-Tier event uses prefix `state.verifier.crosstier.*` (single word, no hyphen, no underscore — matches the rest of the namespace's atom-segmentation).
    - No naming-drift entries; all entries `[a-z_.]+` only.

    ### Mode Isolation

    All `state.verifier.*` events are **build-mode only** (`BUILD_ONLY_EVENT_PREFIXES` — add `"state.verifier."` to that set in `src/state_core/schema.py` when v14 Build Kernel implements). Teach mode has its own verification family (owned by v48; out of scope here).

    ### Append-Only Note

    *Original v40 spec text and all four prior v41 amendment blocks (Phase 402, 403, 404, 405) above this block are untouched. This amendment is purely additive, appended per Phase 402 convention. Phase 411 may append a `## v42 Amendment — Phase 411 ...` block extending this registry with additional evidence-chain events (EVD-01..05).*
    ```

    **Procedure for the executor:**

    1. Run `wc -l .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` and record the line count (baseline).
    2. Run `grep -c '^## v41 Amendment' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` and record the count (baseline = 4).
    3. Append the block above to the END of the file (after the last existing v41 amendment block's closing paragraph).
    4. Re-run both checks: line count must be ≥ baseline + 130; v41 Amendment count must equal 4 (unchanged).
    5. For each of the ~25 event names, run `grep -c '^| \`state.verifier.<name>\`' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` and verify it returns ≥ 1.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — 4 existing v41 amendment blocks at lines 199, 239, 285, 352. Mirror the structure verbatim.
        - Known: existing event prefix set in `src/state_core/schema.py` — `BUILD_ONLY_EVENT_PREFIXES`. Reference for the mode-isolation subsection.
        - Grep pattern (verify no event-name collision with existing v40/v41 entries): `for evt in step.goal_backward.passed step.goal_backward.failed step.security.passed step.security.failed step.stub_detector.passed step.stub_detector.failed step.anti_pattern.passed step.anti_pattern.failed step.passed step.failed slice.passed slice.failed stage.passed stage.failed arc.passed arc.failed crosstier.passed crosstier.regression_detected verdict_changed autofix_applied autofix_failed; do grep -c "state.verifier.$evt" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md; done`  — every count BEFORE the append must be 0 (no prior collision).
      </code_to_reuse>
      <docs_to_consult>
        - 407-CONTEXT.md `<decisions>` VCH-07 subsection — verbatim source for the ~25-event enumeration.
        - v40 EVENT-TAXONOMY.md Design Conventions section (top of file) — naming-convention check is consistent.
        - Phase 405 amendment block in EVENT-TAXONOMY.md (at line ~352) — most recent precedent for the v42 block's structure.
      </docs_to_consult>
      <tests_to_write>
        N/A — design-only markdown amendment.
      </tests_to_write>
    </quality_scan>
  </action>
  <acceptance_criteria>
    - `grep -c '^## v42 Amendment — Phase 407 Verifier Event Family$' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns 1
    - `grep -c '^### Event-Name Registry$' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns 1
    - `grep -c '^### Pydantic Payload Models$' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns 1
    - `grep -c '^### Append-Only Note$' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns 1
    - `grep -c 'state.verifier.step.goal_backward.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.goal_backward.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.security.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.security.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.stub_detector.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.stub_detector.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.anti_pattern.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.anti_pattern.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.step.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.slice.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.slice.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.stage.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.stage.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.arc.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.arc.failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.crosstier.passed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.crosstier.regression_detected' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.verdict_changed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.autofix_applied' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c 'state.verifier.autofix_failed' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1
    - `grep -c "ConfigDict(extra='forbid')" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 2 (was 0 from v42 plan if grep against the new block alone; project-wide count must increase by ≥ 1 from the new amendment)
    - `grep -c '^## v41 Amendment' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns exactly 4 (unchanged — append-only preserved)
    - `grep -c 'Phase 411 EVD-01' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns ≥ 1 (forward-reference present)
    - `grep -ci '\bgsd-\?[0-9]' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns 0 (no GSD references introduced by this plan; baseline must be 0 too)
    - The v42 Amendment block must appear AFTER all v41 Amendment blocks (line-order check): `awk '/^## v41 Amendment/{v41=NR} /^## v42 Amendment/{v42=NR} END{exit !(v42>v41)}' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` returns exit code 0
  </acceptance_criteria>
  <verify>
    <automated>grep -q '^## v42 Amendment — Phase 407 Verifier Event Family$' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md &amp;&amp; [ "$(grep -c '^## v41 Amendment' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md)" = "4" ] &amp;&amp; grep -q 'state.verifier.crosstier.regression_detected' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md &amp;&amp; grep -q "ConfigDict(extra='forbid')" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md &amp;&amp; awk '/^## v41 Amendment/{v41=NR} /^## v42 Amendment/{v42=NR} END{exit !(v42&gt;v41)}' .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md</automated>
  </verify>
  <done>
    `## v42 Amendment — Phase 407 Verifier Event Family` block exists at the end of EVENT-TAXONOMY.md with event-name registry table (~25 events), Pydantic payload models section, naming-convention check, mode isolation note, and append-only note. All prior v41 amendment blocks unchanged. All acceptance grep patterns pass.
  </done>
</task>

</tasks>

<verification>
- v42 Amendment block exists with header `## v42 Amendment — Phase 407 Verifier Event Family`.
- Event-name registry table contains ≥ 25 events covering Step sub-verifier (4 × 3 = 12 with warnings), Step composite (2), Slice/Stage/Arc rollups (3 × 2 = 6), Cross-Tier (2), auxiliary (verdict_changed, autofix_applied, autofix_failed) = 25 base events.
- All event names match `^state\.verifier\.[a-z_.]+$`.
- Pydantic payload base + extensions present with `ConfigDict(extra='forbid')`.
- Forward-reference to Phase 411 EVD-01 present.
- 4 prior v41 amendment blocks unmodified; v42 block sits after them.
- No GSD-NN references introduced.
</verification>

<success_criteria>
- v42 Amendment appended to canonical EVENT-TAXONOMY.md
- ~25 verifier event names registered
- Pydantic payload models documented as markdown code blocks (not source files)
- All payload models use `ConfigDict(extra='forbid')`
- Append-only invariant preserved (v41 amendments unchanged)
- Naming convention check matches v41 amendment-block pattern
</success_criteria>

<output>
After completion, create `.planning/milestones/v42/phases/407-verifier-chain-architecture/407-03-SUMMARY.md` with:
- 1-paragraph outcome (v42 Amendment appended, event count, append-only preserved)
- Cross-references: VCH-07 requirement satisfied
- Forward-references: Phase 411 EVD-01 (canonical Citation schema + extended verifier-output-schema)
- Append-only invariant proof: pre/post `wc -l` + v41 amendment count unchanged
</output>
