# Consistency Validation Codes — W001–W015

> **Design contract for v41+ consistency validation, health checking, and daemon startup gating.**
> Consumed by: v41+ daemon (validate_consistency() startup gate), v41+ projector health module (incremental W-code checks on state.* events), v41+ CLI (state build health command), v42 quality pipeline verifier, v17 TUI dashboard (health status display).

## Section 1: Design Conventions

This document is the single source of truth for consistency validation in the `.state/build/` filesystem. It defines 15 validation codes (W001–W015) that cover every category of inconsistency between the event store, index.json, the filesystem, and artifact frontmatter. It also specifies the `validate_consistency()` function contract — what it checks, what it returns, when it runs, and how it gates daemon startup.

**Foundational rules:**

- **15 codes: W001–W015.** These are stable identifiers — W001 will always mean "Orphan ID in index.json." New codes get new numbers (W016, W017, ...); existing codes are never renumbered. Renumbering would break audit logs, consumer code, and TUI dashboard displays that reference codes by number.
- **Three severity tiers per D-401-16:**
  - **ERROR** — blocks daemon startup, ship, or verify. The inconsistency makes the event stream irreconcilable with the filesystem, creates a data loss risk, or violates a hard architectural constraint (mode isolation, ID uniqueness, state machine validity).
  - **WARNING** — advisory at plan time. The inconsistency indicates degraded information or a projection that is out of sync but can be self-healed by the projector. No data loss risk — the projector can rebuild from the event stream.
  - **INFO** — informational, no action required. The inconsistency is a normal state (e.g., a hash mismatch on a mutable artifact that is expected to change) or a display-only concern.
- **Severity assignment principle (RESEARCH.md pitfall #3):** Only issues that make the event stream irreconcilable with the filesystem (data loss risk) are ERROR. Degraded information that the projector can self-heal is WARNING. Display-only issues with no operational impact are INFO. This principle ensures that daemon startup is only blocked for truly critical inconsistencies — not for minor projection drift.
- **Every W-code has 9 structured properties:** Code, Name, Category, Severity, Trigger, Detection Logic, Resolution, Blocking behavior, and Affected Tiers. Additionally, every code includes a **Severity Rationale** — a 1-sentence explanation of why it received its severity tier, referencing the data-loss-risk principle.
- **The event store is ALWAYS authoritative on mismatch** (REF-06). On any conflict between filesystem state and event store state, the event store wins. The projector rebuilds all projections (STATE.md, index.json) from the event stream. Filesystem state is a derived cache that can be regenerated at any time.

---

## Section 2: W-Code Catalog (REF-05)

### Summary Table

| Code | Name | Category | Severity | Blocks Startup |
|------|------|----------|----------|---------------|
| W001 | Orphan ID in index.json | Projection Health | ERROR | Yes |
| W002 | Stale index (file on disk, missing from index.json) | Projection Health | WARNING | No |
| W003 | Mismatched status (index.json status ≠ artifact frontmatter status) | Projection Health | WARNING | No |
| W004 | Unresolved cross-reference (depends_on[{id}] not in index.json) | Cross-Reference Integrity | ERROR | Yes (if referrer in_progress) |
| W005 | Cross-referenced to descoped (target abandoned/deferred/descoped) | Cross-Reference Integrity | WARNING | No |
| W006 | Missing parent pointer (child lacks arc_id/stage_id/slice_id) | Hierarchy Integrity | ERROR | Yes |
| W007 | Parent-child ID mismatch (child's stage_id ≠ parent actual ID) | Hierarchy Integrity | ERROR | Yes |
| W008 | Invalid state transition (current + pending → invalid per FSM) | State Machine Integrity | ERROR | Yes |
| W009 | Duplicate aggregate ID (two artifacts claim same aggregate ID) | Hierarchy Integrity | ERROR | Yes |
| W010 | Invalid edge type (depends_on[{edge}] not in {blocks, soft, data}) | Cross-Reference Integrity | ERROR | Yes |
| W011 | Cycle detected (DAG cycle in dependency edges) | DAG Integrity | ERROR | Yes |
| W012 | Cross-mode leakage (build artifact refs teach artifact, or vice versa) | Mode Isolation | ERROR | Yes |
| W013 | Stale projection (STATE.md doesn't match event store computed state) | Projection Health | WARNING | No |
| W014 | Invalid decimal ID (double decimal, empty trailing) | ID Format Integrity | ERROR | Yes |
| W015 | Filesystem-vs-event-store divergence (event store says artifact exists, filesystem doesn't) | System Integrity | ERROR | Yes |

**Severity distribution:** 10 ERROR, 4 WARNING, 1 INFO. W005 is WARNING by default but can surface as INFO in edge cases where the descoped target is soft-done via deferment (D-14) — see W005 entry for the nuance.

### W001: Orphan ID in index.json

| Property | Value |
|----------|-------|
| **Code** | W001 |
| **Name** | Orphan ID in index.json |
| **Category** | Projection Health |
| **Severity** | ERROR |
| **Trigger** | An entry exists in index.json but no corresponding file exists on disk at the entry's path. |
| **Detection Logic** | `validate_consistency()` iterates all entries across all four index.json tier sections (`arcs`, `stages`, `slices`, `steps`). For each entry, it checks `os.path.exists(.state/build/{entry.path})`. If the file is missing, the entry is orphaned → W001. |
| **Resolution** | **Manual:** Remove the orphan entry from index.json by deleting the corresponding key from the tier section. **Auto-resolution (D-401-17):** The projector removes orphan entries during daemon restart full rebuild — if the event stream confirms no such aggregate was ever created, the entry is purged. If the event stream does contain a creation event for the aggregate ID but the file is missing, the auto-resolution escalates to W015 (filesystem divergence). |
| **Blocking** | BLOCKS daemon startup (ERROR severity per D-401-17). Rationale: An orphan entry means the projector believes an artifact exists at the mapped path but no file exists. Any ID→path resolution that hits this entry would return a path to a non-existent file, causing "file not found" errors downstream. |
| **Affected Tiers** | All (any tier's artifact can become orphaned if its file is deleted without a corresponding event) |

**Severity Rationale:** Orphan in index means the projector believes an artifact exists that doesn't. Could cause down-path resolution failures where consumers attempt to open non-existent files. ERROR because index is authoritative for ID→path resolution — an incorrect entry breaks the fundamental lookup contract. Fixable in milliseconds (remove the entry or rebuild index).

### W002: Stale index (file on disk, missing from index.json)

| Property | Value |
|----------|-------|
| **Code** | W002 |
| **Name** | Stale index — file on disk, missing from index.json |
| **Category** | Projection Health |
| **Severity** | WARNING |
| **Trigger** | A file exists on disk under `.state/build/` (specifically an artifact file recognized by its filename pattern) but no corresponding entry exists in index.json. |
| **Detection Logic** | `validate_consistency()` walks the `.state/build/arcs/` directory tree, identifying all artifact files by their standard filenames (ARC.md, STAGE.md, SLICE.md, stepNPLAN.md, CRIT.md, MAP.md, DESIGN.md, RESEARCH.md, VERIFICATION.md, SUMMARY.md, DECISIONS.md). For each file found, it extracts the aggregate ID from the file's frontmatter or path. If that ID is NOT present in the corresponding index.json tier section → W002. |
| **Resolution** | **Auto-healing:** The projector will add the entry on the next full or incremental rebuild. No user action required. The projector reads the file's frontmatter, constructs an IndexEntry, and inserts it into the appropriate tier section. **Manual:** Trigger a projector full rebuild via `state build health --rebuild`. |
| **Blocking** | Does NOT block daemon startup. WARNING severity — the index is stale but the projector can self-heal. The missing entry only affects ID→path resolution for that specific artifact until the next rebuild; CLI commands that need to find it by ID would get "not found" temporarily. |
| **Affected Tiers** | All (any tier's artifact file can exist without a corresponding index entry) |

**Severity Rationale:** File exists but index doesn't know about it. The projector can add the entry on next rebuild — no data loss, no irreconcilable state. WARNING because it represents degraded information (the index is not fully current) but not a correctness issue. The filesystem is the ground truth for "what files exist"; the index is a projection that can be regenerated.

### W003: Mismatched status (index.json status ≠ artifact frontmatter status)

| Property | Value |
|----------|-------|
| **Code** | W003 |
| **Name** | Mismatched status |
| **Category** | Projection Health |
| **Severity** | WARNING |
| **Trigger** | The `status` field in an index.json IndexEntry does not match the `status` field in the corresponding artifact's frontmatter. |
| **Detection Logic** | For each entry in index.json, `validate_consistency()` reads the artifact file from disk (if it exists — if it doesn't, W001 handles it), parses the frontmatter, and extracts the `status` field. Compares `entry.status` vs `frontmatter_status`. If they differ → W003. Note: This check only applies to artifacts where the frontmatter `status` field is projector-owned (ARC.md, STAGE.md, SLICE.md, stepNPLAN.md). For agent-owned artifacts without a `status` field (DESIGN.md, RESEARCH.md), the check is skipped. |
| **Resolution** | **Auto-healing:** The projector will correct the index.json status on the next incremental rebuild triggered by a `state.*` event affecting that aggregate. The projector always writes the correct status to index.json based on event stream processing. **Manual:** Trigger a projector full rebuild. |
| **Blocking** | Does NOT block daemon startup. WARNING severity — status mismatch indicates the index is out of sync but the projector can self-heal. The mismatch could cause CLI commands to display stale status information until corrected. |
| **Affected Tiers** | Arc, Stage, Slice, Step (the four tiers where `status` is a projector-owned frontmatter field) |

**Severity Rationale:** Status mismatch between index and frontmatter. The projector can rebuild the index from events — no data loss. WARNING because the mismatch could cause a CLI command to display the wrong status temporarily, but it self-corrects on the next state change event.

### W004: Unresolved cross-reference (depends_on[{id}] not in index.json)

| Property | Value |
|----------|-------|
| **Code** | W004 |
| **Name** | Unresolved cross-reference |
| **Category** | Cross-Reference Integrity |
| **Severity** | ERROR |
| **Trigger** | A `depends_on[{id}]` entry references an aggregate ID that does not exist in index.json — the target was deleted, descoped, or never created. |
| **Detection Logic** | For every artifact that has a `depends_on` frontmatter field, `validate_consistency()` iterates each entry. For each `{id}` value, it calls `resolve_id(id)` (O(1) index.json dictionary lookup per CROSS-REFERENCES.md §Section 2). If `resolve_id()` returns None (not found or malformed format) → W004. The Finding's `detail` includes the unresolved `target_id`. |
| **Resolution** | Per D-401-15, user must choose one of three paths: (1) **Reassign target** — edit `depends_on[{id}]` to point to a different existing aggregate, (2) **Defer dependency** — mark the target as deferred (D-14), which unblocks the referrer with a `deferred_dep` flag, (3) **Remove reference** — delete the `depends_on` entry entirely. The auto-resolution workflow (D-401-17) surfaces each unresolved reference to the user with these options. |
| **Blocking** | BLOCKS daemon startup if the referrer is `in_progress`. If the referrer is in a non-executing state (`planned`, `designing`, `worktree_ready`), the finding is recorded but does NOT block daemon startup — the unresolvable dependency will block execution later when the referrer attempts to enter `in_progress`. The blocked state uses `blocked_reason: "Dependency {target_id} unresolved"`. |
| **Affected Tiers** | Arc, Stage, Slice (the three tiers that support `depends_on` frontmatter). Steps do not have `depends_on` (they run serially within a Slice per D-11). |

**Severity Rationale:** Critical — the referrer has a dependency on a non-existent target. If the referrer is `in_progress`, it is blocked on a phantom dependency and cannot complete. The scheduler's DAG has a broken edge. Must be resolved before daemon operates because the DAG is integral to all execution operations. ERROR with conditional blocking (only blocks if referrer is actively executing).

### W005: Cross-referenced to descoped (target abandoned/deferred/descoped)

| Property | Value |
|----------|-------|
| **Code** | W005 |
| **Name** | Cross-referenced to descoped |
| **Category** | Cross-Reference Integrity |
| **Severity** | WARNING (can be INFO for soft-done deferment) |
| **Trigger** | A `depends_on[{id}]` entry references a target that exists in index.json but has a status of `abandoned`, `deferred`, or a `deferred_dep`/`deferred_data` flag — the target was intentionally descoped from active work. |
| **Detection Logic** | For each `depends_on` entry, `validate_consistency()` resolves the target via `resolve_id(id)`. If the target exists but its `status` is `abandoned` or its entry has a `deferred` flag, and the edge type of the dependency is `blocks` or `data` → W005. For `soft` edges, no warning (soft edges are advisory and the target's descoping releases the constraint). |
| **Resolution** | **Informational for planning.** The user should review whether the dependency still makes sense — if the target is permanently abandoned, the dependency should be reassigned or removed. If the target is deferred (D-14), the referrer is already unblocked with a `deferred_dep` flag per CROSS-REFERENCES.md §Section 5 — the W005 finding confirms to the user that this transition occurred. |
| **Blocking** | Does NOT block daemon startup. WARNING severity — the target was intentionally descoped by the user. This is a planning decision, not a system error. The scheduler already handles descoped targets per the broken reference cascade rules (CROSS-REFERENCES.md §Section 5). |
| **Affected Tiers** | Arc, Stage, Slice |

**Severity Rationale:** Target was intentionally descoped (abandoned/deferred) by user decision. Not a system error — the user knows the target is descoped because they initiated the abandon or defer. WARNING for blocks/data edges because the dependency chain has a permanent gap; advisory for planning review. **Nuance:** If the target is deferred and the referrer is already proceeding with `deferred_dep`, W005 can be downgraded to INFO — the system has already adapted and no action is needed. This is the only W-code that crosses the WARNING/INFO boundary based on context.

### W006: Missing parent pointer

| Property | Value |
|----------|-------|
| **Code** | W006 |
| **Name** | Missing parent pointer |
| **Category** | Hierarchy Integrity |
| **Severity** | ERROR |
| **Trigger** | A child artifact (Stage, Slice, Step) is missing its required parent-reference frontmatter field (`arc_id` for Stages, `stage_id` for Slices, `slice_id` for Steps). |
| **Detection Logic** | For each non-Arc artifact found on disk, `validate_consistency()` reads the frontmatter and checks for the required parent field: (1) For STAGE.md artifacts: `arc_id` must be present and non-empty. (2) For SLICE.md artifacts: `stage_id` must be present and non-empty. (3) For stepNPLAN.md artifacts: `slice_id` must be present and non-empty. If the required field is missing, null, or empty → W006. The check also validates that the parent field value is a valid aggregate ID format (matches D-01 regex). |
| **Resolution** | **Manual:** Edit the child artifact's frontmatter to add the correct parent reference field. The child's hierarchical ID can be derived from its path (e.g., `arcs/arc-1/stages/stage-3/slices/slice-12/SLICE.md` → `stage_id: "stage-3"`), but the user should verify the intent. **Auto-resolution:** The projector can derive the parent ID from the filesystem path during full rebuild and populate the frontmatter field, but this requires user confirmation to avoid silent corrections. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: A child without a parent pointer breaks hierarchical traversal — the DAG cannot determine the child's position in the hierarchy, the projector cannot compute parent aggregate counts, and CLI commands cannot resolve "show me all Slices in Stage-3." |
| **Affected Tiers** | Stage, Slice, Step |

**Severity Rationale:** Child without parent pointer breaks hierarchical traversal. Cannot resolve child's place in the DAG. Fundamental structural integrity — the hierarchy is the backbone of the system. ERROR because without parent pointers, projection computations, DAG building, and path resolution all fail or produce incorrect results.

### W007: Parent-child ID mismatch

| Property | Value |
|----------|-------|
| **Code** | W007 |
| **Name** | Parent-child ID mismatch |
| **Category** | Hierarchy Integrity |
| **Severity** | ERROR |
| **Trigger** | A child artifact's parent-reference field (`arc_id`, `stage_id`, `slice_id`) specifies a parent ID that does not match the actual parent directory structure — the parent field contradicts the filesystem location. |
| **Detection Logic** | For each non-Arc artifact, `validate_consistency()` extracts the parent ID from both sources: (1) From frontmatter: the `arc_id`/`stage_id`/`slice_id` field. (2) From the filesystem path: parse the directory hierarchy to derive the expected parent ID (e.g., `arcs/arc-3/stages/stage-2/slices/slice-5/SLICE.md` → expected `stage_id` = `stage-2`). If frontmatter parent ID ≠ filesystem-derived parent ID → W007. |
| **Resolution** | **Manual:** The user must reconcile the mismatch. Either: (1) The frontmatter parent field is wrong — edit it to match the directory structure, or (2) The directory structure is wrong — the artifact file was placed in the wrong location, requiring a move or a Snapshot-and-recreate. **Auto-resolution:** The resolution workflow presents both values and asks the user which is correct. It can then apply the chosen fix (edit frontmatter or move the file). |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: "Stage claims to be child of Arc-5 but directory is under Arc-3" — fundamental data inconsistency. The DAG cannot determine the artifact's true position, leading to incorrect parent aggregate computations and potentially wrong dependency resolution. |
| **Affected Tiers** | Stage, Slice, Step |

**Severity Rationale:** "Stage claims to be child of Arc-5 but directory is under Arc-3" — fundamental data inconsistency. The projector cannot determine the artifact's true position. ERROR because two authoritative sources (frontmatter and filesystem) disagree on a structural fact — the inconsistency must be resolved before any hierarchy-dependent operation can proceed.

### W008: Invalid state transition

| Property | Value |
|----------|-------|
| **Code** | W008 |
| **Name** | Invalid state transition |
| **Category** | State Machine Integrity |
| **Severity** | ERROR |
| **Trigger** | An event in the event stream would transition an aggregate from its current state to a new state that is not a valid transition per the FSM tables defined in Phase 400 FSM-TABLES.md. |
| **Detection Logic** | `validate_consistency()` reads the event stream from the event store and replays it (deterministic replay) to compute the expected state of each aggregate. It then compares the replayed state sequence against the FSM transition tables. For each step where the current state + event type is not a valid transition in the FSM table for that tier → W008. Example: A Slice is `planned` but the event stream contains `state.slice.shipped` (would bypass `in_progress` and `worktree_ready` states). |
| **Resolution** | **Projector full rebuild reconciliation:** The projector replays the event stream from genesis and reconstructs the aggregate's correct state sequence. If the invalid transition is in the event stream itself (a corrupted event), the resolution workflow surfaces the event to the user for review. The user can either: (1) Mark the event as a known anomaly (adds an `ignored` flag to the event), or (2) Rewind to the last valid checkpoint and discard subsequent events. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: An invalid state transition indicates either event stream corruption or a projector bug. The aggregate's computed state would be different from what the FSM specifies, breaking all state-dependent operations (scheduler gating, projector counts, CLI status display). |
| **Affected Tiers** | Arc, Stage, Slice, Step |

**Severity Rationale:** "Slice is planned but event says state.slice.shipped" — state machine violation. Data integrity issue. The event stream and FSM disagree on what the valid state progression is. ERROR because this breaks all state-dependent operations. The event stream is the authoritative source, but if it contains an impossible transition, the system cannot trust its own history.

### W009: Duplicate aggregate ID

| Property | Value |
|----------|-------|
| **Code** | W009 |
| **Name** | Duplicate aggregate ID |
| **Category** | Hierarchy Integrity |
| **Severity** | ERROR |
| **Trigger** | Two or more artifacts in the same tier section claim the same aggregate ID. E.g., two SLICE.md files both have `id: "slice-12"` under the same parent Stage. |
| **Detection Logic** | For each tier section in index.json (`arcs`, `stages`, `slices`, `steps`), `validate_consistency()` checks for duplicate keys. This is primarily an index.json integrity check — the JSON spec enforces unique keys within an object, so a properly-formed index.json cannot have duplicate keys. However, the check also validates across the filesystem: for each tier, collect all aggregate IDs from artifact frontmatters and check for duplicates. If two distinct files claim the same ID → W009. |
| **Resolution** | **Manual:** The user must reassign one of the duplicate artifacts a new aggregate ID. This may require: (1) Editing the artifact's `id` frontmatter field to a new unique value, (2) Renaming the artifact's directory to match the new ID (if the path encodes the ID), (3) Updating all cross-references that pointed to the reassigned artifact's old ID. This is a significant operation that may require a Slice-level re-plan. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: Two Arcs claim `arc-1`. Cannot distinguish them — every ID→path resolution, every cross-reference, every CLI command that operates by ID would be ambiguous. This is a fundamental identity violation. |
| **Affected Tiers** | All |

**Severity Rationale:** Two distinct artifacts claim the same aggregate ID. Cannot distinguish them — fundamental identity violation. ERROR because aggregate IDs are the primary key for all artifact operations. Duplicate IDs break every consumer that looks up an artifact by ID (which is all of them).

### W010: Invalid edge type

| Property | Value |
|----------|-------|
| **Code** | W010 |
| **Name** | Invalid edge type |
| **Category** | Cross-Reference Integrity |
| **Severity** | ERROR |
| **Trigger** | A `depends_on[{edge}]` value is not one of `blocks`, `soft`, `data` — the value does not match the scheduler's `EdgeKind = Literal["blocks", "soft", "data"]` per `src/state_core/scheduler.py` line 15. |
| **Detection Logic** | For every `depends_on` entry across all artifacts, `validate_consistency()` checks the `edge` value. Valid values: `"blocks"`, `"soft"`, `"data"` (case-sensitive, lowercase only). Any value outside this set → W010. The Finding's `detail` includes the invalid edge value and the artifact that declared it. |
| **Resolution** | **Manual:** Edit the `depends_on[{edge}]` to one of the three valid values. The auto-resolution workflow (D-401-17) surfaces the invalid edge to the user — it does NOT auto-correct because the intended semantics are unknown. The user must choose which valid edge type was intended. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: An unknown edge type ("requires", "needs", "triggers", etc.) breaks the scheduler's EdgeKind validation. The scheduler cannot determine the edge's semantics (hard prerequisite? advisory? artifact-producing?), making DAG building impossible for edges involving this dependency. All W010 findings must be resolved before the DAG can be built. |
| **Affected Tiers** | Arc, Stage, Slice |

**Severity Rationale:** Unknown edge type "requires" breaks scheduler EdgeKind validation. Edge semantics are undefined — cannot determine if this is a hard prerequisite, advisory, or artifact-producing. The scheduler's DAG has an edge it cannot classify. ERROR because the entire dependency resolution system is built on the three EdgeKind values; an invalid value makes the edge unprocessable.

### W011: Cycle detected

| Property | Value |
|----------|-------|
| **Code** | W011 |
| **Name** | Cycle detected |
| **Category** | DAG Integrity |
| **Severity** | ERROR |
| **Trigger** | The dependency graph contains a cycle — a path of `depends_on` edges that leads from an artifact back to itself. E.g., A depends on B, B depends on C, C depends on A. Self-references (A depends on A) are a trivial 1-node cycle. |
| **Detection Logic** | `validate_consistency()` builds the full dependency graph from all `depends_on` entries across all artifacts. It then runs a cycle detection algorithm (e.g., Tarjan's strongly connected components, or a depth-first search with back-edge detection). Any SCC with more than one node, or any self-loop → W011. The Finding's `detail` includes the cycle path (the sequence of artifact IDs that form the cycle). |
| **Resolution** | **Manual:** The user must break the cycle by removing or reassigning one of the edges in the cycle. The auto-resolution workflow (D-401-17) surfaces the cycle path and identifies the most recently added edge in the cycle (by event timestamp or dependency declaration order). It proposes removing that edge, but the user must confirm. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: A cycle in the DAG means the scheduler cannot compute a valid topological sort. There is no valid execution order — every node in the cycle is waiting for another node in the cycle. The scheduler would deadlock. |
| **Affected Tiers** | Arc, Stage, Slice (any tier that supports `depends_on`) |

**Severity Rationale:** A→B and B→A cycle in DAG. Scheduler cannot resolve — no valid topological order exists. ERROR because the entire scheduling system relies on a DAG (Directed Acyclic Graph). A cycle makes the graph non-acyclic, breaking the fundamental data structure of the scheduler.

### W012: Cross-mode leakage

| Property | Value |
|----------|-------|
| **Code** | W012 |
| **Name** | Cross-mode leakage |
| **Category** | Mode Isolation |
| **Severity** | ERROR |
| **Trigger** | A build-mode artifact (under `.state/build/`) has a `depends_on[{id}]` that resolves to a teach-mode artifact (under `.state/teach/`), or vice versa. |
| **Detection Logic** | For each `depends_on` entry, `validate_consistency()` resolves the target via `resolve_id()` which returns the target's IndexEntry with its `path`. It checks whether the target's path starts with `.state/build/` or `.state/teach/`. It then checks the referrer's own path (also extracted from its IndexEntry or filesystem location). If the subtree prefixes differ (`build` vs `teach`) → W012. The authoritative mode prefixes are defined in `src/state_core/schema.py`: `BUILD_SUBTREE = ".state/build"`, `TEACH_SUBTREE = ".state/teach"`. |
| **Resolution** | **Manual:** The user must either: (1) **Reassign** the dependency to a same-mode target, or (2) **Remove** the dependency if it was declared in error. Cross-mode dependencies are never valid (mode isolation is a hard architectural constraint per v11). The auto-resolution workflow surfaces the cross-mode reference to the user but does NOT auto-correct — the user must decide. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: Cross-mode dependencies violate the mode isolation defense-in-depth (v11). Build and teach artifacts exist in physically separate subtrees with separate MCP servers, separate command namespaces, and separate event prefixes. A cross-mode reference would attempt to bridge these two isolated systems, potentially causing mode-gate violations during execution. |
| **Affected Tiers** | Arc, Stage, Slice |

**Severity Rationale:** Build referencing teach breaks mode isolation (v11). Defense-in-depth violation — the entire architecture separates build and teach into physically isolated subtrees. A cross-mode reference attempts to bridge two systems that are designed to be mutually exclusive. ERROR because mode isolation is a cardinal architectural rule with 6 enforcement layers; a cross-mode dependency bypasses all of them.

### W013: Stale projection

| Property | Value |
|----------|-------|
| **Code** | W013 |
| **Name** | Stale projection |
| **Category** | Projection Health |
| **Severity** | WARNING |
| **Trigger** | A STATE.md projection file (`.state/build/state/arcs.json`, `stages.json`, `slices.json`, `steps.json`) contains state information that does not match the state computed by replaying the event stream. |
| **Detection Logic** | `validate_consistency()` replays the event stream from the event store to compute the expected state of each aggregate. It then reads the corresponding STATE.md projection file and compares the computed state against the projected state. If they differ for any aggregate → W013. The Finding's `detail` includes the aggregate ID, expected state (from event stream replay), and actual state (from projection file). |
| **Resolution** | **Auto-healing:** The projector will overwrite the projection on the next state change event for the affected aggregate. The projection is derived from the event stream — it is a cache, not an authoritative source. **Manual:** Trigger a projector full rebuild via `state build health --rebuild`. |
| **Blocking** | Does NOT block daemon startup. WARNING severity — the projection is stale but the projector can self-heal. Stale projections only affect read-only consumers (TUI dashboard, CLI status display) and will be corrected on the next write. |
| **Affected Tiers** | All (STATE.md projections exist per tier: arcs.json, stages.json, slices.json, steps.json) |

**Severity Rationale:** STATE.md projection stale. The projector will overwrite on next state change — no data loss because the projection is derived from the event stream (a read model, not the write model). WARNING because stale projections could cause the TUI dashboard or CLI to display outdated status information temporarily until the projector catches up.

### W014: Invalid decimal ID

| Property | Value |
|----------|-------|
| **Code** | W014 |
| **Name** | Invalid decimal ID |
| **Category** | ID Format Integrity |
| **Severity** | ERROR |
| **Trigger** | An aggregate ID uses a decimal insertion format (`stage-{n}.{d}` or `slice-{n}.{d}`) that violates the D-16 decimal insertion rules: double decimal (`slice-12.1.2`), empty trailing decimal (`slice-12.`), non-numeric decimal portion (`slice-12.abc`), or a decimal insertion applied to a non-insertion tier (`arc-1.5`). |
| **Detection Logic** | `validate_consistency()` parses every aggregate ID in index.json (keys across all four tier sections) against the D-16 regex: `^(arc|stage|slice)-[1-9][0-9]*(\.[0-9]+)?$` for Arc/Stage/Slice; `^step-[1-9][0-9]*$` for Step (Steps do not support decimal insertion — they are always whole numbers per D-04). Violations: (1) Double decimal: matches `\.[0-9]+\.[0-9]+` → W014. (2) Empty trailing: matches `\.$` → W014. (3) Non-numeric: matches `\.[a-zA-Z]` → W014. (4) Step with decimal: `step-{n}.{d}` → W014. (5) Arc with decimal: `arc-{n}.{d}` → W014 (decimal insertion is only valid for Stage and Slice tiers per D-16). |
| **Resolution** | **Manual:** Reassign the aggregate ID to a valid format. For decimal insertion errors (double decimal), the user must choose which single-decimal value was intended. For Arc decimal or Step decimal, remove the decimal entirely. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: An invalid decimal ID violates the D-16 format constraint. The ID cannot be parsed correctly — hierarchical key construction, parent extraction, and tier prefix detection would all produce incorrect results for malformed IDs. |
| **Affected Tiers** | Stage, Slice (for decimal insertion errors), Arc, Step (for decimal-on-non-insertion-tier errors) |

**Severity Rationale:** `slice-12.1.2` violates D-16 single-decimal-level constraint. The ID format is irreconcilable — hierarchical key construction and parent extraction depend on deterministic parsing of the ID string. ERROR because a malformed ID breaks all operations that parse the ID (which is every operation that references the artifact).

### W015: Filesystem-vs-event-store divergence

| Property | Value |
|----------|-------|
| **Code** | W015 |
| **Name** | Filesystem-vs-event-store divergence |
| **Category** | System Integrity |
| **Severity** | ERROR |
| **Trigger** | The event store (`.state/events.sqlite`) contains events indicating that an artifact was created (e.g., `state.slice.created`) but no corresponding file exists on disk at the expected path. This is the inverse of W001 (which detects orphan index entries without files). W015 detects missing files for events that say the artifact should exist. |
| **Detection Logic** | `validate_consistency()` reads the event stream from `.state/events.sqlite` and collects all `state.{tier}.created` events. For each creation event, it constructs the expected file path from the event payload's aggregate ID and the directory tree layout (per DIRECTORY-TREE.md). It then checks `os.path.exists(.state/build/{expected_path})`. If the file does not exist → W015. The check accounts for artifacts that may have been intentionally deleted (those would have a corresponding `state.{tier}.deleted` event in the stream — if such an event exists, the missing file is expected and not a divergence). |
| **Resolution** | **Auto-resolution (projector full rebuild):** The projector replays the event stream from genesis and recreates any missing files by reconstructing their frontmatter and body content from the events. If the event stream contains enough information to reconstruct the artifact (frontmatter fields + body prose from snapshot events), the projector regenerates the file. If the event stream does NOT contain enough information (e.g., body prose was never snapshotted), the projector creates a placeholder file with reconstructed frontmatter and a `MISSING_CONTENT` marker. **Manual:** Restore the file from a backup or Snapshot. |
| **Blocking** | BLOCKS daemon startup (ERROR severity). Rationale: The event store — the authoritative source of truth per REF-06 — says an artifact exists but the filesystem disagrees. This is a fundamental divergence between the two primary data stores. While the event store is authoritative, operating with missing files would cause "file not found" errors for any consumer that reads artifacts by path. |
| **Affected Tiers** | All |

**Severity Rationale:** Event store says artifact was created but no file on disk. Fundamental divergence — the two primary data stores disagree on the state of the world. ERROR because the event store is authoritative per REF-06, but operating with missing files would cause runtime failures. The divergence must be resolved (either by recreating the files from events or by acknowledging the deletion and purging the creation events) before the daemon can operate.

---

## Section 3: validate_consistency() Function Specification (REF-06)

> **DESIGN CONTRACT NOTICE:** This is a FUNCTION CONTRACT — not pseudocode, not implementation. It specifies WHAT validate_consistency() does: its inputs, checks, output format, and execution timing. v41+ implements HOW.

### Purpose

Walk all artifacts in `.state/build/`, verify every cross-reference resolves to an existing ID, detect filesystem-vs-event-store divergence, and report all inconsistencies as a structured `ConsistencyReport`. The event store is ALWAYS authoritative on any mismatch between filesystem state and event store state (REF-06 requirement).

### Signature

```
validate_consistency() -> ConsistencyReport
```

No parameters — the function reads from the event store, index.json, and filesystem internally. All data sources are accessed through the daemon's standard I/O paths (SQLite connection for events, filesystem for artifacts, JSON parse for index.json).

### Inputs (5 sources)

1. **Event store (`.state/events.sqlite`)** — authoritative source of truth. Read aggregate streams for all known artifacts. The event store provides: creation events (which artifacts exist), state change events (current status of each aggregate), and snapshot events (frontmatter + body content for file reconstruction in W015).

2. **index.json (`.state/build/index.json`)** — projector-rebuilt artifact registry. Source for: ID→path mapping (all tier sections), artifact types, statuses, content hashes. Read once at the start of validation; not re-read during incremental checks (cache is valid for the duration of the function call).

3. **Filesystem (`.state/build/` directory tree)** — actual artifact files on disk. Walked for W002 detection (files without corresponding index entries). Checked per-entry for file existence (W001 detection). Artifact files are read for frontmatter parsing (W003, W006, W007 detection).

4. **All artifact frontmatter files** — parsed for: `depends_on` fields (cross-reference source data for W004, W005, W010), `status` fields (for W003 comparison), parent-reference fields `arc_id`/`stage_id`/`slice_id` (for W006, W007), aggregate `id` fields (for W009 duplication check). Frontmatter is extracted from markdown files (YAML frontmatter between `---` delimiters) and from JSON projection files (direct property access).

5. **Phase 400 FSM transition tables** — reference for W008 state transition validity checks. Read from FSM-TABLES.md (or its machine-readable equivalent). The function does not re-implement FSM logic — it delegates to the FSM module's transition validation function, passing (current_state, event_type, tier) and receiving (valid: bool).

### Checks Performed (15 checks, W001–W015)

The checks are ordered by category for logical grouping. The function may parallelize checks within categories (e.g., all Projection Health checks can run concurrently since they read different data sources). Categories that depend on prior results (e.g., DAG Integrity depends on Cross-Reference Integrity to identify which edges to include) run sequentially after their dependencies.

| Category | Checks | Description |
|----------|--------|-------------|
| **Projection Health** | W001, W002, W003 | Index-to-filesystem and index-to-frontmatter consistency. W001: orphans in index. W002: files without index entries. W003: status mismatch between index and frontmatter. |
| **Cross-Reference Integrity** | W004, W005, W010 | Dependency graph edge validation. W004: unresolved IDs. W005: references to descoped targets. W010: invalid edge types. |
| **Hierarchy Integrity** | W006, W007, W009 | Structural parent-child relationships. W006: missing parent pointers. W007: parent ID mismatch. W009: duplicate aggregate IDs. |
| **State Machine Integrity** | W008 | FSM transition validity. Compares event stream state progression against Phase 400 FSM-TABLES.md. |
| **DAG Integrity** | W011 | Cycle detection in the full dependency graph. Runs after Cross-Reference Integrity checks have identified all valid edges. |
| **Mode Isolation** | W012 | Cross-mode reference detection. Validates that no dependency crosses the `.state/build/` ↔ `.state/teach/` boundary. |
| **ID Format Integrity** | W014 | Decimal ID format validation against D-16 rules. Runs on all aggregate IDs in index.json. |
| **System Integrity** | W015 | Filesystem-vs-event-store divergence. The most comprehensive check — replays the event stream and validates that every creation event has a corresponding file. |

### Output: ConsistencyReport

```
ConsistencyReport {
    daemon_startup_blocked: bool,
        // true if any ERROR-severity Finding exists where the referrer
        // is in_progress (for W004, W011) or where the ERROR is
        // unconditional (W001, W006-W012, W014, W015).
        // false if no ERROR findings or all ERROR findings affect
        // non-executing referrers.

    errors: list[Finding],
        // All ERROR-severity findings. Sorted by artifact_id then code.
        // This is the list passed to the auto-resolution workflow.

    warnings: list[Finding],
        // All WARNING-severity findings. Sorted by artifact_id then code.
        // Logged at daemon startup; displayed in TUI health dashboard.

    infos: list[Finding],
        // All INFO-severity findings. Sorted by artifact_id then code.
        // Logged at daemon startup; displayed in TUI health dashboard
        // under "info" filter.

    total_artifacts_checked: int,
        // Count of all artifacts examined (sum of entries across all
        // four index.json tier sections + any filesystem-only artifacts
        // detected in W002).

    total_cross_references_checked: int,
        // Total number of depends_on entries examined across all
        // artifacts. Includes all edge types (blocks, soft, data).

    event_store_sequence: int,
        // Sequence number of the last processed event from the event
        // store. Used for incremental check skip optimization — events
        // with sequence ≤ this value have already been validated.

    duration_ms: int,
        // Wall-clock duration of the validate_consistency() call in
        // milliseconds. Used for performance monitoring and to detect
        // regressions as the artifact tree grows.
}

Finding {
    code: str,
        // "W001" through "W015". The consistency code.

    severity: Literal["ERROR", "WARNING", "INFO"],
        // Severity tier per D-401-16.

    artifact_id: str,
        // Hierarchical aggregate ID of the affected artifact.
        // E.g., "arc-3/stage-2/slice-5" for a Slice-level finding.
        // This is the full hierarchical ID for unambiguous identification.

    path: str | None,
        // Filesystem path of the affected artifact, relative to
        // .state/build/ root. None if the artifact does not have a
        // filesystem presence (e.g., referenced but never created).

    message: str,
        // Human-readable description of the inconsistency.
        // Format: "W{NNN}: {name} — {specific detail}."
        // Example: "W004: Unresolved cross-reference — slice-12
        // depends_on[{id: 'slice-99'}] not found in index.json."

    detail: dict | None,
        // Structured detail for programmatic consumption.
        // Schema varies by W-code:
        //   W004, W005: {"target_id": str, "edge": str}
        //   W006: {"missing_field": str, "tier": str}
        //   W007: {"expected_parent": str, "actual_parent": str}
        //   W008: {"current_state": str, "event_type": str, "expected_state": str}
        //   W009: {"duplicate_id": str, "paths": [str, str]}
        //   W010: {"invalid_edge": str, "valid_values": ["blocks", "soft", "data"]}
        //   W011: {"cycle_path": [str, ...]}
        //   W012: {"referrer_subtree": str, "target_subtree": str, "target_id": str}
        //   W014: {"invalid_id": str, "violation": str}
        //   W015: {"missing_path": str, "event_type": str, "event_sequence": int}
        //   W001-W003, W013: None (prose message is sufficient)
}
```

### Execution Timing (3 trigger points)

| Timing | Scope | Behavior |
|--------|-------|----------|
| **Daemon startup (D-401-17)** | **Full check** — all artifacts across all tiers. | Runs BEFORE the HTTP server binds. The daemon process starts, loads index.json, connects to the event store, and calls validate_consistency(). If `daemon_startup_blocked == true` → daemon auto-launches the resolution workflow (per Auto-Resolution Path below), does NOT bind the HTTP server. If `daemon_startup_blocked == false` → daemon logs the warnings and infos, binds the HTTP server, and starts normal operation. The full check at startup is the primary gating mechanism — it ensures the daemon never operates on an inconsistent state. |
| **Post-state-change** | **Incremental check** — only artifacts affected by the state change event. | Runs after the projector processes every `state.*` event. The projector identifies which aggregate(s) were affected by the event (direct target + cascade parents). validate_consistency() runs a scoped check on just those aggregates: W003 (status mismatch for the changed aggregate), W004/W005 (cross-references where the changed aggregate is the target), W008 (state transition validity for the event). Incremental checks are fast (single-digit milliseconds) because they touch only 1-3 artifacts. They do NOT block daemon operation — the daemon is already running. Findings are logged and emitted as SSE events for TUI dashboard updates. |
| **On-demand (CLI: `state build health`)** | **Full check or scoped** — user specifies `--tier`, `--id`, or `--category` filters. | User-invoked via `state build health` CLI command. Runs validate_consistency() and returns the ConsistencyReport to stdout (formatted as JSON or a rich table). Does NOT block daemon operation — the daemon is already running and this is a read-only diagnostic. Supports filters: `--tier arc` (only check Arc tier), `--id arc-3/stage-2` (only check a specific aggregate), `--category "Cross-Reference Integrity"` (only run W004, W005, W010 checks). Also supports `--force` flag: start daemon even if ERROR findings exist (overrides daemon_startup_blocked). |

### Authority Rule (REF-06 Requirement)

**On any mismatch between filesystem state and event store state: the event store is authoritative.**

This rule applies specifically to W013 (stale projection) and W015 (filesystem-vs-event-store divergence):

- For W013: The event store's computed state (from replay) is authoritative. The STATE.md projection is a derived cache — it is overwritten to match the event store's computed state, not the other way around.
- For W015: The event store's creation events are authoritative. If the event store says an artifact exists but the filesystem doesn't, the projector attempts to recreate the file from event data. If the filesystem has files that the event store doesn't know about (W002), the projector adds them to the index — the filesystem is evidence of existence, but the event store determines the artifact's history and state.

This authority rule is fundamental to the event-sourced architecture: the event stream is the write model (source of truth), and all projections (index.json, STATE.md, TUI displays) are read models that can be regenerated from the event stream at any time.

### Auto-Resolution Path (D-401-17)

When ERROR-severity codes block daemon startup:

1. **Collect ERROR findings.** The daemon aggregates all Finding objects with `severity == "ERROR"` into a resolution context. The resolution context is a structured JSON object containing: the list of ERROR findings, the event_store_sequence, the daemon's process ID, and a timestamp.

2. **Launch resolution session.** The daemon auto-launches an opencode subagent (or an equivalent session) with the resolution context as input. The subagent's prompt instructs it to iterate findings and resolve each one. The resolution session has access to the filesystem, index.json, and the event store (read-write for resolution actions, read-only for consultation).

3. **Resolve per-code.** For each ERROR finding, the resolution session applies the code-specific resolution path:
   - **W001:** Removes orphan index entries. If the event stream confirms no creation event exists for the orphan ID → the entry is purged from index.json. If a creation event does exist → escalates to W015 handling.
   - **W006/W007/W009:** Reconciles hierarchy from event stream. For W006 (missing parent), derives parent ID from filesystem path. For W007 (mismatch), presents both values and asks user which is correct. For W009 (duplicate), identifies both claimants and asks user which to reassign.
   - **W004:** Surfaces each unresolved cross-reference to the user with the three resolution options (reassign target, defer dependency, remove reference — per D-401-15 and CROSS-REFERENCES.md §Section 5).
   - **W008/W014/W015:** Triggers projector full rebuild from event stream. W008 replays event stream to detect invalid transitions and asks user whether to acknowledge. W014 logs invalid IDs and asks user to reassign. W015 attempts file reconstruction from event stream snapshots.
   - **W010:** Validates edge type against scheduler EdgeKind. Reports the corrupt reference to the user — auto-correction is not attempted because the intended semantics are unknown.
   - **W011:** Identifies the cycle path. Proposes breaking the cycle by removing the most recently added edge in the cycle (based on event timestamp or `last_updated` field). User must confirm.
   - **W012:** Surfaces cross-mode reference. User must reassign or remove — cross-mode is never auto-resolved.

4. **Restart daemon.** After all ERROR findings are resolved (resolution session exits with success), the resolution workflow restarts the daemon. The daemon re-runs validate_consistency() on startup — if clean, it binds the HTTP server and starts normal operation.

5. **Handle failure.** If the resolution session fails (e.g., unresolvable W015 where event stream is corrupted and files cannot be reconstructed), the daemon:
   - Writes a crash report to `.state/build/crash/daemon-startup-failed-{timestamp}.json` containing the full ConsistencyReport and the resolution session's failure details.
   - Exits with a non-zero status code and a log message indicating which findings could not be resolved.
   - Does NOT enter a restart loop — each resolution attempt is a single session. If it fails, the user must intervene manually.

6. **Non-deadlock path.** The user can invoke `state build health --force` to start the daemon with ERRORS logged but not blocking. The `--force` flag overrides `daemon_startup_blocked` and allows the daemon to bind its HTTP server despite ERROR findings. This is a manual override for when the user has reviewed the ERROR findings and decided they are acceptable (e.g., W004 findings for referrers that will never enter `in_progress` during this session). The daemon logs a prominent warning on startup when `--force` is used.

---

## Section 4: W-Code to Requirement Traceability

| Code | Requirement | Phase 400 / Phase 401 Reference |
|------|------------|--------------------------------|
| W001 | DSK-05 (index.json integrity) | INDEX-SCHEMA.md §Projector Rebuild Rules — orphan cleanup during full rebuild |
| W002 | DSK-05 (index.json completeness) | INDEX-SCHEMA.md §Incremental Rebuild — filesystem walk adds missing entries |
| W003 | DSK-05 (index.json accuracy) | INDEX-SCHEMA.md §Trigger Events → Index Updates — projector keeps index in sync |
| W004 | REF-01 (cross-reference format) | CROSS-REFERENCES.md §Section 5 — unresolved cross-reference handling |
| W005 | REF-04 (broken reference handling) | CROSS-REFERENCES.md §Section 5 — descoped target handling; DESC-SEMANTICS.md §D-13/D-14 |
| W006 | DSK-01 (directory tree structure) | ARTIFACT-CATALOG.md §Section 1 — parent reference fields per artifact type |
| W007 | DSK-01 (directory tree integrity) | FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding — hierarchical ID encoding |
| W008 | FSM-01 (state transitions) | FSM-TABLES.md — all state transition tables per tier |
| W009 | DSK-02 (naming conventions) | D-01 ID format — aggregate ID uniqueness; FRONTMATTER-SCHEMAS.md §id field |
| W010 | REF-02 (edge type semantics) | CROSS-REFERENCES.md §Section 3 — edge validation; scheduler EdgeKind literal |
| W011 | REF-03 (dependency policy) | CROSS-REFERENCES.md §Section 4 — D-10 same-parent constraint; cycle detection |
| W012 | REF-03 (cross-mode blocking) | CROSS-REFERENCES.md §Section 4 — cross-mode detection; schema.py BUILD_ONLY/TEACH_ONLY prefixes |
| W013 | REF-06 (validate_consistency authority) | DESC-SEMANTICS.md §Composite Cascade — projector rebuild from events |
| W014 | D-16 (decimal insertion) | DESC-SEMANTICS.md §Decimal Insertion — single-decimal-level constraint |
| W015 | REF-06 (event store authoritative) | CROSS-REFERENCES.md §Section 5 — authority rule; COMPOSITE-CASCADE.md — event stream replay |

---

## Section 5: Cross-References to Phase 400 and Phase 401 Specifications

This document depends on the following specifications. Each is referenced by document+section — Phase 400 and Phase 401 content is never reproduced here.

### Phase 400 Specifications

| Phase 400 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| **FSM-TABLES.md** | State transition tables for all four tiers — used in W008 detection logic to validate that each state transition in the event stream is valid for the given tier and current state. |
| **FRONTMATTER-SCHEMAS.md** §Cross-Tier ID Encoding (lines 239–269) | Hierarchical aggregate ID format — used in W014 decimal ID validation and W006/W007 parent pointer checks. The parent extraction algorithm is used to derive expected parent IDs from filesystem paths. |
| **FRONTMATTER-SCHEMAS.md** §Field Ownership Rules (TIER-07) | Agent vs. Projector field classification — used in W003 to determine which frontmatter fields are projector-owned (status) and therefore comparable against index.json. |
| **DESC-SEMANTICS.md** §Abandon Cascade (D-13), Deferment (D-14), Blocked State (D-15) | Target state cascade rules — used in W005 detection logic to determine whether a descoped target should trigger a WARNING (abandoned) or INFO (deferred with soft-done treatment). Also used in the broken reference cascade rules referenced by the resolution workflow. |
| **DESC-SEMANTICS.md** §Decimal Insertion (D-16) | Decimal ID format rules — used in W014 detection logic to validate that decimal insertions have a single decimal level and are only applied to Stage and Slice tiers. |
| **EVENT-TAXONOMY.md** | Event type names — used in W008 (identifying state change events for transition validation) and W015 (identifying creation events for filesystem existence checks). |
| **COMPOSITE-CASCADE.md** | Composite event rules — used in W013 to understand how composite state changes propagate, ensuring the projection replay correctly handles cascading state updates. |

### Phase 401 Specifications

| Phase 401 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| **CROSS-REFERENCES.md** (Plan 03 Task 1) §Section 5 | W004/W005/W010/W011 definitions — the broken reference handling rules and edge type semantics in CROSS-REFERENCES.md are the source of truth for these four W-codes. This document's W004, W005, W010, and W011 entries MUST match CROSS-REFERENCES.md §Section 5 exactly. |
| **CROSS-REFERENCES.md** §Section 3 | Edge type semantics — W010 detection logic validates against the same EdgeKind literal and edge validation rules defined in CROSS-REFERENCES.md. |
| **CROSS-REFERENCES.md** §Section 4 | Dependency policy — W011 cycle detection and W012 cross-mode detection logic implement the dependency direction constraints defined in CROSS-REFERENCES.md. |
| **INDEX-SCHEMA.md** (Plan 02) §Section 1 | JSON Schema — W001/W002/W003 detection logic reads index.json structure (tier-separated objects, IndexEntry properties) as specified in INDEX-SCHEMA.md. |
| **INDEX-SCHEMA.md** §Section 3 | Projector rebuild rules — the auto-resolution paths for W001, W002, W013, and W015 rely on the projector's full and incremental rebuild capabilities as specified in INDEX-SCHEMA.md. |
| **ARTIFACT-CATALOG.md** (Plan 01) §Section 1 | Artifact type list — W006 detection logic uses the parent-reference field definitions per artifact type from ARTIFACT-CATALOG.md (arc_id for Stages, stage_id for Slices, slice_id for Steps). |
| **SCHEMA-OWNERSHIP.md** (Plan 01) §Section 1 | Schema owner classifications — W003 detection logic uses schema_owner classification to determine which `status` fields are projector-owned and therefore comparable between index.json and frontmatter. |

### Consumer Attribution

CONSISTENCY-CODES.md is consumed by these v41+ components at these lifecycle points:

| Consumer | When | What It Reads |
|----------|------|---------------|
| **v41+ daemon** | Startup (before HTTP bind) | Reads validate_consistency() function contract to implement the startup gate. Checks `daemon_startup_blocked` to decide whether to bind HTTP or launch resolution workflow. Reads all W-code definitions for error message formatting. |
| **v41+ projector health module** | Every `state.*` event (incremental) | Reads W-code detection logic for incremental checks (W003, W004, W005, W008). Implements scoped validation that only checks the aggregate(s) affected by the event. |
| **v41+ CLI (`state build health`)** | On-demand (user-invoked) | Reads ConsistencyReport/Finding output format to render results. Supports category/tier/ID filters derived from W-code categories. |
| **v41+ resolution workflow subagent** | Daemon startup blocked (D-401-17) | Reads auto-resolution path (6-step flow) and per-code resolution instructions to implement the automated fix workflow. Reads Finding.detail schema for programmatic fix logic. |
| **v42 quality pipeline verifier** | Pre-ship gate | Runs validate_consistency() as a pre-ship gate. Reads W-code severity distribution to determine which findings block the ship pipeline (ERROR) vs. which are advisory (WARNING/INFO). |
| **v17 TUI dashboard** | Session lifecycle | Reads W-code summaries and severity tiers for health status display. Color-codes findings by severity (red for ERROR, yellow for WARNING, blue for INFO). Displays W-code counts in the status bar. |

---

## Section 6: Anti-Patterns

The following patterns are explicitly forbidden. They are listed here as guardrails for implementers and extenders of this specification.

- **Do NOT produce Python pseudocode with variable assignments, loops, or module imports.** This is a function contract — it describes WHAT validate_consistency() does (inputs, checks, output format, timing). The v41+ developer decides HOW to implement it. Pseudocode would constrain the implementation unnecessarily and would become stale as the implementation evolves.

- **Do NOT assign excessive codes to ERROR severity (pitfall #3).** The 10 ERROR codes in this specification are justified by the data-loss-risk principle — each represents an inconsistency that makes the event stream irreconcilable with the filesystem, breaks a hard architectural constraint, or would cause downstream failures if the daemon operated on the inconsistent state. Review each ERROR code before implementation: is this truly irreconcilable, or could the projector self-heal?

- **Do NOT omit the severity rationale for any code.** Every W-code entry includes a 1-sentence explanation of WHY it received its severity tier. This is critical for future reviewers who may question severity assignments and for the auto-resolution workflow which uses severity to determine which findings to surface to the user.

- **Do NOT define codes that overlap with Phase 400 state machine concerns.** W008 references Phase 400 FSM-TABLES.md for transition validation — it does not redefine the FSM tables. W-code detection logic should delegate to Phase 400 specifications, not reproduce them. Reproduction would create a parallel source of truth that could drift.

- **Do NOT renumber W-codes.** W001–W015 are stable identifiers. If a new consistency check is needed in a future phase, assign it W016 (or the next available number). Renumbering would break every consumer that logs, displays, or filters by W-code number.

- **Do NOT auto-resolve user-facing decisions.** The auto-resolution workflow (D-401-17) automates technical fixes (rebuilding projections, purging orphans) but surfaces all user-facing decisions (reassigning dependencies, resolving duplicates, accepting cycle breaks). Cross-reference resolution, ID reassignment, and cycle breaking all require user confirmation.

- **Do NOT conflate ERROR severity with unconditional blocking.** W004 and W011 are ERROR but only block daemon startup if the referrer is `in_progress`. A planned artifact with an unresolved dependency should not block the daemon — the dependency will be checked again when the referrer attempts to enter `in_progress`. The conditional blocking rule prevents false-positive daemon blocks during early planning phases.

---

## Requirement Cross-Reference

| Requirement | Section(s) | Description |
|-------------|-----------|-------------|
| **REF-05** | Section 2 | 15 consistency validation codes (W001–W015). Each code has structured entry with 9 properties + severity rationale. Severity distribution: 10 ERROR, 4 WARNING, 1 INFO (W005 INFO nuance documented). Summary table provides at-a-glance reference. |
| **REF-06** | Section 3 | validate_consistency() function specification. Signature: `validate_consistency() -> ConsistencyReport`. 5 inputs, 15 checks organized by category. Output: ConsistencyReport (8 fields) and Finding (6 fields) types. Execution timing: 3 trigger points with scoped behaviors. Authority rule: event store authoritative on mismatch. Auto-resolution path: 6-step flow per D-401-17. |

---

*Design contract for v41+ consistency validation, health checking, and daemon startup gating. Complete specification covering REF-05 (15 W-codes with structured entries, severity rationales, and summary table) and REF-06 (validate_consistency() function contract with 5 inputs, 15 checks, ConsistencyReport/Finding output types, 3 timing points, authority rule, and 6-step auto-resolution path). 10 ERROR / 4 WARNING / 1 INFO severity distribution with data-loss-risk justification. Consumed by daemon, projector health module, CLI, resolution workflow, quality pipeline verifier, and TUI dashboard.*
