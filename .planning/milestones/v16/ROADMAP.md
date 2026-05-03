# v16 — Build GSD Command Ports + Net-New Product-Hierarchy Commands

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 145–158 (14 phases)

---

## Phases

#### Phase 145 — `/state:build:code-review` + `/state:build:code-review-fix`
**Goal:** Ports gsd-code-reviewer + gsd-code-fixer; spawns task subagents; emits fix Steps.
**Depends on:** 144
**Requirements:** PORT-01
**Parallelizable:** yes

#### Phase 146 — `/state:build:intel` (codebase intelligence refresh)
**Goal:** Parallel intel subagents; writes `.state/build/intel/`.
**Depends on:** 144
**Requirements:** PORT-02
**Parallelizable:** yes

#### Phase 147 — `/state:build:map-codebase` (parallel mappers → CODEMAP.md)
**Goal:** Multi-agent; writes `.state/build/codebase/`.
**Depends on:** 144
**Requirements:** PORT-03
**Parallelizable:** yes

#### Phase 148 — `/state:build:debug` (persistent debug session w/ scientific-method guardrails)
**Goal:** State machine: hypothesize → observe → test → conclude; session persisted.
**Depends on:** 144
**Requirements:** PORT-04
**Parallelizable:** yes

#### Phase 149 — `/state:build:forensics` (post-mortem vs git + events + artifacts)
**Goal:** Event replay + git log walk; writes forensics report.
**Depends on:** 009, 144
**Requirements:** PORT-05
**Parallelizable:** yes

#### Phase 150 — `/state:build:pause-work` + `/state:build:resume-work` (context handoff)
**Goal:** STATE.md projection captures + restores hot context; Step state → paused/resumed.
**Depends on:** 125
**Requirements:** PORT-06
**Parallelizable:** yes

#### Phase 151 — `/state:build:thread` + `/state:build:workstreams` (persistent contexts, parallel streams)
**Goal:** Thread = cross-Phase side investigation; workstreams = multiple parallel work contexts in one project.
**Depends on:** 150
**Requirements:** PORT-07, PORT-08
**Parallelizable:** yes

#### Phase 152 — `/state:build:stats` + `/state:build:progress`
**Goal:** Project statistics (phases, plans, reqs, git, timeline); progress snapshot.
**Depends on:** 009
**Requirements:** PORT-09 (also covers MCP `dag_status` surfacing)
**Parallelizable:** yes

#### Phase 153 — `/state:build:audit-uat` + `/state:build:audit-milestone`
**Goal:** Cross-Slice UAT audit; Arc/Phase boundary audit.
**Depends on:** 130, 144
**Requirements:** PORT-10, PORT-11
**Parallelizable:** yes

#### Phase 154 — `/state:build:docs-update` + `/state:build:backlog`/`todos`/`notes`
**Goal:** Regenerate project docs verified against code; capture surfaces for backlog/todos/notes.
**Depends on:** 144
**Requirements:** PORT-12, PORT-13
**Parallelizable:** yes

#### Phase 155 — `/state:build:undo` + `/state:build:ui-phase`/`ui-review` + `/state:build:autonomous`
**Goal:** Manifest-aware revert; UI spec + retroactive UI audit; autonomous runs all unblocked work.
**Depends on:** 040, 144
**Requirements:** PORT-14, PORT-15, PORT-16
**Parallelizable:** yes

#### Phase 156 — `/state:build:onboard`/`help`/`explore`/`brainstorm`/`scan`/`cleanup`/`reapply-patches`
**Goal:** Discoverability + ideation + lightweight assessment + archive + patch-reapply.
**Depends on:** 144
**Requirements:** PORT-17, PORT-18, PORT-19, PORT-20, PORT-21, PORT-22
**Parallelizable:** yes

#### Phase 157 — Hierarchy bootstrapping (`/state:build:new-arc`/`new-phase`/`new-slice`/`insert-slice`/`add-phase`/`remove-phase`) + `/state:build:multi-arc`
**Goal:** Scaffolding commands + decimal-numbering insertion; batch plan multiple Arcs.
**Depends on:** 126, 144
**Requirements:** PORT-23, PORT-24, PORT-25, PORT-26
**Parallelizable:** yes

#### Phase 158 — `/state:build:review` + `/state:build:set-quality`/`set-profile`/`settings` + `/state:build:health` + `/state:build:manager`
**Goal:** Cross-AI peer review from external CLIs; runtime toggles; health diagnosis; command center.
**Depends on:** 144
**Requirements:** PORT-27, PORT-28, PORT-29, PORT-30
**Parallelizable:** yes

---

