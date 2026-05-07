# Cross-Reference System: Format, Resolution, Edge Semantics, Dependency Policy, and Broken Reference Handling

> **Design contract for v41+ cross-reference resolution, dependency validation, and broken reference handling.**
> Consumed by: v41+ daemon artifact loader (ID resolution), v41+ scheduler (dependency DAG building, edge enforcement), v41+ projector (index.json cross-reference indexing), v41+ validate_consistency() (W004/W005/W010/W011 checks), v42 quality pipeline verifier.

## Section 1: Design Conventions

This document is the single source of truth for how artifacts in `.state/build/` reference each other, how those references are resolved, how dependency edges constrain the scheduler, and how broken references are detected and handled. It implements REF-01 (cross-reference format), REF-02 (edge type semantics), REF-03 (dependency policy), and REF-04 (broken reference handling) from the Phase 401 requirement set.

**Foundational rules:**

- **All cross-references use stable aggregate IDs — NEVER paths, NEVER slugs.** Per REF-01, references are expressed through the `depends_on` frontmatter field using aggregate IDs that follow the D-01 format (`arc-{n}`, `stage-{n}`, `slice-{n}`, `step-{n}`). Paths change when files are renamed or reorganized; slugs are ambiguous. Aggregate IDs are the stable, unique, and verifiable identity for every artifact.
- **ID resolution via index.json O(1) dictionary lookup.** Per D-401-14, `index.json` has a tier-separated structure (`{arcs: {}, stages: {}, slices: {}, steps: {}}`) enabling O(1) ID→path resolution without filesystem traversal. The resolution algorithm parses the tier prefix from the ID, then performs a single dictionary lookup in the appropriate tier section.
- **Content-hash pinning at cross-reference creation time.** When artifact A creates a cross-reference to artifact B, A can optionally record B's current `content_hash` from index.json. This enables change detection on consistency checks — if B has changed since the reference was created, the mismatch is surfaced with a severity calibrated to B's mutability.
- **Edge types match scheduler `EdgeKind = Literal["blocks", "soft", "data"]` exactly.** No custom edge types are permitted. The three edge types are immutable per `src/state_core/scheduler.py` line 15, which is the canonical source. Phase 401 does not introduce new edge types.
- **Same-parent-only dependency constraint (D-10).** Dependencies are only valid between siblings within the same parent container. A Slice in Stage-3 cannot depend on a Slice in Stage-5. Cross-Arc dependencies are a deferred idea (v42+).
- **Broken references surface-and-block (D-401-15).** When a cross-reference target is deleted, abandoned, or never existed, the reference is flagged with a W-code, and the referrer is blocked if it is `in_progress`. There is no auto-cascade — the user must explicitly reassign, defer, or remove the dependency. This preserves user agency and prevents cascading failures from silently destroying dependent work.

---

## Section 2: Cross-Reference Format (REF-01)

### Depends-On Frontmatter Structure

Cross-references are expressed in the `depends_on` frontmatter field as a list of objects. Each object specifies the target aggregate ID, the edge type, and an optional content hash for change detection.

**YAML format (per Phase 400 D-12):**

```yaml
depends_on:
  - {id: "slice-10", edge: "blocks", hash: "sha256:abc123..."}
  - {id: "stage-02", edge: "soft"}
  - {id: "slice-09", edge: "data", hash: "sha256:def456..."}
```

**Field definitions:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | Yes | String | Short-form aggregate ID — `slice-10`, `stage-02`, `arc-03`. Must match the D-01 format: `{tier}-{n}` with optional single-decimal insertion (`slice-10.5` per D-16). |
| `edge` | Yes | String | One of `blocks`, `soft`, `data` — must match scheduler EdgeKind exactly. Case-sensitive, lowercase only. No custom edge types permitted. |
| `hash` | No | String | SHA-256 content hash of the target artifact at creation time (hex-encoded, prefixed `sha256:`). Pinned for change detection. Omitted if the target does not support hash pinning (e.g., projector-rebuilt artifacts) or if the reference creator opts out. |

**ID resolution within depends_on:**

The `id` field uses the short-form aggregate ID — the same format used in the artifact's own `id` frontmatter field. For Arc-level artifacts, the short form is `arc-{n}`. For child tiers, the short form is `stage-{n}`, `slice-{n}`, or `step-{n}` — the parent context is implicit from the referrer's own hierarchy position. The resolver constructs the hierarchical key (e.g., `arc-1/stage-2/slice-5`) using the referrer's `arc_id`/`stage_id` fields and performs the lookup in the appropriate tier section of index.json.

**Frontmatter field ownership:**

The `depends_on` field is agent-owned across all artifact types that support it (ARC.md, STAGE.md, SLICE.md). The agent writes the depends_on entries during planning. The projector reads depends_on for DAG building and dependency resolution but never modifies the entries directly. This separation is documented in SCHEMA-OWNERSHIP.md.

### ID Resolution Algorithm

The `resolve_id()` algorithm converts an aggregate ID (short or hierarchical form) to an `IndexEntry` by performing an O(1) dictionary lookup in index.json. No filesystem traversal is required.

```
resolve_id(id: str) -> Optional[IndexEntry]

1. Parse the ID to extract the tier prefix:
   - "arc-"   → Tier: arc   → Look in index.arcs
   - "stage-" → Tier: stage → Look in index.stages
   - "slice-" → Tier: slice → Look in index.slices
   - "step-"  → Tier: step  → Look in index.steps

2. Construct the full hierarchical key:
   - Arc:     id itself ("arc-{n}" — root tier, no parent prefix needed)
   - Stage:   From referrer context: "arc-{n}/stage-{n}"
   - Slice:   From referrer context: "arc-{n}/stage-{n}/slice-{n}"
   - Step:    From referrer context: "arc-{n}/stage-{n}/slice-{n}/step-{n}"

3. Look up the full hierarchical key in the appropriate tier section (O(1) dict lookup):
   - index.arcs["arc-{n}"]  or  index.arcs.get("arc-{n}")
   - index.stages["arc-{n}/stage-{n}"]
   - index.slices["arc-{n}/stage-{n}/slice-{n}"]
   - index.steps["arc-{n}/stage-{n}/slice-{n}/step-{n}"]

4. Resolution outcomes:
   a. FOUND → Return the IndexEntry (entry.path gives the filesystem path).
      Cache the result for subsequent lookups (hot path optimization).
   b. NOT FOUND but valid format (matches D-01 regex) → Return None.
      Unresolved cross-reference — triggers W004 (ERROR) on consistency check.
   c. INVALID FORMAT (does not match D-01 regex) → Return None.
      Malformed ID — also triggers W004 (ERROR).

5. Cache invalidation: index.json event_sequence change clears the resolution cache.

Performance:
  - O(1) dictionary key lookup — no filesystem I/O, no directory walking, no scanning.
  - Cache hit rate is near-100% after first resolution (IDs are stable).
  - The resolved IndexEntry provides: entry.path (filesystem path), entry.type (artifact type),
    entry.status (current FSM state), entry.schema_owner (agent/projector/hybrid),
    entry.content_hash (SHA-256 hash, if present).
```

**Resolution examples:**

| Input ID (short) | Referrer Context | Hierarchical Key | Tier Section | Result |
|------------------|------------------|------------------|-------------|--------|
| `arc-45` | (root) | `arc-45` | `arcs` | IndexEntry or None |
| `stage-3` | Arc-1 | `arc-1/stage-3` | `stages` | IndexEntry or None |
| `slice-12` | Arc-1 / Stage-3 | `arc-1/stage-3/slice-12` | `slices` | IndexEntry or None |
| `step-5` | Arc-1 / Stage-3 / Slice-12 | `arc-1/stage-3/slice-12/step-5` | `steps` | IndexEntry or None |

**Note on short-form IDs and parent context:** The short form (`slice-12`) is unambiguous within the referrer's parent container due to D-10 same-parent-only constraint. The referrer's own `arc_id`/`stage_id`/`slice_id` frontmatter fields provide the parent context needed to construct the full hierarchical key. Cross-Arc references (e.g., Slice in Arc-1 referencing Slice in Arc-2) are never valid per REF-03 dependency policy, so the resolver does not need to search across multiple parent containers.

### Content-Hash Pinning

Content-hash pinning is the mechanism for detecting when a cross-referenced artifact has changed since the reference was created. It operates on the principle that mutable artifacts (DESIGN.md, RESEARCH.md) legitimately change, while immutable artifacts (CRIT.md after lock, stepNPLAN.md after lock) should not.

**Pinning at reference creation time:**

1. When artifact A creates a cross-reference to artifact B, A resolves B's ID via `resolve_id()` which returns B's IndexEntry.
2. If B's IndexEntry has a `content_hash` field present, A MAY record it in the depends_on entry:
   ```yaml
   depends_on:
     - {id: "slice-12", edge: "blocks", hash: "sha256:e3b0c44298fc1c14..."}
   ```
3. The `hash` field is optional — the reference creator can opt out of hash pinning. This is appropriate when:
   - The target does not support hash pinning (e.g., STATE.md projections, index.json entries — their content is derived, not authored).
   - The target is expected to change frequently and pinning would generate constant false-positive warnings.
   - The reference creator deems change detection unnecessary for this specific dependency.

**Hash mismatch detection (on consistency check):**

1. `validate_consistency()` resolves each `depends_on[{id}]` to its current IndexEntry.
2. If the depends_on entry has a `hash` field and the current IndexEntry has a `content_hash`, compare them.
3. If the hashes match → OK, no finding.
4. If the hashes differ:
   - **WARNING severity** if the target is in a **mutable state** (`planned`, `designing`, `in_progress`, `worktree_ready`). Rationale: mutable artifacts legitimately change — the reference was created against a snapshot that has since evolved. The warning is advisory for the planner to review whether the change affects the dependency.
   - **INFO severity** if the target is in an **immutable state** (`shipped`, `done`, `abandoned`, `completed`, `audited`). Rationale: immutable artifacts should not change — a hash mismatch on a shipped artifact is a strong signal of tampering, post-hoc editing, or corruption. However, since the artifact is in a terminal state and can no longer affect execution, the finding is informational rather than blocking.

**Hash computation:**

- The hash is SHA-256 of the **full file content** (not just the frontmatter). This ensures body prose changes are detected as well as structural changes.
- For markdown artifacts: hash the raw file bytes (UTF-8 encoded full file content).
- For JSON artifacts (STATE.md projections): hash pinning is not applicable — these artifacts should never have a `content_hash` in index.json. The `content_hash` field on IndexEntry is only populated for agent-authored artifacts.
- Hash format: `"sha256:{hex_digest}"` — 64-character lowercase hex string prefixed with `sha256:` for algorithm disambiguation. This format enables future migration to stronger hash algorithms (e.g., `sha512:`) without breaking the comparison logic.

---

## Section 3: Edge Type Semantics (REF-02)

The three edge types (`blocks`, `soft`, `data`) define the nature of a dependency relationship. Each edge type has distinct scheduler behavior, artifact behavior (whether artifacts are transferred), and broken behavior (how the system responds when the target is deleted, abandoned, or deferred).

**Canonical source:** `src/state_core/scheduler.py` line 15: `EdgeKind = Literal["blocks", "soft", "data"]`. This is an immutable literal — Phase 401 does NOT introduce new edge types, and ALL cross-reference edge values must match this literal exactly.

### Edge Type Specifications

| Edge | Prerequisite Type | Scheduler Behavior | Artifact Behavior | Broken Behavior |
|------|-------------------|-------------------|-------------------|-----------------|
| `blocks` | Hard prerequisite | Dependent cannot enter `in_progress` until target is `shipped` or `done`. Scheduler skips blocked dependents in frontier calculation. | N/A — no artifact transfer. Blocks edges only enforce ordering; they do not produce or consume artifacts. | Target deleted → dependent marked `BLOCKED` with `blocked_reason: "Dependency {target_id} unresolved"`. Target abandoned (D-13) → same, `blocked_reason: "Dependency {target_id} abandoned"`. Target deferred (D-14) → dependent unblocks with `deferred_dep: true` flag on the depends_on entry. |
| `soft` | Advisory ordering | Scheduler prioritizes target-before-dependent ordering but **may override** if resources are available or if the dependent is otherwise unblocked. Soft edges are hints, not gates. | N/A — no artifact transfer. Soft edges only express ordering preference; they do not impose constraints. | Target deleted or abandoned → soft edge is **silently dropped** from depends_on (removed during consistency check). Dependent proceeds normally. W004 warning emitted for audit trail. Target deferred → no effect (soft edges ignore deferral). |
| `data` | Hard prerequisite + artifact-producing | Same as `blocks` — hard prerequisite gating. Dependent cannot enter `in_progress` until target is `shipped` or `done`. | When target ships, the target's **output directory** is copied from the source worktree to the dependent's worktree artifact input path. This enables artifact-producing dependencies where one Slice's build output is consumed by a downstream Slice (e.g., a library Slice produces compiled artifacts consumed by an application Slice). | Target deleted or abandoned → dependent marked `BLOCKED` (artifacts will never arrive). Same semantics as blocks for gating, with the added loss of the artifact copy. Target deferred → dependent **unblocks** but the data edge is marked `deferred_data: true` (no actual artifacts are transferred). A warning is emitted. |

### Edge Validation Rules

- **Allowed values:** `blocks`, `soft`, `data` — exactly these three, case-sensitive, lowercase only.
- **No custom edge types:** The scheduler's EdgeKind literal is immutable. Any value outside `{blocks, soft, data}` is an invalid edge type.
- **W010 detection:** `validate_consistency()` detects any `depends_on[{edge}]` value not matching the EdgeKind literal. W010 (ERROR, blocks daemon startup) is emitted.
- **Empty depends_on array is valid:** An artifact with `depends_on: []` has no dependencies and is unblocked from the start (subject to parent tier gating).

### Scheduler EdgeKind Alignment

The three edge types in this specification **exactly match** `src/state_core/scheduler.py` line 15:

```python
EdgeKind = Literal["blocks", "soft", "data"]
```

No new edge types are introduced in Phase 401. The scheduler's EdgeKind is the **canonical source** — cross-reference edge validation defers to this literal. If the scheduler ever adds new edge types (e.g., `"trigger"` for explicit event-driven activation), the cross-reference system would extend to match at that time. Until then, `{blocks, soft, data}` is the complete set.

### Edge Semantics by Dependency Direction

The edge type determines **how** a dependency constrains execution, while the dependency direction (Section 4) determines **whether** a dependency is allowed at all. For allowed directions, edge semantics apply as described above. For forbidden directions, the dependency is rejected at schema validation time regardless of edge type.

---

## Section 4: Dependency Policy (REF-03)

The dependency policy defines which directions cross-references are allowed to point. It encodes the D-10 same-parent constraint, mode isolation (v11), and the scoping hierarchy. Dependencies that violate this policy are rejected at schema validation time or flagged by `validate_consistency()`.

### Allowed Dependency Directions

| Direction | Allowed? | Constraint | Validation |
|-----------|----------|------------|------------|
| **Same-tier sibling** (Arc→Arc, Stage→Stage, Slice→Slice) | **Yes** | Same-parent only (D-10): sibling must be within the same parent container. Slice→Slice deps only valid if both Slices share the same parent Stage. Stage→Stage deps only valid if both Stages share the same parent Arc. | Check that both referrer and target share the same `arc_id` (for Stage) or same `stage_id` (for Slice). |
| **Upward** (child→parent) | **Yes** | Implicit via aggregate ID hierarchy (`arc_id`, `stage_id`, `slice_id` frontmatter fields). Child always references its parent through its frontmatter, not through depends_on. | Parent ID must exist in index.json. Parent tier is implicit — a Stage references its Arc via `arc_id`, a Slice references its Stage via `stage_id`. |
| **Downward** (parent→child) | **No** | FORBIDDEN — violates the scoping hierarchy. A parent Arc should not `depends_on` a child Stage. A parent Stage should not `depends_on` a child Slice. The parent plans and scopes children; it does not depend on them. | Schema validation rejects any `depends_on` entry whose tier is lower (more specific) than the referrer's tier. Detection: if `depends_on[{id}]` tier is lower than referrer's tier (e.g., Arc referencing Slice) → reject. |
| **Cross-mode** (build↔teach) | **No** | FORBIDDEN — mode isolation (v11). Build-mode artifacts (`.state/build/` subtree) must only reference targets in `.state/build/`. Teach-mode artifacts (`.state/teach/` subtree) must only reference targets in `.state/teach/`. | W012 detects cross-subtree references at consistency check. Authoritative mode prefixes: `BUILD_ONLY_EVENT_PREFIXES` (`state.arc.`, `state.phase.`, `state.slice.`, `state.step.`) and `TEACH_ONLY_EVENT_PREFIXES` (`state.concept.`, `state.drill.`) from `src/state_core/schema.py` lines 42-48. |
| **Cross-arc** (Slice in Arc-1 depends on Slice in Arc-2) | **No** | D-10 same-parent constraint — cross-Arc dependencies are a deferred idea. Arcs are the coarsest scoping root; dependencies across Arc boundaries imply a coupling that should be expressed at the Arc level. | Schema validation rejects any `depends_on` entry whose target is in a different Arc than the referrer. Detection: resolve both referrer and target to their root Arc via hierarchical ID parsing; if Arc IDs differ → reject. |
| **Self-reference** (A depends on A) | **No** | FORBIDDEN — a meaningless cycle. An artifact cannot depend on itself. | W011 cycle detection catches self-references as trivial 1-node cycles. Schema validation also rejects any `depends_on[{id}]` that matches the referrer's own ID. |

### Downward Reference Detection

Downward references violate the scoping hierarchy. Detection logic:

- If the referrer is an **Arc** (tier 0) and `depends_on[{id}]` has tier prefix `stage-`, `slice-`, or `step-` → reject. Arc is the root scoping container; it plans Stages, it does not depend on them.
- If the referrer is a **Stage** (tier 1) and `depends_on[{id}]` has tier prefix `slice-` or `step-` → reject. Stage plans Slices; it does not depend on them.
- Arc→Arc dependencies (same-tier sibling) are allowed per the table above — Arcs can depend on sibling Arcs at the root tier (cross-Arc constraint does not apply at the Arc level, since D-10's "parent" for an Arc is the build root itself).

### Cross-Mode Detection (W012)

Cross-mode leakage violates the mode isolation defense-in-depth (v11). Detection logic:

- **Build-mode referrer:** File path starts with `.state/build/`. All `depends_on[{id}]` entries must resolve to targets whose paths start with `.state/build/`. If any target path starts with `.state/teach/` → W012 (ERROR, blocks daemon startup).
- **Teach-mode referrer:** File path starts with `.state/teach/`. All `depends_on[{id}]` entries must resolve to targets whose paths start with `.state/teach/`. If any target path starts with `.state/build/` → W012 (ERROR).

**Authoritative mode prefixes** (from `src/state_core/schema.py`):

```python
BUILD_SUBTREE: str = ".state/build"
TEACH_SUBTREE: str = ".state/teach"
BUILD_ONLY_EVENT_PREFIXES: frozenset[str] = frozenset(
    {"state.arc.", "state.phase.", "state.slice.", "state.step."}
)
TEACH_ONLY_EVENT_PREFIXES: frozenset[str] = frozenset(
    {"state.concept.", "state.drill."}
)
```

The subtree path check (`target.path` starts with `.state/build/` vs `.state/teach/`) is the primary detection mechanism. The event prefix check is a secondary validation for defense-in-depth — even if a path somehow spans both subtrees, the target's event prefix would reveal its true mode.

### Self-Reference Detection

Self-references are trivially detected: if `depends_on[{id}]` equals the referrer's own aggregate ID (in short form), reject. This is a special case of W011 cycle detection.

### Cross-Arc Detection

Cross-Arc dependencies are detected by resolving both the referrer and target to their root Arc:

1. Parse the referrer's hierarchical ID to extract the Arc component: `arc-{n}`.
2. For each `depends_on[{id}]`, resolve the target to its IndexEntry.
3. Parse the target's hierarchical key from index.json to extract its Arc component.
4. If the Arc components differ → reject (forbidden cross-Arc dependency).

**Arc-level exception:** Cross-Arc detection only applies below the Arc tier. An Arc artifact's `depends_on[{id: "arc-X"}]` is allowed — sibling Arcs can depend on each other. The D-10 same-parent constraint for Arc-level artifacts means "same build root" (which is always true — there is one build root per `.state/build/`).

---

## Section 5: Broken Reference Handling (REF-04)

Broken references occur when a dependency's target is deleted, abandoned, deferred, or never existed. The handling strategy follows D-401-15: **surface and block**, with explicit user resolution paths. No auto-cascade — the user retains full agency over dependency resolution.

### Target States → Referrer Behavior

The behavior of a referrer when its dependency target enters a non-normal state depends on the edge type. The table below covers all 12 scenarios: 4 target states × 3 edge types.

| Target State | blocks Edge | soft Edge | data Edge |
|-------------|------------|-----------|----------|
| **Target deleted** (missing from index.json — the aggregate ID has no entry in any tier section) | Referrer flagged **W004** (ERROR). If referrer is `in_progress` → BLOCKED with `blocked_reason: "Dependency {target_id} unresolved"`. If referrer is in a non-executing state (`planned`, `designing`) → W004 found but execution not yet affected. | Edge silently dropped from `depends_on` during consistency check (the depends_on entry for this target is removed). W004 warning emitted for audit trail. | Same as blocks: flagged **W004**. If referrer `in_progress` → BLOCKED. The data artifacts will never arrive; blocking is necessary to prevent execution with missing data. |
| **Target abandoned** (target exists in index.json with `status: abandoned`) | Referrer flagged **W005** (WARNING). If referrer is `in_progress` → BLOCKED with `blocked_reason: "Dependency {target_id} abandoned"`. Per D-13, abandonment cascades to blocked for dependents — never auto-abandon. | Edge silently dropped from `depends_on`. W005 info emitted. No blocking — soft edges are advisory and the target's abandonment releases the advisory constraint. | Same as blocks: flagged **W005**. If referrer `in_progress` → BLOCKED. Artifacts from the abandoned target will never arrive. |
| **Target deferred** (D-14 — target exists in index.json with `status: deferred` or has explicit deferment flag) | Referrer **unblocked**. The `depends_on` entry is updated to: `{id: "slice-X", edge: "blocks", deferred_dep: true}`. The referrer proceeds with the `deferred_dep` flag, which surfaces to the scheduler that one dependency was deferred. W005 warning emitted for audit trail. | **No effect** — soft edges are advisory. The deferral of a soft-edge dependency does not change anything. The edge remains in `depends_on` as-is. | Referrer **unblocked**, but the data edge is marked: `{id: "slice-X", edge: "data", deferred_data: true}`. The referrer proceeds without the actual data artifacts. A warning is emitted. The `deferred_data` flag signals to downstream consumers that the data dependency was never satisfied. |
| **Target descoped** (ID format appears valid but no aggregate was ever created — effectively a "phantom" reference) | Referrer flagged **W004** (ERROR — same as deleted). If referrer `in_progress` → BLOCKED with `blocked_reason: "Dependency {target_id} unresolved"`. This covers cases where a planner added a depends_on entry for an ID that was planned but never created. | Edge silently dropped from `depends_on`. W004 info emitted for audit trail. | Same as blocks: flagged **W004**. If referrer `in_progress` → BLOCKED. |

### Key Design Decisions

**Why blocked, not auto-abandoned?** Per D-13, the cascade always stops at `blocked` — never auto-abandons dependents. A single abandon action cannot silently destroy dependent work. Each blocked dependent is surfaced with a clear `blocked_reason`, giving the user visibility into why their work is stalled and agency over how to resolve it.

**Why is soft edge dropped on target deletion?** Soft edges express advisory ordering preferences. If the target no longer exists, there is nothing to order against. Dropping the edge silently is the correct behavior — the advisory constraint is naturally released. The W004 warning preserves the audit trail.

**Why does deferral unblock dependents?** D-14 deferment semantics treat a deferred Slice as "soft-done" — it is not abandoned, but it will not complete in the current planning horizon. Blocking dependents on an indefinitely deferred target would create a permanent deadlock. Unblocking with the `deferred_dep` flag gives the scheduler visibility into the incomplete dependency while allowing forward progress.

### W-Code Assignments for Broken References

| Code | Condition | Severity | Blocking Behavior |
|------|-----------|----------|-------------------|
| **W004** | Unresolved cross-reference — `depends_on[{id}]` not found in index.json (deleted, descoped, or never existed) | **ERROR** | Blocks daemon startup if the referrer is `in_progress`. If referrer is in a non-executing state, the finding is recorded but does not block daemon startup. |
| **W005** | Cross-referenced to descoped — target is `abandoned`, `deferred`, or otherwise intentionally removed from active work | **WARNING** | Does not block daemon startup. Advisory for planning — the user should review whether the dependency needs reassignment or removal. |

### Resolution Paths (User Actions)

Per D-401-15, the user has three resolution paths for broken references. All preserve user agency — the system surfaces the problem and offers options, but never resolves autonomously.

**1. Reassign target:** Edit the `depends_on[{id}]` to point to a different existing aggregate.

   Example: `{id: "slice-10", edge: "blocks"}` → `{id: "slice-14", edge: "blocks"}`

   Use when: A replacement Slice/Stage exists that provides the same or equivalent dependency.

**2. Defer dependency:** Mark the target as deferred (D-14). This unblocks the referrer with the `deferred_dep` flag.

   Use when: The dependency will not be satisfied in the current planning cycle but the referrer can proceed without it.

**3. Remove reference:** Delete the `depends_on` entry entirely. This removes the dependency edge.

   Use when: The dependency was never actually needed, or the referrer has been redesigned to not require it.

### Surface-to-Agent Protocol (D-401-15 / D-401-17)

When a broken reference is detected during `validate_consistency()` on daemon startup:

1. **Finding recorded:** Each broken reference is recorded as a `Finding` object with `code` (W004 or W005), `severity` (ERROR or WARNING), `artifact_id` (referrer's aggregate ID), `path` (referrer's filesystem path), and `message` (human-readable description including the missing target ID).

2. **ERROR gate (D-401-17):** If any ERROR-severity finding exists for an `in_progress` referrer, the daemon blocks startup (`daemon_startup_blocked: true` in the ConsistencyReport). The daemon does NOT bind its HTTP server.

3. **Resolution workflow launched:** The daemon auto-launches a resolution session (opencode subagent) with the full `ConsistencyReport.errors` list as context.

4. **Resolution session iterates findings:** For each ERROR finding, the resolution session surfaces the finding to the user with options:
   - "Artifact `{referrer_id}` depends on `{target_id}` which is {deleted/abandoned/descoped}."
   - Options: **[Reassign target]** (specify new target ID), **[Defer dependency]** (mark target as deferred), **[Remove reference]** (delete the depends_on entry).

5. **User resolves each finding:** The resolution session applies the user's chosen action for each finding.

6. **Resolution workflow restarts daemon:** After all ERROR findings are resolved, the resolution workflow restarts the daemon. The daemon re-runs `validate_consistency()` — if clean, it binds the HTTP server and starts normal operation.

**Non-deadlock path:** If the resolution session fails (e.g., the user is not available to resolve findings, or the event stream is corrupted), the daemon writes a crash report to `.state/build/crash/daemon-startup-failed-{timestamp}.json` and exits. The user can invoke `state build health --force` to start the daemon with ERRORS logged but not blocking — a manual override for when the user decides the consistency issues are acceptable.

---

## Section 6: Cross-References to Phase 400 and Phase 401 Specifications

This document depends on the following specifications. Each is referenced by document+section — Phase 400 and Phase 401 content is never reproduced here (per the anti-pattern avoidance pattern from PATTERNS.md).

### Phase 400 Specifications

| Phase 400 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| **FRONTMATTER-SCHEMAS.md** §Cross-Tier ID Encoding (lines 239–269) | Hierarchical aggregate ID format — slash-delimited keys for cross-reference resolution. Short form vs. hierarchical form conventions. Parent extraction algorithm used in downward-reference detection. |
| **FSM-TABLES.md** lines 163–166 | D-12 edge type definitions — the three edge types (`blocks`, `soft`, `data`) and their initial semantics. This document extends those semantics with broken-reference behavior and artifact-copy rules (for `data` edges). |
| **FSM-TABLES.md** full document | State transition tables — used to determine if a referrer is `in_progress` (blocking condition for W004/W005). Also used to determine if a target is in a mutable vs. immutable state (for hash mismatch severity). |
| **DESC-SEMANTICS.md** §Abandon Cascade (D-13), lines 1–55 | Abandon cascade rules — when a target is abandoned, its dependents are marked `blocked`, NOT auto-abandoned. This document's broken reference handling aligns with D-13 cascade semantics. |
| **DESC-SEMANTICS.md** §Deferment (D-14), lines 56–85 | Deferment rules — when a target is deferred, dependents are unblocked with `deferred_dep` flag. Deferred data edges are marked `deferred_data`. |
| **DESC-SEMANTICS.md** §Blocked State (D-15), lines 86–110 | Blocked state mechanics — indefinite pause, no timeout. Blocked Slices remain in STATE.md and DAG visualizations until the user resolves. |
| **DESC-SEMANTICS.md** §Decimal Insertion (D-16) | Decimal ID format (`slice-{n}.{d}`) — cross-references can target decimal-insertion IDs. The resolver handles decimal IDs the same as integer IDs (both resolve through the same index.json tier section). |
| **EVENT-TAXONOMY.md** | Event types for target state changes — the events that trigger re-evaluation of cross-reference validity (e.g., `state.slice.abandoned` triggers W005 for dependents). |

### Phase 401 Specifications

| Phase 401 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| **INDEX-SCHEMA.md** (Plan 02) §Section 4 | ID→Path resolution algorithm — the `resolve_id()` function described in this document is the same algorithm specified in INDEX-SCHEMA.md, adapted for cross-reference context (short-form IDs with parent context construction). |
| **INDEX-SCHEMA.md** §Section 4 — Content-Hash Pinning | Hash pinning integration — the `content_hash` field on IndexEntry is the source of truth for hash comparison. This document specifies the comparison severity rules (WARNING/INFO based on target mutability). |
| **INDEX-SCHEMA.md** §Section 1 — JSON Schema | IndexEntry structure — the `type`, `path`, `tier`, `status`, `schema_owner`, and `content_hash` fields are the data source for cross-reference resolution and validation. |
| **ARTIFACT-CATALOG.md** (Plan 01) §Section 1 | All 13 artifact types — used for cross-reference source/target identification. The `depends_on` field's presence and ownership per artifact type are documented in the catalog. |
| **SCHEMA-OWNERSHIP.md** (Plan 01) §Section 1 | Schema owner classifications — the `depends_on` field is agent-owned on ARC.md, STAGE.md, and SLICE.md. The projector reads but never modifies depends_on entries. |

### Consumer Attribution

CROSS-REFERENCES.md is consumed by these v41+ components at these lifecycle points:

| Consumer | When | What It Reads |
|----------|------|---------------|
| **v41+ daemon artifact loader** | Daemon startup | Reads the `depends_on` format specification to parse dependency entries. Uses `resolve_id()` algorithm for ID→path resolution when loading artifacts. |
| **v41+ scheduler** | DAG building; frontier calculation | Reads edge type semantics to enforce hard/soft/data constraints. Builds dependency DAG from `depends_on` edges. Skips blocked dependents in frontier calculation. |
| **v41+ projector** | Every state change event | Reads dependency policy to validate cross-references during index.json rebuild. Indexes cross-references in index.json for fast W004/W005 checks. |
| **v41+ validate_consistency()** | Daemon startup; post-state-change; on-demand | Reads broken reference handling rules to detect W004 (unresolved refs), W005 (descoped refs). Reads edge type semantics for W010 (invalid edge type) and dependency policy for W011 (cycles), W012 (cross-mode). |
| **v41+ CLI commands** | `/state-design`, `/state-run`, `/state-verify` | Reads the `depends_on` format to display dependency status. Uses `resolve_id()` to verify all declared dependencies exist before allowing execution. |
| **v42 quality pipeline verifier** | Pre-ship gate | Reads the full cross-reference validation ruleset to audit all depends_on entries across the artifact tree for consistency. |

---

## Section 7: Anti-Patterns

The following patterns are explicitly forbidden. They are listed here as a guardrail for implementers and extenders of this specification.

- **Do NOT use paths or slugs in cross-reference format.** Always use stable aggregate IDs. Paths change when files are renamed or reorganized; slugs are ambiguous and not guaranteed unique. Aggregate IDs are the single source of identity.
- **Do NOT introduce edge types beyond `blocks`, `soft`, `data`.** The scheduler's `EdgeKind = Literal["blocks", "soft", "data"]` is immutable. No custom edge types, no "convenience" aliases (e.g., `hard` as an alias for `blocks`). W010 detects any deviation.
- **Do NOT specify auto-cascade-abandon behavior.** D-401-15 requires surface + block, with user resolution. Auto-cascade-abandon would violate user agency and could silently destroy dependent work.
- **Do NOT define resolution paths that bypass the user.** All broken reference resolution must preserve user agency. Even the D-401-17 auto-resolution workflow presents each finding to the user for explicit resolution. The system never autonomously reassigns, defers, or removes dependencies.
- **Do NOT allow cross-Arc dependencies below the Arc tier.** D-10 same-parent-only is a hard constraint. A Slice in Arc-3 cannot depend on a Slice in Arc-7. This may be revisited in v42+ when cross-Arc dependency patterns are better understood, but for v41 it is a schema-level rejection.
- **Do NOT use the `hash` field for non-agent-authored artifacts.** Projector-rebuilt artifacts (index.json, STATE.md projections) should never have a `content_hash` in index.json and should never be referenced with a `hash` in depends_on. Their content is derived, not authored — hash pinning is meaningless.
- **Do NOT specify implementation details in cross-reference entries.** The `depends_on` format uses declarative fields (`id`, `edge`, `hash`). Do not add implementation-specific fields like `resolved_at`, `resolution_attempts`, or `scheduler_queue_position`. Those belong in the daemon's runtime state, not in the artifact frontmatter.

---

## Requirement Cross-Reference

| Requirement | Section(s) | Description |
|-------------|-----------|-------------|
| **REF-01** | Section 2 | Cross-reference format: `depends_on` YAML structure with `id` (required), `edge` (required), `hash` (optional) fields. ID resolution algorithm with O(1) index.json dictionary lookup. Content-hash pinning with SHA-256 of full file content and severity-calibrated mismatch handling. |
| **REF-02** | Section 3 | Edge type semantics: comprehensive table covering all 3 edge types (`blocks`, `soft`, `data`) with 5 columns (Prerequisite Type, Scheduler Behavior, Artifact Behavior, Broken Behavior). Edge validation confirming match with scheduler EdgeKind literal. |
| **REF-03** | Section 4 | Dependency policy: table covering all 6 direction types (same-tier sibling, upward, downward, cross-mode, cross-arc, self-reference) with allowed/forbidden + constraint + validation. Detection logic for downward references, cross-mode leakage (W012), self-references, and cross-Arc dependencies. |
| **REF-04** | Section 5 | Broken reference handling: 12-scenario matrix (4 target states × 3 edge types) covering deleted, abandoned, deferred, and descoped targets. Resolution paths per D-401-15 (reassign, defer, remove). Surface-to-agent protocol per D-401-17. W-code assignments (W004 ERROR, W005 WARNING). |

---

*Design contract for v41+ cross-reference resolution, dependency validation, and broken reference handling. Complete specification covering REF-01 (cross-reference format with ID resolution algorithm and hash pinning), REF-02 (edge type semantics with 5-column table and EdgeKind alignment), REF-03 (dependency policy with 6 direction types and detection logic), and REF-04 (broken reference handling with 12-scenario matrix and 3-path user resolution protocol). Consumed by daemon artifact loader, scheduler, projector, validate_consistency(), CLI commands, and quality pipeline verifier.*
