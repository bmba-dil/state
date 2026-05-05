# v9 — Plugin TUI Bundle Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Opencode Plugin: TUI Bundle (A9)

- [x] **TUI-01**: SolidJS-based TUI extension matching opencode's catalog (solid-js 1.9.10, @opentui/{core,solid} 0.1.99)
- [x] **TUI-02**: Sidebar slot — build progress (current Step + Slice DAG mini-view) or teach concept state (current concept + mastery)
- [x] **TUI-03**: Statusline — current mode / current Step / provider / cost so far this session
- [x] **TUI-04**: Toast notifications for Slice completion, drill availability, gray-area decisions
- [x] **TUI-05**: Plugin install script auto-registers with opencode via `TuiPluginInstallOptions`
