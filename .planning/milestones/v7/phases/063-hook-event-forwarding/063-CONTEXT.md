---
phase: 063
wave: 1
depends_on: [061]
files_modified:
  - src/state_worker/bridge.py
  - tests/test_worker_bridge.py
autonomous: true
---

# Plan 063-01: Hook Event Forwarding

**Goal:** POST /hook/<name> with typed payload; retry on transient failure.
**Requirements:** WRK-12

### Tasks

#### 063.1 — HTTP POST bridge + retry
**Acceptance:** `forward_hook` function posts JSON to daemon hook endpoints with retry on transient failure
**Estimated effort:** Small
**Dependencies:** 061

<read_first>
- src/state_worker/bridge.py
- src/state_daemon/hooks.py
</read_first>

<action>
Add to `src/state_worker/bridge.py`:
- `async def forward_hook(hook_name: str, payload: dict[str, object], socket_path: str, timeout: float = 5.0, max_retries: int = 3) -> bool`:
  - Open Unix socket to daemon
  - POST JSON to `/hook/<hook_name>`
  - Read HTTP response
  - Retry on ConnectionError, TimeoutError, or 5xx status
  - Return True on 2xx, False after exhausting retries
- Export from module
</action>

<acceptance_criteria>
- `grep -q "async def forward_hook" src/state_worker/bridge.py`
- `grep -q "POST /hook/" src/state_worker/bridge.py`
</acceptance_criteria>

#### 063.2 — Tests
**Acceptance:** Tests cover successful POST, retry on connection error, retry on 503, non-retry on 4xx
**Estimated effort:** Small

<read_first>
- src/state_worker/bridge.py
</read_first>

<action>
Add to `tests/test_worker_bridge.py`:
- `TestForwardHook`: test successful 200, test retry on connection refused, test retry on 503, test no retry on 400, test exhaust retries
</action>
