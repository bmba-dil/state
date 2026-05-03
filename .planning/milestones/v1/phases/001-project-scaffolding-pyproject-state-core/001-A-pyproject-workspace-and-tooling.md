---
phase: 001
plan: A
type: auto
autonomous: true
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - .gitignore
  - .pre-commit-config.yaml
requirements: []  # foundational phase, no REQ-IDs assigned
---

<objective>
Create the project root scaffolding for `state`: `pyproject.toml` with full dependency list pinned per STACK.md, `uv` workspace configuration, development tooling config (ruff, mypy, pre-commit), and updated `.gitignore`. This plan establishes the build system so subsequent plans can create importable Python packages.
</objective>

<read_first>
  - /Users/tmac/Projects/state/.gitignore
  - /Users/tmac/Projects/state/.planning/research/STACK.md (lines 327–400 for pyproject layout + tooling)
  - /Users/tmac/Projects/state/CLAUDE.md
</read_first>

---

### Task 1: Create `pyproject.toml` with full dependency pins

<action>
Create `pyproject.toml` at project root with:

1. **[project]** section:
   - `name = "state"`
   - `version = "0.1.0"`
   - `requires-python = ">=3.12"`
   - `dependencies` list matching STACK.md lines 339–364 EXACTLY (every library + version floor verbatim):
     - `mcp>=1.27.0`
     - `litellm>=1.80.0`
     - `anthropic>=0.80.0`
     - `httpx>=0.28.1`
     - `pydantic>=2.13.2`
     - `pydantic-settings>=2.7`
     - `orjson>=3.11.8`
     - `aiosqlite>=0.22.1`
     - `filelock>=3.20.3`
     - `pluggy>=1.6.0`
     - `pygit2>=1.19.2`
     - `google-auth>=2.35`
     - `google-auth-oauthlib>=1.2`
     - `google-genai>=0.9`
     - `openai>=1.60`
     - `cryptography>=43.0`
     - `structlog>=25.1`
     - `rich>=13.9`
     - `typer>=0.15`

2. **[project.optional-dependencies]** section:
   - `dev` group containing:
     - Testing: `pytest>=8.4.0`, `pytest-asyncio>=1.3.0`, `pytest-cov>=6.0`, `hypothesis>=6.120`, `pytest-httpx>=0.35`, `pytest-mock>=3.14`, `freezegun>=1.5`, `pytest-xdist>=3.6`
     - Tooling: `ruff>=0.9.0`, `mypy>=1.14`, `pre-commit>=4.0`
   - `mcp` extras: `mcp[cli]>=1.27.0` (for `mcp dev` inspector)

3. **[build-system]** section:
   - `requires = ["uv_build>=0.5"]`
   - `build-backend = "uv_build"`

4. **[tool.ruff]** section (all config inline per STACK.md "no `.ruff.toml` scatter"):
   - `target-version = "py312"`
   - `line-length = 120`
   - Select rules: `["E", "F", "I", "N", "W", "UP", "B", "SIM", "ARG", "C4", "T20"]`
   - `[tool.ruff.lint.per-file-ignores]`: `"__init__.py" = ["F401"]`
   - `[tool.ruff.format]`: `quote-style = "double"`, `indent-style = "space"`

5. **[tool.mypy]** section:
   - `python_version = "3.12"`
   - `strict = true`
   - `warn_unused_ignores = true`
   - `explicit_package_bases = true`
   - `namespace_packages = true`

6. **[tool.pytest.ini_options]** section:
   - `asyncio_mode = "auto"`
   - `testpaths = ["tests"]`
   - `markers = ["e2e: marks tests as end-to-end (deselect with '-m \"not e2e\"')", "provider_parity: tests that run against live providers"]`

7. **[tool.coverage.run]** section:
   - `source = ["state_core", "state_build", "state_teach", "state_daemon", "state_worker", "state_cli"]`
</action>

<acceptance_criteria>
  - File `pyproject.toml` exists at project root.
  - Contains `name = "state"` and `version = "0.1.0"`.
  - Contains `requires-python = ">=3.12"`.
  - Contains `build-backend = "uv_build"`.
  - Contains every dependency from STACK.md lines 344–364 (19 libraries) with correct version floors.
  - Contains `[tool.ruff]` section with `target-version = "py312"`.
  - Contains `[tool.mypy]` section with `python_version = "3.12"`.
  - `grep -c "mcp>=" pyproject.toml` returns at least 1.
  - `grep -c "uv_build" pyproject.toml` returns at least 1.
</acceptance_criteria>

---

### Task 2: Update `.gitignore`

<action>
Append to existing `.gitignore` at project root:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
dist/
build/
*.egg
.venv/
.uv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store

# Testing
.coverage
htmlcov/
.pytest_cache/

# Type checking
.mypy_cache/
.ruff_cache/

# Project
.state/
```
</action>

<acceptance_criteria>
  - `.gitignore` contains `__pycache__/`, `.venv/`, `*.egg-info/`, `.state/`.
  - `.gitignore` does NOT contain `state-inputs/` or `.planning/` entries (those are existing managed lines to preserve).
  - `grep -c "__pycache__" .gitignore` returns at least 1.
</acceptance_criteria>

---

### Task 3: Create `.pre-commit-config.yaml`

<action>
Create `.pre-commit-config.yaml` at project root:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        additional_dependencies:
          - "pydantic>=2.13.2"
          - "types-requests"
        args: [--ignore-missing-imports]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: [--maxkb=500]
```
</action>

<acceptance_criteria>
  - File `.pre-commit-config.yaml` exists at project root.
  - Contains `ruff-pre-commit` with `v0.9.0`.
  - Contains `mirrors-mypy` with `v1.14.0`.
  - Contains `pre-commit-hooks` with `v5.0.0`.
  - Contains `check-toml` hook.
  - `grep -c "ruff-format" .pre-commit-config.yaml` returns at least 1.
  - `grep -c "check-toml" .pre-commit-config.yaml` returns at least 1.
</acceptance_criteria>

---

<verification>
1. `python3 -c "import tomllib; d = tomllib.load(open('pyproject.toml','rb')); print(d['project']['name'])"` prints `state`.
2. `python3 -c "import tomllib; d = tomllib.load(open('pyproject.toml','rb')); print(len(d['project']['dependencies']))"` prints `19` (all libraries counted).
3. `uv sync` succeeds without errors (installs all dependencies).
4. `ruff check --no-cache pyproject.toml` exits 0 (ruff reads config from pyproject.toml itself).
5. `pre-commit validate-config` exits 0 if pre-commit is installed.
</verification>

<must_haves>
- **pyproject.toml** with full dependency list, uv_build backend, ruff/mypy/pytest inline config
- **.gitignore** with Python, IDE, testing, and `.state/` entries
- **.pre-commit-config.yaml** with ruff, mypy, and standard hooks
- `uv sync` installable without errors
</must_haves>
