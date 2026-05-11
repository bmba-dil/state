# Step Plan Format (Canonical, v41)

> **Phase:** 403
> **Status:** Canonical (v41)
> **Requirements covered:** STP-01..STP-08
> **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
> **Sibling specs:** PLAN-AS-PROMPT.md (injection + mutability), EXEMPLAR-stepNPLAN.md (canonical worked example).

A `stepNPLAN.md` is the harness-readable plan artifact for a single Step in the Build mode execution
pipeline. It is the executor's primary system prompt when `execute-slice` is running (PAP-01). The
YAML frontmatter block is Pydantic-validated with `extra="forbid"` — any unknown key is a hard
validation error, not a silent pass. The XML body carries the prose, tasks, threat model,
verification gates, and success criteria. The on-disk filename form is `stepNPLAN.md` (no dash, no
leading zeros) per the Phase 402 vocabulary carry-forward and the v40 ARTIFACT-CATALOG.md
confirmation (`stepNPLAN.md` is the canonical filename; `stepNN-PLAN.md` variants are rejected).

---

## Frontmatter Schema (STP-02)

The frontmatter block sits between two `---` delimiters at the top of the file. It is loaded with
`yaml.safe_load` and validated with `StepFrontmatter.model_validate(...)`. Any extra key raises a
`ValidationError`; any missing required key raises a `ValidationError`. The full field set is
declared once here; v14's StepPlan parser loads this module to construct the validator.

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal


class ArtifactCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    provides: str
    min_lines: int


class KeyLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_: str    # alias "from" — Python keyword collision
    to: str
    via: str
    pattern: str


class MustHaves(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truths: list[str]                            # bash/python assertions (verifiable per PRF-04)
    artifacts: list[ArtifactCheck]               # {path, provides, min_lines}
    key_links: list[KeyLink]                     # {from, to, via, pattern}


class StepFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: str                                   # e.g., "402"
    slice: str                                   # slice_id (slug form)
    step: str                                    # step_id (slug form, stable across replans)
    type: Literal["auto", "auto+tdd",
                  "checkpoint:human-verify",
                  "checkpoint:decision",
                  "checkpoint:human-action"]
    wave: int                                    # non-negative; v5 scheduler input
    depends_on: list[str]                        # same-Slice step_ids ONLY
    files_modified: list[str]                    # exact paths or globs
    autonomous: bool                             # back-compat with REQUIREMENTS wording
    requirements: list[str]                      # REQ-IDs (e.g., ["STP-01"])
    must_haves: MustHaves                        # nested model
```

### Field constraints

- **`autonomy` is NOT a Step frontmatter field.** Per DEV-06 + SUB-09, autonomy lives only on the
  Slice frontmatter; Steps inherit. Single precedence chain: milestone default → Slice override →
  done. No Step-level autonomy axis.

- **`autonomous` (bool) is a back-compat field only.** The operative autonomy tier is on the Slice.
  `autonomous: true` on a Step says "this Step does not require a human checkpoint by design" —
  information for tooling display, not a runtime gate.

- **`depends_on` lists same-Slice step_ids ONLY.** Cross-Slice deps belong to the Slice DAG
  (CTX-02 fresh-session-per-Slice abstraction must hold). Allowing cross-Slice Step deps would
  smuggle the Slice DAG into Step plans and break the fresh-session context boundary.

- **`files_modified` may be exact paths or globs** (planner picks; both forms valid). Glob
  expansion happens at the planner-validation stage, not at runtime.

- **`depends_on` cross-check (planner validation):** at the research-slice validation stage, the
  planner verifies `depends_on` is consistent with `<read_first>` references against upstream
  Steps' `provides:` blocks. Misalignment fails `N-VALIDATION.md` and forces a replan iteration.
  Reference: `workflow-docs-from-gsd-2/workflow-engine.md` §6 three-scope dependency model +
  Correction 2.

### Literal example (from EXEMPLAR-stepNPLAN.md)

From `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` (frontmatter, lines 10–46 —
the full YAML block between the two `---` delimiters):

```yaml
phase: "v14-1"
slice: "compaction-snapshot-schema"
step: "compaction-snapshot-schema-step-1"
type: "auto+tdd"
wave: 1
depends_on: []
files_modified:
  - "src/state_build/snapshot/compaction.py"
  - "tests/state_build/snapshot/test_compaction.py"
autonomous: true
requirements:
  - "CTX-05"
  - "CTX-06"

must_haves:
  truths:
    - "python3 -c 'from state_build.snapshot.compaction import CompactionSnapshot; print(CompactionSnapshot.model_config[\"extra\"])' prints 'forbid'."
    - "orjson round-trip: dumps→loads of a populated CompactionSnapshot is bit-identical to the original."
    - "All seven snapshot fields from CONTEXT-PROTOCOL.md are present (slice_id, step_id, task_id, session_id, active_plan_path, current_task_pointer, provides_blocks)."
  artifacts:
    - path: "src/state_build/snapshot/compaction.py"
      provides: "CompactionSnapshot Pydantic model + orjson serializer helpers"
      min_lines: 60
    - path: "tests/state_build/snapshot/test_compaction.py"
      provides: "Round-trip test + extra='forbid' rejection test + missing-field rejection test"
      min_lines: 80
  key_links:
    - from: "src/state_build/snapshot/compaction.py"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "Field set matches CompactionSnapshot schema specified in §5 (CTX-05)"
      pattern: "class CompactionSnapshot"
    - from: "tests/state_build/snapshot/test_compaction.py"
      to: "src/state_build/snapshot/compaction.py"
      via: "Test imports CompactionSnapshot for round-trip validation"
      pattern: "from state_build\\.snapshot\\.compaction import"
```

---

## XML Body Section Catalog (STP-03)

The XML body follows the closing `---` frontmatter delimiter. Each section is an XML-tagged block.
The ordering below is canonical — v14's StepPlan parser validates this order. Sections marked
**Immutable** are locked by the mutability matrix (see PLAN-AS-PROMPT.md §Mutability Matrix,
PAP-03). Sections marked **Mutable** may be refined by the executor as it learns. The hybrid
`<threat_model>` has a special append-only carve-out documented in Section 5.

### <objective>

**Purpose:** States the Step contract — what must be true when this Step is done — in 1–2
paragraphs. Written by the plan author at research-slice time. The executor reads this to orient
itself; it cannot change it (re-planning is required if the contract changes). **Immutable.**

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:

```xml
<objective>
Define and implement the `CompactionSnapshot` Pydantic model that the daemon emits to the event
store on every compaction event (intra-Slice or Slice-boundary). The on-the-wire shape is the
canonical reinject payload spec; v14 Build Kernel's compaction handler serializes this model via
orjson into the `state.slice.compacted` event row. The model enforces `extra="forbid"` at all
field boundaries so unknown keys fail fast at the daemon boundary rather than silently propagating
through the event store.

Without this model, downstream Phase 403 STEP-PLAN-FORMAT.md cannot demonstrate the
`must_haves.artifacts` shape on a realistic Pydantic file, and v14's compaction subsystem cannot
type-validate snapshot payloads at the daemon boundary. This Step is the first in the
`compaction-snapshot-schema` Slice and blocks the Layer-A persistence integration (CTX-05) and the
reinject payload assembly (CTX-06).
</objective>
```

### <execution_context>

**Purpose:** At-references to harness-bootstrap docs (workflow spec + summary template). Resolved at
injection time per PAP-02 (one-level inline + token cap). These are the harness playbook references
the executor uses to understand the execution protocol. **Immutable** (the bootstrap docs do not
change per-Step; the only valid edits are if the harness references a different workflow version).

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:

```xml
<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
(All `@`-references in this file resolve under repo root + `.planning/` per PAP-02 path-confinement rule.)
</execution_context>
```

### <context>

**Purpose:** At-references to project-level, spec-level, and sibling code files the executor needs
for background understanding. Resolved at injection time per PAP-02. **Mutable** — the executor may
add or remove `@`-refs as it discovers what additional context it needs. Every executor-added ref
emits a `plan_edit` event (PAP-04). The planner pre-populates 3–7 high-value refs; the executor
extends the list as needed.

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` (5 @-refs):

```xml
<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@src/state_core/schema.py
</context>
```

### <interfaces>

**Purpose:** Literal upstream code excerpts — the exact contracts from upstream artifacts that this
Step's code must conform to. The executor sees the exact contract without any codebase exploration
(STP-07 zero-codebase-exploration rule). These are verbatim copy-pastes from upstream source files
or spec documents, annotated with the source path and line range. **Immutable** — mutating
`<interfaces>` silently desyncs from the upstream artifact; if upstream genuinely changes, a replan
is required. The exception is PAP-06 stripping: when an upstream Step's `provides:` blocks are
already inlined in `<upstream_provides>`, the `<interfaces>` excerpt is replaced at injection time
with `<interfaces ref="upstream_provides[step-N]"/>` pointer (deduplication only; the contract
stays in-context).

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` (two upstream
excerpts):

```xml
<interfaces>
<!-- Upstream excerpts used by this Step. Executor must NOT re-derive these from the codebase (STP-07 zero-codebase-exploration). -->

Excerpt A — from `src/state_core/schema.py` (lines 239-265):
```python
# From src/state_core/schema.py (lines 239-265)
from pydantic import BaseModel, ConfigDict
from typing import Any, Literal

class EventEnvelope(BaseModel):
    """Generic event envelope — used for serialization and generic reads."""
    model_config = ConfigDict(extra="forbid")
    id: str = ""
    seq: int = 0
    aggregate_type: str = "arc"
    aggregate_id: str = ""
    type: str = ""
    data: dict[str, Any] = {}
```

Excerpt B — from `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §5 (CTX-05):
```python
class CompactionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slice_id: str
    step_id: str
    task_id: str | None
    session_id: str
    ...
```

Excerpts above are LITERAL upstream content. The executor must NOT re-derive these contracts
from the codebase (STP-07 zero-codebase-exploration).
</interfaces>
```

### <tasks>

**Purpose:** Container for one or more `<task>` blocks. Each `<task>` represents one discrete unit
of work within the Step. Tasks are executed sequentially by default; wave-parallelism is a Slice-
level concern (same-wave Steps run in parallel; tasks within a Step run in order). The `<tasks>`
container itself has no attributes. See Section 4 for the full `<task>` sub-tag specification.

### <threat_model>

**Purpose:** STRIDE-style threat register authored at design time (research-slice). Lists known
threats with mitigations so the executor sees the security context before writing code. The parent
`<threat_model>` block is **Immutable** (design-time locked). **Hybrid carve-out:** the
`<discovered_threats>` sub-tag is append-only at runtime — see Section 5 for the exact carve-out
semantic and enforcement rule. Forward-pointer to PAP-05 (PLAN-AS-PROMPT.md §Immutable-section
block) which specifies the diff-the-proposed-write enforcer.

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:

```xml
<threat_model>
## STRIDE Register

**Spoofing — malicious input forging a CompactionSnapshot with extra fields.**
Mitigation: `extra="forbid"` on `CompactionSnapshot` and all helper models rejects unknown keys at
the Pydantic validation boundary.

**Tampering — replay attack with a stale snapshot from a prior session.**
Mitigation: `session_id` and `slice_id` fields are validated against daemon state at rehydrate
time.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>
```

### <verification>

**Purpose:** Slice-level pre-commit bash one-liners that gate task → Step → Slice advancement. Run
after the last task in the Step completes and before the Slice wrap. Every command must exit 0 for
the gate to pass (PRF-03, PRF-07). **Immutable** — the gate is locked per PAP-03; mutating it means
the proof contract changed and a re-plan is required.

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:

```xml
<verification>
<!-- Slice-level pre-commit checks — all must pass before the Slice closes. -->

```bash
# 1. extra="forbid" enforced at import time
python3 -c "from state_build.snapshot.compaction import CompactionSnapshot; assert CompactionSnapshot.model_config['extra'] == 'forbid', 'extra forbid missing'"

# 2. Full test suite green
pytest tests/state_build/snapshot/test_compaction.py -q

# 3. Implementation file meets minimum line count
wc -l src/state_build/snapshot/compaction.py | awk '{exit ($1 < 60)}'

# 4. Test file meets minimum line count
wc -l tests/state_build/snapshot/test_compaction.py | awk '{exit ($1 < 80)}'

# 5. Mode isolation — no teach-mode imports
test "$(grep -c 'state_teach' src/state_build/snapshot/compaction.py)" -eq 0
```
</verification>
```

### <success_criteria>

**Purpose:** Plain-language restatement of the `must_haves.truths` proof conditions. Written for
human readability alongside the machine-checkable truths. **Immutable** — step contract; if criteria
change, re-plan. Bullets should be phrased as assertions that are also checkable by the verifier.

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:

```xml
<success_criteria>
- `CompactionSnapshot` is importable from `state_build.snapshot.compaction` and `model_config["extra"] == "forbid"`.
- orjson round-trip (dumps with `OPT_SORT_KEYS | OPT_NAIVE_UTC`, then `model_validate_json`) produces a value that equals the original snapshot instance.
- All seven required fields from CONTEXT-PROTOCOL.md §5 (CTX-05) are present in the model.
- Passing 5 / 5 tests; no teach-mode (`state_teach`) imports in any implementation file touched by this Step.
</success_criteria>
```

### <output>

**Purpose:** Post-Step deliverable instruction — where to create the Step SUMMARY.md and what to
include in its `provides:` block. This is the canonical handoff spec: downstream Steps read the
SUMMARY to find what this Step produced. **Immutable** (the output path is part of the step
contract).

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:

```xml
<output>
After completion, create `.planning/milestones/v14/phases/v14-1/slices/compaction-snapshot-schema/compaction-snapshot-schema-step-1-SUMMARY.md`
with a `provides:` block listing the exported symbols (`CompactionSnapshot`, `ProvidesBlock`,
`TaskPointer`, `VerifyResult`, `snapshot_to_bytes`, `snapshot_from_bytes`) and the verified
minimum-line counts for both files. This SUMMARY feeds the `<upstream_provides>` slot of the next
Step's reinject payload (CTX-06).
</output>
```

---

## <task> Sub-tag Specification (STP-04)

Each `<task>` block within `<tasks>` declares a discrete unit of work. The table below is
exhaustive for the common sub-tags; type-specific sub-tags (like `<options>` for
`checkpoint:decision`) are documented in Section 5.

| Sub-tag / attribute | Required? | Mutability | Definition |
|---------------------|-----------|------------|------------|
| `type` (attribute on `<task>`) | required | **immutable** (changing it means it's a different task) | Literal: `auto` \| `auto+tdd` \| `checkpoint:human-verify` \| `checkpoint:decision` \| `checkpoint:human-action`. See Section 5. |
| `tdd` (attribute) | optional, defaults `false` | immutable | Boolean. When `true`, harness enforces RED-before-GREEN per Section 5 auto+tdd behavior. |
| `<name>` | required | immutable | Human-readable task name (used in events + SUMMARY.md). |
| `<files>` | required | **immutable** (task contract) | Newline-delimited file paths the task may write. Empty for decision-only tasks. |
| `<read_first>` | required | mutable | List of `path lines N-M` entries the executor must read before writing. STP-08 contract — see Section 6. |
| `<action>` | required | mutable | Step-by-step prose with code blocks. Executor refines as it learns. |
| `<verify>` (with nested `<automated>`) | required | **immutable** (gate per PAP-03) | Bash one-liner that runs in <60s. Exit code 0 = pass; non-zero = fail. PRF-02 task gate. |
| `<acceptance_criteria>` | required | **immutable** (task contract) | Bullet list of grep-verifiable conditions. Each condition checkable with grep, file read, or CLI output. |
| `<done>` | required | **immutable** (task contract) | 1-line measurable acceptance state. |
| `<options>` (only for `<task type="checkpoint:decision">`) | required when type=checkpoint:decision | **immutable** | Container of 2–4 `<option>` elements; each option has `name`, `pros`, `cons` attributes. See Section 5 checkpoint:decision behavior. |

### Literal example (from EXEMPLAR-stepNPLAN.md)

The following is Task 2 from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` —
the `auto`-type implementation task. It exercises every required sub-tag without the auto+tdd or
checkpoint complexity:

```xml
<task type="auto">
  <name>Task 2: Implement CompactionSnapshot Pydantic model to make tests GREEN</name>
  <files>src/state_build/snapshot/compaction.py</files>

  <read_first>
    - tests/state_build/snapshot/test_compaction.py lines 1-80 (the RED test file from Task 1 — these are the load-bearing acceptance assertions)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md lines 85-200 (CompactionSnapshot field types, orjson flag pins, helper-type sketches for ProvidesBlock/TaskPointer/VerifyResult)
    - src/state_core/schema.py lines 239-265 (EventEnvelope — the extra="forbid" Pydantic pattern to mirror)
  </read_first>

  <action>
    - Create `src/state_build/snapshot/` directory with an empty `__init__.py`.
    - Create `src/state_build/snapshot/compaction.py` with:
      1. Helper Pydantic models (in order): `ProvidesBlock`, `TaskPointer`, `VerifyResult`.
         Each uses `ConfigDict(extra="forbid")`.
      2. `CompactionSnapshot(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and
         the full field set from CONTEXT-PROTOCOL.md §5 (CTX-05).
      3. Two module-level helpers:
         - `snapshot_to_bytes(snapshot: CompactionSnapshot) -> bytes`
         - `snapshot_from_bytes(data: bytes) -> CompactionSnapshot`
    - Verify mode isolation: the file MUST NOT import from the teach-mode subsystem.
    - Run `pytest tests/state_build/snapshot/test_compaction.py -x` — all tests must pass.
    - Commit with message: `feat(compaction-snapshot-schema-step-1): implement CompactionSnapshot Pydantic model`
      and trailer `GSD-Test-Result: PASS`.
  </action>

  <verify>
    <automated>pytest tests/state_build/snapshot/test_compaction.py -x</automated>
  </verify>

  <acceptance_criteria>
    - `src/state_build/snapshot/compaction.py` exists with ≥60 lines.
    - All 5 tests in `test_compaction.py` pass (pytest exits 0).
    - `grep -q 'extra="forbid"' src/state_build/snapshot/compaction.py` exits 0.
    - `grep -c "state_teach" src/state_build/snapshot/compaction.py` returns 0.
    - `git log -1 --format=%B | grep -q "GSD-Test-Result: PASS"` exits 0.
  </acceptance_criteria>

  <done>GREEN phase complete. CompactionSnapshot is importable, all field constraints enforced, orjson round-trip confirmed identity-preserving.</done>
</task>
```

### Note on STP-04 enumeration

403-CONTEXT.md's locked decisions extend STP-04 with the `<options>` sub-tag (specific to
`checkpoint:decision` tasks). This is additive — STP-04's "each `<task>` declares: …" list is
non-exhaustive for type-specific sub-tags. No REQUIREMENTS amendment is required because STP-04
covers the COMMON sub-tags; type-specific sub-tags (like `<options>`) are part of the task-type
behavior spec (STP-05). The `<discovered_threats>` sub-tag (under `<threat_model>`) is similarly
additive to STP-03.

---

## Five-Type Task Taxonomy (STP-05)

Each task type drives a distinct harness behavior. The behaviors below are verbatim from
403-CONTEXT.md `<decisions>` Task-type behaviors subsection. v14 implements these behaviors in
`state_build.harness.task_dispatcher`.

### auto

**Harness action:** Fully autonomous; harness allows all writes within `files_modified` allowlist;
on completion, gate runs (PRF-02 task `<verify>` + `<acceptance_criteria>`).

**Gate/checkpoint mechanism:** After the task's `<action>` completes, harness runs
`<verify><automated>` as a subprocess. Exit code 0 → task marked done, next task unlocked. Non-zero
→ gate failure; PRF-06 strike escalation begins.

**Autonomy interaction (DEV-05):** All three tiers (`--tiered`, `--full-yolo`, `--conservative`)
permit `auto` tasks without stopping. The autonomy tier only differentiates checkpoint behavior.

### auto+tdd

**Harness action:** RED-before-GREEN enforcement via git-log + `tool.execute.before`:

- Harness consults git log for the current task's commit chain.
- Rejects writes to non-test files until at least one commit exists with a `test:` or `red:` prefix
  AND a captured failing-test artifact (e.g., pytest exit code != 0 stored in commit trailer
  `GSD-Test-Result: FAIL`).
- After the first commit with `GSD-Test-Result: PASS` (GREEN), refactor commits unrestricted within
  `files_modified`.
- Pure-machine, replayable. Aligns with `file-tracking.md` Correction 3: GSD metadata in commit
  trailers (`GSD-Task: <sliceId>/<taskId>`); state extends with `GSD-Test-Result: FAIL|PASS`.

**Gate/checkpoint mechanism:** Same as `auto` after GREEN is reached. Before GREEN, any Write/Edit
to non-test files is blocked by `tool.execute.before` with the message "RED phase not complete —
commit a failing test first."

**Autonomy interaction (DEV-05):** All three tiers permit `auto+tdd` tasks without stopping. The
RED-before-GREEN check is mechanical, not autonomy-gated.

### checkpoint:human-verify

**Harness action:** Pause and surface the current state for human visual inspection. Executor has
already produced output; human confirms it looks correct.

**Gate/checkpoint mechanism:** Autonomy-tiered behavior per DEV-05 literal:

- `--tiered` (default): auto-approves (visual sanity check passed).
- `--full-yolo`: auto-approves.
- `--conservative`: stops; opencode `question` tool rendered.

Auto-approval emits `state.step.checkpoint_auto_resolved` event with `tier`, `task_id`,
`selection="auto-approved"`. Event schema: see STEP-EVENTS.md (Plan 04 / Phase 403).

**Autonomy interaction:** `--conservative` is the only tier that stops for human-verify. Both
`--tiered` and `--full-yolo` auto-approve and continue. Use `checkpoint:human-action` if a human
stop is always required.

### checkpoint:decision

**Harness action:** Surface a bounded decision list and record the human (or auto) selection before
proceeding.

**Gate/checkpoint mechanism:** Autonomy-tiered behavior per DEV-05 literal:

- `--tiered`: stops.
- `--full-yolo`: auto-picks option 1 deterministically.
- `--conservative`: stops.

The option list is authored by the plan author in an `<options>` sub-tag of the `<task>` block.
Required: 2–4 named options each with `pros` and `cons` attributes.

Harness renders via opencode `question` tool with the labeled list. Under `--full-yolo`, picks
first option deterministically.

`<options>` is **immutable** (mutability matrix in PLAN-AS-PROMPT.md). Executor cannot
add/remove/edit options at runtime.

**No "Other" free-text affordance** under build-mode strictness — diverges from AskUserQuestion's
default. Decisions are bounded.

Canonical example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`
(Task 3 `<options>` block):

```xml
<task type="checkpoint:decision">
  <name>Task 3: Pick orjson serialization flag for datetime handling: OPT_NAIVE_UTC or OPT_UTC_Z</name>
  <files></files>

  <options>
    <option name="OPT_NAIVE_UTC"
            pros="naive timestamps without TZ suffix; smallest payload; deterministic replay per PROJECT.md no-datetime.now() rule; CONTEXT-PROTOCOL.md canonical pin"
            cons="ambiguous on cross-host replay without UTC-only convention enforcement; reader must assume UTC"/>
    <option name="OPT_UTC_Z"
            pros="explicit Z suffix; unambiguous ISO-8601; safe across hosts and timezones without convention"
            cons="3 extra bytes per datetime field; payload size increases; diverges from CONTEXT-PROTOCOL.md canonical pin (requires amending the spec)"/>
  </options>
  ...
</task>
```

**Autonomy interaction:** `--tiered` and `--conservative` both stop. Only `--full-yolo` auto-picks
option 1 deterministically. This is the only task type where `--tiered` stops (unlike
`checkpoint:human-verify` which `--tiered` auto-approves).

### checkpoint:human-action

**Harness action:** A step that requires a physical human action (e.g., enter an MFA code, approve
an OAuth flow, push a button in an external UI) that cannot be automated.

**Gate/checkpoint mechanism:** Autonomy-tiered behavior per DEV-05 literal:

- ALL tiers stop. Harness surfaces via opencode `question` tool with the action prompt; resumes
  when human confirms completion.
- Emits `state.step.checkpoint_human_action_pending` on entry,
  `state.step.checkpoint_human_action_resolved` on resume.

**Autonomy interaction:** The one task type where even `--full-yolo` stops. Physical human
actions cannot be automated by definition. Use sparingly — each `checkpoint:human-action` breaks
the automated pipeline.

### `<discovered_threats>` append-only carve-out

The `<threat_model>` block is design-time-locked (immutable per the mutability matrix). However,
the executor MAY APPEND newly discovered threats into a `<discovered_threats>` sub-tag during
execution — write-only-append. The exact diff shape that counts as "append-only": ONLY new
`<threat>...</threat>` sub-elements added at the end of `<discovered_threats>`; no removal of
existing children, no edit of existing children's text. Any other diff touching `<threat_model>`
(including editing an existing threat's text) is rejected by the `tool.execute.before` hook with
a `plan_edit_blocked` event. The carve-out allows observed-during-execution security findings to
land in the artifact rather than getting lost. Forward-pointer to PAP-05 (PLAN-AS-PROMPT.md
§Immutable-section block) which specifies the diff-the-proposed-write enforcer that allows this
carve-out.

---

## STP-07 / STP-08 Contracts (Zero-Codebase-Exploration)

### STP-07 — `<interfaces>` literal-excerpt rule

**Rule statement:** "The `<interfaces>` block contains literal code excerpts from upstream
artifacts so the executor needs **zero codebase exploration** for upstream context."

The plan author reads the upstream artifact at research-slice time and pastes the relevant excerpt
verbatim, annotated with source path and line range. The executor trusts this excerpt — it does not
open the file to verify. If the upstream artifact has changed, that is a replan trigger (the
`<interfaces>` excerpt is immutable; a stale excerpt is a spec violation, not an executor
problem).

Example from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`:

```xml
<interfaces>
<!-- Upstream excerpts used by this Step. Executor must NOT re-derive these from the codebase (STP-07 zero-codebase-exploration). -->

Excerpt A — from `src/state_core/schema.py` (lines 239-265):
```python
class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = ""
    seq: int = 0
    aggregate_type: str = "arc"
    aggregate_id: str = ""
    type: str = ""
    data: dict[str, Any] = {}
```

Excerpts above are LITERAL upstream content. The executor must NOT re-derive these contracts
from the codebase (STP-07 zero-codebase-exploration).
</interfaces>
```

**Counterexamples (rejection cases):**

- `<interfaces>see the existing schema for the field set</interfaces>` — REJECT (vague pointer; no
  literal excerpt provided; executor must explore to find the schema)

- `<interfaces>refer to the prior Step's output for the contract</interfaces>` — REJECT (forces
  exploration; the prior Step's output may not be in context)

- `<interfaces ref="upstream_provides[step-N]"/>` at a Step where step-N is NOT yet in
  upstream_provides — REJECT (PAP-06 stripping precondition not met; the pointer is dangling)

- `<interfaces><!-- TBD --></interfaces>` — REJECT (placeholder; STP-07 violation; a non-empty
  `<interfaces>` must contain literal excerpts; if there are genuinely no upstream contracts to
  cite, use `<interfaces><!-- first Step in Slice; no upstream contracts --></interfaces>` with a
  meaningful comment)

### STP-08 — `<read_first>` exact-files-with-line-ranges rule

**Rule statement:** "`<read_first>` specifies exact files and line ranges per task — never 'explore
the codebase.'"

The `<read_first>` entries are a reading list the executor follows in order before writing anything.
Each entry must name a specific file and a specific line range (or the whole file). The planner
authors these at research-slice time, having already read the referenced files. The executor reads
them verbatim — no additional exploration is needed or permitted before starting the task.

Example `<read_first>` block from `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md`
(Task 1):

```xml
<read_first>
  - tests/conftest.py lines 1-40 (pytest fixtures — session_id factories and tmp_path usage)
  - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md lines 85-200 (CompactionSnapshot field definitions and round-trip example with orjson flag pins)
  - src/state_core/schema.py lines 239-265 (EventEnvelope shape — the extra="forbid" pattern to mirror)
</read_first>
```

**Counterexamples (rejection cases):**

- `<read_first>explore the codebase</read_first>` — REJECT (vague; no specific file or line range;
  this is exactly what STP-08 prohibits)

- `<read_first>relevant test files</read_first>` — REJECT (vague; "relevant" is undefined; no path,
  no line range)

- `<read_first>tests/</read_first>` — REJECT (directory reference with no specific file or line
  range; the executor would need to explore the directory to find what to read)

- `<read_first>src/state_core/schema.py</read_first>` — REJECT (path without line range; the
  required form is `src/state_core/schema.py lines 1-40` or
  `src/state_core/schema.py (full file)`)

- `<read_first>check the relevant files in the snapshot module</read_first>` — REJECT (exploratory
  instruction; equivalent to "explore the codebase")

**Allowed forms:**
- `path lines N-M` — read lines N through M inclusive.
- `path lines N-M and lines P-Q` — read two non-contiguous ranges.
- `path (full file)` — read the entire file; used when the file is short or the executor needs the
  whole context.

---

## Granularity Selection Algorithm (STP-06)

The plan-slice stage auto-selects Step granularity for each Slice based on deterministic inputs.
The algorithm is a fixed table lookup — no LLM judgment, no formula tuning. Same inputs → same
output on every invocation (idempotent). This is load-bearing for replan determinism (PAP-04
audit-log clarity requires that replans with identical inputs produce identical plans).

### Inputs (deterministic)

1. **Slice scope token estimate** — sum of input artifact sizes (`DESIGN.md` + `RESEARCH.md` +
   `PATTERNS.md`) tokenized with a fixed tokenizer. Pin the tokenizer choice: **`tiktoken
   cl100k_base` is recommended; chars/4 fallback per CTX-08 rule**. This spec ships with
   `tiktoken cl100k_base` as the canonical choice; v14 implementations may pin a Python-native
   alternative if `tiktoken` package availability is constrained.

2. **`files_modified` union count** — distinct files the Slice will touch, computed from the
   planner's preliminary file map before Step assignment.

3. **`provides:` blocks count** — distinct upstream→downstream artifact handoffs the Slice will
   produce; maps to DAG edge count.

**LLM-counted task estimates are explicitly REJECTED** — they violate STP-06's "deterministic
function" wording. Replan determinism is load-bearing for PAP-04 audit-log clarity (see
PLAN-AS-PROMPT.md).

### Algorithm (table-driven, bucketed thresholds)

```text
granularity(scope_tokens, files, provides) -> "coarse" | "standard" | "fine":
  if scope_tokens ≤ 30_000 AND files ≤ 3 AND provides ≤ 2:
    return "coarse"        # 1–2 Steps
  elif scope_tokens ≤ 80_000 AND files ≤ 6 AND provides ≤ 5:
    return "standard"      # 2–3 Steps
  else:
    return "fine"          # 3–5 Steps
```

### Step count (collapsing the range to a single integer)

- **coarse** → 2 if `scope_tokens > 15_000`, else 1.
- **standard** → 3 if `scope_tokens > 50_000` OR `files > 4`, else 2.
- **fine** → ceil(`provides` / 2), clamped to [3, 5].

Match REQUIREMENTS literal ranges (1–2 / 2–3 / 3–5). Reproducible, debuggable, easy to tune.
Inspired by gsd-2 quality-enforcement bucketed gate registries
(`workflow-docs-from-gsd-2/quality-enforcement.md` §1 five-pipeline taxonomy) — fixed lookup
tables beat formula tuning for spec docs.

---

## step_id Stable-Hash Rule + Replan Determinism

### step_id derivation

- **step_ids derived from a stable hash:** `step_id = slugify(slice_id) + '-step-' + ordinal`
- **ordinal:** position after sorting candidate Steps by (min `files_modified` path
  lexicographically, then `provides` count desc).

**Worked example using EXEMPLAR's step_id:** The EXEMPLAR's step is
`compaction-snapshot-schema-step-1` — slice slug `compaction-snapshot-schema` + `-step-` +
ordinal `1` (first in sort order). If a sibling step in the same slice is added later, sorting by
min `files_modified` path lexicographically determines its ordinal. A second Step that writes
`tests/state_build/snapshot/test_compaction_v2.py` would sort after `src/state_build/...` (t >
s), giving it ordinal `2` and step_id `compaction-snapshot-schema-step-2`.

### Replan determinism

- **Same inputs → same Step count + same step_ids.** Replan with identical inputs reproduces the
  same plan exactly (idempotent at the file level).

- **Replan with changed inputs** recomputes granularity and emits `state.step.renamed` /
  `state.step.added` / `state.step.removed` events for diff-replay continuity. Schemas: see
  STEP-EVENTS.md (Plan 04 / Phase 403).

- **Locks held by PAP-03** (`must_haves`, `<verify>`) survive replan when step_id is unchanged;
  if step_id changes (input change forced rename), the new Step inherits authored content but
  `must_haves` are re-authored fresh (no carry-over of stale gates).

### Step-id collision strategy

When inputs produce duplicate slugs across Slices, the slice_id slug prefix prevents collision by
construction. Cross-Slice step_id collisions are not possible because
`step_id = slugify(slice_id) + '-step-' + ordinal` and slice_ids are unique within the milestone
scope.

---

## Planner Validation Hooks

This section enumerates the validation checks the research-slice planning + validation pipeline
runs against authored stepNPLAN.md files. v15 Build Core Commands implements these checks; v41
specifies them. Validation runs after the plan-slice authoring stage and before execute-slice is
dispatched. Failure at any check emits `state.slice.validation_failed` and forces a replan
iteration — no partial execution from a validation-failed plan.

- **Pydantic load** — `StepFrontmatter.model_validate(yaml.safe_load(frontmatter))` raises
  `ValidationError` on missing required keys, unknown extras (`extra="forbid"`), or wrong types.
  Failure: planner emits `state.slice.validation_failed`; replan-iteration triggered.

- **`depends_on` IO cross-check** — verify each `depends_on[i]` step_id exists in the same
  Slice; verify `<read_first>` references resolve against upstream Steps' `provides:` blocks.
  Reference: `workflow-docs-from-gsd-2/workflow-engine.md` §6 three-scope dependency model +
  Correction 2.

- **DAG cycle detection** — at the planner-validation stage, NOT runtime. State's Steps are
  pre-planned, so runtime cycle detection (gsd-2's `reactive-graph.ts:detectDeadlock`) is not
  needed; cycles fail before execute-slice ever spawns.

- **`files_modified` distinctness** — same-Wave Steps in the same Slice must not share files
  (parallel-safe). Sequential same-Slice Steps may share files via depends_on edge (later Step's
  writes are gated on earlier Step's gate-pass).

- **`<read_first>` line-range form** — every `<read_first>` entry matches
  `^.+ (lines \d+-\d+|\(full file\))$`. STP-08 enforcement.

- **`<interfaces>` non-empty (when depends_on non-empty)** — STP-07 contract; first-Step
  `<interfaces>` may be empty (no upstream).

- **`<verify><automated>` non-empty** — every task carries an automated verify command (Nyquist
  rule).

- **`<options>` cardinality (checkpoint:decision tasks)** — 2 ≤ count ≤ 4.

- **Task type ↔ structure consistency** — `<task type="auto+tdd">` MUST have `tdd="true"`
  attribute (back-compat); `<task type="checkpoint:decision">` MUST have `<options>` block.

---

## Cross-references

- **Sibling spec — mutability matrix:** `PLAN-AS-PROMPT.md` §Mutability Matrix (PAP-03) defines
  which sections this format declares mutable vs. immutable. This format spec marks each section's
  mutability inline; PLAN-AS-PROMPT.md authoritatively rolls them up + specifies the runtime
  enforcer.

- **Sibling spec — events:** `STEP-EVENTS.md` (Plan 04) defines the Pydantic schemas for
  `state.step.plan_authored`, `state.step.plan_edit`, `state.step.plan_edit_blocked`,
  `state.step.checkpoint_auto_resolved`, `state.step.checkpoint_human_action_pending`,
  `state.step.checkpoint_human_action_resolved`, `state.step.renamed`, `state.step.added`,
  `state.step.removed`.

- **Worked example:** `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` is the
  canonical hand-authored worked example; v14 implementations use it as a parser test fixture.

- **Phase 402 carry-forward:** filename form `stepNPLAN.md` (no dash, no leading zeros) is locked
  by 402-CONTEXT.md + v40 ARTIFACT-CATALOG.md; reinject body XML shape compatibility is locked by
  402's CONTEXT-PROTOCOL.md.

- **v40 baseline:** `state.build.harness.*` MUST NOT import `state.teach.*` (PROJECT.md cardinal
  rule). This spec is Build-mode only.

v14 Build Kernel implements the StepPlan parser, planner-validation hook chain, granularity
algorithm, and task-type behavior dispatch from this spec. v15 Build Core Commands implements the
research-slice multi-stage pipeline that produces stepNPLAN.md files (planning + validation stages
cited above). Phase 404 consumes the must_haves frontmatter sub-block schema. Phase 405 consumes
the `<options>` sub-tag and autonomy-tier interactions. Phase 406 cross-references all of the above
in the layered harness diagram.

