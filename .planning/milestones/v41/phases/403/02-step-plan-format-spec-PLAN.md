---
phase: 403
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
autonomous: false
requirements:
  - STP-01
  - STP-02
  - STP-03
  - STP-04
  - STP-05
  - STP-06
  - STP-07
  - STP-08

must_haves:
  truths:
    - "STEP-PLAN-FORMAT.md exists at .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md and fully specifies the stepNPLAN.md contract."
    - "Pydantic StepFrontmatter class is rendered with model_config = ConfigDict(extra='forbid') and every required field from 403-CONTEXT.md (phase, slice, step, type, wave, depends_on, files_modified, autonomous, requirements, must_haves)."
    - "Pydantic MustHaves class is rendered with extra='forbid' and three sub-models: truths (list[str]), artifacts (list[ArtifactCheck]), key_links (list[KeyLink])."
    - "Every XML body section from STP-03 (objective, execution_context, context, interfaces, tasks, threat_model, verification, success_criteria, output) has a dedicated subsection with at least one literal example excerpt drawn from EXEMPLAR-stepNPLAN.md."
    - "Every <task> sub-tag from STP-04 (type attribute, tdd attribute, <name>, <files>, <read_first>, <action>, <verify><automated>, <acceptance_criteria>, <done>) is documented with at least one literal example excerpt drawn from EXEMPLAR-stepNPLAN.md."
    - "All five task types (auto, auto+tdd, checkpoint:human-verify, checkpoint:decision, checkpoint:human-action) have a behavior section covering harness action, gate/checkpoint mechanism, autonomy-tier interaction — verbatim from 403-CONTEXT.md <decisions> Task-type behaviors subsection."
    - "Granularity-selection algorithm is rendered as a deterministic pseudocode function with the exact bucket thresholds from 403-CONTEXT.md (≤30k/3/2 coarse, ≤80k/6/5 standard, else fine) and the step-count collapsing rules (coarse: 2 if scope>15k else 1; standard: 3 if scope>50k or files>4 else 2; fine: ceil(provides/2) clamped [3,5])."
    - "step_id stable-hash rule is documented: step_id = slugify(slice_id) + '-step-' + ordinal where ordinal is sorted by (min files_modified path lexicographically, then provides-count desc)."
    - "STP-07 zero-codebase-exploration contract is stated and counterexamples (vague references like 'see the existing schema') are listed as rejection cases."
    - "STP-08 exact-files-with-line-ranges rule is stated and counterexamples (e.g., 'explore the codebase', 'check the relevant files') are listed as rejection cases."
    - "<options> sub-tag for checkpoint:decision is documented with the 2–4 named options requirement and pros/cons attribute set, citing the EXEMPLAR Task 3 literally."
    - "<discovered_threats> append-only carve-out is documented with the runtime-only-append semantic (forward-pointer to PAP-05 enforcement)."
  artifacts:
    - path: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      provides: "Canonical stepNPLAN.md format spec covering STP-01..STP-08."
      min_lines: 500
  key_links:
    - from: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      to: ".planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md"
      via: "Literal-excerpt citations from EXEMPLAR for every body section and every task sub-tag"
      pattern: "EXEMPLAR-stepNPLAN\\.md"
    - from: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      to: ".planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md"
      via: "Pydantic frontmatter convention extension (StepFrontmatter extends the v40 pattern)"
      pattern: "FRONTMATTER-SCHEMAS\\.md"
    - from: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      to: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      via: "Sibling-doc cross-reference (mutability matrix lives in PLAN-AS-PROMPT.md; STEP-PLAN-FORMAT.md forward-points)"
      pattern: "PLAN-AS-PROMPT\\.md"
---

<objective>
Author the canonical `STEP-PLAN-FORMAT.md` spec document. This file is the design contract that v14 Build Kernel implements. It fully specifies the `stepNPLAN.md` artifact: the Pydantic frontmatter schema, every XML body section with literal example excerpts drawn from `EXEMPLAR-stepNPLAN.md`, every `<task>` sub-tag, the five-type task taxonomy and per-type behavior, the deterministic granularity-selection algorithm, and the literal-excerpt + exact-files-with-line-ranges contracts (STP-07/STP-08).

Purpose: STP-01..STP-08 fully covered. Downstream consumers — v14 (StepPlan parser implementation), Phase 404 (consumes the must_haves frontmatter sub-block schema), Phase 405 (consumes <options> sub-tag), Phase 406 (rolls up the format) — all read from this file.
Output: One markdown spec doc at `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md`, ≥500 lines, fully populated with literal Pydantic class definitions, literal EXEMPLAR excerpts, and the granularity-selection pseudocode.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/STATE.md
@.planning/milestones/v41/ROADMAP.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/HANDOFF.md
@.planning/milestones/v41/phases/403/403-CONTEXT.md
@.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
@.planning/milestones/v41/phases/402/402-CONTEXT.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
@.planning/milestones/v40/phases/400/specs/TIER-STEP.md
@.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
@.planning/milestones/v41/workflow-docs-from-gsd-2/frontmatter-first-skill-discovery.md
@.planning/milestones/v41/workflow-docs-from-gsd-2/frontmatter-defined-agent-role.md
@.planning/milestones/v41/workflow-docs-from-gsd-2/workflow-engine.md
@.planning/milestones/v41/workflow-docs-from-gsd-2/file-tracking.md
</context>

<threat_model>
Phase 403 is design-only. STEP-PLAN-FORMAT.md introduces no production attack surface — it is a markdown specification. Threats considered (per `<security_threat_model_gate>`):

- **`<discovered_threats>` append-only enforcement weakness**: This spec defines the `<discovered_threats>` sub-tag as a runtime-only-append carve-out from the immutable `<threat_model>` lock. If the spec is vague about WHAT counts as "append-only," a malicious executor could rewrite an existing threat under the guise of "appending" and the diff-the-proposed-write check would pass. Mitigation in spec: this doc MUST stipulate the EXACT diff shape — only NEW <threat>...</threat> sub-elements added at the end of <discovered_threats>; no removal of existing children, no edit of existing children's text. Encode as a 5-line rule with a positive and negative example. Forward-pointer to PAP-05 (PLAN-AS-PROMPT.md) which specifies the diff-the-proposed-write enforcer.
- **<options> attribute set drift**: <options> for checkpoint:decision authors the runtime-rendered choice list. If the spec leaves the attribute set ambiguous, plan authors may add free-text fields the harness cannot safely render. Mitigation: lock the attribute set to {name, pros, cons} in this spec; document that the planner discretion in 403-CONTEXT.md to add `risk` or `effort` requires a follow-up REQUIREMENTS amendment (defer; not in scope here).
- **Granularity algorithm tampering**: If the spec leaves the bucket thresholds soft (e.g., "approximately 30k tokens"), planners can drift; replan determinism is broken. Mitigation: render thresholds as exact integer constants in pseudocode + cite PRF-04's pure-machine spirit (table lookup, not LLM-judged).
- **STP-07/STP-08 evasion**: If counterexamples are not enumerated explicitly, plan authors writing vague <read_first> entries (e.g., "explore relevant tests") may pass through the planner-validation stage. Mitigation: list rejection-case examples literally — at least 4 anti-patterns each for STP-07 and STP-08.
- **Mode-isolation drift**: Build-only spec. Mitigation — explicit "Build-mode only" header note; no `state.teach.*` references.

No production code lands. No secrets. No network calls. No untrusted input.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author STEP-PLAN-FORMAT.md sections 1-6 (overview, frontmatter schema, body section catalog, task sub-tag spec)</name>
  <files>
    .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/403-CONTEXT.md (full file — every locked decision is load-bearing)
    - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md (full file — written by Plan 01; this spec quotes literal excerpts from it)
    - .planning/milestones/v41/REQUIREMENTS.md lines 38-56 (STP-01..STP-08 verbatim)
    - .planning/milestones/v41/HANDOFF.md lines 36-72 (§2 Task Decomposition Protocol; lines 84-116 §3 Plan-as-Prompt template structure)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic frontmatter convention pattern this spec extends)
    - .planning/milestones/v40/phases/400/specs/TIER-STEP.md (full file — Step is leaf artifact, behavioral baseline)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (search "stepNPLAN" — confirms filename form: no dash, no leading zeros)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/frontmatter-first-skill-discovery.md (full file — strict-validation pole reference; state aligns with this side replacing regex/length with Pydantic extra="forbid")
    - .planning/milestones/v41/workflow-docs-from-gsd-2/workflow-engine.md (search §6 — three-scope dependency model + Correction 2; informs hybrid depends_on + IO cross-check)
    - .planning/milestones/v41/phases/402/02-context-protocol-spec-PLAN.md lines 1-90 (Phase 402 spec-doc plan shape reference)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (full file — confirms how Phase 402 specs structure Pydantic class renders + reference-citation patterns)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md`. Sections 1–6 below; Task 2 owns sections 7–10. **Concrete content from 403-CONTEXT.md verbatim — do NOT re-derive.**

    ## Required structure (Sections 1-6)

    ### Section 1 — File header

    ```
    # Step Plan Format (Canonical, v41)

    > **Phase:** 403
    > **Status:** Canonical (v41)
    > **Requirements covered:** STP-01..STP-08
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
    > **Sibling specs:** PLAN-AS-PROMPT.md (injection + mutability), EXEMPLAR-stepNPLAN.md (canonical worked example).
    ```

    Add a 1-paragraph overview: harness-readable Step plan; YAML frontmatter (Pydantic-validated, `extra="forbid"`) carries the contract; XML body carries the prose, tasks, threat model, verification. The on-disk filename form is `stepNPLAN.md` (no dash, no leading zeros) per Phase 402 carry-forward + v40 ARTIFACT-CATALOG.md confirmation.

    ### Section 2 — Frontmatter Schema (STP-02)

    Heading: `## Frontmatter Schema (STP-02)`.

    Render the Pydantic class definitions verbatim from 403-CONTEXT.md `<decisions>` "Frontmatter schema completeness" subsection. Embed as fenced Python:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict
    from typing import Literal

    class ArtifactCheck(BaseModel):
        model_config = ConfigDict(extra="forbid")
        path: str
        provides: str
        min_lines: int

    class KeyLink(BaseModel):
        model_config = ConfigDict(extra="forbid")
        from_: str    # alias "from" — Python keyword collision
        to: str
        via: str
        pattern: str

    class MustHaves(BaseModel):
        model_config = ConfigDict(extra="forbid")
        truths: list[str]                            # bash/python assertions (verifiable per PRF-04)
        artifacts: list[ArtifactCheck]               # {path, provides, min_lines}
        key_links: list[KeyLink]                     # {from, to, via, pattern}

    class StepFrontmatter(BaseModel):
        model_config = ConfigDict(extra="forbid")
        phase: str                                   # e.g., "402"
        slice: str                                   # slice_id (slug form)
        step: str                                    # step_id (slug form, stable across replans)
        type: Literal["auto", "auto+tdd",
                      "checkpoint:human-verify",
                      "checkpoint:decision",
                      "checkpoint:human-action"]
        wave: int                                    # non-negative; v5 scheduler input
        depends_on: list[str]                        # same-Slice step_ids ONLY
        files_modified: list[str]                    # exact paths or globs
        autonomous: bool                             # back-compat with REQUIREMENTS wording
        requirements: list[str]                      # REQ-IDs (e.g., ["STP-01"])
        must_haves: MustHaves                        # nested model
    ```

    Add a sub-section `### Field constraints`:
    - "**autonomy is NOT a Step frontmatter field.** Per DEV-06 + SUB-09, autonomy lives only on the Slice frontmatter; Steps inherit. Single precedence chain: milestone default → Slice override → done."
    - "`depends_on` lists same-Slice step_ids ONLY. Cross-Slice deps belong to the Slice DAG (CTX-02 fresh-session-per-Slice abstraction must hold)."
    - "`files_modified` may be exact paths or globs (planner picks; both forms valid). Glob expansion happens at the planner-validation stage, not at runtime."
    - "**`depends_on` cross-check (planner validation):** at the research-slice validation stage, the planner verifies `depends_on` is consistent with `<read_first>` references against upstream Steps' `provides:` blocks. Misalignment fails `N-VALIDATION.md` and forces a replan iteration. Reference: `workflow-docs-from-gsd-2/workflow-engine.md` §6 three-scope dependency model + Correction 2."

    Add a sub-section `### Literal example (from EXEMPLAR-stepNPLAN.md)`:
    Quote the EXEMPLAR's full frontmatter (between the two `---` delimiters) verbatim as a fenced YAML block. Cite the source as: "From `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` (frontmatter, lines 1–N — the full YAML block)."

    ### Section 3 — XML Body Section Catalog (STP-03)

    Heading: `## XML Body Section Catalog (STP-03)`.

    Sub-sections — one H3 per body section, in this exact order. Each sub-section: 1 paragraph defining purpose + 1 fenced literal example excerpt drawn from EXEMPLAR-stepNPLAN.md.

    Sub-sections (use these exact H3 headings):
    1. `### <objective>` — Purpose: states the Step contract (what must be true when this Step is done) in 1–2 paragraphs. **Immutable** (locked by mutability matrix; see PLAN-AS-PROMPT.md). Quote EXEMPLAR's `<objective>` block as the example.
    2. `### <execution_context>` — Purpose: at-references to harness-bootstrap docs (workflow + summary template). Resolved at injection time per PAP-02. Quote EXEMPLAR's block.
    3. `### <context>` — Purpose: at-references to project + spec + sibling code files. Resolved at injection time per PAP-02 (one-level inline + token cap). **Mutable** (executor may add/remove `@`-refs as it learns). Quote EXEMPLAR's block (5 @-refs).
    4. `### <interfaces>` — Purpose: literal upstream code excerpts; the executor sees the exact contract without codebase exploration (STP-07). **Immutable** (locks the upstream contract; mutating silently desyncs from upstream — re-plan required if upstream genuinely changes). Quote EXEMPLAR's two upstream excerpts (EventEnvelope + CompactionSnapshot).
    5. `### <tasks>` — Purpose: container for one or more `<task>` blocks. Documented in detail in Section 4 below.
    6. `### <threat_model>` — Purpose: STRIDE-style register at design time. **Immutable** at the parent-block level. **Hybrid carve-out:** the `<discovered_threats>` sub-tag is append-only at runtime — see Section 5 for the carve-out semantic. Quote EXEMPLAR's threat block + the empty `<discovered_threats>` placeholder.
    7. `### <verification>` — Purpose: Slice-level pre-commit bash one-liners that gate task→Step→Slice advancement. **Immutable** (locks the gate per PAP-03). Quote EXEMPLAR's 3-4 bash lines.
    8. `### <success_criteria>` — Purpose: plain-language restatement of must_haves.truths. **Immutable**. Quote EXEMPLAR's bullets.
    9. `### <output>` — Purpose: post-Step deliverable instruction (typically the SUMMARY.md path). Quote EXEMPLAR's verbatim line.

    ### Section 4 — `<task>` Sub-tag Specification (STP-04)

    Heading: `## <task> Sub-tag Specification (STP-04)`.

    Render an exhaustive table:

    | Sub-tag / attribute | Required? | Mutability | Definition |
    |---------------------|-----------|------------|------------|
    | `type` (attribute on `<task>`) | required | **immutable** (changing it means it's a different task) | Literal: `auto` \| `auto+tdd` \| `checkpoint:human-verify` \| `checkpoint:decision` \| `checkpoint:human-action`. See Section 5. |
    | `tdd` (attribute) | optional, defaults `false` | immutable | Boolean. When `true`, harness enforces RED-before-GREEN per Section 5 auto+tdd. |
    | `<name>` | required | immutable | Human-readable task name (used in events + SUMMARY.md). |
    | `<files>` | required | **immutable** (task contract) | Newline-delimited file paths the task may write. Empty for decision-only tasks. |
    | `<read_first>` | required | mutable | List of `path lines N-M` entries the executor must read before writing. STP-08 contract — see Section 6. |
    | `<action>` | required | mutable | Step-by-step prose with code blocks. Executor refines as it learns. |
    | `<verify>` (with nested `<automated>`) | required | **immutable** (gate per PAP-03) | Bash one-liner that runs in <60s. Exit code 0 = pass; non-zero = fail. PRF-02 task gate. |
    | `<acceptance_criteria>` | required | **immutable** (task contract) | Bullet list of grep-verifiable conditions. Each condition checkable with grep, file read, or CLI output. |
    | `<done>` | required | **immutable** (task contract) | 1-line measurable acceptance state. |
    | `<options>` (only for `<task type="checkpoint:decision">`) | required when type=checkpoint:decision | **immutable** | Container of 2–4 `<option>` elements; each option has `name`, `pros`, `cons` attributes. See Section 5 checkpoint:decision behavior. |

    Add a sub-section `### Literal example (from EXEMPLAR-stepNPLAN.md)`: quote ONE full `<task>` block verbatim from the EXEMPLAR (recommend Task 2, the `auto`-type implementation task — exercises every required sub-tag without the auto+tdd or checkpoint complexity).

    Add a sub-section `### Note on STP-04 enumeration`: 403-CONTEXT.md's locked decisions extend STP-04 with the `<options>` sub-tag (specific to checkpoint:decision). This is additive — STP-04's "each `<task>` declares: …" list is non-exhaustive for type-specific sub-tags. No REQUIREMENTS amendment is required because STP-04 covers the COMMON sub-tags; type-specific sub-tags (like `<options>`) are part of the task-type behavior spec (STP-05). The `<discovered_threats>` sub-tag (under `<threat_model>`) is similarly additive to STP-03.

    ### Section 5 — Five-Type Task Taxonomy (STP-05)

    Heading: `## Five-Type Task Taxonomy (STP-05)`.

    One H3 per type. Each must cover (verbatim from 403-CONTEXT.md `<decisions>` Task-type behaviors subsection):
    - **Harness action** on encountering the type (what writes/reads are allowed/blocked).
    - **Gate/checkpoint mechanism** (where the type halts vs. proceeds; what events fire).
    - **Autonomy interaction** (per DEV-05: `--tiered`, `--full-yolo`, `--conservative`).

    Render each section with concrete content from 403-CONTEXT.md:

    `### auto`
    > Fully autonomous; harness allows all writes within `files_modified` allowlist; on completion, gate runs (PRF-02 task `<verify>` + `<acceptance_criteria>`).

    `### auto+tdd`
    > RED-before-GREEN enforcement via git-log + `tool.execute.before`:
    > - Harness consults git log for the current task's commit chain.
    > - Rejects writes to non-test files until at least one commit exists with a `test:` or `red:` prefix AND a captured failing-test artifact (e.g., pytest exit code != 0 stored in commit trailer `GSD-Test-Result: FAIL`).
    > - After the first commit with `GSD-Test-Result: PASS` (GREEN), refactor commits unrestricted within `files_modified`.
    > - Pure-machine, replayable. Aligns with `file-tracking.md` Correction 3: GSD metadata in commit trailers (`GSD-Task: <sliceId>/<taskId>`); state extends with `GSD-Test-Result: FAIL|PASS`.

    `### checkpoint:human-verify`
    > Autonomy-tiered behavior per DEV-05 literal:
    > - `--tiered` (default): auto-approves (visual sanity check passed).
    > - `--full-yolo`: auto-approves.
    > - `--conservative`: stops; opencode `question` tool rendered.
    > - Auto-approval emits `state.step.checkpoint_auto_resolved` event with `tier`, `task_id`, `selection="auto-approved"`. Event schema: see STEP-EVENTS.md (Plan 04 / Phase 403).

    `### checkpoint:decision`
    > Autonomy-tiered behavior per DEV-05 literal:
    > - `--tiered`: stops.
    > - `--full-yolo`: auto-picks option 1 deterministically.
    > - `--conservative`: stops.
    > - The option list is authored by the plan author in an `<options>` sub-tag of the `<task>` block. Required: 2–4 named options each with `pros` and `cons` attributes.
    > - **Quote the EXEMPLAR Task 3 `<options>` block here verbatim** as the canonical example.
    > - Harness renders via opencode `question` tool with the labeled list. Under `--full-yolo`, picks first option deterministically.
    > - `<options>` is **immutable** (mutability matrix in PLAN-AS-PROMPT.md). Executor cannot add/remove/edit options at runtime.
    > - **No "Other" free-text affordance** under build-mode strictness — diverges from AskUserQuestion's default. Decisions are bounded.

    `### checkpoint:human-action`
    > Autonomy-tiered behavior per DEV-05 literal:
    > - ALL tiers stop. Harness surfaces via opencode `question` tool with the action prompt; resumes when human confirms completion.
    > - Emits `state.step.checkpoint_human_action_pending` on entry, `state.step.checkpoint_human_action_resolved` on resume.

    Add closing sub-section `### `<discovered_threats>` append-only carve-out`: 1 paragraph. The `<threat_model>` block is design-time-locked, but the executor MAY APPEND newly discovered threats into a `<discovered_threats>` sub-tag (write-only-append). The exact diff shape that counts as "append-only": ONLY new `<threat>...</threat>` sub-elements added at the end of `<discovered_threats>`; no removal of existing children, no edit of existing children's text. Forward-pointer to PAP-05 (PLAN-AS-PROMPT.md §Immutable-section block) which specifies the diff-the-proposed-write enforcer that allows this carve-out.

    ### Section 6 — STP-07 + STP-08 Contracts

    Heading: `## STP-07 / STP-08 Contracts (Zero-Codebase-Exploration)`.

    Sub-section `### STP-07 — `<interfaces>` literal-excerpt rule`:
    - Rule statement: "The `<interfaces>` block contains literal code excerpts from upstream artifacts so the executor needs **zero codebase exploration** for upstream context."
    - Quote the EXEMPLAR's `<interfaces>` block verbatim.
    - Counterexamples (rejection cases — at least 4):
      - "see the existing schema for the field set" — REJECT (vague pointer)
      - "refer to the prior Step's output" — REJECT (forces exploration)
      - `<interfaces ref="upstream_provides[step-N]"/>` at a Step where step-N is NOT yet in upstream_provides — REJECT (PAP-06 stripping precondition not met)
      - `<interfaces><!-- TBD --></interfaces>` — REJECT (placeholder; STP-07 violation)

    Sub-section `### STP-08 — `<read_first>` exact-files-with-line-ranges rule`:
    - Rule statement: "`<read_first>` specifies exact files and line ranges per task — never 'explore the codebase.'"
    - Quote one EXEMPLAR `<read_first>` block verbatim.
    - Counterexamples (rejection cases — at least 4):
      - `<read_first>explore the codebase</read_first>` — REJECT (vague)
      - `<read_first>relevant test files</read_first>` — REJECT (vague)
      - `<read_first>tests/</read_first>` — REJECT (directory; no line range, no specific file)
      - `<read_first>src/state_core/schema.py</read_first>` — REJECT (path without line range; required form is `src/state_core/schema.py lines 1-40` or `src/state_core/schema.py (full file)`)
      - Allowed forms: `path lines N-M`, `path lines N-M and lines P-Q`, `path (full file)`.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` (Plan 01 output) — quote literal blocks for every body-section subsection and the `<task>` example.
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — pattern for "Pydantic class as fenced Python + sub-section field constraints" rendering. Mirror that section structure.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md | head -40` — confirms heading hierarchy depth used in v41 spec docs.
        - Grep pattern: `grep -nE "^---$" /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` — locates frontmatter delimiters for the literal-frontmatter quote.
      </code_to_reuse>
      <docs_to_consult>
        - 403-CONTEXT.md `<decisions>` "Frontmatter schema completeness" — verbatim Pydantic class source for Section 2.
        - 403-CONTEXT.md `<decisions>` "Task-type behaviors" — verbatim source for Section 5; copy each bullet exactly.
        - workflow-engine.md §6 three-scope dependency model — informs the depends_on cross-check note in Section 2.
        - frontmatter-first-skill-discovery.md — strict-validation pole; the spec's tone ("Pydantic supersedes regex/length") tracks this doc.
        - file-tracking.md Correction 3 — GSD trailer convention (`GSD-Task:`, extended to `GSD-Test-Result:`) for the auto+tdd subsection.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's StepPlan parser will be tested against EXEMPLAR-stepNPLAN.md as a fixture; this spec doc is the contract those tests assert against.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 250)}' \
        && grep -qE "^# Step Plan Format" "$F" \
        && grep -qE "^## Frontmatter Schema" "$F" \
        && grep -qE "^## XML Body Section Catalog" "$F" \
        && grep -qE "^## <task> Sub-tag Specification" "$F" \
        && grep -qE "^## Five-Type Task Taxonomy" "$F" \
        && grep -qE "^## STP-07 / STP-08 Contracts" "$F" \
        && grep -q "class StepFrontmatter" "$F" \
        && grep -q "class MustHaves" "$F" \
        && grep -q "class ArtifactCheck" "$F" \
        && grep -q "class KeyLink" "$F" \
        && grep -q 'extra="forbid"' "$F" \
        && grep -qE "^### <objective>" "$F" \
        && grep -qE "^### <execution_context>" "$F" \
        && grep -qE "^### <context>" "$F" \
        && grep -qE "^### <interfaces>" "$F" \
        && grep -qE "^### <tasks>" "$F" \
        && grep -qE "^### <threat_model>" "$F" \
        && grep -qE "^### <verification>" "$F" \
        && grep -qE "^### <success_criteria>" "$F" \
        && grep -qE "^### <output>" "$F" \
        && grep -qE "^### auto$" "$F" \
        && grep -qE "^### auto\+tdd" "$F" \
        && grep -qE "^### checkpoint:human-verify" "$F" \
        && grep -qE "^### checkpoint:decision" "$F" \
        && grep -qE "^### checkpoint:human-action" "$F" \
        && grep -q "GSD-Test-Result" "$F" \
        && grep -q "EXEMPLAR-stepNPLAN.md" "$F" \
        && grep -q "discovered_threats" "$F" \
        && grep -q "REJECT" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - File exists at `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` with ≥250 lines (Task 2 will extend it).
    - H1 `# Step Plan Format` present.
    - All four section H2 headings present: Frontmatter Schema, XML Body Section Catalog, `<task>` Sub-tag Specification, Five-Type Task Taxonomy, STP-07 / STP-08 Contracts.
    - Pydantic class definitions present: StepFrontmatter, MustHaves, ArtifactCheck, KeyLink — all with `extra="forbid"`.
    - All 9 body-section H3 headings present (objective, execution_context, context, interfaces, tasks, threat_model, verification, success_criteria, output) — line-anchored grep returns 9 matches.
    - All 5 task-type H3 headings present (auto, auto+tdd, checkpoint:human-verify, checkpoint:decision, checkpoint:human-action).
    - At least 3 EXEMPLAR-stepNPLAN.md citations (`grep -c "EXEMPLAR-stepNPLAN.md"` returns ≥3).
    - At least 4 `REJECT` counterexamples for STP-07/STP-08 (`grep -c "REJECT"` returns ≥8 — 4 each).
    - `GSD-Test-Result` trailer convention referenced.
    - `discovered_threats` carve-out section present.
  </acceptance_criteria>

  <done>
    Sections 1–6 of STEP-PLAN-FORMAT.md authored. STP-01 (template), STP-02 (frontmatter schema), STP-03 (body sections), STP-04 (`<task>` sub-tags), STP-05 (task types), STP-07 (literal-excerpt rule), STP-08 (line-ranges rule) all covered. Task 2 will add the granularity algorithm (STP-06) and closing material.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append STEP-PLAN-FORMAT.md sections 7-10 (granularity algorithm, step_id rule, replan determinism, validation hooks)</name>
  <files>
    .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — Task 1 output; this task appends to it)
    - .planning/milestones/v41/phases/403/403-CONTEXT.md lines 128-170 (Granularity selection algorithm section — verbatim source)
    - .planning/milestones/v41/REQUIREMENTS.md lines 47-50 (STP-06 verbatim)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "CTX-08" — confirms tokenizer fallback rule chars/4)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/quality-enforcement.md (search "§1" — five-pipeline taxonomy; informs the "fixed lookup tables beat formula tuning" rationale cited in 403-CONTEXT.md)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/workflow-engine.md (search "§6" + "Correction 2" — three-scope dependency model + the IO-derivation cross-check)
    - .planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md (full file — for closing literal-citation cross-references)
  </read_first>

  <action>
    Append sections 7–10 to the existing `STEP-PLAN-FORMAT.md`. Use Edit (insert at end of file). **Concrete content from 403-CONTEXT.md verbatim.**

    ### Section 7 — Granularity Selection Algorithm (STP-06)

    Heading: `## Granularity Selection Algorithm (STP-06)`.

    Sub-section `### Inputs (deterministic)`:
    Render verbatim from 403-CONTEXT.md `<decisions>` Granularity selection algorithm subsection:

    1. **Slice scope token estimate** — sum of input artifact sizes (`DESIGN.md` + `RESEARCH.md` + `PATTERNS.md`) tokenized with a fixed tokenizer. Pin the tokenizer choice: **`tiktoken cl100k_base` is recommended; chars/4 fallback per CTX-08 rule**. This spec ships with `tiktoken cl100k_base` as the canonical choice; v14 implementations may pin a Python-native alternative if `tiktoken` package availability is constrained.
    2. **`files_modified` union count** — distinct files the Slice will touch, computed from the planner's preliminary file map before Step assignment.
    3. **`provides:` blocks count** — distinct upstream→downstream artifact handoffs the Slice will produce.

    Add a 1-line note: "**LLM-counted task estimates are explicitly REJECTED** — they violate STP-06's 'deterministic function' wording. Replan determinism is load-bearing for PAP-04 audit-log clarity (see PLAN-AS-PROMPT.md)."

    Sub-section `### Algorithm (table-driven, bucketed thresholds)`:
    Render the algorithm verbatim as fenced pseudocode:

    ```text
    granularity(scope_tokens, files, provides) -> "coarse" | "standard" | "fine":
      if scope_tokens ≤ 30_000 AND files ≤ 3 AND provides ≤ 2:
        return "coarse"        # 1–2 Steps
      elif scope_tokens ≤ 80_000 AND files ≤ 6 AND provides ≤ 5:
        return "standard"      # 2–3 Steps
      else:
        return "fine"          # 3–5 Steps
    ```

    Sub-section `### Step count (collapsing the range to a single integer)`:
    Render verbatim:
    - coarse → 2 if `scope_tokens > 15_000`, else 1.
    - standard → 3 if `scope_tokens > 50_000` OR `files > 4`, else 2.
    - fine → ceil(`provides` / 2), clamped to [3, 5].

    Add a 1-paragraph rationale: "Match REQUIREMENTS literal ranges (1–2 / 2–3 / 3–5). Reproducible, debuggable, easy to tune. Inspired by gsd-2 quality-enforcement bucketed gate registries (`workflow-docs-from-gsd-2/quality-enforcement.md` §1 five-pipeline taxonomy) — fixed lookup tables beat formula tuning for spec docs."

    ### Section 8 — step_id Stable-Hash Rule + Replan Determinism

    Heading: `## step_id Stable-Hash Rule + Replan Determinism`.

    Sub-section `### step_id derivation`:
    Render verbatim:
    - "**step_ids derived from a stable hash:** `step_id = slugify(slice_id) + '-step-' + ordinal`"
    - "**ordinal:** position after sorting candidate Steps by (min `files_modified` path lexicographically, then `provides` count desc)."
    - Add a worked example using EXEMPLAR's step_id: "EXEMPLAR's step is `compaction-snapshot-schema-step-1` — slice slug `compaction-snapshot-schema` + `-step-` + ordinal `1` (first in sort order). If a sibling step in the same slice is added later, sorting by min `files_modified` path lexicographically determines its ordinal."

    Sub-section `### Replan determinism`:
    Render verbatim from 403-CONTEXT.md:
    - "Same inputs → same Step count + same step_ids."
    - "Replan with identical inputs reproduces the same plan exactly (idempotent at the file level)."
    - "Replan with changed inputs recomputes granularity and emits `state.step.renamed` / `state.step.added` / `state.step.removed` events for diff-replay continuity. Schemas: see STEP-EVENTS.md (Plan 04 / Phase 403)."
    - "**Locks held by PAP-03** (`must_haves`, `<verify>`) survive replan when step_id is unchanged; if step_id changes (input change forced rename), the new Step inherits authored content but `must_haves` are re-authored fresh (no carry-over of stale gates)."

    Sub-section `### Step-id collision strategy`:
    Render: "When inputs produce duplicate slugs across Slices, the slice_id slug prefix prevents collision by construction. Cross-Slice step_id collisions are not possible because `step_id = slugify(slice_id) + '-step-' + ordinal` and slice_ids are unique within the milestone scope."

    ### Section 9 — Planner Validation Hooks

    Heading: `## Planner Validation Hooks`.

    1-paragraph intro: this section enumerates the validation checks the research-slice planning + validation pipeline runs against authored stepNPLAN.md files. v15 Build Core Commands implements these checks; v41 specifies them.

    Bullet list (verbatim from 403-CONTEXT.md `<decisions>` "depends_on cross-check" + the implicit checks needed for STP-02..08):

    - **Pydantic load** — `StepFrontmatter.model_validate(yaml.safe_load(frontmatter))` raises `ValidationError` on missing required keys, unknown extras (`extra="forbid"`), or wrong types. Failure: planner emits `state.slice.validation_failed`; replan-iteration triggered.
    - **`depends_on` IO cross-check** — verify each `depends_on[i]` step_id exists in the same Slice; verify `<read_first>` references resolve against upstream Steps' `provides:` blocks. Reference: `workflow-docs-from-gsd-2/workflow-engine.md` §6 three-scope dependency model + Correction 2.
    - **DAG cycle detection** — at the planner-validation stage, NOT runtime. State's Steps are pre-planned, so runtime cycle detection (gsd-2's `reactive-graph.ts:detectDeadlock`) is not needed; cycles fail before execute-slice ever spawns.
    - **`files_modified` distinctness** — same-Wave Steps in the same Slice must not share files (parallel-safe). Sequential same-Slice Steps may share files via depends_on edge (later Step's writes are gated on earlier Step's gate-pass).
    - **`<read_first>` line-range form** — every `<read_first>` entry matches `^.+ (lines \d+-\d+|\(full file\))$`. STP-08 enforcement.
    - **`<interfaces>` non-empty (when depends_on non-empty)** — STP-07 contract; first-Step `<interfaces>` may be empty (no upstream).
    - **`<verify><automated>` non-empty** — every task carries an automated verify command (Nyquist rule).
    - **`<options>` cardinality (checkpoint:decision tasks)** — 2 ≤ count ≤ 4.
    - **Task type ↔ structure consistency** — `<task type="auto+tdd">` MUST have `tdd="true"` attribute (back-compat); `<task type="checkpoint:decision">` MUST have `<options>` block.

    ### Section 10 — Cross-references + Closing

    Heading: `## Cross-references`.

    Bullet list:
    - **Sibling spec — mutability matrix:** `PLAN-AS-PROMPT.md` §Mutability Matrix (PAP-03) defines which sections this format declares mutable vs. immutable. This format spec marks each section's mutability inline; PLAN-AS-PROMPT.md authoritatively rolls them up + specifies the runtime enforcer.
    - **Sibling spec — events:** `STEP-EVENTS.md` (Plan 04) defines the Pydantic schemas for `state.step.plan_authored`, `state.step.plan_edit`, `state.step.plan_edit_blocked`, `state.step.checkpoint_auto_resolved`, `state.step.checkpoint_human_action_pending`, `state.step.checkpoint_human_action_resolved`, `state.step.renamed`, `state.step.added`, `state.step.removed`.
    - **Worked example:** `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` is the canonical hand-authored worked example; v14 implementations use it as a parser test fixture.
    - **Phase 402 carry-forward:** filename form `stepNPLAN.md` (no dash, no leading zeros) is locked by 402-CONTEXT.md + v40 ARTIFACT-CATALOG.md; reinject body XML shape compatibility is locked by 402's CONTEXT-PROTOCOL.md.
    - **v40 baseline:** `state.build.harness.*` MUST NOT import `state.teach.*` (PROJECT.md cardinal rule). This spec is Build-mode only.

    Add closing 1-paragraph note: "v14 Build Kernel implements the StepPlan parser, planner-validation hook chain, granularity algorithm, and task-type behavior dispatch from this spec. v15 Build Core Commands implements the research-slice multi-stage pipeline that produces stepNPLAN.md files (planning + validation stages cited above). Phase 404 consumes the must_haves frontmatter sub-block schema. Phase 405 consumes the `<options>` sub-tag and autonomy-tier interactions. Phase 406 cross-references all of the above in the layered harness diagram."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` — Task 1 already cites; this Task 2 reinforces with the worked-step_id-example bullet.
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — pattern for "Cross-references" closing section; mirror its structure.
        - Grep pattern: `grep -nE "^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` — confirms Task 1's Section headings before appending.
      </code_to_reuse>
      <docs_to_consult>
        - 403-CONTEXT.md `<decisions>` Granularity selection algorithm — verbatim source for Section 7.
        - workflow-engine.md §6 three-scope dependency model + Correction 2 — informs Section 9 depends_on cross-check rule.
        - quality-enforcement.md §1 five-pipeline taxonomy — informs the bucketed-table rationale.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown spec.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 500)}' \
        && grep -qE "^## Granularity Selection Algorithm" "$F" \
        && grep -qE "^## step_id Stable-Hash Rule" "$F" \
        && grep -qE "^## Planner Validation Hooks" "$F" \
        && grep -qE "^## Cross-references" "$F" \
        && grep -q "tiktoken cl100k_base" "$F" \
        && grep -q "scope_tokens" "$F" \
        && grep -q "30_000" "$F" \
        && grep -q "80_000" "$F" \
        && grep -q "ceil(\`provides\` / 2)" "$F" \
        && grep -q "slugify(slice_id)" "$F" \
        && grep -q "compaction-snapshot-schema-step-1" "$F" \
        && grep -q "state.step.renamed" "$F" \
        && grep -q "state.step.added" "$F" \
        && grep -q "state.step.removed" "$F" \
        && grep -q "STEP-EVENTS.md" "$F" \
        && grep -q "PLAN-AS-PROMPT.md" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - STEP-PLAN-FORMAT.md ≥500 lines after this task.
    - All four new section H2 headings present (Granularity Selection Algorithm, step_id Stable-Hash Rule, Planner Validation Hooks, Cross-references).
    - Granularity algorithm pseudocode contains exact thresholds 30_000, 80_000, and the step-count rules `if scope_tokens > 15_000`, `> 50_000`, `ceil(provides / 2)`.
    - `tiktoken cl100k_base` referenced as canonical tokenizer.
    - step_id stable-hash rule rendered with EXEMPLAR's literal step_id worked example.
    - All three replan events referenced (`state.step.renamed`, `state.step.added`, `state.step.removed`) — forward-pointer to STEP-EVENTS.md (Plan 04).
    - Cross-references section forward-points to PLAN-AS-PROMPT.md AND STEP-EVENTS.md AND EXEMPLAR-stepNPLAN.md.
  </acceptance_criteria>

  <done>
    STEP-PLAN-FORMAT.md complete — all 10 sections present. STP-01..STP-08 fully covered with literal Pydantic schemas, EXEMPLAR citations, deterministic granularity algorithm, replan determinism rules, and planner-validation hook list.
  </done>
</task>

<task type="auto">
  <name>Task 3: Write 02-step-plan-format-spec-SUMMARY.md</name>
  <files>
    .planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — Tasks 1+2 output)
    - .planning/milestones/v41/phases/402/402-02-SUMMARY.md (full file — sibling SUMMARY shape reference)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory gate
  </read_first>

  <action>
    Author the per-plan SUMMARY.md. Mirror `402-02-SUMMARY.md` structure:

    1. `# Plan 403-02 Summary: STEP-PLAN-FORMAT.md`
    2. Status line: `**Status:** Shipped` + `**Wave:** 2` + `**Depends on:** 01 (EXEMPLAR-stepNPLAN.md)` + `**Blocks:** 04 (STEP-EVENTS.md)`.
    3. `## What Was Built` — 1 paragraph: STEP-PLAN-FORMAT.md at the canonical path; covers STP-01..STP-08; cites EXEMPLAR for every body section + `<task>` sub-tag.
    4. `## Key Decisions` — bullets:
       - "Pydantic StepFrontmatter renders verbatim from 403-CONTEXT.md (no re-derivation)."
       - "All 9 body-section H3 headings + all 5 task-type H3 headings + all 9 `<task>` sub-tags from STP-04 documented with EXEMPLAR literal citations."
       - "Granularity algorithm: bucketed thresholds 30k/80k + step-count rules collapse the 1–2/2–3/3–5 ranges to single integers per inputs."
       - "step_id stable-hash rule: `slugify(slice_id) + '-step-' + ordinal` ensures replan idempotency."
       - "Forward-pointers to PLAN-AS-PROMPT.md (Plan 03 — mutability matrix + injection mechanics) and STEP-EVENTS.md (Plan 04 — replan event schemas)."
       - "STP-04 enumeration extended with `<options>` sub-tag (checkpoint:decision) and `<discovered_threats>` sub-tag (under `<threat_model>`) — both additive; no REQUIREMENTS amendment needed because both are type-specific extensions of the common task contract enumerated by STP-04."
    5. `## Files Touched` — STEP-PLAN-FORMAT.md only.
    6. `## Open Items / Deferred` — bullets:
       - "Tokenizer pin (`tiktoken cl100k_base` recommended) — v14 may pick Python-native alternative; spec accommodates."
       - "<options> attribute set may grow if EXEMPLAR sizing reveals need (per 403-CONTEXT.md Claude's Discretion section)."
       - "REQUIREMENTS amendment NOT needed — STP-04 covers common sub-tags; type-specific sub-tags fall under STP-05 task-type behavior spec."
    7. `## Downstream Hooks` — bullets:
       - "v14 Build Kernel implements the StepPlan parser against this spec."
       - "v15 Build Core Commands implements the planner-validation hook chain."
       - "Phase 404 (Boolean Proof Gate) consumes the `must_haves` frontmatter sub-block schema."
       - "Phase 405 (Deviation Rules & Subagent Management) consumes the `<options>` sub-tag spec + autonomy-tier task-type interactions."
       - "Phase 406 (Harness Architecture Rollup) cross-references this format spec in the layered harness diagram."

    Length: 80-150 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/402/402-02-SUMMARY.md` — sibling SUMMARY exemplar; mirror sections + bullet density.
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md per-plan-SUMMARY-mandatory subsection.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 60)}' \
        && grep -q "Plan 403-02" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "STEP-PLAN-FORMAT.md" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - SUMMARY exists with ≥60 lines.
    - References Plan 02, the STEP-PLAN-FORMAT.md spec, and forward-points to Plans 03 and 04.
    - All four core sections present.
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate closed for Plan 02.
  </done>
</task>

</tasks>

<verification>
- File `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` exists with ≥500 lines.
- File `.planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md` exists with ≥60 lines.
- All 10 H2 sections present in STEP-PLAN-FORMAT.md (Frontmatter Schema, XML Body Section Catalog, `<task>` Sub-tag Specification, Five-Type Task Taxonomy, STP-07/STP-08 Contracts, Granularity Selection Algorithm, step_id Stable-Hash Rule, Planner Validation Hooks, Cross-references — plus the H1 file header).
- All 9 body-section H3 headings present.
- All 5 task-type H3 headings present.
- All four Pydantic class definitions present (StepFrontmatter, MustHaves, ArtifactCheck, KeyLink) with `extra="forbid"`.
- Granularity thresholds (30_000, 80_000) present.
- step_id stable-hash worked example uses EXEMPLAR's literal value (`compaction-snapshot-schema-step-1`).
- Forward-pointers to PLAN-AS-PROMPT.md and STEP-EVENTS.md present.
- No `state.teach.` references.
</verification>

<success_criteria>
- STP-01 (template form) covered: full structure documented + EXEMPLAR cited as canonical.
- STP-02 (frontmatter schema) covered: Pydantic StepFrontmatter + nested MustHaves/ArtifactCheck/KeyLink with `extra="forbid"`.
- STP-03 (every XML body section documented with EXEMPLAR literal): 9 sub-sections with quoted excerpts.
- STP-04 (every `<task>` sub-tag documented with EXEMPLAR literal): exhaustive table + literal `<task>` block citation.
- STP-05 (five task types behavior spec): one sub-section per type with verbatim 403-CONTEXT.md content.
- STP-06 (granularity-selection algorithm): deterministic pseudocode with exact thresholds + step-count rules.
- STP-07 (literal-excerpt rule + zero-codebase-exploration contract): rule statement + counterexamples.
- STP-08 (line-ranges rule): rule statement + counterexamples.
- Per-plan SUMMARY.md gate closed.
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` (≥500 lines)
- `.planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md` (≥60 lines)

Plan 04 (STEP-EVENTS.md) in Wave 3 can now reference this spec for the `state.step.*` event family.
</output>
