# Phase 407: Verifier Chain Architecture — Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 407 produces one canonical specification document:

1. **`VERIFIER-CHAIN.md`** — the v42 verifier-chain rollup. Enumerates the **five verifier scopes** — Step (VCH-01), Slice rollup (VCH-02), Stage rollup (VCH-03), Arc rollup (VCH-04), Cross-Tier (VCH-05) — with one normalized schema row per verifier: `inputs` (artifacts/events/code read), `algorithm` (concrete decision logic, not pseudocode), `outputs` (event + markdown + TUI update), `failure_mode` (one of: retry-loop, human-gate, auto-fix-attempt), `evidence` (what counts as proof). Decomposes the Step verifier suite into four named sub-verifiers — goal-backward, security, stub-detector, anti-pattern — with forward-references to Phase 408 (stub deep-dive), 409 (goal-backward / adversarial deep-dive), 410 (security / anti-pattern deep-dive). Documents per-verifier failure-mode mapping (VCH-06) and registers the verifier event family as a `## v42 Amendment` block appended to the v40 EVENT-TAXONOMY.md canonical location (VCH-07).

Phase 407 is **design-only — no code lands.** Spec is implemented by v14 (Build Kernel) and v15 (Build Core Commands). Every check specified here is **pure-machine** (PRF-04 spirit carries forward; LLM-as-judge debate deferred to Phase 409 ADV design but pre-empted here: pure-machine across the entire chain).

</domain>

<decisions>
## Implementation Decisions

### Naming discipline (project-wide, carried forward from 405/406)

**All new identifiers MUST be `STATE-*` or `state-*`, never `GSD-*`.** Phase 407 introduces:

- Events: `state.verifier.step.goal_backward.passed`, `state.verifier.step.goal_backward.failed`, `state.verifier.step.security.{passed,failed}`, `state.verifier.step.stub_detector.{passed,failed}`, `state.verifier.step.anti_pattern.{passed,failed}`, `state.verifier.step.{passed,failed}` (composite), `state.verifier.slice.{passed,failed}`, `state.verifier.stage.{passed,failed}`, `state.verifier.arc.{passed,failed}`, `state.verifier.crosstier.{passed,regression_detected}` — ~25 event types total.
- MCP tools: `run_step_verifier`, `run_slice_rollup`, `run_stage_rollup`, `run_arc_rollup`, `run_crosstier_verifier` (registered under `state-build` MCP server; full Pydantic input/output schemas owned by Phase 411 EVD-01).
- Modules: `state_build/verifier/{step,slice,stage,arc,crosstier}/` for orchestration; `state_build/verifier/subverifiers/{goal_backward,security,stub_detector,anti_pattern}/` for Step sub-verifiers; `state_build/verifier/aggregator/` for the pure-machine rollup aggregator.

### Tier vocabulary (carried forward from 400 D-17, D-03, 402)

Canonical four-tier hierarchy: **Arc → Stage → Slice → Step.** v40 D-03 wins: never call Stages "phases" in any spec/event/module/command. Workflow-phase vocabulary (Slice cycle) is design-slice → research-slice → run-slice → verify-slice.

The Cross-Tier verifier is **state-specific**; gsd-2 has no aggregation tier above milestone (kb workflow-engine §9.2). Phase 407 owns the entire Cross-Tier design as new ground.

### Verifier intelligence stance (pre-empts Phase 409 ADV debate)

**Pure-machine across the entire chain.** Every algorithm in VERIFIER-CHAIN.md is deterministic: AST walkers (Python `ast.NodeVisitor`), grep regex over `files_modified`, `pathlib` existence checks, `events.sqlite` queries via `aiosqlite`, `pygit2` for git evidence, ruff for anti-pattern fixable patterns, subprocess invocation of test runners. **No LLM-as-judge anywhere in the verifier chain.** This locks the deferred Phase 409 question in the negative: the harness never asks an LLM "is this code correct?" — only deterministic falsification + positive evidence. Carries forward PRF-04 spirit from v41 Phases 404/405/406.

The orthogonal "can the agent's retry use the failureContext re-injection pattern" question is unchanged: yes (kb §3.2 + §4.1) — that's the agent doing work in response to verifier output, not the verifier consulting an LLM.

### Five verifier scopes (VCH-01..VCH-05)

#### VCH-01 — Step verifier suite (4 parallel sub-verifiers)

**Composition: parallel via opencode `task` subagent fan-out.** The four sub-verifiers — goal-backward, security, stub-detector, anti-pattern — run independently in their own subagent contexts. Matches the gsd-2 Q3/Q4 parallel-subagent dispatch pattern (kb quality-enforcement §9.1) and reuses Phase 405 SUB-01's typed-spawn surface over opencode `task` (`dispatch_subagent` MCP tool). Four independent concerns over disjoint axes — serialization wastes wall-clock with no correctness gain.

**Short-circuit policy: always run all 4; collect full evidence.** No early termination on first BLOCKER. The agent gets all sub-verifier findings in one failureContext re-injection (kb §4.1 step 6 server-side merge pattern), so a single retry can address all four classes of failure rather than fix-retry-fix-retry serial cycles. Wall-clock cost is parallel anyway.

**Composite Step verdict: strict AND on PASS; any BLOCKER → FAIL.** Server-recomputed per kb §11.5 (never LLM-summarized). Step verdict = `passed` iff all 4 sub-verifiers return `passed` or `warning` (no BLOCKER). Any BLOCKER from any sub-verifier → Step verdict = `failed`. Composite evidence list is the **union** of all 4 sub-verifier evidence lists. Citations follow Phase 409 ADV-03 canonical grammar (`file_path:line_number`, `commit:<hash>`, `event:<id>`, `test:<runner-output-id>`).

**Sub-verifier forward-references:**

| Sub-verifier | Owns deep design |
|---|---|
| goal-backward | Phase 409 GBP-01..05 |
| security | Phase 410 THM-01..05 |
| stub-detector | Phase 408 STB-01..04 + LVL-04..06 |
| anti-pattern | Phase 410 APS-01..05 |

Each row in `VERIFIER-CHAIN.md` cites the forward-phase REQ-IDs; deep algorithm spec lives downstream.

#### VCH-02 — Slice rollup verifier

**Pure aggregator.** Reads child Step VERIFY.md verdicts + Slice-level integration check evidence. Algorithm: `slice_verdict = passed iff every child_step.verdict ∈ {passed, warning} AND slice_integration_check.verdict == passed`. Any child `failed` → Slice `failed` with composite evidence list = union(child evidence). Output: `SLICE-VERIFY.md` (per-tier-VERIFY-artifact decision — see "Per-tier VERIFY artifact" below) + `state.verifier.slice.{passed,failed}` event.

**Failure mode: no action; verdict propagates upward.** The rollup is a *boolean aggregation*, not an actor. If any child failed, Slice rollup verdict = `failed`. The *child's* failure mode (retry-loop / human-gate / auto-fix) owns retry/escalation. Slice rollup itself never retries, never escalates, never auto-fixes — it just emits its verdict and waits for child remediation events to re-aggregate (see "Event-driven re-aggregation" below).

#### VCH-03 — Stage rollup verifier

Same pure-aggregator pattern as VCH-02, scoped to child Slices. Reads Slice VERIFY.md verdicts + Stage-level acceptance criteria (CRIT.md). Output: `STAGE-VERIFY.md` + `state.verifier.stage.{passed,failed}` event. **Invocation surface includes the `/state-ship-stage <id>` command** (user request — mirrors `/state-ship-arc` from v40 D-18). Stage rollup is the gate that the ship-stage workflow consults before transitioning Stage state `verified → shipped`.

#### VCH-04 — Arc rollup verifier

Same pure-aggregator pattern, scoped to child Stages. Reads Stage VERIFY.md verdicts + Arc-level acceptance criteria. Output: `ARC-VERIFY.md` + `state.verifier.arc.{passed,failed}` event. Fires as part of the `/state-ship-arc` flow's auditing-state transition (v40 D-18: `auditing` entry guard = all child Stages shipped; Arc rollup verifies before transition to `shipped`).

#### VCH-05 — Cross-Tier verifier (state-specific; novel)

**Scope rule: depends_on closure over already-shipped Arcs.** Walk the transitive closure of v40 Arc-level `depends_on` edges (D-12 edge types: `blocks`/`soft`/`data`) of the just-shipped Arc. Filter to Arcs in state `shipped` (in-progress Arcs have no stable verifier evidence to regress against — state's all-concurrent model means many Arcs may be `in_progress` simultaneously per PROJECT.md).

Rationale: matches the only gsd-2 precedent (`milestones.depends_on` JSON column, kb workflow-engine §9.2); bounded by declared intent; deterministic; cheap (DAG walk + per-Arc evidence re-check). State's v40 D-10 same-parent-only rule at lower tiers means undeclared cross-Arc coupling is already discouraged; depends_on is the strongest declared signal.

**Trigger: auto on Arc ship + manual re-run.** Auto-fires as the final gate of `/state-ship-arc` after VCH-04 Arc rollup passes (matches v40 D-18 Arc audit workflow). Also exposed as a CLI surface `state verify crosstier <arc-id>` (full design owned by Phase 411 EVD-04 `state verify trace` family) for diagnostic / drift-recovery re-runs.

**Regression criteria (composite — both checked):**

1. **Prior Arc's verifier verdict flips PASS→FAIL on re-run.** Re-execute each closure-Arc's stored Step/Slice/Stage verifier evidence against current HEAD. Any verdict that was `passed` at original ship but is now `failed` = regression. Matches kb server-side recomputation discipline (kb §11.5).
2. **Prior Arc's must_haves no longer satisfied.** Walk each closure-Arc's CRIT.md + frontmatter `must_haves.{truths,artifacts,key_links}` (v41 STP-02 schema) and re-verify via the four evidence types (code-exists, tests-pass, LSP-clean, behavioral-check — Phase 409 GBP-03 taxonomy). Any unsatisfied must_have = regression. Falsification-first stance pre-empts Phase 409 ADV-01.

Both conditions are evaluated; either triggering = `state.verifier.crosstier.regression_detected`.

**Failure mode: human-gate immediately.** Regression means a previously-shipped Arc is now broken. Cannot auto-fix (the new Arc's commits caused it; deterministic harness pass would not know which path to take) or retry-loop (no agent action against the *current* Arc fixes it; the right answer is a decision about the *broken* Arc). Routes through opencode `question` tool (v41 HRN-06): rollback / patch-via-new-Slice / accept-with-registry-entry (Phase 410 THM-04 accepted-risks registry analog). Fail-closed: the just-shipped Arc cannot transition to `shipped` until human gate clears.

### VCH-06 — Failure-mode mapping

Per-verifier defaults from the {retry-loop, human-gate, auto-fix-attempt} triad:

| Verifier | Default failure-mode ladder |
|---|---|
| **anti-pattern** (Step sub) | deterministic auto-fix → retry-loop → human-gate. Harness first runs deterministic formatter pass (`ruff --fix`, `black`, `isort`) for fixable patterns (unused imports, formatting, ordering). Remaining violations re-dispatch agent with failureContext (kb §3.2). After 3 retries on same `(pattern, file)` pair, escalate to human gate (matches kb §10.1 + v41 PRF-06 3-strike ladder). |
| **stub-detector** (Step sub) | retry-loop → human-gate. Stubs require code-writing; no deterministic auto-fix. Re-dispatch agent with stub-trace evidence (Phase 408 STB-03 call-chain to user surface). 3-strike → human gate. Known-Stubs registration (STB-04) bypasses by promoting to KNOWN tier before the retry counter triggers. |
| **security** (Step sub) | retry-loop → human-gate. Re-dispatch agent with mitigation-missing evidence cited `file:line`. 3-strike → human gate. |
| **goal-backward** (Step sub) | retry-loop → human-gate. Re-dispatch agent with missing-must-have evidence (kb §4.3 recoverable failure pattern). 3-strike → human gate. |
| **Step composite** | inherits from sub-verifier strikes; composite Step `failed` triggers a single failureContext bundle (union of sub-verifier evidence) for the agent's retry. Retry counter is per-`(task_id, check_id)` per v41 PRF-06 (no scope conflation between sub-verifiers). |
| **Slice rollup** | no action; verdict propagates upward. Pure aggregator. Child Step's failure mode owns retry. |
| **Stage rollup** | no action; verdict propagates upward. Pure aggregator. Child Slice's failure mode owns retry (which itself delegates to Step). |
| **Arc rollup** | no action; verdict propagates upward. Pure aggregator. |
| **Cross-Tier** | human-gate immediately. No retry, no auto-fix — see VCH-05 above. |

**Auto-fix-attempt definition (state-specific):** a *deterministic harness pass* (ruff --fix, black, isort, similar pure-tooling). **NOT** an agent retry — that's `retry-loop`. **NOT** an LLM-mediated fix — that violates the pure-machine stance. This is a finer-grained class than gsd-2's verification-gate (which conflates them as "retry with failureContext"). Auto-fix only applies to anti-pattern sub-verifier for now; opens an extension path for future verifiers with mechanically-fixable findings.

### VCH-07 — Event taxonomy amendment

**Event-name dimensionality: scope + sub-verifier + verdict.** Full namespace shape: `state.verifier.<scope>[.<sub_verifier>].<verdict>`. ~25 event types:

```
# Step sub-verifier events (4 × 2 = 8)
state.verifier.step.goal_backward.passed
state.verifier.step.goal_backward.failed
state.verifier.step.security.passed
state.verifier.step.security.failed
state.verifier.step.stub_detector.passed
state.verifier.step.stub_detector.failed
state.verifier.step.anti_pattern.passed
state.verifier.step.anti_pattern.failed

# Step composite events (2)
state.verifier.step.passed
state.verifier.step.failed

# Slice / Stage / Arc rollup events (3 × 2 = 6)
state.verifier.slice.passed
state.verifier.slice.failed
state.verifier.stage.passed
state.verifier.stage.failed
state.verifier.arc.passed
state.verifier.arc.failed

# Cross-Tier events (2)
state.verifier.crosstier.passed
state.verifier.crosstier.regression_detected

# Auxiliary (verdict-warning, override, auto-fix attempt) — full enumeration in plan
state.verifier.step.<sub>.warning
state.verifier.verdict_changed       # fires on re-aggregation flip
state.verifier.autofix_applied       # anti-pattern auto-fix landed
state.verifier.autofix_failed        # anti-pattern auto-fix attempted but pattern remains
```

Every event has a Pydantic payload model (`extra="forbid"`) following the v41 STATE-* discipline. Payloads include: `verifier_name`, `scope_id` (step_id / slice_id / stage_id / arc_id), `verdict: Literal["passed", "failed", "warning"]`, `evidence: list[Citation]` (Phase 409 ADV-03 grammar), `triggered_at: datetime`, `session_id`, `snapshot_event_id: str | None`. Full schemas owned by Phase 411 EVD-01; Phase 407 enumerates only the event-name registry and required-field shape.

**Amendment block format:** appended as `## v42 Amendment` to v40 EVENT-TAXONOMY.md (canonical location TBD — likely `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` or `.state/build/runtime/EVENT-TAXONOMY.md`; plan-phase picks). Block reads as a published correction: never edit original v40 entries. Matches Phase 405's amendment-as-append pattern.

### Verdict vocabulary (project-wide)

**3-state across all verifier scopes: `Literal["passed", "failed", "warning"]`.**

- `passed` — all checks green; no BLOCKER findings; verifier verdict carries forward upward without escalation.
- `failed` — at least one BLOCKER finding; verdict halts upward propagation (parent rollup also `failed`); failure_mode-defined ladder fires.
- `warning` — WARNING-only findings (no BLOCKER); verdict carries forward upward but emits an advisory event for human/audit attention; does NOT block ship.

Mapping to existing v40/v41/Phase-408 vocabulary:

- Phase 408 STB-02 severity (BLOCKER / WARNING / KNOWN): BLOCKER → `failed`; WARNING → `warning`; KNOWN → does not contribute to verdict at all (registered out per STB-04).
- Phase 411 PCK-10 plan-checker (passed / blocked / warnings): same shape; `blocked` is just `failed` at the plan-checker scope. Phase 411 spec aligns to the same `Literal` set.
- gsd-2's `pass | flag | omitted` (kb §8.7) is rejected for state: `omitted` collides semantically with v40 D-14 `deferred` and v41 SRP-06 `deferred-items.md`. State's `warning` covers the "noteworthy but not blocking" case; explicit deferment is its own artifact.

### Per-tier VERIFY artifact

**Every rollup tier writes its own VERIFY artifact:**

- Step → `stepNVERIFY.md` (one per Step file, lives alongside `stepNPLAN.md` + `stepNSUMMARY.md` in the Slice folder). Contains 4 sub-verifier sections (`## Goal-Backward` / `## Security` / `## Stub-Detector` / `## Anti-Pattern`) each with sub-verdict + evidence list (citations per Phase 409 ADV-03), plus a composite verdict in frontmatter + summary block.
- Slice → `N-VERIFICATION.md` (already canonical per v41 Phase 402 SLICE-CYCLE.md `verify-slice` stage). Phase 407 amends: must contain `## Step Verdict Table` (one row per child Step with verdict + link to stepNVERIFY.md) + `## Slice Integration Check` section.
- Stage → `STAGE-VERIFY.md` (new artifact). Contains `## Slice Verdict Table` + `## Stage Acceptance Check` (against CRIT.md must_haves).
- Arc → `ARC-VERIFY.md` (new artifact). Contains `## Stage Verdict Table` + `## Arc Acceptance Check` + `## Cross-Tier Verdict` block (results of VCH-05 against depends_on closure).

**Authorship rule (matches v40 D-401-09):** all VERIFY artifacts are server-written by the verifier orchestrator. **Agents have zero authorship privilege on any VERIFY.md.** A `tool.execute.before` write-block rejects any agent Write/Edit targeting `*VERIFY.md` paths (extends Phase 404 SRP-04 allowlist enforcement).

Forward-reference: Phase 411 EVD-03 walker walks this chain `stepNVERIFY → stepNPLAN → STEP-file → SLICE → STAGE → ARC` upward; the per-tier-VERIFY-artifact rule is what makes the walk possible.

### Event-driven re-aggregation

**Daemon listens on the v6 SSE bus for any `state.verifier.<child>.{passed,failed}` event.** On a verdict-flip event for a child of an open rollup, daemon re-runs the parent rollup verifier (pure-machine, no LLM). Composite verdict updates idempotently. Matches v6 daemon + v40 projector pattern (verifier verdicts are projected state; re-aggregation is a projector handler).

Crucially: **this is how the chain heals after gap-closure.** When a failed Step is retried and now passes (its `state.verifier.step.failed` is followed by `state.verifier.step.passed`), the daemon re-aggregates the parent Slice rollup, which may now pass, which re-aggregates the Stage rollup, and so on upward. The `state.verifier.verdict_changed` event fires at each tier whose verdict flipped, enabling the TUI to update progressively.

Re-aggregation cost is bounded: only the parent of the changed child is re-aggregated, and only if it's in an `open` state (not already shipped). Already-shipped Arcs/Stages/Slices/Steps are not re-aggregated by child changes — they're immutable verdicts in the event log (Phase 411 EVD-05 retention rule territory).

### Claude's Discretion

- Exact Pydantic field ordering inside each event payload model (user specified `extra="forbid"` + payload fields; planner picks order)
- Per-sub-verifier MCP tool naming (e.g., `run_goal_backward_verifier` vs `run_step_subverifier(name="goal_backward")` — planner picks)
- Exact 3-strike retry counter scope for the auto-fix-attempt tier (e.g., per-`(verifier, pattern, file)` vs per-`(verifier, pattern)` — planner picks based on Phase 405 SUB-09 inheritance pattern)
- The specific canonical location for the `## v42 Amendment` block in v40 EVENT-TAXONOMY.md (planner enumerates and picks)
- Exact CLI signature for `state verify crosstier <arc-id>` (full design owned by Phase 411 EVD-04; Phase 407 just declares the command exists)
- VERIFY artifact frontmatter Pydantic schemas (planner authors from this section's content)

</decisions>

<specifics>
## Specific Ideas

- **Cross-Tier verifier is genuinely novel for state** — gsd-2 stops at milestone (kb workflow-engine §9.2). State introduces Arc as a new top tier above Stage (gsd-2 milestone-equivalent) to group multiple Stages by feature/generation. No precedent to port; Phase 407 owns the entire Cross-Tier design.

- **All Arcs/Stages run concurrently** — there is no global "active" pointer in state. The verifier chain must handle the case where many Arcs are `in_progress` simultaneously. Cross-Tier scope only checks already-shipped Arcs to avoid evidence-instability against in-flight work.

- **Slash-command routing layer** — any-tier slash command (e.g., `/state-design-slice ###`, `/state-new-stage ###`, `/state-ship-stage ###`, `/state-ship-arc ###`) must resolve from a bare tier ID via the v40 D-09 index.json mechanism, OR prompt the user for disambiguation if the ID is ambiguous (e.g., a slug that matches multiple tiers). This is **NOT** a Phase 407 concern — captured as a deferred idea below (v43 command-layer territory).

- **Auto-fix-attempt is a state innovation over gsd-2.** kb describes "retry with failureContext re-injection" (agent doing fix work) but no deterministic harness-side fix pass. State adds the `auto-fix-attempt` tier between the verifier failure and the agent retry, scoped to mechanically-fixable patterns (ruff --fix, black, isort). This is the lightest tier of the failure-mode triad.

- **Agent has zero authorship privilege on VERIFY.md files.** Reinforces server-side recomputation discipline (kb §11.5). Enforced via `tool.execute.before` write-block extending v41 SRP-04 allowlist.

- **Phase 407 leaves the sub-verifier deep designs intact** — the 4 sub-verifiers are named here with normalized schema row stubs; full algorithm spec lives in Phase 408 (stub, 4-level model) and Phases 409/410 (goal-backward, adversarial, anti-pattern, threat model). The forward-reference invariant means Phase 408+ specs must satisfy the schema rows declared here.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/state_core/schema.py`** — already defines event types for verification (`state.step.verify_passed`, `state.step.verify_failed`, etc.). Phase 407 amends the schema with the ~25 new verifier event types above; existing types are aliased or migrated per planner's call.
- **`src/state_core/projector.py`** — CQRS projection engine with 19 handlers / 3 cache tables. Phase 407's event-driven re-aggregation is a new projector handler family (one per rollup scope). Slots into existing dispatcher cleanly.
- **`src/state_core/events.py`** — event store API (verifier writes events through this surface). No structural changes needed; Phase 407 just adds new event-name registrations.
- **`src/state_core/import_lint.py`** — existing mode-isolation lint. Phase 410's APS-02 architecture anti-pattern catalog will extend this lint with additional rules (state_build ↛ state_teach, direct FS access outside `.state/`, event-store bypass). Phase 407 just declares the anti-pattern Step sub-verifier exists and forward-references Phase 410.
- **`src/state_core/observability/redactor.py`** — existing token redaction (related to Phase 410 APS-01 secret-like-string detection). Phase 407 references it as the secret-detection source for the security Step sub-verifier.

### Established Patterns

- **Pure-machine verification (PRF-04)** — carries forward from v41 Phases 404/405/406. Phase 407 explicitly locks "no LLM-as-judge anywhere in the verifier chain" — pre-empts Phase 409 ADV debate in the negative.
- **Pydantic `extra="forbid"` for every event/payload** — carries forward from Phase 400+.
- **Single monolithic spec doc per phase** — `VERIFIER-CHAIN.md` is one file with all 5 scope rows, matching Phase 406 pattern. Inline operative contracts (Pydantic schemas, event-name registry) verbatim; pointer-only for explanatory prose.
- **Mermaid for diagrams** — Phase 407 produces at least one diagram (verifier chain topology: Step → Slice → Stage → Arc → Cross-Tier with edges labeled by re-aggregation triggers). Plus possibly a Step-sub-verifier parallel-fanout diagram showing the 4 sub-verifiers running concurrently and merging at the composite verdict.
- **Forward-reference invariant** — Phase 408/409/410/411 specs satisfy the schema rows declared in Phase 407 `VERIFIER-CHAIN.md`. No backward edits to 407 once shipped; downstream phases consume forward.
- **Server-side recomputation, never LLM-summarized** — every composite verdict (Step composite, Slice rollup, Stage rollup, Arc rollup, Cross-Tier) is computed by the daemon's projector, not by an LLM summarization. Matches kb quality-enforcement §11.5 convergent defense.
- **3-tier failure-mode ladder** — auto-fix → retry-loop → human-gate. The retry-loop tier reuses v41 PRF-06 3-strike counter discipline (per-`(task_id, check_id)` scope, no conflation across sub-verifiers).

### Integration Points

- **v6 daemon SSE bus** — verifier events flow through here; event-driven re-aggregation listens here.
- **v40 projector** — adds new handler family for rollup re-aggregation.
- **v40 EVENT-TAXONOMY.md** — amended with `## v42 Amendment` block carrying the ~25 new event-name registrations.
- **opencode `task` MCP tool (via Phase 405 `dispatch_subagent`)** — the 4 Step sub-verifiers fan out via this surface.
- **opencode `question` MCP tool** — the human-gate failure-mode tier dispatches through this (carries forward v41 HRN-06).
- **v41 SRP-04 `files_modified` allowlist + `tool.execute.before` write-block** — extended to reject agent Write/Edit on `*VERIFY.md` paths.
- **v40 D-18 Arc audit workflow** — Cross-Tier verifier (VCH-05) fires as the final gate after VCH-04 Arc rollup, before Arc state transitions `auditing → shipped`. New `/state-ship-stage` command (user request) mirrors `/state-ship-arc` and uses VCH-03 Stage rollup as its gate.

</code_context>

<deferred>
## Deferred Ideas

- **Pivot to state-native Python TUI + harness (drop opencode coupling).** Briefly explored mid-session: legitimate strategic option but massive blast radius — invalidates v41 HRN-01..08, the `@state/opencode-plugin` component, every "via plugin hook X" cross-reference, and the entire SolidJS TUI layer. TUI alone is months; pi-class parity is 6–12 months. User confirmed: side project rather than this-repo pivot. Captured here as a reminder, not a roadmap item.

- **Any-tier slash command routing layer.** `/state-design-slice ###`, `/state-new-stage ###`, `/state-ship-stage ###` etc. must resolve from a bare tier ID via v40 D-09 index.json, OR prompt the user for disambiguation if ambiguous. **NOT** Phase 407 — belongs in v43 (Build Command Layer / GSD command porting milestone per HANDOFF "Out of scope").

- **`/state-ship-stage <id>` command.** User requested in the cross-tier discussion to mirror `/state-ship-arc`. Phase 407 declares its existence (VCH-03 Stage rollup is its gate) but the command itself lives in v43.

- **LLM-assisted verification (verifier-as-agent).** ROADMAP marks this "deferred to ADV design; if rejected as non-deterministic, capture in Out of Scope at milestone close." Phase 407 pre-empts: pure-machine across the entire chain, no LLM-as-judge anywhere. Phase 409 ADV design should formalize this rejection in `ADVERSARIAL-PROTOCOL.md`.

- **Weighted-score verdict aggregation (eval-review style).** Phase 407 picks 3-state `passed | failed | warning` over a weighted score band. Score-band verdicts (kb §11.5 eval-review `NOT_IMPLEMENTED / SIGNIFICANT_GAPS / NEEDS_WORK / PRODUCTION_READY`) are richer signal but agent-gameable. Defer to v44+ if a use case emerges.

- **Cross-Tier verifier as a daemon-scheduled background job.** Currently fires only on Arc ship + manual. A future enhancement: scheduled re-runs (e.g., nightly) to catch regressions caused by drift in shared dependencies (`pip` upgrade, upstream library deprecation). Belongs in v44+ test-infrastructure milestone.

</deferred>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 407 scope & requirements
- `.planning/milestones/v42/ROADMAP.md` — Phase 407 goal, success criteria SC1–SC5, phase dependencies (nothing — first v42 phase).
- `.planning/milestones/v42/REQUIREMENTS.md` — VCH-01..VCH-07 (7 requirements for Phase 407).
- `.planning/milestones/v42/HANDOFF.md` — Key questions (now resolved above), research inputs (kb docs loaded into session), scope boundaries.

### v40 prerequisites
- `.planning/milestones/v40/phases/400/400-CONTEXT.md` — D-17 tier state machines (Arc/Stage/Slice/Step); D-12 `depends_on` edge types (`blocks`/`soft`/`data`); D-18 Arc audit workflow.
- `.planning/milestones/v40/phases/401/401-CONTEXT.md` — D-401-09 agent-authored vs projector-authored boundary (VERIFY.md is server-written); index.json structure (D-401-14); REF-01..06 cross-reference invariants (consumed by Phase 411 EVD-03 walker).

### v41 prerequisites
- `.planning/milestones/v41/phases/402/402-CONTEXT.md` — Slice-cycle vocabulary (design-slice / research-slice / run-slice / verify-slice); `N-VERIFICATION.md` artifact at Slice tier.
- `.planning/milestones/v41/phases/404/404-CONTEXT.md` — PRF-04 pure-machine discipline; PRF-06 3-strike per-`(task_id, check_id)` retry counter; PRF-07 write-block enforcement (extends to VERIFY.md authorship).
- `.planning/milestones/v41/phases/405/405-CONTEXT.md` — SUB-01 typed-spawn over opencode `task`; SUB-09 autonomy inheritance from parent Slice; STATE-* naming discipline.
- `.planning/milestones/v41/phases/406/406-CONTEXT.md` — HRN-01..08 harness rollup; HRN-06 human-gate-only-via-opencode-`question`-tool rule; v41 amendment-as-append pattern.

### Knowledge base (gsd-2 design heritage; loaded during Phase 407 discuss session)
- `kb/workflow/quality-enforcement/01-overview.md` — five-pipeline taxonomy (verification-gate, post-unit, pre/post-exec checks, gate registry, eval-review-and-friends).
- `kb/workflow/quality-enforcement/03-the-verification-gate-pipeline.md` — command-discovery 3-tier fallback; failureContext 2KB-per-check / 10KB-total cap.
- `kb/workflow/quality-enforcement/04-post-unit-verification-orchestration.md` — discriminated outcome `continue | retry | pause`; server-side recompute of `result.passed`.
- `kb/workflow/quality-enforcement/06-quality-gate-registry.md` — exhaustive registry via `satisfies Record<GateId, GateDefinition>`; runtime `assertGateCoverage`; per-`(scope_id, gate_id)` DB row.
- `kb/workflow/quality-enforcement/07-per-turn-gate-flow.md` — Q3/Q4 parallel subagent dispatch (model for Step sub-verifier parallelism).
- `kb/workflow/quality-enforcement/08-milestone-validation.md` — three-parallel-reviewers dispatch (model for parallel sub-verifier independence).
- `kb/workflow/quality-enforcement/09-eval-review-pipeline.md` — server-side recomputation of score / counts / verdict; defense against LLM arithmetic.
- `kb/workflow/quality-enforcement/14-custom-verification-policies.md` — 4-policy dispatcher (`content-heuristic`, `shell-command`, `prompt-verify`, `human-review`); fail-closed default = `pause`.
- `kb/workflow/quality-enforcement/17-known-concerns-python-reimplementation-notes.md` — server-side recomputation as THE defining pattern for the Python port.
- `kb/workflow/workflow-engine/07-verification-gate-flow.md` — Surface 1 (per-task) vs Surface 2 (gate questions) separation.
- `kb/workflow/workflow-engine/08-milestone-boundaries.md` — §9.2 "no aggregation tier above milestone" rule (state's Arc tier is novel).
- `kb/workflow/workflow-engine/09-stuck-detection-recovery.md` — sliding-window stuck detector; 3-strike escalation ladder (model for retry-loop tier).

### Architecture & integration
- `.planning/research/ARCHITECTURE.md` — daemon SSE bus, projector handler family, event-store API surfaces (all consumed by event-driven re-aggregation).
- `src/state_core/schema.py` — existing event-type registry (amended with ~25 new verifier event types).
- `src/state_core/projector.py` — existing CQRS projection (extended with rollup re-aggregation handler family).
- `src/state_core/import_lint.py` — existing mode-isolation lint (extended in Phase 410 APS-02).
- `src/state_core/observability/redactor.py` — secret-redaction (reused by Phase 410 security sub-verifier for APS-01 secret-like-string detection).

</canonical_refs>

---

*Phase: 407-verifier-chain-architecture*
*Context gathered: 2026-05-13*
