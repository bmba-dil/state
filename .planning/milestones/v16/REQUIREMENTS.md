# v16 — Build GSD Command Ports + Net-New Product-Hierarchy Commands Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Build Kernel: GSD Command Ports (A16)

- [ ] **PORT-01**: `/state:build:code-review` + `/state:build:code-review-fix` — spawned gsd-code-reviewer + gsd-code-fixer equivalents
- [ ] **PORT-02**: `/state:build:intel` — codebase intelligence refresh, writes `.state/build/intel/`
- [ ] **PORT-03**: `/state:build:map-codebase` — parallel mapper agents, writes `.state/build/codebase/`
- [ ] **PORT-04**: `/state:build:debug` — persistent debug session with scientific-method guardrails
- [ ] **PORT-05**: `/state:build:forensics` — post-mortem against git history + event log + artifacts
- [ ] **PORT-06**: `/state:build:pause-work` / `/state:build:resume-work` — context handoff via STATE.md projection
- [ ] **PORT-07**: `/state:build:thread` — persistent context threads across Steps/Slices
- [ ] **PORT-08**: `/state:build:workstreams` — multiple parallel work contexts in one project
- [ ] **PORT-09**: `/state:build:stats` — project statistics (phases, plans, requirements, git metrics, timeline)
- [ ] **PORT-10**: `/state:build:audit-uat` — cross-Slice UAT audit
- [ ] **PORT-11**: `/state:build:audit-milestone` — Arc/Phase boundary audit
- [ ] **PORT-12**: `/state:build:docs-update` — regenerate project docs verified against code
- [ ] **PORT-13**: `/state:build:backlog` + `/state:build:todos` + `/state:build:notes` — capture surfaces
- [ ] **PORT-14**: `/state:build:undo` — manifest-aware revert
- [ ] **PORT-15**: `/state:build:ui-phase` + `/state:build:ui-review` — UI spec + retroactive UI audit
- [ ] **PORT-16**: `/state:build:autonomous` — run all remaining unblocked work without interactive gates
- [ ] **PORT-17**: `/state:build:onboard` + `/state:build:help` — discoverability
- [ ] **PORT-18**: `/state:build:explore` — Socratic ideation router
- [ ] **PORT-19**: `/state:build:brainstorm` — 3-stage Seed → Expand → Converge
- [ ] **PORT-20**: `/state:build:scan` — lightweight codebase assessment
- [ ] **PORT-21**: `/state:build:cleanup` — archive completed artifacts
- [ ] **PORT-22**: `/state:build:reapply-patches` — reapply local mods after update
- [ ] **PORT-23**: `/state:build:new-arc` / `/state:build:new-phase` / `/state:build:new-slice` — hierarchy bootstrapping
- [ ] **PORT-24**: `/state:build:insert-slice` — urgent work via decimal numbering
- [ ] **PORT-25**: `/state:build:add-phase` / `/state:build:remove-phase`
- [ ] **PORT-26**: `/state:build:multi-arc` — batch-plan multiple Arcs from a feature dump
- [ ] **PORT-27**: `/state:build:review` — cross-AI peer review from external CLIs
- [ ] **PORT-28**: `/state:build:set-quality` / `/state:build:set-profile` / `/state:build:settings` — runtime toggles
- [ ] **PORT-29**: `/state:build:health` — diagnose planning health
- [ ] **PORT-30**: `/state:build:manager` — interactive command center
