---
wave: 1
depends_on: ["050"]
files_modified:
  - src/state_daemon/socket.py
  - src/state_daemon/server.py
  - tests/test_daemon_socket.py
autonomous: true
---

# Plan 052-1: Unix Socket Path Resolution + Wiring

**Goal:** Deterministic unix socket path based on project root hash, with macOS fallback for missing `$XDG_RUNTIME_DIR`, and storage of the socket path in `.state/daemon.sock` for worker discovery.

**Requirements:** DAE-04

### Tasks

#### 052.1 Socket Path Resolution

**Acceptance:** `resolve_socket_path(project_root) -> str` returns a deterministic, platform-aware unix socket path.
**Estimated effort:** Small
**Dependencies:** none

**Details:**
- Hash the project root absolute path via `hashlib.sha256(project_root.encode()).hexdigest()[:16]` for the socket name.
- Socket name format: `state-<hash>.sock`.
- Prefer `$XDG_RUNTIME_DIR` on Linux; fallback to `$TMPDIR` or `/tmp` on macOS.
- Ensure the parent directory exists before binding.
- Return the full absolute path.
- Test: unit tests for hash determinism, Linux XDG path, macOS fallback.

**Files:**
- `src/state_daemon/socket.py` — new file

#### 052.2 Socket Path Storage + Discovery

**Acceptance:** Socket path written to `.state/daemon.sock` at startup; `read_socket_path()` reads it back for worker/client discovery.
**Estimated effort:** Small
**Dependencies:** 052.1

**Details:**
- `write_socket_path(socket_path: str)`: writes the resolved socket path to `.state/daemon.sock`.
- `read_socket_path() -> str | None`: reads the socket path back.
- Uses atomic write (temp + rename), consistent with pid-file pattern from Phase 051.
- Wire into orchestrator: write socket path after server bind succeeds.
- Test: write/read round-trip tests.

**Files:**
- `src/state_daemon/socket.py` — extend with storage functions

#### 052.3 Integration with DaemonServer

**Acceptance:** Server uses resolved socket path; if port/socket already in use, error is clear.
**Estimated effort:** Small
**Dependencies:** 052.1, 050.1

**Details:**
- Update `orchestrator.startup()` to call `resolve_socket_path()` and pass it to `DaemonServer`.
- Remove the temporary socket path placeholder from Phase 050.
- Handle `OSError` (Address already in use) with a clear error message suggesting to check for stale daemon.
- Test: integration test that verifies the socket path is created at the expected location.

**Files:**
- `src/state_daemon/orchestrator.py` — use resolved socket path
- `src/state_daemon/server.py` — potentially minor cleanup

### Integration Notes

- This phase finalizes the socket path; Phase 050's temporary path placeholder is replaced.
- The `.state/daemon.sock` marker file enables workers (Phase 061) to discover the daemon socket.
- The sha256 hash makes the socket name deterministic across restarts but unique per project checkout.

### must_haves

1. Socket path is deterministic (same project root → same socket path).
2. macOS fallback works when `$XDG_RUNTIME_DIR` is absent.
3. Socket path is stored atomically in `.state/daemon.sock` for worker discovery.
4. Server binds to the resolved socket path.
5. Address-already-in-use errors produce clear diagnostic messages.
