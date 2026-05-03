
# PITFALLS Research — `state` Project

## P0 Rollup (Release Blockers)

| # | Pitfall | Surface | Maps to Arc |
|---|---------|---------|-------------|
| P0-1 | Missing `user-agent: claude-cli/<version>` header on Anthropic OAuth request | Auth / Anthropic stealth | Auth Arc |
| P0-2 | Missing `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…` header | Auth / Anthropic stealth | Auth Arc |
| P0-3 | Missing `x-app: cli` header | Auth / Anthropic stealth | Auth Arc |
| P0-4 | Using `x-api-key` instead of Bearer for `sk-ant-oat` tokens | Auth / Anthropic stealth | Auth Arc |
| P0-5 | Registering a new OAuth client ID instead of reusing Claude Code's `9d1c250a-e61b-44d9-88ed-5944d1962f5e` | Auth / Anthropic stealth | Auth Arc |
| P0-6 | Dual-refresh race invalidates live token when two processes refresh concurrently | Auth / refresh lock | Auth Arc |
| P0-7 | `expires_in` used verbatim (no 5-min buffer) causes mid-request expiry | Auth / Anthropic stealth | Auth Arc |
| P0-8 | PKCE `state` not reused as verifier → server round-trip fails | Auth / Anthropic stealth | Auth Arc |
| P0-9 | SQLite event-sequence non-monotonic under crash → replay permanently breaks aggregate | Events / dual-write | Event Store Arc |
| P0-10 | Orphan locked worktrees accumulate until disk fills | Worktree | Worktree Arc |
| P0-11 | Mode isolation leakage: Build planning artifacts visible in Teach (or vice versa) | Cross-mode | Mode Isolation Arc |
| P0-12 | MCP tool-name collision between `state-build` and `state-teach` in the same opencode session | MCP | MCP Arc |
| P0-13 | `auth.json` left world-readable (chmod != 0600) — credential leak | Auth / vault | Auth Arc |
| P0-14 | Anthropic OAuth refresh path writes plaintext tokens to log when debug=true | Auth / secret leakage | Observability Arc |
| P0-15 | Daemon crash leaves stale pid file → subsequent `state` invocations refuse to start | Daemon lifecycle | Daemon Arc |
| P0-16 | TaskGroup silently swallows a CancelledError, deadlocking the DAG scheduler | Python 3.12 asyncio | Scheduler Arc |

---

## Surface 1: Anthropic OAuth Stealth Flow (Claude Code Subscription)

### P0-1 — Dropped `user-agent: claude-cli/<version>` header
**Surface:** Auth / Anthropic stealth
**Failure mode:** Anthropic silently downgrades the request from subscription-priced to API-key-priced inference (or returns 401). Users on Pro/Max hit their metered bill and think the tool is broken.
**Warning signs:** Token validates but requests return 401 with "invalid authentication" for `sk-ant-oat*` tokens; or billing dashboard shows API-key usage when user is on Pro/Max.
**Prevention:** Hard-code the header in the Anthropic client wrapper. Ship a unit test that captures every outgoing request header (via httpx transport mock) and asserts all three stealth headers are present. Never let any litellm code path touch this client — use direct SDK.
**Maps to Arc:** Auth Arc (Anthropic OAuth Slice) + Provider Routing Arc (escape-hatch rule).
**Severity:** P0

### P0-2 — Dropped `anthropic-beta: claude-code-20250219,oauth-2025-04-20,…` header
**Surface:** Auth / Anthropic stealth
**Failure mode:** Same as above — Anthropic's server disambiguates Claude Code requests via the beta flag combination. Missing the `oauth-2025-04-20` flag disables subscription-scoped inference entirely.
**Warning signs:** Token authenticates but returns permission-scoped errors on specific models; sudden quota exhaustion on free tier when user expected subscription tier.
**Prevention:** Pin the exact beta string in a constant; add a CI test that periodically curl-probes with/without the flag to detect upstream changes. Maintain a `CLAUDE_CODE_VERSION_LOCK.md` in `.state/` that tracks which claude-cli version we masquerade as and when it was last verified.
**Maps to Arc:** Auth Arc.
**Severity:** P0

### P0-3 — Dropped `x-app: cli` header
**Surface:** Auth / Anthropic stealth
**Failure mode:** Request identified as "not Claude Code" → subscription killswitch triggers.
**Warning signs:** Intermittent 403s that stop after upgrading to API-key mode.
**Prevention:** Include in header constant; test as above.
**Maps to Arc:** Auth Arc.
**Severity:** P0

### P0-4 — Using `x-api-key` instead of Bearer for `sk-ant-oat` tokens
**Surface:** Auth / Anthropic stealth
**Failure mode:** Server rejects OAuth token wire-shape; auth always fails.
**Warning signs:** Every OAuth request returns 401; logs show `x-api-key` header on outgoing request.
**Prevention:** Token-shape sniffer (`token.startswith("sk-ant-oat")`) must be the FIRST branch in the Anthropic client; API-key path is the fallback. Unit test covers both branches with snapshot assertions on outgoing headers.
**Maps to Arc:** Auth Arc.
**Severity:** P0

### P0-5 — Fresh OAuth client ID registration
**Surface:** Auth / Anthropic stealth
**Failure mode:** Anthropic's PKCE+state verification succeeds but the token issued is not recognized as a Claude Code token; subscription access is silently denied. Even worse, a fresh client ID may trip abuse-detection and invalidate the user's account.
**Warning signs:** Auth flow completes, token returned, but every inference request 403s.
**Prevention:** Hard-code Claude Code's ID `9d1c250a-e61b-44d9-88ed-5944d1962f5e` (base64-decoded at runtime to avoid scanner flags on the literal). Document *why* in a comment pointing to `claude-oauth.md`. Never expose this as a configurable value.
**Maps to Arc:** Auth Arc.
**Severity:** P0

### P0-6 — Concurrent token refresh invalidates live token
**Surface:** Auth / refresh lock
**Failure mode:** Two `state` processes (daemon + opencode worker, or two opencode sessions) both see an expiring token, both call the refresh endpoint. Anthropic invalidates the earlier refresh-token; one process's next request 401s mid-stream.
**Warning signs:** Mid-session "authentication expired" errors with no user action; corrupted `auth.json` where a just-refreshed token is already rejected.
**Prevention:** File-level lock on `auth.json` via `filelock` (cross-platform) with a 10-second timeout; inside the lock, *re-read* `auth.json` and check if another process already refreshed (refresh-token changed) before issuing the network call. Double-check pattern — don't refresh if someone beat us to it. **Do not** use SQLite advisory locks for this — auth must work even when the daemon is down.
**Maps to Arc:** Auth Arc (refresh lock Slice).
**Severity:** P0

### P0-7 — `expires_in` stored verbatim
**Surface:** Auth / Anthropic stealth
**Failure mode:** Long-running tool call starts 30 seconds before expiry, makes multiple API calls, first succeeds, second fails mid-stream with 401.
**Warning signs:** Intermittent mid-call 401s that correlate with long completions.
**Prevention:** Subtract 5 minutes (300s) from `expires_in` before storing. Refresh-on-read logic checks against the shaved expiry, not the raw value.
**Maps to Arc:** Auth Arc.
**Severity:** P0

### P0-8 — PKCE state parameter not reused as verifier
**Surface:** Auth / Anthropic stealth
**Failure mode:** Server-side state round-trip check fails; token exchange returns error.
**Warning signs:** Token exchange always returns `invalid_grant`.
**Prevention:** Generate verifier once; pass the same string as both PKCE `code_verifier` and OAuth `state`. This is the exact Claude Code flow — deviate at your peril.
**Maps to Arc:** Auth Arc.
**Severity:** P0

### P0-13 — `auth.json` permissions
**Surface:** Auth / vault
**Failure mode:** `.state/auth.json` created with default umask (typically 0644) exposes tokens to any local user. A compromised user account on a shared machine → compromised Anthropic subscription.
**Warning signs:** `ls -la .state/auth.json` shows world-readable; security-scanner flags.
**Prevention:** `os.open(path, O_WRONLY|O_CREAT, 0o600)` then `os.fchmod(fd, 0o600)` after write; never use `open(path, 'w')`. Verify mode on every read; refuse to proceed and log error if mode is wrong. Mirror GSD-pi's `auth-storage.ts` approach exactly.
**Maps to Arc:** Auth Arc (vault Slice).
**Severity:** P0

### P1-1 — `sk-ant-oat` vs `sk-ant-api` branch missing
**Surface:** Auth / vault
**Failure mode:** Single code path tries Bearer for all Anthropic tokens; API-key-users get 401.
**Warning signs:** Users report API keys stop working after switching to `state`.
**Prevention:** `isOAuthToken()` equivalent in Python — check prefix; route to correct auth header. Test with both fixture tokens.
**Maps to Arc:** Auth Arc.
**Severity:** P1

### P1-2 — Token paste UX silently strips `#state`
**Surface:** Auth / Anthropic stealth
**Failure mode:** User pastes `code#state` into a prompt that's validating as "code only"; split-on-`#` is not done; state check fails.
**Warning signs:** Token exchange fails immediately after paste; error mentions missing state.
**Prevention:** Accept full paste string; `code, _, state = pasted.partition("#")`; if no `#`, reject with a helpful message. Match GSD-pi's exact paste contract.
**Maps to Arc:** Auth Arc.
**Severity:** P1

### P2-1 — `anthropic-beta` string drift
**Surface:** Auth / Anthropic stealth
**Failure mode:** Claude Code adds a new beta flag (e.g., a new thinking version); we don't mirror; subscription quietly downgrades features.
**Warning signs:** New Claude features don't appear to be available even though Anthropic announced them.
**Prevention:** Document the version-lock process. When a new Claude Code release ships, re-capture its headers with a test script (`tools/check-claude-cli-headers.py`) and diff. Add a staleness warning if version-lock file is >60 days old.
**Maps to Arc:** Auth Arc + Observability Arc.
**Severity:** P2

---

## Surface 2: Gemini CLI Free-Tier OAuth

### P1-3 — Google OAuth client_secret committed obfuscated
**Surface:** Auth / Gemini
**Failure mode:** Security scanners flag obfuscated embedded credentials as malicious/malware → AV false positives, PyPI package rejections, users' environments quarantine the install.
**Warning signs:** Users report install blocked by corporate AV; Snyk/Trivy flags.
**Prevention:** Commit client_id + client_secret **in plaintext** with a code comment quoting the GSD-2pi rationale (Desktop OAuth pattern relies on PKCE + redirect URI validation, not secret confidentiality). Document in AUTH.md. Do **not** base64 or XOR.
**Maps to Arc:** Auth Arc.
**Severity:** P1

### P1-4 — Free-tier quota exhaustion not surfaced
**Surface:** Auth / Gemini
**Failure mode:** User hits Code Assist daily quota mid-workflow; next request returns 429 with a body the user can't interpret; `state` presents it as a generic "provider error."
**Warning signs:** 429s clustered at the end of a work session.
**Prevention:** Parse Gemini's 429 body; extract `quotaExceeded` + reset timestamp; surface via TUI toast with "switch model" call-to-action. Multi-cred round-robin should try the next credential automatically.
**Maps to Arc:** Provider Routing Arc + Multi-cred Arc.
**Severity:** P1

### P2-2 — Refresh token rotation silently drops new refresh-token
**Surface:** Auth / Gemini
**Failure mode:** Google rotates refresh tokens on every access-token refresh; storing only the access token loses the rotation → next refresh fails.
**Warning signs:** OAuth works for exactly one refresh cycle then stops; user must re-login.
**Prevention:** On every refresh response, persist *both* access AND refresh tokens even if unchanged. Write-through to `auth.json` inside the refresh lock.
**Maps to Arc:** Auth Arc.
**Severity:** P2

---

## Surface 3: Antigravity + Copilot Device-Code

### P1-5 — Device-code polling timeout leaks the verification URL
**Surface:** Auth / Copilot/Antigravity
**Failure mode:** User walks away mid-auth; 15-min timeout hits; polling loop exits without clearing the verification URL or instructing the user. Next auth attempt starts over but the user's browser still has the old prompt.
**Warning signs:** Users complain "I can't tell if auth worked"; stale OAuth state accumulates.
**Prevention:** Explicit timeout (15 min) with a user-visible countdown; on timeout, print a clear "authorization expired, restart" message and clear any transient state. Return structured failure, not silent exit.
**Maps to Arc:** Auth Arc.
**Severity:** P1

### P1-6 — Copilot grant revocation returns 200 with empty body
**Surface:** Auth / Copilot
**Failure mode:** User revokes Copilot access in GitHub settings; next refresh request returns 200 but with a null token; our code crashes on JSON parse or stores `null` as the access token.
**Warning signs:** Mysterious JSON parse errors during refresh; `auth.json` with `access_token: null`.
**Prevention:** Validate refresh response shape with pydantic; on any missing/null token, treat as "credentials revoked" and prompt user to re-login via TUI toast. Distinguish from network errors.
**Maps to Arc:** Auth Arc.
**Severity:** P1

### P2-3 — Antigravity scope drift
**Surface:** Auth / Antigravity
**Failure mode:** Google adds a required scope (e.g., a new `cclog` variant); our scope list is stale; auth succeeds but Claude-via-Google-Cloud requests return 403.
**Warning signs:** Antigravity path works for discovery but fails for inference.
**Prevention:** Scope list documented in code with a link to the Antigravity OAuth reference; periodic CI check against Google's discovery document.
**Maps to Arc:** Auth Arc.
**Severity:** P2

---

## Surface 4: API-Key Vault

### P0-14 — Tokens logged in plaintext when debug=true
**Surface:** Auth / secret leakage
**Failure mode:** User turns on debug logging for one session; `auth.json` contents get logged; log files get shared in bug reports; tokens leak.
**Warning signs:** `grep "sk-ant-" ~/.state/logs/*` returns hits.
**Prevention:** Custom log filter that redacts any string matching `sk-ant-*`, `sk-*`, `ya29.*`, or matching a compiled set of token regexes. Apply at the root logger — not per call site. Unit test the redactor with every known token shape. Refuse to start daemon if the redactor isn't attached.
**Maps to Arc:** Auth Arc + Observability Arc (logging Slice).
**Severity:** P0

### P1-7 — `auth.json` migration corrupts array shape
**Surface:** Auth / vault
**Failure mode:** First-run import from opencode's `auth.json` collapses GSD-pi's multi-credential array to a single object; round-robin silently stops working because there's only one credential.
**Warning signs:** Rate-limit fallback doesn't fire even with multiple credentials configured.
**Prevention:** Preserve the array shape always, even for single credentials. Migration tool promotes single-credential opencode auth to a 1-element array. Test: round-trip migration with 1, 2, and 5 credentials per provider.
**Maps to Arc:** Auth Arc + Migration Arc.
**Severity:** P1

### P2-4 — Backup of `auth.json` creates unsecured copies
**Surface:** Auth / vault
**Failure mode:** User or tooling backs up `.state/` to cloud storage; `auth.json` ends up in Dropbox/iCloud with default permissions.
**Warning signs:** —
**Prevention:** Ship a `.state/.gitignore` that ignores `auth.json`. Document in INSTALL.md: backup tooling should skip `auth.json`. Optional: OS keychain integration (phase 2+).
**Maps to Arc:** Auth Arc.
**Severity:** P2

---

## Surface 5: Multi-Cred Round-Robin + Refresh Lock

### P1-8 — Starvation: same credential refreshed forever
**Surface:** Auth / multi-cred
**Failure mode:** Round-robin picks credential 0; refresh lock serializes on it; credentials 1..N never get exercised; first-credential quota exhausts.
**Warning signs:** Usage heavily skewed to one credential; other credentials show no activity despite being configured.
**Prevention:** Index into credentials array with `(now_ms // bucket_ms) % len(creds)` — time-bucketed rotation — instead of "first not rate-limited." On 429, mark credential with a cool-down timestamp; round-robin skips cooled-down creds.
**Maps to Arc:** Multi-cred Arc.
**Severity:** P1

### P1-9 — Refresh lock deadlocks with daemon shutdown
**Surface:** Auth / refresh lock
**Failure mode:** Process A holds the `filelock` on `auth.json`, starts the HTTP refresh, hangs on network; daemon shutdown SIGTERMs process B which is waiting for the lock; the wait blocks cleanup.
**Warning signs:** Daemon hangs on shutdown; pid-file lingers; force-kill required.
**Prevention:** Refresh lock has a hard 10-second timeout for *acquisition* AND a 15-second timeout for the *HTTP refresh* inside the lock. SIGTERM handler in every worker releases lock via context manager unwind. Log every lock acquisition with duration.
**Maps to Arc:** Auth Arc + Daemon Arc.
**Severity:** P1

### P2-5 — Cross-process lock weak on NFS/SMB
**Surface:** Auth / refresh lock
**Failure mode:** User has `$HOME` on NFS; `filelock` doesn't provide atomic locking; dual-refresh race returns.
**Warning signs:** Token invalidation on multi-host setups.
**Prevention:** Document: `.state/` must be on a local filesystem. Detect NFS at startup (`/proc/mounts` / `mount | grep`) and warn. Offer `--auth-dir` override for users who need non-default location.
**Maps to Arc:** Auth Arc.
**Severity:** P2

---

## Surface 6: MCP Protocol

### P1-10 — Tool description token bloat
**Surface:** MCP
**Failure mode:** 40+ MCP tools × 300 tokens each = 12k+ tokens consumed on every LLM call before any user prompt. Doubled because `state-build` + `state-teach` register separately. Subscription users burn through context windows; costs balloon.
**Warning signs:** Low effective context; LLM reports it doesn't have room for file contents.
**Prevention:** Hard cap tool count at 15 per server (matches Christian Posta / Solo.io guidance). Consolidate related operations into single tools with enum `action` args (e.g., `phase.control` with `action: advance|revert|verify` beats three tools). Every tool description ≤ 80 tokens. Ship a `state dev tool-budget` command that reports token cost per tool. Rely on Anthropic prompt caching for repeat-session amortization.
**Maps to Arc:** MCP Arc + Observability Arc.
**Severity:** P1

### P1-11 — Schema validation swallows errors
**Surface:** MCP
**Failure mode:** Tool receives a malformed arg; pydantic raises; opencode's MCP client wraps in a generic "tool error"; the LLM gets no useful feedback and retries the same bad call.
**Warning signs:** Same tool called 3+ times in a row with similar args; conversation thrashing.
**Prevention:** Every tool wraps its handler in a try/except that returns a structured error with a `validation_errors: [...]` field the LLM can parse. Include field names and expected types. Test: send malformed args via mock MCP client, assert structured errors are surfaced to LLM.
**Maps to Arc:** MCP Arc.
**Severity:** P1

### P1-12 — Stateful tool leaks state across sessions
**Surface:** MCP
**Failure mode:** `state-build` tool accumulates in-process state (e.g., "current phase") keyed by nothing; session A's phase bleeds into session B.
**Warning signs:** Tools return "wrong phase" responses when multiple opencode sessions run concurrently.
**Prevention:** MCP server is **stateless per call** — every tool reads state from SQLite keyed by `sessionID` from the opencode-supplied context. No module-level mutable state. Test: run two pytest-asyncio sessions in parallel against the same MCP server; assert no cross-talk.
**Maps to Arc:** MCP Arc + Event Store Arc.
**Severity:** P1

### P2-6 — Streaming/progress semantics broken for long tools
**Surface:** MCP
**Failure mode:** A tool takes >30s (default `DEFAULT_TIMEOUT` in `opencode/src/mcp/index.ts:35`); opencode times it out even though it's making progress.
**Warning signs:** Long-running state tools timeout before completing.
**Prevention:** Use MCP's progress notifications (opencode calls `callTool` with `resetTimeoutOnProgress: true`); every long-running tool must emit progress updates at least every 20s. Unit test a tool with a deliberate 45s delay + progress emissions; assert no timeout.
**Maps to Arc:** MCP Arc.
**Severity:** P2

### P2-7 — Error propagation drops stack context
**Surface:** MCP
**Failure mode:** Tool panic surfaces to LLM as "Internal server error"; debugging requires reading daemon logs; user thinks product is broken.
**Warning signs:** Bug reports: "it just said error and stopped."
**Prevention:** Tool errors include a short human-readable message + a `trace_id` that correlates to a daemon log entry. `state doctor` and `/state:forensics` resolve trace_id → full stack.
**Maps to Arc:** MCP Arc + Observability Arc.
**Severity:** P2

---

## Surface 7: Two MCP Servers (state-build + state-teach)

### P0-12 — Tool-name collision across servers
**Surface:** MCP / two-server
**Failure mode:** Both servers register a tool called `phase.advance` (or `snapshot.take`); opencode's MCP registry uses `server_toolname` naming (`opencode/src/mcp/index.ts:660` does `sanitize(clientName) + "_" + sanitize(mcpTool.name)`), so technically no collision — BUT users see `state-build_phase_advance` AND `state-teach_phase_advance` and invoke the wrong one by habit.
**Warning signs:** Teach session invokes a build tool; state corruption; confused audit log.
**Prevention:** Tool names are already namespaced inside each server (`build.phase.advance` vs `teach.phase.advance`). Even after opencode's sanitize, the name is self-documenting. Every tool description starts with `[BUILD MODE]` or `[TEACH MODE]`. Runtime guard: `state-build` tools reject invocation if `.state/mode.json` says teach-mode is active; vice versa.
**Maps to Arc:** MCP Arc + Mode Isolation Arc.
**Severity:** P0

### P1-13 — Accidental registration of both servers in a build-only project
**Surface:** MCP
**Failure mode:** opencode.json registers both `state-build` and `state-teach`; teach tools pollute the LLM's tool list in a build-only project; 2× the token budget for zero value.
**Warning signs:** Tool counts doubled; teach tools appear in `/help`.
**Prevention:** First-run detection: if `.state/mode.json` specifies build only (or no teach/ dir exists), write an opencode.json snippet that enables only `state-build`. Ship `state install --mode=build` / `--mode=teach` / `--mode=both` to generate the right config.
**Maps to Arc:** MCP Arc + Install Arc.
**Severity:** P1

### P2-8 — Tool-list change notifications broadcast from wrong server
**Surface:** MCP
**Failure mode:** `state-build` reloads tools (e.g., plugin added); `mcp.tools.changed` event fires with `{server: "state-build"}`; plugin handler naively invalidates both servers' caches.
**Warning signs:** Spurious teach-mode tool reloads when build plugins change.
**Prevention:** Handlers filter on `event.server` before reloading. Integration test covers cross-server isolation.
**Maps to Arc:** MCP Arc.
**Severity:** P2

---

## Surface 8: Dual-Write Event Store (SyncEvent + SQLite)

### P0-9 — Event-sequence non-monotonic after crash
**Surface:** Events / dual-write
**Failure mode:** `state` daemon crashes mid-write after publishing to opencode SyncEvent but before inserting into `.state/events.sqlite`. Next startup: the SyncEvent seq has advanced, but our SQLite doesn't reflect it. On replay, `SyncEvent.replay` asserts `event.seq !== expected` and throws "Sequence mismatch for aggregate" — **permanent** until manual intervention (see `opencode/src/sync/index.ts:190`).
**Warning signs:** Daemon won't start; logs full of sequence mismatch errors; event aggregates get "wedged."
**Prevention:** Write to SQLite **first** (our system of record), then publish to opencode's SyncEvent. On startup, run a reconciliation pass: for each aggregate, compare our SQLite max seq to opencode's; if opencode is ahead, replay the missing events from opencode's event table into ours; if we're ahead, re-publish. Document this as the authoritative ordering: `.state/events.sqlite` is truth; SyncEvent is derived.
**Maps to Arc:** Event Store Arc.
**Severity:** P0

### P1-14 — Replay idempotency broken by non-deterministic data
**Surface:** Events / dual-write
**Failure mode:** Event payload contains `timestamp: datetime.now()` or a uuid; replay produces different projection than original; event sourcing's core guarantee dies.
**Warning signs:** Replay produces different SQLite state than live execution.
**Prevention:** Event payloads contain only deterministic data. Timestamps captured at the event site and passed in; no `datetime.now()` inside event handlers. IDs generated at event-creation time, not event-processing time. Replay is read-only against deterministic input.
**Maps to Arc:** Event Store Arc.
**Severity:** P1

### P1-15 — Clock skew across daemon + worker processes
**Surface:** Events / dual-write
**Failure mode:** Worker process's wall clock is 3 seconds ahead (multi-host edge case or NTP drift); events from worker interleave incorrectly with daemon events if ordering is timestamp-based.
**Warning signs:** Event ordering doesn't match causal ordering; rare but catastrophic when it happens.
**Prevention:** **Never order events by wall-clock timestamp.** Use monotonic sequence per aggregate (opencode already does this). All process-level logical clocks use `time.monotonic_ns()` from a single process; cross-process ordering goes through SQLite.
**Maps to Arc:** Event Store Arc.
**Severity:** P1

### P1-16 — Partial write recovery loses events
**Surface:** Events / dual-write
**Failure mode:** Power loss / OOM mid-transaction; SQLite WAL recovers but our in-memory queue of pending events is lost.
**Warning signs:** Events present in live TUI but not in replay.
**Prevention:** Use SQLite WAL mode with `synchronous=NORMAL` or `FULL`; events are durable before UI is notified. Emit-then-commit is the wrong order; commit-then-emit is correct. Startup replay emits all events since last known checkpoint.
**Maps to Arc:** Event Store Arc.
**Severity:** P1

### P2-9 — Event schema migration breaks old replays
**Surface:** Events / dual-write
**Failure mode:** A v2 event adds a required field; replaying v1 events against v2 projector throws.
**Warning signs:** Forensics/debug on old sessions crashes.
**Prevention:** Follow opencode's pattern (`opencode/src/sync/index.ts:66` — `versionedType`): register all historical versions of an event; projector accepts the union; adding a field is "new version"; removing a field requires a migration Slice.
**Maps to Arc:** Event Store Arc.
**Severity:** P2

---

## Surface 9: Always-On Daemon Lifecycle

### P0-15 — Stale pid-file refuses daemon start
**Surface:** Daemon
**Failure mode:** Daemon killed by OOM / kill -9 / laptop reboot without clean shutdown; pid-file contains the old PID; next `state` invocation reads pid-file, probes pid, either finds a different process (refuses to start) or the pid has been recycled (refuses to kill and overwrite).
**Warning signs:** `state daemon status` reports "already running" but nothing's listening on the socket.
**Prevention:** Pid-file contains `{pid, start_time_ns, socket_path}`. On startup, read pid-file; if pid exists, verify `/proc/<pid>/stat`'s start time matches. If mismatch → stale, safe to overwrite. If match but no listener on socket_path → stale. Only refuse start if a *real* daemon is alive.
**Maps to Arc:** Daemon Arc.
**Severity:** P0

### P1-17 — launchd/systemd re-entry loop after crash
**Surface:** Daemon
**Failure mode:** Daemon crashes on startup due to a bug (e.g., corrupted `.state/events.sqlite`); launchd/systemd KeepAlive respawns; each respawn crashes again; syslog fills.
**Warning signs:** Hundreds of entries in system log for daemon restart; CPU spike from repeated startup.
**Prevention:** Exponential-backoff wrapper script before daemon entry; max 5 restarts in 60 seconds before falling back to "manual intervention required" mode. Crash-cause detection: if startup fails >3x in a row, log the error prominently and wait for user action. Never configure `KeepAlive` without backoff.
**Maps to Arc:** Daemon Arc.
**Severity:** P1

### P1-18 — Zombie worker processes after opencode session exits
**Surface:** Daemon
**Failure mode:** Per-session worker spawned for opencode session; opencode session ends abnormally; worker keeps running forever, consuming memory and file handles. Mirrors the opencode MCP stdio cleanup pattern (`opencode/src/mcp/index.ts:533` does `descendants()` + SIGTERM — we need the equivalent).
**Warning signs:** Over time: `ps | grep state-worker` shows more processes than active opencode sessions.
**Prevention:** Workers register with daemon via heartbeat; daemon reaps workers that haven't heartbeat in 60s. Workers listen for parent opencode PID exit via `os.getppid()` polling (on Linux) or kqueue (on macOS). On SIGTERM, worker drains current work, flushes events, exits cleanly.
**Maps to Arc:** Daemon Arc.
**Severity:** P1

### P1-19 — Log rotation lost on crash
**Surface:** Daemon
**Failure mode:** Daemon holds open log file; crash; no flush; last ~4KB of log lost; exactly the 4KB that would have explained the crash.
**Warning signs:** Post-mortems with nothing in the log from the crash window.
**Prevention:** Line-buffered logging (`logging.StreamHandler` with `flush()` on every `ERROR` and above; `logging.FileHandler(..., delay=False)`). Crash handler installs a SIGSEGV / atexit flusher. Use `logrotate` or Python's `RotatingFileHandler` with copy-truncate.
**Maps to Arc:** Observability Arc.
**Severity:** P1

### P2-10 — Socket path collision across projects
**Surface:** Daemon
**Failure mode:** User has two projects using `state`; both daemons try to bind `/tmp/state.sock`; second fails or (worse) hijacks the first's traffic.
**Warning signs:** Cross-project event bleed; users report seeing wrong project's status.
**Prevention:** Socket path keyed by project root hash: `$XDG_RUNTIME_DIR/state-<hash>.sock`. Refuse to start if path is already bound.
**Maps to Arc:** Daemon Arc.
**Severity:** P2

---

## Surface 10: Plugin Shim Hot-Reload

### P1-20 — Stale HTTP connections to daemon after opencode plugin reload
**Surface:** Plugin
**Failure mode:** opencode fires `config` hook; plugin reloads; old HTTP client still references closed sockets; requests silently fail.
**Warning signs:** Plugin features stop working after config edits; requires opencode restart.
**Prevention:** Plugin entry creates HTTP client in `plugin(input)` function scope, not module scope; `lifecycle.onDispose(fn)` closes the client. On config reload, opencode reinvokes `server(input)`; new client is created. Unit test: fire config hook 10× and assert each reload produces a working client.
**Maps to Arc:** Plugin Arc.
**Severity:** P1

### P1-21 — Plugin/daemon version mismatch
**Surface:** Plugin
**Failure mode:** User upgrades `state` daemon but opencode plugin is cached at older version; API shapes drift; plugin sends v1 payloads to v2 daemon; cryptic deserialization errors.
**Warning signs:** Errors reference fields that don't exist on either side.
**Prevention:** Plugin sends `X-State-Plugin-Version` header on every request; daemon rejects if major version mismatches and returns a user-facing "please upgrade plugin" message. Bundle plugin version in daemon and expose via `/version`.
**Maps to Arc:** Plugin Arc + Release Arc.
**Severity:** P1

### P2-11 — TUI slot registration leaks after reload
**Surface:** Plugin
**Failure mode:** Plugin registers a TUI sidebar slot via `api.ui.Slot.register(...)`; plugin reloads; new registration happens but old one isn't torn down; two sidebar entries appear.
**Warning signs:** Duplicated TUI elements after config hot-reload.
**Prevention:** All registrations go through `lifecycle.onDispose` (`plugin/src/tui.ts` — `onDispose(fn)`). Refuse to re-register if old disposal didn't run.
**Maps to Arc:** Plugin Arc.
**Severity:** P2

---

## Surface 11: Per-Slice Worktree Management

### P0-10 — Orphan locked worktrees fill disk
**Surface:** Worktree
**Failure mode:** Opencode/CC writes `.git/worktrees/<slice-id>/locked` during active session; session crashes or is force-killed; `git worktree remove` refuses to remove locked worktrees; our cleanup swallows the error (`2>/dev/null || true` pattern); worktrees accumulate on disk; over weeks, fills disk. **This is documented in the wild** as a CC/opencode failure mode.
**Warning signs:** Disk usage grows with project age; `git worktree list` shows worktrees for Slices completed weeks ago; `.git/worktrees/` has many subdirs.
**Prevention:** Cleanup path: (1) read `.git/worktrees/<id>/locked` to understand who claimed the lock; (2) if lock is by the current process's parent opencode session and that session is dead, force-remove with `git worktree remove --force` AND `git worktree prune`. (3) Never silently swallow `remove` errors — log and surface. (4) Daemon's nightly GC scans `.git/worktrees/`, finds ones with no active Slice in our SQLite, removes them. (5) `state doctor` reports orphan count.
**Maps to Arc:** Worktree Arc + Daemon Arc (GC Slice).
**Severity:** P0

### P1-22 — Worktree bootstrap partial-failure leaks directory
**Surface:** Worktree
**Failure mode:** `git worktree add` fails mid-creation (disk full, permission denied); directory created but branch not; next attempt with same slug collides and fails. Documented in `opencode` upstream (`issue #14648`).
**Warning signs:** Stale directories in the worktree root with no git metadata.
**Prevention:** Worktree creation is transactional at our layer: try to create; on any failure, attempt cleanup of directory + branch with independent error handling; if cleanup itself fails, record the state to SQLite and surface to `state doctor`. Retry with fresh slug (suffix counter) rather than reusing the name.
**Maps to Arc:** Worktree Arc.
**Severity:** P1

### P1-23 — Branch-name collision across Slices
**Surface:** Worktree
**Failure mode:** Two Slices with similar titles generate the same slug (`auth-flow-refactor` both times); second worktree create fails because branch exists.
**Warning signs:** Intermittent Slice creation failures; errors mention "branch already exists."
**Prevention:** Slug = `<arcID>-<sliceID>-<title_slug>`; arcID/sliceID are monotonic integers guaranteeing uniqueness. Never rely on title alone.
**Maps to Arc:** Worktree Arc + Planning Arc.
**Severity:** P1

### P1-24 — Rebase/merge conflicts when Slices overlap
**Surface:** Worktree
**Failure mode:** DAG scheduler runs two independent Slices; both modify the same file; merge-back to main conflicts; no automatic resolution; user is blocked.
**Warning signs:** Frequent merge conflict errors during `ship`; scheduler thinks Slices are independent but they actually aren't.
**Prevention:** DAG typed edges include `conflicts_with` inferred from static file-touch analysis. Slices declare file ownership patterns in their spec; scheduler serializes any Slices whose patterns overlap. On conflict during merge, pause both Slices, surface a "gray-area decision" dialog.
**Maps to Arc:** Scheduler Arc + Worktree Arc.
**Severity:** P1

### P2-12 — `.gitignore` inheritance breaks in worktree
**Surface:** Worktree
**Failure mode:** Project-level `.gitignore` references `../other-worktree/`; in the Slice worktree that path doesn't exist; `.gitignore` semantics silently drift.
**Warning signs:** Files ignored in main checkout but tracked in worktree (or vice versa).
**Prevention:** Document: `.gitignore` patterns must be relative to repo root, not worktree root. `state doctor` checks for `../` in gitignore patterns and warns.
**Maps to Arc:** Worktree Arc.
**Severity:** P2

---

## Surface 12: Snapshot / Diff / Revert

### P1-25 — Snapshot bloat
**Surface:** Snapshot
**Failure mode:** Step-level snapshots taken on every tool call; large binary files re-snapshotted every step; `.state/snapshots/` grows to gigabytes.
**Warning signs:** Disk usage dominated by snapshots; slow snapshot operations.
**Prevention:** Content-addressed snapshot store (blob dedup by sha256); snapshots store file hashes + a manifest, not content. Garbage-collect snapshots older than the most recent successful Slice checkpoint. Never snapshot files matching `.gitignore` or a `.state/snapshot-ignore` list. Test: snapshot a 100MB binary 10×; assert total disk usage ≈ 100MB + manifest overhead.
**Maps to Arc:** Snapshot Arc.
**Severity:** P1

### P1-26 — Revert across worktrees breaks other in-flight Slices
**Surface:** Snapshot
**Failure mode:** User reverts Slice A; revert touches a file that Slice B is currently editing in its own worktree; Slice B's working tree becomes inconsistent with its base.
**Warning signs:** Slice B's verification starts failing after an unrelated Slice A revert.
**Prevention:** Revert scope is the Slice's *own worktree*. Cross-worktree revert (e.g., reverting a merged change) requires the scheduler to pause dependents, revert, replay; no silent cross-worktree state mutation.
**Maps to Arc:** Snapshot Arc + Scheduler Arc.
**Severity:** P1

### P2-13 — Partial-revert semantics ambiguous
**Surface:** Snapshot
**Failure mode:** User reverts "step 3 of Slice X" — does that revert step 3 only, or step 3 + 4 + 5? Unclear semantics; inconsistent results.
**Warning signs:** Users report revert "didn't do what I expected."
**Prevention:** Define revert semantics up front: reverting step N reverts N, N+1, …, latest in the same Slice (prefix revert only). No arbitrary "revert just step 3" — that's a branch, not a revert. Document clearly.
**Maps to Arc:** Snapshot Arc.
**Severity:** P2

### P2-14 — Snapshot + git-commit drift
**Surface:** Snapshot
**Failure mode:** Step commits to git AND takes a snapshot; user manually `git reset`s; snapshot still thinks files are in a different state; revert replays a broken state.
**Warning signs:** Revert restores files to states that don't match any commit.
**Prevention:** Each snapshot stores `HEAD commit hash` at snapshot time; revert flow verifies the git state matches snapshot's expected parent before restoring. If drift detected, surface a dialog rather than silently fixing up.
**Maps to Arc:** Snapshot Arc.
**Severity:** P2

---

## Surface 13: DAG Scheduler

### P0-16 — TaskGroup silently swallows CancelledError (deadlock)
**Surface:** Scheduler / Python 3.12 asyncio
**Failure mode:** Nested `asyncio.TaskGroup` for per-Slice workers; inner `TaskGroup.__aexit__` never includes `CancelledError` in its `ExceptionGroup` if there are other exceptions (known CPython issue #116720); the outer scheduler's cancellation request is silently dropped; scheduler hangs.
**Warning signs:** Scheduler stops advancing but shows no errors; `/state:forensics` shows in-flight Slices that never time out.
**Prevention:** Python 3.13+ recommended. For every `async with asyncio.TaskGroup() as tg:` block, follow up with an explicit `if task.cancelled():` re-raise pattern. Add a scheduler watchdog: if no progress event in 5 minutes, log scheduler stall, dump all task stacks via `asyncio.all_tasks()`. Write a regression test that spawns nested TaskGroups and cancels from the outside; asserts no hang.
**Maps to Arc:** Scheduler Arc.
**Severity:** P0

### P1-27 — Cycle detection misses transitive edges
**Surface:** Scheduler
**Failure mode:** `Slice A depends_on Slice B`, `B depends_on C`, `C depends_on A` (added later); basic cycle detection only checks direct edges; accept the edge; scheduler never picks up any of the three.
**Warning signs:** Slices show "blocked" forever with no obvious blocker.
**Prevention:** On every edge insert, run full DFS cycle check; reject insert if it would close a cycle. Periodic audit via `state doctor`. Test: programmatically build a 1000-node DAG with random edges; assert no cycle persists after construction.
**Maps to Arc:** Scheduler Arc.
**Severity:** P1

### P1-28 — Silent deadlock on descoped dependency
**Surface:** Scheduler
**Failure mode:** Slice X `depends_on` Slice Y; Slice Y gets descoped (user moves to "out of scope"); Y is never going to complete; X blocks forever.
**Warning signs:** Slices stuck in "blocked" state; `/state:next` reports no work despite incomplete slices.
**Prevention:** Descope operation rewrites all dependents: either cascade-descope or offer to break the dependency with an explicit `--assume-satisfied` flag. Scheduler warns on any `depends_on` pointing to a descoped target at load time.
**Maps to Arc:** Scheduler Arc + Planning Arc.
**Severity:** P1

### P2-15 — Priority inversion
**Surface:** Scheduler
**Failure mode:** High-priority Slice blocks on a low-priority dependency; low-pri starves because scheduler picks unrelated work first.
**Warning signs:** Critical Slices complete later than less important ones.
**Prevention:** Priority inheritance: a blocked Slice's priority is max(self, max dependents). Priority recomputed on dependency insert. Test: build scenario with known priority inversion; assert scheduler picks correctly.
**Maps to Arc:** Scheduler Arc.
**Severity:** P2

### P2-16 — Edge-type typo accepted silently
**Surface:** Scheduler
**Failure mode:** User writes `depends_on` as `depend_on` in a YAML spec; schema is permissive; dependency is ignored; scheduler runs Slices out of expected order.
**Warning signs:** Work executes in wrong order; user discovers only on broken verification.
**Prevention:** Strict pydantic validation with `extra = "forbid"` on all spec schemas; typos reject on load with a suggestion.
**Maps to Arc:** Scheduler Arc + Planning Arc.
**Severity:** P2

---

## Surface 14: Subagent Spawn via opencode task tool + task_id resume

### P1-29 — `task_id` resume token staleness
**Surface:** Subagent / task tool
**Failure mode:** `state` stores `task_id` from first spawn; hours later tries to resume; opencode's internal session may have been archived or GC'd; resume fails.
**Warning signs:** Resume attempts return "session not found" intermittently.
**Prevention:** On resume failure, fall back to a fresh `task()` call with the same `subagent_type` and a "rehydrate from `.planning/...`" prompt. Never treat `task_id` as permanent. Store `task_id` + `created_at` + `last_used_at`; refresh every use.
**Maps to Arc:** Subagent Arc.
**Severity:** P1

### P1-30 — Context loss between resume attempts
**Surface:** Subagent
**Failure mode:** Subagent's conversation history gets compacted between our first call and our resume; resume fires but the subagent has lost the "you were working on PHASE X" context.
**Warning signs:** Subagent's second turn asks "what were we doing?"
**Prevention:** Every resume prompt re-injects phase/slice state from `.planning/` as a "here's your context" section. Don't rely on session memory.
**Maps to Arc:** Subagent Arc.
**Severity:** P1

### P2-17 — Cost accounting wrong for resumed subagents
**Surface:** Subagent
**Failure mode:** Cost tracking logs each `task()` call; resumed calls aren't a "new session" but we count them as such; total cost inflated.
**Warning signs:** Cost reports don't match provider bills.
**Prevention:** Track cost per session ID (opencode's `task_id`), not per call. Aggregate across resumes.
**Maps to Arc:** Observability Arc + Subagent Arc.
**Severity:** P2

### P2-18 — Subagent timeout kills parent
**Surface:** Subagent
**Failure mode:** Subagent hangs; parent `task()` tool call has no timeout; opencode's session waits forever; user force-kills opencode.
**Warning signs:** opencode hangs when `state` spawns a subagent.
**Prevention:** Every `task()` call has an explicit timeout (30 min default); on timeout, `ctx.abort` fires; parent gets a structured timeout error it can report in-phase and retry/pause.
**Maps to Arc:** Subagent Arc.
**Severity:** P2

---

## Surface 15: Teach-Mode Specific

### P1-31 — Mental-model drift after event-log truncation
**Surface:** Teach / mental model
**Failure mode:** Learner's `MENTAL-MODEL.json` is a projection of the event log; if event log is truncated (compaction, privacy purge, storage limit), the projection becomes inconsistent with reality; teacher asks drill questions based on false beliefs about the learner.
**Warning signs:** Learner answers easy drill question; teacher reports surprise; or teacher asks about a concept the learner already mastered.
**Prevention:** `MENTAL-MODEL.json` always snapshots alongside event truncation; rebuild from current snapshot + tail of events, not from full replay. Test: truncate event log to last 100 events, reproject, compare to live state; must match.
**Maps to Arc:** Teach Arc + Event Store Arc.
**Severity:** P1

### P1-32 — Kolb-cycle state machine gets stuck
**Surface:** Teach / Kolb
**Failure mode:** Learner fails to provide "abstract conceptualization" input; state machine has no timeout or escape; session frozen in one Kolb stage.
**Warning signs:** Teach sessions hang mid-cycle; learner reports "I don't know what it wants."
**Prevention:** Every Kolb state has an explicit "escape" transition: idle timeout (30 min) → "would you like to pause here?" Every state exposes an explicit "skip" or "reframe" option. Use opencode `question` tool for structured options.
**Maps to Arc:** Teach Arc.
**Severity:** P1

### P1-33 — Drill question token bloat
**Surface:** Teach / drill
**Failure mode:** Drill engine includes full mental-model history in every drill prompt; LLM receives 20k+ tokens of history for a 5-token answer.
**Warning signs:** Drill sessions cost 10×+ expected; rate-limits hit earlier.
**Prevention:** Drill prompt contains only the *current concept*, *last 3 observations*, and *one diagnostic hypothesis*. History is query-on-demand. Budget enforced via assertion: drill prompt ≤ 3000 tokens.
**Maps to Arc:** Teach Arc.
**Severity:** P1

### P1-34 — Learner privacy leakage in observation logs
**Surface:** Teach / privacy
**Failure mode:** Observation events capture full tool outputs, shell history, file contents — potentially including secrets, personal data, unrelated project files.
**Warning signs:** Grep `events.sqlite` for common secret patterns returns hits.
**Prevention:** Observations are *structured*, not raw. Only capture: concept ID, learner action type, outcome status, teacher assessment. Never capture raw shell output or file contents in event payloads. If raw content is needed for forensics, store in a separate `observations/raw/*.json` that's gitignored and opt-in.
**Maps to Arc:** Teach Arc + Auth/Vault Arc.
**Severity:** P1

### P2-19 — Teaching-style config hot-reload causes mid-concept drift
**Surface:** Teach
**Failure mode:** User changes teaching style from Socratic to PRIMM mid-concept; `config` hook fires; next drill uses new style but learner was in Socratic flow.
**Warning signs:** Learner reports teacher "changed personality" mid-lesson.
**Prevention:** Teaching-style switch scopes to next concept boundary; current concept finishes in its original style. Surface a TUI toast on switch: "will take effect on next concept."
**Maps to Arc:** Teach Arc.
**Severity:** P2

---

## Surface 16: Cross-Mode Coupling Leakage

### P0-11 — Build planning artifacts visible in Teach (or vice versa)
**Surface:** Cross-mode / isolation
**Failure mode:** Plugin shim reads `.planning/` indiscriminately; teach session's system-prompt gets build-mode phase state injected; modes contaminate; learners see shipping agendas they shouldn't; build agents see teaching state and get confused.
**Warning signs:** Teach session mentions "current phase"; build agent offers to teach a concept.
**Prevention:** Separate directory trees. Build: `.planning/build/`; Teach: `.planning/teach/`. `.state/mode.json` declares active mode; plugin shim only reads the active mode's tree. Cross-mode reads require explicit flag. Test: run teach session; grep its system prompt for "phase"; assert zero hits (unless user explicitly mentioned it).
**Maps to Arc:** Mode Isolation Arc.
**Severity:** P0

### P1-35 — Shared kernel state leaks mode flag
**Surface:** Cross-mode
**Failure mode:** Event store shared across modes; a Build event with `aggregateID: slice-123` is read by Teach's projector; teach state corrupts.
**Warning signs:** Teach mental model contains build-mode concepts.
**Prevention:** Every event has a `mode: "build" | "teach"` field; projectors filter on mode; cross-mode events are explicitly allowed only for kernel events (auth, provider). Projector asserts on unexpected mode at runtime.
**Maps to Arc:** Event Store Arc + Mode Isolation Arc.
**Severity:** P1

### P2-20 — Single `state doctor` reports both modes, confusing users
**Surface:** Cross-mode
**Failure mode:** Build-only user runs `state doctor`; report includes teach-mode checks; user gets warnings about teach subsystems they don't use.
**Warning signs:** User confusion reports.
**Prevention:** `state doctor --mode=build` / `--mode=teach`; default respects `.state/mode.json`. `--all` for cross-mode audits.
**Maps to Arc:** Observability Arc.
**Severity:** P2

---

## Surface 17: Python 3.12+ Specific

### P0-16 (cross-ref) — TaskGroup cancellation semantics — see Scheduler surface

### P1-36 — Async generator swallows cancellation (PEP 789)
**Surface:** Python 3.12 asyncio
**Failure mode:** SSE stream consumer uses an async generator that yields; parent cancels; the generator's `finally` runs cleanup that awaits; second cancellation arrives during cleanup; generator swallows it; parent never sees the cancellation.
**Warning signs:** SSE streams don't terminate when opencode session cancels.
**Prevention:** Follow PEP 789 — don't `yield` inside async generators that consume cancellable resources. Use explicit `async def consume(): ...` functions instead. Mark known-safe generators with a comment citing the review.
**Maps to Arc:** Event Store Arc + Plugin Arc.
**Severity:** P1

### P1-37 — Free-threaded CPython (PEP 703) incompatibility
**Surface:** Python 3.13+ free-threaded
**Failure mode:** User installs `python3.13t` (free-threaded); one of our deps (pygit2, litellm, aiosqlite) isn't compatible; mysterious crashes under GIL-less mode.
**Warning signs:** Crashes only on free-threaded builds.
**Prevention:** Constraint in pyproject: `requires-python = ">=3.12,<3.14"` or explicit "free-threaded not supported yet." Document in INSTALL.md. Test matrix includes standard 3.12 and 3.13 but not `3.13t` until deps catch up.
**Maps to Arc:** Release Arc.
**Severity:** P1

### P2-21 — Blocking subprocess in async context
**Surface:** Python asyncio
**Failure mode:** A Slice executes `subprocess.run("git worktree add …")` from async context; blocks event loop; scheduler stalls.
**Warning signs:** Scheduler latency spikes during git operations.
**Prevention:** All subprocess calls go through `asyncio.create_subprocess_exec`; never `subprocess.run` from async. Lint rule: flag `subprocess.run` inside any `async def`.
**Maps to Arc:** Scheduler Arc + Tooling Arc.
**Severity:** P2

---

## Surface 18: Provider Routing

### P1-38 — litellm version drift breaks Anthropic beta headers
**Surface:** Provider / litellm
**Failure mode:** litellm upgrade silently changes how it forwards `anthropic-beta` headers (known upstream issues: `BerriAI/litellm#9016`, `#15622`); OAuth stealth requests lose their stealth; subscription pricing breaks.
**Warning signs:** After upgrade, Anthropic OAuth starts billing at API-key rates.
**Prevention:** **Never route OAuth-stealth Anthropic requests through litellm.** Use direct Anthropic SDK (`anthropic`) with our own header injection. litellm is for *non-Anthropic* providers + API-key Anthropic requests. Version-pin litellm; integration test with every upgrade captures outgoing headers.
**Maps to Arc:** Provider Routing Arc + Auth Arc.
**Severity:** P1

### P1-39 — Cache-control markers stripped on route
**Surface:** Provider
**Failure mode:** Our request sets `cache_control: {"type": "ephemeral"}` on system prompt; litellm strips it because its normalization doesn't recognize the shape (docs only guarantee a subset).
**Warning signs:** Cache hit rate reports show near-zero on long sessions that should be cached.
**Prevention:** Direct SDK for all cache-control-using requests. Integration test captures outgoing payload and asserts cache_control markers survive.
**Maps to Arc:** Provider Routing Arc.
**Severity:** P1

### P1-40 — Thinking-mode incompatibility across providers
**Surface:** Provider
**Failure mode:** User configures "extended thinking" as a mode-level default; request goes to OpenAI via litellm; silently dropped; user thinks thinking is on but isn't.
**Warning signs:** Responses look shallow despite thinking config.
**Prevention:** Provider capability matrix (pydantic `Provider.supports_thinking: bool`); scheduler refuses to route a "thinking required" request to a non-thinking provider; explicit fallback with user-visible toast.
**Maps to Arc:** Provider Routing Arc.
**Severity:** P1

### P2-22 — Cost accounting wrong after model aliasing
**Surface:** Provider
**Failure mode:** User's config aliases `sonnet` to different models at different times; cost report groups all by `sonnet` label; blurs actual spend.
**Warning signs:** Cost breakdown doesn't match provider invoice.
**Prevention:** Log the *resolved* model string (provider/model_id) on every request; aggregate reports by resolved model.
**Maps to Arc:** Observability Arc.
**Severity:** P2

---

## Surface 19: Portability Shims (Claude Code, Gemini CLI, Qwen Code)

### P1-41 — TUI-dependent features silently no-op on non-opencode hosts
**Surface:** Portability
**Failure mode:** Slice emits a `ui.toast` or `dialog.select`; Claude Code has no equivalent; plugin shim silently drops the call; user never sees the prompt; Slice hangs waiting for a reply that won't come.
**Warning signs:** Slices that require user input hang on non-opencode hosts.
**Prevention:** Capability detection at shim registration: declare what each host supports. Slices that require a missing capability error immediately with a clear "this requires opencode TUI" message. Fallback: degrade dialog to a numbered text prompt via stdin; degrade toast to a log line.
**Maps to Arc:** Portability Arc + TUI Arc.
**Severity:** P1

### P2-23 — Non-opencode host lacks hooks
**Surface:** Portability
**Failure mode:** On Claude Code host, the shim adapts opencode-style hooks to CC's `SessionStart`/`PostToolUse` lifecycle; some hooks (like `experimental.session.compacting`) have no CC equivalent; those features don't work.
**Warning signs:** Feature parity gaps documented but not surfaced to user.
**Prevention:** Feature matrix in docs per host. `state doctor` on non-opencode hosts reports missing capabilities. Don't pretend to support what we can't.
**Maps to Arc:** Portability Arc.
**Severity:** P2

---

## Surface 20: GSD Lineage Pitfalls

### P1-42 — Pause/resume state loss (GSD lesson)
**Surface:** Session continuity
**Failure mode:** GSD's `pause-work` writes a `.continue-here.md` but the next session on a different machine can't parse it due to absolute-path assumptions; work resumes with wrong context.
**Warning signs:** `/resume-work` reports inconsistencies; user has to manually reconstruct state.
**Prevention:** Pause artifact stores paths relative to repo root; resume rewrites to local absolute paths on load. All paths in events are relative; absolute paths only in runtime.
**Maps to Arc:** Session Arc + Event Store Arc.
**Severity:** P1

### P1-43 — Thread management unbounded growth (GSD lesson)
**Surface:** Threads / context
**Failure mode:** `/gsd-thread` creates threads indefinitely; no archive or pruning; `.planning/threads/` grows to hundreds of files; resume loads all of them; token budget exhausted.
**Warning signs:** Resume session slower over time; eventually OOMs or times out on load.
**Prevention:** Threads with `status: resolved` + updated > 90 days auto-archive to `.planning/threads/archive/`; only `open` + `in_progress` loaded on resume. `state doctor` reports thread count.
**Maps to Arc:** Planning Arc.
**Severity:** P1

### P1-44 — Forensics report leaks absolute paths / secrets (GSD lesson)
**Surface:** Forensics / observability
**Failure mode:** `/gsd-forensics` reports posted to GitHub issues include absolute paths (`/Users/tmac/...`) and occasionally embedded tokens from log snippets.
**Warning signs:** Manual review catches leaks right before issue publish.
**Prevention:** Forensics report generator runs the same redaction filter used for logs; strip absolute paths → repo-relative paths; strip known token prefixes. Test: generate a report with embedded secrets, assert redaction.
**Maps to Arc:** Observability Arc.
**Severity:** P1

### P1-45 — Debug-session slug collisions (GSD lesson)
**Surface:** Debug workflow
**Failure mode:** GSD's debug.md generates slug from user description; two similar issues collide; session data overwrites.
**Warning signs:** Debug session content unexpectedly changes.
**Prevention:** Slug includes monotonic counter suffix on collision. Never overwrite an existing debug session file.
**Maps to Arc:** Debug Arc.
**Severity:** P1

### P2-24 — GSD's serial milestone→phase ordering assumption bleeds into Arc→Phase→Slice
**Surface:** Planning
**Failure mode:** Users coming from GSD assume Phases are serial; `state` DAG scheduler actually parallelizes Slices; users get confused when two Slices run concurrently unexpectedly.
**Warning signs:** User reports "wrong Slice ran first."
**Prevention:** Documentation clearly distinguishes: Arcs and Phases are *scope containers* (no implicit ordering); Slices have *explicit `depends_on` DAG*. Scheduler defaults to max parallelism; users must opt into serialization via explicit edges. TUI dashboard visualizes the DAG so concurrency is visible.
**Maps to Arc:** Planning Arc + TUI Arc.
**Severity:** P2

### P2-25 — GSD debt-markdown files accumulate unmaintained
**Surface:** Planning / debt tracking
**Failure mode:** GSD pattern: debt accumulates in markdown files; nobody reads them; grows to unusable size; value lost.
**Warning signs:** `.planning/debt/*.md` with staleness >90 days.
**Prevention:** Debt is a first-class event type, not a markdown artifact. Projected to a queryable SQLite table. `state doctor` reports debt items older than N days with priority. Auto-close debt that references resolved Slices.
**Maps to Arc:** Planning Arc + Event Store Arc.
**Severity:** P2

### P2-26 — Command proliferation without inventory (GSD lesson)
**Surface:** Commands
**Failure mode:** GSD ships 100+ `/gsd:*` commands with overlapping semantics; users don't discover the right one; help text goes stale.
**Warning signs:** Same functionality accessed via 3 different commands.
**Prevention:** Every command inventoried at roadmap time: port / redesign / drop decision. Command namespace is `/state:build:*` and `/state:teach:*` only. Document a deprecation path; don't ship v1 with 100 commands — ship with 20 and grow.
**Maps to Arc:** Command Arc + Planning Arc.
**Severity:** P2

---

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Anthropic OAuth stealth | HIGH | `claude-oauth.md` is authoritative and explicit; cross-referenced with GSD-2 analysis |
| MCP protocol traps | HIGH | Opencode source read directly (`mcp/index.ts`); verified with 2026 MCP ecosystem posts |
| Event sourcing | HIGH | Opencode `sync/index.ts` code is explicit about sequence-mismatch behavior (line 190) |
| Python 3.12 asyncio | MEDIUM | CPython issue trackers verified; PEP 789 real; exact pattern requires testing |
| litellm drift | MEDIUM | Multiple BerriAI/litellm issues verified (9016, 15622, 10226, 14293) |
| Worktree orphans | MEDIUM | Pattern confirmed in upstream CC/opencode issues; cleanup pattern matches reality |
| Teach mode specific | LOW | No explicit AOL files were readable; synthesized from general teaching-tool patterns + event-sourcing principles |
| GSD lineage | MEDIUM | pause-work, resume-work, forensics, debug, thread command files read; patterns inferred |

## Sources

- [claude-oauth.md](file:///Users/tmac/Projects/state/state-inputs/claude-oauth.md) — stealth flow (authoritative)
- [opencode-extension-surface.md](file:///Users/tmac/Projects/state/state-inputs/opencode-extension-surface.md) — plugin surface
- [opencode/packages/opencode/src/sync/index.ts](file:///Users/tmac/Projects/state/state-inputs/opencode/packages/opencode/src/sync/index.ts) — event sequence guarantees
- [opencode/packages/opencode/src/mcp/index.ts](file:///Users/tmac/Projects/state/state-inputs/opencode/packages/opencode/src/mcp/index.ts) — MCP client behavior
- [opencode/packages/plugin/src/index.ts](file:///Users/tmac/Projects/state/state-inputs/opencode/packages/plugin/src/index.ts) — plugin hooks
- [gsd-2pi-codebase-analysis/11-architecture-discussion.md](file:///Users/tmac/Projects/state/state-inputs/gsd-2pi-codebase-analysis/11-architecture-discussion.md) — Python rebuild tradeoffs
- [MCP Token Counter: Why Your Tools Are Silently Eating Your Context Window](https://mcpplaygroundonline.com/blog/mcp-token-counter-optimize-context-window)
- [The New Stack: MCP roadmap 2026](https://thenewstack.io/model-context-protocol-roadmap-2026/)
- [CPython #116720 — Nested TaskGroup swallows cancellation](https://github.com/python/cpython/issues/116720)
- [CPython #94398 — TaskGroup may not cancel all tasks on failure](https://github.com/python/cpython/issues/94398)
- [PEP 789 — Preventing task-cancellation bugs in async generators](https://peps.python.org/pep-0789/)
- [BerriAI/litellm #9016 — anthropic-beta header not forwarded](https://github.com/BerriAI/litellm/issues/9016)
- [BerriAI/litellm #15622 — Bedrock beta header drop](https://github.com/BerriAI/litellm/issues/15622)
- [BerriAI/litellm #14293 — Vertex cache-enabled header fails](https://github.com/BerriAI/litellm/issues/14293)
- [BerriAI/litellm #15880 — Bedrock Anthropic cache TTL header](https://github.com/BerriAI/litellm/issues/15880)
- [BerriAI/litellm #10226 — cache control injection](https://github.com/BerriAI/litellm/issues/10226)
- [pygit2 worktree documentation](https://www.pygit2.org/worktree.html)
- [git-worktree manual](https://git-scm.com/docs/git-worktree)
- [Python asyncio tasks — 3.14 docs](https://docs.python.org/3/library/asyncio-task.html)

## Roadmap Implications (brief)

- **Auth Arc is a P0 release blocker Arc.** Stealth headers + refresh lock + vault permissions must all be Slices in the first Arc. No "stub with API keys and add OAuth later" — header tests are Slice-level acceptance criteria from day one.
- **Event Store Arc precedes anything that emits events** — including all mode logic. The dual-write contract (SQLite first, SyncEvent second) is a global invariant.
- **Mode Isolation Arc is physical, not logical.** Two MCP servers, two `.planning/` subtrees, two Python packages. Do not create a "shared mode abstraction" Arc.
- **Worktree Arc must ship with a GC mechanism** — orphan cleanup is P0. No "we'll add it later."
- **Observability Arc is load-bearing.** Log redaction, trace_ids, `state doctor`, forensics — all depend on structured events + redactors from day one.
- **Portability Arcs are explicitly deprioritized** per PROJECT.md. Pitfalls documented but don't drive near-term phases.