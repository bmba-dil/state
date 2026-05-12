<!--
  EXEMPLAR-stepNPLAN.md — canonical worked example.
  Owned by: Phase 403 (Step/Task Decomposition & Plan-as-Prompt).
  Subject: Implement CompactionSnapshot Pydantic model (notional v14 Build Kernel Step).
  Cited by: STEP-PLAN-FORMAT.md (literal excerpts) and PLAN-AS-PROMPT.md (literal excerpts).
  v14 implementations may diverge from specifics, but the SHAPE is the contract.
  Build-mode only. No teach-mode module imports permitted.
-->

---
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
---

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

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
(All `@`-references in this file resolve under repo root + `.planning/` per PAP-02 path-confinement rule.)
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@src/state_core/schema.py
</context>

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
    id: str = ""                        # ULID; validated via field_validator when non-empty
    seq: int = 0                        # per-aggregate monotonic sequence number
    aggregate_type: str = "arc"         # which aggregate this event belongs to
    aggregate_id: str = ""              # ID of the aggregate instance (e.g. arc-01, step-17.3)
    type: str = ""                      # event type string, e.g. "state.step.verify_passed"
    data: dict[str, Any] = {}
```

Excerpt B — from `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §5 (CTX-05):
```python
# From .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md §5 (CompactionSnapshot)
from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict

class CompactionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slice_id: str
    step_id: str
    task_id: str | None              # None if compaction fires between tasks
    session_id: str                  # session being compacted
    prior_session_id: str | None     # set on Slice-boundary spawn
    summary: str                     # markdown digest, ≤8KB; verbatim
    first_kept_entry_id: str         # event-store row id of first non-summarized entry
    tokens_before: int               # telemetry: token count at trigger
    trigger: Literal["manual", "threshold", "overflow"]
    from_hook: bool                  # True if extension hook initiated
    worktree_path: Path
    provides_blocks: list            # list[ProvidesBlock] — helper type in same module
    active_plan_path: Path           # current stepNPLAN.md
    current_task_pointer: object | None   # TaskPointer | None
    last_verify_result: object | None     # VerifyResult | None
    created_at: datetime             # UTC, ISO-8601; set by daemon at snapshot time
```

Excerpts above are LITERAL upstream content. The executor must NOT re-derive these contracts from the codebase (STP-07 zero-codebase-exploration).
</interfaces>

<tasks>

<task type="auto+tdd" tdd="true">
  <name>Task 1: Write failing tests for CompactionSnapshot round-trip and extra='forbid'</name>
  <files>tests/state_build/snapshot/test_compaction.py</files>

  <read_first>
    - tests/conftest.py lines 1-40 (pytest fixtures — session_id factories and tmp_path usage)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md lines 85-200 (CompactionSnapshot field definitions and round-trip example with orjson flag pins)
    - src/state_core/schema.py lines 239-265 (EventEnvelope shape — the extra="forbid" pattern to mirror)
  </read_first>

  <action>
    - Create `tests/state_build/snapshot/` directory with an empty `__init__.py`.
    - Create `tests/state_build/snapshot/test_compaction.py` with the following test cases:
      1. `test_round_trip_identity` — construct a fully-populated `CompactionSnapshot`, serialize
         with `orjson.dumps(snapshot.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS | orjson.OPT_NAIVE_UTC)`,
         deserialize with `CompactionSnapshot.model_validate_json(payload)`, assert `restored == snapshot`.
      2. `test_extra_field_rejected` — assert that `CompactionSnapshot(**{valid_fields, "unknown_field": 1})`
         raises `pydantic.ValidationError`.
      3. `test_missing_required_field_rejected` — assert that `CompactionSnapshot()` (no args) raises
         `pydantic.ValidationError` listing the required fields.
      4. `test_task_id_none_allowed` — construct snapshot with `task_id=None`; no exception.
      5. `test_trigger_literal_validated` — assert `CompactionSnapshot(**{..., "trigger": "bogus"})` raises
         `pydantic.ValidationError` (Literal enforcement).
    - Do NOT import from `state_build.snapshot.compaction` yet — the module does not exist;
      imports will fail at collection time. This intentional import failure is the RED artifact.
    - Run `pytest tests/state_build/snapshot/test_compaction.py -x 2>&1 | tee /tmp/red.log`.
    - Confirm pytest exits non-zero. Capture the exit code.
    - Commit with message: `test(compaction-snapshot-schema-step-1): add failing tests for CompactionSnapshot`
      and commit trailer `STATE-Test-Result: FAIL`.
  </action>

  <verify>
    <automated>pytest tests/state_build/snapshot/test_compaction.py -x 2>&1 | tee /tmp/red.log; grep -q "FAILED\|ERROR\|ImportError\|ModuleNotFoundError" /tmp/red.log</automated>
  </verify>

  <acceptance_criteria>
    - Test file `tests/state_build/snapshot/test_compaction.py` exists with ≥80 lines.
    - pytest exits non-zero (RED) — collection error or test failures confirm the module is absent.
    - `git log -1 --format=%B` shows commit with `test:` prefix and trailer `STATE-Test-Result: FAIL`.
  </acceptance_criteria>

  <done>RED phase complete; failing tests captured and committed. The implementation Step (Task 2) may now proceed.</done>
</task>

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
         the full field set from CONTEXT-PROTOCOL.md §5 (CTX-05):
         `slice_id`, `step_id`, `task_id`, `session_id`, `prior_session_id`, `summary`,
         `first_kept_entry_id`, `tokens_before`, `trigger`, `from_hook`, `worktree_path`,
         `provides_blocks`, `active_plan_path`, `current_task_pointer`, `last_verify_result`,
         `created_at`.
      3. Two module-level helpers:
         - `snapshot_to_bytes(snapshot: CompactionSnapshot) -> bytes` — wraps
           `orjson.dumps(snapshot.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS | orjson.OPT_NAIVE_UTC)`.
         - `snapshot_from_bytes(data: bytes) -> CompactionSnapshot` — wraps
           `CompactionSnapshot.model_validate_json(data)`.
    - Verify mode isolation: the file MUST NOT import from the teach-mode subsystem. Run
      `grep -n "state_teach" src/state_build/snapshot/compaction.py` — must return nothing.
    - Run `pytest tests/state_build/snapshot/test_compaction.py -x` — all tests must pass.
    - Commit with message: `feat(compaction-snapshot-schema-step-1): implement CompactionSnapshot Pydantic model`
      and trailer `STATE-Test-Result: PASS`.
  </action>

  <verify>
    <automated>pytest tests/state_build/snapshot/test_compaction.py -x</automated>
  </verify>

  <acceptance_criteria>
    - `src/state_build/snapshot/compaction.py` exists with ≥60 lines.
    - All 5 tests in `test_compaction.py` pass (pytest exits 0).
    - `grep -q 'extra="forbid"' src/state_build/snapshot/compaction.py` exits 0.
    - `grep -c "state_teach" src/state_build/snapshot/compaction.py` returns 0 (no teach-mode imports; mode isolation).
    - `git log -1 --format=%B | grep -q "STATE-Test-Result: PASS"` exits 0.
  </acceptance_criteria>

  <done>GREEN phase complete. CompactionSnapshot is importable, all field constraints enforced, orjson round-trip confirmed identity-preserving.</done>
</task>

<task type="checkpoint:decision">
  <name>Task 3: Pick orjson serialization flag for datetime handling: OPT_NAIVE_UTC or OPT_UTC_Z</name>
  <files></files>

  <read_first>
    - src/state_build/snapshot/compaction.py lines 1-60 (Task 2 output — the orjson call site that will be updated)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md lines 136-155 (Round-trip example — canonical flag pin `OPT_SORT_KEYS | OPT_NAIVE_UTC`; rationale: naive timestamps, no TZ suffix, deterministic replay)
  </read_first>

  <options>
    <option name="OPT_NAIVE_UTC"
            pros="naive timestamps without TZ suffix; smallest payload; deterministic replay per PROJECT.md no-datetime.now() rule; CONTEXT-PROTOCOL.md canonical pin"
            cons="ambiguous on cross-host replay without UTC-only convention enforcement; reader must assume UTC"/>
    <option name="OPT_UTC_Z"
            pros="explicit Z suffix; unambiguous ISO-8601; safe across hosts and timezones without convention"
            cons="3 extra bytes per datetime field; payload size increases; diverges from CONTEXT-PROTOCOL.md canonical pin (requires amending the spec)"/>
  </options>

  <action>
    Render the choice via opencode `question` tool with the labeled option list. Under `--full-yolo`
    autonomy the harness picks `option name="OPT_NAIVE_UTC"` deterministically (first option, and
    the CONTEXT-PROTOCOL.md canonical pin). Under `--tiered` or `--conservative`, the harness stops
    and surfaces the labeled list to the human. The selection is recorded via event; no source file
    change is required because Task 2 already committed `OPT_NAIVE_UTC` as the default.
  </action>

  <verify>
    <automated>echo "checkpoint:decision is gate-resolved at runtime by harness; no automated verification at task level"</automated>
  </verify>

  <acceptance_criteria>
    - `checkpoint_auto_resolved` or `checkpoint_human_action_resolved` event emitted with `selection` field set to one of the option `name` attributes.
  </acceptance_criteria>

  <done>Decision recorded; emit `state.step.checkpoint_auto_resolved` (autonomy=full-yolo) or `state.step.checkpoint_human_action_resolved` (autonomy=tiered) event with `selection` set to one of the option `name` attributes (`OPT_NAIVE_UTC` or `OPT_UTC_Z`).</done>
</task>

</tasks>

<threat_model>
## STRIDE Register

**Spoofing — malicious input forging a CompactionSnapshot with extra fields.**
Mitigation: `extra="forbid"` on `CompactionSnapshot` and all helper models rejects unknown keys at
the Pydantic validation boundary. Any event-store write attempt with an injected extra field raises
`ValidationError` before the daemon's persistence layer is reached. The `EventEnvelope` parent
convention (lines 239-265 of `src/state_core/schema.py`) applies the same pattern.

**Tampering — replay attack with a stale snapshot from a prior session.**
Mitigation: `session_id` and `slice_id` fields are validated against daemon state at rehydrate
time. A snapshot whose `session_id` does not match the active session is rejected by the reinject
handler. `created_at` is set by the daemon (not the plugin/executor), preventing client-side
timestamp spoofing.

**Repudiation — snapshot row written without a corresponding event-store row.**
Mitigation: the compaction handler emits the `state.slice.compacted` event row FIRST (SQLite
transaction), then materializes the Layer-B markdown digest as a projection side-effect. SQLite is
authoritative per PROJECT.md cardinal rule; the projection may lag but the event row is atomic.
Missing event rows are detectable via replay gap analysis.

**DoS — oversized `provides_blocks` list causes snapshot row to exceed event-store row size budget.**
Mitigation: per-injection token cap (PAP-02); `provides_blocks` list is truncated by the
snapshot assembler when the combined serialized size of all `ProvidesBlock` entries exceeds the
per-injection cap. A `<truncated />` sentinel is appended so replay consumers detect the gap.
The `summary` field has a hard ≤8KB cap enforced in memory before write.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

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

<success_criteria>
- `CompactionSnapshot` is importable from `state_build.snapshot.compaction` and `model_config["extra"] == "forbid"`.
- orjson round-trip (dumps with `OPT_SORT_KEYS | OPT_NAIVE_UTC`, then `model_validate_json`) produces a value that equals the original snapshot instance.
- All seven required fields from CONTEXT-PROTOCOL.md §5 (CTX-05) are present in the model: `slice_id`, `step_id`, `task_id`, `session_id`, `active_plan_path`, `current_task_pointer`, and `provides_blocks`.
- Passing 5 / 5 tests; no teach-mode (`state_teach`) imports in any implementation file touched by this Step.
</success_criteria>

<output>
After completion, create `.planning/milestones/v14/phases/v14-1/slices/compaction-snapshot-schema/compaction-snapshot-schema-step-1-SUMMARY.md`
with a `provides:` block listing the exported symbols (`CompactionSnapshot`, `ProvidesBlock`,
`TaskPointer`, `VerifyResult`, `snapshot_to_bytes`, `snapshot_from_bytes`) and the verified
minimum-line counts for both files. This SUMMARY feeds the `<upstream_provides>` slot of the next
Step's reinject payload (CTX-06).
</output>
