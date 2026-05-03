# v24 — Subject Authoring + 4-Gate Promoter

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 223–230 (8 phases)

---

## Phases

#### Phase 223 — SUBJECT.md + CONCEPT.md schema (pydantic, `extra = "forbid"`)
**Goal:** Schema per ARCHITECTURE §11.2; validator.
**Depends on:** 167
**Requirements:** SUB-04
**Parallelizable:** yes

#### Phase 224 — Conversational interview workflow (Gate 1)
**Goal:** Task subagent: asks required questions; writes DRAFT/SUBJECT.md draft.
**Depends on:** 223, 117
**Requirements:** SUB-01, SUB-02 (gate 1)
**Parallelizable:** yes

#### Phase 225 — Concept-graph authoring (Gate 2: graph approval)
**Goal:** Propose concepts + prereq edges; user approves or edits.
**Depends on:** 224
**Requirements:** SUB-01, SUB-02 (gate 2)
**Parallelizable:** yes

#### Phase 226 — Draft staging (Gate 3: draft validation)
**Goal:** Generate full `DRAFT/` tree; run validator; surface errors.
**Depends on:** 225
**Requirements:** SUB-02 (gate 3)
**Parallelizable:** yes

#### Phase 227 — Promote command (Gate 4: explicit acknowledgement)
**Goal:** `state teach subject promote <id>`; moves DRAFT/ → canonical path; emits `state.subject.promoted`.
**Depends on:** 226
**Requirements:** SUB-02 (gate 4), SUB-03
**Parallelizable:** no

#### Phase 228 — `state teach subject new|edit` CLI
**Goal:** Typer commands; `new` invokes interview; `edit` opens existing for amendment.
**Depends on:** 224, 225
**Requirements:** SUB-03
**Parallelizable:** yes

#### Phase 229 — Schema-validation test suite (golden + malformed fixtures)
**Goal:** Property test: valid fixtures pass; each mandatory field missing → fails with clear error.
**Depends on:** 223
**Requirements:** SUB-04
**Parallelizable:** yes

#### Phase 230 — 4-gate integration test (end-to-end authoring run)
**Goal:** Synthetic interview → approve graph → validate draft → promote → subject appears in `subject list`.
**Depends on:** 223..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

