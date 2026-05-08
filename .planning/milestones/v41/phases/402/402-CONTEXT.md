# Phase 402: Slice-Cycle & Context Window Spec — Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 402 produces two canonical specification documents and a set of v40-amendment headers:

1. **`SLICE-CYCLE.md`** — defines the four-stage Slice cycle (canonical owner = Slice; Step is a leaf artifact) with per-stage owner, inputs, outputs, and stage-boundary events. Enumerates every artifact in the canonical Slice folder layout (SLC-06) with its producing stage.
2. **`CONTEXT-PROTOCOL.md`** — defines the 200k absolute Slice budget, the fresh-session-per-Slice rule, the intra-Slice compaction rule, the threshold action table (≤25% emergency, ≤35% warning, slice-boundary spawn), the compaction snapshot Pydantic schema, the reinject payload shape, the identifier-survival contract, and the context-meter wiring.
3. **v41 Amendment headers** appended to every Phase 400 / Phase 401 spec doc affected by the Slice-owns-cycle correction (SLC-07) and the v40↔v41 vocabulary reconciliation.

Phase 402 is design-only. No code lands. Compaction algorithm internals (cut-point detection, summary prompt templates, chunked-vs-single-pass dispatch, degenerate-summary recovery) are deferred to v14 Build Kernel; Phase 402 only owns the trigger surface, the snapshot Pydantic schema, the reinject payload shape, and identifier-survival contract.

</domain>

<decisions>
## Implementation Decisions

### Naming reconciliation (v40↔v41 vocabulary)

- **v40 wins** for stage names: the four Slice stages are **design-slice → research-slice → run-slice → verify-slice**. Carries forward v40 D-03 (`/state-design-slice`, `/state-run-slice`, DESIGN.md, "design"+"run" everywhere). The v41 REQUIREMENTS' use of `discuss-slice/plan-slice/execute-slice/verify-slice` is mechanically rewritten to v40 vocabulary in-place; the rewrite mapping is:

  | v41 REQUIREMENTS term | Canonical (Phase 402) term |
  |---|---|
  | `discuss-slice` | `design-slice` |
  | `plan-slice` (multi-stage internal pipeline) | `research-slice` |
  | `execute-slice` | `run-slice` |
  | `verify-slice` | `verify-slice` |
  | `N-CONTEXT.md` | `DESIGN.md` |
  | `N-DISCUSSION-LOG.md` | `DECISIONS.md` (reuses v40 D-401-02 artifact) |
  | `stepNN-PLAN.md` | `stepNPLAN.md` (v40 D-04 form; no leading zeros) |

- **design-slice** produces: `DESIGN.md` + `DECISIONS.md` (per v40 D-401-09 / D-401-02). Drops v41's bespoke `N-DISCUSSION-LOG.md` artifact in favor of the existing append-only DECISIONS.md.

- **research-slice** is a multi-stage internal pipeline (research → pattern-mapping → planning → validation) producing four artifacts:
  - `N-RESEARCH.md`
  - `N-PATTERNS.md`
  - `stepNPLAN.md` (one per Step, granularity per STP-06)
  - `N-VALIDATION.md` (re-runs planning on failure)

- **run-slice** runs each Step's `stepNPLAN.md` per DAG ordering and writes `stepNSUMMARY.md` for each Step.

- **verify-slice** writes `N-VERIFICATION.md` (truth table) and emits the slice-complete event.

- **Slice folder canonical layout** (amends SLC-06 to v40 vocabulary):
  ```
  slices/N-name/
    DESIGN.md            (design-slice)
    DECISIONS.md         (design-slice + run-slice append-only)
    N-RESEARCH.md        (research-slice / research stage)
    N-PATTERNS.md        (research-slice / pattern-mapping stage)
    stepNPLAN.md         (research-slice / planning stage; 1..M)
    N-VALIDATION.md      (research-slice / validation stage)
    N-UI-SPEC.md         (optional, frontend Slices)
    stepNSUMMARY.md      (run-slice; 1..M)
    N-VERIFICATION.md    (verify-slice)
    deferred-items.md    (out-of-scope findings; per SRP-06)
    RESUME.txt           (cross-session orientation pointer)
  ```

- **v40 amendment writing**: append `## v41 Amendment` block at the bottom of each affected v40 doc, citing prior model + v41 canonical model. Original v40 spec text untouched; amendment block reads as a published correction. No in-line strikethroughs.

- **v40 docs requiring amendment headers** (planner enumerates exhaustively from Phase 400/401 spec inventory):
  - `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — clarify Slice owns the four-stage cycle (was: cycle ownership ambiguous)
  - `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — clarify Step is a leaf artifact (was: D-04/D-11 already aligned, amendment is a forward-pointer to SLICE-CYCLE.md)
  - `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — add Slice-stage-boundary events
  - `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — confirm cascade stops at Slice (Step is leaf)
  - `.planning/milestones/v40/phases/401/specs/*.md` — artifact catalog already enumerated DESIGN/DECISIONS/RESEARCH/stepNPLAN/VERIFICATION/SUMMARY; only minor pointer additions
  - Planner produces a complete amendment-target list as a dependency of the SLICE-CYCLE.md task.

### Threshold action table (CTX-04 expanded)

- **≤25% remaining (Emergency)** — snapshot+rotate at next **task boundary** (current `<task>` block completes first, then snapshot). No mid-tool snapshots; no immediate hard interrupt. Plugin's `tool.execute.after` reports the threshold cross; daemon decides + waits for current task to finish before spawning the new session and reinjecting.

- **≤35% remaining (Warning)** — block start of next task via **`tool.execute.before` hook**. Daemon flags `next-task-blocked` state. Executor finishes current `<task>` (cleanup / last `<verify>` / summary fragment). Any Write/Edit aimed at the *next* task is rejected with a `compact-and-rotate` advisory + `harness_intervention` event (tier=tool-block, trigger_reason=warning_threshold). Reuses HRN-04 tier-2 intervention.

- **Slice boundary** — end session, daemon spawns fresh session via opencode HTTP, plugin's `chat.params` hook reinjects new Slice context. Mandatory regardless of remaining budget.

- **Threshold trigger source**: **plugin reads + daemon decides**. Plugin's `tool.execute.after` reads `usage.input_tokens + usage.cache_read_input_tokens` from the tool response (gsd-2 §2.2 `calculateContextTokens` pattern) and posts to daemon over HTTP. Daemon's middleware consults harness state and decides which intervention tier to fire (advisory inject / tool-block / clear+reinject / human gate). Plugin shim stays a thin reporter (preserves the ~300 LOC contract).

- **Per-Slice threshold override**: Slice frontmatter MAY narrow (move thresholds *earlier* / make stricter) but never widen. Field: `compaction: {emergency_pct: int, warning_pct: int}`. Daemon validates: emergency_pct ≥ default 25; warning_pct ≥ default 35. Mirrors the SUB-03 narrow-only pattern.

- **Manual `/compact`**: state does NOT introduce its own slash command or MCP tool for manual compaction. State observes opencode's native `/compact` via the `session.compacting` hook and writes a `compaction.snapshot_taken` event with `trigger="manual"`. State only initiates the auto path (threshold + overflow).

- **Reactive overflow recovery (NEW — adds CTX-09)**: when the provider rejects a request with a context-overflow error, the harness mirrors gsd-2's `_overflowRecoveryAttempted` one-shot pattern:
  1. Strip the failing assistant turn from the context.
  2. Force-compact (snapshot+reinject), bypassing the percent-threshold check.
  3. Retry the provider call once.
  4. Set the `_overflow_recovery_attempted` flag on the active session.
  5. Reset the flag on next user/agent message OR on successful turn.
  6. If the flag is already set when a second overflow fires within the same user turn, surface the error to the user (no infinite loop).

  This is added as **CTX-09** in REQUIREMENTS.md; planner must amend REQUIREMENTS.md as part of Phase 402's planning.

### Compaction snapshot — two-layer persistence

- **Layer A (authoritative): Pydantic model serialized via orjson, written to `.state/events.sqlite` as a `compaction.snapshot_taken` event.** Field set (gsd-2-aligned, `extra="forbid"`):

  ```python
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

  Round-trip: `orjson.dumps(snapshot.model_dump(mode="json"))` → bytes; reconstruction via `CompactionSnapshot.model_validate_json(...)`. Determinism: orjson with `OPT_SORT_KEYS | OPT_NAIVE_UTC` (or aware-UTC; planner picks; but pin one in the spec).

- **Layer B (orientation): lossy markdown digest at `<projectRoot>/.state/build/last-snapshot.md`, ≤2KB UTF-8.** Mirrors gsd-2's `compaction-snapshot.ts` model (per-project, fixed path). Three priority tiers:
  - `## Active context` — single line: `Active: arc-N / stage-N / slice-N / step-N — <title>`
  - `## Top project memories` — up to 6 entries
  - `## Recent run history` — up to 5 most-recent run-slice executions

  Used for cross-session orientation when a fresh agent boots without knowing the session_id (it knows `process.cwd()` though; reads `.state/build/last-snapshot.md` from there before the daemon hand-off completes). Written on every `compaction.snapshot_taken` event by the daemon's projector.

  **NOT atomic in v1.** Mirror gsd-2 §7.3 honest scoping: byte cap is enforced in memory before write, but no temp+rename. Document as known limitation; atomic write is a v44 (Rust DB rewrite) follow-up.

### Reinject payload — hybrid format

- **Body (LLM-facing)**: XML-tagged markdown, single system-message string passed via `chat.params` hook. Sections (Anthropic-best-practice tagging):
  ```
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
    ...
  </upstream_provides>

  <worktree_path>/path/to/worktree</worktree_path>

  <compaction_summary>
    <!-- six-section markdown digest from compaction; see gsd-2 §4.4 reference -->
  </compaction_summary>
  ```
  Anthropic's RLHF-tuned response to XML tagging is the load-bearing reason for this shape. Other providers (Gemini, GPT) parse XML adequately; markdown headers are an acceptable fallback if a future provider is XML-hostile.

- **Metadata (programmatic)**: same Pydantic snapshot serialized as JSON, attached to `chat.params` metadata field for daemon/projector/SSE consumers and other middleware. The Pydantic model is the single source of truth; the body is a rendered view.

### Compaction algorithm — scope deferral

- Phase 402 owns: trigger surface (when), Pydantic snapshot schema (what), reinject payload shape (how it's delivered), identifier-survival contract (what survives).

- Phase 402 does NOT own: cut-point detection algorithm, summary-generation prompt templates (`SUMMARIZATION_PROMPT`, `UPDATE_SUMMARIZATION_PROMPT`, `TURN_PREFIX_SUMMARIZATION_PROMPT`), single-pass-vs-chunked dispatch, degenerate-summary R6 fallback, file-operation tail extraction. These are deferred to **v14 Build Kernel**.

- `CONTEXT-PROTOCOL.md` includes a `## Reference Implementation` section pointing to `.planning/milestones/v41/compaction-docs-from-gsd-2/*.md` as the canonical algorithm source. v14 implements per those patterns. Phase 402 keeps the design-only framing without losing the reference trail.

### Identifier survival across session-spawn boundaries

- **Canonical storage**: SQLite event store (`.state/events.sqlite`). The `compaction.snapshot_taken` event row carries `slice_id`, `step_id`, `task_id`, `session_id`, `prior_session_id`. Authoritative; survives daemon restart.

- **Transport to new session**: `chat.params` metadata field on the new session's first hook fire. Daemon mints the new session, attaches the IDs (read from event store) into `chat.params.metadata`, and the plugin's `chat.message` hook (or first `tool.execute.before` fire) writes them to plugin-local hot state.

- **Reinjection event**: `compaction.reinject_completed` emitted by the daemon when the new session's `chat.params` hook acknowledges receipt. Schema:
  ```python
  class CompactionReinjectCompleted(BaseModel):
      model_config = ConfigDict(extra="forbid")
      prior_session_id: str
      new_session_id: str
      slice_id: str
      step_id: str
      task_id: str | None
      snapshot_event_id: str         # row id of the source compaction.snapshot_taken
      reinject_at: datetime
  ```

  Replay can reconstruct the full Slice timeline by following the `prior_session_id → new_session_id` chain.

### Context-meter wiring

- **Plugin hook**: `tool.execute.after` (fires after every tool call). Reads `usage.input_tokens + usage.cache_read_input_tokens` from the tool response (gsd-2 §2.2). Reports `{session_id, tokens_used, tokens_budget}` to daemon over HTTP after each fire.

- **Token-counting fallback**: if `usage` is absent (error turn / non-Anthropic provider that doesn't surface usage), plugin uses gsd-2 §2.1 `chars/4` heuristic via `estimateContextTokens`. Heuristic is known imprecise (±20-40%); accepted as fallback. Documented in CONTEXT-PROTOCOL.md.

- **Daemon SSE event**: `harness.context_meter` with payload `{session_id, slice_id, tokens_used, tokens_budget, pct_remaining, threshold_state}` where `threshold_state ∈ {ok, warning, emergency, over_budget}`. Debounced to max 1/sec (daemon-side) to prevent SSE spam during fast tool-call sequences. Plugin still reports per-tool-call to daemon; daemon throttles outbound to TUI.

### TUI threshold-state surface

- v9 statusline shows context budget percent + `threshold_state` color (green=ok / amber=warning / red=emergency). Color flips on the SSE event.
- v9 sidebar shows persistent token countdown + budget bar.
- One-shot toast on threshold *cross* (ok→warning, warning→emergency, any→over_budget). Toast text names the next harness action ("entering compact-and-rotate at next task boundary").

### Abort controller multiplicity

- Daemon-side: **two independent abort surfaces** (manual + auto). gsd-2's third (branch-summary) is omitted — state has no tree-navigation analog.
- Manual abort cancels in-flight `session.compacting`-triggered compaction (user-initiated `/compact`); auto abort cancels threshold/overflow-driven compaction. Cross-cancel forbidden — user `/compact` cancellation must NOT kill an in-flight auto-compaction.
- `is_compacting` is a derived OR over both controllers (gsd-2 §1 pattern).

### Subagent compaction inheritance

- When a parent Slice session compacts, **in-flight subagents finish independently**. Their structured returns are written to event store via `subagent_complete`. Parent's reinject payload includes those returns as `provides:` blocks. No subagent reinjection; subagents are context-isolated by SUB-04 ("subagents are free context").

### Claude's Discretion

- Exact orjson option flags (`OPT_SORT_KEYS`, `OPT_NAIVE_UTC` vs `OPT_UTC_Z`) — planner picks one, pins in spec.
- Exact wording of `<slice_context>` etc. XML section names — recommendations above; planner may rename for clarity.
- Exact debounce window (1Hz suggested; planner may tune to 2Hz or 0.5Hz based on TUI animation budget).
- TUI statusline color codes (recommended green/amber/red; planner picks hex / ANSI codes that match v9 palette).
- Lossy markdown digest exact section ordering — three tiers fixed but the exact heading wording is planner's call.
- The *complete* enumeration of v40 docs requiring amendment headers — recommended list above; planner walks the v40 spec inventory and adds any missed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 402 scope & requirements
- `.planning/milestones/v41/ROADMAP.md` §Phase 402 — goal, dependencies (none — first v41 phase), success criteria 1–5
- `.planning/milestones/v41/REQUIREMENTS.md` — SLC-01..SLC-07 + CTX-01..CTX-08; planner must add CTX-09 (reactive overflow recovery) per this CONTEXT.md
- `.planning/milestones/v41/HANDOFF.md` — D-1..D-12 locked design decisions

### gsd-2 reference patterns (canonical algorithm source — Phase 402 cites, defers impl to v14)
- `.planning/milestones/v41/compaction-docs-from-gsd-2/compaction-threshold-management.md` — Phase 1 trigger surface (3 controllers, `_overflowRecoveryAttempted` flag, `shouldCompact` signature)
- `.planning/milestones/v41/compaction-docs-from-gsd-2/context-management.md` — Phase 2 reference doc (token accounting §2, decision algorithm §3, summary generation §4, persistence §5, budget computation §6, snapshot §7)
- `.planning/milestones/v41/compaction-docs-from-gsd-2/compaction.ts.md` — full file walkthrough
- `.planning/milestones/v41/compaction-docs-from-gsd-2/budget-computation.md` — pure-function budget engine

### Phase 400 + 401 prior decisions (v40)
- `.planning/milestones/v40/phases/400/400-CONTEXT.md` — D-01..D-19 (ID format, "design"/"run" rename, Step-as-file, same-parent dependency, composite states)
- `.planning/milestones/v40/phases/401/401-CONTEXT.md` — D-401-01..D-401-17 (artifact catalog, projection-vs-authored, immutability, index.json, W-codes)
- `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — Slice tier behavioral definition (target of v41 amendment)
- `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — Step is leaf (target of v41 amendment forward-pointer)
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — existing event taxonomy (Phase 402 adds Slice-stage-boundary events, compaction events)
- `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — cascade rules (target of amendment)
- `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — Pydantic frontmatter models (CompactionSnapshot extends this pattern)

### Project-level constraints
- `.planning/PROJECT.md` — Build/Teach exclusivity, Python 3.12+, opencode primary host, library locks
- `CLAUDE.md` (project) — per-plan SUMMARY.md mandatory, security_enforcement, mode isolation cardinal rule

### Architecture & integration (shipped, reference only)
- `.planning/research/ARCHITECTURE.md` — daemon/worker/plugin trio, event store, mode middleware
- `src/state_core/schema.py` — existing event types, aggregate definitions (CompactionSnapshot extends)
- `src/state_core/projector.py` — CQRS projection engine (the lossy `last-snapshot.md` writer is a new projector handler)
- `src/state_daemon/middleware.py` — mode-enforcement HTTP middleware pattern (threshold-decision middleware follows this shape)
- `src/state_worker/hooks/` — plugin hook handlers (chat.params, tool.execute.after wiring)
- `state-inputs/opencode/packages/plugin/src/index.ts` — opencode plugin hook signatures (chat.params, tool.execute.before/after, session.compacting)

### Downstream consumers (these will read Phase 402 output)
- v14 Build Kernel — implements the Step FSM + verifiers + the deferred compaction algorithm internals
- Phase 403 (Step/Task Decomposition) — consumes the canonical Slice-cycle definition + stepNPLAN.md ↔ stepNN-PLAN.md naming
- Phase 404 (Boolean Proof Gate) — consumes the threshold-action ladder + intervention-tier event schema
- Phase 405 (Subagent Management) — consumes the subagent-compaction-inheritance decision (subagents finish independently)
- Phase 406 (Harness Architecture Rollup) — consumes all of the above

</canonical_refs>

<specifics>
## Specific Ideas

- **gsd-2 is the canonical algorithm reference.** The user explicitly routed the discussion through `compaction-docs-from-gsd-2/` mid-session; that folder is now load-bearing for Phase 402's CONTEXT-PROTOCOL.md "Reference Implementation" section. The four docs in that folder must be cited by name in the spec.

- **Anthropic-XML tagging for the reinject body** is the load-bearing affordance. Anthropic's RLHF-tuned response to XML tagging (`<conversation>`, `<previous-summary>`, etc.) is gsd-2-validated. Pure JSON in prompt bodies degrades instruction-following on every major provider; markdown-only is acceptable but loses Anthropic-specific tuning.

- **Two-layer snapshot persistence (event store + lossy markdown digest)** mirrors gsd-2's two-tier model. The `.state/build/last-snapshot.md` is specifically for the "fresh agent boots in project root, doesn't know session_id yet" case — gsd-2 §7.4 demonstrates auto-injection into chat.params preamble works.

- **Plugin shim stays a thin reporter** (~300 LOC contract from PROJECT.md) — daemon owns intervention decisions. Mirrors v6 mode-enforcement HTTP middleware as the canonical decision point.

- **No state-specific manual `/compact` command.** State listens to opencode's native `/compact` via `session.compacting`. Avoids namespace bloat; manual path is observable, not state-initiated.

- **Reactive overflow recovery is a NEW requirement (CTX-09)** beyond v41 REQUIREMENTS as written. Without it, OAuth/Pro/Max users hitting hard 200K limits would see provider errors surface to the user instead of autonomous recovery. gsd-2's `_overflowRecoveryAttempted` one-shot pattern is the validated recovery shape.

- **v40 wins the naming reconciliation** — `design-slice/research-slice/run-slice/verify-slice` is canonical. The v41 REQUIREMENTS get rewritten in-place to match. The mapping table above is the planner's translation key.

</specifics>

<code_context>
## Existing Code Insights

### Reference only (Phase 402 is design-only — no code lands)

This phase produces architecture specification documents. Shipped code below is reference for understanding existing patterns and integration points the spec must respect.

### Reusable Assets

- `state_core.schema` — `EventEnvelope`, `extra="forbid"` Pydantic convention, deterministic serialization via orjson. `CompactionSnapshot` and `CompactionReinjectCompleted` extend this.
- `state_core.projector` — CQRS handler registration pattern. New handler for the lossy `.state/build/last-snapshot.md` writer follows this shape (subscribes to `compaction.snapshot_taken`, writes the 3-tier digest, enforces ≤2KB byte cap).
- `state_daemon.middleware` (v6) — mode-enforcement HTTP middleware. Threshold-decision middleware mirrors the pattern: read state, decide intervention tier, emit event.
- `state_worker.hooks` (v7) — opencode hook handlers. `tool.execute.after` is where the plugin reads context-meter and posts to daemon.
- `state_core.scheduler` (v5) — the cross-session linkage event chain (`prior_session_id → new_session_id`) is replayable per the scheduler's event-driven model.
- v9 statusline + sidebar plugin TUI extensions — context-meter SSE consumer.

### Established Patterns

- `extra="forbid"` on every Pydantic model (v1–v11 convention).
- Event-sourced: SQLite authoritative + SyncEvent mirror; projector rebuilds from events.
- Daemon HTTP middleware as canonical mode/decision gate (v6).
- Captured-header golden suites (v2 stealth pattern) — translates here as: snapshot Pydantic round-trip golden test (orjson serialize → deserialize → equal) at v14 implementation time.
- mode isolation grep gate: `state_build.harness.*` MUST NOT import `state_teach.*`. v41 is Build-only; the harness lives under `state_build/`.

### Integration Points

- Plugin's `tool.execute.after` hook posts context-meter readings to daemon HTTP endpoint (new in v14).
- Daemon's middleware decides intervention tier and emits `harness_intervention` events (new in v14, schema defined in Phase 402).
- Projector subscribes to `compaction.snapshot_taken` and writes `.state/build/last-snapshot.md` as a side-effect projection.
- Daemon SSE bus emits `harness.context_meter` events; v9 statusline + sidebar subscribe.
- Compaction events live in the same event store as state.* events; replay rebuilds harness state alongside Slice/Step state.

</code_context>

<deferred>
## Deferred Ideas

- **Compaction algorithm internals** (cut-point detection, summary prompt templates, single-pass-vs-chunked dispatch, degenerate-summary R6 fallback, file-operation tail) — v14 Build Kernel.
- **Atomic snapshot file write** (temp+rename) — currently NOT atomic, mirrors gsd-2 §7.3 honest scoping. Atomic write is a v44 (Rust DB rewrite) follow-up.
- **Identifier-corruption recovery** (event store row malformed; new session can't read prior IDs) — fail-safe behavior is "spawn new Slice from current state, log corruption event, surface human gate." Detailed protocol deferred to v14.
- **Slice-resume-after-N-days flow** (user returns days later; daemon was off; how do they re-attach to a Slice mid-flight?) — out of Phase 402 scope; design owned by v15 Build Core Commands (`state-resume-slice`).
- **Snapshot file rotation policy** (`last-snapshot.md` is overwritten every compaction; do we keep a `last-snapshot.{N}.md` history?) — out of scope; if needed, deferred to v15 or post-v17.
- **Subagent compaction events** (subagents emit their own per-subagent summaries when they themselves grow large) — out of scope for Phase 402; subagents are SUB-04 "free context" and finish independently. Revisit if subagent context-pressure becomes an observed failure mode post-v17.
- **Per-provider context-meter quirks** (Gemini reports tokens differently from Anthropic; non-Anthropic providers may not surface `usage.cache_read_input_tokens`) — gsd-2 §2.5 ContextUsageEstimate accommodates this; v14 implementation handles per-provider parity. Phase 402 documents the contract; v14 maps providers.
- **Manual `/compact` telemetry** — observable via `compaction.snapshot_taken` event with `trigger="manual"` + `from_hook=False` (gsd-2's manual path doesn't emit `auto_compaction_*`). Sufficient for v1; richer telemetry deferred.

</deferred>

---

*Phase: 402-slice-cycle-context-window-spec*
*Context gathered: 2026-05-08*
