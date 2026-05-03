# v21 — Teach Personalities + Teaching Style

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 198–205 (8 phases)

---

## Phases

#### Phase 198 — Port 7 AOL personalities verbatim
**Goal:** Copy `~/.claude/agent-of-learning/personalities/*.md` → `.state/teach/personalities/`; no semantic changes; attribution preserved.
**Depends on:** 167
**Requirements:** PER-01
**Parallelizable:** yes

#### Phase 199 — Personality loader (reads file, prepares system-prompt block)
**Goal:** Pydantic `Personality` model; loader reads + validates.
**Depends on:** 198
**Requirements:** PER-01
**Parallelizable:** yes with P3

#### Phase 200 — Inject personality via `chat.params` / `chat.headers` system prompt
**Goal:** Integrated with `experimental.chat.system.transform` hook (074).
**Depends on:** 199, 074
**Requirements:** PER-02
**Parallelizable:** yes

#### Phase 201 — 7-dimension teaching-style schema
**Goal:** `TeachingStyle` pydantic model: warmth, directness, humor, formality, patience, challenge, explicitness.
**Depends on:** 198
**Requirements:** PER-03
**Parallelizable:** yes

#### Phase 202 — CLI: `state teach style edit` (interactive 7-dim editor)
**Goal:** Typer + rich interactive prompt; saves to `.state/teach/style.json`.
**Depends on:** 201
**Requirements:** PER-03
**Parallelizable:** yes

#### Phase 203 — Per-subject personality override
**Goal:** Subject frontmatter or `personality-override.md`; override precedence rules.
**Depends on:** 199
**Requirements:** PER-04
**Parallelizable:** yes

#### Phase 204 — Personality + style integration with modes (v20)
**Goal:** Mode system-prompt template composed with personality preamble and style dimensions.
**Depends on:** 196, 200, 201
**Requirements:** (integration)
**Parallelizable:** yes

#### Phase 205 — Regression test (personality substring in system prompt)
**Goal:** For each personality, spawn session → assert substring present in outgoing system prompt.
**Depends on:** 198..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

