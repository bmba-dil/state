# v8 — Plugin Server Hooks (all 9)

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 068–079 (12 phases)

---

## Phases

#### Phase 068 — `@state/opencode-plugin` TS package scaffolding (bun, tsconfig match opencode)
**Goal:** `package.json` peer deps per STACK.md; `tsconfig` extends `@tsconfig/node22`; `build: "tsc"`; `bun install`.
**Depends on:** 060
**Requirements:** HOOK-11
**Parallelizable:** yes (independent TS workspace)

#### Phase 069 — `chat.message` hook (prompt guard + state injection)
**Goal:** Parse `/state:*`, reject cross-mode, append active Step/Concept hint.
**Depends on:** 068, 063
**Requirements:** HOOK-01
**Parallelizable:** yes with P3..P11

#### Phase 070 — `tool.execute.before` hook (mode gate + scope gate)
**Goal:** Block writes outside active Slice worktree; block `mcp__state-teach__*` in build mode; rewrite `.state/` path args.
**Depends on:** 068
**Requirements:** HOOK-02
**Parallelizable:** yes

#### Phase 071 — `tool.execute.after` hook (output verification + observation)
**Goal:** Build: match against Step `verify_contract`; Teach: classify + feed mental_model.
**Depends on:** 068
**Requirements:** HOOK-03
**Parallelizable:** yes

#### Phase 072 — `permission.ask` hook (gray-area routing)
**Goal:** Auto-approve within scope; route to dialog otherwise; persist `state.permission.decided`.
**Depends on:** 068
**Requirements:** HOOK-04
**Parallelizable:** yes

#### Phase 073 — `event` hook (universal observer → SSE mirror)
**Goal:** Subscribe to `session.idle`, `worktree.ready`, `question.replied`, `permission.replied`, etc.; mirror to daemon.
**Depends on:** 068
**Requirements:** HOOK-05
**Parallelizable:** yes

#### Phase 074 — `experimental.chat.system.transform` hook (mode-specific system injection)
**Goal:** Prepend mode banner + active artifact content (STEP.md frontmatter, verify contract, personality).
**Depends on:** 068
**Requirements:** HOOK-06
**Parallelizable:** yes

#### Phase 075 — `experimental.session.compacting` hook (phase-aware compaction)
**Goal:** Inject "preserve these IDs" (active Step ID, last 3 verify results, open gray-area, pending drills).
**Depends on:** 068
**Requirements:** HOOK-07
**Parallelizable:** yes

#### Phase 076 — `chat.params` + `chat.headers` hook (profile + cache-control injection)
**Goal:** Inject model profile resolution (from 027); cache-control markers; thinking budget.
**Depends on:** 068, 027
**Requirements:** HOOK-08
**Parallelizable:** yes

#### Phase 077 — `command.execute.before` hook (mode gate for slash commands)
**Goal:** Reject `/state:build:*` when mode=teach, and vice versa; inject expanded `.planning/*.md` content.
**Depends on:** 068
**Requirements:** HOOK-09
**Parallelizable:** yes

#### Phase 078 — `shell.env` hook (STATE_* env var injection)
**Goal:** Export `STATE_ARC`, `STATE_PHASE`, `STATE_SLICE`, `STATE_STEP`, `STATE_WORKTREE`, `STATE_DAEMON_URL`, `STATE_AUTH_JSON`.
**Depends on:** 068
**Requirements:** HOOK-10
**Parallelizable:** yes

#### Phase 079 — Plugin bundle + `bun build` packaging + install script
**Goal:** Bundled `@state/opencode-plugin` TS package; `state install` auto-registers.
**Depends on:** 069..P11
**Requirements:** HOOK-11
**Parallelizable:** no (final integration)

---

