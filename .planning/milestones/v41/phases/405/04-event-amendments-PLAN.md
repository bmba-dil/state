---
phase: 405
plan: 04
type: execute
wave: 2
depends_on:
  - 01
  - 02
  - 03
files_modified:
  - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
  - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
  - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
autonomous: false
requirements:
  - DEV-07
  - SUB-05
  - SUB-06
  - SUB-07
  - SUB-08
  - SUB-09

must_haves:
  truths:
    - "EVENT-TAXONOMY.md has a NEW `## v41 Amendment — Phase 405 Deviation + Subagent Event Family` block appended at the bottom (below the existing Phase 402, Phase 403, Phase 404 amendment blocks) that registers the 14 new event types introduced by Phase 405."
    - "The 14 new event types are exhaustively listed in the amendment table: state.step.deviation_logged (DEV-07), state.step.deviation_classification_rejected (DEV-07), state.step.deviation_resolution_recorded (DEV-07), state.step.deviation_cap_exceeded (DEV-07), state.step.subagent_started (SUB-05), state.step.subagent_progress (SUB-05), state.step.subagent_complete (SUB-05), state.step.subagent_spot_check_failed (SUB-06), state.step.subagent_crash_detected (SUB-07), state.step.subagent_restart (SUB-07), state.step.subagent_restart_exhausted (SUB-07), state.step.subagent_orphan_detected (SUB-08), state.step.subagent_whitelist_violation (SUB-03), state.slice.subagent_cap_expansion_rejected (SUB-04)."
    - "Each event row in the amendment table has columns: Event Type, Trigger, State Transition, Owning REQ — mirroring the Phase 402 + Phase 403 + Phase 404 v41 amendment table shape."
    - "Forward-pointers from each event row to its canonical home spec (DEVIATION-RULES.md for the 4 deviation events; SUBAGENT-MANAGEMENT.md for whitelist_violation + cap_expansion_rejected; SUBAGENT-MONITORING.md for the remaining 8 subagent events) are rendered."
    - "EVENT-TAXONOMY.md v40 original content + Phase 402 + Phase 403 + Phase 404 amendment blocks are UNCHANGED (append-only; no in-line strikethroughs); the new amendment block is appended below all of them."
    - "v40 EVENT-TAXONOMY.md final line count is ≥ 360 after this amendment (was ≥320 after Phase 404 amendment per 404 Plan-04 must_haves; expected +40 lines for 14 new events)."
    - "Naming-convention verification: every new event type matches `^state\\.(step|slice)\\.[a-z_]+$` regex — no naming-drift events."
    - "Mode-isolation note rendered: all 14 new events live in BUILD_ONLY_EVENT_PREFIXES (Build-only). CI grep `grep -nE 'state\\.teach\\.(deviation|subagent)' .planning/milestones/v41/phases/405/` MUST return zero."
    - "STATE-* naming-discipline assertion rendered: amendment block explicitly states the four STATE-* trailers (STATE-Task, STATE-DeviationRule, STATE-DeviationAttempt, STATE-Subagent-Invocation); no `GSD-` references in the amendment block."
    - "ARTIFACT-CATALOG.md has a NEW `## v41 Amendment — Phase 405 Deviation + Subagent Artifacts` block appended at the bottom (below existing Phase 402 + Phase 404 amendments) registering: `state_build/deviation/arch_patterns.py` (Python module — single-source-of-truth for ARCH_PATTERN_ALLOWLIST); `state_build/subagents/types.py` (Python module — SubagentType + STAGE_ROSTER); `state_build/subagents/returns.py` (Python module — SUBAGENT_RETURN_REGISTRY); `state_build/commit/trailers.py` (Python module — STATE-* trailer constants + infer_commit_type); `stepNSUMMARY.md` `## Deviations` section (projector-generated, owned by DEVIATION-RULES.md Section 10)."
    - "ARTIFACT-CATALOG.md amendment also registers the extension to Phase 402's CompactionSnapshot Pydantic model with the two new fields (subagent_restart_counters, in_flight_subagents) — owned by SUBAGENT-MONITORING.md Section 7."
    - "ARTIFACT-CATALOG.md v40 original content + Phase 402 + Phase 404 amendments are UNCHANGED (append-only)."
    - "Each new artifact row has columns: Filename / Module Path, Producer Stage, Schema Owner (spec doc), Immutability, Description — mirroring the v40 ARTIFACT-CATALOG.md row shape used by Phase 404 Plan 04."
    - "FRONTMATTER-SCHEMAS.md gains a `## v41 Amendment — Phase 405 SliceFrontmatter Extensions` block registering the three new Slice frontmatter fields (`autonomy: Literal['tiered','full-yolo','conservative'] | None` from DEV-06; `allowed_subagents: list[SubagentType] | None` from SUB-03; `subagent: SubagentSliceConfig | None` nested config from SUB-04 + SUB-07 holding parallel_cap / progress_timeout_s / remediation_hints) with forward-pointers to owning specs."
    - "FRONTMATTER-SCHEMAS.md v40 original content + any prior v41 amendments are UNCHANGED (append-only)."
    - "Authoritative-ordering note rendered in each amendment: Pydantic class definitions in the owning specs (DEVIATION-RULES.md / SUBAGENT-MANAGEMENT.md / SUBAGENT-MONITORING.md) are authoritative; this taxonomy / catalog / frontmatter amendment is a registry index."
    - "Plan 04 PLAN.md and final amendment text do NOT contain the literal string `GSD-` (project naming discipline)."
  artifacts:
    - path: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      provides: "v40 EVENT-TAXONOMY.md with a fourth v41 amendment block registering Phase 405's 14 new state.{step,slice}.* events with forward-pointers to DEVIATION-RULES.md / SUBAGENT-MANAGEMENT.md / SUBAGENT-MONITORING.md owning specs."
      min_lines: 360
    - path: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      provides: "v40 ARTIFACT-CATALOG.md with a third v41 amendment block registering Phase 405's four new modules (arch_patterns.py / subagents/types.py / subagents/returns.py / commit/trailers.py), the stepNSUMMARY ## Deviations section, and the CompactionSnapshot extension."
      min_lines: 870
    - path: ".planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md"
      provides: "v40 FRONTMATTER-SCHEMAS.md with a v41 amendment block registering Phase 405's three new SliceFrontmatter fields (autonomy, allowed_subagents, subagent nested config) with forward-pointers to owning specs."
      min_lines: 230
  key_links:
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      via: "Forward-pointer for deviation_logged / deviation_classification_rejected / deviation_resolution_recorded / deviation_cap_exceeded event schemas"
      pattern: "DEVIATION-RULES\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      via: "Forward-pointer for subagent_whitelist_violation + subagent_cap_expansion_rejected event schemas"
      pattern: "SUBAGENT-MANAGEMENT\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      via: "Forward-pointer for the eight subagent runtime events (started/progress/complete/spot_check_failed/crash_detected/restart/restart_exhausted/orphan_detected)"
      pattern: "SUBAGENT-MONITORING\\.md"
    - from: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      to: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      via: "Forward-pointer for state_build/deviation/arch_patterns.py + state_build/commit/trailers.py + stepNSUMMARY ## Deviations projector ownership"
      pattern: "DEVIATION-RULES\\.md"
    - from: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md"
      via: "Forward-pointer for state_build/subagents/{types,returns,spot_check,restart,orphan_reconcile,autonomy}.py + CompactionSnapshot extension owner"
      pattern: "SUBAGENT-MONITORING\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md"
      to: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      via: "Forward-pointer for `autonomy` Slice frontmatter field owner (DEV-06)"
      pattern: "DEVIATION-RULES\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md"
      to: ".planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md"
      via: "Forward-pointer for `allowed_subagents` + `subagent` Slice frontmatter fields owner (SUB-03 + SUB-04)"
      pattern: "SUBAGENT-MANAGEMENT\\.md"
---

<objective>
Append three v41 amendment blocks to v40 master spec documents, registering the artifacts and events introduced by Phase 405's three sibling specs (DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md):

1. **EVENT-TAXONOMY.md** — `## v41 Amendment — Phase 405 Deviation + Subagent Event Family` block registering the 14 new event types (4 deviation, 2 subagent-control, 8 subagent-runtime).
2. **ARTIFACT-CATALOG.md** — `## v41 Amendment — Phase 405 Deviation + Subagent Artifacts` block registering the four new modules, the `## Deviations` SUMMARY section, and the CompactionSnapshot extension.
3. **FRONTMATTER-SCHEMAS.md** — `## v41 Amendment — Phase 405 SliceFrontmatter Extensions` block registering the three new Slice frontmatter fields (`autonomy`, `allowed_subagents`, `subagent` nested config).

Why these amendments exist: v40's master spec docs are the canonical registries. The Phase 402 + Phase 403 + Phase 404 precedent (append-only `## v41 Amendment` blocks) is the canonical pattern. Each amendment block is a registry index pointing to the owning Phase 405 spec; full Pydantic schemas + behaviors live in the owning Phase 405 spec docs.

Purpose: DEV-07 (deviation event family) + SUB-05/SUB-06/SUB-07/SUB-08/SUB-09 (subagent event family + monitoring events) each contribute event types, modules, and frontmatter fields that need master-registry registration. The amendments are registry indexes; full Pydantic schemas + behaviors live in the owning Phase 405 spec docs (Plans 01-03; forward-pointers in the amendment tables).

Output: Three amended files. Each file's original content + prior v41 amendments are preserved (append-only); the new amendment blocks are appended at the bottom.
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
@.planning/milestones/v41/phases/405/405-CONTEXT.md
@.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md
@.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md
@.planning/milestones/v41/phases/404/04-event-amendments-PLAN.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
@.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
</context>

<interfaces>
<!-- The existing v41 amendment blocks in EVENT-TAXONOMY.md (Phase 402 + 403 + 404), ARTIFACT-CATALOG.md (Phase 402 + 404), and FRONTMATTER-SCHEMAS.md (any prior v41 amendments) define the pattern this plan replicates. -->

The Phase 404 Plan 04 pattern is the closest precedent for both EVENT-TAXONOMY.md and ARTIFACT-CATALOG.md amendments:
- Read `.planning/milestones/v41/phases/404/04-event-amendments-PLAN.md` lines 60-100 for the amendment block shape (heading format, column-shape, forward-pointer convention).

The new event-row column shape (rendered as a markdown table) is:
| Event Type | Trigger | State Transition | Owning REQ |
| `state.step.deviation_logged` | `log_deviation` MCP call after cross-validation succeeds | task → deviation chain attempt N | DEV-07 → DEVIATION-RULES.md §9 |

The new artifact-row column shape is:
| Filename / Module Path | Producer Stage | Schema Owner | Immutability | Description |
| `state_build/deviation/arch_patterns.py` | v14 Build Kernel | DEVIATION-RULES.md §5 | append-extensible | ARCH_PATTERN_ALLOWLIST: list[re.Pattern] (6 entries) — Rule-4 detection regex list; single-source-of-truth for arch-pattern matching. |
</interfaces>

<threat_model>
Phase 405 Plan 04 is design-only. The three amendment blocks introduce no production attack surface — they are markdown appendments to spec documents. Threats considered:

- **[high] Append-only invariant violation**: If this plan edits v40 original content or prior v41 amendment blocks, audit-trail determinism is broken. **Mitigation in spec:** all three amendments are STRICTLY append-only. Spec stipulates `diff --stat` against the previous head MUST show only ADDED lines below the existing trailing content. v14's spec-replay determinism depends on this invariant. Task action stipulates: read the existing file's last line; append below; never edit existing lines.

- **[high] Event-type naming-drift**: If a new event type doesn't match `^state\\.(step|slice)\\.[a-z_]+$`, replay parsers fail at load. **Mitigation in spec:** each row's Event Type cell is verified against the regex; CI grep target included in the success_criteria of this plan. Spec stipulates the literal regex check.

- **[high] STATE-* vs GSD-* naming-discipline drift in amendment text**: If the amendment uses GSD-* in commit-trailer examples or event-payload field cites, it perpetuates the past-phase drift documented in 405-CONTEXT.md `<deferred>` "Past-phase `GSD-*` trailer rename pass." **Mitigation in spec:** the amendment block MUST use STATE-* exclusively; CI grep `grep -nE '\\bGSD-' .planning/milestones/v40/phases/{400,401}/specs/EVENT-TAXONOMY.md ARTIFACT-CATALOG.md FRONTMATTER-SCHEMAS.md` MUST NOT include any lines from Phase 405 additions (existing pre-Phase-405 GSD-* references are not in scope for this plan — they're the deferred rename pass).

- **[med] Forward-pointer path drift**: If the amendment cites a wrong path (e.g., `phases/405/DEVIATION-RULES.md` instead of `phases/405/specs/DEVIATION-RULES.md`), readers cannot navigate. **Mitigation in spec:** all forward-pointers use the explicit `specs/` subdirectory pattern matching the Phase 405 Plans 01-03 output paths. Each grep target in the verify block confirms the path renders correctly.

- **[med] Mode-isolation drift via teach-mode event mention**: If any new event is mentioned in a way that suggests teach-mode might emit it, mode-isolation is violated. **Mitigation in spec:** the amendment block's preamble explicitly states "All 14 new events live in `BUILD_ONLY_EVENT_PREFIXES`." CI grep ensures no `state.teach.*` event names appear in the amendment text.

- **[low] Table column-shape divergence from prior amendments**: If column count or column names differ from Phase 404's amendment, audit tooling that parses the tables breaks. **Mitigation in spec:** verbatim column shape from Phase 404 Plan 04 spec; the verify block grep checks the column headers literal.

No production code lands. No secrets. No network calls.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Append `## v41 Amendment — Phase 405 Deviation + Subagent Event Family` block to v40 EVENT-TAXONOMY.md registering 14 new events with owning-spec forward-pointers</name>
  <files>
    .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
  </files>

  <read_first>
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — read the entire existing taxonomy including the Phase 402 + Phase 403 + Phase 404 amendment blocks at the bottom; the new block is appended below the last existing line)
    - .planning/milestones/v41/phases/404/04-event-amendments-PLAN.md lines 1-120 (Phase 404 Plan 04 amendment-block precedent — heading format, column shape, forward-pointer convention)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (Plan 01 output — verbatim source for the 4 deviation events + their triggers + state transitions)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md (Plan 02 output — verbatim source for subagent_whitelist_violation + subagent_cap_expansion_rejected)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md (Plan 03 output — verbatim source for the 8 subagent runtime events)
    - .planning/milestones/v41/REQUIREMENTS.md lines 89-117 (DEV-01..DEV-07 + SUB-01..SUB-09 verbatim)
  </read_first>

  <action>
    Append the following block at the bottom of `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`. Do NOT edit any existing content above the append point. Use the Edit tool with `old_string` = the last existing line of the file + `new_string` = the last existing line + the block below. (Or read the file, then use Write to rewrite the file with appended content — but Write requires reading first; the safer pattern is Edit with the last existing line as `old_string`.)

    Block to append (verbatim):

    ```markdown

    ---

    ## v41 Amendment — Phase 405 Deviation + Subagent Event Family

    **Phase:** 405 (Deviation Rules & Subagent Management)
    **Status:** Canonical (v41)
    **Append-only:** All entries below are NEW; nothing above this header has been edited.
    **Build-mode only:** All 14 new event types live in `BUILD_ONLY_EVENT_PREFIXES`. No `state.teach.*` analog exists; teach-mode harness owns its own event family (v47 territory).
    **Naming discipline:** All identifiers are `STATE-*` / `state-*`. The four commit trailers (`STATE-Task`, `STATE-DeviationRule`, `STATE-DeviationAttempt`, `STATE-Subagent-Invocation`) are documented in DEVIATION-RULES.md §5.

    Phase 405 introduces three sibling spec documents (DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md) which together specify the deviation framework + subagent management subsystem. The following 14 new event types are emitted by the deviation classifier, subagent dispatch handler, and subagent monitoring projector. Full Pydantic payload schemas live in the owning specs; this amendment is a registry index.

    ### 14 New Event Types

    | Event Type | Trigger | State Transition | Owning REQ → Spec |
    |---|---|---|---|
    | `state.step.deviation_logged` | `log_deviation` MCP call after harness cross-validation succeeds (or on cap-exceeded for audit completeness) | task → deviation chain attempt N | DEV-07 → DEVIATION-RULES.md §9 |
    | `state.step.deviation_classification_rejected` | Cross-validation step 1-4 rejects the agent's declared `rule_id` | (no state change; advisory event) | DEV-07 → DEVIATION-RULES.md §4 |
    | `state.step.deviation_resolution_recorded` | Append-only mutation event; updates `Deviation.resolution` from `pending` → terminal value | deviation row resolution → terminal | DEV-07 → DEVIATION-RULES.md §9 |
    | `state.step.deviation_cap_exceeded` | Cross-validation step 5 detects the 4th attempt on the same `(task_id, rule_id, issue_signature)` tuple | deviation chain → escalation (Rule 4 promotion or `checkpoint:decision`) | DEV-07 → DEVIATION-RULES.md §4 |
    | `state.step.subagent_started` | Daemon dispatch handler after opencode `task` tool spawn confirms session creation | parent task → subagent in-flight | SUB-05 → SUBAGENT-MONITORING.md §2 |
    | `state.step.subagent_progress` | Every TUI-visible event from child session (message_end, tool_use start/end) | (no state change; observability event) | SUB-05 → SUBAGENT-MONITORING.md §2 |
    | `state.step.subagent_complete` | Child session reaches `stop_reason ∈ {end_turn, tool_use, max_tokens, error, aborted}` | subagent in-flight → completed (success or crash; spot-check follows) | SUB-05 → SUBAGENT-MONITORING.md §2 |
    | `state.step.subagent_spot_check_failed` | Any layer 1-4 of the 4-layer pure-machine spot-check stack fails | feeds into restart counter chain (not PRF strike chain) | SUB-06 → SUBAGENT-MONITORING.md §4 |
    | `state.step.subagent_crash_detected` | Any of 5 crash sources (process_exit / stop_reason / spot_check / sse_silence / parent_task_error) fires | restart counter for `(parent_task_id, subagent_type)` increments | SUB-07 → SUBAGENT-MONITORING.md §5 |
    | `state.step.subagent_restart` | Daemon spawns retry with augmented `<prior_crash>` continuation context | new invocation_id; restart_number 1..3 | SUB-07 → SUBAGENT-MONITORING.md §5-6 |
    | `state.step.subagent_restart_exhausted` | Restart counter hits 4th occurrence on the same tuple | escalation → parent must call `log_deviation(rule_id=3|4)` | SUB-07 → SUBAGENT-MONITORING.md §5 |
    | `state.step.subagent_orphan_detected` | Daemon resume reconciliation cannot resolve an in-flight subagent | persistent orphan → Rule 4 human gate | SUB-08 → SUBAGENT-MONITORING.md §7 |
    | `state.step.subagent_whitelist_violation` | `dispatch_subagent` payload references a SubagentType not in the effective whitelist | dispatch rejected at runtime `tool.execute.before` | SUB-03 → SUBAGENT-MANAGEMENT.md §5 |
    | `state.slice.subagent_cap_expansion_rejected` | Slice frontmatter `subagent.parallel_cap` exceeds 20 at plan-validation stage | replan iteration triggered | SUB-04 → SUBAGENT-MANAGEMENT.md §6 |

    ### Naming-convention check

    Every event type above matches the regex `^state\.(step|slice)\.[a-z_]+$`. No naming-drift entries. Mode-isolation gate: all entries are `state.{step,slice}.*` (Build-only); no `state.teach.*` references in Phase 405.

    ### Authoritative-ordering note

    Pydantic class definitions in the owning Phase 405 spec docs are authoritative; this amendment is a registry index. When event-payload field-set details diverge between this index and the owning spec, the owning spec wins.

    ### Cross-reference to umbrella event (Phase 406)

    Phase 406's `state.harness.intervention` umbrella event (HRN-05) aggregates Rule-4 escalations from `deviation_logged`, `subagent_spot_check_failed`, `subagent_crash_detected`, and `subagent_orphan_detected`. The umbrella event is owned by Phase 406's HARNESS-ARCHITECTURE.md; this amendment forward-references the rollup.
    ```

    After appending, validate:
    - The Phase 402 / 403 / 404 amendment blocks above the new block are byte-identical to before.
    - The new block is appended (separator `---` line, then the heading, then content).
    - File line count is ≥ 360.
    - No `GSD-` literal appears in the new block.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/404/04-event-amendments-PLAN.md` lines 23-32 — Phase 404 amendment block shape (column count, column names, forward-pointer convention) — mirror this verbatim.
        - Known: Phase 404's amendment block already in EVENT-TAXONOMY.md (search for `## v41 Amendment — Phase 404` in the existing file) — locate the last line of the file before appending below it.
        - Grep pattern: `grep -nE "^## v41 Amendment" /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — locates existing amendment block headers.
        - Grep pattern: `tail -20 /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — locates the literal last line for the Edit tool's `old_string`.
        - Grep pattern: `wc -l /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — baseline line count; after this task, new line count = baseline + ~40-50.
      </code_to_reuse>
      <docs_to_consult>
        - Phase 404 Plan 04 PLAN.md and SUMMARY.md — precedent.
        - DEVIATION-RULES.md §4 + §9 — verbatim source for the 4 deviation events.
        - SUBAGENT-MANAGEMENT.md §5 + §6 — verbatim source for whitelist_violation + cap_expansion_rejected.
        - SUBAGENT-MONITORING.md §2 + §4 + §5 + §7 — verbatim source for the 8 subagent runtime events.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendment.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 360)}' \
        && grep -qE "^## v41 Amendment — Phase 405 Deviation \+ Subagent Event Family" "$F" \
        && grep -q "state.step.deviation_logged" "$F" \
        && grep -q "state.step.deviation_classification_rejected" "$F" \
        && grep -q "state.step.deviation_resolution_recorded" "$F" \
        && grep -q "state.step.deviation_cap_exceeded" "$F" \
        && grep -q "state.step.subagent_started" "$F" \
        && grep -q "state.step.subagent_progress" "$F" \
        && grep -q "state.step.subagent_complete" "$F" \
        && grep -q "state.step.subagent_spot_check_failed" "$F" \
        && grep -q "state.step.subagent_crash_detected" "$F" \
        && grep -q "state.step.subagent_restart" "$F" \
        && grep -q "state.step.subagent_restart_exhausted" "$F" \
        && grep -q "state.step.subagent_orphan_detected" "$F" \
        && grep -q "state.step.subagent_whitelist_violation" "$F" \
        && grep -q "state.slice.subagent_cap_expansion_rejected" "$F" \
        && grep -qE "^## v41 Amendment — Phase 402" "$F" \
        && grep -qE "^## v41 Amendment — Phase 403" "$F" \
        && grep -qE "^## v41 Amendment — Phase 404" "$F" \
        && ! awk '/## v41 Amendment — Phase 405/,0' "$F" | grep -qE '\bGSD-'
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] EVENT-TAXONOMY.md has the new amendment block appended below all prior v41 amendments.
    - [check: must_haves.truths[1]] All 14 event-type strings appear literally in the amendment block.
    - [check: must_haves.truths[2]] Markdown table renders with 4 columns (Event Type, Trigger, State Transition, Owning REQ).
    - [check: must_haves.truths[3]] Forward-pointers (DEVIATION-RULES.md / SUBAGENT-MANAGEMENT.md / SUBAGENT-MONITORING.md) appear in the Owning REQ column.
    - [check: must_haves.truths[4]] Phase 402 + 403 + 404 amendment blocks remain intact (still present in the file).
    - [check: must_haves.truths[5]] File line count is ≥ 360.
    - [check: must_haves.truths[6]] Naming-convention statement rendered.
    - [check: must_haves.truths[7]] BUILD_ONLY_EVENT_PREFIXES statement rendered.
    - [check: must_haves.truths[8]] STATE-* trailer cross-reference rendered; no `GSD-` literal in Phase 405's new block.
    - [check: must_haves.truths[16]] Authoritative-ordering note rendered.
  </acceptance_criteria>

  <done>
    EVENT-TAXONOMY.md has the Phase 405 amendment block appended (append-only); 14 new events documented with forward-pointers; existing Phase 402/403/404 amendments untouched; verify-block bash passes.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append `## v41 Amendment — Phase 405 Deviation + Subagent Artifacts` block to v40 ARTIFACT-CATALOG.md AND `## v41 Amendment — Phase 405 SliceFrontmatter Extensions` block to v40 FRONTMATTER-SCHEMAS.md</name>
  <files>
    .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
    .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
  </files>

  <read_first>
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (full file — locate Phase 402 + Phase 404 amendments at bottom; append new block below)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md (full file — locate any prior v41 amendment at bottom; append new block below)
    - .planning/milestones/v41/phases/404/04-event-amendments-PLAN.md (Phase 404 Plan 04 amendment-block precedent — ARTIFACT-CATALOG.md amendment shape, especially the row column count)
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (Plan 01 — module paths state_build/deviation/arch_patterns.py, state_build/commit/trailers.py, state_build/projectors/deviation_summary.py; ## Deviations SUMMARY section owner)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md (Plan 02 — module paths state_build/subagents/{types,dispatch,parallel_cap}.py + SliceFrontmatter.allowed_subagents + .subagent nested config fields)
    - .planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md (Plan 03 — module paths state_build/subagents/{returns,spot_check,restart,orphan_reconcile,autonomy,remediation_hints}.py + CompactionSnapshot extension + SliceFrontmatter.autonomy via DEV-06)
    - .planning/milestones/v41/REQUIREMENTS.md lines 89-117 (DEV + SUB requirements)
  </read_first>

  <action>
    Two sub-actions. **Both are STRICTLY append-only.**

    ### Sub-action A: Append to ARTIFACT-CATALOG.md

    Append the following block at the bottom of `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md`. Use Edit with `old_string` = last existing line, `new_string` = last existing line + the block.

    Block to append (verbatim):

    ```markdown

    ---

    ## v41 Amendment — Phase 405 Deviation + Subagent Artifacts

    **Phase:** 405 (Deviation Rules & Subagent Management)
    **Status:** Canonical (v41)
    **Append-only:** All entries below are NEW; nothing above this header has been edited.
    **Build-mode only:** All entries live under `state_build/` lineage. CI import-graph lint enforces no `state_teach/` imports.
    **Naming discipline:** All module paths are `state_build/*`; no `state_gsd/*` or `gsd_*` paths exist in Phase 405.

    Phase 405's three sibling spec docs (DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md) introduce nine new Python modules + one extension to Phase 402's `CompactionSnapshot` Pydantic + one new `stepNSUMMARY.md` section. Full Pydantic schemas + behaviors live in the owning Phase 405 spec docs; this amendment is a registry index.

    ### New Artifacts

    | Filename / Module Path | Producer Stage | Schema Owner (spec doc) | Immutability | Description |
    |---|---|---|---|---|
    | `state_build/deviation/arch_patterns.py` | v14 Build Kernel | DEVIATION-RULES.md §5 | append-extensible | `ARCH_PATTERN_ALLOWLIST: list[re.Pattern]` (6 starter entries) + `match_arch_pattern()` + `classify_diff_kind()` — Rule-4 detection single-source-of-truth. |
    | `state_build/deviation/log_deviation.py` | v14 Build Kernel | DEVIATION-RULES.md §3-§4 | append-extensible | `log_deviation` MCP tool handler + 5-step cross-validation chain. |
    | `state_build/commit/trailers.py` | v14 Build Kernel | DEVIATION-RULES.md §5 | append-extensible | STATE-* trailer constants (`STATE-Task`, `STATE-DeviationRule`, `STATE-DeviationAttempt`, `STATE-Subagent-Invocation`) + `infer_commit_type()` (gsd-2 COMMIT_TYPE_RULES adapter). |
    | `state_build/projectors/deviation_summary.py` | v14 Build Kernel | DEVIATION-RULES.md §10 | append-extensible | `## Deviations` SUMMARY section projector — subscribes to `deviation_logged` + `deviation_resolution_recorded`; aggregates by `(rule_id, issue_signature)`; writes 8-column markdown table to `stepNSUMMARY.md`. |
    | `state_build/subagents/types.py` | v14 Build Kernel | SUBAGENT-MANAGEMENT.md §3 | append-extensible | `SubagentType` Literal (14 named types) + `STAGE_ROSTER: dict[SliceStage, frozenset[SubagentType]]` (4 stage rosters). |
    | `state_build/subagents/dispatch.py` | v14 Build Kernel | SUBAGENT-MANAGEMENT.md §2 + §5-§6 | append-extensible | `dispatch_subagent` MCP tool handler + DispatchSubagent / SingleDispatch / ParallelDispatch / ChainDispatch Pydantic shapes + whitelist enforcement + parallel-cap accounting. |
    | `state_build/subagents/parallel_cap.py` | v14 Build Kernel | SUBAGENT-MANAGEMENT.md §6 | append-extensible | `MAX_PARALLEL_CAP_DEFAULT = 20` + `resolve_effective_cap()` + `acquire_slot()` / `release_slot()` — daemon-side FIFO semaphore. |
    | `state_build/subagents/returns.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §3 | append-extensible | `SUBAGENT_RETURN_REGISTRY: dict[SubagentType, type[SubagentReturnBase]]` + `ArtifactDeclaration` + `SubagentReturnBase` Pydantic shapes; per-stage subclasses in `returns_{stage}.py` modules. |
    | `state_build/subagents/spot_check.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §4 | append-extensible | `run_spot_check_stack()` — 4-layer pure-machine validation (process / pydantic / artifact / commit). |
    | `state_build/subagents/restart.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §6 | append-extensible | `build_restart_prompt()` — augmented `<prior_crash>` XML continuation context. |
    | `state_build/subagents/remediation_hints.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §6 | append-extensible | Default `remediation_hint` strings keyed by `crash_source`. |
    | `state_build/subagents/orphan_reconcile.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §7 | append-extensible | 6-step daemon-resume orphan reconciliation flow + `SubagentOrphanDetected` + `InFlightSubagent` Pydantic. |
    | `state_build/subagents/autonomy.py` | v14 Build Kernel | SUBAGENT-MONITORING.md §8 | append-extensible | `compute_effective_autonomy(parent_effective, override) -> AutonomyMode` — SUB-09 inheritance flow. |
    | `stepNSUMMARY.md` `## Deviations` section | v15 Build Core Commands (verify-slice) | DEVIATION-RULES.md §10 | projector-generated | 8-column markdown table; section omitted when zero deviations. |

    ### CompactionSnapshot Extension (Phase 402 Pydantic model)

    Phase 405 EXTENDS Phase 402's `CompactionSnapshot` Pydantic model with two new fields. The schema owner remains Phase 402's CONTEXT-PROTOCOL.md; the Phase 405 extension is documented in SUBAGENT-MONITORING.md §7:

    | Field | Type | Owning REQ → Spec |
    |---|---|---|
    | `subagent_restart_counters` | `dict[str, int]` (key = `"{parent_task_id}|{subagent_type}"`) | SUB-08 → SUBAGENT-MONITORING.md §7 |
    | `in_flight_subagents` | `list[InFlightSubagent]` | SUB-08 → SUBAGENT-MONITORING.md §7 |

    ### Authoritative-ordering note

    Pydantic class definitions in the owning Phase 405 spec docs are authoritative; this amendment is a registry index for module paths. When module-export details diverge between this catalog and the owning spec, the owning spec wins.
    ```

    ### Sub-action B: Append to FRONTMATTER-SCHEMAS.md

    Append the following block at the bottom of `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md`.

    Block to append (verbatim):

    ```markdown

    ---

    ## v41 Amendment — Phase 405 SliceFrontmatter Extensions

    **Phase:** 405 (Deviation Rules & Subagent Management)
    **Status:** Canonical (v41)
    **Append-only:** All entries below are NEW; nothing above this header has been edited.
    **Build-mode only:** All three new fields are Build-mode-only; teach-mode SliceFrontmatter (v47 territory) owns its own analogs.
    **Pydantic `extra="forbid"`** continues per v40+Phase 403 convention.

    Phase 405's three sibling spec docs introduce three new fields on the `SliceFrontmatter` Pydantic model. Full validation rules + behavioral semantics live in the owning Phase 405 spec docs; this amendment is a registry index.

    ### New SliceFrontmatter Fields

    | Field | Type | Default | Owning REQ → Spec |
    |---|---|---|---|
    | `autonomy` | `Literal["tiered","full-yolo","conservative"] \| None` | `None` (inherit from milestone default) | DEV-06 → DEVIATION-RULES.md §6 |
    | `allowed_subagents` | `list[SubagentType] \| None` | `None` (use `STAGE_ROSTER[current_stage]`) | SUB-03 → SUBAGENT-MANAGEMENT.md §5 |
    | `subagent` | `SubagentSliceConfig \| None` | `None` | SUB-04 + SUB-07 → SUBAGENT-MANAGEMENT.md §6 + SUBAGENT-MONITORING.md §5 |

    ### Nested `SubagentSliceConfig` shape

    ```python
    class SubagentSliceConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        parallel_cap: int | None = None                       # SUB-04 narrowing-only override (≤20)
        progress_timeout_s: int | None = None                 # SUB-07 default 180s
        remediation_hints: dict[str, str] | None = None       # SUB-07 keyed by crash_source
    ```

    ### Validation rules (cross-references)

    - **`autonomy`**: Slice override CAN move stricter OR looser (narrowing-only does NOT apply; autonomy is policy not capability). Precedence: `milestone default → Slice override → done`. See DEVIATION-RULES.md §6.
    - **`allowed_subagents`**: Narrowing-only (subset of `STAGE_ROSTER[current_stage]`). Two-gate validation: plan-validation stage (Phase 403 N-VALIDATION.md) + runtime `tool.execute.before`. See SUBAGENT-MANAGEMENT.md §5.
    - **`subagent.parallel_cap`**: Narrowing-only (≤20). Expansion attempts → `state.slice.subagent_cap_expansion_rejected` at plan-validation. See SUBAGENT-MANAGEMENT.md §6.

    ### Authoritative-ordering note

    Pydantic class definitions in the owning Phase 405 spec docs are authoritative; this amendment is a registry index for the SliceFrontmatter additions.
    ```

    After both appends, validate per file:
    - The prior content above the new block is byte-identical to before.
    - The new block is appended (separator `---`, heading, content).
    - Mode-isolation: no `state.teach.*` or `state_teach/` references in the new blocks.
    - No `GSD-` literal in either new block.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/404/04-event-amendments-PLAN.md` lines 30-42 — Phase 404 ARTIFACT-CATALOG amendment block shape (column shape: Filename, Producer Stage, Schema Owner, Immutability, Description) — mirror verbatim.
        - Known: `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md` Sections 5 + 10 — module-path single-source-of-truth statements verbatim.
        - Known: `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md` Sections 2-3 + 5-6 — module paths verbatim.
        - Known: `.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md` Sections 3-8 — module paths verbatim.
        - Grep pattern: `tail -20 /Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — locates literal last line for Edit's old_string.
        - Grep pattern: `tail -20 /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — locates literal last line.
        - Grep pattern: `wc -l /Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — baseline line counts.
      </code_to_reuse>
      <docs_to_consult>
        - Phase 404 Plan 04 PLAN.md + SUMMARY.md — precedent.
        - DEVIATION-RULES.md §5 (commit trailers + arch_patterns module) + §10 (## Deviations projector).
        - SUBAGENT-MANAGEMENT.md §2 (dispatch.py) + §3 (types.py) + §6 (parallel_cap.py).
        - SUBAGENT-MONITORING.md §3 (returns.py) + §4 (spot_check.py) + §6 (restart.py + remediation_hints.py) + §7 (orphan_reconcile.py + CompactionSnapshot ext) + §8 (autonomy.py).
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendments.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      A=/Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
      F=/Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
      test -f "$A" && test -f "$F" \
        && wc -l "$A" | awk '{exit ($1 < 870)}' \
        && wc -l "$F" | awk '{exit ($1 < 230)}' \
        && grep -qE "^## v41 Amendment — Phase 405 Deviation \+ Subagent Artifacts" "$A" \
        && grep -qE "^## v41 Amendment — Phase 405 SliceFrontmatter Extensions" "$F" \
        && grep -q "state_build/deviation/arch_patterns.py" "$A" \
        && grep -q "state_build/deviation/log_deviation.py" "$A" \
        && grep -q "state_build/commit/trailers.py" "$A" \
        && grep -q "state_build/projectors/deviation_summary.py" "$A" \
        && grep -q "state_build/subagents/types.py" "$A" \
        && grep -q "state_build/subagents/dispatch.py" "$A" \
        && grep -q "state_build/subagents/parallel_cap.py" "$A" \
        && grep -q "state_build/subagents/returns.py" "$A" \
        && grep -q "state_build/subagents/spot_check.py" "$A" \
        && grep -q "state_build/subagents/restart.py" "$A" \
        && grep -q "state_build/subagents/remediation_hints.py" "$A" \
        && grep -q "state_build/subagents/orphan_reconcile.py" "$A" \
        && grep -q "state_build/subagents/autonomy.py" "$A" \
        && grep -q "subagent_restart_counters" "$A" \
        && grep -q "in_flight_subagents" "$A" \
        && grep -q "CompactionSnapshot" "$A" \
        && grep -q "## Deviations" "$A" \
        && grep -q "autonomy" "$F" \
        && grep -q "allowed_subagents" "$F" \
        && grep -q "SubagentSliceConfig" "$F" \
        && grep -q "parallel_cap" "$F" \
        && grep -q "progress_timeout_s" "$F" \
        && grep -q "remediation_hints" "$F" \
        && ! awk '/## v41 Amendment — Phase 405/,0' "$A" | grep -qE '\bGSD-' \
        && ! awk '/## v41 Amendment — Phase 405/,0' "$F" | grep -qE '\bGSD-'
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[9]] ARTIFACT-CATALOG.md amendment block renders with all 13 module paths + CompactionSnapshot extension fields + ## Deviations section.
    - [check: must_haves.truths[10]] CompactionSnapshot extension table renders with subagent_restart_counters + in_flight_subagents fields and SUB-08 forward-pointer.
    - [check: must_haves.truths[11]] ARTIFACT-CATALOG.md v40 + prior amendments preserved (Phase 402 + Phase 404 amendments still present).
    - [check: must_haves.truths[12]] Row column shape (Filename, Producer Stage, Schema Owner, Immutability, Description) renders for all rows.
    - [check: must_haves.truths[13]] FRONTMATTER-SCHEMAS.md amendment block renders with three new SliceFrontmatter fields (autonomy, allowed_subagents, subagent) + SubagentSliceConfig nested shape.
    - [check: must_haves.truths[14]] FRONTMATTER-SCHEMAS.md v40 + prior amendments preserved.
    - [check: must_haves.truths[15]] Authoritative-ordering note rendered in both new blocks.
    - [check: must_haves.truths[16]] No `GSD-` literal in either new amendment block (CI grep result = 0).
  </acceptance_criteria>

  <done>
    ARTIFACT-CATALOG.md and FRONTMATTER-SCHEMAS.md have their Phase 405 amendment blocks appended (append-only); all 13 modules + CompactionSnapshot extension + ## Deviations section + 3 SliceFrontmatter fields documented with forward-pointers; existing v40 + prior v41 amendments untouched; verify-block bash passes.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

```bash
T=/Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
A=/Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
F=/Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md

# All three v41 Phase 405 amendment blocks present
grep -qE "^## v41 Amendment — Phase 405 Deviation \+ Subagent Event Family" "$T" || { echo "MISSING amendment in EVENT-TAXONOMY.md"; exit 1; }
grep -qE "^## v41 Amendment — Phase 405 Deviation \+ Subagent Artifacts" "$A" || { echo "MISSING amendment in ARTIFACT-CATALOG.md"; exit 1; }
grep -qE "^## v41 Amendment — Phase 405 SliceFrontmatter Extensions" "$F" || { echo "MISSING amendment in FRONTMATTER-SCHEMAS.md"; exit 1; }

# Line-count floors
wc -l "$T" | awk '{ if ($1 < 360) { print "EVENT-TAXONOMY line count fail: " $1; exit 1 } }'
wc -l "$A" | awk '{ if ($1 < 870) { print "ARTIFACT-CATALOG line count fail: " $1; exit 1 } }'
wc -l "$F" | awk '{ if ($1 < 230) { print "FRONTMATTER-SCHEMAS line count fail: " $1; exit 1 } }'

# Append-only invariant: prior amendments still present
grep -qE "^## v41 Amendment — Phase 402" "$T" || { echo "DESTROYED Phase 402 amendment in EVENT-TAXONOMY.md"; exit 1; }
grep -qE "^## v41 Amendment — Phase 403" "$T" || { echo "DESTROYED Phase 403 amendment in EVENT-TAXONOMY.md"; exit 1; }
grep -qE "^## v41 Amendment — Phase 404" "$T" || { echo "DESTROYED Phase 404 amendment in EVENT-TAXONOMY.md"; exit 1; }

# Naming-discipline: no GSD- inside Phase 405's new blocks
! awk '/## v41 Amendment — Phase 405/,0' "$T" | grep -qE '\bGSD-' || { echo "GSD_NAMING_VIOLATION in EVENT-TAXONOMY.md Phase 405 block"; exit 1; }
! awk '/## v41 Amendment — Phase 405/,0' "$A" | grep -qE '\bGSD-' || { echo "GSD_NAMING_VIOLATION in ARTIFACT-CATALOG.md Phase 405 block"; exit 1; }
! awk '/## v41 Amendment — Phase 405/,0' "$F" | grep -qE '\bGSD-' || { echo "GSD_NAMING_VIOLATION in FRONTMATTER-SCHEMAS.md Phase 405 block"; exit 1; }

# Event-naming regex check (every event in Phase 405 amendment matches the regex)
for ev in deviation_logged deviation_classification_rejected deviation_resolution_recorded deviation_cap_exceeded subagent_started subagent_progress subagent_complete subagent_spot_check_failed subagent_crash_detected subagent_restart subagent_restart_exhausted subagent_orphan_detected subagent_whitelist_violation subagent_cap_expansion_rejected; do
  awk '/## v41 Amendment — Phase 405/,0' "$T" | grep -qE "state\\.(step|slice)\\.${ev}" || { echo "MISSING_EVENT: ${ev}"; exit 1; }
done

echo "Phase 405 Plan 04 verification OK"
```
</verification>

<success_criteria>
- EVENT-TAXONOMY.md has Phase 405 amendment block with 14 new events + forward-pointers + ≥360 lines.
- ARTIFACT-CATALOG.md has Phase 405 amendment block with 13 modules + CompactionSnapshot extension + ## Deviations section + ≥870 lines.
- FRONTMATTER-SCHEMAS.md has Phase 405 amendment block with 3 new SliceFrontmatter fields + SubagentSliceConfig nested shape + ≥230 lines.
- All three append-only invariants hold (prior content + prior v41 amendments preserved byte-identically).
- No `GSD-` literal inside any Phase 405 amendment block.
- DEV-07 + SUB-05..SUB-09 all addressed (registered in master indexes).
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/405/04-event-amendments-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: line-count deltas for the three amended v40 files, list of 14 new events registered, list of 13 new modules registered, list of 3 new SliceFrontmatter fields registered, append-only invariant verification result, naming-discipline verification result (`grep '\bGSD-' inside Phase 405 blocks = 0`).
</output>
