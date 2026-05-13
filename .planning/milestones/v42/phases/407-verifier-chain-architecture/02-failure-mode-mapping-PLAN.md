---
phase: 407-verifier-chain-architecture
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - .state/build/quality/VERIFIER-CHAIN.md
autonomous: true
requirements:
  - VCH-06
must_haves:
  truths:
    - "VERIFIER-CHAIN.md contains a dedicated `## VCH-06 — Failure-Mode Mapping` section that maps every verifier (Step suite × 4 sub-verifiers + Step composite + Slice + Stage + Arc + Cross-Tier — 9 rows total) to one or more of the three failure-mode classes (retry-loop, human-gate, auto-fix-attempt) with explicit transition criteria."
    - "The 3-strike retry ladder semantics from CONTEXT.md are documented (per-`(task_id, check_id)` scope per v41 PRF-06; counter conflict-free across sub-verifiers)."
    - "Human-gate routing is specified as flowing through the opencode `question` MCP tool consistent with v41 D-10 / HRN-06."
    - "Auto-fix-attempt is defined as a deterministic harness pass (ruff --fix, black, isort) — NOT an agent retry and NOT an LLM-mediated fix; it applies only to the anti-pattern sub-verifier in v42 (extension path documented)."
  artifacts:
    - path: ".state/build/quality/VERIFIER-CHAIN.md"
      provides: "VCH-06 failure-mode mapping table + 3-strike ladder section appended after VCH-05"
      min_lines: 380
      contains_sections:
        - "## VCH-06 — Failure-Mode Mapping"
        - "### Failure-Mode Ladder (3-Strike)"
        - "### Auto-Fix-Attempt — Definition and Scope"
        - "### Human-Gate Routing"
  key_links:
    - from: ".state/build/quality/VERIFIER-CHAIN.md"
      to: "v41 PRF-06 (per-(task_id, check_id) retry counter scope)"
      via: "explicit citation in 3-strike ladder section"
    - from: ".state/build/quality/VERIFIER-CHAIN.md"
      to: "v41 HRN-06 (human-gate-only-via-opencode-`question`-tool rule)"
      via: "explicit citation in Human-Gate Routing section"
---

<threat_model>
ASVS L1. Phase 407 design-doc deliverable. Two relevant risks:

- **Ladder ambiguity (T-407-03)**: A vague failure-mode mapping that lets the harness silently downgrade `failed` to `warning`, or auto-fix-attempt that runs an LLM mediator, would defeat the pure-machine stance. **Mitigation**: section explicitly defines auto-fix-attempt as deterministic-tooling-only (verbatim list: `ruff --fix`, `black`, `isort`); acceptance grep enforces presence of "deterministic harness pass" wording AND absence of "LLM" within the auto-fix-attempt subsection.
- **Human-gate bypass (T-407-04)**: If human-gate routing is described informally (e.g., "ask the user"), implementers might inline a free-text prompt instead of using the constrained opencode `question` tool — opening a social-engineering / unbounded-trust surface. **Mitigation**: section explicitly cites v41 HRN-06 verbatim; acceptance grep requires the exact string "opencode `question`" AND "HRN-06".
</threat_model>

<objective>
Append the VCH-06 failure-mode mapping section to `VERIFIER-CHAIN.md` (already created by Plan 01). The section maps every verifier in the chain to one or more of {retry-loop, human-gate, auto-fix-attempt} with explicit transition criteria (3-strike counter, per-`(task_id, check_id)` scope, deterministic auto-fix scope, human-gate routing through opencode `question`).

Purpose: Lock the ladder semantics so the downstream harness implementation (v14 Build Kernel) knows exactly which tier escalates first, when, and how.

Output: ~90 lines appended to `.state/build/quality/VERIFIER-CHAIN.md`.
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
@.state/build/quality/VERIFIER-CHAIN.md
@.planning/milestones/v41/phases/404/404-CONTEXT.md
@.planning/milestones/v41/phases/406/406-CONTEXT.md
</context>

<interfaces>
<!-- Failure-mode triad and counter scope. Verbatim from 407-CONTEXT.md. -->

The 3 failure-mode classes (verbatim):
- `retry-loop` — re-dispatch the agent with failureContext bundle (kb §3.2 + §4.1).
- `human-gate` — route through opencode `question` MCP tool (v41 HRN-06); fail-closed until resolved.
- `auto-fix-attempt` — **deterministic harness pass** (ruff --fix, black, isort, similar pure-tooling). NOT an agent retry. NOT an LLM-mediated fix.

Retry counter scope (v41 PRF-06): per-`(task_id, check_id)` — no scope conflation across sub-verifiers.

3-strike threshold (carries forward from v41 PRF-06 + kb workflow-engine §9 stuck detector).
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Append VCH-06 mapping table + 3-strike ladder + auto-fix-attempt definition + human-gate routing section</name>
  <files>.state/build/quality/VERIFIER-CHAIN.md</files>
  <read_first>
    - .state/build/quality/VERIFIER-CHAIN.md (current state after Plan 01)
    - .planning/milestones/v42/phases/407-verifier-chain-architecture/407-CONTEXT.md (VCH-06 subsection in `<decisions>` block, verbatim)
    - .planning/milestones/v42/REQUIREMENTS.md (VCH-06 verbatim)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (PRF-04 pure-machine, PRF-06 3-strike per-`(task_id, check_id)` counter, PRF-07 write-block)
    - .planning/milestones/v41/phases/406/406-CONTEXT.md (HRN-06 human-gate-only-via-opencode-`question` rule)
  </read_first>
  <behavior>
    - A new `## VCH-06 — Failure-Mode Mapping` section is appended after VCH-05.
    - The section contains a comprehensive mapping table with one row per verifier (anti-pattern, stub-detector, security, goal-backward, Step composite, Slice rollup, Stage rollup, Arc rollup, Cross-Tier).
    - The 3-strike ladder is documented with explicit counter scope (per-`(task_id, check_id)`) citing PRF-06.
    - The auto-fix-attempt section enumerates the deterministic-tooling scope (ruff --fix, black, isort) and explicitly states "NOT an agent retry; NOT an LLM-mediated fix".
    - The human-gate routing section cites HRN-06 and names the opencode `question` MCP tool as the sole entrypoint.
  </behavior>
  <action>
    Append the following to `.state/build/quality/VERIFIER-CHAIN.md` after the `## VCH-05 — Cross-Tier Verifier` section (preserve all content above; only append).

    **Section header:** `## VCH-06 — Failure-Mode Mapping`

    **Intent paragraph:**
    "Every verifier in the chain maps to one or more failure-mode classes from the triad `{retry-loop, human-gate, auto-fix-attempt}`. The mapping below is normative — downstream harness implementation (v14 Build Kernel) consumes it directly. Defaults are layered: cheaper-tier first, escalate to next tier on tier-exhaustion. Pure aggregators (Slice / Stage / Arc) have no failure-mode of their own — they propagate child verdicts upward without action."

    **Mapping table:**

    | Verifier | Default failure-mode ladder | Counter scope (3-strike) | Notes |
    |---|---|---|---|
    | **anti-pattern** (Step sub) | `auto-fix-attempt` → `retry-loop` → `human-gate` | per-`(task_id, anti_pattern_check_id, file_path)` | Harness first runs deterministic formatter pass (`ruff --fix`, `black`, `isort`) for fixable patterns (unused imports, formatting, ordering). Remaining violations re-dispatch agent with failureContext (kb §3.2). After 3 retries on same `(pattern, file)` pair, escalate to human gate. |
    | **stub-detector** (Step sub) | `retry-loop` → `human-gate` | per-`(task_id, stub_check_id)` | Stubs require code-writing; no deterministic auto-fix. Re-dispatch agent with stub-trace evidence (Phase 408 STB-03 call-chain to user surface). 3-strike → human gate. **Known-Stubs registration (STB-04) bypasses** by promoting to KNOWN tier before the retry counter triggers. |
    | **security** (Step sub) | `retry-loop` → `human-gate` | per-`(task_id, security_check_id)` | Re-dispatch agent with mitigation-missing evidence cited `file:line`. 3-strike → human gate. |
    | **goal-backward** (Step sub) | `retry-loop` → `human-gate` | per-`(task_id, goal_backward_check_id)` | Re-dispatch agent with missing-must-have evidence (kb §4.3 recoverable failure pattern). 3-strike → human gate. |
    | **Step composite** | inherits from sub-verifier strikes; composite `failed` triggers a *single* failureContext bundle (union of sub-verifier evidence) for the agent's retry | per-`(task_id, check_id)` per v41 PRF-06 (no scope conflation between sub-verifiers) | The composite never has its own counter; it aggregates sub-verifier counters server-side. |
    | **Slice rollup** | none — pure aggregator | N/A | Child Step's failure mode owns retry. Slice rollup re-runs only on child verdict-flip events (event-driven re-aggregation per VCH-05 subsection). |
    | **Stage rollup** | none — pure aggregator | N/A | Child Slice's failure mode owns retry (which itself delegates to Step). |
    | **Arc rollup** | none — pure aggregator | N/A | Child Stage's failure mode owns retry. |
    | **Cross-Tier** | `human-gate` immediately | N/A — no retry counter | Regression means a previously-shipped Arc is now broken. Cannot auto-fix (harness pass can't choose remedy) or retry-loop (no agent action against current Arc fixes it). Routes to opencode `question` (HRN-06): rollback / patch-via-new-Slice / accept-with-registry-entry (Phase 410 THM-04 accepted-risks registry). **Fail-closed**: just-shipped Arc cannot transition to `shipped` until human gate clears. |

    **Subsection `### Failure-Mode Ladder (3-Strike)`:**

    "Retry-loop tier follows the v41 PRF-06 3-strike counter discipline:

    1. **Counter scope**: per-`(task_id, check_id)` — NO scope conflation across sub-verifiers. Each sub-verifier maintains its own counter; the composite Step verdict aggregates but does not inflate counters.
    2. **Strike events**: each failed retry emits a `state.verifier.step.<sub>.failed` event with the strike count in the payload (`strike_n: int`, range `1..3`).
    3. **Escalation trigger**: on strike 3, the failure-mode ladder advances to `human-gate`. The harness MUST NOT issue a 4th retry — escalation is mandatory and enforced by the daemon's projector handler.
    4. **Counter reset**: counter resets to 0 when the sub-verifier returns `passed` OR when the parent Step's PLAN is amended (re-planning resets the slate; matches kb §9 stuck-detector cooldown semantics).
    5. **No serial-cycle penalty**: because all 4 sub-verifiers fan out in parallel (VCH-01 short-circuit policy), a single agent retry that fixes 3 sub-verifier failures does NOT count as 3 strikes — it counts as 1 strike per sub-verifier counter, evaluated independently."

    **Subsection `### Auto-Fix-Attempt — Definition and Scope`:**

    "**Definition (state-specific innovation over gsd-2):** `auto-fix-attempt` is a **deterministic harness pass** — pure tooling run by the harness against the failing file(s) BEFORE escalating to `retry-loop`. It is **NOT** an agent retry (that is `retry-loop`). It is **NOT** an LLM-mediated fix (that violates the pure-machine stance pre-empted in VCH-01 overview).

    **In-scope tools (v42)**:
    - `ruff --fix` (autofixable lint rules: unused imports, unused variables, sorted imports, simple format issues)
    - `black` (formatting)
    - `isort` (import ordering)

    **Scope restriction**: auto-fix-attempt applies ONLY to the **anti-pattern sub-verifier** in v42. Other sub-verifiers (goal-backward, security, stub-detector) require semantic code changes that no deterministic tool can safely apply.

    **Audit event**: each auto-fix-attempt run emits `state.verifier.autofix_applied` (success — pattern resolved) or `state.verifier.autofix_failed` (attempt made; pattern remains) with payload `tool: Literal['ruff', 'black', 'isort']` + `pattern_id` + `file_path` + `before_hash` / `after_hash`.

    **Extension path**: future verifiers with mechanically-fixable findings (e.g., a doc-generator anti-pattern catching missing-docstring, or a migration-script generator) may register their own deterministic tool. Registration goes through Phase 411 EVD-01 verifier-output-schema extension hook (not a Phase 407 concern; declared here as an extension point).

    **Why this matters**: gsd-2's `verification-gate` conflates 'retry with failureContext' and 'deterministic fix' as a single tier (kb §3.2). State splits them: deterministic fix is cheapest (no agent context burn, no LLM invocation, byte-deterministic) and runs first; agent retry is the second tier. The split is a state innovation."

    **Subsection `### Human-Gate Routing`:**

    "Human-gate is the terminal tier of every ladder. Per v41 HRN-06, human-gate dispatches **exclusively through the opencode `question` MCP tool** — never an inline prompt, never a free-text request, never a CLI stdin read.

    **`question` payload fields** (consumed verbatim by the human-gate dispatcher):
    - `prompt: str` — the question for the human (server-templated; agent has zero authorship)
    - `options: list[str]` — finite enumerated choices (e.g., for Cross-Tier regression: `['rollback', 'patch-via-new-slice', 'accept-with-registry-entry']`)
    - `default: str | None` — fail-closed when human declines to answer (typically `None`; ambiguous defaults are an anti-pattern)
    - `context: dict[str, Any]` — citations + evidence bundle (per Phase 409 ADV-03 grammar)

    **Fail-closed semantics**: while a human-gate is open, the parent FSM (Step / Stage / Arc) state CANNOT advance. The daemon's middleware blocks state-transition events whose `from_state` requires a verifier verdict in `{passed, warning}` if the verdict is `failed` and the human-gate has not emitted its resolution event.

    **Resolution events** per ladder class:
    - retry-loop human-gate exit → `state.verifier.<sub>.passed` (human accepts evidence) OR `state.verifier.<sub>.failed` (human rejects and re-dispatches) OR Step abandonment
    - Cross-Tier human-gate exit → one of `state.arc.rollback_requested` / `state.slice.patch_requested` / `state.verifier.crosstier.passed` (with accepted-risks registry entry created)

    **No bypass**: agents cannot self-resolve a human-gate. Attempting to write a resolution event from an agent context is rejected by the `tool.execute.before` write-block (extends v41 SRP-04 allowlist; sibling rule to the VERIFY.md write-block declared in Plan 01)."

    <quality_scan>
      <code_to_reuse>
        - Known: opencode `question` MCP tool — already in the tool catalog (v41 HRN-06). Reference path: `@state/opencode-plugin` tool registration.
        - Known: v41 PRF-06 — per-`(task_id, check_id)` retry counter scope. Reference verbatim.
        - Grep pattern (confirm HRN-06 reference in v41 specs): `grep -rn "HRN-06\|opencode \`question\`" .planning/milestones/v41/phases/ | head -10`
      </code_to_reuse>
      <docs_to_consult>
        - 407-CONTEXT.md `<decisions>` VCH-06 subsection — verbatim source for the mapping table.
        - v41 PRF-06 detail in 404-CONTEXT.md — exact counter-scope wording.
        - v41 HRN-06 detail in 406-CONTEXT.md — exact human-gate-via-question wording.
        - kb/workflow/quality-enforcement/03-the-verification-gate-pipeline.md — failureContext re-injection pattern (retry-loop tier mechanism).
        - kb/workflow/workflow-engine/09-stuck-detection-recovery.md — 3-strike ladder precedent.
      </docs_to_consult>
      <tests_to_write>
        N/A — design-only.
      </tests_to_write>
    </quality_scan>
  </action>
  <acceptance_criteria>
    - `grep -c '^## VCH-06 — Failure-Mode Mapping$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Failure-Mode Ladder (3-Strike)$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Auto-Fix-Attempt — Definition and Scope$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '^### Human-Gate Routing$' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*anti-pattern\*\* (Step sub) |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*stub-detector\*\* (Step sub) |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*security\*\* (Step sub) |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*goal-backward\*\* (Step sub) |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*Step composite\*\* |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*Slice rollup\*\* |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*Stage rollup\*\* |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*Arc rollup\*\* |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c '| \*\*Cross-Tier\*\* |' .state/build/quality/VERIFIER-CHAIN.md` returns 1
    - `grep -c 'auto-fix-attempt' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 4
    - `grep -c 'retry-loop' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 4
    - `grep -c 'human-gate' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 5
    - `grep -c 'PRF-06' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'HRN-06' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'opencode \`question\`' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '3-strike\|3 strike\|strike 3' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c 'ruff --fix' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -c '(task_id, check_id)' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - The Auto-Fix-Attempt subsection MUST state "NOT an LLM" or "NOT an LLM-mediated fix": `grep -c 'NOT an LLM' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - The Auto-Fix-Attempt subsection MUST state "NOT an agent retry": `grep -c 'NOT an agent retry' .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 1
    - `grep -ci '\bgsd-\?[0-9]' .state/build/quality/VERIFIER-CHAIN.md` returns 0
    - `wc -l .state/build/quality/VERIFIER-CHAIN.md` returns ≥ 380 lines after this task
  </acceptance_criteria>
  <verify>
    <automated>grep -q '^## VCH-06 — Failure-Mode Mapping$' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q 'PRF-06' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q 'HRN-06' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q 'NOT an LLM' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; grep -q 'ruff --fix' .state/build/quality/VERIFIER-CHAIN.md &amp;&amp; [ "$(wc -l &lt; .state/build/quality/VERIFIER-CHAIN.md)" -ge 380 ] &amp;&amp; ! grep -qi '\bgsd-\?[0-9]' .state/build/quality/VERIFIER-CHAIN.md</automated>
  </verify>
  <done>
    `## VCH-06 — Failure-Mode Mapping` section appended with 9-row mapping table, 3-strike ladder subsection, auto-fix-attempt definition (deterministic-tooling-only, not LLM, not agent retry), human-gate routing subsection (opencode `question` MCP tool per HRN-06). All acceptance grep patterns pass. No GSD references introduced.
  </done>
</task>

</tasks>

<verification>
- VCH-06 section exists with intent paragraph + 9-row mapping table + 3 subsections.
- Mapping table covers all verifiers in the chain: 4 Step sub-verifiers + Step composite + 3 rollup tiers + Cross-Tier.
- 3-strike counter scope is per-`(task_id, check_id)` per v41 PRF-06.
- Auto-fix-attempt enumerates `ruff --fix`, `black`, `isort` and explicitly excludes LLM-mediated fixes and agent retries.
- Human-gate routing cites HRN-06 and names opencode `question` MCP tool.
- No GSD references introduced.
</verification>

<success_criteria>
- VCH-06 section maps all 9 verifiers to failure-mode classes
- 3-strike retry counter scope documented per v41 PRF-06
- Auto-fix-attempt is deterministic-tooling-only (state innovation over gsd-2)
- Human-gate is via opencode `question` MCP tool (v41 HRN-06)
- File length ≥ 380 lines (was ~280 after Plan 01)
</success_criteria>

<output>
After completion, create `.planning/milestones/v42/phases/407-verifier-chain-architecture/407-02-SUMMARY.md` with:
- 1-paragraph outcome (what VCH-06 mapping now specifies)
- Cross-references: VCH-06 requirement satisfied
- Forward-references: Plan 04 (Cross-Tier scope-rule justification deepening)
</output>
