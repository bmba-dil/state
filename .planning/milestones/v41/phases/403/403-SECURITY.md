---
phase: 403
slug: step-task-decomposition-plan-as-prompt
status: verified
threats_open: 0
threats_closed: 20
asvs_level: 1
created: 2026-05-10
---

# Security Verification — Phase 403 (Step/Task Decomposition & Plan-as-Prompt)

**Phase:** 403 — Step/Task Decomposition & Plan-as-Prompt
**ASVS Level:** 1 (design-only phase; no production code)
**Date:** 2026-05-10
**Auditor:** gsd-security-auditor
**Threats closed:** 20 / 20
**Threats open:** 0 / 20

---

## Verification Summary

Phase 403 is a design-only phase producing 4 markdown spec documents:
- `EXEMPLAR-stepNPLAN.md` — canonical worked example
- `STEP-PLAN-FORMAT.md` — stepNPLAN.md format spec
- `PLAN-AS-PROMPT.md` — injection, mutability, and audit-log spec
- `STEP-EVENTS.md` — step-tier event Pydantic schema spec

For each threat, mitigation is verified as: the stipulated content (rule statement, diff shape,
example, header note) EXISTS in the produced spec file. No runtime code is involved.

---

## Threat Verification

### Plan 01 — EXEMPLAR-stepNPLAN.md

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| 403-01-T01 | Tampering — Path-traversal in @-refs | mitigate | `EXEMPLAR-stepNPLAN.md` line 66: "(All `@`-references in this file resolve under repo root + `.planning/` per PAP-02 path-confinement rule.)" Every @-ref is under `.planning/` or repo root; zero absolute-path refs. |
| 403-01-T02 | Tampering — `<discovered_threats>` pre-populated | mitigate | `EXEMPLAR-stepNPLAN.md` lines 288-290: `<discovered_threats>` block contains only `<!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->`. |
| 403-01-T03 | Tampering — Markdown code-block injection | mitigate | All code in EXEMPLAR is fenced (6 fenced blocks confirmed). File is static markdown; no executor runs it. |
| 403-01-T04 | Information Disclosure — Mode-isolation drift | mitigate | Header comment line 7: "Build-mode only. No teach-mode module imports permitted." `grep -c "state\.teach\." EXEMPLAR-stepNPLAN.md` = 0. |

### Plan 02 — STEP-PLAN-FORMAT.md

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| 403-02-T01 | Tampering — `<discovered_threats>` append-only enforcement weak | mitigate | `STEP-PLAN-FORMAT.md` lines 565-576: exact diff shape rule present — "ONLY new `<threat>...</threat>` sub-elements added at the end of `<discovered_threats>`; no removal of existing children, no edit of existing children's text." Forward-pointer to PAP-05 (PLAN-AS-PROMPT.md §7) which contains the positive diff (ACCEPTED) and two negative diffs (REJECTED). |
| 403-02-T02 | Tampering — `<options>` attribute set drift | mitigate | `STEP-PLAN-FORMAT.md` lines 384 and 514: spec locks attribute set to `name`, `pros`, `cons` (no additional attributes). Line 384 table entry specifies "each option has `name`, `pros`, `cons` attributes." |
| 403-02-T03 | Tampering — Granularity algorithm soft thresholds | mitigate | `STEP-PLAN-FORMAT.md` lines 708-710: pseudocode contains exact integer constants `30_000` and `80_000` as bucket thresholds. |
| 403-02-T04 | Tampering — STP-07/STP-08 vague-entry evasion | mitigate | `STEP-PLAN-FORMAT.md`: 10 REJECT counterexamples total (confirmed via grep). STP-07 section has 4 REJECT cases; STP-08 section has 5 REJECT cases. Exceeds ≥4 each floor. |
| 403-02-T05 | Information Disclosure — Mode-isolation drift | mitigate | `STEP-PLAN-FORMAT.md` line 6: "Build-mode only. `state.build.*` MUST NOT import `state.teach.*`". Lines 6 and 827 are both rule-prohibition statements quoting the cardinal rule — neither is an actual teach-mode import or reference. Zero teach-mode module references. |

### Plan 03 — PLAN-AS-PROMPT.md

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| 403-03-T01 | Tampering — @-ref resolver path traversal | mitigate | `PLAN-AS-PROMPT.md` lines 118-148: realpath confinement via `pathlib.Path.resolve()` + ancestor check specified. ALLOWED block (3 examples) and REJECTED block with `@/etc/passwd`, `@../../../home/user/.ssh/id`, `@/tmp/whatever.md`, `@http://evil.example/x.md` (4 rejected examples). Fail-closed semantics stated. |
| 403-03-T02 | Tampering — PlanEdit replay tampering | mitigate | `PLAN-AS-PROMPT.md` lines 306-312: "Replay-time integrity check (security mitigation)" subsection. `before_sha256` and `after_sha256` both required to match SHA-256 of content before/after diff. Hash mismatch rejects the event and surfaces as daemon-startup error. |
| 403-03-T03 | Tampering — PlanEditBlocked enforcement bypass via direct write | mitigate | `PLAN-AS-PROMPT.md` lines 390-392: "No-direct-write contract" subsection. "ALL writes to `*/stepNPLAN.md` MUST go through `tool.execute.before`." Subprocess shell bypass is "out-of-policy." |
| 403-03-T04 | Tampering — StepPlanAuthored snapshot tampering | mitigate | `PLAN-AS-PROMPT.md` line 316: "the `state.step.plan_authored` row is append-only; replay rebuilds the original from this row alone." v40 EVENT-TAXONOMY.md append-only convention cited. |
| 403-03-T05 | Tampering — `<discovered_threats>` diff masquerade | mitigate | `PLAN-AS-PROMPT.md` lines 360-388: `<discovered_threats>` append-only diff shape section with 1 ACCEPTED diff and 2 REJECTED diffs ("existing threat text edited", "existing threat removed"). |
| 403-03-T06 | Information Disclosure — Mode-isolation drift | mitigate | `PLAN-AS-PROMPT.md` header (line 6): "Build-mode modules must not import teach-mode modules (cardinal rule, PROJECT.md — mode isolation enforced by CI import-graph lint)." `grep -c "state\.teach\." PLAN-AS-PROMPT.md` = 0. |

### Plan 04 — STEP-EVENTS.md + v40 EVENT-TAXONOMY.md Amendment

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| 403-04-T01 | Tampering — StepPlanAuthored snapshot tampering | mitigate | `STEP-EVENTS.md` lines 39, 74, 86, 302: append-only stated in Conventions; Security note on StepPlanAuthored states row is append-only; `original_sha256` field present; projector verifies hash on every load (PlanAuthoredIntegrityError on mismatch). |
| 403-04-T02 | Tampering — PlanEdit replay tampering | mitigate | `STEP-EVENTS.md` lines 132-148: "Replay-time integrity check" subsection. `before_sha256` and `after_sha256` verified at replay. Pseudocode algorithm for replay reconstruction with assertions present. |
| 403-04-T03 | Tampering — v40 EVENT-TAXONOMY.md amendment overwriting | mitigate | `EVENT-TAXONOMY.md` line 1: H1 "# Event Taxonomy — All Four Tiers" unchanged. Amendment at line 239 uses unique anchor "## v41 Amendment — Step-Tier Event Family Extension" (the line 199 "## v41 Amendment" is the Phase 402 amendment, pre-existing). Phase 403 amendment is append-only via Edit. Line count = 281 (below the plan's ≥600 expectation — see Accepted Anomalies below). |
| 403-04-T04 | Tampering — Event-name convention drift | mitigate | `STEP-EVENTS.md` lines 20-28, 36: all 9 events follow `state.step.{action}` form. Listed upfront in overview table. Convention rule stated: "All events have type string `state.step.{action}` per v40 EVENT-TAXONOMY.md." |
| 403-04-T05 | Information Disclosure — Mode-isolation drift | mitigate | `STEP-EVENTS.md` lines 6, 42: "Build-mode only. All events go in `BUILD_ONLY_EVENT_PREFIXES`." Conventions section: "Mode prefix: `BUILD_ONLY_EVENT_PREFIXES` includes `state.step.` (Build-only)." `grep -c "state\.teach\." STEP-EVENTS.md` = 0. |

---

## Unregistered Threat Flags

No `## Threat Flags` section was detected in any SUMMARY.md for Phase 403. No unregistered flags to report.

---

## Accepted Anomalies (Non-Blocking)

### EVENT-TAXONOMY.md line count below 600

The v40 EVENT-TAXONOMY.md has 281 lines (the Plan 04 `<verify>` script checked for ≥600). Investigation shows the plan's ≥600 floor was an overestimate of the original v40 file size. The important mitigation properties hold:
- Original H1 is unchanged (line 1 verified).
- Phase 402 v41 Amendment is present at line 199 (pre-existing from Phase 402 execution).
- Phase 403 v41 Amendment is appended at line 239 with unique anchor "## v41 Amendment — Step-Tier Event Family Extension".
- All 9 new event types listed in the amendment table.
- Append-only: no original v40 content was modified.

This is a documentation threshold anomaly, not a security gap. Threat 403-04-T03 is CLOSED.

### STEP-PLAN-FORMAT.md `state.teach.*` appearances

Two occurrences of `state.teach.*` appear in STEP-PLAN-FORMAT.md (lines 6 and 827). Both are
rule-prohibition statements quoting the cardinal mode-isolation rule ("MUST NOT import `state.teach.*`"),
not actual references to teach-mode modules. Mode isolation is enforced, not violated.

---

## Mode Isolation Scan (All Spec Files)

| File | `state.teach.*` count | Assessment |
|------|----------------------|------------|
| EXEMPLAR-stepNPLAN.md | 0 | PASS |
| STEP-PLAN-FORMAT.md | 2 (both are prohibition statements) | PASS |
| PLAN-AS-PROMPT.md | 0 | PASS |
| STEP-EVENTS.md | 0 | PASS |

Path-traversal demo check (should appear ONLY as REJECT examples):
- `@/etc/passwd` appears in PLAN-AS-PROMPT.md line 142 only — inside the REJECTED block. PASS.
- `@../` traversal appears in PLAN-AS-PROMPT.md line 143 only — inside the REJECTED block. PASS.
- Neither pattern appears in EXEMPLAR-stepNPLAN.md, STEP-PLAN-FORMAT.md, or STEP-EVENTS.md.
