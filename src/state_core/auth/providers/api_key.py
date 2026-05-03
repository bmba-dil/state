"""Plain API-key provider — registry-driven AuthMethod for 12 vendors.

Phase 018 (M-A2 / AUTH-05). FIFTH AuthMethod implementation (after Phase
014 Anthropic OAuth, 015 Gemini-CLI, 016 Antigravity, 017 GitHub Copilot)
but the FIRST without an OAuth flow — plain api keys are uniform table-
driven specs (env_var, header, prefix). One PlainApiKeyAuth class
parameterised by provider_id replaces what would be 12 sibling files.

Cardinal rules (CLAUDE.md / Phase 011 / Phase 018 RESEARCH):

  1. _REGISTRY iteration order is LOAD-BEARING — sk- prefixed providers
     MUST be ordered longest-prefix-first across providers (Anthropic
     sk-ant-api03- → OpenRouter sk-or-v1- → OpenAI sk-). Within a
     provider, key_prefixes MUST also be longest-first. The downstream
     token-shape sniffer (Phase 022 CLI / Phase 020 redactor) walks
     _REGISTRY in declared order. Adding a new sk- provider requires
     re-reviewing this ordering. tests/auth/test_api_key.py asserts.

  2. Mode isolation (CLAUDE.md) — imports limited to stdlib + pydantic
     + structlog + state_core.auth.{base, errors}. NO state_core.auth.
     loader (one-way edge — T-018-7), NO state.build.* / state.teach.*.
     _main() locally imports state_core.auth.store for vault persistence;
     this is the ONLY non-base/errors auth import in the file.

  3. Secret hygiene (T-018-1, T-018-2, T-018-3):
        - argparse defines NO --api-key flag (T-018-1 — argv leakage).
        - Login reads via getpass.getpass on TTY, sys.stdin on non-TTY.
        - The prefix-mismatch warning logs ONLY observed_prefix=key[:8],
          NEVER the full key (T-018-3).
        - UnknownApiKeyProviderError messages carry provider_id only,
          NEVER the api key (T-018-2 — Phase 020 redactor is layer 2).
        - ApiKeyCredential.key inherits Field(repr=False) from Phase 011.

  4. Determinism (Phase 011 cardinal rule 2) — is_expired(cred, now)
     takes `now` as a parameter; never time.time() internally. Phase
     018 trivially complies (always returns False).

  5. Per-call construction (Phase 014 Pattern 2 / P1-9) — get_api_key_auth
     returns a fresh PlainApiKeyAuth instance per call. No module-level
     singletons except _REGISTRY itself (an immutable spec table).

  6. Provenance comments (mirrors claude-oauth.md byte-for-byte
     provenance pattern Phase 014 established) — every _REGISTRY row
     carries a `# captured 2026-04-30 from <url>` comment so vendor
     prefix drift is detectable without git archaeology.

Module layout:
  * Imports
  * print = print rebind (testability — mirrors anthropic.py / google_gemini.py)
  * ApiKeyProviderSpec (frozen Pydantic, extra="forbid")
  * _REGISTRY (12 rows, captured 2026-04-30, longest-sk-prefix-first ordering)
  * Helpers: _validate_format, _warn_prefix_mismatch
  * PlainApiKeyAuth class (5-method AuthMethod)
  * Public factory + helper: get_api_key_auth, iter_known_prefixes
  * `if __name__ == "__main__": sys.exit(_main())` block

Downstream consumers:
  * tests/auth/test_api_key.py — Plan 01 RED → GREEN target
  * tests/auth/test_main_api_key.py — argparse surface tests
  * state_core.auth.loader — Phase 018 Plan 03 imports _REGISTRY
  * Phase 019 multi-cred round-robin — operates on vault.providers[provider_id]
    lists; Phase 018 ensures array shape preserved (P0-13 invariant).
  * Phase 020 root-logger redactor — consumes iter_known_prefixes() for
    regex set construction.
  * Phase 022 CLI — wraps PlainApiKeyAuth.login + _main delegate.

See .planning/milestones/v2/phases/018-plain-api-key-vault/018-RESEARCH.md
for the full registry verification, sk- collision resolution, threat
model (10 threats), and validation matrix (21 rows).
"""

from __future__ import annotations

import getpass
import os
import sys
from typing import Iterator

# Re-bind for testability — mirrors anthropic.py / google_gemini.py / etc.
# Plan 01's argparse tests monkeypatch this module-level binding to
# capture printed output without spawning a subprocess.
print = print  # noqa: A001 — intentional re-bind for testability

import structlog
from pydantic import BaseModel, ConfigDict

from state_core.auth.base import (
    ApiKeyCredential,
    AuthMethod,  # noqa: F401 — runtime_checkable Protocol; isinstance check in tests
    Credential,
)
from state_core.auth.errors import (
    AuthError,  # noqa: F401 — re-export symmetry; Phase 022 catches AuthError broadly
    AuthLoginError,
    UnknownApiKeyProviderError,
)

# T-018-7 one-way edge: this module MUST NOT depend on the loader module
# at module scope (loader depends on us; reverse edge would be circular).
# Enforced by tests/auth/test_import_graph.py.
# CONTEXT.md "PlainApiKeyAuth is pure": this module also MUST NOT depend
# on the store module at module scope. _main() locally imports store
# for the login subcommand only.

log = structlog.get_logger(__name__)


# ── ApiKeyProviderSpec ───────────────────────────────────────────────────


class ApiKeyProviderSpec(BaseModel):
    """Frozen spec describing one plain-api-key provider.

    model_config:
        frozen=True       — immutable post-construction (mirrors _CredentialBase)
        extra="forbid"    — adding a new column requires editing the schema

    Fields:
        provider_id: stable vault key (e.g. "anthropic.api_key", "google.ai_studio")
        auth_header: (header_name, value_template) — value_template uses
                     "{key}" placeholder rendered via .format(key=cred.key)
        key_prefixes: longest-first within this provider; () means "no
                      published prefix; warn-and-store any value"
        env_var: canonical SDK env-var name (12-factor; empty-string == unset)
        notes: free-form provenance / SDK-divergence comment
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str
    auth_header: tuple[str, str]
    key_prefixes: tuple[str, ...]
    env_var: str
    notes: str = ""


# ── _REGISTRY — 12 rows, captured 2026-04-30 ─────────────────────────────


_REGISTRY: dict[str, ApiKeyProviderSpec] = {
    # captured 2026-04-30 from https://platform.claude.com/docs/en/api/getting-started
    "anthropic.api_key": ApiKeyProviderSpec(
        provider_id="anthropic.api_key",
        auth_header=("x-api-key", "{key}"),
        key_prefixes=("sk-ant-api03-",),
        env_var="ANTHROPIC_API_KEY",
        notes=(
            "Direct console keys (NOT OAuth — the 'anthropic' provider_id "
            "is reserved for Phase 014's OAuth stealth flow)."
        ),
    ),
    # captured 2026-04-30 from https://openrouter.ai/docs/api/reference/authentication
    "openrouter": ApiKeyProviderSpec(
        provider_id="openrouter",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=("sk-or-v1-", "sk-or-"),
        env_var="OPENROUTER_API_KEY",
        notes="Longest-first within provider — sk-or-v1- before sk-or-.",
    ),
    # captured 2026-04-30 from https://platform.openai.com/docs/api-reference/authentication
    "openai": ApiKeyProviderSpec(
        provider_id="openai",
        auth_header=("Authorization", "Bearer {key}"),
        # Longest-first within provider: sk-svcacct- (11) > sk-proj- (8) ==
        # sk-None- (8) > sk- (4). The bare sk- is the legacy fallback and
        # MUST be last so longer-prefix matches win locally.
        key_prefixes=("sk-svcacct-", "sk-proj-", "sk-None-", "sk-"),
        env_var="OPENAI_API_KEY",
        notes=(
            "Bare sk- is the legacy fallback; new keys are sk-proj-/"
            "sk-svcacct-/sk-None-. OpenAI rotated to sk-proj- in 2024."
        ),
    ),
    # captured 2026-04-30 from https://docs.anyscale.com/endpoints/text-generation/authenticate/
    "anyscale": ApiKeyProviderSpec(
        provider_id="anyscale",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=("esecret_",),
        env_var="ANYSCALE_API_KEY",
        notes=(
            "Anyscale Endpoints product status uncertain as of 2026-04-30; "
            "verify before relying in production."
        ),
    ),
    # captured 2026-04-30 from https://docs.x.ai/developers/quickstart
    "xai": ApiKeyProviderSpec(
        provider_id="xai",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=("xai-",),
        env_var="XAI_API_KEY",
        notes="xAI Grok inference.",
    ),
    # captured 2026-04-30 from https://console.groq.com/docs/quickstart
    "groq": ApiKeyProviderSpec(
        provider_id="groq",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=("gsk_",),
        env_var="GROQ_API_KEY",
        notes="",
    ),
    # captured 2026-04-30 from https://ai.google.dev/gemini-api/docs/api-key
    "google.ai_studio": ApiKeyProviderSpec(
        provider_id="google.ai_studio",
        auth_header=("x-goog-api-key", "{key}"),
        key_prefixes=(),
        env_var="GEMINI_API_KEY",
        notes=(
            "Header form preferred over ?key= query param. "
            "Google's SDK also accepts GOOGLE_API_KEY; Phase 022 may "
            "add as alias if collision pain materializes."
        ),
    ),
    # captured 2026-04-30 from https://api-docs.deepseek.com/
    "deepseek": ApiKeyProviderSpec(
        provider_id="deepseek",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=(),
        env_var="DEEPSEEK_API_KEY",
        notes="",
    ),
    # captured 2026-04-30 from https://docs.together.ai/docs/quickstart
    "together": ApiKeyProviderSpec(
        provider_id="together",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=(),
        env_var="TOGETHER_API_KEY",
        notes="",
    ),
    # captured 2026-04-30 from https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key
    "mistral": ApiKeyProviderSpec(
        provider_id="mistral",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=(),
        env_var="MISTRAL_API_KEY",
        notes="",
    ),
    # captured 2026-04-30 from https://docs.cohere.com/reference/about
    "cohere": ApiKeyProviderSpec(
        provider_id="cohere",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=(),
        env_var="COHERE_API_KEY",
        notes=(
            "Cohere's official Python SDK reads CO_API_KEY; ecosystem "
            "(litellm, LangChain, AutoGen) uses COHERE_API_KEY. Phase 018 "
            "ships COHERE_API_KEY (12-factor canonical); Phase 022 may "
            "add CO_API_KEY as alias if pain materializes."
        ),
    ),
    # captured 2026-04-30 from https://inference-docs.cerebras.ai/api-reference/authentication
    "cerebras": ApiKeyProviderSpec(
        provider_id="cerebras",
        auth_header=("Authorization", "Bearer {key}"),
        key_prefixes=(),
        env_var="CEREBRAS_API_KEY",
        notes="",
    ),
}
"""The 12 plain-api-key providers per AUTH-05.

Iteration order is LOAD-BEARING — adding a new sk-prefixed provider
requires re-reviewing the longest-prefix-first invariant across all
sk- providers. See cardinal rule 1 in the module docstring.

Adding a 13th provider:
  1. Append a new entry with provenance comment + ApiKeyProviderSpec call.
  2. If new entry has sk- prefixes, re-order to maintain longest-first.
  3. Run tests/auth/test_api_key.py::test_sniff_resolves_sk_collision and
     test_registry_has_12_providers (the 12 will need updating).
  4. Update Phase 020's redactor regex if the prefix is novel.
"""


# ── Helpers ──────────────────────────────────────────────────────────────


def _validate_format(key: str) -> None:
    """Raise AuthLoginError if *key* is empty / whitespace-only.

    T-018-2: error message is generic — never carries the key bytes.
    """
    if not key or not key.strip():
        raise AuthLoginError("API key cannot be empty or whitespace-only.")


def _warn_prefix_mismatch(
    provider_id: str, key: str, spec: ApiKeyProviderSpec
) -> None:
    """Emit a single structlog warning if *key* matches none of spec.key_prefixes.

    T-018-3: logs ONLY observed_prefix=key[:8], NEVER the full key.

    No-op if spec.key_prefixes is () — providers without published prefixes
    get warn-free.
    """
    if not spec.key_prefixes:
        return
    if any(key.startswith(p) for p in spec.key_prefixes):
        return
    log.warning(
        "api_key.prefix_mismatch",
        provider_id=provider_id,
        observed_prefix=key[:8],
        expected_prefixes=spec.key_prefixes,
    )


# ── PlainApiKeyAuth ──────────────────────────────────────────────────────


class PlainApiKeyAuth:
    """AuthMethod implementation for table-driven plain-api-key providers.

    Constructed from an ApiKeyProviderSpec; one instance per provider_id.
    Use the `get_api_key_auth(provider_id)` factory rather than calling
    __init__ directly (factory raises UnknownApiKeyProviderError on miss).

    Structurally satisfies @runtime_checkable AuthMethod (5-method
    Protocol) — `isinstance(auth, AuthMethod)` returns True.
    """

    def __init__(self, spec: ApiKeyProviderSpec) -> None:
        self.spec = spec
        self.provider_id: str = spec.provider_id

    # ── Sync (pure introspection — no I/O) ───────────────────────────

    def is_token(self, value: str) -> bool:
        """Return True iff *value* matches one of this provider's prefixes.

        Empty key_prefixes tuple → always returns False. The downstream
        token-shape sniffer iterates _REGISTRY in declared order; the
        longest-matching provider wins (sk- collision resolution).
        """
        if not self.spec.key_prefixes:
            return False
        return any(value.startswith(p) for p in self.spec.key_prefixes)

    def is_expired(self, cred: Credential, now: float) -> bool:
        """ApiKeyCredential never expires — always returns False.

        Determinism rule: `now` is accepted as a parameter (per Phase 011)
        but unused. Signature preservation matters for AuthMethod Protocol
        symmetry across all 5 implementations.
        """
        return False

    def http_headers(self, cred: Credential) -> dict[str, str]:
        """Render spec.auth_header against cred.key.

        Examples:
          anthropic.api_key  → {"x-api-key": cred.key}
          google.ai_studio   → {"x-goog-api-key": cred.key}
          else (10 of 12)    → {"Authorization": f"Bearer {cred.key}"}

        Raises TypeError if cred is not an ApiKeyCredential — the Protocol
        contract is per-method permissive but downstream callers MUST
        type-narrow first.
        """
        if not isinstance(cred, ApiKeyCredential):
            raise TypeError(
                f"PlainApiKeyAuth.http_headers requires ApiKeyCredential, "
                f"got {type(cred).__name__}"
            )
        name, value_template = self.spec.auth_header
        return {name: value_template.format(key=cred.key)}

    # ── Async (interactive / CPU-trivial) ─────────────────────────────

    async def login(self) -> ApiKeyCredential:
        """Run the interactive login flow and return a fresh ApiKeyCredential.

        Flow:
          1. Read key via getpass on TTY, sys.stdin on non-TTY.
             - TTY detection: os.isatty(0).
             - Non-TTY: read first line, rstrip newline.
          2. _validate_format → AuthLoginError on empty/whitespace.
          3. _warn_prefix_mismatch → structlog warning (no raise).
          4. Return ApiKeyCredential(key=..., provider_id=spec.provider_id).

        Does NOT touch auth.json — persistence is the caller's job
        (typically _main() for the smoke surface, or Phase 022's CLI
        handler). This keeps PlainApiKeyAuth pure and round-trippable.

        T-018-1: NO --api-key flag exists at the argparse layer; this
        method has no `key` parameter. argv leakage is impossible by
        construction.

        Raises:
            AuthLoginError: empty / whitespace-only key.
        """
        prompt = f"{self.spec.provider_id} API key: "
        if os.isatty(0):
            key = getpass.getpass(prompt)
        else:
            # Non-TTY: pipe / heredoc / CI. Read one line, drop newline.
            key = sys.stdin.readline().rstrip("\n").rstrip("\r")

        _validate_format(key)
        _warn_prefix_mismatch(self.provider_id, key, self.spec)

        return ApiKeyCredential(
            key=key,
            provider_id=self.provider_id,
        )

    async def refresh(self, cred: Credential) -> Credential:
        """Plain api keys never expire — return *cred* unchanged.

        Symmetry with Phase 011's AuthMethod Protocol: the OAuth provider
        refresh path returns a model_copy with new access/refresh/expires.
        ApiKeyCredential has no such fields; the unchanged credential is
        structurally a "refresh" with zero deltas.

        For the api_key case, NO AuthRefreshError is reachable — there's
        no network call, no 401, no expiry check. Phase 022's __main__
        refresh subcommand prints "API keys never expire" and returns 0.
        """
        return cred


# ── Public factory + helper ──────────────────────────────────────────────


def get_api_key_auth(provider_id: str) -> AuthMethod:
    """Return a fresh PlainApiKeyAuth for *provider_id*.

    Per-call construction (Pattern 2 / P1-9) — no cached singleton.
    Tests rely on isinstance(get_api_key_auth(pid), AuthMethod) holding.

    Raises:
        UnknownApiKeyProviderError: provider_id not in _REGISTRY.
            Message includes the offending provider_id but NEVER any
            api key (T-018-2 — caller must NOT pass keys through this
            exception's chain).
    """
    try:
        spec = _REGISTRY[provider_id]
    except KeyError:
        raise UnknownApiKeyProviderError(provider_id) from None
    return PlainApiKeyAuth(spec)


def iter_known_prefixes() -> Iterator[str]:
    """Yield every key prefix across all 12 providers in _REGISTRY order.

    Phase 020's root-logger redactor consumer — provides a stable surface
    independent of _REGISTRY's internal layout, so a future _REGISTRY
    refactor doesn't ripple into the redactor.

    Order: outer = _REGISTRY insertion (longest-sk- first), inner =
    spec.key_prefixes (longest-first within provider). Providers with
    empty key_prefixes contribute nothing.
    """
    for spec in _REGISTRY.values():
        for prefix in spec.key_prefixes:
            yield prefix


# ── __main__ argparse block ──────────────────────────────────────────────


def _main() -> int:
    """argparse entry-point: login | list | refresh subcommands.

    Exit codes:
      0   — success
      1   — AuthLoginError / UnknownApiKeyProviderError / persistence failure
      2   — argparse usage (provided by argparse itself)
      130 — KeyboardInterrupt (POSIX SIGINT)
    """
    import argparse
    import asyncio

    # Local-import store: keeps PlainApiKeyAuth itself pure of vault I/O
    # at module-load (CONTEXT.md "PlainApiKeyAuth.login does not touch
    # auth.json").
    from state_core.auth.store import (
        ensure_initialized,
        get_auth_json_path,
        load_vault,
        save_vault,
    )

    parser = argparse.ArgumentParser(
        prog="python -m state_core.auth.providers.api_key",
        description="Plain api-key provider — Phase 018 smoke surface.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # login subcommand
    login_parser = sub.add_parser(
        "login",
        help="Interactive login: getpass on TTY, stdin on non-TTY.",
    )
    login_parser.add_argument(
        "provider_id",
        choices=sorted(_REGISTRY.keys()),
        help="One of the 12 registered providers.",
    )
    login_parser.add_argument(
        "--replace",
        action="store_true",
        default=False,
        help=(
            "Truncate provider's vault entry to a single new credential "
            "(default: append)."
        ),
    )

    # list subcommand
    sub.add_parser(
        "list",
        help="Print every registry row: provider_id, env_var, prefixes, header.",
    )

    # refresh subcommand (no-op for api keys)
    refresh_parser = sub.add_parser(
        "refresh",
        help="No-op for api keys — included for AuthMethod symmetry.",
    )
    refresh_parser.add_argument(
        "provider_id",
        choices=sorted(_REGISTRY.keys()),
        help="One of the 12 registered providers.",
    )

    args = parser.parse_args()

    if args.cmd == "list":
        for pid, spec in _REGISTRY.items():
            hdr = spec.auth_header[0]
            prefixes = (
                ",".join(spec.key_prefixes) if spec.key_prefixes else "(none)"
            )
            print(f"{pid}\t{spec.env_var}\t{prefixes}\t{hdr}")
        return 0

    if args.cmd == "refresh":
        print(
            f"API key credentials never expire — nothing to refresh "
            f"for {args.provider_id}."
        )
        return 0

    if args.cmd == "login":
        try:
            auth = get_api_key_auth(args.provider_id)
            cred = asyncio.run(auth.login())
        except KeyboardInterrupt:
            print("\nLogin cancelled.", file=sys.stderr)
            return 130
        except UnknownApiKeyProviderError as exc:
            print(f"Unknown provider: {exc}", file=sys.stderr)
            return 1
        except AuthLoginError as exc:
            print(f"Login failed: {exc}", file=sys.stderr)
            return 1

        # Persist via Phase 012's atomic-write + chmod 0600. Append-default
        # with dedup; --replace truncates.
        try:
            vault_path = get_auth_json_path()
            ensure_initialized(vault_path)
            vault = load_vault(vault_path)
            bucket = vault.providers.setdefault(args.provider_id, [])
            if args.replace:
                bucket.clear()
                bucket.append(cred)
            else:
                # Dedup on identical key string (T-018 CONTEXT.md decision).
                if not any(
                    isinstance(existing, ApiKeyCredential)
                    and existing.key == cred.key
                    for existing in bucket
                ):
                    bucket.append(cred)
            save_vault(vault_path, vault)
        except Exception as exc:
            print(
                f"Failed to persist credential to vault: {exc}",
                file=sys.stderr,
            )
            return 1

        print(
            f"Logged in to {args.provider_id} "
            f"({len(vault.providers[args.provider_id])} credential(s) on file)."
        )
        return 0

    # argparse with required=True should never reach here.
    return 2


if __name__ == "__main__":
    sys.exit(_main())


__all__ = [
    "ApiKeyProviderSpec",
    "PlainApiKeyAuth",
    "UnknownApiKeyProviderError",
    "_REGISTRY",
    "get_api_key_auth",
    "iter_known_prefixes",
]
