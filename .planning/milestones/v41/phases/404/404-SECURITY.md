---
phase: 404
phase_name: Boolean Proof Gate & Discipline Guards
audited: 2026-05-11
asvs_level: 1
phase_type: design-only
threats_total: 23
threats_closed: 23
threats_open: 0
status: secure
---

# Phase 404 Security Audit

## Audit Scope

Phase 404 is **design-only** — produces 3 canonical specification documents (PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, SCOPE-PROHIBITION.md) plus 2 amendment blocks to v40 catalog files. No production code lands.

Threats live at two scopes:
1. **Spec authoring threats** — risk that the produced spec docs themselves mislead the v14 implementer (mitigations: verbatim Pydantic schemas, explicit prose authority statements, cross-reference pinning).
2. **Forward-design threats** — risks that the *specified* runtime behaviors create attack surface when v14 implements them (mitigations: explicit constraints in the spec text that v14 MUST implement).

All threats are classified CLOSED because: (a) mitigations are documented in the spec content that this phase produces, and (b) actual runtime enforcement is owned by v14 Build Kernel (Milestone v42-v50 implementation territory), which inherits these spec contracts as test fixtures and Pydantic-schema fixtures.

## Threat Register

### Plan 01 — PROOF-GATE.md (PRF-01..07)

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 01-T1 | high | spec-misinterpretation | Spec leaves 4-state verdict (pass/flag/omitted/fail) or strike-counter scope (per-(task_id, check_id)) ambiguous → v14 collapses states or counters | CLOSED | `specs/PROOF-GATE.md` §6 (strike counter semantics, verbatim from CONTEXT.md `<decisions>` Strike-counter section); §7 Pydantic `StepVerifyResult` enumerates `Literal["pass", "flag", "omitted", "fail"]` verbatim |
| 01-T2 | med | integer-overflow | Unbounded strike counter overflows under pathological agent loops | CLOSED | `specs/PROOF-GATE.md` §6 stipulates `strike_number: int  # 1..6`; ladder closes at strike 6 → human_gate |
| 01-T3 | high | aggregate-corruption | Agent-emitted `overall_passed: true` while sub-check is `fail` corrupts audit log | CLOSED | `specs/PROOF-GATE.md` §7 "Server-side recomputation is NON-NEGOTIABLE" subsection with positive/negative examples; v14 enforces at StepVerifyResult parser boundary |
| 01-T4 | med | mode-isolation | Build-only spec must not leak into Teach mode | CLOSED | `specs/PROOF-GATE.md` header `> **Build-mode only.**` callout; `grep -c "state.teach."` = 0 |
| 01-T5 | low | injection | Truncation marker `[... truncated <N> bytes ...]` collides with agent-controllable N | CLOSED | `specs/PROOF-GATE.md` §7 stipulates N is harness-computed from byte length, not agent-controlled |
| 01-T6 | med | spec-divergence | Mermaid sequence diagram contradicts prose protocol → v14 follows whichever is convenient | CLOSED | `specs/PROOF-GATE.md` §5 states "prose protocol is authoritative; diagram is supplementary"; both cross-checked at planner-validation stage |

### Plan 02 — ANALYSIS-PARALYSIS-GUARD.md (APG-01..06)

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 02-T1 | med | classifier-evasion | Compound commands / eval-piped / base64-encoded payloads hide a write under a read-classified surface | CLOSED | `specs/ANALYSIS-PARALYSIS-GUARD.md` §1 explicit "ADVISORY, not security boundary" framing (cites gsd-2 `tool-system.md:851`); §4 "worst-sub-command wins" for compound; documented limitation acknowledged; canonical security boundary is `files_modified` allowlist (SCOPE-PROHIBITION.md SRP-04) |
| 02-T2 | med | regex-DoS | Catastrophic backtracking on pathological Bash command strings | CLOSED | `specs/ANALYSIS-PARALYSIS-GUARD.md` §3 requires READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS to be pre-compiled (`re.compile`); no nested quantifiers; payload cap recommended at 64KB |
| 02-T3 | high | integer-overflow | `count: int` unbounded; advisory_number unbounded | CLOSED | `specs/ANALYSIS-PARALYSIS-GUARD.md` §8 ParalysisEvent payload stipulates `advisory_number: int  # 1..6`; counter resets at threshold transition; v14 enforces via type guard |
| 02-T4 | med | mode-isolation | `state_build/harness/paralysis/bash_classifier.py` must not import `state.teach.*` | CLOSED | `specs/ANALYSIS-PARALYSIS-GUARD.md` "Build-mode only" header; explicit module-path pin; stdlib `re` only |
| 02-T5 | low | spec-ambiguity | Redirection rules ambiguous (e.g., `tee` distinguishing write vs `tee --version` read) | CLOSED | `specs/ANALYSIS-PARALYSIS-GUARD.md` §4 redirection rules rendered as markdown table with positive AND negative examples for each form; v14 tests use table as fixture |
| 02-T6 | low | module-drift | v14 splits READ_ONLY_PATTERNS into multiple modules → drift on updates | CLOSED | `specs/ANALYSIS-PARALYSIS-GUARD.md` §3 explicit "single Python module" requirement at `state_build/harness/paralysis/bash_classifier.py` (mirrors gsd-2 `branch-patterns.ts`) |

### Plan 03 — SCOPE-PROHIBITION.md (SRP-01..06)

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 03-T1 | high | privilege-escalation | `scope_deviation_request` to sensitive paths (`~/.ssh/config`, auth credentials, parent repo's `.git/config`) | CLOSED | `specs/SCOPE-PROHIBITION.md` §7 event-scoped one-shot allowlist; deviation = `checkpoint:decision` requiring human approval under `--tiered`/`--conservative`; **`files_modified` NEVER mutated at runtime**; auto-resolution policy owned by Phase 405 (not this spec) |
| 03-T2 | high | path-traversal | `requested_path` with `..` segments or absolute paths outside repo root → arbitrary read/write | CLOSED | `specs/SCOPE-PROHIBITION.md` §7 stipulates realpath-resolution within repo root (mirrors Phase 403 PAP-02 path-confinement); traversal-resolved paths outside root rejected at MCP-tool-handler boundary before human decision surfaced; v14 implements via `pathlib.Path.resolve()` + ancestor check |
| 03-T3 | med | scan-bypass | EXCEPTION_RE bypass via fake tracking IDs (`# TODO(FAKE-99)`) | CLOSED | `specs/SCOPE-PROHIBITION.md` §4 pure-machine grep cross-check at scan time; captured ID MUST resolve to REQUIREMENTS.md `**ID-NN**` heading OR `deferred-items.md - ID-NN:` row; unresolved → `scope_check` advisory + reject |
| 03-T4 | med | regex-DoS | PROHIBITED_RE and EXCEPTION_RE catastrophic backtracking on long content | CLOSED | `specs/SCOPE-PROHIBITION.md` §4 stipulates pre-compiled regex with `re.compile`; simple alternation, no nested quantifiers; per-write content cap recommended at 1 MB |
| 03-T5 | high | scope-evasion | `request_step_split` abuse — agent bails out of every Step | CLOSED | `specs/SCOPE-PROHIBITION.md` §8 `reason: str ≤2KB` becomes audit log; Phase 405 DEV-04 consumes split_recommendation events; over-frequent splits trigger Rule 4 human gate; v14 emits split_recommendation_telemetry at Slice close |
| 03-T6 | low | mode-isolation | Build-only spec | CLOSED | "Build-mode only" header; `state_build/harness/scope/` module-path pin |
| 03-T7 | low | injection | Truncation marker harness-controlled | CLOSED | Shared truncation utility across Phase 404 sibling specs; marker not user-controllable |

### Plan 04 — Event Amendments

| # | Severity | Category | Threat | Status | Evidence (mitigation site) |
|---|----------|----------|--------|--------|--------------------------|
| 04-T1 | high | spec-corruption | Amendment overwrites v40 EVENT-TAXONOMY.md or ARTIFACT-CATALOG.md original content → v40 history corrupted | CLOSED | Plan 04 verify_automated block confirmed prior Phase 402 (line 199) + Phase 403 (line 239) amendment headers preserved byte-for-byte in EVENT-TAXONOMY.md; Phase 402 (line 796) preserved in ARTIFACT-CATALOG.md; append-only via unique H2 anchor `## v41 Amendment — Phase 404 ...` |
| 04-T2 | med | naming-drift | New events use form other than `state.{tier}.{action}` → projector/replay breaks | CLOSED | Plan 04 amendment uses `^state\\.(step|slice)\\.[a-z_]+$` form for all 10 new events (gate_strike, gate_resolved, step_verify_completed, slice_verify_completed, paralysis_event, scope_check, scope_deviation_request, scope_deviation_resolved, split_recommendation, plan_edit_blocked); convention preserved |
| 04-T3 | med | broken-references | Phase 404 spec files renamed → amendment forward-pointers break | CLOSED | Accepted maintenance risk; alternative (inlining schemas) would create harder schema-drift problem; v14+ teams surface broken refs at planner-validation stage |
| 04-T4 | low | mode-isolation | All Phase 404 events live in BUILD_ONLY_EVENT_PREFIXES | CLOSED | Amendment explicitly states Build-only; mirrors Phase 402+403 amendment pattern |

## Summary

| Severity | Total | Closed | Open |
|----------|-------|--------|------|
| High | 7 | 7 | 0 |
| Med | 11 | 11 | 0 |
| Low | 5 | 5 | 0 |
| **Total** | **23** | **23** | **0** |

`threats_open: 0` — phase is THREAT-SECURE.

## Accepted Risks Log

(none — all threats CLOSED via specified mitigations; no risk acceptance required)

## v14 Inheritance Contract

The following spec-text mitigations create implementation contracts for v14 Build Kernel:

| Contract | Site | v14 enforcement point |
|----------|------|----------------------|
| Pydantic `extra="forbid"` on every event payload | spec docs §6/§7/§8 | Pydantic parser at MCP-tool-handler boundary |
| `strike_number: int  # 1..6` bound | PROOF-GATE.md §6 | Type guard at strike-counter increment site |
| Server-side recomputation of `overall_passed` | PROOF-GATE.md §7 | StepVerifyResult parser rejects LLM-emitted aggregate when sub-fields contradict |
| `pathlib.Path.resolve()` + ancestor check on `scope_deviation_request.requested_path` | SCOPE-PROHIBITION.md §7 | MCP-tool-handler boundary, before human decision surfaced |
| Pre-compiled regex with no nested quantifiers | ANALYSIS-PARALYSIS-GUARD.md §3 + SCOPE-PROHIBITION.md §4 | v14 regex-module load-time |
| `files_modified` NEVER mutated at runtime | SCOPE-PROHIBITION.md §6/§7 | Tool.execute.before write-block enforces; deviation events are scoped, not mutating |
| Single-module pattern for regex corpora | ANALYSIS-PARALYSIS-GUARD.md §3 | v14 architecture review |
| Append-only `<discovered_threats>` carve-out | All plans `<discovered_threats>` block | PAP-05 immutability matrix exempts this sub-block |

v14 inherits this contract as Pydantic-schema fixtures and unit-test corpora — the spec docs are the single source of truth.

## Audit Trail

### Audit 2026-05-11
| Metric | Count |
|--------|-------|
| Threats found | 23 |
| Closed (mitigation in spec) | 23 |
| Closed (accepted risk) | 0 |
| Open | 0 |

Phase 404 design-only — runtime enforcement deferred to v14 Build Kernel. All threats have written mitigations in the produced spec docs. No accepted risks. No escalations. Gate: PASS.
