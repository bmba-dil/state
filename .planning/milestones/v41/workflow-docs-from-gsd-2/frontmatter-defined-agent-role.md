# Pattern: Frontmatter-Defined Agent Role

**Layer:** Skills & Agents (M2) — agent-discovery surface used by `subagent/index.ts:execute()`
**Source:** `gsd-2/src/resources/extensions/subagent/agents.ts:13-22` (`AgentConfig` interface); `subagent/agents.ts:63-111` (`loadAgentsFromDir`); `subagent/agents.ts:91-93` (the minimal validation gauntlet — `typeof === "string"`, no regex, no length cap); `subagent/agents.ts:137-156` (`discoverAgents` with scope precedence). Representative agent file: `gsd-2/src/resources/agents/scout.md`.
**Discovered in:** Phase 7 (SKILL-02)
**Related reference:** [`../agents/agent-roles.md`](../agents/agent-roles.md) §1 (Definition Format), §2 (Discovery & Scope Resolution); **sibling-pattern cross-link:** [`./frontmatter-first-skill-discovery.md`](./frontmatter-first-skill-discovery.md) (Phase 6) — same shape, divergent validation + opposite precedence (see schema-divergence callout below)

## What it does

Define agent personas as markdown files where YAML frontmatter is the role manifest (`name`, `description`, optional `tools`/`model`/`conflicts_with`) and the body is the system prompt. Discover them by walking a directory, parsing each `.md` file in place via the same `parseFrontmatter` helper used for skills, validating with a deliberately permissive gauntlet (`typeof === "string"` for the two required fields and nothing more), and merging via name-keyed `Map.set`. Scope resolution (`"user" | "project" | "both"`) determines which directory is walked first; on collision under scope=`"both"`, the agent loader applies **project-overrides-user** precedence — the opposite of skills, which are user-first dedup'd. The discovered `AgentConfig[]` flows into `subagent/index.ts:execute()` where the agent's body becomes the `--append-system-prompt` argument to a freshly spawned subagent process.

## Why it works that way

1. **Self-documenting.** The role definition IS the role behavior: frontmatter (manifest) + body (system prompt) live in one file. Reading the file tells you both what the agent IS (manifest) and what the agent DOES (body). No registration ceremony, no parallel config file, no cross-reference table.
2. **Hot-reloadable.** A directory walk on every dispatch picks up edits without restart. Authors iterate by editing `scout.md`, saving, and dispatching again — no rebuild, no reload, no daemon restart.
3. **Trivial composition.** Adding a new agent is dropping a `.md` file in `~/.gsd/agent/agents/` (user scope) or `<cwd>/.gsd/agents/` (project scope). Removing an agent is deleting the file. There is no class hierarchy, no decorator registration, no plugin manifest to update.
4. **Permissive validation by design.** The gauntlet at `subagent/agents.ts:91-93` only checks `typeof === "string"` for `name` and `description`. No regex, no length cap, no emptiness check. This is the **opposite** discipline from skills (`skills.ts:280-298` enforces `name ∈ /[a-z0-9-]/ ≤ 64 chars` and `description ≤ 1024 chars`). The reason: agents are user-supplied personas authored by humans iterating live; rejecting an agent because the description is 1025 chars long would be a hostile DX. The cost: pathological agent names (empty string, slashes, unicode) load successfully and may surface confusing errors downstream.
5. **Project-overrides-user precedence.** `discoverAgents` at `subagent/agents.ts:144-153` calls `Map.set` user-first then project-second, so project agents REPLACE user agents on name collision. Skills are the inverse (user-first dedup). The trade-off is intentional: agents are persona prompts that may legitimately be specialized per repository, so allowing project overrides matches the workflow. It also opens an attack surface — see schema-divergence callout below.
6. **Alternatives rejected:**
   - **Plugin-class system (one Python class per agent, registered via decorator):** ceremony with no benefit when the role is mostly a system prompt. The class-per-agent shape forces authors to think about object lifecycles, init order, and import paths — none of which a persona needs.
   - **Single config file (`agents.toml` listing all agents):** collision-prone (everyone editing the same file in a team), poor diffability, no per-agent file-history.
   - **Database-stored personas (Postgres/SQLite registry):** loses git history, loses diff-ability, loses the file-as-source-of-truth invariant.

### Schema-divergence callout (sibling-pattern)

> **Skills vs Agents — same shape, divergent rules.** Phase 6's [`frontmatter-first-skill-discovery.md`](./frontmatter-first-skill-discovery.md) is the same structural pattern (directory walk + frontmatter parse + dedup) but for *capabilities* rather than *roles*. The two loaders differ in three material ways:
>
> 1. **Validation strictness.** Skills enforce `name` regex `[a-z0-9-]` ≤ 64 chars and `description` non-empty ≤ 1024 chars (`skills.ts:280-298`). Agents only check `typeof === "string"` for both (`subagent/agents.ts:91-93`). Agents are materially more permissive.
> 2. **Precedence on collision.** Skills are user-first dedup'd (`skills.ts:401-417`); project skills are dropped if they collide. Agents are project-overrides-user (`subagent/agents.ts:144-153`); project agents REPLACE user agents.
> 3. **Manifest fields.** Agents add three optional fields skills don't have: `tools` (whitelist for the child's tool registry), `model` (per-agent model override), `conflicts_with` (phase-conflict guard, used only by `planner`).
>
> **Security implication of (2):** an untrusted project repo can ship `.gsd/agents/scout.md` that overrides the user's trusted `~/.gsd/agent/agents/scout.md`. The mitigation flag is `confirmProjectAgents: true` on the `subagent` tool (`subagent-index.ts:624-626`), but it defaults to `false` and is only consulted when `ctx.hasUI` is true. The pattern crystallizes the design choice: a role is a system prompt under a typed manifest, not a class.

## When to use it

- Persona-shaped logic where the persona is mostly a system prompt with a thin manifest of runtime knobs.
- User-extensible agent rosters where end-users add/remove agents without touching tool source.
- Rapid persona iteration where the feedback loop is "edit file → dispatch → observe → edit again".
- Project-specific personas that should override organization defaults (e.g., a repo-specific `reviewer.md` that knows the codebase's idioms).

## When NOT to use it

- Behaviorally complex agents requiring stateful initialization (DB connections, model warm-up, background workers) beyond what a CLI flag can express.
- Agents that need cross-file shared resources (multi-file system prompts with includes, shared knowledge bases) — frontmatter is flat metadata only.
- Systems requiring strict capability versioning (frontmatter has no version field; pin via lockfile if needed).
- High-stakes deployments where untrusted project repos must NOT be able to override user agents — set `confirmProjectAgents: true` or scope dispatches to `"user"` only.

## Implementation Sketch

```text
load_agents_from_dir(dir, source) -> AgentConfig[]:
  agents = []
  for md_file in dir.glob("*.md"):
    content = read(md_file)
    fm, body = parse_frontmatter(content)        # YAML head between --- markers
    if typeof(fm.name) != "string": continue     # the gauntlet — that's it
    if typeof(fm.description) != "string": continue
    agents.append(AgentConfig(
      name=fm.name,
      description=fm.description,
      tools=parse_tools(fm.tools),               # csv string or list → list[str] | None
      model=fm.model,
      conflicts_with=parse_conflicts(fm.conflicts_with),
      system_prompt=body,
      source=source,                             # "user" | "project"
      file_path=md_file.absolute(),
    ))
  return agents

discover_agents(cwd, scope) -> AgentDiscoveryResult:
  user_dir   = home() / ".gsd" / "agent" / "agents"
  project_dir = cwd / ".gsd" / "agents"          # or legacy cwd/.pi/agents
  by_name = {}                                   # Map<name, AgentConfig>
  if scope in ("user", "both"):
    for a in load_agents_from_dir(user_dir, "user"):
      by_name[a.name] = a
  if scope in ("project", "both"):
    for a in load_agents_from_dir(project_dir, "project"):
      by_name[a.name] = a                        # PROJECT OVERRIDES USER
  return AgentDiscoveryResult(agents=list(by_name.values()),
                              project_agents_dir=project_dir if exists(project_dir) else None)
```

## Python equivalent

```python
import os
import pathlib
from dataclasses import dataclass
from typing import Literal, Optional

import frontmatter  # python-frontmatter: pip install python-frontmatter


AgentScope = Literal["user", "project", "both"]


@dataclass
class AgentConfig:
    name: str
    description: str
    system_prompt: str
    source: Literal["user", "project"]
    file_path: pathlib.Path
    tools: Optional[list[str]] = None
    model: Optional[str] = None
    conflicts_with: Optional[list[str]] = None


def _parse_tools(raw) -> Optional[list[str]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(x) for x in raw if isinstance(x, str)]
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return None


def _parse_conflicts(raw) -> Optional[list[str]]:
    return _parse_tools(raw)  # same shape


def load_agents_from_dir(dir_path: pathlib.Path,
                         source: Literal["user", "project"]) -> list[AgentConfig]:
    """Mirror of loadAgentsFromDir at subagent/agents.ts:63."""
    if not dir_path.is_dir():
        return []
    out: list[AgentConfig] = []
    for md in sorted(dir_path.glob("*.md")):
        try:
            post = frontmatter.load(str(md))
        except Exception:
            # Malformed YAML — skip silently (same posture as the TypeScript loader)
            continue
        # The minimal validation gauntlet (subagent/agents.ts:91-93):
        # typeof === "string" for name and description. That's it.
        name = post.metadata.get("name")
        desc = post.metadata.get("description")
        if not isinstance(name, str) or not isinstance(desc, str):
            continue
        out.append(AgentConfig(
            name=name,
            description=desc,
            system_prompt=post.content,
            source=source,
            file_path=md.resolve(),
            tools=_parse_tools(post.metadata.get("tools")),
            model=post.metadata.get("model") if isinstance(post.metadata.get("model"), str) else None,
            conflicts_with=_parse_conflicts(post.metadata.get("conflicts_with")),
        ))
    return out


@dataclass
class AgentDiscoveryResult:
    agents: list[AgentConfig]
    project_agents_dir: Optional[pathlib.Path]


def discover_agents(cwd: pathlib.Path, scope: AgentScope = "both") -> AgentDiscoveryResult:
    """Mirror of discoverAgents at subagent/agents.ts:137."""
    user_dir = pathlib.Path.home() / ".gsd" / "agent" / "agents"
    project_dir = cwd / ".gsd" / "agents"
    by_name: dict[str, AgentConfig] = {}
    if scope in ("user", "both"):
        for a in load_agents_from_dir(user_dir, "user"):
            by_name[a.name] = a
    if scope in ("project", "both"):
        # PROJECT OVERRIDES USER — opposite of skills (skills.ts:401-417 is user-first dedup)
        for a in load_agents_from_dir(project_dir, "project"):
            by_name[a.name] = a
    return AgentDiscoveryResult(
        agents=list(by_name.values()),
        project_agents_dir=project_dir if project_dir.is_dir() else None,
    )
```

Key Python constructs:

- `python-frontmatter` — parses the YAML head; same role as `parseFrontmatter` imported from `@gsd/pi-coding-agent` in `subagent/agents.ts:1-2`.
- `dict[str, AgentConfig]` keyed by name with `.set(...)` semantics — direct equivalent of `Map<string, AgentConfig>` at `subagent/agents.ts:139`.
- The two-phase loop (user, then project) with `by_name[a.name] = a` enforces the project-overrides-user invariant.
- `sorted(dir_path.glob("*.md"))` — deterministic discovery order, same as a Node `readdirSync` followed by `sort()`.
