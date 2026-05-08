---
phase: 402
plan: 03
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - .planning/milestones/v40/phases/400/specs/TIER-SLICE.md
  - .planning/milestones/v40/phases/400/specs/TIER-STEP.md
  - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
  - .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md
  - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
  - .planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md
  - .planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md
autonomous: true
requirements:
  - SLC-07

must_haves:
  truths:
    - "Every v40 spec doc affected by the Slice-owns-cycle correction has a `## v41 Amendment` block at the bottom."
    - "Each amendment cites the prior v40 model and the v41 canonical model with a path-link to SLICE-CYCLE.md."
    - "Original v40 spec text is untouched; amendments are appended (no in-line strikethroughs)."
    - "EVENT-TAXONOMY.md amendment introduces the four `state.slice.{stage}_completed` events from SLICE-CYCLE.md §7."
    - "COMPOSITE-CASCADE.md amendment confirms cascade stops at Slice (Step is leaf)."
  artifacts:
    - path: ".planning/milestones/v40/phases/400/specs/TIER-SLICE.md"
      provides: "v40 TIER-SLICE.md with v41 amendment block clarifying Slice owns four-stage cycle."
      min_lines: 200
    - path: ".planning/milestones/v40/phases/400/specs/TIER-STEP.md"
      provides: "v40 TIER-STEP.md with v41 amendment forward-pointer (Step is leaf)."
      min_lines: 100
    - path: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      provides: "v40 EVENT-TAXONOMY.md with v41 amendment listing the four new stage-boundary events."
      min_lines: 220
    - path: ".planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md"
      provides: "v40 COMPOSITE-CASCADE.md with v41 amendment confirming cascade stops at Slice."
      min_lines: 100
    - path: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      provides: "v40 ARTIFACT-CATALOG.md with v41 pointer-amendment to SLC-06 superseding layout."
      min_lines: 700
    - path: ".planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md"
      provides: "v40 DIRECTORY-TREE.md with v41 pointer-amendment."
      min_lines: 500
    - path: ".planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md"
      provides: "v40 CROSS-REFERENCES.md with v41 pointer-amendment."
      min_lines: 350
  key_links:
    - from: ".planning/milestones/v40/phases/400/specs/TIER-SLICE.md"
      to: ".planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md"
      via: "v41 Amendment block forward-pointer"
      pattern: "v41/phases/402/specs/SLICE-CYCLE\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md"
      via: "v41 Amendment block forward-pointer + new event listing"
      pattern: "state\\.slice\\.(design|research|run|verify)_completed"
---

<objective>
Append `## v41 Amendment` blocks to every v40 spec doc affected by the Slice-owns-cycle correction (SLC-07). Each amendment cites the prior v40 model + the v41 canonical model and forward-points to `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`. Original v40 spec text is untouched (append-only; no in-line strikethroughs) — amendments read as published corrections.

Purpose: Closes SLC-07. Without these forward-pointers, future readers of v40 docs would not know cycle-ownership was reassigned to Slice in v41.
Output: Seven v40 markdown files, each with a `## v41 Amendment` block at the bottom.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/milestones/v41/phases/402/402-CONTEXT.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/TIER-SLICE.md
@.planning/milestones/v40/phases/400/specs/TIER-STEP.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md
@.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
@.planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md
@.planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md
</context>

<threat_model>
Phase 402 is design-only. Amendment blocks introduce no production attack surface. Threats considered:

- **Amendment overwriting existing spec text**: If the amendment writer accidentally edits non-amendment regions, v40 spec history is corrupted. Mitigation — every amendment is APPENDED (write to end of file); the executor must use Edit with unique header anchor `## v41 Amendment` (which does not exist in v40 docs) so insertions are unambiguous; verification grep checks line counts (must be ≥ original) and confirms v40 H1 + first H2 are unchanged.
- **Forward-pointer drift**: If SLICE-CYCLE.md path changes between Plan 01 and Plan 03 (e.g., user moves the file), amendment pointers break. Mitigation — depends_on: [01] enforces ordering; verify-phase grep confirms the cited path resolves at amendment time.
- **Amendment text conflict with v40 model**: If the amendment language contradicts v40 base spec without acknowledging "v41 supersedes", reader is confused. Mitigation — every amendment explicitly opens with "Prior model (v40):" + "Canonical model (v41):" structure.
- **Mode-isolation drift**: Amendments must not introduce Teach-mode references. Mitigation — amendment text reused across files; pre-written in this plan; reviewed once.

No production code changes. No secrets. No network calls.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Append v41 amendments to v40 Phase 400 specs (4 files)</name>
  <files>
    .planning/milestones/v40/phases/400/specs/TIER-SLICE.md,
    .planning/milestones/v40/phases/400/specs/TIER-STEP.md,
    .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md,
    .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md (the canonical doc the amendments forward-point to — sections "The Four Stages", "Stage-Boundary Events", "Step is a Leaf Artifact")
    - .planning/milestones/v41/phases/402/402-CONTEXT.md `<decisions>` "v40 amendment writing" + "v40 docs requiring amendment headers" subsections
    - .planning/milestones/v40/phases/400/specs/TIER-SLICE.md (full file — to know where to append)
    - .planning/milestones/v40/phases/400/specs/TIER-STEP.md (full file)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md lines 60-150 (existing Slice/Step events)
    - .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md lines 1-80 (cascade rules)
  </read_first>

  <action>
    For each of the four Phase 400 spec files, append a `## v41 Amendment` block at the very end of the file using the Edit tool (or Write if append is unsupported — read full file content, append, write back). The block content per file is below (copy verbatim).

    **Common amendment structure (used by all four blocks):**

    ```
    ---

    ## v41 Amendment

    **Amended:** Phase 402 (v41 milestone — Slice-Cycle & Context Window Spec)
    **Cause:** SLC-07 — Slice-owns-cycle correction; v40 cycle-ownership ambiguity is resolved canonically in v41.
    **Canonical successor:** [`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md)

    ### Prior model (v40)
    {file-specific prior-model paragraph}

    ### Canonical model (v41)
    {file-specific canonical-model paragraph}

    ### Effect on this document
    {file-specific effect paragraph}

    *Original v40 spec text above this amendment block is untouched. This amendment is a published correction, appended per Phase 402 convention (no in-line strikethroughs).*
    ```

    **Per-file content:**

    ### A. `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md`

    - Prior model (v40): "TIER-SLICE.md (v40) defined Slice as the terminal container tier and listed DESIGN.md / RESEARCH.md / step1PLAN.md..stepNPLAN.md / VERIFICATION.md / SUMMARY.md as owned artifacts under a `Workflow order (D-06): design → research → run → verify → summary` shape. Cycle ownership between Slice and Step was implicit — v40 D-04 already constrained Steps to flat files, but no doc explicitly said the four-stage cycle is owned by Slice."
    - Canonical model (v41): "Slice owns the four-stage cycle: **design-slice → research-slice → run-slice → verify-slice**. Step is a leaf artifact (`stepNPLAN.md`, `stepNSUMMARY.md`) consumed by run-slice. The Slice cycle terms and the canonical Slice folder layout (with producer-stage mapping) are defined in [`SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md). The v41 vocabulary table reconciles v41 REQUIREMENTS' `discuss-slice/plan-slice/execute-slice` to the canonical `design-slice/research-slice/run-slice/verify-slice` terms."
    - Effect: "TIER-SLICE.md's `## State Machine`, `## Owned Artifacts`, and `## Frontmatter Fields` sections remain authoritative for Slice FSM and frontmatter shape. The `Workflow order (D-06)` line is forward-pointed to SLICE-CYCLE.md for the canonical four-stage terminology and per-stage owner/inputs/outputs."

    ### B. `.planning/milestones/v40/phases/400/specs/TIER-STEP.md`

    - Prior model (v40): "TIER-STEP.md (v40) defined Step as the smallest unit of work, owning a `design → plan → run → verify` cycle in its own state machine (`idle → designing → planning → running → verifying → done`). D-04 constrained Steps to flat files within the parent Slice folder, but the Step state machine implied Step also 'owns' a four-phase cycle."
    - Canonical model (v41): "Step is a **leaf artifact** of the Slice's run-slice stage. Step's `state.step.designed/planned/ran/verify_passed` events represent **intra-run-slice granularity** — they track Step lifecycle as run-slice executes each `stepNPLAN.md` per DAG ordering. Step does NOT own its own four-stage Slice cycle. The cycle owner is the parent Slice; canonical definition in [`SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md)."
    - Effect: "TIER-STEP.md's state machine and event tables remain authoritative for Step lifecycle within run-slice. Readers should treat Step as a leaf within the Slice cycle, not a parallel cycle owner."

    ### C. `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`

    - Prior model (v40): "EVENT-TAXONOMY.md (v40) catalogued 33 events across Arc/Stage/Slice/Step tiers and 2 composite events. Slice events covered FSM transitions (`created`, `worktree_ready`, `started`, `shipped`, `reverted`, `replanned`, `blocked`, `unblocked`, `deferred`, `undeferred`, `updated`) but NOT stage-boundary events for the four Slice stages because cycle ownership was implicit."
    - Canonical model (v41): "Four NEW stage-boundary events are added at the Slice tier — one per stage of the four-stage Slice cycle defined in [`SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md):"

      ```
      | Event Type                          | Trigger                                | Aggregate | Data Fields                                                                                                          |
      |-------------------------------------|----------------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------|
      | state.slice.design_completed        | design-slice produces DESIGN.md + DECISIONS.md       | slice     | slice_id: str, stage: Literal["design"], produced_artifacts: list[str], completed_at: datetime                       |
      | state.slice.research_completed      | research-slice's four sub-stages all produce artifacts | slice     | slice_id: str, stage: Literal["research"], produced_artifacts: list[str], completed_at: datetime                     |
      | state.slice.run_completed           | run-slice writes all stepNSUMMARY.md files            | slice     | slice_id: str, stage: Literal["run"], produced_artifacts: list[str], completed_at: datetime                          |
      | state.slice.verify_completed        | verify-slice writes N-VERIFICATION.md                 | slice     | slice_id: str, stage: Literal["verify"], produced_artifacts: list[str], completed_at: datetime                       |
      ```

      "Plus one event added for cross-session compaction lineage:"

      ```
      | Event Type                          | Trigger                                | Aggregate | Data Fields                                                                                                          |
      |-------------------------------------|----------------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------|
      | compaction.snapshot_taken           | Threshold/overflow/manual compaction fires | session   | (see CONTEXT-PROTOCOL.md §8 — full CompactionSnapshot Pydantic shape)                                                |
      | compaction.reinject_completed       | Daemon's `chat.params` ack on new session | session   | (see CONTEXT-PROTOCOL.md §10 — full CompactionReinjectCompleted Pydantic shape)                                       |
      ```

    - Effect: "Event count rises from 33 to 39 (+4 stage-boundary, +2 compaction lifecycle). The `BUILD_ONLY_EVENT_PREFIXES` frozenset gains `\"compaction.\"` per the new compaction events. Mode-isolation rules unchanged — all new events are build-mode only. Full schema for the compaction events is owned by [`CONTEXT-PROTOCOL.md`](../../../v41/phases/402/specs/CONTEXT-PROTOCOL.md) §8 + §10."

    ### D. `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md`

    - Prior model (v40): "COMPOSITE-CASCADE.md (v40) documented the upward cascade Step → Slice → Stage → Arc, with composite events `state.slice.steps_completed`, `state.stage.slices_shipped`, `state.arc.stages_shipped`. Step → Slice cascade fires when ALL child Steps reach `done`."
    - Canonical model (v41): "Cascade rules remain unchanged. Confirmation: Step is a leaf artifact (per [`SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md) §'Step is a Leaf Artifact'); the cascade STOPS at Slice. There is no Step-owned cycle to cascade above; the four Slice stage-boundary events (`state.slice.{design,research,run,verify}_completed` per the EVENT-TAXONOMY v41 amendment) fire WITHIN a Slice's lifecycle, not as Step → Slice composite cascades. They are intra-Slice progress markers, not cross-tier rollup events."
    - Effect: "No cascade-rule changes. The doc's existing `## Step → Slice Cascade` section is correct; Step `state.step.verify_passed` (last child Step) still triggers `state.slice.steps_completed`, which (combined with VERIFICATION.md passing) advances the Slice to `shipped`. The four new stage-boundary events documented in EVENT-TAXONOMY's v41 amendment are NOT composite cascade events — they are intra-Slice and are emitted directly by the agent / daemon at each stage boundary."

    Use the Edit tool with the exact append pattern. For each file: (a) Read final ~20 lines, (b) Edit by appending the amendment block after the last existing line, (c) Verify the file ends with the amendment.

    Mode isolation note inside each amendment block: "All v41-introduced events remain build-mode only (`state.slice.*`, `compaction.*` prefixes). Teach-mode harness is v47 scope."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` §"v40 Amendment Targets" — already enumerates exactly these four files (Plan 01 owns the checklist; Plan 03 executes against it)
        - Known: 402-CONTEXT.md `<decisions>` section "v40 amendment writing" — declares append-only convention
        - Grep pattern: `grep -n "^## " .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md | tail -3` (find last H2 to confirm append target)
      </code_to_reuse>
      <docs_to_consult>
        - SLICE-CYCLE.md §"Stage-Boundary Events" — source of the four new event names + data field set
        - SLICE-CYCLE.md §"Step is a Leaf Artifact" — source for the COMPOSITE-CASCADE amendment text
        - 402-CONTEXT.md `<decisions>` "v40 amendment writing" subsection — append-only convention
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendments only.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>for f in TIER-SLICE TIER-STEP EVENT-TAXONOMY COMPOSITE-CASCADE; do \
  grep -q "^## v41 Amendment" .planning/milestones/v40/phases/400/specs/$f.md || { echo "MISSING amendment header in $f"; exit 1; }; \
  grep -q "v41/phases/402/specs/SLICE-CYCLE.md" .planning/milestones/v40/phases/400/specs/$f.md || { echo "MISSING canonical-successor link in $f"; exit 1; }; \
done && \
grep -q "state.slice.design_completed" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md && \
grep -q "state.slice.research_completed" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md && \
grep -q "state.slice.run_completed" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md && \
grep -q "state.slice.verify_completed" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md && \
grep -q "compaction.snapshot_taken" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md && \
grep -q "compaction.reinject_completed" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md && \
grep -q "leaf artifact" .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md</automated>
  </verify>

  <acceptance_criteria>
    - All four Phase 400 spec files have a `## v41 Amendment` H2.
    - All four amendments include the exact link `v41/phases/402/specs/SLICE-CYCLE.md`.
    - EVENT-TAXONOMY.md amendment includes all four `state.slice.{design,research,run,verify}_completed` events AND the two compaction lifecycle events.
    - COMPOSITE-CASCADE.md amendment includes the phrase "leaf artifact" confirming cascade stops at Slice.
    - Original v40 H1 lines unchanged (exact strings from pre-edit `head -1`):
      - `grep -q "^# Tier Specification: Slice$" .planning/milestones/v40/phases/400/specs/TIER-SLICE.md`
      - `grep -q "^# Tier Specification: Step$" .planning/milestones/v40/phases/400/specs/TIER-STEP.md`
      - `grep -q "^# Event Taxonomy — All Four Tiers$" .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`
      - `grep -q "^# Composite Event Cascade — Step→Slice→Stage→Arc$" .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md`
    - Append-only behavior: the `## v41 Amendment` H2 appears exactly once at end-of-file in each target, AND each original H1 above is still the file's first non-empty line. The combination of H1-unchanged + amendment-header-present is sufficient evidence of append-only behavior; no separate line-count-delta check is required.
  </acceptance_criteria>

  <done>
    All four Phase 400 spec files carry a `## v41 Amendment` block at the end. Forward-pointers to SLICE-CYCLE.md resolve. EVENT-TAXONOMY.md's amendment lists the four new stage-boundary events plus the two compaction lifecycle events. COMPOSITE-CASCADE.md confirms cascade stops at Slice. Original v40 spec text unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append v41 pointer-amendments to v40 Phase 401 specs (3 files)</name>
  <files>
    .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md,
    .planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md,
    .planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md §"Canonical Slice Folder Layout (SLC-06 amended)"
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (skim section headings; locate any reference to Slice folder layout)
    - .planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md (skim — locate any Slice subdirectory tree)
    - .planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md (skim — locate any Slice-cycle-vocabulary reference)
  </read_first>

  <action>
    Append a lightweight `## v41 Amendment` block to each of the three Phase 401 specs. These are pointer-amendments only (Phase 401 already enumerated DESIGN/DECISIONS/RESEARCH/stepNPLAN/VERIFICATION/SUMMARY artifacts per CONTEXT.md "v40 docs requiring amendment headers" subsection — content is mostly aligned, the amendment is a forward-pointer for readers).

    **Common pointer-amendment template** (used by all three):

    ```
    ---

    ## v41 Amendment

    **Amended:** Phase 402 (v41 milestone — Slice-Cycle & Context Window Spec)
    **Cause:** SLC-06 / SLC-07 — canonical Slice folder layout + cycle ownership.
    **Canonical successor:** [`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md) §"Canonical Slice Folder Layout (SLC-06 amended)"

    ### Effect on this document
    {file-specific effect paragraph}

    *Original v40 spec text above this amendment block is untouched.*
    ```

    **Per-file effect paragraphs:**

    - `ARTIFACT-CATALOG.md`: "Artifact catalog (ART-01) entries for the Slice tier remain authoritative for filename, schema owner, and immutability. SLICE-CYCLE.md adds the producer-stage mapping (which of design-slice / research-slice / run-slice / verify-slice writes each artifact) and the v41 vocabulary reconciliation. Readers consulting this catalog for v41+ scheduling should cross-reference SLICE-CYCLE.md §'Canonical Slice Folder Layout'."

    - `DIRECTORY-TREE.md`: "Directory tree (DSK-01) Slice subdirectory layout remains authoritative for path shape (`.state/build/arcs/arc-N/stages/stage-N/slices/slice-N/`). SLICE-CYCLE.md §'Canonical Slice Folder Layout' enumerates the per-file producer stage; the two specs are non-conflicting (DIRECTORY-TREE owns paths; SLICE-CYCLE owns producer mapping)."

    - `CROSS-REFERENCES.md`: "Cross-reference format (REF-01) and edge-type semantics (REF-02) remain authoritative. The four-stage Slice cycle vocabulary (`design-slice`, `research-slice`, `run-slice`, `verify-slice`) is reconciled against v41 REQUIREMENTS' alternate vocabulary (`discuss-slice`, `plan-slice`, `execute-slice`) by the SLICE-CYCLE.md vocabulary mapping table; references that use either vocabulary resolve via that table."

    Use Edit tool to append. Preserve all existing content.

    <quality_scan>
      <code_to_reuse>
        - Known: SLICE-CYCLE.md §"Canonical Slice Folder Layout" — source paragraph the pointer-amendments cite
        - Known: 402-CONTEXT.md `<decisions>` "v40 docs requiring amendment headers" — confirms these three are pointer-only (minor additions)
        - Grep pattern: `grep -n "^## " .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md | tail -2` to locate end-of-file H2
      </code_to_reuse>
      <docs_to_consult>
        - SLICE-CYCLE.md §"v40 Amendment Targets" bulleted list — names these three files
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendments only.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>for f in ARTIFACT-CATALOG DIRECTORY-TREE CROSS-REFERENCES; do \
  grep -q "^## v41 Amendment" .planning/milestones/v40/phases/401/specs/$f.md || { echo "MISSING amendment header in 401/$f"; exit 1; }; \
  grep -q "v41/phases/402/specs/SLICE-CYCLE.md" .planning/milestones/v40/phases/401/specs/$f.md || { echo "MISSING canonical-successor link in 401/$f"; exit 1; }; \
done</automated>
  </verify>

  <acceptance_criteria>
    - All three Phase 401 spec files have a `## v41 Amendment` H2.
    - All three amendments include the exact link `v41/phases/402/specs/SLICE-CYCLE.md`.
    - Original v40 H1 lines unchanged (exact strings from pre-edit `head -1`):
      - `grep -q "^# Artifact Catalog: \`.state/build/\` Complete Blueprint$" .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md`
      - `grep -q "^# Directory Tree: \`.state/build/\` Filesystem Blueprint$" .planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md`
      - `grep -q "^# Cross-Reference System: Format, Resolution, Edge Semantics, Dependency Policy, and Broken Reference Handling$" .planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md`
    - Append-only behavior: the `## v41 Amendment` H2 appears exactly once at end-of-file in each target, AND each original H1 above is still the file's first non-empty line. The combination of H1-unchanged + amendment-header-present is sufficient evidence of append-only behavior; no separate line-count-delta check is required.
  </acceptance_criteria>

  <done>
    All three Phase 401 spec files carry a lightweight `## v41 Amendment` block at the end with a forward-pointer to SLICE-CYCLE.md. Original v40 spec text unchanged.
  </done>
</task>

</tasks>

<verification>
- Seven v40 spec files modified (4 in Phase 400 specs/, 3 in Phase 401 specs/).
- Every modified file ends with a `## v41 Amendment` block.
- Every amendment forward-points to `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`.
- EVENT-TAXONOMY.md amendment lists the four `state.slice.{stage}_completed` events plus the two compaction lifecycle events.
- All v40 H1 lines unchanged (proves append-only).
- All v40 line counts strictly increased (proves append-only).
</verification>

<success_criteria>
- ROADMAP.md success criterion 2 satisfied: v41 amendment headers appended to every Phase 400 spec affected by SLC-07; each cites prior model + v41 canonical model.
- Future readers of v40 docs encounter the amendment block and follow the forward-pointer to SLICE-CYCLE.md.
- v14 Build Kernel implementer reading v40 EVENT-TAXONOMY.md sees the four new stage-boundary events + two compaction events without needing to discover them in v41 specs.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/402/402-03-SUMMARY.md` per project rule. The SUMMARY MUST: (a) list all seven amended files with line-count delta, (b) confirm each amendment's forward-pointer resolves to `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`, (c) note any v40 doc that was inspected but did NOT need an amendment (and why), (d) confirm SLC-07 is closed.
</output>
