---
phase: 405
phase_name: Deviation Rules & Subagent Management
audited: 2026-05-11
asvs_level: 1
phase_type: design-only
threats_total: 29
threats_closed: 29
threats_open: 0
status: secure
---

# Phase 405 Security Audit

## Audit Scope

Phase 405 is **design-only** — produces 3 canonical specification documents (DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md) plus 3 amendment blocks appended to v40 master spec docs (EVENT-TAXONOMY.md, ARTIFACT-CATALOG.md, FRONTMATTER-SCHEMAS.md). No production code lands.

Threats live at two scopes:
1. **Spec authoring threats** — risk that the produced spec docs themselves mislead the v14 implementer (mitigations: verbatim Pydantic schemas, explicit prose authority statements, cross-reference pinning).
2. **Forward-design threats** — risks that the *specified* runtime behaviors create attack surface when v14 implements them (mitigations: explicit constraints in the spec text that v14 MUST honor, treating the spec as the implementation contract).

All threats are classified CLOSED because: (a) mitigations are documented in the spec content this phase produces; (b) actual runtime enforcement is owned by v14 Build Kernel (Milestone v42+ implementation territory), which inherits these spec contracts as Pydantic-schema fixtures and unit-test corpora.

No SUMMARY.md `## Threat Flags` sections were emitted during execution (no executor-discovered surface). All threats audited are sourced from the four PLAN.md `<threat_model>` blocks.

## Threat Register

### Plan 01 — DEVIATION-RULES.md (DEV-01..07)

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 01-T1 | high | autonomy-bypass | Rule-4 always-stop left as policy check (`if mode != 'full-yolo'`) lets `--full-yolo` mode land an irreversible architectural migration without human gate | CLOSED | `specs/DEVIATION-RULES.md:47` — "**Rule-4 always-stop is STRUCTURAL, not policy.** The implementation guarantee: there is no `if mode == 'full-yolo' bypass` code path. The `log_deviation(rule_id=4)` MCP handler unconditionally renders opencode `question`."; reinforced at `:295` ("there is no autonomy short-circuit code path"); cross-validation step 2 (line 165) enforces `alternatives is not None and len(alternatives) >= 2 and sum(o.recommended for o in alternatives) == 1` before question fires |
| 01-T2 | high | classification-spoofing | Agent self-classifies `rule_id=1` for a schema migration (arch change); harness must catch via pure-machine signal | CLOSED | `specs/DEVIATION-RULES.md:167` — cross-validation step 3 (Rule-4 auto-promotion via `ARCH_PATTERN_ALLOWLIST` scan at `tool.execute.before` write target); mismatch → `state.step.deviation_classification_rejected` with `reason: "arch_pattern_promotion_required"`; allowlist rendered verbatim at `:192` and lives at named single-source-of-truth `state_build/deviation/arch_patterns.py` (`:218`) |
| 01-T3 | high | naming-drift | Past phases (403, 404) drifted into `GSD-*` trailer references; Phase 405 must use `STATE-*` exclusively per project cardinal rule | CLOSED | `specs/DEVIATION-RULES.md:242-272` — "Commit Trailer Convention (STATE-* Naming Discipline)" section naming all four trailers (`STATE-Task`, `STATE-DeviationRule`, `STATE-DeviationAttempt`, `STATE-Subagent-Invocation`); CI grep `grep -nE '\bGSD-' specs/DEVIATION-RULES.md` returns zero (verified) |
| 01-T4 | med | counter-cross-contamination | APG / PRF / DEV chains must remain independent (gsd-2 `loop-control.md` Correction 1); shared rollup would auto-escalate prematurely | CLOSED | `specs/DEVIATION-RULES.md:11,398-404` — three-counter independence subsection: "Cross-module imports are forbidden by CI lint. Each counter has its own event-store query, its own per-tuple key, and its own escalation verdict. The umbrella event (HRN-05) is the ONLY shared touch-point and lives in `state_build/harness/intervention.py` (Phase 406 territory)." |
| 01-T5 | med | signature-nondeterminism | If `issue_signature` hashed full stack traces, different OS / Python builds compute different hashes for the same logical failure → counter cross-contamination | CLOSED | `specs/DEVIATION-RULES.md:121` — `issue_signature` SHA-256 16-char hex over `(task_id, rule_id, error_kind, file:line, matched_token)` tuple — all deterministic across hosts; whole-stack hashing not part of input set; daemon recomputes for verification (cross-validation step 1, line 163) |
| 01-T6 | med | replay-determinism | Append-only mutation of `Deviation.resolution` must preserve replay determinism (single-row state changes via events) | CLOSED | `specs/DEVIATION-RULES.md:477` — "**Single-mutable-row pattern.** The `Deviation` row's `resolution` field starts as `pending` at `deviation_logged` time; mutates to a terminal value via an append-only `deviation_resolution_recorded` event. The projector applies these events in event-store seq order; the latest `deviation_resolution_recorded.resolution` for a given `deviation_event_id` wins. **Replay determinism preserved** — never edited in-place; the event store is authoritative." |
| 01-T7 | low | atomic-write-race | `## Deviations` SUMMARY temp+rename atomic-write race (read cache invalidation could lag) | CLOSED | `specs/DEVIATION-RULES.md:496` — "Atomic write via temp+rename (acknowledged as not-yet-atomic per Phase 402 §7.3 note for `last-snapshot.md`; v44 follow-up applies)" — explicit forward-pointer to v44 follow-up; mirrors Phase 404 N-VERIFICATION.md projector pattern |
| 01-T8 | low | mode-isolation | Build-only spec must not leak into Teach mode | CLOSED | `specs/DEVIATION-RULES.md:6` — `> **Build-mode only.** state.build.* MUST NOT import state.teach.*`; module path `state_build/deviation/` enforced; CI import-graph lint; events under `BUILD_ONLY_EVENT_PREFIXES` |

### Plan 02 — SUBAGENT-MANAGEMENT.md (SUB-01..04)

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 02-T1 | high | whitelist-bypass | Slice frontmatter `allowed_subagents` could expand beyond `STAGE_ROSTER[current_stage]` and spawn an unauthorized subagent type | CLOSED | `specs/SUBAGENT-MANAGEMENT.md:184,222-228` — TWO-GATE enforcement: Gate 1 plan-validation (`set(frontmatter) ⊆ STAGE_ROSTER[stage]` via N-VALIDATION.md machinery); Gate 2 runtime `tool.execute.before` per-entry verification; "Diverges from gsd-2's single-gate runtime-only model (`precedence-divergence-by-trust-model.md` defense-in-depth pole)" |
| 02-T2 | high | grandchild-fanout | Child subagent dispatching 20 grandchildren → `parallel_cap^2 = 400` worst-case process count | CLOSED | `specs/SUBAGENT-MANAGEMENT.md:318` — "Child-of-child (grandchild) accounting" subsection: "**Rejected for v1.** Subagents are spawned in fresh opencode sessions; their own `task` tool invocations are managed by opencode, not state-daemon… **Risk:** `parallel_cap^2 = 400` worst-case process count if every child fans out 20 grandchildren. Documented as known limitation; revisit if real workloads show concurrency-storm patterns." |
| 02-T3 | med | whitelist-drift | Plan-validation could use an outdated STAGE_ROSTER snapshot diverging from runtime | CLOSED | `specs/SUBAGENT-MANAGEMENT.md:125` — single-source-of-truth module `state_build/subagents/types.py` exports `STAGE_ROSTER` as module-level constant; both gates import the same constant; computed-derived-state (`frozenset[SubagentType]`), not stored |
| 02-T4 | med | exhaustiveness-gap | Future patch adds SubagentType Literal value but forgets STAGE_ROSTER entry → runtime fail-open or fail-loud unpredictably | CLOSED | `specs/SUBAGENT-MANAGEMENT.md:141-170` — Compile-Time Exhaustiveness via `assert_never` section; "CI MUST run `mypy --strict src/state_build/subagents/` (and `pyright --warnings`) on every PR"; same pattern guards `SUBAGENT_RETURN_REGISTRY` (Plan 03) |
| 02-T5 | med | mode-validator-bypass | Pydantic root validator missing edge case (e.g., `single` and `parallel` both set) → dispatcher nondeterministic | CLOSED | `specs/SUBAGENT-MANAGEMENT.md:63-66` — exactly-one-mode root validator with verbatim predicate `sum(1 for x in (single, parallel, chain) if x is not None) == 1`; cites gsd-2's mode resolution at `subagent/index.ts:709-720`; Pydantic-level rejection at parse time (line 250) |
| 02-T6 | high | naming-drift | Trailer must be `STATE-Subagent-Invocation:`, not `GSD-*` | CLOSED | `specs/SUBAGENT-MANAGEMENT.md` — verbatim `STATE-Subagent-Invocation:` trailer named at line 8 (header) and forward-references DEVIATION-RULES.md §5; CI grep `grep -nE '\bGSD-' specs/SUBAGENT-MANAGEMENT.md` returns zero (verified) |
| 02-T7 | low | fifo-starvation | 20 slow subagents block FIFO queue of 100 fast follow-ups → latency-sensitive work starves | CLOSED | `specs/SUBAGENT-MANAGEMENT.md` Section 6 — "FIFO queue semantics" subsection: "Latency-sensitive priority queuing is **deferred to post-v17** — FIFO is the v1 invariant for simplicity and determinism. Known limitation: 20 slow subagents can starve a queue of 100 fast follow-ups; if observed, planner adds a priority field…" |
| 02-T8 | low | mode-isolation | Build-only spec | CLOSED | `specs/SUBAGENT-MANAGEMENT.md:7,178` — explicit "Build-mode only" header; `state_build/subagents/types.py MUST NOT import from state_teach/`; CI import-graph lint; events live in `BUILD_ONLY_EVENT_PREFIXES` |

### Plan 03 — SUBAGENT-MONITORING.md (SUB-05..09)

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 03-T1 | high | aggregate-corruption | Agent-emitted `overall_success: true` could trivially bypass layer-3 (artifact existence) spot-check failures | CLOSED | `specs/SUBAGENT-MONITORING.md:252-254` — "**The harness recomputes `overall_success` from layer verdicts; agent-emitted aggregates are rejected.** Mirrors gsd-2's `server-recomputation-of-llm-emitted-fields.md` pattern + Phase 404 PRF `overall_passed` recomputation. The subagent's structured return SHALL NOT include an `overall_success` field; if present, it is ignored (Pydantic `extra='forbid'` rejects at parse time)." |
| 03-T2 | high | counter-evasion | Per-`invocation_id` counter scope lets agent reset 3-restart budget via prompt variation | CLOSED | `specs/SUBAGENT-MONITORING.md:322` — "**Per-`(parent_task_id, subagent_type)` tuple.** Diverges from per-`invocation_id` because the agent should not get a fresh 3-restart budget by re-invoking the same subagent type with a slightly different prompt for the same logical work unit. Mirrors Phase 404's per-`(task_id, check_id)` strike discipline." |
| 03-T3 | high | orphan-persistence | Slice closes with in-flight subagents and daemon never reconciles → worktree merge before subagent commits land | CLOSED | `specs/SUBAGENT-MONITORING.md` Section 7 — 6-step orphan reconciliation flow runs on daemon resume AND at Slice-close gate; `subagent_orphan_detected` event fired (line 28 registered); persistent orphans escalate to Rule 4 with pre-authored alternatives `[abort_slice, retry_subagent, manual_resolve]` (line 445); cross-references DEVIATION-RULES.md Rule 4 always-stop |
| 03-T4 | med | hash-collision | SHA-256 collision in ArtifactDeclaration (theoretical) | CLOSED | `specs/SUBAGENT-MONITORING.md:278` — "SHA-256 is the canonical algorithm — not MD5, not SHA-1, not BLAKE2…(1) SHA-256 is collision-resistant under adversarial conditions, which matters because a malicious or hallucinating subagent could otherwise emit a hash matching a benign file while the actual artifact differs; (2) SHA-256 is the same algorithm used by git's content-addressable-store"; intentional-collision out-of-scope for v1 |
| 03-T5 | med | false-positive-crash | `sse_silence` 180s threshold may flag legitimate long-running work as crashed | CLOSED | `specs/SUBAGENT-MONITORING.md:296` — "no `subagent_progress` SSE event received for > `progress_timeout_s` (default 180s, configurable via Slice frontmatter `subagent: {progress_timeout_s: int}`)"; planner-tunable per Slice; default documented as starter value |
| 03-T6 | high | autonomy-bypass-inheritance | Per-dispatch autonomy override could silently propagate Rule-4-bypass to grandchildren | CLOSED | `specs/SUBAGENT-MONITORING.md:484,489-491` — per-dispatch override allowed (stricter or looser per DEV-06 policy, narrowing-only does NOT apply because autonomy is policy not capability); "Rule-4 always-stop preservation" subsection: "**Rule 4 always-stop is preserved across inheritance.** Even if a grandchild's effective autonomy is `--full-yolo`, a `log_deviation(rule_id=4)` from the grandchild still synchronously renders opencode `question` (DEVIATION-RULES.md Section 2 structural-not-policy guarantee)." |
| 03-T7 | med | naming-drift | `STATE-Subagent-Invocation:` trailer mandatory inside subagent sessions; no `GSD-*` references allowed | CLOSED | `specs/SUBAGENT-MONITORING.md` — trailer named verbatim; forward-references DEVIATION-RULES.md §5 single-source-of-truth module `state_build/commit/trailers.py`; CI grep `grep -nE '\bGSD-' specs/SUBAGENT-MONITORING.md` returns zero (verified) |
| 03-T8 | low | mode-isolation | Build-only spec | CLOSED | `specs/SUBAGENT-MONITORING.md:9,274` — `> **Build-mode only.**` header; `state_build/subagents/` is a Build-mode package; imports from `state_teach/` forbidden by cardinal mode-isolation rule; all eight new event types live under `BUILD_ONLY_EVENT_PREFIXES`; CI import-graph lint `python -m state.tools.import_lint --mode build` |

### Plan 04 — Event / Catalog / Frontmatter Amendments (DEV-07 + SUB-05..09 registration)

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 04-T1 | high | append-only-violation | Plan 04 edits v40 original content or prior v41 amendment blocks → audit-trail determinism broken | CLOSED | All three files verified: `EVENT-TAXONOMY.md` line 1 `# Event Taxonomy` header preserved; prior amendments at lines 199 (Phase 402), 239 (Phase 403), 285 (Phase 404) all retained before Phase 405 amendment at line 352. `ARTIFACT-CATALOG.md` Phase 402 (line 796) + Phase 404 (line 810) amendments preserved; Phase 405 block at line 853. `FRONTMATTER-SCHEMAS.md` Phase 405 block at line 307 — first v41 amendment (no prior to preserve, consistent with Plan 04's stated precondition) |
| 04-T2 | high | event-naming-drift | New event type fails `^state\.(step\|slice)\.[a-z_]+$` → replay parsers fail at load | CLOSED | All 14 events extracted from Phase 405 amendment block in EVENT-TAXONOMY.md match the regex: `state.step.deviation_logged`, `state.step.deviation_classification_rejected`, `state.step.deviation_resolution_recorded`, `state.step.deviation_cap_exceeded`, `state.step.subagent_started`, `state.step.subagent_progress`, `state.step.subagent_complete`, `state.step.subagent_spot_check_failed`, `state.step.subagent_crash_detected`, `state.step.subagent_restart`, `state.step.subagent_restart_exhausted`, `state.step.subagent_orphan_detected`, `state.step.subagent_whitelist_violation`, `state.slice.subagent_cap_expansion_rejected` |
| 04-T3 | high | naming-drift-in-amendment | Amendment uses `GSD-*` in trailer examples or event-payload field cites → perpetuates past-phase drift | CLOSED | `awk '/## v41 Amendment — Phase 405/,0'` over each of the three amended v40 files returns zero `\bGSD-` matches (verified); STATE-* trailers (`STATE-Task`, `STATE-DeviationRule`, `STATE-DeviationAttempt`, `STATE-Subagent-Invocation`) named explicitly in EVENT-TAXONOMY.md Phase 405 amendment header |
| 04-T4 | med | forward-pointer-drift | Amendment cites wrong path (e.g., `phases/405/DEVIATION-RULES.md` missing `specs/`) → readers cannot navigate | CLOSED | All forward-pointers in Phase 405 amendment tables use explicit `specs/` subdirectory pattern matching Phase 405 Plans 01-03 output paths (`DEVIATION-RULES.md §N`, `SUBAGENT-MANAGEMENT.md §N`, `SUBAGENT-MONITORING.md §N`); ARTIFACT-CATALOG.md amendment module paths match the verified files-on-disk |
| 04-T5 | med | mode-isolation-drift | Amendment text mentions teach-mode event emission | CLOSED | Phase 405 amendment preambles in all three files explicitly state Build-mode only with no `state.teach.*` analogs. The only `state.teach.*` / `state_teach/` references inside the Phase 405 blocks are negative disclaimers ("No `state.teach.*` analog exists; teach-mode harness owns its own event family (v47 territory)"; "CI import-graph lint enforces no `state_teach/` imports") — these are mitigation prose, not violations |
| 04-T6 | low | table-column-drift | Column count or names differ from Phase 404's amendment → audit tooling that parses tables breaks | CLOSED | EVENT-TAXONOMY.md Phase 405 amendment uses verbatim 4-column shape `\| Event Type \| Trigger \| State Transition \| Owning REQ →`. ARTIFACT-CATALOG.md Phase 405 amendment uses verbatim 5-column shape `\| Filename / Module Path \| Producer Stage \| Schema Owner (spec doc) \| Immutability \| Description \|` mirroring Phase 404 precedent |

## Summary

| Severity | Total | Closed | Open |
|----------|-------|--------|------|
| High | 14 | 14 | 0 |
| Med | 11 | 11 | 0 |
| Low | 4 | 4 | 0 |
| **Total** | **29** | **29** | **0** |

`threats_open: 0` — phase is THREAT-SECURE.

## Accepted Risks Log

(none — all threats CLOSED via specified mitigations in the produced spec content or via append-only invariant verification; no risk acceptance required)

## v14 Inheritance Contract

The following spec-text mitigations create implementation contracts for v14 Build Kernel:

| Contract | Site | v14 enforcement point |
|----------|------|----------------------|
| No `if mode == 'full-yolo' bypass` branch in Rule-4 handler | DEVIATION-RULES.md §2 (line 47) + §6 (line 295) | Code review + CI grep `! grep -qE 'full[_-]yolo.*bypass' state_build/deviation/log_deviation.py` |
| `ARCH_PATTERN_ALLOWLIST` single-source-of-truth | DEVIATION-RULES.md §5 (line 218) | Module `state_build/deviation/arch_patterns.py`; CI lint rejects allowlist edits via other paths |
| `issue_signature` deterministic inputs (no stack traces) | DEVIATION-RULES.md §7 | Daemon recomputes server-side; rejects on disagreement |
| Append-only `Deviation.resolution` mutation pattern | DEVIATION-RULES.md §10 (line 477) | Projector applies events in event-store seq order |
| Three-counter independence (APG / PRF / DEV) | DEVIATION-RULES.md §8 (line 398) | Cross-module imports forbidden by CI lint; HRN-05 is sole rollup |
| Pydantic `extra="forbid"` on every event / dispatch payload | All three Phase 405 specs | Pydantic parser at MCP-tool-handler boundary |
| Exactly-one-mode root validator | SUBAGENT-MANAGEMENT.md §2 (line 63) | Pydantic-level rejection at parse time |
| `assert_never` exhaustiveness for SubagentType | SUBAGENT-MANAGEMENT.md §4 | `mypy --strict src/state_build/subagents/` + `pyright --warnings` on every PR |
| Two-gate whitelist enforcement (plan-validation + runtime) | SUBAGENT-MANAGEMENT.md §5 | Gate 1 in `state_build/validators/subagent_whitelist.py`; Gate 2 in daemon `tool.execute.before` middleware |
| 20-cap FIFO daemon semaphore | SUBAGENT-MANAGEMENT.md §6 | `state_build/subagents/parallel_cap.py` `acquire_slot()` / `release_slot()`; per-`parent_task_id` scope |
| Server-side recomputation of `overall_success` | SUBAGENT-MONITORING.md §4 (line 252) | Harness derives from layer verdicts; Pydantic `extra='forbid'` rejects agent-emitted aggregate |
| Per-`(parent_task_id, subagent_type)` restart-counter scope | SUBAGENT-MONITORING.md §5 (line 322) | Projector enforces tuple scope at event-store write time |
| 6-step orphan reconciliation on daemon resume + Slice-close | SUBAGENT-MONITORING.md §7 | `state_build/subagents/orphan_reconcile.py` |
| Rule-4 always-stop preservation across autonomy inheritance | SUBAGENT-MONITORING.md §8 (line 489) | `log_deviation(rule_id=4)` synchronously renders opencode `question` regardless of inherited autonomy |
| Append-only `<discovered_threats>` carve-out | All four PLAN.md files | PAP-05 immutability matrix exempts this sub-block |

v14 inherits this contract as Pydantic-schema fixtures and unit-test corpora — the Phase 405 spec docs are the single source of truth.

## Audit Trail

### Audit 2026-05-11
| Metric | Count |
|--------|-------|
| Threats found | 29 |
| Closed (mitigation in spec) | 29 |
| Closed (accepted risk) | 0 |
| Open | 0 |

Phase 405 design-only — runtime enforcement deferred to v14 Build Kernel. All threats have written mitigations in the produced spec docs (DEVIATION-RULES.md, SUBAGENT-MANAGEMENT.md, SUBAGENT-MONITORING.md) or are verified by the append-only invariant of the v40 master-spec amendments (EVENT-TAXONOMY.md, ARTIFACT-CATALOG.md, FRONTMATTER-SCHEMAS.md). Naming-discipline check: zero `\bGSD-` matches in any of the Phase 405 spec docs or Phase 405 amendment blocks. Event-naming-regex check: all 14 new event types match `^state\.(step|slice)\.[a-z_]+$`. Mode-isolation check: zero `state.teach.*` event emissions; the only teach-mode mentions in Phase 405 are negative-disclaimer mitigation prose. No accepted risks. No escalations. Gate: PASS.
