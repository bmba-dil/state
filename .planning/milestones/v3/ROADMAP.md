# v3 — Provider Routing + Model Profiles

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 023–031 (9 phases)

---

## Phases

#### Phase 023: Shared `httpx.AsyncClient` with connection pool + proxy/TLS config
**Goal:** Single daemon-owned client, dep-injected via `Deps`.
**Depends on:** 001
**Requirements:** PRV-06
**Parallelizable:** yes

#### Phase 024: litellm wrapper (`state_core.providers.litellm_client`)
**Goal:** `acompletion` with `client=shared_httpx`, streaming normalization, error taxonomy.
**Depends on:** 023
**Requirements:** PRV-01, PRV-07
**Parallelizable:** yes with 025

#### Phase 025: Direct Anthropic SDK escape hatch
**Goal:** `anthropic.AsyncAnthropic(http_client=shared_httpx)` with stealth headers when OAuth cred; extended thinking blocks + fine-grained cache-control preserved.
**Depends on:** 023, 014
**Requirements:** PRV-02, PRV-08, PRV-09
**Parallelizable:** yes with 024

#### Phase 026: OAuth stealth bypass guard (PRV-03)
**Goal:** `ProviderRouter.select()` — if cred is `sk-ant-oat*`, route MUST be direct SDK; litellm path raises if invoked.
**Depends on:** 024, 025
**Requirements:** PRV-03
**Parallelizable:** no

#### Phase 027: Model-profile resolver (quality/balanced/budget/inherit)
**Goal:** Per-Arc/Phase/Slice/Step override, inheritance chain, resolver used by `chat.params` hook.
**Depends on:** 024
**Requirements:** PRV-04
**Parallelizable:** yes

#### Phase 028: Cost accounting per request (event emission + aggregation)
**Goal:** Emit `state.provider.request`/`state.provider.response` with token/cost; aggregator reads events → per-scope rollup.
**Depends on:** 024, 004
**Requirements:** PRV-05
**Parallelizable:** yes

#### Phase 029: Thinking-budget tag propagation
**Goal:** `thinking.budget_tokens` flows through extended-thinking path; regression test with capture.
**Depends on:** 025
**Requirements:** PRV-08
**Parallelizable:** yes

#### Phase 030: Cache-control marker end-to-end preservation
**Goal:** `cache_control: ephemeral` markers preserved client → provider → response accounting; verifier.
**Depends on:** 025, 028
**Requirements:** PRV-09
**Parallelizable:** no (integration)

#### Phase 031: Provider parity matrix tests (available-provider scope)
**Goal:** Hypothesis-driven 10-prompt matrix across the **providers user has live credentials for**; normalized output snapshot diff. **Live coverage limited by available auth** — providers without local creds are deferred to a documented release-time smoke gate (mirrors v2 OAuth smoke pattern).

**In-scope (live, executed in CI):**
- Anthropic OAuth (stealth route via direct SDK)
- Anthropic API key (litellm route)
- Gemini CLI OAuth (free-tier; via litellm, normalized)
- Antigravity OAuth (free-tier; via litellm, normalized)

**Deferred to release-time smoke gate (recorded as tech debt at phase close):**
- GitHub Copilot device-code (requires Copilot subscription)
- Plain API-key providers (12): OpenAI, Gemini API-key, DeepSeek, Groq, Together, Anyscale, Mistral, Cohere, OpenRouter, Grok (xAI), Cerebras, plus any v3-era additions (Codex, GLM if added later) — each requires a paid key the user does not currently hold

**Test approach:**
- 10-prompt Hypothesis-driven matrix on the 4 in-scope providers (40 live calls per CI run; bounded cost on the 2 paid routes via `model_profile=budget`)
- Normalized output snapshot diff (structural, not byte-exact — providers differ on stop reasons, token counts, safety refusals)
- Per-provider golden header capture (mirrors v2 Phase 014's captured-header pattern) for the deferred providers, so contract-level regressions surface even without live calls

**Depends on:** 026, 027
**Requirements:** (verifier; PRV-01..09 — full coverage on in-scope providers; structural-only coverage on deferred providers)
**Parallelizable:** no (final)
**Tech debt at close:** "Phase 031 release-time smoke — 13 providers (Copilot + 12 plain API-key) require live credentials" (intentional; same shape as v2's manual OAuth smoke gates)

---

