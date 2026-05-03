# Phase 021: First-run import from opencode `~/.local/share/opencode/auth.json` - Context

**Gathered:** 2026-05-01
**Status:** Ready for planning
**Mode:** Interactive discuss (4 areas, 17 questions across 5 rounds)

<domain>
## Phase Boundary

Detect opencode's existing `auth.json` and import its credentials into state's `.state/auth.json`, preserving array-per-provider shape (P1-7 defense).

Owns: the opencode-source migration path (`state_core.auth.import_opencode` or equivalent) + the daemon-start hook that calls it. Reuses Phase 012's `AuthVault` / `save_vault` and Phase 011's `Credential` union — never re-implements vault I/O or schema.

Requirement: AUTH-11.
P1 pitfall owned: P1-7 (`auth.json` migration corrupts array shape).

Does NOT own: the public `state auth` CLI surface (Phase 022), provider-specific OAuth flows (014–017), the API-key registry (018), or multi-cred rotation logic (019).

</domain>

<decisions>
## Implementation Decisions

### Trigger & invocation

- **Sync model: every daemon start, scan + diff + import-new-only.** Opencode is a living vault; users add/change credentials over time. On every `state-daemon` boot, read opencode's auth.json, compute the diff against state's vault, and append-only the new credentials.
- **Identity / equality check: `(provider_id, first 12 chars of access-or-key)`.** A rotated opencode token has a new prefix → imports as a new array element under the same provider. State-side credentials are never modified or deleted by the importer.
- **Merge shape: append to multi-cred array.** When state already has a cred for a provider AND opencode has a (different-prefix) one, the state vault's `providers[provider_id]` grows by one. Phase 019 round-robin handles selection. Honors the array-per-provider invariant unconditionally.
- **CLI surface: daemon-internal only.** Phase 021 ships the import function + the daemon-start hook. Phase 022 owns user-facing `state auth` Typer commands. No `python -m` argparse entry point in 021 (deferred to 022 if useful for smoke tests).
- **Failure mode: all-or-nothing (transactional).** Validate every opencode entry first → build a candidate `AuthVault` in memory → single `save_vault()` write through Phase 012. Any validation error aborts; state's vault stays untouched.
- **Hardness when opencode auth.json is unreadable** (wrong mode, corrupt JSON, decode failure): warn-and-continue. Daemon boots normally; structlog WARN with path + reason; vault untouched. Do NOT refuse daemon start (this is foreign data, not state's incident).

### Discovery surface

- **Path resolution: mirror opencode's algorithm exactly** (its `Global.Path.data`):
  1. Honor `OPENCODE_AUTH_CONTENT` env var (parse as in-memory JSON, mirrors `auth/index.ts:59`).
  2. Then `$XDG_DATA_HOME/opencode/auth.json` if XDG_DATA_HOME is set.
  3. Then platform default: `~/.local/share/opencode/auth.json` on Linux, `~/Library/Application Support/opencode/auth.json` on macOS.
- **State-side override: `STATE_OPENCODE_AUTH_PATH` env var wins over auto-discovery.** Mirrors Phase 012's `STATE_AUTH_JSON` pattern. Used in tests/CI to point at fixture vaults without mutating `~/.local/share/opencode/`.
- **Absent file: silent no-op (DEBUG log only).** Most users won't have opencode installed; absence is expected. One DEBUG log line on daemon start with the paths probed.
- **Windows: out of scope** (mirrors Phase 012's POSIX-only stance). On Windows the importer emits the same one-time warning Phase 012 emits and returns no-op.

### Type & ID mapping

- **Opencode `wellknown` (`{type, key, token}`): skip with INFO log.** State's `Credential` union is OAuth + ApiKey only (Phase 011 deliberately limited). Logs `{provider_id, reason: "wellknown_unsupported"}` — never the bytes. Forward-compatible: when a future phase adds wellknown support, the importer will pick them up automatically.
- **Opencode `OAUTH_DUMMY_KEY = "opencode-oauth-dummy-key"`: detect and skip with DEBUG log.** Opencode uses this sentinel to mark "logged in via OAuth, no real api key here" (`auth/index.ts:7`). Importing it as `ApiKeyCredential(key="opencode-oauth-dummy-key", ...)` would create a useless cred that silently 401s.
- **Provider ID translation: pass-through verbatim, then validate against known list.** Use opencode's key as our `provider_id` directly. After staging the candidate vault, validate each `provider_id` against the union of (Phase 018's 12-row API-key registry) ∪ (the 4 OAuth provider IDs from 014–017). Unknown `provider_id` is imported but logged INFO ("untracked_provider_imported"). Lets us see what users actually have without dropping data.
- **OAuth field renames (camelCase → snake_case):**
  - opencode `accountId` → state `account_id` (first-class field on `OAuthCredential`).
  - opencode `enterpriseUrl` → state `extras["enterprise_url"]` (provider-specific; only Anthropic enterprise uses it).
  - opencode api `metadata: dict` → state `extras` (verbatim copy; keys may be camelCase from opencode but loader code reads `extras` keys explicitly).
- **Type discriminator translation:**
  - opencode `type: "oauth"` → state `OAuthCredential` (`type: "oauth"` matches).
  - opencode `type: "api"` → state `ApiKeyCredential` (`type: "api_key"`). Type-string mismatch is the rename here.
  - opencode `type: "wellknown"` → skipped (above).

### Conflict resolution

- **Rotation handling**: identity is access-prefix only (above), so a rotated opencode token = different prefix = new array element. No in-place mutation. Array may grow over time; pruning is deferred to Phase 022's CLI (`state auth prune --expired` is a 022 candidate, NOT a 021 deliverable).
- **Provenance marker**: every imported cred carries `extras["_source"] = "opencode-import"`. Loader/runtime code MUST ignore underscore-prefixed extras keys. Used for debugging, audit, and future selective re-import. NO `_imported_at` timestamp (would violate determinism in handlers).
- **Audit event**: emit one `auth.imported` domain event per imported credential into `.state/events.sqlite` (dual-write to SyncEvent per the v1 cardinal rule). Event payload: `{provider_id, source: "opencode", cred_kind: "oauth" | "api_key"}`. NEVER includes any secret bytes (Phase 020 redactor is second defense layer; payload contract is first).
- **Duplicate input** (same `provider_id` + same access prefix appearing twice in opencode's auth.json — should be impossible but defensive): dedupe silently, first occurrence wins. Use a set during candidate-build.

### Claude's Discretion

- Module placement (`state_core/auth/import_opencode.py` vs `state_core/auth/migrations/opencode.py`).
- Function naming and internal helper structure.
- Whether the importer is sync or async (recommend sync — no I/O beyond stdlib + structlog; called once per daemon-start before any await).
- Exact structlog event names (suggest `auth.import.{found,started,credential_imported,wellknown_skipped,dummy_skipped,untracked_provider,duplicate_input,unreadable,absent,completed}`).
- Pydantic model for parsing opencode's auth.json shape (private to this module; do NOT import opencode's TS schema).
- The `auth.imported` event's exact field names and the `EventEnvelope` aggregate it belongs to (likely `auth` aggregate; coordinate with v1 event schema).
- Test fixture strategy (suggest hypothesis-strategy generators for round-trip tests with 1, 2, 5 creds per provider per P1-7 prevention).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`state_core.auth.store.AuthVault`** (Phase 012): the destination schema. `AuthVault.providers: dict[str, list[Credential]]` with the `_coerce_to_list` `field_validator` that promotes bare-dict to 1-element list — first line of P1-7 defense.
- **`state_core.auth.store.save_vault(path, vault)`** (Phase 012): atomic 0o600 write. The importer MUST go through this; no direct `auth.json` writes from 021.
- **`state_core.auth.store.load_vault(path)`** (Phase 012): reads existing state vault before diffing. Returns empty `AuthVault()` if missing.
- **`state_core.auth.store.get_auth_json_path()`** (Phase 012): resolves state's `.state/auth.json` path, honoring `STATE_AUTH_JSON` env override.
- **`state_core.auth.base.OAuthCredential` / `ApiKeyCredential`** (Phase 011): the discriminated-union variants. Importer constructs these directly; `CredentialAdapter.validate_python(...)` round-trips dicts.
- **`state_core.auth.base.Credential` discriminated union with `Field(discriminator="type")`**: opencode's `type: "api"` → must be remapped to our `type: "api_key"` before pydantic validation, not after.

### Established Patterns

- **Path resolution via env-var-then-default** (`state_core.auth.store.get_auth_json_path`): the importer's discovery function will mirror this pattern.
- **POSIX-only mode enforcement, Windows warn-and-skip** (`state_core.auth.store._verify_mode`): if 021 needs to verify opencode's file mode, follow the same shape.
- **Module isolation discipline**: `state_core.auth.*` imports are limited to stdlib + pydantic + orjson + structlog + sibling auth modules. NO `state_build.*` / `state_teach.*`. The import-graph test (BASE-08 / STORE-17 family) will need a new row for 021.
- **Frozen Pydantic credentials**: never mutate; use `model_copy(update={...})`. Importer constructs fresh instances from opencode dicts.
- **structlog event-dict logging** with `log = structlog.get_logger(__name__)` at module top. Phase 020's redactor is attached at root logger — safe to log paths and provider IDs (never secret bytes).
- **Determinism rule**: no `time.time()` / `datetime.now()` in handlers; clock injected as parameter. The importer either takes `now: float` or has none of its decisions depend on time (preferred — equality is by access-prefix, not by expiry).

### Integration Points

- **Daemon-start hook**: the importer's entry point is called from `state_daemon.orchestrator` boot sequence. Coordinate with Phase 020's `assert_redactor_attached()` self-check — order is:
  1. Install root-logger redactor (Phase 020 Step 0).
  2. Self-check redactor.
  3. Run opencode importer (Phase 021).
  4. Continue boot.
  Importer runs AFTER redactor is attached so any structlog calls are filtered.
- **`auth.imported` domain event** plugs into v1's `EventEnvelope` schema. Likely a new event-type variant under the `auth` aggregate. Coordinate with `state_core.events` (v1) for the type-versioning pattern.
- **Phase 019 multi-cred rotation** consumes the array shape this importer produces. Round-trip test: import 1, 2, 5 opencode creds for the same `provider_id` (each with distinct access prefix) → assert Phase 019's `select_credential` rotates over all of them.
- **Phase 022 CLI**: `state auth status` will likely surface "imported from opencode" via the `extras["_source"]` marker. 021 sets the marker; 022 reads it.

</code_context>

<specifics>
## Specific Ideas

- **Real opencode shape on the dev box** (verified `~/.local/share/opencode/auth.json` 2026-05-01): `{ "opencode": {"type": "api", "key": "..."}, "openrouter": {"type": "api", "key": "..."}, "deepseek": {"type": "api", "key": "..."} }`. Three plain api keys, no oauth, no wellknown — minimal smoke-test fixture is "import three api creds, end up with `providers["opencode"]`, `providers["openrouter"]`, `providers["deepseek"]` each as 1-element lists".
- **Opencode source of truth**: `state-inputs/opencode/packages/opencode/src/auth/index.ts` lines 13–34 (Oauth/Api/WellKnown schema); line 7 (`OAUTH_DUMMY_KEY`); line 59 (`OPENCODE_AUTH_CONTENT` env override); line 9 (`Global.Path.data` path).
- **P1-7 round-trip test (PITFALLS.md:197)**: "round-trip migration with 1, 2, and 5 credentials per provider". Use hypothesis to generate opencode-shaped dicts and assert `len(state_vault.providers[pid]) == n_imported_for_pid`.
- **No reflection of opencode's TS schema**: state's `OpencodeAuthEntry` Pydantic model is hand-rolled, lives inside the import module, and is private (`_OpencodeOauthEntry`, `_OpencodeApiEntry`). When opencode's schema evolves, this module gets a manual update.
- **Ordering invariant**: when appending to `providers[pid]`, append at the END of the existing list. State-native creds (added via 014–018 login flows) sort first; opencode imports sort after. Phase 019's rotation index continues working unchanged.
- **`expires` unit**: opencode's `Schema.Number` for `expires` matches state's `OAuthCredential.expires: float` (epoch seconds; `auth/base.py` lines 65–72). Carry verbatim — no unit conversion. (If the planner finds opencode actually uses ms anywhere, that becomes a bug to fix at planning time.)

</specifics>

<deferred>
## Deferred Ideas

- **`state auth prune --expired`** (cleanup of accumulated multi-cred arrays from rotation-driven appends) — Phase 022 candidate.
- **`state auth import-opencode --force` Typer command** (manual re-import + opt-out of auto-import) — Phase 022.
- **`state auth status` UX showing "imported from opencode" provenance** — Phase 022, reads the `extras["_source"]` marker this phase sets.
- **Wellknown credential support** — needs a third Credential variant in Phase 011's union, plus protocol updates in 014–017. Not a first-class need; revisit only if a real provider requires it.
- **Bidirectional sync** (write state's new credentials back into opencode's auth.json so opencode can use them) — explicit non-goal; opencode is read-only from state's perspective.
- **Windows path resolution + mode enforcement** — milestone-level Windows support is its own arc; 021 emits the same warning as 012.
- **Opencode metadata-based identity** (`accountId` + `metadata` fingerprint as identity) — possibly a more robust identity than access-prefix; revisit if rotation churn becomes a real issue in the field.

</deferred>

---

*Phase: 021-first-run-import-opencode-local*
*Context gathered: 2026-05-01*
