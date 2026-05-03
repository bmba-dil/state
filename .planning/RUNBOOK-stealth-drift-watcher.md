# Runbook — Stealth-Drift Watcher (Phase 014)

**Phase:** v2.014 — Anthropic OAuth provider (stealth flow)
**Created:** 2026-04-29
**Owner:** local launchd job, user-scoped (no root, no daemon)

## What it does

Detects when the locally-installed Claude Code (`claude --version`) drifts from the
`_CLAUDE_CLI_VERSION` constant pinned in
`src/state_core/auth/providers/anthropic.py`. On drift, fires a macOS notification
with sound (Glass) prompting a fresh mitmproxy capture against the new Claude Code.

Source-of-truth is the constant in the source file — when the constant is updated
after a future capture, the watcher auto-syncs on the next run. No script edit
needed.

Silent in steady state; logs every check (drift or not) to a single line in
`~/Library/Logs/state-mitm-drift-check.log`.

## Files

| Path | Purpose |
|---|---|
| `~/.local/bin/state-mitm-drift-check.sh` | The check script — runs every Monday 10am via launchd |
| `~/Library/LaunchAgents/dev.state.mitm-drift-check.plist` | launchd job definition (Weekday=1 Hour=10) |
| `~/Library/Logs/state-mitm-drift-check.log` | One-line-per-run audit history |
| `~/Library/Logs/state-mitm-drift-check.launchd.{out,err}` | launchd-level stdout/stderr (only used if the script itself crashes) |

## Schedule

`StartCalendarInterval` Weekday=1 Hour=10 Minute=0 → every Monday at 10:00 local time.
If the Mac is asleep at the scheduled time, launchd fires on the next wake. Survives
reboots automatically (launchd reloads `~/Library/LaunchAgents/*` on login).

## Operational commands

```bash
# Inspect job state (last exit code, last fire time, env)
launchctl print gui/$(id -u)/dev.state.mitm-drift-check

# Confirm the job is registered
launchctl list | grep state.mitm

# Run the check manually right now
~/.local/bin/state-mitm-drift-check.sh

# Tail the run log
tail -f ~/Library/Logs/state-mitm-drift-check.log

# Disable (unloads the schedule; .plist file stays on disk)
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/dev.state.mitm-drift-check.plist

# Re-enable (after editing the .plist or after an unload)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.state.mitm-drift-check.plist

# Validate plist XML before bootstrapping (catches typos before launchd does)
plutil -lint ~/Library/LaunchAgents/dev.state.mitm-drift-check.plist
```

## How to act on a drift notification

1. Run a fresh mitmproxy capture against the new Claude Code (see
   `.planning/milestones/v2/phases/014-anthropic-oauth-provider/014-CONTEXT.md`
   §specifics for the capture procedure).
2. Diff captured `user-agent`, `x-app`, `anthropic-beta` against the constants in
   `src/state_core/auth/providers/anthropic.py`.
3. Update `_CLAUDE_CLI_VERSION`, `_USER_AGENT`, `_ANTHROPIC_BETA` to match. Update
   the matching `_EXPECTED_*` literals in `tests/auth/providers/test_anthropic.py`
   in lockstep.
4. Refresh the provenance comments to cite the new capture date.
5. Run `pytest tests/auth/oauth_common/ tests/auth/providers/ -q` — must show 18
   passed.
6. Commit on a `chore/stealth-drift-YYYY-MM-DD` branch and merge to `main`.

The watcher self-syncs after step 3 — no change needed in
`~/.local/bin/state-mitm-drift-check.sh`.

## Permissions

The script invokes `osascript` to fire `display notification`. macOS attributes
that notification to whatever app launched osascript. If notifications stop
appearing:

- System Settings → Notifications → look for **Script Editor** or **osascript**
- Allow Notifications, Sounds, Banners

A test fire to verify the path:

```bash
osascript -e 'display notification "test" with title "state — drift watcher test" sound name "Glass"'
```

## When to retire this watcher

Phase 022 ships the captured-header golden-file regression test (AUTH-13). When
that lands and runs in CI on every push, this watcher becomes redundant for
detecting stealth-shape drift on a current `claude` install — but it remains
useful for detecting that the *operator's local* Claude Code has drifted past
what the project pins. Decision: keep the watcher running locally; CI handles
the project-side enforcement.

To retire fully:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/dev.state.mitm-drift-check.plist
rm ~/Library/LaunchAgents/dev.state.mitm-drift-check.plist
rm ~/.local/bin/state-mitm-drift-check.sh
# logs in ~/Library/Logs/state-mitm-drift-check.* can be deleted at leisure
```

## Reference

- Phase 014 context: `.planning/milestones/v2/phases/014-anthropic-oauth-provider/014-CONTEXT.md`
- Phase 014 verification: `.planning/milestones/v2/phases/014-anthropic-oauth-provider/014-VERIFICATION.md`
- Drift-fix commit: `32bc4a2 feat(014): pin stealth constants to live Claude Code 2.1.121 capture`
- Reference snapshot (gitignored): `.state-inputs/references/milady/` (claude-cli 2.1.92)
