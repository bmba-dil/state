---
phase: 405-deviation-rules-and-subagent-management
phase_name: Deviation Rules & Subagent Management
verified: 2026-05-11
status: passed
phase_type: design-only
must_haves_total: 5
must_haves_verified: 5
score: 5/5 success criteria verified; 16/16 REQ-IDs covered; 3/3 produced specs + 3/3 amended v40 specs pass levels 1-3
re_verification: null
gaps: []
human_verification: []
---

# Phase 405: Deviation Rules & Subagent Management — Verification Report

**Phase Goal (ROADMAP.md §Phase 405):** The 4-rule deviation framework with tiered autonomy is fully specified, and the subagent management protocol (whitelist, parallel fanout, structured returns, crash recovery) is specified as a complete control-plane subsystem.

**Verified:** 2026-05-11
**Status:** passed
**Phase type:** DESIGN-ONLY (3 canonical sibling specs + amendments to 3 v40 master registries; no source code lands — runtime owned by v14 Build Kernel)
**Re-verification:** No — initial verification
**Verification mode:** Goal-backward against ROADMAP.md success criteria; spec-content grep verification (line counts, section headers, Pydantic class identifiers, requirement coverage).

## Verdict

All 5 ROADMAP success criteria substantively satisfied. All 16 declared REQ-IDs (DEV-01..07, SUB-01..09) map to substantive Pydantic-typed content in the owning spec files. The append-only invariant on v40 master spec amendments is mathematically verified (127 insertions, 0 deletions across EVENT-TAXONOMY.md, ARTIFACT-CATALOG.md, FRONTMATTER-SCHEMAS.md). Naming-discipline rule (no `GSD-` literal trailer prefix) holds across all 6 affected files. A v14 Build Kernel implementer reading DEVIATION-RULES.md + SUBAGENT-MANAGEMENT.md + SUBAGENT-MONITORING.md can implement the deviation framework + subagent control-plane subsystem without re-asking design questions.

## Success Criteria

### SC-1 — DEVIATION-RULES.md defines all four rules (DEV-01..DEV-04) with category, max-attempts, commit-prefix, escalation path; Rule 4 always-human-gate

| Check | Status | Evidence |
|---|---|---|
| Spec exists at `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md` | ✓ | 614 lines |
| H2 section per rule (Rule 1..Rule 4) | ✓ | `^## Rule [1234]` matches at lines 19, 26, 33, 40 |
| `max-attempts: 3` cap for Rules 1–3, `max-attempts: 1` for Rule 4 | ✓ | Rule 1 line 22, Rule 2 line 29, Rule 3 line 36, Rule 4 line 43 (single-shot) |
| Commit-prefix convention named per rule | ✓ | `fix:` (Rule 1), `feat:`/`fix:` keyword inference (Rule 2), `refactor:` (Rule 3), `feat:`/`refactor:` (Rule 4); STATE-DeviationRule trailer × 11 |
| Rule 4 always-human-gate via opencode `question` tool, never auto-approved under `--full-yolo`, structural-not-policy | ✓ | Line 45 "ALWAYS human gate via opencode `question` tool"; line 47 "no `if mode == 'full-yolo' bypass`"; "STRUCTURAL, not policy" rendered |
| `## Deviations` SUMMARY section auto-rendered | ✓ | H2 §"## Deviations SUMMARY Section Projector" at line 487; 8-column markdown schema rendered; sample at line 530 |
| `log_deviation` MCP tool with Pydantic-typed signature | ✓ | H2 §"log_deviation MCP Tool" at line 75; 24 references; Pydantic `Rule4Option`, `DeviationLogResult` rendered with `extra="forbid"` |

### SC-2 — Tiered autonomy table (DEV-05) + per-Slice autonomy override (DEV-06)

| Check | Status | Evidence |
|---|---|---|
| Three-mode autonomy table | ✓ | DEVIATION-RULES.md lines 291–293: `--tiered` (default) / `--full-yolo` / `--conservative` rows × 4 columns (`human-verify`, `decision`, `human-action`, Rule 4) |
| Rule 4 always-stop in all three modes (4th column) | ✓ | All 3 rows show **stop** bolded in the Rule 4 column (lines 291, 292, 293) |
| Per-Slice autonomy override frontmatter field | ✓ | Line 299: `autonomy: Literal["tiered","full-yolo","conservative"] \| None = None` |
| Precedence rule (Slice override beats milestone default) | ✓ | Line 300: "milestone default -> Slice override -> done"; resolution example lines 305–312 |
| Narrowing-only does NOT apply to autonomy (policy, not capability) | ✓ | Line 301: "**Narrowing-only does NOT apply to autonomy** — autonomy is policy, not capability" |

### SC-3 — Deviation event schema (DEV-07) + ## Deviations SUMMARY projector

| Check | Status | Evidence |
|---|---|---|
| `Deviation` Pydantic payload with `rule_id`, `fix_attempt_count`, `resolution` | ✓ | H2 §"Deviation Event Payload" at line 408; 14-field Pydantic class with `Literal[1, 2, 3, 4]` rule_id discriminator and `extra="forbid"` |
| Four `state.step.deviation_*` event types defined | ✓ | `deviation_logged` ×10, `deviation_classification_rejected` ×5, `deviation_resolution_recorded` ×7, `deviation_cap_exceeded` ×6 (occurrences in spec) |
| Append-only `deviation_resolution_recorded` mutation pattern | ✓ | Section 9 documents single-mutable-row pattern with rejection rationale for two-event-split alternative |
| `## Deviations` SUMMARY projector algorithm specified | ✓ | H2 §"## Deviations SUMMARY Section Projector" at line 487; 6-step algorithm + 8-column schema + worked example |
| `issue_signature` derivation (per-tuple counter scope) | ✓ | H2 §"issue_signature Derivation" at line 317; `compute_issue_signature` function rendered verbatim (SHA-256 16-char hex of `error_kind\|file_path\|line_no\|matched_token`) |

### SC-4 — SUBAGENT-MANAGEMENT.md defines typed-spawn (SUB-01), whitelist (SUB-02), narrowing-only override (SUB-03), 20-default parallel cap (SUB-04)

| Check | Status | Evidence |
|---|---|---|
| Spec exists at `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md` | ✓ | 453 lines (≥450 target) |
| `dispatch_subagent` MCP tool with three Pydantic modes (single/parallel/chain) | ✓ | H2 §"dispatch_subagent MCP Tool" at line 20; `DispatchSubagent` + `SingleDispatch` + `ParallelDispatch` + `ChainDispatch` rendered with `model_config = ConfigDict(extra="forbid")`; exactly-one-mode root validator predicate documented |
| 14-member `SubagentType` Literal + 4-roster `STAGE_ROSTER` | ✓ | H2 §"SubagentType Whitelist (SUB-02)" at line 85; 14 named types organized into 4 stage frozensets; `researcher` dual-listed in discuss-slice + plan-slice rosters per SUB-02 verbatim |
| Narrowing-only frontmatter override `allowed_subagents` with two-gate enforcement | ✓ | H2 §"Static Whitelist Enforcement + Narrowing-Only Override (SUB-03)" at line 182; 5-step protocol rendered; plan-validation Gate 1 + runtime `tool.execute.before` Gate 2; `subagent_whitelist_violation` event payload |
| 20-default parallel cap + daemon-side FIFO semaphore | ✓ | H2 §"Parallel Cap Accounting (SUB-04)" at line 271; `MAX_PARALLEL_CAP_DEFAULT = 20` ×6; FIFO ×9; per-Slice `subagent.parallel_cap` narrowing-only override; grandchild deferral with `parallel_cap^2 = 400` risk acknowledged |
| Compile-time exhaustiveness via `assert_never` | ✓ | H2 §"Compile-Time Exhaustiveness via assert_never" at line 141; 14-case match pattern rendered |

### SC-5 — Subagent monitoring (SUB-05..SUB-09): SSE events, structured return + spot-check, crash recovery, task_id survival, autonomy inheritance

| Check | Status | Evidence |
|---|---|---|
| Spec exists at `.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md` | ✓ | 653 lines |
| SSE event family linked by parent `task_id` (SUB-05) | ✓ | H2 §"SSE Event Family (SUB-05)" at line 32; `SubagentStarted` + `SubagentProgress` + `SubagentComplete` Pydantic payloads; `parent_task_id` × 21 |
| `SUBAGENT_RETURN_REGISTRY` + 4-layer spot-check (SUB-06) | ✓ | H2 §"SUBAGENT_RETURN_REGISTRY (SUB-06)" at line 111; H2 §"4-Layer Pure-Machine Spot-Check (SUB-06)" at line 215; `ArtifactDeclaration` + `SubagentReturnBase` + per-stage modules |
| 5-source crash taxonomy + 3-restart counter + `<prior_crash>` continuation (SUB-07) | ✓ | H2 §"5-Source Crash Taxonomy + 3-Restart Counter (SUB-07)" at line 283; `process_exit` + `sse_silence` + `parent_task_error` + `stop_reason` + `spot_check` sources documented; H2 §"<prior_crash> Continuation Context" at line 362 |
| `task_id` survival across compaction + Slice-boundary respawn (SUB-08) | ✓ | H2 §"task_id Survival + Daemon-Down Orphan Reconciliation (SUB-08)" at line 407; `CompactionSnapshot` extension fields (`subagent_restart_counters` + `in_flight_subagents`); 6-step orphan reconciliation flow |
| Autonomy inheritance from parent Slice (SUB-09) | ✓ | H2 §"Autonomy Inheritance from Parent Slice (SUB-09)" at line 475; 3-step flow + Rule-4 always-stop preservation + grandchild recursion |
| 8 new `state.step.subagent_*` events registered | ✓ | Plan 04 registers 8 events in v40 EVENT-TAXONOMY.md amendment block (subagent_started, _progress, _complete, _spot_check_failed, _crash_detected, _restart, _restart_exhausted, _orphan_detected) |

**Score:** 5/5 success criteria verified.

## Requirement Coverage

| REQ-ID | Source Plan | Description (REQUIREMENTS.md) | Status | Evidence |
|---|---|---|---|---|
| DEV-01 | 405-01 | Rule 1 — auto-fix bugs, max 3 attempts, `fix:` prefix, escalate to Rule 4 | ✓ SATISFIED | DEVIATION-RULES.md §"Rule 1: Auto-fix Bugs (DEV-01)" line 19 |
| DEV-02 | 405-01 | Rule 2 — auto-add critical functionality with `## Deviations` SUMMARY section | ✓ SATISFIED | DEVIATION-RULES.md §"Rule 2: Auto-add Critical Functionality (DEV-02)" line 26 + §"## Deviations SUMMARY Section Projector" line 487 |
| DEV-03 | 405-01 | Rule 3 — auto-fix blocking issues with `checkpoint:decision` escalation | ✓ SATISFIED | DEVIATION-RULES.md §"Rule 3: Auto-fix Blocking Issues (DEV-03)" line 33; checkpoint:decision escalation documented in inter-rule promotion graph |
| DEV-04 | 405-01 | Rule 4 — architectural changes, always-human-gate via opencode `question` tool, never auto-approved | ✓ SATISFIED | DEVIATION-RULES.md §"Rule 4: Architectural Changes (DEV-04)" line 40; "STRUCTURAL, not policy" rendered at line 47 |
| DEV-05 | 405-01 | Tiered autonomy (`--tiered`/`--full-yolo`/`--conservative`) per checkpoint type | ✓ SATISFIED | DEVIATION-RULES.md §"Tiered Autonomy (DEV-05, DEV-06)" line 283; 3-row × 4-column autonomy table at lines 291–293 |
| DEV-06 | 405-01 | Per-Slice autonomy override via Slice frontmatter `autonomy` field | ✓ SATISFIED | DEVIATION-RULES.md §"Per-Slice override (DEV-06)" line 297; `autonomy: Literal["tiered","full-yolo","conservative"] \| None` at line 299 |
| DEV-07 | 405-01 | `deviation` event schema + SUMMARY.md `## Deviations` section algorithm | ✓ SATISFIED | DEVIATION-RULES.md §"Deviation Event Payload" line 408 + §"## Deviations SUMMARY Section Projector" line 487 |
| SUB-01 | 405-02 | `dispatch_subagent` MCP tool wrapping opencode `task` with explicit `subagent_type` | ✓ SATISFIED | SUBAGENT-MANAGEMENT.md §"dispatch_subagent MCP Tool (SUB-01)" line 20 |
| SUB-02 | 405-02 | Static whitelist per Slice stage (discuss/plan/execute/verify rosters) | ✓ SATISFIED | SUBAGENT-MANAGEMENT.md §"SubagentType Whitelist (SUB-02)" line 85; 14 named types organized into 4 stage frozensets |
| SUB-03 | 405-02 | Narrowing-only frontmatter override `allowed_subagents` | ✓ SATISFIED | SUBAGENT-MANAGEMENT.md §"Static Whitelist Enforcement + Narrowing-Only Override (SUB-03)" line 182; 5-step protocol + two-gate enforcement |
| SUB-04 | 405-02 | 20-default parallel cap, near-uncapped fanout encouraged | ✓ SATISFIED | SUBAGENT-MANAGEMENT.md §"Parallel Cap Accounting (SUB-04)" line 271; 20-cap rationale + daemon-side FIFO semaphore + per-Slice narrowing override |
| SUB-05 | 405-03 | SSE events linked by parent `task_id` (`subagent_started`/`_progress`/`_complete`) | ✓ SATISFIED | SUBAGENT-MONITORING.md §"SSE Event Family (SUB-05)" line 32; three Pydantic event payloads + parent linkage discipline |
| SUB-06 | 405-03 | Structured return per subagent_type + 4-layer artifact/commit spot-check | ✓ SATISFIED | SUBAGENT-MONITORING.md §"SUBAGENT_RETURN_REGISTRY (SUB-06)" line 111 + §"4-Layer Pure-Machine Spot-Check (SUB-06)" line 215 |
| SUB-07 | 405-03 | 3-restart crash-recovery with `subagent_restart` event | ✓ SATISFIED | SUBAGENT-MONITORING.md §"5-Source Crash Taxonomy + 3-Restart Counter (SUB-07)" line 283 + §"<prior_crash> Continuation Context" line 362 |
| SUB-08 | 405-03 | `task_id` survival across compaction + Slice-boundary spawn (cross-refs CTX-07) | ✓ SATISFIED | SUBAGENT-MONITORING.md §"task_id Survival + Daemon-Down Orphan Reconciliation (SUB-08)" line 407; `CompactionSnapshot` extension + 6-step orphan reconciliation |
| SUB-09 | 405-03 | Subagents inherit parent Slice's autonomy level | ✓ SATISFIED | SUBAGENT-MONITORING.md §"Autonomy Inheritance from Parent Slice (SUB-09)" line 475; 3-step flow + Rule-4 always-stop preservation + grandchild recursion rule |

**Orphaned requirements check:** None. REQUIREMENTS.md maps DEV-01..07 and SUB-01..09 (16 IDs) to Phase 405; all 16 are covered by the declared plans' `requirements` fields and have substantive content in the produced specs.

## Spec File Inventory

| File | Plan | Required min_lines | Actual | Exists | Substantive | Wired (cross-refs) | Status |
|---|---|---|---|---|---|---|---|
| `.planning/milestones/v41/phases/405/specs/DEVIATION-RULES.md` | 405-01 | 600 | 614 | ✓ | ✓ (14 H2 sections; all 7 DEV REQ-IDs verbatim-cited; Pydantic classes `extra="forbid"` ×5; 11 STATE-DeviationRule trailer references) | Cited by SUBAGENT-MANAGEMENT.md (Section 7) + SUBAGENT-MONITORING.md (Section 8) + v40 EVENT-TAXONOMY amendment | ✓ VERIFIED |
| `.planning/milestones/v41/phases/405/specs/SUBAGENT-MANAGEMENT.md` | 405-02 | 450 | 453 | ✓ | ✓ (7 H2 sections; all 4 SUB-01..04 REQ-IDs verbatim-cited; Pydantic classes for DispatchSubagent + 3 mode payloads; STAGE_ROSTER 4-key frozenset; 20-cap + FIFO semaphore) | Cited by SUBAGENT-MONITORING.md (Section 1 sibling cross-ref) + v40 EVENT-TAXONOMY amendment + v40 ARTIFACT-CATALOG amendment + v40 FRONTMATTER-SCHEMAS amendment | ✓ VERIFIED |
| `.planning/milestones/v41/phases/405/specs/SUBAGENT-MONITORING.md` | 405-03 | 650 | 653 | ✓ | ✓ (8 H2 sections + 5 appendices; all 5 SUB-05..09 REQ-IDs verbatim-cited; 8 Pydantic event payloads; SUBAGENT_RETURN_REGISTRY; CompactionSnapshot extension; 6-step orphan reconciliation flow) | Cited by v40 EVENT-TAXONOMY amendment (8 of 14 new events owned here) + v40 ARTIFACT-CATALOG amendment (7 of 13 new modules owned here) | ✓ VERIFIED |
| `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` | 405-04 | 360 | 391 | ✓ | ✓ (Phase 405 amendment registers 14 new state.{step,slice}.* events at lines 352–391; all event types match `^state\.(step\|slice)\.[a-z_]+$`; Build-mode-only) | Forward-pointers to all 3 Phase 405 sibling specs | ✓ VERIFIED |
| `.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` | 405-04 | 870 | 893 | ✓ | ✓ (Phase 405 amendment registers 13 new state_build/* modules + CompactionSnapshot extension + stepNSUMMARY `## Deviations` section at lines 853–893) | Forward-pointers to DEVIATION-RULES.md + SUBAGENT-MANAGEMENT.md + SUBAGENT-MONITORING.md | ✓ VERIFIED |
| `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` | 405-04 | 230 | 343 | ✓ | ✓ (first v41 amendment landed in this plan; registers 3 new SliceFrontmatter fields: `autonomy`, `allowed_subagents`, `subagent` nested) | Forward-pointers to DEVIATION-RULES.md (DEV-06) + SUBAGENT-MANAGEMENT.md (SUB-03 + SUB-04) + SUBAGENT-MONITORING.md (SUB-07) | ✓ VERIFIED |

All 3 produced specs exceed plan-mandated line-count floors. All 3 amended v40 master specs grew strictly by append. All 14 new event types and 13 new module paths are forward-pointer rows; canonical Pydantic schemas + behaviors live in owning Phase 405 sibling specs (authoritative-ordering note rendered in each amendment block).

## Naming-Discipline Verification

Project cardinal rule (CLAUDE.md + MEMORY.md): never use `GSD-` literal trailer prefix in state-project artifacts.

| File | `grep -cE '\bGSD-'` | Status |
|---|---|---|
| DEVIATION-RULES.md | 0 | ✓ PASS |
| SUBAGENT-MANAGEMENT.md | 0 | ✓ PASS |
| SUBAGENT-MONITORING.md | 0 | ✓ PASS |
| EVENT-TAXONOMY.md Phase 405 amendment | 0 | ✓ PASS |
| ARTIFACT-CATALOG.md Phase 405 amendment | 0 | ✓ PASS |
| FRONTMATTER-SCHEMAS.md Phase 405 amendment | 0 | ✓ PASS |

**STATE-* trailer constants confirmed:** DEVIATION-RULES.md uses `STATE-Task`, `STATE-DeviationRule`, `STATE-DeviationAttempt` (11 occurrences); SUBAGENT-MANAGEMENT.md / SUBAGENT-MONITORING.md cross-reference `STATE-Subagent-Invocation` (per DEVIATION-RULES.md §5 trailer-constant ownership).

**Observation (not a violation):** DEVIATION-RULES.md line 237 contains the literal `GSD` (no hyphen) in the phrase "handled by the GSD workflow" — this is a reference to the legacy planning workflow (gsd-2 lineage), not a STATE identifier. Bare `GSD` word is permitted; only the `GSD-` trailer-prefix literal is prohibited.

## Append-Only Invariant Verification

`git diff --numstat` from each v40 master spec's pre-Phase-405-amendment commit to HEAD:

```
43   0   .planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
40   0   .planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
44   0   .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
```

**Total: 127 insertions, 0 deletions across 3 v40 master spec files.** No content in prior amendment blocks (Phase 402, Phase 403, Phase 404) was modified during Phase 405 work.

**Boundary inspection (EVENT-TAXONOMY.md):**
- Phase 402 amendment header at line 199 — byte-identical to pre-Phase-405 state
- Phase 403 amendment header at line 239 — byte-identical
- Phase 404 amendment header at line 285 — byte-identical
- Phase 405 amendment header at line 352 (new, appended after Phase 404 closing line 348)

**Boundary inspection (ARTIFACT-CATALOG.md):**
- Phase 402 amendment header at line 796 — byte-identical
- Phase 404 amendment header at line 810 — byte-identical
- Phase 405 amendment header at line 853 (new, appended after Phase 404 closing line 849)

**Boundary inspection (FRONTMATTER-SCHEMAS.md):**
- v40 design contract closing line preserved
- Phase 405 amendment header at line 307 (first v41 amendment in this file)

The append-only invariant is the load-bearing safety property for v40 master registry evolution; it holds rigorously.

## Anti-Patterns Scan

| Item | Severity | Notes |
|---|---|---|
| TODO / FIXME / placeholder / v1 / simplified / future tokens in specs | ℹ️ INFO | Appearances are intentional spec content (e.g., "v1 invariant", "deferred to post-v17") — these tokens are themselves the subject of Phase 404 SCOPE-PROHIBITION.md PROHIBITED_RE; spec files under `.planning/**/*.md` are exempt via PATH_ALLOWLIST_GLOB. |
| Mode-isolation violation (`state.teach.` references) | ✓ CLEAN | 0 matches in all 6 affected files. All 14 new event types and 13 new module paths live under `state_build/*` / `state.{step,slice}.*` (Build-mode-only). |
| Stub / placeholder spec sections | ✓ CLEAN | All 14 H2 sections in DEVIATION-RULES.md, all 7 in SUBAGENT-MANAGEMENT.md, all 8 in SUBAGENT-MONITORING.md are substantive with verbatim Pydantic / Literal / regex / table content. Line counts exceed minimums (614/600, 453/450, 653/650). |
| GSD- literal trailer prefix | ✓ CLEAN | 0 occurrences across all 6 files (see Naming-Discipline Verification). |

### Step 7b: Quality Findings

Skipped (quality.level: fast for design-only phase; no source code under `src/`, no `.cjs`/`.js`/`.ts` files produced — Step 7b is N/A for markdown-only deliverables).

## Human Verification Required

None. All goal-backward checks for a design-only phase are programmatically verifiable via grep + line-count + `git diff --numstat`. No visual, runtime, or external-service behaviors at stake — this is a spec deliverable consumed by future v14 Build Kernel + v15 Build Core Commands implementers.

## Gaps Summary

No gaps. Every ROADMAP.md success criterion has substantive grep-verifiable content in the owning spec file. Every declared REQ-ID (DEV-01..07, SUB-01..09) is verbatim-cited and supported by Pydantic-typed content in the owning spec. The append-only invariant on v40 master spec amendments holds (127 insertions, 0 deletions). All forward-pointers / sibling cross-references wire correctly:

- DEVIATION-RULES.md ↔ SUBAGENT-MANAGEMENT.md ↔ SUBAGENT-MONITORING.md (mutual sibling cross-refs)
- Phase 405 specs ↔ v40 EVENT-TAXONOMY.md amendment (14 events, owning-spec forward-pointers)
- Phase 405 specs ↔ v40 ARTIFACT-CATALOG.md amendment (13 modules + CompactionSnapshot extension + stepNSUMMARY ## Deviations section)
- Phase 405 specs ↔ v40 FRONTMATTER-SCHEMAS.md amendment (3 new SliceFrontmatter fields)
- Phase 405 specs → Phase 406 forward-pointers (state.harness.intervention umbrella event HRN-05 aggregating Rule-4 escalations + subagent crash/orphan events)
- Phase 405 specs → v14 Build Kernel forward-pointers (8 modules under `state_build/deviation/` + `state_build/subagents/`)
- Phase 405 specs → v15 Build Core Commands forward-pointer (plan-validation Gate 1 narrowing-only check)

**Phase goal is achieved.** A v14 Build Kernel implementer reading DEVIATION-RULES.md + SUBAGENT-MANAGEMENT.md + SUBAGENT-MONITORING.md (with their indexed entries in v40 EVENT-TAXONOMY.md + ARTIFACT-CATALOG.md + FRONTMATTER-SCHEMAS.md) can implement the 4-rule deviation framework (DEV-01..07) and the subagent management control-plane subsystem (SUB-01..09) without re-asking design questions. The structural Rule-4 always-stop invariant has unambiguous enforcement spec (no `if mode == 'full-yolo' bypass` code path in `state_build/deviation/log_deviation.py`; verified by absence-grep). The narrowing-only whitelist override has defense-in-depth two-gate enforcement (plan-validation + runtime `tool.execute.before`). The 20-default parallel cap has daemon-side FIFO semaphore mechanism with derived-from-event-store in-flight counter. The 3-restart crash counter is per-`(parent_task_id, subagent_type)` tuple-scoped, closing the prompt-variation gaming surface. Four-counter independence (APG / PRF / DEV / SUB) is restated across the relevant specs.

---

_Verified: 2026-05-11_
_Verifier: Claude (gsd-verifier)_
