# Pattern: Frontmatter-First Skill Discovery

**Layer:** Skills & Agents (M2) — used by `skills.ts` to discover bundled, user, and project skills
**Source:** `gsd-2/packages/pi-coding-agent/src/core/skills.ts:172` (`loadSkillsFromDirInternal`); `skills.ts:260-298` (per-file parse + validate — `parseFrontmatter`, `validateName`, `validateDescription`); `skills.ts:380-440` (collision dedup, `realpathSync` symlink dedup)
**Discovered in:** Phase 6 (SKILL-01)
**Related reference:** `kb/skills/skill-system.md` §1 (loader internals — landed in Wave 2)

## What it does

Walk a directory tree looking for `<unit>/SKILL.md` index files (or equivalent manifest file at each plugin unit's root), parse the YAML frontmatter block at the head of each file, validate the parsed fields against a spec (`name` ≤ 64 chars matching `[a-z0-9-]`, `description` ≤ 1024 chars non-empty), and build a keyed map from validated name to skill object. Dedup at two levels: by name (first-wins when two skills declare the same name, later one is dropped with a diagnostic) and by realpath (symlinks to the same on-disk unit are counted once, preventing double-loading when users symlink personal skills into multiple search directories). The result is a flat `Map<name, Skill>` ready for consumption by the trigger table, the system prompt renderer, and the explicit `Skill`-tool invocation path.

## Why it works that way

1. **Plugin systems must discover capabilities without a central registry.** Frontmatter embedded in each capability's own file is the lowest-friction registration mechanism that exists: no build step, no explicit import list, no re-run of a code-generation pass. Each skill is fully self-describing at its filesystem location. This mirrors the approach taken by Sphinx (`conf.py` per extension), Hexo (YAML front matter per post), Hugo (toml/yaml/json at file head), and MkDocs (`mkdocs.yml` plugin declarations). The pattern is the ecosystem's convergent answer to the problem of registering authoring-time content without central bookkeeping.

2. **Validation must be cheap and at-discovery time, not at-use time.** Invalid frontmatter (malformed YAML, name too long, description missing) is dropped with a diagnostic at load, not at the moment the LLM tries to invoke the skill. Early rejection with a clear diagnostic ("invalid name: 'My Skill' — must match [a-z0-9-]") lets skill authors debug during development, not at runtime inside an agent session. A single broken SKILL.md should not prevent the other 34 bundled skills from loading — the loader is deliberately permissive-by-default, dropping invalid entries rather than aborting.

3. **Symlink dedup matters because users legitimately symlink skills across tool namespaces.** GSD-2 searches both `~/.agents/skills/` (the Agent Skills standard path) and `~/.claude/skills/` (Claude Code's path). A user who installs a skill once via `npx skills add` but symlinks it from their dotfiles into both paths will see the same SKILL.md file at two different `filePath` values. Without `realpathSync` dedup, the loader produces two `Skill` entries with different `filePath` fields but identical `name`, causing the trigger table to render duplicate rows and the system prompt to grow unnecessarily. The fix is: after name-based collision dedup, also dedup by realpath (call `fs.realpathSync(filePath)` on each, track seen realpaths in a `Set`, drop duplicates silently).

4. **Name-based collision is first-wins, not error-on-conflict.** Users may install a community skill that shares a name with a bundled skill. A hard error would break every session until the user notices and removes one. First-wins gives the bundled skill (loaded first, from the standard search order) priority, degrades gracefully for the user, and emits a diagnostic they can act on at their leisure.

Alternatives rejected:
- **Central registry (an explicit registration file or code-gen step):** Requires skill authors to edit a second artifact every time they add a skill. The markdown file IS the registration. Double-bookkeeping breaks when the two sources drift.
- **JSON manifest per skill directory (`manifest.json` alongside SKILL.md):** Forces double-bookkeeping: the manifest and the SKILL.md prose both describe the same capability. The YAML frontmatter block at the head of the prose document is the minimal-duplication choice.
- **SHA-keyed store where identity is the content hash:** Overkill for hand-authored markdown. Skill names are the stable identity — authors pick them and embed them in system prompt instructions. Renaming by hash would require updating every reference.
- **Recursive glob for any `*.md` file:** Too broad. Scoping discovery to `<unit>/SKILL.md` (or whichever index filename the spec defines) prevents partial reads of multi-file skill packages (e.g., skills with reference subdirectories).

## Variations

- **Index filename:** `SKILL.md` is the Agent Skills standard; other systems use `index.md`, `plugin.json`, `pyproject.toml [tool.plugin]`. The pattern works with any fixed filename — change the glob target only.
- **Ignore-rule respect:** The gsd implementation honours `.gitignore`, `.ignore`, and `.fdignore` files via the `ignore` npm package, so users can exclude skill-like directories from discovery without deleting them. Python ports can use `pathspec` for the same effect.
- **Collision strategy:** gsd uses first-wins with a warning diagnostic. Stricter systems may prefer hard-fail on any collision (useful for deterministic CI environments where duplicate names are bugs). The collision strategy is a policy knob, not a structural constraint of the pattern.
- **Search-directory priority order:** gsd searches `~/.agents/skills/`, then `<cwd>/.agents/skills/`, then `~/.gsd/agent/skills/` (legacy). Priority order determines which skill wins on collision. Document it explicitly — the order is load-bearing for users who intentionally shadow bundled skills with local overrides.
- **Windows symlink caveat:** `fs.realpathSync` has known quirks on Windows network paths and junctions. The gsd implementation falls back at `resource-loader.ts:265` (`copyDirRecursive`) for Windows path failures. A Python port on Windows should catch `OSError` from `os.path.realpath` and fall back to path-string comparison.
- **`disable-model-invocation` flag:** Some skills (e.g., the GSD orchestrator skill itself) set `disable-model-invocation: true` in frontmatter to opt out of automatic listing in `formatSkillsForPrompt`. The loader reads this field (`skills.ts:292`) but the discovery walk itself is unaffected — all skills are discovered; the flag only controls downstream rendering.

## Python equivalent

```python
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import frontmatter  # python-frontmatter: pip install python-frontmatter


NAME_MAX_LEN = 64
NAME_PATTERN = re.compile(r'^[a-z0-9-]+$')
DESC_MAX_LEN = 1024


@dataclass
class Skill:
    name: str
    description: str
    file_path: Path
    base_dir: Path
    disable_model_invocation: bool = False


def _validate_name(name: str) -> Optional[str]:
    """Returns error message or None if valid. Mirror of validateName at skills.ts:260."""
    if not name or len(name) > NAME_MAX_LEN:
        return f"name must be 1–{NAME_MAX_LEN} chars"
    if not NAME_PATTERN.match(name):
        return "name must match [a-z0-9-]"
    return None


def _validate_description(desc: str) -> Optional[str]:
    """Mirror of validateDescription at skills.ts:275."""
    if not desc or not desc.strip():
        return "description must be non-empty"
    if len(desc) > DESC_MAX_LEN:
        return f"description must be ≤ {DESC_MAX_LEN} chars"
    return None


def load_skills_from_dir(
    search_dir: Path,
    *,
    index_filename: str = "SKILL.md",
) -> dict[str, Skill]:
    """
    Walk search_dir for <unit>/SKILL.md files.
    Mirror of loadSkillsFromDirInternal at skills.ts:172.
    Returns: Map<name, Skill> (first-wins on collision; symlink-deduped).
    """
    skills: dict[str, Skill] = {}
    seen_realpaths: set[str] = set()

    if not search_dir.is_dir():
        return skills

    # Walk one level: each immediate subdirectory is a potential skill unit
    for unit_dir in sorted(search_dir.iterdir()):
        if not unit_dir.is_dir():
            continue
        skill_file = unit_dir / index_filename
        if not skill_file.is_file():
            continue

        # Symlink dedup via realpath (mirror of realpathSync dedup at skills.ts:380)
        try:
            real = os.path.realpath(skill_file)
        except OSError:
            real = str(skill_file)  # Windows fallback: compare path string
        if real in seen_realpaths:
            continue
        seen_realpaths.add(real)

        # Parse YAML frontmatter (mirror of parseFrontmatter at skills.ts:260)
        try:
            post = frontmatter.load(str(skill_file))
        except Exception as e:
            print(f"[skill-loader] skipping {skill_file}: parse error: {e}")
            continue

        name = post.metadata.get("name", "")
        description = post.metadata.get("description", "")
        disable = bool(post.metadata.get("disable-model-invocation", False))

        # Validate (mirror of validateName + validateDescription at skills.ts:260-298)
        err = _validate_name(name)
        if err:
            print(f"[skill-loader] skipping {skill_file}: invalid name ({err})")
            continue
        err = _validate_description(description)
        if err:
            print(f"[skill-loader] skipping {skill_file}: invalid description ({err})")
            continue

        # Name-collision dedup: first-wins (mirror of collision handling at skills.ts:380-440)
        if name in skills:
            print(f"[skill-loader] collision: '{name}' already loaded from "
                  f"{skills[name].file_path}; skipping {skill_file}")
            continue

        skills[name] = Skill(
            name=name,
            description=description,
            file_path=skill_file,
            base_dir=unit_dir,
            disable_model_invocation=disable,
        )

    return skills


def load_skills(
    search_dirs: list[Path],
    *,
    index_filename: str = "SKILL.md",
) -> dict[str, Skill]:
    """
    Load skills from multiple search dirs in priority order.
    First dir's skills win on name collision across dirs.
    """
    all_skills: dict[str, Skill] = {}
    for d in search_dirs:
        for name, skill in load_skills_from_dir(d, index_filename=index_filename).items():
            if name not in all_skills:
                all_skills[name] = skill
    return all_skills
```

Key Python constructs:
- `python-frontmatter` (or `pyyaml` directly against the `---`-delimited head) — parses YAML frontmatter at the top of each markdown file; direct equivalent of `parseFrontmatter` in `skills.ts:260`.
- `os.path.realpath` — resolves symlinks to canonical paths; equivalent of Node's `fs.realpathSync`. Wrapped in `try/except OSError` for Windows junction/network-path failures.
- `dict[str, Skill]` keyed by name — first-wins collision semantics: once a name is in the dict, later loads skip it.
- `sorted(search_dir.iterdir())` — deterministic discovery order regardless of filesystem ordering; prevents non-reproducible collision winners across OS runs.

## When to use it

- Plugin systems where capabilities are content-authored (markdown, MDX, TOML, YAML) rather than code-registered.
- Systems where users self-publish capabilities via the filesystem — zero-friction installation (drop a directory, restart the tool).
- CLI tools that auto-discover at launch from well-known directories (`~/.config/tool/plugins/`, `.tool/plugins/` at project root).
- Any system following the Agent Skills standard (`SKILL.md` with YAML frontmatter as the capability manifest).
- Situations where capability authorship is decoupled from the tool's release cycle (users write skills; the tool ships a loader; they never need to sync).

## When NOT to use it

- **Hot-loaded plugins in production servers** — walking a filesystem directory and parsing YAML at request time is too slow. Use a capability registry with versioning and in-memory lookups instead.
- **Dependency resolution between plugins** — frontmatter is flat metadata only. If plugins must declare dependencies on each other, a frontmatter-first loader cannot satisfy or validate those dependencies. Use a manifest-based registry (e.g., `package.json` + npm, `.csproj` project references) that supports dependency graphs.
- **Systems requiring strict capability versioning** — SKILL.md frontmatter has no version field in the Agent Skills standard. If consumers need to pin to a specific skill version, use a lockfile-based registry.
- **Windows environments where symlink semantics are unacceptable** — `fs.realpathSync` and `os.path.realpath` have known quirks on Windows (network paths, junctions, UNC paths). Test explicitly or fall back to path-string comparison if symlink dedup is not critical.
- **Capability counts above ~5000** — a full filesystem walk at every launch adds up. Above this scale, consider a persistent index (SQLite or similar) rebuilt only when the filesystem changes, rather than a fresh walk each time.

## Cross-references

- Reference doc: `kb/skills/skill-system.md` §1 (loader internals, load lifecycle end-to-end)
- Related pattern: `kb/patterns/content-fingerprint-resync-gate.md` — the gate that decides whether the bundled skills tree needs to be re-synced before discovery runs
- Related pattern: `kb/patterns/llm-mediated-trigger-table.md` — the trigger table that consumes discovered skill names to build the system prompt matching surface
- Forward ref: `kb/extensions/plugin-system.md` (Phase 8 / SKILL-03) — extension-defined skill registration, the parallel path where extensions register skills programmatically rather than via frontmatter discovery
