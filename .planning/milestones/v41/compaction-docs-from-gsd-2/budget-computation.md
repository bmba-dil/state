# Pattern: Budget Computation

**Layer:** Core Runtime (M1) — boundary with Workflow Engine (M3)
**Source:** `gsd-2/src/resources/extensions/gsd/context-budget.ts:13-50` (constants, ratios, `TASK_COUNT_TIERS`); `gsd-2/src/resources/extensions/gsd/context-budget.ts:101-116` (`computeBudgets` pure function); `gsd-2/src/resources/extensions/gsd/context-budget.ts:177-205` (`resolveExecutorContextWindow` 3-step fallback); `gsd-2/src/resources/extensions/gsd/context-budget.ts:223-228` (`resolveTaskCountMax`); `gsd-2/src/resources/extensions/gsd/context-budget.ts:230-235` (`resolveEffectiveContextWindow` Claude-Code 200K clamp, issue #4676); `gsd-2/src/resources/extensions/gsd/auto-prompts.ts:53` (`MAX_PREAMBLE_CHARS = 30_000` historical ceiling); `gsd-2/src/resources/extensions/gsd/auto-prompts.ts:187-195` (`capPreamble` consumer)
**Discovered in:** Phase 2 (CORE-02)
**Related reference:** `kb/core/context-management.md` §6 (Budget Computation)

## What it does

A pure function `computeBudgets(windowTokens, provider?)` (context-budget.ts:101-116) derives four character budgets and a task-count range from a single window-token input:

- `summaryBudgetChars` (15% of total chars) — for dependency / prior-task summaries
- `inlineContextBudgetChars` (40% of total chars) — for plans, decisions, code snippets
- `verificationBudgetChars` (10% of total chars) — for verification sections
- `taskCountRange = {min: 2, max: tier-table-lookup}` — parallel-task count for the executor
- `continueThresholdPercent = 70` — fixed constant for continue-here checkpoints

Inputs come from a 3-step fallback resolution chain in `resolveExecutorContextWindow` (context-budget.ts:177-205): (1) `preferences.models.execution → modelRegistry.findModelById → model.contextWindow`; (2) the session-provided `sessionContextWindow`; (3) `DEFAULT_CONTEXT_WINDOW = 200_000`. Each branch passes through `resolveEffectiveContextWindow` (context-budget.ts:230-235), which applies a Claude-Code-specific clamp at 200K (issue #4676) — anything larger is reduced to 200K when the provider is `claude-code`.

The primary direct consumer is `capPreamble` (auto-prompts.ts:187-195), which takes `min(MAX_PREAMBLE_CHARS=30_000, inlineContextBudgetChars)`. The 30K ceiling is historical and predates the ratio system; both protections coexist. Other consumers include `formatExecutorConstraints` (which emits the user-visible "{min}–{max} tasks" block) and a verification-budget consumer that truncates carry-forward content at `inlineContextBudgetChars * 0.4`.

This is the most directly Python-portable subsystem in GSD-2: pure function, no I/O, no global state, deterministic for any input.

## Why it works that way

Five forces shape the engine:

1. **Pure-function purity** — `computeBudgets` reads no global state, performs no I/O, and is deterministic for any `(windowTokens, provider)`. The file's own header (context-budget.ts:5) calls this out explicitly: "All functions are pure or near-pure (DI). No global state, no I/O." This is what makes the engine portable.
2. **Ratio constants over magic numbers** — the 0.15 / 0.40 / 0.10 / 0.70 ratios are exposed as named module-level constants (context-budget.ts:18-36), making policy tuning a one-line change. A future audit can reason about the ratio sums without code-archaeology.
3. **Tiered task-count** — `TASK_COUNT_TIERS` (500K→8, 200K→6, 128K→5, else→3) gives larger context windows more parallel-task headroom while bounding the orchestrator's branching factor for small models. Linear scan from largest threshold downward (context-budget.ts:223-228) — first-match-wins.
4. **Provider-specific char-per-token** — `getCharsPerToken(provider)` (default `4`) allows model-family-specific tokenization heuristics without recomputing ratios. Anthropic's tokenizer differs from OpenAI's; the conversion factor absorbs that.
5. **Historical preamble cap (30K) survives the ratio system** — preamble bloat causes a specific failure mode (model-attention cliff) that the percentage-based budget cannot guard against directly. `capPreamble = min(MAX_PREAMBLE_CHARS, scaledBudget)` keeps both protections: the percentage tightens the cap on small windows; the 30K ceiling holds for large ones.

Alternatives rejected:
- **Single "context budget" number** — different consumers (preamble, summary, verification, inline-context) have wildly different size profiles. One number forces all to the smallest of them.
- **Per-consumer hard-coded values** — couples budget policy to consumer code. The pure function decouples policy (ratios in context-budget.ts) from application (consumers in auto-prompts.ts).
- **Removing the 30K preamble cap as redundant** — it is NOT redundant for windows above the crossover (~75K); the percentage budget grows unboundedly with window size, but the model-attention cliff does not.

## Abstract algorithm

```text
Constants:
  SUMMARY_RATIO         = 0.15
  INLINE_CONTEXT_RATIO  = 0.40
  VERIFICATION_RATIO    = 0.10
  CHARS_PER_TOKEN       = 4
  DEFAULT_CONTEXT_WINDOW = 200_000
  CLAUDE_CODE_EFFECTIVE_WINDOW = 200_000   # issue #4676 clamp
  CONTINUE_THRESHOLD_PERCENT = 70
  TASK_COUNT_MIN = 2
  TASK_COUNT_TIERS = [(500_000, 8), (200_000, 6), (128_000, 5), (0, 3)]
  MAX_PREAMBLE_CHARS = 30_000              # historical ceiling (auto-prompts.ts:53)

computeBudgets(windowTokens, provider=None) -> BudgetAllocation:
  effectiveWindow = windowTokens if windowTokens > 0 else DEFAULT_CONTEXT_WINDOW
  charsPerToken   = getCharsPerToken(provider) if provider else CHARS_PER_TOKEN
  totalChars      = effectiveWindow * charsPerToken
  return BudgetAllocation(
    summaryBudgetChars       = floor(totalChars * SUMMARY_RATIO),
    inlineContextBudgetChars = floor(totalChars * INLINE_CONTEXT_RATIO),
    verificationBudgetChars  = floor(totalChars * VERIFICATION_RATIO),
    continueThresholdPercent = CONTINUE_THRESHOLD_PERCENT,
    taskCountRange           = (TASK_COUNT_MIN, resolveTaskCountMax(effectiveWindow)),
  )

resolveTaskCountMax(window) -> int:
  for (threshold, max_tasks) in TASK_COUNT_TIERS:
    if window >= threshold:
      return max_tasks
  return TASK_COUNT_MIN              # unreachable: tiers end with (0, 3)

resolveEffectiveContextWindow(window, provider) -> int:
  if provider == "claude-code" and window > CLAUDE_CODE_EFFECTIVE_WINDOW:
    return CLAUDE_CODE_EFFECTIVE_WINDOW
  return window

resolveExecutorContextWindow(modelRegistry, prefs, sessionWindow, sessionProvider) -> int:
  # Step 1: prefs.models.execution → registry → contextWindow
  if prefs?.models?.execution:
    model = findModelById(modelRegistry, prefs.models.execution)
    if model: return resolveEffectiveContextWindow(model.contextWindow, model.provider)
  # Step 2: session-provided window
  if sessionWindow > 0:
    return resolveEffectiveContextWindow(sessionWindow, sessionProvider)
  # Step 3: default fallback
  return DEFAULT_CONTEXT_WINDOW

# Consumer (auto-prompts.ts:187-195)
capPreamble(preamble) -> str:
  budget = min(MAX_PREAMBLE_CHARS, computeBudgets(...).inlineContextBudgetChars)
  return truncateAtSectionBoundary(preamble, budget).content
```

### Worked-example math (4 windows)

| `windowTokens` | `totalChars` (×4) | `summaryBudgetChars` (15%) | `inlineContextBudgetChars` (40%) | `verificationBudgetChars` (10%) | `taskCountRange` | `capPreamble` budget = min(30_000, inline) |
|---:|---:|---:|---:|---:|:---:|---:|
| 32_000 | 128_000 | 19_200 | 51_200 | 12_800 | (2, 3) | 30_000 |
| 128_000 | 512_000 | 76_800 | 204_800 | 51_200 | (2, 5) | 30_000 |
| 200_000 | 800_000 | 120_000 | 320_000 | 80_000 | (2, 6) | 30_000 |
| 1_000_000 | 4_000_000 | 600_000 | 1_600_000 | 400_000 | (2, 8) | 30_000 |

**Crossover analysis for `capPreamble`:** `inlineContextBudgetChars = windowTokens * 4 * 0.40 = windowTokens * 1.6`. They cross at `windowTokens = 30_000 / 1.6 = 18_750 tokens`. Below 18.75K windows, the scaled budget tightens the cap (helping small local models — issue #4435). Above 18.75K windows, the historical 30K ceiling holds. All four worked examples are above the crossover, so all show `capPreamble = 30_000`.

## Python equivalents

```python
from dataclasses import dataclass
from typing import Optional, List, Tuple
import math

# ─── Module-level constants (mirror context-budget.ts:18-50) ────────────────
SUMMARY_RATIO = 0.15
INLINE_CONTEXT_RATIO = 0.40
VERIFICATION_RATIO = 0.10
CHARS_PER_TOKEN = 4
DEFAULT_CONTEXT_WINDOW = 200_000
CLAUDE_CODE_EFFECTIVE_WINDOW = 200_000
CONTINUE_THRESHOLD_PERCENT = 70
TASK_COUNT_MIN = 2
TASK_COUNT_TIERS: List[Tuple[int, int]] = [
    (500_000, 8),
    (200_000, 6),
    (128_000, 5),
    (0, 3),
]
MAX_PREAMBLE_CHARS = 30_000  # auto-prompts.ts:53


@dataclass(frozen=True)
class BudgetAllocation:
    summary_budget_chars: int
    inline_context_budget_chars: int
    verification_budget_chars: int
    continue_threshold_percent: int
    task_count_range: Tuple[int, int]   # (min, max)


def get_chars_per_token(provider: Optional[str]) -> int:
    """Provider-specific tokenization factor. Default is 4."""
    # Override per provider if you have measurements
    return CHARS_PER_TOKEN


def resolve_task_count_max(window: int) -> int:
    """Linear scan over TASK_COUNT_TIERS — first match wins."""
    for threshold, max_tasks in TASK_COUNT_TIERS:
        if window >= threshold:
            return max_tasks
    return TASK_COUNT_MIN  # unreachable: tiers end with (0, 3)


def compute_budgets(window_tokens: int, provider: Optional[str] = None) -> BudgetAllocation:
    """Pure function. Mirror of computeBudgets at context-budget.ts:101-116."""
    effective_window = window_tokens if window_tokens > 0 else DEFAULT_CONTEXT_WINDOW
    chars_per_token = get_chars_per_token(provider) if provider else CHARS_PER_TOKEN
    total_chars = effective_window * chars_per_token
    return BudgetAllocation(
        summary_budget_chars=math.floor(total_chars * SUMMARY_RATIO),
        inline_context_budget_chars=math.floor(total_chars * INLINE_CONTEXT_RATIO),
        verification_budget_chars=math.floor(total_chars * VERIFICATION_RATIO),
        continue_threshold_percent=CONTINUE_THRESHOLD_PERCENT,
        task_count_range=(TASK_COUNT_MIN, resolve_task_count_max(effective_window)),
    )


def resolve_effective_context_window(window: int, provider: Optional[str]) -> int:
    """Apply Claude-Code 200K clamp (issue #4676)."""
    if provider == "claude-code" and window > CLAUDE_CODE_EFFECTIVE_WINDOW:
        return CLAUDE_CODE_EFFECTIVE_WINDOW
    return window


def resolve_executor_context_window(
    model_registry,
    prefs,
    session_window: int,
    session_provider: Optional[str] = None,
) -> int:
    """3-step fallback chain. Mirror of resolveExecutorContextWindow."""
    # Step 1: preferences.models.execution → registry lookup
    if prefs and getattr(prefs.models, "execution", None):
        model = model_registry.find_by_id(prefs.models.execution)
        if model:
            return resolve_effective_context_window(model.context_window, model.provider)
    # Step 2: session-provided window
    if session_window > 0:
        return resolve_effective_context_window(session_window, session_provider)
    # Step 3: default
    return DEFAULT_CONTEXT_WINDOW


def cap_preamble_budget(window_tokens: int, provider: Optional[str] = None) -> int:
    """Mirror of capPreamble (auto-prompts.ts:187-195) — the consumer side."""
    inline = compute_budgets(window_tokens, provider).inline_context_budget_chars
    return min(MAX_PREAMBLE_CHARS, inline)
```

Key Python constructs:
- `dataclass(frozen=True)` — `BudgetAllocation` is immutable; mirrors the TypeScript `interface BudgetAllocation` exactly. Frozen prevents accidental mutation by consumers.
- Module-level constants — direct port of the TypeScript module-level `const` declarations. Tunable in one place.
- `math.floor` — matches `Math.floor` in the TypeScript source exactly (NOT `int(...)` truncation, which differs for negatives — though negatives never appear here).
- `Tuple[int, int]` for `task_count_range` — preserves the `(min, max)` semantics. Could also be a `dataclass`; tuple is lighter for a 2-field value.

## Variations / pitfalls

- **Forgetting the Claude-Code 200K clamp** — without it, larger advertised windows (e.g., 1M for Gemini routed through claude-code) over-allocate and trigger Claude-Code-specific failures (issue #4676). The clamp must run on every resolution branch, not just the model-registry branch.
- **Conflating preamble-cap with inline-context budget** — preamble has its own historical cap (30K) that is NOT derivable from the ratio system. The consumer (`capPreamble`) takes `min(30K, inlineContextBudgetChars)`. Dropping the 30K removes the model-attention-cliff protection on large windows.
- **Hardcoding `chars_per_token = 4`** — fine as default but provider-specific deviation matters at small windows. Keep the `getCharsPerToken(provider)` indirection even if it returns the same value today.
- **Using integer division instead of `Math.floor`** — for the cases here all values are positive, so they coincide. But if window or ratio ever go negative, `int()` rounds toward zero while `floor()` rounds toward negative infinity. Match the source behavior.
- **Treating `TASK_COUNT_TIERS` as ordered descending** — the source orders descending; the linear scan depends on this order (first-match-wins). Reordering breaks the algorithm silently.
- **Recomputing budgets per consumer** — they are pure and cheap, but caching at the session level is fine. Just don't cache across sessions where `windowTokens` could change.
- **Skipping the `if windowTokens > 0` guard** — invalid input (0, negative) silently defaults to 200K (D002). Bypassing this guard makes downstream ratio multiplications produce zero or negative budgets.

## Cross-references

- Reference doc: `kb/core/context-management.md` §6 (Budget Computation)
- Sibling Phase-2 pattern: `kb/patterns/snapshot-persistence.md` (paired in `auto-prompts.ts` — both feed prompt assembly; siblings in the prompt-assembly story)
- Forward refs: `kb/core/provider-abstraction.md` (Phase 3 — provider-specific token caps, the per-model windowTokens that this engine consumes), `kb/prompts/template-system.md` (Phase 16 — how budgets feed prompt assembly)
- Walkthrough: `kb/walkthroughs/compaction.ts.md` §7 (the `4000`-token cushion in `maxInputTokens` is a related budget-cushion pattern)
