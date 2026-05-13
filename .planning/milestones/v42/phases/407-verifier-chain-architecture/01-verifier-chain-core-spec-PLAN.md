---
phase: 407-verifier-chain-architecture
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .state/build/quality/VERIFIER-CHAIN.md
autonomous: true
requirements:
  - VCH-01
  - VCH-02
  - VCH-03
  - VCH-04
  - VCH-05
must_haves:
  truths:
    - "VERIFIER-CHAIN.md exists at .state/build/quality/VERIFIER-CHAIN.md and is the single canonical verifier-chain spec for milestone v42."
    - "The doc enumerates all five verifier scopes — Step (VCH-01), Slice rollup (VCH-02), Stage rollup (VCH-03), Arc rollup (VCH-04), Cross-Tier (VCH-05) — each with a normalized schema row (inputs / algorithm / outputs / failure_mode / evidence)."
    - "The VCH-01 Step section enumerates the four named sub-verifiers (goal-backward, security, stub-detector, anti-pattern) with forward-references to the deep-design phase (Phase 409, 410, 408, 410 respectively)."
    - "VCH-05 Cross-Tier section declares the scope rule (depends_on closure over shipped Arcs) and the regression criteria (verdict-flip + must_haves unsatisfied)."
    - "Tier vocabulary follows the canonical Arc → Stage → Slice → Step hierarchy and NEVER uses 'GSD' or 'Phase' as a tier name (Stage is the v40 mid-tier; planning phase is a separate workflow concept)."
  artifacts:
    - path: ".state/build/quality/VERIFIER-CHAIN.md"
      provides: "Canonical v42 verifier-chain spec covering all 5 scopes."
      min_lines: 280
      contains_sections:
        - "## Overview"
        - "## Verifier-Chain Topology"
        - "## VCH-01 — Step Verifier Suite"
        - "## VCH-02 — Slice Rollup Verifier"
        - "## VCH-03 — Stage Rollup Verifier"
        - "## VCH-04 — Arc Rollup Verifier"
        - "## VCH-05 — Cross-Tier Verifier"
        - "## Verdict Vocabulary"
        - "## Per-Tier VERIFY Artifact"
  key_links:
    - from: ".state/build/quality/VERIFIER-CHAIN.md"
      to: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      via: "forward-reference to the v42 Amendment block (VCH-07, owned by Plan 03)"
    - from: ".state/build/quality/VERIFIER-CHAIN.md"
      to: ".planning/milestones/v42/phases/408..410"
      via: "forward-reference per Step sub-verifier row (goal-backward → 409, security → 410, stub-detector → 408, anti-pattern → 410)"
---

<threat_model>
ASVS L1. Phase 407 deliverable is a markdown spec document — minimal direct attack surface but two relevant risks:

- **Spec ambiguity (T-407-01)**: Vague algorithm wording (e.g., "verifies appropriately") lets unsafe runtime behavior pass downstream. **Mitigation**: every verifier algorithm spec uses imperative declarative language (AST node names, exact grep patterns, exact tool names — `ruff --fix`, `aiosqlite`, `pygit2`). Acceptance criteria below require grep-verifiable section headings AND minimum line counts on the high-stakes sections (VCH-01 Step suite, VCH-05 Cross-Tier).
- **Forward-reference rot (T-407-02)**: If a Step sub-verifier row points at the wrong forward-phase REQ-ID, downstream phases (408–410) may implement an algorithm that doesn't match what 407 declared. **Mitigation**: the forward-reference table is normative (see acceptance criteria) — exact REQ-ID ranges per sub-verifier (goal-backward → GBP-01..05 + ADV-01..04 / security → THM-01..05 / stub-detector → STB-01..04 + LVL-04..06 / anti-pattern → APS-01..05). Acceptance criteria grep-checks each cell.

No code lands; no event-name collision risk in this plan (Plan 03 owns event registration). Naming-discipline risk (GSD vs STATE) is enforced by the acceptance criterion `! grep -i "\bgsd-\?[0-9]" VERIFIER-CHAIN.md`.
</threat_model>

<objective>
Create the canonical `VERIFIER-CHAIN.md` spec document for milestone v42's verifier chain. The doc establishes the full topology (Step → Slice → Stage → Arc → Cross-Tier) and defines each verifier with a normalized schema row (inputs / algorithm / outputs / failure_mode / evidence). The Step suite (VCH-01) further decomposes into four sub-verifiers with forward-references to the deep-design phases. This plan establishes the schema rows and the per-scope sections; failure-mode mapping deepening lives in Plan 02 and event registration lives in Plan 03.

Purpose: Lock the verifier-chain architecture so v14 Build Kernel and v15 Build Core Commands can implement against a single canonical contract.

Output: One spec document at `.state/build/quality/VERIFIER-CHAIN.md` (~280–400 lines).
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/milestones/v42/STATE.md
@.planning/milestones/v42/ROADMAP.md
@.planning/milestones/v42/REQUIREMENTS.md
@.planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md

# Reference (background — do not amend in this plan):
@.planning/milestones/v40/phases/400/specs/TIER-ARC.md
@.planning/milestones/v40/phases/400/specs/TIER-STAGE.md
@.planning/milestones/v40/phases/400/specs/TIER-SLICE.md
@.planning/milestones/v40/phases/400/specs/TIER-STEP.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v41/phases/406/406-CONTEXT.md
</context>

<interfaces>
<!-- Verbatim tier vocabulary and naming rules. Use exactly as written. -->

Canonical tier hierarchy (v40 D-03 / D-17):
- Arc — root tier; feature block / project branch
- Stage — child of Arc; group of related Slices
- Slice — child of Stage; one worktree; verifier's primary unit-of-work boundary
- Step — child of Slice; smallest planned unit; owns the discuss/plan/run/verify cycle

Slice-cycle workflow phases (v41 SLC-01): design-slice → research-slice → run-slice → verify-slice.

Verdict vocabulary (project-wide, 3-state):
```python
Literal["passed", "failed", "warning"]
```
- `passed` — all green; no BLOCKER findings
- `failed` — ≥1 BLOCKER finding; halts upward propagation
- `warning` — WARNING-only findings; carries forward but advisory-only

Forward-reference invariant: rows in VERIFIER-CHAIN.md cite forward-phase REQ-IDs by exact ID range; downstream phases satisfy schema rows declared here.
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Author VERIFIER-CHAIN.md overview, topology diagram, verdict vocabulary, and per-tier VERIFY artifact section</name>
  <files>.state/build/quality/VERIFIER-CHAIN.md</files>
  <read_first>
    - .state/build/quality/VERIFIER-CHAIN.md (the file being written — read if any prior content exists; otherwise verify directory)
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md (authoritative spec source — entire `<decisions>` block)
    - .planning/milestones/v42/REQUIREMENTS.md (VCH-01..VCH-07 verbatim)
    - .planning/milestones/v40/phases/400/specs/TIER-ARC.md (Arc tier behavior — VCH-04 input)
    - .planning/milestones/v40/phases/400/specs/TIER-STAGE.md (Stage tier behavior — VCH-03 input)
    - .planning/milestones/v40/phases/400/specs/TIER-SLICE.md (Slice tier behavior — VCH-02 input)
    - .planning/milestones/v40/phases/400/specs/TIER-STEP.md (Step tier behavior — VCH-01 input)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md (HRN-06 human-gate-via-question, verdict semantics carry-forward)
  </read_first>
  <behavior>
    - VERIFIER-CHAIN.md opens with: title heading `# Verifier Chain — Milestone v42`, an Overview section, a Verifier-Chain Topology mermaid diagram, a Verdict Vocabulary table, and a Per-Tier VERIFY Artifact section.
    - The Overview section names the 5 verifier scopes verbatim: Step (VCH-01), Slice rollup (VCH-02), Stage rollup (VCH-03), Arc rollup (VCH-04), Cross-Tier (VCH-05).
    - The Topology section contains a mermaid diagram with edges labeled by re-aggregation trigger events (e.g., `state.verifier.step.passed`, `state.verifier.slice.failed`).
    - The Verdict Vocabulary section defines `Literal["passed", "failed", "warning"]` and includes the explicit mapping table to v40/v41/Phase-408 vocabulary (rejecting gsd-2's `pass | flag | omitted`).
    - The Per-Tier VERIFY Artifact section enumerates stepNVERIFY.md / N-VERIFICATION.md / STAGE-VERIFY.md / ARC-VERIFY.md with the authorship rule (server-written; agent zero authorship privilege; enforced via `tool.execute.before` write-block extending v41 SRP-04).
  </behavior>
  <action>
    Create directory `.state/build/quality/` if absent (mkdir -p), then create `VERIFIER-CHAIN.md` with the following sections in order. Use the exact heading text, verbatim event/term names, and the schema fields specified.

    **Section 1 — Title and frontmatter:**

    ```
    # Verifier Chain — Milestone v42

    > **Design contract for v14 Build Kernel and v15 Build Core Commands.**
    > Owned by: Phase 407 (Verifier Chain Architecture).
    > Forward-reference invariant: rows below cite forward-phase REQ-IDs; deep algorithm spec lives in Phases 408–411.
    > Pure-machine across the entire chain — no LLM-as-judge anywhere (pre-empts Phase 409 ADV debate in the negative, carries forward v41 PRF-04).
    ```

    **Section 2 — `## Overview`:**

    Two paragraphs:
    1. Name the 5 verifier scopes and what each scope verifies (Step = goal-backward + security + stub-detector + anti-pattern; Slice = pure aggregator over child Steps + Slice integration check; Stage = pure aggregator over child Slices + Stage acceptance check; Arc = pure aggregator over child Stages + Arc acceptance check; Cross-Tier = regression detection across already-shipped Arcs).
    2. State the pure-machine stance verbatim: "Every algorithm in this document is deterministic — AST walkers (Python `ast.NodeVisitor`), grep regex over `files_modified`, `pathlib` existence checks, `events.sqlite` queries via `aiosqlite`, `pygit2` for git evidence, `ruff` for anti-pattern fixable patterns, subprocess invocation of test runners. No LLM-as-judge anywhere in the verifier chain."

    **Section 3 — `## Verifier-Chain Topology`:**

    Embed a mermaid diagram (use ```mermaid fence). Nodes: Step, Slice rollup, Stage rollup, Arc rollup, Cross-Tier. Edges labeled with the propagation event names. Sketch:

    ```
    graph TD
      Step["Step Verifier Suite<br/>(4 parallel sub-verifiers)"]
      Slice["Slice Rollup Verifier"]
      Stage["Stage Rollup Verifier"]
      Arc["Arc Rollup Verifier"]
      CrossTier["Cross-Tier Verifier"]
      Step -->|state.verifier.step.passed/failed| Slice
      Slice -->|state.verifier.slice.passed/failed| Stage
      Stage -->|state.verifier.stage.passed/failed| Arc
      Arc -->|state.verifier.arc.passed/failed| CrossTier
      CrossTier -->|state.verifier.crosstier.regression_detected| Arc
    ```

    Below the diagram, one paragraph naming the event-driven re-aggregation mechanism (daemon listens on the v6 SSE bus; on any child verdict-flip, re-runs the parent rollup verifier).

    **Section 4 — `## Verdict Vocabulary`:**

    A code block declaring the verdict type:

    ```python
    from typing import Literal
    Verdict = Literal["passed", "failed", "warning"]
    ```

    Then a markdown table mapping each verdict to its semantics:

    | Verdict | Semantics | Propagation |
    |---|---|---|
    | `passed` | all checks green; no BLOCKER findings | carries forward upward without escalation |
    | `failed` | ≥1 BLOCKER finding | halts upward propagation; parent rollup also `failed`; failure_mode ladder fires |
    | `warning` | WARNING-only findings (no BLOCKER) | carries forward upward; advisory event for human/audit; does NOT block ship |

    Then a vocabulary-mapping table for downstream/related specs:

    | Source | Source value | Maps to |
    |---|---|---|
    | Phase 408 STB-02 | BLOCKER | `failed` |
    | Phase 408 STB-02 | WARNING | `warning` |
    | Phase 408 STB-02 | KNOWN | excluded from verdict (registered out via STB-04) |
    | Phase 411 PCK-10 | `blocked` | `failed` (at plan-checker scope) |
    | Phase 411 PCK-10 | `warnings` | `warning` |
    | Phase 411 PCK-10 | `passed` | `passed` |

    Add a final paragraph rejecting gsd-2's `pass | flag | omitted` (kb §8.7): "Rejected for state because `omitted` collides semantically with v40 D-14 `deferred` and v41 SRP-06 `deferred-items.md`. State's `warning` covers the noteworthy-but-not-blocking case; explicit deferment is its own artifact."

    **Section 5 — `## Per-Tier VERIFY Artifact`:**

    Markdown table:

    | Tier | Artifact filename | Required sections | Author |
    |---|---|---|---|
    | Step | `stepNVERIFY.md` (alongside `stepNPLAN.md` + `stepNSUMMARY.md`) | `## Goal-Backward` / `## Security` / `## Stub-Detector` / `## Anti-Pattern` + composite verdict in frontmatter | server-written (verifier orchestrator) |
    | Slice | `N-VERIFICATION.md` (existing v41 SLC artifact, amended) | `## Step Verdict Table` (one row per child Step) + `## Slice Integration Check` | server-written |
    | Stage | `STAGE-VERIFY.md` (new artifact) | `## Slice Verdict Table` + `## Stage Acceptance Check` (against CRIT.md must_haves) | server-written |
    | Arc | `ARC-VERIFY.md` (new artifact) | `## Stage Verdict Table` + `## Arc Acceptance Check` + `## Cross-Tier Verdict` block | server-written |

    Below the table, one paragraph declaring the authorship rule verbatim: "All VERIFY artifacts are server-written by the verifier orchestrator. Agents have zero authorship privilege on any VERIFY.md. A `tool.execute.before` write-block rejects any agent Write/Edit targeting `*VERIFY.md` paths (extends v41 SRP-04 allowlist enforcement). Matches v40 D-401-09 agent-vs-projector authorship boundary."

    Forward-reference paragraph: "Phase 411 EVD-03 walker traverses this chain upward (`stepNVERIFY → stepNPLAN → STEP-file → SLICE → STAGE → ARC`); the per-tier-VERIFY-artifact rule is what makes the walk possible."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — defines `state.session.*` / `state.harness.*` namespace conventions; mirror the `state.verifier.*` namespace at same depth.
        - Known: `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` (if present) — N-VERIFICATION.md canonical filename comes from here.
        - Grep pattern (verify tier vocabulary consistency): `grep -rn "Arc\|Stage\|Slice\|Step" .planning/milestones/v40/phases/400/specs/TIER-*.md | head -20`
      </code_to_reuse>
      <docs_to_consult>
        - 407-CONTEXT.md `<decisions>` block — verbatim source for verdict vocabulary table and per-tier-VERIFY-artifact section. Read line-by-line.
        - 407-CONTEXT.md `<canonical_refs>` — TIER-ARC.md / TIER-STAGE.md / TIER-SLICE.md / TIER-STEP.md must be consulted for accurate inputs/outputs per scope.
      </docs_to_consult>
      <tests_to_write>
        N/A — design-only markdown deliverable. Acceptance is grep + line-count based (see `<acceptance_criteria>`).
      </tests_to_write>
    </quality_scan>
  </action>
  <acceptance_criteria>
    - `test -f .state/build/quality/VERIFIER-CHAIN.md` returns 0
    - `grep -c '^# Verifier Chain — Milestone v42$' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '^## Overview$' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '^## Verifier-Chain Topology$' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '^## Verdict Vocabulary$' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '^## Per-Tier VERIFY Artifact$' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '```mermaid' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'Literal\["passed", "failed", "warning"\]' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'stepNVERIFY.md' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'N-VERIFICATION.md' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'STAGE-VERIFY.md' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'ARC-VERIFY.md' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -ci '\bgsd-\?[0-9]' .state/build/quality/VERIFIER-CHAIN.md` returns 0 (no GSD references in deliverable)
    - `wc -l .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 80 lines after this task
  </acceptance_criteria>
  <verify>
    <automated>test -f .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; [ "$(wc -l &lt; .state/build/quality/VERIFIER-CHAIN.md)" -ge 80 ] &amp;&amp; grep -q '^## Verdict Vocabulary$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; ! grep -qi '\bgsd-\?[0-9]' .state/build/quality/VERIFIER-CHAIN.md</automated>
  </verify>
  <done>
    VERIFIER-CHAIN.md exists with title, Overview, Topology (with mermaid diagram), Verdict Vocabulary (with type alias + mapping tables), Per-Tier VERIFY Artifact sections. All acceptance grep patterns pass. No GSD references present.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Author VCH-01 Step Verifier Suite section (4 sub-verifiers with normalized schema rows + forward-references)</name>
  <files>.state/build/quality/VERIFIER-CHAIN.md</files>
  <read_first>
    - .state/build/quality/VERIFIER-CHAIN.md (current state from Task 1)
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md (`<decisions>` block, VCH-01 subsection — entire content)
    - .planning/milestones/v42/REQUIREMENTS.md (VCH-01 verbatim + forward-phase REQ-IDs: GBP-01..05, ADV-01..04, THM-01..05, STB-01..04, LVL-04..06, APS-01..05)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md (SUB-01 dispatch_subagent typed-spawn pattern — referenced for parallel fan-out)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (PRF-04 pure-machine; PRF-06 3-strike retry counter scope; PRF-07 write-block)
    - .planning/milestones/v40/phases/400/specs/TIER-STEP.md (Step tier state machine — VCH-01 verifier fires from `running → verified` transition)
  </read_first>
  <behavior>
    - The VCH-01 section opens with intent (Step verifier suite is 4 parallel sub-verifiers, fan-out via `dispatch_subagent`, server-recomputed composite verdict).
    - Each of the 4 sub-verifiers has its own subsection (`### Sub-verifier: goal-backward` / security / stub-detector / anti-pattern) with the normalized schema (5 rows: inputs / algorithm / outputs / failure_mode / evidence).
    - Each sub-verifier subsection includes a `**Forward-reference:**` line citing the deep-design phase + REQ-ID range.
    - A composite-verdict subsection defines the strict-AND-on-PASS / any-BLOCKER → FAIL rule and the union-of-evidence aggregation, citing server-side recomputation discipline.
    - A short-circuit-policy paragraph states: always run all 4 sub-verifiers in parallel; collect full evidence; no early termination.
  </behavior>
  <action>
    Append to `.state/build/quality/VERIFIER-CHAIN.md` after the Per-Tier VERIFY Artifact section. Add:

    **Section header:** `## VCH-01 — Step Verifier Suite`

    **Intent paragraph (verbatim spirit):**
    "The Step verifier suite is composed of **four parallel sub-verifiers** — goal-backward, security, stub-detector, anti-pattern — running independently via opencode `task` subagent fan-out (Phase 405 SUB-01 `dispatch_subagent` typed-spawn surface). The composite Step verdict is server-recomputed (never LLM-summarized; matches kb quality-enforcement §11.5). Composite evidence list = union of all 4 sub-verifier evidence lists. All citations follow the canonical citation grammar (Phase 409 ADV-03): `file_path:line_number`, `commit:<hash>`, `event:<id>`, `test:<runner-output-id>`."

    **Short-circuit policy paragraph:**
    "Always run all 4 sub-verifiers; collect full evidence. No early termination on first BLOCKER. The agent receives all sub-verifier findings in one failureContext re-injection (kb §4.1 server-side merge), so a single retry can address all four classes of failure rather than fix-retry-fix-retry serial cycles."

    **Sub-section per sub-verifier (4 subsections, each with this exact schema — 5 fields):**

    Each `### Sub-verifier: <name>` subsection must contain a markdown table with rows `inputs`, `algorithm`, `outputs`, `failure_mode`, `evidence`, plus a `**Forward-reference:**` line.

    Content for each sub-verifier (copy these table cells verbatim):

    **`### Sub-verifier: goal-backward`**

    | Field | Spec |
    |---|---|
    | `inputs` | STEP.md goal text + ARC/STAGE/SLICE success-criteria blocks + REQ-IDs cited in STEP.md + locked decisions from DISCUSS.md; must_haves frontmatter from PLAN.md |
    | `algorithm` | Deterministic must-have derivation (Phase 409 GBP-01); for each derived must-have, find codebase evidence via the 4 evidence types (code-exists via `pathlib` + AST match; tests-pass via test-runner subprocess invocation; LSP-clean via `ruff check` / `pyright`; behavioral-check via cited runnable assertion). Falsification-first stance per Phase 409 ADV-01. |
    | `outputs` | `## Goal-Backward` section of `stepNVERIFY.md` + `state.verifier.step.goal_backward.passed` or `state.verifier.step.goal_backward.failed` event |
    | `failure_mode` | retry-loop → human-gate. Re-dispatch agent with missing-must-have evidence (kb §4.3 recoverable failure). 3-strike → human gate via opencode `question` tool (v41 HRN-06). |
    | `evidence` | List of `Citation` (Phase 409 ADV-03 grammar) per must-have: ≥1 of {file:line, commit:hash, event:id, test:runner-output-id}. SUMMARY.md claims do NOT count as evidence (Phase 409 GBP-04 trust rule). |

    **Forward-reference:** Deep design in Phase 409, REQ-IDs GBP-01..05 + ADV-01..04.

    **`### Sub-verifier: security`**

    | Field | Spec |
    |---|---|
    | `inputs` | PLAN.md STRIDE register (THM-01) + accepted-risks registry (THM-04) + cited mitigation files + `files_modified` allowlist |
    | `algorithm` | Per Phase 410 THM-03 disposition logic: for `mitigate` threats — grep/AST-check mitigation pattern in cited files; for `accept` threats — verify entry in accepted-risks registry with valid `accepted_by`; for `transfer` threats — verify transfer doc exists and target system verified. Secret-detection via `src/state_core/observability/redactor.py` reused over `files_modified` diffs. |
    | `outputs` | `## Security` section of `stepNVERIFY.md` + `state.verifier.step.security.passed` or `state.verifier.step.security.failed` event |
    | `failure_mode` | retry-loop → human-gate. Re-dispatch agent with mitigation-missing evidence cited `file:line`. 3-strike → human gate. |
    | `evidence` | Per-STRIDE-category verdict (CLOSED / OPEN:BLOCKER / WARNING) with citations to cited mitigation files + registry entries. |

    **Forward-reference:** Deep design in Phase 410, REQ-IDs THM-01..05.

    **`### Sub-verifier: stub-detector`**

    | Field | Spec |
    |---|---|
    | `inputs` | `files_modified` set + SUMMARY.md `## Known Stubs` section (STB-04) + AST of changed Python files + import graph |
    | `algorithm` | Stub pattern catalog (STB-01) detected via AST walker (`ast.NodeVisitor`) + grep over files_modified; matched stubs classified per severity (STB-02: BLOCKER/WARNING/KNOWN); trace-through algorithm (STB-03) walks all callers via import-graph traversal; promote to BLOCKER if emptiness reaches rendering/API surface, demote to WARNING if handled gracefully; legitimate-stub disambiguation (LVL-06) cross-references `## Known Stubs` before promoting. |
    | `outputs` | `## Stub-Detector` section of `stepNVERIFY.md` + `state.verifier.step.stub_detector.passed` or `state.verifier.step.stub_detector.failed` event |
    | `failure_mode` | retry-loop → human-gate. Re-dispatch agent with stub-trace evidence (call-chain to user surface). 3-strike → human gate. Known-Stubs registration (STB-04) bypasses by promoting to KNOWN tier before counter triggers. |
    | `evidence` | Per-stub Citation list: `file:line` of stub + call-chain Citations to user-surface (rendering/API) where reachability promotes to BLOCKER. |

    **Forward-reference:** Deep design in Phase 408, REQ-IDs STB-01..04 + LVL-04..06.

    **`### Sub-verifier: anti-pattern`**

    | Field | Spec |
    |---|---|
    | `inputs` | `files_modified` set + Python 3.12 anti-pattern catalog (APS-01) + architecture anti-pattern catalog (APS-02, extending `src/state_core/import_lint.py`) + test anti-pattern catalog (APS-03) + project-specific extensions (APS-05) |
    | `algorithm` | Per-pattern detection via {regex, AST node match, ruff rule ID, import-graph query}; severity classification per APS-01/APS-02/APS-03 BLOCKER/WARNING tables; fixable-pattern subset (unused imports, formatting, ordering) routed through deterministic auto-fix tier (VCH-06 below). |
    | `outputs` | `## Anti-Pattern` section of `stepNVERIFY.md` + `state.verifier.step.anti_pattern.passed` or `state.verifier.step.anti_pattern.failed` event |
    | `failure_mode` | auto-fix-attempt → retry-loop → human-gate. Harness first runs deterministic formatter pass (`ruff --fix`, `black`, `isort`) for fixable patterns. Remaining violations re-dispatch agent. After 3 retries on same `(pattern, file)` pair, human gate. |
    | `evidence` | Per-violation Citation: `file:line` + pattern ID (ruff rule ID or AST match name) + severity. |

    **Forward-reference:** Deep design in Phase 410, REQ-IDs APS-01..05.

    **Composite-verdict subsection:**

    Add `### Composite Step Verdict` subsection. Content:

    "Step verdict = `passed` iff all 4 sub-verifiers return `passed` or `warning` (no BLOCKER). Any BLOCKER from any sub-verifier → Step verdict = `failed`. Server-recomputed via the daemon's projector (kb §11.5); never LLM-summarized. Composite event: `state.verifier.step.passed` or `state.verifier.step.failed`. Composite evidence list = union of all 4 sub-verifier evidence lists. Retry counter scope: per-`(task_id, check_id)` per v41 PRF-06 (no scope conflation across sub-verifiers; each sub-verifier maintains its own 3-strike counter)."

    <quality_scan>
      <code_to_reuse>
        - Known: `src/state_core/import_lint.py` — exists; APS-02 architecture anti-pattern catalog extends this lint. Reference the module path; downstream phase implements.
        - Known: `src/state_core/observability/redactor.py` — exists; security sub-verifier reuses for secret-like-string detection. Reference path.
        - Grep pattern (confirm exact module paths): `grep -rn "import_lint\|redactor" src/state_core/ --include="*.py" | head -10`
      </code_to_reuse>
      <docs_to_consult>
        - 407-CONTEXT.md VCH-01 subsection — every table cell here paraphrases CONTEXT decisions verbatim; cross-check.
        - Phase 405 SUB-01 deep spec — `dispatch_subagent` typed-spawn surface for fan-out (forward-reference only; do NOT re-derive).
        - kb/workflow/quality-enforcement/07-per-turn-gate-flow.md (Q3/Q4 parallel subagent dispatch) — pattern that backs the fan-out.
      </docs_to_consult>
      <tests_to_write>
        N/A — design-only markdown deliverable.
      </tests_to_write>
    </quality_scan>
  </action>
  <acceptance_criteria>
    - `grep -c '^## VCH-01 — Step Verifier Suite$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Sub-verifier: goal-backward$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Sub-verifier: security$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Sub-verifier: stub-detector$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Sub-verifier: anti-pattern$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Composite Step Verdict$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c 'Phase 409' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 2 (forward-ref from goal-backward + composite citation grammar)
    - `grep -c 'Phase 410' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 2 (forward-ref from security + anti-pattern)
    - `grep -c 'Phase 408' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1 (forward-ref from stub-detector)
    - `grep -c 'state.verifier.step.goal_backward.passed\|state.verifier.step.goal_backward.failed' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 2
    - `grep -c 'state.verifier.step.security' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'state.verifier.step.stub_detector' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'state.verifier.step.anti_pattern' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '| `inputs` |' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 4 (one inputs row per sub-verifier)
    - `grep -c '| `algorithm` |' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 4
    - `grep -c '| `failure_mode` |' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 4
    - `grep -c 'dispatch_subagent\|opencode `task`' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `wc -l .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 180 lines after this task
  </acceptance_criteria>
  <verify>
    <automated>grep -q '^### Sub-verifier: goal-backward$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^### Sub-verifier: security$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^### Sub-verifier: stub-detector$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^### Sub-verifier: anti-pattern$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^### Composite Step Verdict$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; [ "$(wc -l &lt; .state/build/quality/VERIFIER-CHAIN.md)" -ge 180 ]</automated>
  </verify>
  <done>
    VCH-01 section contains 4 sub-verifier subsections with normalized 5-row schema tables, forward-references to Phase 408/409/410 deep designs, composite-verdict subsection with server-side-recomputation rule, and short-circuit policy paragraph. All acceptance grep patterns pass.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Author VCH-02/VCH-03/VCH-04 rollup-verifier sections and VCH-05 Cross-Tier section</name>
  <files>.state/build/quality/VERIFIER-CHAIN.md</files>
  <read_first>
    - .state/build/quality/VERIFIER-CHAIN.md (current state from Tasks 1+2)
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md (`<decisions>` block — VCH-02, VCH-03, VCH-04, VCH-05 subsections verbatim)
    - .planning/milestones/v42/REQUIREMENTS.md (VCH-02..VCH-05 verbatim)
    - .planning/milestones/v40/phases/400/specs/TIER-ARC.md (Arc tier state machine — D-18 auditing state + `/state-ship-arc` flow for VCH-04 invocation)
    - .planning/milestones/v40/phases/400/specs/TIER-STAGE.md (Stage tier — `/state-ship-stage` mirror gate for VCH-03)
    - .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md (Arc depends_on edge types — D-12 `blocks`/`soft`/`data` — for VCH-05 scope rule)
  </read_first>
  <behavior>
    - VCH-02 / VCH-03 / VCH-04 each have their own `## VCH-NN — ...` section, each with the same 5-row normalized schema table (inputs / algorithm / outputs / failure_mode / evidence).
    - VCH-02/03/04 all describe pure aggregator behavior (boolean AND aggregation; verdict propagates upward; rollup never retries / never escalates / never auto-fixes).
    - VCH-05 Cross-Tier section declares the scope rule (depends_on closure over shipped Arcs), the regression criteria (verdict-flip + must_haves-unsatisfied), the trigger (auto on Arc ship + manual via CLI), and the failure mode (human-gate immediately).
    - VCH-05 includes an event-driven re-aggregation paragraph (daemon SSE bus listener; on `state.verifier.<child>.{passed,failed}` event, re-aggregate parent rollup; cost-bounded to open rollups only).
  </behavior>
  <action>
    Append to `.state/build/quality/VERIFIER-CHAIN.md`. Add 4 sections with the schema-row tables.

    **Section `## VCH-02 — Slice Rollup Verifier`:**

    Opening paragraph: "Pure aggregator over child Steps + Slice-level integration check. Reads each child `stepNVERIFY.md` composite verdict + Slice integration evidence (Phase 402 SLC-XX verify-slice stage outputs). Algorithm: `slice_verdict = passed iff every child_step.verdict ∈ {passed, warning} AND slice_integration_check.verdict == passed`. Any child `failed` → Slice `failed`. The rollup is a *boolean aggregation*, not an actor — it never retries, never escalates, never auto-fixes; the child's failure mode owns those."

    Then a schema table:

    | Field | Spec |
    |---|---|
    | `inputs` | All child `stepNVERIFY.md` composite verdicts + Slice integration check evidence (output of verify-slice stage per v41 SLC-XX) + `N-VERIFICATION.md` integration sections |
    | `algorithm` | Strict-AND aggregation: `slice_verdict = passed iff every child_step.verdict ∈ {passed, warning} AND slice_integration_check == passed`. Any child `failed` → Slice `failed`. Server-recomputed by daemon projector handler. |
    | `outputs` | `N-VERIFICATION.md` `## Step Verdict Table` + `## Slice Integration Check` sections (server-written) + `state.verifier.slice.passed` or `state.verifier.slice.failed` event |
    | `failure_mode` | **No action; verdict propagates upward.** Child Step's failure mode owns retry/escalation. Slice rollup re-runs only when daemon receives a child verdict-flip event (`state.verifier.verdict_changed`). |
    | `evidence` | Composite Citation list = union of child Step evidence lists + Slice integration check citations. |

    **Section `## VCH-03 — Stage Rollup Verifier`:**

    Opening paragraph: "Same pure-aggregator pattern as VCH-02, scoped to child Slices. Reads each child `N-VERIFICATION.md` Slice verdict + Stage acceptance criteria (CRIT.md must_haves at Stage tier). Output `STAGE-VERIFY.md` (new artifact, server-written) + `state.verifier.stage.passed` or `state.verifier.stage.failed` event. **Invocation surface includes `/state-ship-stage <id>`** (user request mirroring `/state-ship-arc` — v40 D-18; command itself owned by v43 Build Command Layer)."

    Schema table:

    | Field | Spec |
    |---|---|
    | `inputs` | All child `N-VERIFICATION.md` Slice verdicts + Stage CRIT.md must_haves + Stage state machine current state (must be in `verifying` per v40 D-17) |
    | `algorithm` | Strict-AND aggregation: `stage_verdict = passed iff every child_slice.verdict ∈ {passed, warning} AND every stage_must_have satisfied`. Stage must_have satisfaction verified via the 4 evidence types (code-exists, tests-pass, LSP-clean, behavioral-check). |
    | `outputs` | `STAGE-VERIFY.md` (server-written) with `## Slice Verdict Table` + `## Stage Acceptance Check` sections + `state.verifier.stage.passed` or `state.verifier.stage.failed` event |
    | `failure_mode` | No action; verdict propagates upward. Pure aggregator. |
    | `evidence` | Composite Citation list = union of child Slice evidence + Stage must_have evidence citations. |

    **Section `## VCH-04 — Arc Rollup Verifier`:**

    Opening paragraph: "Same pure-aggregator pattern, scoped to child Stages. Reads each child `STAGE-VERIFY.md` Stage verdict + Arc acceptance criteria. Fires as part of the `/state-ship-arc` flow's `auditing` state transition (v40 D-18: `auditing` entry guard = all child Stages shipped; Arc rollup verifies before transition to `shipped`)."

    Schema table:

    | Field | Spec |
    |---|---|
    | `inputs` | All child `STAGE-VERIFY.md` Stage verdicts + Arc CRIT.md must_haves + Arc state machine current state (must be `auditing` per v40 D-18) |
    | `algorithm` | Strict-AND aggregation: `arc_verdict = passed iff every child_stage.verdict ∈ {passed, warning} AND every arc_must_have satisfied`. Arc must_have satisfaction verified via the 4 evidence types. |
    | `outputs` | `ARC-VERIFY.md` (server-written) with `## Stage Verdict Table` + `## Arc Acceptance Check` + `## Cross-Tier Verdict` block (Cross-Tier result, see VCH-05) + `state.verifier.arc.passed` or `state.verifier.arc.failed` event |
    | `failure_mode` | No action; verdict propagates upward. Pure aggregator. (However: VCH-05 Cross-Tier verifier fires *after* VCH-04 passes and CAN fail the Arc — see VCH-05 below.) |
    | `evidence` | Composite Citation list = union of child Stage evidence + Arc must_have evidence citations + Cross-Tier verdict citations. |

    **Section `## VCH-05 — Cross-Tier Verifier`:**

    Opening paragraph: "**State-specific; novel.** gsd-2 has no aggregation tier above milestone (kb workflow-engine §9.2). Cross-Tier verifier detects regressions across already-shipped Arcs caused by the just-shipped Arc."

    **Scope rule subsection (`### Scope Rule`):**

    "**Depends-on closure over already-shipped Arcs.** Walk the transitive closure of v40 Arc-level `depends_on` edges (D-12 edge types: `blocks` / `soft` / `data`) of the just-shipped Arc. Filter to Arcs in state `shipped` (in-progress Arcs have no stable verifier evidence to regress against — state's all-concurrent model means many Arcs may be `in_progress` simultaneously per PROJECT.md).

    **Rationale**: matches the only gsd-2 precedent (`milestones.depends_on` JSON column, kb workflow-engine §9.2); bounded by declared intent; deterministic; cheap (DAG walk + per-Arc evidence re-check). State's v40 D-10 same-parent-only rule at lower tiers means undeclared cross-Arc coupling is already discouraged; `depends_on` is the strongest declared signal.

    Plan 04 deepens this justification with the alternative-rules-rejected analysis."

    **Trigger subsection (`### Trigger`):**

    "Auto-fires as the final gate of `/state-ship-arc` after VCH-04 Arc rollup passes (matches v40 D-18 Arc audit workflow). Also exposed as a CLI surface `state verify crosstier <arc-id>` (full design owned by Phase 411 EVD-04 `state verify trace` family) for diagnostic / drift-recovery re-runs."

    **Regression criteria subsection (`### Regression Criteria`):**

    "Both criteria are evaluated; either triggering = `state.verifier.crosstier.regression_detected`:

    1. **Prior Arc's verifier verdict flips PASS→FAIL on re-run.** Re-execute each closure-Arc's stored Step/Slice/Stage verifier evidence against current HEAD. Any verdict that was `passed` at original ship but is now `failed` = regression. Matches kb server-side recomputation discipline (kb §11.5).
    2. **Prior Arc's must_haves no longer satisfied.** Walk each closure-Arc's CRIT.md + frontmatter `must_haves.{truths,artifacts,key_links}` (v41 STP-02 schema) and re-verify via the 4 evidence types (code-exists, tests-pass, LSP-clean, behavioral-check — Phase 409 GBP-03 taxonomy). Any unsatisfied must_have = regression. Falsification-first stance pre-empts Phase 409 ADV-01."

    **Schema table:**

    | Field | Spec |
    |---|---|
    | `inputs` | Just-shipped Arc ID + transitive closure of `depends_on` edges over Arcs in state `shipped` + stored verifier evidence for each closure-Arc + each closure-Arc's CRIT.md must_haves |
    | `algorithm` | For each Arc in closure: (1) re-execute stored Step/Slice/Stage verifier evidence against current HEAD via pure-machine checks; (2) re-verify must_haves via the 4 evidence types. Cross-Tier verdict = `passed` iff NO closure-Arc shows verdict-flip OR must-have unsatisfaction. Any failure → `regression_detected`. |
    | `outputs` | `## Cross-Tier Verdict` block in `ARC-VERIFY.md` of the just-shipped Arc + `state.verifier.crosstier.passed` OR `state.verifier.crosstier.regression_detected` event |
    | `failure_mode` | **Human-gate immediately.** Regression means a previously-shipped Arc is now broken. Cannot auto-fix (new Arc's commits caused it; harness pass can't choose remedy) or retry-loop (no agent action against the *current* Arc fixes it). Routes through opencode `question` tool (v41 HRN-06): rollback / patch-via-new-Slice / accept-with-registry-entry (Phase 410 THM-04 accepted-risks registry analog). **Fail-closed**: the just-shipped Arc cannot transition to `shipped` until human gate clears. |
    | `evidence` | Per-closure-Arc verdict-flip Citation (verifier_name + scope_id + old verdict + new verdict + diff Citations to current HEAD) + per-unsatisfied-must-have Citation list (must_have ID + 4-evidence-type failure mode). |

    **Event-driven re-aggregation subsection (`### Event-Driven Re-Aggregation`):**

    "The daemon listens on the v6 SSE bus for any `state.verifier.<child>.{passed,failed}` event. On a verdict-flip event for a child of an open rollup, daemon re-runs the parent rollup verifier (pure-machine, no LLM). Composite verdict updates idempotently. The `state.verifier.verdict_changed` event fires at each tier whose verdict flipped, enabling the TUI to update progressively.

    **Bounded cost**: only the parent of the changed child is re-aggregated, and only if it's in an `open` state (not already shipped). Already-shipped Arcs/Stages/Slices/Steps are immutable verdicts in the event log (Phase 411 EVD-05 retention rule territory).

    This is how the chain heals after gap-closure: a failed Step retried that now passes triggers cascading parent re-aggregation upward."

    <quality_scan>
      <code_to_reuse>
        - Known: `src/state_core/projector.py` — exists, CQRS projection engine with 19 handlers / 3 cache tables. Cross-Tier re-aggregation is a new projector handler family. Reference path; downstream implements.
        - Known: v40 COMPOSITE-CASCADE.md — owns D-12 `depends_on` edge types (`blocks`/`soft`/`data`). Cite verbatim in VCH-05.
        - Grep pattern (confirm Arc depends_on shape): `grep -n "depends_on\|D-12" .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md | head -20`
      </code_to_reuse>
      <docs_to_consult>
        - 407-CONTEXT.md VCH-02 / VCH-03 / VCH-04 / VCH-05 subsections — verbatim source.
        - kb/workflow/workflow-engine/08-milestone-boundaries.md §9.2 — gsd-2 has no above-milestone tier; cite for VCH-05 novelty.
        - kb/workflow/quality-enforcement/11-server-side-recomputation.md (or §11.5) — server-recompute discipline.
      </docs_to_consult>
      <tests_to_write>
        N/A — design-only.
      </tests_to_write>
    </quality_scan>
  </action>
  <acceptance_criteria>
    - `grep -c '^## VCH-02 — Slice Rollup Verifier$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^## VCH-03 — Stage Rollup Verifier$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^## VCH-04 — Arc Rollup Verifier$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^## VCH-05 — Cross-Tier Verifier$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Scope Rule$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Trigger$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Regression Criteria$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Event-Driven Re-Aggregation$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c 'state.verifier.slice.passed\|state.verifier.slice.failed' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'state.verifier.stage.passed\|state.verifier.stage.failed' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'state.verifier.arc.passed\|state.verifier.arc.failed' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'state.verifier.crosstier.regression_detected' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '/state-ship-stage\|/state-ship-arc' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 2
    - `grep -c 'depends_on' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 2
    - `grep -c 'pure aggregator' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 3 (one per VCH-02/03/04)
    - `grep -c 'human-gate\|human gate' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `wc -l .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 280 lines after this task
  </acceptance_criteria>
  <verify>
    <automated>grep -q '^## VCH-02 — Slice Rollup Verifier$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^## VCH-03 — Stage Rollup Verifier$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^## VCH-04 — Arc Rollup Verifier$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^## VCH-05 — Cross-Tier Verifier$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q 'state.verifier.crosstier.regression_detected' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; [ "$(wc -l &lt; .state/build/quality/VERIFIER-CHAIN.md)" -ge 280 ]</automated>
  </verify>
  <done>
    All four sections (VCH-02/03/04/05) exist with normalized schema-row tables. VCH-05 has Scope Rule, Trigger, Regression Criteria, Event-Driven Re-Aggregation subsections. All acceptance grep patterns pass.
  </done>
</task>

</tasks>

<verification>
- All 5 verifier scopes (VCH-01..VCH-05) have a `## VCH-NN — ...` section in `.state/build/quality/VERIFIER-CHAIN.md`.
- Each verifier section has the 5-row normalized schema (inputs / algorithm / outputs / failure_mode / evidence).
- The VCH-01 Step section has 4 sub-verifier subsections + composite verdict subsection.
- The forward-reference table cells point at the correct phases (goal-backward → 409, security → 410, stub-detector → 408, anti-pattern → 410).
- The Verdict Vocabulary section defines `Literal["passed", "failed", "warning"]` and maps to Phase 408 STB-02 and Phase 411 PCK-10 vocabularies.
- The Per-Tier VERIFY Artifact section names stepNVERIFY.md / N-VERIFICATION.md / STAGE-VERIFY.md / ARC-VERIFY.md.
- No `gsd-NN` references in the deliverable (naming discipline).
- File length ≥ 280 lines.
</verification>

<success_criteria>
- VERIFIER-CHAIN.md exists at `.state/build/quality/VERIFIER-CHAIN.md`
- Covers VCH-01 (Step suite, 4 sub-verifiers), VCH-02 (Slice rollup), VCH-03 (Stage rollup), VCH-04 (Arc rollup), VCH-05 (Cross-Tier)
- Each scope has the normalized 5-field schema row
- VCH-01 sub-verifiers carry forward-references to Phase 408/409/410
- VCH-05 declares depends_on-closure scope rule + regression criteria + human-gate failure mode
- Verdict vocabulary normalized to `Literal["passed", "failed", "warning"]`
- All tier names are canonical (Arc → Stage → Slice → Step); no "GSD-NN" identifiers in deliverable
</success_criteria>

<output>
After completion, create `.planning/milestones/v42/phases/407-verifier-chain-architecture/407-01-SUMMARY.md` with:
- 1-paragraph plan outcome (what VERIFIER-CHAIN.md now contains, scope coverage)
- Cross-references: VCH-01..VCH-05 requirement coverage
- Forward-references to Plans 02 (VCH-06 failure-mode mapping), 03 (VCH-07 event amendment), 04 (VCH-05 scope-rule justification deepening)
- Known Stubs section: none expected (design-only deliverable)
</output>
