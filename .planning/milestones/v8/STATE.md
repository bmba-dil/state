# STATE: v8 — Plugin Server Hooks (all 9)

**Milestone:** v8
**Phase range:** 068–079
**Status:** Complete (11/12 phases; 073 deferred)
**Phases complete:** 11 / 12
**Last activity:** 2026-05-05 — Milestone shipped. 10/11 HOOK requirements satisfied. HOOK-05 (event hook) deferred — `event` key not in opencode Hooks type (v1.14.35).

---

## Phase Status

| Phase | Slug | Status |
|-------|------|--------|
| 068 | state-opencode-plugin-ts-package | Complete |
| 069 | chat-message-hook | Complete |
| 070 | tool-execute-before-hook | Complete |
| 071 | tool-execute-after-hook | Complete |
| 072 | permission-ask-hook | Complete |
| 073 | event-hook | ⏭ Deferred (API gap — `event` not in opencode Hooks type v1.14.35) |
| 074 | experimental-chat-system-transform | Complete |
| 075 | experimental-session-compacting | Complete |
| 076 | chat-params-and-headers-hook | Complete |
| 077 | command-execute-before-hook | Complete |
| 078 | shell-env-hook | Complete |
| 079 | plugin-bundle-and-install-script | Complete |

## Requirement Coverage

| Requirement | Status | Phases |
|-------------|--------|--------|
| HOOK-01 | ✅ Satisfied | 069 |
| HOOK-02 | ✅ Satisfied | 070 |
| HOOK-03 | ✅ Satisfied | 071 |
| HOOK-04 | ✅ Satisfied | 072 |
| HOOK-05 | ⏭ Deferred | 073 (upstream API gap) |
| HOOK-06 | ✅ Satisfied | 074 |
| HOOK-07 | ✅ Satisfied | 075 |
| HOOK-08 | ✅ Satisfied | 076 |
| HOOK-09 | ✅ Satisfied | 077 |
| HOOK-10 | ✅ Satisfied | 078 |
| HOOK-11 | ✅ Satisfied | 068, 079 |

## Deferred Items

- **HOOK-05 (event hook):** The `event` key does not exist in opencode's `Hooks` type as of v1.14.35. Event mirroring to daemon will be implemented when the API supports it. A standalone SSE mirror utility can be called from other hooks in the interim.
