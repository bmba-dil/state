# Plan-as-Prompt: Injection, Mutability, Audit-Log (Canonical, v41)

> **Phase:** 403
> **Status:** Canonical (v41)
> **Requirements covered:** PAP-01..PAP-06
> **Build-mode only.** Build-mode modules must not import teach-mode modules (cardinal rule, PROJECT.md — mode isolation enforced by CI import-graph lint).
> **Sibling specs:** STEP-PLAN-FORMAT.md (frontmatter + body sections); EXEMPLAR-stepNPLAN.md (canonical worked example).

At execute-slice start, the on-disk `stepNPLAN.md` IS the executor's primary system prompt. The harness reads it, strips upstream-only sections (plan-slice reasoning meta and already-completed upstream `<interfaces>` excerpts), resolves `@`-references to inlined content (one level only, subject to a per-injection token cap), augments with runtime state (worktree path, prior task results, resolved upstream provides blocks, and the current task pointer), and injects via the `chat.params` plugin hook. Plans are mutable with audit log: immutable sections (frontmatter fields, `<verify>` blocks, `must_haves.*`, and most body tags enumerated in the Mutability Matrix) are enforced via the `tool.execute.before` diff-the-proposed-write mechanism, which emits `state.step.plan_edit_blocked` on violations; mutable sections (`<action>`, `<read_first>`, prose `<context>`) are edited freely by executors, each change logged as a `state.step.plan_edit` event.

---

## Injection Flow (PAP-01)

The injection flow executes at every execute-slice start and at every re-injection triggered by context overflow (CTX-09 carry-forward from Phase 402).

1. **Slice spawn** — daemon initiates a fresh opencode session at Slice boundary (CTX-02). The plugin's `chat.params` hook fires, granting the harness the opportunity to supply the initial chat parameters (system prompt, parameters) before the executor sees any message.

2. **Read on-disk plan** — harness reads the current Step's on-disk `stepNPLAN.md` from the slice's worktree. The file at this point is the LIVE version (potentially already edited from the `plan_edit` chain if the slice has been re-entered). The `state.step.plan_authored` event row (see Section 8) holds the immutable original for replay.

3. **Apply content stripping (PAP-06)** — harness strips plan-slice reasoning meta blocks and `<interfaces>` excerpts for already-completed upstream Steps (deduplicated against the reinject payload's `<upstream_provides>` slot from CTX-06). The on-disk file is unchanged. The stripped injection is an ephemeral, in-memory artifact only. Audit-logged original preserved in the event store via the `state.step.plan_authored` row.

4. **Resolve `@`-references (PAP-02)** — harness inlines `@.planning/X.md` content one level only, with a per-injection token cap of 30_000 tokens for all inlined refs combined; excess content replaced with `<truncated path="X.md" bytes_omitted="N"/>`. Cache key `(snapshot_event_id, ref_path)`; cache lifetime = current Slice session.

5. **Augment with runtime state** — harness appends a `<runtime_augmentation>` block carrying:
   - `<worktree_path>` — current worktree absolute path (from Phase 402 worktree service).
   - `<prior_task_results>` — recent `<verify>` results for completed sibling tasks within this Step.
   - `<upstream_provides>` — resolved upstream Step `provides:` blocks from CTX-06 reinject payload.
   - `<current_task_pointer>` — task_id of the next task to execute (CTX-06).

6. **Inject via `chat.params` hook** — the plugin posts the assembled prompt as the system message of the new chat session. The plugin is a thin reporter (Phase 402 carry-forward); the daemon authoritatively assembles the prompt. The plugin does not apply any further transformation — it relays the daemon's assembled bytes verbatim.

### Why on-disk plan is the source of truth

The on-disk `stepNPLAN.md` is the LIVE version executors edit. The audit-logged original lives in the event store as a `state.step.plan_authored` row (see Section 8). Replay reconstructs the original from event store; live state from file. Git history of the file (commit_docs=true in v41 config) provides a secondary audit trail — useful for human review, NOT load-bearing.

### What the executor sees

The executor sees the (potentially stripped + @-resolved + augmented) injected version during execution, NOT the on-disk file directly. To re-read the plan, the executor invokes `Read` on the on-disk path; the resulting content has NO @-resolution applied — the executor reads the same on-disk file the harness saw at injection time. (Re-injection on context overflow per CTX-09 re-runs the full injection flow.)

### Injection timing diagram

The following sequence illustrates injection timing across Slice boundary and context overflow:

```
Slice boundary spawn:
  daemon       plugin        executor
     |--spawn session-------->|
     |<--chat.params fires----|
     |--read on-disk plan---->|
     |--strip content-------->|
     |--resolve @-refs------->|
     |--build augmentation--->|
     |--inject as system msg->|
                              |<--executor starts work--|

Context overflow (CTX-09):
  daemon       plugin        executor
     |<--CTX-09 trigger-------|
     |--re-read on-disk------>|
     |--strip (updated LRU)-->|
     |--resolve @-refs (cache)|
     |--rebuild augmentation->|
     |--reinject as sys msg-->|
                              |<--executor resumes work--|
```

Notes:
- Cache hit rate is high on re-injection (same `session_id`, refs unchanged in most cases).
- Mutable edits the executor made before overflow ARE present in on-disk file at re-injection time (carried forward).
- `<runtime_augmentation>` is always rebuilt fresh (current task pointer, latest prior task results).

---

## Runtime Augmentation Block

The `<runtime_augmentation>` slot appended to the injected plan carries dynamic state the on-disk plan cannot express. The slot's body shape is fixed by Phase 402's CONTEXT-PROTOCOL.md reinject payload spec; this spec adds the per-Step pointers so that the executor knows its current task position and has immediate access to upstream contract content.

```xml
<runtime_augmentation>
  <worktree_path>{absolute_path}</worktree_path>
  <prior_task_results>
    <task_result task_id="..." status="pass|fail" automated_output_excerpt="..."/>
    ...
  </prior_task_results>
  <upstream_provides>
    <provides step_id="..."><![CDATA[{markdown content of upstream SUMMARY.md provides: block}]]></provides>
    ...
  </upstream_provides>
  <current_task_pointer>{task_id}</current_task_pointer>
</runtime_augmentation>
```

### Stripping pointer for upstream `<interfaces>`

When an `<interfaces>` excerpt is for an upstream Step whose `provides:` block is already present in `<upstream_provides>` above, the harness REPLACES the excerpt with: `<interfaces ref="upstream_provides[step-N]"/>`. The contract is still in-context (executor scans the named upstream-provides slot for the literal); no STP-07 violation. **Silent removal would force executors to discover that upstream excerpts moved** — the pointer form preserves zero-codebase-exploration.

Forward-pointer: Reinject payload XML body shape source: see `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §6 (reinject payload, CTX-06).

---

## @-Reference Resolution Rule (PAP-02)

### Resolution semantics

Harness resolves `@.planning/X.md` and `@-` refs at injection time, **inlines verbatim file content**, **stops at one level** (no recursive @-resolution; if a referenced doc itself uses @-refs, the planner is encouraged to inline-expand them at planning time).

**Per-injection token cap: 30_000 tokens for all inlined refs combined.** Pinned in this spec; v14 may tune to 20k or 40k based on EXEMPLAR-stepNPLAN.md realistic measurements (per 403-CONTEXT.md Claude's Discretion).

Excess content replaced with `<truncated path="X.md" bytes_omitted="N"/>` marker.

Cache key: `(snapshot_event_id, ref_path)` tuple; cache lifetime = current Slice session.

Token-counter: same fallback as CTX-08 (Anthropic `usage` if present; chars/4 heuristic otherwise).

The one-level restriction is intentional. Recursive expansion violates token-budget predictability (Phase 402's CTX-01 200k absolute budget is load-bearing). One-level + token cap + truncation marker keeps the prompt budget computable at planning time.

### Path confinement (security)

All `@`-references MUST resolve to paths under repo root + `.planning/` subtree OR the workspace's source tree (`src/`, `tests/`, `packages/`, root `*.md` like `CLAUDE.md` and `PROJECT.md`). The exact allow-list is computed at planning time from the milestone's repo-root manifest; v14 implements via `pathlib.Path.resolve()` + ancestor check.

Example from EXEMPLAR-stepNPLAN.md — its `<context>` block contains:
```
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@src/state_core/schema.py
```
All five references are confinement-compliant: repo-root file (`CLAUDE.md`), `.planning/` subtree references, and `src/` subtree reference.

Positive and negative example pair:

```text
ALLOWED:
  @.planning/PROJECT.md          → resolves under repo root + .planning/
  @CLAUDE.md                     → resolves at repo root (allow-listed)
  @src/state_core/schema.py      → resolves under src/
  @.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md  → .planning/ subtree

REJECTED (resolver raises + emits state.step.plan_edit_blocked):
  @/etc/passwd                   → absolute path outside repo root
  @../../../home/user/.ssh/id    → parent-dir traversal escapes repo root
  @/tmp/whatever.md              → absolute path outside repo root
  @http://evil.example/x.md      → URL form not supported (only filesystem refs)
```

**fail-closed semantics:** on rejection the resolver does NOT silently drop the reference. The whole injection is aborted; daemon emits `state.step.plan_edit_blocked` with `locked_section="@-reference-confinement"` and `proposed_diff` describing the rejected ref. The Slice session is held; human gate via opencode `question` tool surfaces the violation.

### Caching

The @-reference cache is scoped to the current Slice session, keyed by `(snapshot_event_id, ref_path)`. A Slice-boundary spawn (fresh session) invalidates the cache entirely (new `snapshot_event_id`). Compaction within a Slice (CTX-03) preserves the cache because the `session_id` is retained across intra-Slice compaction; only the `snapshot_event_id` advances, which causes a targeted cache invalidation for any ref whose content may have changed since the prior snapshot.

### @-reference resolution pseudocode (v14 implementation note)

```python
ALLOWED_SUBTREES = [
    repo_root / ".planning",
    repo_root / "src",
    repo_root / "tests",
    repo_root / "packages",
    repo_root / "CLAUDE.md",
    repo_root / "PROJECT.md",
    # ... extended from milestone repo-root manifest
]

def resolve_at_ref(ref_path: str, session_id: str, snapshot_event_id: str) -> str:
    """Resolves one @-reference. Returns inlined content or raises."""
    cache_key = (snapshot_event_id, ref_path)
    if cache_key in _at_ref_cache:
        return _at_ref_cache[cache_key]

    # Confinement check
    resolved = (repo_root / ref_path.lstrip("@")).resolve()
    if not any(resolved.is_relative_to(subtree) for subtree in ALLOWED_SUBTREES):
        raise AtRefConfinementError(ref_path, resolved)

    content = resolved.read_text()
    _at_ref_cache[cache_key] = content
    return content

def inline_at_refs(plan_text: str, session_id: str, snapshot_event_id: str,
                   token_cap: int = 30_000) -> str:
    """
    Inline all @-refs in plan_text, one level only.
    Excess content beyond token_cap replaced with <truncated ...> markers.
    """
    tokens_used = 0
    result_parts = []
    for chunk in split_on_at_refs(plan_text):
        if is_at_ref(chunk):
            inlined = resolve_at_ref(chunk, session_id, snapshot_event_id)
            inlined_tokens = count_tokens(inlined)
            if tokens_used + inlined_tokens > token_cap:
                bytes_omitted = len(inlined.encode())
                result_parts.append(
                    f'<truncated path="{chunk}" bytes_omitted="{bytes_omitted}"/>'
                )
            else:
                result_parts.append(inlined)
                tokens_used += inlined_tokens
        else:
            result_parts.append(chunk)
    return "".join(result_parts)
```

This pseudocode is non-normative; v14 may use a different splitting strategy. The normative requirement is: one-level resolution, token cap 30_000, fail-closed on confinement violation, cache by `(snapshot_event_id, ref_path)`.

---

## Mutability Matrix (PAP-03)

This section is the authoritative roll-up of which `stepNPLAN.md` sections are mutable vs. immutable at runtime. STEP-PLAN-FORMAT.md sibling spec marks each section's mutability inline; this section is the canonical reference table. The diff-the-proposed-write enforcer (Section 7) reads from this matrix to determine whether a proposed write to a `*/stepNPLAN.md` file should be allowed or blocked.

PAP-03 originally required only `must_haves.*` and `<verify>` blocks to be immutable. This matrix STRENGTHENS that requirement by locking ALL frontmatter fields and most body sections; the strengthening is justified by the Step-identity-fields rationale: changing a locked field means it is a different Step, which requires a replan via plan-slice, not an in-place mutation.

| Section / Block | Lock state | Rationale |
|-----------------|------------|-----------|
| All frontmatter fields (every key in `StepFrontmatter`) | **Locked** | Step-identity fields. Changing them means it's a different Step. PAP-03 already locks `must_haves`; this matrix locks the rest. |
| `must_haves.truths` / `.artifacts` / `.key_links` | **Locked** | PAP-03 verbatim — gate definition. The Boolean Proof Gate (Phase 404) reads these. |
| `<objective>` | **Locked** | Step contract. Changing the objective changes the Step's purpose — replan required. |
| `<execution_context>` | **Locked** | Bootstrap doc references. Harness resolves these; mutation would desync from the injected content. |
| `<context>` (prose @-refs) | **Mutable** | Executor may add/remove @-refs as it learns what context it needs. Changes logged as `plan_edit` events. |
| `<interfaces>` | **Locked** | STP-07 literal upstream excerpts; mutating silently desyncs from upstream artifact (re-plan required if upstream genuinely changes). |
| `<task type="...">` | (per-sub-tag below) | Task tag itself is structural; sub-tag mutability varies. |
| `<task>` `type` attribute | **Locked** | Changing the type means it's a different task. Different types trigger different harness behaviors. |
| `<task>` `tdd` attribute | **Locked** | Same as above — TDD cycle enforcement depends on this attribute being stable. |
| `<name>` | **Locked** | Used as event key + SUMMARY anchor. Changing it orphans prior events. |
| `<files>` | **Locked** | Task contract; allowlist. SRP-04 enforces the allowlist at runtime — mutation would bypass the guard. |
| `<read_first>` | **Mutable** | Executor refines as it discovers what to read. The plan author's list is a starting point. |
| `<action>` | **Mutable** | Executor refines implementation steps as it learns. The core delivery contract is in `<verify>` + `<acceptance_criteria>`, not `<action>`. |
| `<verify>` (any nested element) | **Locked** | PAP-03 verbatim — gate per task. Phase 404 consumes this for the Boolean Proof Gate. |
| `<acceptance_criteria>` | **Locked** | Task contract. Defines measurable done-ness. |
| `<done>` | **Locked** | Task contract. Transition trigger for the harness. |
| `<options>` (under `<task type="checkpoint:decision">`) | **Locked** | Decision-bounded; no runtime expansion. 403-CONTEXT.md `<decisions>` Task-type behaviors. |
| `<threat_model>` (parent block + initial `<threat>` children) | **Locked** | Design-time contract. |
| `<threat_model>/<discovered_threats>` (carve-out) | **Append-only** | Hybrid; new `<threat>` sub-elements may be appended at runtime. See Section 7 for the exact diff shape that qualifies as append-only. |
| `<verification>` (Slice-level pre-commit bash block) | **Locked** | Slice gate per PAP-03. Harness runs this before advancing to the next Step. |
| `<success_criteria>` | **Locked** | Step contract. |
| `<output>` | **Locked** | SUMMARY path; not for runtime mutation. |

### Quick reference — what executors can edit

Mutable sections (executor edits freely): `<context>`, `<read_first>`, `<action>`, `<discovered_threats>` (append-only). Everything else is locked; attempted edits emit `state.step.plan_edit_blocked` (Section 7).

### Mutability matrix enforcement phases

The matrix is consumed at three points in the lifecycle:

1. **Plan authoring (research-slice validation stage)** — the plan-slice planner validates that all frontmatter fields are populated and that the `must_haves.*` + `<verify>` blocks are complete. If any locked section is missing or malformed, the validation stage fails and the Step plan is not committed to the event store as `plan_authored`.

2. **Execute-slice runtime (tool.execute.before enforcement)** — on every Write/Edit to `*/stepNPLAN.md`, the diff-the-proposed-write enforcer (Section 7) consults the matrix to determine if any locked section is modified. Rejected edits emit `state.step.plan_edit_blocked`.

3. **Replay / milestone close** — the projector replays all `plan_edit` events for a Step. If any event's diff touches a locked section (which should be impossible after runtime enforcement, but checked defensively), the projector logs a `PlanIntegrityError` with the event id and section name.

### Rationale for locking all frontmatter (extension of PAP-03)

PAP-03 (REQUIREMENTS.md) originally stated: "`must_haves.*` and every `<verify>` block are immutable." This matrix extends the lock to ALL frontmatter fields for the following reasons:

- **`step_id`** — event store uses `step_id` as the correlation key for all `plan_edit` events for a Step. Changing it mid-execution would orphan the prior events.
- **`depends_on`** — the DAG scheduler reads this field at execute-slice start. Changing it mid-Slice would race with the scheduler.
- **`files_modified`** — SRP-04 reads this as the allowlist for Write/Edit. Changing it would bypass the scope guard.
- **`wave`** — the wave-executor uses this to determine parallelism. Changing it mid-run would violate the parallelism contract.

The extension is absorbed inline per the REQUIREMENTS amendments survey (Section 9): it is a STRENGTHENING, not a contradiction.

---

## plan_edit Event Schema (PAP-04)

Every plan edit emits a `state.step.plan_edit` event carrying a unified diff plus before/after content hashes. Replay reconstructs full content by walking the diff chain from the original `state.step.plan_authored` event. Compact, auditable, replay-deterministic. Aligned with `workflow-docs-from-gsd-2/file-tracking.md` Correction 1 (best-effort commit, not transactional).

The event naming convention follows v40 EVENT-TAXONOMY.md: `state.{tier}.{action}` where tier is the owning aggregate/subsystem. All step-plan events use `state.step.*`:

| Event type | When emitted |
|-----------|-------------|
| `state.step.plan_authored` | At research-slice end, once per Step, carries full original content |
| `state.step.plan_edit` | On every mutable-section Write/Edit to `stepNPLAN.md` |
| `state.step.plan_edit_blocked` | When `tool.execute.before` rejects a locked-section write |
| `state.step.checkpoint_resolved` | When a checkpoint task is resolved (auto or human) |
| `state.step.checkpoint_human_action_pending` | When `checkpoint:human-action` task is waiting |
| `state.step.checkpoint_human_action_resolved` | When human confirms the human-action checkpoint |

(Full event family — 9 events — is specified in STEP-EVENTS.md, Plan 04. This spec defines only the 3 plan-edit events inline; the checkpoint + replan family lives in Plan 04.)

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal

class PlanEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    diff: str                                    # git-style unified diff
    before_sha256: str                           # full file before edit
    after_sha256: str                            # full file after edit
    editor: Literal["executor", "harness", "human"]
    edited_at: datetime                          # UTC, ISO-8601
    session_id: str                              # editing session
    immutable_section_touched: bool              # set by tool.execute.before; True triggers plan_edit_blocked instead
```

### Replay verification

**Replay-time integrity check (security mitigation):** when the projector replays a `state.step.plan_edit` event, it MUST verify:

1. `before_sha256` matches the SHA-256 of the on-disk content prior to applying `diff` (or, on cold replay starting from `state.step.plan_authored`, matches the original content hash).
2. `after_sha256` matches the SHA-256 of the on-disk content after applying `diff`.
3. On hash mismatch, the projector REJECTS the event (logs error, does not advance the projection state). Mismatched-hash events surface as a daemon-startup error gating the harness from spawning new sessions until reconciled.

Forward-pointer: v14 Build Kernel implements the projector + replay verifier. Reference convention: `state_core.projector` (existing CQRS handler registration).

### Event store row append-only guarantee

Per v40 EVENT-TAXONOMY.md, all event rows are append-only (immutable). The `state.step.plan_edit` row inherits this guarantee — no UPDATE/DELETE on the event row; corrections are NEW events with editor-history transparency. The `state.step.plan_authored` row (Section 8) is similarly append-only: "the `state.step.plan_authored` row is append-only; replay rebuilds the original from this row alone."

### Replay reconstruction algorithm

Given the `state.step.plan_authored` row (original content + hash) and the ordered sequence of `state.step.plan_edit` events for a given `step_id`, the projector reconstructs the content at any edit `N` as:

```
content_at_N = plan_authored.original_content
for event in plan_edit_events[0..N]:
    assert sha256(content_at_N) == event.before_sha256      # integrity check
    content_at_N = apply_unified_diff(content_at_N, event.diff)
    assert sha256(content_at_N) == event.after_sha256        # post-apply check
```

Failure at any assertion: the projector raises `PlanEditReplayError` with the event id and hash mismatch detail. The daemon surfaces this via the `GET /health` endpoint as `plan_edit_replay: degraded`.

---

## plan_edit_blocked + Diff-the-Proposed-Write Enforcer (PAP-05)

### PlanEditBlocked Pydantic schema

```python
class PlanEditBlocked(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    proposed_diff: str
    locked_section: str                          # e.g., "frontmatter.must_haves.truths" or "<acceptance_criteria>"
    blocked_at: datetime
    session_id: str
    proposed_by: Literal["executor", "harness", "human"]
```

### Diff-the-proposed-write algorithm

1. `tool.execute.before` hook intercepts every Write/Edit targeting `*/stepNPLAN.md` files.
2. Computes prospective new content (apply Edit operation in-memory; for Write, the new content is the input).
3. Parses both old and new with the StepPlan parser (Pydantic frontmatter + XML body) — see STEP-PLAN-FORMAT.md.
4. Compares the immutable subset (locked frontmatter keys + locked XML tags from the Mutability Matrix in Section 5) using a normalized AST diff.
5. Any change to a locked section → reject + emit `state.step.plan_edit_blocked` event.
6. Pure-machine check (matches PRF-04 spirit). Works for both partial Edit and full Write.
7. The `<discovered_threats>` append-only carve-out is a special case: writes that ONLY add nodes to `<discovered_threats>` (no other diff) pass.

### `<discovered_threats>` append-only diff shape

**The exact diff shape that counts as 'append-only':** ONLY new `<threat>...</threat>` sub-elements added at the end of `<discovered_threats>`; no removal of existing children, no edit of existing children's text.

```diff
ACCEPTED (new threat appended at end of <discovered_threats>):
--- before
+++ after
 <discovered_threats>
   <threat id="T-1">existing threat text</threat>
+  <threat id="T-2">new threat discovered at runtime</threat>
 </discovered_threats>

REJECTED (existing threat text edited):
--- before
+++ after
 <discovered_threats>
-  <threat id="T-1">existing threat text</threat>
+  <threat id="T-1">existing threat text MODIFIED</threat>
 </discovered_threats>

REJECTED (existing threat removed):
--- before
+++ after
 <discovered_threats>
-  <threat id="T-1">existing threat text</threat>
   <threat id="T-2">other threat</threat>
 </discovered_threats>
```

### No-direct-write contract

**ALL writes to `*/stepNPLAN.md` MUST go through `tool.execute.before`.** Other write paths (e.g., subprocess shell commands, raw filesystem writes from outside the harness-managed tool surface) are out-of-policy. v14 enforces by routing all Write/Edit through the daemon's HTTP middleware (Phase 402 carry-forward: `tool.execute.before` is the canonical block hook). Subprocess shell calls that mutate stepNPLAN.md bypass the enforcer; the spec stipulates they MUST NOT happen — v14 implementation MAY add a filesystem watcher as defense-in-depth, but the contract is the hook routing.

### Advisory message text

On block, harness injects an advisory into the executor's context (system message). Recommended wording (Claude's Discretion per 403-CONTEXT.md):

> "Cannot edit immutable `<{locked_section}>` — re-run plan-slice if scope changed. The proposed diff was rejected by the diff-the-proposed-write enforcer (PAP-05). Run `/state-replan` to author a new Step plan, or revise your edit to touch only mutable sections."

### Integration with v9 TUI toast notifications

The daemon's SSE bus emits `plan_edit_blocked` events. The v9 statusline + sidebar plugin (Phase 9 milestone) subscribes to this stream and surfaces the block reason as a one-shot toast notification so the executor sees the rejection inline without needing to inspect the daemon logs. The toast wording mirrors the advisory message above, truncated to 120 chars. This is a v14 implementation note, not a spec requirement.

### `plan_edit_blocked` and `plan_edit` relationship

When `tool.execute.before` detects a locked-section diff, it emits ONLY `state.step.plan_edit_blocked` — NOT `state.step.plan_edit`. The proposed write is rejected; the on-disk file is unchanged; the event log records what was attempted and blocked. A human or re-plan is required to proceed. This is intentional: the event log has no half-applied state, only clean before/after pairs (for allowed edits) or blocked attempts (for rejected edits).

---

## Content Stripping + Audit-Log Original (PAP-06)

### What gets stripped at injection time

- **plan-slice reasoning meta blocks** — research notes, pattern-mapping rationale, validation-stage commentary, alternatives-considered. Belongs in DECISIONS.md, not the executor's working prompt.
- **`<interfaces>` excerpts for already-completed upstream Steps** — when the upstream Step's `provides:` blocks are already inlined in `<upstream_provides>` (carried via reinject payload per CTX-06), the redundant `<interfaces>` excerpt is replaced with `<interfaces ref="upstream_provides[step-N]"/>` pointer. Preserves STP-07 zero-codebase-exploration: the contract is still in-context, just deduplicated. Executor scans the named upstream-provides slot for the literal.
- **Stripping does NOT modify on-disk `stepNPLAN.md`.** The audit-logged original (event store row) carries the full unredacted content.

### state.step.plan_authored event (audit-log original)

The `StepPlanAuthored` Pydantic schema is defined here as an inline forward-pointer to STEP-EVENTS.md (Plan 04), which carries the full event family. Brief shape:

```python
class StepPlanAuthored(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    slice_id: str
    original_content: str                        # full file content, verbatim
    original_sha256: str                         # SHA-256 of original_content
    authored_at: datetime
    authored_by: Literal["plan-slice", "human", "harness"]
    session_id: str
```

**Authoritative audit log:** the original is committed at research-slice end (when the planner-validation stage passes). The on-disk `stepNPLAN.md` is the LIVE version; replay reconstructs original from the event store row + diff chain.

### Why a single file (not stepNPLAN.original.md)

Per 403-CONTEXT.md `<deferred>`: a two-file scheme (`stepNPLAN.original.md` + `stepNPLAN.md`) is REJECTED — divergence risk + double the per-Slice file count. Single file + event-store snapshot wins.

### Conditional stripping deferred

Per 403-CONTEXT.md `<deferred>`: per-section conditional stripping via plan-author-driven `inject:` frontmatter flag is DEFERRED to v14 if EXEMPLAR sizing reveals default rules are insufficient.

### Re-injection on context overflow (CTX-09)

When context overflow triggers re-injection (CTX-09 carry-forward), the harness repeats steps 3–6 of the injection flow (Section 2) but uses the CURRENT on-disk file (not the `plan_authored` original) as the read source. This is intentional: the executor may have made valid mutable edits during the session; re-injection should carry those forward. The `<runtime_augmentation>` block is rebuilt fresh at re-injection time (worktree path, prior task results, upstream provides are current-session state).

Re-injection does NOT reset the diff chain. `state.step.plan_edit` events already committed before the overflow remain in the event store; replay reconstructs the on-disk state from them.

### Token budget accounting at injection time

The harness computes the injection budget before assembling the final prompt:

```
budget_used  = len(tokenize(on_disk_plan_content_after_stripping))
             + len(tokenize(all_inlined_at_refs_content))
             + len(tokenize(runtime_augmentation_block))

budget_limit = CTX-01_absolute_200k_tokens - CTX-01_executor_reserve
```

If `budget_used > budget_limit`, the harness applies additional stripping before injecting (removes the largest `<interfaces>` excerpt not already replaced with a pointer, then re-measures). The token counter uses the CTX-08 fallback: Anthropic `usage` field if present in the prior session's final response; otherwise chars/4 heuristic. The 30_000 token cap for @-reference inlining is a sub-budget within the larger CTX-01 200k absolute.

---

## Cross-references + REQUIREMENTS Survey

### Sibling specs

- **STEP-PLAN-FORMAT.md** — defines the format this spec injects, mutates, and audits. The Mutability Matrix in Section 5 above is the canonical cross-reference; STEP-PLAN-FORMAT.md marks each section's mutability inline citing this table.
- **STEP-EVENTS.md (Plan 04)** — defines the Pydantic schemas for `state.step.plan_authored`, `state.step.plan_edit`, `state.step.plan_edit_blocked`, plus the checkpoint and replan event family (the full 9-event family; this spec embeds 3 inline for immediate reference, the rest live in Plan 04).
- **EXEMPLAR-stepNPLAN.md** — canonical worked example; v14 implementations parse this file as a fixture and mutate it through every Mutability Matrix row to test the enforcer.

### Phase 402 carry-forward consumed

- **`tool.execute.before` as canonical block hook** — Phase 402 confirmed; PAP-05 enforcer attaches here.
- **`chat.params` as injection vector** — Phase 402 confirmed; PAP-01 injection flow uses it.
- **Plugin-as-thin-reporter** — Phase 402 carry-forward; the plugin posts proposed writes to the daemon, which authoritatively decides allow/reject.
- **Reinject payload XML body shape (CTX-06)** — Phase 402 owns the slot names (`<active_plan>`, `<upstream_provides>`, `<current_task_pointer>`); this spec adds runtime per-Step pointers.

### REQUIREMENTS amendments survey

**Surveyed:** the locked decisions in 403-CONTEXT.md were checked against v1 STP-* and PAP-* requirements for any extension that would warrant a REQUIREMENTS.md amendment. Findings:

| Decision | Extends a v1 REQ? | Amendment needed? |
|----------|-------------------|-------------------|
| `<discovered_threats>` append-only carve-out | Adds a sub-tag under `<threat_model>`. STP-03 enumerates body sections (`<threat_model>`, etc.) but does NOT enumerate sub-tags. | **No** — additive; sub-tags are spec-doc-level concerns. |
| `<options>` sub-tag for `<task type="checkpoint:decision">` | Adds a type-specific sub-tag. STP-04 enumerates COMMON `<task>` sub-tags (`<name>`, `<files>`, etc.); type-specific sub-tags are part of STP-05 task-type behavior. | **No** — STP-04 is non-exhaustive for type-specific sub-tags. |
| Mutability matrix locks every frontmatter field (PAP-03 originally only locked `must_haves` + `<verify>`) | **Extends PAP-03 wording** — the original requirement said only `must_haves.*` and `<verify>` blocks immutable; this spec locks all frontmatter + most body sections. | **Yes — but absorbed inline.** This spec's Section 5 IS the canonical mutability matrix; PAP-03 is satisfied as long as `must_haves.*` and `<verify>` are immutable (they are). The spec's broader lock list is a STRENGTHENING of PAP-03, not a contradiction; no separate amendment plan needed. **Documented:** the strengthening is justified by the Step-identity-fields rationale (changing them means it's a different Step). |
| Path confinement for `@`-resolution (security mitigation in PAP-02) | PAP-02 says "harness resolves all `@.planning/...` and `@-` references at injection time so the executor sees inlined content"; security stipulations are NOT in v1 REQ wording. | **No** — security mitigations supplement the requirement; not extension of the requirement's positive scope. |
| `auto+tdd` GSD-Test-Result trailer convention | STP-05 says "auto+tdd — autonomous with TDD cycle (RED→GREEN→REFACTOR commits required)". Trailer convention is implementation detail. | **No** — the trailer is the v41 mechanism; STP-05 wording covered. |

**Conclusion:** No standalone REQUIREMENTS amendment plan is needed for Phase 403. All decisions either satisfy v1 REQ wording or are absorbed inline as additive specifications.

### Security threat model for this spec

This spec introduces the injection flow, mutability enforcement, and audit-log mechanism. Threats considered:

**Path traversal via @-reference (PAP-02 security):**
Mitigation: realpath-based confinement. Resolver calls `pathlib.Path.resolve()` on each `@`-ref before checking the ancestor constraint. Symlinks are followed; the resolved path (after symlink expansion) must still be within the allowed subtrees. Fail-closed: injection aborted on violation.

**Diff-payload tampering in plan_edit event (PAP-04 security):**
Mitigation: `before_sha256` + `after_sha256` verified at replay time. The projector cannot apply a diff that doesn't match the pre-apply content hash. Mismatched hashes surface as a daemon-startup error. Even if an attacker injects a malformed `plan_edit` row into the SQLite event store, the replay verifier catches it at next daemon start.

**Immutability enforcement bypass via subprocess write (PAP-05 security):**
Mitigation: No-direct-write contract (Section 7). `tool.execute.before` is the canonical block hook; all Write/Edit calls to `*/stepNPLAN.md` must route through it. Subprocess shell calls that bypass the hook are out-of-policy. v14 MAY add a filesystem watcher as defense-in-depth. The contract is the routing, not the watcher.

**Audit-log original tampering (PAP-06 security):**
Mitigation: `state.step.plan_authored` row is append-only per v40 EVENT-TAXONOMY.md (SQLite rows are never updated or deleted). The `original_sha256` field provides a content integrity check. Replay verifier checks the hash on first use.

**`<discovered_threats>` carve-out masquerade (PAP-05 security):**
Mitigation: exact diff shape enforcement (Section 7). The enforcer checks that the diff ONLY adds `<threat>...</threat>` sub-elements at the end of `<discovered_threats>` — no removal, no text edit of existing children. The diff shape is normalized (whitespace-insensitive, tag-aware) before the check.

Forward-pointer: v14 security audit MUST verify each of these mitigations in the implementation. The above are spec-level contract statements; the implementation is the load-bearing artifact.

### Closing

v14 Build Kernel implements the @-reference resolver, the diff-the-proposed-write enforcer, the chat.params injection trampoline, the runtime-augmentation slot assembly, and the projector replay-verifier. Phase 404 (Boolean Proof Gate) consumes the immutability lock for `<verify>` blocks. Phase 405 (Deviation Rules & Subagent Management) consumes the autonomy-tier behavior for `checkpoint:*` task types (cross-referenced in STEP-PLAN-FORMAT.md Section 5). Phase 406 (Harness Architecture Rollup) cross-references the injection flow in the layered harness diagram.

---

*Spec: PLAN-AS-PROMPT.md — Phase 403 (Step/Task Decomposition & Plan-as-Prompt)*
*Authored: 2026-05-11*
*Requirements: PAP-01..PAP-06*
