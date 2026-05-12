# Requirements: state — v42 Build Quality Pipeline Architecture

**Defined:** 2026-05-12
**Core Value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.
**Milestone goal:** Design the complete quality pipeline for Build mode — verifier chain, goal-backward planning protocol, adversarial verification stance, stub detection, anti-pattern scanning, threat modeling, plan checker, and evidence chain. **No source code; spec markdown only.**
**Source:** `.planning/milestones/v42/HANDOFF.md` (9 design areas).
**Phase numbering:** continues from **407** (v41 ended at 406).

---

## v1 Requirements

### Verifier Chain (VCH)

The hierarchical verifier chain that aggregates upward through all four tiers (Step → Slice → Phase → Arc) plus a Cross-Tier verifier for regressions between completed Arcs.

- [ ] **VCH-01**: Spec defines the Step verifier suite — goal-backward verifier, security verifier, stub detector, anti-pattern scanner — with each sub-verifier's input/algorithm/output/failure-mode/evidence specified.
- [ ] **VCH-02**: Spec defines the Slice rollup verifier — aggregates Step results, runs Slice-level integration check, fails the Slice if ANY Step failed; input/algorithm/output/failure-mode/evidence specified.
- [ ] **VCH-03**: Spec defines the Phase rollup verifier — aggregates Slice results, applies Phase-level acceptance criteria, with full input/algorithm/output/failure-mode/evidence.
- [ ] **VCH-04**: Spec defines the Arc rollup verifier — aggregates Phase results, applies Arc acceptance criteria, fails Arc if ANY Phase failed; full input/algorithm/output/failure-mode/evidence.
- [ ] **VCH-05**: Spec defines the Cross-Tier verifier — regression detection between completed Arcs + cross-Arc integration tests; scope rule explicit (all Arcs / dependency-edged Arcs / file-overlapping Arcs).
- [ ] **VCH-06**: Each verifier's failure mode is mapped to one of: retry loop, human gate, auto-fix attempt, with explicit transition criteria.
- [ ] **VCH-07**: Per-verifier event types defined and appended to v40 EVENT-TAXONOMY.md (e.g., `state.verifier.step.passed`, `state.verifier.slice.failed`, `state.verifier.crosstier.regression_detected`).

### 4-Level Verification Model (LVL)

The verification-depth ladder. Each level deeper than the previous; Build mode runs all 4 unless explicitly overridden.

- [ ] **LVL-01**: Level 1 (Existence) spec — file/artifact on disk, commit in git log, event in event store. Checks, tools (`pathlib`, `git log --grep`, `events.sqlite`), pass/fail evidence, edge cases.
- [ ] **LVL-02**: Level 2 (Substantive) spec — min_lines, pattern match, required frontmatter fields, meaningful commit diff (not whitespace-only). Checks, tools, pass/fail evidence, edge cases.
- [ ] **LVL-03**: Level 3 (Wired) spec — file imported AND used; commit code reached by another caller; artifact cross-referenced by upstream artifact. Checks, tools (AST + grep + ruff), pass/fail evidence, edge cases, **scope rule** (Slice worktree only vs. full project).
- [ ] **LVL-04**: Level 4 (Data-Flowing) spec — real DB queries, real fetch/store calls, props not hardcoded empty at call site, UI renders live data, API returns dynamic response. Checks, tools, pass/fail evidence, edge cases, **Python-3.12 feasibility analysis** documented.
- [ ] **LVL-05**: Per-level override mechanism — frontmatter override with `reason`, `accepted_by`, `accepted_at` (80% token-overlap fuzzy match for goal alignment); audit trail in VERIFY.md.
- [ ] **LVL-06**: Legitimate-stub disambiguation rule — verifier reads `Known Stubs` section of SUMMARY.md to distinguish Step-appropriate stub from forgotten implementation; missing-Known-Stubs requirement.
- [ ] **LVL-07**: Per-Step performance budget — verifier perf cap (≤10s per behavioural check; full 4-level cap for a Step) documented with measurement protocol.

### Goal-Backward Planning Protocol (GBP)

Pre-execution plan-checker + post-execution goal-backward verifier + shared must-have derivation.

- [ ] **GBP-01**: Must-have derivation algorithm spec — derives full must-have list from STEP.md goal + ARC/PHASE/SLICE success criteria + REQ-IDs + DISCUSS.md decisions; output written to VERIFY.md frontmatter for audit.
- [ ] **GBP-02**: Pre-execution plan-checker spec — for each must-have, trace concrete task path through PLAN.md; verdict `passed | blocked | warnings` with definitions.
- [ ] **GBP-03**: Post-execution goal-backward verifier spec — for each must-have, find codebase evidence; evidence types (code exists, tests pass, LSP clean, behavioral check passes) with what counts/doesn't count.
- [ ] **GBP-04**: SUMMARY.md trust rule — verifier reads SUMMARY.md only to enumerate claims; codebase evidence is sole arbiter.
- [ ] **GBP-05**: Must-have override authority spec — who can mark `deferred` / `not-applicable`, with what evidence (agent self-override prohibited; explicit accepted_by required).

### Adversarial Verification Stance (ADV)

The default-distrust posture every verifier adopts.

- [ ] **ADV-01**: Adversarial protocol spec — default assumption "implementation is wrong"; falsification-first approach; acceptance requires falsification failure AND positive evidence.
- [ ] **ADV-02**: Evidence taxonomy — what is/isn't evidence (code diff yes, commit message no; substantive tests yes, mocks-of-mocks no; LSP clean partial; behavioral check yes only if verifier runs it itself).
- [ ] **ADV-03**: Claim-citation contract — every accepted/rejected claim cited with file path + line number, commit hash, event ID, or test run output.
- [ ] **ADV-04**: Adversarial protocol reusable across all verifiers (Step / Slice / Phase / Arc / Cross-Tier) — single canonical doc referenced by each verifier spec.

### Stub Detection Framework (STB)

Detect incomplete implementations and trace their reach to user surfaces.

- [ ] **STB-01**: Stub pattern catalog — `pass`, `...`, `NotImplementedError`, `return None`, empty containers, TODO/FIXME without tracking, placeholder strings, hardcoded example values, empty data files; per-pattern detection mechanism.
- [ ] **STB-02**: Stub severity classification — BLOCKER / WARNING / KNOWN with explicit promotion/demotion rules.
- [ ] **STB-03**: Stub trace-through algorithm — if a function returns hardcoded-empty, trace all callers; flag BLOCKER if empty reaches rendering/API surface, WARNING if handled gracefully; AST walker + import graph required.
- [ ] **STB-04**: KNOWN-stub registration — SUMMARY.md `## Known Stubs` section schema (id, location, severity, resolution-plan-link); verifier consults registration before promoting to BLOCKER.

### Anti-Pattern Scanning System (APS)

Runs during verify; optionally during code review.

- [ ] **APS-01**: Code anti-pattern catalog — bare `except`, `print()` in production paths, secret-like strings, SQL string concatenation, `os.system`/`shell=True` with user input, hardcoded file paths, undeclared imports, functions >100 lines, deep nesting (>4 levels), missing public-API docstrings; detection mechanism per pattern; severity (BLOCKER/WARNING); remediation guidance.
- [ ] **APS-02**: Architecture anti-pattern catalog — circular imports, `state_build` importing `state_teach` (mode isolation violation), direct FS access outside `.state/` subtree, bypassing event store for state changes; detection (import-graph lint), severity, remediation.
- [ ] **APS-03**: Test anti-pattern catalog — no-assertion tests, mock-only tests, tautological asserts (`assert True`), tests not exercising stated verify criteria; detection, severity, remediation.
- [ ] **APS-04**: Python-3.12 specific extensions over the GSD baseline — explicit listing of which GSD anti-patterns map to Python equivalents and which are new (e.g., `print()` vs `console.log`, `subprocess(shell=True)` vs `exec`).
- [ ] **APS-05**: Extension hook — how a phase/plan declares additional project-specific anti-patterns without forking the canonical catalog.

### Threat Modeling Framework (THM)

STRIDE threat register required in every PLAN.md, with automated post-execution verification.

- [ ] **THM-01**: STRIDE category coverage requirement — every PLAN.md must declare disposition (`mitigate` / `accept` / `transfer`) for all 6 STRIDE categories; missing categories block plan-checker.
- [ ] **THM-02**: Disposition schema — per disposition kind: required fields, evidence pointers, acceptance authority.
- [ ] **THM-03**: Security verifier spec — for every `mitigate` threat: grep/AST-check mitigation pattern in cited files; for every `accept` threat: verify entry in accepted-risks registry; for every `transfer` threat: verify transfer doc exists. Verdicts: CLOSED / OPEN:BLOCKER / WARNING.
- [ ] **THM-04**: Accepted-risks registry schema — global registry file location, per-entry required fields, audit format.
- [ ] **THM-05**: STRIDE register example — full worked example of a PLAN.md threat model showing all 6 categories with realistic Build-mode threats and dispositions.

### Plan Checker (PCK)

The pre-execution validation checks. Gate that determines whether PLAN.md can proceed to execute.

- [ ] **PCK-01**: Check 1 — PLAN.md declares requirement ID matching STEP.md; detection and verdict criteria.
- [ ] **PCK-02**: Check 2 — every PLAN.md task has all four required fields (`files`, `action`, `verify`, `done`); detection and verdict.
- [ ] **PCK-03**: Check 3 — task `files` use exact paths (no wildcards, no directories); detection and verdict.
- [ ] **PCK-04**: Check 4 — no two concurrent-wave tasks touch the same file (forces wave bump); detection and verdict.
- [ ] **PCK-05**: Check 5 — every must-have traceable to at least one task; uses GBP-01 derivation.
- [ ] **PCK-06**: Check 6 — every RESEARCH.md recommendation either followed or explicitly overridden in PLAN.md; detection.
- [ ] **PCK-07**: Check 7 — every CONTEXT.md locked decision implemented or explicitly deferred; detection.
- [ ] **PCK-08**: Check 8 — STRIDE coverage complete per THM-01.
- [ ] **PCK-09**: Check 9 — task context budgets within thresholds (token budget per task ≤ harness limit from v41 CTX-XX).
- [ ] **PCK-10**: Verdict semantics spec — `passed` / `blocked` / `warnings` with what triggers each; replan loop for `blocked`; human gate for `warnings`.

### Evidence & Artifact Chain (EVD)

How verifier output is stored, linked, and walkable.

- [ ] **EVD-01**: Verifier output schema — verifier name, timestamp, event ID, pass/fail, evidence list, citations; written to both VERIFY.md and event store.
- [ ] **EVD-02**: Evidence citation format — file path + line number, commit hash, event ID, test run output identifier; canonical citation grammar.
- [ ] **EVD-03**: Auditable chain spec — VERIFY.md → PLAN.md → STEP.md → PHASE.md → ARC.md upward walker; cross-reference invariants reuse v40 REF-XX rules.
- [ ] **EVD-04**: `state verify trace <step-id>` CLI design — output shape, traversal order, failure modes when chain breaks.
- [ ] **EVD-05**: Evidence retention rule — when verifier outputs are pruned vs. retained; coupling to event-store retention.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Implementation of any verifier | v42 is design-only; implementation tracked in downstream milestones (v14 Build Kernel + v15 Build Core Commands) |
| GSD command porting (plan-phase, verify, etc. as CLI commands) | v43 milestone (Build Command Layer) |
| Workflow orchestration (how verifiers are invoked from a Step lifecycle) | v43 milestone |
| Teach-mode verification (learning verifier, mental-model checks) | v48 milestone |
| LLM-assisted verification (verifier-as-agent) | Decision deferred to v42 adversarial-stance design; if rejected as non-deterministic, capture in Out of Scope at milestone close |
| UAT script generation / behavioural test automation | v44+ (test infrastructure milestone) |
| Performance benchmarking suite for verifiers | v44+ |

---

## Traceability

Every v1 REQ maps to exactly one phase. Filled by gsd-roadmapper 2026-05-12.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VCH-01 | 407 | Pending |
| VCH-02 | 407 | Pending |
| VCH-03 | 407 | Pending |
| VCH-04 | 407 | Pending |
| VCH-05 | 407 | Pending |
| VCH-06 | 407 | Pending |
| VCH-07 | 407 | Pending |
| LVL-01 | 408 | Pending |
| LVL-02 | 408 | Pending |
| LVL-03 | 408 | Pending |
| LVL-04 | 408 | Pending |
| LVL-05 | 408 | Pending |
| LVL-06 | 408 | Pending |
| LVL-07 | 408 | Pending |
| GBP-01 | 409 | Pending |
| GBP-02 | 409 | Pending |
| GBP-03 | 409 | Pending |
| GBP-04 | 409 | Pending |
| GBP-05 | 409 | Pending |
| ADV-01 | 409 | Pending |
| ADV-02 | 409 | Pending |
| ADV-03 | 409 | Pending |
| ADV-04 | 409 | Pending |
| STB-01 | 408 | Pending |
| STB-02 | 408 | Pending |
| STB-03 | 408 | Pending |
| STB-04 | 408 | Pending |
| APS-01 | 410 | Pending |
| APS-02 | 410 | Pending |
| APS-03 | 410 | Pending |
| APS-04 | 410 | Pending |
| APS-05 | 410 | Pending |
| THM-01 | 410 | Pending |
| THM-02 | 410 | Pending |
| THM-03 | 410 | Pending |
| THM-04 | 410 | Pending |
| THM-05 | 410 | Pending |
| PCK-01 | 411 | Pending |
| PCK-02 | 411 | Pending |
| PCK-03 | 411 | Pending |
| PCK-04 | 411 | Pending |
| PCK-05 | 411 | Pending |
| PCK-06 | 411 | Pending |
| PCK-07 | 411 | Pending |
| PCK-08 | 411 | Pending |
| PCK-09 | 411 | Pending |
| PCK-10 | 411 | Pending |
| EVD-01 | 411 | Pending |
| EVD-02 | 411 | Pending |
| EVD-03 | 411 | Pending |
| EVD-04 | 411 | Pending |
| EVD-05 | 411 | Pending |

**Coverage:**
- v1 requirements: 51 total (VCH:7 + LVL:7 + GBP:5 + ADV:4 + STB:4 + APS:5 + THM:5 + PCK:10 + EVD:5)
- Mapped to phases: 51 / 51 (100%) ✓
- Unmapped: 0

---

*Requirements defined: 2026-05-12*
*Last updated: 2026-05-12 — traceability mapped to phases 407–411 (gsd-roadmapper).*
