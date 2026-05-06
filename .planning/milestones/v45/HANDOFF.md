# v45 Handoff: Consolidated Design & v14–v27 Rewrite Specs

## Milestone Goal

Perform a comprehensive gap analysis between state's current v14–v27 milestone plans and the new designs produced by v40–v44. Produce per-milestone rewrite specifications, updated REQ-IDs, updated phase decompositions, and updated tracking files. This is the **capstone** that ensures the original milestones are refined with everything learned during the design spike.

## What This Milestone Must Produce

### 1. Gap Analysis

For each original milestone v14–v27, analyze: what did the original plan specify, and what does the new design (v40–v44) add or change?

**Per-milestone gap table:**
| Milestone | Original Scope | Gaps Found | New Scope |
|-----------|---------------|------------|-----------|
| v14 | Build Kernel Step FSM (11 phases, BLD-01..09) | v40 adds: full artifact schemas, cross-referencing, STATE.md projector model. v42 adds: full verifier chain, 4-level model, stub detection, anti-pattern scanner. v43 adds: full workflow cycle, DAG integration, session management. | Expand from 11 to ~15 phases. |
| v15 | Build Core Commands (10 phases, CMD-01..08) | v41 adds: task decomposition protocol, analysis paralysis guard, deviation rules. v42 adds: plan checker, threat model. v43 adds: GSD port map. | Expand from 10 to ~14 phases. |
| v16 | GSD Ports + Hierarchy Commands (14 phases, PORT-01..30) | v43 adds: complete command port map with design rationale per command. v40 adds: new-arc/new-phase/new-slice commands. | Expand from 14 to ~18 phases. |
| v17 | Build TUI Extensions (8 phases, B-TUI-01..04) | The new design's richer quality pipeline needs richer TUI: verifier progress, threat model viewer, stub report, DAG execution view. v41 adds: context meter, paralysis indicator. | Expand from 8 to ~12 phases. |
| v18 | Teach Kernel Kolb+Concepts (11 phases, TCH-01..08) | (Deferred to v46–v50 design spike, but gap analysis still needed: what does build-mode design imply for teach mode?) | Re-scoped by v50. |
| v19 | Teach Drill Engine (9 phases, DRL-01..06) | (Deferred to v46–v50) | Re-scoped by v50. |
| v20 | Teach Four Modes (11 phases) | (Deferred to v46–v50) | Re-scoped by v50. |
| v21 | Teach Personalities+Style (8 phases) | (Deferred to v46–v50) | Re-scoped by v50. |
| v22 | Scaffolding+Coding Partner (9 phases) | (Deferred to v46–v50) | Re-scoped by v50. |
| v23 | Teach TUI Extensions (8 phases) | (Deferred to v46–v50) | Re-scoped by v50. |
| v24 | Subject Authoring (8 phases) | (Deferred to v46–v50) | Re-scoped by v50. |
| v25 | Migration & Import (8 phases, MIG-01..04) | v40's artifact catalog changes the import target structure. GSD's 2-tier→state's 4-tier mapping is now well-defined by v40. | Refine phases per v40. |
| v26 | Portability Shims (8 phases, PORT-SHIM-01..04) | v44's Rust DB is a new portability concern (Rust toolchain requirement). v41's harness is opencode-specific; portability shims need to handle harness gaps. | Add Rust DB portability phase. |
| v27 | Release & Packaging (10 phases, REL-01..06, DOC-01..08, etc.) | v44's Rust DB adds build complexity. New documentation needs: hierarchy guide, harness guide, quality pipeline guide, GSD migration guide, RTK guide. | Expand doc scope. Add Rust build phase. |

### 2. Updated REQ-ID Mappings

Produce updated requirements for v14–v17 at minimum (v18–v24 deferred to v50):

**New REQ-IDs to add:**
- `HAR-01` through `HAR-12` (Harness requirements from v41)
- `QUAL-01` through `QUAL-15` (Quality requirements from v42)
- `WF-01` through `WF-20` (Workflow requirements from v43)
- `ART-01` through `ART-15` (Artifact requirements from v40)

**Updated REQ-IDs for v14:**
- BLD-01 (STEP.md schema) → expanded with v40's full artifact schema
- BLD-02 (Step FSM) → expanded with v40's full FSM + v43's workflow integration
- BLD-03 (Goal-backward verifier) → expanded with v42's 4-level model + adversarial stance
- BLD-04 (Slice rollup) → expanded with v42's hierarchical verifier chain
- BLD-05–07 → similarly expanded
- BLD-08 (Security verifier) → expanded with v42's threat model framework
- BLD-09 (Result storage) → expanded with v42's evidence chain + v40's artifact catalog

### 3. Updated Phase Decompositions

For v14–v17, produce new phase breakdowns reflecting the expanded scope:

**v14 updated phases (example — 11 → ~15):**
```
124: STEP.md schema (pydantic model with extra="forbid", all frontmatter fields)
125: StepMachine FSM (all states, guards, transitions, per v40+v43 design)
126: Arc/Phase/Slice FSMs (simpler state machines per v40)
127: Goal-backward verifier (4-level model, adversarial stance, per v42)
128: Security verifier (STRIDE register, threat model verification, per v42)
129: Stub detector (all patterns, severity classification, trace-through, per v42)
130: Anti-pattern scanner (code/arch/test patterns, per v42)
131: Slice rollup verifier (Step aggregation, per v42)
132: Phase rollup verifier (Slice aggregation + Phase integration tests)
133: Arc rollup verifier (Phase aggregation + Arc acceptance criteria)
134: Cross-tier verifier (regression detection, per v42)
135: Evidence chain (verification evidence storage + audit trail, per v42)
136: Verification result storage (SQLite + Markdown dual-write)
137: Plan checker (pre-execution validation, per v42)
138: Gray-area plumbing (decision surfaces, per v40)
139: Golden fixture suite (integration tests for full verifier chain)
```

(Similarly expanded for v15, v16, v17)

### 4. Updated Tracking Files

Produce updated versions of:

**ROADMAP.md updates:**
- v14–v17 milestones updated with new phase counts, new REQ-IDs, new success criteria
- v18–v24 milestones annotated: "[PENDING v46–v50 TEACH DESIGN SPIKE]"
- v40–v50 milestones added to ROADMAP.md
- Dependency graph updated (v40–v44 feed into v45, v45 feeds into v14–v17 rewrites)
- v12/v13 noted as "proceeding in parallel"

**REQUIREMENTS.md updates:**
- New REQ-ID sections: HAR-01..12, QUAL-01..15, WF-01..20, ART-01..15
- Updated REQ-IDs for v14–v17
- Annotations on deferred REQ-IDs (v18–v24 pending v46–v50)

**STATE.md update:**
- Current milestone recorded as "v12/v13 executing, v40–v50 design spike planned"
- Decisions logged from this design session

**PROJECT.md update:**
- Key Decisions table: added entry for "11-milestone design spike (v40–v50)"
- Context post-v11: updated to reflect design spike initiation
- Active requirements: updated to reflect v40–v50 in-flight

### 5. Design Traceability Matrix

Produce a matrix showing how every v40–v44 design decision maps to v14–v17 phase updates:

| Design Decision (v40–v44) | Affects v14 Phase | Affects v15 Phase | Affects v16 Phase | Affects v17 Phase |
|---------------------------|-------------------|-------------------|-------------------|-------------------|
| 4-tier artifact catalog (v40) | 124 (STEP.md schema) | — | 150 (hierarchy commands) | — |
| STATE.md projector model (v40) | 125 (Step FSM) | 135 (state tracking) | 150 (hierarchy commands) | 160 (dashboard) |
| Context management protocol (v41) | — | 135 (execute command) | — | 162 (context meter) |
| Task decomposition protocol (v41) | — | 135 (execute command) | — | — |
| Plan-as-prompt architecture (v41) | 124 (STEP.md schema) | 136 (plan command) | — | — |
| Analysis paralysis guard (v41) | — | 138 (execution guard) | — | 162 (paralysis indicator) |
| Scope reduction prohibition (v41) | — | 136 (plan command) | — | — |
| Deviation rules (v41) | — | 135 (execute command) | — | — |
| 4-level verification (v42) | 127 (goal-backward) | — | — | — |
| Adversarial verification (v42) | 127 (goal-backward) | — | — | — |
| Stub detection (v42) | 129 (stub detector) | — | — | — |
| Anti-pattern scanner (v42) | 130 (anti-pattern) | — | 145 (code review) | — |
| Threat model framework (v42) | 128 (security verifier) | 136 (plan command) | — | — |
| Full workflow cycle (v43) | 125 (Step FSM) | 135–144 (all commands) | — | — |
| DAG scheduler integration (v43) | 125 (Step FSM) | — | — | 160 (DAG viewer) |
| Session management (v43) | — | — | — | — |
| GSD port map (v43) | — | — | 145–158 (all ports) | — |
| Rust DB schema (v44) | — | — | — | — |
| RTK compression (v44) | — | 135 (context injection) | — | — |

### 6. Integration Verification

Design how we verify that the v14–v17 rewrites satisfy both:
- The original v14–v17 milestone goals (from .planning/milestones/)
- The new design specifications (from v40–v44)

This is a meta-verification: does the updated plan achieve what the design says it should?

**Verification checklist (per v14–v17 milestone):**
1. Every REQ-ID from the original milestone is covered by at least one phase in the rewrite
2. Every new REQ-ID from v40–v44 is assigned to the correct milestone
3. Every phase has a clear goal, success criteria, and dependencies
4. No phase depends on a design that is still in-flight (v46–v50 for teach mode)
5. The total phase count is reasonable (not bloated beyond execution feasibility)
6. The dependency graph has no cycles
7. Every phase that writes events references the correct event types from schema.py
8. Every phase that reads/writes artifacts references the correct artifact from the catalog (v40)

## Success Criteria

1. Gap analysis is complete for all 14 milestones (v14–v27) with before/after scope documented.
2. Updated REQ-ID mappings cover all new design concepts from v40–v44.
3. Updated phase decompositions for v14–v17 reflect all new design decisions with traceable rationale.
4. Updated tracking files (ROADMAP.md, REQUIREMENTS.md, STATE.md, PROJECT.md) are ready to commit.
5. Design traceability matrix connects every v40–v44 decision to its v14–v17 phase impact.
6. Integration verification checklist is complete and all items pass.

## Research Inputs

**All v40–v44 handoff documents:**
- `.planning/research/v40-handoff.md` — Hierarchy & Artifact System
- `.planning/research/v41-handoff.md` — Agent Harness & Context Control
- `.planning/research/v42-handoff.md` — Build Quality Pipeline
- `.planning/research/v43-handoff.md` — Workflow Orchestration & GSD Port Map
- `.planning/research/v44-handoff.md` — Rust DB & RTK

**All original milestone plans:**
- `.planning/milestones/v14/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v15/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v16/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v17/ROADMAP.md` + `REQUIREMENTS.md` + `STATE.md`
- `.planning/milestones/v18/` through `v24/` — for teach-mode gap analysis
- `.planning/milestones/v25/` through `v27/` — for tier 4 gap analysis

**Master tracking files:**
- `.planning/ROADMAP.md` — current master roadmap
- `.planning/REQUIREMENTS.md` — current requirements
- `.planning/STATE.md` — current state
- `.planning/PROJECT.md` — project definition

**Shipped code for consistency check:**
- `src/state_core/schema.py` — verify new REQ-IDs align with event types
- `src/state_build/kernel.py` — verify FSM design aligns with current skeleton
- `src/state_build/mcp.py` — verify MCP tool stubs align with new design

## Key Questions for Discuss-Phase

1. **Phase expansion tolerance**: Some milestones are expanding significantly (v14: 11→15, v16: 14→18). Is there a maximum acceptable phase count per milestone? At what point should a milestone be split?

2. **v12/v13 impact**: As v12/v13 execute in parallel, they may produce MCP tool registrations that constrain the v14+ design. How do we handle conflicts if v12/v13 decisions don't match the v45 rewrite?

3. **GSD port completeness**: Some GSD commands are being redesigned rather than ported. At what point is a redesign so different it's effectively a new command? Should the old GSD name be retained for familiarity, or given a new name to signal the redesign?

4. **Documentation scope creep**: v27's documentation list is growing (hierarchy guide, harness guide, quality pipeline guide, GSD migration guide, RTK guide). Are all needed for launch? Which can be post-launch?

5. **Milestone renumbering**: The original milestones are v14–v27. With v40–v50 inserted, do we renumber v14→v28 and shift everything up? Or keep v14–v27 as-is and just update their content?

## Dependencies

- **v40, v41, v42, v43, v44** — ALL MUST be complete. This milestone synthesizes their output.
- **Original v14–v27 milestone plans** — all exist, need to be read.
- **Master tracking files** — all exist, need to be read.

## Scope Boundaries

**In scope:**
- Gap analysis for v14–v27
- Updated REQ-IDs
- Updated phase decompositions for v14–v17
- Updated tracking files
- Design traceability matrix
- Integration verification checklist

**Out of scope:**
- Any implementation
- Teach mode gap analysis detail (v50 does this)
- New milestone creation (this milestone PRODUCES the specs; `gsd-new-milestone` creates them)
