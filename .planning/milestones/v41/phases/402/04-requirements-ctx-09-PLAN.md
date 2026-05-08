---
phase: 402
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/REQUIREMENTS.md
  - .planning/milestones/v41/ROADMAP.md
autonomous: true
requirements:
  - CTX-09

must_haves:
  truths:
    - "REQUIREMENTS.md contains a CTX-09 entry under the Context Window Management category."
    - "CTX-09 entry text matches the six-step reactive overflow recovery flow defined in 402-CONTEXT.md."
    - "REQUIREMENTS.md Traceability table includes a CTX-09 row mapped to Phase 402."
    - "REQUIREMENTS.md coverage totals are updated: CTX category rises from 8 to 9; v1 total rises from 72 to 73."
    - "ROADMAP.md Phase 402 `**Requirements:**` line is updated to include CTX-09."
    - "ROADMAP.md Requirement Coverage table updates the CTX row count from 8 to 9 and total from 72 to 73."
  artifacts:
    - path: ".planning/milestones/v41/REQUIREMENTS.md"
      provides: "REQUIREMENTS.md with CTX-09 (Reactive overflow recovery) added; traceability + totals updated."
      min_lines: 256
    - path: ".planning/milestones/v41/ROADMAP.md"
      provides: "ROADMAP.md with Phase 402 Requirements line and coverage table updated for CTX-09."
      min_lines: 160
  key_links:
    - from: ".planning/milestones/v41/REQUIREMENTS.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "CTX-09 spec implementation pointer (REQUIREMENTS lists the requirement; CONTEXT-PROTOCOL.md §12 specifies it)"
      pattern: "CTX-09"
    - from: ".planning/milestones/v41/ROADMAP.md"
      to: ".planning/milestones/v41/REQUIREMENTS.md"
      via: "Phase 402 Requirements line includes CTX-09; coverage table count matches"
      pattern: "CTX-0[1-9]"
---

<objective>
Add a new requirement CTX-09 (Reactive overflow recovery) to REQUIREMENTS.md and update the Traceability table + coverage totals. Also update ROADMAP.md's Phase 402 `**Requirements:**` line and the milestone-level Requirement Coverage table to reflect the new CTX-09. CTX-09 is a NEW requirement surfaced during Phase 402's `/gsd:discuss-phase` (locked in 402-CONTEXT.md `<decisions>` section "Reactive overflow recovery (NEW — adds CTX-09)").

Purpose: Without REQUIREMENTS.md carrying CTX-09, the traceability table is incomplete and CONTEXT-PROTOCOL.md §12 cites a requirement that doesn't exist in the requirements doc. This plan closes that gap.
Output: Updated REQUIREMENTS.md with CTX-09 entry + Traceability row; updated ROADMAP.md Phase 402 Requirements line and coverage table.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/ROADMAP.md
@.planning/milestones/v41/phases/402/402-CONTEXT.md
</context>

<threat_model>
Phase 402 is design-only. Adding a requirement entry introduces no production attack surface. Threats considered:

- **Numbering collision**: If CTX-09 is added but the Traceability table is not updated, downstream tooling (gsd-roadmapper) reports orphaned coverage. Mitigation — both REQUIREMENTS.md body AND Traceability table updated atomically; verification grep checks both locations.
- **Requirement-text drift from CONTEXT.md**: If REQUIREMENTS.md text diverges from the six-step flow in 402-CONTEXT.md, CONTEXT-PROTOCOL.md §12 and REQUIREMENTS.md will disagree. Mitigation — task action embeds the exact CTX-09 text verbatim; executor copies it to REQUIREMENTS.md without rewording.
- **Milestone total miscount**: If the v1 total is updated incorrectly (e.g., still says 72), traceability appears inconsistent. Mitigation — explicit acceptance criterion checks the new total `73`.
- **ROADMAP.md drift**: ROADMAP.md's Phase 402 `**Requirements:**` line and its milestone-level coverage table must both update to include CTX-09. Mitigation — verification greps both locations.

No code changes. No secrets.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add CTX-09 to REQUIREMENTS.md and update traceability + totals</name>
  <files>
    .planning/milestones/v41/REQUIREMENTS.md
  </files>

  <read_first>
    - .planning/milestones/v41/REQUIREMENTS.md (full file — current CTX-08 entry sits before STP section; Traceability table; coverage section)
    - .planning/milestones/v41/phases/402/402-CONTEXT.md (decisions section "Reactive overflow recovery (NEW — adds CTX-09)" — verbatim source for the requirement text)
  </read_first>

  <action>
    Make three edits to REQUIREMENTS.md:

    **Edit 1: Insert CTX-09 entry under Context Window Management**

    Locate the existing CTX-08 line:
    `- [ ] **CTX-08**: Harness reads opencode's context meter via plugin hook on each tool-execute event; daemon mirrors meter state to SSE for TUI consumption.`

    Append immediately after it (new line) the following CTX-09 entry verbatim:

    ```
    - [ ] **CTX-09**: Reactive overflow recovery — when the provider rejects a request with a context-overflow error, the harness mirrors gsd-2's `_overflowRecoveryAttempted` one-shot pattern. Six-step flow: (1) strip the failing assistant turn from context; (2) force-compact (snapshot+reinject), bypassing the percent-threshold check; (3) retry the provider call once; (4) set `_overflow_recovery_attempted` flag on the active session; (5) reset the flag on next user/agent message OR on successful turn; (6) if the flag is already set when a second overflow fires within the same user turn, surface the error to the user (no infinite loop).
    ```

    **Edit 2: Update Traceability table**

    Locate the row `| CTX-08 | 402 | Pending |` in the Traceability table. Insert a new row immediately after it:

    ```
    | CTX-09 | 402 | Pending |
    ```

    **Edit 3: Update coverage totals**

    Locate the lines under `**Coverage:**`:
    ```
    - v1 requirements: 72 total (SLC: 7, CTX: 8, STP: 8, PAP: 6, PRF: 7, APG: 6, SRP: 6, DEV: 7, SUB: 9, HRN: 8)
    - Mapped to phases: 72 / 72 (100%)
    ```

    Replace with:
    ```
    - v1 requirements: 73 total (SLC: 7, CTX: 9, STP: 8, PAP: 6, PRF: 7, APG: 6, SRP: 6, DEV: 7, SUB: 9, HRN: 8)
    - Mapped to phases: 73 / 73 (100%)
    ```

    Also locate the **Phase distribution:** line:
    ```
    - Phase 402 (Slice-Cycle & Context Window Spec): 15 reqs (SLC + CTX)
    ```

    Replace with:
    ```
    - Phase 402 (Slice-Cycle & Context Window Spec): 16 reqs (SLC + CTX)
    ```

    Also add a final-line annotation at the bottom of the doc (just before the closing `*Last updated:*` line):

    ```
    *2026-05-08 — Phase 402 planning added CTX-09 (Reactive overflow recovery) per 402-CONTEXT.md `<decisions>` "Reactive overflow recovery" subsection. v1 requirement total: 72 → 73.*
    ```

    Do NOT modify any other entry. Use Edit tool for each of the three edits.

    <quality_scan>
      <code_to_reuse>
        - Known: 402-CONTEXT.md `<decisions>` "Reactive overflow recovery (NEW — adds CTX-09)" subsection — verbatim source for CTX-09 text
        - Known: REQUIREMENTS.md existing CTX-01..CTX-08 entries — pattern for the new bullet (markdown checkbox + bold REQ-ID + colon + text)
        - Grep pattern: `grep -n "^- \[ \] \*\*CTX-08\*\*" .planning/milestones/v41/REQUIREMENTS.md` (locate insertion point)
        - Grep pattern: `grep -n "| CTX-08 | 402" .planning/milestones/v41/REQUIREMENTS.md` (locate Traceability insertion point)
        - Grep pattern: `grep -n "v1 requirements: 72 total" .planning/milestones/v41/REQUIREMENTS.md` (locate totals line)
      </code_to_reuse>
      <docs_to_consult>
        - 402-CONTEXT.md `<decisions>` "Reactive overflow recovery" subsection — full six-step flow
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendment only.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>grep -q "^- \[ \] \*\*CTX-09\*\*" .planning/milestones/v41/REQUIREMENTS.md && \
grep -q "_overflow_recovery_attempted" .planning/milestones/v41/REQUIREMENTS.md && \
grep -q "^| CTX-09 | 402 | Pending |$" .planning/milestones/v41/REQUIREMENTS.md && \
grep -q "v1 requirements: 73 total" .planning/milestones/v41/REQUIREMENTS.md && \
grep -q "CTX: 9" .planning/milestones/v41/REQUIREMENTS.md && \
grep -q "Mapped to phases: 73 / 73" .planning/milestones/v41/REQUIREMENTS.md && \
grep -q "16 reqs (SLC + CTX)" .planning/milestones/v41/REQUIREMENTS.md && \
! grep -q "v1 requirements: 72 total" .planning/milestones/v41/REQUIREMENTS.md && \
! grep -q "Mapped to phases: 72 / 72" .planning/milestones/v41/REQUIREMENTS.md</automated>
  </verify>

  <acceptance_criteria>
    - CTX-09 entry exists in body, exactly one occurrence: `[ "$(grep -c '^- \[ \] \*\*CTX-09\*\*' .planning/milestones/v41/REQUIREMENTS.md)" -eq 1 ]`.
    - Traceability table has CTX-09 row.
    - Six-step flow content present: phrases `_overflow_recovery_attempted`, `force-compact`, `surface the error to the user` all greppable in CTX-09 entry.
    - Coverage totals updated to 73 (CTX: 9). Old "72 total" and "72 / 72" strings absent.
    - Original CTX-01..CTX-08 entries unchanged: `for n in 01 02 03 04 05 06 07 08; do grep -q "^- \[ \] \*\*CTX-$n\*\*" .planning/milestones/v41/REQUIREMENTS.md || echo "MISSING CTX-$n"; done` produces no output.
    - REQUIREMENTS.md line count increased by ≥3 over original (verify against git: `git diff --stat .planning/milestones/v41/REQUIREMENTS.md | tail -1` shows insertions ≥3).
  </acceptance_criteria>

  <done>
    REQUIREMENTS.md carries CTX-09 (Reactive overflow recovery) under Context Window Management with the full six-step flow. Traceability table includes a `CTX-09 | 402 | Pending` row. Coverage totals updated to 73 reqs (CTX: 9). All other entries preserved unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update ROADMAP.md Phase 402 requirements + milestone coverage table</name>
  <files>
    .planning/milestones/v41/ROADMAP.md
  </files>

  <read_first>
    - .planning/milestones/v41/ROADMAP.md (full file — Phase 402 detail section + Requirement Coverage table)
    - .planning/milestones/v41/REQUIREMENTS.md (post-Task-1 state — to confirm CTX-09 is landed before mirroring counts in ROADMAP)
  </read_first>

  <action>
    Make two edits to ROADMAP.md:

    **Edit 1: Update Phase 402 Requirements line**

    Locate this line in the Phase 402 detail section:
    ```
    **Requirements**: SLC-01, SLC-02, SLC-03, SLC-04, SLC-05, SLC-06, SLC-07, CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CTX-07, CTX-08
    ```

    Replace with:
    ```
    **Requirements**: SLC-01, SLC-02, SLC-03, SLC-04, SLC-05, SLC-06, SLC-07, CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CTX-07, CTX-08, CTX-09
    ```

    **Edit 2: Update milestone-level Requirement Coverage table**

    Locate the table row:
    ```
    | CTX — Context Window Management | 8 | CTX-01..CTX-08 | 402 |
    ```

    Replace with:
    ```
    | CTX — Context Window Management | 9 | CTX-01..CTX-09 | 402 |
    ```

    Also locate the totals row:
    ```
    | **Total** | **72** | — | **100% mapped** |
    ```

    Replace with:
    ```
    | **Total** | **73** | — | **100% mapped** |
    ```

    Do NOT modify any other phase's row, the Phase 402 Goal, or any other section. Use Edit tool for each replacement.

    <quality_scan>
      <code_to_reuse>
        - Known: ROADMAP.md current Phase 402 Requirements line — exact pre-edit string
        - Known: ROADMAP.md current Requirement Coverage table CTX row + Total row
        - Grep pattern: `grep -n "CTX-01..CTX-08\|\*\*Requirements\*\*: SLC-01\|\*\*Total\*\* | \*\*72\*\*" .planning/milestones/v41/ROADMAP.md` (locate all three edit anchors)
      </code_to_reuse>
      <docs_to_consult>
        - REQUIREMENTS.md after Task 1 — confirm CTX-09 landed before ROADMAP edit
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendment only.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>grep -q "CTX-08, CTX-09" .planning/milestones/v41/ROADMAP.md && \
grep -q "| CTX — Context Window Management | 9 | CTX-01..CTX-09 | 402 |" .planning/milestones/v41/ROADMAP.md && \
grep -q "| \*\*Total\*\* | \*\*73\*\* | — | \*\*100% mapped\*\* |" .planning/milestones/v41/ROADMAP.md && \
! grep -q "| CTX — Context Window Management | 8 | CTX-01..CTX-08 | 402 |" .planning/milestones/v41/ROADMAP.md && \
! grep -q "| \*\*Total\*\* | \*\*72\*\* | — | \*\*100% mapped\*\* |" .planning/milestones/v41/ROADMAP.md</automated>
  </verify>

  <acceptance_criteria>
    - Phase 402 Requirements line includes CTX-09 (verified by grep `CTX-08, CTX-09`).
    - Coverage table CTX row updated to count 9 and range `CTX-01..CTX-09`.
    - Coverage Total updated from 72 to 73.
    - Old `CTX-01..CTX-08` form absent from coverage table.
    - Old `**Total** | **72**` row absent.
    - All other phase rows (Phases 403, 404, 405, 406) unchanged: `for n in 403 404 405 406; do grep -q "Phase $n:" .planning/milestones/v41/ROADMAP.md || echo "MISSING Phase $n"; done` produces no output.
    - Phase 402 Goal line unchanged: `grep -q "The Slice cycle is canonically defined as the cycle owner" .planning/milestones/v41/ROADMAP.md`.
  </acceptance_criteria>

  <done>
    ROADMAP.md Phase 402 Requirements line carries CTX-09. Milestone-level Requirement Coverage table reflects CTX category at 9 reqs and grand total at 73. No other phase metadata altered.
  </done>
</task>

</tasks>

<verification>
- REQUIREMENTS.md contains CTX-09 entry (body + Traceability table) with the six-step flow text.
- REQUIREMENTS.md totals updated: CTX category from 8→9; v1 milestone total from 72→73.
- ROADMAP.md Phase 402 Requirements line includes CTX-09.
- ROADMAP.md milestone Requirement Coverage table updated: CTX row 8→9; Total 72→73.
- Both files validate: `for f in REQUIREMENTS.md ROADMAP.md; do grep -q "CTX-09" .planning/milestones/v41/$f || echo "MISSING in $f"; done` produces no output.

**Cross-plan ordering note (wave 1 invariant):** This plan and Plan 02 both run in wave 1 with disjoint `files_modified` (Plan 04 owns REQUIREMENTS.md + ROADMAP.md; Plan 02 owns specs/CONTEXT-PROTOCOL.md). The CTX-09 traceability invariant — "REQUIREMENTS.md contains CTX-09 AND CONTEXT-PROTOCOL.md §12 cites CTX-09" — closes only when BOTH plans land. Either order within wave 1 is acceptable; the verifier asserting the joint invariant must run after wave 1 completes (e.g., `<verify>`-phase or phase-close). Plan 04 alone cannot prove §12 exists; Plan 02 alone cannot prove the REQ-ID is registered. No `depends_on` edge added — serializing wave 1 is unnecessary; the joint check belongs to phase-close, not Plan 04.
</verification>

<success_criteria>
- CTX-09 is a first-class requirement in the v41 traceability chain.
- CONTEXT-PROTOCOL.md §12 (Reactive Overflow Recovery, owned by Plan 02) cites a REQ-ID that exists in REQUIREMENTS.md. (Cross-plan invariant: closes at end of wave 1 once both Plan 02 and Plan 04 have landed; either order acceptable since their `files_modified` sets are disjoint. Verifier check belongs to phase-close, not to Plan 04 in isolation.)
- Phase 402's requirements coverage is closed: every REQ-ID listed in ROADMAP.md Phase 402 detail (SLC-01..07 + CTX-01..09) has a corresponding entry in REQUIREMENTS.md.
- gsd-roadmapper / planner / checker tooling reads consistent counts across both docs.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/402/402-04-SUMMARY.md` per project rule. The SUMMARY MUST: (a) confirm CTX-09 added to REQUIREMENTS.md body + Traceability + coverage totals, (b) confirm ROADMAP.md Phase 402 Requirements line + Coverage table updated, (c) note traceability is now closed for the new CTX-09 with CONTEXT-PROTOCOL.md §12 (Plan 02's deliverable), (d) link to the CONTEXT.md decision rationale.
</output>
