# Graph Report - state  (2026-04-23)

## Corpus Check
- 39 files · ~10,920 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 377 nodes · 4965 edges · 31 communities detected
- Extraction: 9% EXTRACTED · 91% INFERRED · 0% AMBIGUOUS · INFERRED: 4525 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]

## God Nodes (most connected - your core abstractions)
1. `EventEnvelope` - 116 edges
2. `TestStepDataModels` - 81 edges
3. `TestEventEnvelope` - 79 edges
4. `TestBuildEvent` - 79 edges
5. `ArcCreatedData` - 78 edges
6. `TestModeDecisionAuthDataModels` - 77 edges
7. `TestDiscriminatedUnions` - 77 edges
8. `TestEdgeCases` - 77 edges
9. `TestConceptDataModels` - 76 edges
10. `TestPhaseDataModels` - 75 edges

## Surprising Connections (you probably didn't know these)
- `TestEventEnvelope` --uses--> `ArcCreatedData`  [INFERRED]
  tests/test_schema.py → src/state_core/schema.py
- `TestEventEnvelope` --uses--> `ArcCreatedEvent`  [INFERRED]
  tests/test_schema.py → src/state_core/schema.py
- `TestEventEnvelope` --uses--> `ArcRetiredData`  [INFERRED]
  tests/test_schema.py → src/state_core/schema.py
- `TestEventEnvelope` --uses--> `ArcRetiredEvent`  [INFERRED]
  tests/test_schema.py → src/state_core/schema.py
- `TestEventEnvelope` --uses--> `ArcUpdatedData`  [INFERRED]
  tests/test_schema.py → src/state_core/schema.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (60): get_connection(), get_db_path(), Async SQLite connection factory with WAL mode, synchronous=NORMAL, path resoluti, Resolve the database file path.      Priority:     1. STATE_DB_PATH environment, Open a connection to the event store with WAL + synchronous=NORMAL.      Ensures, Return the resolved database path without opening a connection., _resolve_db_path(), applied_migrations() (+52 more)

### Community 1 - "Community 1"
Cohesion: 0.51
Nodes (62): ArcRetiredEvent, ArcUpdatedEvent, AuthRefreshedEvent, AuthRotatedData, AuthRotatedEvent, ConceptDrilledEvent, ConceptIntroducedEvent, ConceptMasteredEvent (+54 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (11): ArcCreatedData, ArcCreatedEvent, build_event(), Construct a typed event with auto-generated ULID and timestamp.      Args:, StepVerifyPassedData, _build_event(), make_envelope_kwargs(), test_event_construction() (+3 more)

### Community 3 - "Community 3"
Cohesion: 0.51
Nodes (39): BaseModel, ConceptDrilledData, ConceptIntroducedData, ConceptObservedData, ConceptReviewedData, DecisionAskedData, DecisionMadeData, ModeActivatedData (+31 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (14): AuthMethod, Credential, AuthMethod protocol + Credential container., EventStore, Event store: SQLite writer + SyncEvent mirror for dual-write architecture., Protocol for writing and reading domain events., Concrete EventStore backed by events.sqlite via database.py., Append an event row and return its id.          NOTE: This is a stub for Phase 0 (+6 more)

### Community 5 - "Community 5"
Cohesion: 0.19
Nodes (4): EventEnvelope, Generic event envelope -- used for serialization and generic reads.      All fie, TestEdgeCases, TestEventEnvelope

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (1): Worker package — per-session process for state.

### Community 7 - "Community 7"
Cohesion: 0.18
Nodes (3): ConceptMasteredData, TestConceptDataModels, TestImports

### Community 8 - "Community 8"
Cohesion: 0.38
Nodes (8): AuthRefreshedData, PhaseCompletedData, PhasePlannedData, PhaseStartedData, PhaseVerifiedData, Tests for Phase aggregate data models., PhaseStartedData has no required fields beyond the empty model., TestPhaseDataModels

### Community 9 - "Community 9"
Cohesion: 0.42
Nodes (6): DrillGradedData, DrillPreparedData, DrillSubmittedData, StepVerifyPassedEvent, Tests for Drill aggregate data models., TestDrillDataModels

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (4): KolbMachine, Step state machine: idle->discussing->planning->executing->verifying->done., Finite state machine for a single Step's lifecycle., StepMachine

### Community 11 - "Community 11"
Cohesion: 0.29
Nodes (3): Verify all packages import without errors., Verify build and teach can both be imported without conflict., test_mode_silos_independent()

### Community 12 - "Community 12"
Cohesion: 0.29
Nodes (1): TestModeDecisionAuthDataModels

### Community 13 - "Community 13"
Cohesion: 0.52
Nodes (5): ArcRetiredData, ArcUpdatedData, DecisionMadeEvent, Tests for Arc aggregate data models., TestArcDataModels

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (4): DAGScheduler, Pure-Python DAG scheduler. No networkx dependency., Return all Step IDs ready for concurrent dispatch., Reactive DAG scheduler that computes unblocked Steps on state change.

### Community 15 - "Community 15"
Cohesion: 0.33
Nodes (3): Step + Slice tier snapshot glue for fine-grained revert., Manages snapshots at Step and Slice boundaries., SnapshotManager

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (3): db_init(), Per-session worker spawned by the plugin shim., Initialize the event store database by applying all pending migrations.

### Community 17 - "Community 17"
Cohesion: 0.4
Nodes (3): ProviderRouter, ProviderRouter: resolves model calls to litellm or direct SDK., Routes provider calls — litellm default, Anthropic SDK for extended thinking.

### Community 18 - "Community 18"
Cohesion: 0.67
Nodes (2): Pydantic event schemas for all state.* event types.  Event taxonomy (28+ events, SliceRevertedEvent

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (1): state-build MCP server entry point.

### Community 20 - "Community 20"
Cohesion: 0.67
Nodes (3): _check_ulid(), Validate that v is a well-formed ULID string., _validate_ulid()

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Event-sourced mental model projection for teach mode.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Drill engine for teach mode.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Concept graph operations for teach mode.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): HTTP API server for the state daemon.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): File and SSE watchers for the state daemon.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): `state daemon start/stop/status` CLI commands.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): auth.json I/O with filelock, chmod 0600 enforcement.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): opencode HTTP + state-daemon client bridge.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Validate ULID format if id is non-empty.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Protocol for writing and reading domain events.

## Knowledge Gaps
- **64 isolated node(s):** `Tests for state_core.database — connection factory, path resolution, WAL mode.`, `Default path points to .state/events.sqlite relative to CWD.`, `STATE_DB_PATH env var overrides the default path.`, `Connection has WAL journal mode enabled.`, `Connection has synchronous=NORMAL.` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 6`** (13 nodes): `Worker package — per-session process for state.`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (7 nodes): `TestModeDecisionAuthDataModels`, `.test_all_data_models_reject_extra()`, `.test_auth_refreshed_data()`, `.test_auth_rotated_data()`, `.test_decision_asked_data()`, `.test_decision_made_data()`, `.test_mode_activated_data()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (3 nodes): `Pydantic event schemas for all state.* event types.  Event taxonomy (28+ events`, `SliceRevertedEvent`, `schema.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (3 nodes): `state-build MCP server entry point.`, `mcp.py`, `mcp.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `Event-sourced mental model projection for teach mode.`, `mental_model.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `Drill engine for teach mode.`, `drill.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `Concept graph operations for teach mode.`, `concepts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `HTTP API server for the state daemon.`, `server.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `watchers.py`, `File and SSE watchers for the state daemon.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): ``state daemon start/stop/status` CLI commands.`, `cli.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `store.py`, `auth.json I/O with filelock, chmod 0600 enforcement.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `opencode HTTP + state-daemon client bridge.`, `bridge.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Validate ULID format if id is non-empty.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Protocol for writing and reading domain events.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Credential` connect `Community 4` to `Community 3`?**
  _High betweenness centrality (0.273) - this node is a cross-community bridge._
- **Are the 79 inferred relationships involving `EventEnvelope` (e.g. with `TestEventEnvelope` and `TestArcDataModels`) actually correct?**
  _`EventEnvelope` has 79 INFERRED edges - model-reasoned connections that need verification._
- **Are the 69 inferred relationships involving `TestStepDataModels` (e.g. with `ArcCreatedData` and `ArcCreatedEvent`) actually correct?**
  _`TestStepDataModels` has 69 INFERRED edges - model-reasoned connections that need verification._
- **Are the 69 inferred relationships involving `TestEventEnvelope` (e.g. with `ArcCreatedData` and `ArcCreatedEvent`) actually correct?**
  _`TestEventEnvelope` has 69 INFERRED edges - model-reasoned connections that need verification._
- **Are the 69 inferred relationships involving `TestBuildEvent` (e.g. with `ArcCreatedData` and `ArcCreatedEvent`) actually correct?**
  _`TestBuildEvent` has 69 INFERRED edges - model-reasoned connections that need verification._
- **Are the 76 inferred relationships involving `ArcCreatedData` (e.g. with `TestEventEnvelope` and `TestArcDataModels`) actually correct?**
  _`ArcCreatedData` has 76 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Tests for state_core.database — connection factory, path resolution, WAL mode.`, `Default path points to .state/events.sqlite relative to CWD.`, `STATE_DB_PATH env var overrides the default path.` to the rest of the system?**
  _64 weakly-connected nodes found - possible documentation gaps or missing edges._