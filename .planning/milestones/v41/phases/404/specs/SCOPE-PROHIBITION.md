# Scope Reduction Prohibition (Canonical, v41)

> **Phase:** 404
> **Status:** Canonical (v41)
> **Requirements covered:** SRP-01..SRP-06
> **Build-mode only.** The Build mode's Python package (`state_build.*`) MUST NOT import the Teach mode's Python package (cardinal rule, PROJECT.md). The single-source-of-truth regex module lives at `state_build/harness/scope/`.
> **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
> **Sibling specs:** PROOF-GATE.md (Layer 1 + Layer 3 of the `tool.execute.before` stack are owned by this spec; Layer 2 = Phase 403 PAP-05; Layer 4 = PROOF-GATE.md PRF-07), ANALYSIS-PARALYSIS-GUARD.md (paralysis counter — independent from scope events; both feed `harness_intervention` via Phase 406 HRN-05).

## Overview

The harness prevents scope reduction via four overlapping mechanisms working as a coordinated discipline pipeline: (1) `<done>`-vs-`must_haves.artifacts` cross-check at task end (SRP-01) — missing artifacts trigger `gate_strike` per PROOF-GATE.md PRF-06; (2) prohibited-language scan (SRP-02) against `\b(v1|simplified|placeholder|todo|fixme|future)\b` on every Write/Edit content with case-insensitive word-boundary regex; (3) tracking-issue exception (SRP-03) via `TODO(REQ-ID)` form, cross-checked against REQUIREMENTS.md and `deferred-items.md`; (4) `files_modified` allowlist (SRP-04) via `tool.execute.before` Layer 1 + event-scoped `scope_deviation_request` flow. Plus two coordination tools: `request_step_split` MCP tool (SRP-05) for legitimate scope-too-large signals, and `deferred-items.md` artifact (SRP-06) for out-of-scope findings raised during execution.

Each mechanism is pure-machine (PRF-04): regex match, file existence, line count, glob match, grep cross-check. No LLM-as-judge anywhere in the scope-prohibition pipeline. The four-layer `tool.execute.before` stack composes the enforcement: Layer 1 (`files_modified` allowlist — SRP-04, owned by this spec) → Layer 2 (Phase 403 PAP-05 immutability) → Layer 3 (prohibited-language scan — SRP-02, owned by this spec) → Layer 4 (gate-failing next-task block — PROOF-GATE.md PRF-07). The composition is the canonical enforcement pipeline; SCOPE-PROHIBITION.md owns two of the four layers.

## <done>-vs-must_haves.artifacts Cross-Check (SRP-01)

SRP-01 ensures every task's `<done>` claim is backed by observable artifacts. The harness validates `<done>` against the Step's `must_haves.artifacts` after task completion; missing artifacts trigger gate failure (cross-references PROOF-GATE.md PRF-06). This is the structural protection against the most-commonly-observed scope-reduction vector: an agent declaring "done" on a stub artifact or skipping an artifact entirely.

### Cross-check protocol

1. **Task signals complete** — agent calls `complete_task` MCP tool OR attempts Write/Edit to a next-task file (per PROOF-GATE.md Section 6 §Strike trigger).
2. **Harness reads frontmatter `must_haves.artifacts`** — list of `{path, provides, min_lines}` entries (Phase 403 `ArtifactCheck` — see `<interfaces>` Excerpt D in the plan; canonical schema in `STEP-PLAN-FORMAT.md` §Frontmatter Schema).
3. **For each `ArtifactCheck`**:
   - `test -f "<path>"` — file MUST exist.
   - `wc -l "<path>"` — MUST be >= `<min_lines>`.
4. **Verdict**: any missing artifact OR under-line-count file → task verdict `fail`; strike chain accrues per PROOF-GATE.md PRF-06.
5. **`provides` field is informational only** (NOT machine-evaluated against the file's actual content). Per PROOF-GATE.md Section 2 (must_haves Evaluator Dispatch), this is by design — file existence + line count is the pure-machine boundary; semantic content checks require `must_haves.truths` or `must_haves.key_links` (regex grep).

### Forward-pointer to PROOF-GATE.md

The SRP-01 cross-check is implemented as part of the task-end gate evaluation (PROOF-GATE.md Section 4 §Numbered protocol). The strike chain triggered by a missing artifact uses `check_type='artifact'` and `check_id='artifacts[i]'` in the `GateStrike` payload. Strike escalation (3-advisory → reinject → 3-advisory → human gate) is owned by PROOF-GATE.md; this spec only documents the trigger condition.

### Why `<done>`-vs-artifacts and not `<done>`-vs-everything

The `<done>` claim is 1-line measurable acceptance state (Phase 403 `STEP-PLAN-FORMAT.md` §`<task>` Sub-tag Specification: "1-line measurable acceptance state. Immutable (task contract)."). It captures the agent's understanding of completion. The `must_haves.artifacts` list is the PLANNER's pre-authored set of observable artifacts. The cross-check ensures the agent's `<done>` claim is backed by these planner-pre-authored observables — preventing the agent from declaring 'done' on stub or skipped artifacts. The `truths` and `key_links` cross-checks happen at the same task-end gate evaluation pass; this section focuses on `artifacts` because they are the most-commonly-skipped scope-reduction vector in observed agent runs (matches gsd-2's empirical evidence — the artifact-skip pattern is the dominant failure shape).

## Prohibited-Language Scan (SRP-02)

The prohibited-language scan is the lightweight runtime guard against scope-reducing language landing in code. It runs on every Write/Edit content body, applies a single compiled regex, and emits a `scope_check` event for every match. The scan is the v1 minimum-viable enforcement; richer semantic analysis (e.g., LLM-as-judge for "is this a placeholder stub?") is explicitly rejected per PRF-04.

### Regex corpus

From `404-CONTEXT.md` `<decisions>` Prohibited-language scan subsection (verbatim):

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

### Regex shape rationale

- **Case-insensitive word boundary.** Single compiled regex per scanner load.
- Matches `# v1 stub`, `# TODO: future work`.
- Does **not** match `v1.5.2`, `version 1`, `simplified-config-loader.ts` (file name), `oversimplification` (substring), `futures.py` (substring).
- Mirrors gsd-2's `inferCommitType` shape (`file-tracking.md:445` — "concatenate, lowercase, then for each rule and each keyword, word-boundary regex matches"; multi-word phrases use substring — state has no multi-word tokens in v1 so word-boundary uniformly).
- The `re.IGNORECASE` flag is load-bearing: agents emit `TODO`, `Todo`, `todo` interchangeably; without case-insensitivity the scan would miss ~40% of real occurrences (empirical observation from gsd-2 logs).

### Single-source-of-truth module

- Regex constants live in a single Python module under `state_build/harness/scope/`, mirroring gsd-2's `branch-patterns.ts` pattern (single module exporting `SLICE_BRANCH_RE`/`QUICK_BRANCH_RE`/`WORKFLOW_BRANCH_RE`; imported by every consumer; updates flow from one place).
- **Exported symbols:** `PROHIBITED_RE`, `EXCEPTION_RE`, `PATH_ALLOWLIST_GLOB`.
- **v14 implementation:** `src/state_build/harness/scope/patterns.py`.
- The module is import-only — it exposes constants, not functions. The scanner logic that consumes these constants lives in a sibling module (`scanner.py`), separating "what to match" from "how to scan."
- This single-module pattern means any future tightening (e.g., adding `temp` or `stub` to the corpus) is one file edit + one test update; consumers re-import on next module reload.

### Positive and negative scan examples

| Content                                         | `PROHIBITED_RE` match?                                            | Verdict                                                                                                          |
| ----------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `# v1 stub for the auth handler`                | YES (`v1` matches at word boundary)                               | `scope_check` emitted (tier=advisory)                                                                            |
| `# TODO: implement future work`                 | YES (`TODO` AND `future` match)                                   | `scope_check` emitted (multiple matches; one event per token)                                                    |
| `# Placeholder for the docs section`            | YES (`Placeholder` matches case-insensitive)                      | `scope_check` emitted                                                                                            |
| `import v1_5_2` (variable name)                 | NO (no word boundary around `v1`)                                 | pass through                                                                                                     |
| `from importlib import simplified` (hypothetical module) | YES (`simplified` matches at word boundary)                 | `scope_check` emitted                                                                                            |
| `# version 1 of the spec`                       | NO (the token is `version`, not `v1`; `v1` is not a standalone token here) | pass through                                                                                                     |
| `simplified-config-loader.ts` (filename in prose) | YES if scan target includes prose (`simplified` matches at word boundary) | `scope_check` emitted — agent must justify via `EXCEPTION_RE`                                                  |
| `oversimplification of the design`              | NO (`simplified` is a substring, not a token)                     | pass through                                                                                                     |
| `futures.py` (filename)                         | NO (`future` is a substring of `futures.py`, broken at the `s`)   | pass through; BUT `future` would match in prose `future-proof design`                                            |
| `# TODO(SRP-04) — defer to v14`                 | YES (`TODO` matches)                                              | `scope_check` emitted; `EXCEPTION_RE` matches `TODO(SRP-04)`; cross-check resolves SRP-04 to REQUIREMENTS.md heading; scan PASSES |

**Edge case clarification — `v14` does NOT match `v1`.** The regex uses word-boundary `\b` — the `4` after `1` is a word character, so `v1` in `v14` is not at a word boundary (no `\b` between `v1` and `4`). `PROHIBITED_RE` matches `v1` only when it is a standalone token (preceded and followed by non-word characters or string boundaries). Tested via the bottom row of the table above (`TODO(SRP-04) — defer to v14`): the `v14` substring does NOT trigger a `v1` match; only the `TODO` does. This is the intended semantic and is load-bearing for the EXCEPTION_RE cross-check to function: tracking IDs like `SLC-04`, `PRF-04`, `SRP-04` would otherwise constantly false-positive on the embedded version-like substring.

### Scan target scoping

- **Scan target: source files inside `files_modified` only.** Scope = the SRP-04 allowlist.
- If a Write/Edit targets a path **not** in `files_modified`, it is rejected by the allowlist (Layer 1 of the `tool.execute.before` stack — see PROOF-GATE.md Section 5) **before** the prohibited-language scan ever runs.
- Files with `.md`, `.json`, `.yml`, `.yaml`, `.toml` extensions inside `files_modified` are **still scanned** (they are scoped sources for this Step) — UNLESS the path matches the spec-doc allowlist (Section "Path-Allowlist Scan Exemption + Tracking-Issue Exception (SRP-03)" below).
- Lightest enforcement consistent with PRF-04: the planner controls what gets scanned by what they put in `files_modified`; the scanner just enforces.

### Performance bounds

- **Per-write content cap**: 1 MB. Writes larger than 1 MB MAY skip the scan with a `scope_check_skipped` advisory event (v14 implementation territory).
- **Pre-compiled regex** (`re.compile` at module load) — no per-write compilation cost.
- **Single-pass scan** (no nested loops) — O(n) over content length.
- No catastrophic backtracking is possible: `PROHIBITED_RE` uses simple alternation with no nested quantifiers; `EXCEPTION_RE` uses a single character class `[A-Z]+\d+` with linear matching.

## Path-Allowlist Scan Exemption + Tracking-Issue Exception (SRP-03)

SRP-03 provides two escape hatches for legitimate use of prohibited tokens: a coarse-grained **path-allowlist** for the `.planning/` meta-prose layer, and a fine-grained **tracking-issue exception** via `TODO(ID)` references. Both exist because some places MUST contain the literal words `v1`, `TODO`, `placeholder`, etc. — the harness needs to distinguish "this is a real placeholder" from "this is meta-discussion of the placeholder concept" or "this is a tracked-and-deferred TODO."

### Path-allowlist scan exemption

- **Spec-doc allowlist:** `.planning/**/*.md` path glob. Files matching the glob skip the prohibited-language scan **entirely**.
- Phase 404's own CONTEXT.md, ROADMAP.md, REQUIREMENTS.md, every `*-PLAN.md`, every `*-SUMMARY.md`, every `*-VERIFICATION.md`, every `*-RESEARCH.md` etc. exempt.
- Coarse but predictable; matches the project's structural convention that `.planning/` is the meta-prose layer where forbidden tokens carry their **literal meaning** (the word "v1" in a roadmap describes version 1; it is not a placeholder).

### Scope of the exemption (CRITICAL)

- **Scan exemption only.** The path-allowlist does **not** exempt files from `files_modified` enforcement (SRP-04) — Steps that write `.planning/` artifacts MUST still declare them in `files_modified`.
- **Layer order matters**: Layer 1 (`files_modified`) runs FIRST; Layer 3 (prohibited-language) is conditional on Layer 1 passing. Path-allowlist short-circuits Layer 3 only, never Layer 1.
- Cross-reference: PROOF-GATE.md Section 5 §Layer order — the four-layer stack is `files_modified → Phase 403 immutability → prohibited-language → gate-failing next-task block`. The path-allowlist short-circuit happens inside Layer 3's matching logic, never bypasses Layer 1.
- This means an agent cannot smuggle a write to `.planning/secrets.md` past the `files_modified` allowlist by relying on the scan exemption — the write is rejected at Layer 1 regardless of whether Layer 3 would have scanned it.

### Glob implementation pin

- **Glob syntax**: Python `fnmatch.fnmatch` (PEP-compliant; double-star `**` supported).
- v14 may pick `pathlib.PurePath.match` instead (similar semantics); spec accepts both.
- v14 implementation tip: pre-compile the glob to a regex at module load (`fnmatch.translate(PATH_ALLOWLIST_GLOB)`) for fast path checks. Pre-compilation avoids per-write fnmatch overhead.
- Path normalization: glob match runs against the realpath-resolved path (relative to repo root), not the agent-supplied raw string. This prevents `./planning/foo.md` from accidentally bypassing the glob via current-directory tricks.

### Tracking-issue exception (SRP-03)

A prohibited token passes the scan if-and-only-if its occurrence matches `EXCEPTION_RE` AND the captured ID resolves to a real reference. Re-render of `EXCEPTION_RE` (already in `<interfaces>` Excerpt B of the plan):

```python
EXCEPTION_RE = re.compile(r"\b(TODO|FIXME)\(([A-Z]+-\d+)\)")
# Captured ID must satisfy:
#   1. Match an entry in .planning/milestones/<MS>/REQUIREMENTS.md (look for `**ID-NN**` heading), OR
#   2. Match an entry in .planning/milestones/<MS>/slices/<N>/deferred-items.md (look for `- ID-NN:` row)
```

The exception is intentionally narrow: only `TODO` and `FIXME` (the two universally recognized tracking tokens) get the exception. `placeholder`, `simplified`, `v1`, `future` do NOT get the exception form — those tokens always trigger `scope_check`. If an agent needs to use those tokens in code legitimately, the path-allowlist (`.planning/**/*.md` for meta-prose) or a `TODO(ID)` wrapper is the only sanctioned path.

### Cross-check protocol

1. `PROHIBITED_RE` match found at `file_path`, `matched_offset`, `matched_line`.
2. Apply `EXCEPTION_RE` to the surrounding context (the entire matching line, plus a small window — recommended ±1 line for inline `TODO(REQ-ID)` usage).
3. If `EXCEPTION_RE` matches, extract the captured ID (group 2 — e.g., `SRP-04` from `TODO(SRP-04)`).
4. Cross-check the ID via pure-machine grep:
   - `grep -E '^\*\*<ID>\*\*' .planning/milestones/<MS>/REQUIREMENTS.md`
   - OR `grep -E '^- <ID>:' .planning/milestones/<MS>/slices/<N>/deferred-items.md`
5. If either grep returns >= 1 match → exception RESOLVED → scan passes for this occurrence (the `ScopeCheck` event is still emitted with `exception_resolved=True` for audit, but the write proceeds).
6. If both greps return 0 matches → exception UNRESOLVED → emit `state.step.scope_check` (tier=advisory) with the bullet `Unresolved tracking ID: <id>. Add to deferred-items.md or REQUIREMENTS.md first.`

### Path-confinement for the cross-check greps

The cross-check grep paths (REQUIREMENTS.md, deferred-items.md) MUST be realpath-resolved within the current milestone root + slice subdir. Any path traversal in the captured ID (e.g., `TODO(SLC-99/../../../secret)`) is rejected by `EXCEPTION_RE` itself — the regex only matches `[A-Z]+-\d+` — no slashes, no dots, no parent-dir tokens. Defense-in-depth: even if `EXCEPTION_RE` were widened in a future revision, the cross-check resolver still runs realpath-confinement against the milestone root, so an attacker cannot smuggle a traversal via the ID.

### Cross-check is pure-machine

Mirrors gsd-2's content-fingerprint-resync-gate pattern (declarative manifest + cross-check). No LLM-as-judge anywhere. PRF-04 compliance maintained. The grep cross-check returns a binary verdict (`resolved` | `unresolved`) — no fuzzy matching, no semantic similarity scoring, no LLM-augmented "did the agent mean this ID?" inference. Either the ID literal appears in the manifest at the expected anchor, or it doesn't.

## ScopeCheck Pydantic Event Payload (SRP-02)

Every prohibited-language match (with or without exception cross-check) emits a `state.step.scope_check` event. The Pydantic payload carries the audit-trail evidence: `file_path`, `matched_token`, `matched_offset`, `matched_line`, `exception_matched` / `exception_id` / `exception_resolved` flags, `session_id`. The event is emitted regardless of whether the scan passes or rejects, because the audit trail is more useful with full visibility than with selective emission.

### Pydantic class

Render verbatim from `404-CONTEXT.md` `<decisions>` Prohibited-language scan subsection:

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

Twelve fields total. Every field is required except `exception_id` (None when `exception_matched=False`). `extra="forbid"` rejects any extra fields at parse time — matches state's v1+v2 convention across all event payloads.

### Tier and harness action by exception state

| `exception_matched` | `exception_resolved` | Tier                                  | Harness action                                                                                              | Write decision |
| -------------------- | --------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------- |
| False                | (n/a)                 | advisory                              | Inject advisory naming the `matched_token` + remediation prompt ("add `TODO(REQ-ID)` reference")            | REJECT         |
| True                 | False                 | advisory                              | Inject advisory naming the unresolved `exception_id` ("Add `<id>` to REQUIREMENTS.md or deferred-items.md first") | REJECT         |
| True                 | True                  | (no event tier; pass-through)         | None (write proceeds; the `ScopeCheck` event is still emitted for audit)                                    | ALLOW          |

**Note**: in the third row (`exception_matched=True`, `exception_resolved=True`), the `ScopeCheck` event IS still emitted — but with tier-equivalent semantics "audit-only" (no advisory inject, no reject). v14 implementation may add an explicit `tier: Literal['advisory', 'audit']` field; this spec's current payload uses the `(exception_matched, exception_resolved)` tuple as the implicit tier signal. The implicit-tuple form keeps the schema minimal at v1; if observation shows the implicit form is hard to query downstream, v14 may promote to an explicit field.

### Bounded truncation

Same discipline as `GateStrike` and `ParalysisEvent` (see PROOF-GATE.md Section 7 §Bounded truncation): **content excerpts <= 2KB**. The `matched_offset` and `matched_line` are integers (no truncation); `matched_token` is by construction a single token from the `PROHIBITED_RE` corpus (max ~12 chars). If a future revision adds an `evidence_excerpt: str` field carrying the matched line content, that field will inherit the 2KB cap from the shared truncation utility (`formatFailureContext` analog).

### Event envelope

The `ScopeCheck` payload rides the standard `EventEnvelope` (see `<interfaces>` Excerpt C in the plan; canonical envelope in `src/state_core/schema.py`):

- `aggregate_type` = `"step"` — scope checks are scoped to the Step the Write/Edit was issued from.
- `aggregate_id` = `step_id` — the Step receiving the write attempt.
- `type` = `"state.step.scope_check"` — per the v40 EVENT-TAXONOMY.md naming convention; Plan 04 of this phase amends EVENT-TAXONOMY.md to register the new event types.
- `data` = serialized `ScopeCheck` instance (orjson `OPT_SORT_KEYS | OPT_NAIVE_UTC` per the v40 round-trip pin).
- `seq` / `id` — assigned by the event store at write time (not author-controlled).

### Event ordering semantics

A single Write/Edit may produce multiple `ScopeCheck` events when the content contains multiple prohibited tokens. Each match emits a distinct event with the same `triggered_at` (the request started at the same instant) but distinct `matched_offset` / `matched_line` / `matched_token` triples. The harness's tier decision is taken on the WORST verdict across all emitted events for the Write: any unresolved match → REJECT; all matches resolved (via path-allowlist short-circuit OR `EXCEPTION_RE` cross-check) → ALLOW.

This per-token granularity matches the audit-trail discipline of gsd-2's quality-enforcement evidence-emission pattern (`quality-enforcement.md` §7.1 EvidenceJSON v1): one row per check, never one rolled-up "any match" boolean. Replay can reconstruct the full set of matched tokens by filtering events on `(session_id, file_path, triggered_at)`.

### Per-token advisory wording (Claude's Discretion guidance)

Per `404-CONTEXT.md` `<decisions>` Claude's Discretion subsection, the exact wording of advisory messages on `scope_check` is recommendation-level (not locked). Recommended template:

```
Scope check triggered: prohibited token `<matched_token>` at <file_path>:<matched_line>.
Remediation:
  1. If this is a real placeholder, replace with the actual implementation.
  2. If this is tracked-and-deferred work, wrap as `TODO(<REQ-ID>)` and add a row
     to deferred-items.md (or reference an existing REQUIREMENTS.md entry).
  3. If this token carries its literal meaning in meta-prose, ensure the file
     is under `.planning/**/*.md` (scan-exempt; still subject to files_modified).
```

The template is suggestive — v14 implementation finalizes wording after EXEMPLAR-stepNPLAN.md gates show real agent failure modes.

### Why advisory-tier (not hard-block) on first match

`404-CONTEXT.md` `<deferred>` "`scope_check` tier-2 tool-block on first match (vs advisory-only)" was offered but rejected. Mirrors SRP-02's "Detection emits `scope_check` event and injects a justification request" — tier=advisory, not block. The agent gets a chance to justify (via tracking-issue reference) before the write is rejected. Hard-block on first match would force ceremony before legitimate spec docs ever pass.

In practice the effect is the same — the write is rejected when the advisory cannot be satisfied — but the framing differs: "you have an opportunity to justify" is friendlier than "you are blocked." The friendly framing matters because agents observed in gsd-2 logs frequently emit legitimate `TODO(REQ-ID)` references that just happen to land in a file the harness hadn't seen before; an advisory-first protocol lets the agent self-correct on the next attempt without escalating to a strike.

This is the philosophical distinction between SCOPE-PROHIBITION's regime and PROOF-GATE's regime: scope checks are a discipline guard (the agent should self-correct), while PROOF-GATE strikes are a correctness gate (the agent's claim of completion is mechanically refuted). Both can reject writes, but the strike-counter ladder (3→reinject→3→human-gate) is owned by PROOF-GATE, not by `scope_check`.

### Relationship to PROOF-GATE strike accrual

A `scope_check` event does NOT increment the PROOF-GATE strike counter (PRF-06). The strike counter accrues per `(task_id, check_id)` tuple at the **completion-claim boundary** (per `404-CONTEXT.md` `<decisions>` Strike-counter semantics: "A strike accrues if-and-only-if the agent signals 'task complete'... AND at least one evaluator returns `fail`"). A `scope_check` is a mid-task discipline event: it rejects the write inline, surfaces an advisory, and the agent retries. No completion claim is made; no strike accrues.

The independence mirrors `404-CONTEXT.md` `<decisions>` "APG vs PRF: independent counters" — counter independence is load-bearing across all three sibling specs. ANALYSIS-PARALYSIS-GUARD's paralysis counter, PROOF-GATE's strike counter, and SCOPE-PROHIBITION's per-event advisory chain are three distinct surfaces; they can each independently surface a `harness_intervention` (Phase 406 HRN-05), but they never share state. This is a literal application of gsd-2 `loop-control.md` §0 Correction 1 ("four distinct counters at four scopes... refuses to conflate distinct failure modes").

## files_modified Allowlist Enforcement (SRP-04)

SRP-04 is the spatial scope guard: it confines every Write/Edit to the set of paths the planner declared at plan-slice end. The list is locked at plan-slice end (Phase 403 PAP-03 mutability matrix), and the harness enforces against it via `tool.execute.before` Layer 1 — the first layer of the four-layer stack. Layer 1 runs before any other check; if a write target is not in the allowlist, the write is rejected immediately and no subsequent layer fires.

### tool.execute.before write-block enforcement

From `404-CONTEXT.md` `<decisions>` SRP-04 subsection (verbatim):

- **`tool.execute.before` write-block enforces the allowlist.** Inherits the diff-the-proposed-write mechanism from Phase 403 PAP-05; reuses the same hook handler.
- Behavior:
  - Compute the prospective target path (Edit operation in-memory; Write target directly).
  - If target NOT in `files_modified` (exact match OR glob match — Phase 403 allowed both) → reject the write with `scope_deviation` event.
  - If target IS in `files_modified` → fall through to PAP-05 immutability check, then to the prohibited-language scan, then allow.
- Cross-reference: PROOF-GATE.md Section 5 §Layer order — this is Layer 1 of the four-layer stack.

The Layer 1 rejection short-circuits the entire downstream pipeline: Layers 2 (immutability), 3 (prohibited-language), and 4 (next-task block from a failing gate) never run when Layer 1 rejects. This ordering is deliberate — `files_modified` is the coarsest, fastest check; running it first minimizes wasted work on out-of-scope writes.

### Glob-match implementation

- **Glob syntax**: same as the path-allowlist (Section "Path-Allowlist Scan Exemption"): Python `fnmatch.fnmatch` with `**` support; v14 may pick `pathlib.PurePath.match`.
- **Multi-entry semantics**: `files_modified` is a list; a target matches if ANY list entry matches (exact or glob).
- **Pre-resolution**: all entries are realpath-resolved at plan-slice validation stage; resolution happens once, cached for the Step's lifetime.
- **Exact-vs-glob detection**: an entry is treated as a glob if it contains any of `*`, `?`, `[`; otherwise it is an exact-path match (string-equal after realpath normalization). The detection is pre-computed at module load (per-entry tag) so per-write checks are O(1) per entry.

### files_modified immutability

From `404-CONTEXT.md` `<decisions>` SRP-04 subsection (verbatim):

- **`files_modified` is locked at end of plan-slice** (Phase 403 PAP-03 mutability matrix; cross-reference: `PLAN-AS-PROMPT.md` §Mutability Matrix).
- **The `scope_deviation_request` flow does NOT mutate the field** — overrides are event-scoped one-shot allowlists (Section "scope_deviation_request MCP Tool Flow" below). The on-disk `stepNPLAN.md` `files_modified` list is read-only at runtime.
- Replan re-entry from `split_recommendation` (Section "request_step_split MCP Tool (SRP-05)") re-authors `files_modified` for the new Steps; the old Step's `files_modified` is preserved in the audit log (`state.step.plan_authored` event per Phase 403 STEP-EVENTS.md).

The "never-mutate-at-runtime" rule is load-bearing: replay correctness depends on `files_modified` being an immutable contract for each Step. If runtime mutation were allowed, a replay would have to reconstruct the mutation history before evaluating any later write decision — which would break event-replay determinism (the cardinal rule in PROJECT.md). Event-scoped one-shot allowlists keep the contract intact: the underlying file never changes; the override is a transient permit that lives only in event history.

### Pydantic scope_deviation event payload

Every Layer 1 rejection emits `state.step.scope_deviation`:

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

Emitted on every Layer 1 rejection; the agent receives the `reject_reason` as the `tool.execute.before` hook's response. The agent's next action is typically a `scope_deviation_request` MCP call (next section) OR a `request_step_split` MCP call (Section "request_step_split MCP Tool (SRP-05)") OR a different write within the allowlist.

The `files_modified_at_time` snapshot captures the allowlist state at the rejection instant for forensic clarity — if a one-shot allowlist entry was active but didn't apply (wrong path), the snapshot shows what WAS active versus what the write attempted. This is the audit-trail analog of gsd-2's `EvidenceJSON` evidence-with-context discipline (`quality-enforcement.md` §7.1).

## scope_deviation_request MCP Tool Flow

The `scope_deviation_request` MCP tool is the agent's sanctioned channel for requesting a write outside the current `files_modified` allowlist. It is a request, not a directive — the harness routes it through a `checkpoint:decision` (per Phase 403 task-type behavior + Phase 405 DEV-03 territory) and writes either an approve or reject `ScopeDeviationResolved` event in response. Approved deviations are scoped to one tool invocation; the underlying `files_modified` list is never mutated.

### Use case

When the agent legitimately needs to edit a file outside `files_modified` (e.g., discovers a missing import in a sibling file during execution), the agent emits a `scope_deviation_request` MCP tool call. Typical scenarios:

- A bug fix requires a touch in a sibling module that the planner didn't anticipate.
- A test file's location was guessed wrong during planning; the agent needs to update one extra path.
- An import-cycle break requires moving a small declaration to a neutral location.

Scenarios that should NOT use `scope_deviation_request`:

- The work is genuinely larger than one Step → use `request_step_split` (Section "request_step_split MCP Tool (SRP-05)").
- The write is a stub or simplification → that's exactly what SRP-02/SRP-03 are guarding against; fix the underlying scope decision instead.

### Pydantic MCP tool signature + payload

From `404-CONTEXT.md` `<decisions>` SRP-04 subsection (verbatim):

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

The MCP tool synchronously returns the resolution payload to the calling agent's session. Synchronous return matches the `complete_task` / `complete_slice` / `validate_milestone` pattern from gsd-2's `tools/complete-*.ts` family — agent intent is signaled by tool call, agent receives the harness verdict in-band, no out-of-band SSE listening required.

### Resolution event + checkpoint:decision flow

From `404-CONTEXT.md`:

- The request surfaces as a `checkpoint:decision` under `--tiered` (per Phase 403 task-type behavior + Phase 405 DEV-03 territory).
- Resolution emits `scope_deviation_resolved` with `resolution: approve | reject`.

Pydantic class:

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

The `request_event_id` cross-link enables replay to walk forward from each request to its resolution deterministically. The `resolver` field distinguishes human vs harness-auto decisions for the post-hoc audit ("which deviations did humans actually look at?").

### One-shot allowlist semantic

From `404-CONTEXT.md`:

- **Approved deviations write a temporary one-shot allowlist entry.**
- Semantics:
  - The allowlist entry is keyed by `(session_id, task_id, requested_path)`.
  - The entry is consumed by the NEXT `tool.execute.before` invocation targeting the path.
  - The entry is one-shot: after consumption, subsequent writes to the same path require a fresh request.
- **The request and resolution events are part of the audit chain.**
- **`files_modified` itself is NEVER mutated at runtime** — the override is event-scoped.

The one-shot semantic mirrors gsd-2's transient permission grants (`tool-system.md` §5 advisory-not-security framing) — each deviation is a discrete event, not a permanent capability widening. If the agent needs to write to the same out-of-scope path twice, it must request twice; each request is independently audited.

### Path-confinement at request boundary

- The MCP tool handler MUST realpath-resolve `requested_path` within repo root + slice subdir BEFORE surfacing the `checkpoint:decision`.
- Path-traversal-resolved targets outside repo root are rejected at MCP-tool-handler boundary; an automatic `ScopeDeviationResolved` event is emitted with `resolution='reject'`, `resolver='harness_auto'`, `resolution_justification='path traversal outside repo root'`.
- No human decision is surfaced for traversal-rejected requests.

The auto-reject path means an agent attempting `requested_path='../../../etc/passwd'` never reaches a human gate — the MCP handler resolves the path, detects it falls outside the repo, and emits the rejection event in-band. This is defense-in-depth alongside the EXCEPTION_RE regex's own slash/dot rejection (Section "Path-Allowlist Scan Exemption + Tracking-Issue Exception (SRP-03)" §Path-confinement) — even if one layer were misconfigured, the other still catches.

### Audit chain

- Audit chain for one approve cycle: `ScopeDeviationRequest` event → `checkpoint:decision` surfaces via opencode `question` tool → human approves → `ScopeDeviationResolved(resolution='approve')` event → one-shot allowlist entry written → next Write/Edit consumes the entry → `tool.execute.before` Layer 1 falls through → Layers 2-4 still run normally → write allowed.
- Audit chain for one reject cycle: `ScopeDeviationRequest` event → `checkpoint:decision` surfaces → human rejects → `ScopeDeviationResolved(resolution='reject', resolution_justification=<reason>)` event → agent receives rejection as the MCP tool's return value → agent typically replans OR calls `request_step_split`.

Replay walks the chain by following `request_event_id` cross-links. Forensics queries can answer "show me all approved deviations in this Slice" by joining `ScopeDeviationRequest` events to their `ScopeDeviationResolved` peers and filtering on `resolution='approve'`.

## request_step_split MCP Tool (SRP-05)

`request_step_split` is the canonical channel for the agent to signal that the current Step is too large to complete within its `must_haves` contract. The harness responds by recording the recommendation as an event, taking a worktree snapshot, transitioning the Slice to `pending_replan`, and exiting `run-slice` cleanly. The replan re-enters the research-slice planning stage to break the oversized Step into smaller Steps. No `must_haves` are reauthored on the original Step — they remain in the audit log; the new Steps get fresh `must_haves` blocks.

### Canonical trigger

From `404-CONTEXT.md` `<decisions>` SRP-05 subsection (verbatim):

- **Explicit MCP tool `request_step_split` is the canonical trigger.**
- **No NL keyword detection; no heuristic auto-split.** The agent must call the MCP tool explicitly.
- Mirrors gsd-2's explicit `complete_task` / `complete_slice` / `validate_milestone` MCP tool-call boundary pattern (`tools/complete-task.ts`, `tools/complete-slice.ts`, `tools/validate-milestone.ts`) — agent intent is signaled by tool call, not by NL output scan.

The tool-call-boundary discipline is non-negotiable: any NL-keyword heuristic that auto-detects "this is too much for one Step" pattern would either false-positive (legitimately hard checks look the same as oversized scopes from the harness's view) or false-negative (an agent that doesn't say the right words gets stuck). Explicit tool call eliminates both failure modes.

### Pydantic MCP tool signature + payload

From `404-CONTEXT.md` `<decisions>` SRP-05 subsection (verbatim):

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

Seven fields total. `reason` is bounded at 2KB (matches the `agent_response_summary` truncation in `GateStrike` and `ParalysisEvent` — gsd-2 convention). `partial_artifacts` is an open list of paths; the planner is expected to keep this realistic (a Step that produced 50 partial artifacts is itself an audit signal that the original sizing was severely off).

### Harness behavior (4-step sequence)

From `404-CONTEXT.md` `<decisions>` SRP-05 subsection (verbatim):

1. **Emit `split_recommendation` event** with the payload above (rides `state.slice.split_recommendation` event-type per the v40 EventEnvelope convention; `aggregate_id` is the `slice_id`).
2. **Take a worktree snapshot** (mirrors Phase 402 `compaction.snapshot_taken` plumbing): records `slice_id`, `step_id`, `task_id`, worktree commit SHA, partial artifact paths.
3. **Transition the Slice state to `pending_replan`** (run-slice terminal state — see SLICE-CYCLE.md).
4. **Exit run-slice cleanly.** Partial commits stay on the worktree branch; the replan inherits them.

The aggregate-type for the event is `slice` (not `step`) because the Slice is the entity whose state is transitioning. The replan re-enters the Slice's research/planning stage; the original Step ceases to be the active execution unit.

### Replan re-entry

From `404-CONTEXT.md`:

- The replan re-enters research-slice / planning stage, which reads the `split_recommendation` event + the worktree snapshot and produces NEW `stepNPLAN.md` files breaking the over-scoped Step into smaller Steps.
- **PAP-03 locks survive replan when `step_id` is unchanged** (Phase 403).
- **A split necessarily changes `step_id`s**, so `must_haves` for the new Steps are re-authored fresh.

The replan path consumes both the event payload (the agent's stated reason) AND the worktree snapshot (the actual partial-state on disk). The planner uses both: the reason informs the breakdown rationale; the snapshot informs which artifacts already exist and can be referenced by the new Steps' `must_haves.artifacts` lists.

### Returned value

- The MCP tool returns the populated `SplitRecommendation` Pydantic model to the agent's session so the agent's last log statement is auditable (per `404-CONTEXT.md` Claude's Discretion — recommended over fire-and-exit).
- After the return, the harness exits run-slice cleanly; the agent's session continues only until the run-slice exit signal propagates.

The synchronous return shape mirrors `scope_deviation_request` — agent calls, agent receives. The harness then begins shutdown asynchronously, but the agent's last visible action is the structured tool-return.

### Abuse vector mitigation

- Over-frequent splits in the milestone trigger a Rule 4 (architectural) human gate (Phase 405 DEV-04).
- v14 emits `split_recommendation_telemetry` rolled up at Slice close for human review (frequency, reasons, partial_artifact patterns).

The telemetry is the long-tail mitigation for the abuse pattern. A single `request_step_split` is legitimate; ten splits in a milestone signals something systematic (the planner is consistently under-sizing Steps, or the agent is using splits as a way to avoid debugging). Phase 405 DEV-04 is the architectural escalation surface for that signal.

### NL keyword detection rejected

- NL keyword detection for split-trigger was offered and rejected. Removes agent intent; risks false positives on legitimately hard checks.
- Implicit `split_recommendation` from N-paralysis+N-strike pattern ALSO rejected (mirrors `404-CONTEXT.md` `<deferred>`). The agent calling `request_step_split` is the canonical signal.

Both rejections share the same underlying principle: the harness should not infer agent intent from indirect signals. Counter-correlation (N paralyses + M strikes = split) was tempting because it would auto-rescue stuck agents, but it confuses two distinct failure modes (paralysis is "agent doesn't know what to do" vs split is "scope is too large"). Conflating them would risk auto-triggering splits when a small refocus would suffice.

## deferred-items.md Artifact (SRP-06)

The `deferred-items.md` artifact is the per-Slice register of out-of-scope findings. Items raised during a Slice's execution that fall outside the Slice's scope are logged here, not silently dropped and not retroactively scoped in. The file is the structural memory of "we noticed this; we tracked it; we will route it correctly later."

### Artifact location and shape

- **File path:** `slices/N-name/deferred-items.md` (per-Slice; rooted in the slice folder).
- **Format:** GFM-flavored markdown with a single H1 + a table + appended bullet rows.

### Canonical template

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

### Row append rule

- **Auto-append on `scope_check` events with `exception_matched=False`**: when the prohibited-language scanner emits a ScopeCheck with no resolved exception, the harness's deferred-items writer projector subscribes and appends a row with auto-generated ID (`DEF-<NN>` sequential within the Slice).
- **Auto-append on `scope_deviation_request` events with `resolution='reject'`**: a rejected deviation that the human flagged as "real but out-of-scope" (`resolution_justification` contains the tag `[defer]`) also triggers row append.
- **Manual append**: humans MAY append rows directly (e.g., during `checkpoint:decision` resolution); the file is mutable post-execute-slice start (NOT immutable like `stepNPLAN.md`).

The projector subscribes to both event types and applies dedup keyed by `(source_task, description-prefix-32-chars)` so retries don't produce duplicate rows. ID assignment is monotonically increasing per Slice; gaps are not reused (a deleted-by-human row keeps its ID slot empty).

### Status vocabulary

- `open` — newly raised; not yet routed.
- `scheduled-next-slice` — promoted to the next Slice's CONTEXT.md `<deferred>` block.
- `scheduled-future-milestone` — promoted to the milestone-level v2 REQUIREMENTS section.
- `rejected` — reviewed and determined out-of-product-scope (not v1, not v2).
- `resolved-in-slice` — addressed within the current Slice (e.g., a TODO turned into actual code with EXCEPTION_RE-satisfied tracking).

The five statuses cover the full lifecycle: open → triaged → routed (one of three terminal destinations) OR rejected OR resolved-in-place. Transitions are recorded by the human or the harness's auto-promotion logic (v14 implementation).

### Surface in Slice SUMMARY.md

- The Slice SUMMARY.md (Phase 402 SLICE-CYCLE.md verify-slice stage output) MUST include a `## Deferred Items` section with a copy of the deferred-items.md table (or a `## Deferred Items` section stating "No deferred items raised during this Slice." if the table is empty).
- v15 Build Core Commands implements the SUMMARY-generation step that pulls from `deferred-items.md`.

The SUMMARY-surface ensures deferred items are visible at Slice close, not hidden in a per-Slice file that closes-then-orphans. Promotion decisions (which deferred items become next-Slice context, which become next-milestone requirements) happen at the SUMMARY review boundary.

### ARTIFACT-CATALOG.md amendment

- **v40 ARTIFACT-CATALOG.md WILL receive a `## v41 Amendment` block** (Plan 04 of this phase) registering `deferred-items.md` as a per-Slice artifact in the canonical Slice folder layout.

The amendment is the structural counterpart to the spec text here: ARTIFACT-CATALOG.md gives v14 implementers a canonical "this file goes here in the Slice folder" reference; this spec defines its content shape and append-rules.

## Cross-references

- **Sibling spec — proof gate:** `PROOF-GATE.md` Section 5 four-layer `tool.execute.before` stack: Layer 1 (`files_modified` — owned by this spec SRP-04), Layer 2 (Phase 403 PAP-05 immutability), Layer 3 (prohibited-language — owned by this spec SRP-02), Layer 4 (gate-failing next-task block — owned by PROOF-GATE.md PRF-07). The composition is the canonical enforcement pipeline; this spec owns 50% of it.
- **Sibling spec — paralysis:** `ANALYSIS-PARALYSIS-GUARD.md` Section 7 §APG-vs-PRF — paralysis counter independent from scope events; both feed `harness_intervention` via Phase 406 HRN-05.
- **Phase 403 carry-forward — format:** `STEP-PLAN-FORMAT.md` §Frontmatter Schema (STP-02) provides the `files_modified` field this spec enforces against; §`<task>` Sub-tag Specification (STP-04) provides the `<done>` field this spec cross-checks; §Mutability Matrix forward-pointer to `PLAN-AS-PROMPT.md` confirms `files_modified` is locked.
- **Phase 403 carry-forward — mutability:** `PLAN-AS-PROMPT.md` §Mutability Matrix (PAP-03) locks `files_modified`; §6 (PAP-05) is Layer 2 below SRP-04 Layer 1 in the `tool.execute.before` stack.
- **Phase 402 carry-forward — compaction snapshot:** `CONTEXT-PROTOCOL.md` §Compaction (CTX-05/06) is the source of the worktree-snapshot plumbing that `request_step_split` reuses; the `SplitRecommendation` does NOT cross-link `snapshot_event_id` by default (the snapshot is a side effect of run-slice exit, not a strike-replay analog), but v14 implementation MAY add the cross-link if EXEMPLAR observation warrants.
- **Phase 402 carry-forward — Slice cycle:** `SLICE-CYCLE.md` defines the `pending_replan` run-slice terminal state that SRP-05 transitions to; the replan re-entry path is part of the plan-slice multi-stage internal pipeline (SLC-03).
- **v40 baseline — events:** `EVENT-TAXONOMY.md` naming convention `state.{tier}.{action}`; this spec adds `state.step.scope_check`, `state.step.scope_deviation`, `state.step.scope_deviation_request`, `state.step.scope_deviation_resolved`, `state.slice.split_recommendation`. Plan 04 of this phase appends the `## v41 Amendment` block registering these.
- **v40 baseline — artifacts:** `ARTIFACT-CATALOG.md` will receive Plan 04 amendment registering `deferred-items.md` as a per-Slice artifact.
- **gsd-2 lineage:** `quality-enforcement.md` — explicit MCP tool-call boundary pattern (`complete_task`/`complete_slice`/`validate_milestone`) informs `request_step_split` shape; `file-tracking.md:445` — word-boundary regex pattern informs `PROHIBITED_RE` shape; `file-tracking.md §branch-patterns` — single-module pattern informs `state_build/harness/scope/`; `tool-system.md:851` — no-allowlist/denylist framing informs the advisory-not-security note in SCOPE-PROHIBITION (lighter than PROOF-GATE strikes, but stronger than ANALYSIS-PARALYSIS advisories — scope is a security-AND-quality boundary, not just advisory).
- **Phase 405 forward:** `DEV-03` (auto-fix blocking issues with `checkpoint:decision` escalation) is the resolution path for `scope_deviation_request` under `--tiered`; `DEV-04` (architectural always-human-gate) is the resolution path for `split_recommendation` when frequency exceeds milestone threshold; `DEV-05` tiered autonomy table specifies the `--full-yolo` auto-approval policy (NOT owned by this spec).
- **Phase 406 forward:** `harness_intervention` (HRN-05) umbrella event aggregates `scope_check` + `scope_deviation_request` + `split_recommendation`; the 4-tier intervention ladder (HRN-04) cites this spec for tier-1 (advisory inject from ScopeCheck tier=advisory) + tier-2 (tool-block from Layer 1 + Layer 3 of the stack) + tier-4 forward-reference for `pending_replan` transition triggered by `request_step_split`.

v14 Build Kernel implements `state_build/harness/scope/patterns.py` (single module with `PROHIBITED_RE` + `EXCEPTION_RE` + `PATH_ALLOWLIST_GLOB`) + the `files_modified` allowlist checker + the `EXCEPTION_RE` cross-check resolver + the `scope_deviation_request` MCP handler + the `request_step_split` MCP handler + the worktree-snapshot reuse + the `deferred-items.md` writer projector. v15 Build Core Commands implements the planner-validation `<acceptance_criteria>` annotation check that ties to SRP-01 + the SUMMARY-generation step that pulls from `deferred-items.md` + the replan re-entry path that consumes `split_recommendation` events + the worktree snapshot. Phase 405 owns the auto-approval policy for `scope_deviation_request` under `--full-yolo` (DEV-05). Phase 406 cites this spec for tier-1 (advisory) + tier-2 (tool-block) of the 4-tier intervention ladder.
