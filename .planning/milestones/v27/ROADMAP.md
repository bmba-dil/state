# v27 — Release & Packaging

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 247–256 (10 phases)

---

## Phases

#### Phase 247 — `pyproject.toml` with `uv_build` backend (full dep pins per STACK.md)
**Goal:** Complete `pyproject.toml`; CI install-from-source check.
**Depends on:** 001
**Requirements:** REL-01
**Parallelizable:** yes

#### Phase 248 — `uvx state install` installer (detect opencode, auto-register)
**Goal:** Typer command; detects opencode binary; adds plugin + MCP to `opencode.json`.
**Depends on:** 247, 079, 106, 115
**Requirements:** REL-02
**Parallelizable:** yes

#### Phase 249 — Wheel bundling (plugin TS source + bun build output)
**Goal:** Build pipeline: `bun build` plugin → include in wheel; CI verifies wheel contents.
**Depends on:** 079, 247
**Requirements:** REL-03
**Parallelizable:** yes

#### Phase 250 — `state update` PyPI version check + upgrade prompt
**Goal:** Typer command; queries PyPI; prompts; invokes `uv pip install -U state`.
**Depends on:** 247
**Requirements:** REL-04
**Parallelizable:** yes

#### Phase 251 — Remote skill registry (`state skills add <url>`)
**Goal:** Fetches manifest; integrates with opencode `cfg.skills.urls` mechanism.
**Depends on:** 247
**Requirements:** REL-05
**Parallelizable:** yes

#### Phase 252 — Release-notes generator (from commit history + phase artifacts)
**Goal:** Walks event log + git log; produces structured release notes.
**Depends on:** 009
**Requirements:** REL-06
**Parallelizable:** yes

#### Phase 253 — Documentation — all 8 guides (architecture, user, command ref, build-author, teach-author, plugin-dev, auth setup, portability)
**Goal:** Written throughout earlier milestones but finalized here; cross-linked; version-locked.
**Depends on:** v1, 247 (hard — docs source-of-truth + structure scaffold); all other v1..v26 (soft — feature-complete docs coverage)
**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08
**Parallelizable:** yes

#### Phase 254 — Full test infrastructure + P0 regression suite (all 16 pitfalls)
**Goal:** pytest + pytest-asyncio (strict_asyncio), Hypothesis property tests, E2E opencode fixture, provider parity matrix, captured-header regression, mode-isolation import-graph, P0 regression tests. Artifact: `.state/build/p0-test-matrix.md` mapping each P0-ID (P0-1..P0-16) → upstream regression-test path + owning milestone/phase + release-time re-run site.
**Depends on:** v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15, v16, v17, v18, v19, v20, v21, v22, v23, v24, v25, v26 (hard — each milestone's verifier phase must ship before P0-regression matrix is green)
**Requirements:** TST-01, TST-02, TST-03, TST-04, TST-05, TST-06, TST-07, TST-08
**Parallelizable:** yes

#### Phase 255 — Observability finalization (structlog, redactor, event-log forensics, CLI `state logs tail`)
**Goal:** Final wiring; `state logs tail [--level] [--component]` CLI; OpenTelemetry hooks present but opt-in (v2). P0-14 release-time redactor regression re-runs here as the hand-off from 020 — asserts no `sk-ant-*` / `sk-*` / `ya29.*` tokens leak to structlog output when `debug=true`.
**Depends on:** 020, 056
**Requirements:** OBS-01, OBS-02, OBS-03, OBS-04
**Parallelizable:** yes

#### Phase 256 — Security baseline (path-traversal, prompt-injection, shell-meta, regex-DoS, JSON-bomb, chmod-0600 verifiers)
**Goal:** All guards attached to every surface; per-Step security verifier (refinement of 132); regression tests including chmod-0600 verifier (re-runs the P0-13 regression harness from 012 — asserts auth.json chmod is verified on every read under concurrent access).
**Depends on:** 132, 012
**Requirements:** SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06
**Parallelizable:** yes

