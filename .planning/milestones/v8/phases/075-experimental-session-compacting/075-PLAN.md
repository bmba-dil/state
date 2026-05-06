---
phase: "075"
phase_name: "experimental.session.compacting Hook"
goal: "Inject preserve-IDs for active Step, last 3 verify results, open gray-area, pending drills"
wave: 1
depends_on: ["068"]
files_modified: []
autonomous: true
requirements: [HOOK-07]
---

## Plan 1: Implement `experimental.session.compacting` Hook

**Goal:** Inject context preservation instructions during session compaction to maintain critical state across context resets.

### Tasks

#### 1.1 Create Compaction Preservation Logic
**Acceptance:** `packages/opencode-plugin/src/hooks/session-compacting.ts` exports the hook
**Estimated effort:** Medium
**Dependencies:** 068

<acceptance_criteria>
- grep 'experimental.session.compacting' packages/opencode-plugin/src/hooks/session-compacting.ts
- grep 'output.context' packages/opencode-plugin/src/hooks/session-compacting.ts
- grep 'preserve\|Step\|Slice\|Phase' packages/opencode-plugin/src/hooks/session-compacting.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/hooks/session-compacting.ts`:

1. Implement `getActiveStateIds()` — reads STATE_STEP, STATE_SLICE, STATE_PHASE from env
2. Implement `getPreserveContext()` — generates context string with active IDs + last verify results
3. Implement the main hook function that appends preservation instructions to `output.context`
4. Export as `export const sessionCompacting: Hooks["experimental.session.compacting"]`
</action>

#### 1.2 Register Hook and Verify Build
**Acceptance:** Hook registered; build passes
**Estimated effort:** Small
**Dependencies:** 1.1

<acceptance_criteria>
- grep 'experimental.session.compacting' packages/opencode-plugin/src/index.ts
- bun run build exits 0; bun run typecheck exits 0
</acceptance_criteria>

### Verification Criteria (must_haves)
- [ ] Inject preserve-IDs during compaction
- [ ] Append context strings
- [ ] Hook registered in server
- [ ] TypeScript compiles cleanly
