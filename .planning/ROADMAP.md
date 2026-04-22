# ROADMAP: state

**Created:** 2026-04-22
**Core Value:** A single polyglot engine lets me ship software (build mode) and learn new skills (teach mode) with the same deep tooling — event-sourced history, dependency-DAG concurrency, cross-host portability.

**Granularity:** fine (research/config.json)
**Parallelization:** true — milestones and phases execute concurrently per explicit `Depends on:` DAG
**Structural note:** GSD uses milestones → phases (this document). The **product** (`state`) uses Arc → Phase → Slice → Step, which is Thomas's product vocabulary and is built inside the phases themselves. One GSD milestone == one product Arc. A GSD phase DELIVERS capability into one or more product-runtime Slices — but is not itself a Slice object in `.state/`.

---

## Scope at a Glance

| Metric | Value |
|---|---|
| Milestones (= product Arcs) | **27** |
| Phases total | **256** |
| v1 requirements mapped | **221 / 221 (100%)** |
| Tier 1 (Foundation) milestones | 5 (parallel) |
| Tier 2 (Kernel & Plumbing) milestones | 8 |
| Tier 3a (Build domain) milestones | 4 |
| Tier 3b (Teach domain) milestones | 7 |
| Tier 4 (Polish & portability) milestones | 3 |
| P0 pitfalls owned in v1 | 16 / 16 |

---

## Milestones (Summary Checklist)

### Tier 1 — Foundation (parallel — no internal deps after scaffolding)

- [ ] **M-A1 — Event Store Foundation** — Dual-write SQLite + SyncEvent event store with deterministic replay
- [ ] **M-A2 — Auth Coverage (5 methods)** — All five auth methods with filelock-guarded refresh and token redaction
- [ ] **M-A3 — Provider Routing + Model Profiles** — litellm default + Anthropic SDK escape hatch with OAuth bypass
- [ ] **M-A4 — Worktree + Snapshot Service** — Per-Slice worktrees with Step/Slice snapshots and GC
- [ ] **M-A5 — DAG Scheduler** — Pure-Python reactive scheduler with TaskGroup watchdog

### Tier 2 — Kernel & Plumbing (depends on Tier 1)

- [ ] **M-A6 — State Daemon (HTTP + SSE + mode middleware)** — Always-on user service with canonical mode gate
- [ ] **M-A7 — Per-Session Worker** — Session-scoped worker bridging plugin and daemon
- [ ] **M-A8 — Plugin Server Hooks (9 hooks)** — Full opencode hook surface wired
- [ ] **M-A9 — Plugin TUI Bundle** — SolidJS TUI extensions (sidebar, statusline, toasts)
- [ ] **M-A10 — TUI DAG Viewer** — Shared DAG visualization route
- [ ] **M-A11 — Mode Enforcement (6 layers)** — Physical + runtime + static enforcement of exclusive modes
- [ ] **M-A12 — state-build MCP Server (skeleton)** — Mode-gated MCP server with 15-tool budget
- [ ] **M-A13 — state-teach MCP Server (skeleton)** — Mode-gated MCP server with 15-tool budget

### Tier 3a — Build Domain Kernel (parallel with Tier 3b)

- [ ] **M-A14 — Build Kernel: Step FSM + Verifiers** — Step state machine, goal-backward verifier, rollups
- [ ] **M-A15 — Build Core Commands (plan/execute/verify/ship)** — The canonical Build-mode cycle
- [ ] **M-A16 — Build GSD Command Ports + Net-New Product-Hierarchy Commands** — GSD ports + net-new product-hierarchy scaffolding commands (new-arc/new-phase/new-slice/insert-slice/add-phase/remove-phase/multi-arc)
- [ ] **M-A17 — Build TUI Extensions** — Build dashboard, Step detail, commit browser, gray-area dialog

### Tier 3b — Teach Domain Kernel (parallel with Tier 3a)

- [ ] **M-A18 — Teach Kernel: Kolb + Concepts + Mental Model** — Concept graph, Kolb FSM, event-sourced mental model
- [ ] **M-A19 — Teach Drill Engine** — opencode `question`-bound drill prepare/verify with Bayesian mastery
- [ ] **M-A20 — Teach Four Modes + Selector** — PRIMM/Scaffolded/Socratic/Constructivist + mastery-based router
- [ ] **M-A21 — Teach Personalities + Teaching Style** — 7 AOL personalities + 7-dimension style config
- [ ] **M-A22 — Scaffolding-Mentor + Coding-Partner** — Two first-class teach workflows for project building
- [ ] **M-A23 — Teach TUI Extensions** — Teach dashboard, drill UI, mental-model viewer, session timeline
- [ ] **M-A24 — Subject Authoring + 4-Gate Promoter** — Conversational subject + concept-graph authoring

### Tier 4 — Polish & Portability

- [ ] **M-A25 — Migration & Import** — from-gsd + from-aol importers with replay preservation
- [ ] **M-A26 — Portability Shims** — Claude Code / Gemini CLI / Qwen Code MCP-only shims
- [ ] **M-A27 — Release & Packaging** — pyproject + uvx installer + opencode plugin bundle + updater

---

## Milestone DAG (Dependencies)

```
Tier 1 (parallel-safe starts; M-A3 soft-after M-A2 for auth; M-A5 reacts to M-A1 events):
  M-A1 ─┐
  M-A2 ─┤
  M-A3 ─┤ (soft-after M-A2 for auth headers)
  M-A4 ─┤
  M-A5 ─┘ (reactive to M-A1 events)

Tier 2:
  M-A1, M-A2           ──► M-A6 ──► M-A7 ──┬─► M-A8 ──┐
                                            └─► M-A9 ──┴──► M-A10
  M-A6, M-A8           ──► M-A11 ──┬──► M-A12
                                    └──► M-A13
Tier 3a (build):
  M-A5, M-A12          ──► M-A14 ──► M-A15 (and M-A4 ──► M-A15) ──► M-A16
  M-A9, M-A14          ──► M-A17

Tier 3b (teach):
  M-A5, M-A13          ──► M-A18 ──┬──► M-A19
                                    ├──► M-A20 ──► M-A22
                                    ├──► M-A21 ──► M-A22
                                    └──► M-A24
  M-A9, M-A18          ──► M-A23

Tier 4:
  M-A1, M-A11          ──► M-A25 (soft)
  M-A12, M-A13         ──► M-A26
  most-of-M-A1..M-A24  ──► M-A27
```

<!-- TODO: tighten phase-level depends-on edges (M-A11.P3/P4 → M-A8 phase specificity; M-A9.P5 → M-A6/M-A7 split; M-A17 → M-A14.P10 soft-dep) before M-A5 wave planning. See REVIEW-ROADMAP.md §5b/§5c. -->

### Critical Path

**A1 → A6 → A7 → A8 → A11 → A12 → A14 → A15 → A16 → A27** (Build critical path)

**A1 → A6 → A7 → A8 → A11 → A13 → A18 → A20 → A22 → A27** (Teach critical path longest)

### Parallel-Safe Milestone Groups

| Wave | Parallel-safe group |
|------|---------------------|
| W1 | M-A1, M-A2, M-A4 |
| W1-prep | M-A3 (after M-A2 creds), M-A5 (after M-A1 events) |
| W2 | M-A6 (after A1+A2) |
| W3 | M-A7 (after A6) |
| W4 | M-A8, M-A9 (after A7) |
| W5 | M-A10 (after A8+A9), M-A11 (after A6+A8) |
| W6 | M-A12, M-A13 (after A11; parallel) |
| W7 | M-A14 (after A5+A12), M-A18 (after A5+A13) — **build and teach kernels start simultaneously** |
| W8a | M-A15 (after A14+A4), M-A19/M-A20/M-A21/M-A24 (after A18; all parallel) |
| W8b | M-A17 (after A9+A14), M-A23 (after A9+A18) |
| W9 | M-A16 (after A15), M-A22 (after A20+A21) |
| W10 | M-A25 (after A1+A11), M-A26 (after A12+A13 skeleton complete) |
| W11 | M-A27 (after most) |

### Tier boundaries

Tier 1 ends when M-A1..M-A5 all report `shipped`.
Tier 2 ends when M-A6..M-A13 all report `shipped`.
Tier 3 ends when M-A14..M-A24 all report `shipped` (Build + Teach kernels complete).
Tier 4 ends at M-A27 shipped — this is v1 release.

---

## Progress Table

| Milestone | Phases | Status | Started | Completed |
|---|---|---|---|---|
| M-A1. Event Store Foundation | 0/10 | Not started | - | - |
| M-A2. Auth Coverage | 0/12 | Not started | - | - |
| M-A3. Provider Routing | 0/9 | Not started | - | - |
| M-A4. Worktree + Snapshot | 0/9 | Not started | - | - |
| M-A5. DAG Scheduler | 0/9 | Not started | - | - |
| M-A6. State Daemon | 0/10 | Not started | - | - |
| M-A7. Per-Session Worker | 0/8 | Not started | - | - |
| M-A8. Plugin Server Hooks | 0/12 | Not started | - | - |
| M-A9. Plugin TUI Bundle | 0/9 | Not started | - | - |
| M-A10. TUI DAG Viewer | 0/8 | Not started | - | - |
| M-A11. Mode Enforcement | 0/9 | Not started | - | - |
| M-A12. state-build MCP | 0/9 | Not started | - | - |
| M-A13. state-teach MCP | 0/9 | Not started | - | - |
| M-A14. Build Kernel Step FSM | 0/11 | Not started | - | - |
| M-A15. Build Core Commands | 0/10 | Not started | - | - |
| M-A16. Build GSD Ports | 0/14 | Not started | - | - |
| M-A17. Build TUI | 0/8 | Not started | - | - |
| M-A18. Teach Kernel Kolb+Concepts | 0/11 | Not started | - | - |
| M-A19. Teach Drill Engine | 0/9 | Not started | - | - |
| M-A20. Teach Four Modes | 0/11 | Not started | - | - |
| M-A21. Teach Personalities + Style | 0/8 | Not started | - | - |
| M-A22. Scaffolding + Coding Partner | 0/9 | Not started | - | - |
| M-A23. Teach TUI | 0/8 | Not started | - | - |
| M-A24. Subject Authoring | 0/8 | Not started | - | - |
| M-A25. Migration & Import | 0/8 | Not started | - | - |
| M-A26. Portability Shims | 0/8 | Not started | - | - |
| M-A27. Release & Packaging | 0/10 | Not started | - | - |
| **TOTAL** | **0/256** | — | — | — |

---

# Milestone Details

---

## M-A1 — Event Store Foundation

**Version:** v0.1
**Goal:** Dual-write event store where `.state/events.sqlite` is authoritative truth and opencode SyncEvent is a derived mirror; replay is bit-identical across restarts and survives opencode being offline.
**Depends on:** (none — foundation)
**Tier:** 1
**Complexity:** L
**P0 pitfalls owned:** P0-9 (SQLite event-sequence non-monotonic after crash)

**Opencode surface extended:**
- `state-inputs/opencode/packages/opencode/src/sync/index.ts`
- `state-inputs/opencode/packages/opencode/src/sync/event.sql.ts`
- `state-inputs/opencode/packages/opencode/src/storage/`

**Source influence:**
- `state-inputs/get-shit-done/bin/lib/state.cjs` (intent — state machine persistence)
- `state-inputs/gsd-2pi-codebase-analysis/10-python-rebuild-mapping.md`
- `state-inputs/opencode-extension-surface.md` (bus + sync sections)

**.state/ artifacts written:**
- `.state/events.sqlite`, `.state/events.sqlite-wal`, `.state/events.sqlite-shm`
- `.state/migrations/0001_init.sql` (and onward — hand-rolled)

**MCP tool surface delivered:** (none — foundation package)

**Verifier:** Replay 10,000 synthetic events through the projector; assert identical `steps`/`slices`/`concepts` cache tables AND identical opencode SyncEvent feed; crash at random offsets and verify recovery converges to same projection.

**Requirements covered:** EVT-01, EVT-02, EVT-03, EVT-04, EVT-05, EVT-06, EVT-07, EVT-08

**Success criteria:**
1. User can `state events tail` and see every domain event emitted by the daemon in real time with mode filtering
2. User can kill the daemon mid-write, restart, and resume without event loss or sequence corruption
3. User can `state events replay --from <ulid>` and produce a byte-identical projection of steps/slices/concepts
4. User can run `state events export --format jsonl` to get a portable dump suitable for forensics
5. Developer can add a new event type by editing one pydantic schema file (`extra = "forbid"`) with no DB migration when payload fits existing columns

### Phases

#### Phase M-A1.P1 — Project scaffolding + pyproject + `state_core` package skeleton
**Goal:** Create the `state_core` package, `pyproject.toml` (pinning per STACK.md), `uv` workspace, base directory layout.
**Depends on:** (none)
**Requirements:** (foundational; no REQ-IDs directly — prerequisite)
**Parallelizable:** no (first phase)

#### Phase M-A1.P2 — Pydantic event schema for all 28+ event types (`state_core.schema`)
**Goal:** Define `EventEnvelope` and every `state.*` event with `extra = "forbid"`, including aggregate discriminator, ULID IDs, per-aggregate seq.
**Depends on:** M-A1.P1
**Requirements:** EVT-05, EVT-08
**Parallelizable:** yes with M-A1.P3

#### Phase M-A1.P3 — SQLite schema + numbered migrations (0001_init.sql)
**Goal:** Author `events`, `aggregate_seq`, `steps`, `slices`, `concepts`, `decisions`, `tool_calls`, `auth_rotations` tables per ARCHITECTURE §11.3; WAL mode, synchronous=NORMAL, full index set.
**Depends on:** M-A1.P1
**Requirements:** EVT-01, EVT-02
**Parallelizable:** yes with M-A1.P2

#### Phase M-A1.P4 — Writer task (single-writer aiosqlite + commit-then-emit)
**Goal:** Implement `EventStore.append()` with per-aggregate seq enforcement, monotonic guarantee, deterministic clock injection.
**Depends on:** M-A1.P2, M-A1.P3
**Requirements:** EVT-01, EVT-02, EVT-03, EVT-06
**Parallelizable:** no

#### Phase M-A1.P5 — SyncEvent mirror emitter
**Goal:** Implement post-commit SyncEvent emission over opencode HTTP (when reachable), marking `synced_to_opencode=1` per row.
**Depends on:** M-A1.P4
**Requirements:** EVT-01
**Parallelizable:** yes with M-A1.P6

#### Phase M-A1.P6 — Startup reconciliation (unsent-event replay to opencode)
**Goal:** On daemon start, find rows with `synced_to_opencode=0` and emit; handle opencode-unreachable with exponential backoff.
**Depends on:** M-A1.P4
**Requirements:** EVT-04
**Parallelizable:** yes with M-A1.P5

#### Phase M-A1.P7 — Monotonic seq crash-recovery (P0-9 regression test harness)
**Goal:** Add `fsync` discipline + recovery routine that detects and repairs gaps/duplicates in `aggregate_seq`; Hypothesis property-test that ANY crash offset + replay → monotonic sequence.
**Depends on:** M-A1.P4
**Requirements:** EVT-03
**Parallelizable:** no

#### Phase M-A1.P8 — Projector (steps/slices/concepts cache rebuild from events)
**Goal:** Rebuildable projections written through the single writer; `state events rebuild-projections` CLI.
**Depends on:** M-A1.P4
**Requirements:** EVT-02
**Parallelizable:** yes with M-A1.P9

#### Phase M-A1.P9 — CLI: `state events tail | replay | export`
**Goal:** Typer-based commands with SSE tailing, `--from <ulid>` replay, `--format jsonl` export, `--mode build|teach|kernel` filter.
**Depends on:** M-A1.P4
**Requirements:** EVT-07, EVT-08
**Parallelizable:** yes with M-A1.P8

#### Phase M-A1.P10 — Event-store verifier + 10,000-event replay golden fixture
**Goal:** Hypothesis property tests: idempotence + determinism; golden-fixture replay assertion.
**Depends on:** M-A1.P5, M-A1.P7, M-A1.P8
**Requirements:** EVT-06 (verifier)
**Parallelizable:** no (final)

---

## M-A2 — Auth Coverage (5 Methods + Multi-Cred)

**Version:** v0.1
**Goal:** (1) All five auth methods operational day one (Anthropic OAuth stealth, Gemini CLI, Antigravity, Copilot device-code, plain API-key). (2) Refresh safety + redaction + 0600 enforced (filelock-guarded concurrent refresh, structlog root-logger token redactor, chmod-0600 vault verified on every read). (3) Multi-cred fan-out (round-robin across per-provider credential arrays; rate-limit rotation). Unblocks the Anthropic Pro/Max primary audience.
**Depends on:** (none — foundation; no runtime deps on A1 yet, auth.json is standalone)
**Tier:** 1
**Complexity:** L
**P0 pitfalls owned:** P0-1, P0-2, P0-3, P0-4, P0-5, P0-6, P0-7, P0-8, P0-13, P0-14

**Opencode surface extended:**
- `state-inputs/opencode/packages/opencode/src/auth/index.ts` (reference shape, not ported)
- Plugin `AuthHook` at `state-inputs/opencode/packages/plugin/src/index.ts:89`

**Source influence:**
- `state-inputs/claude-oauth.md` (verbatim headers — P0 blocker — load-bearing)
- `state-inputs/gsd2-auth-analysis.md` (four-method coverage strategy)
- `state-inputs/get-shit-done/` auth storage precedent

**.state/ artifacts written:**
- `.state/auth.json` (chmod 0600)
- `.state/CLAUDE_CODE_VERSION_LOCK.md` (version-lock tracking)

**MCP tool surface delivered:** (none — shared library; auth commands exposed via `state` CLI)

**Verifier:** (1) Captured-header regression (httpx transport mock) for all 5 auth methods' stealth requests. (2) P0 regression suite (9 tests: P0-1..P0-8 + P0-13) + chmod-0600 verification on every auth.json read + structlog redactor golden-file assertion. (3) Concurrent-refresh filelock double-check harness (two-process race).

**Requirements covered:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10, AUTH-11, AUTH-12, AUTH-13

**Success criteria:**
1. User can `state auth login anthropic-oauth` and get a Claude Pro/Max subscription-priced inference run end-to-end
2. User can configure all 5 auth methods and see them all round-robin on rate-limit
3. Running `state auth status` shows mode, expiry with 5-min buffer applied, credential index, never raw tokens
4. Turning on debug logging does NOT leak any `sk-ant-*` / `sk-*` / `ya29.*` tokens to any log file (redactor verified)
5. Two concurrent processes refreshing the same near-expiry token do not invalidate each other's refresh-token (filelock double-check)

### Phases

#### Phase M-A2.P1 — `state_core.auth.base` (AuthMethod protocol + Credential container)
**Goal:** Pydantic `Credential` model, `AuthMethod` Protocol, `is_token`/`is_expired`/`http_headers`/`login`/`refresh` signatures.
**Depends on:** M-A1.P1
**Requirements:** (foundational)
**Parallelizable:** no

#### Phase M-A2.P2 — `auth.json` vault (`store.py`) with chmod-0600 + array-per-provider
**Goal:** `os.open(..., 0o600)` + `os.fchmod`; array-shape preserved even for single credentials; refuse to proceed if mode wrong.
**Depends on:** M-A2.P1
**Requirements:** AUTH-06
**Parallelizable:** no
**P0 pitfall:** P0-13

#### Phase M-A2.P3 — Filelock-guarded refresh lock (`refresh.py`)
**Goal:** 10s acquire, re-read auth.json, double-check expiry, refresh only if still stale, write, release; reader-path blocks refresher.
**Depends on:** M-A2.P2
**Requirements:** AUTH-07, AUTH-09
**Parallelizable:** no
**P0 pitfall:** P0-6, P0-7

#### Phase M-A2.P4 — Anthropic OAuth provider (stealth flow, byte-for-byte vs claude-oauth.md)
**Goal:** PKCE verifier reused as `state`, client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e` (base64-decoded at runtime), Bearer for `sk-ant-oat*`, headers `user-agent: claude-cli/<ver>` + `x-app: cli` + `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…`, 5-min expiry buffer, token-shape sniffer first branch.
**Depends on:** M-A2.P3
**Requirements:** AUTH-01
**Parallelizable:** yes with M-A2.P5..P7
**P0 pitfalls:** P0-1, P0-2, P0-3, P0-4, P0-5, P0-7, P0-8

#### Phase M-A2.P5 — Gemini CLI OAuth provider (google-auth + google-auth-oauthlib, PKCE, refresh rotation)
**Goal:** Desktop OAuth pattern, plaintext client_secret with rationale comment (NOT base64/XOR — P1-3), refresh-token rotation persisted on every refresh.
**Depends on:** M-A2.P3
**Requirements:** AUTH-02
**Parallelizable:** yes with M-A2.P4, P6, P7

#### Phase M-A2.P6 — Antigravity OAuth provider (custom OAuth2 device-code)
**Goal:** Antigravity endpoints, scope list documented with Google discovery-doc link, refresh handling.
**Depends on:** M-A2.P3
**Requirements:** AUTH-03
**Parallelizable:** yes with M-A2.P4, P5, P7

#### Phase M-A2.P7 — GitHub Copilot device-code flow
**Goal:** Device-code endpoint polling with 15-min countdown, grant-revocation detection (200-with-null-body), pydantic validation of refresh responses.
**Depends on:** M-A2.P3
**Requirements:** AUTH-04
**Parallelizable:** yes with M-A2.P4, P5, P6

#### Phase M-A2.P8 — Plain API-key vault (12 providers)
**Goal:** API-key storage for Anthropic/OpenAI/Google/DeepSeek/Groq/Together/Anyscale/Mistral/Cohere/OpenRouter/Grok/Cerebras; env var fallback.
**Depends on:** M-A2.P2
**Requirements:** AUTH-05
**Parallelizable:** yes with M-A2.P4..P7

#### Phase M-A2.P9 — Multi-cred round-robin across a provider's credential array
**Goal:** Rotation index persisted in `last_rotation`; fallback on 429 + on rate-limit-seen flags; array-shape preserved across migrations.
**Depends on:** M-A2.P2
**Requirements:** AUTH-08
**Parallelizable:** yes with M-A2.P8

#### Phase M-A2.P10 — Root-logger token redactor (structlog filter, `sk-ant-*` / `sk-*` / `ya29.*` / device-code patterns)
**Goal:** Compiled regex set, applied at root logger, refuse-daemon-start if not attached.
**Depends on:** M-A2.P1
**Requirements:** AUTH-10
**Parallelizable:** yes with most
**P0 pitfall:** P0-14

#### Phase M-A2.P11 — First-run import from opencode `~/.local/share/opencode/auth.json`
**Goal:** Detect + import into `.state/auth.json`, preserving array shape (P1-7 defence).
**Depends on:** M-A2.P2
**Requirements:** AUTH-11
**Parallelizable:** yes with M-A2.P9

#### Phase M-A2.P12 — CLI: `state auth login|logout|status` + captured-header regression tests
**Goal:** Typer commands with interactive + non-interactive flows; golden-file header diffs for every stealth request; P0 regression test (one per P0-1..P0-8 + P0-13).
**Depends on:** M-A2.P4, M-A2.P5, M-A2.P6, M-A2.P7, M-A2.P8, M-A2.P10
**Requirements:** AUTH-12, AUTH-13
**Parallelizable:** no (integration)

---

## M-A3 — Provider Routing + Model Profiles

**Version:** v0.1
**Goal:** litellm as the default multi-provider router with Anthropic SDK escape hatch for extended thinking + fine-grained cache control; OAuth stealth NEVER routes through litellm; per-Arc/Phase/Slice/Step model profiles; cost accounting in SQLite.
**Depends on:** M-A2 (soft — provider tests need auth creds, but scaffolding can start in parallel)
**Tier:** 1
**Complexity:** L
**P0 pitfalls owned:** (shares P0-1/2/3 with M-A2 via stealth bypass guard)

**Opencode surface extended:**
- Plugin hooks `chat.params`, `chat.headers`
- `provider: ProviderHook` in `state-inputs/opencode/packages/plugin/src/index.ts`

**Source influence:**
- `state-inputs/get-shit-done/` model-profiles.cjs (intent)
- `state-inputs/gsd-2pi-codebase-analysis/10-python-rebuild-mapping.md`

**.state/ artifacts written:**
- `.state/config.toml` (model profile definitions)
- SQLite: `events` rows with `state.provider.request`/`state.provider.response` cost fields

**MCP tool surface delivered:** (shared library; no tools directly)

**Verifier:** Bypass-guard test — any code path with `is_oauth_token(cred)` true must NOT call litellm; provider parity matrix across 10 reference prompts; cache-control marker end-to-end assertion; thinking-budget propagation.

**Requirements covered:** PRV-01, PRV-02, PRV-03, PRV-04, PRV-05, PRV-06, PRV-07, PRV-08, PRV-09

**Success criteria:**
1. User on Anthropic Pro/Max sees requests billed against subscription, never API-key pricing
2. User can set `model_profile: quality` on a Step and see Anthropic `claude-opus-*` with `thinking.budget_tokens` propagated through to the API
3. User can inspect `state stats --scope arc <id>` and see per-provider cost totals aggregated from every request
4. Cache-control breakpoints set in a prompt survive round-trip through the router (response accounting matches)
5. Two concurrent sessions share a single httpx client (no connection-pool exhaustion under 20-concurrent-Slice load)

### Phases

#### Phase M-A3.P1 — Shared `httpx.AsyncClient` with connection pool + proxy/TLS config
**Goal:** Single daemon-owned client, dep-injected via `Deps`.
**Depends on:** M-A1.P1
**Requirements:** PRV-06
**Parallelizable:** yes

#### Phase M-A3.P2 — litellm wrapper (`state_core.providers.litellm_client`)
**Goal:** `acompletion` with `client=shared_httpx`, streaming normalization, error taxonomy.
**Depends on:** M-A3.P1
**Requirements:** PRV-01, PRV-07
**Parallelizable:** yes with M-A3.P3

#### Phase M-A3.P3 — Direct Anthropic SDK escape hatch
**Goal:** `anthropic.AsyncAnthropic(http_client=shared_httpx)` with stealth headers when OAuth cred; extended thinking blocks + fine-grained cache-control preserved.
**Depends on:** M-A3.P1, M-A2.P4
**Requirements:** PRV-02, PRV-08, PRV-09
**Parallelizable:** yes with M-A3.P2

#### Phase M-A3.P4 — OAuth stealth bypass guard (PRV-03)
**Goal:** `ProviderRouter.select()` — if cred is `sk-ant-oat*`, route MUST be direct SDK; litellm path raises if invoked.
**Depends on:** M-A3.P2, M-A3.P3
**Requirements:** PRV-03
**Parallelizable:** no

#### Phase M-A3.P5 — Model-profile resolver (quality/balanced/budget/inherit)
**Goal:** Per-Arc/Phase/Slice/Step override, inheritance chain, resolver used by `chat.params` hook.
**Depends on:** M-A3.P2
**Requirements:** PRV-04
**Parallelizable:** yes

#### Phase M-A3.P6 — Cost accounting per request (event emission + aggregation)
**Goal:** Emit `state.provider.request`/`state.provider.response` with token/cost; aggregator reads events → per-scope rollup.
**Depends on:** M-A3.P2, M-A1.P4
**Requirements:** PRV-05
**Parallelizable:** yes

#### Phase M-A3.P7 — Thinking-budget tag propagation
**Goal:** `thinking.budget_tokens` flows through extended-thinking path; regression test with capture.
**Depends on:** M-A3.P3
**Requirements:** PRV-08
**Parallelizable:** yes

#### Phase M-A3.P8 — Cache-control marker end-to-end preservation
**Goal:** `cache_control: ephemeral` markers preserved client → provider → response accounting; verifier.
**Depends on:** M-A3.P3, M-A3.P6
**Requirements:** PRV-09
**Parallelizable:** no (integration)

#### Phase M-A3.P9 — Provider parity matrix tests
**Goal:** Hypothesis-driven 10-prompt matrix across Anthropic/Gemini/Copilot/API-key; normalized output snapshot diff.
**Depends on:** M-A3.P4, M-A3.P5
**Requirements:** (verifier; PRV-01..09)
**Parallelizable:** no (final)

---

## M-A4 — Worktree + Snapshot Service

**Version:** v0.1
**Goal:** Per-Slice worktree orchestration with opencode-preferred / pygit2-fallback, transactional bootstrap, Step/Slice snapshot composition, prefix-only revert, orphan-GC — enabling concurrent Slice execution.
**Depends on:** (none — foundation; snapshot-composition uses opencode Snapshot but abstraction hides it)
**Tier:** 1
**Complexity:** M
**P0 pitfalls owned:** P0-10 (orphan locked worktrees)

**Opencode surface extended:**
- `state-inputs/opencode/packages/opencode/src/worktree/index.ts`
- `state-inputs/opencode/packages/opencode/src/snapshot/index.ts`

**Source influence:** (new — no direct GSD/AOL precedent)

**.state/ artifacts written:**
- `.state/snapshots/<project-hash>/` (opencode Snapshot storage path)
- SQLite: `slices` table rows with `worktree_dir`, `worktree_branch`

**MCP tool surface delivered:** (shared library; `state snapshot list|diff|revert` CLI)

**Verifier:** Spawn 10 concurrent Slices → verify each gets unique worktree, sequential Steps within; crash mid-bootstrap → rollback leaves no orphan; orphan-GC finds + removes stale `.git/worktrees/*/locked`; prefix-revert test.

**Requirements covered:** WRK-01, WRK-02, WRK-03, WRK-04, WRK-05, WRK-06, WRK-07, WRK-08, WRK-09

**Success criteria:**
1. User can run 5 Slices concurrently and see 5 worktrees with deterministic branch names `slice/<arc-id>/<product-phase-id>/<slice-id>`
2. Aborting a Slice mid-bootstrap leaves the repo + `.state/` in the pre-bootstrap state (atomic transactional)
3. User can `state snapshot revert <step-id>` and see Steps N..last reverted without touching earlier Steps in the same Slice
4. A crashed Slice leaving a locked worktree gets cleaned up within 24 hours (nightly GC)
5. User on Claude Code (no opencode) can still create worktrees via pygit2 fallback

### Phases

#### Phase M-A4.P1 — Worktree abstraction interface (`state_core.worktree.WorktreeService`)
**Goal:** `create/list/remove/reset` methods, host-agnostic signature.
**Depends on:** M-A1.P1
**Requirements:** (foundational)
**Parallelizable:** yes

#### Phase M-A4.P2 — opencode-HTTP worktree adapter
**Goal:** `POST /worktree` via opencode HTTP client; subscribe to `worktree.ready`/`worktree.failed` bus events.
**Depends on:** M-A4.P1
**Requirements:** WRK-02
**Parallelizable:** yes with M-A4.P3

#### Phase M-A4.P3 — pygit2 fallback adapter
**Goal:** `Repository.add_worktree()`, `list_worktrees()`, `Worktree.prune()`; out-of-tree `state-snapshots` ref namespace for snapshots.
**Depends on:** M-A4.P1
**Requirements:** WRK-02
**Parallelizable:** yes with M-A4.P2

#### Phase M-A4.P4 — Deterministic branch + worktree naming (`slice/<arc-id>/<product-phase-id>/<slice-id>`)
**Goal:** Name generator with collision detection.
**Depends on:** M-A4.P1
**Requirements:** WRK-05
**Parallelizable:** yes

#### Phase M-A4.P5 — Transactional bootstrap (`.state/` inheritance + rollback)
**Goal:** Branch + worktree dir + `.state/` link atomic; rollback via compensation if any step fails.
**Depends on:** M-A4.P2, M-A4.P3
**Requirements:** WRK-03, WRK-01
**Parallelizable:** no

#### Phase M-A4.P6 — Orphan worktree GC (P0-10 defence)
**Goal:** Nightly daemon task scans `.git/worktrees/*/locked`, stale branch names, removes; never swallows errors.
**Depends on:** M-A4.P2, M-A4.P3
**Requirements:** WRK-04
**Parallelizable:** yes with M-A4.P7, P8
**P0 pitfall:** P0-10

#### Phase M-A4.P7 — Step snapshot (pre-execute + pre-verify via opencode `Snapshot.track`)
**Goal:** `snapshot(tier="step", reason="pre_execute"|"pre_verify")` with content-addressed hash stored in events + STEP.md frontmatter.
**Depends on:** M-A4.P5
**Requirements:** WRK-06
**Parallelizable:** yes with M-A4.P6, P8

#### Phase M-A4.P8 — Slice snapshot (boundary hash + ship-time reference)
**Goal:** On Slice shipped, store slice-tier hash in events + SLICE.md.
**Depends on:** M-A4.P7
**Requirements:** WRK-07
**Parallelizable:** yes with M-A4.P6

#### Phase M-A4.P9 — Prefix-only revert + CLI `state snapshot list|diff|revert`
**Goal:** Revert Step N within a Slice reverts N..last chronologically; Typer CLI.
**Depends on:** M-A4.P7, M-A4.P8
**Requirements:** WRK-08, WRK-09
**Parallelizable:** no (integration)

---

## M-A5 — DAG Scheduler

**Version:** v0.1
**Goal:** Pure-Python (~300 LOC) reactive DAG scheduler with typed edges, cycle detection, TaskGroup watchdog for the `CancelledError`-swallow deadlock, priority-inversion + silent-deadlock detection, and ASCII rendering.
**Depends on:** M-A1 (reactive to event-store updates)
**Tier:** 1
**Complexity:** L
**P0 pitfalls owned:** P0-16 (TaskGroup CancelledError swallow)

**Opencode surface extended:** (none — standalone; interacts with M-A1 only)

**Source influence:** (new)

**.state/ artifacts written:**
- SQLite: `aggregate_seq` reads; scheduler itself writes `state.step.advanced`, `state.slice.worktree_ready` events via M-A1

**MCP tool surface delivered:** `dag_status` (via M-A12); `state dag show` CLI

**Verifier:** Hypothesis property tests — any valid DAG terminates in topological order; cycle detection never false-positives a valid DAG; TaskGroup watchdog detects swallowed `CancelledError` within 1s of injection; 10,000-Step benchmark < 500ms per schedule tick.

**Requirements covered:** DAG-01, DAG-02, DAG-03, DAG-04, DAG-05, DAG-06, DAG-07

**Success criteria:**
1. User can author 50 Slices with a mix of `blocks`/`soft`/`data` edges and see the scheduler dispatch all unblocked ones concurrently up to the configured cap
2. Introducing a cycle in `depends_on` surfaces a clear error at roadmap validation, not at run time
3. A Step stuck on a descoped predecessor surfaces as a "silent deadlock" in the TUI within 30s
4. A `soft` dependency holding back a critical-path Slice triggers a priority-inversion warning
5. `state dag show --arc <id>` renders an ASCII DAG in <1s for arcs with up to 500 nodes

### Phases

#### Phase M-A5.P1 — Scheduler core module (`state_core.scheduler`) — typed `depends_on` edges
**Goal:** Edge kinds `blocks`/`soft`/`data`, pydantic `Edge` model, node registry.
**Depends on:** M-A1.P1
**Requirements:** DAG-01
**Parallelizable:** yes

#### Phase M-A5.P2 — Topological sort (Kahn's algorithm, stable ordering)
**Goal:** `topo_sort()` returning stable sequence; key = `(slice_id, step_id)`.
**Depends on:** M-A5.P1
**Requirements:** DAG-01
**Parallelizable:** yes with M-A5.P3

#### Phase M-A5.P3 — Cycle detection (DFS color marking)
**Goal:** `detect_cycles()` returns cycle paths; used at roadmap validation.
**Depends on:** M-A5.P1
**Requirements:** DAG-01
**Parallelizable:** yes with M-A5.P2

#### Phase M-A5.P4 — Frontier calculator (unblocked set per tick)
**Goal:** `frontier(state)` — all IDLE nodes whose `blocks`/`data` predecessors are DONE.
**Depends on:** M-A5.P1
**Requirements:** DAG-01, DAG-02
**Parallelizable:** yes

#### Phase M-A5.P5 — Dispatcher (group by Slice → TaskGroup per Slice, concurrency cap)
**Goal:** `asyncio.gather` across Slices with cap; serial within Slice; configurable cap in `config.toml`.
**Depends on:** M-A5.P4
**Requirements:** DAG-02
**Parallelizable:** no

#### Phase M-A5.P6 — TaskGroup watchdog (P0-16 defence)
**Goal:** Nested TaskGroup regression harness; watchdog detects `CancelledError` swallow via exception group inspection; fails loud.
**Depends on:** M-A5.P5
**Requirements:** DAG-03
**Parallelizable:** no
**P0 pitfall:** P0-16

#### Phase M-A5.P7 — Reactive trigger (subscribe to M-A1 event stream)
**Goal:** On `state.step.advanced`, `state.slice.worktree_ready`, `state.phase.planned` → recompute frontier; no polling.
**Depends on:** M-A5.P5, M-A1.P9
**Requirements:** DAG-04
**Parallelizable:** no

#### Phase M-A5.P8 — Priority inversion + silent deadlock detection
**Goal:** Heuristic: if critical-path Step is blocked on `soft` edge, warn; if all in-flight are blocked on descoped/missing predecessors, emit `state.scheduler.deadlock` → TUI surfaces.
**Depends on:** M-A5.P7
**Requirements:** DAG-05, DAG-06
**Parallelizable:** yes

#### Phase M-A5.P9 — CLI: `state dag show [--arc|--phase|--slice]` ASCII renderer
**Goal:** Box-drawing rendering with status colors; Hypothesis property test: any valid graph renders without crash.
**Depends on:** M-A5.P2, M-A5.P4
**Requirements:** DAG-07
**Parallelizable:** yes

---

## M-A6 — State Daemon (HTTP + SSE + Mode Middleware)

**Version:** v0.2
**Goal:** Always-on Python user service (launchd + systemd units) with unix-socket HTTP API, SSE bus broadcast, canonical mode-enforcement middleware, pid-file + stale-pid detection, crash recovery from events log, log rotation.
**Depends on:** M-A1 (events), M-A2 (auth)
**Tier:** 2
**Complexity:** L
**P0 pitfalls owned:** P0-15 (stale pid refuses start)

**Opencode surface extended:**
- opencode HTTP API (client)
- opencode SSE bus

**Source influence:** (new)

**.state/ artifacts written:**
- `.state/daemon.sock`, `.state/daemon.pid` (with `start_time_ns`)
- `.state/logs/daemon.log` (rotating)

**MCP tool surface delivered:** (none; daemon exposes HTTP, not MCP)

**Verifier:** Kill daemon with `kill -9` → stale pid detected via `/proc` (Linux) or `ps` (macOS), new daemon starts cleanly; load-test 100 req/s on unix socket; mode middleware rejects cross-mode event writes; crash during in-flight Step → recovery replays STATE.md projection.

**Requirements covered:** DAE-01, DAE-02, DAE-03, DAE-04, DAE-05, DAE-06, DAE-07, DAE-08, DAE-09

**Success criteria:**
1. User starts opencode 3 days later and dashboards still reflect the correct state (daemon never stopped running)
2. Daemon crashes mid-Step → on restart, the Step resumes from its last snapshot + event position
3. `state daemon status` shows pid, start time, socket path, events-since-start count
4. No `build` event can be written while mode is `teach` (middleware rejects at the daemon — canonical gate)
5. Log files rotate at configurable threshold; old logs never exceed the cap

### Phases

#### Phase M-A6.P1 — Starlette (or bare) HTTP server + unix socket binding
**Goal:** `asyncio.start_unix_server`, JSON-RPC 2.0 framing, request router.
**Depends on:** M-A1.P4
**Requirements:** DAE-05
**Parallelizable:** yes with M-A6.P2

#### Phase M-A6.P2 — pid-file + start_time_ns + stale detection
**Goal:** `.state/daemon.pid` with `{pid, start_time_ns}`; `/proc/<pid>/stat` on Linux, `ps -o lstart=` on macOS; stale → remove and start fresh.
**Depends on:** M-A1.P1
**Requirements:** DAE-03
**Parallelizable:** yes with M-A6.P1
**P0 pitfall:** P0-15

#### Phase M-A6.P3 — Unix socket path (`$XDG_RUNTIME_DIR/state-<hash>.sock` / tmp fallback)
**Goal:** Project-hash-based socket name; fallback when `$XDG_RUNTIME_DIR` missing (macOS).
**Depends on:** M-A6.P1
**Requirements:** DAE-04
**Parallelizable:** yes

#### Phase M-A6.P4 — Mode-enforcement HTTP middleware (canonical gate)
**Goal:** Every request carries `mode` header; validator against `.state/mode.json` rejects mismatches with 403; **authoritative mode-isolation point**.
**Depends on:** M-A6.P1, M-A1.P4
**Requirements:** DAE-05, MODE-05
**Parallelizable:** no (depends on M-A11 schema too — soft dep)

#### Phase M-A6.P5 — SSE bus broadcast endpoint
**Goal:** `/events/subscribe` SSE stream fan-out of event-store updates; multi-client support; heartbeats.
**Depends on:** M-A6.P1, M-A1.P9
**Requirements:** DAE-06
**Parallelizable:** yes with M-A6.P4

#### Phase M-A6.P6 — launchd plist + systemd --user unit + installer
**Goal:** `state daemon install` drops plist/unit, enables at login; uninstall removes.
**Depends on:** M-A6.P2
**Requirements:** DAE-01
**Parallelizable:** yes

#### Phase M-A6.P7 — structlog + RotatingFileHandler + log rotation config
**Goal:** JSON mode + dev-renderer mode; size + time rotation; retention cap; redactor attached (M-A2.P10).
**Depends on:** M-A2.P10
**Requirements:** DAE-07
**Parallelizable:** yes

#### Phase M-A6.P8 — Crash recovery (replay STATE.md projection + resume in-flight Steps)
**Goal:** On start, read last events, rebuild STATE.md projection, find Steps in `executing`/`verifying` → resume from last checkpoint.
**Depends on:** M-A1.P7, M-A4.P7
**Requirements:** DAE-08
**Parallelizable:** no

#### Phase M-A6.P9 — CLI: `state daemon start|stop|restart|status|logs`
**Goal:** Typer commands; `status` shows pid + start_time + events-count + mode; `logs` tails daemon.log.
**Depends on:** M-A6.P2, M-A6.P6
**Requirements:** DAE-09
**Parallelizable:** yes

#### Phase M-A6.P10 — Auth-manager wiring into daemon (provider refresh, rotation)
**Goal:** Daemon owns the auth refresh loop; multi-cred round-robin surfaced via HTTP `GET /auth/status`.
**Depends on:** M-A2.P3, M-A6.P1
**Requirements:** AUTH-07, AUTH-08 (runtime wiring)
**Parallelizable:** no (integration)

---

## M-A7 — Per-Session Worker

**Version:** v0.2
**Goal:** Per-opencode-session Python worker spawned by plugin shim, owns hot state for active Slice/Step/drill, forwards opencode hook events to daemon, tears down on session close, refuses on version mismatch.
**Depends on:** M-A6
**Tier:** 2
**Complexity:** M

**Opencode surface extended:** opencode HTTP session ops + plugin shim handshake

**Source influence:** (new)

**.state/ artifacts written:** `.state/logs/worker-<pid>.log`

**MCP tool surface delivered:** (none directly — plumbing)

**Verifier:** Spawn 3 concurrent opencode sessions → 3 workers attached; kill one session → its worker gone; old plugin vs new daemon handshake → refused.

**Requirements covered:** WRK-10, WRK-11, WRK-12, WRK-13

**Success criteria:**
1. Opening an opencode session spawns a worker within 200ms
2. Worker holds active Slice/Step/drill state locally for fast access
3. Worker forwards every hook event to the daemon with ≤50ms latency
4. Version mismatch between plugin and daemon refuses attach with a human-readable error

### Phases

#### Phase M-A7.P1 — Worker main module + bootstrap (spawned by plugin shim)
**Goal:** `state_worker.main`; reads session ID, attaches to daemon, registers hot state.
**Depends on:** M-A6.P1
**Requirements:** WRK-10
**Parallelizable:** yes

#### Phase M-A7.P2 — Daemon ↔ worker bridge (HTTP+SSE client)
**Goal:** Worker connects to daemon unix socket; subscribes to SSE for session-scoped events.
**Depends on:** M-A7.P1, M-A6.P5
**Requirements:** WRK-10, WRK-12
**Parallelizable:** no

#### Phase M-A7.P3 — Hot state container (active Slice/Step/drill)
**Goal:** In-memory pydantic container synced from daemon on attach; updated on events.
**Depends on:** M-A7.P2
**Requirements:** WRK-11
**Parallelizable:** yes with M-A7.P4

#### Phase M-A7.P4 — Hook event forwarding (HTTP POST to daemon)
**Goal:** `POST /hook/<name>` with typed payload; retries on transient failure.
**Depends on:** M-A7.P2
**Requirements:** WRK-12
**Parallelizable:** yes with M-A7.P3

#### Phase M-A7.P5 — Version handshake (plugin/daemon compatibility)
**Goal:** Plugin sends `X-State-Plugin-Version`; worker/daemon validates against compat range; refuse attach with error.
**Depends on:** M-A7.P1
**Requirements:** WRK-13
**Parallelizable:** yes

#### Phase M-A7.P6 — Session tear-down on opencode close
**Goal:** Plugin signals close → worker flushes pending hook events → exits cleanly.
**Depends on:** M-A7.P4
**Requirements:** WRK-10
**Parallelizable:** yes

#### Phase M-A7.P7 — Worker logs + structured logging
**Goal:** Per-worker-PID log file; rotating; redactor attached.
**Depends on:** M-A6.P7
**Requirements:** OBS-01 (partial)
**Parallelizable:** yes

#### Phase M-A7.P8 — Multi-session stress test + teardown verifier
**Goal:** 3-session concurrent harness; kill/restart + verify no leaked workers.
**Depends on:** M-A7.P1..P7
**Requirements:** (verifier for WRK-10..13)
**Parallelizable:** no (final)

---

## M-A8 — Plugin Server Hooks (all 9)

**Version:** v0.2
**Goal:** `@state/opencode-plugin` server bundle — all 9 opencode hooks (`chat.message`, `tool.execute.before/after`, `permission.ask`, `event`, `experimental.chat.system.transform`, `experimental.session.compacting`, `chat.params`, `command.execute.before`, `shell.env`) wired to the per-session worker over HTTP, mode-gated.
**Depends on:** M-A7
**Tier:** 2
**Complexity:** L

**Opencode surface extended:**
- `state-inputs/opencode/packages/plugin/src/index.ts:222-333` (all 9 hook types)

**Source influence:** `state-inputs/get-shit-done/hooks/*.js,*.sh`

**.state/ artifacts written:** (hooks emit events via worker → M-A1; plugin is a client)

**MCP tool surface delivered:** (MCP server registration wiring; tool surface from M-A12/M-A13)

**Verifier:** Every hook exercises a smoke test that round-trips through worker → daemon → events.sqlite and asserts a matching event row.

**Requirements covered:** HOOK-01, HOOK-02, HOOK-03, HOOK-04, HOOK-05, HOOK-06, HOOK-07, HOOK-08, HOOK-09, HOOK-10, HOOK-11

**Success criteria:**
1. Every opencode hook fires a corresponding `state.*` event visible in `state events tail`
2. `/state:build:*` invocations in a teach-mode session are rejected with a helpful error
3. Tool invocations outside the active Slice's worktree are blocked at `tool.execute.before`
4. System prompts are injected with current Step goal + verify contract on every chat turn
5. Compaction preserves active Step ID + last 3 verify results

### Phases

#### Phase M-A8.P1 — `@state/opencode-plugin` TS package scaffolding (bun, tsconfig match opencode)
**Goal:** `package.json` peer deps per STACK.md; `tsconfig` extends `@tsconfig/node22`; `build: "tsc"`; `bun install`.
**Depends on:** M-A7.P1
**Requirements:** HOOK-11
**Parallelizable:** yes (independent TS workspace)

#### Phase M-A8.P2 — `chat.message` hook (prompt guard + state injection)
**Goal:** Parse `/state:*`, reject cross-mode, append active Step/Concept hint.
**Depends on:** M-A8.P1, M-A7.P4
**Requirements:** HOOK-01
**Parallelizable:** yes with P3..P11

#### Phase M-A8.P3 — `tool.execute.before` hook (mode gate + scope gate)
**Goal:** Block writes outside active Slice worktree; block `mcp__state-teach__*` in build mode; rewrite `.state/` path args.
**Depends on:** M-A8.P1
**Requirements:** HOOK-02
**Parallelizable:** yes

#### Phase M-A8.P4 — `tool.execute.after` hook (output verification + observation)
**Goal:** Build: match against Step `verify_contract`; Teach: classify + feed mental_model.
**Depends on:** M-A8.P1
**Requirements:** HOOK-03
**Parallelizable:** yes

#### Phase M-A8.P5 — `permission.ask` hook (gray-area routing)
**Goal:** Auto-approve within scope; route to dialog otherwise; persist `state.permission.decided`.
**Depends on:** M-A8.P1
**Requirements:** HOOK-04
**Parallelizable:** yes

#### Phase M-A8.P6 — `event` hook (universal observer → SSE mirror)
**Goal:** Subscribe to `session.idle`, `worktree.ready`, `question.replied`, `permission.replied`, etc.; mirror to daemon.
**Depends on:** M-A8.P1
**Requirements:** HOOK-05
**Parallelizable:** yes

#### Phase M-A8.P7 — `experimental.chat.system.transform` hook (mode-specific system injection)
**Goal:** Prepend mode banner + active artifact content (STEP.md frontmatter, verify contract, personality).
**Depends on:** M-A8.P1
**Requirements:** HOOK-06
**Parallelizable:** yes

#### Phase M-A8.P8 — `experimental.session.compacting` hook (phase-aware compaction)
**Goal:** Inject "preserve these IDs" (active Step ID, last 3 verify results, open gray-area, pending drills).
**Depends on:** M-A8.P1
**Requirements:** HOOK-07
**Parallelizable:** yes

#### Phase M-A8.P9 — `chat.params` + `chat.headers` hook (profile + cache-control injection)
**Goal:** Inject model profile resolution (from M-A3.P5); cache-control markers; thinking budget.
**Depends on:** M-A8.P1, M-A3.P5
**Requirements:** HOOK-08
**Parallelizable:** yes

#### Phase M-A8.P10 — `command.execute.before` hook (mode gate for slash commands)
**Goal:** Reject `/state:build:*` when mode=teach, and vice versa; inject expanded `.planning/*.md` content.
**Depends on:** M-A8.P1
**Requirements:** HOOK-09
**Parallelizable:** yes

#### Phase M-A8.P11 — `shell.env` hook (STATE_* env var injection)
**Goal:** Export `STATE_ARC`, `STATE_PHASE`, `STATE_SLICE`, `STATE_STEP`, `STATE_WORKTREE`, `STATE_DAEMON_URL`, `STATE_AUTH_JSON`.
**Depends on:** M-A8.P1
**Requirements:** HOOK-10
**Parallelizable:** yes

#### Phase M-A8.P12 — Plugin bundle + `bun build` packaging + install script
**Goal:** Bundled `@state/opencode-plugin` TS package; `state install` auto-registers.
**Depends on:** M-A8.P2..P11
**Requirements:** HOOK-11
**Parallelizable:** no (final integration)

---

## M-A9 — Plugin TUI Bundle

**Version:** v0.2
**Goal:** SolidJS-based TUI extensions matching opencode's catalog — sidebar (mode-gated build/teach), statusline, toast notifications; installed alongside the server shim in one bundle.
**Depends on:** M-A7
**Tier:** 2
**Complexity:** L

**Opencode surface extended:**
- `state-inputs/opencode/packages/plugin/src/tui.ts` — `TuiPluginApi`

**Source influence:** `state-inputs/get-shit-done/` gsd-statusline.js

**.state/ artifacts written:** (UI only — talks to daemon HTTP + opencode bus)

**MCP tool surface delivered:** (none; UI)

**Verifier:** TUI renders sidebar in build mode (Arc/Phase/Slice tree), swaps to concept graph in teach mode; statusline shows mode + Step + cost; toasts fire on Slice completion / drill availability / auth refresh.

**Requirements covered:** TUI-01, TUI-02, TUI-03, TUI-04, TUI-05

**Success criteria:**
1. Sidebar shows active Arc/Phase/Slice hierarchy (build) or concept + mastery (teach) based on `.state/mode.json`
2. Statusline shows `mode / step N.m / provider / $X.XX`
3. Toast fires within 2s of Slice completion, drill availability, or auth refresh
4. Running `state install` registers the plugin with opencode in one step

### Phases

#### Phase M-A9.P1 — TUI entry module + `TuiPluginModule` export
**Goal:** `tui.ts` scaffold, solid-js + @opentui/core + @opentui/solid imports at catalog versions.
**Depends on:** M-A8.P1
**Requirements:** TUI-01
**Parallelizable:** yes

#### Phase M-A9.P2 — Sidebar slot (`sidebar_content`) — mode-aware renderer
**Goal:** Reads `.state/mode.json` at render; conditional render build-tree vs concept-state.
**Depends on:** M-A9.P1, M-A6.P5
**Requirements:** TUI-02
**Parallelizable:** yes with P3..P5

#### Phase M-A9.P3 — Build-progress sub-component (current Step + Slice DAG mini-view)
**Goal:** Subscribes to daemon SSE; renders Step status colors + Slice DAG thumbnail.
**Depends on:** M-A9.P2
**Requirements:** TUI-02
**Parallelizable:** yes with P4, P5

#### Phase M-A9.P4 — Teach-concept sub-component (current concept + mastery bar)
**Goal:** Subscribes to daemon SSE; renders concept card + Kolb stage + mastery bar.
**Depends on:** M-A9.P2
**Requirements:** TUI-02
**Parallelizable:** yes with P3, P5

#### Phase M-A9.P5 — Statusline (`sidebar_footer` / `home_footer`)
**Goal:** One-line mode + scope + provider + session cost; subscribes to cost events.
**Depends on:** M-A9.P1
**Requirements:** TUI-03
**Parallelizable:** yes

#### Phase M-A9.P6 — Toast notifications (`ui.toast`)
**Goal:** Slice completion, drill availability, gray-area decisions, auth refresh; de-dup.
**Depends on:** M-A9.P1
**Requirements:** TUI-04
**Parallelizable:** yes

#### Phase M-A9.P7 — Plugin install script (`TuiPluginInstallOptions`)
**Goal:** Auto-registers plugin + MCP servers in `opencode.json` on first run.
**Depends on:** M-A8.P12
**Requirements:** TUI-05
**Parallelizable:** yes

#### Phase M-A9.P8 — Prompt hint slot (`session_prompt_right`)
**Goal:** Shows model + token cost + Step N.m indicator.
**Depends on:** M-A9.P5
**Requirements:** TUI-03
**Parallelizable:** yes

#### Phase M-A9.P9 — Bun test suite for TUI components
**Goal:** `bun test` unit tests for sidebar/statusline/toast logic.
**Depends on:** M-A9.P2..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A10 — TUI DAG Viewer

**Version:** v0.3
**Goal:** Shared (mode-agnostic) interactive DAG visualization route with color-coded nodes, filters, critical-path highlighting, SSE live updates.
**Depends on:** M-A8, M-A9
**Tier:** 2
**Complexity:** M

**Opencode surface extended:**
- `route.register({ name: "state.dag" })`
- `ui.Slot`

**Source influence:** (new)

**.state/ artifacts written:** (UI only)

**MCP tool surface delivered:** (none; UI)

**Verifier:** Open `/state:dag` → see nodes colored by status; click node → detail pane; filter by Arc → subset; live update as scheduler advances (<2s).

**Requirements covered:** DAG-VIEW-01, DAG-VIEW-02, DAG-VIEW-03, DAG-VIEW-04

**Success criteria:**
1. User invokes `/state:dag` and sees the full Arc/Phase/Slice/Step DAG within 1s
2. Clicking a node opens detail pane with the corresponding `.md` content
3. Filtering by `critical path` highlights only the longest dependency chain
4. DAG updates within 2s of any `state.step.advanced` event

### Phases

#### Phase M-A10.P1 — Route registration + layout (topological auto-layout)
**Goal:** `route.register({ name: "state.dag" })`; topological layout algorithm.
**Depends on:** M-A9.P1
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes

#### Phase M-A10.P2 — Node rendering (color-coded by status)
**Goal:** Status palette: pending/in-progress/done/failed/blocked; colors from opencode theme.
**Depends on:** M-A10.P1
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes with P3, P4

#### Phase M-A10.P3 — Click-to-detail pane (STEP.md / SLICE.md / PHASE.md / ARC.md)
**Goal:** Side panel renders markdown content; scroll sync.
**Depends on:** M-A10.P2
**Requirements:** DAG-VIEW-02
**Parallelizable:** yes with P4

#### Phase M-A10.P4 — Filter bar (Arc / Phase / Slice / critical-path)
**Goal:** Filter presets; critical-path computed from scheduler data.
**Depends on:** M-A10.P2
**Requirements:** DAG-VIEW-03
**Parallelizable:** yes with P3

#### Phase M-A10.P5 — SSE live updates
**Goal:** Subscribe to daemon SSE; diff-patch node status.
**Depends on:** M-A10.P2, M-A6.P5
**Requirements:** DAG-VIEW-04
**Parallelizable:** yes

#### Phase M-A10.P6 — Keyboard navigation + accessibility
**Goal:** Arrow keys move focus; Enter opens detail; `F` focuses filter.
**Depends on:** M-A10.P3
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes

#### Phase M-A10.P7 — Large-graph performance (≥500 nodes)
**Goal:** Virtualized rendering; clip off-screen; layout cache.
**Depends on:** M-A10.P2
**Requirements:** DAG-VIEW-01
**Parallelizable:** yes

#### Phase M-A10.P8 — Integration smoke test (multi-mode projects)
**Goal:** Verify DAG viewer works in both build and teach (teach shows concept DAG).
**Depends on:** M-A10.P1..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A11 — Mode Enforcement (6 Layers)

**Version:** v0.3
**Goal:** Physical + runtime + static enforcement of the "exclusive modes" cardinal rule across disk, MCP registration, plugin hooks, command dispatch, daemon HTTP middleware (canonical), and Python import-graph lint.
**Depends on:** M-A6, M-A8
**Tier:** 2
**Complexity:** M
**P0 pitfalls owned:** P0-11 (mode isolation leakage)

**Opencode surface extended:**
- `config` hook (MCP registration toggle)
- `command.execute.before`, `tool.execute.before` (already wired in M-A8)

**Source influence:** (new)

**.state/ artifacts written:**
- `.state/mode.json`
- `.state/build/` or `.state/teach/` subtrees (created by init)

**MCP tool surface delivered:** (none directly — infrastructure)

**Verifier:** All 6 layers individually tested — disk (M-A11.P2: `.state/build/` vs `.state/teach/` directory-presence assertion), MCP registration (M-A11.P3: build→teach switch stops build MCP server, starts teach within the <3s SLO at success-criterion #2 line 1134), plugin hooks (M-A11.P4: `command.execute.before` rejects cross-mode `/state:*`; `tool.execute.before` rejects cross-mode `mcp__state-*__` invocation), command dispatch (M-A11.P4: same layer), daemon HTTP middleware canonical gate (M-A11.P5: attempted `state.concept.observed` write while mode=build rejected with 403), Python import-graph lint (M-A11.P6: `state.build` importing `state.teach` fails CI). M-A11.P9 P0-11 regression suite is the integrating cross-mode-leakage test.

**Requirements covered:** MODE-01, MODE-02, MODE-03, MODE-04, MODE-05, MODE-06, MODE-07

**Success criteria:**
1. `.state/mode.json` with invalid mode rejected at daemon start
2. Running `state mode set teach` stops `state-build` MCP server and starts `state-teach` within 3s
3. Cross-mode command invocation fails with helpful error, not silent mismatch
4. CI fails on any PR that introduces `state.build.*` importing `state.teach.*`
5. Daemon HTTP `/events/append` rejects `state.concept.*` when mode=build (canonical gate)

### Phases

#### Phase M-A11.P1 — `.state/mode.json` schema + validator
**Goal:** Pydantic `ModeConfig` with `mode: build|teach|both`; strict validation; CLI init.
**Depends on:** M-A1.P2
**Requirements:** MODE-01
**Parallelizable:** yes

#### Phase M-A11.P2 — Directory-presence signal (`.state/build/` vs `.state/teach/`)
**Goal:** Daemon refuses writes into the wrong subtree; `state mode init` bootstraps structure.
**Depends on:** M-A11.P1
**Requirements:** MODE-02
**Parallelizable:** yes with P3

#### Phase M-A11.P3 — MCP registration toggle (`config` hook)
**Goal:** Plugin reads `.state/mode.json` at boot; `config` hook returns enabled/disabled for each server; hot-reload on mode change.
**Depends on:** M-A8.P1, M-A11.P1
**Requirements:** MODE-03
**Parallelizable:** yes with P2

#### Phase M-A11.P4 — Plugin hook mode gate (refinement of M-A8.P2/P3/P10)
**Goal:** `command.execute.before` rejects `/state:build:*` when mode=teach; `tool.execute.before` rejects `mcp__state-teach__*` when mode=build.
**Depends on:** M-A8.P3, M-A8.P10
**Requirements:** MODE-04
**Parallelizable:** yes

#### Phase M-A11.P5 — Daemon HTTP mode middleware (canonical gate)
**Goal:** Already partially in M-A6.P4; extend with event-type-level validation (reject `state.concept.*` when mode=build).
**Depends on:** M-A6.P4
**Requirements:** MODE-05
**Parallelizable:** no
**P0 pitfall:** P0-11

#### Phase M-A11.P6 — Python import-graph lint (CI)
**Goal:** Ruff plugin or custom script; fails if `state.build.*` imports `state.teach.*` or vice versa.
**Depends on:** M-A1.P1
**Requirements:** MODE-06, TST-07
**Parallelizable:** yes

#### Phase M-A11.P7 — CLI: `state mode init build|teach|both` + `state mode set`
**Goal:** Typer commands; init bootstraps subtree + mode.json; set validates + reloads.
**Depends on:** M-A11.P1, M-A11.P2
**Requirements:** MODE-07
**Parallelizable:** yes

#### Phase M-A11.P8 — Mode activation event (`state.mode.activated`)
**Goal:** Emit event on mode change; SSE fan-out triggers MCP reload.
**Depends on:** M-A11.P3, M-A1.P4
**Requirements:** MODE-03, MODE-05
**Parallelizable:** no

#### Phase M-A11.P9 — Cross-mode leakage regression suite
**Goal:** P0-11 test suite: attempt every illegal combination, assert rejection at canonical gate.
**Depends on:** M-A11.P1..P8
**Requirements:** (verifier; TST-08)
**Parallelizable:** no (final)

---

## M-A12 — state-build MCP Server (skeleton)

**Version:** v0.3
**Goal:** Mode-gated `state-build` MCP server with ≤15 tools, each ≤80-token description, stateful tools via opencode `task` resumption, streaming progress, tool-budget CI assertion.
**Depends on:** M-A11
**Tier:** 2
**Complexity:** M
**P0 pitfalls owned:** P0-12 (MCP tool-name collision) (shared with M-A13)

**Opencode surface extended:**
- `state-inputs/opencode/packages/opencode/src/mcp/index.ts` (client side)

**Source influence:** (new — tool names mapped to GSD commands per ARCHITECTURE §4.1)

**.state/ artifacts written:** (tools write via daemon)

**MCP tool surface delivered:** (skeleton — canonical names): `plan_step`, `execute_step`, `verify_step`, `discuss_step`, `research_step`, `snapshot_revert`, `dag_status`, `arc_show`, `slice_ship`, `code_review`, `debug_session`, `forensics`, `intel_refresh`, `pause_work`, `resume_work`. Full semantics land in M-A14/15/16.

**Verifier:** `state dev tool-budget` asserts 15 tools × ≤80 tokens per description; invoking `mcp__state-teach__*` tool while `state-build` is registered is blocked by mode gate.

**Requirements covered:** MCP-B-01, MCP-B-02, MCP-B-03, MCP-B-04, MCP-B-05, MCP-B-06

**Success criteria:**
1. `state-build` registered in opencode only when mode in `{build, both}`
2. Tool budget test passes (`state dev tool-budget` green)
3. Stateful tools survive context compaction via `task_id` resume
4. Long-running tool (e.g., `forensics`) streams progress via MCP protocol
5. Attempted invocation with `state-teach` server also registered in same session is blocked (P0-12)

### Phases

#### Phase M-A12.P1 — MCP server scaffold (FastMCP from `mcp` SDK)
**Goal:** `state_build.mcp` entry with stdio transport; pydantic tool schemas.
**Depends on:** M-A11.P3
**Requirements:** MCP-B-01
**Parallelizable:** yes

#### Phase M-A12.P2 — 15 skeleton tools with ≤80-token descriptions
**Goal:** Names per MCP-B-03; skeleton returns "not implemented" with structured error; descriptions tuned for token budget.
**Depends on:** M-A12.P1
**Requirements:** MCP-B-02, MCP-B-03
**Parallelizable:** yes

#### Phase M-A12.P3 — `state dev tool-budget` command + CI assertion
**Goal:** Sum tool-description tokens (tiktoken replacement: use provider counts), refuse > budget.
**Depends on:** M-A12.P2
**Requirements:** MCP-B-06
**Parallelizable:** yes

#### Phase M-A12.P4 — Stateful tool resume (opencode `task` + `task_id`)
**Goal:** `discuss_step`/`plan_step`/`execute_step`/`verify_step`/`code_review`/`debug_session` use `task` tool; task_id stored in event; resume after compaction.
**Depends on:** M-A12.P1
**Requirements:** MCP-B-04
**Parallelizable:** yes

#### Phase M-A12.P5 — Streaming progress via MCP protocol
**Goal:** Long-running tools emit `progress` notifications per MCP spec.
**Depends on:** M-A12.P1
**Requirements:** MCP-B-05
**Parallelizable:** yes

#### Phase M-A12.P6 — Shared library wiring (auth, events, provider via `state_core`)
**Goal:** Tool impls call `state_core` helpers; no duplicate auth/provider logic.
**Depends on:** M-A12.P1
**Requirements:** (infrastructure)
**Parallelizable:** yes

#### Phase M-A12.P7 — Mode-gate integration (refuse start when mode=teach)
**Goal:** Server checks `.state/mode.json` at boot; exits with clear error if mode mismatch.
**Depends on:** M-A11.P1
**Requirements:** MCP-B-01, MODE-03
**Parallelizable:** yes

#### Phase M-A12.P8 — P0-12 tool-name collision regression test
**Goal:** Spawn both servers → assert opencode refuses or mode-gate blocks; name prefix contract.
**Depends on:** M-A12.P7
**Requirements:** (P0-12 defence)
**Parallelizable:** yes

#### Phase M-A12.P9 — Integration test against real opencode MCP client
**Goal:** E2E: spawn opencode binary, register state-build, enumerate tools, invoke each skeleton tool.
**Depends on:** M-A12.P1..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A13 — state-teach MCP Server (skeleton)

**Version:** v0.3
**Goal:** Mode-gated `state-teach` MCP server with ≤15 tools, drill tools bound to opencode `question`, structured-only observations, ≤3000-token drill prompts.
**Depends on:** M-A11
**Tier:** 2
**Complexity:** M
**P0 pitfalls owned:** P0-12 (shared with M-A12)

**Opencode surface extended:**
- `state-inputs/opencode/packages/opencode/src/mcp/index.ts` (client side)
- `state-inputs/opencode/packages/opencode/src/question/index.ts` (binding)

**Source influence:** AOL workflows (`teach.md`, `build-subject.md`, `state.md`)

**.state/ artifacts written:** (tools write via daemon)

**MCP tool surface delivered:** `concept_next`, `drill_prepare`, `drill_verify`, `concept_teach`, `observation_record`, `mental_model_show`, `subject_pick`, `subject_author`, `style_edit`, `learner_state`, `review_session`, `mentor_scaffold`, `coding_partner`, `learning_verify`. Full semantics land in M-A18..M-A24.

**Verifier:** 15-tool budget; drill prompt ≤3000 tokens (Hypothesis property test); observation payloads reject freeform text (schema-validated).

**Requirements covered:** MCP-T-01, MCP-T-02, MCP-T-03, MCP-T-04, MCP-T-05, MCP-T-06

**Success criteria:**
1. `state-teach` registered only when mode in `{teach, both}`
2. `drill_prepare` tool returns ≤3000-token prompts
3. Observation tool rejects freeform strings (schema-validated)
4. `drill_verify` + `concept_teach` route to opencode `question` tool for structured input
5. Tool budget test passes

### Phases

#### Phase M-A13.P1 — MCP server scaffold (`state_teach.mcp`)
**Goal:** FastMCP stdio; mode-gate check.
**Depends on:** M-A11.P3
**Requirements:** MCP-T-01
**Parallelizable:** yes

#### Phase M-A13.P2 — 15 skeleton tools with ≤80-token descriptions
**Goal:** Names per MCP-T-03; "not implemented" skeletons.
**Depends on:** M-A13.P1
**Requirements:** MCP-T-02, MCP-T-03
**Parallelizable:** yes

#### Phase M-A13.P3 — Opencode `question` tool binding wrapper
**Goal:** `ask_structured(questions: list[Question])` → typed answers via `client.question.ask(...)`.
**Depends on:** M-A13.P1
**Requirements:** MCP-T-04
**Parallelizable:** yes

#### Phase M-A13.P4 — Observation schema (structured-only, reject freeform)
**Goal:** Pydantic `Observation` with discriminator `kind`; `extra = "forbid"`.
**Depends on:** M-A1.P2
**Requirements:** MCP-T-05
**Parallelizable:** yes

#### Phase M-A13.P5 — Drill prompt token cap (≤3000 tokens)
**Goal:** Helper to count + cap; Hypothesis property test.
**Depends on:** M-A13.P1
**Requirements:** MCP-T-06
**Parallelizable:** yes

#### Phase M-A13.P6 — Shared library wiring (auth, events via `state_core`)
**Goal:** As M-A12.P6.
**Depends on:** M-A13.P1
**Requirements:** (infrastructure)
**Parallelizable:** yes

#### Phase M-A13.P7 — Mode-gate integration (refuse start when mode=build)
**Goal:** As M-A12.P7.
**Depends on:** M-A11.P1
**Requirements:** MCP-T-01, MODE-03
**Parallelizable:** yes

#### Phase M-A13.P8 — Tool-budget CI assertion (shared helper w/ M-A12)
**Goal:** `state dev tool-budget --server state-teach` green.
**Depends on:** M-A13.P2
**Requirements:** (shares MCP-B-06 infra)
**Parallelizable:** yes

#### Phase M-A13.P9 — Integration test against real opencode MCP client
**Goal:** As M-A12.P9.
**Depends on:** M-A13.P1..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A14 — Build Kernel: Step FSM + Verifiers

**Version:** v0.4
**Goal:** The heart of build-mode — Step state machine + STEP.md frontmatter schema + goal-backward verifier + Slice/Phase/Arc rollup verifiers + cross-tier integration verifier + security verifier.
**Depends on:** M-A5 (scheduler), M-A12 (MCP skeleton)
**Tier:** 3a
**Complexity:** XL

**Opencode surface extended:**
- `tool.execute.after` hook (verify trigger)
- `experimental.chat.system.transform` (system prompt injection with Step goal)
- `task` tool (verifier subagent spawn)

**Source influence:**
- `state-inputs/get-shit-done/` gsd-executor, gsd-verifier, verify.cjs
- AOL learning verifier pattern

**.state/ artifacts written:**
- `.state/build/steps/<step-id>/STEP.md` (with frontmatter schema)
- `.state/build/steps/<step-id>/VERIFY.md` (structured results)
- SQLite: `state.step.*` events, `steps` projection

**MCP tool surface delivered (full semantics):** `verify_step`, `advance_step` (internally)

**Verifier:** 10 golden-fixture Steps with known goal + committed code assert verifier pass/fail per Step FSM (M-A14.P2); goal-backward verifier (M-A14.P4) rejects mismatched must-haves; Slice rollup (M-A14.P5) fails if any child Step fails; product-Phase rollup (M-A14.P6) and product-Arc rollup (M-A14.P7) aggregate upward; cross-tier integration verifier (M-A14.P8) catches regression when product-Arc A interacts with product-Arc B (synthetic Arc-A/B fixture required); security verifier part-1 (M-A14.P9 — input guards) rejects SQLi/path-traversal/secret-leak/shell-meta inputs. M-A14.P11 10-Step golden-fixture suite is the integrating test.

**Requirements covered:** BLD-01, BLD-02, BLD-03, BLD-04, BLD-05, BLD-06, BLD-07, BLD-08, BLD-09

**Success criteria:**
1. A Step transitions through `pending → discussing → planning → executing → verifying → shipped` emitting events at each edge
2. A failing verify reverts via the `pre_verify` snapshot and surfaces the reason in VERIFY.md
3. Shipping a Slice with any failed Step is rejected by the Slice rollup verifier
4. Cross-tier verifier catches a PR that breaks a completed Arc
5. Security verifier flags SQL injection / path traversal / secret leakage / shell meta in the diff

### Phases

#### Phase M-A14.P1 — STEP.md frontmatter schema + pydantic validator
**Goal:** `goal`, `verify_contract`, `depends_on[]`, `model_profile`, `snapshots[]`, `cost_cap`; `extra = "forbid"`.
**Depends on:** M-A1.P2
**Requirements:** BLD-02
**Parallelizable:** yes

#### Phase M-A14.P2 — Step state machine (StepMachine)
**Goal:** Per ARCHITECTURE §8.1 pseudocode; on_event handler; event-driven transitions.
**Depends on:** M-A14.P1, M-A5.P7
**Requirements:** BLD-01
**Parallelizable:** yes with P3

#### Phase M-A14.P3 — Product Slice/Phase/Arc scoping containers (simpler FSMs)
**Goal:** `planned → in_progress → shipped | abandoned`.
**Depends on:** M-A14.P1
**Requirements:** BLD-01
**Parallelizable:** yes with P2

#### Phase M-A14.P4 — Goal-backward verifier (reads STEP.md goal → walks diff → asserts)
**Goal:** Verify contract runner: `tests`, `lsp`, `script` types; writes VERIFY.md pass/fail + evidence.
**Depends on:** M-A14.P1, M-A14.P2
**Requirements:** BLD-03, BLD-09
**Parallelizable:** yes with P5..P9

#### Phase M-A14.P5 — Slice rollup verifier
**Goal:** Aggregate Step verify results; fail Slice if any Step failed.
**Depends on:** M-A14.P4
**Requirements:** BLD-04
**Parallelizable:** yes with P6..P9

#### Phase M-A14.P6 — Phase rollup verifier + Phase-level integration tests
**Goal:** Aggregate Slice rollups plus Phase-level integration tests.
**Depends on:** M-A14.P5
**Requirements:** BLD-05
**Parallelizable:** yes with P7..P9

#### Phase M-A14.P7 — Product-Arc rollup verifier
**Goal:** Aggregate product-Phase rollups plus product-Arc acceptance criteria.
**Depends on:** M-A14.P6
**Requirements:** BLD-06
**Parallelizable:** yes with P8, P9

#### Phase M-A14.P8 — Cross-tier integration verifier (runs after Arc boundary)
**Goal:** Checks interactions between completed Arcs; rollback if regression.
**Depends on:** M-A14.P7
**Requirements:** BLD-07
**Parallelizable:** yes with P9

#### Phase M-A14.P9 — Security verifier (part 1 — input guards: SQLi, path traversal, secret leak, shell meta)
**Goal:** Per-Step; diff-based; uses regex + libs for known patterns.
**Depends on:** M-A14.P4
**Requirements:** BLD-08, SEC-01, SEC-02, SEC-03
**Parallelizable:** yes with P5..P8

#### Phase M-A14.P10 — Gray-area decision plumbing (detection + dialog routing)
**Goal:** Planner detects ambiguity; emits `state.decision.asked`; routes to dialog OR logs to DECISIONS.md per config.
**Depends on:** M-A14.P2, M-A8.P5
**Requirements:** CMD-08
**Parallelizable:** yes

#### Phase M-A14.P11 — Verifier integration + 10-Step golden fixture suite
**Goal:** E2E: plan → execute → verify on 10 fixture Steps; assert expected pass/fail.
**Depends on:** M-A14.P4..P10
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A15 — Build Core Commands (plan/execute/verify/ship)

**Version:** v0.4
**Goal:** The canonical build-mode cycle — `/state:build:discuss`, `/state:build:plan`, `/state:build:execute`, `/state:build:verify`, `/state:build:ship`, `/state:build:quick` — with plan-checker agent and gray-area routing.
**Depends on:** M-A14, M-A4 (ship needs worktree+snapshot)
**Tier:** 3a
**Complexity:** L

**Opencode surface extended:**
- opencode `command.*`, `task` tool, `Snapshot` service

**Source influence:**
- `state-inputs/get-shit-done/commands/gsd/plan-phase.md`, `execute-phase.md`, `verify-work.md`, `ship.md`

**.state/ artifacts written:**
- `.state/build/steps/<id>/DISCUSS.md`, `PLAN.md`, `EXECUTE.log`, `VERIFY.md`
- `.state/build/decisions/*.md`

**MCP tool surface delivered (full semantics):** `discuss_step`, `plan_step`, `execute_step`, `verify_step` (semantics), `slice_ship`

**Verifier:** End-to-end: create Step → discuss → plan → execute → verify → ship. Fail verify → revert via snapshot. Plan-checker agent rejects PLAN.md that won't achieve goal. Gray-area decision recorded in DECISIONS.md.

**Requirements covered:** CMD-01, CMD-02, CMD-03, CMD-04, CMD-05, CMD-06, CMD-07, CMD-08

**Success criteria:**
1. User runs `/state:build:discuss <step>` and gets multi-turn clarification dialog that writes DISCUSS.md
2. User runs `/state:build:plan` → PLAN.md with task decomposition + test plan + risks
3. User runs `/state:build:execute` → atomic commits per sub-task, EXECUTE.log
4. User runs `/state:build:verify` → chain of verifiers → VERIFY.md pass/fail
5. User runs `/state:build:ship` → PR opened + code review + Slice finalized

### Phases

#### Phase M-A15.P1 — `/state:build:discuss <step>` command (multi-turn clarification)
**Goal:** Task-based subagent; writes DISCUSS.md on completion; state → DISCUSSING.
**Depends on:** M-A14.P2, M-A12.P4
**Requirements:** CMD-01
**Parallelizable:** yes

#### Phase M-A15.P2 — `/state:build:plan <step>` command (task decomposition, test plan, risks)
**Goal:** Emits PLAN.md with structured sections.
**Depends on:** M-A15.P1
**Requirements:** CMD-02
**Parallelizable:** yes with P4

#### Phase M-A15.P3 — Plan-checker agent (validates PLAN will achieve goal)
**Goal:** Before `execute`, plan-checker reviews PLAN.md against STEP.md goal; blocks on red.
**Depends on:** M-A15.P2
**Requirements:** CMD-07
**Parallelizable:** no

#### Phase M-A15.P4 — `/state:build:execute <step>` command (atomic commits)
**Goal:** Dispatches to worker; one commit per sub-task; EXECUTE.log.
**Depends on:** M-A15.P3, M-A4.P7
**Requirements:** CMD-03
**Parallelizable:** yes with P5

#### Phase M-A15.P5 — `/state:build:verify <step>` command (runs verifier chain)
**Goal:** Invokes M-A14 verifier chain; writes VERIFY.md; advances or reverts Step.
**Depends on:** M-A14.P4, M-A15.P4
**Requirements:** CMD-04
**Parallelizable:** no

#### Phase M-A15.P6 — `/state:build:ship <slice>` command (PR + code review + finalize)
**Goal:** Opens PR via `gh`; triggers code-review; on green, finalizes Slice; Slice snapshot.
**Depends on:** M-A4.P8, M-A15.P5
**Requirements:** CMD-05
**Parallelizable:** yes

#### Phase M-A15.P7 — `/state:build:quick <description>` fast path
**Goal:** Skip Arc/Phase scaffolding; inline Slice+Step; execute end-to-end in one command.
**Depends on:** M-A15.P4, M-A15.P5
**Requirements:** CMD-06
**Parallelizable:** yes

#### Phase M-A15.P8 — Gray-area decision routing (dialog vs DECISIONS.md)
**Goal:** Detect ambiguity in planner; surface via `ui.DialogSelect` (TUI) or append to DECISIONS.md (per config).
**Depends on:** M-A14.P10
**Requirements:** CMD-08
**Parallelizable:** yes

#### Phase M-A15.P9 — Revert-on-fail wiring (verify fail → snapshot revert)
**Goal:** On `state.step.verify_failed`, call `Snapshot.revert` to `pre_verify` hash.
**Depends on:** M-A15.P5, M-A4.P7
**Requirements:** CMD-04
**Parallelizable:** no

#### Phase M-A15.P10 — End-to-end integration test (discuss → plan → execute → verify → ship)
**Goal:** 3-Step fixture Slice; exercises full happy path and revert path.
**Depends on:** M-A15.P1..P9
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A16 — Build GSD Command Ports + Net-New Product-Hierarchy Commands

> **Disambiguator (vocabulary):** Commands named `new-phase`, `add-phase`, `remove-phase` in this milestone operate on the **product-Phase tier** (Arc → Phase → Slice → Step per PROJECT.md / CLAUDE.md lines 48–49). They are NET-NEW scaffolding — GSD has no Arcs or Slices. They are not GSD-phase ports. See PROJECT.md cardinal rules for the vocabulary boundary.

**Version:** v0.5
**Goal:** Port existing GSD commands as state-native Step workflows — code-review, intel, map-codebase, debug, forensics, pause/resume-work, thread, workstreams, stats, audit-uat, audit-milestone, docs-update, backlog/todos/notes, undo, ui-phase/review, autonomous, onboard/help, explore, brainstorm, scan, cleanup, reapply-patches, review, set-quality/profile/settings, health, manager. Plus net-new product-hierarchy commands (no GSD equivalents): new-arc, new-phase (product-Phase tier), new-slice, insert-slice, add-phase, remove-phase, multi-arc.
**Depends on:** M-A15
**Tier:** 3a
**Complexity:** XL

**Opencode surface extended:** `task` tool + built-in tools (skill, plan mode, lsp, permission)

**Source influence:** `state-inputs/get-shit-done/commands/gsd/*.md` (50+ files, each inventoried)

**.state/ artifacts written:**
- `.state/build/intel/*.md`, `.state/build/codebase/*.md`
- `.state/build/backlog/*.md`, `.state/build/todos/*.md`, `.state/build/notes/*.md`
- `.state/build/forensics/<run>/*.md`
- `.state/build/threads/*.md`, `.state/build/workstreams/*.md`

**MCP tool surface delivered (full semantics):** `code_review`, `debug_session`, `forensics`, `intel_refresh`, `pause_work`, `resume_work` (from M-A12 skeleton); plus CLI `state:build:*` commands

**Verifier:** Three assertion classes — (a) file-emitter commands (new-arc, new-phase, new-slice, insert-slice, add-phase, remove-phase, docs-update, backlog/todos/notes, stats, health, etc.): golden-file fixture per command exercises input/output contract; (b) subagent-spawning commands (code-review, intel, forensics, debug, map-codebase): task-completion assertion against synthetic Step fixture; (c) batch/DAG commands (multi-arc, insert-slice, add-phase, remove-phase): DAG-validity assertion on generated product-Slice/Phase graph.

**Requirements covered:** PORT-01 through PORT-30 (all 30 GSD port requirements)

**Success criteria:**
1. User can run `/state:build:code-review` on a Slice and get reviewer feedback + fix Steps enqueued
2. User can run `/state:build:forensics` and get a post-mortem against git + event log + artifacts
3. User can pause a Slice mid-execute and resume hours later with full context restored
4. User can batch-plan multiple Arcs from a feature dump via `/state:build:multi-arc`
5. All 30 commands accessible via TUI command palette

### Phases

#### Phase M-A16.P1 — `/state:build:code-review` + `/state:build:code-review-fix`
**Goal:** Ports gsd-code-reviewer + gsd-code-fixer; spawns task subagents; emits fix Steps.
**Depends on:** M-A15.P10
**Requirements:** PORT-01
**Parallelizable:** yes

#### Phase M-A16.P2 — `/state:build:intel` (codebase intelligence refresh)
**Goal:** Parallel intel subagents; writes `.state/build/intel/`.
**Depends on:** M-A15.P10
**Requirements:** PORT-02
**Parallelizable:** yes

#### Phase M-A16.P3 — `/state:build:map-codebase` (parallel mappers → CODEMAP.md)
**Goal:** Multi-agent; writes `.state/build/codebase/`.
**Depends on:** M-A15.P10
**Requirements:** PORT-03
**Parallelizable:** yes

#### Phase M-A16.P4 — `/state:build:debug` (persistent debug session w/ scientific-method guardrails)
**Goal:** State machine: hypothesize → observe → test → conclude; session persisted.
**Depends on:** M-A15.P10
**Requirements:** PORT-04
**Parallelizable:** yes

#### Phase M-A16.P5 — `/state:build:forensics` (post-mortem vs git + events + artifacts)
**Goal:** Event replay + git log walk; writes forensics report.
**Depends on:** M-A1.P9, M-A15.P10
**Requirements:** PORT-05
**Parallelizable:** yes

#### Phase M-A16.P6 — `/state:build:pause-work` + `/state:build:resume-work` (context handoff)
**Goal:** STATE.md projection captures + restores hot context; Step state → paused/resumed.
**Depends on:** M-A14.P2
**Requirements:** PORT-06
**Parallelizable:** yes

#### Phase M-A16.P7 — `/state:build:thread` + `/state:build:workstreams` (persistent contexts, parallel streams)
**Goal:** Thread = cross-Phase side investigation; workstreams = multiple parallel work contexts in one project.
**Depends on:** M-A16.P6
**Requirements:** PORT-07, PORT-08
**Parallelizable:** yes

#### Phase M-A16.P8 — `/state:build:stats` + `/state:build:progress`
**Goal:** Project statistics (phases, plans, reqs, git, timeline); progress snapshot.
**Depends on:** M-A1.P9
**Requirements:** PORT-09 (also covers MCP `dag_status` surfacing)
**Parallelizable:** yes

#### Phase M-A16.P9 — `/state:build:audit-uat` + `/state:build:audit-milestone`
**Goal:** Cross-Slice UAT audit; Arc/Phase boundary audit.
**Depends on:** M-A14.P7, M-A15.P10
**Requirements:** PORT-10, PORT-11
**Parallelizable:** yes

#### Phase M-A16.P10 — `/state:build:docs-update` + `/state:build:backlog`/`todos`/`notes`
**Goal:** Regenerate project docs verified against code; capture surfaces for backlog/todos/notes.
**Depends on:** M-A15.P10
**Requirements:** PORT-12, PORT-13
**Parallelizable:** yes

#### Phase M-A16.P11 — `/state:build:undo` + `/state:build:ui-phase`/`ui-review` + `/state:build:autonomous`
**Goal:** Manifest-aware revert; UI spec + retroactive UI audit; autonomous runs all unblocked work.
**Depends on:** M-A4.P9, M-A15.P10
**Requirements:** PORT-14, PORT-15, PORT-16
**Parallelizable:** yes

#### Phase M-A16.P12 — `/state:build:onboard`/`help`/`explore`/`brainstorm`/`scan`/`cleanup`/`reapply-patches`
**Goal:** Discoverability + ideation + lightweight assessment + archive + patch-reapply.
**Depends on:** M-A15.P10
**Requirements:** PORT-17, PORT-18, PORT-19, PORT-20, PORT-21, PORT-22
**Parallelizable:** yes

#### Phase M-A16.P13 — Hierarchy bootstrapping (`/state:build:new-arc`/`new-phase`/`new-slice`/`insert-slice`/`add-phase`/`remove-phase`) + `/state:build:multi-arc`
**Goal:** Scaffolding commands + decimal-numbering insertion; batch plan multiple Arcs.
**Depends on:** M-A14.P3, M-A15.P10
**Requirements:** PORT-23, PORT-24, PORT-25, PORT-26
**Parallelizable:** yes

#### Phase M-A16.P14 — `/state:build:review` + `/state:build:set-quality`/`set-profile`/`settings` + `/state:build:health` + `/state:build:manager`
**Goal:** Cross-AI peer review from external CLIs; runtime toggles; health diagnosis; command center.
**Depends on:** M-A15.P10
**Requirements:** PORT-27, PORT-28, PORT-29, PORT-30
**Parallelizable:** yes

---

## M-A17 — Build TUI Extensions

**Version:** v0.5
**Goal:** Build-mode TUI: Arc/Phase/Slice/Step hierarchy browser, Step detail with discuss/plan/execute/verify tabs, commit browser with revert UI, gray-area decision dialog.
**Depends on:** M-A9, M-A14
**Tier:** 3a
**Complexity:** M

**Opencode surface extended:**
- `sidebar_content`, `route.register`, `ui.DialogSelect`, `ui.Slot`

**Source influence:** `state-inputs/get-shit-done/` gsd-statusline.js (ethos)

**.state/ artifacts written:** (UI only)

**MCP tool surface delivered:** (none; UI surface for M-A15/M-A16)

**Verifier:** Open build dashboard → see Arc hierarchy; click Step → 4 tabs; commit browser shows per-Step commits + working revert button; gray-area dialog surfaces + auto-decides per config.

**Requirements covered:** B-TUI-01, B-TUI-02, B-TUI-03, B-TUI-04

**Success criteria:**
1. `/state:build:dashboard` shows Arc/Phase/Slice/Step tree with drill-down
2. Clicking a Step opens a tabbed view (DISCUSS/PLAN/EXECUTE/VERIFY)
3. Commit browser shows per-Step commits with one-click revert
4. Gray-area decisions surface in a dialog with structured options

### Phases

#### Phase M-A17.P1 — Build dashboard route (`state.build.dashboard`)
**Goal:** `route.register`; product Arc/Phase/Slice/Step hierarchy (product-tier vocabulary, not GSD Milestone/Phase); burndown + verify-pass rate.
**Depends on:** M-A9.P1, M-A14.P3
**Requirements:** B-TUI-01
**Parallelizable:** yes

#### Phase M-A17.P2 — Hierarchy tree component (drill-down, collapse/expand)
**Goal:** SolidJS tree; SSE-driven updates.
**Depends on:** M-A17.P1
**Requirements:** B-TUI-01
**Parallelizable:** yes with P3..P5

#### Phase M-A17.P3 — Step detail view (DISCUSS/PLAN/EXECUTE/VERIFY tabs)
**Goal:** Tab component; markdown rendering; file links.
**Depends on:** M-A17.P1, M-A15.P1..P5
**Requirements:** B-TUI-02
**Parallelizable:** yes with P2, P4, P5

#### Phase M-A17.P4 — Commit browser with revert UI
**Goal:** Per-Step commits from events + git; revert triggers `snapshot_revert`.
**Depends on:** M-A4.P9, M-A17.P1
**Requirements:** B-TUI-03
**Parallelizable:** yes with P3, P5

#### Phase M-A17.P5 — Gray-area decision dialog (`ui.DialogSelect`)
**Goal:** Structured options from planner; auto-decide per config with manual override; persists `state.decision.made`.
**Depends on:** M-A14.P10, M-A9.P1
**Requirements:** B-TUI-04
**Parallelizable:** yes

#### Phase M-A17.P6 — Sidebar extensions (build-specific — current Slice DAG mini-view)
**Goal:** Refine M-A9.P3 sub-component.
**Depends on:** M-A9.P3
**Requirements:** B-TUI-01
**Parallelizable:** yes

#### Phase M-A17.P7 — Keyboard shortcuts + command palette integration
**Goal:** Quick-switch commands registered via `command.register`.
**Depends on:** M-A9.P1
**Requirements:** B-TUI-01
**Parallelizable:** yes

#### Phase M-A17.P8 — Build TUI integration test
**Goal:** E2E: create Arc → Phase → Slice → Step → ship; all TUI surfaces exercised.
**Depends on:** M-A17.P1..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A18 — Teach Kernel: Kolb + Concepts + Mental-Model

**Version:** v0.4
**Goal:** The heart of teach-mode — concept-graph projection, Kolb state machine (CE → RO → AC → AE), event-sourced mental-model projection, concept-teacher orchestrator, next-concept selector, frustration-signal drop-to-simpler.
**Depends on:** M-A5 (scheduler for review queues), M-A13 (MCP)
**Tier:** 3b
**Complexity:** L

**Opencode surface extended:**
- `experimental.chat.system.transform` (system prompt with concept card + Kolb stage + personality)
- `tool.execute.after` (observation capture)

**Source influence:**
- `~/.claude/agent-of-learning/workflows/teach.md`
- `~/.claude/agent-of-learning/workflows/state.md`
- AOL `aol-concept-teacher` skill
- AOL `knowledge-graph.json` schema (rebuildable projection)

**.state/ artifacts written:**
- `.state/teach/subjects/<subject>/CONCEPT-GRAPH.json` (projection)
- `.state/teach/learners/<learner>/MENTAL-MODEL.json` (projection)
- `.state/teach/learners/<learner>/OBSERVATIONS.jsonl` (append-only, authoritative)
- `.state/teach/learners/<learner>/confidence.jsonl`, `mistakes.jsonl` (AOL-compat)

**MCP tool surface delivered (full semantics):** `concept_next`, `concept_teach`, `observation_record`, `mental_model_show`, `learner_state`, `subject_pick`

**Verifier:** Seed 10 synthetic observations → project mental model; rebuild from OBSERVATIONS.jsonl → byte-identical; Kolb machine transitions through CE/RO/AC/AE/MASTERED given event fixtures; frustration signal drops scaffold level.

**Requirements covered:** TCH-01, TCH-02, TCH-03, TCH-04, TCH-05, TCH-06, TCH-07, TCH-08

**Success criteria:**
1. User can `state teach next-concept` and get the right next concept given current mastery
2. Teaching a concept walks through full Kolb cycle with opencode `question` tool in RO stage
3. Rebuilding MENTAL-MODEL.json from OBSERVATIONS.jsonl produces identical projection
4. Frustration signal (detected from observations) auto-drops to simpler mode
5. Raw user inputs never appear in observations (schema-validated, structured-only)

### Phases

#### Phase M-A18.P1 — Concept-graph schema (CONCEPT-GRAPH.json) + CONCEPT.md frontmatter
**Goal:** Pydantic models: `Concept`, `Edge`, `Prerequisite`; `scaffold_levels`, `teaching_modes`, `observation_rules`.
**Depends on:** M-A1.P2
**Requirements:** TCH-01
**Parallelizable:** yes

#### Phase M-A18.P2 — Subject-loading + concept-graph projection
**Goal:** Load `.state/teach/subjects/<id>/*` → build graph; rebuildable from `state.concept.introduced` events.
**Depends on:** M-A18.P1
**Requirements:** TCH-01
**Parallelizable:** yes

#### Phase M-A18.P3 — Kolb state machine (CE → RO → AC → AE → MASTERED)
**Goal:** Per ARCHITECTURE §9.2 pseudocode; one machine instance per active concept.
**Depends on:** M-A18.P1
**Requirements:** TCH-02
**Parallelizable:** yes with P4..P6

#### Phase M-A18.P4 — Mental-model projection (event-sourced from OBSERVATIONS.jsonl)
**Goal:** `project_mental_model(events)` per ARCHITECTURE §9.4; Bayesian mastery update placeholder (full math in M-A19).
**Depends on:** M-A18.P3
**Requirements:** TCH-03
**Parallelizable:** yes with P3, P5, P6

#### Phase M-A18.P5 — Observation recording (schema-validated, structured-only)
**Goal:** Pydantic `Observation` with `extra = "forbid"`; rejects freeform text; writes to OBSERVATIONS.jsonl + events.
**Depends on:** M-A18.P1, M-A13.P4
**Requirements:** TCH-07, MCP-T-05
**Parallelizable:** yes

#### Phase M-A18.P6 — Rebuild MENTAL-MODEL.json on demand (`state teach mental-model rebuild`)
**Goal:** CLI; reads OBSERVATIONS.jsonl → replays → writes projection.
**Depends on:** M-A18.P4
**Requirements:** TCH-08
**Parallelizable:** yes

#### Phase M-A18.P7 — Concept-teacher orchestrator (mode selection + personality + Kolb stage)
**Goal:** `concept_teach` tool dispatches to correct mode (M-A20) + personality (M-A21) + current Kolb stage.
**Depends on:** M-A18.P3
**Requirements:** TCH-04
**Parallelizable:** no

#### Phase M-A18.P8 — Next-concept selector (`concept_next`)
**Goal:** Given current mastery + prereq graph, pick next concept; surfaces via CLI + MCP.
**Depends on:** M-A18.P2, M-A18.P4
**Requirements:** TCH-06
**Parallelizable:** yes

#### Phase M-A18.P9 — Frustration-signal detection + drop-to-simpler
**Goal:** Pattern-match OBSERVATIONS.jsonl (e.g., 3 errors in 5 min) → emit `state.concept.frustration_detected` → mode-selector drops to simpler.
**Depends on:** M-A18.P5
**Requirements:** TCH-05
**Parallelizable:** yes

#### Phase M-A18.P10 — Learner privacy guard (no raw-input leakage verifier)
**Goal:** Regression test: scan OBSERVATIONS.jsonl for prose patterns; fail if found.
**Depends on:** M-A18.P5
**Requirements:** TCH-07
**Parallelizable:** yes

#### Phase M-A18.P11 — Teach-kernel integration test (Kolb walkthrough w/ fixture concept)
**Goal:** E2E: introduce concept → Kolb CE→RO (question)→AC→AE (drill stub)→MASTERED.
**Depends on:** M-A18.P1..P10
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A19 — Teach Drill Engine

**Version:** v0.5
**Goal:** Drill-prepare + drill-verify tools bound to opencode `question` tool, with Bayesian mastery update (formula verified against AOL source), ≤3000-token drill prompts, plain-stdin fallback for non-opencode hosts.
**Depends on:** M-A18
**Tier:** 3b
**Complexity:** M

**Opencode surface extended:**
- `state-inputs/opencode/packages/opencode/src/question/index.ts`
- built-in `question` tool

**Source influence:**
- AOL `aol drill prepare` / `aol drill verify` (internals — flagged as MEDIUM confidence in SUMMARY §10; deep-dive required)
- `~/.claude/agent-of-learning/workflows/teach.md` drill phase

**.state/ artifacts written:**
- Events: `state.drill.prepared`, `state.drill.submitted`, `state.drill.graded`
- SQLite: `concepts` table `mastery_probability` updates

**MCP tool surface delivered (full semantics):** `drill_prepare`, `drill_verify`, `drill_stats`

**Verifier:** Drill prompt Hypothesis property test ≤3000 tokens; Bayesian update formula matches AOL golden fixture; graded drill updates mental-model; fallback stdin drill runs on bare CLI.

**Requirements covered:** DRL-01, DRL-02, DRL-03, DRL-04, DRL-05, DRL-06

**Success criteria:**
1. `drill_prepare` generates concept + Kolb-stage-appropriate drill ≤3000 tokens
2. `drill_verify` grades response and updates mastery probability via Bayesian update
3. Drill prompts bind to opencode `question` tool for structured input on primary host
4. Bayesian update formula matches AOL's reference implementation
5. `state teach drill` CLI runs drills on plain stdin for non-opencode hosts

### Phases

#### Phase M-A19.P1 — AOL drill-verify internals deep-dive research (MEDIUM → HIGH)
**Goal:** Read `~/.claude/agent-of-learning/` drill code; document exact Bayesian update formula; golden fixture.
**Depends on:** M-A18.P4
**Requirements:** DRL-05 (prep)
**Parallelizable:** yes
**Note:** Flagged as research gap in SUMMARY §10.

#### Phase M-A19.P2 — `drill_prepare` tool (generate drill per concept + Kolb stage)
**Goal:** Tool impl; reads CONCEPT.md `scaffold_levels`; ≤3000 tokens.
**Depends on:** M-A13.P3, M-A19.P1, M-A18.P7
**Requirements:** DRL-01, DRL-04
**Parallelizable:** yes with P3

#### Phase M-A19.P3 — Drill prompt token cap enforcement (Hypothesis property test)
**Goal:** Any generated drill ≤3000 tokens across 1000 property-test iterations.
**Depends on:** M-A19.P2
**Requirements:** DRL-04
**Parallelizable:** yes

#### Phase M-A19.P4 — opencode `question` tool binding (route drill prompts through question.ask)
**Goal:** `client.question.ask(sessionID, questions)` → typed answers.
**Depends on:** M-A13.P3
**Requirements:** DRL-03
**Parallelizable:** yes

#### Phase M-A19.P5 — `drill_verify` tool (grade + update mental-model event)
**Goal:** Grader; emits `state.drill.graded` with score; triggers mastery update.
**Depends on:** M-A19.P2, M-A19.P4
**Requirements:** DRL-02
**Parallelizable:** no

#### Phase M-A19.P6 — Bayesian mastery update (formula from M-A19.P1)
**Goal:** Implement prior → posterior; verified against AOL golden fixture.
**Depends on:** M-A19.P1, M-A19.P5
**Requirements:** DRL-05
**Parallelizable:** no

#### Phase M-A19.P7 — `drill_stats` tool (mastery projection)
**Goal:** Aggregates mental-model data → projection for next review time.
**Depends on:** M-A19.P6
**Requirements:** DRL-02 (surface)
**Parallelizable:** yes

#### Phase M-A19.P8 — `state teach drill` CLI fallback (plain stdin)
**Goal:** For non-opencode hosts; same grader path; stdin I/O.
**Depends on:** M-A19.P5
**Requirements:** DRL-06
**Parallelizable:** yes

#### Phase M-A19.P9 — End-to-end drill test (concept → prepare → question → verify → mental-model update)
**Goal:** E2E with real opencode + fixture concept.
**Depends on:** M-A19.P1..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A20 — Teach Four Modes + Selector

**Version:** v0.5
**Goal:** PRIMM, Scaffolded, Socratic, Constructivist modes as first-class state machines + mastery-based selector (PRIMM <30% → Scaffolded 30–50% → Socratic 50–70% → Constructivist 70–80%), manual override, drop-to-simpler.
**Depends on:** M-A18
**Tier:** 3b
**Complexity:** XL

**Opencode surface extended:**
- `chat.params` (mode-specific temperature + params per personality)

**Source influence:**
- `~/.claude/skills/primm.md`
- `~/.claude/skills/scaffolded.md`
- `~/.claude/skills/socratic.md`
- `~/.claude/skills/constructivist.md`

**.state/ artifacts written:**
- `.state/teach/modes/active-mode.json`
- Events: `state.mode.activated` (teach-scope)

**MCP tool surface delivered (full semantics):** `mode_select` (surfaced via `concept_teach`)

**Verifier:** Each mode FSM runs a full concept teach via its own state machine (PRIMM, Scaffolded, Socratic, Constructivist — M-A20.P2–P5); mastery-based selector picks correct mode at each boundary (<30% → PRIMM, 30–50% → Scaffolded, 50–70% → Socratic, 70–80% → Constructivist); manual override sticks until explicitly cleared (M-A20.P7); drop-to-simpler triggered by frustration signal from M-A18.P9 (M-A20.P8); per-mode temperature injection into `chat.params` (M-A20.P9); per-mode system-prompt templates applied (M-A20.P10). M-A20.P11 four-mode golden-fixture test is the integrating assertion.

**Requirements covered:** MODE-P-01, MODE-S-01, MODE-SO-01, MODE-C-01, MODE-SEL-01, MODE-SEL-02, MODE-SEL-03

**Success criteria:**
1. Running PRIMM mode walks learner through predict → run → investigate → modify → make for a concept
2. Scaffolded mode offers graduated hints matching `scaffold_levels` in CONCEPT.md
3. Socratic mode never gives direct answers — always question-led
4. Constructivist mode with minimal scaffolding lets learner build-your-own
5. Auto-selector picks PRIMM for new concept, progresses to Constructivist as mastery rises

### Phases

#### Phase M-A20.P1 — Shared plumbing implementation (SUMMARY Q2 resolution — hosted in M-A18 kernel)
**Goal:** Implement shared plumbing (selector + drop-to-simpler + Kolb + observation emission) hosted in M-A18 kernel; four modes (P2–P5) consume. SUMMARY Q2 decision already resolved in STATE.md line 92 — this phase is scaffolding, not discussion.
**Depends on:** M-A18.P11
**Requirements:** (infrastructure)
**Parallelizable:** no

#### Phase M-A20.P2 — PRIMM mode state machine (predict / run / investigate / modify / make)
**Goal:** 5-stage FSM per concept; system-prompt injection per stage.
**Depends on:** M-A20.P1
**Requirements:** MODE-P-01
**Parallelizable:** yes with P3..P5

#### Phase M-A20.P3 — Scaffolded mode (graduated hints, prereq reinforcement, worked examples)
**Goal:** Reads `scaffold_levels` from CONCEPT.md; progression logic.
**Depends on:** M-A20.P1
**Requirements:** MODE-S-01
**Parallelizable:** yes with P2, P4, P5

#### Phase M-A20.P4 — Socratic mode (question-led discovery, no direct answers)
**Goal:** System-prompt guard: never provide answers; question-generation heuristic.
**Depends on:** M-A20.P1
**Requirements:** MODE-SO-01
**Parallelizable:** yes with P2, P3, P5

#### Phase M-A20.P5 — Constructivist mode (build-your-own, minimal scaffolding)
**Goal:** Minimal system prompts; learner drives; observer-only teacher.
**Depends on:** M-A20.P1
**Requirements:** MODE-C-01
**Parallelizable:** yes with P2, P3, P4

#### Phase M-A20.P6 — Mastery-based mode selector (PRIMM <30% → Scaffolded → Socratic → Constructivist)
**Goal:** Reads `mastery_probability`; picks mode with threshold crossings.
**Depends on:** M-A20.P2, M-A20.P3, M-A20.P4, M-A20.P5
**Requirements:** MODE-SEL-01
**Parallelizable:** no

#### Phase M-A20.P7 — Manual override (learner picks mode)
**Goal:** CLI + MCP: set active mode; selector respects override until cleared.
**Depends on:** M-A20.P6
**Requirements:** MODE-SEL-02
**Parallelizable:** yes

#### Phase M-A20.P8 — Drop-to-simpler on frustration signal
**Goal:** Subscribe to `state.concept.frustration_detected`; decrement mode; emit `state.mode.activated`.
**Depends on:** M-A20.P6, M-A18.P9
**Requirements:** MODE-SEL-03
**Parallelizable:** yes

#### Phase M-A20.P9 — Mode-specific `chat.params` injection (temperature per mode)
**Goal:** Low-temp Socratic (0.3), mid Scaffolded (0.5), higher PRIMM/Constructivist (0.7+).
**Depends on:** M-A8.P9, M-A20.P2..P5
**Requirements:** (wiring; supports MODE-*)
**Parallelizable:** yes

#### Phase M-A20.P10 — Per-mode system-prompt templates
**Goal:** Mode-specific preambles injected via `experimental.chat.system.transform`.
**Depends on:** M-A8.P7, M-A20.P2..P5
**Requirements:** (wiring)
**Parallelizable:** yes

#### Phase M-A20.P11 — Four-mode golden-fixture test
**Goal:** Teach same concept in all 4 modes; assert distinct behaviors via event patterns.
**Depends on:** M-A20.P1..P10
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A21 — Teach Personalities + Teaching Style

**Version:** v0.5
**Goal:** Port all 7 AOL personalities verbatim as text blocks, inject via `chat.params`/`chat.headers` system prompt, 7-dimension teaching-style config, per-subject personality override.
**Depends on:** M-A18
**Tier:** 3b
**Complexity:** M

**Opencode surface extended:**
- `chat.params`, `chat.headers`
- `agent.options` (read for defaults)

**Source influence:**
- `~/.claude/agent-of-learning/personalities/*.md` (all 7 — verbatim port)
- AOL `workflows/style.md`

**.state/ artifacts written:**
- `.state/teach/personalities/*.md` (ports)
- `.state/teach/style.json` (7-dim config)
- `.state/teach/subjects/<id>/personality-override.md` (optional per-subject)

**MCP tool surface delivered (full semantics):** `style_edit`, `personality_set` (surfaced via `concept_teach`)

**Verifier:** Loading each of 7 personalities produces expected system-prompt substring; 7-dim style edit round-trips via CLI; per-subject override takes precedence over global.

**Requirements covered:** PER-01, PER-02, PER-03, PER-04

**Success criteria:**
1. User sees 7 personalities available via `state teach personality list`
2. Switching personality changes teacher tone in real time (system prompt injected)
3. `state teach style edit` walks through 7 dimensions + saves
4. Per-subject personality override wins over global when active

### Phases

#### Phase M-A21.P1 — Port 7 AOL personalities verbatim
**Goal:** Copy `~/.claude/agent-of-learning/personalities/*.md` → `.state/teach/personalities/`; no semantic changes; attribution preserved.
**Depends on:** M-A18.P1
**Requirements:** PER-01
**Parallelizable:** yes

#### Phase M-A21.P2 — Personality loader (reads file, prepares system-prompt block)
**Goal:** Pydantic `Personality` model; loader reads + validates.
**Depends on:** M-A21.P1
**Requirements:** PER-01
**Parallelizable:** yes with P3

#### Phase M-A21.P3 — Inject personality via `chat.params` / `chat.headers` system prompt
**Goal:** Integrated with `experimental.chat.system.transform` hook (M-A8.P7).
**Depends on:** M-A21.P2, M-A8.P7
**Requirements:** PER-02
**Parallelizable:** yes

#### Phase M-A21.P4 — 7-dimension teaching-style schema
**Goal:** `TeachingStyle` pydantic model: warmth, directness, humor, formality, patience, challenge, explicitness.
**Depends on:** M-A21.P1
**Requirements:** PER-03
**Parallelizable:** yes

#### Phase M-A21.P5 — CLI: `state teach style edit` (interactive 7-dim editor)
**Goal:** Typer + rich interactive prompt; saves to `.state/teach/style.json`.
**Depends on:** M-A21.P4
**Requirements:** PER-03
**Parallelizable:** yes

#### Phase M-A21.P6 — Per-subject personality override
**Goal:** Subject frontmatter or `personality-override.md`; override precedence rules.
**Depends on:** M-A21.P2
**Requirements:** PER-04
**Parallelizable:** yes

#### Phase M-A21.P7 — Personality + style integration with modes (M-A20)
**Goal:** Mode system-prompt template composed with personality preamble and style dimensions.
**Depends on:** M-A20.P10, M-A21.P3, M-A21.P4
**Requirements:** (integration)
**Parallelizable:** yes

#### Phase M-A21.P8 — Regression test (personality substring in system prompt)
**Goal:** For each personality, spawn session → assert substring present in outgoing system prompt.
**Depends on:** M-A21.P1..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A22 — Scaffolding-Mentor + Coding-Partner

**Version:** v0.6
**Goal:** Two first-class teach workflows — scaffolding-mentor (guides file-by-file skeleton; records structural decisions; never takes keyboard) and coding-partner (watches code; graduated hints when stuck; teaches prereqs; session growth note; never writes code for learner).
**Depends on:** M-A20, M-A21
**Tier:** 3b
**Complexity:** L

**Opencode surface extended:**
- `permission.ask` (keyboard-handoff guard)
- `task` tool (subagent for observation)

**Source influence:**
- `~/.claude/agent-of-learning/skills/aol-scaffolding-mentor.md`
- `~/.claude/agent-of-learning/skills/coding-partner.md`

**.state/ artifacts written:**
- `.state/teach/sessions/<session>/SCAFFOLD-LOG.md`
- `.state/teach/sessions/<session>/PARTNER-LOG.md`
- `.state/teach/sessions/<session>/GROWTH-NOTE.md` (end-of-session)

**MCP tool surface delivered (full semantics):** `mentor_scaffold`, `coding_partner`

**Verifier:** Scaffolding-mentor never calls `edit` / `write` on learner code (permission.ask blocks); coding-partner emits observations but never `write`; end-of-session growth note gate triggers.

**Requirements covered:** SCA-01, SCA-02, SCA-03, CPT-01, CPT-02, CPT-03, CPT-04

**Success criteria:**
1. Scaffolding-mentor walks learner through creating project skeleton file-by-file, asking learner to write each
2. Every file creation records structural-decision observation
3. Neither scaffolding-mentor nor coding-partner ever writes code for the learner (permission layer)
4. Coding-partner detects "stuck" signal and offers graduated hints from PROJECT-PLAN.md prereqs
5. Session end triggers growth-note gate recording accomplishments

### Phases

#### Phase M-A22.P1 — Scaffolding-mentor state machine + system-prompt template
**Goal:** FSM: introduce → plan → create-file-N → reflect → next; system prompt emphasizes "never take keyboard".
**Depends on:** M-A20.P1, M-A21.P3
**Requirements:** SCA-01
**Parallelizable:** yes with P2

#### Phase M-A22.P2 — Scaffolding-mentor observation hooks (file creation, structural decision)
**Goal:** Tap `tool.execute.after` for file-creation events; record observations.
**Depends on:** M-A8.P4, M-A22.P1
**Requirements:** SCA-02
**Parallelizable:** yes

#### Phase M-A22.P3 — Keyboard-handoff guard (permission.ask blocks mentor-initiated writes)
**Goal:** `permission.ask` hook in scaffolding-mentor mode refuses edit/write by the agent.
**Depends on:** M-A8.P5, M-A22.P1
**Requirements:** SCA-03
**Parallelizable:** yes

#### Phase M-A22.P4 — Coding-partner state machine + system-prompt template
**Goal:** FSM: observe → detect-stuck → hint-level-1 → hint-level-2 → hint-level-3 → back to observe.
**Depends on:** M-A20.P1, M-A21.P3
**Requirements:** CPT-01
**Parallelizable:** yes with P5

#### Phase M-A22.P5 — Prereq teacher (from PROJECT-PLAN.md)
**Goal:** Detect missing prereqs in learner's code; proactively teach before continuing.
**Depends on:** M-A22.P4
**Requirements:** CPT-02
**Parallelizable:** yes

#### Phase M-A22.P6 — Accomplishments logger + end-of-session growth-note gate
**Goal:** Append to PARTNER-LOG.md; session-end event triggers growth-note write.
**Depends on:** M-A22.P4
**Requirements:** CPT-03
**Parallelizable:** yes

#### Phase M-A22.P7 — Coding-partner keyboard guard (never writes code for learner)
**Goal:** `permission.ask` hook in coding-partner mode refuses edit/write.
**Depends on:** M-A8.P5, M-A22.P4
**Requirements:** CPT-04
**Parallelizable:** yes

#### Phase M-A22.P8 — Scaffolding-mentor + coding-partner handoff (common session)
**Goal:** Mentor finishes scaffold → coding-partner takes over; shared session state.
**Depends on:** M-A22.P3, M-A22.P7
**Requirements:** (integration)
**Parallelizable:** yes

#### Phase M-A22.P9 — Golden-session regression test
**Goal:** Simulated learner session; assert no agent writes; growth note generated; observations recorded.
**Depends on:** M-A22.P1..P8
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A23 — Teach TUI Extensions

**Version:** v0.6
**Goal:** Teach-mode TUI: subject + concept-graph + mastery heatmap dashboard, drill UI (question card / input / feedback), mental-model viewer with mastery badges, session timeline.
**Depends on:** M-A9, M-A18
**Tier:** 3b
**Complexity:** M

**Opencode surface extended:**
- `route.register`, `ui.Prompt`, `ui.DialogSelect`, `ui.Slot`

**Source influence:** `~/.claude/agent-of-learning/workflows/state.md`

**.state/ artifacts written:** (UI only)

**MCP tool surface delivered:** (none; UI surface)

**Verifier:** Teach dashboard renders concept graph + heatmap; drill UI replaces prompt input during drill; mental-model viewer shows tree + badges; timeline shows observations, mode transitions, drill history.

**Requirements covered:** T-TUI-01, T-TUI-02, T-TUI-03, T-TUI-04

**Success criteria:**
1. `/state:teach:dashboard` shows subject + concept graph + mastery heatmap
2. During a drill, the session prompt input is replaced with drill input (timer visible)
3. Mental-model viewer shows concept tree with mastery badges + last-drilled dates
4. Session timeline shows observations, mode transitions, drill history

### Phases

#### Phase M-A23.P1 — Teach dashboard route (`state.teach.dashboard`)
**Goal:** `route.register`; subject picker + concept graph + mastery heatmap.
**Depends on:** M-A9.P1, M-A18.P2
**Requirements:** T-TUI-01
**Parallelizable:** yes

#### Phase M-A23.P2 — Concept graph visualization (SolidJS + opentui)
**Goal:** Topological layout; prereq edges; clickable concepts.
**Depends on:** M-A23.P1
**Requirements:** T-TUI-01
**Parallelizable:** yes with P3, P4, P5

#### Phase M-A23.P3 — Mastery heatmap (concept × mastery band)
**Goal:** Color-coded grid; hover → detail.
**Depends on:** M-A23.P1, M-A18.P4
**Requirements:** T-TUI-01
**Parallelizable:** yes with P2, P4, P5

#### Phase M-A23.P4 — Drill UI (`ui.Prompt` replacement during drill)
**Goal:** Replace session prompt with drill question card + answer input + timer + feedback panel.
**Depends on:** M-A23.P1, M-A19.P4
**Requirements:** T-TUI-02
**Parallelizable:** yes with P2, P3, P5

#### Phase M-A23.P5 — Mental-model viewer (concept tree + mastery badges)
**Goal:** Tree component; last-drilled / next-review dates; badge colors.
**Depends on:** M-A23.P1, M-A18.P4
**Requirements:** T-TUI-03
**Parallelizable:** yes with P2, P3, P4

#### Phase M-A23.P6 — Session timeline (observations, mode transitions, drill history)
**Goal:** Chronological timeline; filter by aggregate.
**Depends on:** M-A23.P1, M-A1.P9
**Requirements:** T-TUI-04
**Parallelizable:** yes

#### Phase M-A23.P7 — Sidebar extension (teach — refines M-A9.P4)
**Goal:** Current concept + Kolb stage + mastery bar + next-drill timer.
**Depends on:** M-A9.P4
**Requirements:** TUI-02 (teach side)
**Parallelizable:** yes

#### Phase M-A23.P8 — Teach TUI integration test
**Goal:** E2E: subject → concept → drill → mastered; all surfaces exercised.
**Depends on:** M-A23.P1..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A24 — Subject Authoring + 4-Gate Promoter

**Version:** v0.6
**Goal:** Conversational subject-authoring workflow (interview → concept-graph approval → draft → promote) with subject schema validation.
**Depends on:** M-A18
**Tier:** 3b
**Complexity:** M

**Opencode surface extended:** (none directly — uses MCP tools + task subagent)

**Source influence:**
- `~/.claude/agent-of-learning/workflows/build-subject.md`
- `~/.claude/agent-of-learning/workflows/new.md`

**.state/ artifacts written:**
- `.state/teach/subjects/<subject>/SUBJECT.md`
- `.state/teach/subjects/<subject>/concepts/<concept>/CONCEPT.md`
- `.state/teach/subjects/<subject>/DRAFT/` (staging dir)

**MCP tool surface delivered (full semantics):** `subject_new`, `subject_edit`, `subject_promote`, `subject_author`

**Verifier:** Author → promote flow produces schema-valid subject + concept graph; 4 gates block invalid drafts; interview covers required SUBJECT.md fields.

**Requirements covered:** SUB-01, SUB-02, SUB-03, SUB-04

**Success criteria:**
1. User runs `state teach subject new` and gets a conversational interview
2. 4 gates block promotion until: interview complete, concept graph approved, draft validated, promote acknowledged
3. Subject + concept graph round-trip through schema validation
4. CLI `state teach subject edit <id>` + `promote <id>` work

### Phases

#### Phase M-A24.P1 — SUBJECT.md + CONCEPT.md schema (pydantic, `extra = "forbid"`)
**Goal:** Schema per ARCHITECTURE §11.2; validator.
**Depends on:** M-A18.P1
**Requirements:** SUB-04
**Parallelizable:** yes

#### Phase M-A24.P2 — Conversational interview workflow (Gate 1)
**Goal:** Task subagent: asks required questions; writes DRAFT/SUBJECT.md draft.
**Depends on:** M-A24.P1, M-A13.P3
**Requirements:** SUB-01, SUB-02 (gate 1)
**Parallelizable:** yes

#### Phase M-A24.P3 — Concept-graph authoring (Gate 2: graph approval)
**Goal:** Propose concepts + prereq edges; user approves or edits.
**Depends on:** M-A24.P2
**Requirements:** SUB-01, SUB-02 (gate 2)
**Parallelizable:** yes

#### Phase M-A24.P4 — Draft staging (Gate 3: draft validation)
**Goal:** Generate full `DRAFT/` tree; run validator; surface errors.
**Depends on:** M-A24.P3
**Requirements:** SUB-02 (gate 3)
**Parallelizable:** yes

#### Phase M-A24.P5 — Promote command (Gate 4: explicit acknowledgement)
**Goal:** `state teach subject promote <id>`; moves DRAFT/ → canonical path; emits `state.subject.promoted`.
**Depends on:** M-A24.P4
**Requirements:** SUB-02 (gate 4), SUB-03
**Parallelizable:** no

#### Phase M-A24.P6 — `state teach subject new|edit` CLI
**Goal:** Typer commands; `new` invokes interview; `edit` opens existing for amendment.
**Depends on:** M-A24.P2, M-A24.P3
**Requirements:** SUB-03
**Parallelizable:** yes

#### Phase M-A24.P7 — Schema-validation test suite (golden + malformed fixtures)
**Goal:** Property test: valid fixtures pass; each mandatory field missing → fails with clear error.
**Depends on:** M-A24.P1
**Requirements:** SUB-04
**Parallelizable:** yes

#### Phase M-A24.P8 — 4-gate integration test (end-to-end authoring run)
**Goal:** Synthetic interview → approve graph → validate draft → promote → subject appears in `subject list`.
**Depends on:** M-A24.P1..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A25 — Migration & Import

**Version:** v0.7
**Goal:** Importers for existing GSD `.planning/` and AOL `.aol/` into `.state/build/` and `.state/teach/` respectively, with event-log replay preserving history and dry-run diff preview.
**Depends on:** M-A1, M-A11
**Tier:** 4
**Complexity:** M

**Opencode surface extended:** (none directly — CLI surface)

**Source influence:**
- `state-inputs/get-shit-done/` (reverse of `from-gsd2.md`)
- `~/.claude/agent-of-learning/` directory layout

**.state/ artifacts written:**
- `.state/build/` migrated Arcs/Phases (or best-effort mapping from milestones)
- `.state/teach/` migrated subjects/learners
- Events: `state.migration.run`, `state.migration.item_migrated`

**MCP tool surface delivered:** (none; CLI `state migrate from-gsd` / `from-aol`)

**Verifier:** Dry-run on fixture GSD + AOL project shows expected diff; apply → produces schema-valid `.state/` tree; round-trip: migrate → export → re-import → identical projections.

**Requirements covered:** MIG-01, MIG-02, MIG-03, MIG-04

**Success criteria:**
1. User with existing GSD project can run `state migrate from-gsd --dry-run` and see a diff preview
2. Applying the migration produces a schema-valid `.state/build/` tree
3. AOL project migrates via `state migrate from-aol` preserving OBSERVATIONS history
4. Migration events are replayable (can replay migration from the event log)

### Phases

#### Phase M-A25.P1 — `state migrate from-gsd` importer (reads `.planning/` → writes `.state/build/`)
**Goal:** Best-effort mapping: GSD milestones → Arcs, phases → Phases, plans → Slices; preserves REQUIREMENTS.md traceability.
**Depends on:** M-A14.P1
**Requirements:** MIG-01
**Parallelizable:** yes

#### Phase M-A25.P2 — `state migrate from-aol` importer (reads `.aol/` → writes `.state/teach/`)
**Goal:** Subject + concepts + OBSERVATIONS.jsonl + mental model + confidence/mistakes → `.state/teach/`; preserves array shape (P1-7).
**Depends on:** M-A18.P1
**Requirements:** MIG-02
**Parallelizable:** yes

#### Phase M-A25.P3 — Event replay of migration actions (auditable)
**Goal:** Each migration step is an event; full migration replayable from log; idempotence.
**Depends on:** M-A1.P9, M-A25.P1, M-A25.P2
**Requirements:** MIG-03
**Parallelizable:** yes

#### Phase M-A25.P4 — Dry-run mode + diff preview
**Goal:** `--dry-run` flag; rich-rendered diff of intended writes; no filesystem changes.
**Depends on:** M-A25.P1, M-A25.P2
**Requirements:** MIG-04
**Parallelizable:** yes

#### Phase M-A25.P5 — AOL array-shape preservation (P1-7 defence)
**Goal:** Multi-credential arrays preserved even for single-credential sources; round-trip test 1/2/5 creds.
**Depends on:** M-A25.P2
**Requirements:** MIG-02
**Parallelizable:** yes

#### Phase M-A25.P6 — Import from opencode `auth.json` (first-run migration path)
**Goal:** Refinement of M-A2.P11; treat as a migration, not ambient bootstrap.
**Depends on:** M-A2.P11, M-A25.P1
**Requirements:** AUTH-11 (shared)
**Parallelizable:** yes

#### Phase M-A25.P7 — GSD-2pi analysis integration
**Goal:** Use `state-inputs/gsd-2pi-codebase-analysis/10-python-rebuild-mapping.md` as a mapping authority; capture unknown field warnings.
**Depends on:** M-A25.P1
**Requirements:** MIG-01
**Parallelizable:** yes

#### Phase M-A25.P8 — Migration integration test (fixture GSD + AOL projects)
**Goal:** Canned fixture repo; migrate; verify projections; re-migrate → no-op.
**Depends on:** M-A25.P1..P7
**Requirements:** (verifier)
**Parallelizable:** no (final)

---

## M-A26 — Portability Shims

**Version:** v0.8
**Goal:** Claude Code, Gemini CLI, Qwen Code MCP-only shims — reduced UX (no TUI, no bus subscription), host capability detection with graceful degradation when `question`/TUI slots/`Snapshot` are missing.
**Depends on:** M-A12, M-A13
**Tier:** 4
**Complexity:** L

**Opencode surface extended:** (none — these are non-opencode hosts)

**Source influence:** (new)

**.state/ artifacts written:** (same as opencode — cross-host reusable)

**MCP tool surface delivered:** (MCP surface from M-A12/M-A13 exposed across hosts via stdio)

**Verifier:** Each host spawns with MCP server(s); attempts `question`-backed drill → fallback to stdin; snapshot missing → graceful degrade; CLI guidance in CLAUDE.md for Claude Code.

**Requirements covered:** PORT-SHIM-01, PORT-SHIM-02, PORT-SHIM-03, PORT-SHIM-04

**Success criteria:**
1. User on Claude Code can register `state-build` MCP server via CLAUDE.md guidance and run `plan_step`
2. User on Gemini CLI can register both MCP servers via its config
3. Drill falls back to plain stdin when host lacks `question` tool
4. Snapshot-missing host logs a warning and continues without Step-level revert

### Phases

#### Phase M-A26.P1 — Host-capability detection (`HostCapabilities` negotiation)
**Goal:** Probe host for `question` tool, snapshot, TUI slots, worktree service; report capabilities to daemon.
**Depends on:** M-A12.P1, M-A13.P1
**Requirements:** PORT-SHIM-04
**Parallelizable:** yes

#### Phase M-A26.P2 — Graceful degradation logic
**Goal:** Each feature has a degraded path when its capability is missing (drill → stdin, snapshot → git-only, TUI → CLI rich-render).
**Depends on:** M-A26.P1
**Requirements:** PORT-SHIM-04
**Parallelizable:** yes

#### Phase M-A26.P3 — Claude Code shim (MCP registration + CLAUDE.md guidance)
**Goal:** Document registration flow; ship CLAUDE.md template with slash-command guidance.
**Depends on:** M-A26.P1, M-A26.P2
**Requirements:** PORT-SHIM-01
**Parallelizable:** yes with P4, P5

#### Phase M-A26.P4 — Gemini CLI shim (MCP stdio registration)
**Goal:** Register both MCP servers via Gemini CLI config; first-run auth import from Gemini's own store where applicable.
**Depends on:** M-A26.P1, M-A26.P2
**Requirements:** PORT-SHIM-02
**Parallelizable:** yes with P3, P5

#### Phase M-A26.P5 — Qwen Code shim (MCP stdio registration)
**Goal:** Register both MCP servers; document setup.
**Depends on:** M-A26.P1, M-A26.P2
**Requirements:** PORT-SHIM-03
**Parallelizable:** yes with P3, P4

#### Phase M-A26.P6 — pygit2 worktree fallback activation (per-host)
**Goal:** When opencode HTTP worktree unreachable, use pygit2 (already in M-A4.P3); activate via capability detection.
**Depends on:** M-A4.P3, M-A26.P1
**Requirements:** WRK-02 (cross-host runtime)
**Parallelizable:** yes

#### Phase M-A26.P7 — Cross-host parity test matrix
**Goal:** Run same 10 reference tool invocations on all 3 hosts; assert equivalent outputs (minus TUI).
**Depends on:** M-A26.P3, M-A26.P4, M-A26.P5
**Requirements:** (verifier; TST-05)
**Parallelizable:** no

#### Phase M-A26.P8 — Portability documentation (DOC-08 prep)
**Goal:** Setup guide per host; known limitations; feeds M-A27.
**Depends on:** M-A26.P3, M-A26.P4, M-A26.P5
**Requirements:** DOC-08
**Parallelizable:** yes

---

## M-A27 — Release & Packaging

**Version:** v1.0
**Goal:** v1 release — `pyproject.toml` with `uv_build`, `uvx state install` one-command installer, wheel includes plugin TS source + bun build output, `state update` auto-check, remote skill registry, release-notes generator, all documentation, full test infrastructure, security baseline verification, observability finalization.
**Depends on:** M-A1, M-A8, M-A11, M-A12, M-A13, M-A14, M-A26 (hard); all other M-A1..M-A24 (soft — feature completeness)
**Tier:** 4
**Complexity:** M
**P0 pitfalls owned:** P0-14 (shared with M-A2 — release-time redactor regression in M-A27.P9)

**Opencode surface extended:**
- `cfg.skills.urls` (skill registry)
- `TuiPluginInstallOptions` (install discovery)

**Source influence:** `state-inputs/get-shit-done/` gsd update command

**.state/ artifacts written:**
- (none — release artifacts outbound)

**MCP tool surface delivered:** (finalization — all prior tools)

**Verifier:** `uvx state install` on clean macOS + Linux auto-registers plugin + MCP; `state update` checks PyPI; skill `add <url>` fetches + registers; release-notes generator produces valid markdown from event log.

**Requirements covered:** REL-01, REL-02, REL-03, REL-04, REL-05, REL-06, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, TST-01, TST-02, TST-03, TST-04, TST-05, TST-06, TST-07, TST-08, OBS-01, OBS-02, OBS-03, OBS-04, SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06

**Success criteria:**
1. User runs `uvx state install` on macOS or Linux and plugin + both MCP servers register automatically
2. User runs `state update` and gets prompt to upgrade when newer version on PyPI
3. User runs `state skills add <url>` and community skill appears in opencode's skill list
4. All 16 P0 pitfalls have regression tests (TST-08) — green
5. All v1 documentation (8 guides) published and linked from README

### Phases

#### Phase M-A27.P1 — `pyproject.toml` with `uv_build` backend (full dep pins per STACK.md)
**Goal:** Complete `pyproject.toml`; CI install-from-source check.
**Depends on:** M-A1.P1
**Requirements:** REL-01
**Parallelizable:** yes

#### Phase M-A27.P2 — `uvx state install` installer (detect opencode, auto-register)
**Goal:** Typer command; detects opencode binary; adds plugin + MCP to `opencode.json`.
**Depends on:** M-A27.P1, M-A8.P12, M-A12.P1, M-A13.P1
**Requirements:** REL-02
**Parallelizable:** yes

#### Phase M-A27.P3 — Wheel bundling (plugin TS source + bun build output)
**Goal:** Build pipeline: `bun build` plugin → include in wheel; CI verifies wheel contents.
**Depends on:** M-A8.P12, M-A27.P1
**Requirements:** REL-03
**Parallelizable:** yes

#### Phase M-A27.P4 — `state update` PyPI version check + upgrade prompt
**Goal:** Typer command; queries PyPI; prompts; invokes `uv pip install -U state`.
**Depends on:** M-A27.P1
**Requirements:** REL-04
**Parallelizable:** yes

#### Phase M-A27.P5 — Remote skill registry (`state skills add <url>`)
**Goal:** Fetches manifest; integrates with opencode `cfg.skills.urls` mechanism.
**Depends on:** M-A27.P1
**Requirements:** REL-05
**Parallelizable:** yes

#### Phase M-A27.P6 — Release-notes generator (from commit history + phase artifacts)
**Goal:** Walks event log + git log; produces structured release notes.
**Depends on:** M-A1.P9
**Requirements:** REL-06
**Parallelizable:** yes

#### Phase M-A27.P7 — Documentation — all 8 guides (architecture, user, command ref, build-author, teach-author, plugin-dev, auth setup, portability)
**Goal:** Written throughout earlier milestones but finalized here; cross-linked; version-locked.
**Depends on:** M-A1, M-A27.P1 (hard — docs source-of-truth + structure scaffold); all other M-A1..M-A26 (soft — feature-complete docs coverage)
**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08
**Parallelizable:** yes

#### Phase M-A27.P8 — Full test infrastructure + P0 regression suite (all 16 pitfalls)
**Goal:** pytest + pytest-asyncio (strict_asyncio), Hypothesis property tests, E2E opencode fixture, provider parity matrix, captured-header regression, mode-isolation import-graph, P0 regression tests.
**Depends on:** M-A1, M-A2, M-A3, M-A4, M-A5, M-A6, M-A7, M-A8, M-A9, M-A10, M-A11, M-A12, M-A13, M-A14, M-A15, M-A16, M-A17, M-A18, M-A19, M-A20, M-A21, M-A22, M-A23, M-A24, M-A25, M-A26 (hard — each milestone's verifier phase must ship before P0-regression matrix is green)
**Requirements:** TST-01, TST-02, TST-03, TST-04, TST-05, TST-06, TST-07, TST-08
**Parallelizable:** yes

#### Phase M-A27.P9 — Observability finalization (structlog, redactor, event-log forensics, CLI `state logs tail`)
**Goal:** Final wiring; `state logs tail [--level] [--component]` CLI; OpenTelemetry hooks present but opt-in (v2).
**Depends on:** M-A2.P10, M-A6.P7
**Requirements:** OBS-01, OBS-02, OBS-03, OBS-04
**Parallelizable:** yes

#### Phase M-A27.P10 — Security baseline (path-traversal, prompt-injection, shell-meta, regex-DoS, JSON-bomb, chmod-0600 verifiers)
**Goal:** All guards attached to every surface; per-Step security verifier (refinement of M-A14.P9); regression tests.
**Depends on:** M-A14.P9, M-A2.P2
**Requirements:** SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06
**Parallelizable:** yes

---

# Requirements Traceability

All 221 v1 REQ-IDs are mapped to exactly one phase. See `REQUIREMENTS.md` Traceability table for the full matrix.

| Category | Requirements | Milestone |
|---|---|---|
| EVT (8) | EVT-01..EVT-08 | M-A1 |
| AUTH (13) | AUTH-01..AUTH-13 | M-A2 |
| PRV (9) | PRV-01..PRV-09 | M-A3 |
| WRK (13) | WRK-01..WRK-13 | M-A4 (WRK-01..09) + M-A7 (WRK-10..13) |
| DAG (7) | DAG-01..DAG-07 | M-A5 |
| DAE (9) | DAE-01..DAE-09 | M-A6 |
| HOOK (11) | HOOK-01..HOOK-11 | M-A8 |
| TUI (5) | TUI-01..TUI-05 | M-A9 |
| DAG-VIEW (4) | DAG-VIEW-01..04 | M-A10 |
| MODE (7) | MODE-01..MODE-07 | M-A11 |
| MCP-B (6) | MCP-B-01..06 | M-A12 |
| MCP-T (6) | MCP-T-01..06 | M-A13 |
| BLD (9) | BLD-01..BLD-09 | M-A14 |
| CMD (8) | CMD-01..CMD-08 | M-A15 |
| PORT (30) | PORT-01..PORT-30 | M-A16 |
| B-TUI (4) | B-TUI-01..04 | M-A17 |
| TCH (8) | TCH-01..TCH-08 | M-A18 |
| DRL (6) | DRL-01..DRL-06 | M-A19 |
| MODE-* (7) | MODE-P-01, MODE-S-01, MODE-SO-01, MODE-C-01, MODE-SEL-01..03 | M-A20 |
| PER (4) | PER-01..PER-04 | M-A21 |
| SCA + CPT (7) | SCA-01..03, CPT-01..04 | M-A22 |
| T-TUI (4) | T-TUI-01..04 | M-A23 |
| SUB (4) | SUB-01..SUB-04 | M-A24 |
| MIG (4) | MIG-01..MIG-04 | M-A25 |
| PORT-SHIM (4) | PORT-SHIM-01..04 | M-A26 |
| REL (6) | REL-01..REL-06 | M-A27 |
| DOC (8) | DOC-01..DOC-08 | M-A27 (threaded throughout, finalized here) |
| TST (8) | TST-01..TST-08 | M-A27 (threaded; finalized) |
| OBS (4) | OBS-01..OBS-04 | M-A27 (w/ redactor in M-A2.P10) |
| SEC (6) | SEC-01..SEC-06 | M-A27 (w/ security verifier in M-A14.P9 and auth vault in M-A2.P2) |

**Total:** 221 v1 requirements → 256 phases across 27 milestones. **Coverage: 100%.**

---

## Notes for Plan-Phase

1. Each Phase will be decomposed into Slices + Steps by `/gsd:plan-phase <milestone> <phase>`.
2. Parallelizable phases within a milestone should be scheduled on separate worktrees when M-A4 is ready.
3. `Depends on:` edges in each phase inform the DAG scheduler's `depends_on` typed edges.
4. P0 pitfall defences are explicitly called out per phase; verifiers MUST include a P0 regression test before phase closure.
5. Opencode surface file paths are load-bearing — reviewers should open those files and confirm the extension surface is unchanged.

---

*Roadmap created: 2026-04-22*
*Last updated: 2026-04-22 after initial creation*
