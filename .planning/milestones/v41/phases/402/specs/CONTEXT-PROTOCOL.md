# Context Protocol (Canonical, v41)

Phase: 402
Status: Canonical (v41)
Requirements covered: CTX-01..09
Reference algorithm: `.planning/milestones/v41/compaction-docs-from-gsd-2/*` (defers algorithm internals to v14 Build Kernel)

Build-mode only. `state.build.harness.*` MUST NOT import `state.teach.*`. Cardinal rule per PROJECT.md.

## Overview

The harness — not the agent — controls what is in context throughout a Slice's run-slice stage. This document defines the canonical trigger surface (when context-management actions fire), the canonical snapshot schema (what is captured), and the canonical reinject payload (how state is rehydrated into a fresh or compacted session). Algorithm internals (cut-point detection, summary-generation prompt templates, single-pass-vs-chunked dispatch, degenerate-summary recovery, file-operation tail extraction) are deferred to the v14 Build Kernel; the canonical algorithm reference is the four gsd-2 docs cited in §13. Phase 402 owns the contract; v14 implements per these patterns.

## 200k Absolute Slice Budget (CTX-01)

The Slice token budget is 200k absolute, regardless of the active model's context-window size (200k or 1M+). plan-slice (the research-slice planning stage in v40 vocabulary, per HANDOFF.md D-3) sizes the Step set so executor work fits within ≤80% of budget (~160k of executor work), leaving headroom for compaction snapshots, reinject payloads, and reactive-overflow recovery. The budget is enforced per-Slice — a Slice may transit through more than one opencode session (manual `/compact` or threshold-driven intra-Slice compaction continues the same `session_id`; Slice-boundary spawn mints a new `session_id`) but the 200k ceiling applies to the cumulative context held by whichever session is active at any moment within the Slice. See REQUIREMENTS.md CTX-01 and HANDOFF.md D-3 for the locked decision.

## Fresh Session Per Slice (CTX-02)

A fresh opencode session is spawned at every Slice boundary. The boundary is the verify-slice → next Slice's design-slice transition (per SLICE-CYCLE.md, the four-stage cycle that defines "Slice boundary"). Spawn protocol:

1. The daemon initiates the spawn after observing `state.slice.verify_completed` for the closing Slice.
2. The daemon mints a new opencode session via opencode HTTP and obtains the new `session_id`.
3. The plugin's `chat.params` hook fires on the first message of the new session and injects the new Slice context as a single system-message string (see §9 for the reinject payload shape).
4. The injected payload includes parent Phase intentions, non-negotiables and crits from the parent Phase, the current Slice's scope (DESIGN.md `<domain>` + `<canonical_refs>` excerpts), upstream Step `provides:` blocks for resolved dependencies, and the active worktree path.
5. The new session emits `compaction.reinject_completed` (see §10) once `chat.params` acknowledges receipt; this event chains the new `session_id` to the prior `session_id` for replay and forensics.

Identifier reuse rule: each new Slice receives a fresh `slice_id`. The same `slice_id` is reused only on Slice-revert per v40 TIER-SLICE.md `state.slice.replanned` event semantics — that path explicitly preserves the original `slice_id` so historical events remain attributable. Cite HANDOFF.md D-2 (fresh session per Slice; daemon initiates spawn).

## Intra-Slice Compaction (CTX-03)

Intra-Slice context pressure is handled inside the same opencode session (no new `session_id`); the harness snapshots state, strips stale content, and reinjects compact form. The same `session_id` continues across the compaction boundary. Two trigger paths:

- **opencode-native trigger** — opencode's `session.compacting` hook fires when the user invokes opencode's built-in `/compact` slash command. State observes this hook and emits `compaction.snapshot_taken` with `trigger="manual"` (and `from_hook=False` per the gsd-2 manual path convention). State does NOT introduce its own slash command for manual compaction; state observes opencode's native command, never initiates the manual path.
- **daemon-initiated trigger** — the daemon's threshold/overflow paths (see §7) compute that compaction is needed and request a snapshot+reinject through the worker. The daemon emits `compaction.snapshot_taken` with `trigger="threshold"` or `trigger="overflow"`.

State adopts a two-controller subset of the gsd-2 three-controller design (per gsd-2 `compaction-threshold-management.md` "Why it works that way" §2 abort multiplicity). Controllers: **manual** (cancels in-flight `session.compacting`-triggered compaction) and **auto** (cancels threshold/overflow-driven compaction). gsd-2's third "branch" controller is omitted because state has no tree-navigation analog. The derived predicate is:

```
is_compacting = manual_active OR auto_active
```

Cross-cancel is forbidden: a user `/compact` cancellation MUST NOT kill an in-flight auto-compaction, and vice versa. The two controllers are independent abort surfaces; the `is_compacting` predicate is read-only and never set directly. This mirrors gsd-2 §1's pattern verbatim with the third controller dropped.

## Threshold Action Table (CTX-04 + CTX-09)

| Threshold | Trigger | Hook | Action | Event Emitted |
|-----------|---------|------|--------|---------------|
| **Emergency (≤25% remaining)** | Plugin `tool.execute.after` reports threshold cross to daemon over HTTP after a tool call returns | `tool.execute.after` | Daemon waits for the current `<task>` block to complete (no mid-tool snapshots; no immediate hard interrupt), then snapshots and rotates at the next task boundary. The current task finishes naturally; the next task starts in a freshly compacted session. | `compaction.snapshot_taken` (trigger=`threshold`) |
| **Warning (≤35% remaining)** | Plugin `tool.execute.before` blocks the start of the next `<task>` in the same session | `tool.execute.before` | Daemon flags `next-task-blocked` state. The executor finishes the current `<task>` (cleanup / last `<verify>` / summary fragment). Any Write/Edit aimed at the next task is rejected with a `compact-and-rotate` advisory. Reuses HRN-04 tier-2 intervention. | `harness_intervention` (tier=`tool-block`, trigger_reason=`warning_threshold`) |
| **Slice boundary** | verify-slice closes (per SLICE-CYCLE.md) and the daemon spawns a fresh session via opencode HTTP | `chat.params` (on first message of new session) | Daemon mints new session, plugin's `chat.params` hook reinjects new Slice context (see §9). Mandatory regardless of remaining budget. | `state.slice.verify_completed` (closing Slice) followed by `state.slice.created` (new Slice); `compaction.reinject_completed` chains the prior→new session IDs |
| **Reactive overflow (CTX-09)** | Provider rejects request with context-overflow error mid-turn | (provider error → daemon middleware) | Harness mirrors the gsd-2 `_overflowRecoveryAttempted` one-shot pattern. Six-step flow: (1) strip the failing assistant turn from context, (2) force-compact (snapshot+reinject), bypassing the percent-threshold check, (3) retry the provider call once, (4) set `_overflow_recovery_attempted` flag on the active session, (5) reset the flag on next user/agent message OR successful turn, (6) if the flag is already set when a second overflow fires within the same user turn, surface the error to the user (no infinite loop). | `compaction.snapshot_taken` (trigger=`overflow`) |

### Threshold trigger source — plugin reads + daemon decides

The plugin's `tool.execute.after` hook reads `usage.input_tokens + usage.cache_read_input_tokens` from the tool response (gsd-2 §2.2 `calculateContextTokens` pattern) and posts `{session_id, tokens_used, tokens_budget}` to the daemon over HTTP after every tool call. The daemon's middleware consults harness state and decides which intervention tier to fire:

- **advisory inject** — soft warning at threshold cross (informational TUI toast; no behavior change yet).
- **tool-block** — `tool.execute.before` rejects writes-to-next-task at warning threshold (HRN-04 tier-2).
- **clear+reinject** — full snapshot+reinject at emergency threshold or overflow.
- **human gate** — surfaces via opencode `question` tool when the gate-strike escalation ladder hits 6 (PRF-06 territory; cited here for completeness).

The plugin shim stays a thin reporter (preserves the ~300 LOC contract from PROJECT.md). All decision logic lives in the daemon's middleware — consistent with the v6 mode-enforcement HTTP middleware as the canonical decision point.

### Per-Slice threshold override

Slice frontmatter MAY narrow (move thresholds *earlier* / make stricter) but never widen. The override field on Slice frontmatter:

```yaml
compaction:
  emergency_pct: int   # ≥ 25 (default); must be greater than or equal to 25
  warning_pct: int     # ≥ 35 (default); must be greater than or equal to 35
```

The daemon validates the override at Slice-load time and rejects values below the defaults (a Slice cannot relax the global limits). This mirrors the SUB-03 narrow-only pattern from v41 REQUIREMENTS — local overrides may make the harness more conservative but never less.

### Manual /compact telemetry

State observes opencode's native `/compact` via `session.compacting` and emits `compaction.snapshot_taken` with `trigger="manual"`, `from_hook=False`. This is the v1 milestone-label telemetry shape; richer telemetry (per-section size accounting, summary-quality scoring, manual-vs-auto outcome comparison) is deferred per 402-CONTEXT.md `<deferred>` "Manual /compact telemetry". The v1 milestone deliberately keeps the manual path observable-but-thin so the auto path (threshold + overflow) gets the engineering attention.

## Compaction Snapshot Schema (CTX-05)

The compaction snapshot is a structured artifact (Pydantic model serialized via orjson, written to the event store), not a markdown blob. Two persistence layers coexist: Layer A is authoritative (event-store row); Layer B is a lossy markdown digest used for cross-session orientation.

### Layer A — Authoritative (Pydantic + orjson + event store)

The authoritative snapshot is a `CompactionSnapshot` Pydantic model. Every field is sourced verbatim from 402-CONTEXT.md `<decisions>` "Compaction snapshot — two-layer persistence":

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

Field-by-field commentary:

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `slice_id` | `str` | hot session state (transported via `chat.params.metadata` after spawn) | survives session-spawn boundary per CTX-07 |
| `step_id` | `str` | hot session state | survives session-spawn boundary per CTX-07 |
| `task_id` | `str \| None` | hot session state; `None` between tasks | survives session-spawn boundary per CTX-07 |
| `session_id` | `str` | opencode session being compacted | the session whose context is being snapshotted |
| `prior_session_id` | `str \| None` | event-store linkage | set on Slice-boundary spawn (`compaction.reinject_completed` chains the linkage); `None` for intra-Slice compaction |
| `summary` | `str` (≤8KB) | summary-generation pass (algorithm internals deferred to v14) | verbatim markdown digest; not parsed by the harness |
| `first_kept_entry_id` | `str` | event-store row id | first non-summarized entry; everything before this row is replaced by `summary` |
| `tokens_before` | `int` | plugin's `tool.execute.after` reading at trigger time | telemetry only; no decision logic depends on it |
| `trigger` | `Literal["manual", "threshold", "overflow"]` | daemon middleware decision | matches the threshold action table rows |
| `from_hook` | `bool` | controller path | `True` when `session.compacting` initiated; `False` when daemon-initiated |
| `worktree_path` | `Path` | Slice metadata | absolute path on disk (per-Slice worktree per v4 milestone artifact) |
| `provides_blocks` | `list[ProvidesBlock]` | upstream Step `SUMMARY.md` `provides:` parsing | one entry per resolved upstream dep |
| `active_plan_path` | `Path` | current Step | absolute path to active `stepNPLAN.md` |
| `current_task_pointer` | `TaskPointer \| None` | hot session state | `None` between tasks |
| `last_verify_result` | `VerifyResult \| None` | most recent task `<verify>` output | `None` if no verify has run yet in current Step |
| `created_at` | `datetime` | UTC, ISO-8601 | deterministic — set by daemon at snapshot time |

### Round-trip example

orjson is the canonical serializer. The exact flag combination is pinned so v14 implementations produce byte-identical round-trips:

```python
import orjson

# Serialize
payload: bytes = orjson.dumps(
    snapshot.model_dump(mode="json"),
    option=orjson.OPT_SORT_KEYS | orjson.OPT_NAIVE_UTC,
)

# Deserialize
restored = CompactionSnapshot.model_validate_json(payload)
assert restored == snapshot
```

The flag combination `OPT_SORT_KEYS | OPT_NAIVE_UTC` is the canonical pin. `OPT_SORT_KEYS` makes byte-order deterministic across Python interpreters; `OPT_NAIVE_UTC` serializes datetimes as naive UTC ISO-8601 strings (matches the deterministic-replay rule from PROJECT.md — no `datetime.now()` quirks across timezones). v14 implementations MUST use this same flag combination.

### Layer B — Lossy markdown digest (`.state/build/last-snapshot.md`)

A second, lossy projection writes to `<projectRoot>/.state/build/last-snapshot.md` on every `compaction.snapshot_taken` event. This mirrors gsd-2's `compaction-snapshot.ts` model (per-project, fixed path).

- **Path:** `<projectRoot>/.state/build/last-snapshot.md` — a fixed location relative to the project root, NOT per-Slice and NOT per-session. Discoverable by a fresh agent that knows only `process.cwd()`.
- **Byte cap:** ≤2KB UTF-8, enforced in memory before write.
- **Three priority tiers** in fixed order (the projector emits these exact heading wordings):
  - `## Active context` — single line: `Active: arc-N / stage-N / slice-N / step-N — <title>`.
  - `## Top project memories` — up to 6 entries.
  - `## Recent run history` — up to 5 most-recent run-slice executions.
- **Use case:** cross-session orientation when a fresh agent boots without knowing `session_id` (it knows `process.cwd()`); reads `.state/build/last-snapshot.md` from there before the daemon hand-off completes.
- **Writer:** the daemon's projector handler subscribed to `compaction.snapshot_taken` writes this file as a side-effect projection (mirrors the v6 mode-enforcement projection pattern).
- **NOT atomic in the v1 milestone.** Byte cap is enforced in memory before write, but no temp+rename. Documented as a known limitation; atomic-write follow-up deferred to v44 (Rust DB rewrite). This honest scoping mirrors gsd-2 §7.3.

### Helper-type sketches

The `CompactionSnapshot` model references three helper types. Full helper-type schemas are owned by Phase 403 (Step/Task Decomposition) and Phase 404 (Boolean Proof Gate); this doc lists the minimum shape needed to validate `CompactionSnapshot`.

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

class ProvidesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_step_id: str            # source Step that produced this block
    provides: dict[str, str]     # key/value pairs from SUMMARY.md `provides:` block

class TaskPointer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_index: int              # 0-based index into the Step's <tasks> list
    task_name: str               # the <name> from the active <task> block
    started_at: datetime         # UTC, ISO-8601 — when this task entered active state

class VerifyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["pass", "fail", "skipped"]
    details: str                 # captured stdout/stderr or rationale (≤4KB)
    verified_at: datetime        # UTC, ISO-8601
```

## Reinject Payload (CTX-06)

The reinject payload is hybrid: an LLM-facing XML body + a programmatic Pydantic JSON metadata block, both transported through opencode's `chat.params` hook on the new (or compacted) session.

### Body (LLM-facing) — XML-tagged markdown

The body is a single system-message string, passed via `chat.params`. Sections (Anthropic-best-practice tagging):

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

Anthropic's RLHF tuning is the load-bearing reason for XML tagging — pure JSON in prompt bodies degrades instruction-following on every major provider. Markdown-header fallback is acceptable for XML-hostile providers (any provider that misparses XML); the harness emits markdown headers in that path. v14 picks per-provider via the litellm provider taxonomy.

### Metadata (programmatic) — Pydantic JSON via chat.params metadata field

The same `CompactionSnapshot` instance is serialized as JSON via orjson (using the flag combination pinned in §8) and attached to the `chat.params.metadata` field for daemon, projector, SSE consumers, and any other middleware that needs structured access. The Pydantic model is the single source of truth; the XML body is a rendered view derived from the same instance. Drift between body and metadata is a defect.

### Content-stripping reference

The `<active_plan>` content is content-stripped per PAP-06 (Phase 403 owns PAP-06; this doc references the rule). PAP-06 strips upstream-only sections (e.g., research-stage reasoning meta) at injection time to save tokens, while preserving the audit-logged original on disk. The stripped body is what reaches the LLM; the audit trail keeps the un-stripped form.

## Identifier Survival Contract (CTX-07)

`task_id`, `step_id`, and `slice_id` survive both intra-Slice compaction and Slice-boundary session spawn. Three layers carry the identifiers across boundaries.

### Canonical storage

The SQLite event store at `.state/events.sqlite` is the authoritative carrier (survives daemon restart). The `compaction.snapshot_taken` event row carries `slice_id`, `step_id`, `task_id`, `session_id`, and `prior_session_id`. Any consumer that needs the identifiers can read them from the event store by filtering on `compaction.snapshot_taken` events for the active Slice.

### Transport across session-spawn boundary

When the daemon mints a new session at Slice boundary:

1. Daemon reads the prior `slice_id`, `step_id`, `task_id` from the event store (most recent `compaction.snapshot_taken` row for the closing Slice, or directly from Slice/Step state if no compaction has fired yet).
2. Daemon attaches the IDs into `chat.params.metadata` for the new session's first hook fire.
3. The plugin's `chat.message` hook (or first `tool.execute.before` fire) reads `chat.params.metadata` and writes the IDs to plugin-local hot state.
4. From then on, all plugin hooks have the IDs available in hot state for the duration of the session.

### Reinjection event — `compaction.reinject_completed`

Once the new session's `chat.params` hook acknowledges receipt, the daemon emits `compaction.reinject_completed`:

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict

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

This event chains the prior session to the new session through `prior_session_id → new_session_id`. Replay can reconstruct the full Slice timeline by walking the chain forward from the Slice's first session through every compaction and Slice-boundary spawn.

### Subagent compaction inheritance

When a parent Slice session compacts, in-flight subagents finish independently. Their structured returns are written to the event store via `subagent_complete`. The parent's reinject payload includes those returns as `<provides>` blocks (see §9 `<upstream_provides>`). No subagent reinjection occurs — subagents are SUB-04 free context (per v41 REQUIREMENTS), context-isolated by design. If subagent context-pressure becomes an observed failure mode post-v17, per-subagent compaction events will be reconsidered (see 402-CONTEXT.md `<deferred>` "Subagent compaction events").

## Context-Meter Wiring (CTX-08)

The context meter is the harness's read path for token-budget state. It is wired plugin → daemon → SSE → TUI, with the plugin staying a thin reporter.

### Plugin hook — `tool.execute.after`

The plugin's `tool.execute.after` hook fires after every tool call. It reads `usage.input_tokens + usage.cache_read_input_tokens` from the tool response (gsd-2 §2.2 `calculateContextTokens` pattern). On every fire it posts `{session_id, tokens_used, tokens_budget}` to the daemon over HTTP. The plugin holds no decision logic — it is a sensor only.

Note on auth-header isolation: the meter reads `usage` fields from tool-response payloads only; it never inspects auth headers. Anthropic OAuth stealth headers stay isolated to the auth subsystem per the cardinal rule "OAuth traffic NEVER routes through litellm" — the context meter has no business touching auth state.

### Token-counting fallback

If `usage` is absent (error turn / non-Anthropic provider that doesn't surface `usage.cache_read_input_tokens`), the plugin uses gsd-2 §2.1 `chars/4` heuristic via `estimateContextTokens`. The heuristic is imprecise (±20-40% from real tokenizers depending on language and code density); the imprecision is accepted as a documented limitation. The fallback is engaged only on error-turn or provider-doesn't-surface-usage paths; the success path always uses the authoritative `usage` count. Per-provider quirks (Gemini reports tokens differently from Anthropic) are mapped at v14 implementation per gsd-2 §2.5 `ContextUsageEstimate`; Phase 402 documents the contract, v14 maps providers.

### Daemon SSE event — `harness.context_meter`

The daemon emits an SSE event with payload:

```
{
  session_id: str,
  slice_id: str,
  tokens_used: int,
  tokens_budget: int,
  pct_remaining: float,
  threshold_state: Literal["ok", "warning", "emergency", "over_budget"]
}
```

The event is debounced to a maximum of 1/sec daemon-side to prevent SSE spam during fast tool-call sequences. The plugin still reports per-tool-call to the daemon; the daemon throttles outbound to TUI consumers. Debounce window: 1Hz suggested; v14 may tune to 2Hz or 0.5Hz based on TUI animation budget per the planner-discretion note in 402-CONTEXT.md.

### TUI threshold-state surface

The v9 TUI bundle consumes `harness.context_meter` events:

- **statusline** — shows context budget percent + `threshold_state` color (green=ok / amber=warning / red=emergency). Color flips on each SSE event.
- **sidebar** — shows persistent token countdown + budget bar.
- **toast** — one-shot toast on threshold *cross* (ok→warning, warning→emergency, any→over_budget). Toast text names the next harness action ("entering compact-and-rotate at next task boundary").

The exact hex / ANSI codes match the v9 palette (planner-discretion per 402-CONTEXT.md); cross-color choices follow the standard green/amber/red traffic-light convention.

## Reactive Overflow Recovery (CTX-09)

Reactive overflow recovery is the harness's last line of defense when the provider rejects a request with a context-overflow error mid-turn. Reiterating the six-step one-shot pattern from §7 in dedicated form so v14 implementers see the algorithm in isolation.

### Trigger

The provider rejects a chat-completion request with a context-overflow error (HTTP 4xx with provider-specific overflow code; litellm normalizes the error class). The error fires mid-turn — after the user message has been sent but before a successful assistant turn closes. The threshold path predicts overflow (compact before sending); the overflow path reacts (compact because the provider rejected the request). Both must exist: prediction is cheaper but not all overflow is predictable (image-token expansion, system-prompt growth, runaway tool output).

### One-shot flow

The harness mirrors gsd-2's `_overflowRecoveryAttempted` one-shot pattern. Six steps verbatim from 402-CONTEXT.md `<decisions>` "Reactive overflow recovery":

1. **Strip the failing assistant turn from the context.** The half-formed turn that triggered the overflow is removed; subsequent re-invocation must not see it.
2. **Force-compact (snapshot+reinject), bypassing the percent-threshold check.** The threshold percent check is irrelevant — by definition the request just overflowed; the harness compacts unconditionally.
3. **Retry the provider call once.** Single retry. The retry uses the freshly compacted context (`summary` replacing the pre-`first_kept_entry_id` history).
4. **Set `_overflow_recovery_attempted` flag on the active session.** This flag is the one-shot guard.
5. **Reset the flag on next user/agent message OR successful turn.** Either path clears the flag — a successful turn means the recovery worked; a new user message means the user implicitly forgave the failure and is moving on.
6. **If `_overflow_recovery_attempted` is already set when a second overflow fires within the same user turn, surface the error to the user (no infinite loop).** The escape hatch — the harness refuses to enter an unbounded compact-retry-fail-compact-retry-fail loop on a single user turn.

The flag is per-session (lives in plugin hot state, mirrored to daemon for replay). Cross-cancel rules apply: a manual `/compact` that fires while overflow recovery is mid-retry MUST NOT clear `_overflow_recovery_attempted` (cross-cancel forbidden per §6).

### Cross-reference to gsd-2

The canonical algorithm reference is gsd-2 `compaction-threshold-management.md` §"Abstract algorithm" `onProviderOverflowError()` block. State's implementation is a subset: state has two abort controllers (manual + auto) where gsd-2 has three; state's overflow path uses the auto controller and the `_overflow_recovery_attempted` flag verbatim.

## Reference Implementation (deferred to v14)

Algorithm internals are deferred to v14 Build Kernel. The four canonical reference docs (relative paths under `.planning/milestones/v41/compaction-docs-from-gsd-2/`):

- `compaction-threshold-management.md` — three-controller pattern + `_overflowRecoveryAttempted` flag (state uses two controllers — manual + auto — and drops the third "branch" controller). Owns the `shouldCompact` signature, the `onProviderOverflowError()` recovery flow, and the `isCompacting` derived predicate.
- `context-management.md` — token accounting (§2 `calculateContextTokens` / `estimateContextTokens` / `chars/4` fallback), decision algorithm (§3 four-stage branch in `checkCompaction`), summary generation (§4 single-pass-vs-chunked dispatch + prompt templates), persistence (§5 event-store row shape), budget computation (§6 reserve-tokens vs threshold-percent dual-mode), snapshot persistence (§7 the lossy markdown projection), state diagram (§8 trigger-to-event sequence).
- `compaction.ts.md` — full file walkthrough of the canonical `compaction.ts` reference. Cut-point detection, summary-generation prompt templates, file-operation tail extraction, degenerate-summary R6 fallback all live here.
- `budget-computation.md` — pure-function budget engine. Reserve-tokens-vs-threshold-percent dual-mode, off-by-one rules (`>=` vs `>`), per-provider context-window mapping.

Explicit deferral list (Phase 402 does NOT own):

- Cut-point detection algorithm — choosing where in the conversation to slice for summarization.
- Summary-generation prompt templates — `SUMMARIZATION_PROMPT`, `UPDATE_SUMMARIZATION_PROMPT`, `TURN_PREFIX_SUMMARIZATION_PROMPT`.
- Single-pass-vs-chunked dispatch — how the harness decides whether to summarize the whole pre-cut history in one pass or in chunks.
- Degenerate-summary R6 fallback — what happens when the summary itself comes back malformed.
- File-operation tail extraction — preserving the most recent file ops when the rest of history collapses to summary.

v14 Build Kernel implements per these docs. Phase 402 keeps the design-only framing without losing the reference trail.

The deferral boundary is deliberate. Phase 402 owns four tightly scoped contracts: (1) when compaction fires (the trigger surface in §7), (2) what gets captured (the `CompactionSnapshot` schema in §8), (3) how it gets delivered back to the model (the reinject payload in §9), and (4) what survives across session boundaries (the identifier-survival contract in §10). Algorithm internals (cut-point detection, summary-prompt templates, single-pass-vs-chunked dispatch, degenerate-summary recovery, file-operation tail extraction) are tightly coupled to the active model's behavior — Anthropic's summarization quality differs from Gemini's, which differs from GPT's; pinning algorithmic choices in a design doc would force premature model-specific commitments. v14 owns those choices because v14 ships the runtime that observes per-model behavior and tunes accordingly.

## Requirements Coverage

| REQ-ID | Section | Notes |
|--------|---------|-------|
| CTX-01 | §4 200k Absolute Slice Budget | absolute 200k regardless of model context-window size; ≤80% sized at planning |
| CTX-02 | §5 Fresh Session Per Slice | daemon-initiated spawn at Slice boundary; `chat.params` reinjects new context |
| CTX-03 | §6 Intra-Slice Compaction | same `session_id` continues; two-controller (manual + auto) abort surface |
| CTX-04 | §7 Threshold Action Table | four-row table: emergency / warning / slice-boundary / overflow |
| CTX-05 | §8 Compaction Snapshot Schema | `CompactionSnapshot` Pydantic model with `extra="forbid"`; orjson round-trip; lossy Layer-B digest |
| CTX-06 | §9 Reinject Payload | hybrid XML body + Pydantic JSON metadata via `chat.params` |
| CTX-07 | §10 Identifier Survival Contract | event-store carrier; `chat.params.metadata` transport; `compaction.reinject_completed` chains sessions |
| CTX-08 | §11 Context-Meter Wiring | plugin `tool.execute.after` reads usage; daemon SSE `harness.context_meter`; v9 TUI surface |
| CTX-09 | §12 Reactive Overflow Recovery | gsd-2 `_overflowRecoveryAttempted` one-shot pattern; six-step flow |

## Cross-References

- **Sibling spec doc** — `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` (defines the four-stage Slice cycle; the verify-slice → next design-slice transition is the canonical "Slice boundary" referenced throughout this doc).
- **v40 EVENT-TAXONOMY.md** — `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` (existing event taxonomy; Plan 03 of Phase 402 adds the `compaction.*` and `harness_intervention` event rows in a `## v41 Amendment` block).
- **v40 FRONTMATTER-SCHEMAS.md** — `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` (Pydantic frontmatter pattern; `extra="forbid"` convention reused for `CompactionSnapshot` and `CompactionReinjectCompleted`).
- **gsd-2 reference docs** (canonical algorithm source — Phase 402 cites, v14 implements):
  - `.planning/milestones/v41/compaction-docs-from-gsd-2/compaction-threshold-management.md`
  - `.planning/milestones/v41/compaction-docs-from-gsd-2/context-management.md`
  - `.planning/milestones/v41/compaction-docs-from-gsd-2/compaction.ts.md`
  - `.planning/milestones/v41/compaction-docs-from-gsd-2/budget-computation.md`
- **v41 REQUIREMENTS** — `.planning/milestones/v41/REQUIREMENTS.md` (CTX-01..08 verbatim; CTX-09 added by Plan 04 of this phase).
- **v41 HANDOFF** — `.planning/milestones/v41/HANDOFF.md` (D-2 fresh-session-per-Slice; D-3 200k absolute budget; D-4 intra-Slice compaction).
- **v41 phase-context** — `.planning/milestones/v41/phases/402/402-CONTEXT.md` `<decisions>` section (every decision in this doc traces verbatim to a `<decisions>` subsection: "Threshold action table", "Compaction snapshot — two-layer persistence", "Reinject payload — hybrid format", "Identifier survival across session-spawn boundaries", "Context-meter wiring", "Abort controller multiplicity", "Subagent compaction inheritance"). Drift between this spec and 402-CONTEXT.md is a defect — 402-CONTEXT.md is the load-bearing source.
- **PROJECT.md cardinal rules** — mode-isolation (`state.build.harness.*` MUST NOT import `state.teach.*`); deterministic event payloads (no `datetime.now()` in handlers); OAuth stealth never routes through litellm (the context-meter §11 explicitly avoids touching auth headers).
