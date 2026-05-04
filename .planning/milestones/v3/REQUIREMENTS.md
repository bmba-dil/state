# v3 — Provider Routing + Model Profiles Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Kernel: Provider Routing (A3)

- [ ] **PRV-01**: litellm >= 1.80.0 as default provider abstraction for non-stealth traffic
- [ ] **PRV-02**: Direct Anthropic SDK escape hatch for extended thinking and fine-grained cache-control breakpoints
- [ ] **PRV-03**: OAuth stealth flow NEVER routes through litellm (bypass guard in provider selector)
- [x] **PRV-04**: Model profiles (`quality` / `balanced` / `budget` / `inherit`) configurable per-Arc, per-Phase, or globally
- [x] **PRV-05**: Cost accounting per request, aggregated per Step / Slice / Phase / Arc in SQLite
- [ ] **PRV-06**: Shared httpx client across daemon with connection pooling
- [ ] **PRV-07**: Streaming tokens flow through `chat.params` / `chat.headers` hook without mutation loss
- [x] **PRV-08**: Thinking-budget tag propagation (`thinking.budget_tokens`) for Anthropic extended thinking
- [ ] **PRV-09**: Cache-control marker preservation end-to-end (client → provider → response accounting)
