# Frontmatter Schema Design Contracts

> **Design contract for v41+ runtime pydantic validation of all tier artifact frontmatter.**
> Consumed by: Phase 401 (ART-02 template frontmatter validation; ART-05 schema validation rules reference these models). v41+ (runtime pydantic validation implemented as `state_core/schemas/frontmatter.py`).

## Design Conventions

- All models use `ConfigDict(extra="forbid")` — NOT `frozen=True` (frontmatter is a mutable document). Event data payloads use `frozen=True` (per existing schema.py convention), but frontmatter schemas are read-write documents.
- Field ownership is classified as **AGENT** or **PROJECTOR** — never mixed within a field. Agent-owned fields are written during planning/review/verification. Projector-owned fields are written exclusively by the daemon projector.
- Status fields use pydantic `Literal` types for state-machine enforcement — valid values match the state lists in FSM-TABLES.md.
- ID fields follow D-01 dash-prefix format: `arc-{n}`, `stage-{n}`, `slice-{n}`, `step-{n}`. No leading zeros.
- All models use Python 3.12+ syntax (`str | None`, `list[str]`, `list[dict[str, str]]`).
- These are design contracts for v41+ runtime; code implementation is out of scope for v40.
- The schema pattern follows existing `src/state_core/schema.py` conventions: `ConfigDict(extra="forbid")` on all models, `Literal` for enumerated types, optional fields with `= None` defaults.

---

## Arc Frontmatter (ARC.md)

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ArcFrontmatter(BaseModel):
    """Design contract for ARC.md frontmatter — v41+ runtime validation.

    ARC.md is the Arc definition document. The frontmatter block is written
    by the agent during Arc creation and planning, read and updated by the
    projector to reflect the current state.
    """
    model_config = ConfigDict(extra="forbid")

    # ── Agent-owned fields (written by /state-new arc, /state-plan arc) ──
    id: str                              # "arc-{n}" per D-01. Example: "arc-45"
    title: str                           # Human-readable name. Example: "Auth System"
    goal: str                            # One-line outcome describing what the Arc delivers
    success_criteria: list[str]           # Measurable outcomes that define Arc completion. CRIT.md defines the
                                            # full set — this field is limitless, bound only by scope.
    depends_on: list[dict[str, str]] = []  # [{id: "arc-02", edge: "blocks"}]. Edge types: blocks, soft, data (D-12). Arc is root tier — cross-Arc deps allowed.

    # ── Projector-owned fields (written by daemon projector, NEVER by agent) ──
    status: Literal["planned", "in_progress", "auditing", "shipped", "abandoned"] = "planned"
    stage_count: int = 0                 # Number of child Stages (all statuses)
    shipped_stage_count: int = 0         # Number of child Stages in "shipped" state
    completed_at: str | None = None      # ISO 8601 timestamp when Arc reached "shipped"
```

**Field count:** 5 agent-owned, 4 projector-owned = 9 total fields.

**Status valid values** (from Arc state machine):
`planned`, `in_progress`, `auditing`, `shipped`, `abandoned`

---

## Stage Frontmatter (STAGE.md)

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class StageFrontmatter(BaseModel):
    """Design contract for STAGE.md frontmatter — v41+ runtime validation.

    Migration: This was formerly PhaseFrontmatter. Renamed per D-01.
    Existing codebase uses PhasePlannedData, PhaseStartedData, etc.
    These are design contracts for v41+ — the actual code migration
    from state.phase.* → state.stage.* is out of scope for v40.

    STAGE.md is the Stage definition document. The frontmatter block is
    written by the agent during Stage creation/planning and updated by
    the projector.
    """
    model_config = ConfigDict(extra="forbid")

    # ── Agent-owned fields (written by /state-new stage, /state-plan stage) ──
    id: str                              # "stage-{n}" per D-01. Example: "stage-22"
    title: str                           # Human-readable name. Example: "OAuth Provider Migration"
    goal: str                            # One-line outcome describing what the Stage delivers
    success_criteria: list[str]           # Measurable outcomes that define Stage completion
    arc_id: str                          # Parent Arc ID: "arc-{n}". Every Stage belongs to exactly ONE Arc.
    depends_on: list[dict[str, str]] = []  # [{id: "stage-02", edge: "blocks"}]. Edge types: blocks, soft, data (D-12). Same-parent-only: Stages can only depend on sibling Stages within the same Arc (D-10).

    # ── Projector-owned fields (written by daemon projector, NEVER by agent) ──
    status: Literal["planned", "in_progress", "verified", "auditing", "shipped", "abandoned"] = "planned"
    slice_count: int = 0                 # Number of child Slices (all statuses)
    shipped_slice_count: int = 0         # Number of child Slices in "shipped" state
    completed_at: str | None = None      # ISO 8601 timestamp when Stage reached "shipped"
```

**Field count:** 6 agent-owned, 4 projector-owned = 10 total fields.

**Status valid values** (from Stage state machine):
`planned`, `in_progress`, `verified`, `auditing`, `shipped`, `abandoned`

**Migration note:** This model replaces `PhaseFrontmatter` from existing code. The `depends_on` field uses the key `edge` (per D-12), not `kind`. The `arc_id` field is a mandatory parent reference — every Stage must belong to an Arc.

---

## Slice Frontmatter (SLICE.md)

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class SliceFrontmatter(BaseModel):
    """Design contract for SLICE.md frontmatter — v41+ runtime validation.

    SLICE.md is the Slice definition document. The frontmatter block is
    written by the agent during Slice creation and planning, and updated
    by the projector and agent (blocked_reason, deferred_reason are agent
    fields written when entering those states).
    """
    model_config = ConfigDict(extra="forbid")

    # ── Agent-owned fields (written by /state-new slice, /state-plan slice) ──
    id: str                              # "slice-{n}" per D-01. Example: "slice-12". Decimal: "slice-12.1" (D-16).
    title: str                           # Human-readable name. Example: "Anthropic OAuth Byte-for-Byte"
    goal: str                            # One-line outcome describing what the Slice delivers
    success_criteria: list[str]           # Measurable outcomes that define Slice completion
    stage_id: str                        # Parent Stage ID: "stage-{n}". Every Slice belongs to exactly ONE Stage.
    depends_on: list[dict[str, str]] = []  # [{id: "slice-10", edge: "blocks"}]. Edge types: blocks, soft, data (D-12). Same-parent-only: Slices can only depend on sibling Slices within the same Stage (D-10).

    # ── Projector-owned fields (written by daemon projector, NEVER by agent) ──
    status: Literal["planned", "worktree_ready", "in_progress", "shipped",
                    "reverted", "blocked", "deferred"] = "planned"
    step_count: int = 0                  # Number of child Steps (all statuses)
    completed_step_count: int = 0        # Number of child Steps in "done" state
    worktree_dir: str | None = None      # Absolute path to Slice worktree. Set at worktree_ready transition.
    worktree_branch: str | None = None   # Git branch name for Slice worktree. Set at worktree_ready transition.
    completed_at: str | None = None      # ISO 8601 timestamp when Slice reached "shipped"

    # ── Agent-written reason fields (projector NEVER modifies these) ──
    deferred_reason: str | None = None   # Reason Slice was deferred (D-14). Agent writes when entering deferred.
    blocked_reason: str | None = None    # Reason Slice is blocked (D-13/D-15). Agent writes when entering blocked.
```

**Field count:** 6 agent-owned (including reasons), 7 projector-owned, 2 agent-written reasons = 15 total fields.

**Status valid values** (from Slice state machine):
`planned`, `worktree_ready`, `in_progress`, `shipped`, `reverted`, `blocked`, `deferred`

**Design note:** `deferred_reason` and `blocked_reason` are agent-owned fields — the agent writes them when entering the deferred/blocked state, and the projector NEVER modifies them. The projector only reads them for display in STATE.md. This preserves agent intent even across projection rebuilds.

---

## Step Frontmatter (stepNPLAN.md)

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class StepFrontmatter(BaseModel):
    """Design contract for stepNPLAN.md frontmatter — v41+ runtime validation.

    Steps are markdown FILES (not directories) per D-04. This frontmatter
    is embedded in the step tracking file within the parent Slice folder.
    The Step has NO dedicated directory — all Step files are flat files
    in the Slice folder.

    Steps are NOT scheduler-dispatched (D-11). They run serially within
    a single agent session. The Step tracking file is generated by the
    run phase and contains the plan for executing this Step.
    """
    model_config = ConfigDict(extra="forbid")

    # ── Agent-owned fields (written by run phase, /state-run slice) ──
    step_number: int                     # Sequential within parent Slice (1, 2, 3...). No leading zeros per D-01.
    title: str                           # Human-readable name. Example: "Implement JWT token verification"
    goal: str                            # What this Step delivers
    slice_id: str                        # Parent Slice ID: "slice-{n}". Every Step belongs to exactly ONE Slice.
    plan_summary: str = ""               # Brief summary of how the Step will be executed
    verification_criteria: list[str] = []  # Criteria that must pass for this Step to be "done"

    # ── Projector-owned fields (written by daemon projector, NEVER by agent) ──
    status: Literal["idle", "designing", "planning", "running", "verifying",
                    "done", "blocked", "abandoned"] = "idle"
    completed_at: str | None = None      # ISO 8601 timestamp when Step reached "done"

    # ── Agent-written reason field (projector NEVER modifies) ──
    blocked_reason: str | None = None    # Reason Step is blocked (D-15). Agent writes when entering blocked.
```

**Field count:** 6 agent-owned, 2 projector-owned, 1 agent-written reason = 9 total fields.

**Status valid values** (from Step state machine, using D-03 renamed values):
`idle`, `designing`, `planning`, `running`, `verifying`, `done`, `blocked`, `abandoned`

**Design note:** Step frontmatter deliberately omits:
- `depends_on` — Steps run serially per D-11; intra-Slice ordering is agent's responsibility
- `worktree_dir` — Steps share the parent Slice's worktree (D-04)
- `step_count` — Step is the leaf tier; has no children
- Slugs — Steps are terminal units identified by number within parent Slice (no slugs per D-02)

**D-03 terminology:** Status values use `designing` (not `discussing`) and `running` (not `executing`). The D-03 rename applies consistently across all Step artifacts.

---

## Field Ownership Rules (TIER-07)

Every field is classified EXACTLY ONCE as **Agent** or **Projector**. No field is owned by both.
Agent never writes projector-owned fields. Projector never writes agent-owned fields
(including reason fields like `blocked_reason` and `deferred_reason`).

| Field | Arc | Stage | Slice | Step | Owner | Notes |
|-------|-----|-------|-------|------|-------|-------|
| `id` | ✓ | ✓ | ✓ | — | Agent | D-01 dash-prefix format |
| `step_number` | — | — | — | ✓ | Agent | Sequential within Slice; no leading zeros |
| `title` | ✓ | ✓ | ✓ | ✓ | Agent | Human-readable name |
| `goal` | ✓ | ✓ | ✓ | ✓ | Agent | One-line outcome |
| `success_criteria` | ✓ | ✓ | ✓ | — | Agent | Measurable outcomes (list) |
| `verification_criteria` | — | — | — | ✓ | Agent | Criteria for Step to be "done" |
| `plan_summary` | — | — | — | ✓ | Agent | Brief execution plan summary |
| `arc_id` | — | ✓ | — | — | Agent | Parent Arc reference |
| `stage_id` | — | — | ✓ | — | Agent | Parent Stage reference |
| `slice_id` | — | — | — | ✓ | Agent | Parent Slice reference |
| `depends_on` | ✓ | ✓ | ✓ | — | Agent | D-12 edge types: blocks, soft, data |
| `status` | ✓ | ✓ | ✓ | ✓ | Projector | Literal type; state-machine enforced |
| `stage_count` | ✓ | — | — | — | Projector | Child Stage count |
| `shipped_stage_count` | ✓ | — | — | — | Projector | Shipped child Stage count |
| `slice_count` | — | ✓ | — | — | Projector | Child Slice count |
| `shipped_slice_count` | — | ✓ | — | — | Projector | Shipped child Slice count |
| `step_count` | — | — | ✓ | — | Projector | Child Step count |
| `completed_step_count` | — | — | ✓ | — | Projector | Done child Step count |
| `worktree_dir` | — | — | ✓ | — | Projector | Absolute worktree path |
| `worktree_branch` | — | — | ✓ | — | Projector | Git branch name |
| `completed_at` | ✓ | ✓ | ✓ | ✓ | Projector | ISO 8601; set at terminal state |
| `deferred_reason` | — | — | ✓ | — | Agent | Why Slice was deferred (D-14) |
| `blocked_reason` | — | — | ✓ | ✓ | Agent | Why unit is blocked (D-13/D-15) |

**Field count by owner:**
- **Agent-owned:** 11 distinct fields across all tiers
- **Projector-owned:** 11 distinct fields across all tiers
- **Total:** 22 fields classified, each owned by exactly one role

**TIER-07 satisfied:** NO field is classified as both Agent and Projector. The `blocked_reason` and `deferred_reason` fields are agent-owned — the agent writes them when entering those states, and the projector preserves (never modifies) them across projection rebuilds.

---

## Cross-Tier ID Encoding

Aggregate IDs use hierarchical slash-delimited encoding that enables parent extraction at parse time.

```
Arc:    "arc-{n}"                                    Example: "arc-45"
Stage:  "arc-{n}/stage-{n}"                           Example: "arc-45/stage-22"
Slice:  "arc-{n}/stage-{n}/slice-{n}"                 Example: "arc-45/stage-22/slice-12"
Step:   "arc-{n}/stage-{n}/slice-{n}/step-{n}"        Example: "arc-45/stage-22/slice-12/step-5"
```

**Encoding rules:**
- Step numbers use 1-based sequential numbering within parent Slice (no zero-padding per D-01)
- Slice decimal insertions (D-16): `slice-12.1`, `slice-12.354` — single decimal level, no cap
- Every aggregate ID encodes its full lineage, enabling parent resolution without index lookup
- The `arc_id`, `stage_id`, and `slice_id` frontmatter fields store the SHORT form (`arc-{n}`, `stage-{n}`, `slice-{n}`) — not the hierarchical form
- The hierarchical form is used internally for event store keying and aggregate stream partitioning

**Parent extraction (projector):**
```python
def extract_parent_id(aggregate_id: str, parent_tier: str) -> str:
    """Extract parent aggregate ID from hierarchical child ID.
    
    Example: extract_parent_id("arc-45/stage-22/slice-12", "stage") → "arc-45/stage-22"
             extract_parent_id("arc-45/stage-22/slice-12", "arc") → "arc-45"
    """
    parts = aggregate_id.split("/")
    tier_positions = {"arc": 0, "stage": 1, "slice": 2, "step": 3}
    end = tier_positions[parent_tier] + 1
    return "/".join(parts[:end])
```

---

## Threat Model Alignment

The schema design enforces trust boundaries from the plan's threat model:

| Threat ID | Category | Mitigation in Schema |
|-----------|----------|---------------------|
| T-400-01 | Tampering — Agent writing status | `status` is projector-owned across ALL tiers. Agent schema lacks status write permission. |
| T-400-02 | Tampering — Agent adding unknown fields | `extra="forbid"` on all models rejects unknown fields at parse time. |
| T-400-04 | Tampering — Malformed ID (double decimal) | Regex validation on ID fields rejects double decimals. Documented in D-16. |
| T-400-07 | Elevation — Agent writing completed_at | `completed_at` is projector-owned across ALL tiers. No agent writes to this field. |

---

## Comparison with Existing Codebase

| Aspect | Existing (`schema.py`) | v40 Design (this doc) |
|--------|----------------------|----------------------|
| Models | Event data payloads (34+, frozen) | Frontmatter schemas (4, non-frozen) |
| `extra="forbid"` | Yes (on all event data models) | Yes (on all frontmatter models) |
| `frozen` | Yes (immutable event data) | No (mutable frontmatter documents) |
| Field ownership | Not classified | Agent/Projector classification per field |
| Arc model | `ArcCreatedData` (event payload) | `ArcFrontmatter` (document schema) |
| Stage model | `PhasePlannedData` etc. (event payloads) | `StageFrontmatter` (document schema, renamed) |
| Slice model | `SlicePlannedData` etc. (event payloads) | `SliceFrontmatter` (document schema) |
| Step model | `StepDiscussedData` etc. (event payloads) | `StepFrontmatter` (document schema, renamed states) |

**Key difference:** Existing `schema.py` defines event data payload models (what data an event carries). This v40 design defines frontmatter document schemas (what fields an artifact's YAML frontmatter contains). Both use the same pydantic conventions (`extra="forbid"`, `Literal` types), but serve different purposes. The v41+ runtime will implement both: event data models in `state_core/schema.py` and frontmatter models in `state_core/schemas/frontmatter.py`.

---

*Design contract for v41+ runtime pydantic validation. All models validated against FSM-TABLES.md state lists, TIER-07 field ownership rules, and D-01/D-03 naming conventions. Consumed by Phase 401 artifact catalog (ART-02 templates, ART-05 validation rules).*

---

## v41 Amendment — Phase 405 SliceFrontmatter Extensions

**Phase:** 405 (Deviation Rules & Subagent Management)
**Status:** Canonical (v41)
**Append-only:** All entries below are NEW; nothing above this header has been edited.
**Build-mode only:** All three new fields are Build-mode-only; teach-mode SliceFrontmatter (v47 territory) owns its own analogs.
**Pydantic `extra="forbid"`** continues per v40+Phase 403 convention.

Phase 405's three sibling spec docs introduce three new fields on the `SliceFrontmatter` Pydantic model. Full validation rules + behavioral semantics live in the owning Phase 405 spec docs; this amendment is a registry index.

### New SliceFrontmatter Fields

| Field | Type | Default | Owning REQ → Spec |
|---|---|---|---|
| `autonomy` | `Literal["tiered","full-yolo","conservative"] \| None` | `None` (inherit from milestone default) | DEV-06 → DEVIATION-RULES.md §6 |
| `allowed_subagents` | `list[SubagentType] \| None` | `None` (use `STAGE_ROSTER[current_stage]`) | SUB-03 → SUBAGENT-MANAGEMENT.md §5 |
| `subagent` | `SubagentSliceConfig \| None` | `None` | SUB-04 + SUB-07 → SUBAGENT-MANAGEMENT.md §6 + SUBAGENT-MONITORING.md §5 |

### Nested `SubagentSliceConfig` shape

```python
class SubagentSliceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parallel_cap: int | None = None                       # SUB-04 narrowing-only override (≤20)
    progress_timeout_s: int | None = None                 # SUB-07 default 180s
    remediation_hints: dict[str, str] | None = None       # SUB-07 keyed by crash_source
```

### Validation rules (cross-references)

- **`autonomy`**: Slice override CAN move stricter OR looser (narrowing-only does NOT apply; autonomy is policy not capability). Precedence: `milestone default → Slice override → done`. See DEVIATION-RULES.md §6.
- **`allowed_subagents`**: Narrowing-only (subset of `STAGE_ROSTER[current_stage]`). Two-gate validation: plan-validation stage (Phase 403 N-VALIDATION.md) + runtime `tool.execute.before`. See SUBAGENT-MANAGEMENT.md §5.
- **`subagent.parallel_cap`**: Narrowing-only (≤20). Expansion attempts → `state.slice.subagent_cap_expansion_rejected` at plan-validation. See SUBAGENT-MANAGEMENT.md §6.

### Authoritative-ordering note

Pydantic class definitions in the owning Phase 405 spec docs are authoritative; this amendment is a registry index for the SliceFrontmatter additions.
