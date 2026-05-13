---
phase: 403
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
autonomous: false
requirements:
  - STP-01
  - STP-02
  - STP-03
  - STP-04
  - STP-05
  - STP-06
  - STP-07
  - STP-08
  - PAP-01
  - PAP-03
  - PAP-06

must_haves:
  truths:
    - "EXEMPLAR-stepNPLAN.md exists at .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md and is a fully realized worked example using a v14 Build Kernel Step (Implement CompactionSnapshot Pydantic model)."
    - "Frontmatter parses as valid YAML and contains every StepFrontmatter field from 403-CONTEXT.md (phase, slice, step, type, wave, depends_on, files_modified, autonomous, requirements, must_haves) with no extras."
    - "must_haves block contains all three sub-blocks (truths, artifacts, key_links) populated with realistic content."
    - "Body contains every required XML section: <objective>, <execution_context>, <context>, <interfaces>, <tasks>, <threat_model>, <verification>, <success_criteria>, <output>."
    - "At least one <task> block exists with all required sub-tags: type, <name>, <files>, <read_first>, <action>, <verify> (with nested <automated>), <acceptance_criteria>, <done>."
    - "At least one <task> demonstrates the <task type=\"checkpoint:decision\"> shape with the <options> sub-tag carrying 2–4 named options each with pros and cons attributes (per 403-CONTEXT.md <decisions> Task-type behaviors)."
    - "At least one <task type=\"auto+tdd\"> demonstrates RED-before-GREEN expectations citing the GSD-Test-Result: FAIL|PASS commit-trailer convention from 403-CONTEXT.md."
    - "<interfaces> block contains literal code excerpts (real Python class skeletons or function signatures) drawn from the simulated upstream artifact — not placeholder text — fulfilling STP-07 zero-codebase-exploration contract."
    - "<read_first> entries cite exact file paths with line ranges (e.g., 'src/state_core/schema.py lines 1-40') — never 'explore the codebase' or unscoped paths — fulfilling STP-08."
    - "Spec docs in Plan 02 and Plan 03 can quote LITERAL excerpts from this file for STP-03 success criterion 2 — meaning the file is realistic enough that quoting a 5–15 line block from each section produces a useful demonstration."
  artifacts:
    - path: ".planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md"
      provides: "Canonical hand-authored stepNPLAN.md worked example for the CompactionSnapshot Pydantic model Step. Substrate for STEP-PLAN-FORMAT.md and PLAN-AS-PROMPT.md literal-excerpt citations."
      min_lines: 250
  key_links:
    - from: ".planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "Step subject (CompactionSnapshot Pydantic model) is defined in Phase 402's CONTEXT-PROTOCOL.md; <interfaces> block excerpts reference its schema"
      pattern: "CompactionSnapshot"
    - from: ".planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md"
      to: ".planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md"
      via: "Frontmatter Pydantic convention reference"
      pattern: "extra=\"forbid\""
---

<objective>
Hand-author the canonical EXEMPLAR-stepNPLAN.md worked example. This is the substrate for the STP-03 success criterion 2 requirement that "every XML body section AND every `<task>` sub-tag is documented with at least one literal example excerpt from the GSD-shape demonstration plan." Without this file existing first, the spec docs in Plan 02 and Plan 03 cannot quote literal excerpts — they would have to fabricate placeholder text, which fails the success criterion.

The example uses a realistic v14 Build Kernel Step: **"Implement CompactionSnapshot Pydantic model"** — concrete, plausibly real, exercises every section from `<objective>` through `<task><verify><automated>`. The CompactionSnapshot model is defined in Phase 402's CONTEXT-PROTOCOL.md and represents the on-the-wire shape used by the compaction reinject flow (CTX-05/CTX-06).

Purpose: Phase 403's downstream consumers (STEP-PLAN-FORMAT.md spec author in Plan 02, PLAN-AS-PROMPT.md spec author in Plan 03) cite literal excerpts from this file. v14 Build Kernel implementations test their StepPlan parser against this file as the canonical "shape contract."
Output: One markdown file at `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`, ≥250 lines, fully populated with realistic content (not placeholders).

This plan does not directly own a unique REQ-ID — its `requirements` frontmatter field tags the union of STP-01..STP-08 + PAP-01/03/06 because EXEMPLAR is the substrate for all of them. STP-IDs and PAP-IDs that the EXEMPLAR exercises in its content are listed; PAP-02/04/05 (injection-time mechanics) are not exercised because the EXEMPLAR is a static authored artifact, not a runtime injection trace.
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
@.planning/milestones/v41/phases/403/403-CONTEXT.md
@.planning/milestones/v41/phases/402/402-CONTEXT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
</context>

<threat_model>
Phase 403 is design-only. EXEMPLAR-stepNPLAN.md introduces no production attack surface — it is a markdown specification file. The threat surface for Phase 403 spec docs (per `<security_threat_model_gate>` in the planner directive) is narrow but the EXEMPLAR is the SHAPE contract from which the runtime threats are specified. Threats considered:

- **Path-traversal demonstration via `@`-references in <context>**: The EXEMPLAR's `<context>` block uses `@.planning/...` references. If the EXEMPLAR demonstrates a path that escapes `.planning/` (e.g., `@/etc/passwd` or `@../../../`), readers may infer this is allowed. Mitigation — every `@`-reference in the EXEMPLAR resolves under `.planning/` or repo-root paths only; the EXEMPLAR's <context> block contains a 1-line note: "All `@`-references resolve under repo root + `.planning/` per PAP-02 path-confinement rule (specified in PLAN-AS-PROMPT.md)."
- **Demonstration of a `<discovered_threats>` sub-tag that already contains threats at authoring time**: If the EXEMPLAR shows `<discovered_threats>` with content, readers may think pre-population is allowed (it is not — append-only at runtime). Mitigation — EXEMPLAR's `<discovered_threats>` is empty or contains only a comment `<!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->`.
- **Markdown injection in code blocks**: The EXEMPLAR contains fenced Python and bash code blocks. All code is illustrative; no executable templating. Mitigation — every code block is fenced; no executor will execute the EXEMPLAR (it IS the spec).
- **Mode-isolation drift**: Build-only EXEMPLAR. Mitigation — explicit "Build-mode only" header note; no `state.teach.*` references; the EXEMPLAR's frontmatter `slice` field uses a build-mode slice slug.

No production code lands. No secrets. No network calls. No untrusted input.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author EXEMPLAR-stepNPLAN.md with full frontmatter + every body section + 3 representative tasks</name>
  <files>
    .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/403-CONTEXT.md (full file — every locked decision in <decisions> must be honored verbatim)
    - .planning/milestones/v41/phases/402/402-CONTEXT.md (full file — Phase 402 carry-forward decisions: stepNPLAN.md filename form, reinject XML shape, tool.execute.before canonical block hook)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (full file — CompactionSnapshot Pydantic model is THIS file's authoritative source; the EXEMPLAR's <interfaces> block quotes it literally)
    - .planning/milestones/v41/REQUIREMENTS.md lines 38-56 (STP-01..STP-08 + PAP-01..PAP-06 verbatim)
    - .planning/milestones/v41/HANDOFF.md (D-5 Step shape decision; §2 Task Decomposition; §3 Plan-as-Prompt template structure lines 84-116)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-50 (Pydantic frontmatter convention — extra="forbid" pattern)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (search for "stepNPLAN" — confirms filename: no dash, no leading zeros)
    - .planning/milestones/v41/phases/402/01-slice-cycle-spec-PLAN.md lines 1-100 (Phase 402 plan shape reference — Phase 403 EXEMPLAR follows the same shape with v41 vocabulary)
    - .planning/milestones/v41/phases/402/02-context-protocol-spec-PLAN.md lines 1-90 (Phase 402 plan shape reference — must_haves block populated form)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` as a hand-authored worked example. The Step subject is **"Implement CompactionSnapshot Pydantic model"** — a v14 Build Kernel Step (notional Slice: `compaction-snapshot-schema` under v14's first Phase). The EXEMPLAR demonstrates the GSD-shape (YAML frontmatter + XML body) such that v14 implementations of the StepPlan parser can use it as a parser test fixture.

    Use the structure below verbatim. **Concrete values — not placeholders.** Every section must contain realistic content.

    ## Required structure

    ### Section A — File header (markdown comment)

    Start the file with this exact comment block (so readers know it is a spec exemplar, not a real Step):

    ```
    <!--
      EXEMPLAR-stepNPLAN.md — canonical worked example.
      Owned by: Phase 403 (Step/Task Decomposition & Plan-as-Prompt).
      Subject: Implement CompactionSnapshot Pydantic model (notional v14 Build Kernel Step).
      Cited by: STEP-PLAN-FORMAT.md (literal excerpts) and PLAN-AS-PROMPT.md (literal excerpts).
      v14 implementations may diverge from specifics, but the SHAPE is the contract.
      Build-mode only. No state.teach.* references.
    -->
    ```

    ### Section B — YAML frontmatter (between `---` delimiters)

    Populate every field from the StepFrontmatter Pydantic model in 403-CONTEXT.md `<decisions>` "Frontmatter schema completeness" subsection. Use these exact concrete values:

    ```yaml
    phase: "v14-1"                              # notional v14 Build Kernel Phase 1
    slice: "compaction-snapshot-schema"
    step: "compaction-snapshot-schema-step-1"   # stable hash form per Granularity §step_id rule
    type: "auto+tdd"                            # demonstrates RED-before-GREEN
    wave: 1
    depends_on: []                              # first Step in slice
    files_modified:
      - "src/state_build/snapshot/compaction.py"
      - "tests/state_build/snapshot/test_compaction.py"
    autonomous: true
    requirements:
      - "CTX-05"
      - "CTX-06"

    must_haves:
      truths:
        - "python -c 'from state_build.snapshot.compaction import CompactionSnapshot; print(CompactionSnapshot.model_config[\"extra\"])' prints 'forbid'."
        - "orjson round-trip: dumps→loads of a populated CompactionSnapshot is bit-identical to the original."
        - "All seven snapshot fields from CONTEXT-PROTOCOL.md are present (slice_id, step_id, task_id, session_id, active_plan_path, current_task_pointer, upstream_provides)."
      artifacts:
        - path: "src/state_build/snapshot/compaction.py"
          provides: "CompactionSnapshot Pydantic model + orjson serializer"
          min_lines: 60
        - path: "tests/state_build/snapshot/test_compaction.py"
          provides: "Round-trip test + extra='forbid' rejection test + missing-field rejection test"
          min_lines: 80
      key_links:
        - from: "src/state_build/snapshot/compaction.py"
          to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
          via: "Field set matches CompactionSnapshot schema specified in §5"
          pattern: "class CompactionSnapshot"
        - from: "tests/state_build/snapshot/test_compaction.py"
          to: "src/state_build/snapshot/compaction.py"
          via: "Test imports CompactionSnapshot for round-trip validation"
          pattern: "from state_build\\.snapshot\\.compaction import"
    ```

    ### Section C — XML body (after closing `---`)

    Author each of the nine required body sections in this exact order. Each section must contain realistic content. Use the structure below as a skeleton — fill in concrete content; no placeholder strings like "TBD" or "[CONTENT HERE]".

    1. `<objective>` block — 2 paragraphs:
       - Paragraph 1: What this Step accomplishes. Example phrasing: "Define and implement the `CompactionSnapshot` Pydantic model that the daemon emits to the event store on every compaction event (intra-Slice or Slice-boundary). The on-the-wire shape is the canonical reinject payload spec; v14 Build Kernel's compaction handler serializes this model via orjson into the `state.slice.compacted` event row."
       - Paragraph 2: Why it matters. Example phrasing: "Without this model, downstream Phase 403 STEP-PLAN-FORMAT.md cannot demonstrate the must_haves.artifacts shape on a realistic Pydantic file, and v14's compaction subsystem cannot type-validate snapshot payloads at the daemon boundary."

    2. `<execution_context>` block — verbatim:
       ```
       @~/.claude/get-shit-done/workflows/execute-plan.md
       @~/.claude/get-shit-done/templates/summary.md
       ```
       Include a 1-line note immediately after: "(All `@`-references in this file resolve under repo root + `.planning/` per PAP-02 path-confinement rule.)"

    3. `<context>` block — at least 5 `@`-references covering the project, the requirement spec, the upstream spec doc, the schema convention, and a sibling code file:
       ```
       @CLAUDE.md
       @.planning/PROJECT.md
       @.planning/milestones/v41/REQUIREMENTS.md
       @.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
       @src/state_core/schema.py
       ```

    4. `<interfaces>` block — STP-07 literal-excerpt rule. Include AT LEAST TWO upstream excerpts. Realistic content (not placeholder):

       Excerpt A — from `state_core.schema` (illustrative; the EXEMPLAR is permitted to render the upstream artifact even if the actual file differs slightly):
       ```python
       # From src/state_core/schema.py (lines ~1-30)
       from pydantic import BaseModel, ConfigDict
       from typing import Literal

       class EventEnvelope(BaseModel):
           model_config = ConfigDict(extra="forbid")
           event_id: str
           event_type: str            # "state.{tier}.{action}"
           aggregate_id: str
           emitted_at: str            # ISO-8601 UTC
           payload: dict              # validated per event_type
       ```

       Excerpt B — from CONTEXT-PROTOCOL.md (the field shape this Step implements):
       ```python
       # From .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md §5 (CompactionSnapshot)
       class CompactionSnapshot(BaseModel):
           model_config = ConfigDict(extra="forbid")
           slice_id: str
           step_id: str
           task_id: str | None        # None at Slice-boundary spawn
           session_id: str
           active_plan_path: str
           current_task_pointer: str | None
           upstream_provides: dict[str, str]   # step_id → provides-block markdown
       ```

       Add a 1-line note after the excerpts: "Excerpts above are LITERAL upstream content. The executor must NOT re-derive these contracts from the codebase (STP-07 zero-codebase-exploration)."

    5. `<tasks>` block — exactly 3 `<task>` blocks, demonstrating three task types:

       **Task 1** — `<task type="auto+tdd">` "Write failing test for CompactionSnapshot round-trip and extra='forbid'":
       - `<files>tests/state_build/snapshot/test_compaction.py</files>`
       - `<read_first>` cites: `tests/conftest.py lines 1-40`, `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md lines 200-260` (the CompactionSnapshot section), `src/state_core/schema.py lines 1-40`
       - `<action>` ~6-8 bullet points: create the test file, write a round-trip test asserting orjson dumps→loads is identity, write an extras-forbid test asserting CompactionSnapshot(**{"unknown_field": 1}) raises ValidationError, write a missing-required-field test, run pytest and capture the FAIL exit code, commit with prefix `test:` and trailer `GSD-Test-Result: FAIL`.
       - `<verify><automated>pytest tests/state_build/snapshot/test_compaction.py -x 2>&1 | tee /tmp/red.log; grep -q "FAILED" /tmp/red.log</automated></verify>`
       - `<acceptance_criteria>` 3 bullets: "Test file exists with ≥80 lines", "pytest exits non-zero (RED)", "git log shows commit with `test:` prefix and `GSD-Test-Result: FAIL` trailer"
       - `<done>` "RED phase complete; failing test captured and committed."

       **Task 2** — `<task type="auto">` "Implement CompactionSnapshot Pydantic model to make tests pass":
       - `<files>src/state_build/snapshot/compaction.py</files>`
       - `<read_first>` cites: `tests/state_build/snapshot/test_compaction.py lines 1-80` (the test file from Task 1, now load-bearing), `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md lines 200-260`, `src/state_core/schema.py lines 1-40`
       - `<action>` ~5 bullet points: create the file, define `class CompactionSnapshot(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and the seven fields from the upstream spec, add an `orjson_dumps` and `orjson_loads` round-trip helper, run pytest and confirm GREEN, commit with prefix `feat:` and trailer `GSD-Test-Result: PASS`.
       - `<verify><automated>pytest tests/state_build/snapshot/test_compaction.py -x</automated></verify>`
       - `<acceptance_criteria>` 4 bullets including: file exists ≥60 lines, all tests pass, ConfigDict(extra="forbid") present (`grep -q 'extra="forbid"' src/state_build/snapshot/compaction.py`), commit trailer present (`git log -1 --format=%B | grep -q "GSD-Test-Result: PASS"`)
       - `<done>` "GREEN phase complete; CompactionSnapshot importable and round-trippable."

       **Task 3** — `<task type="checkpoint:decision">` "Pick orjson serialization mode: OPT_NAIVE_UTC or OPT_UTC_Z":
       - `<files></files>` (decision-only; no file writes)
       - `<read_first>` cites: `src/state_build/snapshot/compaction.py lines 1-60` (Task 2 output), `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md lines 260-280` (timestamp serialization note)
       - `<options>` block — 2 named options each with `pros` and `cons` attributes:
         ```xml
         <options>
           <option name="OPT_NAIVE_UTC"
                   pros="naive timestamps, no TZ suffix, smallest payload"
                   cons="ambiguous on cross-host replay, requires UTC-only convention"/>
           <option name="OPT_UTC_Z"
                   pros="explicit Z suffix, unambiguous, IS0-8601-compliant"
                   cons="3 extra bytes per timestamp, slightly larger payload"/>
         </options>
         ```
       - `<action>` "Render the choice via opencode `question` tool. Under `--full-yolo` autonomy, the harness picks `option name=\"OPT_NAIVE_UTC\"` deterministically (first option). Under `--tiered` or `--conservative`, the harness stops and surfaces the labeled list to the human."
       - `<verify><automated>echo "checkpoint:decision is gate-resolved at runtime by harness; no automated verification at task level"</automated></verify>`
       - `<acceptance_criteria>` 1 bullet: "checkpoint_auto_resolved or checkpoint_human_action_resolved event emitted with selection field set."
       - `<done>` "Decision recorded; emit `state.step.checkpoint_resolved` event with `selection` set to one of the option `name` attributes."

    6. `<threat_model>` block — STRIDE-style register, 4 threats, each with mitigation. Examples:
       - "Spoofing: malicious input forging a CompactionSnapshot with extra fields. Mitigation: extra='forbid' rejects unknown keys."
       - "Tampering: replay attack with a stale snapshot from a prior session. Mitigation: session_id field must match the active session at rehydrate time; daemon validates."
       - "Repudiation: snapshot row written without an event-store row. Mitigation: snapshot is emitted as a `state.slice.compacted` event payload — event store is authoritative."
       - "DoS via huge upstream_provides dict: snapshot row exceeds event-store row size budget. Mitigation: per-injection token cap (PAP-02); upstream_provides values truncated with marker."

       Add an empty `<discovered_threats>` placeholder block:
       ```xml
       <discovered_threats>
         <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
       </discovered_threats>
       ```

    7. `<verification>` block — Slice-level pre-commit checks. 3-4 bash one-liners:
       - `python -c "from state_build.snapshot.compaction import CompactionSnapshot; assert CompactionSnapshot.model_config['extra'] == 'forbid'"`
       - `pytest tests/state_build/snapshot/test_compaction.py -q`
       - `wc -l src/state_build/snapshot/compaction.py | awk '{exit ($1 < 60)}'`
       - `wc -l tests/state_build/snapshot/test_compaction.py | awk '{exit ($1 < 80)}'`

    8. `<success_criteria>` block — 4 bullets restating must_haves.truths in plain language. Example: "CompactionSnapshot importable, extras forbidden, round-trip identity, all 7 fields present."

    9. `<output>` block — verbatim:
       ```
       After completion, create `.planning/milestones/v14/phases/v14-1/slices/compaction-snapshot-schema/compaction-snapshot-schema-step-1-SUMMARY.md`
       ```

    ## Constraints

    - Every field in the frontmatter must be present (Pydantic `extra="forbid"` rejects missing required keys; the EXEMPLAR is the spec for that contract).
    - The frontmatter MUST parse as valid YAML standalone (no Python f-strings, no Jinja).
    - Every `<read_first>` entry MUST cite a path AND a line range (or "full file" — never just a path).
    - Every `<task>` MUST have its full sub-tag set per STP-04: `type` (attribute), `<name>`, `<files>`, `<read_first>`, `<action>`, `<verify><automated>`, `<acceptance_criteria>`, `<done>`. The `tdd` attribute is set to "true" on Task 1 only.
    - The `<options>` sub-tag (Task 3) is the EXEMPLAR's demonstration of the checkpoint:decision shape — Plan 02 will quote it literally.
    - Use realistic content. The reader of this file should be able to imagine v14 actually executing it.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/02-context-protocol-spec-PLAN.md` lines 1-90 — Phase 402 plan shape; mirror the must_haves population form, the threat_model XML structure, the <verify><automated> embed pattern.
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — the CompactionSnapshot model is here; quote it byte-for-byte in the EXEMPLAR's `<interfaces>` block (one-shot inline).
        - Grep pattern: `grep -nE "^class .*BaseModel" /Users/tmac/Projects/state/src/state_core/schema.py | head -10` — confirms EventEnvelope shape for the upstream excerpt in `<interfaces>`.
        - Grep pattern: `grep -nE "^### " /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md | head -20` — locates the §5 CompactionSnapshot section the EXEMPLAR cites.
      </code_to_reuse>
      <docs_to_consult>
        - 403-CONTEXT.md `<decisions>` Frontmatter schema completeness subsection — every field in the StepFrontmatter / MustHaves Pydantic models is defined here verbatim. Cite exact field set.
        - 403-CONTEXT.md `<decisions>` Task-type behaviors subsection — auto+tdd RED-before-GREEN protocol, GSD-Test-Result trailer convention, checkpoint:decision <options> shape with pros/cons attributes are defined here.
        - 402-CONTEXT.md (Phase 402 carry-forward) — confirms stepNPLAN.md filename form (no dash, no leading zeros) and tool.execute.before block hook canonicalization.
        - HANDOFF.md §3 lines 84-116 — original Plan-as-Prompt template structure (less specific than 403-CONTEXT.md but informs the field intuition).
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). The EXEMPLAR's own `<tasks>` blocks describe tests v14 would run; no Phase 403 task is required to write executable tests against the EXEMPLAR.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 250)}' \
        && grep -q "phase: \"v14-1\"" "$F" \
        && grep -q "slice: \"compaction-snapshot-schema\"" "$F" \
        && grep -q "step: \"compaction-snapshot-schema-step-1\"" "$F" \
        && grep -q "type: \"auto+tdd\"" "$F" \
        && grep -q "must_haves:" "$F" \
        && grep -q "  truths:" "$F" \
        && grep -q "  artifacts:" "$F" \
        && grep -q "  key_links:" "$F" \
        && grep -qE "^<objective>" "$F" \
        && grep -qE "^<execution_context>" "$F" \
        && grep -qE "^<context>" "$F" \
        && grep -qE "^<interfaces>" "$F" \
        && grep -qE "^<tasks>" "$F" \
        && grep -qE "^<threat_model>" "$F" \
        && grep -qE "^<verification>" "$F" \
        && grep -qE "^<success_criteria>" "$F" \
        && grep -qE "^<output>" "$F" \
        && grep -q "<task type=\"auto+tdd\"" "$F" \
        && grep -q "<task type=\"auto\"" "$F" \
        && grep -q "<task type=\"checkpoint:decision\"" "$F" \
        && grep -q "<options>" "$F" \
        && grep -q "<option name=" "$F" \
        && grep -q "pros=" "$F" \
        && grep -q "cons=" "$F" \
        && grep -q "GSD-Test-Result: FAIL" "$F" \
        && grep -q "GSD-Test-Result: PASS" "$F" \
        && grep -q "CompactionSnapshot" "$F" \
        && grep -q "extra=\"forbid\"" "$F" \
        && grep -q "<discovered_threats>" "$F" \
        && grep -q "<read_first>" "$F" \
        && grep -q "<acceptance_criteria>" "$F" \
        && grep -q "<verify><automated>" "$F" || grep -q "<verify>" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - File `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` exists with ≥250 lines.
    - Frontmatter contains every field from StepFrontmatter (phase, slice, step, type, wave, depends_on, files_modified, autonomous, requirements, must_haves) — `grep` for each key passes.
    - Frontmatter `must_haves` block contains all three sub-blocks (truths, artifacts, key_links) — `grep` for each passes.
    - All 9 XML body sections present (objective, execution_context, context, interfaces, tasks, threat_model, verification, success_criteria, output) — line-anchored grep `^<section>` returns 9 matches.
    - All 3 task type forms demonstrated: `<task type="auto+tdd"`, `<task type="auto"`, `<task type="checkpoint:decision"` — grep returns ≥1 match each.
    - `<options>` sub-tag present with at least 2 `<option name=...` lines, each with `pros=` and `cons=` attributes.
    - `GSD-Test-Result: FAIL` and `GSD-Test-Result: PASS` both present (auto+tdd RED→GREEN demonstration).
    - `<discovered_threats>` placeholder block present (with the empty-at-authoring-time comment).
    - At least one `<read_first>` block contains a line range (e.g., grep for `lines [0-9]`).
    - `<interfaces>` block contains both upstream excerpts (EventEnvelope and CompactionSnapshot class definitions present in the file body).
    - No `state.teach.` references (`grep -c "state\\.teach\\." returns 0`).
    - No external-domain `@`-reference (`grep -E "^@/" returns 0` — confirms path confinement).
  </acceptance_criteria>

  <done>
    EXEMPLAR-stepNPLAN.md is a fully realized worked example demonstrating every section and every task sub-tag, with realistic CompactionSnapshot content that downstream specs can quote literally. The file is the canonical "GSD-shape" reference for v14 implementations.
  </done>
</task>

<task type="auto">
  <name>Task 2: Write 01-exemplar-stepnplan-SUMMARY.md and add a Phase 403 README.md pointer</name>
  <files>
    .planning/milestones/v41/phases/403/01-exemplar-stepnplan-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md (full file — written by Task 1; the SUMMARY references it)
    - .planning/milestones/v41/phases/402/402-01-SUMMARY.md (full file — Phase 402 SUMMARY shape reference; mirror its sections: Status, What Was Built, Key Decisions, Files Touched, Open Items, Downstream Hooks)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory; this task closes that gate for Plan 01
  </read_first>

  <action>
    Create the per-plan SUMMARY.md for Plan 01 to satisfy CLAUDE.md's "Per-plan SUMMARY.md is mandatory (project-specific gate)" requirement. Mirror the Phase 402 SUMMARY shape (`402-01-SUMMARY.md`) using these sections:

    1. `# Plan 403-01 Summary: EXEMPLAR-stepNPLAN.md` (H1)
    2. `**Status:** Shipped` + `**Completed:** {today}` + `**Wave:** 1` + `**Depends on:** none` + `**Blocks:** 403-02 (STEP-PLAN-FORMAT.md), 403-03 (PLAN-AS-PROMPT.md)`.
    3. `## What Was Built` — 1 paragraph: the EXEMPLAR file at `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`, what subject it covers (CompactionSnapshot Pydantic model, v14 Build Kernel notional Step), what it demonstrates (every body section, three task types: auto+tdd, auto, checkpoint:decision; full frontmatter; `<options>` sub-tag; GSD-Test-Result trailers).
    4. `## Key Decisions` — 4-5 bullets:
       - "Subject chosen: CompactionSnapshot Pydantic model — matches CONTEXT.md recommendation; concrete, plausibly v14, exercises every section."
       - "step_id form: `compaction-snapshot-schema-step-1` — slugify(slice_id)+'-step-'+ordinal per 403-CONTEXT.md Granularity §step_id rule."
       - "Task 3 demonstrates `<options>` with 2 options (OPT_NAIVE_UTC, OPT_UTC_Z) — meets the 2–4 named options floor; pros/cons attributes literal."
       - "<discovered_threats> shipped empty with the runtime-only-append comment — locks the carve-out semantic at authoring time."
       - "Frontmatter requirements field tags only CTX-05/CTX-06 (the model's actual REQs) — not STP/PAP — to keep the requirements-traceability honest. The EXEMPLAR ITSELF is referenced by Plan 01's frontmatter requirements field for STP-01..08+PAP-01/03/06 traceability."
    5. `## Files Touched` — 1 file: the EXEMPLAR.
    6. `## Open Items / Deferred` — bullets:
       - "<options> attribute set may grow if EXEMPLAR sizing in Plan 02/03 reveals need (per 403-CONTEXT.md Claude's Discretion)."
       - "Token cap for `@`-resolved inlines (recommended 30k) is not numerically pinned in this Plan; Plan 03 (PLAN-AS-PROMPT.md) finalizes."
    7. `## Downstream Hooks` — bullets:
       - "STEP-PLAN-FORMAT.md (Plan 02) will quote literal excerpts from this EXEMPLAR for STP-03 success criterion 2 (every body section + every task sub-tag documented with literal example)."
       - "PLAN-AS-PROMPT.md (Plan 03) will reference this EXEMPLAR for the content-stripping rule demonstration (PAP-06) and the @`-reference resolution example (PAP-02)."
       - "STEP-EVENTS.md (Plan 04) will reference the `<options>` sub-tag for the checkpoint_auto_resolved event payload schema."
       - "v14 Build Kernel uses this file as a parser test fixture (StepPlan parser must round-trip it)."

    Mirror the language register and section depth from `402-01-SUMMARY.md`. Keep total length 80-150 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/402-01-SUMMARY.md` — full Phase 402 SUMMARY exemplar. Mirror Section headers, bullet density, status line format.
        - Grep pattern: `grep -nE "^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/402-01-SUMMARY.md` — confirms section anchors to mirror.
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md "Per-plan SUMMARY.md is mandatory" subsection — confirms the gate this task closes.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY; no executable artifacts.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/01-exemplar-stepnplan-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 60)}' \
        && grep -q "Plan 403-01" "$F" \
        && grep -q "Status:" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "EXEMPLAR-stepNPLAN.md" "$F" \
        && grep -q "CompactionSnapshot" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - SUMMARY file exists with ≥60 lines.
    - References Plan 01, the EXEMPLAR file, and CompactionSnapshot subject.
    - All four core sections present: What Was Built, Key Decisions, Files Touched, Downstream Hooks.
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate (CLAUDE.md mandatory) closed for Plan 01. Downstream consumers can find the EXEMPLAR file via the SUMMARY's path reference.
  </done>
</task>

</tasks>

<verification>
- File `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` exists with ≥250 lines.
- File `.planning/milestones/v41/phases/403/01-exemplar-stepnplan-SUMMARY.md` exists with ≥60 lines.
- All 9 body sections present in the EXEMPLAR.
- All 3 task type forms (auto+tdd, auto, checkpoint:decision) demonstrated.
- `<options>` sub-tag with pros/cons attributes present.
- `GSD-Test-Result: FAIL` and `PASS` both present (RED-before-GREEN).
- No `state.teach.` references (mode isolation).
- No path-traversal `@`-references (`@/...` or `@../...`).
</verification>

<success_criteria>
- EXEMPLAR-stepNPLAN.md exists at the canonical path and is a fully realized worked example.
- Plan 02 (STEP-PLAN-FORMAT.md author) and Plan 03 (PLAN-AS-PROMPT.md author) can quote literal excerpts from any of the 9 body sections OR any of the 3 tasks for STP-03 success criterion 2.
- The EXEMPLAR's frontmatter parses as valid YAML standalone with every StepFrontmatter field present.
- The EXEMPLAR's content is realistic enough that v14 Build Kernel implementations can use it as a parser test fixture.
- Per-plan SUMMARY.md gate closed.
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` (the worked example, ≥250 lines)
- `.planning/milestones/v41/phases/403/01-exemplar-stepnplan-SUMMARY.md` (the per-plan SUMMARY, ≥60 lines)

Plan 02 and Plan 03 in Wave 1 can now begin (they depend on `01`).
</output>
