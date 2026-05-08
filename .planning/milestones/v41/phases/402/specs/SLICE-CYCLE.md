# Slice Cycle (Canonical, v41)

**Phase:** 402
**Status:** Canonical (v41)
**Supersedes:** TIER-SLICE.md cycle-ownership ambiguity (v40 Phase 400)
**Requirements covered:** SLC-01..07

---

## Overview

The **Slice tier owns the canonical four-stage cycle**: design-slice → research-slice → run-slice → verify-slice. The Step tier is a **leaf artifact** (a flat `stepNPLAN.md` / `stepNSUMMARY.md` file inside the Slice folder), not a cycle of its own. This locks D-1 of the v41 HANDOFF (which resolved v40's cycle-ownership ambiguity in favor of Slice) and binds SLC-01.

This document is the single source of truth for the four-stage Slice cycle, the canonical Slice folder layout, the per-stage stage-boundary events, and the v40→v41 vocabulary reconciliation. Every downstream v41 phase (Phases 403–406) and the v14 Build Kernel implementation cite this doc.

**Build-mode only.** Teach-mode harness is v47 scope; mode silos remain physical (`state.build.*` must not import `state.teach.*`). Nothing in this document constitutes a Teach-mode contract.

---

## Stage Sequencing & Re-Entry Semantics

The four stages run in a fixed forward order: **design-slice → research-slice → run-slice → verify-slice**. Re-entry into a prior stage is permitted only via the explicit transitions enumerated below; ad-hoc back-stepping is prohibited (the proof-gate at each stage boundary enforces forward-only progress unless an explicit re-entry event fires).

| From → To | Trigger | Rationale |
|---|---|---|
| `design-slice` → `research-slice` | `state.slice.design_completed` lands; Slice is in `worktree_ready` after worktree bootstrap | Forward path. design-slice must finish before research-slice starts. |
| `research-slice` → `research-slice` (planning sub-stage replays) | `N-VALIDATION.md` truth-table fails; D-12 from HANDOFF.md | Internal pipeline replay; does NOT re-enter design-slice. |
| `research-slice` → `run-slice` | `state.slice.research_completed` lands (validation sub-stage passes) | Forward path. |
| `run-slice` → `run-slice` (intra-Slice compaction) | Context-pressure threshold cross per CTX-04 (≤25% emergency or ≤35% warning) | Stays in run-slice; same session_id; uses opencode `session.compacting` hook per CTX-03. |
| `run-slice` → `verify-slice` | `state.slice.run_completed` lands (every `stepNSUMMARY.md` on disk + Slice `must_haves` checks pass) | Forward path. |
| `verify-slice` → `run-slice` | `N-VERIFICATION.md` truth-table fails; agent re-runs the failing Step(s) under run-slice | Re-entry; intra-Slice. The Slice does not exit to the outer FSM until verify passes. |
| `verify-slice` → outer FSM `shipped` | `state.slice.verify_completed` lands; outer composite-state guard from D-19 (Slice's `state.slice.shipped` event) fires | Slice is complete; downstream Slices unblock. |

A Slice is **revertable** at any point via the outer FSM `state.slice.reverted` event from v40 TIER-SLICE.md; revert destroys the worktree and returns the Slice to `planned`. A re-planned Slice re-enters the cycle at design-slice (the four-stage cycle restarts from the beginning). Block / deferment semantics from v40 (D-13/D-14/D-15) operate on the outer Slice FSM and are orthogonal to the four-stage cycle defined here.

---

## Vocabulary Reconciliation (v40 ↔ v41)

The v41 REQUIREMENTS document (drafted before Phase 402's reconciliation) used a slightly different stage-name vocabulary than v40 Phase 400. **v40 vocabulary wins.** References to v41 REQUIREMENTS' `discuss-slice/plan-slice/execute-slice` resolve to the canonical terms via this table:

| v41 REQUIREMENTS term | Canonical (Phase 402) term |
|---|---|
| `discuss-slice` | `design-slice` |
| `plan-slice` (multi-stage internal pipeline) | `research-slice` |
| `execute-slice` | `run-slice` |
| `verify-slice` | `verify-slice` |
| `N-CONTEXT.md` | `DESIGN.md` |
| `N-DISCUSSION-LOG.md` | `DECISIONS.md` (reuses v40 D-401-02 artifact) |
| `stepNN-PLAN.md` | `stepNPLAN.md` (v40 D-04 form; no leading zeros) |

v40 vocabulary wins. References to v41 REQUIREMENTS' `discuss-slice/plan-slice/execute-slice` resolve to the canonical terms via this table. Downstream readers translating in either direction MUST use this mapping.

---

## The Four Stages

Each stage of the Slice cycle has exactly one owner, an explicit input set, an explicit output artifact set, and exactly one stage-boundary event that signals stage completion. The four stages run **sequentially within a Slice** (the agent does not parallelize across stage boundaries; intra-stage parallelism is allowed where noted).

### design-slice

- **Owner:** design-slice agent (build-mode `/state-design-slice` command).
- **Inputs:**
  - Parent Stage's `CRIT.md` (non-negotiables) and `STAGE.md` (scoping intent)
  - Parent Phase's narrative state (background, prior decisions)
  - Any user message context provided at Slice creation time
  - Cross-Slice references via `depends_on` edges from `SLICE.md` frontmatter
- **Outputs:**
  - `DESIGN.md` — XML-tagged sections (`<domain>`, `<decisions>`, `<canonical_refs>`, `<code_context>`, `<deferred>`) capturing the design space, locked decisions, and reference inventory.
  - `DECISIONS.md` — append-only log of locked design decisions (reuses v40 D-401-02 artifact; receives further appends during run-slice).
- **Stage-boundary event:** `state.slice.design_completed` (NEW in v41 — added in Phase 402; v40 EVENT-TAXONOMY.md gets v41 amendment in Plan 03)
- **REQ-IDs covered:** SLC-02

### research-slice

`research-slice` is a **multi-stage internal pipeline** with four sub-stages (research → pattern-mapping → planning → validation), each producing exactly one artifact. The pipeline runs sequentially within the single research-slice stage; if validation fails, the pipeline re-runs from the planning sub-stage (D-12 from HANDOFF.md).

- **Owner:** research-slice agent (build-mode `/state-research-slice` command); subagent fanout is permitted at sub-stage granularity per SUB-04.
- **Inputs:**
  - `DESIGN.md` and `DECISIONS.md` from design-slice
  - Parent Stage's `CRIT.md`
  - Reference material declared in `<canonical_refs>` of `DESIGN.md`
  - Codebase grep targets enumerated in design-slice
- **Sub-stage 1 — research:**
  - **Inputs:** `DESIGN.md` (`<canonical_refs>` section), reference material citations, library/framework candidates declared in design-slice.
  - **Output:** `N-RESEARCH.md` — library / pattern / alternative evaluation.
- **Sub-stage 2 — pattern-mapping:**
  - **Inputs:** `N-RESEARCH.md` (output of sub-stage 1), the in-repo pattern catalog (existing v6 middleware, v7 hooks, v8 plugin shim, v40 artifact catalog), and `<code_context>` from `DESIGN.md`.
  - **Output:** `N-PATTERNS.md` — established-pattern citations and re-use proposals.
- **Sub-stage 3 — planning:**
  - **Inputs:** `N-RESEARCH.md`, `N-PATTERNS.md`, the Slice's `must_haves` proof-gate contract from frontmatter (PRF-01), and the parent Stage's `CRIT.md`.
  - **Output:** `stepNPLAN.md` (one per Step; 1..M) — GSD-shape Step PLAN files (YAML frontmatter + XML body) per STP-01..STP-05; Step granularity auto-selected per STP-06 against the 200k Slice budget.
- **Sub-stage 4 — validation:**
  - **Inputs:** All `stepNPLAN.md` files produced by sub-stage 3, plus the Slice's `must_haves` contract.
  - **Output:** `N-VALIDATION.md` — plan-check truth table. On failure (any check fails), the validation sub-stage triggers the planning sub-stage to re-run (D-12); the new attempt overwrites the prior `stepNPLAN.md` set and `N-VALIDATION.md` is re-written.
- **Stage-boundary event:** `state.slice.research_completed` (NEW in v41 — added in Phase 402; v40 EVENT-TAXONOMY.md gets v41 amendment in Plan 03). Emitted only after the validation sub-stage passes.
- **REQ-IDs covered:** SLC-03

### run-slice

`run-slice` runs each Step's `stepNPLAN.md` per DAG ordering. Steps within a Slice are dispatched serially by the agent (the scheduler's job ends at the Slice boundary; intra-Slice ordering is the agent's responsibility per D-11 of v40). Each Step's individual lifecycle (designing → planning → running → verifying → done from v40 EVENT-TAXONOMY) runs intra-`run-slice`, NOT as its own outer Slice-level cycle (see §"Step is a Leaf Artifact" below).

run-slice runs the Steps in `stepNPLAN.md` order (intra-Slice DAG ordering is encoded in the Step PLAN frontmatter `depends_on`), opening a fresh executor session per Slice (CTX-02). On context pressure within the Slice, run-slice drives the intra-Slice compaction cycle defined in CONTEXT-PROTOCOL.md (CTX-03..04) without leaving the run-slice stage. On successful completion of every Step, the Slice's `must_haves` proof-gate (PRF-01) runs against the on-disk artifact set; only then does the stage-boundary event fire.

- **Owner:** run-slice agent (build-mode `/state-run-slice` command); subagent fanout permitted per Step per SUB-04.
- **Inputs:**
  - `stepNPLAN.md` for each Step in the Slice
  - All `provides:` blocks from upstream-resolved Step `stepNSUMMARY.md` files
  - Active worktree path (one per Slice; bootstrapped at `state.slice.worktree_ready`)
  - Parent Slice's `DECISIONS.md` (read-only during run; appended only on Rule-4 architectural decisions per DEV-04)
- **Outputs:**
  - `stepNSUMMARY.md` — one per Step (1..M). Step-level completion documentation per v40 D-401-09 / D-401-02.
  - Append-only updates to `DECISIONS.md` for Rule-4 architectural deviations.
  - Code commits in the Slice's worktree (one or more per Step; semantic commit prefixes per v40 D-04).
- **Stage-boundary event:** `state.slice.run_completed` (NEW in v41 — added in Phase 402; v40 EVENT-TAXONOMY.md gets v41 amendment in Plan 03). Emitted when every `stepNSUMMARY.md` for the Slice is on disk and the Slice's `must_haves.{truths, artifacts, key_links}` checks pass per PRF-01..05.
- **REQ-IDs covered:** SLC-04

### verify-slice

- **Owner:** verify-slice agent (build-mode `/state-verify-slice` command).
- **Inputs:**
  - `stepNSUMMARY.md` for every Step in the Slice
  - Slice-level `<verification>` block declared in the Slice's design artifacts
  - Each Step's task-level `<verify><automated>` results from run-slice
  - Truth-table contract from `must_haves.truths` (Slice frontmatter)
- **Outputs:**
  - `N-VERIFICATION.md` — slice-level truth table. Pure-machine checks (bash exit codes, file existence, line counts, regex matches per PRF-04). No LLM-as-judge.
- **Stage-boundary event:** `state.slice.verify_completed` (NEW in v41 — added in Phase 402; v40 EVENT-TAXONOMY.md gets v41 amendment in Plan 03). This event is the **slice-complete signal** per SLC-05; downstream Slices waiting on this Slice's `depends_on` edges unblock on this event.
- **REQ-IDs covered:** SLC-05

---

## Canonical Slice Folder Layout (SLC-06 amended)

The canonical Slice folder layout amends SLC-06 (which was originally drafted using v41 REQUIREMENTS vocabulary `N-CONTEXT.md` / `N-DISCUSSION-LOG.md`). Per the vocabulary table above, those v41 artifacts are renamed to v40 vocabulary (`DESIGN.md` / `DECISIONS.md`).

```
slices/N-name/
  DESIGN.md            (design-slice)
  DECISIONS.md         (design-slice + run-slice append-only)
  N-RESEARCH.md        (research-slice / research stage)
  N-PATTERNS.md        (research-slice / pattern-mapping stage)
  stepNPLAN.md         (research-slice / planning stage; 1..M)
  N-VALIDATION.md      (research-slice / validation stage)
  N-UI-SPEC.md         (optional, frontend Slices)
  stepNSUMMARY.md      (run-slice; 1..M)
  N-VERIFICATION.md    (verify-slice)
  deferred-items.md    (out-of-scope findings; per SRP-06)
  RESUME.txt           (cross-session orientation pointer)
```

Per-artifact producer-stage table (grep-greppable cross-reference):

| Artifact | Producing Stage |
|---|---|
| `DESIGN.md` | design-slice |
| `DECISIONS.md` | design-slice (initial) + run-slice (append-only on Rule-4 architectural deviations) |
| `N-RESEARCH.md` | research-slice / research sub-stage |
| `N-PATTERNS.md` | research-slice / pattern-mapping sub-stage |
| `stepNPLAN.md` | research-slice / planning sub-stage (one per Step; 1..M) |
| `N-VALIDATION.md` | research-slice / validation sub-stage |
| `N-UI-SPEC.md` | research-slice (optional; frontend Slices only) |
| `stepNSUMMARY.md` | run-slice (one per Step; 1..M) |
| `N-VERIFICATION.md` | verify-slice |
| `deferred-items.md` | run-slice (append-only out-of-scope findings; SRP-06) |
| `RESUME.txt` | run-slice (cross-session orientation pointer; rewritten on each session resume) |

This layout supersedes SLC-06's v41 form (`N-CONTEXT.md` / `N-DISCUSSION-LOG.md`); those v41 artifacts are renamed to v40 vocabulary (`DESIGN.md` / `DECISIONS.md`) per the vocabulary table.

---

## Stage-Boundary Events

Each Slice stage emits exactly one stage-boundary event when it completes. All four are **NEW in v41** and must be added to v40 EVENT-TAXONOMY.md via Plan 03's amendment work. Event-naming follows the existing v40 `state.slice.*` convention; payload-field shape follows the v40 EVENT-TAXONOMY pattern, adapted to `Aggregate` (slice id) since stage-boundary events are intra-Slice and do not move the Slice's outer FSM.

| Event Type | Trigger | Aggregate | Data Fields |
|---|---|---|---|
| `state.slice.design_completed` (NEW in v41 — to be added to v40 EVENT-TAXONOMY.md via Plan 03 amendment) | design-slice agent finishes writing `DESIGN.md` and the initial `DECISIONS.md` | Slice (`slice_id: str`) | `slice_id: str`, `stage: Literal["design", "research", "run", "verify"]` (= `"design"` here), `produced_artifacts: list[str]` (relative paths under the Slice folder, e.g., `["DESIGN.md", "DECISIONS.md"]`), `completed_at: datetime` |
| `state.slice.research_completed` (NEW in v41 — to be added to v40 EVENT-TAXONOMY.md via Plan 03 amendment) | research-slice validation sub-stage passes | Slice (`slice_id: str`) | `slice_id: str`, `stage: Literal["design", "research", "run", "verify"]` (= `"research"` here), `produced_artifacts: list[str]` (e.g., `["N-RESEARCH.md", "N-PATTERNS.md", "step1PLAN.md", "step2PLAN.md", "N-VALIDATION.md"]`), `completed_at: datetime` |
| `state.slice.run_completed` (NEW in v41 — to be added to v40 EVENT-TAXONOMY.md via Plan 03 amendment) | run-slice produces all `stepNSUMMARY.md` files and Slice `must_haves` checks pass | Slice (`slice_id: str`) | `slice_id: str`, `stage: Literal["design", "research", "run", "verify"]` (= `"run"` here), `produced_artifacts: list[str]` (e.g., `["step1SUMMARY.md", "step2SUMMARY.md"]`), `completed_at: datetime` |
| `state.slice.verify_completed` (NEW in v41 — to be added to v40 EVENT-TAXONOMY.md via Plan 03 amendment) | verify-slice writes `N-VERIFICATION.md` truth table with all checks passing | Slice (`slice_id: str`) | `slice_id: str`, `stage: Literal["design", "research", "run", "verify"]` (= `"verify"` here), `produced_artifacts: list[str]` (e.g., `["N-VERIFICATION.md"]`), `completed_at: datetime` |

`state.slice.verify_completed` is the **slice-complete signal** per SLC-05. Downstream Slices whose `depends_on` edges target this Slice unblock when this event lands in the event store.

All four stage-boundary events have minimum-required field set: `slice_id: str`, `stage: Literal["design", "research", "run", "verify"]`, `produced_artifacts: list[str]` (relative paths under the Slice folder), `completed_at: datetime`. Pydantic models (`extra="forbid"`) shipping these events are defined in v14 Build Kernel; Phase 402 owns the schema contract here.

---

## Step is a Leaf Artifact (D-1 / SLC-01 explicit)

Steps are **flat files** (`stepNPLAN.md`, `stepNSUMMARY.md`) inside the Slice folder. Steps do **NOT** own their own four-stage cycle. The Step "FSM" tracked in v40 EVENT-TAXONOMY (`state.step.designed/planned/ran/verify_passed`) is **intra-`run-slice`** granularity (run-slice runs each Step PLAN through its individual lifecycle), not a separate Slice-level cycle. The four-stage cycle (design / research / run / verify) is owned exclusively by the Slice tier; the Step tier owns only an internal lifecycle that lives entirely within the run-slice stage. v40 TIER-STEP.md receives a v41 amendment forward-pointer to this section in Plan 03.

---

## Cycle Invariants

The following invariants are canonical commitments. v14 Build Kernel implements against them; CI enforces each via grep / lint / test gates as the implementation lands.

1. **Stage ownership is one-to-one.** Each stage has exactly one owning agent role and exactly one stage-boundary event. No stage emits the boundary event of another stage.
2. **Stage-boundary events are forward-only by default.** Re-entry is permitted only via the table in §"Stage Sequencing & Re-Entry Semantics". Out-of-band stage-boundary events are rejected by the daemon's middleware (mode-enforcement layer plus a new stage-boundary-validation layer added in v14).
3. **Step is a leaf, always.** No Step emits a stage-boundary event. The Step FSM transitions (`state.step.*`) are intra-`run-slice` and do not move the Slice's outer FSM.
4. **One worktree per Slice.** The worktree is bootstrapped at `state.slice.worktree_ready` (before design-slice runs in the worktree; design-slice runs in the worktree per v40 D-04). All four stages share the single worktree; verify-slice does not spawn a new worktree.
5. **`stepNPLAN.md` is mutable-with-audit-log within run-slice; immutable in verify-slice.** Per PAP-03, the executor may edit mutable sections of a `stepNPLAN.md` during run-slice; once `state.slice.run_completed` fires, the Step PLAN files become read-only for verify-slice. PAP-04 emits a `plan_edit` event for every edit; PAP-05 blocks edits to immutable sections.
6. **Slice token budget is 200k absolute (CTX-01).** Independent of the active model's context window. research-slice / planning sub-stage sizes the Step set to ≤80% of budget (~160k of executor work); run-slice's intra-Slice compaction cycle (CTX-03..04) keeps the executor below the threshold.
7. **All proof checks are pure-machine (PRF-04).** Bash exit codes, file existence, line counts, regex matches. No LLM-as-judge anywhere in any stage's stage-boundary check or in `N-VERIFICATION.md`.

---

## Step is a Leaf Artifact: Forward-Pointer to Plan 03

Plan 03 amends `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` with a forward-pointer block citing the §"Step is a Leaf Artifact (D-1 / SLC-01 explicit)" section above. The amendment text reads:

> **v41 Amendment.** Per `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` §"Step is a Leaf Artifact (D-1 / SLC-01 explicit)", Step is a leaf artifact and does not own its own four-stage cycle. The Step FSM defined in this document (`state.step.designed/planned/ran/verify_passed`) is intra-`run-slice` granularity. The Slice tier owns the four-stage cycle (design-slice → research-slice → run-slice → verify-slice). See SLICE-CYCLE.md for the canonical model.

Plan 03 grep-confirms the amendment lands at the bottom of TIER-STEP.md without altering prior v40 content.

---

## v40 Amendment Targets

The following v40 docs receive a `## v41 Amendment` block as part of Plan 03's amendment work. This list is the canonical checklist for Plan 03; the planner of Plan 03 confirms each amendment lands.

- `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — clarifies Slice owns the four-stage cycle (was: cycle ownership ambiguous between Slice and Step).
- `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — forward-pointer that Step is a leaf artifact, with the Step-level FSM clarified as intra-`run-slice` rather than an outer Step-owned cycle.
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — adds the four `state.slice.{design,research,run,verify}_completed` events listed in §"Stage-Boundary Events".
- `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — confirms cascade stops at Slice (Step is leaf, no Step-owned cycle); the `state.slice.shipped` composite-state guard from D-19 stays as written.
- `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — pointer addition: SLC-06 layout (this doc §"Canonical Slice Folder Layout") supersedes any conflicting layout fragment.
- `.planning/milestones/v40/phases/401/specs/DIRECTORY-TREE.md` — pointer addition: same as above.
- `.planning/milestones/v40/phases/401/specs/CROSS-REFERENCES.md` — pointer addition only if Slice-cycle wording in CROSS-REFERENCES.md conflicts with the canonical model here; Plan 03 grep-confirms before amending.

---

## Requirements Coverage

| REQ-ID | Section in this doc | Notes |
|---|---|---|
| SLC-01 | §Overview, §"Step is a Leaf Artifact (D-1 / SLC-01 explicit)" | Slice owns the four-stage cycle; Step is a leaf artifact. Corrects v40 Phase 400 ambiguity. |
| SLC-02 | §"The Four Stages" / `### design-slice` | design-slice produces `DESIGN.md` + `DECISIONS.md` (renamed from v41 REQUIREMENTS' `N-CONTEXT.md` / `N-DISCUSSION-LOG.md` per the vocabulary table). |
| SLC-03 | §"The Four Stages" / `### research-slice` | research-slice is a multi-stage internal pipeline (research → pattern-mapping → planning → validation) producing four artifacts; validation re-runs planning on failure. |
| SLC-04 | §"The Four Stages" / `### run-slice` | run-slice runs each Step's `stepNPLAN.md` per DAG ordering and writes `stepNSUMMARY.md`. |
| SLC-05 | §"The Four Stages" / `### verify-slice`, §"Stage-Boundary Events" | verify-slice writes `N-VERIFICATION.md` and emits `state.slice.verify_completed` (the slice-complete signal). |
| SLC-06 | §"Canonical Slice Folder Layout (SLC-06 amended)" | Slice folder layout enumerated with each artifact's producing stage; supersedes the v41 REQUIREMENTS form. |
| SLC-07 | §"v40 Amendment Targets" | v41 amends Phase 400 spec docs in-line so Slice-owns-cycle is canonical going forward; affected docs receive a `## v41 Amendment` header per Plan 03's checklist. |

---

## Cross-References

- `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — sibling doc (Plan 02). Defines the 200k absolute Slice budget, threshold action table, compaction snapshot Pydantic schema, reinject payload shape, and identifier-survival contract that govern context across the Slice cycle defined here.
- `.planning/milestones/v41/REQUIREMENTS.md` — REQ source (SLC-01..07; CTX-01..09; STP-01..08; PAP-01..06; PRF-01..07).
- `.planning/milestones/v41/HANDOFF.md` — D-1 (Slice owns the four-stage cycle) and D-12 (research-slice validation re-runs planning on failure) are cited in §Overview and §"The Four Stages" / `### research-slice` respectively.
- `.planning/milestones/v40/phases/400/specs/TIER-SLICE.md` — target of v41 amendment per §"v40 Amendment Targets"; Slice tier behavioral definition that this doc clarifies on cycle-ownership.
- `.planning/milestones/v40/phases/400/specs/TIER-STEP.md` — target of v41 amendment forward-pointer; Step-as-leaf framing.
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — target of v41 amendment for the four new stage-boundary events listed in §"Stage-Boundary Events".
- `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — target of v41 amendment confirming cascade stops at Slice.
