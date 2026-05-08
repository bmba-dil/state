# Pattern: Compaction Threshold Management

**Layer:** Core Runtime (M1)
**Source:** `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:90-95` (`thresholdPercent`); `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:200` (`shouldCompact`); `gsd-2/packages/pi-coding-agent/src/core/compaction-orchestrator.ts:47-80` (three abort controllers, `isCompacting`, `_overflowRecoveryAttempted`)
**Discovered in:** Phase 1 (CORE-01)
**Related reference:** `kb/core/agent-lifecycle.md` §5 (Compaction Triggering)

## What it does

Coordinates *when* to compact a context window using a dual-mode trigger (fractional `thresholdPercent` OR absolute `reserveTokens`), with three independent abort surfaces (manual/auto/branch) and a one-shot reactive flag (`_overflowRecoveryAttempted`) preventing infinite compact-retry loops on a single user turn.

Phase 1 documents the trigger surface only. The compaction *algorithm* (summary generation, preservation rules, branch summarization) is owned by Phase 2.

## Why it works that way

Three forces shape this pattern:

1. **Two policies for "when is the context too full"** — Different consumers want to express thresholds differently. The GSD orchestrator extension wants "compact when 80% full" (fraction). Internal agent code may know an exact reserve budget ("always keep 8K tokens free"). Supporting both with a single `shouldCompact()` function avoids divergent code paths.
2. **Concurrent compaction concerns must not collide** — A user can manually trigger `/compact` *while* a threshold-driven auto-compaction is running, *while* a branch-summary compaction is firing for tree navigation. Sharing one abort controller would force these unrelated operations into a single cancel surface; instead, three independent controllers let each be cancelled without affecting the others. The aggregate `isCompacting` getter (any controller active) is a derived view.
3. **Provider overflow is reactive, not predictive** — The threshold path predicts overflow (compact before sending). The overflow path reacts (compact because the provider rejected the request). Both must exist: prediction is cheaper but not all overflow is predictable (image-token expansion, system-prompt growth). The `_overflowRecoveryAttempted` flag prevents the reactive path from looping indefinitely on a single turn.

Alternatives rejected:
- **Single threshold-percent only** — would force all consumers to express budgets as fractions; awkward for absolute reserves.
- **Single abort controller** — would force `/compact` cancellation to also cancel branch summary, surprising the user.
- **No reactive recovery** — would punt all context overflow to the user; degrades autonomous-mode UX.

## Abstract algorithm

```text
State (per session):
  manualAbort: AbortController | null
  autoAbort: AbortController | null
  branchAbort: AbortController | null
  overflowRecoveryAttempted: bool        // one-shot per user turn

isCompacting() -> bool:
  return any(controller.signal.aborted == false and controller.active for controller in [manualAbort, autoAbort, branchAbort])

shouldCompact(contextTokens, contextWindow, settings) -> bool:
  if settings.thresholdPercent != null:
    return (contextTokens / contextWindow) >= settings.thresholdPercent
  else:
    return (contextWindow - contextTokens) <= settings.reserveTokens

onIncomingUserMessage():
  overflowRecoveryAttempted = false       // reset one-shot
  if shouldCompact(...): triggerAuto(reason="threshold")

onProviderOverflowError():
  if overflowRecoveryAttempted: surface_error_to_caller()
  else:
    overflowRecoveryAttempted = true
    triggerAuto(reason="overflow")
    retry_provider_call()

onTurnEnd():
  overflowRecoveryAttempted = false       // also reset on success
```

## Python equivalents

```python
import asyncio
from dataclasses import dataclass
from typing import Optional

@dataclass
class CompactionSettings:
    threshold_percent: Optional[float] = None
    reserve_tokens: int = 8000

class CompactionOrchestrator:
    def __init__(self) -> None:
        self._manual_event = asyncio.Event()        # set = abort
        self._auto_event = asyncio.Event()
        self._branch_event = asyncio.Event()
        self._overflow_recovery_attempted = False

    @property
    def is_compacting(self) -> bool:
        return any(
            getattr(self, attr).is_set() is False and getattr(self, f"_{name}_active", False)
            for attr, name in [("_manual_event", "manual"), ("_auto_event", "auto"), ("_branch_event", "branch")]
        )

def should_compact(context_tokens: int, context_window: int, settings: CompactionSettings) -> bool:
    if settings.threshold_percent is not None:
        return (context_tokens / context_window) >= settings.threshold_percent
    return (context_window - context_tokens) <= settings.reserve_tokens
```

Key Python constructs:
- `asyncio.Event` — replaces `AbortController`. Set to abort, clear to reset.
- `dataclass` — `CompactionSettings`, mirrors the TypeScript struct.
- Optional `functools.cached_property` — only if `is_compacting` becomes a hot path; usually a simple property suffices.

## Variations / pitfalls

- **Threshold-percent off-by-one** — `>=` vs. `>` matters when tokens exactly equal the threshold. The codebase uses `>=`; reimplementations should match.
- **Race between `onIncomingUserMessage` reset and in-flight overflow recovery** — if the user submits a new message *while* overflow recovery is mid-retry, the reset can clear the flag and allow infinite recursion. The TypeScript code coordinates via the abort controllers; a Python port must do the same.
- **Three controllers ≠ three booleans** — using booleans loses the "ongoing operation" semantics; AbortController / asyncio.Event correctly model in-flight cancellation.
- **`isCompacting` is a derived view** — never set it directly. Always derive from controller states.

## Cross-references

- Reference doc: `kb/core/agent-lifecycle.md` §5 (Compaction Triggering), §5.1-5.6
- Reference doc (Phase 2): [`kb/core/context-management.md`](../core/context-management.md) — owns the compaction *algorithm* this pattern triggers (§3 decision algorithm, §4 summary generation)
- Sibling pattern: `kb/patterns/event-emitter-session.md` — orchestrator emits `auto_compaction_start` / `auto_compaction_end` on Bus A
- Sibling pattern (Phase 2): [`auto-compaction-trigger.md`](auto-compaction-trigger.md) — the decision algorithm that fires once thresholds say "compact". This pattern documented the trigger surface; that pattern documents the decision flow.
- Sibling pattern (Phase 2): [`branch-summary-abort.md`](branch-summary-abort.md) — formalizes the three-AbortController multiplicity invariant named in this pattern's `## What it does`.
- Sibling pattern (Phase 2): [`overflow-recovery-one-shot.md`](overflow-recovery-one-shot.md) — formalizes the `_overflowRecoveryAttempted` flag named in this pattern's `## What it does`.
