# v27 — Release & Packaging Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Release & Packaging (A27)

- [ ] **REL-01**: `pyproject.toml` with `uv_build` backend
- [ ] **REL-02**: `uvx state install` auto-registers plugin + MCP servers with opencode
- [ ] **REL-03**: Wheel includes opencode plugin TS source + bun build output
- [ ] **REL-04**: `state update` checks PyPI for newer version, prompts to upgrade
- [ ] **REL-05**: Remote skill registry — `state skills add <url>` fetches community skills
- [ ] **REL-06**: Release notes generated from commit history + phase artifacts
