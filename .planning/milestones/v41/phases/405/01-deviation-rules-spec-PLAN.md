---
phase: 405
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
autonomous: false
requirements:
  - DEV-01
  - DEV-02
  - DEV-03
  - DEV-04
  - DEV-05
  - DEV-06
  - DEV-07

must_haves:
  truths:
    - "DEVIATION-RULES.md exists at .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md and fully specifies the 4-rule deviation framework (DEV-01..04), tiered autonomy table (DEV-05), per-Slice autonomy override (DEV-06), and the `deviation` event family + SUMMARY projector (DEV-07)."
    - "All four rules are documented with literal headings `## Rule 1: Auto-fix Bugs (DEV-01)`, `## Rule 2: Auto-add Critical Functionality (DEV-02)`, `## Rule 3: Auto-fix Blocking Issues (DEV-03)`, `## Rule 4: Architectural Changes (DEV-04)`."
    - "Each rule entry specifies (verbatim from 405-CONTEXT.md): category description, max-attempts (literal `max-attempts: 3` for Rules 1-3; `max-attempts: 1` for Rule 4), commit-prefix convention (`fix:` for Rule 1; `feat:` or `fix:` per gsd-2 inference for Rule 2; `fix:` for Rule 3; Rule 4 commits via opencode question resolution), and escalation path (Rule 1 -> Rule 4; Rule 2 -> documented in SUMMARY; Rule 3 -> checkpoint:decision; Rule 4 -> always human gate)."
    - "Rule 4 always-human-gate semantics are documented as STRUCTURAL not policy: the `log_deviation(rule_id=4)` MCP handler synchronously renders opencode `question` tool with the `alternatives` payload — there is no `if mode == 'full-yolo' bypass` branch."
    - "The `log_deviation` MCP tool signature is rendered verbatim as a Pydantic-typed Python signature with the four classification_source values (`agent_declared`, `harness_promoted`, `arch_pattern_match`), required Rule4Option list for `rule_id=4`, and DeviationLogResult return shape covering `deviation_event_id`, `attempt_number`, `cap_exceeded`, `classification_accepted`, `rejection_reason`."
    - "Harness cross-validation flow is rendered as a numbered 5-step protocol (issue_signature recomputation -> Rule-4 alternatives check -> Rule-4 auto-promotion -> scope_deviation_request correlation -> cap check) with the exact rejection-event names: `deviation_classification_rejected` for steps 1-3, `deviation_cap_exceeded` for step 5."
    - "The arch-pattern allowlist is rendered verbatim with all six regex patterns (alembic/, migrations/, schema.{sql,prisma,graphql}, pyproject.toml/uv.lock, src/state_*/__init__.py, mcp/tools/*.py) plus the literal module path `state_build/deviation/arch_patterns.py` as single-source-of-truth."
    - "ADD vs BUMP discrimination is documented for pyproject.toml/uv.lock with the two literal regex patterns (`^\\+\\s*\"[a-zA-Z0-9_\\-]+>=` for ADD; `-\\s*\"X>=A.B\"\\s*\\n\\+\\s*\"X>=C.D\"` for BUMP) and the verdict (ADD -> force Rule 4; BUMP -> no auto-promotion)."
    - "Commit trailer convention is rendered verbatim: `STATE-Task:`, `STATE-DeviationRule: N` (N in {1,2,3,4}), `STATE-DeviationAttempt: K` (K in {1,2,3}) with literal example commit body. Single-source-of-truth module path `state_build/commit/trailers.py` is named. Auditor grep target `git log --grep=\"STATE-DeviationRule: 4\"` is documented."
    - "Tiered autonomy table is rendered as a 4-column markdown table (Mode, human-verify, decision, human-action, **Rule 4 deviation**) with the three modes (`--tiered`, `--full-yolo`, `--conservative`) and the literal cell values verbatim from 405-CONTEXT.md (e.g., `--full-yolo` row: auto-approve / auto-pick option 1 / stop / **stop**)."
    - "Per-Slice autonomy override (DEV-06) is documented: Slice frontmatter `autonomy: Literal[\"tiered\",\"full-yolo\",\"conservative\"]`, precedence rule `milestone default -> Slice override -> done`, Slice override CAN move stricter OR looser (narrowing-only does NOT apply to autonomy — autonomy is policy not capability). No Step-level override (locked by Phase 403)."
    - "The `issue_signature` derivation function is rendered verbatim as a Python def with the sha256 16-char-hex output, the canonical concatenation `{error_kind.value}|{file_path}|{line_no}|{matched_token}`, and a literal note that whole-stack hashing is rejected (OS/env nondeterminism)."
    - "The `ErrorKind` Literal/Enum is rendered with the 10 starter values (pytest_failure, type_error, import_error, null_dereference, schema_validation_failure, scope_violation, paralysis_threshold_cross, proof_gate_failure, subagent_spot_check_failure, other) and a note that planner extends in v14 as new failure modes surface."
    - "Three-counter independence is documented citing gsd-2 loop-control.md Correction 1: APG `paralysis_event` (per task_id), PRF `gate_strike` (per task_id,check_id), DEV `deviation_logged` (per task_id,rule_id,issue_signature). Forward-pointer to Phase 406 HRN-05 harness_intervention umbrella event."
    - "Counter scope is documented as per-(task_id, rule_id, issue_signature) tuple. Reset-on-success rule is stated: when the next pure-machine eval of the same tuple returns success, counter drops to 0. Different tuples never share state."
    - "The `Deviation` Pydantic event payload is rendered verbatim with all 14 fields (deviation_event_id, task_id, step_id, slice_id, session_id, rule_id Literal[1,2,3,4], issue_signature, attempt_number, classification_source, commit_sha, resolution Literal of 6 values, alternatives, error_excerpt, agent_response_summary, triggered_at, intervention_event_id) and `model_config = ConfigDict(extra='forbid')`."
    - "The append-only `deviation_resolution_recorded` event is documented: single-mutable-row pattern (resolution starts `pending`, mutates on resolution); rejection of two-event split is justified (deviation lifecycle short-lived, ≤3 attempts, lives within one task boundary). Replay determinism preserved."
    - "The `## Deviations` SUMMARY projector is specified: subscribes to `deviation_logged` + `deviation_resolution_recorded`; aggregates by (rule_id, issue_signature); writes to stepNSUMMARY.md `## Deviations` section atomically (temp+rename); invalidates read cache; 8-column markdown table schema rendered verbatim (#, Rule, Issue, Source, Attempts, Resolution, Commit, When) with each column's source field cited; section omitted entirely when zero deviations."
    - "Projector module path `state_build/projectors/deviation_summary.py` is named as single-source-of-truth. Mirrors gsd-2 db-writer.ts projection pattern + 404 N-VERIFICATION.md projector pattern."
    - "Mode-isolation note is rendered: `state_build/deviation/` MUST NOT import from `state_teach/`; CI import-graph lint enforces. Events live in BUILD_ONLY_EVENT_PREFIXES."
    - "DEVIATION-RULES.md does NOT contain the literal string 'GSD' anywhere (project naming-discipline rule — all identifiers are STATE-* / state-*)."
  artifacts:
    - path: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      provides: "Canonical 4-rule deviation framework spec covering DEV-01..DEV-07: log_deviation MCP tool, arch-pattern allowlist, tiered autonomy table, per-Slice override, deviation event family, ## Deviations SUMMARY projector."
      min_lines: 600
  key_links:
    - from: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "Three-counter independence — deviation chain is the third independent counter alongside PRF gate_strike and APG paralysis_event; mirrors per-(task_id, check_id) tuple discipline"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      to: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      via: "scope_deviation_request correlation in cross-validation step 4; Rule 4 auto-promotion triggered by open SRP-04 request matching arch-pattern allowlist"
      pattern: "SCOPE-PROHIBITION\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      via: "Slice frontmatter `autonomy` field (DEV-06) consumed from Phase 403 frontmatter schema; the field gains new Literal['tiered','full-yolo','conservative'] union here"
      pattern: "STEP-PLAN-FORMAT\\.md"
    - from: ".planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md"
      to: ".planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md"
      via: "Forward-pointer for new state.step.deviation_logged / deviation_classification_rejected / deviation_resolution_recorded / deviation_cap_exceeded events registered by Plan 04"
      pattern: "EVENT-TAXONOMY\\.md"
---

<objective>
Author the canonical `DEVIATION-RULES.md` spec document — the design contract that v14 Build Kernel implements for the 4-rule deviation framework with tiered autonomy. This file fully specifies: (1) all four deviation rules with category, max-attempts cap, commit-prefix convention, and escalation path (DEV-01..DEV-04); (2) the `log_deviation` MCP tool signature with agent-declared + harness-cross-validated routing; (3) the arch-pattern allowlist that forces Rule-4 auto-promotion on architectural file targets; (4) tiered autonomy table extended with the **Rule 4 always-stop** 4th column (DEV-05); (5) per-Slice autonomy override mechanism with precedence rule (DEV-06); (6) the `Deviation` event payload + append-only `deviation_resolution_recorded` mutation pattern (DEV-07); (7) the `## Deviations` SUMMARY projector algorithm.

Purpose: DEV-01..DEV-07 fully covered. Downstream consumers — v14 (Build Kernel: log_deviation MCP tool, attempt-counter projector, arch-pattern allowlist module, deviation event family, ## Deviations SUMMARY projector, infer_commit_type + STATE-* trailer module), v15 (Build Core Commands: per-Slice autonomy resolution, verify-slice SUMMARY assembly), Phase 406 (harness rollup cites Rule-4 escalation as tier 4 of HRN-04 intervention ladder), Plan 04 (Phase 405 cross-reference plan registers the new event family in EVENT-TAXONOMY.md) — all read from this file.

Output: One markdown spec doc at `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md`, ≥600 lines, fully populated with literal Pydantic class definitions for `DispatchSubagent.alternatives` (Rule4Option), `DeviationLogResult`, `Deviation`, `ErrorKind`, with the arch-pattern allowlist regex list rendered verbatim, the tiered autonomy 4-column table rendered verbatim, the `## Deviations` SUMMARY projector 8-column schema rendered verbatim, and an `infer_commit_type` cite to gsd-2 COMMIT_TYPE_RULES + the STATE-* trailer constants.
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
@.planning/milestones/v41/phases/405/405-CONTEXT.md
@.planning/milestones/v41/phases/404/404-CONTEXT.md
@.planning/milestones/v41/phases/404/specs/PROOF-GATE.md
@.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
@.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — `Slice.autonomy` frontmatter field (extension to Phase 403 STEP-PLAN-FORMAT.md frontmatter schema; DEV-06 consumes):
```python
class SliceFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... existing v40+Phase 403 fields ...
    autonomy: Literal["tiered","full-yolo","conservative"] | None = None  # DEV-06
    allowed_subagents: list[SubagentType] | None = None                   # SUB-03 (Plan 02 owns)
    subagent: SubagentSliceConfig | None = None                           # SUB-04 (Plan 02 owns)
```

Excerpt B — `EventEnvelope` from src/state_core/schema.py (every event in this spec rides this envelope; v40 EVENT-TAXONOMY.md convention `state.{tier}.{action}`):
```python
class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = ""               # ULID
    seq: int = 0               # per-aggregate monotonic sequence
    aggregate_type: str = "arc"
    aggregate_id: str = ""
    type: str = ""             # e.g. "state.step.deviation_logged"
    data: dict[str, Any] = {}
```

Excerpt C — Phase 404 `GateStrike` per-tuple counter discipline (DEV deviation chain mirrors this exact tuple shape):
```python
# Per-(task_id, check_id) tuple, 6-strike ladder; resets on success
# Reference: .planning/milestones/v41/phases/404/specs/PROOF-GATE.md Section 6
```
DEV deviation chain diverges: per-(task_id, rule_id, issue_signature) tuple; 3-attempt cap (not 6); Rules 1-3 escalate to Rule 4 or checkpoint:decision; Rule 4 immediately human-gates.

Excerpt D — Phase 404 `scope_deviation_request` MCP shape (DEV cross-validation step 4 correlates against open requests):
```python
# Reference: .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md §SRP-04
# log_deviation correlates open scope_deviation_request (task_id, requested_path)
# against the arch-pattern allowlist; match -> force rule_id=4
```

Excerpt E — gsd-2 `infer_commit_type` 7-rule keyword-based inference (state extends with STATE-* trailers; cite verbatim):
```typescript
// Reference: ~/projects/gsd2deconstruction/kb/walkthroughs/git-service.ts.md:616
// state/src/state_build/commit/trailers.py adapts; keyword table unchanged
// New trailers added: STATE-Task, STATE-DeviationRule, STATE-DeviationAttempt, STATE-Subagent-Invocation
```
</interfaces>

<threat_model>
Phase 405 is design-only. DEVIATION-RULES.md introduces no production attack surface — it is a markdown specification. Threats considered (per `<security_constraint>` and ASVS L1 baseline):

- **[high] Rule-4 autonomy bypass**: If the spec leaves the Rule-4 always-stop rule as a policy check (`if mode != 'full-yolo'`), an LLM that mis-classifies an architectural change could land an irreversible migration under `--full-yolo`. **Mitigation in spec:** Rule-4 always-human-gate is STRUCTURAL — the `log_deviation(rule_id=4)` MCP handler synchronously calls opencode `question` tool; there is no autonomy short-circuit code path. Spec MUST state "no `if mode == 'full-yolo' bypass` branch exists" verbatim. Cross-validation flow step 2 enforces `alternatives is not None and len >= 2 and exactly one recommended=True` before the question fires.

- **[high] Classification spoofing**: If the agent self-classifies `rule_id=1` for a schema migration (arch change), the harness must catch this. **Mitigation in spec:** cross-validation step 3 (Rule-4 auto-promotion) recomputes against `ARCH_PATTERN_ALLOWLIST` at the `tool.execute.before` write-target. Mismatch -> reject + `deviation_classification_rejected` event. The arch-pattern allowlist is rendered verbatim and lives at a named single-source-of-truth module.

- **[high] Naming-discipline drift (STATE-* vs GSD-*)**: Past phases (403, 404) drifted into GSD-* trailer references; Phase 405 specs MUST use STATE-* exclusively (project cardinal rule from CLAUDE.md + user memory). **Mitigation in spec:** explicit subsection "Naming Discipline" naming all four STATE-* trailers; the v40 amendment in Plan 04 will register them. CI grep `grep -nE '\\bGSD-' .planning/milestones/v41/phases/405/` MUST return zero. Spec author verifies before commit.

- **[med] Counter cross-contamination between three chains**: APG, PRF, and DEV chains must remain independent (gsd-2 loop-control.md Correction 1). **Mitigation in spec:** explicit "Three-counter independence" subsection with a 4-row table showing chain / per-tuple key / trigger / owner. Forward-pointer to Phase 406 HRN-05 harness_intervention umbrella is the SOLE rollup point.

- **[med] issue_signature collision via OS/env nondeterminism**: If issue_signature included full stack traces, different OS/Python builds would compute different hashes for the same logical failure. **Mitigation in spec:** whole-stack hashing is REJECTED explicitly; signature inputs are limited to (error_kind, file_path, line_no, matched_token) — all deterministic across hosts. Spec includes the literal `compute_issue_signature` function.

- **[med] Append-only mutation of `Deviation.resolution`**: Single-mutable-row pattern via `deviation_resolution_recorded` event must preserve replay determinism. **Mitigation in spec:** the row's terminal state is recomputed via event replay (latest `deviation_resolution_recorded.resolution` wins); never edited in-place. Spec stipulates the projector applies events in event-store seq order.

- **[low] `## Deviations` SUMMARY temp+rename race**: Atomic write via temp+rename, but the read cache invalidation could lag. **Mitigation in spec:** mirrors 404 N-VERIFICATION.md projector pattern (acknowledged not-yet-atomic per Phase 402 §7.3 note; v44 follow-up); spec carries the same forward-pointer.

- **[low] Mode-isolation drift**: Build-only spec. **Mitigation:** explicit "Build-mode only" header note; deviation module path `state_build/deviation/`; events go in `BUILD_ONLY_EVENT_PREFIXES`; CI import-graph lint enforces.

No production code lands. No secrets. No network calls. No untrusted input parsed by the spec doc itself. The spec describes runtime mechanisms; threats listed above target v14 implementation, which Phase 405's spec must constrain via authoritative Pydantic/regex/protocol shapes.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author DEVIATION-RULES.md sections 1-5 (header, 4 rules, log_deviation MCP tool, cross-validation flow, arch-pattern allowlist, commit trailers)</name>
  <files>
    .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/405/405-CONTEXT.md lines 1-300 (full domain + decisions blocks through "Continuation context on restart" — verbatim source for Rule 1-4 specs, log_deviation signature, cross-validation flow, arch-pattern allowlist, commit trailers)
    - .planning/milestones/v41/REQUIREMENTS.md lines 89-100 (DEV-01..DEV-07 verbatim)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file — gate_strike per-tuple counter discipline; Section 6 strike-counter semantics; mirrors deviation 3-attempt-cap pattern)
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (full file — scope_deviation_request shape; cross-validation step 4 correlates against open requests)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (search "per-(task_id, check_id)" — counter scope precedent)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — frontmatter schema Slice.autonomy field extension lands here)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md lines 1-100 (naming convention state.{tier}.{action}; this spec adds state.step.deviation_* events — full event list registered by Plan 04)
    - .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md lines 1-100 (Pydantic extra="forbid" convention)
    - .planning/milestones/v41/phases/404/01-proof-gate-spec-PLAN.md lines 1-130 (Phase 404 spec-doc plan reference for verbose format/density target)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md`. Sections 1-5 below; Task 2 owns sections 6-10. **Concrete content from 405-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 1 — File header

    ```
    # Deviation Rules & Tiered Autonomy (Canonical, v41)

    > **Phase:** 405
    > **Status:** Canonical (v41)
    > **Requirements covered:** DEV-01..DEV-07
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
    > **Sibling specs:** SUBAGENT-MANAGEMENT.md (subagent typed-spawn + spot-check + crash recovery — Phase 405 Plan 02-03).
    > **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Past-phase `GSD-*` trailer references are deferred-rename items.
    > **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
    ```

    1-paragraph overview: the harness governs deviation from a Step's locked PLAN via a 4-rule framework. Each rule has a category (bug fix / missing critical functionality / blocking issue / architectural change), a max-attempts cap, a commit-prefix convention, and an escalation path. Agent declares the rule via `log_deviation` MCP tool; harness cross-validates against pure-machine signals (issue_signature recomputation, arch-pattern allowlist, scope_deviation_request correlation, cap check). Rule 4 (architectural) is structurally always-human-gate — no autonomy mode can bypass. Tiered autonomy (`--tiered` default / `--full-yolo` / `--conservative`) gates the other rule outcomes; per-Slice autonomy override allowed. Three-counter independence (APG / PRF / DEV) is preserved per gsd-2 `loop-control.md` Correction 1.

    ### Section 2 — The Four Rules (DEV-01..DEV-04)

    Heading: `## The Four Rules`.

    Sub-heading per rule. Each rule entry contains: category description, max-attempts (literal), commit-prefix convention, escalation path.

    Render `## Rule 1: Auto-fix Bugs (DEV-01)`:
    - **Category:** wrong queries, logic errors, type errors, null-pointer dereference.
    - **max-attempts: 3** (cap enforced per `(task_id, rule_id=1, issue_signature)`).
    - **Commit-prefix convention:** `fix: <description>` per gsd-2 `COMMIT_TYPE_RULES`; trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 1`, `STATE-DeviationAttempt: K` (K in {1,2,3}).
    - **Escalation path:** after 3 failed attempts on the same tuple, harness emits `deviation_cap_exceeded` and force-promotes to Rule 4 (the assumption: persistent bug-fix failures indicate a structural/architectural problem requiring human resolution).

    Render `## Rule 2: Auto-add Critical Functionality (DEV-02)`:
    - **Category:** missing error handling, missing input validation, missing null checks, missing auth on protected routes, missing DB indexes.
    - **max-attempts: 3**.
    - **Commit-prefix convention:** `feat:` if adding a new capability; `fix:` if patching a missed safety check (gsd-2 keyword inference applies); trailers `STATE-Task`, `STATE-DeviationRule: 2`, `STATE-DeviationAttempt: K`.
    - **Escalation path:** documented in `stepNSUMMARY.md` `## Deviations` section (auto-rendered by the projector — Section 9). After 3 failed attempts: same `deviation_cap_exceeded` -> Rule 4 promotion as Rule 1.

    Render `## Rule 3: Auto-fix Blocking Issues (DEV-03)`:
    - **Category:** missing dependency, wrong types in upstream contract, broken imports, build config errors.
    - **max-attempts: 3**.
    - **Commit-prefix convention:** `fix:` (typically); trailers `STATE-Task`, `STATE-DeviationRule: 3`, `STATE-DeviationAttempt: K`.
    - **Escalation path:** after 3 failed attempts -> `checkpoint:decision` (Phase 403 task-type) presenting the resolution options to the human via opencode `question` tool. Diverges from Rules 1-2 (which promote to Rule 4): blocking issues are often choice-shaped (which dep to pin? roll back the import?) rather than architectural-shaped.

    Render `## Rule 4: Architectural Changes (DEV-04)`:
    - **Category:** new DB table, major schema change, switching frameworks, new infrastructure (CDN, queue, cache).
    - **max-attempts: 1** (Rule 4 is single-shot: render question -> resolution arrives -> attempt complete).
    - **Commit-prefix convention:** typically `feat:`; trailers `STATE-Task`, `STATE-DeviationRule: 4`, `STATE-DeviationAttempt: 1`.
    - **Escalation path:** ALWAYS human gate via opencode `question` tool with a pros/cons table. Never auto-approved, even under `--full-yolo`. The `log_deviation(rule_id=4, ...)` MCP handler synchronously renders the question; there is no autonomy short-circuit branch in the harness. The `alternatives: list[Rule4Option]` payload is REQUIRED (Pydantic-validated; at least 2 options; exactly one `recommended=True`).

    Add a 1-paragraph note after the 4 rule subsections: "**Rule-4 always-stop is STRUCTURAL, not policy.** The implementation guarantee: there is no `if mode == 'full-yolo' bypass` code path. The `log_deviation(rule_id=4)` MCP handler unconditionally renders opencode `question`. This pattern mirrors gsd-2's MCP-tool-call-as-canonical-agent-intent-signal (`tool-system.md` §5); state extends with strict cross-validation."

    ### Section 3 — `log_deviation` MCP Tool

    Heading: `## log_deviation MCP Tool`.

    Sub-section `### Signature (Pydantic-typed)`:
    Quote verbatim from 405-CONTEXT.md `<decisions>` "Deviation classification" subsection — the `log_deviation` function signature + the `Rule4Option` + `DeviationLogResult` Pydantic classes. Use `python` code-fence. Cite the source: "Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` 'Deviation classification (DEV-01..04 expanded)' subsection."

    Sub-section `### MCP tool registration`:
    "The tool is registered under the `state-build` MCP server at module path `state_build/deviation/log_deviation.py`. The MCP tool name is the literal string `log_deviation`. The handler is invoked from the daemon's middleware (single source of truth — daemon decides). The handler returns `DeviationLogResult` synchronously."

    Sub-section `### Caller responsibilities (agent side)`:
    - Compute `issue_signature` via the SHA-256 16-char-hex function (Section 7); pass it as input. Harness recomputes for verification.
    - Set `classification_source = "agent_declared"` for self-classified deviations. Harness MAY override to `"harness_promoted"` (cross-validation step 3) or `"arch_pattern_match"` (step 4) before event emit.
    - For `rule_id == 4`: supply at least 2 `Rule4Option` entries with exactly one `recommended=True`. Pros/cons strings ≤512 chars each (Pydantic-validated).
    - `justification` ≤ 1KB, `error_excerpt` ≤ 2KB (gsd-2 `formatFailureContext` truncation discipline; mirrors 404 bounded-truncation 2KB/10KB pattern).

    Sub-section `### Return shape`:
    Quote `DeviationLogResult` verbatim with the 5 fields. Explain semantics:
    - `deviation_event_id`: ULID; the primary key of the just-emitted `state.step.deviation_logged` event.
    - `attempt_number`: 1..3 for Rules 1-3 (computed by harness from the per-tuple counter +1); always 1 for Rule 4.
    - `cap_exceeded`: True when this attempt is the 4th — auto-escalation already triggered server-side.
    - `classification_accepted`: False if cross-validation rejected the declared `rule_id` (rejection event already emitted; agent must re-call with corrected `rule_id` + payload).
    - `rejection_reason`: set when `classification_accepted` is False (one of: `"issue_signature_mismatch"`, `"rule_4_alternatives_missing"`, `"rule_4_recommended_invalid"`, `"arch_pattern_promotion_required"`, `"scope_deviation_correlation_promoted"`).

    ### Section 4 — Harness Cross-Validation Flow

    Heading: `## Harness Cross-Validation Flow`.

    1-paragraph intro: post-call (before event emit), the daemon runs a 5-step pure-machine validation against the proposed deviation. Mismatch -> rejection event + `classification_accepted=False` return. Mirrors 404's diff-the-proposed-write pattern (cross-validation against deterministic signals).

    Sub-section `### Numbered protocol`:

    Render verbatim:

    1. **Re-compute `issue_signature`** from the current `(task_id, rule_id, error_kind, file:line, matched_token)` tuple via the SHA-256 function (Section 7). Compare with agent-supplied value. Disagreement -> emit `state.step.deviation_classification_rejected` with `reason: "issue_signature_mismatch"`, return early.
    2. **Rule-4 alternatives check:** if `rule_id == 4`, require `alternatives is not None and len(alternatives) >= 2 and sum(o.recommended for o in alternatives) == 1`. Mismatch -> emit `state.step.deviation_classification_rejected` with `reason: "rule_4_alternatives_missing"` or `"rule_4_recommended_invalid"`, return early.
    3. **Rule-4 auto-promotion (arch-pattern allowlist):** scan the agent's recent `Write/Edit` targets (sourced from `tool.execute.before` event audit, last 60s window) against `ARCH_PATTERN_ALLOWLIST` (Section 5). If `rule_id ∈ {1,2,3}` but a recent write hits the allowlist -> emit `state.step.deviation_classification_rejected` with `reason: "arch_pattern_promotion_required"`; agent must re-call with `rule_id=4` and an `alternatives` payload.
    4. **`scope_deviation_request` correlation:** if there's an open `state.step.scope_deviation_request` (Phase 404 SRP-04) for this `(task_id, requested_path)` AND the path matches the arch-pattern allowlist, force `rule_id=4`. Emit `state.step.deviation_classification_rejected` with `reason: "scope_deviation_correlation_promoted"` if the agent supplied a lower `rule_id`.
    5. **Cap check:** query event store for `count(state.step.deviation_logged WHERE (task_id, rule_id, issue_signature) = ?)`. If `count >= 3` (this would be the 4th attempt) -> set `cap_exceeded=True`; emit `state.step.deviation_cap_exceeded`; auto-escalate per the rule's escalation path (Rule 3 -> `checkpoint:decision`; Rules 1-2 -> force Rule-4 promotion). Event emit for the original `deviation_logged` STILL happens (audit trail completeness), but with `resolution: "aborted_chain"`.

    Add a 1-line ordering note: "Steps 1-5 run in deterministic order. Step 5 (cap check) runs LAST because the cap-exceeded path still emits the `deviation_logged` event for audit. Earlier steps short-circuit (return early on rejection). v14 implements as a synchronous chain inside `state_build/deviation/log_deviation.py`."

    Sub-section `### Server-side recomputation discipline`:
    "Harness recomputes `issue_signature`, `attempt_number`, `cap_exceeded`, and `classification_source` from authoritative server-side state; agent-emitted values for these fields are recomputed (mirrors 404's PRF `overall_passed` server-recomputation pattern + gsd-2's `server-recomputation-of-llm-emitted-fields.md`). Mismatch between agent input and server recomputation triggers the rejection events listed above. The `classification_source` field's final value is server-set: `agent_declared` (default) -> `harness_promoted` (cross-validation step 3 override) -> `arch_pattern_match` (step 4 override)."

    ### Section 5 — Arch-Pattern Allowlist (Rule-4 Detection)

    Heading: `## Arch-Pattern Allowlist (Rule-4 Detection)`.

    1-paragraph intro: the canonical pure-machine signal for an architectural change is a Write/Edit target matching the arch-pattern allowlist. Mirrors 404's `READ_ONLY_PATTERNS` + `WRITE_SYSCALL_PATTERNS` single-module shape; lives at `state_build/deviation/arch_patterns.py`.

    Sub-section `### Regex allowlist`:
    Quote verbatim the Python list `ARCH_PATTERN_ALLOWLIST` from 405-CONTEXT.md `<decisions>` "Rule-4 detection" subsection — all six `re.compile(...)` patterns. Render as `python` code-fence with the literal module-level constant.

    Sub-section `### Match semantics`:
    - Match is against the **proposed write target path** (the file path the agent attempts to Write/Edit), intercepted via `tool.execute.before`. Not against existing on-disk content.
    - Paths are normalized to repo-root-relative POSIX form (forward slashes always) before matching.
    - First-match-wins; the order in the list is not semantically significant beyond determinism (mirrors gsd-2 `dispatch-rules-table.md` pattern).

    Sub-section `### ADD vs BUMP discrimination (pyproject.toml / uv.lock)`:
    Render verbatim:
    - **Pure-machine diff parse.** Lines beginning `+` matching regex `^\+\s*"[a-zA-Z0-9_\-]+>=` match the **ADD** pattern (adding a new dependency).
    - Lines matching `-\s*"X>=A.B"\s*\n\+\s*"X>=C.D"` (same package name, only version delta) match the **BUMP** pattern.
    - **ADD -> arch-pattern match (force Rule 4).** A new dependency is an architectural decision.
    - **BUMP -> no auto-promotion.** Version pin updates are routine (Rule 3 or below).
    - **Multi-line YAML/TOML edge cases** (e.g., `pyproject.toml` `dependencies = [...]` array spanning many lines): planner pins exact tokenizer in v14; for now the discriminator regex above is the starter set.

    Sub-section `### Module ownership`:
    "Single-source-of-truth module: `state_build/deviation/arch_patterns.py`. Exports: `ARCH_PATTERN_ALLOWLIST: list[re.Pattern]`, `match_arch_pattern(path: str) -> bool`, `classify_diff_kind(file_path: str, diff_text: str) -> Literal['ADD','BUMP','NEITHER']`. v14 implements; v15 uses at the daemon middleware layer."

    Sub-section `### Commit Trailer Convention (STATE-* Naming Discipline)`:
    Render verbatim:

    State keeps gsd-2's 7-rule keyword-based type-inference table (`COMMIT_TYPE_RULES`, sourced from `git-service.ts:616`) unchanged for the conventional-commit prefix selection. State adds new trailers:

    ```
    fix: resolve null-pointer in CompactionSnapshot.serialize

    Restore the missing None-guard before orjson.dumps.

    STATE-Task: 405-deviation-rules/step-2
    STATE-DeviationRule: 1
    STATE-DeviationAttempt: 1
    ```

    - `STATE-Task: <step_id>` — mandatory on every commit produced inside a Step.
    - `STATE-DeviationRule: N` (N ∈ {1,2,3,4}) — mandatory on every commit produced as the resolution of an open deviation.
    - `STATE-DeviationAttempt: K` (K ∈ {1,2,3}) — mandatory alongside `STATE-DeviationRule`.
    - `STATE-Subagent-Invocation: <invocation_id>` — mandatory on every commit produced inside a subagent session (Plan 02 owns this trailer; cited here for completeness).

    **Auditor grep target:** `git log --grep="STATE-DeviationRule: 4"` enumerates every architectural change ever made. CI grep `grep -nE '\bGSD-' .planning/milestones/v41/phases/405/` MUST return zero (project naming discipline — STATE-* only).

    **Single-source-of-truth module:** `state_build/commit/trailers.py` exports the trailer constants + the `infer_commit_type(message: str, files: list[str]) -> Literal['fix','feat','refactor','docs','test','chore','perf']` function (adapted from gsd-2's `git-service.ts` keyword table). v14 implements.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Deviation classification (DEV-01..04 expanded)" subsection — log_deviation signature + Rule4Option + DeviationLogResult Pydantic classes are rendered verbatim; do NOT re-derive.
        - Known: `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Rule-4 detection" subsection — ARCH_PATTERN_ALLOWLIST 6-regex list rendered verbatim.
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` Section 6 — per-(task_id, check_id) tuple counter discipline; cite as precedent for DEV per-(task_id, rule_id, issue_signature) tuple.
        - Known: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` §SRP-04 — scope_deviation_request shape; cross-validation step 4 cites this.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md | head -40` — confirms heading hierarchy depth used in v41 spec docs.
        - Grep pattern: `grep -nE "model_config = ConfigDict" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` — locates verbatim Pydantic class rendering pattern.
        - Grep pattern: `grep -c 'STATE-' /Users/tmac/Projects/state/.planning/milestones/v41/phases/405/405-CONTEXT.md` — confirms STATE-* trailer pattern in source CONTEXT.
      </code_to_reuse>
      <docs_to_consult>
        - 405-CONTEXT.md `<decisions>` Deviation classification (DEV-01..04 expanded) — verbatim source for Sections 2, 3.
        - 405-CONTEXT.md `<decisions>` Attempt-counter semantics (DEV-07 expanded) — verbatim source for Section 4 cap check + Section 6 (Task 2).
        - 405-CONTEXT.md `<decisions>` Rule-4 always-human-gate semantics (DEV-04 + DEV-05 expanded) — verbatim source for Section 2 Rule 4 + Section 6 autonomy table (Task 2).
        - 405-CONTEXT.md `<specifics>` "Rule 4 always-stop is the autonomy table's 4th column" — verbatim source for the structural-not-policy framing.
        - Phase 404 PROOF-GATE.md Section 6 — strike-counter scope precedent; DEV per-tuple discipline mirrors.
        - gsd-2 `loop-control.md` §0 Correction 1 — three-counter independence rationale (Section 6 / Task 2).
        - gsd-2 `git-service.ts.md:616` — COMMIT_TYPE_RULES keyword table; state extends with STATE-* trailers.
        - gsd-2 `server-recomputation-of-llm-emitted-fields.md` — defensive recomputation pattern; Section 4 sub-section cites.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's log_deviation handler unit tests will assert against the Pydantic class definitions in this spec as fixtures; this spec doc is the contract those tests assert against.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 280)}' \
        && grep -qE "^# Deviation Rules" "$F" \
        && grep -qE "^## The Four Rules" "$F" \
        && grep -qE "^## Rule 1: Auto-fix Bugs \(DEV-01\)" "$F" \
        && grep -qE "^## Rule 2: Auto-add Critical Functionality \(DEV-02\)" "$F" \
        && grep -qE "^## Rule 3: Auto-fix Blocking Issues \(DEV-03\)" "$F" \
        && grep -qE "^## Rule 4: Architectural Changes \(DEV-04\)" "$F" \
        && grep -qE "^## log_deviation MCP Tool" "$F" \
        && grep -qE "^## Harness Cross-Validation Flow" "$F" \
        && grep -qE "^## Arch-Pattern Allowlist" "$F" \
        && grep -q "max-attempts: 3" "$F" \
        && grep -q "ARCH_PATTERN_ALLOWLIST" "$F" \
        && grep -q "STATE-DeviationRule" "$F" \
        && grep -q "STATE-DeviationAttempt" "$F" \
        && grep -q "STATE-Task" "$F" \
        && grep -q "log_deviation" "$F" \
        && grep -q "Rule4Option" "$F" \
        && grep -q "DeviationLogResult" "$F" \
        && grep -q 'model_config = ConfigDict(extra="forbid")' "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] DEVIATION-RULES.md exists at the spec'd path and is ≥ 280 lines after Task 1 (Task 2 brings it to ≥ 600).
    - [check: must_haves.truths[1]] All four `## Rule N: ...` headings render verbatim.
    - [check: must_haves.truths[2]] `max-attempts: 3` literal appears in the rule entries; commit-prefix trailers appear with STATE-* names.
    - [check: must_haves.truths[3]] Rule 4 structural-not-policy framing is rendered verbatim.
    - [check: must_haves.truths[4]] `log_deviation` signature with Rule4Option + DeviationLogResult is rendered verbatim with `extra="forbid"`.
    - [check: must_haves.truths[5]] 5-step cross-validation protocol is rendered with the exact rejection-event names.
    - [check: must_haves.truths[6]] ARCH_PATTERN_ALLOWLIST 6-regex list is rendered verbatim and `state_build/deviation/arch_patterns.py` module path is named.
    - [check: must_haves.truths[7]] ADD/BUMP discrimination regex pair is rendered with the verdict (ADD -> Rule 4; BUMP -> no auto-promotion).
    - [check: must_haves.truths[8]] STATE-* trailer convention is rendered verbatim; auditor grep target `git log --grep="STATE-DeviationRule: 4"` is named.
    - [check: must_haves.truths[20]] No `GSD-` literal string appears in the file (project naming-discipline rule).
  </acceptance_criteria>

  <done>
    DEVIATION-RULES.md exists at the spec'd path; Task 1 sections 1-5 render verbatim per the action body; file is ≥ 280 lines (Task 2 brings it to ≥ 600); verify-block bash passes (every grep hits; no `GSD-` literal in the file).
  </done>
</task>

<task type="auto">
  <name>Task 2: Author DEVIATION-RULES.md sections 6-10 (tiered autonomy table, per-Slice override, issue_signature derivation, three-counter independence, Deviation event payload, ## Deviations SUMMARY projector)</name>
  <files>
    .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md (the file Task 1 just authored — append sections 6-10 below Task 1's content)
    - .planning/milestones/v41/phases/405/405-CONTEXT.md lines 300-720 (decisions blocks "Attempt-counter semantics", "Rule-4 always-human-gate semantics", "`## Deviations` SUMMARY section projector" — verbatim source for Sections 6-10)
    - .planning/milestones/v41/REQUIREMENTS.md lines 89-100 (DEV-01..DEV-07 verbatim)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file — Section 6 strike-counter discipline mirrored; Section 8 N-VERIFICATION.md projector pattern mirrored)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (search "loop-control.md" — gsd-2 three-counter-independence rationale)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — Slice frontmatter `autonomy` field extension; DEV-06 lands here)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "stepNSUMMARY" — SUMMARY.md generation precedent)
    - .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md (full file — event-naming convention; this spec adds 4 new state.step.deviation_* events)
  </read_first>

  <action>
    Append sections 6-10 to `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md`. **Concrete content from 405-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 6 — Tiered Autonomy Table (DEV-05) + Per-Slice Override (DEV-06)

    Heading: `## Tiered Autonomy (DEV-05, DEV-06)`.

    1-paragraph intro: the harness's per-checkpoint-type behavior is governed by an autonomy mode set at the milestone default, optionally overridden per Slice. The mode determines whether `checkpoint:human-verify` / `checkpoint:decision` / `checkpoint:human-action` auto-resolve or stop. Rule-4 deviations are the 4th column and always stop regardless of mode (structural, not policy).

    Sub-section `### Autonomy modes`:

    Render the 4-column markdown table verbatim:

    | Mode | `checkpoint:human-verify` | `checkpoint:decision` | `checkpoint:human-action` | **Rule 4 deviation** |
    |---|---|---|---|---|
    | `--tiered` (default) | auto-approve | stop | stop | **stop** |
    | `--full-yolo` | auto-approve | auto-pick option 1 | stop | **stop** |
    | `--conservative` | stop | stop | stop | **stop** |

    Add the 1-paragraph implementation note verbatim from 405-CONTEXT.md: "The autonomy table's first three columns are inherited verbatim from Phase 403 task-type behaviors; the fourth column (Rule 4 deviation) is novel to Phase 405. Implementation guarantee: the `log_deviation(rule_id=4, ...)` MCP handler synchronously renders opencode `question` tool with the `alternatives` payload — **there is no autonomy short-circuit code path**. The structural enforcement is the absence of an `if mode == 'full-yolo' bypass` branch in `state_build/deviation/log_deviation.py`."

    Sub-section `### Per-Slice override (DEV-06)`:

    Render verbatim:
    - **Slice frontmatter field:** `autonomy: Literal["tiered","full-yolo","conservative"] | None = None`. Lives at the **Slice** level only — there is no Step-level override (locked by Phase 403's "`autonomy` is NOT a Step frontmatter field" decision).
    - **Precedence rule:** `milestone default -> Slice override -> done`. The effective autonomy for any deviation/checkpoint decision is `Slice.frontmatter.autonomy ?? milestone.autonomy_default`.
    - **Direction:** the Slice override CAN move stricter (e.g., milestone `--tiered`, Slice `--conservative`) AND CAN move looser (e.g., milestone `--tiered`, Slice `--full-yolo`). **Narrowing-only does NOT apply to autonomy** — autonomy is policy, not capability. The narrowing-only rule (which applies to `allowed_subagents` per SUB-03, Plan 02) is capability-only.
    - **Rationale:** mirrors gsd-2's permissive-vs-strict trust-model divergence (`precedence-divergence-by-trust-model.md`); state's permissive-pole choice here reflects the user-controlled-runtime framing.

    ### Section 7 — `issue_signature` Derivation (DEV-07 expanded)

    Heading: `## issue_signature Derivation`.

    1-paragraph intro: the per-tuple counter requires a deterministic, host-independent identifier for "the same logical failure." `issue_signature` is a SHA-256 16-char hex of canonicalized inputs.

    Sub-section `### Function`:

    Render the `compute_issue_signature` function verbatim from 405-CONTEXT.md `<decisions>` "Attempt-counter semantics" subsection:

    ```python
    def compute_issue_signature(
        error_kind: ErrorKind,
        file_path: str,                                      # repo-root-relative POSIX
        line_no: int,                                        # 1-indexed
        matched_token: str,                                  # failing token / error head / scanner match
    ) -> str:
        canonical = f"{error_kind.value}|{file_path}|{line_no}|{matched_token}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    ```

    Sub-section `### ErrorKind enum`:

    Render the `ErrorKind` Literal/Enum verbatim with all 10 starter values: `pytest_failure`, `type_error`, `import_error`, `null_dereference`, `schema_validation_failure`, `scope_violation`, `paralysis_threshold_cross`, `proof_gate_failure`, `subagent_spot_check_failure`, `other`. Use `class ErrorKind(str, Enum)` syntax.

    1-line note: "Open-ended; planner extends in v14 as new failure modes surface (recommended additions deferred to v14 EXEMPLAR: `oauth_refresh_failure`, `worktree_checkout_failure`, `pygit2_lock_contention`, `mcp_tool_validation_failure`)."

    Sub-section `### Why whole-stack hashing is rejected`:

    Render verbatim: "Whole-stack hashing — i.e., including the Python stack trace in the signature inputs — is **rejected**. Research confirmed OS/env differences make stack traces nondeterministic across hosts. The 4-tuple `(error_kind, file_path, line_no, matched_token)` is the minimum-spec set that preserves cross-host determinism while still distinguishing logically-distinct failures."

    Sub-section `### matched_token extraction`:

    "When the error has a clear failing token (e.g., a Python identifier in a TypeError, a missing import name, a failing pytest assertion's left-hand operand), use that token. When the error has no clear token, fall back to the first line of the error message truncated to 64 characters. v14 finalizes the exact extraction rule."

    Sub-section `### file_path canonicalization`:

    "Repo-root-relative POSIX form (forward slashes always). Computed via `pathlib.PurePosixPath` against the worktree root. Symlinks resolved; `.`/`..` segments normalized. v14 pins the exact `os.path.relpath` vs `pathlib.PurePosixPath.relative_to` strategy; both produce the same canonical output for normal repo paths."

    ### Section 8 — Three-Counter Independence + Reset-on-Success

    Heading: `## Three-Counter Independence`.

    1-paragraph intro: state has three independent counter chains, each capable of independently reaching force-stop/human-gate. Each chain has its own per-tuple key and trigger. Conflating any pair violates gsd-2 `loop-control.md` §0 Correction 1.

    Sub-section `### Three independent chains`:

    Render the 4-column markdown table verbatim:

    | Chain | Per-tuple key | Trigger | Owner |
    |---|---|---|---|
    | APG `paralysis_event` | `(task_id,)` | N consecutive read-only operations | Phase 404 |
    | PRF `gate_strike` | `(task_id, check_id)` | Failed `must_haves.*` or `<verify>` at completion-claim | Phase 404 |
    | DEV `deviation_logged` | `(task_id, rule_id, issue_signature)` | `log_deviation` MCP call | Phase 405 |

    Add the 1-line forward-pointer: "**Umbrella event:** the `state.harness.intervention` event (HRN-05, owned by Phase 406) is the SOLE rollup point. All three chains cite it as `trigger_reason`. Mirrors gsd-2 `loop-control.md` §0 Correction 1's refusal to conflate four distinct counters at four scopes."

    Sub-section `### Counter scope and reset-on-success`:

    Render verbatim:
    - **Scope:** per-`(task_id, rule_id, issue_signature)` tuple. Wider scopes (Step-level, Slice-level) risk cross-task chain poisoning; narrower scopes (per-`invocation_id`) let the agent game by re-invoking with different prompts.
    - **Reset rule:** on success of the same `(task_id, rule_id, issue_signature)` tuple, the counter drops to 0. "Success" = the next pure-machine eval of that exact tuple returns success (failing test now passes; type error gone; scanner clean). Different tuples never share state.
    - **Rationale:** preserves audit clarity AND chain interpretability. The same tuple succeeding signals "this issue is resolved"; the counter dropping to 0 lets a future regression of the SAME issue start a fresh chain — distinguishable from "this issue has been retried 3 times and failed."
    - **Mirrors:** gsd-2's `consecutiveAllToolErrorTurns = 0`-on-success pattern (`agent-loop.ts:191`) AND Phase 404 PRF strike-chain-resets-on-success principle.

    Sub-section `### log_deviation mid-task semantics (different-from-PRF)`:

    Render verbatim: "`log_deviation` can be called any time during task execution; the harness records and counters increment. Mid-task incidental calls (e.g., agent realizes a fix attempt failed before commit) accrue toward the 3-attempt cap. Mirrors 404's 'strike accrues at completion-claim boundary' discipline NOT applied here — deviations are agent-declared explicitly, not inferred. v14 implements without a completion-claim guard at the MCP boundary."

    ### Section 9 — `Deviation` Event Payload + Append-Only Resolution Mutation

    Heading: `## Deviation Event Payload`.

    Sub-section `### Pydantic event schema`:

    Render the `Deviation` Pydantic class verbatim from 405-CONTEXT.md (14 fields including `deviation_event_id`, `task_id`, `step_id`, `slice_id`, `session_id`, `rule_id: Literal[1, 2, 3, 4]`, `issue_signature`, `attempt_number`, `classification_source`, `commit_sha`, `resolution: Literal['auto_fix_succeeded','auto_fix_failed','escalated_to_decision','escalated_to_human_gate','aborted_chain','pending']`, `alternatives`, `error_excerpt`, `agent_response_summary`, `triggered_at`, `intervention_event_id`). Use `python` code-fence with `model_config = ConfigDict(extra="forbid")`.

    Cite source: "Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` 'Attempt-counter semantics' subsection."

    Sub-section `### Event ring (4 new event types)`:

    Bulleted list:
    - `state.step.deviation_logged` — primary event; emitted by `log_deviation` MCP handler after cross-validation succeeds (or on cap-exceeded for audit completeness). Rides the `Deviation` Pydantic payload.
    - `state.step.deviation_classification_rejected` — emitted when any of cross-validation steps 1-4 rejects the agent's classification. Rides a `DeviationClassificationRejected` Pydantic payload: `{task_id, attempted_rule_id, reason: Literal['issue_signature_mismatch','rule_4_alternatives_missing','rule_4_recommended_invalid','arch_pattern_promotion_required','scope_deviation_correlation_promoted'], agent_response_summary, triggered_at, session_id}`.
    - `state.step.deviation_resolution_recorded` — append-only mutation event; updates the `Deviation` row's `resolution` from `pending` -> one of the 5 terminal values. Rides `{deviation_event_id, resolution, commit_sha, triggered_at}`.
    - `state.step.deviation_cap_exceeded` — emitted when cross-validation step 5 detects the 4th attempt on the same tuple. Rides `{task_id, rule_id, issue_signature, prior_attempt_count: int, escalation_path: Literal['rule_4_promotion','checkpoint_decision'], triggered_at, session_id}`.

    Sub-section `### Append-only mutation pattern`:

    Render verbatim: "**Single-mutable-row pattern.** The `Deviation` row's `resolution` field starts as `pending` at `deviation_logged` time; mutates to a terminal value via an append-only `deviation_resolution_recorded` event. The projector applies these events in event-store seq order; the latest `deviation_resolution_recorded.resolution` for a given `deviation_event_id` wins. **Replay determinism preserved** — never edited in-place; the event store is authoritative."

    Render the rejection-rationale verbatim: "**Two-event request/resolved split (404-style) rejected.** Diverges from Phase 404's `scope_deviation_request` / `scope_deviation_resolved` two-event split because the deviation lifecycle is short-lived (≤3 attempts) and lives within one task boundary; a single row simplifies the `## Deviations` SUMMARY projector. The mutation event is sufficient for replay determinism; v14 wires the resolution-mutation step inside `log_deviation` (success path) and inside the cross-validation rejection / cap-exceeded path."

    ### Section 10 — `## Deviations` SUMMARY Section Projector

    Heading: `## ## Deviations SUMMARY Section Projector`.

    1-paragraph intro: the projector renders the `## Deviations` section into `stepNSUMMARY.md` at task end by aggregating `deviation_logged` + `deviation_resolution_recorded` events for the current `(step_id, slice_id)`. The section is omitted entirely when zero deviations exist for the Step. Mirrors 404's `N-VERIFICATION.md` projector pattern + gsd-2's `db-writer.ts` projection discipline.

    Sub-section `### Algorithm (numbered)`:

    Render verbatim:

    1. Subscribe to `state.step.deviation_logged` + `state.step.deviation_resolution_recorded` events, filtered by `(step_id, slice_id)`.
    2. Aggregate by `(rule_id, issue_signature)` — one row per unique issue. Multiple attempts on the same tuple collapse to one row with `Attempts = max(attempt_number) / 3` (or `1 / 1` for Rule 4).
    3. Determine each row's `Resolution` by applying mutation events in event-store seq order; the latest `deviation_resolution_recorded.resolution` for the row's `deviation_event_id` wins. Rows with no resolution mutation render as `pending`.
    4. Render the markdown table (column order below) into the `## Deviations` section. Atomic write via temp+rename (acknowledged as not-yet-atomic per Phase 402 §7.3 note for `last-snapshot.md`; v44 follow-up applies).
    5. Invalidate the read cache (mirrors gsd-2 `invalidateStateCache()` + `clearParseCache()` trio in `db-writer.ts`).
    6. If zero rows aggregate, the `## Deviations` section is **omitted entirely** from `stepNSUMMARY.md` (do not render an empty section).

    Sub-section `### Column schema (8 columns)`:

    Render the 8-column markdown table schema verbatim:

    | Column | Source | Notes |
    |---|---|---|
    | `#` | row ordinal | Stable across runs (sorted by first `triggered_at`) |
    | `Rule` | `Deviation.rule_id` formatted as "Rule 1", "Rule 2", "Rule 3", "Rule 4" | |
    | `Issue` | `Deviation.error_excerpt[:120]` | gsd-2 truncation, ≤120 char excerpt |
    | `Source` | `Deviation.classification_source` | |
    | `Attempts` | `max(attempt_number) / 3` | "2 / 3" form; for Rule 4 always "1 / 1" |
    | `Resolution` | terminal `Deviation.resolution` | |
    | `Commit` | `Deviation.commit_sha[:7]` | short SHA; "—" if pending |
    | `When` | `Deviation.triggered_at` | ISO-8601 UTC |

    Sub-section `### Module ownership`:

    "Single-source-of-truth module: `state_build/projectors/deviation_summary.py`. Subscribes to the daemon's event-store SSE stream filtered by step_id; renders to `slices/N-name/stepNSUMMARY.md` `## Deviations` section. v14 implements; v15 wires from the verify-slice stage."

    Sub-section `### Mode-isolation`:

    "The projector module lives under `state_build/projectors/`; MUST NOT import from `state_teach/`. CI import-graph lint enforces. The `## Deviations` section is a Build-mode-only artifact."

    Sub-section `### Authoritative ordering`:

    "Pydantic class definitions in this spec are authoritative. The column-schema table is the canonical column-order definition; v14 unit tests assert the projector's output matches the column order byte-for-byte."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Attempt-counter semantics" subsection — `compute_issue_signature` function, `ErrorKind` enum, `Deviation` Pydantic payload rendered verbatim; do NOT re-derive.
        - Known: `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "`## Deviations` SUMMARY section projector" subsection — 5-step algorithm + 8-column table schema rendered verbatim.
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` Section 8 — N-VERIFICATION.md projector pattern; mirror for `## Deviations` projector.
        - Known: `.planning/milestones/v41/phases/404/404-CONTEXT.md` strike-counter-resets-on-success subsection — DEV reset-on-success rationale mirrors.
        - Grep pattern: `grep -nE 'state_build/projectors' /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` — locates projector module-path convention.
      </code_to_reuse>
      <docs_to_consult>
        - 405-CONTEXT.md `<decisions>` Attempt-counter semantics + Three-counter independence — verbatim source for Sections 6-8.
        - 405-CONTEXT.md `<decisions>` `## Deviations` SUMMARY section projector — verbatim source for Section 10.
        - Phase 404 PROOF-GATE.md Section 6 — strike-counter-reset-on-success precedent; Section 8 N-VERIFICATION.md projector mirrored.
        - gsd-2 `loop-control.md` §0 Correction 1 — three-counter independence rationale.
        - gsd-2 `db-writer.ts.md` §1, §2, §6, §10, §12 — projection cache-invalidation discipline.
        - Phase 403 STEP-PLAN-FORMAT.md — Slice frontmatter `autonomy` field extension consumed here.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's projector unit tests assert against the 8-column schema rendered here; this spec doc is the contract.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 600)}' \
        && grep -qE "^## Tiered Autonomy" "$F" \
        && grep -qE "^## issue_signature Derivation" "$F" \
        && grep -qE "^## Three-Counter Independence" "$F" \
        && grep -qE "^## Deviation Event Payload" "$F" \
        && grep -qE "^## ## Deviations SUMMARY Section Projector" "$F" \
        && grep -q "compute_issue_signature" "$F" \
        && grep -q "ErrorKind" "$F" \
        && grep -q "pytest_failure" "$F" \
        && grep -q "deviation_logged" "$F" \
        && grep -q "deviation_classification_rejected" "$F" \
        && grep -q "deviation_resolution_recorded" "$F" \
        && grep -q "deviation_cap_exceeded" "$F" \
        && grep -q "paralysis_event" "$F" \
        && grep -q "gate_strike" "$F" \
        && grep -q "state_build/projectors/deviation_summary.py" "$F" \
        && grep -q "state_build/deviation/arch_patterns.py" "$F" \
        && grep -qE "^\| Mode \|" "$F" \
        && grep -qE "\\-\\-full-yolo" "$F" \
        && grep -qE "\\-\\-conservative" "$F" \
        && grep -qE "\\-\\-tiered" "$F" \
        && ! grep -qE '\bGSD-' "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[10]] Tiered autonomy 4-column markdown table renders with `--tiered`/`--full-yolo`/`--conservative` rows + 4th column "**Rule 4 deviation**" all "stop".
    - [check: must_haves.truths[11]] Per-Slice autonomy override is documented with precedence `milestone default -> Slice override -> done`; narrowing-only does NOT apply note rendered verbatim.
    - [check: must_haves.truths[12]] `compute_issue_signature` function renders verbatim with sha256 16-char-hex output; whole-stack hashing rejection note rendered.
    - [check: must_haves.truths[13]] `ErrorKind` enum renders with 10 starter values; planner-extends-in-v14 note included.
    - [check: must_haves.truths[14]] Three-counter independence 4-column table renders with APG/PRF/DEV chains; forward-pointer to Phase 406 HRN-05.
    - [check: must_haves.truths[15]] Counter scope per-(task_id, rule_id, issue_signature); reset-on-success rule rendered.
    - [check: must_haves.truths[16]] `Deviation` Pydantic class renders verbatim with 14 fields + `extra="forbid"`.
    - [check: must_haves.truths[17]] Append-only `deviation_resolution_recorded` mutation pattern rendered; two-event split rejection rationale rendered.
    - [check: must_haves.truths[18]] `## Deviations` SUMMARY projector 5-step algorithm + 8-column schema rendered verbatim.
    - [check: must_haves.truths[19]] Projector module path `state_build/projectors/deviation_summary.py` named; gsd-2 db-writer.ts cite.
    - [check: must_haves.truths[20]] No `GSD-` literal string appears in the file.
    - [check: must_haves.artifacts[0]] File at the spec'd path with min_lines: 600.
  </acceptance_criteria>

  <done>
    DEVIATION-RULES.md is complete at ≥600 lines; sections 1-10 render verbatim per Tasks 1+2 action bodies; verify-block bash passes (every grep hits; no `GSD-` literal; line count ≥600).
  </done>
</task>

</tasks>

<verification>
After both tasks complete, run the slice-level verification block (mirrors Phase 404 plan pattern):

```bash
F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md

# All Section headers present
for section in \
  "^# Deviation Rules" \
  "^## The Four Rules" \
  "^## Rule 1: Auto-fix Bugs \(DEV-01\)" \
  "^## Rule 2: Auto-add Critical Functionality \(DEV-02\)" \
  "^## Rule 3: Auto-fix Blocking Issues \(DEV-03\)" \
  "^## Rule 4: Architectural Changes \(DEV-04\)" \
  "^## log_deviation MCP Tool" \
  "^## Harness Cross-Validation Flow" \
  "^## Arch-Pattern Allowlist" \
  "^## Tiered Autonomy" \
  "^## issue_signature Derivation" \
  "^## Three-Counter Independence" \
  "^## Deviation Event Payload" \
  "^## ## Deviations SUMMARY Section Projector"; do
  grep -qE "$section" "$F" || { echo "MISSING: $section"; exit 1; }
done

# Min lines
wc -l "$F" | awk '{ if ($1 < 600) { print "LINE_COUNT_FAIL: " $1; exit 1 } }'

# Naming discipline
! grep -qE '\bGSD-' "$F" || { echo "GSD_NAMING_VIOLATION"; exit 1; }

# Required Pydantic + Literal constructs
for term in \
  'model_config = ConfigDict(extra="forbid")' \
  'Literal\[1, 2, 3, 4\]' \
  'class Deviation' \
  'log_deviation' \
  'Rule4Option' \
  'DeviationLogResult' \
  'ARCH_PATTERN_ALLOWLIST' \
  'compute_issue_signature' \
  'ErrorKind' \
  'STATE-DeviationRule' \
  'STATE-DeviationAttempt' \
  'STATE-Task'; do
  grep -q "$term" "$F" || { echo "MISSING_TERM: $term"; exit 1; }
done

echo "DEVIATION-RULES.md verification OK"
```
</verification>

<success_criteria>
- DEVIATION-RULES.md exists at `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md` with ≥ 600 lines.
- All 4 rules + all 5 cross-validation steps + autonomy table + per-Slice override + 3 counter chains + Deviation event + ## Deviations projector are rendered verbatim per 405-CONTEXT.md.
- No `GSD-` literal string in the file (project naming discipline).
- All Pydantic class definitions render with `model_config = ConfigDict(extra="forbid")`.
- All 4 new event types are named (registered by Plan 04 in EVENT-TAXONOMY.md).
- DEV-01..DEV-07 fully covered.
</success_criteria>

<output>
After completion, create `.planning/milestones/v41/phases/405/01-deviation-rules-spec-SUMMARY.md` per CLAUDE.md mandatory-SUMMARY rule. Include: spec-doc final line count, sections rendered, requirement coverage (DEV-01..DEV-07 all addressed), forward-pointers to Plans 02-04 + Phase 406, naming-discipline verification result (`grep '\bGSD-' = 0`).
</output>
