# v11 — Mode Enforcement (6 Layers)

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 097–105 (9 phases)

---

## Phases

#### Phase 097 — `.state/mode.json` schema + validator
**Goal:** Pydantic `ModeConfig` with `mode: build|teach|both`; strict validation; CLI init.
**Depends on:** 002
**Requirements:** MODE-01
**Parallelizable:** yes
**Plans:** 2 plans

Plans:
- [x] 097-01-PLAN.md — Canonical ModeConfig + validator in schema.py
- [x] 097-02-PLAN.md — CLI `state mode init` command

#### Phase 098 — Directory-presence signal (`.state/build/` vs `.state/teach/`)
**Goal:** Daemon refuses writes into the wrong subtree; `state mode init` bootstraps structure.
**Depends on:** 097
**Requirements:** MODE-02
**Parallelizable:** yes with P3
**Plans:** 2 plans

Plans:
- [ ] 098-01-PLAN.md — Core subtree constants + validate_subtree_path() + CLI subtree bootstrap
- [ ] 098-02-PLAN.md — Daemon middleware subtree enforcement (validate_daemon_path)

#### Phase 099 — MCP registration toggle (`config` hook)
**Goal:** Plugin reads `.state/mode.json` at boot; `config` hook returns enabled/disabled for each server; hot-reload on mode change.
**Depends on:** 068, 097
**Requirements:** MODE-03
**Parallelizable:** yes with P2

#### Phase 100 — Plugin hook mode gate (refinement of 069/P3/P10)
**Goal:** `command.execute.before` rejects `/state:build:*` when mode=teach; `tool.execute.before` rejects `mcp__state-teach__*` when mode=build.
**Depends on:** 070, 077, 099
**Requirements:** MODE-04
**Parallelizable:** yes
**Plans:** 1 plan

Plans:
- [ ] 100-01-PLAN.md — Cached mode reader + hook updates (command + tool mode gates)

#### Phase 101 — Daemon HTTP mode middleware (canonical gate)
**Goal:** Already partially in 053; extend with event-type-level validation (reject `state.concept.*` when mode=build).
**Depends on:** 053
**Requirements:** MODE-05
**Parallelizable:** no
**P0 pitfall:** P0-11
**Plans:** 1 plan

Plans:
- [ ] 101-01-PLAN.md — Event-type prefix sets + extraction helper + middleware validation + tests

#### Phase 102 — Python import-graph lint (CI)
**Goal:** Ruff plugin or custom script; fails if `state.build.*` imports `state.teach.*` or vice versa.
**Depends on:** 001
**Requirements:** MODE-06, TST-07
**Parallelizable:** yes
**Plans:** 1 plan

Plans:
- [ ] 102-01-PLAN.md — Core import_lint module (ast-based) + comprehensive test suite

#### Phase 103 — CLI: `state mode init build|teach|both` + `state mode set`
**Goal:** Typer commands; init bootstraps subtree + mode.json; set validates + reloads.
**Depends on:** 097, 098
**Requirements:** MODE-07
**Parallelizable:** yes

#### Phase 104 — Mode activation event (`state.mode.activated`)
**Goal:** Emit event on mode change; SSE fan-out triggers MCP reload.
**Depends on:** 099, 004
**Requirements:** MODE-03, MODE-05
**Parallelizable:** no

#### Phase 105 — Cross-mode leakage regression suite
**Goal:** P0-11 test suite: attempt every illegal combination, assert rejection at canonical gate.
**Depends on:** 097..P8
**Requirements:** (verifier; TST-08)
**Parallelizable:** no (final)

---

