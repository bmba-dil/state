# Walkthrough: compaction.ts

> Phase 2 (CORE-02) — full annotated walkthrough of `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts` (981 lines).
> This file is the algorithmic heart of compaction: token estimation, cut-point detection, summary generation prompts, single-pass-vs-chunked decision, split-turn parallel summarization.
> Companion: `kb/core/context-management.md` §2 (Token Accounting), §3 (Decision Algorithm), §4 (Summary Generation), §5 (in-session persistence).

---

## §1. File Operation Tracking                  (lines 29-78)

The file opens with a 6-line file-level docstring (`compaction.ts:1-6`) — "Pure functions for compaction logic. The session manager handles I/O, and after compaction the session is reloaded." This is load-bearing: every function defined below is either pure or near-pure (DI on `complete`). The orchestrator class in `compaction-orchestrator.ts` owns I/O coordination; this file owns algorithm.

After imports (`compaction.ts:8-27`) — agent-core types, AI types, the `completeSimple` LLM call surface, the two compaction-token constants from `../constants.js`, the message converter, session schema types, and a long list of utilities re-exported from `./utils.js` — the first divider arrives at `compaction.ts:29-31` (`// File Operation Tracking`).

### `CompactionDetails` interface

`compaction.ts:34-37`:
```typescript
export interface CompactionDetails {
    readFiles: string[];
    modifiedFiles: string[];
}
```

This is the schema stored in `CompactionEntry.details` for the in-house (non-extension) compaction path. It enumerates files the LLM has read and modified during the segment being compacted away — preserved across compactions so that memory of "which files matter" survives the summary.

### `extractFileOperations` (compaction.ts:42-70)

Three-step gather:

1. **Inherit from previous compaction's details** (`compaction.ts:50-62`): if a prior compaction entry exists and was *not* extension-supplied (`!prevCompaction.fromHook`) and has `details`, fold its `readFiles` + `modifiedFiles` arrays into the current `fileOps`. The `fromHook` field name is preserved for session-file backward compatibility (older sessions used a different distinguishing field).
2. **Extract from message tool calls** (`compaction.ts:64-67`): iterate every message and let `extractFileOpsFromMessage` (from `./utils.js`) inspect tool calls (read, write, edit, etc.) and add to the running `fileOps`.
3. **Return** the accumulated `FileOperations` set.

This is the producer of `CompactionDetails` — every successful compaction's `details` is built from this function's output via `computeFileLists` (called from `compact` at `compaction.ts:940`).

### `CompactionResult<T>` interface (compaction.ts:73-79)

```typescript
export interface CompactionResult<T = unknown> {
    summary: string;
    firstKeptEntryId: string;
    tokensBefore: number;
    /** Extension-specific data (e.g., ArtifactIndex, version markers for structured compaction) */
    details?: T;
}
```

The `T` generic lets extensions define richer detail shapes (the GSD orchestrator extension uses an `ArtifactIndex`-flavoured detail; a plain pi compaction uses `CompactionDetails`). Note that `firstKeptEntryId` is the **UUID** of the first kept entry — the boundary marker — not an array index. This is the schema-evolution survivor of the migration documented at `session-manager.ts.md` §5.

The accompanying narrative comment at `compaction.ts:72` notes "SessionManager adds uuid/parentUuid when saving" — the `compact` function returns this struct, the SessionManager-level `appendCompaction` enriches it with persistence metadata.

---

## §2. Types — `CompactionSettings`             (lines 81-102)

After the second divider at `compaction.ts:81-83`, the `CompactionSettings` interface (`compaction.ts:85-96`) carries four fields:

| Field | Type | Purpose |
|-------|------|---------|
| `enabled` | `boolean` | Master gate. `shouldCompact` returns `false` immediately when disabled |
| `reserveTokens` | `number` | Absolute token reserve to leave free; legacy threshold mode |
| `keepRecentTokens` | `number` | Token budget for the kept-tail (passed to `findCutPoint`) |
| `thresholdPercent` | `number?` (optional, in `(0, 1)`) | Fraction-based override; if set, `shouldCompact` fires at `contextWindow * thresholdPercent` |

The `thresholdPercent` field is declared at `compaction.ts:85-95` (the JSDoc spans L89-94). It is the source of the dual-mode decision algorithm at `shouldCompact`. The doc-block explicitly notes the host-integration motivation: "Lets host integrations (e.g. GSD) express compaction policy as a fraction independent of model size." Since GSD-2 is a multi-model environment with windows ranging from 32K (small local llama.cpp servers) to 1M (Gemini 2.5), a percentage-based policy adapts where an absolute reserve would not.

`DEFAULT_COMPACTION_SETTINGS` at `compaction.ts:98-102`:
```typescript
export const DEFAULT_COMPACTION_SETTINGS: CompactionSettings = {
    enabled: true,
    reserveTokens: COMPACTION_RESERVE_TOKENS,
    keepRecentTokens: COMPACTION_KEEP_RECENT_TOKENS,
};
```

The two constants come from `../constants.js`. `thresholdPercent` is unset by default — the legacy absolute-reserve mode is the baseline; percentage mode is opt-in. See `../patterns/compaction-threshold-management.md` (Phase 1's pattern doc) for the full discussion of dual-mode trigger semantics.

---

## §3. Token Calculation                        (lines 104-210)

The third section (after the divider at `compaction.ts:104-106`) catalogues the token-accounting helpers. All are exported pure functions.

### `calculateContextTokens` (compaction.ts:112-114)

```typescript
export function calculateContextTokens(usage: Usage): number {
    return usage.totalTokens || usage.input + usage.output + usage.cacheRead + usage.cacheWrite;
}
```

The `||` is a documented preference: providers that report `totalTokens` directly (Anthropic, OpenAI) win; providers that don't, get a manual sum of the four components. Note: `cacheRead` + `cacheWrite` are included in the manual fallback because they consume window space even when billed differently.

### `getAssistantUsage` (compaction.ts:120-128)

Internal helper. Pulls `usage` off an `AssistantMessage`, **but** only if the stop reason is neither `"aborted"` nor `"error"` — those messages carry stale or absent usage. This guard is the reason `checkCompaction` in the orchestrator switches to `estimateContextTokens` for error-stopped messages (`compaction-orchestrator.ts:256`).

### `getLastAssistantUsage` (compaction.ts:133-142)

Walks `entries` backwards looking for the most recent `message`-typed entry whose `getAssistantUsage` returns truthy. Used by external code that needs a baseline token count from the session log.

### `ContextUsageEstimate` interface (compaction.ts:144-149)

```typescript
export interface ContextUsageEstimate {
    tokens: number;
    usageTokens: number;
    trailingTokens: number;
    lastUsageIndex: number | null;
}
```

The shape returned by `estimateContextTokens`. Decomposes the estimate into its sources so the caller can inspect: `usageTokens` (from the LLM's reported usage), `trailingTokens` (estimated from messages after the last usage), `lastUsageIndex` (the message index whose usage was used; `null` if none found).

### `getLastAssistantUsageInfo` (compaction.ts:151-157)

Internal helper. Like `getLastAssistantUsage` but returns `{ usage, index }` so the caller can locate the message. Used by `estimateContextTokens` below.

### `estimateContextTokens` (compaction.ts:163-191)

The token-source-of-last-resort. Algorithm:

1. Find the last assistant message with valid `usage` (via `getLastAssistantUsageInfo`).
2. If no usage anywhere → estimate every message via `estimateTokens` (the chars/4 heuristic from §4) and return `{ tokens: estimated, usageTokens: 0, trailingTokens: estimated, lastUsageIndex: null }`.
3. Otherwise → take the LLM's reported `usageTokens` for everything up through the usage-bearing message, then add `estimateTokens` for everything *after* that message (the trailing newer messages whose tokens have not yet been LLM-counted).

The final tokens count is `usageTokens + trailingTokens`. This is the canonical "estimate context size when usage data is incomplete" surface.

### `shouldCompact` (compaction.ts:200-210)

The decision function. Reproduced verbatim:

```typescript
export function shouldCompact(contextTokens: number, contextWindow: number, settings: CompactionSettings): boolean {
    if (!settings.enabled) return false;
    if (
        settings.thresholdPercent !== undefined &&
        settings.thresholdPercent > 0 &&
        settings.thresholdPercent < 1
    ) {
        return contextTokens > contextWindow * settings.thresholdPercent;
    }
    return contextTokens > contextWindow - settings.reserveTokens;
}
```

The dual-mode logic:

- **Percentage mode** (`thresholdPercent` set and in `(0, 1)`): `contextTokens > contextWindow * thresholdPercent`. Fire when usage exceeds a fraction of the window (e.g., 70%).
- **Absolute reserve mode** (default): `contextTokens > contextWindow - reserveTokens`. Fire when free headroom drops below the reserve.

The `> contextWindow * thresholdPercent` (strict greater-than) means the threshold is a high-water mark — exactly hitting `0.7 * contextWindow` does not trigger; exceeding it does. Same semantics for the absolute mode. This is `compaction.ts:200` (the function declaration line) — the line citation Phase 2's validation script anchors on.

---

## §4. Cut Point Detection                      (lines 212-433)

After the divider at `compaction.ts:212-214`, the cut-point detection subsystem follows. This section is the source of the §4.1 subsection of `kb/core/context-management.md`.

### `estimateTokens` (compaction.ts:220-278)

The chars/4 heuristic for token estimation, dispatched on message role. The JSDoc at `compaction.ts:217-218` explicitly states "This is conservative (overestimates tokens)". By role:

- **`"user"`** (`compaction.ts:224-236`): supports both string content and structured content arrays; sums `text.length` of each `text`-typed block.
- **`"assistant"`** (`compaction.ts:237-249`): iterates `content` blocks, summing `text.length` for `"text"`, `thinking.length` for `"thinking"`, and `name.length + JSON.stringify(arguments).length` for `"toolCall"`.
- **`"custom"` / `"toolResult"`** (`compaction.ts:250-265`): supports string or array content. For arrays, sums `text.length` for text blocks and adds **4800 chars per image** (estimated as ~1200 tokens — note the explicit comment at `compaction.ts:260`).
- **`"bashExecution"`** (`compaction.ts:266-269`): `command.length + output.length`.
- **`"branchSummary"` / `"compactionSummary"`** (`compaction.ts:270-274`): just `summary.length`.

Final `Math.ceil(chars / 4)` everywhere. Default fallback returns 0 (`compaction.ts:277`).

### `findValidCutPoints` (compaction.ts:287-322)

Returns the indices in `[startIndex, endIndex)` where it is safe to cut. Algorithm: iterate, examining each entry:

- **`message` entries**: cut points include `bashExecution`, `custom`, `branchSummary`, `compactionSummary`, `user`, `assistant` roles. **`toolResult` is explicitly skipped** — never cut at a tool result, because it must follow its tool call.
- **`branch_summary` and `custom_message` entry types**: also valid cut points (they are user-role-equivalent in the entry type system) — handled separately at `compaction.ts:317-319`.
- **All other entry types** (`thinking_level_change`, `model_change`, `compaction`, `custom`, `label`): not cut points; the `switch` falls through with `compaction.ts:308-315` listing them explicitly.

The structural rule: tool-result entries are paired with their tool-calling assistant message; they cannot be the *first kept* entry because they have no semantic head.

### `findTurnStartIndex` (compaction.ts:329-344)

Walks backwards from `entryIndex` to `startIndex`, returning the index of the entry that begins the current turn. Recognizes turn-starts as:

- `branch_summary` and `custom_message` entry types (treated as user-role at the schema level)
- `message` entries with role `user` or `bashExecution`

Returns `-1` if no turn start found (used as a sentinel by the caller).

### `CutPointResult` (compaction.ts:346-353)

```typescript
export interface CutPointResult {
    /** Index of first entry to keep */
    firstKeptEntryIndex: number;
    /** Index of user message that starts the turn being split, or -1 if not splitting */
    turnStartIndex: number;
    /** Whether this cut splits a turn (cut point is not a user message) */
    isSplitTurn: boolean;
}
```

The output triplet from `findCutPoint`. `isSplitTurn` is the signal that the turn-prefix-summary parallel branch in `compact()` must run.

### **Line-by-line: `findCutPoint` (compaction.ts:371-433)**

The 63-line algorithmic core. JSDoc at `compaction.ts:355-369` describes the contract. Body:

```typescript
export function findCutPoint(
    entries: SessionEntry[],
    startIndex: number,
    endIndex: number,
    keepRecentTokens: number,
): CutPointResult {
    const cutPoints = findValidCutPoints(entries, startIndex, endIndex);

    if (cutPoints.length === 0) {
        return { firstKeptEntryIndex: startIndex, turnStartIndex: -1, isSplitTurn: false };
    }

    // Walk backwards from newest, accumulating estimated message sizes
    let accumulatedTokens = 0;
    let cutIndex = cutPoints[0]; // Default: keep from first message (not header)

    for (let i = endIndex - 1; i >= startIndex; i--) {
        const entry = entries[i];
        if (entry.type !== "message") continue;

        // Estimate this message's size
        const messageTokens = estimateTokens(entry.message);
        accumulatedTokens += messageTokens;

        // Check if we've exceeded the budget
        if (accumulatedTokens >= keepRecentTokens) {
            // Find the closest valid cut point at or after this entry
            for (let c = 0; c < cutPoints.length; c++) {
                if (cutPoints[c] >= i) {
                    cutIndex = cutPoints[c];
                    break;
                }
            }
            break;
        }
    }

    // Scan backwards from cutIndex to include any non-message entries (bash, settings, etc.)
    while (cutIndex > startIndex) {
        const prevEntry = entries[cutIndex - 1];
        // Stop at session header or compaction boundaries
        if (prevEntry.type === "compaction") {
            break;
        }
        if (prevEntry.type === "message") {
            // Stop if we hit any message
            break;
        }
        // Include this non-message entry (bash, settings change, etc.)
        cutIndex--;
    }

    // Determine if this is a split turn
    const cutEntry = entries[cutIndex];
    const isUserMessage = cutEntry.type === "message" && cutEntry.message.role === "user";
    const turnStartIndex = isUserMessage ? -1 : findTurnStartIndex(entries, cutIndex, startIndex);

    return {
        firstKeptEntryIndex: cutIndex,
        turnStartIndex,
        isSplitTurn: !isUserMessage && turnStartIndex !== -1,
    };
}
```

Annotation by phase:

| Lines | Phase | Meaning |
|-------|-------|---------|
| `compaction.ts:377` | Discover valid cut points | Delegates to `findValidCutPoints` |
| `compaction.ts:379-381` | Empty session edge case | If no valid cuts (e.g., only tool results), return `firstKeptEntryIndex = startIndex` (keep everything) and `isSplitTurn = false` |
| `compaction.ts:384-385` | Initialize state | `accumulatedTokens = 0` (running token budget); `cutIndex = cutPoints[0]` (default fallback: keep from the *first* valid cut point — the earliest message) |
| `compaction.ts:387-406` | **Walk-back-with-token-budget** loop | Iterate from newest (`endIndex - 1`) backwards |
| ↳ `compaction.ts:388-389` | Skip non-message entries | They have no token cost in this loop |
| ↳ `compaction.ts:392-393` | Add this message's token estimate | Uses `estimateTokens` (the chars/4 heuristic) |
| ↳ `compaction.ts:396-405` | Budget exceeded → find cut | Once `accumulatedTokens >= keepRecentTokens`, scan `cutPoints` for the first one `>= i` (the current message index). That is the cut. `break` out of the walk |
| `compaction.ts:408-421` | **Scan-back to swallow non-message entries** | After landing on a cut, walk `cutIndex` backwards across `thinking_level_change`, `model_change`, `label`, etc. so the kept tail starts cleanly. **Stop conditions**: `compaction` entry (`compaction.ts:412-414` — never cross a prior compaction boundary) or any `message` entry (`compaction.ts:415-418` — stop at the previous semantic message). Increment `cutIndex` decreases until one of these fires |
| `compaction.ts:424-426` | **Split-turn detection** | If the cut entry is itself a `user` message → not split (the turn starts cleanly at the cut). Otherwise → call `findTurnStartIndex(entries, cutIndex, startIndex)` to locate the user message that began this turn |
| `compaction.ts:428-432` | Build result | `firstKeptEntryIndex` = the cut, `turnStartIndex` from the previous step, `isSplitTurn` true iff the cut is *not* a user message *and* a turn start was found |

Subtle: the inner `for (let c = 0; …)` loop at `compaction.ts:398-403` does a forward linear scan of `cutPoints` to find the first valid cut at-or-after the over-budget index `i`. Because `cutPoints` is sorted ascending (built by `findValidCutPoints` in forward order), the first hit is the smallest valid cut index >= `i`. This is the "we crossed the budget at message `i`; cut at the *next* valid boundary at-or-after `i`" rule.

---

## §5. Summarization Prompts & `chunkMessages`  (lines 435-546)

After the divider at `compaction.ts:435-437`, three prompt strings and `chunkMessages` follow.

### `SUMMARIZATION_PROMPT` (compaction.ts:439-470)

Reproduced verbatim:

```
The messages above are a conversation to summarize. Create a structured context checkpoint summary that another LLM will use to continue the work.

Use this EXACT format:

## Goal
[What is the user trying to accomplish? Can be multiple items if the session covers different tasks.]

## Constraints & Preferences
- [Any constraints, preferences, or requirements mentioned by user]
- [Or "(none)" if none were mentioned]

## Progress
### Done
- [x] [Completed tasks/changes]

### In Progress
- [ ] [Current work]

### Blocked
- [Issues preventing progress, if any]

## Key Decisions
- **[Decision]**: [Brief rationale]

## Next Steps
1. [Ordered list of what should happen next]

## Critical Context
- [Any data, examples, or references needed to continue]
- [Or "(none)" if not applicable]

Keep each section concise. Preserve exact file paths, function names, and error messages.
```

The prompt's structural choices are deliberate:

- **Six top-level sections** — Goal / Constraints & Preferences / Progress / Key Decisions / Next Steps / Critical Context.
- **Progress is sub-divided** into Done / In Progress / Blocked subsections.
- **Done uses `- [x]`** (markdown checkbox); In Progress uses `- [ ]` (unchecked) — visually evocative.
- **Next Steps is the only ordered (numbered) list** — implies action priority.
- **The closing rule** "Preserve exact file paths, function names, and error messages" is repeated in the update prompt — the single most-cited preservation invariant.

This prompt is the source for `kb/patterns/summary-generation-format.md` (Plan 02 pattern).

### `UPDATE_SUMMARIZATION_PROMPT` (compaction.ts:472-509)

Reproduced verbatim:

```
The messages above are NEW conversation messages to incorporate into the existing summary provided in <previous-summary> tags.

Update the existing structured summary with new information. RULES:
- PRESERVE all existing information from the previous summary
- ADD new progress, decisions, and context from the new messages
- UPDATE the Progress section: move items from "In Progress" to "Done" when completed
- UPDATE "Next Steps" based on what was accomplished
- PRESERVE exact file paths, function names, and error messages
- If something is no longer relevant, you may remove it

Use this EXACT format:

## Goal
[Preserve existing goals, add new ones if the task expanded]

## Constraints & Preferences
- [Preserve existing, add new ones discovered]

## Progress
### Done
- [x] [Include previously done items AND newly completed items]

### In Progress
- [ ] [Current work - update based on progress]

### Blocked
- [Current blockers - remove if resolved]

## Key Decisions
- **[Decision]**: [Brief rationale] (preserve all previous, add new)

## Next Steps
1. [Update based on current state]

## Critical Context
- [Preserve important context, add new if needed]

Keep each section concise. Preserve exact file paths, function names, and error messages.
```

The contract has three verbs in capital letters:
- **PRESERVE** — keep what was already there
- **ADD** — fold in new information
- **UPDATE** — mutate (most notably: move items from "In Progress" to "Done" as they complete)

The single relaxation: "If something is no longer relevant, you may remove it" — the only license for forgetting. Phase 2's `summary-generation-format.md` pattern hangs on this verb-triple as the iterative-merge algorithm.

### `chunkMessages` (compaction.ts:516-546)

Splits a message list into chunks each within `maxTokensPerChunk`. The body is straightforward (greedy fill, push, reset) but the **token-source choice is the load-bearing decision**:

```typescript
const msgTokens = estimateSerializedTokens(msg);
```

`compaction.ts:528`. Uses **`estimateSerializedTokens`** (from `./utils.js`), not `estimateTokens` (defined in this file). The 7-line comment block at `compaction.ts:522-527` documents why:

> Use POST-truncation token estimate: `serializeConversation` caps every large content block to `TOOL_RESULT_MAX_CHARS` before sending to the LLM, so chunk sizing must reflect what the LLM will actually see. Using the pre-truncation `estimateTokens` here was the root cause of issue #4665: a single 400K-char tool result looked like 100K tokens but serialized to ~600 tokens, producing tens of tiny information-starved chunks.

This is the single most important comment in the file: it documents why two parallel token-estimation surfaces (`estimateTokens` and `estimateSerializedTokens`) coexist, and which is correct in which context. The general rule: token estimates feeding decisions about *what the LLM will see* must use the post-serialization view, because tool-result truncation happens between message storage and LLM prompt assembly.

Single-message-larger-than-budget edge case: a chunk that would exceed `maxTokensPerChunk` *with one message in it* is allowed to start a new chunk anyway — `currentChunk.length > 0` guards the split. A single oversized message becomes a chunk of one. Comment "never dropped" at `compaction.ts:514`.

---

## §6. Degenerate Summary Detection (#4665)     (lines 548-579)

Section divider at `compaction.ts:548-550`. The `isDegenerateSummary` function (`compaction.ts:567-579`) is the issue-#4665 mitigation:

```typescript
export function isDegenerateSummary(summary: string | undefined): boolean {
    // undefined means "no summary was produced yet" (first chunk before any call)
    // — not degenerate. Empty string IS degenerate: the LLM returned nothing.
    if (summary === undefined) return false;
    const lower = summary.toLowerCase();
    if (lower.includes("empty conversation")) return true;
    if (lower.includes("no conversation to summarize")) return true;
    if (lower.includes("no messages to summarize")) return true;
    // Length guard: any summary shorter than 100 chars is almost certainly
    // degenerate for a multi-chunk pipeline.
    if (summary.trim().length < 100) return true;
    return false;
}
```

The 13-line JSDoc at `compaction.ts:552-566` explains the failure mode: when an early chunk contains only truncated tool-call preambles, the LLM may return a phrase like "(empty conversation)". The iterative `UPDATE_SUMMARIZATION_PROMPT` instructs the next chunk to "PRESERVE all existing information from the previous summary" — so an empty seed *propagates* emptiness through the entire chain. Without this guard, a single bad chunk poisons the rest.

Detection is **deterministic**:
- Three substring matches (case-insensitive): `"empty conversation"`, `"no conversation to summarize"`, `"no messages to summarize"`
- A length-floor: `summary.trim().length < 100` characters

The JSDoc at `compaction.ts:561-563` explicitly defends the determinism: "We keep this deterministic (no fuzzy scoring) because fuzzy matching is where quality gates become flaky and hard to test."

The `undefined` carve-out (return `false`) is critical: `undefined` means "no prior summary exists yet" (first chunk); empty string `""` IS degenerate (the LLM returned nothing).

---

## §7. `generateSummary` — single-pass vs chunked (lines 584-716)

The algorithmic crown jewel. JSDoc at `compaction.ts:584-593` explains: "When the messages exceed the model's context window, automatically falls back to chunked summarization". The function signature at `compaction.ts:594-603` is 8 parameters, including an injectable `_completeFn` for tests.

### **Line-by-line: `generateSummary` (compaction.ts:594-703)**

#### Step 1 — Total token estimation (compaction.ts:609-612)

```typescript
let totalTokens = 0;
for (const msg of currentMessages) {
    totalTokens += estimateSerializedTokens(msg);
}
```

Uses the *serialized* estimator for the same #4665 reason as `chunkMessages`. The 3-line comment at `compaction.ts:606-608` repeats the rationale.

#### Step 2 — Budget math (compaction.ts:614-617)

```typescript
const promptOverhead = 4_000;
const maxTokens = Math.floor(0.8 * reserveTokens);
const maxInputTokens = (model.contextWindow || 200_000) - reserveTokens - promptOverhead;
```

- `promptOverhead = 4_000` — a hard 4 K cushion for prompt framing + system prompt + response budget.
- `maxTokens` (for LLM response) is `0.8 * reserveTokens` floored — the LLM may write up to 80% of the reserve.
- `maxInputTokens` is the input budget: the model's context window (defaulting to 200 K) minus `reserveTokens` minus `promptOverhead`.

For a 200 K window with a 32 K reserve: `maxInputTokens = 200_000 - 32_000 - 4_000 = 164_000`. The 4 K cushion is the same number `kb/core/context-management.md §6` references when discussing budget-engine cushions; it is not the same as the budget engine's `MAX_PREAMBLE_CHARS = 30_000` (those are independent).

#### Step 3 — Single-pass branch (compaction.ts:619-622)

```typescript
if (totalTokens <= maxInputTokens) {
    return singlePassSummary(currentMessages, model, reserveTokens, apiKey, signal, customInstructions, previousSummary, complete);
}
```

If the messages fit in one prompt, defer to `singlePassSummary` (§8). No more decisions to make.

#### Step 4 — Chunked fallback setup (compaction.ts:624-626)

```typescript
const chunks = chunkMessages(currentMessages, maxInputTokens);
let runningSummary = previousSummary;
```

Build the chunks via `chunkMessages` (§5). `runningSummary` starts as whatever `previousSummary` was — could be `undefined` (no prior summary) or a string (iterative merge from a prior compaction). This is the seed for the iterative-merge loop.

#### Step 5 — The chunked-fallback running-summary loop (compaction.ts:628-683)

```typescript
for (let i = 0; i < chunks.length; i++) {
    const chunkSummary = await singlePassSummary(
        chunks[i],
        model,
        reserveTokens,
        apiKey,
        signal,
        customInstructions,
        runningSummary,
        complete,
    );

    if (isDegenerateSummary(chunkSummary)) {
        const retryPreviousSummary = i === 0 && runningSummary === undefined
            ? undefined
            : runningSummary;
        const retry = await singlePassSummary(
            chunks[i],
            model,
            reserveTokens,
            apiKey,
            signal,
            customInstructions,
            retryPreviousSummary,
            complete,
        );
        if (!isDegenerateSummary(retry)) {
            runningSummary = retry;
            continue;
        }
        // Both attempts degenerate — log and skip without poisoning the chain.
        process.stderr.write(
            `[compaction] WARN: chunk ${i + 1}/${chunks.length} produced a degenerate summary on both attempts; dropping chunk content from summary.\n`,
        );
        continue;
    }

    runningSummary = chunkSummary;
}
```

Annotated walkthrough:

| Lines | What | Why |
|-------|------|-----|
| `compaction.ts:628` | Iterate chunks in order | Each chunk runs `singlePassSummary` with the running summary as `previousSummary` argument |
| `compaction.ts:629-638` | First attempt for chunk `i` | Pass `runningSummary` as `previousSummary` so `singlePassSummary` will pick `UPDATE_SUMMARIZATION_PROMPT` if it's a string, or `SUMMARIZATION_PROMPT` if `undefined` |
| `compaction.ts:655` | Degenerate check on chunk output | The first guard against #4665 propagation |
| `compaction.ts:656-658` | **Retry seed selection** | If this is the first chunk *and* there was no prior summary → retry with `undefined` (use the initial `SUMMARIZATION_PROMPT` instead of the update prompt — break the poison chain at its source). Otherwise → retry with the same `runningSummary` (the failure may have been transient) |
| `compaction.ts:659-668` | Retry attempt | Same call shape, with `retryPreviousSummary` substituted |
| `compaction.ts:669-672` | Retry succeeded → adopt | Set `runningSummary = retry` and `continue` to next chunk |
| `compaction.ts:673-679` | **Both attempts degenerate** | Write a WARN line to `process.stderr` directly (bypassing logger to avoid dependency cycle), then `continue` to the next chunk **without updating `runningSummary`**. The 6-line comment at `compaction.ts:640-654` explains: "losing that chunk's content is still preferable to propagating emptiness forward, but the drop is now observable in logs." |
| `compaction.ts:682` | Non-degenerate path | Adopt `chunkSummary` as new `runningSummary` |

The double-degenerate-retry strategy is the issue-#4665 mitigation in full: one retry per chunk, with a smart seed flip on chunk 0; if both fail, observable drop, no silent corruption.

#### Step 6 — R6 fallback (compaction.ts:685-700)

```typescript
if (runningSummary === undefined) {
    if (previousSummary !== undefined) {
        process.stderr.write(
            "[compaction] WARN: every chunk produced a degenerate summary; falling back to existing previousSummary.\n",
        );
        return previousSummary;
    }
    throw new CompactionProducedNoSummaryError(
        `Compaction produced no usable summary: all ${chunks.length} chunk(s) were degenerate and no previousSummary was available.`,
    );
}
```

The 4-line comment at `compaction.ts:685-689` documents the failure mode: "if every chunk was degenerate and we have no `runningSummary`, do NOT silently return `""` — the caller would write an empty compaction entry, destroying all context with no signal."

Two fallback branches:
1. **`previousSummary !== undefined`**: warn + return the prior summary unchanged. Compaction effectively no-ops; the existing summary is reused; old messages are still summarized-away but the *summary* doesn't change.
2. **No previousSummary either**: throw `CompactionProducedNoSummaryError` with a counted-chunks message. The orchestrator's catch block (`compaction-orchestrator.ts:402-404`) translates this into the user-facing "session history preserved as-is" message.

#### Step 7 — Success return (compaction.ts:702)

```typescript
return runningSummary;
```

`runningSummary` is guaranteed to be a string at this point (we returned/threw above if it was `undefined`).

### `CompactionProducedNoSummaryError` class (compaction.ts:711-716)

```typescript
export class CompactionProducedNoSummaryError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "CompactionProducedNoSummaryError";
    }
}
```

A trivial named error class. The dedicated type lets `compaction-orchestrator.ts:402` use `instanceof` to distinguish #4665 from generic compaction failures and emit a clearer event.

---

## §8. `singlePassSummary` helper                (lines 722-767)

The non-chunked summary primitive. JSDoc at `compaction.ts:718-721`. Body:

- **`maxTokens` budget** (`compaction.ts:732`): `Math.floor(0.8 * reserveTokens)`. Same ratio as `generateSummary`. The LLM gets up to 80% of the reserve as response budget.
- **Prompt selection** (`compaction.ts:735`):
  ```typescript
  let basePrompt = previousSummary ? UPDATE_SUMMARIZATION_PROMPT : SUMMARIZATION_PROMPT;
  ```
  Truthy `previousSummary` (a non-empty string) → use the iterative-merge prompt. Falsy → use the initial-summary prompt. This is the source of the verb-triple PRESERVE/ADD/UPDATE branching at the prompt level.
- **`customInstructions` extension hook** (`compaction.ts:736-738`):
  ```typescript
  if (customInstructions) {
      basePrompt = `${basePrompt}\n\nAdditional focus: ${customInstructions}`;
  }
  ```
  The host can append focus instructions (e.g., "preserve the OAuth-related decisions specifically") that are merged into the bottom of the prompt. The orchestrator's manual `compact(customInstructions?)` is the typical caller.
- **Conversation wrapping** (`compaction.ts:740-750`):
  ```typescript
  const llmMessages = convertToLlm(currentMessages);
  const conversationText = serializeConversation(llmMessages);
  let promptText = `<conversation>\n${conversationText}\n</conversation>\n\n`;
  if (previousSummary) {
      promptText += `<previous-summary>\n${previousSummary}\n</previous-summary>\n\n`;
  }
  promptText += basePrompt;
  ```
  Two XML-ish wrappers: `<conversation>` always; `<previous-summary>` only when iterating. The `basePrompt` then sits at the bottom — the LLM sees data first, instructions last, which empirically yields better adherence.

  Note: messages are first converted via `convertToLlm` (handles custom message types like `bashExecution`, `custom`, `branchSummary`, etc.) and then serialized via `serializeConversation` (the toolResult-truncation point — the post-truncation view that #4665 hinges on).
- **Reasoning-aware completion options** (`compaction.ts:752-754`):
  ```typescript
  const completionOptions = model.reasoning
      ? { maxTokens, signal, apiKey, reasoning: "high" as const }
      : { maxTokens, signal, apiKey };
  ```
  If the model supports reasoning (Claude reasoning, Gemini thinking, etc.), request `"high"`. Summarization is one of the workloads where reasoning quality directly improves output integrity.
- **The completion call** (`compaction.ts:756-760`): `complete(model, { systemPrompt: SUMMARIZATION_SYSTEM_PROMPT, messages: createSummarizationMessage(promptText) }, completionOptions)`. The `SUMMARIZATION_SYSTEM_PROMPT` is the system-level role; `createSummarizationMessage` wraps `promptText` in the proper user-message envelope.
- **Error handling** (`compaction.ts:762-764`): `if (response.stopReason === "error") throw new Error("Summarization failed: ...")` — turns LLM errors into thrown exceptions, which the chunked loop in `generateSummary` handles via `try/catch` at the orchestrator level.
- **Return** (`compaction.ts:766`): `extractTextContent(response.content)` — strips the response down to its concatenated text content.

---

## §9. `prepareCompaction`                       (lines 769-859)

The pre-flight planner — given a session's path entries, decide *what* will be compacted and *what* will survive. Returns `CompactionPreparation | undefined` (`undefined` means "nothing to compact" — the orchestrator translates this to the "Already compacted" or "Nothing to compact" error).

### `CompactionPreparation` interface (compaction.ts:773-789)

Eight fields:

| Field | Purpose |
|-------|---------|
| `firstKeptEntryId` | UUID boundary marker — the first entry NOT summarized (kept verbatim) |
| `messagesToSummarize` | The messages that will be replaced by the summary |
| `turnPrefixMessages` | Messages forming the prefix of a split turn (empty if not split) |
| `isSplitTurn` | Whether the cut splits a turn (drives the parallel-summary branch in `compact`) |
| `tokensBefore` | Pre-compaction token count, used for telemetry / telemetry-driven follow-ups |
| `previousSummary?` | The prior compaction's summary (drives iterative-merge prompt selection) |
| `fileOps` | Accumulated `FileOperations` from messages + previous compaction |
| `settings` | The `CompactionSettings` snapshot — passed through so `compact` and downstream don't re-fetch |

The `settings` field's typo at `compaction.ts:787` ("Compaction settions from settings.jsonl") is an upstream comment artifact, preserved here for fidelity.

### Body — `prepareCompaction` (compaction.ts:791-859)

Boundary math, in order:

1. **Last-is-already-compaction guard** (`compaction.ts:795-797`): if the most recent entry is itself a `compaction`, return `undefined`. There is nothing to compact between "the last compaction" and "now".
2. **Find previous compaction index** (`compaction.ts:799-805`): walk the entries backwards to find the most recent `compaction`-typed entry. `prevCompactionIndex = -1` if none.
3. **Compute boundaries** (`compaction.ts:806-807`):
   - `boundaryStart = prevCompactionIndex + 1` — the entry just *after* the prior compaction (or 0 if none)
   - `boundaryEnd = pathEntries.length` — the array end
4. **`tokensBefore` calculation** (`compaction.ts:809-811`):
   ```typescript
   const usageStart = prevCompactionIndex >= 0 ? prevCompactionIndex : 0;
   const usageMessages = collectMessages(pathEntries, usageStart, boundaryEnd);
   const tokensBefore = estimateContextTokens(usageMessages).tokens;
   ```
   Note the `usageStart` includes the prior compaction entry itself (its own messages are summary tokens that contribute to the running context). `estimateContextTokens` is from §3.
5. **Cut point** (`compaction.ts:813`): `cutPoint = findCutPoint(pathEntries, boundaryStart, boundaryEnd, settings.keepRecentTokens)`. This is the §4 algorithm in action.
6. **First-kept-entry UUID resolve** (`compaction.ts:815-820`):
   ```typescript
   const firstKeptEntry = pathEntries[cutPoint.firstKeptEntryIndex];
   if (!firstKeptEntry?.id) {
       return undefined; // Session needs migration
   }
   const firstKeptEntryId = firstKeptEntry.id;
   ```
   If the entry has no `id`, the session is from an older schema version and needs the index→id migration documented at `session-manager.ts.md` §5. Compaction refuses to proceed.
7. **History-end split** (`compaction.ts:822`):
   ```typescript
   const historyEnd = cutPoint.isSplitTurn ? cutPoint.turnStartIndex : cutPoint.firstKeptEntryIndex;
   ```
   On a split turn, the history-to-summarize ends at `turnStartIndex` (so the in-progress turn's prefix gets a *separate* summary). On a clean cut, it ends at `firstKeptEntryIndex`.
8. **Separate `messagesToSummarize` from `turnPrefixMessages`** (`compaction.ts:824-830`):
   - `messagesToSummarize = collectMessages(pathEntries, boundaryStart, historyEnd)` — the bulk
   - `turnPrefixMessages = isSplitTurn ? collectMessages(...) : []` — the prefix of the in-progress turn, only when splitting
9. **Pull previous summary** (`compaction.ts:832-837`): if a prior compaction exists, pluck its `summary` for iterative-merge.
10. **File operations** (`compaction.ts:840-847`):
    - `extractFileOperations(messagesToSummarize, pathEntries, prevCompactionIndex)` — bulk extraction (§1)
    - For split turns, also fold in file ops from `turnPrefixMessages` (`compaction.ts:843-847`) so the appended file lists cover both halves.
11. **Return** (`compaction.ts:849-858`): the `CompactionPreparation` struct.

The orchestrator's manual and auto paths both call `prepareCompaction` first, and treat `undefined` as "nothing to do" — see `compaction-orchestrator.ts:108` and `compaction-orchestrator.ts:313`.

---

## §10. Main `compact()` & split-turn parallel   (lines 861-981)

After the divider at `compaction.ts:861-863`, the section reproducing two key surfaces.

### `TURN_PREFIX_SUMMARIZATION_PROMPT` (compaction.ts:865-878)

Reproduced verbatim:

```
This is the PREFIX of a turn that was too large to keep. The SUFFIX (recent work) is retained.

Summarize the prefix to provide context for the retained suffix:

## Original Request
[What did the user ask for in this turn?]

## Early Progress
- [Key decisions and work done in the prefix]

## Context for Suffix
- [Information needed to understand the retained recent work]

Be concise. Focus on what's needed to understand the kept suffix.
```

A **smaller, narrower prompt** than `SUMMARIZATION_PROMPT`. Three sections only — Original Request / Early Progress / Context for Suffix. The target is "what does the LLM need to know about the *first half* of an in-progress turn to make sense of the *second half* that's being kept verbatim?". This is a context bridge, not a session summary.

### **Line-by-line: `compact` (compaction.ts:887-953)**

The 67-line public entry. Body annotation:

#### Step 1 — Destructure preparation (compaction.ts:894-903)

```typescript
const {
    firstKeptEntryId,
    messagesToSummarize,
    turnPrefixMessages,
    isSplitTurn,
    tokensBefore,
    previousSummary,
    fileOps,
    settings,
} = preparation;
```

All eight fields pulled into local scope. No I/O, no allocations.

#### Step 2 — Split-turn parallel summarization branch (compaction.ts:906-925)

The most subtle control flow in the file. Reproduced verbatim:

```typescript
let summary: string;

if (isSplitTurn && turnPrefixMessages.length > 0) {
    // Generate both summaries in parallel
    const [historyResult, turnPrefixResult] = await Promise.all([
        messagesToSummarize.length > 0
            ? generateSummary(
                    messagesToSummarize,
                    model,
                    settings.reserveTokens,
                    apiKey,
                    signal,
                    customInstructions,
                    previousSummary,
                )
            : Promise.resolve("No prior history."),
        generateTurnPrefixSummary(turnPrefixMessages, model, settings.reserveTokens, apiKey, signal),
    ]);
    // Merge into single summary
    summary = `${historyResult}\n\n---\n\n**Turn Context (split turn):**\n\n${turnPrefixResult}`;
}
```

Annotation:

| Lines | What | Why |
|-------|------|-----|
| `compaction.ts:908` | Branch gate | Both `isSplitTurn === true` AND `turnPrefixMessages.length > 0`. The latter is defensive — `prepareCompaction` should already enforce this, but a belt-and-braces check |
| `compaction.ts:910` | `Promise.all` parallel | The two summaries are independent — `messagesToSummarize` and `turnPrefixMessages` are disjoint slices, no shared state — so they run concurrently. Two LLM calls in flight at once |
| `compaction.ts:911-921` | History summary task | Standard `generateSummary` for the bulk-history half. The `messagesToSummarize.length > 0` guard handles the edge case where the entire compaction is *just* a turn prefix (the cut landed before any complete prior turns). In that case use the literal string `"No prior history."` |
| `compaction.ts:922` | Turn-prefix summary task | `generateTurnPrefixSummary` (defined at L958-981 below) — uses `TURN_PREFIX_SUMMARIZATION_PROMPT` and a smaller `0.5 * reserveTokens` budget |
| `compaction.ts:925` | Merge | Single string concatenation with a `\n\n---\n\n` divider and the `**Turn Context (split turn):**` header. The history summary comes first (chronological order), the turn-context comes second (it's the *new* in-progress work) |

The non-split branch (`compaction.ts:926-937`) is mechanically simpler: just `summary = await generateSummary(messagesToSummarize, ...)`. No parallel.

#### Step 3 — File-list append (compaction.ts:940-941)

```typescript
const { readFiles, modifiedFiles } = computeFileLists(fileOps);
summary += formatFileOperations(readFiles, modifiedFiles);
```

`computeFileLists` deduplicates and sorts the `FileOperations` Sets into arrays. `formatFileOperations` (from `./utils.js`) renders them as a markdown tail appended directly to the summary string. Every successful compaction summary ends with this file-operations section — a structural invariant the consumer (`buildSessionContext` in session-manager) can rely on.

#### Step 4 — UUID assertion + return (compaction.ts:943-952)

```typescript
if (!firstKeptEntryId) {
    throw new Error("First kept entry has no UUID - session may need migration");
}

return {
    summary,
    firstKeptEntryId,
    tokensBefore,
    details: { readFiles, modifiedFiles } as CompactionDetails,
};
```

The migration guard is duplicated from `prepareCompaction` (`compaction.ts:817-819`) — defensive against partial migration or schema drift. The return shape is the public `CompactionResult`.

### `generateTurnPrefixSummary` (compaction.ts:958-981)

The dedicated turn-prefix variant of `singlePassSummary`. Differences:

- **Smaller budget**: `maxTokens = Math.floor(0.5 * reserveTokens)` (`compaction.ts:965`) — half the response budget of a regular summary, because turn prefixes are by construction smaller and the output should be tighter.
- **Different prompt**: `TURN_PREFIX_SUMMARIZATION_PROMPT` (no choice between initial vs update — turn-prefix summaries are always single-shot, never iteratively merged).
- **No `customInstructions`** parameter — turn-prefix summaries don't accept host-supplied focus.
- **No reasoning-aware path** — direct `{ maxTokens, signal, apiKey }`, no `reasoning: "high"`. The shorter shape doesn't benefit as much from reasoning escalation.
- **Same `<conversation>...</conversation>` wrap** but no `<previous-summary>` (it's always single-shot).

Otherwise identical to `singlePassSummary` (§8): `convertToLlm` → `serializeConversation` → wrap → `completeSimple` → error check → `extractTextContent`.

---

## §11. Cross-references

### Forward references — Phase 2 reference doc (Plan 03)

- [`../core/context-management.md`](../core/context-management.md) §2 — Token Accounting. Covers §3 here in narrative form.
- [`../core/context-management.md`](../core/context-management.md) §3 — Compaction Decision Algorithm. Covers `shouldCompact` consumer behavior.
- [`../core/context-management.md`](../core/context-management.md) §4 — Summary Generation (subsections 4.1-4.7). The narrative summary of §4-§10 here.
- [`../core/context-management.md`](../core/context-management.md) §5 — Compaction Persistence (in-session). The consumer side of `compact`'s output.

### Pattern siblings (Plan 02 deliverables)

- [`../patterns/auto-compaction-trigger.md`](../patterns/auto-compaction-trigger.md) — sourced partly from §3 (`shouldCompact` dual-mode logic).
- [`../patterns/summary-generation-format.md`](../patterns/summary-generation-format.md) — the prompt-shape pattern, sourced from §5 + §10.
- [`../patterns/overflow-recovery-one-shot.md`](../patterns/overflow-recovery-one-shot.md) — the bounded-retry pattern, with the orchestrator side of the algorithm.
- [`../patterns/budget-computation.md`](../patterns/budget-computation.md) — the budget engine; the `4_000`-token cushion at `compaction.ts:615` is one of the cushion choices documented there.

### Phase 1 sibling pattern

- [`../patterns/compaction-threshold-management.md`](../patterns/compaction-threshold-management.md) — the trigger surface (signature of `shouldCompact`, the abort-controller multiplicity). Phase 2's `auto-compaction-trigger.md` deepens the *decision* side of this surface.

### Sibling walkthroughs (this plan)

- [`./compaction-orchestrator.ts.md`](./compaction-orchestrator.ts.md) — the caller of `compact()`, `prepareCompaction()`, and `shouldCompact()`. See §4 step 7 (manual) and §7 branch 6 (auto).
- [`./session-manager.ts.md`](./session-manager.ts.md) — `findCutPoint` (§4 here) produces `firstKeptEntryId`, which is consumed by `buildSessionContext` and persisted via `appendCompaction` (§7 / §8 there).
- [`./compaction-snapshot.ts.md`](./compaction-snapshot.ts.md) — the snapshot subsystem fires on `session_before_compact`, which the orchestrator emits *before* invoking `compact()` from this file.
