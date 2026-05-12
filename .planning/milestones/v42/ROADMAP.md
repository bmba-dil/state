# ROADMAP: v42 Build Quality Pipeline Architecture

**Milestone:** v42
**Phase range:** 407–411
**Created:** 2026-05-12
**Type:** Design-phase milestone (zero code — architecture/specification documents only)
**Granularity:** fine (from config.json)

**Core value:** The Build-mode quality pipeline — the **truth-and-completeness layer** that every Step, Slice, Phase, and Arc must clear before promotion — is fully specified across verifier-chain topology, depth-of-verification model, goal-backward planning protocol, adversarial verification stance, stub detection, anti-pattern scanning, threat modeling, plan checker, and evidence chain. The output is the design contract that v14 (Build Kernel: Step FSM + Verifiers) and v15 (Build Core Commands) implement.

**Depends on:**
- **v40 (Build Hierarchy & Artifact System)** — shipped 2026-05-07. The verifier chain spans all four tiers (Arc/Phase/Slice/Step) defined in v40 and writes evidence into the v40 artifact catalog (`PHASE.md`, `STEP.md`, `VERIFY.md`, `SUMMARY.md`).
- **v41 (Agent Harness & Context Control)** — shipped 2026-05-12. The plan checker (PCK) is a pre-execution gate that interacts with the v41 harness's deviation rules (DEV) and proof gates (PRF); PCK-09 explicitly cites v41 CTX-XX context budgets.
- **v1 (Event Store)**, **v6 (Daemon)** — shipped. Verifier event types append-only to v40 EVENT-TAXONOMY.md and flow through the daemon SSE bus.
- **v11 (Mode Enforcement)** — shipped. APS-02 architecture anti-pattern catalog cites the `state_build` ↛ `state_teach` mode-isolation rule.

**Downstream consumers:**
- **v14 Build Kernel: Step FSM + Verifiers** (Phases 124–134) — implements every spec produced here.
- **v15 Build Core Commands** — `state verify`, `state verify trace`, `state plan-check` CLI commands all bind to v42 specs.
- **v45 Consolidated Design & v14–v27 Rewrite Specs** — folds v42 deltas into the v14 REQ-IDs.

**Out of scope (this milestone):**
- Any implementation code. Pure spec markdown only.
- GSD command porting (owned by v43).
- Workflow orchestration / how verifiers are invoked from a Step lifecycle (owned by v43).
- Teach-mode verification (owned by v48).
- LLM-assisted verification (verifier-as-agent) — decision deferred to ADV design; if rejected as non-deterministic, captured in Out of Scope at milestone close.
- Performance benchmarking suite for verifiers (owned by v44+).

---

## Phases

- [ ] **Phase 407: Verifier Chain Architecture** — Step/Slice/Phase/Arc/Cross-Tier verifier topology + per-verifier I/O/algorithm/failure-mode + verifier event family appended to v40 EVENT-TAXONOMY.md
- [ ] **Phase 408: 4-Level Verification Model & Stub Detection** — Existence → Substantive → Wired → Data-Flowing ladder with per-level tools/evidence/edge-cases + stub pattern catalog + severity + trace-through algorithm + Known-Stubs schema
- [ ] **Phase 409: Goal-Backward Protocol & Adversarial Stance** — Must-have derivation + pre-exec plan-checker + post-exec goal-backward verifier + SUMMARY-not-evidence rule + override authority + universal adversarial protocol + evidence taxonomy + claim-citation contract
- [ ] **Phase 410: Anti-Pattern Scanning & Threat Modeling** — Code/architecture/test anti-pattern catalog + Python-3.12 extensions + extension hook + STRIDE register + per-disposition schemas + security verifier verdict logic + accepted-risks registry + worked STRIDE example
- [ ] **Phase 411: Plan Checker & Evidence Chain** — 9 pre-execution checks (PCK-01..09) + verdict semantics (passed/blocked/warnings) + verifier output schema + canonical citation grammar + VERIFY→PLAN→STEP→PHASE→ARC walker + `state verify trace` CLI design + retention rule

---

## Phase Details

### Phase 407: Verifier Chain Architecture
**Goal**: The hierarchical verifier chain is canonically specified across all five scopes (Step / Slice / Phase / Arc / Cross-Tier) with each verifier's input, algorithm, output, failure mode, and evidence type fully documented — implementable without further design. Every verifier's event types are registered as an append-only amendment to v40 EVENT-TAXONOMY.md.
**Depends on**: Nothing (first v42 phase; consumes v40 hierarchy + v41 harness as background context)
**Requirements**: VCH-01, VCH-02, VCH-03, VCH-04, VCH-05, VCH-06, VCH-07
**Success Criteria** (what must be TRUE):
  1. A `VERIFIER-CHAIN.md` spec document exists at the canonical location (TBD by plan-phase, likely `.state/build/quality/`) enumerating the five verifier scopes — Step (VCH-01), Slice rollup (VCH-02), Phase rollup (VCH-03), Arc rollup (VCH-04), Cross-Tier (VCH-05) — with a single normalized schema per verifier: `inputs` (artifacts/events/code read), `algorithm` (concrete decision logic, not pseudocode), `outputs` (event + markdown + TUI update), `failure_mode` (one of: retry loop, human gate, auto-fix attempt), `evidence` (what counts as proof).
  2. The Step verifier suite (VCH-01) decomposes into four named sub-verifiers — goal-backward, security, stub-detector, anti-pattern — each with its own row in the verifier schema and a forward-reference to the phase that owns its deep design (goal-backward → Phase 409, security → Phase 410, stub → Phase 408, anti-pattern → Phase 410).
  3. The Cross-Tier verifier (VCH-05) has an explicit scope rule documented as one of: all Arcs, only Arcs with `depends_on` edges, or only Arcs with file overlap; the chosen rule is justified against the v40 Arc model and the v5 DAG scheduler's edge semantics.
  4. Every verifier's failure mode (VCH-06) is mapped to one of the three classes — retry loop, human gate, auto-fix attempt — with explicit transition criteria (max retries, escalation triggers, human-gate routing through opencode `question` tool consistent with v41 D-10 / HRN-06).
  5. A `## v42 Amendment` block appended to `.state/build/runtime/EVENT-TAXONOMY.md` (or the v40 canonical location for the event registry) registers every new verifier event type (VCH-07) — e.g., `state.verifier.step.passed`, `state.verifier.step.failed`, `state.verifier.slice.passed`, `state.verifier.slice.failed`, `state.verifier.phase.passed`, `state.verifier.phase.failed`, `state.verifier.arc.passed`, `state.verifier.arc.failed`, `state.verifier.crosstier.passed`, `state.verifier.crosstier.regression_detected` — with Pydantic payload models (`extra="forbid"`) and replay semantics.

**Plans**: TBD

---

### Phase 408: 4-Level Verification Model & Stub Detection
**Goal**: The 4-level verification depth model (Existence → Substantive → Wired → Data-Flowing) is fully specified per level with checks, tools, pass/fail evidence, edge cases, and a Python-3.12 feasibility analysis; and the stub detection framework — pattern catalog, severity classification (BLOCKER/WARNING/KNOWN), AST-driven caller trace-through, and Known-Stubs SUMMARY.md schema — is fully specified, including the legitimate-stub disambiguation rule that prevents false BLOCKER promotion of Step-appropriate stubs.
**Depends on**: Phase 407 (the 4-level model is the depth dimension OF each Step sub-verifier defined in VCH-01; stub detection is one of the four Step sub-verifiers)
**Requirements**: LVL-01, LVL-02, LVL-03, LVL-04, LVL-05, LVL-06, LVL-07, STB-01, STB-02, STB-03, STB-04
**Success Criteria** (what must be TRUE):
  1. A `VERIFICATION-LEVELS.md` spec document defines all four levels (LVL-01 Existence, LVL-02 Substantive, LVL-03 Wired, LVL-04 Data-Flowing) with a uniform per-level schema: `checks` (concrete behavioral assertions), `tools` (e.g., `pathlib`, `git log --grep`, `events.sqlite` query, `ast.NodeVisitor`, `ruff`), `pass_evidence` (what success looks like), `fail_evidence` (what failure looks like), `edge_cases` (per-level corner cases including legitimate stubs at the Step boundary). Level 3 (LVL-03) names its scope rule explicitly — Slice worktree only vs. full project — and justifies the choice against verifier perf budget (LVL-07). Level 4 (LVL-04) contains a dedicated Python-3.12 feasibility analysis section (which patterns are detectable: real DB queries, fetch/store calls, UI render with live data; which are NOT reliably detectable: arbitrary code paths in dynamic languages).
  2. The per-level override mechanism (LVL-05) is specified with frontmatter schema (`reason: <text>`, `accepted_by: <user|agent>`, `accepted_at: <ISO-8601>`) plus the 80% token-overlap fuzzy-match rule for goal alignment (matching GSD's proven pattern), and the audit-trail rule that every override is logged into VERIFY.md and emits a `state.verifier.level.overridden` event.
  3. The legitimate-stub disambiguation rule (LVL-06) is specified as the canonical interplay between the 4-level model and STB-04: the verifier reads `## Known Stubs` from SUMMARY.md before promoting any stub detection to BLOCKER; missing-Known-Stubs section when stubs are present is itself a verifier failure mode; the Known-Stubs schema (id, location, severity, resolution-plan-link) is defined as required SUMMARY.md frontmatter or section.
  4. A `STUB-DETECTION.md` spec document defines the full stub pattern catalog (STB-01) — `pass`, `...` (Ellipsis), `raise NotImplementedError`, `return None` (in data-producing functions), `return []`/`return {}`/`return ""`, untracked `TODO`/`FIXME`, hardcoded example strings, empty data files, placeholder strings (`"todo"`, `"fixme"`, `"placeholder"`, `"stub"`, `"example"`, `"test value"`) — with per-pattern detection mechanism (grep regex, AST node match, content-equality check).
  5. The stub severity classification (STB-02) defines BLOCKER / WARNING / KNOWN with explicit promotion/demotion rules, and the stub trace-through algorithm (STB-03) is specified as an AST walker + import-graph traversal: if a function returns a hardcoded-empty value, walk all callers; promote to BLOCKER if the emptiness reaches a rendering or API surface, demote to WARNING if the emptiness is handled gracefully (consumer guards against empty result). The Per-Step performance budget (LVL-07) is documented with measurement protocol (`time` wrapping per behavioral check, ≤10s per check, full-Step 4-level cap).

**Plans**: TBD

---

### Phase 409: Goal-Backward Protocol & Adversarial Stance
**Goal**: The shared must-have derivation algorithm, the pre-execution plan-checker, and the post-execution goal-backward verifier are fully specified as one cohesive goal-backward protocol; and the universal adversarial verification stance — default-distrust posture, falsification-first protocol, evidence taxonomy, claim-citation contract — is specified as a single canonical doc that every verifier (Step / Slice / Phase / Arc / Cross-Tier) references.
**Depends on**: Phase 408 (the goal-backward verifier's evidence types reference the 4-level model from Phase 408; the adversarial stance's "what is/isn't evidence" rule references the stub-detection BLOCKER/WARNING/KNOWN taxonomy)
**Requirements**: GBP-01, GBP-02, GBP-03, GBP-04, GBP-05, ADV-01, ADV-02, ADV-03, ADV-04
**Success Criteria** (what must be TRUE):
  1. A `GOAL-BACKWARD.md` spec document defines the must-have derivation algorithm (GBP-01) as a deterministic function whose inputs are STEP.md goal text + ARC/PHASE/SLICE success-criteria blocks + REQ-IDs cited in STEP.md + locked decisions from DISCUSS.md; output is the full must-have list written to VERIFY.md frontmatter for audit. The derivation algorithm names every input source by canonical path (relative to a Slice worktree) and orders precedence when sources conflict.
  2. The pre-execution plan-checker contract (GBP-02) is specified: for each must-have, the checker traces a concrete task path through PLAN.md and produces verdict `passed | blocked | warnings` with explicit definitions per verdict (passed = all must-haves trace to ≥1 task; blocked = ≥1 must-have has no traceable task — replan required; warnings = task traces exist but are thin/ambiguous — human gate). PCK-05 (Phase 411) is identified as the plan-checker's invocation of this contract.
  3. The post-execution goal-backward verifier contract (GBP-03) enumerates the four evidence types — code exists (file present + AST match), tests pass (substantive test, not tautological), LSP clean (type-safe), behavioral check passes — with explicit "what counts / what doesn't count" rules per type, and the SUMMARY.md trust rule (GBP-04) is asserted as a normative gate: the verifier reads SUMMARY.md only to enumerate claims; codebase evidence is the sole arbiter (matches D-7 mutability matrix from v41). The must-have override authority spec (GBP-05) prohibits agent self-override and requires explicit `accepted_by` (user identity) with the supporting evidence type.
  4. An `ADVERSARIAL-PROTOCOL.md` spec document specifies the adversarial protocol (ADV-01) as a four-step procedure: (i) load all claims from PLAN.md, SUMMARY.md, EXECUTE.log; (ii) for each claim, attempt to falsify against codebase evidence; (iii) accept only if falsification fails AND positive evidence exists; (iv) produce verdict with specific citations per accepted/rejected claim. The evidence taxonomy (ADV-02) is documented as a table: code diff (yes), commit message (no), substantive tests (yes), mocks-of-mocks (no), LSP clean (partial — type-safety only), behavioral check (yes only if verifier runs it itself), SUMMARY.md claim (no — claim enumeration only).
  5. The claim-citation contract (ADV-03) defines canonical citation grammar — `file_path:line_number`, `commit:<hash>`, `event:<id>`, `test:<runner-output-id>` — and asserts every accepted/rejected claim must carry ≥1 citation. The adversarial protocol's reusability across all verifier scopes (ADV-04) is enforced by making `ADVERSARIAL-PROTOCOL.md` the single canonical doc referenced by every verifier spec in Phase 407's `VERIFIER-CHAIN.md` (forward cross-reference invariant).

**Plans**: TBD

---

### Phase 410: Anti-Pattern Scanning & Threat Modeling
**Goal**: The anti-pattern scanning system — code, architecture, and test anti-pattern catalogs with Python-3.12 specific extensions and a per-project extension hook — is fully specified; and the STRIDE threat modeling framework — required disposition coverage, per-disposition schemas, automated security verifier verdict logic, accepted-risks registry, and a fully worked example — is fully specified. Both systems are concrete enough that the Step-level security verifier and anti-pattern scanner sub-verifiers (declared in VCH-01) can be built without further design.
**Depends on**: Phase 409 (the anti-pattern scanner and security verifier both inherit the adversarial protocol and claim-citation contract from Phase 409; the security verifier's BLOCKER/WARNING verdict semantics reuse ADV-02 evidence taxonomy)
**Requirements**: APS-01, APS-02, APS-03, APS-04, APS-05, THM-01, THM-02, THM-03, THM-04, THM-05
**Success Criteria** (what must be TRUE):
  1. An `ANTI-PATTERN-CATALOG.md` spec document defines the code anti-pattern catalog (APS-01) — bare `except` / `except Exception` without re-raise, `print()` in production paths, secret-like strings (entropy + format heuristics), SQL string concatenation, `os.system` / `subprocess(shell=True)` with user input, hardcoded file paths, undeclared imports, functions >100 lines, deep nesting (>4 levels), missing public-API docstrings — with per-pattern detection mechanism (regex, AST node match, ruff rule ID, import-graph query), severity (BLOCKER or WARNING), and remediation guidance. The architecture anti-pattern catalog (APS-02) — circular imports, `state_build` importing `state_teach` (mode-isolation violation, cites v11), direct FS access outside `.state/` subtree, bypassing the event store for state changes — is specified with detection (import-graph lint reusing `state_core.import_lint`), severity, and remediation.
  2. The test anti-pattern catalog (APS-03) — no-assertion tests, mock-only tests, tautological asserts (`assert True`, `assert 1 == 1`), tests not exercising stated verify criteria — is specified with detection, severity, and remediation, including the cross-reference to GBP-03's "substantive tests" evidence rule.
  3. The Python-3.12 specific extensions (APS-04) are documented as an explicit mapping table — which GSD anti-patterns map to Python equivalents (e.g., `console.log` → `print()`, `exec` → `subprocess(shell=True)`, `==` → `is` for singletons) and which are new (e.g., asyncio task-cancellation handling, structural pattern-matching exhaustiveness, type-hint coverage). The extension hook (APS-05) defines the per-phase / per-plan declaration mechanism: a frontmatter `anti_patterns_extensions: [...]` list or a colocated `EXTENSIONS.md` file referenced by PLAN.md, with the integration rule that extensions are union-merged with the canonical catalog (never override).
  4. A `THREAT-MODEL.md` spec document defines the STRIDE coverage requirement (THM-01): every PLAN.md must declare disposition (`mitigate` / `accept` / `transfer`) for all 6 STRIDE categories — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege; missing categories block the plan-checker (Phase 411 PCK-08 cross-references this rule). The per-disposition schema (THM-02) defines required fields per kind: `mitigate` requires `mitigation_pattern: <code/grep target>` + `cited_files: [path:line]` + `test_evidence`; `accept` requires `acceptance_authority: <user-id>` + `registry_entry_id` + `rationale`; `transfer` requires `target_system` + `transfer_doc_link` + `system_verified: bool`.
  5. The security verifier spec (THM-03) defines verdict logic per disposition: for `mitigate` threats — grep/AST-check mitigation pattern in cited files, verdict `CLOSED` if found, `OPEN:BLOCKER` if missing; for `accept` threats — verify entry in accepted-risks registry, verdict `CLOSED` if registered with valid authority, `OPEN:BLOCKER` if not; for `transfer` threats — verify transfer doc exists and target system is verified, verdict `CLOSED` if both, `WARNING` if doc exists but verification thin. The accepted-risks registry schema (THM-04) defines the global registry file location (e.g., `.state/build/quality/accepted-risks.md` or `.state/build/quality/accepted-risks.jsonl`), per-entry required fields (id, threat, disposition rationale, accepted_by, accepted_at, expiry), and audit format. A complete worked STRIDE example (THM-05) covers all 6 categories with realistic Build-mode threats (e.g., S = forged auth token in MCP request, T = event-store tampering, R = missing audit trail for verifier override, I = secret leak via log redactor failure, D = subagent fanout exhausts daemon, E = mode-isolation bypass via plugin hook) with realistic dispositions.

**Plans**: TBD

---

### Phase 411: Plan Checker & Evidence Chain
**Goal**: The pre-execution plan checker — 9 named validation checks producing verdict `passed | blocked | warnings` — and the post-execution evidence & artifact chain — verifier output schema, canonical citation grammar, VERIFY→PLAN→STEP→PHASE→ARC walker, `state verify trace <step-id>` CLI design, and evidence retention rule — are fully specified. This phase synthesizes every prior v42 phase: PCK-05 cites GBP-01, PCK-06/07 cite the v41 harness CONTEXT-PROTOCOL/HARNESS-ARCHITECTURE, PCK-08 cites THM-01, PCK-09 cites v41 CTX-XX, and EVD-03 reuses v40 REF-XX cross-reference invariants.
**Depends on**: Phase 410 (PCK-08 directly cites THM-01 STRIDE coverage; the verifier output schema EVD-01 unifies the verdict shapes from VCH/LVL/STB/GBP/ADV/APS/THM specs)
**Requirements**: PCK-01, PCK-02, PCK-03, PCK-04, PCK-05, PCK-06, PCK-07, PCK-08, PCK-09, PCK-10, EVD-01, EVD-02, EVD-03, EVD-04, EVD-05
**Success Criteria** (what must be TRUE):
  1. A `PLAN-CHECKER.md` spec document defines all 9 pre-execution checks as a numbered protocol with per-check `detection_mechanism` + `verdict_criteria` + `failure_action`: Check 1 (PCK-01) — PLAN.md requirement ID matches STEP.md; Check 2 (PCK-02) — every task has all four required fields (`files`, `action`, `verify`, `done`); Check 3 (PCK-03) — task `files` use exact paths (no wildcards, no directories); Check 4 (PCK-04) — no two concurrent-wave tasks touch the same file (forces wave bump); Check 5 (PCK-05) — every must-have traceable to ≥1 task (cross-reference GBP-01 derivation algorithm); Check 6 (PCK-06) — every RESEARCH.md recommendation either followed or explicitly overridden; Check 7 (PCK-07) — every CONTEXT.md locked decision implemented or explicitly deferred; Check 8 (PCK-08) — STRIDE coverage complete per THM-01; Check 9 (PCK-09) — task context budgets within thresholds (cross-reference v41 CTX-01 200k absolute budget + CTX-XX per-task harness limit).
  2. The plan-checker verdict semantics (PCK-10) are specified: `passed` = all 9 checks green, execution proceeds; `blocked` = ≥1 critical check failed, replan loop returns control to plan-slice (cross-reference v41 SLC plan-slice cycle); `warnings` = non-critical checks raised flags, human gate via opencode `question` tool (cross-reference v41 HRN-06). The per-check classification of "critical" vs "non-critical" is documented as a static table (e.g., PCK-02/03/05/08 critical; PCK-06/07 non-critical with warnings; PCK-04 critical; PCK-09 warning unless exceeds hard cap).
  3. An `EVIDENCE-CHAIN.md` spec document defines the verifier output schema (EVD-01): `verifier_name`, `timestamp`, `event_id`, `pass_fail: bool`, `evidence_list: [Citation]`, `citations: [Citation]`, written to both VERIFY.md (markdown for human audit) and the event store (Pydantic-validated event payload). The canonical citation grammar (EVD-02) is normatively defined: `file_path:line_number` (file evidence), `commit:<hash>` (git evidence), `event:<id>` (event-store evidence), `test:<runner-output-id>` (test evidence) — this is the SAME grammar referenced by ADV-03 (Phase 409), enforced as the single canonical definition.
  4. The auditable chain spec (EVD-03) defines the upward walker VERIFY.md → PLAN.md → STEP.md → PHASE.md → ARC.md, with cross-reference invariants reusing the v40 REF-XX rules (named explicitly: REF-01 through REF-06 from v40 Phase 401). Every artifact's required cross-reference fields (e.g., STEP.md.parent = SLICE id, SLICE.parent = PHASE id) are tabulated, and chain-break detection is specified: the walker emits a `state.evidence.chain_broken` event if any required parent reference is missing or unresolvable.
  5. The `state verify trace <step-id>` CLI design (EVD-04) is specified: output shape (text tree with VERIFY → PLAN → STEP → PHASE → ARC nodes, per-node verifier verdict + citations + timestamp), traversal order (Step-up — always upward from `<step-id>`), failure modes when chain breaks (one of: artifact missing on disk, parent reference missing, parent reference unresolvable; per failure mode the CLI emits a distinct exit code and writes a diagnostic event). The evidence retention rule (EVD-05) defines when verifier outputs are pruned vs retained: VERIFY.md is permanent (artifact in git); event-store rows for verifier events follow the v1 event-store retention policy (never pruned for SQLite authoritative tier); SUMMARY-attached evidence (test logs, behavioral check outputs) follows the retention coupling rule (retained as long as the parent Step/Slice is referenced by any unshipped downstream).

**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 407. Verifier Chain Architecture | 0/0 | Not started | - |
| 408. 4-Level Verification Model & Stub Detection | 0/0 | Not started | - |
| 409. Goal-Backward Protocol & Adversarial Stance | 0/0 | Not started | - |
| 410. Anti-Pattern Scanning & Threat Modeling | 0/0 | Not started | - |
| 411. Plan Checker & Evidence Chain | 0/0 | Not started | - |

---

## Requirement Coverage

| Category | Count | REQ-IDs | Phase |
|----------|-------|---------|-------|
| VCH — Verifier Chain | 7 | VCH-01..VCH-07 | 407 |
| LVL — 4-Level Verification Model | 7 | LVL-01..LVL-07 | 408 |
| STB — Stub Detection Framework | 4 | STB-01..STB-04 | 408 |
| GBP — Goal-Backward Planning Protocol | 5 | GBP-01..GBP-05 | 409 |
| ADV — Adversarial Verification Stance | 4 | ADV-01..ADV-04 | 409 |
| APS — Anti-Pattern Scanning System | 5 | APS-01..APS-05 | 410 |
| THM — Threat Modeling Framework | 5 | THM-01..THM-05 | 410 |
| PCK — Plan Checker | 10 | PCK-01..PCK-10 | 411 |
| EVD — Evidence & Artifact Chain | 5 | EVD-01..EVD-05 | 411 |
| **Total** | **51** | — | **100% mapped** |

---

## Phase DAG

```
407 ──► 408 ──► 409 ──► 410 ──► 411
(linear; each phase consumes prior spec output)
```

Linear by design — each phase synthesizes the prior phase's specs:

- **407 → 408**: Phase 408 deepens the Step-verifier sub-verifiers declared by VCH-01.
- **408 → 409**: Phase 409 references the 4-level evidence types and STB severity taxonomy.
- **409 → 410**: Phase 410 inherits the adversarial protocol and citation grammar; security verifier reuses ADV evidence taxonomy.
- **410 → 411**: Phase 411 PCK-08 cites THM-01; EVD-01 verifier output schema unifies every prior phase's verdict shape.

No phases are parallel-safe within v42 — the spec cohesion gain from sequential synthesis outweighs the wall-clock cost of parallelism, especially for a design-only milestone.

---

## Out of Scope (v42)

- **Implementation code** — design-only milestone; implementation lives in v14 (Build Kernel) and v15 (Build Core Commands).
- **GSD command porting** (`state verify`, `state verify trace`, `state plan-check` CLI commands) — owned by v15 / v16.
- **Workflow orchestration** (how verifiers are invoked from a Step lifecycle, retry routing across verifier scopes) — owned by v43 (Build Workflow Orchestration).
- **Teach-mode verification** (learning verifier, mental-model checks) — owned by v48 (Teach Quality & Learning Verification Pipeline).
- **LLM-assisted verification** (verifier-as-agent) — decision deferred to Phase 409 adversarial-stance design; if rejected as non-deterministic, captured here at milestone close.
- **UAT script generation / behavioral test automation** — owned by v44+ (test infrastructure milestone).
- **Performance benchmarking suite for verifiers** — owned by v44+.

---

*Roadmap created: 2026-05-12*
