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
