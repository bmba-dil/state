---
milestone: v8
audited: "2026-05-05T07:00:00Z"
status: tech_debt
scores:
  requirements: "10/11"
  phases: "11/12"
  integration: "10/11"
  flows: "10/11"
gaps:
  requirements:
    - id: "HOOK-05"
      status: "unsatisfied"
      phase: "073"
      claimed_by_plans: []
      completed_by_plans: []
      verification_status: "gap_found"
      evidence: "`event` key does not exist in opencode Hooks type (v1.14.35). Event mirroring deferred until API supports it."
  integration: []
  flows: []
tech_debt:
  - phase: "073-event-hook"
    items:
      - "HOOK-05: event mirror to daemon deferred — `event` hook not in opencode Hooks type (v1.14.35)"
      - "SSE mirror utility not implemented (awaiting API support)"
---

# v8 — Plugin Server Hooks (all 9) — Milestone Audit

## Requirements Coverage

| REQ-ID | Description | Phase | Status | Evidence |
|--------|-------------|-------|--------|----------|
| HOOK-01 | `chat.message` — observation + context injection | 069 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/chat-message.ts` implements parsing, mode gating, hint injection |
| HOOK-02 | `tool.execute.before` — mode-gate tool invocation | 070 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/tool-execute-before.ts` blocks cross-mode tools |
| HOOK-03 | `tool.execute.after` — verify outputs + observation | 071 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/tool-execute-after.ts` implements build verify + teach observe |
| HOOK-04 | `permission.ask` — gray-area routing | 072 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/permission-ask.ts` auto-approves state-internal permissions |
| HOOK-05 | `event` — mirror opencode events to daemon | 073 | ⚠ deferred | `event` key not in opencode Hooks type (v1.14.35). Deferred until API support. |
| HOOK-06 | `experimental.chat.system.transform` — mode-specific system prompts | 074 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/chat-system-transform.ts` injects BUILD/TEACH banners |
| HOOK-07 | `experimental.session.compacting` — checkpoint Step state | 075 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/session-compacting.ts` injects preserve-IDs |
| HOOK-08 | `chat.params` / `chat.headers` — profile + cache-control | 076 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/chat-params.ts` resolves profiles, injects headers |
| HOOK-09 | `command.execute.before` — mode gate for slash commands | 077 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/command-execute-before.ts` blocks cross-mode commands |
| HOOK-10 | `shell.env` — export STATE_* env vars | 078 | ✅ satisfied | VERIFICATION.md passed; `src/hooks/shell-env.ts` exports all 7 STATE_* vars |
| HOOK-11 | Bundled as `@state/opencode-plugin` | 068 + 079 | ✅ satisfied | VERIFICATION.md passed; `bun build` produces 11.53 KB bundle; `install.sh` auto-registers |

## Phase Summary

| Phase | Name | Status | Verified |
|-------|------|--------|----------|
| 068 | TS Package Scaffolding | ✅ Complete | passed |
| 069 | chat.message Hook | ✅ Complete | passed |
| 070 | tool.execute.before Hook | ✅ Complete | passed |
| 071 | tool.execute.after Hook | ✅ Complete | passed |
| 072 | permission.ask Hook | ✅ Complete | passed |
| 073 | event Hook | ⏭ Deferred | gap_found |
| 074 | chat.system.transform Hook | ✅ Complete | passed |
| 075 | session.compacting Hook | ✅ Complete | passed |
| 076 | chat.params + chat.headers Hook | ✅ Complete | passed |
| 077 | command.execute.before Hook | ✅ Complete | passed |
| 078 | shell.env Hook | ✅ Complete | passed |
| 079 | Bundle + Install | ✅ Complete | passed |

## Integration Check

- All hooks registered in single `server` export (`src/index.ts`)
- `bun build` bundles all 10 modules into single `dist/index.js` (11.53 KB)
- TypeScript declarations emitted via `tsc`
- `install.sh` auto-registers plugin path in opencode config
- Cross-hook dependencies: chat.params and chat.headers share `resolveProfile()` utility

## Score

**10/11 requirements satisfied** (HOOK-05 deferred)

## Verdict: Tech Debt

No critical blockers. One requirement (HOOK-05) is deferred due to an upstream API gap — the `event` hook does not exist in opencode's `Hooks` type as of v1.14.35. When opencode adds the event hook, a follow-up phase can implement HOOK-05.
