---
phase: 402
slug: slice-cycle-context-window-spec
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-08
---

# Phase 402 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Phase 402 is **design-only** — it produces markdown specifications (SLICE-CYCLE.md, CONTEXT-PROTOCOL.md), 7 v40 spec amendments (append-only), and a single new requirement entry (CTX-09). No production code lands. No secrets handled. No network calls. No untrusted input. The threat surface is restricted to specification correctness, mode-isolation discipline in spec text, and downstream-implementation contract drift.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Phase 402 specs ↔ v14 Build Kernel implementer | Future v14 phase reads `CONTEXT-PROTOCOL.md` to implement `CompactionSnapshot`, context-meter, reinject payload | Schema contract (Pydantic field set, JSON wire format) |
| Phase 402 specs ↔ Phases 403–406 (v41 follow-on) | Downstream phases cite `SLICE-CYCLE.md` as canonical Slice-cycle reference | Vocabulary, stage names, event payload shapes |
| Phase 402 specs ↔ v40 spec corpus | Plan 03 amends 7 v40 spec files (`TIER-SLICE.md`, `TIER-STEP.md`, `EVENT-TAXONOMY.md`, `COMPOSITE-CASCADE.md`, `ARTIFACT-CATALOG.md`, `DIRECTORY-TREE.md`, `CROSS-REFERENCES.md`) | Append-only `## v41 Amendment` blocks |
| Build-mode (`state.build.harness.*`) ↔ Teach-mode (`state.teach.*`) | Cardinal cross-mode import isolation per PROJECT.md | Specification text MUST stay Build-only — no Teach contract bleed |
| Anthropic OAuth subsystem ↔ context-meter | Cardinal rule: "OAuth traffic NEVER routes through litellm"; meter must not inspect auth headers | `usage.input_tokens` / `usage.cache_read_input_tokens` from tool-response payloads only |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-402-01 | Tampering / Information Disclosure | SLICE-CYCLE.md (Plan 01) | mitigate | Only inside-repo content quoted; all examples fenced; no executable templating; no fetched/external content | closed |
| T-402-02 | Tampering | SLICE-CYCLE.md ↔ Plan 03 forward-pointer (Plan 01) | mitigate | Plan 03 verifies forward-pointer round-trip after writing amendments; `depends_on: [01]` enforces ordering | closed |
| T-402-03 | Information Disclosure / Repudiation | SLICE-CYCLE.md mode-isolation drift (Plan 01) | mitigate | Explicit "Build-mode only. `state.build.harness.*` MUST NOT import `state.teach.*`" header at line 16; verified by grep | closed |
| T-402-04 | Tampering / Information Disclosure | CONTEXT-PROTOCOL.md (Plan 02) | mitigate | All Pydantic / orjson / XML examples fenced; no executable templating; illustrative only | closed |
| T-402-05 | Tampering | CompactionSnapshot schema drift v14 (Plan 02) | mitigate | Field list matches 402-CONTEXT.md verbatim; `extra="forbid"` enforced (7 occurrences) — unknown fields fail validation; v14 must extend via explicit migration | closed |
| T-402-06 | Information Disclosure / Spoofing | OAuth-stealth-route bleed in context-meter (Plan 02) | mitigate | CONTEXT-PROTOCOL.md line 294 explicitly states "the meter reads `usage` fields from tool-response payloads only; it never inspects auth headers"; cardinal rule cited (line 400) | closed |
| T-402-07 | Information Disclosure / Repudiation | CONTEXT-PROTOCOL.md mode-isolation drift (Plan 02) | mitigate | "Build-mode only" header at line 8; cardinal rule cited; no Teach references | closed |
| T-402-08 | Tampering | v40 amendment overwriting (Plan 03) | mitigate | All amendments APPENDED with unique `## v41 Amendment` anchor (which does not exist in v40 base text); 7/7 spec files verified to contain anchor; original v40 H1 + first H2 unchanged per executor self-check | closed |
| T-402-09 | Tampering | v40 amendment forward-pointer drift (Plan 03) | mitigate | `depends_on: [01]` enforces ordering; SLICE-CYCLE.md present at amendment time (verified post-merge); pointer paths cited verbatim | closed |
| T-402-10 | Repudiation / Information Disclosure | v40 amendment text contradicts v40 base (Plan 03) | mitigate | Each Phase-400 amendment opens with `Prior model (v40):` + `Canonical model (v41):` structure (verified: TIER-SLICE/TIER-STEP/EVENT-TAXONOMY/COMPOSITE-CASCADE all show prior_refs ≥ 1, canonical_refs ≥ 5); Phase-401 amendments are short pointer amendments (no v40-vs-v41 model conflict to disambiguate) | closed |
| T-402-11 | Information Disclosure | v40 amendment mode-isolation drift (Plan 03) | mitigate | Amendment text reused across files; pre-written in plan; reviewed once; no Teach references introduced | closed |
| T-402-12 | Tampering | CTX-09 numbering collision (Plan 04) | mitigate | REQUIREMENTS.md body AND Traceability table both updated atomically; verification grep confirmed 3 occurrences of "CTX-09" in REQUIREMENTS.md | closed |
| T-402-13 | Tampering | CTX-09 text drift from CONTEXT.md (Plan 04) | mitigate | Task action embedded the exact six-step CTX-09 text verbatim; executor copied without rewording; cross-plan invariant Plan 02↔Plan 04 confirmed (CTX-09 cited 5× in CONTEXT-PROTOCOL.md, 3× in REQUIREMENTS.md) | closed |
| T-402-14 | Tampering | Milestone total miscount 72→73 (Plan 04) | mitigate | Acceptance criterion checked the new total; tail annotation "v1 requirement total: 72 → 73" present at line 259 of REQUIREMENTS.md | closed |
| T-402-15 | Tampering | ROADMAP.md ↔ REQUIREMENTS.md drift on CTX-09 (Plan 04) | mitigate | Verification greps both v41 ROADMAP.md (3 occurrences) and v41 REQUIREMENTS.md (3 occurrences); Phase 402 reqs line + milestone-level coverage table both updated | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-08 | 15 | 15 | 0 | /gsd:secure-phase orchestrator |

### Audit Notes

- All 4 plans had explicit `<threat_model>` blocks in their PLAN.md files; threats consolidated into the register above.
- Phase 402 is a design-only documentation phase: no production code, no secrets, no network surface, no untrusted input. The threat surface reduces to (a) spec correctness, (b) mode-isolation discipline in spec text, (c) downstream-implementation contract drift.
- All 15 mitigations verified post-merge via direct grep against the merged artifacts on `gsd/phase-402-phase`. No auditor spawn was needed because no threats remained open after artifact verification.
- Cardinal rules honored:
  - Build-mode only header lines verified in both spec docs (SLICE-CYCLE.md line 16, CONTEXT-PROTOCOL.md line 8).
  - OAuth-stealth isolation explicitly called out in CONTEXT-PROTOCOL.md §11 (line 294) and reinforced in cross-references (line 400).
  - `extra="forbid"` Pydantic discipline present 7× in CONTEXT-PROTOCOL.md (≥2 floor).

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (none)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-08
