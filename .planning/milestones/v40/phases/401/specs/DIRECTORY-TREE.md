# Directory Tree: `.state/build/` Filesystem Blueprint

> **Design contract for v41+ filesystem layout, naming conventions, and concurrent access rules.**
> Consumed by: v41+ daemon (directory creation, index.json projector handler), v41+ CLI commands (`/state-new`, `/state-design`, `/state-run`), v41+ worktree manager, v42 quality pipeline verifier, Phase 401 Plan 03 (CROSS-REFERENCES.md resolution algorithm).

## Design Conventions

This document is the authoritative specification for the `.state/build/` on-disk layout. It specifies **where** every artifact lives, **who** creates each directory and file, **when** creation happens, and **how** concurrent access is managed. It builds on the artifact catalog (ARTIFACT-CATALOG.md) which defines **what** each artifact is — this document specifies the filesystem placement for every catalog entry.

All paths are relative to `.state/build/` root. Variable notation is uniform: `arc-{n}`, `stage-{n}`, `slice-{n}`, `step-{n}` — per Phase 400 D-01 (dash-prefix, no leading zeros). No competing notations are permitted (e.g., `{arc-id}`, `arc_id`, `arc_{n}` are all invalid). Directory nodes use `[OWNER]` annotation: `[AGENT]` for agent-created, `[PROJECTOR]` for projector-rebuilt, `[AGENT+PROJECTOR]` for hybrid ownership, `[STATIC]` for shipped-with-engine files. `{n}` is a sequential integer per parent, no leading zeros per D-01. Slugs are kebab-case display-only strings, not part of the stable ID (D-02).

**Single source of truth:** ARTIFACT-CATALOG.md (Plan 401-01) is the canonical definition of every artifact type. This document references catalog paths — never redefines them. The Path Verification Table at the end of Section 2 confirms every tree entry has a corresponding catalog entry with an identical path.

---

## Section 1: Complete Directory Tree (DSK-01)

The annotated tree covers every directory and file in `.state/build/`. Each node is annotated with its `[OWNER]` tag and purpose. The tree is the authoritative reference for v41+ filesystem initialization.

```
.state/build/
├── index.json                    # [PROJECTOR] Artifact registry — ID→path mapping, O(1) lookup
│                                  # Rebuilt on daemon startup (full) and every state.* event (incremental)
│                                  # Consumed by: daemon artifact loader, CLI ID resolution, validate_consistency()
├── state/                        # [PROJECTOR] Consolidated STATE.md JSON projections
│   │                              # Created by daemon initializer on first startup
│   ├── arcs.json                 # [PROJECTOR] All Arc STATE projections, keyed by arc-{n}
│   ├── stages.json               # [PROJECTOR] All Stage STATE projections, keyed by arc-{n}/stage-{n}
│   ├── slices.json               # [PROJECTOR] All Slice STATE projections, keyed by arc-{n}/stage-{n}/slice-{n}
│   └── steps.json                # [PROJECTOR] All Step STATE projections, keyed by arc-{n}/stage-{n}/slice-{n}/step-{n}
│                                  # Consumed by: state export-state CLI, daemon dashboard, TUI extensions
├── arcs/
│   └── arc-{n}/                  # [AGENT] Arc directory — created by /state-new arc
│       │                          # D-01: dash-prefix, no leading zeros. Optional slug: arc-{n}-{slug}/
│       ├── ARC.md                # [AGENT] Arc definition — see ARTIFACT-CATALOG.md §ARC.md
│       │                          # Created by: /state-new arc. Projector updates status, counts, completed_at.
│       │                          # Consumed by: daemon artifact loader, projector status updates, CLI commands
│       ├── CRIT.md               # [AGENT] Must-have criteria (CRIT-01, CRIT-02, ...) per D-401-03
│       │                          # Created by: planner during /state-new arc flow
│       │                          # All fields lock when Arc enters in_progress per D-401-12
│       ├── MAP.md                # [AGENT+PROJECTOR] Stage plan + tracker per D-401-04/05
│       │                          # Agent writes child entries + goals. Projector updates checkboxes.
│       │                          # Consumed by: DAG scheduler (child inventory), STATE.md projections
│       ├── DECISIONS.md          # [AGENT] Gray-area decision log (append-only) per D-401-02
│       │                          # Agent-authored, projector NEVER modifies
│       ├── stages/
│       │   └── stage-{n}/        # [AGENT] Stage directory — created by /state-new stage
│       │       │                  # D-01: dash-prefix, no leading zeros. Decimal: stage-{n}.{d} per D-16
│       │       ├── STAGE.md      # [AGENT] Stage definition — see ARTIFACT-CATALOG.md §STAGE.md
│       │       │                  # Created by: /state-new stage. Projector updates status, counts, completed_at.
│       │       ├── CRIT.md       # [AGENT] Must-have criteria for this Stage
│       │       │                  # All fields lock when Stage enters in_progress per D-401-12
│       │       ├── MAP.md        # [AGENT+PROJECTOR] Slice plan + tracker
│       │       │                  # Agent writes child entries + goals. Projector updates checkboxes.
│       │       ├── DECISIONS.md  # [AGENT] Decision log for this Stage
│       │       │
│       │       └── slices/
│       │           └── slice-{n}/    # [AGENT] Slice directory — created by /state-new slice
│       │               │             # D-01: dash-prefix, no leading zeros. Decimal: slice-{n}.{d} per D-16
│       │               │             # Optional slug: slice-{n}-{slug}/ per D-02
│       │               ├── SLICE.md          # [AGENT] Slice definition — see ARTIFACT-CATALOG.md §SLICE.md
│       │               │                      # Created by: /state-new slice. Projector updates status, counts, worktree info.
│       │               ├── DESIGN.md         # [AGENT] Design phase output — see ARTIFACT-CATALOG.md §DESIGN.md
│       │               │                      # Always mutable per D-401-12. Created during /state-design slice.
│       │               ├── RESEARCH.md       # [AGENT] Research phase output — see ARTIFACT-CATALOG.md §RESEARCH.md
│       │               │                      # Always mutable per D-401-12. Created during /state-research slice.
│       │               ├── step1PLAN.md      # [AGENT] Run tracking file (Step 1) — per D-04 (Steps are flat files)
│       │               │                      # Created by agent during /state-run slice. Projector updates status, completed_at.
│       │               │                      # All fields lock when parent Slice enters in_progress per D-401-12.
│       │               ├── step2PLAN.md      # [AGENT] Run tracking file (Step 2)
│       │               ├── stepNPLAN.md      # [AGENT] Run tracking file (Step N — sequential, max N per Slice)
│       │               │                      # Consumed by: agent run phase (reads plan), projector (updates status),
│       │               │                      # verify phase (reads verification_criteria)
│       │               ├── VERIFICATION.md   # [AGENT] Verify phase output — see ARTIFACT-CATALOG.md §VERIFICATION.md
│       │               │                      # Locked when parent Slice enters shipped per D-401-13
│       │               ├── SUMMARY.md        # [AGENT] Summary phase output — see ARTIFACT-CATALOG.md §SUMMARY.md
│       │               │                      # Locked when parent Slice enters shipped per D-401-13
│       │               └── {worktree}/       # [AGENT+SYSTEM] Git worktree — one per Slice
│       │                                      # Created by worktree manager when Slice enters worktree_ready
│       │                                      # Named by Slice ID: worktree-slice-{n}/ or git branch name
│       │                                      # Preserved on abandon (forensics per D-13), destroyed on shipped
│       │                                      # (configurable retention via flag)
└── templates/                    # [STATIC] Shipped with engine — NOT written by agent or projector
    │                              # Created by daemon initializer on first startup from engine install path
    │                              # Consumed by: /state-new CLI commands (renders template into working artifact)
    ├── ARC.md.tmpl               # [STATIC] Template for Arc definition — see ARTIFACT-CATALOG.md §ARC.md.tmpl
    ├── STAGE.md.tmpl             # [STATIC] Template for Stage definition — see ARTIFACT-CATALOG.md §STAGE.md.tmpl
    ├── SLICE.md.tmpl             # [STATIC] Template for Slice definition — see ARTIFACT-CATALOG.md §SLICE.md.tmpl
    ├── STEP.md.tmpl              # [STATIC] Template for Step plan — see ARTIFACT-CATALOG.md §STEP.md.tmpl
    ├── CRIT.md.tmpl              # [STATIC] Template for criteria — see ARTIFACT-CATALOG.md §CRIT.md.tmpl
    ├── MAP.md.tmpl               # [STATIC] Template for plan+tracker — see ARTIFACT-CATALOG.md §MAP.md.tmpl
    ├── DECISIONS.md.tmpl         # [STATIC] Template for decision log — see ARTIFACT-CATALOG.md §DECISIONS.md.tmpl
    ├── DESIGN.md.tmpl            # [STATIC] Template for design doc — see ARTIFACT-CATALOG.md §DESIGN.md.tmpl
    ├── RESEARCH.md.tmpl          # [STATIC] Template for research doc — see ARTIFACT-CATALOG.md §RESEARCH.md.tmpl
    └── PLAN.md.tmpl              # [STATIC] Template for GSD-origin PLAN.md (Step execution plan variant)
                                   # Provides backward compatibility for GSD-format plan templates
```

### Consumer Notes

Every tree node has specific consumers that read it at well-defined lifecycle points:

| Tree Node | Consumer | When | Purpose |
|-----------|----------|------|---------|
| `index.json` | Daemon artifact loader | Daemon startup | Load full artifact registry into memory for O(1) ID→path resolution |
| `index.json` | Projector | Every `state.*` event | Incremental rebuild of affected entries |
| `index.json` | `validate_consistency()` | Daemon startup + on-demand | Walk all entries; detect orphans, staleness, hash mismatches (Plan 401-03) |
| `state/*.json` | `state export-state` CLI | On-demand | Generate per-directory STATE.md from canonical JSON |
| `state/*.json` | Daemon dashboard | Continuous | Display current project state across all tiers |
| `state/*.json` | TUI extensions (v17) | Session lifecycle | Populate sidebar, statusline, build-progress tree |
| `arcs/arc-{n}/ARC.md` | Daemon artifact loader | Artifact read | Load Arc frontmatter for status tracking |
| `arcs/arc-{n}/ARC.md` | Projector | `state.arc.*` events | Update status, stage_count, shipped_stage_count, completed_at |
| `arcs/arc-{n}/ARC.md` | CLI `/state-design`, `/state-run` | Planning/execution | Read Arc scope for context window planning |
| `stage-{n}/STAGE.md` | Daemon artifact loader | Artifact read | Load Stage frontmatter for status tracking |
| `stage-{n}/STAGE.md` | Projector | `state.stage.*` events | Update status, slice_count, shipped_slice_count, completed_at |
| `slice-{n}/SLICE.md` | Daemon artifact loader | Artifact read | Load Slice frontmatter for status tracking |
| `slice-{n}/SLICE.md` | Projector | `state.slice.*` events | Update status, step_count, completed_step_count, worktree info |
| `stepNPLAN.md` | Agent run phase | Step creation | Read plan_summary and verification_criteria for execution |
| `stepNPLAN.md` | Projector | `state.step.*` events | Update status, completed_at |
| `stepNPLAN.md` | Verify phase | Verification | Read verification_criteria for pass/fail determination |
| `templates/*.tmpl` | `/state-new` CLI commands | Artifact creation | Render template fields into new artifact file |
| `{worktree}/` | Worktree manager | Slice `worktree_ready` | Create isolated git worktree for concurrent work |
| `{worktree}/` | Agent | During `/state-run` | Execute Step plans against worktree filesystem |

### Path Verification Table

Every node in the directory tree is verified against its canonical path in ARTIFACT-CATALOG.md (Plan 401-01 output). The catalog is the single source of truth for artifact paths — this table confirms consistency.

| Directory/File in Tree | Path in ARTIFACT-CATALOG.md | Match? | Notes |
|------------------------|-----------------------------|--------|-------|
| `index.json` | `index.json` | ✓ | Projector-rebuilt, lives at root |
| `state/arcs.json` | `state/arcs.json` | ✓ | Projector-rebuilt STATE.md projection |
| `state/stages.json` | `state/stages.json` | ✓ | Projector-rebuilt STATE.md projection |
| `state/slices.json` | `state/slices.json` | ✓ | Projector-rebuilt STATE.md projection |
| `state/steps.json` | `state/steps.json` | ✓ | Projector-rebuilt STATE.md projection |
| `arcs/arc-{n}/ARC.md` | `arcs/arc-{n}/ARC.md` | ✓ | Agent-authored Arc definition |
| `arcs/arc-{n}/CRIT.md` | `arcs/arc-{n}/CRIT.md` | ✓ | Arc-level criteria |
| `arcs/arc-{n}/MAP.md` | `arcs/arc-{n}/MAP.md` | ✓ | Arc-level plan+tracker (hybrid) |
| `arcs/arc-{n}/DECISIONS.md` | `arcs/arc-{n}/DECISIONS.md` | ✓ | Arc-level decision log |
| `arcs/arc-{n}/stages/stage-{n}/STAGE.md` | `arcs/arc-{n}/stages/stage-{n}/STAGE.md` | ✓ | Agent-authored Stage definition |
| `arcs/arc-{n}/stages/stage-{n}/CRIT.md` | `arcs/arc-{n}/stages/stage-{n}/CRIT.md` | ✓ | Stage-level criteria |
| `arcs/arc-{n}/stages/stage-{n}/MAP.md` | `arcs/arc-{n}/stages/stage-{n}/MAP.md` | ✓ | Stage-level plan+tracker (hybrid) |
| `arcs/arc-{n}/stages/stage-{n}/DECISIONS.md` | `arcs/arc-{n}/stages/stage-{n}/DECISIONS.md` | ✓ | Stage-level decision log |
| `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/SLICE.md` | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/SLICE.md` | ✓ | Agent-authored Slice definition |
| `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/DESIGN.md` | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/DESIGN.md` | ✓ | Design phase output |
| `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/RESEARCH.md` | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/RESEARCH.md` | ✓ | Research phase output |
| `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/step{step_number}PLAN.md` | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/step{step_number}PLAN.md` | ✓ | Step tracking files (flat, per D-04) |
| `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/VERIFICATION.md` | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/VERIFICATION.md` | ✓ | Verify phase output |
| `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/SUMMARY.md` | `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/SUMMARY.md` | ✓ | Summary phase output |
| `templates/ARC.md.tmpl` | `templates/ARC.md.tmpl` | ✓ | Template shipped with engine |
| `templates/STAGE.md.tmpl` | `templates/STAGE.md.tmpl` | ✓ | Template shipped with engine |
| `templates/SLICE.md.tmpl` | `templates/SLICE.md.tmpl` | ✓ | Template shipped with engine |
| `templates/STEP.md.tmpl` | `templates/STEP.md.tmpl` | ✓ | Template shipped with engine |
| `templates/CRIT.md.tmpl` | `templates/CRIT.md.tmpl` | ✓ | Template shipped with engine |
| `templates/MAP.md.tmpl` | `templates/MAP.md.tmpl` | ✓ | Template shipped with engine |
| `templates/DECISIONS.md.tmpl` | `templates/DECISIONS.md.tmpl` | ✓ | Template shipped with engine |
| `templates/DESIGN.md.tmpl` | `templates/DESIGN.md.tmpl` | ✓ | Template shipped with engine |
| `templates/RESEARCH.md.tmpl` | `templates/RESEARCH.md.tmpl` | ✓ | Template shipped with engine |
| `templates/PLAN.md.tmpl` | *(not in ARTIFACT-CATALOG)* | ⚠ | Backward-compatibility template for GSD-origin PLAN format |
| `{worktree}/` under Slice | *(not in catalog — runtime concern)* | — | Worktree is a git artifact, not an engine artifact |

**Verification result:** 28/28 catalog paths match. One template (`PLAN.md.tmpl`) is not in the catalog — it is a backward-compatibility template for GSD-origin plan formats, included for migration support. The `{worktree}/` directory is a runtime git artifact (not an engine design artifact) and is correctly absent from the catalog.

---

## Section 2: Naming Conventions (DSK-02)

Every name in `.state/build/` follows a strict convention that enables stable ID resolution, human readability, and programmatic parsing. These conventions implement Phase 400 decisions D-01 (dash-prefix, no leading zeros), D-02 (kebab-case slugs), D-04 (Steps are flat files), and D-16 (decimal insertions).

### ID Format

Stable identifiers are the primary key for all artifact resolution. They are dash-prefix, lowercase, and never contain leading zeros.

| Tier | Format | Regex Validation | Examples |
|------|--------|-----------------|----------|
| Arc | `arc-{n}` | `^arc-\d+$` | `arc-1`, `arc-45` |
| Stage | `stage-{n}` | `^stage-\d+(\.\d+)?$` | `stage-1`, `stage-22`, `stage-12.1` (decimal per D-16) |
| Slice | `slice-{n}` | `^slice-\d+(\.\d+)?$` | `slice-1`, `slice-12`, `slice-12.354` (decimal per D-16) |
| Step | `step{number}` (embedded in filename) | `step_number` is integer ≥ 1 | `step1PLAN.md`, `step5PLAN.md` |

**Rules:**
1. Dash prefix always present: `arc-`, `stage-`, `slice-`
2. Always lowercase
3. No leading zeros in `{n}`: `arc-1` (valid), `arc-01` (invalid) — per D-01
4. Decimal insertions supported at single level: `slice-12.1`, `slice-12.354` — per D-16
5. Step numbers are sequential integers, not dash-prefixed in the ID (the file name embeds them differently)
6. ID is the stable, immutable identifier — never changes for the lifetime of the aggregate

### Directory Naming

Directories are named by their stable ID, enabling programmatic resolution without parsing slugs.

| Pattern | Example | Notes |
|---------|---------|-------|
| ID-only | `arc-45/` | Primary format — used for all ID resolution |
| ID + slug | `arc-45-auth-system/` | Optional display add-on per D-02. Slug is not part of the stable ID |
| Stage nested | `arc-45/stages/stage-3/` | Full path uses parent→child nesting |
| Slice nested | `arc-45/stages/stage-3/slices/slice-12/` | Deepest nesting level |

**Slug rules:**
- Slug is a kebab-case display string derived from the artifact title: `"Auth System"` → `auth-system`
- Max 50 characters
- Alphanumeric + hyphens only. No underscores, no spaces, no special characters
- Slug deduplication: if two Arcs produce `auth-system`, the second gets `auth-system-2`
- Slug is informational metadata — ID resolution works identically with or without slug
- Example with slug: `arc-45-auth-system/stages/stage-3-oauth-flow/slices/slice-12-pkce-handler/`

### Step File Naming

Steps are flat markdown files within the Slice directory, NOT subdirectories (per D-04). This is a deliberate design choice: Steps run serially within a single agent session and exist only within their parent Slice's scope.

| Pattern | Example | Notes |
|---------|---------|-------|
| Single Step | `step1PLAN.md` | Step number + literal "PLAN" + extension |
| Multiple Steps | `step1PLAN.md`, `step2PLAN.md`, `step3PLAN.md` | Sequential within Slice directory |
| Convention | `step{step_number}PLAN.md` | `{step_number}` is an integer ≥ 1, no leading zeros |

**Step directory rule:** Steps do NOT have their own subdirectory. All stepNPLAN.md files live flat in the Slice directory alongside DESIGN.md, RESEARCH.md, VERIFICATION.md, and SUMMARY.md. This avoids unnecessary directory nesting and keeps all Slice-level artifacts co-located.

### Display Prefixes

For human readability in CLI output and TUI displays, hierarchical prefixes are generated from the aggregate ID hierarchy. These are display-only — never used for ID resolution or filesystem operations.

| Prefix Format | Example | Meaning |
|---------------|---------|---------|
| `arc-{n}-stage-{n}` | `arc-1-stage-3` | Stage 3 within Arc 1 |
| `arc-{n}-stage-{n}-slice-{n}` | `arc-1-stage-3-slice-12` | Slice 12 within Stage 3 within Arc 1 |
| Full aggregate ID | `arc-1/stage-3/slice-12/step-5` | Step 5 within Slice 12 within Stage 3 within Arc 1 (slash-delimited hierarchical form per FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding) |

Display prefixes are generated on-the-fly from the hierarchical aggregate ID. They have no regex rules — they are derived directly from the stable IDs.

---

## Section 3: STATE.md Placement Strategy (DSK-03)

Per D-401-07, consolidated JSON projections under `.state/build/state/` are the canonical STATE representation. The CLI `state export-state` generates per-directory STATE.md on demand for human consumption. This keeps source-controlled markdown clean while providing fast, queryable state access.

### Canonical STATE Locations

| File | Contents | Key Format |
|------|----------|------------|
| `.state/build/state/arcs.json` | All Arc STATE projections | `arc-{n}` |
| `.state/build/state/stages.json` | All Stage STATE projections | `arc-{n}/stage-{n}` |
| `.state/build/state/slices.json` | All Slice STATE projections | `arc-{n}/stage-{n}/slice-{n}` |
| `.state/build/state/steps.json` | All Step STATE projections | `arc-{n}/stage-{n}/slice-{n}/step-{n}` |

### JSON Projection Format

Each projection entry includes all frontmatter fields (agent + projector), a `projection_updated` timestamp, and an `event_sequence` for incremental rebuild tracking.

```json
{
  "arc-45": {
    "id": "arc-45",
    "title": "Auth System",
    "goal": "Implement all five auth methods with stealth header parity",
    "status": "in_progress",
    "success_criteria": [
      "OAuth stealth headers match claude-oauth.md byte-for-byte",
      "All five providers pass smoke test within 30 days"
    ],
    "depends_on": [],
    "stage_count": 3,
    "shipped_stage_count": 1,
    "completed_at": null,
    "projection_updated": "2026-05-07T12:00:00Z",
    "event_sequence": 1042
  },
  "arc-46": {
    "id": "arc-46",
    "title": "Event Store v2",
    "goal": "Dual-write event store with deterministic replay",
    "status": "planned",
    "success_criteria": [
      "Replay produces bit-identical results across 10K events"
    ],
    "depends_on": [],
    "stage_count": 0,
    "shipped_stage_count": 0,
    "completed_at": null,
    "projection_updated": "2026-05-07T11:00:00Z",
    "event_sequence": 1038
  }
}
```

**Required fields per projection entry:**
- All frontmatter fields from the artifact's pydantic model (agent + projector)
- `projection_updated`: ISO 8601 timestamp of last projector update
- `event_sequence`: integer — sequence number of last processed event for this aggregate

### export-state CLI Contract

The `state export-state` command generates human-readable per-directory STATE.md files from the canonical JSON projections. It does NOT read the event store — it reads from already-projected JSON files for speed.

```
Command: state export-state [--tier arc|stage|slice|step] [--id <aggregate-id>] [--dir <path>]
Purpose: Generate per-directory STATE.md from canonical JSON projections
Output: Markdown file at <path>/STATE.md with YAML frontmatter + status table
Behavior: Read-only — reads from state/*.json, writes STATE.md to specified directory
```

**Options:**
- `--tier`: Filter to a specific tier (default: all tiers)
- `--id`: Export STATE.md for a single aggregate (default: all)
- `--dir`: Target directory for STATE.md output (default: current working directory)

**Output format (per-directory STATE.md):**
```markdown
---
id: arc-45
title: Auth System
status: in_progress
stage_count: 3
shipped_stage_count: 1
projection_updated: "2026-05-07T12:00:00Z"
---

# STATE: arc-45 Auth System

## Child Stages
| ID | Goal | Status |
|----|------|--------|
| stage-1 | OAuth handler implementation | shipped |
| stage-2 | Token management | in_progress |
| stage-3 | Provider parity matrix | planned |
```

### Rebuild Semantics

**Full rebuild (daemon startup):**
1. Projector reads all events from the event store (`.state/events.sqlite`)
2. Replays events in sequence order, building current state for every aggregate
3. Writes `state/arcs.json`, `state/stages.json`, `state/slices.json`, `state/steps.json` atomically (write to `.tmp`, rename)

**Incremental rebuild (per state.* event):**
1. Projector receives event with `event_sequence` number
2. Extracts `aggregate_id` from event payload
3. Updates the affected entry in the appropriate tier's JSON file
4. Sets `projection_updated` to current timestamp and `event_sequence` to the event's sequence number
5. Writes the tier JSON file atomically (write to `.tmp`, rename)

**Incremental skip optimization:**
- `event_sequence` field enables incremental rebuild skip: if the projector's last processed sequence is ≥ an event's sequence, skip that event
- This makes daemon restart fast — the projector only processes events that arrived while it was down

**STATE.md generation:**
- Per-directory STATE.md is NEVER source-controlled — it is a generated artifact
- Generated on-demand via `state export-state` CLI
- Reads from `state/*.json`, never from individual artifact files
- Format is markdown with YAML frontmatter matching the corresponding pydantic model

---

## Section 4: File Count Strategy (DSK-04)

Per D-401-08, Step files remain separate — each Step in a Slice produces one tracking file (`stepNPLAN.md`). This section projects file counts across project scales and validates that the design scales without filesystem bloat.

### Per-Step File Formula

A Slice with N Steps produces this file set:

| File | Count | Always Present? |
|------|-------|-----------------|
| `SLICE.md` | 1 | Yes |
| `DESIGN.md` | 1 | Yes (always mutable) |
| `RESEARCH.md` | 1 | Yes (always mutable) |
| `step{1..N}PLAN.md` | N | Yes (one per Step) |
| `VERIFICATION.md` | 1 | After verify phase |
| `SUMMARY.md` | 1 | After summary phase |
| **Total per Slice** | **N + 5** | |

A typical 3-step Slice has 8 files. A 5-step Slice has 10 files.

### Scalability Projection

| Scale | Arcs | Stages/Arc | Slices/Stage | Steps/Slice | Total Slice Files | Total Arc+Stage Files | Total Artifact Files |
|-------|------|------------|--------------|-------------|-------------------|----------------------|----------------------|
| Small project | 3 | 2 | 3 | 3 | 3×2×3×8 = 144 | 3×5 + 6×5 = 45 | ~189 |
| Medium project | 10 | 3 | 3 | 3 | 10×3×3×8 = 720 | 10×5 + 30×5 = 200 | ~920 |
| Large project | 20 | 5 | 5 | 5 | 20×5×5×10 = 5,000 | 20×5 + 100×5 = 600 | ~5,600 |
| Upper bound | 20 | 10 | 10 | 3 | 20×10×10×8 = 16,000 | 20×5 + 200×5 = 1,100 | ~17,100 |

**Total artifact files at upper bound:**
- Arc-level files per Arc: ARC.md + CRIT.md + MAP.md + DECISIONS.md = 4 files
- Stage-level files per Stage: STAGE.md + CRIT.md + MAP.md + DECISIONS.md = 4 files
- Slice-level files per Slice: SLICE.md + DESIGN.md + RESEARCH.md + stepNPLAN.md×(avg steps) + VERIFICATION.md + SUMMARY.md ≈ 8–10 files
- Projector files: index.json + 4 state JSON projections = 5 files
- Templates: 10 shipped-with-engine template files (STATIC, not counted in runtime files)

**Worst case (20 Arcs × 10 Stages × 10 Slices = 2,000 Slices):**
- Arc files: 20 × 4 = 80
- Stage files: 200 × 4 = 800
- Slice files: 2,000 × 8 = 16,000
- Projector files: 5
- **Total: ~16,885 files in `.state/build/`**

This is acceptable on modern filesystems:
- **ext4:** Max files per directory: unlimited (with `dir_index` and `large_dir` features). Subdirectory limit: ~64K. All well within bounds.
- **APFS:** No practical directory file count limit. FUSE indexing efficient at this scale.
- **NTFS:** 4,294,967,295 files per volume. MFT handles millions of small files efficiently.

### Filesystem Bloat Mitigation

The design self-corrects against unbounded growth through several mechanisms:

1. **Stage planning scope (FSM-06):** Each Slice must fit within the agent's context window. This naturally produces many bounded Slices, but each is deliberately scoped — not an unbounded proliferation.

2. **All files within single `.state/build/` subtree:** No scattering across the repository. `rm -rf .state/build/` resets everything. Backup and migration are single-directory operations.

3. **No artificial cap:** The design scales with project size. A 20-Arc monorepo with 2,000 Slices is realistic for a multi-year project but still produces manageable file counts.

4. **Index-driven discovery:** The daemon never needs to `os.walk()` the entire tree to find artifacts. `index.json` provides O(1) lookup — directory size doesn't affect read performance.

5. **Worktree isolation:** Each `{worktree}/` is a git worktree, not a repository clone — disk cost per worktree is minimal (git object sharing).

---

## Section 5: Concurrent Access Rules (DSK-06)

The `.state/build/` filesystem supports multiple concurrent writers — agent processes, projector, worktree manager, and CLI commands — without file locks. The design relies on atomic rename patterns, clear directory creation ownership, and event-sourced conflict resolution.

### Directory Creation Ownership

Only the designated creator may create a specific directory. This prevents race conditions on `mkdir` and ensures the filesystem starts in a known state.

| Directory | Created By | When |
|-----------|-----------|------|
| `.state/build/` root | Daemon initializer (one-time) | First daemon startup — creates arcs/, state/, templates/ |
| `.state/build/arcs/` | Daemon initializer (one-time) | First daemon startup |
| `.state/build/state/` | Daemon initializer (one-time) | First daemon startup |
| `.state/build/templates/` | Daemon initializer (one-time) | First daemon startup — copies from engine install path |
| `arcs/arc-{n}/` | `/state-new arc` CLI | Arc creation — agent invokes CLI |
| `arcs/arc-{n}/stages/` | `/state-new arc` CLI | Arc creation — pre-creates stages container |
| `arcs/arc-{n}/stages/stage-{n}/` | `/state-new stage` CLI | Stage creation — agent invokes CLI |
| `arcs/arc-{n}/stages/stage-{n}/slices/` | `/state-new stage` CLI | Stage creation — pre-creates slices container |
| `arcs/arc-{n}/stages/stage-{n}/slices/slice-{n}/` | `/state-new slice` CLI | Slice creation — agent invokes CLI |
| `{worktree}/` under Slice | Worktree manager (v41+) | Slice enters `worktree_ready` transition |

**Agent MUST NOT create directories in projector-owned paths:**
- `state/` — projector-only
- Any new top-level directory under `.state/build/` — must be added to this spec first

### Lock-Free Append-Only Write Model

The filesystem uses an append-only model with atomic file writes. File locks are never used — the event store is the authoritative source of truth for conflict resolution.

**Atomic write pattern:**
```
1. Writer creates temp file: index.json.tmp (same directory)
2. Writer fully writes content to temp file
3. Writer calls os.rename(index.json.tmp, index.json) — POSIX atomic rename
4. Reader always opens index.json directly — never sees partial writes
```

**Append-only semantics:**
- Artifact files are created once, then overwritten with full contents (never appended-to in place)
- "Append-only" refers to the logical model: decisions are appended to DECISIONS.md, but the file is rewritten atomically each time
- No in-place mutation — every write is a full file rewrite via atomic rename

**Conflict resolution:**
- Concurrent writes to the SAME artifact file: last atomic rename wins (the earlier writer's rename is a no-op if the target file was already replaced)
- The event store resolves conflicts: the daemon replays events in sequence order — the projector writes the correct state regardless of which agent write "won" the filesystem race
- Projector writes always take precedence over agent writes for projector-owned fields — the projector overwrites those fields on every state change event

**index.json rebuild safety:**
- Projector writes to `index.json.tmp`, then atomically renames to `index.json`
- Readers always see a consistent state — either the old index (before rename) or the new index (after rename), never a partially-written file
- If the daemon crashes mid-rebuild, the `.tmp` file is cleaned up on next startup (full rebuild from scratch)

### Concurrent Worktree Rules

Worktrees are the only runtime artifact that involves git operations. The worktree manager enforces these rules:

1. **One worktree per Slice:** D-04 requires one worktree per Slice. Multiple worktrees for the same Slice are forbidden — the worktree manager checks for existing worktree before creating a new one.

2. **Worktree directory naming:** Named by Slice ID: `worktree-slice-{n}/` or the git branch name (e.g., `slice-12-auth-flow/`).

3. **Creation gate:** Worktree is only created when the Slice enters `worktree_ready` state. The worktree manager reads Slice status before creating.

4. **Multiple worktrees CAN coexist:** Each Slice gets its own worktree directory. Multiple Slices can have active worktrees simultaneously — they operate on different directories and different git branches.

5. **Worktree lifecycle:**
   - Created: Slice enters `worktree_ready`
   - Active: Agent runs Steps against worktree during `/state-run slice`
   - Preserved on abandon: If Slice is abandoned (D-13 abandon cascade), worktree is kept for forensics analysis
   - Destroyed on shipped: When Slice transitions to `shipped`, worktree is cleaned up by default
   - Configurable retention: `--keep-worktree` flag on `/state-run` preserves worktree after shipping for post-mortem review

6. **Worktree cleanup:** The worktree manager cleans up stale worktrees on daemon startup — if a worktree directory exists but the Slice is in a terminal state (shipped, abandoned) and the configuration does not preserve it, the worktree is removed.

---

## Section 6: Cross-References to Phase 400 and Plan 401-01

This document depends on the following specifications. Each is referenced by document+section — Phase 400 and Plan 401-01 content is never reproduced.

### Phase 400 Specifications

| Phase 400 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| TIER-ARC.md | Arc directory path (`.state/build/arcs/arc-{n}/`), Arc state machine status values |
| TIER-STAGE.md | Stage directory path (under `arcs/arc-{n}/stages/stage-{n}/`), Stage state machine status values |
| TIER-SLICE.md | Slice directory path (under `.../slices/slice-{n}/`), Slice state machine status values, Step file naming convention (D-04) |
| TIER-STEP.md | Step file convention (flat files, no subdirectory per D-04), Step state machine status values |
| FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding (lines 239–269) | Hierarchical aggregate ID format — slash-delimited parent→child encoding for index keys and projection entries |
| FRONTMATTER-SCHEMAS.md §Field Ownership Rules (TIER-07) | Agent vs Projector field classification — drives `[OWNER]` annotations in the directory tree |
| DESC-SEMANTICS.md §D-16 (lines 180–211) | Decimal insertion ID format — `slice-12.1`, `slice-12.354` |
| DESC-SEMANTICS.md §D-13 | Abandon cascade — worktree preservation on abandon |
| FSM-TABLES.md | Status values per tier — used in STATE.md projection format and consumer documentation |

### Plan 401-01 Specifications

| Plan 401-01 Spec | What This Document Uses From It |
|------------------|--------------------------------|
| ARTIFACT-CATALOG.md (all sections) | Single source of truth for all 13 artifact file paths. Every path in the directory tree is verified against the catalog. |
| ARTIFACT-CATALOG.md §Section 2 — Templates | All 9 template file paths (ARC.md.tmpl through RESEARCH.md.tmpl). Templates section in the directory tree mirrors catalog template entries. |
| ARTIFACT-CATALOG.md §Section 3 — Immutability Rules | Lock trigger timing — used to determine when directories are "frozen" (no new files created) |
| SCHEMA-OWNERSHIP.md §Section 1 | Classification table (Agent/Projector/Hybrid) — drives `[OWNER]` annotations and directory creation ownership rules |

### Plan 401-02 Internal Cross-References

| This Document's Section | Consumed By |
|-------------------------|-------------|
| Section 1 (Directory Tree) | Plan 401-03 CROSS-REFERENCES.md — resolution algorithm uses index.json paths |
| Section 3 (STATE.md Placement) | Plan 401-03 — consistency codes validate projection integrity |
| Section 4 (File Count Strategy) | v41+ daemon initializer — validates reasonable file counts on startup |
| Section 5 (Concurrent Access Rules) | v41+ worktree manager — implements worktree lifecycle per rules |

### Anti-Patterns (Enforced)

- **Do NOT redefine paths:** ARTIFACT-CATALOG.md is the single source of truth for artifact paths. This document references catalog paths — never redefines them.
- **Do NOT use slug-based paths for ID resolution:** ID-based directory naming is mandatory. Slugs are display-only metadata appended to directory names (D-02).
- **Do NOT propose file locking:** Lock-free append-only model is the committed design. Event store is authoritative — filesystem is a projection.
- **Do NOT use competing variable notations:** Only `arc-{n}`, `stage-{n}`, `slice-{n}`, `step-{n}` are permitted. `{arc-id}`, `arc_id`, `arc_{n}` are all invalid.
- **Do NOT add agent-owned directories outside the `arcs/` tree:** `state/`, `templates/`, and root-level files are projector or STATIC. Agent creates only under `arcs/`.

---

## Requirement Cross-Reference

| Requirement | Section(s) | Description |
|-------------|-----------|-------------|
| DSK-01 | Section 1 | Complete annotated directory tree covering every file and directory in `.state/build/` |
| DSK-02 | Section 2 | Naming conventions — ID regex patterns, directory naming, slug derivation, display prefixes |
| DSK-03 | Section 3 | STATE.md placement strategy — consolidated JSON projections, export-state CLI contract, rebuild semantics |
| DSK-04 | Section 4 | File count strategy — per-Step formula, scalability projections, bloat mitigation rationale |
| DSK-05 | *(covered by INDEX-SCHEMA.md — Task 2)* | index.json JSON Schema with rebuild rules |
| DSK-06 | Section 5 | Concurrent access rules — directory creation ownership, lock-free atomic write model, worktree rules |

---

*Design contract for v41+ filesystem layout, naming conventions, STATE.md placement, file count strategy, and concurrent access rules. All 28 catalog paths verified against ARTIFACT-CATALOG.md with no competing notations. Consumed by daemon, projector, CLI commands, worktree manager, and Plan 401-03 cross-reference resolution.*

---

## v41 Amendment

**Amended:** Phase 402 (v41 milestone — Slice-Cycle & Context Window Spec)
**Cause:** SLC-06 / SLC-07 — canonical Slice folder layout + cycle ownership.
**Canonical successor:** [`.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md`](../../../v41/phases/402/specs/SLICE-CYCLE.md) §"Canonical Slice Folder Layout (SLC-06 amended)"

### Effect on this document

Directory tree (DSK-01) Slice subdirectory layout remains authoritative for path shape (`.state/build/arcs/arc-N/stages/stage-N/slices/slice-N/`). SLICE-CYCLE.md §"Canonical Slice Folder Layout" enumerates the per-file producer stage; the two specs are non-conflicting (DIRECTORY-TREE owns paths; SLICE-CYCLE owns producer mapping).

*Original v40 spec text above this amendment block is untouched.*
