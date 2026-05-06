# v50 Handoff: Consolidated Teach Design & v18–v24 Rewrite Specs

## Milestone Goal

Perform a comprehensive gap analysis between state's current v18–v24 milestone plans and the new designs produced by v46–v49. Produce per-milestone rewrite specifications, updated REQ-IDs, updated phase decompositions, and ensure the consolidated teach-mode design is complete, consistent, and implementable. This is the teach-mode capstone — the counterpart to v45.

## What This Milestone Must Produce

### 1. Teach Mode Gap Analysis

For each original teach-mode milestone v18–v24, analyze: what did the original plan specify, and what does the new design (v46–v49) add or change?

**Per-milestone gap table:**
| Milestone | Original Scope | Gaps Found | New Scope |
|-----------|---------------|------------|-----------|
| v18 | Teach Kernel: Kolb + Concepts (11 phases, TCH-01..08) | v46 adds: full Subject/Module/Concept/Drill hierarchy, artifact catalog, Kolb FSM with all stages and transitions. v47 adds: teaching mode selection, personality injection. | Expand from 11 to ~15 phases. |
| v19 | Drill Engine (9 phases, DRL-01..06) | v48 adds: full Bayesian mastery formula, 8 drill types, hint/time penalty, spaced repetition scheduler, misconception detection. Original had Phase 178 as a research gap — now resolved. | Expand from 9 to ~14 phases. |
| v20 | Four Teaching Modes + Selector (11 phases) | v47 adds: mode selection algorithm (mastery-based + frustration override), mode-specific prompt templates, transparent mode transition. Original had mastery thresholds but no selection logic. | Refine 11 phases with algorithm specifics. |
| v21 | Personalities + Style (8 phases, PER-01..04) | v47 adds: 7-dimension style vector with scale ranges, style inference from observation, style-to-prompt conversion. Original had dimension names but no mechanics. | Expand from 8 to ~10 phases. |
| v22 | Scaffolding + Coding Partner (9 phases) | v49 adds: full workflow specifications for both modes, hard constraints (never take keyboard, never write code), blueprint tracking for scaffolding, graduated hint escalation for coding partner. | Refine 9 phases with workflow specs. |
| v23 | Teach TUI Extensions (8 phases, T-TUI-01..04) | New workflows (scaffolding progress, drill interface, mastery heatmap, session timeline) need TUI. Original had component names but no interaction contracts. | Expand from 8 to ~12 phases. |
| v24 | Subject Authoring + 4-Gate Promoter (8 phases) | v49 adds: full 4-gate workflow (interview→graph→draft→promote), validation rules, dry-run verification. Original had gate names but no workflow. | Refine 8 phases with workflow specs. |

### 2. Updated Teach REQ-IDs

Produce updated requirements for v18–v24:

**New REQ-IDs to add:**
- `T-STR-01` through `T-STR-12` (Teach Structure from v46)
- `T-HAR-01` through `T-HAR-15` (Teach Harness from v47)
- `T-QUAL-01` through `T-QUAL-20` (Teach Quality from v48)
- `T-WF-01` through `T-WF-15` (Teach Workflow from v49)

**Updated REQ-IDs for v18:**
- TCH-01 (Concept graph schema) → expanded with v46's full hierarchy
- TCH-02 (Kolb FSM) → expanded with v46's full Kolb state machine + v47's mode-stage composition
- TCH-03–08 similarly expanded

**Updated REQ-IDs for v19:**
- DRL-01 (Drill bank schema) → expanded with v48's 8 drill types
- DRL-02 (Drill engine) → expanded with v48's Bayesian formula
- DRL-03 (Drill presentation) → expanded with v48's question-tool integration + timer
- DRL-04 (Drill grading) → expanded with v48's hint/time penalties + fuzzy matching
- DRL-05 (Mastery tracking) → expanded with v48's Bayesian update + spaced repetition
- DRL-06 (Session management) → expanded with v48's early termination + drill budget

### 3. Updated Phase Decompositions

For v18–v24, produce new phase breakdowns reflecting the expanded scope:

**v18 updated phases (example — 11 → ~15):**
```
167: Subject/MODULE.md schema (pydantic models, per v46)
168: Concept/CONCEPT.md schema (pydantic models, per v46)
169: Drill/DRILLS.md schema (pydantic models, 8 types, per v46+v48)
170: KolbMachine FSM (full state machine with all stages, per v46)
171: Mental model schema (MENTAL-MODEL.json projection, per v46)
172: Observation schema (OBSERVATIONS.jsonl format, per v46)
173: Mistake schema (MISTAKES.jsonl format, per v46)
174: Subject/Module/Concept state machines (simpler FSMs, per v46)
175: Concept graph builder (prerequisite DAG, per v46)
176: Mode selector algorithm (mastery-based + frustration override, per v47)
177: Style-to-prompt converter (7-dim→system prompt, per v47)
178: [RESOLVED] Bayesian mastery formula (per v48) ← previously a research gap
179: Mental model projector (rebuild from OBSERVATIONS.jsonl, per v46)
180: Cross-referencing rules (teach-mode artifact links, per v46)
181: Golden fixture suite (integration tests for full Kolb cycle)
```

**v19 updated phases (9 → ~14):**
```
182: Drill bank loader (reads DRILLS.md, validates, per v48)
183: Drill engine core (session flow: prepare→present→submit→grade→feedback, per v48)
184: Bayesian mastery calculator (prior, likelihood, posterior, aggregation, per v48)
185: Drill selection algorithm (mastery-based + mistake-prioritized, per v48)
186: Drill presentation via question tool (timer, hint button, per v48)
187: Drill grading (fuzzy match, code tests, LLM judge, per v48)
188: Hint penalty system (weight reduction per hint level, per v48)
189: Time penalty system (optimal range calibration, per v48)
190: Drill difficulty calibration (per-drill difficulty rating, per v48)
191: Session budget enforcement (max drills, max time, max tokens, per v48)
192: Spaced repetition scheduler (SM-2 with learner calibration, per v48)
193: Review session handler (triggered by scheduler, per v48)
194: Misconception detector (5 types, per v48)
195: Drill engine integration test (full session from preparation to mastery)
```

(Similarly expanded for v20, v21, v22, v23, v24)

### 4. Updated Tracking Files

Produce updated versions of:

**ROADMAP.md updates:**
- v18–v24 milestones updated with new phase counts, new REQ-IDs, new success criteria
- v46–v50 milestones added to ROADMAP.md (next to v40–v45)
- Dependency graph updated: v46→v47→v48→v49→v50, v50→v18-v24 rewrites
- v18 Phase 178 marked "[RESOLVED by v48]"

**REQUIREMENTS.md updates:**
- New REQ-ID sections: T-STR-01..12, T-HAR-01..15, T-QUAL-01..20, T-WF-01..15
- Updated REQ-IDs for v18–v24
- Annotations on deferred REQ-IDs

**STATE.md update:**
- Decisions logged from teach-mode design session
- Current status updated

**PROJECT.md update:**
- Key Decisions: added entries for teach-mode design decisions
- Active requirements: updated to reflect v46–v50 in-flight

### 5. Teach-Mode Design Traceability Matrix

Same format as v45, but for teach mode:

| Design Decision (v46–v49) | Affects v18 Phase | Affects v19 Phase | Affects v20 Phase | Affects v21 Phase | Affects v22 Phase | Affects v23 Phase | Affects v24 Phase |
|---------------------------|-------------------|-------------------|-------------------|-------------------|-------------------|-------------------|-------------------|
| 4-tier teach hierarchy (v46) | 167–169 (schemas) | — | — | — | — | — | — |
| Kolb FSM (v46) | 170 (KolbMachine) | — | — | — | — | — | — |
| Mental model schema (v46) | 171 (MENTAL-MODEL) | 192 (review) | — | — | — | — | — |
| Mode selection (v47) | 176 (selector) | — | 187–197 (all modes) | — | — | — | — |
| Style injection (v47) | 177 (converter) | — | — | 198–205 (personalities) | — | — | — |
| Bayesian formula (v48) | 178 (formula) | 184 (calculator) | — | — | — | — | — |
| Drill engine (v48) | — | 182–183 (engine) | — | — | — | — | — |
| Spaced repetition (v48) | — | 192 (scheduler) | — | — | — | — | — |
| Misconception detection (v48) | — | 194 (detector) | — | — | — | — | — |
| Teaching cycle (v49) | 170 (KolbMachine) | — | — | — | 206–214 (all) | — | 223–230 (authoring) |
| Scaffolding workflow (v49) | — | — | — | — | 206–208 (scaffolding) | 215 (TUI) | — |
| Coding partner workflow (v49) | — | — | — | — | 209–214 (partner) | 216 (TUI) | — |
| Subject authoring (v49) | — | — | — | — | — | — | 223–230 (all) |

### 6. Integration with Build Mode Design

Cross-reference teach and build designs to ensure consistency:

**Shared concepts (must align):**
- Session management: build-mode session (v43) and teach-mode session (v49) use the same daemon, same event store, same SSE bus
- Subagent spawning: both modes use opencode's `task` tool — same protocol (v43)
- Context management: different strategies (build = task-focused, teach = learner-focused) but same harness infrastructure (v41/v47)
- Mode isolation: build and teach share only `state_core` (v11) — the designs must respect this boundary

**Mode transition:**
- When a learner in teach mode hits the AC phase and needs to write code, should the harness briefly switch to build mode? Or stay in teach mode with coding-partner sub-mode?
- Design decision required: teach-mode code exercises use teach-mode MCP server, not build-mode MCP server

## Success Criteria

1. Gap analysis is complete for all 7 teach-mode milestones (v18–v24) with before/after scope documented.
2. Updated REQ-ID mappings cover all new design concepts from v46–v49.
3. Updated phase decompositions for v18–v24 reflect all new design decisions with traceable rationale.
4. Updated tracking files (ROADMAP.md, REQUIREMENTS.md, STATE.md, PROJECT.md) are ready to commit.
5. Teach-mode design traceability matrix connects every v46–v49 decision to its v18–v24 phase impact.
6. Cross-reference with build mode design confirms consistency in shared infrastructure.
7. Phase 178 (Bayesian formula research gap) is marked RESOLVED.

## Research Inputs

**All v46–v49 handoff documents:**
- `.planning/research/v46-handoff.md` — Teach Structure & Artifacts
- `.planning/research/v47-handoff.md` — Teach Harness & Teaching Control
- `.planning/research/v48-handoff.md` — Teach Quality & Learning Verification
- `.planning/research/v49-handoff.md` — Teach Workflow & AOL Port Map

**All original teach-mode milestone plans:**
- `.planning/milestones/v18/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v19/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v20/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v21/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v22/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v23/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v24/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`

**Master tracking files:**
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/PROJECT.md`

**Build mode design (for cross-reference):**
- `.planning/research/v40-handoff.md` through `v45-handoff.md`

## Key Questions for Discuss-Phase

1. **Teach mode concurrent with build mode**: Can teach-mode and build-mode sessions run simultaneously (different concepts/arcs)? The daemon supports both modes. The mode middleware enforces isolation. But can a learner be running a build Slice AND a teach Concept at the same time in different opencode sessions?

2. **Code exercises and worktrees**: When a learner writes code in the AC phase, should the code go into a temporary worktree (isolated, can be discarded)? Or into the learner's actual project? Teaching exercises shouldn't pollute a build Slice's worktree.

3. **AOL backwards compatibility**: Should state be able to read AOL's existing OBSERVATIONS.jsonl and MENTAL-MODEL.json files? This would enable migration (v25) for teach mode.

4. **Phase 178 resolution confidence**: How confident are we that the Bayesian formula design in v48 resolves the Phase 178 research gap? Should the formula be validated against AOL's actual drill grading before we declare victory?

5. **Teach TUI scope**: v23's TUI expansion is significant (4 new components: scaffolding progress, drill interface, mastery heatmap, session timeline). Should these be designed to the same depth as v9/v10 (detailed UI-SPEC.md) during this milestone, or during v23 execution?

## Dependencies

- **v46, v47, v48, v49** — ALL MUST be complete. This milestone synthesizes their output.
- **v45 (Build Consolidated Design)** — useful for patterns and cross-reference.
- **Original v18–v24 milestone plans** — all exist, need to be read.
- **Master tracking files** — all exist, need to be read.

## Scope Boundaries

**In scope:**
- Gap analysis for v18–v24
- Updated REQ-IDs
- Updated phase decompositions for v18–v24
- Updated tracking files
- Teach-mode design traceability matrix
- Cross-reference with build mode design
- Marking Phase 178 as resolved

**Out of scope:**
- Any implementation
- Build mode gap analysis (v45 does this)
- New milestone creation (this milestone PRODUCES the specs; `gsd-new-milestone` creates them)
