# Opencode Integration Analysis

A conversation analyzing how to move from Claude Code + API-switching hacks to opencode as a multi-provider CLI, with full GSD/AOL tooling ported.

---

## Q1: Analyze the repo and tell me how to best use opencode vs the old apiswitch files, and how to use other CLIs like Qwen or Gemini.

### What the old `apiswitch` files did

Claude Code only speaks the Anthropic API. The old approach (from `HOW-API-SWITCHING-WORKS.md` + `execution.md`) exploited that by pointing Claude Code at an **Anthropic-compatible proxy** using env vars in `.claude/settings.local.json`:

```json
"env": {
  "ANTHROPIC_AUTH_TOKEN": "<glm-key>",
  "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
  "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.7",
  "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
  "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.7"
}
```

Switching = inject those 5 keys. Switching back = delete them. Everything else (Python CLI, YAML configs, model allocator) was scaffolding. **Limitation:** it only works for providers that ship an Anthropic-compatible endpoint (GLM/z.ai does, OpenAI/Gemini don't natively).

### How opencode does it (fundamentally different)

opencode is **provider-agnostic by design** — not a hack. `packages/opencode/src/provider/schema.ts:10-26` ships well-known IDs for `anthropic`, `openai`, `google`, `google-vertex`, `github-copilot`, `amazon-bedrock`, `azure`, `openrouter`, `mistral`, etc. Each provider has its own SDK adapter under `src/provider/sdk/`, so it speaks each API natively — no proxy trickery.

Auth lives in `~/.local/share/opencode/auth.json` (chmod 600, see `src/auth/index.ts:9,79`) and stores per-provider credentials as `{type: "api" | "oauth" | "wellknown", ...}`. The CLI commands are:

- `opencode auth login` (alias of `providers login`) — picks a provider, prompts for key or runs OAuth flow (`src/cli/cmd/providers.ts:273`)
- `opencode auth list` — shows all configured providers + any `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` env vars being picked up (line 222)
- `opencode auth logout` — removes credentials (line 482)
- `opencode models [provider]` — lists available models

Provider config (base URL, custom endpoints, model overrides) goes in `opencode.json` under `provider.<id>.options.baseURL` / `apiKey` (`src/config/provider.ts:82-107`). This is the clean equivalent of the old env-var hack — if you want to route `anthropic` through z.ai, you set `baseURL` in config rather than mutating Claude Code's settings.

**Switching providers at runtime** = pick a different model in the TUI (Ctrl-X M by default) or set `model: "provider/model-id"` in `opencode.json`. No file surgery, no restart dance.

### Recommendation

**For Claude Code specifically** (if you still want to use it): keep the old env-var approach. It's the only way, because Claude Code refuses to speak anything but Anthropic's protocol. The ~5 shell scripts described in `execution.md` are the right minimal implementation — skip the Python/MoAI baggage.

**For everything else: stop API-switching, start CLI-switching.** Use opencode as your multi-provider CLI. One tool, native support for Anthropic + OpenAI + Google (Gemini) + OpenRouter + local models. `opencode auth login` per provider, then pick the model. Strictly better than proxying Anthropic-shaped traffic to a non-Anthropic backend.

**For Qwen / Gemini / other CLIs**, three tiers in order of preference:

1. **Just use opencode** — it already supports Gemini (`google` provider) and anything OpenRouter proxies (which includes Qwen).
2. **Use each vendor's own CLI** — `gemini-cli` (Google), Qwen's official CLI (`qwen-code`), `codex` (OpenAI). These speak their native APIs and don't need switching logic.
3. **Anthropic-proxy route** (only if locked to Claude Code) — only viable for providers that expose an Anthropic-compatible endpoint: z.ai (GLM), some OpenRouter configs, LiteLLM running locally.

---

## Q2: So what is the value of opencode when users could just use the vendor CLIs?

The honest answer is **the value is in not having to context-switch between four different CLIs**, plus a few structural wins.

**One UX, one config, one session.** Vendor CLIs each have their own keybinds, agent model, tool set, permissions system, and session format. With opencode you learn the TUI once and swap the model underneath. Your `opencode.json`, custom agents, MCP servers, and skills work with any backend. With vendor CLIs, setting up MCP or agents in Claude Code doesn't carry over to gemini-cli or qwen-code.

**Mid-task model switching.** Ctrl-X M swaps models within the same session/context — "use Sonnet to plan, switch to Qwen to execute the cheap grep-heavy parts, switch to Gemini for the 1M-token file." Vendor CLIs can't do this; you'd restart in a different tool and lose the conversation.

**Provider-agnostic auth store.** One `auth.json`, one `auth login` flow, OAuth + API key + plugin-provided auth all handled uniformly. Vendor CLIs each reinvent this.

**Client/server split.** opencode's backend runs headless; the TUI is just one client. There's a desktop app, mobile-driven remote sessions, a web UI. Vendor CLIs are monolithic terminal apps.

**Open source, not coupled.** If Anthropic changes pricing or Google deprecates a model, you flip a config line. No migration.

**Where vendor CLIs actually win:**
- **Claude Code** has the deepest Anthropic-specific features — subagents, skills ecosystem, hooks, the 1M-context Sonnet/Opus tuning, and tools built against Anthropic's exact quirks. It will always be slightly ahead for Claude models specifically.
- **gemini-cli** gets first-party access to Google-specific features (long context caching semantics, Vertex-specific auth, grounding).
- **codex** ships OpenAI-specific features first.
- Vendor CLIs get new model support the day of release; opencode lags by hours/days.

**Honest take:** if you're 95% on one provider, use that vendor's CLI — you'll get the best integration. If you genuinely hop between providers (cost, capability, availability), opencode earns its keep.

---

## Q3: What agents does opencode use? How do skills, subagents, and workflow markdown files correlate across CLIs? Do I have to re-tool for every CLI?

### The honest portability situation

Skills, subagents, commands, and workflow markdown files are mostly CLI-specific formats. They look similar (markdown + YAML frontmatter) but each CLI scans different directories with different schemas.

| Artifact | Claude Code | opencode | Gemini CLI | Qwen Code |
|---|---|---|---|---|
| Memory file | `CLAUDE.md` | `AGENTS.md` | `GEMINI.md` | `QWEN.md` |
| Skills | `.claude/skills/*/SKILL.md` | reads `.claude/skills/` **and** `.opencode/skill(s)/` **and** `.agents/skills/` | none | none |
| Subagents | `.claude/agents/*.md` (frontmatter) | defined in `opencode.json` under `agent.*` | its own extension format | its own |
| Slash commands | `.claude/commands/*.md` | defined in `opencode.json` under `command.*` | TOML-based extensions | similar to Gemini |
| Hooks | `.claude/settings.json hooks` | plugin system | extensions | extensions |

### What opencode actually does (the real news)

From `src/skill/index.ts:21`:
```ts
const EXTERNAL_DIRS = [".claude", ".agents"]
```

opencode **explicitly scans `~/.claude/skills/` and walks up from cwd looking for `.claude/skills/`**, parses the same `SKILL.md` frontmatter Claude Code uses, and `src/command/index.ts:148-159` auto-promotes every discovered skill into a slash command. So **your Claude Code skills work in opencode with zero changes**.

What doesn't port automatically:
- `.claude/agents/*.md` subagents — opencode ignores these. Its agents live in `opencode.json` as `{name, prompt, model, permission, mode: "subagent"|"primary"}`.
- `.claude/commands/*.md` — also ignored. But since opencode turns skills into commands, if your "command" is really just a prompt template, move it to `.claude/skills/<name>/SKILL.md` and it works in both.
- Claude Code hooks — opencode has a plugin system instead; not a drop-in port.
- `CLAUDE.md` — opencode reads `AGENTS.md`. Symlinking one to the other works today.

### What happens when you switch model mid-session in opencode

Your agents, skills, commands, permissions, MCP servers, and `AGENTS.md` are **all loaded per-session, independent of the active model** (see `agent/agent.ts` — agent config is resolved before a model is even picked; the model is just a field on the agent). So Ctrl-X M swaps Qwen → Claude → Gemini underneath without reloading any of your tooling. The only thing that changes is which API the tokens go to.

### Recommendation

1. **Keep everything in `.claude/skills/` and `AGENTS.md`** (symlink from `CLAUDE.md`). Least-common-denominator format.
2. **Port your `.claude/agents/*.md` subagents into `opencode.json`** one time. You get opencode's multi-provider routing on top of your existing subagent lineup.
3. **Use Claude Code** when you want Claude specifically and want first-party feature depth.
4. **Use opencode** when you want Qwen or Gemini (or any other) backing your existing skills/agents.
5. **Skip gemini-cli and qwen-code as separate daily drivers** unless you need a vendor-specific feature.

---

## Q4: Look at my ~/.claude folder — agents, skills, agent-of-learning, get-shit-done. How does it all integrate into opencode?

### What you actually have

| Layer | Count | Lines | Portable to opencode? |
|---|---|---|---|
| Subagents (`~/.claude/agents/`) | 36 | 15,488 | Partial — need translation |
| Skills (`~/.claude/skills/`) | ~65 | 3,221 + refs | **Yes, natively** |
| Slash commands (`~/.claude/commands/` + subfolders) | ~150 | 10,027 | Partial — rewrite as skills |
| Hooks (`~/.claude/hooks/`) | 20 scripts wired via 4 lifecycle events | — | **No** — incompatible lifecycle |
| GSD runtime (`get-shit-done/bin/lib/*.cjs`) | 20+ modules, MCP server, state machine | — | **No** — Claude-Code coupled |
| AOL runtime (`agent-of-learning/`) | workflows, personalities, learners state | — | **No** — assumes `aol` binary + Claude lifecycle |

The GSD executor agent alone calls `Task` 19 times. Agents reference `TodoWrite`, `AskUserQuestion`, `mcp__context7`. Commands use `@~/.claude/...` import syntax. Hooks fire on Claude-Code-specific events (`SessionStart`, `PostToolUse`).

### What opencode reads from your existing setup today

From `opencode/packages/opencode/src/skill/index.ts:21`, opencode scans:
- `~/.claude/skills/**/SKILL.md` ✓
- `.claude/skills/**/SKILL.md` walking up from cwd ✓
- `~/.agents/skills/**` and project `.agents/skills/**` ✓

And `src/command/index.ts:148-159` auto-promotes every discovered skill into a slash command.

### Integration plan ranked by ROI

**Tier 1 — Zero effort, already works.**
Skills like `api-design`, `beautiful-commits`, `code-review`, `decision-framework`, `typescript-patterns`, `env-setup`, `test-generator`, `file-operation-patterns`, `debug-like-expert`, `python-*`, `react-best-practices`, `frontend-design`, `context-handoff`, `session-awareness`. **~40 of your 65 skills fit here.**

**Tier 2 — Port mechanically (half-day of work).**
The ~15 generic subagents that don't assume GSD/AOL runtime: `codebase-navigator`, `doc-linter`, `changelog-generator`, `observer`. For each:
```json
{
  "agent": {
    "codebase-navigator": {
      "mode": "subagent",
      "description": "…",
      "prompt": "…",
      "permission": { "edit": "deny", "write": "deny" },
      "model": "anthropic/claude-sonnet-4-6"
    }
  }
}
```

**Tier 3 — Rewrite commands as skills.**
~60 of your 150 commands are prompt templates with `$ARGUMENTS` (everything under `commands/research/`, `commands/consider/`, etc.). Convert to `~/.claude/skills/<name>/SKILL.md` and they work as slash commands in opencode **and** as skills in Claude Code.

**Tier 4 — Port GSD/AOL as plugins.** (see Q5)

---

## Q5: CAN opencode do the same things as Claude Code, IF I transform GSD and AOL to use it? Does it have hooks, triggers, injections, and the ability to fire state machines through local MCPs?

### GSD/AOL requirements → opencode equivalents

| Claude Code mechanism you use | opencode equivalent | Notes |
|---|---|---|
| `SessionStart` hook | `experimental.chat.system.transform` + subscribe to bus `session.*` events via `event` hook | Direct match |
| `UserPromptSubmit` hook | `chat.message(input, output)` — mutate message + parts | Direct match |
| `PreToolUse` hook | `tool.execute.before(input, output)` | Direct match, better-typed |
| `PostToolUse` hook | `tool.execute.after(input, output)` — with tool, sessionID, callID, args, output, metadata | Direct match |
| `Stop` hook | Subscribe to bus events via `event(input: { event })` | Equivalent |
| System-prompt manipulation | `experimental.chat.system.transform` → `{system: string[]}` | Cleaner |
| Status line | TUI plugin surface (`packages/plugin/src/tui.ts`, 501 lines) | Match |
| `@~/.claude/...` imports | Not supported — read files explicitly in plugin | Port needed |
| Custom tools | `Hooks.tool: { [id]: ToolDefinition }` with Zod args, `context.ask()` for runtime permissions | **Better** — typed |
| MCP servers (stdio/HTTP/SSE) | Full MCP client support — configured in `opencode.json` under `mcp.*` | Direct match |
| Custom slash commands with `$ARGUMENTS`, `$1..$N` | `command.*` in opencode.json — same syntax | Direct match |
| Skills | Native — reads `~/.claude/skills/**/SKILL.md` and auto-exposes as commands | **Strict superset** |
| Subagent definitions | Agents in opencode.json with `mode: "subagent"`, own `prompt`, `model`, `permission` ruleset | Direct match |
| Per-subagent `tools:` restriction | Permission ruleset per agent (`allow/ask/deny` per tool, glob patterns) | **Better** |
| `TodoWrite` | Built-in todo tool + event bus | Match |
| Model profile resolution | Per-agent `model` + `chat.params(input, output)` hook for per-call overrides | Match |

### Things that aren't built in but are trivially buildable

**1. `Task(subagent_type, prompt)` programmatic subagent spawning.**
In Claude Code, `gsd-orchestrator` tool-calls `Task` to spawn `gsd-executor`. In opencode, subagents are user-invoked via `@agent-name`. No built-in tool for programmatic spawning from within a running agent. **But** plugin API gives you `client: createOpencodeClient(...)` — full opencode HTTP/RPC client. Write a tiny custom tool `gsd.spawn(agentName, prompt)` whose `execute` calls `client.session.create()` and `client.session.chat()` with the target agent. ~30 lines. Register in `Hooks.tool`.

**2. `AskUserQuestion` structured multi-choice prompts.**
`context.ask()` inside a custom tool issues a permission-style prompt. TUI plugin surface supports custom UI. Write once.

**3. Hook lifecycle name translation.**
A ~150-line adapter translates Claude-style hook scripts (JSON on stdin, JSON on stdout) into opencode hook callbacks. Keep existing `~/.claude/hooks/*.js` unchanged and shell out to them. **Biggest lift-saver** — don't rewrite 20 hook scripts, wrap them.

### Things opencode has that Claude Code doesn't

- **Client/server split.** Headless server, plugins run server-side, TUI is just a client. GSD's current MCP server model maps natively.
- **Typed event bus with pub/sub.** `Bus.publish` / `subscribe` / `subscribeAll` with Zod-typed event definitions. GSD state machine transitions become `gsd.phase.started`, `gsd.plan.completed`, etc.
- **`chat.params` / `chat.headers` / `tool.definition` / `experimental.chat.messages.transform` / `experimental.session.compacting`.** Claude Code doesn't expose these. GSD's model-profile resolver, context budget manager, and compaction rules become plugin hooks.
- **`permission.ask` hook.** Intercept every permission prompt globally.
- **Custom auth providers** (plugin `auth` hook). GSD could register itself as an auth provider for API-key rotation.

### Real port cost for GSD + AOL

| Component | Effort |
|---|---|
| Skills (cross-compatible) | 0 |
| Subagent frontmatter → `opencode.json` | 1–2 days (mechanical) |
| Slash commands → skills or commands | 1–2 days (scriptable) |
| Hook scripts → plugin hooks (wrap, don't rewrite) | 2–3 days |
| `gsd-tools.cjs` MCP server | ~0 (register in opencode.json) |
| `Task`-equivalent custom tool | ~1 day |
| Model profile resolver | 1 day |
| Correction-capture, skill-load-tracker | ~1 day each |
| AOL `aol` binary integration | 1 day |
| Statusline | 1 day |
| Testing | week+ |

**Total: ~3–4 weeks of focused work** for a first-class port. Resulting plugin runs GSD/AOL against any provider opencode supports.

### Staged recommendation

- **Phase 1 (week 1):** Skills + generic agents. Port 40 clean skills (free) + 15 generic subagents.
- **Phase 2 (week 2):** GSD as opencode plugin. Focus on `Task`-spawn custom tool, MCP server registration, hook-script adapter, core agents.
- **Phase 3 (week 3):** AOL plugin + advanced hooks. Port AOL, add `chat.params` model resolver, compaction hooks.
- **Phase 4 (week 4):** Harden. Fix edge cases, verify against multiple providers, delete Claude-Code-only fallback path.

Architecture supports everything. It's a real port, not a rewrite — end state gives you GSD+AOL on Qwen, Gemini, and Claude interchangeably, with a cleaner hook system than you have now.
