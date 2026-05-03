# v11 — Mode Enforcement (6 Layers) Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Mode Enforcement (A11)

- [ ] **MODE-01**: `.state/mode.json` declares `mode: build|teach|both` with schema validation
- [ ] **MODE-02**: Directory presence (`.state/build/` vs `.state/teach/`) is physical signal; writes to the wrong subtree are rejected at the daemon
- [ ] **MODE-03**: MCP server registration — `state-build` only started when mode in `{build, both}`; `state-teach` only when `{teach, both}`
- [ ] **MODE-04**: Plugin hook mode gate — `command.execute.before` rejects `/state:build:*` when mode is teach, etc.
- [ ] **MODE-05**: Daemon HTTP middleware (canonical gate) — every request carries `mode` header, validated against `mode.json`
- [ ] **MODE-06**: Python import-graph lint — CI test fails if `state.build.*` imports `state.teach.*` or vice versa
- [ ] **MODE-07**: `state mode init build|teach|both` CLI bootstraps the correct `.state/` subtree
