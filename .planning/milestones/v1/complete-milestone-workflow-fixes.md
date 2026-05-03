# Complete-Milestone Workflow Fixes

**Date:** 2026-04-26
**Context:** Milestone v1 (Event Store Foundation) — first milestone using GSD workflows against a milestone-scoped `.planning/` layout at `.planning/milestones/v1/`.

---

## 1. Phase Directory Structure Mismatch (Root Cause)

**The tools assume phases live at `.planning/phases/` but they're at `.planning/milestones/v1/phases/`.**

This is the single biggest source of tool breakage. Every command that globs for phases, plans, or summaries failed silently or returned zero counts.

| Command / Tool | Expected Path | Actual Path | Impact |
|---|---|---|---|
| `phase-plan-index` | `.planning/phases/{phase-dir}/*-PLAN.md` | `.planning/milestones/v1/phases/{phase-dir}/*-PLAN.md` | Returned `plans: []` — zero plans found. Required manual rename + recheck. |
| `init execute-phase` | globs for plans in `.planning/phases/` | same mismatch | Returned `plan_count: 0, incomplete_count: 0` even when files existed. |
| `roadmap analyze --milestone v1` | `.planning/phases/` | same mismatch | Returned `milestones: [], phases: [], phase_count: 0`. Completely useless output. |
| `roadmap get-phase` | reads ROADMAP.md from root | ROADMAP.md exists at `.planning/ROADMAP.md` (monolithic) NOT `.planning/milestones/v1/ROADMAP.md` | Returned `found: false` for phases 008+ even though `init` found them. The tool reads a different ROADMAP file. |
| `milestone complete` | `.planning/phases/` for SUMMARY scanning | same mismatch | Reported `phases: 0, plans: 0, tasks: 0`. Created v1-ROADMAP.md from monolithic root ROADMAP.md (2,734 lines) instead of the milestone-scoped one. |
| `audit-open` | glob `*.planning/phases/*/*-VERIFICATION.md` | VERIFICATION.md files at `.planning/milestones/v1/phases/*/VERIFICATION.md` | Returned zero VERIFICATION.md findings. |

**Fix needed:** The tools need a `--milestone` flag or `milestone_scope` config that redirects all path resolution to `.planning/milestones/{scope}/`. Currently only `init` respects milestone_scope; downstream commands (`phase-plan-index`, `roadmap analyze`, `milestone complete`, `audit-open`, `find-phase`) do not consistently use it.

---

## 2. Decimal Phase Number Handling (010.1)

Phase 010.1 (gap closure) exposed multiple issues with decimal phase numbers:

- **Branch name mangling:** `init execute-phase` returned `branch_name: "gsd/phase-010.1-phase"` instead of `"gsd/phase-010.1-gap-closure"`. The tool extracted `phase` from somewhere instead of the slug.
- **Phase directory matching:** `phase-plan-index "010.1"` returned `plans: []` even though `010.1-A-CLI-Mode-Validation-PLAN.md` existed in the correctly-named directory `010.1-gap-closure/`. The `phaseTokenMatches` function failed to match the normalized decimal against the directory name.
- **Works-in-practice workaround:** I bypassed the tools and executed plans by spawning `gsd-executor` agents directly with explicit plan file paths. This worked but bypassed all tool-based wave/plan discovery.

**Fix needed:** Decimal phase support in `phaseTokenMatches`, `normalizePhaseName`, and branch template resolution.

---

## 3. `gsd-tools.cjs` Unknown Config Keys

Every single tool invocation emitted:
```
gsd-tools: warning: unknown config key(s) in .planning/config.json: quality, concurrent — these will be ignored
```

This repeated 4-5 times per invocation, creating significant noise (appears 20+ times per workflow step).

**Fix needed:** Either add `quality` and `concurrent` as known keys, or suppress unknown key warnings.

---

## 4. Plan File Naming Convention Mismatch

The tools filter plan files with `f.endsWith('-PLAN.md') || f === 'PLAN.md'`. But:

- **gsd-planner agent consistently writes files as `PLAN-{letter}-{Name}.md`** (e.g., `PLAN-A.md`, `PLAN-B.md`, `PLAN-001-Projector-Core.md`).
- These do NOT end with `-PLAN.md` or equal `PLAN.md`. They start with `PLAN-`.
- **Manual rename required every time** across ALL phases: 008 (3 files), 009 (3 files), 010 (4 files), 010.1 (3 files).
- The 010 planner renamed correctly (files were `010-A-*-PLAN.md`). The 008/009 planners wrote `PLAN-*.md` without phase prefix.
- The 010.1 planner returned `## PLANNING COMPLETE` but wrote **zero files to disk**. Had to create them manually.

**Fix needed (two options):**
- Change the planner agent prompt to enforce `{padded_phase}-{plan_id}-PLAN.md` naming, OR
- Change the tool filter to also match `PLAN-*.md` patterns, OR
- Post-process: rename files after planner returns.

---

## 5. SUMMARY.md Frontmatter Inconsistency

The `summary-extract` tool and `complete-milestone` workflow expect SUMMARY.md files to have:
- `one_liner:` field
- `objective:` field
- `requirements_completed:` field

But the executors wrote SUMMARY.md files with:
- `provides:` section (list of deliverables)
- `requires:` section (dependency mapping)
- No `one_liner:` or `objective:` YAML fields

This caused:
- `/gsd summary-extract --fields one_liner` returned nothing for all 17 summaries
- The MILESTONES.md entry showed `(none recorded)` for accomplishments because the `milestone complete` tool couldn't extract one-liners
- Had to manually edit MILESTONES.md to add accomplishments

**Fix needed:** Standardize the SUMMARY.md template that executors follow. Either add `one_liner:` to the template, or have the milestone tool fall back to `provides:`.

---

## 6. Planner Agent Doesn't Write Files to Disk (Silent Failure)

Across multiple phases, the `gsd-planner` agent returned `## PLANNING COMPLETE` with file lists but:

- **Phase 010.1:** Stated "3 plans created" with exact filenames but **zero files existed on disk**. Files had to be created manually from the prompt output.
- **Phase 008:** Files were on disk but named `PLAN-001-*.md` (no `-PLAN.md` suffix).
- **Phase 009:** Files were on disk as `PLAN-A.md`, `PLAN-B.md`, `PLAN-C.md`.

**Pattern:** The planner agent states it used the Write tool but either the tool didn't execute or the path was wrong. The orchestrator never verifies disk writes — it trusts the return signal.

**Fix needed:** After planner returns PLANNING COMPLETE, always verify files exist on disk via `ls {phase_dir}/*-PLAN.md`. If empty, enter filesystem fallback step.

---

## 7. Stale Audit Not Reevaluated After Gap Closure

**Flow that failed:**
1. Ran `/gsd-audit-milestone` → status: `tech_debt` (4 items)
2. Ran `/gsd-plan-milestone-gaps` → created Phase 010.1
3. Planned + executed Phase 010.1 (closed all 4 tech debt items)
4. Ran `/gsd-complete-milestone v1`
5. **The workflow checked the stale `v1-MILESTONE-AUDIT.md`** which still showed `status: tech_debt`
6. Did NOT detect that Phase 010.1 had been created and completed since the audit
7. I had to manually reason that the gaps were closed

**Fix needed:** The complete-milestone pre-flight check should:
- Detect if any gap-closure phases exist and are complete since the last audit
- Offer to re-run audit before completing if gaps were addressed
- Or at minimum flag: "Audit is stale — Phase 010.1 completed since audit was run. Re-audit?"

---

## 8. Executor Completion Signal Inconsistency

Multiple executor agents returned without the expected marker but had done the work:

| Plan | Expected Marker | Actual Return | Work Done? |
|------|----------------|---------------|------------|
| 010-A | `## PLAN COMPLETE` | Procedural description, no marker | ✅ Files created, commits present |
| 010-C | `## PLAN COMPLETE` | "Maximum steps reached" | ✅ Files created, commits present |
| 010-D | `## PLAN COMPLETE` | No marker | ✅ Files created, commits present |

The execute-phase workflow says:
> *"Completion signal fallback: If a spawned agent does not return a completion signal but appears to have finished its work (commits visible, SUMMARY.md exists), treat it as successful."*

This fallback was triggered for every single plan. No executor ever returned the canonical `## PLAN COMPLETE` marker. The orchestrator had to verify via spot-check (check SUMMARY.md exists + commits present) every time.

**Fix needed:** Either fix the executor agent prompt to return the marker, or make the fallback the primary verification path and remove the marker dependency.

---

## 9. Mode / Yolo Config Bypassed Confirmation Gates

The config has `mode: yolo` which triggers `<if mode="yolo">` auto-approvals:

```
⚡ Auto-approved: Milestone scope verification
[Show breakdown summary without prompting]
Proceeding to stats gathering...
```

This skipped the user confirmation at every gate. While intentional (yolo mode), it conflicted with the user's expectation of being prompted. The complete-milestone workflow's `verify_readiness` step has a yolo branch that silently proceeds — the user was never asked to confirm the milestone scope.

**Fix needed:** This is working as designed for yolo mode. No change needed — just understand that yolo bypasses confirmation gates.

---

## 10. `phase complete` Updates Tool State But Not STATE.md Content

The `node gsd-tools.cjs phase complete "N"` command returned `state_updated: true` but:

- The actual `.planning/milestones/v1/STATE.md` file content still showed `Phases complete: 3 / 10` and `Status: planning` (the old pre-migration content).
- The `gsd_state_version: 1.0` frontmatter was updated, but the markdown body was not regenerated.
- This is likely because the tool updates its internal JSON state store but not the human-readable markdown file.

**Fix needed:** Either update the STATE.md markdown content, or clarify that the JSON tool state is authoritative and STATE.md is a human-readable snapshot.

---

## 11. Test Pollution: Global structlog Configuration

Adding CLI tests (Phase 009) broke existing crash-recovery tests because:

1. `conftest.py` was written with module-level `structlog.configure(wrapper_class=CRITICAL)` to suppress ConsoleRenderer output during CliRunner tests.
2. This **globally suppressed all structlog logging to CRITICAL** for the entire process lifetime.
3. The crash-recovery test (`test_seq_crash_recovery.py`) captures structlog output at INFO level to verify `repair_summary` is logged.
4. Because conftest.py set `wrapper_class=CRITICAL` at module level (before any test module imports), the crash-recovery test's `structlog.configure(processors=..., logger_factory=...)` couldn't override it — `wrapper_class` is applied at a different layer.
5. Fixed by: emptying conftest.py, moving suppression into `test_cli.py` at module level, and adding `wrapper_class=logging.DEBUG` to the crash-recovery test's structlog setup.

**Root cause:** structlog's `wrapper_class` and `processors` are independent configuration axes. `configure(wrapper_class=CRITICAL)` cannot be overridden by a subsequent `configure(processors=...)`. This is a structlog API design trap.

---

## 12. `.example()` Banned by Modern Hypothesis

Three plans (010-B, 010-C) used `@given(...).example(...)` which raised `HypothesisException:`. Modern Hypothesis (>=6.104) explicitly forbids `.example()` inside `@given`. Fixed by using `data.draw()` pattern instead.

**This is a known deprecation but the plan template wasn't updated.** All new Hypothesis-based plans should use `data.draw(st.fixed_dictionaries(...))` instead of `.example()`.

---

## 13. Golden Fixture: `migrations.py` `datetime('now')` Breaks Bit-Identical Guarantee

The golden fixture generator plan (010-A) claimed "bit-identical on rerun" but `migrations.py` line 87 uses `datetime('now')` for the `_migrations.applied_at` column. Each rerun at a different wall clock produces different DB bytes, breaking SHA-256 checksum identity.

Caught by the plan checker (MUST_FIX). Fixed by adding `freezegun.freeze_time("2026-01-01T00:00:00Z")` wrapping the script.

**Lesson:** Any plan claiming deterministic output must audit ALL sources of non-determinism, including metadata columns in dependency modules.

---

## Summary: What Needs Fixing

| Priority | Issue | Area |
|----------|-------|------|
| **HIGH** | Phase path resolution ignores milestone_scope in most tools | All tools |
| **HIGH** | Planner doesn't write files to disk (silent failure) | gsd-planner agent |
| **HIGH** | Decimal phase numbers break tool matching | Phase matching logic |
| **MEDIUM** | Plan file naming convention mismatch (`PLAN-A.md` vs `*-PLAN.md`) | Planner prompt / Tool filter |
| **MEDIUM** | SUMMARY.md lacks `one_liner:`, `objective:` fields | Executor template |
| **MEDIUM** | Stale audit not reevaluated after gap closure | complete-milestone workflow |
| **MEDIUM** | Executor never returns `## PLAN COMPLETE` marker | Executor agent prompt |
| **LOW** | Unknown config keys (`quality`, `concurrent`) produce noise | Config validation |
| **LOW** | `phase complete` doesn't update STATE.md body text | gsd-tools.cjs |
| **LOW** | `.example()` banned by modern Hypothesis | Plan templates |
| **LOW** | `datetime('now')` in migrations breaks determinism claims | Cross-module audit gap |
