---
phase: 406
phase_name: Harness Architecture Rollup
status: secured
threats_total: 18
threats_closed: 18
threats_open: 0
asvs_level: 1
created: 2026-05-12
updated: 2026-05-12
---

# Phase 406 — Security Threat Verification

**Status:** SECURED — `threats_open: 0`

Phase 406 is **design-only**. Output is one canonical markdown specification document at `.planning/milestones/v41/phases/406/specs/HARNESS-ARCHITECTURE.md` (1991 lines). No production source code, no runtime, no network surface, no secrets, no untrusted input parsing lands in this phase. All threats target either (a) spec quality / accuracy that could mislead downstream v14 implementation, or (b) project naming-discipline drift. Mitigations are structural (grep-detectable in the spec body, structural invariants asserted, exhaustive registries with `assert_never`, absence-of-bypass patterns).

The phase verifier (`406-VERIFICATION.md`) independently confirmed 8/8 must_haves pass, including all naming-discipline and structural-invariant checks listed below.

---

## Threat Register

| # | Plan | Threat | Severity | Disposition | Status | Evidence |
|---|------|--------|----------|-------------|--------|----------|
| T-01 | 01 | Spec inaccuracy could mislead v14 implementation | med | Mitigate | CLOSED | Every operative contract (TS hook signatures, MCP tool names, v41-REQ cross-refs) rendered verbatim from 402–405 source specs; verifier confirmed all 8 ROADMAP success criteria match the spec literally |
| T-02 | 01 | Naming-discipline drift (STATE-* vs GSD-*) | med | Mitigate | CLOSED | `grep -nE '\bGSD-' HARNESS-ARCHITECTURE.md` → 0 matches; 9 STATE-* identifiers (STATE_TASK, STATE_DEVIATION_RULE, etc.) used correctly |
| T-03 | 01 | Mode-isolation drift between state_build and state_teach | low | Mitigate | CLOSED | §1 Mode-isolation subsection asserts `state_build/*` MUST NOT import `state_teach/*`; CI import-graph lint cited; `BUILD_ONLY_EVENT_PREFIXES` token present in spec |
| T-04 | 02 | Spec inaccuracy in inlined Pydantic shapes could mislead v14 implementation | med | Mitigate | CLOSED | 45 `ConfigDict(extra="forbid")` occurrences across the spec; each per-tool input/output renders the source-spec authoritative shape verbatim; drift detectable via grep against source specs |
| T-05 | 02 | Naming-discipline drift (STATE-* vs GSD-*) in §3 tool catalog | med | Mitigate | CLOSED | Verify-block bash `! grep -qE '\bGSD-' "$F"` passed at plan execution time; all 14 tool names are `state.*` exclusively |
| T-06 | 02 | `MCP_TOOL_REGISTRY` exhaustiveness gap could fail-open at runtime | med | Mitigate | CLOSED | 11 `assert_never` references in spec; CI runs `mypy --strict src/state_build/mcp/`; mirrors 405 SUBAGENT-MANAGEMENT.md §4 pattern with identical 14-case shape |
| T-07 | 02 | 4 NEW Phase-406 tools first specified (emit_advisory, force_clear_and_reinject, surface_human_gate, query_event_store) lack upstream cross-validation | med | Mitigate | CLOSED | Each NEW tool cross-referenced to operational owner (HRN-04 tier 1/3/4, HRN-07 reconstruction protocol); Plan 03 §4 and Plan 04 §5 cite these tools by name — consistency grep-detectable across §3 ↔ §4 ↔ §5 |
| T-08 | 02 | Mode-isolation drift in `state_build/mcp/` | low | Mitigate | CLOSED | §3 includes explicit Mode-isolation note; `state_build/mcp/` MUST NOT import `state_teach/` |
| T-09 | 03 | **HRN-06 human-gate bypass** — v14 could introduce custom TUI for human gates | HIGH | Mitigate | CLOSED | §4.6 asserts STRUCTURAL invariant with literal CI grep target rejecting Inquirer / click.prompt / prompt_toolkit / Textual in `state_build/harness/intervention/`; mirrors 405 DEV-04 absence-of-`full_yolo bypass` pattern. Verifier confirmed §4.6 present in spec |
| T-10 | 03 | **Tier-4 autonomy bypass via mis-classified tier** — irreversible action without human approval | HIGH | Mitigate | CLOSED | §4.4 tier dispatcher renders as deterministic match-case on source-chain event type → tier; `assert_never(source_type)` closes the match (line 1333 of spec); DEV Rule 4 events ALWAYS map to tier="human_gate" with no alternate path |
| T-11 | 03 | Umbrella event drift from per-chain events could miss tier classifications during HRN-07 reconstruction | med | Mitigate | CLOSED | §4.3 renders 18-value `trigger_reason` Literal verbatim from 406-CONTEXT.md; §4.4 documents "two events per intervention" invariant — replay can reconstruct from EITHER per-chain rows OR umbrella rows; drift detectable across the two views |
| T-12 | 03 | Pure-machine discipline drift — future LLM-as-judge in tier dispatcher | med | Mitigate | CLOSED | §4 closing paragraph asserts "umbrella `tier` value is server-derived, never agent-emitted. The dispatcher is a deterministic match; no LLM-as-judge anywhere"; carry-forward from PRF-04 spirit |
| T-13 | 03 | Naming-discipline drift (STATE-* vs GSD-*) in §4 | med | Mitigate | CLOSED | Plan verify-block bash passed; zero `GSD-` literals in spec body |
| T-14 | 03 | Mode-isolation drift in `state_build/harness/intervention/` | low | Mitigate | CLOSED | §4.6 mode-isolation note asserts `state_build/harness/intervention/` MUST NOT import `state_teach/` |
| T-15 | 04 | **Incomplete replay enumeration could leave gaps in harness reconstruction** | HIGH | Mitigate | CLOSED | §5.1 renders 5-category event table with 40 event types (exceeds the ~30 estimate); cross-checked against 4 source-event categories from 402+403+404+405; v14 unit tests assert `set(events_in_replay) == set(BUILD_ONLY_EVENT_TYPES)` per spec |
| T-16 | 04 | Reconstruction protocol step ordering ambiguity could break replay determinism | med | Mitigate | CLOSED | §5.2 renders 5 steps as numbered ordered list; step 2 explicitly seeds projector state BEFORE step 3 replays forward; `first_kept_entry_id` field on `CompactionSnapshot` pins forward-replay starting seq |
| T-17 | 04 | Orphan reconciliation false-positive could spuriously surface Rule 4 human gate | med | Mitigate | CLOSED | §5.2 step 4 references Phase 405 SUB-08 6-step protocol for canonical orphan reconciliation; persistent-orphan surfacing requires confirmation across multiple reconciliation passes (not single-shot) |
| T-18 | 04 | §6 Mermaid sequence-diagram event omission — could miss a tier | med | Mitigate | CLOSED | Verifier confirmed §6 contains single Mermaid `sequenceDiagram` with 36 event lines (above ≥25 minimum) and all 4 tier interventions surfaced (one per tier) |

---

## Severity Summary

| Severity | Count | Status |
|----------|-------|--------|
| HIGH | 3 (T-09, T-10, T-15) | All CLOSED — structural mitigations grep-verifiable |
| MED | 12 | All CLOSED — verifier confirmed every grep-target landed |
| LOW | 3 | All CLOSED — explicit mode-isolation notes present in spec |
| **Total** | **18** | **18 CLOSED / 0 OPEN** |

---

## Accepted Risks

None. All threats CLOSED via grep-detectable structural mitigations in the spec body. No risks deferred.

---

## Audit Trail

### Initial Verification — 2026-05-12

| Metric | Count |
|--------|-------|
| Threats found across 4 plans | 18 |
| HIGH severity | 3 |
| MED severity | 12 |
| LOW severity | 3 |
| Closed | 18 |
| Open | 0 |

**Verification method:** Cross-referenced each plan's `<threat_model>` mitigation claim against the `406-VERIFICATION.md` evidence and direct grep against `HARNESS-ARCHITECTURE.md`. All mitigations are structural and grep-detectable:

- `! grep -qE '\bGSD-' HARNESS-ARCHITECTURE.md` → 0 matches (naming discipline confirmed)
- `grep -c 'extra="forbid"' HARNESS-ARCHITECTURE.md` → 45 (Pydantic models constrained)
- `grep -c 'assert_never' HARNESS-ARCHITECTURE.md` → 11 (exhaustiveness pattern enforced)
- `grep -c 'sequenceDiagram\|flowchart' HARNESS-ARCHITECTURE.md` → ≥2 (HRN-01 + HRN-08 Mermaid diagrams present)
- `grep -c 'BUILD_ONLY_EVENT_PREFIXES\|state_build.*MUST NOT import' HARNESS-ARCHITECTURE.md` → present (mode-isolation enforced)
- §4.6 HRN-06 CI grep target rejecting alternate UI primitives in `state_build/harness/intervention/`
- §4.4 tier dispatcher `assert_never(source_type)` at line 1333 (tier-4 bypass impossible)

**Outcome:** Phase 406 is THREAT-SECURE. No production attack surface — design-only specification. All mitigations target downstream v14 implementation through grep-detectable structural constraints in the spec body. Phase verifier independently confirmed all required structural mitigations are present.

---

## Forward References (v14 Implementation Constraints)

Phase 406 binds v14 Build Kernel and v15 Build Core Commands to the following structural security invariants:

1. **HRN-06 absence-of-UI rule:** `state_build/harness/intervention/` MUST NOT import from `Inquirer`, `click.prompt`, `prompt_toolkit`, or `Textual`. Human gates render exclusively via opencode's `question` tool. CI grep gate must enforce.
2. **Tier dispatcher exhaustiveness:** `state_build/harness/intervention/dispatcher.py` MUST use `assert_never(source_type)` to close the match-case. `mypy --strict` must catch missing cases at type-check time.
3. **`MCP_TOOL_REGISTRY` exhaustiveness:** `state_build/mcp/registry.py` MUST use `assert_never(tool_name)` in the dispatch loop. Mirrors Phase 405 `SUBAGENT_RETURN_REGISTRY` pattern.
4. **Pure-machine `tier` derivation:** The umbrella `tier` value in `state.harness.intervention` MUST be server-derived from source-chain event type. NEVER agent-emitted. No LLM-as-judge in the dispatch path.
5. **Append-only replay invariant:** Every event listed in §5.1's 5-category table MUST be append-only. Corrections are NEW events; existing rows are immutable. Replay determinism depends on this.
6. **Mode-isolation:** `state_build/*` MUST NOT import `state_teach/*`. Events live in `BUILD_ONLY_EVENT_PREFIXES`. CI import-graph lint enforces.

These constraints are CI-enforceable by v14 onwards; the spec doc is the authoritative source.
