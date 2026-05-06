# v42 Handoff: Build Quality Pipeline Architecture

## Milestone Goal

Design the complete quality pipeline for Build mode — the verifier chain, goal-backward planning protocol, adversarial verification stance, stub detection framework, anti-pattern scanning system, threat modeling framework, and plan checker. This is what ensures the code output is correct, complete, secure, and achieves its intended goal.

## What This Milestone Must Produce

### 1. Verifier Chain Architecture

Design the hierarchical verifier chain that aggregates upward through all four tiers:

```
STEP VERIFIERS (run per Step)
├── Goal-backward verifier — "does this Step's output achieve its stated goal?"
├── Security verifier — SQLi, path traversal, secret leak, shell meta
├── Stub detector — empty values, placeholders, disconnected code
└── Anti-pattern scanner — TODO/FIXME, console.log, empty catch, hardcoded data

SLICE VERIFIER (runs after all Steps in a Slice are DONE)
├── Slice rollup — aggregates Step results + Slice-level integration
└── Fails the Slice if ANY Step failed

PHASE VERIFIER (runs after all Slices in a Phase are SHIPPED)
├── Phase rollup — aggregates Slice results + cross-Slice integration
└── Phase-level acceptance criteria

ARC VERIFIER (runs after all Phases in an Arc are SHIPPED)
├── Arc rollup — aggregates Phase results + Arc acceptance criteria
└── Fails the Arc if ANY Phase failed

CROSS-TIER VERIFIER (runs after an Arc boundary)
├── Regression detection — does Arc B's work break Arc A?
└── Cross-Arc integration tests
```

For EACH verifier, specify:
- **Input**: What artifacts, events, and code it reads
- **Algorithm**: How it determines pass/fail (not pseudocode — actual decision logic)
- **Output**: What it writes (event + markdown + TUI update)
- **Failure mode**: What happens on fail (retry loop? human gate? auto-fix attempt?)
- **Evidence**: What evidence it produces to support its verdict

### 2. The 4-Level Verification Model

Design the verification depth levels. This is GSD's most powerful quality innovation — most tools stop at Level 1 (does the file exist?). State's verifier must go deeper:

**Level 1 — Existence:**
- Does the file/artifact exist on disk?
- Does the commit exist in git log?
- Does the event exist in the event store?

**Level 2 — Substantive:**
- Does the file have content beyond a stub? (min_lines check, pattern check)
- Does the commit have a meaningful diff? (not just whitespace)
- Does the artifact have all required frontmatter fields?

**Level 3 — Wired:**
- Is the file imported AND used? (check imports, check usage via grep/AST)
- Does the commit's code actually get called from somewhere?
- Is the artifact cross-referenced by other artifacts that should reference it?

**Level 4 — Data-Flowing:**
- Does the implementation produce real data? (not static/empty/dummy returns)
- For code: real DB queries found → data variable set by fetch/query/store → props not hardcoded empty at call site
- For config: config value actually read at runtime, not just defined
- For UI: component renders with live data, not placeholder strings
- For APIs: endpoint returns dynamic response, not hardcoded example

For each level, define:
- What checks are run
- What tools/techniques are used (grep patterns, AST analysis, runtime probes)
- What evidence constitutes a pass
- What evidence constitutes a fail
- Edge cases (what if the code IS supposed to be a stub at this stage?)

### 3. Goal-Backward Planning Protocol

Design how the plan-checker and goal-backward verifier work together:

**Plan-checker (pre-execution, Phase 137):**
- Input: PLAN.md + STEP.md goal + parent Slice/Phase context
- Checks: Does this plan, if executed perfectly, guarantee the goal is achieved?
- Method: For each must-have in the goal, trace a concrete path through the plan's tasks
- Output: `plan_check: passed | blocked | warnings`
- Blocked means: the plan CANNOT achieve the goal — must replan
- Warnings means: the plan MIGHT achieve the goal but has gaps — human decision

**Goal-backward verifier (post-execution, BLD-03):**
- Input: STEP.md goal + committed code + EXECUTE.log
- Method: For each must-have in the goal, find evidence in the codebase that it is satisfied
- Evidence types: code exists, tests pass, LSP clean, behavioral check passes
- Output: VERIFY.md with per-must-have pass/fail + evidence citations
- Trusts NOTHING from SUMMARY.md — only codebase evidence

**Must-have derivation:**
- Must-haves come from: STEP.md goal + ARC/PHASE/SLICE success criteria + REQ-IDs + decisions from DISCUSS.md
- The verifier derives the full must-have list before verification begins
- The derived list is written to VERIFY.md frontmatter for audit trail
- Overrides: specific must-haves can be marked as deferred/not-applicable with reason

### 4. Adversarial Verification Stance

Design the adversarial posture all verifiers take:

- **Default assumption: the implementation is wrong.** Evidence must prove otherwise.
- **SUMMARY.md claims are NOT evidence.** The verifier reads SUMMARY.md only to know what was claimed, then verifies against codebase.
- **Commit messages are NOT evidence.** Code diff is evidence.
- **Test pass is evidence** — but only if tests are substantive (not tautological, not testing mocks of mocks)
- **LSP clean is evidence** — but only for type-safety, not correctness
- **Behavioral check is evidence** — but the verifier runs it itself, doesn't trust agent output

Define the adversarial verification protocol:
1. Load all claims (from PLAN.md, SUMMARY.md, EXECUTE.log)
2. For each claim, attempt to falsify it against the codebase
3. Only accept a claim as true if falsification fails AND positive evidence exists
4. Produce a verdict with specific citations for every accepted/rejected claim

### 5. Stub Detection Framework

Design how the verifier detects incomplete implementations:

**Stub patterns to detect:**
- `pass` in function bodies that should have logic
- `...` (Ellipsis) in function bodies
- `raise NotImplementedError`
- `return None` in functions that should return data
- `return []` / `return {}` / `return ""` in data-producing functions
- `TODO` and `FIXME` comments without associated tracking
- Hardcoded example values flowing to UI/API output
- Empty data files (`[]`, `{}`, `""`)
- Placeholder strings ("todo", "fixme", "placeholder", "stub", "example", "test value")

**Stub severity classification:**
- BLOCKER: stub prevents feature from working at all
- WARNING: stub degrades quality but feature partially works
- KNOWN: stub is documented in SUMMARY.md `## Known Stubs` section with a plan for resolution

**Stub trace-through:**
- If a function returns a hardcoded empty value, trace all callers to see if the emptiness reaches the UI/API surface
- Flag as BLOCKER if empty data reaches rendering, WARNING if emptiness is handled gracefully

### 6. Anti-Pattern Scanning System

Design the anti-pattern scanner (runs during verify, also optionally during code review):

**Code anti-patterns:**
- Bare `except:` or `except Exception:` without re-raise or structured handling
- `console.log` / `print()` in production paths
- Secret-like patterns in code (API keys, tokens, passwords)
- SQL string concatenation (SQL injection vector)
- `os.system()` / `subprocess(shell=True)` with user input
- Hardcoded file paths (not config-driven)
- Import of modules not in declared dependencies
- Functions > 100 lines (complexity smell)
- Deep nesting (>4 levels)
- Missing docstrings on public APIs

**Architecture anti-patterns:**
- Circular imports
- `state_build` importing `state_teach` (mode isolation violation)
- Direct filesystem access outside `.state/` subtree
- Bypassing the event store for state changes

**Test anti-patterns:**
- Tests with no assertions
- Tests that only test mocks
- Tautological tests (`assert True`)
- Tests that don't exercise the stated verify criteria

For each anti-pattern: detection mechanism (grep, AST, import-graph), severity (BLOCKER/WARNING), and remediation guidance.

### 7. Threat Modeling Framework

Design the threat model system that every PLAN.md must include:

**STRIDE threat register:**
| Threat Category | Example | Required in Plan? |
|-----------------|---------|-------------------|
| Spoofing | Impersonation, forged tokens | Yes |
| Tampering | Data modification, injection | Yes |
| Repudiation | Non-repudiation, audit gaps | Yes |
| Information Disclosure | Data leaks, logging secrets | Yes |
| Denial of Service | Resource exhaustion | Yes |
| Elevation of Privilege | Unauthorized access | Yes |

For each threat in the register, PLAN.md must declare:
- **Disposition**: `mitigate` (code will address it) | `accept` (risk is known and accepted) | `transfer` (delegated to another system)
- **If mitigate**: What code/pattern mitigates it? What tests prove the mitigation works?
- **If accept**: Why is this risk acceptable? Who accepted it?
- **If transfer**: What system handles it? Is that system verified?

**Security verifier (post-execution):**
- For every `mitigate` threat: grep for the mitigation pattern in the cited files
- For every `accept` threat: verify the acceptance is logged in the accepted risks registry
- For every `transfer` threat: verify the transfer documentation exists
- Verdict: CLOSED (mitigation found), OPEN:BLOCKER (mitigation missing), WARNING (evidence thin)

### 8. Plan Checker Design

Design the plan checker that validates PLAN.md before execution can proceed:

**Checks:**
1. Does PLAN.md declare a requirement ID that matches STEP.md?
2. Does every task in PLAN.md have: files, action, verify, done?
3. Does every task's files list use exact paths (not wildcards, not directories)?
4. Do any two concurrent-wave tasks touch the same file? (force wave bump)
5. Is every must-have from the goal traceable to at least one task?
6. Is every RESEARCH.md recommendation followed or explicitly overridden?
7. Is every CONTEXT.md locked decision implemented or explicitly deferred?
8. Does the threat model cover all STRIDE categories?
9. Are task context budgets within thresholds?

**Verdicts:**
- `passed` — all checks green, execution can proceed
- `blocked` — critical check failed, must replan (returns to plan phase)
- `warnings` — non-critical issues, human decides whether to proceed

### 9. Evidence & Artifact Chain

Design how verification evidence is stored and linked:

- Every verifier output includes: verifier name, timestamp, event ID, pass/fail, evidence list, citations
- Evidence citations use: file paths + line numbers, commit hashes, event IDs, test run outputs
- The evidence chain is auditable: from VERIFY.md → PLAN.md → STEP.md → PHASE.md → ARC.md
- `state verify trace <step-id>` should be able to walk the entire evidence chain

## Success Criteria

1. The 4-level verification model is specified with exact checks, tools, pass/fail criteria, and edge cases per level.
2. The goal-backward planning protocol produces a must-have list that can be mechanically verified.
3. The adversarial verification stance is specified as a protocol that any verifier follows.
4. The stub detection framework catches all stub patterns with severity classification.
5. The anti-pattern scanner covers code, architecture, and test anti-patterns with detection mechanisms.
6. The threat modeling framework produces auditable STRIDE registers per Step.
7. The plan checker has all 9 checks specified with pass/blocked/warnings verdicts.
8. The evidence chain is auditable from VERIFY.md up to ARC.md.

## Research Inputs

**Primary reference — GSD quality pipeline (the richest source):**
- `state-inputs/get-shit-done/commands/gsd/gsd-verifier.md` — 10-step adversarial verification protocol, 4-level depth, anti-pattern scan, behavioral spot-checks, must-have derivation, override system, gap closure
- `state-inputs/get-shit-done/commands/gsd/gsd-planner.md` — goal-backward planning, scope reduction prohibition, must-have artifact reachability, multi-source coverage audit
- `state-inputs/get-shit-done/commands/gsd/gsd-secure-phase.md` — threat model verification, STRIDE dispositions, OPEN_THREATS classification
- `state-inputs/get-shit-done/commands/gsd/gsd-code-review.md` — BLOCKER/WARNING finding classification, adversarial stance
- `state-inputs/get-shit-done/commands/gsd/gsd-code-review-fix.md` — auto-fix pipeline per finding
- `state-inputs/get-shit-done/commands/gsd/gsd-plan-checker.md` — plan validation criteria (if exists)
- `state-inputs/get-shit-done/bin/lib/verify.cjs` — 19 health-check codes, schema drift detection, artifact validation
- `state-inputs/get-shit-done/bin/lib/security.cjs` — injection pattern scanning, entropy anomaly detection

**State shipped code (what's already built):**
- `src/state_core/schema.py` — event types for verification (`state.step.verify_passed`, `state.step.verify_failed`, etc.)
- `src/state_core/projector.py` — how verification events update cache tables
- `src/state_core/events.py` — event store API (verifier writes events here)
- `src/state_core/import_lint.py` — existing mode isolation lint (extend for anti-pattern scanning?)
- `src/state_core/observability/redactor.py` — existing token redaction (related to secret detection)

**Planning context:**
- `.planning/milestones/v14/REQUIREMENTS.md` — BLD-03 (goal-backward verifier), BLD-04 (slice rollup), BLD-05 (phase rollup), BLD-06 (arc rollup), BLD-07 (cross-tier), BLD-08 (security verifier), BLD-09 (result storage)
- `.planning/research/ARCHITECTURE.md` — §8 (build mode kernel, verifier chain pseudocode), §5 (event taxonomy)
- `.planning/milestones/v15/REQUIREMENTS.md` — CMD-07 (plan checker), CMD-08 (gray-area routing)

## Key Questions for Discuss-Phase

1. **Verifier intelligence**: How smart should the verifier be? Purely mechanical (grep, AST, test runs) or LLM-assisted (reads code, reasons about goal achievement)? Mechanical is reproducible but limited. LLM-assisted is powerful but non-deterministic.

2. **Level 3 (Wired) depth**: Tracing imports and usage across a codebase is expensive. Should Level 3 be limited to files within the current Slice's worktree? Or should it trace across the entire project?

3. **Level 4 (Data-Flowing) feasibility**: Detecting whether data actually flows vs. is hardcoded is extremely hard in a general-purpose language. Is Level 4 realistic for Python? Should it be limited to specific patterns (DB queries, API responses)?

4. **Stub detection vs legitimate stubs**: Some code is legitimately stubbed at a given Step (the next Step implements it). How does the verifier distinguish between a Step-appropriate stub and a forgotten implementation?

5. **Must-have override authority**: Who can override a must-have? The agent? The user? Only the user? With what evidence requirement?

6. **Verifier performance budget**: How long should verification take? GSD targets individual behavioral checks at ≤10 seconds each. What's the budget for a full 4-level verification of a Step?

7. **Cross-tier verifier scope**: The cross-tier verifier checks regressions between completed Arcs. What's the scope? All Arcs? Only Arcs that share files? Only Arcs with declared dependencies?

## Dependencies

- **v40 (Hierarchy & Artifact System)** — MUST be complete. The verifier chain spans all four tiers and must know what artifacts to check.
- **v41 (Agent Harness)** — SHOULD be complete. The plan checker and scope reduction prohibition interact with the harness's deviation rules.
- **v14 (Build Kernel Step FSM)** — original milestone that this design will eventually inform.

## Scope Boundaries

**In scope:**
- Complete verifier chain architecture (all tiers)
- 4-level verification model (exists → substantive → wired → data-flowing)
- Goal-backward planning protocol
- Adversarial verification stance
- Stub detection framework with severity
- Anti-pattern scanning system
- Threat modeling framework
- Plan checker design
- Evidence chain design

**Out of scope:**
- Implementation of any verifier
- GSD command porting (v43)
- How verifiers are invoked (workflow orchestration is v43)
- Teach mode verification (v48)

## Reference Patterns from GSD

1. **4-level verification**: GSD's exists→substantive→wired→data-flowing model is the gold standard. State should adopt it but design each level for Python 3.12+ (not TypeScript/Node as GSD does).

2. **Anti-pattern scanning**: GSD's verifier scans for TODO/FIXME, hardcoded data, console.log, disconnected props. State should extend this with Python-specific anti-patterns (bare except, shell=True, import *).

3. **STRIDE threat modeling**: GSD's PLAN.md threat model with mitigate/accept/transfer dispositions and automated verification by the security auditor is proven. State should adopt it.

4. **Gap closure cycle**: GSD's `gaps_found → plan-gaps → re-execute → re-verify → repeat` cycle is essential. State's verifier chain must support partial re-verification.

5. **Override system**: GSD's frontmatter overrides with 80% token-overlap fuzzy matching and required reason/accepted_by/accepted_at fields is well-designed. State should adopt a similar system.
