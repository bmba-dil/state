---
phase: 402
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
autonomous: true
requirements:
  - SLC-01
  - SLC-02
  - SLC-03
  - SLC-04
  - SLC-05
  - SLC-06
  - SLC-07

must_haves:
  truths:
    - "SLICE-CYCLE.md exists and is the canonical Slice-cycle definition for v41+."
    - "All four Slice stages are defined with v40 vocabulary (design-slice, research-slice, run-slice, verify-slice)."
    - "Every stage has explicit owner, inputs, outputs, stage-boundary event."
    - "The canonical Slice folder layout is enumerated with each artifact's producing stage."
    - "v40↔v41 vocabulary mapping table is present so downstream readers can translate either direction."
  artifacts:
    - path: ".planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md"
      provides: "Canonical 4-stage Slice cycle definition (covers SLC-01..07)."
      min_lines: 250
  key_links:
    - from: ".planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md"
      to: ".planning/milestones/v41/REQUIREMENTS.md"
      via: "REQ-ID citations in section bodies"
      pattern: "SLC-0[1-7]"
    - from: ".planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md"
      to: ".planning/milestones/v40/phases/400/specs/TIER-SLICE.md"
      via: "v40 amendment forward-pointer (SLC-07)"
      pattern: "TIER-SLICE\\.md"
---

<objective>
Author the canonical Slice-cycle specification document for v41, fixing v40's cycle-ownership ambiguity. SLICE-CYCLE.md becomes the single source of truth for the four-stage Slice cycle (design-slice → research-slice → run-slice → verify-slice) and the canonical Slice folder layout. Every downstream v41 phase and the v14 Build Kernel implementation read this doc.

Purpose: v40 left "who owns the cycle" ambiguous between Slice and Step (D-1 of v41 HANDOFF locked Slice). This plan publishes the corrected canonical model so subsequent plans (02, 03) can cite it.
Output: One markdown spec doc at `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`, ≥250 lines, fully populated.
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
@.planning/milestones/v41/phases/402/402-CONTEXT.md
@.planning/milestones/v40/phases/400/specs/TIER-SLICE.md
@.planning/milestones/v40/phases/400/specs/TIER-STEP.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md
</context>

<threat_model>
Phase 402 is a design-only milestone phase. SLICE-CYCLE.md introduces no production attack surface — it is a markdown specification consumed by humans and downstream planning agents. Threats considered:

- **Markdown injection in cited content**: This doc cites verbatim text from CONTEXT.md and v40 specs. Mitigation — only quote from inside-repo files; no fetched/external content; quoted blocks use fenced code; no executable templating.
- **Stale-spec risk**: If the v40 amendment forward-pointer is wrong, the canonical-correction trail breaks. Mitigation — Plan 03 verifies forward-pointer round-trip after writing amendments.
- **Mode-isolation drift**: This is a Build-only spec; the doc must not introduce vocabulary that bleeds into Teach. Mitigation — explicit "Build-mode only; Teach-mode out of scope" note in the doc header.

No production code lands. No secrets. No network calls. No untrusted input.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Create specs/ subdirectory and write SLICE-CYCLE.md spec body</name>
  <files>
    .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/402/402-CONTEXT.md (full file — load-bearing decisions table, vocabulary mapping, folder layout)
    - .planning/milestones/v41/REQUIREMENTS.md (lines 1-50 — SLC-01..07 verbatim)
    - .planning/milestones/v41/HANDOFF.md (D-1, D-12 sections)
    - .planning/milestones/v40/phases/400/specs/TIER-SLICE.md (full file — current Slice definition; the doc to amend)
    - .planning/milestones/v40/phases/400/specs/TIER-STEP.md lines 1-60 (Step-as-leaf framing)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md lines 60-100 (Slice events; SLICE-CYCLE.md references stage-boundary events)
  </read_first>

  <action>
    Create the specs/ directory if missing, then write SLICE-CYCLE.md with exactly the section structure below. Copy concrete content (vocabulary mapping, folder layout) verbatim from 402-CONTEXT.md `<decisions>` section — do NOT re-derive.

    Required section list (write each as a `## ` heading in this order):

    1. `# Slice Cycle (Canonical, v41)` — H1 title.
    2. Frontmatter line block at top of doc body (after the H1): "Phase: 402", "Status: Canonical (v41)", "Supersedes: TIER-SLICE.md cycle-ownership ambiguity (v40 Phase 400)", "Requirements covered: SLC-01..07".
    3. `## Overview` — 1 paragraph stating: Slice owns the four-stage cycle; Step is a leaf artifact (not its own cycle); cite D-1 from HANDOFF.md and SLC-01.
    4. `## Vocabulary Reconciliation (v40 ↔ v41)` — Reproduce the exact 6-row mapping table from 402-CONTEXT.md `<decisions>` section "Naming reconciliation" subsection (the table beginning "| v41 REQUIREMENTS term | Canonical (Phase 402) term |"). Add a short prose note: "v40 vocabulary wins. References to v41 REQUIREMENTS' `discuss-slice/plan-slice/execute-slice` resolve to the canonical terms via this table."
    5. `## The Four Stages` — One `### ` subsection per stage in this order: `### design-slice`, `### research-slice`, `### run-slice`, `### verify-slice`. Each subsection MUST contain these labelled bullet lines verbatim (fill in values per CONTEXT.md):
       - `**Owner:**` — single agent role (e.g., "design-slice agent (build-mode `/state-design-slice` command)")
       - `**Inputs:**` — bullet list of artifacts/state read
       - `**Outputs:**` — bullet list of artifacts produced
       - `**Stage-boundary event:**` — single event name from the v40 EVENT-TAXONOMY (or a NEW event named here for v41 — if NEW, mark `(NEW in v41 — added in Phase 402; v40 EVENT-TAXONOMY.md gets v41 amendment in Plan 03)`)
       - `**REQ-IDs covered:**` — comma-separated SLC-IDs, e.g., `SLC-02` for design-slice, `SLC-03` for research-slice (multi-stage internal pipeline; enumerate the four sub-stages: research → pattern-mapping → planning → validation, each producing an artifact per CONTEXT.md), `SLC-04` for run-slice, `SLC-05` for verify-slice
       Per-stage content sourced verbatim from 402-CONTEXT.md `<decisions>` "design-slice produces", "research-slice is a multi-stage internal pipeline", "run-slice runs each Step's stepNPLAN.md", "verify-slice writes N-VERIFICATION.md".
       For research-slice, document the four-sub-stage internal pipeline explicitly: each of research/pattern-mapping/planning/validation has its own bullet listing the artifact it produces (`N-RESEARCH.md`, `N-PATTERNS.md`, `stepNPLAN.md` per Step, `N-VALIDATION.md`). Note that validation re-runs planning on failure (D-12 from HANDOFF.md).
    6. `## Canonical Slice Folder Layout (SLC-06 amended)` — Reproduce verbatim the fenced code block from 402-CONTEXT.md `<decisions>` section showing `slices/N-name/` and every artifact line including its producer-stage parenthetical. The block is the one beginning:
       ```
       slices/N-name/
         DESIGN.md            (design-slice)
         DECISIONS.md         (design-slice + run-slice append-only)
         ...
         RESUME.txt           (cross-session orientation pointer)
       ```
       After the code block, add a markdown table with two columns `| Artifact | Producing Stage |` enumerating every line of the layout for grep-greppable cross-reference. Note explicitly: this layout supersedes SLC-06's v41 form (`N-CONTEXT.md` / `N-DISCUSSION-LOG.md`) — those v41 artifacts are renamed to v40 vocabulary (`DESIGN.md` / `DECISIONS.md`) per the vocabulary table.
    7. `## Stage-Boundary Events` — Markdown table `| Event Type | Trigger | Aggregate | Data Fields |`. Document four events (one per stage boundary): `state.slice.design_completed`, `state.slice.research_completed`, `state.slice.run_completed`, `state.slice.verify_completed`. Use the existing `state.slice.*` event-naming convention from v40 EVENT-TAXONOMY.md. Mark all four as `(NEW in v41 — to be added to v40 EVENT-TAXONOMY.md via Plan 03 amendment)`. Each event carries minimum fields: `slice_id: str`, `stage: Literal["design", "research", "run", "verify"]`, `produced_artifacts: list[str]` (relative paths under the Slice folder), `completed_at: datetime`. Cite SLC-05 for the `verify_completed` event being the slice-complete signal.
    8. `## Step is a Leaf Artifact (D-1 / SLC-01 explicit)` — One paragraph explicitly clarifying: Steps are flat files (`stepNPLAN.md`, `stepNSUMMARY.md`) inside the Slice folder; Steps do NOT own their own four-stage cycle; the Step "FSM" tracked in v40 EVENT-TAXONOMY (`state.step.designed/planned/ran/verify_passed`) is intra-`run-slice` granularity (run-slice runs each Step PLAN through its individual lifecycle), not a separate Slice-level cycle. Forward-pointer: "v40 TIER-STEP.md receives a v41 amendment forward-pointer to this section in Plan 03."
    9. `## v40 Amendment Targets` — Bulleted list of v40 docs that get a `## v41 Amendment` block as part of Plan 03's work (so Plan 03 has a checklist):
       - `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — clarifies Slice owns the four-stage cycle
       - `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — forward-pointer that Step is a leaf artifact
       - `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — adds the four `state.slice.{stage}_completed` events listed in §7
       - `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — confirms cascade stops at Slice (Step is leaf, no Step-owned cycle)
       - `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — pointer addition: SLC-06 layout supersedes any conflicting layout fragment
       - `.planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md` — pointer addition: same
       - `.planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md` — pointer addition only if Slice-cycle wording conflicts
    10. `## Requirements Coverage` — Markdown table `| REQ-ID | Section in this doc | Notes |`. One row per SLC-01..07.
    11. `## Cross-References` — Bulleted list pointing to: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` (sibling doc; Plan 02), `.planning/milestones/v41/REQUIREMENTS.md` (REQ source), `.planning/milestones/v41/HANDOFF.md` (D-1, D-12), `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` (target of v41 amendment).

    Mode-isolation note (must appear once in the Overview): "Build-mode only. Teach-mode harness is v47 scope; mode silos remain physical (state.build.* must not import state.teach.*)."

    Do NOT include any code beyond markdown/fenced blocks. Do NOT include placeholder language ("v1", "TODO", "FIXME", "future") — every commitment is canonical.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/402-CONTEXT.md` `<decisions>` section — copy vocabulary table and folder layout VERBATIM (do not re-derive)
        - Known: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` lines 67-93 — pattern for Slice event tables (column shape: `| Event Type | Trigger | State Transition | Data Fields |`); adapt to `| Event Type | Trigger | Aggregate | Data Fields |` since stage-boundary events are intra-Slice (no FSM transition)
        - Known: `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — reuse "Owned Artifacts" table shape for the per-stage Inputs/Outputs presentation
        - Grep pattern: `grep -n "v40 vocabulary\|v41 vocabulary\|design-slice\|research-slice\|run-slice\|verify-slice" .planning/milestones/v41/phases/402/402-CONTEXT.md` (locate every authoritative usage to cite)
      </code_to_reuse>
      <docs_to_consult>
        - 402-CONTEXT.md `<decisions>` "Naming reconciliation (v40↔v41 vocabulary)" subsection — vocabulary table is load-bearing
        - 402-CONTEXT.md `<decisions>` "Slice folder canonical layout" code block — canonical layout source
        - 402-CONTEXT.md `<decisions>` "v40 amendment writing" + "v40 docs requiring amendment headers" subsections — drives §9 of this doc
        - HANDOFF.md D-1 + D-12 — locked design decisions cited in §3 and §5
        - REQUIREMENTS.md SLC-01..07 — verbatim REQ text cited in §10
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only spec doc; no exported logic. Verification is grep-based (see <verify> + <acceptance_criteria>).
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>test -f .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
[ "$(wc -l < .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md)" -ge 250 ] && \
grep -q "^# Slice Cycle (Canonical, v41)" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^## Vocabulary Reconciliation" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^### design-slice" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^### research-slice" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^### run-slice" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^### verify-slice" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^## Canonical Slice Folder Layout" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^## Stage-Boundary Events" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^## Step is a Leaf Artifact" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^## v40 Amendment Targets" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && \
grep -q "^## Requirements Coverage" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md</automated>
  </verify>

  <acceptance_criteria>
    - File exists at `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`.
    - All 11 required H1/H2/H3 headings present (verified by `<verify>` greps).
    - Length ≥250 lines.
    - All seven SLC requirement IDs (`SLC-01`..`SLC-07`) referenced at least once in the doc body: `for n in 01 02 03 04 05 06 07; do grep -q "SLC-$n" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md || echo "MISSING SLC-$n"; done` produces no output.
    - Vocabulary mapping table present: `grep -q "discuss-slice" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && grep -q "design-slice" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`.
    - Stage-boundary events documented: `grep -q "state.slice.design_completed" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && grep -q "state.slice.run_completed" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && grep -q "state.slice.verify_completed" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && grep -q "state.slice.research_completed" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`.
    - Folder layout code fence: `grep -q "stepNPLAN.md" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && grep -q "DECISIONS.md" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md && grep -q "N-VERIFICATION.md" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`.
    - Mode-isolation note present: `grep -q "Build-mode only" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`.
    - No prohibited language: `! grep -nE "\b(v1\b|simplified|placeholder|TODO|FIXME|future)\b" .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` (the doc is canonical; no deferral markers).
  </acceptance_criteria>

  <done>
    SLICE-CYCLE.md is the canonical v41 Slice-cycle definition, ≥250 lines, with all 11 required sections, complete vocabulary mapping, full folder layout, four stage-boundary event definitions, and explicit forward-pointers for the Plan 03 amendment work. Plan 02 (CONTEXT-PROTOCOL.md) and Plan 03 (v40 amendments) can cite this doc verbatim.
  </done>
</task>

</tasks>

<verification>
- File exists at `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`.
- Doc structurally complete (all 11 H1/H2/H3 headings; length ≥250 lines).
- All 7 SLC requirement IDs cited.
- Vocabulary table, folder-layout code fence, four stage-boundary events all present.
- Doc cleared of prohibited-language markers.
</verification>

<success_criteria>
- ROADMAP.md success criterion 1 satisfied: SLICE-CYCLE.md exists and defines all four stages with owner / inputs / outputs / stage-boundary event; canonical Slice folder layout enumerated.
- Downstream plans (02, 03) can `@`-reference SLICE-CYCLE.md and pull verbatim text into their own deliverables.
- v14 Build Kernel implementer reading only SLICE-CYCLE.md + CONTEXT-PROTOCOL.md + REQUIREMENTS.md has the full canonical Slice-cycle contract.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/402/402-01-SUMMARY.md` per project rule (per-plan SUMMARY.md is mandatory, summary_strict=true). The SUMMARY MUST: (a) link to SLICE-CYCLE.md, (b) confirm all 11 sections wrote, (c) list the v40 amendment targets handed off to Plan 03, (d) note any ambiguity surfaced for downstream plans.
</output>
