---
phase: 400
slug: tier-definitions-state-machines
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-06
---

# Phase 400 — Validation Strategy

> Design-phase milestone — validation is manual peer review of specification documents. No executable code.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | N/A — design-phase milestone |
| **Config file** | N/A |
| **Quick run command** | N/A |
| **Full suite command** | N/A |
| **Estimated runtime** | N/A |

---

## Sampling Rate

- N/A — design-phase milestone. No automated tests.

---

## Per-Task Verification Map

Design-phase milestone — verification is manual review against success criteria.

| Req ID | Behavior | Validation Type | How Verified | Status |
|--------|----------|----------------|-------------|--------|
| TIER-01 | Four standalone tier spec documents | Manual review | Spec docs exist, internally complete, readable without cross-reference | ⬜ pending |
| TIER-02 | Arc spec: state machine, artifacts, frontmatter | Manual review | ARC.md frontmatter fields match D-17 Arc states | ⬜ pending |
| TIER-03 | Stage spec: state machine, artifacts, frontmatter | Manual review | Uses "Stage" not "Phase" terminology throughout | ⬜ pending |
| TIER-04 | Slice spec: state machine, artifacts, Steps as files | Manual review | No Step subdirectory in on-disk layout | ⬜ pending |
| TIER-05 | Step spec: design→plan→run→verify cycle | Manual review | Uses D-03 renamed terminology | ⬜ pending |
| TIER-06 | Event taxonomy per tier with composite events | Manual review | All events map to state transitions | ⬜ pending |
| TIER-07 | Field ownership classified per field | Manual review | No field claimed by both agent and projector | ⬜ pending |
| TIER-08 | Pydantic models with extra="forbid" | Manual review | All schema code blocks include ConfigDict(extra="forbid") | ⬜ pending |
| FSM-01 | State transition tables for all four tiers | Manual review | Every transition has guard condition and event trigger | ⬜ pending |
| FSM-02 | Composite event cascade fully specified | Manual review | Step→Slice→Stage→Arc trigger conditions explicit | ⬜ pending |
| FSM-03 | Descope/abandon semantics with cascade rules | Manual review | Abandon→dependents blocked (D-13); defer→dependents soft-done (D-14) | ⬜ pending |
| FSM-04 | Decimal insertion protocol | Manual review | Single decimal level; no 12.1.2; reorganization threshold | ⬜ pending |
| FSM-05 | Blocked state semantics | Manual review | Entry conditions, blocked_reason, unblock detection | ⬜ pending |
| FSM-06 | Budget enforcement per tier | Manual review | Arc≤4, Stage≤4, Slice≤4, Step≤8 per D-17 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — this is a design-phase milestone with no test infrastructure needed.

---

## Manual-Only Verifications

All 14 requirements are manual review — design-phase milestone with no executable code.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All tier spec documents self-contained | TIER-01 | Architecture docs | Read each spec doc; verify no external reference required for understanding |
| State machine budget enforcement | FSM-06 | Requires human judgment | Count forward-progression states per tier against D-17 budgets |
| Agent vs projector field ownership | TIER-07 | Architectural boundary | Scan every frontmatter field; verify single owner |
| Composite event cascade | FSM-02 | Cross-tier integration | Trace Step→Slice→Stage→Arc event chains; verify each trigger condition |
| Descope/abandon/defer cascade | FSM-03 | Complex semantics | Test each cascade scenario (abandon→block, defer→soft-done) against spec |

---

## Validation Sign-Off

- [ ] All tasks have verification mapped
- [ ] Sampling continuity: N/A (design-phase)
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < N/A
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
