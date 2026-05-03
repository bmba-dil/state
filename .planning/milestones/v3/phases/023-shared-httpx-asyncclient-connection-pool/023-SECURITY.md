---
phase: 023-shared-httpx-asyncclient-connection-pool
auditor: gsd-security-auditor
asvs_level: 1
block_on: high
completed: 2026-05-03
result: SECURED
threats_open: 0
---

# Security Audit — Phase 023

**Phase:** 023 — Shared `httpx.AsyncClient` with connection pool + proxy/TLS config
**Threats Closed:** 12/12
**ASVS Level:** 1
**Result:** SECURED

---

## Threat Verification

### 023-02-PLAN.md (Implementation Threats)

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-023-1 | Availability | mitigate | `build_shared_client()` is a plain function (not called at module level); `Deps(http_client=build_shared_client())` instantiated inside `async def startup()` at `orchestrator.py:57`. Module-level client construction confirmed absent. |
| T-023-2 | Integrity | mitigate | No `state_core/auth/providers/` or `auth/refresh.py` files appear in Phase 023 commits. `git log -- src/state_core/auth/providers/ src/state_core/sync_mirror.py` shows last touch predates Phase 023. |
| T-023-3 | Availability | accept | litellm.aclient_session assignment is annotated `# best-effort; works for non-Anthropic providers` at `orchestrator.py:58`. The `import litellm` at module level (line 5) will surface ImportError at daemon startup rather than inside startup(), but litellm is a declared dependency. Accepted disposition confirmed present. |
| T-023-4 | Integrity | mitigate | `src/state_core/sync_mirror.py` not present in Phase 023 modified-files lists in either PLAN or SUMMARY. No git diff output against that file. |
| T-023-5 | Availability | mitigate | `build_shared_client()` called from inside `async def startup()` (`orchestrator.py:57`), which executes within a running event loop. No module-level `httpx.AsyncClient` construction present. |
| T-023-6 | Integrity | mitigate | `deps.py:38`: `model_config = ConfigDict(arbitrary_types_allowed=True)`. `class Deps(BaseModel)` confirmed at `deps.py:28`. |
| T-023-7 | Integrity | mitigate | `http_client.py:33`: `_DEFAULT_KEEPALIVE_EXPIRY: float = 30.0`. Constructor call at line 70: `keepalive_expiry=keepalive_expiry` with default 30.0. |
| T-023-8 | Integrity | accept | `state_core.*` confirmed as shared kernel. `grep -rn "state_teach\|state_build" src/state_core/http_client.py src/state_core/deps.py` returns no matches — no cross-mode import violation present. Accepted disposition documented. |

### 023-01-PLAN.md (Test Infrastructure Threats)

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-023-9 | Integrity | mitigate | `tests/test_http_client.py:14`: `from state_core.http_client import build_shared_client` at module top level. `tests/test_deps.py:13`: `from state_core.deps import Deps` at module top level. Both import unconditionally — no `pytest.skip()` or conditional guard present (verified via grep: only occurrence in test_deps.py is in a docstring comment). |
| T-023-10 | Integrity | mitigate | Test function names confirmed present in implementation files matching VALIDATION.md map: `test_build_shared_client_defaults`, `test_build_shared_client_proxy`, `test_build_shared_client_tls_skip`, `test_build_shared_client_env_proxy`, `test_build_shared_client_env_ca`, `test_deps_holds_client`, `test_deps_aclose`, `test_startup_creates_deps`, `test_anthropic_client_injection`. |
| T-023-11 | Availability | mitigate | pyproject.toml `asyncio_mode = "auto"` (pre-existing). No module-level `httpx.AsyncClient` instances in test files. Each async test function gets an isolated loop via pytest-asyncio. |
| T-023-12 | Integrity | mitigate | `grep -c "auth.providers" tests/test_deps.py` returns 0. `test_deps.py` uses only `MagicMock(spec=httpx.AsyncClient)` and `AsyncMock(spec=httpx.AsyncClient)` — no auth provider module imported. |

---

## Unregistered Flags

None. Neither 023-01-SUMMARY.md nor 023-02-SUMMARY.md contains a `## Threat Flags` section. The SUMMARY files record two auto-fixed deviations (httpx 0.28.1 `_limits` attribute absent; AsyncMock needed for async startup methods) — both are implementation adaptations, not new threat surface. No unregistered flags to log.

---

## Accepted Risks Log

| Threat ID | Rationale |
|-----------|-----------|
| T-023-3 | litellm.aclient_session is best-effort for non-Anthropic provider traffic. If litellm is absent at startup, daemon currently surfaces ImportError at module load rather than a graceful WARN. This is accepted: litellm is a declared pinned dependency (`litellm>=1.80.0`) and absence indicates a broken install, not a runtime degradation scenario. Acceptable at ASVS Level 1. |
| T-023-8 | state_core.* is the shared kernel by architectural definition. Importing it from both state_build and state_teach is intentional and correct. The mode isolation rule (build must not import teach) is not violated. |
