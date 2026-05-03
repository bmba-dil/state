"""state_core.observability — mode-neutral observability plumbing.

Phase 020 (M-A2 / AUTH-10): root-logger token redactor.

Cardinal rules (per PROJECT.md / CLAUDE.md):

  1. Mode isolation — this package MUST NOT import state_build.*,
     state_teach.*, state.build.*, or state.teach.*. Enforced by
     tests/test_observability_import_graph.py (REDACT-25).

  2. Determinism — regex compilation at module-import time, no
     per-call re.compile, no datetime.now() / random.* reads.

  3. Defense-in-depth: this is layer 2 of the P0-14 secret-leak
     pitfall mitigation. Layer 1 is per-call-site discipline (already
     shipped in Phases 011-019). Layer 2 (this package) is the
     root-logger redactor that catches leaks even when layer 1
     regresses.

Public surface:
  * redact_processor(logger, method_name, event_dict) -> dict
    — structlog processor callable (Plan 02 owns).
  * iter_token_patterns() -> tuple[re.Pattern, ...]
    — accessor for the 12-family regex set (Plan 02 owns).
  * REDACTED — replacement literal (`"[REDACTED]"`, Plan 02 owns).
  * CYCLE_SENTINEL — cycle-detection sentinel (`"[CYCLE]"`, WK-01 / 022.3).
  * install(level=logging.DEBUG) -> None — idempotent installer (Plan 03 owns).
  * assert_redactor_attached() -> None — startup self-check (Plan 03 owns).
  * RedactorNotAttached — fatal exception (Plan 03 owns).
"""
from __future__ import annotations

from state_core.observability.redactor import (
    CYCLE_SENTINEL,
    REDACTED,
    RedactorNotAttached,
    assert_redactor_attached,
    install,
    iter_token_patterns,
    redact_processor,
)

__all__ = [
    "CYCLE_SENTINEL",
    "REDACTED",
    "RedactorNotAttached",
    "assert_redactor_attached",
    "install",
    "iter_token_patterns",
    "redact_processor",
]
