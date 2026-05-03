# v26 — Portability Shims

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 239–246 (8 phases)

---

## Phases

#### Phase 239 — Host-capability detection (`HostCapabilities` negotiation)
**Goal:** Probe host for `question` tool, snapshot, TUI slots, worktree service; report capabilities to daemon.
**Depends on:** 106, 115
**Requirements:** PORT-SHIM-04
**Parallelizable:** yes

#### Phase 240 — Graceful degradation logic
**Goal:** Each feature has a degraded path when its capability is missing (drill → stdin, snapshot → git-only, TUI → CLI rich-render).
**Depends on:** 239
**Requirements:** PORT-SHIM-04
**Parallelizable:** yes

#### Phase 241 — Claude Code shim (MCP registration + CLAUDE.md guidance)
**Goal:** Document registration flow; ship CLAUDE.md template with slash-command guidance.
**Depends on:** 239, 240
**Requirements:** PORT-SHIM-01
**Parallelizable:** yes with P4, P5

#### Phase 242 — Gemini CLI shim (MCP stdio registration)
**Goal:** Register both MCP servers via Gemini CLI config; first-run auth import from Gemini's own store where applicable.
**Depends on:** 239, 240
**Requirements:** PORT-SHIM-02
**Parallelizable:** yes with P3, P5

#### Phase 243 — Qwen Code shim (MCP stdio registration)
**Goal:** Register both MCP servers; document setup.
**Depends on:** 239, 240
**Requirements:** PORT-SHIM-03
**Parallelizable:** yes with P3, P4

#### Phase 244 — pygit2 worktree fallback activation (per-host)
**Goal:** When opencode HTTP worktree unreachable, use pygit2 (already in 034); activate via capability detection.
**Depends on:** 034, 239
**Requirements:** WRK-02 (cross-host runtime)
**Parallelizable:** yes

#### Phase 245 — Cross-host parity test matrix
**Goal:** Run same 10 reference tool invocations on all 3 hosts; assert equivalent outputs (minus TUI).
**Depends on:** 241, 242, 243
**Requirements:** (verifier; TST-05)
**Parallelizable:** no

#### Phase 246 — Portability documentation (DOC-08 prep)
**Goal:** Setup guide per host; known limitations; feeds v27.
**Depends on:** 241, 242, 243
**Requirements:** DOC-08
**Parallelizable:** yes

---

