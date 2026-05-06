# Project Research Summary

**Project:** state — v40 Build Hierarchy & Artifact System Architecture (Design-Phase Milestone)
**Domain:** Multi-tier product hierarchy (Arc → Phase → Slice → Step) for event-sourced agentic workflow engine
**Researched:** 2026-05-06
**Confidence:** HIGH on event-sourcing integration, CQRS projection, and hierarchy patterns (code read directly); MEDIUM on naming convention details and on-disk layout tradeoffs (tension between ARCHITECTURE.md and PITFALLS.md recommendations)

## Executive Summary

State's four-tier hierarchy (Arc → Phase → Slice → Step) replaces GSD's flat two-tier milestone→phase model with a richer decomposition that separates scope, concurrency, and the full discuss→plan→execute→verify cycle into distinct tiers. Every tier is an independent CQRS aggregate with its own event types, state machine, projector handlers, and on-disk artifacts. The event store (events.sqlite) is the single source of truth at every tier; STATE.md files at each level are projector-rebuilt projections, never agent-written — directly eliminating the GSD problem where agents forget to update tracking files.

The research across four parallel domains (stack, features, architecture, pitfalls) converges on a clear recommendation: define the four-tier hierarchy using Pydantic v2 models and Mermaid diagrams as the design contract, enforce machine-generated hierarchical IDs (`arc-001/phase-003/slice-012/step-004`), keep tier state machines simple (Arc: 3-4 states, Phase: 4-5, Slice: 4-5, Step: 8), and use a hybrid tree+DAG model where structural hierarchy is a tree (one parent per node) but execution ordering is a DAG (typed `depends_on` edges). Cross-tier coordination flows upward through composite events emitted by the daemon, never through cross-tier `depends_on` edges that would create deadlock cycles.

Three critical design tensions emerged across the research files and must be resolved during the v40 discuss-phase: (1) whether on-disk STATE.md files exist per-directory (ARCHITECTURE.md) or as consolidated JSON projections (PITFALLS.md), (2) whether canonical IDs are sequential integers (ARCHITECTURE.md) or UUIDs/ULIDs (PITFALLS.md), and (3) whether Step artifacts are separate files (DISCUSS.md, PLAN.md, VERIFY.md, EXECUTE.log) or consolidated into a single ARTIFACTS.md (PITFALLS.md). These are explicitly flagged below as discuss-phase agenda items.

## Key Findings

### Design Stack (from STACK.md)

The v40 design-phase milestone uses a documentation and specification stack, not a runtime stack. The recommended tools:

**Core technologies:**
- **Mermaid state diagrams + C4 diagrams** — All architecture and state machine visualization. Zero-dependency text format; renders in VS Code, GitHub, opencode. C4 diagrams (C4Context/C4Container/C4Component) are marked experimental upstream but sufficient for design docs. Fallback: Structurizr DSL export to Mermaid if C4 proves insufficient.
- **Pydantic v2 `BaseModel` with `extra="forbid"`** — Formal artifact schemas. The same models that validate frontmatter at creation time serve as the design contract. `model_json_schema()` emits JSON Schema for cross-language use. Already proven in state's runtime event schemas (34+ event types).
- **Python `Enum` + `Literal`** — State name enumerations, event type enumerations, guard condition lists. Type-safe, IDE-auto-completing, importable at runtime.
- **YAML frontmatter in Markdown** — Human-readable artifact metadata. GSD convention carried forward. Every `.md` artifact has a Pydantic-validated frontmatter block.

**Rejected for design docs:** XState v5 (JS-only, no Python runtime), SCXML (XML-based, verbose, no Python ecosystem), Structurizr DSL (Java toolchain adds friction), PlantUML (requires JVM renderer), Arc42 (overly formal 12-section template), OpenAPI (category error for artifact schemas).

### Feature Landscape (from FEATURES.md)

**Table stakes (every tier must support):**
- Unique stable ID per artifact + human-readable slug (display-only)
- Per-tier state machine with event-driven transitions
- Typed dependency edges (`blocks`, `soft`, `data`)
- DAG cycle validation on edge insert
- Per-tier status rollup (parent aggregates child states)
- Path-based discovery + ID-based lookup + parent-chain navigation

**Differentiators (what makes state's hierarchy great):**
- **Projector-built STATE.md at every tier** — Agents NEVER write STATE.md directly. The daemon's CQRS projector rebuilds all STATE.md files from the event stream on every state change. This eliminates the #1 tracking problem in agentic systems.
- **Typed dependency DAG with descope awareness** — Three edge kinds (`blocks`, `soft`, `data`) with full DFS cycle detection. Scheduler handles abandoned/descoped nodes by surfacing dependents rather than silently blocking.
- **Stable identity with decimal insertions** — Machine-sortable sequential IDs support gap-closure inserts (`phase-003.1` between 003 and 004) without renumbering. IDs survive renames; slugs are display-only.
- **Tiered immutability** — STEP.md plan freezes when execution begins. ARC.md goal/success_criteria freeze when the first child Phase enters `in_progress`.
- **Canonical artifact catalog** — Single registry of every recognized artifact with schema validation on read.

**Anti-features (explicitly NOT building):**
- Agent-written tracking files (projector-only)
- Arbitrary "relates to" graph links (typed edges only)
- Deeply nested decimal insertions (cap at one decimal layer)
- Mixed agent/projector field ownership (clear ownership per field)
- Five+ tiers or dynamic tier creation (four fixed tiers)

**Cross-referencing pattern:** ID-based with path lookup. Every cross-reference stores the target's unique ID (survives renames). The projector maintains an ID→path index in SQLite. Hybrid model: structural hierarchy is a tree (one parent per node), execution ordering is a DAG (`depends_on` edges across the tree).

**MVP priority (for v40 design spike):**

| Priority | What to Specify |
|----------|----------------|
| **Must (Phase 1)** | Tier state machines, artifact catalog, naming conventions, on-disk layout, cross-referencing rules |
| **Should (Phase 2)** | STATE.md projection schemas, consistency validator, artifact immutability rules, decimal insertion protocol |
| **Defer** | Agent harness (v41), quality pipeline (v42), GSD command porting (v43), teach-mode equivalents (v46) |

### Architecture Approach (from ARCHITECTURE.md)

The four-tier hierarchy integrates with every existing subsystem in state. The fundamental insight: each tier is a CQRS aggregate with its own event stream, projector handler, and on-disk artifacts.

**Major components and their tier integration:**

1. **Event Store** — Each tier is an aggregate type. Arc/Phase events carry parent IDs. Daemon emits composite events for cross-tier rollup (Step→Slice→Phase→Arc cascade via post-commit callbacks). Hierarchical aggregate IDs (`arc-01/phase-03/slice-12/step-004`) make parent extraction trivial via prefix parsing.

2. **CQRS Projector** — New cache tables for `arcs` and `phases` (extending existing `steps`, `slices`, `concepts`). New projection handlers for Arc/Phase aggregate events. Projector rebuilds STATE.md files at every tier on daemon startup. `validate_consistency()` function detects drift between filesystem STATE.md and event-store state.

3. **DAG Scheduler** — Extended to handle four-tier nodes. Scheduler reads `depends_on` edges from SLICE.md and STEP.md frontmatter. Frontier computation includes Slice nodes. Slice dispatch triggers worktree creation, then dispatches Steps serially within the Slice. Cross-Phase Slice dependencies supported via fully-qualified IDs.

4. **Worktree Service** — Unchanged model: one worktree per Slice. Steps execute serially within the Slice's single worktree. Worktree naming follows hierarchical ID convention. Parallel work requires separate Slices.

5. **MCP Tools** — Follow `state_build__{tier}_{action}` naming convention. Tier-scoped: Arc tools (roadmap, retire), Phase tools (verify, complete), Slice tools (ship, revert), Step tools (discuss, plan, execute, verify). Cross-tier tools (dag_show, progress, health) use no tier prefix.

6. **TUI (`@state/opencode-plugin`)** — Four-tier expandable tree in sidebar with status icons. DAG viewer renders all four tiers with hierarchical grouping. Statusline shows active hierarchy path (`build | arc-02:auth | phase-01:oauth | slice-12:anthropic | step-004:verify | DONE`).

**Key design decisions (with recommendations):**
- Hierarchical slash-delimited aggregate IDs (YES)
- Daemon emits composite events for rollup, not synchronous nested writes (YES)
- STATE.md at every tier (YES — projector-rebuilt, throwaway)
- Sequential per-parent numeric IDs with decimal insertion (Arc/Phase: no decimals; Slice/Step: one decimal layer)
- `depends_on` edges at both Slice and Step levels
- Steps always serial within a Slice; parallel work requires separate Slices
- Cross-Arc and cross-Phase dependencies allowed via fully-qualified IDs

### Critical Pitfalls (from PITFALLS.md)

Nine critical pitfalls identified, ranked by severity and likelihood:

1. **Hierarchy Over-Engineering — Too Many Tiers, Too Many States** — Cap states per tier: Arc (3), Phase (4), Slice (4-5), Step (8 max). No substates at Arc/Phase/Slice. If you find yourself wanting a substate, the dependency DAG should handle it, not the state machine. Total states across all 4 tiers should be ≤ 20.

2. **Under-Specified Cross-Referencing — Orphan Artifacts** — Use UUIDs/ULIDs as canonical IDs (not human-readable slugs). Include content hashes in cross-references to detect drift. Run `validate_consistency` as a daemon post-commit hook (not a manual CLI command). Broken references become `state.reference.broken` events that trigger TUI toasts immediately.

3. **Inconsistent State Machine Behavior Across Tiers** — Define explicit composite state rules for each parent-child pair (e.g., "Arc is `shipped` if ALL Phases are `shipped`"). These rules live in the projector (CQRS read-side), not in the FSM (command-side). No tier should have a `BLOCKED` state if a child tier already has one — let the projector compute "effectively blocked" from child states.

4. **Naming Convention Drift** — Machine-enforce ID generation via CLI commands. IDs are globally unique hierarchical integers (`arc-001-phase-003-slice-012-step-004`). Slugs are display-only metadata in frontmatter. Directory names use slugs for human browsing; cross-references use IDs. No human-chosen slugs as canonical identifiers.

5. **On-Disk Layout Proliferation** — Flatten where possible. Consolidate DISCUSS.md, PLAN.md, VERIFY.md, EXECUTE.log into a single `ARTIFACTS.md` per Step. No per-directory STATE.md files (use consolidated JSON projections under `.state/build/state/`). Snapshots are content-addressed under a shared pool. File count reduction: ~8,200 → ~2,480 for a typical project.

6. **Frontmatter Schema Bloat** — Tier-specific field budgets (ARC.md: 6 required/4 optional; PHASE.md: 7/5; SLICE.md: 7/5; STEP.md: 10/8). Frontmatter is for machine-readable metadata, not prose (>200 chars = belongs in body). Temporal data (snapshot history, cost accounting) lives in events.sqlite, not frontmatter.

7. **Over-Coupling to GSD's Legacy Hierarchy Model** — Define tiers by behavioral primitives, not GSD analogies. Explicit anti-GSD rules: no linear roadmap (DAG of Arcs), no "verification at the end" (continuous per-tier), no "one active thing at a time" (concurrent Slices across Arcs), no `.planning/` monolith (federated `.state/build/` tree).

8. **State Machine Deadlocks — Cross-Tier Blocking** — DAG edges only point child→parent, never parent→child. Cross-tier coordination is event-driven, not dependency-edge-driven. The scheduler rejects cross-tier edges at creation time. Runtime deadlock detection as a daemon health check.

9. **Artifact Immutability Violations — Mid-Execution Plan Changes** — Tiered freezing rules: STEP.md freezes on `executing` entry, DISCUSS.md/PLAN.md freeze on `planning` entry, SLICE.md's `depends_on` freezes on `worktree_ready` entry, ARC.md's `goal`/`success_criteria` freeze on `in_progress` entry. Daemon HTTP middleware enforces immutability server-side. For necessary changes: abandon and replan via successor artifact.

## Implications for Roadmap

Based on combined research, the v40 design spike should be structured in two phases, followed by implementation milestones v41-v47:

### v40 Phase 1: Tier Definitions & State Machines (Discuss + Specify)

**Rationale:** The tier definitions are the foundation every other artifact depends on. State machines, event taxonomies, and behavioral primitives must be locked before naming conventions or on-disk layouts can be designed. Per PITFALLS.md, the state counts per tier must be capped at design time to prevent over-engineering during implementation.

**Delivers:**
- Arc, Phase, Slice, Step tier specifications (behavioral primitives, NOT GSD analogies)
- State machine diagrams (Mermaid) with all transitions, guards, and events
- Event taxonomy extension (28+ → ~40 events) with composite event definitions
- Tension resolution: tier state counts (cap at Arc:3, Phase:4, Slice:5, Step:8)
- Tension resolution: canonical ID format (sequential vs UUID — discuss-phase decides)

**Addresses features:** Tier identity/lifecycle, event-driven state transitions, parent pointers, state machines mapped to artifact lifecycles

**Avoids pitfalls:** Hierarchy over-engineering (#1), GSD coupling (#7), state machine deadlocks (#8)

**Needs research:** Light — well-understood domain. The discuss-phase should resolve the ID format tension.

---

### v40 Phase 2: Artifact Catalog, Naming, Layout, Cross-Refs (Specify)

**Rationale:** Once tiers are defined, the artifacts that populate them, the conventions that name them, and the cross-references that connect them can be specified. This phase resolves the three major tensions identified across research files.

**Delivers:**
- Complete artifact catalog (every file, schema, owner, cross-refs)
- Naming conventions (ID formats, slug rules, directory naming, MARKER conventions)
- On-disk layout specification (resolves ARCHITECTURE.md vs PITFALLS.md tension)
- Cross-referencing rules (ID-based with path lookup, broken-reference handling)
- Pydantic schema models for every artifact (ArcFrontmatter, PhaseFrontmatter, etc.)
- Tension resolution: STATE.md placement (per-directory vs consolidated JSON)
- Tension resolution: Step file count (separate files vs consolidated ARTIFACTS.md)
- Tension resolution: canonical ID type (sequential numeric vs UUID/ULID)

**Addresses features:** Artifact discovery/navigation, canonical artifact catalog, cross-referencing patterns, naming conventions, on-disk layout, STATE.md consistency model

**Avoids pitfalls:** Cross-reference drift (#2), naming convention drift (#4), on-disk proliferation (#5), frontmatter bloat (#6), artifact immutability violations (#9)

**Needs research:** MEDIUM — the three tensions above need discuss-phase resolution. Decimal insertion depth and descoped-dependency semantics also flagged.

---

### v41-v47 Implementation Ordering Rationale

Based on architecture dependencies extracted from research:

1. **v41 (Agent Harness)** — Consumes artifact schemas produced by v40. Needs the on-disk layout and artifact catalog locked first because the harness reads/writes these files. The harness's `system.transform` hook must know which frontmatter fields are context-relevant (~200 tokens, not ~2000).

2. **v42 (Quality Pipeline)** — Needs the event taxonomy and state machines from v40, plus the harness from v41 to verify agent behavior. The verifier must traverse all 4 tiers for cross-tier rollup verification. Consistency validator (19+ warning codes) is specified in v40 Phase 2.

3. **v43 (GSD Command Porting)** — Maps GSD's commands to state's four-tier model. Per PITFALLS.md pitfall #7, every ported command must be audited for serial execution assumptions and redesigned for DAG-based concurrency.

4. **v44 (Rust DB)** — Independent of hierarchy design. Only needs the event schema from v40 Phase 1.

5. **v46 (Teach-Mode Equivalents)** — Needs the complete build-mode hierarchy (v41-v43) as a template for teach-mode adaptation.

### Research Flags

**Phases needing deeper research during planning:**
- **v40 Phase 2 (Artifact Catalog):** The three tensions (STATE.md placement, ID format, file consolidation) need discuss-phase exploration. Recommended: `/gsd-discuss-phase v40.P2` before planning.
- **v42 (Quality Pipeline):** Cross-tier verification and deadlock detection are novel patterns with sparse prior art. Needs research on verifier architecture for hierarchical state machines.

**Phases with standard patterns (skip research-phase):**
- **v40 Phase 1 (Tier Definitions):** Well-understood domain. CQRS aggregate design, UML state machine patterns, and event taxonomy are documented in existing state codebase and industry sources.
- **v41 (Agent Harness):** Standard plugin architecture. Follows opencode's 9-hook extension surface. The harness design is largely prescribed by opencode's API.
- **v44 (Rust DB):** Standard database design. Independent of hierarchy complexity.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (design tools) | HIGH | Mermaid and Pydantic are mature, verified via official docs v11.14.0 and pydantic.dev. Mermaid C4 is experimental but sufficient for design docs. |
| Features | HIGH | Hierarchy patterns validated against Jira, Azure DevOps, and Linear. State's existing event store, projector, and scheduler code read directly. MEDIUM on descoped-dependency resolution (needs discuss-phase). |
| Architecture | HIGH | Event-store integration, CQRS projector, DAG scheduler, and worktree service code read directly from state's codebase. Composite event flow and cross-tier projection handlers are well-specified. MEDIUM on TUI visualization (inferred from plugin structure). |
| Pitfalls | HIGH | Pitfalls #1, #2, #3, #7, #8, #9 grounded in formalisms (UML HSM, CQRS patterns, Martin Fowler) and direct GSD implementation experience (13 milestones). MEDIUM on #4 (naming drift patterns inferred from large-scale post-mortems), #5 (layout scale concerns are projections, not measured), #6 (schema bloat synthesized from best practices, no dedicated literature). |

**Overall confidence: HIGH**

The four research streams are complementary and internally consistent on the core architecture (CQRS aggregates, composite events, projector-built STATE.md, typed DAG edges, tiered immutability). The tensions that exist (ID format, STATE.md placement, file consolidation) are explicit and scoped — they don't undermine the foundational design but represent implementation detail choices resolvable in discuss-phase.

### Gaps to Address

- **UUID vs sequential IDs:** PITFALLS.md strongly recommends UUIDs for referential integrity; ARCHITECTURE.md recommends sequential per-parent numbers for readability and sortability. Resolve in v40 discuss-phase. Recommendation: sequential integers with decimal insertion, augmented by content-hash cross-references to catch drift (hybrid approach).

- **STATE.md placement:** ARCHITECTURE.md recommends per-directory STATE.md files; PITFALLS.md recommends consolidated JSON projections under `.state/build/state/`. Resolve in v40 discuss-phase. Recommendation: consolidated JSON files for the projector's read cache, with an optional `state build export-state` command that renders per-directory STATE.md on demand for human inspection. This satisfies both the "STATE.md files are throwaway projections" principle and the "don't create 400+ files that are redundant cache" concern.

- **Step file consolidation:** ARCHITECTURE.md lists 5 files per Step (STEP.md, DISCUSS.md, PLAN.md, VERIFY.md, EXECUTE.log); PITFALLS.md recommends consolidating into STEP.md + ARTIFACTS.md (2 files). Resolve in v40 discuss-phase. Recommendation: start with separate files for design clarity (easier tooling, clearer lifecycle), add consolidation as an optimization in v42 if file count becomes a performance problem. The architecture research notes that 2000 Steps at 5 files each = 10,000 files, which is manageable on modern filesystems.

- **Descope semantics:** What happens when a `blocks` dependency is abandoned? Cascade-abandon, assume-satisfied with manual flag, or block-and-surface? Flagged as discuss-phase decision in both FEATURES.md and ARCHITECTURE.md. Recommendation: surface dependents with a health warning (W011) and require explicit `assume_satisfied: true` flag on the dependent's `depends_on` edge to proceed.

## Sources

### Primary (HIGH confidence — code read directly)
- `src/state_core/schema.py` — 34+ event types, aggregate definitions, mode enforcement
- `src/state_core/projector.py` — CQRS projection engine (19 handlers, 3 cache tables)
- `src/state_core/events.py` — Event store API (append, read_stream, post-commit callbacks)
- `src/state_build/kernel.py` — StepMachine skeleton (8 states defined)
- `src/state_core/scheduler.py` — DAG scheduler (frontier, topo_sort, cycle detection)
- `src/state_core/worktree.py` — WorktreeService protocol
- `.planning/PROJECT.md` — Cardinal rules, constraints, architectural decisions
- `.planning/milestones/v40/HANDOFF.md` — Milestone scope, artifact catalog, key questions

### Primary (HIGH confidence — official documentation)
- [Mermaid.js v11.14.0 — State Diagrams](https://mermaid.js.org/syntax/stateDiagram.html)
- [Mermaid.js v11.14.0 — C4 Diagrams](https://mermaid.js.org/syntax/c4.html)
- [Pydantic v2 — Models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic v2 — JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [Azure CQRS Pattern (Microsoft Learn, 2025-02-20)](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)
- [UML State Machine (Wikipedia)](https://en.wikipedia.org/wiki/UML_state_machine)

### Secondary (MEDIUM confidence — industry patterns studied)
- GSD v1-v13 implementation experience (13 milestones, 784+ tests, ~26K LoC)
- GSD `artifacts.cjs` — canonical registry pattern (10 exact-match + 2 pattern-match)
- GSD `verify.cjs` — health checks (19 warning codes for drift detection)
- Jira hierarchy model (Epic→Story→Task, workflow states, link types)
- Azure DevOps hierarchy (Epic→Feature→PBI→Task, work item states)
- [Martin Fowler on CQRS (2011)](https://martinfowler.com/bliki/CQRS.html)
- [C4 Model official site](https://c4model.com)

### Tertiary (LOW confidence — inference/community)
- Linear hierarchy model (Project→Cycle→Issue — documentation 404, inferred from training data)
- Large-scale project directory layout post-mortems (naming drift patterns)
- Mermaid C4 diagram syntax (marked experimental upstream — may evolve)

---
*Research completed: 2026-05-06*
*Ready for roadmap: yes — with flagged tensions for v40 discuss-phase resolution*
