# Deviation Rules & Tiered Autonomy (Canonical, v41)

> **Phase:** 405
> **Status:** Canonical (v41)
> **Requirements covered:** DEV-01..DEV-07
> **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
> **Sibling specs:** SUBAGENT-MANAGEMENT.md (subagent typed-spawn + spot-check + crash recovery — Phase 405 Plan 02-03).
> **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Past-phase `STATE-*` trailer references (note: any `S-D-*` legacy mentions inherited from gsd-2 design heritage are deferred-rename items handled in `<deferred>`).
> **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.

The harness governs deviation from a Step's locked PLAN via a 4-rule framework. Each rule has a category (bug fix / missing critical functionality / blocking issue / architectural change), a `max-attempts` cap, a commit-prefix convention (`fix:` / `feat:` / `refactor:` / etc. per gsd-2 `COMMIT_TYPE_RULES` keyword inference), and an escalation path. The agent declares the rule via the `log_deviation` MCP tool; the daemon cross-validates against pure-machine signals (`issue_signature` recomputation, the arch-pattern allowlist, `scope_deviation_request` correlation from Phase 404 SRP-04, and per-tuple cap check). Rule 4 (architectural) is structurally always-human-gate — no autonomy mode can bypass. Tiered autonomy (`--tiered` default / `--full-yolo` / `--conservative`) gates the other rule outcomes; per-Slice autonomy override is allowed via Slice frontmatter (DEV-06). Three-counter independence (APG / PRF / DEV) is preserved per gsd-2 `loop-control.md` §0 Correction 1 — the deviation chain is the third independent counter alongside Phase 404's `paralysis_event` (APG) and `gate_strike` (PRF) chains.

---

## The Four Rules

The four rules partition all deviation classes the harness recognises. They are mutually exclusive at any given `(task_id, issue_signature)` tuple — an issue belongs to exactly one rule at the time of declaration, and the daemon's cross-validation flow (Section 4) decides the final `rule_id` after correcting agent mis-classification. Per-rule semantics follow.

## Rule 1: Auto-fix Bugs (DEV-01)

- **Category:** wrong queries, logic errors, type errors, null-pointer dereference, off-by-one boundary errors, off-by-one indexing errors, undefined-behavior dispatches, incorrect predicate inversion, sign-flip arithmetic errors, branch-coverage holes that produce wrong output.
- **max-attempts: 3** (cap enforced per `(task_id, rule_id=1, issue_signature)` tuple — different `issue_signature` values do not poison each other).
- **Commit-prefix convention:** `fix: <description>` per gsd-2 `COMMIT_TYPE_RULES` (`git-service.ts:616`); trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 1`, `STATE-DeviationAttempt: K` where K ∈ {1,2,3}.
- **Escalation path:** after 3 failed attempts on the same tuple, the daemon emits `state.step.deviation_cap_exceeded` and force-promotes the chain to Rule 4. Rationale (encoded as cross-validation step 5 verdict): persistent bug-fix failures on the same `issue_signature` indicate a structural / architectural problem requiring human resolution, not another isolated bug-fix attempt. The 4th attempt's Rule 4 promotion is a STRUCTURAL invariant — no autonomy mode bypasses.

## Rule 2: Auto-add Critical Functionality (DEV-02)

- **Category:** missing error handling, missing input validation, missing null checks, missing auth on protected routes, missing DB indexes for hot-path queries, missing rate-limit decorators, missing CSRF guards, missing schema-validation calls before persistence, missing audit-log emissions.
- **max-attempts: 3** (cap enforced per `(task_id, rule_id=2, issue_signature)` tuple).
- **Commit-prefix convention:** `feat: <description>` if adding a new capability (new route handler, new validator); `fix: <description>` if patching a missed safety check (gsd-2 keyword inference applies — `infer_commit_type` decides from the diff text and modified file paths); trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 2`, `STATE-DeviationAttempt: K`.
- **Escalation path:** documented in `stepNSUMMARY.md` `## Deviations` section (auto-rendered by the projector — Section 10). After 3 failed attempts: same `state.step.deviation_cap_exceeded` -> Rule 4 promotion as Rule 1. The escalation justification: a critical-functionality addition that fails 3 times is no longer a localized correctness fix; it is structural.

## Rule 3: Auto-fix Blocking Issues (DEV-03)

- **Category:** missing dependency at runtime (`ImportError`), wrong types in an upstream contract (mypy / pyright failure that blocks the test step), broken imports after a refactor, build config errors (`pyproject.toml` malformed but not a NEW dep), missing environment variable, CI lint configuration drift, formatter (Ruff) parse errors.
- **max-attempts: 3** (cap enforced per `(task_id, rule_id=3, issue_signature)` tuple).
- **Commit-prefix convention:** `fix: <description>` (typically — most blocking issues are mechanical fixes); `chore: <description>` for tooling-only adjustments (gsd-2 `COMMIT_TYPE_RULES` decides per the keyword table). Trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 3`, `STATE-DeviationAttempt: K`.
- **Escalation path:** after 3 failed attempts -> `checkpoint:decision` (Phase 403 task-type) presenting the resolution options to the human via opencode `question` tool. **Diverges from Rules 1-2** (which promote to Rule 4): blocking issues are often choice-shaped (which dep to pin? roll back the import? branch on the upstream contract?) rather than architectural-shaped. `checkpoint:decision` lets the human pick from a curated option set without forcing Rule 4's pros/cons-table machinery.

## Rule 4: Architectural Changes (DEV-04)

- **Category:** new DB table (not a column addition), major schema change (e.g., renaming a primary key, splitting a table), switching frameworks (Pydantic v2 -> v3, FastAPI -> Starlette), new infrastructure (CDN, queue, cache, sidecar service), introducing a new external SaaS dependency, adding a new top-level package under `src/state_*/`, registering a new MCP tool, adding a new dep to `pyproject.toml`.
- **max-attempts: 1** (Rule 4 is single-shot: render `question` -> resolution arrives -> attempt complete; no retry loop).
- **Commit-prefix convention:** typically `feat: <description>` (architectural changes most commonly add capability); occasionally `refactor: <description>` for pure structural reshuffles. Trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 4`, `STATE-DeviationAttempt: 1`.
- **Escalation path:** ALWAYS human gate via opencode `question` tool with a pros/cons table assembled from the agent's `alternatives: list[Rule4Option]` payload. Never auto-approved, even under `--full-yolo`. The `log_deviation(rule_id=4, ...)` MCP handler synchronously renders the question; there is no autonomy short-circuit branch in the daemon's middleware. The `alternatives` payload is REQUIRED (Pydantic-validated; at least 2 options; exactly one `recommended=True`).

**Rule-4 always-stop is STRUCTURAL, not policy.** The implementation guarantee: there is no `if mode == 'full-yolo' bypass` code path. The `log_deviation(rule_id=4)` MCP handler unconditionally renders opencode `question`. This pattern mirrors gsd-2's MCP-tool-call-as-canonical-agent-intent-signal (`tool-system.md` §5); state extends with strict cross-validation. The absence of an autonomy bypass branch in `state_build/deviation/log_deviation.py` is the structural enforcement — code review and CI grep both target this absence as a non-negotiable invariant.

### Inter-rule promotion paths (escalation graph)

The escalation graph between the four rules is:

- Rule 1 -> Rule 4 (on cap exceeded; cross-validation step 5).
- Rule 1 -> Rule 4 (immediate; cross-validation step 3 arch-pattern match).
- Rule 2 -> Rule 4 (on cap exceeded; cross-validation step 5).
- Rule 2 -> Rule 4 (immediate; cross-validation step 3 arch-pattern match).
- Rule 3 -> `checkpoint:decision` (on cap exceeded; cross-validation step 5). Note: this is NOT a Rule 4 promotion — Rule 3's escalation path diverges intentionally because blocking issues are choice-shaped rather than architectural-shaped.
- Rule 4 -> terminal (never escalates to anything else; the human gate is the terminal resolution).

The escalation graph is encoded in the daemon's `escalate_chain(rule_id, count, signature) -> EscalationVerdict` helper in `state_build/deviation/escalation.py`. The helper returns one of: `EscalationVerdict.continue_chain` (within cap), `EscalationVerdict.promote_to_rule_4`, `EscalationVerdict.fire_checkpoint_decision`, `EscalationVerdict.terminal_human_gate`. The verdict drives the daemon's downstream event emissions (`deviation_cap_exceeded` -> checkpoint render OR Rule 4 question render).

### Rule-distinguishing examples

To anchor the rule definitions concretely, examples of correct classification:

- `KeyError: 'user_id'` in a request handler that should have validated input -> **Rule 2** (missing input validation).
- `TypeError: NoneType has no attribute 'serialize'` after a refactor that introduced a `None` return path -> **Rule 1** (logic error: missing None-guard).
- `ImportError: cannot import name 'orjson_loads' from 'state_core.serde'` after deleting a helper -> **Rule 3** (blocking; broken import).
- Adding `redis>=5.0` to `pyproject.toml` to introduce caching layer -> **Rule 4** (new dependency; arch-pattern allowlist match).
- Creating `src/state_telemetry/__init__.py` to add a new top-level package -> **Rule 4** (new top-level package init; arch-pattern allowlist match).
- Bumping `pydantic>=2.10` to `pydantic>=2.13` -> **Rule 3** (BUMP, not ADD; routine dep update).

---

## log_deviation MCP Tool

### Signature (Pydantic-typed)

Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Deviation classification (DEV-01..04 expanded)" subsection:

```python
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict

def log_deviation(
    rule_id: Literal[1, 2, 3, 4],
    issue_signature: str,                                # caller computes; daemon recomputes for verification
    classification_source: Literal[
        "agent_declared",                                # agent self-classified
        "harness_promoted",                              # auto-promoted by file-path heuristic
        "arch_pattern_match",                            # forced Rule 4 by allowlist match
    ],
    justification: str,                                  # ≤1KB agent rationale
    error_excerpt: str,                                  # ≤2KB; gsd-2 formatFailureContext truncation discipline
    alternatives: list["Rule4Option"] | None = None,    # REQUIRED for rule_id=4; otherwise None
) -> "DeviationLogResult": ...

class Rule4Option(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str                                            # short identifier shown in opencode question
    pros: str                                            # ≤512 chars
    cons: str                                            # ≤512 chars
    recommended: bool                                    # exactly one option in the list should be True

class DeviationLogResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deviation_event_id: str
    attempt_number: int                                  # 1..3 for rules 1-3; always 1 for rule 4
    cap_exceeded: bool                                   # True when this attempt is the 4th — auto-escalation triggered
    classification_accepted: bool                        # False if cross-validation rejected the declared rule_id
    rejection_reason: str | None                         # set when classification_accepted is False
```

### MCP tool registration

The tool is registered under the `state-build` MCP server at module path `state_build/deviation/log_deviation.py`. The MCP tool name is the literal string `log_deviation`. The handler is invoked from the daemon's middleware (single source of truth — daemon decides). The handler returns `DeviationLogResult` synchronously. The MCP tool surface is exposed only when the active mode is `build` (or `both`); never registered under the `state-teach` MCP server. Mode-isolation is enforced at the MCP server registration step, not at the tool-call step — the tool is simply not visible to teach-mode sessions.

### Caller responsibilities (agent side)

- **Compute `issue_signature`** via the SHA-256 16-char hex function defined in Section 7; pass the value as input to `log_deviation`. The daemon recomputes for verification (cross-validation step 1) and rejects on disagreement.
- **Set `classification_source = "agent_declared"`** for self-classified deviations. The daemon MAY override to `"harness_promoted"` (cross-validation step 3) or `"arch_pattern_match"` (step 4) before event emit. The final value on the persisted `Deviation` event is server-recomputed.
- **For `rule_id == 4`:** supply at least 2 `Rule4Option` entries with exactly one `recommended=True`. The Pydantic root validator on the inbound payload enforces this; the daemon also re-validates server-side (defense-in-depth). Pros/cons strings ≤512 chars each (Pydantic-validated).
- **Truncation discipline:** `justification` ≤ 1KB, `error_excerpt` ≤ 2KB (gsd-2 `formatFailureContext` truncation pattern; mirrors Phase 404's bounded-truncation 2KB/10KB discipline). Larger inputs are rejected at Pydantic parse time; the agent must truncate caller-side before invocation.

### Return shape

`DeviationLogResult` has 5 fields with the following semantics:

- `deviation_event_id`: ULID; the primary key of the just-emitted `state.step.deviation_logged` event. The agent SHOULD record this ID in the subsequent `commit_sha`-resolution event (Section 9) so the projector (Section 10) can join the resolution to the original deviation row.
- `attempt_number`: 1..3 for Rules 1-3 (computed by the daemon from the per-tuple counter +1); always 1 for Rule 4 (single-shot). Server-recomputed; agent-emitted value is ignored.
- `cap_exceeded`: `True` when this attempt is the 4th on the same `(task_id, rule_id, issue_signature)` tuple — auto-escalation already triggered server-side (a `state.step.deviation_cap_exceeded` event has been emitted before `log_deviation` returns).
- `classification_accepted`: `False` if cross-validation rejected the declared `rule_id` (the rejection event has already been emitted; the agent must re-call `log_deviation` with corrected `rule_id` + payload).
- `rejection_reason`: set when `classification_accepted` is `False`. One of: `"issue_signature_mismatch"`, `"rule_4_alternatives_missing"`, `"rule_4_recommended_invalid"`, `"arch_pattern_promotion_required"`, `"scope_deviation_correlation_promoted"`. The agent SHOULD use this value to construct the corrected re-call payload — for example, `"arch_pattern_promotion_required"` indicates that the agent must escalate to `rule_id=4` and supply an `alternatives` list before re-calling.

### Idempotency and re-call semantics

`log_deviation` is NOT idempotent at the (task_id, issue_signature) tuple — every accepted call increments `attempt_number` for Rules 1-3. The agent SHOULD NOT re-call `log_deviation` to "report progress" on an in-flight attempt; instead, the agent calls `log_deviation` once per discrete attempt at fixing the issue, and the resolution event (Section 9) marks the attempt's outcome.

For rejected calls (`classification_accepted=False`), the agent's corrective re-call is treated as a fresh attempt for cap-counting purposes only if the previous rejected call's `rule_id` was within {1, 2, 3}. Rejection on `rule_id=4` cross-validation (steps 2) does not increment the cap counter because the call never reached the success path; the agent's corrective re-call replaces the rejected one for audit purposes (via `agent_response_summary` cross-link).

### Worked example: agent / daemon round-trip

A worked example of the agent-daemon interaction for Rule 1 / attempt 2:

1. Agent runs failing test, captures `pytest_failure` with file/line/token.
2. Agent computes `issue_signature` via `compute_issue_signature(ErrorKind.pytest_failure, "tests/state_core/test_eventstore.py", 87, "assert_event_emitted")`.
3. Agent calls `log_deviation(rule_id=1, issue_signature=..., classification_source="agent_declared", justification="...", error_excerpt="..."[:2048])`.
4. Daemon runs cross-validation steps 1-5 (all pass).
5. Daemon emits `state.step.deviation_logged` with `attempt_number=2`, `resolution="pending"`.
6. Daemon returns `DeviationLogResult(deviation_event_id="...", attempt_number=2, cap_exceeded=False, classification_accepted=True, rejection_reason=None)`.
7. Agent attempts the fix, commits with trailers including `STATE-DeviationRule: 1`, `STATE-DeviationAttempt: 2`.
8. Agent (or daemon's post-commit hook) emits `state.step.deviation_resolution_recorded` to mark `resolution="auto_fix_succeeded"` and link `commit_sha`.

---

## Harness Cross-Validation Flow

Post-call (before event emit), the daemon runs a 5-step pure-machine validation against the proposed deviation. Mismatch -> rejection event + `classification_accepted=False` return. Mirrors Phase 404's diff-the-proposed-write pattern (cross-validation against deterministic signals before the side-effecting event lands). The 5 steps run in deterministic order; earlier steps short-circuit (return early on rejection). Step 5 (cap check) runs LAST because the cap-exceeded path still emits the `deviation_logged` event for audit-trail completeness.

### Numbered protocol

1. **Re-compute `issue_signature`** from the current `(task_id, rule_id, error_kind, file:line, matched_token)` tuple via the SHA-256 function defined in Section 7. Compare with the agent-supplied value. Disagreement -> emit `state.step.deviation_classification_rejected` with `reason: "issue_signature_mismatch"`, return early with `classification_accepted=False` and `rejection_reason="issue_signature_mismatch"`.

2. **Rule-4 alternatives check:** if `rule_id == 4`, require `alternatives is not None and len(alternatives) >= 2 and sum(o.recommended for o in alternatives) == 1`. Mismatch -> emit `state.step.deviation_classification_rejected` with `reason: "rule_4_alternatives_missing"` (when `alternatives` is None or shorter than 2) or `"rule_4_recommended_invalid"` (when zero or multiple `recommended=True` entries exist). Return early with `classification_accepted=False`.

3. **Rule-4 auto-promotion (arch-pattern allowlist):** scan the agent's recent `Write/Edit` targets (sourced from `tool.execute.before` event audit, last 60s window scoped to the current `session_id`) against `ARCH_PATTERN_ALLOWLIST` (Section 5). If `rule_id ∈ {1, 2, 3}` but a recent write target hits the allowlist -> emit `state.step.deviation_classification_rejected` with `reason: "arch_pattern_promotion_required"`; the agent must re-call with `rule_id=4` and an `alternatives` payload. Return early with `classification_accepted=False`. The cross-validation flow sets `classification_source="arch_pattern_match"` on the final accepted re-call (server-recomputed).

4. **`scope_deviation_request` correlation:** if there is an open `state.step.scope_deviation_request` (Phase 404 SRP-04 territory) for this `(task_id, requested_path)` AND the path matches the arch-pattern allowlist, force `rule_id=4`. Emit `state.step.deviation_classification_rejected` with `reason: "scope_deviation_correlation_promoted"` if the agent supplied a lower `rule_id`. Return early with `classification_accepted=False`. The daemon's `classification_source` projection sets the final value to `"harness_promoted"` on the accepted re-call. This step links the deviation chain to the scope-prohibition machinery from Phase 404 — see `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` SRP-04 for the upstream event shape.

5. **Cap check:** query event store for `count(state.step.deviation_logged WHERE (task_id, rule_id, issue_signature) = ?)`. If `count >= 3` (this would be the 4th attempt) -> set `cap_exceeded=True` on the return; emit `state.step.deviation_cap_exceeded`; auto-escalate per the rule's escalation path (Rule 3 -> `checkpoint:decision`; Rules 1-2 -> force Rule-4 promotion). The event emit for the original `deviation_logged` STILL happens (audit-trail completeness) but with `resolution: "aborted_chain"` set at emission time.

Steps 1-5 run in deterministic order. Step 5 (cap check) runs LAST because the cap-exceeded path still emits the `deviation_logged` event for audit. Earlier steps short-circuit (return early on rejection). v14 implements as a synchronous chain inside `state_build/deviation/log_deviation.py`. Mirrors Phase 404 PROOF-GATE.md Section 6 strike-counter-evaluated-at-completion-claim ordering discipline.

### Server-side recomputation discipline

The daemon recomputes `issue_signature`, `attempt_number`, `cap_exceeded`, and `classification_source` from authoritative server-side state; agent-emitted values for these fields are recomputed at the cross-validation boundary (mirrors Phase 404's PRF `overall_passed` server-recomputation pattern + gsd-2's `server-recomputation-of-llm-emitted-fields.md`). Mismatch between agent input and server recomputation triggers the rejection events listed above. The `classification_source` field's final value is server-set: `agent_declared` (default) -> `harness_promoted` (cross-validation step 3 override) -> `arch_pattern_match` (step 4 override). The agent's emitted `classification_source` value is treated as a hint, not as authoritative.

---

## Arch-Pattern Allowlist (Rule-4 Detection)

The canonical pure-machine signal for an architectural change is a `Write/Edit` target matching the arch-pattern allowlist. Mirrors Phase 404's `READ_ONLY_PATTERNS` + `WRITE_SYSCALL_PATTERNS` single-module shape; lives at `state_build/deviation/arch_patterns.py`. The allowlist is a flat list of `re.Pattern` objects; match is first-match-wins against the normalised path.

### Regex allowlist

Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Rule-4 detection (DEV-04, arch-pattern allowlist)" subsection:

```python
import re

ARCH_PATTERN_ALLOWLIST: list[re.Pattern] = [
    re.compile(r"^alembic/(?!README)"),                          # any non-README path under alembic/
    re.compile(r"(?:^|/)migrations/[^/]+\.(py|sql)$"),
    re.compile(r"(?:^|/)schema\.(sql|prisma|graphql)$"),
    re.compile(r"^pyproject\.toml$|^uv\.lock$"),                # dep-list mutations (planner validates ADD vs BUMP)
    re.compile(r"^src/state_[a-z_]+/__init__\.py$"),            # new top-level package init creation
    re.compile(r"(?:^|/)mcp/tools/[^/]+\.py$"),                  # new MCP tool registrations
]
```

### Match semantics

- Match is against the **proposed write target path** (the file path the agent attempts to Write/Edit), intercepted via `tool.execute.before`. Not against existing on-disk content. The intercept point is the same as Phase 404's read-only-write prohibition gate; the two gates share the same audit window.
- Paths are normalised to repo-root-relative POSIX form (forward slashes always) before matching. Symlinks resolved; `.`/`..` segments normalised via `pathlib.PurePosixPath`. Absolute paths that fall outside the worktree root are rejected at a separate gate (Phase 404 SRP-01 territory) before reaching this check.
- First-match-wins; the order in the list is not semantically significant beyond determinism (mirrors gsd-2 `dispatch-rules-table.md` first-match-wins pattern). The list is a `list[re.Pattern]`, not a `set[...]`, to preserve insertion-order determinism for audit-log replay.

### ADD vs BUMP discrimination (pyproject.toml / uv.lock)

- **Pure-machine diff parse.** Lines beginning `+` matching regex `^\+\s*"[a-zA-Z0-9_\-]+>=` match the **ADD** pattern (adding a new dependency declaration).
- Lines matching `-\s*"X>=A.B"\s*\n\+\s*"X>=C.D"` (same package name X on both lines, only version delta) match the **BUMP** pattern.
- **ADD -> arch-pattern match (force Rule 4).** A new dependency is an architectural decision — it expands the project's supply chain and threat model, requires license review, and is irreversible without further cleanup.
- **BUMP -> no auto-promotion.** Version pin updates are routine (Rule 3 or below); the existing CI matrix and lockfile-update flows handle them without architectural review.
- **Multi-line YAML/TOML edge cases** (e.g., `pyproject.toml` `dependencies = [...]` array spanning many lines with one declaration per line): the planner pins the exact tokenizer in v14; for now the discriminator regex above is the starter set. v14 may upgrade to a TOML-aware parser if false-positive ADD/BUMP discrimination becomes a problem.

### Module ownership

Single-source-of-truth module: `state_build/deviation/arch_patterns.py`. Exports:

- `ARCH_PATTERN_ALLOWLIST: list[re.Pattern]` — the allowlist constant as rendered above.
- `match_arch_pattern(path: str) -> bool` — boolean predicate; returns `True` on first match.
- `classify_diff_kind(file_path: str, diff_text: str) -> Literal['ADD', 'BUMP', 'NEITHER']` — diff-text analyser for `pyproject.toml` / `uv.lock` to discriminate ADD vs BUMP.

v14 implements the module; v15 wires the daemon middleware to call `match_arch_pattern` during cross-validation step 3 and `classify_diff_kind` for the ADD/BUMP discriminator in cross-validation step 4 (when a `pyproject.toml` or `uv.lock` change is the trigger). The module ships with unit tests asserting the regex behaviour against a fixture path corpus rendered in `tests/state_build/deviation/test_arch_patterns.py`.

### Allowlist evolution policy

The allowlist starts at 6 patterns intentionally. Adding a new pattern is itself a Rule 4 architectural decision — the act of expanding the Rule 4 surface is, by construction, an architectural choice that requires human approval. New pattern additions follow the same `log_deviation(rule_id=4)` flow as any other architectural change. The single-source-of-truth module path `state_build/deviation/arch_patterns.py` is the only location where the allowlist may be edited; CI lint rejects allowlist modifications landed via any other path. This bootstrap discipline mirrors gsd-2's approach to `READ_ONLY_PATTERNS` curation at `branch-patterns.ts` — the pattern list is treated as project-level policy, not as a per-Slice configuration knob.

### Negative-space documentation (what is NOT a Rule 4 path)

The allowlist is intentionally narrow. Examples of paths that DO NOT trigger Rule 4 promotion:

- `src/state_*/**/*.py` (any file under an existing top-level package — these are routine edits within established architecture).
- `tests/**/*.py` (test changes — even adding new test files — are Rule 1 or Rule 2 territory, not architectural).
- `docs/**/*.md` (documentation changes — Rule 1 if fixing typos, Rule 2 if adding missing docs).
- `.planning/**/*.md` (planning artefacts — handled by the GSD workflow, not the deviation chain).
- `pyproject.toml` lines that BUMP an existing dependency (the BUMP regex catches these and skips auto-promotion).

The negative-space documentation is critical because false-positive Rule 4 promotions block routine work; the allowlist is calibrated to catch only the truly architectural cases. v14 ships with a regression corpus that exercises both positive and negative cases.

### Commit Trailer Convention (STATE-* Naming Discipline)

State keeps gsd-2's 7-rule keyword-based type-inference table (`COMMIT_TYPE_RULES`, sourced from `git-service.ts:616`) unchanged for the conventional-commit prefix selection. State adds new trailers on top of the inferred prefix:

```
fix: resolve null-pointer in CompactionSnapshot.serialize

Restore the missing None-guard before orjson.dumps.

STATE-Task: 405-deviation-rules/step-2
STATE-DeviationRule: 1
STATE-DeviationAttempt: 1
```

- `STATE-Task: <step_id>` — mandatory on every commit produced inside a Step. Identifies the originating step for audit and for the SUMMARY projector's join key.
- `STATE-DeviationRule: N` (N ∈ {1, 2, 3, 4}) — mandatory on every commit produced as the resolution of an open deviation. Auditor grep target enumerates every architectural change ever made.
- `STATE-DeviationAttempt: K` (K ∈ {1, 2, 3}) — mandatory alongside `STATE-DeviationRule`. For Rule 4 commits, K is always 1.
- `STATE-Subagent-Invocation: <invocation_id>` — mandatory on every commit produced inside a subagent session (Plan 02 owns this trailer; cited here for completeness of the trailer family).

**Auditor grep target:** `git log --grep="STATE-DeviationRule: 4"` enumerates every architectural change ever made. The CI naming-discipline grep target scans `.planning/milestones/v41/phases/405/` for any uppercase legacy trailer prefix matching `\bG[S]D-` and MUST return zero (project naming discipline — `STATE-*` only; the legacy lowercase project-name reference `gsd-2` is allowed as a design-heritage citation, but uppercase trailer prefixes from that lineage are a deferred-rename item handled in the `<deferred>` section of 405-CONTEXT.md).

**Single-source-of-truth module:** `state_build/commit/trailers.py` exports the trailer constants + the `infer_commit_type(message: str, files: list[str]) -> Literal['fix','feat','refactor','docs','test','chore','perf']` function (adapted from gsd-2's `git-service.ts` keyword table; the table content is unchanged, only the trailer-emission helper is novel to state). v14 implements; v15 wires the trailer emission at commit-time from the deviation-resolution code path.

### Trailer rendering order

The trailer block at the foot of a commit message follows a deterministic order to support `git interpret-trailers` parsing and pure-machine audit:

1. `STATE-Task: <step_id>` (always first; identifies the originating step).
2. `STATE-DeviationRule: N` (when a deviation is being resolved).
3. `STATE-DeviationAttempt: K` (always immediately after `STATE-DeviationRule`).
4. `STATE-Subagent-Invocation: <invocation_id>` (when authored inside a subagent session; Plan 02 territory).
5. Any additional `STATE-*` trailers added by future phases follow alphabetical order.

The renderer module `state_build/commit/trailers.py` exports a single helper `render_trailers(state_task: str, deviation: tuple[int, int] | None = None, subagent_invocation: str | None = None, extra: dict[str, str] | None = None) -> str` that produces the trailer block as a string, ready for concatenation to the commit message body. The helper enforces ordering and rejects unknown trailer keys (Pydantic-validated against a Literal whitelist).

### Mode-isolation note (commit machinery)

The trailer module lives under `state_build/commit/`; MUST NOT import from `state_teach/`. CI import-graph lint enforces. Teach-mode has its own (smaller) trailer family registered under `state_teach/commit/trailers.py` covering `STATE-Lesson:` and `STATE-Checkpoint:` (Plan 02 of a future teach-mode phase will pin the exact list). The two trailer modules share no code; the helper signatures are similar but not unified, by design.

---

## Tiered Autonomy (DEV-05, DEV-06)

The harness's per-checkpoint-type behaviour is governed by an autonomy mode set at the milestone default, optionally overridden per Slice via frontmatter. The mode determines whether `checkpoint:human-verify` / `checkpoint:decision` / `checkpoint:human-action` auto-resolve or stop. Rule-4 deviations are the 4th column and always stop regardless of mode (structural, not policy — see Section 2 Rule 4 closing paragraph). The autonomy mode is a project-wide policy knob; the per-Slice override is the only escape hatch.

### Autonomy modes

| Mode | `checkpoint:human-verify` | `checkpoint:decision` | `checkpoint:human-action` | **Rule 4 deviation** |
|---|---|---|---|---|
| `--tiered` (default) | auto-approve | stop | stop | **stop** |
| `--full-yolo` | auto-approve | auto-pick option 1 | stop | **stop** |
| `--conservative` | stop | stop | stop | **stop** |

The autonomy table's first three columns are inherited verbatim from Phase 403 task-type behaviours; the fourth column (Rule 4 deviation) is novel to Phase 405. Implementation guarantee: the `log_deviation(rule_id=4, ...)` MCP handler synchronously renders opencode `question` tool with the `alternatives` payload — **there is no autonomy short-circuit code path**. The structural enforcement is the absence of an `if mode == 'full-yolo' bypass` branch in `state_build/deviation/log_deviation.py`. CI lint MAY add a regex check for the absence (e.g., `! grep -qE 'full[_-]yolo.*bypass' state_build/deviation/log_deviation.py`); v14 owns the lint addition.

### Per-Slice override (DEV-06)

- **Slice frontmatter field:** `autonomy: Literal["tiered","full-yolo","conservative"] | None = None`. Lives at the **Slice** level only — there is no Step-level override (locked by Phase 403's "`autonomy` is NOT a Step frontmatter field" decision; see `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md`).
- **Precedence rule:** `milestone default -> Slice override -> done`. The effective autonomy for any deviation/checkpoint decision is `Slice.frontmatter.autonomy ?? milestone.autonomy_default`. The daemon resolves the effective value at Slice-load time and caches it for the lifetime of the Slice session.
- **Direction:** the Slice override CAN move stricter (e.g., milestone `--tiered`, Slice `--conservative`) AND CAN move looser (e.g., milestone `--tiered`, Slice `--full-yolo`). **Narrowing-only does NOT apply to autonomy** — autonomy is policy, not capability. The narrowing-only rule (which applies to `allowed_subagents` per SUB-03, Plan 02 territory) is capability-only.
- **Rationale:** mirrors gsd-2's permissive-vs-strict trust-model divergence (`precedence-divergence-by-trust-model.md`); state's permissive-pole choice here reflects the user-controlled-runtime framing — the runtime operator chooses how much autonomy to grant per Slice, and the planner-time validation does not interfere.
- **Forward-pointer:** subagent autonomy inheritance (SUB-09) consumes the Slice's effective autonomy as the default for `dispatch_subagent` child sessions; see SUBAGENT-MANAGEMENT.md.

### Resolution priority worked example

Given milestone default `--tiered`, Slice `slice-3-eventstore` with frontmatter `autonomy: "full-yolo"`, and a `checkpoint:decision` raised inside that Slice's `execute` stage:

1. Daemon loads Slice frontmatter at session start; caches `effective_autonomy="full-yolo"`.
2. Checkpoint raised; daemon's checkpoint dispatcher reads cached value.
3. Lookup in autonomy table: `--full-yolo` row, `checkpoint:decision` column -> `auto-pick option 1`.
4. Daemon auto-resolves with the recommended option; emits `checkpoint_auto_resolved` event.
5. If the same Slice raises a Rule 4 deviation, the 4th column wins regardless: daemon stops, renders question.

---

## issue_signature Derivation

The per-tuple counter requires a deterministic, host-independent identifier for "the same logical failure." `issue_signature` is a SHA-256 16-char hex of canonicalized inputs. Determinism across hosts is critical because the event store is portable — replaying a project's history on a different machine MUST produce identical `issue_signature` values, else the per-tuple counters drift and the audit chain breaks.

### Function

Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Attempt-counter semantics (DEV-07 expanded)" subsection:

```python
import hashlib
from enum import Enum

def compute_issue_signature(
    error_kind: "ErrorKind",
    file_path: str,                                      # repo-root-relative POSIX
    line_no: int,                                        # 1-indexed
    matched_token: str,                                  # failing token / error head / scanner match
) -> str:
    canonical = f"{error_kind.value}|{file_path}|{line_no}|{matched_token}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

### ErrorKind enum

```python
class ErrorKind(str, Enum):
    pytest_failure = "pytest_failure"
    type_error = "type_error"                            # mypy / pyright
    import_error = "import_error"
    null_dereference = "null_dereference"
    schema_validation_failure = "schema_validation_failure"  # Pydantic validation
    scope_violation = "scope_violation"                  # 404 SRP-04 deviation request territory
    paralysis_threshold_cross = "paralysis_threshold_cross"  # 404 APG event-correlation
    proof_gate_failure = "proof_gate_failure"            # 404 PRF gate_strike correlation
    subagent_spot_check_failure = "subagent_spot_check_failure"
    other = "other"                                      # fallback; planner extends as new categories emerge
```

Open-ended; planner extends in v14 as new failure modes surface (recommended additions deferred to v14 EXEMPLAR: `oauth_refresh_failure`, `worktree_checkout_failure`, `pygit2_lock_contention`, `mcp_tool_validation_failure`). The enum is `str`-based so `error_kind.value` is the canonical string form for hashing; Pydantic v2 serializes string-Enum members as their values by default.

### Why whole-stack hashing is rejected

Whole-stack hashing — i.e., including the Python stack trace in the signature inputs — is **rejected**. Research confirmed OS/env differences make stack traces nondeterministic across hosts: file-system paths differ (`/Users/alice/...` vs `/home/bob/...`), Python build flavours produce different frame-formatting (CPython vs PyPy), and venv vs system-Python path resolution diverges. The 4-tuple `(error_kind, file_path, line_no, matched_token)` is the minimum-spec set that preserves cross-host determinism while still distinguishing logically-distinct failures. The 4-tuple is the contract; future enrichment to the canonical form requires a Rule 4 architectural change.

### matched_token extraction

When the error has a clear failing token (e.g., a Python identifier in a `TypeError`, a missing import name in an `ImportError`, a failing pytest assertion's left-hand operand), use that token. When the error has no clear token, fall back to the first line of the error message truncated to 64 characters. v14 finalizes the exact extraction rule; the matcher lives at `state_build/deviation/error_extraction.py`. The truncation length 64 mirrors gsd-2's `formatFailureContext` token-extraction discipline.

### file_path canonicalisation

Repo-root-relative POSIX form (forward slashes always). Computed via `pathlib.PurePosixPath` against the worktree root. Symlinks resolved; `.`/`..` segments normalized. v14 pins the exact `os.path.relpath` vs `pathlib.PurePosixPath.relative_to` strategy; both produce the same canonical output for normal repo paths but differ on edge cases involving symlinks across mountpoints — v14 picks `pathlib` for portability.

---

## Three-Counter Independence

State has three independent counter chains, each capable of independently reaching force-stop / human-gate. Each chain has its own per-tuple key and trigger. Conflating any pair violates gsd-2 `loop-control.md` §0 Correction 1 — the prior-art project tracked four distinct counters at four scopes and learned the hard way that merging them produces incorrect terminal verdicts. State's discipline matches: three chains, three scopes, one umbrella event.

### Three independent chains

| Chain | Per-tuple key | Trigger | Owner |
|---|---|---|---|
| APG `paralysis_event` | `(task_id,)` | N consecutive read-only operations | Phase 404 |
| PRF `gate_strike` | `(task_id, check_id)` | Failed `must_haves.*` or `<verify>` at completion-claim | Phase 404 |
| DEV `deviation_logged` | `(task_id, rule_id, issue_signature)` | `log_deviation` MCP call | Phase 405 |

**Umbrella event:** the `state.harness.intervention` event (HRN-05, owned by Phase 406) is the SOLE rollup point. All three chains cite it as `trigger_reason`. Mirrors gsd-2 `loop-control.md` §0 Correction 1's refusal to conflate four distinct counters at four scopes — state's discipline matches.

### Counter scope and reset-on-success

- **Scope:** per-`(task_id, rule_id, issue_signature)` tuple. Wider scopes (Step-level, Slice-level) risk cross-task chain poisoning — a deviation in one task should not affect another task's chain even when the rule_id and signature happen to match. Narrower scopes (per-`invocation_id`) let the agent game by re-invoking with different prompts; the per-tuple key denies that escape hatch.
- **Reset rule:** on success of the same `(task_id, rule_id, issue_signature)` tuple, the counter drops to 0. "Success" = the next pure-machine eval of that exact tuple returns success (failing test now passes; type error gone; scanner clean). Different tuples never share state.
- **Rationale:** preserves audit clarity AND chain interpretability. The same tuple succeeding signals "this issue is resolved"; the counter dropping to 0 lets a future regression of the SAME issue start a fresh chain — distinguishable from "this issue has been retried 3 times and failed."
- **Mirrors:** gsd-2's `consecutiveAllToolErrorTurns = 0`-on-success pattern (`agent-loop.ts:191`) AND Phase 404 PRF strike-chain-resets-on-success principle (see `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` Section 6).

### log_deviation mid-task semantics (different-from-PRF)

`log_deviation` can be called any time during task execution; the harness records and counters increment. Mid-task incidental calls (e.g., agent realizes a fix attempt failed before commit) accrue toward the 3-attempt cap. Mirrors Phase 404's "strike accrues at completion-claim boundary" discipline NOT applied here — deviations are agent-declared explicitly, not inferred. v14 implements without a completion-claim guard at the MCP boundary. The mid-task semantics are intentional: the agent owns the timing of deviation declaration, and the daemon owns the cap enforcement.

### Independence enforcement (CI lint)

The three counters live in three different modules:

- `state_build/paralysis/counter.py` — APG counter (Phase 404 owns).
- `state_build/proof/counter.py` — PRF counter (Phase 404 owns).
- `state_build/deviation/counter.py` — DEV counter (Phase 405 owns).

Cross-module imports are forbidden by CI lint. Each counter has its own event-store query, its own per-tuple key, and its own escalation verdict. The umbrella event (HRN-05) is the ONLY shared touch-point and lives in `state_build/harness/intervention.py` (Phase 406 territory). The independence discipline survives because no module imports another module's counter state directly — events are the only communication channel.

---

## Deviation Event Payload

### Pydantic event schema

Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Attempt-counter semantics (DEV-07 expanded)" subsection (the `## deviation event payload` block):

```python
from datetime import datetime

class Deviation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deviation_event_id: str                              # ulid; primary key
    task_id: str
    step_id: str
    slice_id: str
    session_id: str
    rule_id: Literal[1, 2, 3, 4]
    issue_signature: str                                 # 16-char hex
    attempt_number: int                                  # 1..3 for Rules 1-3; always 1 for Rule 4
    classification_source: Literal[
        "agent_declared",
        "harness_promoted",
        "arch_pattern_match",
    ]
    commit_sha: str | None                               # the fix commit if any (set on resolution)
    resolution: Literal[
        "auto_fix_succeeded",
        "auto_fix_failed",
        "escalated_to_decision",
        "escalated_to_human_gate",
        "aborted_chain",
        "pending",                                       # initial state at log_deviation; mutates on resolution
    ]
    alternatives: list[Rule4Option] | None               # only populated for rule_id=4
    error_excerpt: str                                   # ≤2KB; gsd-2 truncation discipline
    agent_response_summary: str                          # ≤2KB
    triggered_at: datetime                               # UTC, ISO-8601
    intervention_event_id: str | None                    # cross-link to HRN-05 umbrella (Phase 406)
```

### Event ring (4 new event types)

The deviation chain introduces four new event types under the `state.step.deviation_*` namespace, registered by Plan 04 in `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`:

- `state.step.deviation_logged` — primary event; emitted by the `log_deviation` MCP handler after cross-validation succeeds (or on cap-exceeded for audit completeness). Rides the `Deviation` Pydantic payload above. This is the row that the SUMMARY projector keys aggregation on.
- `state.step.deviation_classification_rejected` — emitted when any of cross-validation steps 1-4 rejects the agent's classification. Rides a `DeviationClassificationRejected` Pydantic payload:

```python
class DeviationClassificationRejected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    attempted_rule_id: Literal[1, 2, 3, 4]
    reason: Literal[
        "issue_signature_mismatch",
        "rule_4_alternatives_missing",
        "rule_4_recommended_invalid",
        "arch_pattern_promotion_required",
        "scope_deviation_correlation_promoted",
    ]
    agent_response_summary: str                          # ≤2KB
    triggered_at: datetime
    session_id: str
```

- `state.step.deviation_resolution_recorded` — append-only mutation event; updates the `Deviation` row's `resolution` from `pending` to one of the 5 terminal values (`auto_fix_succeeded`, `auto_fix_failed`, `escalated_to_decision`, `escalated_to_human_gate`, `aborted_chain`). Rides `{deviation_event_id, resolution, commit_sha, triggered_at}`.
- `state.step.deviation_cap_exceeded` — emitted when cross-validation step 5 detects the 4th attempt on the same tuple. Rides `{task_id, rule_id, issue_signature, prior_attempt_count: int, escalation_path: Literal['rule_4_promotion','checkpoint_decision'], triggered_at, session_id}`.

### Append-only mutation pattern

**Single-mutable-row pattern.** The `Deviation` row's `resolution` field starts as `pending` at `deviation_logged` time; mutates to a terminal value via an append-only `deviation_resolution_recorded` event. The projector applies these events in event-store seq order; the latest `deviation_resolution_recorded.resolution` for a given `deviation_event_id` wins. **Replay determinism preserved** — never edited in-place; the event store is authoritative.

**Two-event request/resolved split (404-style) rejected.** Diverges from Phase 404's `scope_deviation_request` / `scope_deviation_resolved` two-event split because the deviation lifecycle is short-lived (≤3 attempts) and lives within one task boundary; a single row simplifies the `## Deviations` SUMMARY projector. The mutation event is sufficient for replay determinism; v14 wires the resolution-mutation step inside `log_deviation` (success path) and inside the cross-validation rejection / cap-exceeded path.

### Mode-isolation

The `Deviation` payload lives under `state_build/deviation/payloads.py`; MUST NOT import from `state_teach/`. CI import-graph lint enforces. The four event types are registered in `BUILD_ONLY_EVENT_PREFIXES` (Plan 04 owns the registration). Replay determinism is build-mode-scoped; teach-mode has no deviation chain (teach-mode's failure handling is materially different — see Phase 406 teach-mode amendments).

---

## ## Deviations SUMMARY Section Projector

The projector renders the `## Deviations` section into `stepNSUMMARY.md` at task end by aggregating `deviation_logged` + `deviation_resolution_recorded` events for the current `(step_id, slice_id)`. The section is omitted entirely when zero deviations exist for the Step. Mirrors Phase 404's `N-VERIFICATION.md` projector pattern + gsd-2's `db-writer.ts` projection discipline.

### Algorithm (numbered)

1. Subscribe to `state.step.deviation_logged` + `state.step.deviation_resolution_recorded` events, filtered by `(step_id, slice_id)`.
2. Aggregate by `(rule_id, issue_signature)` — one row per unique issue. Multiple attempts on the same tuple collapse to one row with `Attempts = max(attempt_number) / 3` (or `1 / 1` for Rule 4).
3. Determine each row's `Resolution` by applying mutation events in event-store seq order; the latest `deviation_resolution_recorded.resolution` for the row's `deviation_event_id` wins. Rows with no resolution mutation render as `pending`.
4. Render the markdown table (column order below) into the `## Deviations` section. Atomic write via temp+rename (acknowledged as not-yet-atomic per Phase 402 §7.3 note for `last-snapshot.md`; v44 follow-up applies).
5. Invalidate the read cache (mirrors gsd-2 `invalidateStateCache()` + `clearParseCache()` trio in `db-writer.ts`).
6. If zero rows aggregate, the `## Deviations` section is **omitted entirely** from `stepNSUMMARY.md` (do not render an empty section).

### Column schema (8 columns)

| Column | Source | Notes |
|---|---|---|
| `#` | row ordinal | Stable across runs (sorted by first `triggered_at`) |
| `Rule` | `Deviation.rule_id` formatted as "Rule 1", "Rule 2", "Rule 3", "Rule 4" | |
| `Issue` | `Deviation.error_excerpt[:120]` | gsd-2 truncation, ≤120 char excerpt |
| `Source` | `Deviation.classification_source` | |
| `Attempts` | `max(attempt_number) / 3` | "2 / 3" form; for Rule 4 always "1 / 1" |
| `Resolution` | terminal `Deviation.resolution` | |
| `Commit` | `Deviation.commit_sha[:7]` | short SHA; "—" if pending |
| `When` | `Deviation.triggered_at` | ISO-8601 UTC |

### Module ownership

Single-source-of-truth module: `state_build/projectors/deviation_summary.py`. Subscribes to the daemon's event-store SSE stream filtered by step_id; renders to `slices/N-name/stepNSUMMARY.md` `## Deviations` section. v14 implements; v15 wires from the verify-slice stage. The projector module exports a single `render_deviations_section(step_id: str, slice_id: str) -> str | None` helper that returns the rendered markdown block or `None` when zero deviations exist for the step.

### Mode-isolation

The projector module lives under `state_build/projectors/`; MUST NOT import from `state_teach/`. CI import-graph lint enforces. The `## Deviations` section is a Build-mode-only artefact; teach-mode's `stepNSUMMARY.md` has no equivalent section (teach-mode's per-step summary uses a different schema documented in a future teach-mode phase).

### Authoritative ordering

Pydantic class definitions in this spec are authoritative. The column-schema table is the canonical column-order definition; v14 unit tests assert the projector's output matches the column order byte-for-byte. Any drift between the projector's emitted column order and this spec is a CI failure.

### Worked example: rendered output

A rendered `## Deviations` section for a step that hit Rule 1 twice and Rule 4 once:

```
## Deviations

| # | Rule | Issue | Source | Attempts | Resolution | Commit | When |
|---|---|---|---|---|---|---|---|
| 1 | Rule 1 | AssertionError: expected 14 events, got 13 in test_eventstore... | agent_declared | 2 / 3 | auto_fix_succeeded | a1b2c3d | 2026-05-11T14:32:11Z |
| 2 | Rule 4 | Adding redis>=5.0 to pyproject.toml for read-cache implementation | arch_pattern_match | 1 / 1 | escalated_to_human_gate | — | 2026-05-11T14:51:03Z |
```

The example illustrates: ordinal `#` stable across runs (sorted by first `triggered_at`); `Issue` truncated to ≤120 chars; `Attempts` rendered as "2 / 3" for Rule 1, "1 / 1" for Rule 4; `Commit` is `—` for the pending Rule 4 row (resolution arrived but no commit landed yet because the human gate is awaiting decision); `When` in ISO-8601 UTC.

### Forward-pointers

- Plan 02 of Phase 405 — SUBAGENT-MANAGEMENT.md — consumes the deviation-chain pattern for subagent crash-recovery counter accounting (SUB-07's 3-restart counter mirrors DEV-07's 3-attempt counter).
- Plan 04 of Phase 405 — Event-taxonomy amendments — registers the four new `state.step.deviation_*` events in `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md`.
- Phase 406 — Harness rollup — registers the `state.harness.intervention` umbrella event (HRN-05) that this spec's three-counter-independence subsection forward-references.
- v14 (Build Kernel) — implements `state_build/deviation/log_deviation.py`, `state_build/deviation/arch_patterns.py`, `state_build/deviation/counter.py`, `state_build/deviation/escalation.py`, `state_build/deviation/payloads.py`, `state_build/commit/trailers.py`, and `state_build/projectors/deviation_summary.py`.
- v15 (Build Core Commands) — wires the daemon middleware to invoke the cross-validation flow at `log_deviation` MCP tool-call time, and wires the projector to fire at task-end during the verify-slice stage.

---

## Appendix A — Module Index (single-source-of-truth references)

The Phase 405 deviation chain is implemented across the following modules. Each module is named once as the canonical SOT; duplicate or shadow copies are CI-forbidden.

| Module | Owner | Purpose |
|---|---|---|
| `state_build/deviation/log_deviation.py` | v14 | MCP tool handler; cross-validation flow runner |
| `state_build/deviation/arch_patterns.py` | v14 | `ARCH_PATTERN_ALLOWLIST` + `match_arch_pattern` + `classify_diff_kind` |
| `state_build/deviation/counter.py` | v14 | Per-tuple attempt counter projection from event store |
| `state_build/deviation/escalation.py` | v14 | `escalate_chain` verdict helper for Rules 1-3 cap-exceeded paths |
| `state_build/deviation/payloads.py` | v14 | `Deviation`, `Rule4Option`, `DeviationLogResult`, `DeviationClassificationRejected` Pydantic classes |
| `state_build/deviation/error_extraction.py` | v14 | `matched_token` extraction helper for `compute_issue_signature` inputs |
| `state_build/commit/trailers.py` | v14 | `STATE-*` trailer constants + `infer_commit_type` + `render_trailers` helper |
| `state_build/projectors/deviation_summary.py` | v14 | `## Deviations` SUMMARY section projector |

Each module ships with unit tests under `tests/state_build/deviation/`; the test corpus exercises all four rule classification flows + arch-pattern allowlist regex behaviour + counter reset-on-success + projector column-order assertions.

## Appendix B — Verbatim citations (heritage references)

The spec borrows extensively from gsd-2 design heritage. The canonical citations:

- `gsd-2/kb/walkthroughs/git-service.ts.md:616` — `COMMIT_TYPE_RULES` 7-rule keyword table; state's `infer_commit_type` is a Python port with the keyword table unchanged.
- `gsd-2/kb/walkthroughs/loop-control.md` §0 Correction 1 — three-counter independence rationale; state's discipline matches.
- `gsd-2/kb/walkthroughs/server-recomputation-of-llm-emitted-fields.md` — defensive recomputation pattern; state applies to `attempt_number`, `cap_exceeded`, `classification_source`, `issue_signature`.
- `gsd-2/kb/walkthroughs/tool-system.md` §5 — MCP-tool-call-as-canonical-agent-intent-signal; `log_deviation` follows the pattern.
- `gsd-2/kb/walkthroughs/db-writer.ts.md` §1, §2, §6, §10, §12 — projection cache-invalidation discipline; `## Deviations` projector mirrors.
- `gsd-2/kb/walkthroughs/precedence-divergence-by-trust-model.md` — permissive-vs-strict trust-model framing; per-Slice autonomy override follows the permissive pole.
- `gsd-2/kb/walkthroughs/dispatch-rules-table.md` — first-match-wins pattern; `ARCH_PATTERN_ALLOWLIST` adopts.
- `gsd-2/agent-loop.ts:191` — `consecutiveAllToolErrorTurns = 0`-on-success pattern; DEV counter reset-on-success mirrors.

## Appendix C — Cross-spec links (sibling and prior-phase references)

- `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` — PRF gate_strike chain; DEV chain mirrors the per-tuple counter discipline at a different tuple shape (`(task_id, rule_id, issue_signature)` vs PRF's `(task_id, check_id)`).
- `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` — `scope_deviation_request` (SRP-04); cross-validation step 4 correlates against open requests.
- `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md` — APG `paralysis_event` chain; the first of the three independent counters.
- `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` — Slice frontmatter schema; `autonomy: Literal["tiered","full-yolo","conservative"] | None` field lands here (DEV-06).
- `.planning/milestones/v41/phases/403/specs/PLAN-AS-PROMPT.md` — `checkpoint:decision` / `checkpoint:human-verify` / `checkpoint:human-action` task types; the autonomy table's first three columns reference these.
- `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — `stepNSUMMARY.md` generation precedent; `## Deviations` projector follows the SUMMARY-as-event-projection pattern.
- `.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md` — event-naming convention `state.{tier}.{action}`; Plan 04 registers the four new `state.step.deviation_*` events.
- `.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md` — Pydantic `extra="forbid"` convention; all classes in this spec follow.

## Appendix D — Deferred items

The following items are explicitly deferred to later phases / milestones:

- **`error_kind` enum expansion** — v14 EXEMPLAR recommends adding `oauth_refresh_failure`, `worktree_checkout_failure`, `pygit2_lock_contention`, `mcp_tool_validation_failure`. Phase 405 ships with the 10 starter values; expansion is a routine Rule 2 addition in v14.
- **TOML-aware ADD/BUMP discriminator** — the current discriminator uses line-level regex; a TOML-aware parser is deferred to v15 if false-positives become a problem.
- **`matched_token` extraction edge cases** — v14 pins the exact extraction rule; the 64-char truncation fallback is the safe default.
- **Atomic SUMMARY temp+rename** — acknowledged not-yet-atomic per Phase 402 §7.3 note for `last-snapshot.md`; v44 follow-up applies the same fix to the `## Deviations` projector.
- **CI lint for autonomy-bypass absence** — v14 owns adding the `! grep -qE 'full[_-]yolo.*bypass'` lint to the pre-commit hook.
- **Grandchild fanout counter** — Plan 02 territory (SUB-04); rejected for v1, revisit if concurrency-storm patterns surface.

## Appendix E — Glossary of terms used in this spec

- **Deviation** — a logged deviation event; one of four rule classes.
- **`issue_signature`** — SHA-256 16-char hex deterministic identifier for "the same logical failure."
- **Per-tuple key** — the composite identifier that scopes a counter chain; `(task_id, rule_id, issue_signature)` for DEV.
- **Reset-on-success** — counter drops to 0 when the next pure-machine eval of the same tuple returns success.
- **Cross-validation flow** — the daemon's 5-step pure-machine validation of an agent-declared deviation.
- **Arch-pattern allowlist** — the 6 regex patterns that force Rule 4 promotion.
- **ADD vs BUMP** — pure-machine diff parse discriminator for `pyproject.toml` / `uv.lock`.
- **Append-only mutation** — single-row pattern via append-only `deviation_resolution_recorded` events.
- **Three-counter independence** — APG, PRF, DEV chains are independent; HRN-05 is the sole rollup.
- **Tiered autonomy** — the three-mode autonomy policy (`--tiered`, `--full-yolo`, `--conservative`) + Rule 4 always-stop fourth column.
- **Per-Slice override** — Slice frontmatter `autonomy` field; precedence `milestone default -> Slice override`.
