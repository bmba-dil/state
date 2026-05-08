---
phase: 402
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
autonomous: true
requirements:
  - CTX-01
  - CTX-02
  - CTX-03
  - CTX-04
  - CTX-05
  - CTX-06
  - CTX-07
  - CTX-08
  - CTX-09

must_haves:
  truths:
    - "CONTEXT-PROTOCOL.md exists and fully specifies the Slice context-management protocol."
    - "200k absolute Slice budget, fresh-session-per-Slice rule, and intra-Slice compaction rule are documented with exact harness behavior."
    - "Threshold action table (≤25% emergency, ≤35% warning, slice-boundary spawn, reactive overflow) is exhaustive and grep-greppable."
    - "CompactionSnapshot Pydantic model is fully written out with extra='forbid', orjson round-trip example, and every field from CONTEXT.md."
    - "Reinject payload XML body shape and Pydantic JSON metadata shape are both documented."
    - "Identifier-survival contract (slice_id/step_id/task_id) is explicit across both compaction and Slice-boundary spawn."
    - "Context-meter wiring (plugin tool.execute.after + daemon SSE harness.context_meter) is named with hook signatures."
    - "Reactive overflow recovery one-shot pattern (CTX-09) is documented per gsd-2 reference."
    - "Reference Implementation section cites the four gsd-2 docs by name and defers algorithm internals to v14."
  artifacts:
    - path: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      provides: "Canonical context-management protocol covering CTX-01..09."
      min_lines: 400
  key_links:
    - from: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      to: ".planning/milestones/v41/compaction-docs-from-gsd-2/context-management.md"
      via: "Reference Implementation citation"
      pattern: "compaction-docs-from-gsd-2"
    - from: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      to: ".planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md"
      via: "Sibling-doc cross-reference (Slice boundary triggers session spawn)"
      pattern: "SLICE-CYCLE\\.md"
---

<objective>
Author the canonical context-management protocol document for v41. CONTEXT-PROTOCOL.md specifies the 200k absolute Slice budget, fresh-session-per-Slice spawn rule, intra-Slice compaction rule, threshold action ladder, the CompactionSnapshot Pydantic model, the reinject payload (XML body + JSON metadata), the identifier-survival contract, the context-meter wiring, and the reactive-overflow one-shot pattern.

Purpose: This doc is the design contract that v14 Build Kernel implements. Phase 402 owns the trigger surface and snapshot schema; algorithm internals defer to v14. Cites gsd-2 reference docs as canonical algorithm source.
Output: One markdown spec doc at `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md`, ≥400 lines, fully populated.
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
@.planning/milestones/v41/compaction-docs-from-gsd-2/compaction-threshold-management.md
@.planning/milestones/v41/compaction-docs-from-gsd-2/context-management.md
@.planning/milestones/v41/compaction-docs-from-gsd-2/compaction.ts.md
@.planning/milestones/v41/compaction-docs-from-gsd-2/budget-computation.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
</context>

<threat_model>
Phase 402 is design-only. CONTEXT-PROTOCOL.md introduces no production attack surface — it is a markdown specification. Threats considered:

- **Markdown injection in cited content**: This doc embeds a Pydantic model, an orjson round-trip example, and an XML reinject payload. Mitigation — all code blocks are fenced; no executable templating; all examples are illustrative.
- **Schema drift between this doc and v14 implementation**: If v14 implements a CompactionSnapshot with a different field set, the design contract breaks. Mitigation — every field listed here matches 402-CONTEXT.md verbatim and uses `extra="forbid"` so unknown fields fail validation; v14 must extend via explicit migration.
- **OAuth-stealth-route bleed**: PROJECT.md says "Anthropic OAuth stealth never routes through litellm." This doc must not introduce a context-meter that touches OAuth headers. Mitigation — context-meter reads `usage.input_tokens + usage.cache_read_input_tokens` from tool-response payloads only; never inspects auth headers; explicit note in the wiring section.
- **Mode-isolation drift**: Build-only spec. Mitigation — explicit "Build-mode only" header note; no Teach references.

No production code lands. No secrets. No network calls. No untrusted input.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Write CONTEXT-PROTOCOL.md spec — budget, session rule, threshold table</name>
  <files>
    .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/402/402-CONTEXT.md (full file — every decision is load-bearing for this doc)
    - .planning/milestones/v41/REQUIREMENTS.md lines 24-50 (CTX-01..08 verbatim)
    - .planning/milestones/v41/HANDOFF.md (D-2, D-3, D-4 sections)
    - .planning/milestones/v41/compaction-docs-from-gsd-2/compaction-threshold-management.md (full file — canonical for threshold logic + overflow one-shot)
    - .planning/milestones/v41/compaction-docs-from-gsd-2/context-management.md lines 136-200 (token accounting §2) and lines 478-545 (budget computation §6)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-50 (Pydantic frontmatter pattern — extra="forbid" convention)
  </read_first>

  <action>
    Create the file at the exact path above. Write the section structure below; the next task fills in the snapshot/reinject/identifier-survival sections. This task owns sections 1–7. Source content verbatim from 402-CONTEXT.md `<decisions>` — do NOT re-derive.

    Required H1 + H2 sections in order:

    1. `# Context Protocol (Canonical, v41)` — H1 title.
    2. Frontmatter prose block at top: "Phase: 402", "Status: Canonical (v41)", "Requirements covered: CTX-01..09", "Reference algorithm: `.planning/milestones/v41/compaction-docs-from-gsd-2/*` (defers algorithm internals to v14 Build Kernel)". Include mode-isolation note: "Build-mode only. `state.build.harness.*` MUST NOT import `state.teach.*`. Cardinal rule per PROJECT.md."
    3. `## Overview` — 1 paragraph: harness controls context, not the agent; trigger surface + snapshot schema + reinject payload owned here; algorithm internals deferred to v14.
    4. `## 200k Absolute Slice Budget (CTX-01)` — 1 paragraph stating: budget is 200k absolute regardless of model context-window size (200k or 1M+); plan-slice sizes Steps to ≤80% (~160k); the budget is enforced per-Slice, not per-session within a Slice. Cite REQUIREMENTS.md CTX-01 and HANDOFF.md D-3.
    5. `## Fresh Session Per Slice (CTX-02)` — Document the spawn protocol:
       - Daemon initiates spawn at every Slice boundary (verify-slice → next Slice's design-slice).
       - Plugin's `chat.params` hook injects new Slice context.
       - The injected payload includes parent Phase intentions, non-negotiables/crits, current Slice scope.
       - Cite SLICE-CYCLE.md for the four-stage cycle that defines "Slice boundary" and HANDOFF.md D-2.
       - Note: same `slice_id` is reused only on Slice-revert (per v40 TIER-SLICE.md `state.slice.replanned` event); otherwise each new Slice gets a fresh `slice_id`.
    6. `## Intra-Slice Compaction (CTX-03)` — Document the in-Slice compaction protocol:
       - Triggered by opencode's `session.compacting` hook OR daemon-initiated threshold/overflow paths.
       - Same `session_id` continues; harness snapshots state, strips stale content, reinjects compact form.
       - Cite gsd-2 `compaction-threshold-management.md` for the three-controller design (manual / auto; state omits the third "branch" controller per CONTEXT.md `<decisions>` "Abort controller multiplicity").
       - Document state's two-controller subset (manual + auto) and the `is_compacting = manual_active OR auto_active` derived predicate. Explicit forbidden cross-cancel: user `/compact` cancellation must NOT kill an in-flight auto-compaction.
       - Note: state does NOT introduce its own slash command for manual `/compact`. State observes opencode's native `/compact` via `session.compacting` and writes a `compaction.snapshot_taken` event with `trigger="manual"`. State only initiates the auto path (threshold + overflow).
    7. `## Threshold Action Table (CTX-04 + CTX-09)` — Reproduce the exact decisions from 402-CONTEXT.md `<decisions>` "Threshold action table" subsection. Required content (write verbatim from CONTEXT.md):
       - Markdown table `| Threshold | Trigger | Hook | Action | Event Emitted |` with rows for:
         - **Emergency (≤25% remaining)** — plugin `tool.execute.after` reports threshold cross; daemon waits for current `<task>` to complete, then snapshot+rotate at task boundary; emits `compaction.snapshot_taken` (trigger=`threshold`).
         - **Warning (≤35% remaining)** — plugin `tool.execute.before` blocks start of next `<task>` in same session; daemon flags `next-task-blocked`; executor finishes current task / cleanup / verify; Write/Edit aimed at next-task is rejected with `compact-and-rotate` advisory; emits `harness_intervention` (tier=`tool-block`, trigger_reason=`warning_threshold`); reuses HRN-04 tier-2 intervention.
         - **Slice boundary** — verify-slice closes; daemon spawns fresh session; plugin `chat.params` reinjects new Slice context; mandatory regardless of remaining budget. Emits `state.slice.verify_completed` (per SLICE-CYCLE.md) followed by the new Slice's `state.slice.created`.
         - **Reactive overflow (CTX-09)** — provider rejects request with context-overflow error; harness mirrors gsd-2 `_overflowRecoveryAttempted` one-shot. Steps:
           1. Strip the failing assistant turn from context.
           2. Force-compact (snapshot+reinject), bypassing the percent-threshold check.
           3. Retry the provider call once.
           4. Set `_overflow_recovery_attempted` flag on the active session.
           5. Reset the flag on next user/agent message OR successful turn.
           6. If flag already set when a second overflow fires within the same user turn, surface the error to the user (no infinite loop).
           Emits `compaction.snapshot_taken` (trigger=`overflow`).
       - Subsection `### Threshold trigger source — plugin reads + daemon decides`: plugin's `tool.execute.after` reads `usage.input_tokens + usage.cache_read_input_tokens` per gsd-2 §2.2, posts to daemon over HTTP; daemon middleware consults harness state and decides intervention tier (advisory inject / tool-block / clear+reinject / human gate). Plugin shim stays a thin reporter — preserves the ~300 LOC contract from PROJECT.md.
       - Subsection `### Per-Slice threshold override`: Slice frontmatter MAY narrow (move thresholds *earlier* / make stricter) but never widen. Field: `compaction: {emergency_pct: int, warning_pct: int}`. Daemon validates: `emergency_pct ≥ 25` and `warning_pct ≥ 35` (defaults). Mirrors SUB-03 narrow-only pattern.
       - Subsection `### Manual /compact telemetry`: state observes opencode's native `/compact` via `session.compacting` and emits `compaction.snapshot_taken` with `trigger="manual"`, `from_hook=False`. Sufficient for v1; richer telemetry deferred per CONTEXT.md `<deferred>`.

    Use markdown tables consistently. Cite REQ-IDs inline (e.g., "(CTX-04)", "(CTX-09)") so grep can verify coverage. Do NOT use prohibited language ("v1", "simplified", "placeholder", "TODO", "FIXME", "future"). The phrase "v1" appears in this doc only as a milestone version label inside a quoted parenthetical (e.g., "(sufficient for v1; richer telemetry deferred)") — use `**Sufficient for the v1 implementation**` wording with explicit milestone reference if grep flags this.

    <quality_scan>
      <code_to_reuse>
        - Known: 402-CONTEXT.md `<decisions>` section — every threshold-table row, override rule, and manual-compact rule is sourced verbatim
        - Known: gsd-2 `compaction-threshold-management.md` — abort-controller pattern, `_overflowRecoveryAttempted` one-shot, `shouldCompact` signature
        - Known: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — pattern for event tables
        - Grep pattern: `grep -n "≤25%\|≤35%\|threshold\|overflow" .planning/milestones/v41/phases/402/402-CONTEXT.md` (locates all CTX-04/CTX-09 source content)
      </code_to_reuse>
      <docs_to_consult>
        - 402-CONTEXT.md `<decisions>` "Threshold action table" subsection — load-bearing
        - 402-CONTEXT.md `<decisions>` "Abort controller multiplicity" subsection — two-controller decision
        - gsd-2 `compaction-threshold-management.md` "Why it works that way" §2 (abort multiplicity) and §3 (reactive overflow)
        - HANDOFF.md D-2, D-3 — locked decisions
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only spec doc; no exported logic. Verification is grep-based.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>test -f .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^# Context Protocol (Canonical, v41)" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## 200k Absolute Slice Budget" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Fresh Session Per Slice" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Intra-Slice Compaction" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Threshold Action Table" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "_overflow_recovery_attempted" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "tool.execute.after" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "tool.execute.before" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "session.compacting" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md</automated>
  </verify>

  <acceptance_criteria>
    - File exists at exact path.
    - Sections 1-7 H1/H2 headings all present (verified by `<verify>` greps).
    - Threshold table contains all four rows (emergency, warning, slice-boundary, overflow): `for s in "≤25%" "≤35%" "Slice boundary" "overflow"; do grep -qi "$s" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md || echo "MISSING $s"; done` produces no output.
    - Plugin hook names cited: `tool.execute.before`, `tool.execute.after`, `session.compacting`, `chat.params` all greppable.
    - REQ-IDs CTX-01 through CTX-04 + CTX-09 referenced inline: `for n in 01 02 03 04 09; do grep -q "CTX-$n" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md || echo "MISSING CTX-$n"; done` produces no output.
    - Mode-isolation note present: `grep -q "Build-mode only" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md`.
    - HRN-04 / SUB-03 cross-references present: `grep -q "HRN-04" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && grep -q "SUB-03" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md`.
  </acceptance_criteria>

  <done>
    Sections 1–7 of CONTEXT-PROTOCOL.md are written. Budget rule, session rule, intra-Slice compaction rule, and the four-row threshold action table (including CTX-09 reactive overflow) are all canonical and grep-verifiable. Plugin/daemon role split is explicit. Task 2 picks up at section 8 (CompactionSnapshot Pydantic model).
  </done>
</task>

<task type="auto">
  <name>Task 2: Append CompactionSnapshot, reinject payload, identifier-survival, context-meter wiring, reference-impl sections</name>
  <files>
    .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (the file as written by Task 1 — append sections 8+ to the same file)
    - .planning/milestones/v41/phases/402/402-CONTEXT.md (full file)
    - .planning/milestones/v41/compaction-docs-from-gsd-2/context-management.md lines 423-477 (Compaction Persistence §5) and 640-720 (Snapshot Persistence §7)
    - .planning/milestones/v41/compaction-docs-from-gsd-2/budget-computation.md (full file — for context-meter math)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic patterns)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md lines 1-50 (event-naming conventions)
  </read_first>

  <action>
    Append sections 8–14 to the existing CONTEXT-PROTOCOL.md (do NOT overwrite — append). Source content verbatim from 402-CONTEXT.md.

    8. `## Compaction Snapshot Schema (CTX-05)` —
       - Subsection `### Layer A — Authoritative (Pydantic + orjson + event store)`. Reproduce the EXACT Pydantic class verbatim from 402-CONTEXT.md `<decisions>` section "Compaction snapshot — two-layer persistence" (the code block beginning `class CompactionSnapshot(BaseModel):`). The code block must include:

         ```python
         from datetime import datetime
         from pathlib import Path
         from typing import Literal
         from pydantic import BaseModel, ConfigDict

         class CompactionSnapshot(BaseModel):
             model_config = ConfigDict(extra="forbid")
             slice_id: str
             step_id: str
             task_id: str | None              # None if compaction fires between tasks
             session_id: str                  # session being compacted
             prior_session_id: str | None     # set on Slice-boundary spawn
             summary: str                     # markdown digest, ≤8KB; verbatim
             first_kept_entry_id: str         # event-store row id of first non-summarized entry
             tokens_before: int               # telemetry: token count at trigger
             trigger: Literal["manual", "threshold", "overflow"]
             from_hook: bool                  # True if extension hook initiated
             worktree_path: Path
             provides_blocks: list[ProvidesBlock]   # upstream Step SUMMARY.md `provides:` blocks
             active_plan_path: Path           # current stepNPLAN.md
             current_task_pointer: TaskPointer | None
             last_verify_result: VerifyResult | None
             created_at: datetime             # UTC, ISO-8601
         ```

         Field-by-field commentary table (markdown table `| Field | Type | Source | Notes |`).
       - Subsection `### Round-trip example`: orjson serialize → bytes → deserialize using `CompactionSnapshot.model_validate_json(...)`. Pin determinism flags: `orjson.dumps(snapshot.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS | orjson.OPT_NAIVE_UTC)`. Note: planner picks `OPT_NAIVE_UTC` (datetimes serialize as naive UTC ISO-8601 strings); v14 implementer must use the same flag combination for byte-identical round-trip.
       - Subsection `### Layer B — Lossy markdown digest (`.state/build/last-snapshot.md`)`. Document:
         - Path: `<projectRoot>/.state/build/last-snapshot.md` (per-project, fixed path; mirrors gsd-2 `compaction-snapshot.ts` model).
         - Byte cap: ≤2KB UTF-8, enforced in memory before write.
         - **Three priority tiers** in fixed order (exact heading wording the projector emits):
           - `## Active context` — single line: `Active: arc-N / stage-N / slice-N / step-N — <title>`.
           - `## Top project memories` — up to 6 entries.
           - `## Recent run history` — up to 5 most-recent run-slice executions.
         - Use case: cross-session orientation when a fresh agent boots without knowing `session_id` (it knows `process.cwd()`); reads `.state/build/last-snapshot.md` from there before daemon hand-off completes.
         - Written by the daemon's projector on every `compaction.snapshot_taken` event.
         - **NOT atomic in v1** — byte cap enforced in memory before write, but no temp+rename. Documented as known limitation; atomic-write follow-up deferred to v44 (Rust DB rewrite).
       - Subsection `### Helper-type sketches`: include three helper Pydantic stubs the snapshot references — `ProvidesBlock`, `TaskPointer`, `VerifyResult` — each with `model_config = ConfigDict(extra="forbid")` and 2-3 fields each (`ProvidesBlock`: `from_step_id: str`, `provides: dict[str, str]`; `TaskPointer`: `task_index: int`, `task_name: str`, `started_at: datetime`; `VerifyResult`: `status: Literal["pass", "fail", "skipped"]`, `details: str`, `verified_at: datetime`). Note: full helper-type schemas are owned by Phase 403 / Phase 404; this doc lists the minimum shape needed to validate `CompactionSnapshot`.

    9. `## Reinject Payload (CTX-06)` — Hybrid format documentation:
       - Subsection `### Body (LLM-facing) — XML-tagged markdown`. Reproduce the EXACT XML body shape verbatim from 402-CONTEXT.md `<decisions>` "Reinject payload — hybrid format" section (the fenced block beginning `<slice_context>`):

         ```xml
         <slice_context>
           <slice_id>...</slice_id>
           <step_id>...</step_id>
           <task_id>...</task_id>
         </slice_context>

         <active_plan>
           <!-- verbatim stepNPLAN.md content, content-stripped per PAP-06 -->
         </active_plan>

         <current_task_pointer>...</current_task_pointer>

         <last_verify_result>
           <status>pass|fail|skipped</status>
           <details>...</details>
         </last_verify_result>

         <upstream_provides>
           <provides from="step-N">...</provides>
         </upstream_provides>

         <worktree_path>/path/to/worktree</worktree_path>

         <compaction_summary>
           <!-- six-section markdown digest from compaction; see gsd-2 §4.4 reference -->
         </compaction_summary>
         ```

         Note: passed via `chat.params` hook as a single system-message string. Anthropic's RLHF tuning is the load-bearing reason for XML tagging; markdown-header fallback is acceptable for XML-hostile providers.
       - Subsection `### Metadata (programmatic) — Pydantic JSON via chat.params metadata field`. Document: same `CompactionSnapshot` instance serialized as JSON via orjson, attached to `chat.params.metadata` for daemon/projector/SSE consumers and other middleware. Pydantic model is single source of truth; XML body is a rendered view.
       - Subsection `### Content-stripping reference`: `<active_plan>` content is content-stripped per PAP-06 (Phase 403 owns PAP-06; this doc references the rule).

    10. `## Identifier Survival Contract (CTX-07)` —
        - Subsection `### Canonical storage`: SQLite event store at `.state/events.sqlite` (authoritative; survives daemon restart). The `compaction.snapshot_taken` event row carries `slice_id`, `step_id`, `task_id`, `session_id`, `prior_session_id`.
        - Subsection `### Transport across session-spawn boundary`: daemon mints new session, attaches IDs (read from event store) into `chat.params.metadata`; plugin's `chat.message` hook (or first `tool.execute.before` fire) writes them to plugin-local hot state.
        - Subsection `### Reinjection event — `compaction.reinject_completed``: Reproduce verbatim the Pydantic class from 402-CONTEXT.md `<decisions>`:

          ```python
          class CompactionReinjectCompleted(BaseModel):
              model_config = ConfigDict(extra="forbid")
              prior_session_id: str
              new_session_id: str
              slice_id: str
              step_id: str
              task_id: str | None
              snapshot_event_id: str         # row id of source compaction.snapshot_taken
              reinject_at: datetime
          ```

          Replay reconstructs the full Slice timeline by following the `prior_session_id → new_session_id` chain.
        - Subsection `### Subagent compaction inheritance` — when parent Slice session compacts, in-flight subagents finish independently; their structured returns are written to event store via `subagent_complete`; parent's reinject payload includes those returns as `<provides>` blocks; no subagent reinjection (subagents are SUB-04 free context).

    11. `## Context-Meter Wiring (CTX-08)` —
        - Subsection `### Plugin hook — `tool.execute.after``: fires after every tool call; reads `usage.input_tokens + usage.cache_read_input_tokens` from tool response (gsd-2 §2.2 `calculateContextTokens` pattern); reports `{session_id, tokens_used, tokens_budget}` to daemon over HTTP after each fire.
        - Subsection `### Token-counting fallback`: if `usage` is absent (error turn / non-Anthropic provider that doesn't surface usage), plugin uses gsd-2 §2.1 `chars/4` heuristic via `estimateContextTokens`. Heuristic is imprecise (±20–40%); accepted as fallback. Documented limitation.
        - Subsection `### Daemon SSE event — `harness.context_meter``: payload `{session_id, slice_id, tokens_used, tokens_budget, pct_remaining, threshold_state}` where `threshold_state ∈ {ok, warning, emergency, over_budget}`. Debounced to max 1/sec daemon-side to prevent SSE spam; plugin still reports per-tool-call to daemon, daemon throttles outbound to TUI.
        - Subsection `### TUI threshold-state surface`: v9 statusline shows context budget percent + `threshold_state` color (green=ok / amber=warning / red=emergency); v9 sidebar shows persistent token countdown + budget bar; one-shot toast on threshold *cross* (ok→warning, warning→emergency, any→over_budget); toast text names next harness action ("entering compact-and-rotate at next task boundary").

    12. `## Reactive Overflow Recovery (CTX-09)` — Reiterate the six-step one-shot pattern from §7 in dedicated subsections:
        - Subsection `### Trigger`: provider rejects request with context-overflow error mid-turn.
        - Subsection `### One-shot flow` — numbered list of the six steps verbatim from 402-CONTEXT.md "Reactive overflow recovery" (strip failing turn → force-compact → retry → set flag → reset on next message OR success → surface error if flag already set on second overflow within same user turn).
        - Subsection `### Cross-reference to gsd-2`: cite `compaction-threshold-management.md` §"Abstract algorithm" `onProviderOverflowError()` block.

    13. `## Reference Implementation (deferred to v14)` — Algorithm internals deferred. Cite the four gsd-2 docs by name with relative paths under `.planning/milestones/v41/compaction-docs-from-gsd-2/`:
        - `compaction-threshold-management.md` — three-controller pattern + `_overflowRecoveryAttempted` flag (state uses two controllers).
        - `context-management.md` — token accounting (§2), decision algorithm (§3), summary generation (§4), persistence (§5), budget computation (§6), snapshot persistence (§7), state diagram (§8).
        - `compaction.ts.md` — full file walkthrough.
        - `budget-computation.md` — pure-function budget engine.

        Explicit deferral list (Phase 402 does NOT own): cut-point detection algorithm, summary-generation prompt templates (`SUMMARIZATION_PROMPT`, `UPDATE_SUMMARIZATION_PROMPT`, `TURN_PREFIX_SUMMARIZATION_PROMPT`), single-pass-vs-chunked dispatch, degenerate-summary R6 fallback, file-operation tail extraction. v14 Build Kernel implements per these docs.

    14. `## Requirements Coverage` — Markdown table `| REQ-ID | Section | Notes |`, one row per CTX-01..CTX-09, pointing each to the H2 above where it is fully specified.

    Final check: append `## Cross-References` block linking SLICE-CYCLE.md (sibling), v40 EVENT-TAXONOMY.md (event additions in Plan 03 amendment), v40 FRONTMATTER-SCHEMAS.md (Pydantic pattern), and the four gsd-2 reference docs.

    <quality_scan>
      <code_to_reuse>
        - Known: 402-CONTEXT.md `<decisions>` section is the verbatim source for the Pydantic class, the XML body shape, and the lossy-digest tier names — copy, do not re-derive
        - Known: `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` lines 14-15 — `extra="forbid"` convention pattern; reuse the exact import-block style (`from pydantic import BaseModel, ConfigDict`) for Layer-A code blocks
        - Known: gsd-2 `compaction-threshold-management.md` "Abstract algorithm" — `onProviderOverflowError()` reference for §12
        - Grep pattern: `grep -n "first_kept_entry_id\|provides_blocks\|active_plan_path\|current_task_pointer" .planning/milestones/v41/phases/402/402-CONTEXT.md` (locate every authoritative field reference)
      </code_to_reuse>
      <docs_to_consult>
        - 402-CONTEXT.md `<decisions>` "Compaction snapshot — two-layer persistence" — load-bearing for §8
        - 402-CONTEXT.md `<decisions>` "Reinject payload — hybrid format" — load-bearing for §9
        - 402-CONTEXT.md `<decisions>` "Identifier survival across session-spawn boundaries" — load-bearing for §10
        - 402-CONTEXT.md `<decisions>` "Context-meter wiring" + "TUI threshold-state surface" — load-bearing for §11
        - gsd-2 `context-management.md` §2 (token accounting) and §6 (budget computation) — for context-meter math
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only spec doc; no exported logic.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>test -f .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
[ "$(wc -l < .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md)" -ge 400 ] && \
grep -q "^## Compaction Snapshot Schema" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Reinject Payload" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Identifier Survival Contract" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Context-Meter Wiring" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Reactive Overflow Recovery" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Reference Implementation" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "^## Requirements Coverage" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "class CompactionSnapshot" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "first_kept_entry_id" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "class CompactionReinjectCompleted" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "harness.context_meter" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && \
grep -q "compaction-docs-from-gsd-2" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md</automated>
  </verify>

  <acceptance_criteria>
    - File length ≥400 lines.
    - All 14 H1/H2 sections present (verified by `<verify>` greps for the seven new sections + the seven from Task 1).
    - CompactionSnapshot Pydantic class includes every field from CONTEXT.md: `for f in slice_id step_id task_id session_id prior_session_id summary first_kept_entry_id tokens_before trigger from_hook worktree_path provides_blocks active_plan_path current_task_pointer last_verify_result created_at; do grep -q "$f" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md || echo "MISSING $f"; done` produces no output.
    - `extra="forbid"` present at least twice (one each for CompactionSnapshot and CompactionReinjectCompleted): `[ "$(grep -c 'extra=\"forbid\"' .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md)" -ge 2 ]`.
    - orjson round-trip example present: `grep -q "orjson.dumps" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && grep -q "OPT_SORT_KEYS" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && grep -q "OPT_NAIVE_UTC" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md`.
    - XML reinject body greppable: `grep -q "<slice_context>" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && grep -q "<active_plan>" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && grep -q "<compaction_summary>" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md`.
    - All 9 CTX REQ-IDs (CTX-01..09) referenced: `for n in 01 02 03 04 05 06 07 08 09; do grep -q "CTX-$n" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md || echo "MISSING CTX-$n"; done` produces no output.
    - Lossy digest path documented: `grep -q "\.state/build/last-snapshot.md" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md`.
    - Three lossy-digest tiers: `grep -q "Active context" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && grep -q "Top project memories" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md && grep -q "Recent run history" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md`.
    - All four gsd-2 reference docs cited: `for d in compaction-threshold-management context-management compaction.ts budget-computation; do grep -q "$d" .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md || echo "MISSING $d"; done` produces no output.
  </acceptance_criteria>

  <done>
    CONTEXT-PROTOCOL.md is the canonical context-management protocol covering CTX-01..09. CompactionSnapshot Pydantic model is fully specified with `extra="forbid"` and orjson round-trip; reinject payload (XML body + JSON metadata) documented; identifier-survival contract complete; context-meter wiring named with hook signatures; reactive overflow recovery documented with one-shot flag; reference implementation deferred to v14 with explicit gsd-2 doc citations.
  </done>
</task>

</tasks>

<verification>
- File at `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` exists with ≥400 lines.
- All 14 H1/H2 sections present.
- Pydantic models written verbatim from CONTEXT.md with `extra="forbid"`.
- All 9 CTX REQ-IDs cited.
- All four gsd-2 reference docs cited by name.
- Mode-isolation note + threat-model considerations honored.
</verification>

<success_criteria>
- ROADMAP.md success criteria 3, 4, 5 satisfied:
  - 3: 200k absolute budget + fresh-session-per-Slice + intra-Slice compaction + threshold action table all documented.
  - 4: CompactionSnapshot Pydantic model + orjson round-trip + reinject payload + event-store row schema all documented.
  - 5: Identifier-survival contract specified; context-meter read path names plugin hook + daemon SSE event.
- CTX-09 (Reactive overflow recovery) fully specified in this doc; Plan 04 adds the requirement to REQUIREMENTS.md so the traceability table matches.
- v14 Build Kernel implementer can implement compaction without re-discovering decisions.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/402/402-02-SUMMARY.md` per project rule. The SUMMARY MUST: (a) link to CONTEXT-PROTOCOL.md, (b) confirm all 14 sections wrote, (c) confirm Pydantic model field set matches CONTEXT.md, (d) note CTX-09 was added in §7 + §12 (Plan 04 will land it in REQUIREMENTS.md).
</output>
