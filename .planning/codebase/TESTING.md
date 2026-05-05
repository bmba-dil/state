# Testing Patterns

**Analysis Date:** 2026-05-05

## Test Framework

**Runner:**
- pytest >= 8.4.0
- Config: `pyproject.toml` `[tool.pytest.ini_options]` (lines 70-79)
- Async mode: `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` required, but explicitly used in codebase anyway for clarity
- Test paths: `testpaths = ["tests"]`
- Python path: `pythonpath = ["src"]` — allows both `src.state_core.*` and bare `state_core.*` imports in tests

**Plugins:**
- `pytest-asyncio >= 1.3.0` — async test support
- `pytest-cov >= 6.0` — coverage
- `hypothesis >= 6.120` — property-based testing
- `pytest-httpx >= 0.35` — HTTP mocking
- `pytest-mock >= 3.14` — mock fixture
- `freezegun >= 1.5` — time freezing
- `pytest-xdist >= 3.6` — parallel test execution

**Assertion Library:**
- Built-in `assert` statements (no separate library)
- Descriptive assertion messages with f-strings: `f"Expected FULL (2), got {sync_val}"`

**Run Commands:**
```bash
pytest                                  # Run all tests
pytest -m "not e2e and not slow"        # Skip heavy tests
pytest -m "not integration"             # Skip integration tests
pytest --cov                            # With coverage
pytest --update-goldens                 # Regenerate golden test fixtures
pytest -x --pdb                        # Stop on first failure with debugger
```

**Custom Markers** (from `pyproject.toml` lines 74-79):
```python
markers = [
    "e2e: marks tests as end-to-end (deselect with '-m \"not e2e\"')",
    "provider_parity: tests that run against live providers",
    "integration: multi-process or cross-process tests (deselect with '-m \"not integration\"')",
    "slow: tests that intentionally wait for timeouts (deselect with '-m \"not slow\"')",
]
```

## Test File Organization

**Location:**
- Tests are co-located in `tests/` at project root
- Source code is under `src/`
- Mirror source structure: `tests/test_events.py` tests `src/state_core/events.py`
- Nested: `tests/auth/test_api_key.py` tests `src/state_core/auth/providers/api_key.py`

**Naming:**
- Test files: `test_<module_name>.py` — e.g., `test_config.py`, `test_database.py`
- Test classes: `Test<FeatureName>` — e.g., `TestBasicRoundTrip`, `TestSeqEnforcement`, `TestEdgeCases`
- Test methods: `test_<behavior>` — e.g., `test_append_returns_ulid()`, `test_default_mode_is_kernel()`
- Module-level test functions (no enclosing class): `test_<behavior>` with `@pytest.mark.asyncio`

**Structure:**
```
tests/
├── __init__.py                        # Empty (marks as package)
├── conftest.py                        # Empty (root-level fixtures go here)
├── test_events.py                     # Tests for src/state_core/events.py
├── test_config.py                     # Tests for src/state_core/config.py
├── test_database.py                   # Tests for src/state_core/database.py
├── test_schema.py                     # Tests for src/state_core/schema.py
├── test_migrations.py                 # Tests for src/state_core/migrations.py
├── test_imports.py                    # Import graph / mode isolation tests
├── test_deps.py                       # Tests for src/state_core/deps.py
├── test_http_client.py                # Tests for src/state_core/http_client.py
├── test_router.py                     # Tests for src/state_core/providers/router.py
├── test_anthropic_client.py           # Tests for src/state_core/providers/anthropic_client.py
├── test_litellm_client.py             # Tests for src/state_core/providers/litellm_client.py
├── test_cost_accounting.py            # Tests for src/state_core/providers/cost_accounting.py
├── test_redactor.py                   # Tests for src/state_core/observability/redactor.py
├── test_projector.py                  # Tests for src/state_core/projector.py
├── test_reconciler.py                 # Tests for src/state_core/reconciler.py
├── test_sync_mirror.py                # Tests for src/state_core/sync_mirror.py
├── test_scheduler.py                  # Tests for src/state_core/scheduler.py
├── test_cli.py                        # Tests for src/state_cli/
├── test_daemon_*.py                   # Tests for src/state_daemon/ components
├── test_worktree.py                   # Tests for src/state_core/worktree.py
├── test_snapshot.py                   # Tests for src/state_core/snapshot.py
└── auth/
    ├── __init__.py
    ├── conftest.py                    # Rich auth-specific fixtures
    ├── test_api_key.py                # Auth provider tests
    ├── test_base.py                   # Auth base model tests
    ├── test_store.py                  # Auth vault tests
    ├── test_refresh.py                # Auth refresh tests
    ├── test_rotation.py               # Credential rotation tests
    ├── test_loader.py                 # Credential loader tests
    ├── test_errors.py                 # Auth error tests
    ├── test_import_graph.py           # Mode-isolation checks
    ├── test_p0_regression.py          # P0 regression suite
    ├── test_cli_ops.py                # Auth CLI ops tests
    ├── test_cli_typer.py              # Auth Typer CLI tests
    ├── test_import_opencode.py        # Opencode import tests
    ├── test_main_api_key.py           # API key main tests
    ├── providers/
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── test_anthropic.py
    │   ├── test_google_gemini.py
    │   ├── test_antigravity.py
    │   └── test_github_copilot.py
    ├── oauth_common/
    │   ├── __init__.py
    │   ├── test_loopback.py
    │   └── test_pkce.py
    └── golden/                        # Golden test fixture data
```

## Test Structure

**Class-based Organization (primary pattern, from `tests/test_events.py`):**

```python
"""Tests for state_core.events — SqliteEventStore append + read_stream.

Covers: basic round-trip, seq enforcement, determinism, mode storage,
edge cases, and Hypothesis property tests.
"""

from __future__ import annotations

import pytest

from src.state_core.events import SqliteEventStore

# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory for every test."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

# ── Basic round-trip ──────────────────────────────────────────────────────

class TestBasicRoundTrip:
    """Fundamental append → read_stream round-trip."""

    async def test_append_returns_ulid(self, store: SqliteEventStore) -> None:
        id_ = await store.append("step", "step-01", "state.step.executed", {"changes_summary": "x"})
        assert isinstance(id_, str)
        assert len(id_) == 26

class TestSeqEnforcement:
    """Per-aggregate monotonic sequence enforcement."""

    async def test_seq_starts_at_one(self, store: SqliteEventStore) -> None:
        await store.append("step", "step-01", "state.step.executed", {"changes_summary": "a"})
        stream = [e async for e in store.read_stream("step-01")]
        assert stream[0]["seq"] == 1
```

**Module-level parametrized tests (from `tests/test_schema.py`):**

```python
class TestTypedEvents:
    @pytest.mark.parametrize(
        "event_cls, data_obj, type_str, agg_type",
        [
            (ArcCreatedEvent, ArcCreatedData(title="T", goal="G"), "state.arc.created", "arc"),
            (ArcRetiredEvent, ArcRetiredData(reason="R"), "state.arc.retired", "arc"),
            # ... 29+ entries
        ],
    )
    def test_event_construction(self, event_cls, data_obj, type_str, agg_type) -> None:
        ...
```

**Property-based tests with Hypothesis (from `tests/test_events.py`):**

```python
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    aggregate_type=st.sampled_from(["arc", "phase", "slice", "step", "concept", ...]),
    mode_val=st.sampled_from(["build", "teach", "kernel"]),
    data=st.dictionaries(
        st.text(min_size=1, max_size=10),
        st.one_of(st.integers(), st.text(max_size=20)),
        min_size=0, max_size=5,
    ),
)
async def test_property_append_read_roundtrip(
    tmp_path: Path, aggregate_type: str, mode_val: str, data: dict,
) -> None:
    """Hypothesis property: any valid input round-trips correctly."""
    import uuid
    unique = tmp_path / uuid.uuid4().hex
    unique.mkdir(parents=True)
    # ... isolated setup per Hypothesis example ...
```

## Fixture Patterns

**Auto-use fixtures for isolation (from `tests/test_events.py` and `tests/auth/conftest.py`):**
```python
@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))
    # Plus copy migration files to temp dir
```

**Async fixtures (from `tests/test_events.py`):**
```python
@pytest.fixture
async def store() -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()
```

**Pydantic model fixtures (from `tests/auth/conftest.py`):**
```python
@pytest.fixture
def oauth_cred() -> OAuthCredential:
    return OAuthCredential(
        access="sk-ant-oat-test-token-do-not-redact-in-test-only",
        refresh="rt-test-refresh-token-do-not-redact-in-test-only",
        expires=2_000_000_000.0,
        provider_id="anthropic",
        account_id="acct-test-12345",
    )
```

**Teardown pattern:**
- `finally` blocks for env var cleanup in tests that directly modify `os.environ`
- `autouse=True` fixtures for cleanup (`_clear_cool_down` clears module-level state before and after each test)
- Async context managers via `async with` — pytest fixtures auto-close

## Mocking

**Framework:** `unittest.mock` from stdlib (no external mocking library required)

**Context manager pattern (from `tests/test_deps.py`):**
```python
from unittest.mock import AsyncMock, MagicMock, patch

async def test_startup_creates_deps() -> None:
    fake_client = MagicMock(spec=httpx.AsyncClient)
    mock_store = MagicMock()
    mock_store.run_repair_now = AsyncMock(return_value=[])

    with (
        patch("state_daemon.orchestrator.build_shared_client", return_value=fake_client) as mock_build,
        patch("state_daemon.orchestrator.install"),
        patch("state_daemon.orchestrator.SqliteEventStore", mock_store_cls),
        patch("state_daemon.orchestrator.migrate", new_callable=AsyncMock),
    ):
        from state_daemon.orchestrator import startup
        await startup()

    mock_build.assert_called_once()
```

**Env var mocking (via monkeypatch fixture):**
```python
def test_get_db_path_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATE_DB_PATH", "/tmp/test_state_events.sqlite")
    p = get_db_path()
    assert p == Path("/tmp/test_state_events.sqlite").resolve()
```

**Log capture (structlog testing):**
```python
from structlog.testing import capture_logs

def test_oauth_route_log_no_token(deps: Deps) -> None:
    with structlog.testing.capture_logs() as cap_logs:
        router.select(FAKE_OAUTH, deps)
    for entry in cap_logs:
        for value in entry.values():
            assert "sk-ant-oat-fake" not in str(value)
```

**Direct function patching:**
```python
with patch("src.state_core.config.Path.cwd", return_value=Path("/tmp")):
    result = find_opencode_config()
```

**What to Mock:**
- External SDK clients (`httpx.AsyncClient`, `anthropic.AsyncAnthropic`)
- Third-party library internals (`litellm.aclient_session`)
- Environment variables (via `monkeypatch`)
- System functions (`os.isatty`, `sys.stdin`)
- Time (via `freezegun` for `time.time()` / `datetime.now()`)

**What NOT to Mock:**
- Pydantic models — construct real instances: `OAuthCredential(access="test-...", ...)`
- Database — use real SQLite via `tmp_path` + `STATE_DB_PATH` env override
- `SqliteEventStore` — test against real, isolated instances
- Filesystem — use `tmp_path` for real file operations
- `structlog` — use `capture_logs()` for assertion, not mocking

## Fixtures and Factories

**Test Data Construction (from `tests/auth/conftest.py`):**
```python
@pytest.fixture
def oauth_cred() -> OAuthCredential:
    """Deterministic OAuth credential for round-trip + redaction tests."""
    return OAuthCredential(
        access="sk-ant-oat-test-token-do-not-redact-in-test-only",
        refresh="rt-test-refresh-token-do-not-redact-in-test-only",
        expires=2_000_000_000.0,
        provider_id="anthropic",
        account_id="acct-test-12345",
    )
```

**Golden file fixtures (from `tests/auth/conftest.py`):**
```python
GOLDEN_DIR = Path(__file__).parent / "golden"

@pytest.fixture
def golden_load():
    """Return a loader function: golden_load(provider_id, flow_name) -> dict."""
    def _load(provider_id: str, flow_name: str) -> dict:
        path = GOLDEN_DIR / provider_id / f"{flow_name}.json"
        return json.loads(path.read_text())
    return _load
```

**Hypothesis strategies as test-data generators (from `tests/test_events.py`):**
```python
EVENT_DATA_STRATEGIES: dict[str, st.SearchStrategy[dict]] = {
    "state.arc.created": st.fixed_dictionaries({
        "title": st.just("Arc Title"),
        "goal": st.just("Build the thing"),
    }),
    "state.step.verify_passed": st.fixed_dictionaries({
        "duration_ms": st.integers(min_value=0, max_value=60000),
    }),
    # ... 34 event types total
}
```

## Coverage

**Configuration** (from `pyproject.toml` lines 81-89):
```toml
[tool.coverage.run]
source = [
    "state_core",
    "state_build",
    "state_teach",
    "state_daemon",
    "state_worker",
    "state_cli",
]
```

**View Coverage:**
```bash
pytest --cov --cov-report=term-missing
pytest --cov --cov-report=html   # HTML report
```

**Coverage Targets:** Not explicitly enforced in CI, but `pytest-cov` is configured in dev dependencies. Six source packages are tracked.

## Test Types

**Unit Tests:**
- Test individual functions and classes in isolation
- Use class-based organization: `TestBasicRoundTrip`, `TestSeqEnforcement`, `TestEdgeCases`
- Most common test type in the codebase (~90% of test files)
- Found in `tests/test_events.py`, `tests/test_config.py`, `tests/test_database.py`, etc.

**Property-Based Tests (Hypothesis):**
- Used for key data paths: event append/read round-trips, mode filtering
- Found in `tests/test_events.py` (lines 546-697), `tests/test_redactor.py`
- Pattern: `@given(...)` + `@settings(max_examples=100)` + per-example `tmp_path` subdirectory isolation
- Strategies use `st.sampled_from()`, `st.fixed_dictionaries()`, `st.dictionaries()`, `st.data()`

**Integration Tests:**
- Multi-step flows: migration → event write → event read
- Daemon startup sequence tests (full orchestrator wire-up with mocked dependencies)
- Marked with `@pytest.mark.integration` when they span multiple processes

**E2E Tests:**
- Marked with `@pytest.mark.e2e`
- Provider parity matrix tests (`test_litellm_client.py`, `test_anthropic_client.py`)
- Can be skipped with `pytest -m "not e2e"`

**Import / Mode-Isolation Tests:**
- `tests/test_imports.py` — verifies all packages import without errors
- `tests/test_router.py::test_no_mode_silo_import` — verifies `state_core.providers` does not import mode-specific packages
- `tests/test_observability_import_graph.py` — verifies observability module isolation
- These are lightweight, fast, and critical for architecture enforcement

**Golden Tests:**
- `tests/auth/golden/` — JSON fixtures for auth provider header regression tests
- Regenerate with `pytest --update-goldens`
- Compare byte-for-byte against `state-inputs/claude-oauth.md` specs

**RED-First Testing (TDD pattern):**
- Some test files are written as RED scaffolding before implementation
- Commented at top of file: "Wave 0 — every test in this file MUST FAIL until Wave 1 lands"
- Tests are expected to fail with `ImportError` or `AttributeError` until the implementation is written
- No `pytest.skip()` or `pytest.importorskip()` used — the RED failure is the signal

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_connection_wal_mode(tmp_path: Path) -> None:
    db_path = tmp_path / ".state" / "events.sqlite"
    os.environ["STATE_DB_PATH"] = str(db_path)
    try:
        async with get_connection() as db:
            cursor = await db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert str(row[0]).lower() == "wal"
    finally:
        os.environ.pop("STATE_DB_PATH", None)
```

**Error Testing:**
```python
def test_oauth_routing_error_importable() -> None:
    assert issubclass(OAuthRoutingError, StateProviderError)

def test_event_rejects_mismatched_type(self) -> None:
    with pytest.raises(ValidationError):
        ArcCreatedEvent(
            **make_envelope_kwargs(),
            type="state.arc.retired",  # wrong!
            data=ArcCreatedData(title="T", goal="G"),
        )
```

**Pydantic Validation Testing:**
```python
def test_extra_forbid(self) -> None:
    with pytest.raises(ValidationError):
        EventEnvelope(nonexistent_field="value")  # type: ignore[call-arg]
```

**Security Regression Testing:**
```python
def test_oauth_route_log_no_token(deps: Deps) -> None:
    """select() for OAuthCredential must NOT log the access token value."""
    router = ProviderRouter()
    with structlog.testing.capture_logs() as cap_logs:
        router.select(FAKE_OAUTH, deps)
    for entry in cap_logs:
        for value in entry.values():
            assert "sk-ant-oat-fake" not in str(value)
```

**Protocol Conformance Testing:**
```python
def test_get_api_key_auth_returns_auth_method(provider_id: str) -> None:
    auth = get_api_key_auth(provider_id)
    assert isinstance(auth, AuthMethod)  # @runtime_checkable Protocol
```

---

*Testing analysis: 2026-05-05*
