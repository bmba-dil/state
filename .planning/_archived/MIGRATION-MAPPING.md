# Migration Mapping: M-A&lt;N&gt;.P&lt;M&gt; → v&lt;N&gt; + NNN

**Status:** Approved. Executing now.
**Date:** 2026-04-22
**GSD compatibility:** native `/^v\d/` milestone prefix — zero patching required.
**Config flag:** `"concurrent": true` in `.planning/config.json` (enables milestone-scoped layout).

---

## Rule

- **Milestone ID:** `M-A<N>` → `v<N>` (native GSD naming; e.g. `M-A01` → `v1`, `M-A27` → `v27`)
- **Phase ID:** Flat 3-digit global `NNN`, assigned in ROADMAP order. M-A1.P1 = 001, last phase of M-A27 = 256.
- **Phase slug:** kebab-case of the portion after `— ` in the ROADMAP `#### Phase` heading.
- **Plan file naming (inside phase dir):** `NNN-MM-PLAN.md` (e.g. `001-01-PLAN.md`).

---

## Milestone-level summary (27 milestones, 256 phases)

| Old   | New  | Name                                            | Phase range | Count |
|-------|------|-------------------------------------------------|-------------|-------|
| M-A01 | v1   | Event Store Foundation                          | 001–010     | 10    |
| M-A02 | v2   | Auth Coverage (5 Methods + Multi-Cred)          | 011–022     | 12    |
| M-A03 | v3   | Provider Routing + Model Profiles               | 023–031     |  9    |
| M-A04 | v4   | Worktree + Snapshot Service                     | 032–040     |  9    |
| M-A05 | v5   | DAG Scheduler                                   | 041–049     |  9    |
| M-A06 | v6   | State Daemon (HTTP + SSE + Mode Middleware)     | 050–059     | 10    |
| M-A07 | v7   | Per-Session Worker                              | 060–067     |  8    |
| M-A08 | v8   | Plugin Server Hooks (all 9)                     | 068–079     | 12    |
| M-A09 | v9   | Plugin TUI Bundle                               | 080–088     |  9    |
| M-A10 | v10  | TUI DAG Viewer                                  | 089–096     |  8    |
| M-A11 | v11  | Mode Enforcement (6 Layers)                     | 097–105     |  9    |
| M-A12 | v12  | state-build MCP Server (skeleton)               | 106–114     |  9    |
| M-A13 | v13  | state-teach MCP Server (skeleton)               | 115–123     |  9    |
| M-A14 | v14  | Build Kernel: Step FSM + Verifiers              | 124–134     | 11    |
| M-A15 | v15  | Build Core Commands (plan/execute/verify/ship)  | 135–144     | 10    |
| M-A16 | v16  | Build GSD Command Ports + Net-New               | 145–158     | 14    |
| M-A17 | v17  | Build TUI Extensions                            | 159–166     |  8    |
| M-A18 | v18  | Teach Kernel: Kolb + Concepts + Mental-Model    | 167–177     | 11    |
| M-A19 | v19  | Teach Drill Engine                              | 178–186     |  9    |
| M-A20 | v20  | Teach Four Modes + Selector                     | 187–197     | 11    |
| M-A21 | v21  | Teach Personalities + Teaching Style            | 198–205     |  8    |
| M-A22 | v22  | Scaffolding-Mentor + Coding-Partner             | 206–214     |  9    |
| M-A23 | v23  | Teach TUI Extensions                            | 215–222     |  8    |
| M-A24 | v24  | Subject Authoring + 4-Gate Promoter             | 223–230     |  8    |
| M-A25 | v25  | Migration & Import                              | 231–238     |  8    |
| M-A26 | v26  | Portability Shims                               | 239–246     |  8    |
| M-A27 | v27  | Release & Packaging                             | 247–256     | 10    |

Total: **256 phases** ✓ (matches STATE.md target).

---

## Directory transformations

```
.planning/Milestones/M-A01-event-store-foundation/  →  .planning/milestones/v1/
.planning/Milestones/M-A02-auth-coverage/           →  .planning/milestones/v2/
…
.planning/Milestones/M-A27-release-and-packaging/   →  .planning/milestones/v27/
```

Inside each `milestones/v<N>/`:
```
milestones/v1/
├── ROADMAP.md              # extracted from monolithic — v1's phases only, renumbered 001–010
├── REQUIREMENTS.md         # REQ-IDs referenced by v1's phases
├── STATE.md                # per-milestone status
└── phases/
    ├── 001-project-scaffolding/          (empty — ready for /gsd:plan-phase 001)
    ├── 002-pydantic-event-schema/
    └── …010-event-store-verifier/
```

---

## Top-level `.planning/` changes

| File                 | Action                                                          |
|----------------------|-----------------------------------------------------------------|
| `ROADMAP.md`         | Copy to `_archived/ROADMAP.md`; rewrite as coordinator stub pointing to `milestones/v<N>/ROADMAP.md` |
| `REQUIREMENTS.md`    | Copy to `_archived/REQUIREMENTS.md`; rewrite as REQ-ID → milestone index |
| `MILESTONES.md`      | **New.** 27-row index                                           |
| `Milestones/` (old)  | Delete after content moved                                      |
| `REVIEW-ROADMAP.md`  | Rewrite `M-A<N>.P<M>` refs → new IDs                            |
| `DEBT.md`            | Rewrite phase refs                                              |
| `PROJECT.md`         | Rewrite refs (spot-check)                                       |
| `STATE.md`           | Rewrite refs; keep 0/256, 0/27 counters                         |
| `config.json`        | Set `"concurrent": true`                                        |

---

## depends_on rewrites

Every `**Depends on:**` line gets its `M-A<N>.P<M>` refs translated via the mapping table.

| Before                                    | After                          |
|-------------------------------------------|--------------------------------|
| `**Depends on:** (none)`                  | unchanged                      |
| `**Depends on:** M-A1.P1`                 | `**Depends on:** 001`          |
| `**Depends on:** M-A5.P5, M-A1.P4`        | `**Depends on:** 045, 004`     |

---

## Grep assertion (post-migration)

```
rg 'M-A\d+\.P\d+' .planning/ --glob '!_archived/**' --glob '!_archived/*'
```

Must return 0 matches.
