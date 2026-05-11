---
phase: 404
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
autonomous: false
requirements:
  - SRP-01
  - SRP-02
  - SRP-03
  - SRP-04
  - SRP-05
  - SRP-06

must_haves:
  truths:
    - "SCOPE-PROHIBITION.md exists at .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md and fully specifies the scope-reduction-prohibition discipline guards (SRP-01..SRP-06)."
    - "<done>-vs-must_haves.artifacts cross-check is documented (SRP-01) with the harness behavior: at task end, every entry in must_haves.artifacts MUST have a corresponding observable artifact (file exists + wc -l >= min_lines); missing artifacts emit gate_strike (PRF-06 forward-reference)."
    - "Prohibited-language scan regex is rendered verbatim: PROHIBITED_RE = re.compile(r'\\b(v1|simplified|placeholder|todo|fixme|future)\\b', re.IGNORECASE) — case-insensitive word-boundary single-pass compiled regex."
    - "Positive and negative scan examples are rendered: matches `# v1 stub`, `# TODO: future work`; does NOT match `v1.5.2`, `version 1`, `simplified-config-loader.ts` (filename), `oversimplification` (substring), `futures.py` (filename substring)."
    - "Single-source-of-truth module is documented at state_build/harness/scope/ (mirrors gsd-2 branch-patterns.ts single-module pattern) exporting PROHIBITED_RE + EXCEPTION_RE + PATH_ALLOWLIST_GLOB."
    - "Scan-target scoping is documented: scan applies to source files inside files_modified ONLY; if Write/Edit targets a path NOT in files_modified, the allowlist check (Layer 1 of tool.execute.before stack) rejects FIRST and the language scan never runs."
    - "Tracking-issue exception (SRP-03) is rendered verbatim: EXCEPTION_RE = re.compile(r'\\b(TODO|FIXME)\\(([A-Z]+-\\d+)\\)') with cross-check that the captured ID resolves to (a) a REQUIREMENTS.md entry `**ID-NN**` heading OR (b) a deferred-items.md entry `- ID-NN:` row; cross-check is pure-machine grep at scan time."
    - "Path-allowlist scan exemption is documented: `.planning/**/*.md` path glob skips the prohibited-language scan entirely; the exemption is SCAN-ONLY (does NOT exempt from files_modified enforcement SRP-04)."
    - "Pydantic ScopeCheck event payload is rendered verbatim with the field set from 404-CONTEXT.md (task_id, step_id, slice_id, file_path, matched_token, matched_offset, matched_line, exception_matched bool, exception_id optional, exception_resolved bool, triggered_at, session_id)."
    - "files_modified allowlist enforcement (SRP-04) is documented: tool.execute.before write-block compares prospective target path against files_modified (exact match OR glob match); reject -> scope_deviation event; allow -> fall through to Phase 403 PAP-05 immutability check."
    - "scope_deviation_request MCP tool flow is rendered with the Pydantic ScopeDeviationRequest payload (task_id, step_id, slice_id, requested_path, justification <=1KB, requested_at, session_id) + scope_deviation_resolved event (resolution: approve | reject) + event-scoped one-shot allowlist semantic + 'files_modified itself is NEVER mutated at runtime' rule."
    - "request_step_split MCP tool (SRP-05) is rendered as the canonical split-recommendation trigger with Pydantic signature (reason str <=2KB, partial_artifacts list[str]) returning SplitRecommendation; NO NL keyword detection; explicit tool-call boundary mirrors gsd-2's complete_task / complete_slice / validate_milestone pattern."
    - "request_step_split harness behavior is rendered as a 4-step sequence: emit split_recommendation event + take worktree snapshot (mirrors compaction.snapshot_taken plumbing) + transition Slice to pending_replan terminal state + exit run-slice cleanly with partial commits preserved on the worktree branch."
    - "Pydantic SplitRecommendation event payload is rendered verbatim with the field set (task_id, step_id, slice_id, reason, partial_artifacts, requested_at, session_id)."
    - "deferred-items.md (SRP-06) artifact shape is documented: file at slices/N-name/deferred-items.md with table columns (ID, source_task, description, raised_at, status); harness appends rows on `scope_check` events with `exception_matched=False`; the Slice SUMMARY.md surfaces the deferred-items table."
    - "PAP-03 immutability of files_modified is restated: files_modified is locked at end of plan-slice (Phase 403 mutability matrix); scope_deviation_request flow does NOT mutate the field — overrides are event-scoped one-shot allowlists."
    - "Replan re-entry path is documented: research-slice planning stage reads split_recommendation event + worktree snapshot and produces NEW stepNPLAN.md files; PAP-03 locks survive replan when step_id unchanged; a split necessarily changes step_ids so must_haves are re-authored fresh."
    - "tool.execute.before write-block layer composition (Layers 1 and 3) is cross-referenced to PROOF-GATE.md Section 5: Layer 1 = files_modified allowlist (SRP-04), Layer 3 = prohibited-language scan (SRP-02), Layer 2 = Phase 403 PAP-05 immutability, Layer 4 = gate-failing next-task block (PRF-07)."
  artifacts:
    - path: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      provides: "Canonical scope-reduction-prohibition spec covering SRP-01..SRP-06 with PROHIBITED_RE + EXCEPTION_RE + path-allowlist + scope_deviation_request + request_step_split + deferred-items.md spec."
      min_lines: 500
  key_links:
    - from: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "tool.execute.before stack Layer 1 (files_modified) + Layer 3 (prohibited-language) cross-reference; SRP-01 done-vs-artifacts gate failure emits gate_strike (PRF-06)"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      via: "files_modified frontmatter field consumed from Phase 403 schema (STP-02); <done>-vs-must_haves.artifacts cross-check consumes the must_haves schema"
      pattern: "STEP-PLAN-FORMAT\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      to: ".planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md"
      via: "PAP-03 immutability of files_modified field consumed; PAP-05 diff-the-proposed-write is Layer 2 below SRP-04 Layer 1"
      pattern: "PLAN-AS-PROMPT\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "request_step_split worktree-snapshot mechanism reuses compaction.snapshot_taken plumbing"
      pattern: "CONTEXT-PROTOCOL\\.md"
---

<objective>
Author the canonical `SCOPE-PROHIBITION.md` spec document — the design contract that v14 Build Kernel implements for the scope-reduction-prohibition discipline guards. This file fully specifies: (1) the `<done>`-vs-`must_haves.artifacts` cross-check at task end (SRP-01); (2) the prohibited-language scan with PROHIBITED_RE corpus + EXCEPTION_RE tracking-issue pattern + path-allowlist scan exemption (SRP-02, SRP-03); (3) the `files_modified` allowlist enforcement via `tool.execute.before` Layer 1 + the `scope_deviation_request` MCP tool flow with event-scoped one-shot allowlist (SRP-04); (4) the `request_step_split` MCP tool as the canonical split-recommendation trigger (SRP-05); (5) the `deferred-items.md` out-of-scope logging artifact (SRP-06).

Purpose: SRP-01..SRP-06 fully covered. Downstream consumers — v14 (Build Kernel: implements `state_build/harness/scope/` module + PROHIBITED_RE/EXCEPTION_RE scanners + files_modified allowlist checker + scope_deviation_request MCP handler + request_step_split MCP handler + worktree-snapshot reuse), v15 (Build Core Commands: implements the deferred-items.md generator + the planner-validation `<acceptance_criteria>` annotation check that supplies the SRP-01 done-vs-artifacts evidence chain), Phase 405 (DEV-03 + DEV-04 paths consume scope_deviation_resolved events; subagent management consumes `request_step_split` recommendations), Phase 406 (harness rollup cites this spec for tier-1 advisory + tier-2 tool-block + the worktree-snapshot integration with compaction infrastructure) — all read from this file.

Output: One markdown spec doc at `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md`, ≥500 lines, fully populated with the PROHIBITED_RE + EXCEPTION_RE regex corpora, the path-allowlist scan exemption rule, three Pydantic event/MCP payloads (ScopeCheck, ScopeDeviationRequest, SplitRecommendation), the request_step_split harness behavior sequence, and the deferred-items.md artifact shape.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/STATE.md
@.planning/milestones/v41/ROADMAP.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/HANDOFF.md
@.planning/milestones/v41/phases/404/404-CONTEXT.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md
@.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md
@.planning/milestones/v41/phases/403/403-CONTEXT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — `files_modified` frontmatter field from Phase 403 STEP-PLAN-FORMAT.md (SRP-04 enforces against this list):
```python
class StepFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... other fields ...
    files_modified: list[str]                    # exact paths or globs
    # ... other fields ...
```
"`files_modified` may be exact paths or globs (planner picks; both forms valid). Glob expansion happens at the planner-validation stage, not at runtime."

Excerpt B — PROHIBITED_RE and EXCEPTION_RE corpora, verbatim from 404-CONTEXT.md `<decisions>` Prohibited-language scan subsection:
```python
import re
# Case-insensitive word-boundary single-pass regex; matches `# v1 stub`, `# TODO: future work`;
# does NOT match `v1.5.2`, `version 1`, `simplified-config-loader.ts`, `oversimplification`, `futures.py`.
PROHIBITED_RE = re.compile(r"\b(v1|simplified|placeholder|todo|fixme|future)\b", re.IGNORECASE)

# A prohibited token passes the scan if-and-only-if its occurrence matches EXCEPTION_RE
# AND the captured ID resolves to a real reference (REQUIREMENTS.md heading OR deferred-items.md row).
EXCEPTION_RE = re.compile(r"\b(TODO|FIXME)\(([A-Z]+-\d+)\)")

# Path glob skipping the scan entirely; .planning/ is the meta-prose layer where forbidden
# tokens carry their literal meaning.
PATH_ALLOWLIST_GLOB = ".planning/**/*.md"
```

Excerpt C — `EventEnvelope` from src/state_core/schema.py lines 239-265 (every event in this spec rides this envelope):
```python
class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = ""
    seq: int = 0
    aggregate_type: str = "arc"
    aggregate_id: str = ""               # step_id (per-step scope events) or slice_id (split events)
    type: str = ""                       # "state.step.scope_check" / "state.step.scope_deviation_request" / "state.slice.split_recommendation"
    data: dict[str, Any] = {}
```

Excerpt D — `MustHaves.artifacts` schema from Phase 403 STEP-PLAN-FORMAT.md (SRP-01 cross-checks against this):
```python
class ArtifactCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    provides: str
    min_lines: int
```

Excerpt E — `<done>` task sub-tag from Phase 403 STEP-PLAN-FORMAT.md §<task> Sub-tag Specification: "1-line measurable acceptance state. Immutable (task contract)."
</interfaces>

<threat_model>
Phase 404 is design-only. SCOPE-PROHIBITION.md introduces no production attack surface — it is a markdown specification. Threats considered (per `<security_constraint>`):

- **[high] scope_deviation_request abuse**: A malicious or sloppy agent could request deviation to a sensitive path (e.g., `~/.ssh/config`, `state-inputs/auth-credentials.md`, the parent repo's `.git/config`) and trigger a write outside the Step's scope. **Mitigation in spec:** the deviation flow uses event-scoped one-shot allowlists; the request, the resolution, and the time-bounded permit are all events. The resolution is a `checkpoint:decision` (Phase 405 DEV-03 path) requiring human approval under `--tiered` and `--conservative`. Under `--full-yolo`, the spec stipulates the auto-resolution policy is owned by Phase 405 (NOT this spec); SRP-04 specifies the request flow + the never-mutate-files_modified rule, NOT the auto-approval criteria. **`files_modified` itself is NEVER mutated at runtime** — overrides are scoped to one tool.execute.before invocation; subsequent writes to the same path require a fresh request.

- **[high] Path-traversal in scope_deviation_request.requested_path**: A `requested_path` containing `..` segments or absolute paths outside the repo root could exfiltrate or overwrite arbitrary files. **Mitigation in spec:** SCOPE-PROHIBITION.md stipulates requested_path MUST be realpath-resolved within repo root (mirrors Phase 403 PAP-02 path-confinement rule); requests with traversal-resolved paths outside repo root are rejected at MCP-tool-handler boundary before any human decision is surfaced. v14 implements via `pathlib.Path.resolve()` + ancestor check.

- **[med] EXCEPTION_RE bypass via fake tracking IDs**: A malicious agent could write `# TODO(FAKE-99)` to pass the prohibited-language scan. **Mitigation in spec:** cross-check is pure-machine grep at scan time: captured ID MUST resolve to (a) a REQUIREMENTS.md `**ID-NN**` heading OR (b) a deferred-items.md `- ID-NN:` row. Failure to resolve emits `state.step.scope_check` (tier=advisory) — the agent gets an advisory naming the unresolved ID; the write is rejected. v14 implements cross-check at the language-scan layer.

- **[med] Regex catastrophic backtracking**: PROHIBITED_RE and EXCEPTION_RE could DoS the scanner on long content. **Mitigation in spec:** spec MUST pre-compile both regexes with `re.compile`; both use simple alternation with no nested quantifiers (single-pass). Per-write content cap is recommended at 1 MB (v14 implementation).

- **[high] request_step_split abuse to skip work**: An agent could call request_step_split to bail out of every Step. **Mitigation in spec:** request_step_split takes a `reason: str <=2KB` argument that becomes part of the audit log. Phase 405 (DEV-04) consumes split_recommendation events; over-frequent splits in the milestone trigger a Rule 4 (architectural) human gate. Spec acknowledges the abuse vector; v14 emits split_recommendation_telemetry rolled up at Slice close for human review.

- **[low] Mode-isolation drift**: Build-only spec. **Mitigation:** explicit "Build-mode only" header note; explicit module-path pin (`state_build/harness/scope/`).

- **[low] Truncation marker injection**: The literal marker `[... truncated <N> bytes ...]` is harness-controlled (Phase 404 sibling specs share the truncation utility).

No production code lands. No secrets. No network calls. No untrusted input.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author SCOPE-PROHIBITION.md sections 1-5 (overview, done-vs-artifacts SRP-01, PROHIBITED_RE + EXCEPTION_RE corpora, scan target scoping, path-allowlist exemption)</name>
  <files>
    .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (full file — every locked decision; <decisions> subsection "Prohibited-language scan (SRP-02 / SRP-03 expanded)" provides verbatim source)
    - .planning/milestones/v41/REQUIREMENTS.md lines 80-87 (SRP-01..SRP-06 verbatim)
    - .planning/milestones/v41/HANDOFF.md lines 128-160 (§5 Scope Reduction Prohibition framing)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (search "files_modified" — confirms field is locked at plan-slice end; immutability via PAP-03 mutability matrix; search "ArtifactCheck" — for SRP-01 cross-check)
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (full file — PAP-03 mutability matrix locks files_modified; PAP-05 diff-the-proposed-write enforcer is Layer 2 of the tool.execute.before stack below SRP-04 Layer 1)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/file-tracking.md (search "inferCommitType" / "line 445" — word-boundary regex pattern this spec mirrors; search "branch-patterns" — single-module pattern)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (search "deferred-items" — confirms whether the artifact is already cataloged; if not, this spec proposes addition + Plan 04 amendment)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file if available — Plan 01 output; quote Layer 1 and Layer 3 of the tool.execute.before stack to confirm composition)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-PLAN.md lines 1-100 (Phase 403 spec-doc plan reference for verbose format/density target)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md`. Sections 1–5 below; Task 2 owns sections 6–10. **Concrete content from 404-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 1 — File header

    ```
    # Scope Reduction Prohibition (Canonical, v41)

    > **Phase:** 404
    > **Status:** Canonical (v41)
    > **Requirements covered:** SRP-01..SRP-06
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md). The single-source-of-truth regex module lives at `state_build/harness/scope/`.
    > **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
    > **Sibling specs:** PROOF-GATE.md (Layer 1 + Layer 3 of the tool.execute.before stack are owned by this spec; Layer 2 = Phase 403 PAP-05; Layer 4 = PROOF-GATE.md PRF-07), ANALYSIS-PARALYSIS-GUARD.md (paralysis counter — independent from scope events; both feed harness_intervention via Phase 406 HRN-05).
    ```

    1-paragraph overview: the harness prevents scope reduction via four overlapping mechanisms: (1) `<done>`-vs-`must_haves.artifacts` cross-check at task end (SRP-01) — missing artifacts trigger gate_strike per PROOF-GATE.md PRF-06; (2) prohibited-language scan (SRP-02) against `\b(v1|simplified|placeholder|todo|fixme|future)\b` on every Write/Edit content with case-insensitive word-boundary regex; (3) tracking-issue exception (SRP-03) via `TODO(REQ-ID)` form, cross-checked against REQUIREMENTS.md and deferred-items.md; (4) `files_modified` allowlist (SRP-04) via tool.execute.before Layer 1 + event-scoped scope_deviation_request flow. Plus two coordination tools: `request_step_split` MCP tool (SRP-05) for legitimate scope-too-large signals, and `deferred-items.md` artifact (SRP-06) for out-of-scope findings.

    ### Section 2 — `<done>`-vs-`must_haves.artifacts` Cross-Check (SRP-01)

    Heading: `## <done>-vs-must_haves.artifacts Cross-Check (SRP-01)`.

    1-paragraph intro: SRP-01 ensures every task's `<done>` claim is backed by observable artifacts. The harness validates `<done>` against the Step's `must_haves.artifacts` after task completion; missing artifacts trigger gate failure (cross-references PROOF-GATE.md PRF-06).

    Sub-section `### Cross-check protocol`:
    Render verbatim:
    1. **Task signals complete** — agent calls `complete_task` MCP tool OR attempts Write/Edit to a next-task file (per PROOF-GATE.md Section 6 §Strike trigger).
    2. **Harness reads frontmatter `must_haves.artifacts`** — list of `{path, provides, min_lines}` entries (Phase 403 ArtifactCheck — see `<interfaces>` Excerpt D).
    3. **For each ArtifactCheck**:
       - `test -f "<path>"` — file MUST exist.
       - `wc -l "<path>"` — MUST be >= `<min_lines>`.
    4. **Verdict**: any missing artifact OR under-line-count file -> task verdict `fail`; strike chain accrues per PROOF-GATE.md PRF-06.
    5. **`provides` field is informational only** (NOT machine-evaluated against the file's actual content). Per PROOF-GATE.md Section 2 (must_haves Evaluator Dispatch), this is by design — file existence + line count is the pure-machine boundary; semantic content checks require `must_haves.truths` or `must_haves.key_links` (regex grep).

    Sub-section `### Forward-pointer to PROOF-GATE.md`:
    "The SRP-01 cross-check is implemented as part of the task-end gate evaluation (PROOF-GATE.md Section 4 §Numbered protocol). The strike chain triggered by a missing artifact uses `check_type='artifact'` and `check_id='artifacts[i]'` in the GateStrike payload."

    Sub-section `### Why <done>-vs-artifacts and not <done>-vs-everything`:
    "The `<done>` claim is 1-line measurable acceptance state (Phase 403 STEP-PLAN-FORMAT.md §<task> Sub-tag Specification: see `<interfaces>` Excerpt E). It captures the agent's understanding of completion. The `must_haves.artifacts` list is the PLANNER's pre-authored set of observable artifacts. The cross-check ensures the agent's `<done>` claim is backed by these planner-pre-authored observables — preventing the agent from declaring 'done' on stub or skipped artifacts. The truths and key_links cross-checks happen at the same task-end gate; this section focuses on artifacts because they are the most-commonly-skipped scope-reduction vector."

    ### Section 3 — Prohibited-Language Scan (SRP-02)

    Heading: `## Prohibited-Language Scan (SRP-02)`.

    Sub-section `### Regex corpus`:
    Render verbatim (quote `<interfaces>` Excerpt B as a fenced Python block). Cite the source: "From 404-CONTEXT.md `<decisions>` Prohibited-language scan subsection."

    Sub-section `### Regex shape rationale`:
    Render verbatim from 404-CONTEXT.md:
    - "**Case-insensitive word boundary.** Single compiled regex per scanner load."
    - "Matches `# v1 stub`, `# TODO: future work`."
    - "Does **not** match `v1.5.2`, `version 1`, `simplified-config-loader.ts` (file name), `oversimplification` (substring), `futures.py` (substring)."
    - "Mirrors gsd-2's `inferCommitType` shape (`file-tracking.md:445` — 'concatenate, lowercase, then for each rule and each keyword, word-boundary regex matches'; multi-word phrases use substring — state has no multi-word tokens in v1 so word-boundary uniformly)."

    Sub-section `### Single-source-of-truth module`:
    Render verbatim:
    - "Regex constants live in a single Python module under `state_build/harness/scope/`, mirroring gsd-2's `branch-patterns.ts` pattern (single module exporting `SLICE_BRANCH_RE`/`QUICK_BRANCH_RE`/`WORKFLOW_BRANCH_RE`; imported by every consumer; updates flow from one place)."
    - "**Exported symbols:** `PROHIBITED_RE`, `EXCEPTION_RE`, `PATH_ALLOWLIST_GLOB`."
    - "v14 implementation: `src/state_build/harness/scope/patterns.py`."

    Sub-section `### Positive and negative scan examples`:
    Render as a markdown table:

    | Content | PROHIBITED_RE match? | Verdict |
    |---------|---------------------|---------|
    | `# v1 stub for the auth handler` | YES (`v1` matches at word boundary) | scope_check emitted (tier=advisory) |
    | `# TODO: implement future work` | YES (`TODO` AND `future` match) | scope_check emitted (multiple matches) |
    | `# Placeholder for the docs section` | YES (`Placeholder` matches case-insensitive) | scope_check emitted |
    | `import v1_5_2` (variable name) | NO (no word boundary around `v1`) | pass through |
    | `from importlib import simplified` (hypothetical module) | YES (`simplified` matches at word boundary) | scope_check emitted |
    | `# version 1 of the spec` | NO (`v1` substring of `version 1` is broken by the space; the token is `version`, not `v1`) | pass through |
    | `simplified-config-loader.ts` (filename in prose) | YES if scan target includes prose (`simplified` matches at word boundary) | scope_check emitted — agent must justify via EXCEPTION_RE |
    | `oversimplification of the design` | NO (`simplified` is a substring, not a token) | pass through |
    | `futures.py` (filename) | NO (`future` is a substring of `futures.py`, broken at the `s`) | pass through; BUT `future` would match in prose `future-proof design` |
    | `# TODO(SRP-04) — defer to v14` | YES (`TODO`, `v14` substring of `v1`?) | scope_check emitted; EXCEPTION_RE matches `TODO(SRP-04)`; cross-check resolves SRP-04 to REQUIREMENTS.md heading; scan PASSES |

    "**Edge case clarification**: `v14` does NOT match `v1` because the regex uses word-boundary `\b` — the `4` after `1` is a word character, so `v1` in `v14` is not at a word boundary. PROHIBITED_RE matches `v1` only when it's a standalone token. Tested via the bottom row of the table above."

    Sub-section `### Scan target scoping`:
    Render verbatim:
    - "**Scan target: source files inside `files_modified` only.** Scope = the SRP-04 allowlist."
    - "If a Write/Edit targets a path **not** in `files_modified`, it is rejected by the allowlist (Layer 1 of the tool.execute.before stack — see PROOF-GATE.md Section 5) **before** the prohibited-language scan ever runs."
    - "Files with `.md`, `.json`, `.yml`, `.yaml`, `.toml` extensions inside `files_modified` are **still scanned** (they are scoped sources for this Step) — UNLESS the path matches the spec-doc allowlist (Section 4)."
    - "Lightest enforcement consistent with PRF-04."

    Sub-section `### Performance bounds`:
    Render verbatim:
    - "**Per-write content cap**: 1 MB. Writes larger than 1 MB MAY skip the scan with a `scope_check_skipped` advisory event (v14 implementation territory)."
    - "**Pre-compiled regex** (`re.compile` at module load) — no per-write compilation cost."
    - "**Single-pass scan** (no nested loops) — O(n) over content length."

    ### Section 4 — Path-Allowlist Scan Exemption + Tracking-Issue Exception (SRP-03)

    Heading: `## Path-Allowlist Scan Exemption + Tracking-Issue Exception (SRP-03)`.

    Sub-section `### Path-allowlist scan exemption`:
    Render verbatim:
    - "**Spec-doc allowlist:** `.planning/**/*.md` path glob. Files matching the glob skip the prohibited-language scan **entirely**."
    - "Phase 404's own CONTEXT.md, ROADMAP.md, REQUIREMENTS.md, every `*-PLAN.md`, every `*-SUMMARY.md`, every `*-VERIFICATION.md`, every `*-RESEARCH.md` etc. exempt."
    - "Coarse but predictable; matches the project's structural convention that `.planning/` is the meta-prose layer where forbidden tokens carry their **literal meaning** (the word 'v1' in a roadmap describes version 1; it is not a placeholder)."

    Sub-section `### Scope of the exemption (CRITICAL)`:
    Render verbatim:
    - "**Scan exemption only.** The path-allowlist does **not** exempt files from `files_modified` enforcement (SRP-04) — Steps that write `.planning/` artifacts MUST still declare them in `files_modified`."
    - "**Layer order matters**: Layer 1 (files_modified) runs FIRST; Layer 3 (prohibited-language) is conditional on Layer 1 passing. Path-allowlist short-circuits Layer 3 only, never Layer 1."
    - "Cross-reference: PROOF-GATE.md Section 5 §Layer order — the four-layer stack is `files_modified -> Phase 403 immutability -> prohibited-language -> gate-failing next-task block`."

    Sub-section `### Glob implementation pin`:
    Render verbatim:
    - "**Glob syntax**: Python `fnmatch.fnmatch` (PEP-compliant; double-star `**` supported)."
    - "v14 may pick `pathlib.PurePath.match` instead (similar semantics); spec accepts both."
    - "v14 implementation tip: pre-compile the glob to a regex at module load (`fnmatch.translate(PATH_ALLOWLIST_GLOB)`) for fast path checks."

    Sub-section `### Tracking-issue exception (SRP-03)`:
    Render verbatim:
    - "A prohibited token passes the scan if-and-only-if its occurrence matches EXCEPTION_RE AND the captured ID resolves to a real reference."

    Re-render the EXCEPTION_RE (already in `<interfaces>` Excerpt B):

    ```python
    EXCEPTION_RE = re.compile(r"\b(TODO|FIXME)\(([A-Z]+-\d+)\)")
    # Captured ID must satisfy:
    #   1. Match an entry in .planning/milestones/<MS>/REQUIREMENTS.md (look for `**ID-NN**` heading), OR
    #   2. Match an entry in .planning/milestones/<MS>/slices/<N>/deferred-items.md (look for `- ID-NN:` row)
    ```

    Sub-section `### Cross-check protocol`:
    Render verbatim:
    1. PROHIBITED_RE match found at file_path, offset, line.
    2. Apply EXCEPTION_RE to the surrounding context (the entire matching line, plus a small window — recommended ±1 line for inline `TODO(REQ-ID)` usage).
    3. If EXCEPTION_RE matches, extract the captured ID (group 2 — e.g., `SRP-04` from `TODO(SRP-04)`).
    4. Cross-check the ID via pure-machine grep:
       - `grep -E '^\*\*<ID>\*\*' .planning/milestones/<MS>/REQUIREMENTS.md`
       - OR `grep -E '^- <ID>:' .planning/milestones/<MS>/slices/<N>/deferred-items.md`
    5. If either grep returns >= 1 match -> exception RESOLVED -> scan passes for this occurrence.
    6. If both greps return 0 matches -> exception UNRESOLVED -> emit `state.step.scope_check` (tier=advisory) with the bullet `Unresolved tracking ID: <id>. Add to deferred-items.md or REQUIREMENTS.md first.`

    Sub-section `### Path-confinement for the cross-check greps`:
    "The cross-check grep paths (REQUIREMENTS.md, deferred-items.md) MUST be realpath-resolved within the current milestone root + slice subdir. Any path traversal in the captured ID (e.g., `TODO(SLC-99/../../../secret)`) is rejected by EXCEPTION_RE itself (the regex only matches `[A-Z]+-\d+` — no slashes, no dots, no parent-dir tokens)."

    Sub-section `### Cross-check is pure-machine`:
    "Mirrors gsd-2's content-fingerprint-resync-gate pattern (declarative manifest + cross-check). No LLM-as-judge anywhere. PRF-04 compliance maintained."

    ### Section 5 — ScopeCheck Pydantic Event Payload (SRP-02)

    Heading: `## ScopeCheck Pydantic Event Payload (SRP-02)`.

    1-paragraph intro: every prohibited-language match (with or without exception cross-check) emits a `state.step.scope_check` event. The Pydantic payload carries the audit-trail evidence: file_path, matched_token, matched_offset, matched_line, exception_matched / exception_id / exception_resolved flags, session_id.

    Sub-section `### Pydantic class`:
    Render verbatim from 404-CONTEXT.md `<decisions>` Prohibited-language scan subsection:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict
    from typing import Literal

    class ScopeCheck(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str
        step_id: str
        slice_id: str
        file_path: str                                  # the file being written
        matched_token: str                              # the literal token, e.g., "v1", "TODO"
        matched_offset: int                             # byte offset in the proposed content
        matched_line: int                               # 1-indexed line number
        exception_matched: bool                         # True if EXCEPTION_RE matched the surrounding context
        exception_id: str | None                        # captured ID if exception_matched
        exception_resolved: bool                        # True if cross-check found the ID in REQUIREMENTS or deferred-items
        triggered_at: datetime
        session_id: str
    ```

    Sub-section `### Tier and harness action by exception state`:
    Render as a markdown table:

    | exception_matched | exception_resolved | Tier | Harness action | Write decision |
    |-------------------|---------------------|------|----------------|----------------|
    | False | (n/a) | advisory | Inject advisory naming the matched_token + remediation prompt ("add `TODO(REQ-ID)` reference") | REJECT |
    | True | False | advisory | Inject advisory naming the unresolved exception_id ("Add `<id>` to REQUIREMENTS.md or deferred-items.md first") | REJECT |
    | True | True | (no event tier; pass-through) | None (write proceeds; the ScopeCheck event is still emitted for audit) | ALLOW |

    "**Note**: in the third row (exception_matched=True, exception_resolved=True), the ScopeCheck event IS still emitted — but with tier-equivalent semantics 'audit-only' (no advisory inject, no reject). v14 implementation may add an explicit `tier: Literal['advisory', 'audit']` field; this spec's current payload uses the (exception_matched, exception_resolved) tuple as the implicit tier signal."

    Sub-section `### Bounded truncation`:
    "Same discipline as `GateStrike` and `ParalysisEvent` (see PROOF-GATE.md Section 7 §Bounded truncation): **content excerpts <= 2KB**. The `matched_offset` and `matched_line` are integers (no truncation); `matched_token` is by construction a single token from the PROHIBITED_RE corpus (max ~12 chars)."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` (Plan 01 output, if available) — Section 5 four-layer stack; quote the Layer 1 / Layer 3 descriptions verbatim and cross-reference here.
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` Section 2 — files_modified field; ArtifactCheck Pydantic class; quote for SRP-01 cross-check + SRP-04 enforcement target.
        - Known: `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` §Mutability Matrix — files_modified is locked; quote for the "never mutated at runtime" rule in Section 6 (Task 2).
        - Known: `.planning/milestones/v41/phases/403/specs/EXEMPLAR-stepNPLAN.md` lines 17-19 — example files_modified declaration; cite as the canonical worked example.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md | head -40` — confirms heading depth convention.
        - Grep pattern: `grep -n "PROHIBITED_RE\|EXCEPTION_RE\|PATH_ALLOWLIST_GLOB" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/404-CONTEXT.md` — locates verbatim source for the regex corpora.
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<decisions>` Prohibited-language scan subsection — verbatim source for Sections 3-4 (PROHIBITED_RE, EXCEPTION_RE, path-allowlist, ScopeCheck payload).
        - 404-CONTEXT.md `<decisions>` SRP-04 files_modified enforcement subsection — verbatim source for the layer composition note in Sections 3-4.
        - 404-CONTEXT.md `<specifics>` "Path-allowlist .planning/**/*.md is the right granularity" — informs Section 4 framing prose.
        - REQUIREMENTS.md lines 80-87 — SRP-01..SRP-06 verbatim (especially SRP-01 done-vs-artifacts wording, SRP-03 tracking-issue example).
        - file-tracking.md:445 (inferCommitType pattern) — informs Section 3 regex shape rationale.
        - file-tracking.md §branch-patterns — informs single-module pattern.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's scope-scanner unit tests will assert against this spec's positive/negative example table as a fixture.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 250)}' \
        && grep -qE "^# Scope Reduction Prohibition" "$F" \
        && grep -qE "^## <done>-vs-must_haves.artifacts Cross-Check" "$F" \
        && grep -qE "^## Prohibited-Language Scan" "$F" \
        && grep -qE "^## Path-Allowlist Scan Exemption" "$F" \
        && grep -qE "^## ScopeCheck Pydantic Event Payload" "$F" \
        && grep -q "PROHIBITED_RE" "$F" \
        && grep -q "EXCEPTION_RE" "$F" \
        && grep -q "PATH_ALLOWLIST_GLOB" "$F" \
        && grep -q "state_build/harness/scope" "$F" \
        && grep -q "branch-patterns" "$F" \
        && grep -q 'class ScopeCheck' "$F" \
        && grep -q 'extra="forbid"' "$F" \
        && grep -q "files_modified" "$F" \
        && grep -q "fnmatch" "$F" \
        && grep -q '.planning/\*\*/\*.md' "$F" \
        && grep -q "TODO(SRP-04)" "$F" \
        && grep -q "exception_matched" "$F" \
        && grep -q "exception_resolved" "$F" \
        && grep -q "PROOF-GATE.md" "$F" \
        && grep -q "STEP-PLAN-FORMAT.md" "$F" \
        && ! grep -q "state.teach" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[0]] File exists at `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` with >= 250 lines after Task 1 (Task 2 extends to >= 500).
    - [check: must_haves.truths[0]] H1 `# Scope Reduction Prohibition (Canonical, v41)` present.
    - [check: must_haves.truths[1]] SRP-01 done-vs-artifacts cross-check protocol documented (5-step numbered list).
    - [check: must_haves.truths[2]] PROHIBITED_RE rendered verbatim with the six tokens (v1, simplified, placeholder, todo, fixme, future).
    - [check: must_haves.truths[3]] Positive and negative scan examples table rendered with at least 8 rows including all the canonical cases from 404-CONTEXT.md.
    - [check: must_haves.truths[4]] Single-source-of-truth module documented (state_build/harness/scope/) citing file-tracking.md §branch-patterns.
    - [check: must_haves.truths[5]] Scan-target scoping documented (files_modified only; .md / .json / .yml / .yaml / .toml inside files_modified are still scanned unless in spec-doc allowlist).
    - [check: must_haves.truths[6]] EXCEPTION_RE rendered verbatim with cross-check protocol (5-step numbered list).
    - [check: must_haves.truths[7]] Path-allowlist `.planning/**/*.md` documented as SCAN-ONLY exemption (not files_modified exemption).
    - [check: must_haves.truths[8]] Pydantic ScopeCheck class rendered verbatim with all 12 fields.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: must_haves.key_links[0]] PROOF-GATE.md cross-referenced in Section 1 and Section 4 (Layer composition).
    - [check: must_haves.key_links[1]] STEP-PLAN-FORMAT.md cross-referenced for files_modified field and ArtifactCheck class in Section 2.
    - [check: verify_automated] File contains no `state.teach.` references (Build-mode isolation).
  </acceptance_criteria>

  <done>
    Sections 1–5 of SCOPE-PROHIBITION.md authored: file header + done-vs-artifacts SRP-01 cross-check + prohibited-language scan SRP-02 (PROHIBITED_RE corpus + positive/negative examples + single-module pattern + scan-target scoping) + path-allowlist scan exemption + tracking-issue exception SRP-03 (EXCEPTION_RE + cross-check protocol) + Pydantic ScopeCheck event payload. Task 2 will add files_modified allowlist enforcement (SRP-04), scope_deviation_request MCP flow, request_step_split MCP tool (SRP-05), deferred-items.md artifact (SRP-06), and the cross-references closing section.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append SCOPE-PROHIBITION.md sections 6-10 (files_modified allowlist SRP-04, scope_deviation_request flow, request_step_split SRP-05, deferred-items.md SRP-06, cross-references)</name>
  <files>
    .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (full file — Task 1 output; this task appends to it)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md lines 268-323 (SRP-04 files_modified enforcement subsection + SRP-05 split_recommendation mechanism subsection — verbatim source for Sections 6-8)
    - .planning/milestones/v41/REQUIREMENTS.md lines 84-87 (SRP-04..SRP-06 verbatim)
    - .planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md (full file — PAP-03 mutability + PAP-05 diff-the-proposed-write enforcer; the deviation flow lives inside the same tool.execute.before hook chain)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (search "files_modified" — confirms exact-paths OR glob-match semantics)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "compaction.snapshot_taken" — request_step_split worktree-snapshot mechanism reuses this plumbing)
    - .planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md (search "pending_replan" / "run-slice" — confirms the run-slice terminal state name)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file if available — Plan 01 output; quote the GateStrike / GateResolved pattern that this spec mirrors for scope_deviation_resolved)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/quality-enforcement.md (search "complete_task" / "complete_slice" / "validate_milestone" — explicit MCP tool-call boundary pattern that request_step_split mirrors)
    - .planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md (search "deferred-items" — confirms whether the artifact is already cataloged)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-PLAN.md lines 380-460 (Phase 403 spec-doc plan reference for Task 2 append pattern)
  </read_first>

  <action>
    Append sections 6–10 to the existing `SCOPE-PROHIBITION.md`. Use Edit (insert at end of file). **Concrete content from 404-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 6 — files_modified Allowlist Enforcement (SRP-04)

    Heading: `## files_modified Allowlist Enforcement (SRP-04)`.

    Sub-section `### tool.execute.before write-block enforcement`:
    Render verbatim from 404-CONTEXT.md `<decisions>` SRP-04 subsection:
    - "**`tool.execute.before` write-block enforces the allowlist.** Inherits the diff-the-proposed-write mechanism from Phase 403 PAP-05; reuses the same hook handler."
    - "Behavior:"
    - "  - Compute the prospective target path (Edit operation in-memory; Write target directly)."
    - "  - If target NOT in `files_modified` (exact match OR glob match — Phase 403 allowed both) -> reject the write with `scope_deviation` event."
    - "  - If target IS in `files_modified` -> fall through to PAP-05 immutability check, then to the prohibited-language scan, then allow."
    - "Cross-reference: PROOF-GATE.md Section 5 §Layer order — this is Layer 1 of the four-layer stack."

    Sub-section `### Glob-match implementation`:
    Render verbatim:
    - "**Glob syntax**: same as Section 4 path-allowlist (Python `fnmatch.fnmatch` with `**` support; v14 may pick `pathlib.PurePath.match`)."
    - "**Multi-entry semantics**: `files_modified` is a list; a target matches if ANY list entry matches (exact or glob)."
    - "**Pre-resolution**: all entries are realpath-resolved at plan-slice validation stage; resolution happens once, cached for the Step's lifetime."

    Sub-section `### files_modified immutability`:
    Render verbatim:
    - "**files_modified is locked at end of plan-slice** (Phase 403 PAP-03 mutability matrix; cross-reference: `PLAN-AS-PROMPT.md` §Mutability Matrix)."
    - "**The scope_deviation_request flow does NOT mutate the field** — overrides are event-scoped one-shot allowlists (Section 7 below). The on-disk `stepNPLAN.md` files_modified list is read-only at runtime."
    - "Replan re-entry from `split_recommendation` (Section 8) re-authors files_modified for the new Steps; the old Step's files_modified is preserved in the audit log (`state.step.plan_authored` event per Phase 403 STEP-EVENTS.md)."

    Sub-section `### Pydantic scope_deviation event payload`:
    Render:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict

    class ScopeDeviation(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str
        step_id: str
        slice_id: str
        attempted_path: str
        files_modified_at_time: list[str]               # snapshot of the Step's allowlist at the moment of rejection
        triggered_at: datetime
        session_id: str
        reject_reason: str                              # human-readable, e.g., "path not in files_modified allowlist"
    ```

    "Emitted on every Layer 1 rejection; the agent receives the reject_reason as the tool.execute.before hook's response. The agent's next action is typically a scope_deviation_request MCP call (Section 7) OR a request_step_split MCP call (Section 8) OR a different write within the allowlist."

    ### Section 7 — scope_deviation_request MCP Tool Flow

    Heading: `## scope_deviation_request MCP Tool Flow`.

    Sub-section `### Use case`:
    Render verbatim:
    - "When the agent legitimately needs to edit a file outside `files_modified` (e.g., discovers a missing import in a sibling file during execution), the agent emits a `scope_deviation_request` MCP tool call."

    Sub-section `### Pydantic MCP tool signature + payload`:
    Render verbatim from 404-CONTEXT.md:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict

    class ScopeDeviationRequest(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str
        step_id: str
        slice_id: str
        requested_path: str
        justification: str                              # agent-supplied rationale <= 1KB
        requested_at: datetime
        session_id: str

    # MCP tool signature
    def scope_deviation_request(
        requested_path: str,
        justification: str,                             # agent-supplied; daemon truncates to 1KB if longer
    ) -> ScopeDeviationResolved: ...
    ```

    Sub-section `### Resolution event + checkpoint:decision flow`:
    Render verbatim:
    - "The request surfaces as a `checkpoint:decision` under `--tiered` (per Phase 403 task-type behavior + Phase 405 DEV-03 territory)."
    - "Resolution emits `scope_deviation_resolved` with `resolution: approve | reject`."

    Render Pydantic class:

    ```python
    from typing import Literal

    class ScopeDeviationResolved(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str
        step_id: str
        slice_id: str
        requested_path: str
        resolution: Literal["approve", "reject"]
        resolver: Literal["human", "harness_auto"]      # harness_auto under --full-yolo per Phase 405 DEV-05 (autonomy-tier policy owned there)
        resolution_justification: str                   # if reject: human-supplied reason; if approve: optional context
        resolved_at: datetime
        session_id: str
        request_event_id: str                           # cross-link to ScopeDeviationRequest event
    ```

    Sub-section `### One-shot allowlist semantic`:
    Render verbatim:
    - "**Approved deviations write a temporary one-shot allowlist entry.**"
    - "Semantics:"
    - "  - The allowlist entry is keyed by `(session_id, task_id, requested_path)`."
    - "  - The entry is consumed by the NEXT tool.execute.before invocation targeting the path."
    - "  - The entry is one-shot: after consumption, subsequent writes to the same path require a fresh request."
    - "**The request and resolution events are part of the audit chain.**"
    - "**Files_modified itself is NEVER mutated at runtime** — the override is event-scoped."

    Sub-section `### Path-confinement at request boundary`:
    Render verbatim:
    - "The MCP tool handler MUST realpath-resolve `requested_path` within repo root + slice subdir BEFORE surfacing the checkpoint:decision."
    - "Path-traversal-resolved targets outside repo root are rejected at MCP-tool-handler boundary; an automatic `ScopeDeviationResolved` event is emitted with `resolution='reject'`, `resolver='harness_auto'`, `resolution_justification='path traversal outside repo root'`."
    - "No human decision is surfaced for traversal-rejected requests."

    Sub-section `### Audit chain`:
    Render verbatim:
    - "Audit chain for one approve cycle: `ScopeDeviationRequest` event -> `checkpoint:decision` surfaces via opencode `question` tool -> human approves -> `ScopeDeviationResolved(resolution='approve')` event -> one-shot allowlist entry written -> next Write/Edit consumes the entry -> tool.execute.before Layer 1 falls through -> Layers 2-4 still run normally -> write allowed."
    - "Audit chain for one reject cycle: `ScopeDeviationRequest` event -> `checkpoint:decision` surfaces -> human rejects -> `ScopeDeviationResolved(resolution='reject', resolution_justification=<reason>)` event -> agent receives rejection as the MCP tool's return value -> agent typically replans OR calls request_step_split."

    ### Section 8 — request_step_split MCP Tool (SRP-05)

    Heading: `## request_step_split MCP Tool (SRP-05)`.

    Sub-section `### Canonical trigger`:
    Render verbatim:
    - "**Explicit MCP tool `request_step_split` is the canonical trigger.**"
    - "**No NL keyword detection; no heuristic auto-split.** The agent must call the MCP tool explicitly."
    - "Mirrors gsd-2's explicit `complete_task` / `complete_slice` / `validate_milestone` MCP tool-call boundary pattern (`tools/complete-task.ts`, `tools/complete-slice.ts`, `tools/validate-milestone.ts`) — agent intent is signaled by tool call, not by NL output scan."

    Sub-section `### Pydantic MCP tool signature + payload`:
    Render verbatim from 404-CONTEXT.md:

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict

    class SplitRecommendation(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str
        step_id: str
        slice_id: str
        reason: str
        partial_artifacts: list[str]
        requested_at: datetime
        session_id: str

    # MCP tool signature
    def request_step_split(
        reason: str,                                    # <= 2KB; why the current Step exceeds one Step's scope
        partial_artifacts: list[str],                   # paths in the worktree that should be preserved for the replan
    ) -> SplitRecommendation: ...
    ```

    Sub-section `### Harness behavior (4-step sequence)`:
    Render verbatim:
    1. **Emit `split_recommendation` event** with the payload above (rides `state.slice.split_recommendation` event-type per the v40 EventEnvelope convention; aggregate_id is the slice_id).
    2. **Take a worktree snapshot** (mirrors Phase 402 `compaction.snapshot_taken` plumbing): records `slice_id`, `step_id`, `task_id`, worktree commit SHA, partial artifact paths.
    3. **Transition the Slice state to `pending_replan`** (run-slice terminal state — see SLICE-CYCLE.md).
    4. **Exit run-slice cleanly.** Partial commits stay on the worktree branch; the replan inherits them.

    Sub-section `### Replan re-entry`:
    Render verbatim:
    - "The replan re-enters research-slice / planning stage, which reads the `split_recommendation` event + the worktree snapshot and produces NEW `stepNPLAN.md` files breaking the over-scoped Step into smaller Steps."
    - "**PAP-03 locks survive replan when step_id is unchanged** (Phase 403)."
    - "**A split necessarily changes step_ids**, so `must_haves` for the new Steps are re-authored fresh."

    Sub-section `### Returned value`:
    Render verbatim:
    - "The MCP tool returns the populated `SplitRecommendation` Pydantic model to the agent's session so the agent's last log statement is auditable (per 404-CONTEXT.md Claude's Discretion — recommended over fire-and-exit)."
    - "After the return, the harness exits run-slice cleanly; the agent's session continues only until the run-slice exit signal propagates."

    Sub-section `### Abuse vector mitigation`:
    Render verbatim:
    - "Over-frequent splits in the milestone trigger a Rule 4 (architectural) human gate (Phase 405 DEV-04)."
    - "v14 emits `split_recommendation_telemetry` rolled up at Slice close for human review (frequency, reasons, partial_artifact patterns)."

    Sub-section `### NL keyword detection rejected`:
    Render verbatim:
    - "NL keyword detection for split-trigger was offered and rejected. Removes agent intent; risks false positives on legitimately hard checks."
    - "Implicit `split_recommendation` from N-paralysis+N-strike pattern ALSO rejected (mirrors 404-CONTEXT.md `<deferred>`). The agent calling `request_step_split` is the canonical signal."

    ### Section 9 — deferred-items.md Artifact (SRP-06)

    Heading: `## deferred-items.md Artifact (SRP-06)`.

    Sub-section `### Artifact location and shape`:
    Render verbatim:
    - "**File path:** `slices/N-name/deferred-items.md` (per-Slice; rooted in the slice folder)."
    - "**Format:** GFM-flavored markdown with a single H1 + a table + appended bullet rows."

    Sub-section `### Canonical template`:
    Render verbatim as a fenced markdown block:

    ```markdown
    # Deferred Items — Slice {N} ({slice-name})

    Out-of-scope findings raised during the Slice's lifecycle. Each row is referenced by tracking ID
    (per EXCEPTION_RE convention). Items in this file MUST satisfy EXCEPTION_RE cross-check in any
    later commit that uses `# TODO({ID})` or `# FIXME({ID})` referencing them.

    | ID | source_task | description | raised_at | status |
    |----|-------------|-------------|-----------|--------|
    | DEF-01 | step-1/task-2 | Missing error handling in CompactionSnapshot orjson loader | 2026-05-11T14:32:01Z | open |
    | DEF-02 | step-2/task-1 | TODO: pluggy plugin registration for state-build MCP server | 2026-05-11T15:01:44Z | scheduled-next-slice |
    ```

    Sub-section `### Row append rule`:
    Render verbatim:
    - "**Auto-append on `scope_check` events with `exception_matched=False`**: when the prohibited-language scanner emits a ScopeCheck with no resolved exception, the harness's deferred-items writer projector subscribes and appends a row with auto-generated ID (`DEF-<NN>` sequential within the Slice)."
    - "**Auto-append on `scope_deviation_request` events with `resolution='reject'`**: a rejected deviation that the human flagged as 'real but out-of-scope' (resolution_justification contains the tag `[defer]`) also triggers row append."
    - "**Manual append**: humans MAY append rows directly (e.g., during checkpoint:decision resolution); the file is mutable post-execute-slice start (NOT immutable like stepNPLAN.md)."

    Sub-section `### Status vocabulary`:
    Render verbatim:
    - "`open` — newly raised; not yet routed."
    - "`scheduled-next-slice` — promoted to the next Slice's CONTEXT.md `<deferred>` block."
    - "`scheduled-future-milestone` — promoted to the milestone-level v2 REQUIREMENTS section."
    - "`rejected` — reviewed and determined out-of-product-scope (not v1, not v2)."
    - "`resolved-in-slice` — addressed within the current Slice (e.g., a TODO turned into actual code with EXCEPTION_RE-satisfied tracking)."

    Sub-section `### Surface in Slice SUMMARY.md`:
    Render verbatim:
    - "The Slice SUMMARY.md (Phase 402 SLICE-CYCLE.md verify-slice stage output) MUST include a `## Deferred Items` section with a copy of the deferred-items.md table (or a `## Deferred Items` section stating 'No deferred items raised during this Slice.' if the table is empty)."
    - "v15 Build Core Commands implements the SUMMARY-generation step that pulls from `deferred-items.md`."

    Sub-section `### ARTIFACT-CATALOG.md amendment`:
    Render verbatim:
    - "**v40 ARTIFACT-CATALOG.md WILL receive a `## v41 Amendment` block** (Plan 04 of this phase) registering `deferred-items.md` as a per-Slice artifact in the canonical Slice folder layout."

    ### Section 10 — Cross-references

    Heading: `## Cross-references`.

    Bullet list:
    - **Sibling spec — proof gate:** `PROOF-GATE.md` Section 5 four-layer tool.execute.before stack: Layer 1 (files_modified — owned by this spec SRP-04), Layer 2 (Phase 403 PAP-05 immutability), Layer 3 (prohibited-language — owned by this spec SRP-02), Layer 4 (gate-failing next-task block — owned by PROOF-GATE.md PRF-07). The composition is the canonical enforcement pipeline; this spec owns 50% of it.
    - **Sibling spec — paralysis:** `ANALYSIS-PARALYSIS-GUARD.md` Section 7 §APG-vs-PRF — paralysis counter independent from scope events; both feed `harness_intervention` via Phase 406 HRN-05.
    - **Phase 403 carry-forward — format:** `STEP-PLAN-FORMAT.md` §Frontmatter Schema (STP-02) provides the `files_modified` field this spec enforces against; §<task> Sub-tag Specification (STP-04) provides the `<done>` field this spec cross-checks; §Mutability Matrix forward-pointer to PLAN-AS-PROMPT.md confirms files_modified is locked.
    - **Phase 403 carry-forward — mutability:** `PLAN-AS-PROMPT.md` §Mutability Matrix (PAP-03) locks files_modified; §6 (PAP-05) is Layer 2 below SRP-04 Layer 1 in the tool.execute.before stack.
    - **Phase 402 carry-forward — compaction snapshot:** `CONTEXT-PROTOCOL.md` §Compaction (CTX-05/06) is the source of the worktree-snapshot plumbing that `request_step_split` reuses; the SplitRecommendation does NOT cross-link snapshot_event_id by default (the snapshot is a side effect of run-slice exit, not a strike-replay analog), but v14 implementation MAY add the cross-link if EXEMPLAR observation warrants.
    - **Phase 402 carry-forward — Slice cycle:** `SLICE-CYCLE.md` defines the `pending_replan` run-slice terminal state that SRP-05 transitions to; the replan re-entry path is part of the plan-slice multi-stage internal pipeline (SLC-03).
    - **v40 baseline — events:** `EVENT-TAXONOMY.md` naming convention `state.{tier}.{action}`; this spec adds `state.step.scope_check`, `state.step.scope_deviation`, `state.step.scope_deviation_request`, `state.step.scope_deviation_resolved`, `state.slice.split_recommendation`. Plan 04 of this phase appends the `## v41 Amendment` block registering these.
    - **v40 baseline — artifacts:** `ARTIFACT-CATALOG.md` will receive Plan 04 amendment registering `deferred-items.md` as a per-Slice artifact.
    - **gsd-2 lineage:** `quality-enforcement.md` — explicit MCP tool-call boundary pattern (`complete_task`/`complete_slice`/`validate_milestone`) informs `request_step_split` shape; `file-tracking.md:445` — word-boundary regex pattern informs PROHIBITED_RE shape; `file-tracking.md §branch-patterns` — single-module pattern informs `state_build/harness/scope/`; `tool-system.md:851` — no-allowlist/denylist framing informs the advisory-not-security note in SCOPE-PROHIBITION (lighter than PROOF-GATE strikes, but stronger than ANALYSIS-PARALYSIS advisories — scope is a security-AND-quality boundary, not just advisory).
    - **Phase 405 forward:** `DEV-03` (auto-fix blocking issues with checkpoint:decision escalation) is the resolution path for `scope_deviation_request` under `--tiered`; `DEV-04` (architectural always-human-gate) is the resolution path for split_recommendation when frequency exceeds milestone threshold; `DEV-05` tiered autonomy table specifies the `--full-yolo` auto-approval policy (NOT owned by this spec).
    - **Phase 406 forward:** `harness_intervention` (HRN-05) umbrella event aggregates `scope_check` + `scope_deviation_request` + `split_recommendation`; the 4-tier intervention ladder (HRN-04) cites this spec for tier-1 (advisory inject from ScopeCheck tier=advisory) + tier-2 (tool-block from Layer 1 + Layer 3 of the stack) + tier-4 forward-reference for `pending_replan` transition triggered by request_step_split.

    Add closing 1-paragraph note: "v14 Build Kernel implements `state_build/harness/scope/patterns.py` (single module with PROHIBITED_RE + EXCEPTION_RE + PATH_ALLOWLIST_GLOB) + the files_modified allowlist checker + the EXCEPTION_RE cross-check resolver + the scope_deviation_request MCP handler + the request_step_split MCP handler + the worktree-snapshot reuse + the deferred-items.md writer projector. v15 Build Core Commands implements the planner-validation `<acceptance_criteria>` annotation check that ties to SRP-01 + the SUMMARY-generation step that pulls from deferred-items.md + the replan re-entry path that consumes split_recommendation events + the worktree snapshot. Phase 405 owns the auto-approval policy for `scope_deviation_request` under `--full-yolo` (DEV-05). Phase 406 cites this spec for tier-1 (advisory) + tier-2 (tool-block) of the 4-tier intervention ladder."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` (Plan 01 output, if available) — Section 5 four-layer stack; Section 7 GateStrike Pydantic class rendering pattern; Section 6 strike-chain cross-link pattern (mirror for scope_deviation_resolved's request_event_id cross-link).
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` Section 3 (state.step.plan_authored Pydantic class rendering) — event payload rendering pattern.
        - Known: `.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` — confirms `pending_replan` terminal state name + run-slice exit semantics.
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §6 — worktree-snapshot mechanism reused by request_step_split.
        - Grep pattern: `grep -nE "^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` — confirms Task 1's Section headings before appending.
        - Grep pattern: `grep -n "pending_replan\|run-slice" /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md` — confirms terminal-state name and run-slice exit semantics.
        - Grep pattern: `grep -n "deferred-items" /Users/tmac/Projects/state/.planning/milestones/v40/phases/401/specs/ARTIFACT-CATALOG.md` — confirms whether the artifact is already cataloged (informs whether Section 9 needs a "WILL receive amendment" forward-pointer or merely cites existing entry).
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<decisions>` SRP-04 files_modified enforcement subsection — verbatim source for Section 6.
        - 404-CONTEXT.md `<decisions>` SRP-05 split_recommendation mechanism subsection — verbatim source for Section 8.
        - 404-CONTEXT.md `<specifics>` "request_step_split is an explicit MCP-tool-call boundary, NOT an NL keyword pipe" — informs Section 8 framing.
        - 404-CONTEXT.md `<specifics>` "scope_deviation_request resolves via checkpoint:decision, not via direct files_modified mutation" — informs Section 7 framing.
        - 404-CONTEXT.md `<deferred>` "NL keyword detection for split_recommendation" and "Implicit split_recommendation from N-paralysis+N-strike pattern" both REJECTED — informs Section 8 §NL keyword detection rejected subsection.
        - REQUIREMENTS.md lines 84-87 — SRP-04..SRP-06 verbatim (files_modified blocks, split_recommendation, deferred-items.md).
        - quality-enforcement.md — explicit MCP tool-call boundary pattern (complete_task / complete_slice / validate_milestone).
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown spec. v14's scope_deviation_request + request_step_split MCP handler unit tests will use this spec's Pydantic class renderings as fixtures.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 500)}' \
        && grep -qE "^## files_modified Allowlist Enforcement" "$F" \
        && grep -qE "^## scope_deviation_request MCP Tool Flow" "$F" \
        && grep -qE "^## request_step_split MCP Tool" "$F" \
        && grep -qE "^## deferred-items.md Artifact" "$F" \
        && grep -qE "^## Cross-references" "$F" \
        && grep -q "class ScopeDeviation" "$F" \
        && grep -q "class ScopeDeviationRequest" "$F" \
        && grep -q "class ScopeDeviationResolved" "$F" \
        && grep -q "class SplitRecommendation" "$F" \
        && grep -q "scope_deviation_request" "$F" \
        && grep -q "request_step_split" "$F" \
        && grep -q "pending_replan" "$F" \
        && grep -q "one-shot allowlist" "$F" \
        && grep -q "never mutated" "$F" \
        && grep -q "complete_task" "$F" \
        && grep -q "compaction.snapshot_taken" "$F" \
        && grep -q "deferred-items.md" "$F" \
        && grep -q "DEF-" "$F" \
        && grep -q "EXCEPTION_RE" "$F" \
        && grep -q "PROOF-GATE.md" "$F" \
        && grep -q "ANALYSIS-PARALYSIS-GUARD.md" "$F" \
        && grep -q "PLAN-AS-PROMPT.md" "$F" \
        && grep -q "CONTEXT-PROTOCOL.md" "$F" \
        && grep -q "SLICE-CYCLE.md" "$F" \
        && grep -q "harness_intervention" "$F" \
        && grep -q "STEP-PLAN-FORMAT.md" "$F" \
        && grep -q "ARTIFACT-CATALOG.md" "$F" \
        && ! grep -q "state.teach" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[0]] SCOPE-PROHIBITION.md >= 500 lines after this task.
    - [check: must_haves.truths[9]] tool.execute.before write-block enforcement of files_modified documented in Section 6 with exact-match OR glob-match semantics + reject -> scope_deviation event + fall-through to PAP-05.
    - [check: must_haves.truths[15]] PAP-03 immutability of files_modified restated in Section 6 with "scope_deviation_request flow does NOT mutate" rule.
    - [check: must_haves.truths[10]] scope_deviation_request MCP tool flow documented with Pydantic ScopeDeviationRequest + ScopeDeviationResolved payloads + checkpoint:decision flow + event-scoped one-shot allowlist + "files_modified itself is NEVER mutated" rule.
    - [check: must_haves.truths[11]] request_step_split documented as canonical MCP tool with Pydantic signature (reason, partial_artifacts) returning SplitRecommendation; NO NL keyword detection; gsd-2 pattern citation.
    - [check: must_haves.truths[12]] 4-step harness behavior sequence documented (emit split_recommendation event + worktree snapshot + transition to pending_replan + clean run-slice exit with partial commits preserved).
    - [check: must_haves.truths[13]] Pydantic SplitRecommendation payload rendered with all 7 fields (task_id, step_id, slice_id, reason, partial_artifacts, requested_at, session_id).
    - [check: must_haves.truths[14]] deferred-items.md artifact shape documented (path slices/N-name/deferred-items.md + 5-column table + status vocabulary + Slice SUMMARY.md surface mechanism).
    - [check: must_haves.truths[16]] Replan re-entry path documented (research-slice planning stage consumes split_recommendation + worktree snapshot; PAP-03 locks survive when step_id unchanged; split necessarily changes step_ids so must_haves re-authored).
    - [check: must_haves.truths[17]] tool.execute.before layer composition cross-referenced to PROOF-GATE.md Section 5 in Section 10 (Layer 1 + 3 owned by this spec; Layer 2 = PAP-05; Layer 4 = PRF-07).
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: must_haves.key_links[0]] PROOF-GATE.md cited in Section 6 + Section 10.
    - [check: must_haves.key_links[2]] PLAN-AS-PROMPT.md cited in Section 6 for PAP-03 mutability.
    - [check: must_haves.key_links[3]] CONTEXT-PROTOCOL.md cited in Section 8 for compaction.snapshot_taken reuse.
    - [check: verify_automated] File contains no `state.teach.` references (Build-mode isolation).
  </acceptance_criteria>

  <done>
    SCOPE-PROHIBITION.md complete — all 10 sections present. SRP-01..SRP-06 fully covered with: SRP-01 done-vs-artifacts cross-check protocol (Section 2); SRP-02 PROHIBITED_RE corpus + positive/negative scan examples + single-module pattern + scan-target scoping + Pydantic ScopeCheck event (Sections 3+5); SRP-03 EXCEPTION_RE tracking-issue exception + path-allowlist scan exemption + cross-check protocol (Section 4); SRP-04 files_modified allowlist enforcement via tool.execute.before Layer 1 + scope_deviation_request MCP tool flow with event-scoped one-shot allowlist (Sections 6+7); SRP-05 request_step_split MCP tool with 4-step harness behavior + replan re-entry (Section 8); SRP-06 deferred-items.md artifact shape + auto-append rules + status vocabulary + Slice SUMMARY.md surface (Section 9); cross-references to sibling specs + Phase 402/403 carry-forwards (Section 10).
  </done>
</task>

<task type="auto">
  <name>Task 3: Write 03-scope-prohibition-spec-SUMMARY.md</name>
  <files>
    .planning/milestones/v41/phases/404/03-scope-prohibition-spec-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md (full file — Tasks 1+2 output)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md (full file — sibling SUMMARY shape reference)
    - .planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md (if available — Plan 01 sibling for consistency within Phase 404)
    - .planning/milestones/v41/phases/404/02-analysis-paralysis-guard-spec-SUMMARY.md (if available — Plan 02 sibling for consistency)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory gate
  </read_first>

  <action>
    Author the per-plan SUMMARY.md. Mirror `403-02-SUMMARY.md` structure (frontmatter + body sections).

    1. Frontmatter (mirror sibling shape):
       - `phase: 404-boolean-proof-gate-discipline-guards`
       - `plan: 03`
       - `subsystem: design-spec`
       - `tags: [scope-prohibition, prohibited-language, files-modified, scope-deviation, split-recommendation, deferred-items, srp]`
       - `requires`: 404-01 (PROOF-GATE.md for tool.execute.before stack Layer composition), 403 (STEP-PLAN-FORMAT.md for files_modified + ArtifactCheck schemas; PLAN-AS-PROMPT.md for PAP-03 mutability + PAP-05 immutability layer), 402 (CONTEXT-PROTOCOL.md for compaction.snapshot_taken plumbing; SLICE-CYCLE.md for pending_replan run-slice terminal state), 400 (EVENT-TAXONOMY.md naming + FRONTMATTER-SCHEMAS.md Pydantic convention; ARTIFACT-CATALOG.md for canonical Slice layout)
       - `provides`: SCOPE-PROHIBITION.md — canonical scope-reduction-prohibition spec covering SRP-01..SRP-06 (>=500 lines); PROHIBITED_RE + EXCEPTION_RE + PATH_ALLOWLIST_GLOB regex corpora; ScopeCheck + ScopeDeviation + ScopeDeviationRequest + ScopeDeviationResolved + SplitRecommendation Pydantic event/payload classes; tool.execute.before Layer 1 (files_modified) and Layer 3 (prohibited-language) ownership; request_step_split MCP tool + worktree-snapshot reuse; deferred-items.md per-Slice artifact shape with auto-append projector behavior + status vocabulary
       - `affects`: 404-04 (event taxonomy amendment registers state.step.scope_* + state.slice.split_recommendation; ARTIFACT-CATALOG.md amendment registers deferred-items.md), v14 Build Kernel (implements state_build/harness/scope/patterns.py + scope_deviation_request + request_step_split MCP handlers + deferred-items.md projector + worktree-snapshot reuse), v15 Build Core Commands (implements planner-validation acceptance-criteria annotation check + SUMMARY-generation step pulling deferred-items.md + replan re-entry path consuming split_recommendation events), Phase 405 (DEV-03 + DEV-04 paths consume scope_deviation_resolved + split_recommendation events; DEV-05 tiered autonomy specifies --full-yolo auto-approval policy NOT owned here), Phase 406 (harness rollup cites this spec for tier-1 advisory + tier-2 tool-block of the 4-tier intervention ladder; harness_intervention aggregates ScopeCheck + ScopeDeviationRequest + SplitRecommendation)
       - `tech-stack.patterns`: ["Single-module regex pattern state_build/harness/scope/ mirroring gsd-2 branch-patterns.ts (PROHIBITED_RE + EXCEPTION_RE + PATH_ALLOWLIST_GLOB)", "Word-boundary case-insensitive regex with no nested quantifiers; mirrors gsd-2 inferCommitType pattern (file-tracking.md:445)", "Path-allowlist .planning/**/*.md as SCAN-ONLY exemption (does NOT exempt from files_modified enforcement)", "Tracking-issue exception EXCEPTION_RE with pure-machine grep cross-check against REQUIREMENTS.md and deferred-items.md", "files_modified locked at plan-slice end (PAP-03 immutability); event-scoped one-shot allowlist for legitimate deviations; never-mutate-at-runtime rule", "Explicit MCP tool-call boundary for request_step_split (no NL keyword detection); mirrors gsd-2 complete_task/complete_slice/validate_milestone pattern", "Worktree-snapshot reuse for split_recommendation (mirrors Phase 402 compaction.snapshot_taken plumbing)", "deferred-items.md auto-append projector triggered on scope_check.exception_matched=False events"]
       - `key-files.created`: `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` (>=500 lines)
       - `key-decisions`: 8-10 locked-in design choices (regex word-boundary shape, single-module pattern, .planning/**/*.md path allowlist, EXCEPTION_RE form `TODO|FIXME(ID-NN)` with cross-check, scope_deviation_request via checkpoint:decision NOT files_modified mutation, request_step_split as explicit MCP tool boundary, NL-keyword-detection REJECTED, implicit-split-from-N-paralysis-and-N-strike REJECTED, deferred-items.md per-Slice file with auto-append projector, layer composition with PROOF-GATE.md owning Layers 2+4 and this spec owning Layers 1+3)
       - `requirements-completed`: SRP-01..SRP-06
       - `duration`: ~28min (estimated; this is the densest Plan in Phase 404)
       - `completed`: {date}

    2. Body sections (mirror 403-02-SUMMARY.md format):
       - `# Plan 404-03 Summary: SCOPE-PROHIBITION.md`
       - Bold tagline (1-2 sentences)
       - `## What Was Built` — 1 paragraph: SCOPE-PROHIBITION.md at canonical path; 10 sections; SRP-01..SRP-06 covered; 3 regex corpora + 5 Pydantic event/payload classes; tool.execute.before Layer 1 + Layer 3 ownership; deferred-items.md artifact shape.
       - `## Key Decisions` — bullets
       - `## Files Touched` — SCOPE-PROHIBITION.md only
       - `## Open Items / Deferred` — bullets:
         - "Hybrid per-token regex for prohibited language REJECTED — uniform word-boundary suffices for v1 token list; revisit if v2 expands."
         - "Frontmatter opt-out marker for prohibited-language scan REJECTED — path-allowlist `.planning/**/*.md` is correct granularity."
         - "`scope_check` tier-2 tool-block on first match REJECTED — tier=advisory only; agent justifies via EXCEPTION_RE."
         - "NL keyword detection for split_recommendation REJECTED — explicit MCP tool-call boundary."
         - "Implicit split_recommendation from N-paralysis+N-strike pattern REJECTED — preserves agent intent."
         - "Shared APG+PRF counter REJECTED — counter independence preserved per loop-control.md Correction 1."
         - "Bullet-as-regex pattern extraction for <acceptance_criteria> REJECTED — index binding wins."
         - "auto+tdd test-file inference deferred to v14 (planner emits both source AND test paths in files_modified for v1)."
         - "Generated-file allowlist (lockfiles, migrations, code-gen) deferred to v14 (files_modified.generated sub-field if needed)."
         - "Plan 04 of this phase appends `## v41 Amendment` block to v40 EVENT-TAXONOMY.md (registers scope events + split_recommendation) and ARTIFACT-CATALOG.md (registers deferred-items.md as per-Slice artifact)."
       - `## Downstream Hooks` — bullets:
         - "v14 Build Kernel implements state_build/harness/scope/patterns.py (PROHIBITED_RE + EXCEPTION_RE + PATH_ALLOWLIST_GLOB) + files_modified allowlist checker + EXCEPTION_RE cross-check resolver + scope_deviation_request MCP handler + request_step_split MCP handler + worktree-snapshot reuse + deferred-items.md projector."
         - "v15 Build Core Commands implements planner-validation <acceptance_criteria> annotation check (PRF-02 ANNOTATION_RE binding) + SUMMARY-generation pull from deferred-items.md + replan re-entry consuming split_recommendation."
         - "Phase 405 DEV-03 consumes scope_deviation_resolved; DEV-04 consumes split_recommendation telemetry; DEV-05 specifies --full-yolo auto-approval policy NOT owned here."
         - "Phase 406 cites this spec for tier-1 + tier-2 of the 4-tier intervention ladder; harness_intervention aggregates all five scope/split events."
       - `## Task Commits` — placeholder
       - `## Deviations from Plan` — placeholder
       - `## Self-Check: PASSED` — checklist of every must_haves.truth verified

    Length: 100-180 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md` — sibling SUMMARY exemplar; mirror frontmatter shape + body sections + bullet density.
        - Known: `.planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md` (Plan 01 sibling, if available) — Phase 404 internal sibling for consistency.
        - Known: `.planning/milestones/v41/phases/404/02-analysis-paralysis-guard-spec-SUMMARY.md` (Plan 02 sibling, if available).
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md per-plan-SUMMARY-mandatory subsection.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/03-scope-prohibition-spec-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 80)}' \
        && grep -q "Plan 404-03" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "SCOPE-PROHIBITION.md" "$F" \
        && grep -q "SRP-01" "$F" \
        && grep -q "SRP-06" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] SUMMARY exists with >= 80 lines.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: verify_automated] SUMMARY references Plan 03, the SCOPE-PROHIBITION.md spec, all 6 SRP requirements covered, and forward-points to Plans 01/02/04 (sibling specs + amendment plan).
    - [check: verify_automated] All four core sections present (What Was Built, Key Decisions, Files Touched, Downstream Hooks).
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate closed for Plan 404-03.
  </done>
</task>

</tasks>

<verification>
- File `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` exists with >= 500 lines.
- File `.planning/milestones/v41/phases/404/03-scope-prohibition-spec-SUMMARY.md` exists with >= 80 lines.
- All 10 H2 sections present in the spec (<done>-vs-must_haves.artifacts Cross-Check, Prohibited-Language Scan, Path-Allowlist Scan Exemption + Tracking-Issue Exception, ScopeCheck Pydantic Event Payload, files_modified Allowlist Enforcement, scope_deviation_request MCP Tool Flow, request_step_split MCP Tool, deferred-items.md Artifact, Cross-references — plus the H1 file header).
- PROHIBITED_RE, EXCEPTION_RE, PATH_ALLOWLIST_GLOB all rendered verbatim.
- Five Pydantic classes rendered (ScopeCheck, ScopeDeviation, ScopeDeviationRequest, ScopeDeviationResolved, SplitRecommendation) — all with `extra="forbid"`.
- Positive and negative scan examples table rendered with at least 8 rows.
- `state_build/harness/scope/` single-module pattern documented.
- `.planning/**/*.md` path-allowlist documented as SCAN-ONLY exemption.
- request_step_split 4-step harness behavior sequence rendered (emit event + take snapshot + transition pending_replan + exit clean).
- deferred-items.md canonical template + auto-append projector + 5-status vocabulary rendered.
- Cross-references to PROOF-GATE.md, ANALYSIS-PARALYSIS-GUARD.md, STEP-PLAN-FORMAT.md, PLAN-AS-PROMPT.md, CONTEXT-PROTOCOL.md, SLICE-CYCLE.md, EVENT-TAXONOMY.md, ARTIFACT-CATALOG.md, harness_intervention all present.
- No `state.teach.` references.
- "files_modified itself is NEVER mutated at runtime" rule rendered.
- "explicit MCP tool-call boundary" + "no NL keyword detection" rendered.
- Layer composition with PROOF-GATE.md ownership (Layers 2+4) and this spec ownership (Layers 1+3) documented.
</verification>

<success_criteria>
- SRP-01 (<done>-vs-must_haves.artifacts cross-check): 5-step protocol rendered with gate_strike forward-reference to PROOF-GATE.md PRF-06.
- SRP-02 (prohibited-language scan): PROHIBITED_RE rendered with positive/negative examples + single-module pattern + scan-target scoping + Pydantic ScopeCheck event.
- SRP-03 (tracking-issue exception): EXCEPTION_RE rendered with `TODO|FIXME(ID-NN)` form + pure-machine grep cross-check against REQUIREMENTS.md and deferred-items.md.
- SRP-04 (files_modified allowlist via tool.execute.before): Layer 1 of the stack documented; Pydantic ScopeDeviation event + scope_deviation_request MCP tool flow + event-scoped one-shot allowlist + "files_modified itself NEVER mutated" rule.
- SRP-05 (split_recommendation routing): request_step_split MCP tool as canonical boundary + Pydantic SplitRecommendation + 4-step harness behavior + replan re-entry + NL-keyword-detection REJECTED + abuse-vector mitigation.
- SRP-06 (deferred-items.md): per-Slice file path + canonical template + auto-append projector on scope_check.exception_matched=False events + 5-status vocabulary + Slice SUMMARY.md surface mechanism.
- Per-plan SUMMARY.md gate closed.
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` (>= 500 lines)
- `.planning/milestones/v41/phases/404/03-scope-prohibition-spec-SUMMARY.md` (>= 80 lines)

Plan 04 (v40 EVENT-TAXONOMY.md + ARTIFACT-CATALOG.md amendments) in Wave 2 can now reference this spec for `state.step.scope_check` / `state.step.scope_deviation` / `state.step.scope_deviation_request` / `state.step.scope_deviation_resolved` / `state.slice.split_recommendation` events and `deferred-items.md` artifact registration.
</output>
