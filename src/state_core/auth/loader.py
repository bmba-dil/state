"""Credential resolver — fuses Phase 012's vault with Phase 018's env-var spec.

Phase 018 (M-A2 / AUTH-05). Sibling of base.py / store.py / refresh.py /
errors.py at the auth-module top level — placement chosen because
load_credentials is *orchestration* (vault + env-fallback fusion), not a
*provider implementation*. Putting it under providers/ would mislead
callers ("load credentials FROM a provider" vs "load credentials").

Public API (single function):
    load_credentials(provider_id: str) -> list[Credential]

Resolution rules (CONTEXT.md §Env-var fallback locked):
    1. Vault > env. Vault-empty fallback only.
    2. If auth.json has 1+ credentials for provider_id, return them
       (env ignored).
    3. If vault has no entry (file missing OR provider_id not in
       providers OR providers[provider_id] is the empty list), AND
       os.environ[spec.env_var] is set + non-empty (after strip),
       synthesize ONE ephemeral ApiKeyCredential and return [it].
    4. Empty / whitespace-only env values treated as unset (12-factor).
    5. Synthesized credentials are NEVER persisted — vault file
       unchanged after env-only synthesis (T-018-10 ASVS V8.3.7).
    6. Cross-provider env-var leak prevented — only consult
       _REGISTRY[provider_id].env_var (T-018-5 ASVS V1.4.5).

Cardinal rules (CLAUDE.md / Phase 018 RESEARCH §loader Placement):

  1. Mode isolation — imports limited to stdlib + state_core.auth.{base,
     store, providers.api_key, errors}. NO state.build.* / state.teach.*.
     Import-graph one-way edge: this module imports providers/api_key.py;
     providers/api_key.py MUST NOT depend on this module at module scope
     (T-018-7 / cycle prevention). tests/auth/test_import_graph.py
     enforces both directions.

  2. No persistence inside load_credentials — synthesizing from env
     must NEVER write the vault. The "env was wrong, now it's stuck"
     footgun was the design driver (CONTEXT.md `<deferred>` rejection
     of state-auth-import-env until Phase 022 if asked). Concretely,
     this module does not import or invoke any vault-mutation surface
     from state_core.auth.store; only the read side is in scope.

  3. Determinism — no time.time() / datetime.now() reads. The function
     is pure of clock state; pure of randomness.

  4. AuthVaultPermissionError propagates. Wrong-mode auth.json is a
     security incident handled at the daemon-boot / CLI layer (Phase
     022); this module is a thin pass-through.

Downstream consumers:
  * Phase 022 CLI (state auth status / login) — primary consumer.
  * Phase 019 multi-cred round-robin — operates on what
    load_credentials returns; round-robin only applies to vault-sourced
    lists (env synthesis returns at most 1 cred, no rotation).
  * v3 milestone (Provider Routing) — reads load_credentials before
    injecting auth headers via cred-method.http_headers().

See .planning/milestones/v2/phases/018-plain-api-key-vault/018-RESEARCH.md
§state_core.auth.loader Placement for the architectural rationale and
the directional-import constraint.
"""

from __future__ import annotations

import os

import structlog

from state_core.auth.base import ApiKeyCredential, Credential
from state_core.auth.errors import UnknownApiKeyProviderError
from state_core.auth.providers.api_key import _REGISTRY
from state_core.auth.store import (
    AuthVaultPermissionError,  # noqa: F401 — re-exported for caller convenience
    get_auth_json_path,
    load_vault,
)

log = structlog.get_logger(__name__)


def load_credentials(provider_id: str) -> list[Credential]:
    """Resolve credentials for *provider_id* — vault wins, env synthesizes.

    See module docstring for the full resolution rule set.

    Args:
        provider_id: One of the 12 registered provider_ids
                     (state_core.auth.providers.api_key._REGISTRY keys).

    Returns:
        list[Credential] — empty when neither vault nor env have a
        value for this provider; a 1-element list of an ephemeral
        ApiKeyCredential when env-synthesized; the vault list (in
        insertion order, preserved by Phase 012's array-per-provider
        invariant P0-13) when vault is the source.

    Raises:
        UnknownApiKeyProviderError: *provider_id* not in _REGISTRY.
            Proxied from the registry lookup; same exception subclass
            consumers expect from get_api_key_auth.
        AuthVaultPermissionError: vault file exists but mode != 0o600.
            Propagates unchanged from store._verify_mode (Phase 012).

    Examples:
        >>> # vault has openai cred → vault wins
        >>> load_credentials("openai")
        [ApiKeyCredential(provider_id='openai', extras={})]

        >>> # vault empty, OPENAI_API_KEY set → 1 ephemeral cred
        >>> os.environ["OPENAI_API_KEY"] = "sk-test-XXXX"
        >>> load_credentials("openai")
        [ApiKeyCredential(provider_id='openai', extras={})]

        >>> # neither set → []
        >>> del os.environ["OPENAI_API_KEY"]
        >>> load_credentials("openai")
        []
    """
    # Step 1: registry lookup — fail-fast on unknown provider_id.
    try:
        spec = _REGISTRY[provider_id]
    except KeyError:
        raise UnknownApiKeyProviderError(provider_id) from None

    # Step 2: try the vault first. load_vault returns AuthVault() for
    # missing files (Phase 012 contract — FileNotFoundError caught
    # inside). AuthVaultPermissionError propagates unchanged.
    vault_path = get_auth_json_path()
    vault = load_vault(vault_path)

    # Step 3: vault wins when non-empty.
    vault_creds: list[Credential] = list(vault.providers.get(provider_id, []))
    if vault_creds:
        log.debug(
            "loader.vault_hit",
            provider_id=provider_id,
            count=len(vault_creds),
        )
        return vault_creds

    # Step 4: env-fallback synthesis. T-018-5 — consult ONLY this
    # provider's env_var. T-018-8 (12-factor) — strip + empty == unset.
    env_value = os.environ.get(spec.env_var, "")
    if not env_value or not env_value.strip():
        log.debug(
            "loader.no_creds",
            provider_id=provider_id,
            env_var=spec.env_var,
        )
        return []

    # Synthesize ephemeral credential. T-018-10 — this code path MUST
    # NOT invoke any vault-mutation surface; the synthesized credential
    # exists only in the returned list. Use the stripped value (matches
    # user intent — leading/trailing whitespace in an env var is almost
    # certainly a typo). Phase 022 may revisit if a real user complaint
    # surfaces.
    cred = ApiKeyCredential(
        key=env_value.strip(),
        provider_id=provider_id,
    )
    log.debug(
        "loader.env_synthesis",
        provider_id=provider_id,
        env_var=spec.env_var,
    )
    return [cred]


__all__ = ["load_credentials"]
