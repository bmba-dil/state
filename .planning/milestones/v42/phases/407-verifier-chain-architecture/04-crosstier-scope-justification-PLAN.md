---
phase: 407-verifier-chain-architecture
plan: 04
type: execute
wave: 3
depends_on:
  - 01
  - 02
files_modified:
  - .state/build/quality/VERIFIER-CHAIN.md
autonomous: true
requirements:
  - VCH-05
must_haves:
  truths:
    - "VERIFIER-CHAIN.md contains a `## VCH-05 — Cross-Tier Scope Rule Justification` section (appended AFTER VCH-06) that deepens the scope-rule rationale established in Plan 01's VCH-05 section."
    - "The justification explicitly evaluates and rejects the two alternative scope rules — (a) all Arcs / (c) Arcs with file overlap — citing concrete cost / instability / over-reach reasons grounded in v40 Arc model + v5 DAG scheduler edge semantics."
    - "The justification ties the chosen rule (depends_on closure over shipped Arcs) to three named precedents: gsd-2 kb workflow-engine §9.2 (milestones.depends_on JSON column), v40 D-12 edge types (`blocks`/`soft`/`data`), v5 DAG scheduler's typed-edge precedence ordering."
    - "The section names state's all-concurrent-Arc model (PROJECT.md) as the load-bearing reason in-progress Arcs are excluded from the closure (no stable verifier evidence to regress against)."
  artifacts:
    - path: ".state/build/quality/VERIFIER-CHAIN.md"
      provides: "VCH-05 scope-rule justification subsection appended after VCH-06"
      min_lines: 470
      contains_sections:
        - "## VCH-05 — Cross-Tier Scope Rule Justification"
        - "### Alternative (a) — All Arcs (rejected)"
        - "### Alternative (c) — File-Overlapping Arcs (rejected)"
        - "### Chosen Rule — depends_on Closure Over Shipped Arcs (accepted)"
        - "### Edge-Type Precedence in the Closure Walk"
  key_links:
    - from: ".state/build/quality/VERIFIER-CHAIN.md (VCH-05 justification section)"
      to: ".planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md (D-12 edge types)"
      via: "explicit citation of `blocks` / `soft` / `data` edge types"
    - from: ".state/build/quality/VERIFIER-CHAIN.md (VCH-05 justification section)"
      to: "v5 DAG scheduler typed-edge spec"
      via: "explicit citation of edge precedence in closure walk"
---

<threat_model>
ASVS L1. Phase 407 design-doc deliverable. Two relevant risks:

- **Spec-ambiguity-by-omission (T-407-07)**: Plan 01's VCH-05 section already declared the scope rule but the brief justification might leave downstream implementers wondering "did the author consider alternative X?" — leading to drift when v14 Build Kernel team revisits. **Mitigation**: this plan explicitly enumerates and rejects each alternative with named cost. Acceptance grep enforces presence of both rejected-alternative subsections.
- **Edge-type opacity (T-407-08)**: If the closure walk doesn't specify which `depends_on` edge types are followed (`blocks` MUST be; `soft` and `data` MAY be — see v40 D-12), the verifier could under-detect regressions (skipping `data` edges that share state) or over-detect (walking `soft` edges that are advisory-only). **Mitigation**: a dedicated subsection `### Edge-Type Precedence in the Closure Walk` declares for each of `blocks` / `soft` / `data` whether it participates in the closure walk and why.
</threat_model>

<objective>
Append a deepened justification section to `.state/build/quality/VERIFIER-CHAIN.md` (already authored by Plans 01 + 02). Plan 01's VCH-05 section established the scope rule (depends_on closure over shipped Arcs); this plan adds the rejected-alternatives analysis + edge-type-precedence rules, satisfying the ROADMAP SC3 "the chosen rule is justified against the v40 Arc model and the v5 DAG scheduler's edge semantics."

Purpose: Close the spec-ambiguity gap on Cross-Tier scope. Downstream implementers should have zero remaining questions about why this specific rule was chosen over the alternatives.

Output: ~80 lines appended to `.state/build/quality/VERIFIER-CHAIN.md`, lifting total to ≥ 470 lines.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md
@.planning/milestones/v42/REQUIREMENTS.md
@.planning/milestones/v42/phases/407-verifier-chain-architecture/407-01-SUMMARY.md
@.planning/milestones/v42/phases/407-verifier-chain-architecture/407-02-SUMMARY.md
@.state/build/quality/VERIFIER-CHAIN.md
@.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md
@.planning/milestones/v40/phases/400/specs/TIER-ARC.md
</context>

<interfaces>
<!-- v40 D-12 edge types. Verbatim from COMPOSITE-CASCADE.md. -->

Arc `depends_on` edge types (v40 D-12):
- `blocks` — hard dependency. Parent cannot ship until child Arc is in state `shipped`. Strongest signal.
- `soft` — advisory dependency. Parent CAN ship before child; declared for planning visibility. Weakest signal.
- `data` — data dependency. Parent's code/artifacts CONSUME outputs of child Arc (e.g., `state-build` consumes `state-core` schema). Mid-strength signal; coupling is concrete (shared state) but ship-order is not enforced.

state's PROJECT.md / v40 D-10 same-parent-only rule at lower tiers: at Stage / Slice / Step, every dependency MUST be intra-Arc. Inter-Arc coupling is only legal at the Arc tier and only via explicit `depends_on`.

state's all-concurrent-Arc model (PROJECT.md): many Arcs may be `in_progress` simultaneously; there is no global active pointer.
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Append VCH-05 scope-rule justification section (alternatives rejected + chosen-rule deepening + edge-type precedence)</name>
  <files>.state/build/quality/VERIFIER-CHAIN.md</files>
  <read_first>
    - .state/build/quality/VERIFIER-CHAIN.md (current state after Plans 01 + 02; verify it contains `## VCH-05 — Cross-Tier Verifier` and `## VCH-06 — Failure-Mode Mapping` sections)
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md (`<decisions>` VCH-05 subsection + `<specifics>` Cross-Tier-novelty paragraph)
    - .planning/milestones/v42/REQUIREMENTS.md (VCH-05 verbatim)
    - .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md (D-12 edge types verbatim — `blocks`/`soft`/`data` semantics)
    - .planning/milestones/v40/phases/400/specs/TIER-ARC.md (Arc state machine — shipped/in_progress states)
    - .planning/PROJECT.md (all-concurrent-Arc model — no global active pointer)
  </read_first>
  <behavior>
    - A `## VCH-05 — Cross-Tier Scope Rule Justification` section is appended AFTER `## VCH-06 — Failure-Mode Mapping` (preserves all prior content).
    - The section explicitly enumerates and rejects two alternative rules — `(a) all Arcs` and `(c) Arcs with file overlap` — with concrete cost/instability rationale per alternative.
    - The section deepens the accepted rule (`depends_on closure over shipped Arcs`) with three named precedents.
    - The section includes an Edge-Type Precedence subsection that declares per `depends_on` edge type (`blocks` / `soft` / `data`) whether the closure walk follows it.
    - Cross-links: the section references Plan 01's `## VCH-05 — Cross-Tier Verifier` section header at the top of the deepening, so a reader knows the relationship.
  </behavior>
  <action>
    Append the following to `.state/build/quality/VERIFIER-CHAIN.md` after the `## VCH-06 — Failure-Mode Mapping` section (and its subsections). Preserve all prior content; APPEND-ONLY.

    **Section header:** `## VCH-05 — Cross-Tier Scope Rule Justification`

    **Intent paragraph:**
    "This section deepens the Cross-Tier scope rule declared in `## VCH-05 — Cross-Tier Verifier` above. The accepted rule (`depends_on` closure over shipped Arcs) is justified by enumerating the alternative scope rules considered and rejected, then anchoring the choice to three named precedents from v40, v5, and gsd-2."

    **Subsection `### Alternative (a) — All Arcs (rejected)`:**

    "**Definition**: Cross-Tier verifier walks every Arc in state `shipped` (and only `shipped`) regardless of declared dependency, comparing stored verifier evidence to current HEAD for each.

    **Why rejected — cost**: O(N_shipped_arcs) per Arc ship, growing linearly with project age. The 4 evidence types (code-exists, tests-pass, LSP-clean, behavioral-check) each have a fixed per-Arc evaluation cost; re-running them across N Arcs every ship makes Cross-Tier the dominant wall-clock cost of the chain. State's CRIT.md must_haves can have ≥ 10 must_haves per Arc; the 4-evidence-type check per must_have means O(40 × N) operations per ship. v5 DAG scheduler perf budget is set against per-Slice cost, not per-Arc; over-walking blows past the budget.

    **Why rejected — false-positive risk**: many Arcs share no semantic coupling whatsoever (e.g., the auth Arc and the TUI-styling Arc); a re-evaluation that produces a verdict flip in one due to drift in an unrelated upstream library will trigger `state.verifier.crosstier.regression_detected` against an Arc that had nothing to do with the just-shipped Arc. False-positive human-gates are the worst class of failure in the failure-mode triad — they erode trust in the harness and incentivize bypass.

    **Why rejected — undeclared-coupling validation**: rule (a) implicitly validates undeclared cross-Arc coupling (since any pairwise drift triggers regression). v40 D-10 explicitly discourages undeclared cross-Arc coupling; the Cross-Tier verifier should NOT have to backfill what D-10 prevents at the design layer."

    **Subsection `### Alternative (c) — File-Overlapping Arcs (rejected)`:**

    "**Definition**: Cross-Tier verifier walks every shipped Arc whose `files_modified` set intersects the just-shipped Arc's `files_modified` set.

    **Why rejected — undeclared-by-design**: file overlap is the *symptom* of coupling, not the declaration. Two Arcs that touch the same file may have orthogonal intents (one renamed a function, the other added a doc-string); the overlap signal is noisy. Conversely, two Arcs that *share state via a third file* (e.g., both write to `events.sqlite` through `events.py`) have zero `files_modified` overlap but real coupling. File overlap under-detects the real signal.

    **Why rejected — depends_on already addresses this case**: when two Arcs genuinely share files (e.g., `state-build` extending `state-core`), the correct expression is a `data` edge in `depends_on` (v40 D-12). The closure walk DOES follow `data` edges (see Edge-Type Precedence subsection below). File overlap without a `data` edge declaration is a design smell — the verifier should not patch over it.

    **Why rejected — cost (mid-tier but still wrong)**: O(|files_modified| × N_shipped_arcs) intersection cost per ship. Cheaper than (a) but still grows linearly with project age and adds zero coverage over (b)'s `data`-edge closure."

    **Subsection `### Chosen Rule — depends_on Closure Over Shipped Arcs (accepted)`:**

    "**Definition** (restated from Plan 01's VCH-05 section): walk the transitive closure of v40 Arc-level `depends_on` edges of the just-shipped Arc; filter to Arcs in state `shipped`.

    **Precedent 1 — gsd-2 (kb workflow-engine §9.2)**: gsd-2's `milestones.depends_on` JSON column is the only above-tier coupling declaration in the prior system. State's Cross-Tier verifier directly inherits this signal. gsd-2 has no aggregation tier above milestone, so no closure walk; state's Arc tier is novel ground, but the *signal-source* is precedented.

    **Precedent 2 — v40 D-12 edge types (`blocks`/`soft`/`data`)**: the closure walk's edge-type semantics are defined here. Combined with v40 D-10's discouragement of undeclared lower-tier coupling, `depends_on` IS the canonical inter-Arc coupling channel.

    **Precedent 3 — v5 DAG scheduler typed-edge precedence**: the DAG scheduler already uses `blocks`/`soft` for frontier computation (`blocks` participate in topological sort; `soft` do not). The closure walk follows the same precedent (see Edge-Type Precedence subsection below) — verifier and scheduler agree on what an edge means.

    **Why this rule, not the alternatives**:
    - Bounded by *declared intent* — rule (a) over-walks; rule (c) under-detects.
    - Deterministic — the closure is a finite DAG walk; no fuzzy matching, no LLM-as-judge anywhere.
    - Cheap — O(closure_size × evidence_check_cost); typical closure is 1–4 Arcs.
    - Compatible with state's all-concurrent-Arc model (PROJECT.md): in-progress Arcs are excluded from the closure because their evidence is not yet stable — re-evaluating in-flight evidence would produce verdict flips that reflect work-in-progress, not regression.

    **Trade-off accepted**: the rule cannot catch undeclared cross-Arc coupling. This is *by design* — undeclared coupling is a v40 D-10 anti-pattern; surfacing it should happen at the design layer (DISCUSS.md must_haves, RESEARCH.md identified coupling) not at the verifier layer."

    **Subsection `### Edge-Type Precedence in the Closure Walk`:**

    "Per v40 D-12, `depends_on` edges have three types. The closure walk follows them as follows:

    | Edge type | Follow in closure? | Rationale |
    |---|---|---|
    | `blocks` | **Yes — mandatory** | Hard dependency. The just-shipped Arc could not have shipped without this child Arc shipping first; any verdict-flip in the blocker IS a regression for the just-shipped Arc (its assumptions broke). Strongest signal; closure MUST include. |
    | `data` | **Yes — mandatory** | Concrete coupling: the just-shipped Arc consumes outputs of the child Arc. A verdict-flip or unsatisfied must-have in the child means the data contract the just-shipped Arc was written against is no longer valid. Mid-strength signal; closure MUST include. |
    | `soft` | **No — excluded** | Advisory dependency for planning visibility only. v40 D-12 explicitly states `soft` does not enforce ship-order; therefore the just-shipped Arc's correctness does NOT depend on the soft-linked Arc's verifier state. Including soft edges in the closure would re-introduce alternative (a)'s false-positive surface. Soft edges are surfaced in `state dag show`, not in Cross-Tier closure. |

    **Walk discipline (verbatim algorithm)**:
    1. Start: just-shipped Arc's `depends_on` list.
    2. Filter: edges with `kind ∈ {blocks, data}`. Discard `soft`.
    3. Resolve: edge target Arc IDs.
    4. Filter: Arcs in state `shipped`. Discard `in_progress` / `descoped` / `abandoned`.
    5. Recurse: repeat steps 1–4 on each surviving Arc (transitive closure).
    6. Terminate: when no new Arc IDs are added (fixpoint).
    7. Re-evaluate: for each Arc in the closure, run the regression criteria (Plan 01 VCH-05 — verdict-flip + must_haves-unsatisfied).

    **Cycle safety**: the closure walk treats the dependency graph as a DAG (v5 invariant — cycle detection guaranteed by the scheduler). If a cycle is encountered (which would indicate a v5 invariant violation, not a verifier bug), the walker emits `state.verifier.crosstier.regression_detected` with `regression_kind='cycle_detected'` and human-gates immediately."

    **Closing note**: "This section is the *justification deepening* for Plan 01's `## VCH-05 — Cross-Tier Verifier` section. The two sections together fully satisfy ROADMAP SC3 ('chosen rule is justified against the v40 Arc model and the v5 DAG scheduler edge semantics')."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md` — owns D-12 edge types verbatim. Cite section headings.
        - Known: v5 DAG scheduler shipped already (PROJECT.md). Reference verbatim: "v5 DAG scheduler typed-edge precedence ordering".
        - Grep pattern (confirm D-12 edge-type names verbatim): `grep -n "blocks\|soft\|data\|D-12" .planning/milestones/v40/phases/400/specs/COMPOSITE-CASCADE.md | head -20`
      </code_to_reuse>
      <docs_to_consult>
        - 407-CONTEXT.md VCH-05 subsection — verbatim source for chosen-rule rationale.
        - v40 COMPOSITE-CASCADE.md — D-12 edge-type semantics.
        - kb/workflow/workflow-engine/08-milestone-boundaries.md §9.2 — gsd-2 milestones.depends_on precedent.
        - PROJECT.md "all concurrent Arcs" — state's no-global-active-pointer architectural decision.
      </docs_to_consult>
      <tests_to_write>
        N/A — design-only.
      </tests_to_write>
    </quality_scan>
  </action>
  <acceptance_criteria>
    - `grep -c '^## VCH-05 — Cross-Tier Scope Rule Justification$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Alternative (a) — All Arcs (rejected)$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Alternative (c) — File-Overlapping Arcs (rejected)$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Chosen Rule — depends_on Closure Over Shipped Arcs (accepted)$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Edge-Type Precedence in the Closure Walk$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c 'D-12' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 2
    - `grep -c 'D-10' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'v5 DAG scheduler' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'gsd-2\|kb workflow-engine §9.2' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1 (acceptable to mention "gsd-2" as a *prior-art reference* — NOT as a state deliverable identifier — so the global `\bgsd-\?[0-9]` check below must scope appropriately; verify the prior-art mentions stay inside this single deepening section only)
    - `grep -c '| `blocks` |' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '| `data` |' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '| `soft` |' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'Yes — mandatory' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 2 (one for `blocks`, one for `data`)
    - `grep -c 'No — excluded' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1 (for `soft`)
    - `grep -c 'all-concurrent-Arc\|all-concurrent' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'PROJECT.md' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'cycle_detected\|Cycle safety' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `wc -l .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 470 (was ≥ 380 after Plan 02; this plan adds ≥ 80 lines)
    - **Naming-discipline scope check**: the only `gsd-2` mentions in `VERIFIER-CHAIN.md` are *prior-art citations* in the Chosen Rule subsection (used as a system-of-origin reference, not as a state identifier). Run `grep -n 'gsd-2' .state/build/quality/VERIFIER-CHAIN.md` and confirm all matches sit within lines bounded by `## VCH-05 — Cross-Tier Scope Rule Justification` and the end of file, AND they all appear in prose context ("gsd-2's milestones.depends_on", "kb workflow-engine"). No event/module/command/identifier in the deliverable bears a `GSD-NN` form.
    - `grep -cE '\bGSD-[0-9]' .state/build/quality/VERIFIER-CHAIN.md` returns 0 (no state deliverable identifiers use GSD-NN form; lowercase `gsd-2` system-of-origin references are permitted per CONTEXT.md `<naming_constraints>` 'Treat GSD-2 / GSD-* references as background only')
  </acceptance_criteria>
  <verify>
    <automated>grep -q '^## VCH-05 — Cross-Tier Scope Rule Justification$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^### Alternative (a) — All Arcs (rejected)$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^### Alternative (c) — File-Overlapping Arcs (rejected)$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q '^### Edge-Type Precedence in the Closure Walk$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q 'D-12' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q 'v5 DAG scheduler' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; [ "$(wc -l &lt; .state/build/quality/VERIFIER-CHAIN.md)" -ge 470 ] &amp;&amp; [ "$(grep -cE '\bGSD-[0-9]' .state/build/quality/VERIFIER-CHAIN.md)" = "0" ]</automated>
  </verify>
  <done>
    VCH-05 justification section appended with rejected-alternatives analysis, deepened chosen-rule rationale citing 3 precedents (gsd-2 §9.2, v40 D-12, v5 DAG scheduler), and Edge-Type Precedence subsection declaring `blocks` (mandatory) / `data` (mandatory) / `soft` (excluded). All acceptance grep patterns pass. No state deliverable uses GSD-NN identifier form.
  </done>
</task>

</tasks>

<verification>
- `## VCH-05 — Cross-Tier Scope Rule Justification` section appended after VCH-06.
- Two alternative-rejection subsections present with cost/false-positive/under-detection rationale.
- Chosen-rule subsection cites 3 named precedents (gsd-2 kb §9.2, v40 D-12, v5 DAG scheduler).
- Edge-Type Precedence subsection declares walk discipline per edge type with cycle-safety note.
- File length ≥ 470 lines.
- No GSD-NN state-identifier form introduced.
</verification>

<success_criteria>
- VCH-05 deepening section completes ROADMAP SC3 ("chosen rule is justified against the v40 Arc model and the v5 DAG scheduler edge semantics")
- Rejected alternatives (a) and (c) explicitly enumerated with cost/over-reach/under-detection rationale
- Edge-type precedence table makes the closure-walk discipline implementable without further design
- gsd-2 / v40 / v5 precedents named explicitly
</success_criteria>

<output>
After completion, create `.planning/milestones/v42/phases/407-verifier-chain-architecture/407-04-SUMMARY.md` with:
- 1-paragraph outcome (justification deepened; ROADMAP SC3 satisfied)
- Cross-references: VCH-05 requirement fully addressed (combined with Plan 01's section)
- Note: this completes Phase 407 requirement coverage. VCH-01..VCH-05 satisfied by Plan 01; VCH-06 by Plan 02; VCH-07 by Plan 03; VCH-05 deepening by Plan 04.
</output>
