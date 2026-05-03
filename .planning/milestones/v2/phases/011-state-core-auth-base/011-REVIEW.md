---
phase: 011
slug: state-core-auth-base
status: clean
reviewed: 2026-04-28
findings_critical: 0
findings_major: 0
findings_minor: 0
findings_style: 0
---

# Phase 011 — Code Review

**Files reviewed:**
- `src/state_core/auth/base.py` (221 LOC)
- `src/state_core/auth/__init__.py` (29 LOC)
- `tests/auth/test_base.py` (183 LOC)
- `tests/auth/conftest.py` (39 LOC)

## Summary

**Status: CLEAN.** No findings at any severity level.

## Strengths

- **Discriminated union mirrors `state_core.schema` pattern verbatim.** New providers slot in via Pydantic discriminator — variants are explicit, visible in PR review.
- **Secret hygiene defense-in-depth.** `Field(repr=False)` on `access`, `refresh`, `key` is layer 1; structlog redactor in Phase 020 will be layer 2. Pydantic's `frozen=True` ensures secrets cannot be re-assigned post-construction.
- **Determinism enforced at the source.** Module-level grep gate (no `import time`, no `from datetime`) keeps replay byte-identical. The `now: float` parameter on `is_expired` is the only legal clock surface.
- **Mode isolation respected.** No `state_build` / `state_teach` imports. `state_core.auth.base` is in the shared kernel, importable by both modes.
- **Documentation embeds the cardinal rules.** Each non-obvious design choice (wire-shape `expires`, runtime_checkable caveat, Pitfall 1 mitigation) is documented inline so the next maintainer sees them.
- **`__all__` matches the public surface in both `base.py` and `__init__.py`.** No stray re-exports.

## Correctness

No issues. Pydantic v2 idioms used correctly:
- `ConfigDict` (not the v1 `class Config:` form)
- `Annotated[Union, Field(discriminator=...)]` (the v2-canonical discriminated-union form)
- `TypeAdapter` for runtime validation of the union
- `model_copy(update={...})` for refresh-creates-new-instance semantics

## Security

No issues. `Field(repr=False)` is applied to every secret; tests confirm `repr(cred)` does not leak.

## Performance

No issues. `TypeAdapter` is pre-built at module import, avoiding per-call rebuild cost in the vault hot path (Phase 012).

## Maintainability

- **Naming is clear.** `OAuthCredential` / `ApiKeyCredential` / `Credential` (the union alias) follow the existing schema-aggregate naming pattern.
- **Single responsibility.** `base.py` defines shape only — no I/O, no provider logic, no dispatcher. All deferred concerns (registry, sniffer dispatch, filelock, redaction) carry forward-references to their owning phase.
- **DRY.** `_CredentialBase` factors out shared `model_config`. Each variant adds only its own fields.
- **Test coverage.** 11/11 BASE-XX tests pass; conftest has 3 minimal fixtures (frozen `now`, sample OAuth, sample API key).

## Notes (non-findings)

The verifier flagged a project-wide `mypy --strict` issue affecting 11 unrelated errors across 6 files in `state_core/`; strict on `base.py` itself is clean ("Success: no issues found in 1 source file"). This is pre-existing and out of scope for phase 011.
