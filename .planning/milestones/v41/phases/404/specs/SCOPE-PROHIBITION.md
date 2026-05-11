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
