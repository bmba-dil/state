# Graph Report - state  (2026-05-04)

## Corpus Check
- 163 files · ~262,080 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4076 nodes · 17463 edges · 61 communities detected
- Extraction: 26% EXTRACTED · 74% INFERRED · 0% AMBIGUOUS · INFERRED: 12878 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]

## God Nodes (most connected - your core abstractions)
1. `OAuthCredential` - 487 edges
2. `SqliteEventStore` - 450 edges
3. `ApiKeyCredential` - 384 edges
4. `AuthMethod` - 299 edges
5. `Node` - 281 edges
6. `AuthVault` - 258 edges
7. `Edge` - 254 edges
8. `AuthLoginError` - 244 edges
9. `Projector` - 214 edges
10. `DAGScheduler` - 181 edges

## Surprising Connections (you probably didn't know these)
- `test_connection_refused()` --calls--> `attach_to_daemon()`  [INFERRED]
  tests/test_worker_main.py → src/state_worker/main.py
- `test_daemon_not_running_no_socket_marker()` --calls--> `attach_to_daemon()`  [INFERRED]
  tests/test_worker_main.py → src/state_worker/main.py
- `test_timeout()` --calls--> `attach_to_daemon()`  [INFERRED]
  tests/test_worker_main.py → src/state_worker/main.py
- `Phase 018 — VALIDATION rows 09–11, 19 (RED scaffolding).  Wave 0 — every test fa` --uses--> `ApiKeyCredential`  [INFERRED]
  tests/auth/test_main_api_key.py → src/state_core/auth/base.py
- `VALIDATION row 19 — getpass path; key never appears in argv.      T-018-1 ASVS V` --uses--> `ApiKeyCredential`  [INFERRED]
  tests/auth/test_main_api_key.py → src/state_core/auth/base.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (663): AnthropicAccount, AnthropicAuth, AnthropicTokenResponse, _build_authorize_url(), _exchange_code(), inject_stealth_system_prefix(), _is_stealth_rejection(), _main() (+655 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (412): get_connection(), Open a connection to the event store with WAL + synchronous=FULL.      Ensures t, Event store: SQLite writer + SyncEvent mirror for dual-write architecture., Run repair once per session if not yet done.          Safe to call multiple time, Force repair immediately, regardless of _repair_done state.          Called by d, Append an event row with ULID generation and seq enforcement.          Every cal, Read events for an aggregate, ordered by seq, starting after_seq.          Deser, Return all events not yet synced to opencode, ordered by id (ULID = time-ordered (+404 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (425): _main(), _main(), logout(), AuthRefreshLoop, AuthRoundRobin, AuthStatusHandler, _account_label(), _emit_auth_event() (+417 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (272): _box_chars(), _build_demo_dag(), _compute_depths(), _compute_inner_width(), `state dag show` CLI — colored box-drawing DAG visualization.  D-01: Unicode box, Render a single node as 3 box lines (top, content, bottom).      Returns [top_li, Render a single node as 3 pre-colored box lines.      Returns [top_line, content, Render a DAG as colored box-drawing art.      Returns a string suitable for term (+264 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (261): _dispatch_event(), forward_hook(), opencode HTTP + state-daemon client bridge., Read the HTTP status line and return the status code., Sleep with exponential backoff., Parse JSON data and invoke the callback if set., Read and discard HTTP response headers until the blank line., Forward a hook event payload to the daemon via HTTP POST.      Sends a JSON-enco (+253 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (219): AnthropicClient, Direct Anthropic SDK escape hatch for OAuth stealth inference (PRV-02).  Use Ant, Non-streaming inference via direct Anthropic SDK (PRV-02).          Args:, Streaming inference via direct Anthropic SDK (PRV-02).          Yields RawMessag, Direct Anthropic SDK escape hatch for OAuth stealth inference (PRV-02).      One, Build AsyncAnthropic with correct auth strategy for the credential type., BaseSettings, Deps (+211 more)

### Community 6 - "Community 6"
Cohesion: 0.2
Nodes (150): BaseModel, ArcCreatedData, ArcCreatedEvent, ArcRetiredData, ArcRetiredEvent, ArcUpdatedData, ArcUpdatedEvent, AuthRefreshedData (+142 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (132): EventStore, Protocol for writing and reading domain events., OpencodeHTTPWorktreeService, Opencode-HTTP worktree adapter.  Implements the WorktreeService Protocol (Phase, Opencode-HTTP implementation of the WorktreeService Protocol., Protocol, Pygit2WorktreeService, Pygit2 fallback worktree adapter.  Implements the WorktreeService Protocol (Phas (+124 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (91): daemon_logs(), daemon_restart(), daemon_start(), daemon_status(), daemon_stop(), _follow_log(), _format_uptime(), _is_service_installed() (+83 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (71): SSE client bridge — subscribes to daemon event stream via Unix socket.      Conn, Open a Unix socket connection and subscribe to the SSE stream.          Sends ``, Stop the SSE read loop and close the connection., Read and parse SSE lines until disconnect or connection loss., SseBridge, _event_data(), HotState, Hot state container — in-memory pydantic model tracking active session state.  S (+63 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (105): assert_redactor_attached(), install(), iter_token_patterns(), Root-logger token redactor — Phase 020 / AUTH-10 / P0-14 layer 2.  Compiled rege, Apply every pattern in _PATTERNS to *s*; replace each match with REDACTED., Recursive type-dispatch redactor — the redaction kernel.      Args:         v: T, structlog processor — install at position 0 of the chain.      Walks every value, Public accessor for the compiled regex set.      Phase 018's auth/providers/api_ (+97 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (51): daemon_install(), daemon_uninstall(), Install the state daemon as an OS-level user service.      macOS: writes ``~/Lib, Remove the state daemon OS service definition.      macOS: ``launchctl unload``, PermissionError, current_platform_name(), _disable_cmd(), generate_plist() (+43 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (36): _chdir_tmp_path(), _patch_service_def(), Tests for state_daemon.cli — start, stop, restart, status, logs commands.  Uses, When the spawned process dies before pid verification, exit 1., When pid file never appears within timeout, exit 1., Tests for ``state daemon stop``., When no pid file exists, reports daemon is not running., Stale pid file is cleaned up and reported as not running. (+28 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (49): aggregate_provider_costs(), compute_cost(), ProviderCostEmitter, Cost accounting for provider inference calls — Phase 028 (PRV-05).  Provides thr, Aggregate cost + token stats from state.provider.response events.      Reads all, Compute cost in USD using litellm's cost map.      Works for both litellm and An, Wraps LitellmClient or AnthropicClient to emit cost-accounting events.      Emit, Execute an inference call with cost-accounting event emission.          Emits st (+41 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (32): Unix socket path resolution — deterministic, platform-aware socket paths.  Resol, Return a deterministic, platform-aware unix socket path.      The socket name is, Return the preferred runtime directory for unix sockets., Atomically write *socket_path* to ``.state/daemon.sock``.      Uses temp + renam, Read the daemon socket path from ``.state/daemon.sock``.      Returns ``None`` w, read_socket_path(), resolve_socket_path(), _runtime_dir() (+24 more)

### Community 15 - "Community 15"
Cohesion: 0.1
Nodes (31): _hash_directory(), _hash_file(), Step + Slice tier snapshot glue for fine-grained revert., Compare two snapshots by digest.          Returns:             {"status": "ident, Capture a content-addressed snapshot of a worktree., SHA-256 hex digest of file contents., SHA-256 hex digest of all files in a directory (sorted by path)., List all snapshots, most recent first. (+23 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (7): find_opencode_config(), Opencode config file discovery and URL resolution.  Searches up from CWD for ope, Walk up from *start_dir* looking for opencode.json or .opencode/opencode.json., Resolve the opencode HTTP base URL from config, with fallback defaults.      Pri, resolve_opencode_url(), TestFindOpencodeConfig, TestResolveOpencodeUrl

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (16): get_db_path(), Async SQLite connection factory with WAL mode, synchronous=NORMAL, path resoluti, Resolve the database file path.      Priority:     1. STATE_DB_PATH environment, Return the resolved database path without opening a connection., _resolve_db_path(), Tests for state_core.database — connection factory, path resolution, WAL mode., Default path points to .state/events.sqlite relative to CWD., STATE_DB_PATH env var overrides the default path. (+8 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (17): Phase 018 — VALIDATION row 21 (RED scaffolding).  Architectural constraint: prov, rotation.py may import ONLY from base / store / refresh / errors / loader under, Phase 021 IMPORT-MODE-ISOLATION — state_core.auth.import_opencode     MUST NOT i, Phase 021 IMPORT-MODE-ALLOWLIST — explicit allowlist of allowed     import roots, VALIDATION 022-row-A — state_cli/auth.py may import state_core.auth.* but     MU, VALIDATION 022-row-B — state_core/auth/cli_ops.py MUST NOT import state_cli.*., VALIDATION row 21 — providers/api_key.py MUST NOT import loader.      Wave 0 RED, loader.py may import ONLY from base / store / providers.api_key under state_core (+9 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (3): test_deterministic_serialization(), test_extra_forbid(), test_hypothesis_round_trip()

### Community 20 - "Community 20"
Cohesion: 0.25
Nodes (7): _isolate_structlog(), Phase 021 integration tests — orchestrator boot ordering + importer failure.  Ve, T-021-03-3 — importer receives the SAME store + mirror used by reconciler., Snapshot/restore structlog config — same pattern as tests/auth/conftest.py., T-021-03-1 — boot order is locked: install → assert_attached → importer.      A, test_orchestrator_passes_store_and_mirror_to_importer(), test_orchestrator_runs_importer_after_redactor_selfcheck()

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (7): Phase 020 — VALIDATION row REDACT-25 (RED scaffolding).  Architectural constrain, REDACT-25 — state_core.observability.* MUST NOT import state.build.* or state.te, redactor.py may import ONLY from stdlib + structlog + state_core.auth.providers., src/state_core/observability/__init__.py exists as the package marker.      Wave, test_observability_imports_only_allowed_targets(), test_observability_init_exists(), test_observability_no_mode_imports()

### Community 22 - "Community 22"
Cohesion: 0.29
Nodes (4): KolbMachine, Step state machine: idle->discussing->planning->executing->verifying->done., Finite state machine for a single Step's lifecycle., StepMachine

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (3): Verify all packages import without errors., Verify build and teach can both be imported without conflict., test_mode_silos_independent()

### Community 25 - "Community 25"
Cohesion: 0.5
Nodes (3): RED stubs for state_core.auth.oauth_common.pkce — Phase 014 / AUTH-01.  Plan 01, generate_verifier() returns a base64url-no-pad string in RFC 7636's [43, 128] wi, test_verifier_format()

### Community 26 - "Community 26"
Cohesion: 0.67
Nodes (1): state-build MCP server entry point.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Event-sourced mental model projection for teach mode.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Drill engine for teach mode.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Concept graph operations for teach mode.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): File and SSE watchers for the state daemon.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): write_socket_path writes the path; read_socket_path returns it.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Target file never exists in a partially-written state.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Parent directory is created if it doesn't exist.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Missing marker file returns None.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Empty marker file returns None.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Whitespace-only marker file returns None.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Subsequent writes overwrite the previous value.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Remove a file if it exists.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Return the number of currently connected clients.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Validate ULID format if id is non-empty.

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Coerce a bare-dict provider value into a 1-element list.          Phase 011 call

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Insert an event row and read it back.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Insert rows into all 6 cascade tables and read them back.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Initialize the event store database by applying all pending migrations.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Protocol for writing and reading domain events.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Concrete EventStore backed by events.sqlite via database.py.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Append an event row and return its id.          NOTE: This is a stub for Phase 0

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Read events for an aggregate, ordered by seq, starting after_seq.          Yield

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Resolve the database file path.      Priority:     1. STATE_DB_PATH environment

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Open a connection to the event store with WAL + synchronous=NORMAL.      Ensures

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Return the resolved database path without opening a connection.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Create/list/remove worktrees, preferring opencode HTTP API.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Reactive DAG scheduler that computes unblocked Steps on state change.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Return all Step IDs ready for concurrent dispatch.

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Manages snapshots at Step and Slice boundaries.

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Validate that v is a well-formed ULID string.

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Generic event envelope -- used for serialization and generic reads.      All fie

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Validate ULID format if id is non-empty.

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Construct a typed event with auto-generated ULID and timestamp.      Args:

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Routes provider calls — litellm default, Anthropic SDK for extended thinking.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Protocol for writing and reading domain events.

## Knowledge Gaps
- **393 isolated node(s):** `Tests for state_daemon.logging — daemon structured logging with rotation.  Task`, `A temporary project root with an empty .state/ directory.`, `A dedicated temporary log directory.`, `Snapshot and restore root logger state around each test.      structlog.configur`, `Verify configure_daemon_logging() sets up rotation, redaction, and modes.` (+388 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 26`** (3 nodes): `state-build MCP server entry point.`, `mcp.py`, `mcp.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `Event-sourced mental model projection for teach mode.`, `mental_model.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `Drill engine for teach mode.`, `drill.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (2 nodes): `Concept graph operations for teach mode.`, `concepts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `watchers.py`, `File and SSE watchers for the state daemon.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `write_socket_path writes the path; read_socket_path returns it.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Target file never exists in a partially-written state.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Parent directory is created if it doesn't exist.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Missing marker file returns None.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Empty marker file returns None.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Whitespace-only marker file returns None.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Subsequent writes overwrite the previous value.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Remove a file if it exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Return the number of currently connected clients.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Validate ULID format if id is non-empty.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Coerce a bare-dict provider value into a 1-element list.          Phase 011 call`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Insert an event row and read it back.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Insert rows into all 6 cascade tables and read them back.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Initialize the event store database by applying all pending migrations.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Protocol for writing and reading domain events.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Concrete EventStore backed by events.sqlite via database.py.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Append an event row and return its id.          NOTE: This is a stub for Phase 0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Read events for an aggregate, ordered by seq, starting after_seq.          Yield`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Resolve the database file path.      Priority:     1. STATE_DB_PATH environment`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Open a connection to the event store with WAL + synchronous=NORMAL.      Ensures`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Return the resolved database path without opening a connection.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Create/list/remove worktrees, preferring opencode HTTP API.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Reactive DAG scheduler that computes unblocked Steps on state change.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Return all Step IDs ready for concurrent dispatch.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Manages snapshots at Step and Slice boundaries.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Validate that v is a well-formed ULID string.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Generic event envelope -- used for serialization and generic reads.      All fie`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Validate ULID format if id is non-empty.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Construct a typed event with auto-generated ULID and timestamp.      Args:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Routes provider calls — litellm default, Anthropic SDK for extended thinking.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Protocol for writing and reading domain events.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SqliteEventStore` connect `Community 1` to `Community 2`, `Community 4`, `Community 8`, `Community 9`, `Community 11`, `Community 13`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `Worker package — per-session process for state.` connect `Community 3` to `Community 0`, `Community 9`, `Community 2`, `Community 10`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `Node` connect `Community 3` to `Community 6`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 484 inferred relationships involving `OAuthCredential` (e.g. with `Tests for state_core.providers.anthropic_client — AnthropicClient contract.  RED` and `AnthropicClient uses the shared httpx client as transport (PRV-02).`) actually correct?**
  _`OAuthCredential` has 484 INFERRED edges - model-reasoned connections that need verification._
- **Are the 435 inferred relationships involving `SqliteEventStore` (e.g. with `TestStepProjection` and `TestSliceProjection`) actually correct?**
  _`SqliteEventStore` has 435 INFERRED edges - model-reasoned connections that need verification._
- **Are the 381 inferred relationships involving `ApiKeyCredential` (e.g. with `Tests for state_core.providers.anthropic_client — AnthropicClient contract.  RED` and `AnthropicClient uses the shared httpx client as transport (PRV-02).`) actually correct?**
  _`ApiKeyCredential` has 381 INFERRED edges - model-reasoned connections that need verification._
- **Are the 291 inferred relationships involving `AuthMethod` (e.g. with `Local fixtures for tests/auth/providers/ — Phase 014 (AUTH-01).  Lives alongside` and `Deterministic OAuth credential for round-trip + redaction tests.      `expires``) actually correct?**
  _`AuthMethod` has 291 INFERRED edges - model-reasoned connections that need verification._