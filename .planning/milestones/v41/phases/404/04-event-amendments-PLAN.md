---
phase: 404
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
autonomous: false
requirements:
  - PRF-06
  - APG-06
  - SRP-02
  - SRP-04
  - SRP-05
  - SRP-06

must_haves:
  truths:
    - "EVENT-TAXONOMY.md has a NEW `## v41 Amendment — Phase 404 Discipline-Guard Event Family` block appended at the bottom that registers the nine new event types introduced by Phase 404."
    - "The nine event types are exhaustively listed in the amendment table: state.step.gate_strike (PRF-06), state.step.gate_resolved (PRF-06), state.step.step_verify_completed (PRF-05), state.slice.slice_verify_completed (PRF-05), state.step.paralysis_event (APG-06), state.step.scope_check (SRP-02), state.step.scope_deviation (SRP-04), state.step.scope_deviation_request (SRP-04), state.step.scope_deviation_resolved (SRP-04), state.slice.split_recommendation (SRP-05)."
    - "Each event row has columns: Event Type, Trigger, State Transition, Owning REQ — mirroring the Phase 403 v41 amendment table shape."
    - "Forward-pointers from each event row to its canonical home spec (PROOF-GATE.md for gate_strike/gate_resolved/step_verify_completed/slice_verify_completed; ANALYSIS-PARALYSIS-GUARD.md for paralysis_event; SCOPE-PROHIBITION.md for scope_check/scope_deviation/scope_deviation_request/scope_deviation_resolved/split_recommendation) are rendered."
    - "EVENT-TAXONOMY.md v40 original content is UNCHANGED (append-only amendment; no in-line strikethroughs); the Phase 402 + Phase 403 amendment blocks are also untouched; the new amendment block is appended below them."
    - "v40 EVENT-TAXONOMY.md final line count is >= original baseline (was 281 after Phase 403 amendment; expected >= 320 after this amendment with ~40+ added lines)."
    - "Naming convention verification: every new event type matches `^state\\.(step|slice)\\.[a-z_]+$` regex — no naming-drift events."
    - "Mode-isolation note is rendered: all 10 new events live in `BUILD_ONLY_EVENT_PREFIXES` (Build-only)."
    - "ARTIFACT-CATALOG.md has a NEW `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` block appended at the bottom (below the existing Phase 402 amendment) registering: `stepN-VERIFY.json` (per-Step machine-readable Pydantic StepVerifyResult schema v1; owned by PROOF-GATE.md); `slice-verification.sh` (per-Slice executable bash script; owned by PROOF-GATE.md); `deferred-items.md` (per-Slice out-of-scope log markdown table; owned by SCOPE-PROHIBITION.md). The N-VERIFICATION.md entry is REAFFIRMED with a forward-pointer to PROOF-GATE.md Section 8 for its column schema (which is owned by PROOF-GATE.md not by ARTIFACT-CATALOG.md)."
    - "ARTIFACT-CATALOG.md v40 original content + Phase 402 amendment are UNCHANGED (append-only)."
    - "Each new artifact row has columns: Filename, Producer Stage, Schema Owner (spec doc), Immutability, Description — mirroring the v40 ARTIFACT-CATALOG.md row shape."
    - "Authoritative-ordering note is restated: Pydantic class definitions in the owning specs (PROOF-GATE.md / ANALYSIS-PARALYSIS-GUARD.md / SCOPE-PROHIBITION.md) are authoritative; this taxonomy / catalog amendment is a registry index — full schemas live elsewhere."
  artifacts:
    - path: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      provides: "v40 EVENT-TAXONOMY.md with a third v41 amendment block registering Phase 404's 10 new state.{step,slice}.* events with forward-pointers to PROOF-GATE.md / ANALYSIS-PARALYSIS-GUARD.md / SCOPE-PROHIBITION.md owning specs."
      min_lines: 320
    - path: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      provides: "v40 ARTIFACT-CATALOG.md with a second v41 amendment block registering stepN-VERIFY.json (per-Step JSON), slice-verification.sh (per-Slice executable), deferred-items.md (per-Slice out-of-scope log), and reaffirming N-VERIFICATION.md column-schema ownership by PROOF-GATE.md."
      min_lines: 830
  key_links:
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "Forward-pointer for gate_strike / gate_resolved / step_verify_completed / slice_verify_completed event schemas"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md"
      via: "Forward-pointer for paralysis_event schema"
      pattern: "ANALYSIS-PARALYSIS-GUARD\\.md"
    - from: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      to: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      via: "Forward-pointer for scope_check / scope_deviation / scope_deviation_request / scope_deviation_resolved / split_recommendation event schemas"
      pattern: "SCOPE-PROHIBITION\\.md"
    - from: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "Forward-pointer for stepN-VERIFY.json schema owner (Pydantic StepVerifyResult v1) and N-VERIFICATION.md column-schema ownership"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md"
      to: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      via: "Forward-pointer for deferred-items.md producer + auto-append projector spec"
      pattern: "SCOPE-PROHIBITION\\.md"
---

<objective>
Append a `## v41 Amendment — Phase 404 Discipline-Guard Event Family` block to `EVENT-TAXONOMY.md` (v40), registering the ten new event types introduced by Phase 404's three sibling specs (PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, SCOPE-PROHIBITION.md). Append a parallel `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` block to `ARTIFACT-CATALOG.md` (v40), registering three new per-Slice/per-Step artifacts (`stepN-VERIFY.json`, `slice-verification.sh`, `deferred-items.md`) and reaffirming `N-VERIFICATION.md` column-schema ownership.

Why this amendment exists: Phase 404's three spec docs (Plans 01-03) introduce a substantial new event family (10 events) and three new on-disk artifacts. v40's EVENT-TAXONOMY.md is the master taxonomy; v40's ARTIFACT-CATALOG.md is the master artifact registry. Both MUST be kept current — the Phase 402 + Phase 403 precedent (append-only `## v41 Amendment` blocks) is the canonical pattern.

Purpose: PRF-06 / APG-06 / SRP-02 / SRP-04 / SRP-05 / SRP-06 each contribute event types or artifacts that need master-taxonomy registration. The amendment is the registry index; full Pydantic schemas + behaviors live in the owning Phase 404 spec docs (forward-pointers in the amendment tables).

Output: Two amended files. Each file's original content + prior v41 amendments are preserved (append-only); the new amendment blocks are appended at the bottom of each file.
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
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
@.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
@.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md
@.planning/milestones/v41/phases/402/03-v40-amendments-PLAN.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
</context>

<interfaces>
<!-- The two existing v41 amendment blocks in EVENT-TAXONOMY.md and the existing v41 amendment block in ARTIFACT-CATALOG.md. These define the pattern this plan replicates. -->

Excerpt A — EVENT-TAXONOMY.md existing Phase 403 amendment shape (lines 239-281), verbatim header + table format this plan mirrors:
```
## v41 Amendment — Step-Tier Event Family Extension

> **Source phase:** v41 Phase 403 (Step/Task Decomposition & Plan-as-Prompt)
> **Amendment date:** 2026-05-11
> **Amendment type:** Additive — new event types added to the step tier; v40 baseline events unchanged.
> **Forward-pointer:** Full Pydantic schemas + replay rules in `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md`.

### v40 baseline scope
...

### v41 extension scope (9 new state.step.* events)

| Event Type | Trigger | State Transition | Owning REQ |
|-----------|---------|------------------|------------|
| `state.step.plan_authored` | ... | ... | PAP-06 |
| ...

All v41 additions follow v40 conventions:
- Naming: `state.{tier}.{action}` form preserved.
- Envelope: ride `EventEnvelope` outer shape.
- ...

### v14 implementation pointer
...

*Original v40 spec text and Phase 402 amendment above this block are untouched. This amendment is purely additive, appended per Phase 402 convention (no in-line strikethroughs).*
```

Excerpt B — ARTIFACT-CATALOG.md existing Phase 402 amendment shape (lines 796-806), verbatim format this plan mirrors:
```
## v41 Amendment

**Amended:** Phase 402 (v41 milestone — Slice-Cycle & Context Window Spec)
**Cause:** SLC-06 / SLC-07 — canonical Slice folder layout + cycle ownership.
**Canonical successor:** [`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md) §"Canonical Slice Folder Layout (SLC-06 amended)"

### Effect on this document

Artifact catalog (ART-01) entries for the Slice tier remain authoritative for filename, schema owner, and immutability. SLICE-CYCLE.md adds the producer-stage mapping ...

*Original v40 spec text above this amendment block is untouched.*
```

Excerpt C — The full event taxonomy of Phase 404 events (consolidated from Plans 01-03; this is the source-of-truth list this plan registers):

| Event Type | Owner (Plan) | Owning REQ | Aggregate tier |
|-----------|--------------|------------|----------------|
| state.step.gate_strike | Plan 01 (PROOF-GATE.md) | PRF-06 | step |
| state.step.gate_resolved | Plan 01 (PROOF-GATE.md) | PRF-06 | step |
| state.step.step_verify_completed | Plan 01 (PROOF-GATE.md) | PRF-05 | step |
| state.slice.slice_verify_completed | Plan 01 (PROOF-GATE.md) | PRF-05 | slice |
| state.step.paralysis_event | Plan 02 (ANALYSIS-PARALYSIS-GUARD.md) | APG-06 | step |
| state.step.scope_check | Plan 03 (SCOPE-PROHIBITION.md) | SRP-02 | step |
| state.step.scope_deviation | Plan 03 (SCOPE-PROHIBITION.md) | SRP-04 | step |
| state.step.scope_deviation_request | Plan 03 (SCOPE-PROHIBITION.md) | SRP-04 | step |
| state.step.scope_deviation_resolved | Plan 03 (SCOPE-PROHIBITION.md) | SRP-04 | step |
| state.slice.split_recommendation | Plan 03 (SCOPE-PROHIBITION.md) | SRP-05 | slice |
</interfaces>

<threat_model>
Phase 404 is design-only. This plan amends two existing v40 spec docs in append-only fashion; no production attack surface. Threats considered:

- **[high] Amendment overwriting v40 EVENT-TAXONOMY.md or ARTIFACT-CATALOG.md original content**: If the amendment writer accidentally edits non-amendment regions, v40 history is corrupted. **Mitigation:** the executor uses Edit with a unique header anchor `## v41 Amendment — Phase 404 Discipline-Guard Event Family` (which does NOT exist in v40 EVENT-TAXONOMY.md prior to this plan) and `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` (unique in ARTIFACT-CATALOG.md). Verification grep checks line counts are >= baseline (281 for EVENT-TAXONOMY.md after Phase 403; 806 for ARTIFACT-CATALOG.md after Phase 402) AND that the two prior v41 amendment headers (Phase 402 + Phase 403 for EVENT-TAXONOMY.md; Phase 402 for ARTIFACT-CATALOG.md) are still present unchanged.

- **[med] Event taxonomy naming convention drift**: If new events use different naming form than v40's `state.{tier}.{action}`, the projector / replay machinery breaks. **Mitigation:** spec stipulates every new event in this amendment follows `state.{step|slice}.{snake_case_action}` form; verification regex `^state\\.(step|slice)\\.[a-z_]+$` confirms no event name violates the convention. Owning REQ-IDs are cited; full schemas live in the owning Phase 404 specs.

- **[med] Forward-pointer drift / broken links**: If the Phase 404 spec files renamed or moved post-publication, the amendment's forward-pointers become broken. **Mitigation:** the forward-pointer paths are relative to repo root (`.planning/milestones/v41/phases/404/specs/PROOF-GATE.md`); v14+ teams operating on the codebase will surface broken refs at planner-validation stage; this is acceptable maintenance risk (the alternative — inlining schemas — would duplicate content and create the harder problem of schema drift between owning spec and the registry).

- **[low] Mode-isolation drift**: All Phase 404 events live in `BUILD_ONLY_EVENT_PREFIXES`. **Mitigation:** amendment explicitly states this; mirrors Phase 402 + Phase 403 amendment mode-isolation pattern.

- **[low] Truncation marker / authoring artifacts**: Markdown-only amendment; no Pydantic / code. **Mitigation:** N/A.

No production code lands. No secrets. No network calls. No untrusted input.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Append `## v41 Amendment — Phase 404 Discipline-Guard Event Family` block to EVENT-TAXONOMY.md</name>
  <files>
    .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
  </files>

  <read_first>
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — confirm current state; baseline 281 lines after Phase 403 amendment)
    - .planning/milestones/v41/phases/403/specs/STEP-EVENTS.md (full file — Phase 403 sibling-doc reference; mirror its amendment-block shape)
    - .planning/milestones/v41/phases/402/03-v40-amendments-PLAN.md (full file — Phase 402's amendments plan; this Plan 04 mirrors its append-only pattern)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file — Plan 01 output; quote event Pydantic class names + triggers for the table rows)
    - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md (full file — Plan 02 output; quote ParalysisEvent trigger for the table row)
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (full file — Plan 03 output; quote ScopeCheck/ScopeDeviation/ScopeDeviationRequest/ScopeDeviationResolved/SplitRecommendation triggers for the table rows)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (search "<canonical_refs>" — confirms the full event list expected by this phase)
    - .planning/milestones/v41/REQUIREMENTS.md lines 58-87 (PRF + APG + SRP requirements that this amendment cross-references via Owning REQ column)
  </read_first>

  <action>
    Use Edit to append a new amendment block at the end of `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`. **Mirror the Phase 403 amendment shape verbatim** (file structure lines 239-281 are the template — see `<interfaces>` Excerpt A).

    Before appending, run `wc -l` on the target to confirm baseline (expected: ~281 lines). The amendment adds ~50 lines (header + intro + table + conventions + v14 pointer + closing note); final line count expected ~330.

    **Exact content to append (verbatim — replace placeholders with actual data; do NOT paraphrase):**

    ```markdown

    ---

    ## v41 Amendment — Phase 404 Discipline-Guard Event Family

    > **Source phase:** v41 Phase 404 (Boolean Proof Gate & Discipline Guards)
    > **Amendment date:** {today's date — ISO-8601, e.g., 2026-05-11}
    > **Amendment type:** Additive — new event types added to the step + slice tiers; v40 baseline events + Phase 402 amendment + Phase 403 amendment unchanged.
    > **Forward-pointers:**
    >   - Gate events: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md`
    >   - Paralysis event: `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md`
    >   - Scope + split events: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md`

    ### v40 + Phase 402 + Phase 403 baseline scope

    The original v40 EVENT-TAXONOMY.md catalogued 33 events across Arc / Stage / Slice / Step tiers and 2 composite events. The Phase 402 amendment added four Slice stage-boundary events (`state.slice.{design,research,run,verify}_completed`) and two compaction-lifecycle events (`compaction.snapshot_taken`, `compaction.reinject_completed`). The Phase 403 amendment added nine `state.step.*` events for plan-authoring, plan-mutation, autonomy-tiered checkpoint resolution, and replan diff-replay continuity. Phase 404 extends the taxonomy with TEN new events for the boolean proof gate, the analysis-paralysis guard, and the scope-reduction-prohibition discipline guards. None of these v41 additions change v40 baseline event semantics or names.

    ### v41 extension scope (10 new state.{step,slice}.* events)

    | Event Type | Trigger | State Transition | Owning REQ | Owning Spec |
    |-----------|---------|------------------|------------|-------------|
    | `state.step.gate_strike` | Pure-machine evaluator returns `fail` at the completion-claim boundary (Write/Edit to next-task file OR `complete_task` MCP call); strike counter increments for the (task_id, check_id) tuple | (none — append-only audit record; the strike-counter in-memory state transitions on emission) | PRF-06 | PROOF-GATE.md §6 |
    | `state.step.gate_resolved` | (task_id, check_id) chain closes — verdict transitions to pass/flag/omitted, OR human resolution at strike 6 | (none — append-only audit record; closes the strike-chain in the in-memory counter) | PRF-06 | PROOF-GATE.md §7 |
    | `state.step.step_verify_completed` | Step-end after `stepN-VERIFY.json` is written; carries the path + server-side recomputed overall_verdict | step: `verifying` → `verified` (or `verify_failed` on fail verdict) | PRF-05 | PROOF-GATE.md §7 |
    | `state.slice.slice_verify_completed` | Slice-end after `slice-verification.sh` exits 0 AND `N-VERIFICATION.md` is written by the deterministic projector | slice: `verifying` → `verified` | PRF-05 | PROOF-GATE.md §7 |
    | `state.step.paralysis_event` | Per-task consecutive-read-only counter crosses threshold; emits at advisory 1, 2, 3+reinject, 4, 5, 6+human-gate | (none — append-only audit record; the paralysis-counter in-memory state transitions on emission) | APG-06 | ANALYSIS-PARALYSIS-GUARD.md §8 |
    | `state.step.scope_check` | Prohibited-language scan match on a Write/Edit content; emitted whether or not EXCEPTION_RE resolves | (none — write decision flows from exception_matched + exception_resolved tuple) | SRP-02 | SCOPE-PROHIBITION.md §5 |
    | `state.step.scope_deviation` | tool.execute.before Layer 1 rejects a Write/Edit whose target path is not in `files_modified` | (none — append-only audit record; the write was rejected) | SRP-04 | SCOPE-PROHIBITION.md §6 |
    | `state.step.scope_deviation_request` | Agent calls `scope_deviation_request` MCP tool requesting a one-shot allowlist entry | (none — append-only audit record; surfaces a `checkpoint:decision`) | SRP-04 | SCOPE-PROHIBITION.md §7 |
    | `state.step.scope_deviation_resolved` | Human (or harness_auto under `--full-yolo` per Phase 405 DEV-05) resolves the `checkpoint:decision`; carries resolution: approve \| reject | one-shot allowlist entry written on approve; nothing on reject | SRP-04 | SCOPE-PROHIBITION.md §7 |
    | `state.slice.split_recommendation` | Agent calls `request_step_split` MCP tool; harness records the recommendation + takes worktree snapshot + transitions Slice to `pending_replan` | slice: `running` → `pending_replan` (run-slice terminal state) | SRP-05 | SCOPE-PROHIBITION.md §8 |

    ### Conventions inherited

    All v41 Phase 404 additions follow v40 conventions:
    - **Naming**: `state.{tier}.{action}` form preserved; tier ∈ {step, slice}; action is snake_case.
    - **Envelope**: ride `EventEnvelope` outer shape (per v40 baseline + Phase 402 amendment confirmation).
    - **Validation**: `model_config = ConfigDict(extra="forbid")` on every payload (full Pydantic schemas in the owning specs).
    - **Append-only**: event store rows never UPDATED/DELETED; corrections are NEW events (e.g., `state.step.gate_resolved` to close a strike chain; `state.step.scope_deviation_resolved` to close a deviation request).
    - **Mode prefix**: all 10 new events live in `BUILD_ONLY_EVENT_PREFIXES`; teach-mode harness is v47 scope.
    - **Bounded truncation**: `agent_response_summary` / `eval_evidence` / similar excerpt fields are <= 2KB each; 10KB total per event (mirrors PROOF-GATE.md Section 7 §Bounded truncation discipline).

    ### Counter independence (load-bearing)

    Phase 404 introduces TWO independent counters (per `loop-control.md §0 Correction 1` — distinct counters at distinct scopes; conflation forbidden):

    - **`gate_strike` chain (PRF)**: per `(task_id, check_id)` tuple. 3 advisory → clear+reinject (single shot) → 3 more → human gate at strike 6. Per failing must_haves check.
    - **`paralysis_event` chain (APG)**: per task. 3 advisory → clear+reinject (single shot) → 3 more → human gate at advisory 6. Per consecutive-read-only-tool-uses window.

    Each can independently reach force-stop. The Phase 406 `harness_intervention` event (HRN-05) is the umbrella that aggregates both; this amendment confirms the umbrella's expected member set.

    ### Event count summary

    Event count rises from 39 (after Phase 403 amendment) to **49** after Phase 404 amendment: +4 gate events (gate_strike, gate_resolved, step_verify_completed, slice_verify_completed) + 1 paralysis event + 5 scope events (scope_check, scope_deviation, scope_deviation_request, scope_deviation_resolved, split_recommendation). Mode-isolation rules unchanged — all new events Build-only.

    ### v14 implementation pointer

    v14 Build Kernel implements:
    - Pydantic payload models per the owning Phase 404 specs (PROOF-GATE.md / ANALYSIS-PARALYSIS-GUARD.md / SCOPE-PROHIBITION.md).
    - Daemon emitters at the documented trigger sites (one row per harness action).
    - Projector reducers for in-memory counter state (PRF strike chain, APG paralysis chain, scope_deviation one-shot allowlist).
    - Bounded-truncation utility shared across PROOF-GATE.md / ANALYSIS-PARALYSIS-GUARD.md / SCOPE-PROHIBITION.md events (2KB per excerpt, 10KB total per event, literal marker `[... truncated <N> bytes ...]`).
    - Deterministic projectors for `N-VERIFICATION.md` (PROOF-GATE.md) and `deferred-items.md` (SCOPE-PROHIBITION.md) — both replayable from event store at any time.

    See `.planning/milestones/v41/phases/404/specs/{PROOF-GATE,ANALYSIS-PARALYSIS-GUARD,SCOPE-PROHIBITION}.md` for full schemas, behaviors, and cross-references.

    *Original v40 spec text, Phase 402 amendment, and Phase 403 amendment above this block are untouched. This amendment is purely additive, appended per Phase 402 convention (no in-line strikethroughs).*
    ```

    **Implementation guidance:**
    1. Read the file's last 5 lines first to find the EXACT trailing whitespace / newline of the Phase 403 amendment.
    2. Use Edit with `old_string` = the last paragraph of the Phase 403 amendment (the `*Original v40 spec text and Phase 402 amendment...*` italic line + any trailing blank lines), and `new_string` = the same line + the full Phase 404 amendment block above.
    3. After Edit, verify with `wc -l` (should be ~330 ± 10 lines) and `grep` for the new H2 heading.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` lines 199-281 (Phase 402 + Phase 403 amendment blocks) — mirror the heading shape (`## v41 Amendment — <descriptor>`) + the metadata bullets (Source phase, Amendment date, Amendment type, Forward-pointer) + the v40-baseline-scope intro + the table + the conventions + the v14-implementation-pointer + the closing italic note.
        - Known: `.planning/milestones/v41/phases/403/04-step-events-PLAN.md` Task 2 (v40 EVENT-TAXONOMY.md amendment append) — mirror the Edit-with-trailing-paragraph-anchor strategy.
        - Grep pattern: `tail -10 /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — confirms exact trailing content for the Edit anchor.
        - Grep pattern: `grep -n "^## v41 Amendment" /Users/tmac/Projects/state/.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — confirms exactly 2 prior amendment blocks exist (Phase 402 + Phase 403); after this task: exactly 3.
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<canonical_refs>` section §"Phase 400 + 401 prior decisions (v40)" — confirms the exact list of new events Phase 404 adds: `gate_strike`, `gate_resolved`, `paralysis_event`, `scope_check`, `scope_deviation_request`, `scope_deviation_resolved`, `split_recommendation`, `step_verify_completed`, `slice_verify_completed`. This amendment ALSO registers `scope_deviation` (the rejection event from Layer 1 — Plan 03 added; not in the original 404-CONTEXT list but consistent with Plan 03's spec).
        - PROOF-GATE.md §6 (StrikeCounter) + §7 (Pydantic event payloads) — verbatim source for the gate event triggers + state transitions table cells.
        - ANALYSIS-PARALYSIS-GUARD.md §7 (Six-Advisory Ladder) + §8 (ParalysisEvent payload) — verbatim source for paralysis_event row.
        - SCOPE-PROHIBITION.md §5 (ScopeCheck) + §6 (files_modified Layer 1) + §7 (scope_deviation_request) + §8 (request_step_split) — verbatim source for the 5 scope/split event rows.
        - loop-control.md §0 Correction 1 — informs the "Counter independence (load-bearing)" subsection.
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
        && wc -l "$F" | awk '{exit ($1 < 320)}' \
        && grep -c "^## v41 Amendment" "$F" | awk '{exit ($1 < 3)}' \
        && grep -q "v41 Amendment — Phase 404 Discipline-Guard Event Family" "$F" \
        && grep -q "state.step.gate_strike" "$F" \
        && grep -q "state.step.gate_resolved" "$F" \
        && grep -q "state.step.step_verify_completed" "$F" \
        && grep -q "state.slice.slice_verify_completed" "$F" \
        && grep -q "state.step.paralysis_event" "$F" \
        && grep -q "state.step.scope_check" "$F" \
        && grep -q "state.step.scope_deviation" "$F" \
        && grep -q "state.step.scope_deviation_request" "$F" \
        && grep -q "state.step.scope_deviation_resolved" "$F" \
        && grep -q "state.slice.split_recommendation" "$F" \
        && grep -q "PRF-06" "$F" \
        && grep -q "PRF-05" "$F" \
        && grep -q "APG-06" "$F" \
        && grep -q "SRP-02" "$F" \
        && grep -q "SRP-04" "$F" \
        && grep -q "SRP-05" "$F" \
        && grep -q "PROOF-GATE.md" "$F" \
        && grep -q "ANALYSIS-PARALYSIS-GUARD.md" "$F" \
        && grep -q "SCOPE-PROHIBITION.md" "$F" \
        && grep -q "BUILD_ONLY_EVENT_PREFIXES" "$F" \
        && grep -q "Counter independence" "$F" \
        && grep -q "harness_intervention" "$F" \
        && grep -q "v41 Amendment$" "$F" \
        && grep -q "v41 Amendment — Step-Tier Event Family Extension" "$F" \
        && ! grep -q "state.teach" "$F" \
        && python3 -c "import re, sys; content = open('$F').read(); events = re.findall(r'state\.(step|slice)\.[a-z_]+', content); illegal = [e for e in events if not re.match(r'^state\.(step|slice)\.[a-z_]+$', 'state.'+e)]; sys.exit(0 if not illegal else 1)"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[0]] EVENT-TAXONOMY.md final line count >= 320 (was ~281 after Phase 403 amendment; +40 expected).
    - [check: must_haves.truths[5]] v40 EVENT-TAXONOMY.md line count baseline pin: >= 320 lines confirms Phase 404 amendment landed atop the Phase 403 baseline of 281 lines (the +40-line expansion from Phase 404 satisfies truths[5]).
    - [check: must_haves.truths[0]] New H2 `## v41 Amendment — Phase 404 Discipline-Guard Event Family` heading present.
    - [check: must_haves.truths[1]] All 10 new event types present as table rows (grep returns >= 1 match each for state.step.gate_strike, state.step.gate_resolved, state.step.step_verify_completed, state.slice.slice_verify_completed, state.step.paralysis_event, state.step.scope_check, state.step.scope_deviation, state.step.scope_deviation_request, state.step.scope_deviation_resolved, state.slice.split_recommendation).
    - [check: must_haves.truths[2]] Each row has Event Type, Trigger, State Transition, Owning REQ columns (verified via table structure inspection).
    - [check: must_haves.truths[3]] All three Phase 404 spec doc forward-pointers present (PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, SCOPE-PROHIBITION.md).
    - [check: must_haves.truths[4]] Prior amendments untouched: Phase 402 amendment heading `## v41 Amendment` (just that, line 199) AND Phase 403 amendment heading `## v41 Amendment — Step-Tier Event Family Extension` (line 239) both still present (`grep -c "^## v41 Amendment" "$F"` returns >= 3).
    - [check: must_haves.truths[6]] Naming convention verified: python3 regex check `^state\.(step|slice)\.[a-z_]+$` passes for all event types in the file.
    - [check: must_haves.truths[7]] BUILD_ONLY_EVENT_PREFIXES mode-isolation note rendered.
    - [check: must_haves.key_links[0]] PROOF-GATE.md cited as forward-pointer in the amendment header.
    - [check: must_haves.key_links[1]] ANALYSIS-PARALYSIS-GUARD.md cited as forward-pointer.
    - [check: must_haves.key_links[2]] SCOPE-PROHIBITION.md cited as forward-pointer.
    - [check: verify_automated] All grep + line-count + python3-regex assertions in `<verify><automated>` pass.
    - [check: verify_automated] File contains no `state.teach.` references.
  </acceptance_criteria>

  <done>
    EVENT-TAXONOMY.md amended with Phase 404 discipline-guard event family registration: 10 new events tabulated with triggers, state transitions, owning REQ-IDs, and owning Phase 404 spec forward-pointers. Counter-independence (PRF vs APG) explicitly noted. v40 baseline + Phase 402 + Phase 403 amendments preserved verbatim (append-only).
  </done>
</task>

<task type="auto">
  <name>Task 2: Append `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` block to ARTIFACT-CATALOG.md</name>
  <files>
    .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
  </files>

  <read_first>
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (full file — confirm current state; baseline 806 lines after Phase 402 amendment; the Phase 402 amendment is at lines 796-806 — this Task 2 appends a SECOND v41 amendment block below it)
    - .planning/milestones/v41/phases/402/03-v40-amendments-PLAN.md (full file — Phase 402's amendments plan; this Plan 04 mirrors its append-only pattern)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file — Plan 01 output; quote Section 9 "Artifact Catalog Additions" subsection where this spec stipulates new artifacts)
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (full file — Plan 03 output; quote Section 9 "deferred-items.md Artifact" subsection)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (search "ARTIFACT-CATALOG.md" — confirms the spec is expected to register stepN-VERIFY.json and slice-verification.sh; N-VERIFICATION.md is already cataloged in v40)
  </read_first>

  <action>
    Use Edit to append a new amendment block at the end of `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md`. **Mirror the Phase 402 amendment shape** (see `<interfaces>` Excerpt B; lines 796-806).

    Before appending, run `wc -l` on the target to confirm baseline (expected: ~806 lines). The amendment adds ~30 lines (header + intro + table + conventions + closing note); final line count expected ~840.

    **Exact content to append (verbatim — replace placeholders):**

    ```markdown

    ---

    ## v41 Amendment — Phase 404 Verification + Discipline Artifacts

    **Amended:** Phase 404 (v41 milestone — Boolean Proof Gate & Discipline Guards)
    **Amendment date:** {today's date — ISO-8601, e.g., 2026-05-11}
    **Amendment type:** Additive — three new per-Step/per-Slice artifacts registered; v40 baseline + Phase 402 amendment unchanged.
    **Forward-pointers:**
      - `stepN-VERIFY.json` + `slice-verification.sh` + `N-VERIFICATION.md` column schema: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md`
      - `deferred-items.md`: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md`

    ### v40 baseline + Phase 402 amendment scope

    The v40 ARTIFACT-CATALOG.md catalogued the canonical Slice folder layout including `N-CONTEXT.md`, `N-DISCUSSION-LOG.md`, `N-RESEARCH.md`, `N-PATTERNS.md`, `N-VALIDATION.md`, `stepNPLAN.md`, `stepNSUMMARY.md`, `N-VERIFICATION.md`, and `RESUME.txt`. The Phase 402 amendment confirmed Slice-owns-cycle producer mapping. Phase 404 introduces three new artifacts (one per-Step JSON, one per-Slice executable script, one per-Slice markdown out-of-scope log) and pins `N-VERIFICATION.md`'s previously-implicit column schema to PROOF-GATE.md Section 8.

    ### v41 extension scope (3 new artifacts + 1 column-schema pin)

    | Filename | Producer Stage | Schema Owner | Immutability | Description |
    |---------|----------------|--------------|--------------|-------------|
    | `stepN-VERIFY.json` | execute-slice (Step-end gate) | PROOF-GATE.md §7 (StepVerifyResult schema_version Literal[1]) | Immutable post-write (append-only event store row; rewrites of stepN-VERIFY.json on replay are projector-driven from events) | Per-Step machine-readable verification artifact. Pydantic StepVerifyResult v1 (server-side recomputed `overall_passed`; nested `must_haves` + `acceptance_criteria` + `verify_automated` results with bounded-truncation 2KB per check, 10KB total). Authoritative per-Step evidence. |
    | `slice-verification.sh` | plan-slice (authored at planning end); immutable post-execute-slice start | PROOF-GATE.md §4 + §8 (bash script; pure-machine; 600s timeout default; Slice-frontmatter override `verify: {slice_timeout_s: int}`) | Immutable post-execute-slice start (locked per PAP-03 mutability matrix on the parent Slice) | Per-Slice executable bash script. Runs at verify-slice stage. Aggregates Step-level evidence (reads each `stepN-VERIFY.json`) + runs cross-Step integration checks. Pure-machine; exit 0 = pass (gates `N-VERIFICATION.md` projector emission); non-zero = fail. |
    | `deferred-items.md` | execute-slice (auto-appended by `state.step.scope_check` projector on `exception_matched=False` events) + verify-slice (Slice SUMMARY.md surface step) | SCOPE-PROHIBITION.md §9 (5-column table: ID, source_task, description, raised_at, status) | Mutable (humans + harness append rows; status updates allowed) | Per-Slice out-of-scope log. Auto-append rule: `scope_check` events with unresolved EXCEPTION_RE produce new rows. Status vocabulary: `open`, `scheduled-next-slice`, `scheduled-future-milestone`, `rejected`, `resolved-in-slice`. Surfaces in Slice SUMMARY.md `## Deferred Items` section. |
    | `N-VERIFICATION.md` (column-schema pin) | verify-slice (deterministic projector — re-renderable from event store at any time) | PROOF-GATE.md §8 (10-column truth-table schema: step_id, task_id, check_id, scope, source_expr, verdict, strike_count_at_close, gate_strike_event_ids, evidence_excerpt, timestamp) | Mutable (re-renderable; the underlying event-store source rows are append-only) | Existing v40 artifact; column schema previously implicit. Phase 404 PINS the schema to PROOF-GATE.md §8 (rolled-up wide audit-traceable view). Per-row `evidence_excerpt` <= 2KB; whole-file size unbounded (per-Step JSON files cap evidence). Ordering: Step DAG topology, then check_id index ascending within each Step. omitted rows ARE included (audit clarity). |

    ### Conventions inherited

    All v41 Phase 404 artifact additions follow v40 conventions:
    - **Filename form**: `stepN` prefix has no dash and no leading zeros (per Phase 402 carry-forward + v40 ARTIFACT-CATALOG.md confirmation).
    - **Per-Slice folder**: artifacts live in `slices/N-name/` per the canonical Slice folder layout (SLC-06).
    - **Schema-version migration**: `stepN-VERIFY.json` carries `schema_version: Literal[1]` per PROOF-GATE.md §7; bump literal to migrate; old files surface as parse errors.
    - **Build-mode only**: all three artifacts (and the column-schema pin) live under Build-mode subtree; teach-mode equivalents are v47 scope.
    - **Mutability classification**: stepN-VERIFY.json immutable post-write; slice-verification.sh immutable post-execute-slice start; deferred-items.md mutable (rows appended over Slice lifecycle); N-VERIFICATION.md mutable-but-re-renderable (projector idempotent from event store).

    ### Effect on this document

    Canonical Slice folder layout (ART-01 entries for `slices/N-name/`) gains three new files: `stepN-VERIFY.json` (one per Step), `slice-verification.sh` (one per Slice), and `deferred-items.md` (one per Slice; may be empty). Plus a column-schema pin for the existing `N-VERIFICATION.md`. Readers consulting this catalog for v41+ scheduling should cross-reference PROOF-GATE.md §8 (column schema) + §9 (artifact list) and SCOPE-PROHIBITION.md §9 (deferred-items.md). v14 Build Kernel implements the StepVerifyResult parser, the slice-verification.sh runner with timeout, the N-VERIFICATION.md projector, and the deferred-items.md auto-append projector.

    *Original v40 spec text + Phase 402 amendment above this block are untouched. This amendment is purely additive, appended per Phase 402 convention (no in-line strikethroughs).*
    ```

    **Implementation guidance:**
    1. Read the file's last 5 lines first to find the EXACT trailing content of the existing Phase 402 amendment (the `*Original v40 spec text above this amendment block is untouched.*` italic line).
    2. Use Edit with `old_string` = that italic line (plus its trailing newline), and `new_string` = the same line + the full Phase 404 amendment block.
    3. After Edit, verify with `wc -l` (should be ~840 ± 10 lines) and `grep -c "^## v41 Amendment"` (should be 2 — Phase 402 + Phase 404).

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` lines 796-806 (Phase 402 amendment block) — mirror the heading shape + metadata bullets + intro + content + closing italic note.
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` Section 9 (Artifact Catalog Additions) — quote the artifact list verbatim for this amendment's table rows.
        - Known: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` Section 9 (deferred-items.md Artifact) — quote the artifact spec verbatim.
        - Grep pattern: `tail -10 /Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — confirms exact trailing content for Edit anchor.
        - Grep pattern: `grep -n "^## v41 Amendment" /Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — confirms exactly 1 prior amendment block exists (Phase 402); after this task: exactly 2.
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<canonical_refs>` section §"Phase 400 + 401 prior decisions (v40)" — confirms the spec adds stepN-VERIFY.json + slice-verification.sh to the canonical Slice folder layout; N-VERIFICATION.md is already cataloged with column schema pinned here.
        - PROOF-GATE.md §9 "Artifact Catalog Additions" — verbatim source for the stepN-VERIFY.json + slice-verification.sh + N-VERIFICATION.md column-schema entries.
        - SCOPE-PROHIBITION.md §9 "deferred-items.md Artifact" — verbatim source for the deferred-items.md row.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown amendment.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 830)}' \
        && grep -c "^## v41 Amendment" "$F" | awk '{exit ($1 < 2)}' \
        && grep -q "v41 Amendment — Phase 404 Verification + Discipline Artifacts" "$F" \
        && grep -q "stepN-VERIFY.json" "$F" \
        && grep -q "slice-verification.sh" "$F" \
        && grep -q "deferred-items.md" "$F" \
        && grep -q "N-VERIFICATION.md" "$F" \
        && grep -q "PROOF-GATE.md" "$F" \
        && grep -q "SCOPE-PROHIBITION.md" "$F" \
        && grep -q "StepVerifyResult" "$F" \
        && grep -q "schema_version: Literal\[1\]" "$F" \
        && grep -q "600s" "$F" \
        && grep -q "10-column" "$F" \
        && grep -q "Build-mode only" "$F" \
        && ! grep -q "state.teach" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[1]] ARTIFACT-CATALOG.md final line count >= 830 (was 806 after Phase 402 amendment; +30 expected).
    - [check: must_haves.truths[8]] New H2 `## v41 Amendment — Phase 404 Verification + Discipline Artifacts` heading present.
    - [check: must_haves.truths[9]] Existing Phase 402 amendment heading `## v41 Amendment` (line 796 of original) UNCHANGED (grep returns the prior heading; `grep -c "^## v41 Amendment"` returns >= 2).
    - [check: must_haves.truths[10]] Three new artifacts present as table rows: `stepN-VERIFY.json`, `slice-verification.sh`, `deferred-items.md`. Plus the `N-VERIFICATION.md` column-schema pin entry.
    - [check: must_haves.truths[11]] All five table columns present (Filename, Producer Stage, Schema Owner, Immutability, Description).
    - [check: must_haves.truths[12]] Authoritative-ordering note rendered (full schemas live in owning specs; this catalog is a registry).
    - [check: must_haves.key_links[3]] PROOF-GATE.md cited as forward-pointer for stepN-VERIFY.json + slice-verification.sh + N-VERIFICATION.md column schema.
    - [check: must_haves.key_links[4]] SCOPE-PROHIBITION.md cited as forward-pointer for deferred-items.md.
    - [check: verify_automated] All grep + line-count assertions in `<verify><automated>` pass.
    - [check: verify_automated] File contains no `state.teach.` references.
  </acceptance_criteria>

  <done>
    ARTIFACT-CATALOG.md amended with Phase 404 verification + discipline artifacts registration: stepN-VERIFY.json (per-Step JSON), slice-verification.sh (per-Slice executable), deferred-items.md (per-Slice out-of-scope log), and N-VERIFICATION.md column-schema pin. v40 baseline + Phase 402 amendment preserved verbatim (append-only).
  </done>
</task>

<task type="auto">
  <name>Task 3: Write 04-event-amendments-SUMMARY.md</name>
  <files>
    .planning/milestones/v41/phases/404/04-event-amendments-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — Task 1 output; confirms the amendment landed)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (full file — Task 2 output; confirms the amendment landed)
    - .planning/milestones/v41/phases/403/04-step-events-SUMMARY.md (full file — sibling SUMMARY shape reference for an amendments plan)
    - .planning/milestones/v41/phases/402/03-v40-amendments-SUMMARY.md (if exists — Phase 402 amendments SUMMARY sibling for v40-amendment-plan-specific shape)
    - .planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md (Plan 01 sibling for Phase 404 consistency)
    - .planning/milestones/v41/phases/404/02-analysis-paralysis-guard-spec-SUMMARY.md (Plan 02 sibling)
    - .planning/milestones/v41/phases/404/03-scope-prohibition-spec-SUMMARY.md (Plan 03 sibling)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory gate
  </read_first>

  <action>
    Author the per-plan SUMMARY.md for the amendments plan. Mirror Phase 403 Plan 04 SUMMARY shape (sibling that ALSO did v40 amendments).

    1. Frontmatter (mirror sibling shape):
       - `phase: 404-boolean-proof-gate-discipline-guards`
       - `plan: 04`
       - `subsystem: design-spec-amendment`
       - `tags: [event-taxonomy, artifact-catalog, v40-amendment, append-only, phase-404-rollup]`
       - `requires`: 404-01 (PROOF-GATE.md — sources gate_strike/gate_resolved/step_verify_completed/slice_verify_completed events + stepN-VERIFY.json + slice-verification.sh + N-VERIFICATION.md column schema), 404-02 (ANALYSIS-PARALYSIS-GUARD.md — sources paralysis_event), 404-03 (SCOPE-PROHIBITION.md — sources scope_check/scope_deviation/scope_deviation_request/scope_deviation_resolved/split_recommendation events + deferred-items.md), 403 (Phase 403 EVENT-TAXONOMY.md amendment precedent), 402 (Phase 402 EVENT-TAXONOMY.md + ARTIFACT-CATALOG.md amendment precedent — both v40 files this plan amends)
       - `provides`: v40 EVENT-TAXONOMY.md third v41 amendment block (10 new events: 4 gate + 1 paralysis + 5 scope; >=320 lines final); v40 ARTIFACT-CATALOG.md second v41 amendment block (3 new artifacts + N-VERIFICATION.md column-schema pin; >=830 lines final); event taxonomy now contains 49 events (was 39 after Phase 403); canonical Slice folder layout enriched with per-Step + per-Slice verification + scope discipline artifacts
       - `affects`: v14 Build Kernel (master taxonomy registry now includes all Phase 404 events; v14 implementers consult both the amendment table AND the owning spec docs for full schemas), v15 Build Core Commands (canonical Slice folder layout now stipulates stepN-VERIFY.json + slice-verification.sh + deferred-items.md creation responsibilities), Phase 405 (DEV-04 architectural human-gate references the now-registered split_recommendation event), Phase 406 (HRN-05 harness_intervention umbrella event aggregates the 10 newly-registered Phase 404 events; the layered diagram has a complete event surface to draw from)
       - `tech-stack.patterns`: ["Append-only `## v41 Amendment — <descriptor>` block convention mirroring Phase 402 + Phase 403", "Naming-convention enforcement via python3 regex check `^state\\.(step|slice)\\.[a-z_]+$` over all event types in EVENT-TAXONOMY.md", "Master-taxonomy-as-registry-index pattern (full schemas live in owning specs; the taxonomy lists triggers + state transitions + owning REQ-IDs + forward-pointers)", "Canonical artifact catalog with 5-column row schema (Filename, Producer Stage, Schema Owner, Immutability, Description)", "Counter-independence note (PRF vs APG) restated in the amendment to mirror the cross-spec invariant"]
       - `key-files.created`: (none)
       - `key-files.modified`: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (>= 320 lines after amendment; was ~281); `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` (>= 830 lines after amendment; was ~806)
       - `key-decisions`: ["Append-only convention preserved verbatim (no in-line strikethroughs)", "10 events registered (4 gate + 1 paralysis + 5 scope) — scope_deviation event added beyond the original 9 from 404-CONTEXT.md to match Plan 03's spec", "Column schema for N-VERIFICATION.md PINNED to PROOF-GATE.md §8 (was implicit in v40)", "Counter-independence (PRF vs APG) restated in the EVENT-TAXONOMY amendment to prevent v14 implementers from conflating", "Forward-pointer pattern (registry refs owning spec, not inline schema duplication) — avoids schema drift"]
       - `requirements-completed`: (this plan does NOT fully complete any REQ — it transitively completes PRF-06 / APG-06 / SRP-02 / SRP-04 / SRP-05 / SRP-06 via taxonomy registration, but the substantive specs landed in Plans 01-03; this plan provides closure)
       - `requirements-touched`: PRF-06, APG-06, SRP-02, SRP-04, SRP-05, SRP-06
       - `duration`: ~12min (estimated; lightest plan in Phase 404 — pure amendment work)
       - `completed`: {date}

    2. Body sections (mirror sibling SUMMARY format):
       - `# Plan 404-04 Summary: v40 EVENT-TAXONOMY.md + ARTIFACT-CATALOG.md Amendments`
       - Bold tagline (1-2 sentences)
       - `## What Was Built` — 1 paragraph: two append-only amendment blocks; EVENT-TAXONOMY.md registers 10 new events (4 gate + 1 paralysis + 5 scope) with triggers, state transitions, owning REQ-IDs, and forward-pointers to Phase 404 spec docs; ARTIFACT-CATALOG.md registers 3 new artifacts (stepN-VERIFY.json, slice-verification.sh, deferred-items.md) plus a column-schema pin for the existing N-VERIFICATION.md; both v40 originals + prior v41 amendments preserved verbatim.
       - `## Key Decisions` — bullets
       - `## Files Touched` — EVENT-TAXONOMY.md (>= 320 lines), ARTIFACT-CATALOG.md (>= 830 lines)
       - `## Open Items / Deferred` — bullets:
         - "No new requirements completed substantively; this plan provides registry closure for PRF-06 / APG-06 / SRP-02 / SRP-04 / SRP-05 / SRP-06 which were substantively specified in Plans 01-03."
         - "Phase 406's harness_intervention (HRN-05) umbrella event will aggregate these 10 newly-registered events; the rollup happens in v41 Phase 406, NOT here."
         - "v14 Build Kernel implementation: event Pydantic payload classes already specified in Phase 404 spec docs; this amendment is registry-only (no new schemas)."
       - `## Downstream Hooks` — bullets:
         - "v14 Build Kernel consults the EVENT-TAXONOMY.md master registry for event-emission validation; consults ARTIFACT-CATALOG.md for the canonical Slice folder layout."
         - "v15 Build Core Commands implements artifact-creation responsibilities (slice-verification.sh authoring at plan-slice end; stepN-VERIFY.json writing at Step-end gate; deferred-items.md initialization at execute-slice start)."
         - "Phase 405 (Deviation Rules & Subagent Management) consumes split_recommendation telemetry (rollup over a milestone) for DEV-04 architectural human-gate triggering."
         - "Phase 406 (Harness Architecture Rollup) cites the master taxonomy + catalog for the layered diagram event surface; harness_intervention (HRN-05) aggregates all 10 newly-registered events."
       - `## Task Commits` — placeholder
       - `## Deviations from Plan` — placeholder
       - `## Self-Check: PASSED` — checklist of every must_haves.truth verified

    Length: 80-130 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/04-step-events-SUMMARY.md` — sibling SUMMARY exemplar for a plan that does v40 EVENT-TAXONOMY.md amendment + canonical-spec authoring; mirror format especially the `## Files Touched` listing both modified + created and the `requirements-touched` vs `requirements-completed` distinction.
        - Known: Phase 404 sibling SUMMARYs (Plans 01, 02, 03 if available) — for consistency within Phase 404.
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md per-plan-SUMMARY-mandatory subsection (project gate).
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/04-event-amendments-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 60)}' \
        && grep -q "Plan 404-04" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "EVENT-TAXONOMY.md" "$F" \
        && grep -q "ARTIFACT-CATALOG.md" "$F" \
        && grep -q "stepN-VERIFY.json" "$F" \
        && grep -q "deferred-items.md" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] SUMMARY exists with >= 60 lines.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: verify_automated] SUMMARY references Plan 04, both amended v40 files, all 3 sibling Plan 404 specs, and confirms the 49-event count + 3-new-artifact registration.
    - [check: verify_automated] All four core sections present (What Was Built, Key Decisions, Files Touched, Downstream Hooks).
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate closed for Plan 404-04.
  </done>
</task>

</tasks>

<verification>
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` exists with >= 320 lines (baseline ~281 + ~40 amendment).
- `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` exists with >= 830 lines (baseline ~806 + ~30 amendment).
- `.planning/milestones/v41/phases/404/04-event-amendments-SUMMARY.md` exists with >= 60 lines.
- EVENT-TAXONOMY.md has at least 3 `## v41 Amendment` H2 headings (Phase 402, Phase 403, Phase 404).
- ARTIFACT-CATALOG.md has at least 2 `## v41 Amendment` H2 headings (Phase 402, Phase 404).
- All 10 new event types grep-verifiable in EVENT-TAXONOMY.md: state.step.gate_strike, state.step.gate_resolved, state.step.step_verify_completed, state.slice.slice_verify_completed, state.step.paralysis_event, state.step.scope_check, state.step.scope_deviation, state.step.scope_deviation_request, state.step.scope_deviation_resolved, state.slice.split_recommendation.
- All 3 new artifacts grep-verifiable in ARTIFACT-CATALOG.md: stepN-VERIFY.json, slice-verification.sh, deferred-items.md. Plus N-VERIFICATION.md column-schema pin.
- Naming-convention regex `^state\.(step|slice)\.[a-z_]+$` passes for all event types in EVENT-TAXONOMY.md (python3 check).
- Forward-pointers to PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, SCOPE-PROHIBITION.md all present in both amendment blocks.
- Phase 402 amendment block in EVENT-TAXONOMY.md (line ~199 `## v41 Amendment`) unchanged.
- Phase 403 amendment block in EVENT-TAXONOMY.md (line ~239 `## v41 Amendment — Step-Tier Event Family Extension`) unchanged.
- Phase 402 amendment block in ARTIFACT-CATALOG.md (line ~796 `## v41 Amendment`) unchanged.
- No `state.teach.` references introduced into either amended file.
</verification>

<success_criteria>
- PRF-06 closure (taxonomy registry): state.step.gate_strike + state.step.gate_resolved registered with forward-pointer to PROOF-GATE.md §6 and §7.
- PRF-05 closure (taxonomy + artifact): state.step.step_verify_completed + state.slice.slice_verify_completed registered; stepN-VERIFY.json + slice-verification.sh + N-VERIFICATION.md column-schema pin registered.
- APG-06 closure (taxonomy registry): state.step.paralysis_event registered with forward-pointer to ANALYSIS-PARALYSIS-GUARD.md §8.
- SRP-02 closure (taxonomy registry): state.step.scope_check registered with forward-pointer to SCOPE-PROHIBITION.md §5.
- SRP-04 closure (taxonomy registry): state.step.scope_deviation + state.step.scope_deviation_request + state.step.scope_deviation_resolved registered with forward-pointer to SCOPE-PROHIBITION.md §6, §7.
- SRP-05 closure (taxonomy registry): state.slice.split_recommendation registered with forward-pointer to SCOPE-PROHIBITION.md §8.
- SRP-06 closure (artifact catalog): deferred-items.md registered in canonical Slice folder layout with forward-pointer to SCOPE-PROHIBITION.md §9.
- Per-plan SUMMARY.md gate closed.
- Append-only convention preserved (v40 originals + prior v41 amendments verbatim).
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (>= 320 lines; +~40 from amendment)
- `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` (>= 830 lines; +~30 from amendment)
- `.planning/milestones/v41/phases/404/04-event-amendments-SUMMARY.md` (>= 60 lines)

This plan closes Phase 404's registry-side work; the three substantive spec docs (PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, SCOPE-PROHIBITION.md) from Plans 01-03 are now fully indexed in v40's master taxonomy + artifact catalog. Phase 405 (Deviation Rules & Subagent Management) can proceed; the event surface for DEV-04 architectural human-gate (consumes split_recommendation telemetry) and DEV-05 tiered autonomy auto-approval policy (for scope_deviation_request) is registered.
</output>
