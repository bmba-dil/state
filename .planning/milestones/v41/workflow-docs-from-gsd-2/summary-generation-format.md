# Pattern: Summary Generation Format

**Layer:** Core Runtime (M1)
**Source:** `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:439-470` (`SUMMARIZATION_PROMPT`); `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:472-509` (`UPDATE_SUMMARIZATION_PROMPT`); `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:865-878` (`TURN_PREFIX_SUMMARIZATION_PROMPT`); `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:735-738` (prompt selection); `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:746-750` (conversation wrap); `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:567-579` (`isDegenerateSummary`); `gsd-2/packages/pi-coding-agent/src/core/compaction/compaction.ts:940-941` (file-ops tail)
**Discovered in:** Phase 2 (CORE-02)
**Related reference:** `kb/core/context-management.md` §4 (Summary Generation)

## What it does

Defines the markdown shape, prompt wording, and surrounding ceremony that turns a raw conversation slice into a structured summary stored in a `CompactionEntry`. Three prompts cover three scenarios: `SUMMARIZATION_PROMPT` (initial — no prior summary), `UPDATE_SUMMARIZATION_PROMPT` (iterative-merge — incorporate new messages into a previous summary), and `TURN_PREFIX_SUMMARIZATION_PROMPT` (split-turn prefix — when a single turn is too large to keep, summarize its prefix while retaining its suffix). Selection at compaction.ts:735 is `previousSummary ? UPDATE_SUMMARIZATION_PROMPT : SUMMARIZATION_PROMPT`.

The conversation is wrapped in `<conversation>...</conversation>` tags (and optionally `<previous-summary>...</previous-summary>`) before the chosen prompt is appended (compaction.ts:746-750). After the LLM returns, two deterministic post-processes apply: a *file-operations tail* is computed from the messages and appended (compaction.ts:940-941, `summary += formatFileOperations(readFiles, modifiedFiles)`), and `isDegenerateSummary` (compaction.ts:567-579) checks for malformed output (substring match or length<100) so the chunked-fallback loop can retry.

## Why it works that way

Four forces shape the prompt-and-format design:

1. **Iterative merge avoids re-summarization drift** — re-summarizing a 30-message session produces materially different output than incrementally updating a previous summary. The UPDATE prompt explicitly enumerates rules (PRESERVE, ADD, UPDATE) that pin the model to merge-semantics rather than re-derivation. Without this, every incremental compaction drifts further from original intent.
2. **Markdown structure is parseable** — the EXACT format (`## Goal`, `## Constraints & Preferences`, `## Progress` with Done/InProgress/Blocked subsections, `## Key Decisions`, `## Next Steps`, `## Critical Context`) means downstream tooling can split on the headings to extract specific sections. The compaction summary is structured data the agent can re-traverse.
3. **File-operations tail is computed deterministically** — appending the file list AFTER the LLM call rather than asking the model to enumerate paths in prose ensures the tail is always present and accurate. Models routinely paraphrase or omit file paths under summary pressure; deterministic append eliminates the risk.
4. **Degenerate-summary detection guards the chunked loop** — small models (and token-budget violations) sometimes return one-sentence summaries like "no messages to summarize" or empty strings. `isDegenerateSummary` (substring-match against three known phrases plus a length<100 guard) catches these so the chunked loop can retry, rather than poisoning the iterative chain (issue #4665).

Alternatives rejected:
- **Free-form summary (no fixed structure)** — defeats downstream parsing and produces wildly inconsistent quality across model families.
- **Ask the model to enumerate file paths** — unreliable; deterministic append is the fix.
- **Re-summarize from scratch every time** — drifts away from original intent and burns tokens linearly with session length.
- **Fuzzy degenerate-summary scoring** — flaky and hard to test. Substring + length is deterministic.

## Abstract algorithm

```text
generateSummary(messages, previousSummary, customInstructions, fileOps) -> str:
  # Step 1: Pick the base prompt
  if previousSummary is None:
    basePrompt = SUMMARIZATION_PROMPT
  else:
    basePrompt = UPDATE_SUMMARIZATION_PROMPT

  # Step 2: Optional extension hook
  if customInstructions:
    basePrompt += "\n\nAdditional focus: " + customInstructions

  # Step 3: Wrap the conversation
  conversationText = serialize(messages)
  promptText = "<conversation>\n" + conversationText + "\n</conversation>\n\n"
  if previousSummary:
    promptText += "<previous-summary>\n" + previousSummary + "\n</previous-summary>\n\n"
  promptText += basePrompt

  # Step 4: LLM call (with chunked fallback for over-budget messages — see compaction.ts:594-703)
  summary = llm.complete(promptText)

  # Step 5: Degenerate detection — retry once on the same chunk if degenerate
  if isDegenerateSummary(summary):
    summary = retry_or_fallback(messages, previousSummary)

  # Step 6: Deterministic file-ops tail
  summary += formatFileOperations(fileOps.readFiles, fileOps.modifiedFiles)

  return summary

isDegenerateSummary(summary) -> bool:
  if summary is None: return False
  lower = summary.lower()
  if "empty conversation" in lower: return True
  if "no conversation to summarize" in lower: return True
  if "no messages to summarize" in lower: return True
  if len(summary.strip()) < 100: return True
  return False
```

## Python equivalents

```python
from dataclasses import dataclass
from typing import Optional, List

SUMMARIZATION_PROMPT = """The messages above are a conversation to summarize. Create a structured context checkpoint summary that another LLM will use to continue the work.

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

Keep each section concise. Preserve exact file paths, function names, and error messages."""

UPDATE_SUMMARIZATION_PROMPT = """The messages above are NEW conversation messages to incorporate into the existing summary provided in <previous-summary> tags.

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

Keep each section concise. Preserve exact file paths, function names, and error messages."""

TURN_PREFIX_SUMMARIZATION_PROMPT = """This is the PREFIX of a turn that was too large to keep. The SUFFIX (recent work) is retained.

Summarize the prefix to provide context for the retained suffix:

## Original Request
[What did the user ask for in this turn?]

## Early Progress
- [Key decisions and work done in the prefix]

## Context for Suffix
- [Information needed to understand the retained recent work]

Be concise. Focus on what's needed to understand the kept suffix."""


def compose_summarization_prompt(
    conversation_text: str,
    previous_summary: Optional[str],
    custom_instructions: Optional[str] = None,
) -> str:
    base = UPDATE_SUMMARIZATION_PROMPT if previous_summary else SUMMARIZATION_PROMPT
    if custom_instructions:
        base = base + "\n\nAdditional focus: " + custom_instructions
    parts = [f"<conversation>\n{conversation_text}\n</conversation>\n\n"]
    if previous_summary:
        parts.append(f"<previous-summary>\n{previous_summary}\n</previous-summary>\n\n")
    parts.append(base)
    return "".join(parts)


def is_degenerate_summary(summary: Optional[str]) -> bool:
    """Conservative substring + length match. Mirror of compaction.ts:567-579."""
    if summary is None:
        return False
    lower = summary.lower()
    if "empty conversation" in lower:
        return True
    if "no conversation to summarize" in lower:
        return True
    if "no messages to summarize" in lower:
        return True
    if len(summary.strip()) < 100:
        return True
    return False


def format_file_operations(read_files: List[str], modified_files: List[str]) -> str:
    """Append a deterministic file-ops tail. Mirror of formatFileOperations."""
    parts = []
    if read_files:
        parts.append("\n\n## Files Read\n" + "\n".join(f"- {p}" for p in read_files))
    if modified_files:
        parts.append("\n\n## Files Modified\n" + "\n".join(f"- {p}" for p in modified_files))
    return "".join(parts)
```

Key Python constructs:
- Triple-quoted module-level constants — the prompts are pure data; treat them as configuration, not code.
- `Optional[str]` for `previous_summary` — `None` selects the initial prompt; non-`None` selects the iterative-merge prompt.
- Pure functions with no I/O — `compose_summarization_prompt`, `is_degenerate_summary`, `format_file_operations` are easy to unit-test.

## Variations / pitfalls

- **Forgetting the `<conversation>` wrapping** — without tags, the model can confuse the prompt instructions with the conversation content (especially on small models that aren't strong at role separation).
- **Re-deriving instead of merging** — if you don't pass `UPDATE_SUMMARIZATION_PROMPT` for iterative compaction, the model rewrites earlier decisions, losing fidelity. The PRESERVE/ADD/UPDATE rules are load-bearing.
- **Skipping the file-ops post-process** — the model cannot be trusted to enumerate file paths reliably under token pressure. Deterministic append after the LLM call is the only reliable path.
- **Fuzzy degenerate detection** — substring + length<100 is deterministic. Adding a learned classifier or fuzzy match makes test gates flaky and hard to reproduce across model families.
- **Modifying the prompt strings without versioning** — the prompts are part of the contract with downstream tooling that splits on the headings. Changing `## Done` to `## Completed` silently breaks that contract.

## Cross-references

- Reference doc: `kb/core/context-management.md` §4 (Summary Generation)
- Sibling Phase-2 pattern: `kb/patterns/auto-compaction-trigger.md` (when to invoke this)
- Walkthrough: `kb/walkthroughs/compaction.ts.md` §5, §6, §7, §10 (Plan 01 / Task 2)
