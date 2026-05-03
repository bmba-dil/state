# Research Synthesis — `state`

**Researched:** 2026-04-22 • **Confidence:** HIGH on stack + opencode surface + auth; MEDIUM on teach-mode internals + sequencing granularity

This synthesis distills four research files so the roadmapper can start shaping the Arc DAG without re-reading the primary sources:

- [STACK.md](./STACK.md) — Python + opencode plugin stack, version floors, rejected alternatives
- [FEATURES.md](./FEATURES.md) — 85 GSD commands, 26 modules, 33 subagents, 11 hooks, 10 AOL workflows, 4 modes, 7 personalities, 60+ skills — each with disposition
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 6-process topology, 9-hook wiring, two MCP servers, build + teach kernels, SQLite + SyncEvent dual-write
- [PITFALLS.md](./PITFALLS.md) — 20 surfaces, 16 P0 release blockers, plus P1/P2 detail

---

## 1. TL;DR

1. `state` is six physical artifacts: **state-daemon** (always-on), **state-worker** (per-session), **state-build** + **state-teach** (sibling MCP servers), **@state/opencode-plugin** (one TS bundle: hook shim + SolidJS TUI), and the **.state/** on-disk artifacts (dual-write events.sqlite + opencode SyncEvent). Build and Teach share the kernel, silo everything else.
2. The stack is **load-bearing and prescriptive**: Python 3.12+, `mcp>=1.27.0` (matches opencode's TS SDK 1.27.1), `litellm>=1.80.0` + `anthropic>=0.80.0` escape-hatch, `pygit2>=1.19.2`, `pydantic>=2.13.2`, `aiosqlite>=0.22.1`, `filelock>=3.20.3` (CVE floor), `pluggy>=1.6.0`, `httpx>=0.28.1`. `uv` + `uv_build` for packaging. Plugin matches opencode's catalog byte-for-byte (bun 1.3.13, typescript 5.8.2, effect 4.0.0-beta.48, zod 4.1.8, solid-js 1.9.10).
3. **Five auth methods ship day-one** (Anthropic OAuth stealth, Gemini CLI, Antigravity, Copilot device-code, API keys). The Anthropic stealth path alone carries 8 of the 16 P0 pitfalls — it's the tallest release blocker in the whole project.
4. The full opencode hook surface (9 hooks: `chat.message`, `tool.execute.before/after`, `permission.ask`, `event`, `experimental.chat.system.transform`, `experimental.session.compacting`, `chat.params`, `command.execute.before`, `shell.env`) is wired from day one. Each hook wiring is a first-class Slice per PROJECT.md.
5. Planning is **four tiers** (Arc → Phase → Slice → Step), Step owns the full discuss/plan/execute/verify cycle, Slice is the concurrency unit (one worktree per Slice), Arc/Phase are scope containers. The DAG scheduler is **~300 LOC of pure Python** — no Prefect/Dask/Airflow/NetworkX.
6. Research consolidates **27 candidate Arcs** (see §5). Confidence is HIGH on component-boundary Arcs and feature coverage. Complexity skews heavy: ~6 XL, ~10 L, rest M/S.
7. Under-planning is the explicit failure mode. Expected roadmap output: 20+ Arcs, 60–100+ Phases, hundreds of Slices.

---

## 2. Stack Commitments (load-bearing pins)

| Layer | Pin | Why load-bearing |
|---|---|---|
| Runtime | CPython **3.12.0+** | Project mandate; TaskGroup semantics |
| MCP SDK | `mcp>=1.27.0` | Matches opencode's `@modelcontextprotocol/sdk@1.27.1` protocol version |
| Provider routing | `litellm>=1.80.0` + `anthropic>=0.80.0` | Anthropic direct SDK escape for extended thinking + fine-grained cache-control; **OAuth stealth never routes through litellm** |
| Git/worktree | `pygit2>=1.19.2` | libgit2 wheels; fallback when opencode worktree service absent |
| Data/async | `pydantic>=2.13.2`, `orjson>=3.11.8`, `aiosqlite>=0.22.1`, `httpx>=0.28.1` | Shared httpx client across daemon |
| Locking | `filelock>=3.20.3` | **CVE-2026-22701 floor** — do not float below |
| Plugins | `pluggy>=1.6.0` | Extension points inside daemon |
| Auth libs | `google-auth>=2.35`, `google-auth-oauthlib>=1.2`, `cryptography>=43.0` | Gemini + Antigravity OAuth |
| Packaging | `uv>=0.5.0` + `uv_build` | Default; `hatchling` fallback only if C deps demand |
| CLI | `typer>=0.15` + `rich>=13.9` | Typed CLI |
| Observability | `structlog>=25.1` | OpenTelemetry **deferred to v2** |
| Opencode plugin | bun **1.3.13**, typescript **5.8.2**, effect **4.0.0-beta.48**, zod **4.1.8**, solid-js **1.9.10**, @opentui/{core,solid} **0.1.99**, ulid **3.0.1**, remeda **2.26.0**, oxlint **1.60.0**, prettier **3.6.2** (semi:false, printWidth:120) | Plugin runs inside opencode's runtime |

Testing: `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` + `hypothesis>=6.120` + `pytest-httpx>=0.35` + `freezegun>=1.5`. E2E via spawned bun opencode binary pinned in `resources/opencode-version.txt`.

**Explicit rejects:** Prefect/Dask/Airflow, LangChain/LangGraph, SQLAlchemy/Alembic, GitPython, NetworkX, Textual (primary TUI), FastAPI (primary daemon), Poetry, AnyIO/Trio, third-party `fastmcp`, tiktoken.

---

## 3. Table Stakes (day-one MUST ship)

- **Dual-write event store** — `.state/events.sqlite` is truth; opencode `SyncEvent` derived. Daemon is the only writer. WAL, `synchronous=NORMAL/FULL`, commit-then-emit.
- **All five auth methods** — Anthropic OAuth stealth (headers `user-agent: claude-cli/...`, `x-app: cli`, `anthropic-beta: claude-code-20250219,oauth-2025-04-20,...`; PKCE verifier = OAuth `state`; client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e`; Bearer for `sk-ant-oat*`), Gemini CLI OAuth, Antigravity OAuth, Copilot device-code, API keys. Multi-cred round-robin with filelock-guarded refresh.
- **Two independent MCP servers** — `state-build` + `state-teach`, each ≤15 tools with ≤80-token descriptions, mode-gated.
- **Single opencode plugin bundle** — `@state/opencode-plugin` exports `server` (9 hooks, ~300 LOC) + `tui` (sidebar, routes, dialogs, statusline).
- **Four-tier planning hierarchy** with typed `depends_on` edges (`blocks`/`soft`/`data`) and Step-owned discuss/plan/execute/verify cycle.
- **Pure-Python DAG scheduler** — reactive, per-Slice worktree concurrency, watchdog for TaskGroup cancellation bug (P0-16).
- **Per-Slice worktree** — opencode worktree service preferred, pygit2 fallback. Transactional bootstrap; GC for orphan locked worktrees.
- **Step + Slice snapshots** — content-addressed, via opencode `Snapshot.track/revert`. Prefix-only revert within Slice.
- **Mode enforcement, 6 layers** — `.state/mode.json` + MCP registration + plugin hook + command dispatch + daemon HTTP middleware (**canonical**) + Python import-graph lint.
- **Build kernel** — Step state machine + STEP.md frontmatter (goal, `verify_contract`, `depends_on`, `model_profile`, `snapshots`) + goal-backward verifier + Slice/Phase/Arc rollup + cross-tier integration verifier.
- **Teach kernel** — Kolb state machine (CE→RO→AC→AE), concept-graph projection, drill engine bound to opencode `question` tool, event-sourced mental-model projection, learning verifier.
- **Four teaching modes** as first-class Phases with mode-selector (PRIMM <30% → Scaffolded 30–50% → Socratic 50–70% → Constructivist 70–80%), drop-to-simpler on frustration.
- **Security baseline** — path-traversal + prompt-injection + shell-meta + JSON + regex-DoS guards; `auth.json` chmod 0600 verified on every read; root-logger token redactor.
- **TUI extensions** — build dashboard, teach dashboard, DAG viewer (shared), drill UI, statusline, toasts, gray-area decision dialog.
- **Docs + test infra + packaging** — `uvx state install` auto-registers plugin + MCP servers.

---

## 4. Differentiators

| Differentiator | Why it matters |
|---|---|
| **Build + Teach fused** | Shared kernel with siloed mode logic; nobody else ships both. |
| **4-tier Arc/Phase/Slice/Step with Step-owned cycle** | GSD's 2-tier is too coarse + implicitly serial. |
| **DAG concurrency native** | Roadmaps are DAGs not lists; one-worktree-per-Slice parallelism. |
| **Opencode as primary host** | Mid-session provider switching, typed bus events, client/server split, 9 hook types. |
| **Five-auth day-one incl. Anthropic OAuth stealth** | Pro/Max users are primary audience. |
| **Cross-host portability via MCP** | Claude Code / Gemini CLI / Qwen Code get reduced-UX access. |
| **Event-sourced everything** | STATE.md / MENTAL-MODEL.json are projections; replay + forensics + cross-session restore. |
| **Personalities × modes orthogonal** | 4 modes × 7 personalities × subject compose cleanly. |
| **Python as user-facing learning surface** | Thomas learns via building; cardinal. |

---

## 5. Arc Candidate Rollup — 27 Arcs

| # | Arc | Source(s) | Opencode surface | GSD/AOL source | Predecessors | Complexity |
|---|---|---|---|---|---|---|
| A1 | **Event store foundation** (SQLite + SyncEvent dual-write) | ARCH, FEATURES §2, §10 | `sync/`, `storage/` | state.cjs | — | L |
| A2 | **Auth coverage — 5 methods + multi-cred** | ARCH, FEATURES §10, PITFALLS S1–5 | `auth/index.ts`, plugin `AuthHook` | claude-oauth.md + gsd2-auth-analysis.md | — | L |
| A3 | **Provider routing + model profiles** | ARCH, FEATURES §2, §10 | `chat.params`, `chat.headers`, `provider` hook | model-profiles.cjs | A2 | L |
| A4 | **Worktree + snapshot service** | ARCH, FEATURES §11 | `worktree/`, `snapshot/` | — (new) | — | M |
| A5 | **DAG scheduler** (~300 LOC pure Python) | ARCH, FEATURES §10, §11 | — (standalone) | — (new) | A1 | L |
| A6 | **State daemon + HTTP + SSE + mode middleware** | ARCH, FEATURES §10 | opencode HTTP API, SSE bus | — (new) | A1, A2 | L |
| A7 | **Per-session worker** | ARCH | opencode HTTP session ops | — (new) | A6 | M |
| A8 | **Plugin server hooks** (all 9) | ARCH, FEATURES §4 | `plugin/src/index.ts:222-333` | hooks/*.js,*.sh | A7 | L |
| A9 | **Plugin TUI bundle** | ARCH, FEATURES §11 | `plugin/src/tui.ts` | gsd-statusline.js | A7 | L |
| A10 | **TUI DAG viewer** | ARCH, FEATURES §12 | `route.register`, `ui.Slot` | — (new) | A8, A9 | M |
| A11 | **Mode enforcement** (6 layers) | ARCH, FEATURES §11, PITFALLS S7, S16 | `config`, `command.execute.before`, `tool.execute.before` | — (new) | A6, A8 | M |
| A12 | **state-build MCP server** | ARCH, FEATURES §11 | `mcp/index.ts` | — (new) | A11 | M |
| A13 | **state-teach MCP server** | ARCH, FEATURES §11 | `mcp/index.ts` | — (new) | A11 | M |
| A14 | **Build kernel — Step FSM + verifiers** | ARCH, FEATURES §1, §2, §3, §11 | `tool.execute.after`, `system.transform`, `task` | gsd-executor + gsd-verifier + verify.cjs | A5, A12 | XL |
| A15 | **Build commands — plan/execute/verify/ship** | ARCH, FEATURES §1.2 | `command.*`, `task`, `Snapshot` | plan-phase, execute-phase, verify-work, ship | A14, A4 | L |
| A16 | **Build commands — GSD ports** | FEATURES §1.3–1.9 | `task` + built-ins | 50+ GSD commands | A15 | XL |
| A17 | **Build TUI** | ARCH, FEATURES §11 | `sidebar_content`, `route.register` | gsd-statusline.js | A9, A14 | M |
| A18 | **Teach kernel — Kolb + concepts + mental-model** | ARCH, FEATURES §5, §8 | `system.transform`, `tool.execute.after` | aol-concept-teacher + workflows/teach.md | A5, A13 | L |
| A19 | **Teach drill engine** | ARCH, FEATURES §8 | `question/index.ts` | aol drill prepare/verify | A18 | M |
| A20 | **Teach modes** (PRIMM + Scaffolded + Socratic + Constructivist + selector) | FEATURES §6 | `chat.params` | skills/{primm,scaffolded,socratic,constructivist}.md | A18 | XL |
| A21 | **Teach personalities + teaching-style** | FEATURES §7 | `chat.params`, `chat.headers` | personalities/*.md (7) + workflows/style.md | A18 | M |
| A22 | **Scaffolding-mentor + coding-partner** | FEATURES §8 | `permission.ask`, `task` | aol-scaffolding-mentor + coding-partner | A20, A21 | L |
| A23 | **Teach TUI** | ARCH, FEATURES §11 | `route.register`, `ui.Prompt`, `ui.DialogSelect` | workflows/state.md | A9, A18 | M |
| A24 | **Subject authoring + 4-gate promoter** | FEATURES §5 | — | workflows/build-subject.md | A18 | M |
| A25 | **Migration & import** (GSD `.planning/`, AOL `.aol/` → `.state/`) | FEATURES §11 | — | from-gsd2.md (reversed), AOL | A1, A11 | M |
| A26 | **Portability shims** (Claude Code / Gemini / Qwen — MCP-only) | ARCH, FEATURES §12 | — | — | A12, A13 | L |
| A27 | **Release & packaging** | ARCH, FEATURES §10, §11 | `cfg.skills.urls` | gsd update | most of A1–A23 | M |

**Roadmapper may also split/fold:** Event replay/forensics CLI, Knowledge graph (graphify + ingest-docs), Documentation (threaded vs standalone), Test infrastructure, Verification split, Eval infrastructure.

**Arc DAG hard edges:**

```
A1 ─┬─► A5 ─┬─► A14 ─► A15 ─► A16
    │       └─► A18 ─┬─► A19
    │                ├─► A20 ─► A22
    │                ├─► A21 ─► A22
    │                └─► A24
    └─► A6 ─► A7 ─┬─► A8 ─┬─► A10 ─► (A17, A23)
                  │       └─► A17, A23
                  └─► A9 ─► A10
A2 ─► A3 (and A6)
A2, A6 ─► A11 ─► A12 ─► A14
A2, A6 ─► A11 ─► A13 ─► A18
A4 ─► A15
A25 soft-depends on A1, A11
A26 soft-depends on all build + teach Arcs
A27 soft-depends on most everything
```

---

## 6. P0 Pitfalls — Release-Blocker Rollup

| # | Pitfall | Surface | Arc(s) |
|---|---------|---------|--------|
| P0-1 | Missing `user-agent: claude-cli/<version>` header | Anthropic OAuth stealth | A2, A3 |
| P0-2 | Missing `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…` header | Anthropic OAuth stealth | A2 |
| P0-3 | Missing `x-app: cli` header | Anthropic OAuth stealth | A2 |
| P0-4 | Using `x-api-key` instead of Bearer for `sk-ant-oat*` | Anthropic OAuth stealth | A2 |
| P0-5 | Registering fresh OAuth client instead of `9d1c250a-e61b-44d9-88ed-5944d1962f5e` | Anthropic OAuth stealth | A2 |
| P0-6 | Dual-refresh race invalidates live token | Refresh lock | A2 |
| P0-7 | `expires_in` verbatim (no 5-min buffer) | Anthropic OAuth stealth | A2 |
| P0-8 | PKCE `state` not reused as verifier | Anthropic OAuth stealth | A2 |
| P0-9 | SQLite event-sequence non-monotonic after crash → replay breaks | Dual-write | A1 |
| P0-10 | Orphan locked worktrees fill disk | Worktree | A4, A6 |
| P0-11 | Mode isolation leakage | Cross-mode | A11 |
| P0-12 | MCP tool-name collision / cross-mode invocation | MCP | A11, A12, A13 |
| P0-13 | `auth.json` world-readable | Auth vault | A2 |
| P0-14 | OAuth refresh writes plaintext tokens to log when debug=true | Secret leakage | A2, observability |
| P0-15 | Stale pid-file refuses daemon start | Daemon | A6 |
| P0-16 | TaskGroup silently swallows `CancelledError`, deadlocking scheduler | Py 3.12 asyncio | A5 |

All 16 need explicit regression tests before v1. A2 carries 9 of them (P0-1..P0-8 + P0-13); give it a dedicated header-capture test Phase.

---

## 7. Open Questions for the Roadmapper

1. **Verification Arc granularity** — keep inside A14 (current) vs split (a) A14 + rollup/cross-tier Arc, or (b) full split (Step / Rollup / Cross-tier / Eval-audit).
2. **Mode-runtime factoring** — shared plumbing (selector, drop rules, Kolb runner, observation emission) lives (a) as a cross-cutting Phase before the four mode Phases, (b) duplicated inside each, or (c) in A18 (Teach kernel).
3. **Concept-teacher ↔ modes direction** — AOL: concept-teacher invokes modes. Cleaner state shape: modes invoke concept-teacher. Roadmapper picks — affects A18/A20/A22 boundaries.
4. **Docs Arc timing** — threaded per-Arc (living docs) vs a single late Arc.
5. **Test-infra Arc timing** — same question; thoroughness-philosophy favors threaded.
6. **Workstreams ↔ Arcs overlap** — collapse, keep both, or make workstreams a projection of Arc metadata.
7. **Knowledge-graph Arc fit** — own Arc (Kuzu/DuckDB — L) vs folded into Codebase Intelligence.
8. **MVP personality count** — 3 of 7 (FEATURES-suggested) vs full 7 day-one.
9. **Quick/Sketch/Spike collapse** — three Arcs vs one "Ad-hoc" Arc with modes as Slices.
10. **Eval infrastructure timing** — MVP (threaded into verifiers) vs post-MVP.
11. **MVP scope boundary** — especially host portability (A26): FEATURES "required before GA" vs PROJECT.md "deprioritized."

---

## 8. Watch Out For — Top 10

1. **Anthropic OAuth stealth header trio** (P0-1/2/3) — version-lock doc + captured-header regression test; **OAuth never through litellm** (P1-38).
2. **Refresh-lock double-check** (P0-6) — re-read `auth.json` inside filelock; 10s acquire + 15s HTTP timeouts.
3. **Events SQLite-first, SyncEvent-after** (P0-9) — startup reconciliation; deterministic payloads only (no `datetime.now()` in handlers).
4. **TaskGroup CancelledError swallow** (P0-16) — scheduler watchdog + nested-TaskGroup regression test.
5. **Orphan worktrees GC** (P0-10) — inspect `.git/worktrees/*/locked`; nightly daemon GC; never silently swallow `remove` errors.
6. **Mode isolation at daemon middleware** (P0-11/12) — canonical gate is daemon-side; `mode` field on every event; projector filters.
7. **MCP tool-budget cap** (P1-10) — ≤15 tools per server, ≤80 tokens per description; `state dev tool-budget` command.
8. **Daemon pid-file with `start_time_ns`** (P0-15) — `/proc/<pid>/stat` verification; socket path `$XDG_RUNTIME_DIR/state-<hash>.sock`.
9. **auth.json vault hygiene** (P0-13/14) — `os.open(..., 0o600)` + `os.fchmod`; root-logger token redactor.
10. **Gemini OAuth client_secret in plaintext** (P1-3) — do NOT base64/XOR; comment Desktop-OAuth PKCE rationale.

Also: drill prompt ≤3000 tokens (P1-33), structured-only observations (P1-34), plugin/daemon version header (P1-21), Google refresh-token rotation persistence (P2-2), pydantic `extra = "forbid"` on all specs (P2-16).

---

## 9. Suggested Build Order

**Tier 1 — Foundation** (parallel): A1 Event store, A2 Auth (start early — tallest P0 concentration), A3 Provider routing, A4 Worktree+snapshot, A5 DAG scheduler.

**Tier 2 — Kernels**: A6 Daemon, A7 Worker, A8 Plugin hooks, A9 Plugin TUI bundle, A10 DAG viewer, A11 Mode enforcement, A12 state-build skeleton, A13 state-teach skeleton.

**Tier 3 — Domain kernels** (build + teach parallel):
- Build: A14 Step FSM + verifiers, A15 plan/execute/verify/ship, A16 GSD ports, A17 Build TUI.
- Teach: A18 Kolb + concepts + mental-model, A19 Drill engine, A20 Four modes + selector, A21 Personalities + style, A22 Scaffolding/coding-partner, A23 Teach TUI, A24 Subject authoring.

**Tier 4 — Polish & portability**: A25 Migration, A26 Portability shims, A27 Release & packaging.

Test-infra + docs threading is open (see §7); if threaded, every Arc grows `-tests` + `-docs` tail-Slices.

---

## 10. Confidence & Gaps

| Area | Confidence | Notes |
|---|---|---|
| Stack pins | HIGH | Validated against opencode `package.json` catalog + PyPI |
| Opencode hook/TUI/bus/task/question/snapshot/worktree surface | HIGH | Source read directly |
| Auth 5-method + stealth headers | HIGH | claude-oauth.md + gsd2-auth-analysis.md verbatim |
| GSD command/module/agent/hook inventory | HIGH | 85 + 26 + 33 + 11 files enumerated |
| Teaching modes breakdown | HIGH | All four skill files read; Slice counts from numbered rules |
| Personalities | HIGH | All 7 read; trivial port |
| Event store + daemon architecture | HIGH | Topology + taxonomy + SQL schema concrete |
| Kolb/scaffold/mastery math | MEDIUM | Exact `drill verify` Bayesian update formula not confirmed in sources read — flag A18/A19 deep-dive |
| GSD state-machine internals (bin/lib/*.cjs function-level) | MEDIUM | Top-level roles enumerated; PROJECT.md mandates redesign |
| Arc granularity (27) | MEDIUM | Component-boundary is HIGH; XL Arcs may split |
| Exotic cross-compat skills | LOW | Default `keep`; low stakes |

**Gaps for roadmap-time research:**
- AOL `aol drill verify` internals (grader signatures, mastery update formula) — feeds A18/A19.
- `TuiPluginInstallOptions` + opencode plugin install-discovery mechanics — feeds A27.
- Interaction of opencode's `experimental.primary_tools` whitelist with `mcp__state-*__` names — A12/A13 compatibility test.
- GSD's current hook-adapter interface-set confirmation (not porting) — feeds A8.
- litellm's exact 1.80+ Anthropic beta-flag forwarding — capture-and-assert at A3 research.

---

## 11. Sources

- PROJECT.md
- `state-inputs/opencode/` (especially `packages/plugin/src/{index,tui}.ts`, `packages/opencode/src/{sync,storage,mcp,auth,task,question,permission,snapshot,worktree,skill,command}/`)
- `state-inputs/claude-oauth.md` (load-bearing)
- `state-inputs/gsd2-auth-analysis.md`
- `state-inputs/opencode-extension-surface.md` + `opencode-integration-analysis.md`
- `state-inputs/get-shit-done/` (commands, bin/lib, agents, hooks)
- `state-inputs/gsd-2pi-codebase-analysis/{10-python-rebuild-mapping,11-architecture-discussion}.md`
- `~/.claude/agent-of-learning/` (workflows, personalities, skills, learner JSON)
- `~/.claude/skills/` (60+ cross-compat enumerated)
- PyPI/GitHub releases for version floors; filelock CVE-2026-22701 advisory
