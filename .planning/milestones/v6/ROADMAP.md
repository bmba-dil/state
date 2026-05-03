# v6 — State Daemon (HTTP + SSE + Mode Middleware)

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 050–059 (10 phases)

---

## Phases

#### Phase 050 — Starlette (or bare) HTTP server + unix socket binding
**Goal:** `asyncio.start_unix_server`, JSON-RPC 2.0 framing, request router.
**Depends on:** 004
**Requirements:** DAE-05
**Parallelizable:** yes with 051

#### Phase 051 — pid-file + start_time_ns + stale detection
**Goal:** `.state/daemon.pid` with `{pid, start_time_ns}`; `/proc/<pid>/stat` on Linux, `ps -o lstart=` on macOS; stale → remove and start fresh.
**Depends on:** 001
**Requirements:** DAE-03
**Parallelizable:** yes with 050
**P0 pitfall:** P0-15

#### Phase 052 — Unix socket path (`$XDG_RUNTIME_DIR/state-<hash>.sock` / tmp fallback)
**Goal:** Project-hash-based socket name; fallback when `$XDG_RUNTIME_DIR` missing (macOS).
**Depends on:** 050
**Requirements:** DAE-04
**Parallelizable:** yes

#### Phase 053 — Mode-enforcement HTTP middleware (canonical gate)
**Goal:** Every request carries `mode` header; validator against `.state/mode.json` rejects mismatches with 403; **authoritative mode-isolation point**.
**Depends on:** 050, 004
**Requirements:** DAE-05, MODE-05
**Parallelizable:** no (depends on v11 schema too — soft dep)

#### Phase 054 — SSE bus broadcast endpoint
**Goal:** `/events/subscribe` SSE stream fan-out of event-store updates; multi-client support; heartbeats.
**Depends on:** 050, 009
**Requirements:** DAE-06
**Parallelizable:** yes with 053

#### Phase 055 — launchd plist + systemd --user unit + installer
**Goal:** `state daemon install` drops plist/unit, enables at login; uninstall removes.
**Depends on:** 051
**Requirements:** DAE-01
**Parallelizable:** yes

#### Phase 056 — structlog + RotatingFileHandler + log rotation config
**Goal:** JSON mode + dev-renderer mode; size + time rotation; retention cap; redactor attached (020).
**Depends on:** 020
**Requirements:** DAE-07
**Parallelizable:** yes

#### Phase 057 — Crash recovery (replay STATE.md projection + resume in-flight Steps)
**Goal:** On start, read last events, rebuild STATE.md projection, find Steps in `executing`/`verifying` → resume from last checkpoint.
**Depends on:** 007, 038
**Requirements:** DAE-08
**Parallelizable:** no

#### Phase 058 — CLI: `state daemon start|stop|restart|status|logs`
**Goal:** Typer commands; `status` shows pid + start_time + events-count + mode; `logs` tails daemon.log.
**Depends on:** 051, 055
**Requirements:** DAE-09
**Parallelizable:** yes

#### Phase 059 — Auth-manager wiring into daemon (provider refresh, rotation)
**Goal:** Daemon owns the auth refresh loop; multi-cred round-robin surfaced via HTTP `GET /auth/status`.
**Depends on:** 013, 050
**Requirements:** AUTH-07, AUTH-08 (runtime wiring)
**Parallelizable:** no (integration)

---

