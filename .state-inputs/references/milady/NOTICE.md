# Milady reference snapshot

Source: https://github.com/milady-ai/milady (MIT License)
PR: https://github.com/milady-ai/milady/pull/1910 — "deploy: systemd bare-metal + claude-code-stealth preload + eliza runtime fixes"
Snapshot SHA: `55665598132a15ae6a91a13d803919a2192137fd`
Captured: 2026-04-28

## Files

- `claude-code-stealth.mjs` — Bun preload module that intercepts `fetch` to `api.anthropic.com`,
  coerces `sk-ant-oat*` tokens to `Bearer`, injects Claude Code stealth headers + system prefix,
  adds `?beta=true`, defensively deletes `x-api-key`. The reference implementation that
  finalised our Phase 014 stealth surface (full `anthropic-beta` value, `(external, cli)`
  user-agent suffix, system-message-prefix injection).
- `milady-refresh-oauth.sh` — operational refresh pattern: 60-min proactive timer reading
  `~/.claude/.credentials.json`. NOT used by Phase 014 (which is provider-level, on-demand);
  informs the deferred daemon-level scheduler work.

## License

MIT — see https://github.com/milady-ai/milady/blob/develop/LICENSE
We do not redistribute or derive from the milady codebase; these snapshots exist only as
reference / audit artifacts for our independent reimplementation in Python.

## Usage

Read-only. Do not import / shell-out to these files. They are evidence of Claude Code
stealth surface as observed in 2026-04. Replace via the deferred traffic-capture phase
when one lands.
