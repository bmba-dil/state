# Index Schema: `index.json` JSON Schema & Projector Rebuild Rules

> **Design contract for v41+ projector index.json rebuild and artifact registry.**
> Consumed by: v41+ daemon (startup index load), v41+ projector (incremental rebuild on every `state.*` event), v41+ `validate_consistency()` (W002/W003 checks), CLI commands (ID→path resolution).

## Design Conventions

This document specifies the complete JSON Schema for `index.json` — the projector-rebuilt artifact registry that maps every aggregate ID to its filesystem path, type, tier, status, schema owner, and last-updated timestamp. The schema implements D-401-14 (tier-separated structure), enabling O(1) ID→path resolution without filesystem traversal.

**Tier-separated structure (D-401-14):** Four top-level objects — `arcs`, `stages`, `slices`, `steps` — each keyed by aggregate ID in hierarchical format. This structure groups artifacts by their owning tier, making tier-specific queries fast and avoiding key collisions between tiers.

**Projector ownership:** `index.json` is exclusively owned by the projector (per SCHEMA-OWNERSHIP.md §Section 1: Projector-rebuilt classification). The agent NEVER writes to this file — any agent modifications would be overwritten on the next projector rebuild. The projector performs full rebuild on daemon startup and incremental rebuild on every `state.*` event.

**Content-hash pinning:** The optional `content_hash` field stores a SHA-256 hash of the artifact's file content, enabling cross-reference hash pinning (REF-01). When artifact A creates a cross-reference to artifact B, A pins B's hash from `index.json` at creation time. On consistency checks (Plan 401-03), hash comparison detects drift.

**Schema versioning:** The `version` field enables forward compatibility. The v41+ daemon checks this field against its expected schema version on startup — mismatch triggers a migration or rejection. This prevents silent schema drift as the engine evolves.

---

## Section 1: JSON Schema Specification (DSK-05)

The complete JSON Schema for `index.json` uses JSON Schema Draft 2020-12. All enum values are verified against ARTIFACT-CATALOG.md (artifact type names), Phase 400 tier definitions (tier names), and SCHEMA-OWNERSHIP.md (schema_owner classifications).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Artifact Index",
  "description": "Projector-rebuilt registry mapping every artifact ID to its path, type, tier, status, schema owner, and last-updated timestamp. Tier-separated per D-401-14. Rebuilt on daemon startup (full) and every state.* event (incremental).",
  "type": "object",
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0",
      "description": "Schema version for forward compatibility. v41+ daemon checks this field on startup to ensure index.json schema matches expected version — rejects on mismatch to prevent silent schema drift."
    },
    "last_rebuilt": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of last projector rebuild (full or incremental). Updated on every write."
    },
    "event_sequence": {
      "type": "integer",
      "minimum": 0,
      "description": "Sequence number of last processed event from the event store. Enables incremental rebuild — projector skips events with sequence ≤ this value. Resets to 0 on full rebuild."
    },
    "arcs": {
      "type": "object",
      "description": "All Arc-level artifacts, keyed by aggregate ID (arc-{n}). Each value is an IndexEntry describing the artifact's current state.",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    },
    "stages": {
      "type": "object",
      "description": "All Stage-level artifacts, keyed by hierarchical aggregate ID (arc-{n}/stage-{n}). Decimal IDs (stage-{n}.{d}) are valid per D-16.",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    },
    "slices": {
      "type": "object",
      "description": "All Slice-level artifacts, keyed by hierarchical aggregate ID (arc-{n}/stage-{n}/slice-{n}). Decimal IDs (slice-{n}.{d}) are valid per D-16.",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    },
    "steps": {
      "type": "object",
      "description": "All Step-level artifacts, keyed by hierarchical aggregate ID (arc-{n}/stage-{n}/slice-{n}/step-{n}). Steps are flat files in Slice directories per D-04.",
      "additionalProperties": {
        "$ref": "#/$defs/IndexEntry"
      }
    }
  },
  "required": ["version", "last_rebuilt", "event_sequence", "arcs", "stages", "slices", "steps"],
  "additionalProperties": false,
  "$defs": {
    "IndexEntry": {
      "type": "object",
      "description": "A single artifact entry in the index. Maps one aggregate ID to its filesystem path, type, tier, status, schema owner, and optional content hash.",
      "properties": {
        "type": {
          "type": "string",
          "description": "Artifact file type — the filename as it appears on disk. Values must match ARTIFACT-CATALOG.md artifact type names exactly.",
          "enum": [
            "ARC.md",
            "STAGE.md",
            "SLICE.md",
            "stepNPLAN.md",
            "CRIT.md",
            "MAP.md",
            "DESIGN.md",
            "RESEARCH.md",
            "VERIFICATION.md",
            "SUMMARY.md",
            "DECISIONS.md",
            "STATE.md"
          ]
        },
        "path": {
          "type": "string",
          "description": "Relative path from .state/build/ root to the artifact file. Must match the path in DIRECTORY-TREE.md and ARTIFACT-CATALOG.md."
        },
        "tier": {
          "type": "string",
          "description": "Owning tier of the artifact. Must match Phase 400 tier definitions exactly.",
          "enum": ["arc", "stage", "slice", "step"]
        },
        "status": {
          "type": "string",
          "description": "Current FSM state of the owning aggregate. Must be a valid Literal status value for this tier as defined in Phase 400 FSM-TABLES.md. Examples: planned, in_progress, shipped, abandoned."
        },
        "schema_owner": {
          "type": "string",
          "description": "Who owns the schema for this artifact. Must match SCHEMA-OWNERSHIP.md classification: agent (agent-authored, projector updates only owned fields), projector (fully rebuilt from event stream), hybrid (MAP.md — agent writes structure, projector updates checkboxes).",
          "enum": ["agent", "projector", "hybrid"]
        },
        "last_updated": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 timestamp of the last modification to this artifact's IndexEntry. Updated by projector on every state change affecting this artifact."
        },
        "content_hash": {
          "type": "string",
          "description": "SHA-256 hash of the artifact file's current content (hex-encoded). Optional — only present for artifacts that support hash pinning (REF-01). Absent for projector-rebuilt artifacts (index.json, STATE.md projections) since their content is derived, not authored."
        }
      },
      "required": ["type", "path", "tier", "status", "schema_owner", "last_updated"],
      "additionalProperties": false
    }
  }
}
```

### Schema Property Reference

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `version` | `string` (const: `"1.0"`) | Yes | Schema version for forward compatibility. Daemon rejects mismatched versions. |
| `last_rebuilt` | `string` (date-time) | Yes | ISO 8601 timestamp of most recent projector rebuild. Source of truth for index freshness. |
| `event_sequence` | `integer` (≥ 0) | Yes | Sequence number of last processed event from event store. Enables incremental rebuild skip. |
| `arcs` | `object` (IndexEntry values) | Yes | All Arc-level artifacts keyed by `arc-{n}` aggregate ID |
| `stages` | `object` (IndexEntry values) | Yes | All Stage-level artifacts keyed by `arc-{n}/stage-{n}` hierarchical ID |
| `slices` | `object` (IndexEntry values) | Yes | All Slice-level artifacts keyed by `arc-{n}/stage-{n}/slice-{n}` hierarchical ID |
| `steps` | `object` (IndexEntry values) | Yes | All Step-level artifacts keyed by `arc-{n}/stage-{n}/slice-{n}/step-{n}` hierarchical ID |

### IndexEntry Property Reference

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | `string` (enum: 12 values) | Yes | Artifact file type — must match ARTIFACT-CATALOG.md exactly |
| `path` | `string` | Yes | Relative path from `.state/build/` root |
| `tier` | `string` (enum: `arc`, `stage`, `slice`, `step`) | Yes | Owning tier per Phase 400 tier definitions |
| `status` | `string` | Yes | Current FSM state per Phase 400 FSM-TABLES.md |
| `schema_owner` | `string` (enum: `agent`, `projector`, `hybrid`) | Yes | Schema ownership per SCHEMA-OWNERSHIP.md |
| `last_updated` | `string` (date-time) | Yes | ISO 8601 timestamp of last update |
| `content_hash` | `string` | No | SHA-256 hash of file content for cross-ref pinning (REF-01) |

### Enum Value Verification

**IndexEntry.type enum — verified against ARTIFACT-CATALOG.md artifact type names:**

| Enum Value | Catalog Entry | Match? |
|-----------|---------------|--------|
| `ARC.md` | ARTIFACT-CATALOG.md §ARC.md | ✓ |
| `STAGE.md` | ARTIFACT-CATALOG.md §STAGE.md | ✓ |
| `SLICE.md` | ARTIFACT-CATALOG.md §SLICE.md | ✓ |
| `stepNPLAN.md` | ARTIFACT-CATALOG.md §stepNPLAN.md | ✓ |
| `CRIT.md` | ARTIFACT-CATALOG.md §CRIT.md | ✓ |
| `MAP.md` | ARTIFACT-CATALOG.md §MAP.md | ✓ |
| `DESIGN.md` | ARTIFACT-CATALOG.md §DESIGN.md | ✓ |
| `RESEARCH.md` | ARTIFACT-CATALOG.md §RESEARCH.md | ✓ |
| `VERIFICATION.md` | ARTIFACT-CATALOG.md §VERIFICATION.md | ✓ |
| `SUMMARY.md` | ARTIFACT-CATALOG.md §SUMMARY.md | ✓ |
| `DECISIONS.md` | ARTIFACT-CATALOG.md §DECISIONS.md | ✓ |
| `STATE.md` | ARTIFACT-CATALOG.md §STATE.md | ✓ |

**IndexEntry.tier enum — verified against Phase 400 tier definitions:** `["arc", "stage", "slice", "step"]` matches TIER-ARC.md, TIER-STAGE.md, TIER-SLICE.md, TIER-STEP.md exactly. No extra tier names, no missing tiers.

**IndexEntry.schema_owner enum — verified against SCHEMA-OWNERSHIP.md §Section 1:** `["agent", "projector", "hybrid"]` matches the three classifications in the Classification Table. 10 artifacts classified as agent, 2 as projector, 1 as hybrid (MAP.md).

---

## Section 2: Example index.json

A complete example demonstrating one entry per tier with hierarchical aggregate ID keys.

```json
{
  "version": "1.0",
  "last_rebuilt": "2026-05-07T12:00:00Z",
  "event_sequence": 1042,
  "arcs": {
    "arc-1": {
      "type": "ARC.md",
      "path": "arcs/arc-1/ARC.md",
      "tier": "arc",
      "status": "in_progress",
      "schema_owner": "agent",
      "last_updated": "2026-05-07T11:30:00Z",
      "content_hash": "sha256:a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
    }
  },
  "stages": {
    "arc-1/stage-1": {
      "type": "STAGE.md",
      "path": "arcs/arc-1/stages/stage-1/STAGE.md",
      "tier": "stage",
      "status": "in_progress",
      "schema_owner": "agent",
      "last_updated": "2026-05-07T11:45:00Z"
    }
  },
  "slices": {
    "arc-1/stage-1/slice-1": {
      "type": "SLICE.md",
      "path": "arcs/arc-1/stages/stage-1/slices/slice-1/SLICE.md",
      "tier": "slice",
      "status": "in_progress",
      "schema_owner": "agent",
      "last_updated": "2026-05-07T12:00:00Z"
    }
  },
  "steps": {
    "arc-1/stage-1/slice-1/step-1": {
      "type": "stepNPLAN.md",
      "path": "arcs/arc-1/stages/stage-1/slices/slice-1/step1PLAN.md",
      "tier": "step",
      "status": "running",
      "schema_owner": "agent",
      "last_updated": "2026-05-07T12:05:00Z"
    }
  }
}
```

**Example notes:**
- The `arcs` entry uses the short aggregate key `arc-1` (no parent prefix needed since it's the root tier)
- The `stages` entry uses the hierarchical key `arc-1/stage-1` (includes parent Arc context per FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding)
- The `slices` entry uses `arc-1/stage-1/slice-1` (full lineage for disambiguation)
- The `steps` entry uses `arc-1/stage-1/slice-1/step-1` (complete hierarchical path)
- `content_hash` is present on the Arc entry (agent-authored, hash-pinnable) but absent on others (not all artifacts require hash pinning)

---

## Section 3: Projector Rebuild Rules

The projector is the exclusive owner of `index.json`. It rebuilds the index on two triggers: daemon startup (full rebuild from event store) and every `state.*` event (incremental rebuild for affected entries).

### Full Rebuild (Daemon Startup)

Triggered on daemon startup to ensure the index is consistent with the event store. This is the authoritative rebuild — it reconciles the entire filesystem with the complete event history.

**Steps:**
1. Projector truncates the in-memory index representation
2. Projector walks the `.state/build/arcs/` directory tree, discovering all artifact files
3. For each artifact file found:
   a. Reads the file's frontmatter (for markdown artifacts) or file metadata (for non-frontmatter artifacts)
   b. Extracts: aggregate ID, type, tier, status, schema owner, last_updated
   c. Optionally computes `content_hash` (SHA-256 of file content) if the artifact supports hash pinning
   d. Creates an IndexEntry and inserts it into the appropriate tier section keyed by hierarchical aggregate ID
4. Projector reconciles with the event stream:
   a. Reads all events from `.state/events.sqlite` in sequence order
   b. For each event, updates the corresponding IndexEntry (or creates it if not found during directory walk)
   c. Removes any IndexEntry whose aggregate ID has no corresponding event in the stream (orphan cleanup)
5. Projector sets `version` to `"1.0"`, `last_rebuilt` to current UTC timestamp, `event_sequence` to the sequence number of the last processed event
6. Projector writes `index.json` atomically: write to `index.json.tmp`, then `os.rename(index.json.tmp, index.json)`

**Guarantees:**
- Complete consistency: every entry in the index corresponds to an event in the event store
- Orphan cleanup: entries without backing events are removed (not left as stale)
- Atomic write: readers never see a partially-written index
- Event stream is authoritative: filesystem state is reconciled against events, not the other way around

### Incremental Rebuild (Per state.* Event)

Triggered on every `state.*` event to keep the index current without a full filesystem walk.

**Steps:**
1. Projector receives a `state.*` event from the event bus (SSE or internal dispatch)
2. Projector extracts `aggregate_id` and event type from the event payload
3. Projector determines which IndexEntry(s) are affected by this event:
   a. The aggregate whose state changed (direct update)
   b. Any parent aggregates whose child counts need recomputation (cascade update — e.g., Slice `shipped` updates parent Stage's `shipped_slice_count`)
4. For each affected entry:
   a. Reads the artifact file from disk to get current frontmatter
   b. Updates the IndexEntry with current `type`, `path`, `tier`, `status`, `schema_owner`, `last_updated`
   c. Optionally recomputes `content_hash` if the artifact supports hash pinning and has changed
5. Projector increments `event_sequence` to match the event's sequence number
6. Projector updates `last_rebuilt` to current UTC timestamp
7. Projector writes `index.json` atomically (same atomic rename pattern as full rebuild)

**Incremental skip optimization:**
- Before processing any event, the projector checks if `event.sequence ≤ index.event_sequence`
- If yes: skip this event (already reflected in the index)
- If no: process the event (it arrived while the projector was down or is new)
- This makes daemon restart fast — only events that arrived during downtime are processed

### Trigger Events → Index Updates

| Event Pattern | Index Update | Cascade |
|---------------|-------------|---------|
| `state.arc.created` | Insert new `arcs[arc-{n}]` entry | None (Arc has no parent) |
| `state.arc.started` | Update `arcs[arc-{n}].status` to `in_progress` | None |
| `state.arc.stages_shipped` | Update `arcs[arc-{n}].shipped_stage_count` | None |
| `state.arc.shipped` | Update `arcs[arc-{n}].status` to `shipped`, set `completed_at` | None |
| `state.arc.abandoned` | Update `arcs[arc-{n}].status` to `abandoned` | Cascade: update all descendant entries' parent-linked computed fields |
| `state.stage.created` | Insert new `stages[arc-{n}/stage-{n}]` entry | Cascade: update parent Arc's `stage_count` |
| `state.stage.started` | Update `stages[arc-{n}/stage-{n}].status` to `in_progress` | None |
| `state.stage.slices_shipped` | Update `stages[arc-{n}/stage-{n}].shipped_slice_count` | Cascade: update parent Arc's `shipped_stage_count` |
| `state.stage.audited` | Update `stages[arc-{n}/stage-{n}].status` to `audited` | None |
| `state.stage.completed` | Update `stages[arc-{n}/stage-{n}].status` to `completed` | None |
| `state.stage.abandoned` | Update `stages[arc-{n}/stage-{n}].status` to `abandoned` | Cascade: remove from parent Arc's active counts |
| `state.slice.created` | Insert new `slices[arc-{n}/stage-{n}/slice-{n}]` entry | Cascade: update parent Stage's `slice_count` |
| `state.slice.worktree_ready` | Update `slices[...].status` to `worktree_ready`, set `worktree_dir`, `worktree_branch` | None |
| `state.slice.started` | Update `slices[...].status` to `in_progress` | None |
| `state.slice.shipped` | Update `slices[...].status` to `shipped`, set `completed_at` | Cascade: update parent Stage's `shipped_slice_count` |
| `state.slice.abandoned` | Update `slices[...].status` to `abandoned` | Cascade: remove from parent Stage's active counts |
| `state.step.created` | Insert new `steps[arc-{n}/stage-{n}/slice-{n}/step-{n}]` entry | Cascade: update parent Slice's `step_count` |
| `state.step.designed` | Update `steps[...].status` to `designed` | None |
| `state.step.planned` | Update `steps[...].status` to `planned` | None |
| `state.step.ran` | Update `steps[...].status` to `ran` | None |
| `state.step.verify_passed` | Update `steps[...].status` to `verify_passed` | Cascade: update parent Slice's `completed_step_count` |
| `state.step.abandoned` | Update `steps[...].status` to `abandoned` | Cascade: remove from parent Slice's active counts |

---

## Section 4: ID→Path Resolution Algorithm

The `index.json` structure enables O(1) ID→path resolution via dictionary lookup — no filesystem traversal required. This is the core lookup algorithm used by the daemon artifact loader, CLI commands, and cross-reference resolver.

### Algorithm

```
Algorithm: resolve_id(id: str) -> Optional[IndexEntry]

1. Parse the aggregate ID to extract the tier prefix:
   - "arc-"   → Tier: arc   → Look in index.arcs
   - "stage-" → Tier: stage → Look in index.stages
   - "slice-" → Tier: slice → Look in index.slices
   - "step-"  → Tier: step  → Look in index.steps

2. Look up the full hierarchical ID in the appropriate tier section:
   - Arc:     index.arcs["arc-{n}"]
   - Stage:   index.stages["arc-{n}/stage-{n}"]
   - Slice:   index.slices["arc-{n}/stage-{n}/slice-{n}"]
   - Step:    index.steps["arc-{n}/stage-{n}/slice-{n}/step-{n}"]

3. Resolution outcomes:
   a. FOUND → Return the IndexEntry (entry.path gives filesystem path)
      Cache the result for subsequent lookups (hot path optimization)
   b. NOT FOUND but valid format → Return None (unresolved — triggers W004 in Plan 401-03)
   c. INVALID FORMAT → Return None (malformed ID — triggers W004)

4. Resolution is O(1) via dictionary key lookup — no filesystem I/O, no walking, no scanning.

5. The resolved IndexEntry provides:
   - entry.path: filesystem path for file I/O operations
   - entry.type: artifact type for consumer routing
   - entry.status: current FSM state for status checks
   - entry.schema_owner: whether agent or projector owns the schema
   - entry.content_hash: SHA-256 hash for cross-ref pinning (if present)
```

### Resolution Examples

| Input ID | Tier Section | Key | Result |
|----------|-------------|-----|--------|
| `arc-45` | `arcs` | `arc-45` | `IndexEntry(type="ARC.md", path="arcs/arc-45/ARC.md", ...)` |
| `arc-1/stage-3` | `stages` | `arc-1/stage-3` | `IndexEntry(type="STAGE.md", path="arcs/arc-1/stages/stage-3/STAGE.md", ...)` |
| `arc-1/stage-3/slice-12` | `slices` | `arc-1/stage-3/slice-12` | `IndexEntry(type="SLICE.md", path="arcs/arc-1/stages/stage-3/slices/slice-12/SLICE.md", ...)` |
| `arc-1/stage-3/slice-12/step-5` | `steps` | `arc-1/stage-3/slice-12/step-5` | `IndexEntry(type="stepNPLAN.md", path="arcs/arc-1/stages/stage-3/slices/slice-12/step5PLAN.md", ...)` |
| `arc-99` (does not exist) | `arcs` | `arc-99` | `None` (unresolved) |
| `invalid-id` (bad format) | — | — | `None` (malformed) |

### Content-Hash Pinning Integration (REF-01)

When artifact A creates a cross-reference to artifact B (e.g., SLICE.md has `depends_on: [{id: "slice-12", edge: "blocks"}]`), the reference creation flow:

1. A resolves B's ID via `resolve_id("slice-12")` — returns B's IndexEntry
2. If B's IndexEntry has a `content_hash`, A pins it in the reference:
   ```json
   { "id": "slice-12", "edge": "blocks", "pinned_hash": "sha256:abc123..." }
   ```
3. On consistency check (Plan 401-03 `validate_consistency()`):
   a. Resolve `slice-12` to its current IndexEntry
   b. Compare `current_entry.content_hash` vs `pinned_hash` from the reference
   c. If match → OK
   d. If mismatch → WARNING if B is mutable (DESIGN.md, RESEARCH.md — expected to change), INFO if B is immutable (CRIT.md after lock, stepNPLAN.md after lock — unexpected change)

This enables drift detection without blocking — mutable artifacts can change (with a warning), immutable artifacts changing is a strong signal of tampering or corruption.

---

## Section 5: Cross-References to Phase 400 and Plan 401-01

This document depends on the following specifications. Each is referenced by document+section — Phase 400 and Plan 401-01 content is never reproduced.

### Phase 400 Specifications

| Phase 400 Spec | What This Document Uses From It |
|----------------|--------------------------------|
| FRONTMATTER-SCHEMAS.md §Cross-Tier ID Encoding (lines 239–269) | Hierarchical aggregate ID format — slash-delimited keys for index sections (`arc-{n}/stage-{n}/slice-{n}/step-{n}`). Short form vs hierarchical form conventions. |
| FRONTMATTER-SCHEMAS.md §Field Ownership Rules (TIER-07) | Agent vs Projector field classification — drives IndexEntry `schema_owner` values |
| FSM-TABLES.md | Status values per tier — IndexEntry `status` field must contain valid Literal members for that tier's state machine |
| TIER-ARC.md | Arc tier definition — `arc` in IndexEntry `tier` enum |
| TIER-STAGE.md | Stage tier definition — `stage` in IndexEntry `tier` enum |
| TIER-SLICE.md | Slice tier definition — `slice` in IndexEntry `tier` enum |
| TIER-STEP.md | Step tier definition — `step` in IndexEntry `tier` enum |
| DESC-SEMANTICS.md §D-16 | Decimal insertion — `stage-{n}.{d}` and `slice-{n}.{d}` keys in index are valid |
| EVENT-TAXONOMY.md | Event type names — used in Trigger Events → Index Updates table |

### Plan 401-01 Specifications

| Plan 401-01 Spec | What This Document Uses From It |
|------------------|--------------------------------|
| ARTIFACT-CATALOG.md §Section 1 | All 12 artifact type names — verified against IndexEntry `type` enum. Each catalog entry's file format, schema owner, and status values inform IndexEntry properties. |
| ARTIFACT-CATALOG.md §Section 1 — index.json entry | index.json purpose, schema owner (Projector), update triggers — this schema implements the catalog specification |
| SCHEMA-OWNERSHIP.md §Section 1 — Classification Table | Schema owner classifications — verified against IndexEntry `schema_owner` enum. 10 agent, 2 projector, 1 hybrid. |

### Plan 401-02 Internal Cross-References

| This Document's Section | Consumed By |
|-------------------------|-------------|
| Section 1 (JSON Schema) | v41+ projector — implements schema validation on write; v41+ daemon — validates on startup |
| Section 3 (Rebuild Rules) | v41+ projector — implements full + incremental rebuild logic |
| Section 4 (Resolution Algorithm) | v41+ daemon artifact loader, CLI commands, cross-reference resolver — all use O(1) ID→path lookup |
| Section 4 (Hash Pinning) | Plan 401-03 `validate_consistency()` — W012 hash mismatch detection |

### Consumer Attribution

`index.json` is consumed by these v41+ components at these lifecycle points:

| Consumer | When | What It Reads |
|----------|------|---------------|
| Daemon artifact loader | Daemon startup | Loads full index into memory; caches for O(1) ID→path resolution throughout daemon lifetime |
| Projector | Every `state.*` event | Reads index for incremental update; writes index atomically after update |
| `validate_consistency()` | Daemon startup + on-demand | Walks all entries to detect orphans (W002), stale entries (W003), hash mismatches (W012) |
| CLI `/state-design` | Slice design phase | Resolves `depends_on` IDs to verify targets exist and check status before allowing design to proceed |
| CLI `/state-run` | Slice execution phase | Resolves parent Slice ID to find worktree directory; reads Step file paths |
| TUI extensions (v17) | Session lifecycle | Reads index for artifact browser directory navigation; tier-filtered queries |
| Cross-reference resolver | Any ID→path lookup | O(1) dictionary access — used by all consumers that need to convert an aggregate ID to a filesystem path |

### Anti-Patterns (Enforced)

- **Do NOT change `type` enum values from ARTIFACT-CATALOG.md definitions:** The 12 values in the enum are the canonical artifact type names. Adding, removing, or renaming a value breaks the ID→type mapping used by artifact loaders and CLI commands.
- **Do NOT use a flat key structure:** D-401-14 requires tier-separated top-level objects (`arcs`, `stages`, `slices`, `steps`). A flat structure loses tier grouping and risks key collisions between tiers.
- **Do NOT specify implementation details:** This document describes the schema contract and rebuild rules in structural terms — not Python dict update code, async I/O patterns, or database queries. The v41+ developer decides HOW to implement these contracts.
- **Do NOT add `content_hash` to projector-rebuilt artifacts:** `index.json` and `state/*.json` entries should never have `content_hash` — their content is derived, not authored. Hash pinning is meaningful only for agent-authored artifacts.
- **Do NOT require `content_hash` on all entries:** The field is optional. Some artifacts (DESIGN.md, RESEARCH.md) change frequently and hash pinning would generate constant warnings. Hash pinning is opt-in per artifact type.

---

## Requirement Cross-Reference

| Requirement | Section(s) | Description |
|-------------|-----------|-------------|
| DSK-05 | Sections 1–4 | index.json JSON Schema (JSON Schema 2020-12), projector rebuild rules (full + incremental), O(1) ID→path resolution algorithm, content-hash pinning integration |

---

*Design contract for v41+ projector index.json rebuild and artifact registry. Complete JSON Schema (Draft 2020-12) with 7 IndexEntry properties, 12 artifact type enum values verified against ARTIFACT-CATALOG.md, tier and schema_owner enums verified against Phase 400 and SCHEMA-OWNERSHIP.md. Projector rebuild rules for full (daemon startup) and incremental (per event) rebuilds with atomic write pattern. O(1) ID→path resolution algorithm with hash-pinning integration. Consumed by daemon, projector, validate_consistency(), CLI commands, and TUI extensions.*
